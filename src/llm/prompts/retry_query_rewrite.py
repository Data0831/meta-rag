RETRY_QUERY_REWRITE_PROMPT = """
Role: Search Query Optimizer
Task: Generate a completely NEW search query because the previous attempts failed to produce relevant results.

Original User Query: {original_query}
Failed Query Attempt: {current_query}
Query History (Already Tried): {history}

Instructions:
1. Analyze the 'Query History' to understand what strategies have already failed.
2. Avoid using keywords or phrasing that are too similar to those in the 'Query History'.
3. Generate a SINGLE new search query that takes a DIFFERENT angle or uses DIFFERENT terminology.
4. The goal is to find relevant information that was missed by previous attempts.
5. Output ONLY the new query string.
"""
