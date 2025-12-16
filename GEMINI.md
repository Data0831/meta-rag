# 技術規格書：Microsoft RAG 混合檢索系統

## 1. 專案目標 (Objectives)
本專案旨在建構一套高效能的 Microsoft 公告智慧檢索系統，並為未來擴充為對話機器人 (Chatbot) 奠定基礎。
*   **混合檢索 (Hybrid Search)**：結合 SQLite FTS5 的關鍵字精準度與 Qdrant 的語意理解能力，解決單一技術盲點。
*   **自動化 ETL**：利用 LLM (Gemini) 自動提取高價值 Metadata 並進行文本增強。
*   **服務化架構 (Service-Oriented)**：設計解耦的服務層 (Service Layer)，支援 CLI 工具與未來的 Flask Web API 共用核心邏輯。

## 2. 系統核心架構 (Core Architecture)

系統採用 **四層式架構 (4-Tier Architecture)** 以確保關注點分離。

### 2.1 架構分層
1.  **應用層 (Application Layer)**
    *   負責與使用者互動。目前為 CLI，未來可無縫擴充 Flask Web App。
    *   *職責*：接收請求、呼叫 Service 層、格式化輸出。
2.  **服務層 (Service Layer)**
    *   核心業務邏輯所在，協調不同的資料來源。
    *   **SearchService**: 執行「兩階段檢索」(Query Qdrant -> Get ids -> Fetch SQLite)。
    *   **RAGService**: 負責 Prompt 組裝與 LLM 對話生成。
    *   **ETLPipeline**: 負責資料清洗、Metadata 提取與寫入。
3.  **資料存取層 (Data Access Layer / DAL)**
    *   封裝對資料庫的具體操作。
    *   `db_adapter_sqlite.py`: 處理 FTS5 查詢與 CRUD。
    *   `db_adapter_qdrant.py`: 處理向量 Upsert 與 Payload Filtering。
4.  **基礎設施層 (Infrastructure)**
    *   LLM Client (Gemini 2.5 Flash)。
    *   Embedding Model (bge-m3 / OpenAI)。

### 2.2 關鍵資料流 (Data Flow)
*   **寫入 (ETL)**: Raw Data -> Chunking -> LLM Extraction -> Text Enrichment -> (SQLite + Qdrant)。
*   **讀取 (Search)**: User Query -> Embedding -> **Qdrant (Top-K ids)** -> **SQLite (Full Content)** -> Result。

## 3. 專案檔案結構 (Project Structure)

```text
project_root/
├── data/
│   ├── datastructure/          # 資料結構定義文件
│   │   └── schema_definitions.md
│   └── ...
├── database/                   # 實體資料庫檔案
├── src/
│   ├── config.py               # 全域設定
│   ├── main.py                 # CLI 入口點
│   ├── app.py                  # [Future] Flask 入口點
│   ├── services/               # [核心] 業務邏輯服務層
│   │   ├── __init__.py
│   │   ├── search_service.py   # 整合 Qdrant 與 SQLite 檢索邏輯
│   │   └── rag_service.py      # [Future] RAG 對話邏輯
│   ├── database/               # 資料庫轉接器 (DAL)
│   │   ├── db_adapter_qdrant.py
│   │   └── db_adapter_sqlite.py
│   ├── etl/                    # 資料處理流程
│   │   └── etl_pipe/           # 包含 Parser, Batch Processor
│   ├── llm/                    # LLM 客戶端封裝
│   └── schema/                 # Pydantic 資料模型
│       └── schemas.py
└── requirements.txt
```

## 4. 程式開發規範 (Engineering Conventions)

### 4.1 風格與格式
*   **Python 版本**: 3.10+
*   **Formatter**: 嚴格使用 `Black`。
*   **Imports**: 絕對路徑導入 (e.g., `from src.database import ...`)。

### 4.2 類型系統 (Typing)
*   全面使用 Python **Type Hints**。
*   資料交換強制使用 **Pydantic Models** (`src/schema/schemas.py`)，禁止傳遞裸字典 (Dict)。

### 4.3 資料庫設計原則
*   **Payload Strategy**: Qdrant Payload **不儲存內文**，僅儲存 Filter 用 Metadata。
*   **Lookup Pattern**: 所有詳細內文展示必須透過 id 回查 SQLite。
*   **Idempotency**: ETL 流程須具備冪等性 (Idempotent)，重複執行不應產生重複資料 (透過 id 檢查)。

### 4.4 擴充指南 (Flask Migration)
未來遷移至 Web App 時，應保持 `src/services` 與 `src/database` 不變，僅需新增 Flask Route 呼叫 `src/services` 中的方法即可。
