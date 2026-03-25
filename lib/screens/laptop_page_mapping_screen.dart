import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_provider.dart';
import '../theme/app_theme.dart';

// Sports in display order
const _kSports = [
  'AFL', 'Soccer', 'Cricket', 'Rugby', 'Hockey', 'Basketball',
];

const _kSportIcons = {
  'AFL'        : '🏉',
  'Soccer'     : '⚽',
  'Cricket'    : '🏏',
  'Rugby'      : '🏉',
  'Hockey'     : '🏒',
  'Basketball' : '🏀',
};

// Page options for sports: null + 0–6
const _kSportPages = [null, 0, 1, 2, 3, 4, 5, 6];

// Page options for ads: null + 0–10
const _kAdPages = [null, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10];

class LaptopPageMappingScreen extends StatefulWidget {
  const LaptopPageMappingScreen({super.key});

  @override
  State<LaptopPageMappingScreen> createState() =>
      _LaptopPageMappingScreenState();
}

class _LaptopPageMappingScreenState extends State<LaptopPageMappingScreen> {
  // Local copies — applied on Save
  late Map<String, int?> _sportPages;
  late Map<String, int?> _adPages;

  @override
  void initState() {
    super.initState();
    final app = context.read<AppProvider>();
    _sportPages = Map<String, int?>.from(app.config.laptopSportPages);
    _adPages    = Map<String, int?>.from(app.config.laptopAdPages);
  }

  bool get _hasChanges {
    final app = context.read<AppProvider>();
    for (final sport in _kSports) {
      if (_sportPages[sport] != app.config.laptopSportPages[sport]) return true;
    }
    for (int i = 1; i <= 5; i++) {
      final key = 'Ad$i';
      if (_adPages[key] != app.config.laptopAdPages[key]) return true;
    }
    return false;
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
          'Leave without saving page mapping changes?',
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
    for (final sport in _kSports) {
      app.setLaptopSportPage(sport, _sportPages[sport]);
    }
    for (int i = 1; i <= 5; i++) {
      final key = 'Ad$i';
      app.setLaptopAdPage(key, _adPages[key]);
    }
    Navigator.pop(context);
  }

  void _resetToDefaults() async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (d) => AlertDialog(
        backgroundColor: AppColors.surface,
        title: const Text('Reset Page Mapping'),
        content: const Text(
          'Reset all sport and ad page mappings to factory defaults?\n\n'
          'Sports → Page 0    •    Ad1 → 1, Ad2 → 2, etc.',
          style: TextStyle(color: AppColors.textSecondary, fontSize: 15),
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
    if (ok != true) return;
    setState(() {
      _sportPages = {for (final s in _kSports) s: 0};
      _adPages    = {'Ad1': 1, 'Ad2': 2, 'Ad3': 3, 'Ad4': 4, 'Ad5': 5};
    });
  }

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppProvider>();

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
          title: const Text('Page Mapping',
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
        body: SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [

              // ── ⚠ Warning ──────────────────────────────────────────────────
              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: AppColors.danger.withOpacity(0.10),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: AppColors.danger.withOpacity(0.5)),
                ),
                child: const Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(Icons.warning_amber_rounded,
                        size: 20, color: AppColors.danger),
                    SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        '⚠  Do not change these settings unless specifically '
                        'instructed to do so. Incorrect page mapping will '
                        'cause the wrong content to display on the scoreboard.',
                        style: TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w600,
                            color: AppColors.danger),
                      ),
                    ),
                  ],
                ),
              ),


              const SizedBox(height: 28),

              // ── SPORTS ─────────────────────────────────────────────────────
              _heading('SPORT PAGE MAPPING'),
              const SizedBox(height: 4),
              const Text(
                'When a sport is selected, the scoreboard switches to this page.',
                style: TextStyle(fontSize: 13, color: AppColors.textMuted),
              ),
              const SizedBox(height: 14),

              // Column header
              _pageColumnHeader(options: _kSportPages, labelWidth: 110),
              const SizedBox(height: 6),

              for (final sport in _kSports) ...[
                _PageMappingRow(
                  label: '${_kSportIcons[sport] ?? ''}  $sport',
                  labelWidth: 110,
                  options: _kSportPages,
                  selected: _sportPages[sport],
                  color: AppColors.accent,
                  onSelect: (v) =>
                      setState(() => _sportPages[sport] = v),
                ),
                const SizedBox(height: 6),
              ],

              const SizedBox(height: 28),

              // ── ADVERTISEMENTS ──────────────────────────────────────────────
              _heading('ADVERTISEMENT PAGE MAPPING'),
              const SizedBox(height: 4),
              const Text(
                'When an ad slot plays, the scoreboard switches to this page.',
                style: TextStyle(fontSize: 13, color: AppColors.textMuted),
              ),
              const SizedBox(height: 14),

              _pageColumnHeader(options: _kAdPages, labelWidth: 90),
              const SizedBox(height: 6),

              for (int i = 1; i <= 5; i++) ...[
                _PageMappingRow(
                  label: app.getLaptopAdName(i),
                  labelWidth: 90,
                  options: _kAdPages,
                  selected: _adPages['Ad$i'],
                  color: AppColors.warning,
                  onSelect: (v) =>
                      setState(() => _adPages['Ad$i'] = v),
                ),
                const SizedBox(height: 6),
              ],

              const SizedBox(height: 36),

              // ── Reset + Save row ───────────────────────────────────────────
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: _resetToDefaults,
                      icon: const Icon(Icons.restore, size: 18),
                      label: const Text('Reset Defaults',
                          style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold)),
                      style: OutlinedButton.styleFrom(
                        foregroundColor: AppColors.danger,
                        side: const BorderSide(color: AppColors.danger),
                        padding: const EdgeInsets.symmetric(vertical: 14),
                        shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(10)),
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: ElevatedButton.icon(
                      onPressed: _save,
                      icon: const Icon(Icons.save_outlined, size: 18),
                      label: const Text('Save',
                          style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold)),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppColors.success,
                        foregroundColor: Colors.white,
                        elevation: 0,
                        padding: const EdgeInsets.symmetric(vertical: 14),
                        shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(10)),
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 24),
            ],
          ),
        ),
      ),
    );
  }

  Widget _pageColumnHeader({
    required List<int?> options,
    required double labelWidth,
  }) {
    return Row(
      children: [
        SizedBox(width: labelWidth),
        ...options.map((v) => Expanded(
          child: Text(
            v == null ? '—' : '$v',
            textAlign: TextAlign.center,
            style: const TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.bold,
              color: AppColors.textMuted,
            ),
          ),
        )),
      ],
    );
  }
}

// ─── Single mapping row ───────────────────────────────────────────────────────

class _PageMappingRow extends StatelessWidget {
  final String label;
  final double labelWidth;
  final List<int?> options;
  final int? selected;
  final Color color;
  final ValueChanged<int?> onSelect;

  const _PageMappingRow({
    required this.label,
    required this.labelWidth,
    required this.options,
    required this.selected,
    required this.color,
    required this.onSelect,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        SizedBox(
          width: labelWidth,
          child: Text(
            label,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w500,
                color: Colors.white),
          ),
        ),
        ...options.map((v) {
          final sel = selected == v;
          // Null cell shows "—"
          final btnLabel = v == null ? '—' : '$v';
          return Expanded(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 2),
              child: GestureDetector(
                onTap: () => onSelect(v),
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 120),
                  padding: const EdgeInsets.symmetric(vertical: 9),
                  decoration: BoxDecoration(
                    color: sel ? color : AppColors.surfaceHigh,
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(
                      color: sel ? color : AppColors.surfaceBorder,
                    ),
                  ),
                  child: Text(
                    btnLabel,
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontSize: 12,
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

Widget _heading(String text) => Text(text,
    style: const TextStyle(
      fontSize: 12,
      fontWeight: FontWeight.w800,
      color: AppColors.textSecondary,
      letterSpacing: 1.0,
    ));
