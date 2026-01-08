sequenceDiagram
    autonumber
    
    participant Web as Data Sources<br/>(Microsoft Sites)
    participant CRAW as Crawlers<br/>(crawlers/*.py)
    participant SCHED as Scheduler<br/>(main_scheduler.py)
    participant DIFF as Diff Engine<br/>(diff_engine.py)
    participant SYNC as RAG Syncer<br/>(rag_sync.py)
    participant PS as Data Parser<br/>(parser.py)
    participant VP as Vector Processor<br/>(vectorPreprocessing.py)
    participant DB as Meilisearch DB<br/>(Meilisearch)

    rect rgb(255, 250, 240)
        Note over Web,CRAW: 階段一：自動化數據抓取 (Data Acquisition)
        loop 定期排程任務 (Scheduled Jobs)
            CRAW->>Web: 抓取 HTML / JSON 原始數據
            Web-->>CRAW: 返回產品公告與技術內容
        end
    end

    rect rgb(245, 250, 255)
        Note over CRAW,SCHED: 階段二：穩定性偵測與熔斷 (Diff & Quality Control)
        CRAW->>SCHED: 提交原始分塊數據 (Raw Chunks)
        SCHED->>DIFF: 執行差異偵測 (process_diff_and_save)
        
        alt 刪除異常 (Delete Limit > 33%)
            DIFF-->>SCHED: 觸發熔斷保護 (Circuit Breaker)
            Note over SCHED: 停止更新流程，發送系統警告通知
        else 驗證通過
            DIFF-->>SCHED: 返回變動清單 (Added / Deleted List)
        end
    end

    rect rgb(255, 250, 245)
        Note over SCHED,SYNC: 階段三：資料清洗與結構化 (Data Cleaning & Parsing)
        SCHED->>SYNC: 啟動同步程序 (notify_rag_system)
        
        loop 增量內容處理 (Item Processing)
            SYNC->>PS: 執行文本清洗 (process_item)
            Note over PS: 清洗邏輯：<br/>■ HTML 轉 Markdown<br/>■ 移除廣告與社群雜訊<br/>■ 計算 Token 並生成 Hash ID
        end
        
        SYNC->>SYNC: 產出動態同步文件 (Upsert/Delete JSON)
    end

    rect rgb(240, 248, 255)
        Note over SYNC,DB: 階段四：向量化與入庫 (Hardware-Aware Indexing)
        SYNC->>VP: 執行向量處理器 (run_dynamic_sync)
        
        Note over VP: 硬體感知調優 (Auto-Scaling)：<br/>■ GPU 加速 (RTX 4050/3060)<br/>■ 高併發 (16C+ CPU)<br/>■ 節能模式 (Low-End Hardware)
        
        VP->>VP: 非同步批次生成向量 (Batch Embedding)
        VP->>DB: 執行資料庫原子更新 (Atomic Upsert/Delete)
    end

    Note over DB: 索引同步完成，數據即時可用


## 核心組件說明

| 組件 | 職責 |
| :--- | :--- |
| **Crawlers** | 針對不同來源（Azure, M365, Partner Center）的客製化抓取邏輯。 |
| **Diff Engine** | 核心穩定性偵測，確保系統不會因爬蟲失效而清空現有資料（熔斷機制）。 |
| **Data Parser** | 清理廣告、社群連結與樣板代碼，並將長度標準化，是 RAG 品質的關鍵。 |
| **Vector Processor** | 實現「硬體感知」的非同步向量生成，在不同運算資源下都能快速重建索引。 |
