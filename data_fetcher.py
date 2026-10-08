# -*- coding: utf-8 -*-
"""
市場資料擷取模組 (data_fetcher.py)

負責透過 yfinance 擷取台灣加權指數 (^TWII) 與台股個股歷史日 K 線資料，
計算 20EMA、14ATR、成交金額與均量，並轉換為儀表板圖表所需之資料結構。
"""

import time
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd
import numpy as np
import yfinance as yf

import config


def fetch_market_index(ticker: str = config.BENCHMARK_TICKER) -> Dict[str, Any]:
    """
    抓取大盤加權指數日線，計算 20EMA 並判定多空狀態
    """
    print(f"[行情] 抓取大盤指數資料 ({ticker})...")
    try:
        t = yf.Ticker(ticker)
        df = t.history(period="6mo")
        if df.empty or len(df) < config.EMA_PERIOD:
            print(f"[警告] 大盤資料筆數不足 ({len(df)} 筆)")
            return {"close": 0.0, "ema20": 0.0, "bullish": False}
            
        df["EMA20"] = df["Close"].ewm(span=config.EMA_PERIOD, adjust=False).mean()
        
        last_close = float(df["Close"].iloc[-1])
        last_ema20 = float(df["EMA20"].iloc[-1])
        bullish = last_close > last_ema20
        
        return {
            "close": round(last_close, 2),
            "ema20": round(last_ema20, 2),
            "bullish": bool(bullish)
        }
    except Exception as e:
        print(f"[錯誤] 抓取大盤指數失敗: {e}")
        return {"close": 0.0, "ema20": 0.0, "bullish": False}


def calculate_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    計算價格行為引擎所需的技術指標 (EMA20, ATR14, 成交金額, 成交均量)
    """
    if df.empty or len(df) < 5:
        return df
        
    df = df.copy()
    
    df["EMA20"] = df["Close"].ewm(span=config.EMA_PERIOD, adjust=False).mean()
    
    high = df["High"]
    low = df["Low"]
    close_prev = df["Close"].shift(1)
    
    tr1 = high - low
    tr2 = (high - close_prev).abs()
    tr3 = (low - close_prev).abs()
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df["TR"] = tr
    df["ATR14"] = tr.rolling(window=config.ATR_PERIOD).mean()
    
    df["Turnover"] = df["Close"] * df["Volume"]
    df["Volume_MA20"] = df["Volume"].rolling(window=config.VOLUME_MA_PERIOD).mean()
    
    return df


def fetch_stock_daily_bars(ticker: str, lookback_days: int = config.DATA_LOOKBACK_DAYS) -> Optional[pd.DataFrame]:
    """
    抓取單檔股票指定天數之歷史日線資料，並預先計算技術指標
    """
    try:
        t = yf.Ticker(ticker)
        df = t.history(period="1y")
        if df.empty or len(df) < config.EMA_PERIOD + 5:
            return None
            
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
            
        req_cols = ["Open", "High", "Low", "Close", "Volume"]
        for col in req_cols:
            if col not in df.columns:
                return None
        df = df[req_cols]
        
        df = calculate_technical_indicators(df)
        
        if len(df) > lookback_days + 30:
            df = df.iloc[-(lookback_days + 30):]
            
        return df
    except Exception:
        return None


def format_chart_series(df: pd.DataFrame, bars_count: int = 60) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    將 DataFrame 格式化為 Lightweight Charts 可直接消費的 K 線與 EMA 陣列
    """
    candles: List[Dict[str, Any]] = []
    ema_points: List[Dict[str, Any]] = []
    
    if df.empty:
        return candles, ema_points
        
    slice_df = df.tail(bars_count)
    for idx, row in slice_df.iterrows():
        date_str = idx.strftime("%Y-%m-%d")
        open_val = float(round(row["Open"], 2))
        high_val = float(round(row["High"], 2))
        low_val = float(round(row["Low"], 2))
        close_val = float(round(row["Close"], 2))
        
        candles.append({
            "time": date_str,
            "open": open_val,
            "high": high_val,
            "low": low_val,
            "close": close_val
        })
        
        if "EMA20" in row and not pd.isna(row["EMA20"]):
            ema_points.append({
                "time": date_str,
                "value": float(round(row["EMA20"], 2))
            })
            
    return candles, ema_points
