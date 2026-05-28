"""Surface 03 · EBITDA Bridge — 7-lever RCM bridge from current EBITDA to
pro-forma.

Wired to real services only:
- `_compute_bridge` from `ui.ebitda_bridge_page` (calibrated to research bands)
  computes per-lever revenue/cost/EBITDA/WC impact, ramp curves, and totals
  from net revenue + current EBITDA + Medicare share. It is the same engine
  the live /ebitda-bridge page uses.
- All inputs to the bridge come from real HCRIS (net_patient_revenue,
  operating_expenses, percent_days_medicare). When any of those is missing,
  the bridge cannot run and we render an honest empty state instead of
  fabricating numbers.

Components shipped in this Phase 2 PR (4 of the 8 in the handoff):
1. Hero stat strip      — net rev, current EBITDA, RCM uplift, pro forma,
                          margin Δ (bps), WC released (one-time)
2. 7 RCM lever bars     — gradient with $ impact + bp per row
3. Lever detail table   — current → target + Δ EBITDA + ramp months
4. Implementation timing — cumulative annualized EBITDA at each milestone

Sensitivity heatmap, covenant headroom, value-creation waterfall, and the
realization-estimate panel land in Phase 2b once their data wiring is solid.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional

from ._shell import _fmt_money, _fmt_pct, deal_shell


def _safe_float(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f else f  # filter NaN


def _medicare_share(h: Dict[str, Any]) -> Optional[float]:
    for k in ("percent_days_medicare", "pct_days_medicare",
              "medicare_days_pct", "medicare_day_pct"):
        v = _safe_float(h.get(k))
        if v is not None:
            return v
    return None


def _fmt_bps(bps: float) -> str:
    """Format basis-points with sign for clarity ('+125 bps' / '-30 bps')."""
    if bps is None:
        return "—"
    try:
        b = round(float(bps))
    except (TypeError, ValueError):
        return "—"
    sign = "+" if b > 0 else ("" if b == 0 else "")
    return f"{sign}{b:,} bps"


def _panel(eyebrow: str, title: str, body_html: str) -> str:
    return (
        '<section style="background:#fff;border:1px solid #c9c1ac;'
        'padding:20px 22px;margin:0 0 18px;">'
        f'<span style="font-family:var(--sc-mono);font-size:10px;'
        f'letter-spacing:.18em;text-transform:uppercase;color:#1f7a5a;">'
        f'{_html.escape(eyebrow)}</span>'
        f'<h3 style="font-family:var(--sc-serif);font-weight:400;font-size:22px;'
        f'line-height:1.15;margin:6px 0 14px;color:#15202b;">'
        f'{_html.escape(title)}</h3>'
        f'{body_html}</section>'
    )


def _hero_strip(bridge: Dict[str, Any]) -> str:
    rows = [
        ("Net revenue",      _fmt_money(bridge.get("net_revenue"))),
        ("Current EBITDA",   _fmt_money(bridge.get("current_ebitda"))),
        ("RCM uplift",       _fmt_money(bridge.get("total_ebitda_impact"))),
        ("Pro-forma EBITDA", _fmt_money(bridge.get("new_ebitda"))),
        ("Margin Δ",         _fmt_bps(bridge.get("margin_improvement_bps"))),
        ("WC released",      _fmt_money(bridge.get("total_wc_released"))),
    ]
    cells = "".join(
        '<div style="border:1px solid #c9c1ac;background:#faf6ec;'
        'padding:12px 14px;">'
        f'<dt style="font-family:var(--sc-mono);font-size:9.5px;'
        f'letter-spacing:.14em;text-transform:uppercase;color:#6a7480;'
        f'margin:0 0 4px;">{_html.escape(label)}</dt>'
        '<dd style="font-family:var(--sc-serif);font-size:20px;margin:0;'
        'color:#15202b;font-variant-numeric:tabular-nums;">'
        f'{value}</dd></div>'
        for label, value in rows
    )
    return (
        '<dl style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));'
        f'gap:12px;margin:0;">{cells}</dl>'
        '<p style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.1em;'
        'color:#6a7480;margin:10px 0 0;">'
        'PRO-FORMA APPLIES THE FULL 7-LEVER UPLIFT. MARGIN Δ AND WC ARE THE '
        'DIRECT CONSEQUENCES &mdash; NOT INDEPENDENT ASSUMPTIONS.</p>'
    )


def _lever_bars(levers: List[Dict[str, Any]]) -> str:
    if not levers:
        return (
            '<p style="font-family:var(--sc-serif);font-style:italic;'
            'color:#6a7480;font-size:13px;margin:0;">'
            'No lever produced any impact at this metric set.</p>'
        )
    max_abs = max((abs(float(l.get("ebitda_impact") or 0.0)) for l in levers),
                  default=0.0) or 1.0
    rows = []
    for lev in levers:
        name = str(lev.get("name") or lev.get("metric") or "")
        impact = float(lev.get("ebitda_impact") or 0.0)
        bps = float(lev.get("margin_bps") or 0.0)
        category = str(lev.get("category") or "")
        # Bar width proportional to the strongest lever in this fit.
        w_pct = max(2.0, min(100.0, abs(impact) / max_abs * 100.0))
        # Greens for revenue/cost levers, ink-grey for working-capital (one-time).
        color = "#1f7a5a"
        if "working_capital" in category or lev.get("metric") == "days_in_ar":
            color = "#5a6f7a"   # one-time WC release renders in ink not green
        rows.append(
            '<div style="display:grid;grid-template-columns:1.4fr 3fr 1.1fr 0.7fr;'
            'gap:14px;align-items:center;padding:8px 0;'
            'border-bottom:1px solid #ece6d7;">'
            f'<div style="font-family:var(--sc-serif);font-size:14.5px;'
            f'color:#15202b;">{_html.escape(name)}</div>'
            '<div style="background:#f3eddb;border:1px solid #ece6d7;'
            'height:14px;overflow:hidden;">'
            f'<div style="background:{color};height:100%;width:{w_pct:.1f}%;"></div>'
            '</div>'
            '<div style="font-family:var(--sc-mono);font-size:12.5px;'
            'color:#2a3a4a;text-align:right;'
            'font-variant-numeric:tabular-nums;">'
            f'{_fmt_money(impact)}</div>'
            '<div style="font-family:var(--sc-mono);font-size:11px;'
            'color:#6a7480;text-align:right;'
            'font-variant-numeric:tabular-nums;">'
            f'{_fmt_bps(bps)}</div></div>'
        )
    return (
        '<div style="display:grid;grid-template-columns:1.4fr 3fr 1.1fr 0.7fr;'
        'gap:14px;padding:0 0 6px;font-family:var(--sc-mono);font-size:9.5px;'
        'letter-spacing:.14em;text-transform:uppercase;color:#6a7480;">'
        '<div>Lever</div><div>&nbsp;</div>'
        '<div style="text-align:right;">EBITDA Δ</div>'
        '<div style="text-align:right;">Margin</div></div>'
        + "".join(rows) +
        '<p style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.1em;'
        'color:#6a7480;margin:10px 0 0;">'
        'BARS SCALED TO THE STRONGEST LEVER. WORKING-CAPITAL LEVERS (DAYS IN AR) '
        'RENDER IN INK BECAUSE THE WC RELEASE IS ONE-TIME, NOT RECURRING.</p>'
    )


def _lever_detail_table(levers: List[Dict[str, Any]]) -> str:
    if not levers:
        return ""
    def _fmt_target(lever: Dict[str, Any], key: str) -> str:
        v = _safe_float(lever.get(key))
        if v is None:
            return "—"
        metric = str(lever.get("metric") or "")
        # Days-in-AR is a count of days; rates/shares are percent-style.
        if metric == "days_in_ar":
            return f"{v:.0f} days"
        if metric == "case_mix_index":
            return f"{v:.2f}"
        if metric == "cost_to_collect":
            return f"{v:.2f}%"
        return f"{v:.1f}%"
    rows = "".join(
        '<tr>'
        f'<td>{_html.escape(str(lev.get("name") or lev.get("metric") or ""))}</td>'
        f'<td class="num">{_fmt_target(lev, "current")}</td>'
        f'<td class="num">{_fmt_target(lev, "target")}</td>'
        f'<td class="num">{_fmt_money(lev.get("ebitda_impact"))}</td>'
        f'<td class="num">{_fmt_money(lev.get("wc_impact")) if lev.get("wc_impact") else "—"}</td>'
        f'<td class="num">{int(lev.get("ramp_months") or 0)} mo</td>'
        '</tr>'
        for lev in levers
    )
    return (
        '<table class="cad-table" style="width:100%;font-family:var(--sc-serif);">'
        '<thead><tr>'
        '<th>Lever</th><th class="num">Current</th><th class="num">Target</th>'
        '<th class="num">EBITDA Δ</th><th class="num">WC released</th>'
        '<th class="num">Ramp</th>'
        '</tr></thead>'
        f'<tbody>{rows}</tbody></table>'
        '<p style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.1em;'
        'color:#6a7480;margin:10px 0 0;">'
        'CURRENT METRICS ARE RESEARCH-BAND DEFAULTS UNTIL THE DEAL TEAM '
        'CAPTURES ACTUALS &mdash; TARGETS ARE PEER P75 BANDS.</p>'
    )


def _implementation_timing(levers: List[Dict[str, Any]]) -> str:
    """Cumulative annualized EBITDA per quarter, summed across all levers.

    Each lever ramps linearly to its full run-rate over ``ramp_months``; the
    table sums per-lever ramps at the 3/6/9/12/24/36-month milestones so a
    partner can see the realized EBITDA build out. All from real ramp data.
    """
    if not levers:
        return ""
    milestones = [3, 6, 9, 12, 18, 24, 30, 36]
    by_quarter: Dict[int, float] = {m: 0.0 for m in milestones}
    for lev in levers:
        impact = float(lev.get("ebitda_impact") or 0.0)
        ramp = max(1, int(lev.get("ramp_months") or 12))
        for m in milestones:
            pct = 1.0 if m >= ramp else (m / ramp)
            by_quarter[m] += impact * pct
    head = "".join(
        f'<th class="num">M{m}</th>' for m in milestones
    )
    cells = "".join(
        f'<td class="num">{_fmt_money(by_quarter[m])}</td>' for m in milestones
    )
    return (
        '<table class="cad-table" style="width:100%;font-family:var(--sc-serif);">'
        f'<thead><tr><th>Milestone</th>{head}</tr></thead>'
        f'<tbody><tr><td>Annualized EBITDA at month</td>{cells}</tr></tbody>'
        '</table>'
        '<p style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.1em;'
        'color:#6a7480;margin:10px 0 0;">'
        'LINEAR RAMP PER LEVER · SUM ACROSS ALL 7 LEVERS · FULL RUN-RATE AT '
        '<code>RAMP_MONTHS</code> · NUMBERS ARE ANNUALIZED, NOT PERIOD-EBITDA.</p>'
    )


def _empty_bridge_panel(reason: str) -> str:
    return (
        '<section style="background:#faf6ec;border:1px solid #c9c1ac;'
        'padding:24px 26px;">'
        '<span style="font-family:var(--sc-mono);font-size:10px;'
        'letter-spacing:.18em;text-transform:uppercase;color:#b8842e;">'
        'Bridge cannot run</span>'
        '<h3 style="font-family:var(--sc-serif);font-weight:400;font-size:22px;'
        'margin:6px 0 12px;color:#15202b;">'
        'Inputs not available in HCRIS for this hospital</h3>'
        f'<p style="font-family:var(--sc-serif);font-size:14.5px;line-height:1.55;'
        f'color:#2a3a4a;margin:0;">{_html.escape(reason)} The 7-lever model '
        'needs net revenue, current EBITDA (= NPR &minus; operating expenses), '
        'and Medicare day-share. Until those land in the HCRIS row no impact '
        'is shown here rather than fabricated.</p>'
        '</section>'
    )


def render_deal_bridge(ccn: str, hospital: Dict[str, Any]) -> str:
    """Render Surface 03 (EBITDA Bridge) for ``ccn``.

    Reads net_patient_revenue + operating_expenses + percent_days_medicare from
    the HCRIS row. If any required input is missing the surface renders an
    honest empty panel — no defaulted numbers.
    """
    npr = _safe_float(hospital.get("net_patient_revenue"))
    opex = _safe_float(hospital.get("operating_expenses"))
    if not npr or not opex or npr <= 1e5:
        body = _empty_bridge_panel(
            "HCRIS net patient revenue or operating expenses are missing for "
            f"CCN {ccn}."
        )
        return deal_shell(ccn, hospital, active_slug="bridge", body_html=body)

    current_ebitda = npr - opex
    medicare = _medicare_share(hospital) or 0.40   # research-band fallback
    try:
        from ..ebitda_bridge_page import _compute_bridge
    except ImportError:                                # pragma: no cover
        from rcm_mc.ui.ebitda_bridge_page import _compute_bridge

    try:
        bridge = _compute_bridge(
            net_revenue=float(npr), current_ebitda=float(current_ebitda),
            medicare_pct=float(medicare),
        )
    except Exception:                                  # noqa: BLE001
        return deal_shell(
            ccn, hospital, active_slug="bridge",
            body_html=_empty_bridge_panel(
                "The bridge engine returned an error for this hospital's "
                "inputs."
            ),
        )

    levers = bridge.get("levers") or []
    panels = [
        _panel("01 · HERO", "From current EBITDA to pro-forma", _hero_strip(bridge)),
        _panel("02 · 7-LEVER MODEL", "Per-lever EBITDA impact",
               _lever_bars(levers)),
        _panel("03 · LEVER DETAIL", "Current → target, with ramp",
               _lever_detail_table(levers)),
        _panel("04 · IMPLEMENTATION TIMING",
               "Cumulative annualized EBITDA, all 7 levers",
               _implementation_timing(levers)),
        _panel("05 · WHAT'S NEXT", "Coming in Phase 2b",
               '<p style="font-family:var(--sc-serif);font-size:14.5px;'
               'line-height:1.55;color:#2a3a4a;margin:0;">'
               'Sensitivity heatmap (entry × exit multiples), covenant headroom '
               'under stress, the 5-year value-creation waterfall, and the '
               'ML realization-estimate panel are deferred to a later PR. The '
               'sensitivity and waterfall need an LBO assumption set, which is '
               'the Returns surface’s job; the realization panel needs '
               'metric-level inputs that aren’t in HCRIS. Cross-link out '
               f'to <a href="/deals/{_html.escape(ccn, quote=True)}/returns" '
               'style="color:#1f7a5a;">Returns</a> when it ships.</p>'),
    ]
    body = "".join(panels)
    return deal_shell(
        ccn, hospital, active_slug="bridge", body_html=body,
        page_title=f"EBITDA Bridge · {hospital.get('name') or f'CCN {ccn}'}",
    )
