import * as DOM from './dom.js';
import { escapeHtml, getScoreDisplayInfo } from './utils.js';
import { EMBEDDING_DIMENSIONS } from './constants.js';

// Model configuration cache
let MODEL_CONFIGS = {};
let DEFAULT_MODEL_ID = '';

export function setModelConfig(config) {
    MODEL_CONFIGS = {};
    if (config.models) {
        config.models.forEach(model => {
            MODEL_CONFIGS[model.id] = model;
        });
    }
    DEFAULT_MODEL_ID = config.default_model || '';
    populateModelSelects(config.models);
}

function populateModelSelects(models) {
    if (!models) return;

    const selects = [DOM.llmSelect, DOM.rewriteModelSelect, DOM.relevanceModelSelect];
    
    selects.forEach(select => {
        if (!select) return;
        
        const currentValue = select.value;
        select.innerHTML = '';
        
        models.forEach(model => {
            const option = document.createElement('option');
            option.value = model.id;
            option.textContent = model.name;
            select.appendChild(option);
        });

        // Restore selection if possible, otherwise use default
        if (currentValue && MODEL_CONFIGS[currentValue]) {
            select.value = currentValue;
        } else if (DEFAULT_MODEL_ID) {
            select.value = DEFAULT_MODEL_ID;
        }
    });

    // Update limit display for the main LLM select
    if (DOM.llmSelect) {
        updateModelLimit(DOM.llmSelect.value);
    }
}

// Helper function to get embedding model from collection name
export function getEmbeddingModelFromCollection(collectionName) {
    // Map: collection-name -> embedding-model
    const collectionToModel = {
        'nomic-hybrid-coll': 'nomic-embed-text',
        'nomic-coll': 'nomic-embed-text',
        'bge-hybrid-coll': 'bge-m3:latest',
        'bge-coll': 'bge-m3:latest'
    };
    return collectionToModel[collectionName] || 'nomic-embed-text';
}

// Helper function to get current collection name from collection select
export function getCollectionName() {
    // Get from collection select dropdown
    return DOM.collectionNameInput?.value || 'nomic-hybrid-coll';
}

// Helper function to get current embedding model based on selected collection
export function getCurrentEmbeddingModel() {
    const collectionName = getCollectionName();
    return getEmbeddingModelFromCollection(collectionName);
}

export function updateCollectionStatsDisplay(count) {
    if (count !== null) {
        DOM.vectorsCountHeader.textContent = `(${count.toLocaleString()} vectors)`;
    } else {
        DOM.vectorsCountHeader.textContent = '(error)';
    }
}

export function updateTokenStats(tokenStats) {
    if (!tokenStats) {
        DOM.tokenStatsHeader.textContent = '0 / 200K';
        DOM.tokenPercentageHeader.textContent = '(0%)';
        if (DOM.historyTokenStatsHeader) DOM.historyTokenStatsHeader.textContent = '0';
        return;
    }

    const conversationTokens = tokenStats.conversation_tokens || 0;
    const limit = tokenStats.model_limit || 200000;
    const percentage = tokenStats.usage_percentage || 0;
    const historyTokens = tokenStats.session_history_tokens || 0;

    const limitFormatted = limit >= 1000000
        ? `${(limit / 1000000).toFixed(1)}M` 
        : `${Math.round(limit / 1000)}K`;

    DOM.tokenStatsHeader.textContent = `${conversationTokens.toLocaleString()} / ${limitFormatted}`;
    DOM.tokenPercentageHeader.textContent = `(${percentage.toFixed(2)}%)`;
    
    if (DOM.historyTokenStatsHeader) {
        DOM.historyTokenStatsHeader.textContent = historyTokens.toLocaleString();
    }

    if (percentage > 80) {
        DOM.tokenStatsHeader.classList.remove('text-primary', 'text-yellow-500');
        DOM.tokenStatsHeader.classList.add('text-orange-500');
    } else if (percentage > 50) {
        DOM.tokenStatsHeader.classList.remove('text-primary', 'text-orange-500');
        DOM.tokenStatsHeader.classList.add('text-yellow-500');
    } else {
        DOM.tokenStatsHeader.classList.remove('text-orange-500', 'text-yellow-500');
        DOM.tokenStatsHeader.classList.add('text-primary');
    }
}

export function updateModelLimit(modelName) {
    const model = MODEL_CONFIGS[modelName];
    const limit = model ? model.token_limit : 200000;

    const limitFormatted = limit >= 1000000
        ? `${(limit / 1000000).toFixed(1)}M`
        : `${Math.round(limit / 1000)}K`;

    // Get current token count from display (or default to 0)
    const currentText = DOM.tokenStatsHeader.textContent;
    const currentTokens = currentText.split('/')[0].trim().replace(/,/g, '');

    DOM.tokenStatsHeader.textContent = `${parseInt(currentTokens) || 0} / ${limitFormatted}`;

    // Update percentage display
    const tokens = parseInt(currentTokens) || 0;
    const percentage = (tokens / limit) * 100;
    DOM.tokenPercentageHeader.textContent = `(${percentage.toFixed(2)}%)`;

    // Update color based on percentage
    if (percentage > 80) {
        DOM.tokenStatsHeader.classList.remove('text-primary', 'text-yellow-500');
        DOM.tokenStatsHeader.classList.add('text-orange-500');
    } else if (percentage > 50) {
        DOM.tokenStatsHeader.classList.remove('text-primary', 'text-orange-500');
        DOM.tokenStatsHeader.classList.add('text-yellow-500');
    } else {
        DOM.tokenStatsHeader.classList.remove('text-orange-500', 'text-yellow-500');
        DOM.tokenStatsHeader.classList.add('text-primary');
    }
}

export function updateDisplayHeaders() {
    const collectionName = getCollectionName();
    const embeddingModel = getCurrentEmbeddingModel();

    const isHybrid = collectionName.includes('hybrid');

    DOM.collectionDisplayHeader.textContent = collectionName;

    if (DOM.denseModelNameHeader) {
        DOM.denseModelNameHeader.textContent = embeddingModel;
    }

    if (DOM.vectorDimensionHeader) {
        const dimension = EMBEDDING_DIMENSIONS[embeddingModel] || 768;
        DOM.vectorDimensionHeader.textContent = `(${dimension}d)`;
    }

    if (isHybrid) {
        DOM.sparseModelInfoHeader.classList.remove('hidden');
    } else {
        DOM.sparseModelInfoHeader.classList.add('hidden');
    }

    if (DOM.retrievalModeHeader) {
        DOM.retrievalModeHeader.textContent = isHybrid ? 'Hybrid' : 'Dense';
    }

    // Update threshold toggle availability
    updateThresholdAvailability();
}

export function updateThresholdAvailability() {
    const collectionName = getCollectionName();
    const isHybrid = collectionName.includes('hybrid');
    const isRerankEnabled = DOM.rerankCheckbox.checked;

    // Only enable in Dense mode AND no rerank
    const canUseThreshold = !isHybrid && !isRerankEnabled;

    if (DOM.thresholdToggle) {
        DOM.thresholdToggle.disabled = !canUseThreshold;

        if (!canUseThreshold) {
            DOM.thresholdToggle.checked = false;
            DOM.thresholdConfig.classList.add('hidden');
            DOM.thresholdDisabledNotice.classList.remove('hidden');
        } else {
            DOM.thresholdDisabledNotice.classList.add('hidden');
        }
    }

    // Update rerank threshold availability
    updateRerankThresholdAvailability();
}

export function updateRerankThresholdAvailability() {
    const isRerankEnabled = DOM.rerankCheckbox.checked;

    // In integrated UI, threshold is part of reranker config.
    // We ensure the hidden toggle is checked so the logic uses the threshold value.
    if (DOM.rerankThresholdToggle) {
        DOM.rerankThresholdToggle.disabled = !isRerankEnabled;
        DOM.rerankThresholdToggle.checked = true; // Always check it so it's active when Rerank is active
    }

    if (DOM.rerankThresholdConfig) {
        DOM.rerankThresholdConfig.classList.remove('hidden');
    }
    
    // Legacy notice handling (if element exists)
    if (DOM.rerankThresholdDisabledNotice) {
        DOM.rerankThresholdDisabledNotice.classList.add('hidden');
    }
}

export function updateCharCount() {
    const count = DOM.systemInstructionInput.value.length;
    DOM.promptCharCount.textContent = `${count} 字元`;
}

export function appendUserBubble(text) {
    const html = `
        <div class="flex justify-end">
            <div class="flex flex-col items-end gap-3 max-w-2xl">
                <div class="p-4 rounded-lg rounded-br-none bg-primary shadow-soft">
                    <p class="text-white text-base leading-relaxed">${escapeHtml(text)}</p>
                </div>
            </div>
        </div>`;
    DOM.chatContainer.insertAdjacentHTML('beforeend', html);
    DOM.chatContainer.scrollTop = DOM.chatContainer.scrollHeight;
}

export function appendLoadingBubble() {
    const id = 'loading-' + Date.now();
    const html = `
        <div id="${id}" class="flex flex-col items-start gap-3 max-w-2xl">
            <div class="p-4 rounded-lg rounded-bl-none bg-bubble-ai-light dark:bg-bubble-ai-dark">
                <div class="flex space-x-1 h-6 items-center">
                    <div class="w-2 h-2 bg-text-secondary-light rounded-full typing-dot"></div>
                    <div class="w-2 h-2 bg-text-secondary-light rounded-full typing-dot"></div>
                    <div class="w-2 h-2 bg-text-secondary-light rounded-full typing-dot"></div>
                </div>
            </div>
        </div>`;
    DOM.chatContainer.insertAdjacentHTML('beforeend', html);
    return id;
}

export function removeBubble(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

export function appendAIBubble(text, sources = [], isReranked = false, metadata = {}) {
    let sourcesHTML = '';
    
    // Check for explicit irrelevance
    if (metadata.is_relevant === false) {
         sourcesHTML = `
            <details class="w-full">
                <summary class="list-none cursor-pointer flex items-center gap-2 text-sm text-text-secondary-light dark:text-text-secondary-dark font-medium py-1 px-2 rounded hover:bg-neutral-200 dark:hover:bg-neutral-700 transition-colors">
                    <span aria-hidden="true" class="material-symbols-outlined !font-thin text-amber-500">warning</span>
                    <span>0 References</span>
                    <span class="text-xs bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400 px-2 py-0.5 rounded-full ml-2">
                        Irrelevant to Collection
                    </span>
                </summary>
                <div class="mt-2 p-3 text-xs text-text-secondary-light dark:text-text-secondary-dark italic bg-neutral-50 dark:bg-neutral-800/50 rounded-lg">
                    Query was determined to be unrelated to the provided collection description. Answering with general knowledge.
                </div>
            </details>
        `;
    } else if (sources && sources.length > 0) {
        const sourcesList = sources.map((s, i) => {
            const scoreInfo = getScoreDisplayInfo(s.score, s.type, isReranked);
            const filename = s.filename || 'Unknown Source';
            const isExcluded = s.excluded === true;

            // Apply opacity and different styling for excluded sources
            const itemOpacity = isExcluded ? 'opacity-50' : '';
            const excludedBadge = isExcluded
                ? `<span class="text-xs font-semibold bg-neutral-300 dark:bg-neutral-700 text-neutral-600 dark:text-neutral-400 px-2 py-0.5 rounded-full">未引用</span>`
                : '';

            return `
            <div class="reference-item flex items-start gap-3 py-2 ${itemOpacity}">
                <span class="text-sm font-semibold text-text-secondary-light dark:text-text-secondary-dark mt-0.5">${i + 1}.</span>
                <div class="flex-1">
                    <div class="flex items-center gap-2 mb-1">
                        <span class="material-symbols-outlined !text-base text-text-secondary-light dark:text-text-secondary-dark">description</span>
                        <p class="text-sm font-medium text-text-primary-light dark:text-text-primary-dark">${escapeHtml(filename)}</p>
                        <span class="material-symbols-outlined !text-base text-primary cursor-help" title="Hover to view text snippet">info</span>
                    </div>
                    <div class="flex items-center gap-2 mb-2">
                        <span class="text-xs font-medium ${scoreInfo.colorClass} px-2 py-0.5 rounded-full">${scoreInfo.label}: ${s.score.toFixed(4)}</span>
                        <span class="text-xs font-semibold ${scoreInfo.badgeClass} px-2 py-0.5 rounded-full">${scoreInfo.confidence}</span>
                        ${excludedBadge}
                    </div>
                    <div class="reference-tooltip absolute left-0 right-0 mt-1 p-3 bg-white dark:bg-neutral-900 border border-primary/30 dark:border-primary/50 rounded-lg shadow-medium z-50 max-w-full">
                        <p class="text-xs text-text-secondary-light dark:text-text-secondary-dark mb-1.5 font-semibold flex items-center gap-1">
                            <span class="material-symbols-outlined !text-sm">article</span>
                            文本片段預覽
                        </p>
                        <p class="text-xs text-text-primary-light dark:text-text-primary-dark leading-relaxed max-h-32 overflow-y-auto">${escapeHtml(s.text || 'No text available')}</p>
                    </div>
                </div>
            </div>
        `}).join('');
        
        // Optimized Query Display
        const optimizedQueryHTML = metadata.optimized_query 
            ? `<div class="ml-auto flex items-center gap-1.5 text-xs text-primary bg-primary/10 px-2 py-1 rounded-md" title="Optimized Query used for vector search">
                 <span class="material-symbols-outlined !text-sm">auto_fix</span>
                 <span class="font-mono max-w-[200px] truncate">"${escapeHtml(metadata.optimized_query)}"</span>
               </div>`
            : '<span aria-hidden="true" class="material-symbols-outlined !font-thin ml-auto transform transition-transform duration-200">expand_more</span>';

        sourcesHTML = `
            <details class="w-full">
                <summary class="list-none cursor-pointer flex items-center gap-2 text-sm text-text-secondary-light dark:text-text-secondary-dark font-medium py-1 px-2 rounded hover:bg-neutral-200 dark:hover:bg-neutral-700 transition-colors">
                    <span aria-hidden="true" class="material-symbols-outlined !font-thin">info</span>
                    <span>${sources.length} References</span>
                    ${optimizedQueryHTML}
                </summary>
                <div class="mt-2 p-4 rounded-lg border border-border-light dark:border-border-dark bg-white dark:bg-neutral-800 shadow-medium space-y-3">
                    ${sourcesList}
                </div>
            </details>
        `;
    }

    const formattedText = escapeHtml(text).replace(/\*\*(.*?)\*\*/g, '<b>$1</b>').replace(/\n/g, '<br>');

    const html = `
        <div class="flex flex-col items-start gap-3 max-w-2xl">
            <div class="p-4 rounded-lg rounded-bl-none bg-bubble-ai-light dark:bg-bubble-ai-dark">
                <p class="text-text-primary-light dark:text-text-primary-dark text-base leading-relaxed">${formattedText}</p>
            </div>
            ${sourcesHTML}
        </div>`;
    DOM.chatContainer.insertAdjacentHTML('beforeend', html);
    DOM.chatContainer.scrollTop = DOM.chatContainer.scrollHeight;
}

export function appendSystemMessage(message, type = 'success', autoHideDelay = 3000) {
    const bgColor = type === 'error'
        ? 'bg-red-100 dark:bg-red-900/30 border-red-300 dark:border-red-700'
        : 'bg-green-100 dark:bg-green-900/30 border-green-300 dark:border-green-700';

    const textColor = type === 'error'
        ? 'text-red-700 dark:text-red-300'
        : 'text-green-700 dark:text-green-300';

    const messageId = 'system-msg-' + Date.now();
    const html = `
        <div id="${messageId}" class="flex justify-center my-2 transition-opacity duration-500 opacity-100">
            <div class="px-4 py-2 rounded-lg border ${bgColor} ${textColor} text-sm font-medium shadow-soft">
                ${escapeHtml(message)}
            </div>
        </div>`;
    DOM.chatContainer.insertAdjacentHTML('beforeend', html);
    DOM.chatContainer.scrollTop = DOM.chatContainer.scrollHeight;

    if (autoHideDelay > 0) {
        setTimeout(() => {
            const messageEl = document.getElementById(messageId);
            if (messageEl) {
                messageEl.style.opacity = '0';
                setTimeout(() => {
                    messageEl.remove();
                }, 500);
            }
        }, autoHideDelay);
    }
}

export function showStatus(message, type = 'info') {
    DOM.uploadStatusText.textContent = message;
    DOM.uploadStatus.classList.remove('hidden');

    DOM.uploadStatusText.className = 'text-xs';
    if (type === 'success') {
        DOM.uploadStatusText.classList.add('text-green-700', 'dark:text-green-300');
    } else if (type === 'error') {
        DOM.uploadStatusText.classList.add('text-red-700', 'dark:text-red-300');
    } else if (type === 'warning') {
        DOM.uploadStatusText.classList.add('text-orange-600', 'dark:text-orange-400');
    } else {
        DOM.uploadStatusText.classList.add('text-text-primary-light', 'dark:text-text-primary-dark');
    }

    if (type !== 'info') {
        setTimeout(() => {
            DOM.uploadStatus.classList.add('hidden');
        }, 8000);
    }
}

export function enableRetryButton() {
    DOM.retryBtn.disabled = false;
    DOM.retryBtn.classList.remove('opacity-50', 'cursor-not-allowed');
    DOM.retryBtn.classList.add('hover:bg-gray-400', 'dark:hover:bg-gray-600', 'hover:text-primary-light', 'dark:hover:text-primary-dark'); // Adjust hover color as needed
}

export function disableRetryButton() {
    DOM.retryBtn.disabled = true;
    DOM.retryBtn.classList.add('opacity-50', 'cursor-not-allowed');
    DOM.retryBtn.classList.remove('hover:bg-gray-400', 'dark:hover:bg-gray-600', 'hover:text-primary-light', 'dark:hover:text-primary-dark');
}

export function removeLastUserAndAiBubbles() {
    const chatBubbles = DOM.chatContainer.querySelectorAll(':scope > div'); // Direct children div elements

    // Ensure there are at least two bubbles (user + AI)
    if (chatBubbles.length >= 2) {
        // Remove the last AI bubble
        chatBubbles[chatBubbles.length - 1].remove();
        // Remove the user bubble before it
        chatBubbles[chatBubbles.length - 2].remove();
    }
}
