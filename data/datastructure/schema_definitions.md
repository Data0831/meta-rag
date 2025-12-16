# 資料結構定義 (Data Schema Definitions)

本文件定義系統核心資料模型、資料庫 Schema 以及向量負載結構。所有模組間的資料交換應嚴格遵守此定義。

## 1. 應用層模型 (Application Models)
定義於 `src/schema/schemas.py`，基於 Pydantic。

### 1.1 AnnouncementDoc (核心物件)
| 欄位 (Key) | 類型 | 說明 | 來源 |
| :--- | :--- | :--- | :--- |
| `id` | String (id) | 唯一識別碼 | System |
| `month` | String | 資料月份 (e.g., "2025-12") | Source |
| `title` | String | 公告標題 | Source |
| `link` | Optional[String] | 原始連結 | Source |
| `original_content` | String | 原始公告內文 | Source |
| `metadata` | Object | 詳見 `AnnouncementMetadata` | ETL |

### 1.2 AnnouncementMetadata (Metadata)
| 欄位 | 類型 | 格式/Enum | 說明 |
| :--- | :--- | :--- | :--- |
| `meta_date_effective` | Date | YYYY-MM-DD | 政策生效日 |
| `meta_date_announced` | Date | YYYY-MM-DD | 公告發布日 |
| `meta_products` | List[Str] | | 相關產品 |
| `meta_audience` | List[Str] | | 目標受眾 |
| `meta_category` | Enum | Pricing, Security... | 公告類別 |
| `meta_impact_level` | Enum | High, Medium, Low | 衝擊等級 |
| `meta_summary` | String | | 繁體中文摘要 |

---

## 2. 儲存層 Schema (Storage Schema)

### 2.1 SQLite (關聯式/全文檢索)
*   **Table**: `announcements`
*   **Module**: FTS5 Virtual Table

| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | TEXT | Primary Key |
| `title` | TEXT | **FTS Indexed** |
| `content` | TEXT | **FTS Indexed** (Original Content) |
| `metadata_json` | TEXT | Full JSON Dump |
| `date_effective` | TEXT | ISO String |
| `impact_level` | TEXT | Filter Field |

### 2.2 Qdrant (向量/語意檢索)
*   **Collection**: `announcements`
*   **Vector**: 1024 dim (`bge-m3`) via Enriched Text.

**Payload Structure (注意：不含內文)**
| Key | Type | Description |
| :--- | :--- | :--- |
| `id` | String | 關聯 SQLite 用 |
| `meta_impact_level` | String | Filterable |
| `meta_category` | String | Filterable |
| `meta_products` | List[Str] | Filterable |
| `...` | ... | 其他 Metadata |
