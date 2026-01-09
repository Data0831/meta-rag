import { currentResults, activeResults, applyThresholdToResults } from './render.js';
import { searchConfig, appConfig } from './config.js';
import { showAlert } from './alert.js';
import { sendFeedback } from './api.js';
import { convertCitationsToLinks } from './citation.js';

const MAX_CHAT_HISTORY = 10;
const DEBOUNCE_DELAY = 150;
const HEADER_UPDATE_DELAY = 500;

let currentTokenUsage = null;
let currentLinkMapping = {};

function estimateTokens(text) {
    if (!text) return 0;
    const chineseChars = (text.match(/[\u4e00-\u9fa5]/g) || []).length;
    const otherChars = text.length - chineseChars;
    return Math.ceil(chineseChars * 2.5 + otherChars / 4);
}

function debounce(func, delay) {
    let timeoutId;
    return function (...args) {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => func.apply(this, args), delay);
    };
}

function getCurrentThreshold() {
    const sliderEl = document.getElementById('similarity-slider') || document.querySelector('input[type="range"]');
    return sliderEl ? parseInt(sliderEl.value) : (searchConfig.similarityThreshold || 0);
}

function getValidResults() {
    const thresholdPercent = getCurrentThreshold();

    if (activeResults && activeResults.length > 0) {
        return activeResults;
    }

    if (!currentResults || currentResults.length === 0) {
        return [];
    }

    const isAnyDimmed = document.querySelector('.dimmed-result');
    if (isAnyDimmed) {
        return [];
    }

    return currentResults.filter(item => {
        const rawScore = item._rerank_score !== undefined ? item._rerank_score : (item._rankingScore || 0);
        const scorePercent = Math.round(rawScore * 100);
        return scorePercent >= thresholdPercent;
    });
}

function estimateTotalTokens(results, history) {
    let contextTokens = 0;
    results.forEach(item => {
        const content = item.content || item.cleaned_content || item.body || "";
        contextTokens += estimateTokens(content);
    });

    const historyTokens = history.reduce((sum, msg) => {
        return sum + estimateTokens(msg.content || "");
    }, 0);

    return contextTokens + historyTokens;
}

function calculateTokenStatus(total, limit) {
    const percentage = (total / limit) * 100;
    const isActual = currentTokenUsage && currentTokenUsage.total;
    const actualTotal = isActual ? currentTokenUsage.total : total;
    const actualPercentage = isActual ? (currentTokenUsage.total / limit) * 100 : percentage;

    let bgColor = "bg-slate-700";
    let borderColor = "border-slate-600";
    let iconColor = "text-white";
    let textColor = "text-white";
    let icon = "data_usage";
    const prefix = isActual ? "" : "~";

    if (actualPercentage >= 90) {
        bgColor = "bg-red-900/50";
        borderColor = "border-red-600";
        iconColor = "text-red-400";
        textColor = "text-red-300";
        icon = "warning";
    } else if (actualPercentage >= 70) {
        bgColor = "bg-amber-900/50";
        borderColor = "border-amber-600";
        iconColor = "text-amber-400";
        textColor = "text-amber-300";
    }

    return { bgColor, borderColor, iconColor, textColor, icon, prefix, actualTotal };
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

    messagesDiv.innerHTML = '';
    appendMessage('bot', '您好！我是您的搜尋助手。關於目前的搜尋結果，有什麼想問的嗎？');

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
                chatCharCount.classList.remove('text-slate-400');
            } else {
                chatCharCount.classList.remove('text-red-500', 'font-bold');
                chatCharCount.classList.add('text-slate-400');
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
        if (!list || list.length === 0) return;

        const containerDiv = document.createElement('div');
        containerDiv.className = 'chat-suggestion';

        list.forEach(text => {
            const btn = document.createElement('button');
            btn.textContent = text;
            btn.className = 'chat-suggestion__btn';
            btn.addEventListener('click', () => {
                containerDiv.remove();
                chatInput.value = text;
                sendMessage();
            });
            containerDiv.appendChild(btn);
        });

        messagesDiv.appendChild(containerDiv);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }

    if (clearBtn) {
        clearBtn.addEventListener('click', () => {
            chatHistory = [];
            messagesDiv.innerHTML = '';
            currentTokenUsage = null;

            if (headerStatus) headerStatus.innerHTML = '';

            appendMessage('bot', '您好！我是您的搜尋助手。關於目前的搜尋結果，有什麼想問的嗎？');

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

    function validateInput(text) {
        if (!text) {
            return { valid: false };
        }

        if (text.length > appConfig.maxChatInputLength) {
            showAlert(`訊息字數超過 ${appConfig.maxChatInputLength} 字限制，請縮短內容`, 'warning');
            return { valid: false };
        }

        return { valid: true };
    }

    function checkTokenLimit(text, validResults, chatHistory) {
        const userTokens = estimateTokens(text);
        const estimatedTotal = estimateTotalTokens(validResults, chatHistory) + userTokens;
        const tokenLimit = appConfig.llmTokenLimit;

        if (estimatedTotal > tokenLimit) {
            showAlert(`預估 Token 使用量 (${estimatedTotal.toLocaleString()}) 超過限制 (${tokenLimit.toLocaleString()})，請清除對話歷史或降低相似度閾值`, 'warning');
            return false;
        }

        return true;
    }

    function clearSuggestions() {
        const existingSuggestions = messagesDiv.querySelectorAll('.chat-suggestion');
        existingSuggestions.forEach(el => el.remove());
    }

    function prepareContext(validResults) {
        currentLinkMapping = {};
        return validResults.map((item, idx) => {
            const originalIndex = currentResults.indexOf(item);
            const rank = originalIndex + 1;
            const docIndex = idx + 1;

            currentLinkMapping[String(docIndex)] = item.link || "";

            return {
                title: `[No.${rank}] ${item.title}`,
                content: item.content || item.cleaned_content || item.body || item.text || "",
                link: item.link,
                year_month: item.year_month,
                year: item.year || "",
                website: item.website || ""
            };
        });
    }

    function handleChatResponse(data, userQuery) {
        if (data.error) {
            if (data.error.includes("Input length exceeds")) {
                appendMessage('bot', '**輸入的字數過多**，請精簡您的問題後再試一次。', userQuery);
            } else if (data.error.includes("Token 使用量")) {
                appendMessage('bot', `**Token 超限錯誤**\n\n${data.error}`, userQuery);
                if (data.suggestions && data.suggestions.length > 0) {
                    renderSuggestions(data.suggestions);
                }
            } else {
                appendMessage('bot', '系統錯誤：' + data.error, userQuery);
            }

            if (data.token_usage) {
                currentTokenUsage = data.token_usage;
                updateHeaderStatus();
            }
        } else {
            appendMessage('bot', data.answer, userQuery);

            if (data.suggestions && data.suggestions.length > 0) {
                renderSuggestions(data.suggestions);
            }

            chatHistory.push({ role: 'user', content: userQuery });
            chatHistory.push({ role: 'model', content: data.answer });

            if (chatHistory.length > MAX_CHAT_HISTORY) {
                chatHistory = chatHistory.slice(-MAX_CHAT_HISTORY);
            }

            if (data.token_usage) {
                currentTokenUsage = data.token_usage;
                updateHeaderStatus();
            }
        }
    }

    async function sendMessage() {
        const text = chatInput.value.trim();
        const validation = validateInput(text);
        if (!validation.valid) return;

        const validResults = getValidResults();

        if (!checkTokenLimit(text, validResults, chatHistory)) {
            return;
        }

        clearSuggestions();

        if (!currentResults || currentResults.length === 0) {
            appendMessage('user', text);
            setTimeout(() => {
                appendMessage('bot', '請先在左側搜尋欄輸入關鍵字查詢公告，我才能根據搜尋結果回答您的問題喔！', text);
                renderSuggestions(["如何搜尋公告？", "Copilot 是什麼？", "搜尋最新價格"]);
            }, 500);
            chatInput.value = '';
            return;
        }

        appendMessage('user', text);
        chatInput.value = '';

        const loadingId = appendLoading();

        try {
            const thresholdPercent = getCurrentThreshold();
            const totalScanned = currentResults.length;

            if (validResults.length === 0) {
                removeMessage(loadingId);
                appendMessage('bot', `機器人提示：發現資料並未符合相似度，參考前 ${totalScanned} 篇，如果要參考更多篇請調低 相似閾值`, text);
                return;
            }

            console.log(`Chatbot Context: 使用了 ${validResults.length} 筆資料 (門檻: ${thresholdPercent}%)`);

            const currentContext = prepareContext(validResults);

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

            handleChatResponse(data, text);

        } catch (error) {
            removeMessage(loadingId);
            appendMessage('bot', '網路連線錯誤，請檢查後端是否啟動。', text);
            console.error(error);
        }
    }

    sendBtn.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });

    messagesDiv.addEventListener('click', (e) => {
        const copyBtn = e.target.closest('.chat-message__action-btn--copy');
        const goodBtn = e.target.closest('.chat-message__action-btn--good');
        const badBtn = e.target.closest('.chat-message__action-btn--bad');

        if (copyBtn) {
            const messageText = copyBtn.getAttribute('data-message');
            navigator.clipboard.writeText(messageText).then(() => {
                const icon = copyBtn.querySelector('.material-icons-round');
                icon.textContent = 'check';
                setTimeout(() => icon.textContent = 'content_copy', 2000);
            });
        }

        if (goodBtn) {
            const userQuery = goodBtn.getAttribute('data-query');
            sendFeedback('positive', userQuery || "Chatbot Response", { ...searchConfig, source: 'chatbot' })
                .then(() => {
                    goodBtn.classList.add('active');
                    showAlert('感謝您的肯定！', 'success');
                })
                .catch(e => console.error(e));
        }

        if (badBtn) {
            const userQuery = badBtn.getAttribute('data-query');
            sendFeedback('negative', userQuery || "Chatbot Response", { ...searchConfig, source: 'chatbot' })
                .then(() => {
                    badBtn.classList.add('active');
                    showAlert('感謝您的意見，我們會持續改進！', 'info');
                })
                .catch(e => console.error(e));
        }
    });

    function appendMessage(role, text, userQuery = null) {
        const div = document.createElement('div');
        const isBot = role === 'bot';

        div.className = `chat-message chat-message--${role}`;

        if (isBot) {
            const parsedHtml = marked.parse(text);
            const htmlWithLinks = convertCitationsToLinks(parsedHtml, currentLinkMapping);
            div.innerHTML = `
                <div class="prose prose-sm max-w-none leading-relaxed chat-message__bot">
                    ${htmlWithLinks}
                </div>
                <div class="chat-message__actions">
                    <button class="chat-message__action-btn chat-message__action-btn--copy" title="複製回覆" data-message="${text.replace(/"/g, '&quot;')}">
                        <span class="material-icons-round" style="font-size: 16px;">content_copy</span>
                    </button>
                    <button class="chat-message__action-btn chat-message__action-btn--good" title="有幫助" data-query="${(userQuery || 'Chatbot Response').replace(/"/g, '&quot;')}">
                        <span class="material-icons-round" style="font-size: 16px;">thumb_up</span>
                    </button>
                    <button class="chat-message__action-btn chat-message__action-btn--bad" title="沒幫助" data-query="${(userQuery || 'Chatbot Response').replace(/"/g, '&quot;')}">
                        <span class="material-icons-round" style="font-size: 16px;">thumb_down</span>
                    </button>
                </div>
            `;
        } else {
            const messageContent = text.replace(/\n/g, '<br>');
            div.innerHTML = `
                <div class="chat-message__user">
                    ${messageContent}
                </div>
            `;
        }

        messagesDiv.appendChild(div);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
        return div.id;
    }

    function appendLoading() {
        const id = 'msg-' + Date.now();
        const div = document.createElement('div');
        div.id = id;
        div.className = 'chat-loading';
        div.innerHTML = `
            <div class="chat-loading__container">
                <div class="chat-loading__dot"></div>
                <div class="chat-loading__dot"></div>
                <div class="chat-loading__dot"></div>
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

        const thresholdPercent = getCurrentThreshold();

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

        const estimatedTotal = estimateTotalTokens(validResults, chatHistory);
        const tokenLimit = appConfig.llmTokenLimit;

        const tokenStatus = calculateTokenStatus(estimatedTotal, tokenLimit);

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
                    <div class="inline-flex items-center gap-1.5 px-2 py-1 rounded-md bg-slate-700 border border-slate-600">
                        <span class="material-icons-round text-white" style="font-size: 14px;">description</span>
                        <span class="text-xs text-white font-medium">${validCount}/${totalScanned} 篇</span>
                    </div>
                    <div class="inline-flex items-center gap-1.5 px-2 py-1 rounded-md ${tokenStatus.bgColor} border ${tokenStatus.borderColor}">
                        <span class="material-icons-round ${tokenStatus.iconColor}" style="font-size: 14px;">${tokenStatus.icon}</span>
                        <span class="text-xs ${tokenStatus.textColor} font-medium">${tokenStatus.prefix}${tokenStatus.actualTotal.toLocaleString()}</span>
                    </div>
                </div>
            `;
        }
    }

    function renderChatbotModelBadge() {
        const badgeEl = document.getElementById('modelNameBadge');
        if (badgeEl && appConfig.proxyModelName) {
            badgeEl.textContent = appConfig.proxyModelName;
        }
    }

    window.updateChatHeader = updateHeaderStatus;
    window.renderChatbotModelBadge = renderChatbotModelBadge;

    const sliderInput = document.getElementById('similarity-slider') || document.querySelector('input[type="range"]');
    if (sliderInput) {
        const debouncedUpdate = debounce(() => {
            searchConfig.similarityThreshold = parseInt(sliderInput.value);
            applyThresholdToResults();
            updateHeaderStatus();
        }, DEBOUNCE_DELAY);

        sliderInput.addEventListener('input', debouncedUpdate);
    }

    setTimeout(() => {
        updateHeaderStatus();
        renderChatbotModelBadge();
    }, HEADER_UPDATE_DELAY);
}
