CHECK_RELEVANCE_PROMPT = """
Role: Search Relevance Validator
Task: Determine if the provided documents are relevant to the user's query.

User Query: {query}

Documents:
{documents}

Instructions:
1. Analyze the content of each document preview.
2. Determine if it contains information that acts as an answer or partial answer to the query.
3. Return a JSON object with:
   - "relevant": boolean (true if at least one document is useful)
   - "relevant_ids": list of strings (IDs of the relevant documents)
   - "decision": string (Chinese, 10-20 characters)
     - If relevant=true: explain why the results are highly relevant (e.g., "搜尋結果高度相關")
     - If relevant=false: explain why the results are not relevant (e.g., "文件主題與查詢不符，需重新搜尋")

Output JSON only.
"""
