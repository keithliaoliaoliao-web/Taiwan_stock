import pandas as pd
import numpy as np
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple

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
    h1_status: str = "NONE"
    h2_detected: bool = False
    h2_index: Optional[int] = None
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

def detect_h1_h2(df: pd.DataFrame, eval_idx: int, trend_start_idx: int = 0) -> H1H2Diagnostics:
    diag = H1H2Diagnostics()
    
    if eval_idx < 2 or len(df) < 3:
        diag.state = H1H2State.NOT_YET_QUANTIFIED
        diag.h2_status = "NOT_YET_QUANTIFIED"
        diag.invalidation_reason = "INSUFFICIENT_HISTORY"
        diag.audit_trail.append("Insufficient bar history for structural analysis")
        return diag
    
    # 1. Identify Peak of Bull Trend prior to or at eval_idx
    # Search from trend_start_idx to eval_idx
    highs = df["High"].iloc[trend_start_idx : eval_idx + 1]
    peak_rel_idx = highs.argmax()
    peak_idx = trend_start_idx + peak_rel_idx
    peak_high = float(df["High"].iloc[peak_idx])
    diag.peak_index = peak_idx
    diag.peak_high = peak_high
    
    # If the peak is at eval_idx, price is at trend high -> No pullback exists
    if peak_idx == eval_idx:
        diag.state = H1H2State.NO_SETUP
        diag.invalidation_reason = "AT_TREND_HIGH_NO_PULLBACK"
        diag.audit_trail.append(f"Bar {eval_idx} is at peak ({peak_high}); no pullback underway")
        return diag
    
    # 2. Walk through the pullback from peak_idx + 1 to eval_idx
    state = H1H2State.PULLBACK_DETECTED
    diag.pullback_state = "LEG_1_DOWN"
    diag.leg_state = "LEG_1_DOWN"
    diag.audit_trail.append(f"Pullback started at bar {peak_idx + 1} from peak {peak_high} (bar {peak_idx})")
    
    h1_idx = None
    h1_high = None
    h1_attempt_high = None
    leg1_low = None
    leg2_low = None
    pullback_low = None
    
    for b in range(peak_idx + 1, eval_idx + 1):
        cur_high = float(df["High"].iloc[b])
        cur_low = float(df["Low"].iloc[b])
        prev_high = float(df["High"].iloc[b - 1])
        prev_low = float(df["Low"].iloc[b - 1])
        
        pullback_low = cur_low if pullback_low is None else min(pullback_low, cur_low)
        
        if state == H1H2State.PULLBACK_DETECTED:
            leg1_low = cur_low if leg1_low is None else min(leg1_low, cur_low)
            # First time price exceeds prior bar high -> H1 attempt
            if cur_high > prev_high:
                state = H1H2State.FIRST_ATTEMPT_DETECTED
                h1_idx = b
                h1_high = cur_high
                h1_attempt_high = cur_high
                diag.h1_detected = True
                diag.h1_index = b
                diag.h1_high = cur_high
                diag.h1_status = "DETECTED"
                diag.pullback_state = "ATTEMPT_1_UP"
                diag.leg_state = "ATTEMPT_1_UP"
                diag.audit_trail.append(f"Bar {b}: H1 detected (High {cur_high} > prev High {prev_high})")
            else:
                diag.audit_trail.append(f"Bar {b}: Leg 1 down continues (High {cur_high} <= prev High {prev_high})")
                
        elif state == H1H2State.FIRST_ATTEMPT_DETECTED:
            # Did H1 exceed peak_high (resumed trend)?
            if cur_high >= peak_high:
                state = H1H2State.INVALIDATED
                diag.h1_status = "SUCCEEDED"
                diag.invalidation_reason = "H1_RESUMED_TREND_NEW_HIGH"
                diag.audit_trail.append(f"Bar {b}: H1 attempt exceeded peak ({cur_high} >= {peak_high}); trend resumed, no H2 possible")
                break
            # Did H1 attempt continue higher below peak?
            elif cur_high > prev_high:
                h1_attempt_high = max(h1_attempt_high, cur_high)
                diag.h1_high = max(diag.h1_high, cur_high)
                diag.audit_trail.append(f"Bar {b}: H1 attempt extended higher ({cur_high})")
            # Did H1 stall and turn back down?
            elif cur_low < prev_low or cur_high < prev_high:
                state = H1H2State.FIRST_ATTEMPT_FAILED
                diag.h1_status = "FAILED"
                diag.pullback_state = "LEG_2_DOWN"
                diag.leg_state = "LEG_2_DOWN"
                leg2_low = cur_low
                diag.audit_trail.append(f"Bar {b}: H1 attempt failed; seller resumption (Low {cur_low} < prev Low {prev_low}); Leg 2 down starts")
            else:
                # Inside bar or neutral pause
                diag.audit_trail.append(f"Bar {b}: Pause in H1 attempt")
                
        elif state == H1H2State.FIRST_ATTEMPT_FAILED:
            leg2_low = cur_low if leg2_low is None else min(leg2_low, cur_low)
            # Second attempt: High > prev High in Leg 2 down
            if cur_high > prev_high:
                state = H1H2State.H2_CONFIRMED
                diag.h2_detected = True
                diag.h2_index = b
                diag.h2_status = "CONFIRMED"
                diag.setup_type = "H2"
                diag.pullback_state = "ATTEMPT_2_UP"
                diag.leg_state = "ATTEMPT_2_UP"
                diag.audit_trail.append(f"Bar {b}: H2 confirmed (second attempt breaking prev High {prev_high})")
            else:
                diag.audit_trail.append(f"Bar {b}: Leg 2 down continues (High {cur_high} <= prev High {prev_high})")
                
        elif state == H1H2State.H2_CONFIRMED:
            # If bars continue after H2 confirmation
            if cur_high >= peak_high:
                state = H1H2State.INVALIDATED
                diag.invalidation_reason = "H2_RESUMED_TREND_NEW_HIGH"
            elif cur_high > prev_high:
                # H2 extending
                pass
            elif cur_low < prev_low:
                # H2 failed or wedge / H3
                state = H1H2State.INVALIDATED
                diag.invalidation_reason = "H2_ATTEMPT_COMPLETED_OR_FAILED"
                diag.audit_trail.append(f"Bar {b}: H2 attempt finished/stalled")
    
    diag.state = state
    diag.pullback_low = pullback_low
    diag.leg1_low = leg1_low
    diag.leg2_low = leg2_low
    
    if diag.h2_status != "CONFIRMED":
        if state == H1H2State.PULLBACK_DETECTED:
            diag.invalidation_reason = "NO_BULLISH_ATTEMPT_DETECTED"
        elif state == H1H2State.FIRST_ATTEMPT_DETECTED:
            diag.invalidation_reason = "ONLY_FIRST_ATTEMPT_DETECTED"
        elif state == H1H2State.FIRST_ATTEMPT_FAILED:
            diag.invalidation_reason = "FIRST_ATTEMPT_FAILED_NO_SECOND_ATTEMPT"
            
    return diag

print("detect_h1_h2 defined successfully")

# TEST A: Valid bullish trend pullback -> H1 -> H1 fails -> second bullish attempt -> H2 confirmed
df_a = pd.DataFrame({
    'Open':  [100, 102, 104, 103, 102, 101.5, 102.5, 101, 100, 101],
    'High':  [102, 104, 106, 104, 103, 103.5, 102.5, 101, 100.5, 102],
    'Low':   [ 99, 101, 103, 102, 101, 101.0, 101.0,  99.5, 99.0, 100],
    'Close': [102, 104, 105, 102.5, 101.5, 103.0, 101.5, 100, 99.5, 101.8]
})
# Peak at bar 2 (High 106)
# Bar 3: High 104 <= 106 (Pullback started, Leg 1)
# Bar 4: High 103 <= 104 (Leg 1 continues)
# Bar 5: High 103.5 > 103 (H1 detected!)
# Bar 6: Low 101 <= 101, High 102.5 < 103.5 (H1 failed! Leg 2 starts)
# Bar 7: High 101 <= 102.5, Low 99.5 < 101 (Leg 2 continues)
# Bar 8: High 100.5 <= 101, Low 99.0 < 99.5 (Leg 2 continues)
# Bar 9: High 102 > 100.5 (H2 confirmed!)
res_a = detect_h1_h2(df_a, eval_idx=9, trend_start_idx=0)
print("TEST A:", res_a.h2_status, "H1 idx:", res_a.h1_index, "H2 idx:", res_a.h2_index)
assert res_a.h2_status == "CONFIRMED"
assert res_a.h1_index == 5
assert res_a.h2_index == 9

# TEST B: Bullish trend pullback -> only one bullish attempt -> H2 NOT confirmed
# Evaluate at bar 5 or bar 7
res_b = detect_h1_h2(df_a, eval_idx=7, trend_start_idx=0)
print("TEST B:", res_b.h2_status, "Reason:", res_b.invalidation_reason)
assert res_b.h2_status == "NOT_CONFIRMED"
assert res_b.h1_detected == True
assert res_b.h2_detected == False

# TEST C: Single bullish candle after a pullback -> must NOT automatically become H2
df_c = pd.DataFrame({
    'Open':  [100, 102, 105, 103, 101, 100],
    'High':  [102, 105, 107, 104, 102, 103], # Peak at bar 2 (107). Bar 3 High 104. Bar 4 High 102. Bar 5 High 103 (H1)
    'Low':   [ 99, 101, 104, 102, 100, 100],
    'Close': [102, 105, 106, 102, 100.5, 102.5]
})
res_c = detect_h1_h2(df_c, eval_idx=5, trend_start_idx=0)
print("TEST C: H1 detected:", res_c.h1_detected, "H2 status:", res_c.h2_status)
assert res_c.h1_detected == True
assert res_c.h2_detected == False
assert res_c.h2_status == "NOT_CONFIRMED"

# TEST E: H1 occurs but successfully resumes the bullish trend -> must NOT create a second H2
df_e = pd.DataFrame({
    'Open':  [100, 104, 102, 101, 103, 107],
    'High':  [104, 106, 103, 102, 105, 109], # Peak at bar 1 (106). Bar 2 High 103. Bar 3 High 102. Bar 4 High 105 (H1). Bar 5 High 109 (new high >= 106!)
    'Low':   [ 99, 103, 101, 100, 102, 106],
    'Close': [104, 105, 101.5, 101, 104.5, 108.5]
})
res_e = detect_h1_h2(df_e, eval_idx=5, trend_start_idx=0)
print("TEST E: H1 status:", res_e.h1_status, "H2 status:", res_e.h2_status, "Reason:", res_e.invalidation_reason)
assert res_e.h1_status == "SUCCEEDED"
assert res_e.h2_detected == False

# TEST F: Insufficient structural information -> status must be NOT_YET_QUANTIFIED
df_f = pd.DataFrame({
    'Open':  [100, 101],
    'High':  [102, 103],
    'Low':   [ 99, 100],
    'Close': [101, 102]
})
res_f = detect_h1_h2(df_f, eval_idx=1, trend_start_idx=0)
print("TEST F: H2 status:", res_f.h2_status, "Reason:", res_f.invalidation_reason)
assert res_f.h2_status == "NOT_YET_QUANTIFIED"

print("All prototype tests passed!")
