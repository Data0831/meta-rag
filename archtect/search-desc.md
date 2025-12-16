讓我用一個具體範例來說明完整的搜索流程：

  搜索流程範例

  假設用戶查詢："過去兩個月的高影響力安全公告"

  步驟 1: 意圖解析 (LLM)

  SearchService.parse_intent() 使用 LLM 將自然語言轉換為結構化意圖：

  SearchIntent {
    filters: {
      months: ["2025-10", "2025-11"],  # 過去兩個月
      category: "Security",            # 安全
      impact_level: "High"             # 高影響力
    },
    keyword_query: "安全公告",
    semantic_query: "高影響力的安全性公告通知"
  }

  步驟 2: 生成查詢向量

  src/services/search_service.py:140
  query_vector = vector_utils.get_embedding(intent.semantic_query)
  # 返回: [0.123, -0.456, 0.789, ...] (1024維向量)

  步驟 3: 構建過濾條件

  src/database/db_adapter_meili.py:238
  meili_filter = build_meili_filter(intent.filters)
  # 輸出: "month IN ['2025-october', '2025-november'] AND
  #        metadata.meta_category = 'Security' AND
  #        metadata.meta_impact_level = 'High'"

  步驟 4: Meilisearch 混合搜索

  src/database/db_adapter_meili.py:120-163
  self.meili_adapter.search(
      query="安全公告",                    # 關鍵字搜索
      vector=query_vector,                  # 向量搜索 (1024維)
      filters=meili_filter,                 # 過濾條件
      limit=5,
      semantic_ratio=0.5                    # 50% 關鍵字 + 50% 語意
  )

  步驟 5: 分數計算

  Meilisearch 內部執行以下計算：

  1. 關鍵字分數（基於 Ranking Rules）
  - words: 關鍵字匹配度（"安全公告" 在文檔中出現）
  - typo: 容錯匹配
  - proximity: 詞彙距離
  - attribute: 欄位權重（title > content）
  - exactness: 精確匹配獎勵

  2. 語意分數（向量相似度）
  - 計算查詢向量與文檔向量的餘弦相似度
  - 範圍: -1 到 1（越接近 1 越相似）

  3. 混合分數
  final_score = (1 - semantic_ratio) × keyword_score + semantic_ratio × semantic_score
              = 0.5 × keyword_score + 0.5 × semantic_score

  步驟 6: 返回結果

  src/database/db_adapter_meili.py:146
  {
    "hits": [
      {
        "id": "...",
        "title": "重大安全更新：Azure AD 漏洞修補",
        "month": "2025-november",
        "metadata": {
          "meta_category": "Security",
          "meta_impact_level": "High"
        },
        "_rankingScore": 0.9876    # ← 這就是分數！
      }
    ]
  }

  分數的意義

  - _rankingScore: 0.0 ~ 1.0 之間
    - >0.9: 高度相關（強烈匹配）
    - 0.7-0.9: 相關（中等匹配）
    - <0.7: 弱相關（低匹配）
  - 這個分數綜合考慮：
    - 關鍵字是否出現在 title 或 content
    - 語意上是否表達相同的概念
    - 過濾條件是否完全符合（符合才會返回）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 深度解析：關鍵字模糊比對與 Metadata 作用

### 一、關鍵字模糊比對機制

#### 1.1 Meilisearch Ranking Rules（排序規則）

從 `db_adapter_meili.py:63-72` 配置可見，Meilisearch 使用以下規則依序計算分數：

```python
ranking_rules = [
    "words",      # ① 詞彙匹配度（最重要）
    "typo",       # ② 容錯匹配
    "proximity",  # ③ 詞彙接近度
    "attribute",  # ④ 欄位權重
    "sort",       # ⑤ 自定義排序
    "exactness",  # ⑥ 精確匹配獎勵
]
```

**詳細說明：**

① **words**: 匹配查詢中的詞彙數量
   - 查詢："Azure OpenAI 價格"
   - 文檔 A 包含 3 個詞 → 高分
   - 文檔 B 只包含 1 個詞 → 低分

② **typo**: 容忍拼寫錯誤（Fuzzy Matching）
   - 允許最多 2 個字符差異
   - "Azrue" → 仍能匹配 "Azure"
   - "OpneAI" → 仍能匹配 "OpenAI"
   - ⚠️ 中文不支持 typo tolerance（因為是字符級分詞）

③ **proximity**: 詞彙在文檔中的距離
   - "Azure OpenAI" 連續出現 → 高分
   - "Azure ... (100字) ... OpenAI" → 低分

④ **attribute**: 欄位權重（由 searchable attributes 順序決定）
   ```python
   ["title", "content", "metadata.meta_summary"]
   ```
   - title 匹配 > content 匹配 > meta_summary 匹配

⑤ **sort**: 自定義排序（目前未使用）

⑥ **exactness**: 精確匹配獎勵
   - 完全匹配整個查詢詞 → 加分
   - "Azure OpenAI" 完整出現 > "Azure" 和 "OpenAI" 分散出現

#### 1.2 分詞機制（Critical）

**英文：**
- 按空格、標點符號分詞
- "Azure OpenAI Service" → ["Azure", "OpenAI", "Service"]

**中文：**
- **問題**: Meilisearch 預設使用 **Character-level tokenization**
- "價格更新公告" → ["價", "格", "更", "新", "公", "告"]
- 這會導致中文搜索精準度較低

**混合查詢：**
- "Azure OpenAI 價格" → ["Azure", "OpenAI", "價", "格"]

**⚠️ 當前架構的限制：**
目前未配置專業的中文分詞器（如 jieba），這會影響中文關鍵字搜索的精準度。

#### 1.3 單一查詢 vs 多次查詢

**重要觀念修正：**

從 `search_service.py:145-151` 可見：

```python
results = self.meili_adapter.search(
    query=intent.keyword_query,  # ← 單一查詢字符串
    vector=query_vector,
    filters=meili_filter,
    limit=limit,
    semantic_ratio=semantic_ratio,
)
```

**實際行為：**
- **不是**每個關鍵字分別搜索
- **是**將整個 `keyword_query` 字符串送入 Meilisearch
- Meilisearch 內部自動分詞並計算相關性
- **一次 API 調用**完成所有匹配

**範例：**
```python
keyword_query = "Azure OpenAI 價格"
# Meilisearch 內部處理：
# 1. 分詞: ["Azure", "OpenAI", "價", "格"]
# 2. 對每個 token 在 searchable attributes 中查找
# 3. 根據 ranking rules 計算總分
# 4. 返回排序結果
```

### 二、Metadata 在搜索中的實際作用

#### 2.1 Metadata 欄位分類

從 `db_adapter_meili.py:36-49` 配置：

```python
# 可過濾欄位（用於 filter）
filterable_attributes = [
    "month",
    "metadata.meta_category",
    "metadata.meta_audience",
    "metadata.meta_products",
    "metadata.meta_impact_level",
]

# 可搜索欄位（用於模糊搜索 + 語義搜索）
searchable_attributes = [
    "title",
    "content",
    "metadata.meta_summary"  # ← 唯一參與搜索的 metadata
]
```

#### 2.2 參與關鍵字搜索的欄位（Fuzzy Search）

**三個欄位參與 Meilisearch 的關鍵字搜索：**

```python
searchable_attributes = [
    "title",                      # ① 權重最高
    "content",                    # ② 權重中等
    "metadata.meta_summary"       # ③ 權重最低
]
```

**權重說明：**
- **title**：匹配到 title 中的關鍵字會獲得最高分數
- **content**：原始公告內容，英文為主
- **metadata.meta_summary**：LLM 生成的繁體中文摘要

**meta_summary 的獨特價值：**
- 原始 `content` 可能是英文或混合語言
- `meta_summary` 是純繁體中文，更符合中文查詢習慣
- 例如查詢「價格調整」時，即使 content 只有 "pricing update"，但 meta_summary 包含「價格調整」，仍能被檢索到

#### 2.3 參與向量搜索的欄位（Semantic Search）

**重要發現：向量化包含幾乎所有信息！**

從 `vector_utils.py:18-50` 的 `create_enriched_text` 函數：

```python
def create_enriched_text(doc: AnnouncementDoc) -> str:
    text = (
        f"Title: {doc.title}\n"
        f"Impact Level: {impact}\n"           # ✅ metadata
        f"Target Audience: {audience}\n"      # ✅ metadata
        f"Products: {products}\n"             # ✅ metadata
        f"Change Type: {change_type}\n"       # ✅ metadata
        f"Summary: {summary}\n"               # ✅ metadata
        f"Content: {doc.original_content}"    # ✅ content
    )
    return text  # 這段文字會被編碼為 1024 維向量
```

**這意味著：**
- 所有 metadata（products、audience、impact_level 等）都被編碼到向量中
- 語義搜索能夠理解這些結構化信息
- 例如：查詢 "Azure OpenAI 相關公告" 時，即使 content 沒提到 "Azure OpenAI"，但如果 `meta_products` 包含它，向量相似度仍會較高

#### 2.4 其他 Metadata 的作用（僅過濾）

**這些欄位 NOT 參與關鍵字搜索（但參與向量搜索）：**
- `meta_category`: 只用於過濾（`filters.category`）+ 向量搜索
- `meta_impact_level`: 只用於過濾（`filters.impact_level`）+ 向量搜索
- `meta_products`: 可過濾但未使用 + **向量搜索中有作用**
- `meta_audience`: 可過濾但未使用 + **向量搜索中有作用**

**關鍵字 vs 向量的差異：**
1. **關鍵字搜索（Fuzzy）：**
   - 查詢 "Azure OpenAI"
   - 只在 `title`, `content`, `meta_summary` 中查找這些詞
   - `meta_products` 中的 "Azure OpenAI" **不會**被匹配

2. **向量搜索（Semantic）：**
   - 查詢 "Azure OpenAI 相關公告"
   - 編碼為向量後與文檔向量計算相似度
   - `meta_products` 中的 "Azure OpenAI" **會**影響向量相似度
   - 語義上更接近的文檔會得到更高分數

**問題分析：**
1. **`meta_products` 在關鍵字搜索中缺席**
   - 已設為 filterable，但不 searchable
   - 查詢 "Azure OpenAI" 時，只能靠語義搜索（semantic_ratio = 0.5）
   - 如果用戶期望精確匹配產品名稱，可能效果不佳

2. **`meta_audience` 未充分利用**
   - 可能的應用："Show announcements for developers"
   - 但目前架構未支持這種查詢

### 三、LLM 生成的 Keywords 如何工作

#### 3.1 LLM 輸出結構

從 `search_prompts.py` 可見 LLM 生成三種查詢：

```python
SearchIntent {
    keyword_query: str,        # 用於關鍵字搜索
    semantic_query: str,       # 用於向量搜索
    boost_keywords: List[str], # 🚨 預期用於提升相關性（但未實現）
}
```

#### 3.2 Keyword Query 的處理

**實際使用：**
```python
# search_service.py:145
results = self.meili_adapter.search(
    query=intent.keyword_query,  # ← 例如 "Azure OpenAI 價格"
    ...
)
```

**Meilisearch 內部處理：**
1. 接收完整字符串 "Azure OpenAI 價格"
2. 自動分詞為 tokens
3. 在 `searchable_attributes` 中查找每個 token
4. 根據 ranking rules 計算分數

**不是多次查詢**，而是一次查詢包含多個 tokens。

#### 3.3 Boost Keywords 的問題（未實現功能）

**預期行為：**
```python
# 從 search_prompts.py:44-47
boost_keywords: ["Azure OpenAI", "AI 雲合作夥伴計劃"]
# 預期：這些詞應該提升包含它們的文檔分數
```

**實際狀態：**
- `boost_keywords` 被 LLM 生成
- 但在 `search_service.py` 中**完全未使用**
- 只在 `test_search.py:35-36` 輸出顯示

**這是一個功能缺口！**

### 四、架構優化建議

#### 4.1 啟用 Boost Keywords

**選項 A: 合併到 keyword_query**
```python
# 在 search_service.py 中
if intent.boost_keywords:
    keyword_query = f"{intent.keyword_query} {' '.join(intent.boost_keywords)}"
```

**選項 B: 使用 Meilisearch 的 matchingStrategy**
```python
# 需要研究 Meilisearch 的 boost API
```

#### 4.2 優化 Metadata 使用

**選項 A: 將 meta_products 加入 searchable**
```python
searchable_attributes = [
    "title",
    "content",
    "metadata.meta_summary",
    "metadata.meta_products",  # ← 新增
]
```

**優點：** 產品名稱能參與搜索
**缺點：** 可能過度提升產品名稱的權重

**選項 B: 實現產品過濾**
```python
# 在 LLM Prompt 中允許產品過濾
# 在 build_meili_filter 中支持 meta_products
if filters.products:
    products_str = ", ".join([f"'{p}'" for p in filters.products])
    conditions.append(f"metadata.meta_products IN [{products_str}]")
```

#### 4.3 改善中文分詞

**當前問題：**
- Meilisearch 對中文使用 character-level tokenization
- "價格調整" → ["價", "格", "調", "整"]

**解決方案：**
1. 在 ETL 時使用 jieba 預處理中文
2. 在 `meta_summary` 中加入空格分詞："價格 調整"
3. 或考慮使用支持中文的搜索引擎（如 Elasticsearch with IK analyzer）

### 五、總結

**當前搜索機制（雙引擎協同）：**

#### 5.1 關鍵字搜索（Fuzzy Search）- 50% 權重
- ✅ 搜索欄位：`title`（高權重）+ `content`（中權重）+ `meta_summary`（低權重）
- ✅ 模糊匹配：英文支援 typo tolerance（最多 2 字符差異）
- ✅ Ranking Rules：words → typo → proximity → attribute → exactness
- ⚠️ 中文分詞：使用 character-level tokenization，精準度有限
- ❌ `meta_products` 不參與：產品名稱無法被關鍵字搜索匹配

#### 5.2 語義搜索（Semantic Search）- 50% 權重
- ✅ 向量化內容：title + **所有 metadata** + content
- ✅ `meta_products` 有作用：產品名稱被編碼到向量中
- ✅ 語義理解：能理解結構化信息（impact level、audience 等）
- ✅ 跨語言：能關聯英文 content 和中文查詢

#### 5.3 核心問題
1. **`meta_products` 在關鍵字搜索中缺席**
   - 查詢 "Azure OpenAI" 時，只能靠語義搜索（50% 權重）
   - 無法像 title/content 那樣獲得關鍵字精確匹配的高分

2. **`boost_keywords` 功能缺失**
   - LLM 提取的產品名稱完全未被使用
   - 無法手動提升特定關鍵字的權重

3. **中文分詞限制**
   - "價格調整" → ["價", "格", "調", "整"]
   - 影響中文關鍵字搜索精準度（但 `meta_summary` 部分彌補了這個問題）

#### 5.4 為什麼 meta_summary 很重要
- 原始 content 通常是英文
- meta_summary 是 LLM 生成的繁體中文摘要
- 同時參與：關鍵字搜索（提供中文 tokens）+ 向量搜索（語義信息）
- 是連接中文查詢和英文 content 的關鍵橋樑