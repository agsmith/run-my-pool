## Why

RunMyPool is a mobile-use-case app — users open it once a week to make a pick and check results. The existing web app is already mobile-responsive, but it cannot be installed to a home screen, does not cache anything offline, and has no install prompt. Phase 1 adds the foundational PWA infrastructure that makes the app installable and establishes the baseline for future push notification and offline features.

## What Changes

- Add a `manifest.json` (web app manifest) with name, icons, theme color, and `display: standalone`
- Add a service worker via `next-pwa` that provides basic offline fallback
- Add all required app icon sizes (192px, 512px, maskable variants)
- Add a static offline fallback page
- Wire the manifest link into `_app.js` `<Head>`
- Configure `next.config.js` to integrate `next-pwa`

## Capabilities

### New Capabilities
- `pwa-installability`: Web app manifest, service worker registration, home screen install support, and offline fallback page

### Modified Capabilities
<!-- None — no existing spec-level behavior changes -->

## Impact

- **Frontend**: `next.config.js`, `pages/_app.js`, `public/` (manifest.json, icons, offline.html), new `next-pwa` dependency
- **Infrastructure**: No changes required — static assets served through existing ECS/Next.js setup
- **No breaking changes**
