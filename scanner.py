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
    print(f"[大盤] 加權指數: {market_status['close']}, EMA20: {market_status['ema20']}, 多頭: {market_status['bullish']}")

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
        if df.empty or len(df) < config.EMA_PERIOD:
            continue

        latest_bar = df.iloc[-1]
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
        is_signal_h2 = bool(last_row.get("Signal_H2", False)) and is_liquid and is_valid_price
        is_forming = bool(last_row.get("Setup_Forming", False))
        grade = str(last_row.get("Signal_Grade", "NONE"))
        trend_up = bool(last_row.get("Always_In", "") == "LONG")

        # 整理最近 120 根 K 線與 EMA 供前端 Lightweight Charts 渲染
        recent_bars = analyzed_df.tail(120)
        candles = []
        ema_series = []
        for _, b in recent_bars.iterrows():
            d_str = str(b["Date"])
            candles.append({
                "time": d_str,
                "open": round(float(b["Open"]), 2),
                "high": round(float(b["High"]), 2),
                "low": round(float(b["Low"]), 2),
                "close": round(float(b["Close"]), 2),
            })
            if pd.notna(b.get("EMA_20")):
                ema_series.append({
                    "time": d_str,
                    "value": round(float(b["EMA_20"]), 2),
                })

        # 記錄觀察池總覽 (注入真實 K 線供看圖)
        universe_list.append({
            "ticker": ticker,
            "name": name,
            "sector": sector,
            "close": round(close_price, 2),
            "ema20": round(ema20, 2),
            "trend_up": trend_up,
            "has_signal": is_signal_h2,
            "grade": grade,
            "candles": candles,
            "ema": ema_series,
        })

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
                "close": round(close_price, 2),
                "trigger_price": round(trigger_p, 2),
                "stop_loss": round(stop_p, 2),
                "target_price": round(target_p, 2),
                "risk_pct": round(risk_pct, 2),
                "net_rr": round(net_rr, 2),
                "candles": candles,
                "ema": ema_series,
            })
            print(f"  ★ [訊號發出] {ticker} {name} (等級: {grade}) | 觸發: {trigger_p}, 停損: {stop_p}")

        # 醞釀中名單 (注入真實 K 線供看圖)
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

    # 5. 評估現有持倉 (若持倉中有不在觀察池之標的，補抓最新行情)
    from portfolio_tracker import load_holdings
    holdings_raw = load_holdings()
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
