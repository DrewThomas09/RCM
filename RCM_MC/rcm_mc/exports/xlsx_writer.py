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
      {"header","text","money","money2","pct","num","num2"}.
    write_xlsx(sheets) -> bytes
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional, Sequence, Tuple
from xml.sax.saxutils import escape
import io
import zipfile

# Style ids map to cellXfs entries in _STYLES_XML below (order matters).
_STYLE_IDS = {
    "text": 0,
    "header": 1,
    "money": 2,    # $#,##0
    "money2": 3,   # $#,##0.00
    "pct": 4,      # 0.0%
    "num": 5,      # #,##0
    "num2": 6,     # #,##0.00
}

_STYLES_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<numFmts count="2">
<numFmt numFmtId="164" formatCode="$#,##0"/>
<numFmt numFmtId="165" formatCode="$#,##0.00"/>
</numFmts>
<fonts count="2">
<font><sz val="11"/><name val="Calibri"/></font>
<font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Calibri"/></font>
</fonts>
<fills count="3">
<fill><patternFill patternType="none"/></fill>
<fill><patternFill patternType="gray125"/></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FF0B2341"/><bgColor indexed="64"/></patternFill></fill>
</fills>
<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="7">
<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
<xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1"/>
<xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>
<xf numFmtId="165" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>
<xf numFmtId="10" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>
<xf numFmtId="3" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>
<xf numFmtId="4" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>
</cellXfs>
</styleSheet>"""


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


def _cell_xml(ref: str, value: Any, style: str) -> str:
    sid = _STYLE_IDS.get(style, 0)
    if isinstance(value, (int, float)) and value is not True and value is not False:
        return f'<c r="{ref}" s="{sid}"><v>{value}</v></c>'
    if value is None or value == "":
        return f'<c r="{ref}" s="{sid}"/>'
    txt = escape(str(value))
    return (f'<c r="{ref}" s="{sid}" t="inlineStr">'
            f'<is><t xml:space="preserve">{txt}</t></is></c>')


def _sheet_xml(sheet: Sheet) -> str:
    cols = ""
    if sheet.col_widths:
        col_parts = "".join(
            f'<col min="{i+1}" max="{i+1}" width="{w}" customWidth="1"/>'
            for i, w in enumerate(sheet.col_widths))
        cols = f"<cols>{col_parts}</cols>"
    rows_xml = []
    for r_i, row in enumerate(sheet.rows, start=1):
        cells = []
        for c_i, cell in enumerate(row):
            if isinstance(cell, tuple):
                value, style = cell
            else:
                value, style = cell, "text"
            cells.append(_cell_xml(f"{_col_letter(c_i)}{r_i}", value, style))
        rows_xml.append(f'<row r="{r_i}">{"".join(cells)}</row>')
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/'
        'spreadsheetml/2006/main">'
        f'{cols}<sheetData>{"".join(rows_xml)}</sheetData></worksheet>'
    )


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
            z.writestr(f"xl/worksheets/sheet{i+1}.xml", _sheet_xml(s))
    return buf.getvalue()
