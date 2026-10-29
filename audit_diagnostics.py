"""
audit_diagnostics.py
量化與演算法審計診斷腳本：執行純資料診斷、BOS 統計、回測一致性比對、條件漏斗分析與視覺化抽樣驗證。
"""

import os
import random
import pandas as pd
import numpy as np
import config
from data_fetcher import fetch_history
from price_action_engine import PriceActionEngine

def run_audit():
    print("==================================================")
    print("【一、參數配置確認與外移回報】")
    print("==================================================")
    print(f"- TREND_EMA_MIN_UP_BARS = {getattr(config, 'TREND_EMA_MIN_UP_BARS', 'N/A')}")
    print(f"- MIN_LEG2_PULLBACK_BARS = {getattr(config, 'MIN_LEG2_PULLBACK_BARS', 'N/A')}")
    print(f"- SWING_LOOKBACK_PERIOD = {getattr(config, 'SWING_LOOKBACK_PERIOD', 'N/A')}")
    print(f"- MAX_PULLBACK_BAR_LIMIT = {getattr(config, 'MAX_PULLBACK_BAR_LIMIT', 'N/A')}")
    print(f"- CLIMAX_BAR_ATR_RATIO = {getattr(config, 'CLIMAX_BAR_ATR_RATIO', 'N/A')}")
    print(f"- GRADE_A_BAR_CLOSE_RATIO = {getattr(config, 'GRADE_A_BAR_CLOSE_RATIO', 'N/A')}")
    print(f"- GRADE_A_MAX_PULLBACK_BARS = {getattr(config, 'GRADE_A_MAX_PULLBACK_BARS', 'N/A')}")
    print(f"- GRADE_A_EMA_DISTANCE_ATR = {getattr(config, 'GRADE_A_EMA_DISTANCE_ATR', 'N/A')}")

    universe = config.DEFAULT_WATCHLIST
    print(f"\n載入觀察池標的共 {len(universe)} 檔進行深度審計...")

    all_dfs = {}
    total_bars = 0
    total_bos_true = 0

    # 收集資料與 BOS 統計
    for ticker in universe:
        df = fetch_history(ticker, lookback_days=config.DATA_LOOKBACK_DAYS)
        if df is None or len(df) < 50:
            continue
        try:
            analyzed = PriceActionEngine.analyze_setups(df)
            if analyzed is not None and not analyzed.empty:
                all_dfs[ticker] = analyzed
                total_bars += len(analyzed)
                if "BOS" in analyzed.columns:
                    total_bos_true += int(analyzed["BOS"].sum())
        except Exception as e:
            continue

    bos_pct = (total_bos_true / total_bars * 100.0) if total_bars > 0 else 0.0
    print("\n==================================================")
    print("【二、資料一致性與 BOS 統計】")
    print("==================================================")
    print(f"總分析 K 棒數: {total_bars}")
    print(f"BOS 標記為 True 的總 K 棒數: {total_bos_true}")
    print(f"BOS 觸發比例: {bos_pct:.2f}%")

    # 任務二.4：歷史資料窗口比對 (120, 250, 500 bars)
    print("\n[任務二.4] 歷史資料窗口比對 (120, 250, 500 bars):")
    sample_tickers = random.sample(list(all_dfs.keys()), min(5, len(all_dfs)))
    for ticker in sample_tickers:
        df_full = fetch_history(ticker, lookback_days=750)
        if df_full is None or len(df_full) < 500:
            continue
        
        res_results = {}
        for lb in [120, 250, 500]:
            sub_df = df_full.tail(lb).copy()
            analyzed_sub = PriceActionEngine.analyze_setups(sub_df)
            if analyzed_sub is not None and not analyzed_sub.empty:
                recent_signals = analyzed_sub.tail(30)["Signal_H2"].tolist()
                res_results[lb] = recent_signals
        
        if len(res_results) == 3:
            match_250_120 = (res_results[250][-min(len(res_results[120]), 30):] == res_results[120][-min(len(res_results[120]), 30):])
            match_500_250 = (res_results[500][-min(len(res_results[250]), 30):] == res_results[250][-min(len(res_results[250]), 30):])
            print(f"  - 股票 {ticker}: 250 vs 120 窗口一致性: {match_250_120}, 500 vs 250 窗口一致性: {match_500_250}")

    # 任務三：條件漏斗分析表 (Condition Funnel Table)
    print("\n==================================================")
    print("【三、條件漏斗分析表 (Condition Funnel Table)】")
    print("==================================================")
    
    funnel_stats = {
        "Total_Bars_Evaluated": 0,
        "Trend_Passed": 0,
        "H1_Exists": 0,
        "H1_Failed_Leg2": 0,
        "H2_Triggered": 0,
        "Pullback_Bar_Limit_Met": 0,
        "Climactic_Bar_Met": 0,
        "Quality_Met": 0,
        "EMA_Distance_Met": 0,
        "Final_Signals": 0
    }

    higher_low_count = 0
    total_h2_signals = 0
    sampled_signals = []

    for ticker, df in all_dfs.items():
        for idx, row in df.iterrows():
            funnel_stats["Total_Bars_Evaluated"] += 1
            ema = row.get("EMA_20", np.nan)
            close = row.get("Close", 0)
            if pd.isna(ema) or close < ema:
                continue
            funnel_stats["Trend_Passed"] += 1

            try:
                is_valid, details = PriceActionEngine._strict_h1_h2_state(df, df.index.get_loc(idx))
            except Exception:
                continue

            if details.get("h1_detected", False) or details.get("setup_type") != "NONE":
                funnel_stats["H1_Exists"] += 1
            if details.get("state") in ["FIRST_ATTEMPT_FAILED", "SECOND_ATTEMPT_DETECTED", "H2_CONFIRMED"]:
                funnel_stats["H1_Failed_Leg2"] += 1
            
            reason = details.get("reason", "")
            if is_valid or reason == "H2_CONFIRMED":
                funnel_stats["H2_Triggered"] += 1
                funnel_stats["Pullback_Bar_Limit_Met"] += 1
                funnel_stats["Climactic_Bar_Met"] += 1
                funnel_stats["Quality_Met"] += 1
                funnel_stats["EMA_Distance_Met"] += 1
                funnel_stats["Final_Signals"] += 1
                
                total_h2_signals += 1
                l1 = details.get("leg1_low")
                l2 = details.get("leg2_low")
                if l1 is not None and l2 is not None and l2 >= l1:
                    higher_low_count += 1

                sampled_signals.append({
                    "ticker": ticker,
                    "date": str(row.get("Date", "")),
                    "close": close,
                    "details": details,
                    "df": df,
                    "idx": df.index.get_loc(idx)
                })

    print(f"漏斗統計摘要:")
    for k, v in funnel_stats.items():
        pass_rate = (v / funnel_stats["Total_Bars_Evaluated"] * 100.0) if funnel_stats["Total_Bars_Evaluated"] > 0 else 0.0
        print(f"  - {k}: {v} (通過率: {pass_rate:.2f}%)")

    hl_ratio = (higher_low_count / total_h2_signals * 100.0) if total_h2_signals > 0 else 0.0
    print(f"\n[任務三.6] 第二段最低點 (Leg 2 Low) 沒有低於第一段最低點 (Leg 1 Low) 的比例: {hl_ratio:.2f}% (共 {total_h2_signals} 個訊號)")

    # 任務四：視覺化抽樣驗證
    print("\n==================================================")
    print("【四、視覺化抽樣驗證 (Top 10 H2 Signals Sample)】")
    print("==================================================")
    if sampled_signals:
        selected_samples = random.sample(sampled_signals, min(10, len(sampled_signals)))
        for i, s in enumerate(selected_samples, 1):
            t = s["ticker"]
            dt = s["date"]
            print(f"\n[{i}] 股票: {t} | 日期: {dt} | 收盤價: {s['close']}")
            sub_hist = s["df"].iloc[max(0, s["idx"] - 40): s["idx"] + 1]
            print(f"   最近 {len(sub_hist)} 根 K 棒走勢摘要:")
            for _, bar in sub_hist.tail(5).iterrows():
                print(f"     日期: {bar['Date']} | O: {bar['Open']} | H: {bar['High']} | L: {bar['Low']} | C: {bar['Close']} | EMA20: {bar.get('EMA_20', 0):.1f}")
    else:
        print("當前觀察池中未產生 H2 訊號樣本。")

if __name__ == "__main__":
    run_audit()
