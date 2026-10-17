"""
run_task_k.py
嚴格對齊 Claude 規格之任務 K (20日高點突破) 5年歷史回測
- 台股法定檔位撮合 (Tick Size)
- 零投信濾網、零自創均線或量能門檻
- 次日未過高不進場、跳空開高以開盤價進場
- 進場日反轉停損、跳空跌破停損滑價、收盤破20EMA次日開盤出清、滿120日上限
"""

import os
import re
import time
import pandas as pd
import numpy as np
import config
from data_fetcher import fetch_history


def get_tw_tick(price: float) -> float:
    """計算台股法定升降單位 (Tick Size)"""
    if price < 10.0:
        return 0.01
    elif price < 50.0:
        return 0.05
    elif price < 100.0:
        return 0.1
    elif price < 500.0:
        return 0.5
    elif price < 1000.0:
        return 1.0
    else:
        return 5.0


def get_tick_down(price: float) -> float:
    """計算向下退 1 檔之價格"""
    tick = get_tw_tick(price)
    # 若恰好位於門檻邊界 (例如 100.0)，向下退 1 檔為 99.9 (依低區間級距 0.1)
    if price in [10.0, 50.0, 100.0, 500.0, 1000.0]:
        tick = get_tw_tick(price - 0.001)
    return round(price - tick, 2)


def get_tick_up(price: float) -> float:
    """計算向上進 1 檔之價格"""
    tick = get_tw_tick(price)
    return round(price + tick, 2)


def get_universe_tickers() -> list:
    """取得 150 檔觀察池"""
    for fn_name in ["load_universe", "get_universe", "get_stock_list"]:
        fn = getattr(config, fn_name, None)
        if callable(fn):
            try:
                res = fn()
                if isinstance(res, dict): return list(res.keys())
                if isinstance(res, (list, tuple)): return [str(x) for x in res]
            except Exception:
                pass
    return []


def run_backtest_task_k(stock_map: dict, use_breadth_50: bool, use_fixed_risk_1pct: bool):
    """
    執行符合規格的任務 K 回測
    手續費雙向 0.1425% (打折計 0.001425*2) + 證交稅 0.3% = 0.585%
    """
    cost_rate = 0.00585
    candidates = []

    # 計算市場廣度
    records = []
    for tkr, df in stock_map.items():
        sub = df[["Date", "Close", "EMA_20"]].copy()
        sub["Above"] = sub["Close"] >= sub["EMA_20"]
        records.append(sub[["Date", "Above"]])
    all_b = pd.concat(records, ignore_index=True)
    breadth_map = all_b.groupby("Date")["Above"].mean().to_dict()

    for ticker, df in stock_map.items():
        df_len = len(df)
        for i in range(21, df_len - 1):
            sig_row = df.iloc[i]
            sig_date = sig_row["Date"]
            if sig_date < pd.Timestamp("2022-01-01"):
                continue

            # 1. 訊號判斷：當日最高突破前 20 日最高價 (不含當日) 且 收盤站上 20EMA
            prev_20_high = df["High"].iloc[i-20:i].max()
            if not (sig_row["High"] > prev_20_high and sig_row["Close"] >= sig_row["EMA_20"]):
                continue

            if use_breadth_50 and breadth_map.get(sig_date, 0.5) < 0.50:
                continue

            # 2. 進場掛單 (次日最高價必須觸及 訊號棒最高 + 1 Tick)
            trigger_price = get_tick_up(float(sig_row["High"]))
            initial_stop = get_tick_down(float(sig_row["Low"]))

            next_bar = df.iloc[i + 1]
            next_open = float(next_bar["Open"])
            next_high = float(next_bar["High"])
            next_low = float(next_bar["Low"])

            # 隔天未觸及觸發價 -> 不進場
            if next_high < trigger_price:
                continue

            # 突破進場：若開盤跳空開高以開盤價進場，否則以觸發價進場
            entry_price = max(trigger_price, next_open)
            risk_per_share = entry_price - initial_stop
            if risk_per_share <= 0:
                continue

            entry_date = next_bar["Date"]
            exit_date = entry_date
            exit_price = entry_price
            exit_reason = ""
            days_held = 0

            # 判斷進場當日是否觸發反轉停損
            if next_low <= initial_stop:
                exit_date = entry_date
                # 若跳空開低破停損以開盤價計，否則以停損價成交
                exit_price = min(next_open, initial_stop)
                exit_reason = "SAME_DAY_STOP"
            else:
                # 進入持有階段監控
                pending_ema_exit = False
                for k in range(i + 2, df_len):
                    cur_bar = df.iloc[k]
                    days_held += 1
                    cur_open = float(cur_bar["Open"])
                    cur_close = float(cur_bar["Close"])
                    cur_low = float(cur_bar["Low"])
                    cur_ema = float(cur_bar["EMA_20"])

                    # 1. 跌破 20EMA 之次日開盤市價出清
                    if pending_ema_exit:
                        exit_date = cur_bar["Date"]
                        exit_price = cur_open
                        exit_reason = "EXIT_EMA20"
                        break

                    # 2. 觸及初始停損 (含跳空開低)
                    if cur_low <= initial_stop:
                        exit_date = cur_bar["Date"]
                        exit_price = min(cur_open, initial_stop)
                        exit_reason = "INITIAL_STOP"
                        break

                    # 3. 達 120 交易日上限
                    if days_held >= 120 or k == df_len - 1:
                        exit_date = cur_bar["Date"]
                        exit_price = cur_close
                        exit_reason = "MAX_120D"
                        break

                    # 當日收盤若跌破 20EMA，標記次日開盤出場
                    if cur_close < cur_ema:
                        pending_ema_exit = True

            r_mult = ((exit_price * (1 - cost_rate)) - entry_price) / risk_per_share
            pct_ret = ((exit_price * (1 - cost_rate)) - entry_price) / entry_price

            candidates.append({
                "ticker": ticker,
                "sig_date": sig_date,
                "entry_date": entry_date,
                "exit_date": exit_date,
                "entry_price": entry_price,
                "stop_price": initial_stop,
                "exit_price": exit_price,
                "exit_reason": exit_reason,
                "risk_per_share": risk_per_share,
                "r_mult": r_mult,
                "pct_ret": pct_ret,
                "year": entry_date.year
            })

    candidates.sort(key=lambda x: x["entry_date"])

    # 資金池模擬
    equity = 1_000_000.0
    peak = equity
    max_dd = 0.0
    active = []
    executed = []
    max_pos = 5 if use_fixed_risk_1pct else 3

    for c in candidates:
        still = []
        for a in active:
            if a["exit_date"] <= c["entry_date"]:
                equity += a["pnl"]
                if equity > peak: peak = equity
                dd = (peak - equity) / peak
                if dd > max_dd: max_dd = dd
            else:
                still.append(a)
        active = still

        if len(active) >= max_pos:
            continue
        if any(a["ticker"] == c["ticker"] for a in active):
            continue

        if use_fixed_risk_1pct:
            shares = int((equity * 0.01) / c["risk_per_share"])
        else:
            shares = int((equity / 3.0) / c["entry_price"])

        if shares <= 0:
            continue

        rec = dict(c)
        rec["shares"] = shares
        rec["pnl"] = shares * c["entry_price"] * c["pct_ret"]
        active.append(rec)
        executed.append(rec)

    for a in active:
        equity += a["pnl"]
        if equity > peak: peak = equity
        dd = (peak - equity) / peak
        if dd > max_dd: max_dd = dd

    return pd.DataFrame(executed), equity, max_dd * 100


def print_report(title: str, df: pd.DataFrame, final_eq: float, mdd: float):
    print("\n" + "=" * 70)
    print(f"【{title}】")
    print("=" * 70)
    if df.empty:
        print("無成交紀錄")
        return

    wins = df[df["pnl"] > 0]
    losses = df[df["pnl"] <= 0]
    win_rate = (len(wins) / len(df)) * 100
    pf = (wins["pnl"].sum() / abs(losses["pnl"].sum())) if len(losses) > 0 and losses["pnl"].sum() != 0 else 99.9

    reasons = df["exit_reason"].value_counts().to_dict()

    print(f"總成交筆數   : {len(df)} 筆")
    print(f"整體勝率     : {win_rate:.1f}%  | 平均期望值: {df['r_mult'].mean():+.2f} R  | 獲利因子(PF): {pf:.2f}")
    print(f"期末資產淨值 : NT$ {int(final_eq):,} (總報酬: {((final_eq - 1_000_000)/10_000):+.1f}%)")
    print(f"最大回撤(MDD): -{mdd:.1f}%")
    print(f"出場原因分佈 : 破20EMA({reasons.get('EXIT_EMA20', 0)}), 初始停損({reasons.get('INITIAL_STOP', 0)}), 進場日反轉({reasons.get('SAME_DAY_STOP', 0)}), 滿120日({reasons.get('MAX_120D', 0)})")
    print("-" * 70)
    print("年份   | 成交筆數 | 勝率    | 平均 R    | 年度損益 (NT$)")
    print("-" * 70)
    for yr in [2022, 2023, 2024, 2025, 2026]:
        sub = df[df["year"] == yr]
        if sub.empty:
            print(f"{yr}   |   0 筆   |  0.0%   |  +0.00 R  | NT$ 0")
        else:
            w = (len(sub[sub["pnl"] > 0]) / len(sub)) * 100
            r = sub["r_mult"].mean()
            pnl = int(sub["pnl"].sum())
            print(f"{yr}   | {len(sub):3d} 筆   | {w:5.1f}%  | {r:+6.2f} R  | NT$ {pnl:+,}")


def main():
    tickers = get_universe_tickers()
    print(f"載入觀察池 {len(tickers)} 檔，開始下載日 K 線計算標準任務 K...")

    stock_map = {}
    for idx, t in enumerate(tickers, 1):
        df = fetch_history(t, lookback_days=1800)
        if not df.empty and len(df) >= 120:
            df = df.copy().sort_values("Date").reset_index(drop=True)
            df["EMA_20"] = df["Close"].ewm(span=20, adjust=False).mean()
            stock_map[t] = df
        time.sleep(0.2)

    print(f"資料準備完畢 (有效標的: {len(stock_map)} 檔)，開始模擬 3 組對照...")

    # G0 / 原版任務 K：無廣度、固定 1/3 資金 (MaxPos=3)
    df_g0, eq_g0, mdd_g0 = run_backtest_task_k(stock_map, use_breadth_50=False, use_fixed_risk_1pct=False)
    # G1 / 任務 K + 1% 以損定量 (無廣度)
    df_g1, eq_g1, mdd_g1 = run_backtest_task_k(stock_map, use_breadth_50=False, use_fixed_risk_1pct=True)
    # G2 / 任務 K + 50% 廣度 + 1% 以損定量
    df_g2, eq_g2, mdd_g2 = run_backtest_task_k(stock_map, use_breadth_50=True, use_fixed_risk_1pct=True)

    print_report("G0：任務 K 原版基準 (無廣度 / 固定 1/3 資金)", df_g0, eq_g0, mdd_g0)
    print_report("G1：任務 K + 1% 以損定量 (無廣度)", df_g1, eq_g1, mdd_g1)
    print_report("G2：任務 K + 50% 廣度濾網 + 1% 以損定量", df_g2, eq_g2, mdd_g2)


if __name__ == "__main__":
    main()
