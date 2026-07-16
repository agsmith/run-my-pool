# Design: pwa-phase-1

Make RunMyPool installable as a Progressive Web App. Adds a web app manifest, service worker with offline fallback, and all required app icons. No new backend work required.

## Context

The frontend is Next.js (Pages Router, `output: standalone`) served via AWS ECS. It is already mobile-responsive with `apple-mobile-web-app-capable` and `theme-color` meta tags in `_app.js`, but it is not installable — it lacks a manifest and service worker.

The `public/` directory currently contains only `public/nfl/` (team logo assets). `next.config.js` is minimal.

No `docs/dev/architecture.md` exists in the project.

## References

- [next-pwa docs](https://github.com/shadowwalker/next-pwa) — Configuration and service worker setup for Next.js apps
- [web.dev PWA installability criteria](https://web.dev/install-criteria/) — Chrome/browser requirements for the install prompt
- [MDN: Web App Manifest](https://developer.mozilla.org/en-US/docs/Web/Manifest) — Manifest field reference
- [web.dev: Add to Home Screen](https://web.dev/customize-install/) — How to surface an install prompt in-app

## Goals / Non-Goals

**Goals:**

- App is installable to home screen on Android (Chrome) and iOS (Safari)
- Standalone display mode — no browser chrome when launched from home screen
- Offline fallback page displayed when network is unavailable
- All required manifest icons at correct sizes
- Maskable icon for Android adaptive icon support
- No regressions to existing web functionality

**Non-Goals:**

- Push notifications (Phase 2)
- Offline data caching / background sync (Phase 2)
- Service worker pre-caching of app routes (Phase 2)
- App Store / Play Store listing via Capacitor (Phase 3)
- Custom install prompt UI (can be added later)

## Decisions

### D1: Use `next-pwa` for service worker integration

**Decision:** Install `next-pwa` as the service worker solution. Wrap `nextConfig` in `withPWA()` inside `next.config.js`. This generates a service worker automatically on build.

```javascript
// rmp/frontend/next.config.js
const withPWA = require('next-pwa')({
  dest: 'public',
  disable: process.env.NODE_ENV === 'development',
  register: true,
  skipWaiting: true,
  fallbacks: {
    document: '/offline',
  },
})

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'standalone',
}

module.exports = withPWA(nextConfig)
```

`disable: process.env.NODE_ENV === 'development'` prevents service worker interference during local dev (a common source of confusion).

**Alternative considered:** Manual Workbox configuration. Rejected — significantly more boilerplate for no additional benefit at this phase.

---

### D2: Manifest linked via `_app.js` `<Head>`

**Decision:** Add the manifest link tag to `pages/_app.js` `<Head>`. This is already where all global meta tags live — consistent placement.

```jsx
// rmp/frontend/pages/_app.js (additions only)
<link rel="manifest" href="/manifest.json" />
```

**Alternative considered:** `next/head` in a layout component. No layout component exists yet — adding to `_app.js` is the minimal-change path.

---

### D3: Manifest content

**Decision:** `manifest.json` placed in `public/` with `display: standalone`, short and full names, theme and background color matching the existing `#667eea` theme color, and icon entries for 192px, 512px, and maskable 512px variants.

```json
// rmp/frontend/public/manifest.json
{
  "name": "Run My Pool",
  "short_name": "RunMyPool",
  "description": "NFL pick pool management. Create, manage, and track your survivor pools.",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#ffffff",
  "theme_color": "#667eea",
  "orientation": "portrait-primary",
  "icons": [
    {
      "src": "/icons/icon-192x192.png",
      "sizes": "192x192",
      "type": "image/png"
    },
    {
      "src": "/icons/icon-512x512.png",
      "sizes": "512x512",
      "type": "image/png"
    },
    {
      "src": "/icons/icon-512x512-maskable.png",
      "sizes": "512x512",
      "type": "image/png",
      "purpose": "maskable"
    }
  ]
}
```

**Alternative considered:** Using SVG icons. Safari does not support SVG in manifests — PNG required.

---

### D4: Offline fallback page

**Decision:** Create `pages/offline.js` as a static page. `next-pwa` serves this when a navigation request fails due to network unavailability.

```jsx
// rmp/frontend/pages/offline.js
export default function OfflinePage() {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '100vh',
      padding: '2rem',
      textAlign: 'center',
      fontFamily: 'system-ui, sans-serif',
    }}>
      <h1 style={{ fontSize: '1.5rem', marginBottom: '1rem' }}>You're offline</h1>
      <p style={{ color: '#666', maxWidth: '320px' }}>
        Check your connection and try again. Your picks are safe — they'll sync when you're back online.
      </p>
      <button
        onClick={() => window.location.reload()}
        style={{
          marginTop: '2rem',
          padding: '0.75rem 1.5rem',
          background: '#667eea',
          color: '#fff',
          border: 'none',
          borderRadius: '8px',
          fontSize: '1rem',
          cursor: 'pointer',
        }}
      >
        Try Again
      </button>
    </div>
  )
}
```

**Alternative considered:** Custom error page via `pages/_error.js`. That overrides all errors — too broad. A dedicated `/offline` route is cleanly targeted.

---

### D5: Icons generated from a source SVG/PNG

**Decision:** Icons are generated programmatically using `sharp` (CLI) from a single source image. The implementer creates or obtains a source image (512px square PNG or SVG) and runs a generation script. This avoids committing large binary blobs without provenance.

```bash
# One-time generation script (not checked in — run manually)
npx sharp-cli --input source-icon.png --output public/icons/icon-192x192.png resize 192
npx sharp-cli --input source-icon.png --output public/icons/icon-512x512.png resize 512
npx sharp-cli --input source-icon.png --output public/icons/icon-512x512-maskable.png resize 512
```

The maskable icon should have safe-zone padding (at least 10% on all sides). If the source icon is full-bleed, the implementer should create a padded variant manually.

**Alternative considered:** Manually creating icons in a design tool. Fine for one-off, but script is reproducible and easier to update.

---

## Interfaces

### Install Prompt (future / implicit)

The browser handles the install prompt natively. No custom UI is added in Phase 1. The browser will display its own prompt once installability criteria are met (manifest + service worker + HTTPS).

---

## Accessibility

### Offline Page

- The offline page uses semantic HTML (`<h1>`, `<p>`, `<button>`).
- The "Try Again" button is keyboard-accessible and focusable.
- No information is conveyed by color alone.
- No animations — no `prefers-reduced-motion` concerns.

---

## Migrations

No database migrations. No backend changes.

**Deployment order:**

1. Generate icons and place in `public/icons/`
2. Add `manifest.json` to `public/`
3. Install `next-pwa` dependency
4. Update `next.config.js`
5. Update `pages/_app.js`
6. Add `pages/offline.js`
7. Build and deploy frontend — service worker is generated at build time

**Rollback:** Revert `next.config.js` and `_app.js`, remove manifest and service worker files. No data at risk.

---

## Testing Philosophy

### Installability

Verify in Chrome DevTools → Application → Manifest that the manifest is parsed without errors and all icons resolve. Confirm "Add to Home Screen" prompt appears on Android Chrome after a page reload.

### Offline fallback

In DevTools → Network → Offline mode, navigate to any page. Confirm `/offline` is served instead of a browser error page. Confirm the "Try Again" button triggers a reload.

### iOS behavior

Open in Safari on iOS. Tap Share → Add to Home Screen. Confirm the app opens in standalone mode (no Safari address bar). Confirm the home screen icon uses the correct icon.

### No regression

Confirm existing navigation, authentication, and pick flows are unaffected. Run `npm run test` and confirm all existing tests pass.

---

## Risks / Trade-offs

### iOS PWA limitations

**Risk:** Safari on iOS has historically lagged on PWA feature support. Push notifications (Phase 2) only work if the user installs the PWA to the home screen AND is on iOS 16.4+. Users on older iOS will not receive push notifications.

**Mitigation:** Phase 1 is installability only — no push notifications are promised. Document iOS requirements when push is added in Phase 2.

### Service worker caching in standalone mode

**Risk:** `next-pwa` generates a service worker with precaching enabled by default. On first install, it may cache a large number of static assets, increasing initial load time on slow connections.

**Mitigation:** `next-pwa` defaults are well-tuned for Next.js. If performance issues arise in Phase 2 when adding route caching, the precache manifest can be restricted via `runtimeCaching` config.

### Generated service worker files in `public/`

**Risk:** `next-pwa` writes `sw.js` and `workbox-*.js` into `public/` at build time. These should not be committed to git — they are build artifacts.

**Mitigation:** Add `public/sw.js` and `public/workbox-*.js` to `.gitignore`.
