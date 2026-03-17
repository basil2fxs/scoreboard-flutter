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
                  style: TextStyle(fontSize: 12, color: AppColors.textMuted)),
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
  style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold,
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
                  style: TextStyle(fontSize: 12, color: AppColors.textMuted)),
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
                _sectionLabel('Leading Spaces'),
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
  showDisplayStyleDialog(context,
    title: 'Quarter Style',
    initial: app.config.aflQuarterStyle,
    onApply: app.updateAflQuarterStyle,
    showHAlign: true,
  );
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
