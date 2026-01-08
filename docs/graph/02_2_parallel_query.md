sequenceDiagram
    autonumber
    
    participant SVC as Search Service<br/>(search_service.py)
    participant VU as Vector Engine<br/>(vector_utils.py)
    participant Meili as Meilisearch Engine<br/>(db_adapter_meili.py)

    Note over SVC: 承接意圖解析結果 (Receive SearchIntent)

    rect rgb(245, 250, 255)
        Note over SVC,Meili: 平行查詢執行 (Parallel Multi-Search)
        
        loop 參數預處理 (Query Preprocessing)
            opt 語義向量化 (Semantic Search Only)
                SVC->>VU: 針對子查詢生成 Embedding
                VU-->>SVC: 返回語義向量 (Vector)
            end
            SVC->>SVC: 封裝檢索參數 (Build Params)
        end
        
        SVC->>Meili: 批次發送請求 (Multi-Search Batch)
        
        Note over Meili: Meilisearch 混合檢索引擎空間：<br/>■ 檢索機制：模糊匹配 + 向量相似度<br/>■ 過濾引擎：套用日期 / 網站來源 / 排除 ID<br/>■ 混合排序：Hybrid Score Calculation
        
        Meili-->>SVC: 返回批次結果 (Raw Results Batch)
    end

    Note over SVC: 階段二完成，準備進入結果重排 (Ready for Ranking)
