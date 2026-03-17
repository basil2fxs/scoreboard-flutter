# Scoreboard Flutter

Professional LED scoreboard controller for **TF-F6 display systems** — Flutter port of the Python desktop app, built for Android and iOS phones and tablets.

---

## Quick Start

```bash
cd scoreboard_flutter
flutter pub get
flutter run
```

See **[docs/SETUP.md](docs/SETUP.md)** for full build and deployment instructions.

---

## Features

| Feature | Description |
|---------|-------------|
| 🏉 AFL | Goals + Points per team, automatic totals, Q1–Q4 + Off quarter display |
| ⚽ Soccer | Home/Away scores, count-up timer |
| 🏏 Cricket | Runs/Wickets/Extras/Overs per team |
| 🏉 Rugby | Home/Away scores, timer |
| 🏒 Hockey | Home/Away scores, timer, shot clock (Start/Stop) |
| 🏀 Basketball | Home/Away scores, fouls, timeouts, timer, shot clock (Start/Stop/Reset) |
| ⏱ Timer | Count-up or countdown, live on display, configurable size/colour/offset |
| ⏲ Shot clock | Per-sport logic, disappears on Stop |
| 📢 Ads | Multi-ad playlist with per-ad duration, loop until back, create/edit/delete |
| 🎨 Settings | Colour, size, h-align, v-align per sport element with live preview |
| 🔌 Connection | Auto-reconnect every 3s, bypass mode for no-controller testing |
| 💾 Config | All settings auto-saved to device storage (JSON via SharedPreferences) |
| ♻️ Reset | One-button factory reset with confirmation |

---

## Project Structure

```
lib/
├── main.dart                  App entry, routing, theme setup
├── theme/app_theme.dart       Dark theme, colour palette, LED constants
├── models/
│   ├── app_config.dart        Full serialisable state
│   └── advertisement.dart     Ad + AdRow + AdSelection models
├── services/
│   ├── udp_service.dart       UDP send queue (120ms inter-command delay)
│   ├── ramt_service.dart      RAMT chunking + all display commands
│   └── config_service.dart    SharedPreferences JSON persistence
├── providers/
│   └── app_provider.dart      ChangeNotifier — all game logic + state
├── screens/
│   ├── display_setup_screen.dart
│   ├── home_screen.dart
│   ├── sport_selection_screen.dart
│   ├── soccer_screen.dart
│   ├── afl_screen.dart
│   ├── cricket_screen.dart
│   ├── simple_sport_screen.dart   (Rugby / Hockey / Basketball)
│   └── ad_editor_screen.dart
└── widgets/
    ├── section_card.dart          Consistent dark card wrapper
    ├── score_card.dart            +/− score row with manual entry
    ├── timer_widget.dart          MM:SS + Start/Pause/Reset
    ├── shot_clock_widget.dart     Shot clock
    ├── afl_quarter_widget.dart    Off / Q1–Q4 selector
    ├── team_names_card.dart       Home/Away name inputs
    ├── ads_panel.dart             Ad checklist + loop controls
    └── settings_dialogs.dart      Bottom-sheet style/colour pickers
```

---

## Hardware Protocol

Commands are sent as **ASCII UDP datagrams** to `192.168.1.252:5959`.

```
Program:  *#1PRGC3{prog},0000
Counter:  *#1CNTS{n},S{value},0000
RAMT:     *#1RAMT{slot},{color}{size}{hAlign}{vAlign}{text}0000
```

Commands are queued with 120ms inter-command delay to avoid overwhelming the controller.

---

## Documentation

| File | Contents |
|------|----------|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Full tech architecture, chunking logic, RAMT slot map |
| [docs/FEATURES.md](docs/FEATURES.md) | Complete feature reference |
| [docs/SETUP.md](docs/SETUP.md) | Flutter install, build, permissions, troubleshooting |

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `provider` ^6.1.2 | State management (ChangeNotifier) |
| `shared_preferences` ^2.3.1 | Config persistence |
| `udp` ^4.1.0 | UDP socket (fallback; UdpService uses dart:io directly) |

---

## Differences from Python App

| Area | Python | Flutter |
|------|--------|---------|
| UI framework | tkinter | Material 3 dark theme |
| State | Instance variables | Provider (ChangeNotifier) |
| Persistence | `~/scoreboard_config.json` | SharedPreferences |
| UDP | socket.socket | dart:io RawDatagramSocket |
| Threading | tkinter.after | Timer + async/await |
| Navigation | Screen replace | Named routes |

All functional behaviour is identical to the Python app.
