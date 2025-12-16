# 技術規格書：Microsoft RAG 智慧檢索系統 (Meilisearch 版)

## 1. 專案目標 (Objectives)
本專案旨在建構一套高效能的 Microsoft 公告智慧檢索系統，並為未來擴充為對話機器人 (Chatbot) 奠定基礎。
*   **統一檢索 (Unified Search)**：採用 **Meilisearch** 作為單一核心引擎，同時處理「關鍵字精準匹配」、「中文分詞」、「屬性過濾」與「語意向量檢索 (Hybrid Search)」。
*   **自動化 ETL**：利用 LLM (Gemini) 自動提取高價值 Metadata 並進行文本增強，直接適配搜尋引擎索引結構。
*   **輕量化架構**：移除複雜的資料庫同步邏輯 (No SQL, No Fusion Code)，大幅降低維護成本與系統延遲。

## 2. 系統核心架構 (Core Architecture)

系統採用 **三層式架構 (3-Tier Architecture)** 以確保輕量與高效。

### 2.1 架構分層
1.  **應用層 (Application Layer)**
    *   負責與使用者互動 (CLI / Future Flask Web App)。
    *   *職責*：接收使用者自然語言查詢，轉發至 Service 層，並展示排序後的結果。
2.  **服務層 (Service Layer)**
    *   核心業務邏輯所在。
    *   **SearchService**: 負責「意圖識別」(Intent Parsing) 與「單一檢索呼叫」(One-Shot Search)。它將使用者的自然語言轉換為 Meilisearch 的 `filter` 表達式與 Hybrid Search 參數。
    *   **RAGService**: 負責 Prompt 組裝與 LLM 對話生成 (Answer Generation)。
    *   **ETLPipeline**: 負責資料清洗、Metadata 提取、向量計算 (Embedding)，並轉換為 Meilisearch Document 格式。
3.  **資料存取層 (Data Access Layer / DAL)**
    *   **`db_adapter_meili.py`**: 系統唯一的資料庫轉接器。封裝 Meilisearch SDK，處理 Index 設定、Documents Upsert 與 Hybrid Search 查詢。
    *   **Infrastructure**: 
        *   LLM Client (Gemini 2.5 Flash)。
        *   Embedding Model (bge-m3) - *由 ETL 端計算後傳入 Meilisearch*。
        *   **Meilisearch Engine**: 運行於 Docker，負責儲存與計算。

### 2.2 關鍵資料流 (Data Flow)
*   **寫入 (ETL)**: Raw Data -> LLM Extraction -> Embedding Calculation -> **Meilisearch Indexing** (JSON Documents with `_vectors`)。
*   **讀取 (Search)**: User Query -> LLM Intent Parser (Filters) -> **Meilisearch (Hybrid Search)** -> Result。

## 3. 專案檔案結構 (Project Structure)

```text
project_root/
├── data/
│   ├── datastructure/          # 資料結構定義文件
│   └── ...
├── src/
│   ├── config.py               # 全域設定 (Meilisearch Host, Key 等)
│   ├── meilisearch_config.py   # Meilisearch 設定
│   ├── dataPreprocessing.py    # 資料前處理 (ETL 入口)
│   ├── vectorPreprocessing.py  # 向量計算與 Index Reset 工具
│   ├── app.py                  # [Future] Flask 入口點
│   ├── services/               # [核心] 業務邏輯服務層
│   │   ├── __init__.py
│   │   ├── search_service.py   # 處理 Intent Parsing 與 Meili Search 呼叫
│   │   └── rag_service.py      # [Future] RAG 對話邏輯
│   ├── database/               # 資料庫轉接器 (DAL)
│   │   └── db_adapter_meili.py # [唯一] Meilisearch Adapter
│   ├── etl/                    # 資料處理流程
│   │   └── etl_pipe/           # Parser, Batch Processor, Meili Transformer
│   ├── llm/                    # LLM 客戶端封裝
│   └── schema/                 # Pydantic 資料模型
│       └── schemas.py          # 定義 MeiliDocument 與 SearchIntent
└── requirements.txt            # meilisearch, google-generativeai 等
```

## 4. 程式開發規範 (Engineering Conventions)

### 4.1 風格與格式
*   **Python 版本**: Anaconda (Python 3.10+)
*   **Imports**: 絕對路徑導入 (e.g., `from src.database import ...`)。

### 4.2 類型系統 (Typing)
*   全面使用 Python **Type Hints**。
*   資料交換使用 **Pydantic Models**，特別是 `MeiliDocument` Schema 須嚴格對應 Index 結構。

### 4.3 資料庫與索引設計原則 (Meilisearch Specific)
*   **Document Structure**: 
    *   `id`: 唯一識別碼 (原 id)。
    *   `title`, `content`: 全文檢索欄位。
    *   `metadata`: 巢狀物件，Meilisearch 自動攤平供過濾 (e.g., `metadata.category = 'Pricing'`)。
    *   `_vectors`: 儲存 Embedding 向量，啟用 Hybrid Search。
*   **Filterable Attributes**: 必須在 `db_adapter_meili.py` 初始化時明確設定 (如 `month`, `metadata.category`)，否則無法過濾。
*   **Idempotency**: 使用 `id` 作為 Primary Key，重複 `add_documents` 會自動執行 Upsert (覆蓋舊資料)，確保資料一致性。

### 4.4 擴充指南
*   未來新增過濾欄位時，僅需更新 `schemas.py` 並在 `db_adapter_meili.py` 的 `update_filterable_attributes` 列表中加入新欄位名稱即可，無需重寫搜尋邏輯。