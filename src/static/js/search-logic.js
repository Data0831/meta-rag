import * as DOM from './dom.js';
import { performSearchStream } from './api.js';
import { showLoading, showError, hideAllStates } from './ui.js';
import { renderResults } from './render.js';
import { renderStructuredSummary } from './citation.js';
import { getSelectedSources } from './search-config.js';

export function setupEventListeners(performSearchCallback) {
    DOM.searchIconBtn.addEventListener('click', performSearchCallback);
    DOM.searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            performSearchCallback();
        }
    });
}

export async function performSearch() {
    const query = DOM.searchInput.value.trim();

    if (!query) {
        console.warn('⚠️ Empty query');
        showError('請輸入搜尋查詢');
        return;
    }

    const selectedWebsites = getSelectedSources();

    console.log('Active Source Filters:', selectedWebsites);

    hideAllStates();

    const summaryContainer = document.getElementById('summaryContainer');
    const summaryContent = document.getElementById('summaryContent');
    const summaryTitle = document.getElementById('summaryTitle');
    const searchTimeValue = document.getElementById('searchTimeValue');

    if (summaryContainer) {
        summaryContainer.classList.remove('hidden');
        summaryTitle.innerHTML = `<span class="material-icons-round animate-pulse mr-2 align-middle text-primary">manage_search</span>正在初始化搜尋...`;

        summaryContent.innerHTML = `
            <div class="animate-pulse space-y-3">
                <div class="h-2 bg-slate-200 dark:bg-slate-700 rounded w-3/4"></div>
                <div class="h-2 bg-slate-200 dark:bg-slate-700 rounded w-full"></div>
                <div class="h-2 bg-slate-200 dark:bg-slate-700 rounded w-5/6"></div>
            </div>
        `;
    } else {
        showLoading();
    }

    const totalStartTime = performance.now();
    let hasUpdatedResults = false;

    try {
        const response = await performSearchStream(query, selectedWebsites);

        if (!response.body) throw new Error("ReadableStream not supported");

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop();

            for (const line of lines) {
                if (!line.trim()) continue;

                try {
                    const data = JSON.parse(line);
                    console.log('Agent Stream:', data.status, data);

                    if (data.status === "failed") {
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
                        return;
                    }

                    if (data.stage === "searching") {
                        summaryTitle.innerHTML = `<span class="material-icons-round animate-spin mr-2 align-middle text-primary">sync</span>${data.message}`;
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
                        const totalEndTime = performance.now();
                        const totalDuration = Math.round(totalEndTime - totalStartTime);

                        if (searchTimeValue) {
                            searchTimeValue.textContent = totalDuration;
                            searchTimeValue.style.filter = 'none';
                            searchTimeValue.style.opacity = '1';
                        }

                        summaryTitle.innerHTML = `以下為「<span class="text-primary">${query}</span>」的相關公告總結：`;

                        if (data.summary) {
                            summaryContent.innerHTML = renderStructuredSummary(data.summary, data.link_mapping || {});
                        } else {
                            summaryContent.innerHTML = "<p>無相關總結。</p>";
                        }

                        if (data.results && data.results.length > 0) {
                            const renderData = {
                                results: data.results,
                                intent: data.intent || null,
                            };

                            renderResults(renderData, totalDuration, query);

                            if (window.updateChatHeader) {
                                window.updateChatHeader();
                            }
                        } else {
                            if (DOM.resultsContainer) DOM.resultsContainer.classList.add('hidden');
                            if (!data.summary) {
                                showError("未找到相關結果");
                            }
                        }
                    }

                    if (data.new_query) {
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
