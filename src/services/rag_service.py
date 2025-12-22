# src/services/rag_service.py

from typing import Dict, Any, List, Optional
from src.services.search_service import SearchService
from src.llm.client import LLMClient
from src.llm.rag_prompts import RAG_SYSTEM_PROMPT

class RAGService:
    def __init__(self):
        # 初始化依賴的服務
        self.search_service = SearchService()
        self.llm_client = LLMClient()

    def chat(self, user_query: str, provided_context: List[Dict] = None, history: List[Dict] = None) -> Dict[str, Any]:
        """
        RAG 聊天主邏輯
        Args:
            user_query: 使用者當前的問題
            provided_context: 前端傳來的搜尋結果 (若有則優先使用)
            history: 前端傳來的對話歷史紀錄 [{role: 'user'/'model', content: '...'}]
        """
        
        print(f"🤖 RAGService: Processing query '{user_query}'")
        
        # --- 步驟 1: 決定 Context (資料來源) ---
        results = []
        source_type = "search"

        if provided_context and len(provided_context) > 0:
            # A. 優先使用前端傳來的搜尋結果 (Context Injection)
            print(f"  Using {len(provided_context)} documents provided by frontend.")
            results = provided_context
            source_type = "provided"
        else:
            # B. 如果前端沒傳，則自己去資料庫搜尋 (Fallback)
            print(f"  No context provided, searching DB...")
            search_data = self.search_service.search(
                user_query=user_query,
                limit=3,
                semantic_ratio=0.5,
                enable_llm=True
            )
            results = search_data.get("results", [])

        # --- 步驟 2: 將文件組裝成文字字串 ---
        context_text = ""
        if results:
            for idx, doc in enumerate(results, 1):
                title = doc.get('title', 'No Title')
                content = doc.get('content', '') or doc.get('cleaned_content', '')
                date = doc.get('year_month', 'N/A')
                
                # 簡單截斷過長的內容 (避免超過 Token 限制)
                if len(content) > 800:
                    content = content[:800] + "..."
                
                context_text += f"Document {idx}:\nTitle: {title}\nDate: {date}\nContent: {content}\n\n"
        else:
            # 完全無資料時的處理
            return {
                "answer": "抱歉，目前沒有相關的搜尋結果可供參考，請嘗試先在左側搜尋欄輸入關鍵字。",
                "references": []
            }

        # --- 步驟 3: 組裝 LLM 的 Messages (包含 System Prompt + History) ---
        messages = []

        # (A) System Prompt: 注入當前的 Context
        full_system_prompt = RAG_SYSTEM_PROMPT.format(context=context_text)
        messages.append({"role": "system", "content": full_system_prompt})

        # (B) History: 注入歷史紀錄 (讓 LLM 擁有短期記憶)
        if history:
            print(f"  Loading {len(history)} history messages...")
            for msg in history:
                # 轉換 role 名稱: 前端傳來的 'model' 對應 OpenAI 的 'assistant'
                role = "assistant" if msg.get("role") == "model" else "user"
                content = msg.get("content", "")
                if content:
                    messages.append({"role": role, "content": content})

        # (C) User Query: 加入當前最新的問題
        messages.append({"role": "user", "content": user_query})

        # --- 步驟 4: 呼叫 LLM 生成回答 ---
        print("  Asking LLM...")
        try:
            # ★★★ 修改這裡：將 temperature 從 0.3 改成 0.5 ★★★
            answer = self.llm_client.call_gemini(messages=messages, temperature=0.5)
            
            if not answer:
                answer = "抱歉，系統暫時無法生成回應，請稍後再試。"
                
        except Exception as e:
            print(f"❌ LLM Error: {e}")
            answer = "抱歉，AI 服務連線發生錯誤。"

        return {
            "answer": answer,
            "references": results if source_type == "search" else [] # 如果是前端傳的，通常不需要再回傳 references
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
            title = doc.get('title', 'No Title')
            content = doc.get('content', '') or doc.get('cleaned_content', '')
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