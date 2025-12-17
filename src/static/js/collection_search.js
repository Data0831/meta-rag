// Collection Search - Meilisearch Hybrid Search Interface
// Supports keyword search, semantic search, and metadata filtering

/**
 * Search Configuration
 *
 * To add UI controls for these settings, add the following elements to your HTML:
 *
 * For semantic ratio control (slider):
 * <input type="range" id="semanticRatioSlider" min="0" max="1" step="0.1" value="0.5">
 * <span id="semanticRatioValue">50%</span>
 *
 * For limit control (number input):
 * <input type="number" id="limitInput" min="1" max="100" value="10">
 */
let searchConfig = {
    limit: 10,  // Number of results to return
    semanticRatio: 0.5  // Weight for semantic search (0.0 = pure keyword, 1.0 = pure semantic)
};

// DOM Elements
const searchInput = document.getElementById('searchInput');
const searchIconBtn = document.getElementById('searchIconBtn');

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
    setupEventListeners();
    setupSearchConfig();
});

// Setup search configuration (can be extended with UI controls)
function setupSearchConfig() {
    // Try to get semantic ratio slider if it exists in the UI
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

    // Try to get limit input if it exists in the UI
    const limitInput = document.getElementById('limitInput');
    if (limitInput) {
        limitInput.addEventListener('change', (e) => {
            const value = parseInt(e.target.value);
            if (value > 0 && value <= 100) {
                searchConfig.limit = value;
            }
        });
    }
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

    if (!query) {
        showError('請輸入搜尋查詢');
        return;
    }

    showLoading();

    const startTime = performance.now();

    try {
        const response = await fetch('/api/collection_search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                query: query,
                limit: searchConfig.limit,
                semantic_ratio: searchConfig.semanticRatio
            })
        });

        const endTime = performance.now();
        const duration = Math.round(endTime - startTime);

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || `HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        renderResults(data, duration);

    } catch (error) {
        showError(error.message);
    }
}

// Render Search Results
function renderResults(data, duration) {
    hideAllStates();

    // Extract results from SearchService response
    const results = data.results || [];

    if (results.length === 0) {
        showEmpty('沒有找到相關結果', '請嘗試不同的搜尋查詢');
        return;
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

    return `
        <div class="rounded-lg bg-gray-50 dark:bg-gray-800 p-5 card-shadow transition-shadow hover:shadow-lg">
            <!-- Header -->
            <div class="flex justify-between items-start mb-3">
                <div class="flex items-center gap-2">
                    <span class="flex items-center justify-center w-6 h-6 rounded-full bg-blue-600 text-white text-xs font-bold">
                        ${rank}
                    </span>
                    <p class="text-xs font-mono text-gray-500 dark:text-gray-400">
                        ID: <span class="text-gray-700 dark:text-gray-300">${result.id.substring(0, 8)}...</span>
                    </p>
                </div>
                <span class="px-2 py-1 rounded-full text-xs font-semibold ${scoreColor.bg} ${scoreColor.text}">
                    ${scorePercent}% Similarity
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
    hideAllStates();
    loadingState.classList.remove('hidden');
    loadingState.classList.add('flex');
}

function showError(message) {
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
}
