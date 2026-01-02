"""
Search Service - Simplified with Meilisearch Hybrid Search

This service uses Meilisearch for unified hybrid search that combines:
- Keyword search (with fuzzy matching and typo tolerance)
- Semantic vector search

No more RRF fusion needed - Meilisearch handles it internally!
"""

from typing import Dict, Any, Optional, List
from src.llm.client import LLMClient
from src.llm.search_prompts import SEARCH_INTENT_PROMPT
from src.schema.schemas import SearchIntent
from src.database.db_adapter_meili import MeiliAdapter, build_meili_filter
from src.database import vector_utils
from src.config import MEILISEARCH_HOST, MEILISEARCH_API_KEY, MEILISEARCH_INDEX, PRE_SEARCH_LIMIT
from meilisearch_config import DEFAULT_SEMANTIC_RATIO
from datetime import datetime


class SearchService:
    """
    Simplified Search Service using Meilisearch.

    Architecture:
    1. Parse user query into SearchIntent (LLM)
    2. Convert filters to Meilisearch syntax
    3. Generate query embedding (if using semantic search)
    4. Single API call to Meilisearch (hybrid search)
    5. Return results with ranking scores
    """

    def __init__(self, show_init_messages: bool = False):

        if show_init_messages:
            print(" SearchService.__init__() called")
            print(f"  MEILISEARCH_HOST: {MEILISEARCH_HOST}")
            print(f"  MEILISEARCH_INDEX: {MEILISEARCH_INDEX}")

        try:
            print("  Initializing LLMClient...")
            self.llm_client = LLMClient()
            print("  LLMClient initialized")
        except Exception as e:
            print(f"  LLMClient initialization failed: {e}")
            raise

        try:
            print("  Initializing MeiliAdapter...")
            self.meili_adapter = MeiliAdapter(
                host=MEILISEARCH_HOST,
                api_key=MEILISEARCH_API_KEY,
                collection_name=MEILISEARCH_INDEX,
            )
            print("  MeiliAdapter initialized")
        except Exception as e:
            print(f"  MeiliAdapter initialization failed: {e}")
            raise

    def parse_intent(self, user_query: str) -> Optional[SearchIntent]:
        """
        Convert user query into structured search intent using LLM.

        Args:
            user_query: Natural language query from user

        Returns:
            SearchIntent object with filters, keyword_query, and semantic_query
        """
        # Construct prompt with current date context
        system_prompt = SEARCH_INTENT_PROMPT.format(
            current_date=datetime.now().strftime("%Y-%m-%d")
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query},
        ]

        # Use LLM with schema validation
        intent = self.llm_client.call_with_schema(
            messages=messages, response_model=SearchIntent, temperature=0.0
        )
        return intent

    def _merge_duplicate_links(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Merge documents with the same link by concatenating their content.
        Results should already be sorted by _rankingScore (highest first).

        Args:
            results: List of search results sorted by score

        Returns:
            List of deduplicated results with merged content
        """
        if not results:
            return []

        link_to_doc = {}
        merged_results = []

        for doc in results:
            link = doc.get("link")
            if not link:
                merged_results.append(doc)
                continue

            if link not in link_to_doc:
                link_to_doc[link] = doc
                merged_results.append(doc)
            else:
                existing_doc = link_to_doc[link]
                existing_content = existing_doc.get("content", "")
                new_content = doc.get("content", "")
                existing_doc["content"] = f"{existing_content}\n---\n{new_content}"

        return merged_results

    def search(
        self,
        user_query: str,
        limit: int = 20,
        semantic_ratio: float = DEFAULT_SEMANTIC_RATIO,
        enable_llm: bool = True,
        manual_semantic_ratio: bool = False,
        website_filters: Optional[List[str]] = None,  # 新增：接收 UI 傳來的網站列表
    ) -> Dict[str, Any]:
        """
        Perform unified hybrid search using Meilisearch.

        Workflow:
        1. Parse Intent (LLM) -> Extract filters, keyword_query, semantic_query, recommended_semantic_ratio
           (If enable_llm=False, skips LLM and uses raw query)
        2. Build Meilisearch filter expression
        3. Generate query embedding for semantic search
        4. Single Meilisearch API call (combines keyword + semantic + filters)
        5. Return ranked results
        
        Args:
            user_query: Natural language query
            limit: Maximum number of results to return
            semantic_ratio: Initial weight for semantic search (0.0 = pure keyword, 1.0 = pure semantic)
                            Default 0.5 - Will be overridden by LLM's recommended_semantic_ratio if available
            enable_llm: Whether to use LLM for intent parsing (default: True)
            manual_semantic_ratio: If True, strictly use provided semantic_ratio. If False, use LLM recommendation if available.

        Returns:
            Dictionary with:
            - intent: Parsed search intent (includes recommended_semantic_ratio)
            - results: List of ranked documents from Meilisearch
            - llm_error: (optional) Error message if LLM failed
        """
        # 1. Parse Intent
        intent = None
        llm_error = None

        if enable_llm:
            try:
                intent = self.parse_intent(user_query)
            except Exception as e:
                print(f"LLM Intent parsing failed: {e}")
                llm_error = str(e)

        if not intent:
            if enable_llm:
                print("Intent parsing failed. Using fallback basic search.")

            intent = SearchIntent(
                keyword_query=user_query,
                semantic_query=user_query,
            )

        # Override limit if specified in intent
        if intent.limit is not None:
            limit = intent.limit

        
        # 如果前端有傳來 website_filters，強制覆蓋 intent 裡的設定
        if website_filters and len(website_filters) > 0:
            print(f"UI Override: Applying website filters: {website_filters}")
            intent.websites = website_filters
        else:
            # 如果前端沒傳 (例如全選或沒選)，確保它是空的，避免 None 導致錯誤
            if not hasattr(intent, 'websites') or intent.websites is None:
                intent.websites = []

        # Use LLM-recommended semantic_ratio logic:
        # If manual_semantic_ratio is True, we respect the user's provided ratio.
        # If manual_semantic_ratio is False (Auto Mode), we use LLM's recommendation if available.
        if not manual_semantic_ratio and intent.recommended_semantic_ratio is not None:
            semantic_ratio = intent.recommended_semantic_ratio
            print(f"Auto Mode: Using LLM-recommended semantic_ratio: {semantic_ratio:.2f}")
        else:
            print(f"Manual Mode (or no LLM rec): Using provided semantic_ratio: {semantic_ratio:.2f}")

        # 2. Build Meilisearch filter expression
        # 這裡會呼叫 db_adapter_meili.py 的 build_meili_filter
        # 因為上面已經把 intent.websites 更新了，所以這裡會自動產生 website IN [...] 的語法
        meili_filter = build_meili_filter(intent)

        # 2.1 Enforce "Must Have" keywords via Soft Boosting
        
        # We append critical keywords multiple times (e.g., 3x) to the query string.
        # Mechanics:
        # - No quotes: Preserves Meilisearch's typo tolerance (GEMNI -> GEMINI works).
        # - Repetition: Heavily boosts the BM25/keyword score contribution for these terms.
        #   If a doc is missing these terms, its keyword score will near-zero, dragging down the final hybrid score
        #   even if the vector score is high.
        if intent.must_have_keywords:
            # Repeat 2 times for strong boosting
            boosted_keywords = []
            for kw in intent.must_have_keywords:
                boosted_keywords.extend([kw] * 2)

            intent.keyword_query = (
                f"{intent.keyword_query} {' '.join(boosted_keywords)}"
            )
            # print(f"Boosting critical keywords (2x): {intent.must_have_keywords}"

        # 3. Generate query embedding for semantic search
        query_vector = None
        if semantic_ratio > 0:
            # Only generate embedding if we're using semantic search
            print(f"Generating embedding for: '{intent.semantic_query}'")
            try:
                query_vector = vector_utils.get_embedding(intent.semantic_query)
                if query_vector:
                    print(f"  Embedding generated (dim: {len(query_vector)})")
                else:
                    print("  Embedding generation returned empty vector")
            except Exception as e:
                print(f"  Embedding generation failed: {e}")
                import traceback
                traceback.print_exc()
                query_vector = None

            if not query_vector:
                print("Embedding generation failed. Falling back to keyword-only search.")
                semantic_ratio = 0

        # 4. Single Meilisearch API call (Hybrid Search)
        print(f"Calling Meilisearch...")
        print(f"  Keyword query: '{intent.keyword_query}'")
        print(f"  Has vector: {query_vector is not None}")
        print(f"  Filter: {meili_filter}")
        print(f"  Pre-search limit: {PRE_SEARCH_LIMIT}")
        print(f"  Semantic ratio: {semantic_ratio}")

        try:
            results = self.meili_adapter.search(
                query=intent.keyword_query,
                vector=query_vector,
                filters=meili_filter,
                limit=PRE_SEARCH_LIMIT,
                semantic_ratio=semantic_ratio,
            )
            print(f"  Meilisearch returned {len(results)} results")
        except Exception as e:
            print(f"  Meilisearch search failed: {e}")
            import traceback
            traceback.print_exc()
            raise

        # 4.1 Merge documents with same link
        merged_results = self._merge_duplicate_links(results)
        print(f"  After merging duplicates: {len(merged_results)} results")

        # 4.2 Take top limit results
        final_results = merged_results[:limit]
        print(f"  Final results (top {limit}): {len(final_results)} results")

        # 5. Return results with intent
        print(f"DEBUG - Before serialization:")
        print(f"  intent.year_month: {intent.year_month}")
        print(f"  intent.workspaces: {intent.workspaces}")
        serialized_intent = (
            intent.model_dump() if hasattr(intent, "model_dump") else intent.dict()
        )
        
        # Debug print updated with websites info
        print(f"DEBUG - Intent Summary:")
        print(f"  year_month: {serialized_intent.get('year_month')}")
        print(f"  workspaces: {serialized_intent.get('workspaces')}")
        print(f"  websites: {serialized_intent.get('websites')}")

        response = {
            "intent": serialized_intent,
            "meili_filter": meili_filter,
            "results": final_results,
            "final_semantic_ratio": semantic_ratio,
        }

        if llm_error:
            response["llm_error"] = llm_error

        return response
