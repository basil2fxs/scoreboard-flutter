import 'udp_service.dart';
import '../models/app_config.dart';

/// Builds and sends all RAMT / CNTS / TIMS commands to the TF-F6 controller.
class RamtService {
  final UdpService udp;
  RamtService(this.udp);

  /// When true, double chars-per-slot for ultra-wide displays.
  bool ultraWide = false;

  /// When true, all RAMT sends are forced to colour '1' (red).
  bool singleColour = false;

  // ─── Chunk size lookup (LED size code → chars per RAMT slot) ──────────────
  static int chunkSize(String sizeCode) =>
      const {'4': 1, '3': 2, '2': 4, '1': 7, '9': 10}[sizeCode] ?? 4;

  /// Effective chunk size — doubled for ultra-wide screens.
  int effectiveChunkSize(String sizeCode) {
    final base = chunkSize(sizeCode);
    return ultraWide ? base * 2 : base;
  }

  // ─── Low-level RAMT send ──────────────────────────────────────────────────

  void sendRamt(int slot, String color, String size, String hAlign, String vAlign, String text) {
    final c = singleColour ? '1' : color;
    udp.send('*#1RAMT$slot,${c}${size}${hAlign}${vAlign}${text}0000');
  }

  // ─── Program select ───────────────────────────────────────────────────────

  void sendProgram(String programNum) {
    udp.send('*#1PRGC3${programNum},0000');
  }

  // ─── Counter commands ─────────────────────────────────────────────────────

  void setCounter(int n, int value) =>
      udp.send('*#1CNTS$n,S$value,0000');

  void addCounter(int n, int delta) =>
      udp.send('*#1CNTS$n,A$delta,0000');

  void subtractCounter(int n, int delta) =>
      udp.send('*#1CNTS$n,D$delta,0000');

  // ─── Hardware timer commands (Laptop mode) ────────────────────────────────

  void sendHardwareTimerStart(int n) => udp.send('*#1TIMS$n,0000');
  void sendHardwareTimerPause(int n) => udp.send('*#1TIMP$n,0000');
  void sendHardwareTimerReset(int n) => udp.send('*#1TIMR$n,0000');

  // ─── Team name (2 RAMT slots — any 2 slots) ──────────────────────────────
  void sendTeamName(String name, List<int> slots, DisplayStyle style) {
    const hAlign = '3'; // always Left
    final vAlign = style.vAlign;
    final cs = effectiveChunkSize(style.size);
    final src = name.isEmpty ? ' ' : name;
    final chunks = <String>[];
    for (int i = 0; i < src.length; i += cs) {
      chunks.add(src.substring(i, (i + cs).clamp(0, src.length)));
    }
    while (chunks.length < slots.length) chunks.add(' ');
    for (int i = 0; i < slots.length; i++) {
      sendRamt(slots[i], style.color, style.size, hAlign, vAlign, chunks[i]);
    }
  }

  // ─── Timer (3 RAMT slots — any 3 slots) ──────────────────────────────────
  void sendTimer(int totalSeconds, DisplayStyle style, int leadingSpaces,
      {List<int> slots = const [5, 6, 7]}) {
    final mins = totalSeconds ~/ 60;
    final secs = totalSeconds  % 60;
    final raw  = '${'$mins'.padLeft(2,'0')}:${'$secs'.padLeft(2,'0')}';
    final text = (' ' * leadingSpaces) + raw;
    final cs   = effectiveChunkSize(style.size);
    final src  = text.isEmpty ? ' ' : text;
    final chunks = <String>[];
    for (int i = 0; i < src.length; i += cs) {
      chunks.add(src.substring(i, (i + cs).clamp(0, src.length)));
    }
    while (chunks.length < slots.length) chunks.add(' ');
    for (int i = 0; i < slots.length; i++) {
      sendRamt(slots[i], style.color, style.size, style.hAlign, style.vAlign, chunks[i]);
    }
  }

  // ─── Shot clock ───────────────────────────────────────────────────────────
  void sendShotClock(int seconds, DisplayStyle style, {int slot = 8}) {
    sendRamt(slot, style.color, style.size, style.hAlign, style.vAlign, '$seconds');
  }

  void clearRamt8(DisplayStyle style, {int slot = 8}) {
    sendRamt(slot, style.color, style.size, style.hAlign, style.vAlign, ' ');
  }

  // ─── AFL Quarter ──────────────────────────────────────────────────────────
  void sendAflQuarter(int quarter, DisplayStyle style, {int slot = 8}) {
    if (quarter == 0) {
      sendRamt(slot, style.color, style.size, style.hAlign, style.vAlign, ' ');
    } else {
      sendRamt(slot, style.color, style.size, style.hAlign, style.vAlign, 'Q$quarter');
    }
  }

  // ─── Advertisement row ────────────────────────────────────────────────────
  void sendAdRow(int slot, String color, String size, String hAlign, String vAlign, String text) {
    sendRamt(slot, color, size, hAlign, vAlign, text);
  }

  // ─── Blank display ────────────────────────────────────────────────────────
  void blankDisplay() {
    udp.send('*#1RAMT1,1211 0000');
  }
}
