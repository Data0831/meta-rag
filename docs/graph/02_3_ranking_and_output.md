sequenceDiagram
    autonumber
    
    participant SVC as Search Service<br/>(search_service.py)
    participant ALG as Keyword Algorithm<br/>(keyword_alg.py)
    participant Agent as Search Sum Agent<br/>(srhSumAgent.py)

    Note over SVC: 接收檢索批次結果 (Receive Raw Results)

    rect rgb(255, 250, 245)
        Note over SVC,ALG: 階段三：結果重排與加權 (Deduplicate & Rerank)
        SVC->>SVC: 跨查詢全局去重 (Global ID Deduplication)
        
        SVC->>ALG: 啟動關鍵字權重優化 (Keyword Reranking)
        Note over ALG: 權重計算邏輯：<br/>■ 標題與內容關鍵字命中 (Must-have Check)<br/>■ 動態加乘：Hit Boost / Miss Penalty<br/>■ 最終得分：Meili Score & Algorithm Weight
        ALG-->>SVC: 返回重排後的有序列表 (Ranked List)
    end

    rect rgb(255, 255, 245)
        Note over SVC: 階段四：數據聚合與截斷 (Aggregation & Final Output)
        loop 文檔 Link 彙整 (Link-based Merging)
            SVC->>SVC: 同源內容整合 (\n---\n 分隔)<br/>■ 累加內容 Token 數<br/>■ 保留最具參考價值之 Metadata
        end
        SVC->>SVC: 套用 Limit 限制與截斷處理
    end

    SVC-->>Agent: 返回精煉結果 (Sorted Top-K)
    Note over Agent: 搜尋任務結束
