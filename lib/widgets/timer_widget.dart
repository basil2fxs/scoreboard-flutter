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
    final isLaptop    = app.laptopScoring;

    return SectionCard(
      title: 'TIMER',
      trailing: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          _HeaderBtn(
            label: 'Set Time',
            icon: Icons.timer_outlined,
            onTap: () => _showSetTimeDialog(context, app),
          ),
          const SizedBox(width: 6),
          // Hide style settings in laptop mode
          if (!isLaptop)
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
              if (isLaptop) ...[
                const SizedBox(width: 8),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: AppColors.accent.withOpacity(0.18),
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: AppColors.accent.withOpacity(0.45)),
                  ),
                  child: Text(
                    'HW TIMER ${app.config.timerChannel}',
                    style: const TextStyle(
                      fontSize: 9,
                      fontWeight: FontWeight.bold,
                      letterSpacing: 0.8,
                      color: AppColors.accent,
                    ),
                  ),
                ),
              ],
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

  void _showSetTimeDialog(BuildContext context, AppProvider app) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      isDismissible: false,
      enableDrag: false,
      backgroundColor: AppColors.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (_) => _SetTimerSheet(app: app),
    );
  }
}

// ─── Set Timer sheet ──────────────────────────────────────────────────────────

class _SetTimerSheet extends StatefulWidget {
  final AppProvider app;
  const _SetTimerSheet({required this.app});
  @override
  State<_SetTimerSheet> createState() => _SetTimerSheetState();
}

class _SetTimerSheetState extends State<_SetTimerSheet> {
  late bool _countdown;
  late TextEditingController _minsCtrl;
  late TextEditingController _secsCtrl;
  late int _timerChannel;
  String? _minsError;
  String? _secsError;

  @override
  void initState() {
    super.initState();
    _countdown    = widget.app.config.timerCountdown;
    _timerChannel = widget.app.config.timerChannel;
    final targetSecs = _countdown ? widget.app.config.timerTargetSeconds : 0;
    _minsCtrl = TextEditingController(
        text: (targetSecs ~/ 60).toString().padLeft(2, '0'));
    _secsCtrl = TextEditingController(
        text: (targetSecs % 60).toString().padLeft(2, '0'));
  }

  @override
  void dispose() {
    _minsCtrl.dispose();
    _secsCtrl.dispose();
    super.dispose();
  }

  void _applyQuick(int totalSeconds) {
    _minsCtrl.text = (totalSeconds ~/ 60).toString().padLeft(2, '0');
    _secsCtrl.text = (totalSeconds % 60).toString().padLeft(2, '0');
    if (mounted) setState(() { _minsError = null; _secsError = null; });
  }

  void _submit() {
    if (_countdown) {
      final mBlank = _minsCtrl.text.trim().isEmpty;
      final sBlank = _secsCtrl.text.trim().isEmpty;
      if (mBlank || sBlank) {
        if (mounted) setState(() {
          _minsError = mBlank ? 'Enter minutes' : null;
          _secsError = sBlank ? 'Enter seconds' : null;
        });
        return;
      }
    }
    final m = int.tryParse(_minsCtrl.text) ?? 0;
    final s = (int.tryParse(_secsCtrl.text) ?? 0).clamp(0, 59);
    widget.app.setTimerChannel(_timerChannel);
    widget.app.setTimerTime(
      countdown: _countdown,
      totalSeconds: _countdown ? m * 60 + s : 0,
    );
    if (mounted) Navigator.pop(context);
  }

  static InputDecoration _field(String label, String? error) => InputDecoration(
    labelText: label,
    labelStyle: const TextStyle(fontSize: 12, color: AppColors.textMuted),
    errorText: error,
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
      borderSide: const BorderSide(color: AppColors.accent, width: 2),
    ),
  );

  @override
  Widget build(BuildContext context) {
    final bottomInset = MediaQuery.of(context).viewInsets.bottom;
    final isLaptop    = widget.app.laptopScoring;
    return Padding(
      padding: EdgeInsets.fromLTRB(20, 20, 20, bottomInset + 24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // ── Header ─────────────────────────────────────────────────────
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text('Set Timer',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white)),
              TextButton(
                onPressed: () { if (mounted) Navigator.pop(context); },
                child: const Text('Cancel',
                    style: TextStyle(color: AppColors.textMuted, fontWeight: FontWeight.bold)),
              ),
            ],
          ),
          const SizedBox(height: 8),

          // ── Count Up / Down toggle ──────────────────────────────────────
          Row(children: [
            Expanded(
              child: GestureDetector(
                onTap: () { if (mounted) setState(() => _countdown = false); },
                child: Container(
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  decoration: BoxDecoration(
                    color: !_countdown ? AppColors.success : AppColors.surfaceHigh,
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Column(children: [
                    Icon(Icons.trending_up, size: 20,
                        color: !_countdown ? Colors.white : AppColors.textMuted),
                    const SizedBox(height: 4),
                    Text('Count Up', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13,
                        color: !_countdown ? Colors.white : AppColors.textMuted)),
                  ]),
                ),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: GestureDetector(
                onTap: () { if (mounted) setState(() => _countdown = true); },
                child: Container(
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  decoration: BoxDecoration(
                    color: _countdown ? AppColors.warning : AppColors.surfaceHigh,
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Column(children: [
                    Icon(Icons.trending_down, size: 20,
                        color: _countdown ? Colors.white : AppColors.textMuted),
                    const SizedBox(height: 4),
                    Text('Count Down', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13,
                        color: _countdown ? Colors.white : AppColors.textMuted)),
                  ]),
                ),
              ),
            ),
          ]),
          const SizedBox(height: 20),

          // ── Time inputs (countdown only) ────────────────────────────────
          if (_countdown) ...[
            const _SectionLabel('Start Time'),
            const SizedBox(height: 8),
            Row(children: [
              Expanded(
                child: TextField(
                  controller: _minsCtrl,
                  keyboardType: TextInputType.number,
                  inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                  textAlign: TextAlign.center,
                  style: const TextStyle(fontSize: 32, fontWeight: FontWeight.bold,
                      color: Colors.white, fontFeatures: [FontFeature.tabularFigures()]),
                  onChanged: (_) { if (mounted) setState(() => _minsError = null); },
                  decoration: _field('MIN', _minsError),
                ),
              ),
              const Padding(
                padding: EdgeInsets.symmetric(horizontal: 14),
                child: Text(':', style: TextStyle(fontSize: 36, fontWeight: FontWeight.bold, color: Colors.white)),
              ),
              Expanded(
                child: TextField(
                  controller: _secsCtrl,
                  keyboardType: TextInputType.number,
                  inputFormatters: [
                    FilteringTextInputFormatter.digitsOnly,
                    _MaxValueFormatter(59),
                  ],
                  textAlign: TextAlign.center,
                  style: const TextStyle(fontSize: 32, fontWeight: FontWeight.bold,
                      color: Colors.white, fontFeatures: [FontFeature.tabularFigures()]),
                  onChanged: (_) { if (mounted) setState(() => _secsError = null); },
                  decoration: _field('SEC', _secsError),
                ),
              ),
            ]),
            const SizedBox(height: 16),
            const _SectionLabel('Quick Set'),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8, runSpacing: 8,
              children: [
                _QuickChip(label: '10:00', onTap: () => _applyQuick(10 * 60)),
                _QuickChip(label: '12:00', onTap: () => _applyQuick(12 * 60)),
                _QuickChip(label: '15:00', onTap: () => _applyQuick(15 * 60)),
                _QuickChip(label: '20:00', onTap: () => _applyQuick(20 * 60)),
                _QuickChip(label: '25:00', onTap: () => _applyQuick(25 * 60)),
                _QuickChip(label: '40:00', onTap: () => _applyQuick(40 * 60)),
                _QuickChip(label: '45:00', onTap: () => _applyQuick(45 * 60)),
              ],
            ),
          ] else ...[
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: AppColors.surfaceHigh,
                borderRadius: BorderRadius.circular(10),
              ),
              child: const Row(children: [
                Icon(Icons.info_outline, size: 16, color: AppColors.textMuted),
                SizedBox(width: 8),
                Text('Timer will count up from 00:00',
                    style: TextStyle(color: AppColors.textMuted, fontSize: 13)),
              ]),
            ),
          ],

          // ── Hardware Timer Channel (laptop mode) ────────────────────────
          if (isLaptop) ...[
            const SizedBox(height: 16),
            const _SectionLabel('Hardware Timer Channel'),
            const SizedBox(height: 8),
            Row(children: [
              _ChannelChip(
                label: 'Timer 1',
                selected: _timerChannel == 1,
                onTap: () { if (mounted) setState(() => _timerChannel = 1); },
              ),
              const SizedBox(width: 10),
              _ChannelChip(
                label: 'Timer 2',
                selected: _timerChannel == 2,
                onTap: () { if (mounted) setState(() => _timerChannel = 2); },
              ),
            ]),
          ],

          const SizedBox(height: 24),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: _submit,
              style: ElevatedButton.styleFrom(backgroundColor: AppColors.accent),
              child: const Text('Set & Reset Timer',
                  style: TextStyle(fontWeight: FontWeight.bold)),
            ),
          ),
        ],
      ),
    );
  }
}

// ─── Channel chip ──────────────────────────────────────────────────────────────

class _ChannelChip extends StatelessWidget {
  final String label;
  final bool selected;
  final VoidCallback onTap;
  const _ChannelChip({required this.label, required this.selected, required this.onTap});
  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: GestureDetector(
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 10),
          decoration: BoxDecoration(
            color: selected ? AppColors.accent : AppColors.surfaceHigh,
            borderRadius: BorderRadius.circular(8),
          ),
          child: Center(
            child: Text(label,
              style: TextStyle(
                fontWeight: FontWeight.bold,
                color: selected ? Colors.white : AppColors.textSecondary,
              ),
            ),
          ),
        ),
      ),
    );
  }
}

// ─── Max-value input formatter ─────────────────────────────────────────────────

class _MaxValueFormatter extends TextInputFormatter {
  final int max;
  const _MaxValueFormatter(this.max);
  @override
  TextEditingValue formatEditUpdate(TextEditingValue old, TextEditingValue val) {
    if (val.text.isEmpty) return val;
    final n = int.tryParse(val.text);
    if (n == null || n > max) return old;
    return val;
  }
}

// ─── Small header button ───────────────────────────────────────────────────────

class _HeaderBtn extends StatelessWidget {
  final String label;
  final IconData icon;
  final VoidCallback onTap;
  const _HeaderBtn({required this.label, required this.icon, required this.onTap});

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
            Text(label, style: const TextStyle(
                fontSize: 12, color: AppColors.textSecondary, fontWeight: FontWeight.bold)),
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
  const _TimerBtn({required this.label, required this.color, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return ElevatedButton(
      onPressed: onTap,
      style: ElevatedButton.styleFrom(
        backgroundColor: color,
        padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 13),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        elevation: 0,
      ),
      child: Text(label,
          style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.white)),
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
                fontSize: 13, color: Colors.white, fontWeight: FontWeight.bold)),
      ),
    );
  }
}

// ─── Section sub-label ─────────────────────────────────────────────────────────

class _SectionLabel extends StatelessWidget {
  final String text;
  const _SectionLabel(this.text);
  @override
  Widget build(BuildContext context) => Text(text,
    style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold,
        color: AppColors.textMuted, letterSpacing: 0.8));
}
