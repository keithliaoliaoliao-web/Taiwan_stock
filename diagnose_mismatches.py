"""
diagnose_mismatches.py
診斷 2308.TW 與 2880.TW 資料差異，並清查 150 檔 Volume<=0 剔除之棒
"""
import os
import pandas as pd
import numpy as np

from data_fetcher import fetch_history
from run_task_k import get_universe_tickers, adjust_corporate_actions as k_adj, clean_stock_data as k_clean
from scanner import prepare_stock_data as s_prep

def run_diagnostics():
    print("=== 開始執行資料診斷 ===")
    tickers = get_universe_tickers()
    
    # 1. 診斷 2308.TW (2025-05-08 至 2025-10-31)
    raw_2308 = fetch_history("2308.TW", lookback_days=2200)
    k_df_2308 = k_adj(raw_2308)
    k_df_2308, _ = k_clean(k_df_2308, "2308.TW")
    k_df_2308["DateStr"] = pd.to_datetime(k_df_2308["Date"]).dt.strftime("%Y-%m-%d")
    k_df_2308["EMA_20"] = k_df_2308["Close"].ewm(span=20, adjust=False).mean()
    
    s_df_2308 = s_prep(raw_2308)
    
    k_sub_2308 = k_df_2308[(k_df_2308["DateStr"] >= "2025-05-08") & (k_df_2308["DateStr"] <= "2025-10-31")].copy()
    s_sub_2308 = s_df_2308[(s_df_2308["DateStr"] >= "2025-05-08") & (s_df_2308["DateStr"] <= "2025-10-31")].copy()
    
    merged_2308 = pd.merge(
        k_sub_2308[["DateStr", "Open", "High", "Low", "Close", "Volume", "EMA_20"]],
        s_sub_2308[["DateStr", "Open", "High", "Low", "Close", "Volume", "EMA_20"]],
        on="DateStr", how="outer", suffixes=("_task_k", "_scanner")
    ).sort_values("DateStr").reset_index(drop=True)
    
    merged_2308["bar_index"] = np.arange(len(merged_2308))
    merged_2308.to_csv("diag_2308.csv", index=False, encoding="utf-8-sig")
    print(f"已輸出 diag_2308.csv: 共 {len(merged_2308)} 列")
    
    # 2. 診斷 2880.TW (2025-08-08 至 2025-08-15)
    raw_2880 = fetch_history("2880.TW", lookback_days=2200)
    k_df_2880 = k_adj(raw_2880)
    k_df_2880, _ = k_clean(k_df_2880, "2880.TW")
    k_df_2880["DateStr"] = pd.to_datetime(k_df_2880["Date"]).dt.strftime("%Y-%m-%d")
    k_df_2880["EMA_20"] = k_df_2880["Close"].ewm(span=20, adjust=False).mean()
    
    s_df_2880 = s_prep(raw_2880)
    
    k_sub_2880 = k_df_2880[(k_df_2880["DateStr"] >= "2025-08-08") & (k_df_2880["DateStr"] <= "2025-08-15")].copy()
    s_sub_2880 = s_df_2880[(s_df_2880["DateStr"] >= "2025-08-08") & (s_df_2880["DateStr"] <= "2025-08-15")].copy()
    
    merged_2880 = pd.merge(
        k_sub_2880[["DateStr", "Open", "High", "Low", "Close", "Volume", "EMA_20"]],
        s_sub_2880[["DateStr", "Open", "High", "Low", "Close", "Volume", "EMA_20"]],
        on="DateStr", how="outer", suffixes=("_task_k", "_scanner")
    ).sort_values("DateStr").reset_index(drop=True)
    
    merged_2880["ema_diff"] = merged_2880["EMA_20_scanner"] - merged_2880["EMA_20_task_k"]
    merged_2880.to_csv("diag_2880.csv", index=False, encoding="utf-8-sig")
    print(f"已輸出 diag_2880.csv: 共 {len(merged_2880)} 列")
    
    # 3. 清查 150 檔在 2022-04 至 2026-10 之間被 Volume<=0 剔除之棒清單
    dropped_records = []
    for t in tickers:
        raw_df = fetch_history(t, lookback_days=2200)
        if raw_df.empty:
            continue
        raw_df["DateStr"] = pd.to_datetime(raw_df["Date"]).dt.strftime("%Y-%m-%d")
        sub_raw = raw_df[(raw_df["DateStr"] >= "2022-04-01") & (raw_df["DateStr"] <= "2026-10-31")]
        for _, row in sub_raw.iterrows():
            o = float(row.get("Open", 0))
            h = float(row.get("High", 0))
            l = float(row.get("Low", 0))
            c = float(row.get("Close", 0))
            has_vol = "Volume" in row and pd.notna(row["Volume"])
            v = float(row["Volume"]) if has_vol else 1.0
            
            if (o <= 0 and c <= 0) or (has_vol and v <= 0):
                dropped_records.append({
                    "ticker": t,
                    "date": row["DateStr"],
                    "open": o,
                    "high": h,
                    "low": l,
                    "close": c,
                    "volume": float(row["Volume"]) if has_vol else np.nan,
                    "reason": "ZERO_BAR" if (o <= 0 and c <= 0) else "VOLUME_LE_ZERO"
                })
                
    dropped_df = pd.DataFrame(dropped_records)
    dropped_df.to_csv("diag_dropped_volume_bars.csv", index=False, encoding="utf-8-sig")
    print(f"已輸出 diag_dropped_volume_bars.csv: 共 {len(dropped_df)} 筆剔除棒")

if __name__ == "__main__":
    run_diagnostics()
