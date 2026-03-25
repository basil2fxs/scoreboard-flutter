import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_provider.dart';
import '../theme/app_theme.dart';

// ─── Fields available per sport ───────────────────────────────────────────────

const Map<String, List<(String, String)>> _kSportFields = {
  'AFL': [
    ('homeGoals',  'Home Goals'),
    ('homePoints', 'Home Points'),
    ('homeTotal',  'Home Total'),
    ('awayGoals',  'Away Goals'),
    ('awayPoints', 'Away Points'),
    ('awayTotal',  'Away Total'),
  ],
  'Cricket': [
    ('homeRuns',     'Home Runs'),
    ('homeWickets',  'Home Wickets'),
    ('awayRuns',     'Away Runs'),
    ('awayWickets',  'Away Wickets'),
    ('extras',       'Extras'),
    ('overs',        'Overs'),
  ],
  'Soccer': [
    ('homeScore', 'Home Score'),
    ('awayScore', 'Away Score'),
  ],
  'Rugby': [
    ('homeScore', 'Home Score'),
    ('awayScore', 'Away Score'),
  ],
  'Hockey': [
    ('homeScore', 'Home Score'),
    ('awayScore', 'Away Score'),
  ],
  'Basketball': [
    ('homeScore',    'Home Points'),
    ('awayScore',    'Away Points'),
    ('homeTimeouts', 'Home Timeouts'),
    ('awayTimeouts', 'Away Timeouts'),
    ('homeFouls',    'Home Fouls'),
    ('awayFouls',    'Away Fouls'),
  ],
};

const List<(String, String)> _kDefaultFields = [
  ('homeScore', 'Home Score'),
  ('awayScore', 'Away Score'),
];

bool _hasShotClock(String sport) =>
    sport == 'Hockey' || sport == 'Basketball';

bool _hasAflQuarter(String sport) => sport == 'AFL';

bool _hasExtraSlot(String sport) =>
    _hasShotClock(sport) || _hasAflQuarter(sport);

// ─── Screen ───────────────────────────────────────────────────────────────────

class RemappingScreen extends StatefulWidget {
  final String sport;
  const RemappingScreen({super.key, required this.sport});

  @override
  State<RemappingScreen> createState() => _RemappingScreenState();
}

class _RemappingScreenState extends State<RemappingScreen> {
  // Counter channels
  late Map<String, int> _channels;

  // Hardware timer channels (laptop mode only)
  late int _timerChannel;
  late int _shotClockChannel;

  // RAMT slots — stored as independent lists (normal mode only)
  late List<int> _ramtHomeSlots;
  late List<int> _ramtAwaySlots;
  late List<int> _ramtTimerSlots;
  late int       _ramtShotClockSlot;

  @override
  void initState() {
    super.initState();
    final app = context.read<AppProvider>();
    final fields = _kSportFields[widget.sport] ?? _kDefaultFields;

    _channels = {
      for (final (field, _) in fields)
        field: app.counterFor(widget.sport, field),
    };

    _timerChannel     = app.config.timerChannel;
    _shotClockChannel = app.config.shotClockChannel;

    _ramtHomeSlots     = List<int>.from(app.config.ramtHomeSlots);
    _ramtAwaySlots     = List<int>.from(app.config.ramtAwaySlots);
    _ramtTimerSlots    = List<int>.from(app.config.ramtTimerSlots);
    _ramtShotClockSlot = app.config.ramtShotClockSlot;
  }

  bool get _hasChanges {
    final app = context.read<AppProvider>();
    final isLaptop = app.laptopScoring;
    final fields = _kSportFields[widget.sport] ?? _kDefaultFields;

    for (final (field, _) in fields) {
      if (_channels[field] != app.counterFor(widget.sport, field)) return true;
    }
    if (isLaptop) {
      if (_timerChannel     != app.config.timerChannel)     return true;
      if (_hasShotClock(widget.sport) &&
          _shotClockChannel != app.config.shotClockChannel) return true;
    } else {
      if (!_listEq(_ramtHomeSlots,  app.config.ramtHomeSlots))  return true;
      if (!_listEq(_ramtAwaySlots,  app.config.ramtAwaySlots))  return true;
      if (!_listEq(_ramtTimerSlots, app.config.ramtTimerSlots)) return true;
      if (_hasExtraSlot(widget.sport) &&
          _ramtShotClockSlot != app.config.ramtShotClockSlot) return true;
    }
    return false;
  }

  static bool _listEq(List<int> a, List<int> b) {
    if (a.length != b.length) return false;
    for (int i = 0; i < a.length; i++) {
      if (a[i] != b[i]) return false;
    }
    return true;
  }

  Future<bool> _confirmDiscard() async {
    if (!_hasChanges) return true;
    final leave = await showDialog<bool>(
      context: context,
      builder: (d) => AlertDialog(
        backgroundColor: AppColors.surface,
        title: const Row(children: [
          Icon(Icons.warning_amber_rounded, color: AppColors.warning, size: 22),
          SizedBox(width: 8),
          Text('Unsaved Changes'),
        ]),
        content: const Text(
          'You have unsaved remapping changes. Leave without saving?',
          style: TextStyle(color: AppColors.textSecondary, fontSize: 16),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(d, false),
            child: const Text('Keep Editing'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(d, true),
            style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.danger,
                foregroundColor: Colors.white),
            child: const Text('Discard'),
          ),
        ],
      ),
    );
    return leave ?? false;
  }

  void _save() {
    final app = context.read<AppProvider>();
    final isLaptop = app.laptopScoring;
    final fields = _kSportFields[widget.sport] ?? _kDefaultFields;

    for (final (field, _) in fields) {
      app.setCounterChannel(widget.sport, field, _channels[field]!);
    }

    if (isLaptop) {
      app.setTimerChannel(_timerChannel);
      if (_hasShotClock(widget.sport)) {
        app.setShotClockChannel(_shotClockChannel);
      }
    } else {
      app.setRamtSlots(
        homeSlots    : _ramtHomeSlots,
        awaySlots    : _ramtAwaySlots,
        timerSlots   : _ramtTimerSlots,
        shotClockSlot: _hasExtraSlot(widget.sport)
            ? _ramtShotClockSlot
            : app.config.ramtShotClockSlot,
      );
    }

    Navigator.pop(context);
  }

  Future<void> _resetToDefaults() async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (d) => AlertDialog(
        backgroundColor: AppColors.surface,
        title: const Text('Reset Remapping'),
        content: Text(
          'Reset all ${widget.sport} remapping to factory defaults?',
          style: const TextStyle(color: AppColors.textSecondary, fontSize: 16),
        ),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(d, false),
              child: const Text('Cancel')),
          ElevatedButton(
            onPressed: () => Navigator.pop(d, true),
            style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.danger,
                foregroundColor: Colors.white),
            child: const Text('Reset'),
          ),
        ],
      ),
    );
    if (ok != true || !mounted) return;

    final app = context.read<AppProvider>();
    app.clearCounterChannels(widget.sport);

    setState(() {
      final fields = _kSportFields[widget.sport] ?? _kDefaultFields;
      for (final (field, _) in fields) {
        _channels[field] = app.counterFor(widget.sport, field);
      }
      _timerChannel      = 1;
      _shotClockChannel  = 2;
      _ramtHomeSlots     = [1, 2];
      _ramtAwaySlots     = [3, 4];
      _ramtTimerSlots    = [5, 6, 7];
      _ramtShotClockSlot = 8;
    });
  }

  @override
  Widget build(BuildContext context) {
    final app      = context.watch<AppProvider>();
    final fields   = _kSportFields[widget.sport] ?? _kDefaultFields;
    final isLaptop = app.laptopScoring;

    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, _) async {
        if (didPop) return;
        final ok = await _confirmDiscard();
        if (ok && context.mounted) Navigator.pop(context);
      },
      child: Scaffold(
        backgroundColor: AppColors.background,
        appBar: AppBar(
          backgroundColor: AppColors.surface,
          title: const Text('Remapping',
              style: TextStyle(fontWeight: FontWeight.bold)),
          actions: [
            Padding(
              padding: const EdgeInsets.only(right: 12),
              child: ElevatedButton(
                onPressed: _save,
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.success,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
                  textStyle: const TextStyle(fontWeight: FontWeight.bold),
                  elevation: 0,
                ),
                child: const Text('Save'),
              ),
            ),
          ],
        ),
        body: SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [

              // ── Intro ──────────────────────────────────────────────────────
              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: AppColors.accent.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: AppColors.accent.withOpacity(0.3)),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.info_outline, size: 18, color: AppColors.accent),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        isLaptop
                            ? 'Laptop mode: configure counter channels and hardware timer channels.'
                            : 'Reassign counter channels and RAMT display slots. '
                              'Each slot can be set independently to any slot 1–8.',
                        style: const TextStyle(
                            fontSize: 13, color: AppColors.textSecondary),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 24),

              // ── Counter Channels ───────────────────────────────────────────
              _heading('COUNTER CHANNELS (CNTS)'),
              const SizedBox(height: 4),
              const Text(
                'Choose which hardware counter slot (1–6) each field maps to.',
                style: TextStyle(fontSize: 13, color: AppColors.textMuted),
              ),
              const SizedBox(height: 12),

              // Column headers
              Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Row(
                  children: [
                    const SizedBox(width: 140),
                    ...List.generate(6, (i) => Expanded(
                      child: Text('${i + 1}',
                        textAlign: TextAlign.center,
                        style: const TextStyle(
                          fontSize: 13, fontWeight: FontWeight.bold,
                          color: AppColors.textMuted)),
                    )),
                  ],
                ),
              ),

              ...fields.map(((String, String) pair) {
                final (field, label) = pair;
                final current = _channels[field] ?? 1;
                return Padding(
                  padding: const EdgeInsets.symmetric(vertical: 4),
                  child: Row(
                    children: [
                      SizedBox(
                        width: 140,
                        child: Text(label,
                          style: const TextStyle(
                              fontSize: 14, color: Colors.white,
                              fontWeight: FontWeight.w500)),
                      ),
                      ...List.generate(6, (i) {
                        final n = i + 1;
                        final sel = current == n;
                        return Expanded(
                          child: GestureDetector(
                            onTap: () => setState(() => _channels[field] = n),
                            child: Container(
                              margin: const EdgeInsets.symmetric(horizontal: 2),
                              padding: const EdgeInsets.symmetric(vertical: 10),
                              decoration: BoxDecoration(
                                color: sel ? AppColors.accent : AppColors.surfaceHigh,
                                borderRadius: BorderRadius.circular(6),
                              ),
                              child: Text('$n',
                                textAlign: TextAlign.center,
                                style: TextStyle(
                                  fontSize: 14,
                                  fontWeight: FontWeight.bold,
                                  color: sel ? Colors.white : AppColors.textSecondary,
                                ),
                              ),
                            ),
                          ),
                        );
                      }),
                    ],
                  ),
                );
              }),

              // ── Laptop mode: Timer Channels ────────────────────────────────
              if (isLaptop) ...[
                const SizedBox(height: 28),
                _heading('TIMER CHANNELS'),
                const SizedBox(height: 4),
                const Text(
                  'Select which hardware timer channel drives each clock.',
                  style: TextStyle(fontSize: 13, color: AppColors.textMuted),
                ),
                const SizedBox(height: 12),

                _timerChannelRow(
                  label: 'Game Timer',
                  selected: _timerChannel,
                  color: AppColors.accent,
                  onSelect: (n) => setState(() => _timerChannel = n),
                ),

                if (_hasShotClock(widget.sport)) ...[
                  const SizedBox(height: 10),
                  _timerChannelRow(
                    label: 'Shot Clock',
                    selected: _shotClockChannel,
                    color: AppColors.warning,
                    onSelect: (n) => setState(() => _shotClockChannel = n),
                  ),
                ],
              ],

              // ── Normal mode: RAMT Display Slots ───────────────────────────
              if (!isLaptop) ...[
                const SizedBox(height: 32),
                _heading('RAMT DISPLAY SLOTS'),
                const SizedBox(height: 4),
                const Text(
                  'Assign any slot (1–8) to each position independently.',
                  style: TextStyle(fontSize: 13, color: AppColors.textMuted),
                ),
                const SizedBox(height: 16),

                _RamtMultiSlotPicker(
                  label: 'Home Team Name',
                  color: AppColors.homeTeam,
                  slots: _ramtHomeSlots,
                  positionLabels: const ['Part 1', 'Part 2'],
                  onChanged: (updated) =>
                      setState(() => _ramtHomeSlots = updated),
                ),
                const SizedBox(height: 12),

                _RamtMultiSlotPicker(
                  label: 'Away Team Name',
                  color: AppColors.awayTeam,
                  slots: _ramtAwaySlots,
                  positionLabels: const ['Part 1', 'Part 2'],
                  onChanged: (updated) =>
                      setState(() => _ramtAwaySlots = updated),
                ),
                const SizedBox(height: 12),

                _RamtMultiSlotPicker(
                  label: 'Timer',
                  color: AppColors.accent,
                  slots: _ramtTimerSlots,
                  positionLabels: const ['Slot 1', 'Slot 2', 'Slot 3'],
                  onChanged: (updated) =>
                      setState(() => _ramtTimerSlots = updated),
                ),

                if (_hasExtraSlot(widget.sport)) ...[
                  const SizedBox(height: 12),
                  _RamtMultiSlotPicker(
                    label: _hasAflQuarter(widget.sport)
                        ? 'AFL Quarter'
                        : 'Shot Clock',
                    color: AppColors.warning,
                    slots: [_ramtShotClockSlot],
                    positionLabels: const ['Slot'],
                    onChanged: (updated) =>
                        setState(() => _ramtShotClockSlot = updated[0]),
                  ),
                ],
              ],

              const SizedBox(height: 36),

              // ── Reset ──────────────────────────────────────────────────────
              SizedBox(
                width: double.infinity,
                child: OutlinedButton.icon(
                  onPressed: _resetToDefaults,
                  icon: const Icon(Icons.restore, size: 20),
                  label: const Text('Reset to Factory Defaults',
                      style: TextStyle(
                          fontSize: 15, fontWeight: FontWeight.bold)),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: AppColors.danger,
                    side: const BorderSide(color: AppColors.danger, width: 1.5),
                    padding: const EdgeInsets.symmetric(vertical: 16),
                    shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(10)),
                  ),
                ),
              ),
              const SizedBox(height: 24),
            ],
          ),
        ),
      ),
    );
  }

  Widget _timerChannelRow({
    required String label,
    required int selected,
    required Color color,
    required ValueChanged<int> onSelect,
  }) {
    return Row(
      children: [
        SizedBox(
          width: 100,
          child: Text(label,
              style: const TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                  color: Colors.white)),
        ),
        ...List.generate(4, (i) {
          final n = i + 1;
          final sel = selected == n;
          return Expanded(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 3),
              child: GestureDetector(
                onTap: () => onSelect(n),
                child: Container(
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  decoration: BoxDecoration(
                    color: sel ? color : AppColors.surfaceHigh,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text('Ch $n',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.bold,
                      color: sel ? Colors.white : AppColors.textSecondary,
                    ),
                  ),
                ),
              ),
            ),
          );
        }),
      ],
    );
  }
}

// ─── RAMT multi-slot picker: each position picks any slot 1–8 ─────────────────

class _RamtMultiSlotPicker extends StatelessWidget {
  final String label;
  final Color color;
  final List<int> slots;           // one entry per position
  final List<String> positionLabels;
  final ValueChanged<List<int>> onChanged;

  const _RamtMultiSlotPicker({
    required this.label,
    required this.color,
    required this.slots,
    required this.positionLabels,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
      decoration: BoxDecoration(
        color: AppColors.surfaceHigh,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AppColors.surfaceBorder),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Row(
            children: [
              Container(
                width: 12, height: 12,
                decoration: BoxDecoration(color: color, shape: BoxShape.circle),
              ),
              const SizedBox(width: 8),
              Text(label,
                  style: const TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.bold,
                      color: Colors.white)),
            ],
          ),
          const SizedBox(height: 10),

          // One row per slot position
          for (int pos = 0; pos < slots.length; pos++) ...[
            if (pos > 0) const SizedBox(height: 6),
            Row(
              children: [
                // Position label
                SizedBox(
                  width: 52,
                  child: Text(
                    positionLabels[pos],
                    style: const TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: AppColors.textMuted),
                  ),
                ),
                // 8 slot buttons
                ...List.generate(8, (i) {
                  final n = i + 1;
                  final sel = slots[pos] == n;
                  return Expanded(
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 2),
                      child: GestureDetector(
                        onTap: () {
                          final updated = List<int>.from(slots);
                          updated[pos] = n;
                          onChanged(updated);
                        },
                        child: Container(
                          padding: const EdgeInsets.symmetric(vertical: 8),
                          decoration: BoxDecoration(
                            color: sel ? color : AppColors.surface,
                            borderRadius: BorderRadius.circular(6),
                            border: Border.all(
                              color: sel ? color : AppColors.surfaceBorder,
                            ),
                          ),
                          child: Text('$n',
                            textAlign: TextAlign.center,
                            style: TextStyle(
                              fontSize: 13,
                              fontWeight: FontWeight.bold,
                              color: sel ? Colors.white : AppColors.textSecondary,
                            ),
                          ),
                        ),
                      ),
                    ),
                  );
                }),
              ],
            ),
          ],
        ],
      ),
    );
  }
}

Widget _heading(String text) => Text(text,
  style: const TextStyle(
    fontSize: 12, fontWeight: FontWeight.w800,
    color: AppColors.textSecondary, letterSpacing: 1.0,
  ));
