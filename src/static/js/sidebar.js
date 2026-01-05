export function setupSidebar() {
    const sidebar = document.getElementById('sidebar');
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebarBackdrop = document.getElementById('sidebarBackdrop');

    function openSidebar() {
        sidebar.classList.remove('-translate-x-full');
        sidebarBackdrop.classList.remove('pointer-events-none');
        sidebarBackdrop.classList.add('opacity-100');
    }

    function closeSidebar() {
        sidebar.classList.add('-translate-x-full');
        sidebarBackdrop.classList.add('pointer-events-none');
        sidebarBackdrop.classList.remove('opacity-100');
    }

    sidebarToggle.addEventListener('click', () => {
        if (sidebar.classList.contains('-translate-x-full')) {
            openSidebar();
        } else {
            closeSidebar();
        }
    });

    sidebarBackdrop.addEventListener('click', closeSidebar);
}

export function setupChatbotToggle() {
    const chatTriggerBtn = document.getElementById('chatTriggerBtn');
    const chatbotContainer = document.getElementById('chatbotContainer');

    chatTriggerBtn.addEventListener('click', () => {
        const isOpening = chatbotContainer.classList.contains('translate-x-[calc(100%-4rem)]');

        if (isOpening) {
            chatbotContainer.classList.remove('translate-x-[calc(100%-4rem)]');
            chatbotContainer.classList.add('translate-x-0');
            document.body.classList.add('lock-scroll');
        } else {
            chatbotContainer.classList.add('translate-x-[calc(100%-4rem)]');
            chatbotContainer.classList.remove('translate-x-0');
            document.body.classList.remove('lock-scroll');
        }
    });
}
