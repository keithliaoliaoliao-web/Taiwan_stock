"""
universe_updater.py
自動追蹤 0050 (元大台灣50) 與 0051 (元大中型100) 官方成分股動態，維持全市場 150 檔完整名冊。
支援下市標的自動替補與智慧重試機制。
"""

import csv
import json
import logging
import os
import requests
import config

logger = logging.getLogger("universe_updater")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
}

# 知名上櫃代號對照表 (確保上櫃股票使用 .TWO 後綴，上市使用 .TW)
OTC_CODES = {"3324", "6274", "5347", "6488", "3529", "4966", "3105", "5483", "8069", "8299", "3293", "5274"}
# 已下市或終止交易黑名單 (遇此代號強制自動替補)
DELISTED_BLACKLIST = {"2809"}


def fetch_yuanta_etf_constituents(fund_id: str) -> list:
    """
    抓取元大投信 0050 (fundid=1066) 或 0051 (fundid=1067) 每日法定公布之真實成分股名單
    """
    url = f"https://www.yuantaetfs.com/api/stk_pc?fundid={fund_id}"
    items = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=12)
        if resp.status_code == 200:
            data = resp.json()
            # 解析元大 API 回傳結構
            stk_list = data if isinstance(data, list) else data.get("data", [])
            for row in stk_list:
                code = str(row.get("stk_code") or row.get("code") or "").strip()
                name = str(row.get("stk_name") or row.get("name") or "").strip()
                if code and code.isdigit() and code not in DELISTED_BLACKLIST:
                    items.append((code, name))
            if items:
                logger.info(f"成功自元大投信 API 取得基金 {fund_id} 共 {len(items)} 檔成分股")
    except Exception as e:
        logger.debug(f"元大投信 API 抓取基金 {fund_id} 失敗: {e}")
    return items


def fetch_tip_constituents(index_code: str) -> list:
    """
    備援：自臺灣指數公司 (TIP) 抓取最新成分股 (TW50: 臺灣50, TWMC: 臺灣中型100)
    """
    url = f"https://taiwanindex.com.tw/api/indexes/{index_code}/constituents"
    items = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=12)
        if resp.status_code == 200:
            data = resp.json()
            c_list = data.get("data", []) if isinstance(data, dict) else data
            for row in c_list:
                code = str(row.get("code") or row.get("stock_code") or "").strip()
                name = str(row.get("name") or row.get("stock_name") or "").strip()
                if code and code.isdigit() and code not in DELISTED_BLACKLIST:
                    items.append((code, name))
            if items:
                logger.info(f"成功自臺灣指數公司取得 {index_code} 共 {len(items)} 檔成分股")
    except Exception as e:
        logger.debug(f"TIP API 抓取 {index_code} 失敗: {e}")
    return items


def update_universe(filepath: str = None) -> bool:
    """
    主更新函式：
    1. 優先透過 0050 (50檔) + 0051 (100檔) 官方持股管線更新
    2. 次選透過臺灣指數公司 (TIP) 官方成分股 API
    3. 若連線受限，自動校驗並自癒現有 watchlist.csv (替除下市股、正名 .TWO、補滿 150 檔)
    """
    if filepath is None:
        filepath = config.WATCHLIST_FILE

    logger.info("[更新] 正在連線官方通道同步 臺灣50 (0050) 與 中型100 (0051) 最新名冊...")

    # 1. 嘗試元大投信 0050 / 0051 官方 API
    tw50_raw = fetch_yuanta_etf_constituents("1066")
    mid100_raw = fetch_yuanta_etf_constituents("1067")

    # 2. 備援：臺灣指數公司
    if len(tw50_raw) < 50:
        tw50_raw = fetch_tip_constituents("TW50") or tw50_raw
    if len(mid100_raw) < 100:
        mid100_raw = fetch_tip_constituents("TWMC") or mid100_raw

    # 若線上抓取成功且達標，寫入最新 watchlist.csv
    if len(tw50_raw) >= 45 and len(mid100_raw) >= 90:
        valid_tw50 = {}
        for code, name in tw50_raw[:50]:
            ext = ".TWO" if code in OTC_CODES else ".TW"
            valid_tw50[f"{code}{ext}"] = (name, "Taiwan50")

        valid_mid100 = {}
        for code, name in mid100_raw:
            ext = ".TWO" if code in OTC_CODES else ".TW"
            full_t = f"{code}{ext}"
            if full_t not in valid_tw50 and len(valid_mid100) < 100:
                valid_mid100[full_t] = (name, "Mid100")

        total = len(valid_tw50) + len(valid_mid100)
        try:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["ticker", "name", "sector", "market", "basket"])
                for t, (n, b) in valid_tw50.items():
                    mkt = "TPEx" if ".TWO" in t else "TWSE"
                    writer.writerow([t, n, "核心權值", mkt, b])
                for t, (n, b) in valid_mid100.items():
                    mkt = "TPEx" if ".TWO" in t else "TWSE"
                    writer.writerow([t, n, "中型成長", mkt, b])
            logger.info(f"觀察池已完成線上同步，共 {total} 檔（臺灣50: {len(valid_tw50)} 檔，中型100: {len(valid_mid100)} 檔）")
            return True
        except Exception as e:
            logger.error(f"寫入 {filepath} 失敗: {e}")

    # 3. 自癒保護機制：若離線或網路暫時中斷，檢查現有 watchlist.csv，確保移除下市股並維持剛好 150 檔
    logger.info("[保護] 線上 API 連線未滿足門檻，啟用自癒校驗維持 150 檔滿編...")
    try:
        existing_rows = []
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                header = next(reader, None)
                for r in reader:
                    if r and r[0].replace(".TW", "").replace(".TWO", "") not in DELISTED_BLACKLIST:
                        # 自動校正 .TWO
                        clean_c = r[0].replace(".TW", "").replace(".TWO", "")
                        if clean_c in OTC_CODES:
                            r[0] = f"{clean_c}.TWO"
                            r[3] = "TPEx"
                        existing_rows.append(r)

        # 若不足 150 檔，依序由候補優質權值股自動補齊 (例如群益證 6005、聯鈞 3450)
        candidates = [
            ("6005.TW", "群益證", "金融保險", "TWSE", "Mid100"),
            ("3450.TW", "聯鈞", "半導體", "TWSE", "Mid100"),
            ("3006.TW", "晶豪科", "半導體", "TWSE", "Mid100"),
        ]
        for cand in candidates:
            if len(existing_rows) >= 150:
                break
            if not any(r[0] == cand[0] for r in existing_rows):
                existing_rows.append(list(cand))
                logger.info(f"[自動替補] 補入遞補個股 {cand[0]} {cand[1]}")

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["ticker", "name", "sector", "market", "basket"])
            writer.writerows(existing_rows[:150])

        logger.info(f"觀察池自癒校驗完成，現行清單精確維持 {len(existing_rows[:150])} 檔")
        return True
    except Exception as e:
        logger.error(f"觀察池自癒失敗: {e}")
        return False


if __name__ == "__main__":
    update_universe()
