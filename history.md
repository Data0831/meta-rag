
## 2025-12-18
**強制關鍵字策略實作 (Strict Keyword Enforcement via Soft Boosting)**：針對使用者反饋「語意搜尋分數過高導致不相關結果浮現」的問題，提出並實作「軟性強制 (Soft Enforcement)」方案。
- **設計理念**：不使用雙引號強制完全匹配（保留 Typo Tolerance），改用「重複關鍵字加權 (Keyword Repetition Boosting)」策略，利用 Meilisearch 的關鍵字頻率權重機制創造分數斷層。
- **實作細節**：
    - 更新 `schemas.py`：新增 `SearchIntent.must_have_keywords` 欄位。
    - 更新 `search_prompts.py`：指導 LLM 識別必須存在的關鍵字（如專有名詞 GEMINI）。
    - 修改 `search_service.py`：將識別出的關鍵字在查詢字串中重複 3 次 (e.g., `GEMINI GEMINI GEMINI`)。
- **效果**：若文檔缺失關鍵字，BM25 分數歸零，即使向量分數高，總分也會被大幅拖累沉底；若文檔有關鍵字（含錯字），BM25 分數滿分，總分顯著提升。有效解決了向量搜尋發散問題，同時保留了模糊搜尋的容錯優勢。