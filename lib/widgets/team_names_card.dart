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
  late FocusNode _homeFocus;
  late FocusNode _awayFocus;

  // Track last known non-blank values so we can restore on blank unfocus
  String _lastHome = '';
  String _lastAway = '';

  @override
  void initState() {
    super.initState();
    final cfg = context.read<AppProvider>().config;
    _lastHome = _getHome(cfg).isNotEmpty ? _getHome(cfg) : 'HOME';
    _lastAway = _getAway(cfg).isNotEmpty ? _getAway(cfg) : 'AWAY';
    _homeCtr = TextEditingController(text: _lastHome);
    _awayCtr = TextEditingController(text: _lastAway);

    _homeFocus = FocusNode()..addListener(_onHomeFocusChange);
    _awayFocus = FocusNode()..addListener(_onAwayFocusChange);
  }

  void _onHomeFocusChange() {
    if (!_homeFocus.hasFocus && _homeCtr.text.isEmpty) {
      // Restore last good value if user cleared the field
      _homeCtr.text = _lastHome;
      _setHome(context.read<AppProvider>(), _lastHome);
    }
  }

  void _onAwayFocusChange() {
    if (!_awayFocus.hasFocus && _awayCtr.text.isEmpty) {
      _awayCtr.text = _lastAway;
      _setAway(context.read<AppProvider>(), _lastAway);
    }
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
    _homeFocus.removeListener(_onHomeFocusChange);
    _awayFocus.removeListener(_onAwayFocusChange);
    _homeFocus.dispose();
    _awayFocus.dispose();
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
          _nameRow('Home', _homeCtr, _homeFocus, AppColors.homeTeam, (v) {
            if (v.isNotEmpty) _lastHome = v;
            _setHome(app, v);
          }),
          const SizedBox(height: 8),
          _nameRow('Away', _awayCtr, _awayFocus, AppColors.awayTeam, (v) {
            if (v.isNotEmpty) _lastAway = v;
            _setAway(app, v);
          }),
        ],
      ),
    );
  }

  Widget _nameRow(String label, TextEditingController ctrl, FocusNode focus,
      Color color, ValueChanged<String> onChange) {
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
            focusNode: focus,
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
