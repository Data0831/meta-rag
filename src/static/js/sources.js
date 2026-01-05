import { appConfig } from './config.js';

export function setupSources() {
    const sourceCheckboxList = document.getElementById('sourceCheckboxList');
    if (!sourceCheckboxList) {
        console.error('sourceCheckboxList element not found');
        return;
    }

    const sources = appConfig.sources;
    if (!sources || !Array.isArray(sources)) {
        console.error('No sources configuration found');
        return;
    }

    sources.forEach(source => {
        const label = document.createElement('label');
        label.className = 'flex items-center space-x-3 cursor-pointer group';

        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.name = 'source_checkbox';
        checkbox.value = source.value;
        checkbox.checked = source.default_checked;
        checkbox.className = 'source-item w-4 h-4 text-primary bg-white dark:bg-slate-700 border-slate-300 dark:border-slate-500 rounded focus:ring-primary transition-colors group-hover:border-primary';

        const span = document.createElement('span');
        span.className = 'text-sm text-slate-600 dark:text-slate-300 group-hover:text-primary transition-colors';
        span.textContent = source.label;

        label.appendChild(checkbox);
        label.appendChild(span);
        sourceCheckboxList.appendChild(label);
    });

    console.log('Sources initialized:', sources.length);
}
