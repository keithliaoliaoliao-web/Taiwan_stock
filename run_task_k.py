"""
run_task_k.py
嚴格落實 Claude 任務 K 規格：
- 本次不做：廣度濾網、1%以損定量、固定1/3資金、資金曲線/複利模擬、投信濾網
- 評估方式：每筆獨立交易計 1R，無資金限制，同標的持倉中不重複進場
- 三組對照：
  Group A: H2 全條件 (剔除緯創 3231)
  Group B: 順勢任意棒 (Close >= 20EMA)
  Group C: 任務 K (Close >= 20EMA 且 High > 前20日最高價)
- 輸出：task_k_trades.csv 與 task_k_report.md
"""

import os
import time
import pandas as pd
import numpy as np
import config
from data_fetcher import fetch_history

# 嘗試載入 H2 原始引擎
try:
    from price_action_engine import PriceActionEngine
    HAS_PA = True
except Exception:
    HAS_PA = False


def get_tw_tick(price: float) -> float:
    """台股法定升降單位"""
    if price < 10.0: return 0.01
    elif price < 50.0: return 0.05
    elif price < 100.0: return 0.1
    elif price < 500.0: return 0.5
    elif price < 1000.0: return 1.0
    else: return 5.0


def get_tick_down(price: float) -> float:
    """向下退 1 檔 (停損)"""
    tick = get_tw_tick(price)
    if price in [10.0, 50.0, 100.0, 500.0, 1000.0]:
        tick = get_tw_tick(price - 0.001)
    return round(price - tick, 2)


def get_tick_up(price: float) -> float:
    """向上進 1 檔 (觸發進場)"""
    tick = get_tw_tick(price)
    return round(price + tick, 2)


def get_universe_tickers() -> list:
    for fn in ["load_universe", "get_universe", "get_stock_list"]:
        f = getattr(config, fn, None)
        if callable(f):
            try:
                res = f()
                if isinstance(res, dict): return list(res.keys())
                if isinstance(res, (list, tuple)): return [str(x) for x in res]
            except Exception: pass
    return []


def simulate_group_trades(stock_map: dict, group_name: str) -> list:
    cost_rate = 0.00585
    trades = []

    for ticker, df in stock_map.items():
        if group_name == "A_H2" and "3231" in ticker:
            continue  # 規格：A組剔除緯創

        df_len = len(df)
        in_pos = False
        pos_exit_idx = -1

        for i in range(21, df_len - 1):
            if in_pos and i <= pos_exit_idx:
                continue
            in_pos = False

            sig_row = df.iloc[i]
            sig_date = sig_row["Date"]
            if sig_date < pd.Timestamp("2021-01-01"):
                continue

            # 訊號判斷
            is_signal = False
            if group_name == "A_H2":
                is_signal = bool(sig_row.get("Signal_H2_Orig", False))
            elif group_name == "B_AnyBar":
                is_signal = bool(sig_row["Close"] >= sig_row["EMA_20"])
            elif group_name == "C_TaskK":
                prev_20_h = df["High"].iloc[i-20:i].max()
                is_signal = bool(sig_row["Close"] >= sig_row["EMA_20"] and sig_row["High"] > prev_20_h)

            if not is_signal:
                continue

            trigger_price = get_tick_up(float(sig_row["High"]))
            initial_stop = get_tick_down(float(sig_row["Low"]))

            next_bar = df.iloc[i + 1]
            next_open = float(next_bar["Open"])
            next_high = float(next_bar["High"])
            next_low = float(next_bar["Low"])

            # 隔日未過高則不進場
            if next_high < trigger_price:
                continue

            entry_price = max(trigger_price, next_open)
            risk_per_share = entry_price - initial_stop
            if risk_per_share <= 0:
                continue

            entry_date = next_bar["Date"]
            exit_date = entry_date
            exit_price = entry_price
            exit_reason = ""
            days_held = 0

            # 進場當日反轉停損
            if next_low <= initial_stop:
                exit_date = entry_date
                exit_price = min(next_open, initial_stop)
                exit_reason = "SAME_DAY_STOP"
                pos_exit_idx = i + 1
                in_pos = True
            else:
                pending_ema_exit = False
                for k in range(i + 2, df_len):
                    cur_bar = df.iloc[k]
                    days_held += 1
                    cur_open = float(cur_bar["Open"])
                    cur_close = float(cur_bar["Close"])
                    cur_low = float(cur_bar["Low"])
                    cur_ema = float(cur_bar["EMA_20"])

                    if pending_ema_exit:
                        exit_date = cur_bar["Date"]
                        exit_price = cur_open
                        exit_reason = "EXIT_EMA20"
                        pos_exit_idx = k
                        in_pos = True
                        break

                    if cur_low <= initial_stop:
                        exit_date = cur_bar["Date"]
                        exit_price = min(cur_open, initial_stop)
                        exit_reason = "INITIAL_STOP"
                        pos_exit_idx = k
                        in_pos = True
                        break

                    if days_held >= 120 or k == df_len - 1:
                        exit_date = cur_bar["Date"]
                        exit_price = cur_close
                        exit_reason = "MAX_120D"
                        pos_exit_idx = k
                        in_pos = True
                        break

                    if cur_close < cur_ema:
                        pending_ema_exit = True

            net_r = ((exit_price * (1.0 - cost_rate)) - entry_price) / risk_per_share
            trades.append({
                "group": group_name,
                "ticker": ticker,
                "sig_date": str(sig_date)[:10],
                "entry_date": str(entry_date)[:10],
                "exit_date": str(exit_date)[:10],
                "entry_price": entry_price,
                "stop_price": initial_stop,
                "exit_price": exit_price,
                "exit_reason": exit_reason,
                "risk_per_share": risk_per_share,
                "net_r": net_r,
                "days_held": days_held,
                "year": entry_date.year,
                "month_cohort": str(entry_date)[:7]
            })

    return trades


def calc_stats(r_series: pd.Series) -> dict:
    if len(r_series) == 0:
        return {"n": 0, "win_rate": 0, "median": 0, "trim1_mean": 0, "pf": 0, "mean_r": 0}
    n = len(r_series)
    wins = r_series[r_series > 0]
    losses = r_series[r_series <= 0]
    win_rate = (len(wins) / n) * 100
    median_r = r_series.median()
    
    # 剔除最大 1%
    trim_k = max(1, int(np.ceil(n * 0.01)))
    trimmed = r_series.sort_values().iloc[:-trim_k] if n > 10 else r_series
    trim1_mean = trimmed.mean()
    
    pf = (wins.sum() / abs(losses.sum())) if len(losses) > 0 and losses.sum() != 0 else 99.9
    mean_r = r_series.mean()

    return {
        "n": n, "win_rate": win_rate, "median": median_r,
        "trim1_mean": trim1_mean, "pf": pf, "mean_r": mean_r
    }


def bootstrap_diff(df_a: pd.DataFrame, df_b: pd.DataFrame, n_iter: int = 2000, seed: int = 42) -> tuple:
    """按月分群 Block Bootstrap 95% 信賴區間"""
    np.random.seed(seed)
    all_months = sorted(list(set(df_a["month_cohort"].unique()).union(set(df_b["month_cohort"].unique()))))
    m_a = df_a.groupby("month_cohort")["net_r"].mean()
    m_b = df_b.groupby("month_cohort")["net_r"].mean()

    diffs = []
    n_m = len(all_months)
    for _ in range(n_iter):
        sampled_months = np.random.choice(all_months, size=n_m, replace=True)
        mean_a = np.nanmean([m_a.get(m, 0.0) for m in sampled_months])
        mean_b = np.nanmean([m_b.get(m, 0.0) for m in sampled_months])
        diffs.append(mean_b - mean_a)

    return np.percentile(diffs, 2.5), np.percentile(diffs, 97.5)


def main():
    print("【任務 K 規格檢驗啟動】")
    print("本次不做清單：廣度濾網、1%以損定量、固定1/3資金、資金曲線/複利模擬、投信濾網")
    print("每筆獨立交易計 1R，無資金上限，同標的持倉中不重複進場。")

    tickers = get_universe_tickers()
    stock_map = {}
    for t in tickers:
        df = fetch_history(t, lookback_days=2200)
        if not df.empty and len(df) >= 120:
            df = df.copy().sort_values("Date").reset_index(drop=True)
            df["EMA_20"] = df["Close"].ewm(span=20, adjust=False).mean()
            df["Signal_H2_Orig"] = False
            if HAS_PA:
                try:
                    pdf = PriceActionEngine.analyze_setups(df.copy())
                    if "Signal_H2" in pdf.columns:
                        df["Signal_H2_Orig"] = pdf["Signal_H2"].fillna(False).astype(bool)
                except Exception: pass
            stock_map[t] = df
        time.sleep(0.18)

    # 執行三組模擬
    trades_a = simulate_group_trades(stock_map, "A_H2")
    trades_b = simulate_group_trades(stock_map, "B_AnyBar")
    trades_c = simulate_group_trades(stock_map, "C_TaskK")

    all_trades = pd.DataFrame(trades_a + trades_b + trades_c)
    all_trades.to_csv("task_k_trades.csv", index=False, encoding="utf-8-sig")
    print("已輸出 task_k_trades.csv (逐筆交易明細)")

    # 統計指標計算
    df_a = all_trades[all_trades["group"] == "A_H2"]
    df_b = all_trades[all_trades["group"] == "B_AnyBar"]
    df_c = all_trades[all_trades["group"] == "C_TaskK"]

    ci_c_minus_a = bootstrap_diff(df_a, df_c)
    ci_c_minus_b = bootstrap_diff(df_b, df_c)

    # 生成 Markdown 報表
    md = []
    md.append("# 任務 K 嚴格規格檢驗報表\n")
    md.append("## 一、 核心設定原則")
    md.append("- **本次不做**：廣度濾網、1%以損定量、固定 1/3 資金、資產曲線/複利模擬、投信濾網。")
    md.append("- **部位評估**：每筆獨立交易計算 Net R，無資金上限限制，同標的持倉中不重複進場。\n")

    md.append("## 二、 三組全期間 vs 排除 2023 表現對照")
    md.append("| 組別 | 期間 | 成交筆數 | 勝率 | 單筆中位數 | 剔除最大1%平均 | 獲利因子 (PF) | 平均淨 R |")
    md.append("| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |")

    for name, df_sub in [("A組 (H2不含BOS/無緯創)", df_a), ("B組 (順勢任意棒)", df_b), ("C組 (任務K 突破20日高)", df_c)]:
        s_all = calc_stats(df_sub["net_r"])
        s_no23 = calc_stats(df_sub[df_sub["year"] != 2023]["net_r"])
        md.append(f"| {name} | 全期間 (2021-2026) | {s_all['n']} | {s_all['win_rate']:.1f}% | {s_all['median']:+.2f}R | {s_all['trim1_mean']:+.2f}R | {s_all['pf']:.2f} | **{s_all['mean_r']:+.3f}R** |")
        md.append(f"| {name} | 排除 2023 | {s_no23['n']} | {s_no23['win_rate']:.1f}% | {s_no23['median']:+.2f}R | {s_no23['trim1_mean']:+.2f}R | {s_no23['pf']:.2f} | **{s_no23['mean_r']:+.3f}R** |")

    md.append("\n## 三、 組間差值與按月分群 95% 信賴區間 (2000次 Bootstrap, seed=42)")
    md.append(f"- **C 組 vs A 組 (任務K - H2)**：差值 {df_c['net_r'].mean() - df_a['net_r'].mean():+.3f}R，95% CI [{ci_c_minus_a[0]:+.3f}R, {ci_c_minus_a[1]:+.3f}R]")
    md.append(f"- **C 組 vs B 組 (任務K - 任意棒)**：差值 {df_c['net_r'].mean() - df_b['net_r'].mean():+.3f}R，95% CI [{ci_c_minus_b[0]:+.3f}R, {ci_c_minus_b[1]:+.3f}R]\n")

    md.append("## 四、 各組最大 5 筆獲利交易")
    for name, df_sub in [("A組 (H2)", df_a), ("B組 (順勢任意棒)", df_b), ("C組 (任務K)", df_c)]:
        md.append(f"### {name}")
        top5 = df_sub.sort_values("net_r", ascending=False).head(5)
        for _, r in top5.iterrows():
            md.append(f"- {r['ticker']} | 進場: {r['entry_date']} (${r['entry_price']}) \vert{} 出場: {r['exit_date']} (${r['exit_price']}) | 原因: {r['exit_reason']} | **{r['net_r']:+.2f}R**")

    md.append("\n## 五、 回測核心邏輯程式碼原文")
    md.append("```python")
    md.append("# 1. 訊號判斷")
    md.append("prev_20_high = df['High'].iloc[i-20:i].max()")
    md.append("is_signal = (sig_row['Close'] >= sig_row['EMA_20']) and (sig_row['High'] > prev_20_high)")
    md.append("")
    md.append("# 2. 進場價 (次日破最高價下一檔進場，跳空開高以開盤價計)")
    md.append("trigger_price = get_tick_up(float(sig_row['High']))")
    md.append("if next_high >= trigger_price:")
    md.append("    entry_price = max(trigger_price, next_open)")
    md.append("")
    md.append("# 3. 停損價 (訊號棒最低價退下一檔)")
    md.append("initial_stop = get_tick_down(float(sig_row['Low']))")
    md.append("```")

    report_text = "\n".join(md)
    with open("task_k_report.md", "w", encoding="utf-8") as f:
        f.write(report_text)
    print("已輸出 task_k_report.md")
    print("\n" + report_text)


if __name__ == "__main__":
    main()
