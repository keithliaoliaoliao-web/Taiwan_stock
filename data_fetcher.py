"""
data_fetcher.py
統一資料取得模組 (FinMind API 完整相容版 + 具備 12 小時時效與日期檢核之本地快取)
"""

import os
import shutil
import time
import requests
import pandas as pd
from datetime import datetime, timedelta

FINMIND_API_URL = "https://api.finmindtrade.com/api/v4/data"
CACHE_DIR = ".cache_ohlcv"


def clear_cache():
    """清除本地快取資料夾 (.cache_ohlcv)，供即時執行流程在啟動時呼叫"""
    if os.path.exists(CACHE_DIR):
        shutil.rmtree(CACHE_DIR, ignore_errors=True)


def get_expected_latest_trading_date(now_dt: datetime = None) -> str:
    """推算預期最新交易日 (扣除週末；若當日早於 16:30 則預期為前一交易日)"""
    if now_dt is None:
        now_dt = datetime.now()
    dt = now_dt
    if dt.weekday() < 5 and (dt.hour < 16 or (dt.hour == 16 and dt.minute < 30)):
        dt = dt - timedelta(days=1)
    while dt.weekday() >= 5:
        dt = dt - timedelta(days=1)
    return dt.strftime("%Y-%m-%d")


def clean_ticker(ticker: str) -> str:
    """去除 .TW、.TWO、^TWII 等後綴，轉為 FinMind 所需代碼"""
    t = str(ticker).strip()
    if t.upper() in ["^TWII", "0000", "TAIEX"]:
        return "TAIEX"
    return t.split(".")[0].strip()


def _request_finmind(params: dict, max_retries: int = 3, timeout: int = 10) -> list:
    """發送請求至 FinMind API 並處理基礎容錯重試"""
    headers = {"User-Agent": "Mozilla/5.0"}
    for attempt in range(max_retries):
        try:
            res = requests.get(FINMIND_API_URL, params=params, headers=headers, timeout=timeout)
            if res.status_code == 200:
                payload = res.json()
                if payload.get("status") == 200 or "data" in payload:
                    return payload.get("data", [])
            elif res.status_code == 429:
                time.sleep(1.5 * (attempt + 1))
        except Exception:
            time.sleep(0.5 * (attempt + 1))
    return []


def fetch_history(ticker: str, lookback_days: int = 300, use_cache: bool = True) -> pd.DataFrame:
    """
    從 FinMind 取得歷史日 K 線並轉為標準 DataFrame
    快取規則：僅在快取檔建立時間 <= 12 小時內，或最後一根日 K 日期 >= 預期最新交易日時才使用快取
    """
    stock_id = clean_ticker(ticker)
    try:
        days = int(lookback_days)
    except (ValueError, TypeError):
        days = 300

    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_file = os.path.join(CACHE_DIR, f"{stock_id}_{days}.csv")

    if use_cache and os.path.exists(cache_file):
        try:
            mtime = os.path.getmtime(cache_file)
            age_hours = (time.time() - mtime) / 3600.0
            df_c = pd.read_csv(cache_file)
            if not df_c.empty and "Date" in df_c.columns:
                last_bar_date = str(df_c["Date"].iloc[-1])[:10]
                expected_date = get_expected_latest_trading_date()
                if age_hours <= 12.0 or last_bar_date >= expected_date:
                    df_c["Date"] = pd.to_datetime(df_c["Date"])
                    return df_c
        except Exception:
            pass

    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    params = {
        "dataset": "TaiwanStockPrice",
        "data_id": stock_id,
        "start_date": start_date,
        "end_date": end_date
    }

    raw_data = _request_finmind(params)
    if not raw_data:
        return pd.DataFrame()

    try:
        df = pd.DataFrame(raw_data)
        rename_map = {
            "date": "Date",
            "open": "Open",
            "max": "High",
            "min": "Low",
            "close": "Close",
            "Trading_Volume": "Volume"
        }
        df = df.rename(columns=rename_map)

        df["Date"] = pd.to_datetime(df["Date"])
        num_cols = ["Open", "High", "Low", "Close", "Volume"]
        for col in num_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        df = df.dropna(subset=["Close", "Open", "High", "Low"])
        df = df.sort_values("Date").reset_index(drop=True)

        if not df.empty:
            df.to_csv(cache_file, index=False)

        return df

    except Exception as e:
        print(f"[{ticker}] 轉換日K線資料失敗: {e}")
        return pd.DataFrame()


def get_market_status(ticker: str = "^TWII", lookback_days: int = 120) -> dict:
    if isinstance(ticker, int):
        lookback_days = ticker
        target_ticker = "TAIEX"
    else:
        target_ticker = clean_ticker(ticker)
        try:
            lookback_days = int(lookback_days)
        except (ValueError, TypeError):
            lookback_days = 120

    df = fetch_history(target_ticker, lookback_days=lookback_days)
    if df.empty or len(df) < 25:
        df = fetch_history("0050", lookback_days=lookback_days)

    if df.empty or len(df) < 20:
        return {
            "bullish": True,
            "close": 0.0,
            "ema20": 0.0,
            "market_phase": "盤後定盤"
        }

    df["EMA_20"] = df["Close"].ewm(span=20, adjust=False).mean()
    last_row = df.iloc[-1]
    close_val = round(float(last_row["Close"]), 2)
    ema20_val = round(float(last_row["EMA_20"]), 2)
    is_bullish = bool(close_val >= ema20_val)

    now = datetime.now()
    phase = "盤後定盤" if (now.hour > 13 or (now.hour == 13 and now.minute >= 45)) else "盤中即時"

    return {
        "bullish": is_bullish,
        "close": close_val,
        "ema20": ema20_val,
        "market_phase": phase
    }


def fetch_batch_history(tickers: list, lookback_days: int = 300, delay_sec: float = 0.05) -> dict:
    results = {}
    for t in tickers:
        df = fetch_history(t, lookback_days=lookback_days)
        if not df.empty:
            results[t] = df
        if delay_sec > 0:
            time.sleep(delay_sec)
    return results


def fetch_institutional_investors(ticker: str, days: int = 15) -> dict:
    return {"investment_trust_net_buy": 0}
