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

Output JSON only.
"""
