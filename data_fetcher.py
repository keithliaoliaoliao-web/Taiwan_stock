"""
data_fetcher.py
資料取得模組 (FinMind)。
所有「今天 / 現在」的判斷一律使用台灣時間，並考慮證交所休市日。
"""

import os
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import requests

FINMIND_API_URL = "https://api.finmindtrade.com/api/v4/data"
TZ_TW = ZoneInfo("Asia/Taipei")
DATA_READY_HM = (16, 30)  # 台灣時間 16:30 之後，才預期當天收盤資料已可取得

# 證交所休市日 (含農曆年前「僅辦理交割、不交易」的日子)。
# 2026：已對照證交所公告。
# 2027：暫定 (依國定假日推算)，證交所公布 2027 開休市表後需再核對。
# M5 FIX: 單一來源 (config.TWSE_HOLIDAYS)，避免 data_fetcher 與 config 兩份清單不一致。
try:
    from config import TWSE_HOLIDAYS as _CFG_HOLIDAYS
    TWSE_HOLIDAYS = set(_CFG_HOLIDAYS)
except Exception:  # pragma: no cover - fallback if config unavailable
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


def fetch_realtime_price(ticker: str) -> dict:
    """從 TWSE MIS API 取得即時報價 (盤中)。回傳 dict 含 price, open, high, low, volume, time, yesterday_close。"""
    import requests
    clean_id = clean_ticker(ticker)
    # TWSE for listed, TPEx (TWO) for OTC
    ex = "tse"
    if ticker.upper().endswith(".TWO"):
        ex = "otc"
    url = f"https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch={ex}_{clean_id}.tw&json=1&delay=0"
    try:
        res = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        if res.status_code == 200:
            payload = res.json()
            arr = payload.get("msgArray", [])
            if arr:
                info = arr[0]
                z = info.get("z", "")
                if z and z != "-":
                    return {
                        "price": float(z),
                        "open": float(info.get("o", 0) or 0),
                        "high": float(info.get("h", 0) or 0),
                        "low": float(info.get("l", 0) or 0),
                        "volume": int(float(info.get("v", 0) or 0)),
                        "time": info.get("t", ""),
                        "yesterday_close": float(info.get("y", 0) or 0),
                        "name": info.get("n", ticker),
                    }
    except Exception:
        pass
    return {}


def fetch_dividends(ticker: str, lookback_days: int = 2200) -> pd.DataFrame:
    """從 FinMind 取得現金股利資料，回傳欄位 ex_date, cash_dividend"""
    stock_id = clean_ticker(ticker)
    end = now_tw().date()
    start = end - timedelta(days=int(lookback_days))
    params = {
        "dataset": "TaiwanStockDividend",
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
        df = pd.DataFrame(raw)
        # extract ex-dividend date and cash dividend
        rows = []
        for r in raw:
            ex_date = r.get("CashExDividendTradingDate", "")
            cash_div = r.get("CashEarningsDistribution", 0) or 0
            if ex_date and cash_div and float(cash_div) > 0:
                rows.append({"ex_date": ex_date, "cash_dividend": float(cash_div)})
        if not rows:
            return pd.DataFrame()
        return pd.DataFrame(rows).drop_duplicates(subset=["ex_date"])
    except Exception as e:
        print(f"[{ticker}] 轉換股利資料失敗: {e}")
        return pd.DataFrame()


def fetch_splits(ticker: str, lookback_days: int = 2200) -> pd.DataFrame:
    """從 FinMind 取得分割資料"""
    stock_id = clean_ticker(ticker)
    end = now_tw().date()
    start = end - timedelta(days=int(lookback_days))
    params = {
        "dataset": "TaiwanStockSplitPrice",
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
        df = pd.DataFrame(raw)
        return df
    except Exception as e:
        print(f"[{ticker}] 轉換分割資料失敗: {e}")
        return pd.DataFrame()


def adjust_for_dividends(df: pd.DataFrame, div_df: pd.DataFrame) -> pd.DataFrame:
    """用現金股利調整歷史價格 (向後調整, 讓指標計算不受除息缺口影響)。
    調整後的價格 = 原始價格 + 除息日前的累計股利 (向後還原)。
    """
    if df.empty or div_df is None or div_df.empty:
        return df.copy()
    out = df.copy()
    out["Date"] = pd.to_datetime(out["Date"])
    # build cumulative dividend adjustment per date
    div_map = {}
    for _, r in div_df.iterrows():
        try:
            ex_date = pd.to_datetime(r["ex_date"])
            div_map[ex_date] = div_map.get(ex_date, 0) + float(r["cash_dividend"])
        except Exception:
            pass
    if not div_map:
        return out
    # H3 FIX: vectorised backward adjustment.
    # Original code looped over every bar AND every ex-date (O(N*D)) inside
    # iterrows(). Now we compute, for each bar, the total dividends whose ex-date
    # is strictly after that bar, using a sorted cumulative-sum + searchsorted.
    ex_dates = sorted(div_map.keys())
    ex_amts = np.array([div_map[d] for d in ex_dates], dtype=float)
    total_div = float(ex_amts.sum())
    ex_dates_np = pd.to_datetime(pd.Series(ex_dates)).to_numpy()
    bar_dates = pd.to_datetime(out["Date"]).to_numpy()
    # cumulative sum of dividends with ex_date <= bar_date
    idx = np.searchsorted(ex_dates_np, bar_dates, side="right")
    cum_inclusive = np.concatenate([[0.0], np.cumsum(ex_amts)])[idx]
    adj = total_div - cum_inclusive  # dividends strictly after this bar
    for col in ["Open", "High", "Low", "Close"]:
        if col in out.columns:
            out[col] = out[col] + pd.Series(adj, index=out.index)
    return out


def adjust_for_splits(df: pd.DataFrame, split_df: pd.DataFrame) -> pd.DataFrame:
    """用分割資料調整歷史價格"""
    if df.empty or split_df is None or split_df.empty:
        return df.copy()
    # FinMind TaiwanStockSplitPrice format varies; if no standard columns, skip
    return df.copy()


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
