from typing import List, Dict, Any
from src.services.search_service import SearchService
from src.llm.client import LLMClient
from src.llm.prompts.summary import SUMMARY_SYSTEM_INSTRUCTION, SUMMARY_USER_TEMPLATE
import re


class SearchTool:
    def __init__(self):
        self.search_service = SearchService()
        self.llm_client = LLMClient()

    def _clean_citation_format(self, text: str) -> str:
        """將全角括號 【n】 或 ［n］ 統一轉換為半角 [n]"""
        if not text:
            return ""
        # 修正 【1】 -> [1] 以及 ［1］ -> [1]
        text = re.sub(r"[【［](\d+)[】］]", r"[\1]", text)
        return text

    def search(
        self,
        query: str,
        limit: int = 20,
        semantic_ratio: float = 0.5,
        enable_llm: bool = True,
        manual_semantic_ratio: bool = False,
        exclude_ids: List[str] = None,
        history: List[str] = None,
        direction: str = None,
        start_date: str = None,
        end_date: str = None,
        website: List[str] = None,
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
            exclude_ids=exclude_ids,
            history=history,
            direction=direction,
            start_date=start_date,
            end_date=end_date,
            website=website,
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
            year = doc.get("year", "")
            year_month = doc.get("year_month", "")
            website = doc.get("website", "")

            # if len(content) > 1200:
            #     content = content[:1200] + "..."

            context_text += f'<document index="{idx}">\n'
            context_text += f"<title>{title}</title>\n"
            context_text += f"<year_month>{year_month}</year_month>\n"
            context_text += f"<year>{year}</year>\n"
            context_text += f"<website>{website}</website>\n"
            context_text += f"<content>{content}</content>\n"
            context_text += f"</document>\n\n"
            link_mapping[str(idx)] = link

        # 2. Build Prompt
        system_msg = SUMMARY_SYSTEM_INSTRUCTION
        user_msg = SUMMARY_USER_TEMPLATE.format(context=context_text, query=user_query)
        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ]

        # 3. Call LLM with schema
        llm_response = self.llm_client.call_with_schema(
            messages=messages,
            response_model=StructuredSummary,
            temperature=0.1,
        )

        if llm_response.get("status") == "success":
            validated_result = llm_response.get("result")
            return {
                "status": "success",
                "summary": {
                    "brief_answer": self._clean_citation_format(
                        validated_result.brief_answer
                    ),
                    "detailed_answer": self._clean_citation_format(
                        validated_result.detailed_answer
                    ),
                    "general_summary": self._clean_citation_format(
                        validated_result.general_summary
                    ),
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
