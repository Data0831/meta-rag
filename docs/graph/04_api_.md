sequenceDiagram
    autonumber
    participant UI as Browser/Frontend
    participant API as Flask App<br/>(src/app.py)
    participant Agent as SearchAgent<br/>(SrhSumAgent)
    participant Svc as ChatService<br/>(RAGService)
    participant DB as Meilisearch
    participant Log as LogManager

    Note over UI, API: 系統初始化與狀態檢查

    rect rgb(255, 250, 240)
        UI->>API: GET /api/config
        API-->>UI: 返回版本、來源列表、前端限制定義
        
        UI->>API: GET /api/health
        API->>DB: 檢查連線與文檔數 (get_stats)
        DB-->>API: 返回健康狀態
        API-->>UI: 返回系統狀態
    end

    Note over UI, Agent: 階段一：智慧搜尋與摘要渲染 (Streaming)

    rect rgb(245, 250, 255)
        UI->>API: POST /api/search (query, filters...)
        API->>Agent: 初始化 Agent 並呼叫 run()
        
        loop 串流產出結果
            Agent->>DB: 執行多向量檢索 (search)
            DB-->>Agent: 檢索結果
            Agent->>Agent: LLM 意圖識別與檢視 (check_retry)
            Agent-->>API: Yield: 搜尋狀態 / 原始結果
            Agent-->>API: Yield: 摘要內容 (Streaming Markdown)
            API-->>UI: NDJSON 串流數據回傳
        end
        
        API->>Log: log_search (紀錄完整歷程)
    end

    Note over UI, Svc: 階段二：RAG 對話互動 (Contextual QA)

    rect rgb(240, 255, 240)
        UI->>API: POST /api/chat (message, history, context)
        API->>Svc: chat(user_query, context, history)
        Svc->>Svc: 組合 Prompt 與上下文檢索
        Svc-->>API: 返回 LLM 生成回覆
        API->>Log: log_chat (記錄對話卷標)
        API-->>UI: 返回 JSON 格式回覆
    end

    Note over UI, Log: 用戶回饋與管理

    rect rgb(250, 250, 250)
        UI->>API: POST /api/feedback (positive/negative)
        API->>Log: log_feedback (歸檔意見)
        API-->>UI: HTTP 200 Success

        UI->>API: POST /api/admin/update-json/:target
        Note right of API: 需驗證 X-Admin-Token
        API->>API: 更新 website.json / announcement.json
        API-->>UI: 更新成功通知
    end