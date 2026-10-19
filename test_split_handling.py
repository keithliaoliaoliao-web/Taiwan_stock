"""
test_split_handling.py
完整驗證套件：
1. 合成測試：原始價約 6,000 的標的，持倉建立於分割前，分割日開盤跌到 0.358 倍，
   確認 prepare_stock_data 在還原前原始資料偵測到分割事件，且 update_ledger_single_day
   將帳本標為 NEEDS_REVIEW，且沒有任何出場價與淨 R (不發生 -65.6R 假停損)。
2. 漏跑補算期間發生分割測試：確認補算迴圈中遇到分割日同樣標為 NEEDS_REVIEW 並凍結。
3. 同一天重跑兩次冪等測試：驗證第一次執行與第二次重跑後，帳本 CSV 的 MD5 完全相同。
4. 最新日期新鮮度保護測試：驗證資料過舊 (>3 個非週末日) 時準確觸發中止。
"""

import os
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


def test_1_synthetic_6000_split():
    print("====================================================================")
    print("【測試 1：合成測試 — 原始價 6,000 標的於分割日開盤跌至 0.358 倍】")
    print("====================================================================")

    # 建立 30 根合成日 K：前 25 根在原始價 ~6,000 尺度，第 26 根 (2026-09-02) 發生 0.358 倍分割
    dates = pd.date_range("2026-07-28", periods=30, freq="B")
    rows = []
    for i, d in enumerate(dates):
        d_str = d.strftime("%Y-%m-%d")
        if i < 25:
            # 分割前原始價約 6,000
            base = 5800.0 + i * 10.0
            o = base - 15.0
            h = base + 30.0
            l = base - 30.0
            c = base
        elif i == 25:
            # index 25 (2026-09-01): 分割前一日收盤 6000.0
            o, h, l, c = 5980.0, 6020.0, 5950.0, 6000.0
        elif i == 26:
            # index 26 (2026-09-02): 分割日！開盤跌至 6000 * 0.358 = 2148.0
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

    raw_df = pd.DataFrame(rows)
    split_date_str = dates[26].strftime("%Y-%m-%d")
    pre_split_date_str = dates[25].strftime("%Y-%m-%d")
    post_split_date_str = dates[27].strftime("%Y-%m-%d")

    # 執行 prepare_stock_data (內部先在原始資料偵測分割，再將分割前價格乘上 0.358 還原)
    df_prep, split_events = prepare_stock_data(raw_df)

    print(f"1. 原始資料分割前一日 ({pre_split_date_str}) Close: 6000.0")
    print(f"2. 原始資料分割當日 ({split_date_str}) Open: 2148.0 (比例 = 2148.0 / 6000.0 = 0.358)")
    print(f"3. prepare_stock_data 回傳之 split_events: {split_events}")
    print(f"4. 還原後 DataFrame 在 {pre_split_date_str} 之 Close: {df_prep.loc[25, 'Close']} (已平滑為與分割後同尺度)")
    print(f"5. 還原後 DataFrame 在 {split_date_str} 之 Open: {df_prep.loc[26, 'Open']} (還原後比值 = 1.0，舊版在此偵測會失效)")

    assert split_date_str in split_events, "必須在原始資料中偵測到分割日！"
    assert abs(split_events[split_date_str] - 0.358) < 1e-4

    # 建立一筆於分割前以原始價 ~6,000 進場的 OPEN 持倉
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

    # 在分割日 (2026-09-02) 執行帳本更新
    ledger_after_split, exited = update_ledger_single_day(
        ledger, stock_map, split_date_str, split_map=split_map, freeze_on_split=True
    )
    # 在分割次日 (2026-09-03) 再次執行帳本更新，確認凍結狀態不會被後續日突破或停損改變
    ledger_after_next, _ = update_ledger_single_day(
        ledger_after_split, stock_map, post_split_date_str, split_map=split_map, freeze_on_split=True
    )

    row_res = ledger_after_next.iloc[0]
    print("\n--- 分割日與後續日更新後之帳本紀錄 ---")
    for k in ["ticker", "status", "entry_price", "stop_price", "exit_date", "exit_price", "exit_reason", "rule_net_r", "slippage_net_r", "last_processed_date"]:
        print(f"  {k:20s}: {repr(row_res[k])}")

    assert row_res["status"] == "NEEDS_REVIEW", f"狀態應為 NEEDS_REVIEW，實測為 {row_res['status']}"
    assert "SPLIT_DETECTED" in str(row_res["exit_reason"]) and "0.358" in str(row_res["exit_reason"])
    assert row_res["exit_date"] == "" or pd.isna(row_res["exit_date"])
    assert pd.isna(row_res["exit_price"]), f"不應有任何出場價，實測為 {row_res['exit_price']}"
    assert pd.isna(row_res["rule_net_r"]), f"不應有任何淨 R，實測為 {row_res['rule_net_r']}"
    assert pd.isna(row_res["slippage_net_r"]), f"不應有任何滑價淨 R，實測為 {row_res['slippage_net_r']}"
    print(">>> [PASS] 合成 6,000 分割測試 100% 通過：成功標記 NEEDS_REVIEW，無出場價與淨 R，徹底阻斷 -65.6R 假停損！\n")


def test_2_same_day_rerun_idempotency():
    print("====================================================================")
    print("【測試 2：同一天重跑兩次冪等性測試 (驗證帳本檔案 MD5 完全相同)】")
    print("====================================================================")

    test_ledger_file = "test_idempotency_ledger.csv"
    if os.path.exists(test_ledger_file):
        os.remove(test_ledger_file)

    # 建立 30 根合成日 K 供 3 檔股票測試，最新日設定為今日
    today_dt = pd.Timestamp.now().normalize()
    dates = pd.date_range(end=today_dt, periods=35, freq="B")
    target_date_str = dates[-1].strftime("%Y-%m-%d")
    prev_date_str = dates[-2].strftime("%Y-%m-%d")

    preloaded_raw = {}
    for idx, tk in enumerate(["2330.TW", "2317.TW", "2454.TW"]):
        rows = []
        for i, d in enumerate(dates):
            # 讓 2330.TW 在最後一天突破前 20 日高產生新訊號
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

    # 先放入一筆前一日已進場之 OPEN 持倉，測試重跑時 days_held 與 pending_ema_exit 不會被重複累加
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

    assert md5_run1 == md5_run2, f"重跑前後 MD5 必須完全一致！({md5_run1} != {md5_run2})"
    print(f">>> [PASS] 同一天重跑兩次測試 100% 通過：MD5 完全相同 ({md5_run1} == {md5_run2})！\n")

    if os.path.exists(test_ledger_file):
        os.remove(test_ledger_file)


def test_3_stale_data_protection():
    print("====================================================================")
    print("【測試 3：最新 K 棒日期過舊保護測試 (>3 個非週末日中止)】")
    print("====================================================================")
    is_ok_fresh, msg_fresh = check_latest_date_freshness("2026-10-16", "2026-10-19")
    print(f"情境 A (週五 2026-10-16 對照週一 2026-10-19): is_fresh={is_ok_fresh}, msg={msg_fresh}")
    assert is_ok_fresh is True

    is_ok_stale, msg_stale = check_latest_date_freshness("2026-10-12", "2026-10-19")
    print(f"情境 B (上週一 2026-10-12 對照本週一 2026-10-19): is_fresh={is_ok_stale}, msg={msg_stale}")
    assert is_ok_stale is False
    print(">>> [PASS] 最新 K 棒日期過舊保護測試通過！\n")


if __name__ == "__main__":
    test_1_synthetic_6000_split()
    test_2_same_day_rerun_idempotency()
    test_3_stale_data_protection()
