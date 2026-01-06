import { currentResults, activeResults, applyThresholdToResults } from './render.js';
import { searchConfig } from './config.js';

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

    // --- [新增] 直接在 JS 設定輸入框最大長度，防止使用者輸入過多 ---
    if (chatInput) {
        chatInput.setAttribute('maxlength', '500');
    }

    let isOpen = false;
    let chatHistory = [];

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

            // fetchInitialSuggestions();
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
                // --- [修改] 針對字數過長顯示友善訊息 ---
                if (data.error.includes("Input length exceeds")) {
                    appendMessage('bot', '**輸入的字數過多**，請精簡您的問題後再試一次。');
                } else {
                    appendMessage('bot', '系統錯誤：' + data.error);
                }
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

    function updateHeaderStatus() {
        if (!headerStatus) return;

        // 1. 嘗試抓取滑桿 DOM 元素 (為了做到拖拉時即時變動)
        // 這裡預設 ID 為 'similarity-slider'，如果你的 HTML ID 不同請在此修改
        const sliderEl = document.getElementById('similarity-slider') || document.querySelector('input[type="range"]');
        
        // 2. 決定當下的門檻值
        let thresholdPercent = searchConfig.similarityThreshold || 0;
        
        // 如果抓得到滑桿，就直接用滑桿的值 (這樣拖曳時才會即時反應)
        if (sliderEl) {
            thresholdPercent = parseInt(sliderEl.value);
        }

        // 3. 檢查是否有資料
        if (!currentResults || currentResults.length === 0) {
            headerStatus.innerHTML = `<span class="text-slate-400">(等待搜尋...)</span>`;
            return;
        }

        const totalScanned = currentResults.length;
        
        // 4. 計算符合門檻的數量
        const validResults = currentResults.filter(item => {
            const rawScore = item._rerank_score !== undefined ? item._rerank_score : (item._rankingScore || 0);

            const scorePercent = Math.round(rawScore * 100);
            
            return scorePercent >= thresholdPercent;
        });
        const validCount = validResults.length;

        // 5. 根據結果顯示不同顏色與文字
        if (validCount === 0) {
            // [紅色] 全部反灰
            headerStatus.innerHTML = `<span style="color: #ffffff; font-size: 15px; font-weight: bold;">(未符合門檻)</span>`;
        } else {
            // [綠色] 有資料 (字體顏色依照你原本設定的 #ffffff 或 #10b981 調整)
            headerStatus.innerHTML = `<span style="color: #ffffff; font-size: 15px; font-weight: bold;">(已載入 ${validCount}/${totalScanned} 篇)</span>`;
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
