import 'dart:convert';
import 'dart:io';
import 'package:path_provider/path_provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/app_config.dart';

/// Persists [AppConfig] using two layers:
///
/// PRIMARY  — JSON file in the app's documents directory.
///            Survives app updates indefinitely; never cleared by the OS.
///
/// FALLBACK — SharedPreferences (legacy / migration path).
///            If the JSON file is absent but SharedPreferences has data,
///            the data is migrated into the JSON file automatically.
///
/// On every [save] both layers are written so there is always a backup.
class ConfigService {
  static const _legacyKey  = 'scoreboard_config';
  static const _fileName   = 'scoreboard_config.json';

  // ─── File helpers ──────────────────────────────────────────────────────────

  Future<File> _file() async {
    final dir = await getApplicationDocumentsDirectory();
    return File('${dir.path}/$_fileName');
  }

  // ─── Load ──────────────────────────────────────────────────────────────────

  Future<AppConfig> load() async {
    // 1. Try primary JSON file
    try {
      final f = await _file();
      if (await f.exists()) {
        final raw  = await f.readAsString();
        final json = jsonDecode(raw) as Map<String, dynamic>;
        return AppConfig.fromJson(json);
      }
    } catch (e) {
      // ignore: avoid_print
      print('[Config] file load error: $e');
    }

    // 2. Migrate from SharedPreferences if file absent
    try {
      final prefs = await SharedPreferences.getInstance();
      final raw   = prefs.getString(_legacyKey);
      if (raw != null) {
        final json   = jsonDecode(raw) as Map<String, dynamic>;
        final config = AppConfig.fromJson(json);
        // Write to primary file immediately so next launch uses the file
        await save(config);
        // ignore: avoid_print
        print('[Config] migrated from SharedPreferences → file');
        return config;
      }
    } catch (e) {
      // ignore: avoid_print
      print('[Config] SharedPreferences migration error: $e');
    }

    return const AppConfig();
  }

  // ─── Save (writes both layers) ─────────────────────────────────────────────

  Future<void> save(AppConfig config) async {
    final encoded = jsonEncode(config.toJson());

    // Primary: file
    try {
      final f = await _file();
      await f.writeAsString(encoded, flush: true);
    } catch (e) {
      // ignore: avoid_print
      print('[Config] file save error: $e');
    }

    // Backup: SharedPreferences
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_legacyKey, encoded);
    } catch (e) {
      // ignore: avoid_print
      print('[Config] SharedPreferences save error: $e');
    }
  }

  // ─── Clear (removes both layers) ───────────────────────────────────────────

  Future<void> clear() async {
    try {
      final f = await _file();
      if (await f.exists()) await f.delete();
    } catch (_) {}
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove(_legacyKey);
    } catch (_) {}
  }
}
