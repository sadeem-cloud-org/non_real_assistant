// Assistants Page JavaScript

let editingAssistantId = null;
let allAssistants = [];
let allAssistantTypes = [];
let allNotifyTemplates = [];

// Load on page ready
document.addEventListener('DOMContentLoaded', function() {
    initializeTheme();
    loadAssistantTypes();
    loadNotifyTemplates();
    loadAssistants();

    // Modal event listener
    const modalElement = document.getElementById('modal-assistant');
    if (modalElement) {
        modalElement.addEventListener('hidden.bs.modal', function () {
            closeAssistantModal();
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

// Load assistant types from API
async function loadAssistantTypes() {
    try {
        const response = await fetch('/api/assistant-types');
        allAssistantTypes = await response.json();
        populateAssistantTypes();
    } catch (error) {
        console.error('Error loading assistant types:', error);
    }
}

// Populate assistant types dropdown
function populateAssistantTypes() {
    const select = document.getElementById('assistant-type');
    if (!select) return;

    select.innerHTML = '';

    // Only 2 types: task notifications and script execution
    const typeNames = {
        'task_notify': 'تنبيه بالمهام',
        'script_runner': 'تشغيل سكريبتات'
    };

    allAssistantTypes.forEach(type => {
        const option = document.createElement('option');
        option.value = type.id;
        option.dataset.name = type.name;
        option.dataset.relatedAction = type.related_action;
        option.textContent = typeNames[type.name] || type.name;
        select.appendChild(option);
    });

    // Update hint based on selection
    select.addEventListener('change', updateTypeHint);
}

function updateTypeHint() {
    const select = document.getElementById('assistant-type');
    const hint = document.getElementById('type-hint');
    const selectedOption = select.options[select.selectedIndex];

    if (selectedOption && selectedOption.dataset.relatedAction) {
        const action = selectedOption.dataset.relatedAction;
        if (action === 'task') {
            hint.textContent = 'هذا المساعد يعمل مع المهام';
        } else if (action === 'script') {
            hint.textContent = 'هذا المساعد يعمل مع السكريبتات';
        }
    }
}

// Load notify templates from API
async function loadNotifyTemplates() {
    try {
        const response = await fetch('/api/notify-templates');
        allNotifyTemplates = await response.json();
        populateNotifyTemplates();
    } catch (error) {
        console.error('Error loading notify templates:', error);
    }
}

// Populate notify templates dropdown
function populateNotifyTemplates() {
    const select = document.getElementById('assistant-notify-template');
    if (!select) return;

    // Keep the default option
    select.innerHTML = '<option value="">القالب الافتراضي</option>';

    allNotifyTemplates.forEach(template => {
        const option = document.createElement('option');
        option.value = template.id;
        option.textContent = template.name;
        select.appendChild(option);
    });
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
    let taskAssistants = 0;
    let scriptAssistants = 0;
    let scheduledCount = 0;

    allAssistants.forEach(assistant => {
        // Check assistant type
        if (assistant.assistant_type) {
            if (assistant.assistant_type.related_action === 'task') {
                taskAssistants++;
            } else if (assistant.assistant_type.related_action === 'script') {
                scriptAssistants++;
            }
        }

        // Check if scheduled
        if (assistant.run_every) {
            scheduledCount++;
        }
    });

    document.getElementById('stat-total').textContent = allAssistants.length;
    document.getElementById('stat-tasks').textContent = taskAssistants;
    document.getElementById('stat-scripts').textContent = scriptAssistants;
    document.getElementById('stat-scheduled').textContent = scheduledCount;
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
    // Only 2 types: task notifications and script execution
    const typeIcons = {
        'task_notify': 'bell-ringing',
        'script_runner': 'code'
    };

    const typeNames = {
        'task_notify': 'تنبيه بالمهام',
        'script_runner': 'تشغيل سكريبتات'
    };

    const runEveryNames = {
        'minute': 'كل دقيقة',
        'hourly': 'كل ساعة',
        'daily': 'يومياً',
        'weekly': 'أسبوعياً',
        'monthly': 'شهرياً'
    };

    const typeName = assistant.assistant_type ? (typeNames[assistant.assistant_type.name] || assistant.assistant_type.name) : 'مخصص';
    const typeIcon = assistant.assistant_type ? (typeIcons[assistant.assistant_type.name] || 'robot') : 'robot';
    const relatedAction = assistant.assistant_type ? assistant.assistant_type.related_action : 'task';
    const actionColor = relatedAction === 'task' ? 'green' : 'cyan';

    return `
        <div class="col-md-6 col-lg-4">
            <div class="card assistant-card">
                <div class="card-status-top bg-${actionColor}"></div>
                <div class="card-body text-center">
                    <div class="mb-3">
                        <span class="avatar avatar-xl assistant-avatar bg-${actionColor}-lt text-${actionColor}">
                            <i class="ti ti-${typeIcon}"></i>
                        </span>
                    </div>
                    <h3 class="card-title mb-1">${escapeHtml(assistant.name)}</h3>
                    <div class="text-muted mb-3">${typeName}</div>

                    <div class="d-flex justify-content-center gap-2 mb-3 flex-wrap">
                        <span class="badge bg-${actionColor}">
                            <i class="ti ti-${relatedAction === 'task' ? 'subtask' : 'code'}"></i>
                            ${relatedAction === 'task' ? 'مهام' : 'سكريبتات'}
                        </span>

                        ${assistant.telegram_notify ? `
                            <span class="badge bg-info">
                                <i class="ti ti-brand-telegram"></i>
                                تليجرام
                            </span>
                        ` : ''}

                        ${assistant.email_notify ? `
                            <span class="badge bg-warning">
                                <i class="ti ti-mail"></i>
                                إيميل
                            </span>
                        ` : ''}

                        ${assistant.run_every ? `
                            <span class="badge bg-purple">
                                <i class="ti ti-calendar-event"></i>
                                ${runEveryNames[assistant.run_every] || assistant.run_every}
                            </span>
                        ` : ''}
                    </div>

                    <div class="d-flex justify-content-center gap-3 text-muted small mb-3">
                        <span>
                            <i class="ti ti-subtask"></i>
                            ${assistant.tasks_count || 0} مهام
                        </span>
                        <span>
                            <i class="ti ti-code"></i>
                            ${assistant.scripts_count || 0} سكريبتات
                        </span>
                    </div>

                    ${assistant.create_time ? `
                        <div class="text-muted small">
                            <i class="ti ti-clock icon"></i>
                            تم الإنشاء ${formatDateTime(assistant.create_time)}
                        </div>
                    ` : ''}
                </div>

                <div class="card-footer">
                    <div class="btn-list justify-content-center">
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
    const assistantTypeId = document.getElementById('assistant-type').value;

    if (!name) {
        showToast('يرجى إدخال اسم المساعد', 'warning');
        return;
    }

    if (!assistantTypeId) {
        showToast('يرجى اختيار نوع المساعد', 'warning');
        return;
    }

    const saveBtn = document.getElementById('btn-save-assistant');
    const originalText = saveBtn.textContent;

    saveBtn.disabled = true;
    saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>جاري الحفظ...';

    const runEvery = document.getElementById('assistant-run-every').value;
    const notifyTemplateId = document.getElementById('assistant-notify-template').value;

    const assistantData = {
        name: name,
        assistant_type_id: parseInt(assistantTypeId),
        telegram_notify: document.getElementById('assistant-telegram-notify').checked,
        email_notify: document.getElementById('assistant-email-notify').checked,
        notify_template_id: notifyTemplateId ? parseInt(notifyTemplateId) : null,
        run_every: runEvery || null
    };

    // Calculate next_run_time if scheduling
    if (runEvery) {
        assistantData.next_run_time = new Date().toISOString();
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
            showToast(editingAssistantId ? 'تم تحديث المساعد بنجاح' : 'تم إضافة المساعد بنجاح', 'success');

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

        // Fill form
        document.getElementById('assistant-name').value = assistant.name;
        document.getElementById('assistant-type').value = assistant.assistant_type_id;
        document.getElementById('assistant-telegram-notify').checked = assistant.telegram_notify;
        document.getElementById('assistant-email-notify').checked = assistant.email_notify;
        document.getElementById('assistant-notify-template').value = assistant.notify_template_id || '';
        document.getElementById('assistant-run-every').value = assistant.run_every || '';

        // Set edit mode
        editingAssistantId = assistantId;
        document.getElementById('modal-title').textContent = 'تعديل المساعد';
        document.getElementById('btn-save-assistant').textContent = 'حفظ التعديلات';

        // Show modal by clicking the trigger button
        const triggerBtn = document.querySelector('[data-bs-target="#modal-assistant"]');
        if (triggerBtn) {
            triggerBtn.click();
        }

    } catch (error) {
        console.error('Error loading assistant:', error);
        showToast('حدث خطأ في تحميل المساعد', 'danger');
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
            showToast('تم حذف المساعد', 'success');
            await loadAssistants();
        } else {
            showToast('حدث خطأ في حذف المساعد', 'danger');
        }
    } catch (error) {
        console.error('Error deleting assistant:', error);
        showToast('حدث خطأ في الاتصال', 'danger');
    }
}

// View assistant details - redirect to relevant page based on type
function viewAssistantDetails(assistantId) {
    const assistant = allAssistants.find(a => a.id === assistantId);
    if (!assistant) return;

    // Redirect to tasks or scripts page filtered by this assistant
    const relatedAction = assistant.assistant_type ? assistant.assistant_type.related_action : 'task';
    if (relatedAction === 'task') {
        window.location.href = `/tasks?assistant_id=${assistantId}`;
    } else {
        window.location.href = `/scripts?assistant_id=${assistantId}`;
    }
}

// Close modal
function closeAssistantModal() {
    document.getElementById('assistant-name').value = '';
    document.getElementById('assistant-type').selectedIndex = 0;
    document.getElementById('assistant-telegram-notify').checked = true;
    document.getElementById('assistant-email-notify').checked = false;
    document.getElementById('assistant-notify-template').value = '';
    document.getElementById('assistant-run-every').value = '';

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
