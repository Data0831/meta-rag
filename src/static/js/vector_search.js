// Vector Search Collections Management

// DOM Elements
const loadingState = document.getElementById('loadingState');
const errorState = document.getElementById('errorState');
const errorMessage = document.getElementById('errorMessage');
const collectionsContainer = document.getElementById('collectionsContainer');
const collectionsBody = document.getElementById('collectionsBody');
const emptyState = document.getElementById('emptyState');
const refreshBtn = document.getElementById('refreshBtn');
const detailsModal = document.getElementById('detailsModal');
const closeModalBtn = document.getElementById('closeModalBtn');
const modalTitle = document.getElementById('modalTitle');
const modalContent = document.getElementById('modalContent');

// State Management
let collections = [];

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadCollections();
    setupEventListeners();
    highlightActiveTab();
});

// Highlight active tab
function highlightActiveTab() {
    const currentPath = window.location.pathname;
    const tabs = document.querySelectorAll('a[href^="/"]');

    tabs.forEach(tab => {
        const href = tab.getAttribute('href');
        if (href === currentPath) {
            // Active tab styles (already set in HTML, but ensure consistency)
            tab.classList.add('bg-white', 'dark:bg-gray-800', 'text-gray-900', 'dark:text-gray-100', 'shadow-sm', 'z-10');
            tab.classList.remove('text-gray-600', 'dark:text-gray-400');
        }
    });
}

// Event Listeners
function setupEventListeners() {
    refreshBtn.addEventListener('click', loadCollections);
    closeModalBtn.addEventListener('click', closeModal);

    // Close modal on backdrop click
    detailsModal.addEventListener('click', (e) => {
        if (e.target === detailsModal) {
            closeModal();
        }
    });
}

// Fetch Collections from API
async function loadCollections() {
    showLoading();

    try {
        const response = await fetch('/api/collections');

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        collections = data.collections || [];

        if (collections.length === 0) {
            showEmptyState();
        } else {
            renderCollections();
        }
    } catch (error) {
        showError(error.message);
    }
}

// Render Collections Table
function renderCollections() {
    hideAllStates();
    collectionsContainer.classList.remove('hidden');

    collectionsBody.innerHTML = collections.map(collection => {
        // Check if collection has error
        if (collection.error) {
            return `
                <tr class="hover:bg-gray-50 transition-colors bg-red-50">
                    <td class="px-6 py-4 whitespace-nowrap">
                        <div class="flex items-center space-x-2">
                            <span class="material-symbols-outlined text-red-400">error</span>
                            <span class="text-sm font-medium text-gray-900">${collection.name}</span>
                        </div>
                    </td>
                    <td colspan="6" class="px-6 py-4">
                        <span class="text-sm text-red-600">Error: ${collection.error}</span>
                    </td>
                </tr>
            `;
        }

        // Safely access config properties with fallbacks
        const vectors = collection.config?.params?.vectors || {};
        const shardNumber = collection.config?.params?.shard_number || 1;

        const vectorConfigs = renderVectorConfigs(vectors);
        const statusBadge = renderStatusBadge(collection.status);

        return `
            <tr class="hover:bg-gray-50 transition-colors">
                <td class="px-6 py-4 whitespace-nowrap">
                    <a href="/collection/${encodeURIComponent(collection.name)}" class="flex items-center space-x-2 group">
                        <span class="material-symbols-outlined text-gray-400 group-hover:text-blue-600 transition-colors">folder</span>
                        <span class="text-sm font-medium text-gray-900 group-hover:text-blue-600 transition-colors cursor-pointer">${collection.name}</span>
                    </a>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    ${statusBadge}
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <span class="text-sm text-gray-900">${collection.points_count.toLocaleString()}</span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <span class="text-sm text-gray-900">${collection.segments_count}</span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <span class="text-sm text-gray-900">${shardNumber}</span>
                </td>
                <td class="px-6 py-4">
                    ${vectorConfigs}
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <button onclick="showDetails('${collection.name}')"
                            class="text-blue-600 hover:text-blue-800 transition-colors">
                        <span class="material-symbols-outlined">more_vert</span>
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}

// Render Vector Configuration Badges
function renderVectorConfigs(vectorsConfig) {
    if (!vectorsConfig || Object.keys(vectorsConfig).length === 0) {
        return '<span class="text-sm text-gray-400">N/A</span>';
    }

    // Handle both object and direct config formats
    const configs = [];

    if (typeof vectorsConfig === 'object' && vectorsConfig !== null) {
        // Named vectors (e.g., {dense: {...}, sparse: {...}})
        for (const [name, config] of Object.entries(vectorsConfig)) {
            // Null/undefined check
            if (!config) continue;

            // Dense vector - check for size property
            if (config.size !== undefined && config.size !== null) {
                const distance = config.distance || 'Cosine';
                configs.push({
                    name: name,
                    type: 'dense',
                    size: config.size,
                    distance: distance
                });
            }
            // Sparse vector - check for various sparse indicators
            else if (config.sparse === true || config.index !== undefined || config.modifier !== undefined) {
                configs.push({
                    name: name,
                    type: 'sparse'
                });
            }
        }
    } else if (vectorsConfig.size !== undefined && vectorsConfig.size !== null) {
        // Single unnamed vector
        configs.push({
            name: 'Default',
            type: 'dense',
            size: vectorsConfig.size,
            distance: vectorsConfig.distance || 'Cosine'
        });
    }

    // If no valid configs found, return N/A
    if (configs.length === 0) {
        return '<span class="text-sm text-gray-400">N/A</span>';
    }

    return configs.map(config => {
        if (config.type === 'dense') {
            return `
                <div class="inline-flex items-center space-x-1 bg-blue-50 text-blue-700 px-2 py-1 rounded text-xs mr-2 mb-1">
                    <span class="font-medium">${config.name}</span>
                    <span class="text-blue-500">&bull;</span>
                    <span>${config.size}</span>
                    <span class="text-blue-500">&bull;</span>
                    <span>${config.distance}</span>
                </div>
            `;
        } else {
            return `
                <div class="inline-flex items-center space-x-1 bg-purple-50 text-purple-700 px-2 py-1 rounded text-xs mr-2 mb-1">
                    <span class="font-medium">${config.name}</span>
                    <span class="text-purple-500">&bull;</span>
                    <span>Sparse</span>
                </div>
            `;
        }
    }).join('');
}

// Render Status Badge
function renderStatusBadge(status) {
    const statusMap = {
        'green': { color: 'green', label: 'GREEN', icon: 'check_circle' },
        'yellow': { color: 'yellow', label: 'YELLOW', icon: 'warning' },
        'red': { color: 'red', label: 'RED', icon: 'error' },
        'unknown': { color: 'gray', label: 'UNKNOWN', icon: 'help' }
    };

    const statusInfo = statusMap[status?.toLowerCase()] || statusMap['green'];

    return `
        <div class="inline-flex items-center space-x-1.5">
            <span class="material-symbols-outlined text-${statusInfo.color}-600 text-base">${statusInfo.icon}</span>
            <span class="text-sm font-medium text-${statusInfo.color}-700">${statusInfo.label}</span>
        </div>
    `;
}

// Show Collection Details Modal
function showDetails(collectionName) {
    const collection = collections.find(c => c.name === collectionName);
    if (!collection) return;

    modalTitle.textContent = collection.name;
    modalContent.innerHTML = `
        <div class="space-y-6">
            <!-- Basic Info -->
            <div>
                <h3 class="text-sm font-medium text-gray-500 mb-3">Basic Information</h3>
                <dl class="grid grid-cols-2 gap-4">
                    <div>
                        <dt class="text-sm text-gray-500">Status</dt>
                        <dd class="mt-1 text-sm font-medium text-gray-900">${collection.status.toUpperCase()}</dd>
                    </div>
                    <div>
                        <dt class="text-sm text-gray-500">Points Count</dt>
                        <dd class="mt-1 text-sm font-medium text-gray-900">${collection.points_count.toLocaleString()}</dd>
                    </div>
                    <div>
                        <dt class="text-sm text-gray-500">Segments</dt>
                        <dd class="mt-1 text-sm font-medium text-gray-900">${collection.segments_count}</dd>
                    </div>
                    <div>
                        <dt class="text-sm text-gray-500">Shards</dt>
                        <dd class="mt-1 text-sm font-medium text-gray-900">${collection.config.params.shard_number || 1}</dd>
                    </div>
                </dl>
            </div>

            <!-- Vector Configuration -->
            <div>
                <h3 class="text-sm font-medium text-gray-500 mb-3">Vector Configuration</h3>
                <div class="bg-gray-50 rounded-lg p-4">
                    <pre class="text-xs text-gray-800 overflow-x-auto">${JSON.stringify(collection.config.params.vectors, null, 2)}</pre>
                </div>
            </div>

            <!-- Optimizer Config -->
            ${collection.config.optimizer_config ? `
            <div>
                <h3 class="text-sm font-medium text-gray-500 mb-3">Optimizer Configuration</h3>
                <div class="bg-gray-50 rounded-lg p-4">
                    <pre class="text-xs text-gray-800 overflow-x-auto">${JSON.stringify(collection.config.optimizer_config, null, 2)}</pre>
                </div>
            </div>
            ` : ''}

            <!-- Actions -->
            <div class="flex flex-col space-y-2 pt-4 border-t border-gray-200">
                <a href="/collection/${encodeURIComponent(collection.name)}"
                   class="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
                    <span class="flex items-center justify-center space-x-2">
                        <span class="material-symbols-outlined text-base">search</span>
                        <span>搜尋此集合</span>
                    </span>
                </a>
                <div class="flex space-x-3">
                    <button onclick="deleteCollection('${collection.name}')"
                            class="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors">
                        <span class="flex items-center justify-center space-x-2">
                            <span class="material-symbols-outlined text-base">delete</span>
                            <span>Delete</span>
                        </span>
                    </button>
                    <button onclick="exportCollection('${collection.name}')"
                            class="flex-1 px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors">
                        <span class="flex items-center justify-center space-x-2">
                            <span class="material-symbols-outlined text-base">download</span>
                            <span>Export</span>
                        </span>
                    </button>
                </div>
            </div>
        </div>
    `;

    detailsModal.classList.remove('hidden');
}

// Close Modal
function closeModal() {
    detailsModal.classList.add('hidden');
}

// Delete Collection (Placeholder)
function deleteCollection(collectionName) {
    if (!confirm(`Are you sure you want to delete collection "${collectionName}"? This action cannot be undone.`)) {
        return;
    }

    // TODO: Implement delete API call
    alert('Delete function not yet implemented');
}

// Export Collection (Placeholder)
function exportCollection(collectionName) {
    // TODO: Implement export API call
    alert('Export function not yet implemented');
}

// UI State Management
function showLoading() {
    hideAllStates();
    loadingState.classList.remove('hidden');
}

function showError(message) {
    hideAllStates();
    errorMessage.textContent = message;
    errorState.classList.remove('hidden');
}

function showEmptyState() {
    hideAllStates();
    emptyState.classList.remove('hidden');
}

function hideAllStates() {
    loadingState.classList.add('hidden');
    errorState.classList.add('hidden');
    collectionsContainer.classList.add('hidden');
    emptyState.classList.add('hidden');
}

// Make functions globally accessible for onclick handlers
window.showDetails = showDetails;
window.deleteCollection = deleteCollection;
window.exportCollection = exportCollection;
