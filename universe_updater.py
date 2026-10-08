# -*- coding: utf-8 -*-
"""
觀察池更新模組 (universe_updater.py)

優先從台灣證券交易所 (TWSE) API 抓取「台灣50」與「中型100」成分股，
過濾 ETF 與上櫃標的後，將最新清單輸出至 watchlist.csv。
若網路或 API 抓取失敗，保留現有 watchlist.csv 不覆蓋並發出警告。
"""

import os
import csv
import json
from typing import Dict, List, Tuple
import requests

import config

# ETF 排除清單
EXCLUDED_ETFS = {"0050", "0051", "0052", "0053", "0054", "0055", "0056", "006208"}

# 常用產業別對照表 (確保中繼資料完整度)
SECTOR_MAP = {
    # 半導體
    "2330": "半導體", "2454": "半導體", "2303": "半導體", "3711": "半導體",
    "3034": "半導體", "2379": "半導體", "3443": "半導體", "6415": "半導體",
    "3661": "半導體", "2408": "半導體", "2344": "半導體", "3529": "半導體",
    "6770": "半導體", "2449": "半導體", "6239": "半導體", "4966": "半導體",
    # 電腦及週邊 / 其他電子 / 電子零組件
    "2317": "其他電子", "2382": "電腦及週邊", "2357": "電腦及週邊", "3231": "電腦及週邊",
    "2308": "電子零組件", "2301": "電腦及週邊", "2395": "電腦及週邊", "4938": "電腦及週邊",
    "6669": "電腦及週邊", "3017": "電腦及週邊", "2376": "電腦及週邊", "2377": "電腦及週邊",
    "2324": "電腦及週邊", "2356": "電腦及週邊", "2353": "電腦及週邊", "3037": "電子零組件",
    "2360": "電子零組件", "3045": "電子零組件", "2327": "電子零組件", "3035": "半導體",
    # 光電業
    "3008": "光電業", "2409": "光電業", "3481": "光電業", "3653": "電子零組件",
    # 金融保險
    "2881": "金融保險", "2882": "金融保險", "2891": "金融保險", "2886": "金融保險",
    "2884": "金融保險", "2892": "金融保險", "2885": "金融保險", "2890": "金融保險",
    "2880": "金融保險", "2883": "金融保險", "2887": "金融保險", "2888": "金融保險",
    "2834": "金融保險", "5880": "金融保險", "5876": "金融保險", "2801": "金融保險",
    "2812": "金融保險", "2838": "金融保險", "2889": "金融保險",
    # 航運業
    "2603": "航運業", "2609": "航運業", "2615": "航運業", "2618": "航運業",
    "2610": "航運業", "2605": "航運業", "2637": "航運業",
    # 傳產、塑化、鋼鐵、水泥、紡織
    "1101": "水泥工業", "1102": "水泥工業", "1301": "塑膠工業", "1303": "塑膠工業",
    "1326": "塑膠工業", "6505": "油電燃氣", "2002": "鋼鐵工業", "1216": "食品工業",
    "1402": "紡織纖維", "2105": "橡膠工業", "2201": "汽車工業", "2207": "汽車工業",
    # 電機機械 / 綠能環保
    "1503": "電機機械", "1504": "電機機械", "1513": "電機機械", "1519": "電機機械",
    "2371": "電機機械", "6805": "其他", "9958": "鋼鐵工業",
    # 通信網路
    "2412": "通信網路", "3045": "通信網路", "4904": "通信網路",
}


def _fetch_twse_index_constituents(index_id: str, label: str) -> List[Tuple[str, str]]:
    """
    從台灣證交所 API 抓取特定指數成分股 (股票代號, 股票名稱)
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
    }
    
    urls = [
        f"https://www.twse.com.tw/rwd/zh/TAIEX/indexComponents?indexId={index_id}",
        f"https://www.twse.com.tw/rwd/zh/indicesReport/{index_id.lower()}i?response=json",
    ]
    
    raw_response_text = ""
    for url in urls:
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                raw_response_text = resp.text
                break
        except Exception:
            continue
            
    if not raw_response_text:
        raise ConnectionError(f"無法從 TWSE API 取得 {label} ({index_id}) 成分股資料")
        
    print(f"[除錯] 原始 API 回傳前 500 字 ({label}):\n{raw_response_text[:500]}\n")
    
    constituents: List[Tuple[str, str]] = []
    try:
        data = json.loads(raw_response_text)
        rows = data.get("data") or data.get("tables", [{}])[0].get("data") or []
        for row in rows:
            if isinstance(row, list) and len(row) >= 2:
                code = str(row[0]).strip()
                name = str(row[1]).strip()
                constituents.append((code, name))
            elif isinstance(row, dict):
                code = str(row.get("Code") or row.get("股票代號") or row.get("symbol") or "").strip()
                name = str(row.get("Name") or row.get("股票名稱") or "").strip()
                if code:
                    constituents.append((code, name or code))
    except Exception as e:
        raise ValueError(f"解析 {label} JSON 資料失敗: {e}")
        
    return constituents


def update_universe(filepath: str = None) -> bool:
    """
    執行觀察池更新主流程
    """
    target_path = filepath or config.WATCHLIST_FILE
    print(f"[開始] 更新台股觀察池名單...")
    
    tw50_stocks: List[Tuple[str, str]] = []
    tw100_stocks: List[Tuple[str, str]] = []
    
    try:
        tw50_stocks = _fetch_twse_index_constituents("TAI50", "台灣50")
    except Exception as e:
        print(f"[警告] 抓取台灣50失敗: {e}")
        
    try:
        tw100_stocks = _fetch_twse_index_constituents("TAI100", "中型100")
    except Exception as e:
        print(f"[警告] 抓取中型100失敗: {e}")
        
    if not tw50_stocks and not tw100_stocks:
        print(f"[警告] 觀察池更新失敗（無法自證交所取得有效資料），保留現有 {target_path} 不覆蓋。")
        return False
        
    universe_map: Dict[str, Dict[str, str]] = {}
    
    count_tw50 = 0
    for code, name in tw50_stocks:
        if code in EXCLUDED_ETFS or code.startswith("00"):
            continue
        ticker = f"{code}.TW"
        if "TWO" in ticker:
            continue
        sector = SECTOR_MAP.get(code, "電子工業" if code.startswith("2") or code.startswith("3") else "傳統產業")
        universe_map[ticker] = {
            "ticker": ticker,
            "name": name,
            "sector": sector,
            "category": "台灣50"
        }
        count_tw50 += 1
        
    count_tw100 = 0
    for code, name in tw100_stocks:
        if code in EXCLUDED_ETFS or code.startswith("00"):
            continue
        ticker = f"{code}.TW"
        if "TWO" in ticker:
            continue
        if ticker in universe_map:
            continue
        sector = SECTOR_MAP.get(code, "電子工業" if code.startswith("2") or code.startswith("3") else "製造業")
        universe_map[ticker] = {
            "ticker": ticker,
            "name": name,
            "sector": sector,
            "category": "中型100"
        }
        count_tw100 += 1
        
    total_count = len(universe_map)
    if total_count == 0:
        print(f"[警告] 過濾後成分股為 0，保留現有 {target_path} 不覆蓋。")
        return False
        
    try:
        with open(target_path, mode="w", encoding="utf-8-sig", newline="") as f:
            fieldnames = ["ticker", "name", "sector", "category"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for item in universe_map.values():
                writer.writerow(item)
                
        print(f"[更新] 觀察池已更新，共 {total_count} 檔（台灣50: {count_tw50} 檔，中型100: {count_tw100} 檔）")
        return True
    except Exception as e:
        print(f"[錯誤] 寫入 {target_path} 失敗: {e}，保留原檔案。")
        return False


if __name__ == "__main__":
    update_universe()
