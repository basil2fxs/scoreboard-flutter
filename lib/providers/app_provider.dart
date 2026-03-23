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
  'AFL'              : '1',
  'Soccer/ Universal': '2',
  'Cricket'          : '3',
  'Rugby'            : '4',
  'Hockey'           : '5',
  'Basketball'       : '6',
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
  String? _timerConfiguredFor;

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
  List<(Advertisement, int)> _adPlaylist = [];
  Timer? _adLoopJob;

  // ─── Laptop ad loop ────────────────────────────────────────────────────────
  List<(int, int)> _laptopAdPlaylist = []; // (adNumber, durationMs)
  int _laptopAdIdx = 0;

  // ─── Ad preview ────────────────────────────────────────────────────────────
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

  // ─── Laptop scoring mode ───────────────────────────────────────────────────

  bool get laptopScoring => _config.laptopScoring;

  void setLaptopScoring(bool v) {
    _timerConfiguredFor = null; // Reset so timer re-initialises on next sport entry
    _update(_config.copyWith(laptopScoring: v));
  }

  // ─── Counter channel mapping ───────────────────────────────────────────────

  /// Returns the hardware CNTS number for a given sport+field.
  /// Checks user overrides first, then mode-aware defaults.
  int counterFor(String sport, String field) {
    final key = '$sport/$field';
    if (_config.counterChannels.containsKey(key)) {
      return _config.counterChannels[key]!;
    }
    return _config.laptopScoring
        ? _laptopDefault(sport, field)
        : _normalDefault(sport, field);
  }

  static int _laptopDefault(String sport, String field) {
    const defaults = <String, Map<String, int>>{
      'AFL': {
        'homeGoals': 1, 'homePoints': 2, 'homeTotal': 3,
        'awayGoals': 4, 'awayPoints': 5, 'awayTotal': 6,
      },
      'Cricket': {
        'homeWickets': 1, 'homeRuns': 2,
        'awayWickets': 3, 'awayRuns': 4,
        'extras': 5, 'overs': 6,
      },
      'Basketball': {
        'homeTimeouts': 1, 'awayTimeouts': 2,
        'homeFouls': 3, 'awayFouls': 4,
        'homeScore': 5, 'awayScore': 6,
      },
    };
    return defaults[sport]?[field] ?? (field.startsWith('home') ? 1 : 2);
  }

  static int _normalDefault(String sport, String field) {
    const defaults = <String, Map<String, int>>{
      'AFL': {
        'homeGoals': 1, 'awayGoals': 2, 'homePoints': 3, 'awayPoints': 4,
        'homeTotal': 5, 'awayTotal': 6,
      },
      'Cricket': {
        'homeRuns': 1, 'homeWickets': 2,
        'awayRuns': 3, 'awayWickets': 4,
        'extras': 5, 'overs': 6,
      },
      'Basketball': {
        'homeScore': 1, 'awayScore': 2,
        'homeTimeouts': 3, 'awayTimeouts': 4,
        'homeFouls': 5, 'awayFouls': 6,
      },
    };
    return defaults[sport]?[field] ?? (field.startsWith('home') ? 1 : 2);
  }

  void setCounterChannel(String sport, String field, int channel) {
    final channels = Map<String, int>.from(_config.counterChannels);
    channels['$sport/$field'] = channel;
    _update(_config.copyWith(counterChannels: channels));
  }

  /// Clears all user-overridden counter channel mappings for [sport],
  /// reverting to mode-aware defaults.
  void clearCounterChannels(String sport) {
    final channels = Map<String, int>.from(_config.counterChannels);
    channels.removeWhere((key, _) => key.startsWith('$sport/'));
    _update(_config.copyWith(counterChannels: channels));
  }

  // ─── Laptop ad settings ────────────────────────────────────────────────────

  void setLaptopAdSetting(String key, String value) {
    final settings = Map<String, String>.from(_config.laptopAdSettings);
    settings[key] = value;
    _update(_config.copyWith(laptopAdSettings: settings));
  }

  bool getLaptopAdSelected(int n) =>
      _config.laptopAdSettings['Ad${n}_sel'] == 'true';

  String getLaptopAdDuration(int n) =>
      _config.laptopAdSettings['Ad${n}_dur'] ?? '10';

  // ─── Connection ────────────────────────────────────────────────────────────

  void _startAutoReconnect() {
    _reconnectTimer?.cancel();
    _reconnectTimer = Timer.periodic(const Duration(seconds: 3), (_) {
      _testConnectionBackground();
    });
  }

  Future<void> _testConnectionBackground() async {
    if (_connStatus != ConnectionStatus.disconnected) return;
    try {
      final ok = await _udp.testConnection();
      if (_connStatus == ConnectionStatus.bypass) return;
      if (ok) {
        _connStatus = ConnectionStatus.connected;
        notifyListeners();
      }
    } catch (_) {}
  }

  Future<void> testConnection() async {
    if (_connStatus == ConnectionStatus.bypass) return;
    _connStatus = ConnectionStatus.connecting;
    notifyListeners();
    final ok = await _udp.testConnection();
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

  /// In laptop mode always sends PRGC30. In normal mode sends the sport program.
  void sendSportProgram() {
    if (_config.laptopScoring) {
      _ramt.sendProgram('0');
      return;
    }
    final p = kSportPrograms[_config.currentSport];
    if (p != null) _ramt.sendProgram(p);
  }

  // ─── Timer channel setters ─────────────────────────────────────────────────

  void setTimerChannel(int channel) {
    _update(_config.copyWith(timerChannel: channel));
  }

  void setShotClockChannel(int channel) {
    _update(_config.copyWith(shotClockChannel: channel));
  }

  // ─── Timer ─────────────────────────────────────────────────────────────────

  static int defaultShotClockFor(String sport) {
    if (sport == 'Hockey') return 40;
    return 30;
  }

  void initTimerForSport(String sport) {
    if (_timerConfiguredFor == sport || _timerRunning) return;
    _timerConfiguredFor = sport;

    if (_config.laptopScoring) {
      _initLaptopTimerForSport(sport);
      return;
    }

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
      case 'Soccer/ Universal':
      case 'Rugby':
      default:
        _update(_config.copyWith(
          timerCountdown    : false,
          timerTargetSeconds: 0,
          timerSeconds      : 0,
        ));
    }
  }

  void _initLaptopTimerForSport(String sport) {
    switch (sport) {
      case 'AFL':
        _update(_config.copyWith(
          timerCountdown    : true,
          timerTargetSeconds: 25 * 60,
          timerSeconds      : 25 * 60,
          timerChannel      : 1,
        ));
        break;
      case 'Hockey':
        _update(_config.copyWith(
          timerCountdown    : true,
          timerTargetSeconds: 45 * 60,
          timerSeconds      : 45 * 60,
          timerChannel      : 1,
          shotClockSeconds  : 45,
          shotClockChannel  : 2,
        ));
        _shotClockSecondsLive = 45;
        break;
      case 'Basketball':
        _update(_config.copyWith(
          timerCountdown    : true,
          timerTargetSeconds: 12 * 60,
          timerSeconds      : 12 * 60,
          timerChannel      : 2,
          shotClockSeconds  : 30,
          shotClockChannel  : 1,
        ));
        _shotClockSecondsLive = 30;
        break;
      case 'Rugby':
        _update(_config.copyWith(
          timerCountdown    : true,
          timerTargetSeconds: 40 * 60,
          timerSeconds      : 40 * 60,
          timerChannel      : 1,
        ));
        break;
      case 'Soccer/ Universal':
        _update(_config.copyWith(
          timerCountdown    : false,
          timerTargetSeconds: 0,
          timerSeconds      : 0,
          timerChannel      : 1,
        ));
        break;
      case 'Cricket':
      default:
        break;
    }
  }

  void setTimerTime({required bool countdown, required int totalSeconds}) {
    pauseTimer();
    _update(_config.copyWith(
      timerCountdown    : countdown,
      timerTargetSeconds: countdown ? totalSeconds : 0,
      timerSeconds      : countdown ? totalSeconds : 0,
    ));
    if (_config.laptopScoring) {
      _ramt.sendHardwareTimerReset(_config.timerChannel);
    } else {
      _sendTimerDisplay();
    }
  }

  void setShotClockDefault(int seconds) {
    _shotClockSecondsLive = seconds;
    _update(_config.copyWith(shotClockSeconds: seconds));
    if (_shotClockVisible && !_config.laptopScoring) {
      _ramt.sendShotClock(_shotClockSecondsLive, _config.shotClockStyle);
    }
  }

  void startTimer() {
    if (_timerRunning) return;
    _timerRunning = true;
    if (_config.laptopScoring) {
      // 1-second delay before sending hardware start in laptop mode
      Timer(const Duration(seconds: 1),
          () => _ramt.sendHardwareTimerStart(_config.timerChannel));
    }
    _timerJob = Timer.periodic(const Duration(seconds: 1), (_) => _timerTick());
    notifyListeners();
  }

  void pauseTimer() {
    if (_timerRunning && _config.laptopScoring) {
      _ramt.sendHardwareTimerPause(_config.timerChannel);
    }
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
    if (_config.laptopScoring) {
      _ramt.sendHardwareTimerReset(_config.timerChannel);
    } else {
      _sendTimerDisplay();
    }
  }

  void _timerTick() {
    int s = _config.timerSeconds;
    if (_config.timerCountdown) {
      s = (s - 1).clamp(0, 9999);
      if (s == 0) pauseTimer();
    } else {
      s = s + 1;
    }
    _config = _config.copyWith(timerSeconds: s);
    if (!_config.laptopScoring) _sendTimerDisplay();
    notifyListeners();
  }

  void _sendTimerDisplay() {
    if (_config.laptopScoring) return;
    final leading = _config.currentSport == 'AFL'
        ? _config.timerOffsetAfl
        : _config.timerOffsetDefault;
    _ramt.sendTimer(_config.timerSeconds, _config.timerStyle, leading);
  }

  void updateTimerStyle(DisplayStyle style) {
    _update(_config.copyWith(timerStyle: style));
    if (!_config.laptopScoring) _sendTimerDisplay();
  }

  void updateTimerOffset(bool isAfl, int value) {
    _update(isAfl
      ? _config.copyWith(timerOffsetAfl: value)
      : _config.copyWith(timerOffsetDefault: value));
    if (!_config.laptopScoring) _sendTimerDisplay();
  }

  String get timerDisplay {
    final s = _config.timerSeconds;
    return '${(s ~/ 60).toString().padLeft(2,'0')}:${(s % 60).toString().padLeft(2,'0')}';
  }

  // ─── Shot Clock ────────────────────────────────────────────────────────────

  void shotClockStart() {
    if (_shotClockRunning) return;
    _shotClockVisible = true;
    _shotClockRunning = true;
    if (_config.laptopScoring) {
      // 1-second delay before sending hardware start in laptop mode
      Timer(const Duration(seconds: 1),
          () => _ramt.sendHardwareTimerStart(_config.shotClockChannel));
    } else {
      _ramt.sendShotClock(_shotClockSecondsLive, _config.shotClockStyle);
    }
    _shotClockJob = Timer.periodic(const Duration(seconds: 1), (_) => _shotClockTick());
    notifyListeners();
  }

  void shotClockStop() {
    _shotClockRunning = false;
    _shotClockVisible = false;
    _shotClockJob?.cancel();
    _shotClockJob = null;
    _shotClockSecondsLive = _config.shotClockSeconds;
    if (_config.laptopScoring) {
      _ramt.sendHardwareTimerPause(_config.shotClockChannel);
    } else {
      _ramt.clearRamt8(_config.shotClockStyle);
    }
    notifyListeners();
  }

  void shotClockReset() {
    _shotClockJob?.cancel();
    _shotClockJob = null;
    _shotClockSecondsLive = _config.shotClockSeconds;
    if (_config.laptopScoring) {
      // Laptop mode: reset immediately, then start after 1-second delay
      _ramt.sendHardwareTimerReset(_config.shotClockChannel);
      Timer(const Duration(seconds: 1),
          () => _ramt.sendHardwareTimerStart(_config.shotClockChannel));
      _shotClockRunning = true;
      _shotClockVisible = true;
      _shotClockJob = Timer.periodic(const Duration(seconds: 1), (_) => _shotClockTick());
    } else {
      _ramt.sendShotClock(_shotClockSecondsLive, _config.shotClockStyle);
      if (_shotClockRunning) {
        _shotClockJob = Timer.periodic(const Duration(seconds: 1), (_) => _shotClockTick());
      }
    }
    notifyListeners();
  }

  void _shotClockTick() {
    _shotClockSecondsLive = (_shotClockSecondsLive - 1).clamp(0, 999);
    if (!_config.laptopScoring) {
      _ramt.sendShotClock(_shotClockSecondsLive, _config.shotClockStyle);
    }
    if (_shotClockSecondsLive == 0) {
      _shotClockRunning = false;
      _shotClockJob?.cancel();
      _shotClockJob = null;
    }
    notifyListeners();
  }

  void updateShotClockStyle(DisplayStyle style) {
    _update(_config.copyWith(shotClockStyle: style));
    if (_shotClockVisible && !_config.laptopScoring) {
      _ramt.sendShotClock(_shotClockSecondsLive, style);
    }
  }

  // ─── AFL Quarter ───────────────────────────────────────────────────────────

  void setAflQuarter(int q) {
    _update(_config.copyWith(aflQuarter: q));
    if (!_config.laptopScoring) {
      _ramt.sendAflQuarter(q, _config.aflQuarterStyle);
    }
  }

  void updateAflQuarterStyle(DisplayStyle style) {
    _update(_config.copyWith(aflQuarterStyle: style));
    if (!_config.laptopScoring) {
      _ramt.sendAflQuarter(_config.aflQuarter, style);
    }
  }

  // ─── Team Names (generic sports) ──────────────────────────────────────────

  void setHomeName(String name) {
    _update(_config.copyWith(homeName: name));
    if (!_config.laptopScoring) {
      _ramt.sendTeamName(name, 1, _config.teamStyle);
    }
  }

  void setAwayName(String name) {
    _update(_config.copyWith(awayName: name));
    if (!_config.laptopScoring) {
      _ramt.sendTeamName(name, 3, _config.teamStyle);
    }
  }

  void updateTeamStyle(DisplayStyle style) {
    _update(_config.copyWith(teamStyle: style));
    if (!_config.laptopScoring) {
      _ramt.sendTeamName(_config.homeName, 1, style);
      _ramt.sendTeamName(_config.awayName, 3, style);
    }
  }

  // ─── AFL team names ────────────────────────────────────────────────────────

  void setAflHomeName(String name) {
    _update(_config.copyWith(aflHomeName: name, homeName: name));
    if (!_config.laptopScoring) {
      _ramt.sendTeamName(name, 1, _config.aflTeamStyle);
    }
  }

  void setAflAwayName(String name) {
    _update(_config.copyWith(aflAwayName: name, awayName: name));
    if (!_config.laptopScoring) {
      _ramt.sendTeamName(name, 3, _config.aflTeamStyle);
    }
  }

  void updateAflTeamStyle(DisplayStyle style) {
    _update(_config.copyWith(aflTeamStyle: style));
    if (!_config.laptopScoring) {
      _ramt.sendTeamName(_config.aflHomeName, 1, style);
      _ramt.sendTeamName(_config.aflAwayName, 3, style);
    }
  }

  // ─── Cricket team names ────────────────────────────────────────────────────

  void setCricketHomeName(String name) {
    _update(_config.copyWith(cricketHomeName: name, homeName: name));
    if (!_config.laptopScoring) {
      _ramt.sendTeamName(name, 1, _config.cricketTeamStyle);
    }
  }

  void setCricketAwayName(String name) {
    _update(_config.copyWith(cricketAwayName: name, awayName: name));
    if (!_config.laptopScoring) {
      _ramt.sendTeamName(name, 3, _config.cricketTeamStyle);
    }
  }

  void updateCricketTeamStyle(DisplayStyle style) {
    _update(_config.copyWith(cricketTeamStyle: style));
    if (!_config.laptopScoring) {
      _ramt.sendTeamName(_config.cricketHomeName, 1, style);
      _ramt.sendTeamName(_config.cricketAwayName, 3, style);
    }
  }

  // ─── Simple scores (Soccer/Universal, Rugby, Hockey, Basketball) ───────────

  void adjustScore(String team, int delta) {
    final sport = _config.currentSport ?? 'Soccer/ Universal';
    if (team == 'home') {
      final v = (_config.homeScore + delta).clamp(0, 999);
      _update(_config.copyWith(homeScore: v));
      _ramt.setCounter(counterFor(sport, 'homeScore'), v);
    } else {
      final v = (_config.awayScore + delta).clamp(0, 999);
      _update(_config.copyWith(awayScore: v));
      _ramt.setCounter(counterFor(sport, 'awayScore'), v);
    }
  }

  void setScore(String team, int value) {
    final sport = _config.currentSport ?? 'Soccer/ Universal';
    final v = value.clamp(0, 999);
    if (team == 'home') {
      _update(_config.copyWith(homeScore: v));
      _ramt.setCounter(counterFor(sport, 'homeScore'), v);
    } else {
      _update(_config.copyWith(awayScore: v));
      _ramt.setCounter(counterFor(sport, 'awayScore'), v);
    }
  }

  void resetScores() {
    final sport = _config.currentSport ?? 'Soccer/ Universal';
    _update(_config.copyWith(homeScore: 0, awayScore: 0));
    _ramt.setCounter(counterFor(sport, 'homeScore'), 0);
    _ramt.setCounter(counterFor(sport, 'awayScore'), 0);
  }

  // ─── AFL scores ────────────────────────────────────────────────────────────

  void adjustAflGoals(String team, int delta) {
    if (team == 'home') {
      final v = (_config.aflHomeGoals + delta).clamp(0, 999);
      _update(_config.copyWith(aflHomeGoals: v));
      final n = counterFor('AFL', 'homeGoals');
      delta > 0 ? _ramt.addCounter(n, delta) : _ramt.subtractCounter(n, -delta);
    } else {
      final v = (_config.aflAwayGoals + delta).clamp(0, 999);
      _update(_config.copyWith(aflAwayGoals: v));
      final n = counterFor('AFL', 'awayGoals');
      delta > 0 ? _ramt.addCounter(n, delta) : _ramt.subtractCounter(n, -delta);
    }
    _updateAflTotals();
  }

  void adjustAflPoints(String team, int delta) {
    if (team == 'home') {
      final v = (_config.aflHomePoints + delta).clamp(0, 999);
      _update(_config.copyWith(aflHomePoints: v));
      final n = counterFor('AFL', 'homePoints');
      delta > 0 ? _ramt.addCounter(n, delta) : _ramt.subtractCounter(n, -delta);
    } else {
      final v = (_config.aflAwayPoints + delta).clamp(0, 999);
      _update(_config.copyWith(aflAwayPoints: v));
      final n = counterFor('AFL', 'awayPoints');
      delta > 0 ? _ramt.addCounter(n, delta) : _ramt.subtractCounter(n, -delta);
    }
    _updateAflTotals();
  }

  void setAflScore(String team, String type, int value) {
    final v = value.clamp(0, 999);
    if (team == 'home') {
      if (type == 'goals') {
        _update(_config.copyWith(aflHomeGoals: v));
        _ramt.setCounter(counterFor('AFL', 'homeGoals'), v);
      } else {
        _update(_config.copyWith(aflHomePoints: v));
        _ramt.setCounter(counterFor('AFL', 'homePoints'), v);
      }
    } else {
      if (type == 'goals') {
        _update(_config.copyWith(aflAwayGoals: v));
        _ramt.setCounter(counterFor('AFL', 'awayGoals'), v);
      } else {
        _update(_config.copyWith(aflAwayPoints: v));
        _ramt.setCounter(counterFor('AFL', 'awayPoints'), v);
      }
    }
    _updateAflTotals();
  }

  void resetAflScores(String team) {
    if (team == 'home') {
      _update(_config.copyWith(aflHomeGoals: 0, aflHomePoints: 0));
      _ramt.setCounter(counterFor('AFL', 'homeGoals'), 0);
      _ramt.setCounter(counterFor('AFL', 'homePoints'), 0);
    } else {
      _update(_config.copyWith(aflAwayGoals: 0, aflAwayPoints: 0));
      _ramt.setCounter(counterFor('AFL', 'awayGoals'), 0);
      _ramt.setCounter(counterFor('AFL', 'awayPoints'), 0);
    }
    _updateAflTotals();
  }

  void _updateAflTotals() {
    final ht = _config.aflHomeGoals * 6 + _config.aflHomePoints;
    final at = _config.aflAwayGoals * 6 + _config.aflAwayPoints;
    _ramt.setCounter(counterFor('AFL', 'homeTotal'), ht);
    _ramt.setCounter(counterFor('AFL', 'awayTotal'), at);
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
        updated = c.copyWith(cricketHomeRuns: newVal);
        counterN = counterFor('Cricket', 'homeRuns'); break;
      case 'homeWickets':
        newVal = (c.cricketHomeWickets + delta).clamp(0, 10);
        updated = c.copyWith(cricketHomeWickets: newVal);
        counterN = counterFor('Cricket', 'homeWickets'); break;
      case 'awayRuns':
        newVal = (c.cricketAwayRuns + delta).clamp(0, 9999);
        updated = c.copyWith(cricketAwayRuns: newVal);
        counterN = counterFor('Cricket', 'awayRuns'); break;
      case 'awayWickets':
        newVal = (c.cricketAwayWickets + delta).clamp(0, 10);
        updated = c.copyWith(cricketAwayWickets: newVal);
        counterN = counterFor('Cricket', 'awayWickets'); break;
      case 'extras':
        newVal = (c.cricketExtras + delta).clamp(0, 999);
        updated = c.copyWith(cricketExtras: newVal);
        counterN = counterFor('Cricket', 'extras'); break;
      case 'overs':
        newVal = (c.cricketOvers + delta).clamp(0, 999);
        updated = c.copyWith(cricketOvers: newVal);
        counterN = counterFor('Cricket', 'overs'); break;
      default: return;
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
      _ramt.setCounter(counterFor('Cricket', 'homeRuns'), 0);
      _ramt.setCounter(counterFor('Cricket', 'homeWickets'), 0);
    } else {
      _update(_config.copyWith(cricketAwayRuns: 0, cricketAwayWickets: 0));
      _ramt.setCounter(counterFor('Cricket', 'awayRuns'), 0);
      _ramt.setCounter(counterFor('Cricket', 'awayWickets'), 0);
    }
  }

  // ─── Basketball extras ─────────────────────────────────────────────────────

  void adjustTimeout(String team, int delta) {
    if (team == 'home') {
      final v = (_config.homeTimeouts + delta).clamp(0, 99);
      _update(_config.copyWith(homeTimeouts: v));
      _ramt.setCounter(counterFor('Basketball', 'homeTimeouts'), v);
    } else {
      final v = (_config.awayTimeouts + delta).clamp(0, 99);
      _update(_config.copyWith(awayTimeouts: v));
      _ramt.setCounter(counterFor('Basketball', 'awayTimeouts'), v);
    }
  }

  void adjustFoul(String team, int delta) {
    if (team == 'home') {
      final v = (_config.homeFouls + delta).clamp(0, 99);
      _update(_config.copyWith(homeFouls: v));
      _ramt.setCounter(counterFor('Basketball', 'homeFouls'), v);
    } else {
      final v = (_config.awayFouls + delta).clamp(0, 99);
      _update(_config.copyWith(awayFouls: v));
      _ramt.setCounter(counterFor('Basketball', 'awayFouls'), v);
    }
  }

  void resetTimeouts() {
    _update(_config.copyWith(homeTimeouts: 0, awayTimeouts: 0));
    _ramt.setCounter(counterFor('Basketball', 'homeTimeouts'), 0);
    _ramt.setCounter(counterFor('Basketball', 'awayTimeouts'), 0);
  }

  void resetFouls() {
    _update(_config.copyWith(homeFouls: 0, awayFouls: 0));
    _ramt.setCounter(counterFor('Basketball', 'homeFouls'), 0);
    _ramt.setCounter(counterFor('Basketball', 'awayFouls'), 0);
  }

  void resetCricketMatchInfo() {
    _update(_config.copyWith(cricketExtras: 0, cricketOvers: 0));
    _ramt.setCounter(counterFor('Cricket', 'extras'), 0);
    _ramt.setCounter(counterFor('Cricket', 'overs'), 0);
  }

  // ─── Resend all display data ────────────────────────────────────────────────

  void resendAll() {
    final c = _config;
    final sport = c.currentSport ?? '';

    if (_config.laptopScoring) {
      // In laptop mode, don't send PRGC30 if ads are currently playing
      if (!_adLoopActive) sendSportProgram();
      _resendLaptopCounters(sport, c);
      return;
    }

    // Normal mode: don't switch back to sport program if ads are playing
    if (!_adLoopActive) sendSportProgram();

    // Normal mode: team names + counters + timer
    switch (sport) {
      case 'AFL':
        _ramt.sendTeamName(c.aflHomeName, 1, c.aflTeamStyle);
        _ramt.sendTeamName(c.aflAwayName, 3, c.aflTeamStyle);
        _ramt.setCounter(counterFor(sport, 'homeGoals'),  c.aflHomeGoals);
        _ramt.setCounter(counterFor(sport, 'awayGoals'),  c.aflAwayGoals);
        _ramt.setCounter(counterFor(sport, 'homePoints'), c.aflHomePoints);
        _ramt.setCounter(counterFor(sport, 'awayPoints'), c.aflAwayPoints);
        _ramt.setCounter(counterFor(sport, 'homeTotal'),  aflHomeTotal);
        _ramt.setCounter(counterFor(sport, 'awayTotal'),  aflAwayTotal);
        _ramt.sendAflQuarter(c.aflQuarter, c.aflQuarterStyle);
        break;
      case 'Cricket':
        _ramt.sendTeamName(c.cricketHomeName, 1, c.cricketTeamStyle);
        _ramt.sendTeamName(c.cricketAwayName, 3, c.cricketTeamStyle);
        _ramt.setCounter(counterFor(sport, 'homeRuns'),    c.cricketHomeRuns);
        _ramt.setCounter(counterFor(sport, 'homeWickets'), c.cricketHomeWickets);
        _ramt.setCounter(counterFor(sport, 'awayRuns'),    c.cricketAwayRuns);
        _ramt.setCounter(counterFor(sport, 'awayWickets'), c.cricketAwayWickets);
        _ramt.setCounter(counterFor(sport, 'extras'),      c.cricketExtras);
        _ramt.setCounter(counterFor(sport, 'overs'),       c.cricketOvers);
        break;
      case 'Basketball':
        _ramt.sendTeamName(c.homeName, 1, c.teamStyle);
        _ramt.sendTeamName(c.awayName, 3, c.teamStyle);
        _ramt.setCounter(counterFor(sport, 'homeScore'),    c.homeScore);
        _ramt.setCounter(counterFor(sport, 'awayScore'),    c.awayScore);
        _ramt.setCounter(counterFor(sport, 'homeTimeouts'), c.homeTimeouts);
        _ramt.setCounter(counterFor(sport, 'awayTimeouts'), c.awayTimeouts);
        _ramt.setCounter(counterFor(sport, 'homeFouls'),    c.homeFouls);
        _ramt.setCounter(counterFor(sport, 'awayFouls'),    c.awayFouls);
        break;
      default:
        _ramt.sendTeamName(c.homeName, 1, c.teamStyle);
        _ramt.sendTeamName(c.awayName, 3, c.teamStyle);
        _ramt.setCounter(counterFor(sport, 'homeScore'), c.homeScore);
        _ramt.setCounter(counterFor(sport, 'awayScore'), c.awayScore);
    }
    _sendTimerDisplay();
  }

  void _resendLaptopCounters(String sport, AppConfig c) {
    switch (sport) {
      case 'AFL':
        _ramt.setCounter(counterFor(sport, 'homeGoals'),  c.aflHomeGoals);
        _ramt.setCounter(counterFor(sport, 'homePoints'), c.aflHomePoints);
        _ramt.setCounter(counterFor(sport, 'homeTotal'),  aflHomeTotal);
        _ramt.setCounter(counterFor(sport, 'awayGoals'),  c.aflAwayGoals);
        _ramt.setCounter(counterFor(sport, 'awayPoints'), c.aflAwayPoints);
        _ramt.setCounter(counterFor(sport, 'awayTotal'),  aflAwayTotal);
        break;
      case 'Cricket':
        _ramt.setCounter(counterFor(sport, 'homeWickets'), c.cricketHomeWickets);
        _ramt.setCounter(counterFor(sport, 'homeRuns'),    c.cricketHomeRuns);
        _ramt.setCounter(counterFor(sport, 'awayWickets'), c.cricketAwayWickets);
        _ramt.setCounter(counterFor(sport, 'awayRuns'),    c.cricketAwayRuns);
        _ramt.setCounter(counterFor(sport, 'extras'),      c.cricketExtras);
        _ramt.setCounter(counterFor(sport, 'overs'),       c.cricketOvers);
        break;
      case 'Basketball':
        _ramt.setCounter(counterFor(sport, 'homeTimeouts'), c.homeTimeouts);
        _ramt.setCounter(counterFor(sport, 'awayTimeouts'), c.awayTimeouts);
        _ramt.setCounter(counterFor(sport, 'homeFouls'),    c.homeFouls);
        _ramt.setCounter(counterFor(sport, 'awayFouls'),    c.awayFouls);
        _ramt.setCounter(counterFor(sport, 'homeScore'),    c.homeScore);
        _ramt.setCounter(counterFor(sport, 'awayScore'),    c.awayScore);
        break;
      default:
        _ramt.setCounter(counterFor(sport, 'homeScore'), c.homeScore);
        _ramt.setCounter(counterFor(sport, 'awayScore'), c.awayScore);
    }
  }

  // ─── Advertisements (normal mode) ──────────────────────────────────────────

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
    if (_config.laptopScoring) {
      _startLaptopAdLoop();
      return;
    }
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
    if (_adPreviewActive) return; // Don't send during preview
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
    // Select correct TF-F6 program based on number of rows and border.
    // From Python: prog_base = {1:7, 2:9, 3:11, 4:13}[numRows], prog += border ? 1 : 0
    final n = (ad.numRows > 0 ? ad.numRows : ad.rows.length).clamp(1, 4);
    final progBase = const {1: 7, 2: 9, 3: 11, 4: 13}[n] ?? 7;
    final prog = progBase + (ad.border ? 1 : 0);
    _ramt.sendProgram(prog.toString());
    // Send RAMT slot for every row slot (send space for empty rows to clear them)
    for (int i = 0; i < n; i++) {
      if (i < ad.rows.length) {
        final row = ad.rows[i];
        _ramt.sendAdRow(i + 1, row.color, row.size, row.hAlign, row.vAlign,
            row.text.isEmpty ? ' ' : row.text);
      } else {
        _ramt.sendAdRow(i + 1, '7', '2', '1', '2', ' ');
      }
    }
  }

  // ─── Laptop ad loop ────────────────────────────────────────────────────────

  List<(int, int)> _buildLaptopPlaylist() {
    final result = <(int, int)>[];
    for (int i = 1; i <= 5; i++) {
      final sel = _config.laptopAdSettings['Ad${i}_sel'] ?? 'false';
      if (sel == 'true') {
        final dur = (int.tryParse(_config.laptopAdSettings['Ad${i}_dur'] ?? '10') ?? 10) * 1000;
        result.add((i, dur));
      }
    }
    return result;
  }

  void _startLaptopAdLoop() {
    final playlist = _buildLaptopPlaylist();
    if (playlist.isEmpty) return;
    _adLoopActive     = true;
    _laptopAdPlaylist = playlist;
    _laptopAdIdx      = 0;
    _adLoopJob?.cancel();
    _laptopAdLoopNext();
    notifyListeners();
  }

  void _laptopAdLoopNext() {
    if (!_adLoopActive || _laptopAdPlaylist.isEmpty) return;
    if (_adPreviewActive) return; // Don't send during preview
    final (adNum, durationMs) = _laptopAdPlaylist[_laptopAdIdx];
    _ramt.sendProgram(adNum.toString()); // e.g. PRGC31, PRGC32, ...
    if (_laptopAdPlaylist.length == 1) {
      _adLoopJob = null; // Single ad stays permanently
      return;
    }
    _laptopAdIdx = (_laptopAdIdx + 1) % _laptopAdPlaylist.length;
    _adLoopJob = Timer(Duration(milliseconds: durationMs), _laptopAdLoopNext);
  }

  // ─── Ad Preview ────────────────────────────────────────────────────────────

  void previewAd(Advertisement ad) {
    // Pause any running ad loop timer while previewing
    _adLoopJob?.cancel();
    _adLoopJob = null;
    _adPreviewActive = true;
    _playAd(ad);
    notifyListeners();
  }

  void stopAdPreview() {
    if (!_adPreviewActive) return;
    _adPreviewActive = false;
    notifyListeners();
    if (_adLoopActive) {
      // Resume from current loop position
      if (_config.laptopScoring) {
        _laptopAdLoopNext();
      } else {
        _adLoopNext();
      }
    } else {
      sendSportProgram();
      Timer(const Duration(milliseconds: 150), resendAll);
    }
  }

  // ─── Return to scores ──────────────────────────────────────────────────────

  void returnToScores() {
    stopAdLoop();
    sendSportProgram(); // PRGC30 in laptop mode, sport prog in normal mode
    if (!_config.laptopScoring) {
      Timer(const Duration(milliseconds: 150), resendAll);
    }
  }

  // ─── Back to home ──────────────────────────────────────────────────────────

  void backToHome() {
    pauseTimer();
    stopAdLoop();
    _ramt.sendProgram('0');
    if (!_config.laptopScoring) {
      Timer(const Duration(milliseconds: 120), _ramt.blankDisplay);
    }
  }

  // ─── Reset to factory defaults ─────────────────────────────────────────────

  Future<void> resetToDefaults() async {
    pauseTimer();
    shotClockStop();
    stopAdLoop();
    _timerConfiguredFor = null;
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
