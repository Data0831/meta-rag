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

    def run(self, user_query: str) -> Dict[str, Any]:
        """
        Main execution loop for the Agentic RAG.
        """
        current_query = user_query
        exclude_ids = []
        retry_count = 0
        final_results = []
        traces = []

        while retry_count <= self.max_retries:
            traces.append(f"Attempt {retry_count + 1}: Searching for '{current_query}'")

            # 1. Search
            search_response = self.tool.search(current_query, exclude_ids=exclude_ids)
            results = search_response.get("results", [])
            traces.extend(search_response.get("traces", []))

            if not results:
                traces.append("No results found.")
                # We can retry if we haven't hit max, or just break if totally empty on first try?
                # If first try empty, maybe rewrite query?
                pass

            # 2. Check Relevance
            is_relevant, relevant_ids = self._check_relevance(current_query, results)

            if is_relevant:
                traces.append("Relevant results found.")
                # Filter to only keep relevant ones?? Or keep all returned by search?
                # User flow says "If relevant -> Generate Summary/Answer"
                # But maybe some are irrelevant.
                # Let's assume we pass the full filtered batch of 'relevant' docs or just the original top K.
                # To be precise: let's filter the results to only include relevant ones for the summary.
                final_results = [r for r in results if r.get("id") in relevant_ids]
                if not final_results:
                    # LLM said relevant but didn't return IDs? Fallback to all.
                    final_results = results
                break
            else:
                traces.append("Results not relevant.")
                # Add current result IDs to exclude list
                current_ids = [r.get("id") for r in results if r.get("id")]
                exclude_ids.extend(current_ids)

                if retry_count < self.max_retries:
                    # 3. Rewrite Query
                    new_query = self._rewrite_query(user_query, current_query, results)
                    traces.append(
                        f"Rewriting query: '{current_query}' -> '{new_query}'"
                    )
                    current_query = new_query
                    retry_count += 1
                else:
                    traces.append("Max retries reached. Falling back.")
                    break

        # Generate Answer or Summary
        # The user request said "Generate Summary". The RAGService previously generated a full RAG answer.
        # "剝離 summarize 讓查找完成後 agent 判別與問題是否有關，如果有去生成摘要"
        # So I will return the results and let RAGService formatting handle it,
        # OR I can generate the summary here and return it.
        # RAGService.chat expects: { "answer": ..., "suggestions": ..., "references": ... }
        # So I should return the data needed for that.

        return {
            "results": final_results,
            "traces": traces,
            "final_query": current_query,
        }

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

    def generate_summary(
        self,
        query: str,
        limit: int = 20,
        semantic_ratio: float = 0.5,
        enable_llm: bool = True,
        manual_semantic_ratio: bool = False,
        enable_keyword_weight_rerank: bool = True,
    ):
        """
        Agentic Summary Generation (Streaming Version):
        1. Execute initial search internally.
        2. Check relevance of results.
        3. If good -> Summarize.
        4. If bad -> Start Search Loop (max 1 retries) using history-aware search.
        5. Summarize final results.
        """
        from src.config import SCORE_PASS_THRESHOLD

        # Use a dict to deduplicate by ID, storing only results that meet the threshold
        collected_results = {}
        # Track ALL seen IDs to exclude them from future searches (even low score ones)
        all_seen_ids = set()

        # Initial history is just the user query
        query_history = [query]

        # 0. Execute Initial Search
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

        # 0.1. Initial Filtering & Accumulation
        for r in initial_results:
            rid = r.get("id")
            if rid:
                all_seen_ids.add(rid)
                score = r.get("_rankingScore")
                r["score_pass"] = score is not None and score >= SCORE_PASS_THRESHOLD
                collected_results[rid] = r

        print(f"[DEBUG] After initial search: collected_results={len(collected_results)}, all_seen_ids={len(all_seen_ids)}")

        # 1. Initial Check
        yield {
            "status": "success",
            "stage": "checking",
            "message": "正在檢查初始搜尋結果的關聯性...",
        }

        # Only check relevance if we have high-quality results.
        # If nothing met the threshold, we automatically consider it 'bad' and need retry.
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

                # Sort by score descending and limit to top-k
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
            # No results met the threshold
            yield {
                "status": "success",
                "stage": "checking",
                "message": "初始結果未達關聯度門檻...",
            }

        # 2. If valid results not found or insufficient, start loop
        yield {
            "status": "success",
            "stage": "rewriting",
            "message": "初始結果關聯度不足，AI 正在嘗試重寫查詢語句...",
            "original_query": query,
        }

        retry_count = 0

        while retry_count < self.max_retries:
            # Start search with history
            yield {
                "status": "success",
                "stage": "searching",
                "message": f"AI 正在參考歷史紀錄 ({len(query_history)} 筆) 規劃新的搜尋策略...",
            }

            # Search - exclude ALL IDs we have seen (both good and bad)
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

            # Extract actual used queries from response to update history
            if search_response.get("status") == "success":
                intent = search_response.get("intent", {})
                kw = intent.get("keyword_query")
                sq = intent.get("sub_queries", [])

                # Update history with what was actually used
                if kw and kw not in query_history:
                    query_history.append(kw)
                for q in sq:
                    if q and q not in query_history:
                        query_history.append(q)

                new_results = search_response.get("results", [])

                # UI Update
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

            # Accumulate new high-score results AND update seen_ids
            for r in new_results:
                rid = r.get("id")
                if rid:
                    all_seen_ids.add(rid)
                    if rid not in collected_results:
                        score = r.get("_rankingScore")
                        r["score_pass"] = score is not None and score >= SCORE_PASS_THRESHOLD
                        collected_results[rid] = r

            print(f"[DEBUG] After retry search: collected_results={len(collected_results)}, all_seen_ids={len(all_seen_ids)}")

            # Check relevance on the *updated* collection
            yield {
                "status": "success",
                "stage": "checking",
                "message": "正在評估重新搜尋結果的關聯性...",
            }

            if not collected_results:
                is_relevant = False
                print(f"[DEBUG] No collected_results, is_relevant=False")
            else:
                is_relevant, relevant_ids = self._check_relevance(
                    query, list(collected_results.values())
                )
                print(f"[DEBUG] Relevance check result: is_relevant={is_relevant}, relevant_ids_count={len(relevant_ids)}")

            if is_relevant:
                yield {
                    "status": "success",
                    "stage": "summarizing",
                    "message": "找到相關資訊，正在為您生成總結內容...",
                }

                # Sort by score descending and limit to top-k
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

            # If not relevant
            retry_count += 1
            if retry_count < self.max_retries:
                yield {
                    "status": "success",
                    "stage": "rewriting",
                    "message": "結果仍未達標，正在進行最後一次嘗試...",
                }

        # Fallback
        print(f"[DEBUG] Entering fallback: collected_results={len(collected_results)}, all_seen_ids={len(all_seen_ids)}")
        # Sort by score descending and limit to top-k
        final_results = sorted(
            list(collected_results.values()),
            key=lambda x: x.get("_rankingScore", 0),
            reverse=True,
        )[:limit]

        print(f"[DEBUG] Fallback final_results length: {len(final_results)}")
        if final_results:
            print(f"[DEBUG] Fallback final_results sample: {[(r.get('id')[:16], r.get('_rankingScore')) for r in final_results[:3]]}")

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
