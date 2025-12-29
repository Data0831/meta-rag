from typing import Dict, Any, Optional, List
from src.llm.client import LLMClient
from src.llm.search_prompts import SEARCH_INTENT_PROMPT
from src.schema.schemas import SearchIntent
from src.database.db_adapter_meili import MeiliAdapter, build_meili_filter
from src.database import vector_utils
from src.config import (
    MEILISEARCH_HOST,
    MEILISEARCH_API_KEY,
    MEILISEARCH_INDEX,
    PRE_SEARCH_LIMIT,
)
from meilisearch_config import DEFAULT_SEMANTIC_RATIO
from datetime import datetime
from src.tool.ANSI import print_red
from src.services.keyword_alg import ResultReranker


class SearchService:
    def __init__(self, enable_debug: bool = False):
        self.enable_debug = enable_debug
        if self.enable_debug:
            print(" SearchService.__init__() called")
            print(f"  MEILISEARCH_HOST: {MEILISEARCH_HOST}")
            print(f"  MEILISEARCH_INDEX: {MEILISEARCH_INDEX}")
        try:
            self.llm_client = LLMClient()
        except Exception as e:
            print_red(f"  LLMClient initialization failed: {e}")
            raise
        try:
            self.meili_adapter = MeiliAdapter(
                host=MEILISEARCH_HOST,
                api_key=MEILISEARCH_API_KEY,
                collection_name=MEILISEARCH_INDEX,
            )
        except Exception as e:
            print_red(f"  MeiliAdapter initialization failed: {e}")
            raise

    def parse_intent(self, user_query: str) -> Optional[SearchIntent]:
        try:
            system_prompt = SEARCH_INTENT_PROMPT.format(
                current_date=datetime.now().strftime("%Y-%m-%d")
            )
        except Exception as e:
            print_red(f"System prompt formatting failed: {e}")
            raise

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query},
        ]
        intent = self.llm_client.call_with_schema(
            messages=messages, response_model=SearchIntent, temperature=0.0
        )
        return intent

    def _merge_duplicate_links(
        self, results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
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
        enable_rerank: bool = True,
        fall_back: bool = False,
    ) -> Dict[str, Any]:
        # 1. Parse Intent
        intent = None
        llm_error = None
        if enable_llm:
            try:
                intent = self.parse_intent(user_query)
            except Exception as e:
                print_red(f"LLM Intent parsing failed: {e} | {user_query}")
                llm_error = str(e)
                if not fall_back:
                    raise
        if not intent:
            if enable_llm:
                print_red("Intent parsing failed. Using fallback basic search.")
            intent = SearchIntent(
                keyword_query=user_query,
                semantic_query=user_query,
            )
        if intent.limit is not None:
            limit = intent.limit
        if not manual_semantic_ratio and intent.recommended_semantic_ratio is not None:
            semantic_ratio = intent.recommended_semantic_ratio

        # 2. Build Meilisearch filter expression
        meili_filter = build_meili_filter(intent)
        # 2.1 Enforce "Must Have" keywords via Soft Boosting
        if intent.must_have_keywords:
            boosted_keywords = []
            for kw in intent.must_have_keywords:
                boosted_keywords.extend([kw] * 2)
            intent.keyword_query = (
                f"{intent.keyword_query} {' '.join(boosted_keywords)}"
            )

        # 3. Generate query embedding for semantic search
        query_vector = None
        if semantic_ratio > 0:
            try:
                query_vector = vector_utils.get_embedding(intent.semantic_query)
                if query_vector:
                    if self.enable_debug:
                        print(
                            f"Generating embedding for: '{intent.semantic_query}' Embedding (dim: {len(query_vector)})"
                        )
            except Exception as e:
                print_red(f"  Embedding generation failed: {e}")
                import traceback

                traceback.print_exc()
                if not fall_back:
                    raise
                query_vector = None
            if not query_vector:
                print_red(
                    "Embedding generation failed. Falling back to keyword-only search."
                )
                semantic_ratio = 0

        # 4. Single Meilisearch API call (Hybrid Search)
        if self.enable_debug:
            print(f"\nKeyword query: '{intent.keyword_query}'")
            print(f"Has vector: {query_vector is not None}")
            print(f"Filter: {meili_filter}")
            print(f"Semantic ratio: {semantic_ratio}")

        try:
            results = self.meili_adapter.search(
                query=intent.keyword_query,
                vector=query_vector,
                filters=meili_filter,
                limit=PRE_SEARCH_LIMIT,
                semantic_ratio=semantic_ratio,
            )
            if self.enable_debug:
                print(
                    f"  Meilisearch {len(results)} / {PRE_SEARCH_LIMIT} Pre-search limit"
                )
        except Exception as e:
            print_red(f"  Meilisearch search failed: {e}")
            import traceback

            traceback.print_exc()
            raise

        pre_merge_limit = round(limit * 1.3) + 1
        reranker = ResultReranker(results, intent.must_have_keywords)
        reranked_results = reranker.rerank(
            top_k=pre_merge_limit, enable_rerank=enable_rerank
        )
        if self.enable_debug:
            print(
                f"  After reranking: {len(reranked_results)} results (top {pre_merge_limit})"
            )

        if reranked_results and "_rerank_score" in reranked_results[0]:
            reranked_results.sort(key=lambda x: x.get("_rerank_score", 0), reverse=True)

        # 4.1 Merge documents with same link
        merged_results = self._merge_duplicate_links(reranked_results)
        if self.enable_debug:
            print(f"  After merging duplicates: {len(merged_results)} results")
        # 4.2 Take top limit results
        final_results = merged_results[:limit]
        print(f"  Final results (top {limit}): {len(final_results)} results")
        # 5. Return results with intent
        serialized_intent = (
            intent.model_dump() if hasattr(intent, "model_dump") else intent.dict()
        )
        response = {
            "intent": serialized_intent,
            "meili_filter": meili_filter,
            "results": final_results,
            "final_semantic_ratio": semantic_ratio,
            "mode": "semantic" if semantic_ratio > 0 else "keyword",
        }
        if llm_error:
            response["llm_error"] = llm_error
        return response
