import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/app_config.dart';

/// Persists and loads [AppConfig] via SharedPreferences (cross-platform).
class ConfigService {
  static const _key = 'scoreboard_config';

  Future<AppConfig> load() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final raw   = prefs.getString(_key);
      if (raw == null) return const AppConfig();
      final json  = jsonDecode(raw) as Map<String, dynamic>;
      return AppConfig.fromJson(json);
    } catch (e) {
      // ignore: avoid_print
      print('[Config] load error: $e — using defaults');
      return const AppConfig();
    }
  }

  Future<void> save(AppConfig config) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_key, jsonEncode(config.toJson()));
    } catch (e) {
      // ignore: avoid_print
      print('[Config] save error: $e');
    }
  }

  Future<void> clear() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_key);
  }
}
