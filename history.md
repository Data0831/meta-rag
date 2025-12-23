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

## 2025-12-19
- **前端重構 (Modularization)**：將龐大的 `search.js` 拆分為 6 個 ES6 模組 (Config/DOM/API/UI/Render/Main)，大幅提升代碼可維護性。
- **UI/UX 全面更新**：將介面升級為 Tailwind CSS 設計，引入 `marked.js` 支援 Markdown 渲染，並優化搜尋結果展示 (預設展開第一筆、改進卡片佈局)。
- **配置整合**：建立後端配置 API (`/api/config`) 與前端動態同步機制，統一管理相似度閾值與語意權重 (Slider 調整為 0-100 整數範圍)。
- **系統優化**：修正 `/collection_search` 路由重定向問題，並修復 LLM 過濾條件 (Year/Workspace/Links) 在前端的視覺化標籤顯示。

## 2025-12-23 11:14:13
- **Link 去重合併功能**：在 `config.py` 新增 `PRE_SEARCH_LIMIT=24` 配置（附 TODO 建議未來可改為動態倍數）。修改 `search_service.py` 實作 `_merge_duplicate_links()` 方法，先向 Meilisearch 請求 24 筆結果，按 `_rankingScore` 排序後合併相同 link 的文檔（content 用 `
---
` 拼接，保留最高 score 的 metadata），最後取前 `limit` 筆返回。更新 `docs/archtect/search-flow.md` 流程圖與文字說明，記錄去重邏輯以避免切塊後同一網頁重複出現。

## 2025-12-23 13:50:37
- **搜尋結果 UI 優化**：修改 `render.js` 與 `search_service.py`，在後端返回 `final_semantic_ratio` 欄位，前端根據此值在搜尋結果卡片的 match score 旁顯示搜尋類型標籤（Keyword/Semantic/Hybrid，分別使用藍/綠/紫配色）。卡片標題限制為 15 字，超過加上 "..."，展開後顯示完整標題。
- **LLM 錯誤處理**：在 `search_service.py` 中檢測 LLM 調用失敗（`parse_intent` 返回 `None`），設置 `llm_error` 欄位並使用 fallback 基本搜尋。前端在 `intentContainer` 頂部（查詢資訊後）顯示琥珀色警告橫幅「LLM 服務暫時無法使用，使用基本搜尋模式」。同步修復摘要生成失敗時的錯誤顯示，改為友好提示而非隱藏區塊。

## 2025-12-23 15:00:00
- **搜尋模式邏輯修復**：修正 `SearchService` 與 UI 在切換純關鍵字/語意模式時的不一致問題。
  - 將 Schema 中 `recommended_semantic_ratio` 預設值改為 `None` 以區分 LLM 建議。
  - 更新後端邏輯：當用戶手動設定極端值 (0.0 或 1.0) 時優先採納，忽略 LLM 建議。
  - 優化前端標籤：將 `render.js` 中的標籤判定改為容許浮點數誤差範圍 (<=0.01, >=0.99)，解決切換 Hybrid 顯示錯誤。