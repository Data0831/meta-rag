# Project History

## 2025-12-15 ~ 12-26 系統奠基與檢索升級
- **架構與部署**：遷移至 Meilisearch (30ms 延遲)，完成 Azure App Service 部署與 OpenAI Structured Outputs 兼容性修復。
- **檢索優化**：Link 去重合併技術，實作關鍵字精確加權重排 (Reranking) 與雙語擴展，並優化 Schema (年份/主標題) 適配新資料源。
- **UI/UX 重構**：前端模組化設計，採用 Tailwind CSS 與 Markdown 渲染，實作動態配置同步與 LLM 異常回退機制。
- **日誌開發**：全面導入 ANSI 彩色日誌，提升後端解析與 API 異常除錯的可辨識度。
  

## 2025-12-29
- **系統架構優化與功能增強**：統一全域錯誤處理機制與配置管理系統，實作 ID-based 文檔異動與分批預處理以提升效能，優化非對稱關鍵字加權演算法與意圖匹配邏輯，並重構前端 UI 與錯誤處理流程。

## 2025-12-30 代理式檢索與結構化摘要 (Agentic RAG & Structured Summary)
- **Agentic RAG 核心實作**：推出 `SrhSumAgent` 實作「搜尋 -> 判定 -> 重寫 -> 摘要」迭代流程，支援歷史意識查詢改寫與文檔排除，提升檢索覆蓋率與精準度。
- **架構與 API 重構**：整合搜尋邏輯至 Agent 主導，統一端點為 `/api/search` 並導入多階段狀態回傳（Stage-based streaming），提升系統反饋的透明度。
- **評分與過濾優化**：統一 Match 分數顯示邏輯，實作 `SCORE_PASS_THRESHOLD` 品質門檻與智慧篩選機制，並修正 Meilisearch 語法錯誤以確保檢索強健性。
- **結構化摘要與 UI 適配**：實作三段式摘要（簡答/詳答/總結）與引用超連結系統，優化檢索耗時計算視覺提示，提供層次分明且具備可信度的資訊呈現。

### 2026-01-02 搜尋檢索邏輯調整 (Search Logic Adjustment)
- **移除查詢字串加成 (Remove Query Augmentation)**：修改 `src/services/search_service.py`，移除在 Meilisearch 初步檢索階段將 `must_have_keywords` 重複附加於查詢字串後方的邏輯。此舉旨在簡化原始查詢，避免 Meilisearch 內建評分過度受到關鍵字重複出現的干擾。關鍵字的加權功能現在完全由服務層的 `ResultReranker` 負責，透過 `hit_ratio` 實現更精確且可控的二次分數加成，確保最終排名能真實反映文件與關鍵字的相關性。

### 2026-01-02 引用連結轉換修復 (Citation Link Conversion Fix)
- **修復內容總結引用連結 (Fix General Summary Citations)**：修正 `src/static/js/search.js` 的 `renderStructuredSummary` 函數，在處理「內容總結」(general_summary) 時補上遺漏的 `convertCitationsToLinks()` 調用。現在三段式摘要中的「詳細說明」與「內容總結」區塊都能正確將引用標記 `[1]`, `[2]` 等轉換為藍色上標超連結，點擊後於新標籤頁開啟來源文件，提升使用者體驗一致性與資訊可信度。

### 2026-01-02 前端模組化重構 (Frontend Modularization)
- **JavaScript 模組化架構**：將 `src/static/js/search.js` (778 行) 重構為模組化架構，拆分為 5 個獨立模組：`alert.js` (通知功能)、`citation.js` (引用轉換與摘要渲染)、`search-config.js` (搜尋配置 UI)、`search-logic.js` (搜尋執行邏輯)、`chatbot.js` (聊天機器人)。主檔案精簡為 18 行作為入口點，採用 ES6 import/export 模組系統，提升程式碼可維護性與可讀性。所有原有功能保持不變，同步更新 `CLAUDE.md` 專案文件以反映新架構。

### 2026-01-02 搜尋服務模組化重構 (Search Service Modularization)
- **搜尋服務層重構**：將 `src/services/search_service.py` 的 `search()` 方法（234 行）重構為模組化架構，拆分為 8 個職責單一的內部方法：服務初始化檢查、意圖解析、查詢候選構建、過濾器表達式構建、單查詢參數構建、結果去重、重排與合併、響應構建。主方法精簡至 72 行，採用異常拋出策略由主函數統一處理，對外 API 契約完全不變。提升程式碼可讀性、可測試性與可維護性，向後兼容現有測試。

### 2026-01-02 向量生成效能優化 (Vectorization Performance Optimization)
- **非同步批次處理 (Async Batch Embedding)**：優化 `src/database/vector_utils.py`，新增 `get_embeddings_batch` 函數，結合 Ollama AsyncClient 與 `asyncio.gather` 實作並行批次向量生成，顯著提升 ETL 資料處理量。
- **錯誤紀錄機制 (Error Logging)**：實作向量生成錯誤持久化邏輯，自動紀錄失敗資訊於 `src/error_log/` 目錄下之 JSON 檔案，確保資料處理過程具備可追溯性。

### 2026-01-05 硬體感知向量生成優化 (Hardware-Aware Vectorization Optimization)
- **硬體配置管理 (Dynamic Hardware Profiles)**：新增 `src/database/vector_config.py`，定義三套針對不同硬體環境（RTX 4050、16核 CPU、2c4t 低階設備）的向量生成參數模組。透過精確控制 `sub_batch_size` 與 `max_concurrency`，在高效能 GPU 上壓榨矩陣運算潛力，並在極低階設備上採取保守策略以防止記憶體溢出，兼顧效能與系統穩定性。
- **ETL 流程場景化切換**：重構 `data_update/vectorPreprocessing.py`，實作互動式硬體 Profile 選擇機制。在 `VectorPreProcessor` 中注入硬體感知參數，讓資料預處理流程能根據運算資源動態調整 Batch 大小與併發數。此優化大幅提升了系統在不同開發環境下的適配彈性，確保資料重構任務能以最優化路徑執行。

### 2026-01-05 統一日誌管理系統 (Unified Logging System)
- **LogManager 核心實作**：建立 `src/log/logManager.py` 統一管理三類日誌（client/search/chat），採用 JSON 格式與按小時分檔機制（`log_{YYYYMMDD_HH}.json`），日誌主目錄 `LOG_BASE_DIR` 可透過 `config.py` 環境變數配置（預設 `data_logs`），子目錄（client/search/chat）寫死於系統架構。
- **LLM 日誌遷移**：重構 `src/llm/client.py` 的 `_log_request()` 方法，移除手動日誌寫入邏輯，改為呼叫 `LogManager.log_client()`，簡化程式碼並確保日誌格式一致性。
- **API 端點日誌整合**：在 `src/app.py` 的 `/api/search` 與 `/api/chat` endpoint 整合日誌記錄，收集請求 IP（`request.remote_addr`）、完整 Headers、請求參數與回應結果。對於 streaming response，實作累積機制確保完整記錄所有階段回應。所有日誌寫入失敗僅透過 `print_red` 發出警告，不影響主流程，確保系統可追溯性與穩定性。

### 2026-01-05 用戶反饋系統 (User Feedback System)
- **反饋日誌擴展**：擴充 `LogManager` 支援第四類日誌 `feedback`，新增 `log_feedback()` 方法記錄用戶對搜尋摘要的讚/倒讚反饋，日誌儲存至 `data_logs/feedback/` 並包含反饋類型、查詢內容、搜尋參數等完整上下文。
- **後端 API 實作**：新增 `/api/feedback` POST 端點於 `src/app.py`，驗證 `feedback_type` 必須為 "positive" 或 "negative"，收集請求 IP 與 Headers，調用 `LogManager.log_feedback()` 完成日誌記錄後回傳成功狀態。
- **前端互動整合**：為 `index.html` 摘要區塊的讚/倒讚按鈕添加唯一 ID（`feedbackThumbUp`/`feedbackThumbDown`），於 `render.js` 實作 `setupFeedbackButtons()` 綁定 click 事件，點擊後透過 `api.js` 的 `sendFeedback()` 發送反饋請求，並使用 `alert.js` 顯示「感謝您的反饋」提示訊息。按鈕可重複點擊且互不影響，每次點擊均記錄獨立日誌條目。前端採用模組化架構，於 `search.js` 主入口調用 `setupFeedbackButtons()` 完成初始化。

### 2026-01-05 向量生成日誌整合 (Embedding Log Integration)
- **LogManager 擴展**：新增第五類日誌 `embedding`，實作 `log_embedding()` 單筆記錄與 `log_embedding_batch()` 批次記錄方法，支援向量生成錯誤的完整上下文（text/error/model/index）。新增內部方法 `_write_log_batch()` 提供批次寫入能力，日誌儲存至 `data_logs/embedding/log_YYYYMMDD_HH.json`。
- **向量工具重構**：移除 `src/database/vector_utils.py` 中的獨立日誌系統（`ERROR_LOG_DIR` 常數與 `log_embedding_error()` 函數），改用 `LogManager.log_embedding()` 統一管理。在 `get_embeddings_batch()` 與 `get_embedding()` 兩處錯誤處理邏輯中整合新日誌方法，確保向量生成失敗時自動記錄至統一日誌系統，提升系統可追溯性與維護性。

### 2026-01-05 前端錯誤處理優化 (Frontend Error Handling Enhancement)
- **錯誤顯示模組化**：於 `src/static/js/search-logic.js` 新增 `error_display()` 函數，封裝錯誤標題映射與 HTML 生成邏輯，接收 `error_stage` 和 `error` 參數，返回結構化的 `{title, content}` 物件，取代原本 36 行內嵌邏輯。
- **統一錯誤格式**：修改 `src/app.py` 的 `/api/chat` 與 `/api/search` 端點字數限制錯誤返回，統一為 `{status: "failed", error_stage: "input_validation", error: "..."}`，並於前端 `error_display()` 新增 `input_validation` 類型映射為「輸入驗證失敗」，確保後端錯誤與前端顯示格式一致。
- **HTTP 錯誤處理升級**：重構 `src/static/js/api.js` 的 `performSearchStream()` 錯誤捕獲邏輯，解析 HTTP 400 錯誤的 JSON 內容，將完整錯誤資訊附加至 `Error.errorData`，使 `search-logic.js` 能透過 `error_display()` 統一處理流式錯誤與 HTTP 錯誤，提升錯誤顯示一致性。
- **反饋按鈕條件顯示**：為 `src/templates/index.html` 的反饋容器添加 `feedbackContainer` ID，於 `search-logic.js` 實作條件控制邏輯：搜尋成功完成（`stage: "complete"`）時顯示，任何錯誤發生時（流式錯誤或 catch 錯誤）隱藏，確保用戶僅能對成功的搜尋結果提供反饋，避免對錯誤狀態誤操作。

### 2026-01-05 引用格式強制規範 (Citation Format Enforcement)
- **多重中括號標準化**：修正 LLM 摘要偶爾出現全形引用的問題。在 Prompt 中明確禁止全形中括號 `【】`，並在後端 `LLMClient` 解析 JSON 前與前端 `citation.js` 渲染前，同步實作 `replace()` 強制將所有全形標記轉換為標準半形 `[]`。這確保了引用超連結系統的穩定性與視覺一致性，徹底解決標籤解析失敗的問題。
