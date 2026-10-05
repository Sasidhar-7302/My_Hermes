// Hermes Smartphone Service Worker
const CACHE_NAME = 'hermes-phone-companion-v1';

self.addEventListener('install', (event) => {
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(clients.claim());
});

self.addEventListener('push', (event) => {
    const data = event.data ? event.data.json() : { title: 'Hermes Alert', body: 'New notification from PC' };
    event.waitUntil(
        self.registration.showNotification(data.title, {
            body: data.body,
            icon: '/companions/smartphone/manifest.json',
            vibrate: data.vibrate || [150, 50, 150]
        })
    );
});
