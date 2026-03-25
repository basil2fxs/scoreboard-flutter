import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_provider.dart';
import '../theme/app_theme.dart';

class SportSelectionScreen extends StatelessWidget {
  const SportSelectionScreen({super.key});

  static const _sports = [
    ('AFL',              '🦘', Color(0xFFCC6600)),
    ('Soccer','⚽', Color(0xFF0066CC)),
    ('Cricket',          '🏏', Color(0xFF006600)),
    ('Rugby',            '🏉', Color(0xFF660066)),
    ('Hockey',           '🏒', Color(0xFF006666)),
    ('Basketball',       '🏀', Color(0xFFCC3300)),
  ];

  @override
  Widget build(BuildContext context) {
    final current = context.watch<AppProvider>().config.currentSport;
    return Scaffold(
      appBar: AppBar(title: const Text('Select Sport')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const Text('Choose a sport to begin scoring.',
              style: TextStyle(color: AppColors.textMuted, fontSize: 13)),
          const SizedBox(height: 16),
          ..._sports.map((s) {
            final (name, icon, color) = s;
            final selected = current == name;
            return Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Material(
                color: selected ? color : AppColors.surface,
                borderRadius: BorderRadius.circular(14),
                elevation: 0,
                child: InkWell(
                  borderRadius: BorderRadius.circular(14),
                  onTap: () {
                    context.read<AppProvider>().selectSport(name);
                    Navigator.pop(context);
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(content: Text('$name selected'), duration: const Duration(seconds: 1)),
                    );
                  },
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 18),
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(14),
                      border: Border.all(
                        color: selected ? color : AppColors.surfaceBorder,
                        width: selected ? 2 : 1,
                      ),
                    ),
                    child: Row(
                      children: [
                        Text(icon, style: const TextStyle(fontSize: 28)),
                        const SizedBox(width: 16),
                        Text(name,
                          style: TextStyle(
                            fontSize: 20, fontWeight: FontWeight.bold,
                            color: selected ? Colors.white : AppColors.textPrimary,
                          ),
                        ),
                        const Spacer(),
                        if (selected)
                          const Icon(Icons.check_circle, color: Colors.white),
                      ],
                    ),
                  ),
                ),
              ),
            );
          }),
        ],
      ),
    );
  }
}
