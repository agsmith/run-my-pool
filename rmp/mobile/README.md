# Run My Pool native app

Expo / React Native app for iOS and Android, using the existing Run My Pool API.

## Run locally

```sh
npm ci
npm run typecheck
npm test
npx expo-doctor
npm run ios
# Or, with Android Studio and a device/emulator:
npm run android
```

Copy `.env.example` to `.env.local` to override the API URL. Never put account credentials or signing keys in Expo public environment variables. Native sessions use the platform secure store and the backend's rotating mobile refresh tokens.

## Implemented

- Native sign-in, My Pools, pool browsing, and account screens.
- Native Survivor board: schedule-derived current week, week selection, multiple entries, entry creation, matchups, and confirmed pick saving.
- Both teams lock at kickoff; pool deadline and existing server locks also apply. Used teams cannot be selected again for the same entry.
- Full-screen native picker with an independently scrolling game list and fixed confirmation footer inside the safe area.
- Native Pool Home team counts and expandable entry names. Only server-revealed picks are shown.
- Pull-to-refresh on data screens. Initial loads, explicit week/entry selection, and successful edits load data; focus changes, foregrounding, and timers do not refresh it. Survivor lock labels update locally at kickoff without a network request.
- Native Forum with posting and own-message deletion, revealed-pick Leaderboard, and permission-gated Pool Admin settings, dues, member pick locks, delegated admin access, and week locking.
- Native Pick ’Em entries, game selections, and tiebreakers; native Squares claims, releases, number drawing, and results.
- Native pool joining and password recovery. Missing Survivor picks have an attention border and filled action; saved picks use an outlined change action. Navigation consistently says Back.
- iOS bundle identifier and Android package: `net.runmypool.app`.

All routes exposed in the app are native. Pool Admin exposes the common pool controls listed above; platform-wide administration, printable exports, and advanced commissioner workflows are not exposed in this release.

## Verification

```sh
npx expo export --platform ios --platform android --output-dir /tmp/rmp-native-export
```

Exports validate JavaScript bundles, not signed binaries or device behavior. Native simulator/device builds and end-to-end testing are required before release. Rule tests cover the exact early-game kickoff boundary, both sides of the game, previous-week reuse, and the pool deadline.

## Distribution

Use `npx eas-cli@latest` rather than installing EAS CLI as a project dependency. The EAS project is linked as `@agsmith11/run-my-pool` (project ID `0c554287-2cbc-40ea-b6e4-b37f3f8216ca`). App Store Connect app ID is `6810498155`; signing credentials are managed by EAS. The existing build profiles cover development, internal preview, and store production. Physical iPhone builds require Apple signing and registered test devices or TestFlight; Android internal builds should use an APK profile.

Before store submission: finish account creation/deletion, store disclosures and screenshots, associated-domain verification, push permissions/reminders, accessibility/device testing, and Apple/Google signing and store configuration. No store submission is implied by a successful export.

Framework references: [Expo Router](https://docs.expo.dev/versions/latest/sdk/router/) and [secure storage](https://docs.expo.dev/develop/user-interface/store-data/).
