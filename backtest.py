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
CHIP_CACHE_DIR = "chip_cache"
RATE_LIMIT_SEC = 6.5  # FinMind 600 req/hour ~ 1 req/6s


def ensure_cache_dir():
    os.makedirs(CACHE_DIR, exist_ok=True)
    os.makedirs(CHIP_CACHE_DIR, exist_ok=True)


def chip_cache_path(ticker):
    return os.path.join(CHIP_CACHE_DIR, f"{ticker.replace('.', '_')}.csv")


def load_chip_cache(ticker, max_age_hours=24):
    p = chip_cache_path(ticker)
    if not os.path.exists(p):
        return None
    age = time.time() - os.path.getmtime(p)
    if age > max_age_hours * 3600:
        return None
    try:
        df = pd.read_csv(p)
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
        return df
    except Exception:
        return None


def save_chip_cache(ticker, df):
    ensure_cache_dir()
    df.to_csv(chip_cache_path(ticker), index=False, encoding="utf-8-sig")


def fetch_chips_history(ticker, start_date, end_date, rate_limit=True):
    cached = load_chip_cache(ticker)
    if cached is not None and not cached.empty:
        return cached
    if rate_limit:
        time.sleep(RATE_LIMIT_SEC)
    clean_id = ticker.split(".")[0].strip()
    params = {
        "dataset": "TaiwanStockInstitutionalInvestorsBuySell",
        "data_id": clean_id,
        "start_date": start_date,
        "end_date": end_date,
    }
    import os as _os
    token = _os.environ.get("FINMIND_TOKEN", "").strip()
    if token:
        params["token"] = token
    try:
        import requests
        res = requests.get("https://api.finmindtrade.com/api/v4/data", params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        if res.status_code == 200:
            payload = res.json()
            if payload.get("status") == 200:
                data = payload.get("data", [])
                if data:
                    df = pd.DataFrame(data)
                    save_chip_cache(ticker, df)
                    return df
    except Exception as e:
        print(f"  [chip fetch error] {ticker}: {e}")
    return pd.DataFrame()


def trust_buy_pass_for_date(chip_df, target_date):
    '''Return True only when the investment trust was a NET BUYER on the signal day
    AND over the trailing 5 trading days (strict AND, previously a weak OR).

    C3 FIX (CRITICAL): the previous implementation compared a full timestamp
    against a date-only string, so the same-day branch never matched. Dates are now
    normalised to %Y-%m-%d before comparison.
    '''
    if chip_df is None or chip_df.empty:
        return False
    try:
        tdf = chip_df.copy()
        tdf["date"] = pd.to_datetime(tdf["date"], errors="coerce")
        tdf = tdf.dropna(subset=["date"])
        target = pd.to_datetime(target_date, errors="coerce")
        if pd.isna(target):
            return False
        target_norm = target.strftime("%Y-%m-%d")

        trust_all = tdf[tdf["name"].astype(str).str.contains("Investment_Trust", case=False, na=False)]
        if trust_all.empty:
            return False

        # Same-day net buy (normalised date comparison)
        day = trust_all[trust_all["date"].dt.strftime("%Y-%m-%d") == target_norm]
        t_net = float((day["buy"] - day["sell"]).sum()) if not day.empty else 0.0

        # Trailing 5-observation net buy (must be on or before the signal day)
        recent = trust_all[trust_all["date"] <= target].tail(5)
        t_5d = float((recent["buy"] - recent["sell"]).sum()) if not recent.empty else 0.0

        # Both conditions required (was: t_net > 0 or t_5d > 0)
        return bool(t_net > 0 and t_5d > 0)
    except Exception:
        return False


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
                    mtr_confirmed_only=False, exit_mode="v1", trail_mult=1.0,
                    exclude_climax=False, min_leg_count=0, channel_only=False,
                    chip_df=None, chip_filter=False, pullback_pct=0.0,
                    pullback_window=5, key_level_only=False,
                    dividend_df=None, short_borrow_fee_annual=0.05,
                    forced_cover=True, no_dividend_income=False):
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
    # C1 FIX: dividend back-adjustment offset per bar (adjusted - raw).
    # Used ONLY to convert reported prices back to the traded scale; never used
    # for simulation, which must stay entirely on the adjusted scale.
    if "_price_offset" in analyzed_df.columns:
        price_offset = analyzed_df["_price_offset"].to_numpy(dtype=float)
    else:
        price_offset = np.zeros(n, dtype=float)

    def _to_raw(idx, adjusted_price):
        """Convert an adjusted scale price back to the raw traded scale for logging."""
        if adjusted_price is None:
            return None
        try:
            return float(adjusted_price) - float(price_offset[idx])
        except Exception:
            return float(adjusted_price)

    cost_rate = 0.00585
    max_hold = int(getattr(config, "EMA_EXIT_MAX_HOLDING_DAYS", 120))

    def record(sig_idx, entry_price, stop, target, direction, sig_type):
        # direction: +1 long, -1 short
        # C1 fix: all signals enter at next day's open (no same-day close execution)
        # H2: limit order at trigger_price, triggers when high >= trigger
        # MTR/Wedge/BOM: market order at next day's open
        entry_day = sig_idx + 1
        if entry_day >= n:
            return
        if sig_type == "H2":
            trig = entry_price
            if high[entry_day] < trig:
                return  # not triggered
            entry_price = max(trig, openp[entry_day])
            entry_day_actual = entry_day
        else:
            # next day open execution (with slippage)
            entry_price = openp[entry_day] * 1.001  # 0.1% slippage
            entry_day_actual = entry_day

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

        # C4 / H1 FIX: unified gap-through-stop handling.
        # If the entry day OPEN is already beyond the stop, the position is either
        # never filled (limit order) or filled and instantly stopped (market order).
        # We model the conservative and consistent choice: skip the trade.
        # This is now applied identically to every signal type (was duplicated and
        # partly dead code, and only partially enforced for H2).
        locked_days = 0
        if direction > 0 and openp[entry_day_actual] < stop:
            return  # gap down through stop, skip trade
        if direction < 0 and openp[entry_day_actual] > stop:
            return  # gap up through stop, skip trade

        # Same-day stop check (unified for ALL signal types)
        if (direction > 0 and low[entry_day_actual] <= stop) or \
           (direction < 0 and high[entry_day_actual] >= stop):
            exit_day = entry_day_actual
            exit_price = (min(openp[entry_day_actual], stop) if direction > 0
                          else max(openp[entry_day_actual], stop))
            exit_reason = "SAME_DAY_STOP"

        if exit_day is None:
            # Pre-scan ex-dividend dates for forced-cover (short) handling.
            # Forced cover day = last tradable day BEFORE the ex-dividend date.
            exdiv_set = set()
            if dividend_df is not None and not dividend_df.empty:
                try:
                    for _, dr in dividend_df.iterrows():
                        exdiv_set.add(str(pd.to_datetime(dr["ex_date"]).date()))
                except Exception:
                    exdiv_set = set()
            track_start = entry_day_actual
            days_held = 0
            locked_days = 0
            trail_stop = stop
            best_price = entry_price
            for j in range(track_start, n):
                prev_c = close[j - 1] if j > 0 else close[j]
                is_one_tick = (openp[j] == high[j] == low[j] == close[j])
                is_limit_down = is_one_tick and abs(openp[j] - prev_c * 0.9) <= prev_c * 0.005
                is_limit_up = is_one_tick and abs(openp[j] - prev_c * 1.1) <= prev_c * 0.005
                # direction-aware block:
                #   long exit = SELL  -> blocked on limit-down
                #   short cover = BUY -> blocked on limit-up
                blocked = is_limit_down if direction > 0 else is_limit_up
                if j == entry_day_actual:
                    # entry day: only EMA condition check (stop already handled)
                    days_held = 0
                    if blocked:
                        pending_ema = False
                    elif (direction > 0 and close[j] < ema[j]) or (direction < 0 and close[j] > ema[j]):
                        pending_ema = True
                    else:
                        pending_ema = False
                    continue
                days_held += 1
                if blocked:
                    # can't exit today (long: limit-down; short: limit-up)
                    locked_days += 1
                    continue
                # C4: forced cover on the day BEFORE ex-dividend for SHORT positions (融券 模式)
                if direction < 0 and forced_cover and exdiv_set:
                    cur_d = str(dates[j])[:10]
                    nxt_d = str(dates[j + 1])[:10] if j + 1 < len(dates) else None
                    if (nxt_d and nxt_d in exdiv_set) or cur_d in exdiv_set:
                        # covered on/before ex-date: no dividend compensation owed
                        exit_day = j
                        exit_price = close[j]
                        exit_reason = "FORCED_COVER_EX_DIV"
                        break
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
            # C4: if still locked at end of data, mark as locked (don't fabricate trade)
            if n > 0:
                last_bar_idx = n - 1
                prev_c = close[last_bar_idx - 1] if last_bar_idx > 0 else close[last_bar_idx]
                last_one_tick = (openp[last_bar_idx] == high[last_bar_idx] == low[last_bar_idx] == close[last_bar_idx])
                locked_long = last_one_tick and direction > 0 and openp[last_bar_idx] <= prev_c * 0.905
                locked_short = last_one_tick and direction < 0 and openp[last_bar_idx] >= prev_c * 1.095
                if locked_days > 0 and (locked_long or locked_short):
                    # still locked at end
                    exit_day = None
                    exit_price = None
                    exit_reason = "LOCKED_AT_END"
            if exit_day is None and exit_reason != "LOCKED_AT_END":
                exit_day = n - 1
                exit_price = close[n-1]
                exit_reason = "END_OF_DATA"

            # C4: if still locked at end, don't record as a completed trade
            if exit_reason == "LOCKED_AT_END":
                return

        # C3: dividend events during [entry_date, exit_date] (inclusive).
        # Convention: ex-date inside holding window counts; buying ON the ex-date is an
        # edge case ignored here (overestimates income by at most one ex-date per trade).
        # Shorts covering via the forced-cover rule exit BEFORE the ex-date, so they
        # owe no dividend compensation; shorts surviving to the ex-date pay it.
        div_per_share = 0.0
        div_events = []
        if (not no_dividend_income) and dividend_df is not None and not dividend_df.empty:
            try:
                entry_d = pd.to_datetime(dates[entry_day_actual])
                exit_d = pd.to_datetime(dates[exit_day])
                for _, dr in dividend_df.iterrows():
                    ex_d = pd.to_datetime(dr["ex_date"])
                    if entry_d <= ex_d <= exit_d:
                        amt = float(dr["cash_dividend"])
                        div_per_share += amt
                        div_events.append(f"{ex_d.date()}:{amt}")
            except Exception:
                pass

        # C4: limit up/down handling
        # Long: entry day 一字漲停 (open==high==close, >= +9.5%) -> can't buy -> UNFILLED
        if direction > 0:
            if openp[entry_day_actual] == high[entry_day_actual] == close[entry_day_actual] and openp[entry_day_actual] > 0:
                prev_c = close[entry_day_actual - 1] if entry_day_actual > 0 else close[entry_day_actual]
                if openp[entry_day_actual] >= prev_c * 1.095:
                    return  # limit up, can't buy
        # Short: entry day 一字跌停 (open==high==low==close, <= -9.5%) -> no supply to borrow/sell -> UNFILLED
        else:
            if openp[entry_day_actual] == high[entry_day_actual] == low[entry_day_actual] == close[entry_day_actual] and openp[entry_day_actual] > 0:
                prev_c = close[entry_day_actual - 1] if entry_day_actual > 0 else close[entry_day_actual]
                if openp[entry_day_actual] <= prev_c * 0.905:
                    return  # limit down, short sale unfilled

        # C3+C4: net R with dividend
        buy_fee = 0.001425
        sell_fee = 0.001425
        sell_tax = 0.003
        borrow_fee = 0.0
        if direction > 0:
            # Long: receive dividend (adds to exit value)
            gross_entry = entry_price * (1.0 + buy_fee)
            net_exit = exit_price * (1.0 - sell_fee - sell_tax) + div_per_share
            net_r = round((net_exit - gross_entry) / risk, 3)
        else:
            # Short (margin/borrow): pay dividend to lender (subtracts from P&L)
            # Taiwan tax 0.3% on SELL side only:
            #   Short entry = SELL → tax on entry
            #   Short cover = BUY → no tax on exit
            gross_entry = entry_price * (1.0 - buy_fee - sell_tax)
            net_exit = exit_price * (1.0 + buy_fee) + div_per_share
            # Borrow fee: annualized rate on shorted value, pro-rated by trading days held
            trade_days = max(1, exit_day - entry_day_actual + 1)
            borrow_fee = entry_price * short_borrow_fee_annual * (trade_days / 252.0)
            net_r = round((gross_entry - net_exit - borrow_fee) / risk, 3)

        # quality metadata for position selection
        leg_count = int(analyzed_df["Leg_Count"].iloc[sig_idx]) if "Leg_Count" in analyzed_df.columns else 0
        channel_type = str(analyzed_df["Channel_Type"].iloc[sig_idx]) if "Channel_Type" in analyzed_df.columns else "NONE"
        weekly_trend = str(analyzed_df["Weekly_Trend"].iloc[sig_idx]) if "Weekly_Trend" in analyzed_df.columns else "LONG"

        trades.append({
            "ticker": analyzed_df["Ticker"].iloc[0] if "Ticker" in analyzed_df.columns else "",
            "sig_date": dates[sig_idx],
            "sig_type": sig_type,
            "direction": "LONG" if direction > 0 else "SHORT",
            "entry_date": dates[entry_day_actual],
            # Reported prices are converted back to the raw traded scale (C1 FIX);
            # net_r/risk remain computed on the internally consistent adjusted scale.
            "entry_price": round(_to_raw(entry_day_actual, entry_price), 2),
            "stop_loss": round(_to_raw(sig_idx, stop), 2),
            "target": round(_to_raw(sig_idx, target), 2) if target and not (isinstance(target, float) and np.isnan(target)) else None,
            "exit_date": dates[exit_day],
            "exit_price": round(_to_raw(exit_day, exit_price), 2),
            "exit_reason": exit_reason,
            "days_held": int(days_held),
            "locked_days": int(locked_days),
            "net_r": net_r,
            "leg_count": leg_count,
            "channel_type": channel_type,
            "weekly_trend": weekly_trend,
            "dividend_cash": round(div_per_share, 4),
            "dividend_events": ";".join(div_events),
            "borrow_fee_cash": round(borrow_fee, 4),
            "forced_cover": bool(exit_reason == "FORCED_COVER_EX_DIV"),
            "initial_risk": round(float(risk), 4),
            "expected_div_delta_r": round((div_per_share / risk) * (1 if direction > 0 else -1), 4) if risk > 0 else 0.0,
        })

    # iterate signals
    for i in range(2, n - 1):
        row = analyzed_df.iloc[i]
        # H2 signal
        if strategy in ("h2", "all"):
            if bool(row.get("Signal_H2", False)):
                if key_level_only and not bool(analyzed_df["At_Key_Level"].iloc[i]):
                    continue
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
                if key_level_only and not bool(analyzed_df["At_Key_Level"].iloc[i]):
                    continue
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
                if key_level_only and not bool(analyzed_df["At_Key_Level"].iloc[i]):
                    continue
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
                    if exclude_climax and bool(row.get("Climax_Detected", False)):
                        continue
                    if key_level_only and not bool(analyzed_df["At_Key_Level"].iloc[i]):
                        continue
                    if min_leg_count and int(row.get("Leg_Count", 0)) < min_leg_count:
                        continue
                    if channel_only and "CHANNEL" not in str(row.get("Channel_Type", "")):
                        continue
                    if chip_filter and chip_df is not None:
                        sig_date = dates[i]
                        if not trust_buy_pass_for_date(chip_df, sig_date):
                            continue
                    if key_level_only and not bool(row.get("At_Key_Level", False)):
                        # check analyzed_df
                        if not bool(analyzed_df["At_Key_Level"].iloc[i]):
                            continue
                    direction = 1 if "BULL" in d else -1

                    if pullback_pct and pullback_pct > 0:
                        # Pullback entry: wait for price to pull back to pullback_price
                        risk = abs(float(entry) - float(stop))
                        if direction > 0:
                            pullback_price = float(entry) - risk * pullback_pct
                        else:
                            pullback_price = float(entry) + risk * pullback_pct
                        # search within window
                        triggered = False
                        entry_day = None
                        for w in range(1, pullback_window + 1):
                            j = i + w
                            if j >= n:
                                break
                            if direction > 0 and low[j] <= pullback_price:
                                triggered = True
                                entry_day = j
                                break
                            if direction < 0 and high[j] >= pullback_price:
                                triggered = True
                                entry_day = j
                                break
                        if not triggered:
                            continue
                        # entry at pullback price
                        pb_entry = pullback_price
                        # same-day stop check
                        exit_day = None
                        exit_price = None
                        exit_reason = None
                        pending_ema = False
                        days_held = 0
                        # C4: gap-through-stop check
                        if direction > 0 and openp[entry_day] < stop:
                            continue  # gap down, skip
                        if direction < 0 and openp[entry_day] > stop:
                            continue  # gap up, skip
                        if direction > 0 and low[entry_day] <= stop:
                            exit_day = entry_day
                            exit_price = min(openp[entry_day], stop)
                            exit_reason = "SAME_DAY_STOP"
                        elif direction < 0 and high[entry_day] >= stop:
                            exit_day = entry_day
                            exit_price = max(openp[entry_day], stop)
                            exit_reason = "SAME_DAY_STOP"
                        if exit_day is None:
                            track_start = entry_day + 1
                            trail_stop = stop
                            best_price = pb_entry
                            for j in range(track_start, n):
                                days_held += 1
                                if direction > 0:
                                    if close[j] > best_price:
                                        best_price = close[j]
                                    effective_stop = stop
                                else:
                                    if close[j] < best_price:
                                        best_price = close[j]
                                    effective_stop = stop
                                if pending_ema:
                                    exit_day = j; exit_price = openp[j]; exit_reason = "EXIT_EMA20"; break
                                if (direction > 0 and low[j] <= effective_stop) or (direction < 0 and high[j] >= effective_stop):
                                    exit_day = j
                                    exit_price = (min(openp[j], effective_stop) if direction > 0 else max(openp[j], effective_stop))
                                    exit_reason = "INITIAL_STOP"; break
                                if days_held >= max_hold:
                                    exit_day = j; exit_price = close[j]; exit_reason = "MAX_120D"; break
                                if (direction > 0 and close[j] < ema[j]) or (direction < 0 and close[j] > ema[j]):
                                    pending_ema = True
                                else:
                                    pending_ema = False
                        if exit_day is None:
                            # C4: check if still locked at end
                            last_idx = n - 1
                            prev_c = close[last_idx - 1] if last_idx > 0 else close[last_idx]
                            if openp[last_idx] == low[last_idx] == close[last_idx] and openp[last_idx] <= prev_c * 0.905:
                                continue  # locked at end, skip trade
                            exit_day = n - 1
                            exit_price = close[n-1]
                            exit_reason = "END_OF_DATA"
                        risk = abs(pb_entry - stop)
                        if risk <= 0:
                            continue
                        if direction > 0:
                            net_r = round(((exit_price * (1.0 - cost_rate)) - pb_entry) / risk, 3)
                        else:
                            net_r = round((pb_entry - (exit_price * (1.0 + cost_rate))) / risk, 3)
                        leg_count = int(analyzed_df["Leg_Count"].iloc[i]) if "Leg_Count" in analyzed_df.columns else 0
                        channel_type = str(analyzed_df["Channel_Type"].iloc[i]) if "Channel_Type" in analyzed_df.columns else "NONE"
                        weekly_trend = str(analyzed_df["Weekly_Trend"].iloc[i]) if "Weekly_Trend" in analyzed_df.columns else "LONG"
                        trades.append({
                            "ticker": analyzed_df["Ticker"].iloc[0] if "Ticker" in analyzed_df.columns else "",
                            "sig_date": dates[i],
                            "sig_type": "BOM_PB",
                            "direction": "LONG" if direction > 0 else "SHORT",
                            "entry_date": dates[entry_day],
                            "entry_price": round(float(pb_entry), 2),
                            "stop_loss": round(float(stop), 2),
                            "target": round(float(target), 2) if target and not (isinstance(target, float) and np.isnan(target)) else None,
                            "exit_date": dates[exit_day],
                            "exit_price": round(float(exit_price), 2),
                            "exit_reason": exit_reason,
                            "days_held": int(days_held),
                            "locked_days": 0,
                            "net_r": net_r,
                            "leg_count": leg_count,
                            "channel_type": channel_type,
                            "weekly_trend": weekly_trend,
                            "dividend_cash": 0.0,
                            "dividend_events": "",
                            "initial_risk": round(float(risk), 4),
                            "expected_div_delta_r": 0.0,
                        })
                    else:
                        record(i, float(entry), float(stop), float(target) if pd.notna(target) else None, direction, "BOM")

    return trades


def compute_metrics(trades):
    if not trades:
        return {}
    df = pd.DataFrame(trades)
    # H2 FIX (CRITICAL): drawdown MUST be computed on a time-ordered equity curve.
    # `trades` is appended ticker-by-ticker, so the previous unsorted cumulative sum
    # produced a meaningless "max drawdown" (e.g. the reported -145R).
    df = df.sort_values(["exit_date", "entry_date", "ticker"], kind="mergesort").reset_index(drop=True)
    n = len(df)
    wins = df[df["net_r"] > 0]
    losses = df[df["net_r"] <= 0]
    win_rate = len(wins) / n
    avg_win = wins["net_r"].mean() if len(wins) > 0 else 0
    avg_loss = losses["net_r"].mean() if len(losses) > 0 else 0
    expectancy = df["net_r"].mean()
    profit_factor = (wins["net_r"].sum() / abs(losses["net_r"].sum())) if len(losses) > 0 and losses["net_r"].sum() != 0 else float("inf")
    # max drawdown on a TIME-ORDERED cumulative R curve (start from 0)
    cum = pd.concat([pd.Series([0.0]), df["net_r"].reset_index(drop=True)], ignore_index=True).cumsum()
    peak = cum.cummax()
    dd = cum - peak
    max_dd = dd.min()
    # longest losing streak (time-ordered)
    max_loss_streak = 0
    cur_streak = 0
    for r in df["net_r"].tolist():
        if r <= 0:
            cur_streak += 1
            max_loss_streak = max(max_loss_streak, cur_streak)
        else:
            cur_streak = 0
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
        "note": "profit_factor = total_win_R / abs(total_loss_R), NOT avg_win/avg_loss ratio",
        "total_r": round(float(df["net_r"].sum()), 3),
        "max_drawdown_r": round(float(max_dd), 3),
        "max_loss_streak": int(max_loss_streak),
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
    parser.add_argument("--cache-only", action="store_true", help="use cached data only, no API calls")
    parser.add_argument("--priority-tickers", type=str, default="", help="comma-separated priority tickers (shorter cache)")
    parser.add_argument("--priority-file", type=str, default="", help="file with priority tickers (one per line)")
    parser.add_argument("--refresh-signals", action="store_true", help="refresh only tickers found in scan_result.json signals")
    parser.add_argument("--priority-max-age", type=int, default=1, help="cache max age (hours) for priority tickers")
    parser.add_argument("--min-rr", type=float, default=0.0, help="minimum risk/reward ratio filter")
    parser.add_argument("--max-risk-pct", type=float, default=100.0, help="max risk pct per trade filter")
    parser.add_argument("--mtr-confirmed-only", action="store_true", help="only take MTR_Confirmed signals")
    parser.add_argument("--exit-mode", type=str, default="v1", choices=["v1", "trailing"], help="exit mode")
    parser.add_argument("--trail-mult", type=float, default=1.0, help="trailing stop ATR multiple")
    parser.add_argument("--pullback-entry", action="store_true", help="BOM pullback entry (buy the dip)")
    parser.add_argument("--pullback-pct", type=float, default=0.5, help="pullback depth (0.5 = 50 percent of risk)")
    parser.add_argument("--pullback-window", type=int, default=5, help="days to wait for pullback")
    parser.add_argument("--include-climax", action="store_true", help="include BOM signals on climax bars (default: excluded)")
    parser.add_argument("--key-level-only", action="store_true", help="only trade signals at key levels (Brooks)")
    parser.add_argument("--no-dividend", action="store_true", help="disable dividend adjustment (use raw prices only)")
    parser.add_argument("--no-dividend-income", action="store_true", help="disable dividend income in returns (adjusted prices only)")
    parser.add_argument("--short-borrow-fee-annual", type=float, default=0.05, help="annualized borrow fee for short positions, pro-rated by trading days (default 0.05)")
    parser.add_argument("--no-forced-cover", action="store_true", help="borrow mode: shorts may hold across ex-dividend (paying dividend compensation and borrow fee); default is margin mode with forced cover before ex-date")
    parser.add_argument("--no-adjustment", action="store_true", help="disable price adjustment (raw prices for signals, dividend income only)")
    parser.add_argument("--chip-filter", action="store_true", help="filter BOM signals by institutional (trust) buy")
    parser.add_argument("--min-leg-count", type=int, default=0, help="minimum Leg_Count filter (0 = no filter)")
    parser.add_argument("--channel-only", action="store_true", help="only trade BOM in channels (BULL/BEAR_CHANNEL)")
    parser.add_argument("--max-positions", type=int, default=0, help="max concurrent positions (0 = unlimited)")
    parser.add_argument("--disable-mtf", action="store_true", help="disable multi-timeframe filter")
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

    if args.disable_mtf:
        config.MTF_ENABLED = False
    print(f"Backtest: {len(tickers)} tickers ({len(priority)} priority), {args.start} ~ {args.end}, strategy={args.strategy}")

    all_trades = []
    for idx, ticker in enumerate(tickers):
        print(f"[{idx+1}/{len(tickers)}] {ticker} ...", end=" ", flush=True)
        try:
            is_priority = ticker in priority
            if args.cache_only:
                df = load_cached(ticker, max_age_hours=99999)
                if df is None or df.empty:
                    print("NO CACHE")
                    continue
            elif args.no_cache:
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
            df_raw = df.copy() if False else None
            df = df.copy()
            # fetch chips if chip filter enabled
            chip_df = None
            if args.chip_filter:
                chip_start = (pd.to_datetime(args.start) - pd.Timedelta(days=20)).strftime("%Y-%m-%d")
                if args.no_cache:
                    chip_df = fetch_chips_history(ticker, chip_start, args.end, rate_limit=False)
                else:
                    chip_df = fetch_chips_history(ticker, chip_start, args.end)

            # fetch dividends for corporate action adjustment (C3)
            from data_fetcher import fetch_dividends as _fd, adjust_for_dividends
            div_df = None
            _div_cache = os.path.join("dividend_cache", f"{ticker.replace('.', '_')}.csv")
            if os.path.exists(_div_cache):
                try:
                    _ddf = pd.read_csv(_div_cache)
                    if not _ddf.empty:
                        div_df = _ddf
                except Exception:
                    pass
            if div_df is None and not args.no_dividend and not (args.no_adjustment and args.no_dividend):
                if not args.cache_only:
                    time.sleep(RATE_LIMIT_SEC)
                    div_df = _fd(ticker, lookback_days=args.lookback)
                    if div_df is not None and not (isinstance(div_df, pd.DataFrame) and div_df.empty):
                        os.makedirs("dividend_cache", exist_ok=True)
                        div_df.to_csv(_div_cache, index=False, encoding="utf-8-sig")
                    else:
                        div_df = None
            if args.no_dividend:
                div_df = None

            # --- C1 FIX (CRITICAL): price-scale consistency ---
            # Previously the raw (un-adjusted) OHLC was written back into `analyzed`
            # while EMA_20 / ATR / Stop_Loss stayed on the dividend-adjusted scale.
            # Comparing a raw Close against an adjusted EMA is a unit mismatch that
            # silently shifted every EXIT_EMA20 trigger for dividend-paying stocks.
            #
            # Resolution: keep the ENTIRE simulation on one scale.
            #   * Signals AND indicator/execution prices use the dividend-adjusted frame
            #     (self-consistent; the back-adjustment already removed ex-div gaps).
            #   * Only the REPORTED entry/stop/target values are converted back to the
            #     raw traded scale so the trade log stays readable / comparable.
            # C1 FIX (CRITICAL): price-scale consistency.
            # The ENTIRE simulation runs on one scale:
            #   * default (C/B): dividend-adjusted frame for signals AND execution;
            #     reported prices converted back to raw scale via _price_offset
            #   * --no-adjustment (D/A): raw frame for signals AND execution
            #     (dividends used ONLY for income + margin-short forced cover)
            if args.no_adjustment or args.no_dividend or div_df is None or (isinstance(div_df, pd.DataFrame) and div_df.empty):
                df_adj = df.copy()
                if not args.no_adjustment:
                    div_df = None
                price_offset = pd.Series(0.0, index=df.index)
            else:
                df_adj = adjust_for_dividends(df, div_df)
                # cumulative dividends with ex_date > date[i] == (adjusted - raw)
                ex_dates, div_amts = [], []
                for _, dr in div_df.iterrows():
                    try:
                        ex_dates.append(pd.to_datetime(dr["ex_date"]))
                        div_amts.append(float(dr["cash_dividend"]))
                    except Exception:
                        pass
                linked = [sum(amt for ed, amt in zip(ex_dates, div_amts) if ed > d)
                          for d in pd.to_datetime(df_adj["Date"])]
                price_offset = pd.Series(linked, index=df_adj.index)

            # run engine on the single consistent frame
            analyzed = PriceActionEngine.analyze_setups(df_adj)
            analyzed["Ticker"] = ticker
            analyzed["Date"] = pd.to_datetime(analyzed["Date"])
            # carry the raw-scale offset so reported prices can be de-adjusted later
            analyzed["_price_offset"] = price_offset.to_numpy(dtype=float)
            trades = simulate_trades(analyzed, strategy=args.strategy, min_rr=args.min_rr,
                                    max_risk_pct=args.max_risk_pct, mtr_confirmed_only=args.mtr_confirmed_only,
                                    exit_mode=args.exit_mode, trail_mult=args.trail_mult,
                                    exclude_climax=not args.include_climax,
                                    min_leg_count=args.min_leg_count,
                                    channel_only=args.channel_only,
                                    chip_df=chip_df, chip_filter=args.chip_filter,
                                    pullback_pct=(args.pullback_pct if args.pullback_entry else 0.0),
                                    pullback_window=args.pullback_window,
                                    key_level_only=args.key_level_only,
                                    dividend_df=(None if args.no_dividend else div_df),
                                    short_borrow_fee_annual=args.short_borrow_fee_annual,
                                    forced_cover=not args.no_forced_cover,
                                    no_dividend_income=args.no_dividend_income)
            # filter trades by sig_date range
            filtered = [t for t in trades if args.start <= t["sig_date"] <= args.end]
            all_trades.extend(filtered)
            print(f"trades={len(filtered)}")
        except Exception as e:
            print(f"ERROR: {e}")

    if not all_trades:
        print("No trades generated.")
        return

    # Position limit simulation (max concurrent positions)
    if args.max_positions and args.max_positions > 0:
        # Quality score: higher = better (leg_count*2 - risk_pct + channel bonus)
        for t in all_trades:
            risk_pct = abs(t["entry_price"] - t["stop_loss"]) / t["entry_price"] * 100 if t["entry_price"] > 0 else 999
            channel_bonus = 1.0 if "CHANNEL" in str(t.get("channel_type", "")) else 0.0
            t["_quality"] = float(t.get("leg_count", 0)) * 2.0 - risk_pct + channel_bonus

        # Sort by entry_date, then quality descending (best first)
        sorted_trades = sorted(all_trades, key=lambda t: (t["entry_date"], -t["_quality"]))

        selected = []
        for cand in sorted_trades:
            cand_entry = cand["entry_date"]
            # M2 FIX: guard against empty/NaN exit_date (open trades) and compare
            # only against positions that actually overlap in time.
            open_count = 0
            for s in selected:
                s_exit = s.get("exit_date") or ""
                if not s_exit:
                    continue  # unknown exit -> cannot overlap-count reliably
                if s["entry_date"] <= cand_entry <= s_exit:
                    open_count += 1
            if open_count < args.max_positions:
                selected.append(cand)
        for t in selected:
            t.pop("_quality", None)
        all_trades = selected
        print(f"Position limit {args.max_positions}: {len(sorted_trades)} -> {len(all_trades)} trades kept")

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
