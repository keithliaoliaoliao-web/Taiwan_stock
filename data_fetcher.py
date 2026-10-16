"""
data_fetcher.py
統一資料取得模組 (FinMind API 專用版)
提供日 K 線行情 (TaiwanStockPrice) 與三大法人買賣超 (TaiwanStockInstitutionalInvestorsBuySell) 擷取
"""

import os
import time
import requests
import pandas as pd
from datetime import datetime, timedelta

FINMIND_API_URL = "https://api.finmindtrade.com/api/v4/data"

def clean_ticker(ticker: str) -> str:
    """去除 .TW、.TWO 等後綴，轉為 FinMind 所需之純代碼 (例如 2330.TW -> 2330)"""
    return str(ticker).split(".")[0].strip()

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
    從 FinMind 取得單一標的歷史日 K 線並轉為 PriceActionEngine 標準 DataFrame
    欄位需求: Date, Open, High, Low, Close, Volume
    """
    stock_id = clean_ticker(ticker)
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")

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
        
        # 欄位對齊系統標準名稱
        rename_map = {
            "date": "Date",
            "open": "Open",
            "max": "High",
            "min": "Low",
            "close": "Close",
            "Trading_Volume": "Volume"
        }
        df = df.rename(columns=rename_map)

        # 數值型別轉換與清理
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

def fetch_batch_history(tickers: list, lookback_days: int = 300, delay_sec: float = 0.05) -> dict:
    """
    批次抓取觀察池歷史日 K
    回傳字典: {ticker: pd.DataFrame}
    """
    results = {}
    total = len(tickers)
    for idx, t in enumerate(tickers, start=1):
        df = fetch_history(t, lookback_days=lookback_days)
        if not df.empty:
            results[t] = df
        if delay_sec > 0:
            time.sleep(delay_sec)
    return results

def fetch_institutional_chips(ticker: str, days: int = 15) -> dict:
    """
    取得標的三大法人籌碼 (專案任務 G 投信買超濾網 C 專用)
    回傳當日淨買超、5日累計買超與濾網是否合格
    """
    stock_id = clean_ticker(ticker)
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    params = {
        "dataset": "TaiwanStockInstitutionalInvestorsBuySell",
        "data_id": stock_id,
        "start_date": start_date,
        "end_date": end_date
    }

    result = {
        "trust_net_today": 0,
        "trust_net_5d": 0,
        "pass_trust_filter": False,
        "detail": []
    }

    raw_data = _request_finmind(params)
    if not raw_data:
        return result

    try:
        df = pd.DataFrame(raw_data)
        if df.empty:
            return result

        df["net"] = df["buy"] - df["sell"]

        # 篩選投信 (Investment Trust)
        trust_df = df[df["name"].str.contains("Investment_Trust|投信", case=False, na=False)].copy()
        if not trust_df.empty:
            trust_df = trust_df.sort_values("date").reset_index(drop=True)
            
            # 轉換為張數 (股數 / 1000)
            today_net = int(trust_df.iloc[-1]["net"] // 1000)
            net_5d = int(trust_df.tail(5)["net"].sum() // 1000)

            result["trust_net_today"] = today_net
            result["trust_net_5d"] = net_5d
            # 任務 G 濾網 C: 當日淨買超 > 0 或 5日累計淨買超 > 0
            result["pass_trust_filter"] = bool(today_net > 0 or net_5d > 0)
            result["detail"] = trust_df[["date", "buy", "sell", "net"]].to_dict(orient="records")

    except Exception as e:
        print(f"[{ticker}] 抓取投信籌碼失敗: {e}")

    return result

def get_latest_quote(ticker: str) -> dict:
    """
    抓取標的最新單日行情
    """
    df = fetch_history(ticker, lookback_days=10)
    if df.empty:
        return {}
    
    last = df.iloc[-1]
    return {
        "ticker": ticker,
        "date": last["Date"].strftime("%Y-%m-%d"),
        "open": float(last["Open"]),
        "high": float(last["High"]),
        "low": float(last["Low"]),
        "close": float(last["Close"]),
        "volume": float(last["Volume"])
    }
