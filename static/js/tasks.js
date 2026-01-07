// Tasks Page JavaScript

let editingTaskId = null;
let allTasks = [];
// Translation object - will be populated from HTML template
const t = window.translations || {};

// Load on page ready
document.addEventListener('DOMContentLoaded', function () {
    initializeDateTimePickers();
    initializeTheme();
    loadTasks();

    // Modal event listener
    const modalElement = document.getElementById('modal-task');
    if (modalElement) {
        modalElement.addEventListener('hidden.bs.modal', function () {
            closeTaskModal();
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

// Initialize Flatpickr
function initializeDateTimePickers() {
    const dateTimeConfig = {
        enableTime: true,
        time_24hr: true,
        dateFormat: "d/m/Y H:i",
        altInput: true,
        altFormat: "d/m/Y H:i",
        allowInput: true,  // Allow manual input
        minuteIncrement: 1,
        locale: {
            firstDayOfWeek: 6,
            weekdays: {
                shorthand: ['أحد', 'إثنين', 'ثلاثاء', 'أربعاء', 'خميس', 'جمعة', 'سبت'],
                longhand: ['الأحد', 'الإثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت']
            },
            months: {
                shorthand: ['يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو', 'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر'],
                longhand: ['يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو', 'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر']
            }
        }
    };

    flatpickr("#task-time", dateTimeConfig);
    loadAssistants();
}

// Load assistants for dropdown
async function loadAssistants() {
    try {
        const response = await fetch('/api/assistants');
        const assistants = await response.json();

        // Filter only task-type assistants
        const taskAssistants = assistants.filter(a => a.assistant_type && a.assistant_type.related_action === 'task');

        const taskAssistantSelect = document.getElementById('task-assistant');
        const filterAssistantSelect = document.getElementById('filter-assistant');

        [taskAssistantSelect, filterAssistantSelect].forEach(select => {
            if (select) {
                const firstOption = select.options[0];
                select.innerHTML = '';
                if (firstOption) select.appendChild(firstOption);

                taskAssistants.forEach(a => {
                    const option = document.createElement('option');
                    option.value = a.id;
                    option.textContent = a.name;
                    select.appendChild(option);
                });
            }
        });
    } catch (error) {
        console.error('Error loading assistants:', error);
    }
}

// Load all tasks
async function loadTasks() {
    const container = document.getElementById('tasks-container');
    const statusFilter = document.getElementById('filter-status');
    const assistantFilter = document.getElementById('filter-assistant');

    try {
        let url = '/api/tasks';
        const params = new URLSearchParams();

        if (statusFilter && statusFilter.value) params.append('status', statusFilter.value);
        if (assistantFilter && assistantFilter.value) params.append('assistant_id', assistantFilter.value);

        if (params.toString()) url += '?' + params.toString();

        const response = await fetch(url);
        allTasks = await response.json();

        if (!response.ok) {
            throw new Error('Failed to load tasks');
        }

        updateStats();
        displayTasks(allTasks);

    } catch (error) {
        console.error('Error loading tasks:', error);
        container.innerHTML = `
            <div class="col-12">
                <div class="empty">
                    <div class="empty-icon">
                        <i class="ti ti-alert-circle icon text-red"></i>
                    </div>
                    <p class="empty-title">${t.no_recent_operations || 'حدث خطأ في تحميل المهام'}</p>
                </div>
            </div>
        `;
    }
}

// Update statistics
function updateStats() {
    const stats = {
        total: 0,
        pending: 0,
        completed: 0,
        late: 0
    };

    allTasks.forEach(task => {
        stats.total++;
        const status = task.status;
        if (status === 'pending') {
            stats.pending++;
        } else if (status === 'overdue' || status === 'late') {
            stats.late++;
        } else if (status === 'completed') {
            stats.completed++;
        }
    });

    const totalEl = document.getElementById('stat-total');
    const pendingEl = document.getElementById('stat-pending');
    const completedEl = document.getElementById('stat-completed');
    const lateEl = document.getElementById('stat-late');

    if (totalEl) totalEl.textContent = stats.total;
    if (pendingEl) pendingEl.textContent = stats.pending;
    if (completedEl) completedEl.textContent = stats.completed;
    if (lateEl) lateEl.textContent = stats.late;
}

// Display tasks
function displayTasks(tasks) {
    const container = document.getElementById('tasks-container');

    if (tasks.length === 0) {
        container.innerHTML = `
            <div class="col-12">
                <div class="empty">
                    <div class="empty-icon">
                        <i class="ti ti-mood-smile icon"></i>
                    </div>
                    <p class="empty-title">${t.no_recent_operations || 'لا توجد مهام'}</p>
                    <p class="empty-subtitle text-muted">${t.no_recent_operations || 'ابدأ بإضافة مهمة جديدة'}</p>
                </div>
            </div>
        `;
        return;
    }

    container.innerHTML = tasks.map(task => createTaskCard(task)).join('');
}

// Create task card HTML
function createTaskCard(task) {
    const statusClass = task.status === 'pending' ? 'cyan' :
        task.status === 'overdue' ? 'orange' :
            task.status === 'completed' ? 'green' : 'red';
    const statusText = getStatusText(task.status);

    return `
        <div class="col-md-6 col-lg-4">
            <div class="card task-card">
                <div class="card-status-top bg-${statusClass}"></div>
                <div class="card-body">
                    <div class="d-flex align-items-center mb-3">
                        <div class="badge bg-${statusClass}-lt">${statusText}</div>
                        ${task.assistant_name ? `
                            <span class="badge bg-blue-lt ms-2">
                                <i class="ti ti-robot"></i>
                                ${escapeHtml(task.assistant_name)}
                            </span>
                        ` : ''}
                        ${task.notify_sent ? `
                            <span class="badge bg-green-lt ms-2" title="تم إرسال الإشعار">
                                <i class="ti ti-bell-check"></i>
                            </span>
                        ` : ''}
                    </div>

                    <h3 class="card-title mb-2">${escapeHtml(task.name)}</h3>

                    ${task.description ? `
                        <p class="text-muted mb-3">${escapeHtml(task.description)}</p>
                    ` : ''}

                    <div class="text-muted small mb-3">
                        ${task.time ? `
                            <div class="mb-1">
                                <i class="ti ti-bell icon"></i>
                                موعد التنبيه: ${formatDateForDisplay(task.time)}
                            </div>
                        ` : ''}
                        ${task.create_time ? `
                            <div>
                                <i class="ti ti-clock icon"></i>
                                ${formatDateTime(task.create_time)}
                            </div>
                        ` : ''}
                    </div>
                </div>

                <div class="card-footer">
                    <div class="btn-list justify-content-center">
                        ${task.status !== 'completed' && task.status !== 'cancelled' ? `
                            <button class="btn btn-success btn-sm" onclick="completeTask(${task.id})" title="إكمال">
                                <i class="ti ti-check"></i>
                            </button>
                        ` : ''}
                        <button class="btn btn-primary btn-sm" onclick="editTask(${task.id})" title="تعديل">
                            <i class="ti ti-edit"></i>
                        </button>
                        ${task.status !== 'cancelled' && task.status !== 'completed' ? `
                            <button class="btn btn-warning btn-sm" onclick="cancelTask(${task.id})" title="إلغاء">
                                <i class="ti ti-x"></i>
                            </button>
                        ` : ''}
                        <button class="btn btn-danger btn-sm" onclick="deleteTask(${task.id})" title="حذف نهائي">
                            <i class="ti ti-trash"></i>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
}

// Search tasks
function searchTasks() {
    const searchTerm = document.getElementById('search-input').value.toLowerCase();

    if (!searchTerm) {
        displayTasks(allTasks);
        return;
    }

    const filtered = allTasks.filter(task =>
        task.title.toLowerCase().includes(searchTerm) ||
        (task.description && task.description.toLowerCase().includes(searchTerm))
    );

    displayTasks(filtered);
}

// Clear search
function clearSearch() {
    document.getElementById('search-input').value = '';
    displayTasks(allTasks);
}

// Complete task
async function completeTask(taskId) {
    if (!confirm('هل تريد تعليم هذه المهمة كمكتملة؟')) {
        return;
    }

    try {
        const response = await fetch(`/api/tasks/${taskId}/complete`, {
            method: 'POST'
        });

        if (response.ok) {
            showToast('تم إكمال المهمة بنجاح ✓', 'success');
            await loadTasks();
        } else {
            showToast('حدث خطأ في تحديث المهمة', 'danger');
        }
    } catch (error) {
        console.error('Error completing task:', error);
        showToast('حدث خطأ في الاتصال', 'danger');
    }
}

// Cancel task
async function cancelTask(taskId) {
    if (!confirm('هل تريد إلغاء هذه المهمة؟')) {
        return;
    }

    try {
        const response = await fetch(`/api/tasks/${taskId}`, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({status: 'cancelled'})
        });

        if (response.ok) {
            showToast('تم إلغاء المهمة', 'warning');
            await loadTasks();
        } else {
            showToast('حدث خطأ', 'danger');
        }
    } catch (error) {
        console.error('Error cancelling task:', error);
        showToast('حدث خطأ في الاتصال', 'danger');
    }
}

// Delete task
async function deleteTask(taskId) {
    if (!confirm('هل أنت متأكد من حذف هذه المهمة نهائياً؟ لا يمكن التراجع!')) {
        return;
    }

    try {
        const response = await fetch(`/api/tasks/${taskId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            showToast('تم حذف المهمة ✓', 'success');
            await loadTasks();
        } else {
            showToast('حدث خطأ في حذف المهمة', 'danger');
        }
    } catch (error) {
        console.error('Error deleting task:', error);
        showToast('حدث خطأ في الاتصال', 'danger');
    }
}

// Edit task
async function editTask(taskId) {
    try {
        const task = allTasks.find(item => item.id === taskId);

        if (!task) {
            showToast('المهمة غير موجودة', 'danger');
            return;
        }

        // Fill form
        document.getElementById('task-name').value = task.name;
        document.getElementById('task-description').value = task.description || '';

        // Set assistant
        const assistantSelect = document.getElementById('task-assistant');
        if (assistantSelect) {
            assistantSelect.value = task.assistant_id || '';
        }

        // Set time
        const timePicker = document.getElementById('task-time');
        if (timePicker && timePicker._flatpickr && task.time) {
            const taskTime = parseUTCDate(task.time);
            if (taskTime && !isNaN(taskTime.getTime())) {
                timePicker._flatpickr.setDate(taskTime, false);
            }
        } else if (timePicker && timePicker._flatpickr) {
            timePicker._flatpickr.clear();
        }

        // Set edit mode
        editingTaskId = taskId;
        document.getElementById('modal-title').textContent = 'تعديل المهمة';
        document.getElementById('btn-save-task').textContent = 'حفظ التعديلات';

        // Show modal by clicking trigger button
        const triggerBtn = document.querySelector('[data-bs-target="#modal-task"]');
        if (triggerBtn) {
            triggerBtn.click();
        }

    } catch (error) {
        console.error('Error loading task:', error);
        showToast('حدث خطأ في تحميل المهمة', 'danger');
    }
}

// Save task
async function saveTask() {
    const name = document.getElementById('task-name').value.trim();

    if (!name) {
        showToast('يرجى إدخال عنوان المهمة', 'warning');
        return;
    }

    const saveBtn = document.getElementById('btn-save-task');
    const originalText = saveBtn.textContent;

    saveBtn.disabled = true;
    saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>جاري الحفظ...';

    const timePicker = document.getElementById('task-time');
    const timeValue = timePicker && timePicker._flatpickr ? timePicker._flatpickr.selectedDates[0] : null;
    const assistantId = document.getElementById('task-assistant').value;

    const taskData = {
        name: name,
        description: document.getElementById('task-description').value.trim(),
        assistant_id: assistantId ? parseInt(assistantId) : null,
        time: timeValue ? timeValue.toISOString() : null
    };

    try {
        let response;

        if (editingTaskId) {
            response = await fetch(`/api/tasks/${editingTaskId}`, {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(taskData)
            });
        } else {
            response = await fetch('/api/tasks', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(taskData)
            });
        }

        if (response.ok) {
            showToast(editingTaskId ? 'تم تحديث المهمة بنجاح ✓' : 'تم إضافة المهمة بنجاح ✓', 'success');

            const modalElement = document.getElementById('modal-task');
            const closeBtn = modalElement.querySelector('[data-bs-dismiss="modal"]');
            if (closeBtn) {
                closeBtn.click();
            }

            setTimeout(async () => {
                await loadTasks();
            }, 300);

        } else {
            const error = await response.json();
            showToast('حدث خطأ: ' + (error.message || 'فشل في حفظ المهمة'), 'danger');
            saveBtn.disabled = false;
            saveBtn.textContent = originalText;
        }
    } catch (error) {
        console.error('Error saving task:', error);
        showToast('حدث خطأ في الاتصال', 'danger');
        saveBtn.disabled = false;
        saveBtn.textContent = originalText;
    }
}

// Close modal
function closeTaskModal() {
    document.getElementById('task-name').value = '';
    document.getElementById('task-description').value = '';

    const assistantSelect = document.getElementById('task-assistant');
    if (assistantSelect) assistantSelect.value = '';

    const timePicker = document.getElementById('task-time');
    if (timePicker && timePicker._flatpickr) {
        timePicker._flatpickr.clear();
    }

    editingTaskId = null;
    document.getElementById('modal-title').textContent = 'إضافة مهمة جديدة';

    const saveBtn = document.getElementById('btn-save-task');
    saveBtn.textContent = 'حفظ';
    saveBtn.disabled = false;
}

// Utility functions
function getStatusText(status) {
    const statusMap = {
        'pending': 'قيد الانتظار',
        'overdue': 'متأخرة',
        'completed': 'مكتملة',
        'cancelled': 'ملغاة'
    };
    return statusMap[status] || status;
}

function parseUTCDate(utcString) {
    if (!utcString) return null;

    let dateStr = utcString.trim();

    if (dateStr.includes('T') && !dateStr.endsWith('Z') && !dateStr.includes('+') && !dateStr.includes('-', 10)) {
        dateStr += 'Z';
    }

    return new Date(dateStr);
}

function formatDateForDisplay(dateString) {
    if (!dateString) return '';

    const date = parseUTCDate(dateString);
    if (!date || isNaN(date.getTime())) return '';

    const day = String(date.getDate()).padStart(2, '0');
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const year = date.getFullYear();
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');

    return `${day}/${month}/${year} ${hours}:${minutes}`;
}

function formatDateTime(dateString) {
    if (!dateString) return '';

    const date = parseUTCDate(dateString);
    if (!date || isNaN(date.getTime())) return '';

    const now = new Date();
    const diff = Math.floor((now.getTime() - date.getTime()) / 1000);

    if (diff < 60) {
        if (diff < 5) return 'الآن';
        if (diff < 10) return 'منذ لحظات';
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

    return formatDateForDisplay(dateString);
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