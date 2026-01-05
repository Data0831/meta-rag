# Project History

## 2025-12-15 ~ 12-26 系統奠基與檢索升級
- **架構與部署**：遷移至 Meilisearch (30ms 延遲)，完成 Azure App Service 部署與 OpenAI Structured Outputs 兼容性修復。
- **檢索優化**：Link 去重合併技術，實作關鍵字精確加權重排 (Reranking) 與雙語擴展，並優化 Schema (年份/主標題) 適配新資料源。
- **UI/UX 重構**：前端模組化設計，採用 Tailwind CSS 與 Markdown 渲染，實作動態配置同步與 LLM 異常回退機制。
- **日誌開發**：全面導入 ANSI 彩色日誌，提升後端解析與 API 異常除錯的可辨識度。
  

## 2025-12-29 ~ 2026-01-02 代理式檢索開發與核心架構重構
- **Agentic RAG 核心**：實作 `SrhSumAgent` 達成「搜尋-判定-重寫-摘要」迭代流程，支援多階段流式輸出與歷史意識查詢改寫。
- **結構化摘要與 UI**：開發三段式摘要與引用超連結系統，完成前後端關鍵服務（`search.js` / `search_service.py`）之模組化拆解重構。
- **搜尋與效能優化**：精確化 `ResultReranker` 權重邏輯，實作非同步批次向量生成（Async Batch Embedding）與 ID-based 文檔異動優化，提升 ETL 與檢索穩定性。


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

### 2026-01-05 跨回合檢索合併與多樣性優化 (Cross-Round Merging & Diversity Optimization)
- **多階段去重合併**：實作 `SrhSumAgent._add_results` 統一入口，將初始與重試搜尋結果按 Link 進行終極合併。透過 `all_ids` 列表化追蹤所有採納片段，確保最終摘要包含最完整上下文，同時徹底解決跨回合網址重複問題。
- **檢索多樣性保障**：保留 `SearchService` 單次搜尋內的 Link 合併機制，確保 20 筆結果涵蓋最大化來源。Agent 改為僅排除已見片段 ID 而非整個 Link，兼顧「多樣性佔位」與「防止區塊遺漏」的召回平衡。

### 2026-01-05 公告資料 API 集中化 (Announcement Data API Centralization)
- **前端資料來源遷移**：重構 `announcement.js` 的 `loadData()` 函數，從原本直接 fetch 靜態 JSON 檔案改為統一從 `/api/config` 端點獲取 `announcements` 與 `websites` 資料，實現前後端資料流一致性。
- **後端讀取邏輯整合**：於 `app.py` 的 `/api/config` 路由中新增讀取 `announcement.json` 和 `website.json` 的邏輯，使用 `os.path.join` 構建跨平台路徑，檔案不存在或讀取失敗時回傳空陣列並透過 `print_red` 記錄錯誤。
- **配置集中管理**：在 `config.py` 新增 `ANNOUNCEMENT_JSON` 與 `WEBSITE_JSON` 路徑常數（指向 `src/datas/`），並於 `app.py` import 使用，確保所有資料來源路徑統一由配置檔管理，提升系統可維護性與配置一致性。

### 2026-01-05 關鍵字重排演算法優化 (Keyword Reranking Algorithm Optimization)
- **精確命中比例計算**：修正 `ResultReranker` 重複計分問題，將演算法優化為「唯一關鍵字命中數 / 總關鍵字數」比例模型。透過預先去重關鍵字清單並整合標題與內文命中判定，確保單一概念不因多次出現或欄位重複而過度加分，提升搜尋結果排序的穩定性與合理性。
- **測試驅動驗證**：建立 `test/test_keyword_rerank.py` 單元測試集，涵蓋關鍵字去重、部分命中、標題/內容單次計分及分數梯級加權等核心邏輯，確保加權機制在各種搜尋情境下均符合預期。

