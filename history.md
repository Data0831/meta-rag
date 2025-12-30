# Project History

## 2025-12-15 ~ 12-26 系統奠基與檢索升級
- **架構與部署**：遷移至 Meilisearch (30ms 延遲)，完成 Azure App Service 部署與 OpenAI Structured Outputs 兼容性修復。
- **檢索優化**：Link 去重合併技術，實作關鍵字精確加權重排 (Reranking) 與雙語擴展，並優化 Schema (年份/主標題) 適配新資料源。
- **UI/UX 重構**：前端模組化設計，採用 Tailwind CSS 與 Markdown 渲染，實作動態配置同步與 LLM 異常回退機制。
- **日誌開發**：全面導入 ANSI 彩色日誌，提升後端解析與 API 異常除錯的可辨識度。
  

## 2025-12-29
- **錯誤處理機制統一 (Unified Error Handling)**：修復 `fall_back=False` 參數無效問題。統一底層函式（`call_with_schema`、`get_embedding`、`meili_adapter.search`）返回格式為 dict，成功時 `{"status": "success", "result": ...}`，失敗時 `{"status": "failed", "error": ..., "stage": ...}`；在 `search_service.py` 的四個執行階段中檢查 `status` 欄位，根據 `fall_back` 參數決定是否提前返回錯誤；在 `_init_meilisearch` 中啟用 `health()` 檢查，確保 Meilisearch 連接成功後才繼續執行。同步更新 `vectorPreprocessing.py` 與 `test_search.py` 以適配新格式。
- **按 ID 增刪文檔功能 (ID-based CRUD)**：在 `db_adapter_meili.py` 新增 `delete_documents_by_ids()` 方法；在 `vectorPreprocessing.py` 實作智能同步系統，包含 `delete_by_ids()` (從 remove.json 讀取刪除清單)、`add_new_documents()` (只處理 Meilisearch 中不存在的新文檔並生成 embedding) 與 `auto_sync()` (一鍵刪除+添加)；新增選單選項 3 支援自動化同步；全面使用 ANSI 彩色輸出 (綠/黃/紅) 提升操作體驗，錯誤採用提示而非 exception。
- **向量預處理批次優化 (Batch Processing)**：在 `vectorPreprocessing.py` 中實作分批處理機制 (`BATCH_SIZE = 100`)。在 `process_and_write` 與 `add_new_documents` 流程中，每處理 100 筆文件即呼叫 `upsert_documents` 寫入 Meilisearch 並清空暫存 List。此舉有效降低處理數千筆資料時的記憶體占用，並避免大型 JSON 請求導致的 HTTP 超時或 Payload 過大問題。
- **Schema ID 欄位補強與過濾器語法修復**：在 `AnnouncementDoc` 新增 `id` 欄位以支援從 `data.json` 預生成 ID 的載入；修改 `transform_doc_for_meilisearch()` 移除 MD5 生成邏輯，改為直接使用 `doc.id`；修復 `get_documents_by_ids()` 的 Meilisearch 過濾器語法，從 `OR` 改為 `IN` 操作符（`id IN [...]`），解決版本兼容性問題。
- **關鍵字演算法優化 (Asymmetric Weighted Scoring)**：將線性加權改為非對稱評分模型 `$Final = Original \times (1 - P(1 - R)) + B \times R \times (1 - Original)$`，引入 `NO_HIT_PENALTY_FACTOR` (0.25) 與 `KEYWORD_HIT_BOOST_FACTOR` (0.55)。此改動能顯著提昇低分但命中關鍵字的結果（如 0.1 -> 0.6），同時對未命中但高語意分數的結果保留一定競爭力（如 0.9 -> 0.675），並確保分數嚴格限制在 [0, 1] 區間。新增 `docs/改變關鍵字權重.md` 提供參數調整指南。
- **空查詢回退機制 (Empty Query Fallback)**：修復使用者輸入無意義字串（如 "123"）導致 LLM 回傳空 `keyword_query` / `semantic_query` 的問題。在 `search_service.py` 新增檢測邏輯，若解析結果為空則自動回退使用原始 `user_query`，並在 Traces 中記錄警告。
- **統一配置管理系統 (Unified Configuration Management)**：建立前後端共享的配置架構。在 `config.py` 使用註解區隔「前端可調整變數」（`DEFAULT_SEARCH_LIMIT`, `DEFAULT_SIMILARITY_THRESHOLD`, `DEFAULT_SEMANTIC_RATIO`, `ENABLE_LLM`, `MANUAL_SEMANTIC_RATIO`, `ENABLE_KEYWORD_WEIGHT_RERANK`）與「純後端配置」（`PRE_SEARCH_LIMIT`, `NO_HIT_PENALTY_FACTOR`, `KEYWORD_HIT_BOOST_FACTOR`）；擴充 `/api/config` 端點返回所有前端可配置項；在前端 `config.js` 實作自動同步機制，載入後端配置並更新 UI 元素狀態；在 `index.html` 新增「啟用重排序 (Rerank)」checkbox；修改 `test_search.py` 移除硬編碼變數，改為從 `src.config` import。此架構確保單一真相來源（Single Source of Truth），前端調整通過無狀態請求參數傳遞，易於維護與擴展。

### 2025-12-29 UI 與搜尋參數顯示優化
優化搜尋結果與意圖顯示介面。將後端除錯參數整合至前端，全端更名 `enable_keyword_weight_rerank` 並修正分數顯示問題。搜尋卡片改為顯示 Match 分數（取小數點後兩位）與段落連結。重構意圖詳情區塊為三欄式佈局，新增權重視覺化條與子查詢顯示，提升介面美觀與資訊清晰度。- **關鍵字匹配邏輯增強 (Keyword Matching Enhancement)**：優化 `keyword_alg.py` 中的匹配演算法，新增 `_normalize` 方法以忽略關鍵字與文本中的空格、連字符與大小寫差異（例如 "Azure -- cloud" 可匹配 "azure cloud"），提升對不規則使用者輸入的兼容性與檢索召回率，並通過 reproduction script 驗證。


### 2025-12-29 前端錯誤處理完整化 (Frontend Error Handling)
建立完整的錯誤處理流程，使前端能正確顯示後端返回的錯誤信息。**後端 (app.py)**：在 /api/collection_search 檢查 search_service.search() 返回的 status 欄位，根據 stage 返回對應 HTTP status code（meilisearch/embedding/llm → 503 Service Unavailable，其他 → 500 Internal Server Error）並使用 print_red() 輸出錯誤日誌。**前端 API (api.js)**：解析錯誤 JSON 中的 stage 欄位，映射為友好的中文標籤（資料庫連線/向量服務/AI 服務/查詢解析/系統錯誤），格式化為「階段標籤 + 詳細訊息」的多行顯示。**前端渲染 (render.js)**：修正 llm_error → llm_warning 欄位名稱，與後端 search_service.py 保持一致。**UI 優化 (index.html)**：重構錯誤顯示區塊，添加錯誤圖示、支援多行顯示（whitespace-pre-line），改為左對齊 flexbox 排版，提升可讀性。此變更確保錯誤信息清晰傳遞給使用者，並區分不同錯誤階段。

### 2025-12-30 代理式與摘要迭代檢索 (Agentic RAG & Iterative Summarization)
實作 `SrhSumAgent` 專門負責摘要生成的迭代檢索流程。**架構解耦**：將 `summarize` 功能從 `RAGService` 剝離，改由 `app.py` 直接呼叫 Agent，原 `chat` 流程維持調用 `SearchService`。**迭代檢索迴圈 (Iterative Search Loop)**：Agent 執行「搜尋 -> LLM 相關性檢查 -> 查詢重寫」的循環；若初次搜尋結果無效，系統自動排除已知無效 IDs 並重寫查詢再次嘗試 (Max 2 Retries)，提升摘要的準確度。**底層支援**：`SearchService` 新增 `exclude_ids` 參數並建構 `NOT id IN [...]` 過濾器，防止無效文檔重複出現。
- **Meilisearch 配置修正 (Config Fix)**：為支援代理式搜尋的「排除已讀文檔」功能，修正 `meilisearch_config.py` 將 `id` 加入 `FILTERABLE_ATTRIBUTES`，並執行線上更新指令，解決 `invalid_search_filter` 錯誤。
- **測試工具增強 (Testing)**：在 `test_search.py` 新增 `test_agent_sum` 函式，並透過 monkey patch 攔截 `_rewrite_query` 實現互動式暫停 (Enter to continue)，便於開發者觀察 Agent 在迭代檢索過程中的決策邏輯。
