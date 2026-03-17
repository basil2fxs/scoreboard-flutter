import 'dart:ui' show FontFeature;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import '../providers/app_provider.dart';
import '../theme/app_theme.dart';
import 'settings_dialogs.dart';
import 'section_card.dart';

class TimerWidget extends StatelessWidget {
  const TimerWidget({super.key});

  @override
  Widget build(BuildContext context) {
    final app         = context.watch<AppProvider>();
    final isCountdown = app.config.timerCountdown;
    final isRunning   = app.timerRunning;

    return SectionCard(
      title: 'TIMER',
      trailing: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Set Time button
          _HeaderBtn(
            label: 'Set Time',
            icon: Icons.timer_outlined,
            onTap: () => _showSetTimeDialog(context, app),
          ),
          const SizedBox(width: 6),
          // Style / offset settings
          SettingsIconButton(onTap: () => showTimerSettingsDialog(context)),
        ],
      ),
      child: Column(
        children: [
          // ── Mode badge ────────────────────────────────────────────────────
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
                decoration: BoxDecoration(
                  color: isCountdown
                      ? AppColors.warning.withOpacity(0.18)
                      : AppColors.success.withOpacity(0.18),
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(
                    color: isCountdown
                        ? AppColors.warning.withOpacity(0.45)
                        : AppColors.success.withOpacity(0.45),
                  ),
                ),
                child: Text(
                  isCountdown ? '⏷  COUNT DOWN' : '⏶  COUNT UP',
                  style: TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.bold,
                    letterSpacing: 0.8,
                    color: isCountdown ? AppColors.warning : AppColors.success,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),

          // ── Big MM:SS display ─────────────────────────────────────────────
          Container(
            padding: const EdgeInsets.symmetric(vertical: 8),
            alignment: Alignment.center,
            child: Text(
              app.timerDisplay,
              style: const TextStyle(
                fontSize: 56,
                fontWeight: FontWeight.bold,
                color: AppColors.timerGreen,
                fontFeatures: [FontFeature.tabularFigures()],
              ),
            ),
          ),
          const SizedBox(height: 8),

          // ── Control buttons ───────────────────────────────────────────────
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: [
              _TimerBtn(
                label: isRunning ? '⏸ Pause' : '▶ Start',
                color: isRunning ? AppColors.warning : AppColors.success,
                onTap: () => isRunning
                    ? context.read<AppProvider>().pauseTimer()
                    : context.read<AppProvider>().startTimer(),
              ),
              _TimerBtn(
                label: '↺ Reset',
                color: AppColors.danger,
                onTap: () => context.read<AppProvider>().resetTimer(),
              ),
            ],
          ),
        ],
      ),
    );
  }

  /// Shows the Set Time bottom sheet.
  void _showSetTimeDialog(BuildContext context, AppProvider app) {
    bool countdown = app.config.timerCountdown;
    final targetSecs = app.config.timerCountdown ? app.config.timerTargetSeconds : 0;
    final initMins = targetSecs ~/ 60;
    final initSecs = targetSecs % 60;

    final minsCtrl = TextEditingController(
        text: initMins.toString().padLeft(2, '0'));
    final secsCtrl = TextEditingController(
        text: initSecs.toString().padLeft(2, '0'));

    // Validation error strings — live across setState calls via closure
    String? minsError;
    String? secsError;

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppColors.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setState) {
          void applyQuick(int totalSeconds) {
            minsCtrl.text = (totalSeconds ~/ 60).toString().padLeft(2, '0');
            secsCtrl.text = (totalSeconds % 60).toString().padLeft(2, '0');
            setState(() { minsError = null; secsError = null; });
          }

          return Padding(
            padding: EdgeInsets.fromLTRB(
                20, 20, 20, MediaQuery.of(ctx).viewInsets.bottom + 24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Handle
                Center(
                  child: Container(
                    width: 40,
                    height: 4,
                    decoration: BoxDecoration(
                      color: AppColors.surfaceBorder,
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                const Text(
                  'Set Timer',
                  style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                      color: Colors.white),
                ),
                const SizedBox(height: 20),

                // ── Count Up / Count Down toggle ──────────────────────────
                Row(
                  children: [
                    Expanded(
                      child: GestureDetector(
                        onTap: () => setState(() => countdown = false),
                        child: Container(
                          padding: const EdgeInsets.symmetric(vertical: 12),
                          decoration: BoxDecoration(
                            color: !countdown
                                ? AppColors.success
                                : AppColors.surfaceHigh,
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child: Column(
                            children: [
                              Icon(Icons.trending_up,
                                  size: 20,
                                  color: !countdown
                                      ? Colors.white
                                      : AppColors.textMuted),
                              const SizedBox(height: 4),
                              Text(
                                'Count Up',
                                style: TextStyle(
                                  fontWeight: FontWeight.bold,
                                  fontSize: 13,
                                  color: !countdown
                                      ? Colors.white
                                      : AppColors.textMuted,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: GestureDetector(
                        onTap: () => setState(() => countdown = true),
                        child: Container(
                          padding: const EdgeInsets.symmetric(vertical: 12),
                          decoration: BoxDecoration(
                            color: countdown
                                ? AppColors.warning
                                : AppColors.surfaceHigh,
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child: Column(
                            children: [
                              Icon(Icons.trending_down,
                                  size: 20,
                                  color: countdown
                                      ? Colors.white
                                      : AppColors.textMuted),
                              const SizedBox(height: 4),
                              Text(
                                'Count Down',
                                style: TextStyle(
                                  fontWeight: FontWeight.bold,
                                  fontSize: 13,
                                  color: countdown
                                      ? Colors.white
                                      : AppColors.textMuted,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 20),

                // ── Time inputs (countdown only) ──────────────────────────
                if (countdown) ...[
                  const _SectionLabel('Start Time'),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: minsCtrl,
                          keyboardType: TextInputType.number,
                          inputFormatters: [
                            FilteringTextInputFormatter.digitsOnly
                          ],
                          textAlign: TextAlign.center,
                          style: const TextStyle(
                            fontSize: 32,
                            fontWeight: FontWeight.bold,
                            color: Colors.white,
                            fontFeatures: [FontFeature.tabularFigures()],
                          ),
                          onChanged: (_) => setState(() => minsError = null),
                          decoration: _timeFieldDecoration('MIN')
                              .copyWith(errorText: minsError),
                        ),
                      ),
                      const Padding(
                        padding: EdgeInsets.symmetric(horizontal: 14),
                        child: Text(':',
                            style: TextStyle(
                                fontSize: 36,
                                fontWeight: FontWeight.bold,
                                color: Colors.white)),
                      ),
                      Expanded(
                        child: TextField(
                          controller: secsCtrl,
                          keyboardType: TextInputType.number,
                          inputFormatters: [
                            FilteringTextInputFormatter.digitsOnly,
                            _MaxValueFormatter(59),
                          ],
                          textAlign: TextAlign.center,
                          style: const TextStyle(
                            fontSize: 32,
                            fontWeight: FontWeight.bold,
                            color: Colors.white,
                            fontFeatures: [FontFeature.tabularFigures()],
                          ),
                          onChanged: (_) => setState(() => secsError = null),
                          decoration: _timeFieldDecoration('SEC')
                              .copyWith(errorText: secsError),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  const _SectionLabel('Quick Set'),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      _QuickChip(
                          label: '10:00',
                          onTap: () => applyQuick(10 * 60)),
                      _QuickChip(
                          label: '12:00',
                          onTap: () => applyQuick(12 * 60)),
                      _QuickChip(
                          label: '15:00',
                          onTap: () => applyQuick(15 * 60)),
                      _QuickChip(
                          label: '20:00',
                          onTap: () => applyQuick(20 * 60)),
                      _QuickChip(
                          label: '25:00',
                          onTap: () => applyQuick(25 * 60)),
                      _QuickChip(
                          label: '45:00',
                          onTap: () => applyQuick(45 * 60)),
                    ],
                  ),
                ] else ...[
                  Container(
                    padding: const EdgeInsets.all(14),
                    decoration: BoxDecoration(
                      color: AppColors.surfaceHigh,
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Row(
                      children: [
                        Icon(Icons.info_outline,
                            size: 16, color: AppColors.textMuted),
                        SizedBox(width: 8),
                        Text('Timer will count up from 00:00',
                            style: TextStyle(
                                color: AppColors.textMuted, fontSize: 13)),
                      ],
                    ),
                  ),
                ],

                const SizedBox(height: 24),
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton(
                    onPressed: () {
                      // Validate: countdown requires both fields filled
                      if (countdown) {
                        final mBlank = minsCtrl.text.trim().isEmpty;
                        final sBlank = secsCtrl.text.trim().isEmpty;
                        if (mBlank || sBlank) {
                          setState(() {
                            minsError = mBlank ? 'Enter minutes' : null;
                            secsError = sBlank ? 'Enter seconds' : null;
                          });
                          return; // stay open
                        }
                      }
                      final m = int.tryParse(minsCtrl.text) ?? 0;
                      final s =
                          (int.tryParse(secsCtrl.text) ?? 0).clamp(0, 59);
                      final total = m * 60 + s;
                      context.read<AppProvider>().setTimerTime(
                            countdown: countdown,
                            totalSeconds: countdown ? total : 0,
                          );
                      Navigator.pop(ctx);
                    },
                    style: ElevatedButton.styleFrom(
                        backgroundColor: AppColors.accent),
                    child: const Text('Set & Reset Timer',
                        style: TextStyle(fontWeight: FontWeight.bold)),
                  ),
                ),
              ],
            ),
          );
        },
      ),
    ).then((_) {
      minsCtrl.dispose();
      secsCtrl.dispose();
    });
  }

  InputDecoration _timeFieldDecoration(String label) => InputDecoration(
        labelText: label,
        labelStyle:
            const TextStyle(fontSize: 12, color: AppColors.textMuted),
        filled: true,
        fillColor: AppColors.background,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: AppColors.surfaceBorder),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: AppColors.surfaceBorder),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide:
              const BorderSide(color: AppColors.accent, width: 2),
        ),
      );
}

// ─── Max-value input formatter ─────────────────────────────────────────────────

class _MaxValueFormatter extends TextInputFormatter {
  final int max;
  const _MaxValueFormatter(this.max);
  @override
  TextEditingValue formatEditUpdate(
      TextEditingValue old, TextEditingValue val) {
    if (val.text.isEmpty) return val;
    final n = int.tryParse(val.text);
    if (n == null || n > max) return old;
    return val;
  }
}

// ─── Small header button (Set Time) ───────────────────────────────────────────

class _HeaderBtn extends StatelessWidget {
  final String label;
  final IconData icon;
  final VoidCallback onTap;
  const _HeaderBtn(
      {required this.label, required this.icon, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
        decoration: BoxDecoration(
          color: AppColors.surfaceHigh,
          borderRadius: BorderRadius.circular(8),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 14, color: AppColors.textSecondary),
            const SizedBox(width: 4),
            Text(label,
                style: const TextStyle(
                    fontSize: 12,
                    color: AppColors.textSecondary,
                    fontWeight: FontWeight.bold)),
          ],
        ),
      ),
    );
  }
}

// ─── Timer control button ──────────────────────────────────────────────────────

class _TimerBtn extends StatelessWidget {
  final String label;
  final Color color;
  final VoidCallback onTap;
  const _TimerBtn(
      {required this.label, required this.color, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return ElevatedButton(
      onPressed: onTap,
      style: ElevatedButton.styleFrom(
        backgroundColor: color,
        padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 13),
        shape:
            RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        elevation: 0,
      ),
      child: Text(label,
          style: const TextStyle(
              fontWeight: FontWeight.bold, color: Colors.white)),
    );
  }
}

// ─── Quick-set chip ────────────────────────────────────────────────────────────

class _QuickChip extends StatelessWidget {
  final String label;
  final VoidCallback onTap;
  const _QuickChip({required this.label, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 7),
        decoration: BoxDecoration(
          color: AppColors.surfaceHigh,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: AppColors.surfaceBorder),
        ),
        child: Text(label,
            style: const TextStyle(
                fontSize: 13,
                color: Colors.white,
                fontWeight: FontWeight.bold)),
      ),
    );
  }
}

// ─── Section sub-label ─────────────────────────────────────────────────────────

class _SectionLabel extends StatelessWidget {
  final String text;
  const _SectionLabel(this.text);
  @override
  Widget build(BuildContext context) => Text(
        text,
        style: const TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.bold,
            color: AppColors.textMuted,
            letterSpacing: 0.8),
      );
}
