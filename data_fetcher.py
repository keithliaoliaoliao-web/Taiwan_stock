"""
data_fetcher.py
統一資料取得模組 (FinMind API 完整相容版)
完全相容 scanner.py / portfolio_tracker.py 既有函式簽名與參數型別
"""

import os
import time
import requests
import pandas as pd
from datetime import datetime, timedelta

FINMIND_API_URL = "https://api.finmindtrade.com/api/v4/data"

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
                time.sleep(1.0 * (attempt + 1))
        except Exception:
            time.sleep(0.5 * (attempt + 1))
    return []

def fetch_history(ticker: str, lookback_days: int = 300) -> pd.DataFrame:
    """
    從 FinMind 取得歷史日 K 線並轉為 PriceActionEngine 標準 DataFrame
    標準欄位: Date, Open, High, Low, Close, Volume
    """
    stock_id = clean_ticker(ticker)
    
    # 型別防呆：若傳入 str，安全轉為 int
    try:
        days = int(lookback_days)
    except (ValueError, TypeError):
        days = 300

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
        return df

    except Exception as e:
        print(f"[{ticker}] 轉換日K線資料失敗: {e}")
        return pd.DataFrame()

def get_market_status(ticker: str = "^TWII", lookback_days: int = 120) -> dict:
    """
    評估大盤加權指數狀態與 20EMA
    參數支援 get_market_status(ticker) 或 get_market_status(lookback_days)
    """
    # 參數型別自動識別相容
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
    
    # 若 TAIEX 暫時無資料，改用 0050 替代判定
    if df.empty or len(df) < 25:
        df = fetch_history("0050", lookback_days=lookback_days)

    if df.empty or len(df) < 20:
        return {
            "bullish": True,
            "close": 0.0,
            "ema20": 0.0,
            "market_phase": "盤後定盤"
        }

    # 計算大盤 20EMA
    df["EMA_20"] = df["Close"].ewm(span=20, adjust=False).mean()
    last_row = df.iloc[-1]
    close_val = round(float(last_row["Close"]), 2)
    ema20_val = round(float(last_row["EMA_20"]), 2)
    is_bullish = bool(close_val >= ema20_val)

    now = datetime.now()
    # 台灣時間 13:45 之後視為收盤定盤
    phase = "盤後定盤" if (now.hour > 13 or (now.hour == 13 and now.minute >= 45)) else "盤中即時"

    return {
        "bullish": is_bullish,
        "close": close_val,
        "ema20": ema20_val,
        "market_phase": phase
    }

def fetch_batch_history(tickers: list, lookback_days: int = 300, delay_sec: float = 0.05) -> dict:
    """批次抓取標的歷史日 K"""
    results = {}
    for t in tickers:
        df = fetch_history(t, lookback_days=lookback_days)
        if not df.empty:
            results[t] = df
        if delay_sec > 0:
            time.sleep(delay_sec)
    return results

def fetch_institutional_investors(ticker: str, days: int = 15) -> dict:
    """
    相容原 scanner.py 函式命名：取得三大法人籌碼 (投信買超濾網 C)
    """
    stock_id = clean_ticker(ticker)
    
    try:
        days = int(days)
    except (ValueError, TypeError):
        days = 15

    end_date = datetime.now
