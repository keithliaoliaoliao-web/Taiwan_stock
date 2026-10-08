# -*- coding: utf-8 -*-
"""
系統全域設定檔 (config.py)

定義資料來源、技術指標參數、資金控管門檻、篩選規則、台灣證交所休市日清單，
並提供觀察池 (watchlist.csv) 讀取機制。
"""

import os
import csv
from typing import Dict, Any

# ==========================================
# 1. 資料設定
# ==========================================
WATCHLIST_FILE = "watchlist.csv"
DATA_LOOKBACK_DAYS = 120
TIMEZONE = "Asia/Taipei"
BENCHMARK_TICKER = "^TWII"

# ==========================================
# 2. 價格行為引擎參數
# ==========================================
EMA_PERIOD = 20
EMA_TREND_PERIOD = 20
ATR_PERIOD = 14
EMA_ATR_TOLERANCE = 1.0
MAX_PULLBACK_BAR_LIMIT = 8
TREND_EMA_SLOPE_PERIOD = 5
TREND_EMA_MIN_UP_BARS = 10
TREND_BAR_BODY_RATIO = 0.50
SIGNAL_BAR_MIN_CLOSE_POS = 0.65
DEFAULT_STOP_MODEL = "SIGNAL_FAILURE"
R_MULTIPLE = 2.0
TAKE_PROFIT_RR = 2.0
GAP_POLICY = "NOT_IMPLEMENTED"

# ==========================================
# 3. 資金管理
# ==========================================
SIGNAL_GRADE_A_AMOUNT = 15000.0
SIGNAL_GRADE_B_AMOUNT = 10000.0
MAX_CONCURRENT_POSITIONS = 3

# ==========================================
# 4. 篩選條件
# ==========================================
MIN_PRICE = 15.0
MAX_PRICE = 4500.0
MIN_DAILY_TURNOVER = 200_000_000
VOLUME_MA_PERIOD = 20
MIN_AVERAGE_VOLUME_SHARES = 0
BEAR_MARKET_POLICY = "WARN"
MAX_HOLDING_DAYS = 15

# ==========================================
# 5. 台灣證券交易所休市日清單
# ==========================================
TWSE_HOLIDAYS_2026 = [
    "2026-01-01", "2026-02-13", "2026-02-16", "2026-02-17",
    "2026-02-18", "2026-02-19", "2026-02-20", "2026-02-27",
    "2026-04-03", "2026-04-06", "2026-05-01", "2026-06-19",
    "2026-09-25", "2026-10-09",
]
TWSE_HOLIDAYS_2027 = [
    "2027-01-01", "2027-02-02", "2027-02-03", "2027-02-04",
    "2027-02-05", "2027-02-08", "2027-02-09", "2027-02-10",
    "2027-03-01", "2027-04-05", "2027-04-06", "2027-04-30",
    "2027-06-09", "2027-09-15", "2027-10-11",
]
TWSE_HOLIDAYS = set(TWSE_HOLIDAYS_2026 + TWSE_HOLIDAYS_2027)

# ==========================================
# 6. 預設備份觀察池 (冷啟動防護)
# ==========================================
DEFAULT_SEED_UNIVERSE = [
    {"ticker": "2330.TW", "name": "台積電", "sector": "半導體", "category": "台灣50"},
    {"ticker": "2317.TW", "name": "鴻海", "sector": "其他電子", "category": "台灣50"},
    {"ticker": "2454.TW", "name": "聯發科", "sector": "半導體", "category": "台灣50"},
    {"ticker": "2308.TW", "name": "台達電", "sector": "電子零組件", "category": "台灣50"},
    {"ticker": "2382.TW", "name": "廣達", "sector": "電腦及週邊", "category": "台灣50"},
    {"ticker": "2881.TW", "name": "富邦金", "sector": "金融保險", "category": "台灣50"},
    {"ticker": "2882.TW", "name": "國泰金", "sector": "金融保險", "category": "台灣50"},
    {"ticker": "2412.TW", "name": "中華電", "sector": "通信網路", "category": "台灣50"},
    {"ticker": "2303.TW", "name": "聯電", "sector": "半導體", "category": "台灣50"},
    {"ticker": "3711.TW", "name": "日月光投控", "sector": "半導體", "category": "台灣50"},
    {"ticker": "2891.TW", "name": "中信金", "sector": "金融保險", "category": "台灣50"},
    {"ticker": "3231.TW", "name": "緯創", "sector": "電腦及週邊", "category": "台灣50"},
    {"ticker": "2357.TW", "name": "華碩", "sector": "電腦及週邊", "category": "台灣50"},
    {"ticker": "2603.TW", "name": "長榮", "sector": "航運業", "category": "台灣50"},
    {"ticker": "3008.TW", "name": "大立光", "sector": "光電業", "category": "台灣50"},
]


def load_universe(filepath: str = None) -> Dict[str, Dict[str, Any]]:
    """
    載入觀察池名單 (預設從 watchlist.csv 讀取)
    
    :param filepath: CSV 檔案路徑，未指定則使用 WATCHLIST_FILE
    :return: 以 ticker 為 key 的字典，包含名稱、產業與類別中繼資料
    """
    target_path = filepath or WATCHLIST_FILE
    result: Dict[str, Dict[str, Any]] = {}
    
    if os.path.exists(target_path):
        try:
            with open(target_path, mode="r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    raw_ticker = row.get("ticker") or row.get("symbol") or ""
                    raw_ticker = raw_ticker.strip()
                    if not raw_ticker:
                        continue
                    ticker = raw_ticker if "." in raw_ticker else f"{raw_ticker}.TW"
                    name = row.get("name") or row.get("stock_name") or ticker
                    sector = row.get("sector") or row.get("industry") or "其他"
                    category = row.get("category") or "觀察池"
                    result[ticker] = {
                        "ticker": ticker,
                        "name": name.strip(),
                        "sector": sector.strip(),
                        "category": category.strip(),
                    }
        except Exception as e:
            print(f"[警告] 讀取 {target_path} 失敗: {e}，改用預設種子觀察池")
    
    # 若檔案不存在或讀取結果為空，使用種子觀察池並儲存預設檔
    if not result:
        for item in DEFAULT_SEED_UNIVERSE:
            result[item["ticker"]] = item
        if not os.path.exists(target_path):
            try:
                with open(target_path, mode="w", encoding="utf-8-sig", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=["ticker", "name", "sector", "category"])
                    writer.writeheader()
                    for item in DEFAULT_SEED_UNIVERSE:
                        writer.writerow(item)
            except Exception:
                pass
                
    return result


WATCHLIST_METADATA = load_universe()
DEFAULT_WATCHLIST = list(WATCHLIST_METADATA.keys())
