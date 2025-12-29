# Project History

## 2025-12-15 ~ 12-18
- **核心架構與 Meilisearch 遷移**：完成基礎 ETL Pipeline 與 Gemini Metadata 提取；執行重大決策遷移至 Meilisearch 單一引擎 (移除 SQLite/Qdrant)，搜尋延遲降至 ~30ms。
- **檢索策略優化**：引入 `jieba` 分詞、軟性強制關鍵字 (Soft Keyword Enforcement) 與雙語擴展技術，解決中英匹配與向量搜尋發散問題。
- **前端整合與系統輕量化**：發布 Collection Search 介面，支援動態語意權重調整；簡化資料結構為扁平化 `parse.json`，並清理大量廢棄代碼。

## 2025-12-19
- **前端重構 (Modularization)**：將龐大的 `search.js` 拆分為 6 個 ES6 模組 (Config/DOM/API/UI/Render/Main)，大幅提升代碼可維護性。
- **UI/UX 全面更新**：將介面升級為 Tailwind CSS 設計，引入 `marked.js` 支援 Markdown 渲染，並優化搜尋結果展示 (預設展開第一筆、改進卡片佈局)。
- **配置整合**：建立後端配置 API (`/api/config`) 與前端動態同步機制，統一管理相似度閾值與語意權重 (Slider 調整為 0-100 整數範圍)。
- **系統優化**：修正 `/collection_search` 路由重定向問題，並修復 LLM 過濾條件 (Year/Workspace/Links) 在前端的視覺化標籤顯示。

## 2025-12-23
- **Link 去重合併功能**：修改 `search_service.py` 實作 `_merge_duplicate_links()`，向 Meilisearch 請求多筆結果後按 `_rankingScore` 排序並拼接相同連結的內容，避免切塊重複輸出；同步更新 `archtect/search-flow.md`。
- **UI 優化與錯誤標示**：搜尋結果顯示配色的類型標籤 (Keyword/Semantic/Hybrid)，標題長度限縮；實作 LLM 調用失敗檢測，在前端顯示琥珀色警告橫幅並自動回退至基本搜尋模式。
- **搜尋模式邏輯修復**：修正手動設定與 LLM 建議權重的執行優先權，優化前端標籤判定的浮點數誤差處理。

## 2025-12-24
- **Azure OpenAI Structured Outputs 兼容性修復**：扁平化 `SearchIntent` Schema 結構（移除 nested class）以解決 Azure 400 錯誤；在 `client.py` 強制注入 `additionalProperties: false` 與 `required` 屬性。
- **Azure App Service 部署與修復**：支援動態 Port 綁定 (`PORT` 環境變數) 並優化啟動日誌；修正前端 `render.js` 讀取扁平化意圖數據的邏輯，新增「必含關鍵字」渲染與 LLM 建議權重百分比顯示。

## 2025-12-26
- **資料格式與搜尋升級**：因應新版資料來源格式，更新全線架構。
  - **Schema 擴充**：`AnnouncementDoc` 新增 `year` (年份)、`main_title` (主標題) 與 `heading_link` (錨點連結)，並將 `workspace` 改為可選欄位 (Optional) 以保持彈性。
  - **Meilisearch 配置**：更新 `meilisearch_config.py`，將 `year` 加入過濾條件 (`FILTERABLE_ATTRIBUTES`)，並新增 `main_title` 至搜尋欄位 (`SEARCHABLE_ATTRIBUTES`)，但設定為最低權重 (Lowest Priority) 以避免干擾核心關鍵字排序。
  - **轉接器適配**：修改 `db_adapter_meili.py` 資料轉換邏輯，確保新欄位正確映射至 Meilisearch 索引。
- **日誌美化 (Logging Aesthetics)**: 引入 `src.tool.ANSI` 工具，將 `SearchService`、`MeiliAdapter`、`app.py` 與 `client.py` 中的所有錯誤、警告、解析失敗、向量生成失敗及 API / LLM 呼叫異常訊息改為紅色輸出，提升後端除錯的可辨識度。
- **關鍵字精確匹配與分數重排 (Keyword Reranking)**：實作 Python 後處理層的關鍵字加權演算法 (`src/services/keyword_alg.py`)，使用 Regex 邊界匹配 (`\b`) 解決版本號與專有名詞精確判定問題；在 `search_service.py` 整合 `ResultReranker`，於 Meilisearch 返回後、合併前執行分數重排（全中 ×2.5、部分命中線性加分、未命中 ×0.81），並將 `PRE_SEARCH_LIMIT` 提升至 50 以擴大 Recall；新增四個可配置參數至 `config.py` (全中加權、部分命中係數、未命中懲罰、標題加權)。

## 2025-12-29
- **錯誤處理機制統一 (Unified Error Handling)**：修復 `fall_back=False` 參數無效問題。統一底層函式（`call_with_schema`、`get_embedding`、`meili_adapter.search`）返回格式為 dict，成功時 `{"status": "success", "result": ...}`，失敗時 `{"status": "failed", "error": ..., "stage": ...}`；在 `search_service.py` 的四個執行階段中檢查 `status` 欄位，根據 `fall_back` 參數決定是否提前返回錯誤；在 `_init_meilisearch` 中啟用 `health()` 檢查，確保 Meilisearch 連接成功後才繼續執行。同步更新 `vectorPreprocessing.py` 與 `test_search.py` 以適配新格式。
- **按 ID 增刪文檔功能 (ID-based CRUD)**：在 `db_adapter_meili.py` 新增 `delete_documents_by_ids()` 方法；在 `vectorPreprocessing.py` 實作智能同步系統，包含 `delete_by_ids()` (從 remove.json 讀取刪除清單)、`add_new_documents()` (只處理 Meilisearch 中不存在的新文檔並生成 embedding) 與 `auto_sync()` (一鍵刪除+添加)；新增選單選項 3 支援自動化同步；全面使用 ANSI 彩色輸出 (綠/黃/紅) 提升操作體驗，錯誤採用提示而非 exception。
- **向量預處理批次優化 (Batch Processing)**：在 `vectorPreprocessing.py` 中實作分批處理機制 (`BATCH_SIZE = 100`)。在 `process_and_write` 與 `add_new_documents` 流程中，每處理 100 筆文件即呼叫 `upsert_documents` 寫入 Meilisearch 並清空暫存 List。此舉有效降低處理數千筆資料時的記憶體占用，並避免大型 JSON 請求導致的 HTTP 超時或 Payload 過大問題。
- **Schema ID 欄位補強與過濾器語法修復**：在 `AnnouncementDoc` 新增 `id` 欄位以支援從 `data.json` 預生成 ID 的載入；修改 `transform_doc_for_meilisearch()` 移除 MD5 生成邏輯，改為直接使用 `doc.id`；修復 `get_documents_by_ids()` 的 Meilisearch 過濾器語法，從 `OR` 改為 `IN` 操作符（`id IN [...]`），解決版本兼容性問題。
