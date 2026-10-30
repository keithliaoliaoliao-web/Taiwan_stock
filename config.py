"""
config.py
台股價格行為選股系統全域參數設定檔
(維持實盤 scanner 與策略凍結參數不變，並新增經任務 C/D/E/F 實證驗收之出場模式參數)
"""

import csv
import os

# 資料與市場設定 (實盤 scanner 預設抓取 260 日曆天 / Yahoo 2y 窗口)
WATCHLIST_FILE = "watchlist.csv"
DATA_LOOKBACK_DAYS = 260
TIMEZONE = "Asia/Taipei"
BENCHMARK_TICKER = "^TWII"

# 價格行為引擎參數 (Al Brooks 規則與趨勢判定 - 嚴格凍結)
EMA_PERIOD = 20
EMA_TREND_PERIOD = 20
ATR_PERIOD = 14
EMA_ATR_TOLERANCE = 1.0
MAX_PULLBACK_BAR_LIMIT = 8
FORMING_EMA_ATR_TOLERANCE = 1.5      # 醞釀中雷達容許度 (原 1.0 放寬至 1.5)
FORMING_MAX_PULLBACK_BARS = 10       # 醞釀中雷達最大拉回棒數 (原 8 放寬至 10)
TREND_EMA_SLOPE_PERIOD = 5
TREND_EMA_MIN_UP_BARS = 6
SWING_LOOKBACK_PERIOD = 20
MIN_LEG2_PULLBACK_BARS = 1
CLIMAX_BAR_ATR_RATIO = 2.0
GRADE_A_BAR_CLOSE_RATIO = 70.0
GRADE_A_MAX_PULLBACK_BARS = 4
GRADE_A_EMA_DISTANCE_ATR = 0.5
TREND_BAR_BODY_RATIO = 0.50
SIGNAL_BAR_MIN_CLOSE_POS = 0.65
DEFAULT_STOP_MODEL = "SIGNAL_FAILURE"
R_MULTIPLE = 2.0
TAKE_PROFIT_RR = 2.0
GAP_POLICY = "NOT_IMPLEMENTED"

# 出場模式與評級模式設定 (經任務 C/D/E/F 實證新增)
# EXIT_MODE 可選：
#   "V1" : 初始停損不變；取消 2R 停利與 15 日上限；收盤跌破當日 20EMA 時隔日開盤出場；120 日保險上限以收盤價出場 (預設，總報酬與期望值最高)
#   "V2" : 觸及 2R 時先賣出一半股數 (無條件捨去至整股)，剩餘部位依 V1 規則出場 (高勝率、低回撤穩健型)
#   "V0" : 舊基準版 (初始停損 + 2R 停利 + 15 日時間出場)
EXIT_MODE = "V1"
EMA_EXIT_MAX_HOLDING_DAYS = 120

# GRADE_A_MODE 可選：
#   "LEGACY"    : 原定義 (實體 > 70% 且 拉回 <= 4 根 且 距 EMA <= 0.5 ATR)，預設維持以確保基準測試 100% 相容
#   "OPTIMIZED" : 任務 E 實證優化定義 (實體 > 70% 且 [高空淺拉回: 拉回<=4根且距EMA>0.5ATR 或 橫盤貼線: 拉回>4根且距EMA<=0.5ATR])
GRADE_A_MODE = "LEGACY"

# Brooks MTR (Major Trend Reversal) detection
MTR_ENABLED = True
MTR_MIN_TREND_BARS = 6          # 至少 N 根同向 K 線才算趨勢
MTR_REVERSAL_BODY_RATIO = 0.5    # 反轉 K 線實體佔振幅比例
MTR_REVERSAL_CLOSE_POS = 0.33    # 反轉 K 線收盤位置 (多頭反轉: 收在高點 1/3 以下)

# Brooks Wedge detection
WEDGE_ENABLED = True
WEDGE_MIN_PUSHES = 3             # 至少 3 推
WEDGE_CONVERGENCE_RATIO = 0.85   # 後推振幅 <= 前推的此比例才算收斂

# Brooks BOM (Buy/Sell the close) strong trend bar entry
BOM_ENABLED = True
BOM_BODY_RATIO = 0.6             # 實體佔振幅比例
BOM_CLOSE_POS = 0.25             # 收盤位置 (多頭: 收在高點 25% 內)
BOM_RANGE_ATR_RATIO = 1.5        # 振幅 >= ATR 的此倍數

# Brooks Multi-timeframe (weekly trend filter)
MTF_ENABLED = True

# 資金管理參數
SIGNAL_GRADE_A_AMOUNT = 15000.0
SIGNAL_GRADE_B_AMOUNT = 10000.0
MAX_CONCURRENT_POSITIONS = 3

# 篩選條件 (流動性指標：近 20 個交易日平均日成交金額)
MIN_PRICE = 15.0
MAX_PRICE = 4500.0
TURNOVER_MA_PERIOD = 20
MIN_TURNOVER_MA = 100_000_000        # 主要測試門檻：100 百萬元 (1 億元新台幣)
MIN_TURNOVER_MA_TIERS = {
    "TIER_1": 100_000_000,          # 1 億元 (100 百萬元)
    "TIER_2": 150_000_000,          # 1.5 億元 (150 百萬元)
    "TIER_3": 200_000_000           # 2 億元 (200 百萬元)
}
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
