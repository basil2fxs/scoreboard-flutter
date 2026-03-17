# PowerLED Display Controller Setup Guide
## Professional Scoreboard Control Application

This guide explains how to configure your PowerLED display controller programs to work with the Scoreboard Control application.

---

## 📋 Table of Contents
1. [Overview](#overview)
2. [Program Assignments](#program-assignments)
3. [AFL Setup (Programs 1 & 2)](#afl-setup)
4. [Soccer Setup (Program 3)](#soccer-setup)
5. [Cricket Setup (Program 4)](#cricket-setup)
6. [Home/Menu Screen (Program 0)](#home-screen)
7. [Object Index Reference](#object-index-reference)
8. [Display Layouts](#display-layouts)

---

## Overview

The Scoreboard Control application uses **Program Switching** commands to display different sports. Each sport requires a specific program to be configured in your PowerLED software.

**Command Format:** `*#1PRGC3X,0000` where X is the program number

---

## Program Assignments

Configure these programs in your PowerLED editor:

| Program # | Sport | Application Name |
|-----------|-------|------------------|
| **0** | Home Screen | Menu/Blank |
| **1** | AFL (Count-Up) | Australian Football |
| **2** | AFL (Count-Down) | Australian Football |
| **3** | Soccer | Football/Soccer |
| **4** | Cricket | Cricket Match |

---

## AFL Setup

### Programs 1 & 2: Australian Football League

**Display Format:**
```
HOME  X . X  XX        AWAY  X . X  XX
      G   P  Total           G   P  Total
```

### Required Objects

#### **Special Text Areas (RAMT)**
- **RAMT1** - HOME Team Name
  - Default: "HOME"
  - Example: "EAGLES"
  
- **RAMT2** - AWAY Team Name
  - Default: "AWAY"
  - Example: "TIGERS"
  
- **RAMT3** - Quarter Display
  - Values: "Q1", "Q2", "Q3", "Q4"
  - Default: "Q1"

#### **Counters (CNTS)**
- **C1** - HOME Goals (0-999)
- **C2** - AWAY Goals (0-999)
- **C3** - HOME Points (0-999)
- **C4** - AWAY Points (0-999)
- **C5** - HOME Total Score (Auto-calculated: Goals×6 + Points)
- **C6** - AWAY Total Score (Auto-calculated: Goals×6 + Points)

#### **Hardcoded Text Areas (Fixed in PowerLED)**
- **T1** - "." (decimal separator between Goals and Points for HOME)
- **T2** - "." (decimal separator between Goals and Points for AWAY)

### Display Layout Example
```
┌─────────────────────────────────────────────┐
│           QUARTER: Q2                       │
│                                             │
│  EAGLES    8 . 4  52                        │
│  TIGERS    6 . 7  43                        │
│                                             │
│           [Timer: 15:23]                    │
└─────────────────────────────────────────────┘
```

### Break Screens
When Quarter Time, Half Time, or 3/4 Time buttons are pressed:
- Switches to Program 0 (Home screen)
- Displays: "Half Time   EAGLES 52 - 43 TIGERS"
- "Return to Scores" button restores AFL program

---

## Soccer Setup

### Program 3: Football/Soccer

**Display Format:**
```
HOME  X        AWAY  X
      Score          Score
```

### Required Objects

#### **Special Text Areas (RAMT)**
- **RAMT1** - HOME Team Name
  - Default: "HOME"
  - Example: "PERTH"
  
- **RAMT2** - AWAY Team Name
  - Default: "AWAY"
  - Example: "SYDNEY"
  
- **RAMT3** - Half Display
  - Values: "1st HALF", "2nd HALF"
  - Default: "1st HALF"

#### **Counters (CNTS)**
- **C1** - HOME Score (0-99)
- **C2** - AWAY Score (0-99)

### Display Layout Example
```
┌─────────────────────────────────────────────┐
│           1st HALF                          │
│                                             │
│  PERTH     2                                │
│  SYDNEY    1                                │
│                                             │
│           [Timer: 23:45]                    │
└─────────────────────────────────────────────┘
```

### Break Screens
When Half Time button is pressed:
- Switches to Program 0
- Displays customizable text with scores
- Default format: "Half Time   HOME 2 - 1 AWAY"

---

## Cricket Setup

### Program 4: Cricket Match

**Display Format:**
```
HOME  XXX / X        AWAY  XXX / X
      Runs Wkt            Runs Wkt

Overs: XX.X          Extras: XX
```

### Required Objects

#### **Special Text Areas (RAMT)**
- **RAMT1** - HOME Team Name
  - Default: "HOME"
  - Example: "AUSTRALIA"
  
- **RAMT2** - AWAY Team Name
  - Default: "AWAY"
  - Example: "ENGLAND"
  
- **RAMT3** - Innings Display
  - Values: "INN1", "INN2"
  - Default: "INN1"

#### **Counters (CNTS)**
- **C1** - HOME Runs (0-999)
- **C2** - AWAY Runs (0-999)
- **C3** - HOME Wickets (0-10)
- **C4** - AWAY Wickets (0-10)
- **C5** - Extras (0-999)
- **C6** - Overs (before decimal, 0-999)
- **C7** - Balls (after decimal, 0-5)

#### **Hardcoded Text Areas (Fixed in PowerLED)**
- **T1** - "Extras" (label)
- **T2** - "Overs" (label)
- **T3** - "/" (separator between Runs and Wickets for HOME)
- **T4** - "/" (separator between Runs and Wickets for AWAY)
- **T5** - "." (decimal point for Overs display)

### Display Layout Example
```
┌─────────────────────────────────────────────┐
│           INN2                              │
│                                             │
│  AUSTRALIA   245 / 7                        │
│  ENGLAND     178 / 4                        │
│                                             │
│  Overs: 43.2          Extras: 12           │
│           [Timer: 2:15:30]                  │
└─────────────────────────────────────────────┘
```

### Special Cricket Features
- **Auto-increment:** When Balls reach 6, automatically adds 1 to Overs and resets Balls to 0
- **Wickets capped:** Maximum 10 wickets per team
- **Runs buttons:** Quick +1, +2, +3, +4, +6 buttons for common scoring

---

## Home Screen

### Program 0: Menu/Blank Display

Used for:
- Initial menu screen (blank)
- Advertisement displays
- Break screen messages (Half Time, Quarter Time, etc.)

**Special Text Area:**
- **RAMT1** - Main display text
  - Used for advertisements
  - Used for break time messages
  - Default: Blank or custom welcome message

---

## Object Index Reference

### Special Text Areas (RAMT)
```
*#1RAMTx,CSHT[text]0000

x = Text area index (1-9)
C = Colour (1-7)
S = Size (1-4, 9)
H = Horizontal alignment (1-3)
T = Vertical alignment (1-3)
```

**Index Usage:**
- **Index 1:** HOME team name (all sports)
- **Index 2:** AWAY team name (all sports)
- **Index 3:** Period indicator (Half/Quarter/Innings)
- **Index 4-9:** Available for custom use

### Counters (CNTS)
```
*#1CNTSx,MV,0000

x = Counter index (1-7)
M = Mode (A=Add, D=Decrease, S=Set)
V = Value
```

**Counter Assignments by Sport:**

| Counter | Soccer | AFL | Cricket |
|---------|--------|-----|---------|
| **C1** | HOME Score | HOME Goals | HOME Runs |
| **C2** | AWAY Score | AWAY Goals | AWAY Runs |
| **C3** | - | HOME Points | HOME Wickets |
| **C4** | - | AWAY Points | AWAY Wickets |
| **C5** | - | HOME Total | Extras |
| **C6** | - | AWAY Total | Overs |
| **C7** | - | - | Balls |

### Timer Commands
```
*#1TIMS1,0000  - Start Timer
*#1TIMP1,0000  - Pause Timer
*#1TIMR1,0000  - Reset Timer
```

---

## Display Layouts

### Recommended PowerLED Program Layouts

#### AFL Program Layout
```
┌─────────────────────────────────────────────┐
│  [RAMT3: Quarter]            [Timer]        │
├─────────────────────────────────────────────┤
│                                             │
│  [RAMT1]  [C1][T1][C3]  [C5]               │
│  HOME     Goals Points  Total               │
│                                             │
│  [RAMT2]  [C2][T2][C4]  [C6]               │
│  AWAY     Goals Points  Total               │
│                                             │
└─────────────────────────────────────────────┘
```

#### Soccer Program Layout
```
┌─────────────────────────────────────────────┐
│  [RAMT3: Half]               [Timer]        │
├─────────────────────────────────────────────┤
│                                             │
│  [RAMT1]        [C1]                        │
│  HOME           Score                       │
│                                             │
│  [RAMT2]        [C2]                        │
│  AWAY           Score                       │
│                                             │
└─────────────────────────────────────────────┘
```

#### Cricket Program Layout
```
┌─────────────────────────────────────────────┐
│  [RAMT3: Innings]            [Timer]        │
├─────────────────────────────────────────────┤
│                                             │
│  [RAMT1]  [C1][T3][C3]                     │
│  HOME     Runs / Wickets                    │
│                                             │
│  [RAMT2]  [C2][T4][C4]                     │
│  AWAY     Runs / Wickets                    │
│                                             │
│  [T2]: [C6][T5][C7]    [T1]: [C5]          │
│  Overs: XX.X            Extras: XX          │
│                                             │
└─────────────────────────────────────────────┘
```

---

## Configuration Notes

### Text Formatting
All text areas support:
- **Colours:** 1=Red, 2=Green, 3=Yellow, 4=Blue, 5=Purple, 6=Cyan, 7=White
- **Sizes:** 9=Very Small, 1=Small, 2=Medium, 3=Large, 4=Extra Large
- **Horizontal:** 1=Center, 2=Right, 3=Left
- **Vertical:** 1=Center, 2=Bottom, 3=Top

### Default Settings
- Team names: Red, Large, Centered (1311)
- Period text: Red, Medium, Centered (1211)
- Break screens: White, Medium, Centered (7211)

### Important
- All counters must exist in PowerLED program even if set to 0
- Text areas can be empty but must be defined
- Program switching only works if all required objects exist
- Timer object is optional but recommended

---

## Troubleshooting

**Issue: Scores not displaying**
- Check that all counter objects (C1-C7) exist in the program
- Verify counter is not hidden or off-screen

**Issue: Team names not showing**
- Ensure RAMT1 and RAMT2 exist in program
- Check text area is large enough for team name

**Issue: Program won't switch**
- Verify program exists in PowerLED with correct number
- Check all required objects are present in program

**Issue: AFL totals incorrect**
- Totals are auto-calculated (Goals×6 + Points)
- Do not manually edit C5 or C6 in PowerLED

**Issue: Cricket balls/overs wrong**
- Balls auto-increment over at 6
- Ensure both C6 and C7 exist
- Check decimal separator (T5) is placed correctly

---

## Support

For additional help:
- Check PowerLED manual for object creation
- Verify UDP communication on port 5959
- Test connection with Bypass mode enabled
- Review application console output for errors

**Application Version:** 1.0  
**Last Updated:** 2025-12-06

---

*This guide assumes PowerLED display controller firmware that supports RAMT, CNTS, TIMS/TIMP/TIMR, and PRGC commands as per TF-F6 specification.*
