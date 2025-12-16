根據您的決定，我們將執行 **方案 A：完全遷移至 Meilisearch**。這會大幅簡化您的架構。

### 步驟 1: 環境準備 (Infrastructure)

1.  **啟動 Meilisearch 服務 (已完成)**
   

2.  **安裝 Python SDK(已完成)**

### 步驟 2: 資料適配器重寫 (Database Adapter)

刪除 `src/database/db_adapter_sqlite.py` 和 `src/database/db_adapter_qdrant.py`，建立一個新的統一 Adapter：

**建立 `src/database/db_adapter_meili.py`**

```python
import meilisearch
from typing import List, Dict, Any

class MeiliAdapter:
    def __init__(self, host="http://localhost:7700", api_key="masterKey"):
        self.client = meilisearch.Client(host, api_key)
        # 確保 index 存在並設定向量搜尋
        self.index = self.client.index('announcements')
        self._configure_index()

    def _configure_index(self):
        # 1. 設定可過濾的屬性 (Filterable Attributes)
        self.index.update_filterable_attributes([
            'month', 
            'metadata.meta_category', 
            'metadata.meta_audience',
            'metadata.meta_products'
        ])
        # 2. 開啟向量搜尋功能 (Hybrid Search)
        self.index.update_settings({
            "embedders": {
                "default": {
                    "source": "userProvided",  # 我們自己算 embedding 傳進去
                    "dimensions": 1024        # 配合您的 embedding model 維度
                }
            }
        })

    def upsert_documents(self, documents: List[Dict[str, Any]]):
        """
        documents 格式需包含:
        - id (原 uuid)
        - _vectors (原 vector, Meilisearch 要求的格式)
        - title, content, metadata...
        """
        # Meilisearch 批次寫入效率高
        self.index.add_documents(documents)

    def search(self, 
               query: str, 
               vector: List[float] = None, 
               filters: str = None, 
               limit: int = 20) -> List[Dict]:
        
        search_params = {
            "limit": limit,
            "filter": filters,
            "hybrid": {
                "semanticRatio": 0.5,  # 0.5 = 關鍵字與語義各半，可依需求調整
                "embedder": "default"
            }
        }
        
        if vector:
            search_params["vector"] = vector

        return self.index.search(query, search_params)['hits']
```

### 步驟 3: ETL Pipeline 修改 (`src/etl_pipeline.py`)

您需要調整資料輸出的格式，以符合 Meilisearch 的要求：

1.  **欄位更名：** 將 `uuid` 改為 `id`。
2.  **向量格式：** Meilisearch 接受 `_vectors` 欄位（注意是複數且有底線）。

```python
# 在 ETL 處理完 metadata 和 embedding 後
def transform_for_meilisearch(doc, embedding_vector):
    return {
        "id": doc["uuid"],  # 關鍵修改
        "title": doc["title"],
        "content": doc["content"], # 原始 Markdown
        "month": doc["month"],
        "link": doc["link"],
        "metadata": doc["metadata"], # 保持巢狀結構
        "_vectors": {
             "default": embedding_vector # 對應 adapter 設定的 embedder 名稱
        }
    }
```

### 步驟 4: 搜尋服務簡化 (`src/services/search_service.py`)

這是變動最大的地方，邏輯會變得非常簡單：

```python
from src.database.db_adapter_meili import MeiliAdapter

class SearchService:
    def __init__(self):
        self.db = MeiliAdapter()
        # LLM 解析器保持不變
        
    def search(self, user_query: str, current_date: str):
        # 1. LLM 解析 Intent (保持原樣)
        intent = self.llm_parser.parse(user_query, current_date)
        
        # 2. 轉換 Filter 語法 (Meilisearch Style)
        # 例如: "month IN ['2025-nov']"
        meili_filter = self._build_meili_filter(intent.filters)
        
        # 3. 取得向量 (如果需要 Hybrid)
        query_vector = self.embedding_model.encode(user_query)
        
        # 4. 單一呼叫搞定所有事
        results = self.db.search(
            query=intent.keyword_query,  # LLM 優化過的關鍵字
            vector=query_vector,
            filters=meili_filter
        )
        
        return results

    def _build_meili_filter(self, filters):
        conditions = []
        if filters.get('months'):
            months_str = ", ".join([f"'{m}'" for m in filters['months']])
            conditions.append(f"month IN [{months_str}]")
            
        if filters.get('category'):
            conditions.append(f"metadata.meta_category = '{filters['category']}'")
            
        return " AND ".join(conditions) if conditions else None
```

### 步驟 5: 清理舊程式碼

完成上述修改後，您可以愉快地刪除以下檔案/功能：
1.  🔥 `src/database/db_adapter_sqlite.py`
2.  🔥 `src/database/db_adapter_qdrant.py`
3.  🔥 `RRF Fusion` 相關的所有演算法函數
4.  🔥 SQLite 的 `.db` 檔案

### 總結
現在您的架構變成了：
`User Query` -> `LLM Intent` -> `Meilisearch (Hybrid)` -> `Results`

這個架構既支援您要的**精準關鍵字匹配**（Meilisearch 強項），也支援**語意搜尋**（透過傳入 `_vectors`），且完全不需要自己維護分詞或複雜的融合邏輯。