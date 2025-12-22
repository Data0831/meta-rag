# Verification Guide: Search Result Dimming (Fixed)

This guide explains how to verify the fix for the "dimming not working on first search with LLM" issue.

## Prerequisites
- The application should be running.
- You should have access to the web interface.

## Verification Steps

### Test Case 1: Initial Search with Threshold & LLM
1.  **Set Threshold**: On the left sidebar, locate the "Similarity Threshold" (相似度閾值) slider. Move it to a high value, e.g., **80%**.
2.  **Enable LLM**: Check the "Enable LLM Query Rewrite" (啟用 LLM 查詢重寫) checkbox.
3.  **Perform Search**: Enter a query (e.g., "Microsoft") and search.
4.  **Observe Results**:
    - **Expected Behavior**: Results with a match percentage **lower than 80%** MUST appear **dimmed** immediately.
    - **Previous Bug**: Previously, they would appear fully opaque (not dimmed) on the first search. This should now be fixed.

### Test Case 2: Standard Search (No LLM)
1.  **Disable LLM**: Uncheck the "Enable LLM Query Rewrite" checkbox.
2.  **Set Threshold**: Set slider to **50%**.
3.  **Perform Search**: Enter a query.
4.  **Observe Results**:
    - **Expected Behavior**: Results < 50% should be dimmed.

### Test Case 3: Slider Interaction
1.  **Keep Results**: Using results from above.
2.  **Move Slider**: Move the slider up and down.
3.  **Observe Results**:
    - **Expected Behavior**: Dimming should update in real-time.

## Technical Note
The fix involved moving the dimming logic directly into the HTML generation phase (`renderResultCard`), ensuring the class is present before the element is even added to the DOM. This eliminates timing issues where the DOM wasn't ready for class manipulation.