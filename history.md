# Project History

## 2025-12-15 ~ 2026-01-08 系統奠基、Agent 開發與基礎設施完善
- **核心架構與檢索優化**：完成 Meilisearch 遷移與 Agentic RAG (SrhSumAgent) 核心實作，整合關鍵字加權重排、多階段去重合併及多樣性檢索機制，顯著提升公告搜尋的精確度與穩定性。
- **基礎設施與配置動態化**：建立統一日誌管理系統 (LogManager) 與硬體感知向量生成優化，並將資料來源、版本、日期範圍等系統參數全面改為後端配置驅動，大幅提升維護性。
- **UI/UX 模組化與互動增強**：重構前端模組化架構，實作引用格式規化、即時字數驗證、反饋系統及 Chatbot 互動優化（含建議回答、複製功能與狀態展示），打造更具層次感的智慧檢索體驗。


### 2026-01-09 Chatbot 重構與 CSS 模組化 (Chatbot Refactoring & CSS Modularization)

- **JavaScript 重構**：提取常數（MAX_CHAT_HISTORY、DEBOUNCE_DELAY、HEADER_UPDATE_DELAY），新增工具函數（debounce、getCurrentThreshold、getValidResults、estimateTotalTokens、calculateTokenStatus）消除重複邏輯。將 sendMessage 從 140 行拆分為 7 個小函數（validateInput、checkTokenLimit、clearSuggestions、prepareContext、handleChatResponse），updateHeaderStatus 從 100 行簡化到 50 行，提升可讀性與可維護性。
- **效能優化**：實作事件委派機制（messagesDiv.addEventListener）統一處理訊息按鈕點擊，避免每次 appendMessage 綁定新監聽器造成記憶體洩漏。為 similarity slider 輸入添加 150ms debounce，減少不必要的計算與 DOM 重繪。
- **CSS 模組化**：建立獨立的 `chat.css`，使用 BEM 命名規範（chat-message、chat-message--bot、chat-message__action-btn、chat-suggestion、chat-loading 等），從 `style.css` 提取 184 行 chat 相關樣式並移除所有 `.dark` 前綴（不支援 dark mode），更新 `index.html` 引用新 CSS 文件，實現樣式模組化管理。
