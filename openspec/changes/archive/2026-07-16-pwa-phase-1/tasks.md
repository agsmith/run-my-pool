## 1. Dependencies and Build Config

- [x] 1.1 Install `next-pwa` as a production dependency in `rmp/frontend/`
- [x] 1.2 Update `next.config.js` to wrap `nextConfig` with `withPWA()` per design D1
- [x] 1.3 Add `public/sw.js` and `public/workbox-*.js` to `.gitignore`

## 2. App Icons

- [x] 2.1 Create or obtain a square source image for the app icon (512×512 PNG, suitable for RunMyPool branding)
- [x] 2.2 Generate `public/icons/icon-192x192.png` from source image
- [x] 2.3 Generate `public/icons/icon-512x512.png` from source image
- [x] 2.4 Generate `public/icons/icon-512x512-maskable.png` with safe-zone padding (10% on all sides)

## 3. Web App Manifest

- [x] 3.1 Create `public/manifest.json` with all required fields per design D3 (name, short_name, start_url, display, theme_color, background_color, icons array)
- [ ] 3.2 Verify manifest parses correctly in Chrome DevTools → Application → Manifest

## 4. App Head Updates

- [x] 4.1 Add `<link rel="manifest" href="/manifest.json" />` to `<Head>` in `pages/_app.js` per design D2

## 5. Offline Fallback Page

- [x] 5.1 Create `pages/offline.js` with the static offline page per design D4
- [x] 5.2 Confirm `next-pwa` `fallbacks.document` is set to `/offline` in `next.config.js`

## 6. Verification

- [x] 6.1 Build the app (`npm run build`) and confirm no build errors
- [x] 6.2 Verify `sw.js` and `workbox-*.js` are generated in `public/` after build
- [x] 6.3 Run existing test suite (`npm run test`) and confirm all tests pass
- [ ] 6.4 Open Chrome DevTools → Application → Manifest and confirm no errors
- [ ] 6.5 Enable DevTools → Network → Offline, navigate to a page, confirm `/offline` is shown
- [ ] 6.6 Test Add to Home Screen on Android Chrome and confirm standalone launch
- [ ] 6.7 Test Add to Home Screen on iOS Safari and confirm standalone launch
