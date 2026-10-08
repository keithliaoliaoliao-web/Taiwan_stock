"""
price_action_engine.py
Strategy Freeze v1 - Al Brooks-inspired Price Action Engine
包含 H2 突破訊號判定、A/B 評級、醞釀中 (Setup Forming) 追蹤與 Always In 狀態量化。

H1/H2 Structural Detection Redesign:
Turned into an explicit, transparent, auditable, deterministic state machine
based strictly on Al Brooks price action concepts without arbitrary numerical proxies.

Rule Classification Tags:
  [A] = Al Brooks price action concept
  [B] = Engineering rule
  [C] = Risk management
  [D] = Proxy
  [E] = NOT_YET_QUANTIFIED / USER DECISION REQUIRED
"""

from __future__ import annotations

from typing import Optional, Dict, Any, Tuple, List
from enum import Enum
from dataclasses import dataclass, field
import numpy as np
import pandas as pd

import config
from taiwan_market_rules import (
    next_tick_price,
    previous_tick_price,
    round_to_tick,
)

NOT_YET_QUANTIFIED = "NOT_YET_QUANTIFIED"
NOT_YET_QUANTIFIED_RANGE_CONTEXT = "NOT_YET_QUANTIFIED_RANGE_CONTEXT"
LEG_IDENTIFICATION = "NOT_YET_QUANTIFIED"


class SwingType(str, Enum):
    """
    Classification of swing points based on structural significance. [A][B]
    """
    MAJOR_HIGH = "MAJOR_HIGH"
    MINOR_HIGH = "MINOR_HIGH"
    MAJOR_LOW = "MAJOR_LOW"
    MINOR_LOW = "MINOR_LOW"


class SwingState(str, Enum):
    """
    Symmetric states of the real-time causal swing engine. [A][B]
    """
    SWING_UP = "SWING_UP"
    ABSORPTION_UP = "ABSORPTION_UP"
    SWING_DOWN = "SWING_DOWN"
    ABSORPTION_DOWN = "ABSORPTION_DOWN"
    # Aliases for backward compatibility
    TREND_PUSH_BULL = "SWING_UP"
    ABSORPTION_BULL = "ABSORPTION_UP"
    PULLBACK_DEVELOPING = "SWING_DOWN"
    ABSORPTION_PB = "ABSORPTION_DOWN"


@dataclass
class SwingNode:
    """
    A causally confirmed swing pivot node. [A][B]
    Guaranteed no repainting: confirmed_at_bar specifies the exact bar where this
    pivot was frozen.
    """
    index: int
    price: float
    swing_type: SwingType
    confirmed_at_bar: int
    bar_date: Optional[str] = None
    ema_pierced: bool = False


@dataclass
class SwingStructureResult:
    """
    Output of PriceActionSwingEngine for a given evaluation bar. [B]
    """
    state: SwingState = SwingState.SWING_UP
    major_swing_high: Optional[SwingNode] = None
    major_swing_low: Optional[SwingNode] = None
    recent_swing_high: Optional[SwingNode] = None
    recent_swing_low: Optional[SwingNode] = None
    minor_nodes: List[SwingNode] = field(default_factory=list)
    all_swings: List[SwingNode] = field(default_factory=list)
    bos: bool = False
    tentative_high: Optional[float] = None
    tentative_high_idx: Optional[int] = None
    tentative_low: Optional[float] = None
    tentative_low_idx: Optional[int] = None
    audit_trail: List[str] = field(default_factory=list)


class PriceActionSwingEngine:
    """
    Symmetric Causal Price Action Swing Structure Engine v1.
    Strictly zero arbitrary numerical thresholds, zero repainting, no fixed window pivots.
    Identifies Major/Minor Swings symmetrically, handles Inside Bar absorption, and detects Break of Structure (BOS).
    Runs in linear O(N) time across entire series.
    """

    @classmethod
    def evaluate_series(
        cls,
        df: pd.DataFrame,
        start_idx: int = 0
    ) -> List[SwingStructureResult]:
        n = len(df)
        if n == 0:
            return []

        results: List[SwingStructureResult] = []
        ema_col = "EMA_20" if "EMA_20" in df.columns else None

        actual_start = max(0, min(start_idx, n - 1))

        # Initial bar
        state = SwingState.SWING_UP
        tentative_high = float(df["High"].iloc[actual_start])
        tentative_high_idx = actual_start
        tentative_low = float(df["Low"].iloc[actual_start])
        tentative_low_idx = actual_start

        major_high: Optional[SwingNode] = None
        major_low: Optional[SwingNode] = None
        recent_high: Optional[SwingNode] = None
        recent_low: Optional[SwingNode] = None
        all_swings: List[SwingNode] = []
        minor_nodes: List[SwingNode] = []
        bos = False
        ema_pierced_in_pb = False

        # Fill any bars before actual_start with default
        for b in range(actual_start):
            results.append(SwingStructureResult(
                state=state,
                tentative_high=tentative_high,
                tentative_high_idx=tentative_high_idx,
                tentative_low=tentative_low,
                tentative_low_idx=tentative_low_idx
            ))

        results.append(SwingStructureResult(
            state=state,
            tentative_high=tentative_high,
            tentative_high_idx=tentative_high_idx,
            tentative_low=tentative_low,
            tentative_low_idx=tentative_low_idx
        ))

        for b in range(actual_start + 1, n):
            cur_o = float(df["Open"].iloc[b])
            cur_h = float(df["High"].iloc[b])
            cur_l = float(df["Low"].iloc[b])
            cur_c = float(df["Close"].iloc[b])
            prev_h = float(df["High"].iloc[b - 1])
            prev_l = float(df["Low"].iloc[b - 1])
            cur_ema = float(df[ema_col].iloc[b]) if ema_col and pd.notna(df[ema_col].iloc[b]) else None

            # 3.C: Inside Bar / Congestion Absorption
            is_inside = (cur_h <= prev_h) and (cur_l >= prev_l)

            # 3.A: Shift in Control Causal Triggers (Pure OHLC boolean)
            shift_to_sellers = (cur_c < prev_l) or (cur_c < cur_o and cur_l < prev_l)
            shift_to_bulls = (cur_c > prev_h) or (cur_c > cur_o and cur_h > prev_h)

            # --- Symmetrical State 1: SWING_UP or ABSORPTION_UP ---
            if state in (SwingState.SWING_UP, SwingState.ABSORPTION_UP):
                if cur_h > tentative_high:
                    tentative_high = cur_h
                    tentative_high_idx = b
                    state = SwingState.SWING_UP

                    # Al Brooks Major Low rule: A major higher low is a low that precedes a new high.
                    # If this push breaks prior major high, the preceding swing low is promoted to Major Low
                    if major_high is not None and tentative_high > major_high.price:
                        if recent_low is not None and recent_low.swing_type == SwingType.MINOR_LOW:
                            recent_low.swing_type = SwingType.MAJOR_LOW
                            major_low = recent_low
                elif is_inside:
                    state = SwingState.ABSORPTION_UP
                elif shift_to_sellers:
                    # 3.A: Freeze tentative high as confirmed Swing High without repainting
                    is_major_h = (major_high is None) or (tentative_high > major_high.price)
                    s_type = SwingType.MAJOR_HIGH if is_major_h else SwingType.MINOR_HIGH

                    node = SwingNode(
                        index=tentative_high_idx,
                        price=tentative_high,
                        swing_type=s_type,
                        confirmed_at_bar=b
                    )
                    all_swings.append(node)
                    recent_high = node
                    if is_major_h:
                        major_high = node
                    else:
                        minor_nodes.append(node)

                    # Symmetrical Transition to SWING_DOWN
                    state = SwingState.SWING_DOWN
                    tentative_low = cur_l
                    tentative_low_idx = b
                    ema_pierced_in_pb = (cur_ema is not None and cur_c < cur_ema)

            # --- Symmetrical State 2: SWING_DOWN or ABSORPTION_DOWN ---
            elif state in (SwingState.SWING_DOWN, SwingState.ABSORPTION_DOWN):
                if cur_l < tentative_low:
                    tentative_low = cur_l
                    tentative_low_idx = b
                    state = SwingState.SWING_DOWN
                    if cur_ema is not None and cur_c < cur_ema:
                        ema_pierced_in_pb = True
                elif is_inside:
                    state = SwingState.ABSORPTION_DOWN
                elif shift_to_bulls:
                    # 3.A: Freeze tentative low as confirmed Swing Low without repainting
                    # Major vs Minor: Pierced EMA (deep structural retracement) -> Major Low;
                    # else Minor Low (promoted to Major if subsequent push exceeds major high)
                    s_type = SwingType.MAJOR_LOW if ema_pierced_in_pb else SwingType.MINOR_LOW

                    node = SwingNode(
                        index=tentative_low_idx,
                        price=tentative_low,
                        swing_type=s_type,
                        confirmed_at_bar=b,
                        ema_pierced=ema_pierced_in_pb
                    )
                    all_swings.append(node)
                    recent_low = node
                    if s_type == SwingType.MAJOR_LOW:
                        major_low = node
                    else:
                        minor_nodes.append(node)

                    # Symmetrical Transition to SWING_UP
                    state = SwingState.SWING_UP
                    tentative_high = cur_h
                    tentative_high_idx = b

            # Break of Structure (BOS) Check
            if major_low is not None and cur_c < major_low.price:
                bos = True

            results.append(SwingStructureResult(
                state=state,
                major_swing_high=major_high,
                major_swing_low=major_low,
                recent_swing_high=recent_high,
                recent_swing_low=recent_low,
                minor_nodes=list(minor_nodes),
                all_swings=list(all_swings),
                bos=bos,
                tentative_high=tentative_high,
                tentative_high_idx=tentative_high_idx,
                tentative_low=tentative_low,
                tentative_low_idx=tentative_low_idx
            ))

        return results

    @classmethod
    def evaluate(
        cls,
        df: pd.DataFrame,
        up_to_idx: int,
        start_idx: int = 0
    ) -> SwingStructureResult:
        series = cls.evaluate_series(df.iloc[: up_to_idx + 1], start_idx=start_idx)
        return series[-1] if series else SwingStructureResult()

class H1H2State(str, Enum):
    """
    Explicit structural states for Al Brooks H1/H2 state machine. [A][B]
    """
    NO_SETUP = "NO_SETUP"
    PULLBACK_DETECTED = "PULLBACK_DETECTED"
    FIRST_ATTEMPT_DETECTED = "FIRST_ATTEMPT_DETECTED"       # H1 detected
    FIRST_ATTEMPT_FAILED = "FIRST_ATTEMPT_FAILED"           # H1 failed / Leg 2 developing
    SECOND_ATTEMPT_DETECTED = "SECOND_ATTEMPT_DETECTED"     # H2 detected
    H2_CONFIRMED = "H2_CONFIRMED"                           # H2 confirmed structurally
    INVALIDATED = "INVALIDATED"                             # Setup invalidated
    NOT_YET_QUANTIFIED = "NOT_YET_QUANTIFIED"


@dataclass
class H1H2Diagnostics:
    """
    Comprehensive diagnostic information for auditable H1/H2 evaluation. [B]
    Answers: 'Why was this classified as H2?' and 'Why was this NOT classified as H2?'
    """
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
    Deterministic Al Brooks H1/H2 structural state machine.

    Conceptual Architecture:
      Bull Trend -> Pullback -> First Bull Attempt (H1) -> H1 Fails ->
      Pullback Continues (Leg 2) -> Second Bull Attempt (H2) -> Potential Long Entry.

    Strict Requirements:
      - H2 is confirmed ONLY when a valid H1 existed, that H1 failed,
        and a subsequent second bullish attempt occurs.
      - No fuzzy scores, no arbitrary thresholds.
      - Concepts that cannot currently be quantified reliably are explicitly
        marked NOT_YET_QUANTIFIED.
    """

    @staticmethod
    def evaluate(
        df: pd.DataFrame,
        eval_idx: int,
        trend_confirmed: bool = True,
        is_trading_range: bool = False,
        trend_start_idx: int = 0,
        swing_res: Optional[SwingStructureResult] = None,
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
        # Al Brooks: H1/H2 buy setups exist strictly within a bull trend pullback.
        # If trading range is present or trend context cannot be established:
        if is_trading_range or not trend_confirmed:
            diag.state = H1H2State.INVALIDATED
            diag.h2_status = NOT_YET_QUANTIFIED_RANGE_CONTEXT
            diag.invalidation_reason = "TRADING_RANGE_CONTEXT_PREVENTS_H2"
            diag.audit_trail.append(
                "[A][E] Market in trading range or unconfirmed trend context; "
                "H2 buy setup requires a confirmed bull trend pullback."
            )
            return diag

        # Rule 2.1 [A]: Price Action Swing Structure Engine v1 & BOS Protection
        if swing_res is None:
            swing_res = PriceActionSwingEngine.evaluate(df, eval_idx, start_idx=trend_start_idx)

        if swing_res.bos:
            diag.state = H1H2State.INVALIDATED
            diag.h2_status = NOT_YET_QUANTIFIED_RANGE_CONTEXT
            diag.invalidation_reason = "BREAK_OF_STRUCTURE_PREVENTS_H2"
            diag.audit_trail.append(
                "[A] Break of Structure (BOS): Close broke below prior Major Swing Low; "
                "bull trend structure violated."
            )
            return diag

        # Rule 3 [A][B]: Locate the Bull Trend Peak (Swing High before the pullback).
        # IMPORTANT: the evaluation bar itself must never become the pullback anchor.
        # Otherwise an H2 signal bar that makes a new intrabar high can be promoted
        # to the tentative trend high by PriceActionSwingEngine, causing the H2 bar
        # to be interpreted as "at the peak" and suppressing its own signal.
        if (
            swing_res.tentative_high_idx is not None
            and swing_res.tentative_high_idx >= trend_start_idx
            and swing_res.tentative_high_idx < eval_idx
            and (
                swing_res.major_swing_high is None
                or swing_res.tentative_high >= swing_res.major_swing_high.price
            )
        ):
            peak_idx = swing_res.tentative_high_idx
            peak_high = swing_res.tentative_high
            diag.audit_trail.append(
                f"[A] Pullback anchor locked to active Trend High at bar {peak_idx} ({peak_high})"
            )
        elif (
            swing_res.major_swing_high is not None
            and swing_res.major_swing_high.index >= trend_start_idx
        ):
            peak_idx = swing_res.major_swing_high.index
            peak_high = swing_res.major_swing_high.price
            diag.audit_trail.append(
                f"[A] Pullback anchor locked to causal Major Swing High at bar {peak_idx} ({peak_high})"
            )
        elif (
            swing_res.recent_swing_high is not None
            and swing_res.recent_swing_high.index >= trend_start_idx
        ):
            peak_idx = swing_res.recent_swing_high.index
            peak_high = swing_res.recent_swing_high.price
            diag.audit_trail.append(
                f"[A] Pullback anchor locked to causal Recent Swing High at bar {peak_idx} ({peak_high})"
            )
        else:
            # Fallback peak must also be strictly before eval_idx.
            # The current signal bar is not allowed to define the pullback it is
            # supposed to complete.
            end_exclusive = eval_idx if eval_idx > trend_start_idx else eval_idx + 1
            highs = df["High"].iloc[trend_start_idx:end_exclusive]
            if len(highs) == 0:
                diag.state = H1H2State.NOT_YET_QUANTIFIED
                diag.h2_status = NOT_YET_QUANTIFIED
                diag.invalidation_reason = "NO_PRIOR_TREND_PEAK"
                diag.audit_trail.append("[B] No prior bar available to anchor the pullback")
                return diag
            peak_rel_idx = int(highs.argmax())
            peak_idx = trend_start_idx + peak_rel_idx
            peak_high = float(df["High"].iloc[peak_idx])

        diag.peak_index = peak_idx
        diag.peak_high = peak_high

        # Rule 4 [A]: If eval_idx is at the peak, price is making a trend high -> No pullback exists
        if peak_idx == eval_idx:
            diag.state = H1H2State.NO_SETUP
            diag.invalidation_reason = "AT_TREND_HIGH_NO_PULLBACK"
            diag.audit_trail.append(f"[A] Bar {eval_idx} is at peak ({peak_high}); no pullback underway")
            return diag

        # Rule 5 [A]: Walk forward through the pullback from peak_idx + 1 to eval_idx
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
                    diag.audit_trail.append(
                        f"[A] Bar {b}: H1 attempt reached/exceeded peak ({cur_high} >= {peak_high}); "
                        "trend resumed, no H2 possible"
                    )
                    break
                # Rule 8 [A]: Did H1 attempt continue higher below peak?
                elif cur_high > prev_high:
                    h1_high = max(h1_high, cur_high) if h1_high is not None else cur_high
                    diag.h1_high = h1_high
                    diag.audit_trail.append(f"[A] Bar {b}: H1 attempt extended higher ({cur_high})")
                # Rule 9 [A]: H1 failure is defined against the H1 attempt itself,
                # not against the immediately preceding bar. A subsequent bar whose
                # High fails to exceed H1's High means the first bullish attempt has
                # stalled/failed and the second leg may develop.
                elif h1_high is not None and cur_high <= h1_high:
                    current_state = H1H2State.FIRST_ATTEMPT_FAILED
                    diag.h1_status = "FAILED"
                    diag.pullback_state = "LEG_2_DOWN"
                    diag.leg_state = "LEG_2_DOWN"
                    leg2_low = cur_low
                    diag.audit_trail.append(
                        f"[A] Bar {b}: H1 attempt failed; High {cur_high} did not exceed H1 High {h1_high}; "
                        "Leg 2 down initiated"
                    )
                else:
                    # Inside / pause bar
                    diag.audit_trail.append(f"[A] Bar {b}: Neutral pause inside H1 attempt")

            # --- State 3: FIRST_ATTEMPT_FAILED (Leg 2 Down) ---
            elif current_state == H1H2State.FIRST_ATTEMPT_FAILED:
                leg2_low = cur_low if leg2_low is None else min(leg2_low, cur_low)

                # Rule 10 [A]: Second bar whose High > previous bar High during pullback is High 2 (H2)
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
                    diag.audit_trail.append(
                        f"[A] Bar {b}: H2 confirmed (second attempt breaking prev High {prev_high} after failed H1)"
                    )
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


class PriceActionEngine:
    """Long-only Strategy Freeze v1 Price Action engine with Al Brooks strict rules and A/B grading."""

    @classmethod
    def classify_bars(cls, df: pd.DataFrame) -> pd.DataFrame:
        required = {"Open", "High", "Low", "Close"}
        missing = required.difference(df.columns)
        if missing:
            raise ValueError(f"Missing OHLC columns: {sorted(missing)}")

        out = df.copy()
        bar_range = (out["High"] - out["Low"]).astype(float)
        safe_range = bar_range.where(bar_range > 0, np.nan)
        body = (out["Close"] - out["Open"]).abs()

        out["Body_Ratio"] = ((body / safe_range) * 100.0).round(1)
        out["Close_Pos"] = (
            ((out["Close"] - out["Low"]) / safe_range) * 100.0
        ).round(1)
        out["Bull_Bar"] = out["Close"] > out["Open"]
        out["Bear_Bar"] = out["Close"] < out["Open"]
        out["Upper_Wick"] = (
            out["High"] - out[["Open", "Close"]].max(axis=1)
        )
        out["Lower_Wick"] = (
            out[["Open", "Close"]].min(axis=1) - out["Low"]
        )
        return out

    @classmethod
    def _prepare_indicators(cls, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        ema_period = int(getattr(config, "EMA_TREND_PERIOD", getattr(config, "EMA_PERIOD", 20)))
        if ema_period <= 0:
            raise ValueError("EMA_TREND_PERIOD must be positive.")

        if "EMA_20" not in out.columns:
            out["EMA_20"] = out["Close"].ewm(
                span=ema_period, adjust=False, min_periods=ema_period
            ).mean()

        atr_period = int(getattr(config, "ATR_PERIOD", 14))
        if "ATR" not in out.columns:
            high_low = out["High"] - out["Low"]
            high_close = (out["High"] - out["Close"].shift(1)).abs()
            low_close = (out["Low"] - out["Close"].shift(1)).abs()
            tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            out["ATR"] = tr.rolling(window=atr_period, min_periods=1).mean()

        return out

    @staticmethod
    def _is_valid_ohlc_bar(row: pd.Series) -> bool:
        return bool(
            pd.notna(row["Open"])
            and pd.notna(row["High"])
            and pd.notna(row["Low"])
            and pd.notna(row["Close"])
            and row["High"] >= row["Low"]
        )

    @staticmethod
    def _derive_pullback_low(
        df: pd.DataFrame,
        h1_position: int,
        signal_position: int,
    ) -> float:
        if signal_position <= h1_position + 1:
            return float(df.iloc[h1_position]["Low"])
        return float(
            df.iloc[h1_position + 1 : signal_position + 1]["Low"].min()
        )

    @staticmethod
    def _derive_structure_low(
        df: pd.DataFrame,
        h1_position: int,
        pullback_low: float,
    ) -> float:
        if h1_position <= 0:
            return pullback_low
        return float(min(df.iloc[: h1_position + 1]["Low"].min(), pullback_low))

    @staticmethod
    def _strict_h1_h2_state(
        df: pd.DataFrame,
        signal_index: int,
        swing_res: Optional[SwingStructureResult] = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        嚴格 Al Brooks H2 順勢拉回確認與 A/B 分級評估。
        
        結構檢驗依賴 H1H2StateMachine 確定 H1/H1-Failure/H2 狀態序列，
        趨勢確立、訊號棒品質與均線距離則保留 Strategy Freeze v1 凍結邏輯。
        """
        slope_period = int(getattr(config, "TREND_EMA_SLOPE_PERIOD", 5))
        min_up_bars = int(getattr(config, "TREND_EMA_MIN_UP_BARS", 10))
        required_bars = max(slope_period, min_up_bars, 2)

        if signal_index < required_bars:
            return False, {
                "reason": "INSUFFICIENT_HISTORY",
                "trend_confirmed": False,
                "h2_status": NOT_YET_QUANTIFIED
            }

        sig = df.iloc[signal_index]
        ema = sig.get("EMA_20", np.nan)
        atr = sig.get("ATR", np.nan)

        if pd.isna(ema):
            return False, {
                "reason": NOT_YET_QUANTIFIED,
                "context": "EMA_TREND_PROXY",
                "trend_confirmed": False,
                "h2_status": NOT_YET_QUANTIFIED
            }

        # 計算由 signal_index 往回之連續 EMA 向上根數 [Frozen Strategy Rule]
        up_count = 0
        k = signal_index
        while k >= 1:
            e_curr = df.iloc[k].get("EMA_20")
            e_prev = df.iloc[k - 1].get("EMA_20")
            if pd.isna(e_curr) or pd.isna(e_prev) or float(e_curr) <= float(e_prev):
                break
            up_count += 1
            k -= 1

        cond1_slope = (up_count >= slope_period)
        cond2_length = (up_count >= min_up_bars)
        # "站上 EMA" is treated strictly: Close must be above EMA, not merely equal.
        cond3_above_ema = bool(sig["Close"] > ema)

        trend_confirmed = cond1_slope and cond2_length and cond3_above_ema

        # 若趨勢未確認，依 Section 11 標記 TRADING_RANGE / NOT_YET_QUANTIFIED
        if not trend_confirmed:
            return False, {
                "reason": NOT_YET_QUANTIFIED_RANGE_CONTEXT,
                "trend_confirmed": False,
                "h2_status": NOT_YET_QUANTIFIED_RANGE_CONTEXT,
                "up_count": up_count,
                "cond1_slope": cond1_slope,
                "cond2_length": cond2_length,
                "cond3_above_ema": cond3_above_ema,
            }

        # 呼叫 H1/H2 狀態機進行結構分析 [A][B]
        trend_start_idx = max(0, signal_index - up_count)
        diag = H1H2StateMachine.evaluate(
            df=df,
            eval_idx=signal_index,
            trend_confirmed=trend_confirmed,
            trend_start_idx=trend_start_idx,
            swing_res=swing_res,
        )

        # 訊號棒品質門檻 [Frozen Strategy Rule - NOT modified]
        bullish = bool(sig["Close"] > sig["Open"])
        body_ratio = float(sig.get("Body_Ratio", 0.0))
        close_pos = float(sig.get("Close_Pos", 0.0))
        min_body_ratio = float(getattr(config, "TREND_BAR_BODY_RATIO", 0.50)) * 100.0
        min_close_pos = float(getattr(config, "SIGNAL_BAR_MIN_CLOSE_POS", 0.65)) * 100.0

        bar_quality_met = bullish and (body_ratio >= min_body_ratio) and (close_pos >= min_close_pos)

        # 檢驗拉回長度與均線距離 [Frozen Strategy Rule]
        max_pullback_bars = int(getattr(config, "MAX_PULLBACK_BAR_LIMIT", 8))
        h1_pos = diag.h1_index
        h1_high = diag.h1_high

        bar_count = (signal_index - h1_pos) if h1_pos is not None else 0
        pullback_low = diag.pullback_low if diag.pullback_low is not None else float(sig["Low"])

        ema_atr_tolerance = float(getattr(config, "EMA_ATR_TOLERANCE", 1.0))
        # The original specification also rejects a pullback that is too shallow
        # to meaningfully test the 20 EMA. Because no numerical lower bound was
        # specified, expose it as a config parameter instead of silently inventing
        # a strategy rule. Default: 0.25 ATR.
        ema_atr_min_proximity = float(getattr(config, "EMA_ATR_MIN_PROXIMITY", 0.25))
        distance_to_ema = abs(pullback_low - ema)
        max_allowed_dist = (ema_atr_tolerance * atr) if (pd.notna(atr) and atr > 0) else float("inf")
        min_required_dist = (ema_atr_min_proximity * atr) if (pd.notna(atr) and atr > 0) else 0.0
        not_too_shallow = distance_to_ema >= min_required_dist
        not_too_deep = distance_to_ema <= max_allowed_dist
        within_ema_range = not_too_shallow and not_too_deep

        # 醞釀中判定：趨勢確立、H1 失敗或建立、回測在 20EMA 附近且尚未出現 H2 觸發
        is_forming = (
            trend_confirmed
            and (diag.state in (H1H2State.FIRST_ATTEMPT_FAILED, H1H2State.FIRST_ATTEMPT_DETECTED))
            and (bar_count <= max_pullback_bars)
            and within_ema_range
            and (diag.h2_status != "CONFIRMED")
        )

        details = {
            "setup_type": diag.setup_type,
            "h1_detected": diag.h1_detected,
            "h1_position": h1_pos,
            "h1_high": h1_high,
            "h1_status": diag.h1_status,
            "h2_detected": diag.h2_detected,
            "h2_position": diag.h2_index,
            "h2_status": diag.h2_status,
            "pullback_state": diag.pullback_state,
            "leg_state": diag.leg_state,
            "peak_position": diag.peak_index,
            "peak_high": diag.peak_high,
            "pullback_low": pullback_low,
            "bar_count": bar_count,
            "ema_distance": distance_to_ema,
            "ema_min_required_distance": min_required_dist,
            "ema_max_allowed_distance": max_allowed_dist,
            "ema_not_too_shallow": not_too_shallow,
            "ema_not_too_deep": not_too_deep,
            "trend_confirmed": True,
            "is_forming": is_forming,
            "invalidation_reason": diag.invalidation_reason,
            "audit_trail": diag.audit_trail,
        }

        # 若 H2 結構未確認，直接回傳未確認
        if diag.h2_status != "CONFIRMED":
            details["reason"] = diag.invalidation_reason or "H2_NOT_CONFIRMED"
            return False, details

        # 檢查最大拉回長度
        if bar_count > max_pullback_bars:
            details["reason"] = "PULLBACK_BAR_COUNT_EXCEEDED"
            details["is_forming"] = False
            return False, details

        # 檢查訊號棒品質 [Frozen Layer]
        if not bar_quality_met:
            details["reason"] = "SIGNAL_BAR_QUALITY_NOT_MET"
            return False, details

        # 檢查 EMA 距離 [Frozen Layer]
        if not within_ema_range:
            if not not_too_shallow:
                details["reason"] = "EMA_ATR_PROXIMITY_TOO_SHALLOW"
            else:
                details["reason"] = "EMA_ATR_PROXIMITY_TOO_DEEP"
            details["is_forming"] = False
            details["distance"] = distance_to_ema
            details["min_required"] = min_required_dist
            details["max_allowed"] = max_allowed_dist
            return False, details

        # 訊號評級判定 (A 級 vs B 級) [Frozen Layer]
        cond_a_body = body_ratio > 70.0
        cond_a_bars = bar_count <= 4
        cond_a_ema = (distance_to_ema <= 0.5 * atr) if (pd.notna(atr) and atr > 0) else True

        signal_grade = "A" if (cond_a_body and cond_a_bars and cond_a_ema) else "B"
        details["signal_grade"] = signal_grade
        details["reason"] = "H2_CONFIRMED"

        return True, details

    @staticmethod
    def _entry_price(signal_high: float) -> float:
        return float(next_tick_price(signal_high))

    @staticmethod
    def _stop_price(stop_reference: float) -> float:
        return float(previous_tick_price(stop_reference))

    @staticmethod
    def _target_price(entry: float, stop: float) -> float:
        risk = entry - stop
        if risk <= 0:
            return np.nan

        r_multiple = float(getattr(config, "R_MULTIPLE", getattr(config, "TAKE_PROFIT_RR", 2.0)))
        raw_target = entry + risk * r_multiple
        return float(round_to_tick(raw_target, "floor"))

    @staticmethod
    def _stop_models(
        signal_low: float,
        pullback_low: float,
        structure_low: float,
    ) -> Dict[str, float]:
        return {
            "SIGNAL_FAILURE": PriceActionEngine._stop_price(signal_low),
            "PULLBACK_FAILURE": PriceActionEngine._stop_price(pullback_low),
            "STRUCTURE_FAILURE": PriceActionEngine._stop_price(structure_low),
        }

    @classmethod
    def analyze_setups(cls, df: pd.DataFrame) -> pd.DataFrame:
        if not isinstance(df, pd.DataFrame):
            raise TypeError("df must be a pandas DataFrame.")

        out = cls.classify_bars(df)
        out = cls._prepare_indicators(out)

        out["Light"] = "WHITE"
        out["Signal_H2"] = False
        out["Signal_Grade"] = "NONE"
        out["Setup_Forming"] = False
        out["Progress_Stage"] = 1

        # 量化 Always In 多空狀態：收盤價 >= 20 EMA 且 20 EMA 向上為多頭 (LONG)
        ema_diff = out["EMA_20"].diff()
        out["Always_In"] = np.where(
            (out["Close"] >= out["EMA_20"]) & (ema_diff >= 0), "LONG", "SHORT"
        )

        out["Entry_Price"] = np.nan
        out["Trigger_Price"] = np.nan
        out["Order_Price"] = np.nan
        out["Fill_Price"] = np.nan

        out["Stop_Signal_Failure"] = np.nan
        out["Stop_Pullback_Failure"] = np.nan
        out["Stop_Structure_Failure"] = np.nan
        out["Stop_Loss"] = np.nan

        out["Target_Price"] = np.nan
        out["Risk_Pct"] = np.nan
        out["Net_RR"] = np.nan

        out["Suggested_Shares"] = 0
        out["H2_Status"] = NOT_YET_QUANTIFIED
        out["H2_Reason"] = ""
        out["Strategy_Valid"] = False
        out["Gap_Policy"] = getattr(config, "GAP_POLICY", "NOT_IMPLEMENTED")

        # Diagnostic columns for auditability [Section 13]
        out["Setup_Type"] = "NONE"
        out["H1_Detected"] = False
        out["H1_Index"] = np.nan
        out["H1_Status"] = "NONE"
        out["H2_Detected"] = False
        out["H2_Index"] = np.nan
        out["Pullback_State"] = "NONE"
        out["Leg_State"] = "NONE"
        out["Invalidation_Reason"] = ""

        # Price Action Swing Structure Engine v1 columns [Auditability]
        out["Swing_State"] = "TREND_PUSH_BULL"
        out["Major_Swing_High"] = np.nan
        out["Major_Swing_Low"] = np.nan
        out["BOS"] = False

        if out.empty:
            return out

        # O(N) 單次全序列評估波段結構，避免 O(N^2) 重複重算
        swing_series = PriceActionSwingEngine.evaluate_series(out)

        for i in range(1, len(out)):
            row = out.iloc[i]

            if not cls._is_valid_ohlc_bar(row):
                out.at[out.index[i], "H2_Status"] = "INVALID_BAR"
                out.at[out.index[i], "Invalidation_Reason"] = "INVALID_OHLC_BAR"
                continue

            swing_info = swing_series[i]
            confirmed, details = cls._strict_h1_h2_state(out, i, swing_res=swing_info)
            out.at[out.index[i], "H2_Status"] = details.get("h2_status", "CONFIRMED" if confirmed else "NOT_CONFIRMED")
            out.at[out.index[i], "H2_Reason"] = details.get("reason", "")
            out.at[out.index[i], "Setup_Type"] = details.get("setup_type", "NONE")
            out.at[out.index[i], "H1_Detected"] = details.get("h1_detected", False)
            h1_pos = details.get("h1_position")
            if h1_pos is not None:
                out.at[out.index[i], "H1_Index"] = h1_pos
            out.at[out.index[i], "H1_Status"] = details.get("h1_status", "NONE")
            out.at[out.index[i], "H2_Detected"] = details.get("h2_detected", False)
            h2_pos = details.get("h2_position")
            if h2_pos is not None:
                out.at[out.index[i], "H2_Index"] = h2_pos
            out.at[out.index[i], "Pullback_State"] = details.get("pullback_state", "NONE")
            out.at[out.index[i], "Leg_State"] = details.get("leg_state", "NONE")
            out.at[out.index[i], "Invalidation_Reason"] = details.get("invalidation_reason", "")

            # 記錄 Swing 結構狀態 (O(1) 讀取)
            out.at[out.index[i], "Swing_State"] = swing_info.state.value
            if swing_info.major_swing_high is not None:
                out.at[out.index[i], "Major_Swing_High"] = swing_info.major_swing_high.price
            if swing_info.major_swing_low is not None:
                out.at[out.index[i], "Major_Swing_Low"] = swing_info.major_swing_low.price
            out.at[out.index[i], "BOS"] = swing_info.bos

            # 若未確認為買訊，但符合醞釀中打底條件
            if not confirmed:
                if details.get("is_forming", False):
                    out.at[out.index[i], "Setup_Forming"] = True
                    out.at[out.index[i], "Light"] = "YELLOW"
                    out.at[out.index[i], "Progress_Stage"] = 3
                continue

            h1_position = int(details["h1_position"]) if details.get("h1_position") is not None else 0
            signal_grade = details.get("signal_grade", "B")
            signal_low = float(row["Low"])
            pullback_low = float(details.get("pullback_low", cls._derive_pullback_low(out, h1_position, i)))
            structure_low = cls._derive_structure_low(
                out, h1_position, pullback_low
            )

            stops = cls._stop_models(
                signal_low,
                pullback_low,
                structure_low,
            )

            entry = cls._entry_price(float(row["High"]))
            stop_model = getattr(config, "DEFAULT_STOP_MODEL", "SIGNAL_FAILURE")
            if stop_model not in stops:
                raise ValueError(
                    f"Unsupported DEFAULT_STOP_MODEL: {stop_model}"
                )

            selected_stop = stops[stop_model]
            risk = entry - selected_stop
            target = cls._target_price(entry, selected_stop)

            out.at[out.index[i], "Signal_H2"] = True
            out.at[out.index[i], "Signal_Grade"] = signal_grade
            out.at[out.index[i], "Strategy_Valid"] = True
            out.at[out.index[i], "Light"] = "GREEN"
            out.at[out.index[i], "Progress_Stage"] = 4
            out.at[out.index[i], "Setup_Forming"] = False

            out.at[out.index[i], "Trigger_Price"] = entry
            out.at[out.index[i], "Entry_Price"] = entry
            out.at[out.index[i], "Order_Price"] = np.nan
            out.at[out.index[i], "Fill_Price"] = np.nan

            out.at[out.index[i], "Stop_Signal_Failure"] = stops["SIGNAL_FAILURE"]
            out.at[out.index[i], "Stop_Pullback_Failure"] = stops["PULLBACK_FAILURE"]
            out.at[out.index[i], "Stop_Structure_Failure"] = stops["STRUCTURE_FAILURE"]
            out.at[out.index[i], "Stop_Loss"] = selected_stop

            out.at[out.index[i], "Target_Price"] = target
            out.at[out.index[i], "Risk_Pct"] = (
                round((risk / entry) * 100.0, 4)
                if entry > 0 and risk > 0
                else np.nan
            )
            out.at[out.index[i], "Net_RR"] = (
                float(getattr(config, "R_MULTIPLE", getattr(config, "TAKE_PROFIT_RR", 2.0)))
                if pd.notna(target) and risk > 0
                else np.nan
            )

        return out
