import { appConfig } from './config.js';

export function estimateTokens(text) {
    if (!text) return 0;
    const chineseChars = (text.match(/[\u4e00-\u9fa5]/g) || []).length;
    const otherChars = text.length - chineseChars;
    return Math.ceil(chineseChars * 2.5 + otherChars / 4);
}

export function estimateTotalTokens(results, history) {
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

export class ChatHistory {
    constructor() {
        this.history = [];
    }

    addMessage(role, content) {
        this.history.push({ role, content });

        const maxHistory = appConfig.maxChatHistory || 10;
        if (this.history.length > maxHistory) {
            this.history = this.history.slice(-maxHistory);
        }
    }

    getHistory() {
        return this.history;
    }

    clear() {
        this.history = [];
    }

    getLength() {
        return this.history.length;
    }
}
