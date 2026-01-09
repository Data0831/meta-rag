let latestAnnouncements = [];

function renderArticle(index) {
    const item = latestAnnouncements[index];
    if (!item) return;

    document.getElementById('articleTitle').innerText = item.title;

    let rawContent = "";
    if (Array.isArray(item.content)) {
        rawContent = item.content.join('\n');
    } else {
        rawContent = String(item.content || "");
    }

    document.getElementById('articleBody').innerHTML = marked.parse(rawContent);

    document.querySelectorAll('.side-menu-item').forEach((el, i) => {
        if (i === index) {
            el.classList.add('bg-[#7facb6]/10', 'text-[#7facb6]', 'border-l-4', 'border-[#7facb6]');
            el.classList.remove('text-slate-600', 'dark:text-slate-400');
        } else {
            el.classList.remove('bg-[#7facb6]/10', 'text-[#7facb6]', 'border-l-4', 'border-[#7facb6]');
            el.classList.add('text-slate-600', 'dark:text-slate-400');
        }
    });
}

function getUpdateStatusHtml(dateStr, count) {
    if (!dateStr) return '';

    const updateDate = new Date(dateStr);
    const today = new Date();

    today.setHours(0, 0, 0, 0);
    updateDate.setHours(0, 0, 0, 0);

    const diffTime = today - updateDate;
    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));

    if (diffDays === 0) {
        return `<span class="text-[#7facb6] font-bold text-[11px]">今日更新 ${count} 篇</span>`;
    }

    if (diffDays >= 1 && diffDays <= 7) {
        return `<span class="text-slate-500 dark:text-slate-400">上次更新時間：${diffDays}天前</span>`;
    }

    return `<span class="text-slate-500 dark:text-slate-400">上次更新時間：${dateStr}</span>`;
}

function switchTab(tab) {
    const tabLatest = document.getElementById('tabLatest');
    const tabWebsites = document.getElementById('tabWebsites');
    const viewLatest = document.getElementById('viewLatest');
    const viewWebsites = document.getElementById('viewWebsites');

    const activeBtn = "bg-white text-[#7facb6] shadow-sm";
    const inactiveBtn = "text-white hover:bg-white/10";

    if (tab === 'latest') {
        tabLatest.className = `px-6 py-1.5 rounded-md text-sm font-bold transition-all ${activeBtn}`;
        tabWebsites.className = `px-6 py-1.5 rounded-md text-sm font-bold transition-all ${inactiveBtn}`;
        viewLatest.classList.remove('hidden');
        viewWebsites.classList.add('hidden');
    } else {
        tabWebsites.className = `px-6 py-1.5 rounded-md text-sm font-bold transition-all ${activeBtn}`;
        tabLatest.className = `px-6 py-1.5 rounded-md text-sm font-bold transition-all ${inactiveBtn}`;
        viewWebsites.classList.remove('hidden');
        viewLatest.classList.add('hidden');
    }
}

async function loadData() {
    const latestSideMenu = document.getElementById('latestSideMenu');
    const announcementGridContainer = document.getElementById('announcementGrid');

    try {
        const res = await fetch('/api/config');
        if (res.ok) {
            const configData = await res.json();

            latestAnnouncements = configData.announcements || [];
            const webData = configData.websites || [];

            latestSideMenu.innerHTML = latestAnnouncements.map((item, index) => `
                <div onclick="window.renderArticle(${index})" class="side-menu-item p-4 cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-800 transition-all border-b border-slate-100 dark:border-slate-800 text-sm font-medium text-slate-600 dark:text-slate-400">
                    ${item.main_title}
                </div>
            `).join('');
            if (latestAnnouncements.length > 0) renderArticle(0);

            announcementGridContainer.innerHTML = webData.map(item => {
                const updateInfoHtml = getUpdateStatusHtml(item.update_date, item.update_count);

                return `
                    <a href="${item.URL}" target="_blank" class="relative group flex items-center bg-slate-50 dark:bg-slate-800 rounded-lg overflow-hidden border border-slate-200 dark:border-slate-700 hover:border-[#7facb6] hover:shadow-md transition-all duration-300">
                        <div class="w-26 h-20 shrink-0 bg-slate-200 dark:bg-slate-700 relative overflow-hidden">
                            <img src="https://s.wordpress.com/mshots/v1/${encodeURIComponent(item.URL)}?w=200"
                                class="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500"
                                onerror="this.src='https://via.placeholder.com/200x160?text=No+Img'">
                        </div>

                        <div class="px-3 py-1 flex-1 min-w-0 text-left">
                            <h4 class="text-[13px] font-bold text-slate-800 dark:text-slate-100 truncate group-hover:text-[#7facb6]">
                                ${item.title}
                            </h4>
                            <p class="text-[10px] text-slate-400 truncate">點擊前往查看</p>
                        </div>

                        <div class="absolute bottom-1 right-2 text-[10px] font-medium pointer-events-none">
                            ${updateInfoHtml}
                        </div>
                    </a>
                `;
            }).join('');
        }
    } catch (err) {
        console.error(err);
    }
}

function initDontShowAgain() {
    const dontShowAgainCheckbox = document.getElementById('dontShowAgain');
    const isHidden = localStorage.getItem('hideAnnouncementModal') === 'true';
    dontShowAgainCheckbox.checked = isHidden;
}

function setupDontShowAgain() {
    const dontShowAgainCheckbox = document.getElementById('dontShowAgain');
    dontShowAgainCheckbox.addEventListener('change', () => {
        localStorage.setItem('hideAnnouncementModal', dontShowAgainCheckbox.checked);
    });
}

function setupDateInputLimits() {
    const startInput = document.getElementById('startDateInput');
    const endInput = document.getElementById('endDateInput');

    if (startInput && endInput) {
        const now = new Date();
        const currentMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;

        startInput.max = currentMonth;
        endInput.max = currentMonth;
    }
}

export function setupAnnouncement() {
    const infoBtn = document.getElementById('infoBtn');
    const closeModalBtn = document.getElementById('closeModal');
    const modalBackdropElement = document.getElementById('modalBackdrop');
    const infoModalElement = document.getElementById('infoModal');
    const tabLatest = document.getElementById('tabLatest');
    const tabWebsites = document.getElementById('tabWebsites');
    const dontShowAgainCheckbox = document.getElementById('dontShowAgain');

    const openModal = (isAuto = false) => {
        if (isAuto && dontShowAgainCheckbox.checked) return;

        modalBackdropElement.classList.remove('hidden');
        setTimeout(() => {
            modalBackdropElement.classList.add('opacity-100');
            infoModalElement.classList.remove('opacity-0', 'scale-95');
            infoModalElement.classList.add('opacity-100', 'scale-100');
        }, 10);
    };

    const hideModal = () => {
        modalBackdropElement.classList.remove('opacity-100');
        infoModalElement.classList.remove('opacity-100', 'scale-100');
        infoModalElement.classList.add('opacity-0', 'scale-95');
        setTimeout(() => modalBackdropElement.classList.add('hidden'), 300);
    };

    infoBtn.addEventListener('click', () => openModal(false));
    closeModalBtn.addEventListener('click', hideModal);
    tabLatest.addEventListener('click', () => switchTab('latest'));
    tabWebsites.addEventListener('click', () => switchTab('websites'));
    modalBackdropElement.addEventListener('click', (e) => {
        if (e.target === modalBackdropElement) hideModal();
    });

    window.renderArticle = renderArticle;

    initDontShowAgain();
    setupDontShowAgain();
    setupDateInputLimits();
    loadData();

    setTimeout(() => openModal(true), 1200);
}
