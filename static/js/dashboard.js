// Dashboard JavaScript with Tabler UI

// Initialize Flatpickr for datetime inputs
let dueDatePicker, reminderPicker;

// Load dashboard data on page load
document.addEventListener('DOMContentLoaded', function() {
    initializeDateTimePickers();
    loadDashboardStats();
    loadRecentExecutions();
    loadPendingTasks();

    // Initialize theme
    initializeTheme();
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
            firstDayOfWeek: 6, // Saturday
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
            document.getElementById('pending-tasks').textContent = data.pending_tasks;
            document.getElementById('completed-today').textContent = data.completed_today;
            document.getElementById('recent-executions-count').textContent = data.recent_executions.length;
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
                <div class="empty-state">
                    <div class="empty-state-icon">📭</div>
                    <p>لا توجد عمليات حديثة</p>
                </div>
            `;
            return;
        }

        container.innerHTML = executions.map(exec => `
            <div class="execution-item">
                <div class="execution-header">
                    <span class="execution-title">Action #${exec.action_id}</span>
                    <span class="execution-status status-${exec.status}">
                        ${getStatusText(exec.status)}
                    </span>
                </div>
                <div class="execution-time">
                    ${formatDateTime(exec.created_at)}
                    ${exec.execution_time ? ` - ${exec.execution_time.toFixed(2)}s` : ''}
                </div>
            </div>
        `).join('');

    } catch (error) {
        console.error('Error loading executions:', error);
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">⚠️</div>
                <p>حدث خطأ في تحميل البيانات</p>
            </div>
        `;
    }
}

// Load pending tasks
async function loadPendingTasks() {
    const container = document.getElementById('tasks-list');

    try {
        const response = await fetch('/api/tasks?status=pending');
        const tasks = await response.json();

        if (!response.ok) {
            throw new Error('Failed to load tasks');
        }

        const limitedTasks = tasks.slice(0, 5);

        if (limitedTasks.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">🎉</div>
                    <p>رائع! لا توجد مهام معلقة</p>
                </div>
            `;
            return;
        }

        container.innerHTML = limitedTasks.map(task => `
            <div class="task-item">
                <div class="task-header">
                    <span class="task-title">${escapeHtml(task.title)}</span>
                    <span class="task-priority priority-${task.priority}">
                        ${getPriorityText(task.priority)}
                    </span>
                </div>
                ${task.description ? `
                    <div class="task-description">${escapeHtml(task.description)}</div>
                ` : ''}
                ${task.due_date ? `
                    <div class="task-time">
                        📅 ${formatDateTime(task.due_date)}
                    </div>
                ` : ''}
                <div class="task-actions">
                    <button class="task-btn btn-complete" onclick="completeTask(${task.id})" title="إكمال">
                        <i class="ti ti-check"></i>
                    </button>
                    <button class="task-btn btn-edit" onclick="editTask(${task.id})" title="تعديل">
                        <i class="ti ti-edit"></i>
                    </button>
                    <button class="task-btn btn-hold" onclick="holdTask(${task.id})" title="تعليق">
                        <i class="ti ti-player-pause"></i>
                    </button>
                    <button class="task-btn btn-delete" onclick="deleteTask(${task.id})" title="حذف">
                        <i class="ti ti-trash"></i>
                    </button>
                </div>
            </div>
        `).join('');

    } catch (error) {
        console.error('Error loading tasks:', error);
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">⚠️</div>
                <p>حدث خطأ في تحميل البيانات</p>
            </div>
        `;
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
            // Reload dashboard
            loadDashboardStats();
            loadPendingTasks();
        } else {
            alert('حدث خطأ في تحديث المهمة');
        }
    } catch (error) {
        console.error('Error completing task:', error);
        alert('حدث خطأ في الاتصال');
    }
}

// Edit task
let editingTaskId = null;

async function editTask(taskId) {
    try {
        const response = await fetch(`/api/tasks?status=pending`);
        const tasks = await response.json();
        const task = tasks.find(t => t.id === taskId);

        if (!task) {
            alert('المهمة غير موجودة');
            return;
        }

        // Fill form with task data
        document.getElementById('task-title').value = task.title;
        document.getElementById('task-description').value = task.description || '';
        document.getElementById('task-priority').value = task.priority;

        // Set dates using Flatpickr
        if (task.due_date) {
            dueDatePicker.setDate(task.due_date);
        }
        if (task.reminder_time) {
            reminderPicker.setDate(task.reminder_time);
        }

        // Change modal title and button
        editingTaskId = taskId;
        document.querySelector('#addTaskModal .modal-header h2').textContent = 'تعديل المهمة';
        document.querySelector('#addTaskModal .btn-primary').textContent = 'حفظ التعديلات';

        // Show modal
        showAddTaskModal();

    } catch (error) {
        console.error('Error loading task:', error);
        alert('حدث خطأ في تحميل المهمة');
    }
}

// Hold task (change status to in_progress or on_hold)
async function holdTask(taskId) {
    if (!confirm('هل تريد تعليق هذه المهمة مؤقتاً؟')) {
        return;
    }

    try {
        const response = await fetch(`/api/tasks/${taskId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                status: 'in_progress'  // or create 'on_hold' status
            })
        });

        if (response.ok) {
            loadDashboardStats();
            loadPendingTasks();
        } else {
            alert('حدث خطأ في تعليق المهمة');
        }
    } catch (error) {
        console.error('Error holding task:', error);
        alert('حدث خطأ في الاتصال');
    }
}

// Delete task
async function deleteTask(taskId) {
    if (!confirm('هل أنت متأكد من حذف هذه المهمة؟ لا يمكن التراجع عن هذا الإجراء!')) {
        return;
    }

    try {
        const response = await fetch(`/api/tasks/${taskId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            loadDashboardStats();
            loadPendingTasks();
        } else {
            alert('حدث خطأ في حذف المهمة');
        }
    } catch (error) {
        console.error('Error deleting task:', error);
        alert('حدث خطأ في الاتصال');
    }
}

// Modal functions
function showAddTaskModal() {
    document.getElementById('addTaskModal').classList.add('show');
}

function closeAddTaskModal() {
    document.getElementById('addTaskModal').classList.remove('show');

    // Reset form
    document.getElementById('task-title').value = '';
    document.getElementById('task-description').value = '';
    document.getElementById('task-priority').value = 'medium';
    dueDatePicker.clear();
    reminderPicker.clear();

    // Reset edit mode
    editingTaskId = null;
    document.querySelector('#addTaskModal .modal-header h2').textContent = 'إضافة مهمة جديدة';
    document.querySelector('#addTaskModal .btn-primary').textContent = 'حفظ';
}

// Save task
async function saveTask() {
    const title = document.getElementById('task-title').value.trim();

    if (!title) {
        alert('يرجى إدخال عنوان المهمة');
        return;
    }

    // Get dates from Flatpickr (already in ISO format internally)
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
            // Update existing task
            response = await fetch(`/api/tasks/${editingTaskId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(taskData)
            });
        } else {
            // Create new task
            response = await fetch('/api/tasks', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(taskData)
            });
        }

        if (response.ok) {
            closeAddTaskModal();
            loadDashboardStats();
            loadPendingTasks();
        } else {
            const error = await response.json();
            alert('حدث خطأ: ' + (error.message || 'فشل في حفظ المهمة'));
        }
    } catch (error) {
        console.error('Error saving task:', error);
        alert('حدث خطأ في الاتصال');
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
        'success': '✓ نجح',
        'failed': '✗ فشل',
        'running': '⏳ قيد التنفيذ',
        'pending': '⏸ معلق'
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

    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;

    // Less than 1 hour
    if (diff < 3600000) {
        const minutes = Math.floor(diff / 60000);
        return `منذ ${minutes} دقيقة`;
    }

    // Less than 24 hours
    if (diff < 86400000) {
        const hours = Math.floor(diff / 3600000);
        return `منذ ${hours} ساعة`;
    }

    // Less than 7 days
    if (diff < 604800000) {
        const days = Math.floor(diff / 86400000);
        return `منذ ${days} يوم`;
    }

    // Format as date
    return date.toLocaleDateString('ar-EG', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

// Close modal when clicking outside
document.addEventListener('click', function(event) {
    const modal = document.getElementById('addTaskModal');
    if (event.target === modal) {
        closeAddTaskModal();
    }
});

// Handle Escape key
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        closeAddTaskModal();
    }
});