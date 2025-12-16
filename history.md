# Project History

## 2025-12-15
完成階段一基礎建設。初始化專案目錄結構 (`src`, `data`, `database`) 與環境設定 (`requirements.txt`, `.env`)。使用 Pydantic 建立資料模型 (`src/schemas.py`) 並修正欄位缺漏。實作資料攝取邏輯 (`src/ingestion.py`)，成功讀取 `page.json` 並完成 Schema 驗證。更新 `task.md` 標記進度為完成。

## 2025-12-15 (Phase 2 & Refactor)
完成 Phase 2 自動化 ETL 流程建置與程式碼重構。
1.  **自動化 ETL**：將原定手動 AI Studio 流程改為 Python 自動化腳本，透過 `openai` 套件串接本地 Gemini 服務，實作批次處理 (`src/pipeline/etl.py`) 與客戶端封裝 (`src/llm/client.py`)。
2.  **架構重構**：將 `src` 目錄模組化拆分為 `ingestion`, `llm`, `models`, `pipeline` 四大子目錄，並修正所有引用路徑。
3.  **文件更新**：同步更新 `task.md` 任務描述與 `GEMINI.md` 專案結構圖。

## 2025-12-15 (ETL Optimization)
優化 ETL 流程與 LLM 整合。
1.  **配置管理**：更新 `client.py` 優先讀取 `PROXY_` 環境變數，提升安全性。
2.  **穩定性增強**：API 呼叫強制啟用 `response_format={"type": "json_object"}` 確保 JSON 格式正確；批次處理增加 1 秒延遲避免 Rate Limit。
3.  **輸出聚合**：重構 Pipeline，將所有批次結果合併寫入單一 `data/processed/metadata.json`，簡化後續檢索流程。

## 2025-12-16
完成 Phase 3 向量功能。將 Embeddings 遷移至 Ollama (bge-m3)，實作 `vector_utils.py` 並加入測試。更新 `task.md` 與文件，修正 Enum 驗證錯誤。

## 2025-12-16 (ETL Schema 升級與錯誤處理)
升級 ETL Pipeline 至 Pydantic Schema 嚴格驗證。新增 `MetadataExtraction` 與 `BatchMetaExtraction` 模型，實作 `client.py` 的 `call_with_schema` 方法支援自動重試與 JSON Schema 轉換。建立企業級錯誤處理機制：`ErrorRecord` 記錄完整上下文（UUID、LLM 輸入/輸出），自動寫入 `data/process_log/*.error.json`；實作互動式重試流程與 `errorlist.json` 輸出，確保可追溯性。修正 `uuid` 與 `id` 欄位匹配問題。

## 2025-12-16 (路徑配置整合)
完成路徑配置統一管理。修復 `config.py` 語法錯誤並新增完整路徑常量（`DATA_DIR`, `PROCESSED_DIR`, `LOG_DIR`, `PAGE_JSON`, `SQLITE_DB` 等）。移除廢棄的 `split` 目錄相關配置與邏輯。重構 `etl.py` 使用集中式路徑配置，修正 `__init__` 參數定義，並簡化 `genMetaData` 方法從處理目錄改為處理單一輸入檔案，提升程式碼可維護性。

## 2025-12-16 (ETL Pipeline 架構簡化)
重構 ETL Pipeline，移除批次文件管理機制。`batch_processor.py` 改為純記憶體處理，移除 `load_batch`、`save_batch` 方法，將 `process_file` 重構為 `process_batch`。`etl.py` 新增 `load_parsed_data`、`load_processed_data`、`append_to_processed` 方法，實作增量處理流程：從 `parse.json` 載入資料、自動追蹤已處理 UUID 避免重複、依可配置批次大小（預設 10）分批處理、成功後立即追加至 `processed.json`。移除 `clean_processed_files`、`merge_processed_files`、`retry_failed_batches` 等冗餘方法。新增 `DEFAULT_BATCH_SIZE` 配置項至 `config.py`，提升容錯性與可恢復性。