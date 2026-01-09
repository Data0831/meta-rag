# src/services/rag_service.py
import re
import json
from typing import Dict, Any, List, Optional
from src.services.search_service import SearchService
from src.llm.client import LLMClient
from src.tool.token_counter import count_tokens
from src.config import LLM_TOKEN_LIMIT
from src.llm.prompts.rag_answer import RAG_CHAT_PROMPT
from src.schema.schemas import ChatResponse


class RAGService:
    def __init__(self):
        self.search_service = SearchService()
        self.llm_client = LLMClient()

    def _clean_json_text(self, text: str) -> str:
        """
        清理 LLM 回傳的 JSON 字串 (移除 ```json 等標記)
        """
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        start = text.find('[')
        end = text.rfind(']')
        if start != -1 and end != -1:
            return text[start:end+1]
        return text

    def chat(
        self,
        user_query: str,
        provided_context: List[Dict] = None,
        history: List[Dict] = None,
        threshold: float = 0.0,  # 接收前端傳來的門檻值
    ) -> Dict[str, Any]:
        print(f"RAGService: Processing query '{user_query}' with threshold {threshold}%")

        # --- 步驟 1: 檢查 Context 是否存在 ---
        if provided_context is None:
            return {
                "answer": "無參考資料無法回應，請先執行搜尋並選擇參考文章。",
                "suggestions": ["如何搜尋？", "最新公告", "Copilot"],
                "references": [],
            }

        # --- 步驟 2: 對 provided_context 執行 threshold 過濾 ---
        final_results = []
        for doc in provided_context:
            score = doc.get("_rerank_score")
            if score is None:
                score = doc.get("@search.score", 0)

            score_percent = round(score * 100)

            if score_percent >= threshold:
                final_results.append(doc)

        # --- 步驟 3: 檢查是否有資料 ---
        # 如果過濾完發現是空的，直接拒絕回答
        if not final_results:
            return {
                "answer": f"抱歉，根據目前的搜尋設定（相似度門檻 {threshold}%），找不到符合條件的公告。請嘗試調低門檻或更換關鍵字。",
                "suggestions": ["如何調整搜尋門檻？", "放寬搜尋條件", "聯絡客服"],
                "references": [], 
            }

        # --- 步驟 4: 將文件組裝成文字 (XML 格式，與 tool.py 一致) ---
        context_text = ""
        for idx, doc in enumerate(final_results, 1):
            title = doc.get("title", "No Title")
            link = doc.get("heading_link") or doc.get("link", "")
            content = doc.get("content") or doc.get("cleaned_content") or ""
            year = doc.get("year", "")
            year_month = doc.get("year_month", "")
            website = doc.get("website", "")

            context_text += f'<document index="{idx}">\n'
            context_text += f"<title>{title}</title>\n"
            context_text += f"<year_month>{year_month}</year_month>\n"
            context_text += f"<year>{year}</year>\n"
            context_text += f"<website>{website}</website>\n"
            context_text += f"<content>{content}</content>\n"
            context_text += f"</document>\n\n"

        # --- 步驟 5: Token 統計與超限檢查 ---
        system_content = RAG_CHAT_PROMPT.format(context=context_text)

        token_system = count_tokens(system_content)
        token_context = count_tokens(context_text)
        token_user = count_tokens(user_query)

        token_history = 0
        if history:
            for msg in history:
                content = msg.get("content", "")
                if content:
                    token_history += count_tokens(content)

        total_tokens = token_system + token_user + token_history

        print(f"   Token Usage: system={token_system}, context={token_context}, user={token_user}, history={token_history}, total={total_tokens}")

        if total_tokens > LLM_TOKEN_LIMIT:
            print(f"   Token limit exceeded: {total_tokens} > {LLM_TOKEN_LIMIT}")
            return {
                "error": f"Token 使用量 ({total_tokens:,}) 超過限制 ({LLM_TOKEN_LIMIT:,})，請清除對話歷史或降低相似度閾值",
                "token_usage": {
                    "total": total_tokens,
                    "system": token_system,
                    "context": token_context,
                    "history": token_history,
                    "user": token_user,
                },
                "suggestions": ["清除對話歷史", "降低相似度閾值", "減少參考文章數量"],
            }

        # --- 步驟 6: 呼叫 LLM (生成回答 + 建議) ---
        print("   Calling LLM for Answer & Suggestions (Schema Mode)...")

        messages = [{"role": "system", "content": system_content}]

        if history:
            for msg in history:
                role = "assistant" if msg.get("role") == "model" else "user"
                content = msg.get("content", "")
                if content:
                    messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": user_query})

        answer_text = "抱歉，生成回答時發生錯誤，請稍後再試。"
        suggestions = ["如何搜尋？", "最新公告", "Copilot"]

        try:
            # 使用 call_with_schema 進行結構化輸出
            response = self.llm_client.call_with_schema(
                messages=messages,
                response_model=ChatResponse,
                temperature=0.5 # 稍微提高溫度以獲得更有創意但合規的建議 (Schema 會限制格式)
            )

            if response["status"] == "success":
                result: ChatResponse = response["result"]
                answer_text = result.answer
                suggestions = result.suggestions
                
                # 確保建議數量不超過 3
                if len(suggestions) > 3:
                     suggestions = suggestions[:3]
                
                # 兜底：如果沒生成建議
                if not suggestions:
                    suggestions = ["如何搜尋？", "最新公告", "Copilot"]
            else:
                 print(f"LLM Schema Call Failed: {response.get('error')}")

        except Exception as e:
            print(f"LLM Chat Error: {e}")

        # --- 步驟 7: 回傳完整資料 ---
        return {
            "answer": answer_text,
            "suggestions": suggestions,
            "references": final_results,
            "token_usage": {
                "total": total_tokens,
                "system": token_system,
                "context": token_context,
                "history": token_history,
                "user": token_user,
            }
        }