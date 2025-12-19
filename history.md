# Project History

## 2025-12-15
- **初期建置**：完成專案基礎架構 (Phase 1-2)，包含 ETL Pipeline、資料攝取與 Pydantic Schema。
- **優化**：實作自動化 ETL，整合 Gemini LLM 進行 Metadata 提取，並優化配置管理與 API 穩定性，建立 `metadata.json` 聚合輸出。

## 2025-12-16
- **架構遷移 (Phase 3-5)**：完成向量攝取與 Hybrid Search 核心後，執行重大決策遷移至 **Meilisearch** 單一引擎，移除 SQLite/Qdrant 雙資料庫架構，搜尋延遲降至 ~30ms。
- **中文優化**：實作 `jieba` 分詞方案 (`meta_summary_segmented`)，並在 ETL 中整合分詞處理，大幅提升中文關鍵字匹配準確度。
- **系統重構**：統一資料庫適配器為 `db_adapter_meili.py`，簡化 `SearchService` 邏輯，建立 `MIGRATION.md`。

## 2025-12-17
- **前端整合**：發布 Collection Search 介面，支援動態相似度閾值、語意權重調整 (Semantic Ratio) 與 LLM 意圖重寫開關。
- **搜尋調優**：建立 `meilisearch_config.py` 集中管理排序規則，修復混合搜尋結果排序問題 (Ranking Score Fix)，並實作 LLM 動態推薦語意權重。
- **路由修復**：修正 Flask 路由與前端導航，確保 Collection 與 Vector Search 頁面連結正常。

## 2025-12-18
- **搜尋策略優化**：實作「軟性強制關鍵字」(Soft Keyword Enforcement) 與「雙語關鍵字擴展」(Bilingual Expansion)，利用重複關鍵字加權 (Boosting) 解決向量搜尋發散與中英匹配問題。
- **架構輕量化 (Phase 6)**：徹底移除 Metadata 與 Enriched Text 複雜結構，改採 parse.json 扁平化格式，大幅簡化 ETL 流程與 Schema。
- **代碼清理**：修復 Meilisearch 過濾器語法 (`IN` operator)，並刪除約 165 行廢棄代碼 (Legacy Code Removal)，系統進入穩定期。

## 2025-12-19 14:00
- **UI/UX 更新**：將 `index.html` 更新為新版 Tailwind CSS 設計，並整合 `collection_search.js` 功能與樣式。
- **路由調整**：修改 `src/app.py`，將 `/collection_search` 重定向至預設集合 `/collection/announcements` 以解決訪問問題。
- **操作規範**：使用者強調應嚴格遵守修改範圍，避免非預期的代碼更動。

## 2025年12月19日 星期五 16:00
- **介面與功能優化**：優化 UI 佈局，移除容器間距並交由卡片控制，引入 `marked.js` 實現 Markdown 渲染，並設定第一筆結果預設展開。
- **配置管理整合**：建立後端配置介面 (`/api/config`) 與前端動態載入機制，將預設搜尋數量調整為 5，提升系統靈活性與一致性。

## 2025年12月19日 星期五 16:15
- **配置參數擴充**：於 config.py 新增 `DEFAULT_SIMILARITY_THRESHOLD` 與 `DEFAULT_SEMANTIC_RATIO`，並透過 API 暴露給前端。
- **前端控制項優化**：更新 `index.html` 將語義權重滑桿範圍調整為 0-100 (整數)，並在 `search.js` 中實作數值轉換與初始化邏輯，確保與後端設定同步。

## 2025年12月19日 星期五 17:00
- **前端模組化重構**：將 `search.js` (458 行) 拆分為 6 個 ES6 模組：`config.js` (配置管理)、`dom.js` (DOM 引用)、`api.js` (API 請求)、`ui.js` (狀態管理)、`render.js` (結果渲染) 與 `search.js` (主入口 114 行)，大幅提升代碼可維護性與模組化程度。
