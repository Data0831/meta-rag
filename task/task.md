## 階段一：基礎建設與資料攝取 (Infrastructure & Ingestion)
**目標**：建立專案結構，成功讀取並解析原始 Markdown 資料，將其轉為 Python 物件。

*   [x] **Task 1.1: 專案環境初始化**
    *   建立資料夾結構 (`src/`, `data/`, `database/`)。
    *   建立 `.env` 檔案 (設定 `GEMINI_API_KEY`, `OPENAI_API_KEY`, `QDRANT_URL` 等)。
    *   建立 `requirements.txt` (包含 `qdrant-client`, `google-generativeai`, `openai`, `pydantic`, `sqlite-utils` 等)。
*   [x] **Task 1.2: 定義資料模型 (`src/schemas.py`)**
    *   使用 `Pydantic` 定義 `AnnouncementMetadata` Class (包含所有 spec 中提到的 meta 欄位)。
    *   定義 `AnnouncementDoc` Class (包含 raw content + metadata)。
*   [x] **Task 1.3: 實作資料攝取 (`src/ingestion.py`)**
    *   撰寫 `parse_markdown(file_path)` 函式。
    *   實作 **Natural Split** 邏輯：解析 Markdown List，將每個 JSON Object 提取為獨立的 Dict (title, link, content, month)。
    *   *驗證點*：執行程式能 print 出 141 筆乾淨的 Dictionary List。

## 階段二：LLM ETL 核心實作 (The Brain)

**目標**：利用 `gemini-balance` 專案將 Google Gemini API 封裝成的 **OpenAI 兼容格式**，建立自動化 ETL 流程。取代原本的手動 AI Studio 操作。

### 技術說明：使用 `openai` 套件連接 Gemini

由於 `gemini-balance` 專案的核心功能是將 Google Gemini API 封裝成 **OpenAI 兼容格式** ，因此最簡單且推薦的方式是直接使用 Python 的 `openai` 官方套件。
您不需要學習 Google 的原生 SDK，只需將 `base_url` 指向您的本地服務即可。

**Python 程式碼範例 (`src/llm/client.py` 參考)**：

```python
from openai import OpenAI
import os

# 初始化客戶端
client = OpenAI(
    # 重要：將 Base URL 指向您的 gemini-balance 容器地址
    # 如果要使用進階功能（如 Fake Stream），請改用 "http://localhost:8000/hf/v1"
    base_url="http://localhost:8000/openai/v1",
    
    # 這裡填入您在 .env 中 "ALLOWED_TOKENS" 設定的密碼，而非 Google 的原始 Key
    api_key=os.getenv("GEMINI_API_KEY", "sk-mysecrettoken123") 
)

def call_gemini(messages, model="gemini-2.5-flash"):
    try:
        response = client.chat.completions.create(
            # 模型名稱需對應 Gemini 的實際模型名稱，例如 gemini-2.5-flash
            model=model, 
            messages=messages,
            stream=False # ETL 通常不需要串流
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"發生錯誤: {e}")
        return None
```

#### 關鍵配置提醒

1.  **Base URL**: 必須是 `http://localhost:8000/openai/v1`（標準）。不要使用 Google 原廠的 URL。
2.  **API Key**: 程式碼中的 `api_key` **不是** Google 的 `AIzaSy...`，而是您在 `.env` 檔案中自定義的 `ALLOWED_TOKENS`。
3.  **Model Name**: 依然要填寫 Gemini 的模型名稱（如 `gemini-2.5-flash`）。

---

### 執行任務 (Tasks)

*   [x] **Task 2.1: LLM Client 封裝 (`src/llm/client.py`)**
    *   安裝 `openai` 套件：`pip install openai`。
    *   根據上述範例，實作 `LLMClient` 類別或函式庫。
    *   *驗證點*：撰寫一小段測試程式，確認能成功呼叫本地 API 並收到回應。
*   [x] **Task 2.2: 定義 ETL Prompt (`src/llm/prompts.py`)**
    *   將 System Prompt 定義為常數字串。
    *   Prompt 重點回顧：
        *   **Role**: Data Extraction Agent.
        *   **Input**: JSON List of announcements.
        *   **Output Rules**: Strict JSON Array, Traditional Chinese summary.
        *   **Fields**: `meta_date_effective`, `meta_products` (normalized), `meta_category`, `meta_impact_level`, `meta_summary` etc.
*   [x] **Task 2.3: 實作批次處理流程 (`src/pipeline/etl.py`)**
    *   **Input**: 引用 Phase 1 解析出的 `raw_data` (List of Dicts)。
    *   **Batching**: 將資料切分為每組 5-10 筆 (Batch Size 可調整)。
    *   **Execution**: 
        *   遍歷每個 Batch。
        *   建構 `user_message` (將 Batch 轉為 JSON string)。
        *   呼叫 `llm_client.call_gemini()`。
        *   取得回應後，使用 `json.loads()` 解析。
    *   **Merge**: 將所有解析後的 Metadata 與原始資料合併 (透過 ID 或索引對應)。
    *   **Output**: 產出完整的 `List[AnnouncementDoc]` 物件列表。


## 階段三：向量處理與儲存層 (Vector & Storage)
**目標**：實作「文本增強」，並將資料分別寫入 SQLite 與 Qdrant。

*   [x] **Task 3.1: 向量增強實作 (`src/vector_utils.py`)**
    *   實作 `create_enriched_text(doc)`：依照 spec 將 metadata 與 content 拼裝成字串。
    *   實作 `get_embedding(text)`：串接 Embedding API (Local ollama bge-m3)。
*   [ ] **Task 3.2: SQLite 適配器 (`src/db_adapter_sqlite.py`)**
    *   實作 `init_db()`：建立 FTS5 Virtual Table。
    *   實作 `insert_documents(docs)`：將 `title`, `content` (Index) 與 Metadata (Unindexed) 寫入。
*   [ ] **Task 3.3: Qdrant 適配器 (`src/db_adapter_qdrant.py`)**
    *   實作 `init_collection()`：設定 Vector Size 與 Distance (Cosine)。
    *   實作 `upsert_documents(docs, vectors)`：
        *   確保 ID 使用 UUID (與 SQLite 一致)。
        *   將原始 Metadata JSON 放入 Payload。
*   [ ] **Task 3.4: 執行完整 ETL (`src/main.py` - Mode: Ingest)**
    *   串聯 Phase 1, 2, 3，執行一次完整的資料寫入流程。

## 階段四：混合檢索服務 (Hybrid Search Service)
**目標**：實作檢索邏輯，提供統一的搜尋介面。

*   [ ] **Task 4.1: SQLite 關鍵字搜尋 (`src/db_adapter_sqlite.py`)**
    *   實作 `search_keyword(query, filters)`：利用 FTS5 語法進行全文檢索與 Metadata 過濾。
*   [ ] **Task 4.2: Qdrant 語意搜尋 (`src/db_adapter_qdrant.py`)**
    *   實作 `search_semantic(vector, filters, top_k)`：執行向量相似度搜尋。
*   [ ] **Task 4.3: 混合檢索邏輯 (`src/search_service.py`)**
    *   定義搜尋介面 `search(user_query, mode="hybrid")`。
    *   (選項 A - 簡單版) 僅使用 Vector Search + Pre-filtering。
    *   (選項 B - 進階版) 同時查詢 SQL 與 Vector，使用 Reciprocal Rank Fusion (RRF) 合併結果。
    *   *建議*：先做選項 A (Qdrant 的 Payload Filter 功能很強大，通常足夠)。

## 階段五：RAG 生成與整合 (RAG & UI)
**目標**：將檢索到的 chunk 餵回給 LLM，生成最終回答。

*   [ ] **Task 5.1: 回答生成 (`src/llm_client.py`)**
    *   實作 `generate_answer(query, context_chunks)`。
    *   Prompt 設計：「請根據以下微軟公告回答使用者的問題...」。
*   [ ] **Task 5.2: 終端機介面 (`src/main.py` - Mode: Chat)**
    *   提供一個簡單的 `input()` 迴圈，讓使用者輸入問題，印出搜尋到的 Source Title 與 LLM 的回答。