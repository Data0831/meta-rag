"""
Search Service - Simplified with Meilisearch Hybrid Search

This service uses Meilisearch for unified hybrid search that combines:
- Keyword search (with fuzzy matching and typo tolerance)
- Semantic vector search
- Strict metadata filtering

No more RRF fusion needed - Meilisearch handles it internally!
"""

from typing import Dict, Any, Optional
from src.llm.client import LLMClient
from src.llm.search_prompts import SEARCH_INTENT_PROMPT
from src.schema.schemas import SearchIntent, SearchFilters
from src.database.db_adapter_meili import MeiliAdapter, build_meili_filter
from src.database import vector_utils
from src.config import MEILISEARCH_HOST, MEILISEARCH_API_KEY, MEILISEARCH_INDEX
from meilisearch_config import DEFAULT_SEMANTIC_RATIO
from datetime import datetime


# Month format conversion mapping (YYYY-MM -> YYYY-monthname)
MONTH_NUM_TO_NAME = {
    "01": "january",
    "02": "february",
    "03": "march",
    "04": "april",
    "05": "may",
    "06": "june",
    "07": "july",
    "08": "august",
    "09": "september",
    "10": "october",
    "11": "november",
    "12": "december",
}


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

    def __init__(self):
        self.llm_client = LLMClient()
        self.meili_adapter = MeiliAdapter(
            host=MEILISEARCH_HOST,
            api_key=MEILISEARCH_API_KEY,
            collection_name=MEILISEARCH_INDEX,
        )

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

    def search(
        self,
        user_query: str,
        limit: int = 20,
        semantic_ratio: float = DEFAULT_SEMANTIC_RATIO,
        enable_llm: bool = True,
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

        Returns:
            Dictionary with:
            - intent: Parsed search intent (includes recommended_semantic_ratio)
            - results: List of ranked documents from Meilisearch
        """
        # 1. Parse Intent
        intent = None
        if enable_llm:
            intent = self.parse_intent(user_query)

        if not intent:
            if enable_llm:
                # Fallback if intent parsing fails
                print("⚠ Intent parsing failed. Using fallback basic search.")

            # Basic intent (no filters, raw query)
            intent = SearchIntent(
                filters=SearchFilters(),  # Empty filters
                keyword_query=user_query,
                semantic_query=user_query,
            )

        # Override limit if specified in intent
        if intent.limit is not None:
            limit = intent.limit

        # Use LLM-recommended semantic_ratio (unless user explicitly overrides)
        if intent.recommended_semantic_ratio is not None:
            semantic_ratio = intent.recommended_semantic_ratio
            print(f"🎯 Using LLM-recommended semantic_ratio: {semantic_ratio:.2f}")

        # Convert month format from YYYY-MM to YYYY-monthname
        if intent.filters.months:
            converted_months = []
            for month_str in intent.filters.months:
                # Check if format is YYYY-MM
                if "-" in month_str and len(month_str.split("-")) == 2:
                    year, month_num = month_str.split("-")
                    if month_num in MONTH_NUM_TO_NAME:
                        # Convert to YYYY-monthname format to match database
                        converted_months.append(
                            f"{year}-{MONTH_NUM_TO_NAME[month_num]}"
                        )
                    else:
                        converted_months.append(month_str)
                else:
                    converted_months.append(month_str)
            intent.filters.months = converted_months

        # 2. Build Meilisearch filter expression
        meili_filter = build_meili_filter(intent.filters)

        # 3. Generate query embedding for semantic search
        query_vector = None
        if semantic_ratio > 0:
            # Only generate embedding if we're using semantic search
            query_vector = vector_utils.get_embedding(intent.semantic_query)
            if not query_vector:
                print(
                    "⚠ Embedding generation failed. Falling back to keyword-only search."
                )

        # 4. Single Meilisearch API call (Hybrid Search)
        results = self.meili_adapter.search(
            query=intent.keyword_query,
            vector=query_vector,
            filters=meili_filter,
            limit=limit,
            semantic_ratio=semantic_ratio,
        )

        # 5. Return results with intent
        return {
            "intent": (
                intent.model_dump() if hasattr(intent, "model_dump") else intent.dict()
            ),
            "results": results,
        }
