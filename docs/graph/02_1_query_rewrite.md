sequenceDiagram
    participant Agent as srhSumAgent.py
    participant LLM as client.py (LLM)
    participant SVC as search_service.py

    Note over Agent,SVC: 進入搜尋流程
    Agent->>SVC: search(query, limit, semantic_ratio, history, direction, exclude_ids...)

    rect rgb(255, 250, 240)
        Note over SVC,LLM: 1. Query Rewrite - 意圖解析與查詢改寫
        SVC->>LLM: 傳入當前查詢、歷史脈絡與優化方向
        LLM-->>SVC: 返回 SearchIntent 結構 (含關鍵字、子查詢、過濾條件)
        
        Note over SVC: 根據 AI 意圖組合參數：<br>■ 搜詢清單：主查詢 + N 組擴展子查詢<br>■ 檢索過濾器：動態日期、網站來源、排除 ID
    end
    
    Note over SVC: 意圖解析完成，進入查詢執行階段
