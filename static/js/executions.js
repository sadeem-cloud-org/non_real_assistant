// Executions Page JavaScript

let allExecutions = [];
let filteredExecutions = [];

// Load on page ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('Executions page loaded');
    initializeTheme();
    initializeNotifications();
    console.log('Starting to load executions...');
    loadExecutions();

    // Auto-refresh every 10 seconds
    setInterval(loadExecutions, 10000);
});

// Initialize theme
function initializeTheme() {
    const urlParams = new URLSearchParams(window.location.search);
    const theme = urlParams.get('theme') || localStorage.getItem('tablerTheme') || 'light';

    if (theme === 'dark') {
        document.body.setAttribute('data-bs-theme', 'dark');
    } else {
        document.body.removeAttribute('data-bs-theme');
    }

    localStorage.setItem('tablerTheme', theme);

    if (urlParams.get('theme')) {
        window.history.replaceState({}, '', window.location.pathname);
    }
}

// Initialize notifications
async function initializeNotifications() {
    const permission = await notificationManager.checkPermission();
    updateNotificationBell(permission);
}

// Request notification permission
async function requestNotificationPermission(event) {
    event.preventDefault();

    try {
        const permission = await notificationManager.requestPermission();
        updateNotificationBell(permission);

        await fetch('/api/notifications/permission', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ permission })
        });

        if (permission === 'granted') {
            showToast('تم تفعيل الإشعارات بنجاح ✓', 'success');
        }
    } catch (error) {
        console.error('Error requesting permission:', error);
        showToast('حدث خطأ في تفعيل الإشعارات', 'danger');
    }
}

// Update notification bell
function updateNotificationBell(permission) {
    const bell = document.getElementById('notification-bell');
    if (!bell) return;

    const icon = bell.querySelector('i');

    if (permission === 'granted') {
        icon.className = 'ti ti-bell-ringing icon text-green';
        bell.title = 'الإشعارات مفعّلة';
    } else if (permission === 'denied') {
        icon.className = 'ti ti-bell-off icon text-red';
        bell.title = 'الإشعارات مغلقة';
    } else {
        icon.className = 'ti ti-bell icon text-muted';
        bell.title = 'اضغط لتفعيل الإشعارات';
    }
}

// Load all executions
async function loadExecutions() {
    console.log('loadExecutions called');
    try {
        console.log('Fetching /api/executions...');
        const response = await fetch('/api/executions');
        console.log('Response:', response.status, response.ok);

        if (!response.ok) {
            throw new Error('Failed to load executions');
        }

        allExecutions = await response.json();
        console.log('Loaded executions:', allExecutions.length);

        updateStats();
        filterExecutions();

    } catch (error) {
        console.error('Error loading executions:', error);
        const container = document.getElementById('executions-container');
        container.innerHTML = `
            <div class="col-12">
                <div class="empty">
                    <div class="empty-icon">
                        <i class="ti ti-alert-circle icon text-red"></i>
                    </div>
                    <p class="empty-title">حدث خطأ في تحميل السجل</p>
                    <p class="empty-subtitle text-muted">${error.message}</p>
                </div>
            </div>
        `;
    }
}

// Update statistics
function updateStats() {
    const stats = {
        total: allExecutions.length,
        success: 0,
        failed: 0,
        timeout: 0,
        running: 0
    };

    allExecutions.forEach(execution => {
        // API returns 'state', not 'status'
        if (execution.state === 'success') stats.success++;
        else if (execution.state === 'failed') stats.failed++;
        else if (execution.state === 'timeout') stats.timeout++;
        else if (execution.state === 'running' || execution.state === 'pending') stats.running++;
    });

    document.getElementById('stat-total').textContent = stats.total;
    document.getElementById('stat-success').textContent = stats.success;
    document.getElementById('stat-failed').textContent = stats.failed;
    document.getElementById('stat-timeout').textContent = stats.timeout;
}

// Filter executions by status
function filterExecutions() {
    const filter = document.getElementById('status-filter').value;

    if (filter === 'all') {
        filteredExecutions = allExecutions;
    } else {
        // API returns 'state', not 'status'
        filteredExecutions = allExecutions.filter(e => e.state === filter);
    }

    displayExecutions(filteredExecutions);
}

// Display executions
function displayExecutions(executions) {
    console.log('displayExecutions called with', executions.length, 'items');
    const container = document.getElementById('executions-container');

    if (executions.length === 0) {
        container.innerHTML = `
            <div class="col-12">
                <div class="empty">
                    <div class="empty-img">
                        <i class="ti ti-list-details icon" style="font-size: 5rem; color: var(--tblr-muted);"></i>
                    </div>
                    <p class="empty-title">لا يوجد سجل تنفيذ</p>
                    <p class="empty-subtitle text-muted">قم بتشغيل سكريبت لعرض النتائج هنا</p>
                    <div class="empty-action">
                        <a href="/scripts" class="btn btn-primary">
                            <i class="ti ti-code icon"></i>
                            الذهاب للسكريبتات
                        </a>
                    </div>
                </div>
            </div>
        `;
        return;
    }

    container.innerHTML = executions.map(execution => createExecutionCard(execution)).join('');
}

// Create execution card HTML
function createExecutionCard(execution) {
    // API returns 'state', not 'status'
    console.log('Creating card for execution:', execution.id, execution.state);

    try {
        const statusConfig = {
            'success': {color: 'green', icon: 'circle-check', text: 'نجح'},
            'failed': {color: 'red', icon: 'circle-x', text: 'فشل'},
            'timeout': {color: 'yellow', icon: 'clock', text: 'انتهى الوقت'},
            'running': {color: 'blue', icon: 'loader', text: 'قيد التشغيل'},
            'pending': {color: 'blue', icon: 'loader', text: 'قيد التشغيل'}
        };

        // API returns 'state', not 'status'
        const status = statusConfig[execution.state] || statusConfig['failed'];

        return `
            <div class="col-12">
                <div class="card execution-card">
                    <div class="card-status-top bg-${status.color}"></div>
                    <div class="card-body">
                        <div class="row align-items-center">
                            <div class="col-auto">
                                <span class="avatar bg-${status.color}-lt text-${status.color}">
                                    <i class="ti ti-${status.icon}"></i>
                                </span>
                            </div>
                            <div class="col">
                                <h3 class="card-title mb-1">
                                    ${execution.script_name || 'Unknown Script'}
                                </h3>
                                <div class="text-muted">
                                    <span class="badge bg-${status.color} me-2">${status.text}</span>
                                    <span class="me-2">ID: #${execution.id}</span>
                                </div>
                            </div>
                            <div class="col-auto">
                                <button class="btn btn-primary" onclick="viewExecutionDetails(${execution.id})">
                                    <i class="ti ti-eye"></i>
                                    عرض التفاصيل
                                </button>
                            </div>
                        </div>

                        <div class="mt-3 text-muted small">
                            <i class="ti ti-clock icon"></i>
                            بدأ ${formatDateTime(execution.start_time)}
                        </div>
                    </div>
                </div>
            </div>
        `;
    } catch (error) {
        console.error('Error creating card:', error);
        return `<div class="col-12"><div class="alert alert-danger">Error creating card for execution #${execution.id}</div></div>`;
    }
}

// View execution details in modal
function viewExecutionDetails(executionId) {
    const execution = allExecutions.find(e => e.id === executionId);
    if (!execution) return;

    const statusConfig = {
        'success': {color: 'green', icon: 'circle-check', text: 'نجح'},
        'failed': {color: 'red', icon: 'circle-x', text: 'فشل'},
        'timeout': {color: 'yellow', icon: 'clock', text: 'انتهى الوقت'},
        'running': {color: 'blue', icon: 'loader', text: 'قيد التشغيل'},
        'pending': {color: 'blue', icon: 'loader', text: 'قيد التشغيل'}
    };

    // API returns 'state', not 'status'
    const status = statusConfig[execution.state] || statusConfig['failed'];

    const modalBody = document.getElementById('modal-body');
    const execTime = execution.execution_time ?
        `${execution.execution_time.toFixed(3)}s` :
        '-';

    modalBody.innerHTML = `
        <div class="mb-3">
            <h4>
                <span class="badge bg-${status.color} me-2">
                    <i class="ti ti-${status.icon}"></i>
                    ${status.text}
                </span>
                ${escapeHtml(execution.script_name || 'Unknown Script')}
            </h4>
        </div>

        <div class="row mb-3">
            <div class="col-md-4">
                <strong>معرف التنفيذ:</strong><br>
                #${execution.id}
            </div>
            <div class="col-md-4">
                <strong>وقت التنفيذ:</strong><br>
                ${execTime}
            </div>
            <div class="col-md-4">
                <strong>الحالة:</strong><br>
                ${status.text}
            </div>
        </div>

        <div class="row mb-3">
            <div class="col-md-6">
                <strong>بداية التنفيذ:</strong><br>
                ${execution.start_time ? new Date(execution.start_time + 'Z').toLocaleString('ar-EG') : '-'}
            </div>
            <div class="col-md-6">
                <strong>نهاية التنفيذ:</strong><br>
                ${execution.end_time ? new Date(execution.end_time + 'Z').toLocaleString('ar-EG') : 'لم ينته بعد'}
            </div>
        </div>

        ${execution.output && execution.output.trim() ? `
            <div class="mb-3">
                <h5 class="text-green">
                    <i class="ti ti-terminal"></i>
                    Output (stdout):
                </h5>
                <div class="output-box">
${escapeHtml(execution.output)}
                </div>
            </div>
        ` : ''}

        ${execution.error && execution.error.trim() ? `
            <div class="mb-3">
                <h5 class="text-red">
                    <i class="ti ti-alert-triangle"></i>
                    Error (stderr):
                </h5>
                <div class="output-box error-box">
${escapeHtml(execution.error)}
                </div>
            </div>
        ` : ''}

        ${!execution.output && !execution.error ? `
            <div class="alert alert-info">
                <i class="ti ti-info-circle"></i>
                لا يوجد مخرجات أو أخطاء
            </div>
        ` : ''}
    `;

    // Show modal using data-bs-toggle simulation
    const modal = document.getElementById('modal-execution');
    modal.classList.add('show');
    modal.style.display = 'block';
    modal.setAttribute('aria-modal', 'true');
    modal.setAttribute('role', 'dialog');
    modal.removeAttribute('aria-hidden');

    // Add backdrop
    const backdrop = document.createElement('div');
    backdrop.className = 'modal-backdrop fade show';
    backdrop.id = 'execution-modal-backdrop';
    document.body.appendChild(backdrop);
    document.body.classList.add('modal-open');

    // Close handlers
    const closeModal = () => {
        modal.classList.remove('show');
        modal.style.display = 'none';
        modal.setAttribute('aria-hidden', 'true');
        modal.removeAttribute('aria-modal');
        modal.removeAttribute('role');

        const existingBackdrop = document.getElementById('execution-modal-backdrop');
        if (existingBackdrop) {
            existingBackdrop.remove();
        }
        document.body.classList.remove('modal-open');
    };

    // Close on backdrop click
    backdrop.addEventListener('click', closeModal);

    // Close on ALL close buttons (header X and footer button)
    const closeBtns = modal.querySelectorAll('[data-bs-dismiss="modal"]');
    closeBtns.forEach(btn => {
        btn.onclick = closeModal;
    });

    // Also handle Escape key
    const escHandler = (e) => {
        if (e.key === 'Escape') {
            closeModal();
            document.removeEventListener('keydown', escHandler);
        }
    };
    document.addEventListener('keydown', escHandler);
}

// Utility functions
function formatDateTime(dateString) {
    if (!dateString) return '';

    const date = new Date(dateString + 'Z');
    if (isNaN(date.getTime())) return '';

    const now = new Date();
    const diff = Math.floor((now.getTime() - date.getTime()) / 1000);

    if (diff < 60) {
        if (diff < 5) return 'الآن';
        return `منذ ${diff} ثانية`;
    }

    const minutes = Math.floor(diff / 60);
    if (minutes < 60) {
        if (minutes === 1) return 'منذ دقيقة';
        if (minutes === 2) return 'منذ دقيقتين';
        return `منذ ${minutes} دقيقة`;
    }

    const hours = Math.floor(minutes / 60);
    if (hours < 24) {
        if (hours === 1) return 'منذ ساعة';
        if (hours === 2) return 'منذ ساعتين';
        return `منذ ${hours} ساعة`;
    }

    const days = Math.floor(hours / 24);
    if (days < 7) {
        if (days === 1) return 'منذ يوم';
        if (days === 2) return 'منذ يومين';
        return `منذ ${days} يوم`;
    }

    return date.toLocaleDateString('ar-EG');
}

function escapeHtml(text) {
    if (!text) return '';
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

function showToast(message, type = 'success') {
    const bgColors = {
        'success': 'bg-green',
        'danger': 'bg-red',
        'warning': 'bg-yellow',
        'info': 'bg-blue'
    };

    const toastHtml = `
        <div class="toast show align-items-center text-white ${bgColors[type] || 'bg-green'} border-0" role="alert">
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" onclick="this.parentElement.parentElement.remove()"></button>
            </div>
        </div>
    `;

    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container position-fixed bottom-0 start-0 p-3';
        container.style.zIndex = '9999';
        document.body.appendChild(container);
    }

    const toastElement = document.createElement('div');
    toastElement.innerHTML = toastHtml;
    const toastDiv = toastElement.firstElementChild;
    container.appendChild(toastDiv);

    setTimeout(() => {
        toastDiv.classList.remove('show');
        setTimeout(() => toastDiv.remove(), 300);
    }, 3000);
}