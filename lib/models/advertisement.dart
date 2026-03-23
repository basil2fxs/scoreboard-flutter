/// Advertisement model — matches Python app's ad structure.
class AdRow {
  final String text;
  final String color;   // LED color code 1–7
  final String size;    // LED size code 1–4
  final String hAlign;
  final String vAlign;

  const AdRow({
    required this.text,
    this.color  = '7',
    this.size   = '2',
    this.hAlign = '1',
    this.vAlign = '2',  // '2' = Bottom on TF-F6
  });

  factory AdRow.fromJson(Map<String, dynamic> j) => AdRow(
    text  : j['text']    as String? ?? '',
    color : j['color']   as String? ?? '7',
    size  : j['size']    as String? ?? '2',
    hAlign: j['h_align'] as String? ?? '1',
    vAlign: j['v_align'] as String? ?? '2',
  );

  Map<String, dynamic> toJson() => {
    'text'   : text,
    'color'  : color,
    'size'   : size,
    'h_align': hAlign,
    'v_align': vAlign,
  };

  AdRow copyWith({String? text, String? color, String? size, String? hAlign, String? vAlign}) => AdRow(
    text  : text   ?? this.text,
    color : color  ?? this.color,
    size  : size   ?? this.size,
    hAlign: hAlign ?? this.hAlign,
    vAlign: vAlign ?? this.vAlign,
  );
}

class Advertisement {
  final String name;
  final List<AdRow> rows;
  final bool border;
  /// Total display rows chosen in the editor (1-4), including empty rows.
  /// Used to select the correct TF-F6 program: {1:7, 2:9, 3:11, 4:13} + border?1:0
  final int numRows;

  const Advertisement({
    required this.name,
    required this.rows,
    this.border  = false,
    this.numRows = 0,   // 0 = fall back to rows.length
  });

  factory Advertisement.fromJson(Map<String, dynamic> j) => Advertisement(
    name    : j['name']     as String? ?? 'Ad',
    border  : j['border']   as bool?   ?? false,
    numRows : j['num_rows'] as int?    ?? 0,
    rows    : (j['rows'] as List<dynamic>? ?? [])
        .map((r) => AdRow.fromJson(r as Map<String, dynamic>))
        .toList(),
  );

  Map<String, dynamic> toJson() => {
    'name'    : name,
    'border'  : border,
    'num_rows': numRows,
    'rows'    : rows.map((r) => r.toJson()).toList(),
  };

  Advertisement copyWith({String? name, List<AdRow>? rows, bool? border, int? numRows}) => Advertisement(
    name    : name    ?? this.name,
    rows    : rows    ?? this.rows,
    border  : border  ?? this.border,
    numRows : numRows ?? this.numRows,
  );
}

/// Per-ad UI state (checkbox + duration), keyed by ad name.
class AdSelection {
  final bool selected;
  final String duration; // seconds as string, default '4'

  const AdSelection({this.selected = false, this.duration = '4'});

  factory AdSelection.fromJson(Map<String, dynamic> j) => AdSelection(
    selected: j['selected'] as bool?   ?? false,
    duration: j['duration'] as String? ?? '4',
  );

  Map<String, dynamic> toJson() => {'selected': selected, 'duration': duration};

  AdSelection copyWith({bool? selected, String? duration}) => AdSelection(
    selected: selected ?? this.selected,
    duration: duration ?? this.duration,
  );
}
