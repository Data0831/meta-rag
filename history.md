# Project History

## 2025-12-15
完成階段一基礎建設。初始化專案目錄結構 (`src`, `data`, `database`) 與環境設定 (`requirements.txt`, `.env`)。使用 Pydantic 建立資料模型 (`src/schemas.py`) 並修正欄位缺漏。實作資料攝取邏輯 (`src/ingestion.py`)，成功讀取 `result.json` 並完成 Schema 驗證。更新 `task.md` 標記進度為完成。

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
