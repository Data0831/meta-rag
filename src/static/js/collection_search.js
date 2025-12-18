// Collection Search - Meilisearch Hybrid Search Interface
// Supports keyword search, semantic search, and metadata filtering

/**
 * Search Configuration
 */
let searchConfig = {
    limit: 10,  // Number of results to return
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
    console.log('📍 Collection Name:', window.COLLECTION_NAME);
    console.log('⚙️ Initial Config:', searchConfig);
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
            searchConfig.semanticRatio = parseFloat(e.target.value);
            // Update label if it exists
            const label = document.getElementById('semanticRatioValue');
            if (label) {
                label.textContent = Math.round(searchConfig.semanticRatio * 100) + '%';
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

    const resultCards = resultsContainer.querySelectorAll('.result-card');
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
    // Extract score from Meilisearch response
    const score = result._rankingScore || 0;
    const scorePercent = Math.round(score * 100);
    const scoreColor = getScoreColor(scorePercent);

    // Extract text from Meilisearch document
    const text = result.content || result.title || '';
    const truncatedText = text.length > 300 ? text.substring(0, 300) + '...' : text;

    // Get metadata fields to display
    const metadata = [];
    if (result.metadata) {
        // Show important metadata fields
        const metaEntries = Object.entries(result.metadata)
            .filter(([key, value]) => value != null && value !== '')
            .slice(0, 3); // Show max 3 metadata fields
        metadata.push(...metaEntries);
    }

    // Add month if available
    if (result.month) {
        metadata.unshift(['month', result.month]);
    }

    // Check if result is below threshold
    const isDimmed = scorePercent < searchConfig.similarityThreshold;
    const dimmedClass = isDimmed ? 'dimmed-result' : '';

        // Score Details Analysis
        let scoreDetailsHtml = '';
        let matchTypeBadge = '';
        
        if (result._rankingScoreDetails) {
            const detailsObj = result._rankingScoreDetails;
            const hasKeywords = detailsObj.words !== undefined;
            const hasVector = detailsObj.vectorSort !== undefined || detailsObj.semantic !== undefined;
            
            // Determine Match Type Badge
            if (hasKeywords && hasVector) {
                matchTypeBadge = `<span class="ml-2 px-1.5 py-0.5 rounded text-[10px] font-bold border border-orange-200 bg-orange-50 text-orange-600 dark:bg-orange-900/30 dark:border-orange-800 dark:text-orange-300">Hybrid</span>`;
            } else if (hasKeywords) {
                matchTypeBadge = `<span class="ml-2 px-1.5 py-0.5 rounded text-[10px] font-bold border border-blue-200 bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:border-blue-800 dark:text-blue-300">Keyword</span>`;
            } else if (hasVector) {
                matchTypeBadge = `<span class="ml-2 px-1.5 py-0.5 rounded text-[10px] font-bold border border-purple-200 bg-purple-50 text-purple-600 dark:bg-purple-900/30 dark:border-purple-800 dark:text-purple-300">Semantic</span>`;
            }
    
            const details = Object.entries(detailsObj)            .map(([key, value]) => {
                // Handle various formats of value
                let valStr = '';
                if (typeof value === 'object' && value !== null && value.score !== undefined) {
                    valStr = Math.round(value.score * 100) + '%';
                } else if (typeof value === 'number') {
                    valStr = Math.round(value * 100) + '%';
                } else {
                    return null;
                }

                // Translate key
                let label = key;
                let icon = '';
                if (key === 'vectorSort' || key === 'semantic') { label = 'Dense (Vector)'; icon = 'hub'; }
                if (key === 'words') { label = 'Keywords'; icon = 'abc'; }
                if (key === 'typo') { label = 'Fuzzy (Typo)'; icon = 'spellcheck'; }
                if (key === 'proximity') { label = 'Proximity'; icon = 'format_align_center'; }
                if (key === 'attribute') { label = 'Attribute'; icon = 'sell'; }
                if (key === 'exactness') { label = 'Exactness'; icon = 'done_all'; }

                return `<div class="flex flex-col items-center bg-gray-100 dark:bg-gray-700/50 rounded px-2 py-1 min-w-[60px]">
                    <span class="text-[10px] text-gray-500 dark:text-gray-400 uppercase tracking-wider flex items-center gap-1">
                        ${icon ? `<span class="material-symbols-outlined text-[10px]">${icon}</span>` : ''} ${label}
                    </span>
                    <span class="text-xs font-bold text-gray-700 dark:text-gray-300">${valStr}</span>
                </div>`;
            })
            .filter(Boolean)
            .join('');

        if (details) {
            scoreDetailsHtml = `
                <div class="mt-3 pt-2 border-t border-gray-100 dark:border-gray-700/50 flex flex-wrap gap-2">
                    ${details}
                </div>
            `;
        }
    }

    return `
        <div class="result-card rounded-lg bg-gray-50 dark:bg-gray-800 p-5 card-shadow transition-all duration-300 hover:shadow-lg ${dimmedClass}">
            <!-- Header -->
            <div class="flex justify-between items-start mb-3">
                <div class="flex items-center gap-2">
                    <span class="flex items-center justify-center w-6 h-6 rounded-full bg-blue-600 text-white text-xs font-bold">
                        ${rank}
                    </span>
                    <p class="text-xs font-mono text-gray-500 dark:text-gray-400">
                        ID: <span class="text-gray-700 dark:text-gray-300">${result.id.substring(0, 8)}...</span>
                    </p>
                    ${matchTypeBadge}
                </div>
                <span class="px-2 py-1 rounded-full text-xs font-semibold ${scoreColor.bg} ${scoreColor.text}">
                    ${scorePercent}% Match
                </span>
            </div>

            <!-- Content -->
            <p class="text-base text-gray-900 dark:text-white leading-relaxed mb-3">
                ${truncatedText}
            </p>

            <!-- Metadata -->
            ${metadata.length > 0 ? `
                <div class="flex flex-wrap gap-2 pt-3 border-t border-gray-200 dark:border-gray-700">
                    ${metadata.map(([key, value]) => `
                        <span class="px-2 py-1 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded text-xs">
                            <strong>${key}:</strong> ${String(value).substring(0, 30)}
                        </span>
                    `).join('')}
                </div>
            ` : ''}

            <!-- Score Details -->
            ${scoreDetailsHtml}

            <!-- Expand Button -->
            <button onclick="showResultDetail(${rank - 1})"
                    class="mt-3 text-sm text-blue-600 hover:text-blue-800 transition-colors flex items-center gap-1">
                <span>查看詳情</span>
                <span class="material-symbols-outlined text-[18px]">arrow_forward</span>
            </button>
        </div>
    `;
}

// Get score color based on percentage
function getScoreColor(percent) {
    if (percent >= 80) {
        return { bg: 'bg-green-100 dark:bg-green-900/50', text: 'text-green-700 dark:text-green-400' };
    } else if (percent >= 60) {
        return { bg: 'bg-blue-100 dark:bg-blue-900/50', text: 'text-blue-700 dark:text-blue-400' };
    } else if (percent >= 40) {
        return { bg: 'bg-orange-100 dark:bg-orange-900/50', text: 'text-orange-700 dark:text-orange-400' };
    } else {
        return { bg: 'bg-gray-100 dark:bg-gray-700', text: 'text-gray-700 dark:text-gray-400' };
    }
}

// Show result detail (placeholder for now)
let currentResults = [];
window.showResultDetail = function (index) {
    if (index < 0 || index >= currentResults.length) {
        alert('無效的結果索引');
        return;
    }

    const result = currentResults[index];

    // For now, show a detailed alert with result information
    // You can implement a modal later
    const details = `
標題: ${result.title || 'N/A'}
月份: ${result.month || 'N/A'}
評分: ${Math.round((result._rankingScore || 0) * 100)}%
連結: ${result.link || 'N/A'}

內容:
${result.content || 'N/A'}
    `.trim();

    alert(details);
};

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
        <span class="material-symbols-outlined text-gray-400 text-6xl">search_off</span>
        <h3 class="mt-4 text-lg font-medium text-gray-900 dark:text-white">${title}</h3>
        <p class="mt-2 text-sm text-gray-500 dark:text-gray-400">${subtitle}</p>
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
