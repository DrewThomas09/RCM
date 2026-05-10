"""SeekingChartis Deal Pipeline — saved searches and hospital tracking.

The workflow platform: analysts save screener filters, add hospitals to
the pipeline, track them through stages, and see the funnel at a glance.
"""
from __future__ import annotations

import html as _html
import json
from typing import Any, Dict, List, Optional

from ..portfolio.store import PortfolioStore
from ._chartis_kit import (
    chartis_shell, ck_kpi_block, ck_panel, ck_section_intro,
)
from .brand import PALETTE


def _stage_badge(stage: str) -> str:
    """Stage pill — uses the editorial navy/teal palette uniformly so
    the funnel reads as a coherent gradient instead of a multi-coloured
    candy bar. Tone shifts subtly by stage progression: muted-bone for
    early funnel (screening/outreach), teal-deep for mid-funnel
    (loi/diligence/ic), navy/positive/negative for terminal states.
    """
    tone_map = {
        "screening": ("var(--sc-bone,#ece6db)",  "var(--sc-navy,#0b2341)"),
        "outreach":  ("var(--sc-teal-2,#3d7d77)", "#fff"),
        "loi":       ("var(--sc-teal,#155752)",  "#fff"),
        "diligence": ("var(--sc-navy-3,#1d3c69)","#fff"),
        "ic":        ("var(--sc-navy-2,#13294a)","#fff"),
        "closed":    ("var(--sc-positive,#0a8a5f)", "#fff"),
        "passed":    ("var(--sc-text-faint,#7a8699)", "#fff"),
    }
    bg, fg = tone_map.get(stage, ("var(--sc-bone,#ece6db)", "var(--sc-navy,#0b2341)"))
    return (
        f'<span style="background:{bg};color:{fg};padding:4px 10px;'
        f'border-radius:2px;font-family:var(--sc-sans);'
        f'font-size:10.5px;font-weight:700;letter-spacing:0.08em;'
        f'text-transform:uppercase;">{_html.escape(stage)}</span>'
    )


def _funnel_bar_color(stage: str) -> str:
    """Bar fill — same family as the badge, but always the deep teal
    spine so the eye reads counts left-to-right without colour jumping
    around. Terminal states (closed/passed) shift to status colours."""
    if stage == "closed":
        return "var(--sc-positive,#0a8a5f)"
    if stage == "passed":
        return "var(--sc-text-faint,#7a8699)"
    return "var(--sc-teal,#155752)"


def _priority_dot(priority: str) -> str:
    colors = {"high": "var(--cad-neg)", "medium": "var(--cad-warn)", "low": "var(--cad-text3)"}
    return f'<span style="color:{colors.get(priority, "var(--cad-text3)")};font-size:16px;">●</span>'


def _fm(val: float) -> str:
    if abs(val) >= 1e9:
        return f"${val/1e9:.1f}B"
    if abs(val) >= 1e6:
        return f"${val/1e6:.0f}M"
    if abs(val) >= 1e3:
        return f"${val/1e3:.0f}K"
    return f"${val:,.0f}"


def render_pipeline(db_path: str) -> str:
    """Render the deal pipeline page."""
    from ..data.pipeline import (
        PIPELINE_STAGES, list_searches, list_pipeline,
        pipeline_summary, get_activity,
    )

    # Route through PortfolioStore (campaign target 4E) so the
    # connection inherits PRAGMA foreign_keys=ON, busy_timeout=
    # 5000, and row_factory=Row instead of running on a bare
    # sqlite3.connect that misses all three.
    with PortfolioStore(db_path).connect() as con:
        searches = list_searches(con)
        hospitals = list_pipeline(con)
        summary = pipeline_summary(con)
        activity = get_activity(con, limit=15)

    total = len(hospitals)
    active = sum(1 for h in hospitals if h.stage not in ("closed", "passed"))

    # ── Editorial intro + KPI strip ──
    intro = ck_section_intro(
        eyebrow="DEAL PIPELINE",
        headline="How prospects flow from screening to close.",
        italic_word="flow",
        body=(
            f"{total} hospitals in pipeline · {active} active · "
            f"{summary.get('diligence', 0)} in diligence · "
            f"{summary.get('closed', 0)} closed · "
            f"{len(searches)} saved searches."
        ),
    )
    kpis = (
        '<div class="ck-kpi-strip">'
        + ck_kpi_block("In Pipeline", f"{total}")
        + ck_kpi_block("Active", f"{active}")
        + ck_kpi_block("In Diligence", f"{summary.get('diligence', 0)}")
        + ck_kpi_block("Closed", f"{summary.get('closed', 0)}")
        + ck_kpi_block("Saved Searches", f"{len(searches)}")
        + '</div>'
    )

    # ── Funnel visualization ──
    # Editorial table-style: stage badge | description | bar | count.
    # Roomier than the prior 4px/20px-bar layout — 14px row padding,
    # 32px bar height, named description column so the partner sees
    # the stage's plain-English meaning without hovering anything.
    funnel_bars = ""
    max_count = max(summary.values()) if summary else 1
    for stage_key, stage_label, stage_desc in PIPELINE_STAGES:
        count = summary.get(stage_key, 0)
        pct = count / max_count * 100 if max_count > 0 and count > 0 else 0
        bar_color = _funnel_bar_color(stage_key)
        # Greyed row when the stage is empty — keeps the structure
        # present (every stage visible) but doesn't draw the eye.
        empty_cls = ' style="opacity:0.45;"' if count == 0 else ""
        funnel_bars += (
            f'<div class="ck-funnel-row"{empty_cls}>'
            f'<div class="ck-funnel-stage">{_stage_badge(stage_key)}'
            f'<span class="ck-funnel-stage-desc">{_html.escape(stage_desc)}</span>'
            f'</div>'
            f'<div class="ck-funnel-track">'
            f'<div class="ck-funnel-fill" style="width:{max(pct, 1.5):.1f}%;'
            f'background:{bar_color};"></div>'
            f'</div>'
            f'<div class="ck-funnel-count">{count}</div>'
            f'</div>'
        )

    funnel_css = (
        '<style>'
        '.ck-funnel-row{display:grid;grid-template-columns:230px 1fr 56px;'
        'align-items:center;gap:18px;padding:12px 4px;'
        'border-bottom:1px solid var(--sc-rule,#d6cfc3);}'
        '.ck-funnel-row:last-child{border-bottom:0;}'
        '.ck-funnel-stage{display:flex;flex-direction:column;gap:4px;}'
        '.ck-funnel-stage-desc{font-family:var(--sc-serif,Georgia,serif);'
        'font-size:12.5px;color:var(--sc-text-dim,#465366);line-height:1.35;}'
        '.ck-funnel-track{position:relative;height:28px;'
        'background:var(--sc-bone,#ece6db);border-radius:2px;overflow:hidden;}'
        '.ck-funnel-fill{position:absolute;top:0;left:0;height:100%;'
        'border-radius:2px;transition:width 0.25s ease-out;}'
        '.ck-funnel-count{font-family:var(--sc-mono,JetBrains Mono,monospace);'
        'font-size:18px;font-weight:600;color:var(--sc-navy,#0b2341);'
        'text-align:right;font-variant-numeric:tabular-nums;}'
        '@media (max-width:720px){.ck-funnel-row{grid-template-columns:1fr 56px;}'
        '.ck-funnel-track{grid-column:1/-1;}}'
        '</style>'
    )

    funnel = (
        f'{funnel_css}'
        + ck_panel(
            '<p class="ck-section-body">'
            'How prospects flow from screening to close. '
            'Empty stages remain visible at low opacity so the funnel '
            'shape stays readable.</p>'
            f'{funnel_bars}',
            title="Pipeline Funnel",
        )
    )

    # ── Saved searches ──
    search_rows = ""
    for s in searches:
        filters_str = " · ".join(
            f'{k}={v}' for k, v in s.filters.items() if v and v != "all" and v != "9999"
        )[:60]
        last_run = s.last_run_at[:10] if s.last_run_at else "never"
        qs = "&".join(f'{k}={v}' for k, v in s.filters.items() if v)
        search_rows += (
            f'<tr>'
            f'<td style="font-weight:500;">'
            f'<a href="/predictive-screener?{_html.escape(qs)}" '
            f'style="color:var(--cad-link);text-decoration:none;">{_html.escape(s.name)}</a></td>'
            f'<td style="font-size:11px;color:var(--cad-text2);">{_html.escape(filters_str)}</td>'
            f'<td class="num">{s.last_result_count}</td>'
            f'<td style="font-size:11px;color:var(--cad-text3);">{last_run}</td>'
            f'</tr>'
        )

    if search_rows:
        search_inner = (
            '<p class="ck-section-body">'
            '<a href="/predictive-screener" class="cad-btn cad-btn-primary">New Search</a></p>'
            '<table class="cad-table"><thead><tr>'
            '<th>Name</th><th>Filters</th><th>Results</th><th>Last Run</th>'
            f'</tr></thead><tbody>{search_rows}</tbody></table>'
        )
    else:
        search_inner = (
            '<p class="ck-section-body">'
            'No saved searches yet. Run a search in the '
            '<a href="/predictive-screener" class="ck-link">Deal Screener</a> '
            'and save it.</p>'
            '<p class="ck-section-body">'
            '<a href="/predictive-screener" class="cad-btn cad-btn-primary">New Search</a></p>'
        )
    search_section = ck_panel(
        search_inner, title=f"Saved Searches ({len(searches)})",
    )

    # ── Enrich pipeline hospitals with HCRIS data ──
    hcris_lookup = {}
    try:
        from ..data.hcris import _get_latest_per_ccn
        hdf = _get_latest_per_ccn()
        for _, row in hdf.iterrows():
            c = str(row.get("ccn", ""))
            if c:
                rev = float(row.get("net_patient_revenue", 0) or 0)
                opex = float(row.get("operating_expenses", 0) or 0)
                margin = (rev - opex) / rev if rev > 1e5 else 0
                hcris_lookup[c] = {"revenue": rev, "margin": margin}
    except Exception:
        pass

    # ── Pipeline hospitals table ──
    hospital_rows = ""
    for h in hospitals:
        ccn = _html.escape(h.ccn)
        name = _html.escape(h.hospital_name[:25])
        hcris = hcris_lookup.get(h.ccn, {})
        rev = hcris.get("revenue", 0)
        margin = hcris.get("margin", 0)
        margin_cls = "cad-pos" if margin > 0.05 else ("cad-warn" if margin > 0 else "cad-neg")
        rev_str = _fm(rev) if rev > 0 else "—"
        margin_str = f"{margin:.1%}" if rev > 0 else "—"

        # Stage advancement form
        stage_idx = next((i for i, (sk, _, _) in enumerate(PIPELINE_STAGES) if sk == h.stage), 0)
        next_stages = PIPELINE_STAGES[stage_idx + 1:stage_idx + 3] if stage_idx < len(PIPELINE_STAGES) - 1 else []
        advance_links = ""
        for ns_key, ns_label, _ in next_stages:
            advance_links += (
                f'<form method="POST" action="/pipeline/stage/{ccn}" class="pp-advance-form">'
                f'<input type="hidden" name="stage" value="{ns_key}">'
                f'<button type="submit" class="pp-advance-btn">→{ns_label[:8]}</button></form> '
            )

        hospital_rows += (
            f'<tr>'
            f'<td>{_priority_dot(h.priority)}</td>'
            f'<td><a href="/hospital/{ccn}" class="ck-link"><strong>{name}</strong></a></td>'
            f'<td>{_html.escape(h.state)}</td>'
            f'<td class="num">{h.beds}</td>'
            f'<td class="num">{rev_str}</td>'
            f'<td class="num {margin_cls}">{margin_str}</td>'
            f'<td>{_stage_badge(h.stage)} {advance_links}</td>'
            f'<td>'
            f'<a href="/ebitda-bridge/{ccn}" class="ck-link">Bridge</a> · '
            f'<a href="/ic-memo/{ccn}" class="ck-link">Memo</a> · '
            f'<a href="/data-room/{ccn}" class="ck-link">Data</a></td>'
            f'</tr>'
        )

    if hospital_rows:
        pipeline_table = ck_panel(
            '<p class="ck-section-body">'
            f'<a href="/pipeline/bridge" class="cad-btn cad-btn-primary">Portfolio EBITDA Bridge</a></p>'
            '<table class="cad-table"><thead><tr>'
            '<th></th><th>Hospital</th><th>State</th><th>Beds</th>'
            '<th>Revenue</th><th>Margin</th><th>Stage</th><th>Actions</th>'
            f'</tr></thead><tbody>{hospital_rows}</tbody></table>',
            title=f"Pipeline Hospitals ({total})",
        )
    else:
        # Replace the bare "No hospitals" line with an editorial
        # empty-state card so the page reads as deliberate and gives
        # the partner a one-click path to fill it.
        from ._chartis_kit import ck_empty_state
        pipeline_table = ck_empty_state(
            "No hospitals in the pipeline yet.",
            body=(
                "Run the Predictive Screener against your thesis "
                "and click “+ PIPE” on any result row to "
                "add a target. The funnel above shows zero counts "
                "until you add at least one hospital."
            ),
            eyebrow="GET STARTED",
            icon="◆",
            cta_label="Open Predictive Screener",
            cta_href="/predictive-screener",
        )

    # ── Recent activity ──
    activity_items = ""
    for a in activity[:10]:
        action = a["action"]
        if action == "stage_change":
            text = f'{a["old_value"]} → {a["new_value"]}'
        elif action == "added":
            text = f'Added at {a["new_value"]}'
        else:
            text = action
        activity_items += (
            '<div class="pp-activity-row">'
            f'<span class="pp-activity-date">{a["created_at"][:10]}</span>'
            f'<a href="/hospital/{_html.escape(a["ccn"])}" class="ck-link pp-activity-ccn">'
            f'{_html.escape(a["ccn"])}</a>'
            f'<span>{_html.escape(text)}</span></div>'
        )

    activity_section = ""
    if activity_items:
        activity_section = ck_panel(
            activity_items, title="Recent Activity",
        )

    nav = ck_panel(
        '<p class="ck-section-body">'
        '<a href="/predictive-screener" class="cad-btn cad-btn-primary">Deal Screener</a> '
        '<a href="/portfolio/monitor" class="cad-btn">Portfolio Monitor</a> '
        '<a href="/ml-insights" class="cad-btn">ML Insights</a>'
        '</p>',
        title="Cross-links",
    )

    pp_styles = """
<style>
.pp-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;}
.pp-advance-form{display:inline;}
.pp-advance-btn{background:none;border:none;color:var(--cad-link);
cursor:pointer;font-size:10px;padding:0;}
.pp-activity-row{display:flex;gap:8px;padding:4px 0;font-size:12px;
border-bottom:1px solid var(--cad-border);}
.pp-activity-date{color:var(--cad-text3);width:70px;font-size:10px;}
.pp-activity-ccn{width:60px;}
</style>
"""
    body = (
        f'{pp_styles}{intro}{kpis}'
        '<div class="pp-grid">'
        f'<div>{funnel}{search_section}</div>'
        f'<div>{activity_section}</div></div>'
        f'{pipeline_table}{nav}'
    )

    return chartis_shell(
        body, "Deal Pipeline",
        active_nav="/pipeline",
        subtitle=f"{total} hospitals | {active} active | {len(searches)} saved searches",
    )
