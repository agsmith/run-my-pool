# Run My Pool native app

Expo/React Native application for iOS and Android. It uses the existing FastAPI backend and stores rotating, revocable mobile session credentials in the platform secure store.

## Local development

1. Copy `.env.example` to `.env.local` and override the API URL if needed.
2. Run `npm install`.
3. Run `npm run ios` or `npm run android`.

## Current foundation

- Branded native shell and pool navigation
- Secure login with 180-day rolling refresh sessions
- My Pools, Pool Directory, account, and pool summary screens
- Universal/deep-link configuration for `https://runmypool.net/join/...`
- EAS development, preview, and production build profiles

## Delivery sequence

1. Native Survivor entry and pick workflow
2. Native Pick Em workflow
3. Native Squares workflow
4. Leaderboards, roster, forum, and commissioner tools
5. Push-token registration and weekly reminder notifications
6. Accessibility, offline/error states, device matrix, TestFlight/Play internal testing
7. Store privacy disclosures, screenshots, review, and phased release

## Store setup still required

- Apple Developer Program membership and App Store Connect app
- Expo account/project (`eas init`)
- Apple associated-domain file deployed on `runmypool.net`
- Privacy-policy review and App Store privacy declarations
