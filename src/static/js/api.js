/**
 * API Module
 * Handles all API requests
 */

import { searchConfig } from './config.js';

/**
 * Perform search with streaming response
 * @param {string} query - Search query
 * @param {Array<string>} selectedWebsites - Selected website filters
 * @returns {Promise<Response>} - Fetch response object (for streaming)
 */
export async function performSearchStream(query, selectedWebsites = []) {
    console.log('Starting search stream...');
    console.log('  Query:', query);
    console.log('  Config:', searchConfig);

    if (!query) {
        throw new Error('請輸入搜尋查詢');
    }

    const requestBody = {
        query: query,
        limit: searchConfig.limit,
        semantic_ratio: searchConfig.semanticRatio,
        enable_llm: searchConfig.enableLlm,
        manual_semantic_ratio: searchConfig.manualSemanticRatio,
        enable_keyword_weight_rerank: searchConfig.enableKeywordWeightRerank,
        start_date: searchConfig.startDate,
        end_date: searchConfig.endDate,
        selected_websites: selectedWebsites
    };

    console.log('Request Body:', requestBody);

    const response = await fetch('/api/search', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestBody)
    });

    console.log('Response Status:', response.status);

    if (!response.ok) {
        console.error('Response not OK:', response.status, response.statusText);
        const errorText = await response.text();
        console.error('Error Body:', errorText);

        try {
            const errorData = JSON.parse(errorText);
            if (errorData.status === "failed" && errorData.error_stage) {
                const error = new Error(errorData.error || `HTTP error! status: ${response.status}`);
                error.errorData = errorData;
                throw error;
            }
            throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        } catch (parseError) {
            if (parseError.errorData) {
                throw parseError;
            }
            throw new Error(errorText || `HTTP error! status: ${response.status}`);
        }
    }

    return response;
}

/**
 * Send user feedback (positive/negative)
 * @param {string} feedbackType - "positive" or "negative"
 * @param {string} query - User's search query
 * @param {Object} searchParams - Search parameters used
 * @returns {Promise<Object>} - Response data
 */
export async function sendFeedback(feedbackType, query, searchParams = {}) {
    console.log('Sending feedback...');
    console.log('  Type:', feedbackType);
    console.log('  Query:', query);
    console.log('  Params:', searchParams);

    const requestBody = {
        feedback_type: feedbackType,
        query: query,
        search_params: searchParams
    };

    const response = await fetch('/api/feedback', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestBody)
    });

    if (!response.ok) {
        const errorText = await response.text();
        console.error('Feedback API Error:', errorText);
        throw new Error('反饋提交失敗');
    }

    return await response.json();
}

