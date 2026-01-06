import { loadBackendConfig } from './config.js';
import { toggleResult, toggleIntentDetails, setupFeedbackButtons } from './render.js';
import { setupSearchConfig } from './search-config.js';
import { setupEventListeners, performSearch } from './search-logic.js';
import { setupChatbot } from './chatbot.js';
import { setupSidebar } from './sidebar.js';
import { setupAnnouncement } from './announcement.js';
import { setupSources } from './sources.js';

document.addEventListener('DOMContentLoaded', async () => {
    console.log('Collection Search initialized');

    await loadBackendConfig();

    setupEventListeners(performSearch);
    setupSources();
    setupSearchConfig();
    setupChatbot();
    setupFeedbackButtons();
    setupSidebar();
});

window.addEventListener('load', () => {
    setupAnnouncement();
});

window.toggleResult = toggleResult;
window.toggleIntentDetails = toggleIntentDetails;
