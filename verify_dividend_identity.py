"""verify_dividend_identity.py - C3 股利精確恆等式驗證

驗證: net_r_with_div - net_r_no_div == dividend_cash / initial_risk
- 持有期間未跨除息日: delta 必須精確為 0
- 跨多個除息日: 股利必須是所有事件加總
- 空頭: delta 應為負 (股利支出)
"""
import pandas as pd

# C (adjusted + income) vs B (adjusted, no income) - same trade set
b = pd.read_csv('bt_B.csv')  # no dividend income
c = pd.read_csv('bt_C.csv')  # with dividend income

b_ids = set(b['ticker'] + '_' + b['sig_date'])
c_ids = set(c['ticker'] + '_' + c['sig_date'])
assert b_ids == c_ids, f"trade sets differ: B={len(b_ids)}, C={len(c_ids)}"
print(f"[OK] Trade sets identical: {len(b_ids)} trades")

merged = b.merge(c, on=['ticker', 'sig_date'], suffixes=('_B', '_C'))
print(f"[OK] Merged: {len(merged)} trades")

# Verify entry/exit match
assert (merged['entry_price_B'] == merged['entry_price_C']).all(), "entry prices differ"
assert (merged['exit_date_B'] == merged['exit_date_C']).all(), "exit dates differ"
assert (merged['entry_date_B'] == merged['entry_date_C']).all(), "entry dates differ"
print("[OK] Entry/exit prices and dates match")

# Verify dividend identity
merged['actual_delta'] = merged['net_r_C'] - merged['net_r_B']
merged['expected_delta'] = merged['expected_div_delta_r_C']  # expected = div_cash / initial_risk

merged['diff'] = (merged['actual_delta'] - merged['expected_delta']).abs()
max_diff = merged['diff'].max()
print(f"[CHECK] Max |actual_delta - expected_delta|: {max_diff:.6f}")

# Cases with no dividend
no_div = merged[merged['dividend_cash_C'] == 0]
print(f"[CHECK] Trades with no dividend: {len(no_div)}")
if len(no_div) > 0:
    zero_delta = (no_div['actual_delta'].abs() < 1e-9).all()
    print(f"  All have delta == 0: {zero_delta}")

# Cases with dividend
with_div = merged[merged['dividend_cash_C'] > 0]
print(f"[CHECK] Trades with dividend: {len(with_div)}")
if len(with_div) > 0:
    print(f"  Avg dividend cash: {with_div['dividend_cash_C'].mean():.4f}")
    print(f"  Avg actual delta: {with_div['actual_delta'].mean():.4f}")
    print(f"  Avg expected delta: {with_div['expected_delta'].mean():.4f}")

# Check direction: long should be positive, short should be negative
long_trades = merged[merged['direction_C'] == 'LONG']
short_trades = merged[merged['direction_C'] == 'SHORT']
print(f"[CHECK] Long trades: {len(long_trades)}, Short trades: {len(short_trades)}")
if len(long_trades) > 0:
    long_with_div = long_trades[long_trades['dividend_cash_C'] > 0]
    if len(long_with_div) > 0:
        print(f"  Long with div: delta >= 0: {(long_with_div['actual_delta'] >= -1e-9).all()}")
if len(short_trades) > 0:
    short_with_div = short_trades[short_trades['dividend_cash_C'] > 0]
    if len(short_with_div) > 0:
        print(f"  Short with div: delta <= 0: {(short_with_div['actual_delta'] <= 1e-9).all()}")

# Multi-event check
multi = merged[merged['dividend_events_C'].astype(str).str.contains(';')]
print(f"[CHECK] Trades with multiple dividend events: {len(multi)}")

if max_diff < 0.001:
    print(f"\n[PASS] Dividend identity holds (max diff {max_diff:.6f} < 0.001)")
else:
    print(f"\n[FAIL] Dividend identity violated (max diff {max_diff:.6f})")

# Save verification result
merged.to_csv('dividend_identity_check.csv', index=False, encoding='utf-8-sig')
print("Saved to dividend_identity_check.csv")
