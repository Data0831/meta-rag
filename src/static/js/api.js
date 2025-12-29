/**
 * API Module
 * Handles all API requests
 */

import { searchConfig } from './config.js';

/**
 * Perform collection search
 * @param {string} query - Search query
 * @returns {Promise<{data: Object, duration: number}>}
 */
export async function performCollectionSearch(query) {
    console.log('Starting search...');
    console.log('  Query:', query);
    console.log('  Config:', searchConfig);

    if (!query) {
        throw new Error('請輸入搜尋查詢');
    }

    const startTime = performance.now();

    const requestBody = {
        query: query,
        limit: searchConfig.limit,
        semantic_ratio: searchConfig.semanticRatio,
        enable_llm: searchConfig.enableLlm,
        manual_semantic_ratio: searchConfig.manualSemanticRatio,
        enable_keyword_weight_rerank: searchConfig.enableKeywordWeightRerank
    };

    console.log('Request Body:', requestBody);

    const response = await fetch('/api/collection_search', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestBody)
    });

    const endTime = performance.now();
    const duration = Math.round(endTime - startTime);

    console.log('Response Status:', response.status);
    console.log('Duration:', duration + 'ms');

    if (!response.ok) {
        console.error('Response not OK:', response.status, response.statusText);
        const errorText = await response.text();
        console.error('Error Body:', errorText);

        let errorMessage;
        try {
            const error = JSON.parse(errorText);
            const stage = error.stage || 'unknown';
            const baseError = error.error || `HTTP error! status: ${response.status}`;

            // Format error message with stage information
            const stageLabels = {
                'meilisearch': '資料庫連線錯誤',
                'embedding': '向量服務錯誤',
                'llm': 'AI 服務錯誤',
                'intent_parsing': '查詢解析錯誤',
                'unknown': '系統錯誤'
            };
            const stageLabel = stageLabels[stage] || stageLabels['unknown'];
            errorMessage = `${stageLabel}\n${baseError}`;
        } catch {
            errorMessage = errorText || `HTTP error! status: ${response.status}`;
        }
        throw new Error(errorMessage);
    }

    const data = await response.json();
    console.log('Response Data:', data);
    console.log('  Results count:', data.results?.length || 0);
    console.log('  Intent:', data.intent);

    return { data, duration };
}
