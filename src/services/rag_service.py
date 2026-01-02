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
        RAG 聊天主邏輯 (最終完整版)
        包含：
        1. Context 組裝
        2. XML 建議問題解析 (<suggestions><question>...</question></suggestions>)
        3. JSON 格式備援
        4. 黑名單與品質過濾
        5. 移除「以下是建議問題」等開場白
        """
        print(f"RAGService: Processing query '{user_query}'")

        # --- 步驟 1: 決定 Context (資料來源) ---
        results = []
        source_type = "search"

        if provided_context is not None:
            results = provided_context
            source_type = "provided"
        else:
            # 只有當 provided_context 真的是 None (前端沒傳這個欄位) 時
            # 才執行後端的自動補位搜尋
            try:
                print("   No context provided, performing backend search...")
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
                # 處理內容可能為 None 的情況
                raw_content = doc.get("content") or doc.get("cleaned_content") or ""
                content = str(raw_content)
                date = doc.get("year_month", "N/A")
                
                # 截斷過長內容以節省 Token
                if len(content) > 15000:
                    content = content[:15000] + "..."     
                context_text += f"Document {idx}:\nTitle: {title}\nDate: {date}\nContent: {content}\n\n"
        else:
            # 若無搜尋結果，直接回傳，不浪費 LLM 資源
            return {
                "answer": "根據目前的搜尋設定（相似度門檻），找不到相關公告可供回答。",
                "suggestions": ["如何使用搜尋？", "最近有什麼公告？", "Copilot 價格查詢"],
                "references": [],
            }

        # --- 步驟 3: 組裝 Messages ---
        messages = []
        # 注意：請確認你的 RAG_SYSTEM_PROMPT 已經更新為要求 XML 格式
        full_system_prompt = RAG_SYSTEM_PROMPT.format(context=context_text)
        messages.append({"role": "system", "content": full_system_prompt})

        if history:
            for msg in history:
                role = "assistant" if msg.get("role") == "model" else "user"
                content = msg.get("content", "")
                if content:
                    messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": user_query})

        # --- 步驟 4: 呼叫 LLM ---
        print("   Asking LLM...")
        answer_text = ""
        suggestions = []

        try:
            # 這裡呼叫你的 LLM Client
            full_response = self.llm_client.call_gemini(messages=messages, temperature=0.1)
            answer_text = full_response
            
            # --- 🔥🔥🔥【解析與清洗核心邏輯】🔥🔥🔥 ---

            # A. 優先處理 XML <suggestions> 
            # 使用 re.DOTALL 讓 . 可以匹配換行符號
            suggestion_match = re.search(r"<suggestions>(.*?)</suggestions>", full_response, re.DOTALL)
            
            if suggestion_match:
                xml_content = suggestion_match.group(1).strip()
                
                # 優化 Regex：
                # 1. 允許標籤前後有空白 (\s*)
                # 2. 忽略大小寫 (re.IGNORECASE)，抓取 <Question> 或 <question>
                xml_questions = re.findall(r'<\s*question\s*>(.*?)<\s*/\s*question\s*>', xml_content, re.DOTALL | re.IGNORECASE)
                
                if xml_questions:
                    suggestions = [q.strip() for q in xml_questions]
                
                # 切割：將整個 <suggestions> 區塊從回答中移除
                answer_text = answer_text.replace(suggestion_match.group(0), "")

            # B. 備援處理 JSON List (以防 LLM 偶爾還是吐 JSON)
            # 如果上面 XML 沒抓到東西，才跑這段
            if not suggestions:
                json_array_pattern = r"\[\s*\"(?:\\.|[^\"\\])*\"(?:,\s*\"(?:\\.|[^\"\\])*\")*\s*\]"
                matches = list(re.finditer(json_array_pattern, full_response, re.DOTALL))
                
                for match in reversed(matches):
                    json_str = match.group(0)
                    try:
                        parsed = json.loads(json_str)
                        if isinstance(parsed, list):
                            suggestions = parsed
                            # 使用索引切割 (Slicing) 移除 JSON 及其後的所有內容
                            cutoff_index = match.start()
                            answer_text = full_response[:cutoff_index]
                            break 
                    except:
                        continue

            # C. 殘骸掃除 (移除 Markdown 標記)
            # 移除結尾可能的 ```xml, ```json, ```
            answer_text = re.sub(r"```\w*\s*$", "", answer_text.strip(), flags=re.IGNORECASE)
            answer_text = answer_text.replace("```", "").strip()

            # D. 🔥 強力清洗與過濾 🔥
            if suggestions:
                final_clean_suggestions = []
                # 黑名單：過濾掉系統關鍵字或無意義的詞
                block_list = ["xml", "json", "question", "suggestions", "item", "none", "null", "nan", "[]", "list"]
                
                for s in suggestions:
                    # 1. 移除可能殘留的 HTML/XML 標籤
                    s = re.sub(r'<[^>]+>', '', str(s)).strip()
                    
                    # 2. 過濾條件：
                    # - 不是空字串
                    # - 長度 > 4 (避免過短的無意義字串)
                    # - 不在黑名單內
                    if (s and len(s) > 4 and s.lower() not in block_list):
                        final_clean_suggestions.append(s)
                
                suggestions = final_clean_suggestions

                # E. 🔥 移除回答尾部的「開場白」 🔥
                # 避免機器人說完「以下是建議問題：」結果後面是一片空白(因為被我們切掉了)
                removals = [
                    "以下是根據搜尋結果，您可能感興趣的後續問題：",
                    "您可能感興趣的後續問題：",
                    "相關建議問題：",
                    "後續問題建議：",
                    "Suggested questions:",
                    "Follow-up questions:"
                ]
                
                for pattern in removals:
                    answer_text = answer_text.replace(pattern, "")
                
                # 再次修剪尾部的冒號或空白
                answer_text = answer_text.strip().rstrip("：:").strip()

            # F. 保底邏輯 (若回答被切光光，給個預設值)
            if not answer_text.strip():
                if suggestions:
                    answer_text = "我已根據搜尋結果整理出回答，請參考下方的建議問題："
                else:
                    answer_text = "抱歉，系統暫時無法生成完整回應。"

        except Exception as e:
            print(f"❌ LLM Error: {e}")
            answer_text = "抱歉，AI 服務連線發生錯誤。"
            suggestions = ["重新整理", "檢查網路", "重試"]

        return {
            "answer": answer_text,
            "suggestions": suggestions,
            "references": results if source_type == "search" else [],
        }
    
    def summarize(self, user_query: str, search_results: List[Dict]) -> str:
        """
        針對搜尋結果生成摘要
        """
        print(f"📝 RAGService: Generating summary for '{user_query}'")

        if not search_results:
            return ""

        # 1. 準備 Context (只取前 5 筆，避免 Token 太多)
        context_text = ""
        for idx, doc in enumerate(search_results[:5], 1):
            title = doc.get("title", "No Title")
            content = doc.get("content", "") or doc.get("cleaned_content", "")
            # 摘要只需要部分內容即可
            if len(content) > 500:
                content = content[:500] + "..."
            context_text += f"[第 {idx} 篇] 標題: {title}\n內容: {content}\n\n"

        # 2. 組裝 Prompt
        from src.llm.rag_prompts import SUMMARY_SYSTEM_PROMPT

        prompt = SUMMARY_SYSTEM_PROMPT.format(context=context_text, query=user_query)

        messages = [{"role": "user", "content": prompt}]

        # 3. 呼叫 LLM
        try:
            # 使用較低的 temperature (0.3) 讓摘要更穩定
            summary = self.llm_client.call_gemini(messages=messages, temperature=0.3)
            return summary
        except Exception as e:
            print(f"❌ Summary Generation Error: {e}")
            return ""
