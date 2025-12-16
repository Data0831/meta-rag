export function escapeHtml(text) {
    if (!text) return '';
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

/**
 * 根據分數類型與數值，返回對應的顯示資訊
 * @param {number} score - 原始分數
 * @param {string} type - 'Dense' 或 'Hybrid' (表示 Vector Search) / 'Rerank' (表示重排序)
 * @param {boolean} isReranked - 是否啟用了 Reranker
 */
export function getScoreDisplayInfo(score, type, isReranked) {
    let label, confidence, colorClass, badgeClass;

    if (isReranked) {
        // Rerank 分數 (Cohere Relevance Score: 0~1，通常較低)
        label = 'Relevance';
        if (score >= 0.7) {
            confidence = 'High';
            badgeClass = 'bg-green-100 dark:bg-green-900/50 text-green-700 dark:text-green-300';
        } else if (score >= 0.4) {
            confidence = 'Medium';
            badgeClass = 'bg-yellow-100 dark:bg-yellow-900/50 text-yellow-700 dark:text-yellow-300';
        } else {
            confidence = 'Low';
            badgeClass = 'bg-orange-100 dark:bg-orange-900/50 text-orange-700 dark:text-orange-300';
        }
        colorClass = 'text-purple-700 dark:text-purple-300 bg-purple-100 dark:bg-purple-900/50';
    } else {
        // Vector Search 分數 (Cosine Similarity: 通常 0.6~1.0)
        label = type === 'Hybrid' ? 'Hybrid Score' : 'Similarity';
        if (score >= 0.85) {
            confidence = 'High';
            badgeClass = 'bg-green-100 dark:bg-green-900/50 text-green-700 dark:text-green-300';
        } else if (score >= 0.70) {
            confidence = 'Medium';
            badgeClass = 'bg-yellow-100 dark:bg-yellow-900/50 text-yellow-700 dark:text-yellow-300';
        } else {
            confidence = 'Low';
            badgeClass = 'bg-orange-100 dark:bg-orange-900/50 text-orange-700 dark:text-orange-300';
        }
        colorClass = 'text-blue-700 dark:text-blue-300 bg-blue-100 dark:bg-blue-900/50';
    }

    return { label, confidence, colorClass, badgeClass };
}
