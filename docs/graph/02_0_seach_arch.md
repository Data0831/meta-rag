sequenceDiagram
    autonumber
    
    participant Agent as Search Sum Agent<br/>(srhSumAgent.py)
    participant SVC as Search Service<br/>(search_service.py)
    participant LLM as LLM Client<br/>(client.py)
    participant VU as Vector Utils<br/>(vector_utils.py)
    participant Meili as Meilisearch DB<br/>(db_adapter_meili.py)

    Agent->>SVC: 調用檢索介面 (Search API)
    
    rect rgb(255, 250, 240)
        Note over SVC,LLM: 階段一：意圖解析與查詢改寫 (Query Rewrite)
        SVC->>LLM: 提交查詢語境與歷史行為
        LLM-->>SVC: 返回 SearchIntent 結構化數據<br/>■ Keyword Query (關鍵字)<br/>■ Semantic Query (語義核心)<br/>■ Sub-Queries (衍生子查詢)
    end

    rect rgb(245, 250, 255)
        Note over SVC,Meili: 階段二：平行查詢執行 (Parallel Multi-Search)
        opt 語義轉換 (Embedding)
            SVC->>VU: 針對語義需求生成 Embedding
            VU-->>SVC: 向量表示
        end
        SVC->>Meili: 執行高效能平行檢索 (multi_search)
        Meili-->>SVC: 返回多維度檢索結果集 (Raw Results)
    end

    rect rgb(255, 250, 245)
        Note over SVC: 階段三：結果重排與輸出 (Ranking & Output)
        SVC->>SVC: 內部運算處理：<br/>■ 跨分片/來源結果去重<br/>■ 關鍵字權重混合重排 (Hybrid Ranking)<br/>■ Link 聚合與前 N 名截斷
    end

    SVC-->>Agent: 返回精煉後的檢索結果 (Sorted Top-K)
