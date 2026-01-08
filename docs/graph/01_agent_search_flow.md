sequenceDiagram
    participant FE as Frontend (UI)
    participant API as app.py (API)
    participant AGT as srhSumAgent.py (Agent)
    participant SVC as search_service.py (Search)
    participant LLM as client.py (LLM)

    rect rgb(255, 250, 240)
        Note over FE,API: 1. 請求發起與預處理
        FE->>API: 傳送搜尋請求
        Note right of API: 驗證參數：<br/>■ 語義比例與日期<br/>■ 字數限制與過濾項
        API->>AGT: 啟動 Agent 工作流
    end

    rect rgb(245, 250, 255)
        Note over AGT,LLM: 2. 深度搜尋循環 (Search Loop)
        loop 檢索與品質驗證
            AGT->>SVC: 執行混合檢索
            SVC->>LLM: 意圖解析 (Intent Parsing)<br/>與查詢改寫 (Query Rewrite)
            SVC-->>AGT: 回傳初始檢索結果 (Raw Hits)
            
            Note over AGT,LLM: 相關性驗證：<br/>■ 評估檢索結果與問題匹配度<br/>■ 判定是否需要補充資訊
            AGT->>LLM: 檢查是否需重試 (_check_retry_search)
            LLM-->>AGT: 回傳決策 (重試標記 + 優化方向)
            
            opt 資訊不足且未達重試上限
                AGT->>AGT: 記錄 exclude_ids 並整合優化方向
            end
        end
    end

    rect rgb(245, 255, 250)
        Note over AGT,LLM: 3. 結果彙整與串流響應
        AGT->>LLM: 最終摘要生成 (summarize)
        Note right of LLM: 整合內容：<br/>■ 核心總結<br/>■ 詳細分析<br/>■ 引用來源映射
        AGT-->>API: 串流回傳狀態與結果 (Streaming)
        API-->>FE: Stream NDJSON 響應
    end
