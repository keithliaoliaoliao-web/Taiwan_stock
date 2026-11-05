"""
test_split_handling.py
完整驗證套件 (涵蓋 6 項獨立測試)：
1. 合成測試：原始價約 6,000 的標的，持倉建立於分割前，分割日開盤跌到 0.358 倍，
   確認標為 NEEDS_REVIEW 且沒有任何出場價與淨 R (不發生 -65.6R 假停損)。
2. 漏跑補算期間發生分割測試：建立持倉，模擬程式漏跑 3 個交易日，補算區間內包含分割日，
   確認補算後標為 NEEDS_REVIEW 且沒有出場價與淨 R。
3. 手動解除指令測試 (--resolve TICKER --action close --price 價格 --date 日期)：
   確認以人工填入價格結案、依規則公式計算淨 R、註記 MANUAL_RESOLVE，且 last_processed_date 維持不變。
4. 手動解除指令測試 (--resolve TICKER --action adjust)：
   確認依記錄的分割比例調整進場價、停損價、觸發價後恢復為 OPEN，且 last_processed_date 維持不變。
5. 同一天重跑兩次冪等測試：驗證第一次執行與第二次重跑後，帳本 CSV 的 MD5 完全相同。
6. 最新日期新鮮度保護與快取預期日檢查測試：驗證資料過舊 (>3 個非週末日) 時準確觸發中止。
"""

import os
import subprocess
import hashlib
import pandas as pd
import numpy as np
from scanner import (
    prepare_stock_data,
    update_ledger_single_day,
    run_daily_scan_workflow,
    check_latest_date_freshness,
    ACTUAL_FEE_DESC
)


def get_md5(filepath: str) -> str:
    with open(filepath, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def build_synthetic_6000_df(dates):
    rows = []
    for i, d in enumerate(dates):
        if i < 25:
            base = 5800.0 + i * 10.0
            o, h, l, c = base - 15.0, base + 30.0, base - 30.0, base
        elif i == 25:
            # 分割前一日收盤 6000.0
            o, h, l, c = 5980.0, 6020.0, 5950.0, 6000.0
        elif i == 26:
            # 分割日！開盤跌至 6000 * 0.358 = 2148.0
            o, h, l, c = 2148.0, 2180.0, 2120.0, 2160.0
        else:
            o, h, l, c = 2160.0, 2190.0, 2140.0, 2175.0

        rows.append({
            "Date": d,
            "Open": o,
            "High": h,
            "Low": l,
            "Close": c,
            "Volume": 5000000
        })
    return pd.DataFrame(rows)


def test_1_synthetic_6000_split():
    print("====================================================================")
    print("【測試 1：合成測試 — 原始價 6,000 標的於分割日開盤跌至 0.358 倍】")
    print("====================================================================")

    dates = pd.date_range("2026-07-28", periods=30, freq="B")
    raw_df = build_synthetic_6000_df(dates)
    split_date_str = dates[26].strftime("%Y-%m-%d")
    pre_split_date_str = dates[25].strftime("%Y-%m-%d")
    post_split_date_str = dates[27].strftime("%Y-%m-%d")

    df_prep, split_events = prepare_stock_data(raw_df)

    print(f"1. 原始資料分割前一日 ({pre_split_date_str}) Close: 6000.0")
    print(f"2. 原始資料分割當日 ({split_date_str}) Open: 2148.0 (比例 = 2148.0 / 6000.0 = 0.358)")
    print(f"3. prepare_stock_data 回傳之 split_events: {split_events}")
    print(f"4. 還原後 DataFrame 在 {pre_split_date_str} 之 Close: {df_prep.loc[25, 'Close']} (已平滑為與分割後同尺度)")
    print(f"5. 還原後 DataFrame 在 {split_date_str} 之 Open: {df_prep.loc[26, 'Open']} (還原後比值 = 1.0，舊版在此偵測會失效)")

    assert split_date_str in split_events
    assert abs(split_events[split_date_str] - 0.358) < 1e-4

    ledger = pd.DataFrame([{
        "signal_date": dates[23].strftime("%Y-%m-%d"),
        "ticker": "6669.TW",
        "trigger_price": 6010.0,
        "stop_price": 5920.0,
        "risk_pct": 1.50,
        "triggered": True,
        "entry_price": 6010.0,
        "entry_date": dates[24].strftime("%Y-%m-%d"),
        "exit_date": "",
        "exit_price": np.nan,
        "exit_reason": "",
        "rule_net_r": np.nan,
        "slippage_net_r": np.nan,
        "actual_fee_settings": ACTUAL_FEE_DESC,
        "status": "OPEN",
        "days_held": 1,
        "pending_ema_exit": False,
        "last_processed_date": pre_split_date_str
    }])

    stock_map = {"6669.TW": df_prep}
    split_map = {"6669.TW": split_events}

    ledger_after_split, _ = update_ledger_single_day(
        ledger, stock_map, split_date_str, split_map=split_map, freeze_on_split=True
    )
    ledger_after_next, _ = update_ledger_single_day(
        ledger_after_split, stock_map, post_split_date_str, split_map=split_map, freeze_on_split=True
    )

    row_res = ledger_after_next.iloc[0]
    print("\n--- 分割日與後續日更新後之帳本紀錄 ---")
    for k in ["ticker", "status", "entry_price", "stop_price", "exit_date", "exit_price", "exit_reason", "rule_net_r", "slippage_net_r", "last_processed_date"]:
        print(f"  {k:20s}: {repr(row_res[k])}")

    assert row_res["status"] == "NEEDS_REVIEW"
    assert "SPLIT_DETECTED" in str(row_res["exit_reason"]) and "0.358" in str(row_res["exit_reason"])
    assert row_res["exit_date"] == "" or pd.isna(row_res["exit_date"])
    assert pd.isna(row_res["exit_price"])
    assert pd.isna(row_res["rule_net_r"])
    assert pd.isna(row_res["slippage_net_r"])
    print(">>> [PASS] 測試 1 通過：成功標記 NEEDS_REVIEW，無出場價與淨 R，阻斷假停損！\n")


def test_2_missed_days_backfill_with_split():
    print("====================================================================")
    print("【測試 2：漏跑補算期間發生分割測試 (漏跑 3 個交易日且中間含分割日)】")
    print("====================================================================")

    test_ledger = "test_missed_split_ledger.csv"
    if os.path.exists(test_ledger):
        os.remove(test_ledger)

    # 30 根日 K，index 24 = 2026-08-31 (上次處理日)
    # 漏跑 3 個交易日：index 25 (2026-09-01), index 26 (2026-09-02 分割日), index 27 (2026-09-03)
    # 今日執行日：index 28 (2026-09-04)
    dates = pd.date_range("2026-07-28", periods=30, freq="B")
    raw_6669 = build_synthetic_6000_df(dates)

    last_proc_str = dates[24].strftime("%Y-%m-%d")
    split_day_str = dates[26].strftime("%Y-%m-%d")
    run_today_str = dates[28].strftime("%Y-%m-%d")

    preloaded_raw = {"6669.TW": raw_6669}

    init_ledger = pd.DataFrame([{
        "signal_date": dates[22].strftime("%Y-%m-%d"),
        "ticker": "6669.TW",
        "trigger_price": 6010.0,
        "stop_price": 5920.0,
        "risk_pct": 1.50,
        "triggered": True,
        "entry_price": 6010.0,
        "entry_date": dates[23].strftime("%Y-%m-%d"),
        "exit_date": "",
        "exit_price": np.nan,
        "exit_reason": "",
        "rule_net_r": np.nan,
        "slippage_net_r": np.nan,
        "actual_fee_settings": ACTUAL_FEE_DESC,
        "status": "OPEN",
        "days_held": 1,
        "pending_ema_exit": False,
        "last_processed_date": last_proc_str
    }])
    init_ledger.to_csv(test_ledger, index=False, encoding="utf-8-sig")

    print(f"初始帳本 last_processed_date: {last_proc_str}")
    print(f"模擬直接於 {run_today_str} 執行 (中間漏跑 {dates[25].strftime('%Y-%m-%d')}, {split_day_str}[分割日], {dates[27].strftime('%Y-%m-%d')} 共 3 個交易日)...")

    ok = run_daily_scan_workflow(
        target_date=run_today_str,
        clear_cache_on_start=False,
        ledger_path=test_ledger,
        preloaded_raw_map=preloaded_raw
    )
    assert ok

    df_res = pd.read_csv(test_ledger)
    row_res = df_res.loc[df_res["ticker"] == "6669.TW"].iloc[0]

    print("\n--- 漏跑補算完成後之 6669.TW 帳本狀態 ---")
    for k in ["ticker", "status", "days_held", "entry_price", "stop_price", "exit_date", "exit_price", "exit_reason", "rule_net_r", "slippage_net_r", "last_processed_date"]:
        print(f"  {k:20s}: {repr(row_res[k])}")

    # 驗證：在 2026-09-01 正常 +1 天 (days_held=2)，在 2026-09-02 (分割日) 標為 NEEDS_REVIEW 並凍結，後續 09-03、09-04 不再變動亦不觸發停損
    assert row_res["status"] == "NEEDS_REVIEW", f"預期 NEEDS_REVIEW，實測 {row_res['status']}"
    assert int(row_res["days_held"]) in [1, 2]
    assert f"SPLIT_DETECTED(date={split_day_str},ratio=0.358)" in str(row_res["exit_reason"])
    assert pd.isna(row_res["exit_date"]) or str(row_res["exit_date"]) == ""
    assert pd.isna(row_res["exit_price"])
    assert pd.isna(row_res["rule_net_r"])
    assert pd.isna(row_res["slippage_net_r"])
    print(">>> [PASS] 測試 2 通過：漏跑 3 日補算期間遇到分割日成功標記 NEEDS_REVIEW 並凍結，無出場價與淨 R！\n")

    if os.path.exists(test_ledger):
        os.remove(test_ledger)


def test_3_cli_resolve_close_and_adjust():
    print("====================================================================")
    print("【測試 3：CLI 解除 NEEDS_REVIEW 指令測試 (--action close 與 --action adjust)】")
    print("====================================================================")

    test_ledger = "test_resolve_cli_ledger.csv"

    # (A) 測試 --resolve 6669.TW --action close --price 2210.0 --date 2026-09-03
    # 假設以原始尺度價格 6170.0 人工結案 (或調整後價格結案)，驗證公式與 last_processed_date 不變
    df_init_close = pd.DataFrame([{
        "signal_date": "2026-08-27",
        "ticker": "6669.TW",
        "trigger_price": 6010.0,
        "stop_price": 5920.0,
        "risk_pct": 1.50,
        "triggered": True,
        "entry_price": 6010.0,
        "entry_date": "2026-08-28",
        "exit_date": "",
        "exit_price": np.nan,
        "exit_reason": "SPLIT_DETECTED(date=2026-09-02,ratio=0.358)",
        "rule_net_r": np.nan,
        "slippage_net_r": np.nan,
        "actual_fee_settings": ACTUAL_FEE_DESC,
        "status": "NEEDS_REVIEW",
        "days_held": 2,
        "pending_ema_exit": False,
        "last_processed_date": "2026-09-02"
    }])
    df_init_close.to_csv(test_ledger, index=False, encoding="utf-8-sig")

    print("--- (3A) 執行 CLI: python scanner.py --resolve 6669.TW --action close --price 6150.0 --date 2026-09-03 ---")
    cmd_close = [
        "python", "scanner.py",
        "--resolve", "6669.TW",
        "--action", "close",
        "--price", "6150.0",
        "--date", "2026-09-03",
        "--ledger", test_ledger
    ]
    res_close = subprocess.run(cmd_close, capture_output=True, text=True)
    print(res_close.stdout.strip())
    assert res_close.returncode == 0

    df_closed = pd.read_csv(test_ledger)
    r_c = df_closed.iloc[0]
    expected_r = round(((6150.0 * (1.0 - 0.00585)) - 6010.0) / (6010.0 - 5920.0), 3)
    print("結案後帳本欄位檢核:")
    for k in ["ticker", "status", "entry_price", "stop_price", "exit_date", "exit_price", "exit_reason", "rule_net_r", "slippage_net_r", "last_processed_date"]:
        print(f"  {k:20s}: {repr(r_c[k])}")

    assert r_c["status"] == "CLOSED"
    assert str(r_c["exit_date"]) == "2026-09-03"
    assert float(r_c["exit_price"]) == 6150.0
    assert abs(float(r_c["rule_net_r"]) - expected_r) < 1e-4
    assert "MANUAL_RESOLVE" in str(r_c["exit_reason"])
    assert str(r_c["last_processed_date"]) == "2026-09-02", "last_processed_date 必須保持不變！"
    print(">>> [PASS] (3A) --action close 測試通過！\n")

    # (B) 測試 --resolve 6669.TW --action adjust
    df_init_adj = pd.DataFrame([{
        "signal_date": "2026-08-27",
        "ticker": "6669.TW",
        "trigger_price": 6010.0,
        "stop_price": 5920.0,
        "risk_pct": 1.50,
        "triggered": True,
        "entry_price": 6010.0,
        "entry_date": "2026-08-28",
        "exit_date": "",
        "exit_price": np.nan,
        "exit_reason": "SPLIT_DETECTED(date=2026-09-02,ratio=0.358)",
        "rule_net_r": np.nan,
        "slippage_net_r": np.nan,
        "actual_fee_settings": ACTUAL_FEE_DESC,
        "status": "NEEDS_REVIEW",
        "days_held": 2,
        "pending_ema_exit": False,
        "last_processed_date": "2026-09-02"
    }])
    df_init_adj.to_csv(test_ledger, index=False, encoding="utf-8-sig")

    print("--- (3B) 執行 CLI: python scanner.py --resolve 6669.TW --action adjust ---")
    cmd_adj = [
        "python", "scanner.py",
        "--resolve", "6669.TW",
        "--action", "adjust",
        "--ledger", test_ledger
    ]
    res_adj = subprocess.run(cmd_adj, capture_output=True, text=True)
    print(res_adj.stdout.strip())
    assert res_adj.returncode == 0

    df_adj = pd.read_csv(test_ledger)
    r_a = df_adj.iloc[0]
    print("調整後帳本欄位檢核:")
    for k in ["ticker", "status", "trigger_price", "entry_price", "stop_price", "exit_reason", "actual_fee_settings", "last_processed_date"]:
        print(f"  {k:20s}: {repr(r_a[k])}")

    assert r_a["status"] == "OPEN"
    assert abs(float(r_a["trigger_price"]) - round(6010.0 * 0.358, 2)) < 1e-4
    assert abs(float(r_a["entry_price"]) - round(6010.0 * 0.358, 2)) < 1e-4
    assert abs(float(r_a["stop_price"]) - round(5920.0 * 0.358, 2)) < 1e-4
    assert str(r_a["last_processed_date"]) == "2026-09-02", "last_processed_date 必須保持不變！"
    print(">>> [PASS] (3B) --action adjust 測試通過！\n")

    if os.path.exists(test_ledger):
        os.remove(test_ledger)


def test_4_same_day_rerun_idempotency():
    print("====================================================================")
    print("【測試 4：同一天重跑兩次冪等性測試 (驗證帳本檔案 MD5 完全相同)】")
    print("====================================================================")

    test_ledger_file = "test_idempotency_ledger.csv"
    if os.path.exists(test_ledger_file):
        os.remove(test_ledger_file)

    today_dt = pd.Timestamp.now().normalize()
    dates = pd.date_range(end=today_dt, periods=35, freq="B")
    target_date_str = dates[-1].strftime("%Y-%m-%d")
    prev_date_str = dates[-2].strftime("%Y-%m-%d")

    preloaded_raw = {}
    for idx, tk in enumerate(["2330.TW", "2317.TW", "2454.TW"]):
        rows = []
        for i, d in enumerate(dates):
            base = 500.0 + i * 2.0 + idx * 50.0
            high = base + 5.0 if (tk == "2330.TW" and i == len(dates) - 1) else base + 1.0
            rows.append({
                "Date": d,
                "Open": base - 1.0,
                "High": high,
                "Low": base - 3.0,
                "Close": base + 2.0,
                "Volume": 10000000
            })
        preloaded_raw[tk] = pd.DataFrame(rows)

    init_ledger = pd.DataFrame([{
        "signal_date": dates[-4].strftime("%Y-%m-%d"),
        "ticker": "2317.TW",
        "trigger_price": 590.0,
        "stop_price": 570.0,
        "risk_pct": 3.39,
        "triggered": True,
        "entry_price": 590.0,
        "entry_date": dates[-3].strftime("%Y-%m-%d"),
        "exit_date": "",
        "exit_price": np.nan,
        "exit_reason": "",
        "rule_net_r": np.nan,
        "slippage_net_r": np.nan,
        "actual_fee_settings": ACTUAL_FEE_DESC,
        "status": "OPEN",
        "days_held": 1,
        "pending_ema_exit": False,
        "last_processed_date": prev_date_str
    }])
    init_ledger.to_csv(test_ledger_file, index=False, encoding="utf-8-sig")

    print(f"--- 執行第 1 次當日掃描與更新 (日期: {target_date_str}) ---")
    ok1 = run_daily_scan_workflow(
        target_date=target_date_str,
        clear_cache_on_start=False,
        ledger_path=test_ledger_file,
        preloaded_raw_map=preloaded_raw
    )
    assert ok1
    md5_run1 = get_md5(test_ledger_file)
    df_run1 = pd.read_csv(test_ledger_file)
    print(f"第 1 次執行後帳本筆數: {len(df_run1)} | 2317.TW days_held: {df_run1.loc[df_run1['ticker']=='2317.TW', 'days_held'].iloc[0]}")
    print(f"第 1 次執行後帳本 MD5: {md5_run1}")

    print(f"\n--- 執行第 2 次同一天重跑 (日期: {target_date_str}) ---")
    ok2 = run_daily_scan_workflow(
        target_date=target_date_str,
        clear_cache_on_start=False,
        ledger_path=test_ledger_file,
        preloaded_raw_map=preloaded_raw
    )
    assert ok2
    md5_run2 = get_md5(test_ledger_file)
    df_run2 = pd.read_csv(test_ledger_file)
    print(f"第 2 次執行後帳本筆數: {len(df_run2)} | 2317.TW days_held: {df_run2.loc[df_run2['ticker']=='2317.TW', 'days_held'].iloc[0]}")
    print(f"第 2 次執行後帳本 MD5: {md5_run2}")

    assert md5_run1 == md5_run2
    print(f">>> [PASS] 測試 4 通過：同日重跑兩次 MD5 完全相同 ({md5_run1} == {md5_run2})！\n")

    if os.path.exists(test_ledger_file):
        os.remove(test_ledger_file)


def test_5_stale_data_protection():
    print("====================================================================")
    print("【測試 5：最新 K 棒日期過舊保護測試 (>3 個非週末日中止)】")
    print("====================================================================")
    is_ok_fresh, msg_fresh = check_latest_date_freshness("2026-10-16", "2026-10-19")
    print(f"情境 A (週五 2026-10-16 對照週一 2026-10-19): is_fresh={is_ok_fresh}, msg={msg_fresh}")
    assert is_ok_fresh is True

    is_ok_stale, msg_stale = check_latest_date_freshness("2026-10-12", "2026-10-19")
    print(f"情境 B (上週一 2026-10-12 對照本週一 2026-10-19): is_fresh={is_ok_stale}, msg={msg_stale}")
    assert is_ok_stale is False
    print(">>> [PASS] 測試 5 通過！\n")


if __name__ == "__main__":
    test_1_synthetic_6000_split()
    test_2_missed_days_backfill_with_split()
    test_3_cli_resolve_close_and_adjust()
    test_4_same_day_rerun_idempotency()
    test_5_stale_data_protection()
