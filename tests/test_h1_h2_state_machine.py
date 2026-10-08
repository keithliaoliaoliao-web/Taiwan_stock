import unittest
import pandas as pd
import numpy as np

import config
from price_action_engine import (
    PriceActionSwingEngine,
    SwingType,
    SwingState,
    PriceActionEngine,
    H1H2StateMachine,
    H1H2State,
    NOT_YET_QUANTIFIED,
    NOT_YET_QUANTIFIED_RANGE_CONTEXT,
)


class TestH1H2StateMachine(unittest.TestCase):
    """
    Deterministic unit test suite for Al Brooks H1/H2 Price Action State Machine.
    Validates structural correctness without arbitrary thresholds.
    """

    def test_a_valid_bullish_h2_confirmed(self):
        """
        TEST A:
        Valid bullish trend pullback -> H1 -> H1 fails -> second bullish attempt -> H2 confirmed.
        """
        df = pd.DataFrame({
            'Open':  [100, 102, 104, 103, 102, 101.5, 102.5, 101, 100, 101],
            'High':  [102, 104, 106, 104, 103, 103.5, 102.5, 101, 100.5, 102],
            'Low':   [ 99, 101, 103, 102, 101, 101.0, 101.0,  99.5, 99.0, 100],
            'Close': [102, 104, 105, 102.5, 101.5, 103.0, 101.5, 100, 99.5, 101.8]
        })
        # Peak at bar 2 (High 106)
        # Pullback starts at bar 3 (High 104 <= 106)
        # Bar 4: High 103 <= 104 (Leg 1 down continues)
        # Bar 5: High 103.5 > 103 (H1 detected!)
        # Bar 6: High 102.5 < 103.5, Low 101.0 <= 101.0 (H1 fails! Leg 2 down starts)
        # Bar 7: High 101.0 <= 102.5, Low 99.5 < 101.0 (Leg 2 down continues)
        # Bar 8: High 100.5 <= 101.0, Low 99.0 < 99.5 (Leg 2 down continues)
        # Bar 9: High 102.0 > 100.5 (H2 confirmed!)
        diag = H1H2StateMachine.evaluate(df, eval_idx=9, trend_confirmed=True)

        self.assertEqual(diag.h2_status, "CONFIRMED")
        self.assertTrue(diag.h1_detected)
        self.assertEqual(diag.h1_index, 5)
        self.assertTrue(diag.h2_detected)
        self.assertEqual(diag.h2_index, 9)
        self.assertEqual(diag.setup_type, "H2")
        self.assertEqual(diag.state, H1H2State.H2_CONFIRMED)

    def test_b_only_one_bullish_attempt_not_confirmed(self):
        """
        TEST B:
        Bullish trend pullback -> only one bullish attempt -> H2 NOT confirmed.
        """
        df = pd.DataFrame({
            'Open':  [100, 102, 104, 103, 102, 101.5, 102.5, 101],
            'High':  [102, 104, 106, 104, 103, 103.5, 102.5, 101],
            'Low':   [ 99, 101, 103, 102, 101, 101.0, 101.0,  99.5],
            'Close': [102, 104, 105, 102.5, 101.5, 103.0, 101.5, 100]
        })
        # Peak at bar 2. H1 at bar 5. H1 fails at bar 6. Leg 2 at bar 7. No second attempt!
        diag = H1H2StateMachine.evaluate(df, eval_idx=7, trend_confirmed=True)

        self.assertNotEqual(diag.h2_status, "CONFIRMED")
        self.assertTrue(diag.h1_detected)
        self.assertFalse(diag.h2_detected)
        self.assertIsNone(diag.h2_index)
        self.assertEqual(diag.invalidation_reason, "FIRST_ATTEMPT_FAILED_NO_SECOND_ATTEMPT")

    def test_c_single_bullish_candle_cannot_become_h2(self):
        """
        TEST C:
        Single bullish candle after a pullback -> must NOT automatically become H2.
        It is strictly H1.
        """
        df = pd.DataFrame({
            'Open':  [100, 102, 105, 103, 101, 100],
            'High':  [102, 105, 107, 104, 102, 103], # Peak at bar 2 (107). Pullback bars 3, 4. H1 at bar 5.
            'Low':   [ 99, 101, 104, 102, 100, 100],
            'Close': [102, 105, 106, 102, 100.5, 102.5]
        })
        diag = H1H2StateMachine.evaluate(df, eval_idx=5, trend_confirmed=True)

        self.assertTrue(diag.h1_detected)
        self.assertEqual(diag.h1_index, 5)
        self.assertFalse(diag.h2_detected)
        self.assertEqual(diag.h2_status, "NOT_CONFIRMED")
        self.assertEqual(diag.invalidation_reason, "ONLY_FIRST_ATTEMPT_DETECTED")

    def test_d_trading_range_noise_protection(self):
        """
        TEST D:
        Sideways trading range with repeated small highs/lows -> must NOT manufacture H1/H2.
        """
        df = pd.DataFrame({
            'Open':  [100, 100.5, 100.2, 100.8, 100.3, 100.7],
            'High':  [101, 101.2, 100.9, 101.3, 101.0, 101.2],
            'Low':   [ 99.5, 99.8, 99.6, 99.7, 99.5, 99.8],
            'Close': [100.5, 100.2, 100.8, 100.3, 100.7, 100.4]
        })
        # Market in trading range / no confirmed bull trend
        diag = H1H2StateMachine.evaluate(df, eval_idx=5, trend_confirmed=False, is_trading_range=True)

        self.assertEqual(diag.h2_status, NOT_YET_QUANTIFIED_RANGE_CONTEXT)
        self.assertFalse(diag.h2_detected)
        self.assertEqual(diag.invalidation_reason, "TRADING_RANGE_CONTEXT_PREVENTS_H2")

    def test_e_h1_resumed_trend_does_not_create_h2(self):
        """
        TEST E:
        H1 occurs but successfully resumes the bullish trend (makes new high)
        -> must NOT create a second H2 from the same attempt.
        """
        df = pd.DataFrame({
            'Open':  [100, 104, 102, 101, 103, 107, 106],
            'High':  [104, 106, 103, 102, 105, 109, 107], # Peak at bar 1 (106). H1 bar 4. Bar 5 breaks to 109! Bar 6 is at 107.
            'Low':   [ 99, 103, 101, 100, 102, 106, 105],
            'Close': [104, 105, 101.5, 101, 104.5, 108.5, 106.5]
        })
        # Evaluating at bar 5 (the breakout bar above prior peak 106)
        diag_b5 = H1H2StateMachine.evaluate(df, eval_idx=5, trend_confirmed=True)
        self.assertNotEqual(diag_b5.h2_status, "CONFIRMED")
        self.assertFalse(diag_b5.h2_detected)

        # Evaluating at bar 6 (a new pullback from the new peak 109)
        diag_b6 = H1H2StateMachine.evaluate(df, eval_idx=6, trend_confirmed=True)
        self.assertNotEqual(diag_b6.h2_status, "CONFIRMED")
        self.assertFalse(diag_b6.h2_detected)
        # Ensure H1 from the previous cycle is not erroneously recycled
        self.assertNotEqual(diag_b6.h1_index, 4)

    def test_f_insufficient_history_not_yet_quantified(self):
        """
        TEST F:
        Insufficient structural information -> status must be NOT_YET_QUANTIFIED.
        """
        df = pd.DataFrame({
            'Open':  [100, 101],
            'High':  [102, 103],
            'Low':   [ 99, 100],
            'Close': [101, 102]
        })
        diag = H1H2StateMachine.evaluate(df, eval_idx=1, trend_confirmed=True)
        self.assertEqual(diag.h2_status, NOT_YET_QUANTIFIED)
        self.assertEqual(diag.invalidation_reason, "INSUFFICIENT_HISTORY")

    def test_g_analyze_setups_backward_compatibility(self):
        """
        TEST G:
        Existing Strategy Freeze v1 interfaces continue to operate with full backward compatibility.
        """
        dates = pd.date_range("2026-01-01", periods=60, freq="B")
        prices = [100.0 + i * 0.4 for i in range(60)]
        df = pd.DataFrame({
            "Open": prices,
            "High": [p + 0.6 for p in prices],
            "Low": [p - 0.4 for p in prices],
            "Close": [p + 0.3 for p in prices],
            "Volume": [1000000] * 60
        }, index=dates)

        result = PriceActionEngine.analyze_setups(df)

        # Mandatory columns for Strategy Freeze v1 and scanner.py
        expected_cols = [
            "Signal_H2", "Signal_Grade", "Setup_Forming", "Trigger_Price",
            "Stop_Loss", "Target_Price", "Risk_Pct", "Net_RR", "Always_In",
            "EMA_20", "H2_Status", "H2_Reason"
        ]
        for col in expected_cols:
            self.assertIn(col, result.columns)

        # Mandatory new diagnostic columns
        diagnostic_cols = [
            "Setup_Type", "H1_Detected", "H1_Index", "H1_Status",
            "H2_Detected", "H2_Index", "Pullback_State", "Leg_State",
            "Invalidation_Reason", "Swing_State", "Major_Swing_High",
            "Major_Swing_Low", "BOS"
        ]
        for col in diagnostic_cols:
            self.assertIn(col, result.columns)

        self.assertEqual(len(result), 60)



    def test_h_swing_causal_freeze_no_repainting(self):
        """
        TEST H:
        Swing High is only frozen upon shift in control to sellers (no future leak/repainting).
        """
        df = pd.DataFrame({
            'Open':  [100, 102, 103],
            'High':  [102, 105, 104],
            'Low':   [ 99, 101, 100],
            'Close': [102, 104, 100.5]  # Bar 2 closes < Low[1] 101
        })
        s1 = PriceActionSwingEngine.evaluate(df, 1)
        self.assertIsNone(s1.major_swing_high)
        self.assertEqual(s1.tentative_high, 105.0)
        self.assertEqual(s1.tentative_high_idx, 1)

        s2 = PriceActionSwingEngine.evaluate(df, 2)
        self.assertIsNotNone(s2.major_swing_high)
        self.assertEqual(s2.major_swing_high.index, 1)
        self.assertEqual(s2.major_swing_high.price, 105.0)
        self.assertEqual(s2.major_swing_high.confirmed_at_bar, 2)

    def test_i_swing_major_vs_minor_classification(self):
        """
        TEST I:
        EMA penetration upgrades a Swing Low to MAJOR_LOW.
        """
        df = pd.DataFrame({
            'Open':   [100, 105, 102, 100, 104],
            'High':   [105, 108, 103, 101, 106],
            'Low':    [ 99, 104, 100,  99, 100],
            'Close':  [105, 107, 100, 101, 105],
            'EMA_20': [100, 101, 102, 102, 102]
        })
        s = PriceActionSwingEngine.evaluate(df, 4)
        self.assertIsNotNone(s.major_swing_low)
        self.assertEqual(s.major_swing_low.index, 3)
        self.assertEqual(s.major_swing_low.price, 99.0)
        self.assertEqual(s.major_swing_low.swing_type, SwingType.MAJOR_LOW)

    def test_j_swing_inside_bar_congestion_absorption(self):
        """
        TEST J:
        Inside bar enters ABSORPTION state without generating false swings or resetting extremes.
        """
        df = pd.DataFrame({
            'Open':  [100, 105, 103],
            'High':  [105, 108, 106],  # Bar 2 is inside bar
            'Low':   [ 99, 102, 103],
            'Close': [105, 107, 105]
        })
        s = PriceActionSwingEngine.evaluate(df, 2)
        self.assertEqual(s.state, SwingState.ABSORPTION_BULL)
        self.assertIsNone(s.major_swing_high)
        self.assertEqual(s.tentative_high, 108.0)

    def test_k_swing_break_of_structure_bos(self):
        """
        TEST K:
        Close below prior confirmed Major Swing Low triggers BOS=True and suppresses H2.
        """
        df = pd.DataFrame({
            'Open':   [100, 105, 102, 100, 104,  98],
            'High':   [105, 108, 103, 101, 106, 100],
            'Low':    [ 99, 104, 100,  99, 100,  95],
            'Close':  [105, 107, 100, 101, 105,  96],  # Bar 5 closes 96 < Major Low 99
            'EMA_20': [100, 101, 102, 102, 102, 102]
        })
        s = PriceActionSwingEngine.evaluate(df, 5)
        self.assertTrue(s.bos)
        diag = H1H2StateMachine.evaluate(df, 5, trend_confirmed=True)
        self.assertEqual(diag.h2_status, NOT_YET_QUANTIFIED_RANGE_CONTEXT)
        self.assertEqual(diag.invalidation_reason, 'BREAK_OF_STRUCTURE_PREVENTS_H2')


if __name__ == "__main__":
    unittest.main()
