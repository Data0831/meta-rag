# src/services/rag_service.py
import re
import json
from typing import Dict, Any, List, Optional
from src.services.search_service import SearchService
from src.llm.client import LLMClient

# --- Prompt 設定 (修正版：補回來源引用指令) ---
DEFAULT_ANSWER_ONLY_PROMPT = """
Role: Microsoft 全方位技術與產品專家
Task: 請「完全且僅依據」下方提供的 [搜尋結果列表] 回答使用者的問題。

Context Info (搜尋結果列表):
{context}

### 嚴格回答準則 (Strict Rules):
1. **資料邊界**：你只能使用 [搜尋結果列表] 中的資訊。
2. **禁止腦補**：如果使用者的問題在 [搜尋結果列表] 中找不到答案，請直接回答：「抱歉，根據目前的搜尋結果，找不到關於此問題的詳細資訊。」
3. **禁止外部知識**：嚴禁使用「雖然搜尋結果沒提到，但通常...」或「一般來說...」這類語句來補充你自己的外部知識。**若資料不在列表中，就當作你不知道。**
4. **引用來源 (重要)**：
    - 請在回答的結尾處，明確標註您參考了哪一篇文件。
    - 格式範例：*(來源：No.1 <文件標題>)*
    - 若整合了多篇，請列出所有來源，例如：*(來源：No.1, No.3)*
5. **語言**：請統一用**繁體中文**回答。
6. **格式**：使用 Markdown 優化排版。

請直接開始回答：
"""

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

        # --- 步驟 1: 決定 Context 與 過濾機制 ---
        final_results = [] # 這是最後要給 LLM 看，也要回傳給前端顯示來源的清單
        
        # 情況 A: 前端已經有傳 Context (通常是手動勾選，或前端已經過濾過)
        if provided_context is not None:
            final_results = provided_context

        # 情況 B: 前端沒傳 Context，後端自己搜尋
        else:
            try:
                # 1. 擴大搜尋範圍 (limit=10)，確保過濾後還有剩
                search_data = self.search_service.search(
                    user_query=user_query,
                    limit=10,
                    semantic_ratio=0.5,
                    enable_llm=True,
                    is_retry_search=False,
                )
                raw_results = search_data.get("results", [])
                
                # 2. 執行「反灰過濾」邏輯 (同步前端算法)
                valid_results = []
                for doc in raw_results:
                    # 取得分數
                    score = doc.get("_rerank_score") 
                    if score is None:
                        score = doc.get("@search.score", 0)
                        
                    # [關鍵] 使用 round 確保與前端 JS 的 Math.round 一致
                    score_percent = round(score * 100)
                    
                    # 比對門檻
                    if score_percent >= threshold:
                        valid_results.append(doc)
                    else:
                        # 這是被過濾掉的 (反灰)
                        # print(f"   [Filtered] Doc '{doc.get('title')}' score {score_percent}% < threshold {threshold}%")
                        pass

                # 3. 只取前 5 篇合格的給 LLM (避免 Token 太多)
                final_results = valid_results[:5]
                
            except Exception as e:
                print(f"  Search failed: {e}")
                final_results = []

        # --- 步驟 2: 檢查是否有資料 ---
        # 如果過濾完發現是空的，直接拒絕回答
        if not final_results:
            return {
                "answer": f"抱歉，根據目前的搜尋設定（相似度門檻 {threshold}%），找不到符合條件的公告。請嘗試調低門檻或更換關鍵字。",
                "suggestions": ["如何調整搜尋門檻？", "放寬搜尋條件", "聯絡客服"],
                "references": [], 
            }

        # --- 步驟 3: 將文件組裝成文字 ---
        context_text = ""
        for idx, doc in enumerate(final_results, 1):
            title = doc.get("title", "No Title")
            raw_content = doc.get("content") or doc.get("cleaned_content") or doc.get("body") or ""
            content = str(raw_content)
            date = doc.get("year_month", "N/A")

            if len(content) > 10000: 
                content = content[:10000] + "..."
            context_text += f"Document {idx}:\nTitle: {title}\nDate: {date}\nContent: {content}\n\n"

        # --- 步驟 4: 第一次呼叫 (生成回答 - Answer Only) ---
        print("   Calling LLM for Answer...")
        
        # 組裝 Prompt (已包含引用指令)
        system_content = DEFAULT_ANSWER_ONLY_PROMPT.format(context=context_text)
        answer_messages = [{"role": "system", "content": system_content}]

        if history:
            for msg in history:
                role = "assistant" if msg.get("role") == "model" else "user"
                content = msg.get("content", "")
                if content:
                    answer_messages.append({"role": role, "content": content})

        answer_messages.append({"role": "user", "content": user_query})

        try:
            answer_text = self.llm_client.call_gemini(messages=answer_messages, temperature=0.1)
        except Exception as e:
            print(f"LLM Answer Error: {e}")
            answer_text = "抱歉，生成回答時發生錯誤，請稍後再試。"

        # --- 步驟 5: 第二次呼叫 (生成建議 - Suggestions) ---
        print("   Calling LLM for Suggestions...")
        
        suggestion_prompt = f"""
        任務：請根據下方的「參考文件」與「AI 回答」，生成 3 個使用者可能會問的後續問題。
        
        參考文件：
        {context_text}
        
        AI 回答內容：
        {answer_text}
        
        嚴格規則：
        1. **可回答性驗證**：你生成的每一個問題，答案**必須**能從上方的「參考文件」中找到。
        2. **如果不相關**：如果參考文件內容太少或與問題無關，請回傳空陣列 []。
        3. **格式**：只回傳 JSON 陣列，例如 ["問題一", "問題二"]。不要 Markdown。
        4. **長度**：每個問題限 15 字以內。
        """
        
        suggestions = []
        try:
            suggestion_response = self.llm_client.call_gemini(
                messages=[{"role": "user", "content": suggestion_prompt}], 
                temperature=0.7 
            )
            clean_json = self._clean_json_text(suggestion_response)
            suggestions = json.loads(clean_json)
            if not isinstance(suggestions, list):
                suggestions = []
            suggestions = [str(s) for s in suggestions[:3]]
        except Exception as e:
            print(f"Suggestion generation failed: {e}")
            suggestions = ["如何搜尋公告？", "最新功能介紹", "聯絡微軟支援"]

        # 兜底預設值
        if not suggestions:
            suggestions = ["如何搜尋？", "最新公告", "Copilot"]

        # --- 步驟 6: 回傳完整資料 ---
        return {
            "answer": answer_text,
            "suggestions": suggestions,
            "references": final_results 
        }