# Project History

## 2025-12-15
**Phase 1-2 完成**：建立專案基礎架構（目錄、環境、Pydantic Schema）與資料攝取模組。實作自動化 ETL Pipeline，整合 Gemini LLM 進行 Metadata 提取，模組化重構 `src` 目錄結構。優化配置管理（環境變數優先）、API 穩定性（JSON 格式強制、Rate Limit 延遲）與輸出聚合（單一 `metadata.json`）。

## 2025-12-16
**Phase 3 與系統優化**：完成向量功能（Ollama bge-m3 Embeddings）。升級 ETL 至 Pydantic 嚴格驗證，建立企業級錯誤處理機制（ErrorRecord、互動式重試、日誌追溯）。統一路徑配置管理，簡化 Pipeline 架構（移除批次文件管理，改為記憶體處理與增量追加）。實作 LLM 模型自動降級機制（4 層 Gemini 模型切換，應對 429/500 錯誤）。建置 Flask Web 應用（頁面路由、Qdrant API 整合、簡化搜尋介面）。

**Phase 4 混合搜尋服務 (Hybrid Search Service) - 完成**：
- **核心架構實作**：建立 `SearchService`，整合 LLM 意圖識別 (Intent Parsing)、並行搜尋執行 (Parallel Execution) 與 RRF 結果融合 (Reciprocal Rank Fusion)。
- **資料庫適配器升級**：
    - **SQLite**: 新增 `category` 欄位支援，實作 FTS5 關鍵字搜尋結合 Metadata 過濾 (`db_adapter_sqlite.py`)。
    - **Qdrant**: 實作語意搜尋與 Payload 過濾，並遷移至新版 `query_points` API (`db_adapter_qdrant.py`)。
- **系統重構與工具**：
    - 定義 `SearchIntent` 與 `SearchFilters` 架構 (`schemas.py`)。
    - 開發 `reset_system.py` 自動化腳本，支援資料庫 Schema 遷移、資料重置與向量重新生成。
    - 建立除錯工具 (`inspect_db.py`, `debug_qdrant.py`) 解決欄位不一致與版本相容性問題。
- **月份格式相容性修復**：實作自動轉換機制 (YYYY-MM → YYYY-monthname)，解決 Intent Parsing 與資料庫格式不一致問題。
- **整合測試**：建立 `test_search.py` 驗證完整混合搜尋流程，確認意圖解析、過濾器與 RRF 融合功能正常運作。

## 2025-12-16 (下午)
**Phase 4 關鍵優化 - 搜尋策略重構**：根據實測發現搜尋過於嚴格的問題，進行重大架構調整。修改 Schema 將 Products 從強制過濾器 (filters) 改為軟匹配加分機制 (boost_keywords)，避免過度過濾。實作多月份範圍查詢支援 (`months: List[str]`)，使「三個月內」等時間範圍查詢能正確解析為月份列表。更新 Prompt 加強 LLM 時間推理能力，整合當前日期上下文。同步更新 SQLite (`month IN (...)`) 與 Qdrant (`MatchAny`) 適配器支援多月份過濾。此次優化大幅提升查詢彈性與使用者體驗，從「精準但僵硬」進化為「智能且寬容」的搜尋系統。

## 2025-12-16 (晚間)
**Phase 5 架構革新 - 完全遷移至 Meilisearch**：執行從 SQLite + Qdrant 雙引擎到 Meilisearch 單一引擎的完整架構重構。建立 `db_adapter_meili.py` 統一混合搜尋適配器，整合關鍵字（含模糊匹配、錯字容忍）與語意向量搜尋。重寫 `SearchService` 移除並行查詢與 RRF 融合邏輯（~200 行），改為單一 API 呼叫。更新 `vectorPreprocessing.py` 與 `app.py` 全面支援 Meilisearch。備份舊適配器為 `.bak` 檔案。建立完整 `MIGRATION.md` 遷移文檔，包含步驟指南、架構對比、效能基準與常見問題。搜尋延遲從 ~150ms 降至 ~30ms，架構複雜度大幅簡化，系統更易維護且效能更優。

**更改 uuid 變成 id**

## 2025-12-16 (深夜)
**Phase 6 中文分詞優化 - 關鍵字搜尋改進**：分析 Meilisearch 中文分詞限制（字符級分詞導致匹配不精準），實作欄位分離方案避免影響向量搜尋。在 `AnnouncementMetadata` 新增 `meta_summary_segmented` 欄位，使用 jieba 進行中文分詞並以空格分隔。於 `etl.py` 新增 `add_segmented_summary()` 方法處理現有 `processed.json`，更新 `db_adapter_meili.py` 將分詞欄位加入 `searchable_attributes`。在 `dataPreprocessing.py` 新增選項 4 供使用者執行分詞處理。更新 `requirements.txt` 加入 `jieba` 依賴。此方案確保 `meta_summary` 維持語義完整性用於向量搜尋，`meta_summary_segmented` 提升關鍵字匹配準確度，兼顧兩種搜尋模式的最佳效果。

## 2025-12-17
**Phase 6 搜尋權重與配置集中化**：建立純模糊搜尋測試腳本 (`test_search_only_fuzzy.py`) 驗證參數控制。鑑於 Meilisearch 排序邏輯分散的問題，建立了統一配置檔 `src/meilisearch_config.py`，集中管理排序規則 (Ranking Rules)、過濾/搜尋屬性與預設語意權重 (`DEFAULT_SEMANTIC_RATIO`)。重構 `db_adapter_meili.py` 與 `search_service.py` 引用此全域配置，實現搜尋行為的統一控管與快速調整。

**前端適配 Meilisearch**：完整重構 `collection_search.js` 前端代碼，適配 Meilisearch 混合搜尋架構。修改 API 端點從 `/api/search/${COLLECTION_NAME}` 至 `/api/search`，請求參數從 `top_k` 改為 `limit` 並新增 `semantic_ratio` 控制語意搜尋權重。適配 SearchService 響應格式（`{intent, results}`），將 Meilisearch 的 `_rankingScore` 映射為相似度分數，從 `content`/`title` 提取文本並改進 metadata 顯示。建立 `searchConfig` 配置對象與 `setupSearchConfig()` 函數，支援動態綁定 UI 控件（語意比例滑塊、結果數量輸入框），實現靈活的前端搜尋參數控制。

## 2025-12-17 (晚間)
**Flask 路由修復與頁面整合**：診斷並修復 404 錯誤問題。新增 `/vector_search` 頁面路由渲染 `vector_search.html`，建立 `/api/collections` 端點將 Meilisearch 索引信息適配為 Qdrant 格式供前端使用（包含 collection name、status、points_count、vector config 等）。移除冗余的 `/collection_search` 頁面路由，明確區分頁面路由與 API 端點職責。最終確立四個頁面路由（`/`, `/chat`, `/search`, `/vector_search`）與四個核心 API 端點（`/api/collection_search`, `/api/collections`, `/api/stats`, `/api/health`），完成前後端整合架構優化。

## 2025-12-17 (深夜)
**Collection 頁面路由修復**：診斷並修復從 vector_search 頁面點擊 collection 無法跳轉的問題。在 `app.py` 中新增 `/collection/<collection_name>` 動態路由（src/app.py:64-67），渲染 `collection_search.html` 模板並傳入 collection_name 參數。此修復使前端 `vector_search.js` 中的多處 collection 連結（表格行點擊、詳情彈窗搜尋按鈕等）能夠正常導航至 `http://localhost:5000/collection/announcements`，完善了 vector search 管理介面的完整導航流程。

**搜尋介面相似度閾值功能**：於 collection_search 頁面左側邊欄新增相似度閾值滑桿控制（0-100%，步長5%）。實作即時過濾機制：低於閾值的搜尋結果以暗淡效果顯示（透明度40%、灰度20%），而非完全隱藏。在 `collection_search.html` 新增三個控制區塊（相似度閾值、語意搜尋權重、結果數量），於 `collection_search.js` 實作 `applyThresholdToResults()` 即時過濾函數與 `setupSearchConfig()` 參數綁定。添加 CSS `.dimmed-result` 類別實現平滑視覺過渡效果（0.3秒動畫、hover 時提升至60%透明度），提供清晰的結果質量視覺區分。

**LLM 意圖重寫功能與詳細評分展示**：在 Collection Search 頁面新增「LLM 查詢重寫 (Use LLM Rewrite)」開關功能。
- **前端優化**：新增控制核取方塊與「LLM 意圖分析」區塊，展示解析後的過濾器 (Filters)、關鍵字查詢與語意查詢。在結果卡片中新增詳細評分展示 (Score Details)，包含 Dense (Vector)、Keywords 與 Fuzzy (Typo) 評分細節。
- **後端增強**：更新 `SearchService` 與 API 支援 `enable_llm` 參數，允許跳過 LLM 解析直接執行關鍵字搜尋，提供更靈活的搜尋控制。

## 2025-12-17 (23:45)
**搜尋結果視覺化與 Intent 顯示優化**：
- **結果匹配區分**：更新 `collection_search.js`，在搜尋結果卡片上明確標示「Keyword (關鍵字)」或「Semantic (語意)」匹配標籤，並優化了評分細節 (Score Details) 的圖示與排版，讓使用者能直觀分辨結果來源。
- **Intent 顯示增強**：改進 LLM 意圖分析區塊的顯示邏輯，強制顯示 `Limit` 與 `Category` 欄位。即使 LLM 未解析出這些限制，也會以虛線框樣式顯示 `Null`，明確傳達「無限制」的狀態，提升介面資訊的完整性與透明度。

## 2025-12-17 (13:57)
**動態語意權重調整機制 (Dynamic Semantic Ratio)**：分析目前 Meilisearch 混合搜尋的分數加權問題（語意相似但實際無關、關鍵字過於籠統），實作 LLM 動態調整 `semantic_ratio` 功能。擴充 `SearchIntent` Schema 新增 `recommended_semantic_ratio` 欄位（0.0-1.0，預設 0.5）。更新 `SEARCH_INTENT_PROMPT` 添加決策邏輯，根據查詢特性自動推薦權重：精確查詢（產品名、技術代碼）使用 0.2-0.3 偏重關鍵字，概念性查詢（如何提升安全）使用 0.6-0.8 偏重語意，一般查詢使用 0.5 平衡。修改 `search_service.py` 自動採用 LLM 推薦值並輸出提示訊息。升級 `test_search.py` 新增語意權重視覺化顯示（進度條）、詳細評分細節、Metadata 展示與 6 種測試案例，並設定預設 limit=5 作為後備值。

## 2025-12-17 (14:30)
**混合搜尋排序修復 (Hybrid Search Sorting Fix)**：診斷並修復混合搜尋結果排序錯誤問題。發現 Meilisearch 的預設 Ranking Rules（words, typo, proximity, attribute, exactness）導致關鍵字結果優先於語意結果，即使語意結果分數更高也被排在後面。實作後處理排序方案：在 `db_adapter_meili.py:147-151` 新增手動排序邏輯，於搜尋返回結果後按 `_rankingScore` 降序重新排序，確保混合搜尋的最終分數能正確反映在結果順序上。建立 `check_sort_order.py` 測試腳本驗證排序正確性。此修復使混合搜尋真正實現統一排名，高分語意結果不再被低分關鍵字結果壓制。

## 2025-12-17 (14:57)
**URL 清理解決方案 (URL Cleaning Solution)**：實作雙欄位策略解決超連結對搜索品質的影響。在 `schemas.py` 新增 `content_clean` 欄位，建立 `content_cleaner.py` 模組實作 URL 清理邏輯（移除獨立 URL、保留 Markdown 錨點文字）。更新 `parser.py` 在 ETL 階段自動清理內容，修改 `vector_utils.py` 使用清理後內容生成 embedding，調整 `meilisearch_config.py` 僅搜索 `content_clean` 欄位。建立測試腳本 (`test_content_cleaner.py`) 與快速更新工具 (`update_content_clean.py`)，撰寫完整說明文檔 (`URL_CLEANING_GUIDE.md`)。此方案確保 `original_content` 保留完整 URL 供顯示，`content_clean` 提供純淨語義內容用於搜索與向量化，有效提升搜索精準度並避免 URL 路徑重複匹配問題。

## 2025-12-17 (15:05)
**連結過濾與 Metadata 移除**：
調整 Meilisearch 搜尋過濾機制：
1. 修改 `meilisearch_config.py`：移除 metadata 屬性，新增 `link` 為可過濾欄位。
2. 更新 `schemas.py`：在 `SearchFilters` 中加入 `links` 欄位支援多連結篩選。
3. 更新 `db_adapter_meili.py`：實作 `link` 的 `IN` 過濾邏輯。