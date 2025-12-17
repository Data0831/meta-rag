# URL 清理解決方案指南

## 問題背景

原始的 `content` 欄位包含大量超連結，會造成以下問題：

### 1. 語義搜索問題
- URL（如 `https://microsoft.com/azure/...`）本身幾乎沒有語義價值
- URL 會稀釋 embedding 向量的語義表示
- 重複的域名路徑在向量空間中產生噪音

### 2. 模糊搜索問題
- URL 前綴（`https://`, `www.`, 域名）在所有文檔中高度重複
- 搜索 "link"、"http"、"microsoft.com" 會匹配到大量無關結果
- 路徑相似度會掩蓋真正的內容相關性

### 3. 具體案例
```
使用者問題: "這個 link 在講什麼"
問題: 所有文檔都包含 "https://microsoft.com/..." 前綴
結果: 搜索分數被路徑相似度主導，而非實際內容
```

---

## 解決方案架構

### 雙欄位策略

```
┌─────────────────────────────────────────────────────────┐
│  Raw Content (含 URLs)                                  │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
            ┌─────────────────┐
            │  ETL Cleaning   │
            │  (Parser 階段)   │
            └────────┬────────┘
                     │
        ┌────────────┴────────────┐
        ▼                         ▼
┌───────────────┐        ┌─────────────────┐
│original_content│       │  content_clean  │
│  (保留完整)    │        │  (移除 URLs)    │
└───────┬───────┘        └────────┬────────┘
        │                         │
        │                         ├─→ Embedding 生成
        │                         ├─→ 關鍵字搜索
        │                         └─→ 語義搜索
        │
        └─→ 結果顯示 (保留原始格式和連結)
```

### 欄位說明

| 欄位名稱 | 用途 | 內容 |
|---------|------|------|
| `original_content` | 結果展示 | 保留原始文本，包含所有 URL |
| `content_clean` | 搜索 & Embedding | 移除 URL，保留錨點文字 (anchor text) |

---

## 實作細節

### 1. URL 清理邏輯 (`content_cleaner.py`)

```python
# Markdown links: [文字](url) → 保留 "文字"
"詳見 [定價](https://azure.com/pricing)" → "詳見 定價"

# Standalone URLs: 完全移除
"訪問 https://example.com 查看" → "訪問 查看"

# www. URLs: 完全移除
"官網：www.microsoft.com" → "官網："
```

**清理模式**:
- **Aggressive** (預設): 完全移除 URL，保留錨點文字
- **Conservative**: 替換 URL 為 `[連結]` 標記

### 2. 整合點

#### Parser 階段 (`parser.py`)
```python
from src.ETL.content_cleaner import clean_content_for_search

# 在解析原始資料時同步清理
content_clean = clean_content_for_search(content)
```

#### Embedding 生成 (`vector_utils.py`)
```python
# 使用清理後的內容生成 embedding
content = doc.content_clean if doc.content_clean else doc.original_content
```

#### Meilisearch 配置 (`meilisearch_config.py`)
```python
SEARCHABLE_ATTRIBUTES = [
    "title",
    "metadata.meta_summary",
    "content_clean",  # 只搜索清理後的內容
]
```

---

## 使用指南

### 步驟 1: 測試清理效果

```bash
# 執行測試腳本查看清理效果
python src/ETL/test_content_cleaner.py
```

預期輸出範例：
```
[Test 1] Markdown link with traditional Chinese
原始內容：
  詳見 [Azure 定價頁面](https://azure.microsoft.com/pricing/) 了解更多資訊。

清理結果 (Aggressive):
  詳見 Azure 定價頁面 了解更多資訊。
```

### 步驟 2: 更新現有資料

#### 選項 A: 完整重新處理 (推薦)

```bash
# 1. 重新解析原始資料 (會自動清理 URLs)
python src/dataPreprocessing.py
# 選擇: 1. Parse raw JSON
# 選擇: 2. Run ETL to generate metadata

# 2. 清空 Meilisearch index
python src/vectorPreprocessing.py
# 選擇: 1. Clear Meilisearch index

# 3. 重新生成 embeddings 並寫入
python src/vectorPreprocessing.py
# 選擇: 2. Process and Write
```

#### 選項 B: 僅更新 content_clean 欄位 (快速)

如果您的 metadata 已經處理完成，可以運行以下腳本只更新 `content_clean` 欄位：

```python
# 創建 update_content_clean.py 腳本
import json
from src.config import PROCESSED_OUTPUT
from src.ETL.content_cleaner import clean_content_for_search

with open(PROCESSED_OUTPUT, 'r', encoding='utf-8') as f:
    docs = json.load(f)

for doc in docs:
    if 'original_content' in doc:
        doc['content_clean'] = clean_content_for_search(doc['original_content'])

with open(PROCESSED_OUTPUT, 'w', encoding='utf-8') as f:
    json.dump(docs, f, ensure_ascii=False, indent=2)

print(f"✓ Updated {len(docs)} documents")
```

然後重新生成 embeddings：
```bash
python src/vectorPreprocessing.py
# 選擇: 1. Clear Meilisearch index
# 選擇: 2. Process and Write
```

### 步驟 3: 驗證搜索效果

```bash
# 啟動搜索服務
python src/app.py
```

測試搜索案例：
1. **關鍵字搜索**: "Azure 定價" (應該匹配到內容，而非 URL)
2. **語義搜索**: "這個 link 在講什麼" (不應被 URL 前綴誤導)
3. **混合搜索**: "Sentinel 預購" (應該返回相關公告，而非 URL 匹配)

---

## 效果評估

### 預期改善

| 指標 | 改善前 | 改善後 |
|------|--------|--------|
| URL 噪音 | 每篇文章 5-15 個 URL | 0 個 URL |
| Embedding 品質 | URL 稀釋語義 | 純語義內容 |
| 模糊搜索精準度 | 被路徑匹配干擾 | 基於實際內容 |
| "link" 搜索結果 | 匹配所有文檔 | 僅匹配相關內容 |

### 測試案例

```python
# 測試 1: 搜索應該不受 URL 影響
query = "定價變更"
# 應該匹配: 內容提到定價的文章
# 不應該匹配: 僅因為 URL 包含 "/pricing/" 的文章

# 測試 2: 語義搜索更準確
query = "如何節省成本"
# 應該匹配: 討論預購計畫、折扣的文章
# Embedding 不會被 URL 稀釋，語義表示更純粹

# 測試 3: 避免誤匹配
query = "link"
# 應該只匹配: 真正討論連結或超連結的內容
# 不應該匹配: 所有包含 URL 的文檔
```

---

## 注意事項

### 1. 向後兼容性
- `original_content` 保留不變，確保原始資料完整性
- `content_clean` 是新增欄位，不影響現有欄位
- `vector_utils.py` 有 fallback 機制，向下兼容舊資料

### 2. 資料完整性
- 錨點文字 (anchor text) 會被保留，例如：
  - `[定價頁面](url)` → `定價頁面` (保留)
- 重要的描述性文字不會丟失

### 3. 效能影響
- 清理操作在 ETL 階段執行，對搜索效能無影響
- 正則表達式處理非常快速 (< 1ms per document)

### 4. 可選配置
如果您希望保留 URL 標記（如 `[連結]`），可以修改 `content_cleaner.py`:
```python
clean_content_for_search = clean_content_conservative  # 改為保守模式
```

---

## 疑難排解

### Q1: 清理後搜索不到預期結果？
**檢查**:
1. 確認 Meilisearch 配置使用 `content_clean`
2. 確認 embeddings 已重新生成
3. 檢查 `SEARCHABLE_ATTRIBUTES` 設定

### Q2: 某些重要的 URL 被移除了？
**解決方案**:
- `original_content` 仍保留完整 URL
- 搜索結果展示時可顯示原始內容
- 如需保留特定 URL pattern，可調整正則表達式

### Q3: Embedding 生成失敗？
**檢查**:
- `content_clean` 欄位是否存在
- `vector_utils.py` 已更新為使用 `content_clean`
- 確認 fallback 機制運作正常

---

## 進階優化

### 1. 連結元資料提取
未來可考慮提取連結作為獨立欄位：
```python
# 新增 links 欄位存放所有 URL
"links": [
    {
        "text": "定價頁面",
        "url": "https://azure.microsoft.com/pricing/",
        "domain": "azure.microsoft.com"
    }
]
```

### 2. LLM 語義增強
使用 LLM 替換 URL 為描述性文字：
```python
# 範例
"[了解更多](https://azure.com/sentinel/pricing)"
↓ (LLM 增強)
"[了解更多關於 Azure Sentinel 的定價資訊]"
```

### 3. 分層搜索策略
```python
# 根據查詢類型動態調整
if "連結" in query or "link" in query:
    # 搜索 original_content (包含 URLs)
else:
    # 搜索 content_clean (更好的語義匹配)
```

---

## 總結

此解決方案通過 **雙欄位策略** 解決了 URL 對搜索品質的影響：

✅ **語義搜索**: Embedding 基於清理後內容，語義表示更純粹
✅ **模糊搜索**: 移除 URL 噪音，避免路徑重複匹配
✅ **資料完整性**: 保留 `original_content`，確保原始資料不丟失
✅ **向後兼容**: Fallback 機制確保系統穩定性
✅ **輕量實作**: 僅需在 ETL 階段處理，無運行時開銷

**建議**: 對於新資料，完整走一遍 ETL pipeline 以確保最佳效果。