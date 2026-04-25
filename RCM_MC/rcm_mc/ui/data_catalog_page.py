"""Data catalog UI — `/data/catalog`.

Surfaces every public-data source we've ingested. Top-of-page
KPI strip (sources / records / avg quality / fresh count), then a
table grouped by category.

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


def _quality_badge(q: Optional[float]) -> str:
    if q is None:
        return ('<span style="display:inline-block;padding:2px 8px;'
                'border-radius:4px;background:#374151;color:#9ca3af;'
                'font-size:11px;">no data</span>')
    if q >= 0.7:
        bg, fg = "#065f46", "#a7f3d0"
        label = "high"
    elif q >= 0.4:
        bg, fg = "#92400e", "#fde68a"
        label = "medium"
    else:
        bg, fg = "#7f1d1d", "#fecaca"
        label = "low"
    return (
        f'<span style="display:inline-block;padding:2px 8px;'
        f'border-radius:4px;background:{bg};color:{fg};'
        f'font-size:11px;font-variant-numeric:tabular-nums;">'
        f'{label} · {q:.2f}</span>')


def _freshness_badge(days: Optional[int]) -> str:
    if days is None:
        return ('<span style="color:#9ca3af;font-size:11px;">'
                'never</span>')
    if days <= 7:
        bg, fg = "#065f46", "#a7f3d0"
    elif days <= 30:
        bg, fg = "#92400e", "#fde68a"
    elif days <= 90:
        bg, fg = "#78350f", "#fed7aa"
    else:
        bg, fg = "#7f1d1d", "#fecaca"
    return (
        f'<span style="display:inline-block;padding:2px 8px;'
        f'border-radius:4px;background:{bg};color:{fg};'
        f'font-size:11px;font-variant-numeric:tabular-nums;">'
        f'{days}d</span>')


def _kpi_card(label: str, value: str,
              sub: str = "") -> str:
    return (
        '<div style="background:#1f2937;border:1px solid #374151;'
        'border-radius:8px;padding:14px 18px;flex:1;'
        'min-width:180px;">'
        f'<div style="font-size:11px;text-transform:uppercase;'
        f'letter-spacing:0.05em;color:#9ca3af;margin-bottom:6px;">'
        f'{_html.escape(label)}</div>'
        f'<div class="kpi-value" style="font-size:24px;'
        f'font-weight:600;color:#f3f4f6;'
        f'font-variant-numeric:tabular-nums;">'
        f'{_html.escape(value)}</div>'
        + (f'<div style="font-size:11px;color:#6b7280;'
           f'margin-top:4px;">{_html.escape(sub)}</div>'
           if sub else "")
        + "</div>")


def _source_row(entry: DataSourceEntry) -> str:
    return (
        "<tr>"
        f'<td style="padding:10px 14px;color:#f3f4f6;">'
        f'<div style="font-weight:500;">'
        f'{_html.escape(entry.name)}</div>'
        f'<div style="font-size:11px;color:#9ca3af;'
        f'margin-top:2px;">{_html.escape(entry.description)}'
        f'</div></td>'
        f'<td style="padding:10px 14px;color:#d1d5db;'
        f'font-variant-numeric:tabular-nums;text-align:right;">'
        f'{entry.record_count:,}</td>'
        f'<td style="padding:10px 14px;color:#d1d5db;'
        f'font-size:11px;">'
        f'{_html.escape(entry.coverage_summary or "—")}</td>'
        f'<td style="padding:10px 14px;text-align:center;">'
        f'{_freshness_badge(entry.freshness_days)}</td>'
        f'<td style="padding:10px 14px;text-align:center;">'
        f'{_quality_badge(entry.quality_score)}</td>'
        f"</tr>")


def _empty_state_html() -> str:
    return (
        '<div style="background:#111827;border:1px solid #374151;'
        'border-radius:8px;padding:40px;text-align:center;'
        'color:#9ca3af;">'
        '<div style="font-size:16px;color:#f3f4f6;'
        'margin-bottom:8px;">No data sources loaded yet</div>'
        '<div style="font-size:13px;">'
        'Run <code>rcm-mc data refresh</code> or visit '
        '<a href="/data/refresh" style="color:#60a5fa;">'
        '/data/refresh</a> to load public-data sources.'
        '</div></div>')


def render_data_catalog_page(store: Any) -> str:
    """Render the full data catalog page."""
    entries = inventory_data_sources(store)
    summary = compute_data_estate_summary(entries)

    # KPI strip
    kpi_html = (
        '<div style="display:flex;gap:12px;flex-wrap:wrap;'
        'margin-bottom:18px;">'
        + _kpi_card("Sources",
                    str(summary["n_sources"]))
        + _kpi_card("Total records",
                    f"{summary['total_records']:,}")
        + _kpi_card(
            "Avg quality",
            (f"{summary['avg_quality']:.2f}"
             if summary["avg_quality"] is not None
             else "—"))
        + _kpi_card(
            "Fresh sources",
            f"{summary['fresh_sources']} / "
            f"{summary['n_sources']}",
            "loaded ≤30 days")
        + _kpi_card(
            "Stale sources",
            f"{summary['stale_sources']} / "
            f"{summary['n_sources']}",
            "loaded >90 days")
        + "</div>"
    )

    # Group entries by category
    by_cat: Dict[str, List[DataSourceEntry]] = {}
    for e in entries:
        by_cat.setdefault(e.category, []).append(e)

    if not entries:
        body = _empty_state_html()
    else:
        sections: List[str] = []
        for cat_id, cat_label in _CATEGORY_ORDER:
            cat_entries = by_cat.get(cat_id, [])
            if not cat_entries:
                continue
            cat_entries.sort(
                key=lambda e: -(e.record_count or 0))
            rows = "".join(_source_row(e)
                           for e in cat_entries)
            sections.append(
                f'<section style="margin-bottom:24px;">'
                f'<h2 style="font-size:14px;'
                f'text-transform:uppercase;'
                f'letter-spacing:0.06em;color:#9ca3af;'
                f'margin:0 0 10px 0;">'
                f'{_html.escape(cat_label)}</h2>'
                f'<table style="width:100%;border-collapse:'
                f'collapse;background:#1f2937;'
                f'border:1px solid #374151;border-radius:8px;'
                f'overflow:hidden;">'
                f'<thead>'
                f'<tr style="background:#111827;'
                f'border-bottom:1px solid #374151;">'
                f'<th style="padding:10px 14px;'
                f'text-align:left;font-size:11px;'
                f'text-transform:uppercase;letter-spacing:'
                f'0.05em;color:#9ca3af;">Source</th>'
                f'<th style="padding:10px 14px;'
                f'text-align:right;font-size:11px;'
                f'text-transform:uppercase;letter-spacing:'
                f'0.05em;color:#9ca3af;">Records</th>'
                f'<th style="padding:10px 14px;'
                f'text-align:left;font-size:11px;'
                f'text-transform:uppercase;letter-spacing:'
                f'0.05em;color:#9ca3af;">Coverage</th>'
                f'<th style="padding:10px 14px;'
                f'text-align:center;font-size:11px;'
                f'text-transform:uppercase;letter-spacing:'
                f'0.05em;color:#9ca3af;">Freshness</th>'
                f'<th style="padding:10px 14px;'
                f'text-align:center;font-size:11px;'
                f'text-transform:uppercase;letter-spacing:'
                f'0.05em;color:#9ca3af;">Quality</th>'
                f'</tr></thead><tbody>{rows}</tbody>'
                f'</table></section>')
        body = "".join(sections)

    page_html = (
        '<div style="max-width:1200px;margin:0 auto;'
        'padding:24px;">'
        '<div style="display:flex;justify-content:space-between;'
        'align-items:baseline;margin-bottom:16px;">'
        '<h1 style="font-size:24px;color:#f3f4f6;'
        'margin:0;">Data Catalog</h1>'
        '<a href="/data/refresh" style="color:#60a5fa;'
        'font-size:13px;">Refresh sources →</a>'
        '</div>'
        '<p style="color:#9ca3af;font-size:13px;'
        'margin:0 0 18px 0;max-width:720px;">'
        'Every public-data source the platform ingests, with '
        'live record counts, refresh dates, and a composite '
        'quality score (volume × coverage × freshness). '
        'Auto-discovered from live SQL — no hand-maintained '
        'registry to drift.'
        '</p>'
        + kpi_html
        + body
        + '</div>')

    return page_html
