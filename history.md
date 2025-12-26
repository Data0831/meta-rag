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

## 2025-12-24 09:09:16
- **Azure OpenAI Structured Outputs 兼容性修復**：解決 LLM Schema 驗證 400 錯誤。
  - 展平 Schema 結構：刪除 `SearchFilters` 類別，將 `year_month/links/workspaces` 直接整合至 `SearchIntent`，消除 `$ref` 引用。
  - 嚴格模式處理：在 `client.py` 新增 `_add_additional_properties()` 方法，遞迴為所有 object 添加 `"additionalProperties": false` 並強制所有 properties 加入 `required` 數組。
  - 級聯更新：修改 `db_adapter_meili.py` 的 `build_meili_filter()` 與 `search_service.py` 的調用邏輯，適配新的扁平化 Schema 結構。

## 2025-12-24 14:30:00
- **Azure App Service 部署優化**：修改 `src/app.py` 以支援 Web App 雲端環境。
  - 實作動態 Port 綁定：改從環境變數 `PORT` 讀取監聽埠號（預設 5000），確保 Azure 流量能正確導向 Flask 容器。
  - 調整啟動 Log 輸出：更新啟動時的 URL 顯示為 `0.0.0.0`，方便除錯。

## 2025-12-24 15:30:00
- **前端 LLM 意圖顯示修復**：修正 `render.js` 中 `updateIntentDisplay()` 函數的數據讀取邏輯，從錯誤的 `intent.filters.year_month` 改為直接讀取 `intent.year_month` 等頂層欄位。新增 `must_have_keywords` 紅色標籤渲染（格式：`[必含: xxx]`）。在 `index.html` 的 `llmDetails` 區塊新增「LLM 建議權重」顯示元素（`intentRecommendedRatio`），動態顯示 `recommended_semantic_ratio` 百分比值（例如：40%）。修復後前端可正確顯示所有 LLM 解析的篩選條件（year_month 藍色標籤、must_have_keywords 紅色標籤、workspaces 綠色標籤、links 紫色標籤、limit 灰色標籤）。

## 2025-12-26
- **資料格式與搜尋升級**：因應新版資料來源格式，更新全線架構。
  - **Schema 擴充**：`AnnouncementDoc` 新增 `year` (年份)、`main_title` (主標題) 與 `heading_link` (錨點連結)，並將 `workspace` 改為可選欄位 (Optional) 以保持彈性。
  - **Meilisearch 配置**：更新 `meilisearch_config.py`，將 `year` 加入過濾條件 (`FILTERABLE_ATTRIBUTES`)，並新增 `main_title` 至搜尋欄位 (`SEARCHABLE_ATTRIBUTES`)，但設定為最低權重 (Lowest Priority) 以避免干擾核心關鍵字排序。
  - **轉接器適配**：修改 `db_adapter_meili.py` 資料轉換邏輯，確保新欄位正確映射至 Meilisearch 索引。
