# Hybrid Search Flow (Phase 4)

## Architecture Overview

```mermaid
graph TD
    User["User Query: '三個月內 AI 雲合作夥伴計劃相關公告'"] --> Context[Current Date Context]
    Context -->|"2025-12-16"| LLM[LLM Query Parser<br/>Intent Recognition]

    LLM -->|"Strict Filters"| Filters["months: [2025-10, 2025-11, 2025-12]<br/>category: null<br/>impact_level: null"]
    LLM -->|"Keyword Query"| KeywordQ["'AI 雲合作夥伴計劃 公告'"]
    LLM -->|"Semantic Query"| SemanticQ["'過去三個月 AI 雲合作夥伴計劃的相關公告'"]
    LLM -->|"Soft Match (Boost)"| Boost["boost_keywords:<br/>['AI 雲合作夥伴計劃', 'AI Cloud Partner Program']"]

    Filters & KeywordQ & SemanticQ & Boost --> SearchArgs[Search Arguments]

    subgraph Parallel Execution
        SearchArgs -->|"Filters + Keyword"| SQLite["SQLite FTS5 Search<br/>month IN (oct, nov, dec) + MATCH query"]
        SearchArgs -->|"Filters + Vector"| Qdrant["Qdrant Semantic Search<br/>month=ANY + Vector Similarity"]
    end

    SQLite --> ResultA["List A: UUIDs + Rank"]
    Qdrant --> ResultB["List B: UUIDs + Score"]

    ResultA & ResultB --> Merger["RRF Fusion Algorithm<br/>score = 1/(k+rank)"]

    Merger --> Sorted["Sorted UUIDs by Combined Score"]
    Sorted --> Fetch["Fetch Full Docs from SQLite<br/>by UUID"]

    Fetch --> Final["Final Results<br/>(with snippets, metadata, RRF score)"]
```

## Key Components

### 1. LLM Query Parser
- **Input**: User query + Current date
- **Output**: Structured SearchIntent
  - `filters` (strict): months, category, impact_level
  - `keyword_query`: Optimized for FTS5
  - `semantic_query`: Optimized for vector search
  - `boost_keywords`: Soft-match terms (不強制過濾)

### 2. Filter Strategy
- **Strict Filters** (MUST match):
  - Time range (months list)
  - Category
  - Impact level

- **Soft Boost** (加分但不過濾):
  - Product names
  - Technical terms
  - Brand names

### 3. Database Adapters
- **SQLite**: FTS5 with metadata filters
  - `month IN (...)` for multi-month support
  - No products filtering

- **Qdrant**: Vector search with payload filters
  - `MatchAny(any=months)` for date ranges
  - No products filtering

### 4. RRF Fusion
- Combines results from both sources
- Formula: `score = 1 / (k + rank)` where k=60
- Handles single-source and dual-source matches

## Example Queries

### Query 1: Time Range + Product Mention
```
Input: "三個月內「AI 雲合作夥伴計劃」相關公告"
Output:
  - months: ["2025-10", "2025-11", "2025-12"]
  - boost_keywords: ["AI 雲合作夥伴計劃"]
  - Result: 返回三個月內所有公告，提及該產品的排序更高
```

### Query 2: Strict Filters
```
Input: "過去兩個月的高影響力安全公告"
Output:
  - months: ["2025-11", "2025-12"]
  - category: "Security"
  - impact_level: "High"
  - Result: 僅返回符合所有條件的公告
```

### Query 3: Soft Match Only
```
Input: "Azure OpenAI pricing details"
Output:
  - months: []
  - category: "Pricing"
  - boost_keywords: ["Azure OpenAI"]
  - Result: 所有價格公告，提及 Azure OpenAI 的優先
```

## Benefits of This Architecture

1. **智能時間解析**: "三個月內" 自動展開為月份列表
2. **彈性匹配**: Products 作為加分項而非過濾器
3. **並行搜尋**: SQLite FTS + Qdrant 同時執行
4. **結果融合**: RRF 演算法平衡兩種搜尋策略
5. **上下文感知**: LLM 能根據當前日期計算相對時間
