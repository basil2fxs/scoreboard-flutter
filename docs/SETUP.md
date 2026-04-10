# Scoreboard Flutter — Setup Guide

## Prerequisites
- Flutter SDK ≥ 3.19 (Dart ≥ 3.3)
- Android Studio or Xcode
- A physical device or emulator with network access to 192.168.1.252

## Install Flutter
```bash
# macOS (via brew)
brew install --cask flutter

# Verify
flutter doctor
```

## Clone / Open Project
```bash
cd "/path/to/scoreboard_flutter"
flutter pub get
```

## Run on Device
```bash
# List devices
flutter devices

# Run (debug)
flutter run -d <device-id>

# Build release APK (Android)
flutter build apk --release

# Build release IPA (iOS - requires Xcode + Apple dev account)
flutter build ios --release
```

## Android Permissions
`android/app/src/main/AndroidManifest.xml` must include:
```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.CHANGE_NETWORK_STATE" />
```
These are already included in the project.

## iOS Permissions
No special permissions needed for outbound UDP on iOS (local network).
For iOS 14+, add to `ios/Runner/Info.plist`:
```xml
<key>NSLocalNetworkUsageDescription</key>
<string>Required to communicate with the LED scoreboard controller.</string>
<key>NSBonjourServices</key>
<array>
    <string>_scoreboard._udp</string>
</array>
```
Already included in the project.

## Network Setup
- The app and controller must be on the same Wi-Fi network as 192.168.1.252
- Controller port: 5959 (UDP)
- Use "Bypass Connection" mode to test the UI without a real controller

## Troubleshooting
| Problem | Solution |
|---------|----------|
| Can't connect | Check same Wi-Fi subnet as 192.168.1.252 |
| UDP blocked | Some corporate/school Wi-Fi blocks UDP; use hotspot |
| iOS won't send UDP | Ensure Local Network permission granted in iOS Settings |
| Timer size stuck | Pull up Timer settings and tap Apply |
| Settings not saving | Check app has storage permissions |

## First Run
On first launch, you will be asked to enter your LED display dimensions (e.g. 128×80).
This configures how text is chunked for the display. Enter your display's pixel size and tap Continue.
