import { loadBackendConfig } from './config.js';
import { toggleResult, toggleIntentDetails } from './render.js';
import { setupSearchConfig } from './search-config.js';
import { setupEventListeners, performSearch } from './search-logic.js';
import { setupChatbot } from './chatbot.js';

document.addEventListener('DOMContentLoaded', () => {
    console.log('Collection Search initialized');

    loadBackendConfig();

    setupEventListeners(performSearch);
    setupSearchConfig();
    setupChatbot();
});

window.toggleResult = toggleResult;
window.toggleIntentDetails = toggleIntentDetails;
