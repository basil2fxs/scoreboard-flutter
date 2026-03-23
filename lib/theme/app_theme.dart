import 'package:flutter/material.dart';

// ─── Colour Palette ──────────────────────────────────────────────────────────
class AppColors {
  AppColors._();

  static const background   = Color(0xFF1A1A1A);
  static const surface      = Color(0xFF2A2A2A);
  static const surfaceHigh  = Color(0xFF333333);
  static const surfaceBorder= Color(0xFF3A3A3A);
  static const accent       = Color(0xFF0099DD);
  static const accentDark   = Color(0xFF0066AA);
  static const success      = Color(0xFF00AA00);
  static const successBright= Color(0xFF00FF00);
  static const warning      = Color(0xFFFFAA00);
  static const danger       = Color(0xFFCC0000);
  static const dangerBright = Color(0xFFFF3333);
  static const textPrimary  = Color(0xFFFFFFFF);
  static const textSecondary= Color(0xFFAAAAAA);
  static const textMuted    = Color(0xFF666666);
  static const homeTeam     = Color(0xFF00AAFF);
  static const awayTeam     = Color(0xFFFF8800);
  static const timerGreen   = Color(0xFF00FF66);
  static const quarterGold  = Color(0xFFFFCC00);
}

// ─── LED Colour Options (matching hardware codes) ─────────────────────────────
class LedColor {
  final String code;
  final String label;
  final Color color;
  const LedColor(this.code, this.label, this.color);
}

const List<LedColor> kLedColors = [
  LedColor('1', 'Red',    Color(0xFFFF3333)),
  LedColor('2', 'Green',  Color(0xFF00DD00)),
  LedColor('3', 'Yellow', Color(0xFFFFDD00)),
  LedColor('4', 'Blue',   Color(0xFF4488FF)),
  LedColor('5', 'Purple', Color(0xFFCC44FF)),
  LedColor('6', 'Cyan',   Color(0xFF00EEFF)),
  LedColor('7', 'White',  Color(0xFFFFFFFF)),
];

// ─── LED Size Options ─────────────────────────────────────────────────────────
class LedSize {
  final String code;
  final String label;
  final String description;
  const LedSize(this.code, this.label, this.description);
}

const List<LedSize> kLedSizes = [
  LedSize('1', 'S',  'Small (7 chars/slot)'),
  LedSize('2', 'M',  'Medium (4 chars/slot)'),
  LedSize('3', 'L',  'Large (2 chars/slot)'),
  LedSize('4', 'XL', 'Extra Large (1 char/slot)'),
];

// ─── Alignment Options ────────────────────────────────────────────────────────
class AlignOption {
  final String code;
  final String label;
  const AlignOption(this.code, this.label);
}

const List<AlignOption> kHAlignOptions = [
  AlignOption('1', 'Centre'),
  AlignOption('2', 'Right'),
  AlignOption('3', 'Left'),
];

const List<AlignOption> kVAlignOptions = [
  AlignOption('3', 'Top'),
  AlignOption('1', 'Mid'),
  AlignOption('2', 'Bot'),
];

// ─── Theme ────────────────────────────────────────────────────────────────────
ThemeData buildAppTheme() {
  return ThemeData(
    useMaterial3: true,
    brightness: Brightness.dark,
    scaffoldBackgroundColor: AppColors.background,
    colorScheme: const ColorScheme.dark(
      primary: AppColors.accent,
      secondary: AppColors.warning,
      surface: AppColors.surface,
      error: AppColors.dangerBright,
      onPrimary: Colors.white,
      onSurface: AppColors.textPrimary,
    ),
    appBarTheme: const AppBarTheme(
      backgroundColor: AppColors.surface,
      foregroundColor: AppColors.textPrimary,
      centerTitle: true,
      elevation: 0,
      titleTextStyle: TextStyle(
        fontSize: 20,
        fontWeight: FontWeight.bold,
        color: AppColors.textPrimary,
      ),
    ),
    cardTheme: CardThemeData(
      color: AppColors.surface,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(14),
        side: const BorderSide(color: AppColors.surfaceBorder),
      ),
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: AppColors.accent,
        foregroundColor: Colors.white,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
        textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
        elevation: 0,
      ),
    ),
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(foregroundColor: AppColors.accent),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: AppColors.surfaceHigh,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
        borderSide: BorderSide.none,
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
        borderSide: const BorderSide(color: AppColors.accent, width: 2),
      ),
      contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
      labelStyle: const TextStyle(color: AppColors.textSecondary),
      hintStyle: const TextStyle(color: AppColors.textMuted),
    ),
    dividerTheme: const DividerThemeData(color: AppColors.surfaceBorder, space: 1),
    textTheme: const TextTheme(
      headlineLarge : TextStyle(fontSize: 28, fontWeight: FontWeight.bold, color: AppColors.textPrimary),
      headlineMedium: TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: AppColors.textPrimary),
      headlineSmall : TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppColors.textPrimary),
      titleLarge    : TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: AppColors.textPrimary),
      titleMedium   : TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: AppColors.textPrimary),
      bodyLarge     : TextStyle(fontSize: 16, color: AppColors.textPrimary),
      bodyMedium    : TextStyle(fontSize: 14, color: AppColors.textSecondary),
      labelLarge    : TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: AppColors.textPrimary),
      labelSmall    : TextStyle(fontSize: 11, color: AppColors.textMuted),
    ),
  );
}
