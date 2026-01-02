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
        direction: str = None,
        start_date: str = None,
        end_date: str = None,
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
            direction=direction,
            start_date=start_date,
            end_date=end_date,
        )

    def summarize(self, user_query: str, search_results: List[Dict]) -> Dict[str, Any]:
        """
        Summarizes the provided search results relevant to the user query.
        Returns structured summary with hyperlink mapping.
        """
        from src.schema.schemas import StructuredSummary
        from src.tool.ANSI import print_red

        if not search_results:
            return {
                "status": "success",
                "summary": {
                    "brief_answer": "沒有參考資料",
                    "detailed_answer": "",
                    "general_summary": "",
                },
                "link_mapping": {},
            }

        # 1. Prepare Context with XML tags (Take top 5)
        context_text = ""
        link_mapping = {}

        for idx, doc in enumerate(search_results[:5], 1):
            title = doc.get("title", "No Title")
            link = doc.get("heading_link") or doc.get("link", "")
            content = doc.get("content") or doc.get("cleaned_content") or ""
            if len(content) > 500:
                content = content[:500] + "..."

            context_text += f'<document index="{idx}">\n<title>{title}</title>\n<content>{content}</content>\n</document>\n\n'
            link_mapping[str(idx)] = link

        # 2. Build Prompt
        prompt = SUMMARY_SYSTEM_PROMPT.format(context=context_text, query=user_query)
        messages = [{"role": "user", "content": prompt}]

        # 3. Call LLM with schema
        llm_response = self.llm_client.call_with_schema(
            messages=messages,
            response_model=StructuredSummary,
            temperature=0.3,
        )

        if llm_response.get("status") == "success":
            validated_result = llm_response.get("result")
            return {
                "status": "success",
                "summary": {
                    "brief_answer": validated_result.brief_answer,
                    "detailed_answer": validated_result.detailed_answer,
                    "general_summary": validated_result.general_summary,
                },
                "link_mapping": link_mapping,
            }
        else:
            print_red(f"Summary generation failed: {llm_response.get('error')}")
            return {
                "status": "failed",
                "error": llm_response.get("error"),
                "summary": {
                    "brief_answer": "",
                    "detailed_answer": "",
                    "general_summary": "",
                },
                "link_mapping": {},
            }
