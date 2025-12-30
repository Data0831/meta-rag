QUERY_REWRITE_PROMPT = """
Role: Search Query Optimizer
Task: Generate a better search query because the previous attempt failed.

Original User Query: {original_query}
Failed Query: {current_query}

Instructions:
1. Analyze why the previous query might have failed (e.g., too specific, wrong keywords).
2. Generate a SINGLE new search query that is more likely to succeed.
3. Output ONLY the new query string.
"""
