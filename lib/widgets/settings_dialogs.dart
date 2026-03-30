import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import '../models/app_config.dart';
import '../providers/app_provider.dart';
import '../theme/app_theme.dart';

// ─── Generic Display Style Picker ─────────────────────────────────────────────

/// Shows a bottom-sheet dialog for picking color / size / v-align.
/// Changes are applied live. [onApply] called when user taps Apply.
Future<void> showDisplayStyleDialog(
  BuildContext context, {
  required String title,
  required DisplayStyle initial,
  required void Function(DisplayStyle) onApply,
  bool showHAlign = false,
}) async {
  final isSingleColour =
      context.read<AppProvider>().config.singleColour;
  // In single-colour mode always force red so any live() call can't change it.
  DisplayStyle current =
      isSingleColour ? initial.copyWith(color: '1') : initial;
  await showModalBottomSheet(
    context: context,
    isScrollControlled: true,
    backgroundColor: AppColors.surface,
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
    ),
    builder: (ctx) => StatefulBuilder(
      builder: (ctx, setState) {
        void live(DisplayStyle s) {
          final applied =
              isSingleColour ? s.copyWith(color: '1') : s;
          setState(() => current = applied);
          onApply(applied);
        }

        return Padding(
          padding: EdgeInsets.fromLTRB(20, 20, 20,
              MediaQuery.of(ctx).viewInsets.bottom + 24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Handle
              Center(
                child: Container(
                  width: 40, height: 4,
                  decoration: BoxDecoration(
                    color: AppColors.surfaceBorder,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              const SizedBox(height: 16),
              Text(title, style: Theme.of(ctx).textTheme.headlineSmall),
              const SizedBox(height: 4),
              const Text('Changes apply live on display',
                  style: TextStyle(fontSize: 14, color: AppColors.textMuted)),
              const SizedBox(height: 20),

              // ── Colour (hidden in single-colour mode) ─────────────────────
              if (!isSingleColour) ...[
                _sectionLabel('Colour'),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8, runSpacing: 8,
                  children: kLedColors.map((lc) {
                    final selected = current.color == lc.code;
                    return GestureDetector(
                      onTap: () => live(current.copyWith(color: lc.code)),
                      child: Container(
                        width: 44, height: 44,
                        decoration: BoxDecoration(
                          color: lc.color,
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(
                            color: selected ? Colors.white : Colors.transparent,
                            width: 3,
                          ),
                        ),
                        child: selected
                            ? const Icon(Icons.check, color: Colors.black, size: 18)
                            : null,
                      ),
                    );
                  }).toList(),
                ),
                const SizedBox(height: 18),
              ],

              // ── Size ──────────────────────────────────────────────────────
              _sectionLabel('Size'),
              const SizedBox(height: 8),
              Row(
                children: kLedSizes.map((ls) {
                  final selected = current.size == ls.code;
                  return Expanded(
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 3),
                      child: GestureDetector(
                        onTap: () => live(current.copyWith(size: ls.code)),
                        child: Container(
                          padding: const EdgeInsets.symmetric(vertical: 10),
                          decoration: BoxDecoration(
                            color: selected ? AppColors.accent : AppColors.surfaceHigh,
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Column(
                            children: [
                              Text(ls.label,
                                textAlign: TextAlign.center,
                                style: TextStyle(
                                  fontSize: 15,
                                  fontWeight: FontWeight.bold,
                                  color: selected ? Colors.white : AppColors.textSecondary,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),
                  );
                }).toList(),
              ),
              const SizedBox(height: 18),

              // ── V-Align ───────────────────────────────────────────────────
              _sectionLabel('Vertical Align'),
              const SizedBox(height: 8),
              Row(
                children: kVAlignOptions.map((a) {
                  final selected = current.vAlign == a.code;
                  return Expanded(
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 3),
                      child: GestureDetector(
                        onTap: () => live(current.copyWith(vAlign: a.code)),
                        child: Container(
                          padding: const EdgeInsets.symmetric(vertical: 10),
                          decoration: BoxDecoration(
                            color: selected ? AppColors.accent : AppColors.surfaceHigh,
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Text(a.label,
                            textAlign: TextAlign.center,
                            style: TextStyle(
                              fontSize: 15,
                              fontWeight: FontWeight.bold,
                              color: selected ? Colors.white : AppColors.textSecondary,
                            ),
                          ),
                        ),
                      ),
                    ),
                  );
                }).toList(),
              ),

              if (showHAlign) ...[
                const SizedBox(height: 18),
                _sectionLabel('Horizontal Align'),
                const SizedBox(height: 8),
                Row(
                  children: kHAlignOptions.map((a) {
                    final selected = current.hAlign == a.code;
                    return Expanded(
                      child: Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 3),
                        child: GestureDetector(
                          onTap: () => live(current.copyWith(hAlign: a.code)),
                          child: Container(
                            padding: const EdgeInsets.symmetric(vertical: 10),
                            decoration: BoxDecoration(
                              color: selected ? AppColors.accent : AppColors.surfaceHigh,
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: Text(a.label,
                              textAlign: TextAlign.center,
                              style: TextStyle(
                                fontWeight: FontWeight.bold,
                                color: selected ? Colors.white : AppColors.textSecondary,
                              ),
                            ),
                          ),
                        ),
                      ),
                    );
                  }).toList(),
                ),
              ],

              const SizedBox(height: 24),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: () => Navigator.pop(ctx),
                  child: const Text('Apply & Close'),
                ),
              ),
            ],
          ),
        );
      },
    ),
  );
}

Widget _sectionLabel(String text) => Text(text,
  style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold,
      color: AppColors.textMuted, letterSpacing: 0.8));

// ─── Specific dialogs ─────────────────────────────────────────────────────────

void showTeamNameSettingsDialog(BuildContext context) {
  final app = context.read<AppProvider>();
  final sport = app.config.currentSport;
  DisplayStyle initial;
  void Function(DisplayStyle) onApply;

  if (sport == 'AFL') {
    initial = app.config.aflTeamStyle;
    onApply = app.updateAflTeamStyle;
  } else if (sport == 'Cricket') {
    initial = app.config.cricketTeamStyle;
    onApply = app.updateCricketTeamStyle;
  } else {
    initial = app.config.teamStyle;
    onApply = app.updateTeamStyle;
  }

  showDisplayStyleDialog(context,
    title: 'Team Name Style',
    initial: initial,
    onApply: onApply,
  );
}

void showTimerSettingsDialog(BuildContext context) {
  final app            = context.read<AppProvider>();
  final isAfl          = app.config.currentSport == 'AFL';
  final isSingleColour = app.config.singleColour;
  DisplayStyle current = isSingleColour
      ? app.config.timerStyle.copyWith(color: '1')
      : app.config.timerStyle;
  int offset = isAfl ? app.config.timerOffsetAfl : app.config.timerOffsetDefault;

  showModalBottomSheet(
    context: context,
    isScrollControlled: true,
    backgroundColor: AppColors.surface,
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
    ),
    builder: (ctx) => StatefulBuilder(
      builder: (ctx, setState) {
        void live(DisplayStyle s) {
          final applied = isSingleColour ? s.copyWith(color: '1') : s;
          setState(() => current = applied);
          app.updateTimerStyle(applied);
        }

        return Padding(
          padding: EdgeInsets.fromLTRB(20, 20, 20,
              MediaQuery.of(ctx).viewInsets.bottom + 24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Handle
              Center(
                child: Container(width: 40, height: 4,
                  decoration: BoxDecoration(color: AppColors.surfaceBorder,
                      borderRadius: BorderRadius.circular(2))),
              ),
              const SizedBox(height: 16),
              const Text('Timer Style',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white)),
              const SizedBox(height: 4),
              const Text('Changes apply live on display',
                  style: TextStyle(fontSize: 14, color: AppColors.textMuted)),
              const SizedBox(height: 20),

              // ── Colour (hidden in single-colour mode) ──────────────────
              if (!isSingleColour) ...[
                _sectionLabel('Colour'),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8, runSpacing: 8,
                  children: kLedColors.map((lc) {
                    final selected = current.color == lc.code;
                    return GestureDetector(
                      onTap: () => live(current.copyWith(color: lc.code)),
                      child: Container(
                        width: 44, height: 44,
                        decoration: BoxDecoration(
                          color: lc.color,
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(
                            color: selected ? Colors.white : Colors.transparent,
                            width: 3),
                        ),
                        child: selected
                            ? const Icon(Icons.check, color: Colors.black, size: 18)
                            : null,
                      ),
                    );
                  }).toList(),
                ),
                const SizedBox(height: 18),
              ],

              // ── Size ────────────────────────────────────────────────────
              _sectionLabel('Size'),
              const SizedBox(height: 8),
              Row(
                children: kLedSizes.map((ls) {
                  final selected = current.size == ls.code;
                  return Expanded(
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 3),
                      child: GestureDetector(
                        onTap: () => live(current.copyWith(size: ls.code)),
                        child: Container(
                          padding: const EdgeInsets.symmetric(vertical: 10),
                          decoration: BoxDecoration(
                            color: selected ? AppColors.accent : AppColors.surfaceHigh,
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Text(ls.label,
                            textAlign: TextAlign.center,
                            style: TextStyle(
                              fontWeight: FontWeight.bold,
                              color: selected ? Colors.white : AppColors.textSecondary,
                            ),
                          ),
                        ),
                      ),
                    ),
                  );
                }).toList(),
              ),
              const SizedBox(height: 18),

              // ── V-Align ─────────────────────────────────────────────────
              _sectionLabel('Vertical Align'),
              const SizedBox(height: 8),
              Row(
                children: kVAlignOptions.map((a) {
                  final selected = current.vAlign == a.code;
                  return Expanded(
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 3),
                      child: GestureDetector(
                        onTap: () => live(current.copyWith(vAlign: a.code)),
                        child: Container(
                          padding: const EdgeInsets.symmetric(vertical: 10),
                          decoration: BoxDecoration(
                            color: selected ? AppColors.accent : AppColors.surfaceHigh,
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Text(a.label,
                            textAlign: TextAlign.center,
                            style: TextStyle(
                              fontSize: 15,
                              fontWeight: FontWeight.bold,
                              color: selected ? Colors.white : AppColors.textSecondary,
                            ),
                          ),
                        ),
                      ),
                    ),
                  );
                }).toList(),
              ),
              const SizedBox(height: 18),

              // ── Leading Spaces ──────────────────────────────────────────
              Row(children: [
                _sectionLabel('Shift to Right'),
                const Spacer(),
                _Stepper(
                  value: offset,
                  onChanged: (v) {
                    setState(() => offset = v);
                    app.updateTimerOffset(isAfl, v);
                  },
                ),
              ]),
              const SizedBox(height: 24),

              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: () => Navigator.pop(ctx),
                  child: const Text('Done'),
                ),
              ),
            ],
          ),
        );
      },
    ),
  );
}

void showShotClockSettingsDialog(BuildContext context) {
  final app = context.read<AppProvider>();
  showDisplayStyleDialog(context,
    title: 'Shot Clock Style',
    initial: app.config.shotClockStyle,
    onApply: app.updateShotClockStyle,
  );
}

void showAflQuarterSettingsDialog(BuildContext context) {
  final app = context.read<AppProvider>();
  final isSingleColour = app.config.singleColour;
  DisplayStyle current = isSingleColour
      ? app.config.aflQuarterStyle.copyWith(color: '1')
      : app.config.aflQuarterStyle;
  bool numberOnly = app.config.aflQuarterNumberOnly;

  showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    backgroundColor: AppColors.surface,
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
    ),
    builder: (ctx) => StatefulBuilder(
      builder: (ctx, setState) {
        void live(DisplayStyle s) {
          final applied = isSingleColour ? s.copyWith(color: '1') : s;
          setState(() => current = applied);
          app.updateAflQuarterStyle(applied);
        }

        return Padding(
          padding: EdgeInsets.fromLTRB(20, 20, 20,
              MediaQuery.of(ctx).viewInsets.bottom + 24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Center(
                child: Container(
                  width: 40, height: 4,
                  margin: const EdgeInsets.only(bottom: 16),
                  decoration: BoxDecoration(
                    color: AppColors.surfaceBorder,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              Text('Quarter Style',
                  style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white)),
              const SizedBox(height: 16),

              // ── Number Only checkbox ─────────────────────────────────
              GestureDetector(
                onTap: () {
                  setState(() => numberOnly = !numberOnly);
                  app.setAflQuarterNumberOnly(numberOnly);
                },
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                  decoration: BoxDecoration(
                    color: numberOnly
                        ? AppColors.accent.withOpacity(0.12)
                        : AppColors.surfaceHigh,
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(
                      color: numberOnly ? AppColors.accent : AppColors.surfaceBorder,
                    ),
                  ),
                  child: Row(
                    children: [
                      Icon(
                        numberOnly ? Icons.check_box : Icons.check_box_outline_blank,
                        color: numberOnly ? AppColors.accent : AppColors.textMuted,
                        size: 22,
                      ),
                      const SizedBox(width: 10),
                      const Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text('Number only',
                                style: TextStyle(
                                    fontSize: 14,
                                    fontWeight: FontWeight.bold,
                                    color: Colors.white)),
                            Text('Show 1, 2, 3, 4 instead of Q1, Q2, Q3, Q4',
                                style: TextStyle(
                                    fontSize: 11, color: AppColors.textMuted)),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),

              // ── Colour ───────────────────────────────────────────────
              _sectionLabel('Colour'),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8, runSpacing: 8,
                children: kLedColors.map((lc) {
                  final selected = current.color == lc.code;
                  return GestureDetector(
                    onTap: isSingleColour ? null : () => live(current.copyWith(color: lc.code)),
                    child: Container(
                      width: 44, height: 44,
                      decoration: BoxDecoration(
                        color: lc.color,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(
                          color: selected ? Colors.white : Colors.transparent,
                          width: 3,
                        ),
                      ),
                      child: selected
                          ? const Icon(Icons.check, color: Colors.black, size: 18)
                          : null,
                    ),
                  );
                }).toList(),
              ),
              const SizedBox(height: 16),

              // ── Size ─────────────────────────────────────────────────
              _sectionLabel('Size'),
              const SizedBox(height: 8),
              Row(
                children: kLedSizes.map((ls) {
                  final selected = current.size == ls.code;
                  return Expanded(
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 3),
                      child: GestureDetector(
                        onTap: () => live(current.copyWith(size: ls.code)),
                        child: Container(
                          padding: const EdgeInsets.symmetric(vertical: 10),
                          decoration: BoxDecoration(
                            color: selected ? AppColors.accent : AppColors.surfaceHigh,
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: Text(ls.label,
                            textAlign: TextAlign.center,
                            style: TextStyle(
                              fontWeight: FontWeight.bold, fontSize: 12,
                              color: selected ? Colors.white : AppColors.textSecondary,
                            ),
                          ),
                        ),
                      ),
                    ),
                  );
                }).toList(),
              ),
              const SizedBox(height: 16),

              // ── Vertical Align ───────────────────────────────────────
              _sectionLabel('Vertical Align'),
              const SizedBox(height: 8),
              Row(
                children: kVAlignOptions.map((a) {
                  final selected = current.vAlign == a.code;
                  return Expanded(
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 3),
                      child: GestureDetector(
                        onTap: () => live(current.copyWith(vAlign: a.code)),
                        child: Container(
                          padding: const EdgeInsets.symmetric(vertical: 10),
                          decoration: BoxDecoration(
                            color: selected ? AppColors.accent : AppColors.surfaceHigh,
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: Text(a.label,
                            textAlign: TextAlign.center,
                            style: TextStyle(
                              fontWeight: FontWeight.bold, fontSize: 12,
                              color: selected ? Colors.white : AppColors.textSecondary,
                            ),
                          ),
                        ),
                      ),
                    ),
                  );
                }).toList(),
              ),
              const SizedBox(height: 16),

              // ── Horizontal Align ─────────────────────────────────────
              _sectionLabel('Horizontal Align'),
              const SizedBox(height: 8),
              Row(
                children: kHAlignOptions.map((a) {
                  final selected = current.hAlign == a.code;
                  return Expanded(
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 3),
                      child: GestureDetector(
                        onTap: () => live(current.copyWith(hAlign: a.code)),
                        child: Container(
                          padding: const EdgeInsets.symmetric(vertical: 10),
                          decoration: BoxDecoration(
                            color: selected ? AppColors.accent : AppColors.surfaceHigh,
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: Text(a.label,
                            textAlign: TextAlign.center,
                            style: TextStyle(
                              fontWeight: FontWeight.bold, fontSize: 12,
                              color: selected ? Colors.white : AppColors.textSecondary,
                            ),
                          ),
                        ),
                      ),
                    ),
                  );
                }).toList(),
              ),
            ],
          ),
        );
      },
    ),
  );
}

// ─── Counter Channel Remapping ────────────────────────────────────────────────

/// Fields per sport: list of (fieldKey, displayLabel) tuples.
const Map<String, List<(String, String)>> _kSportCounterFields = {
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
  'Basketball': [
    ('homeScore',    'Home Points'),
    ('awayScore',    'Away Points'),
    ('homeTimeouts', 'Home Timeouts'),
    ('awayTimeouts', 'Away Timeouts'),
    ('homeFouls',    'Home Fouls'),
    ('awayFouls',    'Away Fouls'),
  ],
};

const List<(String, String)> _kSimpleSportFields = [
  ('homeScore', 'Home Score'),
  ('awayScore', 'Away Score'),
];

/// Opens a bottom sheet for remapping CNTS counter channels for [sport].
void showCounterSettingsDialog(BuildContext context, String sport) {
  showModalBottomSheet(
    context: context,
    isScrollControlled: true,
    backgroundColor: AppColors.surface,
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
    ),
    builder: (ctx) => _CounterSettingsSheet(sport: sport),
  );
}

class _CounterSettingsSheet extends StatefulWidget {
  final String sport;
  const _CounterSettingsSheet({required this.sport});
  @override
  State<_CounterSettingsSheet> createState() => _CounterSettingsSheetState();
}

class _CounterSettingsSheetState extends State<_CounterSettingsSheet> {
  @override
  Widget build(BuildContext context) {
    final app    = context.read<AppProvider>();
    final fields = _kSportCounterFields[widget.sport] ?? _kSimpleSportFields;

    return StatefulBuilder(
      builder: (ctx, setS) => Padding(
        padding: EdgeInsets.fromLTRB(20, 20, 20,
            MediaQuery.of(ctx).viewInsets.bottom + 24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Handle
            Center(
              child: Container(
                width: 40, height: 4,
                decoration: BoxDecoration(
                  color: AppColors.surfaceBorder,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
            const SizedBox(height: 16),
            Text('Counter Channels — ${widget.sport}',
              style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white)),
            const SizedBox(height: 4),
            const Text('Remap which CNTS number each field uses.',
              style: TextStyle(fontSize: 14, color: AppColors.textMuted)),
            const SizedBox(height: 20),

            // Column headers
            Row(children: [
              const SizedBox(width: 130),
              ...List.generate(6, (i) => Expanded(
                child: Text('${i + 1}',
                  textAlign: TextAlign.center,
                  style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: AppColors.textMuted)),
              )),
            ]),
            const SizedBox(height: 6),

            // One row per field
            ...fields.map(((String, String) pair) {
              final field = pair.$1;
              final label = pair.$2;
              final current = app.counterFor(widget.sport, field);
              return Padding(
                padding: const EdgeInsets.symmetric(vertical: 4),
                child: Row(
                  children: [
                    SizedBox(
                      width: 130,
                      child: Text(label,
                        style: const TextStyle(fontSize: 15, color: Colors.white, fontWeight: FontWeight.w500)),
                    ),
                    ...List.generate(6, (i) {
                      final n = i + 1;
                      final selected = current == n;
                      return Expanded(
                        child: GestureDetector(
                          onTap: () {
                            app.setCounterChannel(widget.sport, field, n);
                            setS(() {});
                          },
                          child: Container(
                            margin: const EdgeInsets.symmetric(horizontal: 2),
                            padding: const EdgeInsets.symmetric(vertical: 9),
                            decoration: BoxDecoration(
                              color: selected ? AppColors.accent : AppColors.surfaceHigh,
                              borderRadius: BorderRadius.circular(6),
                            ),
                            child: Text('$n',
                              textAlign: TextAlign.center,
                              style: TextStyle(
                                fontSize: 15,
                                fontWeight: FontWeight.bold,
                                color: selected ? Colors.white : AppColors.textSecondary,
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

            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: () {
                      app.clearCounterChannels(widget.sport);
                      setS(() {});
                    },
                    style: OutlinedButton.styleFrom(
                      foregroundColor: AppColors.textMuted,
                      side: const BorderSide(color: AppColors.surfaceBorder),
                    ),
                    child: const Text('Reset Defaults'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: ElevatedButton(
                    onPressed: () => Navigator.pop(ctx),
                    style: ElevatedButton.styleFrom(backgroundColor: AppColors.accent),
                    child: const Text('Done'),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

// ─── Stepper widget ────────────────────────────────────────────────────────────
class _Stepper extends StatelessWidget {
  final int value;
  final ValueChanged<int> onChanged;
  final int min; final int max;
  const _Stepper({required this.value, required this.onChanged, this.min = 0, this.max = 10});
  @override
  Widget build(BuildContext context) {
    return Row(children: [
      IconButton(
        icon: const Icon(Icons.remove_circle_outline, color: AppColors.textSecondary),
        onPressed: value > min ? () => onChanged(value - 1) : null,
      ),
      SizedBox(width: 36, child: Text('$value',
        textAlign: TextAlign.center,
        style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white),
      )),
      IconButton(
        icon: const Icon(Icons.add_circle_outline, color: AppColors.textSecondary),
        onPressed: value < max ? () => onChanged(value + 1) : null,
      ),
    ]);
  }
}
