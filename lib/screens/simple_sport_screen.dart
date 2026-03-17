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
      Future.delayed(const Duration(milliseconds: 150), app.resendAll);
    });
  }

  @override
  Widget build(BuildContext context) {
    final app   = context.watch<AppProvider>();
    final sport = app.config.currentSport ?? 'Rugby';
    final isHockey     = sport == 'Hockey';
    final isBasketball = sport == 'Basketball';
    final hasShotClock = isHockey || isBasketball;

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
          TeamNamesCard(sport: sport),
          const TimerWidget(),
          // Scores
          SectionCard(
            title: 'SCORES',
            trailing: IconButton(
              icon: const Icon(Icons.refresh, size: 18, color: AppColors.danger),
              onPressed: () => app.resetScores(),
            ),
            child: Column(
              children: [
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
            ),
          ),
          // Basketball extras
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
            Future.delayed(const Duration(milliseconds: 150), app.resendAll);
          }),
        ],
      ),
    );
  }
}

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
