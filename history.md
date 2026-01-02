# Project History

## 2025-12-15 ~ 12-26 系統奠基與檢索升級
- **架構與部署**：遷移至 Meilisearch (30ms 延遲)，完成 Azure App Service 部署與 OpenAI Structured Outputs 兼容性修復。
- **檢索優化**：Link 去重合併技術，實作關鍵字精確加權重排 (Reranking) 與雙語擴展，並優化 Schema (年份/主標題) 適配新資料源。
- **UI/UX 重構**：前端模組化設計，採用 Tailwind CSS 與 Markdown 渲染，實作動態配置同步與 LLM 異常回退機制。
- **日誌開發**：全面導入 ANSI 彩色日誌，提升後端解析與 API 異常除錯的可辨識度。
  

## 2025-12-29
- **系統架構優化與功能增強**：統一全域錯誤處理機制與配置管理系統，實作 ID-based 文檔異動與分批預處理以提升效能，優化非對稱關鍵字加權演算法與意圖匹配邏輯，並重構前端 UI 與錯誤處理流程。

## 2025-12-30 代理式檢索與結構化摘要 (Agentic RAG & Structured Summary)
- **Agentic RAG 核心實作**：推出 `SrhSumAgent` 實作「搜尋 -> 判定 -> 重寫 -> 摘要」迭代流程，支援歷史意識查詢改寫與文檔排除，提升檢索覆蓋率與精準度。
- **架構與 API 重構**：整合搜尋邏輯至 Agent 主導，統一端點為 `/api/search` 並導入多階段狀態回傳（Stage-based streaming），提升系統反饋的透明度。
- **評分與過濾優化**：統一 Match 分數顯示邏輯，實作 `SCORE_PASS_THRESHOLD` 品質門檻與智慧篩選機制，並修正 Meilisearch 語法錯誤以確保檢索強健性。
- **結構化摘要與 UI 適配**：實作三段式摘要（簡答/詳答/總結）與引用超連結系統，優化檢索耗時計算視覺提示，提供層次分明且具備可信度的資訊呈現。

### 2026-01-02 搜尋檢索邏輯調整 (Search Logic Adjustment)
- **移除查詢字串加成 (Remove Query Augmentation)**：修改 `src/services/search_service.py`，移除在 Meilisearch 初步檢索階段將 `must_have_keywords` 重複附加於查詢字串後方的邏輯。此舉旨在簡化原始查詢，避免 Meilisearch 內建評分過度受到關鍵字重複出現的干擾。關鍵字的加權功能現在完全由服務層的 `ResultReranker` 負責，透過 `hit_ratio` 實現更精確且可控的二次分數加成，確保最終排名能真實反映文件與關鍵字的相關性。

### 2026-01-02 引用連結轉換修復 (Citation Link Conversion Fix)
- **修復內容總結引用連結 (Fix General Summary Citations)**：修正 `src/static/js/search.js` 的 `renderStructuredSummary` 函數，在處理「內容總結」(general_summary) 時補上遺漏的 `convertCitationsToLinks()` 調用。現在三段式摘要中的「詳細說明」與「內容總結」區塊都能正確將引用標記 `[1]`, `[2]` 等轉換為藍色上標超連結，點擊後於新標籤頁開啟來源文件，提升使用者體驗一致性與資訊可信度。
