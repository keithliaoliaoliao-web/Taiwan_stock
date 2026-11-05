"""Minimal strategy engines for Taiwan stocks (pre-registered, no tuning).

Strategy A. Donchian breakout:
    Signal (completed bar i):
        Close[i] >= EMA(Close, 20)[i]  AND  Close[i] >= max(High over prior 20 bars, excluding i).
    Entry at open[i+1] with initial stop = lowest(Low over last 20 bars including bar i).
    Exit: at the NEXT session open after Close[j] < EMA(Close, 20)[j]
          OR intraday low[j] <= stop -> exit at stop (or open[j] if gapped through stop)
          OR bars_held >= 60           -> exit at close[j]

Strategy B. Monthly momentum rotation:
    First trading day of each month: rank 150 tickers by 126-day adjusted-price return,
    hold top 10 equal-weight. Rebalance at month-end. No stops.

Both use dividend-adjusted prices for signals/indicators and raw prices for executions.
Costs: buy fee 0.1425% + sell fee 0.1425% + sell tax 0.3%.
Position cap: 10 concurrent (Donchian applies real capital cap; momentum is explicit top-10).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

FEE_RATE = 0.0001425
SELL_TAX = 0.003
MAX_POSITIONS = 10
EMA_PERIOD = 20
ATR_PERIOD = 14
DONCHIAN_PERIOD = 20
MAX_HOLD_BARS = 60
MOMENTUM_LOOKBACK = 126
MOMENTUM_HOLD_N = 10


class PriceData:
    def __init__(self, ticker: str, raw: pd.DataFrame, adj: pd.DataFrame):
        self.ticker = ticker
        self.raw = raw.reset_index(drop=True)
        self.adj = adj.reset_index(drop=True)


def atr_series(df: pd.DataFrame, period: int = ATR_PERIOD) -> pd.Series:
    high, low, close_prev = df["High"], df["Low"], df["Close"].shift(1)
    tr = pd.concat(
        [(high - low).abs(), (high - close_prev).abs(), (low - close_prev).abs()],
        axis=1,
    ).max(axis=1)
    return tr.rolling(period, min_periods=1).mean()


def net_r_long(entry: float, exit_price: float, stop: float):
    risk = entry - stop
    if risk <= 0:
        return float("nan")
    buy_fee = entry * FEE_RATE
    sell_fee = exit_price * FEE_RATE
    tax = exit_price * SELL_TAX
    gross = exit_price - entry
    return (gross - buy_fee - sell_fee - tax) / risk


# ---------- Strategy A: Donchian breakout ---------- #

def backtest_donchian(data: dict[str, PriceData],
                      start_date: str | None = None,
                      end_date: str | None = None) -> pd.DataFrame:
    tickers = list(data.keys())
    frames = {}
    for t in tickers:
        adj = data[t].adj
        raw = data[t].raw
        dates = pd.to_datetime(raw["Date"]).reset_index(drop=True)
        ema = adj["Close"].ewm(span=EMA_PERIOD, adjust=False, min_periods=EMA_PERIOD).mean()
        atr = atr_series(adj)
        dch = adj["High"].shift(1).rolling(DONCHIAN_PERIOD, min_periods=DONCHIAN_PERIOD).max()
        low20 = adj["Low"].rolling(DONCHIAN_PERIOD, min_periods=DONCHIAN_PERIOD).min()
        frames[t] = {
            "adj_close": adj["Close"],
            "raw_open": raw["Open"],
            "raw_high": raw["High"],
            "raw_low": raw["Low"],
            "raw_close": raw["Close"],
            "dates": dates,
            "ema": ema,
            "atr": atr,
            "dch": dch,
            "low20": low20,
        }
    all_dates = sorted({d for t in tickers for d in frames[t]["dates"]})
    start = pd.Timestamp(start_date) if start_date else all_dates[0]
    end = pd.Timestamp(end_date) if end_date else all_dates[-1]
    dates = [d for d in all_dates if start <= d <= end]

    # map: date -> per-ticker positional index
    pos_of_date = {t: {d: i for i, d in enumerate(frames[t]["dates"])} for t in tickers}

    rows = []
    open_positions = []

    for d in dates:
        still_open = []

        # --- update existing positions ---
        for pos in open_positions:
            t = pos["ticker"]
            i = pos_of_date[t].get(d)
            if i is None:
                still_open.append(pos)
                continue
            today_low = float(frames[t]["raw_low"].iloc[i])
            today_open = float(frames[t]["raw_open"].iloc[i])
            today_close = float(frames[t]["raw_close"].iloc[i])
            stop = pos["stop"]
            exit_reason = None
            exit_price = None

            # --- pending exit set yesterday executes at today's open ---
            if pos.get("pending_exit"):
                exit_price = today_open
                exit_reason = "EMA_EXIT"
                net_r = net_r_long(pos["entry_price"], exit_price, stop)
                rows.append({**pos, "exit_date": d, "exit_reason": exit_reason,
                             "exit_price": exit_price, "net_r": net_r})
                continue

            # --- stop hit (intraday) ---
            if today_low <= stop:
                exit_price = min(stop, today_open)
                exit_reason = "INITIAL_STOP"
                net_r = net_r_long(pos["entry_price"], exit_price, stop)
                rows.append({**pos, "exit_date": d, "exit_reason": exit_reason,
                             "exit_price": exit_price, "net_r": net_r})
                continue

            # --- forced exit by holding bars ---
            if pos["bars_held"] >= MAX_HOLD_BARS:
                exit_price = today_close
                exit_reason = "MAX_HOLD"
                net_r = net_r_long(pos["entry_price"], exit_price, stop)
                rows.append({**pos, "exit_date": d, "exit_reason": exit_reason,
                             "exit_price": exit_price, "net_r": net_r})
                continue

            # --- check EMA exit signal (execute tomorrow open) ---
            ema_i = frames[t]["ema"].iloc[i]
            if not pd.isna(ema_i) and today_close < ema_i:
                pos["pending_exit"] = "EMA_EXIT"
                pos["bars_held"] += 1
                still_open.append(pos)
                continue

            pos["bars_held"] += 1
            still_open.append(pos)

        open_positions = still_open

        # --- scan for new signals on today's close; execute at next session's open ---
        for t in tickers:
            if len(open_positions) >= MAX_POSITIONS:
                break
            if any(p["ticker"] == t for p in open_positions):
                continue
            i = pos_of_date[t].get(d)
            if i is None:
                continue
            close_i = float(frames[t]["adj_close"].iloc[i])
            ema_i = frames[t]["ema"].iloc[i]
            dch_i = frames[t]["dch"].iloc[i]
            low20_i = frames[t]["low20"].iloc[i]
            if pd.isna(ema_i) or pd.isna(dch_i) or pd.isna(low20_i):
                continue
            if close_i >= ema_i and close_i >= dch_i:
                # next session for this ticker
                nxt_idx = None
                for j in range(i + 1, len(frames[t]["dates"])):
                    nxt_idx = j
                    break
                if nxt_idx is None:
                    continue
                entry_px = float(frames[t]["raw_open"].iloc[nxt_idx])
                stop = float(low20_i)
                if entry_px - stop <= 0:
                    continue
                open_positions.append({
                    "ticker": t, "sig_date": d,
                    "entry_date": frames[t]["dates"].iloc[nxt_idx],
                    "entry_price": entry_px, "stop": stop, "bars_held": 0,
                    "pending_exit": None,
                })

    # final: liquidate at last known bar
    for pos in open_positions:
        t = pos["ticker"]
        i = len(frames[t]["adj_close"]) - 1
        entry, stop = pos["entry_price"], pos["stop"]
        exit_px = float(frames[t]["adj_close"].iloc[i])
        net_r = net_r_long(entry, exit_px, stop)
        rows.append({**pos, "exit_date": None, "exit_reason": "END_OF_DATA",
                     "exit_price": exit_px, "net_r": net_r})

    return pd.DataFrame(rows)


# ---------- Strategy B: Monthly momentum rotation ---------- #

def backtest_momentum(data: dict[str, PriceData],
                      start_date: str = "2021-05-01",
                      end_date: str | None = None) -> pd.DataFrame:
    tickers = list(data.keys())
    # build a union trading calendar from raw dates
    all_dates = pd.DatetimeIndex(sorted({d for t in tickers for d in data[t].raw["Date"]}))
    adj_close = pd.DataFrame(index=all_dates, columns=tickers, dtype=float)
    raw_open = pd.DataFrame(index=all_dates, columns=tickers, dtype=float)
    raw_close = pd.DataFrame(index=all_dates, columns=tickers, dtype=float)
    for t in tickers:
        r = data[t].raw.set_index(pd.to_datetime(data[t].raw["Date"])).sort_index()
        a = data[t].adj.set_index(pd.to_datetime(data[t].raw["Date"])).sort_index()
        for d in r.index:
            if d in adj_close.index:
                adj_close.loc[d, t] = a.loc[d, "Close"]
                raw_open.loc[d, t] = r.loc[d, "Open"]
                raw_close.loc[d, t] = r.loc[d, "Close"]

    adj_ret = adj_close.pct_change(MOMENTUM_LOOKBACK)
    monthly_last = adj_close.resample("M").last().index
    end_ts = pd.Timestamp(end_date) if end_date else adj_close.index[-1]
    sel_months = [d for d in monthly_last if pd.Timestamp(start_date) <= d <= end_ts]

    rows = []
    for i in range(len(sel_months) - 1):
        m_end = sel_months[i]
        m_next = sel_months[i + 1]
        row = adj_ret.loc[m_end].dropna()
        if len(row) < MOMENTUM_HOLD_N:
            continue
        top = row.nlargest(MOMENTUM_HOLD_N).index.tolist()
        signal_date = m_end
        exit_date = m_next
        for t in top:
            entry_px = raw_open.loc[signal_date, t]
            exit_px = raw_close.loc[exit_date, t]
            if pd.isna(entry_px) or pd.isna(exit_px):
                continue
            buy_fee = entry_px * FEE_RATE
            sell_fee = exit_px * FEE_RATE
            tax = exit_px * SELL_TAX
            ret = (exit_px - entry_px - buy_fee - sell_fee - tax) / entry_px
            rows.append({
                "ticker": t,
                "sig_date": signal_date.strftime("%Y-%m-%d"),
                "entry_date": signal_date.strftime("%Y-%m-%d"),
                "exit_date": exit_date.strftime("%Y-%m-%d"),
                "entry_price": entry_px,
                "exit_price": exit_px,
                "month_return": ret,
                "net_return": ret,
            })

    return pd.DataFrame(rows) if rows else pd.DataFrame()


# ---------- Metrics ---------- #

def compute_metrics(trades: pd.DataFrame, r_col: str = "net_r") -> dict:
    if trades.empty:
        return {"n": 0}
    r = pd.to_numeric(trades[r_col], errors="coerce").dropna()
    if len(r) == 0:
        return {"n": 0}
    wins = r[r > 0]
    losses = r[r <= 0]
    pf = wins.sum() / abs(losses.sum()) if losses.sum() != 0 else float("inf")
    c = 0.0
    peak = 0.0
    max_dd = 0.0
    for v in r.tolist():
        c += v
        if c > peak:
            peak = c
        if c - peak < max_dd:
            max_dd = c - peak
    return {
        "n": int(len(r)),
        "win_rate": float(100 * len(wins) / len(r)),
        "expectancy": float(r.mean()),
        "profit_factor": float(pf),
        "total_r": float(r.sum()),
        "max_dd_r": float(max_dd),
    }


def regime_metrics(trades: pd.DataFrame, date_col: str = "sig_date", r_col: str = "net_r") -> dict:
    if trades.empty:
        return {}
    t = trades.copy()
    t[date_col] = pd.to_datetime(t[date_col])
    regs = {
        "2020-21": (pd.Timestamp("2020-10-01"), pd.Timestamp("2021-12-31")),
        "2022": (pd.Timestamp("2022-01-01"), pd.Timestamp("2022-12-31")),
        "2023-26": (pd.Timestamp("2023-01-01"), pd.Timestamp("2026-12-31")),
    }
    out = {}
    for name, (lo, hi) in regs.items():
        sub = t[(t[date_col] >= lo) & (t[date_col] <= hi)]
        out[name] = compute_metrics(sub, r_col=r_col)
    return out
