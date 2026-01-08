import { currentResults, activeResults, applyThresholdToResults } from './render.js';
import { searchConfig, appConfig } from './config.js';
import { showAlert } from './alert.js';

let currentTokenUsage = null;

function estimateTokens(text) {
    if (!text) return 0;
    const chineseChars = (text.match(/[\u4e00-\u9fa5]/g) || []).length;
    const otherChars = text.length - chineseChars;
    return Math.ceil(chineseChars * 2.5 + otherChars / 4);
}

export function setupChatbot() {
    const container = document.getElementById('chatbotContainer');
    const triggerBtn = document.getElementById('chatTriggerBtn');
    const clearBtn = document.getElementById('clearChatBtn');
    const iconArrow = document.getElementById('chatIconArrow');
    const chatInput = document.getElementById('chatInput');
    const sendBtn = document.getElementById('sendChatBtn');
    const messagesDiv = document.getElementById('chatMessages');
    const headerStatus = document.getElementById('chatHeaderStatus');

    if (!container || !triggerBtn) return;

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

    const chatCharCount = document.getElementById('chatCharCount');
    if (chatCharCount && chatInput) {
        chatInput.addEventListener('input', () => {
            const currentLength = chatInput.value.length;
            const maxLength = appConfig.maxChatInputLength;

            chatCharCount.textContent = `${currentLength}/${maxLength}`;

            if (currentLength > maxLength) {
                chatCharCount.classList.add('text-red-500', 'font-bold');
                chatCharCount.classList.remove('text-slate-400', 'dark:text-slate-500');
            } else {
                chatCharCount.classList.remove('text-red-500', 'font-bold');
                chatCharCount.classList.add('text-slate-400', 'dark:text-slate-500');
            }
        });
    }

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
            chatHistory = [];
            messagesDiv.innerHTML = '';
            currentTokenUsage = null;

            if (suggestionsContainer) suggestionsContainer.innerHTML = '';
            if (headerStatus) headerStatus.innerHTML = '';

            const welcomeDiv = document.createElement('div');
            welcomeDiv.className = 'flex items-start gap-2 animate-fade-in-up';
            welcomeDiv.innerHTML = `
                <div class="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-white flex-shrink-0">
                    <span class="material-icons-round text-sm">smart_toy</span>
                </div>
                <div class="bg-white dark:bg-slate-700 p-3 rounded-2xl rounded-tl-none shadow-sm text-sm text-slate-700 dark:text-slate-200 border border-slate-100 dark:border-slate-600">
                    您好！我是您的搜尋助手。關於目前的搜尋結果，有什麼想問的嗎？
                </div>
            `;
            messagesDiv.appendChild(welcomeDiv);

            updateHeaderStatus();
        });
    }

    function toggleChat() {
        isOpen = !isOpen;
        if (isOpen) {
            container.classList.remove('translate-x-[calc(100%-4rem)]');
            container.classList.add('translate-x-0');
            iconArrow.textContent = 'chevron_right';
            updateHeaderStatus();
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

        if (text.length > appConfig.maxChatInputLength) {
            showAlert(`訊息字數超過 ${appConfig.maxChatInputLength} 字限制，請縮短內容`, 'warning');
            return;
        }

        const validResults = (activeResults && activeResults.length > 0) ? activeResults : currentResults || [];
        let estimatedContextTokens = 0;
        validResults.forEach(item => {
            const content = item.content || item.cleaned_content || item.body || "";
            estimatedContextTokens += estimateTokens(content);
        });

        const historyTokens = chatHistory.reduce((sum, msg) => {
            return sum + estimateTokens(msg.content || "");
        }, 0);
        const userTokens = estimateTokens(text);

        const estimatedTotal = estimatedContextTokens + historyTokens + userTokens;
        const tokenLimit = appConfig.llmTokenLimit;

        if (estimatedTotal > tokenLimit) {
            showAlert(`預估 Token 使用量 (${estimatedTotal.toLocaleString()}) 超過限制 (${tokenLimit.toLocaleString()})，請清除對話歷史或降低相似度閾值`, 'warning');
            return;
        }

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
            const thresholdPercent = searchConfig.similarityThreshold || 0;
            const isAnyDimmed = document.querySelector('.dimmed-result');
            const validResults = (activeResults && activeResults.length > 0)
                ? activeResults
                : (isAnyDimmed ? [] : currentResults);

            // 1. 取得原始搜尋到的總篇數 (用於顯示 "參考前 ? 篇")
            const totalScanned = currentResults.length;
            if (validResults.length === 0) {
                removeMessage(loadingId);

                // [修改] 這裡換成你截圖中要求的 "未符合" 提示文字
                appendMessage('bot', `機器人提示：發現資料並未符合相似度，參考前 ${totalScanned} 篇，如果要參考更多篇請調低 相似閾值`);
                return;
            }
            // [新增] 這裡插入你截圖中要求的 "已載入" 提示文字
            const validCount = validResults.length;
            // appendMessage('bot', `機器人提示：目前已載入 no.1 - ${validCount} 總共 ${validCount} 篇，已隨著 SIMILAR 動態變化。`);

            const finalResults = validResults;
            console.log(`Chatbot Context: 使用了 ${finalResults.length} 筆資料 (門檻: ${thresholdPercent}%)`);

            const currentContext = finalResults.map(item => {
                // 1. 先做運算邏輯
                const originalIndex = currentResults.indexOf(item);
                const rank = originalIndex + 1;

                // 2. 再明確 return 物件
                return {
                    // 把編號直接寫進 title 裡
                    title: `[No.${rank}] ${item.title}`,

                    // 確保內容不為空
                    content: item.content || item.cleaned_content || item.body || item.text || "",
                    link: item.link,
                    year_month: item.year_month
                };
            });

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
                if (data.error.includes("Input length exceeds")) {
                    appendMessage('bot', '**輸入的字數過多**，請精簡您的問題後再試一次。');
                } else if (data.error.includes("Token 使用量")) {
                    appendMessage('bot', `**Token 超限錯誤**\n\n${data.error}`);
                    if (data.suggestions && data.suggestions.length > 0) {
                        renderSuggestions(data.suggestions);
                    }
                } else {
                    appendMessage('bot', '系統錯誤：' + data.error);
                }

                if (data.token_usage) {
                    currentTokenUsage = data.token_usage;
                    updateHeaderStatus();
                }
            } else {
                appendMessage('bot', data.answer);

                if (data.suggestions && data.suggestions.length > 0) {
                    renderSuggestions(data.suggestions);
                }

                chatHistory.push({ role: 'user', content: text });
                chatHistory.push({ role: 'model', content: data.answer });

                if (chatHistory.length > 10) chatHistory = chatHistory.slice(-10);

                if (data.token_usage) {
                    currentTokenUsage = data.token_usage;
                    updateHeaderStatus();
                }
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

    function updateHeaderStatus() {
        if (!headerStatus) return;

        const sliderEl = document.getElementById('similarity-slider') || document.querySelector('input[type="range"]');
        let thresholdPercent = searchConfig.similarityThreshold || 0;

        if (sliderEl) {
            thresholdPercent = parseInt(sliderEl.value);
        }

        if (!currentResults || currentResults.length === 0) {
            headerStatus.innerHTML = `
                <div class="inline-flex items-center gap-1.5 px-2 py-1 rounded-md bg-primary/20 border border-primary/40">
                    <span class="material-icons-round text-white text-base">smart_toy</span>
                    <span class="text-base text-white font-bold">問答機器人</span>
                </div>
            `;
            return;
        }

        const totalScanned = currentResults.length;

        const validResults = currentResults.filter(item => {
            const rawScore = item._rerank_score !== undefined ? item._rerank_score : (item._rankingScore || 0);
            const scorePercent = Math.round(rawScore * 100);
            return scorePercent >= thresholdPercent;
        });
        const validCount = validResults.length;

        let estimatedContextTokens = 0;
        validResults.forEach(item => {
            const content = item.content || item.cleaned_content || item.body || "";
            estimatedContextTokens += estimateTokens(content);
        });

        const historyTokens = chatHistory.reduce((sum, msg) => {
            return sum + estimateTokens(msg.content || "");
        }, 0);

        const estimatedTotal = estimatedContextTokens + historyTokens;
        const tokenLimit = appConfig.llmTokenLimit;
        const tokenPercentage = (estimatedTotal / tokenLimit) * 100;

        let tokenBgColor = "bg-slate-700";
        let tokenBorderColor = "border-slate-600";
        let tokenIconColor = "text-white";
        let tokenTextColor = "text-white";
        let tokenIcon = "data_usage";
        let tokenPrefix = "~";

        if (currentTokenUsage && currentTokenUsage.total) {
            const actualTotal = currentTokenUsage.total;
            const actualPercentage = (actualTotal / tokenLimit) * 100;
            tokenPrefix = "";

            if (actualPercentage >= 90) {
                tokenBgColor = "bg-red-900/50";
                tokenBorderColor = "border-red-600";
                tokenIconColor = "text-red-400";
                tokenTextColor = "text-red-300";
                tokenIcon = "warning";
            } else if (actualPercentage >= 70) {
                tokenBgColor = "bg-amber-900/50";
                tokenBorderColor = "border-amber-600";
                tokenIconColor = "text-amber-400";
                tokenTextColor = "text-amber-300";
                tokenIcon = "data_usage";
            }
        } else {
            if (tokenPercentage >= 90) {
                tokenBgColor = "bg-red-900/50";
                tokenBorderColor = "border-red-600";
                tokenIconColor = "text-red-400";
                tokenTextColor = "text-red-300";
                tokenIcon = "warning";
            } else if (tokenPercentage >= 70) {
                tokenBgColor = "bg-amber-900/50";
                tokenBorderColor = "border-amber-600";
                tokenIconColor = "text-amber-400";
                tokenTextColor = "text-amber-300";
                tokenIcon = "data_usage";
            }
        }

        const actualOrEstimated = currentTokenUsage ? currentTokenUsage.total : estimatedTotal;

        if (validCount === 0) {
            headerStatus.innerHTML = `
                <div class="inline-flex items-center gap-1.5 px-2 py-1 rounded-md bg-red-900/50 border border-red-600">
                    <span class="material-icons-round text-red-400" style="font-size: 14px;">block</span>
                    <span class="text-xs text-red-300 font-medium">未符合門檻</span>
                </div>
            `;
        } else {
            headerStatus.innerHTML = `
                <div class="inline-flex items-center gap-2">
                    <div class="inline-flex items-center gap-1.5 px-2 py-1 rounded-md bg-blue-900/50 border border-blue-600">
                        <span class="material-icons-round text-blue-400" style="font-size: 14px;">description</span>
                        <span class="text-xs text-blue-300 font-medium">${validCount}/${totalScanned} 篇</span>
                    </div>
                    <div class="inline-flex items-center gap-1.5 px-2 py-1 rounded-md ${tokenBgColor} border ${tokenBorderColor}">
                        <span class="material-icons-round ${tokenIconColor}" style="font-size: 14px;">${tokenIcon}</span>
                        <span class="text-xs ${tokenTextColor} font-medium">${tokenPrefix}${actualOrEstimated.toLocaleString()}</span>
                    </div>
                </div>
            `;
        }
    }

    // --- [新增] 將函式公開到全域，讓搜尋結束後 (main.js) 可以呼叫 ---
    window.updateChatHeader = updateHeaderStatus;

    // --- [新增] 綁定滑桿事件：一拉動就更新 Header ---
    const sliderInput = document.getElementById('similarity-slider') || document.querySelector('input[type="range"]');
    if (sliderInput) {
        sliderInput.addEventListener('input', () => {
            // 1. 同步全域設定 (確保按送出時是對的)
            searchConfig.similarityThreshold = parseInt(sliderInput.value);
            // 2. 呼叫 render.js 的函式，讓卡片變灰，並更新 activeResults
            applyThresholdToResults();
            // 3. 即時更新 Header UI (視覺回饋)
            updateHeaderStatus();
        });
    }

    // 初始化時先執行一次，確保狀態正確
    // (稍微延遲一下確保 currentResults 已經載入)
    setTimeout(updateHeaderStatus, 500);
}
