"""backtest.py - Price Action 回測框架 (Brooks H1/H2/MTR/Wedge/BOM)

使用 FinMind 歷史資料，對 PriceActionEngine 產生的訊號進行交易模擬與績效統計。

用法:
  python backtest.py --tickers 2330.TW,2317.TW --start 2024-01-01 --end 2026-06-30 --strategy all
  python backtest.py --watchlist --start 2024-01-01 --end 2026-06-30
  python backtest.py --watchlist --strategy h2 --out backtest_h2.csv
"""
import argparse
import json
import os
import time
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from data_fetcher import fetch_history
from price_action_engine import PriceActionEngine
import config

CACHE_DIR = "data_cache"
RATE_LIMIT_SEC = 6.5  # FinMind 600 req/hour ~ 1 req/6s


def ensure_cache_dir():
    os.makedirs(CACHE_DIR, exist_ok=True)


def cache_path(ticker):
    return os.path.join(CACHE_DIR, f"{ticker.replace('.', '_')}.csv")


def load_cached(ticker, max_age_hours=24):
    p = cache_path(ticker)
    if not os.path.exists(p):
        return None
    age = time.time() - os.path.getmtime(p)
    if age > max_age_hours * 3600:
        return None
    try:
        df = pd.read_csv(p)
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"])
        return df
    except Exception:
        return None


def save_cache(ticker, df):
    ensure_cache_dir()
    df.to_csv(cache_path(ticker), index=False, encoding="utf-8-sig")


def fetch_with_cache(ticker, lookback_days=2200, rate_limit=True):
    cached = load_cached(ticker)
    if cached is not None and not cached.empty:
        return cached
    if rate_limit:
        time.sleep(RATE_LIMIT_SEC)
    df = fetch_history(ticker, lookback_days=lookback_days)
    if df is not None and not df.empty:
        save_cache(ticker, df)
    return df


def passes_filter(sig_type, row, entry, stop, target, min_rr, max_risk_pct, mtr_confirmed_only):
    risk = abs(entry - stop)
    if risk <= 0:
        return False
    risk_pct = (risk / entry) * 100 if entry > 0 else 100
    if risk_pct > max_risk_pct:
        return False
    # R:R using target if available, else R_MULTIPLE
    if target is not None and not (isinstance(target, float) and np.isnan(target)):
        rr = abs(target - entry) / risk
    else:
        rr = float(getattr(config, "R_MULTIPLE", 2.0))
    if rr < min_rr:
        return False
    if sig_type == "MTR" and mtr_confirmed_only:
        if not bool(row.get("MTR_Confirmed", False)):
            return False
    return True


def simulate_trades(analyzed_df, strategy="all", min_rr=0.0, max_risk_pct=100.0,
                    mtr_confirmed_only=False, exit_mode="v1", trail_mult=1.0):
    """Simulate trades from analyzed_df. Returns list of trade dicts."""
    trades = []
    n = len(analyzed_df)
    if n < 5:
        return trades

    close = analyzed_df["Close"].to_numpy(dtype=float)
    high = analyzed_df["High"].to_numpy(dtype=float)
    low = analyzed_df["Low"].to_numpy(dtype=float)
    openp = analyzed_df["Open"].to_numpy(dtype=float)
    ema = analyzed_df["EMA_20"].to_numpy(dtype=float)
    dates = [str(x)[:10] for x in analyzed_df["Date"]]

    cost_rate = 0.00585
    max_hold = int(getattr(config, "EMA_EXIT_MAX_HOLDING_DAYS", 120))

    def record(sig_idx, entry_price, stop, target, direction, sig_type):
        # direction: +1 long, -1 short
        entry_day = sig_idx + 1 if sig_type == "H2" else sig_idx  # H2 triggers next day
        if entry_day >= n:
            return
        # For H2, entry triggers when high >= trigger_price
        if sig_type == "H2":
            trig = entry_price
            if high[entry_day] < trig:
                return  # not triggered
            entry_price = max(trig, openp[entry_day])
            entry_day_actual = entry_day
        else:
            entry_day_actual = entry_day  # buy the close of signal day

        if entry_day_actual >= n:
            return

        risk = abs(entry_price - stop)
        if risk <= 0:
            return

        # simulate forward
        exit_day = None
        exit_price = None
        exit_reason = None
        pending_ema = False
        days_held = 0

        # same-day stop check for H2
        if sig_type == "H2":
            if low[entry_day_actual] <= stop:
                exit_price = min(openp[entry_day_actual], stop)
                exit_reason = "SAME_DAY_STOP"
                exit_day = entry_day_actual
            else:
                # entered, now track
                pass

        if exit_day is None and sig_type == "H2":
            if low[entry_day_actual] <= stop:
                exit_day = entry_day_actual
                exit_price = min(openp[entry_day_actual], stop)
                exit_reason = "SAME_DAY_STOP"

        if exit_day is None:
            # For buy-the-close (MTR/Wedge/BOM), entry at signal day close;
            # start exit checks from the NEXT day.
            track_start = entry_day_actual + 1
            days_held = 0
            trail_stop = stop
            best_price = entry_price
            for j in range(track_start, n):
                days_held += 1
                if direction > 0:
                    if close[j] > best_price:
                        best_price = close[j]
                        if exit_mode == "trailing":
                            trail_stop = max(trail_stop, best_price - risk * trail_mult)
                    effective_stop = trail_stop if exit_mode == "trailing" else stop
                else:
                    if close[j] < best_price:
                        best_price = close[j]
                        if exit_mode == "trailing":
                            trail_stop = min(trail_stop, best_price + risk * trail_mult)
                    effective_stop = trail_stop if exit_mode == "trailing" else stop

                if pending_ema:
                    exit_day = j
                    exit_price = openp[j]
                    exit_reason = "EXIT_EMA20"
                    break
                if (direction > 0 and low[j] <= effective_stop) or (direction < 0 and high[j] >= effective_stop):
                    exit_day = j
                    exit_price = (min(openp[j], effective_stop) if direction > 0
                                  else max(openp[j], effective_stop))
                    exit_reason = "TRAILING_STOP" if exit_mode == "trailing" else "INITIAL_STOP"
                    break
                if days_held >= max_hold:
                    exit_day = j
                    exit_price = close[j]
                    exit_reason = "MAX_120D"
                    break
                if (direction > 0 and close[j] < ema[j]) or (direction < 0 and close[j] > ema[j]):
                    pending_ema = True
                else:
                    pending_ema = False

        if exit_day is None:
            exit_day = n - 1
            exit_price = close[n-1]
            exit_reason = "END_OF_DATA"

        if direction > 0:
            net_r = round(((exit_price * (1.0 - cost_rate)) - entry_price) / risk, 3)
        else:
            net_r = round((entry_price - (exit_price * (1.0 + cost_rate))) / risk, 3)

        trades.append({
            "ticker": analyzed_df["Ticker"].iloc[0] if "Ticker" in analyzed_df.columns else "",
            "sig_date": dates[sig_idx],
            "sig_type": sig_type,
            "direction": "LONG" if direction > 0 else "SHORT",
            "entry_date": dates[entry_day_actual],
            "entry_price": round(float(entry_price), 2),
            "stop_loss": round(float(stop), 2),
            "target": round(float(target), 2) if target and not (isinstance(target, float) and np.isnan(target)) else None,
            "exit_date": dates[exit_day],
            "exit_price": round(float(exit_price), 2),
            "exit_reason": exit_reason,
            "days_held": int(days_held),
            "net_r": net_r,
        })

    # iterate signals
    for i in range(2, n - 1):
        row = analyzed_df.iloc[i]
        # H2 signal
        if strategy in ("h2", "all"):
            if bool(row.get("Signal_H2", False)):
                trig = row.get("Trigger_Price", np.nan)
                stop = row.get("Stop_Loss", np.nan)
                target = row.get("Target_Price", np.nan)
                if pd.notna(trig) and pd.notna(stop):
                    if not passes_filter("H2", row, float(trig), float(stop), float(target) if pd.notna(target) else None, min_rr, max_risk_pct, mtr_confirmed_only):
                        continue
                    record(i, float(trig), float(stop), float(target) if pd.notna(target) else None, 1, "H2")

        # MTR
        if strategy in ("mtr", "all"):
            if bool(row.get("MTR_Detected", False)):
                d = str(row.get("MTR_Direction", "NONE"))
                entry = row.get("MTR_Entry", np.nan)
                stop = row.get("MTR_Stop", np.nan)
                target = row.get("MTR_Target", np.nan)
                if pd.notna(entry) and pd.notna(stop):
                    if not passes_filter("MTR", row, float(entry), float(stop), float(target) if pd.notna(target) else None, min_rr, max_risk_pct, mtr_confirmed_only):
                        continue
                    direction = 1 if "BULL" in d else -1
                    record(i, float(entry), float(stop), float(target) if pd.notna(target) else None, direction, "MTR")

        # Wedge
        if strategy in ("wedge", "all"):
            if bool(row.get("Wedge_Detected", False)):
                typ = str(row.get("Wedge_Type", "NONE"))
                entry = row.get("Wedge_Entry", np.nan)
                stop = row.get("Wedge_Stop", np.nan)
                target = row.get("Wedge_Target", np.nan)
                if pd.notna(entry) and pd.notna(stop):
                    if not passes_filter("Wedge", row, float(entry), float(stop), float(target) if pd.notna(target) else None, min_rr, max_risk_pct, mtr_confirmed_only):
                        continue
                    direction = 1 if "BOTTOM" in typ else -1
                    record(i, float(entry), float(stop), float(target) if pd.notna(target) else None, direction, "Wedge")

        # BOM
        if strategy in ("bom", "all"):
            if bool(row.get("BOM_Detected", False)):
                d = str(row.get("BOM_Direction", "NONE"))
                entry = row.get("BOM_Entry", np.nan)
                stop = row.get("BOM_Stop", np.nan)
                target = row.get("BOM_Target", np.nan)
                if pd.notna(entry) and pd.notna(stop):
                    if not passes_filter("BOM", row, float(entry), float(stop), float(target) if pd.notna(target) else None, min_rr, max_risk_pct, mtr_confirmed_only):
                        continue
                    direction = 1 if "BULL" in d else -1
                    record(i, float(entry), float(stop), float(target) if pd.notna(target) else None, direction, "BOM")

    return trades


def compute_metrics(trades):
    if not trades:
        return {}
    df = pd.DataFrame(trades)
    n = len(df)
    wins = df[df["net_r"] > 0]
    losses = df[df["net_r"] <= 0]
    win_rate = len(wins) / n
    avg_win = wins["net_r"].mean() if len(wins) > 0 else 0
    avg_loss = losses["net_r"].mean() if len(losses) > 0 else 0
    expectancy = df["net_r"].mean()
    profit_factor = (wins["net_r"].sum() / abs(losses["net_r"].sum())) if len(losses) > 0 and losses["net_r"].sum() != 0 else float("inf")
    # max drawdown on cumulative R
    cum = df["net_r"].cumsum()
    peak = cum.cummax()
    dd = cum - peak
    max_dd = dd.min()
    # by exit reason
    by_reason = df.groupby("exit_reason")["net_r"].agg(["count", "mean"]).to_dict("index")
    # by signal type
    by_type = df.groupby("sig_type")["net_r"].agg(["count", "mean"]).to_dict("index")
    return {
        "total_trades": n,
        "win_rate": round(win_rate * 100, 2),
        "avg_win_r": round(float(avg_win), 3),
        "avg_loss_r": round(float(avg_loss), 3),
        "expectancy_r": round(float(expectancy), 3),
        "profit_factor": round(float(profit_factor), 3) if profit_factor != float("inf") else "inf",
        "total_r": round(float(df["net_r"].sum()), 3),
        "max_drawdown_r": round(float(max_dd), 3),
        "by_exit_reason": by_reason,
        "by_signal_type": by_type,
    }


def main():
    parser = argparse.ArgumentParser(description="Price Action Backtest")
    parser.add_argument("--tickers", type=str, default="", help="comma-separated tickers")
    parser.add_argument("--watchlist", action="store_true", help="use watchlist.csv")
    parser.add_argument("--start", type=str, required=True, help="start date YYYY-MM-DD")
    parser.add_argument("--end", type=str, required=True, help="end date YYYY-MM-DD")
    parser.add_argument("--strategy", type=str, default="all", choices=["h2", "mtr", "wedge", "bom", "climax", "all"])
    parser.add_argument("--lookback", type=int, default=2200, help="lookback days for fetch")
    parser.add_argument("--out", type=str, default="backtest_trades.csv", help="output trades CSV")
    parser.add_argument("--no-cache", action="store_true", help="disable cache")
    parser.add_argument("--priority-tickers", type=str, default="", help="comma-separated priority tickers (shorter cache)")
    parser.add_argument("--priority-file", type=str, default="", help="file with priority tickers (one per line)")
    parser.add_argument("--refresh-signals", action="store_true", help="refresh only tickers found in scan_result.json signals")
    parser.add_argument("--priority-max-age", type=int, default=1, help="cache max age (hours) for priority tickers")
    parser.add_argument("--min-rr", type=float, default=0.0, help="minimum risk/reward ratio filter")
    parser.add_argument("--max-risk-pct", type=float, default=100.0, help="max risk pct per trade filter")
    parser.add_argument("--mtr-confirmed-only", action="store_true", help="only take MTR_Confirmed signals")
    parser.add_argument("--exit-mode", type=str, default="v1", choices=["v1", "trailing"], help="exit mode")
    parser.add_argument("--trail-mult", type=float, default=1.0, help="trailing stop ATR multiple")
    args = parser.parse_args()

    # Resolve priority tickers (signal watchlist)
    priority = set()
    if args.priority_tickers:
        for t in args.priority_tickers.split(","):
            t = t.strip()
            if t:
                if not t.endswith(".TW") and not t.endswith(".TWO"):
                    t = f"{t}.TW"
                priority.add(t)
    if args.priority_file:
        with open(args.priority_file, encoding="utf-8") as f:
            for line in f:
                t = line.strip()
                if t and not t.startswith("#"):
                    if not t.endswith(".TW") and not t.endswith(".TWO"):
                        t = f"{t}.TW"
                    priority.add(t)
    if args.refresh_signals:
        # read scan_result.json and extract all signal tickers
        for sf in ["scan_result.json", "public/scan_result.json"]:
            if os.path.exists(sf):
                try:
                    with open(sf, encoding="utf-8") as f:
                        data = json.load(f)
                    for key in ["signals", "mtr_signals", "wedge_signals", "bom_signals", "climax_signals"]:
                        for s in data.get(key, []) or []:
                            t = s.get("ticker", "").strip()
                            if t:
                                if not t.endswith(".TW") and not t.endswith(".TWO"):
                                    t = f"{t}.TW"
                                priority.add(t)
                except Exception:
                    pass

    if args.watchlist:
        import csv
        tickers = []
        with open(config.WATCHLIST_FILE, encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                t = r.get("ticker", "").strip()
                if t:
                    if not t.endswith(".TW") and not t.endswith(".TWO"):
                        t = f"{t}.TW"
                    tickers.append(t)
    else:
        tickers = [t.strip() for t in args.tickers.split(",") if t.strip()]

    # Deduplicate while preserving priority-first order
    seen = set()
    ordered = []
    for t in list(priority) + tickers:
        if t not in seen:
            seen.add(t)
            ordered.append(t)
    tickers = ordered

    print(f"Backtest: {len(tickers)} tickers ({len(priority)} priority), {args.start} ~ {args.end}, strategy={args.strategy}")

    all_trades = []
    for idx, ticker in enumerate(tickers):
        print(f"[{idx+1}/{len(tickers)}] {ticker} ...", end=" ", flush=True)
        try:
            is_priority = ticker in priority
            if args.no_cache:
                df = fetch_history(ticker, lookback_days=args.lookback)
            else:
                cached = load_cached(ticker, max_age_hours=(args.priority_max_age if is_priority else 24))
                if cached is not None and not cached.empty:
                    df = cached
                else:
                    time.sleep(RATE_LIMIT_SEC)
                    df = fetch_history(ticker, lookback_days=args.lookback)
                    if df is not None and not df.empty:
                        save_cache(ticker, df)
            if df is None or df.empty:
                print("NO DATA")
                continue
            # tag ticker column for trade records
            df = df.copy()
            # run engine
            analyzed = PriceActionEngine.analyze_setups(df)
            analyzed["Ticker"] = ticker
            # ensure Date is datetime
            analyzed["Date"] = pd.to_datetime(analyzed["Date"])
            # filter date range
            mask = (analyzed["Date"] >= pd.to_datetime(args.start)) & (analyzed["Date"] <= pd.to_datetime(args.end))
            # keep full history for simulation but only record signals in range
            # (simulate_trades filters by sig_date internally via range? We'll filter trades after)
            trades = simulate_trades(analyzed, strategy=args.strategy, min_rr=args.min_rr,
                                    max_risk_pct=args.max_risk_pct, mtr_confirmed_only=args.mtr_confirmed_only,
                                    exit_mode=args.exit_mode, trail_mult=args.trail_mult)
            # filter trades by sig_date range
            filtered = [t for t in trades if args.start <= t["sig_date"] <= args.end]
            all_trades.extend(filtered)
            print(f"trades={len(filtered)}")
        except Exception as e:
            print(f"ERROR: {e}")

    if not all_trades:
        print("No trades generated.")
        return

    trades_df = pd.DataFrame(all_trades)
    trades_df.to_csv(args.out, index=False, encoding="utf-8-sig")
    print(f"\nSaved {len(all_trades)} trades to {args.out}")

    metrics = compute_metrics(all_trades)
    print("\n=== Backtest Metrics ===")
    for k, v in metrics.items():
        if isinstance(v, dict):
            print(f"  {k}:")
            for kk, vv in v.items():
                print(f"    {kk}: {vv}")
        else:
            print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
