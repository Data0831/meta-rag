/**
 * Search Configuration Module
 */
export const searchConfig = {
    limit: 5,
    maxLimit: 20,
    semanticRatio: 0.5,
    similarityThreshold: 0,
    enableLlm: true,
    manualSemanticRatio: false,
    enableKeywordWeightRerank: true,
    startDate: null,
    endDate: null
};

export const appConfig = {
    version: "v0.0.1",
    sources: [],
    announcements: [],
    websites: [],
    maxSearchInputLength: 100,
    maxChatInputLength: 500,
    dateRangeMin: "2023-01",
    dateRangeMax: null
};

/**
 * Fetch configuration from backend and update searchConfig
 */
export async function loadBackendConfig() {
    try {
        const response = await fetch('/api/config');
        const config = await response.json();
        console.log('Backend Config:', config);

        // Update Version
        if (config.version !== undefined) {
            appConfig.version = config.version;
            const versionElement = document.getElementById('appVersion');
            if (versionElement) versionElement.textContent = `版本 ${config.version}`;
        }

        // Update Limit
        if (config.default_limit !== undefined) {
            searchConfig.limit = config.default_limit;
            const limitInput = document.getElementById('limitInput');
            if (limitInput) limitInput.value = config.default_limit;
        }

        // Update Max Limit
        if (config.max_limit !== undefined) {
            searchConfig.maxLimit = config.max_limit;
            const limitInput = document.getElementById('limitInput');
            if (limitInput) limitInput.max = config.max_limit;
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

        // Update App Config (sources, announcements, websites)
        if (config.sources !== undefined) {
            appConfig.sources = config.sources;
        }
        if (config.announcements !== undefined) {
            appConfig.announcements = config.announcements;
        }
        if (config.websites !== undefined) {
            appConfig.websites = config.websites;
        }
        if (config.max_search_input_length !== undefined) {
            appConfig.maxSearchInputLength = config.max_search_input_length;
        }
        if (config.max_chat_input_length !== undefined) {
            appConfig.maxChatInputLength = config.max_chat_input_length;
        }

        // Update Date Range
        if (config.date_range_min !== undefined) {
            appConfig.dateRangeMin = config.date_range_min;
        }
        if (config.date_range_max !== undefined) {
            appConfig.dateRangeMax = config.date_range_max;
        }

        // Apply Date Range to Input Elements
        const startDateInput = document.getElementById('startDateInput');
        const endDateInput = document.getElementById('endDateInput');
        if (startDateInput) {
            if (appConfig.dateRangeMin) startDateInput.min = appConfig.dateRangeMin;
            if (appConfig.dateRangeMax) startDateInput.max = appConfig.dateRangeMax;
        }
        if (endDateInput) {
            if (appConfig.dateRangeMin) endDateInput.min = appConfig.dateRangeMin;
            if (appConfig.dateRangeMax) endDateInput.max = appConfig.dateRangeMax;
        }

        console.log('Final Config:', searchConfig);
        console.log('App Config:', appConfig);
    } catch (error) {
        console.error('Failed to load config:', error);
        console.log('Using default Config:', searchConfig);
    }
}
