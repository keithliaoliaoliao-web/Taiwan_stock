"""
verify_model.py
2022-2026 跨年度風控與策略對照驗證腳本
一次抓取 150 檔 5 年日 K 線 (僅消耗 150 次 API 請求)，於記憶體內對比：
1. 現行 H2 vs 任務 K (20日高點突破)
2. 固定 1/3 資金 vs 50% 市場廣度濾網 + 1% 以損定量風控
"""

import os
import re
import time
import pandas as pd
import numpy as np
import config
from data_fetcher import fetch_history

# 嘗試載入現有價格行為引擎
try:
    from price_action_engine import PriceActionEngine
    HAS_PA_ENGINE = True
except Exception:
    HAS_PA_ENGINE = False


def get_universe_tickers() -> list:
    """自動從 config.py 或環境中安全提取 150 檔觀察池代碼"""
    for fn_name in ["load_universe", "get_universe", "get_stock_list", "get_tickers"]:
        fn = getattr(config, fn_name, None)
        if callable(fn):
            try:
                res = fn()
                if isinstance(res, dict) and len(res) >= 30:
                    return list(res.keys())
                if isinstance(res, (list, tuple, set)) and len(res) >= 30:
                    return [str(x) for x in res]
            except Exception:
                pass

    for attr in dir(config):
        if attr.startswith("__"):
            continue
        val = getattr(config, attr, None)
        if isinstance(val, dict) and len(val) >= 30:
            k = str(next(iter(val.keys())))
            if re.match(r"^\d{4}(\.TW|\.TWO)?$", k):
                return list(val.keys())
        elif isinstance(val, (list, tuple, set)) and len(val) >= 30:
            v = next(iter(val))
            if isinstance(v, str) and re.match(r"^\d{4}(\.TW|\.TWO)?$", v):
                return list(val)

    # Fallback: 直接從檔案掃描四碼台股代碼
    found = []
    for fname in ["config.py", "scanner.py"]:
        if os.path.exists(fname):
            with open(fname, "r", encoding="utf-8", errors="ignore") as f:
                matches = re.findall(r"\b(\d{4}(?:\.TWO|\.TW)?)\b", f.read())
                for m in matches:
                    code = int(m.split(".")[0])
                    if 1101 <= code <= 9999 and code not in range(2015, 2030):
                        if m not in found:
                            found.append(m)
    return found[:150]


def prepare_stock_df(df: pd.DataFrame) -> pd.DataFrame:
    """計算 20EMA、任務 K (突破20日高) 與 H2 訊號"""
    df = df.copy().sort_values("Date").reset_index(drop=True)
    df["EMA_20"] = df["Close"].ewm(span=20, adjust=False).mean()
    df["Above_EMA20"] = df["Close"] >= df["EMA_20"]

    # 任務 K: 收盤站上 20EMA + 收盤突破前 20 日最高價 + 20EMA 上彎
    df["Prev_20D_High"] = df["High"].shift(1).rolling(20).max()
    df["EMA_Slope_Up"] = df["EMA_20"] > df["EMA_20"].shift(1)
    df["Signal_TaskK"] = (
        df["Above_EMA20"]
        & df["EMA_Slope_Up"]
        & (df["Close"] > df["Prev_20D_High"])
    )
    # 任務 K 結構停損：近 5 日最低點與 20EMA 取較低者
    df["Stop_TaskK"] = np.minimum(df["Low"].rolling(5).min(), df["EMA_20"] * 0.98)

    # 現行 H2 訊號
    df["Signal_H2_Custom"] = False
    df["Stop_H2_Custom"] = df["Stop_TaskK"]

    if HAS_PA_ENGINE:
        try:
            pa_df = PriceActionEngine.analyze_setups(df.copy())
            if "Signal_H2" in pa_df.columns:
                df["Signal_H2_Custom"] = pa_df["Signal_H2"].fillna(False).astype(bool)
                if "Stop_Loss" in pa_df.columns:
                    df["Stop_H2_Custom"] = pa_df["Stop_Loss"].fillna(df["Stop_TaskK"])
                return df
        except Exception:
            pass

    # 若無 PA Engine 則使用標準 H2 替代
    pullback = (df["High"].shift(1) < df["High"].shift(2)) & (df["High"].shift(2) < df["High"].shift(3))
    df["Signal_H2_Custom"] = df["Above_EMA20"] & pullback & (df["Close"] > df["High"].shift(1))
    return df


def simulate_portfolio(
    stock_map: dict,
    breadth_series: pd.Series,
    signal_col: str,
    stop_col: str,
    use_breadth_filter: bool,
    use_fixed_risk: bool,
    cost_rate: float = 0.00585
) -> dict:
    """
    嚴格依時間序列模擬 2022-01-01 ~ 2026-10-16 投資組合表現
    V1 出場規則：觸及初始停損、或收盤跌破 20EMA 隔日開盤出清、或滿 120 交易日
    """
    # 收集所有候選交易
    candidates = []
    for ticker, df in stock_map.items():
        sig_indices = df.index[df[signal_col] == True].tolist()
        for idx in sig_indices:
            if idx + 1 >= len(df):
                continue
            sig_row = df.iloc[idx]
            sig_date = sig_row["Date"]
            if sig_date < pd.Timestamp("2022-01-01"):
                continue

            # 市場廣度濾網檢查 (當日觀察池站上 20EMA 比例 >= 50%)
            b_val = breadth_series.get(sig_date, 0.5)
            if use_breadth_filter and b_val < 0.50:
                continue

            entry_row = df.iloc[idx + 1]
            entry_date = entry_row["Date"]
            entry_price = float(entry_row["Open"])
            stop_price = float(sig_row[stop_col])

            if entry_price <= 0 or stop_price <= 0 or entry_price <= stop_price:
                continue

            risk_per_share = entry_price - stop_price
            if (risk_per_share / entry_price) > 0.20 or (risk_per_share / entry_price) < 0.01:
                continue

            # 預先模擬 V1 出場點
            exit_date = entry_date
            exit_price = entry_price
            days_held = 0
            pending_ema_exit = False

            for k in range(idx + 1, len(df)):
                cur = df.iloc[k]
                days_held += 1
                if pending_ema_exit:
                    exit_date = cur["Date"]
                    exit_price = float(cur["Open"])
                    break
                if float(cur["Low"]) <= stop_price:
                    exit_date = cur["Date"]
                    exit_price = min(float(cur["Open"]), stop_price)
                    break
                if days_held >= 120 or k == len(df) - 1:
                    exit_date = cur["Date"]
                    exit_price = float(cur["Close"])
                    break
                if float(cur["Close"]) < float(cur["EMA_20"]):
                    pending_ema_exit = True

            r_mult = ((exit_price * (1 - cost_rate)) - entry_price) / risk_per_share
            pct_ret = ((exit_price * (1 - cost_rate)) - entry_price) / entry_price

            candidates.append({
                "ticker": ticker,
                "sig_date": sig_date,
                "entry_date": entry_date,
                "exit_date": exit_date,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "risk_per_share": risk_per_share,
                "r_mult": r_mult,
                "pct_ret": pct_ret,
                "year": entry_date.year
            })

    candidates.sort(key=lambda x: x["entry_date"])

    # 模擬資金池與同時持倉上限
    initial_capital = 1_000_000.0
    equity = initial_capital
    peak_equity = initial_capital
    max_dd = 0.0
    max_pos = 5 if use_fixed_risk else 3

    active_trades = []
    executed_trades = []

    for c in candidates:
        # 先結算已出場部位
        still_active = []
        for t in active_trades:
            if t["exit_date"] <= c["entry_date"]:
                equity += t["pnl"]
                if equity > peak_equity:
                    peak_equity = equity
                dd = (peak_equity - equity) / peak_equity
                if dd > max_dd:
                    max_dd = dd
            else:
                still_active.append(t)
        active_trades = still_active

        if len(active_trades) >= max_pos:
            continue
        if any(t["ticker"] == c["ticker"] for t in active_trades):
            continue

        # 部位規模計算
        if use_fixed_risk:
            # 單筆最大停損 = 總資金 1%，且單筆投入不超過總資金 25%
            risk_budget = equity * 0.01
            raw_shares = risk_budget / c["risk_per_share"]
            max_shares = (equity * 0.25) / c["entry_price"]
            shares = int(min(raw_shares, max_shares))
        else:
            # 固定 1/3 資金
            pos_budget = equity * (1.0 / 3.0)
            shares = int(pos_budget / c["entry_price"])

        if shares <= 0:
            continue

        pnl = shares * c["entry_price"] * c["pct_ret"]
        trade_rec = dict(c)
        trade_rec["shares"] = shares
        trade_rec["pnl"] = pnl
        active_trades.append(trade_rec)
        executed_trades.append(trade_rec)

    for t in active_trades:
        equity += t["pnl"]
        if equity > peak_equity:
            peak_equity = equity
        dd = (peak_equity - equity) / peak_equity
        if dd > max_dd:
            max_dd = dd

    df_exec = pd.DataFrame(executed_trades)
    return {
        "final_equity": equity,
        "total_return_pct": ((equity - initial_capital) / initial_capital) * 100,
        "max_dd_pct": max_dd * 100,
        "trades": df_exec
    }


def print_summary(title: str, res: dict):
    df_t = res["trades"]
    print("\n" + "=" * 68)
    print(f"【{title}】")
    print("=" * 68)
    if df_t.empty:
        print("無成交紀錄")
        return

    wins = df_t[df_t["pnl"] > 0]
    losses = df_t[df_t["pnl"] <= 0]
    win_rate = (len(wins) / len(df_t)) * 100
    pf = (wins["pnl"].sum() / abs(losses["pnl"].sum())) if len(losses) > 0 and losses["pnl"].sum() != 0 else 99.9
    avg_r = df_t["r_mult"].mean()

    print(f"總成交筆數   : {len(df_t)} 筆")
    print(f"整體勝率     : {win_rate:.1f}%  | 平均期望值: {avg_r:+.2f} R  | 獲利因子(PF): {pf:.2f}")
    print(f"5年總報酬率  : {res['total_return_pct']:+.1f}% (期末資產: NT$ {int(res['final_equity']):,})")
    print(f"最大回撤(MDD): -{res['max_dd_pct']:.1f}%")
    print("-" * 68)
    print("年份   | 成交筆數 | 勝率    | 平均 R    | 年度損益 (NT$)")
    print("-" * 68)
    for yr in [2022, 2023, 2024, 2025, 2026]:
        sub = df_t[df_t["year"] == yr]
        if sub.empty:
            print(f"{yr}   |   0 筆   |  0.0%   |  +0.00 R  | NT$ 0")
        else:
            w = (len(sub[sub["pnl"] > 0]) / len(sub)) * 100
            r = sub["r_mult"].mean()
            pnl = int(sub["pnl"].sum())
            print(f"{yr}   | {len(sub):3d} 筆   | {w:5.1f}%  | {r:+6.2f} R  | NT$ {pnl:+,}")


def main():
    tickers = get_universe_tickers()
    print(f"載入觀察池共 {len(tickers)} 檔，開始抓取 5 年日 K 線 (預計耗時 40 秒)...")

    stock_map = {}
    breadth_records = []

    for idx, t in enumerate(tickers, 1):
        df = fetch_history(t, lookback_days=1800)
        if not df.empty and len(df) >= 120:
            prep_df = prepare_stock_df(df)
            stock_map[t] = prep_df
            b_sub = prep_df[["Date", "Above_EMA20"]].copy()
            breadth_records.append(b_sub)
        time.sleep(0.22)

    print(f"成功載入 {len(stock_map)} 檔有效歷史資料，正在計算每日市場廣度...")
    all_b = pd.concat(breadth_records, ignore_index=True)
    breadth_series = all_b.groupby("Date")["Above_EMA20"].mean()

    # 執行 4 組對照實驗
    r1 = simulate_portfolio(stock_map, breadth_series, "Signal_H2_Custom", "Stop_H2_Custom", False, False)
    r2 = simulate_portfolio(stock_map, breadth_series, "Signal_H2_Custom", "Stop_H2_Custom", True, True)
    r3 = simulate_portfolio(stock_map, breadth_series, "Signal_TaskK", "Stop_TaskK", False, False)
    r4 = simulate_portfolio(stock_map, breadth_series, "Signal_TaskK", "Stop_TaskK", True, True)

    print_summary("組別 1：現行 H2 + 舊風控 (無廣度濾網 / 固定 1/3 資金)", r1)
    print_summary("組別 2：現行 H2 + 新風控 (50% 廣度濾網 + 1% 以損定量)", r2)
    print_summary("組別 3：任務 K (突破20日高) + 舊風控 (無廣度濾網 / 固定 1/3 資金)", r3)
    print_summary("組別 4：任務 K (突破20日高) + 新風控 (50% 廣度濾網 + 1% 以損定量)", r4)


if __name__ == "__main__":
    main()
