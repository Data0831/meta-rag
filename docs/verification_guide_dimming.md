# Verification Guide: Search Result Dimming

This guide explains how to verify the new feature where search results are dimmed if they fall below the configured similarity threshold.

## Prerequisites
- The application should be running (e.g., `python src/app.py`).
- You should have access to the web interface (usually `http://localhost:5000`).

## Verification Steps

### Test Case 1: Initial Search with Threshold
1.  **Set Threshold**: On the left sidebar, locate the "Similarity Threshold" (相似度閾值) slider. Move it to a high value, for example, **80%**.
2.  **Perform Search**: Enter a query in the search bar (e.g., "Microsoft") and press Enter or click the search icon.
3.  **Observe Results**:
    - Check the "Match" percentage badge on the result cards.
    - **Expected Behavior**: Any result with a match percentage **lower than 80%** should appear **dimmed** (greyed out and semi-transparent). Results with 80% or higher should appear normal.

### Test Case 2: Adjusting Threshold Post-Search
1.  **Keep Results**: Using the results from the previous step.
2.  **Lower Threshold**: Drag the slider down to **0%**.
    - **Expected Behavior**: All dimmed results should immediately become fully visible (normal opacity/color).
3.  **Raise Threshold**: Drag the slider up to **100%**.
    - **Expected Behavior**: Unless you have a perfect 100% match, all results should become dimmed.

### Test Case 3: New Search Resets
1.  **Set Threshold**: Set the slider to **50%**.
2.  **Perform Search**: Enter a different query.
3.  **Observe Results**:
    - **Expected Behavior**: The new results are rendered, and immediately, the logic applies the 50% threshold. Only results < 50% match should be dimmed.

## Troubleshooting
- If results are not dimming, ensure your browser cache is cleared to load the latest `search.js`.
- Check the browser console (F12) for any JavaScript errors.
