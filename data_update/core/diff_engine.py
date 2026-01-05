import os
import json
import hashlib
import tiktoken
import shutil
import glob
from datetime import datetime
from typing import List, Dict, Optional, Union

# ==========================================
# ⚙️ 設定區
# ==========================================
DATA_DIR = "data"
HISTORY_DIR = os.path.join(DATA_DIR, "history")

# Token 限制 (僅作檢查用，不強制截斷，避免破壞 JSON 結構)
TOKEN_LIMIT = 1800

# 歷史備份保留份數
MAX_HISTORY_COUNT = 4

# 初始化 Token 計算器
try:
    enc = tiktoken.encoding_for_model("gpt-4o")
except:
    enc = tiktoken.get_encoding("cl100k_base")

# ==========================================
# 🛠️ 工具函式
# ==========================================

def count_tokens(text: str) -> int:
    """計算字串的 Token 數量"""
    return len(enc.encode(text))

def calculate_chunk_fingerprint(chunk: Dict) -> str:
    """
    計算指紋 (Hash ID)。
    邏輯: website + main_title + title + content
    🔥 加入 website 是為了確保跨來源 ID 的全域唯一性。
    """
    website = str(chunk.get("website", "")).strip()
    main_title = str(chunk.get("main_title", "")).strip()
    title = str(chunk.get("title", "")).strip()
    content = str(chunk.get("content", "")).strip()
    
    # 組合字串進行雜湊
    combined = f"{website}|{main_title}|{title}|{content}"
    return hashlib.md5(combined.encode('utf-8')).hexdigest()

def archive_old_file(source_name: str, file_path: str):
    """將舊的 JSON 檔移入 history 資料夾進行備份"""
    if not os.path.exists(HISTORY_DIR):
        os.makedirs(HISTORY_DIR)
        
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"{source_name}_{timestamp}.json"
    backup_path = os.path.join(HISTORY_DIR, backup_filename)
    
    try:
        shutil.move(file_path, backup_path)
    except Exception as e:
        print(f"⚠️ [DiffEngine] 備份舊檔失敗: {e}")

    # 執行輪替，刪除過舊的備份
    cleanup_history(source_name)

def cleanup_history(source_name: str):
    """清理過舊的歷史備份，只保留 MAX_HISTORY_COUNT 份"""
    pattern = os.path.join(HISTORY_DIR, f"{source_name}_*.json")
    files = glob.glob(pattern)
    # 依修改時間排序 (新的在前)
    files.sort(key=os.path.getmtime, reverse=True)
    
    if len(files) > MAX_HISTORY_COUNT:
        for f in files[MAX_HISTORY_COUNT:]:
            try:
                os.remove(f)
            except OSError:
                pass

# ==========================================
# 🚀 核心邏輯
# ==========================================

def process_diff_and_save(source_name: str, new_chunks: List[Dict]) -> Optional[Dict]:
    """
    執行 Diff 比對，並包含「個別來源熔斷機制」。
    
    Args:
        source_name: 資料來源名稱 (如 'm365_roadmap')，用於決定檔名。
        new_chunks: 爬蟲剛抓回來的最新 Chunk 列表。
        
    Returns:
        Dict: 包含 status, added, deleted 的報告。
        None: 若無變動則回傳 None。
    """
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    # 每個來源有自己的獨立檔案 (例如 data/m365_roadmap.json)
    file_path = os.path.join(DATA_DIR, f"{source_name}.json")
    
    # 1. 準備新資料 (計算 Hash 並建立 Map)
    new_chunk_map = {}
    for chunk in new_chunks:
        # Token 檢查 (僅警告)
        if count_tokens(chunk.get("content", "")) > TOKEN_LIMIT:
            print(f"\033[91m⚠️ [警告] Chunk token 過長: {chunk.get('title', 'Unknown')}\033[0m")
            
        fp = calculate_chunk_fingerprint(chunk)
        chunk["id"] = fp 
        new_chunk_map[fp] = chunk

    # 2. 讀取舊資料 (作為 Source of Truth)
    old_chunk_map = {}
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                old_data = json.load(f)
                for chunk in old_data:
                    # 即使舊檔有 id，仍重新計算以確保邏輯一致
                    fp = calculate_chunk_fingerprint(chunk)
                    chunk["id"] = fp
                    old_chunk_map[fp] = chunk
        except Exception as e:
            print(f"⚠️ [DiffEngine] 讀取舊檔失敗 ({file_path})，視為全新增: {e}")
            old_chunk_map = {}

    # 3. 集合運算找出差異
    new_hashes = set(new_chunk_map.keys())
    old_hashes = set(old_chunk_map.keys())

    added_hashes = new_hashes - old_hashes
    deleted_hashes = old_hashes - new_hashes
    
    # =========================================================
    # 🔥🔥🔥 [個別來源熔斷機制] Per-Source Circuit Breaker 🔥🔥🔥
    # =========================================================
    total_existing_count = len(old_hashes)
    deletion_count = len(deleted_hashes)

    # 觸發條件：
    # 1. 原本有資料 (total > 0)
    # 2. 刪除數量 > 5 (避免資料量極少時的誤判)
    # 3. 刪除比例 > 33.3% (1/3)
    if total_existing_count > 0 and deletion_count > 5:
        if deletion_count > (total_existing_count / 3):
            print("\n" + "!"*60)
            print(f"🛑 [熔斷警告 - {source_name}]")
            print(f"🛑 該來源原本有 {total_existing_count} 筆，本次試圖刪除 {deletion_count} 筆。")
            print(f"🛑 刪除比例 ({deletion_count/total_existing_count:.1%}) 超過 1/3 安全閥值。")
            print(f"🛡️ 系統已拒絕更新此來源。舊資料將被完整保留。")
            print("!"*60 + "\n")

            # 回傳特殊狀態，告知 Scheduler 發生了什麼事
            return {
                "source": source_name,
                "status": "CIRCUIT_BREAKER_TRIGGERED", # 特殊標記
                "added": [],
                "deleted": []
            }

    # 4. 若無變動
    if not added_hashes and not deleted_hashes:
        print(f"💤 {source_name} 資料無變動。")
        return None

    print(f"💾 {source_name} 偵測到變動: 新增 {len(added_hashes)} 筆, 刪除 {len(deleted_hashes)} 筆")

    # 5. 執行存檔 (只有通過檢查才會走到這一步)
    # 先備份舊檔
    if os.path.exists(file_path):
        archive_old_file(source_name, file_path)
    
    # 寫入新檔 (Source of Truth 更新)
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            # 將 map 轉回 list 存檔
            final_list = list(new_chunk_map.values())
            json.dump(final_list, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"❌ [DiffEngine] 寫入檔案失敗: {e}")
        return None

    # 6. 回傳正常報告
    return {
        "source": source_name,
        "status": "SUCCESS",
        "added": [new_chunk_map[h] for h in added_hashes],
        "deleted": [old_chunk_map[h] for h in deleted_hashes]
    }