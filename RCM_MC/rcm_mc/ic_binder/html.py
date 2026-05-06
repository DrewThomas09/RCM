"""HTML IC binder renderer.

Produces a self-contained HTML page (no external CSS / JS) the
partner can open in a browser and print to PDF for the physical
binder. Renders by piping ``render_markdown_binder`` through a
minimal markdown-to-HTML converter so the structure stays in
sync with the markdown form.
"""
from __future__ import annotations

import html as _html
import re
from typing import Any, List

from .markdown import render_markdown_binder


# Minimal markdown-to-HTML — covers the subset our binder renderer
# emits: headings, bold, tables, list items, paragraphs, blockquotes.
# A full markdown parser would pull in another dep; this lite
# version is sufficient + auditable.

def _md_to_html(md: str) -> str:
    out_lines: List[str] = []
    lines = md.split("\n")
    in_table = False
    table_buffer: List[str] = []
    in_list = False

    def _flush_table() -> List[str]:
        # Convert the buffer's | x | y | rows into <table>
        if not table_buffer:
            return []
        rows = [r.strip() for r in table_buffer if r.strip()]
        if len(rows) < 2:
            return [_inline(r) for r in rows]
        html_rows: List[str] = ['<table class="ic-tbl">']
        # First row = header
        header_cells = [c.strip() for c in
                        rows[0].strip("|").split("|")]
        html_rows.append("<thead><tr>" + "".join(
            f"<th>{_inline(c)}</th>" for c in header_cells)
            + "</tr></thead>")
        # Skip the separator row (---)
        body_start = 2 if (len(rows) > 1
                           and "---" in rows[1]) else 1
        html_rows.append("<tbody>")
        for r in rows[body_start:]:
            cells = [c.strip() for c in r.strip("|").split("|")]
            html_rows.append(
                "<tr>" + "".join(
                    f"<td>{_inline(c)}</td>" for c in cells)
                + "</tr>")
        html_rows.append("</tbody></table>")
        return html_rows

    def _inline(s: str) -> str:
        # Bold first (so we don't escape the asterisks before
        # transforming them).
        s_escaped = _html.escape(s)
        s_escaped = re.sub(r"\*\*(.+?)\*\*",
                           r"<strong>\1</strong>", s_escaped)
        return s_escaped

    for line in lines:
        if line.startswith("|"):
            # Buffer for table rendering
            if not in_table:
                in_table = True
                table_buffer = []
            table_buffer.append(line)
            continue
        else:
            if in_table:
                out_lines.extend(_flush_table())
                in_table = False
                table_buffer = []

        if line.startswith("# "):
            if in_list:
                out_lines.append("</ul>")
                in_list = False
            out_lines.append(f"<h1>{_inline(line[2:])}</h1>")
        elif line.startswith("## "):
            if in_list:
                out_lines.append("</ul>")
                in_list = False
            out_lines.append(f"<h2>{_inline(line[3:])}</h2>")
        elif line.startswith("### "):
            if in_list:
                out_lines.append("</ul>")
                in_list = False
            out_lines.append(f"<h3>{_inline(line[4:])}</h3>")
        elif line.startswith("- "):
            if not in_list:
                out_lines.append('<ul class="ic-ul">')
                in_list = True
            out_lines.append(f"<li>{_inline(line[2:])}</li>")
        elif line.strip() == "":
            if in_list:
                out_lines.append("</ul>")
                in_list = False
            out_lines.append("")
        else:
            if in_list:
                out_lines.append("</ul>")
                in_list = False
            out_lines.append(f"<p>{_inline(line)}</p>")

    if in_list:
        out_lines.append("</ul>")
    if in_table:
        out_lines.extend(_flush_table())
    return "\n".join(out_lines)


_CSS = """
:root {
  --c-text: #111827; --c-muted: #6b7280; --c-bg: #fafbfc;
  --c-card: #ffffff; --c-border: #e5e7eb; --c-accent: var(--sc-navy);
  --c-table-head: #f3f4f6;
}
* { box-sizing: border-box; }
body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont,
                'Segoe UI', Roboto, sans-serif;
  font-size: 14px; line-height: 1.55; color: var(--c-text);
  background: var(--c-bg); margin: 0; padding: 32px 0;
}
.ic-wrap {
  max-width: 880px; margin: 0 auto; padding: 36px 48px;
  background: var(--c-card); border: 1px solid var(--c-border);
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);
}
h1 {
  font-size: 24px; margin: 0 0 8px; padding-bottom: 12px;
  border-bottom: 2px solid var(--c-accent);
  letter-spacing: -0.02em;
}
h2 {
  font-size: 17px; margin: 28px 0 10px; color: var(--c-accent);
  letter-spacing: -0.01em; font-weight: 600;
}
h3 {
  font-size: 14px; margin: 18px 0 8px;
  text-transform: uppercase; letter-spacing: 0.06em;
  color: var(--c-muted); font-weight: 600;
}
p { margin: 8px 0; }
ul.ic-ul {
  margin: 6px 0 14px 0; padding-left: 22px;
}
ul.ic-ul li { margin: 3px 0; }
strong { font-weight: 600; color: var(--c-text); }
table.ic-tbl {
  width: 100%; border-collapse: collapse;
  margin: 10px 0; font-size: 13px;
  font-variant-numeric: tabular-nums;
}
table.ic-tbl th, table.ic-tbl td {
  padding: 8px 12px;
  border-bottom: 1px solid var(--c-border);
  text-align: left;
}
table.ic-tbl th {
  background: var(--c-table-head);
  color: var(--c-muted); font-size: 11px;
  text-transform: uppercase; letter-spacing: 0.05em;
  font-weight: 600;
}
table.ic-tbl tr:hover td { background: #fafafa; }
@media print {
  body { background: #fff; padding: 0; }
  .ic-wrap { border: none; box-shadow: none; }
}
"""


def render_html_binder(synthesis_result: Any,
                       *, title: str = "") -> str:
    """Render the synthesis result as a self-contained HTML page.
    No external CSS / JS — drop into any browser, print to PDF
    for the physical binder."""
    md = render_markdown_binder(synthesis_result)
    body_html = _md_to_html(md)
    page_title = (
        title or f"IC Binder — {synthesis_result.deal_name}")
    return (
        "<!DOCTYPE html>\n"
        "<html lang=\"en\">\n<head>\n"
        "<meta charset=\"utf-8\">\n"
        f"<title>{_html.escape(page_title)}</title>\n"
        f"<style>{_CSS}</style>\n"
        "</head>\n<body>\n"
        '<div class="ic-wrap">\n'
        f"{body_html}\n"
        "</div>\n</body>\n</html>"
    )
