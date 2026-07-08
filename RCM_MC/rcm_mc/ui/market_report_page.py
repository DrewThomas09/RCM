"""Market Reports — the ``/market`` index and ``/market/<slug>`` dossier.

The editorial front door to :mod:`rcm_mc.market_reports`. ``/market`` groups
every canonical subsector by care setting; ``/market/<slug>`` renders the full
authored dossier (or an honest scaffold when the report module isn't authored
yet). Both render entirely from ``chartis_shell`` + ``ck_*`` primitives, chip
every figure with its honesty basis, and never fabricate a number.

Public API:
    render_market_index() -> str
    render_market_report(slug: str) -> str
"""
from __future__ import annotations

import html as _html
from typing import List, Optional

from .. import market_reports as _mr
from ._chart_kit import ck_bar_chart, ck_chart_assets
from ._chartis_kit import (
    P, chartis_shell, ck_arrow_link, ck_editorial_head, ck_empty_state,
    ck_eyebrow, ck_fmt_number, ck_fmt_percent, ck_narrative_band,
    ck_next_section, ck_page_actions, ck_panel, ck_provenance_tooltip,
    ck_section_header, ck_section_intro,
)
from .us_geo_map import render_us_geo_map
from ..market_reports import MarketReport
from ..market_reports.analytics import state_breakdown, supply_trend


def _esc(x: object) -> str:
    return _html.escape(str(x if x is not None else ""))


# ── Honesty basis chips ─────────────────────────────────────────────────────
# Every displayed magnitude wears one of these so a partner never mistakes a
# modeled number for a filed one. The tooltip spells out the contract.
_BASIS_KEYS = ("SOURCED", "GOV", "ACADEMIC", "ILLUSTRATIVE", "INDUSTRY",
               "INTERNAL")
_BASIS_TITLE = {
    "SOURCED": "Derived from OUR data (deep-dive / corpus / CMS files).",
    "GOV": "A published government figure (CMS, MedPAC, USRDS, Census).",
    "ACADEMIC": "A real academic / peer-reviewed citation.",
    "ILLUSTRATIVE": "Modeled — the basis is named, not a filed figure.",
    "INDUSTRY": "An industry / trade source.",
    "INTERNAL": "A PE Desk internal surface (deep-dive, corpus, sizing).",
}


def _basis_key(label: str) -> str:
    up = (label or "").strip().upper()
    for k in _BASIS_KEYS:
        if up.startswith(k):
            return k
    return "ILLUSTRATIVE"


def _basis_chip(basis: str) -> str:
    b = _basis_key(basis)
    return (f'<span class="ck-mr-chip ck-mr-chip-{b.lower()}" '
            f'title="{_esc(_BASIS_TITLE[b])}">{_esc(b)}</span>')


def _source_chip(source_label: str) -> str:
    """A basis chip plus the muted remainder of a ``basis · source`` label."""
    b = _basis_key(source_label)
    rest = source_label.split("·", 1)[1].strip() if "·" in source_label else ""
    tail = (f' <span class="ck-mr-src">{_esc(rest)}</span>' if rest else "")
    return _basis_chip(b) + tail


def _fmt_tam(th) -> str:
    """Masthead market-size string. Dollars 2dp, percent 1dp, mono."""
    unit = (th.unit or "").strip()
    try:
        if unit.endswith("B"):
            val = f"${th.value:,.2f}B"
        elif unit.endswith("M"):
            val = f"${th.value:,.2f}M"
        elif unit.endswith("%"):
            val = f"{th.value:.1f}%"
        else:
            val = f"{th.value:,.2f} {unit}".strip()
    except (TypeError, ValueError):
        val = "—"
    return val


def _growth_str(th) -> str:
    if th.growth_pct is None:
        return ""
    sign = "+" if th.growth_pct >= 0 else ""
    return f"{sign}{th.growth_pct:.1f}%/yr"


def _legend_row() -> str:
    """The honesty legend — one chip per basis, shown on both surfaces."""
    chips = "".join(_basis_chip(k) for k in
                    ("SOURCED", "GOV", "ACADEMIC", "ILLUSTRATIVE"))
    return (
        '<div class="ck-mr-legend">'
        '<span class="ck-mr-legend-lab">Every figure is labelled</span>'
        f'{chips}'
        '</div>'
    )


# ── Scoped stylesheet (ck- prefixed so it stays inside the editorial idiom) ──
def _styles() -> str:
    return (
        "<style>"
        ".ck-mr-chip{display:inline-block;font-family:var(--sc-mono);"
        "font-size:9px;font-weight:700;letter-spacing:0.06em;padding:1px 6px;"
        "border-radius:3px;vertical-align:middle;margin:0 2px 2px 0;"
        "text-transform:uppercase;border:1px solid transparent;}"
        ".ck-mr-chip-sourced{color:#0f3d39;border-color:var(--sc-teal,#155752);"
        "background:rgba(21,87,82,0.08);}"
        ".ck-mr-chip-gov{color:#123a63;border-color:var(--sc-navy,#0b2341);"
        "background:rgba(11,35,65,0.06);}"
        ".ck-mr-chip-academic{color:#5a3b12;border-color:var(--sc-warning,#b8732a);"
        "background:rgba(184,115,42,0.08);}"
        ".ck-mr-chip-illustrative{color:#5c6878;border-color:var(--sc-text-faint,#7a8699);"
        "background:rgba(122,134,153,0.08);}"
        ".ck-mr-chip-industry{color:#5c6878;border-color:var(--sc-rule-2,#bfb6a2);}"
        ".ck-mr-chip-internal{color:#0f3d39;border-color:var(--sc-teal,#155752);}"
        ".ck-mr-src{font-size:10px;color:var(--sc-text-dim,#465366);"
        "font-family:var(--sc-mono);}"
        ".ck-mr-legend{margin:10px 0 4px;font-size:11px;"
        "color:var(--sc-text-dim,#465366);}"
        ".ck-mr-legend-lab{font-family:var(--sc-mono);font-size:10px;"
        "letter-spacing:0.06em;text-transform:uppercase;margin-right:8px;}"
        ".ck-mr-table{width:100%;border-collapse:collapse;background:#fff;"
        "border:1px solid var(--sc-rule,#d6cfc0);font-size:12.5px;margin:0 0 6px;}"
        ".ck-mr-table th{text-align:left;padding:8px 12px;font-family:var(--sc-sans);"
        "font-size:10px;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;"
        "color:var(--sc-text-dim,#465366);border-bottom:1px solid var(--sc-rule,#d6cfc0);}"
        ".ck-mr-table td{padding:8px 12px;border-bottom:1px solid var(--sc-panel-alt,#ece5d6);"
        "vertical-align:top;color:var(--sc-text,#1a2332);line-height:1.5;}"
        ".ck-mr-num{font-variant-numeric:tabular-nums;font-family:var(--sc-mono);"
        "text-align:right;white-space:nowrap;}"
        ".ck-mr-prose{font-family:var(--sc-serif,Georgia,serif);font-size:14px;"
        "line-height:1.65;color:var(--sc-text,#1a2332);margin:0 0 10px;max-width:74ch;}"
        ".ck-mr-list{margin:0 0 10px;padding-left:20px;font-size:13px;line-height:1.7;"
        "color:var(--sc-text,#1a2332);}"
        ".ck-mr-list li{margin:0 0 5px;}"
        ".ck-mr-exec{list-style:none;margin:0;padding:0;}"
        ".ck-mr-exec li{position:relative;padding:0 0 10px 26px;font-family:var(--sc-serif);"
        "font-size:14.5px;line-height:1.6;color:var(--sc-text,#1a2332);}"
        ".ck-mr-exec li::before{content:'▪';position:absolute;left:6px;top:0;"
        "color:var(--sc-teal,#155752);}"
        ".ck-mr-lens{list-style:none;margin:0;padding:0;}"
        ".ck-mr-lens li{padding:10px 0 10px 16px;border-left:2px solid var(--sc-teal,#155752);"
        "margin:0 0 8px;font-size:13px;line-height:1.6;color:var(--sc-text,#1a2332);}"
        ".ck-mr-players span{display:inline-block;font-size:11.5px;padding:3px 9px;"
        "margin:0 5px 5px 0;border:1px solid var(--sc-rule,#d6cfc0);border-radius:14px;"
        "background:#fff;color:var(--sc-text,#1a2332);}"
        ".ck-mr-sev-high{color:var(--sc-negative,#b5321e);font-weight:600;}"
        ".ck-mr-sev-medium{color:var(--sc-warning,#b8732a);font-weight:600;}"
        ".ck-mr-sev-low{color:var(--sc-text-dim,#465366);font-weight:600;}"
        ".ck-mr-conn{list-style:none;margin:0;padding:0;font-size:13px;line-height:1.7;}"
        ".ck-mr-conn li{margin:0 0 7px;}"
        ".ck-mr-refs{margin:0;padding-left:22px;font-size:12.5px;line-height:1.7;"
        "color:var(--sc-text,#1a2332);}"
        ".ck-mr-refs li{margin:0 0 7px;}"
        ".ck-mr-mast{margin:2px 0 6px;font-family:var(--sc-mono);font-size:12px;"
        "color:var(--sc-text-dim,#465366);}"
        ".ck-mr-mast b{font-size:15px;color:var(--sc-text,#1a2332);}"
        ".ck-mr-idx-def{color:var(--sc-text-dim,#465366);}"
        "</style>"
    )


# ═══════════════════════════════════════════════════════════════════════════
#  /market  —  editorial index
# ═══════════════════════════════════════════════════════════════════════════
def render_market_index() -> str:
    reports = _mr.all_reports()
    by_setting = _mr.subsectors_by_setting()
    n_total = len(_mr.canonical_slugs())
    n_authored = len(reports)
    n_conn = sum(len(r.connections) for r in reports.values())

    # KPI strip — every count via ck_fmt_number, headline authored count via
    # a provenance tooltip so the "83 subsectors" number is self-explaining.
    kpi_total = ck_provenance_tooltip(
        "Subsectors", ck_fmt_number(n_total),
        explainer=("Every healthcare subsector in the TAM/SAM taxonomy. Each "
                   "has a page; authored ones show a full dossier, the rest an "
                   "honest scaffold."))
    kpi_authored = ck_provenance_tooltip(
        "Authored", ck_fmt_number(n_authored),
        explainer=("Subsectors with a complete, honestly-sourced market "
                   "report. The remainder are scaffolds pending authoring."),
        inject_css=False)
    kpi_conn = ck_provenance_tooltip(
        "Live connections", ck_fmt_number(n_conn),
        explainer=("Links from authored reports into our real data — sizing "
                   "builds, deep-dives, deal history, and connector datasets."),
        inject_css=False)
    kpi_strip = (
        '<div class="ck-kpi-grid ck-mr-grid">'
        + _kpi("Subsectors", kpi_total, "in the taxonomy")
        + _kpi("Authored reports", kpi_authored, "full dossiers")
        + _kpi("Care settings", ck_fmt_number(len(_mr.CARE_SETTINGS)),
               "editorial groupings")
        + _kpi("Live connections", kpi_conn, "into our real data")
        + '</div>'
    )

    head = ck_editorial_head(
        "MARKET REPORTS",
        "Healthcare subsector market reports",
        meta=(f"{n_total} SUBSECTORS · {len(_mr.CARE_SETTINGS)} CARE SETTINGS · "
              f"{n_authored} AUTHORED"),
        lede_italic_phrase="Every subsector, one dossier —",
        lede_body=("how the industry actually works, what the operators know, "
                   "and where you confirm it against our own data."),
        source_note=("Authored from public CMS/MedPAC/USRDS + academic sources "
                     "and PE Desk's real deep-dives; every figure is labelled."),
        show_legend=True,
    )

    intro = ck_section_intro(
        "HOW TO READ THIS",
        "Start with the definition, end with the insider lens.",
        italic_word="insider",
        body=("Each report explains the value chain, reimbursement mechanics, "
              "regulation, consolidation, unit economics, and the non-obvious "
              "dynamics operators live by — then links straight into our "
              "sizing builds and connector data."))

    # One section per care setting, each a scannable table.
    sections: List[str] = []
    for setting in _mr.CARE_SETTINGS:
        rows = by_setting.get(setting, [])
        if not rows:
            continue
        sections.append(ck_section_header(
            setting, eyebrow="CARE SETTING", count=len(rows)))
        sections.append(_index_table(rows, reports))

    body = (
        _styles()
        + ck_eyebrow("Market Reports")
        + head
        + kpi_strip
        + _legend_row()
        + intro
        + "".join(sections)
        + ck_next_section(
            "Size any subsector in the TAM/SAM builder",
            "/diligence/tam-sam",
            eyebrow="Up next", italic_word="TAM/SAM")
        + ck_page_actions()
    )
    return chartis_shell(body, "Market Reports", active_nav="/market")


def _kpi(label: str, value: str, sub: str) -> str:
    # Local KPI block (avoids importing ck_kpi_block's trusted-value contract
    # ambiguity here — value is our own server markup). All ck- classed.
    return (
        '<div class="ck-kpi">'
        f'<div class="ck-kpi-label">{_esc(label)}</div>'
        f'<div class="ck-kpi-value sc-num">{value}</div>'
        f'<div class="ck-kpi-sub">{_esc(sub)}</div>'
        '</div>'
    )


def _index_table(rows, reports) -> str:
    body_rows: List[str] = []
    for slug, name in rows:
        rep: Optional[MarketReport] = reports.get(slug)
        link = (f'<a href="/market/{_esc(slug)}" class="ck-arrow">'
                f'{_esc(name)}</a>')
        if rep is not None:
            definition = f'<span class="ck-mr-idx-def">{_esc(rep.one_line_def)}</span>'
            tam = (f'<span class="ck-mr-num">{_esc(_fmt_tam(rep.tam_headline))}'
                   f'</span> {_basis_chip(rep.tam_headline.basis_label)}')
            conns = f'<span class="ck-mr-num">{ck_fmt_number(len(rep.connections))}</span>'
        else:
            definition = ('<span class="ck-mr-idx-def">Scaffold — dossier '
                          'pending authoring; the page shows what it will '
                          'contain.</span>')
            tam = '<span class="ck-mr-num">—</span>'
            conns = '<span class="ck-mr-num">—</span>'
        body_rows.append(
            "<tr>"
            f"<td>{link}</td>"
            f"<td>{definition}</td>"
            f"<td>{tam}</td>"
            f"<td>{conns}</td>"
            "</tr>"
        )
    return (
        '<table class="ck-mr-table">'
        "<thead><tr>"
        "<th>Subsector</th><th>What it is</th>"
        "<th>Market size</th><th>Connections</th>"
        "</tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody>"
        "</table>"
    )


# ═══════════════════════════════════════════════════════════════════════════
#  /market/<slug>  —  the dossier
# ═══════════════════════════════════════════════════════════════════════════
def render_market_report(slug: str) -> str:
    slug = (slug or "").strip().lower().replace("-", "_")
    rep = _mr.report_for(slug)
    if rep is None:
        return _render_scaffold(slug)
    return _render_full(rep)


# ═══════════════════════════════════════════════════════════════════════════
#  Deep sections — the "one hour and you have the whole idea" layer
# ═══════════════════════════════════════════════════════════════════════════
def _trends_section(rep: MarketReport) -> str:
    if not rep.trends:
        return ""
    return (ck_section_header("Multi-year trends", eyebrow="WHERE IT'S HEADING")
            + ck_panel(f'<p class="ck-mr-prose">{_esc(rep.trends)}</p>'))


def _growth_levers_section(rep: MarketReport) -> str:
    if not rep.growth_levers:
        return ""
    rows = "".join(
        "<tr>"
        f"<td>{_esc(g.lever)}</td>"
        f"<td>{_esc(g.mechanism)}</td>"
        f'<td class="ck-mr-num">{_esc(g.magnitude)}</td>'
        f"<td>{_basis_chip(g.basis)}</td>"
        "</tr>"
        for g in rep.growth_levers)
    body = (
        '<p class="ck-mr-prose">The distinct engines of growth — each with its '
        'mechanism and rough magnitude.</p>'
        '<table class="ck-mr-table"><thead><tr>'
        '<th>Lever</th><th>Mechanism</th><th>Magnitude</th><th>Basis</th>'
        f'</tr></thead><tbody>{rows}</tbody></table>')
    return (ck_section_header("Key growth levers", eyebrow="WHAT DRIVES GROWTH",
                              count=len(rep.growth_levers))
            + ck_panel(body))


def _volume_driver_section(rep: MarketReport) -> str:
    vd = rep.volume_growth_driver
    if vd is None:
        return ""
    body = (
        f'<p class="ck-mr-prose"><strong>{_esc(vd.driver)}</strong> '
        f'{_basis_chip(vd.basis)}</p>'
        f'<p class="ck-mr-prose">{_esc(vd.analysis)}</p>')
    return (ck_section_header("What drives volume",
                              eyebrow="THE DOMINANT DEMAND DRIVER")
            + ck_panel(body))


def _cost_drivers_section(rep: MarketReport) -> str:
    if not rep.cost_drivers:
        return ""
    rows = "".join(
        "<tr>"
        f"<td>{_esc(c.driver)}</td>"
        f'<td class="ck-mr-num">{_esc(c.share_or_rank)}</td>'
        f"<td>{_esc(c.note)}</td>"
        f"<td>{_basis_chip(c.basis)}</td>"
        "</tr>"
        for c in rep.cost_drivers)
    body = (
        '<p class="ck-mr-prose">The ranked cost structure — the big line items '
        'that actually move margin.</p>'
        '<table class="ck-mr-table"><thead><tr>'
        '<th>Cost driver</th><th>Share / rank</th><th>Note</th><th>Basis</th>'
        f'</tr></thead><tbody>{rows}</tbody></table>'
        '<p class="ck-mr-src">Shares/ranks are ILLUSTRATIVE cost-structure '
        'benchmarks unless chipped otherwise — confirm against the target’s '
        'own cost report.</p>')
    return (ck_section_header("Cost structure", eyebrow="WHAT MOVES MARGIN",
                              count=len(rep.cost_drivers))
            + ck_panel(body))


def _cms_trend_section(rep: MarketReport) -> str:
    """A REAL trended CMS series (computed via analytics.supply_trend) rendered
    as an inline-SVG chart PLUS a written takeaway. Missing data → an honest
    note, never a fabricated chart."""
    st = supply_trend(rep.slug)
    ct = rep.cms_trend
    header = ck_section_header("CMS data, trended",
                              eyebrow="REAL SERIES + TAKEAWAY")
    if not st.available:
        note = st.note or ("A trended CMS series is unavailable offline for "
                           "this subsector.")
        body = f'<p class="ck-mr-prose">{_esc(note)}</p>'
        if ct and ct.takeaway:
            body += ('<p class="ck-mr-prose"><strong>Reading</strong> — '
                     f'{_esc(ct.takeaway)}</p>')
        return header + ck_panel(body)

    src = (ct.source_label if (ct and ct.source_label) else st.source_label)
    items = [(c.label, float(c.net_adds), "teal") for c in st.cohorts]
    chart = ck_bar_chart(
        "Facility supply by certification-vintage cohort", items,
        value_fmt=lambda v: f"{int(v):,}",
        source=src,
        subtitle=("Net adds to the currently-open facility stock, by 5-year "
                  "certification cohort"),
        chart_id=f"mr-supply-{rep.slug}")

    facts: List[str] = []
    if st.cagr is not None and st.window_start and st.window_end:
        facts.append(f'cumulative CAGR <b>{st.cagr * 100:+.1f}%/yr</b> '
                     f'({st.window_start}–{st.window_end})')
    if st.inflection_year:
        facts.append(f'peak-build year <b>{st.inflection_year}</b>')
    if st.peak_cohort:
        facts.append(f'heaviest cohort <b>{_esc(st.peak_cohort)}</b>')
    facts_line = (
        '<div class="ck-mr-mast">' + " &middot; ".join(facts)
        + f' {_basis_chip("SOURCED")}</div>') if facts else ""

    authored = (f'<p class="ck-mr-prose">{_esc(ct.takeaway)}</p>'
                if (ct and ct.takeaway) else "")
    body = (
        ck_chart_assets()
        + chart
        + facts_line
        + '<p class="ck-mr-prose"><strong>What this shows</strong> '
        + _source_chip(src) + '</p>'
        + f'<p class="ck-mr-prose">{_esc(st.takeaway)}</p>'
        + authored
        + f'<p class="ck-mr-src">{_esc(st.note)}</p>')
    return header + ck_panel(body)


def _state_breakdown_section(rep: MarketReport) -> str:
    """Per-state facility density, for-profit mix, and chain concentration —
    a computed table (+ a low-risk choropleth) with a written insight. Missing
    data → an honest note, never a fabricated map."""
    sb = state_breakdown(rep.slug)
    header = ck_section_header(
        "State breakdown", eyebrow="HOW THE MARKET DIFFERS BY STATE",
        count=(sb.n_states if sb.available else None))
    if not sb.available:
        body = f'<p class="ck-mr-prose">{_esc(sb.note)}</p>'
        if rep.state_breakdown:
            body += f'<p class="ck-mr-prose">{_esc(rep.state_breakdown)}</p>'
        return header + ck_panel(body)

    top = sb.rows[:12]
    has_chain = any(r.chain_top_share is not None for r in sb.rows)

    def _fp(r) -> str:
        return ("—" if r.for_profit_share is None
                else f"{r.for_profit_share * 100:.0f}%")

    def _ct(r) -> str:
        return ("—" if r.chain_top_share is None
                else f"{r.chain_top_share * 100:.0f}%")

    head_cells = ("<th>State</th><th>Facilities</th><th>% of US</th>"
                  "<th>For-profit</th>")
    if has_chain:
        head_cells += "<th>Top operator (local)</th>"
    body_rows = "".join(
        "<tr>"
        f"<td>{_esc(r.state)}</td>"
        f'<td class="ck-mr-num">{ck_fmt_number(r.facilities)}</td>'
        f'<td class="ck-mr-num">{r.facilities_share * 100:.1f}%</td>'
        f'<td class="ck-mr-num">{_fp(r)}</td>'
        + (f'<td class="ck-mr-num">{_ct(r)}</td>' if has_chain else "")
        + "</tr>"
        for r in top)
    table = ('<table class="ck-mr-table"><thead><tr>' + head_cells
             + f'</tr></thead><tbody>{body_rows}</tbody></table>')

    the_map = render_us_geo_map(
        {r.state: float(r.facilities) for r in sb.rows},
        metric_label="facilities",
        value_format=lambda v: f"{int(v):,}",
        map_title=f"{rep.name}: Medicare-certified facilities by state",
        exposure_label="Facility count (low&nbsp;→&nbsp;high)",
        accent_label="—",
        caveat_text=(
            "Approximate Albers-projected US state map (public-domain Census "
            "boundaries). Shading is the count of vendored Medicare-certified "
            "facilities per state — real counts, not a facility-location map."),
        empty_message="")

    fp_nat = ("" if sb.national_for_profit_share is None
              else f'{sb.for_profit_label} <b>'
                   f'{sb.national_for_profit_share * 100:.1f}%</b> &middot; ')
    hhi = ("" if sb.chain_hhi is None
           else f'chain HHI <b>{sb.chain_hhi:,.0f}</b> &middot; ')
    stat = (
        '<div class="ck-mr-mast">'
        f'{ck_fmt_number(sb.n_states)} states &middot; '
        f'{ck_fmt_number(sb.n_facilities)} facilities &middot; '
        f'top-5 <b>{sb.top5_share * 100:.1f}%</b> &middot; {fp_nat}{hhi}'
        f'{_basis_chip("SOURCED")}</div>')

    extra = (f'<p class="ck-mr-prose">{_esc(rep.state_breakdown)}</p>'
             if rep.state_breakdown else "")
    body = (
        f'<p class="ck-mr-prose">{_esc(sb.insight)} '
        + _source_chip(sb.source_label) + '</p>'
        + stat
        + the_map
        + table
        + '<p class="ck-mr-src">Top 12 states by facility count; for-profit '
        'share is over facilities with reported ownership. '
        + _esc(sb.source_label) + '</p>'
        + extra)
    return header + ck_panel(body)


def _deep_sections(rep: MarketReport) -> str:
    """The ordered deep-analysis block, inserted after Market size. Each part
    renders only when its data/field is present (honest omission otherwise)."""
    return (
        _trends_section(rep)
        + _growth_levers_section(rep)
        + _volume_driver_section(rep)
        + _cost_drivers_section(rep)
        + _cms_trend_section(rep)
        + _state_breakdown_section(rep))


def _render_full(rep: MarketReport) -> str:
    th = rep.tam_headline
    naics = f"NAICS {_esc(rep.naics)} · " if rep.naics else ""
    growth = _growth_str(th)
    growth_meta = f" · {growth} CAGR" if growth else ""

    head = ck_editorial_head(
        f"{rep.care_setting.upper()} · MARKET REPORT",
        _esc(rep.name),
        meta=(f"{naics}{_esc(_fmt_tam(th))} MARKET{growth_meta.upper()} · "
              f"{len(rep.connections)} CONNECTIONS"),
        lede_italic_phrase="What it is —",
        lede_body=_esc(rep.one_line_def),
        source_note=_esc(th.basis_note) if th.basis_note else "",
        show_legend=True,
    )

    # Masthead honesty band: the TAM headline + its basis chip, explicit.
    masthead = (
        '<div class="ck-mr-mast">'
        f'Market size <b>{_esc(_fmt_tam(th))}</b> '
        f'{_basis_chip(th.basis_label)}'
        + (f' &middot; growth <b>{_esc(growth)}</b>' if growth else "")
        + '</div>'
        + _legend_row()
    )

    parts: List[str] = [_styles(), ck_eyebrow(rep.care_setting), head, masthead]

    # ── Executive summary — the easy-to-understand key parts, up top ──
    parts.append(ck_section_intro(
        "THE KEY PARTS", "What you need to know, up top.",
        italic_word="up",
        body="The five things that decide whether this subsector is a deal."))
    exec_items = "".join(f"<li>{_esc(s)}</li>" for s in rep.executive_summary)
    parts.append(f'<ul class="ck-mr-exec">{exec_items}</ul>')

    # ── Our live data (SOURCED from the deep-dives) ──
    if rep.live_figures:
        parts.append(ck_section_header(
            "Our live data", eyebrow="SOURCED FROM OUR DEEP-DIVES",
            count=len(rep.live_figures)))
        cells: List[str] = []
        first = True
        for lf in rep.live_figures:
            val = ck_provenance_tooltip(
                lf.label,
                f'{_esc(lf.value)} {_basis_chip(lf.basis)}',
                explainer=lf.source_label, inject_css=first)
            first = False
            cells.append(_kpi(lf.label, val, ""))
        parts.append('<div class="ck-kpi-grid ck-mr-grid">'
                     + "".join(cells) + '</div>')
        parts.append(ck_narrative_band(
            "The figures above are computed live from our vendored CMS files "
            "and the realized-deal corpus — not authored. Open the deep-dive "
            "for the full state-by-state map."))

    # ── How it works ──
    hiw = rep.how_it_works
    chain = "".join(f"<li>{_esc(s)}</li>" for s in hiw.value_chain)
    sites = "".join(f"<li>{_esc(s)}</li>" for s in hiw.sites_of_care)
    hiw_body = (
        '<p class="ck-mr-prose"><strong>Value chain — referral to cash</strong></p>'
        f'<ol class="ck-mr-list">{chain}</ol>'
        '<p class="ck-mr-prose"><strong>Sites of care</strong></p>'
        f'<ul class="ck-mr-list">{sites}</ul>'
        '<p class="ck-mr-prose"><strong>How the money flows</strong></p>'
        f'<p class="ck-mr-prose">{_esc(hiw.money_flow)}</p>'
        '<p class="ck-mr-prose"><strong>Who the players are</strong></p>'
        f'<p class="ck-mr-prose">{_esc(hiw.key_players)}</p>'
    )
    parts.append(ck_section_header("How it works", eyebrow="THE MOVING PARTS"))
    parts.append(ck_panel(hiw_body))

    # ── Market size ──
    seg_rows = "".join(
        "<tr>"
        f"<td>{_esc(s.name)}</td>"
        f'<td class="ck-mr-num">{_esc(s.value)}</td>'
        f"<td>{_source_chip(s.source_label)}</td>"
        "</tr>"
        for s in rep.market_size.segments)
    drivers = "".join(f"<li>{_esc(d)}</li>"
                      for d in rep.market_size.growth_drivers)
    size_body = (
        f'<p class="ck-mr-prose">Headline market size '
        f'<strong>{_esc(_fmt_tam(th))}</strong> '
        f'{_basis_chip(th.basis_label)}. {_esc(th.basis_note)}</p>'
        '<table class="ck-mr-table"><thead><tr>'
        '<th>Segment</th><th>Size / share</th><th>Basis</th>'
        f'</tr></thead><tbody>{seg_rows}</tbody></table>'
        '<p class="ck-mr-prose"><strong>Growth drivers</strong></p>'
        f'<ul class="ck-mr-list">{drivers}</ul>'
    )
    parts.append(ck_section_header("Market size", eyebrow="HOW BIG"))
    parts.append(ck_panel(size_body))

    # ── Deep sections — trends, growth levers, volume driver, cost structure,
    #    the CMS trend chart, and the state breakdown (computed from our data) ──
    parts.append(_deep_sections(rep))

    # ── Reimbursement ──
    reimb = rep.reimbursement
    payer_rows = "".join(
        "<tr>"
        f"<td>{_esc(k)}</td>"
        f'<td class="ck-mr-num">{ck_fmt_percent(v)}</td>'
        "</tr>"
        for k, v in reimb.payer_mix.items())
    mechanics = "".join(f"<li>{_esc(m)}</li>" for m in reimb.rate_mechanics)
    reimb_body = (
        '<p class="ck-mr-prose"><strong>Payer mix</strong> '
        '<span class="ck-mr-src">shares approximate; percent 1dp</span></p>'
        '<table class="ck-mr-table"><thead><tr>'
        '<th>Payer</th><th>Share</th>'
        f'</tr></thead><tbody>{payer_rows}</tbody></table>'
        '<p class="ck-mr-prose"><strong>Rate mechanics</strong></p>'
        f'<ul class="ck-mr-list">{mechanics}</ul>'
        '<p class="ck-mr-prose"><strong>Reimbursement risk</strong></p>'
        f'<p class="ck-mr-prose">{_esc(reimb.reimbursement_risk)}</p>'
    )
    parts.append(ck_section_header(
        "Reimbursement", eyebrow="HOW IT GETS PAID"))
    parts.append(ck_panel(reimb_body))

    # ── Regulatory ──
    rule_rows = "".join(
        "<tr>"
        + (f'<td><a href="{_esc(r.source_url)}" target="_blank" '
           f'rel="noopener" class="ck-arrow">{_esc(r.name)} ↗</a></td>'
           if r.source_url else f"<td>{_esc(r.name)}</td>")
        + f"<td>{_esc(r.why_it_matters)}</td>"
        "</tr>"
        for r in rep.regulatory.rules)
    watch = "".join(f"<li>{_esc(w)}</li>" for w in rep.regulatory.policy_watch)
    reg_body = (
        '<table class="ck-mr-table"><thead><tr>'
        '<th>Rule / ruling</th><th>Why it matters</th>'
        f'</tr></thead><tbody>{rule_rows}</tbody></table>'
        '<p class="ck-mr-prose"><strong>Policy watch</strong></p>'
        f'<ul class="ck-mr-list">{watch}</ul>'
    )
    parts.append(ck_section_header("Regulatory", eyebrow="THE RULES"))
    parts.append(ck_panel(reg_body))

    # ── Competition ──
    comp = rep.competition
    players = "".join(f"<span>{_esc(p)}</span>" for p in comp.notable_players)
    hhi = (f'<p class="ck-mr-prose"><strong>Concentration</strong> — '
           f'{_esc(comp.hhi_or_share)}</p>' if comp.hhi_or_share else "")
    comp_body = (
        f'<p class="ck-mr-prose"><strong>Fragmentation</strong> — '
        f'{_esc(comp.fragmentation)}</p>'
        f'{hhi}'
        f'<p class="ck-mr-prose"><strong>Consolidation</strong> — '
        f'{_esc(comp.consolidation)}</p>'
        f'<p class="ck-mr-prose"><strong>PE activity</strong> — '
        f'{_esc(comp.pe_activity)}</p>'
        '<p class="ck-mr-prose"><strong>Notable players</strong></p>'
        f'<div class="ck-mr-players">{players}</div>'
    )
    parts.append(ck_section_header(
        "Competition", eyebrow="WHO OWNS THE MARKET"))
    parts.append(ck_panel(comp_body))

    # ── Unit economics ──
    kpi_rows = "".join(
        "<tr>"
        f"<td>{_esc(k.metric)}</td>"
        f'<td class="ck-mr-num">{_esc(k.typical_range)}</td>'
        f"<td>{_esc(k.why)}</td>"
        "</tr>"
        for k in rep.unit_economics.kpis)
    ue_body = (
        '<table class="ck-mr-table"><thead><tr>'
        '<th>KPI</th><th>Typical range</th><th>Why it matters</th>'
        f'</tr></thead><tbody>{kpi_rows}</tbody></table>'
        '<p class="ck-mr-prose"><strong>Margin profile</strong></p>'
        f'<p class="ck-mr-prose">{_esc(rep.unit_economics.margin_profile)}</p>'
        '<p class="ck-mr-src">Ranges are ILLUSTRATIVE operating benchmarks — '
        'confirm against the target’s own financials.</p>'
    )
    parts.append(ck_section_header(
        "Unit economics", eyebrow="THE MARGIN STORY"))
    parts.append(ck_panel(ue_body))

    # ── Risks ──
    risk_rows = "".join(
        "<tr>"
        f"<td>{_esc(r.risk)}</td>"
        f'<td><span class="ck-mr-sev-{_esc(r.severity.lower())}">'
        f'{_esc(r.severity)}</span></td>'
        f"<td>{_esc(r.note)}</td>"
        "</tr>"
        for r in rep.risks)
    parts.append(ck_section_header("Risks", eyebrow="WHAT BREAKS THE THESIS"))
    parts.append(ck_panel(
        '<table class="ck-mr-table"><thead><tr>'
        '<th>Risk</th><th>Severity</th><th>Note</th>'
        f'</tr></thead><tbody>{risk_rows}</tbody></table>'))

    # ── Diligence questions ──
    dq = "".join(f"<li>{_esc(q)}</li>" for q in rep.diligence_questions)
    parts.append(ck_section_header(
        "Diligence questions", eyebrow="WHAT TO ASK"))
    parts.append(ck_panel(f'<ol class="ck-mr-list">{dq}</ol>'))

    # ── Insider lens ──
    lens = "".join(f"<li>{_esc(x)}</li>" for x in rep.insider_lens)
    parts.append(ck_section_header(
        "Insider lens", eyebrow="WHAT THE INDUSTRY KNOWS"))
    parts.append(ck_panel(
        '<p class="ck-mr-prose">The non-obvious dynamics operators live by '
        'and outsiders miss.</p>'
        f'<ul class="ck-mr-lens">{lens}</ul>'))

    # ── Our data connections ──
    conn_items = "".join(
        f'<li>{ck_arrow_link(c.label, c.href)} '
        f'<span class="ck-mr-chip ck-mr-chip-internal">{_esc(c.kind)}</span>'
        f'</li>'
        for c in rep.connections)
    parts.append(ck_section_header(
        "Our data connections", eyebrow="CONFIRM IT WITH REAL DATA",
        count=len(rep.connections)))
    parts.append(ck_panel(
        '<p class="ck-mr-prose">Every link below opens a live PE Desk surface '
        'built on real CMS / connector / corpus data — size it, screen it, or '
        'trace the numbers.</p>'
        f'<ul class="ck-mr-conn">{conn_items}</ul>'))

    # ── Sources ──
    src_items = "".join(
        "<li>"
        + (f'<a href="{_esc(s.url)}" target="_blank" rel="noopener" '
           f'class="ck-arrow">{_esc(s.citation)} ↗</a>'
           if s.url else _esc(s.citation))
        + f" {_basis_chip(s.kind)}</li>"
        for s in rep.sources)
    parts.append(ck_section_header("Sources", eyebrow="REFERENCES"))
    parts.append(ck_panel(f'<ol class="ck-mr-refs">{src_items}</ol>'))

    parts.append(ck_next_section(
        "Back to all market reports", "/market",
        eyebrow="Up next", italic_word="all"))
    parts.append(ck_page_actions())

    return chartis_shell("".join(parts), f"{rep.name} — Market Report",
                         active_nav="/market")


def _render_scaffold(slug: str) -> str:
    """Honest placeholder for a subsector without an authored report — never
    a 404. Shows what the dossier WILL contain and links to the live data
    that already exists for it."""
    name = _mr.display_name(slug)
    setting = _mr.care_setting_for(slug)
    known = slug in set(_mr.canonical_slugs())

    head = ck_editorial_head(
        (setting.upper() + " · MARKET REPORT") if setting else "MARKET REPORT",
        _esc(name),
        meta="SCAFFOLD · DOSSIER PENDING AUTHORING",
        lede_italic_phrase="Not authored yet —",
        lede_body=("this subsector has a page and live data connections; the "
                   "full dossier is in the authoring queue."),
        show_legend=False,
    )

    will_contain = "".join(
        f"<li>{_esc(x)}</li>" for x in (
            "Executive summary — the key parts, up top",
            "How it works — value chain, sites of care, money flow, players",
            "Market size — segments and growth drivers, every figure labelled",
            "Reimbursement — payer mix and rate mechanics",
            "Regulatory — the rules and the policy watch",
            "Competition — fragmentation, consolidation, PE activity",
            "Unit economics — KPIs and the margin profile",
            "Risks, diligence questions, and the insider lens",
            "Our data connections — sizing, deep-dive, screener, connectors",
        ))

    # Live data already exists for every canonical slug (they map 1:1 to the
    # deep-dive registry), so offer those connections even without a report.
    conn_html = ""
    if known:
        conns = _mr.default_connections(slug, deals_sector=slug)
        conn_items = "".join(
            f'<li>{ck_arrow_link(c.label, c.href)} '
            f'<span class="ck-mr-chip ck-mr-chip-internal">{_esc(c.kind)}</span>'
            f'</li>' for c in conns)
        conn_html = (
            ck_section_header("Live data you can use now",
                              eyebrow="ALREADY CONNECTED")
            + ck_panel(f'<ul class="ck-mr-conn">{conn_items}</ul>')
        )

    empty = ck_empty_state(
        "This dossier is in the authoring queue.",
        body=("The framework and data connections are wired; the authored "
              "narrative is not written yet. Below is exactly what it will "
              "contain."),
        eyebrow="SCAFFOLD",
        cta_label="Browse all market reports",
        cta_href="/market",
    )

    body = (
        _styles()
        + ck_eyebrow(setting or "Market Reports")
        + head
        + empty
        + ck_section_header("What this report will contain",
                            eyebrow="THE TEMPLATE")
        + ck_panel(f'<ul class="ck-mr-list">{will_contain}</ul>')
        + conn_html
        + ck_next_section("Back to all market reports", "/market",
                          eyebrow="Up next", italic_word="all")
        + ck_page_actions()
    )
    return chartis_shell(body, f"{name} — Market Report (scaffold)",
                         active_nav="/market")
