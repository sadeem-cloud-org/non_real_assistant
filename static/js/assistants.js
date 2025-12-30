// Assistants Page JavaScript

let editingAssistantId = null;
let allAssistants = [];
let allScripts = [];

// Load on page ready
document.addEventListener('DOMContentLoaded', function() {
    initializeTheme();
    initializeNotifications();
    loadAssistants();
    loadScripts();  // Load scripts for dropdown

    // Schedule checkbox toggle
    const scheduledCheckbox = document.getElementById('assistant-scheduled');
    if (scheduledCheckbox) {
        scheduledCheckbox.addEventListener('change', function() {
            const scheduleConfig = document.getElementById('schedule-config');
            scheduleConfig.style.display = this.checked ? 'block' : 'none';
        });
    }

    // Modal event listener
    const modalElement = document.getElementById('modal-assistant');
    if (modalElement) {
        modalElement.addEventListener('hidden.bs.modal', function () {
            closeAssistantModal();
        });

        // Populate scripts when modal opens
        modalElement.addEventListener('show.bs.modal', function() {
            populateScriptsList();
        });
    }
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

// Load scripts for dropdown
async function loadScripts() {
    try {
        const response = await fetch('/api/scripts');
        allScripts = await response.json();
    } catch (error) {
        console.error('Error loading scripts:', error);
    }
}

// Populate scripts dropdown
function populateScriptsList() {
    const select = document.getElementById('assistant-script');
    if (!select) return;

    // Clear and add empty option
    select.innerHTML = '<option value="">اختر سكريبت...</option>';

    allScripts.forEach(script => {
        const languageEmoji = {
            'python': '🐍',
            'javascript': '📜',
            'bash': '💻'
        }[script.language] || '📄';

        const option = document.createElement('option');
        option.value = script.id;
        option.textContent = `${languageEmoji} ${script.name}`;
        select.appendChild(option);
    });
}

// Toggle script selector based on assistant type
function toggleScriptSelector() {
    const type = document.getElementById('assistant-type').value;
    const scriptSelector = document.getElementById('script-selector');

    if (type === 'automation') {
        scriptSelector.style.display = 'block';
    } else {
        scriptSelector.style.display = 'none';
        document.getElementById('assistant-script').value = '';
    }
}

// Load all assistants
async function loadAssistants() {
    const container = document.getElementById('assistants-container');

    try {
        const response = await fetch('/api/assistants');
        allAssistants = await response.json();

        if (!response.ok) {
            throw new Error('Failed to load assistants');
        }

        updateStats();
        displayAssistants(allAssistants);

    } catch (error) {
        console.error('Error loading assistants:', error);
        container.innerHTML = `
            <div class="col-12">
                <div class="empty">
                    <div class="empty-icon">
                        <i class="ti ti-alert-circle icon text-red"></i>
                    </div>
                    <p class="empty-title">حدث خطأ في تحميل المساعدين</p>
                </div>
            </div>
        `;
    }
}

// Update statistics
function updateStats() {
    const stats = {
        total: allAssistants.length,
        active: 0,
        paused: 0,
        scheduled: 0
    };

    allAssistants.forEach(assistant => {
        if (assistant.is_enabled) stats.active++;
        else stats.paused++;

        const settings = assistant.settings || {};
        if (settings.schedule_type) stats.scheduled++;
    });

    document.getElementById('stat-total').textContent = stats.total;
    document.getElementById('stat-active').textContent = stats.active;
    document.getElementById('stat-paused').textContent = stats.paused;
    document.getElementById('stat-scheduled').textContent = stats.scheduled;
}

// Display assistants
function displayAssistants(assistants) {
    const container = document.getElementById('assistants-container');

    if (assistants.length === 0) {
        container.innerHTML = `
            <div class="col-12">
                <div class="empty">
                    <div class="empty-img">
                        <i class="ti ti-robot icon" style="font-size: 5rem; color: var(--tblr-muted);"></i>
                    </div>
                    <p class="empty-title">لا يوجد مساعدين</p>
                    <p class="empty-subtitle text-muted">ابدأ بإنشاء مساعدك الافتراضي الأول</p>
                    <div class="empty-action">
                        <button class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#modal-assistant">
                            <i class="ti ti-plus icon"></i>
                            إضافة مساعد
                        </button>
                    </div>
                </div>
            </div>
        `;
        return;
    }

    container.innerHTML = assistants.map(assistant => createAssistantCard(assistant)).join('');
}

// Create assistant card HTML
function createAssistantCard(assistant) {
    // Get settings
    const settings = assistant.settings || {};
    const type = settings.type || 'custom';
    const description = settings.description || '';
    const priority = settings.priority || 'medium';

    const statusClass = assistant.is_enabled ? 'success' : 'warning';
    const statusText = assistant.is_enabled ? 'نشط' : 'متوقف';
    const statusIcon = assistant.is_enabled ? 'circle-check' : 'player-pause';

    const typeIcons = {
        'task_manager': 'checkbox',
        'reminder': 'bell',
        'automation': 'robot',
        'data_collector': 'database',
        'custom': 'adjustments'
    };

    const typeNames = {
        'task_manager': 'مدير مهام',
        'reminder': 'تذكيرات',
        'automation': 'أتمتة',
        'data_collector': 'جمع بيانات',
        'custom': 'مخصص'
    };

    const typeIcon = typeIcons[type] || 'robot';
    const typeName = typeNames[type] || type;

    const priorityClass = priority === 'high' ? 'danger' : priority === 'medium' ? 'warning' : 'info';

    const hasSchedule = settings.schedule_type && settings.schedule_value;

    // Check if linked to script
    const script = allScripts.find(s => s.id === assistant.script_id);
    const scriptBadge = script ? `
        <span class="badge bg-cyan">
            <i class="ti ti-code"></i>
            ${escapeHtml(script.name)}
        </span>
    ` : '';

    return `
        <div class="col-md-6 col-lg-4">
            <div class="card assistant-card">
                <div class="card-status-top bg-${statusClass}"></div>
                <div class="card-body text-center">
                    <div class="mb-3">
                        <span class="avatar avatar-xl assistant-avatar bg-${statusClass}-lt text-${statusClass}">
                            <i class="ti ti-${typeIcon}"></i>
                        </span>
                    </div>
                    <h3 class="card-title mb-1">${escapeHtml(assistant.name)}</h3>
                    <div class="text-muted mb-3">${typeName}</div>
                    
                    ${description ? `
                        <p class="text-muted small mb-3">${escapeHtml(description)}</p>
                    ` : ''}
                    
                    <div class="d-flex justify-content-center gap-2 mb-3">
                        <span class="badge bg-${statusClass}">
                            <i class="ti ti-${statusIcon}"></i>
                            ${statusText}
                        </span>
                        <span class="badge bg-${priorityClass}">
                            ${priority === 'high' ? 'أولوية عالية' : priority === 'medium' ? 'أولوية متوسطة' : 'أولوية منخفضة'}
                        </span>
                        ${hasSchedule ? `
                            <span class="badge bg-purple">
                                <i class="ti ti-calendar-event"></i>
                                مجدول
                            </span>
                        ` : ''}
                        ${scriptBadge}
                    </div>
                    
                    ${assistant.created_at ? `
                        <div class="text-muted small">
                            <i class="ti ti-clock icon"></i>
                            تم الإنشاء ${formatDateTime(assistant.created_at)}
                        </div>
                    ` : ''}
                </div>
                
                <div class="card-footer">
                    <div class="btn-list justify-content-center">
                        ${assistant.is_enabled ? `
                            <button class="btn btn-warning btn-sm" onclick="pauseAssistant(${assistant.id})" title="إيقاف">
                                <i class="ti ti-player-pause"></i>
                            </button>
                        ` : `
                            <button class="btn btn-success btn-sm" onclick="activateAssistant(${assistant.id})" title="تشغيل">
                                <i class="ti ti-player-play"></i>
                            </button>
                        `}
                        <button class="btn btn-primary btn-sm" onclick="editAssistant(${assistant.id})" title="تعديل">
                            <i class="ti ti-edit"></i>
                        </button>
                        <button class="btn btn-info btn-sm" onclick="viewAssistantDetails(${assistant.id})" title="التفاصيل">
                            <i class="ti ti-info-circle"></i>
                        </button>
                        <button class="btn btn-danger btn-sm" onclick="deleteAssistant(${assistant.id})" title="حذف">
                            <i class="ti ti-trash"></i>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
}

// Save assistant
async function saveAssistant() {
    const name = document.getElementById('assistant-name').value.trim();
    const selectedType = document.getElementById('assistant-type').value;

    if (!name) {
        showToast('يرجى إدخال اسم المساعد', 'warning');
        return;
    }

    // Validate automation type has a script
    if (selectedType === 'automation') {
        const scriptId = document.getElementById('assistant-script').value;
        if (!scriptId) {
            showToast('يجب اختيار سكريبت لمساعد الأتمتة', 'warning');
            return;
        }
    }

    const saveBtn = document.getElementById('btn-save-assistant');
    const originalText = saveBtn.textContent;

    saveBtn.disabled = true;
    saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>جاري الحفظ...';

    // Map type to assistant_type_id (hardcoded for now)
    const typeMap = {
        'task_manager': 1,
        'reminder': 2,
        'automation': 3,
        'data_collector': 4,
        'custom': 5
    };

    const assistantTypeId = typeMap[selectedType] || 1;

    const assistantData = {
        name: name,
        assistant_type_id: assistantTypeId,
        is_enabled: document.getElementById('assistant-status').value === 'active',
        settings: {
            description: document.getElementById('assistant-description').value.trim(),
            priority: document.getElementById('assistant-priority').value,
            type: selectedType  // Store original type for display
        }
    };

    // Add script_id if automation type
    if (selectedType === 'automation') {
        assistantData.script_id = parseInt(document.getElementById('assistant-script').value);
    }

    // Schedule configuration
    if (document.getElementById('assistant-scheduled').checked) {
        assistantData.settings.schedule_type = document.getElementById('schedule-type').value;
        assistantData.settings.schedule_value = document.getElementById('schedule-value').value.trim();
    }

    try {
        let response;

        if (editingAssistantId) {
            response = await fetch(`/api/assistants/${editingAssistantId}`, {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(assistantData)
            });
        } else {
            response = await fetch('/api/assistants', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(assistantData)
            });
        }

        if (response.ok) {
            showToast(editingAssistantId ? 'تم تحديث المساعد بنجاح ✓' : 'تم إضافة المساعد بنجاح ✓', 'success');

            const modalElement = document.getElementById('modal-assistant');
            const closeBtn = modalElement.querySelector('[data-bs-dismiss="modal"]');
            if (closeBtn) {
                closeBtn.click();
            }

            setTimeout(async () => {
                await loadAssistants();
            }, 300);

        } else {
            const error = await response.json();
            showToast('حدث خطأ: ' + (error.message || error.error || 'فشل في حفظ المساعد'), 'danger');
            saveBtn.disabled = false;
            saveBtn.textContent = originalText;
        }
    } catch (error) {
        console.error('Error saving assistant:', error);
        showToast('حدث خطأ في الاتصال', 'danger');
        saveBtn.disabled = false;
        saveBtn.textContent = originalText;
    }
}

// Edit assistant
async function editAssistant(assistantId) {
    try {
        const assistant = allAssistants.find(a => a.id === assistantId);

        if (!assistant) {
            showToast('المساعد غير موجود', 'danger');
            return;
        }

        const settings = assistant.settings || {};

        // Fill form
        document.getElementById('assistant-name').value = assistant.name;
        document.getElementById('assistant-description').value = settings.description || '';
        document.getElementById('assistant-type').value = settings.type || 'custom';
        document.getElementById('assistant-status').value = assistant.is_enabled ? 'active' : 'paused';
        document.getElementById('assistant-priority').value = settings.priority || 'medium';

        // Show/hide script selector based on type
        toggleScriptSelector();

        // Set script if automation type
        if (settings.type === 'automation' && assistant.script_id) {
            document.getElementById('assistant-script').value = assistant.script_id;
        }

        // Schedule
        const scheduledCheckbox = document.getElementById('assistant-scheduled');
        const scheduleConfig = document.getElementById('schedule-config');

        if (settings.schedule_type) {
            scheduledCheckbox.checked = true;
            scheduleConfig.style.display = 'block';
            document.getElementById('schedule-type').value = settings.schedule_type;
            document.getElementById('schedule-value').value = settings.schedule_value || '';
        } else {
            scheduledCheckbox.checked = false;
            scheduleConfig.style.display = 'none';
        }

        // Set edit mode
        editingAssistantId = assistantId;
        document.getElementById('modal-title').textContent = 'تعديل المساعد';
        document.getElementById('btn-save-assistant').textContent = 'حفظ التعديلات';

        // Show modal
        const modalElement = document.getElementById('modal-assistant');
        const triggerBtn = document.querySelector('[data-bs-target="#modal-assistant"]');
        if (triggerBtn) {
            triggerBtn.click();
        }

    } catch (error) {
        console.error('Error loading assistant:', error);
        showToast('حدث خطأ في تحميل المساعد', 'danger');
    }
}

// Pause assistant
async function pauseAssistant(assistantId) {
    try {
        const response = await fetch(`/api/assistants/${assistantId}`, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({is_enabled: false})
        });

        if (response.ok) {
            showToast('تم إيقاف المساعد', 'warning');
            await loadAssistants();
        } else {
            showToast('حدث خطأ', 'danger');
        }
    } catch (error) {
        console.error('Error pausing assistant:', error);
        showToast('حدث خطأ في الاتصال', 'danger');
    }
}

// Activate assistant
async function activateAssistant(assistantId) {
    try {
        const response = await fetch(`/api/assistants/${assistantId}`, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({is_enabled: true})
        });

        if (response.ok) {
            showToast('تم تشغيل المساعد ✓', 'success');
            await loadAssistants();
        } else {
            showToast('حدث خطأ', 'danger');
        }
    } catch (error) {
        console.error('Error activating assistant:', error);
        showToast('حدث خطأ في الاتصال', 'danger');
    }
}

// Delete assistant
async function deleteAssistant(assistantId) {
    if (!confirm('هل أنت متأكد من حذف هذا المساعد نهائياً؟ لا يمكن التراجع!')) {
        return;
    }

    try {
        const response = await fetch(`/api/assistants/${assistantId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            showToast('تم حذف المساعد ✓', 'success');
            await loadAssistants();
        } else {
            showToast('حدث خطأ في حذف المساعد', 'danger');
        }
    } catch (error) {
        console.error('Error deleting assistant:', error);
        showToast('حدث خطأ في الاتصال', 'danger');
    }
}

// View assistant details
function viewAssistantDetails(assistantId) {
    const assistant = allAssistants.find(a => a.id === assistantId);
    if (!assistant) return;

    // TODO: Show detailed modal with logs, tasks, etc.
    showToast('عرض التفاصيل - قريباً!', 'info');
}

// Close modal
function closeAssistantModal() {
    document.getElementById('assistant-name').value = '';
    document.getElementById('assistant-description').value = '';
    document.getElementById('assistant-type').value = 'task_manager';
    document.getElementById('assistant-status').value = 'active';
    document.getElementById('assistant-priority').value = 'medium';
    document.getElementById('assistant-scheduled').checked = false;
    document.getElementById('schedule-config').style.display = 'none';
    document.getElementById('schedule-type').value = 'interval';
    document.getElementById('schedule-value').value = '';
    document.getElementById('assistant-script').value = '';
    document.getElementById('script-selector').style.display = 'none';

    editingAssistantId = null;
    document.getElementById('modal-title').textContent = 'إضافة مساعد جديد';

    const saveBtn = document.getElementById('btn-save-assistant');
    saveBtn.textContent = 'حفظ';
    saveBtn.disabled = false;
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