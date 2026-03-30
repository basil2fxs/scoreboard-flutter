import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import '../providers/app_provider.dart';
import '../theme/app_theme.dart';
import 'udp_timing_screen.dart';
import 'laptop_page_mapping_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  @override
  void initState() {
    super.initState();
    // On every home screen visit: check connection and send blank screen.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      final app = context.read<AppProvider>();
      app.testConnection();
    });
  }

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppProvider>();

    return Scaffold(
      body: SafeArea(
        child: Stack(
          children: [
            // ── Main column ───────────────────────────────────────────────
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  // ── Logo + iCatcher header — top-aligned ──────────────
                  const SizedBox(height: 10),
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
                          fontSize: 44,
                          fontWeight: FontWeight.w900,
                          color: Colors.white,
                          letterSpacing: -0.5,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'Scoreboard Control',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontSize: 32,
                      fontWeight: FontWeight.bold,
                      color: AppColors.textSecondary,
                      letterSpacing: -0.3,
                    ),
                  ),
                  const SizedBox(height: 6),
                  const Text(
                    'Professional LED Display Management',
                    textAlign: TextAlign.center,
                    style: TextStyle(fontSize: 17, color: AppColors.textMuted),
                  ),

                  // Small gap between subtitle and buttons
                  const SizedBox(height: 18),

                  // ── Buttons block ────────────────────────────────────────
                  Expanded(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.start,
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        // 1) Demo + ℹ + Connect block
                        _ConnectionBtn(
                          status    : app.connStatus,
                          onTap     : () => app.testConnection(),
                          onInfo    : () => _showInfoDialog(context),
                          onDemo    : () => _showDemoDialog(context, app),
                          onExitDemo: () => app.enableBypass(false),
                        ),

                        // Equal gap between all three buttons
                        const SizedBox(height: 12),

                        // 2) Select Sport
                        _HomeBtn(
                          label  : '🏆  Select Sport',
                          color  : AppColors.accentDark,
                          enabled: app.isConnected,
                          onTap  : () => Navigator.pushNamed(context, '/sportSelection'),
                        ),

                        const SizedBox(height: 12),

                        // 3) Manage Scores
                        _HomeBtn(
                          label  : _manageLabel(app.config.currentSport),
                          color  : AppColors.success,
                          enabled: app.isConnected && app.config.currentSport != null,
                          onTap  : () => _goToSport(context, app.config.currentSport),
                        ),

                        const Spacer(),
                      ],
                    ),
                  ),

                  const SizedBox(height: 16),

                  // ── Bottom area ─────────────────────────────────────────
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      // LEFT: New Ad button (hidden in laptop mode)
                      if (!app.laptopScoring)
                        SizedBox(
                          width: 72,
                          height: 72,
                          child: ElevatedButton(
                            onPressed: app.isConnected
                                ? () => Navigator.pushNamed(context, '/adEditor')
                                : null,
                            style: ElevatedButton.styleFrom(
                              backgroundColor: app.isConnected
                                  ? AppColors.accent
                                  : AppColors.surfaceHigh,
                              foregroundColor: Colors.white,
                              padding: EdgeInsets.zero,
                              shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(12)),
                              elevation: 0,
                            ),
                            child: const Column(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Icon(Icons.add, size: 26),
                                SizedBox(height: 4),
                                Text('New Ad',
                                    style: TextStyle(
                                        fontSize: 13,
                                        fontWeight: FontWeight.bold)),
                              ],
                            ),
                          ),
                        )
                      else
                        const SizedBox(width: 72, height: 72),

                      // RIGHT: Settings icon button
                      GestureDetector(
                        onTap: () => _showDisplaySettings(context, app),
                        child: SizedBox(
                          width: 72,
                          height: 72,
                          child: Container(
                            decoration: BoxDecoration(
                              color: AppColors.surfaceHigh,
                              borderRadius: BorderRadius.circular(12),
                              border: Border.all(color: AppColors.surfaceBorder),
                            ),
                            child: const Icon(Icons.settings,
                                size: 32, color: AppColors.textSecondary),
                          ),
                        ),
                      ),
                    ],
                  ),

                  const SizedBox(height: 16),
                  const Text(
                    'iCatcher Digital Signs  •  v1.0.4',
                    style: TextStyle(fontSize: 13, color: AppColors.textMuted),
                  ),
                  const SizedBox(height: 20),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ─── Helpers ──────────────────────────────────────────────────────────────

  String _manageLabel(String? sport) {
    if (sport == null) return '⚽  Manage Scores';
    const icons = {
      'AFL'              : '🦘',
      'Soccer': '⚽',
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
      'Soccer': '/soccer',
      'AFL'              : '/afl',
      'Cricket'          : '/cricket',
      'Rugby'            : '/simple',
      'Hockey'           : '/simple',
      'Basketball'       : '/simple',
    };
    Navigator.pushNamed(ctx, routes[sport] ?? '/simple');
  }

  void _showInfoDialog(BuildContext ctx) {
    showDialog<void>(
      context: ctx,
      builder: (d) => AlertDialog(
        backgroundColor: AppColors.surface,
        title: const Row(
          children: [
            Icon(Icons.wifi, color: AppColors.accent, size: 20),
            SizedBox(width: 8),
            Text('Connection Required'),
          ],
        ),
        content: const Text(
          'Requires you to connect to your iCatcher LED scoreboard\'s Wi-Fi network before using the app.',
          style: TextStyle(color: AppColors.textSecondary, fontSize: 18),
        ),
        actions: [
          ElevatedButton(
            onPressed: () => Navigator.pop(d),
            child: const Text('OK'),
          ),
        ],
      ),
    );
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
          style: TextStyle(color: AppColors.textSecondary, fontSize: 18),
        ),
        actionsAlignment: MainAxisAlignment.center,
        actions: [
          SizedBox(
            width: double.infinity,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                ElevatedButton(
                  onPressed: () {
                    app.enableBypass(true);
                    Navigator.pop(d);
                  },
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.warning,
                    foregroundColor: Colors.black,
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    textStyle: const TextStyle(
                        fontSize: 16, fontWeight: FontWeight.bold),
                  ),
                  child: const Text('Enable Demo Mode'),
                ),
                const SizedBox(height: 8),
                TextButton(
                  onPressed: () => Navigator.pop(d),
                  style: TextButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    foregroundColor: AppColors.textSecondary,
                  ),
                  child: const Text('Cancel',
                      style: TextStyle(
                          fontSize: 16, fontWeight: FontWeight.bold)),
                ),
              ],
            ),
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
    if (ok == true && ctx.mounted) {
      await app.resetToDefaults();
    }
  }

  void _showDisplaySettings(BuildContext ctx, AppProvider app) {
    Navigator.push(
      ctx,
      MaterialPageRoute(
        builder: (_) => _DisplaySettingsScreen(app: app),
      ),
    );
  }
}

// ─── Connection button ────────────────────────────────────────────────────────

class _ConnectionBtn extends StatelessWidget {
  final ConnectionStatus status;
  final VoidCallback onTap;
  final VoidCallback onInfo;
  final VoidCallback onDemo;
  final VoidCallback onExitDemo;
  const _ConnectionBtn({
    required this.status,
    required this.onTap,
    required this.onInfo,
    required this.onDemo,
    required this.onExitDemo,
  });

  @override
  Widget build(BuildContext context) {
    final bool inDemo = status == ConnectionStatus.bypass;

    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // ── Demo Mode (left) + ℹ (right) row ──────────────────────────
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            // Demo button — matches ℹ circle when off, orange pill when active
            GestureDetector(
              onTap: inDemo ? onExitDemo : onDemo,
              child: inDemo
                  // ── Exit Demo: bold orange pill ──────────────────────────
                  ? Container(
                      height: 52,
                      padding: const EdgeInsets.symmetric(horizontal: 22),
                      decoration: BoxDecoration(
                        color: AppColors.warning.withOpacity(0.15),
                        borderRadius: BorderRadius.circular(26),
                        border: Border.all(color: AppColors.warning, width: 2),
                      ),
                      child: const Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(Icons.stop_circle_outlined,
                              size: 22, color: AppColors.warning),
                          SizedBox(width: 10),
                          Text(
                            'Exit Demo',
                            style: TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.bold,
                              color: AppColors.warning,
                            ),
                          ),
                        ],
                      ),
                    )
                  // ── Demo Mode off: pill like ℹ but with "Demo" label ─────
                  : Container(
                      height: 52,
                      padding: const EdgeInsets.symmetric(horizontal: 16),
                      decoration: BoxDecoration(
                        color: AppColors.surfaceHigh,
                        borderRadius: BorderRadius.circular(26),
                        border: Border.all(
                            color: AppColors.surfaceBorder, width: 1.5),
                      ),
                      child: const Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(Icons.slideshow_outlined,
                              size: 22, color: AppColors.textSecondary),
                          SizedBox(width: 8),
                          Text(
                            'Demo Mode',
                            style: TextStyle(
                              fontSize: 15,
                              fontWeight: FontWeight.bold,
                              color: AppColors.textSecondary,
                            ),
                          ),
                        ],
                      ),
                    ),
            ),
            // ℹ button — right, large circle
            GestureDetector(
              onTap: onInfo,
              child: Container(
                width: 52,
                height: 52,
                decoration: BoxDecoration(
                  color: AppColors.surfaceHigh,
                  shape: BoxShape.circle,
                  border: Border.all(color: AppColors.surfaceBorder, width: 1.5),
                ),
                child: const Icon(Icons.info_outline,
                    size: 26, color: AppColors.textSecondary),
              ),
            ),
          ],
        ),
        const SizedBox(height: 20),

        // ── Connection area ────────────────────────────────────────────
        switch (status) {
          ConnectionStatus.disconnected => _HomeBtn(
            label  : '🔌  Connect to Scoreboard',
            color  : AppColors.success,
            enabled: true,
            onTap  : onTap,
          ),
          ConnectionStatus.connecting => _HomeBtn(
            label  : '◌  Testing connection...',
            color  : AppColors.surface,
            enabled: false,
            onTap  : onTap,
          ),
          ConnectionStatus.connected => _StatusBanner(
            dot        : '●',
            text       : 'Connected to Scoreboard',
            dotColor   : AppColors.successBright,
            textColor  : AppColors.successBright,
            bgColor    : const Color(0xFF0A3A0A),
            borderColor: AppColors.successBright,
          ),
          ConnectionStatus.bypass => _StatusBanner(
            dot        : '●',
            text       : 'Demo Mode  (No Connection)',
            dotColor   : AppColors.danger,
            textColor  : AppColors.danger,
            bgColor    : const Color(0xFF3A0A0A),
            borderColor: AppColors.danger,
          ),
        },
      ],
    );
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
    return SizedBox(
      width: double.infinity,
      height: 80,
      child: Container(
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
      ),
    );
  }
}

// ─── Demo banner ──────────────────────────────────────────────────────────────

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
      return _HomeBtn(
        label  : '⏏  Exit Demo',
        color  : AppColors.warning,
        enabled: true,
        onTap  : onDisable,
      );
    }
    return _HomeBtn(
      label  : '▶  Try Demo',
      color  : AppColors.surfaceHigh,
      enabled: true,
      onTap  : onEnable,
    );
  }
}

// ─── Shared home button ───────────────────────────────────────────────────────

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
      height: 80,
      child: AnimatedOpacity(
        opacity : enabled ? 1.0 : 0.4,
        duration: const Duration(milliseconds: 200),
        child: ElevatedButton(
          onPressed: enabled ? onTap : null,
          style: ElevatedButton.styleFrom(
            backgroundColor        : color,
            disabledBackgroundColor: AppColors.surface,
            minimumSize: const Size(double.infinity, 80),
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

// ─── Display Settings (full-screen) ──────────────────────────────────────────

class _DisplaySettingsScreen extends StatefulWidget {
  final AppProvider app;
  const _DisplaySettingsScreen({required this.app});

  @override
  State<_DisplaySettingsScreen> createState() => _DisplaySettingsScreenState();
}

class _DisplaySettingsScreenState extends State<_DisplaySettingsScreen> {
  late final TextEditingController _wCtrl;
  late final TextEditingController _hCtrl;
  late bool _singleColour;
  late bool _ultraWide;
  late bool _laptopScoring;
  // Remapping mode is saved immediately (not via the Save button)
  // so it's always accessible even in laptop mode.

  @override
  void initState() {
    super.initState();
    _wCtrl = TextEditingController(
        text: '${widget.app.config.displayWidth ?? 128}');
    _hCtrl = TextEditingController(
        text: '${widget.app.config.displayHeight ?? 64}');
    _singleColour  = widget.app.config.singleColour;
    _ultraWide     = widget.app.config.ultraWide;
    _laptopScoring = widget.app.config.laptopScoring;
  }

  @override
  void dispose() {
    _wCtrl.dispose();
    _hCtrl.dispose();
    super.dispose();
  }

  bool get _hasChanges {
    final origW = '${widget.app.config.displayWidth ?? 128}';
    final origH = '${widget.app.config.displayHeight ?? 64}';
    return _wCtrl.text.trim() != origW ||
        _hCtrl.text.trim() != origH ||
        _singleColour != widget.app.config.singleColour ||
        _ultraWide    != widget.app.config.ultraWide ||
        _laptopScoring!= widget.app.config.laptopScoring;
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
          'You have unsaved changes. Leave without saving?',
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
    final w = int.tryParse(_wCtrl.text.trim()) ??
        (widget.app.config.displayWidth ?? 128);
    final h = int.tryParse(_hCtrl.text.trim()) ??
        (widget.app.config.displayHeight ?? 64);
    if (w < 32 || w > 512 || h < 16 || h > 256) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
        content: Text('Width: 32–512  •  Height: 16–256'),
        backgroundColor: AppColors.danger,
      ));
      return;
    }
    widget.app.setDisplaySize(w, h);
    widget.app.setSingleColour(_singleColour);
    widget.app.setUltraWide(_ultraWide);
    widget.app.setLaptopScoring(_laptopScoring);
    Navigator.pop(context);
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
        title: const Text('Settings',
            style: TextStyle(fontWeight: FontWeight.bold)),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 12),
            child: ElevatedButton(
              onPressed: _save,
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.success,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
                textStyle: const TextStyle(fontWeight: FontWeight.bold),
                elevation: 0,
              ),
              child: const Text('Save'),
            ),
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [

            // ── Scoring Mode ───────────────────────────────────────────────
            _SectionHeading('SCORING MODE'),
            const SizedBox(height: 10),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
              decoration: BoxDecoration(
                color: AppColors.surfaceHigh,
                borderRadius: BorderRadius.circular(10),
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
                      ),
                    ],
                  ),
                  if (_laptopScoring) ...[
                    const SizedBox(height: 6),
                    const Text(
                      'For Laptop controlled iCatcher scoreboards.',
                      style: TextStyle(fontSize: 12, color: AppColors.textMuted),
                    ),
                  ],
                ],
              ),
            ),

            // ── Page Mapping button — only visible when Laptop mode is on ──
            if (_laptopScoring) ...[
              const SizedBox(height: 8),
              SizedBox(
                width: double.infinity,
                child: OutlinedButton.icon(
                  icon: const Icon(Icons.grid_view_outlined, size: 18),
                  label: const Text('Page Mapping'),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: AppColors.accent,
                    side: BorderSide(color: AppColors.accent.withOpacity(0.5)),
                    alignment: Alignment.centerLeft,
                    padding: const EdgeInsets.symmetric(
                        horizontal: 16, vertical: 14),
                  ),
                  onPressed: () => Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (_) => const LaptopPageMappingScreen(),
                    ),
                  ),
                ),
              ),
            ],

            const SizedBox(height: 32),

            // ── Hardware pixel dimensions (disabled in laptop mode) ─────────
            IgnorePointer(
              ignoring: _laptopScoring,
              child: AnimatedOpacity(
                opacity: _laptopScoring ? 0.35 : 1.0,
                duration: const Duration(milliseconds: 200),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [

                    _SectionHeading('PIXEL SIZE OF SCREEN'),
                    const SizedBox(height: 10),
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Text('Width',
                                  style: TextStyle(fontSize: 12,
                                      fontWeight: FontWeight.w600,
                                      color: AppColors.textSecondary)),
                              const SizedBox(height: 6),
                              TextField(
                                controller: _wCtrl,
                                keyboardType: TextInputType.number,
                                inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                                style: const TextStyle(color: Colors.white, fontSize: 18),
                                decoration: const InputDecoration(
                                  hintText : '128',
                                  hintStyle: TextStyle(color: AppColors.textMuted),
                                  filled    : true,
                                  fillColor : AppColors.surfaceHigh,
                                  contentPadding: EdgeInsets.symmetric(horizontal: 14, vertical: 14),
                                  border: OutlineInputBorder(borderSide: BorderSide(color: AppColors.surfaceBorder)),
                                  enabledBorder: OutlineInputBorder(borderSide: BorderSide(color: AppColors.surfaceBorder)),
                                  focusedBorder: OutlineInputBorder(borderSide: BorderSide(color: AppColors.accent, width: 2)),
                                ),
                                onChanged: (_) => setState(() {}),
                              ),
                            ],
                          ),
                        ),
                        const Padding(
                          padding: EdgeInsets.only(top: 30, left: 14, right: 14),
                          child: Text('×',
                              style: TextStyle(
                                  fontSize: 26, color: AppColors.textMuted)),
                        ),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Text('Height',
                                  style: TextStyle(fontSize: 12,
                                      fontWeight: FontWeight.w600,
                                      color: AppColors.textSecondary)),
                              const SizedBox(height: 6),
                              TextField(
                                controller: _hCtrl,
                                keyboardType: TextInputType.number,
                                inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                                style: const TextStyle(color: Colors.white, fontSize: 18),
                                decoration: const InputDecoration(
                                  hintText : '64',
                                  hintStyle: TextStyle(color: AppColors.textMuted),
                                  filled    : true,
                                  fillColor : AppColors.surfaceHigh,
                                  contentPadding: EdgeInsets.symmetric(horizontal: 14, vertical: 14),
                                  border: OutlineInputBorder(borderSide: BorderSide(color: AppColors.surfaceBorder)),
                                  enabledBorder: OutlineInputBorder(borderSide: BorderSide(color: AppColors.surfaceBorder)),
                                  focusedBorder: OutlineInputBorder(borderSide: BorderSide(color: AppColors.accent, width: 2)),
                                ),
                                onChanged: (_) => setState(() {}),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),

                    const SizedBox(height: 32),

                    // ── Display Type ──────────────────────────────────────
                    _SectionHeading('DISPLAY TYPE'),
                    const SizedBox(height: 10),
                    Row(children: [
                      _SettingsChip(
                        label: 'Multi-Colour',
                        selected: !_singleColour,
                        onTap: () => setState(() => _singleColour = false),
                      ),
                      const SizedBox(width: 10),
                      _SettingsChip(
                        label: 'Single Colour',
                        selected: _singleColour,
                        onTap: () => setState(() => _singleColour = true),
                      ),
                    ]),

                    const SizedBox(height: 32),

                    // ── Ultra Large Screen ────────────────────────────────
                    _SectionHeading('ULTRA LARGE SCREEN'),
                    const SizedBox(height: 10),
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 14, vertical: 12),
                      decoration: BoxDecoration(
                        color: AppColors.surfaceHigh,
                        borderRadius: BorderRadius.circular(10),
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
                                    color: _ultraWide
                                        ? AppColors.warning
                                        : Colors.white,
                                  ),
                                ),
                              ),
                              Switch(
                                value: _ultraWide,
                                onChanged: (v) =>
                                    setState(() => _ultraWide = v),
                                activeColor: AppColors.warning,
                              ),
                            ],
                          ),
                          if (_ultraWide) ...[
                            const SizedBox(height: 8),
                            Container(
                              padding: const EdgeInsets.all(10),
                              decoration: BoxDecoration(
                                color: AppColors.warning.withOpacity(0.1),
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: const Row(
                                children: [
                                  Icon(Icons.warning_amber_rounded,
                                      size: 15, color: AppColors.warning),
                                  SizedBox(width: 8),
                                  Expanded(
                                    child: Text(
                                      'Only select if been instructed to select.',
                                      style: TextStyle(
                                          fontSize: 12,
                                          color: AppColors.warning),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ],
                      ),
                    ),

                    const SizedBox(height: 8),
                  ],
                ),
              ),
            ),

            const SizedBox(height: 24),

            // ── Remapping Mode — always accessible ────────────────────────
            _SectionHeading('ADVANCED'),
            const SizedBox(height: 10),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
              decoration: BoxDecoration(
                color: AppColors.surfaceHigh,
                borderRadius: BorderRadius.circular(10),
                border: Border.all(
                  color: widget.app.remappingMode
                      ? AppColors.accent.withOpacity(0.6)
                      : AppColors.surfaceBorder,
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      const Icon(Icons.cable_outlined,
                          size: 20, color: AppColors.textSecondary),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text('Remapping Mode',
                            style: TextStyle(
                              fontSize: 15,
                              fontWeight: FontWeight.bold,
                              color: widget.app.remappingMode
                                  ? AppColors.accent
                                  : Colors.white,
                            )),
                      ),
                      Switch(
                        value: widget.app.remappingMode,
                        onChanged: (v) {
                          setState(() {});
                          widget.app.setRemappingMode(v);
                        },
                        activeColor: AppColors.accent,
                        materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                      ),
                    ],
                  ),
                  if (widget.app.remappingMode) ...[
                    const SizedBox(height: 6),
                    const Text(
                      'Adds a "Remapping" button to each sport screen to '
                      'customise counter channels, timer channels, and offsets.',
                      style: TextStyle(fontSize: 13, color: AppColors.textMuted),
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(height: 12),

            // ── UDP Timing ───────────────────────────────────────────────────
            SizedBox(
              width: double.infinity,
              child: OutlinedButton.icon(
                icon: const Icon(Icons.tune_outlined, size: 18),
                label: const Text('UDP Timing'),
                style: OutlinedButton.styleFrom(
                  foregroundColor: AppColors.textSecondary,
                  side: const BorderSide(color: AppColors.surfaceBorder),
                  alignment: Alignment.centerLeft,
                  padding: const EdgeInsets.symmetric(
                      horizontal: 16, vertical: 14),
                ),
                onPressed: () => Navigator.push(
                  context,
                  MaterialPageRoute(
                      builder: (_) => const UdpTimingScreen()),
                ),
              ),
            ),

            const SizedBox(height: 20),

            // ── Reset Settings — always accessible (outside IgnorePointer) ──
            SizedBox(
              width: double.infinity,
              child: OutlinedButton.icon(
                onPressed: () async {
                  final ok = await showDialog<bool>(
                    context: context,
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
                          style: ElevatedButton.styleFrom(
                              backgroundColor: AppColors.danger),
                          child: const Text('Reset'),
                        ),
                      ],
                    ),
                  );
                  if (ok == true && mounted) {
                    await widget.app.resetToDefaults();
                    if (mounted) {
                      Navigator.pushNamedAndRemoveUntil(
                          context, '/setup', (r) => false);
                    }
                  }
                },
                icon: const Icon(Icons.restore, size: 20),
                label: const Text('Reset All Settings',
                    style: TextStyle(
                        fontSize: 15, fontWeight: FontWeight.bold)),
                style: OutlinedButton.styleFrom(
                  foregroundColor: AppColors.danger,
                  side: const BorderSide(
                      color: AppColors.danger, width: 1.5),
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(10)),
                ),
              ),
            ),

            const SizedBox(height: 24),
          ],
        ),
      ),
    )); // closes PopScope + Scaffold
  }
}

// ─── Section heading ─────────────────────────────────────────────────────────

class _SectionHeading extends StatelessWidget {
  final String text;
  const _SectionHeading(this.text);
  @override
  Widget build(BuildContext context) => Text(
        text,
        style: const TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.w800,
          color: AppColors.textSecondary,
          letterSpacing: 1.1,
        ),
      );
}

// ─── Settings chip ────────────────────────────────────────────────────────────

class _SettingsChip extends StatelessWidget {
  final String label;
  final bool selected;
  final VoidCallback onTap;
  const _SettingsChip(
      {required this.label, required this.selected, required this.onTap});
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
          child: Center(
            child: Text(label,
                style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.bold,
                    color:
                        selected ? Colors.white : AppColors.textSecondary)),
          ),
        ),
      ),
    );
  }
}
