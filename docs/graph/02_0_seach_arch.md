sequenceDiagram
    participant Agent as srhSumAgent.py
    participant LLM as client.py (LLM)
    participant VU as vector_utils.py (ollama)
    participant Meili as db_adapter_meili.py (Meilisearch)
    participant SVC as search_service.py

    Agent->>SVC: search(query, limit, semantic_ratio, history, direction, exclude_ids...)

    rect rgb(255, 250, 240)
        Note over SVC,LLM: 1. Query Rewrite - 意圖解析與查詢改寫
        SVC->>LLM: prompt(query, history, direction, website)
        LLM-->>SVC: SearchIntent {keyword_query, semantic_query, sub_queries...}
    end

    rect rgb(245, 250, 255)
        Note over SVC,Meili: 2. 平行查詢執行 (Multi-Search)
        SVC->>VU: get_embedding(query_text) (若需)
        VU-->>SVC: 向量表示
        SVC->>Meili: multi_search([query1_params, ...])
        Meili-->>SVC: 批次結果 {results: [...]}
    end

    rect rgb(255, 250, 245)
        Note over SVC: 3. 重排與輸出 (Ranking & Output)
        SVC->>SVC: 跨查詢去重、關鍵字加權重排、Link 合併截斷
    end

    Note over SVC,Agent: 搜尋流程完成，返回 Top-K 結果
