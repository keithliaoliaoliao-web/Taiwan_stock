"""
scanner.py
任務 K - C 組 (突破 20 日高) 前瞻紙上交易掃描器 (重建版)
版面標註：【觀察用，未經實證驗證】

進出場規則、成本、分割偵測與舊版完全相同 (下方「核心規則」區塊直接沿用)。
與舊版的差別只有：
  1. 一律用台灣時間判斷，並考慮休市日
  2. 漏跑補算時，連「那幾天的新訊號」也一起補
  3. 持倉中的股票即使被移出觀察池，也會繼續追蹤到出場
  4. 資料沒到位時：最後一次嘗試會讓工作顯示紅叉，不再假裝成功
  5. 每個新訊號多記一欄 avg_turnover_20d (近 20 日平均成交額，只記錄不篩選)
  6. 輸出 dashboard_data.json 給網頁讀取
"""

import argparse
import csv
import json
import os
import re
import sys
import time

import numpy as np
import pandas as pd

from data_fetcher import fetch_history, get_expected_latest_trading_date, now_tw
from taiwan_market_rules import next_tick_price, previous_tick_price

LEDGER_FILE = "paper_trading_ledger.csv"
WATCHLIST_FILE = "watchlist.csv"
DASHBOARD_FILE = "dashboard_data.json"
COST_RATE = 0.00585  # 回測基準：稅 0.003 + 手續費 0.001425 * 2
ACTUAL_FEE_DESC = "稅0.3% + 手續費0.1425%*2 (回測基準，無折扣無低消)"
LOOKBACK_DAYS = 500
MIN_LOAD_RATIO = 0.95
ACTIVE_STATUSES = ["OPEN", "PENDING", "NEEDS_REVIEW"]


def get_actual_fee_params() -> dict:
    return {"desc": ACTUAL_FEE_DESC}


def calc_actual_net_r(entry_price, exit_price, risk_per_share, rule_net_r):
    """未設定自訂券商費率：actual_net_r 嚴格等於 rule_net_r"""
    return rule_net_r


# ==========================================
# 核心規則 (沿用舊版，未更動)
# ==========================================
# ==========================================
# 1. 檔位運算 (凍結規格)
# ==========================================
# tick 函式統一使用 taiwan_market_rules.py 的版本
# ==========================================
# 2. 資料清洗與還原 (凍結規格)
# ==========================================
def adjust_corporate_actions(df: pd.DataFrame) -> tuple:
    df = df.copy().sort_values("Date").reset_index(drop=True)
    n = len(df)
    adj_factor = np.ones(n)
    split_events = {}

    for i in range(1, n):
        prev_c = float(df.loc[i - 1, "Close"])
        cur_o = float(df.loc[i, "Open"])
        if prev_c > 0 and cur_o > 0 and (cur_o / prev_c) < 0.70:
            ratio = cur_o / prev_c
            adj_factor[:i] *= ratio
            d_str = pd.to_datetime(df.loc[i, "Date"]).strftime("%Y-%m-%d")
            split_events[d_str] = round(ratio, 4)

    for col in ["Open", "High", "Low", "Close"]:
        if col in df.columns:
            df[col] = (df[col] * adj_factor).round(2)

    return df, split_events


def clean_stock_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy().sort_values("Date").reset_index(drop=True)
    cleaned_rows = []

    for idx, row in df.iterrows():
        o = float(row.get("Open", 0))
        h = float(row.get("High", 0))
        l = float(row.get("Low", 0))
        c = float(row.get("Close", 0))

        has_vol = "Volume" in row and pd.notna(row["Volume"])
        v = float(row["Volume"]) if has_vol else 1.0

        if (o <= 0 and c <= 0) or (has_vol and v <= 0):
            continue

        if o <= 0 and c > 0:
            if cleaned_rows:
                row["Open"] = float(cleaned_rows[-1]["Close"])
            else:
                row["Open"] = c

        cleaned_rows.append(row)

    return pd.DataFrame(cleaned_rows).reset_index(drop=True)


def prepare_stock_data(raw_df: pd.DataFrame) -> tuple:
    if raw_df.empty or len(raw_df) < 22:
        return pd.DataFrame(), {}
    df, split_events = adjust_corporate_actions(raw_df)
    df = clean_stock_data(df)
    if len(df) < 22:
        return pd.DataFrame(), {}
    df["DateStr"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")
    df["EMA_20"] = df["Close"].ewm(span=20, adjust=False).mean()
    return df, split_events



# ==========================================
# 3. 核心訊號掃描 (凍結規格)
# ==========================================
def scan_signals_for_ticker(df: pd.DataFrame, ticker: str, as_of_date: str = None) -> dict:
    if df.empty or len(df) < 22:
        return None

    if as_of_date is not None:
        matches = df.index[df["DateStr"] <= as_of_date]
        if len(matches) < 22:
            return None
        cur_idx = matches[-1]
    else:
        cur_idx = len(df) - 1

    if cur_idx < 20:
        return None

    cur_bar = df.iloc[cur_idx]
    sig_date = cur_bar["DateStr"]

    c_above_ema = bool(cur_bar["Close"] >= cur_bar["EMA_20"])
    prev_20_high = float(df["High"].iloc[cur_idx - 20 : cur_idx].max())
    c_break_20h = bool(cur_bar["High"] > prev_20_high)

    if not (c_above_ema and c_break_20h):
        return None

    high = float(cur_bar["High"])
    low = float(cur_bar["Low"])
    close = float(cur_bar["Close"])
    trigger_price = next_tick_price(high)
    stop_price = previous_tick_price(low)
    risk_pct = round(((trigger_price - stop_price) / trigger_price) * 100, 2)

    return {
        "ticker": ticker,
        "signal_date": sig_date,
        "close": close,
        "high": high,
        "low": low,
        "prev_20_high": prev_20_high,
        "ema_20": round(float(cur_bar["EMA_20"]), 2),
        "trigger_price": trigger_price,
        "stop_price": stop_price,
        "risk_pct": risk_pct
    }


# ==========================================
# 4. 帳本狀態管理、時序撮合與手動解除指令
# ==========================================
def load_ledger(filepath: str = LEDGER_FILE) -> pd.DataFrame:
    cols = [
        "signal_date", "ticker", "trigger_price", "stop_price", "risk_pct",
        "triggered", "entry_price", "entry_date", "exit_date", "exit_price", "exit_reason",
        "rule_net_r", "actual_net_r", "slippage_net_r", "actual_fee_settings", "status",
        "days_held", "pending_ema_exit", "last_processed_date", "source",
        "avg_turnover_20d"
    ]
    str_cols = [
        "signal_date", "ticker", "entry_date", "exit_date",
        "exit_reason", "actual_fee_settings", "status", "last_processed_date", "source"
    ]
    if os.path.exists(filepath):
        df = pd.read_csv(filepath, dtype={c: object for c in str_cols})
        if "actual_net_r" not in df.columns:
            df["actual_net_r"] = df.get("rule_net_r", np.nan)
        if "source" not in df.columns:
            df["source"] = "LIVE"
        for c in str_cols:
            if c in df.columns:
                df[c] = df[c].astype(object).fillna("")
        for col in cols:
            if col not in df.columns:
                df[col] = "" if col in str_cols else np.nan
        return df[cols]
    df_empty = pd.DataFrame(columns=cols)
    for c in str_cols:
        df_empty[c] = df_empty[c].astype(object)
    return df_empty


def save_ledger(df: pd.DataFrame, filepath: str = LEDGER_FILE):
    df.to_csv(filepath, index=False, encoding="utf-8-sig")


def print_needs_review_alert(ledger: pd.DataFrame, ledger_path: str = LEDGER_FILE):
    print("\n" + "=" * 68)
    print("【需人工處理部位 (NEEDS_REVIEW) 檢查區塊】")
    print("=" * 68)
    if ledger.empty or "status" not in ledger.columns:
        print("目前無任何 NEEDS_REVIEW 部位。")
        return

    nr_df = ledger[ledger["status"].astype(str) == "NEEDS_REVIEW"]
    if nr_df.empty:
        print("目前無任何 NEEDS_REVIEW 部位。")
        return

    print(f"!!! 警告：共有 {len(nr_df)} 筆部位因偵測到分割/減資事件處於 NEEDS_REVIEW 凍結狀態 !!!")
    cols_show = ["ticker", "signal_date", "entry_date", "entry_price", "stop_price", "days_held", "exit_reason"]
    avail_cols = [c for c in cols_show if c in nr_df.columns]
    print(nr_df[avail_cols].to_string(index=False))
    print("\n請選擇以下任一指令進行人工解除：")
    for _, r in nr_df.iterrows():
        tk = r["ticker"]
        print(f"  [選項 A - 依分割比例調整後繼續持有]:")
        print(f"    python scanner.py --resolve {tk} --action adjust --ledger {ledger_path}")
        print(f"  [選項 B - 以人工填入價格結案出場]:")
        print(f"    python scanner.py --resolve {tk} --action close --price <出場價> --date <YYYY-MM-DD> --ledger {ledger_path}")
    print("=" * 68)


def resolve_needs_review_position(
    ticker: str,
    action: str,
    exit_price: float = None,
    exit_date: str = None,
    ledger_path: str = LEDGER_FILE,
    scale_prices_on_adjust: bool = True
) -> bool:
    ledger = load_ledger(ledger_path)
    if ledger.empty:
        print(f"【解除失敗】帳本為空: {ledger_path}")
        return False

    mask = (ledger["ticker"].astype(str) == str(ticker)) & (ledger["status"].astype(str) == "NEEDS_REVIEW")
    if not mask.any():
        print(f"【解除失敗】找不到標的 {ticker} 處於 NEEDS_REVIEW 狀態的部位！")
        return False

    idx = ledger[mask].index[-1]
    row = ledger.loc[idx].copy()
    orig_last_processed = row["last_processed_date"]
    reason_str = str(row.get("exit_reason", ""))

    m = re.search(r"ratio=([0-9.]+)", reason_str)
    ratio = float(m.group(1)) if m else 1.0
    fee_desc = get_actual_fee_params()["desc"]

    if action == "close":
        if exit_price is None or not exit_date:
            print("【解除失敗】--action close 必須同時指定 --price 與 --date！")
            return False

        entry_p = float(row["entry_price"])
        stop_p = float(row["stop_price"])
        exit_p = float(exit_price)
        risk_per_share = entry_p - stop_p
        if risk_per_share <= 0:
            print(f"【解除失敗】每股風險異常 (entry={entry_p}, stop={stop_p})！")
            return False

        rule_r = round(((exit_p * (1.0 - COST_RATE)) - entry_p) / risk_per_share, 3)
        act_r = calc_actual_net_r(entry_p, exit_p, risk_per_share, rule_r)
        slip_entry = next_tick_price(entry_p)
        slip_exit = previous_tick_price(exit_p)
        slip_r = round(((slip_exit * (1.0 - COST_RATE)) - slip_entry) / risk_per_share, 3)

        ledger.loc[idx, "status"] = "CLOSED"
        ledger.loc[idx, "exit_date"] = str(exit_date)
        ledger.loc[idx, "exit_price"] = exit_p
        ledger.loc[idx, "exit_reason"] = f"MANUAL_RESOLVE({reason_str})" if reason_str else "MANUAL_RESOLVE"
        ledger.loc[idx, "rule_net_r"] = rule_r
        ledger.loc[idx, "actual_net_r"] = act_r
        ledger.loc[idx, "slippage_net_r"] = slip_r
        ledger.loc[idx, "actual_fee_settings"] = str(row.get("actual_fee_settings", fee_desc)) + " | MANUAL_RESOLVE"
        ledger.loc[idx, "last_processed_date"] = orig_last_processed

        save_ledger(ledger, ledger_path)
        print(f"【手動解除成功 - CLOSE】{ticker} 已於 {exit_date} 以 ${exit_p} 結案 | 淨R: {rule_r:+.3f}R (實際成本淨R: {act_r:+.3f}R) | last_processed_date 維持: {orig_last_processed}")
        return True

    elif action == "adjust":
        if scale_prices_on_adjust and ratio > 0 and ratio != 1.0:
            ledger.loc[idx, "trigger_price"] = round(float(row["trigger_price"]) * ratio, 2)
            ledger.loc[idx, "stop_price"] = round(float(row["stop_price"]) * ratio, 2)
            if pd.notna(row["entry_price"]) and str(row["entry_price"]) != "":
                ledger.loc[idx, "entry_price"] = round(float(row["entry_price"]) * ratio, 2)

        was_triggered = bool(row.get("triggered", True)) and pd.notna(row.get("entry_price"))
        ledger.loc[idx, "status"] = "OPEN" if was_triggered else "PENDING"
        ledger.loc[idx, "exit_reason"] = ""
        ledger.loc[idx, "actual_fee_settings"] = str(row.get("actual_fee_settings", fee_desc)) + f" | MANUAL_RESOLVE_ADJUST(ratio={ratio})"
        ledger.loc[idx, "last_processed_date"] = orig_last_processed

        save_ledger(ledger, ledger_path)
        print(
            f"【手動解除成功 - ADJUST】{ticker} 已依分割比例 ({ratio}) 調整價格並恢復為 {ledger.loc[idx, 'status']} | "
            f"新進場價: {ledger.loc[idx, 'entry_price']} | 新停損價: {ledger.loc[idx, 'stop_price']} | 新觸發價: {ledger.loc[idx, 'trigger_price']} | "
            f"last_processed_date 維持: {orig_last_processed}"
        )
        return True

    else:
        print(f"【解除失敗】不支援的 action: {action} (請使用 close 或 adjust)")
        return False


def update_ledger_single_day(
    ledger: pd.DataFrame,
    stock_map: dict,
    today_str: str,
    split_map: dict = None,
    freeze_on_split: bool = True,
    replay_auto_resolve_splits: bool = False,
    target_ticker: str = None,
    missing_out: list = None
) -> tuple:
    if ledger.empty:
        return ledger, set()

    if split_map is None:
        split_map = {}

    updated_rows = []
    tickers_exited_today = set()
    fee_desc = get_actual_fee_params()["desc"]
    if missing_out is None:
        missing_out = []

    for _, row in ledger.iterrows():
        t = str(row["ticker"])
        if target_ticker is not None and t != target_ticker:
            updated_rows.append(row)
            continue

        status = str(row["status"])
        df = stock_map.get(t, pd.DataFrame())

        if status in ["CLOSED", "UNTRIGGERED", "NEEDS_REVIEW"]:
            updated_rows.append(row)
            continue
        if df.empty:
            # 股票不在 stock_map 中（無資料）→ 視為缺棒
            missing_out.append(t)
            if status == "PENDING":
                row["status"] = "UNTRIGGERED"
                row["exit_reason"] = "NO_BAR_ON_TARGET_DAY"
                row["last_processed_date"] = today_str
                updated_rows.append(row)
                continue
            # OPEN 遇到無 K 棒：跳過但記錄
            updated_rows.append(row)
            continue

        if freeze_on_split and status in ["OPEN", "PENDING"]:
            t_splits = split_map.get(t, {})
            sig_d_str = str(row.get("signal_date", ""))
            triggered_splits = [(sd, sr) for sd, sr in sorted(t_splits.items()) if sd > sig_d_str]
            is_split_hit = (today_str in t_splits) if replay_auto_resolve_splits else (today_str in t_splits or bool(triggered_splits))
            if is_split_hit:
                s_date, s_ratio = (today_str, t_splits[today_str]) if today_str in t_splits else triggered_splits[0]
                row["status"] = "NEEDS_REVIEW"
                row["exit_reason"] = f"SPLIT_DETECTED(date={s_date},ratio={s_ratio})"
                row["last_processed_date"] = today_str

                if replay_auto_resolve_splits:
                    was_trig = bool(row.get("triggered", True)) and pd.notna(row.get("entry_price"))
                    row["status"] = "OPEN" if was_trig else "PENDING"
                    row["exit_reason"] = ""
                    row["actual_fee_settings"] = str(row.get("actual_fee_settings", fee_desc)) + f" | AUTO_RESOLVE_ADJUST(date={s_date},ratio={s_ratio})"
                    status = str(row["status"])
                else:
                    updated_rows.append(row)
                    continue

        today_bar_matches = df[df["DateStr"] == today_str]
        if today_bar_matches.empty:
            missing_out.append(t)
            if status == "PENDING":
                # PENDING 遇到無 K 棒：視為掛單失效，不延到隔天
                row["status"] = "UNTRIGGERED"
                row["exit_reason"] = "NO_BAR_ON_TARGET_DAY"
                row["last_processed_date"] = today_str
                updated_rows.append(row)
                continue
            # OPEN 遇到無 K 棒：跳過但記錄，不更新 last_processed_date
            updated_rows.append(row)
            continue

        today_bar = today_bar_matches.iloc[0]
        cur_open = float(today_bar["Open"])
        cur_high = float(today_bar["High"])
        cur_low = float(today_bar["Low"])
        cur_close = float(today_bar["Close"])
        cur_ema = float(today_bar["EMA_20"])

        trigger_price = float(row["trigger_price"])
        stop_price = float(row["stop_price"])

        if status == "PENDING":
            if cur_high >= trigger_price:
                entry_price = max(trigger_price, cur_open)
                risk_per_share = entry_price - stop_price
                row["triggered"] = True
                row["entry_price"] = entry_price
                row["entry_date"] = today_str
                row["days_held"] = 0

                if cur_low <= stop_price:
                    exit_price = min(cur_open, stop_price)
                    row["exit_date"] = today_str
                    row["exit_price"] = exit_price
                    row["exit_reason"] = "SAME_DAY_STOP"
                    row["status"] = "CLOSED"
                    r_rule = round(((exit_price * (1.0 - COST_RATE)) - entry_price) / risk_per_share, 3)
                    row["rule_net_r"] = r_rule
                    row["actual_net_r"] = calc_actual_net_r(entry_price, exit_price, risk_per_share, r_rule)
                    slip_entry = next_tick_price(entry_price)
                    slip_exit = previous_tick_price(exit_price)
                    row["slippage_net_r"] = round(((slip_exit * (1.0 - COST_RATE)) - slip_entry) / risk_per_share, 3)
                    tickers_exited_today.add(t)
                else:
                    row["status"] = "OPEN"
                    row["pending_ema_exit"] = False
            else:
                row["triggered"] = False
                row["status"] = "UNTRIGGERED"
                row["exit_reason"] = "UNTRIGGERED"

            row["last_processed_date"] = today_str
            updated_rows.append(row)
            continue

        if status == "OPEN":
            days_held = int(row["days_held"]) + 1
            row["days_held"] = days_held
            pending_ema = bool(row["pending_ema_exit"])
            entry_price = float(row["entry_price"])
            risk_per_share = entry_price - stop_price

            is_closed = False
            exit_price = 0.0
            exit_reason = ""

            if pending_ema:
                is_closed = True
                exit_price = cur_open
                exit_reason = "EXIT_EMA20"
            elif cur_low <= stop_price:
                is_closed = True
                exit_price = min(cur_open, stop_price)
                exit_reason = "INITIAL_STOP"
            elif days_held >= 120:
                is_closed = True
                exit_price = cur_close
                exit_reason = "MAX_120D"

            if is_closed:
                row["status"] = "CLOSED"
                row["exit_date"] = today_str
                row["exit_price"] = exit_price
                row["exit_reason"] = exit_reason
                r_rule = round(((exit_price * (1.0 - COST_RATE)) - entry_price) / risk_per_share, 3)
                row["rule_net_r"] = r_rule
                row["actual_net_r"] = calc_actual_net_r(entry_price, exit_price, risk_per_share, r_rule)
                slip_entry = next_tick_price(entry_price)
                slip_exit = previous_tick_price(exit_price)
                row["slippage_net_r"] = round(((slip_exit * (1.0 - COST_RATE)) - slip_entry) / risk_per_share, 3)
                tickers_exited_today.add(t)
            else:
                if cur_close < cur_ema:
                    row["pending_ema_exit"] = True
                else:
                    row["pending_ema_exit"] = False

            row["last_processed_date"] = today_str
            updated_rows.append(row)

    return pd.DataFrame(updated_rows), tickers_exited_today


# ==========================================
# 新增部分：觀察池、成交額、每日流程、網頁資料
# ==========================================
def load_watchlist(path: str = WATCHLIST_FILE) -> dict:
    meta = {}
    with open(path, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            t = (r.get("ticker") or "").strip()
            if t:
                meta[t] = {
                    "name": (r.get("name") or t).strip(),
                    "sector": (r.get("sector") or "").strip(),
                    "basket": (r.get("basket") or "").strip(),
                }
    return meta


def calc_avg_turnover(df: pd.DataFrame, as_of: str):
    """近 20 個交易日平均成交金額 (元)；只用來記錄，不用來篩選"""
    sub = df[df["DateStr"] <= as_of].tail(20)
    if sub.empty:
        return np.nan
    if "Trading_money" in sub.columns:
        money = pd.to_numeric(sub["Trading_money"], errors="coerce")
    else:
        money = pd.to_numeric(sub["Close"], errors="coerce") * pd.to_numeric(sub.get("Volume"), errors="coerce")
    val = money.mean()
    return round(float(val)) if pd.notna(val) else np.nan


def scan_today(df: pd.DataFrame, ticker: str, d: str):
    """只接受「訊號日 == d」的訊號 (停牌股的舊 K 棒不會被當成今天的訊號)"""
    sig = scan_signals_for_ticker(df, ticker, as_of_date=d)
    if not sig or sig["signal_date"] != d:
        return None
    sig["avg_turnover_20d"] = calc_avg_turnover(df, d)
    return sig


def _sanitize(o):
    if isinstance(o, dict):
        return {str(k): _sanitize(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_sanitize(v) for v in o]
    if isinstance(o, (bool, np.bool_)):
        return bool(o)
    if isinstance(o, (int, np.integer)):
        return int(o)
    if isinstance(o, (float, np.floating)):
        return None if (np.isnan(o) or np.isinf(o)) else float(o)
    if o is None or o is pd.NaT:
        return None
    return o if isinstance(o, str) else str(o)


def _records(df: pd.DataFrame) -> list:
    return [_sanitize(r) for r in df.to_dict("records")]


def _stats(closed: pd.DataFrame) -> dict:
    r = pd.to_numeric(closed["rule_net_r"], errors="coerce").dropna()
    if r.empty:
        return {"n": 0, "win_rate": None, "avg_r": None, "total_r": None}
    return {
        "n": int(len(r)),
        "win_rate": round(float((r > 0).mean() * 100), 1),
        "avg_r": round(float(r.mean()), 3),
        "total_r": round(float(r.sum()), 3),
    }


def build_dashboard(ledger, stock_map, meta, target, universe) -> dict:
    led = ledger.copy()
    for c in ["entry_price", "stop_price", "trigger_price", "exit_price", "risk_pct", "rule_net_r",
              "actual_net_r", "slippage_net_r", "days_held", "avg_turnover_20d"]:
        if c in led.columns:
            led[c] = pd.to_numeric(led[c], errors="coerce")
    led["name"] = led["ticker"].astype(str).map(lambda t: meta.get(t, {}).get("name", t))

    closed = led[led["status"] == "CLOSED"]
    pending = led[led["status"] == "PENDING"]
    review = led[led["status"] == "NEEDS_REVIEW"]
    opened = led[led["status"] == "OPEN"].copy()

    last_close, last_ema, unreal = [], [], []
    for _, r in opened.iterrows():
        df = stock_map.get(str(r["ticker"]))
        sub = df[df["DateStr"] <= target] if df is not None else pd.DataFrame()
        if sub.empty:
            last_close.append(np.nan); last_ema.append(np.nan); unreal.append(np.nan)
            continue
        c, e = float(sub["Close"].iloc[-1]), float(sub["EMA_20"].iloc[-1])
        risk = float(r["entry_price"]) - float(r["stop_price"])
        last_close.append(c); last_ema.append(round(e, 2))
        unreal.append(round((c * (1 - COST_RATE) - float(r["entry_price"])) / risk, 3) if risk > 0 else np.nan)
    opened["last_close"], opened["last_ema20"], opened["unrealized_r"] = last_close, last_ema, unreal

    watch, stale = [], []
    for t in sorted(universe):
        df = stock_map.get(t)
        if df is None:
            continue
        sub = df[df["DateStr"] <= target]
        if len(sub) < 22:
            continue
        cur = sub.iloc[-1]
        prev20 = float(sub["High"].iloc[-21:-1].max())
        close, ema, high = float(cur["Close"]), float(cur["EMA_20"]), float(cur["High"])
        above, brk = close >= ema, high > prev20
        dist = (prev20 - close) / prev20 * 100 if prev20 > 0 else np.nan
        if above and brk:
            status = "signal"
        elif above and 0 <= dist <= 2:
            status = "forming"
        else:
            status = "above" if above else "below"
        if cur["DateStr"] != target:
            stale.append(t)
        watch.append({
            "ticker": t, "name": meta[t]["name"], "sector": meta[t]["sector"], "basket": meta[t]["basket"],
            "date": cur["DateStr"], "close": round(close, 2), "ema20": round(ema, 2),
            "prev20_high": round(prev20, 2), "dist_to_20h_pct": round(dist, 2) if pd.notna(dist) else None,
            "status": status, "avg_turnover_20d": calc_avg_turnover(df, target),
        })

    live, back = closed[closed["source"] == "LIVE"], closed[closed["source"] != "LIVE"]
    closed_recent = closed.sort_values("exit_date", ascending=False).head(300)
    return _sanitize({
        "label": "觀察用，未經實證驗證",
        "generated_at_tw": now_tw().strftime("%Y-%m-%d %H:%M"),
        "data_date": target,
        "universe_count": len(universe),
        "stale_tickers": stale,
        "pending": _records(pending),
        "open": _records(opened),
        "needs_review": _records(review),
        "closed": _records(closed_recent),
        "stats": {"all": _stats(closed), "live": _stats(live), "backfill": _stats(back)},
        "watch": watch,
    })


def run_daily_scan(final: bool = False, ledger_path: str = LEDGER_FILE,
                   watchlist_path: str = WATCHLIST_FILE, dashboard_path: str = DASHBOARD_FILE) -> bool:
    def retry_or_fail(msg: str) -> bool:
        print(f"【資料未到位】{msg}")
        if final:
            print("【最終嘗試失敗】本日帳本未更新。若今天其實是休市日，請告知以更新休市表。")
            return False
        print("【稍後重試】本次不更新帳本，排程稍晚會再執行一次。")
        return True

    now = now_tw()
    expected = get_expected_latest_trading_date(now)
    print(f"台灣時間 {now:%Y-%m-%d %H:%M}，預期最新交易日: {expected}")

    ledger = load_ledger(ledger_path)
    done_dates = [v for v in ledger["last_processed_date"].astype(str) if v and v != "nan"]
    last_processed = max(done_dates) if done_dates else None
    if last_processed and last_processed >= expected:
        print(f"【無需執行】帳本已處理到 {last_processed}，帳本維持不變。")
        print_needs_review_alert(ledger, ledger_path)
        return True

    meta = load_watchlist(watchlist_path)
    universe = sorted(meta.keys())
    if not universe:
        print("【致命錯誤】觀察池為空，程式終止！")
        return False
    active = sorted(set(ledger.loc[ledger["status"].isin(ACTIVE_STATUSES), "ticker"].astype(str)))
    fetch_list = sorted(set(universe) | set(active))
    print(f"載入資料: 觀察池 {len(universe)} 檔，另加持倉中但不在觀察池 {len(set(active) - set(universe))} 檔")

    stock_map, split_map, failed = {}, {}, []
    for t in fetch_list:
        raw = fetch_history(t, lookback_days=LOOKBACK_DAYS)
        df, ev = prepare_stock_data(raw) if not raw.empty else (pd.DataFrame(), {})
        if df.empty:
            failed.append(t)
        else:
            stock_map[t], split_map[t] = df, ev
        time.sleep(0.05)

    ok = sum(1 for t in universe if t in stock_map)
    ratio = ok / len(universe)
    print(f"載入觀察池: 成功 {ok}/{len(universe)} 檔 ({ratio * 100:.1f}%)")
    if ratio < MIN_LOAD_RATIO:
        return retry_or_fail(f"觀察池載入率低於 95%，失敗例: {failed[:10]}")
    missing_active = [t for t in active if t not in stock_map]
    if missing_active:
        return retry_or_fail(f"持倉中標的缺資料 (會造成漏算停損/出場)，不能繼續: {missing_active}")

    # 檢查 active 標的在 target 日期是否有 K 棒
    missing_for_target = []
    for t in active:
        df = stock_map.get(t)
        if df is None or df.empty or target not in df["DateStr"].values:
            missing_for_target.append(t)
    if missing_for_target:
        if final:
            print(f"【警告】以下持倉/掛單標的在 {target} 缺少 K 棒資料，將跳過: {missing_for_target}")
        else:
            return retry_or_fail(f"持倉/掛單標的在 {target} 缺少 K 棒資料: {missing_for_target}")

    last_dates = [stock_map[t]["DateStr"].iloc[-1] for t in universe if t in stock_map]
    latest = max(set(last_dates), key=last_dates.count)
    if latest < expected:
        return retry_or_fail(f"最新資料停在 {latest}，預期 {expected}")
    target = expected

    counts = {}
    for df in stock_map.values():
        for d in df["DateStr"]:
            counts[d] = counts.get(d, 0) + 1
    all_dates = sorted(d for d, c in counts.items() if c >= 0.5 * len(stock_map))
    if target not in all_dates:
        return retry_or_fail(f"資料中找不到 {target} 的交易日資料")

    dates = [d for d in all_dates if last_processed < d <= target] if last_processed else [target]
    if len(dates) > 1:
        print(f"【漏跑偵測】需補算的交易日: {dates[:-1]}，依序補算 (含當日新訊號)...")

    for d in dates:
        source = "LIVE" if d == target else "BACKFILL"
        n_before = len(ledger)
        missing_today = []
        ledger, exited = update_ledger_single_day(
            ledger, stock_map, d, split_map=split_map, freeze_on_split=True, replay_auto_resolve_splits=False,
            missing_out=missing_today
        )
        if missing_today:
            print(f"【{d}】缺棒標的: {missing_today}")
        ledger = ledger.reset_index(drop=True)
        if len(ledger) != n_before:
            print(f"【致命錯誤】更新 {d} 後帳本筆數異常 ({n_before} -> {len(ledger)})，已中止且未寫入！")
            return False

        active_now = set(ledger.loc[ledger["status"].isin(ACTIVE_STATUSES), "ticker"].astype(str))
        ineligible = active_now | exited
        existing = set(zip(ledger["signal_date"].astype(str), ledger["ticker"].astype(str)))
        fee_desc = get_actual_fee_params()["desc"]
        new_rows = []
        for t in universe:
            if t in ineligible or t not in stock_map:
                continue
            sig = scan_today(stock_map[t], t, d)
            if not sig or (d, t) in existing:
                continue
            new_rows.append({
                "signal_date": sig["signal_date"], "ticker": t,
                "trigger_price": sig["trigger_price"], "stop_price": sig["stop_price"], "risk_pct": sig["risk_pct"],
                "triggered": False, "entry_price": np.nan, "entry_date": "", "exit_date": "", "exit_price": np.nan,
                "exit_reason": "", "rule_net_r": np.nan, "actual_net_r": np.nan, "slippage_net_r": np.nan,
                "actual_fee_settings": fee_desc, "status": "PENDING", "days_held": 0, "pending_ema_exit": False,
                "last_processed_date": d, "source": source, "avg_turnover_20d": sig["avg_turnover_20d"],
            })
        if new_rows:
            ledger = pd.concat([ledger, pd.DataFrame(new_rows)], ignore_index=True)
            print(f"[{d}] ({source}) 新訊號 {len(new_rows)} 檔: " + ", ".join(r["ticker"] for r in new_rows))
        else:
            print(f"[{d}] ({source}) 無符合 C 組條件之新訊號。")
        ledger["last_processed_date"] = d

    save_ledger(ledger, ledger_path)
    print(f"已寫入帳本: {ledger_path}")
    dash = build_dashboard(ledger, stock_map, meta, target, universe)
    with open(dashboard_path, "w", encoding="utf-8") as f:
        json.dump(dash, f, ensure_ascii=False, allow_nan=False)
    print(f"已輸出網頁資料: {dashboard_path} (資料日期 {target})")
    print_needs_review_alert(ledger, ledger_path)
    return True




def run_daily_scan_workflow(target_date=None, clear_cache_on_start=False, ledger_path=LEDGER_FILE,
                           preloaded_raw_map=None, source_tag="LIVE", **kwargs):
    """合成測試 / 單日執行用的 workflow 入口"""
    if target_date is None:
        from datetime import datetime
        target_date = datetime.now().strftime("%Y-%m-%d")

    ledger = load_ledger(ledger_path)

    # 準備股票資料
    stock_map = {}
    split_map = {}
    if preloaded_raw_map:
        for ticker, raw_df in preloaded_raw_map.items():
            df, ev = prepare_stock_data(raw_df.copy() if hasattr(raw_df, "copy") else raw_df)
            if not df.empty:
                stock_map[ticker] = df
                split_map[ticker] = ev

    print(f"DEBUG stock_map keys: {list(stock_map.keys())}")
    # universe
    universe = sorted(set(stock_map.keys()))

    # 處理既有持倉
    exited = set()
    if not ledger.empty:
        ledger, exited = update_ledger_single_day(
            ledger, stock_map, target_date, split_map=split_map,
            freeze_on_split=True, replay_auto_resolve_splits=False
        )
        ledger = ledger.reset_index(drop=True)

    # 掃描新訊號
    active_now = set(ledger.loc[ledger["status"].isin(ACTIVE_STATUSES), "ticker"].astype(str)) if not ledger.empty else set()
    ineligible = active_now | exited
    existing = set(zip(ledger["signal_date"].astype(str), ledger["ticker"].astype(str))) if not ledger.empty else set()

    fee_desc = get_actual_fee_params()["desc"]
    new_rows = []
    for t in universe:
        if t in ineligible or t not in stock_map:
            print(f"DEBUG skip {t}: ineligible={t in ineligible}, not_in_stock_map={t not in stock_map}")
            continue
        sig = scan_today(stock_map[t], t, target_date)
        print(f"DEBUG {t}: sig={sig['signal_date'] if sig else None}, target_date={target_date}, in_stock_map={t in stock_map}")
        if not sig or (target_date, t) in existing:
            continue
        new_rows.append({
            "signal_date": sig["signal_date"], "ticker": t,
            "trigger_price": sig["trigger_price"], "stop_price": sig["stop_price"], "risk_pct": sig["risk_pct"],
            "triggered": False, "entry_price": np.nan, "entry_date": "", "exit_date": "", "exit_price": np.nan,
            "exit_reason": "", "rule_net_r": np.nan, "actual_net_r": np.nan, "slippage_net_r": np.nan,
            "actual_fee_settings": fee_desc, "status": "PENDING", "days_held": 0, "pending_ema_exit": False,
            "last_processed_date": target_date, "source": source_tag, "avg_turnover_20d": sig["avg_turnover_20d"],
        })
    if new_rows:
        ledger = pd.concat([ledger, pd.DataFrame(new_rows)], ignore_index=True)

    if not ledger.empty:
        ledger["last_processed_date"] = target_date
        # Set source for updated rows that don't have it
        if "source" in ledger.columns:
            ledger["source"] = ledger["source"].astype(object).fillna(source_tag)
            ledger.loc[ledger["source"].astype(str) == "", "source"] = source_tag

    save_ledger(ledger, ledger_path)
    return True

def main():
    parser = argparse.ArgumentParser(description="Task K Group C Forward Paper Trading Scanner")
    parser.add_argument("--final", action="store_true", help="最終嘗試：資料沒到位時回報失敗 (紅叉)")
    parser.add_argument("--ledger", type=str, default=LEDGER_FILE)
    parser.add_argument("--watchlist", type=str, default=WATCHLIST_FILE)
    parser.add_argument("--resolve", type=str, default=None, help="要解除 NEEDS_REVIEW 的股票代號")
    parser.add_argument("--action", type=str, choices=["close", "adjust"], default=None)
    parser.add_argument("--price", type=float, default=None)
    parser.add_argument("--date", type=str, default=None)
    args = parser.parse_args()

    print("********************************************************************")
    print("【觀察用，未經實證驗證】")
    print("任務 K - C 組 (突破 20 日高) 前瞻紙上交易掃描器")
    print("********************************************************************")

    if args.resolve:
        if not args.action:
            print("【錯誤】使用 --resolve 時必須指定 --action (close 或 adjust)！")
            sys.exit(1)
        ok = resolve_needs_review_position(
            ticker=args.resolve, action=args.action, exit_price=args.price,
            exit_date=args.date, ledger_path=args.ledger,
        )
        sys.exit(0 if ok else 1)

    ok = run_daily_scan(final=args.final, ledger_path=args.ledger, watchlist_path=args.watchlist)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
