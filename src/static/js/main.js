// RAG Chat Dashboard - Main JavaScript
import * as DOM from './modules/dom.js';
import * as UI from './modules/ui.js';
import * as API from './modules/api.js';
import { DEFAULT_SYSTEM_INSTRUCTION } from './modules/constants.js';

// State
let selectedFile = null;
let lastQuery = null; // Store the last query for retry functionality

// Navigation handling
document.addEventListener('DOMContentLoaded', async () => {
    // Automatically clear LLM history on page load to ensure clean state
    try {
        await API.clearLlmHistory();
        console.log("Automatically cleared LLM history on page load.");
    } catch (e) {
        console.error("Failed to auto-clear history:", e);
    }

    // Highlight active tab
    const currentPath = window.location.pathname;
    const tabs = document.querySelectorAll('a[href^="/"]');

    tabs.forEach(tab => {
        const href = tab.getAttribute('href');
        if (href === currentPath || (currentPath === '/' && href === '/')) {
            tab.classList.add('bg-background-light', 'dark:bg-background-dark', 'text-text-primary-light', 'dark:text-text-primary-dark', 'shadow-sm', 'z-10');
            tab.classList.remove('text-text-secondary-light', 'dark:text-text-secondary-dark');
        }
    });

    UI.updateCharCount();
    UI.updateDisplayHeaders();
    UI.updateThresholdAvailability();
    UI.updateRerankThresholdAvailability();
    updateCollectionStatsWrapper();

    // Fetch Model Configuration
    try {
        const config = await API.fetchConfig();
        UI.setModelConfig(config);
    } catch (error) {
        console.error("Failed to fetch model configuration:", error);
    }
    
    // UI.updateModelLimit will be called inside UI.setModelConfig

    UI.disableRetryButton(); // Disable retry button on page load
});

// Wrapper to bridge API and UI for collection stats
async function updateCollectionStatsWrapper() {
    const collectionName = UI.getCollectionName();
    try {
        const data = await API.fetchCollectionStats(collectionName);
        if (data.exists) {
            UI.updateCollectionStatsDisplay(data.points_count);
        } else {
            UI.updateCollectionStatsDisplay(0);
        }
    } catch (error) {
        console.error('Error fetching collection stats:', error);
        UI.updateCollectionStatsDisplay(null);
    }
}

// Update Top-K Display
DOM.topKSlider.addEventListener('input', (e) => {
    DOM.topKDisplay.textContent = e.target.value;
});

// Update Rerank Top-N Display
DOM.rerankTopNSlider.addEventListener('input', (e) => {
    DOM.rerankTopNDisplay.textContent = e.target.value;
});

// Update Chunk Size Display
if (DOM.chunkSizeSlider && DOM.chunkSizeDisplay) {
    DOM.chunkSizeSlider.addEventListener('input', (e) => {
        DOM.chunkSizeDisplay.textContent = e.target.value;
    });
}

// Update Token Limit Display when LLM Model changes
DOM.llmSelect.addEventListener('change', (e) => {
    UI.updateModelLimit(e.target.value);
});

// Toggle Intelligent Routing Configuration Panel
// Logic: If either "Query Rewrite" OR "Relevance Check" is enabled, show the description field.
function updateRoutingConfigVisibility() {
    const isRewriteEnabled = DOM.optimizeQueryToggle.checked;
    const isRelevanceEnabled = DOM.relevanceCheckToggle.checked;

    // Show/Hide Collection Description
    if (isRewriteEnabled || isRelevanceEnabled) {
        DOM.optimizeQueryConfig.classList.remove('hidden');
    } else {
        DOM.optimizeQueryConfig.classList.add('hidden');
    }

    // Show/Hide Rewrite Model Select
    if (isRewriteEnabled) {
        DOM.rewriteModelConfig.classList.remove('hidden');
    } else {
        DOM.rewriteModelConfig.classList.add('hidden');
    }

    // Show/Hide Relevance Model Select
    if (isRelevanceEnabled) {
        DOM.relevanceModelConfig.classList.remove('hidden');
    } else {
        DOM.relevanceModelConfig.classList.add('hidden');
    }
}

// Collapsible Section Logic
DOM.routingHeaderBtn.addEventListener('click', () => {
    const isHidden = DOM.routingContent.classList.contains('hidden');
    if (isHidden) {
        DOM.routingContent.classList.remove('hidden');
        DOM.routingArrow.classList.add('rotate-180');
    } else {
        DOM.routingContent.classList.add('hidden');
        DOM.routingArrow.classList.remove('rotate-180');
    }
});

DOM.optimizeQueryToggle.addEventListener('change', updateRoutingConfigVisibility);
DOM.relevanceCheckToggle.addEventListener('change', updateRoutingConfigVisibility);

// Toggle Reranker Configuration Panel
DOM.rerankCheckbox.addEventListener('change', (e) => {
    if (e.target.checked) {
        DOM.rerankConfig.classList.remove('hidden');
    } else {
        DOM.rerankConfig.classList.add('hidden');
    }
    // Update threshold availability when rerank changes
    UI.updateThresholdAvailability();
});

// Update Threshold Value Display
DOM.thresholdValueSlider.addEventListener('input', (e) => {
    DOM.thresholdValueDisplay.textContent = parseFloat(e.target.value).toFixed(2);
});

// Toggle Threshold Configuration Panel
DOM.thresholdToggle.addEventListener('change', (e) => {
    if (e.target.checked) {
        DOM.thresholdConfig.classList.remove('hidden');
    } else {
        DOM.thresholdConfig.classList.add('hidden');
    }
});

// Update Rerank Threshold Value Display
DOM.rerankThresholdValueSlider.addEventListener('input', (e) => {
    DOM.rerankThresholdValueDisplay.textContent = parseFloat(e.target.value).toFixed(2);
});

// Toggle Rerank Threshold Configuration Panel
DOM.rerankThresholdToggle.addEventListener('change', (e) => {
    if (e.target.checked) {
        DOM.rerankThresholdConfig.classList.remove('hidden');
    } else {
        DOM.rerankThresholdConfig.classList.add('hidden');
    }
});

// System Instruction - Character Count
DOM.systemInstructionInput.addEventListener('input', UI.updateCharCount);

// System Instruction - Reset Button
DOM.resetPromptBtn.addEventListener('click', () => {
    DOM.systemInstructionInput.value = DEFAULT_SYSTEM_INSTRUCTION;
    UI.updateCharCount();
});

// Auto-update when collection changes
if (DOM.collectionNameInput) {
    DOM.collectionNameInput.addEventListener('change', (e) => {
        UI.updateDisplayHeaders();
        UI.updateThresholdAvailability();
        updateCollectionStatsWrapper();

        // Update upload button state
        if (e.target.value && selectedFile) {
            DOM.uploadBtn.disabled = false;
        } else {
            DOM.uploadBtn.disabled = true;
        }
    });
}

// Clear Chat
DOM.clearBtn.addEventListener('click', async () => {
    DOM.chatContainer.innerHTML = '';
    lastQuery = null; // Clear last query
    UI.disableRetryButton(); // Disable retry button
    try {
        const data = await API.clearLlmHistory();
        if (data.success) {
            console.log("LLM histories cleared successfully.");
            UI.updateTokenStats(null);
            UI.appendSystemMessage('✓ 聊天記錄與對話歷史已清除');
        } else {
            console.error("Failed to clear LLM histories:", data.error);
            UI.appendSystemMessage('✗ 清除對話歷史失敗: ' + data.error, 'error');
        }
    } catch (error) {
        console.error("Network error while clearing LLM histories:", error);
        UI.appendSystemMessage('✗ 網路錯誤: ' + error.message, 'error');
    }
});

// Send Message Logic
async function sendMessage(messageToSend, isRetry = false) {
    const message = messageToSend || DOM.chatInput.value.trim();
    if (!message) return;

    if (!isRetry) {
        DOM.chatInput.value = '';
        lastQuery = message; // Save the last query for retry
    }

    UI.appendUserBubble(message);
    const loadingId = UI.appendLoadingBubble();
    DOM.chatContainer.scrollTop = DOM.chatContainer.scrollHeight;

    const collectionName = UI.getCollectionName();
    const mode = collectionName.includes('hybrid') ? 'Hybrid' : 'Dense';
    const useRerank = DOM.rerankCheckbox.checked;
    const topK = parseInt(DOM.topKSlider.value);
    const rerankTopN = parseInt(DOM.rerankTopNSlider.value);
    const llmModel = DOM.llmSelect.value;
    const embeddingModel = UI.getCurrentEmbeddingModel();

    // Threshold filtering (only applicable in Dense mode without rerank)
    const useThreshold = DOM.thresholdToggle.checked;
    const thresholdValue = parseFloat(DOM.thresholdValueSlider.value);

    // Rerank threshold filtering (only applicable when rerank is enabled)
    const useRerankThreshold = DOM.rerankThresholdToggle.checked;
    const rerankThresholdValue = parseFloat(DOM.rerankThresholdValueSlider.value);

    const userInstruction = DOM.systemInstructionInput.value.trim();
    const systemPrompt = userInstruction ? userInstruction : null;

    // Query Optimization
    const optimizeQuery = DOM.optimizeQueryToggle.checked;
    const checkRelevance = DOM.relevanceCheckToggle.checked;
    const collectionDescription = DOM.collectionDescriptionInput.value.trim();
    const rewriteModel = DOM.rewriteModelSelect.value;
    const relevanceModel = DOM.relevanceModelSelect.value;

    try {
        const payload = {
            message: message,
            mode: mode,
            use_rerank: useRerank,
            top_k: topK,
            rerank_top_n: rerankTopN,
            llm_model: llmModel,
            embedding_model: embeddingModel,
            system_prompt: systemPrompt,
            use_threshold: useThreshold,
            threshold_value: thresholdValue,
            use_rerank_threshold: useRerankThreshold,
            rerank_threshold_value: rerankThresholdValue,
            optimize_query: optimizeQuery,
            check_relevance: checkRelevance,
            collection_description: collectionDescription,
            rewrite_model: rewriteModel,
            relevance_model: relevanceModel
        };

        const data = await API.sendChatRequest(payload);

        UI.removeBubble(loadingId);

        if (data.error) {
            UI.appendAIBubble("Error: " + data.error);
            UI.disableRetryButton(); // Disable retry if an error occurs
        } else {
            UI.appendAIBubble(
                data.answer, 
                data.sources, 
                useRerank, 
                {
                    optimized_query: data.optimized_query,
                    is_relevant: data.is_relevant
                }
            );
            
            if (data.token_stats) {
                UI.updateTokenStats(data.token_stats);
            }
            UI.enableRetryButton(); // Enable retry button on successful response
        }

    } catch (error) {
        UI.removeBubble(loadingId);
        UI.appendAIBubble("Network Error: " + error.message);
        UI.disableRetryButton(); // Disable retry if a network error occurs
    }
}

// Retry Message Logic
async function retryLastMessage() {
    if (!lastQuery) return; // Only retry if there's a last query

    UI.disableRetryButton();
    UI.removeLastUserAndAiBubbles(); // Remove the last user and AI message from UI

    try {
        await API.clearLastLlmTurn(); // Clear last turn from LLM history on backend
        UI.appendSystemMessage('🔄 正在重試上一則訊息...', 'info', 2000);
        sendMessage(lastQuery, true); // Re-send the last query as a retry
    } catch (error) {
        console.error("Error during retry:", error);
        UI.appendSystemMessage('✗ 重試失敗: ' + error.message, 'error');
        // Re-enable retry if clearLastLlmTurn failed, assuming original state
        UI.enableRetryButton();
    }
}

// Event Listeners for Chat
DOM.sendBtn.addEventListener('click', () => sendMessage());
DOM.chatInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
});
DOM.retryBtn.addEventListener('click', retryLastMessage); // Add event listener for retry button

// ===== FILE UPLOAD FUNCTIONALITY =====

// File Selection Handler
DOM.fileDisplay.addEventListener('click', () => {
    DOM.fileInput.click();
});

DOM.fileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
        selectedFile = file;
        DOM.fileName.textContent = file.name;
        DOM.fileName.classList.add('text-primary', 'font-medium');
        DOM.uploadBtn.disabled = false;
    } else {
        selectedFile = null;
        DOM.fileName.textContent = 'No file selected';
        DOM.fileName.classList.remove('text-primary', 'font-medium');
        DOM.uploadBtn.disabled = true;
    }
});

// Upload File to Qdrant
DOM.uploadBtn.addEventListener('click', async () => {
    if (!selectedFile || !DOM.collectionNameInput.value) {
        UI.showStatus('Please select a file and a collection.', 'error');
        return;
    }

    const collectionName = DOM.collectionNameInput.value;
    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('collection_name', collectionName);

    const mode = collectionName.includes('hybrid') ? 'Hybrid' : 'Dense';
    formData.append('mode', mode);

    const embeddingModel = UI.getCurrentEmbeddingModel();
    formData.append('embedding_model', embeddingModel);

    // Add chunk size from slider
    const chunkSize = DOM.chunkSizeSlider ? DOM.chunkSizeSlider.value : 300; // Default to 300 if slider not found
    formData.append('chunk_size', chunkSize);

    DOM.uploadBtn.disabled = true;
    DOM.uploadBtn.innerHTML = '<span class="material-symbols-outlined !text-base animate-spin">progress_activity</span><span>Uploading...</span>';
    UI.showStatus('Processing file and uploading to Qdrant...', 'info');

    try {
        const { ok, data } = await API.uploadFile(formData);

        if (ok) {
            const message = data.message || `Successfully uploaded ${data.successful_uploads}/${data.chunks_count} chunks`;
            const statusType = data.failed_chunks > 0 ? 'warning' : 'success';
            const failedInfo = data.failed_chunks > 0 ? ` (${data.failed_chunks} failed)` : '';
            UI.showStatus(`✓ ${message}${failedInfo} to collection "${collectionName}"`, statusType);

            DOM.fileInput.value = '';
            selectedFile = null;
            DOM.fileName.textContent = 'No file selected';
            DOM.fileName.classList.remove('text-primary', 'font-medium');
            DOM.uploadBtn.disabled = true;
            DOM.uploadBtn.innerHTML = '<span class="material-symbols-outlined !text-base">cloud_upload</span><span>Upload to Qdrant</span>';

            updateCollectionStatsWrapper();
        } else {
            UI.showStatus(`✗ Error: ${data.error || 'Upload failed'}`, 'error');
            DOM.uploadBtn.disabled = false;
            DOM.uploadBtn.innerHTML = '<span class="material-symbols-outlined !text-base">cloud_upload</span><span>Upload to Qdrant</span>';
        }
    } catch (error) {
        UI.showStatus(`✗ Network Error: ${error.message}`, 'error');
        DOM.uploadBtn.disabled = false;
        DOM.uploadBtn.innerHTML = '<span class="material-symbols-outlined !text-base">cloud_upload</span><span>Upload to Qdrant</span>';
    }
});

// Clear Collection
DOM.clearCollectionBtn.addEventListener('click', async () => {
    const collectionName = DOM.collectionNameInput.value;

    if (!collectionName) {
        UI.showStatus('Please select a collection to clear.', 'error');
        return;
    }

    if (!confirm(`Are you sure you want to clear all documents from collection "${collectionName}"? This action cannot be undone.`)) {
        return;
    }

    DOM.clearCollectionBtn.disabled = true;
    DOM.clearCollectionBtn.innerHTML = '<span class="material-symbols-outlined text-orange-500 !text-base animate-spin">progress_activity</span><p class="text-orange-500 text-sm font-medium">Clearing...</p>';
    UI.showStatus('Clearing collection...', 'info');

    try {
        const { ok, data } = await API.clearCollection(collectionName);

        if (ok) {
            UI.showStatus(`✓ Successfully cleared collection "${collectionName}"`, 'success');
            updateCollectionStatsWrapper();
        } else {
            UI.showStatus(`✗ Error: ${data.error || 'Clear failed'}`, 'error');
        }
    } catch (error) {
        UI.showStatus(`✗ Network Error: ${error.message}`, 'error');
    } finally {
        DOM.clearCollectionBtn.disabled = false;
        DOM.clearCollectionBtn.innerHTML = '<span class="material-symbols-outlined text-orange-500 !text-base">delete_sweep</span><p class="text-orange-500 text-sm font-medium">Clear Collection</p>';
    }
});