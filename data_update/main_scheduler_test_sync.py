import os
import importlib
import pkgutil
import schedule
import time
import json
import traceback
import logging
from datetime import datetime
from config.config import TimeConfig

# ==========================================
# 📦 模組引用
# ==========================================
try:
    from crawlers.base import BaseCrawler
    from core.diff_engine import process_diff_and_save
    from core.rag_sync import notify_rag_system
except ImportError as e:
    print(f"❌ [系統錯誤] 模組引用失敗: {e}")
    exit(1)

# ==========================================
# ⚙️ 設定區
# ==========================================
UPDATE_DIR = os.path.join("data", "updates")
LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "system_monitor.log")

# ==========================================
# 📝 日誌系統設定 (Logger Setup)
# ==========================================
def setup_logger():
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)

    logger = logging.getLogger("Microsoft_QA_Scheduler")
    logger.setLevel(logging.INFO)
    
    if logger.handlers:
        return logger

    # 1. 檔案輸出
    file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
    file_formatter = logging.Formatter('%(asctime)s - [%(levelname)s] - %(message)s')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # 2. 螢幕輸出
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter('%(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    return logger

logger = setup_logger()

# ==========================================
# 🛠️ 工具函式
# ==========================================

def load_crawlers():
    crawlers = []
    package_path = "crawlers"
    if not os.path.exists(package_path): return []
    
    for _, name, _ in pkgutil.iter_modules([package_path]):
        if name == "base": continue
        try:
            module = importlib.import_module(f"{package_path}.{name}")
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and issubclass(attr, BaseCrawler) and attr is not BaseCrawler):
                    crawlers.append(attr())
        except Exception as e:
            logger.error(f"❌ [系統] 爬蟲模組 '{name}' 載入失敗: {e}")
    return crawlers

def save_audit_files(source_name, diff_result):
    if not os.path.exists(UPDATE_DIR):
        os.makedirs(UPDATE_DIR)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if diff_result.get("added"):
        filename = os.path.join(UPDATE_DIR, f"{source_name}_{timestamp}_to_add.json")
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(diff_result["added"], f, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.error(f"    ⚠️ 寫入新增紀錄失敗: {e}")

    if diff_result.get("deleted"):
        filename = os.path.join(UPDATE_DIR, f"{source_name}_{timestamp}_to_delete.json")
        try:
            ids = [chunk["id"] for chunk in diff_result["deleted"]]
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(ids, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.error(f"    ⚠️ 寫入刪除紀錄失敗: {e}")

# ==========================================
# 🚀 排程核心邏輯
# ==========================================

def job():
    logger.info(f"\n⏰ [本地同步模式啟動] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 指定要掃描的資料夾
    DATA_SOURCE_DIR = "test_sync"  # 如果您的檔案在其他地方，請修改這裡
    
    if not os.path.exists(DATA_SOURCE_DIR):
        logger.error(f"❌ 找不到資料夾: {DATA_SOURCE_DIR}")
        return

    valid_diff_reports = []
    
    # 遍歷資料夾中的所有 JSON 檔案
    for filename in os.listdir(DATA_SOURCE_DIR):
        if filename.endswith(".json"):
            file_path = os.path.join(DATA_SOURCE_DIR, filename)
            logger.info(f"📂 正在處理本地檔案: {filename}")
            
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                    # 模擬 diff_result 格式
                    # 本地同步模式我們假設全部都是 'added'
                    diff_result = {
                        "source": filename,
                        "added": data if isinstance(data, list) else [data],
                        "deleted": [],
                        "status": "SUCCESS"
                    }
                    valid_diff_reports.append(diff_result)
                    
            except Exception as e:
                logger.error(f"❌ 讀取檔案 {filename} 失敗: {e}")

    if not valid_diff_reports:
        logger.warning(f"⚠️ 在 {DATA_SOURCE_DIR} 中未找到任何可處理的 JSON 檔案。")
        return

    # --- 以下進入 RAG Sync 階段 ---

    # 3. 彙整輸出給 RAG
    if valid_diff_reports:
        logger.info(f"\n🔄 共有 {len(valid_diff_reports)} 個來源變動，開始呼叫 RAG Sync...")
        try:
            notify_rag_system(valid_diff_reports)
            logger.info("🎉 RAG Sync 完成，同步檔案已產出。")
        except Exception as e:
            logger.error(f"❌ [RAG Sync] 失敗: {e}")
    else:
        logger.info("\n💤 本次排程無有效變動，不產生 Sync 檔案。")

    logger.info("✅ 排程結束。\n" + "-"*40)

# ==========================================
# 🏁 程式入口 (修改排程時間)
# ==========================================

if __name__ == "__main__":
    logger.info("🚀 系統啟動 (日誌監控 + 熔斷保護 + 定時任務)...")
    
    logger.info("⚡ 正在執行【初次啟動】掃描任務...")
    job() 
    logger.info("✅ 初次掃描完成，轉入排程待機模式。")
    # 設定每日固定排程
    schedule.every().day.at(TimeConfig.run_time[0]).do(job) # 早上 6 點
    
    logger.info(f"\n⏳ 已設定每日排程：{TimeConfig.run_time[0]} 執行...")
    
    while True:
        try:
            schedule.run_pending()
            time.sleep(TimeConfig.loop_time) # 每分鐘檢查一次時間
        except KeyboardInterrupt:
            logger.info("🛑 系統已手動停止。")
            break
        except Exception as e:
            logger.error(f"❌ 排程迴圈發生致命錯誤: {e}")
            time.sleep(60)