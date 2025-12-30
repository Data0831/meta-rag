# src/services/rag_service.py
import re
import json
from typing import Dict, Any, List, Optional
from src.services.search_service import SearchService
from src.llm.client import LLMClient
from src.llm.rag_prompts import RAG_SYSTEM_PROMPT


class RAGService:
    def __init__(self):
        # 初始化依賴的服務
        self.search_service = SearchService()
        self.llm_client = LLMClient()

    def chat(
        self,
        user_query: str,
        provided_context: List[Dict] = None,
        history: List[Dict] = None,
    ) -> Dict[str, Any]:
        """
        RAG 聊天主邏輯
        """

        print(f"RAGService: Processing query '{user_query}'")

        # --- 步驟 1: 決定 Context (資料來源) ---
        results = []
        source_type = "search"

        if provided_context and len(provided_context) > 0:
            print(f"  Using {len(provided_context)} documents provided by frontend.")
            results = provided_context
            source_type = "provided"
        else:
            print(f"  No context provided, searching DB...")
            try:
                search_data = self.search_service.search(
                    user_query=user_query, limit=3, semantic_ratio=0.5, enable_llm=True
                )
                results = search_data.get("results", [])
            except Exception as e:
                print(f"  Search failed: {e}")
                results = []

        # --- 步驟 2: 將文件組裝成文字字串 ---
        context_text = ""
        if results:
            for idx, doc in enumerate(results, 1):
                title = doc.get("title", "No Title")

                # ★★★ 修復重點 1: 強制轉字串，防止 None 導致 crash ★★★
                raw_content = doc.get("content") or doc.get("cleaned_content") or ""
                content = str(raw_content)

                date = doc.get("year_month", "N/A")

                if len(content) > 800:
                    content = content[:800] + "..."

                context_text += f"Document {idx}:\nTitle: {title}\nDate: {date}\nContent: {content}\n\n"
        else:
            # 若無資料，回傳提示與引導按鈕
            return {
                "answer": "抱歉，目前沒有相關的搜尋結果可供參考，請嘗試先在左側搜尋欄輸入關鍵字。",
                "suggestions": [
                    "如何使用搜尋？",
                    "最近有什麼公告？",
                    "Copilot 價格查詢",
                ],
                "references": [],
            }

        # --- 步驟 3: 組裝 LLM 的 Messages ---
        messages = []
        full_system_prompt = RAG_SYSTEM_PROMPT.format(context=context_text)
        messages.append({"role": "system", "content": full_system_prompt})

        if history:
            for msg in history:
                role = "assistant" if msg.get("role") == "model" else "user"
                content = msg.get("content", "")
                if content:
                    messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": user_query})

        # --- 步驟 4: 呼叫 LLM 生成回答 ---
        print("  Asking LLM...")
        answer_text = ""
        suggestions = []

        try:
            # ★★★ 修復重點 2: 降低 Temperature 減少幻覺 ★★★
            full_response = self.llm_client.call_gemini(
                messages=messages, temperature=0.1
            )
            answer_text = full_response

            # 嘗試解析建議問題
            suggestion_match = re.search(
                r"<suggestions>(.*?)</suggestions>", full_response, re.DOTALL
            )
            if suggestion_match:
                try:
                    json_str = suggestion_match.group(1).strip()
                    # 清理 Markdown 語法 (```json ... ```)
                    json_str = re.sub(r"```json\s*", "", json_str)
                    json_str = re.sub(r"```\s*", "", json_str)

                    parsed = json.loads(json_str)
                    if isinstance(parsed, list) and len(parsed) > 0:
                        suggestions = parsed
                        # 從回答中移除建議區塊
                        answer_text = full_response.replace(
                            suggestion_match.group(0), ""
                        ).strip()
                except Exception as e:
                    print(f"❌ JSON Parse Error: {e}")

            # ★★★ 修復重點 3: 負面回答檢測與強制保底 ★★★
            negative_keywords = [
                "找不到",
                "未提及",
                "沒有提到",
                "無法回答",
                "抱歉",
                "資訊不足",
            ]
            is_negative_answer = any(
                keyword in answer_text for keyword in negative_keywords
            )

            # 情境 A: AI 說找不到 -> 強制換成摘要/通用引導
            if is_negative_answer:
                print("  ⚠️ Detected negative answer. Forcing fallback suggestions.")
                if results:
                    suggestions = [
                        "摘要這幾篇公告",
                        "列出發布日期",
                        "這幾篇的重點是什麼",
                    ]
                else:
                    suggestions = ["重新搜尋", "使用不同關鍵字", "最新公告"]

            # 情境 B: AI 沒給建議 (解析失敗或忘了給) -> 強制補上
            elif not suggestions:
                print("  ⚠️ No suggestions found. Using fallback.")
                suggestions = ["摘要搜尋結果", "列出關鍵重點", "還有其他相關資訊嗎？"]

            if not answer_text:
                answer_text = "抱歉，系統暫時無法生成回應。"

        except Exception as e:
            print(f"LLM Error: {e}")
            answer_text = "抱歉，AI 服務連線發生錯誤。"
            # 出錯時也要給按鈕，讓使用者可以重試
            suggestions = ["重新整理", "檢查網路", "重試"]

        return {
            "answer": answer_text,
            "suggestions": suggestions,  # 這裡保證永遠會有 list
            "references": results if source_type == "search" else [],
        }
