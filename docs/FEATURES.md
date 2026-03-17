# Scoreboard Flutter — Feature Reference

## Sports Supported
- **Soccer** — Home/Away score, count-up timer, team names
- **AFL** — Goals + Points per team (auto total), Q1-Q4 + Off, countdown timer, team names
- **Cricket** — Runs/Wickets/Extras/Overs+Balls per team, team names
- **Rugby** — Home/Away score, timer, team names
- **Hockey** — Home/Away score, timer, shot clock (Start/Stop only)
- **Basketball** — Home/Away score, fouls, timeouts, timer, shot clock (Start/Stop/Reset)

## Timer
- Count-up (Soccer, Rugby, Hockey, Basketball) or countdown (AFL default 20:00, Cricket)
- Start / Pause / Reset
- Settings: colour, size, v-align, leading-space offset
- AFL default offset: 1 space; other sports: 0
- Chunked across RAMT5–7

## Shot Clock
- **Hockey:** Start (appears + counts down), Stop (resets + disappears)
- **Basketball:** Start (appears + counts down), Stop (resets + disappears), Reset (restarts immediately)
- Settings: colour, size, v-align
- Sends to RAMT8

## AFL Quarter
- Off / Q1 / Q2 / Q3 / Q4
- Off → blank RAMT8; Q1-Q4 → sends "Q{n}" to RAMT8
- Settings: colour, size, v-align

## AFL Scoring
- Goals (×6) + Points → Total auto-calculated
- Counters: CNTS1=home goals, CNTS2=away goals, CNTS3=home pts, CNTS4=away pts, CNTS5=home total, CNTS6=away total

## Cricket Scoring
- Runs / Wickets / Extras / Overs / Balls per team
- Counters: CNTS1=home runs, CNTS2=home wkts, CNTS3=away runs, CNTS4=away wkts, CNTS5=extras, CNTS6=overs

## Team Names
- Up to 2 RAMT slots per team (home=1-2, away=3-4)
- Chunked by size: S=7/slot, M=4/slot, L=2/slot, XL=1/slot
- h_align always forced Left (3)
- v_align always uniform across all 4 slots (read from sport settings)

## Advertisements
- Create / Edit / Delete ads (named, multi-row text with colour/size/align per row)
- Per-ad: checkbox (selected), duration (default 4s)
- Loop: plays selected ads in order, loops until "Return to Scores"
- Single ad: plays once and stays on screen
- Stops automatically when returning to home/controller screen
- Selections and durations persisted to config

## Settings (per display element)
- Colour: Red/Green/Yellow/Blue/Purple/Cyan/White
- Size: S/M/L/XL
- H-Align: Centre/Right/Left (team names always forced Left)
- V-Align: Top/Mid/Bot

## Connection
- Auto-reconnect every 2 seconds
- Bypass mode: unlock all features without a real controller (for setup/testing)
- Connection test: sends `*#1PRGC30,0000` and waits for UDP response

## Config Persistence
All settings saved to device storage as JSON:
- Current sport, scores, team names
- Timer state and display settings
- Ad list and per-ad selections
- Per-sport display style settings
- Display width/height (first-run setup)

## Reset Settings
- Single button on home screen → confirmation dialog → wipes all saved state to factory defaults

## Display Setup (First Run)
- Enter LED display width and height in pixels
- Validates range (32–512 × 16–256)
- Saved to config; skipped on subsequent launches
