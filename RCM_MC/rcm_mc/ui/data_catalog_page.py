"""Data catalog UI — ``/data/catalog``.

Surfaces every public-data source the platform has ingested. Top-of-
page KPI strip (sources / records / avg quality / fresh / stale),
then a table grouped by category.

Why this page is exempt from the DealAnalysisPacket invariant:
    The catalog is portfolio-wide infrastructure metadata, not deal
    analytics. There is no deal_id; the source of truth is the
    PortfolioStore's data-source inventory. Per the campaign brief,
    pages of this shape are ones where the packet invariant doesn't
    apply (the equivalent of /v3-status — internal/admin metadata).

Public API::

    render_data_catalog_page(store) -> str
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional

from ..data.catalog import (
    DataSourceEntry,
    compute_data_estate_summary,
    inventory_data_sources,
)
from ._chartis_kit import chartis_shell
from ._ui_kit import fmt_num


_CATEGORY_ORDER = [
    ("financial", "Cost & financial"),
    ("provider", "Provider registry"),
    ("quality", "Quality"),
    ("pricing", "Pricing"),
    ("utilization", "Utilization"),
    ("compliance", "Compliance & conflict"),
    ("market", "Market & demographic"),
    ("ma", "Medicare Advantage"),
    ("internal", "Internal load logs"),
]


def _quality_pill(q: Optional[float]) -> str:
    """Status-pill rendering of the 0..1 quality score.

    Uses the v3 ``.pill`` utility class (declared in
    /static/v3/chartis.css §8.4) plus a status-color modifier so the
    pill picks up the editorial palette automatically.
    """
    if q is None:
        return '<span class="pill" style="color:var(--muted,#9ca3af);">no data</span>'
    if q >= 0.7:
        cls, label = "pill pill-good", "high"
    elif q >= 0.4:
        cls, label = "pill pill-warn", "medium"
    else:
        cls, label = "pill pill-bad", "low"
    return (
        f'<span class="{cls}">'
        f'<span class="num mono">{q:.2f}</span> · {label}'
        f'</span>'
    )


def _freshness_pill(days: Optional[int]) -> str:
    """Days-since-refresh pill. Falls back to v3 ``.pill`` chrome
    plus the .num utility class on the numeric."""
    if days is None:
        return '<span class="pill" style="color:var(--muted,#9ca3af);">never</span>'
    if days <= 7:
        cls = "pill pill-good"
    elif days <= 30:
        cls = "pill pill-warn"
    elif days <= 90:
        cls = "pill pill-warn"
    else:
        cls = "pill pill-bad"
    return f'<span class="{cls}"><span class="num">{days}</span>d</span>'


def _kpi_card(label: str, value_html: str, sub: str = "") -> str:
    """Editorial KPI card — paper background, border, eyebrow label.

    Pulls visual tokens from /static/v3/chartis.css via CSS custom-
    property fallbacks so the same card renders correctly under
    either the legacy dark shell (which sets --ck-* tokens) or the
    editorial parchment shell (which sets --paper, --border, --ink).
    """
    sub_html = (
        f'<div class="micro" style="margin-top:.35rem;color:var(--muted,#9ca3af);">'
        f'{_html.escape(sub)}</div>' if sub else ""
    )
    return (
        '<div style="border:1px solid var(--border,#374151);'
        'background:var(--paper,#1f2937);'
        'border-radius:8px;padding:14px 18px;flex:1;min-width:180px;">'
        f'<div class="micro">{_html.escape(label)}</div>'
        f'<div style="font-size:1.5rem;font-weight:600;margin-top:.4rem;">'
        f'{value_html}</div>'
        f'{sub_html}</div>'
    )


def _source_row(entry: DataSourceEntry) -> str:
    return (
        "<tr>"
        '<td style="padding:.7rem 1rem;">'
        f'<div style="font-weight:500;">{_html.escape(entry.name)}</div>'
        '<div class="micro" style="margin-top:.15rem;font-weight:400;'
        'letter-spacing:.04em;text-transform:none;">'
        f'{_html.escape(entry.description)}</div>'
        '</td>'
        f'<td style="padding:.7rem 1rem;text-align:right;">'
        f'{fmt_num(entry.record_count)}</td>'
        f'<td style="padding:.7rem 1rem;font-size:.85rem;">'
        f'{_html.escape(entry.coverage_summary or "—")}</td>'
        f'<td style="padding:.7rem 1rem;text-align:center;">'
        f'{_freshness_pill(entry.freshness_days)}</td>'
        f'<td style="padding:.7rem 1rem;text-align:center;">'
        f'{_quality_pill(entry.quality_score)}</td>'
        '</tr>'
    )


def _empty_state_html() -> str:
    return (
        '<div style="border:1px solid var(--border,#374151);'
        'background:var(--paper,#111827);border-radius:8px;'
        'padding:2.5rem;text-align:center;">'
        '<div style="font-size:1rem;margin-bottom:.5rem;">'
        'No data sources loaded yet</div>'
        '<div class="micro" style="font-weight:400;letter-spacing:.04em;'
        'text-transform:none;">'
        'Run <code>rcm-mc data refresh</code> or visit '
        '<a href="/data/refresh">/data/refresh</a> to load '
        'public-data sources.</div></div>'
    )


def render_data_catalog_page(store: Any) -> str:
    """Render the full data catalog page.

    Returns a complete HTML document via ``chartis_shell``. The shell
    supplies the dark/editorial chrome, the v3 chartis.css link, and
    the chartis-blue / teal accent — this renderer only emits body
    content.
    """
    entries = inventory_data_sources(store)
    summary = compute_data_estate_summary(entries)

    kpi_html = (
        '<div style="display:flex;gap:.75rem;flex-wrap:wrap;margin:.75rem 0 1.25rem 0;">'
        + _kpi_card("Sources", fmt_num(summary["n_sources"]))
        + _kpi_card("Total records", fmt_num(summary["total_records"]))
        + _kpi_card(
            "Avg quality",
            (f'<span class="num mono">{summary["avg_quality"]:.2f}</span>'
             if summary["avg_quality"] is not None
             else '<span class="num">—</span>'),
        )
        + _kpi_card(
            "Fresh sources",
            f'{fmt_num(summary["fresh_sources"])} / {fmt_num(summary["n_sources"])}',
            sub="loaded ≤30 days",
        )
        + _kpi_card(
            "Stale sources",
            f'{fmt_num(summary["stale_sources"])} / {fmt_num(summary["n_sources"])}',
            sub="loaded >90 days",
        )
        + '</div>'
    )

    by_cat: Dict[str, List[DataSourceEntry]] = {}
    for e in entries:
        by_cat.setdefault(e.category, []).append(e)

    if not entries:
        catalog_body = _empty_state_html()
    else:
        sections: List[str] = []
        for cat_id, cat_label in _CATEGORY_ORDER:
            cat_entries = by_cat.get(cat_id, [])
            if not cat_entries:
                continue
            cat_entries.sort(key=lambda e: -(e.record_count or 0))
            rows = "".join(_source_row(e) for e in cat_entries)
            sections.append(
                '<section style="margin-bottom:1.5rem;">'
                f'<h2 class="micro" style="margin:0 0 .5rem 0;">'
                f'{_html.escape(cat_label)}</h2>'
                '<table style="width:100%;border-collapse:collapse;'
                'border:1px solid var(--border,#374151);'
                'background:var(--paper,#1f2937);border-radius:8px;'
                'overflow:hidden;">'
                '<thead>'
                '<tr style="border-bottom:1px solid var(--border,#374151);">'
                '<th class="micro" style="padding:.6rem 1rem;text-align:left;">Source</th>'
                '<th class="micro" style="padding:.6rem 1rem;text-align:right;">Records</th>'
                '<th class="micro" style="padding:.6rem 1rem;text-align:left;">Coverage</th>'
                '<th class="micro" style="padding:.6rem 1rem;text-align:center;">Freshness</th>'
                '<th class="micro" style="padding:.6rem 1rem;text-align:center;">Quality</th>'
                '</tr></thead>'
                f'<tbody>{rows}</tbody></table></section>'
            )
        catalog_body = "".join(sections)

    body = (
        '<section style="max-width:80rem;">'
        '<div style="display:flex;justify-content:space-between;'
        'align-items:baseline;margin-bottom:.75rem;">'
        '<h1 style="margin:0;">Data Catalog</h1>'
        '<a href="/data/refresh" class="micro" style="font-weight:400;'
        'letter-spacing:.04em;text-transform:none;">'
        'Refresh sources →</a>'
        '</div>'
        '<p style="max-width:48rem;color:var(--muted,#9ca3af);'
        'margin:0 0 1rem 0;">'
        'Every public-data source the platform ingests, with live '
        'record counts, refresh dates, and a composite quality score '
        '(volume × coverage × freshness). Auto-discovered from live '
        'SQL — no hand-maintained registry to drift.</p>'
        + kpi_html
        + catalog_body
        + '</section>'
    )

    return chartis_shell(
        body,
        "Data Catalog",
        subtitle="public-data inventory",
    )
