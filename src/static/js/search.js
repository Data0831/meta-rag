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
 * Show alert notification with auto-dismiss
 */
function showAlert(message, iconName = 'info') {
    const alertNotification = document.getElementById('alertNotification');
    const alertBox = document.getElementById('alertBox');
    const alertMessage = document.getElementById('alertMessage');
    const alertIcon = document.getElementById('alertIcon');

    if (!alertNotification || !alertBox || !alertMessage || !alertIcon) return;

    // Set content
    alertMessage.textContent = message;
    alertIcon.textContent = iconName;

    // Show with animation
    alertNotification.classList.remove('pointer-events-none');
    setTimeout(() => {
        alertBox.classList.remove('opacity-0', 'translate-y-[-20px]', 'scale-95');
        alertBox.classList.add('opacity-100', 'translate-y-0', 'scale-100');
    }, 10);

    // Auto dismiss after 3 seconds
    setTimeout(() => {
        alertBox.classList.remove('opacity-100', 'translate-y-0', 'scale-100');
        alertBox.classList.add('opacity-0', 'translate-y-[-20px]', 'scale-95');
        setTimeout(() => {
            alertNotification.classList.add('pointer-events-none');
        }, 300);
    }, 3000);
}

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
            let value = parseInt(e.target.value);
            const maxLimit = searchConfig.maxLimit;
            let corrected = false;
            let correctedValue = value;

            if (isNaN(value) || value < 1) {
                correctedValue = 1;
                corrected = true;
            } else if (value > maxLimit) {
                correctedValue = maxLimit;
                corrected = true;
            }

            if (corrected) {
                e.target.value = correctedValue;
                searchConfig.limit = correctedValue;
                showAlert(`您輸入的數量超出範圍，已自動調整為 ${correctedValue}`, 'warning');
            } else {
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

    // 🔥【修改點 1】獲取使用者勾選的網站列表
    const selectedWebsites = getSelectedSources();

    // Debug: 在 F12 console 顯示目前勾了哪些，方便你檢查
    console.log('Active Source Filters:', selectedWebsites);

    // 🔥【修改點 2】將 selectedWebsites 作為第二個參數傳給 API
    // 注意：等一下我們還要去 api.js 修改 performCollectionSearch 來接收這個參數
    const { data, duration } = await performCollectionSearch(query, selectedWebsites);

    // Reset UI states
    hideAllStates();

    // Use summary container for status updates instead of generic loading dots
    const summaryContainer = document.getElementById('summaryContainer');
    const summaryContent = document.getElementById('summaryContent');
    const summaryTitle = document.getElementById('summaryTitle');
    const searchTimeValue = document.getElementById('searchTimeValue');

    if (summaryContainer) {
        summaryContainer.classList.remove('hidden');
        summaryTitle.innerHTML = `<span class="material-icons-round animate-pulse mr-2 align-middle text-primary">manage_search</span>正在初始化搜尋...`;

        // Show Skeleton in content area while working
        summaryContent.innerHTML = `
            <div class="animate-pulse space-y-3">
                <div class="h-2 bg-slate-200 dark:bg-slate-700 rounded w-3/4"></div>
                <div class="h-2 bg-slate-200 dark:bg-slate-700 rounded w-full"></div>
                <div class="h-2 bg-slate-200 dark:bg-slate-700 rounded w-5/6"></div>
            </div>
        `;
    } else {
        // Fallback if summary container missing
        showLoading();
    }

    // Record start time
    const totalStartTime = performance.now();
    let hasUpdatedResults = false;

    try {
        // Initiate Stream
        const response = await performSearchStream(query);

        if (!response.body) throw new Error("ReadableStream not supported");

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop(); // Keep incomplete line

            for (const line of lines) {
                if (!line.trim()) continue;

                try {
                    const data = JSON.parse(line);
                    console.log('Agent Stream:', data.status, data); // ★ 修改為印出完整 data

                    // Handle Status Updates
                    if (data.status === "failed") {
                        // Display error in summary container based on error stage
                        let errorTitle = "搜尋失敗";
                        const errorStage = data.error_stage || data.stage || "unknown";

                        switch (errorStage) {
                            case "meilisearch":
                                errorTitle = "資料庫連線失敗";
                                break;
                            case "embedding":
                                errorTitle = "向量服務失敗";
                                break;
                            case "llm":
                                errorTitle = "語言模型服務失敗";
                                break;
                            case "intent_parsing":
                                errorTitle = "意圖解析失敗";
                                break;
                            case "initial_search":
                                errorTitle = "初始搜尋失敗";
                                break;
                            case "summarizing":
                                errorTitle = "摘要生成失敗";
                                break;
                            default:
                                errorTitle = "搜尋過程發生錯誤";
                        }

                        if (summaryContainer) {
                            summaryTitle.innerHTML = `<span class="material-icons-round mr-2 align-middle text-red-500">error</span>${errorTitle}`;
                            summaryContent.innerHTML = `
                                <div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
                                    <div class="text-red-800 dark:text-red-200 font-mono text-sm whitespace-pre-wrap break-words">${data.error || "Unknown error"}</div>
                                </div>
                            `;
                        }
                        return; // Stop processing stream
                    }

                    if (data.stage === "searching") {
                        summaryTitle.innerHTML = `<span class="material-icons-round animate-spin mr-2 align-middle text-primary">sync</span>${data.message}`;
                        // Blur time if needed
                        if (searchTimeValue) {
                            searchTimeValue.style.filter = 'blur(3px)';
                            searchTimeValue.style.opacity = '0.5';
                        }
                    } else if (data.stage === "checking") {
                        summaryTitle.innerHTML = `<span class="material-icons-round animate-pulse mr-2 align-middle text-secondary">fact_check</span>${data.message}`;
                    } else if (data.stage === "rewriting") {
                        summaryTitle.innerHTML = `<span class="material-icons-round animate-pulse mr-2 align-middle text-amber-500">edit_note</span>${data.message}`;
                    } else if (data.stage === "retrying") {
                        summaryTitle.innerHTML = `<span class="material-icons-round animate-spin mr-2 align-middle text-amber-500">sync_problem</span>${data.message}`;
                    } else if (data.stage === "summarizing") {
                        summaryTitle.innerHTML = `<span class="material-icons-round animate-pulse mr-2 align-middle text-primary">auto_awesome</span>${data.message}`;
                    } else if (data.stage === "complete") {
                        // Finalize
                        const totalEndTime = performance.now();
                        const totalDuration = Math.round(totalEndTime - totalStartTime);

                        if (searchTimeValue) {
                            searchTimeValue.textContent = totalDuration;
                            searchTimeValue.style.filter = 'none';
                            searchTimeValue.style.opacity = '1';
                        }

                        // Update Title
                        summaryTitle.innerHTML = `以下為「<span class="text-primary">${query}</span>」的相關公告總結：`;

                        // Render Structured Summary
                        if (data.summary) {
                            summaryContent.innerHTML = renderStructuredSummary(data.summary, data.link_mapping || {});
                        } else {
                            summaryContent.innerHTML = "<p>無相關總結。</p>";
                        }

                        // Render Results
                        if (data.results && data.results.length > 0) {
                            const renderData = {
                                results: data.results,
                                intent: data.intent || null,
                            };

                            // Calculate duration for display (using total time)
                            renderResults(renderData, totalDuration, query);
                        } else {
                            // No results found
                            if (DOM.resultsContainer) DOM.resultsContainer.classList.add('hidden');
                            // Maybe show empty state if summary is also empty?
                            if (!data.summary) {
                                showError("未找到相關結果");
                            }
                        }
                    }

                    // Handle intermediate results if available (optional, dependent on agent implementation)
                    if (data.new_query) {
                        // Just an update, handled by stage message
                    }

                } catch (e) {
                    console.error("Error parsing stream line:", e, line);
                }
            }
        }

    } catch (error) {
        console.error('Search failed:', error);
        showError(error.message);
        if (summaryContainer) summaryContainer.classList.add('hidden');
    }
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
