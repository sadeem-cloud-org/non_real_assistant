// Service Worker for Push Notifications
self.addEventListener('install', (event) => {
    console.log('[Service Worker] Installing...');
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    console.log('[Service Worker] Activating...');
    event.waitUntil(clients.claim());
});

self.addEventListener('push', (event) => {
    console.log('[Service Worker] Push received');

    let data = {};
    try {
        data = event.data ? event.data.json() : {};
    } catch (e) {
        data = {
            title: 'Non Real Assistant',
            body: event.data ? event.data.text() : 'لديك إشعار جديد'
        };
    }

    const title = data.title || 'Non Real Assistant';
    const options = {
        body: data.body || 'لديك إشعار جديد',
        tag: data.tag || 'notification',
        data: data.data || {},
        requireInteraction: data.requireInteraction || false
    };

    event.waitUntil(
        self.registration.showNotification(title, options)
    );
});

self.addEventListener('notificationclick', (event) => {
    console.log('[Service Worker] Notification clicked');
    event.notification.close();

    // Open the app when notification is clicked
    event.waitUntil(
        clients.openWindow(event.notification.data.url || '/')
    );
});