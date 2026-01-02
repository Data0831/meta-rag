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

        let errorMessage;
        try {
            const error = JSON.parse(errorText);
            errorMessage = error.error || `HTTP error! status: ${response.status}`;
        } catch {
            errorMessage = errorText || `HTTP error! status: ${response.status}`;
        }
        throw new Error(errorMessage);
    }

    return response;
}

