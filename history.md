
## 2025-12-18
**強制關鍵字策略實作 (Strict Keyword Enforcement via Soft Boosting)**：針對使用者反饋「語意搜尋分數過高導致不相關結果浮現」的問題，提出並實作「軟性強制 (Soft Enforcement)」方案。
- **設計理念**：不使用雙引號強制完全匹配（保留 Typo Tolerance），改用「重複關鍵字加權 (Keyword Repetition Boosting)」策略，利用 Meilisearch 的關鍵字頻率權重機制創造分數斷層。
- **實作細節**：
    - 更新 `schemas.py`：新增 `SearchIntent.must_have_keywords` 欄位。
    - 更新 `search_prompts.py`：指導 LLM 識別必須存在的關鍵字（如專有名詞 GEMINI）。
    - 修改 `search_service.py`：將識別出的關鍵字在查詢字串中重複 3 次 (e.g., `GEMINI GEMINI GEMINI`)。
- **效果**：若文檔缺失關鍵字，BM25 分數歸零，即使向量分數高，總分也會被大幅拖累沉底；若文檔有關鍵字（含錯字），BM25 分數滿分，總分顯著提升。有效解決了向量搜尋發散問題，同時保留了模糊搜尋的容錯優勢。

## 2025-12-18 (下午)
**簡化數據格式重構 (Metadata Removal & Schema Simplification)**：移除複雜的 metadata 結構，改用 parse.json 的扁平化格式，大幅簡化系統架構。
- **核心變更**：
    - 更新 `schemas.py`：新增簡化的 `AnnouncementDoc`，包含 `link`, `year_month`, `workspace`, `title`, `content`, `cleaned_content` 六個基本欄位；舊版本重命名為 `LegacyAnnouncementDoc`。
    - 更新 `SearchFilters`：新增 `year_months` 和 `workspaces` 欄位以適配新格式。
    - 簡化 `vectorPreprocessing.py`：移除 `create_enriched_text` 功能，直接使用 `cleaned_content` 生成 embedding。
    - 更新 `db_adapter_meili.py`：修改 `transform_doc_for_meilisearch` 函數，使用 MD5 hash 從 link 生成唯一 ID；更新 `build_meili_filter` 支援新欄位過濾。
    - 更新 `meilisearch_config.py`：調整 `FILTERABLE_ATTRIBUTES` 為 `year_month`, `workspace`, `link`；簡化 `SEARCHABLE_ATTRIBUTES` 為 `title`, `cleaned_content`, `content`。
    - 修復導入路徑：統一使用 `from src.schema.schemas` 和 `from src.meilisearch_config` 絕對路徑。
- **效果**：消除了複雜的 LLM metadata 提取流程，減少向量生成的合成文本依賴，降低系統複雜度，提升可維護性。