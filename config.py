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
    {"ticker": "2886.TW", "name": "兆豐金", "sector": "金融保險", "category": "台灣50"},
    {"ticker": "2884.TW", "name": "玉山金", "sector": "金融保險", "category": "台灣50"},
    {"ticker": "2892.TW", "name": "第一金", "sector": "金融保險", "category": "台灣50"},
    {"ticker": "2885.TW", "name": "元大金", "sector": "金融保險", "category": "台灣50"},
    {"ticker": "2890.TW", "name": "永豐金", "sector": "金融保險", "category": "台灣50"},
    {"ticker": "2880.TW", "name": "華南金", "sector": "金融保險", "category": "台灣50"},
    {"ticker": "5880.TW", "name": "合庫金", "sector": "金融保險", "category": "台灣50"},
    {"ticker": "1216.TW", "name": "統一", "sector": "食品工業", "category": "台灣50"},
    {"ticker": "2002.TW", "name": "中鋼", "sector": "鋼鐵工業", "category": "台灣50"},
    {"ticker": "1301.TW", "name": "台塑", "sector": "塑膠工業", "category": "台灣50"},
    {"ticker": "1303.TW", "name": "南亞", "sector": "塑膠工業", "category": "台灣50"},
    {"ticker": "1326.TW", "name": "台化", "sector": "塑膠工業", "category": "台灣50"},
    {"ticker": "6505.TW", "name": "台塑化", "sector": "油電燃氣", "category": "台灣50"},
    {"ticker": "1101.TW", "name": "台泥", "sector": "水泥工業", "category": "台灣50"},
    {"ticker": "1102.TW", "name": "亞泥", "sector": "水泥工業", "category": "台灣50"},
    {"ticker": "2379.TW", "name": "瑞昱", "sector": "半導體", "category": "台灣50"},
    {"ticker": "3034.TW", "name": "聯詠", "sector": "半導體", "category": "台灣50"},
    {"ticker": "3045.TW", "name": "台灣大", "sector": "通信網路", "category": "台灣50"},
    {"ticker": "4904.TW", "name": "遠傳", "sector": "通信網路", "category": "台灣50"},
    {"ticker": "2327.TW", "name": "國巨", "sector": "電子零組件", "category": "台灣50"},
    {"ticker": "3037.TW", "name": "欣興", "sector": "電子零組件", "category": "台灣50"},
    {"ticker": "2395.TW", "name": "研華", "sector": "電腦及週邊", "category": "台灣50"},
    {"ticker": "6669.TW", "name": "緯穎", "sector": "電腦及週邊", "category": "台灣50"},
    {"ticker": "3661.TW", "name": "世芯-KY", "sector": "半導體", "category": "台灣50"},
    {"ticker": "2609.TW", "name": "陽明", "sector": "航運業", "category": "台灣50"},
    {"ticker": "2615.TW", "name": "萬海", "sector": "航運業", "category": "台灣50"},
    {"ticker": "2887.TW", "name": "台新金", "sector": "金融保險", "category": "台灣50"},
    {"ticker": "2883.TW", "name": "凱基金", "sector": "金融保險", "category": "台灣50"},
    {"ticker": "2801.TW", "name": "彰銀", "sector": "金融保險", "category": "台灣50"},
    {"ticker": "5876.TW", "name": "上海商銀", "sector": "金融保險", "category": "台灣50"},
    {"ticker": "2301.TW", "name": "光寶科", "sector": "電腦及週邊", "category": "台灣50"},
    {"ticker": "2409.TW", "name": "友達", "sector": "光電業", "category": "台灣50"},
    {"ticker": "3481.TW", "name": "群創", "sector": "光電業", "category": "台灣50"},
    {"ticker": "1504.TW", "name": "東元", "sector": "電機機械", "category": "台灣50"},
    {"ticker": "2207.TW", "name": "和泰車", "sector": "汽車工業", "category": "台灣50"},
    {"ticker": "1227.TW", "name": "佳格", "sector": "食品工業", "category": "中型100"},
    {"ticker": "1232.TW", "name": "大統益", "sector": "食品工業", "category": "中型100"},
    {"ticker": "1304.TW", "name": "台聚", "sector": "塑膠工業", "category": "中型100"},
    {"ticker": "1308.TW", "name": "亞聚", "sector": "塑膠工業", "category": "中型100"},
    {"ticker": "1309.TW", "name": "台達化", "sector": "塑膠工業", "category": "中型100"},
    {"ticker": "1312.TW", "name": "國喬", "sector": "塑膠工業", "category": "中型100"},
    {"ticker": "1314.TW", "name": "中石化", "sector": "塑膠工業", "category": "中型100"},
    {"ticker": "1402.TW", "name": "遠東新", "sector": "紡織纖維", "category": "中型100"},
    {"ticker": "1476.TW", "name": "儒鴻", "sector": "紡織纖維", "category": "中型100"},
    {"ticker": "1477.TW", "name": "聚陽", "sector": "紡織纖維", "category": "中型100"},
    {"ticker": "1503.TW", "name": "士電", "sector": "電機機械", "category": "中型100"},
    {"ticker": "1513.TW", "name": "中興電", "sector": "電機機械", "category": "中型100"},
    {"ticker": "1519.TW", "name": "華城", "sector": "電機機械", "category": "中型100"},
    {"ticker": "1560.TW", "name": "中砂", "sector": "電機機械", "category": "中型100"},
    {"ticker": "1590.TW", "name": "亞德客-KY", "sector": "電機機械", "category": "中型100"},
    {"ticker": "1605.TW", "name": "華新", "sector": "電器電纜", "category": "中型100"},
    {"ticker": "1707.TW", "name": "葡萄王", "sector": "生技醫療", "category": "中型100"},
    {"ticker": "1717.TW", "name": "長興", "sector": "化學工業", "category": "中型100"},
    {"ticker": "1722.TW", "name": "台肥", "sector": "化學工業", "category": "中型100"},
    {"ticker": "1723.TW", "name": "中碳", "sector": "化學工業", "category": "中型100"},
    {"ticker": "1773.TW", "name": "勝一", "sector": "化學工業", "category": "中型100"},
    {"ticker": "1795.TW", "name": "美時", "sector": "生技醫療", "category": "中型100"},
    {"ticker": "1802.TW", "name": "台玻", "sector": "玻璃陶瓷", "category": "中型100"},
    {"ticker": "2006.TW", "name": "東和鋼鐵", "sector": "鋼鐵工業", "category": "中型100"},
    {"ticker": "2014.TW", "name": "中鴻", "sector": "鋼鐵工業", "category": "中型100"},
    {"ticker": "2027.TW", "name": "大成鋼", "sector": "鋼鐵工業", "category": "中型100"},
    {"ticker": "2049.TW", "name": "上銀", "sector": "電機機械", "category": "中型100"},
    {"ticker": "2059.TW", "name": "川湖", "sector": "其他電子", "category": "中型100"},
    {"ticker": "2105.TW", "name": "正新", "sector": "橡膠工業", "category": "中型100"},
    {"ticker": "2201.TW", "name": "裕隆", "sector": "汽車工業", "category": "中型100"},
    {"ticker": "2204.TW", "name": "中華", "sector": "汽車工業", "category": "中型100"},
    {"ticker": "2324.TW", "name": "仁寶", "sector": "電腦及週邊", "category": "中型100"},
    {"ticker": "2344.TW", "name": "華邦電", "sector": "半導體", "category": "中型100"},
    {"ticker": "2353.TW", "name": "宏碁", "sector": "電腦及週邊", "category": "中型100"},
    {"ticker": "2356.TW", "name": "英業達", "sector": "電腦及週邊", "category": "中型100"},
    {"ticker": "2360.TW", "name": "致茂", "sector": "電子零組件", "category": "中型100"},
    {"ticker": "2371.TW", "name": "大同", "sector": "電機機械", "category": "中型100"},
    {"ticker": "2376.TW", "name": "技嘉", "sector": "電腦及週邊", "category": "中型100"},
    {"ticker": "2377.TW", "name": "微星", "sector": "電腦及週邊", "category": "中型100"},
    {"ticker": "2383.TW", "name": "台光電", "sector": "電子零組件", "category": "中型100"},
    {"ticker": "2385.TW", "name": "群光", "sector": "電子零組件", "category": "中型100"},
    {"ticker": "2404.TW", "name": "漢唐", "sector": "其他電子", "category": "中型100"},
    {"ticker": "2449.TW", "name": "京元電子", "sector": "半導體", "category": "中型100"},
    {"ticker": "2474.TW", "name": "可成", "sector": "其他電子", "category": "中型100"},
    {"ticker": "2501.TW", "name": "國建", "sector": "建材營造", "category": "中型100"},
    {"ticker": "2511.TW", "name": "太子", "sector": "建材營造", "category": "中型100"},
    {"ticker": "2542.TW", "name": "興富發", "sector": "建材營造", "category": "中型100"},
    {"ticker": "2548.TW", "name": "華固", "sector": "建材營造", "category": "中型100"},
    {"ticker": "2605.TW", "name": "新興", "sector": "航運業", "category": "中型100"},
    {"ticker": "2606.TW", "name": "裕民", "sector": "航運業", "category": "中型100"},
    {"ticker": "2607.TW", "name": "榮運", "sector": "航運業", "category": "中型100"},
    {"ticker": "2610.TW", "name": "華航", "sector": "航運業", "category": "中型100"},
    {"ticker": "2618.TW", "name": "長榮航", "sector": "航運業", "category": "中型100"},
    {"ticker": "2637.TW", "name": "慧洋-KY", "sector": "航運業", "category": "中型100"},
    {"ticker": "2809.TW", "name": "京城銀", "sector": "金融保險", "category": "中型100"},
    {"ticker": "2812.TW", "name": "台中銀", "sector": "金融保險", "category": "中型100"},
    {"ticker": "2834.TW", "name": "臺企銀", "sector": "金融保險", "category": "中型100"},
    {"ticker": "2838.TW", "name": "聯邦銀", "sector": "金融保險", "category": "中型100"},
    {"ticker": "2845.TW", "name": "統一證", "sector": "金融保險", "category": "中型100"},
    {"ticker": "2888.TW", "name": "新光金", "sector": "金融保險", "category": "中型100"},
    {"ticker": "2889.TW", "name": "國票金", "sector": "金融保險", "category": "中型100"},
    {"ticker": "2903.TW", "name": "遠百", "sector": "貿易百貨", "category": "中型100"},
    {"ticker": "2912.TW", "name": "統一超", "sector": "貿易百貨", "category": "中型100"},
    {"ticker": "3017.TW", "name": "奇鋐", "sector": "電腦及週邊", "category": "中型100"},
    {"ticker": "3035.TW", "name": "智原", "sector": "半導體", "category": "中型100"},
    {"ticker": "3036.TW", "name": "文曄", "sector": "電子通路", "category": "中型100"},
    {"ticker": "3042.TW", "name": "晶技", "sector": "電子零組件", "category": "中型100"},
    {"ticker": "3044.TW", "name": "健鼎", "sector": "電子零組件", "category": "中型100"},
    {"ticker": "3443.TW", "name": "創意", "sector": "半導體", "category": "中型100"},
    {"ticker": "3529.TW", "name": "力旺", "sector": "半導體", "category": "中型100"},
    {"ticker": "3532.TW", "name": "台勝科", "sector": "半導體", "category": "中型100"},
    {"ticker": "3653.TW", "name": "健策", "sector": "電子零組件", "category": "中型100"},
    {"ticker": "3702.TW", "name": "大聯大", "sector": "電子通路", "category": "中型100"},
    {"ticker": "3706.TW", "name": "神達", "sector": "電腦及週邊", "category": "中型100"},
    {"ticker": "4919.TW", "name": "新唐", "sector": "半導體", "category": "中型100"},
    {"ticker": "4938.TW", "name": "和碩", "sector": "電腦及週邊", "category": "中型100"},
    {"ticker": "4958.TW", "name": "臻鼎-KY", "sector": "電子零組件", "category": "中型100"},
    {"ticker": "4966.TW", "name": "譜瑞-KY", "sector": "半導體", "category": "中型100"},
    {"ticker": "5469.TW", "name": "瀚宇博", "sector": "電子零組件", "category": "中型100"},
    {"ticker": "6176.TW", "name": "瑞儀", "sector": "光電業", "category": "中型100"},
    {"ticker": "6213.TW", "name": "聯茂", "sector": "電子零組件", "category": "中型100"},
    {"ticker": "6239.TW", "name": "力成", "sector": "半導體", "category": "中型100"},
    {"ticker": "6271.TW", "name": "同欣電", "sector": "半導體", "category": "中型100"},
    {"ticker": "6285.TW", "name": "啟碁", "sector": "通信網路", "category": "中型100"},
    {"ticker": "6409.TW", "name": "旭隼", "sector": "其他電子", "category": "中型100"},
    {"ticker": "6415.TW", "name": "矽力*-KY", "sector": "半導體", "category": "中型100"},
    {"ticker": "6770.TW", "name": "力積電", "sector": "半導體", "category": "中型100"},
    {"ticker": "6805.TW", "name": "富世達", "sector": "其他電子", "category": "中型100"},
    {"ticker": "8046.TW", "name": "南電", "sector": "電子零組件", "category": "中型100"},
    {"ticker": "8454.TW", "name": "富邦媒", "sector": "貿易百貨", "category": "中型100"},
    {"ticker": "9904.TW", "name": "寶成", "sector": "其他", "category": "中型100"},
    {"ticker": "9910.TW", "name": "豐泰", "sector": "其他", "category": "中型100"},
    {"ticker": "9914.TW", "name": "美利達", "sector": "其他", "category": "中型100"},
    {"ticker": "9917.TW", "name": "中保科", "sector": "其他", "category": "中型100"},
    {"ticker": "9921.TW", "name": "巨大", "sector": "其他", "category": "中型100"},
    {"ticker": "9933.TW", "name": "中鼎", "sector": "其他", "category": "中型100"},
    {"ticker": "9941.TW", "name": "裕融", "sector": "其他", "category": "中型100"},
    {"ticker": "9945.TW", "name": "潤泰新", "sector": "其他", "category": "中型100"},
    {"ticker": "9958.TW", "name": "世紀鋼", "sector": "鋼鐵工業", "category": "中型100"},
    {"ticker": "2354.TW", "name": "鴻準", "sector": "其他電子", "category": "中型100"},
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
