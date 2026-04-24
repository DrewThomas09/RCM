"""Power-UI builders — Python side of the PE-analyst power features.

Pairs with ``rcm_mc/ui/static/power_ui.{js,css}``. The JS library is
loaded once per page via :func:`power_ui_tags` (the Chartis shell
calls this automatically). Python-side helpers below produce HTML
snippets that opt into the client features via data-attributes.

Usage::

    from .power_ui import (
        power_ui_tags, provenance, sortable_table, export_json_panel,
    )

    body = provenance(
        value="$4,200",
        source="hospital_06 H6-P000 .. H6-P009 (5 paid + 1 bad-debt)",
        formula="sum(paid_amount) over mature cohort",
    )

The tags emitted by this module are self-contained HTML — no
requirement to manually include the bundle; ``chartis_shell`` handles
that now.
"""
from __future__ import annotations

import html
import json
from typing import Any, Dict, Iterable, List, Optional, Sequence


def power_ui_tags() -> str:
    """Emit the <link> + <script> pair for the power-ui bundle.

    Idempotent — safe to call inside pages that might also be wrapped
    by the shell."""
    return (
        '<link rel="stylesheet" href="/static/power_ui.css">\n'
        '<script src="/static/power_ui.js" defer></script>\n'
    )


def provenance(
    value: str,
    *,
    source: str,
    formula: Optional[str] = None,
    detail: Optional[str] = None,
    tag: str = "span",
    extra_class: str = "",
    extra_style: str = "",
) -> str:
    """Wrap ``value`` in a span with a hover tooltip exposing the
    provenance (source, formula, detail). Cursor becomes `help`,
    underline is dotted — discoverable without being distracting.
    """
    attrs = [
        f'data-provenance="{html.escape(source, quote=True)}"',
    ]
    if formula:
        attrs.append(
            f'data-provenance-formula="{html.escape(formula, quote=True)}"'
        )
    if detail:
        attrs.append(
            f'data-provenance-detail="{html.escape(detail, quote=True)}"'
        )
    if extra_class:
        attrs.append(f'class="{html.escape(extra_class, quote=True)}"')
    if extra_style:
        attrs.append(f'style="{html.escape(extra_style, quote=True)}"')
    attrs.append("tabindex=\"0\"")
    return (
        f"<{tag} {' '.join(attrs)}>{html.escape(value)}</{tag}>"
    )


def sortable_table(
    headers: Sequence[str],
    rows: Sequence[Sequence[Any]],
    *,
    name: str = "table",
    sortable: bool = True,
    filterable: bool = True,
    exportable: bool = True,
    sort_keys: Optional[Sequence[Sequence[Any]]] = None,
    caption: Optional[str] = None,
    table_class: str = "",
) -> str:
    """Render a table with optional client features opted in via
    data-attributes. ``sort_keys`` (optional) is a parallel matrix of
    machine-readable sort values for columns where the display text
    isn't directly sortable (e.g. "$1,234" → 1234)."""
    attrs = [f'data-export-name="{html.escape(name, quote=True)}"']
    if sortable:
        attrs.append('data-sortable')
    if filterable:
        attrs.append('data-filterable')
    if exportable:
        attrs.append('data-export')
    if table_class:
        attrs.append(f'class="{html.escape(table_class, quote=True)}"')
    head_cells = "".join(
        f'<th>{html.escape(str(h))}</th>' for h in headers
    )
    body_rows = []
    for ridx, row in enumerate(rows):
        cells = []
        for cidx, cell in enumerate(row):
            display = "" if cell is None else str(cell)
            sort_attr = ""
            if sort_keys is not None:
                try:
                    key = sort_keys[ridx][cidx]
                    if key is not None:
                        sort_attr = (
                            f' data-sort-key="{html.escape(str(key), quote=True)}"'
                        )
                except IndexError:
                    pass
            # If the display value already contains HTML (from
            # provenance etc.) we trust it through — callers who
            # need raw HTML build the cell content themselves.
            cells.append(f'<td{sort_attr}>{display}</td>')
        body_rows.append('<tr>' + "".join(cells) + '</tr>')
    caption_html = (
        f'<caption>{html.escape(caption)}</caption>' if caption else ""
    )
    return (
        f'<table {" ".join(attrs)}>'
        f'{caption_html}'
        f'<thead><tr>{head_cells}</tr></thead>'
        f'<tbody>{"".join(body_rows)}</tbody>'
        f'</table>'
    )


def export_json_panel(
    inner_html: str,
    *,
    payload: Any,
    name: str = "panel",
    extra_class: str = "",
    extra_style: str = "",
) -> str:
    """Wrap a block of HTML in a container that gets a floating
    'Export JSON' button auto-injected by the bundle."""
    encoded = html.escape(json.dumps(payload, default=str), quote=True)
    cls_attr = f' class="{html.escape(extra_class, quote=True)}"' if extra_class else ""
    style_attr = f' style="{html.escape(extra_style, quote=True)}"' if extra_style else ""
    return (
        f'<div data-export-json="{encoded}" '
        f'data-export-name="{html.escape(name, quote=True)}"'
        f'{cls_attr}{style_attr}>'
        f'{inner_html}'
        f'</div>'
    )


def bookmark_hint() -> str:
    """Small hint text (footer) telling the user about b/s shortcuts.
    Use sparingly — don't clutter every page."""
    return (
        '<div style="font-size:10px;color:#64748b;letter-spacing:.5px;'
        'text-transform:uppercase;margin-top:20px;opacity:0.7;">'
        'Press <kbd style="padding:1px 5px;border:1px solid currentColor;'
        'border-radius:2px;font-family:inherit;">?</kbd> for shortcuts · '
        '<kbd style="padding:1px 5px;border:1px solid currentColor;'
        'border-radius:2px;font-family:inherit;">b</kbd> to bookmark · '
        '<kbd style="padding:1px 5px;border:1px solid currentColor;'
        'border-radius:2px;font-family:inherit;">⌘K</kbd> to jump'
        '</div>'
    )


def diff_badge(
    left_value: float,
    right_value: float,
    *,
    format_spec: str = ",.0f",
    unit: str = "$",
    higher_is_better: bool = False,
) -> str:
    """Badge showing left vs right delta for comparison views.

    ``higher_is_better`` flips the coloring: when True, right > left
    gets positive (green); when False, right > left gets negative."""
    if left_value == right_value:
        cls = "rcm-diff-neutral"
        arrow = "→"
        delta_str = "="
    else:
        delta = right_value - left_value
        if (delta > 0) == higher_is_better:
            cls = "rcm-diff-positive"
        else:
            cls = "rcm-diff-negative"
        arrow = "▲" if delta > 0 else "▼"
        delta_str = f"{unit}{format(abs(delta), format_spec)}"
    return (
        f'<span class="rcm-diff-indicator {cls}">'
        f'{arrow} {delta_str}</span>'
    )
