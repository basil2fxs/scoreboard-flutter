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
    final app      = context.watch<AppProvider>();
    final isLaptop = app.laptopScoring;

    return SectionCard(
      title: 'SHOT CLOCK',
      trailing: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          _SetTimeBtn(onTap: () => _showSetTimeDialog(context, app)),
          const SizedBox(width: 6),
          // Hide style settings in laptop mode
          if (!isLaptop)
            SettingsIconButton(onTap: () => showShotClockSettingsDialog(context)),
        ],
      ),
      child: Column(
        children: [
          if (isLaptop)
            Padding(
              padding: const EdgeInsets.only(bottom: 4),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: AppColors.accent.withOpacity(0.18),
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: AppColors.accent.withOpacity(0.45)),
                ),
                child: Text(
                  'HW TIMER ${app.config.shotClockChannel}',
                  style: const TextStyle(
                    fontSize: 9,
                    fontWeight: FontWeight.bold,
                    letterSpacing: 0.8,
                    color: AppColors.accent,
                  ),
                ),
              ),
            ),

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
      builder: (_) => _SetShotClockSheet(app: app),
    );
  }
}

// ─── Set Shot Clock sheet ──────────────────────────────────────────────────────

class _SetShotClockSheet extends StatefulWidget {
  final AppProvider app;
  const _SetShotClockSheet({required this.app});
  @override
  State<_SetShotClockSheet> createState() => _SetShotClockSheetState();
}

class _SetShotClockSheetState extends State<_SetShotClockSheet> {
  late TextEditingController _secsCtrl;
  late int _initSecs;
  late List<int> _chips;
  late int _shotClockChannel;
  String? _secsError;

  @override
  void initState() {
    super.initState();
    _initSecs        = widget.app.config.shotClockSeconds;
    _shotClockChannel = widget.app.config.shotClockChannel;
    _secsCtrl = TextEditingController(text: _initSecs.toString());
    final sport = widget.app.config.currentSport ?? '';
    _chips = sport == 'Hockey' ? [20, 30, 40, 45, 60] : [14, 20, 24, 30];
  }

  @override
  void dispose() {
    _secsCtrl.dispose();
    super.dispose();
  }

  void _applyQuick(int s) {
    _secsCtrl.text = s.toString();
    if (mounted) setState(() => _secsError = null);
  }

  void _submit() {
    if (_secsCtrl.text.trim().isEmpty) {
      if (mounted) setState(() => _secsError = 'Enter seconds');
      return;
    }
    final s = int.tryParse(_secsCtrl.text) ?? _initSecs;
    if (s > 0) {
      widget.app.setShotClockDefault(s.clamp(1, 999));
    }
    widget.app.setShotClockChannel(_shotClockChannel);
    if (mounted) Navigator.pop(context);
  }

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
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text('Set Shot Clock',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white)),
              TextButton(
                onPressed: () { if (mounted) Navigator.pop(context); },
                child: const Text('Cancel',
                    style: TextStyle(color: AppColors.textMuted, fontWeight: FontWeight.bold)),
              ),
            ],
          ),
          const Text('Sets the default reset value in seconds.',
              style: TextStyle(fontSize: 12, color: AppColors.textMuted)),
          const SizedBox(height: 20),

          _SubLabel('Seconds'),
          const SizedBox(height: 8),
          TextField(
            controller: _secsCtrl,
            keyboardType: TextInputType.number,
            inputFormatters: [FilteringTextInputFormatter.digitsOnly],
            textAlign: TextAlign.center,
            style: const TextStyle(fontSize: 36, fontWeight: FontWeight.bold,
                color: Colors.white, fontFeatures: [FontFeature.tabularFigures()]),
            onChanged: (_) { if (mounted) setState(() => _secsError = null); },
            decoration: InputDecoration(
              labelText: 'SECONDS',
              labelStyle: const TextStyle(fontSize: 12, color: AppColors.textMuted),
              errorText: _secsError,
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
            ),
          ),
          const SizedBox(height: 16),

          _SubLabel('Quick Set'),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8, runSpacing: 8,
            children: _chips
                .map((s) => _QuickChip(label: '${s}s', onTap: () => _applyQuick(s)))
                .toList(),
          ),

          // ── Hardware Timer Channel (laptop mode) ─────────────────────────
          if (isLaptop) ...[
            const SizedBox(height: 16),
            _SubLabel('Hardware Timer Channel'),
            const SizedBox(height: 8),
            Row(children: [
              _ChannelChip(
                label: 'Timer 1',
                selected: _shotClockChannel == 1,
                onTap: () { if (mounted) setState(() => _shotClockChannel = 1); },
              ),
              const SizedBox(width: 10),
              _ChannelChip(
                label: 'Timer 2',
                selected: _shotClockChannel == 2,
                onTap: () { if (mounted) setState(() => _shotClockChannel = 2); },
              ),
            ]),
          ],

          const SizedBox(height: 24),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: _submit,
              style: ElevatedButton.styleFrom(backgroundColor: AppColors.accent),
              child: const Text('Set Shot Clock', style: TextStyle(fontWeight: FontWeight.bold)),
            ),
          ),
        ],
      ),
    );
  }
}

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

class _SubLabel extends StatelessWidget {
  final String text;
  const _SubLabel(this.text);
  @override
  Widget build(BuildContext context) => Text(text,
    style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold,
        color: AppColors.textMuted, letterSpacing: 0.8));
}

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
            Text('Set Time', style: TextStyle(
                fontSize: 12, color: AppColors.textSecondary, fontWeight: FontWeight.bold)),
          ],
        ),
      ),
    );
  }
}

class _ShotBtn extends StatelessWidget {
  final String label;
  final Color color;
  final VoidCallback onTap;
  const _ShotBtn({required this.label, required this.color, required this.onTap});
  @override
  Widget build(BuildContext context) {
    return ElevatedButton(
      onPressed: onTap,
      style: ElevatedButton.styleFrom(
        backgroundColor: color,
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        elevation: 0,
      ),
      child: Text(label,
          style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.white)),
    );
  }
}

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
            style: const TextStyle(fontSize: 13, color: Colors.white, fontWeight: FontWeight.bold)),
      ),
    );
  }
}
