# 混合檢索流程 (Hybrid Search Flow - Meilisearch 版)

## 架構概觀 (Architecture Overview)

```mermaid
graph TD
    User["使用者查詢: '三個月內 AI Cloud 合作夥伴計劃相關公告'"] --> Context[當前日期上下文]
    Context -->|"2025-12-16"| LLM[LLM 查詢解析器<br/>意圖識別]

    LLM -->|"嚴格過濾"| Filters["月份: [2025-10, 2025-11, 2025-12]<br/>分類: null<br/>影響等級: null"]
    LLM -->|"關鍵字查詢 (模糊)"| KeywordQ["'AI Cloud 合作夥伴計劃'"]
    LLM -->|"語意向量"| VectorQ["[使用者查詢的向量表示]"]

    Filters & KeywordQ & VectorQ --> SearchArgs[搜尋參數]

    subgraph "Meilisearch 引擎 (統一檢索)"
        SearchArgs -->|"混合查詢 (limit=24)"| Engine[Meilisearch 核心]

        Engine -->|1. 模糊匹配| KeywordResult[錯字容忍 & 前綴搜尋<br/>例如 'partnr' -> 'partner']
        Engine -->|2. 語意匹配| VectorResult[概念相似度]
        Engine -->|3. 套用過濾| FilterResult[Metadata 過濾]

        KeywordResult & VectorResult & FilterResult --> Ranking[內建排序演算法]
    end

    Ranking --> PreResults["預搜尋結果 (24 筆)<br/>按 _rankingScore 排序"]

    subgraph "本地後處理 (Link 去重合併)"
        PreResults --> Merge["遍歷結果<br/>檢查 link 是否重複"]
        Merge -->|"相同 link"| Concat["合併 content<br/>使用 \\n---\\n 分隔<br/>保留最高 score 的 metadata"]
        Merge -->|"不同 link"| Keep["保留文檔"]
        Concat & Keep --> Merged["去重後結果"]
    end

    Merged --> Final["取前 limit 筆<br/>最終結果"]
```

## 去重合併邏輯 (Deduplication & Merge)

為避免文檔切塊後同一網頁重複出現在搜尋結果中，系統採用以下策略：

1. **預搜尋 (Pre-search)**：向 Meilisearch 請求 24 筆結果（可在 `config.PRE_SEARCH_LIMIT` 配置）
2. **合併重複 link**：
   - 遍歷已按 `_rankingScore` 降序排序的結果
   - 遇到相同 `link` 時，將後續文檔的 `content` 拼接至第一個出現的文檔
   - 拼接格式：`content1 + "\n---\n" + content2`
   - 保留最高 score 文檔的所有 metadata (title, year_month, workspace, _rankingScore 等)
3. **截取最終結果**：從去重後的文檔列表中取前 `limit` 筆返回

此設計確保用戶看到的是不同網頁的搜尋結果，而非同一網頁的多個片段，提升搜尋體驗與結果多樣性。
