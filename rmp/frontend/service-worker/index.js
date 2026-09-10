import { defaultCache } from '@serwist/next/worker'
import { Serwist, NetworkOnly } from 'serwist'
import { isForumRequest } from '../lib/forumCache'

const serwist = new Serwist({
  precacheEntries: self.__SW_MANIFEST,
  skipWaiting: true,
  clientsClaim: true,
  navigationPreload: true,
  runtimeCaching: [{ matcher: isForumRequest, handler: new NetworkOnly(), method: "GET" }, ...defaultCache],
  fallbacks: {
    entries: [
      {
        url: '/offline',
        matcher({ request }) {
          return request.destination === 'document'
        },
      },
    ],
  },
})

serwist.addEventListeners()

// Remove responses cached by older service workers before Forum privacy rules.
self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    for (const name of await caches.keys()) {
      const cache = await caches.open(name);
      for (const request of await cache.keys()) {
        if (isForumRequest({ url: new URL(request.url) })) await cache.delete(request);
      }
    }
  })());
});
