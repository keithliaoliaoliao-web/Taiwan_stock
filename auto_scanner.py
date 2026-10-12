import time
import subprocess
import sys
from datetime import datetime, timedelta, time as dtime
import pytz

TW_TZ = pytz.timezone('Asia/Taipei')

def is_trading_time(dt):
    # 週一為 0，週五為 4
    if dt.weekday() > 4:
        return False
    t = dt.time()
    return dtime(9, 0) <= t <= dtime(13, 30)

def main():
    print("=== 台股自動排程掃描器已啟動（含 Git 自動同步） ===")
    while True:
        now = datetime.now(TW_TZ)
        if is_trading_time(now):
            print(f"\n[自動排程] 開始執行選股掃描... 當前時間: {now.strftime('%Y-%m-%d %H:%M:%S')}")
            try:
                subprocess.run([sys.executable, 'scanner.py'], check=True)
                complete_time = datetime.now(TW_TZ)
                next_time = complete_time + timedelta(minutes=30)
                print(f"【本次掃描完成】：{complete_time.strftime('%H:%M:%S')}")
                print(f"【下次掃描時間】：{next_time.strftime('%H:%M:%S')}")

                # 自動同步至 GitHub
                print("[Git] 正在執行自動 Git 同步...")
                subprocess.run(['git', 'add', 'public/scan_result.json'], check=True)
                commit_msg = f"Auto-update scan results: {complete_time.strftime('%Y-%m-%d %H:%M:%S')}"
                commit_res = subprocess.run(['git', 'commit', '-m', commit_msg], capture_output=True, text=True)
                if commit_res.returncode == 0:
                    print("[Git] Commit 成功")
                    push_res = subprocess.run(['git', 'push'], capture_output=True, text=True)
                    if push_res.returncode == 0:
                        print("[Git] Push 至 GitHub 成功！")
                    else:
                        print(f"[Git] Push 失敗: {push_res.stderr.strip()}")
                else:
                    print("[Git] 無新資料變更，略過 Commit/Push")

            except Exception as e:
                print(f"[錯誤] 掃描或 Git 同步執行失敗: {e}")
            
            # 掃描完成後暫停 30 分鐘
            time.sleep(1800)
        else:
            print(f"[休眠] 目前非台股開盤時間 (週一～週五 09:00-13:30)。目前時間: {now.strftime('%Y-%m-%d %H:%M:%S')}。等待 5 分鐘後重新檢查...")
            time.sleep(300)

if __name__ == '__main__':
    main()
