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
import traceback


class SearchService:
    def __init__(self, enable_debug: bool = False):
        self.enable_debug = enable_debug
        # 這裡只做輕量初始化，真正的連線檢查放在 search 或獨立的 check 方法中
        self.meili_adapter = None
        self.llm_client = None

        if self.enable_debug:
            print(" SearchService.__init__() called")
            print(f"  MEILISEARCH_HOST: {MEILISEARCH_HOST}")
            print(f"  MEILISEARCH_INDEX: {MEILISEARCH_INDEX}")

    def _init_meilisearch(self) -> str | None:
        try:
            if not self.meili_adapter:
                self.meili_adapter = MeiliAdapter(
                    host=MEILISEARCH_HOST,
                    api_key=MEILISEARCH_API_KEY,
                    collection_name=MEILISEARCH_INDEX,
                )
            self.meili_adapter.client.health()
            return None
        except Exception as e:
            msg = f"MeiliAdapter initialization failed: {str(e)}"
            print_red(msg)
            return msg

    def _check_embedding_service(self, test_text: str = "test") -> str | None:
        try:
            result = vector_utils.get_embedding(test_text)
            if result.get("status") == "failed":
                return result.get("error")
            if not result.get("result"):
                return "Embedding service returned empty vector"
            return None
        except Exception as e:
            msg = f"Embedding service check failed: {str(e)}"
            print_red(msg)
            return msg

    def _init_llm(self) -> str | None:
        """嘗試初始化 LLM Client"""
        try:
            if not self.llm_client:
                self.llm_client = LLMClient()
            return None
        except Exception as e:
            msg = f"LLMClient initialization failed: {str(e)}"
            print_red(msg)
            return msg

    def parse_intent(self, user_query: str) -> Dict[str, Any]:
        try:
            system_prompt = SEARCH_INTENT_PROMPT.format(
                current_date=datetime.now().strftime("%Y-%m-%d")
            )
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query},
            ]
            result = self.llm_client.call_with_schema(
                messages=messages, response_model=SearchIntent, temperature=0.0
            )
            return result
        except Exception as e:
            print_red(f"System prompt formatting or LLM call failed: {e}")
            return {
                "status": "failed",
                "error": f"System prompt formatting or LLM call failed: {str(e)}",
                "stage": "intent_parsing",
            }

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
                # Avoid appending if content is identical (optional optimization)
                if new_content not in existing_content:
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

        # --- Stage 1: Check Meilisearch Connection ---
        if err := self._init_meilisearch():
            return {"error": err, "status": "failed", "stage": "meilisearch"}

        # --- Stage 2: Check Embedding Service ---
        # 只有在需要語義搜索時才檢查 embedding，或者根據您的需求強制檢查
        if semantic_ratio > 0 or not manual_semantic_ratio:
            if err := self._check_embedding_service():
                # 根據需求，embedding 失敗可以是 Fatal 或是降級為關鍵字搜尋
                # 您的需求是「停止」，所以這裡直接回傳 error
                return {"error": err, "status": "failed", "stage": "embedding"}

        # --- Stage 3: Check/Init LLM Service ---
        if enable_llm:
            if err := self._init_llm():
                return {"error": err, "status": "failed", "stage": "llm"}

        # --- Stage 4: Execution (Run) ---
        try:
            # 4.1 Parse Intent (Using LLM)
            intent = None
            llm_error = None
            traces = []  # Log search steps

            if enable_llm:
                intent_result = self.parse_intent(user_query)
                if intent_result.get("status") == "failed":
                    llm_error = intent_result.get("error")
                    print_red(f"LLM Intent parsing failed: {llm_error}")
                    if not fall_back:
                        return intent_result
                else:
                    intent = intent_result.get("result")
                    # Fix: If LLM returns empty query strings (e.g. for nonsense input), fallback to user_query
                    if not intent.keyword_query or not intent.keyword_query.strip():
                        intent.keyword_query = user_query
                        traces.append("Warning: LLM returned empty keyword_query, fallback to origin user_query")
                    if not intent.semantic_query or not intent.semantic_query.strip():
                        intent.semantic_query = user_query
                        traces.append("Warning: LLM returned empty semantic_query, fallback to origin user_query")

            # Fallback intent if LLM failed or disabled
            if not intent:
                intent = SearchIntent(
                    keyword_query=user_query, semantic_query=user_query, sub_queries=[]
                )

            # Update params based on intent
            if intent.limit is not None:
                limit = intent.limit
            if (
                not manual_semantic_ratio
                and intent.recommended_semantic_ratio is not None
            ):
                semantic_ratio = intent.recommended_semantic_ratio

            # 4.2 Build Query Batch
            # Collect all distinct queries: primary intent + sub_queries
            query_candidates = []

            # Add primary (original intent)
            query_candidates.append(intent.keyword_query)
            traces.append(f"Primary Query: {intent.keyword_query}")

            # Add sub-queries
            if intent.sub_queries:
                for sq in intent.sub_queries:
                    if sq and sq not in query_candidates:
                        query_candidates.append(sq)
                        traces.append(f"Sub-Query: {sq}")

            # 4.3 Prepare Batch Request
            meili_filter = build_meili_filter(intent)

            # Boost keywords logic
            boosted_suffix = ""
            if intent.must_have_keywords:
                boosted_keywords = []
                for kw in intent.must_have_keywords:
                    boosted_keywords.extend([kw] * 2)
                boosted_suffix = f" {' '.join(boosted_keywords)}"

            # Generate Embeddings & Build Multi-Search Queries
            multi_search_queries = []

            for q_text in query_candidates:
                # 1. Keyword Component
                final_kw_query = f"{q_text}{boosted_suffix}"

                # 2. Vector Component
                vector = None
                if semantic_ratio > 0:
                    text_for_embedding = q_text
                    # Use intent.semantic_query if this is the primary candidate
                    if q_text == intent.keyword_query and intent.semantic_query:
                        text_for_embedding = intent.semantic_query

                    embedding_result = vector_utils.get_embedding(text_for_embedding)
                    if embedding_result.get("status") == "success":
                        vector = embedding_result.get("result")
                    else:
                        print_red(
                            f"Embedding failed for '{q_text}': {embedding_result.get('error')}"
                        )

                # 3. Build Query Object
                search_params = {
                    "indexUid": MEILISEARCH_INDEX,
                    "q": final_kw_query,
                    "limit": PRE_SEARCH_LIMIT,
                    "attributesToRetrieve": ["*"],
                    "showRankingScore": True,
                    "showRankingScoreDetails": True,
                }

                if meili_filter:
                    search_params["filter"] = meili_filter

                if vector:
                    search_params["hybrid"] = {
                        "semanticRatio": semantic_ratio,
                        "embedder": "default",
                    }
                    search_params["vector"] = vector

                multi_search_queries.append(search_params)

            # 4.4 Execute Multi-Search
            if not multi_search_queries:
                return {
                    "status": "success",
                    "results": [],
                    "traces": traces,
                    "intent": (
                        intent.model_dump()
                        if hasattr(intent, "model_dump")
                        else intent.dict()
                    ),
                }

            batch_result = self.meili_adapter.multi_search(multi_search_queries)
            if batch_result.get("status") == "failed":
                return batch_result

            # 4.5 Aggregate Results
            raw_hits_batch = batch_result.get("result", {}).get("results", [])

            # Flatten and Deduplicate by ID
            all_hits = []
            seen_ids = set()

            for i, result_set in enumerate(raw_hits_batch):
                hits = result_set.get("hits", [])

                for hit in hits:
                    doc_id = hit.get("id")
                    if doc_id and doc_id not in seen_ids:
                        seen_ids.add(doc_id)
                        all_hits.append(hit)

            # 4.6 Rerank & Process
            pre_merge_limit = round(limit * 2.5)

            reranker = ResultReranker(all_hits, intent.must_have_keywords)
            reranked_results = reranker.rerank(
                top_k=pre_merge_limit, enable_rerank=enable_rerank
            )

            if reranked_results and "_rerank_score" in reranked_results[0]:
                reranked_results.sort(
                    key=lambda x: x.get("_rerank_score", 0), reverse=True
                )

            # Merge same links
            merged_results = self._merge_duplicate_links(reranked_results)
            final_results = merged_results[:limit]

            # 4.7 Response
            response = {
                "status": "success",
                "intent": (
                    intent.model_dump()
                    if hasattr(intent, "model_dump")
                    else intent.dict()
                ),
                "meili_filter": meili_filter,
                "results": final_results,
                "final_semantic_ratio": semantic_ratio,
                "mode": "semantic" if semantic_ratio > 0 else "keyword",
                "traces": traces,
            }
            if llm_error:
                response["llm_warning"] = llm_error

            return response

        except Exception as e:
            traceback.print_exc()
            return {
                "error": f"Unexpected error: {str(e)}",
                "status": "failed",
                "stage": "unknown",
            }
