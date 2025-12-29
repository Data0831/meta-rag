/**
 * Search Configuration Module
 */

export const searchConfig = {
    limit: 5,
    semanticRatio: 0.5,
    similarityThreshold: 0,
    enableLlm: true,
    manualSemanticRatio: false,
    enableKeywordWeightRerank: true
};

/**
 * Fetch configuration from backend and update searchConfig
 */
export async function loadBackendConfig() {
    try {
        const response = await fetch('/api/config');
        const config = await response.json();
        console.log('Backend Config:', config);

        // Update Limit
        if (config.default_limit !== undefined) {
            searchConfig.limit = config.default_limit;
            const limitInput = document.getElementById('limitInput');
            if (limitInput) limitInput.value = config.default_limit;
        }

        // Update Similarity Threshold
        if (config.default_similarity_threshold !== undefined) {
            // Convert from 0-1 range to 0-100 range
            const thresholdPercent = Math.round(config.default_similarity_threshold * 100);
            searchConfig.similarityThreshold = thresholdPercent;
            const thresholdInput = document.getElementById('similarityThreshold');
            const thresholdValue = document.getElementById('thresholdValue');
            if (thresholdInput) thresholdInput.value = thresholdPercent;
            if (thresholdValue) thresholdValue.textContent = thresholdPercent + '%';
        }

        // Update Semantic Ratio
        if (config.default_semantic_ratio !== undefined) {
            searchConfig.semanticRatio = config.default_semantic_ratio;
            const ratioInput = document.getElementById('semanticRatioSlider');
            const ratioValue = document.getElementById('semanticRatioValue');
            if (ratioInput) ratioInput.value = config.default_semantic_ratio * 100;
            if (ratioValue) ratioValue.textContent = Math.round(config.default_semantic_ratio * 100) + '%';
        }

        // Update Enable LLM
        if (config.enable_llm !== undefined) {
            searchConfig.enableLlm = config.enable_llm;
            const llmCheckbox = document.getElementById('llmRewriteCheckbox');
            if (llmCheckbox) llmCheckbox.checked = config.enable_llm;
        }

        // Update Manual Semantic Ratio
        if (config.manual_semantic_ratio !== undefined) {
            searchConfig.manualSemanticRatio = config.manual_semantic_ratio;
            const manualCheckbox = document.getElementById('manualRatioCheckbox');
            if (manualCheckbox) manualCheckbox.checked = config.manual_semantic_ratio;
        }

        // Update Enable Rerank
        if (config.enable_rerank !== undefined) {
            searchConfig.enableKeywordWeightRerank = config.enable_rerank;
            const rerankCheckbox = document.getElementById('enableKeywordWeightRerankCheckbox');
            if (rerankCheckbox) rerankCheckbox.checked = config.enable_rerank;
        }

        console.log('Final Config:', searchConfig);
    } catch (error) {
        console.error('Failed to load config:', error);
        console.log('Using default Config:', searchConfig);
    }
}
