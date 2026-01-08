sequenceDiagram
    participant FE as Frontend (Browser)
    participant API as app.py (/api/search)
    participant Agent as srhSumAgent.py (Agent)
    participant SVC as search_service.py (Search)
    participant LLM as LLM (gpt-4o-mini)

    FE->>API: POST { query, limit, semantic_ratio, start_date, website... }
    Note over API: 驗證參數與字數限制
    API->>Agent: Agent.run(query, limit, website, date_range...)
    rect rgb(240, 240, 240)
        Note right of Agent: 進入搜尋循環
        Agent->>SVC: search(query, history, website...)
        SVC->>LLM: Intent Parsing (關鍵字/子查詢/日期)<br>+ QueryRewrite (模糊 + 語義 + 子查詢)
        SVC-->>Agent: 回傳初篩結果 (Raw Hits)
        Agent->>LLM: _check_retry_search (評估相關性)
        LLM->>Agent: LLM 決定始否需要繼續查詢，回傳優化後新查詢方向
        alt 資訊有缺或相關度不足可重試
            Agent->>Agent: 記錄 exclude_ids(排除之前查詢) & 取得優化方向
            Agent->>SVC: 重新執行 search (帶入方向與排除項)
        end
    end

    Agent->>LLM: summarize (針對 搜索倒的所有內容 進行結構化總結)
    Agent-->>API: yield { stage, message, results, summary... } (Streaming)
    API-->>FE: Stream NDJSON response