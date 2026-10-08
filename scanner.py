# -*- coding: utf-8 -*-
"""
台股價格行為選股系統主程式 (scanner.py)

執行流程：
1. 呼叫 universe_updater.update_universe() 更新觀察池
2. 重新載入 config.WATCHLIST_METADATA
3. 抓取大盤指數資料 (^TWII)
4. 對每檔標的抓取日線資料並呼叫 PriceActionEngine.analyze_setups()
5. 呼叫 portfolio_tracker.evaluate_holdings() 評估持倉
6. 整合所有資料為 scan_result.json 格式
7. 套用 sanitize_for_json() 後寫入 public/scan_result.json
8. 在終端機顯示完整執行摘要
"""

import os
import json
import math
import inspect
from datetime import datetime
from typing import Dict, List, Any
import pandas as pd
import pytz

import config
import universe_updater
import data_fetcher
import portfolio_tracker

# 嘗試載入使用者的價格行為引擎
try:
    from price_action_engine import PriceActionEngine
except ImportError:
    PriceActionEngine = None


def sanitize_for_json(obj: Any) -> Any:
    """
    遞迴清洗資料結構，將所有 NaN 與 Infinity 轉為 None (JSON null)
    """
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize_for_json(i) for i in obj]
    return obj


def pd_isna(val: Any) -> bool:
    """安全檢查數值是否為 NaN"""
    try:
        return math.isnan(float(val))
    except (ValueError, TypeError):
        return False


def run_scan() -> None:
    """
    主掃描排程函式
    """
    print("=" * 60)
    print("  台股價格行為選股系統 - 自動化掃描作業啟動")
    print("=" * 60)

    # 1. 更新觀察池
    universe_updater.update_universe()

    # 2. 重新載入觀察池中繼資料
    config.WATCHLIST_METADATA = config.load_universe()
    watchlist_items = list(config.WATCHLIST_METADATA.values())
    print(f"[觀察池] 載入標的共 {len(watchlist_items)} 檔")

    # 設定掃描時間（台北時區）
    tz = pytz.timezone(config.TIMEZONE)
    now = datetime.now(tz)
    scan_date = now.strftime("%Y-%m-%d")
    scan_time = now.strftime("%H:%M")

    # 3. 抓取大盤指數資料
    market_status = data_fetcher.fetch_market_index(config.BENCHMARK_TICKER)
    print(f"[大盤狀態] 加權指數收盤: {market_status.get('close')}, 20EMA: {market_status.get('ema20')}, 多頭格局: {market_status.get('bullish')}")

    engine_instance = None
    if PriceActionEngine is not None:
        if isinstance(PriceActionEngine, type):
            try:
                engine_instance = PriceActionEngine()
            except Exception:
                engine_instance = PriceActionEngine
        else:
            engine_instance = PriceActionEngine

    signals: List[Dict[str, Any]] = []
    forming: List[Dict[str, Any]] = []
    universe: List[Dict[str, Any]] = []
    current_prices: Dict[str, float] = {}

    # 4. 對每檔標的抓取日線資料並分析
    total_targets = len(watchlist_items)
    print(f"[掃描] 開始分析 {total_targets} 檔個股價格行為...")

    for idx, item in enumerate(watchlist_items, 1):
        ticker = item["ticker"]
        name = item["name"]
        sector = item.get("sector", "其他")

        df = data_fetcher.fetch_stock_daily_bars(ticker, lookback_days=config.DATA_LOOKBACK_DAYS)
        if df is None or df.empty or len(df) < config.EMA_PERIOD:
            continue

        last_row = df.iloc[-1]
        last_close = float(round(last_row["Close"], 2))
        last_ema20 = float(round(last_row["EMA20"], 2)) if "EMA20" in last_row and not pd_isna(last_row["EMA20"]) else last_close
        current_prices[ticker] = last_close

        turnover = float(last_row.get("Turnover", 0.0))
        if last_close < config.MIN_PRICE or last_close > config.MAX_PRICE:
            continue
        if turnover < config.MIN_DAILY_TURNOVER:
            continue

        trend_up = last_close > last_ema20

        # 呼叫價格行為引擎
        setup_result = None
        if engine_instance is not None and hasattr(engine_instance, "analyze_setups"):
            try:
                func = getattr(engine_instance, "analyze_setups")
                sig = inspect.signature(func)
                call_kwargs = {}
                if "ticker" in sig.parameters:
                    call_kwargs["ticker"] = ticker
                if "name" in sig.parameters:
                    call_kwargs["name"] = name
                if "sector" in sig.parameters:
                    call_kwargs["sector"] = sector
                if "config" in sig.parameters:
                    call_kwargs["config"] = config

                setup_result = func(df, **call_kwargs)
            except Exception as e:
                setup_result = None

        has_signal = False
        is_forming = False
        grade = None
        trigger_price = None
        stop_loss = None
        target_price = None
        risk_pct = None
        net_rr = None

        # 解析引擎回傳結果 (支援 DataFrame、dict 或物件)
        if setup_result is not None:
            if isinstance(setup_result, pd.DataFrame):
                # 支援 PriceActionEngine 回傳的 DataFrame 結構
                if not setup_result.empty:
                    last_setup_row = setup_result.iloc[-1]
                    grade = str(last_setup_row.get("Signal_Grade", "NONE")).strip()
                    is_signal_h2 = bool(last_setup_row.get("Signal_H2", False))
                    has_signal = bool(is_signal_h2 or grade in ["A", "B"])
                    is_forming = bool(last_setup_row.get("Setup_Forming", False))

                    trig_val = last_setup_row.get("Trigger_Price")
                    trigger_price = float(trig_val) if trig_val is not None and not pd_isna(trig_val) else None

                    stop_val = last_setup_row.get("Stop_Loss")
                    stop_loss = float(stop_val) if stop_val is not None and not pd_isna(stop_val) else None

                    target_val = last_setup_row.get("Target_Price")
                    target_price = float(target_val) if target_val is not None and not pd_isna(target_val) else None

                    risk_val = last_setup_row.get("Risk_Pct")
                    risk_pct = float(risk_val) if risk_val is not None and not pd_isna(risk_val) else None

                    rr_val = last_setup_row.get("Net_RR")
                    net_rr = float(rr_val) if rr_val is not None and not pd_isna(rr_val) else None

                    if "Always_In" in last_setup_row:
                        trend_up = bool(last_setup_row.get("Always_In") == "LONG")
            elif isinstance(setup_result, dict):
                grade = setup_result.get("grade")
                status = setup_result.get("status")
                has_signal = bool(setup_result.get("has_signal", False) or status == "SIGNAL" or grade in ["A", "B"])
                is_forming = bool(setup_result.get("is_forming", False) or status == "FORMING")
                trigger_price = setup_result.get("trigger_price") or setup_result.get("trigger") or setup_result.get("entry_price")
                stop_loss = setup_result.get("stop_loss") or setup_result.get("stop")
                target_price = setup_result.get("target_price") or setup_result.get("target")
                risk_pct = setup_result.get("risk_pct")
                net_rr = setup_result.get("net_rr") or setup_result.get("rr")
                if "trend_up" in setup_result:
                    trend_up = bool(setup_result["trend_up"])
            else:
                grade = getattr(setup_result, "grade", None)
                status = getattr(setup_result, "status", None)
                has_signal = bool(getattr(setup_result, "has_signal", False) or status == "SIGNAL" or grade in ["A", "B"])
                is_forming = bool(getattr(setup_result, "is_forming", False) or status == "FORMING")
                trigger_price = getattr(setup_result, "trigger_price", None) or getattr(setup_result, "trigger", None) or getattr(setup_result, "entry_price", None)
                stop_loss = getattr(setup_result, "stop_loss", None) or getattr(setup_result, "stop", None)
                target_price = getattr(setup_result, "target_price", None) or getattr(setup_result, "target", None)
                risk_pct = getattr(setup_result, "risk_pct", None)
                net_rr = getattr(setup_result, "net_rr", None) or getattr(setup_result, "rr", None)
                if hasattr(setup_result, "trend_up"):
                    trend_up = bool(getattr(setup_result, "trend_up"))

        # 若無自訂引擎，可根據基礎價格行為法則判定
        if setup_result is None:
            dist_to_ema = abs(last_close - last_ema20) / last_ema20 if last_ema20 > 0 else 1.0
            if trend_up and dist_to_ema <= 0.015:
                is_forming = True

        # 若觸發進場訊號，補齊關鍵價位
        if has_signal:
            candles, ema_series = data_fetcher.format_chart_series(df, bars_count=60)
            
            if trigger_price is None:
                trigger_price = last_close
            if stop_loss is None:
                stop_loss = float(df["Low"].iloc[-3:].min())
            if target_price is None:
                risk_dist = max(0.1, trigger_price - stop_loss)
                target_price = trigger_price + (risk_dist * config.TAKE_PROFIT_RR)

            trigger_price = float(round(trigger_price, 2))
            stop_loss = float(round(stop_loss, 2))
            target_price = float(round(target_price, 2))

            if risk_pct is None and trigger_price > 0:
                risk_pct = round(abs(trigger_price - stop_loss) / trigger_price * 100, 2)
            if net_rr is None and abs(trigger_price - stop_loss) > 0:
                net_rr = round(abs(target_price - trigger_price) / abs(trigger_price - stop_loss), 2)

            signals.append({
                "ticker": ticker,
                "name": name,
                "sector": sector,
                "grade": grade or "B",
                "close": last_close,
                "trigger_price": trigger_price,
                "stop_loss": stop_loss,
                "target_price": target_price,
                "risk_pct": float(risk_pct or 0.0),
                "net_rr": float(net_rr or config.TAKE_PROFIT_RR),
                "candles": candles,
                "ema": ema_series
            })

        # 醞釀中標的
        if is_forming and not has_signal:
            forming.append({
                "ticker": ticker,
                "name": name,
                "sector": sector,
                "close": last_close,
                "ema20": last_ema20
            })

        # 核心觀察池總表
        universe.append({
            "ticker": ticker,
            "name": name,
            "sector": sector,
            "close": last_close,
            "ema20": last_ema20,
            "trend_up": bool(trend_up),
            "has_signal": bool(has_signal),
            "grade": grade if has_signal else None
        })

    # 5. 評估持倉狀態
    holdings_status = portfolio_tracker.evaluate_holdings(
        current_prices=current_prices,
        holdings_path="holdings.json",
        current_date_str=scan_date
    )

    # 6. 整合所有資料
    scan_output = {
        "scan_date": scan_date,
        "scan_time": scan_time,
        "market_status": market_status,
        "signals": signals,
        "forming": forming,
        "holdings_status": holdings_status,
        "universe": universe
    }

    # 7. 套用清洗函式並輸出至 public/scan_result.json
    sanitized_output = sanitize_for_json(scan_output)
    os.makedirs("public", exist_ok=True)
    output_filepath = os.path.join("public", "scan_result.json")

    with open(output_filepath, mode="w", encoding="utf-8") as f:
        json.dump(sanitized_output, f, ensure_ascii=False, indent=2)
    print(f"[儲存] 掃描結果已成功寫入 {output_filepath}")

    # 8. 在終端機顯示執行摘要
    print("\n" + "=" * 60)
    print(f"  台股價格行為選股系統 - 執行摘要報告")
    print(f"  掃描時間: {scan_date} {scan_time}")
    market_str = "多頭格局 🟢" if market_status.get("bullish") else "空頭 / 震盪警戒 ⚠️"
    print(f"  大盤狀態: {market_str} (收盤: {market_status.get('close')}, 20EMA: {market_status.get('ema20')})")
    print(f"  核心觀察池: 共掃描 {len(universe)} 檔標的")
    print(f"  進場訊號: {len(signals)} 檔")
    for s in signals:
        print(f"    - [{s['grade']}級] {s['ticker']} {s['name']} ({s['sector']}) 觸發價: {s['trigger_price']} 停損: {s['stop_loss']} 目標: {s['target_price']}")
    print(f"  醞釀中名單: {len(forming)} 檔")
    for fm in forming[:5]:
        print(f"    - {fm['ticker']} {fm['name']} ({fm['sector']}) 收盤: {fm['close']} 20EMA: {fm['ema20']}")
    if len(forming) > 5:
        print(f"    ... 以及其餘 {len(forming) - 5} 檔")
    print(f"  個人持股監控: {len(holdings_status)} 檔")
    for h in holdings_status:
        pnl_symbol = "+" if h["unrealized_pnl"] >= 0 else ""
        print(f"    - {h['ticker']} {h['name']} [{h['status']}] 損益: {pnl_symbol}{h['unrealized_pnl']} ({pnl_symbol}{h['unrealized_pct']}%) | {h['action_desc']}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    run_scan()
