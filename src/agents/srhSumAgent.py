import re
import json
from typing import Dict, Any, List
from src.agents.tool import SearchTool
from src.llm.client import LLMClient
from src.tool.ANSI import print_red
from src.llm.prompts.check_retry_search import CHECK_RETRY_SEARCH_PROMPT
from src.schema.schemas import RetrySearchDecision

MAX_QUERY_LENGTH = 100


class SrhSumAgent:
    def __init__(self):
        self.tool = SearchTool()
        self.llm_client = LLMClient()
        self.max_retries = 1

    def _check_retry_search(self, query: str, results: List[Dict]) -> Dict[str, Any]:
        if not results:
            return {
                "relevant": False,
                "search_direction": "無任何結果，請嘗試搜尋更通用的關鍵字",
                "decision": "無搜尋結果",
            }

        context_preview = ""
        for doc in results[:5]:
            context_preview += f"ID: {doc.get('id')}\nTitle: {doc.get('title')}\nContent: {str(doc.get('content'))[:200]}...\n\n"

        prompt = CHECK_RETRY_SEARCH_PROMPT.format(
            query=query, documents=context_preview
        )

        llm_response = self.llm_client.call_with_schema(
            messages=[{"role": "user", "content": prompt}],
            response_model=RetrySearchDecision,
            temperature=0.0,
        )

        if llm_response.get("status") == "success":
            validated_result = llm_response.get("result")
            return {
                "relevant": validated_result.relevant,
                "search_direction": validated_result.search_direction,
                "decision": validated_result.decision,
            }
        else:
            print_red(f"Retry check failed: {llm_response.get('error')}")
            return {
                "relevant": True,
                "search_direction": "",
                "decision": "評估失敗，採用現有內容",
            }

    def run(
        self,
        query: str,
        limit: int = 20,
        semantic_ratio: float = 0.5,
        enable_llm: bool = True,
        manual_semantic_ratio: bool = False,
        enable_keyword_weight_rerank: bool = True,
        start_date: str = None,
        end_date: str = None,
    ):
        
        # 如果輸入超過限制，直接 yield 錯誤並結束
        if len(query) > MAX_QUERY_LENGTH:
            yield {
                "status": "failed",
                "stage": "initial_search",
                "error": f"Input length exceeds limit of {MAX_QUERY_LENGTH} characters.",
                "error_stage": "validation"
            }
            return

        from src.config import (
            SCORE_PASS_THRESHOLD,
            get_score_min_threshold,
            FALLBACK_RESULT_COUNT,
        )

        score_min = get_score_min_threshold()
        threshold_info = f"，Pass: {SCORE_PASS_THRESHOLD:.2f}, Min: {score_min:.2f}"

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
            start_date=start_date,
            end_date=end_date,
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
            "message": "正在評估初始搜尋結果的品質...",
        }
        search_direction = ""
        if collected_results:
            results_list = list(collected_results.values())

            filtered = [
                r
                for r in results_list
                if r.get("_rankingScore", 0) >= SCORE_PASS_THRESHOLD
            ]
            if not filtered:
                sorted_all = sorted(
                    results_list,
                    key=lambda x: x.get("_rerank_score", x.get("_rankingScore", 0)),
                    reverse=True,
                )
                filtered = [
                    r
                    for r in sorted_all[:FALLBACK_RESULT_COUNT]
                    if r.get("_rankingScore", 0) >= score_min
                ]

            if filtered:
                scores = [r.get("_rankingScore", 0) for r in filtered]
                score_range_str = f"{min(scores):.2f}-{max(scores):.2f}"
                titles_str = "\n".join(
                    [f"  - {r.get('title', 'Unknown')}" for r in filtered[:3]]
                )
                yield {
                    "status": "success",
                    "stage": "filtered",
                    "message": f"找到 {len(filtered)} 筆相關資料（分數：{score_range_str}{threshold_info}）\n{titles_str}",
                }

            relevance_result = self._check_retry_search(query, results_list)
            search_direction = relevance_result.get("search_direction", "")

            if relevance_result["relevant"]:
                yield {
                    "status": "success",
                    "stage": "summarizing",
                    "message": f"{relevance_result.get('decision', '搜尋結果高度相關')}，正在為您生成公告總結...",
                }
                final_results = sorted(
                    list(collected_results.values()),
                    key=lambda x: x.get("_rerank_score", x.get("_rankingScore", 0)),
                    reverse=True,
                )[:limit]
                summary_response = self.tool.summarize(query, final_results)
                if summary_response.get("status") == "success":
                    yield {
                        "status": "success",
                        "stage": "complete",
                        "summary": summary_response.get("summary"),
                        "link_mapping": summary_response.get("link_mapping"),
                        "results": final_results,
                        "intent": final_intent,
                    }
                else:
                    yield {
                        "status": "failed",
                        "stage": "summarizing",
                        "error": summary_response.get("error"),
                    }
                return
            else:
                decision_msg = relevance_result.get("decision", "初始結果品質不足")
                yield {
                    "status": "success",
                    "stage": "rewriting",
                    "message": f"{decision_msg}，AI 正在嘗試根據優化方向重寫查詢...",
                    "original_query": query,
                    "direction": search_direction,
                }
        else:
            yield {
                "status": "success",
                "stage": "checking",
                "message": f"初始結果未達關聯度門檻（{threshold_info.strip('， ')}）...",
            }

            yield {
                "status": "success",
                "stage": "rewriting",
                "message": "無符合條件的搜尋結果，AI 正在嘗試重寫查詢語句...",
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
                direction=search_direction,
                start_date=start_date,
                end_date=end_date,
            )

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
                "message": "正在評估重新搜尋結果的品質...",
            }
            if collected_results:
                results_list = list(collected_results.values())

                filtered = [
                    r
                    for r in results_list
                    if r.get("_rankingScore", 0) >= SCORE_PASS_THRESHOLD
                ]
                if not filtered:
                    sorted_all = sorted(
                        results_list,
                        key=lambda x: x.get("_rerank_score", x.get("_rankingScore", 0)),
                        reverse=True,
                    )
                    filtered = [
                        r
                        for r in sorted_all[:FALLBACK_RESULT_COUNT]
                        if r.get("_rankingScore", 0) >= score_min
                    ]

                if filtered:
                    scores = [r.get("_rankingScore", 0) for r in filtered]
                    score_range_str = f"{min(scores):.2f}-{max(scores):.2f}"
                    titles_str = "\n".join(
                        [f"  - {r.get('title', 'Unknown')}" for r in filtered[:3]]
                    )
                    yield {
                        "status": "success",
                        "stage": "filtered",
                        "message": f"找到 {len(filtered)} 筆相關資料（分數：{score_range_str}{threshold_info}）\n{titles_str}",
                    }

                relevance_result = self._check_retry_search(query, results_list)
            else:
                relevance_result = {
                    "relevant": False,
                    "search_direction": "嘗試擴大範圍",
                    "decision": "無搜尋結果",
                }
            search_direction = relevance_result.get("search_direction", "")

            if relevance_result["relevant"]:
                decision_msg = relevance_result.get("decision", "找到相關資訊")
                yield {
                    "status": "success",
                    "stage": "summarizing",
                    "message": f"{decision_msg}，正在為您生成總結內容...",
                }
                final_results = sorted(
                    list(collected_results.values()),
                    key=lambda x: x.get("_rerank_score", x.get("_rankingScore", 0)),
                    reverse=True,
                )[:limit]
                summary_response = self.tool.summarize(query, final_results)
                if summary_response.get("status") == "success":
                    yield {
                        "status": "success",
                        "stage": "complete",
                        "summary": summary_response.get("summary"),
                        "link_mapping": summary_response.get("link_mapping"),
                        "results": final_results,
                        "intent": final_intent,
                    }
                else:
                    yield {
                        "status": "failed",
                        "stage": "summarizing",
                        "error": summary_response.get("error"),
                    }
                return
            retry_count += 1
            if retry_count < self.max_retries:
                yield {
                    "status": "success",
                    "stage": "rewriting",
                    "message": f"結果品質仍可優化，正在進行最後一次嘗試（方向：{search_direction}）...",
                }

        final_results = sorted(
            list(collected_results.values()),
            key=lambda x: x.get("_rerank_score", x.get("_rankingScore", 0)),
            reverse=True,
        )[:limit]
        if final_results:
            summary_response = self.tool.summarize(query, final_results)
            if summary_response.get("status") == "success":
                yield {
                    "status": "success",
                    "stage": "complete",
                    "summary": summary_response.get("summary"),
                    "link_mapping": summary_response.get("link_mapping"),
                    "results": final_results,
                    "intent": final_intent,
                }
            else:
                yield {
                    "status": "failed",
                    "stage": "summarizing",
                    "error": summary_response.get("error"),
                }
        else:
            yield {
                "status": "success",
                "stage": "complete",
                "summary": {
                    "brief_answer": "沒有參考資料",
                    "detailed_answer": "",
                    "general_summary": "",
                },
                "link_mapping": {},
                "results": [],
            }
