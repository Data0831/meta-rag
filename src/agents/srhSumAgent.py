import re
import json
from typing import Dict, Any, List
from src.agents.tool import SearchTool
from src.llm.client import LLMClient
from src.tool.ANSI import print_red
from src.llm.prompts.check_retry_search import (
    CHECK_RETRY_SEARCH_SYSTEM_INSTRUCTION,
    CHECK_RETRY_SEARCH_USER_TEMPLATE,
)
from src.schema.schemas import RetrySearchDecision
from src.config import SEARCH_MAX_RETRIES


class SrhSumAgent:
    def __init__(self):
        self.tool = SearchTool()
        self.llm_client = LLMClient()
        self.max_retries = SEARCH_MAX_RETRIES

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

        system_msg = CHECK_RETRY_SEARCH_SYSTEM_INSTRUCTION
        user_msg = CHECK_RETRY_SEARCH_USER_TEMPLATE.format(
            query=query, documents=context_preview
        )

        llm_response = self.llm_client.call_with_schema(
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
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

    def _add_results(
        self,
        collected_results: Dict[str, Any],
        all_seen_ids: set,
        new_results: List[Dict],
    ):
        from src.config import SCORE_PASS_THRESHOLD

        for r in new_results:
            # 1. 記錄所有看到的片段 ID，用於下一次搜尋的 exclude_ids
            ids_to_record = (
                r.get("all_ids", [r.get("id")])
                if r.get("id") or r.get("all_ids")
                else []
            )
            for rid in ids_to_record:
                if rid:
                    all_seen_ids.add(rid)

            # 2. 決定合併的 Key (優先用 link，無 link 用 id)
            link = r.get("link")
            primary_id = r.get("id")
            key = link if link else primary_id
            if not key:
                continue

            # 3. 執行合併邏輯
            if key in collected_results:
                existing = collected_results[key]

                # 合併 all_ids
                if "all_ids" not in existing:
                    existing["all_ids"] = (
                        [existing.get("id")] if existing.get("id") else []
                    )
                for rid in ids_to_record:
                    if rid and rid not in existing["all_ids"]:
                        existing["all_ids"].append(rid)

                # 合併內容 (檢查內容是否重複)
                new_content = r.get("content", "")
                existing_content = existing.get("content", "")
                if new_content and new_content not in existing_content:
                    existing["content"] = (
                        f"{existing_content}\n\n --- \n\n{new_content}"
                    )
                    
                    # 合併 token 計數
                    existing_token = existing.get("token", 0)
                    new_token = r.get("token", 0)
                    existing["token"] = existing_token + new_token

                # 保留最高分
                new_score = r.get("_rankingScore", 0)
                if new_score > existing.get("_rankingScore", 0):
                    existing["_rankingScore"] = new_score
                    if "_rerank_score" in r:
                        existing["_rerank_score"] = r["_rerank_score"]
            else:
                # 新結果：初始化
                if "all_ids" not in r:
                    r["all_ids"] = ids_to_record
                score = r.get("_rankingScore", 0)
                r["score_pass"] = score >= SCORE_PASS_THRESHOLD
                collected_results[key] = r

    def run(
        self,
        query: str,
        limit: int = 20,
        semantic_ratio: float = 0.5,
        enable_llm: bool = True,
        manual_semantic_ratio: bool = False,
        start_date: str = None,
        end_date: str = None,
        website: List[str] = None,
        is_retry_search: bool = False,
    ):

        from src.config import (
            SCORE_PASS_THRESHOLD,
            MAX_SEARCH_LIMIT,
        )

        threshold_info = f"，Pass: {SCORE_PASS_THRESHOLD:.2f}"

        collected_results = {}
        all_seen_ids = set()
        query_history = [query]
        all_sub_queries = []
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
            exclude_ids=None,
            history=None,
            direction=None,
            start_date=start_date,
            end_date=end_date,
            website=website,
            is_retry_search=is_retry_search,
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
        if final_intent:
            initial_sq = final_intent.get("sub_queries", [])
            initial_kw = final_intent.get("keyword_query")
            if initial_kw and initial_kw not in query_history:
                query_history.append(initial_kw)
            for sq in initial_sq:
                if sq and sq not in all_sub_queries:
                    all_sub_queries.append(sq)
                if sq and sq not in query_history:
                    query_history.append(sq)
            final_intent["sub_queries"] = sorted(all_sub_queries)

        yield {
            "status": "success",
            "stage": "search_result",
            "results": initial_results,
            "intent": final_intent,
            "link_mapping": search_response.get("link_mapping"),
            "meili_filter": search_response.get("meili_filter"),
        }

        self._add_results(collected_results, all_seen_ids, initial_results)

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
        current_limit = limit
        while retry_count < self.max_retries:
            current_limit = min(int(limit * 1.5), MAX_SEARCH_LIMIT)
            search_response = self.tool.search(
                query=query,
                limit=current_limit,
                semantic_ratio=semantic_ratio,
                enable_llm=enable_llm,
                manual_semantic_ratio=manual_semantic_ratio,
                exclude_ids=list(all_seen_ids),
                history=query_history,
                direction=search_direction,
                start_date=start_date,
                end_date=end_date,
                website=website,
                is_retry_search=True,
            )

            if search_response.get("status") == "success":
                intent = search_response.get("intent", {})
                final_intent = intent
                kw = intent.get("keyword_query")
                sq = intent.get("sub_queries", [])
                if kw and kw not in query_history:
                    query_history.append(kw)
                for q in sq:
                    if q and q not in all_sub_queries:
                        all_sub_queries.append(q)
                    if q and q not in query_history:
                        query_history.append(q)
                final_intent["sub_queries"] = sorted(all_sub_queries)

            yield {
                "status": "success",
                "stage": "search_result",
                "results": search_response.get("results", []),
                "intent": final_intent,
                "meili_filter": search_response.get("meili_filter"),
            }

            if search_response.get("status") == "success":
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

            self._add_results(collected_results, all_seen_ids, new_results)

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
                )[:current_limit]
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
        )[:current_limit]
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
                "intent": final_intent,
            }
