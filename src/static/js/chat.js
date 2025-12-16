// RAG Chat Dashboard - Main JavaScript
import * as DOM from './modules/dom.js';
import * as UI from './modules/ui.js';
import * as API from './modules/api.js';
import { DEFAULT_SYSTEM_INSTRUCTION } from './modules/constants.js';

// State
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
    // UI.updateDisplayHeaders(); // Removed dependency on removed UI elements
    // UI.updateThresholdAvailability(); // Removed
    // UI.updateRerankThresholdAvailability(); // Removed

    // Initialize token limit display based on selected LLM model
    UI.updateModelLimit(DOM.llmSelect.value);
    UI.disableRetryButton(); // Disable retry button on page load
});

// Update Token Limit Display when LLM Model changes
DOM.llmSelect.addEventListener('change', (e) => {
    UI.updateModelLimit(e.target.value);
});

// System Instruction - Character Count
DOM.systemInstructionInput.addEventListener('input', UI.updateCharCount);

// System Instruction - Reset Button
DOM.resetPromptBtn.addEventListener('click', () => {
    DOM.systemInstructionInput.value = DEFAULT_SYSTEM_INSTRUCTION;
    UI.updateCharCount();
});

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

    // Hardcoded defaults for Pure Chat Mode
    const mode = 'Chat'; // Changed from 'Hybrid' to 'Chat'
    const useRerank = false;
    const topK = 0; // Not used in Chat mode
    const rerankTopN = 0; // Not used in Chat mode
    const llmModel = DOM.llmSelect.value;
    const embeddingModel = 'nomic-embed-text'; // Placeholder, ignored in Chat mode

    // Threshold filtering
    const useThreshold = false;
    const thresholdValue = 0.5;

    // Rerank threshold filtering
    const useRerankThreshold = false;
    const rerankThresholdValue = 0.5;

    const userInstruction = DOM.systemInstructionInput.value.trim();
    const systemPrompt = userInstruction ? userInstruction : null; // Send raw instruction, no RAG suffix

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
            rerank_threshold_value: rerankThresholdValue
        };

        const data = await API.sendChatRequest(payload);

        UI.removeBubble(loadingId);

        if (data.error) {
            UI.appendAIBubble("Error: " + data.error);
            UI.disableRetryButton(); // Disable retry if an error occurs
        } else {
            UI.appendAIBubble(data.answer, data.sources, useRerank);
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
