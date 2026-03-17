import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_provider.dart';
import '../theme/app_theme.dart';
import 'section_card.dart';
import 'settings_dialogs.dart';

/// Team name input card — adapts for AFL / Cricket / generic sports.
class TeamNamesCard extends StatefulWidget {
  final String sport;
  const TeamNamesCard({super.key, required this.sport});
  @override
  State<TeamNamesCard> createState() => _TeamNamesCardState();
}

class _TeamNamesCardState extends State<TeamNamesCard> {
  late TextEditingController _homeCtr;
  late TextEditingController _awayCtr;

  @override
  void initState() {
    super.initState();
    final cfg = context.read<AppProvider>().config;
    _homeCtr = TextEditingController(text: _getHome(cfg));
    _awayCtr = TextEditingController(text: _getAway(cfg));
  }

  String _getHome(c) {
    if (widget.sport == 'AFL')    return c.aflHomeName;
    if (widget.sport == 'Cricket') return c.cricketHomeName;
    return c.homeName;
  }
  String _getAway(c) {
    if (widget.sport == 'AFL')    return c.aflAwayName;
    if (widget.sport == 'Cricket') return c.cricketAwayName;
    return c.awayName;
  }

  void _setHome(AppProvider app, String v) {
    if (widget.sport == 'AFL')    { app.setAflHomeName(v); return; }
    if (widget.sport == 'Cricket') { app.setCricketHomeName(v); return; }
    app.setHomeName(v);
  }
  void _setAway(AppProvider app, String v) {
    if (widget.sport == 'AFL')    { app.setAflAwayName(v); return; }
    if (widget.sport == 'Cricket') { app.setCricketAwayName(v); return; }
    app.setAwayName(v);
  }

  @override
  void dispose() {
    _homeCtr.dispose();
    _awayCtr.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final app = context.read<AppProvider>();
    return SectionCard(
      title: 'TEAM NAMES',
      trailing: SettingsIconButton(onTap: () => showTeamNameSettingsDialog(context)),
      child: Column(
        children: [
          _nameRow('Home', _homeCtr, AppColors.homeTeam, (v) => _setHome(app, v)),
          const SizedBox(height: 8),
          _nameRow('Away', _awayCtr, AppColors.awayTeam, (v) => _setAway(app, v)),
        ],
      ),
    );
  }

  Widget _nameRow(String label, TextEditingController ctrl, Color color, ValueChanged<String> onChange) {
    return Row(
      children: [
        SizedBox(
          width: 48,
          child: Text(label,
            style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: color)),
        ),
        Expanded(
          child: TextField(
            controller: ctrl,
            style: const TextStyle(fontSize: 16, color: Colors.white, fontWeight: FontWeight.bold),
            textCapitalization: TextCapitalization.characters,
            decoration: const InputDecoration(
              filled: true,
              fillColor: AppColors.surfaceHigh,
              border: OutlineInputBorder(borderSide: BorderSide.none),
              contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            ),
            onChanged: onChange,
          ),
        ),
      ],
    );
  }
}
