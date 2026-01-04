// Theme Management
// Shared across all pages

function setTheme(theme) {
    localStorage.setItem('tablerTheme', theme);
    document.body.setAttribute('data-bs-theme', theme);
    updateThemeButtons(theme);
    console.log('✅ Theme changed to:', theme);
}

function toggleTheme() {
    const currentTheme = document.body.getAttribute('data-bs-theme') || 'light';
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    setTheme(newTheme);
}

function updateThemeButtons(theme) {
    const lightButtons = document.querySelectorAll('.light-theme-toggle');
    const darkButtons = document.querySelectorAll('.dark-theme-toggle');

    if (theme === 'dark') {
        // في الوضع الداكن، أظهر زر الشمس (للتحويل للنهاري)
        lightButtons.forEach(btn => {
            btn.style.display = '';
            btn.classList.remove('d-none');
        });
        darkButtons.forEach(btn => {
            btn.style.display = 'none';
            btn.classList.add('d-none');
        });
    } else {
        // في الوضع الفاتح، أظهر زر القمر (للتحويل للداكن)
        lightButtons.forEach(btn => {
            btn.style.display = 'none';
            btn.classList.add('d-none');
        });
        darkButtons.forEach(btn => {
            btn.style.display = '';
            btn.classList.remove('d-none');
        });
    }
}

function initializeTheme() {
    const urlParams = new URLSearchParams(window.location.search);
    const themeParam = urlParams.get('theme');

    // If theme param exists, update localStorage
    if (themeParam) {
        localStorage.setItem('tablerTheme', themeParam);
    }

    // Get theme from localStorage or default to light
    const theme = localStorage.getItem('tablerTheme') || 'light';

    // Apply theme immediately
    document.body.setAttribute('data-bs-theme', theme);

    // Update buttons visibility
    updateThemeButtons(theme);

    // Remove theme param from URL
    if (themeParam) {
        window.history.replaceState({}, '', window.location.pathname);
    }
}

// Run immediately (synchronously) - not waiting for DOMContentLoaded
initializeTheme();

// Also run on DOMContentLoaded to ensure it works if script loads early
document.addEventListener('DOMContentLoaded', initializeTheme);