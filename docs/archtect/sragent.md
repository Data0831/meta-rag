# Agentic Search & Summary Streaming Flow

## 核心流程 (Core Workflow)

本系統採用 **Server-Sent Events (SSE) 風格的 NDJSON 串流** 技術，實現後端 Agent 思考過程的即時視覺化。

### 循序圖 (Sequence Diagram)

```mermaid
sequenceDiagram
    participant UI as 前端 (search.js)
    participant API as Flask API (/api/summary)
    participant Agent as SrhSumAgent
    participant LLM as Google Gemini
    participant DB as Meilisearch

    Note over UI, API: 使用者發起摘要請求
    UI->>API: POST /api/summary {query, initial_results}
    API->>Agent: generate_summary(query, results) (Generator)
    
    activate Agent
    
    %% 階段 1: 檢查初始結果
    Agent-->>API: yield {status: "checking", message: "正在檢查..."}
    API-->>UI: Stream Line JSON
    UI->>UI: 更新摘要標題: 🧐 正在檢查...
    
    Agent->>LLM: Check Relevance Prompt
    LLM-->>Agent: {relevant: boolean, ids: [...]}

    alt 初始結果相關 (Relevant)
        Agent-->>API: yield {status: "summarizing", ...}
        API-->>UI: Stream Line JSON
        UI->>UI: 更新摘要標題: 💡 正在生成摘要...
        
        Agent->>LLM: Summarize Prompt
        LLM-->>Agent: Summary Text
        
        Agent-->>API: yield {status: "complete", summary: "...", results: [...]}
        API-->>UI: Stream Line JSON
        UI->>UI: 渲染 Markdown 摘要
    
    else 初始結果不相關 (Irrelevant)
        Agent-->>API: yield {status: "rewriting", ...}
        API-->>UI: Stream Line JSON
        UI->>UI: 更新摘要標題: ✍️ 正在重寫查詢...
        
        Agent->>LLM: Rewrite Query Prompt
        LLM-->>Agent: New Query String
        
        %% 階段 2: 重新搜尋循環
        loop Max Retries (1 time)
            Agent-->>API: yield {status: "searching", new_query: "...", ...}
            API-->>UI: Stream Line JSON
            UI->>UI: 更新摘要標題: 🔄 正在搜尋 'xxx'...
            
            Agent->>DB: Search(New Query)
            DB-->>Agent: New Results
            
            Agent-->>API: yield {status: "checking", ...}
            API-->>UI: Stream Line JSON
            
            Agent->>LLM: Check Relevance (New Results)
            LLM-->>Agent: {relevant: boolean}
            
            alt 新結果相關
                Agent-->>API: yield {status: "summarizing", ...}
                Agent->>LLM: Summarize
                LLM-->>Agent: Summary
                
                Note right of Agent: 回傳 summary 與 new results
                Agent-->>API: yield {status: "complete", summary: "...", results: NewResults}
                API-->>UI: Stream Line JSON
                UI->>UI: 1. 渲染摘要<br/>2. 發現 results 更新 -> 刷新下方列表
                
            end
        end
        
        %% Fallback
        Agent-->>API: yield {status: "complete", summary: "抱歉...", results: LastResults}
        API-->>UI: Stream Line JSON
        UI->>UI: 顯示道歉訊息 & 更新列表為最後嘗試結果
    end
    
    deactivate Agent
    API-->>UI: Close Stream
```

## 狀態定義 (State Definitions)

| 狀態代碼 (`status`) | UI 行為 | 說明 |
| :--- | :--- | :--- |
| `checking` | 顯示 **🧐 正在檢查...** (Bounce動畫) | Agent 正在評估目前的搜尋結果是否足以回答使用者的問題。 |
| `rewriting` | 顯示 **✍️ 正在重寫...** (Pulse動畫) | 初始結果品質不佳，Agent 正在根據語意生成更好的關鍵字。 |
| `searching` | 顯示 **🔄 正在搜尋...** (Spin動畫) | 使用新的關鍵字向 Meilisearch 發起查詢。 |
| `summarizing` | 顯示 **💡 正在總結...** (Pulse動畫) | 資料充足，正在呼叫 LLM 進行最終的摘要寫作。 |
| `complete` | 顯示 **最終結果** | 流程結束。回傳 Markdown 格式摘要，若有新搜尋結果則一併回傳。 |
