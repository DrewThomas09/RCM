"""Styled HTML renderers for short CSV data tables (UI-7).

CSVs are fine for scripting consumers but unreadable when clicked in the
output-folder index. This module wraps every *short* CSV in a styled,
sortable HTML table view with:

- **Numeric auto-alignment** via the shared ``_html_polish`` post-pass
- **Smart column formatting** — money, percent, integer, multiple (x)
  inferred from column name (e.g. ``net_patient_revenue`` → money)
- **Client-side sort** on every column header (vanilla JS, no deps)
- **Back-link to index** so the user can navigate without typing URLs

Deliberately skips huge CSVs (default threshold: 500 rows). The raw file
stays on disk for scripting consumers; the HTML view is for humans.

Design choice: one function + one schema-inference step, not per-file
renderers. Column formatting is driven by **name heuristics** — the
same conventions the rest of the product uses (``*_pct``, ``npsr_*``,
``moic``, ``irr``, etc.).
"""
from __future__ import annotations

import csv
import html
import os
import re
from datetime import datetime, timezone
from typing import Callable, List, Optional, Tuple

from ._html_polish import polish_tables_in_html


# Column-name → formatter heuristics. First-match wins; order matters.
# Conservative: when in doubt, leave the raw string.
_FORMATTERS: List[Tuple[re.Pattern, Callable]] = []


def _fmt_money(v: str) -> str:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return v
    sign = "-" if f < 0 else ""
    af = abs(f)
    if af >= 1e9:
        return f"{sign}${af/1e9:.2f}B"
    if af >= 1e6:
        return f"{sign}${af/1e6:.1f}M"
    if af >= 1e3:
        return f"{sign}${af/1e3:.0f}K"
    return f"{sign}${af:,.0f}"


def _fmt_pct(v: str) -> str:
    try:
        return f"{float(v)*100:.1f}%"
    except (TypeError, ValueError):
        return v


def _fmt_int(v: str) -> str:
    try:
        return f"{int(float(v)):,}"
    except (TypeError, ValueError):
        return v


def _fmt_float(v: str, digits: int = 3) -> str:
    try:
        return f"{float(v):.{digits}f}"
    except (TypeError, ValueError):
        return v


def _fmt_multi(v: str) -> str:
    try:
        return f"{float(v):.2f}x"
    except (TypeError, ValueError):
        return v


# Order matters — the first matching pattern wins.
_FORMATTERS = [
    (re.compile(r"_pct$"),                            _fmt_pct),
    (re.compile(r"^(irr|variance_pct|share_of)"),     _fmt_pct),
    (re.compile(r"^(moic|ratio$|x_)"),                _fmt_multi),
    (re.compile(r"(revenue|income|ebitda|expenses|proceeds|equity|ev|debt|capital|value|trips_at|uplift|impact|distribution|drag|wacc)", re.I),
                                                      _fmt_money),
    (re.compile(r"^(beds|days$|total_patient_days|medicare_days|medicaid_days|rate_count|unique_codes|unique_payers|total_rows|quarters)"),
                                                      _fmt_int),
    (re.compile(r"(score|hhi|headroom)"),             _fmt_float),
]


def _pick_formatter(col_name: str) -> Optional[Callable]:
    for pat, fn in _FORMATTERS:
        if pat.search(col_name):
            return fn
    return None


# Per-page CSS — sort-arrow affordances on top of the shared _ui_kit.
_EXTRA_CSS = """
th { position: sticky; top: 0; z-index: 1; }
th:hover { background: var(--accent-soft); color: var(--accent); }
th .arrow { opacity: 0.4; font-size: 0.7rem; margin-left: 0.3rem; }
th[aria-sort="ascending"] .arrow, th[aria-sort="descending"] .arrow {
  opacity: 1; color: var(--accent);
}
.sort-btn {
  all: unset;
  display: flex;
  align-items: center;
  gap: 0.25rem;
  width: 100%;
  cursor: pointer;
}
.sort-btn:focus-visible {
  outline: 3px solid var(--blue);
  outline-offset: 2px;
}
.card { padding: 0; overflow: auto; }
"""

# Client-side sort — vanilla JS, numeric-aware via the td.num class.
_JS = """
document.querySelectorAll('table').forEach(function(tbl){
  var buttons = tbl.querySelectorAll('.sort-btn');
  buttons.forEach(function(btn){
    btn.addEventListener('click', function(){
      var colIdx = parseInt(btn.getAttribute('data-col-idx'), 10);
      var th = btn.closest('th');
      var asc = th.getAttribute('aria-sort') !== 'ascending';
      tbl.querySelectorAll('th').forEach(function(x){
        x.setAttribute('aria-sort', 'none');
      });
      th.setAttribute('aria-sort', asc ? 'ascending' : 'descending');
      var tbody = tbl.querySelector('tbody');
      var rows = Array.from(tbody.querySelectorAll('tr'));
      rows.sort(function(a, b){
        var av = a.children[colIdx].innerText.trim();
        var bv = b.children[colIdx].innerText.trim();
        // Strip $ , % x from numeric cells for comparison
        var an = parseFloat(av.replace(/[\\$,%x]/g,''));
        var bn = parseFloat(bv.replace(/[\\$,%x]/g,''));
        if (!isNaN(an) && !isNaN(bn)) return asc ? an-bn : bn-an;
        return asc ? av.localeCompare(bv) : bv.localeCompare(av);
      });
      rows.forEach(function(r){ tbody.appendChild(r); });
    });
  });
});
"""


# ── Core render ────────────────────────────────────────────────────────────

def render_csv(
    path: str,
    *,
    title: Optional[str] = None,
    max_rows: int = 500,
    back_href: str = "index.html",
) -> Optional[str]:
    """Render a CSV file as styled HTML. Returns None for oversized CSVs.

    ``max_rows`` guards against rendering 5k-row simulation dumps into the
    DOM. Over the threshold → None, caller falls back to leaving the CSV
    file alone. Threshold high enough for peer/trend/variance tables.
    """
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        try:
            headers = next(reader)
        except StopIteration:
            return None
        rows = list(reader)

    if len(rows) > max_rows:
        return None

    # Per-column formatters — precompute so we don't re-match per cell
    formatters = [_pick_formatter(h) for h in headers]

    # Title falls back to the humanized filename
    if title is None:
        title = os.path.splitext(os.path.basename(path))[0].replace("_", " ").title()

    header_cells = "".join(
        f'<th scope="col" aria-sort="none">'
        f'<button type="button" class="sort-btn" data-col-idx="{i}" '
        f'aria-label="Sort by {html.escape(h)}">{html.escape(h)}'
        f'<span class="arrow" aria-hidden="true">↕</span></button></th>'
        for i, h in enumerate(headers)
    )
    body_rows: List[str] = []
    for row in rows:
        cells = []
        for i, value in enumerate(row):
            formatter = formatters[i] if i < len(formatters) else None
            rendered = formatter(value) if formatter else value
            cells.append(f'<td>{html.escape(str(rendered))}</td>')
        body_rows.append(f"<tr>{''.join(cells)}</tr>")

    from ._ui_kit import shell
    subtitle = (
        f"{len(rows)} row{'s' if len(rows) != 1 else ''} · "
        f"{os.path.basename(path)} · Click any column header to sort"
    )
    body = (
        f'<div class="card"><table>'
        f'<caption class="sr-only">{html.escape(title)}. '
        f'{len(rows)} row{"s" if len(rows) != 1 else ""}. '
        f'Use the sort buttons on column headers to reorder the table.</caption>'
        f'<thead><tr>{header_cells}</tr></thead>'
        f'<tbody>{"".join(body_rows)}</tbody>'
        f'</table></div>'
    )
    doc = shell(
        body=body, title=title, back_href=back_href,
        subtitle=subtitle, extra_css=_EXTRA_CSS, extra_js=_JS,
    )
    # Apply UI-1 numeric-alignment polish to cells our column-name
    # formatters didn't catch.
    return polish_tables_in_html(doc)


# ── Folder-level orchestration ─────────────────────────────────────────────

def wrap_csvs_in_folder(folder: str, max_rows: int = 500) -> List[str]:
    """Write an ``.html`` sibling for every CSV in ``folder`` that fits the
    size threshold. Large CSVs are intentionally left as raw files.

    Returns paths written. Skips CSVs that already have an ``.html`` of
    the same stem so hand-crafted renders (e.g. pe_hold_grid.html from
    UI-6) aren't clobbered.
    """
    if not os.path.isdir(folder):
        return []
    written: List[str] = []
    for name in sorted(os.listdir(folder)):
        if not name.lower().endswith(".csv"):
            continue
        full = os.path.join(folder, name)
        stem, _ = os.path.splitext(name)
        out_path = os.path.join(folder, stem + ".html")
        if os.path.isfile(out_path):
            continue
        try:
            doc = render_csv(full, max_rows=max_rows)
            if doc is None:
                continue  # oversized
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(doc)
            written.append(out_path)
        except (OSError, UnicodeDecodeError, csv.Error):
            continue
    return written
