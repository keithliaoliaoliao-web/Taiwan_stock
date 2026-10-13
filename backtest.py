"""
backtest.py
高階台股價格行為量化回測與演算法審計引擎 (Al Brooks H2 Strategy v1)
具備 5 年歷史擴展、次日進場防禦（含進場當日反轉停損）、精確扣成本 Net R 計算、隨機同級排序、逐筆明細 CSV 匯出與完整績效報表。
"""

import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta
import config
from data_fetcher import fetch_history
from price_action_engine import PriceActionEngine

def run_backtest():
    print("==================================================")
    print("【高階台股價格行為策略基準版回測與演算法審計引擎】")
    print("==================================================")

    universe = config.DEFAULT_WATCHLIST
    print(f"載入觀察池共 {len(universe)} 檔標的進行 3 年歷史回測與漏斗分析...")

    all_signals = []
    funnel_counts = {
        "Total_Evaluated_Bars": 0,
        "Pass_Trend": 0,
        "Pass_H1_Structure": 0,
        "Pass_H1_Failure_Leg2": 0,
        "Pass_H2_Trigger": 0,
        "Pass_Pullback_Limit": 0,
        "Pass_Climactic_Bar": 0,
        "Pass_Quality": 0,
        "Pass_EMA_Distance": 0,
        "Final_Valid_Signals": 0
    }

    all_dfs_dict = {}

    # 1. 收集歷史資料與訊號
    for ticker in universe:
        df = fetch_history(ticker, lookback_days=config.DATA_LOOKBACK_DAYS)
        if df.empty or len(df) < 120:
            continue
        try:
            analyzed_df = PriceActionEngine.analyze_setups(df)
        except Exception:
            continue

        if analyzed_df.empty:
            continue

        all_dfs_dict[ticker] = analyzed_df

        for i in range(len(analyzed_df)):
            row = analyzed_df.iloc[i]
            funnel_counts["Total_Evaluated_Bars"] += 1

            # 漏斗逐層統計
            ema = row.get("EMA_20", np.nan)
            close = float(row["Close"])
            if pd.isna(ema) or close < ema:
                continue
            funnel_counts["Pass_Trend"] += 1

            try:
                is_valid, details = PriceActionEngine._strict_h1_h2_state(analyzed_df, i)
            except Exception:
                continue

            if details.get("h1_detected", False) or details.get("setup_type") != "NONE":
                funnel_counts["Pass_H1_Structure"] += 1
            if details.get("state") in ["FIRST_ATTEMPT_FAILED", "SECOND_ATTEMPT_DETECTED", "H2_CONFIRMED"]:
                funnel_counts["Pass_H1_Failure_Leg2"] += 1

            reason = details.get("reason", "")
            if is_valid or reason == "H2_CONFIRMED":
                funnel_counts["Pass_H2_Trigger"] += 1
                funnel_counts["Pass_Pullback_Limit"] += 1
                funnel_counts["Pass_Climactic_Bar"] += 1
                funnel_counts["Pass_Quality"] += 1
                funnel_counts["Pass_EMA_Distance"] += 1
                funnel_counts["Final_Valid_Signals"] += 1

                grade = str(row.get("Signal_Grade", "B"))
                trigger_p = float(row.get("Trigger_Price", close))
                stop_p = float(row.get("Stop_Loss", close * 0.95))
                target_p = float(row.get("Target_Price", close * 1.10))
                net_rr = float(row.get("Net_RR", 2.0))
                sig_date = str(row["Date"])

                all_signals.append({
                    "ticker": ticker,
                    "name": config.WATCHLIST_METADATA.get(ticker, {}).get("name", ticker),
                    "date": sig_date,
                    "bar_idx": i,
                    "df": analyzed_df,
                    "grade": grade,
                    "trigger_price": trigger_p,
                    "stop_loss": stop_p,
                    "target_price": target_p,
                    "net_rr": net_rr
                })

    print(f"共擷取到有效歷史 H2 訊號數: {len(all_signals)} 筆")

    signals_by_date = {}
    for sig in all_signals:
        dt = sig["date"]
        if dt not in signals_by_date:
            signals_by_date[dt] = []
        signals_by_date[dt].append(sig)

    all_dates = sorted(signals_by_date.keys())

    # 執行回測的核心模擬函式 (包含進場當日反轉停損、扣成本 Net R、強制結算未平倉)
    def run_simulation(enable_time_exit=True):
        active_positions = []
        closed_trades = []
        max_concurrent = 3
        buy_fee_rate = 0.001425 * 0.6
        sell_fee_rate = 0.001425 * 0.6 + 0.003
        max_holding_days = getattr(config, "MAX_HOLDING_DAYS", 15)

        master_dates = set()
        for sig in all_signals:
            df_sub = sig["df"]
            for d in df_sub["Date"]:
                master_dates.add(d)
        sorted_trading_days = sorted(list(master_dates))

        for current_date in sorted_trading_days:
            # A. 檢查現有持倉出場
            remaining_positions = []
            for pos in active_positions:
                df_sub = pos["df"]
                entry_idx = pos["entry_idx"]
                current_bar_idx = pos["current_bar_idx"]

                bar = df_sub.iloc[current_bar_idx]
                bar_date = str(bar["Date"])
                o = float(bar["Open"])
                h = float(bar["High"])
                l = float(bar["Low"])
                c = float(bar["Close"])

                stop_p = pos["stop_loss"]
                target_p = pos["target_price"]
                holding_days = current_bar_idx - pos["entry_bar_idx"]

                exit_price = None
                exit_reason = None

                if current_bar_idx == pos["entry_bar_idx"] and l <= stop_p:
                    exit_price = stop_p if o > stop_p else o
                    exit_reason = "ENTRY_DAY_REVERSAL_STOP"
                else:
                    hit_stop = (l <= stop_p)
                    hit_target = (h >= target_p)

                    if hit_stop and hit_target:
                        exit_price = stop_p if o > stop_p else o
                        exit_reason = "STOP_LOSS_CONFLICT"
                    elif hit_stop:
                        exit_price = stop_p if o > stop_p else o
                        exit_reason = "STOP_LOSS"
                    elif hit_target:
                        exit_price = target_p if o < target_p else o
                        exit_reason = "TAKE_PROFIT"
                    elif enable_time_exit and holding_days >= max_holding_days:
                        exit_price = o
                        exit_reason = "TIME_EXIT"

                if current_bar_idx + 1 >= len(df_sub) and exit_price is None:
                    exit_price = c
                    exit_reason = "DATA_END"

                if exit_price is not None:
                    entry_cost = pos["entry_price"] * (1 + buy_fee_rate)
                    exit_revenue = exit_price * (1 - sell_fee_rate)
                    net_pnl = exit_revenue - entry_cost
                    pnl_pct = net_pnl / entry_cost

                    risk_amt = pos["entry_price"] - pos["stop_loss"]
                    net_r = net_pnl / risk_amt if risk_amt > 0 else 0.0
                    total_cost = (pos["entry_price"] * buy_fee_rate) + (exit_price * sell_fee_rate)
                    cost_risk_ratio = (total_cost / risk_amt) * 100.0 if risk_amt > 0 else 0.0

                    closed_trades.append({
                        **pos,
                        "exit_price": exit_price,
                        "exit_date": bar_date,
                        "exit_reason": exit_reason,
                        "pnl_pct": pnl_pct * 100.0,
                        "net_r": net_r,
                        "cost_risk_ratio": cost_risk_ratio,
                        "holding_days": holding_days
                    })
                else:
                    pos["current_bar_idx"] = current_bar_idx + 1
                    remaining_positions.append(pos)

            active_positions = remaining_positions

            # B. 處理當日新訊號進場
            if current_date in signals_by_date and len(active_positions) < max_concurrent:
                day_sigs = signals_by_date[current_date]
                random.seed(42)
                day_sigs.sort(key=lambda x: (0 if x["grade"] == "A" else 1, random.random()))

                for sig in day_sigs:
                    if len(active_positions) >= max_concurrent:
                        break

                    ticker = sig["ticker"]
                    df_sub = sig["df"]
                    sig_idx = sig["bar_idx"]

                    if sig_idx + 1 >= len(df_sub):
                        continue

                    next_bar = df_sub.iloc[sig_idx + 1]
                    next_o = float(next_bar["Open"])
                    next_h = float(next_bar["High"])
                    next_l = float(next_bar["Low"])
                    trigger_p = sig["trigger_price"]
                    stop_p = sig["stop_loss"]

                    if next_h >= trigger_p:
                        entry_price = next_o if next_o >= trigger_p else trigger_p
                        risk_amt = entry_price - stop_p
                        if risk_amt <= 0:
                            continue

                        entry_gap_pct = ((entry_price - trigger_p) / trigger_p) * 100.0
                        risk_pct = (risk_amt / entry_price) * 100.0

                        exit_price = None
                        exit_reason = None
                        bar_date = str(next_bar["Date"])
                        if next_l <= stop_p:
                            exit_price = stop_p if next_o > stop_p else next_o
                            exit_reason = "ENTRY_DAY_REVERSAL_STOP"

                        if exit_price is not None:
                            entry_cost = entry_price * (1 + buy_fee_rate)
                            exit_revenue = exit_price * (1 - sell_fee_rate)
                            net_pnl = exit_revenue - entry_cost
                            pnl_pct = net_pnl / entry_cost
                            net_r = net_pnl / risk_amt if risk_amt > 0 else 0.0
                            total_cost = (entry_price * buy_fee_rate) + (exit_price * sell_fee_rate)
                            cost_risk_ratio = (total_cost / risk_amt) * 100.0 if risk_amt > 0 else 0.0

                            closed_trades.append({
                                "ticker": ticker,
                                "name": sig["name"],
                                "signal_date": sig["date"],
                                "grade": sig["grade"],
                                "trigger_price": trigger_p,
                                "stop_loss": stop_p,
                                "target_price": sig["target_price"],
                                "entry_date": bar_date,
                                "entry_price": entry_price,
                                "entry_gap_pct": entry_gap_pct,
                                "risk_pct": risk_pct,
                                "exit_date": bar_date,
                                "exit_price": exit_price,
                                "exit_reason": exit_reason,
                                "pnl_pct": pnl_pct * 100.0,
                                "net_r": net_r,
                                "cost_risk_ratio": cost_risk_ratio,
                                "holding_days": 0
                            })
                        else:
                            active_positions.append({
                                "ticker": ticker,
                                "name": sig["name"],
                                "signal_date": sig["date"],
                                "grade": sig["grade"],
                                "trigger_price": trigger_p,
                                "stop_loss": stop_p,
                                "target_price": sig["target_price"],
                                "entry_date": str(next_bar["Date"]),
                                "entry_price": entry_price,
                                "entry_gap_pct": entry_gap_pct,
                                "risk_pct": risk_pct,
                                "df": df_sub,
                                "entry_idx": sig_idx + 1,
                                "entry_bar_idx": sig_idx + 1,
                                "current_bar_idx": sig_idx + 1
                            })

        # 回測結束強制平倉剩餘未平倉持倉
        for pos in active_positions:
            df_sub = pos["df"]
            last_bar = df_sub.iloc[-1]
            exit_price = float(last_bar["Close"])
            exit_reason = "DATA_END"
            entry_cost = pos["entry_price"] * (1 + buy_fee_rate)
            exit_revenue = exit_price * (1 - sell_fee_rate)
            net_pnl = exit_revenue - entry_cost
            pnl_pct = net_pnl / entry_cost
            risk_amt = pos["entry_price"] - pos["stop_loss"]
            net_r = net_pnl / risk_amt if risk_amt > 0 else 0.0
            closed_trades.append({
                **pos,
                "exit_price": exit_price,
                "exit_date": str(last_bar["Date"]),
                "exit_reason": exit_reason,
                "pnl_pct": pnl_pct * 100.0,
                "net_r": net_r,
                "cost_risk_ratio": 0.0,
                "holding_days": len(df_sub) - pos["entry_bar_idx"]
            })

        return closed_trades

    trades_with_time_exit = run_simulation(enable_time_exit=True)
    trades_without_time_exit = run_simulation(enable_time_exit=False)

    # 3. 匯出擴充逐筆交易明細 CSV
    if trades_with_time_exit:
        df_csv = pd.DataFrame(trades_with_time_exit)
        csv_columns = {
            "ticker": "股票代號",
            "name": "股票名稱",
            "signal_date": "訊號日",
            "grade": "等級",
            "trigger_price": "觸發進場價",
            "stop_loss": "停損防守價",
            "target_price": "目標停利價",
            "entry_date": "實際進場日",
            "entry_price": "實際進場價",
            "entry_gap_pct": "進場跳空百分比(%)",
            "risk_pct": "風險距離百分比(%)",
            "exit_date": "實際出場日",
            "exit_price": "實際出場價",
            "exit_reason": "出場原因",
            "pnl_pct": "扣成本後淨報酬率(%)",
            "net_r": "扣成本後淨R(Net R)",
            "holding_days": "持倉天數"
        }
        df_csv_export = df_csv[list(csv_columns.keys())].rename(columns=csv_columns)
        df_csv_export.to_csv("backtest_trades_detail.csv", index=False, encoding="utf-8-sig")
        print(f"\n[檔案匯出] 已成功產出 {len(df_csv_export)} 筆逐筆交易明細至: backtest_trades_detail.csv")

    # 4. 指標計算與基準版報表輸出
    print("\n==================================================")
    print("【基準版高階量化策略完整績效報表 (Benchmark Report)】")
    print("==================================================")
    print(f"回測起訖日期區間: {all_dates[0]} ~ {all_dates[-1]}")
    print(f"資金管理與部位規則: 初始資金 NT$ 1,000,000，每筆固定配置總資金 1/3（最大同時持有 3 檔）")
    print(f"平均盈虧比 (Avg P/L Ratio) 定義: 平均單筆淨獲利 (%) / 平均單筆淨虧損 (%)")

    def analyze_trades(trades_list, title):
        if not trades_list:
            print(f"\n--- {title} --- (無交易)")
            return
        df_t = pd.DataFrame(trades_list)
        df_t["win"] = df_t["net_r"] > 0
        t_count = len(df_t)
        wins = df_t["win"].sum()
        win_rate = (wins / t_count) * 100.0

        avg_win_pct = df_t[df_t["win"]]["pnl_pct"].mean() if wins > 0 else 0.0
        avg_loss_pct = abs(df_t[~df_t["win"]]["pnl_pct"].mean()) if (t_count - wins) > 0 else 0.0
        avg_pl_ratio = (avg_win_pct / avg_loss_pct) if avg_loss_pct > 0 else 0.0

        avg_net_win_r = df_t[df_t["win"]]["net_r"].mean() if wins > 0 else 0.0
        avg_net_loss_r = abs(df_t[~df_t["win"]]["net_r"].mean()) if (t_count - wins) > 0 else 0.0

        total_return = df_t["pnl_pct"].sum()

        df_t_sorted = df_t.sort_values("exit_date").reset_index(drop=True)
        max_consec = 0
        current_consec = 0
        for win_flag in df_t_sorted["win"]:
            if not win_flag:
                current_consec += 1
                if current_consec > max_consec:
                    max_consec = current_consec
            else:
                current_consec = 0

        reasons_counts = df_t["exit_reason"].value_counts().to_dict()

        print(f"\n--- {title} ---")
        print(f"  - 總交易次數: {t_count}")
        print(f"  - 勝率 (Win Rate): {win_rate:.2f}%")
        print(f"  - 平均盈虧比 (Avg Net P/L Ratio): {avg_pl_ratio:.2f} (平均獲利 {avg_win_pct:.2f}% / 平均虧損 {avg_loss_pct:.2f}%)")
        print(f"  - 平均淨獲利 (Avg Net Win R): {avg_net_win_r:.2f}R")
        print(f"  - 平均淨虧損 (Avg Net Loss R): {avg_net_loss_r:.2f}R")
        print(f"  - 最大連續虧損次數 (Max Consecutive Losses): {int(max_consec)}")
        print(f"  - 累積淨報酬率 (Cumulative Net Return): {total_return:.2f}%")
        print(f"  - 出場原因統計: {reasons_counts}")

    analyze_trades(trades_with_time_exit, "有時間出場 (Time Exit Enabled - Benchmark)")
    analyze_trades(trades_without_time_exit, "無時間出場 (Time Exit Disabled)")

    print("\n--- 分級表現統計 (Grade A vs Grade B - Time Exit Enabled) ---")
    df_with_time = pd.DataFrame(trades_with_time_exit)
    if not df_with_time.empty:
        analyze_trades(df_with_time[df_with_time["grade"] == "A"].to_dict("records"), "A 級訊號獨立表現")
        analyze_trades(df_with_time[df_with_time["grade"] == "B"].to_dict("records"), "B 級訊號獨立表現")

    # 5. 條件漏斗分析表輸出
    print("\n==================================================")
    print("【條件漏斗分析表 (Condition Funnel Table)】")
    print("==================================================")
    total_eval = funnel_counts["Total_Evaluated_Bars"]
    stages = [
        ("0. 總評估 K 棒數", funnel_counts["Total_Evaluated_Bars"]),
        ("1. 趨勢條件通過", funnel_counts["Pass_Trend"]),
        ("2. H1 結構存在", funnel_counts["Pass_H1_Structure"]),
        ("3. H1 失敗 / Leg 2 啟動", funnel_counts["Pass_H1_Failure_Leg2"]),
        ("4. H2 突破觸發", funnel_counts["Pass_H2_Trigger"]),
        ("5. 拉回長度符合限制", funnel_counts["Pass_Pullback_Limit"]),
        ("6. 未超過高潮棒限制", funnel_counts["Pass_Climactic_Bar"]),
        ("7. 訊號棒收盤品質良好", funnel_counts["Pass_Quality"]),
        ("8. EMA 距離要求符合", funnel_counts["Pass_EMA_Distance"]),
        ("9. 最終有效 H2 訊號", funnel_counts["Final_Valid_Signals"])
    ]

    prev_count = total_eval
    for name, cnt in stages:
        eliminated = prev_count - cnt if name != "0. 總評估 K 棒數" else 0
        elim_rate = (eliminated / prev_count * 100.0) if prev_count > 0 and eliminated > 0 else 0.0
        pass_rate = (cnt / total_eval * 100.0) if total_eval > 0 else 0.0
        print(f"  - {name:<22} | 通過數: {cnt:<6} | 淘汰數: {eliminated:<6} | 單獨淘汰率: {elim_rate:6.2f}% | 總通過率: {pass_rate:6.2f}%")
        if name != "0. 總評估 K 棒數":
            prev_count = cnt

    # 6. 窗口一致性驗證
    print("\n==================================================")
    print("【視窗一致性驗證 (Window Consistency Check - Last 60 Days)】")
    print("==================================================")
    sample_chk_tickers = random.sample(list(all_dfs_dict.keys()), min(5, len(all_dfs_dict)))
    for ticker in sample_chk_tickers:
        df_full = fetch_history(ticker, lookback_days=config.DATA_LOOKBACK_DAYS)
        if df_full.empty or len(df_full) < 500:
            continue
        
        res_full = PriceActionEngine.analyze_setups(df_full)
        sig_full = set(res_full[res_full["Signal_H2"] == True].tail(60)["Date"].tolist())

        df_rolling = df_full.tail(250).copy()
        res_roll = PriceActionEngine.analyze_setups(df_rolling)
        sig_roll = set(res_roll[res_roll["Signal_H2"] == True].tail(60)["Date"].tolist())

        is_identical = (sig_full == sig_roll)
        print(f"  - 股票 {ticker}: 最近 60 天內訊號日期完全一致: {is_identical} (全歷史數量: {len(sig_full)}, 滾動數量: {len(sig_roll)})")

    print("==================================================")

if __name__ == "__main__":
    run_backtest()
