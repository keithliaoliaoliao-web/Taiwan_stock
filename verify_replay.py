"""verify_replay.py - 回放驗證"""
import argparse
import hashlib
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scanner import (
    prepare_stock_data,
    scan_signals_for_ticker,
    update_ledger_single_day,
    get_actual_fee_params,
    ACTUAL_FEE_DESC,
)
from data_fetcher import fetch_history


def get_md5(filepath: str) -> str:
    with open(filepath, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def get_universe() -> list:
    csv_path = "task_j_raw_h2_candidates.csv"
    if os.path.exists(csv_path):
        df_j = pd.read_csv(csv_path)
        return sorted(df_j["ticker"].unique().tolist())
    return []


def run_extended_verification(
    benchmark_csv: str = "task_k_trades_base_no_ov.csv",
    replay_auto_resolve_splits: bool = False
) -> bool:
    print("====================================================================")
    print("【執行擴充自我檢驗：涵蓋 2023-H2, 2025-H1, 2026-H1 三區間全流程回放】")
    print(f"【回放分割處理模式】replay_auto_resolve_splits = {replay_auto_resolve_splits}")
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
    if len(tickers) < 142:
        print(f"【檢驗中止】股票池載入數不足 95%: 實測 {len(tickers)} 檔")
        return False

    stock_map = {}
    split_map = {}
    if HAS_FETCHER:
        print(f"載入觀察池 {len(tickers)} 檔行情 (lookback_days=2200，回放驗證保留快取)...")
        for t in tickers:
            raw_df = fetch_history(t, lookback_days=2200)
            if not raw_df.empty:
                df_prep, s_ev = prepare_stock_data(raw_df)
                if not df_prep.empty:
                    stock_map[t] = df_prep
                    split_map[t] = s_ev

    valid_loaded = len(stock_map)
    print(f"擴充回放實際成功載入檔數: {valid_loaded}/{len(tickers)} 檔 ({round(valid_loaded/len(tickers)*100, 1)}%)")
    if valid_loaded < 142:
        print(f"【致命錯誤】有效載入股票數不足 95% (門檻 142 檔，實測 {valid_loaded} 檔)，檢驗強制中止！")
        return False

    all_trading_dates = sorted(list(set.union(*[set(df["DateStr"]) for df in stock_map.values() if not df.empty])))

    eval_periods = [
        ("2023-H2", "2023-07-03", "2023-12-29"),
        ("2025-H1", "2025-01-02", "2025-06-30"),
        ("2026-H1", "2026-01-02", "2026-06-30")
    ]

    total_overall_pass = True

    for period_name, p_start, p_end in eval_periods:
        print(f"\n" + "=" * 68)
        print(f"【開始評估區間: {period_name} ({p_start} ~ {p_end})】")
        print("=" * 68)

        sim_ledger = pd.DataFrame(columns=[
            "signal_date", "ticker", "trigger_price", "stop_price", "risk_pct",
            "triggered", "entry_price", "entry_date", "exit_date", "exit_price", "exit_reason",
            "rule_net_r", "slippage_net_r", "actual_fee_settings", "status",
            "days_held", "pending_ema_exit", "last_processed_date"
        ])

        extra_signals = []
        start_date = "2022-04-01"
        start_idx = all_trading_dates.index(start_date) if start_date in all_trading_dates else 0

        for day_idx in range(start_idx, len(all_trading_dates)):
            today_str = all_trading_dates[day_idx]
            if today_str > p_end and sim_ledger[sim_ledger["status"] == "OPEN"].empty:
                break

            sim_ledger, exited_today = update_ledger_single_day(
                sim_ledger,
                stock_map,
                today_str,
                split_map=split_map,
                freeze_on_split=True,
                replay_auto_resolve_splits=replay_auto_resolve_splits
            )
            active_tickers = set(sim_ledger[sim_ledger["status"].isin(["OPEN", "PENDING", "NEEDS_REVIEW"])]["ticker"].unique())
            ineligible_tickers = active_tickers.union(exited_today)

            if day_idx < len(all_trading_dates) - 1:
                for t in tickers:
                    df_t = stock_map.get(t, pd.DataFrame())
                    if df_t.empty:
                        continue

                    sig = scan_signals_for_ticker(df_t, t, as_of_date=today_str)
                    if sig:
                        in_eval = (p_start <= today_str <= p_end)
                        if t in ineligible_tickers:
                            if in_eval:
                                extra_signals.append({
                                    "sig_date": today_str,
                                    "ticker": t,
                                    "category": "持倉中不重複進場"
                                })
                            continue

                        sim_ledger = pd.concat([sim_ledger, pd.DataFrame([{
                            "signal_date": sig["signal_date"],
                            "ticker": sig["ticker"],
                            "trigger_price": sig["trigger_price"],
                            "stop_price": sig["stop_price"],
                            "risk_pct": sig["risk_pct"],
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
                            "pending_ema_exit": False,
                            "last_processed_date": today_str
                        }])], ignore_index=True)

        bench_sub = c_trades_all[
            (c_trades_all["sig_date"] >= p_start) & (c_trades_all["sig_date"] <= p_end)
        ].sort_values(["sig_date", "ticker"]).reset_index(drop=True)

        scanner_entered = sim_ledger[
            (sim_ledger["signal_date"] >= p_start) & 
            (sim_ledger["signal_date"] <= p_end) & 
            (sim_ledger["triggered"] == True)
        ].sort_values(["signal_date", "ticker"]).reset_index(drop=True)

        scanner_untriggered = sim_ledger[
            (sim_ledger["signal_date"] >= p_start) & 
            (sim_ledger["signal_date"] <= p_end) & 
            (sim_ledger["triggered"] == False)
        ]
        for _, r in scanner_untriggered.iterrows():
            extra_signals.append({
                "sig_date": r["signal_date"],
                "ticker": r["ticker"],
                "category": "次日未觸發"
            })

        print(f"基準應成交: {len(bench_sub)} 筆 | 掃描器成交: {len(scanner_entered)} 筆")
        diff_records = []
        period_pass = True

        for _, b_row in bench_sub.iterrows():
            s_d = b_row["sig_date"]
            tk = b_row["ticker"]

            match = scanner_entered[
                (scanner_entered["signal_date"] == s_d) & 
                (scanner_entered["ticker"] == tk)
            ]
            if match.empty:
                print(f"  [FAIL] 缺少成交: {s_d} {tk}")
                period_pass = False
                continue

            m = match.iloc[0]
            entry_ok = (abs(float(m["entry_price"]) - float(b_row["entry_price"])) <= 0.001)
            stop_ok = (abs(float(m["stop_price"]) - float(b_row["stop_price"])) <= 0.001)
            exit_d_ok = (str(m["exit_date"]) == str(b_row["exit_date"]))
            exit_p_ok = (abs(float(m["exit_price"]) - float(b_row["exit_price"])) <= 0.001)
            reason_ok = (str(m["exit_reason"]) == str(b_row["exit_reason"]))
            r_ok = (abs(float(m["rule_net_r"]) - float(b_row["net_r"])) <= 0.005)

            is_p = (entry_ok and stop_ok and exit_d_ok and exit_p_ok and reason_ok and r_ok)
            if not is_p:
                period_pass = False

            diff_records.append({
                "period": period_name,
                "sig_date": s_d,
                "ticker": tk,
                "scanner_entry": m["entry_price"],
                "csv_entry": b_row["entry_price"],
                "scanner_stop": m["stop_price"],
                "csv_stop": b_row["stop_price"],
                "scanner_exit_date": m["exit_date"],
                "csv_exit_date": b_row["exit_date"],
                "scanner_exit_price": m["exit_price"],
                "csv_exit_price": b_row["exit_price"],
                "scanner_reason": m["exit_reason"],
                "csv_reason": b_row["exit_reason"],
                "scanner_net_r": m["rule_net_r"],
                "csv_net_r": b_row["net_r"],
                "match_status": "PASS" if is_p else "FAIL"
            })

        prefix = period_name.lower().replace("-", "_")
        pd.DataFrame(diff_records).to_csv(f"replay_diff_{prefix}.csv", index=False, encoding="utf-8-sig")
        pd.DataFrame(extra_signals).to_csv(f"replay_extra_{prefix}.csv", index=False, encoding="utf-8-sig")

        if period_pass and len(scanner_entered) == len(bench_sub):
            print(f"【{period_name} 評估結果：100% PASS】")
        else:
            print(f"【{period_name} 評估結果：FAIL】")
            total_overall_pass = False

    return total_overall_pass


# ==========================================
# 6. 主程式單次執行核心 (供 CLI 與重跑測試呼叫)
# ==========================================

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=str, default="task_k_trades_base_no_ov.csv")
    parser.add_argument("--replay-auto-resolve", action="store_true")
    args = parser.parse_args()

    print(f"scanner.py MD5: {get_md5('scanner.py')}")
    if os.path.exists(args.benchmark):
        print(f"benchmark MD5: {get_md5(args.benchmark)}")
    else:
        print(f"benchmark file not found: {args.benchmark}")
        sys.exit(1)

    ok = run_extended_verification(
        benchmark_csv=args.benchmark,
        replay_auto_resolve_splits=args.replay_auto_resolve
    )
    sys.exit(0 if ok else 1)
