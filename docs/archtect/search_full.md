graph TD
    %% 開始節點
    Start[使用者輸入 Query] --> Intent[LLM 解析搜尋意圖<br/>產生 Keyword, Semantic, Sub-queries]

    subgraph Round1 [第一輪：初始搜尋]
        S1_Search[Meilisearch 執行 Multi-Search<br/>包含主查詢與子查詢候選項] --> S1_IDSearched{取得原始 Hits}
        S1_IDSearched --> S1_DedupeID[ID 階層去重<br/>去除同 API Batch 內的重複 ID]
        S1_DedupeID --> S1_Rerank[ResultReranker<br/>關鍵字權重重排]
        S1_Rerank --> S1_Merge1[<b>Stage 1 合併 SearchService</b><br/>按 Link 合併, 產生 all_ids List, 拼接內容]
        S1_Merge1 --> S1_Return[傳回 Agent]
    end

    Round1 --> Agent_Add1[<b>Stage 2 合併 Agent</b><br/>將結果存入 collected_results<br/>記錄 all_seen_ids]

    Agent_Add1 --> QualityCheck{品質評估<br/>分數是否達標 & LLM 判斷相關?}

    %% 品質達標分支
    QualityCheck -- 是 足夠相關 --> Finalize

    %% 品質不佳分支 第二次搜尋
    QualityCheck -- 否 需要重試 --> Rewrite[AI 重寫查詢語句<br/>並帶著已搜尋過的 exclude_ids]

    subgraph Round2 [第二輪：重試搜尋]
        S2_Search[Meilisearch 排除 exclude_ids<br/>執行優化後的搜尋] --> S2_IDSearched{取得新 Hits}
        S2_IDSearched --> S2_DedupeID[ID 階層去重]
        S2_DedupeID --> S2_Rerank[關鍵字權重重排]
        S2_Rerank --> S2_Merge1[<b>Stage 1 合併 SearchService</b><br/>按新搜尋結果內 Link 合併]
        S2_Merge1 --> S2_Return[傳回 Agent]
    end

    Round2 --> Agent_Add2[<b>Stage 2 跨回合合併 Agent</b><br/>比對 collected_results<br/>若 Link 重複則拼接內容與 ID 列表]

    Agent_Add2 --> Finalize

    subgraph Output [最終處理與輸出]
        Finalize[最終排序 Sort<br/>依據 Rerank 或 Ranking Score] --> Limit[截斷至指定數量 Limit]
        Limit --> Summarize[LLM 生成總結<br/>使用合併後的完整 Context]
        Summarize --> End[回傳最終結果與引用]
    end

    %% 樣式設定
    style Round1 fill:#f9f,stroke:#333,stroke-width:2px
    style Round2 fill:#bbf,stroke:#333,stroke-width:2px
    style S1_Merge1 fill:#ff9,stroke:#f66,stroke-width:3px
    style Agent_Add1 fill:#ff9,stroke:#f66,stroke-width:3px
    style Agent_Add2 fill:#ff9,stroke:#f66,stroke-width:3px