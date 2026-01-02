/**
 * Main Search Application
 * Entry point that orchestrates all modules
 */

import { searchConfig, loadBackendConfig } from './config.js';
import * as DOM from './dom.js';
import { performCollectionSearch } from './api.js';
import { showLoading, showError } from './ui.js';
import { renderResults, applyThresholdToResults, toggleResult, toggleIntentDetails, currentResults } from './render.js';

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
    // --- 新增：資料來源篩選 (全選/取消全選邏輯) ---
    const selectAllCheckbox = document.getElementById('selectAllSources');
    // 注意：這裡假設你的 HTML checkbox 有 class="source-item"
    const sourceCheckboxes = document.querySelectorAll('input[name="source_checkbox"]'); 

    if (selectAllCheckbox && sourceCheckboxes.length > 0) {
        // 1. 全選被點擊
        selectAllCheckbox.addEventListener('change', (e) => {
            const isChecked = e.target.checked;
            sourceCheckboxes.forEach(cb => {
                cb.checked = isChecked;
            });
        });

        // 2. 個別選項被點擊 (檢查是否要取消全選勾勾)
        sourceCheckboxes.forEach(cb => {
            cb.addEventListener('change', () => {
                const allChecked = Array.from(sourceCheckboxes).every(item => item.checked);
                selectAllCheckbox.checked = allChecked;
            });
        });
    }
}

/**
 * 新增：取得目前勾選的資料來源列表
 */

function getSelectedSources() {
    const selected = [];
    const sourceCheckboxes = document.querySelectorAll('input[name="source_checkbox"]:checked');
    
    sourceCheckboxes.forEach(cb => {
        selected.push(cb.value);
    });
    
    // 如果什麼都沒選，視同全選 (或是給空陣列，看你後端邏輯)
    return selected;
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
        // 🔥【修改點 1】獲取使用者勾選的網站列表
        const selectedWebsites = getSelectedSources();
        
        // Debug: 在 F12 console 顯示目前勾了哪些，方便你檢查
        console.log('🔍 Active Source Filters:', selectedWebsites);

        // 🔥【修改點 2】將 selectedWebsites 作為第二個參數傳給 API
        // 注意：等一下我們還要去 api.js 修改 performCollectionSearch 來接收這個參數
        const { data, duration } = await performCollectionSearch(query, selectedWebsites);

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

        if (data.summary && data.summary.trim()) {
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
        } else if (data.error) {
            // 後端返回錯誤
            summaryTitle.innerHTML = `摘要生成失敗`;
            summaryContent.innerHTML = `
                <div class="flex items-center gap-2 text-amber-600 dark:text-amber-400">
                    <span class="material-icons-round text-lg">warning</span>
                    <p class="text-sm">AI 服務暫時無法使用，請稍後再試。</p>
                </div>
            `;
        } else {
            // 後端沒返回摘要也沒返回錯誤
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
        // 顯示錯誤訊息而不是隱藏區塊
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

// --- Chatbot Logic (Add to end of search.js) ---

document.addEventListener('DOMContentLoaded', () => {
    setupChatbot();
});

function setupChatbot() {
    const container = document.getElementById('chatbotContainer');
    const triggerBtn = document.getElementById('chatTriggerBtn');
    const clearBtn = document.getElementById('clearChatBtn'); // ★ 新增
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

    // ★ 清除紀錄邏輯
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

        if (!currentResults || currentResults.length === 0) {
            appendMessage('user', text);
            setTimeout(() => {
                appendMessage('bot', '請先在左側搜尋欄輸入關鍵字查詢公告，我才能根據搜尋結果回答您的問題喔！');
                renderSuggestions(["如何搜尋公告？", "Copilot 是什麼？", "搜尋最新價格"]);
            }, 500);
            chatInput.value = '';
            return;
        }

        appendMessage('user', text);
        chatInput.value = '';

        const loadingId = appendLoading();

        try {
            // 1. 取得目前設定的相似度門檻 (預設為 0)
            // 注意：searchConfig.similarityThreshold 通常是 0-100 的整數
            const thresholdPercent = searchConfig.similarityThreshold || 0;
            // 2. 過濾資料：只抓取「未反灰」的結果 (相似度 >= 門檻)
            // 如果你的後端欄位名稱不同 (例如 score, _rankingScore)，請在此調整
            const validResults = currentResults.filter(item => {
            // 這樣能配合 render.js 的邏輯，正確抓到分數
            const score = item._rankingScore ?? item.similarity ?? item.score ?? 0;

            // 將 0-1 的分數轉為 0-100 與門檻比較
            return (score * 100) >= thresholdPercent;
            });
            // 檢查是否全反灰 (也就是 validResults 為空)
            if (validResults.length === 0) {
            // 移除 Loading 動畫
            removeMessage(loadingId);
            
            // 直接回覆使用者，不呼叫後端 API
            appendMessage('bot', `目前的搜尋結果相似度皆低於 **${thresholdPercent}%**，已被全部過濾。請嘗試**調低相似度滑桿**，讓 AI 能參考更多資料。`);
            // 中止函式，不執行後面的 fetch
            return;
            }
            // 3. 如果有資料，就直接使用過濾後的結果 (拿掉原本的保底機制)
            const finalResults = validResults;
            console.log(`Chatbot Context: 使用了 ${finalResults.length} 筆資料 (門檻: ${thresholdPercent}%)`);

            // 4. 組裝 Context (移除 slice 限制，只要符合門檻全都要)
            const currentContext = finalResults.map(item => ({
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