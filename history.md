# Project History

## 2025-12-15 ~ 12-26 系統奠基與檢索升級
- **架構與部署**：遷移至 Meilisearch (30ms 延遲)，完成 Azure App Service 部署與 OpenAI Structured Outputs 兼容性修復。
- **檢索優化**：Link 去重合併技術，實作關鍵字精確加權重排 (Reranking) 與雙語擴展，並優化 Schema (年份/主標題) 適配新資料源。
- **UI/UX 重構**：前端模組化設計，採用 Tailwind CSS 與 Markdown 渲染，實作動態配置同步與 LLM 異常回退機制。
- **日誌開發**：全面導入 ANSI 彩色日誌，提升後端解析與 API 異常除錯的可辨識度。
  

## 2025-12-29
- **系統架構優化與功能增強**：統一全域錯誤處理機制與配置管理系統，實作 ID-based 文檔異動與分批預處理以提升效能，優化非對稱關鍵字加權演算法與意圖匹配邏輯，並重構前端 UI 與錯誤處理流程。

### 2025-12-30 代理式與摘要迭代檢索 (Agentic RAG & Iterative Summarization)
實作 `SrhSumAgent` 專門負責摘要生成的迭代檢索流程。**架構解耦**：將 `summarize` 功能從 `RAGService` 剝離，改由 `app.py` 直接呼叫 Agent，原 `chat` 流程維持調用 `SearchService`。**迭代檢索迴圈 (Iterative Search Loop)**：Agent 執行「搜尋 -> LLM 相關性檢查 -> 查詢重寫」的循環；若初次搜尋結果無效，系統自動排除已知無效 IDs 並重寫查詢再次嘗試 (Max 2 Retries)，提升摘要的準確度。**底層支援**：`SearchService` 新增 `exclude_ids` 參數並建構 `NOT id IN [...]` 過濾器，防止無效文檔重複出現。
- **Meilisearch 配置修正 (Config Fix)**：為支援代理式搜尋的「排除已讀文檔」功能，修正 `meilisearch_config.py` 將 `id` 加入 `FILTERABLE_ATTRIBUTES`，並執行線上更新指令，解決 `invalid_search_filter` 錯誤。
- **測試工具增強 (Testing)**：在 `test_search.py` 新增 `test_agent_sum` 函式，並透過 monkey patch 攔截 `_rewrite_query` 實現互動式暫停 (Enter to continue)，便於開發者觀察 Agent 在迭代檢索過程中的決策邏輯。

### 2025-12-30 分數顯示與閾值判斷統一 (Score Display & Threshold Unification)
修正前端 `render.js` 的分數來源不一致問題。統一 Match 分數顯示與相似度閾值判斷皆使用 `_rerank_score`（優先），不存在時 fallback 至 `_rankingScore`。Match 分數改為無條件捨去小數的整數百分比格式（例如：85%），確保右上角顯示分數與 dimmed-result 閾值判斷邏輯完全一致，提升使用者體驗的直觀性與準確性。

### 2025-12-30 檢索耗時計算優化 (Search Duration Calculation Enhancement)
修改前端 `search.js` 將 Summary Agent retry 時間納入總檢索耗時。在 `performSearch()` 記錄總開始時間 `totalStartTime`，傳遞給 `generateSearchSummary()`。當 Agent 進入 `searching` 或 `retrying` 狀態時，時間顯示添加模糊效果（`blur(3px)`, `opacity: 0.5`）作為視覺提示。`complete` 狀態時計算總耗時（`performance.now() - totalStartTime`），更新 `searchTimeValue` 並移除模糊效果。所有時間計算在前端執行，涵蓋從用戶點擊搜尋到最終答案呈現的完整時間（包含網路傳輸、初始搜尋、Agent 處理與 retry）。

### 2025-12-30 Agentic Search 邏輯優化 (Accumulated Search & History-Aware Rewrite)
- **結果合併去重 (Result Accumulation)**：修改 `SrhSumAgent` 的 `generate_summary` 邏輯。在重試搜尋時，不再丟棄舊結果，而是將 `_rankingScore` 高於閥值 (`DEFAULT_SIMILARITY_THRESHOLD`) 的高分結果保留並合併 (Deduplicated by ID)。確保 LLM 在生成摘要時能獲得跨多次搜尋的最佳資訊集合。
- **具備歷史意識的重寫 (History-Aware Query Rewrite)**：新增 Prompt `retry_query_rewrite.py` 並傳入 `history` (過去使用過的查詢列表)。要求 LLM 在重寫查詢時必須參考歷史紀錄，避免生成重複或相似的關鍵字策略，從而提高重試搜尋的覆蓋率與成功率。

### 2025-12-30 重構與邏輯整合 (Refactoring & Logic Integration)
- **SearchService 整合重試邏輯**：將原 `SrhSumAgent` 的重試查詢改寫邏輯移入 `SearchService`。透過 `SEARCH_INTENT_PROMPT` 新增 `history` 參數，讓 LLM 在解析意圖時能參考過往失敗的查詢紀錄，直接生成具備差異化的新查詢策略，取代了原本獨立的 `retry_query_rewrite.py`。
- **架構簡化**：`SrhSumAgent` 不再負責調用改寫 Prompt，而是維護 `query_history` 並傳遞給 `SearchTool.search()`，实现了更 clean 的職責分離。單元測試已驗證此新流程的正確性。

### 2025-12-30 API 架構重構 - Agent 主導搜尋流程 (API Architecture Refactor)
將搜尋邏輯完全整合至 `SrhSumAgent`，移除獨立的 `/api/collection_search` 端點，改名 `/api/summary` 為 `/api/search`。Agent 內部自行執行首次搜尋（不再由前端傳入 `initial_results`），實現「搜尋 → 結果生成 → 判定 → 優化搜索 → 生成摘要」的完整流程。修正串流格式，將 `status` 欄位改為僅表示成功/失敗（`success`/`failed`），新增 `stage` 欄位表示執行階段（`searching`, `checking`, `summarizing`, `complete`）。`SearchTool.search()` 新增完整參數支援（`limit`, `semantic_ratio`, `enable_llm` 等），所有配置由前端透過 `/api/search` 傳遞給 Agent。

### 2025-12-30 搜尋過濾與閾值邏輯修正 (Search Filter & Threshold Logic Fix)
修正 `search_service.py` 中 Meilisearch exclude filter 語法錯誤（`NOT id IN` → `id NOT IN`），解決二次搜索無法正確排除已見文檔的問題。重構 `SrhSumAgent.generate_summary()` 的結果收集邏輯，移除基於 `DEFAULT_SIMILARITY_THRESHOLD` 的硬過濾條件，改為收集所有搜索結果並添加 `score_pass` 欄位標記品質，確保最終返回 `min(limit, len(collected_results))` 篇結果。將 `DEFAULT_SIMILARITY_THRESHOLD` 重命名為 `SCORE_PASS_THRESHOLD` 以明確其語意為「品質標記門檻」而非「過濾閾值」，避免開發與 AI 理解誤導。增強 `test_search.py` debug 功能，添加詳細的搜索調用追蹤、exclude_ids 顯示、filter 字符串檢查與結果詳情輸出。

### 2025-12-30 檢索反饋透明化增強 (Search Feedback Transparency)
針對 Agentic Search 流程進行透明化回傳改造。**重構 Agent 回傳邏輯**：將 `SrhSumAgent` 核心方法更名為 `run` 並移除舊有代碼，全面轉向生成器模式 (`yield`)；新增 `search_result` 階段事件，在每次執行搜尋（包含初始與重試）後即時回傳該次搜尋的結果清單、解析意圖與過濾器內容，讓前端能即時掌握 Agent 的中間思考過程與檢索細節。**測試工具升級**：`test_search.py` 改寫為 API Client 模式，支援 NDJSON 串流解析，並新增 `search_result` 階段的視覺化輸出，包含結果計數、意圖與前三筆文檔預覽，便於開發驗證。同時執行程式碼清理，移除冗餘註解以符合 coding style。

### 2025-12-30 相關性篩選與反饋優化 (Relevance Filtering & Feedback Enhancement)
重構 `_check_relevance` 方法實作智慧分數篩選邏輯：優先選擇 `score >= SCORE_PASS_THRESHOLD` 的高分資料，若不足 1 筆則取最高分的 `FALLBACK_RESULT_COUNT` 筆（須 >= `SCORE_MIN_THRESHOLD = max(0, SCORE_PASS_THRESHOLD - 0.2)`），對篩選結果再用 LLM 做二次驗證。新增 `filtered` 階段 yield 事件，即時顯示篩選資料數量、分數範圍與前三筆標題。移除冗餘的「參考歷史紀錄」訊息。在 `config.py` 新增 `SCORE_MIN_THRESHOLD` 與 `FALLBACK_RESULT_COUNT` 配置，提升篩選邏輯的可維護性與透明度。
### 2025-12-30 Agent 排序與測試顯示優化 (Sorting & Display Optimization)
- **排序邏輯一致化**：修正 `SrhSumAgent.run` 中的排序 key，優先使用 `_rerank_score` (關鍵字加權分數) 並以 `_rankingScore` 為 fallback。確保 Agent 最終選擇的摘要參考文件與搜尋引擎的加權邏輯完全一致。
- **測試工具詳細化**：恢復 `test_search.py` 的詳細文件顯示格式，並優化分數呈現：優先顯示 `Rerank Score` 隨後顯示 `Ranking Score`。保留 `main_title`、`link` 等關鍵欄位，便於開發者精準評估檢索品質與 Agent 決策依據。
