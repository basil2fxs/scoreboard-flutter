import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import '../models/advertisement.dart';
import '../providers/app_provider.dart';
import '../theme/app_theme.dart';
import 'section_card.dart';

/// Advertisement checklist + loop controls — embedded in every sport screen.
class AdsPanel extends StatelessWidget {
  final VoidCallback onReturnToScores;
  const AdsPanel({super.key, required this.onReturnToScores});

  @override
  Widget build(BuildContext context) {
    final app         = context.watch<AppProvider>();
    final ads         = app.config.advertisements;
    final sel         = app.config.adSelections;
    final loop        = app.adLoopActive;
    final anySelected = ads.any((ad) => sel[ad.name]?.selected == true);

    return SectionCard(
      title: 'ADVERTISEMENTS',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (ads.isEmpty)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 12),
              child: Text('No ads saved yet. Create one below.',
                  style: TextStyle(color: AppColors.textMuted, fontSize: 13)),
            )
          else ...[
            // Header row
            const Row(
              children: [
                SizedBox(width: 36),
                Expanded(child: Text('Advertisement',
                    style: TextStyle(fontSize: 11, color: AppColors.textMuted,
                        fontWeight: FontWeight.bold))),
                SizedBox(width: 64,
                  child: Text('Secs', textAlign: TextAlign.center,
                      style: TextStyle(fontSize: 11, color: AppColors.textMuted,
                          fontWeight: FontWeight.bold))),
              ],
            ),
            const SizedBox(height: 4),
            // List
            ...ads.asMap().entries.map((entry) {
              final idx = entry.key;
              final ad  = entry.value;
              final s   = sel[ad.name] ?? const AdSelection();
              return _AdRow(
                adName   : ad.name,
                selected : s.selected,
                duration : s.duration,
                onToggle : (v) => context.read<AppProvider>().setAdSelection(ad.name, v),
                onDuration: (v) => context.read<AppProvider>().setAdDuration(ad.name, v),
                onEdit   : () => Navigator.pushNamed(context, '/adEditor',
                    arguments: {'index': idx}),
                onDelete : () => _confirmDelete(context, idx, ad.name),
              );
            }),
          ],

          const SizedBox(height: 12),
          const Divider(color: AppColors.surfaceBorder),
          const SizedBox(height: 8),

          // Control buttons
          Row(
            children: [
              Expanded(
                child: ElevatedButton.icon(
                  onPressed: loop
                      ? () {
                          context.read<AppProvider>().stopAdLoop();
                          onReturnToScores();
                        }
                      : null,
                  icon: const Icon(Icons.stop_circle_outlined, size: 18),
                  label: const Text('Return to Scores'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: loop ? AppColors.warning : AppColors.surfaceHigh,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 12),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: ElevatedButton.icon(
                  onPressed: (loop || !anySelected)
                      ? null
                      : () => context.read<AppProvider>().startAdLoop(),
                  icon: const Icon(Icons.play_circle_outline, size: 18),
                  label: const Text('Play Ads'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: (loop || !anySelected)
                        ? AppColors.surfaceHigh
                        : AppColors.success,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 12),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              onPressed: () => Navigator.pushNamed(context, '/adEditor'),
              icon: const Icon(Icons.add, size: 18),
              label: const Text('Create New Advertisement'),
              style: OutlinedButton.styleFrom(
                foregroundColor: AppColors.accent,
                side: const BorderSide(color: AppColors.accent),
                padding: const EdgeInsets.symmetric(vertical: 12),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _confirmDelete(BuildContext ctx, int idx, String name) async {
    final ok = await showDialog<bool>(
      context: ctx,
      builder: (d) => AlertDialog(
        backgroundColor: AppColors.surface,
        title: const Text('Delete Advertisement'),
        content: Text('Delete "$name"?\nThis cannot be undone.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Cancel')),
          ElevatedButton(
            onPressed: () => Navigator.pop(d, true),
            style: ElevatedButton.styleFrom(backgroundColor: AppColors.danger),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
    if (ok == true && ctx.mounted) {
      ctx.read<AppProvider>().deleteAdvertisement(idx);
    }
  }
}

class _AdRow extends StatefulWidget {
  final String adName;
  final bool selected;
  final String duration;
  final ValueChanged<bool> onToggle;
  final ValueChanged<String> onDuration;
  final VoidCallback onEdit;
  final VoidCallback onDelete;
  const _AdRow({
    required this.adName, required this.selected, required this.duration,
    required this.onToggle, required this.onDuration,
    required this.onEdit, required this.onDelete,
  });
  @override
  State<_AdRow> createState() => _AdRowState();
}

class _AdRowState extends State<_AdRow> {
  late TextEditingController _dur;
  @override
  void initState() {
    super.initState();
    _dur = TextEditingController(text: widget.duration);
  }
  @override
  void didUpdateWidget(_AdRow old) {
    super.didUpdateWidget(old);
    if (old.duration != widget.duration && !_dur.selection.isValid) {
      _dur.text = widget.duration;
    }
  }
  @override
  void dispose() { _dur.dispose(); super.dispose(); }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          // Checkbox
          SizedBox(
            width: 36,
            child: Checkbox(
              value: widget.selected,
              onChanged: (v) => widget.onToggle(v ?? false),
              activeColor: AppColors.accent,
              side: const BorderSide(color: AppColors.textMuted),
            ),
          ),
          // Ad name
          Expanded(
            child: Text(widget.adName,
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w600,
                color: widget.selected ? Colors.white : AppColors.textSecondary,
              ),
              maxLines: 1, overflow: TextOverflow.ellipsis,
            ),
          ),
          // Duration entry
          SizedBox(
            width: 48,
            child: TextField(
              controller: _dur,
              textAlign: TextAlign.center,
              keyboardType: TextInputType.number,
              inputFormatters: [FilteringTextInputFormatter.digitsOnly],
              style: const TextStyle(fontSize: 13, color: Colors.white),
              decoration: const InputDecoration(
                filled: true,
                fillColor: AppColors.surfaceHigh,
                border: OutlineInputBorder(borderSide: BorderSide.none),
                contentPadding: EdgeInsets.symmetric(vertical: 8),
              ),
              onChanged: widget.onDuration,
            ),
          ),
          const SizedBox(width: 4),
          // Edit
          IconButton(
            icon: const Icon(Icons.edit_outlined, size: 18, color: AppColors.accent),
            onPressed: widget.onEdit,
            padding: EdgeInsets.zero,
            constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
          ),
          // Delete
          IconButton(
            icon: const Icon(Icons.delete_outline, size: 18, color: AppColors.danger),
            onPressed: widget.onDelete,
            padding: EdgeInsets.zero,
            constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
          ),
        ],
      ),
    );
  }
}
