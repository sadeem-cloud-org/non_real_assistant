// Dashboard JavaScript with Tabler UI

// Initialize Flatpickr for datetime inputs
let dueDatePicker, reminderPicker;
let editingTaskId = null;
// Translation object - will be populated from HTML template
const t = window.translations || {};

// Load dashboard data on page load
document.addEventListener('DOMContentLoaded', function() {
    initializeDateTimePickers();
    loadDashboardStats();
    loadRecentExecutions();
    loadOverdueTasks();

    // Initialize theme
    initializeTheme();

    // Initialize notifications
    initializeNotifications();

    // Check for pending notifications every 30 seconds
    setInterval(checkPendingNotifications, 30000);

    // Get modal element
    const modalElement = document.getElementById('modal-task');
    if (modalElement) {
        modalElement.addEventListener('hidden.bs.modal', function () {
            closeAddTaskModal();
        });
    }
});

// Initialize theme from URL or localStorage
function initializeTheme() {
    const urlParams = new URLSearchParams(window.location.search);
    const theme = urlParams.get('theme') || localStorage.getItem('tablerTheme') || 'light';

    if (theme === 'dark') {
        document.body.setAttribute('data-bs-theme', 'dark');
    } else {
        document.body.removeAttribute('data-bs-theme');
    }

    localStorage.setItem('tablerTheme', theme);

    // Update URL without reload
    if (urlParams.get('theme')) {
        window.history.replaceState({}, '', window.location.pathname);
    }
}

// Initialize Flatpickr datetime pickers
function initializeDateTimePickers() {
    const dateTimeConfig = {
        enableTime: true,
        time_24hr: true,
        dateFormat: "d/m/Y H:i",
        altInput: true,
        altFormat: "d/m/Y H:i",
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

    dueDatePicker = flatpickr("#task-due-date", dateTimeConfig);
    reminderPicker = flatpickr("#task-reminder", dateTimeConfig);
}

// Load dashboard statistics
async function loadDashboardStats() {
    try {
        const response = await fetch('/api/dashboard/stats');
        const data = await response.json();

        if (response.ok) {
            document.getElementById('active-assistants').textContent = data.active_assistants;
            document.getElementById('overdue-tasks').textContent = data.overdue_tasks;
            document.getElementById('completed-today').textContent = data.completed_today;
            document.getElementById('recent-executions-count').textContent = data.recent_executions.length;

            // Show/hide no assistants alert
            const noAssistantsAlert = document.getElementById('no-assistants-alert');
            if (noAssistantsAlert) {
                noAssistantsAlert.style.display = data.active_assistants === 0 ? 'block' : 'none';
            }
        }
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// Load recent executions
async function loadRecentExecutions() {
    const container = document.getElementById('executions-list');

    try {
        const response = await fetch('/api/executions?limit=5');
        const executions = await response.json();

        if (!response.ok) {
            throw new Error('Failed to load executions');
        }

        if (executions.length === 0) {
            container.innerHTML = `
                <div class="empty">
                    <p class="empty-title">${t.no_recent_operations || 'لا توجد عمليات حديثة'}</p>
                </div>
            `;
            return;
        }

        container.innerHTML = '<div class="list-group list-group-flush">' +
            executions.map(exec => {
                const statusClass = exec.status === 'success' ? 'success' : exec.status === 'failed' ? 'danger' : 'warning';
                const statusText = getStatusText(exec.status);

                return `
                    <div class="list-group-item">
                        <div class="row">
                            <div class="col-auto">
                                <span class="badge badge-outline text-${statusClass}">${statusText}</span>
                            </div>
                            <div class="col text-truncate">
                                <div class="text-reset">Action #${exec.action_id}</div>
                                <div class="text-muted">${formatDateTime(exec.created_at)}</div>
                            </div>
                        </div>
                    </div>
                `;
            }).join('') +
        '</div>';

    } catch (error) {
        console.error('Error loading executions:', error);
        container.innerHTML = `<div class="empty"><p class="empty-title">حدث خطأ في تحميل البيانات</p></div>`;
    }
}

// Load overdue tasks
async function loadOverdueTasks() {
    const container = document.getElementById('tasks-list');

    try {
        // Fetch overdue tasks
        const response = await fetch('/api/tasks?status=overdue');
        const allTasks = await response.json();

        if (!response.ok) {
            throw new Error('Failed to load tasks');
        }

        // Limit to 5 tasks
        const limitedTasks = allTasks.slice(0, 5);

        if (limitedTasks.length === 0) {
            container.innerHTML = `
                <div class="empty">
                    <div class="empty-icon">
                        <i class="ti ti-mood-smile icon"></i>
                    </div>
                    <p class="empty-title">${t.no_pending_tasks || 'رائع! لا توجد مهام معلقة'}</p>
                </div>
            `;
            return;
        }

        container.innerHTML = '<div class="list-group list-group-flush">' +
            limitedTasks.map(task => {
                const priorityClass = task.priority === 'high' ? 'text-red' : task.priority === 'medium' ? 'text-yellow' : 'text-green';
                const priorityIcon = task.priority === 'high' ? 'alert-circle' : task.priority === 'medium' ? 'alert-triangle' : 'circle-check';

                // Status badge - these are overdue tasks
                const statusClass = 'red';
                const statusIcon = 'clock-exclamation';
                const statusText = 'متأخرة';

                return `
                    <div class="list-group-item">
                        <div class="row align-items-center">
                            <div class="col-auto">
                                <i class="ti ti-${priorityIcon} ${priorityClass}"></i>
                            </div>
                            <div class="col text-truncate">
                                <div class="d-flex align-items-center gap-2">
                                    <span class="text-reset d-block">${escapeHtml(task.name)}</span>
                                    <span class="badge bg-${statusClass}">
                                        <i class="ti ti-${statusIcon}"></i>
                                        ${statusText}
                                    </span>
                                </div>
                                ${task.description ? `<div class="text-muted text-truncate mt-1">${escapeHtml(task.description)}</div>` : ''}
                                ${task.time ? `<div class="text-danger mt-1"><i class="ti ti-clock-exclamation icon"></i> ${formatDateTime(task.time)}</div>` : ''}
                            </div>
                            <div class="col-auto">
                                <div class="btn-list flex-nowrap">
                                    <button class="btn btn-sm btn-icon btn-success" onclick="completeTask(${task.id})" title="إكمال">
                                        <i class="ti ti-check"></i>
                                    </button>
                                    <button class="btn btn-sm btn-icon btn-primary" onclick="editTask(${task.id})" title="تعديل">
                                        <i class="ti ti-edit"></i>
                                    </button>
                                    <button class="btn btn-sm btn-icon btn-danger" onclick="cancelTask(${task.id})" title="إلغاء">
                                        <i class="ti ti-x"></i>
                                    </button>
                                    <button class="btn btn-sm btn-icon btn-danger" onclick="deleteTask(${task.id})" title="حذف">
                                        <i class="ti ti-trash"></i>
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            }).join('') +
        '</div>';

    } catch (error) {
        console.error('Error loading tasks:', error);
        container.innerHTML = `<div class="empty"><p class="empty-title">حدث خطأ</p></div>`;
    }
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
            await loadDashboardStats();
            await loadOverdueTasks();
        } else {
            showToast('حدث خطأ في تحديث المهمة', 'danger');
        }
    } catch (error) {
        console.error('Error completing task:', error);
        showToast('حدث خطأ في الاتصال', 'danger');
    }
}

// Edit task
async function editTask(taskId) {
    try {
        const response = await fetch(`/api/tasks`);

        if (!response.ok) {
            throw new Error('Failed to fetch tasks');
        }

        const allTasks = await response.json();
        const task = allTasks.find(item => item.id === taskId);

        if (!task) {
            showToast('المهمة غير موجودة', 'danger');
            return;
        }

        // Fill form
        document.getElementById('task-title').value = task.title;
        document.getElementById('task-description').value = task.description || '';
        document.getElementById('task-priority').value = task.priority;

        // Parse dates correctly - convert from UTC to local
        if (task.due_date) {
            const dueDate = parseUTCDate(task.due_date);
            if (dueDate && !isNaN(dueDate.getTime())) {
                dueDatePicker.setDate(dueDate, false);
            }
        } else {
            dueDatePicker.clear();
        }

        if (task.reminder_time) {
            const reminderDate = parseUTCDate(task.reminder_time);
            if (reminderDate && !isNaN(reminderDate.getTime())) {
                reminderPicker.setDate(reminderDate, false);
            }
        } else {
            reminderPicker.clear();
        }

        // Set edit mode
        editingTaskId = taskId;
        document.getElementById('modal-title').textContent = 'تعديل المهمة';
        document.getElementById('btn-save-task').textContent = 'حفظ التعديلات';

        // Show modal by finding the button that opens it
        const modalElement = document.getElementById('modal-task');
        // Trigger modal show using data attribute
        const triggerBtn = document.querySelector('[data-bs-target="#modal-task"]');
        if (triggerBtn) {
            triggerBtn.click();
        } else {
            // Fallback: manually add show class
            modalElement.classList.add('show');
            modalElement.style.display = 'block';
            document.body.classList.add('modal-open');

            // Add backdrop
            const backdrop = document.createElement('div');
            backdrop.className = 'modal-backdrop fade show';
            backdrop.id = 'edit-modal-backdrop';
            document.body.appendChild(backdrop);
        }

    } catch (error) {
        console.error('Error loading task:', error);
        showToast('حدث خطأ في تحميل المهمة', 'danger');
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
            await loadDashboardStats();
            await loadOverdueTasks();
        } else {
            showToast('حدث خطأ في إلغاء المهمة', 'danger');
        }
    } catch (error) {
        console.error('Error cancelling task:', error);
        showToast('حدث خطأ في الاتصال', 'danger');
    }
}

// Delete task
async function deleteTask(taskId) {
    if (!confirm('هل أنت متأكد من حذف هذه المهمة؟ لا يمكن التراجع!')) {
        return;
    }

    try {
        const response = await fetch(`/api/tasks/${taskId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            showToast('تم حذف المهمة ✓', 'success');
            await loadDashboardStats();
            await loadOverdueTasks();
        } else {
            showToast('حدث خطأ في حذف المهمة', 'danger');
        }
    } catch (error) {
        console.error('Error deleting task:', error);
        showToast('حدث خطأ في الاتصال', 'danger');
    }
}

// Save task
async function saveTask() {
    const title = document.getElementById('task-title').value.trim();

    if (!title) {
        showToast('يرجى إدخال عنوان المهمة', 'warning');
        return;
    }

    const saveBtn = document.getElementById('btn-save-task');
    const originalText = saveBtn.textContent;

    // Show loading
    saveBtn.disabled = true;
    saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>جاري الحفظ...';

    const dueDateValue = dueDatePicker.selectedDates[0];
    const reminderValue = reminderPicker.selectedDates[0];

    const taskData = {
        title: title,
        description: document.getElementById('task-description').value.trim(),
        priority: document.getElementById('task-priority').value,
        due_date: dueDateValue ? dueDateValue.toISOString() : null,
        reminder_time: reminderValue ? reminderValue.toISOString() : null
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
            // Show success message
            showToast(editingTaskId ? 'تم تحديث المهمة بنجاح ✓' : 'تم إضافة المهمة بنجاح ✓', 'success');

            // Close modal by clicking the close button
            const modalElement = document.getElementById('modal-task');
            const closeBtn = modalElement.querySelector('[data-bs-dismiss="modal"]');
            if (closeBtn) {
                closeBtn.click();
            }

            // Wait a bit then reload
            setTimeout(async () => {
                await loadDashboardStats();
                await loadOverdueTasks();
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

// Close modal and reset
function closeAddTaskModal() {
    document.getElementById('task-title').value = '';
    document.getElementById('task-description').value = '';
    document.getElementById('task-priority').value = 'medium';
    dueDatePicker.clear();
    reminderPicker.clear();

    editingTaskId = null;
    document.getElementById('modal-title').textContent = 'إضافة مهمة جديدة';

    const saveBtn = document.getElementById('btn-save-task');
    saveBtn.textContent = 'حفظ';
    saveBtn.disabled = false;

    // Remove backdrop if exists
    const backdrop = document.getElementById('edit-modal-backdrop');
    if (backdrop) {
        backdrop.remove();
        document.body.classList.remove('modal-open');
    }
}

// Logout
function logout() {
    if (confirm('هل أنت متأكد من تسجيل الخروج؟')) {
        window.location.href = '/logout';
    }
}

// Utility functions
function getStatusText(status) {
    const statusMap = {
        'success': 'نجح',
        'failed': 'فشل',
        'running': 'قيد التنفيذ',
        'pending': 'معلق'
    };
    return statusMap[status] || status;
}

function getPriorityText(priority) {
    const priorityMap = {
        'high': '🔴 عالية',
        'medium': '🟡 متوسطة',
        'low': '🟢 منخفضة'
    };
    return priorityMap[priority] || priority;
}

function formatDateTime(dateString) {
    if (!dateString) return '';

    const date = parseUTCDate(dateString);
    if (!date || isNaN(date.getTime())) return '';

    // Use getTime() to compare timestamps (both in milliseconds since epoch)
    const now = new Date();
    const diff = Math.floor((now.getTime() - date.getTime()) / 1000); // الفرق بالثواني

    if (diff < 60) {
        // ثواني
        if (diff < 5) return 'الآن';
        if (diff < 10) return 'منذ لحظات';
        return `منذ ${diff} ثانية`;
    }

    const minutes = Math.floor(diff / 60);
    if (minutes < 60) {
        // دقائق
        if (minutes === 1) return 'منذ دقيقة';
        if (minutes === 2) return 'منذ دقيقتين';
        return `منذ ${minutes} دقيقة`;
    }

    const hours = Math.floor(minutes / 60);
    if (hours < 24) {
        // ساعات
        if (hours === 1) return 'منذ ساعة';
        if (hours === 2) return 'منذ ساعتين';
        return `منذ ${hours} ساعة`;
    }

    const days = Math.floor(hours / 24);
    if (days < 7) {
        // أيام
        if (days === 1) return 'منذ يوم';
        if (days === 2) return 'منذ يومين';
        return `منذ ${days} يوم`;
    }

    // More than 1 week - show full date in local time
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

// Parse UTC datetime string and convert to local
function parseUTCDate(utcString) {
    if (!utcString) return null;

    // Force UTC interpretation by adding 'Z' if missing
    let dateStr = utcString.trim();

    // If has 'T' but no timezone indicator, add 'Z'
    if (dateStr.includes('T') && !dateStr.endsWith('Z') && !dateStr.includes('+') && !dateStr.includes('-', 10)) {
        dateStr += 'Z';
    }

    return new Date(dateStr);
}

// Format date for display (local time)
function formatDateForDisplay(dateString) {
    if (!dateString) return '';

    const date = parseUTCDate(dateString);
    if (!date || isNaN(date.getTime())) return '';

    // Format as dd/mm/yyyy hh:mm in local timezone
    const day = String(date.getDate()).padStart(2, '0');
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const year = date.getFullYear();
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');

    return `${day}/${month}/${year} ${hours}:${minutes}`;
}

// Toast notification
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

    // Auto hide after 3 seconds
    setTimeout(() => {
        toastDiv.classList.remove('show');
        setTimeout(() => toastDiv.remove(), 300);
    }, 3000);
}

// ============================================
// Notification Functions
// ============================================

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

        // Save to server
        await fetch('/api/notifications/permission', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ permission })
        });

        if (permission === 'granted') {
            showToast('تم تفعيل الإشعارات بنجاح ✓', 'success');

            // Show test notification
            setTimeout(() => {
                notificationManager.showNotification('مرحباً! 👋', {
                    body: 'الإشعارات تعمل بنجاح. سنرسل لك تذكيرات بالمهام.',
                    requireInteraction: false
                });
            }, 1000);
        } else if (permission === 'denied') {
            showToast('تم رفض الإشعارات', 'danger');
        }
    } catch (error) {
        console.error('Error requesting permission:', error);
        showToast('حدث خطأ في تفعيل الإشعارات', 'danger');
    }
}

// Update notification bell icon based on permission
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

// Check for pending notifications
async function checkPendingNotifications() {
    try {
        const permission = await notificationManager.checkPermission();
        if (permission !== 'granted') return;

        const response = await fetch('/api/notifications/check');
        const data = await response.json();

        if (data.notifications && data.notifications.length > 0) {
            for (const task of data.notifications) {
                await notificationManager.showTaskReminder(task);
            }

            // Update badge
            const badge = document.getElementById('notification-badge');
            if (badge) {
                badge.textContent = data.notifications.length;
                badge.style.display = 'inline';

                // Hide after 10 seconds
                setTimeout(() => {
                    badge.style.display = 'none';
                }, 10000);
            }
        }
    } catch (error) {
        console.error('Error checking notifications:', error);
    }
}