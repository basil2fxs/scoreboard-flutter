import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import '../providers/app_provider.dart';
import '../theme/app_theme.dart';
import '../widgets/team_names_card.dart';
import '../widgets/section_card.dart';
import '../widgets/ads_panel.dart';
import '../widgets/settings_dialogs.dart';

class CricketScreen extends StatefulWidget {
  const CricketScreen({super.key});
  @override
  State<CricketScreen> createState() => _CricketScreenState();
}

class _CricketScreenState extends State<CricketScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final app = context.read<AppProvider>();
      app.initTimerForSport('Cricket');
      app.sendSportProgram();
      Future.delayed(const Duration(milliseconds: 50), app.resendAll);
    });
  }

  @override
  Widget build(BuildContext context) {
    final app      = context.watch<AppProvider>();
    final c        = app.config;
    final isLaptop = app.laptopScoring;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Cricket Match'),
        leading: BackButton(onPressed: () {
          app.backToHome();
          Navigator.pushReplacementNamed(context, '/home');
        }),
        actions: [
          IconButton(
            icon: const Icon(Icons.tune, size: 20),
            tooltip: 'Counter Channels',
            onPressed: () => showCounterSettingsDialog(context, 'Cricket'),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.only(bottom: 24),
        children: [
          if (!isLaptop) const TeamNamesCard(sport: 'Cricket'),
          _CricketTeamCard(
            label: c.cricketHomeName.isEmpty ? 'HOME' : c.cricketHomeName,
            color: AppColors.homeTeam,
            runs: c.cricketHomeRuns, wickets: c.cricketHomeWickets,
            onRuns   : (d) => app.adjustCricket('homeRuns', d),
            onWickets: (d) => app.adjustCricket('homeWickets', d),
            onManualRuns   : (v) => app.setCricketField('homeRuns', v),
            onManualWickets: (v) => app.setCricketField('homeWickets', v),
            onReset: () => app.resetCricketScores('home'),
          ),
          _CricketTeamCard(
            label: c.cricketAwayName.isEmpty ? 'AWAY' : c.cricketAwayName,
            color: AppColors.awayTeam,
            runs: c.cricketAwayRuns, wickets: c.cricketAwayWickets,
            onRuns   : (d) => app.adjustCricket('awayRuns', d),
            onWickets: (d) => app.adjustCricket('awayWickets', d),
            onManualRuns   : (v) => app.setCricketField('awayRuns', v),
            onManualWickets: (v) => app.setCricketField('awayWickets', v),
            onReset: () => app.resetCricketScores('away'),
          ),
          SectionCard(
            title: 'MATCH INFO',
            trailing: IconButton(
              icon: const Icon(Icons.refresh, size: 18, color: AppColors.danger),
              onPressed: () => app.resetCricketMatchInfo(),
              padding: EdgeInsets.zero,
              constraints: const BoxConstraints(minWidth: 28, minHeight: 28),
            ),
            child: Column(children: [
              _CricketStatRow(label: 'Extras', value: c.cricketExtras,
                onDelta: (d) => app.adjustCricket('extras', d),
                onManual: (v) => app.setCricketField('extras', v)),
              const SizedBox(height: 10),
              _CricketStatRow(label: 'Overs',  value: c.cricketOvers,
                onDelta: (d) => app.adjustCricket('overs', d),
                onManual: (v) => app.setCricketField('overs', v)),
            ]),
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

class _CricketTeamCard extends StatelessWidget {
  final String label; final Color color;
  final int runs, wickets;
  final ValueChanged<int> onRuns, onWickets;
  final ValueChanged<int> onManualRuns, onManualWickets;
  final VoidCallback onReset;
  const _CricketTeamCard({
    required this.label, required this.color,
    required this.runs, required this.wickets,
    required this.onRuns, required this.onWickets,
    required this.onManualRuns, required this.onManualWickets,
    required this.onReset,
  });
  @override
  Widget build(BuildContext context) {
    return SectionCard(
      title: label.toUpperCase(),
      trailing: IconButton(
        icon: const Icon(Icons.refresh, size: 18, color: AppColors.danger),
        onPressed: onReset, padding: EdgeInsets.zero,
        constraints: const BoxConstraints(minWidth: 28, minHeight: 28),
      ),
      child: Column(children: [
        _CricketStatRow(label: 'Runs',    value: runs,    onDelta: onRuns,    onManual: onManualRuns,    labelColor: color),
        const SizedBox(height: 10),
        _CricketStatRow(label: 'Wickets', value: wickets, onDelta: onWickets, onManual: onManualWickets, labelColor: color),
      ]),
    );
  }
}

class _CricketStatRow extends StatefulWidget {
  final String label; final int value;
  final ValueChanged<int> onDelta, onManual;
  final Color labelColor;
  const _CricketStatRow({required this.label, required this.value, required this.onDelta, required this.onManual, this.labelColor = AppColors.textSecondary});
  @override State<_CricketStatRow> createState() => _CricketStatRowState();
}
class _CricketStatRowState extends State<_CricketStatRow> {
  late TextEditingController _c;
  @override void initState() { super.initState(); _c = TextEditingController(text: '${widget.value}'); }
  @override void didUpdateWidget(_CricketStatRow old) {
    super.didUpdateWidget(old);
    if (old.value != widget.value) _c.text = '${widget.value}';
  }
  @override void dispose() { _c.dispose(); super.dispose(); }
  @override
  Widget build(BuildContext context) {
    return Row(children: [
      SizedBox(width: 72, child: Text(widget.label, style: TextStyle(color: widget.labelColor, fontSize: 13, fontWeight: FontWeight.bold))),
      _SBtn('−', AppColors.danger, () => widget.onDelta(-1)),
      const SizedBox(width: 6),
      Expanded(child: TextField(
        controller: _c, textAlign: TextAlign.center,
        keyboardType: TextInputType.number,
        inputFormatters: [FilteringTextInputFormatter.digitsOnly],
        style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: Colors.white),
        decoration: const InputDecoration(filled: true, fillColor: AppColors.background,
          border: OutlineInputBorder(borderSide: BorderSide(color: AppColors.surfaceBorder)),
          enabledBorder: OutlineInputBorder(borderSide: BorderSide(color: AppColors.surfaceBorder)),
          contentPadding: EdgeInsets.symmetric(vertical: 8)),
        onSubmitted: (v) => widget.onManual(int.tryParse(v) ?? widget.value),
      )),
      const SizedBox(width: 6),
      _SBtn('+', AppColors.success, () => widget.onDelta(1)),
    ]);
  }
}
class _SBtn extends StatelessWidget {
  final String l; final Color c; final VoidCallback t;
  const _SBtn(this.l, this.c, this.t);
  @override Widget build(BuildContext ctx) => Material(color: c, borderRadius: BorderRadius.circular(8),
    child: InkWell(borderRadius: BorderRadius.circular(8), onTap: t,
      child: SizedBox(width: 38, height: 38, child: Center(child: Text(l, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white))))));
}
