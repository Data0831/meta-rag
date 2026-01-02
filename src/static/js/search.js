/**
 * Main Search Application
 * Entry point that orchestrates all modules
 */

import { searchConfig, loadBackendConfig } from './config.js';
import * as DOM from './dom.js';
import { performSearchStream } from './api.js';
import { showLoading, showError, hideAllStates } from './ui.js';
import { renderResults, applyThresholdToResults, toggleResult, toggleIntentDetails, currentResults } from './render.js';

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    console.log('Collection Search initialized');

    // Load backend configuration
    loadBackendConfig();

    // Setup event listeners
    setupEventListeners();
    setupSearchConfig();
    setupChatbot();
});

/**
 * Setup search configuration UI controls
 */
function setupSearchConfig() {
    // Similarity threshold slider
    const similarityThresholdEl = document.getElementById('similarityThreshold');
    const thresholdValue = document.getElementById('thresholdValue');
    if (similarityThresholdEl && thresholdValue) {
        similarityThresholdEl.addEventListener('input', (e) => {
            const sliderValue = parseInt(e.target.value);
            searchConfig.similarityThreshold = sliderValue;
            thresholdValue.textContent = searchConfig.similarityThreshold + '%';
            // Apply threshold to current results if they exist
            applyThresholdToResults();
        });
    }

    // Semantic ratio slider
    const semanticRatioSlider = document.getElementById('semanticRatioSlider');
    const manualRatioCheckbox = document.getElementById('manualRatioCheckbox');
    const semanticRatioValue = document.getElementById('semanticRatioValue');

    if (semanticRatioSlider && manualRatioCheckbox) {
        // Init state
        semanticRatioSlider.disabled = !manualRatioCheckbox.checked;
        if (!manualRatioCheckbox.checked) {
            if (semanticRatioValue) semanticRatioValue.textContent = "Auto";
        }

        // Checkbox listener
        manualRatioCheckbox.addEventListener('change', (e) => {
            const isManual = e.target.checked;
            searchConfig.manualSemanticRatio = isManual;
            semanticRatioSlider.disabled = !isManual;

            if (isManual) {
                // Restore value from slider
                const val = parseInt(semanticRatioSlider.value);
                searchConfig.semanticRatio = val / 100;
                if (semanticRatioValue) semanticRatioValue.textContent = val + '%';
            } else {
                // Set to Auto display
                if (semanticRatioValue) semanticRatioValue.textContent = "Auto";
            }
        });

        // Slider listener
        semanticRatioSlider.addEventListener('input', (e) => {
            const val = parseInt(e.target.value);
            searchConfig.semanticRatio = val / 100;
            // Update label if it exists
            if (semanticRatioValue) {
                semanticRatioValue.textContent = val + '%';
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
    if (DOM.llmRewriteCheckbox) {
        DOM.llmRewriteCheckbox.addEventListener('change', (e) => {
            searchConfig.enableLlm = e.target.checked;
        });
    }

    // Enable Rerank Checkbox
    const enableKeywordWeightRerankCheckbox = document.getElementById('enableKeywordWeightRerankCheckbox');
    if (enableKeywordWeightRerankCheckbox) {
        enableKeywordWeightRerankCheckbox.addEventListener('change', (e) => {
            searchConfig.enableKeywordWeightRerank = e.target.checked;
        });
    }

    const startDateInput = document.getElementById('startDateInput');
    if (startDateInput) {
        startDateInput.addEventListener('change', (e) => {
            // 客人改了日期，抄進記事本
            searchConfig.startDate = e.target.value;
            console.log('開始日期已更新:', searchConfig.startDate);
        });
    }

    // 2. 抓取結束時間的格子
    const endDateInput = document.getElementById('endDateInput');
    if (endDateInput) {
        endDateInput.addEventListener('change', (e) => {
            // 客人改了日期，抄進記事本
            searchConfig.endDate = e.target.value;
            console.log('結束日期已更新:', searchConfig.endDate);
        });
    }
}

/**
 * Setup event listeners for search triggers
 */
function setupEventListeners() {
    // Search triggers
    DOM.searchIconBtn.addEventListener('click', performSearch);
    DOM.searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            performSearch();
        }
    });
}

/**
 * Convert citation markers [1], [2] etc. to hyperlinks
 */
function convertCitationsToLinks(text, linkMapping) {
    if (!text || !linkMapping) return text;

    return text.replace(/\[(\d+)\]/g, (match, num) => {
        const link = linkMapping[num];
        if (link) {
            return `<a href="${link}" target="_blank" class="citation-link" style="color: #3b82f6; text-decoration: none; font-weight: 600; vertical-align: super; font-size: 0.85em;">${match}</a>`;
        }
        return match;
    });
}

/**
 * Render structured summary with three parts
 */
function renderStructuredSummary(summary, linkMapping) {
    if (typeof summary === 'string') {
        return marked.parse(summary);
    }

    const { brief_answer, detailed_answer, general_summary } = summary;

    const isNoResults = brief_answer === '沒有參考資料' || brief_answer === '從內容 search 不到';

    let html = '';

    // Part 1: Brief Answer (置頂，極簡漸層風格)
    if (brief_answer) {
        const icon = isNoResults ? 'warning' : 'auto_awesome';
        const iconColor = isNoResults ? 'text-amber-500' : 'text-primary';
        const statusClass = isNoResults ? 'warning' : '';

        html += `
            <div class="brief-answer-gradient-bar ${statusClass}">
                <span class="material-icons-round ${iconColor} text-2xl">${icon}</span>
                <span class="brief-answer-text text-slate-800 dark:text-slate-100">${brief_answer}</span>
            </div>
        `;
    }

    // Part 2: Detailed Answer
    if (detailed_answer && detailed_answer.trim()) {
        const detailedParsed = marked.parse(detailed_answer);
        const detailedWithLinks = convertCitationsToLinks(detailedParsed, linkMapping);

        html += `
            <div class="mb-6">
                <h4 class="font-bold text-slate-700 dark:text-slate-300 mb-2">詳細說明</h4>
                <div class="text-slate-600 dark:text-slate-300 leading-relaxed prose prose-sm dark:prose-invert max-w-none">
                    ${detailedWithLinks}
                </div>
            </div>
        `;
    } else if (detailed_answer === '') {
        html += `
            <div class="mb-6">
                <h4 class="font-bold text-slate-700 dark:text-slate-300 mb-2">詳細說明</h4>
                <p class="text-slate-400 dark:text-slate-500 text-sm italic">無詳細內容</p>
            </div>
        `;
    }

    // Part 3: General Summary
    if (general_summary && general_summary.trim()) {
        const summaryParsed = marked.parse(general_summary);
        const summaryWithLinks = convertCitationsToLinks(summaryParsed, linkMapping);

        html += `
            <div class="mb-4">
                <h4 class="font-bold text-slate-700 dark:text-slate-300 mb-2">內容總結</h4>
                <div class="text-slate-600 dark:text-slate-300 leading-relaxed prose prose-sm dark:prose-invert max-w-none">
                    ${summaryWithLinks}
                </div>
            </div>
        `;

        // Add list styling
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = html;
        const ul = tempDiv.querySelector('ul');
        if (ul) ul.classList.add('list-disc', 'pl-5', 'space-y-1');
        html = tempDiv.innerHTML;
    } else if (general_summary === '') {
        html += `
            <div class="mb-4">
                <h4 class="font-bold text-slate-700 dark:text-slate-300 mb-2">內容總結</h4>
                <p class="text-slate-400 dark:text-slate-500 text-sm italic">無總結內容</p>
            </div>
        `;
    }

    return html;
}

/**
 * Perform search operation with streaming handling
 */
async function performSearch() {
    const query = DOM.searchInput.value.trim();

    if (!query) {
        console.warn('⚠️ Empty query');
        showError('請輸入搜尋查詢');
        return;
    }

    // Reset UI states
    hideAllStates();

    // Use summary container for status updates instead of generic loading dots
    const summaryContainer = document.getElementById('summaryContainer');
    const summaryContent = document.getElementById('summaryContent');
    const summaryTitle = document.getElementById('summaryTitle');

    // 1. 先取得當前的門檻值
    const threshold = searchConfig.similarityThreshold || 0;

    // 2. 篩選出高於或等於門檻的文章 (與 render.js 邏輯同步)
    const validResults = (results || []).filter(item => {
        const score = Math.round((item._rankingScore || 0) * 100);
        return score >= threshold;
    });

    // 3. 如果沒有任何合格的文章，則隱藏摘要區塊並結束
    if (validResults.length === 0) {
        summaryContainer.classList.add('hidden');
        return;
    }

    if (summaryContainer) {
        summaryContainer.classList.remove('hidden');
        summaryTitle.innerHTML = `<span class="material-icons-round animate-pulse mr-2 align-middle text-primary">manage_search</span>正在初始化搜尋...`;

    // 顯示 Loading 動畫 (Skeleton)
    summaryContent.innerHTML = `
        <div class="animate-pulse space-y-3">
            <div class="h-2 bg-slate-200 dark:bg-slate-700 rounded w-3/4"></div>
            <div class="h-2 bg-slate-200 dark:bg-slate-700 rounded w-full"></div>
            <div class="h-2 bg-slate-200 dark:bg-slate-700 rounded w-5/6"></div>
        </div>
    `;

    try {
        // 準備要傳給後端的資料 (只取合格的前 5 筆)
        const topResults = validResults.slice(0, 5).map(item => ({
            title: item.title,
            content: item.content || item.cleaned_content
        }));

        // 呼叫後端 API
        const response = await fetch('/api/summary', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                query: query,
                results: topResults
            })
        });

        const data = await response.json();

        if (data.summary && data.summary.trim()) {
            // 更新標題
            summaryTitle.innerHTML = `以下為「<span class="text-primary">${query}</span>」的相關公告總結：`;

            // 渲染 Markdown 內容
            summaryContent.innerHTML = marked.parse(data.summary);

            // 讓列表樣式更好看 (Tailwind Typography)
            const ul = summaryContent.querySelector('ul');
            if (ul) {
                ul.classList.add('list-disc', 'pl-5', 'space-y-1');
            }
        } else if (data.error) {
            summaryTitle.innerHTML = `摘要生成失敗`;
            summaryContent.innerHTML = `
                <div class="flex items-center gap-2 text-amber-600 dark:text-amber-400">
                    <span class="material-icons-round text-lg">warning</span>
                    <p class="text-sm">AI 服務暫時無法使用，請稍後再試。</p>
                </div>
            `;
        } else {
            summaryTitle.innerHTML = `摘要生成失敗`;
            summaryContent.innerHTML = `
                <div class="flex items-center gap-2 text-slate-500 dark:text-slate-400">
                    <span class="material-icons-round text-lg">info</span>
                    <p class="text-sm">無法生成摘要，請稍後再試。</p>
                </div>
            `;
        }

    } catch (error) {
        console.error("摘要生成失敗:", error);
        summaryTitle.innerHTML = `摘要生成失敗`;
        summaryContent.innerHTML = `
            <div class="flex items-center gap-2 text-red-600 dark:text-red-400">
                <span class="material-icons-round text-lg">error</span>
                <p class="text-sm">網路連線錯誤，請檢查後端服務是否正常運行。</p>
            </div>
        `;
    }
}

function hideSummary() {
    const summaryContainer = document.getElementById('summaryContainer');
    if (summaryContainer) summaryContainer.classList.add('hidden');
}

/**
 * Expose toggleResult and toggleIntentDetails to global scope for onclick handlers in HTML
 */
window.toggleResult = toggleResult;
window.toggleIntentDetails = toggleIntentDetails;

// --- Chatbot Logic ---

function setupChatbot() {
    const container = document.getElementById('chatbotContainer');
    const triggerBtn = document.getElementById('chatTriggerBtn');
    const clearBtn = document.getElementById('clearChatBtn');
    const iconArrow = document.getElementById('chatIconArrow');
    const chatInput = document.getElementById('chatInput');
    const sendBtn = document.getElementById('sendChatBtn');
    const messagesDiv = document.getElementById('chatMessages');

    if (!container || !triggerBtn) return;

    // 建立建議問題容器
    const inputArea = chatInput.parentElement.parentElement;
    let suggestionsContainer = document.getElementById('chatSuggestions');
    if (!suggestionsContainer) {
        suggestionsContainer = document.createElement('div');
        suggestionsContainer.id = 'chatSuggestions';
        suggestionsContainer.className = 'px-4 pb-2 flex flex-wrap gap-2 justify-end';
        inputArea.insertBefore(suggestionsContainer, inputArea.firstChild);
    }

    let isOpen = false;
    let chatHistory = [];

    // 初始化
    fetchInitialSuggestions();

    async function fetchInitialSuggestions() {
        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: "", context: [], history: [] })
            });
            const data = await response.json();
            if (data.suggestions && data.suggestions.length > 0) {
                renderSuggestions(data.suggestions);
            }
        } catch (e) {
            console.error("無法載入初始建議", e);
            renderSuggestions(["介紹一下你自己", "最近有什麼重大公告？", "Copilot 價格是多少？"]);
        }
    }

    function renderSuggestions(list) {
        suggestionsContainer.innerHTML = '';
        if (!list || list.length === 0) return;

        list.forEach(text => {
            const btn = document.createElement('button');
            btn.textContent = text;
            btn.className = `
                text-xs px-3 py-1.5 rounded-full border border-slate-300 dark:border-slate-600 
                bg-white dark:bg-slate-700 text-slate-600 dark:text-slate-300 
                hover:bg-slate-100 dark:hover:bg-slate-600 hover:text-primary dark:hover:text-primary
                transition-colors cursor-pointer whitespace-nowrap shadow-sm animate-fade-in-up
            `;
            btn.addEventListener('click', () => {
                chatInput.value = text;
                sendMessage();
            });
            suggestionsContainer.appendChild(btn);
        });
    }

    if (clearBtn) {
        clearBtn.addEventListener('click', () => {
            chatHistory = []; // 清空記憶
            messagesDiv.innerHTML = ''; // 清空畫面

            // 補回歡迎詞
            const welcomeDiv = document.createElement('div');
            welcomeDiv.className = 'flex items-start gap-2 animate-fade-in-up';
            welcomeDiv.innerHTML = `
                <div class="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-white flex-shrink-0">
                    <span class="material-icons-round text-sm">smart_toy</span>
                </div>
                <div class="bg-white dark:bg-slate-700 p-3 rounded-2xl rounded-tl-none shadow-sm text-sm text-slate-700 dark:text-slate-200 border border-slate-100 dark:border-slate-600">
                    您好！我是您的搜尋助手。關於目前的搜尋結果或 Microsoft 合作夥伴計畫，有什麼想問的嗎？
                </div>
            `;
            messagesDiv.appendChild(welcomeDiv);

            // 重置建議
            fetchInitialSuggestions();
        });
    }

    function toggleChat() {
        isOpen = !isOpen;
        if (isOpen) {
            container.classList.remove('translate-x-[calc(100%-4rem)]');
            container.classList.add('translate-x-0');
            iconArrow.textContent = 'chevron_right';
        } else {
            container.classList.add('translate-x-[calc(100%-4rem)]');
            container.classList.remove('translate-x-0');
            iconArrow.textContent = 'chevron_left';
        }
    }

    triggerBtn.addEventListener('click', toggleChat);

    async function sendMessage() {
        const text = chatInput.value.trim();
        if (!text) return;

        suggestionsContainer.innerHTML = '';

        // --- 第一層檢查：完全沒有搜尋結果的情況 (原始邏輯) ---
        if (!currentResults || currentResults.length === 0) {
            appendMessage('user', text);
            setTimeout(() => {
                appendMessage('bot', '請先在左側搜尋欄輸入關鍵字查詢公告，我才能根據搜尋結果回答您的問題喔！');
                renderSuggestions(["如何搜尋公告？", "Copilot 是什麼？", "搜尋最新價格"]);
            }, 500);
            chatInput.value = '';
            return;
        }

        // --- 第二層檢查：有搜尋結果，但根據相似度門檻篩選合格文章 ---
        const threshold = searchConfig.similarityThreshold || 0;
        
        // 根據 render.js 邏輯，使用 Math.round((_rankingScore || 0) * 100) 取得整數分數
        const validResults = currentResults.filter(item => {
            const score = Math.round((item._rankingScore || 0) * 100);
            return score >= threshold;
        });

        // 如果過濾後沒有任何合格的文章
        if (validResults.length === 0) {
            appendMessage('user', text);
            setTimeout(() => {
                appendMessage('bot', `抱歉，目前的搜尋結果相似度皆低於您的門檻 (${threshold}%)，我無法從中獲取準確資訊。請嘗試調低相似度門檻或變更關鍵字。`);
                renderSuggestions(["調低相似度門檻", "重新搜尋"]);
            }, 500);
            chatInput.value = '';
            return;
        }

        // --- 通過檢查，開始發送請求 ---
        appendMessage('user', text);
        chatInput.value = '';

        const loadingId = appendLoading();

        try {
            // 取前 5 筆「合格」的資料作為 Context 傳給 AI
            const currentContext = validResults.slice(0, 5).map(item => ({
                title: item.title,
                content: item.content || item.cleaned_content,
                link: item.link,
                year_month: item.year_month
            }));

            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: text,
                    context: currentContext,
                    history: chatHistory
                })
            });

            const data = await response.json();
            removeMessage(loadingId);

            if (data.error) {
                appendMessage('bot', '系統錯誤：' + data.error);
            } else {
                appendMessage('bot', data.answer);

                if (data.suggestions && data.suggestions.length > 0) {
                    renderSuggestions(data.suggestions);
                }

                chatHistory.push({ role: 'user', content: text });
                chatHistory.push({ role: 'model', content: data.answer });

                if (chatHistory.length > 10) chatHistory = chatHistory.slice(-10);
            }

        } catch (error) {
            removeMessage(loadingId);
            appendMessage('bot', '網路連線錯誤，請檢查後端是否啟動。');
            console.error(error);
        }
    }

    sendBtn.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });

    function appendMessage(role, text) {
        const div = document.createElement('div');
        const isBot = role === 'bot';

        div.className = `flex flex-col gap-1 animate-fade-in-up ${isBot ? 'items-start' : 'items-end'}`;
        const icon = isBot ? 'smart_toy' : 'person';
        const bgClass = isBot ? 'bg-white dark:bg-slate-700 text-slate-700 dark:text-slate-200' : 'bg-primary text-white';
        const iconBg = isBot ? 'bg-primary' : 'bg-slate-400';
        const roundedClass = isBot ? 'rounded-tl-none' : 'rounded-tr-none';

        let messageContent = '';
        if (isBot) {
            messageContent = `<div class="prose prose-sm dark:prose-invert max-w-none leading-relaxed">
                                ${marked.parse(text)}
                              </div>`;
        } else {
            messageContent = text.replace(/\n/g, '<br>');
        }

        div.innerHTML = `
            <div class="flex items-start gap-2 ${isBot ? '' : 'flex-row-reverse'}">
                <div class="w-8 h-8 rounded-full ${iconBg} flex items-center justify-center text-white flex-shrink-0">
                    <span class="material-icons-round text-sm">${icon}</span>
                </div>
                <div class="${bgClass} p-3 rounded-2xl ${roundedClass} shadow-sm text-sm border border-slate-100 dark:border-slate-600 max-w-[90%] overflow-hidden">
                    ${messageContent}
                </div>
            </div>
        `;
        messagesDiv.appendChild(div);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
        return div.id;
    }

    function appendLoading() {
        const id = 'msg-' + Date.now();
        const div = document.createElement('div');
        div.id = id;
        div.className = 'flex items-start gap-2';
        div.innerHTML = `
             <div class="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-white flex-shrink-0">
                <span class="material-icons-round text-sm">smart_toy</span>
            </div>
            <div class="bg-white dark:bg-slate-700 p-4 rounded-2xl rounded-tl-none shadow-sm border border-slate-100 dark:border-slate-600">
                 <div class="flex space-x-1">
                    <div class="w-2 h-2 bg-slate-400 rounded-full animate-bounce"></div>
                    <div class="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style="animation-delay: 0.1s"></div>
                    <div class="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style="animation-delay: 0.2s"></div>
                </div>
            </div>
        `;
        messagesDiv.appendChild(div);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
        return id;
    }

    function removeMessage(id) {
        const el = document.getElementById(id);
        if (el) el.remove();
    }
}
