sequenceDiagram
    participant SVC as search_service.py
    participant Reranker as keyword_alg.py (keyword weight)
    participant Agent as srhSumAgent.py

    Note over SVC: 接收平行搜尋後的批次結果 (Stage 2)

    rect rgb(255, 250, 245)
        Note over SVC,Reranker: 3. 跨查詢去重與重排 (Deduplicate & Rerank)
        SVC->>SVC: 合併所有子查詢結果，按文檔 ID 去重
        
        SVC->>Reranker: 執行關鍵字加權重排 (Keyword Reranking)
        Note over Reranker: 計算加權分數：<br>■ 關鍵字命中：標題/內容檢查 must_have_keywords<br>■ 加權公式：對命中者給予 Boost，未命中者給予 Penalty
        Reranker-->>SVC: 返回重排後 Top-K 筆結果
    end

    rect rgb(245, 255, 250)
        Note over SVC: 4. Link 去重合併 (Link Merging)
        loop 按 Link 進行彙整
            SVC->>SVC: 同網址文檔內容合併 (\n---\n 分隔)<br>累加 Token 數並保留最高分 metadata
        end
        SVC->>SVC: 截取最終 limit 筆數
    end

    SVC-->>Agent: 返回搜尋結果
    Note over Agent: 搜尋流程完成
