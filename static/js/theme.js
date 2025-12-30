// Theme Management
// Shared across all pages

function setTheme(theme) {
    console.log('🎨 setTheme called with:', theme);
    localStorage.setItem('tablerTheme', theme);
    document.body.setAttribute('data-bs-theme', theme);
    console.log('✅ Theme applied. Body attribute:', document.body.getAttribute('data-bs-theme'));
}

function initializeTheme() {
    console.log('🎨 Initializing theme...');
    const urlParams = new URLSearchParams(window.location.search);
    const themeParam = urlParams.get('theme');

    // If theme param exists, update localStorage
    if (themeParam) {
        console.log('🎨 Found theme param:', themeParam);
        localStorage.setItem('tablerTheme', themeParam);
    }

    // Get theme from localStorage or default to light
    const theme = localStorage.getItem('tablerTheme') || 'light';
    console.log('🎨 Current theme:', theme);

    // Apply theme
    if (theme === 'dark') {
        document.body.setAttribute('data-bs-theme', 'dark');
    } else {
        document.body.setAttribute('data-bs-theme', 'light');
    }

    console.log('✅ Theme initialized. Body attribute:', document.body.getAttribute('data-bs-theme'));

    // Remove theme param from URL
    if (themeParam) {
        window.history.replaceState({}, '', window.location.pathname);
    }
}

// Auto-initialize on load
console.log('🎨 theme.js loaded. readyState:', document.readyState);
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeTheme);
} else {
    initializeTheme();
}