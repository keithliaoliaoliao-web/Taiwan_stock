"""
scanner.py
任務 K - C 組 (突破 20 日高) 前瞻紙上交易掃描器
版面標註：【觀察用，未經實證驗證】
"""

import os
import sys
import argparse
import pandas as pd
import numpy as np

try:
    import config
    HAS_CONFIG = True
except Exception:
    HAS_CONFIG = False

try:
    from data_fetcher import fetch_history
    HAS_FETCHER = True
except Exception:
    HAS_FETCHER = False

LEDGER_FILE = "paper_trading_ledger.csv"
COST_RATE = 0.00585
ACTUAL_FEE_DESC = "稅0.3% + 手續費0.1425%*2 (回測基準，無折扣無低消)"


def get_tw_tick(price: float) -> float:
    """台股法定升降檔位表"""
    if price < 10.0:
        return 0.01
    elif price < 50.0:
        return 0.05
    elif price < 100.0:
        return 0.1
    elif price < 500.0:
        return 0.5
    elif price < 1000.0:
        return 1.0
    else:
        return 5.0


def get_tick_down(price: float) -> float:
    """向下退 1 檔 (停損價)"""
    tick = get_tw_tick(price)
    if price in [10.0, 50.0, 100.0, 500.0, 1000.0]:
        tick = get_tw_tick(price - 0.001)
    return round(price - tick, 2)


def get_tick_up(price: float) -> float:
    """向上進 1 檔 (觸發進場價)"""
    tick = get_tw_tick(price)
    return round(price + tick, 2)


def adjust_corporate_actions(df: pd.DataFrame) -> pd.DataFrame:
    """股票分割回溯平滑演算法 (分割已還原、現金股利不加回)"""
    df = df.copy().sort_values("Date").reset_index(drop=True)
    n = len(df)
    adj_factor = np.ones(n)

    for i in range(1, n):
        prev_c = df.loc[i - 1, "Close"]
        cur_o = df.loc[i, "Open"]
        if prev_c > 0 and cur_o > 0 and (cur_o / prev_c) < 0.70:
            ratio = cur_o / prev_c
            adj_factor[:i] *= ratio

    for col in ["Open", "High", "Low", "Close"]:
        if col in df.columns:
            df[col] = (df[col] * adj_factor).round(2)

    return df


def clean_stock_data(df: pd.DataFrame) -> pd.DataFrame:
    """前置資料清洗：整根剔除全零/無量棒，缺開盤價以前日收盤補值"""
    df = df.copy().sort_values("Date").reset_index(drop=True)
    cleaned_rows = []

    for idx, row in df.iterrows():
        o = float(row.get("Open", 0))
        h = float(row.get("High", 0))
        l = float(row.get("Low", 0))
        c = float(row.get("Close", 0))
        v = float(row.get("Volume", 0))

        if (o <= 0 and c <= 0) or v <= 0:
            continue

        if o <= 0 and c > 0:
            if cleaned_rows:
                row["Open"] = float(cleaned_rows[-1]["Close"])
            else:
                row["Open"] = c

        cleaned_rows.append(row)

    return pd.DataFrame(cleaned_rows).reset_index(drop=True)


def get_universe() -> list:
    """載入觀察池標的 (嚴禁在日誌中輸出任何 token)"""
    if HAS_CONFIG:
        for fn in ["load_universe", "get_universe", "get_stock_list"]:
            f = getattr(config, fn, None)
            if callable(f):
                try:
                    res = f()
                    if isinstance(res, dict):
                        return sorted(list(res.keys()))
                    if isinstance(res, (list, tuple)):
                        return sorted([str(x) for x in res])
                except Exception:
                    pass
        tickers = getattr(config, "TARGET_STOCKS", getattr(config, "STOCKS", None))
        if isinstance(tickers, (list, tuple)):
            return sorted([str(x) for x in tickers])

    if os.path.exists("task_j_raw_h2_candidates.csv"):
        df_j = pd.read_csv("task_j_raw_h2_candidates.csv")
        return sorted(df_j["ticker"].unique().tolist())
    return []


def scan_signals_for_ticker(df: pd.DataFrame, ticker: str, as_of_date: str = None) -> dict:
    """
    對單檔股票執行 C 組掃描：
    1. Close >= 20EMA
    2. High > max(High[t-20 : t-1]) (前 20 根日 K 最高，嚴格不含當日)
    """
    if df.empty or len(df) < 22:
        return None

    df = df.copy().sort_values("Date").reset_index(drop=True)
    df["DateStr"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")

    if as_of_date is not None:
        df = df[df["DateStr"] <= as_of_date].reset_index(drop=True)
        if df.empty or len(df) < 22:
            return None

    df = clean_stock_data(df)
    df = adjust_corporate_actions(df)
    if len(df) < 22:
        return None

    df["EMA_20"] = df["Close"].ewm(span=20, adjust=False).mean()

    cur_idx = len(df) - 1
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
    trigger_price = get_tick_up(high)
    stop_price = get_tick_down(low)
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


def load_ledger() -> pd.DataFrame:
    cols = [
        "signal_date", "ticker", "trigger_price", "stop_price", "risk_pct",
        "triggered", "entry_price", "exit_date", "exit_price", "exit_reason",
        "rule_net_r", "slippage_net_r", "actual_fee_settings", "status",
        "days_held", "pending_ema_exit"
    ]
    if os.path.exists(LEDGER_FILE):
        return pd.read_csv(LEDGER_FILE)
    return pd.DataFrame(columns=cols)


def save_ledger(df: pd.DataFrame):
    df.to_csv(LEDGER_FILE, index=False, encoding="utf-8-sig")


def update_ledger_with_market_data(ledger: pd.DataFrame, stock_map: dict, today_str: str) -> pd.DataFrame:
    """每日盤後更新未平倉部位與前一日掛單"""
    if ledger.empty:
        return ledger

    updated_rows = []
    for _, row in ledger.iterrows():
        t = str(row["ticker"])
        status = str(row["status"])
        df = stock_map.get(t, pd.DataFrame())

        if df.empty or status in ["CLOSED", "UNTRIGGERED"]:
            updated_rows.append(row)
            continue

        df["DateStr"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")
        today_bar_matches = df[df["DateStr"] == today_str]
        if today_bar_matches.empty:
            updated_rows.append(row)
            continue

        today_bar = today_bar_matches.iloc[0]
        cur_open = float(today_bar["Open"])
        cur_high = float(today_bar["High"])
        cur_low = float(today_bar["Low"])
        cur_close = float(today_bar["Close"])
        cur_ema = float(today_bar.get("EMA_20", cur_close))

        trigger_price = float(row["trigger_price"])
        stop_price = float(row["stop_price"])

        # 1. 處理 PENDING 掛單 (次日撮合)
        if status == "PENDING":
            if cur_high >= trigger_price:
                entry_price = max(trigger_price, cur_open)
                risk_per_share = entry_price - stop_price
                row["triggered"] = True
                row["entry_price"] = entry_price
                row["days_held"] = 0

                # 當日反轉停損檢核 (含開盤跳空低於停損)
                if cur_low <= stop_price:
                    exit_price = min(cur_open, stop_price)
                    row["exit_date"] = today_str
                    row["exit_price"] = exit_price
                    row["exit_reason"] = "SAME_DAY_STOP"
                    row["status"] = "CLOSED"
                    row["rule_net_r"] = round(((exit_price * (1.0 - COST_RATE)) - entry_price) / risk_per_share, 3)

                    slip_entry = get_tick_up(entry_price)
                    slip_exit = get_tick_down(exit_price)
                    row["slippage_net_r"] = round(((slip_exit * (1.0 - COST_RATE)) - slip_entry) / risk_per_share, 3)
                else:
                    row["status"] = "OPEN"
                    row["pending_ema_exit"] = False
            else:
                row["triggered"] = False
                row["status"] = "UNTRIGGERED"
                row["exit_reason"] = "UNTRIGGERED"

            updated_rows.append(row)
            continue

        # 2. 處理 OPEN 持倉部位 (初始停損在持倉期間每日皆有效)
        if status == "OPEN":
            days_held = int(row["days_held"]) + 1
            row["days_held"] = days_held
            pending_ema = bool(row["pending_ema_exit"])
            entry_price = float(row["entry_price"])
            risk_per_share = entry_price - stop_price

            is_closed = False
            exit_price = 0.0
            exit_reason = ""

            # 依任務 K 原文迴圈優先順序判斷
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
                exit_price = cur_close  # 原文規則：滿 120 日以當日收盤價出場
                exit_reason = "MAX_120D"

            if is_closed:
                row["status"] = "CLOSED"
                row["exit_date"] = today_str
                row["exit_price"] = exit_price
                row["exit_reason"] = exit_reason
                row["rule_net_r"] = round(((exit_price * (1.0 - COST_RATE)) - entry_price) / risk_per_share, 3)

                slip_entry = get_tick_up(entry_price)
                slip_exit = get_tick_down(exit_price)
                row["slippage_net_r"] = round(((slip_exit * (1.0 - COST_RATE)) - slip_entry) / risk_per_share, 3)
            else:
                if cur_close < cur_ema:
                    row["pending_ema_exit"] = True
                else:
                    row["pending_ema_exit"] = False

            updated_rows.append(row)

    return pd.DataFrame(updated_rows)


def run_self_verification(trades_csv: str = "task_k_trades_base_indep.csv") -> bool:
    """
    從 task_k_trades_base_indep.csv 抽樣 5 個不同日期回放檢驗：
    每筆訊號必須出現在掃描清單中，且 stop_price 與 entry_price 須 100% 精確相符。
    """
    print("====================================================================")
    print("【執行自我檢驗：對照 task_k_trades_base_indep.csv C_TaskK 回放驗算】")
    print("====================================================================")

    if not os.path.exists(trades_csv):
        print(f"【檢驗中止】找不到檔案: {trades_csv}")
        return False

    df_k = pd.read_csv(trades_csv)
    c_trades = df_k[df_k["group"] == "C_TaskK"].copy()
    if c_trades.empty:
        print("【檢驗中止】CSV 中無 C_TaskK 交易紀錄！")
        return False

    unique_dates = sorted(c_trades["sig_date"].unique().tolist())
    np.random.seed(42)
    sample_size = min(5, len(unique_dates))
    sampled_dates = sorted(list(np.random.choice(unique_dates, size=sample_size, replace=False)))

    print(f"抽樣檢驗的 5 個訊號日期: {sampled_dates}")

    all_matched = True
    total_checked = 0

    tickers = get_universe()
    stock_map = {}
    if HAS_FETCHER:
        for t in tickers:
            df = fetch_history(t, lookback_days=2500)
            if not df.empty:
                stock_map[t] = df

    for sig_d in sampled_dates:
        expected_trades = c_trades[c_trades["sig_date"] == sig_d]
        print(f"\n--- 檢驗日期: {sig_d} (預期應有 {len(expected_trades)} 筆成交) ---")

        day_signals = {}
        for t in tickers:
            df = stock_map.get(t, pd.DataFrame())
            sig = scan_signals_for_ticker(df, t, as_of_date=sig_d)
            if sig:
                day_signals[t] = sig

        for _, exp in expected_trades.iterrows():
            total_checked += 1
            t = str(exp["ticker"])
            exp_stop = float(exp["stop_price"])
            exp_entry = float(exp["entry_price"])

            if t not in day_signals:
                print(f"  [FAIL] {t} 未被掃描器偵測出訊號！")
                all_matched = False
                continue

            act = day_signals[t]
            act_stop = float(act["stop_price"])
            act_trigger = float(act["trigger_price"])

            if abs(act_stop - exp_stop) > 0.001:
                print(f"  [FAIL] {t} 停損價不符: 掃描器={act_stop} != CSV={exp_stop}")
                all_matched = False
                continue

            df_t = stock_map.get(t, pd.DataFrame())
            df_t["DateStr"] = pd.to_datetime(df_t["Date"]).dt.strftime("%Y-%m-%d")
            next_bars = df_t[df_t["DateStr"] > sig_d].sort_values("DateStr")
            if not next_bars.empty:
                next_bar = next_bars.iloc[0]
                act_entry = max(act_trigger, float(next_bar["Open"]))
                if abs(act_entry - exp_entry) > 0.001:
                    print(f"  [FAIL] {t} 成交價不符: 模擬={act_entry} != CSV={exp_entry}")
                    all_matched = False
                    continue

            print(f"  [PASS] {t}: 停損價=${act_stop}、成交價=${exp_entry} 完全吻合")

    print("\n--------------------------------------------------------------------")
    if all_matched:
        print(f"【自我檢驗結果：100% 通過】共抽查 {total_checked} 筆交易，停損價與成交價全數吻合！")
    else:
        print("【自我檢驗結果：失敗】存在不一致項目，請停止回報並清查原因。")
    print("--------------------------------------------------------------------")
    return all_matched


def main():
    parser = argparse.ArgumentParser(description="Task K Group C Forward Paper Trading Scanner")
    parser.add_argument("--date", type=str, default=None, help="指定掃描日期 (YYYY-MM-DD)，預設為最新日")
    parser.add_argument("--verify", action="store_true", help="執行歷史抽樣自我檢驗")
    args = parser.parse_args()

    print("********************************************************************")
    print("【觀察用，未經實證驗證】")
    print("任務 K - C 組 (突破 20 日高) 前瞻紙上交易掃描器")
    print("********************************************************************")

    if args.verify:
        success = run_self_verification()
        sys.exit(0 if success else 1)

    tickers = get_universe()
    print(f"載入觀察池: 共 {len(tickers)} 檔")

    stock_map = {}
    if HAS_FETCHER:
        for t in tickers:
            df = fetch_history(t, lookback_days=180)
            if not df.empty:
                stock_map[t] = df

    ledger = load_ledger()
    open_positions = set(ledger[ledger["status"].isin(["OPEN", "PENDING"])]["ticker"].unique()) if not ledger.empty else set()

    if args.date and not ledger.empty:
        ledger = update_ledger_with_market_data(ledger, stock_map, args.date)

    signals = []
    for t in tickers:
        if t in open_positions:
            continue
        df = stock_map.get(t, pd.DataFrame())
        sig = scan_signals_for_ticker(df, t, as_of_date=args.date)
        if sig:
            signals.append(sig)

    sig_df = pd.DataFrame(signals)
    print("\n====================================================================")
    print(f"【當日新觸發訊號清單 (排除持倉中)】共 {len(sig_df)} 檔")
    print("====================================================================")
    if not sig_df.empty:
        print(sig_df[["ticker", "signal_date", "trigger_price", "stop_price", "risk_pct"]].to_string(index=False))

        new_records = []
        for _, s in sig_df.iterrows():
            new_records.append({
                "signal_date": s["signal_date"],
                "ticker": s["ticker"],
                "trigger_price": s["trigger_price"],
                "stop_price": s["stop_price"],
                "risk_pct": s["risk_pct"],
                "triggered": False,
                "entry_price": np.nan,
                "exit_date": "",
                "exit_price": np.nan,
                "exit_reason": "",
                "rule_net_r": np.nan,
                "slippage_net_r": np.nan,
                "actual_fee_settings": ACTUAL_FEE_DESC,
                "status": "PENDING",
                "days_held": 0,
                "pending_ema_exit": False
            })
        ledger = pd.concat([ledger, pd.DataFrame(new_records)], ignore_index=True)
    else:
        print("今日無符合 C 組條件之新訊號。")

    save_ledger(ledger)
    print(f"\n已同步更新至紙上交易帳本: {LEDGER_FILE}")


if __name__ == "__main__":
    main()
