export function convertCitationsToLinks(text, linkMapping) {
    if (!text || !linkMapping) return text;

    // Normalize full-width brackets to half-width
    const normalizedText = text.replace(/【/g, '[').replace(/】/g, ']');

    return normalizedText.replace(/\[(\d+)\]/g, (match, num) => {
        const link = linkMapping[num];
        if (link) {
            return `<a href="${link}" target="_blank" class="citation-link" style="color: #3b82f6; text-decoration: none; font-weight: 600; vertical-align: super; font-size: 0.85em;">${match}</a>`;
        }
        return match;
    });
}

export function renderStructuredSummary(summary, linkMapping, summarizedCount = 0, totalTokens = 0) {

    if (typeof summary === 'string') {
        return marked.parse(summary);
    }

    const { brief_answer, detailed_answer, general_summary } = summary;

    const isNoResults = brief_answer === '沒有參考資料' || brief_answer === '從內容搜索不到';

    let html = '';

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

    const isNoReference = summarizedCount === 0 && totalTokens === 0;

    if (isNoReference) {
        html += `
            <div class="flex items-center gap-2 mt-4 px-4 py-2.5 rounded-lg bg-slate-100 dark:bg-slate-700/50 border border-slate-200 dark:border-slate-600">
                <span class="material-icons-round text-amber-600 dark:text-amber-400 text-lg">info</span>
                <span class="text-sm font-medium text-slate-600 dark:text-slate-300">此摘要並未參考任何資料</span>
            </div>
        `;
    } else {
        html += `
            <div class="flex items-center gap-3 mt-4 px-4 py-2.5 rounded-lg bg-slate-100 dark:bg-slate-700/50 border border-slate-200 dark:border-slate-600">
                <div class="flex items-center gap-1.5">
                    <span class="material-icons-round text-primary text-base">description</span>
                    <span class="text-xs font-semibold text-slate-600 dark:text-slate-300">參考前 ${summarizedCount} 篇</span>
                </div>
                <div class="h-4 w-px bg-slate-300 dark:bg-slate-500"></div>
                <div class="flex items-center gap-1.5">
                    <span class="material-icons-round text-primary text-base">data_usage</span>
                    <span class="text-xs font-semibold text-slate-600 dark:text-slate-300">約耗費 ${totalTokens} token</span>
                </div>
            </div>
        `;
    }

    return html;
}
