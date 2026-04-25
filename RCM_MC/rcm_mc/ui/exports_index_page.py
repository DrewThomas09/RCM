"""`/exports` — consolidated landing page listing every export format.

For a user who knows they want to download something but isn't sure
which feature page to open. Groups exports into three tiers:

  1. Deal-level — requires a deal_id; links open `/api/analysis/<id>/export`
  2. Portfolio-level — fund-scope exports not tied to one deal
  3. Data-level — corpus + public data CSV/XLSX dumps

Most pages have their own export buttons too — see _export_menu.py. This
page exists as a single-click shortcut for users who want "just the
downloads, please."

Public API:
    render_exports_index(db_path: str) -> str
"""
from __future__ import annotations

import html as _html
from typing import List, Tuple

from . import _web_components as _wc


# ── Static catalog ─────────────────────────────────────────────────

_PORTFOLIO_EXPORTS: List[Tuple[str, str, str]] = [
    # (label, href, description)
    ("Portfolio CSV",
     "/api/export/portfolio.csv",
     "Latest-per-deal snapshot across every deal in the portfolio store."),
    ("LP Quarterly Update (HTML)",
     "/exports/lp-update?days=90",
     "Fund-scope LP-ready update over the last 90 days of packets."),
    ("Data refresh status",
     "/data/refresh",
     "Trigger per-source data refreshes and watch them complete live."),
    ("API OpenAPI spec",
     "/api/openapi.json",
     "Machine-readable spec for every route in this deployment."),
]

_DATA_EXPORTS: List[Tuple[str, str, str]] = [
    ("Sponsor league table",
     "/sponsor-league",
     "Ranked table of healthcare PE sponsors by realized corpus MOIC."),
    ("Corpus dashboard",
     "/corpus-dashboard",
     "Executive summary of the 635+ deal corpus — browsable tables."),
    ("Deal search",
     "/deal-search",
     "Full-text search across every corpus deal — browser-side filters."),
]


# ── Rendering ─────────────────────────────────────────────────────

def _export_rows(rows: List[Tuple[str, str, str]]) -> List[List[str]]:
    """Build sortable_table row cells from (label, href, description)."""
    out: List[List[str]] = []
    for label, href, desc in rows:
        link = (f'<a href="{_html.escape(href)}" '
                f'style="color:#1F4E78;font-weight:500;">'
                f'{_html.escape(label)}</a>')
        out.append([link, _html.escape(desc)])
    return out


def _deal_format_guide() -> str:
    """Reference card: how to use /api/analysis/<deal_id>/export?format=X.

    Each row carries a typical-size hint so a partner picking the
    right format knows what to expect: HTML is small + browser-
    renderable, PPTX is large + presentation-ready, JSON is round-
    trip safe for tooling.
    """
    formats = [
        ("html",     "Full diligence memo — renders in browser.",
         "~50–200 KB"),
        ("pdf",      "HTML memo with auto-print; use browser's Save-as-PDF.",
         "~50–200 KB"),
        ("xlsx",     "Multi-sheet Excel workbook for the deal.",
         "~100–500 KB"),
        ("pptx",     "PowerPoint deck (requires python-pptx; falls back to .txt).",
         "~500 KB–2 MB"),
        ("csv",      "Raw packet metrics as CSV.",
         "~5–20 KB"),
        ("json",     "Canonical DealAnalysisPacket JSON (round-trip safe).",
         "~10–50 KB"),
        ("package",  "ZIP archive: all formats + provenance index.",
         "~1–3 MB"),
    ]
    rows: List[List[str]] = []
    for name, desc, size in formats:
        rows.append([
            (f'<code>?format={_html.escape(name)}</code>'),
            _html.escape(desc),
            f'<span style="color:#6b7280;font-family:monospace;'
            f'font-size:11px;">{_html.escape(size)}</span>',
        ])
    intro = (
        '<p>Any deal can be exported via '
        '<code>GET /api/analysis/&lt;deal_id&gt;/export?format=X</code>. '
        'Open a deal from the dashboard first, then use its export menu.</p>'
    )
    table = _wc.sortable_table(
        ["Format", "What you get", "Typical size"], rows,
        id="exports-format-guide", hide_columns_sm=[2],
        filterable=True, filter_placeholder="Filter formats…",
    )
    return _wc.section_card("Per-deal exports", intro + table)


def render_exports_index(db_path: str) -> str:
    from ._chartis_kit import chartis_shell

    header = _wc.page_header(
        "Downloads",
        subtitle=("Every export in one place. For deal-specific memos + "
                  "data, open a deal first and use its export menu."),
        crumbs=[("Dashboard", "/dashboard"), ("Downloads", None)],
    )

    portfolio_card = _wc.section_card(
        "Portfolio-scope",
        _wc.sortable_table(
            ["Export", "What it contains"],
            _export_rows(_PORTFOLIO_EXPORTS),
            id="exports-portfolio",
            filterable=True, filter_placeholder="Filter portfolio exports…",
        ),
    )
    corpus_card = _wc.section_card(
        "Corpus browsers",
        _wc.sortable_table(
            ["Export", "What it contains"],
            _export_rows(_DATA_EXPORTS),
            id="exports-corpus",
            filterable=True, filter_placeholder="Filter corpus browsers…",
        ),
    )

    inner = (
        header
        + _deal_format_guide()
        + portfolio_card
        + corpus_card
    )
    body = (
        _wc.web_styles()
        + _wc.responsive_container(inner)
        + _wc.sortable_table_js()
    )
    return chartis_shell(body, "Downloads", active_nav="/exports")
