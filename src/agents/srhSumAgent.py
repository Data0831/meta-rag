import re
import json
from typing import Dict, Any, List
from src.agents.tool import SearchTool
from src.llm.client import LLMClient
from src.tool.ANSI import print_red
from src.llm.prompts.check_relevance import CHECK_RELEVANCE_PROMPT


class SrhSumAgent:
    def __init__(self):
        self.tool = SearchTool()
        self.llm_client = LLMClient()
        self.max_retries = 1

    def _check_relevance(self, query: str, results: List[Dict]) -> (bool, List[str]):
        """
        Uses LLM to check if results are relevant.
        Returns (is_relevant, list_of_relevant_ids)
        """
        if not results:
            return False, []
        context_preview = ""
        for doc in results[:5]:  # Check top 5
            context_preview += f"ID: {doc.get('id')}\nTitle: {doc.get('title')}\nContent: {str(doc.get('content'))[:200]}...\n\n"
        prompt = CHECK_RELEVANCE_PROMPT.format(query=query, documents=context_preview)
        try:
            response = self.llm_client.call_gemini(
                messages=[{"role": "user", "content": prompt}], temperature=0.0
            )
            # Parse JSON
            cleaned = response.strip().replace("```json", "").replace("```", "")
            data = json.loads(cleaned)
            return data.get("relevant", False), data.get("relevant_ids", [])
        except Exception as e:
            print_red(f"Relevance check failed: {e}")
            return True, [
                r.get("id") for r in results
            ]  # Default to true on error to avoid blocking

    def run(
        self,
        query: str,
        limit: int = 20,
        semantic_ratio: float = 0.5,
        enable_llm: bool = True,
        manual_semantic_ratio: bool = False,
        enable_keyword_weight_rerank: bool = True,
    ):
        from src.config import SCORE_PASS_THRESHOLD

        collected_results = {}
        all_seen_ids = set()
        query_history = [query]
        yield {
            "status": "success",
            "stage": "searching",
            "message": "正在執行初始搜尋...",
        }
        search_response = self.tool.search(
            query=query,
            limit=limit,
            semantic_ratio=semantic_ratio,
            enable_llm=enable_llm,
            manual_semantic_ratio=manual_semantic_ratio,
            enable_keyword_weight_rerank=enable_keyword_weight_rerank,
        )
        if search_response.get("status") == "failed":
            yield {
                "status": "failed",
                "stage": "initial_search",
                "error": search_response.get("error"),
                "error_stage": search_response.get("stage"),
            }
            return
        initial_results = search_response.get("results", [])

        # Yield detailed search results
        yield {
            "status": "success",
            "stage": "search_result",
            "results": initial_results,
            "intent": search_response.get("intent", {}),
            "meili_filter": search_response.get("meili_filter"),
        }

        for r in initial_results:
            rid = r.get("id")
            if rid:
                all_seen_ids.add(rid)
                score = r.get("_rankingScore")
                r["score_pass"] = score is not None and score >= SCORE_PASS_THRESHOLD
                collected_results[rid] = r

        yield {
            "status": "success",
            "stage": "checking",
            "message": "正在檢查初始搜尋結果的關聯性...",
        }
        if collected_results:
            is_relevant, relevant_ids = self._check_relevance(
                query, list(collected_results.values())
            )
            if is_relevant:
                yield {
                    "status": "success",
                    "stage": "summarizing",
                    "message": "搜尋結果高度相關，正在為您生成公告總結...",
                }
                final_results = sorted(
                    list(collected_results.values()),
                    key=lambda x: x.get("_rankingScore", 0),
                    reverse=True,
                )[:limit]
                summary = self.tool.summarize(query, final_results)
                yield {
                    "status": "success",
                    "stage": "complete",
                    "summary": summary,
                    "results": final_results,
                }
                return
        else:
            yield {
                "status": "success",
                "stage": "checking",
                "message": "初始結果未達關聯度門檻...",
            }

        yield {
            "status": "success",
            "stage": "rewriting",
            "message": "初始結果關聯度不足，AI 正在嘗試重寫查詢語句...",
            "original_query": query,
        }
        retry_count = 0
        while retry_count < self.max_retries:
            yield {
                "status": "success",
                "stage": "searching",
                "message": f"AI 正在參考歷史紀錄 ({len(query_history)} 筆) 規劃新的搜尋策略...",
            }
            search_response = self.tool.search(
                query=query,
                limit=limit,
                semantic_ratio=semantic_ratio,
                enable_llm=enable_llm,
                manual_semantic_ratio=manual_semantic_ratio,
                enable_keyword_weight_rerank=enable_keyword_weight_rerank,
                exclude_ids=list(all_seen_ids),
                history=query_history,
            )

            # Yield detailed retry search results
            yield {
                "status": "success",
                "stage": "search_result",
                "results": search_response.get("results", []),
                "intent": search_response.get("intent", {}),
                "meili_filter": search_response.get("meili_filter"),
            }

            if search_response.get("status") == "success":
                intent = search_response.get("intent", {})
                kw = intent.get("keyword_query")
                sq = intent.get("sub_queries", [])
                if kw and kw not in query_history:
                    query_history.append(kw)
                for q in sq:
                    if q and q not in query_history:
                        query_history.append(q)
                new_results = search_response.get("results", [])
                if kw:
                    yield {
                        "status": "success",
                        "stage": "searching",
                        "message": f"正在嘗試新策略搜尋：'{kw}'...",
                        "new_query": kw,
                    }
            else:
                new_results = []
            if not new_results:
                retry_count += 1
                if retry_count < self.max_retries:
                    yield {
                        "status": "success",
                        "stage": "retrying",
                        "message": "未找到結果，嘗試再次調整...",
                    }
                continue
            for r in new_results:
                rid = r.get("id")
                if rid:
                    all_seen_ids.add(rid)
                    if rid not in collected_results:
                        score = r.get("_rankingScore")
                        r["score_pass"] = (
                            score is not None and score >= SCORE_PASS_THRESHOLD
                        )
                        collected_results[rid] = r

            yield {
                "status": "success",
                "stage": "checking",
                "message": "正在評估重新搜尋結果的關聯性...",
            }
            if not collected_results:
                is_relevant = False
            else:
                is_relevant, relevant_ids = self._check_relevance(
                    query, list(collected_results.values())
                )
            if is_relevant:
                yield {
                    "status": "success",
                    "stage": "summarizing",
                    "message": "找到相關資訊，正在為您生成總結內容...",
                }
                final_results = sorted(
                    list(collected_results.values()),
                    key=lambda x: x.get("_rankingScore", 0),
                    reverse=True,
                )[:limit]
                summary = self.tool.summarize(query, final_results)
                yield {
                    "status": "success",
                    "stage": "complete",
                    "summary": summary,
                    "results": final_results,
                }
                return
            retry_count += 1
            if retry_count < self.max_retries:
                yield {
                    "status": "success",
                    "stage": "rewriting",
                    "message": "結果仍未達標，正在進行最後一次嘗試...",
                }

        final_results = sorted(
            list(collected_results.values()),
            key=lambda x: x.get("_rankingScore", 0),
            reverse=True,
        )[:limit]
        if final_results:
            summary = self.tool.summarize(query, final_results)
            yield {
                "status": "success",
                "stage": "complete",
                "summary": summary,
                "results": final_results,
            }
        else:
            yield {
                "status": "success",
                "stage": "complete",
                "summary": "抱歉，經由多次搜尋仍未找到足夠相關的資訊以生成摘要。",
                "results": [],
            }
