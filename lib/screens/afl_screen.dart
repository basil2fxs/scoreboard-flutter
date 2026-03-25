import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import '../providers/app_provider.dart';
import '../theme/app_theme.dart';
import '../widgets/team_names_card.dart';
import '../widgets/timer_widget.dart';
import '../widgets/afl_quarter_widget.dart';
import '../widgets/section_card.dart';
import '../widgets/ads_panel.dart';
import '../widgets/settings_dialogs.dart';
import 'remapping_screen.dart';

class AflScreen extends StatefulWidget {
  const AflScreen({super.key});
  @override
  State<AflScreen> createState() => _AflScreenState();
}

class _AflScreenState extends State<AflScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final app = context.read<AppProvider>();
      app.initTimerForSport('AFL');
      app.sendZeroThenResend('AFL');
    });
  }

  @override
  Widget build(BuildContext context) {
    final app     = context.watch<AppProvider>();
    final c       = app.config;
    final isLaptop = app.laptopScoring;

    return Scaffold(
      appBar: AppBar(
        title: const Text('AFL Match'),
        leading: BackButton(onPressed: () {
          app.backToHome();
          Navigator.pushReplacementNamed(context, '/home');
        }),
        actions: [
          if (app.remappingMode)
            TextButton.icon(
              onPressed: () => Navigator.push(context,
                MaterialPageRoute(builder: (_) => const RemappingScreen(sport: 'AFL'))),
              icon: const Icon(Icons.cable_outlined, size: 18, color: AppColors.accent),
              label: const Text('Remapping',
                  style: TextStyle(color: AppColors.accent, fontWeight: FontWeight.bold)),
            ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.only(bottom: 24),
        children: [
          if (!isLaptop) const TeamNamesCard(sport: 'AFL'),
          if (!isLaptop) const AflQuarterWidget(),
          const TimerWidget(),
          _AflTeamCard(
            teamLabel: c.aflHomeName.isEmpty ? 'HOME' : c.aflHomeName,
            teamColor: AppColors.homeTeam,
            goals : c.aflHomeGoals,
            points: c.aflHomePoints,
            total : app.aflHomeTotal,
            onGoals : (d) => app.adjustAflGoals('home', d),
            onPoints: (d) => app.adjustAflPoints('home', d),
            onReset : ()  => app.resetAflScores('home'),
            onManualGoals : (v) => app.setAflScore('home', 'goals', v),
            onManualPoints: (v) => app.setAflScore('home', 'points', v),
          ),
          _AflTeamCard(
            teamLabel: c.aflAwayName.isEmpty ? 'AWAY' : c.aflAwayName,
            teamColor: AppColors.awayTeam,
            goals : c.aflAwayGoals,
            points: c.aflAwayPoints,
            total : app.aflAwayTotal,
            onGoals : (d) => app.adjustAflGoals('away', d),
            onPoints: (d) => app.adjustAflPoints('away', d),
            onReset : ()  => app.resetAflScores('away'),
            onManualGoals : (v) => app.setAflScore('away', 'goals', v),
            onManualPoints: (v) => app.setAflScore('away', 'points', v),
          ),
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

class _AflTeamCard extends StatelessWidget {
  final String teamLabel;
  final Color teamColor;
  final int goals, points, total;
  final ValueChanged<int> onGoals, onPoints;
  final VoidCallback onReset;
  final ValueChanged<int> onManualGoals, onManualPoints;

  const _AflTeamCard({
    required this.teamLabel, required this.teamColor,
    required this.goals, required this.points, required this.total,
    required this.onGoals, required this.onPoints, required this.onReset,
    required this.onManualGoals, required this.onManualPoints,
  });

  @override
  Widget build(BuildContext context) {
    return SectionCard(
      title: teamLabel.toUpperCase(),
      trailing: IconButton(
        icon: const Icon(Icons.refresh, size: 24),
        onPressed: onReset,
        style: IconButton.styleFrom(backgroundColor: AppColors.danger.withOpacity(0.15), foregroundColor: AppColors.danger, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8))), padding: const EdgeInsets.all(6),
        constraints: const BoxConstraints(minWidth: 38, minHeight: 38),
      ),
      child: Column(
        children: [
          Center(
            child: Text(
              'TOTAL: $total',
              style: TextStyle(fontSize: 22, fontWeight: FontWeight.w900, color: teamColor),
            ),
          ),
          const SizedBox(height: 10),
          _AflRow(label: 'Goals',  value: goals,  onDelta: onGoals,  onManual: onManualGoals),
          const SizedBox(height: 10),
          _AflRow(label: 'Points', value: points, onDelta: onPoints, onManual: onManualPoints),
        ],
      ),
    );
  }
}

class _AflRow extends StatefulWidget {
  final String label;
  final int value;
  final ValueChanged<int> onDelta;
  final ValueChanged<int> onManual;
  const _AflRow({required this.label, required this.value, required this.onDelta, required this.onManual});
  @override
  State<_AflRow> createState() => _AflRowState();
}
class _AflRowState extends State<_AflRow> {
  late TextEditingController _ctrl;
  @override void initState() { super.initState(); _ctrl = TextEditingController(text: '${widget.value}'); }
  @override void didUpdateWidget(_AflRow old) {
    super.didUpdateWidget(old);
    if (old.value != widget.value) _ctrl.text = '${widget.value}';
  }
  @override void dispose() { _ctrl.dispose(); super.dispose(); }
  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        SizedBox(width: 60, child: Text(widget.label,
            style: const TextStyle(color: AppColors.textSecondary, fontSize: 13, fontWeight: FontWeight.bold))),
        _Btn('−', AppColors.danger, () => widget.onDelta(-1)),
        const SizedBox(width: 8),
        Expanded(
          child: TextField(
            controller: _ctrl,
            textAlign: TextAlign.center,
            keyboardType: TextInputType.number,
            inputFormatters: [FilteringTextInputFormatter.digitsOnly],
            style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: Colors.white),
            decoration: const InputDecoration(
              filled: true, fillColor: AppColors.background,
              border: OutlineInputBorder(borderSide: BorderSide(color: AppColors.surfaceBorder)),
              enabledBorder: OutlineInputBorder(borderSide: BorderSide(color: AppColors.surfaceBorder)),
              contentPadding: EdgeInsets.symmetric(vertical: 10),
            ),
            onSubmitted: (v) => widget.onManual(int.tryParse(v) ?? widget.value),
          ),
        ),
        const SizedBox(width: 8),
        _Btn('+', AppColors.success, () => widget.onDelta(1)),
      ],
    );
  }
}

class _Btn extends StatelessWidget {
  final String label; final Color color; final VoidCallback onTap;
  const _Btn(this.label, this.color, this.onTap);
  @override
  Widget build(BuildContext ctx) => Material(
    color: color, borderRadius: BorderRadius.circular(8),
    child: InkWell(borderRadius: BorderRadius.circular(8), onTap: onTap,
      child: SizedBox(width: 40, height: 40,
        child: Center(child: Text(label, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: Colors.white))))),
  );
}
