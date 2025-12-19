// Collection Search - Meilisearch Hybrid Search Interface
// Supports keyword search, semantic search, and metadata filtering

const COLLECTION_NAME = 'announcements';

/**
 * Search Configuration
 */
let searchConfig = {
    limit: 5,  // Number of results to return
    semanticRatio: 0.5,  // Weight for semantic search (0.0 = pure keyword, 1.0 = pure semantic)
    similarityThreshold: 0,  // Similarity threshold (0-100), results below this will be dimmed
    enableLlm: false
};

// DOM Elements
const searchInput = document.getElementById('searchInput');
const searchIconBtn = document.getElementById('searchIconBtn');
const llmRewriteCheckbox = document.getElementById('llmRewriteCheckbox');
const intentContainer = document.getElementById('intentContainer');
const intentFilters = document.getElementById('intentFilters');
const intentKeywordQuery = document.getElementById('intentKeywordQuery');
const intentSemanticQuery = document.getElementById('intentSemanticQuery');

// State Elements
const loadingState = document.getElementById('loadingState');
const errorState = document.getElementById('errorState');
const errorMessage = document.getElementById('errorMessage');
const emptyState = document.getElementById('emptyState');
const resultsContainer = document.getElementById('resultsContainer');
const resultsInfo = document.getElementById('resultsInfo');
const resultsCount = document.getElementById('resultsCount');
const searchTime = document.getElementById('searchTime');
const searchTimeValue = document.getElementById('searchTimeValue');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Collection Search initialized');
    console.log('📍 Collection Name:', COLLECTION_NAME);

    // Fetch configuration from backend
    fetch('/api/config')
        .then(response => response.json())
        .then(config => {
            console.log('📥 Backend Config:', config);

            // Update Limit
            if (config.default_limit !== undefined) {
                searchConfig.limit = config.default_limit;
                const limitInput = document.getElementById('limitInput');
                if (limitInput) limitInput.value = config.default_limit;
            }

            // Update Similarity Threshold
            if (config.default_similarity_threshold !== undefined) {
                searchConfig.similarityThreshold = config.default_similarity_threshold;
                const thresholdInput = document.getElementById('similarityThreshold');
                const thresholdValue = document.getElementById('thresholdValue');
                if (thresholdInput) thresholdInput.value = config.default_similarity_threshold * 100;
                if (thresholdValue) thresholdValue.textContent = Math.round(config.default_similarity_threshold * 100) + '%';
            }

            // Update Semantic Ratio
            if (config.default_semantic_ratio !== undefined) {
                searchConfig.semanticRatio = config.default_semantic_ratio;
                const ratioInput = document.getElementById('semanticRatioSlider');
                const ratioValue = document.getElementById('semanticRatioValue');
                if (ratioInput) ratioInput.value = config.default_semantic_ratio * 100;
                if (ratioValue) ratioValue.textContent = Math.round(config.default_semantic_ratio * 100) + '%';
            }

            console.log('⚙️ Final Config:', searchConfig);
        })
        .catch(error => {
            console.error('❌ Failed to load config:', error);
            console.log('⚙️ Using default Config:', searchConfig);
        });

    setupEventListeners();
    setupSearchConfig();
});

// Setup search configuration (can be extended with UI controls)
function setupSearchConfig() {
    // Similarity threshold slider
    const similarityThreshold = document.getElementById('similarityThreshold');
    const thresholdValue = document.getElementById('thresholdValue');
    if (similarityThreshold && thresholdValue) {
        similarityThreshold.addEventListener('input', (e) => {
            searchConfig.similarityThreshold = parseInt(e.target.value);
            thresholdValue.textContent = searchConfig.similarityThreshold + '%';
            // Apply threshold to current results if they exist
            applyThresholdToResults();
        });
    }

    // Semantic ratio slider
    const semanticRatioSlider = document.getElementById('semanticRatioSlider');
    if (semanticRatioSlider) {
        semanticRatioSlider.addEventListener('input', (e) => {
            const val = parseInt(e.target.value);
            searchConfig.semanticRatio = val / 100;
            // Update label if it exists
            const label = document.getElementById('semanticRatioValue');
            if (label) {
                label.textContent = val + '%';
            }
        });
    }

    // Limit input
    const limitInput = document.getElementById('limitInput');
    if (limitInput) {
        limitInput.addEventListener('change', (e) => {
            const value = parseInt(e.target.value);
            if (value > 0 && value <= 100) {
                searchConfig.limit = value;
            }
        });
    }

    // LLM Rewrite Checkbox
    if (llmRewriteCheckbox) {
        llmRewriteCheckbox.addEventListener('change', (e) => {
            searchConfig.enableLlm = e.target.checked;
        });
    }
}

// Apply threshold to current results (real-time update)
function applyThresholdToResults() {
    if (!currentResults || currentResults.length === 0) return;

    const resultCards = resultsContainer.querySelectorAll('.result-card-container');
    resultCards.forEach((card, index) => {
        if (index < currentResults.length) {
            const result = currentResults[index];
            const score = Math.round((result._rankingScore || 0) * 100);

            if (score < searchConfig.similarityThreshold) {
                card.classList.add('dimmed-result');
            } else {
                card.classList.remove('dimmed-result');
            }
        }
    });
}

// Event Listeners
function setupEventListeners() {
    // Search triggers
    searchIconBtn.addEventListener('click', performSearch);
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            performSearch();
        }
    });
}

// Perform Search
async function performSearch() {
    const query = searchInput.value.trim();

    console.log('🔍 Starting search...');
    console.log('  Query:', query);
    console.log('  Config:', searchConfig);

    if (!query) {
        console.warn('⚠️ Empty query');
        showError('請輸入搜尋查詢');
        return;
    }

    showLoading();

    const startTime = performance.now();

    const requestBody = {
        query: query,
        limit: searchConfig.limit,
        semantic_ratio: searchConfig.semanticRatio,
        enable_llm: searchConfig.enableLlm
    };

    console.log('📤 Request Body:', requestBody);

    try {
        const response = await fetch('/api/collection_search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestBody)
        });

        const endTime = performance.now();
        const duration = Math.round(endTime - startTime);

        console.log('📥 Response Status:', response.status);
        console.log('⏱️ Duration:', duration + 'ms');

        if (!response.ok) {
            console.error('❌ Response not OK:', response.status, response.statusText);
            const errorText = await response.text();
            console.error('❌ Error Body:', errorText);

            let errorMessage;
            try {
                const error = JSON.parse(errorText);
                errorMessage = error.error || `HTTP error! status: ${response.status}`;
            } catch {
                errorMessage = errorText || `HTTP error! status: ${response.status}`;
            }
            throw new Error(errorMessage);
        }

        const data = await response.json();
        console.log('✅ Response Data:', data);
        console.log('  Results count:', data.results?.length || 0);
        console.log('  Intent:', data.intent);

        renderResults(data, duration);

    } catch (error) {
        console.error('❌ Search failed:', error);
        console.error('  Error message:', error.message);
        console.error('  Error stack:', error.stack);
        showError(error.message);
    }
}

// Render Search Results
function renderResults(data, duration) {
    console.log('🎨 Rendering results...');
    console.log('  Data:', data);
    console.log('  Duration:', duration);

    hideAllStates();

    // Extract results and intent from SearchService response
    const results = data.results || [];
    const intent = data.intent;

    console.log('  Results array:', results);
    console.log('  Intent:', intent);

    if (results.length === 0) {
        console.log('ℹ️ No results found');
        showEmpty('沒有找到相關結果', '請嘗試不同的搜尋查詢');
        return;
    }

    // Update Intent Display
    if (intent && searchConfig.enableLlm) {
        console.log('🧠 Updating intent display');
        updateIntentDisplay(intent);
    }

    // Store results globally for detail view
    currentResults = results;

    // Show results info
    resultsInfo.classList.remove('hidden');
    resultsCount.textContent = results.length;

    // Show search time
    searchTime.classList.remove('hidden');
    searchTimeValue.textContent = duration;

    // Render result cards
    resultsContainer.classList.remove('hidden');
    resultsContainer.innerHTML = results.map((result, index) => {
        return renderResultCard(result, index + 1);
    }).join('');

    console.log('✅ Results rendered successfully');
}

function updateIntentDisplay(intent) {
    if (!intent) return;

    intentContainer.classList.remove('hidden');

    // Update Keywords & Semantic Query
    intentKeywordQuery.textContent = intent.keyword_query || 'N/A';
    intentSemanticQuery.textContent = intent.semantic_query || 'N/A';

    // Update Filters
    intentFilters.innerHTML = '';
    const filters = intent.filters || {};

    // 1. Limit (Always show)
    const limitVal = intent.limit !== null && intent.limit !== undefined ? intent.limit : 'Null';
    const limitClass = (intent.limit !== null && intent.limit !== undefined) ?
        "bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-300 border-gray-200 dark:border-gray-600" :
        "bg-transparent text-gray-400 border-gray-200 dark:border-gray-700 border-dashed";

    intentFilters.innerHTML += `<span class="px-2 py-0.5 rounded border text-xs ${limitClass}">🔢 Limit: ${limitVal}</span>`;

    // 2. Category (Always show)
    const catVal = filters.category || 'Null';
    const catClass = filters.category ?
        "bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-300 border-green-200 dark:border-green-700" :
        "bg-transparent text-gray-400 border-gray-200 dark:border-gray-700 border-dashed";

    intentFilters.innerHTML += `<span class="px-2 py-0.5 rounded border text-xs ${catClass}">🏷️ Category: ${catVal}</span>`;

    // 3. Months (Only if present)
    if (filters.months && filters.months.length > 0) {
        filters.months.forEach(m => {
            intentFilters.innerHTML += `<span class="px-2 py-0.5 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-300 rounded border border-blue-200 dark:border-blue-700 text-xs">📅 ${m}</span>`;
        });
    }

    // 4. Impact Level (Only if present)
    if (filters.impact_level) {
        intentFilters.innerHTML += `<span class="px-2 py-0.5 bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-300 rounded border border-red-200 dark:border-red-700 text-xs">⚠️ ${filters.impact_level}</span>`;
    }
}

// Render Single Result Card
function renderResultCard(result, rank) {
    const score = result._rankingScore || 0;
    const scorePercent = Math.round(score * 100);
    const id = rank - 1; // 0-based index for IDs
    const isFirst = rank === 1;

    // Map fields
    const title = result.title || '無標題';
    const workspace = result.workspace || 'N/A';
    const date = result.year_month || 'N/A';
    const link = result.link || '#';
    const content = result.content ? marked.parse(result.content) : '';

    // Colors based on score
    let badgeClass = "px-2 py-1 bg-primary/20 dark:bg-primary/30 text-primary dark:text-primary-light text-xs font-bold rounded";
    let containerClass = "result-card-container bg-white dark:bg-slate-800 rounded-xl border border-primary/30 dark:border-primary/20 shadow-sm overflow-hidden mb-6 group hover:shadow-md transition-all duration-300";
    let arrowClass = "material-icons-round text-slate-400 group-hover:text-primary transition-colors";
    let arrowText = "keyboard_arrow_right";
    let numberTextClass = "font-bold text-slate-500 dark:text-slate-400";
    let bodyClass = "hidden p-8";

    if (isFirst) {
        containerClass = "result-card-container bg-white dark:bg-slate-800 rounded-xl border-2 border-primary/40 dark:border-primary/40 shadow-glow overflow-hidden mb-6 relative";
        arrowClass = "material-icons-round text-slate-800 dark:text-white font-bold";
        arrowText = "keyboard_arrow_down";
        numberTextClass = "font-bold text-slate-800 dark:text-white";
        badgeClass = "px-2 py-1 bg-primary text-white text-xs font-bold rounded";
        bodyClass = "p-8";
    }

    return `
    <div id="result-card-${id}" class="${containerClass}">
        <div onclick="toggleResult(${id})" class="px-6 py-4 flex items-center justify-between border-b border-slate-100 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/50 cursor-pointer">
            <div class="flex items-center gap-4">
                <span id="result-arrow-${id}" class="${arrowClass}">${arrowText}</span>
                <span id="result-number-${id}" class="${numberTextClass}">No.${rank}</span>
                <div class="h-4 w-[1px] bg-slate-300 dark:bg-slate-600"></div>
                <h4 class="font-bold text-lg text-slate-800 dark:text-white">${title}</h4>
            </div>
            <span id="result-badge-${id}" class="${badgeClass}">${scorePercent}% Match</span>
        </div>
        
        <div id="result-body-${id}" class="${bodyClass}">
            <h2 class="text-3xl font-bold text-slate-900 dark:text-white mb-6">${title}</h2>
            <div class="space-y-4 text-base text-slate-700 dark:text-slate-300">
                <div class="flex items-start gap-2">
                    <span class="font-bold min-w-[150px] text-slate-900 dark:text-white">• 類別 (Workspace) :</span>
                    <span>${workspace}</span>
                </div>
                <div class="flex items-start gap-2">
                    <span class="font-bold min-w-[150px] text-slate-900 dark:text-white">• 發布日期 (Date) :</span>
                    <span>${date}</span>
                </div>
                <div class="flex items-start gap-2">
                    <span class="font-bold min-w-[150px] text-slate-900 dark:text-white">• 原始連結 (Link) :</span>
                    <a class="text-blue-600 dark:text-blue-400 hover:underline font-medium" href="${link}" target="_blank">點此查看</a>
                </div>
                 <div class="mt-4 pt-4 border-t border-slate-100 dark:border-slate-700">
                    <div class="prose dark:prose-invert max-w-none text-slate-700 dark:text-slate-300">
                        ${content}
                    </div>
                </div>
            </div>
        </div>
    </div>
    `;
}

// Function to toggle result expansion
window.toggleResult = function (index) {
    const container = document.getElementById(`result-card-${index}`);
    const body = document.getElementById(`result-body-${index}`);
    const arrow = document.getElementById(`result-arrow-${index}`);
    const badge = document.getElementById(`result-badge-${index}`);
    const numberText = document.getElementById(`result-number-${index}`);

    const isExpanded = !body.classList.contains('hidden');

    if (isExpanded) {
        // Collapse
        body.classList.add('hidden');

        // Update Container Style
        container.className = "result-card-container bg-white dark:bg-slate-800 rounded-xl border border-primary/30 dark:border-primary/20 shadow-sm overflow-hidden mb-6 group hover:shadow-md transition-all duration-300";

        // Update Arrow
        arrow.textContent = 'keyboard_arrow_right';
        arrow.className = "material-icons-round text-slate-400 group-hover:text-primary transition-colors";

        // Update Number Text
        numberText.className = "font-bold text-slate-500 dark:text-slate-400";

        // Update Badge (Reset to light style)
        if (badge.textContent.includes('100%') || parseInt(badge.textContent) > 80) {
            // Keep high score style if needed, but code.html seems to dim it when collapsed?
            // Actually code.html collapsed card has 100% Match and uses bg-primary/20.
            // Expanded card has 87% Match and uses bg-primary (filled).
            // It implies expanded = prominent badge.
            badge.className = "px-2 py-1 bg-primary/20 dark:bg-primary/30 text-primary dark:text-primary-light text-xs font-bold rounded";
        } else {
            badge.className = "px-2 py-1 bg-primary/20 dark:bg-primary/30 text-primary dark:text-primary-light text-xs font-bold rounded";
        }

    } else {
        // Expand
        body.classList.remove('hidden');

        // Update Container Style
        container.className = "result-card-container bg-white dark:bg-slate-800 rounded-xl border-2 border-primary/40 dark:border-primary/40 shadow-glow overflow-hidden mb-6 relative";

        // Update Arrow
        arrow.textContent = 'keyboard_arrow_down';
        arrow.className = "material-icons-round text-slate-800 dark:text-white font-bold";

        // Update Number Text
        numberText.className = "font-bold text-slate-800 dark:text-white";

        // Update Badge (Prominent)
        badge.className = "px-2 py-1 bg-primary text-white text-xs font-bold rounded";
    }
}

// Current Results Storage
let currentResults = [];

// UI State Management
function showLoading() {
    console.log('⏳ Showing loading state');
    hideAllStates();
    loadingState.classList.remove('hidden');
    loadingState.classList.add('flex');
}

function showError(message) {
    console.error('🚨 Showing error:', message);
    hideAllStates();
    errorMessage.textContent = message;
    errorState.classList.remove('hidden');
}

function showEmpty(title, subtitle) {
    hideAllStates();
    emptyState.classList.remove('hidden');
    emptyState.innerHTML = `
        <span class="material-icons-round text-slate-300 dark:text-slate-600 text-6xl mb-4">search_off</span>
        <h3 class="text-lg font-medium text-slate-700 dark:text-slate-300">${title}</h3>
        <p class="text-sm text-slate-500 dark:text-slate-400 mt-2">${subtitle}</p>
    `;
}

function hideAllStates() {
    loadingState.classList.add('hidden');
    loadingState.classList.remove('flex');
    errorState.classList.add('hidden');
    emptyState.classList.add('hidden');
    resultsContainer.classList.add('hidden');
    resultsInfo.classList.add('hidden');
    searchTime.classList.add('hidden');
    if (intentContainer) intentContainer.classList.add('hidden');
}