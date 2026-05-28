"""Surface 15 · Playbook — 100-day operational playbook.

Initiatives are auto-suggested from real services already wired into the
deal-lens: the 7 EBITDA bridge levers (each becomes a row) and the top
denial drivers (each becomes a row). Priority bands (P0/P1/P2) come from
the spec's dollar-impact thresholds. Timeline is the bridge engine's own
ramp_months per lever (denial recovery defaults to 12 months).

Owner is INTENTIONALLY blank ("TBD") on every row — HCRIS doesn't carry
a management roster, and the spec is explicit: "Owner unassigned → gray
pill 'TBD' in the owner column." The deal team supplies real owners
when management materials are shared; until then, no fabricated names.

Components shipped (all 3 in the spec):
1. Hero strip — initiatives count, total EBITDA impact, equity value at
                a default 10x exit multiple (LABELED), average ramp
2. Playbook table — initiative · category · priority · impact · timeline
                     · owner (with the source-tag chip system from Phase 10
                     marking which engine sourced each row)
3. What this means panel — IC talking point + cross-link buttons to the
                            engines that produced the rows (Bridge / Denial
                            / Levers)
"""
from __future__ import annotations

import html as _html
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ._shell import _fmt_money, _fmt_pct, deal_shell


_DEFAULT_EXIT_MULTIPLE = 10.0       # industry-standard; labeled in UI
_DEFAULT_DENIAL_RAMP = 12           # months — denial-recovery initiatives


@dataclass
class Initiative:
    name: str
    category: str
    priority: str          # "P0" / "P1" / "P2"
    impact: float          # annualized $ EBITDA impact
    ramp_months: int
    source: str            # "bridge" | "denial" — the source-tag chip key


def _safe_float(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f else f


def _medicare_share(h: Dict[str, Any]) -> Optional[float]:
    for k in ("percent_days_medicare", "medicare_day_pct", "medicare_days_pct"):
        v = _safe_float(h.get(k))
        if v is not None:
            return v if v <= 1.5 else v / 100.0
    return None


def _priority_band(impact: float) -> str:
    """Per the spec: P0 coral (largest), P1 amber, P2 neutral."""
    a = abs(impact)
    if a > 25e6:
        return "P0"
    if a >= 5e6:
        return "P1"
    return "P2"


_PRIORITY_STYLE = {
    "P0": ("#b5321e", "#fbe7e2"),
    "P1": ("#b8842e", "#fbedd9"),
    "P2": ("#5a6f7a", "#ece6d7"),
}


_SOURCE_STYLE = {
    # source-tag chip: bridge (green) / denial (gold)
    "bridge":   ("#1f7a5a", "#d6e8df", "Bridge lever"),
    "denial":   ("#a08227", "#ecdfb4", "Denial driver"),
}


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


def _empty(reason: str) -> str:
    return (
        '<section style="background:#faf6ec;border:1px solid #c9c1ac;'
        'padding:24px 26px;">'
        '<span style="font-family:var(--sc-mono);font-size:10px;'
        'letter-spacing:.18em;text-transform:uppercase;color:#b8842e;">'
        'Playbook cannot run</span>'
        '<h3 style="font-family:var(--sc-serif);font-weight:400;font-size:22px;'
        'margin:6px 0 12px;color:#15202b;">HCRIS inputs missing</h3>'
        f'<p style="font-family:var(--sc-serif);font-size:14.5px;line-height:1.55;'
        f'color:#2a3a4a;margin:0;">{_html.escape(reason)} The playbook needs '
        'either the Bridge engine or the Denial engine to seed initiatives.</p>'
        '</section>'
    )


def _derive_initiatives(
    hospital: Dict[str, Any], npr: float, opex: float,
) -> List[Initiative]:
    """Auto-derive initiatives from the Bridge + Denial engines.

    Each lever the bridge surfaces becomes one initiative. Top denial
    drivers (recoverable revenue × contribution-margin proxy) become
    additional rows. Nothing is fabricated — when an engine returns no
    output, no initiative is added.
    """
    try:
        from ..ebitda_bridge_page import _compute_bridge
        from ...finance.denial_drivers import analyze_denial_drivers
    except ImportError:                                # pragma: no cover
        from rcm_mc.ui.ebitda_bridge_page import _compute_bridge
        from rcm_mc.finance.denial_drivers import analyze_denial_drivers

    current_ebitda = float(npr) - float(opex)
    medicare = _medicare_share(hospital) or 0.40
    initiatives: List[Initiative] = []

    # Bridge levers → one initiative each
    try:
        bridge = _compute_bridge(
            net_revenue=float(npr), current_ebitda=float(current_ebitda),
            medicare_pct=float(medicare),
        )
        for lev in bridge.get("levers") or []:
            impact = float(lev.get("ebitda_impact") or 0.0)
            if impact == 0.0:
                continue
            initiatives.append(Initiative(
                name=str(lev.get("name") or lev.get("metric") or "(unnamed)"),
                category=str(lev.get("category") or "rcm"),
                priority=_priority_band(impact),
                impact=impact,
                ramp_months=int(lev.get("ramp_months") or 12),
                source="bridge",
            ))
    except Exception:                                  # noqa: BLE001
        pass

    # Denial drivers → additional initiatives
    try:
        da = analyze_denial_drivers({
            "deal_id": str(hospital.get("ccn", "")),
            "net_revenue": float(npr),
            "claims_volume": max(1000, int(float(npr) / 15000.0)),
            "state": str(hospital.get("state", "") or ""),
        })
        for d in (getattr(da, "drivers", []) or []):
            impact = float(getattr(d, "estimated_annual_impact", 0.0) or 0.0)
            if impact == 0.0:
                continue
            initiatives.append(Initiative(
                name=str(getattr(d, "driver", "(unnamed driver)")),
                category=str(getattr(d, "category", "denial recovery")),
                priority=_priority_band(impact),
                impact=impact,
                ramp_months=_DEFAULT_DENIAL_RAMP,
                source="denial",
            ))
    except Exception:                                  # noqa: BLE001
        pass

    # Sort largest impact first — matches the spec's priority ordering
    initiatives.sort(key=lambda i: -abs(i.impact))
    return initiatives


def _hero(initiatives: List[Initiative]) -> str:
    n = len(initiatives)
    total_impact = sum(i.impact for i in initiatives)
    avg_ramp = (sum(i.ramp_months for i in initiatives) / n) if n else 0.0
    equity_at_exit = total_impact * _DEFAULT_EXIT_MULTIPLE
    p0 = sum(1 for i in initiatives if i.priority == "P0")
    p1 = sum(1 for i in initiatives if i.priority == "P1")
    rows = [
        ("Initiatives",         f"{n}"),
        ("P0 / P1 priority",    f"{p0} / {p1}"),
        ("Total EBITDA impact", _fmt_money(total_impact)),
        ("Equity at exit (10x)", _fmt_money(equity_at_exit)),
        ("Avg ramp",            f"{avg_ramp:.0f} mo"),
        ("Owners assigned",     "0 of " + str(n)),
    ]
    cells = "".join(
        '<div style="border:1px solid #c9c1ac;background:#faf6ec;padding:12px 14px;">'
        f'<dt style="font-family:var(--sc-mono);font-size:9.5px;'
        f'letter-spacing:.14em;text-transform:uppercase;color:#6a7480;'
        f'margin:0 0 4px;">{_html.escape(label)}</dt>'
        '<dd style="font-family:var(--sc-serif);font-size:20px;margin:0;'
        f'color:#15202b;font-variant-numeric:tabular-nums;">{_html.escape(value)}</dd></div>'
        for label, value in rows
    )
    return (
        '<dl style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));'
        f'gap:12px;margin:0;">{cells}</dl>'
        '<p style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.1em;'
        'color:#6a7480;margin:10px 0 0;">'
        'EQUITY-AT-EXIT MULTIPLE IS THE DEFAULT 10× — OVERRIDE WITH THE DEAL\'S '
        'ACTUAL ASSUMED EXIT MULTIPLE WHEN THE LBO IS LOCKED. OWNERS ARE BLANK '
        'BY DESIGN: HCRIS DOESN\'T CARRY A MANAGEMENT ROSTER.</p>'
    )


def _playbook_table(initiatives: List[Initiative]) -> str:
    if not initiatives:
        return ('<p style="font-family:var(--sc-serif);font-style:italic;'
                'color:#6a7480;font-size:13px;margin:0;">'
                'No initiatives derived &mdash; both the Bridge engine and the '
                'Denial engine returned empty for this hospital.</p>')
    rows = []
    for i in initiatives:
        p_color, p_bg = _PRIORITY_STYLE[i.priority]
        s_color, s_bg, s_label = _SOURCE_STYLE[i.source]
        rows.append(
            '<tr>'
            # Initiative name + source chip
            f'<td><div style="font-family:var(--sc-serif);font-size:14px;'
            f'color:#15202b;">{_html.escape(i.name)}</div>'
            f'<span style="font-family:var(--sc-mono);font-size:9px;letter-spacing:.12em;'
            f'text-transform:uppercase;color:{s_color};background:{s_bg};'
            f'border:1px solid {s_color};padding:1px 6px;margin-top:4px;display:inline-block;">'
            f'{_html.escape(s_label)}</span></td>'
            # Category
            f'<td style="font-family:var(--sc-mono);font-size:10.5px;letter-spacing:.08em;'
            f'text-transform:uppercase;color:#6a7480;">'
            f'{_html.escape(i.category)}</td>'
            # Priority badge
            f'<td><span style="font-family:var(--sc-mono);font-size:9.5px;'
            f'letter-spacing:.12em;text-transform:uppercase;color:{p_color};'
            f'background:{p_bg};border:1px solid {p_color};padding:2px 8px;">'
            f'{i.priority}</span></td>'
            # Impact
            f'<td class="num">{_fmt_money(i.impact)}</td>'
            # Timeline
            f'<td class="num" style="font-family:var(--sc-mono);font-size:11px;color:#2a3a4a;">'
            f'{i.ramp_months} mo</td>'
            # Owner — gray TBD pill per spec
            f'<td><span style="font-family:var(--sc-mono);font-size:9.5px;'
            f'letter-spacing:.12em;text-transform:uppercase;color:#6a7480;'
            f'background:#ece6d7;border:1px solid #c9c1ac;padding:2px 8px;">TBD</span></td>'
            '</tr>'
        )
    # Footer with sum row (impact)
    total = sum(i.impact for i in initiatives)
    foot = (
        '<tfoot><tr style="background:#faf6ec;font-family:var(--sc-mono);'
        'font-size:10.5px;letter-spacing:.12em;text-transform:uppercase;color:#2a3a4a;">'
        '<td colspan="3" style="padding:8px 4px;">Total EBITDA impact (sum, not weighted)</td>'
        f'<td class="num" style="padding:8px 4px;">{_fmt_money(total)}</td>'
        '<td colspan="2"></td></tr></tfoot>'
    )
    return (
        '<table class="cad-table" style="width:100%;font-family:var(--sc-serif);">'
        '<thead><tr>'
        '<th>Initiative</th><th>Category</th><th>Priority</th>'
        '<th class="num">Impact</th><th class="num">Timeline</th><th>Owner</th>'
        '</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody>{foot}</table>'
        '<p style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.1em;'
        'color:#6a7480;margin:10px 0 0;">'
        'INITIATIVES AUTO-DERIVED FROM THE BRIDGE + DENIAL ENGINES &middot; '
        'PRIORITY BANDS: P0 &gt;$25M · P1 $5–25M · P2 &lt;$5M (THE SPEC\'S '
        'SEVERITY MAP).</p>'
    )


def _what_this_means(initiatives: List[Initiative], ccn: str) -> str:
    if not initiatives:
        return (
            '<p style="font-family:var(--sc-serif);font-style:italic;'
            'color:#6a7480;font-size:13px;margin:0;">'
            'No initiatives derived for this hospital. Cross-check the Bridge '
            'and Denial surfaces to see why.</p>'
        )
    n = len(initiatives)
    p0 = [i for i in initiatives if i.priority == "P0"]
    total = sum(i.impact for i in initiatives)
    top = initiatives[0]
    quote_text = (
        f"This deal has {n} initiatives sized at {_fmt_money(total)} of "
        f"annualized EBITDA impact. The largest is {top.name} "
        f"({_fmt_money(top.impact)}, {top.ramp_months}-month ramp). "
        + (f"There are {len(p0)} P0 priority items — start there." if p0
           else "All initiatives sit at P1/P2 — no single fire to fight, but "
                "the cumulative impact carries the thesis.")
    )
    ccn_safe = _html.escape(ccn, quote=True)
    return (
        '<blockquote style="border-left:2px solid #1f6a4c;padding:4px 0 4px 18px;'
        'margin:0 0 14px;font-family:var(--sc-serif);font-style:italic;font-size:18px;'
        'line-height:1.55;color:#154e36;">'
        f'<em style="color:#154e36;">"</em>{_html.escape(quote_text)}<em>"</em>'
        '</blockquote>'
        '<p style="font-family:var(--sc-serif);font-size:13.5px;line-height:1.6;'
        'color:#2a3a4a;margin:0;">'
        'The engines that sourced these rows: '
        f'<a href="/deals/{ccn_safe}/bridge" style="color:#1f7a5a;">EBITDA Bridge</a> '
        f'(lever decomposition) &middot; '
        f'<a href="/deals/{ccn_safe}/levers" style="color:#1f7a5a;">Levers</a> '
        f'(P-weighted view of the same data) &middot; '
        f'<a href="/deals/{ccn_safe}/denial" style="color:#1f7a5a;">Denial</a> '
        f'(driver decomposition with sized impact).</p>'
        '<p style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.1em;'
        'color:#6a7480;margin:10px 0 0;">'
        'TALKING POINT DERIVED FROM REAL INITIATIVE COUNTS — NEVER A PROSE THESIS.</p>'
    )


def render_deal_playbook(ccn: str, hospital: Dict[str, Any]) -> str:
    """Render Surface 15 (Playbook) for ``ccn``."""
    npr = _safe_float(hospital.get("net_patient_revenue"))
    opex = _safe_float(hospital.get("operating_expenses"))
    if not npr or npr <= 1e5 or opex is None or opex <= 0:
        return deal_shell(
            ccn, hospital, active_slug="playbook",
            body_html=_empty(
                f"CCN {ccn} is missing the HCRIS revenue or operating-expenses "
                "lines the source engines need."),
            page_title=f"Playbook · {hospital.get('name') or f'CCN {ccn}'}",
        )
    initiatives = _derive_initiatives(hospital, float(npr), float(opex))
    panels = [
        _panel("01 · HERO",
               "100-day plan at a glance",
               _hero(initiatives)),
        _panel("02 · VALUE-CREATION PLAYBOOK",
               "Initiatives auto-derived from Bridge + Denial",
               _playbook_table(initiatives)),
        _panel("03 · WHAT THIS MEANS",
               "IC talking point + the engines that sourced this",
               _what_this_means(initiatives, ccn)),
        _panel("04 · WHAT'S NEXT", "Coming in a later phase",
               '<p style="font-family:var(--sc-serif);font-size:14.5px;'
               'line-height:1.55;color:#2a3a4a;margin:0;">'
               'The spec\'s "Drag rows to reorder priority," "Click priority '
               'badge to cycle P0→P1→P2," and "Click owner → assignment '
               'popover with management roster" interactions all need a '
               'persistence layer + a real management roster — neither lives '
               'in HCRIS. They land when the deal-team config + LinkedIn '
               'integration ship.</p>'),
    ]
    body = "".join(panels)
    return deal_shell(
        ccn, hospital, active_slug="playbook", body_html=body,
        page_title=f"Playbook · {hospital.get('name') or f'CCN {ccn}'}",
    )
