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

    def _check_relevance(self, query: str, results: List[Dict]) -> Dict[str, Any]:
        from src.config import (
            SCORE_PASS_THRESHOLD,
            SCORE_MIN_THRESHOLD,
            FALLBACK_RESULT_COUNT,
        )

        if not results:
            return {
                "is_relevant": False,
                "relevant_ids": [],
                "filtered_count": 0,
                "score_range": None,
                "titles": [],
            }

        filtered_results = []
        for doc in results:
            score = doc.get("_rankingScore")
            if score is not None and score >= SCORE_PASS_THRESHOLD:
                filtered_results.append(doc)

        if len(filtered_results) < 1:
            sorted_results = sorted(
                [r for r in results if r.get("_rankingScore") is not None],
                key=lambda x: x.get("_rankingScore", 0),
                reverse=True,
            )
            filtered_results = [
                r
                for r in sorted_results[:FALLBACK_RESULT_COUNT]
                if r.get("_rankingScore", 0) >= SCORE_MIN_THRESHOLD
            ]

        if not filtered_results:
            return {
                "is_relevant": False,
                "relevant_ids": [],
                "filtered_count": 0,
                "score_range": None,
                "titles": [],
            }

        context_preview = ""
        for doc in filtered_results[:5]:
            context_preview += f"ID: {doc.get('id')}\nTitle: {doc.get('title')}\nContent: {str(doc.get('content'))[:200]}...\n\n"

        prompt = CHECK_RELEVANCE_PROMPT.format(query=query, documents=context_preview)
        try:
            response = self.llm_client.call_gemini(
                messages=[{"role": "user", "content": prompt}], temperature=0.0
            )
            cleaned = response.strip().replace("```json", "").replace("```", "")
            data = json.loads(cleaned)

            scores = [r.get("_rankingScore", 0) for r in filtered_results]
            score_range = (min(scores), max(scores)) if scores else None
            titles = [r.get("title", "") for r in filtered_results]

            return {
                "is_relevant": data.get("relevant", False),
                "relevant_ids": data.get("relevant_ids", []),
                "filtered_count": len(filtered_results),
                "score_range": score_range,
                "titles": titles,
            }
        except Exception as e:
            print_red(f"Relevance check failed: {e}")
            scores = [r.get("_rankingScore", 0) for r in filtered_results]
            score_range = (min(scores), max(scores)) if scores else None
            titles = [r.get("title", "") for r in filtered_results]

            return {
                "is_relevant": True,
                "relevant_ids": [r.get("id") for r in filtered_results],
                "filtered_count": len(filtered_results),
                "score_range": score_range,
                "titles": titles,
            }

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

        final_intent = search_response.get("intent", {})

        # Yield detailed search results
        yield {
            "status": "success",
            "stage": "search_result",
            "results": initial_results,
            "intent": final_intent,
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
            relevance_result = self._check_relevance(
                query, list(collected_results.values())
            )

            if relevance_result["filtered_count"] > 0:
                score_range = relevance_result["score_range"]
                score_str = (
                    f"{score_range[0]:.2f}-{score_range[1]:.2f}"
                    if score_range
                    else "N/A"
                )
                titles_str = "\n".join(
                    [f"  - {title}" for title in relevance_result["titles"][:3]]
                )

                yield {
                    "status": "success",
                    "stage": "filtered",
                    "message": f"找到 {relevance_result['filtered_count']} 筆相關資料（分數：{score_str}）\n{titles_str}",
                }

            if relevance_result["is_relevant"]:
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
                    "intent": final_intent,
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
                final_intent = intent
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
                relevance_result = {"is_relevant": False, "filtered_count": 0}
            else:
                relevance_result = self._check_relevance(
                    query, list(collected_results.values())
                )

            if relevance_result["filtered_count"] > 0:
                score_range = relevance_result["score_range"]
                score_str = (
                    f"{score_range[0]:.2f}-{score_range[1]:.2f}"
                    if score_range
                    else "N/A"
                )
                titles_str = "\n".join(
                    [f"  - {title}" for title in relevance_result["titles"][:3]]
                )

                yield {
                    "status": "success",
                    "stage": "filtered",
                    "message": f"找到 {relevance_result['filtered_count']} 筆相關資料（分數：{score_str}）\n{titles_str}",
                }

            if relevance_result["is_relevant"]:
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
                    "intent": final_intent,
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
                "intent": final_intent,
            }
        else:
            yield {
                "status": "success",
                "stage": "complete",
                "summary": "抱歉，經由多次搜尋仍未找到足夠相關的資訊以生成摘要。",
                "results": [],
            }
