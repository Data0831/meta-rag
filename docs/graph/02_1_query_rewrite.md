sequenceDiagram
    autonumber
    
    participant Agent as Search Sum Agent<br/>(srhSumAgent.py)
    participant SVC as Search Service<br/>(search_service.py)
    participant LLM as LLM Engine<br/>(Gemini / Client)

    Note over Agent,SVC: 觸發檢索流程 (Trigger Search)
    Agent->>SVC: 傳遞查詢參數與對話歷史 (Query Context)

    rect rgb(255, 250, 240)
        Note over SVC,LLM: 意圖擷取與查詢擴展 (Intent Analysis)
        SVC->>LLM: 提交原始 Query + 歷史脈絡 + 優化指令 (Direction)
        LLM-->>SVC: 返回結構化 SearchIntent<br/>■ Keyword Query: 核心關鍵字<br/>■ Sub-Queries: 語義擴展查詢<br/>■ Filters: 自動識別的過濾條件
    end

    rect rgb(245, 250, 255)
        Note over SVC: 搜尋任務整合 (Task Assembly)
        Note over SVC: 根據 AI 意圖動態組裝：<br/>■ 查詢矩陣：[核心] + [擴展子查詢]<br/>■ 過濾引擎：日期範圍、來源限制、排除清單<br/>■ 權重分配：關鍵字 vs 語義比例
    end
    
    Note over SVC: 意圖解析完成，準備平行檢索 (Ready for Multi-Search)
