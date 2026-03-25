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
import 'remapping_screen.dart';

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
      app.initTimerForSport('Soccer');
      app.sendZeroThenResend('Soccer');
    });
  }

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppProvider>();
    return Scaffold(
      appBar: AppBar(
        title: const Text('Soccer'),
        leading: BackButton(onPressed: () {
          app.backToHome();
          Navigator.pushReplacementNamed(context, '/home');
        }),
        actions: [
          if (app.remappingMode)
            TextButton.icon(
              onPressed: () => Navigator.push(context,
                MaterialPageRoute(builder: (_) => const RemappingScreen(sport: 'Soccer'))),
              icon: const Icon(Icons.cable_outlined, size: 18, color: AppColors.accent),
              label: const Text('Remapping',
                  style: TextStyle(color: AppColors.accent, fontWeight: FontWeight.bold)),
            ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.only(bottom: 24),
        children: [
          if (!app.laptopScoring) const TeamNamesCard(sport: 'Soccer'),
          const TimerWidget(),
          SectionCard(
            title: 'SCORES',
            titleTrailing: SettingsIconButton(
              onTap: () => showCounterSettingsDialog(context, 'Soccer')),
            trailing: IconButton(
              icon: const Icon(Icons.refresh, size: 24),
              onPressed: () => context.read<AppProvider>().resetScores(),
              style: IconButton.styleFrom(backgroundColor: AppColors.danger.withOpacity(0.15), foregroundColor: AppColors.danger, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8))), padding: const EdgeInsets.all(6),
              constraints: const BoxConstraints(minWidth: 38, minHeight: 38),
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
