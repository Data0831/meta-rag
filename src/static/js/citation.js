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

export function renderStructuredSummary(summary, linkMapping) {

    if (typeof summary === 'string') {
        return marked.parse(summary);
    }

    const { brief_answer, detailed_answer, general_summary } = summary;

    const isNoResults = brief_answer === '沒有參考資料' || brief_answer === '從內容 search 不到';

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

    return html;
}
