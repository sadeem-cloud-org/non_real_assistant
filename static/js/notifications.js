// Browser Notification Manager
class NotificationManager {
    constructor() {
        this.permission = 'default';
        this.supported = 'Notification' in window;
        this.serviceWorkerSupported = 'serviceWorker' in navigator;
    }

    // Check if notifications are supported
    isSupported() {
        return this.supported;
    }

    // Check current permission status
    async checkPermission() {
        if (!this.supported) {
            return 'denied';
        }
        this.permission = Notification.permission;
        return this.permission;
    }

    // Request notification permission
    async requestPermission() {
        if (!this.supported) {
            throw new Error('Notifications not supported');
        }

        const permission = await Notification.requestPermission();
        this.permission = permission;

        if (permission === 'granted') {
            console.log('✅ Notification permission granted');
            await this.registerServiceWorker();
        } else if (permission === 'denied') {
            console.log('❌ Notification permission denied');
        } else {
            console.log('⏸ Notification permission dismissed');
        }

        return permission;
    }

    // Register service worker for push notifications
    async registerServiceWorker() {
        if (!this.serviceWorkerSupported) {
            console.log('⚠️ Service Worker not supported');
            return null;
        }

        try {
            const registration = await navigator.serviceWorker.register('/static/js/sw.js');
            console.log('✅ Service Worker registered:', registration);
            return registration;
        } catch (error) {
            // Silent fail - service worker is optional
            console.log('ℹ️ Service Worker not available (this is OK)');
            return null;
        }
    }

    // Show a simple notification
    async showNotification(title, options = {}) {
        const permission = await this.checkPermission();

        if (permission !== 'granted') {
            console.log('⚠️ Cannot show notification - permission not granted');
            return null;
        }

        const defaultOptions = {
            body: '',
            tag: 'notification-' + Date.now(),
            requireInteraction: false,
            silent: false
        };

        const notificationOptions = { ...defaultOptions, ...options };

        // Try to use service worker notification first
        if (this.serviceWorkerSupported) {
            try {
                const registration = await navigator.serviceWorker.ready;
                await registration.showNotification(title, notificationOptions);
                console.log('✅ Notification shown via Service Worker');
                return true;
            } catch (error) {
                console.error('❌ Service Worker notification failed:', error);
            }
        }

        // Fallback to regular notification
        try {
            const notification = new Notification(title, notificationOptions);

            notification.onclick = (event) => {
                event.preventDefault();
                if (notificationOptions.data && notificationOptions.data.url) {
                    window.open(notificationOptions.data.url, '_blank');
                }
                notification.close();
            };

            console.log('✅ Notification shown');
            return notification;
        } catch (error) {
            console.error('❌ Notification failed:', error);
            return null;
        }
    }

    // Show task reminder notification
    async showTaskReminder(task) {
        const title = '⏰ تذكير بمهمة';
        const taskTitle = task.title || task.name || 'مهمة';
        const options = {
            body: taskTitle + (task.description ? '\n' + task.description : ''),
            tag: 'task-' + task.id,
            requireInteraction: true,
            data: {
                taskId: task.id,
                url: '/tasks/' + task.id
            }
        };

        return await this.showNotification(title, options);
    }

    // Close all notifications with a specific tag
    async closeNotificationsByTag(tag) {
        if (!this.serviceWorkerSupported) return;

        try {
            const registration = await navigator.serviceWorker.ready;
            const notifications = await registration.getNotifications({ tag });

            notifications.forEach(notification => notification.close());
            console.log(`✅ Closed ${notifications.length} notifications with tag: ${tag}`);
        } catch (error) {
            console.error('❌ Failed to close notifications:', error);
        }
    }
}

// Create global instance
const notificationManager = new NotificationManager();

// Track notified tasks to avoid duplicates
const notifiedTasks = new Set();

// Poll server for pending notifications
async function checkPendingNotifications() {
    // Only check if notifications are enabled
    const permission = await notificationManager.checkPermission();
    if (permission !== 'granted') {
        return;
    }

    try {
        const response = await fetch('/api/notifications/check');
        if (!response.ok) return;

        const data = await response.json();
        const notifications = data.notifications || [];

        for (const task of notifications) {
            // Skip if already notified in this session
            const taskKey = `task-${task.id}`;
            if (notifiedTasks.has(taskKey)) {
                continue;
            }

            // Show notification
            await notificationManager.showTaskReminder(task);
            notifiedTasks.add(taskKey);

            console.log('🔔 Browser notification shown for task:', task.title);
        }
    } catch (error) {
        // Silent fail - don't spam console
    }
}

// Start polling for notifications (every 60 seconds)
let notificationPollInterval = null;

function startNotificationPolling() {
    if (notificationPollInterval) return;

    // Check immediately
    checkPendingNotifications();

    // Then check every 60 seconds
    notificationPollInterval = setInterval(checkPendingNotifications, 60000);
    console.log('🔄 Browser notification polling started');
}

function stopNotificationPolling() {
    if (notificationPollInterval) {
        clearInterval(notificationPollInterval);
        notificationPollInterval = null;
        console.log('⏹ Browser notification polling stopped');
    }
}

// Update notification bell icon based on permission
function updateNotificationBell(permission) {
    const bell = document.getElementById('notification-bell');
    if (!bell) return;

    const icon = bell.querySelector('i');
    if (!icon) return;

    if (permission === 'granted') {
        icon.className = 'ti ti-bell-ringing icon text-success';
        bell.title = 'الإشعارات مفعلة';
    } else if (permission === 'denied') {
        icon.className = 'ti ti-bell-off icon text-danger';
        bell.title = 'الإشعارات معطلة';
    } else {
        icon.className = 'ti ti-bell icon';
        bell.title = 'تفعيل الإشعارات';
    }
}

// Request notification permission (global function for onclick)
async function requestNotificationPermission(event) {
    if (event) event.preventDefault();

    try {
        const permission = await notificationManager.requestPermission();
        updateNotificationBell(permission);

        // Start polling if permission granted
        if (permission === 'granted') {
            startNotificationPolling();
        }

        // Save to server if needed
        try {
            await fetch('/api/notifications/permission', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ permission })
            });
        } catch (e) {
            // Ignore server errors
        }
    } catch (error) {
        console.error('Error requesting notification permission:', error);
    }
}

// Auto-initialize on page load
document.addEventListener('DOMContentLoaded', async () => {
    const permission = await notificationManager.checkPermission();
    console.log('📢 Notification permission:', permission);

    // Update bell icon
    updateNotificationBell(permission);

    // Auto-register service worker and start polling if permission already granted
    if (permission === 'granted') {
        await notificationManager.registerServiceWorker();
        startNotificationPolling();
    }
});

// Handle visibility change - pause polling when tab is hidden
document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') {
        // Resume polling when tab becomes visible
        if (Notification.permission === 'granted') {
            startNotificationPolling();
        }
    } else {
        // Pause polling when tab is hidden to save resources
        stopNotificationPolling();
    }
});