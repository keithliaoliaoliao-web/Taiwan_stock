"""
test_split_handling.py
單元測試：持倉標的發生分割時標記為 NEEDS_REVIEW 並凍結自動撮合
包含即時模式 (Live Mode) 與回放模式 (Replay Mode) 雙向驗證
"""
import pandas as pd
import numpy as np

def update_position_split_check(row: pd.Series, cur_open: float, prev_close: float, cur_low: float, cur_close: float, cur_ema: float, today_str: str) -> pd.Series:
    row = row.copy()
    status = str(row["status"])
    if status not in ["OPEN", "PENDING"]:
        return row
        
    # 偵測分割事件：當日開盤相較前日收盤跌幅超過 30%
    if prev_close > 0 and cur_open > 0 and (cur_open / prev_close) < 0.70:
        ratio = round(cur_open / prev_close, 4)
        row["status"] = "NEEDS_REVIEW"
        row["exit_reason"] = f"SPLIT_DETECTED(ratio={ratio})"
        row["last_processed_date"] = today_str
        return row

    # 正常撮合 (若未分割)
    stop_price = float(row["stop_price"])
    if cur_low <= stop_price:
        row["status"] = "CLOSED"
        row["exit_date"] = today_str
        row["exit_price"] = min(cur_open, stop_price)
        row["exit_reason"] = "INITIAL_STOP"
    return row

def test_live_mode():
    print("--- 測試 1：即時模式 (Live Mode，未還原原始價發生分割) ---")
    pos = pd.Series({
        "ticker": "6669.TW",
        "signal_date": "2026-08-25",
        "status": "OPEN",
        "entry_price": 2700.0,
        "stop_price": 2550.0,
        "exit_date": "",
        "exit_price": np.nan,
        "exit_reason": "",
        "days_held": 5,
        "last_processed_date": "2026-09-01"
    })
    
    updated = update_position_split_check(pos, cur_open=900.0, prev_close=2700.0, cur_low=880.0, cur_close=920.0, cur_ema=910.0, today_str="2026-09-02")
    
    print(f"狀態變更: {pos['status']} -> {updated['status']}")
    print(f"出場原因: {repr(updated['exit_reason'])}")
    print(f"進場價維持: {updated['entry_price']}")
    print(f"停損價維持: {updated['stop_price']}")
    print(f"是否免於假停損出場: {updated['status'] == 'NEEDS_REVIEW' and pd.isna(updated['exit_price'])}")
    assert updated["status"] == "NEEDS_REVIEW"
    assert pd.isna(updated["exit_price"])
    print("[PASS] 即時模式單元測試通過！\n")

def test_replay_mode():
    print("--- 測試 2：回放模式 (Replay Mode，已平滑資料 vs 未平滑資料) ---")
    pos_adj = pd.Series({
        "ticker": "6669.TW",
        "status": "OPEN",
        "entry_price": 966.6,
        "stop_price": 912.9,
        "exit_date": "",
        "exit_price": np.nan,
        "exit_reason": "",
        "days_held": 5,
        "last_processed_date": "2026-09-01"
    })
    updated_adj = update_position_split_check(pos_adj, cur_open=965.0, prev_close=960.0, cur_low=950.0, cur_close=970.0, cur_ema=955.0, today_str="2026-09-02")
    print("情境 A (已平滑回放): 未觸發分割跳空，持倉維持正常撮合 (status:", updated_adj["status"], ")")
    assert updated_adj["status"] == "OPEN"
    
    pos_raw = pd.Series({
        "ticker": "2327.TW",
        "status": "PENDING",
        "entry_price": np.nan,
        "stop_price": 480.0,
        "exit_date": "",
        "exit_price": np.nan,
        "exit_reason": "",
        "days_held": 0,
        "last_processed_date": "2022-10-19"
    })
    updated_raw = update_position_split_check(pos_raw, cur_open=320.0, prev_close=500.0, cur_low=315.0, cur_close=325.0, cur_ema=330.0, today_str="2022-10-31")
    print("情境 B (未平滑回放): 正確捕捉減資/分割跳空，狀態標記為:", updated_raw["status"], "原因:", updated_raw["exit_reason"])
    assert updated_raw["status"] == "NEEDS_REVIEW"
    assert "SPLIT_DETECTED" in updated_raw["exit_reason"]
    print("[PASS] 回放模式單元測試通過！")

if __name__ == "__main__":
    test_live_mode()
    test_replay_mode()
