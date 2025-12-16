// Collection Search - Vector Database Search Interface

// Get collection name from window
const COLLECTION_NAME = window.COLLECTION_NAME;

// DOM Elements
const searchInput = document.getElementById('searchInput');
const searchBtn = document.getElementById('searchBtn');
const searchIconBtn = document.getElementById('searchIconBtn');
const topKSlider = document.getElementById('topKSlider');
const topKValue = document.getElementById('topKValue');
const rerankToggle = document.getElementById('rerankToggle');
const rerankTopNContainer = document.getElementById('rerankTopNContainer');
const rerankTopNSlider = document.getElementById('rerankTopNSlider');
const rerankTopNValue = document.getElementById('rerankTopNValue');

// State Elements
const loadingState = document.getElementById('loadingState');
const errorState = document.getElementById('errorState');
const errorMessage = document.getElementById('errorMessage');
const emptyState = document.getElementById('emptyState');
const resultsContainer = document.getElementById('resultsContainer');
const resultsInfo = document.getElementById('resultsInfo');
const resultsCount = document.getElementById('resultsCount');
const rerankBadge = document.getElementById('rerankBadge');
const searchTime = document.getElementById('searchTime');
const searchTimeValue = document.getElementById('searchTimeValue');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    updateSliderValues();
});

// Event Listeners
function setupEventListeners() {
    // Search triggers
    searchBtn.addEventListener('click', performSearch);
    searchIconBtn.addEventListener('click', performSearch);
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            performSearch();
        }
    });

    // Sliders
    topKSlider.addEventListener('input', (e) => {
        topKValue.textContent = e.target.value;
    });

    rerankTopNSlider.addEventListener('input', (e) => {
        rerankTopNValue.textContent = e.target.value;
    });

    // Rerank toggle
    rerankToggle.addEventListener('change', (e) => {
        if (e.target.checked) {
            rerankTopNContainer.classList.remove('hidden');
            rerankTopNContainer.classList.add('flex');
        } else {
            rerankTopNContainer.classList.add('hidden');
            rerankTopNContainer.classList.remove('flex');
        }
    });
}

// Update slider initial values
function updateSliderValues() {
    topKValue.textContent = topKSlider.value;
    rerankTopNValue.textContent = rerankTopNSlider.value;
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
        const response = await fetch(`/api/search/${COLLECTION_NAME}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                query: query,
                top_k: parseInt(topKSlider.value),
                use_rerank: rerankToggle.checked,
                rerank_top_n: parseInt(rerankTopNSlider.value)
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

    if (!data.results || data.results.length === 0) {
        showEmpty('沒有找到相關結果', '請嘗試不同的搜尋查詢');
        return;
    }

    // Show results info
    resultsInfo.classList.remove('hidden');
    resultsCount.textContent = data.total;

    // Show rerank badge if applicable
    if (data.reranked) {
        rerankBadge.classList.remove('hidden');
    } else {
        rerankBadge.classList.add('hidden');
    }

    // Show search time
    searchTime.classList.remove('hidden');
    searchTimeValue.textContent = duration;

    // Render result cards
    resultsContainer.classList.remove('hidden');
    resultsContainer.innerHTML = data.results.map((result, index) => {
        return renderResultCard(result, index + 1);
    }).join('');
}

// Render Single Result Card
function renderResultCard(result, rank) {
    const score = result.rerank_score !== undefined ? result.rerank_score : result.score;
    const scorePercent = Math.round(score * 100);
    const scoreColor = getScoreColor(scorePercent);

    // Extract text from payload
    const text = result.payload.text || result.payload.content || JSON.stringify(result.payload);
    const truncatedText = text.length > 300 ? text.substring(0, 300) + '...' : text;

    // Get metadata
    const metadata = Object.entries(result.payload)
        .filter(([key]) => key !== 'text' && key !== 'content')
        .slice(0, 3); // Show max 3 metadata fields

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
                    ${scorePercent}% ${result.rerank_score !== undefined ? 'Relevance' : 'Similarity'}
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
window.showResultDetail = function(index) {
    // Store results for detail view
    // For now, just alert - you can implement a modal later
    alert(`詳細資訊功能開發中... (Result #${index + 1})`);
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
