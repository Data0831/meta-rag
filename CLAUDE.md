# 技術規格書：Microsoft 公告混合檢索系統

## 1. 專案目標 (Objectives)
本專案旨在建構一套針對 Microsoft 公告資料（如 `page.example.json`）的高效能混合檢索系統。核心目標如下：
*   **精確與語意並重**：結合 SQLite FTS5 的關鍵字精確過濾（如日期、價格）與 Qdrant 的語意模糊搜尋（如「緊急變更」），解決單一檢索技術的不足。
*   **智慧資料處理**：透過 LLM ETL Pipeline 自動化提取高價值 Metadata，並進行文本增強（Text Enrichment），提升向量檢索的準確度。
*   **成本效益優化**：利用批次處理（Batch Processing）降低 LLM 呼叫成本與時間。

## 2. 系統核心架構 (Core Architecture)

本系統採用 **ETL Pipeline + Hybrid Search** 架構。

### 2.1 技術選型 (Tech Stack)
*   **ETL & Logic**: **Python** (負責資料清洗、LLM 串接、流程控制)。
*   **LLM Provider**: **GEMINI 2.5 flash**。
    *   *理由*：免費。
*   **Relational Database**: **SQLite (with FTS5 extension)**。
    *   *理由*：輕量級、無需伺服器，FTS5 模組足以處理精確關鍵字檢索與 Metadata 過濾。
*   **Vector Database**: **Qdrant**。
    *   *理由*：支援 Payload Filtering，適合混合檢索場景。
*   **Embedding Model**: **本地 **`bge-m3`**。
    *   *理由*：本地呼叫容易。

### 2.2 資料流架構
1.  **Raw Data Input**: 讀取 Markdown 原始檔。
2.  **Chunking**: 採用 **Natural Split** 策略，以單一 List Item (JSON Object) 為最小單位。
3.  **LLM ETL**: 批次傳送內容至 LLM，提取 Metadata 並標準化。
4.  **Vector Enrichment**: 將 Metadata 注入原始文本生成「合成語意文本（Synthetic Context String）」。
5.  **Storage**:
    *   Metadata 與原始文本寫入 **SQLite**。
    *   合成文本的 Vector 與 Metadata Payload 寫入 **Qdrant**。

## 3. 關鍵數據結構 (Data Structures)

### 3.1 核心實體：公告文件 (Announcement Document)
這是經過 ETL 處理後的標準化資料模型。

| 欄位名稱 (Key) | 類型 | 說明 | 來源 |
| :--- | :--- | :--- | :--- |
| `uuid` | String (UUID) | 唯一識別碼，用於關聯 SQLite 與 Qdrant | System Generated |
| `month` | String | 原始資料歸屬月份 (e.g., "2025-12") | Source |
| `title` | String | 公告標題 | Source |
| `original_content` | Text | 原始公告內文 (用於 RAG 最終生成) | Source |
| `meta_date_announced` | Date (ISO) | 公告發布日期 (YYYY-MM-DD) | LLM Extracted |
| `meta_date_effective` | Date (ISO) | 政策生效日期 (YYYY-MM-DD) | LLM Extracted |
| `meta_products` | List[String] | 相關產品 (正規化名稱, e.g., "Microsoft Sentinel") | LLM Extracted |
| `meta_category` | Enum | 公告類別 (Pricing, Feature, Retirement, Security) | LLM Extracted |
| `meta_audience` | List[String] | 受眾 (e.g., CSP, Reseller) | LLM Extracted |
| `meta_impact_level` | Enum | 衝擊等級 (High, Medium, Low) | LLM Extracted |
| `meta_action_deadline` | Date/Null | 行動截止日 | LLM Extracted |
| `meta_summary` | String | 單句摘要 | LLM Extracted |
| `meta_change_type` | String | 變更類型 (e.g., Deprecation) | LLM Extracted |

### 3.2 向量增強文本 (Enriched Text for Embedding)
**注意**：此結構僅用於生成 Embedding Vector，**不直接儲存**，但其邏輯至關重要。

```text
Title: {title}
Impact Level: {meta_impact_level}
Target Audience: {meta_audience}
Products: {meta_products}
Change Type: {meta_change_type}
Summary: {meta_summary}
Content: {original_content}
```

## 4. 模組職責說明 (Module Responsibilities)

### 4.1 資料攝取與分塊模組 (Ingestion & Chunking Module)
*   負責讀取 `page.json`。
*   執行 **Natural Split**：迭代解析 List 中的 JSON Object，確保每個 `{ title, link, content }` 被視為一個獨立的 Chunk，不進行硬性切分以保持語意完整。

### 4.2 Metadata 提取模組 (LLM ETL Module)
*   **Batch Request Management**：將 5-10 篇公告打包為單一 Prompt 發送給 LLM，降低 API 呼叫次數。
*   **Prompt Engineering**：定義 System Prompt，強制 LLM 輸出嚴格的 JSON 格式。
*   **Normalization**：負責清理 LLM 輸出（如日期格式統一為 `YYYY-MM-DD`，Null 值處理）。

### 4.3 向量處理模組 (Vector Processing Module)
*   **Text Enrichment**：實作 `create_embedding_text()` 函式，將 Metadata 與原始內文組合成富文本。
*   **Embedding Generation**：呼叫 Embedding API 將富文本轉換為向量。

### 4.4 儲存管理模組 (Storage Manager)
*   **SQLite Handler**：
    *   建立 FTS5 Virtual Table。
    *   將 `title`, `content` 寫入索引欄位。
    *   將 `products`, `month` 等 Metadata 寫入 `UNINDEXED` 欄位或輔助欄位。
*   **Qdrant Handler**：
    *   將 Vector 與 Payload (完整 Metadata JSON) 寫入 Collection。
    *   確保 ID 與 SQLite 中的 UUID 一致。

### 4.5 檢索服務模組 (Search Service)
*   提供統一查詢介面。
*   處理混合檢索邏輯：
    1.  解析使用者查詢（Keyword vs Semantic）。
    2.  執行 Vector Search（捕捉語意如 "urgent"）。
    3.  視情況套用 Metadata Filter（如 `filter = { meta_impact: "High" }`）。

## 5. 專案檔案結構 (Project Structure)

```text
project_root/
├── data/
│   ├── split/                         # 分批後的原始資料
│   ├── processed/                     # ETL 處理後的資料
│   │   └── processed.json             # 合併後的完整資料
│   ├── process_log/                   # ETL 錯誤日誌
│   ├── page.example.json              # 資料格式示例
│   └── page.json                      # JSON 格式原始資料
├── database/
│   ├── announcements.db               # SQLite 資料庫檔案
│   └── qdrant_storage/                # Qdrant 本地儲存
├── src/
│   ├── ETL/                           # ETL 模組
│   │   ├── etl_pipe/                  # ETL Pipeline 核心
│   │   │   ├── etl.py                 # 主控制器
│   │   │   ├── batch_processor.py     # 批次處理邏輯
│   │   │   ├── error_handler.py       # 錯誤處理與日誌
│   │   ├── spliter/                   # 資料分割
│   │   │   ├── parser.py              # JSON 解析
│   │   │   ├── splitter.py            # Natural Split
│   ├── llm/                           # LLM 核心邏輯
│   │   ├── client.py                  # LLM Client (支援 Pydantic Schema)
│   │   ├── prompts.py                 # System Prompts
│   ├── schema/                        # 資料定義
│   │   ├── schemas.py                 # Pydantic Schemas
│   ├── database/                      # 資料庫操作
│   │   ├── db_adapter_sqlite.py       # SQLite FTS5 封裝
│   │   ├── db_adapter_qdrant.py       # Qdrant 操作封裝
│   │   └── vector_utils.py            # Embedding 與文本增強
│   └── main.py                        # 程式進入點
├── .env                               # API Keys 設定
└── requirements.txt
```ps: 維護時請寫重點，不要過度展開