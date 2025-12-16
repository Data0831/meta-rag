# Database Architecture & Schemas

本專案採用 **Hybrid Search Architecture**，結合 **Relational Database (SQLite)** 的精確檢索能力與 **Vector Database (Qdrant)** 的語意搜尋能力。

## 1. 核心資料模型 (Data Models)

資料模型定義於 `src/schema/schemas.py`，作為系統各模組間的標準資料交換格式。

### 1.1 AnnouncementDoc (核心實體)
代表單篇公告的完整資料結構。

| 欄位 (Field) | 類型 (Type) | 說明 (Description) |
| :--- | :--- | :--- |
| `id` | `str` | 唯一識別碼 (Primary Key) |
| `month` | `str` | 資料歸屬月份 (e.g., "2025-12") |
| `title` | `str` | 公告標題 |
| `link` | `Optional[str]` | 原始連結 |
| `original_content` | `str` | 原始公告內文 |
| `metadata` | `AnnouncementMetadata` | LLM 提取的 Metadata 物件 |

### 1.2 AnnouncementMetadata (Metadata)
由 LLM 從原始內文中提取的結構化資訊。

| 欄位 (Field) | 類型 (Type) | 說明 (Description) | Enum / Format |
| :--- | :--- | :--- | :--- |
| `meta_date_effective` | `date` | 政策生效日期 | YYYY-MM-DD |
| `meta_date_announced` | `date` | 公告發布日期 | YYYY-MM-DD |
| `meta_products` | `List[str]` | 相關產品列表 | e.g. ["Microsoft Sentinel"] |
| `meta_audience` | `List[str]` | 目標受眾 | e.g. ["CSP", "Reseller"] |
| `meta_category` | `Category` | 公告類別 | Pricing, Security, Feature Update... |
| `meta_impact_level` | `ImpactLevel` | 衝擊等級 | High, Medium, Low |
| `meta_action_deadline` | `date` | 行動截止日 | YYYY-MM-DD |
| `meta_summary` | `str` | 繁體中文摘要 | |
| `meta_change_type` | `str` | 變更類型 | e.g. "Deprecation" |

---

## 2. 關聯式資料庫 (SQLite)

採用 SQLite FTS5 (Full-Text Search) 模組，負責高效的關鍵字檢索與資料儲存。

*   **Database File**: `database/announcements.db`
*   **Table Name**: `announcements`

### 2.1 Table Schema

| Column Name | SQLite Type | Source Field | Description |
| :--- | :--- | :--- | :--- |
| `id` | `TEXT` | `doc.id` | Primary Key |
| `month` | `TEXT` | `doc.month` | Partition Key (Logical) |
| `title` | `TEXT` | `doc.title` | **Indexed by FTS5** |
| `content` | `TEXT` | `doc.original_content` | **Indexed by FTS5** |
| `products` | `TEXT` | `doc.metadata.meta_products` | Stored as JSON string |
| `impact_level` | `TEXT` | `doc.metadata.meta_impact_level` | e.g., "High" |
| `date_effective` | `TEXT` | `doc.metadata.meta_date_effective` | ISO 8601 String |
| `metadata_json` | `TEXT` | `doc.metadata` | Full Metadata JSON Dump |

### 2.2 Full-Text Search Configuration
*   **Module**: FTS5
*   **Indexed Columns**: `title`, `content`
*   **Triggers**: 自動建立，確保 `INSERT`/`UPDATE`/`DELETE` 時索引同步更新。

---

## 3. 向量資料庫 (Qdrant)

負責語意檢索 (Semantic Search)，捕捉關鍵字無法涵蓋的語意關聯（如 "urgent" 關聯到 "High Impact"）。

*   **Storage**: `database/qdrant_storage` (Local Persistence)
*   **Collection Name**: `announcements`
*   **Vector Size**: `1024` (配合 `bge-m3` 模型)
*   **Distance Metric**: `Cosine`

### 3.1 Point Structure
每個 Point 包含 Vector 與 Payload。

#### Vector (Embeddings)
*   **Model**: `bge-m3` (via Ollama)
*   **Input Text**: "Enriched Text" (合成語意文本)
    *   為了增強檢索效果，Embedding 不是僅基於原始內文，而是將 Metadata 注入文本中：
    ```text
    Title: {title}
    Impact Level: {meta_impact_level}
    Target Audience: {meta_audience}
    Products: {meta_products}
    Change Type: {meta_change_type}
    Summary: {meta_summary}
    Content: {original_content}
    ```

#### Payload (Metadata for Filtering)
Payload 儲存完整 Metadata，支援 Qdrant 內部的 Filter 運算。

| Key | Type | Description |
| :--- | :--- | :--- |
| `id` | String | 與 SQLite id 一致 |
| `month` | String | |
| `title` | String | |
| `meta_impact_level` | String | Filterable Field |
| `meta_category` | String | Filterable Field |
| `meta_products` | List[String] | Filterable Field |
| `...` | ... | 其他所有 Metadata 欄位 |

> **Note**: Date 物件在 Payload 中會被轉換為 ISO 格式字串以符合 JSON 標準。

### 3.2 設計決策：Payload 儲存策略 (Storage Strategy)

**Qdrant Payload 中不儲存原始內文 (`original_content`)**，這是刻意的架構設計。

*   **原因 (Reasoning)**：
    1.  **效能優化**：Qdrant 預設將 Payload 載入記憶體 (RAM)。儲存大段內文會導致記憶體消耗過大，降低檢索效能。
    2.  **職責分離**：向量資料庫專注於「相似度計算」與「Metadata 過濾」；完整的資料儲存交由 SQLite 負責。
*   **檢索影響 (Retrieval Implication)**：
    *   **準確度**：**不受影響**。向量 (`Vector`) 已包含內文語意，檢索依然精準。
    *   **兩階段檢索 (Two-Stage Retrieval)**：程式邏輯需執行兩個步驟：
        1.  **Step 1 (Search)**：向 Qdrant 查詢，取得 Top-K 的 `id`。
        2.  **Step 2 (Lookup)**：使用 `id` 向 SQLite 查詢完整的 `title` 與 `content` 以呈現給使用者。

---

## 4. 資料流與同步 (Data Flow)

1.  **Ingestion**: 讀取原始 JSON，轉換為 `AnnouncementDoc` 物件。
2.  **Vector Processing**:
    *   呼叫 `create_enriched_text()` 生成合成文本。
    *   呼叫 Embedding API 生成 1024 維向量。
3.  **Storage Sync**:
    *   **SQLite**: 寫入 `announcements` 表格 (FTS Index 更新)。
    *   **Qdrant**: 寫入 Collection (Vector + Payload)。
4.  **Reset Mechanism**: 提供 `clear_all()` 功能，同時清空 SQLite 與 Qdrant 資料，確保開發測試環境的一致性。
