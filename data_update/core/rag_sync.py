import json
import os
from datetime import datetime
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
# 取得專案根目錄 (假設 rag_sync.py 在 core/ 或 src/ 下，往上一層找)
# 如果 rag_sync.py 就在根目錄，這行也不會報錯，依然安全
project_root = os.path.abspath(os.path.join(current_dir, ".."))

if project_root not in sys.path:
    sys.path.append(project_root)
try:
    from parser import DataParser
    from vectorPreprocessing import VectorPreProcessor
    # 這裡請確認您的 config 位置是否正確
    from src.database.vector_config import RTX_4050_6G 
except ImportError:
    print("⚠️ 模組引用失敗，將只執行存檔，跳過清洗與資料庫同步。")
    DataParser = None
    VectorPreProcessor = None

SYNC_OUTPUT_DIR = "sync_output"

def notify_rag_system(diff_reports: list):
    """
    RAG 檔案生成器
    功能：將 diff_reports 中的新增與刪除資料，分別彙整並輸出成兩個獨立的 JSON 檔案。
    
    輸出：
    1. upsert_{timestamp}.json : 包含所有需要新增的完整 Chunk 物件列表。
    2. delete_{timestamp}.json : 包含所有需要刪除的 ID 列表。
    """
    if not diff_reports:
        return

    # 1. 確保輸出目錄存在
    if not os.path.exists(SYNC_OUTPUT_DIR):
        os.makedirs(SYNC_OUTPUT_DIR)

    print("\n" + "="*60)
    print("🚀 [File Generator] 準備生成向量資料庫同步檔案...")

    parser = DataParser([], "") if DataParser else None
    # 2. 彙整所有來源的資料 (Aggregation)
    all_additions = []
    all_deletion_ids = []

    for report in diff_reports:
        source_name = report["source"]
        to_add = report["added"]
        to_delete = report["deleted"]
        
        # 收集新增的 Chunk (完整的物件)
        if to_add:
            print(f"   📂 [{source_name}] 收集新增: {len(to_add)} 筆")
            for chunk in to_add:
                if parser:
                    chunk = parser.process_item(chunk)
                all_additions.append(chunk)
            
        # 收集刪除的 ID (只留 ID 字串)
        if to_delete:
            print(f"   📂 [{source_name}] 收集刪除: {len(to_delete)} 筆")
            # 提取 id 並加入清單
            ids = [chunk.get("id") for chunk in to_delete if chunk.get("id")]
            all_deletion_ids.extend(ids)

    # 3. 產生檔案 (Generate Files)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    upsert_filename = None
    delete_filename = None
    # --- 檔案 A: 新增/更新清單 (Upsert List) ---
    if all_additions:
        upsert_filename = os.path.join(SYNC_OUTPUT_DIR, f"upsert_{timestamp}.json")
        with open(upsert_filename, "w", encoding="utf-8") as f:
            json.dump(all_additions, f, ensure_ascii=False, indent=4)
        print(f"   ✅ [產出] 新增清單已建立: {upsert_filename} (共 {len(all_additions)} 筆)")
    else:
        print("   💤 本次無新增資料。")

    # --- 檔案 B: 刪除清單 (Delete List) ---
    if all_deletion_ids:
        delete_filename = os.path.join(SYNC_OUTPUT_DIR, f"delete_{timestamp}.json")
        with open(delete_filename, "w", encoding="utf-8") as f:
            # 格式: ["id1", "id2", "id3"]
            json.dump(all_deletion_ids, f, ensure_ascii=False, indent=4)
        print(f"   ✅ [產出] 刪除清單已建立: {delete_filename} (共 {len(all_deletion_ids)} 筆)")
    else:
        print("   💤 本次無刪除資料。")

    if VectorPreProcessor and (upsert_filename or delete_filename):
        print("\n⚡ [Auto Sync] 呼叫向量處理器...")
        try:
            # 這裡使用 RTX_4050_6G，請依實際硬體調整
            processor = VectorPreProcessor(
                index_name="announcements", 
                **RTX_4050_6G 
            )
            processor.run_dynamic_sync(
                upsert_path=upsert_filename,
                delete_path=delete_filename
            )
            print("✨ [Auto Sync] 資料庫同步完成！")
        except Exception as e:
            print(f"❌ [Auto Sync Error] 同步失敗: {e}")
            import traceback
            traceback.print_exc()

    print("="*60 + "\n")