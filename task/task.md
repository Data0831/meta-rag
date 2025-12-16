1. 關鍵字模糊比對機制

  並非多次查詢，而是單次查詢自動處理：
  - 你的 keyword_query（例如 "Azure OpenAI 價格"）被一次性送入 Meilisearch
  - Meilisearch 內部自動分詞並依照 6 個 ranking rules 計算分數
  - 重要：中文是按字符級分詞（"價格" → ["價", "格"]），這是目前架構的限制

  Typo Tolerance（模糊匹配）：
  - 英文支援最多 2 字符差異："Azrue" 仍能匹配 "Azure"
  - 中文不支援 typo tolerance（因為是字符級分詞）

  2. Metadata 的實際作用

  只有 meta_summary 真正參與搜索：
  - ✅ meta_summary（LLM 生成的中文摘要）：參與關鍵字 + 語義搜索
    - 這是最有價值的 metadata
    - 彌補了原始 content 可能是英文的問題
    - 提供更豐富的中文語義信息

  其他 metadata 僅用於過濾：
  - ⚠️ meta_category, meta_impact_level：只能用 filter，不參與搜索
  - ❌ meta_products, meta_audience：可過濾但完全未使用

  這表示：
  - 查詢 "Azure OpenAI" 時，meta_products 中的 "Azure OpenAI" 不會提升文檔分數
  - 這些 metadata 的搜索潛力未被發揮

  3. LLM 生成的 Keywords 問題

  發現重大功能缺口：
  - LLM 確實生成了 boost_keywords（例如 ["Azure OpenAI", "AI 雲合作夥伴計劃"]）
  - 但在 search_service.py 中完全未被使用
  - 只在測試輸出中顯示，對搜索結果無任何影響

  這意味著：
  - LLM 的產品名稱提取工作被浪費了
  - 無法通過 boost 機制提升特定產品相關文檔的排名

  建議的優化方向

  1. 啟用 boost_keywords：將其合併到 keyword_query 或研究 Meilisearch 的 boost API
  2. 將 meta_products 加入 searchable：讓產品名稱能參與搜索
  3. 改善中文分詞：在 ETL 時使用 jieba 預處理，或在 meta_summary 中加入空格分詞

  你想針對這些問題進行優化嗎？我可以幫你實現這些改進。