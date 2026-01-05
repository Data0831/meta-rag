graph TD
    subgraph Scheduler ["scheduler.py (排程層)"]
        S1[啟動排程器] --> S2{是否到預定時間?}
        S2 -- 否 --> S3[等待 30 秒]
        S3 --> S2
        S2 -- 是 --> S4[呼叫 sync.run_sync]
    end

    subgraph SyncLogic ["sync.py (工作層)"]
        L1[開始同步工作] --> L2[讀取 remove.json]
        L2 --> L3{有待刪除 ID?}
        L3 -- 是 --> L4[分批刪除 DELETE_CHUNK_SIZE=500]
        L4 --> L5[讀取 data.json]
        L3 -- 否 --> L5
        L5 --> L6[提取所有 ID 並分批查詢]
        L6 --> L7[Meilisearch: get_documents_by_ids]
        L7 --> L8[標記已存在的 ID]
        L8 --> L9[篩選出資料庫不存在的新資料]
        
        L9 --> L10{有新資料嗎?}
        
        L10 -- 否 --> L11[流程結束]
        
        L10 -- 是 --> L12[遍歷每筆新資料]
        L12 --> L13[呼叫 get_embedding 生成向量]
        L13 --> L14[轉換格式並加入批次隊列]
        L14 --> L15{批次滿 100 筆?}
        
        L15 -- 是 --> L16[執行 upsert_documents 上傳]
        L16 --> L12
        
        L15 -- 否 --> L17{最後一筆資料?}
        L17 -- 是 --> L16
        L17 -- 否 --> L12
    end

    S4 --> L1
    L11 --> S3