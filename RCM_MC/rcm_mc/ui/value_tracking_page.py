"""PE Desk Value Creation Tracker — actual vs plan, lever by lever.

Shows the frozen EBITDA bridge plan alongside quarterly actuals.
Computes realization rates, detects ramp deviations, and feeds
accuracy back to the prediction ledger.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional

from ._chartis_kit import (
    chartis_shell, ck_fmt_num, ck_fmt_pct, ck_kpi_block,
    ck_next_section, ck_provenance_tooltip, ck_value_anchor,
)
from ._glossary_link import metric_label_link
from ._provenance_tooltip import provenance_tooltip
from ..portfolio.store import PortfolioStore
from ..provenance.graph import NodeType, ProvenanceGraph, ProvenanceNode
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


_VT_CHART_CAPTION_CSS = (
    ".vt-figcap{font-size:11px;color:#6b6456;margin:6px 0 8px;"
    "font-family:'JetBrains Mono',ui-monospace,monospace;"
    "letter-spacing:0.02em;}"
)


def _realization_chart(
    levers: List[Dict[str, Any]], width: int = 700, row_h: int = 26
) -> str:
    """Horizontal realization-% bars per lever with on-track/lagging bands.

    Each lever's realization (actual ÷ planned) is a bar tone-coded
    green (≥85%, on track), amber (60–85%, lagging), red (<60%, off
    track) — matching the table's status column — with dashed 60% and
    85% reference lines so a partner sees who is hitting plan at a
    glance. Reads the same realization_pct the table shows; empty
    input returns "".
    """
    rows = [lev for lev in (levers or []) if lev.get("lever")]
    if not rows:
        return ""

    pad_l, pad_r, pad_t = 180, 56, 16
    bar_max = width - pad_l - pad_r
    height = pad_t + row_h * len(rows) + 22
    # Scale axis to the largest realization (cap headroom at 120%).
    axis_max = max(1.0, min(1.5, max(
        (lev.get("realization_pct", 0) for lev in rows), default=1.0)))

    pos = PALETTE["positive"]
    warn = PALETTE["warning"]
    neg = PALETTE["negative"]
    rule = PALETTE.get("border", "#BFB6A2")
    txt = PALETTE.get("text_secondary", "#4a5568")
    mut = PALETTE.get("text_muted", "#8a8270")

    def _x(frac: float) -> float:
        return pad_l + max(0.0, min(axis_max, frac)) / axis_max * bar_max

    parts: List[str] = [
        f'<svg viewBox="0 0 {width} {height}" '
        f'preserveAspectRatio="xMidYMid meet" role="img" '
        f'aria-label="Realization percent by value-creation lever" '
        f'style="width:100%;max-width:{width}px;height:auto;'
        f'print-color-adjust:exact;-webkit-print-color-adjust:exact;">'
    ]
    parts.append(
        f'<line x1="{pad_l}" y1="{pad_t - 4}" x2="{pad_l}" '
        f'y2="{height - 18}" stroke="{rule}" stroke-width="1"/>'
    )
    # Reference lines at 60% and 85%.
    for ref, col, lbl in ((0.6, warn, "60%"), (0.85, pos, "85%")):
        rx = _x(ref)
        parts.append(
            f'<line x1="{rx:.1f}" y1="{pad_t - 4}" x2="{rx:.1f}" '
            f'y2="{height - 18}" stroke="{col}" stroke-width="1" '
            f'stroke-dasharray="4 3" opacity="0.5"/>'
            f'<text x="{rx:.1f}" y="{height - 6}" text-anchor="middle" '
            f'font-size="9" font-family="JetBrains Mono,ui-monospace,monospace" '
            f'fill="{col}">{lbl}</text>'
        )
    for i, lev in enumerate(rows):
        name = _html.escape(str(lev["lever"])[:26])
        r = lev.get("realization_pct", 0)
        color = pos if r >= 0.85 else (warn if r >= 0.6 else neg)
        y = pad_t + i * row_h
        w = _x(r) - pad_l
        parts.append(
            f'<text x="{pad_l - 8}" y="{y + row_h / 2 + 3:.1f}" '
            f'text-anchor="end" font-size="11" '
            f'font-family="Inter Tight,system-ui,sans-serif" '
            f'fill="{txt}">{name}</text>'
        )
        status = str(lev.get("status", "")).replace("_", " ")
        tip = _html.escape(
            f"{lev['lever']}: {r:.0%} realized · "
            f"{_fm(lev.get('actual', 0))} actual vs "
            f"{_fm(lev.get('planned', 0))} planned"
            f"{f' · {status}' if status else ''}"
        )
        parts.append(
            f'<rect x="{pad_l}" y="{y + 4:.1f}" width="{max(w, 0.5):.1f}" '
            f'height="{row_h - 11}" rx="2" fill="{color}" opacity="0.82">'
            f'<title>{tip}</title></rect>'
        )
        parts.append(
            f'<text x="{pad_l + w + 6:.1f}" y="{y + row_h / 2 + 3:.1f}" '
            f'text-anchor="start" font-size="10" '
            f'font-family="JetBrains Mono,ui-monospace,monospace" '
            f'fill="{color}">{r:.0%}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


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

    realization_value = ck_provenance_tooltip(
        "Realization rate",
        f'<span style="color:{real_color};">{ck_fmt_pct(realization)}</span>',
        explainer=(
            "Realized EBITDA uplift divided by planned. Above "
            "85% green (deal tracking ahead of plan); below 60% "
            "red (deal slipping). The lever-by-lever table "
            "below decomposes which initiatives are pulling "
            "ahead vs. behind."
        ),
    )
    kpis = (
        '<div class="ck-kpi-grid" style="grid-template-columns:repeat(5,1fr);">'
        + ck_kpi_block(
            "Planned Uplift", _fm(total_planned), "underwriting target",
            help={
                "definition": (
                    "Aggregate annualized EBITDA the value-creation "
                    "plan underwrote at close — sum across every "
                    "RCM lever (rate, denial, AR, contract terms, "
                    "labor, supply). Becomes the denominator for "
                    "realization tracking."
                ),
            },
        )
        + ck_kpi_block("Realized", f'<span style="color:{real_color};">{_fm(total_realized)}</span>',
                       "actual EBITDA")
        + ck_kpi_block(
            "Realization", realization_value, "% of plan",
            help={
                "definition": (
                    "Realized ÷ planned uplift. Above 100% means the "
                    "team beat underwriting; below 70% at year 3 is "
                    "an LP-update talking point. Plot the trajectory "
                    "via the quarterly scorecard below."
                ),
            },
        )
        + ck_kpi_block("Quarters Tracked", ck_fmt_num(quarters), "of hold")
        + ck_kpi_block(
            "Levers On Track", ck_fmt_num(summary.on_track_count if summary else 0),
            "ahead/on plan",
            help={
                "definition": (
                    "Count of value-creation levers currently "
                    "tracking ahead or on the underwriting curve. "
                    "Healthier than realization alone — a deal "
                    "could be 'on plan' aggregate but with 1 lever "
                    "carrying 3 underperforming ones (high "
                    "concentration risk on the hold)."
                ),
            },
        )
        + '</div>'
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
        # Phase 4C: build a manual ProvenanceGraph with one
        # CALCULATED node per lever realization. Each lever's
        # `actual` value is a sum of quarterly actuals against
        # the frozen plan — a CALCULATED node with source
        # "VALUE_TRACKER" and detail showing the realization
        # percentage. Reuses the loop-109 lever-name → glossary-
        # key reverse table so the metric_key resolves through
        # the same alias path the 4A label link uses.
        prov_graph = ProvenanceGraph()
        for lev in summary.levers:
            g_key = _LEVER_NAME_TO_GLOSSARY_KEY.get(lev["lever"], "")
            if not g_key:
                continue
            actual_val = float(lev.get("actual") or 0.0)
            r_pct_val = float(lev.get("realization_pct") or 0.0)
            prov_graph.add_node(ProvenanceNode(
                id=f"observed:{g_key}",
                label=f"{lev['lever']} (Realized)",
                node_type=NodeType.CALCULATED,
                value=actual_val, unit="USD",
                source="VALUE_TRACKER",
                source_detail=(
                    f"{r_pct_val:.0%} of frozen-plan target across "
                    f"{quarters} quarter(s)"
                ),
            ))
        _first_tooltip = True
        for lev in summary.levers:
            r_pct = lev["realization_pct"]
            bar_pct = min(100, abs(r_pct) * 100)
            bar_color = "var(--cad-pos)" if r_pct >= 0.85 else ("var(--cad-warn)" if r_pct >= 0.6 else "var(--cad-neg)")
            # Phase 4C: hover the actual-value cell to see the
            # realization breakdown.
            _actual_tt = provenance_tooltip(
                label=lev["lever"], value=_fm(lev["actual"]),
                graph=prov_graph,
                metric_key=_LEVER_NAME_TO_GLOSSARY_KEY.get(
                    lev["lever"], "",
                ),
                inject_css=_first_tooltip,
            )
            _first_tooltip = False
            lever_rows += (
                f'<tr>'
                f'<td style="font-weight:500;">{metric_label_link(lev["lever"][:25], _LEVER_NAME_TO_GLOSSARY_KEY.get(lev["lever"], ""))}</td>'
                f'<td class="num">{_fm(lev["planned"])}</td>'
                f'<td class="num" style="font-weight:600;">{_actual_tt}</td>'
                f'<td class="num" style="color:{bar_color};font-weight:600;">{r_pct:.0%}</td>'
                f'<td><div style="background:var(--cad-bg3);border-radius:3px;height:10px;width:80px;">'
                f'<div style="width:{bar_pct:.0f}%;background:{bar_color};border-radius:3px;'
                f'height:10px;"></div></div></td>'
                f'<td>{_status_badge(lev["status"])}</td>'
                f'</tr>'
            )

    lever_table = ""
    if lever_rows:
        _realz_chart = _realization_chart(
            list(summary.levers) if summary else [])
        _realz_fig = (
            f'<style>{_VT_CHART_CAPTION_CSS}</style>'
            f'<div class="vt-figcap">Realization by lever &middot; '
            f'green &ge;85% on track &middot; amber 60&ndash;85% lagging '
            f'&middot; red &lt;60% off track</div>'
            f'{_realz_chart}'
        ) if _realz_chart else ""
        lever_table = (
            f'<div class="cad-card">'
            f'<h2>Lever-by-Lever Comparison</h2>'
            f'<p style="font-size:12px;color:var(--cad-text2);margin-bottom:10px;">'
            f'Planned impact from the frozen EBITDA bridge vs cumulative quarterly actuals. '
            f'On Track = &ge;85% realization. Lagging = 60-85%. Off Track = &lt;60%.</p>'
            f'{_realz_fig}'
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

    # 2026-05-28 batch 30 · Tier-4 trope removal — drops decorative
    # 3px accent stripe on the record-actual form card.
    entry_form = (
        f'<div class="cad-card">'
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

    next_up = ck_next_section(
        "Open the EBITDA bridge",
        f"/ebitda-bridge/{ccn}",
        eyebrow="Continue —",
        italic_word="bridge",
    )
    # Lead takeaway — surface the computed realization (realized vs
    # planned uplift) at the top, before the dense KPI grid. All figures
    # come from the tracking summary; tone tracks the 85%/60% bands.
    _vt_tone = (
        "positive" if realization >= 0.85
        else "warning" if realization >= 0.6
        else "negative"
    )
    lead_anchor = ck_value_anchor(
        "VALUE REALIZATION",
        f"{_fm(total_realized)} realized",
        delta=f"{realization:.0%} of plan",
        opportunity=f"{_fm(total_planned)} planned uplift",
        target=(
            f"{summary.on_track_count if summary else 0} levers on track · "
            f"{quarters}Q tracked"
        ),
        tone=_vt_tone,
    )
    # 2026-05-28 batch 27 · Phase 3 · universal strict 5-block head.
    from ._chartis_kit import ck_editorial_head
    head = ck_editorial_head(
        eyebrow="VALUE TRACKER",
        title=f"Value tracker — {name}",
        meta=(
            # helper escapes meta; pass raw — deal_id is a
            # server-controlled identifier (slugified).
            f"{deal_id.upper()} · "
            f"PLANNED {_fm(total_planned).upper()} · "
            f"REALIZED {_fm(total_realized).upper()} "
            f"({realization:.0%}) · "
            f"{quarters} QUARTER"
            f"{'S' if quarters != 1 else ''}"
        ),
        lede_italic_phrase=(
            "What the value plan actually delivered."
        ),
        lede_body=(
            "Per-lever realization rates: planned EBITDA "
            "uplift vs. quarter-over-quarter actual. The "
            "ramp banner flags whether the deal is tracking "
            "ahead, on plan, or behind — early warnings "
            "surface 1-2 quarters before the gap matters."
        ),
    )
    body = f'{head}{lead_anchor}{kpis}{ramp_banner}{lever_table}{entry_form}{plan_section}{nav}{next_up}'

    # 2026-05-28 wave-B: ck_page_actions adds Copy share link
    # + Back-to-top affordances. Idempotent JS guards.
    from ._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(
        body,
        f"Value Tracker — {name}",
        subtitle=(
            f"{_html.escape(deal_id)} | "
            f"Planned {_fm(total_planned)} | Realized {_fm(total_realized)} "
            f"({realization:.0%}) | {quarters} quarters"
        ),
    )
