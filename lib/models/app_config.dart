import 'advertisement.dart';

/// DisplayStyle — shared by team names, timer, shot clock, quarter.
class DisplayStyle {
  final String color;
  final String size;
  final String hAlign;
  final String vAlign;

  const DisplayStyle({
    this.color  = '7',
    this.size   = '2',
    this.hAlign = '1',
    this.vAlign = '2',
  });

  factory DisplayStyle.fromJson(Map<String, dynamic> j) => DisplayStyle(
    color : j['color']   as String? ?? '7',
    size  : j['size']    as String? ?? '2',
    hAlign: j['h_align'] as String? ?? '1',
    vAlign: j['v_align'] as String? ?? '2',
  );

  Map<String, dynamic> toJson() => {
    'color'  : color,
    'size'   : size,
    'h_align': hAlign,
    'v_align': vAlign,
  };

  DisplayStyle copyWith({String? color, String? size, String? hAlign, String? vAlign}) =>
      DisplayStyle(
        color : color  ?? this.color,
        size  : size   ?? this.size,
        hAlign: hAlign ?? this.hAlign,
        vAlign: vAlign ?? this.vAlign,
      );

  // vAlign: '3' = Top, '1' = Mid, '2' = Bottom on TF-F6.
  static const teamDefault    = DisplayStyle(color: '1', size: '2', hAlign: '3', vAlign: '3');
  // Timers always default to Top alignment; shot clock uses Large size by default.
  static const timerDefault   = DisplayStyle(color: '7', size: '2', hAlign: '3', vAlign: '3');
  static const shotDefault    = DisplayStyle(color: '7', size: '1', hAlign: '3', vAlign: '3');
  static const quarterDefault = DisplayStyle(color: '7', size: '2', hAlign: '3', vAlign: '2');
}

/// Full serialisable app config — written to device storage on every change.
class AppConfig {
  // ── Display setup ──────────────────────────────────────────────────────────
  final int? displayWidth;
  final int? displayHeight;

  // ── Sport ──────────────────────────────────────────────────────────────────
  final String? currentSport;

  // ── Simple scores ─────────────────────────────────────────────────────────
  final int homeScore;
  final int awayScore;
  final String homeName;
  final String awayName;

  // ── Team name styles ──────────────────────────────────────────────────────
  final DisplayStyle teamStyle;         // Soccer/Rugby/Hockey/Basketball
  final DisplayStyle aflTeamStyle;
  final DisplayStyle cricketTeamStyle;

  // ── Timer ─────────────────────────────────────────────────────────────────
  final int timerSeconds;
  final bool timerCountdown;
  final int timerTargetSeconds;
  final DisplayStyle timerStyle;
  final int timerOffsetAfl;
  final int timerOffsetDefault;
  final int timerChannel;        // Hardware timer channel (1 or 2) for laptop mode

  // ── Shot clock ────────────────────────────────────────────────────────────
  final int shotClockSeconds;
  final DisplayStyle shotClockStyle;
  final int shotClockChannel;    // Hardware shot clock timer channel (1 or 2) for laptop mode

  // ── AFL ───────────────────────────────────────────────────────────────────
  final String aflHomeName;
  final String aflAwayName;
  final int aflHomeGoals;
  final int aflHomePoints;
  final int aflAwayGoals;
  final int aflAwayPoints;
  final int aflQuarter;
  final DisplayStyle aflQuarterStyle;

  // ── Cricket ───────────────────────────────────────────────────────────────
  final String cricketHomeName;
  final String cricketAwayName;
  final int cricketHomeRuns;
  final int cricketHomeWickets;
  final int cricketAwayRuns;
  final int cricketAwayWickets;
  final int cricketExtras;
  final int cricketOvers;
  final int cricketBalls;

  // ── Basketball extras ─────────────────────────────────────────────────────
  final int homeTimeouts;
  final int awayTimeouts;
  final int homeFouls;
  final int awayFouls;

  // ── Display type ──────────────────────────────────────────────────────────
  final bool singleColour;
  final bool ultraWide;

  // ── Laptop mode ───────────────────────────────────────────────────────────
  final bool laptopScoring;

  // ── UDP timing ────────────────────────────────────────────────────────────
  /// Milliseconds between each queued UDP command. Default 120.
  final int udpCommandDelayMs;
  /// Milliseconds to wait before re-sending real data after zeroing on boot.
  final int udpInitFlushDelayMs;

  // ── Remapping mode ────────────────────────────────────────────────────────
  final bool remappingMode;

  // ── RAMT slot remapping ───────────────────────────────────────────────────
  /// The 2 RAMT slots used by the home team name (any 2 slots from 1-8).
  final List<int> ramtHomeSlots;
  /// The 2 RAMT slots used by the away team name (any 2 slots from 1-8).
  final List<int> ramtAwaySlots;
  /// The 3 RAMT slots used by the timer (any 3 slots from 1-8).
  final List<int> ramtTimerSlots;
  /// RAMT slot for shot clock / AFL quarter (single slot).
  final int ramtShotClockSlot;

  // ── Counter channel remapping (sport/field → CNT number) ─────────────────
  // e.g. 'Basketball/homeScore' → 5
  final Map<String, int> counterChannels;

  // ── Advertisements ────────────────────────────────────────────────────────
  final List<Advertisement> advertisements;
  final Map<String, AdSelection> adSelections;

  // ── Laptop mode fixed ad selections (Ad1–Ad5) ─────────────────────────────
  // 'Ad1' → true/false (selected), 'Ad1_dur' → '10' (seconds)
  final Map<String, String> laptopAdSettings;

  // ── Laptop page mapping ────────────────────────────────────────────────────
  /// Maps sport name → scoreboard page number (null = don't send PRGC).
  final Map<String, int?> laptopSportPages;
  /// Maps 'Ad1'–'Ad5' → scoreboard page number (null = don't send PRGC).
  final Map<String, int?> laptopAdPages;

  // ── Inactivity tracking ───────────────────────────────────────────────────
  /// Milliseconds since epoch of last app activity. Used for 12-hour
  /// inactivity detection — scores reset to 0 if exceeded.
  final int lastActiveMs;

  const AppConfig({
    this.displayWidth,
    this.displayHeight,
    this.currentSport,
    this.homeScore            = 0,
    this.awayScore            = 0,
    this.homeName             = 'HOME',
    this.awayName             = 'AWAY',
    this.teamStyle            = DisplayStyle.teamDefault,
    this.aflTeamStyle         = DisplayStyle.teamDefault,
    this.cricketTeamStyle     = DisplayStyle.teamDefault,
    this.timerSeconds         = 0,
    this.timerCountdown       = false,
    this.timerTargetSeconds   = 0,
    this.timerStyle           = DisplayStyle.timerDefault,
    this.timerOffsetAfl       = 1,
    this.timerOffsetDefault   = 0,
    this.timerChannel         = 1,
    this.shotClockSeconds     = 30,
    this.shotClockStyle       = DisplayStyle.shotDefault,
    this.shotClockChannel     = 2,
    this.aflHomeName          = 'HOME',
    this.aflAwayName          = 'AWAY',
    this.aflHomeGoals         = 0,
    this.aflHomePoints        = 0,
    this.aflAwayGoals         = 0,
    this.aflAwayPoints        = 0,
    this.aflQuarter           = 1,
    this.aflQuarterStyle      = DisplayStyle.quarterDefault,
    this.cricketHomeName      = 'HOME',
    this.cricketAwayName      = 'AWAY',
    this.cricketHomeRuns      = 0,
    this.cricketHomeWickets   = 0,
    this.cricketAwayRuns      = 0,
    this.cricketAwayWickets   = 0,
    this.cricketExtras        = 0,
    this.cricketOvers         = 0,
    this.cricketBalls         = 0,
    this.homeTimeouts         = 0,
    this.awayTimeouts         = 0,
    this.homeFouls            = 0,
    this.awayFouls            = 0,
    this.singleColour         = false,
    this.ultraWide            = false,
    this.laptopScoring        = false,
    this.udpCommandDelayMs    = 120,
    this.udpInitFlushDelayMs  = 500,
    this.remappingMode        = false,
    this.ramtHomeSlots        = const [1, 2],
    this.ramtAwaySlots        = const [3, 4],
    this.ramtTimerSlots       = const [5, 6, 7],
    this.ramtShotClockSlot    = 8,
    this.counterChannels      = const {},
    this.advertisements       = const [],
    this.adSelections         = const {},
    this.laptopAdSettings     = const {'Ad1_sel': 'true', 'Ad1_dur': '4',
                                       'Ad2_dur': '4', 'Ad3_dur': '4',
                                       'Ad4_dur': '4', 'Ad5_dur': '4'},
    this.laptopSportPages     = const {
      'AFL': 0, 'Soccer': 0, 'Cricket': 0,
      'Rugby': 0, 'Hockey': 0, 'Basketball': 0,
    },
    this.laptopAdPages        = const {
      'Ad1': 1, 'Ad2': 2, 'Ad3': 3, 'Ad4': 4, 'Ad5': 5,
    },
    this.lastActiveMs         = 0,
  });

  bool get isDisplayConfigured =>
      displayWidth != null && displayHeight != null;

  /// Returns a copy with all live game scores / counters zeroed.
  /// Preserves names, styles, settings, ads, and all other config.
  AppConfig resetScores() => copyWith(
    homeScore         : 0,
    awayScore         : 0,
    timerSeconds      : 0,
    shotClockSeconds  : 30,
    aflHomeGoals      : 0,
    aflHomePoints     : 0,
    aflAwayGoals      : 0,
    aflAwayPoints     : 0,
    aflQuarter        : 1,
    cricketHomeRuns   : 0,
    cricketHomeWickets: 0,
    cricketAwayRuns   : 0,
    cricketAwayWickets: 0,
    cricketExtras     : 0,
    cricketOvers      : 0,
    cricketBalls      : 0,
    homeTimeouts      : 0,
    awayTimeouts      : 0,
    homeFouls         : 0,
    awayFouls         : 0,
  );

  // ─── Serialisation ────────────────────────────────────────────────────────
  factory AppConfig.fromJson(Map<String, dynamic> j) {
    DisplayStyle _style(String key, DisplayStyle def) {
      final raw = j[key];
      if (raw is Map<String, dynamic>) return DisplayStyle.fromJson(raw);
      return def;
    }

    List<int> _slots(String key, List<int> def, {String? legacyStartKey, int legacySpan = 1}) {
      final raw = j[key];
      if (raw is List && raw.isNotEmpty) return raw.map((e) => e as int).toList();
      // Backwards compatibility: read old ramt_*_start integer and expand to list
      if (legacyStartKey != null) {
        final start = j[legacyStartKey] as int?;
        if (start != null) return List.generate(legacySpan, (i) => start + i);
      }
      return def;
    }

    return AppConfig(
      displayWidth      : j['display_width']         as int?,
      displayHeight     : j['display_height']        as int?,
      currentSport      : j['sport']                 as String?,
      homeScore         : j['home_score']            as int? ?? 0,
      awayScore         : j['away_score']            as int? ?? 0,
      homeName          : j['home_name']             as String? ?? 'HOME',
      awayName          : j['away_name']             as String? ?? 'AWAY',
      teamStyle         : _style('team_style',         DisplayStyle.teamDefault),
      aflTeamStyle      : _style('afl_team_style',     DisplayStyle.teamDefault),
      cricketTeamStyle  : _style('cricket_team_style', DisplayStyle.teamDefault),
      timerSeconds      : j['timer_seconds']         as int? ?? 0,
      timerCountdown    : j['timer_countdown']       as bool? ?? false,
      timerTargetSeconds: j['timer_target_seconds']  as int? ?? 0,
      timerStyle        : _style('timer_style',        DisplayStyle.timerDefault),
      timerOffsetAfl    : j['timer_offset_afl']      as int? ?? 1,
      timerOffsetDefault: j['timer_offset_default']  as int? ?? 0,
      timerChannel      : j['timer_channel']         as int? ?? 1,
      shotClockSeconds  : j['shot_clock_seconds']    as int? ?? 30,
      shotClockStyle    : _style('shot_clock_style',   DisplayStyle.shotDefault),
      shotClockChannel  : j['shot_clock_channel']    as int? ?? 2,
      aflHomeName       : j['afl_home_name']         as String? ?? 'HOME',
      aflAwayName       : j['afl_away_name']         as String? ?? 'AWAY',
      aflHomeGoals      : j['afl_home_goals']        as int? ?? 0,
      aflHomePoints     : j['afl_home_points']       as int? ?? 0,
      aflAwayGoals      : j['afl_away_goals']        as int? ?? 0,
      aflAwayPoints     : j['afl_away_points']       as int? ?? 0,
      aflQuarter        : j['afl_quarter']           as int? ?? 1,
      aflQuarterStyle   : _style('afl_quarter_style',  DisplayStyle.quarterDefault),
      cricketHomeName   : j['cricket_home_name']     as String? ?? 'HOME',
      cricketAwayName   : j['cricket_away_name']     as String? ?? 'AWAY',
      cricketHomeRuns   : j['cricket_home_runs']     as int? ?? 0,
      cricketHomeWickets: j['cricket_home_wickets']  as int? ?? 0,
      cricketAwayRuns   : j['cricket_away_runs']     as int? ?? 0,
      cricketAwayWickets: j['cricket_away_wickets']  as int? ?? 0,
      cricketExtras     : j['cricket_extras']        as int? ?? 0,
      cricketOvers      : j['cricket_overs']         as int? ?? 0,
      cricketBalls      : j['cricket_balls']         as int? ?? 0,
      homeTimeouts      : j['home_timeouts']         as int? ?? 0,
      awayTimeouts      : j['away_timeouts']         as int? ?? 0,
      homeFouls         : j['home_fouls']            as int? ?? 0,
      awayFouls         : j['away_fouls']            as int? ?? 0,
      singleColour      : j['single_colour']            as bool? ?? false,
      ultraWide         : j['ultra_wide']             as bool? ?? false,
      laptopScoring     : j['laptop_scoring']         as bool? ?? false,
      udpCommandDelayMs : j['udp_command_delay_ms']   as int?  ?? 120,
      udpInitFlushDelayMs:j['udp_init_flush_delay_ms']as int?  ?? 500,
      remappingMode     : j['remapping_mode']         as bool? ?? false,
      ramtHomeSlots     : _slots('ramt_home_slots',  [1, 2], legacyStartKey: 'ramt_home_start',  legacySpan: 2),
      ramtAwaySlots     : _slots('ramt_away_slots',  [3, 4], legacyStartKey: 'ramt_away_start',  legacySpan: 2),
      ramtTimerSlots    : _slots('ramt_timer_slots', [5, 6, 7], legacyStartKey: 'ramt_timer_start', legacySpan: 3),
      ramtShotClockSlot : j['ramt_shot_clock_slot']  as int?  ?? 8,
      counterChannels   : (j['counter_channels'] as Map<String, dynamic>? ?? {})
          .map((k, v) => MapEntry(k, v as int)),
      advertisements    : (j['advertisements'] as List<dynamic>? ?? [])
          .map((e) => Advertisement.fromJson(e as Map<String, dynamic>))
          .toList(),
      adSelections      : (j['ad_selections'] as Map<String, dynamic>? ?? {})
          .map((k, v) => MapEntry(k, AdSelection.fromJson(v as Map<String, dynamic>))),
      laptopAdSettings  : (j['laptop_ad_settings'] as Map<String, dynamic>? ?? {})
          .map((k, v) => MapEntry(k, v as String)),
      laptopSportPages  : (() {
        final raw = j['laptop_sport_pages'] as Map<String, dynamic>?;
        if (raw == null) return const <String, int?>{
          'AFL': 0, 'Soccer': 0, 'Cricket': 0,
          'Rugby': 0, 'Hockey': 0, 'Basketball': 0,
        };
        return raw.map((k, v) => MapEntry(k, v as int?));
      })(),
      laptopAdPages     : (() {
        final raw = j['laptop_ad_pages'] as Map<String, dynamic>?;
        if (raw == null) return const <String, int?>{
          'Ad1': 1, 'Ad2': 2, 'Ad3': 3, 'Ad4': 4, 'Ad5': 5,
        };
        return raw.map((k, v) => MapEntry(k, v as int?));
      })(),
      lastActiveMs      : j['last_active_ms']          as int?  ?? 0,
    );
  }

  Map<String, dynamic> toJson() => {
    'display_width'        : displayWidth,
    'display_height'       : displayHeight,
    'sport'                : currentSport,
    'home_score'           : homeScore,
    'away_score'           : awayScore,
    'home_name'            : homeName,
    'away_name'            : awayName,
    'team_style'           : teamStyle.toJson(),
    'afl_team_style'       : aflTeamStyle.toJson(),
    'cricket_team_style'   : cricketTeamStyle.toJson(),
    'timer_seconds'        : timerSeconds,
    'timer_countdown'      : timerCountdown,
    'timer_target_seconds' : timerTargetSeconds,
    'timer_style'          : timerStyle.toJson(),
    'timer_offset_afl'     : timerOffsetAfl,
    'timer_offset_default' : timerOffsetDefault,
    'timer_channel'        : timerChannel,
    'shot_clock_seconds'   : shotClockSeconds,
    'shot_clock_style'     : shotClockStyle.toJson(),
    'shot_clock_channel'   : shotClockChannel,
    'afl_home_name'        : aflHomeName,
    'afl_away_name'        : aflAwayName,
    'afl_home_goals'       : aflHomeGoals,
    'afl_home_points'      : aflHomePoints,
    'afl_away_goals'       : aflAwayGoals,
    'afl_away_points'      : aflAwayPoints,
    'afl_quarter'          : aflQuarter,
    'afl_quarter_style'    : aflQuarterStyle.toJson(),
    'cricket_home_name'    : cricketHomeName,
    'cricket_away_name'    : cricketAwayName,
    'cricket_home_runs'    : cricketHomeRuns,
    'cricket_home_wickets' : cricketHomeWickets,
    'cricket_away_runs'    : cricketAwayRuns,
    'cricket_away_wickets' : cricketAwayWickets,
    'cricket_extras'       : cricketExtras,
    'cricket_overs'        : cricketOvers,
    'cricket_balls'        : cricketBalls,
    'home_timeouts'        : homeTimeouts,
    'away_timeouts'        : awayTimeouts,
    'home_fouls'           : homeFouls,
    'away_fouls'           : awayFouls,
    'single_colour'           : singleColour,
    'ultra_wide'              : ultraWide,
    'laptop_scoring'          : laptopScoring,
    'udp_command_delay_ms'    : udpCommandDelayMs,
    'udp_init_flush_delay_ms' : udpInitFlushDelayMs,
    'remapping_mode'          : remappingMode,
    'ramt_home_slots'      : ramtHomeSlots,
    'ramt_away_slots'      : ramtAwaySlots,
    'ramt_timer_slots'     : ramtTimerSlots,
    'ramt_shot_clock_slot' : ramtShotClockSlot,
    'counter_channels'     : counterChannels,
    'advertisements'       : advertisements.map((a) => a.toJson()).toList(),
    'ad_selections'        : adSelections.map((k, v) => MapEntry(k, v.toJson())),
    'laptop_ad_settings'   : laptopAdSettings,
    'laptop_sport_pages'   : laptopSportPages,
    'laptop_ad_pages'      : laptopAdPages,
    'last_active_ms'       : lastActiveMs,
  };

  AppConfig copyWith({
    int? displayWidth, int? displayHeight,
    String? currentSport,
    int? homeScore, int? awayScore, String? homeName, String? awayName,
    DisplayStyle? teamStyle, DisplayStyle? aflTeamStyle, DisplayStyle? cricketTeamStyle,
    int? timerSeconds, bool? timerCountdown, int? timerTargetSeconds,
    DisplayStyle? timerStyle, int? timerOffsetAfl, int? timerOffsetDefault,
    int? timerChannel,
    int? shotClockSeconds, DisplayStyle? shotClockStyle,
    int? shotClockChannel,
    String? aflHomeName, String? aflAwayName,
    int? aflHomeGoals, int? aflHomePoints, int? aflAwayGoals, int? aflAwayPoints,
    int? aflQuarter, DisplayStyle? aflQuarterStyle,
    String? cricketHomeName, String? cricketAwayName,
    int? cricketHomeRuns, int? cricketHomeWickets,
    int? cricketAwayRuns, int? cricketAwayWickets,
    int? cricketExtras, int? cricketOvers, int? cricketBalls,
    int? homeTimeouts, int? awayTimeouts, int? homeFouls, int? awayFouls,
    bool? singleColour, bool? ultraWide,
    bool? laptopScoring,
    int? udpCommandDelayMs, int? udpInitFlushDelayMs,
    bool? remappingMode,
    List<int>? ramtHomeSlots, List<int>? ramtAwaySlots,
    List<int>? ramtTimerSlots, int? ramtShotClockSlot,
    Map<String, int>? counterChannels,
    List<Advertisement>? advertisements,
    Map<String, AdSelection>? adSelections,
    Map<String, String>? laptopAdSettings,
    Map<String, int?>? laptopSportPages,
    Map<String, int?>? laptopAdPages,
    int? lastActiveMs,
    // Allow explicitly setting nullable displayWidth/Height to null via sentinel
    bool clearDisplay = false,
  }) {
    return AppConfig(
      displayWidth      : clearDisplay ? null : (displayWidth       ?? this.displayWidth),
      displayHeight     : clearDisplay ? null : (displayHeight      ?? this.displayHeight),
      currentSport      : currentSport      ?? this.currentSport,
      homeScore         : homeScore         ?? this.homeScore,
      awayScore         : awayScore         ?? this.awayScore,
      homeName          : homeName          ?? this.homeName,
      awayName          : awayName          ?? this.awayName,
      teamStyle         : teamStyle         ?? this.teamStyle,
      aflTeamStyle      : aflTeamStyle      ?? this.aflTeamStyle,
      cricketTeamStyle  : cricketTeamStyle  ?? this.cricketTeamStyle,
      timerSeconds      : timerSeconds      ?? this.timerSeconds,
      timerCountdown    : timerCountdown    ?? this.timerCountdown,
      timerTargetSeconds: timerTargetSeconds?? this.timerTargetSeconds,
      timerStyle        : timerStyle        ?? this.timerStyle,
      timerOffsetAfl    : timerOffsetAfl    ?? this.timerOffsetAfl,
      timerOffsetDefault: timerOffsetDefault?? this.timerOffsetDefault,
      timerChannel      : timerChannel      ?? this.timerChannel,
      shotClockSeconds  : shotClockSeconds  ?? this.shotClockSeconds,
      shotClockStyle    : shotClockStyle    ?? this.shotClockStyle,
      shotClockChannel  : shotClockChannel  ?? this.shotClockChannel,
      aflHomeName       : aflHomeName       ?? this.aflHomeName,
      aflAwayName       : aflAwayName       ?? this.aflAwayName,
      aflHomeGoals      : aflHomeGoals      ?? this.aflHomeGoals,
      aflHomePoints     : aflHomePoints     ?? this.aflHomePoints,
      aflAwayGoals      : aflAwayGoals      ?? this.aflAwayGoals,
      aflAwayPoints     : aflAwayPoints     ?? this.aflAwayPoints,
      aflQuarter        : aflQuarter        ?? this.aflQuarter,
      aflQuarterStyle   : aflQuarterStyle   ?? this.aflQuarterStyle,
      cricketHomeName   : cricketHomeName   ?? this.cricketHomeName,
      cricketAwayName   : cricketAwayName   ?? this.cricketAwayName,
      cricketHomeRuns   : cricketHomeRuns   ?? this.cricketHomeRuns,
      cricketHomeWickets: cricketHomeWickets?? this.cricketHomeWickets,
      cricketAwayRuns   : cricketAwayRuns   ?? this.cricketAwayRuns,
      cricketAwayWickets: cricketAwayWickets?? this.cricketAwayWickets,
      cricketExtras     : cricketExtras     ?? this.cricketExtras,
      cricketOvers      : cricketOvers      ?? this.cricketOvers,
      cricketBalls      : cricketBalls      ?? this.cricketBalls,
      homeTimeouts      : homeTimeouts      ?? this.homeTimeouts,
      awayTimeouts      : awayTimeouts      ?? this.awayTimeouts,
      homeFouls         : homeFouls         ?? this.homeFouls,
      awayFouls         : awayFouls         ?? this.awayFouls,
      singleColour      : singleColour        ?? this.singleColour,
      ultraWide         : ultraWide           ?? this.ultraWide,
      laptopScoring     : laptopScoring       ?? this.laptopScoring,
      udpCommandDelayMs : udpCommandDelayMs   ?? this.udpCommandDelayMs,
      udpInitFlushDelayMs:udpInitFlushDelayMs ?? this.udpInitFlushDelayMs,
      remappingMode     : remappingMode       ?? this.remappingMode,
      ramtHomeSlots     : ramtHomeSlots     ?? this.ramtHomeSlots,
      ramtAwaySlots     : ramtAwaySlots     ?? this.ramtAwaySlots,
      ramtTimerSlots    : ramtTimerSlots    ?? this.ramtTimerSlots,
      ramtShotClockSlot : ramtShotClockSlot ?? this.ramtShotClockSlot,
      counterChannels   : counterChannels   ?? this.counterChannels,
      advertisements    : advertisements    ?? this.advertisements,
      adSelections      : adSelections      ?? this.adSelections,
      laptopAdSettings  : laptopAdSettings  ?? this.laptopAdSettings,
      laptopSportPages  : laptopSportPages  ?? this.laptopSportPages,
      laptopAdPages     : laptopAdPages     ?? this.laptopAdPages,
      lastActiveMs      : lastActiveMs      ?? this.lastActiveMs,
    );
  }
}
