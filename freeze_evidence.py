"""freeze_evidence.py - 凍結可重現證據

產生版本 hash、資料快照、交易日誌的可重現證據包。
"""
import hashlib
import json
import os
import subprocess
import time
from datetime import datetime

EVIDENCE_DIR = "evidence_freeze"
os.makedirs(EVIDENCE_DIR, exist_ok=True)

def md5_file(path):
    if not os.path.exists(path):
        return None
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest().upper()

# 1. 版本 hash
version_info = {
    "timestamp": datetime.now().isoformat(),
    "git_commit": None,
    "git_branch": None,
    "file_hashes": {},
}
try:
    version_info["git_commit"] = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
    ).strip()
    version_info["git_branch"] = subprocess.check_output(
        ["git", "branch", "--show-current"], text=True, stderr=subprocess.DEVNULL
    ).strip()
except Exception:
    pass

core_files = ["scanner.py", "price_action_engine.py", "price_action_scanner.py",
              "backtest.py", "config.py", "data_fetcher.py", "taiwan_market_rules.py"]
for f in core_files:
    h = md5_file(f)
    if h:
        version_info["file_hashes"][f] = h

with open(os.path.join(EVIDENCE_DIR, "version_info.json"), "w", encoding="utf-8") as f:
    json.dump(version_info, f, indent=2, ensure_ascii=False)

# 2. config hash
config_hash = md5_file("config.py")
with open(os.path.join(EVIDENCE_DIR, "config_hash.txt"), "w", encoding="utf-8") as f:
    f.write(f"config.py MD5: {config_hash}\n")

# 3. 複製交易日誌
import shutil
for logfile in ["bt_bom_final4.csv", "bt_bom_c3.csv", "bt_bom_nodiv.csv"]:
    if os.path.exists(logfile):
        shutil.copy2(logfile, os.path.join(EVIDENCE_DIR, logfile))

# 4. 複製 scan_result.json
for sf in ["scan_result.json", "public/scan_result.json"]:
    if os.path.exists(sf):
        shutil.copy2(sf, os.path.join(EVIDENCE_DIR, os.path.basename(sf)))

# 5. 產生 README
readme = (
    "# 凍結證據包 (Frozen Evidence)\n\n"
    "產生時間: " + datetime.now().isoformat() + "\n"
    "Git commit: " + str(version_info["git_commit"]) + "\n"
    "Git branch: " + str(version_info["git_branch"]) + "\n\n"
    "## 檔案說明\n"
    "- version_info.json: 程式版本與檔案 hash\n"
    "- config_hash.txt: config.py 的 MD5\n"
    "- bt_bom_*.csv: 回測交易日誌\n"
    "- scan_result.json: 最新掃描結果\n\n"
    "## 版本標記\n"
    "本版本應稱為「執行層主要偏差已修復的開發版」，而非「完整驗證版」。\n"
    "- 已修復: C1 (look-ahead), C2 (MTF 失效), C4 (gap-through-stop + limit-down)\n"
    "- 部分修復: C3 (股利調整，分割資料有限)\n"
    "- 未修復: C4 完整版 (連續跌停), 過擬合, Walk-forward\n\n"
    "## 回測結果 (BOM, 150 檔, 2024-2026, 10 倉位)\n"
    "- 交易數: 526\n"
    "- 勝率: 25.67%\n"
    "- 期望值: +0.551R\n"
    "- 盈虧比 (PF): 1.736\n"
    "- 總 R: +290R\n"
    "- 最大回撤: -104R (已平倉交易序列回撤，非 MTM 權益回撤)\n"
)

with open(os.path.join(EVIDENCE_DIR, "README.md"), "w", encoding="utf-8") as f:
    f.write(readme)

print("Evidence package created in:", EVIDENCE_DIR)
print("Files:", os.listdir(EVIDENCE_DIR))