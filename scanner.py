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


# ==========================================
# 1. 檔位與價格運算
# ==========================================
def get_tw_tick(price: float) -> float:
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
    tick = get_tw_tick(price)
    if price in [10.0, 50.0, 100.0, 500.0, 1000.0]:
        tick = get_tw_tick(price - 0.001)
    return round(price - tick, 2)


def get_tick_up(price: float) -> float:
    tick = get_tw_tick(price)
    return round(price + tick, 2)


# ==========================================
# 2. 資料清洗與還原 (任務 K 同軌)
# ==========================================
def adjust_corporate_actions(df: pd.DataFrame) -> pd.DataFrame:
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


def prepare_stock_data(raw_df: pd.DataFrame) -> pd.DataFrame:
    if raw_df.empty or len(raw_df) < 22:
        return pd.DataFrame()
    df = raw_df.copy().sort_values("Date").reset_index(drop=True)
    df = adjust_corporate_actions(df)
    df = clean_stock_data(df)
    if len(df) < 22:
        return pd.DataFrame()
    df["DateStr"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")
    df["EMA_20"] = df["Close"].ewm(span=20, adjust=False).mean()
    return df


def get_universe() -> list:
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


# ==========================================
# 3. 訊號掃描
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


# ==========================================
# 4. 帳本狀態管理與撮合更新
# ==========================================
def load_ledger() -> pd.DataFrame:
    cols = [
        "signal_date", "ticker", "trigger_price", "stop_price", "risk_pct",
        "triggered", "entry_price", "entry_date", "exit_date", "exit_price", "exit_reason",
        "rule_net_r", "slippage_net_r", "actual_fee_settings", "status",
        "days_held", "pending_ema_exit"
    ]
    if os.path.exists(LEDGER_FILE):
        return pd.read_csv(LEDGER_FILE)
    return pd.DataFrame(columns=cols)


def save_ledger(df: pd.DataFrame):
    df.to_csv(LEDGER_FILE, index=False, encoding="utf-8-sig")


def update_ledger_with_market_data(ledger: pd.DataFrame, stock_map: dict, today_str: str) -> tuple:
    """每日盤後更新未平倉部位與前一日掛單，並回傳當日出場的股票集合"""
    if ledger.empty:
        return ledger, set()

    updated_rows = []
    tickers_exited_today = set()

    for _, row in ledger.iterrows():
        t = str(row["ticker"])
        status = str(row["status"])
        df = stock_map.get(t, pd.DataFrame())

        if df.empty or status in ["CLOSED", "UNTRIGGERED"]:
            updated_rows.append(row)
            continue

        today_bar_matches = df[df["DateStr"] == today_str]
        if today_bar_matches.empty:
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

        # 1. 處理 PENDING 掛單
        if status == "PENDING":
            if cur_high >= trigger_price:
                entry_price = max(trigger_price, cur_open)
                risk_per_share = entry_price - stop_price
                row["triggered"] = True
                row["entry_price"] = entry_price
                row["entry_date"] = today_str
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
                    tickers_exited_today.add(t)
                else:
                    row["status"] = "OPEN"
                    row["pending_ema_exit"] = False
            else:
                row["triggered"] = False
                row["status"] = "UNTRIGGERED"
                row["exit_reason"] = "UNTRIGGERED"

            updated_rows.append(row)
            continue

        # 2. 處理 OPEN 持倉部位
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
                exit_price = cur_close
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
                tickers_exited_today.add(t)
            else:
                if cur_close < cur_ema:
                    row["pending_ema_exit"] = True
                else:
                    row["pending_ema_exit"] = False

            updated_rows.append(row)

    return pd.DataFrame(updated_rows), tickers_exited_today


# ==========================================
# 5. 擴充回放自我檢驗模組 (2025-H1 逐日生命週期檢核)
# ==========================================
def run_extended_verification(benchmark_csv: str = "task_k_trades_base_no_ov.csv") -> bool:
    print("====================================================================")
    print("【執行擴充自我檢驗：2025-01-02 至 2025-06-30 逐日回放生命週期驗算】")
    print("====================================================================")

    if not os.path.exists(benchmark_csv):
        print(f"【檢驗中止】找不到基準檔案: {benchmark_csv}")
        return False

    df_k = pd.read_csv(benchmark_csv)
    c_trades_all = df_k[df_k["group"] == "C_TaskK"].copy()
    if c_trades_all.empty:
        print("【檢驗中止】CSV 中無 C_TaskK 交易紀錄！")
        return False

    tickers = get_universe()
    stock_map = {}
    if HAS_FETCHER:
        print(f"載入觀察池 {len(tickers)} 檔股票完整行情...")
        for t in tickers:
            raw_df = fetch_history(t, lookback_days=2500)
            if not raw_df.empty:
                stock_map[t] = prepare_stock_data(raw_df)

    # 取得歷史全交易日並排序
    sample_ticker = tickers[0]
    all_trading_dates = sorted(stock_map[sample_ticker]["DateStr"].tolist())
    
    # 建立回放帳本，從 2022-04-01 暖機開始，以確保 2025-01-02 當日之持倉狀態與回測 100% 相同
    start_date = "2022-04-01"
    eval_start = "2025-01-02"
    eval_end = "2025-06-30"

    sim_ledger = pd.DataFrame(columns=[
        "signal_date", "ticker", "trigger_price", "stop_price", "risk_pct",
        "triggered", "entry_price", "entry_date", "exit_date", "exit_price", "exit_reason",
        "rule_net_r", "status", "days_held", "pending_ema_exit"
    ])

    extra_signals = []
    daily_signals_record = {}

    start_idx = all_trading_dates.index(start_date) if start_date in all_trading_dates else 0
    print(f"自 {start_date} 開始循序模擬每日盤後撮合與掃描...")

    for day_idx in range(start_idx, len(all_trading_dates)):
        today_str = all_trading_dates[day_idx]

        # 1. 每日盤後撮合更新帳本
        sim_ledger, exited_today = update_ledger_with_market_data(sim_ledger, stock_map, today_str)

        # 2. 判斷持倉不可進場股票 (持倉中 + 今日出場者)
        active_tickers = set(sim_ledger[sim_ledger["status"].isin(["OPEN", "PENDING"])]["ticker"].unique())
        ineligible_tickers = active_tickers.union(exited_today)

        # 3. 掃描新訊號
        if day_idx < len(all_trading_dates) - 1:
            day_signals = []
            for t in tickers:
                df_t = stock_map.get(t, pd.DataFrame())
                if df_t.empty:
                    continue
                
                # 原始條件檢核
                sig = scan_signals_for_ticker(df_t, t, as_of_date=today_str)
                if sig:
                    is_in_eval = (eval_start <= today_str <= eval_end)
                    if t in ineligible_tickers:
                        if is_in_eval:
                            extra_signals.append({
                                "sig_date": today_str,
                                "ticker": t,
                                "category": "持倉中不重複進場"
                            })
                        continue

                    # 記錄符合掛單條件的訊號
                    day_signals.append(sig)

            # 將新訊號記入帳本為 PENDING
            new_rows = []
            for s in day_signals:
                new_rows.append({
                    "signal_date": s["signal_date"],
                    "ticker": s["ticker"],
                    "trigger_price": s["trigger_price"],
                    "stop_price": s["stop_price"],
                    "risk_pct": s["risk_pct"],
                    "triggered": False,
                    "entry_price": np.nan,
                    "entry_date": "",
                    "exit_date": "",
                    "exit_price": np.nan,
                    "exit_reason": "",
                    "rule_net_r": np.nan,
                    "status": "PENDING",
                    "days_held": 0,
                    "pending_ema_exit": False
                })
            if new_rows:
                sim_ledger = pd.concat([sim_ledger, pd.DataFrame(new_rows)], ignore_index=True)

    # 4. 抽取 2025-H1 評估區間交易進行對照
    eval_benchmark = c_trades_all[
        (c_trades_all["sig_date"] >= eval_start) & (c_trades_all["sig_date"] <= eval_end)
    ].sort_values(["sig_date", "ticker"]).reset_index(drop=True)

    eval_scanner_entered = sim_ledger[
        (sim_ledger["signal_date"] >= eval_start) & 
        (sim_ledger["signal_date"] <= eval_end) & 
        (sim_ledger["triggered"] == True)
    ].sort_values(["signal_date", "ticker"]).reset_index(drop=True)

    # 檢驗多出訊號：掃描器有訊號但未進入 benchmark 者 (次日未觸發)
    eval_scanner_untriggered = sim_ledger[
        (sim_ledger["signal_date"] >= eval_start) & 
        (sim_ledger["signal_date"] <= eval_end) & 
        (sim_ledger["triggered"] == False)
    ]
    for _, r in eval_scanner_untriggered.iterrows():
        extra_signals.append({
            "sig_date": r["signal_date"],
            "ticker": r["ticker"],
            "category": "次日未觸發"
        })

    print(f"\n====================================================================")
    print(f"【2025-H1 對照總覽】")
    print(f"基準 CSV 應成交筆數: {len(eval_benchmark)} 筆")
    print(f"掃描器帳本實測成交筆數: {len(eval_scanner_entered)} 筆")
    print(f"掃描器多出訊號總數: {len(extra_signals)} 筆 (均已全數分類)")
    print(f"====================================================================")

    # 逐筆對齊比對
    diff_records = []
    all_matched = True

    for idx, bench_row in eval_benchmark.iterrows():
        s_date = bench_row["sig_date"]
        tk = bench_row["ticker"]

        sc_match = eval_scanner_entered[
            (eval_scanner_entered["signal_date"] == s_date) & 
            (eval_scanner_entered["ticker"] == tk)
        ]

        if sc_match.empty:
            print(f"[FAIL] 缺少交易: 基準有 {tk} ({s_date}) 但掃描器帳本未成交！")
            all_matched = False
            continue

        sc = sc_match.iloc[0]

        # 數值精確比對
        entry_match = abs(float(sc["entry_price"]) - float(bench_row["entry_price"])) <= 0.001
        stop_match = abs(float(sc["stop_price"]) - float(bench_row["stop_price"])) <= 0.001
        exit_d_match = str(sc["exit_date"]) == str(bench_row["exit_date"])
        exit_p_match = abs(float(sc["exit_price"]) - float(bench_row["exit_price"])) <= 0.001
        reason_match = str(sc["exit_reason"]) == str(bench_row["exit_reason"])
        net_r_match = abs(float(sc["rule_net_r"]) - float(bench_row["net_r"])) <= 0.005

        row_pass = (entry_match and stop_match and exit_d_match and exit_p_match and reason_match and net_r_match)
        if not row_pass:
            all_matched = False

        status_str = "PASS" if row_pass else "FAIL"
        print(f"[{status_str}] {s_date} {tk} | 進場: {sc['entry_price']} vs {bench_row['entry_price']} | 停損: {sc['stop_price']} vs {bench_row['stop_price']} | 出場日: {sc['exit_date']} vs {bench_row['exit_date']} | 出場價: {sc['exit_price']} vs {bench_row['exit_price']} | 原因: {sc['exit_reason']} vs {bench_row['exit_reason']} | 淨R: {sc['rule_net_r']:+.3f} vs {bench_row['net_r']:+.3f}")

        diff_records.append({
            "sig_date": s_date,
            "ticker": tk,
            "scanner_entry_price": sc["entry_price"],
            "csv_entry_price": bench_row["entry_price"],
            "scanner_stop_price": sc["stop_price"],
            "csv_stop_price": bench_row["stop_price"],
            "scanner_exit_date": sc["exit_date"],
            "csv_exit_date": bench_row["exit_date"],
            "scanner_exit_price": sc["exit_price"],
            "csv_exit_price": bench_row["exit_price"],
            "scanner_exit_reason": sc["exit_reason"],
            "csv_exit_reason": bench_row["exit_reason"],
            "scanner_net_r": sc["rule_net_r"],
            "csv_net_r": bench_row["net_r"],
            "match_status": status_str
        })

    # 匯出逐筆比對 CSV
    diff_df = pd.DataFrame(diff_records)
    diff_df.to_csv("replay_diff_2025_h1.csv", index=False, encoding="utf-8-sig")
    print(f"\n已產出並另存逐筆比對檔案: replay_diff_2025_h1.csv")

    # 輸出多出訊號分類明細
    extra_df = pd.DataFrame(extra_signals)
    extra_df.to_csv("replay_extra_signals_2025_h1.csv", index=False, encoding="utf-8-sig")
    print("\n【多出訊號分類清查】")
    print(extra_df["category"].value_counts().to_string())

    print("\n--------------------------------------------------------------------")
    if all_matched and len(eval_scanner_entered) == len(eval_benchmark):
        print(f"【擴充自我檢驗結果：100% 通過】2025-H1 共 {len(eval_benchmark)} 筆交易生命週期全數吻合！")
    else:
        print("【擴充自我檢驗結果：失敗】存在生命週期不吻合或多餘成交，程式終止。")
    print("--------------------------------------------------------------------")
    return all_matched


# ==========================================
# 6. 主程式進入點
# ==========================================
def main():
    parser = argparse.ArgumentParser(description="Task K Group C Forward Paper Trading Scanner")
    parser.add_argument("--date", type=str, default=None, help="指定掃描日期 (YYYY-MM-DD)，預設為最新日")
    parser.add_argument("--verify", action="store_true", help="執行抽樣進場檢驗")
    parser.add_argument("--extended-verify", action="store_true", help="執行 2025-H1 擴充全流程比對回放")
    args = parser.parse_args()

    print("********************************************************************")
    print("【觀察用，未經實證驗證】")
    print("任務 K - C 組 (突破 20 日高) 前瞻紙上交易掃描器")
    print("********************************************************************")

    if args.extended_verify:
        success = run_extended_verification()
        sys.exit(0 if success else 1)

    tickers = get_universe()
    print(f"載入觀察池: 共 {len(tickers)} 檔")

    stock_map = {}
    if HAS_FETCHER:
        for t in tickers:
            raw_df = fetch_history(t, lookback_days=180)
            if not raw_df.empty:
                stock_map[t] = prepare_stock_data(raw_df)

    # 決定今日日期
    sample_ticker = tickers[0]
    latest_market_date = stock_map[sample_ticker]["DateStr"].iloc[-1] if sample_ticker in stock_map and not stock_map[sample_ticker].empty else "2026-10-16"
    today_str = args.date if args.date else latest_market_date

    # 1. 強制更新既有帳本
    ledger = load_ledger()
    ledger, exited_today = update_ledger_with_market_data(ledger, stock_map, today_str)

    # 2. 取得持倉不可進場之股票名單
    open_positions = set(ledger[ledger["status"].isin(["OPEN", "PENDING"])]["ticker"].unique()) if not ledger.empty else set()
    ineligible_tickers = open_positions.union(exited_today)

    # 3. 掃描新訊號
    signals = []
    for t in tickers:
        if t in ineligible_tickers:
            continue
        df = stock_map.get(t, pd.DataFrame())
        sig = scan_signals_for_ticker(df, t, as_of_date=today_str)
        if sig:
            signals.append(sig)

    sig_df = pd.DataFrame(signals)
    print("\n====================================================================")
    print(f"【{today_str} 當日新觸發訊號清單 (排除持倉與今日出場)】共 {len(sig_df)} 檔")
    print("====================================================================")
    if not sig_df.empty:
        print(sig_df[["ticker", "signal_date", "trigger_price", "stop_price", "risk_pct"]].to_string(index=False))

        # 4. 寫入帳本 (保證冪等性，避免重跑重複累加)
        existing_keys = set(zip(ledger["signal_date"].astype(str), ledger["ticker"].astype(str))) if not ledger.empty else set()
        new_records = []
        for _, s in sig_df.iterrows():
            if (str(s["signal_date"]), str(s["ticker"])) in existing_keys:
                continue
            new_records.append({
                "signal_date": s["signal_date"],
                "ticker": s["ticker"],
                "trigger_price": s["trigger_price"],
                "stop_price": s["stop_price"],
                "risk_pct": s["risk_pct"],
                "triggered": False,
                "entry_price": np.nan,
                "entry_date": "",
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
        if new_records:
            ledger = pd.concat([ledger, pd.DataFrame(new_records)], ignore_index=True)
    else:
        print("今日無符合 C 組條件之新訊號。")

    save_ledger(ledger)
    print(f"\n已同步更新至紙上交易帳本: {LEDGER_FILE}")


if __name__ == "__main__":
    main()
