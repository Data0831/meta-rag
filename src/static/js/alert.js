export function showAlert(message, iconName = 'info') {
    const alertNotification = document.getElementById('alertNotification');
    const alertBox = document.getElementById('alertBox');
    const alertMessage = document.getElementById('alertMessage');
    const alertIcon = document.getElementById('alertIcon');

    if (!alertNotification || !alertBox || !alertMessage || !alertIcon) return;

    alertMessage.textContent = message;
    alertIcon.textContent = iconName;

    alertNotification.classList.remove('pointer-events-none');
    setTimeout(() => {
        alertBox.classList.remove('opacity-0', 'translate-y-[-20px]', 'scale-95');
        alertBox.classList.add('opacity-100', 'translate-y-0', 'scale-100');
    }, 10);

    setTimeout(() => {
        alertBox.classList.remove('opacity-100', 'translate-y-0', 'scale-100');
        alertBox.classList.add('opacity-0', 'translate-y-[-20px]', 'scale-95');
        setTimeout(() => {
            alertNotification.classList.add('pointer-events-none');
        }, 300);
    }, 3000);
}
