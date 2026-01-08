sequenceDiagram
    participant Agent as srhSumAgent.py
    participant LLM as LLMClient
    participant Reranker as ResultReranker
    participant Meili as Meilisearch

    Agent->>search_service.py: search(query, limit, semantic_ratio, history, direction, exclude_ids...)

    rect rgb(255, 250, 240)
        Note over search_service.py,LLM: 1. Query Rewrite - 意圖解析與查詢改寫
        search_service.py->>LLM: (query, history, direction, website)
        Note over LLM: Prompt 包含:<br>- 當前日期<br>- 歷史查詢<br>- AI 優化方向<br>- 指定網站來源
        LLM-->>search_service.py: SearchIntent {<br>  keyword_query: "改寫後關鍵字",<br>  semantic_query: "語義查詢",<br>  sub_queries: ["子查詢1", "子查詢2"],<br>  must_have_keywords: ["關鍵詞"],<br>  year_month: ["2025-12"],<br>  recommended_semantic_ratio: 0.8<br>}
        
        alt LLM 解析失敗
            search_service.py->>search_service.py: Fallback 使用原始 query
        end
    end

    rect rgb(240, 255, 245)
        Note over search_service.py: 3️⃣ 建構查詢候選集 (平行子查詢)
        search_service.py->>search_service.py: _build_query_candidates(intent)
        Note over search_service.py: 組合查詢列表:<br>1. Primary: keyword_query<br>2. Sub-Query 1<br>3. Sub-Query 2<br>...
    end

    rect rgb(255, 245, 250)
        Note over search_service.py: 4️⃣ 建構過濾條件
        search_service.py->>search_service.py: _build_filter_expression(intent, dates, exclude_ids, website)
        Note over search_service.py: 組合 Meilisearch Filter:<br>- AI 日期 OR 手動日期範圍<br>- 指定網站來源<br>- 排除已見 ID (exclude_ids)
    end

    rect rgb(245, 250, 255)
        Note over search_service.py,Meili: 5️⃣ 平行子查詢執行 (Multi-Search)
        
        loop 為每個查詢候選建構參數
            search_service.py->>search_service.py: _build_single_query_params(query_text, intent, semantic_ratio)
            
            alt semantic_ratio > 0 (混合檢索)
                search_service.py->>search_service.py: get_embedding(semantic_query)
                Note over search_service.py: 生成向量表示
            end
            
            Note over search_service.py: 建構搜尋參數:<br>{<br>  q: "keyword_query",<br>  limit: pre_search_limit * 1.5 (if retry),<br>  filter: "year_month >= 2025-10 AND...",<br>  hybrid: { semanticRatio: 0.8 },<br>  vector: [0.123, 0.456, ...]<br>}
        end
        
        search_service.py->>Meili: multi_search([query1_params, query2_params, ...])
        
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
        
        Meili-->>search_service.py: 返回批次結果 {<br>  results: [<br>    { hits: [...], estimatedTotalHits: 100 },<br>    { hits: [...], estimatedTotalHits: 85 },<br>    ...<br>  ]<br>}
    end

    rect rgb(250, 245, 255)
        Note over search_service.py: 6️⃣ 跨查詢去重
        search_service.py->>search_service.py: _deduplicate_hits(raw_hits_batch)
        Note over search_service.py: 合併所有子查詢結果<br>按 document ID 去重<br>保留首次出現的文檔
    end

    rect rgb(255, 250, 245)
        Note over search_service.py,Reranker: 7️⃣ 關鍵字加權重排 (Keyword Reranking)
        search_service.py->>Reranker: ResultReranker(all_hits, must_have_keywords)
        search_service.py->>Reranker: rerank(top_k = limit * 2.5)
        
        loop 遍歷每個文檔
            Reranker->>Reranker: 檢查關鍵字命中
            Note over Reranker: 標題 + 內容中<br>檢查 must_have_keywords<br>計算命中比例 (hit_ratio)
            
            Reranker->>Reranker: 計算加權分數
            Note over Reranker: 公式:<br>penalty = original * (1 - P*(1-ratio))<br>boost = B * ratio * (1-original)<br>final_score = penalty + boost<br><br>P = 0.25 (懲罰係數)<br>B = 0.55 (提升係數)
        end
        
        Reranker->>Reranker: 按 _rerank_score 降序排序
        Reranker-->>search_service.py: 返回重排後結果 (top_k 筆)
    end

    rect rgb(245, 255, 250)
        Note over search_service.py: 8️⃣ Link 去重合併
        search_service.py->>search_service.py: _merge_duplicate_links(reranked_results)
        
        loop 遍歷重排結果
            alt 相同 Link 已存在
                search_service.py->>search_service.py: 合併 content (用 \n---\n 分隔)
                search_service.py->>search_service.py: 合併 all_ids 列表
                search_service.py->>search_service.py: 累加 token 計數
                Note over search_service.py: 保留最高分文檔的 metadata
            else 新 Link
                search_service.py->>search_service.py: 加入結果列表
            end
        end
        
        search_service.py->>search_service.py: 截取前 limit 筆
    end

    rect rgb(250, 250, 250)
        Note over search_service.py: 9️⃣ 建構回應
        search_service.py->>search_service.py: _build_response(intent, results, traces)
    end

    search_service.py-->>Agent: 返回搜尋結果 {<br>  status: "success",<br>  intent: {...},<br>  results: [...],<br>  final_semantic_ratio: 0.8,<br>  mode: "semantic",<br>  traces: [...]<br>}

