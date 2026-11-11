# TTK BOOST Android

Companion app for monitoring TikTok publication notifications on the same Android device.

## Current build
- Android application, Java, minSdk 23.
- NotificationListenerService filters notifications from TikTok package IDs.
- When a notification contains a publication-related phrase, the app records the time and shows a possible-publication signal.
- The app does not automate likes, comments, follows, views, or posting.
- The app does not scrape TikTok screens or access private account data.

## Setup
1. Install the APK.
2. Open TTK BOOST.
3. Tap **ATIVAR MONITORAMENTO**.
4. In Android notification access settings, enable TTK BOOST.
5. Publish normally in TikTok. If TikTok posts a publication confirmation notification, TTK BOOST can detect that signal.

## Important limitation
TikTok does not provide a generally available public API that gives any personal account immediate post-publication view counts, retention, and distribution data. This first version therefore detects publication-related notifications only. It does not fabricate analytics or claim to boost/force TikTok recommendations. Actual metrics require an authorized TikTok data integration or a supported user-provided data source.

## Build
From this directory, run:
```sh
gradle assembleDebug
```
The GitHub Actions workflow `.github/workflows/ttk-boost-android.yml` builds a debug APK and uploads it as the `ttk-boost-debug-apk` artifact.
