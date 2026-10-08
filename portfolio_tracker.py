# -*- coding: utf-8 -*-
"""
持倉追蹤與損益評估模組 (portfolio_tracker.py)

讀取 holdings.json，追蹤個人持股狀態，以「股數」(shares) 為計算基準。
計算未實現損益與持有天數，並根據台股交易與風控規則判定狀態：
- STOP_LOSS：當前收盤 <= 停損價
- TAKE_PROFIT：當前收盤 >= 目標價
- NEAR_STOP：當前收盤距停損價 < 5%
- TIME_EXIT：持有天數 > MAX_HOLDING_DAYS (預設15天)
- HOLD：正常持有中
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
import pytz

import config


def load_holdings(filepath: str = "holdings.json") -> List[Dict[str, Any]]:
    """
    從 JSON 檔案載入持倉清單
    """
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, mode="r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            return []
    except Exception as e:
        print(f"[警告] 讀取持倉檔 {filepath} 失敗: {e}，回傳空清單")
        return []


def save_holdings(holdings: List[Dict[str, Any]], filepath: str = "holdings.json") -> bool:
    """
    將持倉清單寫回 JSON 檔案
    """
    try:
        with open(filepath, mode="w", encoding="utf-8") as f:
            json.dump(holdings, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[錯誤] 儲存持倉至 {filepath} 失敗: {e}")
        return False


def evaluate_holdings(
    current_prices: Dict[str, float],
    holdings_path: str = "holdings.json",
    current_date_str: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    評估所有持倉的最新狀態與損益
    """
    holdings = load_holdings(holdings_path)
    if not holdings:
        return []
        
    tz = pytz.timezone(config.TIMEZONE)
    if current_date_str:
        try:
            today_dt = datetime.strptime(current_date_str, "%Y-%m-%d")
        except ValueError:
            today_dt = datetime.now(tz)
    else:
        today_dt = datetime.now(tz)
        
    evaluated_list: List[Dict[str, Any]] = []
    
    for item in holdings:
        ticker = item.get("ticker", "").strip()
        name = item.get("name", ticker).strip()
        grade = item.get("grade", "B").strip()
        entry_price = float(item.get("entry_price", 0.0))
        entry_date_str = item.get("entry_date", today_dt.strftime("%Y-%m-%d")).strip()
        shares = int(item.get("shares", 0))
        stop_loss = float(item.get("stop_loss", 0.0))
        target_price = float(item.get("target_price", 0.0))
        
        current_close = float(current_prices.get(ticker, entry_price))
        
        unrealized_pnl = round((current_close - entry_price) * shares, 2)
        unrealized_pct = round(((current_close - entry_price) / entry_price) * 100, 2) if entry_price > 0 else 0.0
        
        try:
            entry_dt = datetime.strptime(entry_date_str, "%Y-%m-%d")
            holding_days = max(0, (today_dt.date() - entry_dt.date()).days)
        except Exception:
            holding_days = 0
            
        status = "HOLD"
        action_desc = "正常持有，距停損尚有空間"
        
        if stop_loss > 0 and current_close <= stop_loss:
            status = "STOP_LOSS"
            action_desc = "跌破停損價，觸發停損出場"
        elif target_price > 0 and current_close >= target_price:
            status = "TAKE_PROFIT"
            action_desc = "已達目標價，建議獲利了結"
        elif stop_loss > 0 and ((current_close - stop_loss) / stop_loss < 0.05):
            status = "NEAR_STOP"
            action_desc = "距離停損小於 5%，請密切注意防守"
        elif holding_days > config.MAX_HOLDING_DAYS:
            status = "TIME_EXIT"
            action_desc = f"持倉已達 {holding_days} 天，超過 {config.MAX_HOLDING_DAYS} 天上限，建議時間停損"
        else:
            status = "HOLD"
            action_desc = "正常持有，距停損尚有空間"
            
        record = {
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
            "action_desc": action_desc
        }
        evaluated_list.append(record)
        
    return evaluated_list
