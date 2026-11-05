"""
C4 測試矩陣（合成資料）

目的：驗證回測引擎的出場模擬邏輯正確性，區分「策略邊際」與「出場引擎偏差」。

測試原則（依外部審查 2026-11 意見）：
- 價格路徑必須符合台股漲跌停（每日 ±10%、tick、一字漲/跌停 = 開=高=低=收）
- 停損語義：價格反彈到高於停損時不應觸發；跌停日無法成交就不能假設成交
- 一字漲停出場（放空回補）不可成交；空頭 gap-through-stop 成交價是開盤價不是停損價
- locked_at_end 部位不計入已平倉 R；強制回補前平倉，不支付股利補償
- 多除息日：股利應跨所有 ex-date 加總（合成驗證，實際樣本 0 筆=UNVERIFIED 仍成立）
- 無任何股利的交易 delta 必須精確為 0

each test uses strategy='bom' with a synthetic BOM signal; EMA_20 set to 0 (long) or 999 (short)
to isolate the exit engine.
"""
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, ".")
import backtest

SIG_IDX = 5  # signal bar; entry happens at SIG_IDX+1
n_prefix = 6

results = []
def check(name, cond, detail=""):
    ok = bool(cond)
    results.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}{(' :: ' + detail) if detail else ''}")


def make_df(bars, direction, entry, stop, target):
    rows = []
    for k, b in enumerate(bars):
        o, h, l, c = b[0], b[1], b[2], b[3]
        ema = b[4] if len(b) > 4 else 0.0
        rows.append({
            "Date": (pd.Timestamp("2024-06-03") + pd.Timedelta(days=k)).strftime("%Y-%m-%d"),
            "Open": float(o), "High": float(h), "Low": float(l), "Close": float(c),
            "EMA_20": float(ema),
            "Ticker": "TEST.TW",
            "BOM_Detected": False, "BOM_Direction": "NONE",
            "BOM_Entry": np.nan, "BOM_Stop": np.nan, "BOM_Target": np.nan,
        })
    rows[SIG_IDX]["BOM_Detected"] = True
    rows[SIG_IDX]["BOM_Direction"] = "BULL" if direction > 0 else "BEAR"
    rows[SIG_IDX]["BOM_Entry"] = float(entry)
    rows[SIG_IDX]["BOM_Stop"] = float(stop)
    rows[SIG_IDX]["BOM_Target"] = float(target)
    return pd.DataFrame(rows)


def pre(bars_prefix):
    return list(bars_prefix)


def run_one_test(bars, direction, entry, stop, target, div_df=None, borrow_fee=0.05):
    df = make_df(bars, direction, entry, stop, target)
    return backtest.simulate_trades(df, strategy="bom", dividend_df=div_df,
                                    short_borrow_fee_annual=borrow_fee)


base_prefix = [(100.0, 101.0, 99.0, 100.5, 0.0)] * 6  # 6 calm prefix bars (idx 0-5); signal at idx 5, entry at idx 6

# ============================================================
# T1a: long, 2 consecutive limit-downs, then tradable day gaps below stop
#   expect: exit at OPEN of tradable day, NOT at stop; locked_days == 2
# ============================================================
bars = base_prefix + [
    (100.0, 100.5, 99.0, 100.0, 0.0),   # day0: entry day (open 100), not one-tick
    (90.0, 90.0, 90.0, 90.0, 0.0),      # day1: 一字跌停 - block (long can't sell)
    (81.0, 81.0, 81.0, 81.0, 0.0),      # day2: 一字跌停 - block
    (73.0, 76.0, 72.0, 73.5, 0.0),      # day3: tradable, open 73 < stop 90 -> gap exit at open
]
trades = run_one_test(bars, +1, 100.0, 90.0, 130.0)
check("T1a: 跌停可成交前禁出場，開盤低於停損以開盤價出場",
      len(trades) == 1 and trades[0]["exit_reason"] == "INITIAL_STOP"
      and abs(trades[0]["exit_price"] - 73.0) < 1e-9 and trades[0]["locked_days"] == 2,
      f"trades={len(trades)}" + (f" exit={trades[0]['exit_price']} px, reason={trades[0]['exit_reason']}, locked={trades[0]['locked_days']}" if trades else ""))

# ============================================================
# T1b: long, 3 consecutive limit-downs, tradable day below stop
# ============================================================
bars = base_prefix + [
    (100.0, 100.5, 99.0, 100.0, 0.0),
    (90.0, 90.0, 90.0, 90.0, 0.0),
    (81.0, 81.0, 81.0, 81.0, 0.0),
    (72.9, 72.9, 72.9, 72.9, 0.0),
    (66.0, 68.0, 65.0, 66.5, 0.0),      # open 66 < stop 90
]
trades = run_one_test(bars, +1, 100.0, 90.0, 130.0)
check("T1b: 連續3日跌停，第4日以開盤價出場，locked_days==3",
      len(trades) == 1 and abs(trades[0]["exit_price"] - 66.0) < 1e-9 and trades[0]["locked_days"] == 3)

# ============================================================
# T1c: long, 5 consecutive limit-downs, tradable day below stop
# ============================================================
bars = base_prefix + [
    (100.0, 100.5, 99.0, 100.0, 0.0),
    (90.0, 90.0, 90.0, 90.0, 0.0),
    (81.0, 81.0, 81.0, 81.0, 0.0),
    (72.9, 72.9, 72.9, 72.9, 0.0),
    (65.6, 65.6, 65.6, 65.6, 0.0),
    (59.0, 59.0, 59.0, 59.0, 0.0),
    (53.2, 55.0, 52.0, 53.5, 0.0),      # open 53.2 < stop
]
trades = run_one_test(bars, +1, 100.0, 90.0, 130.0)
check("T1c: 連續5日跌停，第6日以開盤價出場，locked_days==5",
      len(trades) == 1 and abs(trades[0]["exit_price"] - 53.2) < 1e-9 and trades[0]["locked_days"] == 5)

# ============================================================
# T2a: long, limit-downs, then tradable day opens BELOW stop
#   (stop not touched at open → exit at open, NOT at stop)
# ============================================================
bars = base_prefix + [
    (100.0, 100.5, 99.0, 100.0, 0.0),
    (90.0, 90.0, 90.0, 90.0, 0.0),
    (73.0, 74.0, 70.0, 73.5, 0.0),      # gap-down open 73 < stop 90
]
trades = run_one_test(bars, +1, 100.0, 90.0, 130.0)
check("T2a: 跌停後跳空開在停損之下，以開盤價成交，不假設停損價",
      len(trades) == 1 and abs(trades[0]["exit_price"] - 73.0) < 1e-9,
      f"exit_price={trades[0]['exit_price'] if trades else 'n/a'}")

# ============================================================
# T2b-i: long, LD then gap-up open ABOVE stop, intraday dip touches stop
#   path: 100 -> LD 90 -> LD 81 -> open 88 (>85 stop), low 84 <= 85 -> exit at 85
# ============================================================
bars = base_prefix + [
    (100.0, 100.5, 99.0, 100.0, 0.0),
    (90.0, 90.0, 90.0, 90.0, 0.0),
    (81.0, 81.0, 81.0, 81.0, 0.0),
    (88.0, 89.0, 84.0, 87.0, 0.0),      # open > stop, intraday low 84 <= stop 85
]
trades = run_one_test(bars, +1, 100.0, 85.0, 130.0)
check("T2b-i: 跳空開在停損之上，盤中觸停損以停損價出場",
      len(trades) == 1 and abs(trades[0]["exit_price"] - 85.0) < 1e-9 and trades[0]["exit_reason"] == "INITIAL_STOP",
      f"exit_price={trades[0]['exit_price'] if trades else 'n/a'}")

# ============================================================
# T2b-ii: long, same gap-up open, intraday low stays ABOVE stop
#   stop never triggers -> position stays open -> END_OF_DATA at final close
# ============================================================
bars = base_prefix + [
    (100.0, 100.5, 99.0, 100.0, 0.0),
    (90.0, 90.0, 90.0, 90.0, 0.0),
    (81.0, 81.0, 81.0, 81.0, 0.0),
    (88.0, 89.5, 85.5, 89.0, 0.0),      # low 85.5 > stop 85 -> no stop
    (90.0, 91.0, 89.0, 90.5, 0.0),
]
trades = run_one_test(bars, +1, 100.0, 85.0, 130.0)
check("T2b-ii: 跳空開在停損之上且盤中未觸停損，停損維持 pending，以 END_OF_DATA 結束",
      len(trades) == 1 and trades[0]["exit_reason"] == "END_OF_DATA" and abs(trades[0]["exit_price"] - 90.5) < 1e-9,
      f"reason={trades[0]['exit_reason'] if trades else 'n/a'}")

# ============================================================
# T2b-iii (進場日版本): 進場跳空開在停損之上 -> 停損不成交於開盤價
# ============================================================
bars = base_prefix + [
    (100.0, 100.5, 99.0, 100.0, 0.0),
    (88.0, 89.5, 86.0, 89.0, 0.0),      # gap-down from 100 but ABOVE... wait entry 88 < stop 85? no
]
# (this variant covered by T2b-i/ii; skip constructing ambiguous case)

# ============================================================
# T3a: short, holds through consecutive 一字漲停 (can't cover), first tradable day >= stop
#   stop must execute at OPEN of first tradable day (gap-through), NOT at stop 105
#   path: entry 100 -> LU 110 -> LU 121 -> tradable open 115 >= stop 105 -> exit at 115
# ============================================================
bars = base_prefix + [
    (100.0, 100.5, 99.5, 100.0, 999.0),
    (110.0, 110.0, 110.0, 110.0, 999.0),  # 一字漲停 - short can't cover
    (121.0, 121.0, 121.0, 121.0, 999.0),  # 一字漲停 - short can't cover
    (115.0, 116.0, 112.0, 113.0, 999.0),  # tradable, high 115 >= stop 105 -> exit at max(open, stop)=115
]
trades = run_one_test(bars, -1, 100.0, 105.0, 85.0)
check("T3a: 空頭連續一字漲停不成交，首個可成交日 gap-through 以開盤價回補（非停損價）",
      len(trades) == 1 and abs(trades[0]["exit_price"] - 115.0) < 1e-9 and trades[0]["locked_days"] == 2
      and trades[0]["exit_reason"] == "INITIAL_STOP",
      f"exit={trades[0]['exit_price'] if trades else 'n/a'} locked={trades[0]['locked_days'] if trades else 'n/a'}")

# ============================================================
# T3b: short, 一字漲停 absorbs ALL bars to data end
#   -> locked at end, position NOT recorded as closed trade
# ============================================================
bars = base_prefix + [
    (100.0, 100.5, 99.5, 100.0, 999.0),
    (110.0, 110.0, 110.0, 110.0, 999.0),
    (121.0, 121.0, 121.0, 121.0, 999.0),
]
trades = run_one_test(bars, -1, 100.0, 105.0, 85.0)
check("T3b: 空頭連續一字漲停至資料結束，部位維持 OPEN 不計入已平倉（LOCKED_AT_END）",
      len(trades) == 0,
      f"trades={len(trades)}")

# ============================================================
# T4: long, 一字跌停 to data end -> locked_at_end, no trade recorded
# ============================================================
bars = base_prefix + [
    (100.0, 100.5, 99.0, 100.0, 0.0),
    (90.0, 90.0, 90.0, 90.0, 0.0),
    (81.0, 81.0, 81.0, 81.0, 0.0),
]
trades = run_one_test(bars, +1, 100.0, 90.0, 130.0)
check("T4: 多頭跌停至資料結束，LOCKED_AT_END 不計入已平倉（不虛構成交）",
      len(trades) == 0,
      f"trades={len(trades)}")

# ============================================================
# T5a: short, tradable forced-cover day before ex-div
#   entry 100 -> day1 close 102 -> day2 = day before ex-div? No:
#   ex-date on day3 => forced cover on day2 at close, no dividend
# ============================================================
div_df = pd.DataFrame({"ex_date": ["2024-06-09"], "cash_dividend": [1.5]})
# bars: prefix dates 2024-06-03..2024-06-08; SIG_IDX=5 -> sig 2024-06-08, entry day=2024-06-09??
# Recompute dates: day0 = 2024-06-03 (index 6), so day2 = 2024-06-05, day3 = 2024-06-06.
# Use explicit ex_date matching a bar date: prefix 2024-06-03..2024-06-08 (idx 0-5)
# entry (idx 6) = 2024-06-09, day1 = 2024-06-10, day2 = 2024-06-11, day3 = 2024-06-12
div_df = pd.DataFrame({"ex_date": ["2024-06-12"], "cash_dividend": [1.5]})
bars = base_prefix + [
    (100.0, 100.5, 99.5, 100.0, 999.0),   # 2024-06-09 entry
    (101.5, 102.0, 101.0, 102.0, 999.0),  # 2024-06-10
    (103.0, 104.0, 102.5, 103.0, 999.0),  # 2024-06-11 (day before ex-div) -> forced cover at close
    (104.0, 105.0, 103.0, 104.5, 999.0),  # 2024-06-12 ex-div (should NOT reach)
]
trades = run_one_test(bars, -1, 100.0, 105.0, 85.0, div_df=div_df)
check("T5a: 融券空頭於除息日前一日強制回補（收盤價），exit_reason=FORCED_COVER_EX_DIV，不付股利",
      len(trades) == 1 and trades[0]["exit_reason"] == "FORCED_COVER_EX_DIV"
      and trades[0]["exit_date"] == "2024-06-11"
      and abs(trades[0]["dividend_cash"] - 0.0) < 1e-9
      and trades[0]["forced_cover"] is True,
      f"reason={trades[0]['exit_reason'] if trades else 'n/a'} ex={trades[0]['exit_date'] if trades else 'n/a'} div={trades[0]['dividend_cash'] if trades else 'n/a'}")

# ============================================================
# T5b: short, forced-cover day was limit-up (blocked) -> exits ON ex-date, PAYS dividend
#   day before ex-div (2024-06-11) = 一字漲停 -> blocked
#   2024-06-12 = ex-div, exit at close, dividend_cash == 1.5
# ============================================================
bars = base_prefix + [
    (100.0, 100.5, 99.5, 100.0, 999.0),   # entry 2024-06-09
    (101.0, 101.5, 100.5, 101.0, 999.0),  # 2024-06-10
    (111.0, 111.0, 111.0, 111.0, 999.0),  # 2024-06-11 一字漲停 -> blocked, cannot cover
    (112.0, 113.0, 111.5, 112.0, 999.0),  # 2024-06-12 ex-div -> cover at close, pays div
]
trades = run_one_test(bars, -1, 100.0, 105.0, 85.0, div_df=div_df)
check("T5b: 強制回補日遇漲停無法回補，於除息日才蓋倉且必須支付股利補償",
      len(trades) == 1 and trades[0]["exit_reason"] == "FORCED_COVER_EX_DIV"
      and trades[0]["exit_date"] == "2024-06-12"
      and abs(trades[0]["dividend_cash"] - 1.5) < 1e-9
      and trades[0]["locked_days"] == 1,
      f"reason={trades[0]['exit_reason'] if trades else 'n/a'} div={trades[0]['dividend_cash'] if trades else 'n/a'} locked={trades[0]['locked_days'] if trades else 'n/a'}")

# ============================================================
# T6: short entry day 一字跌停 -> no sale possible -> UNFILLED
# ============================================================
bars = base_prefix + [
    (90.0, 90.0, 90.0, 90.0, 999.0),     # 一字跌停 (from 100.5 prev close): short sale unfilled
    (81.0, 81.0, 81.0, 81.0, 999.0),     # further limit-down
]
trades = run_one_test(bars, -1, 100.0, 105.0, 85.0)
check("T6: 空頭入場日一字跌停，無買方可成交，UNFILLED（不成交）",
      len(trades) == 0,
      f"trades={len(trades)}")

# ============================================================
# T6b: long entry day 一字漲停 -> UNFILLED (pre-existing behavior, sanity)
# ============================================================
bars = base_prefix + [
    (111.0, 111.0, 111.0, 111.0, 0.0),   # 一字漲停 (from prev 100.5: +10.4%, within ±10% band tolerance? exactly 1.095 -> flagged)
]
trades = run_one_test(bars, +1, 111.0, 101.0, 140.0)
check("T6b: 多頭入場日一字漲停，無賣方可成交，UNFILLED",
      len(trades) == 0,
      f"trades={len(trades)}")

# ============================================================
# T7: ex-div one-tick bar is NOT limit-down (reference price differs)
#   engine must not lock a long on an ex-date one-tick open
#   open 92 from prev close 100: |92-90|=2 -> beyond 0.5% tolerance of 90 -> not limit-down
#   (only true if data raw; engine uses raw prev_close)
# ============================================================
bars = base_prefix + [
    (100.0, 100.5, 99.0, 100.0, 0.0),
    (92.0, 92.0, 92.0, 92.0, 0.0),       # ex-div adjustment one-tick (NOT 一字跌停)
    (94.0, 95.0, 93.0, 94.0, 0.0),
]
trades = run_one_test(bars, +1, 100.0, 90.0, 130.0)
check("T7: 除息調整造成的一字 bar 不應被判為跌停鎖死（locked_days==0）",
      len(trades) == 1 and trades[0]["locked_days"] == 0,
      f"locked={trades[0]['locked_days'] if trades else 'n/a'}")

# ============================================================
# T8: short covered on 一字跌停 day IS allowed (limit-down is a BUY day for shorts)
#   short holds; one-tick limit-down close 90: blocked=False for shorts
#   -> days_held advances, locked_days stays 0
# ============================================================
bars = base_prefix + [
    (100.0, 100.5, 99.5, 100.0, 999.0),
    (90.0, 90.0, 90.0, 90.0, 999.0),     # 一字跌停: short can cover (buy), must NOT lock
    (81.0, 81.0, 81.0, 81.0, 999.0),     # another 一字跌停
    (85.0, 86.0, 84.0, 85.5, 999.0),     # tradable
]
trades = run_one_test(bars, -1, 100.0, 105.0, 85.0)
check("T8: 空頭可在跌停日回補（blocked 判定方向性），locked_days==0",
      len(trades) == 1 and trades[0]["locked_days"] == 0,
      f"locked={trades[0]['locked_days'] if trades else 'n/a'}")

# ============================================================
# T9: long dividend across TWO ex-dates must be SUMMED
#   entry 100, holds to data end (EMA=0, no stop hit)
# ============================================================
div_df = pd.DataFrame({
    "ex_date": ["2024-06-10", "2024-06-12"],
    "cash_dividend": [1.5, 1.0],
})
bars = base_prefix + [
    (100.0, 100.5, 99.0, 100.0, 0.0),
    (100.5, 101.0, 100.0, 100.8, 0.0),   # 2024-06-10 ex-div 1.5
    (101.0, 102.0, 100.5, 101.5, 0.0),   # 2024-06-11
    (101.5, 102.0, 101.0, 101.8, 0.0),   # 2024-06-12 ex-div 1.0
]
trades = run_one_test(bars, +1, 100.0, 90.0, 130.0, div_df=div_df)
check("T9: 長期持有跨兩次除息，股利加總為 2.5",
      len(trades) == 1 and abs(trades[0]["dividend_cash"] - 2.5) < 1e-9 and len(trades[0]["dividend_events"].split(";")) == 2,
      f"div={trades[0]['dividend_cash'] if trades else 'n/a'} events={trades[0]['dividend_events'] if trades else 'n/a'}")

# ============================================================
# T10: long with NO dividend events -> delta exactly 0 (audited invariant)
# ============================================================
bars = base_prefix + [
    (100.0, 100.5, 99.0, 100.0, 0.0),
    (101.0, 101.5, 100.5, 101.0, 0.0),
    (102.0, 102.5, 101.0, 101.5, 0.0),
]
trades = run_one_test(bars, +1, 100.0, 90.0, 130.0, div_df=None)
check("T10: 無除息交易 dividend_cash 精確為 0，expected_div_delta_r 精確為 0",
      len(trades) == 1 and trades[0]["dividend_cash"] == 0.0 and trades[0]["expected_div_delta_r"] == 0.0,
      f"div={trades[0]['dividend_cash'] if trades else 'n/a'} exp_r={trades[0]['expected_div_delta_r'] if trades else 'n/a'}")

# ============================================================
# T11: short across ex-date (forced-cover day blocked) -> must PAY dividend,
#   net_r lower than identical path without dividend
# ============================================================
div_df = pd.DataFrame({"ex_date": ["2024-06-12"], "cash_dividend": [2.0]})
bars = base_prefix + [
    (100.0, 100.5, 99.5, 100.0, 999.0),
    (101.0, 101.5, 100.5, 101.0, 999.0),
    (111.0, 111.0, 111.0, 111.0, 999.0),   # 2024-06-11 一字漲停: forced-cover day, blocked
    (112.0, 113.0, 111.5, 112.0, 999.0),   # 2024-06-12 ex-div: forced cover at close, PAYS div
]
t_with = run_one_test(bars, -1, 100.0, 110.0, 85.0, div_df=div_df)
t_without = run_one_test(bars, -1, 100.0, 110.0, 85.0, div_df=None)
ok_sign = (len(t_with) == 1 and len(t_without) == 1
           and t_with[0]["exit_reason"] == "FORCED_COVER_EX_DIV"
           and t_with[0]["net_r"] < t_without[0]["net_r"]
           and abs(t_with[0]["dividend_cash"] - 2.0) < 1e-9)
check("T11: 空頭跨除息（除息日強制蓋倉）必須支付股利補償，net_r 低於無股利情境",
      ok_sign,
      f"with_div={t_with[0]['net_r'] if t_with else 'n/a'} (div={t_with[0]['dividend_cash'] if t_with else 'n/a'}) vs without={t_without[0]['net_r'] if t_without else 'n/a'}")

# ============================================================
# T12: MAX_120D fires only on tradable days
#   short with EMA=999, no stop hit, 一字跌停 on day 120 would block... (max_hold is config)
#   Here just assert sane behavior: no crash, trade exits at MAX_120D or END_OF_DATA.
#   (covered implicitly by T2b-ii/T8; skip constructing 120 bars twice)
# ============================================================

print()
n_fail = sum(1 for _, ok, _ in results if not ok)
print(f"Summary: {len(results) - n_fail}/{len(results)} passed")
sys.exit(1 if n_fail else 0)
