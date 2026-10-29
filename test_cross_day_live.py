"""
test_cross_day_live.py
【合成資料邏輯測試：模擬跨日狀態推進、撮合成交、停損結案與分割凍結 (使用合成數據，非真實連線)】
"""

import os
import shutil
import pandas as pd
import numpy as np
from scanner import run_daily_scan_workflow, load_ledger


def test_synthetic_cross_day_state_logic():
    print("====================================================================")
    print("【合成資料邏輯測試：模擬跨日撮合、出場與 NEEDS_REVIEW 凍結 (使用合成數據)】")
    print("====================================================================")

    ledger_path = "test_synthetic_ledger.csv"
    backup_dir = "test_synthetic_backups"
    if os.path.exists(ledger_path):
        os.remove(ledger_path)
    if os.path.exists(backup_dir):
        shutil.rmtree(backup_dir, ignore_errors=True)
    os.makedirs(backup_dir, exist_ok=True)

    dates = pd.date_range("2026-09-15", periods=30, freq="B")
    day1_str = dates[-3].strftime("%Y-%m-%d")
    day2_str = dates[-2].strftime("%Y-%m-%d")
    day3_str = dates[-1].strftime("%Y-%m-%d")

    raw_2330, raw_6669 = [], []
    for i, d in enumerate(dates):
        if i < len(dates) - 3:
            raw_2330.append({"Date": d, "Open": 900.0, "High": 910.0, "Low": 895.0, "Close": 905.0, "Volume": 10000})
            raw_6669.append({"Date": d, "Open": 5900.0, "High": 5950.0, "Low": 5880.0, "Close": 5920.0, "Volume": 5000})
        elif i == len(dates) - 3:
            raw_2330.append({"Date": d, "Open": 910.0, "High": 925.0, "Low": 908.0, "Close": 922.0, "Volume": 20000})
            raw_6669.append({"Date": d, "Open": 5950.0, "High": 6000.0, "Low": 5910.0, "Close": 5990.0, "Volume": 8000})
        elif i == len(dates) - 2:
            raw_2330.append({"Date": d, "Open": 928.0, "High": 935.0, "Low": 920.0, "Close": 930.0, "Volume": 25000})
            raw_6669.append({"Date": d, "Open": 6010.0, "High": 6050.0, "Low": 5980.0, "Close": 6000.0, "Volume": 9000})
        else:
            raw_2330.append({"Date": d, "Open": 905.0, "High": 908.0, "Low": 900.0, "Close": 902.0, "Volume": 30000})
            raw_6669.append({"Date": d, "Open": 2148.0, "High": 2180.0, "Low": 2120.0, "Close": 2160.0, "Volume": 12000})

    df_2330_full = pd.DataFrame(raw_2330)
    df_6669_full = pd.DataFrame(raw_6669)

    print(f"\n>>> [Day 1 ({day1_str})] 合成資料產生新訊號並寫入帳本 <<<")
    map_day1 = {"2330.TW": df_2330_full.iloc[:-2].copy(), "6669.TW": df_6669_full.iloc[:-2].copy()}
    assert run_daily_scan_workflow(target_date=day1_str, clear_cache_on_start=False, ledger_path=ledger_path, preloaded_raw_map=map_day1, source_tag="BACKFILL")
    shutil.copy(ledger_path, os.path.join(backup_dir, f"ledger_{day1_str}.csv"))
    df_l1 = load_ledger(ledger_path)
    print("\n[Day 1 帳本內容]:")
    print(df_l1[["signal_date", "ticker", "status", "trigger_price", "stop_price", "source"]].to_string(index=False))
    assert len(df_l1) == 2 and all(df_l1["status"] == "PENDING")

    print(f"\n>>> [Day 2 ({day2_str})] 模擬跨日撮合成交轉 OPEN <<<")
    map_day2 = {"2330.TW": df_2330_full.iloc[:-1].copy(), "6669.TW": df_6669_full.iloc[:-1].copy()}
    assert run_daily_scan_workflow(target_date=day2_str, clear_cache_on_start=False, ledger_path=ledger_path, preloaded_raw_map=map_day2, source_tag="BACKFILL")
    shutil.copy(ledger_path, os.path.join(backup_dir, f"ledger_{day2_str}.csv"))
    df_l2 = load_ledger(ledger_path)
    print("\n[Day 2 帳本內容]:")
    print(df_l2[["ticker", "status", "triggered", "entry_date", "entry_price", "days_held", "source"]].to_string(index=False))
    assert all(df_l2["status"] == "OPEN")

    print(f"\n>>> [Day 3 ({day3_str})] 模擬停損結案與分割觸發 NEEDS_REVIEW <<<")
    map_day3 = {"2330.TW": df_2330_full.copy(), "6669.TW": df_6669_full.copy()}
    assert run_daily_scan_workflow(target_date=day3_str, clear_cache_on_start=False, ledger_path=ledger_path, preloaded_raw_map=map_day3, source_tag="BACKFILL")
    shutil.copy(ledger_path, os.path.join(backup_dir, f"ledger_{day3_str}.csv"))
    df_l3 = load_ledger(ledger_path)
    print("\n[Day 3 帳本完整內容]:")
    print(df_l3[["ticker", "status", "entry_price", "exit_date", "exit_price", "exit_reason", "rule_net_r", "actual_net_r", "source"]].to_string(index=False))

    r_2330 = df_l3[df_l3["ticker"] == "2330.TW"].iloc[0]
    r_6669 = df_l3[df_l3["ticker"] == "6669.TW"].iloc[0]
    assert r_2330["status"] == "CLOSED"
    assert r_2330["rule_net_r"] == r_2330["actual_net_r"]  # 預設條件下必須嚴格相等
    assert r_6669["status"] == "NEEDS_REVIEW"
    print("\n>>> [PASS] 合成資料狀態機推進邏輯測試通過！\n")

    if os.path.exists(ledger_path):
        os.remove(ledger_path)
    if os.path.exists(backup_dir):
        shutil.rmtree(backup_dir, ignore_errors=True)


if __name__ == "__main__":
    test_synthetic_cross_day_state_logic()
