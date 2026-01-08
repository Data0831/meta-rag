graph LR
    subgraph User_Adjustable [使用者可調整參數]
        P1[user_query: 搜尋關鍵字或描述]
        P2[limit: 返回結果筆數 預設5, 最大50]
        P3[semantic_ratio: 混合檢索比例 0為純關鍵字, 1為純語義]
        P4[manual_semantic_ratio: 是否手動強制比例]
        P5[start_date / end_date: 資料日期範圍 過濾條件]
        P6[website: 來源篩選 如 Azure, M365 等]
    end

    subgraph System_Internal [系統自動管理參數]
        S1[history: 對話上下文 影響意圖解析]
        S2[exclude_ids: 排除已見 ID 避免重複]
        S3[direction: AI 建議的優化方向]
        S4[is_retry_search: 自動重試機制 內部狀態]
        S5[pre_search_limit: 預檢索筆數 系統動態計算]
    end

    subgraph Fixed_Constants [固定系統常數]
        C1[SCORE_PASS_THRESHOLD: 相關性門檻 0.81]
        C2[SEARCH_MAX_RETRIES: 最大重試次數 1次]
        C3[DATE_RANGE_MIN: 最小可查日期 2023-01]
    end

    User_Adjustable --> SearchService
    System_Internal --> SearchService
    Fixed_Constants --> SearchService