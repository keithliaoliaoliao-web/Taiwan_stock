"""
scanner.py
台股價格行為選股系統核心執行排程器 (Strategy Freeze v1 + 投信濾網 C + holdings.json 監控)
"""

from datetime import datetime
import json
import math
import os
import numpy as np
import pandas as pd
from zoneinfo import ZoneInfo
import requests

import config
from data_fetcher import fetch_history
from price_action_engine import PriceActionEngine
try:
    from universe_updater import update_universe
except Exception:
    def update_universe():
        print("[跳過] universe_updater.py 未包含，使用現有 watchlist.csv")
        return True


def sanitize_for_json(obj):
    """全域 JSON 資料清洗函式：將 NaN 與 Infinity 轉為 None"""
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
    """向 FinMind API 查詢單一標的之三大法人籌碼 (濾網 C：投信買超檢定)

    C3 FIX：日期一律正規化為 %Y-%m-%d 後再比對（原實作把含時間的
    timestamp 字串與 FinMind 的 date-only 字串直接比較，導致 day_c 永遠為空）。
    濾網條件由 (當日>0) OR (5日>0) 收緊為 AND，避免過去一週曾買過即放行的
    無效濾網。
    """
    clean_id = ticker.split(".")[0].strip()
    target_norm = pd.to_datetime(target_date).strftime("%Y-%m-%d")
    start_dt = (pd.to_datetime(target_norm) - pd.Timedelta(days=15)).strftime("%Y-%m-%d")
    url = "https://api.finmindtrade.com/api/v4/data"
    params = {
        "dataset": "TaiwanStockInstitutionalInvestorsBuySell",
        "data_id": clean_id,
        "start_date": start_dt,
        "end_date": target_norm
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
                df_c["date"] = pd.to_datetime(df_c["date"], errors="coerce").dt.strftime("%Y-%m-%d")
                df_c["net"] = df_c["buy"] - df_c["sell"]
                day_c = df_c[df_c["date"] == target_norm]
                for _, row in day_c.iterrows():
                    name_s = str(row.get("name", "")).lower()
                    if "foreign" in name_s: f_net += row["net"]
                    elif "trust" in name_s: t_net += row["net"]
                    elif "dealer" in name_s: d_net += row["net"]
                trust_all = df_c[df_c["name"].str.contains("Investment_Trust", case=False, na=False)]
                if not trust_all.empty:
                    t_5d = trust_all[trust_all["date"] <= target_norm].tail(5)["net"].sum()
    except Exception:
        pass

    # AND 條件：當日買超且 5 日累計為正
    trust_buy = bool(t_net > 0 and t_5d > 0)
    return {
        "foreign_net": int(f_net),
        "trust_net": int(t_net),
        "trust_5d": int(t_5d),
        "trust_buy_pass": trust_buy
    }


def get_market_status(ticker: str) -> dict:
    # 大盤指數 (如 ^TWII) 不在 FinMind 中，直接回傳占位
    if not ticker or ticker.startswith("^") or "." not in ticker:
        return {"ticker": ticker, "status": "index_not_available", "note": "大盤指數不在 FinMind 資料集中"}
    try:
        df = fetch_history(ticker, lookback_days=30)
        if df.empty:
            return {"ticker": ticker, "status": "no_data"}
        last = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else last
        close = float(last["Close"])
        prev_close = float(prev["Close"])
        change = round(close - prev_close, 2)
        change_pct = round((close - prev_close) / prev_close * 100, 2) if prev_close > 0 else 0.0
        return {"ticker": ticker, "close": round(close, 2), "change": change, "change_pct": change_pct, "date": str(last["Date"])[:10]}
    except Exception as e:
        return {"ticker": ticker, "status": "error", "error": str(e)}


def load_holdings(filepath: str = "holdings.json") -> list:
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def evaluate_holdings(current_prices: dict, dfs: dict) -> list:
    holdings = load_holdings()
    result = []
    for h in holdings:
        ticker = h.get("ticker", "")
        entry_price = float(h.get("entry_price", 0))
        stop_loss = float(h.get("stop_loss", 0))
        shares = int(h.get("shares", 0))
        name = h.get("name", ticker)
        entry_date = h.get("entry_date", "")
        cur_price = current_prices.get(ticker)
        if cur_price is None:
            df = dfs.get(ticker)
            if df is not None and not df.empty:
                cur_price = float(df.iloc[-1]["Close"])
            else:
                cur_price = entry_price
        unrealized_pnl = round((cur_price - entry_price) * shares, 0) if shares > 0 else 0
        unrealized_pct = round((cur_price - entry_price) / entry_price * 100, 2) if entry_price > 0 else 0.0
        at_stop = cur_price <= stop_loss if stop_loss > 0 else False
        result.append({"ticker": ticker, "name": name, "entry_date": entry_date, "entry_price": entry_price, "current_price": round(cur_price, 2), "shares": shares, "stop_loss": stop_loss, "unrealized_pnl": unrealized_pnl, "unrealized_pct": unrealized_pct, "at_stop": at_stop, "status": "AT_STOP" if at_stop else "HOLDING"})
    return result


def run_scanner():
    tz = ZoneInfo(config.TIMEZONE)
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
    mtr_signals = []
    wedge_signals = []
    bom_signals = []
    climax_signals = []
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
        # C3: dividend adjustment for clean signal detection
        try:
            from data_fetcher import fetch_dividends, adjust_for_dividends
            div_df = fetch_dividends(ticker, lookback_days=config.DATA_LOOKBACK_DAYS)
            df_adj = adjust_for_dividends(df, div_df)
        except Exception:
            df_adj = df

        latest_bar = df.iloc[-1]
        latest_bar_date = pd.to_datetime(latest_bar["Date"])
        if (now.date() - latest_bar_date.date()).days > 6:
            continue

        close_price = float(latest_bar["Close"])
        # 即時報價 (盤中使用 TWSE MIS API，盤後 fallback 到 EOD 收盤)
        if getattr(config, "USE_REALTIME_PRICE", False):
            try:
                from data_fetcher import fetch_realtime_price
                rt = fetch_realtime_price(ticker)
                if rt and rt.get("price"):
                    close_price = float(rt["price"])
            except Exception:
                pass
        current_prices[ticker] = close_price

        turnover_series = df["TradeValue"] if "TradeValue" in df.columns else (df["Close"] * df["Volume"])
        ma_period = getattr(config, "TURNOVER_MA_PERIOD", 20)
        min_turnover_ma = getattr(config, "MIN_TURNOVER_MA", 100_000_000)
        turnover_ma20 = float(turnover_series.rolling(window=ma_period, min_periods=5).mean().iloc[-1]) if len(turnover_series) > 0 else 0.0
        is_liquid = turnover_ma20 >= min_turnover_ma
        is_valid_price = (config.MIN_PRICE <= close_price <= config.MAX_PRICE)

        try:
            analyzed_df = PriceActionEngine.analyze_setups(df_adj)
        except Exception:
            continue

        if analyzed_df.empty:
            continue

        dfs[ticker] = analyzed_df
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
            candles.append({
                "time": d_str,
                "open": round(op, 2), "high": round(float(b["High"]), 2),
                "low": round(float(b["Low"]), 2), "close": round(cl, 2),
                "volume": round(float(b["Volume"]), 2),
                "color": '#ef4444' if cl >= op else '#22c55e'
            })
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
                risk_pct = float(last_row.get("Risk_Pct", 0.0))
                net_rr = float(last_row.get("Net_RR", config.R_MULTIPLE))

                signals.append({
                    "ticker": ticker, "name": name, "sector": sector, "grade": grade,
                    "at_key_level": bool(last_row.get("At_Key_Level", False)),
                    "key_level": round(float(last_row.get("Key_Level", 0)), 2) if pd.notna(last_row.get("Key_Level")) else None,
                    "close": round(close_price, 2), "trigger_price": round(trigger_p, 2),
                    "stop_loss": round(stop_p, 2), "target_price": round(target_p, 2),
                    "risk_pct": round(risk_pct, 2), "net_rr": round(net_rr, 2),
                    "trust_net_lots": int(chip_info["trust_net"] / 1000),
                    "trust_5d_lots": int(chip_info["trust_5d"] / 1000),
                    "candles": candles, "ema": ema_series,
                })
                print(f"  ★ [正式買訊：H2突破＋投信買超] {ticker} {name} (等級: {grade}) | 掛單: {trigger_p}, 停損: {stop_p}")
            else:
                print(f"  [濾網排除] {ticker} {name} 雖符合 H2，但投信未買超 (已濾除假突破)")

        elif is_forming:
            forming.append({
                "ticker": ticker, "name": name, "sector": sector,
                "close": round(close_price, 2), "ema20": round(ema20, 2),
                "candles": candles, "ema": ema_series,
            })

        # Brooks MTR (Major Trend Reversal) 訊號
        is_mtr = bool(last_row.get("MTR_Detected", False)) and is_liquid and is_valid_price
        if is_mtr:
            mtr_dir = str(last_row.get("MTR_Direction", "NONE"))
            mtr_entry = float(last_row.get("MTR_Entry", close_price))
            mtr_stop = float(last_row.get("MTR_Stop", 0.0))
            mtr_target = float(last_row.get("MTR_Target", 0.0))
            mtr_risk_pct = round((abs(mtr_entry - mtr_stop) / mtr_entry) * 100, 2) if mtr_entry > 0 else 0.0
            mtr_confirmed = bool(last_row.get("MTR_Confirmed", False))
            mtr_signals.append({
                "ticker": ticker, "name": name, "sector": sector, "direction": mtr_dir,
                "confirmed": mtr_confirmed,
                "sig_date": scan_date,
                "at_key_level": bool(last_row.get("At_Key_Level", False)),
                "key_level": round(float(last_row.get("Key_Level", 0)), 2) if pd.notna(last_row.get("Key_Level")) else None,
                "close": round(close_price, 2),
                "entry_price": round(mtr_entry, 2), "stop_loss": round(mtr_stop, 2),
                "target_price": round(mtr_target, 2), "risk_pct": mtr_risk_pct,
                "candles": candles, "ema": ema_series,
            })
            print(f"  ★ [MTR 反轉訊號] {ticker} {name} ({mtr_dir}) | 入場: {mtr_entry}, 停損: {mtr_stop}, 目標: {mtr_target}")

        # Brooks Wedge (楔形) 訊號
        is_wedge = bool(last_row.get("Wedge_Detected", False)) and is_liquid and is_valid_price
        if is_wedge:
            w_type = str(last_row.get("Wedge_Type", "NONE"))
            w_entry = float(last_row.get("Wedge_Entry", close_price))
            w_stop = float(last_row.get("Wedge_Stop", 0.0))
            w_target = float(last_row.get("Wedge_Target", 0.0))
            w_risk_pct = round((abs(w_entry - w_stop) / w_entry) * 100, 2) if w_entry > 0 else 0.0
            wedge_signals.append({
                "ticker": ticker, "name": name, "sector": sector, "type": w_type,
                "sig_date": scan_date,
                "at_key_level": bool(last_row.get("At_Key_Level", False)),
                "key_level": round(float(last_row.get("Key_Level", 0)), 2) if pd.notna(last_row.get("Key_Level")) else None,
                "close": round(close_price, 2),
                "entry_price": round(w_entry, 2), "stop_loss": round(w_stop, 2),
                "target_price": round(w_target, 2), "risk_pct": w_risk_pct,
                "candles": candles, "ema": ema_series,
            })
            print(f"  ★ [Wedge 楔形訊號] {ticker} {name} ({w_type}) | 入場: {w_entry}, 停損: {w_stop}, 目標: {w_target}")

        # Brooks BOM (Buy/Sell the close) 強趨勢棒進場
        is_bom = bool(last_row.get("BOM_Detected", False)) and is_liquid and is_valid_price
        if is_bom and getattr(config, "BOM_EXCLUDE_CLIMAX", True) and bool(last_row.get("Climax_Detected", False)):
            is_bom = False
        if is_bom:
            bom_dir = str(last_row.get("BOM_Direction", "NONE"))
            bom_entry = float(last_row.get("BOM_Entry", close_price))
            bom_stop = float(last_row.get("BOM_Stop", 0.0))
            bom_target = float(last_row.get("BOM_Target", 0.0))
            bom_risk_pct = round((abs(bom_entry - bom_stop) / bom_entry) * 100, 2) if bom_entry > 0 else 0.0
            bom_signals.append({
                "ticker": ticker, "name": name, "sector": sector, "direction": bom_dir,
                "sig_date": scan_date,
                "at_key_level": bool(last_row.get("At_Key_Level", False)),
                "key_level": round(float(last_row.get("Key_Level", 0)), 2) if pd.notna(last_row.get("Key_Level")) else None,
                "close": round(close_price, 2),
                "entry_price": round(bom_entry, 2), "stop_loss": round(bom_stop, 2),
                "target_price": round(bom_target, 2), "risk_pct": bom_risk_pct,
                "candles": candles, "ema": ema_series,
            })
            print(f"  ★ [BOM 強趨勢棒] {ticker} {name} ({bom_dir}) | 入場: {bom_entry}, 停損: {bom_stop}, 目標: {bom_target}")

        # Brooks Climax (高潮/耗盡) 訊號
        is_climax = bool(last_row.get("Climax_Detected", False)) and is_liquid and is_valid_price
        if is_climax:
            clim_dir = str(last_row.get("Climax_Direction", "NONE"))
            # climax detail metrics
            clim_high = float(latest_bar["High"])
            clim_low = float(latest_bar["Low"])
            clim_range = round(clim_high - clim_low, 2)
            clim_atr = float(last_row.get("ATR", 0.0)) if pd.notna(last_row.get("ATR")) else 0.0
            clim_atr_mult = round(clim_range / clim_atr, 2) if clim_atr > 0 else 0.0
            # prior trend bars (consecutive same Always_In before this bar)
            prior_trend = 0
            ai_series = analyzed_df["Always_In"].astype(str).tolist()
            for k in range(len(ai_series) - 2, -1, -1):
                if ai_series[k] == ai_series[-1]:
                    prior_trend += 1
                else:
                    break
            climax_signals.append({
                "ticker": ticker, "name": name, "sector": sector, "direction": clim_dir,
                "sig_date": scan_date,
                "at_key_level": bool(last_row.get("At_Key_Level", False)),
                "key_level": round(float(last_row.get("Key_Level", 0)), 2) if pd.notna(last_row.get("Key_Level")) else None,
                "close": round(close_price, 2),
                "climax_range": clim_range,
                "climax_atr": round(clim_atr, 2),
                "climax_atr_mult": clim_atr_mult,
                "prior_trend_bars": prior_trend,
                "candles": candles, "ema": ema_series,
            })
            print(f"  ★ [Climax 高潮棒] {ticker} {name} ({clim_dir})")

    # 5. 評估現有持倉 (呼叫更新後的 portfolio_tracker)
    holdings_raw = load_holdings()
    for h in holdings_raw:
        ht = h.get("ticker")
        if ht and ht not in current_prices:
            try:
                hdf = fetch_history(ht, lookback_days=5)
                if not hdf.empty:
                    current_prices[ht] = float(hdf.iloc[-1]["Close"])
            except Exception:
                pass

    holdings_status = evaluate_holdings(current_prices, dfs)

    # 6. 組裝與輸出 scan_result.json
    signals.sort(key=lambda x: (0 if x["grade"] == "A" else 1, x["trigger_price"]))
    output_payload = {
        "scan_date": scan_date,
        "scan_time": scan_time,
        "realtime": getattr(config, "USE_REALTIME_PRICE", False),
        "market_status": market_status,
        "signals": signals,
        "mtr_signals": mtr_signals,
        "wedge_signals": wedge_signals,
        "bom_signals": bom_signals,
        "climax_signals": climax_signals,
        "forming": forming,
        "holdings_status": holdings_status,
        "universe": universe_list,
    }

    clean_payload = sanitize_for_json(output_payload)
    os.makedirs("public", exist_ok=True)
    with open(os.path.join("public", "scan_result.json"), "w", encoding="utf-8") as f:
        json.dump(clean_payload, f, ensure_ascii=False, indent=2)
    with open("scan_result.json", "w", encoding="utf-8") as f:
        json.dump(clean_payload, f, ensure_ascii=False, indent=2)

    print()
    print("=" * 50)
    print(f"【掃描摘要】時間: {scan_date} {scan_time}")
    print(f"買進訊號 (H2+投信): {len(signals)} 檔 | MTR 反轉: {len(mtr_signals)} 檔 | Wedge: {len(wedge_signals)} 檔 | BOM: {len(bom_signals)} 檔 | Climax: {len(climax_signals)} 檔 | 追蹤持倉: {len(holdings_status)} 檔")
    print(f"輸出成功: public/scan_result.json")
    print("=" * 50)


if __name__ == "__main__":
    run_scanner()
