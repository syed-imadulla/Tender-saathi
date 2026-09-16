/**
 * sw.js — TenderSaathi Service Worker (Cache-First App Shell)
 *
 * Strategy:
 *   - App shell (HTML, JS, CSS, fonts, icons) → Cache-First with network fallback.
 *   - API requests (/api/*) → Network-Only, with a structured offline error if unreachable.
 *
 * Offline behaviour:
 *   - The application shell loads from cache when previously visited.
 *   - Tender analysis, OCR, standards retrieval, and AI parsing REQUIRE a network connection.
 *   - The UI will show a connection-status banner when offline.
 *
 * Cache versioning:
 *   - Bump CACHE_NAME when deploying breaking asset changes to force cache refresh.
 */

const CACHE_NAME = 'tendersaathi-v2';

// Assets to precache on install (app shell)
const PRECACHE_URLS = [
  '/',
  '/index.html',
  '/manifest.webmanifest',
  '/icons/icon-192.png',
  '/icons/icon-512.png',
];

// ---------------------------------------------------------------------------
// Install — precache the app shell
// ---------------------------------------------------------------------------
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      // Cache the shell; non-fatal if some assets are unavailable at install time
      return cache.addAll(PRECACHE_URLS).catch((err) => {
        console.warn('[SW] Precache partial failure (non-fatal):', err);
      });
    }).then(() => self.skipWaiting())
  );
});

// ---------------------------------------------------------------------------
// Activate — remove stale caches
// ---------------------------------------------------------------------------
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name !== CACHE_NAME)
          .map((name) => {
            console.log('[SW] Deleting old cache:', name);
            return caches.delete(name);
          })
      );
    }).then(() => self.clients.claim())
  );
});

// ---------------------------------------------------------------------------
// Fetch — routing logic
// ---------------------------------------------------------------------------
self.addEventListener('fetch', (event) => {
  const { request } = event;

  // Ignore non-HTTP/HTTPS schemes (e.g. chrome-extension://, moz-extension://, data:, blob:)
  if (!request.url.startsWith('http://') && !request.url.startsWith('https://')) {
    return;
  }

  const url = new URL(request.url);

  // Ignore Vite development endpoints, HMR websocket tokens, and hot-updates
  if (
    url.pathname.startsWith('/@') ||
    url.searchParams.has('token') ||
    url.searchParams.has('t') ||
    url.pathname.includes('/node_modules/') ||
    url.pathname.includes('hot-update')
  ) {
    return;
  }

  // Skip WebSocket upgrade requests
  if (request.headers.get('Upgrade') === 'websocket') {
    return;
  }

  // API requests: always go to network; return structured offline error if down
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(networkOnlyWithOfflineError(request));
    return;
  }

  // Only handle GET requests for caching
  if (request.method !== 'GET') {
    return;
  }

  // Everything else: cache-first (app shell + static assets)
  event.respondWith(cacheFirstWithNetworkFallback(request));
});

// ---------------------------------------------------------------------------
// Strategies
// ---------------------------------------------------------------------------

/**
 * Network-only for API calls.
 * On network failure, returns a JSON error so the UI can show a clean message.
 */
async function networkOnlyWithOfflineError(request) {
  try {
    return await fetch(request);
  } catch {
    return new Response(
      JSON.stringify({
        error: 'offline',
        message:
          'TenderSaathi analysis requires an internet connection. ' +
          'Please check your connection and try again.',
        offline: true,
      }),
      {
        status: 503,
        headers: {
          'Content-Type': 'application/json',
          'X-TenderSaathi-Offline': 'true',
        },
      }
    );
  }
}

/**
 * Cache-first for static assets.
 * Falls back to network and caches new responses.
 */
async function cacheFirstWithNetworkFallback(request) {
  // Only cache GET requests with HTTP/HTTPS
  if (request.method !== 'GET' || (!request.url.startsWith('http://') && !request.url.startsWith('https://'))) {
    return fetch(request);
  }

  const cached = await caches.match(request);
  if (cached) {
    return cached;
  }

  try {
    const response = await fetch(request);
    // Cache successful opaque or ok responses
    if (response && (response.ok || response.type === 'opaque')) {
      try {
        const cache = await caches.open(CACHE_NAME);
        await cache.put(request, response.clone());
      } catch (cacheErr) {
        console.warn('[SW] Caching skipped:', cacheErr);
      }
    }
    return response;
  } catch {
    // For navigation requests, serve the cached index.html as fallback
    if (request.mode === 'navigate') {
      const fallback = await caches.match('/index.html');
      if (fallback) return fallback;
    }
    // For other assets, return a minimal 503
    return new Response('Network unavailable', { status: 503 });
  }
}
