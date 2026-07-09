"""Minimal formatted XLSX writer — stdlib only (zipfile + XML strings).

An .xlsx file is a zip of XML parts. This writer produces a real,
Excel/Sheets-openable workbook with the formatting a deal team expects
from a template export — bold headers, $ and % number formats, column
widths, multiple sheets — without adding openpyxl as a runtime dep
("no new runtime dependencies", CLAUDE.md).

Deliberately small: cell values are numbers or inline strings, styles
are a fixed palette (header / text / money / percent / multiple). That
covers the TAM-SAM template (and future tabular exports); it is not a
general spreadsheet library.

Public API:
    Sheet(name, rows, *, col_widths=None)
      rows: list of rows; each cell is either a plain value or a
      (value, style) tuple with style in
      {"header","text","money","money2","pct","num","num2","mult",
       "input","input_pct","label"}.
    F(expr) — a live-formula cell value (expr WITHOUT the leading "=").
      Formulas are opt-in via this wrapper, never inferred from a
      leading "=" in a string: every CSV export in this codebase is
      defanged against Excel formula injection, and silently turning
      strings into formulas here would reopen that hole for any
      template that interpolates partner-supplied text.
    write_xlsx(sheets) -> bytes
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional, Sequence
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


# Style ids map to cellXfs entries in _STYLES_XML below (order matters).
# The "input*" styles render blue — the banker convention (blue =
# hardcoded assumption you may edit, black = formula/derived) that deal
# teams expect in any model template they download. Every text-bearing cell
# wraps and top-aligns (``<alignment vertical="top" wrapText="1"/>``) so the
# long prose these exports carry never overflows or clips a column.
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
}

_ALIGN = '<alignment vertical="top" wrapText="1"/>'

_STYLES_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<numFmts count="3">
<numFmt numFmtId="164" formatCode="$#,##0"/>
<numFmt numFmtId="165" formatCode="$#,##0.00"/>
<numFmt numFmtId="166" formatCode="0.00&quot;x&quot;"/>
</numFmts>
<fonts count="5">
<font><sz val="11"/><name val="Calibri"/></font>
<font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Calibri"/></font>
<font><b/><sz val="11"/><color rgb="FF1A2332"/><name val="Calibri"/></font>
<font><sz val="11"/><color rgb="FF1F4E9C"/><name val="Calibri"/></font>
<font><u/><sz val="11"/><color rgb="FF1F4E9C"/><name val="Calibri"/></font>
</fonts>
<fills count="3">
<fill><patternFill patternType="none"/></fill>
<fill><patternFill patternType="gray125"/></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FF0B2341"/><bgColor indexed="64"/></patternFill></fill>
</fills>
<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="14">
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
</cellXfs>
</styleSheet>""".replace("{A}", _ALIGN)


@dataclass
class Sheet:
    name: str
    rows: List[Sequence[Any]]
    col_widths: Optional[List[float]] = None


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
    links: List = []
    rows_xml = []
    for r_i, row in enumerate(sheet.rows, start=1):
        cells = []
        for c_i, cell in enumerate(row):
            if isinstance(cell, tuple):
                value, style = cell
            else:
                value, style = cell, "text"
            cells.append(_cell_xml(f"{_col_letter(c_i)}{r_i}", value, style,
                                   links))
        rows_xml.append(f'<row r="{r_i}">{"".join(cells)}</row>')
    hyperlinks = ""
    if links:
        parts = "".join(f'<hyperlink ref="{ref}" r:id="rId{i+1}"/>'
                        for i, (ref, _url) in enumerate(links))
        hyperlinks = f"<hyperlinks>{parts}</hyperlinks>"
    xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/'
        'spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/'
        '2006/relationships">'
        f'{cols}<sheetData>{"".join(rows_xml)}</sheetData>{hyperlinks}'
        '</worksheet>'
    )
    return xml, links


def write_xlsx(sheets: List[Sheet]) -> bytes:
    """Assemble a complete .xlsx as bytes."""
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
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", root_rels)
        z.writestr("xl/workbook.xml", workbook)
        z.writestr("xl/_rels/workbook.xml.rels", wb_rels)
        z.writestr("xl/styles.xml", _STYLES_XML)
        for i, s in enumerate(sheets):
            xml, links = _sheet_xml(s)
            z.writestr(f"xl/worksheets/sheet{i+1}.xml", xml)
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
                z.writestr(f"xl/worksheets/_rels/sheet{i+1}.xml.rels", rels)
    return buf.getvalue()
