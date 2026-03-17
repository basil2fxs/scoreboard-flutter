# Scoreboard Flutter — Architecture

## Overview
Flutter mobile app that controls a TF-F6 LED scoreboard controller over UDP.
Targets Android and iOS phones/tablets.

---

## Hardware Protocol

### Controller
- **IP:** 192.168.1.252
- **Port:** 5959 (UDP)
- **Protocol:** ASCII UDP datagrams

### Command Formats
```
Program select:   *#1PRGC3{prog},0000
Counter set:      *#1CNTS{n},S{value},0000
Counter add:      *#1CNTS{n},A{delta},0000
Counter subtract: *#1CNTS{n},D{delta},0000
RAMT text:        *#1RAMT{slot},{color}{size}{h_align}{v_align}{text}0000
```

### RAMT Slots
| Slot | Usage |
|------|-------|
| RAMT1–2 | Home team name (chunked) |
| RAMT3–4 | Away team name (chunked) |
| RAMT5–7 | Timer MM:SS (chunked) |
| RAMT8   | Shot clock OR AFL quarter |

### Display Codes
**Color:** 1=Red 2=Green 3=Yellow 4=Blue 5=Purple 6=Cyan 7=White
**Size (chars/slot):** 1=S(7) 2=M(4) 3=L(2) 4=XL(1)
**H-Align:** 1=Center 2=Right 3=Left
**V-Align:** 1=Top 2=Mid 3=Bot

### Sport Programs
| Sport | Program |
|-------|---------|
| AFL | 1 |
| Soccer | 2 |
| Cricket | 3 |
| Rugby | 4 |
| Hockey | 5 |
| Basketball | 6 |

---

## Flutter Architecture

```
lib/
├── main.dart                    # App entry, MaterialApp, theme
├── theme/
│   └── app_theme.dart           # Dark theme, colours, text styles
├── models/
│   ├── app_config.dart          # All persisted state (serialisable)
│   ├── advertisement.dart       # Ad model (rows, border, name)
│   └── sport_state.dart         # Per-sport score/name state
├── services/
│   ├── udp_service.dart         # Raw UDP send + connection test
│   ├── ramt_service.dart        # RAMT chunking + command helpers
│   └── config_service.dart      # JSON persist/load via shared_preferences
├── providers/
│   └── app_provider.dart        # ChangeNotifier — all app state + actions
├── screens/
│   ├── display_setup_screen.dart
│   ├── home_screen.dart
│   ├── sport_selection_screen.dart
│   ├── soccer_screen.dart
│   ├── afl_screen.dart
│   ├── cricket_screen.dart
│   ├── simple_sport_screen.dart  # Rugby / Hockey / Basketball
│   ├── ads_screen.dart          # Ad management overlay
│   └── ad_editor_screen.dart    # Create/edit ad rows
└── widgets/
    ├── score_card.dart           # Team name + +/- score row
    ├── timer_widget.dart         # MM:SS display + Start/Pause/Reset
    ├── shot_clock_widget.dart    # Shot clock for Hockey/Basketball
    ├── afl_quarter_widget.dart   # Off/Q1–Q4 selector
    ├── ads_panel.dart            # Checklist + loop controls
    ├── settings_dialogs.dart     # Color/size/align picker dialogs
    └── section_card.dart         # Consistent dark card wrapper
```

---

## State Management
Uses **Provider** (`ChangeNotifier`).
`AppProvider` is the single source of truth for all game state and settings.
Screens listen with `context.watch<AppProvider>()` and call actions via `context.read<AppProvider>().someAction()`.

---

## UDP Threading
UDP sends are dispatched to an `Isolate` so they never block the UI thread.
A 120ms inter-command delay queue is maintained in `UdpService`.

---

## Chunking Logic
Team names and timer are split into chunks and sent to consecutive RAMT slots:

```dart
int chunkSize = {'4': 1, '3': 2, '2': 4, '1': 7, '9': 10}[size] ?? 4;
List<String> chunks = [];
for (int i = 0; i < max(text.length, 1); i += chunkSize) {
  chunks.add(text.substring(i, min(i + chunkSize, text.length)));
}
while (chunks.length < numSlots) chunks.add(' ');
```

Names use 2 slots (RAMT1-2 for home, RAMT3-4 for away).
Timer uses 3 slots (RAMT5-7).
v_align is always read from the sport's authoritative settings (never from the caller), ensuring all slots for a name are identical.
