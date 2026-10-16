"""
data_fetcher.py
統一資料取得模組 (FinMind API 完整版)
支援個股歷史 K 線、大盤加權指數 (TAIEX) 狀態判定、三大法人買賣超籌碼
"""

import os
import time
import requests
import pandas as pd
from datetime import datetime, timedelta

FINMIND_API_URL = "https://api.finmindtrade.com/api/v4/data"

def clean_ticker(ticker: str) -> str:
    """去除 .TW、.TWO 等後綴，轉為純代碼 (例如 2330.TW -> 2330)"""
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

def get_market_status(lookback_days: int = 120) -> dict:
    """
    評估大盤加權指數 (TAIEX) 狀態與 20EMA
    回傳字典: {bullish: bool, close: float, ema20: float, market_phase: str}
    供 scanner.py 與前端儀表板顯示
    """
    df = fetch_history("TAIEX", lookback_days=lookback_days)
    
    # 若 TAIEX 暫時無資料，改用台灣 50 (0050) 替代判定
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
    """
    批次抓取標的歷史日 K
    """
    results = {}
    for t in tickers:
        df = fetch_history(t, lookback_days=lookback_days)
        if not df.empty:
            results[t] = df
        if delay_sec > 0:
            time.sleep(delay_sec)
    return results

def fetch_institutional_chips(ticker: str, days: int = 15) -> dict:
    """
    取得三大法人籌碼 (專案任務 G 投信買超濾網 C 專用)
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

        trust_df = df[df["name"].str.contains("Investment_Trust|投信", case=False, na=False)].copy()
        if not trust_df.empty:
            trust_df = trust_df.sort_values("date").reset_index(drop=True)
            today_net = int(trust_df.iloc[-1]["net"] // 1000)
            net_5d = int(trust_df.tail(5)["net"].sum() // 1000)

            result["trust_net_today"] = today_net
            result["trust_net_5d"] = net_5d
            result["pass_trust_filter"] = bool(today_net > 0 or net_5d > 0)
            result["detail"] = trust_df[["date", "buy", "sell", "net"]].to_dict(orient="records")

    except Exception as e:
        print(f"[{ticker}] 抓取投信籌碼失敗: {e}")

    return result

def get_latest_quote(ticker: str) -> dict:
    """
    抓取最新單日報價
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
