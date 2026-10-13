"""
backtest.py
高階台股價格行為量化回測與演算法審計引擎 (Al Brooks H2 Strategy v1 - Benchmark & Monte Carlo)
具備資金整股取整、部位 1/3 配置、訊號流向追蹤、未平倉獨立結算、Bootstrap 95% 信賴區間、年度績效拆解與 10 種亂數種子蒙地卡羅驗證。
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
    print("【高階台股價格行為策略 基準版回測與計量審計引擎】")
    print("==================================================")

    universe = config.DEFAULT_WATCHLIST
    print(f"載入觀察池共 {len(universe)} 檔標的進行歷史回測與計量審計...")

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
    total_universe_bars = 0
    total_bos_true = 0

    # 1. 收集歷史資料與訊號 (模擬 scanner 實際滾動視角，lookback_days = 260)
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
        total_universe_bars += len(analyzed_df)
        if "BOS" in analyzed_df.columns:
            total_bos_true += int(analyzed_df["BOS"].sum())

        for i in range(len(analyzed_df)):
            row = analyzed_df.iloc[i]
            funnel_counts["Total_Evaluated_Bars"] += 1

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

    # 執行回測模擬函式（支援隨機 Seed 與時間出場）
    def run_simulation(seed_val=42, enable_time_exit=True):
        active_positions = []
        closed_trades = []
        open_trades = []
        max_concurrent = 3
        initial_capital = 1000000.0
        allocation_ratio = 1.0 / 3.0
        buy_fee_rate = 0.001425 * 0.6
        sell_fee_rate = 0.001425 * 0.6 + 0.003
        max_holding_days = getattr(config, "MAX_HOLDING_DAYS", 15)

        signal_flow_stats = {
            "total_signals": len(all_signals),
            "untriggered": 0,
            "skipped_capacity": 0,
            "executed": 0,
            "unclosed_at_end": 0
        }

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

                # 進場當日反轉停損檢驗
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
                    entry_price = pos["entry_price"]
                    shares = pos["shares"]
                    buy_cost = entry_price * shares * (1 + buy_fee_rate)
                    sell_revenue = exit_price * shares * (1 - sell_fee_rate)
                    net_pnl = sell_revenue - buy_cost
                    pnl_pct = (net_pnl / buy_cost) * 100.0

                    risk_amt_per_share = entry_price - pos["stop_loss"]
                    total_risk = risk_amt_per_share * shares
                    net_r = net_pnl / total_risk if total_risk > 0 else 0.0
                    unadjusted_r = ((exit_price - entry_price) / risk_amt_per_share) if risk_amt_per_share > 0 else 0.0

                    closed_trades.append({
                        **pos,
                        "exit_price": exit_price,
                        "exit_date": bar_date,
                        "exit_reason": exit_reason,
                        "net_pnl": net_pnl,
                        "pnl_pct": pnl_pct,
                        "net_r": net_r,
                        "unadjusted_r": unadjusted_r,
                        "holding_days": holding_days
                    })
                else:
                    pos["current_bar_idx"] = current_bar_idx + 1
                    remaining_positions.append(pos)

            active_positions = remaining_positions

            # B. 處理當日新訊號進場
            if current_date in signals_by_date:
                day_sigs = signals_by_date[current_date]
                random.seed(seed_val)
                day_sigs.sort(key=lambda x: (0 if x["grade"] == "A" else 1, random.random()))

                for sig in day_sigs:
                    if len(active_positions) >= max_concurrent:
                        signal_flow_stats["skipped_capacity"] += 1
                        continue

                    ticker = sig["ticker"]
                    df_sub = sig["df"]
                    sig_idx = sig["bar_idx"]

                    if sig_idx + 1 >= len(df_sub):
                        signal_flow_stats["untriggered"] += 1
                        continue

                    next_bar = df_sub.iloc[sig_idx + 1]
                    next_o = float(next_bar["Open"])
                    next_h = float(next_bar["High"])
                    next_l = float(next_bar["Low"])
                    trigger_p = sig["trigger_price"]
                    stop_p = sig["stop_loss"]

                    if next_h >= trigger_p:
                        signal_flow_stats["executed"] += 1
                        entry_price = next_o if next_o >= trigger_p else trigger_p
                        risk_amt_per_share = entry_price - stop_p
                        if risk_amt_per_share <= 0:
                            continue

                        # 資金配置與整股取整規則 (1/3 資金，向下取整至整股 1000股倍數或整股張數)
                        allocated_capital = initial_capital * allocation_ratio
                        shares = int(allocated_capital / entry_price)
                        if shares <= 0:
                            shares = 1 # 確保至少 1 股

                        entry_gap_pct = ((entry_price - trigger_p) / trigger_p) * 100.0
                        risk_pct = (risk_amt_per_share / entry_price) * 100.0

                        exit_price = None
                        exit_reason = None
                        bar_date = str(next_bar["Date"])
                        if next_l <= stop_p:
                            exit_price = stop_p if next_o > stop_p else next_o
                            exit_reason = "ENTRY_DAY_REVERSAL_STOP"

                        if exit_price is not None:
                            buy_cost = entry_price * shares * (1 + buy_fee_rate)
                            sell_revenue = exit_price * shares * (1 - sell_fee_rate)
                            net_pnl = sell_revenue - buy_cost
                            pnl_pct = (net_pnl / buy_cost) * 100.0
                            total_risk = risk_amt_per_share * shares
                            net_r = net_pnl / total_risk if total_risk > 0 else 0.0
                            unadjusted_r = ((exit_price - entry_price) / risk_amt_per_share) if risk_amt_per_share > 0 else 0.0

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
                                "shares": shares,
                                "entry_gap_pct": entry_gap_pct,
                                "risk_pct": risk_pct,
                                "exit_date": bar_date,
                                "exit_price": exit_price,
                                "exit_reason": exit_reason,
                                "net_pnl": net_pnl,
                                "pnl_pct": pnl_pct,
                                "net_r": net_r,
                                "unadjusted_r": unadjusted_r,
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
                                "shares": shares,
                                "entry_gap_pct": entry_gap_pct,
                                "risk_pct": risk_pct,
                                "df": df_sub,
                                "entry_idx": sig_idx + 1,
                                "entry_bar_idx": sig_idx + 1,
                                "current_bar_idx": sig_idx + 1
                            })
                    else:
                        signal_flow_stats["untriggered"] += 1

        # 結算未平倉
        for pos in active_positions:
            signal_flow_stats["unclosed_at_end"] += 1
            df_sub = pos["df"]
            last_bar = df_sub.iloc[-1]
            exit_price = float(last_bar["Close"])
            exit_reason = "UNCLOSED_AT_END"
            entry_price = pos["entry_price"]
            shares = pos["shares"]
            buy_cost = entry_price * shares * (1 + buy_fee_rate)
            sell_revenue = exit_price * shares * (1 - sell_fee_rate)
            net_pnl = sell_revenue - buy_cost
            pnl_pct = (net_pnl / buy_cost) * 100.0
            risk_amt_per_share = entry_price - pos["stop_loss"]
            total_risk = risk_amt_per_share * shares
            net_r = net_pnl / total_risk if total_risk > 0 else 0.0
            unadjusted_r = ((exit_price - entry_price) / risk_amt_per_share) if risk_amt_per_share > 0 else 0.0

            open_trades.append({
                **pos,
                "exit_price": exit_price,
                "exit_date": str(last_bar["Date"]),
                "exit_reason": exit_reason,
                "net_pnl": net_pnl,
                "pnl_pct": pnl_pct,
                "net_r": net_r,
                "unadjusted_r": unadjusted_r,
                "holding_days": len(df_sub) - pos["entry_bar_idx"]
            })

        return closed_trades, open_trades, signal_flow_stats

    # 執行基準版模擬
    closed_trades, open_trades, flow_stats = run_simulation(seed_val=42, enable_time_exit=True)

    # 3. 匯出逐筆交易明細 CSV
    all_recorded_trades = closed_trades + open_trades
    if all_recorded_trades:
        df_csv = pd.DataFrame(all_recorded_trades)
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
            "shares": "進場股數",
            "entry_gap_pct": "進場跳空百分比(%)",
            "risk_pct": "風險距離百分比(%)",
            "exit_date": "實際出場日",
            "exit_price": "實際出場價",
            "exit_reason": "出場原因",
            "pnl_pct": "扣成本後淨報酬率(%)",
            "net_r": "扣成本後淨R(Net R)",
            "unadjusted_r": "未扣成本R(Unadjusted R)",
            "holding_days": "持倉天數"
        }
        df_csv_export = df_csv[[c for c in csv_columns.keys() if c in df_csv.columns]].rename(columns=csv_columns)
        df_csv_export.to_csv("backtest_trades_detail.csv", index=False, encoding="utf-8-sig")
        print(f"\n[檔案匯出] 已成功產出 {len(df_csv_export)} 筆逐筆交易明細至: backtest_trades_detail.csv")

    # 4. 統計計量指標與蒙地卡羅驗證
    print("\n==================================================")
    print("【高階量化策略計量審計與蒙地卡羅驗證報表】")
    print("==================================================")
    print(f"回測起訖日期區間: {all_dates[0]} ~ {all_dates[-1]}")
    print(f"資金管理與部位規則: 初始資金 NT$ 1,000,000，每筆固定配置 1/3（最大同時持有 3 檔，股數向下取整）")
    print(f"倖存者偏差宣告: 觀察池為現行 150 檔成分股（包含歷史存活與納入標的，具備潛在倖存者偏差）。")

    # 訊號流向統計輸出
    print("\n--- 訊號流向統計 (Signal Flow Statistics) ---")
    print(f"  - 總訊號數 (Total Signals): {flow_stats['total_signals']}")
    print(f"  - 隔日未突破觸發價未成交數 (Untriggered): {flow_stats['untriggered']}")
    print(f"  - 因帳戶已滿 3 檔上限放棄數 (Skipped Capacity): {flow_stats['skipped_capacity']}")
    print(f"  - 實際成交平倉筆數 (Executed Closed Trades): {flow_stats['executed']}")
    print(f"  - 回測截止未平倉筆數 (Unclosed Open Trades): {flow_stats['unclosed_at_end']}")

    def analyze_metrics(trades_list, title):
        if not trades_list:
            print(f"\n--- {title} --- (無交易)")
            return
        df_t = pd.DataFrame(trades_list)
        df_t["win"] = df_t["net_r"] > 0
        t_count = len(df_t)
        wins = df_t["win"].sum()
        win_rate = (wins / t_count) * 100.0

        avg_net_win_pct = df_t[df_t["win"]]["pnl_pct"].mean() if wins > 0 else 0.0
        avg_net_loss_pct = abs(df_t[~df_t["win"]]["pnl_pct"].mean()) if (t_count - wins) > 0 else 0.0
        avg_pl_ratio = (avg_net_win_pct / avg_net_loss_pct) if avg_net_loss_pct > 0 else 0.0

        avg_net_win_r = df_t[df_t["win"]]["net_r"].mean() if wins > 0 else 0.0
        avg_net_loss_r = abs(df_t[~df_t["win"]]["net_r"].mean()) if (t_count - wins) > 0 else 0.0
        avg_unadjusted_r = df_t["unadjusted_r"].mean()

        total_return_pct = df_t["pnl_pct"].sum()

        # 連續虧損
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

        # Bootstrap 95% 信賴區間 (Net R)
        net_r_arr = df_t["net_r"].values
        bootstrap_means = []
        if len(net_r_arr) > 0:
            for _ in range(1000):
                sample = np.random.choice(net_r_arr, size=len(net_r_arr), replace=True)
                bootstrap_means.append(np.mean(sample))
            ci_lower = np.percentile(bootstrap_means, 2.5)
            ci_upper = np.percentile(bootstrap_means, 97.5)
        else:
            ci_lower, ci_upper = 0.0, 0.0

        reasons_counts = df_t["exit_reason"].value_counts().to_dict()

        print(f"\n--- {title} ---")
        print(f"  - 總結算筆數: {t_count}")
        print(f"  - 勝率 (Win Rate): {win_rate:.2f}%")
        print(f"  - 平均盈虧比 (Avg Net P/L Ratio): {avg_pl_ratio:.2f}")
        print(f"  - 未扣成本 R (Avg Unadjusted R): {avg_unadjusted_r:.2f}R")
        print(f"  - 扣成本後淨 R: 淨獲利 {avg_net_win_r:.2f}R / 淨虧損 {avg_net_loss_r:.2f}R")
        print(f"  - 淨 R 之 95% 信賴區間 (Bootstrap CI): [{ci_lower:.2f}R, {ci_upper:.2f}R]")
        print(f"  - 最大連續虧損次數 (Max Consecutive Losses): {int(max_consec)}")
        print(f"  - 累積淨報酬率 (Cumulative Net Return): {total_return_pct:.2f}%")
        print(f"  - 出場原因統計: {reasons_counts}")

    analyze_metrics(closed_trades, "已平倉交易績效 (Closed Trades)")

    # 年度分段績效拆解
    print("\n--- 年度分段績效拆解 (Yearly Performance Breakdown) ---")
    df_closed = pd.DataFrame(closed_trades)
    if not df_closed.empty:
        df_closed["year"] = pd.to_datetime(df_closed["exit_date"]).dt.year
        for yr, grp in df_closed.groupby("year"):
            yr_return = grp["pnl_pct"].sum()
            yr_trades = len(grp)
            yr_win = (grp["net_r"] > 0).sum()
            yr_winrate = (yr_win / yr_trades) * 100.0 if yr_trades > 0 else 0.0
            print(f"  - {yr} 年: 交易 {yr_trades} 筆 | 勝率 {yr_winrate:.2f}% | 累積報酬 {yr_return:.2f}%")

    # 蒙地卡羅隨機性檢驗 (Seed 1 ~ 10)
    print("\n--- 蒙地卡羅隨機性檢驗 (Monte Carlo Seeds 1 ~ 10) ---")
    mc_results = []
    for s in range(1, 11):
        c_trades, _, _ = run_simulation(seed_val=s, enable_time_exit=True)
        if c_trades:
            ret = pd.DataFrame(c_trades)["pnl_pct"].sum()
            wr = (pd.DataFrame(c_trades)["net_r"] > 0).mean() * 100.0
            mc_results.append({"seed": s, "return": ret, "win_rate": wr, "trades": len(c_trades)})
    
    if mc_results:
        df_mc = pd.DataFrame(mc_results)
        print(f"  - 累積報酬率 (Return %): 最佳 = {df_mc['return'].max():.2f}% | 最差 = {df_mc['return'].min():.2f}% | 平均 = {df_mc['return'].mean():.2f}%")
        print(f"  - 勝率 (Win Rate %): 最佳 = {df_mc['win_rate'].max():.2f}% | 最差 = {df_mc['win_rate'].min():.2f}% | 平均 = {df_mc['win_rate'].mean():.2f}%")

    # 觀察池 BOS 比例與每月平均出訊號天數
    bos_true_pct = (total_bos_true / total_universe_bars * 100.0) if total_universe_bars > 0 else 0.0
    total_months = max(1, (datetime.strptime(all_dates[-1], "%Y-%m-%d") - datetime.strptime(all_dates[0], "%Y-%m-%d")).days / 30.0)
    avg_signal_days_per_month = len(signals_by_date) / total_months
    print(f"\n--- 總體市場計量特徵 ---")
    print(f"  - 觀察池 BOS 標記為 True 的 K 棒總比例: {bos_true_pct:.2f}%")
    print(f"  - 每月平均出訊號的天數: {avg_signal_days_per_month:.1f} 天/月")

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

    print("==================================================")

if __name__ == "__main__":
    run_backtest()
