"""
data_fetcher.py
自 Yahoo Finance 取得台股標的與大盤指數的日線歷史資料
"""

from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf
import config


def fetch_history(ticker: str, lookback_days: int = config.DATA_LOOKBACK_DAYS) -> pd.DataFrame:
    """
    抓取指定標的日線資料，回傳標準 OHLCV DataFrame
    """
    try:
        fetch_days = max(lookback_days + 60, 420)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=fetch_days)

        stock = yf.Ticker(ticker)
        df = stock.history(
            start=start_date.strftime("%Y-%m-%d"),
            end=(end_date + timedelta(days=1)).strftime("%Y-%m-%d"),
            interval="1d",
            auto_adjust=False,
        )

        if df.empty:
            return pd.DataFrame()

        df = df.reset_index()
        # 清洗日期欄位，統整為 YYYY-MM-DD
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
        return df
    except Exception as e:
        print(f"[錯誤] 抓取 {ticker} 行情失敗: {e}")
        return pd.DataFrame()


def get_market_status(benchmark_ticker: str = config.BENCHMARK_TICKER) -> dict:
    """
    評估台股大盤指數狀態（收盤價與 20 EMA）
    """
    df = fetch_history(benchmark_ticker, lookback_days=60)
    if df.empty or len(df) < config.EMA_PERIOD:
        return {
            "close": 0.0,
            "ema20": 0.0,
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
