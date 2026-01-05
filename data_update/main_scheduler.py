import os
import importlib
import pkgutil
import schedule
import time
import json
import traceback
import logging
from datetime import datetime

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
    logger.info(f"\n⏰ [排程啟動] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    active_crawlers = load_crawlers()
    
    if not active_crawlers:
        logger.warning("⚠️ 未偵測到任何有效的爬蟲模組。")
        return

    valid_diff_reports = []
    summary_logs = []

    for crawler in active_crawlers:
        source_name = getattr(crawler, 'source_name', 'Unknown')
        print(f"=== 任務啟動: {source_name} ===") 
        
        try:
            start_time = time.time()
            final_chunks = crawler.run()
            duration = time.time() - start_time
            
            # 🛡️ [防呆 1] 空資料保護
            if not final_chunks:
                msg = f"⚠️ [異常] {source_name}: 爬蟲回傳 0 筆資料 (耗時 {duration:.1f}s)。已跳過比對。"
                logger.warning(msg)
                summary_logs.append(msg)
                continue

            # 2. 執行 Diff Engine
            diff_result = process_diff_and_save(source_name, final_chunks)
            
            if diff_result:
                status = diff_result.get("status")
                add_count = len(diff_result.get("added", []))
                del_count = len(diff_result.get("deleted", []))

                # 🛡️ [防呆 2] 熔斷檢查
                if status == "CIRCUIT_BREAKER_TRIGGERED":
                    msg = f"🚫 [熔斷] {source_name}: 試圖刪除 {del_count} 筆 (超過 1/3)。更新已攔截。"
                    logger.warning(msg)
                    summary_logs.append(msg)
                    continue
                
                elif status == "SUCCESS":
                    save_audit_files(source_name, diff_result)
                    valid_diff_reports.append(diff_result)
                    msg = f"✅ [成功] {source_name}: 新增 {add_count}, 刪除 {del_count} (耗時 {duration:.1f}s)"
                    logger.info(msg)
                    summary_logs.append(msg)
            else:
                msg = f"💤 [無變動] {source_name} (耗時 {duration:.1f}s)"
                logger.info(f"    {msg}")
                summary_logs.append(msg)
                
        except Exception as e:
            error_msg = f"❌ [錯誤] {source_name}: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            summary_logs.append(error_msg)

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
    schedule.every().day.at("06:00").do(job) # 早上 6 點
    
    logger.info(f"\n⏳ 已設定每日排程：06:00 與 18:00 執行...")
    
    while True:
        try:
            schedule.run_pending()
            time.sleep(60) # 每分鐘檢查一次時間
        except KeyboardInterrupt:
            logger.info("🛑 系統已手動停止。")
            break
        except Exception as e:
            logger.error(f"❌ 排程迴圈發生致命錯誤: {e}")
            time.sleep(60)