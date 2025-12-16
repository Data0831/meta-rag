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