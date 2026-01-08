```mermaid
sequenceDiagram
    participant Agent as srhSumAgent.py
    participant SVC as SearchService
    participant LLM as LLMClient
    participant Reranker as ResultReranker
    participant Meili as Meilisearch

    Agent->>SVC: search(query, limit, semantic_ratio, history, direction, exclude_ids...)
    
    rect rgb(245, 245, 250)
        Note over SVC: 1️⃣ 初始化與驗證
        SVC->>SVC: _validate_and_init_services()
        SVC->>Meili: 檢查連線健康狀態
        SVC->>SVC: 檢查 Embedding 服務
        SVC->>LLM: 初始化 LLM Client
    end

    rect rgb(255, 250, 240)
        Note over SVC,LLM: 2️⃣ Query Rewrite - 意圖解析與查詢改寫
        SVC->>LLM: parse_intent(query, history, direction, website)
        Note over LLM: Prompt 包含:<br>- 當前日期上下文<br>- 歷史查詢記錄<br>- AI 優化方向<br>- 指定網站來源
        LLM-->>SVC: SearchIntent {<br>  keyword_query: "改寫後關鍵字",<br>  semantic_query: "語義查詢",<br>  sub_queries: ["子查詢1", "子查詢2"],<br>  must_have_keywords: ["關鍵詞"],<br>  year_month: ["2025-12"],<br>  recommended_semantic_ratio: 0.8<br>}
        
        alt LLM 解析失敗
            SVC->>SVC: Fallback 使用原始 query
        end
    end

    rect rgb(240, 255, 245)
        Note over SVC: 3️⃣ 建構查詢候選集 (平行子查詢)
        SVC->>SVC: _build_query_candidates(intent)
        Note over SVC: 組合查詢列表:<br>1. Primary: keyword_query<br>2. Sub-Query 1<br>3. Sub-Query 2<br>...
    end

    rect rgb(255, 245, 250)
        Note over SVC: 4️⃣ 建構過濾條件
        SVC->>SVC: _build_filter_expression(intent, dates, exclude_ids, website)
        Note over SVC: 組合 Meilisearch Filter:<br>- AI 日期 OR 手動日期範圍<br>- 指定網站來源<br>- 排除已見 ID (exclude_ids)
    end

    rect rgb(245, 250, 255)
        Note over SVC,Meili: 5️⃣ 平行子查詢執行 (Multi-Search)
        
        loop 為每個查詢候選建構參數
            SVC->>SVC: _build_single_query_params(query_text, intent, semantic_ratio)
            
            alt semantic_ratio > 0 (混合檢索)
                SVC->>SVC: get_embedding(semantic_query)
                Note over SVC: 生成向量表示
            end
            
            Note over SVC: 建構搜尋參數:<br>{<br>  q: "keyword_query",<br>  limit: pre_search_limit * 1.5 (if retry),<br>  filter: "year_month >= 2025-10 AND...",<br>  hybrid: { semanticRatio: 0.8 },<br>  vector: [0.123, 0.456, ...]<br>}
        end
        
        SVC->>Meili: multi_search([query1_params, query2_params, ...])
        
        Note over Meili: 🔍 Meilisearch 混合檢索引擎
        
        par 平行執行多個查詢
            rect rgb(255, 255, 240)
                Note over Meili: Query 1: Primary Keyword
                Meili->>Meili: 模糊匹配 (Fuzzy Match)<br>- 錯字容忍<br>- 前綴搜尋<br>- 同義詞擴展
                Meili->>Meili: 語義匹配 (Semantic Search)<br>- 向量相似度計算<br>- 概念理解
                Meili->>Meili: 套用過濾器 (Filters)<br>- 日期範圍<br>- 網站來源<br>- 排除 ID
                Meili->>Meili: 混合排序<br>Score = (1-ratio)*keyword + ratio*semantic
            end
        and
            rect rgb(240, 255, 255)
                Note over Meili: Query 2: Sub-Query 1
                Meili->>Meili: 同上混合檢索流程
            end
        and
            rect rgb(255, 240, 255)
                Note over Meili: Query 3: Sub-Query 2
                Meili->>Meili: 同上混合檢索流程
            end
        end
        
        Meili-->>SVC: 返回批次結果 {<br>  results: [<br>    { hits: [...], estimatedTotalHits: 100 },<br>    { hits: [...], estimatedTotalHits: 85 },<br>    ...<br>  ]<br>}
    end

    rect rgb(250, 245, 255)
        Note over SVC: 6️⃣ 跨查詢去重
        SVC->>SVC: _deduplicate_hits(raw_hits_batch)
        Note over SVC: 合併所有子查詢結果<br>按 document ID 去重<br>保留首次出現的文檔
    end

    rect rgb(255, 250, 245)
        Note over SVC,Reranker: 7️⃣ 關鍵字加權重排 (Keyword Reranking)
        SVC->>Reranker: ResultReranker(all_hits, must_have_keywords)
        SVC->>Reranker: rerank(top_k = limit * 2.5)
        
        loop 遍歷每個文檔
            Reranker->>Reranker: 檢查關鍵字命中
            Note over Reranker: 標題 + 內容中<br>檢查 must_have_keywords<br>計算命中比例 (hit_ratio)
            
            Reranker->>Reranker: 計算加權分數
            Note over Reranker: 公式:<br>penalty = original * (1 - P*(1-ratio))<br>boost = B * ratio * (1-original)<br>final_score = penalty + boost<br><br>P = 0.25 (懲罰係數)<br>B = 0.55 (提升係數)
        end
        
        Reranker->>Reranker: 按 _rerank_score 降序排序
        Reranker-->>SVC: 返回重排後結果 (top_k 筆)
    end

    rect rgb(245, 255, 250)
        Note over SVC: 8️⃣ Link 去重合併
        SVC->>SVC: _merge_duplicate_links(reranked_results)
        
        loop 遍歷重排結果
            alt 相同 Link 已存在
                SVC->>SVC: 合併 content (用 \n---\n 分隔)
                SVC->>SVC: 合併 all_ids 列表
                SVC->>SVC: 累加 token 計數
                Note over SVC: 保留最高分文檔的 metadata
            else 新 Link
                SVC->>SVC: 加入結果列表
            end
        end
        
        SVC->>SVC: 截取前 limit 筆
    end

    rect rgb(250, 250, 250)
        Note over SVC: 9️⃣ 建構回應
        SVC->>SVC: _build_response(intent, results, traces)
    end

    SVC-->>Agent: 返回搜尋結果 {<br>  status: "success",<br>  intent: {...},<br>  results: [...],<br>  final_semantic_ratio: 0.8,<br>  mode: "semantic",<br>  traces: [...]<br>}

    style Meili fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    style Reranker fill:#fff4dd,stroke:#d4a017,stroke-width:2px
    style LLM fill:#fce4ec,stroke:#880e4f,stroke-width:2px
```

---

## 核心技術說明

### 🔍 1. Query Rewrite (查詢改寫)
- **LLM 意圖解析**: 理解使用者真實意圖，改寫為更精確的查詢
- **歷史意識**: 結合對話歷史，理解上下文關聯
- **多維度改寫**:
  - `keyword_query`: 模糊匹配用關鍵字
  - `semantic_query`: 語義搜尋用查詢
  - `sub_queries`: 平行子查詢擴展召回範圍
  - `must_have_keywords`: 關鍵字加權用

### 🔀 2. 平行子查詢 (Parallel Sub-Queries)
- **多查詢並行**: 主查詢 + 多個子查詢同時執行
- **擴大召回**: 不同角度查詢同一主題，提升結果完整性
- **Meilisearch Multi-Search API**: 單次請求批次執行，降低延遲

### 🎯 3. 混合檢索 (Hybrid Search)
**模糊搜索 (Keyword Matching)**:
- 錯字容忍 (Typo Tolerance)
- 前綴搜尋 (Prefix Search)
- 同義詞擴展

**語義搜索 (Semantic Search)**:
- 向量相似度計算
- 概念理解 (非精確匹配)
- 語義關聯發現

**混合排序公式**:
```
Final Score = (1 - semantic_ratio) × keyword_score + semantic_ratio × semantic_score
```

### ⚖️ 4. 關鍵字加權重排 (Keyword Reranking)
**目的**: 提升包含關鍵概念文檔的排名

**演算法**:
1. **命中率計算**: `hit_ratio = matched_keywords / total_keywords`
2. **懲罰機制**: 缺少關鍵字降低分數
3. **提升機制**: 命中關鍵字提升分數
4. **公式**:
   ```
   penalty = original × (1 - 0.25 × (1 - hit_ratio))
   boost = 0.55 × hit_ratio × (1 - original)
   final_score = penalty + boost
   ```

**特點**:
- 去重關鍵字避免重複計分
- 標題 + 內容聯合檢查
- 保持分數在 [0, 1] 範圍

### 🔗 5. Link 去重合併
**目的**: 避免同一網頁的多個片段重複出現

**策略**:
- 預搜尋 `limit × 2.5` 筆結果
- 相同 Link 合併 content (用 `\n---\n` 分隔)
- 保留最高分文檔的 metadata
- 合併 `all_ids` 列表與 `token` 計數
- 最終截取前 `limit` 筆

**優勢**: 提升結果多樣性，使用者看到更多不同來源
