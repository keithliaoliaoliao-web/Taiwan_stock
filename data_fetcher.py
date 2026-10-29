"""
data_fetcher.py
資料取得模組 (FinMind)。
所有「今天 / 現在」的判斷一律使用台灣時間，並考慮證交所休市日。
"""

import os
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import requests

FINMIND_API_URL = "https://api.finmindtrade.com/api/v4/data"
TZ_TW = ZoneInfo("Asia/Taipei")
DATA_READY_HM = (16, 30)  # 台灣時間 16:30 之後，才預期當天收盤資料已可取得

# 證交所休市日 (含農曆年前「僅辦理交割、不交易」的日子)。
# 2026：已對照證交所公告。
# 2027：暫定 (依國定假日推算)，證交所公布 2027 開休市表後需再核對。
TWSE_HOLIDAYS = {
    "2026-01-01", "2026-02-12", "2026-02-13", "2026-02-16", "2026-02-17",
    "2026-02-18", "2026-02-19", "2026-02-20", "2026-02-27", "2026-04-03",
    "2026-04-06", "2026-05-01", "2026-06-19", "2026-09-25", "2026-09-28",
    "2026-10-09", "2026-10-26", "2026-12-25",
    "2027-01-01", "2027-02-04", "2027-02-05", "2027-02-08", "2027-02-09",
    "2027-02-10", "2027-03-01", "2027-04-05", "2027-04-06", "2027-04-30",
    "2027-06-09", "2027-09-15", "2027-09-28", "2027-10-11", "2027-10-25",
    "2027-12-24", "2027-12-31",
}


def now_tw() -> datetime:
    return datetime.now(TZ_TW)


def is_trading_day(d) -> bool:
    """d 可為 date 或 datetime；週末與休市日回傳 False"""
    if hasattr(d, "date"):
        d = d.date()
    return d.weekday() < 5 and d.strftime("%Y-%m-%d") not in TWSE_HOLIDAYS


def get_expected_latest_trading_date(now_dt: datetime = None) -> str:
    """
    推算「此刻應該已經有資料」的最新交易日 (台灣時間)：
    交易日且已過 16:30 → 今天；否則 → 往前找最近一個交易日。
    """
    if now_dt is None:
        now_dt = now_tw()
    if now_dt.tzinfo is not None:
        now_dt = now_dt.astimezone(TZ_TW)
    d = now_dt.date()
    ready = (now_dt.hour, now_dt.minute) >= DATA_READY_HM
    if not (is_trading_day(d) and ready):
        d -= timedelta(days=1)
    while not is_trading_day(d):
        d -= timedelta(days=1)
    return d.strftime("%Y-%m-%d")


def clean_ticker(ticker: str) -> str:
    """去除 .TW / .TWO 後綴，轉為 FinMind 所需代碼"""
    return str(ticker).strip().split(".")[0].strip()


def _request_finmind(params: dict, max_retries: int = 3, timeout: int = 15) -> list:
    headers = {"User-Agent": "Mozilla/5.0"}
    for attempt in range(max_retries):
        try:
            res = requests.get(FINMIND_API_URL, params=params, headers=headers, timeout=timeout)
            if res.status_code == 200:
                payload = res.json()
                if payload.get("status") == 200:
                    return payload.get("data", [])
            time.sleep(1.5 * (attempt + 1))  # 429 / 額度用完 / 其他錯誤：等一下再試
        except Exception:
            time.sleep(0.5 * (attempt + 1))
    return []


def fetch_history(ticker: str, lookback_days: int = 500) -> pd.DataFrame:
    """從 FinMind 取得日 K (未還原)，回傳欄位 Date/Open/High/Low/Close/Volume (+ Trading_money)"""
    stock_id = clean_ticker(ticker)
    end = now_tw().date()
    start = end - timedelta(days=int(lookback_days))
    params = {
        "dataset": "TaiwanStockPrice",
        "data_id": stock_id,
        "start_date": start.strftime("%Y-%m-%d"),
        "end_date": end.strftime("%Y-%m-%d"),
    }
    token = os.environ.get("FINMIND_TOKEN", "").strip()
    if token:
        params["token"] = token

    raw = _request_finmind(params)
    if not raw:
        return pd.DataFrame()

    try:
        df = pd.DataFrame(raw).rename(columns={
            "date": "Date", "open": "Open", "max": "High",
            "min": "Low", "close": "Close", "Trading_Volume": "Volume",
        })
        df["Date"] = pd.to_datetime(df["Date"])
        for col in ["Open", "High", "Low", "Close", "Volume", "Trading_money"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df.dropna(subset=["Close", "Open", "High", "Low"])
        return df.sort_values("Date").reset_index(drop=True)
    except Exception as e:
        print(f"[{ticker}] 轉換日K線資料失敗: {e}")
        return pd.DataFrame()
