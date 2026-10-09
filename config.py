"""
config.py
台股價格行為選股系統全域參數設定檔
"""

import csv
import os

# 資料與市場設定
WATCHLIST_FILE = "watchlist.csv"
DATA_LOOKBACK_DAYS = 120
TIMEZONE = "Asia/Taipei"
BENCHMARK_TICKER = "^TWII"

# 價格行為引擎參數 (Al Brooks 規則與趨勢判定)
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

# 資金管理參數
SIGNAL_GRADE_A_AMOUNT = 15000.0
SIGNAL_GRADE_B_AMOUNT = 10000.0
MAX_CONCURRENT_POSITIONS = 3

# 篩選條件
MIN_PRICE = 15.0
MAX_PRICE = 4500.0
MIN_DAILY_TURNOVER = 200_000_000
VOLUME_MA_PERIOD = 20
MIN_AVERAGE_VOLUME_SHARES = 0
BEAR_MARKET_POLICY = "WARN"
MAX_HOLDING_DAYS = 15

# 台灣證券交易所 2026/2027 年休市日
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


def load_universe(filepath=None):
    """
    載入觀察池 metadata
    回傳字典結構: { '2330.TW': {'name': '台積電', 'sector': '半導體', 'market': 'TWSE'} }
    """
    if filepath is None:
        filepath = WATCHLIST_FILE

    metadata = {}
    if not os.path.exists(filepath):
        # 初始預設標的，防止首次執行尚未抓取清單時拋出空異常
        return {
            "2330.TW": {"name": "台積電", "sector": "半導體", "market": "TWSE"},
            "2454.TW": {"name": "聯發科", "sector": "半導體", "market": "TWSE"},
            "2317.TW": {"name": "鴻海", "sector": "其他電子", "market": "TWSE"},
        }

    try:
        with open(filepath, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ticker = row.get("ticker", "").strip()
                if not ticker:
                    continue
                if not ticker.endswith(".TW") and not ticker.endswith(".TWO"):
                    ticker = f"{ticker}.TW"
                metadata[ticker] = {
                    "name": row.get("name", ticker).strip(),
                    "sector": row.get("sector", "其他").strip(),
                    "market": row.get("market", "TWSE").strip(),
                }
    except Exception as e:
        print(f"[警告] 讀取觀察池檔案 {filepath} 失敗: {e}")

    return metadata


WATCHLIST_METADATA = load_universe()
DEFAULT_WATCHLIST = list(WATCHLIST_METADATA.keys())
