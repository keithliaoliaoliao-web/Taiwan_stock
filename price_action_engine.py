"""
price_action_engine.py
Strategy Freeze v1 - Al Brooks-inspired Price Action Engine
包含 H2 突破訊號判定、A/B 評級、醞釀中 (Setup Forming) 追蹤與 Always In 狀態量化。
"""

from __future__ import annotations

from typing import Optional, Dict, Any, Tuple
import numpy as np
import pandas as pd

import config
from taiwan_market_rules import (
    next_tick_price,
    previous_tick_price,
    round_to_tick,
)

NOT_YET_QUANTIFIED = "NOT_YET_QUANTIFIED"


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
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        嚴格 Al Brooks H2 順勢拉回確認與 A/B 分級評估：
        [需求一] 趨勢確立需同時滿足三條件：
          條件一：最近 TREND_EMA_SLOPE_PERIOD 根 K 棒的 EMA 每根都高於前一根
          條件二：從目前往回找，EMA 連續向上的根數 >= TREND_EMA_MIN_UP_BARS
          條件三：收盤價站上 EMA (sig["Close"] >= ema)
        """
        slope_period = int(getattr(config, "TREND_EMA_SLOPE_PERIOD", 5))
        min_up_bars = int(getattr(config, "TREND_EMA_MIN_UP_BARS", 10))
        required_bars = max(slope_period, min_up_bars, 2)

        if signal_index < required_bars:
            return False, {"reason": "INSUFFICIENT_HISTORY", "trend_confirmed": False}

        sig = df.iloc[signal_index]
        ema = sig.get("EMA_20", np.nan)
        atr = sig.get("ATR", np.nan)

        if pd.isna(ema):
            return False, {
                "reason": NOT_YET_QUANTIFIED,
                "context": "EMA_TREND_PROXY",
                "trend_confirmed": False
            }

        # 計算由 signal_index 往回之連續 EMA 向上根數
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
        cond3_above_ema = bool(sig["Close"] >= ema)

        trend_confirmed = cond1_slope and cond2_length and cond3_above_ema

        if not trend_confirmed:
            return False, {
                "reason": "TREND_CONTEXT_NOT_CONFIRMED",
                "trend_confirmed": False,
                "up_count": up_count,
                "cond1_slope": cond1_slope,
                "cond2_length": cond2_length,
                "cond3_above_ema": cond3_above_ema,
            }

        # 訊號棒品質門檻
        bullish = bool(sig["Close"] > sig["Open"])
        body_ratio = float(sig.get("Body_Ratio", 0.0))
        close_pos = float(sig.get("Close_Pos", 0.0))
        min_body_ratio = float(getattr(config, "TREND_BAR_BODY_RATIO", 0.50)) * 100.0
        min_close_pos = float(getattr(config, "SIGNAL_BAR_MIN_CLOSE_POS", 0.65)) * 100.0

        bar_quality_met = bullish and (body_ratio >= min_body_ratio) and (close_pos >= min_close_pos)

        # H2 突破確認
        prev = df.iloc[signal_index - 1]
        h2_break = bool(sig["High"] > prev["High"])

        # 尋找 H1
        max_pullback_bars = int(getattr(config, "MAX_PULLBACK_BAR_LIMIT", 8))
        h1_pos: Optional[int] = None
        h1_high: Optional[float] = None

        for j in range(signal_index - 1, 0, -1):
            prev_j = df.iloc[j - 1]
            bar_j = df.iloc[j]
            if bar_j["Close"] > bar_j["Open"] and bar_j["High"] > prev_j["High"]:
                h1_pos = j
                h1_high = float(bar_j["High"])
                break

        if h1_pos is None:
            return False, {
                "reason": "H1_NOT_ESTABLISHED",
                "trend_confirmed": True,
                "is_forming": False,
            }

        bar_count = signal_index - h1_pos
        if bar_count > max_pullback_bars:
            return False, {
                "reason": "PULLBACK_BAR_COUNT_EXCEEDED",
                "trend_confirmed": True,
                "is_forming": False,
                "h1_position": h1_pos,
                "bar_count": bar_count,
            }

        pullback_low = PriceActionEngine._derive_pullback_low(df, h1_pos, signal_index)
        ema_atr_tolerance = float(getattr(config, "EMA_ATR_TOLERANCE", 1.0))
        distance_to_ema = abs(pullback_low - ema)
        max_allowed_dist = (ema_atr_tolerance * atr) if (pd.notna(atr) and atr > 0) else float("inf")
        within_ema_range = distance_to_ema <= max_allowed_dist

        # 醞釀中判定：趨勢確認、已建立 H1、回測在 20 EMA 附近且拉回未超過極限
        is_forming = trend_confirmed and (h1_pos is not None) and (bar_count <= max_pullback_bars) and within_ema_range

        if not bar_quality_met:
            return False, {
                "reason": "SIGNAL_BAR_QUALITY_NOT_MET",
                "trend_confirmed": True,
                "is_forming": is_forming,
                "h1_position": h1_pos,
                "bar_count": bar_count,
                "pullback_low": pullback_low,
            }

        if not h2_break:
            return False, {
                "reason": "H2_TRIGGER_NOT_BROKEN",
                "trend_confirmed": True,
                "is_forming": is_forming,
                "h1_position": h1_pos,
                "bar_count": bar_count,
                "pullback_low": pullback_low,
            }

        if signal_index <= h1_pos + 1:
            return False, {
                "reason": "NO_FAILED_CONTINUATION_AFTER_H1",
                "trend_confirmed": True,
                "is_forming": is_forming,
                "h1_position": h1_pos,
            }

        intermediate = df.iloc[h1_pos + 1 : signal_index]
        h1_failed = bool((intermediate["High"] <= h1_high).any())

        if not h1_failed:
            return False, {
                "reason": "H1_CONTINUED_WITHOUT_FAILED_ATTEMPT",
                "trend_confirmed": True,
                "is_forming": is_forming,
                "h1_position": h1_pos,
                "h1_high": h1_high,
            }

        if not within_ema_range:
            return False, {
                "reason": "EMA_ATR_PROXIMITY_NOT_MET",
                "trend_confirmed": True,
                "is_forming": False,
                "pullback_low": pullback_low,
                "ema": ema,
                "distance": distance_to_ema,
                "max_allowed": max_allowed_dist,
            }

        # 訊號評級判定 (A 級 vs B 級)
        cond_a_body = body_ratio > 70.0
        cond_a_bars = bar_count <= 4
        cond_a_ema = (distance_to_ema <= 0.5 * atr) if (pd.notna(atr) and atr > 0) else True

        signal_grade = "A" if (cond_a_body and cond_a_bars and cond_a_ema) else "B"

        return True, {
            "reason": "H2_CONFIRMED",
            "signal_grade": signal_grade,
            "h1_position": h1_pos,
            "h1_high": h1_high,
            "h2_position": signal_index,
            "bar_count": bar_count,
            "pullback_low": pullback_low,
            "trend_proxy": True,
            "above_ema": True,
            "failed_continuation_after_h1": True,
            "is_forming": False,
        }

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

        if out.empty:
            return out

        for i in range(1, len(out)):
            row = out.iloc[i]

            if not cls._is_valid_ohlc_bar(row):
                out.at[out.index[i], "H2_Status"] = "INVALID_BAR"
                continue

            confirmed, details = cls._strict_h1_h2_state(out, i)
            out.at[out.index[i], "H2_Status"] = (
                "CONFIRMED" if confirmed else "NOT_CONFIRMED"
            )
            out.at[out.index[i], "H2_Reason"] = details.get("reason", "")

            # 若未確認為買訊，但符合醞釀中打底條件
            if not confirmed:
                if details.get("is_forming", False):
                    out.at[out.index[i], "Setup_Forming"] = True
                    out.at[out.index[i], "Light"] = "YELLOW"
                    out.at[out.index[i], "Progress_Stage"] = 3
                continue

            h1_position = int(details["h1_position"])
            signal_grade = details.get("signal_grade", "B")
            signal_low = float(row["Low"])
            pullback_low = cls._derive_pullback_low(out, h1_position, i)
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
