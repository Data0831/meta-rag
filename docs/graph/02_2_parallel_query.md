sequenceDiagram
    participant SVC as search_service.py
    participant VU as vector_utils.py (ollama)
    participant Meili as db_adapter_meili.py (Meilisearch)

    Note over SVC: 承接自階段 1 的意圖解析結果 (SearchIntent)

    rect rgb(245, 250, 255)
        Note over SVC,Meili: 2. 平行查詢執行 (Multi-Search)
        
        loop 建構查詢參數 (對應 N 個子查詢)
            SVC->>VU: get_embedding(query_text) (若啟用語義檢索)
            VU-->>SVC: 返回向量表示
            SVC->>SVC: 封裝為 Meilisearch 檢索請求
        end
        
        SVC->>Meili: multi_search (批次發送所有查詢請求)
        
        Note over Meili: Meilisearch 混合檢索引擎：<br>■ 檢索機制：模糊匹配 + 向量相似度<br>■ 過濾器：套用日期/網站來源/排除 ID<br>■ 混合排序：Score = (1-ratio)*keyword + ratio*semantic
        
        Meili-->>SVC: 返回所有查詢之批次結果 (Search Results Batch)
    end

    Note over SVC: 階段 2 完成，準備進入重排流程
