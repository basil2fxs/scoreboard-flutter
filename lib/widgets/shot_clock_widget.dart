import 'dart:ui' show FontFeature;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import '../providers/app_provider.dart';
import '../theme/app_theme.dart';
import 'settings_dialogs.dart';
import 'section_card.dart';

/// Shot clock widget. Pass [hasReset] = true for Basketball, false for Hockey.
class ShotClockWidget extends StatelessWidget {
  final bool hasReset;
  const ShotClockWidget({super.key, this.hasReset = false});

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppProvider>();

    return SectionCard(
      title: 'SHOT CLOCK',
      trailing: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Set Time button
          _SetTimeBtn(onTap: () => _showSetTimeDialog(context, app)),
          const SizedBox(width: 6),
          // Style settings
          SettingsIconButton(
              onTap: () => showShotClockSettingsDialog(context)),
        ],
      ),
      child: Column(
        children: [
          // ── Big seconds display ───────────────────────────────────────────
          Container(
            padding: const EdgeInsets.symmetric(vertical: 10),
            alignment: Alignment.center,
            child: Text(
              '${app.shotClockSecondsLive}',
              style: TextStyle(
                fontSize: 56,
                fontWeight: FontWeight.bold,
                color: app.shotClockVisible
                    ? AppColors.timerGreen
                    : AppColors.textMuted,
                fontFeatures: const [FontFeature.tabularFigures()],
              ),
            ),
          ),
          const SizedBox(height: 8),

          // ── Control buttons ───────────────────────────────────────────────
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: [
              _ShotBtn(
                label: '▶ Start',
                color: AppColors.success,
                onTap: () => context.read<AppProvider>().shotClockStart(),
              ),
              _ShotBtn(
                label: '■ Stop',
                color: AppColors.danger,
                onTap: () => context.read<AppProvider>().shotClockStop(),
              ),
              if (hasReset)
                _ShotBtn(
                  label: '↺ Reset',
                  color: AppColors.warning,
                  onTap: () => context.read<AppProvider>().shotClockReset(),
                ),
            ],
          ),
        ],
      ),
    );
  }

  /// Shows the Set Shot-Clock Time bottom sheet.
  void _showSetTimeDialog(BuildContext context, AppProvider app) {
    final sport = app.config.currentSport ?? '';
    final initSecs = app.config.shotClockSeconds;
    final secsCtrl =
        TextEditingController(text: initSecs.toString());

    // Common quick-set values (seconds)
    final chips = sport == 'Hockey'
        ? [20, 30, 40, 60]
        : [14, 20, 24, 30]; // Basketball defaults

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppColors.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setState) {
          void applyQuick(int s) {
            secsCtrl.text = s.toString();
            setState(() {});
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
                  'Set Shot Clock',
                  style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                      color: Colors.white),
                ),
                const SizedBox(height: 6),
                const Text(
                  'Sets the default reset value in seconds.',
                  style:
                      TextStyle(fontSize: 12, color: AppColors.textMuted),
                ),
                const SizedBox(height: 20),

                // ── Seconds input ─────────────────────────────────────────
                _SubLabel('Seconds'),
                const SizedBox(height: 8),
                TextField(
                  controller: secsCtrl,
                  keyboardType: TextInputType.number,
                  inputFormatters: [
                    FilteringTextInputFormatter.digitsOnly
                  ],
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    fontSize: 36,
                    fontWeight: FontWeight.bold,
                    color: Colors.white,
                    fontFeatures: [FontFeature.tabularFigures()],
                  ),
                  decoration: InputDecoration(
                    labelText: 'SECONDS',
                    labelStyle: const TextStyle(
                        fontSize: 12, color: AppColors.textMuted),
                    filled: true,
                    fillColor: AppColors.background,
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(10),
                      borderSide:
                          const BorderSide(color: AppColors.surfaceBorder),
                    ),
                    enabledBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(10),
                      borderSide:
                          const BorderSide(color: AppColors.surfaceBorder),
                    ),
                    focusedBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(10),
                      borderSide: const BorderSide(
                          color: AppColors.accent, width: 2),
                    ),
                  ),
                ),
                const SizedBox(height: 16),

                // ── Quick chips ───────────────────────────────────────────
                _SubLabel('Quick Set'),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: chips
                      .map((s) => _QuickChip(
                          label: '${s}s', onTap: () => applyQuick(s)))
                      .toList(),
                ),
                const SizedBox(height: 24),

                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton(
                    onPressed: () {
                      final s = int.tryParse(secsCtrl.text) ?? initSecs;
                      if (s > 0) {
                        context
                            .read<AppProvider>()
                            .setShotClockDefault(s.clamp(1, 999));
                      }
                      Navigator.pop(ctx);
                    },
                    style: ElevatedButton.styleFrom(
                        backgroundColor: AppColors.accent),
                    child: const Text('Set Shot Clock',
                        style:
                            TextStyle(fontWeight: FontWeight.bold)),
                  ),
                ),
              ],
            ),
          );
        },
      ),
    ).then((_) => secsCtrl.dispose());
  }
}

// ─── Sub-label ─────────────────────────────────────────────────────────────────

class _SubLabel extends StatelessWidget {
  final String text;
  const _SubLabel(this.text);
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

// ─── Small "Set Time" header button ────────────────────────────────────────────

class _SetTimeBtn extends StatelessWidget {
  final VoidCallback onTap;
  const _SetTimeBtn({required this.onTap});

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
        child: const Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.timer_outlined, size: 14, color: AppColors.textSecondary),
            SizedBox(width: 4),
            Text('Set Time',
                style: TextStyle(
                    fontSize: 12,
                    color: AppColors.textSecondary,
                    fontWeight: FontWeight.bold)),
          ],
        ),
      ),
    );
  }
}

// ─── Shot clock control button ─────────────────────────────────────────────────

class _ShotBtn extends StatelessWidget {
  final String label;
  final Color color;
  final VoidCallback onTap;
  const _ShotBtn(
      {required this.label, required this.color, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return ElevatedButton(
      onPressed: onTap,
      style: ElevatedButton.styleFrom(
        backgroundColor: color,
        padding:
            const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
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
