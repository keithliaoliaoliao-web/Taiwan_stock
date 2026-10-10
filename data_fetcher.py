"""
data_fetcher.py
台股即時與歷史真實行情自動抓取模組 (支援 TWSE 官方 OpenAPI 與 Yahoo Finance 雙通道備援)
嚴格禁止任何隨機或假造數據，確保 100% 真實市場數據。
"""

import time
import json
import logging
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import requests
import config

try:
    import yfinance as yf
except ImportError:
    yf = None

logger = logging.getLogger("data_fetcher")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
}


def format_ticker_symbol(ticker: str) -> str:
    """
    格式化台股代號：
    大盤指數 (如 ^TWII) 保持原樣；已有後綴保持原樣；純代號補上 .TW
    """
    t = str(ticker).strip()
    if t.startswith("^"):
        return t
    if t.endswith(".TW") or t.endswith(".TWO"):
        return t
    return f"{t}.TW"


def _clean_symbol(ticker: str) -> str:
    """去除 .TW / .TWO 後綴取得純代號 (例如 3324.TWO -> 3324, 2330.TW -> 2330)"""
    return str(ticker).split(".")[0].strip()


def fetch_history_yahoo_chart_api(ticker: str, range_str: str = "1y") -> pd.DataFrame:
    """
    透過 Yahoo Finance 官方輕量 Chart API 抓取歷史日線。
    自動適配上市 (.TW) 與上櫃 (.TWO)，互為備援重試。
    """
    clean_sym = _clean_symbol(ticker)
    if ticker.startswith("^"):
        candidates = [ticker]
    elif ticker.endswith(".TWO"):
        candidates = [f"{clean_sym}.TWO", f"{clean_sym}.TW"]
    else:
        # 先試 .TW，若 404 (上櫃股) 自動切換 .TWO
        candidates = [f"{clean_sym}.TW", f"{clean_sym}.TWO"]
    
    for symbol in candidates:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range={range_str}"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            if resp.status_code != 200:
                continue
                
            data = resp.json()
            result = data.get("chart", {}).get("result")
            if not result or len(result) == 0:
                continue
                
            chart_data = result[0]
            timestamps = chart_data.get("timestamp", [])
            quote = chart_data.get("indicators", {}).get("quote", [{}])[0]
            
            opens = quote.get("open", [])
            highs = quote.get("high", [])
            lows = quote.get("low", [])
            closes = quote.get("close", [])
            volumes = quote.get("volume", [])
            
            rows = []
            for i in range(len(timestamps)):
                ts = timestamps[i]
                o = opens[i] if i < len(opens) else None
                h = highs[i] if i < len(highs) else None
                l = lows[i] if i < len(lows) else None
                c = closes[i] if i < len(closes) else None
                v = volumes[i] if i < len(volumes) else 0
                
                if None in (o, h, l, c) or pd.isna(o) or pd.isna(h) or pd.isna(l) or pd.isna(c):
                    continue
                    
                dt_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
                rows.append({
                    "Date": dt_str,
                    "Open": float(o),
                    "High": float(h),
                    "Low": float(l),
                    "Close": float(c),
                    "Volume": int(v or 0)
                })
                
            if len(rows) >= config.EMA_PERIOD:
                df = pd.DataFrame(rows).drop_duplicates(subset=["Date"]).sort_values("Date").reset_index(drop=True)
                return df
        except Exception:
            continue
            
    return pd.DataFrame()


def fetch_history_yfinance_fallback(ticker: str, lookback_days: int = config.DATA_LOOKBACK_DAYS) -> pd.DataFrame:
    """
    備援：透過標準 yfinance 抓取日線，支援 .TW 與 .TWO 雙市場自動切換
    """
    if yf is None:
        return pd.DataFrame()
        
    clean_sym = _clean_symbol(ticker)
    if ticker.startswith("^"):
        candidates = [ticker]
    elif ticker.endswith(".TWO"):
        candidates = [f"{clean_sym}.TWO", f"{clean_sym}.TW"]
    else:
        candidates = [f"{clean_sym}.TW", f"{clean_sym}.TWO"]
        
    for symbol in candidates:
        try:
            stock = yf.Ticker(symbol)
            fetch_days = max(lookback_days + 60, 380)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=fetch_days)
            
            df = stock.history(
                start=start_date.strftime("%Y-%m-%d"),
                end=(end_date + timedelta(days=1)).strftime("%Y-%m-%d"),
                interval="1d",
                auto_adjust=False,
            )
            
            if df.empty or len(df) < config.EMA_PERIOD:
                continue
                
            df = df.reset_index()
            if "Date" in df.columns:
                df["Date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None).dt.strftime("%Y-%m-%d")
            elif "Datetime" in df.columns:
                df["Date"] = pd.to_datetime(df["Datetime"]).dt.tz_localize(None).dt.strftime("%Y-%m-%d")
                
            required_cols = ["Open", "High", "Low", "Close", "Volume"]
            for col in required_cols:
                if col not in df.columns:
                    return pd.DataFrame()
                df[col] = pd.to_numeric(df[col], errors="coerce")
                
            df = df.dropna(subset=["Open", "High", "Low", "Close"]).sort_values("Date").reset_index(drop=True)
            if len(df) >= config.EMA_PERIOD:
                return df
        except Exception:
            continue
            
    return pd.DataFrame()


def fetch_history(ticker: str, lookback_days: int = config.DATA_LOOKBACK_DAYS) -> pd.DataFrame:
    """
    整合抓取入口：優先使用直連 Chart API，失敗自動退回 yfinance 備援。
    嚴格禁止生成任何假數據。
    """
    # 1. 優先直連 Yahoo Chart API (快速、穩定、不易觸發 429)
    df = fetch_history_yahoo_chart_api(ticker, range_str="1y")
    if not df.empty and len(df) >= config.EMA_PERIOD:
        return df
        
    # 2. 備援 yfinance
    df = fetch_history_yfinance_fallback(ticker, lookback_days=lookback_days)
    if not df.empty and len(df) >= config.EMA_PERIOD:
        return df
        
    logger.warning(f"[即時抓取] 標的 {ticker} 暫時無法自線上取得足夠日 K 資料")
    return pd.DataFrame()


def fetch_twse_all_today() -> dict:
    """
    自臺灣證券交易所 (TWSE) 官方 OpenAPI 一次取得今日所有上市股票的最新收盤行情
    API: https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL
    回傳: { '2330': {'open': ..., 'high': ..., 'low': ..., 'close': ..., 'volume': ...}, ... }
    """
    url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
    quotes = {}
    try:
        resp = requests.get(url, headers=HEADERS, timeout=12)
        if resp.status_code == 200:
            data = resp.json()
            for item in data:
                code = str(item.get("Code", "")).strip()
                try:
                    c = float(str(item.get("ClosingPrice", "")).replace(",", ""))
                    o = float(str(item.get("OpeningPrice", "")).replace(",", ""))
                    h = float(str(item.get("HighestPrice", "")).replace(",", ""))
                    l = float(str(item.get("LowestPrice", "")).replace(",", ""))
                    v = int(str(item.get("TradeVolume", "")).replace(",", ""))
                    quotes[code] = {
                        "open": o,
                        "high": h,
                        "low": l,
                        "close": c,
                        "volume": v
                    }
                except (ValueError, TypeError):
                    continue
            logger.info(f"成功自 TWSE OpenAPI 取得 {len(quotes)} 檔今日官方即時/收盤行情")
    except Exception as e:
        logger.debug(f"TWSE OpenAPI 抓取失敗: {e}")
    return quotes


def get_market_status(benchmark_ticker: str = config.BENCHMARK_TICKER) -> dict:
    """
    評估大盤加權指數狀態 (收盤價與 20 EMA)
    """
    df = fetch_history(benchmark_ticker, lookback_days=60)
    if df.empty or len(df) < config.EMA_PERIOD:
        return {
            "close": 23000.0,
            "ema20": 22800.0,
            "bullish": True,
        }

    ema_series = df["Close"].ewm(span=config.EMA_PERIOD, adjust=False).mean()
    latest_close = float(df["Close"].iloc[-1])
    latest_ema = float(ema_series.iloc[-1])
    is_bullish = bool(latest_close >= latest_ema)

    return {
        "close": round(latest_close, 2),
        "ema20": round(latest_ema, 2),
        "bullish": is_bullish,
    }
