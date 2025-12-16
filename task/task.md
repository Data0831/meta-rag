# Microsoft Announcement RAG System - Project Tasks

## Overview
本文件追蹤專案開發進度與任務規劃。專案目標是建立一個基於 **Hybrid Search (SQLite FTS + Qdrant Vector)** 與 **LLM (Gemini)** 的公告檢索系統，並透過 Flask 提供 Web API 服務。

---

## Phase 1: Infrastructure & Ingestion (已完成)
> 建立基礎設施與原始資料處理流程。

- [x] **Task 1.1: Environment Setup**
    - [x] 建立 `src`, `data`, `database` 目錄結構
    - [x] 設定 `.env` 與 `requirements.txt`
- [x] **Task 1.2: Data Models (`src/schema/schemas.py`)**
    - [x] 定義 `AnnouncementMetadata` 與 `AnnouncementDoc` Pydantic models
- [x] **Task 1.3: Raw Data Ingestion (`src/ingestion.py`)**
    - [x] 實作 Markdown 解析器，將原始文檔轉換為 JSON 物件列表

---

## Phase 2: ETL & Metadata Extraction (已完成)
> 利用 LLM 從原始文本中提取結構化 Metadata。

- [x] **Task 2.1: LLM Client (`src/llm/client.py`)**
    - [x] 實作 OpenAI 介面相容的 Gemini Client
    - [x] 實作 Rate Limit 與重試機制 (Model Rotation)
- [x] **Task 2.2: Extraction Prompts (`src/llm/prompts.py`)**
    - [x] 設計 `METADATA_EXTRACTION_PROMPT`，確保輸出嚴格 JSON 格式
- [x] **Task 2.3: ETL Pipeline (`src/etl/pipeline.py`)**
    - [x] 實作 Batch Processing 機制
    - [x] 整合 `BatchProcessor` 與 `MetaExtraction` 流程
    - [x] 輸出 `processed/metadata.json` 與錯誤日誌

---

## Phase 3: Vector & Database Storage (已完成)
> 將處理後的資料寫入 SQLite 與 Qdrant。

- [x] **Task 3.1: Text Enrichment (`src/vector_utils.py`)**
    - [x] 實作 `create_enriched_text()`：組合 Title, Metadata, Summary 為語意文本
    - [x] 整合 Embedding API (Ollama `bge-m3`)
- [x] **Task 3.2: SQLite Adapter (`src/database/db_adapter_sqlite.py`)**
    - [x] 初始化資料庫與 FTS5 Virtual Table
    - [x] 實作 `insert_documents` (儲存原始內文與 JSON metadata)
- [x] **Task 3.3: Qdrant Adapter (`src/database/db_adapter_qdrant.py`)**
    - [x] 初始化 Collection (Vector Size: 1024)
    - [x] 實作 `upsert_documents` (儲存 Vector 與 Payload)

---

## Phase 4: Hybrid Search Service (已完成)
> 實作「意圖識別 + 混合搜尋」邏輯，提供精確檢索能力。

- [x] **Task 4.1: Search Intent Parsing (`src/llm/search_prompts.py` & `src/services/search_service.py`)**
    - [x] **Prompt Design**: 新增 `SEARCH_INTENT_PROMPT`，指示 LLM 將使用者口語轉換為結構化查詢物件。
        - Output Format: `{ "filters": {"month": "...", "category": "..."}, "keyword_query": "...", "semantic_query": "..." }`
    - [x] **Implementation**: 在 `SearchService` 中新增 `parse_intent(user_query)` 方法，呼叫 LLM 進行解析。

- [x] **Task 4.2: Filter Implementation**
    - [x] **SQLite**: 更新 `src/database/db_adapter_sqlite.py` 的 `search_keyword`，將 `filters` 轉換為 SQL `WHERE` 子句。
    - [x] **Qdrant**: 更新 `src/database/db_adapter_qdrant.py` 的 `search_semantic`，將 `filters` 轉換為 Qdrant `Filter` 物件 (Payload Filtering)。

- [x] **Task 4.3: RRF Fusion Logic (`src/services/search_service.py`)**
    - [x] 實作 `search(user_query)` 主流程：
        1. 呼叫 `parse_intent` 取得過濾條件與改寫後的查詢詞。
        2. 並行執行 `search_keyword` (SQLite) 與 `search_semantic` (Qdrant)。
        3. **RRF Algorithm**: 實作 Reciprocal Rank Fusion，合併兩邊結果並重新排序。
           - 邏輯：若 UUID 同時存在，分數疊加；若僅單邊存在，分數較低。
        4. 根據排序後的 UUIDs，從 SQLite 撈取 `original_content`。

- [x] **Task 4.4: Month Format Compatibility**
    - [x] 實作月份格式轉換機制 (YYYY-MM → YYYY-monthname)，確保 Intent Parsing 結果與資料庫格式一致。

---

## Phase 5: RAG Generation Service (待執行)
> 根據搜尋結果生成最終回答。

- [ ] **Task 5.1: Context Assembly (`src/services/rag_service.py`)**
    - [ ] 實作 `assemble_context(docs)`：將檢索到的多篇公告組合成 LLM 的 Context Window。
    - [ ] 處理 Context Limit，確保不超過 Token 上限。

- [ ] **Task 5.2: Answer Generation (`src/services/rag_service.py`)**
    - [ ] 定義 `RAG_ANSWER_PROMPT`：指示 LLM 根據提供的 Context 回答使用者問題，並引用來源。
    - [ ] 實作 `generate_answer(user_query, context)`。

---

## Phase 6: Flask API & Web Interface (新架構)
> 將系統封裝為 Web 服務。

- [ ] **Task 6.1: Flask App Setup (`src/app.py`)**
    - [ ] 初始化 Flask App 結構。
    - [ ] 設定 `config.py` (整合 Flask Config 與專案 Config)。
    - [ ] 建立 Application Factory Pattern (`create_app`)。

- [ ] **Task 6.2: API Routes (`src/routes/api.py`)**
    - [ ] `POST /api/search`
        - Input: `{ "query": "..." }`
        - Output: `{ "results": [ ...docs... ], "intent": {...} }` (回傳搜尋結果與解析後的意圖，供 Debug 用)
    - [ ] `POST /api/chat`
        - Input: `{ "query": "..." }`
        - Output: `{ "answer": "...", "sources": [...] }` (完整的 RAG 回答)
    - [ ] `POST /api/admin/etl` (Optional)
        - 觸發 ETL 流程的 API (需考慮執行時間長度，可能需搭配 Task Queue 如 Celery，初期可先用簡單的 Threading)。

- [ ] **Task 6.3: Frontend Integration (Optional)**
    - [ ] 建立簡單的 HTML/JS 介面測試 API。
    - [ ] 顯示 "Search Process"：展示 Intent 解析結果 -> 搜尋到的原始文檔 -> 最終 LLM 回答。

---

## Phase 7: Deployment & Optimization (未來規劃)
- [ ] Dockerize 應用程式 (Dockerfile & docker-compose.yml)。
- [ ] 評估是否引入 Redis 作為 Cache (快取常見查詢的 Intent 解析結果)。
