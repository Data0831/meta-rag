graph TD
    User[使用者輸入] --> LLM_Intent[LLM 意圖解析與分解]
    
    subgraph "LLM 核心任務"
        LLM_Intent -- "1. 生成" --> SubQueries["<b>子查詢列表 Sub-Queries</b><br/>1. Windows 11 漏洞<br/>2. Windows Server 2025 CVE<br/>3. 安全更新公告"]
    end

    subgraph "檢索層 Batch Processing"
        SubQueries -- "單次多重檢索 Multi-Search Request" --> Meili[**Meilisearch /multi-search Endpoint**]
        
        Meili -- "批量返回" --> Hits_Batch[Results Batch Hits 1, Hits 2, Hits 3]
    end

    subgraph "後處理層"
        Hits_Batch --> Union[<b>聯集與去重 Deduplication</b>]
        Union --> GlobalRerank[<b>總體重排序 Global Reranker</b><br/>根據原始意圖重新評分]
        GlobalRerank --> FinalResults[最終結果 Top K]
    end

    FinalResults --> UI[前端顯示結果 + 搜尋軌跡 Traces]