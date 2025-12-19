/**
 * Results Rendering Module
 */

import * as DOM from './dom.js';
import { searchConfig } from './config.js';
import { hideAllStates, showEmpty } from './ui.js';

// Current Results Storage
export let currentResults = [];

/**
 * Render search results
 * @param {Object} data - Search response data
 * @param {number} duration - Search duration in ms
 * @param {string} query - User search query
 */
export function renderResults(data, duration, query) {
    console.log('Rendering results...');
    console.log('  Data:', data);
    console.log('  Duration:', duration);

    hideAllStates();

    // Extract results and intent from SearchService response
    const results = data.results || [];
    const intent = data.intent;

    console.log('  Results array:', results);
    console.log('  Intent:', intent);

    // Show Intent & Stats Container (always shown after search)
    DOM.intentContainer.classList.remove('hidden');
    DOM.displayQuery.textContent = query;

    // Show/Hide LLM Details
    if (intent && searchConfig.enableLlm) {
        console.log('Updating intent display');
        DOM.llmDetails.classList.remove('hidden');
        updateIntentDisplay(intent);
    } else {
        DOM.llmDetails.classList.add('hidden');
    }

    // Update results count and search time (now part of intentContainer)
    DOM.resultsCount.textContent = results.length;
    DOM.searchTimeValue.textContent = duration;

    if (results.length === 0) {
        console.log('No results found');
        showEmpty('沒有找到相關結果', '請嘗試不同的搜尋查詢');
        return;
    }

    // Store results globally for detail view
    currentResults = results;

    // Render result cards
    DOM.resultsContainer.classList.remove('hidden');
    DOM.resultsContainer.innerHTML = results.map((result, index) => {
        return renderResultCard(result, index + 1);
    }).join('');

    console.log('Results rendered successfully');
}

/**
 * Update intent display section
 * @param {Object} intent - Intent object from search response
 */
function updateIntentDisplay(intent) {
    if (!intent) return;

    DOM.intentContainer.classList.remove('hidden');

    // Update Keywords & Semantic Query
    DOM.intentKeywordQuery.textContent = intent.keyword_query || 'N/A';
    DOM.intentSemanticQuery.textContent = intent.semantic_query || 'N/A';

    // Update Filters
    DOM.intentFilters.innerHTML = '';
    const filters = intent.filters || {};

    // 1. Year Month
    if (filters.year_month && filters.year_month.length > 0) {
        const yearMonthItems = filters.year_month.map(ym =>
            `<span class="px-2 py-0.5 rounded border text-xs bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-300 border-blue-200 dark:border-blue-700">${ym}</span>`
        ).join('');
        DOM.intentFilters.innerHTML += yearMonthItems;
    }

    // 2. Workspaces
    if (filters.workspaces && filters.workspaces.length > 0) {
        const workspaceItems = filters.workspaces.map(ws =>
            `<span class="px-2 py-0.5 rounded border text-xs bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-300 border-green-200 dark:border-green-700">${ws}</span>`
        ).join('');
        DOM.intentFilters.innerHTML += workspaceItems;
    }

    // 3. Links
    if (filters.links && filters.links.length > 0) {
        const linkItems = filters.links.map(link =>
            `<span class="px-2 py-0.5 rounded border text-xs bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-300 border-purple-200 dark:border-purple-700">${link}</span>`
        ).join('');
        DOM.intentFilters.innerHTML += linkItems;
    }

    // 4. Limit (Always show)
    const limitVal = intent.limit !== null && intent.limit !== undefined ? intent.limit : 'Null';
    const limitClass = (intent.limit !== null && intent.limit !== undefined) ?
        "bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-300 border-gray-200 dark:border-gray-600" :
        "bg-transparent text-gray-400 border-gray-200 dark:border-gray-700 border-dashed";

    DOM.intentFilters.innerHTML += `<span class="px-2 py-0.5 rounded border text-xs ${limitClass}">Limit: ${limitVal}</span>`;
}

/**
 * Render a single result card
 * @param {Object} result - Result object
 * @param {number} rank - Result rank (1-based)
 * @returns {string} HTML string
 */
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

/**
 * Toggle result card expansion
 * @param {number} index - Result index (0-based)
 */
export function toggleResult(index) {
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
        badge.className = "px-2 py-1 bg-primary/20 dark:bg-primary/30 text-primary dark:text-primary-light text-xs font-bold rounded";

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

/**
 * Apply threshold to current results (real-time update)
 */
export function applyThresholdToResults() {
    if (!currentResults || currentResults.length === 0) return;

    const resultCards = DOM.resultsContainer.querySelectorAll('.result-card-container');
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
