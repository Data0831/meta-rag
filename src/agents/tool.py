from typing import List, Dict, Any
from src.services.search_service import SearchService
from src.llm.client import LLMClient
from src.llm.prompts.summary import SUMMARY_SYSTEM_PROMPT


class SearchTool:
    def __init__(self):
        self.search_service = SearchService()
        self.llm_client = LLMClient()

    def search(
        self,
        query: str,
        limit: int = 20,
        semantic_ratio: float = 0.5,
        enable_llm: bool = True,
        manual_semantic_ratio: bool = False,
        enable_keyword_weight_rerank: bool = True,
        exclude_ids: List[str] = None,
        history: List[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes a search using the SearchService.
        """
        return self.search_service.search(
            user_query=query,
            limit=limit,
            semantic_ratio=semantic_ratio,
            enable_llm=enable_llm,
            manual_semantic_ratio=manual_semantic_ratio,
            enable_keyword_weight_rerank=enable_keyword_weight_rerank,
            exclude_ids=exclude_ids,
            history=history,
        )

    def summarize(self, user_query: str, search_results: List[Dict]) -> str:
        """
        Summarizes the provided search results relevant to the user query.
        """
        if not search_results:
            return ""

        # 1. Prepare Context (Take top 5)
        context_text = ""
        for idx, doc in enumerate(search_results[:5], 1):
            title = doc.get("title", "No Title")
            # Handle potential None content
            content = doc.get("content") or doc.get("cleaned_content") or ""
            if len(content) > 500:
                content = content[:500] + "..."
            context_text += f"[Document {idx}] Title: {title}\nContent: {content}\n\n"

        # 2. Build Prompt
        prompt = SUMMARY_SYSTEM_PROMPT.format(context=context_text, query=user_query)
        messages = [{"role": "user", "content": prompt}]

        # 3. Call LLM
        try:
            summary = self.llm_client.call_gemini(messages=messages, temperature=0.3)
            return summary
        except Exception as e:
            print(f"Summary Generation Error: {e}")
            return ""
