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
    MAX_SEARCH_LIMIT,
)
from meilisearch_config import DEFAULT_SEMANTIC_RATIO
from datetime import datetime
from src.tool.ANSI import print_red
from src.services.keyword_alg import ResultReranker
import traceback


class SearchService:
    def __init__(self, enable_debug: bool = False):
        self.enable_debug = enable_debug
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
        try:
            if not self.llm_client:
                self.llm_client = LLMClient()
            return None
        except Exception as e:
            msg = f"LLMClient initialization failed: {str(e)}"
            print_red(msg)
            return msg

    def parse_intent(
        self, user_query: str, history: List[str] = None, direction: str = ""
    ) -> Dict[str, Any]:
        try:
            previous_queries_str = str(history) if history else "None"

            system_prompt = SEARCH_INTENT_PROMPT.format(
                current_date=datetime.now().strftime("%Y-%m-%d"),
                previous_queries=previous_queries_str,
                direction=direction or "",
            )
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query},
            ]
            result = self.llm_client.call_with_schema(
                messages=messages,
                response_model=SearchIntent,
                temperature=0.7 if history else 0.0,
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
                if new_content not in existing_content:
                    existing_doc["content"] = (
                        f"{existing_content}\n\n --- \n\n{new_content}"
                    )
        return merged_results

    def search(
        self,
        user_query: str,
        limit: int = 20,
        semantic_ratio: float = DEFAULT_SEMANTIC_RATIO,
        enable_llm: bool = True,
        manual_semantic_ratio: bool = False,
        website_filters: Optional[List[str]] = None,  # 新增：接收 UI 傳來的網站列表
        enable_keyword_weight_rerank: bool = True,
        fall_back: bool = False,
        exclude_ids: List[str] = None,
        history: List[str] = None,
        direction: str = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:

        limit = min(limit, MAX_SEARCH_LIMIT)

        # --- Stage 1: Check Meilisearch Connection ---
        if err := self._init_meilisearch():
            return {"error": err, "status": "failed", "stage": "meilisearch"}

        # --- Stage 2: Check Embedding Service ---
        if semantic_ratio > 0 or not manual_semantic_ratio:
            if err := self._check_embedding_service():
                return {"error": err, "status": "failed", "stage": "embedding"}

        # --- Stage 3: Check/Init LLM Service ---
        if enable_llm:
            if err := self._init_llm():
                return {"error": err, "status": "failed", "stage": "llm"}

        # --- Stage 4: Execution (Run) ---
        try:
            intent = None
            llm_error = None
            traces = []

            if enable_llm:
                intent_result = self.parse_intent(
                    user_query, history=history, direction=direction
                )
                if intent_result.get("status") == "failed":
                    llm_error = intent_result.get("error")
                    print_red(f"LLM Intent parsing failed: {llm_error}")
                    if not fall_back:
                        return intent_result
                else:
                    intent = intent_result.get("result")
                    if not intent.keyword_query or not intent.keyword_query.strip():
                        intent.keyword_query = user_query
                        traces.append(
                            "Warning: LLM returned empty keyword_query, fallback to origin user_query"
                        )
                    if not intent.semantic_query or not intent.semantic_query.strip():
                        intent.semantic_query = user_query
                        traces.append(
                            "Warning: LLM returned empty semantic_query, fallback to origin user_query"
                        )

            if not intent:
                intent = SearchIntent(
                    keyword_query=user_query, semantic_query=user_query, sub_queries=[]
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
            if intent.limit is not None:
                limit = intent.limit
            if (
                not manual_semantic_ratio
                and intent.recommended_semantic_ratio is not None
            ):
                semantic_ratio = intent.recommended_semantic_ratio

            query_candidates = []

            query_candidates.append(intent.keyword_query)
            traces.append(f"Primary Query: {intent.keyword_query}")

            if intent.sub_queries:
                for sq in intent.sub_queries:
                    if sq and sq not in query_candidates:
                        query_candidates.append(sq)
                        traces.append(f"Sub-Query: {sq}")
            meili_filter = build_meili_filter(intent)

            ai_has_date_constraint = intent.year_month and len(intent.year_month) > 0

            if ai_has_date_constraint:
                print(
                    f"  [優先權判定] AI 已指定日期 {intent.year_month}，忽略手動日期篩選。"
                )
            else:
                date_filters = []

                if start_date:
                    ym_start = start_date[:7]
                    date_filters.append(f'year_month >= "{ym_start}"')

                if end_date:
                    ym_end = end_date[:7]
                    date_filters.append(f'year_month <= "{ym_end}"')

                if date_filters:
                    manual_date_filter = " AND ".join(date_filters)
                    print(f"  [手動過濾] 年月範圍: {manual_date_filter}")

                    if meili_filter:
                        meili_filter = f"({meili_filter}) AND ({manual_date_filter})"
                    else:
                        meili_filter = manual_date_filter

            if exclude_ids:
                exclude_filter_safe = (
                    f"id NOT IN [{', '.join([f'\"{eid}\"' for eid in exclude_ids])}]"
                )

                if meili_filter:
                    meili_filter = f"({meili_filter}) AND ({exclude_filter_safe})"
                else:
                    meili_filter = exclude_filter_safe
                traces.append(
                    f"Applied ID exclusion filter for {len(exclude_ids)} items."
                )

            multi_search_queries = []

            for q_text in query_candidates:
                final_kw_query = q_text

                vector = None
                if semantic_ratio > 0:
                    text_for_embedding = q_text
                    if q_text == intent.keyword_query and intent.semantic_query:
                        text_for_embedding = intent.semantic_query

                    embedding_result = vector_utils.get_embedding(text_for_embedding)
                    if embedding_result.get("status") == "success":
                        vector = embedding_result.get("result")
                    else:
                        print_red(
                            f"Embedding failed for '{q_text}': {embedding_result.get('error')}"
                        )

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

            raw_hits_batch = batch_result.get("result", {}).get("results", [])

            all_hits = []
            seen_ids = set()

            for i, result_set in enumerate(raw_hits_batch):
                hits = result_set.get("hits", [])

                for hit in hits:
                    doc_id = hit.get("id")
                    if doc_id and doc_id not in seen_ids:
                        seen_ids.add(doc_id)
                        all_hits.append(hit)

            pre_merge_limit = round(limit * 2.5)

            reranker = ResultReranker(all_hits, intent.must_have_keywords)
            reranked_results = reranker.rerank(
                top_k=pre_merge_limit,
                enable_keyword_weight_rerank=enable_keyword_weight_rerank,
            )

            if reranked_results and "_rerank_score" in reranked_results[0]:
                reranked_results.sort(
                    key=lambda x: x.get("_rerank_score", 0), reverse=True
                )

            merged_results = self._merge_duplicate_links(reranked_results)
            final_results = merged_results[:limit]

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
