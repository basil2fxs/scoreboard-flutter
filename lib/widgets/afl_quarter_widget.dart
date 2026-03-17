import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_provider.dart';
import '../theme/app_theme.dart';
import 'settings_dialogs.dart';
import 'section_card.dart';

class AflQuarterWidget extends StatelessWidget {
  const AflQuarterWidget({super.key});

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppProvider>();
    final q   = app.config.aflQuarter;

    return SectionCard(
      title: 'QUARTER',
      trailing: SettingsIconButton(onTap: () => showAflQuarterSettingsDialog(context)),
      child: Column(
        children: [
          // Big display
          Text(
            q == 0 ? 'Off' : 'Q$q',
            style: TextStyle(
              fontSize: 40,
              fontWeight: FontWeight.bold,
              color: q == 0 ? AppColors.textMuted : AppColors.quarterGold,
            ),
          ),
          const SizedBox(height: 12),
          // Selector buttons
          Row(
            children: [
              _QBtn(label: 'Off', value: 0, selected: q == 0,
                    onTap: () => context.read<AppProvider>().setAflQuarter(0)),
              for (int i = 1; i <= 4; i++)
                _QBtn(label: 'Q$i', value: i, selected: q == i,
                      onTap: () => context.read<AppProvider>().setAflQuarter(i)),
            ],
          ),
        ],
      ),
    );
  }
}

class _QBtn extends StatelessWidget {
  final String label;
  final int value;
  final bool selected;
  final VoidCallback onTap;
  const _QBtn({required this.label, required this.value, required this.selected, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 3),
        child: Material(
          color: selected
              ? (value == 0 ? AppColors.danger.withOpacity(0.8) : AppColors.accentDark)
              : AppColors.surfaceHigh,
          borderRadius: BorderRadius.circular(8),
          child: InkWell(
            borderRadius: BorderRadius.circular(8),
            onTap: onTap,
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 10),
              child: Text(label,
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: 15,
                  color: selected ? Colors.white : AppColors.textSecondary,
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
