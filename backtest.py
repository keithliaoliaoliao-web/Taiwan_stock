"""
backtest.py
獨立台股價格行為回測引擎 (Al Brooks H2 Strategy Freeze v1)
嚴格模擬次日進場、滑價、極端停損停利防禦、手續費與證交稅、資金管理約束（最大 3 檔持倉）與績效指標輸出。
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import config
from data_fetcher import fetch_history
from price_action_engine import PriceActionEngine

def run_backtest():
    print("==================================================")
    print("【台股價格行為策略獨立回測引擎啟動 (Backtest v1)】")
    print("==================================================")

    universe = config.DEFAULT_WATCHLIST
    print(f"載入觀察池共 {len(universe)} 檔標的進行 3 年歷史回測...")

    all_signals = []

    # 1. 收集所有標的的歷史訊號
    for ticker in universe:
        df = fetch_history(ticker, lookback_days=750)
        if df.empty or len(df) < 120:
            continue
        try:
            analyzed_df = PriceActionEngine.analyze_setups(df)
        except Exception:
            continue

        if analyzed_df.empty:
            continue

        # 掃描歷史訊號
        for i in range(1, len(analyzed_df) - 1):
            row = analyzed_df.iloc[i]
            if bool(row.get("Signal_H2", False)):
                grade = str(row.get("Signal_Grade", "B"))
                trigger_p = float(row.get("Trigger_Price", row["Close"]))
                stop_p = float(row.get("Stop_Loss", row["Close"] * 0.95))
                target_p = float(row.get("Target_Price", row["Close"] * 1.10))
                net_rr = float(row.get("Net_RR", 2.0))
                sig_date = str(row["Date"])

                all_signals.append({
                    "ticker": ticker,
                    "date": sig_date,
                    "bar_idx": i,
                    "df": analyzed_df,
                    "grade": grade,
                    "trigger_price": trigger_p,
                    "stop_loss": stop_p,
                    "target_price": target_p,
                    "net_rr": net_rr
                })

    print(f"共擷取到歷史 H2 原始訊號數: {len(all_signals)} 筆")

    # 按日期排序訊號
    all_signals.sort(key=lambda x: x["date"])

    # 2. 模擬真實交易與資金管理（最大同時持有 3 檔）
    active_positions = []
    closed_trades = []
    max_concurrent = 3
    buy_fee_rate = 0.001425 * 0.6
    sell_fee_rate = 0.001425 * 0.6 + 0.003
    max_holding_days = getattr(config, "MAX_HOLDING_DAYS", 15)

    # 依日期分組訊號
    signals_by_date = {}
    for sig in all_signals:
        dt = sig["date"]
        if dt not in signals_by_date:
            signals_by_date[dt] = []
        signals_by_date[dt].append(sig)

    # 按日期推進回測迴圈
    all_dates = sorted(signals_by_date.keys())
    if not all_dates:
        print("警告：未產生任何有效回測訊號。")
        return

    start_date = datetime.strptime(all_dates[0], "%Y-%m-%d")
    end_date = datetime.strptime(all_dates[-1], "%Y-%m-%d") + timedelta(days=30)

    # 我們以全市場所有標的的聯集日期來跑日線推進
    # 簡化起見，合併所有 df 的 Date
    master_dates = set()
    for sig in all_signals:
        df_sub = sig["df"]
        for d in df_sub["Date"]:
            master_dates.add(d)
    sorted_trading_days = sorted(list(master_dates))

    portfolio_equity = [1000000.0] # 初始資金 100 萬
    equity_curve = [1000000.0]

    for day_idx, current_date in enumerate(sorted_trading_days):
        # A. 檢查現有持倉是否出場
        remaining_positions = []
        for pos in active_positions:
            ticker = pos["ticker"]
            df_sub = pos["df"]
            entry_idx = pos["entry_idx"]
            current_bar_idx = pos["current_bar_idx"] + 1

            if current_bar_idx >= len(df_sub):
                # 資料結束強制平倉
                last_bar = df_sub.iloc[-1]
                exit_price = float(last_bar["Close"])
                exit_reason = "DATA_END"
                pnl = (exit_price * (1 - sell_fee_rate)) - (pos["entry_price"] * (1 + buy_fee_rate))
                closed_trades.append({**pos, "exit_price": exit_price, "exit_date": last_bar["Date"], "pnl": pnl, "exit_reason": exit_reason})
                continue

            bar = df_sub.iloc[current_bar_idx]
            bar_date = str(bar["Date"])
            o = float(bar["Open"])
            h = float(bar["High"])
            l = float(bar["Low"])
            c = float(bar["Close"])

            stop_p = pos["stop_loss"]
            target_p = pos["target_price"]
            holding_days = current_bar_idx - entry_idx

            exit_price = None
            exit_reason = None

            # 極端防禦性出場檢驗：同一日若同時觸及停損與停利，一律判定停損 (最悲觀原則)
            hit_stop = (l <= stop_p)
            hit_target = (h >= target_p)

            if hit_stop and hit_target:
                exit_price = stop_p if o > stop_p else o # 若開盤即跳空跌破則以開盤價停損
                exit_reason = "STOP_LOSS_CONFLICT"
            elif hit_stop:
                exit_price = stop_p if o > stop_p else o
                exit_reason = "STOP_LOSS"
            elif hit_target:
                exit_price = target_p if o < target_p else o
                exit_reason = "TAKE_PROFIT"
            elif holding_days >= max_holding_days:
                exit_price = o # 時間到以次日開盤價出場
                exit_reason = "TIME_EXIT"

            if exit_price is not None:
                # 計算淨損益
                entry_cost = pos["entry_price"] * (1 + buy_fee_rate)
                exit_revenue = exit_price * (1 - sell_fee_rate)
                pnl_pct = (exit_revenue - entry_cost) / entry_cost
                closed_trades.append({
                    **pos,
                    "exit_price": exit_price,
                    "exit_date": bar_date,
                    "exit_reason": exit_reason,
                    "pnl_pct": pnl_pct
                })
            else:
                pos["current_bar_idx"] = current_bar_idx
                remaining_positions.append(pos)

        active_positions = remaining_positions

        # B. 處理當日新訊號進場（次日成交）
        if current_date in signals_by_date and len(active_positions) < max_concurrent:
            day_sigs = signals_by_date[current_date]
            # 排序：A 級優先、同級比 Net_RR
            day_sigs.sort(key=lambda x: (0 if x["grade"] == "A" else 1, -x["net_rr"]))

            for sig in day_sigs:
                if len(active_positions) >= max_concurrent:
                    break
                
                ticker = sig["ticker"]
                df_sub = sig["df"]
                sig_idx = sig["bar_idx"]
                
                # 確保次日存在
                if sig_idx + 1 >= len(df_sub):
                    continue

                next_bar = df_sub.iloc[sig_idx + 1]
                next_o = float(next_bar["Open"])
                next_h = float(next_bar["High"])
                next_l = float(next_bar["Low"])
                trigger_p = sig["trigger_price"]

                # 僅當次日最高價 >= 觸發價時才成交
                if next_h >= trigger_p:
                    # 滑價處理：若開盤即跳空高於觸發價，以開盤價成交
                    entry_price = next_o if next_o >= trigger_p else trigger_p
                    active_positions.append({
                        "ticker": ticker,
                        "grade": sig["grade"],
                        "entry_date": str(next_bar["Date"]),
                        "entry_price": entry_price,
                        "stop_loss": sig["stop_loss"],
                        "target_price": sig["target_price"],
                        "df": df_sub,
                        "entry_idx": sig_idx + 1,
                        "current_bar_idx": sig_idx + 1
                    })

    # 3. 統計與指標輸出
    print("\n==================================================")
    print("【回測績效表現報告 (Backtest Performance Report)】")
    print("==================================================")

    total_trades = len(closed_trades)
    if total_trades == 0:
        print("無已平倉交易紀錄。")
        return

    df_trades = pd.DataFrame(closed_trades)
    df_trades["win"] = df_trades["pnl_pct"] > 0

    def print_metrics(subset_df, title):
        if subset_df.empty:
            print(f"\n--- {title} --- (無交易)")
            return
        t_count = len(subset_df)
        wins = subset_df["win"].sum()
        win_rate = (wins / t_count) * 100.0
        
        gross_profit = subset_df[subset_df["pnl_pct"] > 0]["pnl_pct"].sum()
        gross_loss = abs(subset_df[subset_df["pnl_pct"] < 0]["pnl_pct"].sum())
        profit_loss_ratio = (gross_profit / wins) / (gross_loss / (t_count - wins)) if (t_count - wins) > 0 and gross_loss > 0 else 0.0
        
        total_return = subset_df["pnl_pct"].sum() * 100.0
        
        # 最大連續虧損
        subset_df["consec_loss"] = (~subset_df["win"]).astype(int)
        # Calculate max consecutive losses
        max_consec = (subset_df["consec_loss"] * (subset_df["consec_loss"].groupby((~subset_df["win"]).cumsum()).cumcount() + 1)).max()

        print(f"\n--- {title} ---")
        print(f"  - 總交易次數: {t_count}")
        print(f"  - 勝率 (Win Rate): {win_rate:.2f}%")
        print(f"  - 平均盈虧比 (Avg P/L Ratio): {profit_loss_ratio:.2f}")
        print(f"  - 最大連續虧損次數: {int(max_consec)}")
        print(f"  - 總報酬率 (Total Return): {total_return:.2f}%")

    print_metrics(df_trades, "全體訊號總體表現 (Overall)")
    print_metrics(df_trades[df_trades["grade"] == "A"], "A 級訊號獨立表現 (Grade A)")
    print_metrics(df_trades[df_trades["grade"] == "B"], "B 級訊號獨立表現 (Grade B)")
    print("==================================================")

if __name__ == "__main__":
    run_backtest()
