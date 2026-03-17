import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'providers/app_provider.dart';
import 'theme/app_theme.dart';
import 'screens/display_setup_screen.dart';
import 'screens/home_screen.dart';
import 'screens/sport_selection_screen.dart';
import 'screens/soccer_screen.dart';
import 'screens/afl_screen.dart';
import 'screens/cricket_screen.dart';
import 'screens/simple_sport_screen.dart';
import 'screens/ad_editor_screen.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  // Portrait-only (scoreboard is a portrait-optimised control app)
  SystemChrome.setPreferredOrientations([
    DeviceOrientation.portraitUp,
    DeviceOrientation.portraitDown,
  ]);
  SystemChrome.setSystemUIOverlayStyle(const SystemUiOverlayStyle(
    statusBarColor: Colors.transparent,
    statusBarIconBrightness: Brightness.light,
  ));
  runApp(
    ChangeNotifierProvider(
      create: (_) => AppProvider(),
      child: const ScoreboardApp(),
    ),
  );
}

class ScoreboardApp extends StatelessWidget {
  const ScoreboardApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Scoreboard Control',
      debugShowCheckedModeBanner: false,
      theme: buildAppTheme(),
      // Determine initial route based on whether display has been configured.
      home: _InitRouter(),
      routes: {
        '/setup'         : (_) => const DisplaySetupScreen(),
        '/home'          : (_) => const HomeScreen(),
        '/sportSelection': (_) => const SportSelectionScreen(),
        '/soccer'        : (_) => const SoccerScreen(),
        '/afl'           : (_) => const AflScreen(),
        '/cricket'       : (_) => const CricketScreen(),
        '/simple'        : (_) => const SimpleSportScreen(),
        '/adEditor'      : (_) => const AdEditorScreen(),
      },
    );
  }
}

/// Routes to setup or home based on whether display dimensions are saved.
class _InitRouter extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final config = context.watch<AppProvider>().config;
    // Show a loading spinner until the config has been loaded from storage.
    // AppProvider._init() is async, so on very first frame config is default.
    // We treat displayWidth == null as "not yet configured" → setup screen.
    if (!config.isDisplayConfigured) {
      return const DisplaySetupScreen();
    }
    return const HomeScreen();
  }
}
