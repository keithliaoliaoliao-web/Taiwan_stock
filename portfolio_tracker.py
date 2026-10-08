"""
portfolio_tracker.py
個人持股監控與狀態評估模組
"""

from datetime import datetime
import json
import os
from typing import Any, Dict, List
import config

HOLDINGS_FILE = "holdings.json"


def load_holdings(filepath: str = HOLDINGS_FILE) -> List[Dict[str, Any]]:
    """讀取 holdings.json"""
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
    except Exception as e:
        print(f"[警告] 讀取 {filepath} 失敗: {e}")
    return []


def evaluate_holdings(current_prices: Dict[str, float], holdings_filepath: str = HOLDINGS_FILE) -> List[Dict[str, Any]]:
    """
    計算每檔持股的未實現損益與監控狀態
    計算公式：
      未實現損益 = (當前收盤 - 買進價) * 股數
    狀態判斷順序：
      1. STOP_LOSS: 當前收盤 <= 停損價
      2. TAKE_PROFIT: 當前收盤 >= 目標價
      3. NEAR_STOP: 當前收盤距停損價 < 5%
      4. TIME_EXIT: 持有天數 > MAX_HOLDING_DAYS
      5. HOLD: 正常持有
    """
    holdings = load_holdings(holdings_filepath)
    evaluated = []
    today = datetime.now().date()

    for item in holdings:
        ticker = item.get("ticker", "")
        name = item.get("name", ticker)
        grade = item.get("grade", "B")
        entry_price = float(item.get("entry_price", 0.0))
        entry_date_str = item.get("entry_date", str(today))
        shares = int(item.get("shares", 0))
        stop_loss = float(item.get("stop_loss", 0.0))
        target_price = float(item.get("target_price", 0.0))

        # 計算持有日曆天數
        try:
            entry_date = datetime.strptime(entry_date_str, "%Y-%m-%d").date()
            holding_days = (today - entry_date).days
        except Exception:
            holding_days = 0

        current_close = float(current_prices.get(ticker, entry_price))
        unrealized_pnl = round((current_close - entry_price) * shares, 2)
        unrealized_pct = (
            round(((current_close - entry_price) / entry_price) * 100.0, 2)
            if entry_price > 0
            else 0.0
        )

        status = "HOLD"
        action_desc = "正常持有，距停損尚有空間"
        dist_to_stop = (current_close - stop_loss) / current_close if current_close > 0 else 1.0

        if current_close <= stop_loss and stop_loss > 0:
            status = "STOP_LOSS"
            action_desc = f"已跌破停損價 {stop_loss}，建議立即停損出場"
        elif current_close >= target_price and target_price > 0:
            status = "TAKE_PROFIT"
            action_desc = f"已達成目標價 {target_price}，建議停利出場"
        elif dist_to_stop < 0.05 and stop_loss > 0:
            status = "NEAR_STOP"
            action_desc = f"接近停損價（距停損僅 {dist_to_stop * 100:.1f}%），請高度戒備"
        elif holding_days > config.MAX_HOLDING_DAYS:
            status = "TIME_EXIT"
            action_desc = f"持有 {holding_days} 天超過上限（{config.MAX_HOLDING_DAYS}天），建議時間出場"

        evaluated.append({
            "ticker": ticker,
            "name": name,
            "grade": grade,
            "entry_price": entry_price,
            "entry_date": entry_date_str,
            "shares": shares,
            "stop_loss": stop_loss,
            "target_price": target_price,
            "current_close": current_close,
            "unrealized_pnl": unrealized_pnl,
            "unrealized_pct": unrealized_pct,
            "status": status,
            "action_desc": action_desc,
        })

    return evaluated
