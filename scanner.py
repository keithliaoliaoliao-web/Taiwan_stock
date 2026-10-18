"""
scanner.py
任務 K - C 組 (突破 20 日高) 前瞻紙上交易掃描器
版面標註：【觀察用，未經實證驗證】
"""

import argparse
import os
import sys
import numpy as np
import pandas as pd

try:
  import config

  HAS_CONFIG = True
except Exception:
  HAS_CONFIG = False

try:
  from data_fetcher import fetch_history

  HAS_FETCHER = True
except Exception:
  HAS_FETCHER = False

LEDGER_FILE = "paper_trading_ledger.csv"
COST_RATE = 0.00585
ACTUAL_FEE_DESC = "稅0.3% + 手續費0.1425%*2 (回測基準，無折扣無低消)"


def get_tw_tick(price: float) -> float:
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
  tick = get_tw_tick(price)
  if price in [10.0, 50.0, 100.0, 500.0, 1000.0]:
    tick = get_tw_tick(price - 0.001)
  return round(price - tick, 2)


def get_tick_up(price: float) -> float:
  tick = get_tw_tick(price)
  return round(price + tick, 2)


def adjust_corporate_actions(df: pd.DataFrame) -> pd.DataFrame:
  """第一步：股票分割回溯平滑"""
  df = df.copy().sort_values("Date").reset_index(drop=True)
  n = len(df)
  adj_factor = np.ones(n)

  for i in range(1, n):
    prev_c = df.loc[i - 1, "Close"]
    cur_o = df.loc[i, "Open"]
    if prev_c > 0 and cur_o > 0 and (cur_o / prev_c) < 0.70:
      ratio = cur_o / prev_c
      adj_factor[:i] *= ratio

  for col in ["Open", "High", "Low", "Close"]:
    if col in df.columns:
      df[col] = (df[col] * adj_factor).round(2)

  return df


def clean_stock_data(df: pd.DataFrame) -> pd.DataFrame:
  """第二步：清洗異常棒 (容錯保護：無 Volume 欄位不誤殺)"""
  df = df.copy().sort_values("Date").reset_index(drop=True)
  cleaned_rows = []

  for idx, row in df.iterrows():
    o = float(row.get("Open", 0))
    h = float(row.get("High", 0))
    l = float(row.get("Low", 0))
    c = float(row.get("Close", 0))

    has_vol = "Volume" in row and pd.notna(row["Volume"])
    v = float(row["Volume"]) if has_vol else 1.0

    if (o <= 0 and c <= 0) or (has_vol and v <= 0):
      continue

    if o <= 0 and c > 0:
      if cleaned_rows:
        row["Open"] = float(cleaned_rows[-1]["Close"])
      else:
        row["Open"] = c

    cleaned_rows.append(row)

  return pd.DataFrame(cleaned_rows).reset_index(drop=True)


def prepare_stock_data(raw_df: pd.DataFrame) -> pd.DataFrame:
  """資料前置標準層：先還原、後清洗、計算 EMA20"""
  if raw_df.empty or len(raw_df) < 22:
    return pd.DataFrame()
  df = adjust_corporate_actions(raw_df)
  df = clean_stock_data(df)
  if len(df) < 22:
    return pd.DataFrame()
  df["DateStr"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")
  df["EMA_20"] = df["Close"].ewm(span=20, adjust=False).mean()
  return df


def get_universe() -> list:
  if HAS_CONFIG:
    for fn in ["load_universe", "get_universe", "get_stock_list"]:
      f = getattr(config, fn, None)
      if callable(f):
        try:
          res = f()
          if isinstance(res, dict):
            return sorted(list(res.keys()))
          if isinstance(res, (list, tuple)):
            return sorted([str(x) for x in res])
        except Exception:
          pass
    tickers = getattr(config, "TARGET_STOCKS", getattr(config, "STOCKS", None))
    if isinstance(tickers, (list, tuple)):
      return sorted([str(x) for x in tickers])

  if os.path.exists("task_j_raw_h2_candidates.csv"):
    df_j = pd.read_csv("task_j_raw_h2_candidates.csv")
    return sorted(df_j["ticker"].unique().tolist())
  return []


def scan_signals_for_ticker(
    df: pd.DataFrame, ticker: str, as_of_date: str = None
) -> dict:
  if df.empty or len(df) < 22:
    return None

  if as_of_date is not None:
    matches = df.index[df["DateStr"] <= as_of_date]
    if len(matches) < 22:
      return None
    cur_idx = matches[-1]
  else:
    cur_idx = len(df) - 1

  if cur_idx < 20:
    return None

  cur_bar = df.iloc[cur_idx]
  sig_date = cur_bar["DateStr"]

  c_above_ema = bool(cur_bar["Close"] >= cur_bar["EMA_20"])
  prev_20_high = float(df["High"].iloc[cur_idx - 20 : cur_idx].max())
  c_break_20h = bool(cur_bar["High"] > prev_20_high)

  if not (c_above_ema and c_break_20h):
    return None

  high = float(cur_bar["High"])
  low = float(cur_bar["Low"])
  close = float(cur_bar["Close"])
  trigger_price = get_tick_up(high)
  stop_price = get_tick_down(low)
  risk_pct = round(((trigger_price - stop_price) / trigger_price) * 100, 2)

  return {
      "ticker": ticker,
      "signal_date": sig_date,
      "close": close,
      "high": high,
      "low": low,
      "prev_20_high": prev_20_high,
      "ema_20": round(float(cur_bar["EMA_20"]), 2),
      "trigger_price": trigger_price,
      "stop_price": stop_price,
      "risk_pct": risk_pct,
  }


def load_ledger() -> pd.DataFrame:
  cols = [
      "signal_date",
      "ticker",
      "trigger_price",
      "stop_price",
      "risk_pct",
      "triggered",
      "entry_price",
      "entry_date",
      "exit_date",
      "exit_price",
      "exit_reason",
      "rule_net_r",
      "slippage_net_r",
      "actual_fee_settings",
      "status",
      "days_held",
      "pending_ema_exit",
      "last_processed_date",
  ]
  if os.path.exists(LEDGER_FILE):
    return pd.read_csv(LEDGER_FILE)
  return pd.DataFrame(columns=cols)


def save_ledger(df: pd.DataFrame):
  df.to_csv(LEDGER_FILE, index=False, encoding="utf-8-sig")


def update_ledger_single_day(
    ledger: pd.DataFrame,
    stock_map: dict,
    today_str: str,
    target_ticker: str = None,
) -> tuple:
  """撮合單一交易日部位：

  1. 偵測分割事件：若單日開盤相對前日收盤跌幅超過 30%，標記為 NEEDS_REVIEW 並凍結自動撮合
  2. 正常撮合未分割之部位
  """
  if ledger.empty:
    return ledger, set()

  updated_rows = []
  tickers_exited_today = set()

  for _, row in ledger.iterrows():
    t = str(row["ticker"])
    if target_ticker is not None and t != target_ticker:
      updated_rows.append(row)
      continue

    status = str(row["status"])
    df = stock_map.get(t, pd.DataFrame())

    if df.empty or status in ["CLOSED", "UNTRIGGERED", "NEEDS_REVIEW"]:
      updated_rows.append(row)
      continue

    today_bar_matches = df[df["DateStr"] == today_str]
    if today_bar_matches.empty:
      updated_rows.append(row)
      continue

    today_idx = today_bar_matches.index[0]
    today_bar = today_bar_matches.iloc[0]
    cur_open = float(today_bar["Open"])
    cur_high = float(today_bar["High"])
    cur_low = float(today_bar["Low"])
    cur_close = float(today_bar["Close"])
    cur_ema = float(today_bar["EMA_20"])

    # 1. 偵測分割跳空事件 (相較前一根 K 棒收盤價折減超過 30%)
    if today_idx > 0:
      prev_bar = df.iloc[today_idx - 1]
      prev_c = float(prev_bar["Close"])
      if prev_c > 0 and cur_open > 0 and (cur_open / prev_c) < 0.70:
        s_ratio = round(cur_open / prev_c, 4)
        row["status"] = "NEEDS_REVIEW"
        row["exit_reason"] = f"SPLIT_DETECTED(ratio={s_ratio})"
        row["last_processed_date"] = today_str
        updated_rows.append(row)
        continue

    trigger_price = float(row["trigger_price"])
    stop_price = float(row["stop_price"])

    # 2. 處理 PENDING 掛單
    if status == "PENDING":
      if cur_high >= trigger_price:
        entry_price = max(trigger_price, cur_open)
        risk_per_share = entry_price - stop_price
        row["triggered"] = True
        row["entry_price"] = entry_price
        row["entry_date"] = today_str
        row["days_held"] = 0

        if cur_low <= stop_price:
          exit_price = min(cur_open, stop_price)
          row["exit_date"] = today_str
          row["exit_price"] = exit_price
          row["exit_reason"] = "SAME_DAY_STOP"
          row["status"] = "CLOSED"
          row["rule_net_r"] = round(
              ((exit_price * (1.0 - COST_RATE)) - entry_price) / risk_per_share,
              3,
          )
          slip_entry = get_tick_up(entry_price)
          slip_exit = get_tick_down(exit_price)
          row["slippage_net_r"] = round(
              ((slip_exit * (1.0 - COST_RATE)) - slip_entry) / risk_per_share, 3
          )
          tickers_exited_today.add(t)
        else:
          row["status"] = "OPEN"
          row["pending_ema_exit"] = False
      else:
        row["triggered"] = False
        row["status"] = "UNTRIGGERED"
        row["exit_reason"] = "UNTRIGGERED"

      row["last_processed_date"] = today_str
      updated_rows.append(row)
      continue

    # 3. 處理 OPEN 持倉部位
    if status == "OPEN":
      days_held = int(row["days_held"]) + 1
      row["days_held"] = days_held
      pending_ema = bool(row["pending_ema_exit"])
      entry_price = float(row["entry_price"])
      risk_per_share = entry_price - stop_price

      is_closed = False
      exit_price = 0.0
      exit_reason = ""

      if pending_ema:
        is_closed = True
        exit_price = cur_open
        exit_reason = "EXIT_EMA20"
      elif cur_low <= stop_price:
        is_closed = True
        exit_price = min(cur_open, stop_price)
        exit_reason = "INITIAL_STOP"
      elif days_held >= 120:
        is_closed = True
        exit_price = cur_close  # 原文規則：持有滿 120 交易日以當日收盤價出場
        exit_reason = "MAX_120D"

      if is_closed:
        row["status"] = "CLOSED"
        row["exit_date"] = today_str
        row["exit_price"] = exit_price
        row["exit_reason"] = exit_reason
        row["rule_net_r"] = round(
            ((exit_price * (1.0 - COST_RATE)) - entry_price) / risk_per_share, 3
        )
        slip_entry = get_tick_up(entry_price)
        slip_exit = get_tick_down(exit_price)
        row["slippage_net_r"] = round(
            ((slip_exit * (1.0 - COST_RATE)) - slip_entry) / risk_per_share, 3
        )
        tickers_exited_today.add(t)
      else:
        if cur_close < cur_ema:
          row["pending_ema_exit"] = True
        else:
          row["pending_ema_exit"] = False

      row["last_processed_date"] = today_str
      updated_rows.append(row)

  return pd.DataFrame(updated_rows), tickers_exited_today


def run_extended_verification(
    benchmark_csv: str = "task_k_trades_base_no_ov.csv",
) -> bool:
  print("====================================================================")
  print("【執行擴充自我檢驗：涵蓋 2023-H2, 2025-H1, 2026-H1 三區間全流程回放】")
  print("====================================================================")

  if not os.path.exists(benchmark_csv):
    print(f"【檢驗中止】找不到基準檔案: {benchmark_csv}")
    return False

  df_k = pd.read_csv(benchmark_csv)
  c_trades_all = df_k[df_k["group"] == "C_TaskK"].copy()
  if c_trades_all.empty:
    print("【檢驗中止】CSV 中無 C_TaskK 交易紀錄！")
    return False

  tickers = get_universe()
  if len(tickers) < 142:
    print(f"【檢驗中止】股票池載入數不足 95%: 實測 {len(tickers)} 檔")
    return False

  stock_map = {}
  if HAS_FETCHER:
    print(f"載入觀察池 {len(tickers)} 檔行情 (lookback_days=2200)...")
    for t in tickers:
      raw_df = fetch_history(t, lookback_days=2200)
      if not raw_df.empty:
        df_prep = prepare_stock_data(raw_df)
        if not df_prep.empty:
          stock_map[t] = df_prep

  all_trading_dates = sorted(
      list(
          set.union(
              *[
                  set(df["DateStr"])
                  for df in stock_map.values()
                  if not df.empty
              ]
          )
      )
  )

  eval_periods = [
      ("2023-H2", "2023-07-03", "2023-12-29"),
      ("2025-H1", "2025-01-02", "2025-06-30"),
      ("2026-H1", "2026-01-02", "2026-06-30"),
  ]

  total_overall_pass = True

  for period_name, p_start, p_end in eval_periods:
    print(f"\n" + "=" * 68)
    print(f"【開始評估區間: {period_name} ({p_start} ~ {p_end})】")
    print("=" * 68)

    sim_ledger = pd.DataFrame(columns=[
        "signal_date",
        "ticker",
        "trigger_price",
        "stop_price",
        "risk_pct",
        "triggered",
        "entry_price",
        "entry_date",
        "exit_date",
        "exit_price",
        "exit_reason",
        "rule_net_r",
        "slippage_net_r",
        "actual_fee_settings",
        "status",
        "days_held",
        "pending_ema_exit",
        "last_processed_date",
    ])

    extra_signals = []
    start_date = "2022-04-01"
    start_idx = (
        all_trading_dates.index(start_date)
        if start_date in all_trading_dates
        else 0
    )

    for day_idx in range(start_idx, len(all_trading_dates)):
      today_str = all_trading_dates[day_idx]
      if today_str > p_end and sim_ledger[sim_ledger["status"] == "OPEN"].empty:
        break

      sim_ledger, exited_today = update_ledger_single_day(
          sim_ledger, stock_map, today_str
      )
      active_tickers = set(
          sim_ledger[sim_ledger["status"].isin(["OPEN", "PENDING"])][
              "ticker"
          ].unique()
      )
      ineligible_tickers = active_tickers.union(exited_today)

      if day_idx < len(all_trading_dates) - 1:
        for t in tickers:
          df_t = stock_map.get(t, pd.DataFrame())
          if df_t.empty:
            continue

          sig = scan_signals_for_ticker(df_t, t, as_of_date=today_str)
          if sig:
            in_eval = p_start <= today_str <= p_end
            if t in ineligible_tickers:
              if in_eval:
                extra_signals.append({
                    "sig_date": today_str,
                    "ticker": t,
                    "category": "持倉中不重複進場",
                })
              continue

            sim_ledger = pd.concat([
                sim_ledger,
                pd.DataFrame([{
                    "signal_date": sig["signal_date"],
                    "ticker": sig["ticker"],
                    "trigger_price": sig["trigger_price"],
                    "stop_price": sig["stop_price"],
                    "risk_pct": sig["risk_pct"],
                    "triggered": False,
                    "entry_price": np.nan,
                    "entry_date": "",
                    "exit_date": "",
                    "exit_price": np.nan,
                    "exit_reason": "",
                    "rule_net_r": np.nan,
                    "slippage_net_r": np.nan,
                    "actual_fee_settings": ACTUAL_FEE_DESC,
                    "status": "PENDING",
                    "days_held": 0,
                    "pending_ema_exit": False,
                    "last_processed_date": today_str,
                }]),
            ],
                                   ignore_index=True)

    bench_sub = c_trades_all[
        (c_trades_all["sig_date"] >= p_start)
        & (c_trades_all["sig_date"] <= p_end)
    ].sort_values(["sig_date", "ticker"]).reset_index(drop=True)

    scanner_entered = sim_ledger[
        (sim_ledger["signal_date"] >= p_start)
        & (sim_ledger["signal_date"] <= p_end)
        & (sim_ledger["triggered"] == True)
    ].sort_values(["signal_date", "ticker"]).reset_index(drop=True)

    scanner_untriggered = sim_ledger[
        (sim_ledger["signal_date"] >= p_start)
        & (sim_ledger["signal_date"] <= p_end)
        & (sim_ledger["triggered"] == False)
    ]
    for _, r in scanner_untriggered.iterrows():
      extra_signals.append({
          "sig_date": r["signal_date"],
          "ticker": r["ticker"],
          "category": "次日未觸發",
      })

    print(f"基準應成交: {len(bench_sub)} 筆 | 掃描器成交: {len(scanner_entered)} 筆")
    diff_records = []
    period_pass = True

    for _, b_row in bench_sub.iterrows():
      s_d = b_row["sig_date"]
      tk = b_row["ticker"]

      match = scanner_entered[
          (scanner_entered["signal_date"] == s_d)
          & (scanner_entered["ticker"] == tk)
      ]
      if match.empty:
        print(f"  [FAIL] 缺少成交: {s_d} {tk}")
        period_pass = False
        continue

      m = match.iloc[0]
      entry_ok = (
          abs(float(m["entry_price"]) - float(b_row["entry_price"])) <= 0.001
      )
      stop_ok = (
          abs(float(m["stop_price"]) - float(b_row["stop_price"])) <= 0.001
      )
      exit_d_ok = str(m["exit_date"]) == str(b_row["exit_date"])
      exit_p_ok = (
          abs(float(m["exit_price"]) - float(b_row["exit_price"])) <= 0.001
      )
      reason_ok = str(m["exit_reason"]) == str(b_row["exit_reason"])
      r_ok = abs(float(m["rule_net_r"]) - float(b_row["net_r"])) <= 0.005

      is_p = (
          entry_ok
          and stop_ok
          and exit_d_ok
          and exit_p_ok
          and reason_ok
          and r_ok
      )
      if not is_p:
        period_pass = False

      diff_records.append({
          "period": period_name,
          "sig_date": s_d,
          "ticker": tk,
          "scanner_entry": m["entry_price"],
          "csv_entry": b_row["entry_price"],
          "scanner_stop": m["stop_price"],
          "csv_stop": b_row["stop_price"],
          "scanner_exit_date": m["exit_date"],
          "csv_exit_date": b_row["exit_date"],
          "scanner_exit_price": m["exit_price"],
          "csv_exit_price": b_row["exit_price"],
          "scanner_reason": m["exit_reason"],
          "csv_reason": b_row["exit_reason"],
          "scanner_net_r": m["rule_net_r"],
          "csv_net_r": b_row["net_r"],
          "match_status": "PASS" if is_p else "FAIL",
      })

    prefix = period_name.lower().replace("-", "_")
    pd.DataFrame(diff_records).to_csv(
        f"replay_diff_{prefix}.csv", index=False, encoding="utf-8-sig"
    )
    pd.DataFrame(extra_signals).to_csv(
        f"replay_extra_{prefix}.csv", index=False, encoding="utf-8-sig"
    )

    if period_pass and len(scanner_entered) == len(bench_sub):
      print(f"【{period_name} 評估結果：100% PASS】")
    else:
      print(f"【{period_name} 評估結果：FAIL】")
      total_overall_pass = False

  return total_overall_pass


def main():
  parser = argparse.ArgumentParser(
      description="Task K Group C Forward Paper Trading Scanner"
  )
  parser.add_argument(
      "--date",
      type=str,
      default=None,
      help="指定掃描日期 (YYYY-MM-DD)，預設為最新交易日",
  )
  parser.add_argument(
      "--extended-verify",
      action="store_true",
      help="執行三區間擴充全生命週期比對回放",
  )
  args = parser.parse_args()

  print("********************************************************************")
  print("【觀察用，未經實證驗證】")
  print("任務 K - C 組 (突破 20 日高) 前瞻紙上交易掃描器")
  print("********************************************************************")

  if args.extended_verify:
    success = run_extended_verification()
    sys.exit(0 if success else 1)

  tickers = get_universe()
  if not tickers:
    print("【致命錯誤】觀察池為空，程式終止！")
    sys.exit(1)

  stock_map = {}
  if HAS_FETCHER:
    for t in tickers:
      raw_df = fetch_history(t, lookback_days=2200)
      if not raw_df.empty:
        df_prep = prepare_stock_data(raw_df)
        if not df_prep.empty:
          stock_map[t] = df_prep

  valid_count = len(stock_map)
  valid_ratio = valid_count / len(tickers)
  print(
      f"載入觀察池: 成功 {valid_count}/{len(tickers)} 檔 ({round(valid_ratio*100, 1)}%)"
  )

  if valid_ratio < 0.95:
    print(
        f"【致命錯誤】有效載入率低於 95% (門檻 142 檔，實測 {valid_count} 檔)，終止執行！"
    )
    sys.exit(1)

  all_latest_dates = [
      df["DateStr"].iloc[-1] for df in stock_map.values() if not df.empty
  ]
  latest_market_date = max(set(all_latest_dates), key=all_latest_dates.count)
  today_str = args.date if args.date else latest_market_date
  print(f"確認執行交易日: {today_str}")

  ledger = load_ledger()

  last_processed = (
      str(ledger["last_processed_date"].dropna().max())
      if (
          not ledger.empty
          and "last_processed_date" in ledger.columns
          and not ledger["last_processed_date"].dropna().empty
      )
      else None
  )

  all_dates_union = sorted(
      list(set.union(*[set(df["DateStr"]) for df in stock_map.values()])))

  if last_processed:
    if today_str <= last_processed:
      print(
          f"【冪等防護】今日 ({today_str}) 已於先前處理完成 (last_processed:"
          f" {last_processed})，略過重複更新。"
      )
      sys.exit(0)

    prev_idx = (
        all_dates_union.index(last_processed)
        if last_processed in all_dates_union
        else -1
    )
    curr_idx = (
        all_dates_union.index(today_str) if today_str in all_dates_union else -1
    )
    if prev_idx != -1 and curr_idx != -1 and curr_idx > prev_idx + 1:
      missed_dates = all_dates_union[prev_idx + 1 : curr_idx]
      print(f"【漏跑偵測】偵測到未處理之交易日: {missed_dates}，開始循序補算...")
      for m_d in missed_dates:
        ledger, _ = update_ledger_single_day(ledger, stock_map, m_d)

  ledger, exited_today = update_ledger_single_day(ledger, stock_map, today_str)

  open_positions = (
      set(
          ledger[
              ledger["status"].isin(["OPEN", "PENDING", "NEEDS_REVIEW"])
          ]["ticker"].unique()
      )
      if not ledger.empty
      else set()
  )
  ineligible_tickers = open_positions.union(exited_today)

  signals = []
  for t in tickers:
    if t in ineligible_tickers:
      continue
    df = stock_map.get(t, pd.DataFrame())
    sig = scan_signals_for_ticker(df, t, as_of_date=today_str)
    if sig:
      signals.append(sig)

  sig_df = pd.DataFrame(signals)
  print(
      f"\n【{today_str} 當日新觸發訊號清單 (排除持倉與今日出場)】共 {len(sig_df)} 檔"
  )
  if not sig_df.empty:
    print(
        sig_df[[
            "ticker",
            "signal_date",
            "trigger_price",
            "stop_price",
            "risk_pct",
        ]].to_string(index=False)
    )

    existing_keys = (
        set(
            zip(
                ledger["signal_date"].astype(str), ledger["ticker"].astype(str)
            )
        )
        if not ledger.empty
        else set()
    )
    new_records = []
    for _, s in sig_df.iterrows():
      if (str(s["signal_date"]), str(s["ticker"])) in existing_keys:
        continue
      new_records.append({
          "signal_date": s["signal_date"],
          "ticker": s["ticker"],
          "trigger_price": s["trigger_price"],
          "stop_price": s["stop_price"],
          "risk_pct": s["risk_pct"],
          "triggered": False,
          "entry_price": np.nan,
          "entry_date": "",
          "exit_date": "",
          "exit_price": np.nan,
          "exit_reason": "",
          "rule_net_r": np.nan,
          "slippage_net_r": np.nan,
          "actual_fee_settings": ACTUAL_FEE_DESC,
          "status": "PENDING",
          "days_held": 0,
          "pending_ema_exit": False,
          "last_processed_date": today_str,
      })
    if new_records:
      ledger = pd.concat([ledger, pd.DataFrame(new_records)], ignore_index=True)
  else:
    print("今日無符合 C 組條件之新訊號。")

  save_ledger(ledger)
  print(f"\n已同步寫入更新紙上交易帳本: {LEDGER_FILE}")


if __name__ == "__main__":
  main()
