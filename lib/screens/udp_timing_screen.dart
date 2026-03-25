import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import '../providers/app_provider.dart';
import '../theme/app_theme.dart';

/// Settings page for tuning UDP command timing.
/// Changes are applied only when Save is pressed.
class UdpTimingScreen extends StatefulWidget {
  const UdpTimingScreen({super.key});

  @override
  State<UdpTimingScreen> createState() => _UdpTimingScreenState();
}

class _UdpTimingScreenState extends State<UdpTimingScreen> {
  late int _cmdMs;
  late int _initMs;

  @override
  void initState() {
    super.initState();
    final app = context.read<AppProvider>();
    _cmdMs  = app.udpCommandDelayMs;
    _initMs = app.udpInitFlushDelayMs;
  }

  bool get _hasChanges {
    final app = context.read<AppProvider>();
    return _cmdMs != app.udpCommandDelayMs ||
        _initMs != app.udpInitFlushDelayMs;
  }

  void _save() {
    final app = context.read<AppProvider>();
    app.setUdpCommandDelayMs(_cmdMs);
    app.setUdpInitFlushDelayMs(_initMs);
    Navigator.pop(context);
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
          'Leave without saving UDP timing changes?',
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

  @override
  Widget build(BuildContext context) {
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
          title: const Text('UDP Timing',
              style: TextStyle(fontWeight: FontWeight.bold)),
          actions: [
            Padding(
              padding: const EdgeInsets.only(right: 12),
              child: ElevatedButton(
                onPressed: _save,
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.success,
                  foregroundColor: Colors.white,
                  padding:
                      const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
                  textStyle: const TextStyle(fontWeight: FontWeight.bold),
                  elevation: 0,
                ),
                child: const Text('Save'),
              ),
            ),
          ],
        ),
        body: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            // ── Info card ─────────────────────────────────────────────────
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: AppColors.surfaceHigh,
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: AppColors.surfaceBorder),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(Icons.info_outline,
                      size: 20, color: AppColors.accent.withOpacity(0.8)),
                  const SizedBox(width: 10),
                  const Expanded(
                    child: Text(
                      'Lower values send commands faster. The default values '
                      '(120 ms / 500 ms) are the safe maximums — reduce from '
                      'there or type any specific value directly.',
                      style: TextStyle(
                          fontSize: 13, color: AppColors.textSecondary),
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 24),

            // ── Command delay ─────────────────────────────────────────────
            _TimingCard(
              key: const ValueKey('cmdDelay'),
              icon: Icons.send_outlined,
              title: 'Command Delay',
              subtitle: 'Gap between consecutive UDP commands.',
              unit: 'ms',
              value: _cmdMs,
              sliderMax: 120,
              onChanged: (v) => setState(() => _cmdMs = v),
            ),

            const SizedBox(height: 16),

            // ── Boot init flush delay ──────────────────────────────────────
            _TimingCard(
              key: const ValueKey('initDelay'),
              icon: Icons.timer_outlined,
              title: 'Boot Init Delay',
              subtitle:
                  'Wait after zeroing counters before sending real scores on sport entry.',
              unit: 'ms',
              value: _initMs,
              sliderMax: 500,
              onChanged: (v) => setState(() => _initMs = v),
            ),

            const SizedBox(height: 32),

            // ── Reset button ──────────────────────────────────────────────
            SizedBox(
              width: double.infinity,
              child: OutlinedButton.icon(
                icon: const Icon(Icons.restore, size: 18),
                label: const Text('Reset to Defaults'),
                style: OutlinedButton.styleFrom(
                  foregroundColor: AppColors.textSecondary,
                  side: const BorderSide(color: AppColors.surfaceBorder),
                  padding: const EdgeInsets.symmetric(vertical: 14),
                ),
                onPressed: () async {
                  final ok = await showDialog<bool>(
                    context: context,
                    builder: (d) => AlertDialog(
                      backgroundColor: AppColors.surface,
                      title: const Text('Reset UDP Timing'),
                      content: const Text(
                          'Reset command delay to 120 ms and boot init delay to 500 ms?'),
                      actions: [
                        TextButton(
                            onPressed: () => Navigator.pop(d, false),
                            child: const Text('Cancel')),
                        ElevatedButton(
                          onPressed: () => Navigator.pop(d, true),
                          style: ElevatedButton.styleFrom(
                              backgroundColor: AppColors.accent),
                          child: const Text('Reset'),
                        ),
                      ],
                    ),
                  );
                  if (ok == true) {
                    setState(() {
                      _cmdMs  = 120;
                      _initMs = 500;
                    });
                  }
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ─── Timing card — slider + direct text entry ─────────────────────────────────

class _TimingCard extends StatefulWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final String unit;
  final int value;        // current local value
  final int sliderMax;    // upper end of slider (== default value)
  final ValueChanged<int> onChanged;

  const _TimingCard({
    super.key,
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.unit,
    required this.value,
    required this.sliderMax,
    required this.onChanged,
  });

  @override
  State<_TimingCard> createState() => _TimingCardState();
}

class _TimingCardState extends State<_TimingCard> {
  late TextEditingController _ctrl;
  late FocusNode _focus;

  @override
  void initState() {
    super.initState();
    _ctrl  = TextEditingController(text: '${widget.value}');
    _focus = FocusNode()
      ..addListener(() {
        if (!_focus.hasFocus) _applyText();
      });
  }

  @override
  void didUpdateWidget(_TimingCard old) {
    super.didUpdateWidget(old);
    // Sync text when value changes externally (e.g. Reset button)
    if (old.value != widget.value && !_focus.hasFocus) {
      _ctrl.text = '${widget.value}';
    }
  }

  @override
  void dispose() {
    _ctrl.dispose();
    _focus.dispose();
    super.dispose();
  }

  void _applyText() {
    final v = int.tryParse(_ctrl.text.trim());
    if (v != null && v >= 0) {
      widget.onChanged(v);
    } else {
      _ctrl.text = '${widget.value}';
    }
  }

  @override
  Widget build(BuildContext context) {
    // Slider only goes 0 → sliderMax; text input accepts any ≥0 value
    final sliderVal = widget.value.clamp(0, widget.sliderMax).toDouble();
    final isDefault = widget.value == widget.sliderMax;

    return Container(
      padding: const EdgeInsets.fromLTRB(16, 14, 16, 12),
      decoration: BoxDecoration(
        color: AppColors.surfaceHigh,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AppColors.surfaceBorder),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // ── Header: icon + title + text input ─────────────────────────
          Row(
            children: [
              Icon(widget.icon, size: 20, color: AppColors.accent),
              const SizedBox(width: 10),
              Expanded(
                child: Text(widget.title,
                    style: const TextStyle(
                        fontSize: 15,
                        fontWeight: FontWeight.bold,
                        color: Colors.white)),
              ),
              const SizedBox(width: 8),
              // Direct entry field — accepts any value ≥ 0
              SizedBox(
                width: 80,
                height: 36,
                child: TextField(
                  controller: _ctrl,
                  focusNode: _focus,
                  keyboardType: TextInputType.number,
                  inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                  textAlign: TextAlign.center,
                  style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.bold,
                      color: AppColors.accent),
                  decoration: InputDecoration(
                    contentPadding:
                        const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
                    filled: true,
                    fillColor: AppColors.accent.withOpacity(0.12),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(8),
                      borderSide:
                          BorderSide(color: AppColors.accent.withOpacity(0.4)),
                    ),
                    enabledBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(8),
                      borderSide:
                          BorderSide(color: AppColors.accent.withOpacity(0.4)),
                    ),
                    focusedBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(8),
                      borderSide: BorderSide(color: AppColors.accent),
                    ),
                    suffix: Text(widget.unit,
                        style: const TextStyle(
                            fontSize: 11, color: AppColors.textMuted)),
                  ),
                  onSubmitted: (_) => _applyText(),
                ),
              ),
            ],
          ),

          const SizedBox(height: 6),

          // ── Description ───────────────────────────────────────────────
          Text(widget.subtitle,
              style: const TextStyle(
                  fontSize: 12, color: AppColors.textMuted)),

          const SizedBox(height: 4),

          // ── Slider: 0 → sliderMax (= default) ─────────────────────────
          SliderTheme(
            data: SliderTheme.of(context).copyWith(
              activeTrackColor: AppColors.accent,
              inactiveTrackColor: AppColors.surfaceBorder,
              thumbColor: AppColors.accent,
              overlayColor: AppColors.accent.withOpacity(0.15),
              trackHeight: 3,
            ),
            child: Slider(
              value: sliderVal,
              min: 0,
              max: widget.sliderMax.toDouble(),
              divisions: widget.sliderMax,
              onChanged: (v) {
                final rounded = v.round();
                widget.onChanged(rounded);
                if (!_focus.hasFocus) _ctrl.text = '$rounded';
              },
            ),
          ),

          // ── Range labels ──────────────────────────────────────────────
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 4),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text('0 ${widget.unit}',
                    style: const TextStyle(
                        fontSize: 11, color: AppColors.textMuted)),
                if (!isDefault)
                  GestureDetector(
                    onTap: () {
                      widget.onChanged(widget.sliderMax);
                      _ctrl.text = '${widget.sliderMax}';
                    },
                    child: Text(
                      'Default: ${widget.sliderMax} ${widget.unit}  ↑',
                      style: TextStyle(
                          fontSize: 11,
                          color: AppColors.accent.withOpacity(0.8),
                          decoration: TextDecoration.underline),
                    ),
                  )
                else
                  Text('Default: ${widget.sliderMax} ${widget.unit}',
                      style: const TextStyle(
                          fontSize: 11, color: AppColors.textMuted)),
                Text('${widget.sliderMax} ${widget.unit}',
                    style: const TextStyle(
                        fontSize: 11, color: AppColors.textMuted)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
