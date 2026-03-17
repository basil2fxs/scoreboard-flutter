import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../theme/app_theme.dart';

/// Reusable +/− score control row.
class ScoreRow extends StatelessWidget {
  final String label;
  final int value;
  final Color labelColor;
  final VoidCallback onDecrement;
  final VoidCallback onIncrement;
  final ValueChanged<int>? onManualEdit;

  const ScoreRow({
    super.key,
    required this.label,
    required this.value,
    this.labelColor = AppColors.textPrimary,
    required this.onDecrement,
    required this.onIncrement,
    this.onManualEdit,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        // Team label
        SizedBox(
          width: 72,
          child: Text(label,
            style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: labelColor),
            maxLines: 1, overflow: TextOverflow.ellipsis,
          ),
        ),
        // Minus
        _ActionBtn(label: '−', color: AppColors.danger, onTap: onDecrement),
        const SizedBox(width: 8),
        // Score display / editable
        Expanded(
          child: onManualEdit != null
              ? _EditableScore(value: value, onSubmit: onManualEdit!)
              : _StaticScore(value: value),
        ),
        const SizedBox(width: 8),
        // Plus
        _ActionBtn(label: '+', color: AppColors.success, onTap: onIncrement),
      ],
    );
  }
}

class _StaticScore extends StatelessWidget {
  final int value;
  const _StaticScore({required this.value});
  @override
  Widget build(BuildContext context) {
    return Container(
      alignment: Alignment.center,
      padding: const EdgeInsets.symmetric(vertical: 10),
      decoration: BoxDecoration(
        color: AppColors.background,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.surfaceBorder),
      ),
      child: Text('$value',
        style: const TextStyle(fontSize: 28, fontWeight: FontWeight.bold, color: Colors.white),
      ),
    );
  }
}

class _EditableScore extends StatefulWidget {
  final int value;
  final ValueChanged<int> onSubmit;
  const _EditableScore({required this.value, required this.onSubmit});
  @override
  State<_EditableScore> createState() => _EditableScoreState();
}

class _EditableScoreState extends State<_EditableScore> {
  late TextEditingController _ctrl;
  late FocusNode _focus;

  @override
  void initState() {
    super.initState();
    _ctrl = TextEditingController(text: '${widget.value}');
    _focus = FocusNode();
    _focus.addListener(() {
      // When focus is lost, restore to current value if field was cleared
      if (!mounted) return; // guard against post-dispose callbacks
      if (!_focus.hasFocus && _ctrl.text.isEmpty) {
        _ctrl.text = '${widget.value}';
      }
    });
  }

  @override
  void didUpdateWidget(_EditableScore old) {
    super.didUpdateWidget(old);
    // Sync display when value changes externally and field is not focused
    if (old.value != widget.value && !_focus.hasFocus) {
      _ctrl.text = '${widget.value}';
    }
  }

  @override
  void dispose() {
    _focus.dispose();
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return TextField(
      controller: _ctrl,
      focusNode: _focus,
      textAlign: TextAlign.center,
      keyboardType: TextInputType.number,
      inputFormatters: [FilteringTextInputFormatter.digitsOnly],
      style: const TextStyle(fontSize: 28, fontWeight: FontWeight.bold, color: Colors.white),
      decoration: InputDecoration(
        filled: true,
        fillColor: AppColors.background,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: const BorderSide(color: AppColors.surfaceBorder),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: const BorderSide(color: AppColors.surfaceBorder),
        ),
        contentPadding: const EdgeInsets.symmetric(vertical: 10),
      ),
      onSubmitted: (v) => widget.onSubmit(int.tryParse(v) ?? widget.value),
      onEditingComplete: () {
        // Restore if blank, otherwise submit
        if (_ctrl.text.isEmpty) {
          _ctrl.text = '${widget.value}';
        } else {
          widget.onSubmit(int.tryParse(_ctrl.text) ?? widget.value);
        }
        FocusScope.of(context).unfocus();
      },
    );
  }
}

class _ActionBtn extends StatelessWidget {
  final String label;
  final Color color;
  final VoidCallback onTap;
  const _ActionBtn({required this.label, required this.color, required this.onTap});
  @override
  Widget build(BuildContext context) {
    return Material(
      color: color,
      borderRadius: BorderRadius.circular(10),
      child: InkWell(
        borderRadius: BorderRadius.circular(10),
        onTap: onTap,
        child: SizedBox(
          width: 46, height: 46,
          child: Center(
            child: Text(label,
              style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: Colors.white),
            ),
          ),
        ),
      ),
    );
  }
}
