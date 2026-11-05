"""CLI runner: fetch data, backtest two strategies, write artifacts.

Usage:
    python new_strategy_backtest.py [--start 2024-01-02] [--end 2026-11-02]
"""

from __future__ import annotations

import argparse
import os
import sys
import time

import pandas as pd

from data_fetcher import fetch_history, fetch_dividends, adjust_for_dividends
import strategies

WATCHLIST = "watchlist.csv"


def fetch_all(tickers):
    out = {}
    sleep_sec = 6.5
    for i, t in enumerate(tickers, 1):
        print(f"[{i}/{len(tickers)}] {t} ...", end=" ", flush=True)
        try:
            raw = fetch_history(t, lookback_days=2600)
            if raw.empty or len(raw) < 130:
                print(f"skip (bars={len(raw)})")
                continue
            divs = fetch_dividends(t, lookback_days=2600)
            adj = adjust_for_dividends(raw.copy(), divs)
            # align
            raw = raw.reset_index(drop=True)
            adj = adj.reset_index(drop=True)
            out[t] = strategies.PriceData(t, raw=raw, adj=adj)
            print(f"bars={len(raw)} divs={len(divs)}")
            time.sleep(sleep_sec)
        except Exception as e:
            print(f"ERROR: {e}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickers", type=str, default="", help="comma-separated tickers (overrides watchlist)")
    ap.add_argument("--start", type=str, default="2024-01-02")
    ap.add_argument("--end", type=str, default="2026-11-02")
    ap.add_argument("--max-positions", type=int, default=10)
    args = ap.parse_args()

    if args.tickers:
        raw_list = [t.strip() for t in args.tickers.split(",") if t.strip()]
        tickers = raw_list
    else:
        tickers = pd.read_csv(WATCHLIST, encoding="utf-8-sig")["ticker"].tolist()
    print(f"universe: {len(tickers)} tickers")

    data = fetch_all(tickers)
    print(f"data ready: {len(data)}/{len(tickers)} tickers")

    print("\n=== Strategy A: Donchian breakout (Close>=EMA20, Close>=prior 20D high) ===")
    trades_a = strategies.backtest_donchian(data, start_date=args.start, end_date=args.end)
    trades_a.to_csv("bt_donchian.csv", index=False, encoding="utf-8-sig")
    m_a = strategies.compute_metrics(trades_a)
    print(m_a)
    print("by regime:")
    for k, v in strategies.regime_metrics(trades_a, r_col="net_r").items():
        print(f"  {k}: {v}")

    print("\n=== Strategy B: Monthly momentum rotation (top-10 by 126D ret) ===")
    trades_b = strategies.backtest_momentum(data, start_date="2021-05-01", end_date=args.end)
    trades_b.to_csv("bt_momentum.csv", index=False, encoding="utf-8-sig")
    m_b = strategies.compute_metrics(trades_b, r_col="month_return")
    print(m_b)
    print("by regime:")
    for k, v in strategies.regime_metrics(trades_b, date_col="sig_date").items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
