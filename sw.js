// Good Magical Morning service worker: shows the daily alert and opens the paper when it's tapped.
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));

self.addEventListener("push", (e) => {
  let msg = {};
  try { msg = e.data ? e.data.json() : {}; } catch { msg = { title: e.data && e.data.text() }; }
  e.waitUntil(self.registration.showNotification(msg.title || "hot news waitin' ☕️", {
    body: msg.body || "",
    icon: "img/icon-180.png",
    badge: "img/icon-180.png",
    tag: "gmm-daily",
    data: { url: msg.url || "./" },
  }));
});

self.addEventListener("notificationclick", (e) => {
  e.notification.close();
  const url = new URL(e.notification.data?.url || "./", self.registration.scope).href;
  e.waitUntil((async () => {
    const wins = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
    for (const w of wins) if (w.url.startsWith(self.registration.scope)) { await w.focus(); return w.navigate ? w.navigate(url) : null; }
    return self.clients.openWindow(url);
  })());
});
