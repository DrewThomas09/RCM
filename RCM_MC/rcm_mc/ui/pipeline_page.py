"""SeekingChartis Deal Pipeline — saved searches and hospital tracking.

The workflow platform: analysts save screener filters, add hospitals to
the pipeline, track them through stages, and see the funnel at a glance.
"""
from __future__ import annotations

import html as _html
import json
from typing import Any, Dict, List, Optional

from ..portfolio.store import PortfolioStore
from ._chartis_kit import chartis_shell
from .brand import PALETTE


def _stage_badge(stage: str) -> str:
    colors = {
        "screening": "var(--cad-text3)", "outreach": "var(--cad-accent)",
        "loi": "#8b5cf6", "diligence": "var(--cad-warn)",
        "ic": "#e67e22", "closed": "var(--cad-pos)", "passed": "var(--cad-neg)",
    }
    c = colors.get(stage, "var(--cad-text3)")
    return (
        f'<span style="background:{c};color:#fff;padding:2px 8px;border-radius:3px;'
        f'font-size:10px;font-weight:600;text-transform:uppercase;">'
        f'{_html.escape(stage)}</span>'
    )


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

    # ── KPIs ──
    kpis = (
        f'<div class="cad-kpi-grid" style="grid-template-columns:repeat(5,1fr);">'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{total}</div>'
        f'<div class="cad-kpi-label">In Pipeline</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{active}</div>'
        f'<div class="cad-kpi-label">Active</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{summary.get("diligence", 0)}</div>'
        f'<div class="cad-kpi-label">In Diligence</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value" style="color:var(--cad-pos);">'
        f'{summary.get("closed", 0)}</div>'
        f'<div class="cad-kpi-label">Closed</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{len(searches)}</div>'
        f'<div class="cad-kpi-label">Saved Searches</div></div>'
        f'</div>'
    )

    # ── Funnel visualization ──
    funnel_bars = ""
    max_count = max(summary.values()) if summary else 1
    for stage_key, stage_label, stage_desc in PIPELINE_STAGES:
        count = summary.get(stage_key, 0)
        pct = count / max_count * 100 if max_count > 0 and count > 0 else 0
        funnel_bars += (
            f'<div style="display:flex;align-items:center;gap:8px;padding:4px 0;">'
            f'<div style="width:90px;font-size:11px;font-weight:500;">{_stage_badge(stage_key)}</div>'
            f'<div style="flex:1;background:var(--cad-bg3);border-radius:3px;height:20px;">'
            f'<div style="width:{max(pct, 2):.0f}%;background:var(--cad-accent);border-radius:3px;'
            f'height:20px;display:flex;align-items:center;justify-content:center;'
            f'font-size:10px;color:#fff;font-weight:600;min-width:20px;">'
            f'{count}</div></div></div>'
        )

    funnel = (
        f'<div class="cad-card">'
        f'<h2>Pipeline Funnel</h2>'
        f'{funnel_bars}</div>'
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

    search_section = (
        f'<div class="cad-card">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">'
        f'<h2 style="margin:0;">Saved Searches ({len(searches)})</h2>'
        f'<a href="/predictive-screener" class="cad-btn cad-btn-primary" '
        f'style="text-decoration:none;font-size:11px;">New Search</a></div>'
    )
    if search_rows:
        search_section += (
            f'<table class="cad-table"><thead><tr>'
            f'<th>Name</th><th>Filters</th><th>Results</th><th>Last Run</th>'
            f'</tr></thead><tbody>{search_rows}</tbody></table>'
        )
    else:
        search_section += (
            f'<p style="font-size:12px;color:var(--cad-text3);padding:8px 0;">'
            f'No saved searches yet. Run a search in the '
            f'<a href="/predictive-screener" style="color:var(--cad-link);">Deal Screener</a> '
            f'and save it.</p>'
        )
    search_section += '</div>'

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
        margin_color = "var(--cad-pos)" if margin > 0.05 else ("var(--cad-warn)" if margin > 0 else "var(--cad-neg)")
        rev_str = _fm(rev) if rev > 0 else "—"
        margin_str = f"{margin:.1%}" if rev > 0 else "—"

        # Stage advancement form
        stage_idx = next((i for i, (sk, _, _) in enumerate(PIPELINE_STAGES) if sk == h.stage), 0)
        next_stages = PIPELINE_STAGES[stage_idx + 1:stage_idx + 3] if stage_idx < len(PIPELINE_STAGES) - 1 else []
        advance_links = ""
        for ns_key, ns_label, _ in next_stages:
            advance_links += (
                f'<form method="POST" action="/pipeline/stage/{ccn}" style="display:inline;">'
                f'<input type="hidden" name="stage" value="{ns_key}">'
                f'<button type="submit" style="background:none;border:none;color:var(--cad-link);'
                f'cursor:pointer;font-size:10px;padding:0;">→{ns_label[:8]}</button></form> '
            )

        hospital_rows += (
            f'<tr>'
            f'<td>{_priority_dot(h.priority)}</td>'
            f'<td><a href="/hospital/{ccn}" '
            f'style="color:var(--cad-link);text-decoration:none;font-weight:500;">'
            f'{name}</a></td>'
            f'<td>{_html.escape(h.state)}</td>'
            f'<td class="num">{h.beds}</td>'
            f'<td class="num">{rev_str}</td>'
            f'<td class="num" style="color:{margin_color};">{margin_str}</td>'
            f'<td>{_stage_badge(h.stage)} {advance_links}</td>'
            f'<td style="font-size:10px;">'
            f'<a href="/ebitda-bridge/{ccn}" style="color:var(--cad-link);text-decoration:none;">Bridge</a> · '
            f'<a href="/ic-memo/{ccn}" style="color:var(--cad-link);text-decoration:none;">Memo</a> · '
            f'<a href="/data-room/{ccn}" style="color:var(--cad-link);text-decoration:none;">Data</a></td>'
            f'</tr>'
        )

    pipeline_table = (
        f'<div class="cad-card">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;">'
        f'<h2 style="margin:0;">Pipeline Hospitals ({total})</h2>'
        f'<a href="/pipeline/bridge" class="cad-btn" '
        f'style="text-decoration:none;font-size:11px;background:var(--cad-pos);color:#fff;">'
        f'Portfolio EBITDA Bridge</a></div>'
    )
    if hospital_rows:
        pipeline_table += (
            f'<table class="cad-table"><thead><tr>'
            f'<th></th><th>Hospital</th><th>State</th><th>Beds</th>'
            f'<th>Revenue</th><th>Margin</th><th>Stage</th><th>Actions</th>'
            f'</tr></thead><tbody>{hospital_rows}</tbody></table>'
        )
    else:
        pipeline_table += (
            f'<p style="font-size:12px;color:var(--cad-text3);padding:8px 0;">'
            f'No hospitals in the pipeline yet. '
            f'<a href="/predictive-screener" style="color:var(--cad-link);">Screen hospitals</a> '
            f'and click "Add to Pipeline" on any profile page.</p>'
        )
    pipeline_table += '</div>'

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
            f'<div style="display:flex;gap:8px;padding:4px 0;font-size:12px;'
            f'border-bottom:1px solid var(--cad-border);">'
            f'<span style="color:var(--cad-text3);width:70px;font-size:10px;">'
            f'{a["created_at"][:10]}</span>'
            f'<a href="/hospital/{_html.escape(a["ccn"])}" '
            f'style="color:var(--cad-link);text-decoration:none;width:60px;">'
            f'{_html.escape(a["ccn"])}</a>'
            f'<span style="color:var(--cad-text2);">{_html.escape(text)}</span></div>'
        )

    activity_section = ""
    if activity_items:
        activity_section = (
            f'<div class="cad-card">'
            f'<h2>Recent Activity</h2>'
            f'{activity_items}</div>'
        )

    # ── Nav ──
    nav = (
        f'<div class="cad-card" style="display:flex;gap:8px;flex-wrap:wrap;">'
        f'<a href="/predictive-screener" class="cad-btn cad-btn-primary" '
        f'style="text-decoration:none;">Deal Screener</a>'
        f'<a href="/portfolio/monitor" class="cad-btn" '
        f'style="text-decoration:none;">Portfolio Monitor</a>'
        f'<a href="/ml-insights" class="cad-btn" '
        f'style="text-decoration:none;">ML Insights</a>'
        f'</div>'
    )

    body = (
        f'{kpis}'
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">'
        f'<div>{funnel}{search_section}</div>'
        f'<div>{activity_section}</div></div>'
        f'{pipeline_table}{nav}'
    )

    return chartis_shell(
        body, "Deal Pipeline",
        active_nav="/pipeline",
        subtitle=f"{total} hospitals | {active} active | {len(searches)} saved searches",
    )
