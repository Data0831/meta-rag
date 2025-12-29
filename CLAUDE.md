# 專案規格書：Microsoft RAG 智慧檢索系統 (Meilisearch 版)

## 1. 專案概述
本專案旨在建構一套高效能的 Microsoft 公告智慧檢索系統，並為未來擴充為對話機器人 (Chatbot) 奠定基礎。
*   **核心目標**：打造統一且高效的檢索體驗，整合「關鍵字精準匹配」、「中文分詞」、「屬性過濾」與「語意向量檢索 (Hybrid Search)」。
*   **架構特色**：採用輕量化設計，移除複雜的資料庫同步邏輯 (No SQL, No Fusion Code)，直接使用清洗後的內容生成向量並索引至 Meilisearch。
*   **目標用戶**：需要快速查找 Microsoft 產品公告與技術文件的使用者。

## 2. 技術棧
*   **語言與環境**: Python 3.10+ (Anaconda), Windows/Linux
*   **核心引擎**: Meilisearch (Docker 部署) - 負責全文檢索、向量檢索與過濾。
*   **Web 框架**: Flask (規劃中/初步實作)
*   **LLM 模型**: Google Gemini 2.5 Flash (用於意圖識別與 RAG 生成)
*   **Embedding 模型**: bge-m3 (用於向量生成)
*   **資料驗證**: Pydantic (嚴格定義 Schema)
*   **主要依賴**: `meilisearch`, `google-generativeai`, `flask`, `pydantic`

## 3. 檔案結構
僅列出核心目錄與重點檔案：

```text
project_root/
├── data/
│   ├── backup/                 # 備份資料與舊版工具
│   ├── fetch_result/           # 爬蟲抓取的原始資料
│   ├── test/                   # 資料處理測試
│   ├── data.json               # 原始資料來源
│   ├── parser.py               # 資料解析 ETL 工具
│   ├── remove.json             # 待移除資料清單
│   └── vectorPreprocessing.py  # 向量計算與 Index Reset 工具
├── docs/                       # 專案架構與操作文件
├── src/
│   ├── app.py                  # Flask 應用程式入口
│   ├── config.py               # 全域環境設定
│   ├── meilisearch_config.py   # Meilisearch 索引與過濾欄位設定
│   ├── database/
│   │   ├── db_adapter_meili.py # [核心] Meilisearch 資料庫轉接器
│   │   └── vector_utils.py     # 向量處理工具
│   ├── llm/
│   │   ├── client.py           # LLM 客戶端
│   │   ├── search_prompts.py   # 搜尋意圖識別 Prompt
│   │   └── rag_prompts.py      # RAG 回答生成 Prompt
│   ├── schema/
│   │   └── schemas.py          # Pydantic 資料模型
│   ├── services/
│   │   ├── keyword_alg.py      # 關鍵字權重演算法
│   │   ├── search_service.py   # 搜尋業務邏輯 (Intent Parsing -> Search)
│   │   └── rag_service.py      # RAG 業務邏輯
│   ├── static/                 # 前端靜態資源 (CSS, JS)
│   ├── templates/              # 前端 HTML 模板
│   ├── tool/                   # 通用工具 (如 ANSI 輸出)
│   └── logs/                   # 系統日誌檔
├── task/
│   ├── task.md                 # 任務進度追蹤
│   └── log.md                  # 任務執行細節紀錄
├── test/                       # 系統整合與功能測試 (test_search.py 等)
├── tmp/                        # 臨時除錯腳本
├── history.md                  # 專案變更歷史記錄
├── GEMINI.md                   # 專案規格書 (與本檔同步)
├── CLAUDE.md                   # [本檔案] 專案規格書
└── requirements.txt
```

## 4. 開發與修改原則

### 4.1 架構原則 (三層式架構)
1.  **應用層 (App)**: 僅負責路由與參數接收，不做業務邏輯。
2.  **服務層 (Service)**: 核心邏輯所在。`SearchService` 處理意圖與檢索，`RAGService` 處理生成。
3.  **資料層 (DAL)**: `db_adapter_meili.py` 是唯一與 Meilisearch 溝通的窗口。

### 4.2 編碼規範
*   **Type Hints**: 全面使用 Python 類型註釋。
*   **Pydantic**: 資料交換與寫入 DB 前必須通過 Pydantic Model 驗證。
*   **Imports**: 使用絕對路徑 (e.g., `from src.database import ...`)。
*   **Imports**: 不要使用任何註解，包括 docstring。
*   **錯誤處理**: 底層函數統一返回 dict 格式。成功時：`{"status": "success", "result": ...}`；失敗時：`{"status": "failed", "error": ..., "stage": ...}`。調用方必須檢查 `status` 欄位。
*   **錯誤顯示**: 輸出錯誤資訊或失敗的 `dict` 時，必須使用 `src.tool.ANSI.print_red` 以紅色標示。

### 4.3 資料庫設計 (Meilisearch)
*   **ID 生成**: 使用 link+title 的 MD5 hash 作為唯一 ID。
*   **欄位限制**: 必須在 `meilisearch_config.py` 明確定義 `FILTERABLE_ATTRIBUTES` (如 `year_month`, `workspace`) 才能進行過濾。
*   **冪等性**: `add_documents` 操作視為 Upsert (若 ID 存在則覆蓋)。

## 5. 任務執行流程 (強制三階段)

當收到任務時，流程如下：

### 階段 1: 理解與提問 (必須完成)
1. **任務重述**: 用 2-3 句話重述你理解的需求,列出會動到的檔案。
2. **主動提問**: 任何不明確的地方(欄位命名、錯誤處理方式、UI 行為、是否需要額外功能等),整理成問題清單。
3. **停止並等待**: 在問題列表最後明確寫:「**在你回答之前,我不會開始修改程式碼**。」

### 階段 2: 執行 (獲得確認後)
1. 嚴格按照確認的需求執行,不做額外優化。
2. 若執行中產生新疑問,再次停下來提問。
3. 僅使用專案已定義的函式與架構。

### 階段 3: 交付
1. 回報實際修改的檔案與變更內容。
2. 若有未實作的「潛在改進」,以建議列表方式呈現,標註「尚未執行,僅供參考」。
3. 必要時更新 `history.md` (不超過 500 字)。

### 禁止事項
- **禁止臆測**:
    - **數據**: 未經指示，禁用假資料。
    - **檔案**: 操作前，必須檢查檔案是否存在。
    - **函式**: 僅可使用專案已定義函式，不確定時先提問。
- **禁止擅自重構**: 未經要求，禁止重構或優化程式碼。
- **禁止自作主張添加**:
    - 即使你認為「為了程式完整性/穩定性」,也不可擅自添加 `try...catch`、驗證邏輯、防禦性程式碼。
    - 若你認為需要,必須**先以問題形式詢問使用者**,獲得明確同意後才執行。

### 行為範例

#### ❌ 錯誤示例
**用戶要求**: 「在登入頁面添加一個按鈕」  
**AI 錯誤回應**: 「我已添加按鈕,並且為了確保程式穩定性添加了 try...catch 和防抖函數」  
**問題**: 添加了未要求的功能

#### ✅ 正確示例
**用戶要求**: 「在登入頁面添加一個按鈕」  
**AI 正確回應**: 
```
我將在登入頁面添加按鈕。請確認:
1. 按鈕文字是什麼?
2. 點擊後的行為是?
3. 需要特定樣式嗎?
4. 是否需要防抖或錯誤處理?

在你回答之前,我不會開始修改程式碼。
```

## 6. 常見錯誤與注意事項
*   **Meilisearch Filter**: 若過濾無效，請優先檢查 `meilisearch_config.py` 中的 `FILTERABLE_ATTRIBUTES` 是否已包含該欄位，並確認是否已執行 `reset_index` 更新設定。
*   **Schema 同步**: 修改 `schemas.py` 後，需評估是否影響 `vectorPreprocessing.py` (ETL) 與 `meilisearch_config.py`。
*   **No SQL**: 本專案不使用傳統關聯式資料庫，所有資料持久化皆在 Meilisearch，請勿引入 SQLite 或 PostgreSQL。

## 7. 目前任務進度、歷史記憶參考
*   **任務進度**: 請參閱 `task/task.md` 以獲取當前開發階段與待辦事項。
*   **變更歷史**: 請參閱 `history.md` 以了解最近的程式碼變更與決策記錄。