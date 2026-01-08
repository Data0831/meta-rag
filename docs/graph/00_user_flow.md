flowchart TD
    %% 標準色彩定義
    classDef user fill:#f0f9ff,stroke:#0ea5e9,stroke-width:1.5px,color:#0369a1
    classDef system fill:#f0fdf4,stroke:#22c55e,stroke-width:1.5px,color:#15803d
    classDef fixed fill:#f8fafc,stroke:#94a3b8,stroke-width:1px,color:#475569
    classDef core fill:#1e293b,stroke:#0f172a,stroke-width:2px,color:#ffffff,font-weight:bold

    Start(("● 開始提問"))

    subgraph UI_Interaction [前端交互層]
        direction TB
        Input[輸入檢索環境<br/>日期、來源、權重設定]
        View[檢視回答與來源<br/>引用追蹤與摘要展示]
    end

    subgraph AI_Engine [AI 檢索引擎層]
        direction TB
        Strategy[意圖解析與規劃<br/>拆解問題並生成檢索策略]
        Search[執行深度搜尋<br/>混合關鍵字與語義向量]
        QualityCheck{數據品質<br/>足以回答？}
        AI_Retry[AI 自動優化<br/>改寫查詢並擴大搜尋範圍]
    end

    subgraph RAG_Service [生成與摘要層]
        direction TB
        Summarize[RAG 摘要生成<br/>整合原始文本與 AI 分析]
    end

    %% 核心路徑連接
    Start --> Input
    Input ==> Strategy
    
    Strategy --> Search
    Search --> QualityCheck
    
    QualityCheck -- 否 --> AI_Retry
    AI_Retry -- 優化重試 --> Search
    
    QualityCheck -- 是 --> Summarize
    Summarize ==> View

    %% 後續交互路徑
    View --> NextAction{使用者操作}
    NextAction -- 針對結果追問 --> Chat[Chatbot 交互<br/>基於當前內容持續對話]
    Chat -- 顯示回覆 --> View
    
    NextAction -- 發起新搜尋 --> Start
    NextAction -- 結束瀏覽 --> Exit(("● 結束"))

    %% 樣式應用
    class Start,Input,View core
    class Strategy,Search,AI_Retry,Summarize system
    class Chat user
    class Exit fixed

    %% 容器美化
    style UI_Interaction fill:none,stroke:#0ea5e9,stroke-dasharray: 5 5
    style AI_Engine fill:none,stroke:#22c55e,stroke-dasharray: 5 5
    style RAG_Service fill:none,stroke:#94a3b8,stroke-dasharray: 5 5
