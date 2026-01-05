import json
import os
from datetime import datetime

# 設定輸出目錄
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
            all_additions.extend(to_add)
            
        # 收集刪除的 ID (只留 ID 字串)
        if to_delete:
            print(f"   📂 [{source_name}] 收集刪除: {len(to_delete)} 筆")
            # 提取 id 並加入清單
            ids = [chunk.get("id") for chunk in to_delete if chunk.get("id")]
            all_deletion_ids.extend(ids)

    # 3. 產生檔案 (Generate Files)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
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

    print("="*60 + "\n")