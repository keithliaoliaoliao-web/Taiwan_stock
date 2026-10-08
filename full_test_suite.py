import pandas as pd
import numpy as np
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple

NOT_YET_QUANTIFIED = "NOT_YET_QUANTIFIED"
NOT_YET_QUANTIFIED_RANGE_CONTEXT = "NOT_YET_QUANTIFIED_RANGE_CONTEXT"
LEG_IDENTIFICATION_NOT_YET_QUANTIFIED = "NOT_YET_QUANTIFIED"

class H1H2State(str, Enum):
    NO_SETUP = "NO_SETUP"
    PULLBACK_DETECTED = "PULLBACK_DETECTED"
    FIRST_ATTEMPT_DETECTED = "FIRST_ATTEMPT_DETECTED"
    FIRST_ATTEMPT_FAILED = "FIRST_ATTEMPT_FAILED"
    SECOND_ATTEMPT_DETECTED = "SECOND_ATTEMPT_DETECTED"
    H2_CONFIRMED = "H2_CONFIRMED"
    INVALIDATED = "INVALIDATED"
    NOT_YET_QUANTIFIED = "NOT_YET_QUANTIFIED"

@dataclass
class H1H2Diagnostics:
    setup_type: str = "NONE"
    state: H1H2State = H1H2State.NO_SETUP
    h1_detected: bool = False
    h1_index: Optional[int] = None
    h1_high: Optional[float] = None
    h1_low: Optional[float] = None
    h1_status: str = "NONE"
    h2_detected: bool = False
    h2_index: Optional[int] = None
    h2_high: Optional[float] = None
    h2_low: Optional[float] = None
    h2_status: str = "NOT_CONFIRMED"
    pullback_state: str = "NONE"
    leg_state: str = "NONE"
    peak_index: Optional[int] = None
    peak_high: Optional[float] = None
    pullback_low: Optional[float] = None
    leg1_low: Optional[float] = None
    leg2_low: Optional[float] = None
    invalidation_reason: str = ""
    audit_trail: List[str] = field(default_factory=list)

class H1H2StateMachine:
    """
    Transparent, auditable, deterministic state machine for Al Brooks H1/H2 detection.
    
    Category definitions for rules:
    [A] = Al Brooks price action concept
    [B] = Engineering rule
    [C] = Risk management
    [D] = Proxy
    [E] = NOT_YET_QUANTIFIED / USER DECISION REQUIRED
    """
    
    @staticmethod
    def evaluate(
        df: pd.DataFrame,
        eval_idx: int,
        trend_confirmed: bool = True,
        is_trading_range: bool = False
    ) -> H1H2Diagnostics:
        diag = H1H2Diagnostics()
        
        # Rule 1 [B]: Insufficient history check
        if eval_idx < 2 or len(df) < 3:
            diag.state = H1H2State.NOT_YET_QUANTIFIED
            diag.h2_status = NOT_YET_QUANTIFIED
            diag.invalidation_reason = "INSUFFICIENT_HISTORY"
            diag.audit_trail.append("[B] Insufficient bar history (< 3 bars) for structural evaluation")
            return diag
            
        # Rule 2 [A][E]: Trading range context protection
        # Al Brooks: H1/H2 buy setups only exist within a bull trend pullback.
        # If trading range is detected or trend context cannot be established:
        if is_trading_range or not trend_confirmed:
            diag.state = H1H2State.INVALIDATED
            diag.h2_status = NOT_YET_QUANTIFIED_RANGE_CONTEXT
            diag.invalidation_reason = "TRADING_RANGE_CONTEXT_PREVENTS_H2"
            diag.audit_trail.append("[A][E] Market in trading range or unconfirmed trend; H2 buy setup requires a bull trend pullback")
            return diag

        # Rule 3 [A]: Identify the Bull Trend Peak (Swing High before pullback)
        # Search backwards from eval_idx to find the highest High in the current trend
        # Al Brooks: The pullback begins after a trend high is established.
        lookback_start = 0
        highs = df["High"].iloc[lookback_start : eval_idx + 1]
        peak_rel_idx = int(highs.argmax())
        peak_idx = lookback_start + peak_rel_idx
        peak_high = float(df["High"].iloc[peak_idx])
        
        diag.peak_index = peak_idx
        diag.peak_high = peak_high
        
        # Rule 4 [A]: If eval_idx is at the peak, price is making a trend high -> No pullback exists
        if peak_idx == eval_idx:
            diag.state = H1H2State.NO_SETUP
            diag.invalidation_reason = "AT_TREND_HIGH_NO_PULLBACK"
            diag.audit_trail.append(f"[A] Bar {eval_idx} is at peak ({peak_high}); no pullback underway")
            return diag
            
        # Rule 5 [A]: Walk through the pullback sequence from peak_idx + 1 to eval_idx
        current_state = H1H2State.PULLBACK_DETECTED
        diag.pullback_state = "LEG_1_DOWN"
        diag.leg_state = "LEG_1_DOWN"
        diag.audit_trail.append(f"[A] Pullback began at bar {peak_idx + 1} from peak {peak_high} (bar {peak_idx})")
        
        h1_idx: Optional[int] = None
        h1_high: Optional[float] = None
        h1_low: Optional[float] = None
        h2_idx: Optional[int] = None
        h2_high: Optional[float] = None
        h2_low: Optional[float] = None
        leg1_low: Optional[float] = None
        leg2_low: Optional[float] = None
        pullback_low: Optional[float] = None
        
        for b in range(peak_idx + 1, eval_idx + 1):
            cur_high = float(df["High"].iloc[b])
            cur_low = float(df["Low"].iloc[b])
            prev_high = float(df["High"].iloc[b - 1])
            prev_low = float(df["Low"].iloc[b - 1])
            
            pullback_low = cur_low if pullback_low is None else min(pullback_low, cur_low)
            
            # --- State 1: PULLBACK_DETECTED (Leg 1 Down) ---
            if current_state == H1H2State.PULLBACK_DETECTED:
                leg1_low = cur_low if leg1_low is None else min(leg1_low, cur_low)
                
                # Rule 6 [A]: First bar whose High > previous bar High is High 1 (H1)
                if cur_high > prev_high:
                    current_state = H1H2State.FIRST_ATTEMPT_DETECTED
                    h1_idx = b
                    h1_high = cur_high
                    h1_low = cur_low
                    diag.h1_detected = True
                    diag.h1_index = b
                    diag.h1_high = cur_high
                    diag.h1_low = cur_low
                    diag.h1_status = "DETECTED"
                    diag.pullback_state = "ATTEMPT_1_UP"
                    diag.leg_state = "ATTEMPT_1_UP"
                    diag.audit_trail.append(f"[A] Bar {b}: H1 detected (High {cur_high} > prev High {prev_high})")
                else:
                    diag.audit_trail.append(f"[A] Bar {b}: Leg 1 down continues (High {cur_high} <= prev High {prev_high})")
                    
            # --- State 2: FIRST_ATTEMPT_DETECTED (H1 Active) ---
            elif current_state == H1H2State.FIRST_ATTEMPT_DETECTED:
                # Rule 7 [A]: Did H1 attempt reach or exceed the trend peak?
                if cur_high >= peak_high:
                    current_state = H1H2State.INVALIDATED
                    diag.h1_status = "SUCCEEDED"
                    diag.invalidation_reason = "H1_RESUMED_TREND_NEW_HIGH"
                    diag.audit_trail.append(f"[A] Bar {b}: H1 attempt reached/exceeded peak ({cur_high} >= {peak_high}); trend resumed, no H2 possible")
                    break
                # Rule 8 [A]: Did H1 attempt continue higher below peak?
                elif cur_high > prev_high:
                    h1_high = max(h1_high, cur_high)
                    diag.h1_high = h1_high
                    diag.audit_trail.append(f"[A] Bar {b}: H1 attempt extended higher ({cur_high})")
                # Rule 9 [A]: Did H1 attempt stall and sellers take control (H1 Failure)?
                elif cur_low < prev_low or cur_high < prev_high:
                    current_state = H1H2State.FIRST_ATTEMPT_FAILED
                    diag.h1_status = "FAILED"
                    diag.pullback_state = "LEG_2_DOWN"
                    diag.leg_state = "LEG_2_DOWN"
                    leg2_low = cur_low
                    diag.audit_trail.append(f"[A] Bar {b}: H1 attempt failed; seller resumption (Low {cur_low} < prev Low {prev_low}); Leg 2 down initiated")
                else:
                    # Inside / pause bar
                    diag.audit_trail.append(f"[A] Bar {b}: Neutral pause inside H1 attempt")
                    
            # --- State 3: FIRST_ATTEMPT_FAILED (Leg 2 Down) ---
            elif current_state == H1H2State.FIRST_ATTEMPT_FAILED:
                leg2_low = cur_low if leg2_low is None else min(leg2_low, cur_low)
                
                # Rule 10 [A]: Second bar whose High > previous bar High during the pullback is High 2 (H2)
                if cur_high > prev_high:
                    current_state = H1H2State.H2_CONFIRMED
                    h2_idx = b
                    h2_high = cur_high
                    h2_low = cur_low
                    diag.h2_detected = True
                    diag.h2_index = b
                    diag.h2_high = cur_high
                    diag.h2_low = cur_low
                    diag.h2_status = "CONFIRMED"
                    diag.setup_type = "H2"
                    diag.pullback_state = "ATTEMPT_2_UP"
                    diag.leg_state = "ATTEMPT_2_UP"
                    diag.audit_trail.append(f"[A] Bar {b}: H2 confirmed (second attempt breaking prev High {prev_high} after failed H1)")
                else:
                    diag.audit_trail.append(f"[A] Bar {b}: Leg 2 down continues (High {cur_high} <= prev High {prev_high})")
                    
            # --- State 4: H2_CONFIRMED (Post-H2 Evolution) ---
            elif current_state == H1H2State.H2_CONFIRMED:
                if cur_high >= peak_high:
                    current_state = H1H2State.INVALIDATED
                    diag.invalidation_reason = "H2_RESUMED_TREND_NEW_HIGH"
                    diag.audit_trail.append(f"[A] Bar {b}: H2 exceeded peak, trend resumed")
                elif cur_low < prev_low:
                    current_state = H1H2State.INVALIDATED
                    diag.invalidation_reason = "H2_ATTEMPT_COMPLETED_OR_FAILED"
                    diag.audit_trail.append(f"[A] Bar {b}: H2 attempt finished or failed (subsequent attempt would be H3/wedge)")
                    
        diag.state = current_state
        diag.pullback_low = pullback_low
        diag.leg1_low = leg1_low
        diag.leg2_low = leg2_low
        
        # Rule 11 [B]: Final validation for eval_idx
        # H2 is confirmed at eval_idx ONLY IF eval_idx was the bar where H2 triggered!
        if diag.h2_status == "CONFIRMED":
            if diag.h2_index != eval_idx:
                diag.h2_status = "NOT_CONFIRMED"
                diag.invalidation_reason = f"H2_TRIGGERED_AT_PAST_BAR_{diag.h2_index}"
        else:
            if current_state == H1H2State.PULLBACK_DETECTED:
                diag.invalidation_reason = "NO_BULLISH_ATTEMPT_DETECTED"
            elif current_state == H1H2State.FIRST_ATTEMPT_DETECTED:
                diag.invalidation_reason = "ONLY_FIRST_ATTEMPT_DETECTED"
            elif current_state == H1H2State.FIRST_ATTEMPT_FAILED:
                diag.invalidation_reason = "FIRST_ATTEMPT_FAILED_NO_SECOND_ATTEMPT"
                
        return diag

# =========================================================================
# UNIT TESTS (TEST A through TEST G)
# =========================================================================

# TEST A: Valid bullish trend pullback -> H1 -> H1 fails -> second bullish attempt -> H2 confirmed
df_a = pd.DataFrame({
    'Open':  [100, 102, 104, 103, 102, 101.5, 102.5, 101, 100, 101],
    'High':  [102, 104, 106, 104, 103, 103.5, 102.5, 101, 100.5, 102],
    'Low':   [ 99, 101, 103, 102, 101, 101.0, 101.0,  99.5, 99.0, 100],
    'Close': [102, 104, 105, 102.5, 101.5, 103.0, 101.5, 100, 99.5, 101.8]
})
# Peak at bar 2 (106). Pullback bar 3, 4. H1 at bar 5. H1 fails at bar 6. Bar 7, 8 leg 2. H2 at bar 9!
res_a = H1H2StateMachine.evaluate(df_a, eval_idx=9, trend_confirmed=True)
print("TEST A result:", res_a.h2_status, "H1 idx:", res_a.h1_index, "H2 idx:", res_a.h2_index)
assert res_a.h2_status == "CONFIRMED"
assert res_a.h1_index == 5
assert res_a.h2_index == 9
assert res_a.setup_type == "H2"

# TEST B: Bullish trend pullback -> only one bullish attempt -> H2 NOT confirmed
res_b = H1H2StateMachine.evaluate(df_a, eval_idx=7, trend_confirmed=True)
print("TEST B result:", res_b.h2_status, "Reason:", res_b.invalidation_reason)
assert res_b.h2_status == "NOT_CONFIRMED"
assert res_b.h1_detected == True
assert res_b.h2_detected == False
assert res_b.invalidation_reason == "FIRST_ATTEMPT_FAILED_NO_SECOND_ATTEMPT"

# TEST C: Single bullish candle after a pullback -> must NOT automatically become H2
df_c = pd.DataFrame({
    'Open':  [100, 102, 105, 103, 101, 100],
    'High':  [102, 105, 107, 104, 102, 103], # Peak at bar 2 (107). Pullback bars 3, 4. H1 at bar 5.
    'Low':   [ 99, 101, 104, 102, 100, 100],
    'Close': [102, 105, 106, 102, 100.5, 102.5]
})
res_c = H1H2StateMachine.evaluate(df_c, eval_idx=5, trend_confirmed=True)
print("TEST C result: H1 detected:", res_c.h1_detected, "H2 status:", res_c.h2_status, "Reason:", res_c.invalidation_reason)
assert res_c.h1_detected == True
assert res_c.h2_detected == False
assert res_c.h2_status == "NOT_CONFIRMED"
assert res_c.invalidation_reason == "ONLY_FIRST_ATTEMPT_DETECTED"

# TEST D: Sideways trading range with repeated small highs/lows -> must NOT manufacture H1/H2
df_d = pd.DataFrame({
    'Open':  [100, 100.5, 100.2, 100.8, 100.3, 100.7],
    'High':  [101, 101.2, 100.9, 101.3, 101.0, 101.2],
    'Low':   [ 99.5, 99.8, 99.6, 99.7, 99.5, 99.8],
    'Close': [100.5, 100.2, 100.8, 100.3, 100.7, 100.4]
})
res_d = H1H2StateMachine.evaluate(df_d, eval_idx=5, trend_confirmed=False, is_trading_range=True)
print("TEST D result:", res_d.h2_status, "Reason:", res_d.invalidation_reason)
assert res_d.h2_status == NOT_YET_QUANTIFIED_RANGE_CONTEXT
assert res_d.h2_detected == False

# TEST E: H1 occurs but successfully resumes the bullish trend -> must NOT create a second H2 from the same attempt
df_e = pd.DataFrame({
    'Open':  [100, 104, 102, 101, 103, 107, 106],
    'High':  [104, 106, 103, 102, 105, 109, 107], # Peak at bar 1 (106). H1 at bar 4. Bar 5 breaks to 109! Bar 6 is at 107.
    'Low':   [ 99, 103, 101, 100, 102, 106, 105],
    'Close': [104, 105, 101.5, 101, 104.5, 108.5, 106.5]
})
# At bar 5: H1 resumed trend to 109 (new high)
res_e5 = H1H2StateMachine.evaluate(df_e, eval_idx=5, trend_confirmed=True)
print("TEST E (bar 5):", res_e5.h2_status, res_e5.invalidation_reason)
assert res_e5.h2_status == "NOT_CONFIRMED"
assert res_e5.h2_detected == False

# At bar 6: Pullback from the new peak (109). Bar 6 High 107 < 109. No H2!
res_e6 = H1H2StateMachine.evaluate(df_e, eval_idx=6, trend_confirmed=True)
print("TEST E (bar 6):", res_e6.h2_status, res_e6.invalidation_reason)
assert res_e6.h2_status == "NOT_CONFIRMED"
assert res_e6.h2_detected == False

# TEST F: Insufficient structural information -> status must be NOT_YET_QUANTIFIED
df_f = pd.DataFrame({
    'Open':  [100, 101],
    'High':  [102, 103],
    'Low':   [ 99, 100],
    'Close': [101, 102]
})
res_f = H1H2StateMachine.evaluate(df_f, eval_idx=1, trend_confirmed=True)
print("TEST F result:", res_f.h2_status, "Reason:", res_f.invalidation_reason)
assert res_f.h2_status == NOT_YET_QUANTIFIED

print("ALL TESTS (A, B, C, D, E, F) PASSED PERFECTLY!")
