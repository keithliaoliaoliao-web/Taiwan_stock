"""
universe_updater.py
自動自台灣證券交易所 API 抓取最新臺灣50與中型100成分股，並產出 watchlist.csv
"""

import csv
import json
import os
import requests
import config

EXCLUDED_ETFS = {"0050", "0051", "0052", "0053", "0054", "0055", "0056", "006208"}
TWSE_API_URL = "https://www.twse.com.tw/rwd/zh/TAIEX/TWT49U?response=json"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def update_universe(filepath: str = None) -> bool:
    """
    抓取最新臺灣50與中型100成分股，覆蓋 watchlist.csv。
    失敗時保留既有 watchlist.csv 不覆蓋並印出警告。
    """
    if filepath is None:
        filepath = config.WATCHLIST_FILE

    print("[更新] 正在連線台灣證交所取得臺灣50與中型100成分股...")
    try:
        resp = requests.get(TWSE_API_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        raw_text = resp.text
        # 印出原始 API 回傳前 500 字（供除錯驗證）
        print(f"[API 回傳預覽] {raw_text[:500]}")
        data = resp.json()
    except Exception as e:
        print(f"[警告] 連線證交所 API 失敗: {e}。保留現有 {filepath} 不覆蓋。")
        return False

    tw50_items = []
    mid100_items = []

    try:
        # 解析證交所回傳格式
        if "tables" in data and len(data["tables"]) >= 2:
            t0 = data["tables"][0].get("data", [])
            t1 = data["tables"][1].get("data", [])
            for row in t0:
                if len(row) >= 2:
                    tw50_items.append((str(row[0]).strip(), str(row[1]).strip()))
            for row in t1:
                if len(row) >= 2:
                    mid100_items.append((str(row[0]).strip(), str(row[1]).strip()))
        elif "data1" in data and "data2" in data:
            for row in data["data1"]:
                if len(row) >= 2:
                    tw50_items.append((str(row[0]).strip(), str(row[1]).strip()))
            for row in data["data2"]:
                if len(row) >= 2:
                    mid100_items.append((str(row[0]).strip(), str(row[1]).strip()))
        elif "data" in data and isinstance(data["data"], list):
            for i, row in enumerate(data["data"]):
                if len(row) >= 2:
                    code, name = str(row[0]).strip(), str(row[1]).strip()
                    if i < 50:
                        tw50_items.append((code, name))
                    else:
                        mid100_items.append((code, name))
        else:
            raise ValueError("證交所回傳 JSON 結構不符合預期")
    except Exception as e:
        print(f"[警告] 解析證交所成分股資料失敗: {e}。保留現有 {filepath} 不覆蓋。")
        return False

    # 執行過濾：排除指定 ETF 代號、排除上櫃標的（代號含 TWO 或非純數字）
    valid_tw50 = {}
    for code, name in tw50_items:
        clean_code = code.replace(".TW", "").replace(".TWO", "")
        if clean_code in EXCLUDED_ETFS or "TWO" in code or not clean_code.isdigit():
            continue
        valid_tw50[f"{clean_code}.TW"] = name

    valid_mid100 = {}
    for code, name in mid100_items:
        clean_code = code.replace(".TW", "").replace(".TWO", "")
        if clean_code in EXCLUDED_ETFS or "TWO" in code or not clean_code.isdigit():
            continue
        if f"{clean_code}.TW" not in valid_tw50:
            valid_mid100[f"{clean_code}.TW"] = name

    total_count = len(valid_tw50) + len(valid_mid100)
    if total_count == 0:
        print(f"[警告] 抓取解析後可用標的數為 0，保留現有 {filepath} 不覆蓋。")
        return False

    try:
        with open(filepath, mode="w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["ticker", "name", "sector", "market", "basket"])
            for ticker, name in valid_tw50.items():
                writer.writerow([ticker, name, "核心權值", "TWSE", "Taiwan50"])
            for ticker, name in valid_mid100.items():
                writer.writerow([ticker, name, "中型成長", "TWSE", "Mid100"])

        print(f"[更新] 觀察池已更新，共 {total_count} 檔（台灣50: {len(valid_tw50)} 檔，中型100: {len(valid_mid100)} 檔）")
        return True
    except Exception as e:
        print(f"[警告] 寫入 {filepath} 失敗: {e}")
        return False


if __name__ == "__main__":
    update_universe()
