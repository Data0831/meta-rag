sequenceDiagram
    participant Agent as srhSumAgent.py
    participant LLM as client.py (LLM)
    participant VU as vector_utils.py (ollama)
    participant Reranker as keyword_alg.py (keyword weight)
    participant Meili as db_adapter_meili.py (Meilisearch)
    participant SVC as search_service.py

    Agent->>SVC: search(query, limit, semantic_ratio, history, direction, exclude_ids...)

    rect rgb(255, 250, 240)
        Note over SVC,LLM: 1. Query Rewrite - 意圖解析與查詢改寫
        SVC->>LLM: prompt(query, history, direction, website)
        Note over LLM: Prompt 包含: 當前日期, 歷史查詢, AI 優化方向
        LLM-->>SVC: SearchIntent {keyword_query, semantic_query, sub_queries, must_have_keywords, year_month, recommended_semantic_ratio}
        Note over SVC,LLM: 子查詢 與 相關過濾條件
        Note over SVC,LLM: 組合查詢列表:<br>1. Primary: keyword_query<br>2. Sub-Query 1<br>3. Sub-Query 2<br>...
        Note over SVC,LLM: 組合 Meilisearch Filter:<br>- AI 日期 OR 手動日期範圍<br>- 指定網站來源<br>- 排除已見 ID (exclude_ids)
    end

    rect rgb(245, 250, 255)
        Note over SVC,Meili: 2. 平行查詢執行 (Multi-Search)
        
        loop 為每個查詢候選建構參數
            SVC->>SVC: _build_single_query_params(query_text, intent, semantic_ratio)
            opt 如果 semantic_ratio > 0 (混合檢索)
                SVC->>VU: get_embedding(query_text)
                VU-->>SVC: 返回向量表示 [0.123, ...]
            end
        end
        
        SVC->>Meili: multi_search([query1_params, query2_params, ...])
        
        Note over Meili: Meilisearch 混合檢索引擎
        
        par 平行執行多個查詢
            rect rgb(255, 255, 240)
                Note over Meili: Query x 4
                Meili->>Meili: 模糊匹配 (Fuzzy Match) - 錯字容忍, 前綴搜尋, 同義詞擴展
                Meili->>Meili: 語義匹配 (Semantic Search) - 向量相似度計算, 概念理解
                Meili->>Meili: 套用過濾器 (Filters) - 日期範圍, 網站來源, 排除 ID
                Meili->>Meili: 混合排序<br>Score = (1-ratio)*keyword + ratio*semantic
            end
        end
        
        Meili-->>SVC: 返回批次結果 {results: [ { hits: [...], estimatedTotalHits: 100 }, { hits: [...], estimatedTotalHits: 85 }, ... ]}
    end

    rect rgb(255, 250, 245)
        Note over SVC: 3. 跨查詢去重
        SVC->>SVC: _deduplicate_hits(raw_hits_batch)
        Note over SVC: 合併所有子查詢結果按 document ID 去重保留首次出現的文檔
        Note over SVC,Reranker: 4. 關鍵字加權重排 (Keyword Reranking)
        SVC->>Reranker: ResultReranker(all_hits, must_have_keywords)
        SVC->>Reranker: rerank(top_k = limit * 2.5)
        
        loop 遍歷每個文檔
            Reranker->>Reranker: 檢查關鍵字命中
            Note over Reranker: 標題 + 內容中檢查 must_have_keywords計算命中比例 (hit_ratio)
            
            Reranker->>Reranker: 計算加權分數
            Note over Reranker: 公式: penalty = original * (1 - P*(1-ratio)) boost = B * ratio * (1-original) final_score = penalty + boost P = 0.25 (懲罰係數) B = 0.55 (提升係數)
        end
        
        Reranker->>Reranker: 按 _rerank_score 降序排序
        Reranker-->>SVC: 返回重排後結果 (top_k 筆)
    end

    rect rgb(245, 255, 250)
        Note over SVC: 5. Link 去重合併
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

    SVC-->>Agent: 返回搜尋結果 {status: "success", intent: {...}, results: [...], final_semantic_ratio: 0.8, mode: "semantic", traces: [...]}

