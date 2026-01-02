import { searchConfig } from './config.js';
import { applyThresholdToResults } from './render.js';
import { showAlert } from './alert.js';

export function setupSearchConfig() {
    const similarityThresholdEl = document.getElementById('similarityThreshold');
    const thresholdValue = document.getElementById('thresholdValue');
    if (similarityThresholdEl && thresholdValue) {
        similarityThresholdEl.addEventListener('input', (e) => {
            const sliderValue = parseInt(e.target.value);
            searchConfig.similarityThreshold = sliderValue;
            thresholdValue.textContent = searchConfig.similarityThreshold + '%';
            applyThresholdToResults();
        });
    }

    const semanticRatioSlider = document.getElementById('semanticRatioSlider');
    const manualRatioCheckbox = document.getElementById('manualRatioCheckbox');
    const semanticRatioValue = document.getElementById('semanticRatioValue');

    if (semanticRatioSlider && manualRatioCheckbox) {
        semanticRatioSlider.disabled = !manualRatioCheckbox.checked;
        if (!manualRatioCheckbox.checked) {
            if (semanticRatioValue) semanticRatioValue.textContent = "Auto";
        }

        manualRatioCheckbox.addEventListener('change', (e) => {
            const isManual = e.target.checked;
            searchConfig.manualSemanticRatio = isManual;
            semanticRatioSlider.disabled = !isManual;

            if (isManual) {
                const val = parseInt(semanticRatioSlider.value);
                searchConfig.semanticRatio = val / 100;
                if (semanticRatioValue) semanticRatioValue.textContent = val + '%';
            } else {
                if (semanticRatioValue) semanticRatioValue.textContent = "Auto";
            }
        });

        semanticRatioSlider.addEventListener('input', (e) => {
            const val = parseInt(e.target.value);
            searchConfig.semanticRatio = val / 100;
            if (semanticRatioValue) {
                semanticRatioValue.textContent = val + '%';
            }
        });
    }

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

    const llmRewriteCheckbox = document.getElementById('llmRewriteCheckbox');
    if (llmRewriteCheckbox) {
        llmRewriteCheckbox.addEventListener('change', (e) => {
            searchConfig.enableLlm = e.target.checked;
        });
    }

    const enableKeywordWeightRerankCheckbox = document.getElementById('enableKeywordWeightRerankCheckbox');
    if (enableKeywordWeightRerankCheckbox) {
        enableKeywordWeightRerankCheckbox.addEventListener('change', (e) => {
            searchConfig.enableKeywordWeightRerank = e.target.checked;
        });
    }

    const startDateInput = document.getElementById('startDateInput');
    if (startDateInput) {
        startDateInput.addEventListener('change', (e) => {
            searchConfig.startDate = e.target.value;
            console.log('開始日期已更新:', searchConfig.startDate);
        });
    }

    const endDateInput = document.getElementById('endDateInput');
    if (endDateInput) {
        endDateInput.addEventListener('change', (e) => {
            searchConfig.endDate = e.target.value;
            console.log('結束日期已更新:', searchConfig.endDate);
        });
    }

    const selectAllCheckbox = document.getElementById('selectAllSources');
    const sourceCheckboxes = document.querySelectorAll('input[name="source_checkbox"]');

    if (selectAllCheckbox && sourceCheckboxes.length > 0) {
        selectAllCheckbox.addEventListener('change', (e) => {
            const isChecked = e.target.checked;
            sourceCheckboxes.forEach(cb => {
                cb.checked = isChecked;
            });
        });

        sourceCheckboxes.forEach(cb => {
            cb.addEventListener('change', () => {
                const allChecked = Array.from(sourceCheckboxes).every(item => item.checked);
                selectAllCheckbox.checked = allChecked;
            });
        });
    }
}

export function getSelectedSources() {
    const selected = [];
    const sourceCheckboxes = document.querySelectorAll('input[name="source_checkbox"]:checked');

    sourceCheckboxes.forEach(cb => {
        selected.push(cb.value);
    });

    return selected;
}
