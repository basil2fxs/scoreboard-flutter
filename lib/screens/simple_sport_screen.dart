import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_provider.dart';
import '../theme/app_theme.dart';
import '../widgets/team_names_card.dart';
import '../widgets/timer_widget.dart';
import '../widgets/shot_clock_widget.dart';
import '../widgets/score_card.dart';
import '../widgets/section_card.dart';
import '../widgets/ads_panel.dart';
import '../widgets/settings_dialogs.dart';

/// Used for Rugby, Hockey, and Basketball.
class SimpleSportScreen extends StatefulWidget {
  const SimpleSportScreen({super.key});
  @override
  State<SimpleSportScreen> createState() => _SimpleSportScreenState();
}

class _SimpleSportScreenState extends State<SimpleSportScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final app = context.read<AppProvider>();
      app.initTimerForSport(app.config.currentSport ?? '');
      app.sendSportProgram();
      Future.delayed(const Duration(milliseconds: 50), app.resendAll);
    });
  }

  @override
  Widget build(BuildContext context) {
    final app          = context.watch<AppProvider>();
    final sport        = app.config.currentSport ?? 'Rugby';
    final isHockey     = sport == 'Hockey';
    final isBasketball = sport == 'Basketball';
    final hasShotClock = isHockey || isBasketball;
    final isLaptop     = app.laptopScoring;

    return Scaffold(
      appBar: AppBar(
        title: Text('$sport Match'),
        leading: BackButton(onPressed: () {
          app.backToHome();
          Navigator.pushReplacementNamed(context, '/home');
        }),
      ),
      body: ListView(
        padding: const EdgeInsets.only(bottom: 24),
        children: [
          if (!isLaptop) TeamNamesCard(sport: sport),
          const TimerWidget(),

          // ── Scores ───────────────────────────────────────────────────────
          SectionCard(
            title: 'SCORES',
            trailing: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                SettingsIconButton(
                  onTap: () => showCounterSettingsDialog(context, sport)),
                const SizedBox(width: 4),
                IconButton(
                  icon: const Icon(Icons.refresh, size: 18, color: AppColors.danger),
                  onPressed: () => app.resetScores(),
                  padding: EdgeInsets.zero,
                  constraints: const BoxConstraints(minWidth: 28, minHeight: 28),
                ),
              ],
            ),
            child: Column(
              children: [
                if (isBasketball) ...[
                  // Basketball: +1 / +2 / +3 buttons
                  _BasketballScoreRow(
                    label: app.config.homeName.substring(0, app.config.homeName.length.clamp(0, 8)),
                    value: app.config.homeScore,
                    labelColor: AppColors.homeTeam,
                    onDecrement: () => app.adjustScore('home', -1),
                    onAdd1: () => app.adjustScore('home', 1),
                    onAdd2: () => app.adjustScore('home', 2),
                    onAdd3: () => app.adjustScore('home', 3),
                    onManualEdit: (v) => app.setScore('home', v),
                  ),
                  const SizedBox(height: 12),
                  _BasketballScoreRow(
                    label: app.config.awayName.substring(0, app.config.awayName.length.clamp(0, 8)),
                    value: app.config.awayScore,
                    labelColor: AppColors.awayTeam,
                    onDecrement: () => app.adjustScore('away', -1),
                    onAdd1: () => app.adjustScore('away', 1),
                    onAdd2: () => app.adjustScore('away', 2),
                    onAdd3: () => app.adjustScore('away', 3),
                    onManualEdit: (v) => app.setScore('away', v),
                  ),
                ] else ...[
                  ScoreRow(
                    label: app.config.homeName.substring(0, app.config.homeName.length.clamp(0, 8)),
                    value: app.config.homeScore,
                    labelColor: AppColors.homeTeam,
                    onDecrement: () => app.adjustScore('home', -1),
                    onIncrement: () => app.adjustScore('home', 1),
                    onManualEdit: (v) => app.setScore('home', v),
                  ),
                  const SizedBox(height: 12),
                  ScoreRow(
                    label: app.config.awayName.substring(0, app.config.awayName.length.clamp(0, 8)),
                    value: app.config.awayScore,
                    labelColor: AppColors.awayTeam,
                    onDecrement: () => app.adjustScore('away', -1),
                    onIncrement: () => app.adjustScore('away', 1),
                    onManualEdit: (v) => app.setScore('away', v),
                  ),
                ],
              ],
            ),
          ),

          // ── Basketball extras ─────────────────────────────────────────────
          if (isBasketball) ...[
            SectionCard(
              title: 'TIMEOUTS',
              trailing: IconButton(
                icon: const Icon(Icons.refresh, size: 18, color: AppColors.danger),
                onPressed: () => app.resetTimeouts(),
                padding: EdgeInsets.zero,
                constraints: const BoxConstraints(minWidth: 28, minHeight: 28),
              ),
              child: Row(children: [
                Expanded(child: _ExtraRow(
                  label: 'HOME', value: app.config.homeTimeouts, color: AppColors.homeTeam,
                  onDec: () => app.adjustTimeout('home', -1), onInc: () => app.adjustTimeout('home', 1))),
                const SizedBox(width: 12),
                Expanded(child: _ExtraRow(
                  label: 'AWAY', value: app.config.awayTimeouts, color: AppColors.awayTeam,
                  onDec: () => app.adjustTimeout('away', -1), onInc: () => app.adjustTimeout('away', 1))),
              ]),
            ),
            SectionCard(
              title: 'FOULS',
              trailing: IconButton(
                icon: const Icon(Icons.refresh, size: 18, color: AppColors.danger),
                onPressed: () => app.resetFouls(),
                padding: EdgeInsets.zero,
                constraints: const BoxConstraints(minWidth: 28, minHeight: 28),
              ),
              child: Row(children: [
                Expanded(child: _ExtraRow(
                  label: 'HOME', value: app.config.homeFouls, color: AppColors.homeTeam,
                  onDec: () => app.adjustFoul('home', -1), onInc: () => app.adjustFoul('home', 1))),
                const SizedBox(width: 12),
                Expanded(child: _ExtraRow(
                  label: 'AWAY', value: app.config.awayFouls, color: AppColors.awayTeam,
                  onDec: () => app.adjustFoul('away', -1), onInc: () => app.adjustFoul('away', 1))),
              ]),
            ),
          ],

          if (hasShotClock) ShotClockWidget(hasReset: isBasketball),

          AdsPanel(onReturnToScores: () {
            app.sendSportProgram();
            if (!app.laptopScoring) {
              Future.delayed(const Duration(milliseconds: 50), app.resendAll);
            }
          }),
        ],
      ),
    );
  }
}

// ─── Basketball score row (+1/+2/+3) ─────────────────────────────────────────

class _BasketballScoreRow extends StatefulWidget {
  final String label;
  final int value;
  final Color labelColor;
  final VoidCallback onDecrement;
  final VoidCallback onAdd1;
  final VoidCallback onAdd2;
  final VoidCallback onAdd3;
  final ValueChanged<int>? onManualEdit;

  const _BasketballScoreRow({
    required this.label,
    required this.value,
    required this.labelColor,
    required this.onDecrement,
    required this.onAdd1,
    required this.onAdd2,
    required this.onAdd3,
    this.onManualEdit,
  });

  @override
  State<_BasketballScoreRow> createState() => _BasketballScoreRowState();
}

class _BasketballScoreRowState extends State<_BasketballScoreRow> {
  late TextEditingController _ctrl;
  late FocusNode _focus;

  @override
  void initState() {
    super.initState();
    _ctrl = TextEditingController(text: '${widget.value}');
    _focus = FocusNode();
    _focus.addListener(() {
      if (!mounted) return;
      if (!_focus.hasFocus && _ctrl.text.isEmpty) {
        _ctrl.text = '${widget.value}';
      }
    });
  }

  @override
  void didUpdateWidget(_BasketballScoreRow old) {
    super.didUpdateWidget(old);
    if (old.value != widget.value && !_focus.hasFocus) {
      _ctrl.text = '${widget.value}';
    }
  }

  @override
  void dispose() {
    _focus.dispose();
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            SizedBox(
              width: 72,
              child: Text(widget.label,
                style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: widget.labelColor),
                maxLines: 1, overflow: TextOverflow.ellipsis),
            ),
            // − button
            _ActionBtn(label: '−', color: AppColors.danger, onTap: widget.onDecrement),
            const SizedBox(width: 8),
            // Score display
            Expanded(
              child: TextField(
                controller: _ctrl,
                focusNode: _focus,
                textAlign: TextAlign.center,
                keyboardType: TextInputType.number,
                style: const TextStyle(fontSize: 28, fontWeight: FontWeight.bold, color: Colors.white),
                decoration: InputDecoration(
                  filled: true,
                  fillColor: AppColors.background,
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(8),
                    borderSide: const BorderSide(color: AppColors.surfaceBorder),
                  ),
                  enabledBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(8),
                    borderSide: const BorderSide(color: AppColors.surfaceBorder),
                  ),
                  contentPadding: const EdgeInsets.symmetric(vertical: 10),
                ),
                onSubmitted: (v) {
                  if (widget.onManualEdit != null) {
                    widget.onManualEdit!(int.tryParse(v) ?? widget.value);
                  }
                },
                onEditingComplete: () {
                  if (_ctrl.text.isEmpty) {
                    _ctrl.text = '${widget.value}';
                  } else if (widget.onManualEdit != null) {
                    widget.onManualEdit!(int.tryParse(_ctrl.text) ?? widget.value);
                  }
                  FocusScope.of(context).unfocus();
                },
              ),
            ),
          ],
        ),
        const SizedBox(height: 6),
        // +1 / +2 / +3 buttons row
        Row(
          children: [
            const SizedBox(width: 80), // align with score column
            Expanded(
              child: Row(
                children: [
                  _PointBtn(label: '+1', color: AppColors.success, onTap: widget.onAdd1),
                  const SizedBox(width: 6),
                  _PointBtn(label: '+2', color: AppColors.accentDark, onTap: widget.onAdd2),
                  const SizedBox(width: 6),
                  _PointBtn(label: '+3', color: AppColors.warning, onTap: widget.onAdd3),
                ],
              ),
            ),
          ],
        ),
      ],
    );
  }
}

class _PointBtn extends StatelessWidget {
  final String label;
  final Color color;
  final VoidCallback onTap;
  const _PointBtn({required this.label, required this.color, required this.onTap});
  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Material(
        color: color,
        borderRadius: BorderRadius.circular(8),
        child: InkWell(
          borderRadius: BorderRadius.circular(8),
          onTap: onTap,
          child: Container(
            alignment: Alignment.center,
            padding: const EdgeInsets.symmetric(vertical: 8),
            child: Text(label,
              style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: Colors.white)),
          ),
        ),
      ),
    );
  }
}

class _ActionBtn extends StatelessWidget {
  final String label;
  final Color color;
  final VoidCallback onTap;
  const _ActionBtn({required this.label, required this.color, required this.onTap});
  @override
  Widget build(BuildContext context) {
    return Material(
      color: color,
      borderRadius: BorderRadius.circular(10),
      child: InkWell(
        borderRadius: BorderRadius.circular(10),
        onTap: onTap,
        child: SizedBox(
          width: 46, height: 46,
          child: Center(child: Text(label,
            style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: Colors.white))),
        ),
      ),
    );
  }
}

// ─── Extra row (timeouts/fouls) ───────────────────────────────────────────────

class _ExtraRow extends StatelessWidget {
  final String label;
  final int value;
  final Color color;
  final VoidCallback onDec, onInc;
  const _ExtraRow({required this.label, required this.value, required this.color, required this.onDec, required this.onInc});
  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text(label, style: TextStyle(fontSize: 11, color: color, fontWeight: FontWeight.bold)),
        const SizedBox(height: 6),
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            _MiniBtn('−', AppColors.danger, onDec),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 10),
              child: Text('$value', style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: Colors.white)),
            ),
            _MiniBtn('+', AppColors.success, onInc),
          ],
        ),
      ],
    );
  }
}

class _MiniBtn extends StatelessWidget {
  final String l; final Color c; final VoidCallback t;
  const _MiniBtn(this.l, this.c, this.t);
  @override
  Widget build(BuildContext ctx) => Material(
    color: c, borderRadius: BorderRadius.circular(6),
    child: InkWell(borderRadius: BorderRadius.circular(6), onTap: t,
      child: SizedBox(width: 32, height: 32,
        child: Center(child: Text(l, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white))))),
  );
}
