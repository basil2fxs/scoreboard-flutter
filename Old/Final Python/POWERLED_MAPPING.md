# PowerLED TF-F6 — Program Feature Mapping

---

## Program 0 — Home / Idle
No counters or text boxes used.

---

## Program 1 — AFL

| Counter | Purpose |
|---|---|
| CNTS1 | Home goals |
| CNTS2 | Away goals |
| CNTS3 | Home behinds (points) |
| CNTS4 | Away behinds (points) |
| CNTS5 | Home total score (goals×6 + behinds) |
| CNTS6 | Away total score (goals×6 + behinds) |

| RAMT slot | What to display |
|---|---|
| RAMT1–2 | Home team name (style configurable via ⚙ Team Names button) |
| RAMT3–4 | Away team name (style configurable via ⚙ Team Names button) |
| RAMT5   | Game timer — chunk 1 of `MM:SS` (content depends on size) |
| RAMT6   | Game timer — chunk 2 of `MM:SS` |
| RAMT7   | Game timer — chunk 3 of `MM:SS` (blank if not needed) |
| RAMT8   | Quarter indicator — `Off` (blank) / `Q1` / `Q2` / `Q3` / `Q4` |

**Timer chunks shift left with size** (same logic as team names):
- L (size 3, 2 chars/slot): `12` · `:3` · `5`
- M (size 2, 4 chars/slot): `12:3` · `5` · ` `

**Quarter command (RAMT8):**
```
*#1RAMT8,{c}{s}3{v}Q{1-4}0000   ← Q1–Q4
*#1RAMT8,{c}{s}3{v} 0000         ← Off (blank)
```

Timer and quarter h-align is always **Left (3)**. Colour, size, v-align are configurable via ⚙.
Quarter "Off" button blanks RAMT8; Q1–Q4 show the quarter number.

---

## Program 2 — Soccer

| Counter | Purpose |
|---|---|
| CNTS1 | Home score |
| CNTS2 | Away score |

| RAMT slot | What to display |
|---|---|
| RAMT1–2 | Home team name |
| RAMT3–4 | Away team name |
| RAMT5   | Game timer — minutes |
| RAMT6   | Game timer — `:tens` of seconds |
| RAMT7   | Game timer — units of seconds |

**Timer display always left-aligned.** Colour, size, v-align configurable via ⚙.

---

## Program 3 — Cricket

| Counter | Purpose |
|---|---|
| CNTS1 | Home runs |
| CNTS2 | Away runs |
| CNTS3 | Home wickets |
| CNTS4 | Away wickets |
| CNTS5 | Extras |
| CNTS6 | Overs (integer part) |
| CNTS7 | Balls this over (0–5) |

| RAMT slot | What to display |
|---|---|
| RAMT1–2 | Home team name |
| RAMT3–4 | Away team name |

No timer for cricket.

---

## Program 4 — Rugby

| Counter | Purpose |
|---|---|
| CNTS1 | Home score |
| CNTS2 | Away score |

Scoring events add directly to score: Try +5, Conversion +2, Penalty +3, Drop Goal +3.

| RAMT slot | What to display |
|---|---|
| RAMT1–2 | Home team name |
| RAMT3–4 | Away team name |
| RAMT5   | Game timer — minutes |
| RAMT6   | Game timer — `:tens` of seconds |
| RAMT7   | Game timer — units of seconds |

**Timer display always left-aligned.** Colour, size, v-align configurable via ⚙.

---

## Program 5 — Hockey

| Counter | Purpose |
|---|---|
| CNTS1 | Home score |
| CNTS2 | Away score |

| RAMT slot | What to display |
|---|---|
| RAMT1–2 | Home team name |
| RAMT3–4 | Away team name |
| RAMT5   | Game timer — minutes |
| RAMT6   | Game timer — `:tens` of seconds |
| RAMT7   | Game timer — units of seconds |
| RAMT8   | Shot clock — full value (blank when zero) |

**Timer always left-aligned.** Shot clock blanks RAMT8 on Stop or when countdown reaches zero.

**Shot clock buttons (Hockey):**
- **▶ Start** — display appears; clock counts down from current value
- **■ Stop** — resets to target value; display goes blank immediately

---

## Program 6 — Basketball

| Counter | Purpose |
|---|---|
| CNTS1 | Home score |
| CNTS2 | Away score |
| CNTS3 | Home timeouts remaining |
| CNTS4 | Away timeouts remaining |
| CNTS5 | Home fouls |
| CNTS6 | Away fouls |

| RAMT slot | What to display |
|---|---|
| RAMT1–2 | Home team name |
| RAMT3–4 | Away team name |
| RAMT5   | Game timer — minutes |
| RAMT6   | Game timer — `:tens` of seconds |
| RAMT7   | Game timer — units of seconds |
| RAMT8   | Shot clock — full value (blank when zero) |

**Timer and shot clock always left-aligned.**

**Shot clock buttons (Basketball):**
- **▶ Start** — display appears; clock counts down from current value
- **■ Stop** — resets to target value; display goes blank immediately
- **↺ Reset** — resets to target value and immediately starts counting down (display appears)

> Timeouts and fouls use `CNTS` (hardware counters). Reset: `*#1CNTS{N},S0,0000`; set: `*#1CNTS{N},S{value},0000`.

---

## Timer / Shot Clock RAMT Command Format

```
Team names (all sport programs):
  Home → RAMT1–2  (start_slot=1)
  Away → RAMT3–4  (start_slot=3)

Game timer (all sports with timer) — chunked like team names:
  Full string = "MM:SS" (e.g. "12:35"), split into 3 slots by size:
    XL (1 char/slot) → RAMT5='1', RAMT6='2', RAMT7=':'
    L  (2 chars/slot) → RAMT5='12', RAMT6=':3', RAMT7='5'
    M  (4 chars/slot) → RAMT5='12:3', RAMT6='5', RAMT7=' '
    S  (7 chars/slot) → RAMT5='12:35  ', RAMT6=' ', RAMT7=' '
  Each slot: *#1RAMT{5–7},{c}{s}3{v}{chunk}0000
  Unused slots are blanked with a space.

Shot clock (Basketball / Hockey):
  RAMT8 → *#1RAMT8,{c}{s}3{v}{value_or_blank}0000   (full value e.g. 30, 14, 5; blank when zero)

AFL Quarter:
  RAMT8 → *#1RAMT8,{c}{s}3{v}Q{1-4}0000
```

- H-align is **always 3 (Left)** for all timers, shot clocks, and AFL quarter
- `c` = colour, `s` = size, `v` = v-align (all configurable via ⚙ button)

---

## Display Settings — Colour, Size, Alignment Codes

| Setting | Code | Meaning |
|---------|------|---------|
| Colour  | 1 | Red |
| Colour  | 2 | Green |
| Colour  | 3 | Yellow |
| Colour  | 4 | Blue |
| Colour  | 5 | Magenta |
| Colour  | 6 | Cyan |
| Colour  | 7 | White |
| Size    | 1 | S (small — most chars fit) |
| Size    | 2 | M (medium — **default for timers**) |
| Size    | 3 | L (large) |
| Size    | 4 | XL (extra-large — fewest chars fit) |
| H-Align | 1 | Center |
| H-Align | 2 | Right |
| H-Align | 3 | Left |
| V-Align | 1 | Top |
| V-Align | 2 | Middle |
| V-Align | 3 | Bottom |

> **Note on size:** for sport programs (1–6), a **smaller** size code = **smaller text** (more characters fit). A **larger** code = **larger text** (fewer characters). This is the opposite of text programs (7–14).

---

## Text Screen Programs (7–14)

No counters used. Program is selected automatically based on number of rows and border choice.

| Rows | No Border | With Border |
|------|-----------|-------------|
| 1    | Program 7  | Program 8   |
| 2    | Program 9  | Program 10  |
| 3    | Program 11 | Program 12  |
| 4    | Program 13 | Program 14  |

| Rows | RAMT slots used |
|------|-----------------|
| 1    | RAMT1           |
| 2    | RAMT1–2         |
| 3    | RAMT1–3         |
| 4    | RAMT1–4         |

**Per-row command format:**
```
*#1RAMT{N},{color}{size}{h_align}{v_align}{text}0000
```

**Approximate character limits per size (128-wide display):**
| Size Code | Label | Max chars/row |
|-----------|-------|---------------|
| 4         | XL    | ~5 chars      |
| 3         | L     | ~7 chars      |
| 2         | M     | ~15 chars     |

> For text programs (7–14), size 4=XL (largest, fewest chars), size 2=M (smallest of the 3).
> Character limits scale with display width (`display_width / 128`).

Border programs (8, 10, 12, 14) use the same slot layout — animated striped border is drawn around the content area.

### Scroll modes

**Multi-row (snake):** All row texts joined into one string; each row shows a successive window.
**Single-line:** Each row scrolls its own text independently. Enable via the "Single" checkbox.

| Speed | Delay |
|-------|-------|
| Slow  | 1200 ms |
| Med   | 900 ms  |
| Fast  | 600 ms  |

---

## Advertisements

User-created advertisements are saved to `~/scoreboard_config.json` and persist across sessions.

**UI per sport screen:**
- Always-visible checklist of saved ads: each row has a checkbox, name, duration field (seconds, default 3), Edit and Delete buttons
- **▶ Play Selected** — loops through all checked ads in order, each for its specified duration, repeating until stopped
- **↩ Return to Scores** — stops any playing ad loop and returns to the score program
- **＋ New Advertisement** — opens the ad creator (text editor)

Each ad is played by switching to program 0 then to the ad's text program, with RAMT slots set per row.
