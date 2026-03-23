import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import '../providers/app_provider.dart';
import '../theme/app_theme.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppProvider>();

    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              const SizedBox(height: 28),

              // ── Logo + iCatcher header ──────────────────────────────────────
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  ClipRRect(
                    borderRadius: BorderRadius.circular(12),
                    child: Image.asset(
                      'assets/images/icatcher_logo.png',
                      width: 56,
                      height: 52,
                      fit: BoxFit.cover,
                    ),
                  ),
                  const SizedBox(width: 12),
                  const Text(
                    'iCatcher',
                    style: TextStyle(
                      fontSize: 40,
                      fontWeight: FontWeight.w900,
                      color: Colors.white,
                      letterSpacing: -0.5,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 4),
              const Text(
                'Scoreboard Control',
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 22,
                  fontWeight: FontWeight.bold,
                  color: AppColors.textSecondary,
                  letterSpacing: -0.3,
                ),
              ),
              const SizedBox(height: 4),
              const Text(
                'Professional LED Display Management',
                style: TextStyle(fontSize: 15, color: AppColors.textMuted),
              ),
              const SizedBox(height: 24),

              // ── Connection button ─────────────────────────────────────────
              _ConnectionBtn(
                status: app.connStatus,
                onTap  : () => app.testConnection(),
              ),
              const SizedBox(height: 10),

              // ── Demo / Tester mode banner ─────────────────────────────────
              _DemoBanner(
                active   : app.bypassMode,
                onEnable : () => _showDemoDialog(context, app),
                onDisable: () => app.enableBypass(false),
              ),
              const SizedBox(height: 10),

              // ── Select Sport ──────────────────────────────────────────────
              _HomeBtn(
                label  : '🏆  Select Sport',
                color  : AppColors.accentDark,
                enabled: app.isConnected,
                onTap  : () => Navigator.pushNamed(context, '/sportSelection'),
              ),
              const SizedBox(height: 14),

              // ── Manage Scores ─────────────────────────────────────────────
              _HomeBtn(
                label  : _manageLabel(app.config.currentSport),
                color  : AppColors.success,
                enabled: app.isConnected && app.config.currentSport != null,
                onTap  : () => _goToSport(context, app.config.currentSport),
              ),

              const Spacer(),

              // ── Bottom area ───────────────────────────────────────────────
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [

                  // ── LEFT: New Ad button (hidden in laptop mode) ───────────
                  if (!app.laptopScoring)
                    ElevatedButton.icon(
                      onPressed: app.isConnected
                          ? () => Navigator.pushNamed(context, '/adEditor')
                          : null,
                      icon : const Icon(Icons.add, size: 16),
                      label: const Text('New Ad'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: app.isConnected
                            ? AppColors.accent
                            : AppColors.surfaceHigh,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(
                            horizontal: 14, vertical: 10),
                        textStyle: const TextStyle(
                            fontSize: 13, fontWeight: FontWeight.bold),
                        elevation: 0,
                      ),
                    )
                  else
                    const SizedBox.shrink(),

                  // ── RIGHT: Settings icon button ───────────────────────────
                  GestureDetector(
                    onTap: () => _showScreenSizeDialog(context, app),
                    child: Container(
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: AppColors.surfaceHigh,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: AppColors.surfaceBorder),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Icon(Icons.settings,
                              size: 20, color: AppColors.textSecondary),
                          if (app.laptopScoring) ...[
                            const SizedBox(width: 6),
                            Container(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 5, vertical: 2),
                              decoration: BoxDecoration(
                                color: AppColors.accent.withOpacity(0.2),
                                borderRadius: BorderRadius.circular(4),
                              ),
                              child: const Text('LAPTOP',
                                  style: TextStyle(
                                      fontSize: 9,
                                      fontWeight: FontWeight.bold,
                                      color: AppColors.accent)),
                            ),
                          ],
                        ],
                      ),
                    ),
                  ),
                ],
              ),

              const SizedBox(height: 4),
              const Text(
                'iCatcher Digital Signs  •  v1.0',
                style: TextStyle(fontSize: 10, color: AppColors.textMuted),
              ),
              const SizedBox(height: 12),
            ],
          ),
        ),
      ),
    );
  }

  // ─── Helpers ──────────────────────────────────────────────────────────────

  String _manageLabel(String? sport) {
    if (sport == null) return '⚽  Manage Scores';
    const icons = {
      'AFL'              : '🦘',
      'Soccer/ Universal': '⚽',
      'Cricket'          : '🏏',
      'Rugby'            : '🏉',
      'Hockey'           : '🏒',
      'Basketball'       : '🏀',
    };
    return '${icons[sport] ?? '🏅'}  Manage $sport Scores';
  }

  void _goToSport(BuildContext ctx, String? sport) {
    if (sport == null) return;
    ctx.read<AppProvider>().sendSportProgram();
    const routes = {
      'Soccer/ Universal': '/soccer',
      'AFL'              : '/afl',
      'Cricket'          : '/cricket',
      'Rugby'            : '/simple',
      'Hockey'           : '/simple',
      'Basketball'       : '/simple',
    };
    Navigator.pushNamed(ctx, routes[sport] ?? '/simple');
  }

  void _showDemoDialog(BuildContext ctx, AppProvider app) {
    showDialog<void>(
      context: ctx,
      builder: (d) => AlertDialog(
        backgroundColor: AppColors.surface,
        title: const Row(
          children: [
            Icon(Icons.info_outline, color: AppColors.warning, size: 20),
            SizedBox(width: 8),
            Text('Demo Mode'),
          ],
        ),
        content: const Text(
          'Demo Mode lets you explore all features — scores, timers, and '
          'advertisements — without a physical iCatcher scoreboard.\n\n'
          'To use the full app, connect an iCatcher scoreboard to the same '
          'Wi-Fi network as your device.',
          style: TextStyle(color: AppColors.textSecondary, fontSize: 14),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(d),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () {
              app.enableBypass(true);
              Navigator.pop(d);
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.warning,
              foregroundColor: Colors.black,
            ),
            child: const Text('Enable Demo Mode'),
          ),
        ],
      ),
    );
  }

  Future<void> _confirmReset(BuildContext ctx, AppProvider app) async {
    final ok = await showDialog<bool>(
      context: ctx,
      builder: (d) => AlertDialog(
        backgroundColor: AppColors.surface,
        title: const Text('Reset All Settings'),
        content: const Text(
          'This will erase ALL saved settings:\n\n'
          '• Sport selection\n'
          '• Team names and scores\n'
          '• Timer and display settings\n'
          '• Advertisements\n\n'
          'Are you sure?'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(d, false),
              child: const Text('Cancel')),
          ElevatedButton(
            onPressed: () => Navigator.pop(d, true),
            style: ElevatedButton.styleFrom(backgroundColor: AppColors.danger),
            child: const Text('Reset'),
          ),
        ],
      ),
    );
    if (ok == true) {
      await app.resetToDefaults();
    }
  }

  void _showScreenSizeDialog(BuildContext ctx, AppProvider app) {
    showDialog(
      context: ctx,
      builder: (d) => _ScreenSizeDialog(
        currentWidth        : app.config.displayWidth    ?? 128,
        currentHeight       : app.config.displayHeight   ?? 64,
        currentSingleColour : app.config.singleColour,
        currentUltraWide    : app.config.ultraWide,
        currentLaptopScoring: app.config.laptopScoring,
        onSave: (w, h, sc, uw, ls) {
          app.setDisplaySize(w, h);
          app.setSingleColour(sc);
          app.setUltraWide(uw);
          app.setLaptopScoring(ls);
          Navigator.pop(d);
        },
        onReset: () async {
          await _confirmReset(ctx, app);
          if (ctx.mounted) Navigator.pop(d);
        },
      ),
    );
  }
}

// ─── Connection button ────────────────────────────────────────────────────────

class _ConnectionBtn extends StatelessWidget {
  final ConnectionStatus status;
  final VoidCallback onTap;
  const _ConnectionBtn({required this.status, required this.onTap});

  @override
  Widget build(BuildContext context) {
    switch (status) {
      case ConnectionStatus.disconnected:
        return _HomeBtn(
          label  : '🔌  Connect to Controller',
          color  : AppColors.success,
          enabled: true,
          onTap  : onTap,
        );
      case ConnectionStatus.connecting:
        return _HomeBtn(
          label  : '◌  Testing connection...',
          color  : AppColors.surface,
          enabled: false,
          onTap  : onTap,
        );
      case ConnectionStatus.connected:
        return _StatusBanner(
          dot        : '●',
          text       : 'Connected to Scoreboard',
          dotColor   : AppColors.successBright,
          textColor  : AppColors.successBright,
          bgColor    : const Color(0xFF0A3A0A),
          borderColor: AppColors.successBright,
        );
      case ConnectionStatus.bypass:
        return _StatusBanner(
          dot        : '●',
          text       : 'Bypass Mode (No Connection)',
          dotColor   : AppColors.warning,
          textColor  : AppColors.warning,
          bgColor    : const Color(0xFF3A2A00),
          borderColor: AppColors.warning,
        );
    }
  }
}

class _StatusBanner extends StatelessWidget {
  final String dot, text;
  final Color dotColor, textColor, bgColor, borderColor;
  const _StatusBanner({
    required this.dot, required this.text,
    required this.dotColor, required this.textColor,
    required this.bgColor, required this.borderColor,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(vertical: 18, horizontal: 20),
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: borderColor.withOpacity(0.4)),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text('$dot  ', style: TextStyle(
              color: dotColor, fontSize: 16, fontWeight: FontWeight.bold)),
          Flexible(
            child: Text(text, overflow: TextOverflow.ellipsis,
              style: TextStyle(color: textColor, fontSize: 16,
                  fontWeight: FontWeight.bold)),
          ),
        ],
      ),
    );
  }
}

// ─── Screen size / settings dialog ───────────────────────────────────────────

class _ScreenSizeDialog extends StatefulWidget {
  final int currentWidth, currentHeight;
  final bool currentSingleColour, currentUltraWide, currentLaptopScoring;
  final void Function(int w, int h, bool singleColour, bool ultraWide, bool laptopScoring) onSave;
  final Future<void> Function() onReset;
  const _ScreenSizeDialog({
    required this.currentWidth,
    required this.currentHeight,
    required this.currentSingleColour,
    required this.currentUltraWide,
    required this.currentLaptopScoring,
    required this.onSave,
    required this.onReset,
  });

  @override
  State<_ScreenSizeDialog> createState() => _ScreenSizeDlgState();
}

class _ScreenSizeDlgState extends State<_ScreenSizeDialog> {
  late final TextEditingController _wCtrl;
  late final TextEditingController _hCtrl;
  late bool _singleColour;
  late bool _ultraWide;
  late bool _laptopScoring;

  @override
  void initState() {
    super.initState();
    _wCtrl = TextEditingController(text: '${widget.currentWidth}');
    _hCtrl = TextEditingController(text: '${widget.currentHeight}');
    _singleColour  = widget.currentSingleColour;
    _ultraWide     = widget.currentUltraWide;
    _laptopScoring = widget.currentLaptopScoring;
  }

  @override
  void dispose() {
    _wCtrl.dispose();
    _hCtrl.dispose();
    super.dispose();
  }

  void _save() {
    final w = int.tryParse(_wCtrl.text.trim()) ?? widget.currentWidth;
    final h = int.tryParse(_hCtrl.text.trim()) ?? widget.currentHeight;
    if (w < 32 || w > 512 || h < 16 || h > 256) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
        content: Text('Width: 32–512  •  Height: 16–256'),
        backgroundColor: AppColors.danger,
      ));
      return;
    }
    widget.onSave(w, h, _singleColour, _ultraWide, _laptopScoring);
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      backgroundColor: AppColors.surface,
      title: const Text('Display Settings'),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [

            // ── Scoring Mode (TOP — shown first) ───────────────────────
            const Text('SCORING MODE',
                style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold,
                    color: AppColors.textMuted, letterSpacing: 0.8)),
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
                            fontSize: 13,
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
                  Text(
                    _laptopScoring
                        ? 'For Laptop controlled iCatcher scoreboards.'
                        : 'Standard mode: full display control with RAMT commands.',
                    style: const TextStyle(fontSize: 11, color: AppColors.textMuted),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 18),

            // ── The following settings are disabled in Laptop Scoring mode ──
            IgnorePointer(
              ignoring: _laptopScoring,
              child: AnimatedOpacity(
                opacity: _laptopScoring ? 0.35 : 1.0,
                duration: const Duration(milliseconds: 200),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [

                    // ── Dimensions ───────────────────────────────────────
                    const Text('PIXELS',
                        style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold,
                            color: AppColors.textMuted, letterSpacing: 0.8)),
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        Expanded(
                          child: TextField(
                            controller: _wCtrl,
                            keyboardType: TextInputType.number,
                            inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                            style: const TextStyle(color: Colors.white),
                            decoration: const InputDecoration(
                              labelText : 'Width',
                              filled    : true,
                              fillColor : AppColors.surfaceHigh,
                            ),
                            onChanged: (_) => setState(() {}),
                          ),
                        ),
                        const Padding(
                          padding: EdgeInsets.symmetric(horizontal: 12),
                          child: Text('×', style: TextStyle(fontSize: 22, color: AppColors.textMuted)),
                        ),
                        Expanded(
                          child: TextField(
                            controller: _hCtrl,
                            keyboardType: TextInputType.number,
                            inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                            style: const TextStyle(color: Colors.white),
                            decoration: const InputDecoration(
                              labelText : 'Height',
                              filled    : true,
                              fillColor : AppColors.surfaceHigh,
                            ),
                            onChanged: (_) => setState(() {}),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 18),

                    // ── Display Type ────────────────────────────────────
                    const Text('DISPLAY TYPE',
                        style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold,
                            color: AppColors.textMuted, letterSpacing: 0.8)),
                    const SizedBox(height: 8),
                    Row(children: [
                      _DlgChip(
                        label: 'Multi-Colour',
                        selected: !_singleColour,
                        onTap: () => setState(() => _singleColour = false),
                      ),
                      const SizedBox(width: 8),
                      _DlgChip(
                        label: 'Single Colour',
                        selected: _singleColour,
                        onTap: () => setState(() => _singleColour = true),
                      ),
                    ]),
                    const SizedBox(height: 16),

                    // ── Ultra Large Screen ──────────────────────────────
                    const Text('ULTRA LARGE SCREEN',
                        style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold,
                            color: AppColors.textMuted, letterSpacing: 0.8)),
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
                                    fontSize: 13,
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
                                      style: TextStyle(fontSize: 11, color: AppColors.warning),
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
          ],
        ),
      ),
      actionsAlignment: MainAxisAlignment.spaceBetween,
      actions: [
        // Reset Settings — always accessible, red, on the left
        TextButton(
          onPressed: widget.onReset,
          style: TextButton.styleFrom(foregroundColor: AppColors.danger),
          child: const Text('Reset Settings'),
        ),
        Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Cancel'),
            ),
            const SizedBox(width: 8),
            ElevatedButton(
              onPressed: _save,
              style: ElevatedButton.styleFrom(backgroundColor: AppColors.success),
              child: const Text('Save'),
            ),
          ],
        ),
      ],
    );
  }
}

class _DlgChip extends StatelessWidget {
  final String label;
  final bool selected;
  final VoidCallback onTap;
  const _DlgChip({required this.label, required this.selected, required this.onTap});
  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: GestureDetector(
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 9),
          decoration: BoxDecoration(
            color: selected ? AppColors.accent : AppColors.surfaceHigh,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(
                color: selected ? AppColors.accent : AppColors.surfaceBorder),
          ),
          child: Center(
            child: Text(label,
                style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.bold,
                    color: selected ? Colors.white : AppColors.textSecondary)),
          ),
        ),
      ),
    );
  }
}

// ─── Shared home button ────────────────────────────────────────────────────────

class _HomeBtn extends StatelessWidget {
  final String label;
  final Color color;
  final bool enabled;
  final VoidCallback onTap;
  const _HomeBtn({
    required this.label, required this.color,
    required this.enabled, required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: double.infinity,
      child: AnimatedOpacity(
        opacity : enabled ? 1.0 : 0.4,
        duration: const Duration(milliseconds: 200),
        child: ElevatedButton(
          onPressed: enabled ? onTap : null,
          style: ElevatedButton.styleFrom(
            backgroundColor        : color,
            disabledBackgroundColor: AppColors.surface,
            padding: const EdgeInsets.symmetric(vertical: 22),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            textStyle: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
            elevation: 0,
          ),
          child: Text(label, style: const TextStyle(color: Colors.white)),
        ),
      ),
    );
  }
}

// ─── Demo / Tester mode banner ────────────────────────────────────────────────

class _DemoBanner extends StatelessWidget {
  final bool active;
  final VoidCallback onEnable;
  final VoidCallback onDisable;
  const _DemoBanner({
    required this.active, required this.onEnable, required this.onDisable,
  });

  @override
  Widget build(BuildContext context) {
    if (active) {
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(
          color: AppColors.warning.withOpacity(0.15),
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: AppColors.warning.withOpacity(0.5)),
        ),
        child: Row(
          children: [
            const Icon(Icons.science, size: 15, color: AppColors.warning),
            const SizedBox(width: 8),
            const Expanded(
              child: Text('DEMO MODE — commands are simulated',
                style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold,
                    color: AppColors.warning)),
            ),
            GestureDetector(
              onTap: onDisable,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: AppColors.warning.withOpacity(0.2),
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: AppColors.warning.withOpacity(0.5)),
                ),
                child: const Text('Exit',
                    style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold,
                        color: AppColors.warning)),
              ),
            ),
          ],
        ),
      );
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AppColors.surfaceBorder),
      ),
      child: Row(
        children: [
          const Icon(Icons.info_outline, size: 15, color: AppColors.textMuted),
          const SizedBox(width: 8),
          const Expanded(
            child: Text('Requires an iCatcher LED scoreboard on your Wi-Fi',
                style: TextStyle(fontSize: 12, color: AppColors.textMuted)),
          ),
          GestureDetector(
            onTap: onEnable,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
              decoration: BoxDecoration(
                color: AppColors.surfaceHigh,
                borderRadius: BorderRadius.circular(6),
                border: Border.all(color: AppColors.surfaceBorder),
              ),
              child: const Text('Try Demo',
                  style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold,
                      color: AppColors.textSecondary)),
            ),
          ),
        ],
      ),
    );
  }
}
