"""
scanner.py
台股價格行為選股系統核心執行排程器
"""

from datetime import datetime
import json
import math
import os
import numpy as np
import pandas as pd
import pytz

import config
from data_fetcher import fetch_history, get_market_status
from portfolio_tracker import evaluate_holdings
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


def run_scanner():
    tz = pytz.timezone(config.TIMEZONE)
    now = datetime.now(tz)
    scan_date = now.strftime("%Y-%m-%d")
    scan_time = now.strftime("%H:%M")

    print(f"=== 開始執行台股價格行為掃描 [{scan_date} {scan_time}] ===")

    # 1. 更新觀察池清單
    update_universe()

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
    print(f"[大盤] 加權指數: {market_status['close']}, EMA20: {market_status['ema20']}, 多頭: {market_status['bullish']} ({market_status['market_phase']})")

    signals = []
    forming = []
    universe_list = []
    current_prices = {}

    # 4. 逐檔抓取行情與分析
    for idx, ticker in enumerate(tickers, start=1):
        meta = universe_dict.get(ticker, {})
        name = meta.get("name", ticker)
        sector = meta.get("sector", "其他")

        df = fetch_history(ticker, lookback_days=config.DATA_LOOKBACK_DAYS)
        # 防禦升級 2：溫機資料不足過濾（少於 120 根有效 K 棒之新股/標的一律跳過）
        if df.empty or len(df) < 120:
            continue

        latest_bar = df.iloc[-1]
        
        # 防禦升級 3：停牌與無交易過濾（最後一根 K 棒日期距離當前超過 6 天視為停牌或無成交）
        latest_bar_date = pd.to_datetime(latest_bar["Date"])
        if (now.date() - latest_bar_date.date()).days > 6:
            continue

        close_price = float(latest_bar["Close"])
        volume = float(latest_bar["Volume"])
        current_prices[ticker] = close_price

        # 流動性指標：近 20 個交易日平均日成交金額 (無前視偏誤，嚴格僅計算至當日)
        turnover_series = df["TradeValue"] if "TradeValue" in df.columns else (df["Close"] * df["Volume"])
        ma_period = getattr(config, "TURNOVER_MA_PERIOD", 20)
        min_turnover_ma = getattr(config, "MIN_TURNOVER_MA", 100_000_000)
        turnover_ma20 = float(turnover_series.rolling(window=ma_period, min_periods=5).mean().iloc[-1]) if len(turnover_series) > 0 else 0.0
        is_liquid = turnover_ma20 >= min_turnover_ma
        is_valid_price = (config.MIN_PRICE <= close_price <= config.MAX_PRICE)

        try:
            analyzed_df = PriceActionEngine.analyze_setups(df)
        except Exception as e:
            print(f"[分析異常] {ticker} ({name}): {e}")
            continue

        if analyzed_df.empty:
            continue

        last_row = analyzed_df.iloc[-1]
        ema20 = float(last_row.get("EMA_20", 0.0))
        
        # 嚴格過濾：台股漲停鎖死標的（當日漲幅大於 9.5% 或接近漲停）避免追高風險
        prev_close = float(df['Close'].iloc[-2]) if len(df) > 1 else close_price
        is_limit_up = (close_price >= prev_close * 1.095)

        is_signal_h2 = bool(last_row.get("Signal_H2", False)) and is_liquid and is_valid_price and not is_limit_up
        is_forming = bool(last_row.get("Setup_Forming", False)) and is_liquid and is_valid_price
        grade = str(last_row.get("Signal_Grade", "NONE"))
        trend_up = bool(last_row.get("Always_In", "") == "LONG")

        # 整理最近 1 年 (約 250 根交易日) K 線與 20EMA 供前端渲染
        valid_ema_df = analyzed_df.dropna(subset=["EMA_20"])
        recent_bars = valid_ema_df.tail(250) if len(valid_ema_df) >= 250 else valid_ema_df
        if recent_bars.empty:
            recent_bars = analyzed_df.tail(250)

        candles = []
        ema_series = []
        for _, b in recent_bars.iterrows():
            d_str = str(b["Date"])
            op = float(b["Open"])
            cl = float(b["Close"])
            vol = float(b["Volume"])
            candles.append({
                "time": d_str,
                "open": round(op, 2),
                "high": round(float(b["High"]), 2),
                "low": round(float(b["Low"]), 2),
                "close": round(cl, 2),
                "volume": round(vol, 2),
                "color": '#ef4444' if cl >= op else '#22c55e'
            })
            if pd.notna(b.get("EMA_20")):
                ema_series.append({
                    "time": d_str,
                    "value": round(float(b["EMA_20"]), 2),
                })

        universe_list.append({
            "ticker": ticker,
            "name": name,
            "sector": sector,
            "close": round(close_price, 2),
            "ema20": round(ema20, 2),
            "turnover_ma20": round(turnover_ma20 / 1e8, 2),
            "trend_up": trend_up,
            "has_signal": is_signal_h2,
            "grade": grade,
            "candles": candles,
            "ema": ema_series,
        })

        # 防禦升級 1：盤中即時預覽防護標註
        is_intraday_preview = (datetime.strptime("09:00", "%H:%M").time() <= t_now <= datetime.strptime("13:30", "%H:%M").time() and now.weekday() <= 4)
        status_label = "[盤中預覽] (Intraday Preview)" if is_intraday_preview else "[正式定盤]"

        # 訊號符合 (H2 突破)
        if is_signal_h2:
            trigger_p = float(last_row.get("Trigger_Price", close_price))
            stop_p = float(last_row.get("Stop_Loss", 0.0))
            target_p = float(last_row.get("Target_Price", 0.0))
            risk_pct = float(last_row.get("Risk_Pct", 0.0))
            net_rr = float(last_row.get("Net_RR", config.R_MULTIPLE))

            signals.append({
                "ticker": ticker,
                "name": name,
                "sector": sector,
                "grade": grade,
                "status_label": status_label,
                "close": round(close_price, 2),
                "trigger_price": round(trigger_p, 2),
                "stop_loss": round(stop_p, 2),
                "target_price": round(target_p, 2),
                "risk_pct": round(risk_pct, 2),
                "net_rr": round(net_rr, 2),
                "candles": candles,
                "ema": ema_series,
            })
            print(f"  ★ [訊號發出 {status_label}] {ticker} {name} (等級: {grade}) | 觸發: {trigger_p}, 停損: {stop_p}")

        # 醞釀中名單
        elif is_forming:
            forming.append({
                "ticker": ticker,
                "name": name,
                "sector": sector,
                "close": round(close_price, 2),
                "ema20": round(ema20, 2),
                "candles": candles,
                "ema": ema_series,
            })
            print(f"  ● [醞釀中] {ticker} {name} | 現價: {close_price}, 20EMA: {ema20}")

    # 5. 評估現有持倉與持倉上限警示
    from portfolio_tracker import load_holdings
    holdings_raw = load_holdings()
    portfolio_warning = ""
    if len(holdings_raw) >= 3:
        portfolio_warning = "⚠️ 當前持倉已滿 3 檔，建議依紀律不開新倉"
        print(f"[持倉警示] {portfolio_warning}")

    # 防禦升級 4：訊號排序（A 級優先，B 級次之，同級別按 Net_RR 降冪排序）
    signals.sort(key=lambda x: (0 if x["grade"] == "A" else 1, -x["net_rr"]))

    for h in holdings_raw:
        ht = h.get("ticker")
        if ht and ht not in current_prices:
            try:
                hdf = fetch_history(ht, lookback_days=5)
                if not hdf.empty:
                    current_prices[ht] = float(hdf.iloc[-1]["Close"])
            except Exception as e:
                print(f"[提示] 持股 {ht} 補抓收盤行情失敗: {e}")

    holdings_status = evaluate_holdings(current_prices)

    # 6. 組裝輸出資料
    output_payload = {
        "scan_date": scan_date,
        "scan_time": scan_time,
        "market_status": market_status,
        "signals": signals,
        "forming": forming,
        "holdings_status": holdings_status,
        "universe": universe_list,
        "portfolio_warning": portfolio_warning,
    }

    # 7. 全域清洗並寫入 public/scan_result.json
    clean_payload = sanitize_for_json(output_payload)
    os.makedirs("public", exist_ok=True)
    out_path = os.path.join("public", "scan_result.json")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(clean_payload, f, ensure_ascii=False, indent=2)

    with open("scan_result.json", "w", encoding="utf-8") as f:
        json.dump(clean_payload, f, ensure_ascii=False, indent=2)

    # 8. 終端機摘要
    print()
    print("=" * 50)
    print("【掃描執行摘要】")
    print(f"掃描時間: {scan_date} {scan_time}")
    print(f"大盤趨勢: {'多頭格局' if market_status['bullish'] else '防禦警戒'}")
    print(f"產生買進訊號: {len(signals)} 檔")
    print(f"醞釀中標的: {len(forming)} 檔")
    print(f"追蹤持倉標的: {len(holdings_status)} 檔")
    print(f"結果已成功輸出至: {out_path}")
    print("=" * 50)
    print()


if __name__ == "__main__":
    run_scanner()
