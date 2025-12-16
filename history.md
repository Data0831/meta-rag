# Project History

## 2025-12-15
**Phase 1-2 完成**：建立專案基礎架構（目錄、環境、Pydantic Schema）與資料攝取模組。實作自動化 ETL Pipeline，整合 Gemini LLM 進行 Metadata 提取，模組化重構 `src` 目錄結構。優化配置管理（環境變數優先）、API 穩定性（JSON 格式強制、Rate Limit 延遲）與輸出聚合（單一 `metadata.json`）。

## 2025-12-16
**Phase 3 與系統優化**：完成向量功能（Ollama bge-m3 Embeddings）。升級 ETL 至 Pydantic 嚴格驗證，建立企業級錯誤處理機制（ErrorRecord、互動式重試、日誌追溯）。統一路徑配置管理，簡化 Pipeline 架構（移除批次文件管理，改為記憶體處理與增量追加）。實作 LLM 模型自動降級機制（4 層 Gemini 模型切換，應對 429/500 錯誤）。建置 Flask Web 應用（頁面路由、Qdrant API 整合、簡化搜尋介面）。

**Phase 4 混合搜尋服務 (Hybrid Search Service)**：
- **核心架構實作**：建立 `SearchService`，整合 LLM 意圖識別 (Intent Parsing)、並行搜尋執行 (Parallel Execution) 與 RRF 結果融合 (Reciprocal Rank Fusion)。
- **資料庫適配器升級**：
    - **SQLite**: 新增 `category` 欄位支援，實作 FTS5 關鍵字搜尋結合 Metadata 過濾 (`db_adapter_sqlite.py`)。
    - **Qdrant**: 實作語意搜尋與 Payload 過濾，並遷移至新版 `query_points` API (`db_adapter_qdrant.py`)。
- **系統重構與工具**：
    - 定義 `SearchIntent` 與 `SearchFilters` 架構 (`schemas.py`)。
    - 開發 `reset_system.py` 自動化腳本，支援資料庫 Schema 遷移、資料重置與向量重新生成。
    - 建立除錯工具 (`inspect_db.py`, `debug_qdrant.py`) 解決欄位不一致與版本相容性問題。
