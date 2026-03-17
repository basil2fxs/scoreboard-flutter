import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:flutter/scheduler.dart';
import '../models/app_config.dart';
import '../models/advertisement.dart';
import '../services/udp_service.dart';
import '../services/ramt_service.dart';
import '../services/config_service.dart';

enum ConnectionStatus { disconnected, connecting, connected, bypass }

const Map<String, String> kSportPrograms = {
  'AFL'       : '1',
  'Soccer'    : '2',
  'Cricket'   : '3',
  'Rugby'     : '4',
  'Hockey'    : '5',
  'Basketball': '6',
};

class AppProvider extends ChangeNotifier {
  // ─── Services ──────────────────────────────────────────────────────────────
  final UdpService     _udp    = UdpService();
  late final RamtService _ramt;
  final ConfigService  _cfg    = ConfigService();

  // ─── Persisted state ───────────────────────────────────────────────────────
  AppConfig _config = const AppConfig();
  AppConfig get config => _config;

  // ─── Connection ────────────────────────────────────────────────────────────
  ConnectionStatus _connStatus = ConnectionStatus.disconnected;
  ConnectionStatus get connStatus => _connStatus;
  bool get isConnected => _connStatus == ConnectionStatus.connected
                       || _connStatus == ConnectionStatus.bypass;

  // ─── Timer engine ──────────────────────────────────────────────────────────
  bool   _timerRunning = false;
  bool   get timerRunning => _timerRunning;
  Timer? _timerJob;
  String? _timerConfiguredFor; // which sport last set timer defaults

  // ─── Shot clock ────────────────────────────────────────────────────────────
  bool   _shotClockRunning = false;
  bool   get shotClockRunning => _shotClockRunning;
  int    _shotClockSecondsLive = 30;
  int    get shotClockSecondsLive => _shotClockSecondsLive;
  bool   _shotClockVisible = false;
  bool   get shotClockVisible => _shotClockVisible;
  Timer? _shotClockJob;

  // ─── Ad loop ───────────────────────────────────────────────────────────────
  bool   _adLoopActive = false;
  bool   get adLoopActive => _adLoopActive;
  int    _adLoopIdx = 0;
  List<(Advertisement, int)> _adPlaylist = []; // (ad, durationMs)
  Timer? _adLoopJob;

  // ─── Ad preview (editor live preview) ─────────────────────────────────────
  bool _adPreviewActive = false;
  bool get adPreviewActive => _adPreviewActive;

  // ─── Auto-reconnect ────────────────────────────────────────────────────────
  Timer? _reconnectTimer;

  // ─── Init ──────────────────────────────────────────────────────────────────
  AppProvider() {
    _ramt = RamtService(_udp);
    _init();
  }

  Future<void> _init() async {
    _config = await _cfg.load();
    _ramt.ultraWide    = _config.ultraWide;
    _ramt.singleColour = _config.singleColour;
    _shotClockSecondsLive = _config.shotClockSeconds;

    // Defer the first UI rebuild and network probe to after the first frame
    // to avoid doing heavy work while Flutter is still rendering the initial
    // layout (prevents the "Skipped N frames" startup warning).
    SchedulerBinding.instance.addPostFrameCallback((_) {
      notifyListeners();
      _startAutoReconnect();
    });
  }

  // ─── Persistence ───────────────────────────────────────────────────────────

  void _update(AppConfig updated, {bool notify = true}) {
    _config = updated;
    _cfg.save(_config);
    if (notify) notifyListeners();
  }

  // ─── Connection ────────────────────────────────────────────────────────────

  void _startAutoReconnect() {
    _reconnectTimer?.cancel();
    _reconnectTimer = Timer.periodic(const Duration(seconds: 3), (_) {
      // Silent background test — no UI state change so button doesn't flicker
      _testConnectionBackground();
    });
  }

  /// Background probe — does not set 'connecting' state so the UI stays calm.
  Future<void> _testConnectionBackground() async {
    if (_connStatus != ConnectionStatus.disconnected) return;
    try {
      final ok = await _udp.testConnection();
      if (_connStatus == ConnectionStatus.bypass) return;
      if (ok) {
        _connStatus = ConnectionStatus.connected;
        notifyListeners();
      }
      // On failure stay disconnected; timer will retry automatically.
    } catch (_) {
      // Silently ignore — network unavailable (e.g. macOS sandbox).
    }
  }

  /// Manual connect (button press) — shows the 'connecting' spinner.
  Future<void> testConnection() async {
    if (_connStatus == ConnectionStatus.bypass) return;
    _connStatus = ConnectionStatus.connecting;
    notifyListeners();
    final ok = await _udp.testConnection();
    // Re-check bypass in case it was enabled while the async call was in flight
    if (_connStatus == ConnectionStatus.bypass) return;
    _connStatus = ok ? ConnectionStatus.connected : ConnectionStatus.disconnected;
    notifyListeners();
  }

  void enableBypass(bool value) {
    _udp.bypassMode = value;
    _connStatus = value ? ConnectionStatus.bypass : ConnectionStatus.disconnected;
    if (!value) testConnection();
    notifyListeners();
  }

  bool get bypassMode => _udp.bypassMode;

  // ─── Display Setup ─────────────────────────────────────────────────────────

  void setDisplaySize(int w, int h) {
    _update(_config.copyWith(displayWidth: w, displayHeight: h));
  }

  void setSingleColour(bool v) {
    _ramt.singleColour = v;
    _update(_config.copyWith(singleColour: v));
  }

  void setUltraWide(bool v) {
    _ramt.ultraWide = v;
    _update(_config.copyWith(ultraWide: v));
  }

  // ─── Sport selection ───────────────────────────────────────────────────────

  void selectSport(String sport) {
    _update(_config.copyWith(currentSport: sport));
  }

  void sendSportProgram() {
    final p = kSportPrograms[_config.currentSport];
    if (p != null) _ramt.sendProgram(p);
  }

  // ─── Timer ─────────────────────────────────────────────────────────────────

  /// Default shot clock seconds per sport.
  static int defaultShotClockFor(String sport) {
    if (sport == 'Hockey') return 40;
    return 30; // Basketball and others
  }

  /// Call when entering a sport screen to set timer / shot-clock defaults (once per sport).
  void initTimerForSport(String sport) {
    if (_timerConfiguredFor == sport || _timerRunning) return;
    _timerConfiguredFor = sport;
    final scDefault = defaultShotClockFor(sport);
    switch (sport) {
      case 'AFL':
        _update(_config.copyWith(
          timerCountdown    : true,
          timerTargetSeconds: 20 * 60,
          timerSeconds      : 20 * 60,
        ));
        break;
      case 'Hockey':
        _update(_config.copyWith(
          timerCountdown    : true,
          timerTargetSeconds: 20 * 60,
          timerSeconds      : 20 * 60,
          shotClockSeconds  : scDefault,
        ));
        _shotClockSecondsLive = scDefault;
        break;
      case 'Basketball':
        _update(_config.copyWith(
          timerCountdown    : true,
          timerTargetSeconds: 12 * 60,
          timerSeconds      : 12 * 60,
          shotClockSeconds  : scDefault,
        ));
        _shotClockSecondsLive = scDefault;
        break;
      case 'Soccer':
      case 'Rugby':
      default:
        _update(_config.copyWith(
          timerCountdown    : false,
          timerTargetSeconds: 0,
          timerSeconds      : 0,
        ));
    }
  }

  /// Manually set the timer duration / direction from the Set Time dialog.
  void setTimerTime({required bool countdown, required int totalSeconds}) {
    pauseTimer();
    _update(_config.copyWith(
      timerCountdown    : countdown,
      timerTargetSeconds: countdown ? totalSeconds : 0,
      timerSeconds      : countdown ? totalSeconds : 0,
    ));
    _sendTimerDisplay();
  }

  /// Set the shot clock default reset value from the Set Time dialog.
  void setShotClockDefault(int seconds) {
    _shotClockSecondsLive = seconds;
    _update(_config.copyWith(shotClockSeconds: seconds));
    if (_shotClockVisible) {
      _ramt.sendShotClock(_shotClockSecondsLive, _config.shotClockStyle);
    }
  }

  void startTimer() {
    if (_timerRunning) return;
    _timerRunning = true;
    _timerJob = Timer.periodic(const Duration(seconds: 1), (_) => _timerTick());
    notifyListeners();
  }

  void pauseTimer() {
    _timerRunning = false;
    _timerJob?.cancel();
    _timerJob = null;
    notifyListeners();
  }

  void resetTimer() {
    pauseTimer();
    final target = _config.timerTargetSeconds;
    _update(_config.copyWith(
      timerSeconds: _config.timerCountdown ? target : 0,
    ));
    _sendTimerDisplay();
  }

  void _timerTick() {
    int s = _config.timerSeconds;
    if (_config.timerCountdown) {
      s = (s - 1).clamp(0, 9999);
      if (s == 0) {
        pauseTimer();
      }
    } else {
      s = s + 1;
    }
    _config = _config.copyWith(timerSeconds: s);
    _sendTimerDisplay();
    notifyListeners();
  }

  void _sendTimerDisplay() {
    final leading = _config.currentSport == 'AFL'
        ? _config.timerOffsetAfl
        : _config.timerOffsetDefault;
    _ramt.sendTimer(_config.timerSeconds, _config.timerStyle, leading);
  }

  void updateTimerStyle(DisplayStyle style) {
    _update(_config.copyWith(timerStyle: style));
    _sendTimerDisplay();
  }

  void updateTimerOffset(bool isAfl, int value) {
    _update(isAfl
      ? _config.copyWith(timerOffsetAfl: value)
      : _config.copyWith(timerOffsetDefault: value));
    _sendTimerDisplay();
  }

  String get timerDisplay {
    final s = _config.timerSeconds;
    return '${(s ~/ 60).toString().padLeft(2,'0')}:${(s % 60).toString().padLeft(2,'0')}';
  }

  // ─── Shot Clock ────────────────────────────────────────────────────────────

  /// Hockey: Start (appear + count down)
  void shotClockStart() {
    if (_shotClockRunning) return;
    _shotClockVisible = true;
    _shotClockRunning = true;
    _ramt.sendShotClock(_shotClockSecondsLive, _config.shotClockStyle);
    _shotClockJob = Timer.periodic(const Duration(seconds: 1), (_) => _shotClockTick());
    notifyListeners();
  }

  /// Hockey/Basketball Stop: reset + disappear
  void shotClockStop() {
    _shotClockRunning = false;
    _shotClockVisible = false;
    _shotClockJob?.cancel();
    _shotClockJob = null;
    _shotClockSecondsLive = _config.shotClockSeconds;
    _ramt.clearRamt8(_config.shotClockStyle);
    notifyListeners();
  }

  /// Basketball Reset: restart countdown immediately
  void shotClockReset() {
    _shotClockJob?.cancel();
    _shotClockJob = null;
    _shotClockSecondsLive = _config.shotClockSeconds;
    _ramt.sendShotClock(_shotClockSecondsLive, _config.shotClockStyle);
    if (_shotClockRunning) {
      _shotClockJob = Timer.periodic(const Duration(seconds: 1), (_) => _shotClockTick());
    }
    notifyListeners();
  }

  void _shotClockTick() {
    _shotClockSecondsLive = (_shotClockSecondsLive - 1).clamp(0, 999);
    _ramt.sendShotClock(_shotClockSecondsLive, _config.shotClockStyle);
    if (_shotClockSecondsLive == 0) {
      _shotClockRunning = false;
      _shotClockJob?.cancel();
      _shotClockJob = null;
    }
    notifyListeners();
  }

  void updateShotClockStyle(DisplayStyle style) {
    _update(_config.copyWith(shotClockStyle: style));
    if (_shotClockVisible) {
      _ramt.sendShotClock(_shotClockSecondsLive, style);
    }
  }

  // ─── AFL Quarter ───────────────────────────────────────────────────────────

  void setAflQuarter(int q) {
    _update(_config.copyWith(aflQuarter: q));
    _ramt.sendAflQuarter(q, _config.aflQuarterStyle);
  }

  void updateAflQuarterStyle(DisplayStyle style) {
    _update(_config.copyWith(aflQuarterStyle: style));
    _ramt.sendAflQuarter(_config.aflQuarter, style);
  }

  // ─── Team Names (generic sports) ──────────────────────────────────────────

  void setHomeName(String name) {
    _update(_config.copyWith(homeName: name));
    _ramt.sendTeamName(name, 1, _config.teamStyle);
  }

  void setAwayName(String name) {
    _update(_config.copyWith(awayName: name));
    _ramt.sendTeamName(name, 3, _config.teamStyle);
  }

  void updateTeamStyle(DisplayStyle style) {
    _update(_config.copyWith(teamStyle: style));
    _ramt.sendTeamName(_config.homeName, 1, style);
    _ramt.sendTeamName(_config.awayName, 3, style);
  }

  // ─── AFL team names ────────────────────────────────────────────────────────

  void setAflHomeName(String name) {
    _update(_config.copyWith(aflHomeName: name, homeName: name));
    _ramt.sendTeamName(name, 1, _config.aflTeamStyle);
  }

  void setAflAwayName(String name) {
    _update(_config.copyWith(aflAwayName: name, awayName: name));
    _ramt.sendTeamName(name, 3, _config.aflTeamStyle);
  }

  void updateAflTeamStyle(DisplayStyle style) {
    _update(_config.copyWith(aflTeamStyle: style));
    _ramt.sendTeamName(_config.aflHomeName, 1, style);
    _ramt.sendTeamName(_config.aflAwayName, 3, style);
  }

  // ─── Cricket team names ────────────────────────────────────────────────────

  void setCricketHomeName(String name) {
    _update(_config.copyWith(cricketHomeName: name, homeName: name));
    _ramt.sendTeamName(name, 1, _config.cricketTeamStyle);
  }

  void setCricketAwayName(String name) {
    _update(_config.copyWith(cricketAwayName: name, awayName: name));
    _ramt.sendTeamName(name, 3, _config.cricketTeamStyle);
  }

  void updateCricketTeamStyle(DisplayStyle style) {
    _update(_config.copyWith(cricketTeamStyle: style));
    _ramt.sendTeamName(_config.cricketHomeName, 1, style);
    _ramt.sendTeamName(_config.cricketAwayName, 3, style);
  }

  // ─── Simple scores (Soccer, Rugby, Hockey, Basketball) ────────────────────

  void adjustScore(String team, int delta) {
    if (team == 'home') {
      final v = (_config.homeScore + delta).clamp(0, 999);
      _update(_config.copyWith(homeScore: v));
      _ramt.setCounter(1, v);
    } else {
      final v = (_config.awayScore + delta).clamp(0, 999);
      _update(_config.copyWith(awayScore: v));
      _ramt.setCounter(2, v);
    }
  }

  void setScore(String team, int value) {
    final v = value.clamp(0, 999);
    if (team == 'home') {
      _update(_config.copyWith(homeScore: v));
      _ramt.setCounter(1, v);
    } else {
      _update(_config.copyWith(awayScore: v));
      _ramt.setCounter(2, v);
    }
  }

  void resetScores() {
    _update(_config.copyWith(homeScore: 0, awayScore: 0));
    _ramt.setCounter(1, 0);
    _ramt.setCounter(2, 0);
  }

  // ─── AFL scores ────────────────────────────────────────────────────────────

  void adjustAflGoals(String team, int delta) {
    if (team == 'home') {
      final v = (_config.aflHomeGoals + delta).clamp(0, 999);
      _update(_config.copyWith(aflHomeGoals: v));
      delta > 0 ? _ramt.addCounter(1, delta) : _ramt.subtractCounter(1, -delta);
    } else {
      final v = (_config.aflAwayGoals + delta).clamp(0, 999);
      _update(_config.copyWith(aflAwayGoals: v));
      delta > 0 ? _ramt.addCounter(2, delta) : _ramt.subtractCounter(2, -delta);
    }
    _updateAflTotals();
  }

  void adjustAflPoints(String team, int delta) {
    if (team == 'home') {
      final v = (_config.aflHomePoints + delta).clamp(0, 999);
      _update(_config.copyWith(aflHomePoints: v));
      delta > 0 ? _ramt.addCounter(3, delta) : _ramt.subtractCounter(3, -delta);
    } else {
      final v = (_config.aflAwayPoints + delta).clamp(0, 999);
      _update(_config.copyWith(aflAwayPoints: v));
      delta > 0 ? _ramt.addCounter(4, delta) : _ramt.subtractCounter(4, -delta);
    }
    _updateAflTotals();
  }

  void setAflScore(String team, String type, int value) {
    final v = value.clamp(0, 999);
    if (team == 'home') {
      if (type == 'goals') {
        _update(_config.copyWith(aflHomeGoals: v));
        _ramt.setCounter(1, v);
      } else {
        _update(_config.copyWith(aflHomePoints: v));
        _ramt.setCounter(3, v);
      }
    } else {
      if (type == 'goals') {
        _update(_config.copyWith(aflAwayGoals: v));
        _ramt.setCounter(2, v);
      } else {
        _update(_config.copyWith(aflAwayPoints: v));
        _ramt.setCounter(4, v);
      }
    }
    _updateAflTotals();
  }

  void resetAflScores(String team) {
    if (team == 'home') {
      _update(_config.copyWith(aflHomeGoals: 0, aflHomePoints: 0));
      _ramt.setCounter(1, 0);
      _ramt.setCounter(3, 0);
    } else {
      _update(_config.copyWith(aflAwayGoals: 0, aflAwayPoints: 0));
      _ramt.setCounter(2, 0);
      _ramt.setCounter(4, 0);
    }
    _updateAflTotals();
  }

  void _updateAflTotals() {
    final ht = _config.aflHomeGoals * 6 + _config.aflHomePoints;
    final at = _config.aflAwayGoals * 6 + _config.aflAwayPoints;
    _ramt.setCounter(5, ht);
    _ramt.setCounter(6, at);
    notifyListeners();
  }

  int get aflHomeTotal => _config.aflHomeGoals * 6 + _config.aflHomePoints;
  int get aflAwayTotal => _config.aflAwayGoals * 6 + _config.aflAwayPoints;

  // ─── Cricket scores ────────────────────────────────────────────────────────

  void adjustCricket(String field, int delta) {
    final c = _config;
    AppConfig updated;
    int counterN;
    int newVal;
    switch (field) {
      case 'homeRuns':
        newVal = (c.cricketHomeRuns + delta).clamp(0, 9999);
        updated = c.copyWith(cricketHomeRuns: newVal); counterN = 1; break;
      case 'homeWickets':
        newVal = (c.cricketHomeWickets + delta).clamp(0, 10);
        updated = c.copyWith(cricketHomeWickets: newVal); counterN = 2; break;
      case 'awayRuns':
        newVal = (c.cricketAwayRuns + delta).clamp(0, 9999);
        updated = c.copyWith(cricketAwayRuns: newVal); counterN = 3; break;
      case 'awayWickets':
        newVal = (c.cricketAwayWickets + delta).clamp(0, 10);
        updated = c.copyWith(cricketAwayWickets: newVal); counterN = 4; break;
      case 'extras':
        newVal = (c.cricketExtras + delta).clamp(0, 999);
        updated = c.copyWith(cricketExtras: newVal); counterN = 5; break;
      case 'overs':
        newVal = (c.cricketOvers + delta).clamp(0, 999);
        updated = c.copyWith(cricketOvers: newVal); counterN = 6; break;
      default:
        return;
    }
    _update(updated);
    _ramt.setCounter(counterN, newVal);
  }

  void setCricketField(String field, int value) {
    adjustCricket(field, value - _getCricketField(field));
  }

  int _getCricketField(String f) {
    switch (f) {
      case 'homeRuns'    : return _config.cricketHomeRuns;
      case 'homeWickets' : return _config.cricketHomeWickets;
      case 'awayRuns'    : return _config.cricketAwayRuns;
      case 'awayWickets' : return _config.cricketAwayWickets;
      case 'extras'      : return _config.cricketExtras;
      case 'overs'       : return _config.cricketOvers;
      default: return 0;
    }
  }

  void resetCricketScores(String team) {
    if (team == 'home') {
      _update(_config.copyWith(cricketHomeRuns: 0, cricketHomeWickets: 0));
      _ramt.setCounter(1, 0); _ramt.setCounter(2, 0);
    } else {
      _update(_config.copyWith(cricketAwayRuns: 0, cricketAwayWickets: 0));
      _ramt.setCounter(3, 0); _ramt.setCounter(4, 0);
    }
  }

  // ─── Basketball extras ─────────────────────────────────────────────────────

  void adjustTimeout(String team, int delta) {
    if (team == 'home') {
      final v = (_config.homeTimeouts + delta).clamp(0, 99);
      _update(_config.copyWith(homeTimeouts: v));
      _ramt.setCounter(3, v);
    } else {
      final v = (_config.awayTimeouts + delta).clamp(0, 99);
      _update(_config.copyWith(awayTimeouts: v));
      _ramt.setCounter(4, v);
    }
  }

  void adjustFoul(String team, int delta) {
    if (team == 'home') {
      final v = (_config.homeFouls + delta).clamp(0, 99);
      _update(_config.copyWith(homeFouls: v));
      _ramt.setCounter(5, v);
    } else {
      final v = (_config.awayFouls + delta).clamp(0, 99);
      _update(_config.copyWith(awayFouls: v));
      _ramt.setCounter(6, v);
    }
  }

  void resetTimeouts() {
    _update(_config.copyWith(homeTimeouts: 0, awayTimeouts: 0));
    _ramt.setCounter(3, 0);
    _ramt.setCounter(4, 0);
  }

  void resetFouls() {
    _update(_config.copyWith(homeFouls: 0, awayFouls: 0));
    _ramt.setCounter(5, 0);
    _ramt.setCounter(6, 0);
  }

  void resetCricketMatchInfo() {
    _update(_config.copyWith(cricketExtras: 0, cricketOvers: 0));
    _ramt.setCounter(5, 0);
    _ramt.setCounter(6, 0);
  }

  // ─── Resend all display data ────────────────────────────────────────────────

  void resendAll() {
    final c = _config;
    sendSportProgram();

    // Team names
    switch (c.currentSport) {
      case 'AFL':
        _ramt.sendTeamName(c.aflHomeName, 1, c.aflTeamStyle);
        _ramt.sendTeamName(c.aflAwayName, 3, c.aflTeamStyle);
        _ramt.setCounter(1, c.aflHomeGoals);
        _ramt.setCounter(2, c.aflAwayGoals);
        _ramt.setCounter(3, c.aflHomePoints);
        _ramt.setCounter(4, c.aflAwayPoints);
        _ramt.setCounter(5, aflHomeTotal);
        _ramt.setCounter(6, aflAwayTotal);
        _ramt.sendAflQuarter(c.aflQuarter, c.aflQuarterStyle);
        break;
      case 'Cricket':
        _ramt.sendTeamName(c.cricketHomeName, 1, c.cricketTeamStyle);
        _ramt.sendTeamName(c.cricketAwayName, 3, c.cricketTeamStyle);
        _ramt.setCounter(1, c.cricketHomeRuns);
        _ramt.setCounter(2, c.cricketHomeWickets);
        _ramt.setCounter(3, c.cricketAwayRuns);
        _ramt.setCounter(4, c.cricketAwayWickets);
        _ramt.setCounter(5, c.cricketExtras);
        _ramt.setCounter(6, c.cricketOvers);
        break;
      case 'Basketball':
        _ramt.sendTeamName(c.homeName, 1, c.teamStyle);
        _ramt.sendTeamName(c.awayName, 3, c.teamStyle);
        _ramt.setCounter(1, c.homeScore);
        _ramt.setCounter(2, c.awayScore);
        _ramt.setCounter(3, c.homeTimeouts);
        _ramt.setCounter(4, c.awayTimeouts);
        _ramt.setCounter(5, c.homeFouls);
        _ramt.setCounter(6, c.awayFouls);
        break;
      default:
        _ramt.sendTeamName(c.homeName, 1, c.teamStyle);
        _ramt.sendTeamName(c.awayName, 3, c.teamStyle);
        _ramt.setCounter(1, c.homeScore);
        _ramt.setCounter(2, c.awayScore);
    }

    // Timer
    _sendTimerDisplay();
  }

  // ─── Advertisements ────────────────────────────────────────────────────────

  void saveAdvertisement(Advertisement ad, {int? editIndex}) {
    final ads = List<Advertisement>.from(_config.advertisements);
    if (editIndex != null && editIndex >= 0 && editIndex < ads.length) {
      ads[editIndex] = ad;
    } else {
      ads.add(ad);
    }
    _update(_config.copyWith(advertisements: ads));
  }

  void deleteAdvertisement(int index) {
    final ads = List<Advertisement>.from(_config.advertisements);
    if (index < 0 || index >= ads.length) return;
    final name = ads[index].name;
    ads.removeAt(index);
    final sel = Map<String, AdSelection>.from(_config.adSelections)..remove(name);
    _update(_config.copyWith(advertisements: ads, adSelections: sel));
  }

  void setAdSelection(String name, bool selected) {
    final sel = Map<String, AdSelection>.from(_config.adSelections);
    final existing = sel[name] ?? const AdSelection();
    sel[name] = existing.copyWith(selected: selected);
    _update(_config.copyWith(adSelections: sel));
  }

  void setAdDuration(String name, String duration) {
    final sel = Map<String, AdSelection>.from(_config.adSelections);
    final existing = sel[name] ?? const AdSelection();
    sel[name] = existing.copyWith(duration: duration);
    _update(_config.copyWith(adSelections: sel));
  }

  List<(Advertisement, int)> _buildPlaylist() {
    final result = <(Advertisement, int)>[];
    for (final ad in _config.advertisements) {
      final sel = _config.adSelections[ad.name];
      if (sel?.selected == true) {
        final ms = (int.tryParse(sel!.duration) ?? 4) * 1000;
        result.add((ad, ms));
      }
    }
    return result;
  }

  void startAdLoop() {
    final playlist = _buildPlaylist();
    if (playlist.isEmpty) return;
    _adLoopActive   = true;
    _adPlaylist     = playlist;
    _adLoopIdx      = 0;
    _adLoopJob?.cancel();
    _adLoopNext();
    notifyListeners();
  }

  void _adLoopNext() {
    if (!_adLoopActive || _adPlaylist.isEmpty) return;
    final (ad, durationMs) = _adPlaylist[_adLoopIdx];
    _playAd(ad);
    if (_adPlaylist.length == 1) {
      _adLoopJob = null;
      return;
    }
    _adLoopIdx = (_adLoopIdx + 1) % _adPlaylist.length;
    _adLoopJob = Timer(Duration(milliseconds: durationMs), _adLoopNext);
  }

  void stopAdLoop() {
    _adLoopActive = false;
    _adLoopJob?.cancel();
    _adLoopJob = null;
    notifyListeners();
  }

  void _playAd(Advertisement ad) {
    // Send each row to consecutive RAMT slots (same as Python app)
    for (int i = 0; i < ad.rows.length; i++) {
      final row = ad.rows[i];
      if (row.text.trim().isEmpty) continue;
      _ramt.sendAdRow(i + 1, row.color, row.size, row.hAlign, row.vAlign, row.text);
    }
  }

  // ─── Ad Preview ────────────────────────────────────────────────────────────

  /// Send an ad directly to the display for live editor preview.
  void previewAd(Advertisement ad) {
    _adPreviewActive = true;
    _playAd(ad);
    notifyListeners();
  }

  /// Stop the editor preview and restore the scoreboard.
  void stopAdPreview() {
    if (!_adPreviewActive) return;
    _adPreviewActive = false;
    notifyListeners();
    sendSportProgram();
    Timer(const Duration(milliseconds: 150), resendAll);
  }

  // ─── Return to scores ──────────────────────────────────────────────────────

  void returnToScores() {
    stopAdLoop();
    sendSportProgram();
    Timer(const Duration(milliseconds: 150), resendAll);
  }

  // ─── Back to home ──────────────────────────────────────────────────────────

  void backToHome() {
    pauseTimer();
    stopAdLoop();
    _ramt.sendProgram('0');
    Timer(const Duration(milliseconds: 120), _ramt.blankDisplay);
  }

  // ─── Reset to factory defaults ─────────────────────────────────────────────

  Future<void> resetToDefaults() async {
    pauseTimer();
    shotClockStop();
    stopAdLoop();
    _timerConfiguredFor = null;
    // Reset bypass mode to off
    _udp.bypassMode = false;
    _connStatus = ConnectionStatus.disconnected;
    await _cfg.clear();
    _config = const AppConfig();
    notifyListeners();
  }

  // ─── Dispose ───────────────────────────────────────────────────────────────

  @override
  void dispose() {
    _timerJob?.cancel();
    _shotClockJob?.cancel();
    _adLoopJob?.cancel();
    _reconnectTimer?.cancel();
    _udp.dispose();
    super.dispose();
  }
}
