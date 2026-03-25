import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import '../providers/app_provider.dart';
import '../theme/app_theme.dart';

class DisplaySetupScreen extends StatefulWidget {
  const DisplaySetupScreen({super.key});
  @override
  State<DisplaySetupScreen> createState() => _DisplaySetupScreenState();
}

class _DisplaySetupScreenState extends State<DisplaySetupScreen> {
  final _wCtrl = TextEditingController(text: '128');
  final _hCtrl = TextEditingController(text: '80');
  bool _singleColour  = false;
  bool _ultraWide     = false;
  bool _laptopScoring = false;
  String? _error;

  @override
  void dispose() { _wCtrl.dispose(); _hCtrl.dispose(); super.dispose(); }

  void _apply() {
    final w = int.tryParse(_wCtrl.text.trim()) ?? 0;
    final h = int.tryParse(_hCtrl.text.trim()) ?? 0;
    if (w < 32 || w > 512 || h < 16 || h > 256) {
      setState(() => _error = 'Width: 32–512  •  Height: 16–256');
      return;
    }
    final app = context.read<AppProvider>();
    app.setDisplaySize(w, h);
    app.setSingleColour(_singleColour);
    app.setUltraWide(_ultraWide);
    app.setLaptopScoring(_laptopScoring);
    Navigator.pushReplacementNamed(context, '/home');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: 32),
              const Text('Display Setup',
                style: TextStyle(fontSize: 28, fontWeight: FontWeight.bold, color: Colors.white)),
              const SizedBox(height: 6),
              const Text('Configure your iCatcher scoreboard to continue.',
                style: TextStyle(color: AppColors.textSecondary, fontSize: 14)),
              const SizedBox(height: 32),

              // ── Scoring Mode ───────────────────────────────────────────────
              const Text('SCORING MODE',
                  style: TextStyle(fontSize: 14, fontWeight: FontWeight.w800,
                      color: AppColors.textSecondary, letterSpacing: 1.0)),
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                decoration: BoxDecoration(
                  color: AppColors.surfaceHigh,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(
                      color: _laptopScoring
                          ? AppColors.accent.withOpacity(0.5)
                          : AppColors.surfaceBorder),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            'Laptop Scoring Mode',
                            style: TextStyle(
                              fontSize: 15,
                              fontWeight: FontWeight.bold,
                              color: _laptopScoring ? AppColors.accent : Colors.white,
                            ),
                          ),
                        ),
                        Switch(
                          value: _laptopScoring,
                          onChanged: (v) => setState(() => _laptopScoring = v),
                          activeColor: AppColors.accent,
                          materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                        ),
                      ],
                    ),
                    const SizedBox(height: 4),
                    const Text(
                      'For Laptop controlled iCatcher scoreboards.',
                      style: TextStyle(fontSize: 13, color: AppColors.textMuted),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 24),

              // ── Pixel Size ─────────────────────────────────────────────────
              IgnorePointer(
                ignoring: _laptopScoring,
                child: AnimatedOpacity(
                  opacity: _laptopScoring ? 0.35 : 1.0,
                  duration: const Duration(milliseconds: 200),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('PIXEL SIZE OF SCREEN',
                          style: TextStyle(fontSize: 12, fontWeight: FontWeight.w800,
                              color: AppColors.textSecondary, letterSpacing: 1.0)),
                      const SizedBox(height: 8),
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const Text('Width',
                                    style: TextStyle(fontSize: 14,
                                        fontWeight: FontWeight.w600,
                                        color: AppColors.textSecondary)),
                                const SizedBox(height: 6),
                                TextField(
                                  controller: _wCtrl,
                                  keyboardType: TextInputType.number,
                                  inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                                  style: const TextStyle(color: Colors.white, fontSize: 18),
                                  decoration: const InputDecoration(
                                    hintText: '128',
                                    hintStyle: TextStyle(color: AppColors.textMuted),
                                    filled: true,
                                    fillColor: AppColors.surfaceHigh,
                                    contentPadding: EdgeInsets.symmetric(horizontal: 14, vertical: 14),
                                    border: OutlineInputBorder(borderSide: BorderSide(color: AppColors.surfaceBorder)),
                                    enabledBorder: OutlineInputBorder(borderSide: BorderSide(color: AppColors.surfaceBorder)),
                                    focusedBorder: OutlineInputBorder(borderSide: BorderSide(color: AppColors.accent, width: 2)),
                                  ),
                                ),
                              ],
                            ),
                          ),
                          const Padding(
                            padding: EdgeInsets.only(top: 30, left: 12, right: 12),
                            child: Text('×', style: TextStyle(fontSize: 22, color: AppColors.textMuted)),
                          ),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const Text('Height',
                                    style: TextStyle(fontSize: 14,
                                        fontWeight: FontWeight.w600,
                                        color: AppColors.textSecondary)),
                                const SizedBox(height: 6),
                                TextField(
                                  controller: _hCtrl,
                                  keyboardType: TextInputType.number,
                                  inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                                  style: const TextStyle(color: Colors.white, fontSize: 18),
                                  decoration: const InputDecoration(
                                    hintText: '80',
                                    hintStyle: TextStyle(color: AppColors.textMuted),
                                    filled: true,
                                    fillColor: AppColors.surfaceHigh,
                                    contentPadding: EdgeInsets.symmetric(horizontal: 14, vertical: 14),
                                    border: OutlineInputBorder(borderSide: BorderSide(color: AppColors.surfaceBorder)),
                                    enabledBorder: OutlineInputBorder(borderSide: BorderSide(color: AppColors.surfaceBorder)),
                                    focusedBorder: OutlineInputBorder(borderSide: BorderSide(color: AppColors.accent, width: 2)),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                      if (_error != null) ...[
                        const SizedBox(height: 8),
                        Text(_error!,
                            style: const TextStyle(color: AppColors.dangerBright, fontSize: 15)),
                      ],
                      const SizedBox(height: 24),

                      // ── Display Type ─────────────────────────────────────
                      const Text('DISPLAY TYPE',
                          style: TextStyle(fontSize: 12, fontWeight: FontWeight.w800,
                              color: AppColors.textSecondary, letterSpacing: 1.0)),
                      const SizedBox(height: 8),
                      Row(children: [
                        _TypeChip(
                          label: 'Multi-Colour',
                          selected: !_singleColour,
                          onTap: () => setState(() {
                            _singleColour = false;
                            _wCtrl.text = '128';
                            _hCtrl.text = '80';
                          }),
                        ),
                        const SizedBox(width: 8),
                        _TypeChip(
                          label: 'Single Colour',
                          selected: _singleColour,
                          onTap: () => setState(() {
                            _singleColour = true;
                            _wCtrl.text = '96';
                            _hCtrl.text = '128';
                          }),
                        ),
                      ]),
                      if (_singleColour) ...[
                        const SizedBox(height: 8),
                        const Text(
                          'Single colour mode: only red text will be available in the ad editor.',
                          style: TextStyle(fontSize: 14, color: AppColors.textMuted),
                        ),
                      ],
                      const SizedBox(height: 24),

                      // ── Ultra Large Screen ────────────────────────────────
                      const Text('ULTRA LARGE SCREEN',
                          style: TextStyle(fontSize: 12, fontWeight: FontWeight.w800,
                              color: AppColors.textSecondary, letterSpacing: 1.0)),
                      const SizedBox(height: 6),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                        decoration: BoxDecoration(
                          color: AppColors.surfaceHigh,
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(
                              color: _ultraWide
                                  ? AppColors.warning.withOpacity(0.5)
                                  : AppColors.surfaceBorder),
                        ),
                        child: Column(
                          children: [
                            Row(
                              children: [
                                Expanded(
                                  child: Text(
                                    'Ultra Large Screen',
                                    style: TextStyle(
                                      fontSize: 15,
                                      fontWeight: FontWeight.bold,
                                      color: _ultraWide ? AppColors.warning : Colors.white,
                                    ),
                                  ),
                                ),
                                Switch(
                                  value: _ultraWide,
                                  onChanged: (v) => setState(() => _ultraWide = v),
                                  activeColor: AppColors.warning,
                                  materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                                ),
                              ],
                            ),
                            if (_ultraWide) ...[
                              const SizedBox(height: 6),
                              Container(
                                padding: const EdgeInsets.all(8),
                                decoration: BoxDecoration(
                                  color: AppColors.warning.withOpacity(0.1),
                                  borderRadius: BorderRadius.circular(6),
                                ),
                                child: const Row(
                                  children: [
                                    Icon(Icons.warning_amber_rounded,
                                        size: 13, color: AppColors.warning),
                                    SizedBox(width: 6),
                                    Expanded(
                                      child: Text(
                                        'Only select if been instructed to select.',
                                        style: TextStyle(fontSize: 13, color: AppColors.warning),
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),

              const SizedBox(height: 36),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: _apply,
                  style: ElevatedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 18),
                    textStyle: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                  ),
                  child: const Text('Apply & Continue'),
                ),
              ),
              const SizedBox(height: 16),
            ],
          ),
        ),
      ),
    );
  }
}

class _TypeChip extends StatelessWidget {
  final String label;
  final bool selected;
  final VoidCallback onTap;
  const _TypeChip({required this.label, required this.selected, required this.onTap});
  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: GestureDetector(
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 12),
          decoration: BoxDecoration(
            color: selected ? AppColors.accent : AppColors.surfaceHigh,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(
                color: selected ? AppColors.accent : AppColors.surfaceBorder),
          ),
          child: Center(
            child: Text(label,
                style: TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.bold,
                    color: selected ? Colors.white : AppColors.textSecondary)),
          ),
        ),
      ),
    );
  }
}
