"""generate_file_hashes.py - 重新產生 file_hashes.txt (核心檔案 MD5)"""
import hashlib
import os

CORE_FILES = [
    "audit_diagnostics.py",
    "config.py",
    "data_fetcher.py",
    "price_action_engine.py",
    "price_action_scanner.py",
    "requirements.txt",
    "run_task_k.py",
    "scanner.py",
    "taiwan_market_rules.py",
    "test_cross_day_live.py",
    "test_split_handling.py",
    "universe_updater.py",
    "watchlist.csv",
]


def md5_file(path: str) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def main():
    lines = []
    for name in CORE_FILES:
        if not os.path.exists(name):
            print(f"[skip] {name} (不存在)")
            continue
        lines.append(f"{md5_file(name)}  {name}")
    with open("file_hashes.txt", "w", encoding="utf-8-sig") as f:
        f.write("\n".join(lines) + "\n")
    print("已更新 file_hashes.txt")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
