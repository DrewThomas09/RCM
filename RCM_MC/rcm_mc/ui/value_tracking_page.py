"""SeekingChartis Value Creation Tracker — actual vs plan, lever by lever.

Shows the frozen EBITDA bridge plan alongside quarterly actuals.
Computes realization rates, detects ramp deviations, and feeds
accuracy back to the prediction ledger.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional

from ._chartis_kit import chartis_shell
from ._glossary_link import metric_label_link
from ..portfolio.store import PortfolioStore
from .brand import PALETTE


# ── Phase 4A: lever-name → /metric-glossary anchor link ──
# pe.value_tracker stores lever NAMES (not metric keys) because
# the helper module is in the restricted package list. Build a
# name→glossary-key reverse table by reading _LEVER_CONFIG from
# the bridge module — single source of truth, computed once at
# import. The bridge's "cmi" maps to glossary "case_mix_index".
def _build_lever_name_index() -> Dict[str, str]:
    from .ebitda_bridge_page import (
        _LEVER_CONFIG,
        _LEVER_METRIC_TO_GLOSSARY,
    )
    out: Dict[str, str] = {}
    for cfg in _LEVER_CONFIG:
        m = cfg["metric"]
        out[cfg["name"]] = _LEVER_METRIC_TO_GLOSSARY.get(m, m)
    return out


_LEVER_NAME_TO_GLOSSARY_KEY: Dict[str, str] = _build_lever_name_index()


def _fm(val: float) -> str:
    if abs(val) >= 1e9:
        return f"${val/1e9:.2f}B"
    if abs(val) >= 1e6:
        return f"${val/1e6:.1f}M"
    if abs(val) >= 1e3:
        return f"${val/1e3:.0f}K"
    return f"${val:,.0f}"


def _status_badge(status: str) -> str:
    colors = {"on_track": "var(--cad-pos)", "lagging": "var(--cad-warn)", "off_track": "var(--cad-neg)"}
    labels = {"on_track": "On Track", "lagging": "Lagging", "off_track": "Off Track"}
    c = colors.get(status, "var(--cad-text3)")
    l = labels.get(status, status)
    return f'<span style="background:{c};color:#fff;padding:2px 7px;border-radius:3px;font-size:10px;font-weight:600;">{l}</span>'


def render_value_tracker(
    deal_id: str,
    db_path: str,
) -> str:
    """Render the value creation tracking page for a deal."""
    from ..pe.value_tracker import (
        get_plan, get_tracking_summary, _ensure_tables,
    )

    # Route through PortfolioStore (campaign target 4E) so this read
    # inherits busy_timeout=5000, foreign_keys=ON, and Row factory
    # alongside every other deal-aware page.
    with PortfolioStore(db_path).connect() as con:
        _ensure_tables(con)
        plan_data = get_plan(con, deal_id)
        summary = get_tracking_summary(con, deal_id)

    if not plan_data:
        return chartis_shell(
            f'<div class="cad-card">'
            f'<h2>No Value Creation Plan</h2>'
            f'<p style="color:var(--cad-text2);font-size:13px;margin-bottom:12px;">'
            f'No EBITDA bridge has been frozen as a plan for this deal. '
            f'To create a plan, go to the EBITDA bridge and click "Freeze as Plan."</p>'
            f'<div style="display:flex;gap:8px;">'
            f'<a href="/ebitda-bridge/{_html.escape(deal_id)}" class="cad-btn cad-btn-primary" '
            f'style="text-decoration:none;">EBITDA Bridge</a>'
            f'<a href="/pipeline" class="cad-btn" style="text-decoration:none;">Pipeline</a>'
            f'</div></div>',
            f"Value Tracker — {_html.escape(deal_id)}",
        )

    plan = plan_data["plan"]
    name = _html.escape(plan_data["hospital_name"])
    ccn = _html.escape(plan_data.get("ccn", deal_id))
    levers = plan.get("levers", [])

    # ── KPIs ──
    total_planned = plan_data["total_planned"]
    total_realized = summary.total_realized if summary else 0
    realization = summary.realization_pct if summary else 0
    quarters = summary.quarters_tracked if summary else 0
    real_color = "var(--cad-pos)" if realization >= 0.85 else ("var(--cad-warn)" if realization >= 0.6 else "var(--cad-neg)")

    kpis = (
        f'<div class="cad-kpi-grid" style="grid-template-columns:repeat(5,1fr);">'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{_fm(total_planned)}</div>'
        f'<div class="cad-kpi-label">Planned Uplift</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value" style="color:{real_color};">'
        f'{_fm(total_realized)}</div>'
        f'<div class="cad-kpi-label">Realized</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value" style="color:{real_color};">'
        f'{realization:.0%}</div>'
        f'<div class="cad-kpi-label">Realization</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{quarters}</div>'
        f'<div class="cad-kpi-label">Quarters Tracked</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">'
        f'{summary.on_track_count if summary else 0}</div>'
        f'<div class="cad-kpi-label">Levers On Track</div></div>'
        f'</div>'
    )

    # ── Ramp assessment ──
    ramp_banner = ""
    if summary:
        ramp_color = "var(--cad-pos)" if summary.realization_pct >= 0.85 else (
            "var(--cad-warn)" if summary.realization_pct >= 0.6 else "var(--cad-neg)")
        ramp_banner = (
            f'<div class="cad-card" style="border-left:3px solid {ramp_color};">'
            f'<p style="font-size:13px;font-weight:500;color:var(--cad-text);">'
            f'{_html.escape(summary.ramp_assessment)}</p></div>'
        )

    # ── Lever-by-lever comparison ──
    lever_rows = ""
    if summary:
        for lev in summary.levers:
            r_pct = lev["realization_pct"]
            bar_pct = min(100, abs(r_pct) * 100)
            bar_color = "var(--cad-pos)" if r_pct >= 0.85 else ("var(--cad-warn)" if r_pct >= 0.6 else "var(--cad-neg)")
            lever_rows += (
                f'<tr>'
                f'<td style="font-weight:500;">{metric_label_link(lev["lever"][:25], _LEVER_NAME_TO_GLOSSARY_KEY.get(lev["lever"], ""))}</td>'
                f'<td class="num">{_fm(lev["planned"])}</td>'
                f'<td class="num" style="font-weight:600;">{_fm(lev["actual"])}</td>'
                f'<td class="num" style="color:{bar_color};font-weight:600;">{r_pct:.0%}</td>'
                f'<td><div style="background:var(--cad-bg3);border-radius:3px;height:10px;width:80px;">'
                f'<div style="width:{bar_pct:.0f}%;background:{bar_color};border-radius:3px;'
                f'height:10px;"></div></div></td>'
                f'<td>{_status_badge(lev["status"])}</td>'
                f'</tr>'
            )

    lever_table = ""
    if lever_rows:
        lever_table = (
            f'<div class="cad-card">'
            f'<h2>Lever-by-Lever Comparison</h2>'
            f'<p style="font-size:12px;color:var(--cad-text2);margin-bottom:10px;">'
            f'Planned impact from the frozen EBITDA bridge vs cumulative quarterly actuals. '
            f'On Track = &ge;85% realization. Lagging = 60-85%. Off Track = &lt;60%.</p>'
            f'<table class="cad-table"><thead><tr>'
            f'<th>Lever</th><th>Planned</th><th>Actual</th><th>Realization</th>'
            f'<th></th><th>Status</th>'
            f'</tr></thead><tbody>{lever_rows}</tbody></table></div>'
        )

    # ── Bridge plan (frozen at close) ──
    bridge_levers = ""
    for lev in levers:
        if lev.get("ebitda_impact", 0) == 0:
            continue
        bridge_levers += (
            f'<tr>'
            f'<td>{metric_label_link(lev["name"][:25], _LEVER_NAME_TO_GLOSSARY_KEY.get(lev["name"], ""))}</td>'
            f'<td class="num">{_fm(lev["ebitda_impact"])}</td>'
            f'<td class="num">{lev["ramp_months"]}mo</td>'
            f'</tr>'
        )

    plan_section = (
        f'<div class="cad-card">'
        f'<h2>Frozen Bridge Plan (at close)</h2>'
        f'<p style="font-size:12px;color:var(--cad-text3);margin-bottom:8px;">'
        f'Created {plan_data["created_at"][:10]}</p>'
        f'<table class="cad-table"><thead><tr>'
        f'<th>Lever</th><th>Annual Impact</th><th>Ramp</th>'
        f'</tr></thead><tbody>{bridge_levers}</tbody></table></div>'
    )

    # ── Data entry form ──
    lever_options = ""
    for lev in levers:
        if lev.get("ebitda_impact", 0) == 0:
            continue
        lever_options += f'<option value="{_html.escape(lev["name"])}">{_html.escape(lev["name"])}</option>'

    entry_form = (
        f'<div class="cad-card" style="border-left:3px solid var(--cad-accent);">'
        f'<h2>Record Quarterly Actual</h2>'
        f'<form method="POST" action="/value-tracker/{_html.escape(deal_id)}/record" '
        f'style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:10px;">'
        f'<div><label style="font-size:11px;color:var(--cad-text3);display:block;margin-bottom:3px;">'
        f'Quarter</label>'
        f'<input type="text" name="quarter" placeholder="2026Q1" required '
        f'style="width:100%;padding:6px 10px;border:1px solid var(--cad-border);border-radius:4px;'
        f'background:var(--cad-bg3);color:var(--cad-text);font-size:12px;box-sizing:border-box;"></div>'
        f'<div><label style="font-size:11px;color:var(--cad-text3);display:block;margin-bottom:3px;">'
        f'Lever</label>'
        f'<select name="lever" required style="width:100%;padding:6px 10px;border:1px solid var(--cad-border);'
        f'border-radius:4px;background:var(--cad-bg3);color:var(--cad-text);font-size:12px;">'
        f'{lever_options}</select></div>'
        f'<div><label style="font-size:11px;color:var(--cad-text3);display:block;margin-bottom:3px;">'
        f'Actual Impact ($)</label>'
        f'<input type="number" name="actual_impact" step="any" required '
        f'style="width:100%;padding:6px 10px;border:1px solid var(--cad-border);border-radius:4px;'
        f'background:var(--cad-bg3);color:var(--cad-text);font-size:12px;box-sizing:border-box;"></div>'
        f'<div style="display:flex;align-items:flex-end;">'
        f'<button type="submit" class="cad-btn cad-btn-primary" style="width:100%;">Record</button>'
        f'</div></form></div>'
    )

    # ── Nav ──
    nav = (
        f'<div class="cad-card" style="display:flex;gap:8px;flex-wrap:wrap;">'
        f'<a href="/hospital/{ccn}" class="cad-btn cad-btn-primary" '
        f'style="text-decoration:none;">Hospital Profile</a>'
        f'<a href="/ebitda-bridge/{ccn}" class="cad-btn" '
        f'style="text-decoration:none;">EBITDA Bridge</a>'
        f'<a href="/pipeline" class="cad-btn" '
        f'style="text-decoration:none;">Pipeline</a>'
        f'<a href="/portfolio/monitor" class="cad-btn" '
        f'style="text-decoration:none;">Portfolio Monitor</a>'
        f'</div>'
    )

    body = f'{kpis}{ramp_banner}{lever_table}{entry_form}{plan_section}{nav}'

    return chartis_shell(
        body,
        f"Value Tracker — {name}",
        subtitle=(
            f"{_html.escape(deal_id)} | "
            f"Planned {_fm(total_planned)} | Realized {_fm(total_realized)} "
            f"({realization:.0%}) | {quarters} quarters"
        ),
    )
