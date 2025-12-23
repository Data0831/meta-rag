/**
 * Main Search Application
 * Entry point that orchestrates all modules
 */

import { searchConfig, loadBackendConfig } from './config.js';
import * as DOM from './dom.js';
import { performCollectionSearch } from './api.js';
import { showLoading, showError } from './ui.js';
import { renderResults, applyThresholdToResults, toggleResult, currentResults } from './render.js';

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Collection Search initialized');

    // Load backend configuration
    loadBackendConfig();

    // Setup event listeners
    setupEventListeners();
    setupSearchConfig();
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
    if (DOM.llmRewriteCheckbox) {
        DOM.llmRewriteCheckbox.addEventListener('change', (e) => {
            searchConfig.enableLlm = e.target.checked;
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
 * Perform search operation
 */
async function performSearch() {
    const query = DOM.searchInput.value.trim();

    if (!query) {
        console.warn('⚠️ Empty query');
        showError('請輸入搜尋查詢');
        return;
    }

    showLoading();

    // 每次新搜尋前，先隱藏摘要區塊 (避免看到上次的殘留)
    hideSummary();

    try {
        // 發送搜尋請求
        const { data, duration } = await performCollectionSearch(query);

        // Log filters if LLM rewrite is enabled
        if (searchConfig.enableLlm) {
            console.group('LLM Query Rewrite');
            console.log('Filters (JSON):', data.intent?.filters);
            if (data.meili_filter) {
                console.log('Meilisearch Expression:', data.meili_filter);
            }
            console.groupEnd();
        }

        // 1. 渲染搜尋列表 (只要成功拿到資料就渲染)
        renderResults(data, duration, query, searchConfig);

        // 2. ★★★ 觸發摘要生成 (移到這裡，確保 data 讀取得到) ★★★
        if (data.results && data.results.length > 0) {
            // 有搜尋結果才做摘要
            generateSearchSummary(query, data.results);
        } else {
            // 沒結果就隱藏摘要區塊
            hideSummary();
        }

    } catch (error) {
        console.error('Search failed:', error);
        console.error('  Error message:', error.message);
        showError(error.message);
        // 發生錯誤時也要隱藏摘要
        hideSummary();
    }
}

async function generateSearchSummary(query, results) {
    const summaryContainer = document.getElementById('summaryContainer');
    const summaryContent = document.getElementById('summaryContent');
    const summaryTitle = document.getElementById('summaryTitle');

    // 初始化 UI：顯示容器，並顯示 Loading 狀態
    summaryContainer.classList.remove('hidden');
    summaryTitle.innerHTML = `正在為您總結「<span class="text-primary">${query}</span>」的相關公告...`;

    // 顯示 Loading 動畫 (Skeleton)
    summaryContent.innerHTML = `
        <div class="animate-pulse space-y-3">
            <div class="h-2 bg-slate-200 dark:bg-slate-700 rounded w-3/4"></div>
            <div class="h-2 bg-slate-200 dark:bg-slate-700 rounded w-full"></div>
            <div class="h-2 bg-slate-200 dark:bg-slate-700 rounded w-5/6"></div>
        </div>
    `;

    try {
        // 準備要傳給後端的資料 (只傳前 5 筆 ID 或內容，減少傳輸量)
        const topResults = results.slice(0, 5).map(item => ({
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

        if (data.summary) {
            // 更新標題
            summaryTitle.innerHTML = `以下為「<span class="text-primary">${query}</span>」的相關公告總結：`;

            // 渲染 Markdown 內容
            // 使用 marked.parse 來解析後端回傳的 Markdown 列表
            summaryContent.innerHTML = marked.parse(data.summary);

            // 讓列表樣式更好看 (Tailwind Typography)
            // 確保 summaryContent 外層或本身有 prose class，或手動調整 CSS
            const ul = summaryContent.querySelector('ul');
            if (ul) {
                ul.classList.add('list-disc', 'pl-5', 'space-y-1');
            }
        } else {
            // 如果後端沒吐出摘要，就隱藏區塊
            hideSummary();
        }

    } catch (error) {
        console.error("摘要生成失敗:", error);
        // 失敗時隱藏區塊，不要顯示錯誤訊息給使用者看，以免干擾體驗
        hideSummary();
    }
}

function hideSummary() {
    const summaryContainer = document.getElementById('summaryContainer');
    if (summaryContainer) summaryContainer.classList.add('hidden');
}

/**
 * Expose toggleResult to global scope for onclick handlers in HTML
 */
window.toggleResult = toggleResult;

// --- Chatbot Logic (Add to end of search.js) ---

document.addEventListener('DOMContentLoaded', () => {
    setupChatbot();
});

function setupChatbot() {
    const container = document.getElementById('chatbotContainer');
    const triggerBtn = document.getElementById('chatTriggerBtn');
    const closeBtn = document.getElementById('closeChatBtn');
    const iconArrow = document.getElementById('chatIconArrow');
    const chatInput = document.getElementById('chatInput');
    const sendBtn = document.getElementById('sendChatBtn');
    const messagesDiv = document.getElementById('chatMessages');

    if (!container || !triggerBtn) return;

    let isOpen = false;
    let chatHistory = []; // ★★★ 這裡是用來存歷史紀錄的 ★★★

    // 1. 開關側邊欄
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
    closeBtn.addEventListener('click', () => {
        if (isOpen) toggleChat();
    });

    // 2. 發送訊息邏輯 (真實 API 版本)
    async function sendMessage() {
        const text = chatInput.value.trim();
        if (!text) return;

        // 檢查是否有搜尋結果
        if (!currentResults || currentResults.length === 0) {
            appendMessage('user', text);
            setTimeout(() => {
                appendMessage('bot', '請先在左側搜尋欄輸入關鍵字查詢公告，我才能根據搜尋結果回答您的問題喔！');
            }, 500);
            chatInput.value = '';
            return;
        }

        // 顯示使用者訊息
        appendMessage('user', text);
        chatInput.value = '';

        const loadingId = appendLoading();

        try {
            // 準備目前的 Context (取前 5 筆搜尋結果)
            const currentContext = currentResults.slice(0, 5).map(item => ({
                title: item.title,
                content: item.content || item.cleaned_content,
                link: item.link,
                year_month: item.year_month

            }));

            // ★★★ 這裡是用 fetch 呼叫後端，不再是 setTimeout 了 ★★★
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: text,
                    context: currentContext,
                    history: chatHistory // 傳送歷史紀錄
                })
            });

            const data = await response.json();

            removeMessage(loadingId);

            if (data.error) {
                appendMessage('bot', '系統錯誤：' + data.error);
            } else {
                appendMessage('bot', data.answer);

                // 成功後，更新歷史紀錄
                chatHistory.push({ role: 'user', content: text });
                chatHistory.push({ role: 'model', content: data.answer });

                // 限制長度避免太多
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

    // 輔助函式：新增訊息
    function appendMessage(role, text) {
        const div = document.createElement('div');
        const isBot = role === 'bot';

        // 增加 'items-end' 讓 User 靠右時更整齊
        div.className = `flex flex-col gap-1 animate-fade-in-up ${isBot ? 'items-start' : 'items-end'}`;

        const icon = isBot ? 'smart_toy' : 'person';
        const bgClass = isBot ? 'bg-white dark:bg-slate-700 text-slate-700 dark:text-slate-200' : 'bg-primary text-white';
        const iconBg = isBot ? 'bg-primary' : 'bg-slate-400';
        const roundedClass = isBot ? 'rounded-tl-none' : 'rounded-tr-none';

        // ★★★ 修改重點：引入 Markdown 解析 ★★★
        // 1. 如果是 Bot 回覆，使用 marked.parse() 來渲染 HTML
        // 2. 加入 'prose' class 讓列表和粗體樣式生效
        let messageContent = '';
        if (isBot) {
            // 使用 marked.parse 解析 Markdown (前提是你的 HTML head 裡有引入 marked.js，我看你的 index.html 有)
            // prose, prose-sm 是 Tailwind Typography 的樣式，讓列表有圓點
            messageContent = `<div class="prose prose-sm dark:prose-invert max-w-none leading-relaxed">
                                ${marked.parse(text)}
                              </div>`;
        } else {
            // 使用者訊息維持原樣 (只換行)
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

    // 輔助函式：載入動畫
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