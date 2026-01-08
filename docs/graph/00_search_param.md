flowchart TD
    %% 配色與樣式定義
    classDef user fill:#f0f9ff,stroke:#0ea5e9,stroke-width:1.5px,color:#0369a1
    classDef system fill:#f0fdf4,stroke:#22c55e,stroke-width:1.5px,color:#15803d
    classDef fixed fill:#f8fafc,stroke:#94a3b8,stroke-width:1px,color:#475569
    classDef core fill:#1e293b,stroke:#0f172a,stroke-width:2px,color:#ffffff,font-size:16px,font-weight:bold

    %% 主架構
    subgraph Params [搜尋引擎參數體系]
        direction TB

        %% 使用者控制層
        subgraph UserLayer [使用者控制層]
            direction LR
            subgraph U1 [基礎檢索]
                P1[user_query<br/>關鍵字/描述]
                P2[limit<br/>結果筆數]
            end
            subgraph U2 [精確過濾]
                P3[semantic_ratio<br/>語義混合權重]
                P5[date_range<br/>日期篩選條件]
                P6[website<br/>網站來源過濾]
            end
        end

        %% 系統運作層
        subgraph SystemLayer [系統運作層]
            direction LR
            S1[history<br/>對話歷史/上下文]
            S2[exclude_ids<br/>排除重複 ID]
            S3[direction<br/>AI 建議優化方向]
            S5[pre_limit<br/>預檢索動態筆數]
        end

        %% 靜態組態層
        subgraph ConstLayer [靜態組態層]
            direction LR
            C1[THRESHOLD<br/>相關性門檻 0.81]
            C2[MAX_RETRIES<br/>最大重試次數]
            C3[DATE_MIN<br/>查詢日期下限]
        end
    end

    %% 匯入核心連接
    UserLayer ==>|交互參數| SVC
    SystemLayer ==>|執行上下文| SVC
    ConstLayer ==>|系統政策| SVC

    %% 核心組成
    SVC((SearchService<br/>核心檢索調度引擎))

    %% 應用樣式
    class P1,P2,P3,P5,P6 user
    class S1,S2,S3,S5 system
    class C1,C2,C3 fixed
    class SVC core

    %% 容器美化
    style Params fill:#ffffff,stroke:#334155,stroke-width:2px
    style UserLayer fill:none,stroke:#0ea5e9,stroke-dasharray: 5 5
    style SystemLayer fill:none,stroke:#22c55e,stroke-dasharray: 5 5
    style ConstLayer fill:none,stroke:#94a3b8,stroke-dasharray: 5 5

