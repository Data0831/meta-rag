import { searchConfig } from './config.js';
import { applyThresholdToResults } from './render.js';
import { showAlert } from './alert.js';

export function setupSearchConfig() {
    // 1. Similarity threshold slider
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

    // 2. Semantic ratio slider & Mode toggle
    const semanticRatioSlider = document.getElementById('semanticRatioSlider');
    const manualRatioCheckbox = document.getElementById('manualRatioCheckbox');
    const semanticRatioValue = document.getElementById('semanticRatioValue');
    const keywordPercentLabel = document.getElementById('keywordPercent');
    const semanticPercentLabel = document.getElementById('semanticPercent');
    const keywordLabel = document.getElementById('keywordWeightLabel');
    const semanticLabel = document.getElementById('semanticWeightLabel');

    if (semanticRatioSlider && manualRatioCheckbox) {
        const updateUI = (val) => {
            const smVal = parseInt(val);
            const kwVal = 100 - smVal;

            // Update configuration object
            searchConfig.semanticRatio = smVal / 100;

            // Update percentage text
            if (keywordPercentLabel) keywordPercentLabel.textContent = `${kwVal}%`;
            if (semanticPercentLabel) semanticPercentLabel.textContent = `${smVal}%`;

            // Update the main "Ratio Value" label (e.g. "Auto" or "50%")
            if (semanticRatioValue) {
                semanticRatioValue.textContent = manualRatioCheckbox.checked ? "Manual" : "Auto";
                // If you prefer showing the number even in Manual mode, use:
                // semanticRatioValue.textContent = manualRatioCheckbox.checked ? `${smVal}%` : "Auto";
            }

            // Highlighting effect for labels
            if (keywordLabel && semanticLabel) {
                [keywordLabel, semanticLabel].forEach(l => {
                    l.classList.remove('bg-primary', 'text-white');
                    l.classList.add('bg-white', 'dark:bg-slate-700', 'text-slate-500', 'dark:text-slate-400');
                });

                if (smVal < 50) {
                    keywordLabel.classList.add('bg-primary', 'text-white');
                    keywordLabel.classList.remove('bg-white', 'dark:bg-slate-700', 'text-slate-500', 'dark:text-slate-400');
                } else if (smVal > 50) {
                    semanticLabel.classList.add('bg-primary', 'text-white');
                    semanticLabel.classList.remove('bg-white', 'dark:bg-slate-700', 'text-slate-500', 'dark:text-slate-400');
                }
            }
        };

        const handleModeChange = () => {
            // 修正邏輯：Checkbox 勾選代表進入「手動模式」(Manual)
            const isManual = manualRatioCheckbox.checked;

            if (isManual) {
                // 手動模式：啟用滑桿，允許手動調整
                semanticRatioSlider.disabled = false;
                searchConfig.manualSemanticRatio = true;
                // 使用滑桿目前的數值更新 UI 與配置
                updateUI(semanticRatioSlider.value);
            } else {
                // 自動模式：停用滑桿、數值歸位 (50%)、關閉手動配置
                semanticRatioSlider.disabled = true;
                searchConfig.manualSemanticRatio = false;
                semanticRatioSlider.value = 50;
                updateUI(50);
            }
        };

        manualRatioCheckbox.addEventListener('change', handleModeChange);
        semanticRatioSlider.addEventListener('input', (e) => updateUI(e.target.value));

        // Initialization
        handleModeChange();

        // Handle BFCache/Refresh
        window.addEventListener('pageshow', handleModeChange);
    }

    // 3. Search Results Limit
    const limitInput = document.getElementById('limitInput');
    if (limitInput) {
        limitInput.addEventListener('change', (e) => {
            let value = parseInt(e.target.value);
            const maxLimit = searchConfig.maxLimit || 50;
            let correctedValue = value;

            if (isNaN(value) || value < 1) {
                correctedValue = 1;
            } else if (value > maxLimit) {
                correctedValue = maxLimit;
            }

            if (correctedValue !== value) {
                e.target.value = correctedValue;
                showAlert(`您輸入的數量超出範圍，已自動調整為 ${correctedValue}`, 'warning');
            }
            searchConfig.limit = correctedValue;
        });
    }

    // 4. Feature Toggles
    const llmRewriteCheckbox = document.getElementById('llmRewriteCheckbox');
    if (llmRewriteCheckbox) {
        llmRewriteCheckbox.addEventListener('change', (e) => {
            searchConfig.enableLlm = e.target.checked;
        });
    }

    // 5. Date Range
    const startDateInput = document.getElementById('startDateInput');
    if (startDateInput) {
        startDateInput.addEventListener('change', (e) => {
            searchConfig.startDate = e.target.value;
        });
    }

    const endDateInput = document.getElementById('endDateInput');
    if (endDateInput) {
        endDateInput.addEventListener('change', (e) => {
            searchConfig.endDate = e.target.value;
        });
    }

    // 6. Data Source Selection
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

/**
 * Get current selected data source values
 */
export function getSelectedSources() {
    const sourceCheckboxes = document.querySelectorAll('input[name="source_checkbox"]:checked');
    return Array.from(sourceCheckboxes).map(cb => cb.value);
}
