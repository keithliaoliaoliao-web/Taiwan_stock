"""
investigate_universe.py
股票池偏差與資料源三項查證任務：
1. 追溯 150 檔名單在 repo 中的原始定義檔案、代碼與 Git 建立紀錄
2. 檢查 150 檔每檔的第一根日 K 日期，標註在 2021-01-04 前尚未上市櫃的股票
3. 查驗歷史資料來源對已下市櫃股票之支援度，並統計近 5 年下市櫃標的數
"""

import os
import sys
import subprocess
import pandas as pd
import numpy as np
import config
from data_fetcher import fetch_history

FILE_NAME = "task_j_raw_h2_candidates.csv"


def task_1_trace_source():
    print("=" * 70)
    print("【查證任務一：追溯 150 檔股票池的產生來源與 Git 建立紀錄】")
    print("=" * 70)
    
    # 搜尋定義位置
    config_path = getattr(config, "__file__", "config.py")
    print(f"1. 觀察池配置檔案路徑: {config_path}")
    
    # 檢查 Git 提交歷史
    try:
        git_log = subprocess.run(
            ["git", "log", "--diff-filter=A", "--follow", "--format=%H | %an | %ad | %s", "--", "config.py"],
            capture_output=True, text=True
        )
        print("2. config.py 初次建立 Commit 紀錄:")
        print(git_log.stdout.strip() if git_log.stdout else "無 Git 歷史或非 Git 目錄")
        
        git_blame = subprocess.run(
            ["git", "log", "-n", "1", "-p", "config.py"],
            capture_output=True, text=True
        )
        print("\n3. 最近一次修改 config.py 之內容摘要:")
        lines = git_blame.stdout.split("\n")[:25]
        print("\n".join(lines))
    except Exception as e:
        print(f"Git 查詢失敗: {e}")


def task_2_check_listing_dates():
    print("\n" + "=" * 70)
    print("【查證任務二：清查 150 檔第一根日 K 日期與 2021-01-04 前尚未上市標的】")
    print("=" * 70)
    
    if not os.path.exists(FILE_NAME):
        print(f"找不到 {FILE_NAME}")
        return
        
    df_j = pd.read_csv(FILE_NAME)
    tickers = sorted(df_j["ticker"].unique().tolist())
    print(f"開始掃描 150 檔股票歷史資料（上市日檢核）...")
    
    records = []
    unlisted_in_2021 = []
    base_date = pd.Timestamp("2021-01-04")
    
    for idx, t in enumerate(tickers, 1):
        try:
            # 抓取最長歷史
            df = fetch_history(t, lookback_days=2500)
            if df.empty:
                records.append({"ticker": t, "first_date": "NO_DATA", "bars": 0, "status": "無資料"})
                continue
                
            df["Date"] = pd.to_datetime(df["Date"])
            df = df.sort_values("Date").reset_index(drop=True)
            first_date = df["Date"].iloc[0]
            total_bars = len(df)
            
            is_after_start = first_date > base_date
            status = "回測起點後才上市" if is_after_start else "正常上市"
            
            records.append({
                "ticker": t,
                "first_date": first_date.strftime("%Y-%m-%d"),
                "bars": total_bars,
                "status": status
            })
            
            if is_after_start:
                unlisted_in_2021.append((t, first_date.strftime("%Y-%m-%d"), total_bars))
                
        except Exception as e:
            records.append({"ticker": t, "first_date": "ERROR", "bars": 0, "status": str(e)})
            
        if idx % 30 == 0 or idx == len(tickers):
            print(f"進度: {idx}/{len(tickers)} 檔...")
            
    res_df = pd.DataFrame(records)
    res_df.to_csv("universe_listing_audit.csv", index=False, encoding="utf-8-sig")
    
    print("\n【查證二結果摘要】")
    print(f"總檢驗檔數: {len(tickers)} 檔")
    print(f"於 2021-01-04 回測起點前『尚未上市』之標的共 {len(unlisted_in_2021)} 檔:")
    for t, d, b in unlisted_in_2021:
        print(f"  - {t}: 第一根日K為 {d} (總棒數: {b})")


def task_3_check_delisted_support():
    print("\n" + "=" * 70)
    print("【查證任務三：確認資料源是否支援下市櫃股票與近 5 年下市櫃檔數】")
    print("=" * 70)
    
    # 測試已下市代表性股票 (如：綠能 3519、華映 2475、大同盟等)
    known_delisted = [
        ("2475.TW", "華映", "2019 下市"),
        ("3519.TW", "綠能", "2019 下市"),
        ("3698.TW", "隆達", "2021 下市併入富采"),
        ("6456.TW", "GIS-KY", "2023 下市")
    ]
    
    print("1. 測試資料源是否能抓取已下市股票歷史行情:")
    for t, name, desc in known_delisted:
        try:
            df = fetch_history(t, lookback_days=2500)
            if not df.empty and len(df) > 0:
                print(f"  - [{t} {name}] ({desc}): 成功取得歷史日K (共 {len(df)} 根)")
            else:
                print(f"  - [{t} {name}] ({desc}): 無法取得資料 (API 回傳空值)")
        except Exception as e:
            print(f"  - [{t} {name}] ({desc}): 抓取失敗 ({e})")
            
    print("\n2. 資料源下市櫃完整清單查核說明:")
    print("  - 若使用 FinMind：可調用 TaiwanStockInfo，status 欄位區分上市/下市。")
    print("  - 若使用 yfinance：下市股票通常直接下架或停止更新。")
    print("  - 本項詳細清單需由 API 清查後列示於查核報告中。")


if __name__ == "__main__":
    task_1_trace_source()
    task_2_check_listing_dates()
    task_3_check_delisted_support()
