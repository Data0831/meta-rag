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
                "stage": "intent_parsing"
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

            if enable_llm:
                intent_result = self.parse_intent(user_query)
                if intent_result.get("status") == "failed":
                    llm_error = intent_result.get("error")
                    print_red(f"LLM Intent parsing failed: {llm_error}")
                    if not fall_back:
                        return intent_result
                else:
                    intent = intent_result.get("result")

            # Fallback intent if LLM failed or disabled
            if not intent:
                intent = SearchIntent(
                    keyword_query=user_query,
                    semantic_query=user_query,
                )

            # Update params based on intent
            if intent.limit is not None:
                limit = intent.limit
            if (
                not manual_semantic_ratio
                and intent.recommended_semantic_ratio is not None
            ):
                semantic_ratio = intent.recommended_semantic_ratio

            # 4.2 Build Filter & Boost Keywords
            meili_filter = build_meili_filter(intent)
            if intent.must_have_keywords:
                boosted_keywords = []
                for kw in intent.must_have_keywords:
                    boosted_keywords.extend([kw] * 2)
                intent.keyword_query = (
                    f"{intent.keyword_query} {' '.join(boosted_keywords)}"
                )

            # 4.3 Generate Embedding
            query_vector = None
            if semantic_ratio > 0:
                embedding_result = vector_utils.get_embedding(intent.semantic_query)
                if embedding_result.get("status") == "failed":
                    return embedding_result
                query_vector = embedding_result.get("result")

            # 4.4 Meilisearch Query
            search_result = self.meili_adapter.search(
                query=intent.keyword_query,
                vector=query_vector,
                filters=meili_filter,
                limit=PRE_SEARCH_LIMIT,
                semantic_ratio=semantic_ratio,
            )
            if search_result.get("status") == "failed":
                return search_result
            results = search_result.get("result")

            # 4.5 Rerank & Process
            pre_merge_limit = round(limit * 1.3) + 1
            reranker = ResultReranker(results, intent.must_have_keywords)
            reranked_results = reranker.rerank(
                top_k=pre_merge_limit, enable_rerank=enable_rerank
            )

            if reranked_results and "_rerank_score" in reranked_results[0]:
                reranked_results.sort(
                    key=lambda x: x.get("_rerank_score", 0), reverse=True
                )

            merged_results = self._merge_duplicate_links(reranked_results)
            final_results = merged_results[:limit]

            # 4.6 Response
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
            }
            if llm_error:
                response["llm_warning"] = (
                    llm_error  # 使用 warning 而非 error，因為 fallback 成功了
                )

            return response

        except Exception as e:
            traceback.print_exc()
            return {
                "error": f"Unexpected error: {str(e)}",
                "status": "failed",
                "stage": "unknown",
            }
