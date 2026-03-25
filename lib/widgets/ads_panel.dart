import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import '../models/advertisement.dart';
import '../providers/app_provider.dart';
import '../theme/app_theme.dart';
import 'section_card.dart';

/// Advertisement panel — embedded in every sport screen.
/// In laptop mode: shows fixed Ad 1–5 slots (program-select only).
/// In normal mode: shows custom user-created ads with full CRUD.
class AdsPanel extends StatelessWidget {
  final VoidCallback onReturnToScores;
  const AdsPanel({super.key, required this.onReturnToScores});

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppProvider>();
    if (app.laptopScoring) {
      return _LaptopAdsPanel(onReturnToScores: onReturnToScores);
    }
    return _NormalAdsPanel(onReturnToScores: onReturnToScores);
  }
}

// ─── Laptop mode: Fixed Ads 1–5 ───────────────────────────────────────────────

class _LaptopAdsPanel extends StatelessWidget {
  final VoidCallback onReturnToScores;
  const _LaptopAdsPanel({required this.onReturnToScores});

  @override
  Widget build(BuildContext context) {
    final app  = context.watch<AppProvider>();
    final loop = app.adLoopActive;
    final anySelected = List.generate(5, (i) => app.getLaptopAdSelected(i + 1))
        .any((s) => s);

    return SectionCard(
      title: 'ADVERTISEMENTS',
      trailing: IconButton(
        icon: const Icon(Icons.info_outline, size: 20, color: AppColors.textMuted),
        onPressed: () => showDialog<void>(
          context: context,
          builder: (d) => AlertDialog(
            backgroundColor: AppColors.surface,
            title: const Row(
              children: [
                Icon(Icons.info_outline, color: AppColors.accent, size: 22),
                SizedBox(width: 8),
                Text('Laptop Ad Slots'),
              ],
            ),
            content: const Text(
              'Select how many advertisements or sponsor programs you have added in PowerLED.\n\n'
              'Each program is another advertisement slot — Ad 1 corresponds to the first program you added, Ad 2 to the second, and so on.\n\n'
              'Set the duration (in seconds) for each ad and tick the box to include it in the loop.',
              style: TextStyle(color: AppColors.textSecondary, fontSize: 16),
            ),
            actions: [
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: () => Navigator.pop(d),
                  child: const Text('Got it',
                      style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold)),
                ),
              ),
            ],
          ),
        ),
        padding: EdgeInsets.zero,
        constraints: const BoxConstraints(minWidth: 36, minHeight: 36),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          const Row(
            children: [
              SizedBox(width: 36),
              Expanded(child: Text('Advertisement',
                  style: TextStyle(fontSize: 11, color: AppColors.textMuted,
                      fontWeight: FontWeight.bold))),
              SizedBox(width: 52,
                child: Text('Secs', textAlign: TextAlign.center,
                    style: TextStyle(fontSize: 11, color: AppColors.textMuted,
                        fontWeight: FontWeight.bold))),
            ],
          ),
          const SizedBox(height: 4),

          // Fixed Ad 1–5 rows
          ...List.generate(5, (idx) {
            final n = idx + 1;
            return _LaptopAdRow(
              adNumber: n,
              selected: app.getLaptopAdSelected(n),
              duration: app.getLaptopAdDuration(n),
              currentName: app.getLaptopAdName(n),
              onToggle: (v) => context.read<AppProvider>()
                  .setLaptopAdSetting('Ad${n}_sel', v ? 'true' : 'false'),
              onDuration: (v) => context.read<AppProvider>()
                  .setLaptopAdSetting('Ad${n}_dur', v),
            );
          }),

          const SizedBox(height: 12),
          const Divider(color: AppColors.surfaceBorder),
          const SizedBox(height: 8),

          // Control buttons
          Row(
            children: [
              Expanded(
                child: SizedBox(
                  height: 64,
                  child: ElevatedButton.icon(
                    onPressed: loop
                        ? () {
                            context.read<AppProvider>().stopAdLoop();
                            onReturnToScores();
                          }
                        : null,
                    icon: const Icon(Icons.stop_circle_outlined, size: 18),
                    label: const Text('Return to\nScores',
                        textAlign: TextAlign.center, maxLines: 2),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: loop ? AppColors.warning : AppColors.surfaceHigh,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 12),
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: SizedBox(
                  height: 64,
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
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _LaptopAdRow extends StatefulWidget {
  final int adNumber;
  final bool selected;
  final String duration;
  final String currentName;
  final ValueChanged<bool> onToggle;
  final ValueChanged<String> onDuration;
  const _LaptopAdRow({
    required this.adNumber, required this.selected, required this.duration,
    required this.currentName,
    required this.onToggle, required this.onDuration,
  });
  @override
  State<_LaptopAdRow> createState() => _LaptopAdRowState();
}

class _LaptopAdRowState extends State<_LaptopAdRow> {
  late TextEditingController _dur;
  @override
  void initState() {
    super.initState();
    _dur = TextEditingController(text: widget.duration);
  }
  @override
  void didUpdateWidget(_LaptopAdRow old) {
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
          SizedBox(
            width: 36,
            child: Checkbox(
              value: widget.selected,
              onChanged: (v) => widget.onToggle(v ?? false),
              activeColor: AppColors.accent,
              side: const BorderSide(color: AppColors.textMuted),
            ),
          ),
          Expanded(
            child: Text(
              widget.currentName,
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w600,
                color: widget.selected ? Colors.white : AppColors.textSecondary,
              ),
              maxLines: 1, overflow: TextOverflow.ellipsis,
            ),
          ),
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
          GestureDetector(
            onTap: () => _showRenameDialog(context),
            child: Container(
              width: 32, height: 32,
              decoration: BoxDecoration(
                color: AppColors.surfaceHigh,
                borderRadius: BorderRadius.circular(6),
              ),
              child: const Icon(Icons.edit_outlined, size: 16, color: AppColors.accent),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _showRenameDialog(BuildContext context) async {
    final ctrl = TextEditingController(text: widget.currentName);
    final ok = await showDialog<bool>(
      context: context,
      builder: (d) => AlertDialog(
        backgroundColor: AppColors.surface,
        title: Text('Rename Ad ${widget.adNumber}'),
        content: TextField(
          controller: ctrl,
          autofocus: true,
          style: const TextStyle(color: Colors.white, fontSize: 16),
          decoration: const InputDecoration(
            labelText: 'Ad Name',
            labelStyle: TextStyle(color: AppColors.textSecondary),
            filled: true,
            fillColor: AppColors.surfaceHigh,
            border: OutlineInputBorder(
                borderSide: BorderSide(color: AppColors.surfaceBorder)),
            enabledBorder: OutlineInputBorder(
                borderSide: BorderSide(color: AppColors.surfaceBorder)),
            focusedBorder: OutlineInputBorder(
                borderSide: BorderSide(color: AppColors.accent, width: 2)),
          ),
        ),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(d, false),
              child: const Text('Cancel')),
          ElevatedButton(
            onPressed: () => Navigator.pop(d, true),
            style: ElevatedButton.styleFrom(backgroundColor: AppColors.accent),
            child: const Text('Save'),
          ),
        ],
      ),
    );
    final name = ctrl.text.trim();
    ctrl.dispose();
    if (ok == true && context.mounted && name.isNotEmpty) {
      context.read<AppProvider>()
          .setLaptopAdSetting('Ad${widget.adNumber}_name', name);
    }
  }
}

// ─── Normal mode: Custom Ads ───────────────────────────────────────────────────

class _NormalAdsPanel extends StatelessWidget {
  final VoidCallback onReturnToScores;
  const _NormalAdsPanel({required this.onReturnToScores});

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
                child: SizedBox(
                  height: 64,
                  child: ElevatedButton.icon(
                    onPressed: loop
                        ? () {
                            context.read<AppProvider>().stopAdLoop();
                            onReturnToScores();
                          }
                        : null,
                    icon: const Icon(Icons.stop_circle_outlined, size: 18),
                    label: const Text('Return to\nScores',
                        textAlign: TextAlign.center, maxLines: 2),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: loop ? AppColors.warning : AppColors.surfaceHigh,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 12),
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: SizedBox(
                  height: 64,
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
              ),
            ],
          ),
          const SizedBox(height: 8),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              onPressed: () {
                // Stop ads and return to scores before navigating to editor
                final appP = context.read<AppProvider>();
                appP.stopAdLoop();
                appP.sendSportProgram();
                Navigator.pushNamed(context, '/adEditor');
              },
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
          SizedBox(
            width: 36,
            child: Checkbox(
              value: widget.selected,
              onChanged: (v) => widget.onToggle(v ?? false),
              activeColor: AppColors.accent,
              side: const BorderSide(color: AppColors.textMuted),
            ),
          ),
          Expanded(
            child: Text(widget.adName,
              style: TextStyle(
                fontSize: 14, fontWeight: FontWeight.w600,
                color: widget.selected ? Colors.white : AppColors.textSecondary,
              ),
              maxLines: 1, overflow: TextOverflow.ellipsis,
            ),
          ),
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
          IconButton(
            icon: const Icon(Icons.edit_outlined, size: 18, color: AppColors.accent),
            onPressed: widget.onEdit,
            padding: EdgeInsets.zero,
            constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
          ),
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
