/**
 * UI State Management Module
 */

import * as DOM from './dom.js';

/**
 * Show loading state
 */
export function showLoading() {
    console.log('⏳ Showing loading state');
    hideAllStates();
    DOM.loadingState.classList.remove('hidden');
    DOM.loadingState.classList.add('flex');
}

/**
 * Show error state
 * @param {string} message - Error message to display
 */
export function showError(message) {
    console.error('🚨 Showing error:', message);
    hideAllStates();
    DOM.errorMessage.textContent = message;
    DOM.errorState.classList.remove('hidden');
}

/**
 * Show empty state
 * @param {string} title - Empty state title
 * @param {string} subtitle - Empty state subtitle
 */
export function showEmpty(title, subtitle) {
    hideAllStates();
    DOM.emptyState.classList.remove('hidden');
    DOM.emptyState.innerHTML = `
        <span class="material-icons-round text-slate-300 dark:text-slate-600 text-6xl mb-4">search_off</span>
        <h3 class="text-lg font-medium text-slate-700 dark:text-slate-300">${title}</h3>
        <p class="text-sm text-slate-500 dark:text-slate-400 mt-2">${subtitle}</p>
    `;
}

/**
 * Hide all state elements
 */
export function hideAllStates() {
    DOM.loadingState.classList.add('hidden');
    DOM.loadingState.classList.remove('flex');
    DOM.errorState.classList.add('hidden');
    DOM.emptyState.classList.add('hidden');
    DOM.resultsContainer.classList.add('hidden');
    if (DOM.intentContainer) DOM.intentContainer.classList.add('hidden');
}
