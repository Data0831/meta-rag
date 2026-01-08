project_root/
├── data_update
├── src/
│   ├── app.py                  # Flask 應用程式入口
│   ├── config.py               # 全域環境設定
│   ├── meilisearch_config.py   # Meilisearch 索引與過濾欄位設定
│   ├── agents/
│   │   ├── srhSumAgent.py      # 搜尋摘要代理
│   │   └── tool.py             # 代理工具函式
│   ├── database/
│   │   ├── db_adapter_meili.py # [核心] Meilisearch 資料庫轉接器
│   │   └── vector_utils.py     # 向量處理工具
│   ├── llm/
│   │   ├── client.py           # LLM 客戶端
│   │   ├── search_prompts.py   # 搜尋意圖識別 Prompt
│   │   └── prompts/
│   │       ├── check_relevance.py  # 相關性檢查 Prompt
│   │       ├── query_rewrite.py    # 查詢改寫 Prompt
│   │       ├── rag.py              # RAG 生成 Prompt
│   │       └── summary.py          # 摘要生成 Prompt
│   ├── schema/
│   │   └── schemas.py          # Pydantic 資料模型
│   ├── services/
│   │   ├── keyword_alg.py      # 關鍵字權重演算法
│   │   ├── search_service.py   # 搜尋業務邏輯 (Intent Parsing -> Search)
│   │   └── rag_service.py      # RAG 業務邏輯
│   ├── static/
│   │   ├── css/                # 樣式表
│   │   └── js/                 # 前端腳本 (模組化架構)
│   │       ├── search.js       # 主入口，orchestrate 所有模組
│   │       ├── alert.js        # Alert 通知功能
│   │       ├── citation.js     # Citation 轉換與摘要渲染
│   │       ├── search-config.js # 搜尋配置 UI 控制
│   │       ├── search-logic.js # 搜尋執行邏輯
│   │       ├── chatbot.js      # Chatbot 功能
│   │       ├── config.js       # 前端配置管理
│   │       ├── dom.js          # DOM 元素參照
│   │       ├── api.js          # API 呼叫
│   │       ├── ui.js           # UI 狀態管理
│   │       └── render.js       # 結果渲染
│   ├── templates/
│   │   └── index.html          # 主頁面模板
│   ├── tool/
│   │   └── ANSI.py             # ANSI 顏色輸出工具
│   └── logs/                   # 系統日誌檔
├── test/                       # 系統整合與功能測試
├── tmp/                        # 臨時除錯腳本
└── requirements.txt