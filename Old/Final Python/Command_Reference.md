# TF-CNT / TF-F6 Serial Control – Complete README

## 1. Connection Settings

| Setting | Value |
|--------|-------|
| **Port** | COM14 (or your RS232 port) |
| **Baud Rate** | 57600 |
| **Data Bits** | 8 |
| **Parity** | None |
| **Stop Bits** | 1 |
| **Flow Control** | None |

---

## 2. Packet Structure (ALL Commands Use This)

Every command must follow:

```
[Header][ScreenID][Instruction][Partition][,][Content][Check]
```

| Field | Example | Meaning |
|-------|---------|---------|
| `[Header]` | `*#` | Always starts with `*#` |
| `[ScreenID]` | `1` | Controller ID (0 = broadcast) |
| `[Instruction]` | `RAMT`, `PRGC`, `TIMS`, `CNTS` | Command type |
| `[Partition]` | `1`, `12`, etc. | Which area(s) the command applies to |
| `,` | comma | Required for area-based commands |
| `[Content]` | varies | Text, mode, values |
| `[Check]` | `0000` | Use `0000` to skip checksum |

---

## 3. Custom Text Area (RAMT)

### Command Format
```
*#1RAMTx,ABCD[text]0000
```

### Parameter Guide

| Letter | Meaning | Values |
|--------|---------|--------|
| **x** | Text area |1=Small 2=Medium 3=Large 4=Largest 5-8=Medium 9=Very Small|
| **A** | Color | 1 Red, 2 Green, 3 Yellow, 4 Blue, 5 Purple, 6 Cyan, 7 White, 8 Black |
| **B** | Size | 1 Small, 2 Medium, 3 Large, 4 Largest |
| **C** | H-Align | 1 Center, 2 Right, 3 Left |
| **D** | V-Align | 1 Center, 2 Bottom, 3 Top |
| **[text]** | ASCII text | No Unicode |
| `0000` | Check | Always use |

### Examples

```
*#1RAMT1,1311Hello World0000
*#1RAMT1,3212Processing...0000
*#1RAMT1,7343Access Granted0000
```

---

## 4. Timer Controls

### Start Timer
```
*#1TIMS1,0000
```

### Pause Timer
```
*#1TIMP1,0000
```

### Reset Timer
```
*#1TIMR1,0000
```

---

## 5. Counting Control (CNTS)

### Format
```
*#1CNTSx,ModeValue,0000
```

### Modes

| Mode | Meaning |
|------|---------|
| `A` | Increase |
| `D` | Decrease |
| `S` | Set direct value |

### Examples

```
*#1CNTS1,A10,0000
*#1CNTS2,D5,0000
*#1CNTS1,S2000,0000
```

---

## 6. Program Switching (PRGC)

### Format
```
*#1PRGCModeProgramIndex,0000
```

### Modes

| Mode | Action |
|------|--------|
| 1 | Previous program |
| 2 | Next program |
| 3 | Jump to program index |

⚠ Program index starts from **0**

### Examples

```
*#1PRGC2,0000        (next)
*#1PRGC1,0000        (previous)
*#1PRGC35,0000       (jump to program 6)
```

---

## 7. Sending Commands via Windows PowerShell

### Open COM port
```powershell
$port = new-Object System.IO.Ports.SerialPort COM14,57600,None,8,One
$port.Open()
```

### Send commands
```powershell
$port.Write("*#1RAMT1,1211Please SwipeAccess Card0000")
$port.Write("*#1RAMT1,3211Processing0000")
$port.Write("*#1RAMT1,2231    Gate Opening...0000")
$port.Write("*#1RAMT1,1211     No Tailgating0000")
```

### Close port
```powershell
$port.Close()
```

---

## 8. Return Codes

| Code | Meaning |
|------|---------|
| 00 | Success |
| 04 | Parameter error |
| 05 | Instruction format error |
| 06 | Out of range |
| 0A | Length error |

---

## 9. Important Timing Rules

- Minimum delay between full packets: **100ms**
- Max delay between bytes in same packet: **10ms**
- Timer is approximate (not industrial-accurate)
- Count resets on power loss unless user data bit enables memory

---

## 10. Supported Models

| Controller | Support |
|------------|---------|
| TF-CNT-D | Full |
| TF-CNT-F | Full |
| TF-F6 | RAMT + PRGC |
| TF-M3U / TF-M5NUR | Limited |
| TF-AU / TF-MU / TF-S5U | None |
