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
from ._chartis_kit import (
    chartis_shell, ck_fmt_num, ck_kpi_block, ck_next_section,
    ck_page_title, ck_provenance_tooltip,
)
from ._ui_kit import fmt_num

_EXPLAINER_CSS = """<style>
.ck-dc-explainer{font-family:var(--sc-serif,'Georgia',serif);
  font-size:15px;line-height:1.55;color:var(--sc-text-dim,#465366);
  margin:0 0 var(--sc-s-6,18px) 0;max-width:72ch;}
.ck-dc-explainer em{color:var(--sc-teal-ink,#155752);font-style:italic;}
</style>"""


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
        return '<span class="pill" style="color:var(--muted,#9b9382);">no data</span>'
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
        return '<span class="pill" style="color:var(--muted,#9b9382);">never</span>'
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
        f'<div class="micro" style="margin-top:.35rem;color:var(--muted,#9b9382);">'
        f'{_html.escape(sub)}</div>' if sub else ""
    )
    return (
        '<div style="border:1px solid var(--border,#465366);'
        'background:var(--paper,#F2EDE3);'
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
        '<div style="border:1px solid var(--border,#465366);'
        'background:var(--paper,#F2EDE3);border-radius:8px;'
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

    # Cycle 50 — port to ck_kpi_block + provenance.
    quality_value = ck_provenance_tooltip(
        "Average data quality",
        f"{summary['avg_quality']:.2f}" if summary["avg_quality"] is not None else "—",
        explainer=(
            "Composite score per source: volume x coverage x "
            "freshness, scaled 0-1. Above 0.7 is production-"
            "ready; below 0.4 means partner reports leaning on "
            "this source carry warnings about thin denominators."
        ),
    )
    fresh_value = ck_provenance_tooltip(
        "Fresh sources",
        f"{summary['fresh_sources']} / {summary['n_sources']}",
        explainer=(
            "Sources loaded in the last 30 days. The remaining "
            "are either at expected cadence (e.g., HCRIS is "
            "annual) or genuinely stale - cross-check with the "
            "/data/refresh page to see what's overdue."
        ),
        inject_css=False,
    )
    kpi_html = (
        '<div class="ck-kpi-grid" style="display:flex;gap:.75rem;flex-wrap:wrap;margin:.75rem 0 1.25rem 0;">'
        + ck_kpi_block("Sources", ck_fmt_num(summary["n_sources"]), "in catalog")
        + ck_kpi_block("Total Records", ck_fmt_num(summary["total_records"]), "across sources")
        + ck_kpi_block(
            "Avg Quality", quality_value, "composite 0-1",
            help={
                "definition": (
                    "Composite of three signals per source: volume "
                    "(row count vs. expected), coverage (states + "
                    "fiscal years populated), and freshness (days since "
                    "last refresh). 1.0 = ideal; below 0.6 = the "
                    "source is missing rows, lagging, or both."
                ),
            },
        )
        + ck_kpi_block(
            "Fresh", fresh_value, "loaded <=30d",
            help={
                "definition": (
                    "Sources refreshed within the last 30 days. CMS "
                    "HCRIS and Care Compare both refresh quarterly, "
                    "so 'fresh' usually means a recent quarterly "
                    "pull. Below 30d is the green band; partner can "
                    "trust the numbers downstream."
                ),
            },
        )
        + ck_kpi_block(
            "Stale",
            f"{summary['stale_sources']} / {summary['n_sources']}",
            "loaded >90d",
            help={
                "definition": (
                    "Sources past their refresh cadence. Stale data "
                    "means stale benchmarks — peer percentiles and "
                    "comparables computed against stale sources may "
                    "miss recent shifts (e.g. payer-mix swings, "
                    "wage-index updates). Click any stale row to "
                    "trigger a refresh."
                ),
            },
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
                'border:1px solid var(--border,#465366);'
                'background:var(--paper,#F2EDE3);border-radius:8px;'
                'overflow:hidden;">'
                '<thead>'
                '<tr style="border-bottom:1px solid var(--border,#465366);">'
                '<th class="micro" style="padding:.6rem 1rem;text-align:left;">Source</th>'
                '<th class="micro" style="padding:.6rem 1rem;text-align:right;">Records</th>'
                '<th class="micro" style="padding:.6rem 1rem;text-align:left;">Coverage</th>'
                '<th class="micro" style="padding:.6rem 1rem;text-align:center;">Freshness</th>'
                '<th class="micro" style="padding:.6rem 1rem;text-align:center;">Quality</th>'
                '</tr></thead>'
                f'<tbody>{rows}</tbody></table></section>'
            )
        catalog_body = "".join(sections)

    page_title = ck_page_title(
        "Data Catalog",
        eyebrow="DATA CATALOG",
        meta=f"{summary['n_sources']} sources · {summary['total_records']:,} records",
    )
    dc_explainer = (
        '<p class="ck-dc-explainer">'
        "<em>Where every dataset is registered.</em> "
        "Inventory of public-data sources the platform ingests, with row counts, "
        "freshness, and a composite quality score (volume × coverage × freshness). "
        "Auto-discovered from live SQL — the canonical answer to "
        "‘where does X come from?’ before citing a metric."
        "</p>"
    )
    body = (
        page_title
        + dc_explainer
        + '<section style="max-width:80rem;">'
        '<div style="display:flex;justify-content:space-between;'
        'align-items:baseline;margin-bottom:.75rem;">'
        '<a href="/data/refresh" class="micro" style="font-weight:400;'
        'letter-spacing:.04em;text-transform:none;">'
        'Refresh sources →</a>'
        '</div>'
        + kpi_html
        + catalog_body
        + '</section>'
        + ck_next_section(
            "Refresh the public-data loaders",
            "/data/refresh",
            eyebrow="Continue —",
            italic_word="loaders",
        )
    )

    # 2026-05-28 wave-B: ck_page_actions adds Copy share link
    # + Back-to-top affordances. Idempotent JS guards.
    from ._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(
        body,
        "Data Catalog",
        extra_css=_EXPLAINER_CSS,
    )
