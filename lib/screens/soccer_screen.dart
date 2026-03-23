import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_provider.dart';
import '../theme/app_theme.dart';
import '../widgets/team_names_card.dart';
import '../widgets/timer_widget.dart';
import '../widgets/score_card.dart';
import '../widgets/section_card.dart';
import '../widgets/ads_panel.dart';
import '../widgets/settings_dialogs.dart';

class SoccerScreen extends StatefulWidget {
  const SoccerScreen({super.key});
  @override
  State<SoccerScreen> createState() => _SoccerScreenState();
}

class _SoccerScreenState extends State<SoccerScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final app = context.read<AppProvider>();
      app.initTimerForSport('Soccer/ Universal');
      app.sendSportProgram();
      Future.delayed(const Duration(milliseconds: 50), app.resendAll);
    });
  }

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppProvider>();
    return Scaffold(
      appBar: AppBar(
        title: const Text('Soccer/ Universal'),
        leading: BackButton(onPressed: () {
          app.backToHome();
          Navigator.pushReplacementNamed(context, '/home');
        }),
      ),
      body: ListView(
        padding: const EdgeInsets.only(bottom: 24),
        children: [
          if (!app.laptopScoring) const TeamNamesCard(sport: 'Soccer/ Universal'),
          const TimerWidget(),
          SectionCard(
            title: 'SCORES',
            trailing: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                SettingsIconButton(
                  onTap: () => showCounterSettingsDialog(context, 'Soccer/ Universal')),
                const SizedBox(width: 4),
                IconButton(
                  icon: const Icon(Icons.refresh, size: 18, color: AppColors.danger),
                  onPressed: () => context.read<AppProvider>().resetScores(),
                  padding: EdgeInsets.zero,
                  constraints: const BoxConstraints(minWidth: 28, minHeight: 28),
                ),
              ],
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
