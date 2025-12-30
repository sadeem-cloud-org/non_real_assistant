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
            const registration = await navigator.serviceWorker.register('/static/sw.js');
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
        const options = {
            body: task.title + (task.description ? '\n' + task.description : ''),
            tag: 'task-' + task.id,
            requireInteraction: true,
            data: {
                taskId: task.id,
                url: '/tasks'
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

// Auto-initialize on page load
document.addEventListener('DOMContentLoaded', async () => {
    const permission = await notificationManager.checkPermission();
    console.log('📢 Notification permission:', permission);

    // Auto-register service worker if permission already granted
    if (permission === 'granted') {
        await notificationManager.registerServiceWorker();
    }
});