"""Minimal formatted XLSX writer — stdlib only (zipfile + XML strings).

An .xlsx file is a zip of XML parts. This writer produces a real,
Excel/Sheets-openable workbook with the formatting a deal team expects
from a template export — a title/section/column style hierarchy, colored
honesty-basis chips, $ and % number formats, frozen header rows,
autofilter dropdowns, zebra-banded data rows, column widths, multiple
sheets — without adding openpyxl as a runtime dep ("no new runtime
dependencies", CLAUDE.md).

Deliberately small: cell values are numbers or inline strings, styles are
a fixed palette. That covers the IFT / TAM-SAM templates (and future
tabular exports); it is not a general spreadsheet library.

Public API:
    Sheet(name, rows, *, col_widths=None, freeze_rows=0, freeze_cols=0,
          autofilter=None, merges=None, band_rows=None)
      rows: list of rows; each cell is either a plain value or a
      (value, style) tuple with style in
      {"header","text","money","money2","pct","num","num2","mult",
       "input","input_pct","label","title","subtitle","banner","note",
       "basis_gov","basis_sourced","basis_academic","basis_illustrative",
       "basis_framework"}.
      freeze_rows / freeze_cols: keep the top N rows / left N cols visible
        on scroll (freeze the column-header row so it never scrolls away).
      autofilter: an A1 range string ("A4:K21") — adds Excel filter
        dropdowns over that block. None = no filter.
      merges: list of A1 range strings ("A1:E1") — merged cells (used for
        the title banner spanning the table width).
      band_rows: (first_row, last_row) 1-based inclusive — zebra-bands the
        even rows in that range (plain content cells only; styled chips /
        headers keep their own fill).
    basis_style(token) -> the chip style name for a GOV / SOURCED /
      ACADEMIC / ILLUSTRATIVE / FRAMEWORK basis label ("text" if unknown).
    F(expr) — a live-formula cell value (expr WITHOUT the leading "=").
      Formulas are opt-in via this wrapper, never inferred from a
      leading "=" in a string: every CSV export in this codebase is
      defanged against Excel formula injection, and silently turning
      strings into formulas here would reopen that hole for any
      template that interpolates partner-supplied text.
    Link(text, url) — a clickable hyperlink cell.
    write_xlsx(sheets) -> bytes  (byte-for-byte deterministic).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional, Sequence, Tuple
from xml.sax.saxutils import escape
import io
import zipfile


@dataclass(frozen=True)
class F:
    """Live Excel formula. ``F("SUM(B2:B5)")`` renders as ``=SUM(B2:B5)``."""
    expr: str


@dataclass(frozen=True)
class Link:
    """A clickable hyperlink cell. ``Link("MMT study", "https://…/ift-study")``
    renders the visible ``text`` as a blue underlined link to ``url``.

    Opt-in (like :class:`F`) so a plain string is never silently turned into a
    hyperlink — the URL travels separately in the workbook's relationship parts,
    so a partner-supplied string can never inject one."""
    text: str
    url: str


# Style ids map to cellXfs entries in _STYLES_XML below (order matters — the
# existing 0-13 ids are relied on by every other export that imports this
# writer, so NEW styles are only ever APPENDED, never reordered).
# The "input*" styles render blue — the banker convention (blue =
# hardcoded assumption you may edit, black = formula/derived) that deal
# teams expect in any model template they download. The "basis_*" chips carry
# the honesty label's own color so an auditor can scan provenance at a glance;
# "title"/"subtitle"/"banner" give a sheet a real visual hierarchy instead of
# one undifferentiated wall of navy header bars.
_STYLE_IDS = {
    "text": 0,
    "header": 1,
    "money": 2,        # $#,##0
    "money2": 3,       # $#,##0.00
    "pct": 4,          # 0.0%
    "num": 5,          # #,##0
    "num2": 6,         # #,##0.00
    "mult": 7,         # 0.00"x"
    "label": 8,        # bold ink, no fill (section labels)
    "input": 9,        # blue, general
    "input_money": 10, # blue, $#,##0.00
    "input_pct": 11,   # blue, 0.0%
    "input_num": 12,   # blue, #,##0.00
    "link": 13,        # blue underline hyperlink
    # ── appended (safe: higher ids, existing ones unchanged) ──
    "title": 14,       # 16pt bold navy — the sheet title
    "subtitle": 15,    # 10pt muted — the sheet sub-line / dek
    "banner": 16,      # bold white on teal — a section banner (≠ column header)
    "note": 17,        # 9pt italic muted — source / footnote lines
    "basis_gov": 18,          # bold green on pale green
    "basis_sourced": 19,      # bold teal on pale teal
    "basis_academic": 20,     # bold blue on pale blue
    "basis_illustrative": 21, # bold amber on pale amber
    "basis_framework": 22,    # bold grey on pale grey
    # zebra-band variants of the common table content styles (fill only).
    "text_band": 23,
    "num_band": 24,
    "num2_band": 25,
    "money_band": 26,
    "money2_band": 27,
    "pct_band": 28,
    "mult_band": 29,
    "label_band": 30,
}

# Which plain content styles get a banded twin (for zebra rows). Header /
# banner / chip / link / title cells keep their own fill and are never banded.
_BAND_OF = {
    "text": "text_band", "num": "num_band", "num2": "num2_band",
    "money": "money_band", "money2": "money2_band", "pct": "pct_band",
    "mult": "mult_band", "label": "label_band",
}

# Map an honesty-basis token → its chip style. Callers pass the leading token
# (GOV / SOURCED / ACADEMIC / ILLUSTRATIVE / FRAMEWORK), case-insensitive; a
# compound label like "GOV-magnitude" resolves on its first word.
_BASIS_STYLE = {
    "GOV": "basis_gov",
    "SOURCED": "basis_sourced",
    "ACADEMIC": "basis_academic",
    "ILLUSTRATIVE": "basis_illustrative",
    "FRAMEWORK": "basis_framework",
    "PUBLIC-WEB": "basis_framework",
    "PUBLIC": "basis_framework",
    # a network-gated connector (ingest-ready, not yet live) reads as a neutral
    # "pending" grey chip — distinct from the green/teal of a live SOURCED read.
    "CONNECTOR": "basis_framework",
}


def basis_style(token: Any) -> str:
    """Return the chip style name for a basis label, or ``"text"`` if unknown.

    ``basis_style("ILLUSTRATIVE (GOV AIF-anchored)")`` → ``"basis_illustrative"``.
    Used by the report/workbook builders so every Basis cell scans by color."""
    if not token:
        return "text"
    head = str(token).strip().upper().replace("·", " ").split()
    if not head:
        return "text"
    first = head[0].strip("-—:,.").split("-")[0].split("/")[0]
    return _BASIS_STYLE.get(first, "text")


_ALIGN = '<alignment vertical="top" wrapText="1"/>'
_ALIGN_C = '<alignment horizontal="center" vertical="center" wrapText="1"/>'

_STYLES_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<numFmts count="3">
<numFmt numFmtId="164" formatCode="$#,##0"/>
<numFmt numFmtId="165" formatCode="$#,##0.00"/>
<numFmt numFmtId="166" formatCode="0.00&quot;x&quot;"/>
</numFmts>
<fonts count="13">
<font><sz val="11"/><name val="Calibri"/></font>
<font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Calibri"/></font>
<font><b/><sz val="11"/><color rgb="FF1A2332"/><name val="Calibri"/></font>
<font><sz val="11"/><color rgb="FF1F4E9C"/><name val="Calibri"/></font>
<font><u/><sz val="11"/><color rgb="FF1F4E9C"/><name val="Calibri"/></font>
<font><b/><sz val="16"/><color rgb="FF0B2341"/><name val="Calibri"/></font>
<font><sz val="10"/><color rgb="FF6B6357"/><name val="Calibri"/></font>
<font><b/><sz val="10"/><color rgb="FF0A6B3D"/><name val="Calibri"/></font>
<font><b/><sz val="10"/><color rgb="FF0F5C54"/><name val="Calibri"/></font>
<font><b/><sz val="10"/><color rgb="FF1F4E9C"/><name val="Calibri"/></font>
<font><b/><sz val="10"/><color rgb="FF8A5A1E"/><name val="Calibri"/></font>
<font><b/><sz val="10"/><color rgb="FF5A5A5A"/><name val="Calibri"/></font>
<font><i/><sz val="9"/><color rgb="FF6B6357"/><name val="Calibri"/></font>
</fonts>
<fills count="10">
<fill><patternFill patternType="none"/></fill>
<fill><patternFill patternType="gray125"/></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FF0B2341"/><bgColor indexed="64"/></patternFill></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FF155752"/><bgColor indexed="64"/></patternFill></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FFE3F1E8"/><bgColor indexed="64"/></patternFill></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FFE0EFED"/><bgColor indexed="64"/></patternFill></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FFE6EDF7"/><bgColor indexed="64"/></patternFill></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FFF6EEE0"/><bgColor indexed="64"/></patternFill></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FFEDECEA"/><bgColor indexed="64"/></patternFill></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FFF7F4EC"/><bgColor indexed="64"/></patternFill></fill>
</fills>
<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="31">
<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1">{A}</xf>
<xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1" applyAlignment="1">{A}</xf>
<xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1" applyAlignment="1">{A}</xf>
<xf numFmtId="165" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1" applyAlignment="1">{A}</xf>
<xf numFmtId="10" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1" applyAlignment="1">{A}</xf>
<xf numFmtId="3" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1" applyAlignment="1">{A}</xf>
<xf numFmtId="4" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1" applyAlignment="1">{A}</xf>
<xf numFmtId="166" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1" applyAlignment="1">{A}</xf>
<xf numFmtId="0" fontId="2" fillId="0" borderId="0" xfId="0" applyFont="1" applyAlignment="1">{A}</xf>
<xf numFmtId="0" fontId="3" fillId="0" borderId="0" xfId="0" applyFont="1" applyAlignment="1">{A}</xf>
<xf numFmtId="165" fontId="3" fillId="0" borderId="0" xfId="0" applyNumberFormat="1" applyFont="1" applyAlignment="1">{A}</xf>
<xf numFmtId="10" fontId="3" fillId="0" borderId="0" xfId="0" applyNumberFormat="1" applyFont="1" applyAlignment="1">{A}</xf>
<xf numFmtId="4" fontId="3" fillId="0" borderId="0" xfId="0" applyNumberFormat="1" applyFont="1" applyAlignment="1">{A}</xf>
<xf numFmtId="0" fontId="4" fillId="0" borderId="0" xfId="0" applyFont="1" applyAlignment="1">{A}</xf>
<xf numFmtId="0" fontId="5" fillId="0" borderId="0" xfId="0" applyFont="1" applyAlignment="1">{A}</xf>
<xf numFmtId="0" fontId="6" fillId="0" borderId="0" xfId="0" applyFont="1" applyAlignment="1">{A}</xf>
<xf numFmtId="0" fontId="1" fillId="3" borderId="0" xfId="0" applyFont="1" applyFill="1" applyAlignment="1">{A}</xf>
<xf numFmtId="0" fontId="12" fillId="0" borderId="0" xfId="0" applyFont="1" applyAlignment="1">{A}</xf>
<xf numFmtId="0" fontId="7" fillId="4" borderId="0" xfId="0" applyFont="1" applyFill="1" applyAlignment="1">{C}</xf>
<xf numFmtId="0" fontId="8" fillId="5" borderId="0" xfId="0" applyFont="1" applyFill="1" applyAlignment="1">{C}</xf>
<xf numFmtId="0" fontId="9" fillId="6" borderId="0" xfId="0" applyFont="1" applyFill="1" applyAlignment="1">{C}</xf>
<xf numFmtId="0" fontId="10" fillId="7" borderId="0" xfId="0" applyFont="1" applyFill="1" applyAlignment="1">{C}</xf>
<xf numFmtId="0" fontId="11" fillId="8" borderId="0" xfId="0" applyFont="1" applyFill="1" applyAlignment="1">{C}</xf>
<xf numFmtId="0" fontId="0" fillId="9" borderId="0" xfId="0" applyFill="1" applyAlignment="1">{A}</xf>
<xf numFmtId="3" fontId="0" fillId="9" borderId="0" xfId="0" applyNumberFormat="1" applyFill="1" applyAlignment="1">{A}</xf>
<xf numFmtId="4" fontId="0" fillId="9" borderId="0" xfId="0" applyNumberFormat="1" applyFill="1" applyAlignment="1">{A}</xf>
<xf numFmtId="164" fontId="0" fillId="9" borderId="0" xfId="0" applyNumberFormat="1" applyFill="1" applyAlignment="1">{A}</xf>
<xf numFmtId="165" fontId="0" fillId="9" borderId="0" xfId="0" applyNumberFormat="1" applyFill="1" applyAlignment="1">{A}</xf>
<xf numFmtId="10" fontId="0" fillId="9" borderId="0" xfId="0" applyNumberFormat="1" applyFill="1" applyAlignment="1">{A}</xf>
<xf numFmtId="166" fontId="0" fillId="9" borderId="0" xfId="0" applyNumberFormat="1" applyFill="1" applyAlignment="1">{A}</xf>
<xf numFmtId="0" fontId="2" fillId="9" borderId="0" xfId="0" applyFont="1" applyFill="1" applyAlignment="1">{A}</xf>
</cellXfs>
</styleSheet>""".replace("{A}", _ALIGN).replace("{C}", _ALIGN_C)


@dataclass
class Sheet:
    name: str
    rows: List[Sequence[Any]]
    col_widths: Optional[List[float]] = None
    # ── presentation (all keyword-only-in-practice; defaults preserve the old
    # behavior exactly, so every existing Sheet(...) call is unaffected) ──
    freeze_rows: int = 0
    freeze_cols: int = 0
    autofilter: Optional[str] = None
    merges: Optional[List[str]] = None
    band_rows: Optional[Tuple[int, int]] = None


def _col_letter(i: int) -> str:
    out = ""
    i += 1
    while i:
        i, rem = divmod(i - 1, 26)
        out = chr(65 + rem) + out
    return out


def _cell_xml(ref: str, value: Any, style: str,
              links: Optional[List] = None) -> str:
    sid = _STYLE_IDS.get(style, 0)
    if isinstance(value, F):
        return f'<c r="{ref}" s="{sid}"><f>{escape(value.expr)}</f></c>'
    if isinstance(value, Link):
        # A hyperlink is a styled inline-string cell; the target travels in the
        # sheet's <hyperlinks> block + rels (registered via the accumulator).
        if links is not None:
            links.append((ref, value.url))
        txt = escape(str(value.text))
        lsid = _STYLE_IDS["link"]
        return (f'<c r="{ref}" s="{lsid}" t="inlineStr">'
                f'<is><t xml:space="preserve">{txt}</t></is></c>')
    if isinstance(value, (int, float)) and value is not True and value is not False:
        return f'<c r="{ref}" s="{sid}"><v>{value}</v></c>'
    if value is None or value == "":
        return f'<c r="{ref}" s="{sid}"/>'
    txt = escape(str(value))
    return (f'<c r="{ref}" s="{sid}" t="inlineStr">'
            f'<is><t xml:space="preserve">{txt}</t></is></c>')


def _sheet_views_xml(freeze_rows: int, freeze_cols: int) -> str:
    """A ``<sheetViews>`` block that freezes the top ``freeze_rows`` rows and/or
    left ``freeze_cols`` columns so headers stay visible on scroll. Empty when
    neither is set (identical output to the pre-freeze writer)."""
    r = max(0, int(freeze_rows or 0))
    c = max(0, int(freeze_cols or 0))
    if not (r or c):
        return ""
    top_left = f"{_col_letter(c)}{r + 1}"
    active = "bottomRight" if (r and c) else ("bottomLeft" if r else "topRight")
    xs = f' xSplit="{c}"' if c else ""
    ys = f' ySplit="{r}"' if r else ""
    pane = (f'<pane{xs}{ys} topLeftCell="{top_left}" activePane="{active}" '
            'state="frozen"/>')
    sel = f'<selection pane="{active}" activeCell="{top_left}" sqref="{top_left}"/>'
    return ('<sheetViews><sheetView workbookViewId="0">'
            f'{pane}{sel}</sheetView></sheetViews>')


def _sheet_xml(sheet: Sheet):
    """Return ``(worksheet_xml, links)`` where ``links`` is a list of
    ``(cell_ref, url)`` for every :class:`Link` cell — the caller writes the
    per-sheet relationship part for them."""
    cols = ""
    if sheet.col_widths:
        col_parts = "".join(
            f'<col min="{i+1}" max="{i+1}" width="{w}" customWidth="1"/>'
            for i, w in enumerate(sheet.col_widths))
        cols = f"<cols>{col_parts}</cols>"
    # Zebra banding: even rows within [lo, hi] get the banded twin of any plain
    # content style (chips / headers / links keep their own fill).
    band_lo = band_hi = None
    if sheet.band_rows:
        try:
            band_lo, band_hi = int(sheet.band_rows[0]), int(sheet.band_rows[1])
        except (TypeError, ValueError, IndexError):
            band_lo = band_hi = None
    links: List = []
    rows_xml = []
    for r_i, row in enumerate(sheet.rows, start=1):
        banded = (band_lo is not None and band_lo <= r_i <= band_hi
                  and (r_i - band_lo) % 2 == 1)
        cells = []
        for c_i, cell in enumerate(row):
            if isinstance(cell, tuple):
                value, style = cell
            else:
                value, style = cell, "text"
            if banded and style in _BAND_OF:
                style = _BAND_OF[style]
            cells.append(_cell_xml(f"{_col_letter(c_i)}{r_i}", value, style,
                                   links))
        rows_xml.append(f'<row r="{r_i}">{"".join(cells)}</row>')
    views = _sheet_views_xml(sheet.freeze_rows, sheet.freeze_cols)
    autofilter = (f'<autoFilter ref="{escape(sheet.autofilter)}"/>'
                  if sheet.autofilter else "")
    merges = ""
    if sheet.merges:
        parts = "".join(f'<mergeCell ref="{escape(m)}"/>' for m in sheet.merges)
        merges = f'<mergeCells count="{len(sheet.merges)}">{parts}</mergeCells>'
    hyperlinks = ""
    if links:
        parts = "".join(f'<hyperlink ref="{ref}" r:id="rId{i+1}"/>'
                        for i, (ref, _url) in enumerate(links))
        hyperlinks = f"<hyperlinks>{parts}</hyperlinks>"
    # OOXML child order is schema-fixed: sheetViews, cols, sheetData, then
    # autoFilter, mergeCells, … hyperlinks. Emitting them out of order makes
    # Excel reject the file, so the concatenation order here is load-bearing.
    xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/'
        'spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/'
        '2006/relationships">'
        f'{views}{cols}<sheetData>{"".join(rows_xml)}</sheetData>'
        f'{autofilter}{merges}{hyperlinks}'
        '</worksheet>'
    )
    return xml, links


# A fixed DOS timestamp so the zip (and thus the whole workbook) is
# byte-for-byte deterministic — zipfile.writestr(name, ...) otherwise stamps
# time.localtime(), which flips within the same run across a 2-second DOS-time
# boundary and made the workbook non-reproducible (a flaky determinism test).
_EPOCH = (1980, 1, 1, 0, 0, 0)


def _add(z: zipfile.ZipFile, name: str, data: str) -> None:
    info = zipfile.ZipInfo(name, date_time=_EPOCH)
    info.compress_type = zipfile.ZIP_DEFLATED
    z.writestr(info, data)


def write_xlsx(sheets: List[Sheet]) -> bytes:
    """Assemble a complete .xlsx as bytes (byte-for-byte deterministic)."""
    n = len(sheets)
    sheet_entries = "".join(
        f'<sheet name="{escape(s.name[:31])}" sheetId="{i+1}" '
        f'r:id="rId{i+1}"/>'
        for i, s in enumerate(sheets))
    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/'
        'spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/'
        '2006/relationships">'
        f'<sheets>{sheet_entries}</sheets></workbook>'
    )
    wb_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/'
        'package/2006/relationships">'
        + "".join(
            f'<Relationship Id="rId{i+1}" Type="http://schemas.'
            'openxmlformats.org/officeDocument/2006/relationships/'
            f'worksheet" Target="worksheets/sheet{i+1}.xml"/>'
            for i in range(n))
        + f'<Relationship Id="rId{n+1}" Type="http://schemas.'
          'openxmlformats.org/officeDocument/2006/relationships/styles" '
          'Target="styles.xml"/>'
        '</Relationships>'
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/'
        'content-types">'
        '<Default Extension="rels" ContentType="application/'
        'vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/'
        'vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        + "".join(
            f'<Override PartName="/xl/worksheets/sheet{i+1}.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.'
            'spreadsheetml.worksheet+xml"/>'
            for i in range(n))
        + '<Override PartName="/xl/styles.xml" ContentType="application/'
          'vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        '</Types>'
    )
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/'
        'package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/'
        'officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/></Relationships>'
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        _add(z, "[Content_Types].xml", content_types)
        _add(z, "_rels/.rels", root_rels)
        _add(z, "xl/workbook.xml", workbook)
        _add(z, "xl/_rels/workbook.xml.rels", wb_rels)
        _add(z, "xl/styles.xml", _STYLES_XML)
        for i, s in enumerate(sheets):
            xml, links = _sheet_xml(s)
            _add(z, f"xl/worksheets/sheet{i+1}.xml", xml)
            if links:
                rels = (
                    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                    '<Relationships xmlns="http://schemas.openxmlformats.org/'
                    'package/2006/relationships">'
                    + "".join(
                        f'<Relationship Id="rId{j+1}" Type="http://schemas.'
                        'openxmlformats.org/officeDocument/2006/relationships/'
                        # Target is an ATTRIBUTE — escape the double-quote too, or
                        # a URL containing one would terminate the attribute and
                        # corrupt the rels part.
                        f'hyperlink" Target="{escape(url, {chr(34): "&quot;"})}" '
                        'TargetMode="External"/>'
                        for j, (_ref, url) in enumerate(links))
                    + '</Relationships>'
                )
                _add(z, f"xl/worksheets/_rels/sheet{i+1}.xml.rels", rels)
    return buf.getvalue()
