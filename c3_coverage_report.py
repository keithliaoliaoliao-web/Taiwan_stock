"""c3_coverage_report.py - 公司行動資料覆蓋率報告

檢查 FinMind 股利/分割資料的覆蓋率，列出缺事件、缺參考價的股票與日期。
"""
import os
import time
import pandas as pd
from data_fetcher import fetch_dividends, fetch_splits, fetch_history

WATCHLIST_FILE = "watchlist.csv"
RATE_LIMIT_SEC = 6.5


def load_tickers():
    tickers = []
    with open(WATCHLIST_FILE, encoding="utf-8-sig") as f:
        import csv
        for r in csv.DictReader(f):
            t = r.get("ticker", "").strip()
            if t:
                if not t.endswith(".TW") and not t.endswith(".TWO"):
                    t = f"{t}.TW"
                tickers.append(t)
    return tickers


def main():
    tickers = load_tickers()
    print(f"檢查 {len(tickers)} 檔股票的公司行動資料覆蓋率...")

    results = []
    for idx, t in enumerate(tickers):
        print(f"[{idx+1}/{len(tickers)}] {t} ...", end=" ", flush=True)
        try:
            time.sleep(RATE_LIMIT_SEC)
            div_df = fetch_dividends(t, lookback_days=2200)
            time.sleep(RATE_LIMIT_SEC)
            split_df = fetch_splits(t, lookback_days=2200)
            hist_df = fetch_history(t, lookback_days=2200)

            n_div = len(div_df) if div_df is not None and not div_df.empty else 0
            n_split = len(split_df) if split_df is not None and not split_df.empty else 0
            n_bars = len(hist_df) if hist_df is not None and not hist_df.empty else 0

            # check for missing ex_dates in price data
            missing_ex = []
            if not div_df.empty and not hist_df.empty:
                hist_dates = set(pd.to_datetime(hist_df["Date"]).dt.strftime("%Y-%m-%d"))
                for _, r in div_df.iterrows():
                    ex = str(r.get("ex_date", ""))[:10]
                    if ex and ex not in hist_dates:
                        missing_ex.append(ex)

            status = "OK"
            if n_bars == 0:
                status = "NO_PRICE_DATA"
            elif n_div == 0 and n_bars > 100:
                status = "NO_DIVIDEND_DATA"
            elif missing_ex:
                status = f"MISSING_EX_DATES({len(missing_ex)})"

            results.append({
                "ticker": t,
                "n_bars": n_bars,
                "n_dividends": n_div,
                "n_splits": n_split,
                "missing_ex_dates": ";".join(missing_ex) if missing_ex else "",
                "status": status,
            })
            print(f"bars={n_bars} div={n_div} split={n_split} [{status}]")
        except Exception as e:
            results.append({"ticker": t, "n_bars": 0, "n_dividends": 0, "n_splits": 0, "missing_ex_dates": "", "status": f"ERROR: {e}"})
            print(f"ERROR: {e}")

    rdf = pd.DataFrame(results)
    rdf.to_csv("c3_coverage_report.csv", index=False, encoding="utf-8-sig")
    print("\n=== Summary ===")
    print(rdf["status"].value_counts().to_string())
    print(f"\nSaved to c3_coverage_report.csv")
    # stats
    print(f"Total tickers: {len(rdf)}")
    print(f"Tickers with dividends: {(rdf['n_dividends'] > 0).sum()}")
    print(f"Tickers with splits: {(rdf['n_splits'] > 0).sum()}")
    print(f"Tickers with no price data: {(rdf['status'] == 'NO_PRICE_DATA').sum()}")


if __name__ == "__main__":
    main()
