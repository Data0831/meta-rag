import schedule
import time
import os
import sys
from datetime import datetime

# Ensure project root is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from data.sync import run_sync
from src.tool.ANSI import print_cyan, print_yellow

# === 可自行修改執行時間點 (24小時制格式，例如 "03:00") ===
SCHEDULE_TIMES = [
    "01:00",
    "13:00",
    # "18:00", # 可自行增加或取消註解
]


def job():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print_cyan(f"\n[Scheduler] 觸發排程工作於: {now}")
    try:
        run_sync()
    except Exception as e:
        print(f"[Scheduler] 執行同步時發生錯誤: {e}")


def start_scheduler():
    if not SCHEDULE_TIMES:
        print_yellow("[Scheduler] 未設定任何執行時間。請檢查 SCHEDULE_TIMES 配置。")
        return

    print_cyan("=== Meilisearch 同步排程器已啟動 ===")
    print(f"預定執行時間: {', '.join(SCHEDULE_TIMES)}")

    # 註冊所有排程點
    for t in SCHEDULE_TIMES:
        schedule.every().day.at(t).do(job)

    try:
        while True:
            schedule.run_pending()
            # 每 30 秒檢查一次，減少 CPU 負擔
            time.sleep(30)
    except KeyboardInterrupt:
        print_cyan("\n[Scheduler] 排程器已手動停止。")


if __name__ == "__main__":
    start_scheduler()
