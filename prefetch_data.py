"""prefetch_data.py - 預先抓取所有股票的價格與股利資料，存入快取

執行一次後，後續回測可用 --cache-only 模式（不發 API 請求）。
"""
import os
import time
import csv
import pandas as pd
from data_fetcher import fetch_history, fetch_dividends

RATE_LIMIT_SEC = 6.5
CACHE_DIR = "data_cache"
DIV_CACHE_DIR = "dividend_cache"
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(DIV_CACHE_DIR, exist_ok=True)


def load_tickers():
    tickers = []
    with open("watchlist.csv", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            t = r.get("ticker", "").strip()
            if t:
                if not t.endswith(".TW") and not t.endswith(".TWO"):
                    t = f"{t}.TW"
                tickers.append(t)
    return tickers


def cache_path(ticker, d):
    return os.path.join(d, f"{ticker.replace('.', '_')}.csv")


def main():
    tickers = load_tickers()
    print(f"Prefetching {len(tickers)} tickers...")

    for idx, t in enumerate(tickers):
        # Price
        p = cache_path(t, CACHE_DIR)
        if not os.path.exists(p):
            print(f"[{idx+1}/{len(tickers)}] {t} price...", end=" ", flush=True)
            time.sleep(RATE_LIMIT_SEC)
            df = fetch_history(t, lookback_days=2200)
            if df is not None and not df.empty:
                df.to_csv(p, index=False, encoding="utf-8-sig")
                print(f"OK ({len(df)} bars)")
            else:
                print("NO DATA")
        # Dividend
        dp = cache_path(t, DIV_CACHE_DIR)
        if not os.path.exists(dp):
            time.sleep(RATE_LIMIT_SEC)
            ddf = fetch_dividends(t, lookback_days=2200)
            if ddf is not None and not ddf.empty:
                ddf.to_csv(dp, index=False, encoding="utf-8-sig")
            else:
                # save empty file to mark as fetched
                pd.DataFrame().to_csv(dp, index=False, encoding="utf-8-sig")

    print("Prefetch complete.")


if __name__ == "__main__":
    main()
