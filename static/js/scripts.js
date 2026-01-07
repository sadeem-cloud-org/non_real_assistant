// Scripts Page JavaScript

let editingScriptId = null;
let allScripts = [];
let codeEditor = null;

// Load on page ready
document.addEventListener('DOMContentLoaded', function() {
    // Theme is initialized by theme.js
    initializeNotifications();
    initializeCodeEditor();
    loadScriptAssistants();
    loadScripts();

    // Modal event listener
    const modalElement = document.getElementById('modal-script');
    if (modalElement) {
        modalElement.addEventListener('hidden.bs.modal', function () {
            closeScriptModal();
        });
    }
});

// Initialize theme
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

// Initialize CodeMirror
function initializeCodeEditor() {
    const textarea = document.getElementById('script-code');
    if (!textarea) return;

    const editorDiv = document.getElementById('code-editor');

    codeEditor = CodeMirror(editorDiv, {
        value: '# اكتب الكود هنا\nprint("Hello World")',
        mode: 'python',
        theme: 'monokai',
        lineNumbers: true,
        indentUnit: 4,
        indentWithTabs: false,
        lineWrapping: false,
        direction: 'ltr',
        rtlMoveVisually: false,
        inputStyle: 'contenteditable'
    });

    // Export to window for external access
    window.codeEditor = codeEditor;

    // Call fix function
    if (typeof fixCodeMirrorDirection === 'function') {
        fixCodeMirrorDirection();
    }
}

// Update code editor mode based on language
function updateCodeEditor() {
    if (!codeEditor) return;

    const language = document.getElementById('script-language').value;
    const modes = {
        'python': {mode: 'python', template: '# اكتب الكود هنا\nprint("Hello World")'},
        'javascript': {mode: 'javascript', template: '// اكتب الكود هنا\nconsole.log("Hello World");'},
        'bash': {mode: 'shell', template: '#!/bin/bash\n# اكتب الكود هنا\necho "Hello World"'}
    };

    const config = modes[language] || modes['python'];
    codeEditor.setOption('mode', config.mode);

    // Only set template if editor is empty or has default content
    const currentValue = codeEditor.getValue().trim();
    if (!editingScriptId && (currentValue === '' || currentValue.includes('Hello World'))) {
        codeEditor.setValue(config.template);
    }
}

// Load all scripts
async function loadScripts() {
    const container = document.getElementById('scripts-container');

    try {
        const response = await fetch('/api/scripts');
        allScripts = await response.json();

        if (!response.ok) {
            throw new Error('Failed to load scripts');
        }

        updateStats();
        displayScripts(allScripts);

    } catch (error) {
        console.error('Error loading scripts:', error);
        container.innerHTML = `
            <div class="col-12">
                <div class="empty">
                    <div class="empty-icon">
                        <i class="ti ti-alert-circle icon text-red"></i>
                    </div>
                    <p class="empty-title">حدث خطأ في تحميل السكريبتات</p>
                </div>
            </div>
        `;
    }
}

// Update statistics
function updateStats() {
    document.getElementById('stat-total').textContent = allScripts.length;

    // Count by assistant if present
    let withAssistant = 0;
    let withoutAssistant = 0;

    allScripts.forEach(script => {
        if (script.assistant_id) {
            withAssistant++;
        } else {
            withoutAssistant++;
        }
    });

    const pythonEl = document.getElementById('stat-python');
    const jsEl = document.getElementById('stat-javascript');
    const bashEl = document.getElementById('stat-bash');

    if (pythonEl) pythonEl.textContent = withAssistant;
    if (jsEl) jsEl.textContent = withoutAssistant;
    if (bashEl) bashEl.textContent = '0';
}

// Display scripts
function displayScripts(scripts) {
    const container = document.getElementById('scripts-container');

    if (scripts.length === 0) {
        container.innerHTML = `
            <div class="col-12">
                <div class="empty">
                    <div class="empty-img">
                        <i class="ti ti-code icon" style="font-size: 5rem; color: var(--tblr-muted);"></i>
                    </div>
                    <p class="empty-title">لا يوجد سكريبتات</p>
                    <p class="empty-subtitle text-muted">ابدأ بإنشاء سكريبت جديد</p>
                    <div class="empty-action">
                        <button class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#modal-script">
                            <i class="ti ti-plus icon"></i>
                            إضافة سكريبت
                        </button>
                    </div>
                </div>
            </div>
        `;
        return;
    }

    container.innerHTML = scripts.map(script => createScriptCard(script)).join('');
}

// Create script card HTML
function createScriptCard(script) {
    const codePreview = script.code ? script.code.substring(0, 200) : 'لا يوجد كود';
    const language = script.language || 'python';
    const langIcons = {
        'python': {icon: 'ti-brand-python', color: 'blue', name: 'Python'},
        'javascript': {icon: 'ti-brand-javascript', color: 'yellow', name: 'JavaScript'},
        'bash': {icon: 'ti-terminal', color: 'green', name: 'Bash'}
    };
    const langConfig = langIcons[language] || langIcons['python'];

    return `
        <div class="col-md-6 col-lg-4">
            <div class="card script-card">
                <div class="card-status-top bg-${langConfig.color}"></div>
                <div class="card-body">
                    <div class="d-flex align-items-center mb-3">
                        <span class="avatar bg-${langConfig.color}-lt text-${langConfig.color} me-3">
                            <i class="ti ${langConfig.icon}"></i>
                        </span>
                        <div class="flex-fill">
                            <h3 class="card-title mb-0">${escapeHtml(script.name)}</h3>
                            <div class="text-muted small">
                                <span class="badge bg-${langConfig.color}-lt text-${langConfig.color}">${langConfig.name}</span>
                                ${script.assistant_name ? `
                                    <i class="ti ti-robot ms-2"></i>
                                    ${escapeHtml(script.assistant_name)}
                                ` : ''}
                            </div>
                        </div>
                    </div>

                    <div class="code-preview mb-3">
                        <code>${escapeHtml(codePreview)}${script.code && script.code.length > 200 ? '...' : ''}</code>
                    </div>

                    ${script.create_time ? `
                        <div class="text-muted small">
                            <i class="ti ti-clock icon"></i>
                            تم الإنشاء ${formatDateTime(script.create_time)}
                        </div>
                    ` : ''}
                </div>

                <div class="card-footer">
                    <div class="btn-list justify-content-center">
                        <button class="btn btn-success btn-sm" onclick="runScript(${script.id})" title="تشغيل">
                            <i class="ti ti-player-play"></i>
                        </button>
                        <button class="btn btn-primary btn-sm" onclick="editScript(${script.id})" title="تعديل">
                            <i class="ti ti-edit"></i>
                        </button>
                        <button class="btn btn-danger btn-sm" onclick="deleteScript(${script.id})" title="حذف">
                            <i class="ti ti-trash"></i>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
}

// Save script
async function saveScript() {
    const name = document.getElementById('script-name').value.trim();
    const code = codeEditor.getValue();

    if (!name) {
        showToast('يرجى إدخال اسم السكريبت', 'warning');
        return;
    }

    if (!code || code.trim() === '') {
        showToast('يرجى كتابة الكود', 'warning');
        return;
    }

    const saveBtn = document.getElementById('btn-save-script');
    const originalText = saveBtn.textContent;

    saveBtn.disabled = true;
    saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>جاري الحفظ...';

    const assistantSelect = document.getElementById('script-assistant');
    const assistantId = assistantSelect ? assistantSelect.value : null;

    const languageSelect = document.getElementById('script-language');
    const language = languageSelect ? languageSelect.value : 'python';

    const scriptData = {
        name: name,
        language: language,
        code: code,
        assistant_id: assistantId ? parseInt(assistantId) : null
    };

    try {
        let response;

        if (editingScriptId) {
            response = await fetch(`/api/scripts/${editingScriptId}`, {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(scriptData)
            });
        } else {
            response = await fetch('/api/scripts', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(scriptData)
            });
        }

        if (response.ok) {
            showToast(editingScriptId ? 'تم تحديث السكريبت بنجاح ✓' : 'تم إضافة السكريبت بنجاح ✓', 'success');

            const modalElement = document.getElementById('modal-script');
            const closeBtn = modalElement.querySelector('[data-bs-dismiss="modal"]');
            if (closeBtn) {
                closeBtn.click();
            }

            setTimeout(async () => {
                await loadScripts();
            }, 300);

        } else {
            const error = await response.json();
            showToast('حدث خطأ: ' + (error.message || error.error || 'فشل في حفظ السكريبت'), 'danger');
            saveBtn.disabled = false;
            saveBtn.textContent = originalText;
        }
    } catch (error) {
        console.error('Error saving script:', error);
        showToast('حدث خطأ في الاتصال', 'danger');
        saveBtn.disabled = false;
        saveBtn.textContent = originalText;
    }
}

// Edit script
async function editScript(scriptId) {
    try {
        const script = allScripts.find(s => s.id === scriptId);

        if (!script) {
            showToast('السكريبت غير موجود', 'danger');
            return;
        }

        // Fill form
        document.getElementById('script-name').value = script.name;

        // Set language
        const languageSelect = document.getElementById('script-language');
        if (languageSelect) {
            languageSelect.value = script.language || 'python';
            updateCodeEditor();  // Update editor mode
        }

        // Set assistant
        const assistantSelect = document.getElementById('script-assistant');
        if (assistantSelect) {
            assistantSelect.value = script.assistant_id || '';
        }

        // Set code editor (after language is set)
        if (codeEditor) {
            codeEditor.setValue(script.code || '');
        }

        // Set edit mode
        editingScriptId = scriptId;
        document.getElementById('modal-title').textContent = 'تعديل السكريبت';
        document.getElementById('btn-save-script').textContent = 'حفظ التعديلات';

        // Show modal
        const triggerBtn = document.querySelector('[data-bs-target="#modal-script"]');
        if (triggerBtn) {
            triggerBtn.click();
        }

    } catch (error) {
        console.error('Error loading script:', error);
        showToast('حدث خطأ في تحميل السكريبت', 'danger');
    }
}

// Run script
async function runScript(scriptId) {
    const script = allScripts.find(s => s.id === scriptId);
    if (!script) return;

    if (!confirm(`هل تريد تشغيل السكريبت "${script.name}"؟`)) {
        return;
    }

    showToast('جاري تشغيل السكريبت...', 'info');

    try {
        const response = await fetch(`/api/scripts/${scriptId}/run`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({})
        });

        if (response.ok) {
            const result = await response.json();
            showToast('تم تشغيل السكريبت بنجاح ✓', 'success');
            console.log('Script result:', result);
        } else {
            const error = await response.json();
            showToast('فشل تشغيل السكريبت: ' + (error.error || 'خطأ غير معروف'), 'danger');
        }
    } catch (error) {
        console.error('Error running script:', error);
        showToast('حدث خطأ في تشغيل السكريبت', 'danger');
    }
}

// Load assistants for dropdown
async function loadScriptAssistants() {
    try {
        const response = await fetch('/api/assistants');
        const assistants = await response.json();

        // Filter only script-type assistants
        const scriptAssistants = assistants.filter(a => a.assistant_type && a.assistant_type.related_action === 'script');

        const assistantSelect = document.getElementById('script-assistant');
        if (assistantSelect) {
            assistantSelect.innerHTML = '<option value="">بدون مساعد</option>';
            scriptAssistants.forEach(a => {
                const option = document.createElement('option');
                option.value = a.id;
                option.textContent = a.name;
                assistantSelect.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error loading assistants:', error);
    }
}

// Delete script
async function deleteScript(scriptId) {
    const script = allScripts.find(s => s.id === scriptId);
    if (!script) return;

    if (!confirm(`هل أنت متأكد من حذف السكريبت "${script.name}" نهائياً؟ لا يمكن التراجع!`)) {
        return;
    }

    try {
        const response = await fetch(`/api/scripts/${scriptId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            showToast('تم حذف السكريبت ✓', 'success');
            await loadScripts();
        } else {
            showToast('حدث خطأ في حذف السكريبت', 'danger');
        }
    } catch (error) {
        console.error('Error deleting script:', error);
        showToast('حدث خطأ في الاتصال', 'danger');
    }
}

// Close modal
function closeScriptModal() {
    document.getElementById('script-name').value = '';

    // Reset language to Python
    const languageSelect = document.getElementById('script-language');
    if (languageSelect) languageSelect.value = 'python';

    const assistantSelect = document.getElementById('script-assistant');
    if (assistantSelect) assistantSelect.value = '';

    if (codeEditor) {
        codeEditor.setOption('mode', 'python');
        codeEditor.setValue('# اكتب الكود هنا\nprint("Hello World")');
    }

    editingScriptId = null;
    document.getElementById('modal-title').textContent = 'إضافة سكريبت جديد';

    const saveBtn = document.getElementById('btn-save-script');
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