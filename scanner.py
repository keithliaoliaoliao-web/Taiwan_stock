"""
scanner.py
台股價格行為選股系統核心執行排程器 (Strategy Freeze v1 + 投信濾網 C + 持倉 20EMA 監控)
"""

from datetime import datetime, timedelta
import json
import math
import os
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
    start_dt = (pd.to_datetime(target_date) - pd.Timedelta(days=15)).strftime("%Y-%m-%d")
    url = "https://api.finmindtrade.com/api/v4/data"
    params = {
        "dataset": "TaiwanStockInstitutionalInvestorsBuySell",
        "data_id": clean_id,
        "start_date": start_dt,
        "end_date": target_date
    }
    headers = {"User-Agent": "Mozilla/5.0"}
    f_net, t_net, d_net = 0, 0, 0
    t_5d = 0
    try:
        r = requests.get(url, params=params, headers=headers, timeout=6)
        if r.status_code == 200:
            data = r.json().get("data", [])
            if data:
                df_c = pd.DataFrame(data)
                df_c["net"] = df_c["buy"] - df_c["sell"]
                day_c = df_c[df_c["date"] == target_date]
                for _, row in day_c.iterrows():
                    name_s = str(row.get("name", "")).lower()
                    if "foreign" in name_s: f_net += row["net"]
                    elif "trust" in name_s: t_net += row["net"]
                    elif "dealer" in name_s: d_net += row["net"]
                trust_all = df_c[df_c["name"].str.contains("Investment_Trust", case=False, na=False)]
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
        # 建立空白範本檔
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
        cur_p = current_prices.get(tkr, entry_p)

        df_h = dfs.get(tkr)
        ema20 = cur_p
        if df_h is not None and not df_h.empty:
            df_ind = PriceActionEngine._prepare_indicators(df_h)
            ema20 = float(df_ind.iloc[-1].get("EMA_20", cur_p))

        is_broken = bool(cur_p < ema20)
        pnl = (cur_p - entry_p) * shares
        ret_pct = ((cur_p - entry_p) / entry_p * 100.0) if entry_p > 0 else 0.0
        mkt_val = cur_p * shares

        tot_val += mkt_val
        tot_pnl += pnl
        if is_broken: any_alert = True

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
            "action_recommendation": "🔴 跌破 20EMA (次日開盤市價賣出)" if is_broken else "🟢 持穩 20EMA (續抱)"
        })

    return results, tot_val, tot_pnl, any_alert


def generate_static_html(scan_date, scan_time, market_status, signals, forming, holdings_data, tot_val, tot_pnl, any_alert):
    """
    自動生成 public/index.html 現代化儀表板 (含大盤、持倉損益、明日掛單、醞釀中名單)
    """
    status_bg = "#dc3545" if any_alert else ("#198754" if len(signals) > 0 else "#6c757d")
    status_title = "🔴 賣出警示" if any_alert else ("🟢 買進訊號" if len(signals) > 0 else "⚪ 續抱 / 空手觀望")
    status_desc = "持倉中有標的跌破 20EMA，請於次日開盤市價結清！" if any_alert else (f"偵測到 {len(signals)} 檔符合 H2 突破＋投信買超之標的！" if len(signals) > 0 else "目前無新訊號，持倉狀態健康。")

    # 1. 持倉表格 HTML
    holdings_tr = ""
    if holdings_data:
        for h in holdings_data:
            c_color = "#dc3545" if h["unrealized_pnl"] < 0 else "#198754"
            badge = '<span class="badge bg-danger">🔴 跌破 20EMA (賣出)</span>' if h["is_broken_ema"] else '<span class="badge bg-success">🟢 續抱</span>'
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
                <td style="color:#dc3545;">{s['stop_loss']:.2f}</td><td style="color:#198754;">{s['target_price']:.2f}</td>
                <td>{s.get('trust_net_lots', 0):+d} 張 (5日: {s.get('trust_5d_lots', 0):+d} 張)</td>
                <td><strong>{s.get('suggested_shares', 1000):,} 股</strong></td>
            </tr>"""
    else:
        signals_tr = '<tr><td colspan="9" class="text-center py-3 text-muted">今日無符合「H2 突破 ＋ 投信買超」之新訊號</td></tr>'

    html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>臺股價格行為量化選股儀表板</title>
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
        <div><h3 class="mb-1">📊 臺股價格行為量化選股系統（Al Brooks H2 ＋ 投信濾網 C）</h3><small>V1 20EMA 趨勢追蹤體系 | 每檔資金 33 萬 | MaxPos=3</small></div>
        <div class="text-end"><span class="badge bg-light text-dark">更新時間: {scan_date} {scan_time}</span></div>
    </div>

    <div class="light-box d-flex justify-content-between align-items-center">
        <div><h4 class="mb-1">{status_title}</h4><div>{status_desc}</div></div>
        <div class="text-end"><small>大盤加權指數: {market_status['close']} ({'多頭' if market_status['bullish'] else '整理'})</small></div>
    </div>

    <!-- 資產現況 -->
    <div class="row g-3 mb-4">
        <div class="col-md-4"><div class="card p-3 text-center"><div class="text-muted">持股現值總計</div><h4>{tot_val:,.0f} 元</h4></div></div>
        <div class="col-md-4"><div class="card p-3 text-center"><div class="text-muted">未實現浮動損益</div><h4 style="color:{'#dc3545' if tot_pnl < 0 else '#198754'};">{tot_pnl:+,.0f} 元</h4></div></div>
        <div class="col-md-4"><div class="card p-3 text-center"><div class="text-muted">當前持倉檔數</div><h4>{len(holdings_data)} / 3 檔</h4></div></div>
    </div>

    <!-- 區塊一：明日掛單進場清單 -->
    <div class="card p-4">
        <h5 class="text-primary mb-3">🎯 明日掛單進場清單（H2 突破 ＋ 投信買超）</h5>
        <div class="table-responsive"><table class="table table-hover align-middle">
            <thead class="table-light"><tr><th>代號</th><th>名稱</th><th>評級</th><th>最新價</th><th>掛單進場價</th><th>停損防守價</th><th>2R 目標價</th><th>投信籌碼</th><th>建議股數</th></tr></thead>
            <tbody>{signals_tr}</tbody>
        </table></div>
    </div>

    <!-- 區塊二：個人真實持倉 20EMA 監控 -->
    <div class="card p-4">
        <h5 class="text-success mb-3">📈 個人持倉 20EMA 趨勢監控帳本（V1 出場規則）</h5>
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

    print(f"=== 開始執行台股價格行為掃描 [{scan_date} {scan_time}] ===")

    # 1. 更新觀察池清單
    try:
        update_universe()
    except Exception as e:
        print(f"[警告] update_universe 失敗: {e}")

    # 2. 重新載入觀察池 metadata
    config.WATCHLIST_METADATA = config.load_universe()
    universe_dict = config.WATCHLIST_METADATA
    tickers = list(universe_dict.keys())
    print(f"[掃描] 載入觀察池共 {len(tickers)} 檔標的")

    # 3. 抓取大盤指數狀態
    market_status = get_market_status(config.BENCHMARK_TICKER)
    t_now = now.time()
    is_post = (t_now >= datetime.strptime("13:30", "%H:%M").time() or now.weekday() > 4)
    market_status["market_phase"] = "盤後定盤" if is_post else "盤中即時"

    signals = []
    forming = []
    universe_list = []
    current_prices = {}
    dfs = {}

    # 4. 逐檔抓取行情與分析
    for idx, ticker in enumerate(tickers, start=1):
        meta = universe_dict.get(ticker, {})
        name = meta.get("name", ticker)
        sector = meta.get("sector", "其他")

        df = fetch_history(ticker, lookback_days=config.DATA_LOOKBACK_DAYS)
        if df.empty or len(df) < 120:
            continue

        latest_bar = df.iloc[-1]
        latest_bar_date = pd.to_datetime(latest_bar["Date"])
        if (now.date() - latest_bar_date.date()).days > 6:
            continue

        close_price = float(latest_bar["Close"])
        current_prices[ticker] = close_price
        dfs[ticker] = df

        turnover_series = df["TradeValue"] if "TradeValue" in df.columns else (df["Close"] * df["Volume"])
        ma_period = getattr(config, "TURNOVER_MA_PERIOD", 20)
        min_turnover_ma = getattr(config, "MIN_TURNOVER_MA", 100_000_000)
        turnover_ma20 = float(turnover_series.rolling(window=ma_period, min_periods=5).mean().iloc[-1]) if len(turnover_series) > 0 else 0.0
        is_liquid = turnover_ma20 >= min_turnover_ma
        is_valid_price = (config.MIN_PRICE <= close_price <= config.MAX_PRICE)

        try:
            analyzed_df = PriceActionEngine.analyze_setups(df)
        except Exception:
            continue

        if analyzed_df.empty:
            continue

        last_row = analyzed_df.iloc[-1]
        ema20 = float(last_row.get("EMA_20", 0.0))
        
        prev_close = float(df['Close'].iloc[-2]) if len(df) > 1 else close_price
        is_limit_up = (close_price >= prev_close * 1.095)

        is_signal_h2 = bool(last_row.get("Signal_H2", False)) and is_liquid and is_valid_price and not is_limit_up
        is_forming = bool(last_row.get("Setup_Forming", False)) and is_liquid and is_valid_price
        grade = str(last_row.get("Signal_Grade", "NONE"))
        trend_up = bool(last_row.get("Always_In", "") == "LONG")

        # 整理圖表資料
        valid_ema_df = analyzed_df.dropna(subset=["EMA_20"])
        recent_bars = valid_ema_df.tail(250) if len(valid_ema_df) >= 250 else valid_ema_df
        candles = []
        ema_series = []
        for _, b in recent_bars.iterrows():
            d_str = str(b["Date"])
            op, cl = float(b["Open"]), float(b["Close"])
            candles.append({"time": d_str, "open": round(op, 2), "high": round(float(b["High"]), 2), "low": round(float(b["Low"]), 2), "close": round(cl, 2), "volume": round(float(b["Volume"]), 2), "color": '#ef4444' if cl >= op else '#22c55e'})
            if pd.notna(b.get("EMA_20")):
                ema_series.append({"time": d_str, "value": round(float(b["EMA_20"]), 2)})

        universe_list.append({
            "ticker": ticker, "name": name, "sector": sector,
            "close": round(close_price, 2), "ema20": round(ema20, 2),
            "turnover_ma20": round(turnover_ma20 / 1e8, 2),
            "trend_up": trend_up, "has_signal": is_signal_h2, "grade": grade,
            "candles": candles, "ema": ema_series,
        })

        # 訊號符合 (H2 突破) -> 啟動【任務 G 投信買超濾網 C】驗證
        if is_signal_h2:
            chip_info = fetch_institutional_chips(ticker, str(latest_bar["Date"]))
            if chip_info["trust_buy_pass"]:
                trigger_p = float(last_row.get("Trigger_Price", close_price))
                stop_p = float(last_row.get("Stop_Loss", 0.0))
                target_p = float(last_row.get("Target_Price", 0.0))
                s_shares = max(1000, int((333_333.0 / trigger_p) // 1000 * 1000)) if trigger_p > 0 else 0

                signals.append({
                    "ticker": ticker, "name": name, "sector": sector, "grade": grade,
                    "close": round(close_price, 2), "trigger_price": round(trigger_p, 2),
                    "stop_loss": round(stop_p, 2), "target_price": round(target_p, 2),
                    "trust_net_lots": int(chip_info["trust_net"] / 1000),
                    "trust_5d_lots": int(chip_info["trust_5d"] / 1000),
                    "suggested_shares": s_shares,
                    "candles": candles, "ema": ema_series,
                })
                print(f"  ★ [正式買訊：H2突破＋投信買超] {ticker} {name} (等級: {grade}) | 掛單進場: {trigger_p}, 停損: {stop_p}")
            else:
                print(f"  [濾網排除] {ticker} {name} 雖符合 H2，但投信未買超 (已濾除假突破)")

        elif is_forming:
            forming.append({
                "ticker": ticker, "name": name, "sector": sector,
                "close": round(close_price, 2), "ema20": round(ema20, 2),
                "candles": candles, "ema": ema_series,
            })

    # 5. 評估個人真實持倉 (讀取 portfolio.csv)
    ticker_name_map = {t: universe_dict.get(t, {}).get("name", t) for t in tickers}
    holdings_data, tot_val, tot_pnl, any_alert = evaluate_portfolio_holdings(current_prices, dfs, ticker_name_map)

    # 6. 組裝與輸出 scan_result.json (供原本的前端使用)
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

    # 7. 生成現代化靜態 public/index.html (含紅綠燈號與個人持倉帳本)
    generate_static_html(scan_date, scan_time, market_status, signals, forming, holdings_data, tot_val, tot_pnl, any_alert)

    print()
    print("=" * 50)
    print("【掃描執行摘要】")
    print(f"掃描時間: {scan_date} {scan_time}")
    print(f"產生買進訊號 (H2+投信): {len(signals)} 檔")
    print(f"個人追蹤持倉: {len(holdings_data)} 檔 (持股市值: {tot_val:,.0f} 元, 損益: {tot_pnl:+,.0f} 元)")
    print(f"結果已成功輸出至: public/scan_result.json 與 public/index.html")
    print("=" * 50)


if __name__ == "__main__":
    run_scanner()
