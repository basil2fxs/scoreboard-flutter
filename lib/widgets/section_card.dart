import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

/// Consistent dark card used throughout sport screens.
class SectionCard extends StatelessWidget {
  final String title;
  final Widget child;
  final Widget? trailing;
  final EdgeInsetsGeometry padding;

  const SectionCard({
    super.key,
    required this.title,
    required this.child,
    this.trailing,
    this.padding = const EdgeInsets.fromLTRB(14, 6, 14, 14),
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppColors.surfaceBorder),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header row
          Padding(
            padding: const EdgeInsets.fromLTRB(14, 10, 10, 6),
            child: Row(
              children: [
                Text(title,
                  style: const TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.bold,
                    color: AppColors.textSecondary,
                    letterSpacing: 0.8,
                  ),
                ),
                const Spacer(),
                if (trailing != null) trailing!,
              ],
            ),
          ),
          const Divider(height: 1, color: AppColors.surfaceBorder),
          Padding(padding: padding, child: child),
        ],
      ),
    );
  }
}

/// Gear-icon settings button used in card headers.
class SettingsIconButton extends StatelessWidget {
  final VoidCallback onTap;
  const SettingsIconButton({super.key, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(6),
        decoration: BoxDecoration(
          color: AppColors.surfaceHigh,
          borderRadius: BorderRadius.circular(8),
        ),
        child: const Icon(Icons.tune, size: 18, color: AppColors.textSecondary),
      ),
    );
  }
}
