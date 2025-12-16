# 系統架構與操作指南 (System Architecture & Operation Guide)

本文件旨在指導開發者或執行者了解專案目前的架構、程式進入點、核心功能與關鍵配置。

## 1. 程式進入點 (Entry Point)

主要執行腳本位於 `src/main.py`。

### 使用方式
```bash
# 確保位於專案根目錄，並已激活環境 (e.g., conda activate model)
python src/main.py [mode]
```

### 支援模式 (Modes)
*   **`ingest`**: **(目前主要功能)** 執行資料攝取流程。
    *   讀取 `data/processed/processed.json` (經 ETL 處理後的資料)。
    *   透過 Ollama (`bge-m3`) 生成向量。
    *   寫入 SQLite (Metadata & FTS5 Index)。
    *   寫入 Qdrant (Vector & Payload)。
*   **`chat`**: **(待實作)** 啟動互動式問答介面。

## 2. 關鍵環境變數 (.env)

執行前請確保 `.env` 檔案已設定以下關鍵參數：

| 變數名稱 | 說明 | 預設值/範例 |
| :--- | :--- | :--- |
| `PROXY_BASE_URL` | LLM 服務地址 (Gemini via OpenAI Interface) | `http://localhost:8000/openai/v1` |
| `PROXY_API_KEY` | 本地 LLM 服務的存取 Token | `sk-mysecrettoken123` |
| `QDRANT_URL` | 向量資料庫連線位置 | `http://localhost:6333` |
| `QDRANT_API_KEY` | (選填) Qdrant 金鑰 | `None` |
| `GEMINI_API_KEY` | (備用) 直接連線 Google API 時使用 | - |

## 3. 核心功能模組與路徑

### A. 資料攝取與分塊 (`src/ingestion/splitter.py`)
負責將原始 JSON 資料解析並切分為適合 LLM 處理的小批次。
*   **輸入**: `data/page.json`
*   **處理**:
    *   **解析 (`src/ingestion/parser.py`)**: 讀取原始資料，以單一 List Item 為最小單位 (Natural Split)，並生成 UUID。
    *   **分塊 (`src/ingestion/splitter.py`)**: 將清洗後的資料按固定數量 (預設 5) 分組，存為獨立檔案。
*   **輸出**: `data/split/*.json`
*   **執行指令**: `python src/ingestion/splitter.py`

### B. 資料處理 Pipeline (`src/pipeline/etl.py`)
負責將原始 JSON 資料轉換為帶有 Metadata 的結構化資料。
*   **輸入**: `data/split/*.json`
*   **處理**: 呼叫 LLM 提取 Metadata (日期、產品、影響等級等)。
*   **輸出**: `data/processed/processed.json`
*   **執行指令**: 若需重新執行 ETL，可單獨執行 `python src/pipeline/etl.py`。

### C. 向量處理 (`src/vector_utils.py`)
負責文本增強 (Enrichment) 與向量生成。
*   **Embedding Model**: 使用本地 **Ollama** 運行的 `bge-m3` 模型。
*   **Text Enrichment**: 將標題、摘要、產品等 Metadata 組合成 `Title: ...\nContent: ...` 格式以提升檢索準確度。
*   **前提**: 必須先安裝 Ollama 並執行 `ollama pull bge-m3`。

### D. 資料庫適配器
*   **SQLite (`src/db_adapter_sqlite.py`)**:
    *   儲存: `database/announcements.db`
    *   功能: 關鍵字搜尋 (FTS5)、Metadata 篩選。
*   **Qdrant (`src/db_adapter_qdrant.py`)**:
    *   儲存: Qdrant Server (Docker)
    *   Collection 名稱: `announcements`
    *   維度: `1024` (對應 bge-m3)。

## 4. 執行者注意事項 (Executor Checklist)

在執行 `python src/main.py ingest` 之前，請確認：

1.  **環境準備**:
    *   Python 環境已安裝 `requirements.txt` (包含 `ollama`, `qdrant-client` 等)。
    *   **Ollama** 服務已啟動，且已下載模型 (`ollama pull bge-m3`)。
    *   **Qdrant** 容器已啟動 (`docker run -p 6333:6333 ...`)。
    *   (若需重跑 ETL) **Gemini-Balance** 容器已啟動。

2.  **資料準備**:
    *   確認 `data/processed/processed.json` 存在且有資料。
    *   若無，請依序執行：
        1.  `python src/ingestion/splitter.py` (生成分塊資料)
        2.  `python src/pipeline/etl.py` (生成 Metadata 與處理後資料)

3.  **執行驗證**:
    *   執行後觀察 Log，應顯示 "Upserted X documents into SQLite" 與 "Upserted X points into Qdrant"。

## 5. 常見架構問答 (Architecture FAQ)

**Q1: 為什麼不直接將 JSON 格式轉為向量 (Embedding)？**
*   **雜訊干擾**: JSON 包含大量語法符號 (`{`, `}`, "`"`)，對語意模型來說是雜訊。
*   **檢索匹配**: 使用者的查詢通常是自然語言（如「找 Teams 的更新」）。將 JSON 轉換為「合成文本 (Synthetic Text)」(類似文章摘要格式) 能更有效地與自然語言查詢匹配。
*   **權重優化**: 合成文本能明確標示 `Title:`, `Summary:` 等欄位，讓模型更能捕捉重點。

**Q2: 向量生成 (Embedding) 是否包含原始內文？**
*   **是**。在 `src/vector_utils.py` 的 `create_enriched_text` 函式中，我們將 Metadata (標題、產品、影響等級) 與 `original_content` 組合在一起生成向量。這確保了搜尋時能同時考慮公告屬性與實際內容。

**Q3: Qdrant 與 SQLite 的分工為何？**
*   **Qdrant**: 儲存 **Vector** (含內文語意) 與 **Metadata Payload** (用於過濾)。不需儲存原始長文，以節省記憶體。
*   **SQLite**: 儲存 **原始完整內文 (Content)** 與 Metadata。用於最終顯示詳細資料與 FTS5 精確關鍵字搜尋。