import re
import json
from typing import Dict, Any, List
from src.agents.tool import SearchTool
from src.llm.client import LLMClient
from src.tool.ANSI import print_red

from src.llm.rag_prompts import CHECK_RELEVANCE_PROMPT, QUERY_REWRITE_PROMPT


class SrhSumAgent:
    def __init__(self):
        self.tool = SearchTool()
        self.llm_client = LLMClient()
        self.max_retries = 2

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

    def generate_summary(self, query: str, initial_results: List[Dict]) -> str:
        """
        Agentic Summary Generation:
        1. Check relevance of provided results.
        2. If good -> Summarize.
        3. If bad -> Start Search Loop (max 2 retries).
        4. Summarize final results.
        """
        current_results = initial_results

        # 1. Initial Check
        is_relevant, relevant_ids = self._check_relevance(query, current_results)

        if is_relevant:
            # Filter relevant
            final_results = [r for r in current_results if r.get("id") in relevant_ids]
            if not final_results:
                final_results = current_results
            return self.tool.summarize(query, final_results)

        # 2. If valid results not found in initial set, start loop
        print("Initial results irrelevant. Starting Agentic Search Loop...")
        exclude_ids = [r.get("id") for r in current_results if r.get("id")]

        current_query = query
        retry_count = 0

        while retry_count < self.max_retries:
            # Rewrite first since initial failed
            new_query = self._rewrite_query(query, current_query, current_results)
            print(f"Rewriting query: '{current_query}' -> '{new_query}'")
            current_query = new_query

            # Search
            search_response = self.tool.search(current_query, exclude_ids=exclude_ids)
            results = search_response.get("results", [])

            if not results:
                retry_count += 1
                continue

            # Check
            is_relevant, relevant_ids = self._check_relevance(query, results)
            if is_relevant:
                final_results = [r for r in results if r.get("id") in relevant_ids]
                if not final_results:
                    final_results = results
                return self.tool.summarize(query, final_results)

            # Bad again
            exclude_ids.extend([r.get("id") for r in results if r.get("id")])
            current_results = results  # for next rewrite context
            retry_count += 1

        return "抱歉，經由多次搜尋仍未找到足夠相關的資訊以生成摘要。"
