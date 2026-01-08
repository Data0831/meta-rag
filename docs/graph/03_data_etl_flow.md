# 資料預處理與同步流程 (Data ETL Pipeline)

本圖表描述資料從「原始網站」獲取、清洗、差異偵測，直到「向量化」並寫入 Meilisearch 的完整自動化路徑。

```mermaid
sequenceDiagram
    participant Web as Microsoft Sites
    participant CRAW as crawlers/*.py
    participant SCHED as main_scheduler.py
    participant DIFF as diff_engine.py
    participant SYNC as rag_sync.py
    participant PS as parser.py
    participant VP as vectorPreprocessing.py
    participant DB as Meilisearch

    Note over Web,CRAW: 1. 爬蟲階段 (Crawling)
    loop 定期排程執行
        CRAW->>Web: 抓取 HTML / JSON 原始資料
        Web-->>CRAW: 回傳產品公告原始內容
    end

    Note over CRAW,SCHED: 2. 差異偵測與熔斷 (Diff & Circuit Breaker)
    CRAW->>SCHED: 傳回本次抓取的 Raw Chunks (List)
    SCHED->>DIFF: process_diff_and_save (與本地舊資料比對)
    
    alt 刪除筆數 > 33% 總量
        DIFF-->>SCHED: 觸發熔斷 (Circuit Breaker Triggered)
        Note over SCHED: 停止更新，發出警告日誌以防止誤刪
    else 比對通過
        DIFF-->>SCHED: 回傳新增 (Added) 與 刪除 (Deleted) 列表
    end

    Note over SCHED,SYNC: 3. 資料彙整與清洗 (Data Cleaning)
    SCHED->>SYNC: notify_rag_system(valid_diff_reports)
    
    loop 每一筆新增文檔
        SYNC->>PS: process_item(chunk)
        PS->>PS: HTML 轉 Markdown、移除雜訊、<br/>計算 Token、產生 Hash ID
    end
    
    SYNC->>SYNC: 產出動態同步檔 (upsert_*.json, delete_*.json)

    Note over SYNC,VP: 4. 向量生成與資料庫寫入 (Vectorization & Indexing)
    SYNC->>VP: run_dynamic_sync (動態感知同步)
    
    rect rgb(240, 248, 255)
        Note over VP: 根據硬體 Profile 自動調整並發：<br/>- RTX 4050 (GPU 加速)<br/>- 16C CPU (多執行緒)<br/>- 2C4T (低能耗模式)
        
        VP->>VP: 批次生成向量 (Batch Embedding)
        VP->>DB: upsert_documents / delete_documents
    end

    Note over DB: 資料同步完成，可用於檢索
```

## 核心組件說明

| 組件 | 職責 |
| :--- | :--- |
| **Crawlers** | 針對不同來源（Azure, M365, Partner Center）的客製化抓取邏輯。 |
| **Diff Engine** | 核心穩定性偵測，確保系統不會因爬蟲失效而清空現有資料（熔斷機制）。 |
| **Data Parser** | 清理廣告、社群連結與樣板代碼，並將長度標準化，是 RAG 品質的關鍵。 |
| **Vector Processor** | 實現「硬體感知」的非同步向量生成，在不同運算資源下都能快速重建索引。 |
