import re
import json
from typing import Dict, Any, List
from src.agents.tool import SearchTool
from src.llm.client import LLMClient
from src.tool.ANSI import print_red

from src.llm.prompts.check_relevance import CHECK_RELEVANCE_PROMPT
from src.llm.prompts.query_rewrite import QUERY_REWRITE_PROMPT


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

    def _rewrite_query(
        self, original_query: str, current_query: str, bad_results: List[Dict]
    ) -> str:
        """
        Uses LLM to rewrite the query based on failure.
        """
        prompt = QUERY_REWRITE_PROMPT.format(
            original_query=original_query, current_query=current_query
        )
        try:
            response = self.llm_client.call_gemini(
                messages=[{"role": "user", "content": prompt}], temperature=0.7
            )
            return response.strip()
        except:
            return original_query

    def generate_summary(self, query: str, initial_results: List[Dict]):
        """
        Agentic Summary Generation (Streaming Version):
        1. Check relevance of provided results.
        2. If good -> Summarize.
        3. If bad -> Start Search Loop (max 1 retries).
        4. Summarize final results.
        """
        from src.config import DEFAULT_SIMILARITY_THRESHOLD

        # Use a dict to deduplicate by ID, storing only results that meet the threshold
        collected_results = {}
        query_history = [query]

        # 0. Initial Filtering & Accumulation
        # Filter initial results by threshold and add to collection
        for r in initial_results:
            # If _rankingScore is missing, we assume it might be relevant (or check logic elsewhere)
            # But here we strictly follow: "超過就保留，低於就移除"
            score = r.get("_rankingScore")
            if score is not None and score >= DEFAULT_SIMILARITY_THRESHOLD:
                collected_results[r.get("id")] = r

        # 1. Initial Check
        yield {"status": "checking", "message": "正在檢查初始搜尋結果的關聯性..."}

        # We check relevance against the *collected* (high quality) results if any,
        # or fall back to checking strict relevance on original set if collection is empty
        # (though if collection is empty, it means all were below threshold).

        # Let's perform relevance check on the *collected* items + any others?
        # User requirement: "retry 搜索的結果不要重複，但高 match 值的結果要保留下來，合併去重到下次的結果內"
        # So we base our decisions on the *accumulated* set.

        current_check_target = (
            list(collected_results.values()) if collected_results else initial_results
        )
        is_relevant, relevant_ids = self._check_relevance(query, current_check_target)

        if is_relevant and collected_results:
            yield {
                "status": "summarizing",
                "message": "搜尋結果高度相關，正在為您生成公告總結...",
            }
            summary = self.tool.summarize(query, list(collected_results.values()))
            yield {
                "status": "complete",
                "summary": summary,
                "results": list(collected_results.values()),
            }
            return

        # 2. If valid results not found or insufficient, start loop
        yield {
            "status": "rewriting",
            "message": "初始結果關聯度不足，AI 正在嘗試重寫查詢語句...",
            "original_query": query,
        }

        current_query = query
        retry_count = 0

        while retry_count < self.max_retries:
            # Rewrite with history
            new_query = self._rewrite_query_with_history(
                query, current_query, query_history
            )
            query_history.append(new_query)

            yield {
                "status": "searching",
                "message": f"AI 正在嘗試使用新關鍵字重新搜尋：'{new_query}'...",
                "new_query": new_query,
            }

            current_query = new_query

            # Search - exclude IDs we already have in our collection
            search_response = self.tool.search(
                current_query, exclude_ids=list(collected_results.keys())
            )
            new_results = search_response.get("results", [])

            if not new_results:
                retry_count += 1
                if retry_count < self.max_retries:
                    yield {
                        "status": "retrying",
                        "message": "未找到結果，嘗試再次調整查詢語句...",
                    }
                continue

            # Accumulate new high-score results
            found_new_high_score = False
            for r in new_results:
                score = r.get("_rankingScore")
                if score is not None and score >= DEFAULT_SIMILARITY_THRESHOLD:
                    if r.get("id") not in collected_results:
                        collected_results[r.get("id")] = r
                        found_new_high_score = True

            # Check relevance on the *updated* collection
            yield {"status": "checking", "message": "正在評估重新搜尋結果的關聯性..."}

            # If we have collected results, we check them. If still empty, we might check the raw new_results
            # just to see if LLM thinks they are relevant despite low score (edge case),
            # but user rule says "low score -> remove". So we stick to collected_results.

            if not collected_results:
                # If nothing passed threshold, we effectively have no results to summarize.
                # We force a retry if possible.
                is_relevant = False
            else:
                is_relevant, relevant_ids = self._check_relevance(
                    query, list(collected_results.values())
                )

            if is_relevant:
                yield {
                    "status": "summarizing",
                    "message": "找到相關資訊，正在為您生成總結內容...",
                }
                summary = self.tool.summarize(query, list(collected_results.values()))
                yield {
                    "status": "complete",
                    "summary": summary,
                    "results": list(collected_results.values()),
                }
                return

            # If not relevant or explicitly bad, we continue
            retry_count += 1
            if retry_count < self.max_retries:
                yield {
                    "status": "rewriting",
                    "message": "結果仍未達標，正在進行最後一次重寫嘗試...",
                }

        # Fallback
        final_list = list(collected_results.values())
        if final_list:
            # If we have some results but LLM didn't think they were seemingly "perfectly relevant" or sufficient,
            # we still try to summarize what we have.
            summary = self.tool.summarize(query, final_list)
            yield {"status": "complete", "summary": summary, "results": final_list}
        else:
            yield {
                "status": "complete",
                "summary": "抱歉，經由多次搜尋仍未找到足夠相關的資訊以生成摘要。",
                "results": [],
            }

    def _rewrite_query_with_history(
        self, original_query: str, current_query: str, history: List[str]
    ) -> str:
        """
        Uses LLM to rewrite the query with history awareness.
        """
        from src.llm.prompts.retry_query_rewrite import RETRY_QUERY_REWRITE_PROMPT

        prompt = RETRY_QUERY_REWRITE_PROMPT.format(
            original_query=original_query, current_query=current_query, history=history
        )
        try:
            response = self.llm_client.call_gemini(
                messages=[{"role": "user", "content": prompt}], temperature=0.7
            )
            return response.strip()
        except Exception as e:
            print_red(f"Rewrite failed: {e}")
            return original_query
