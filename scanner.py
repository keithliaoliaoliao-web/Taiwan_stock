"""
scanner.py
台股量化選股系統核心執行排程器
架構：組別 4 (任務 K 20日高點突破 + 投信濾網 C + 50% 市場廣度濾網 + 1% 以損定量 + V1 20EMA 出場)
"""

from datetime import datetime, timedelta
import json
import math
import os
import time
import numpy as np
import pandas as pd
import pytz
import requests

import config
from data_fetcher import fetch_history, get_market_status
from price_action_engine import PriceActionEngine
from universe_updater import update_universe


def sanitize_for_json(obj):
    """
    全域 JSON 資料清洗函式：
    將所有 Python/NumPy 的 NaN 與 Infinity 轉為 None (JSON null)
    """
    if isinstance(obj, (float, np.floating)):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return float(obj)
    if isinstance(obj, (int, np.integer)):
        return int(obj)
    if isinstance(obj, (bool, np.bool_)):
        return bool(obj)
    if isinstance(obj, dict):
        return {str(k): sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize_for_json(i) for i in obj]
    return obj


def fetch_institutional_chips(ticker: str, target_date: str) -> dict:
    """
    向 FinMind API 查詢單一標的之三大法人籌碼 (濾網 C：投信買超檢定)
    """
    clean_id = ticker.split(".")[0].strip()
    target_dt_str = pd.to_datetime(target_date).strftime("%Y-%m-%d")
    start_dt = (pd.to_datetime(target_dt_str) - pd.Timedelta(days=15)).strftime("%Y-%m-%d")
    url = "https://api.finmindtrade.com/api/v4/data"
    params = {
        "dataset": "TaiwanStockInstitutionalInvestorsBuySell",
        "data_id": clean_id,
        "start_date": start_dt,
        "end_date": target_dt_str
    }
    token = os.getenv("FINMIND_TOKEN", "")
    if token:
        params["token"] = token

    headers = {"User-Agent": "Mozilla/5.0"}
    f_net, t_net, d_net = 0, 0, 0
    t_5d = 0
    try:
        r = requests.get(url, params=params, headers=headers, timeout=8)
        if r.status_code == 200:
            data = r.json().get("data", [])
            if data:
                df_c = pd.DataFrame(data)
                df_c["net"] = df_c["buy"] - df_c["sell"]
                day_c = df_c[df_c["date"] == target_dt_str]
                if day_c.empty:
                    # 若當日籌碼尚未出爐，取最新一日
                    latest_d = df_c["date"].max()
                    day_c = df_c[df_c["date"] == latest_d]
                for _, row in day_c.iterrows():
                    name_s = str(row.get("name", "")).lower()
                    if "foreign" in name_s:
                        f_net += row["net"]
                    elif "trust" in name_s:
                        t_net += row["net"]
                    elif "dealer" in name_s:
                        d_net += row["net"]
                trust_all = df_c[df_c["name"].str.contains("Investment_Trust|投信", case=False, na=False)]
                if not trust_all.empty:
                    t_5d = trust_all.tail(5)["net"].sum()
    except Exception:
        pass

    trust_buy = bool(t_net > 0 or t_5d > 0)
    return {
        "foreign_net": int(f_net),
        "trust_net": int(t_net),
        "trust_5d": int(t_5d),
        "trust_buy_pass": trust_buy
    }


def evaluate_portfolio_holdings(current_prices: dict, dfs: dict, ticker_name_map: dict):
    """
    評估個人真實持倉 (portfolio.csv)，計算未實現損益與 20EMA 出場警示
    """
    portfolio_file = "portfolio.csv"
    if not os.path.exists(portfolio_file):
        with open(portfolio_file, "w", encoding="utf-8-sig") as f:
            f.write("ticker,name,entry_date,shares,entry_price,stop_loss,status,exit_date,exit_price\n")
        return [], 0.0, 0.0, False

    try:
        pf_df = pd.read_csv(portfolio_file)
    except Exception:
        return [], 0.0, 0.0, False

    if pf_df.empty or "status" not in pf_df.columns:
        return [], 0.0, 0.0, False

    holdings = pf_df[pf_df["status"] == "HOLDING"].copy()
    results = []
    tot_val = 0.0
    tot_pnl = 0.0
    any_alert = False

    for _, row in holdings.iterrows():
        tkr = str(row["ticker"]).strip()
        name = row.get("name", ticker_name_map.get(tkr, tkr))
        shares = int(row.get("shares", 0))
        entry_p = float(row.get("entry_price", 0.0))
        stop_p = float(row.get("stop_loss", 0.0)) if pd.notna(row.get("stop_loss")) else 0.0
        cur_p = current_prices.get(tkr, entry_p)

        df_h = dfs.get(tkr)
        ema20 = cur_p
        if df_h is not None and not df_h.empty:
            ema20 = float(df_h["Close"].ewm(span=20, adjust=False).mean().iloc[-1])

        is_broken_ema = bool(cur_p < ema20)
        is_hit_stop = bool(stop_p > 0 and cur_p <= stop_p)
        is_broken = is_broken_ema or is_hit_stop

        pnl = (cur_p - entry_p) * shares
        ret_pct = ((cur_p - entry_p) / entry_p * 100.0) if entry_p > 0 else 0.0
        mkt_val = cur_p * shares

        tot_val += mkt_val
        tot_pnl += pnl
        if is_broken:
            any_alert = True

        if is_hit_stop:
            action_str = "🔴 觸及初始停損 (次日開盤市價賣出)"
        elif is_broken_ema:
            action_str = "🔴 跌破 20EMA (次日開盤市價賣出)"
        else:
            action_str = "🟢 持穩 20EMA (續抱)"

        results.append({
            "ticker": tkr,
            "name": name,
            "entry_date": str(row.get("entry_date", "")),
            "shares": shares,
            "entry_price": round(entry_p, 2),
            "current_price": round(cur_p, 2),
            "ema20": round(ema20, 2),
            "unrealized_pnl": round(pnl, 2),
            "return_pct": round(ret_pct, 2),
            "is_broken_ema": is_broken,
            "action_recommendation": action_str
        })

    return results, tot_val, tot_pnl, any_alert


def generate_static_html(scan_date, scan_time, market_status, signals, forming, holdings_data, tot_val, tot_pnl, any_alert):
    """
    自動生成 public/index.html 現代化儀表板 (含大盤廣度、持倉損益、明日掛單)
    """
    breadth_pct = market_status.get("breadth_pct", 0.0)
    breadth_pass = market_status.get("breadth_pass", False)

    if any_alert:
        status_bg = "#dc3545"
        status_title = "🔴 賣出警示"
        status_desc = "持倉中有標的跌破 20EMA 或停損，請於次日開盤市價結清！"
    elif not breadth_pass:
        status_bg = "#fd7e14"
        status_title = "🟠 市場廣度不足（空手防禦中）"
        status_desc = f"目前觀察池僅 {breadth_pct:.1f}% 站上 20EMA（低於 50% 門檻），系統自動攔截新買訊以保護本金。"
    elif len(signals) > 0:
        status_bg = "#198754"
        status_title = "🟢 買進訊號"
        status_desc = f"市場廣度健康 ({breadth_pct:.1f}%)，偵測到 {len(signals)} 檔符合「突破 20 日高 ＋ 投信買超」之標的！"
    else:
        status_bg = "#6c757d"
        status_title = "⚪ 續抱 / 空手觀望"
        status_desc = f"市場廣度 {breadth_pct:.1f}%，今日無新突破訊號，持倉狀態健康。"

    # 1. 持倉表格 HTML
    holdings_tr = ""
    if holdings_data:
        for h in holdings_data:
            c_color = "#dc3545" if h["unrealized_pnl"] < 0 else "#198754"
            badge = f'<span class="badge bg-danger">{h["action_recommendation"]}</span>' if h["is_broken_ema"] else '<span class="badge bg-success">🟢 持穩 20EMA (續抱)</span>'
            holdings_tr += f"""
            <tr>
                <td><strong>{h['ticker']}</strong></td><td>{h['name']}</td><td>{h['entry_date']}</td>
                <td>{h['shares']:,}</td><td>{h['entry_price']:.2f}</td><td><strong>{h['current_price']:.2f}</strong></td>
                <td>{h['ema20']:.2f}</td><td style="color:{c_color}; font-weight:bold;">{h['unrealized_pnl']:+,.0f} ({h['return_pct']:+.2f}%)</td>
                <td>{badge}</td>
            </tr>"""
    else:
        holdings_tr = '<tr><td colspan="9" class="text-center py-3 text-muted">目前 portfolio.csv 中無持倉記錄</td></tr>'

    # 2. 買進訊號表格 HTML
    signals_tr = ""
    if signals:
        for s in signals:
            signals_tr += f"""
            <tr>
                <td><strong>{s['ticker']}</strong></td><td>{s['name']}</td>
                <td><span class="badge bg-primary">{s['grade']} 級</span></td>
                <td>{s['close']:.2f}</td><td style="color:#0d6efd; font-weight:bold; font-size:1.1em;">{s['trigger_price']:.2f}</td>
                <td style="color:#dc3545;">{s['stop_loss']:.2f} ({s.get('stop_pct', 0.0):.1f}%)</td>
                <td style="color:#198754;">{s['ema20']:.2f} (破線出場)</td>
                <td>{s.get('trust_net_lots', 0):+d} 張 (5日: {s.get('trust_5d_lots', 0):+d} 張)</td>
                <td><strong>{s.get('suggested_shares', 0):,} 股</strong> <small class="text-muted">(1%風險)</small></td>
            </tr>"""
    else:
        empty_msg = "市場廣度未達 50%，今日強制暫停新進場" if not breadth_pass else "今日無符合「突破 20 日高 ＋ 投信買超」之新訊號"
        signals_tr = f'<tr><td colspan="9" class="text-center py-3 text-muted">{empty_msg}</td></tr>'

    html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>臺股量化趨勢選股儀表板</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{ background-color: #f8f9fa; font-family: -apple-system, sans-serif; }}
        .card {{ border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 24px; border: none; }}
        .header-box {{ background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); color: white; padding: 22px; border-radius: 12px; margin-bottom: 20px; }}
        .light-box {{ background-color: {status_bg}; color: white; padding: 18px 24px; border-radius: 12px; font-weight: bold; margin-bottom: 20px; }}
    </style>
</head>
<body>
<div class="container py-4">
    <div class="header-box d-flex justify-content-between align-items-center">
        <div>
            <h3 class="mb-1">📊 臺股量化趨勢選股系統（任務 K 突破 ＋ 投信濾網 C）</h3>
            <small>組別 4 實證架構 | 50% 市場廣度濾網 | 1% 以損定量風控 | V1 20EMA 趨勢追蹤</small>
        </div>
        <div class="text-end"><span class="badge bg-light text-dark">更新時間: {scan_date} {scan_time}</span></div>
    </div>

    <div class="light-box d-flex justify-content-between align-items-center">
        <div><h4 class="mb-1">{status_title}</h4><div>{status_desc}</div></div>
        <div class="text-end">
            <div><small>大盤指數: {market_status['close']} ({'站上20EMA' if market_status['bullish'] else '跌破20EMA'})</small></div>
            <div><small>市場廣度: {breadth_pct:.1f}% ({'通過 >=50%' if breadth_pass else '未達 50% 防禦'})</small></div>
        </div>
    </div>

    <!-- 資產現況 -->
    <div class="row g-3 mb-4">
        <div class="col-md-4"><div class="card p-3 text-center"><div class="text-muted">持股現值總計</div><h4>{tot_val:,.0f} 元</h4></div></div>
        <div class="col-md-4"><div class="card p-3 text-center"><div class="text-muted">未實現浮動損益</div><h4 style="color:{'#dc3545' if tot_pnl < 0 else '#198754'};">{tot_pnl:+,.0f} 元</h4></div></div>
        <div class="col-md-4"><div class="card p-3 text-center"><div class="text-muted">當前持倉檔數</div><h4>{len(holdings_data)} / 5 檔</h4></div></div>
    </div>

    <!-- 區塊一：明日掛單進場清單 -->
    <div class="card p-4">
        <h5 class="text-primary mb-3">🎯 明日進場候選清單（20日高點突破 ＋ 投信買超 ＋ 1% 以損定量）</h5>
        <div class="table-responsive"><table class="table table-hover align-middle">
            <thead class="table-light"><tr><th>代號</th><th>名稱</th><th>評級</th><th>最新收盤</th><th>參考進場價</th><th>初始停損價 (距離)</th><th>動態防守 (20EMA)</th><th>投信籌碼</th><th>建議買進股數</th></tr></thead>
            <tbody>{signals_tr}</tbody>
        </table></div>
    </div>

    <!-- 區塊二：個人真實持倉 20EMA 監控 -->
    <div class="card p-4">
        <h5 class="text-success mb-3">📈 個人持倉 20EMA 趨勢監控帳本（V1 出場規則：破 20EMA 次日開盤出清）</h5>
        <div class="table-responsive"><table class="table table-hover align-middle">
            <thead class="table-light"><tr><th>代號</th><th>名稱</th><th>買進日期</th><th>股數</th><th>成本價</th><th>現價</th><th>20EMA</th><th>未實現損益</th><th>操作指示</th></tr></thead>
            <tbody>{holdings_tr}</tbody>
        </table></div>
    </div>
</div>
</body>
</html>"""

    os.makedirs("public", exist_ok=True)
    with open("public/index.html", "w", encoding="utf-8") as f:
        f.write(html)


def run_scanner():
    tz = pytz.timezone(config.TIMEZONE)
    now = datetime.now(tz)
    scan_date = now.strftime("%Y-%m-%d")
    scan_time = now.strftime("%H:%M")

    print(f"=== 開始執行台股量化趨勢掃描 (組別 4 架構) [{scan_date} {scan_time}] ===")

    # 1. 更新觀察池清單
    try:
        update_universe()
    except Exception as e:
        print(f"[警告] update_universe 失敗: {e}")

    # 2. 載入觀察池 metadata
    config.WATCHLIST_METADATA = config.load_universe()
    universe_dict = config.WATCHLIST_METADATA
    tickers = list(universe_dict.keys())
    print(f"[掃描] 載入觀察池共 {len(tickers)} 檔標的")

    # 3. 抓取大盤指數狀態
    market_status = get_market_status(config.BENCHMARK_TICKER)
    t_now = now.time()
    is_post = (t_now >= datetime.strptime("13:30", "%H:%M").time() or now.weekday() > 4)
    market_status["market_phase"] = "盤後定盤" if is_post else "盤中即時"

    # 風控參數：預設總本金 100 萬，單筆最大虧損 1% (10,000 元)，單筆最大投入 25% (250,000 元)
    account_capital = float(getattr(config, "ACCOUNT_CAPITAL", 1_000_000.0))
    risk_per_trade_budget = account_capital * 0.01
    max_position_budget = account_capital * 0.25

    raw_candidates = []
    forming = []
    universe_list = []
    current_prices = {}
    dfs = {}
    above_ema20_count = 0
    valid_stock_count = 0

    # 4. 第一階段：逐檔抓取日 K 線、計算市場廣度與篩選「任務 K」突破候選股
    for idx, ticker in enumerate(tickers, start=1):
        meta = universe_dict.get(ticker, {})
        name = meta.get("name", ticker)
        sector = meta.get("sector", "其他")

        df = fetch_history(ticker, lookback_days=config.DATA_LOOKBACK_DAYS)
        time.sleep(0.2)  # 保護 FinMind API 頻率限制

        if df.empty or len(df) < 120:
            continue

        latest_bar = df.iloc[-1]
        latest_bar_date = pd.to_datetime(latest_bar["Date"])
        if (now.date() - latest_bar_date.date()).days > 6:
            continue

        close_price = float(latest_bar["Close"])
        current_prices[ticker] = close_price
        dfs[ticker] = df

        # 計算 20EMA 與任務 K (突破前 20 日高點) 指標
        df_calc = df.copy().sort_values("Date").reset_index(drop=True)
        df_calc["EMA_20"] = df_calc["Close"].ewm(span=20, adjust=False).mean()
        df_calc["Prev_20D_High"] = df_calc["High"].shift(1).rolling(20).max()
        df_calc["Vol_MA20"] = df_calc["Volume"].rolling(20).mean()
        df_calc["Low_5D"] = df_calc["Low"].rolling(5).min()

        ema20 = float(df_calc["EMA_20"].iloc[-1])
        prev_ema20 = float(df_calc["EMA_20"].iloc[-2]) if len(df_calc) > 1 else ema20
        prev_20d_high = float(df_calc["Prev_20D_High"].iloc[-1]) if pd.notna(df_calc["Prev_20D_High"].iloc[-1]) else close_price
        vol_ma20 = float(df_calc["Vol_MA20"].iloc[-1]) if pd.notna(df_calc["Vol_MA20"].iloc[-1]) else 0.0
        low_5d = float(df_calc["Low_5D"].iloc[-1]) if pd.notna(df_calc["Low_5D"].iloc[-1]) else (close_price * 0.95)

        valid_stock_count += 1
        is_above_ema20 = bool(close_price >= ema20)
        if is_above_ema20:
            above_ema20_count += 1

        turnover_series = df_calc["TradeValue"] if "TradeValue" in df_calc.columns else (df_calc["Close"] * df_calc["Volume"])
        ma_period = getattr(config, "TURNOVER_MA_PERIOD", 20)
        min_turnover_ma = getattr(config, "MIN_TURNOVER_MA", 100_000_000)
        turnover_ma20 = float(turnover_series.rolling(window=ma_period, min_periods=5).mean().iloc[-1]) if len(turnover_series) > 0 else 0.0
        is_liquid = turnover_ma20 >= min_turnover_ma
        is_valid_price = (config.MIN_PRICE <= close_price <= config.MAX_PRICE)

        prev_close = float(df_calc["Close"].iloc[-2]) if len(df_calc) > 1 else close_price
        is_limit_up = (close_price >= prev_close * 1.095)

        # 執行既有 PriceActionEngine 以維持兼容
        is_h2_orig = False
        try:
            analyzed_df = PriceActionEngine.analyze_setups(df)
            if not analyzed_df.empty:
                is_h2_orig = bool(analyzed_df.iloc[-1].get("Signal_H2", False))
        except Exception:
            analyzed_df = df_calc

        # 【任務 K 進場條件】：收盤站上 20EMA + 20EMA 上彎 + 收盤突破前 20 日最高價
        ema_slope_up = bool(ema20 > prev_ema20)
        is_task_k_breakout = (
            is_above_ema20
            and ema_slope_up
            and (close_price > prev_20d_high)
            and is_liquid
            and is_valid_price
            and not is_limit_up
        )

        # 醞釀中：站上 20EMA 且距離 20 日高點 2% 以內
        is_forming = (
            is_above_ema20
            and ema_slope_up
            and (not is_task_k_breakout)
            and (close_price >= prev_20d_high * 0.98)
            and is_liquid
            and is_valid_price
        )

        # 停損價設定：近 5 日最低點與 20EMA*0.98 取較低者
        stop_p = min(low_5d, ema20 * 0.98)
        risk_per_share = close_price - stop_p
        stop_pct = (risk_per_share / close_price * 100.0) if close_price > 0 else 0.0
        # 排除停損過寬 (>20%) 或過窄 (<1%) 的異常結構
        valid_stop_range = (1.0 <= stop_pct <= 20.0)
        is_signal_valid = is_task_k_breakout and valid_stop_range

        # 評級：同時爆量(>1.5倍均量)或共振 H2 為 A 級，標準任務 K 為 B 級
        vol_surge = bool(float(latest_bar["Volume"]) >= vol_ma20 * 1.5) if vol_ma20 > 0 else False
        grade = ("A" if (vol_surge or is_h2_orig) else "B") if is_signal_valid else "NONE"

        # 整理圖表資料
        recent_bars = df_calc.dropna(subset=["EMA_20"]).tail(250)
        candles = []
        ema_series = []
        for _, b in recent_bars.iterrows():
            d_str = pd.to_datetime(b["Date"]).strftime("%Y-%m-%d")
            op, cl = float(b["Open"]), float(b["Close"])
            candles.append({
                "time": d_str, "open": round(op, 2), "high": round(float(b["High"]), 2),
                "low": round(float(b["Low"]), 2), "close": round(cl, 2),
                "volume": round(float(b["Volume"]), 2),
                "color": "#ef4444" if cl >= op else "#22c55e"
            })
            if pd.notna(b.get("EMA_20")):
                ema_series.append({"time": d_str, "value": round(float(b["EMA_20"]), 2)})

        universe_list.append({
            "ticker": ticker, "name": name, "sector": sector,
            "close": round(close_price, 2), "ema20": round(ema20, 2),
            "turnover_ma20": round(turnover_ma20 / 1e8, 2),
            "trend_up": is_above_ema20, "has_signal": is_signal_valid, "grade": grade,
            "candles": candles, "ema": ema_series,
        })

        if is_signal_valid:
            raw_candidates.append({
                "ticker": ticker, "name": name, "sector": sector, "grade": grade,
                "date_str": latest_bar_date.strftime("%Y-%m-%d"),
                "close": close_price, "ema20": ema20,
                "trigger_price": close_price, "stop_loss": stop_p,
                "risk_per_share": risk_per_share, "stop_pct": stop_pct,
                "candles": candles, "ema": ema_series
            })
        elif is_forming:
            forming.append({
                "ticker": ticker, "name": name, "sector": sector,
                "close": round(close_price, 2), "ema20": round(ema20, 2),
                "candles": candles, "ema": ema_series,
            })

    # 5. 計算全市場廣度濾網 (50% 門檻)
    breadth_pct = (above_ema20_count / valid_stock_count * 100.0) if valid_stock_count > 0 else 0.0
    breadth_pass = bool(breadth_pct >= 50.0)
    market_status["breadth_pct"] = round(breadth_pct, 1)
    market_status["breadth_pass"] = breadth_pass
    print(f"[市場廣度] 站上 20EMA 檔數: {above_ema20_count}/{valid_stock_count} ({breadth_pct:.1f}%) -> {'通過 (>=50%)' if breadth_pass else '未通過 (<50% 啟動防禦)'}")

    # 6. 第二階段：通過廣度濾網時，僅對觸發突破之候選股查詢投信籌碼并計算 1% 以損定量股數
    signals = []
    if not breadth_pass:
        print(f"[風控攔截] 因市場廣度 ({breadth_pct:.1f}%) 低於 50%，今日自動暫停新買進訊號。")
    else:
        for cand in raw_candidates:
            ticker = cand["ticker"]
            name = cand["name"]
            chip_info = fetch_institutional_chips(ticker, cand["date_str"])
            if chip_info["trust_buy_pass"]:
                trigger_p = cand["trigger_price"]
                stop_p = cand["stop_loss"]
                risk_ps = cand["risk_per_share"]

                # 【1% 以損定量計算】：單筆最大停損 10,000 元，且單筆總投入不超過 25 萬元
                shares_by_risk = risk_per_trade_budget / risk_ps
                shares_by_cap = max_position_budget / trigger_p
                s_shares = max(1, int(min(shares_by_risk, shares_by_cap)))

                # 相容前端欄位：保留 target_price 作為 2R 參考值，實際依 V1 跌破 20EMA 出場
                target_p = trigger_p + (risk_ps * 2.0)

                signals.append({
                    "ticker": ticker, "name": name, "sector": cand["sector"], "grade": cand["grade"],
                    "close": round(cand["close"], 2), "ema20": round(cand["ema20"], 2),
                    "trigger_price": round(trigger_p, 2),
                    "stop_loss": round(stop_p, 2), "stop_pct": round(cand["stop_pct"], 1),
                    "target_price": round(target_p, 2),
                    "trust_net_lots": int(chip_info["trust_net"] / 1000),
                    "trust_5d_lots": int(chip_info["trust_5d"] / 1000),
                    "suggested_shares": s_shares,
                    "candles": cand["candles"], "ema": cand["ema"],
                })
                print(f"  ★ [正式買訊：任務K突破＋投信買超] {ticker} {name} ({cand['grade']}級) | 進場: {trigger_p:.2f}, 停損: {stop_p:.2f} (-{cand['stop_pct']:.1f}%), 1%風險建議股數: {s_shares} 股")
            else:
                print(f"  [濾網排除] {ticker} {name} 雖突破 20 日高，但投信未買超")

    # 7. 評估個人真實持倉 (讀取 portfolio.csv)
    ticker_name_map = {t: universe_dict.get(t, {}).get("name", t) for t in tickers}
    holdings_data, tot_val, tot_pnl, any_alert = evaluate_portfolio_holdings(current_prices, dfs, ticker_name_map)

    # 8. 組裝與輸出 scan_result.json
    signals.sort(key=lambda x: (0 if x["grade"] == "A" else 1, x["trigger_price"]))
    output_payload = {
        "scan_date": scan_date,
        "scan_time": scan_time,
        "market_status": market_status,
        "signals": signals,
        "forming": forming,
        "holdings_status": holdings_data,
        "universe": universe_list,
    }
    clean_payload = sanitize_for_json(output_payload)
    os.makedirs("public", exist_ok=True)
    with open("public/scan_result.json", "w", encoding="utf-8") as f:
        json.dump(clean_payload, f, ensure_ascii=False, indent=2)
    with open("scan_result.json", "w", encoding="utf-8") as f:
        json.dump(clean_payload, f, ensure_ascii=False, indent=2)

    # 9. 生成靜態 public/index.html
    generate_static_html(scan_date, scan_time, market_status, signals, forming, holdings_data, tot_val, tot_pnl, any_alert)

    print()
    print("=" * 55)
    print("【掃描執行摘要 (組別 4 架構)】")
    print(f"掃描時間: {scan_date} {scan_time}")
    print(f"市場廣度: {breadth_pct:.1f}% ({'放行' if breadth_pass else '防禦攔截'})")
    print(f"產生買進訊號 (任務K+投信): {len(signals)} 檔")
    print(f"個人追蹤持倉: {len(holdings_data)} 檔 (持股市值: {tot_val:,.0f} 元, 損益: {tot_pnl:+,.0f} 元)")
    print("=" * 55)


if __name__ == "__main__":
    run_scanner()
