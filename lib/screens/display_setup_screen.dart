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
  final _hCtrl = TextEditingController(text: '64');
  bool _singleColour = false;
  bool _ultraWide    = false;
  String? _error;

  @override
  void dispose() { _wCtrl.dispose(); _hCtrl.dispose(); super.dispose(); }

  void _apply() {
    final w = int.tryParse(_wCtrl.text) ?? 0;
    final h = int.tryParse(_hCtrl.text) ?? 0;
    if (w < 32 || w > 512 || h < 16 || h > 256) {
      setState(() => _error = 'Width: 32–512  •  Height: 16–256');
      return;
    }
    final app = context.read<AppProvider>();
    app.setDisplaySize(w, h);
    app.setSingleColour(_singleColour);
    app.setUltraWide(_ultraWide);
    Navigator.pushReplacementNamed(context, '/home');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(32),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: 40),
              const Text('Display Setup',
                style: TextStyle(fontSize: 30, fontWeight: FontWeight.bold, color: Colors.white)),
              const SizedBox(height: 8),
              const Text('Configure your LED display to continue.',
                style: TextStyle(color: AppColors.textSecondary, fontSize: 15)),
              const SizedBox(height: 40),

              // ── Dimensions ────────────────────────────────────────────────
              _DimField(label: 'Width (pixels)', ctrl: _wCtrl, hint: '128'),
              const SizedBox(height: 20),
              _DimField(label: 'Height (pixels)', ctrl: _hCtrl, hint: '64'),

              if (_error != null) ...[
                const SizedBox(height: 12),
                Text(_error!, style: const TextStyle(color: AppColors.dangerBright, fontSize: 13)),
              ],

              const SizedBox(height: 32),

              // ── Display Type ───────────────────────────────────────────────
              const Text('DISPLAY TYPE',
                style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold,
                    color: AppColors.textMuted, letterSpacing: 0.8)),
              const SizedBox(height: 10),
              Row(children: [
                _TypeChip(
                  label: 'Multi-Colour',
                  icon: Icons.palette,
                  selected: !_singleColour,
                  onTap: () => setState(() => _singleColour = false),
                ),
                const SizedBox(width: 10),
                _TypeChip(
                  label: 'Single Colour',
                  icon: Icons.circle,
                  selected: _singleColour,
                  onTap: () => setState(() => _singleColour = true),
                ),
              ]),
              if (_singleColour) ...[
                const SizedBox(height: 8),
                const Text(
                  'Single colour mode: only red text will be available in the ad editor.',
                  style: TextStyle(fontSize: 12, color: AppColors.textMuted),
                ),
              ],

              const SizedBox(height: 28),

              // ── Ultra Large Screen ────────────────────────────────────────
              const Text('ULTRA LARGE SCREEN',
                style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold,
                    color: AppColors.textMuted, letterSpacing: 0.8)),
              const SizedBox(height: 10),
              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: AppColors.surface,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                      color: _ultraWide
                          ? AppColors.warning.withOpacity(0.6)
                          : AppColors.surfaceBorder),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'Ultra Large Screen',
                                style: TextStyle(
                                  fontSize: 15,
                                  fontWeight: FontWeight.bold,
                                  color: _ultraWide ? AppColors.warning : Colors.white,
                                ),
                              ),
                              const SizedBox(height: 2),
                              const Text(
                                'Doubles characters per RAMT slot for very wide displays.',
                                style: TextStyle(fontSize: 12, color: AppColors.textMuted),
                              ),
                            ],
                          ),
                        ),
                        Switch(
                          value: _ultraWide,
                          onChanged: (v) => setState(() => _ultraWide = v),
                          activeColor: AppColors.warning,
                        ),
                      ],
                    ),
                    if (_ultraWide) ...[
                      const SizedBox(height: 10),
                      Container(
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: AppColors.warning.withOpacity(0.12),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: AppColors.warning.withOpacity(0.4)),
                        ),
                        child: const Row(
                          children: [
                            Icon(Icons.warning_amber_rounded,
                                size: 16, color: AppColors.warning),
                            SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                'Only select if been instructed to select.',
                                style: TextStyle(fontSize: 12, color: AppColors.warning),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ],
                ),
              ),

              const SizedBox(height: 40),
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
            ],
          ),
        ),
      ),
    );
  }
}

class _DimField extends StatelessWidget {
  final String label;
  final TextEditingController ctrl;
  final String hint;
  const _DimField({required this.label, required this.ctrl, required this.hint});
  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: const TextStyle(color: AppColors.textSecondary, fontSize: 14)),
        const SizedBox(height: 6),
        TextField(
          controller: ctrl,
          keyboardType: TextInputType.number,
          inputFormatters: [FilteringTextInputFormatter.digitsOnly],
          style: const TextStyle(fontSize: 24, color: Colors.white, fontWeight: FontWeight.bold),
          decoration: InputDecoration(
            hintText: hint,
            filled: true,
            fillColor: AppColors.surface,
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(10),
              borderSide: const BorderSide(color: AppColors.surfaceBorder),
            ),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(10),
              borderSide: const BorderSide(color: AppColors.surfaceBorder),
            ),
          ),
        ),
      ],
    );
  }
}

class _TypeChip extends StatelessWidget {
  final String label;
  final IconData icon;
  final bool selected;
  final VoidCallback onTap;
  const _TypeChip({required this.label, required this.icon, required this.selected, required this.onTap});
  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: GestureDetector(
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 14),
          decoration: BoxDecoration(
            color: selected ? AppColors.accent : AppColors.surfaceHigh,
            borderRadius: BorderRadius.circular(10),
            border: Border.all(
                color: selected ? AppColors.accent : AppColors.surfaceBorder),
          ),
          child: Column(
            children: [
              Icon(icon, size: 20, color: selected ? Colors.white : AppColors.textSecondary),
              const SizedBox(height: 4),
              Text(label,
                  style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.bold,
                      color: selected ? Colors.white : AppColors.textSecondary)),
            ],
          ),
        ),
      ),
    );
  }
}
