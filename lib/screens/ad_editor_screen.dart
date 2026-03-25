import 'dart:async';
import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import '../models/advertisement.dart';
import '../providers/app_provider.dart';
import '../theme/app_theme.dart';

// ─── Character limit helpers ───────────────────────────────────────────────────

/// LED pixel widths per character for each size code (Small only).
const Map<String, int> kLedPixelW = {'4': 22, '3': 15, '2': 7, '1': 4};
const Map<String, int> kLedPixelH = {'4': 34, '3': 22, '2': 11, '1': 6};

/// Fixed character pixel widths derived from a 128-wide reference display:
///   XL (5 chars @ 128px) → 128/5 = 25.6 px/char
///   Large (7 chars @ 128px) → 128/7 ≈ 18.3 px/char
///   Medium (15 chars @ 128px) → 128/15 ≈ 8.53 px/char
/// These pixel widths are constant regardless of display size.
const Map<String, double> kCharPixelW = {
  '4': 128 / 5,   // XL
  '3': 128 / 7,   // Large
  '2': 128 / 15,  // Medium
};

int _charLimit(String size, int displayWidth) {
  final pw = kCharPixelW[size];
  if (pw != null) {
    // Fixed pixel width — scale count to actual display width
    return math.max(1, (displayWidth / pw).floor());
  }
  // Small — use LED pixel width directly
  final ledW = kLedPixelW[size] ?? 4;
  return math.max(1, displayWidth ~/ ledW);
}

/// Map LED colour code → Flutter Color.
Color _ledColor(String code) {
  switch (code) {
    case '1': return const Color(0xFFFF3333);
    case '2': return const Color(0xFF00DD00);
    case '3': return const Color(0xFFFFDD00);
    case '4': return const Color(0xFF4488FF);
    case '5': return const Color(0xFFCC44FF);
    case '6': return const Color(0xFF00EEFF);
    default:  return const Color(0xFFFFFFFF);
  }
}

// ─── Row data ─────────────────────────────────────────────────────────────────

class _RowData {
  String color;
  String size;
  String hAlign;
  String vAlign;

  _RowData({
    this.color  = '7',
    this.size   = '3',
    this.hAlign = '1',
    this.vAlign = '1', // Mid by default
  });
}

// ─── Screen ───────────────────────────────────────────────────────────────────

/// Create or edit a single advertisement.
/// Route arguments: Map<String, dynamic> {'index': int?} — null for new ad.
class AdEditorScreen extends StatefulWidget {
  const AdEditorScreen({super.key});

  @override
  State<AdEditorScreen> createState() => _AdEditorScreenState();
}

class _AdEditorScreenState extends State<AdEditorScreen>
    with SingleTickerProviderStateMixin {

  // ── Route arg ──────────────────────────────────────────────────────────────
  int? _editIndex;
  bool _initialized = false;

  // ── Editor state ───────────────────────────────────────────────────────────
  final _nameCtrl = TextEditingController();
  late final FocusNode _nameFocusNode;
  bool _nameError = false;

  late final List<TextEditingController> _textCtrs;
  late final List<FocusNode> _textFocusNodes;
  late final List<_RowData> _rows; // 4 slots (not all active)
  int  _numRows       = 1;
  int  _selectedRow   = 0;
  bool _editingActive = false; // true = cursor + keyboard shown
  bool _border        = false;

  // ── Border animation ───────────────────────────────────────────────────────
  late final AnimationController _borderAnim;
  double _borderOffset = 0;

  // ── Display config ─────────────────────────────────────────────────────────
  int _displayWidth  = 128;
  int _displayHeight = 64;
  bool _singleColour = false;

  // ── Font-size cache [sizeCode_numRows → pt] ────────────────────────────────
  final Map<String, double> _fsCache = {};
  double _lastCanvasWidth  = 0;
  double _lastCanvasHeight = 0;

  // ── Preview state ──────────────────────────────────────────────────────────
  bool _previewActive = false;
  late AppProvider _appProvider;

  // ── Cursor blink ───────────────────────────────────────────────────────────
  bool   _cursorVisible = false;
  Timer? _cursorTimer;

  // ── Unsaved-changes tracking ───────────────────────────────────────────────
  bool _hasEdited  = false;
  bool _trackEdits = false; // becomes true after initial load is done
  bool _saved      = false;

  // ─────────────────────────────────────────────────────────────────────────

  @override
  void initState() {
    super.initState();
    _nameFocusNode  = FocusNode();
    _textCtrs       = List.generate(4, (_) => TextEditingController());
    _textFocusNodes = List.generate(4, (_) => FocusNode());
    _rows           = List.generate(4, (_) => _RowData());

    // Listen for edits — only fires after _trackEdits becomes true
    _nameCtrl.addListener(_markEdited);
    for (final c in _textCtrs) c.addListener(_markEdited);

    // Reversed direction (subtracts 0.25/frame ≈ 15 units/sec) and slow
    _borderAnim = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 16),
    )..addListener(() {
        if (mounted) {
          setState(() => _borderOffset = (_borderOffset + 359.75) % 360);
        }
      });
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _appProvider = context.read<AppProvider>();
    if (_initialized) return;
    _initialized = true;

    _displayWidth  = _appProvider.config.displayWidth  ?? 128;
    _displayHeight = _appProvider.config.displayHeight ?? 64;
    _singleColour = _appProvider.config.singleColour;

    final args = ModalRoute.of(context)?.settings.arguments as Map<String, dynamic>?;
    _editIndex = args?['index'] as int?;

    if (_editIndex != null && _editIndex! < _appProvider.config.advertisements.length) {
      final ad = _appProvider.config.advertisements[_editIndex!];
      _nameCtrl.text = ad.name;
      _border        = ad.border;
      _numRows       = ad.rows.length.clamp(1, 4);
      for (int i = 0; i < ad.rows.length && i < 4; i++) {
        final r = ad.rows[i];
        _textCtrs[i].text = r.text;
        _rows[i] = _RowData(
            color: r.color, size: r.size, hAlign: r.hAlign, vAlign: r.vAlign);
      }
    }

    if (_border) _borderAnim.repeat();

    // Start tracking edits; row 0 is highlighted by default, no keyboard on load
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      _trackEdits = true;
    });
  }

  @override
  void dispose() {
    _stopPreviewIfActive();
    _cursorTimer?.cancel();
    _nameCtrl.dispose();
    _nameFocusNode.dispose();
    for (final c in _textCtrs)       c.dispose();
    for (final f in _textFocusNodes) f.dispose();
    _borderAnim.dispose();
    super.dispose();
  }

  // ─── Edit tracking ────────────────────────────────────────────────────────

  void _markEdited() {
    if (!_trackEdits || _hasEdited) return;
    setState(() => _hasEdited = true);
  }

  // ─── Font-size cache ──────────────────────────────────────────────────────

  /// Computes font sizes for each (size-code × numRows) combination.
  /// Font is sized as a fixed fraction of the zone height so that XL/L/M
  /// look proportionally correct — just like on the real LED panel, where
  /// character heights are fixed in pixels and screen width only changes
  /// how many characters fit across.
  void _ensureFontSizes(double cw, double ch) {
    if ((cw - _lastCanvasWidth).abs() < 1) return;
    _lastCanvasWidth  = cw;
    _lastCanvasHeight = ch;
    if (_displayHeight <= 0 || ch <= 0) return;
    // Font size in UI = LED pixel height × (canvas height / display height)
    final scaleY = ch / _displayHeight;
    for (final sz in ['2', '3', '4']) {
      final ledH = kLedPixelH[sz]?.toDouble() ?? 11.0;
      final fontSize = math.max(6.0, ledH * scaleY);
      // Store same font size for all numRows — font height is fixed by LED pixels
      for (int nr = 1; nr <= 4; nr++) {
        _fsCache['${sz}_$nr'] = fontSize;
      }
    }
  }

  // ─── Row management ───────────────────────────────────────────────────────

  int _limitFor(int rowIdx) => _charLimit(_rows[rowIdx].size, _displayWidth);

  /// Highlight a row without opening the keyboard (used by row-chip tabs).
  void _selectRow(int idx) {
    if (idx < 0 || idx >= _numRows) return;
    setState(() {
      _selectedRow   = idx;
      _editingActive = false;
    });
    _stopCursorBlink();
    FocusScope.of(context).unfocus();
  }

  /// Re-focus the active row's hidden TextField without changing cursor position.
  /// Only called after colour/size/align changes when keyboard is already up.
  void _refocusSelectedRow() {
    if (!_editingActive) return;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      _textFocusNodes[_selectedRow].requestFocus();
      SystemChannels.textInput.invokeMethod<void>('TextInput.show');
    });
  }

  /// Given a canvas X position, return the character-slot index closest to
  /// that position for [row], based on the row's hAlign and size.
  int _canvasTapToCharPos(Offset localPos, int row) {
    if (_lastCanvasWidth <= 0 || _displayWidth <= 0) {
      return _textCtrs[row].text.length;
    }
    final rowData = _rows[row];
    final cellW   = _lastCanvasWidth / _charLimit(rowData.size, _displayWidth);
    if (cellW <= 0 || !cellW.isFinite) return _textCtrs[row].text.length;

    final text = _textCtrs[row].text;
    final n    = text.length;

    double xBase;
    if (rowData.hAlign == '2')      xBase = _lastCanvasWidth - n * cellW;
    else if (rowData.hAlign == '3') xBase = 0.0;
    else                            xBase = (_lastCanvasWidth - n * cellW) / 2;

    final tapX = localPos.dx;
    if (tapX <= xBase)              return 0;
    if (tapX >= xBase + n * cellW) return n;
    return ((tapX - xBase) / cellW).round().clamp(0, n);
  }

  void _handleCanvasTap(TapDownDetails d) {
    if (_lastCanvasHeight <= 0 || _numRows <= 0) return;
    final zoneH = _lastCanvasHeight / _numRows;
    final row   = (d.localPosition.dy / zoneH).floor().clamp(0, _numRows - 1);

    if (row != _selectedRow) {
      // First click on a different row: highlight only, no keyboard
      setState(() {
        _selectedRow   = row;
        _editingActive = false;
      });
      _stopCursorBlink();
      FocusScope.of(context).unfocus();
      return;
    }

    // Second click (or click on already-selected row): activate editing
    final charPos = _canvasTapToCharPos(d.localPosition, row);
    setState(() => _editingActive = true);
    _startCursorBlink();
    _textFocusNodes[row].requestFocus();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      final ctrl = _textCtrs[row];
      ctrl.selection = TextSelection.collapsed(
          offset: charPos.clamp(0, ctrl.text.length));
      SystemChannels.textInput.invokeMethod<void>('TextInput.show');
    });
  }

  void _handleCanvasDoubleTap() {
    if (!_editingActive) return;
    final ctrl = _textCtrs[_selectedRow];
    if (ctrl.text.isEmpty) return;
    setState(() {
      ctrl.selection = TextSelection(
          baseOffset: 0, extentOffset: ctrl.text.length);
    });
  }

  void _handleCanvasDragStart(DragStartDetails d) {
    if (_lastCanvasHeight <= 0 || _numRows <= 0) return;
    if (!_editingActive) return;
    final zoneH   = _lastCanvasHeight / _numRows;
    final row     = (d.localPosition.dy / zoneH).floor().clamp(0, _numRows - 1);
    final charPos = _canvasTapToCharPos(d.localPosition, row);

    if (row != _selectedRow) {
      setState(() => _selectedRow = row);
      _textFocusNodes[row].requestFocus();
    }
    _startCursorBlink();
    final ctrl = _textCtrs[row];
    final clamped = charPos.clamp(0, ctrl.text.length);
    ctrl.selection = TextSelection.collapsed(offset: clamped);
    setState(() {});
  }

  void _handleCanvasDragUpdate(DragUpdateDetails d) {
    if (_lastCanvasHeight <= 0) return;
    final row  = _selectedRow;
    final ctrl = _textCtrs[row];
    if (!ctrl.selection.isValid) return;

    final charPos = _canvasTapToCharPos(d.localPosition, row)
        .clamp(0, ctrl.text.length);
    ctrl.selection = TextSelection(
      baseOffset  : ctrl.selection.baseOffset,
      extentOffset: charPos,
    );
    setState(() {});
  }

  void _addRow() {
    if (_numRows >= 4) return;
    setState(() {
      _numRows++;
      _selectedRow   = _numRows - 1;
      _editingActive = true;
    });
    _markEdited();
    _startCursorBlink();
    _textFocusNodes[_selectedRow].requestFocus();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      SystemChannels.textInput.invokeMethod<void>('TextInput.show');
    });
  }

  void _removeLastRow() {
    if (_numRows <= 1) return;
    setState(() {
      _textCtrs[_numRows - 1].text = '';
      _rows[_numRows - 1]          = _RowData();
      _numRows--;
      if (_selectedRow >= _numRows) {
        _selectedRow   = _numRows - 1;
        _editingActive = false;
      }
    });
    _markEdited();
  }

  void _toggleBorder(bool v) {
    setState(() => _border = v);
    _markEdited();
    if (v) {
      _borderAnim.repeat();
    } else {
      _borderAnim.stop();
      setState(() => _borderOffset = 0);
    }
  }

  // ─── Cursor blink ─────────────────────────────────────────────────────────

  void _startCursorBlink() {
    _cursorTimer?.cancel();
    setState(() => _cursorVisible = true);
    _cursorTimer = Timer.periodic(const Duration(milliseconds: 530), (_) {
      if (mounted) setState(() => _cursorVisible = !_cursorVisible);
    });
  }

  void _stopCursorBlink() {
    _cursorTimer?.cancel();
    _cursorTimer = null;
    if (_cursorVisible) setState(() => _cursorVisible = false);
  }

  // ─── Build active rows from current state ─────────────────────────────────

  List<AdRow> _buildActiveRows() {
    return [
      for (int i = 0; i < _numRows; i++)
        if (_textCtrs[i].text.trim().isNotEmpty)
          AdRow(
            text  : _textCtrs[i].text,
            color : _singleColour ? '1' : _rows[i].color,
            size  : _rows[i].size,
            hAlign: _rows[i].hAlign,
            vAlign: _rows[i].vAlign,
          ),
    ];
  }

  // ─── Preview ──────────────────────────────────────────────────────────────

  void _stopPreviewIfActive() {
    if (!_previewActive) return;
    _previewActive = false;
    _appProvider.stopAdPreview();
  }

  void _previewCurrentAd() {
    final rows = _buildActiveRows();
    if (rows.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
        content: Text('Add text to at least one row first.'),
        backgroundColor: AppColors.danger,
      ));
      return;
    }
    setState(() => _previewActive = true);
    _appProvider.previewAd(
        Advertisement(name: 'Preview', rows: rows, border: _border, numRows: _numRows));
  }

  // ─── Save ─────────────────────────────────────────────────────────────────

  void _save() {
    final name = _nameCtrl.text.trim();
    if (name.isEmpty) {
      setState(() => _nameError = true);
      _nameFocusNode.requestFocus();
      return;
    }
    final activeRows = _buildActiveRows();
    if (activeRows.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
        content: Text('Add some text to at least one row first.'),
        backgroundColor: AppColors.danger,
      ));
      return;
    }
    _stopPreviewIfActive();
    _saved = true; // suppress unsaved-changes prompt on pop
    _appProvider.saveAdvertisement(
      Advertisement(name: name, rows: activeRows, border: _border, numRows: _numRows),
      editIndex: _editIndex,
    );
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text('"$name" saved!'),
      backgroundColor: AppColors.success,
    ));
    Navigator.pop(context);
  }

  // ─── Unsaved-changes dialog ───────────────────────────────────────────────

  void _handlePopAttempt() async {
    // No edits or already saved → just pop
    if (!_hasEdited || _saved) {
      _stopPreviewIfActive();
      Navigator.pop(context);
      return;
    }
    // Ask user
    final leave = await showDialog<bool>(
      context: context,
      builder: (d) => AlertDialog(
        backgroundColor: AppColors.surface,
        title: const Text('Unsaved Changes'),
        content: const Text(
            'You have unsaved changes. Leave without saving?'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(d, false),
              child: const Text('Stay')),
          ElevatedButton(
            onPressed: () => Navigator.pop(d, true),
            style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.danger),
            child: const Text('Leave'),
          ),
        ],
      ),
    );
    if (leave == true && mounted) {
      _stopPreviewIfActive();
      Navigator.pop(context);
    }
  }

  // ─── Build ────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    final rowData   = _rows[_selectedRow];
    final limit     = _limitFor(_selectedRow);
    final textLen   = _textCtrs[_selectedRow].text.length;
    final remaining = limit - textLen;

    return PopScope(
      canPop: false, // always intercept to handle unsaved-changes check
      onPopInvoked: (didPop) {
        if (!didPop) _handlePopAttempt();
      },
      child: Scaffold(
        appBar: AppBar(
          title: Text(_editIndex != null
              ? 'Edit Advertisement'
              : 'New Advertisement'),
          leading: BackButton(
              onPressed: () => Navigator.maybePop(context)),
          actions: [
            Padding(
              padding: const EdgeInsets.only(right: 8),
              child: ElevatedButton(
                onPressed: _save,
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.success,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(
                      horizontal: 18, vertical: 8),
                  textStyle: const TextStyle(
                      fontSize: 14, fontWeight: FontWeight.bold),
                  elevation: 0,
                ),
                child: const Text('Save'),
              ),
            ),
          ],
        ),
        body: ListView(
          padding: const EdgeInsets.only(bottom: 36),
          children: [

            // ── Ad Name ────────────────────────────────────────────────────
            Padding(
              padding: const EdgeInsets.fromLTRB(12, 12, 12, 0),
              child: TextField(
                controller: _nameCtrl,
                focusNode : _nameFocusNode,
                style: const TextStyle(color: Colors.white, fontSize: 15),
                onChanged: (v) {
                  if (_nameError && v.isNotEmpty) {
                    setState(() => _nameError = false);
                  }
                },
                decoration: InputDecoration(
                  labelText: 'Advertisement Name',
                  hintText : 'e.g. Sponsor Name',
                  filled   : true,
                  fillColor: _nameError
                      ? const Color(0xFF3A1A1A)
                      : AppColors.surfaceHigh,
                  labelStyle: TextStyle(
                      color: _nameError
                          ? AppColors.dangerBright
                          : AppColors.textSecondary),
                  enabledBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(8),
                    borderSide: BorderSide(
                        color: _nameError
                            ? AppColors.danger
                            : AppColors.surfaceBorder),
                  ),
                  focusedBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(8),
                    borderSide: BorderSide(
                        color: _nameError
                            ? AppColors.dangerBright
                            : AppColors.accent,
                        width: 2),
                  ),
                  border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(8)),
                ),
              ),
            ),
            if (_nameError)
              const Padding(
                padding: EdgeInsets.fromLTRB(12, 4, 12, 0),
                child: Text('Name is required',
                    style: TextStyle(
                        color: AppColors.dangerBright, fontSize: 12)),
              ),

            const SizedBox(height: 12),

            // ── Live Preview canvas ────────────────────────────────────────
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  LayoutBuilder(builder: (ctx, constraints) {
                    final screenH = MediaQuery.of(ctx).size.height;
                    final aspect  = _displayHeight / _displayWidth;
                    double cw = constraints.maxWidth;
                    double ch = cw * aspect;
                    // For portrait/square displays, cap height so it doesn't
                    // dominate the screen. Landscape displays fill full width.
                    if (_displayHeight >= _displayWidth && ch > screenH * 0.40) {
                      ch = screenH * 0.40;
                      cw = ch / aspect;
                    }
                    _ensureFontSizes(cw, ch);

                    return Center(
                      child: SizedBox(
                        width: cw, height: ch,
                        child: Stack(
                          children: [
                        // Canvas with tap + drag-to-select detection
                        GestureDetector(
                          onTapDown             : _handleCanvasTap,
                          onDoubleTap           : _handleCanvasDoubleTap,
                          onHorizontalDragStart : _handleCanvasDragStart,
                          onHorizontalDragUpdate: _handleCanvasDragUpdate,
                          child: Container(
                            width : cw,
                            height: ch,
                            decoration: BoxDecoration(
                              color: Colors.black,
                              borderRadius: BorderRadius.circular(6),
                              border: Border.all(
                                  color: _border
                                      ? const Color(0xFF555555)
                                      : AppColors.surfaceBorder,
                                  width: 2),
                            ),
                            child: ClipRRect(
                              borderRadius: BorderRadius.circular(4),
                              child: CustomPaint(
                                size: Size(cw, ch),
                                painter: () {
                                  final sel = _textCtrs[_selectedRow].selection;
                                  final txtLen = _textCtrs[_selectedRow].text.length;
                                  final curPos = (sel.isValid && sel.extentOffset >= 0)
                                      ? sel.extentOffset.clamp(0, txtLen)
                                      : txtLen;
                                  final selStart = (sel.isValid && !sel.isCollapsed)
                                      ? sel.start : -1;
                                  final selEnd   = (sel.isValid && !sel.isCollapsed)
                                      ? sel.end   : -1;
                                  return _AdPreviewPainter(
                                    numRows       : _numRows,
                                    selectedRow   : _selectedRow,
                                    rows          : _rows,
                                    texts         : List.generate(
                                        4, (i) => _textCtrs[i].text),
                                    displayWidth  : _displayWidth,
                                    displayHeight : _displayHeight,
                                    fontSizes     : Map.from(_fsCache),
                                    border        : _border,
                                    borderOffset  : _borderOffset,
                                    cursorVisible : _cursorVisible && _editingActive,
                                    cursorCharPos : curPos,
                                    selectionStart: selStart,
                                    selectionEnd  : selEnd,
                                    singleColour  : _singleColour,
                                  );
                                }(),
                              ),
                            ),
                          ),
                        ),

                        // Max chars indicator — bottom-right corner of canvas
                        Positioned(
                          right: 6,
                          bottom: 4,
                          child: Text(
                            '$textLen/$limit',
                            style: TextStyle(
                              fontSize  : 11,
                              fontWeight: FontWeight.bold,
                              color: remaining < 0
                                  ? AppColors.dangerBright
                                  : remaining <= 2
                                      ? AppColors.warning
                                      : Colors.white.withOpacity(0.45),
                            ),
                          ),
                        ),

                        // Invisible text fields — one per row for direct typing
                        ...List.generate(4, (i) => Positioned(
                          top: 0, left: 0,
                          child: SizedBox(
                            width: 0, height: 0,
                            child: IgnorePointer(
                              child: Opacity(
                                opacity: 0,
                                child: OverflowBox(
                                  maxWidth  : 300,
                                  maxHeight : 60,
                                  alignment : Alignment.topLeft,
                                  child: TextField(
                                    controller: _textCtrs[i],
                                    focusNode : _textFocusNodes[i],
                                    style: const TextStyle(fontSize: 14),
                                    decoration: const InputDecoration(
                                      border: InputBorder.none,
                                      contentPadding: EdgeInsets.zero,
                                    ),
                                    onChanged: (_) => setState(() {}),
                                    inputFormatters: [
                                      FilteringTextInputFormatter.allow(
                                          RegExp(r'[\x20-\x7E]')),
                                      LengthLimitingTextInputFormatter(
                                          _limitFor(i)),
                                    ],
                                  ),
                                ),
                              ),
                            ),
                          ),
                        )),
                          ],
                        ),     // Stack
                      ),       // SizedBox
                    );         // Center
                  }),

                  // Info bar
                  Padding(
                    padding: const EdgeInsets.only(top: 5),
                    child: Row(
                      children: [
                        Text(
                          '${_displayWidth}×${_displayHeight}',
                          style: const TextStyle(
                              fontSize: 11,
                              color   : AppColors.textMuted),
                        ),
                        const SizedBox(width: 6),
                        Flexible(
                          child: Text(
                            '· Row ${_selectedRow + 1}',
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                                fontSize: 11,
                                color   : AppColors.textSecondary),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 10),

            // ── Row Tabs ───────────────────────────────────────────────────
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12),
              child: Wrap(
                spacing: 6,
                runSpacing: 6,
                crossAxisAlignment: WrapCrossAlignment.center,
                children: [
                  // ROWS label
                  const Text('ROWS',
                      style: TextStyle(
                          fontSize    : 18,
                          fontWeight  : FontWeight.w900,
                          color       : Colors.white,
                          letterSpacing: 1.0)),
                  // Row chips
                  ...List.generate(_numRows, (i) {
                    final sel = i == _selectedRow;
                    return GestureDetector(
                      onTap: () => _selectRow(i),
                      child: Container(
                        width : 38, height: 38,
                        decoration: BoxDecoration(
                          color: sel ? AppColors.accent : AppColors.surfaceHigh,
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(
                              color: sel ? AppColors.accent : AppColors.surfaceBorder),
                        ),
                        child: Center(
                          child: Text('${i + 1}',
                              style: TextStyle(
                                  fontSize  : 16,
                                  fontWeight: FontWeight.bold,
                                  color: sel ? Colors.white : AppColors.textSecondary)),
                        ),
                      ),
                    );
                  }),
                  // + ROW and − ROW — always side-by-side, dimmed when locked
                  Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Opacity(
                        opacity: _numRows >= 4 ? 0.35 : 1.0,
                        child: IgnorePointer(
                          ignoring: _numRows >= 4,
                          child: GestureDetector(
                            onTap: _addRow,
                            child: Container(
                              height: 38,
                              padding: const EdgeInsets.symmetric(horizontal: 14),
                              decoration: BoxDecoration(
                                color: const Color(0xFF003300),
                                borderRadius: BorderRadius.circular(8),
                                border: Border.all(color: AppColors.success.withOpacity(0.5)),
                              ),
                              child: const Center(
                                child: Text('+ ROW',
                                    style: TextStyle(
                                        fontSize  : 13,
                                        fontWeight: FontWeight.bold,
                                        color     : AppColors.success)),
                              ),
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(width: 6),
                      Opacity(
                        opacity: _numRows <= 1 ? 0.35 : 1.0,
                        child: IgnorePointer(
                          ignoring: _numRows <= 1,
                          child: GestureDetector(
                            onTap: _removeLastRow,
                            child: Container(
                              height: 38,
                              padding: const EdgeInsets.symmetric(horizontal: 14),
                              decoration: BoxDecoration(
                                color: const Color(0xFF330000),
                                borderRadius: BorderRadius.circular(8),
                                border: Border.all(color: AppColors.danger.withOpacity(0.5)),
                              ),
                              child: const Center(
                                child: Text('− ROW',
                                    style: TextStyle(
                                        fontSize  : 13,
                                        fontWeight: FontWeight.bold,
                                        color     : AppColors.danger)),
                              ),
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),

            const SizedBox(height: 8),

            // ── Style Controls ─────────────────────────────────────────────
            Container(
              margin : const EdgeInsets.symmetric(horizontal: 12),
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: AppColors.surface,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AppColors.surfaceBorder),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [

                  // ── Size ─────────────────────────────────────────────────
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.center,
                    children: [
                      const _Label('SIZE'),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Row(
                          children: kLedSizes
                              .where((s) => s.code != '1')
                              .map((ls) {
                            final sel = rowData.size == ls.code;
                            final lim = _charLimit(ls.code, _displayWidth);
                            return Expanded(
                              child: Padding(
                                padding: const EdgeInsets.symmetric(
                                    horizontal: 3),
                                child: GestureDetector(
                                  onTap: () {
                                    setState(() {
                                      _rows[_selectedRow].size = ls.code;
                                      if (_textCtrs[_selectedRow]
                                              .text
                                              .length >
                                          lim) {
                                        _textCtrs[_selectedRow].text =
                                            _textCtrs[_selectedRow]
                                                .text
                                                .substring(0, lim);
                                      }
                                    });
                                    _markEdited();
                                    _refocusSelectedRow();
                                  },
                                  child: Container(
                                    padding: const EdgeInsets.symmetric(
                                        vertical: 6),
                                    decoration: BoxDecoration(
                                      color: sel
                                          ? AppColors.accent
                                          : AppColors.surfaceHigh,
                                      borderRadius:
                                          BorderRadius.circular(8),
                                    ),
                                    child: Column(
                                      mainAxisSize: MainAxisSize.min,
                                      children: [
                                        Text(ls.label,
                                            style: TextStyle(
                                                fontSize  : 14,
                                                fontWeight: FontWeight.bold,
                                                color: sel
                                                    ? Colors.white
                                                    : AppColors
                                                        .textSecondary)),
                                        Text('$lim ch',
                                            style: TextStyle(
                                                fontSize: 10,
                                                color: sel
                                                    ? Colors.white70
                                                    : AppColors.textMuted)),
                                      ],
                                    ),
                                  ),
                                ),
                              ),
                            );
                          }).toList(),
                        ),
                      ),
                    ],
                  ),

                  const SizedBox(height: 14),

                  // ── Colour ───────────────────────────────────────────────
                  if (!_singleColour) ...[
                    const _Label('COLOUR'),
                    const SizedBox(height: 8),
                    Wrap(
                      spacing: 8, runSpacing: 8,
                      children: kLedColors.map((lc) {
                        final sel = rowData.color == lc.code;
                        return GestureDetector(
                          onTap: () {
                            setState(() => _rows[_selectedRow].color = lc.code);
                            _markEdited();
                            _refocusSelectedRow();
                          },
                          child: Container(
                            width : 40, height: 40,
                            decoration: BoxDecoration(
                              color: lc.color,
                              borderRadius: BorderRadius.circular(8),
                              border: Border.all(
                                  color: sel ? Colors.white : Colors.transparent,
                                  width: 2.5),
                            ),
                            child: sel
                                ? const Icon(Icons.check,
                                    color: Colors.black, size: 16)
                                : null,
                          ),
                        );
                      }).toList(),
                    ),
                    const SizedBox(height: 10),
                  ],

                  // ── Border ───────────────────────────────────────────────
                  Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const _Label('BORDER'),
                      Switch(
                        value    : _border,
                        onChanged: _toggleBorder,
                        activeColor: AppColors.accent,
                        materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),

                  // ── H-Align + V-Align on one compact row ─────────────────
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.center,
                    children: [
                      // H-ALIGN
                      Expanded(
                        child: Row(children: [
                          _AlignBtn(
                              icon    : Icons.format_align_left,
                              label   : 'L',
                              code    : '3',
                              selected: rowData.hAlign,
                              onTap   : (v) {
                                setState(() => _rows[_selectedRow].hAlign = v);
                                _markEdited();
                                _refocusSelectedRow();
                              }),
                          const SizedBox(width: 4),
                          _AlignBtn(
                              icon    : Icons.format_align_center,
                              label   : 'C',
                              code    : '1',
                              selected: rowData.hAlign,
                              onTap   : (v) {
                                setState(() => _rows[_selectedRow].hAlign = v);
                                _markEdited();
                                _refocusSelectedRow();
                              }),
                          const SizedBox(width: 4),
                          _AlignBtn(
                              icon    : Icons.format_align_right,
                              label   : 'R',
                              code    : '2',
                              selected: rowData.hAlign,
                              onTap   : (v) {
                                setState(() => _rows[_selectedRow].hAlign = v);
                                _markEdited();
                                _refocusSelectedRow();
                              }),
                        ]),
                      ),
                      // Divider
                      Container(
                          width: 1, height: 36,
                          color: AppColors.surfaceBorder,
                          margin: const EdgeInsets.symmetric(horizontal: 10)),
                      // V-ALIGN
                      Expanded(
                        child: Row(children: [
                          _AlignBtn(
                              icon    : Icons.vertical_align_top,
                              label   : 'Top',
                              code    : '3',
                              selected: rowData.vAlign,
                              onTap   : (v) {
                                setState(() => _rows[_selectedRow].vAlign = v);
                                _markEdited();
                                _refocusSelectedRow();
                              }),
                          const SizedBox(width: 4),
                          _AlignBtn(
                              icon    : Icons.vertical_align_center,
                              label   : 'Mid',
                              code    : '1',
                              selected: rowData.vAlign,
                              onTap   : (v) {
                                setState(() => _rows[_selectedRow].vAlign = v);
                                _markEdited();
                                _refocusSelectedRow();
                              }),
                          const SizedBox(width: 4),
                          _AlignBtn(
                              icon    : Icons.vertical_align_bottom,
                              label   : 'Bot',
                              code    : '2',
                              selected: rowData.vAlign,
                              onTap   : (v) {
                                setState(() => _rows[_selectedRow].vAlign = v);
                                _markEdited();
                                _refocusSelectedRow();
                              }),
                        ]),
                      ),
                    ],
                  ),
                ],
              ),
            ),

            const SizedBox(height: 12),

            // ── Preview Button ─────────────────────────────────────────────
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12),
              child: SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  onPressed: _previewCurrentAd,
                  icon : Icon(
                    _previewActive
                        ? Icons.refresh
                        : Icons.preview_outlined,
                    size: 18,
                  ),
                  label: Text(
                    _previewActive
                        ? 'Update Preview on Display'
                        : 'Preview on Display',
                  ),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: _previewActive
                        ? AppColors.accent
                        : const Color(0xFF006622),
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    textStyle: const TextStyle(
                        fontSize: 15, fontWeight: FontWeight.bold),
                    elevation: 0,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ─── Preview Painter ──────────────────────────────────────────────────────────

class _AdPreviewPainter extends CustomPainter {
  final int numRows;
  final int selectedRow;
  final List<_RowData> rows;
  final List<String> texts;
  final int displayWidth;
  final int displayHeight;
  final Map<String, double> fontSizes;
  final bool border;
  final double borderOffset;
  final bool cursorVisible;
  final int  cursorCharPos;   // actual cursor offset in text
  final int  selectionStart;  // -1 if no selection
  final int  selectionEnd;    // -1 if no selection
  final bool singleColour;

  _AdPreviewPainter({
    required this.numRows,
    required this.selectedRow,
    required this.rows,
    required this.texts,
    required this.displayWidth,
    required this.displayHeight,
    required this.fontSizes,
    required this.border,
    required this.borderOffset,
    required this.cursorVisible,
    required this.cursorCharPos,
    this.selectionStart = -1,
    this.selectionEnd   = -1,
    this.singleColour   = false,
  });

  /// Returns the pixel-accurate cell height for a size code given scaleY.
  /// scaleY = canvasHeight / displayHeight.
  double _cellH(String sizeCode, double scaleY) {
    if (scaleY <= 0 || !scaleY.isFinite) return 6.0;
    final h = (kLedPixelH[sizeCode] ?? 11) * scaleY;
    return (h.isFinite && h > 0) ? math.max(6.0, h) : 6.0;
  }

  @override
  void paint(Canvas canvas, Size size) {
    if (size.width <= 0 || size.height <= 0 ||
        displayWidth <= 0 || displayHeight <= 0) return;

    // Per-pixel scale factors: canvas pixels per LED pixel
    final scaleX = size.width  / displayWidth;
    final scaleY = size.height / displayHeight;
    final zoneH  = size.height / numRows;

    // Selected-row highlight
    canvas.drawRect(
      Rect.fromLTWH(0, selectedRow * zoneH, size.width, zoneH),
      Paint()..color = const Color(0xFF1a3a5a),
    );

    // Zone dividers (dashed)
    final divPaint = Paint()
      ..color = const Color(0xFF444444)
      ..strokeWidth = 1;
    for (int z = 1; z < numRows; z++) {
      final y = z * zoneH;
      double x = 0;
      while (x < size.width) {
        canvas.drawLine(
            Offset(x, y), Offset(math.min(x + 6, size.width), y), divPaint);
        x += 10;
      }
    }

    // ── Selection highlight (drawn before text so text renders on top) ──
    if (selectionStart >= 0 && selectionEnd >= 0 &&
        selectionStart != selectionEnd) {
      final row     = rows[selectedRow];
      final limit   = _charLimit(row.size, displayWidth);
      final cellW   = size.width / limit;
      final textLen = math.min(texts[selectedRow].length, limit);
      final sStart  = math.min(selectionStart, selectionEnd).clamp(0, textLen);
      final sEnd    = math.max(selectionStart, selectionEnd).clamp(0, textLen);
      final zoneTop = selectedRow * zoneH;

      double selXBase;
      if (row.hAlign == '2')      selXBase = size.width - textLen * cellW;
      else if (row.hAlign == '3') selXBase = 0.0;
      else                        selXBase = (size.width - textLen * cellW) / 2;

      if (selXBase.isFinite) {
        final selLeft  = (selXBase + sStart * cellW).clamp(0.0, size.width);
        final selRight = (selXBase + sEnd   * cellW).clamp(0.0, size.width);
        canvas.drawRect(
          Rect.fromLTWH(selLeft, zoneTop, selRight - selLeft, zoneH),
          Paint()..color = Colors.blue.withOpacity(0.45),
        );
      }
    }

    // Text rows
    for (int i = 0; i < numRows; i++) {
      final row   = rows[i];
      final text  = texts[i];
      final limit = _charLimit(row.size, displayWidth);
      final color = singleColour ? _ledColor('1') : _ledColor(row.color);

      // Cell width evenly divides canvas across the character limit
      final cellW    = size.width / limit;
      final cellH    = _cellH(row.size, scaleY);
      final fontSize = math.max(6.0, cellH);

      final zoneTop    = i * zoneH;
      final zoneBottom = (i + 1) * zoneH;

      // Character centre Y anchored to LED cell height, not font metrics.
      // vAlign '3' = top  → char top flush with zone top
      // vAlign '2' = bot  → char bottom flush with zone bottom
      // vAlign '1' = mid  → char centred in zone
      final double y;
      if (row.vAlign == '3') {
        y = zoneTop + cellH / 2;
      } else if (row.vAlign == '2') {
        y = zoneBottom - cellH / 2;
      } else {
        y = (zoneTop + zoneBottom) / 2;
      }

      if (text.isEmpty) continue;

      final displayText = text.substring(0, math.min(text.length, limit));

      // Clip the whole row to its zone, then draw each char in its LED cell
      canvas.save();
      canvas.clipRect(Rect.fromLTWH(0, zoneTop, size.width,
          math.max(0.001, zoneH)));
      _drawCharsEvenly(canvas, displayText, y, size.width, cellW, cellH,
          row.hAlign, color, fontSize);
      canvas.restore();
    }

    // ── Blinking cursor for selected row ────────────────────────────────
    if (cursorVisible) {
      final row     = rows[selectedRow];
      final limit   = _charLimit(row.size, displayWidth);
      final textLen = math.min(texts[selectedRow].length, limit);
      final curPos  = cursorCharPos.clamp(0, textLen);

      final cellW  = size.width / limit;
      final cellH  = _cellH(row.size, scaleY);

      final zoneTop    = selectedRow * zoneH;
      final zoneBottom = (selectedRow + 1) * zoneH;

      final double cy;
      if (row.vAlign == '3') {
        cy = zoneTop + cellH / 2;
      } else if (row.vAlign == '2') {
        cy = zoneBottom - cellH / 2;
      } else {
        cy = (zoneTop + zoneBottom) / 2;
      }

      // xBase computed from TOTAL text length (not cursor pos) for correct alignment
      double xBase;
      if (row.hAlign == '2')      xBase = size.width - textLen * cellW;
      else if (row.hAlign == '3') xBase = 0.0;
      else                        xBase = (size.width - textLen * cellW) / 2;

      if (xBase.isFinite) {
        final maxCx = math.max(2.0, size.width - 2.0);
        final cx = (xBase + curPos * cellW).clamp(2.0, maxCx);
        // Cursor spans the full LED cell height
        canvas.drawLine(
          Offset(cx, cy - cellH / 2),
          Offset(cx, cy + cellH / 2),
          Paint()
            ..color = Colors.white.withOpacity(0.85)
            ..strokeWidth = 2.0,
        );
      }
    }

    // Animated striped border (drawn on top)
    if (border) _drawStripedBorder(canvas, size);
  }

  /// Each character is drawn centred inside its LED pixel cell (cellW × cellH).
  /// The character is clipped to that cell, so overflow is cut off accurately.
  void _drawCharsEvenly(Canvas canvas, String text, double cellCenterY,
      double w, double cellW, double cellH, String hAlign, Color color,
      double fontSize) {
    if (cellW <= 0 || !cellW.isFinite) return;
    if (cellH <= 0 || !cellH.isFinite) return;
    if (fontSize <= 0 || !fontSize.isFinite) return;
    if (!cellCenterY.isFinite || !w.isFinite) return;

    final n = text.length;
    if (n == 0) return;

    double xBase;
    if (hAlign == '2')      xBase = w - n * cellW;
    else if (hAlign == '3') xBase = 0.0;
    else                    xBase = (w - n * cellW) / 2;

    if (!xBase.isFinite) return;

    final cellTop = cellCenterY - cellH / 2;

    for (int ci = 0; ci < n; ci++) {
      final cellLeft = xBase + ci * cellW;
      if (!cellLeft.isFinite) continue;

      final tp = TextPainter(
        text: TextSpan(
          text: text[ci],
          style: TextStyle(
            color     : color,
            fontSize  : fontSize,
            fontWeight: FontWeight.normal,
            fontFamily: 'Times New Roman',
            height    : 1.0, // no extra line-height padding
          ),
        ),
        textDirection: TextDirection.ltr,
      )..layout();

      // Only clip vertically to the LED cell height — never horizontally,
      // so characters are never cut off sideways by their neighbours.
      // The outer zone clipRect already handles horizontal canvas bounds.
      canvas.save();
      canvas.clipRect(Rect.fromLTWH(
        0,
        cellTop,
        w,
        math.max(0.001, cellH),
      ));

      // Center the rendered glyph within the cell
      final paintX = cellLeft + cellW / 2 - tp.width  / 2;
      final paintY = cellCenterY          - tp.height / 2;
      if (paintX.isFinite && paintY.isFinite) {
        tp.paint(canvas, Offset(paintX, paintY));
      }

      canvas.restore();
    }
  }

  /// Reversed slow counter-clockwise animated striped border.
  void _drawStripedBorder(Canvas canvas, Size size) {
    const bw   = 4.0;
    const slen = 10.0;
    final sc = [
      const Color(0xFFCC0000),
      const Color(0xFF00AA00),
      const Color(0xFFCCCC00),
    ];

    void seg(Rect rect, double dist) {
      final idx = (((dist + borderOffset) / slen) % 3).floor().clamp(0, 2);
      canvas.drawRect(rect, Paint()..color = sc[idx]);
    }

    var d = 0.0;
    var x = 0.0;
    while (x < size.width) {
      final xe = math.min(x + slen, size.width);
      seg(Rect.fromLTWH(x, 0, xe - x, bw), d); d += xe - x; x = xe;
    }
    var yy = 0.0;
    while (yy < size.height) {
      final ye = math.min(yy + slen, size.height);
      seg(Rect.fromLTWH(size.width - bw, yy, bw, ye - yy), d);
      d += ye - yy; yy = ye;
    }
    x = size.width;
    while (x > 0) {
      final xe = math.max(x - slen, 0.0);
      seg(Rect.fromLTWH(xe, size.height - bw, x - xe, bw), d);
      d += x - xe; x = xe;
    }
    yy = size.height;
    while (yy > 0) {
      final ye = math.max(yy - slen, 0.0);
      seg(Rect.fromLTWH(0, ye, bw, yy - ye), d); d += yy - ye; yy = ye;
    }
  }

  @override
  bool shouldRepaint(_AdPreviewPainter old) {
    if (old.numRows        != numRows        ||
        old.selectedRow    != selectedRow    ||
        old.border         != border         ||
        old.cursorVisible  != cursorVisible  ||
        old.cursorCharPos  != cursorCharPos  ||
        old.selectionStart != selectionStart ||
        old.selectionEnd   != selectionEnd   ||
        old.singleColour   != singleColour   ||
        old.displayWidth   != displayWidth   ||
        old.displayHeight  != displayHeight  ||
        (old.borderOffset - borderOffset).abs() > 0.01) return true;
    for (int i = 0; i < 4; i++) {
      if (old.texts[i] != texts[i]) return true;
      if (old.rows[i].color  != rows[i].color  ||
          old.rows[i].size   != rows[i].size   ||
          old.rows[i].hAlign != rows[i].hAlign ||
          old.rows[i].vAlign != rows[i].vAlign) return true;
    }
    return false;
  }
}

// ─── Small helpers ─────────────────────────────────────────────────────────────

class _Label extends StatelessWidget {
  final String text;
  const _Label(this.text);
  @override
  Widget build(BuildContext context) => Text(
        text,
        style: const TextStyle(
            fontSize  : 11,
            fontWeight: FontWeight.bold,
            color     : AppColors.textMuted,
            letterSpacing: 0.8),
      );
}

class _AlignBtn extends StatelessWidget {
  final IconData icon;
  final String label;
  final String code;
  final String selected;
  final ValueChanged<String> onTap;
  const _AlignBtn({
    required this.icon,
    required this.label,
    required this.code,
    required this.selected,
    required this.onTap,
  });
  @override
  Widget build(BuildContext context) {
    final sel = selected == code;
    return Expanded(
      child: GestureDetector(
        onTap: () => onTap(code),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 6),
          decoration: BoxDecoration(
            color: sel ? AppColors.accent : AppColors.surfaceHigh,
            borderRadius: BorderRadius.circular(8),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon,
                  size : 18,
                  color: sel ? Colors.white : AppColors.textSecondary),
              const SizedBox(height: 2),
              Text(label,
                  style: TextStyle(
                      fontSize  : 11,
                      fontWeight: FontWeight.bold,
                      color: sel
                          ? Colors.white
                          : AppColors.textSecondary)),
            ],
          ),
        ),
      ),
    );
  }
}
