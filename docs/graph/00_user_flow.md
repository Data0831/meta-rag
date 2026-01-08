flowchart TB
    Start(("使用者提出問題")) --> Input["輸入搜索並選擇篩選條件<br>如：特定日期區間、指定網站來源、相似度等等"]
    Input --> Strategy["AI 智慧分析意圖<br>拆解問題並規劃多維檢索策略"]
    Strategy --> Search["執行深度搜索<br>同步撈取關鍵字與相關語義資料"]
    Search --> QualityCheck{"搜尋結果品質<br>是否足以回答問題?"}
    QualityCheck -- 否，品質不足 --> AI_Retry["AI擴大範圍並排除無效資訊，自動優化生成新查詢方向後重試"]
    AI_Retry --> Search
    QualityCheck -- 是，符合需求 --> Summarize["生成摘要<br>包含簡短總結、詳細分析與引用來源"]
    Summarize --> View(("使用者檢視答案與來源"))
    View --> NextStep{"使用者的下一步?"}
    NextStep -- 針對結果持續提問 --> Chat["問答機器人交互<br>(保持上下文並回答)"]
    Chat --> View
    NextStep -- 發起另一個搜尋 --> Start
    NextStep -- 結束瀏覽 --> Exit(("結束對話"))

    style Start fill:#f9f,stroke:#333,stroke-width:2px
    style Strategy fill:#fff4dd,stroke:#d4a017
    style AI_Retry fill:#fce4ec,stroke:#880e4f
    style Summarize fill:#e1f5fe,stroke:#01579b
    style View fill:#bbf,stroke:#333,stroke-width:2px
    style Exit fill:#eee,stroke:#999,stroke-width:2px