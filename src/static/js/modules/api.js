export async function fetchCollectionStats(collectionName) {
    const response = await fetch(`/api/collection_stats/${collectionName}`);
    return await response.json();
}

export async function fetchConfig() {
    const response = await fetch('/api/config');
    return await response.json();
}

export async function clearLlmHistory() {
    const response = await fetch('/api/clear_llm_history', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    });
    return await response.json();
}

export async function sendChatRequest(payload) {
    const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
    return await response.json();
}

export async function uploadFile(formData) {
    const response = await fetch('/api/upload', {
        method: 'POST',
        body: formData
    });
    const data = await response.json();
    return { ok: response.ok, data };
}

export async function clearCollection(collectionName) {
    const response = await fetch('/api/clear_collection', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ collection_name: collectionName })
    });
    const data = await response.json();
    return { ok: response.ok, data };
}

export async function clearLastLlmTurn() {
    const response = await fetch('/api/clear_last_llm_turn', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    });
    return await response.json();
}
