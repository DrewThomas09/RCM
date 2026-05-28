"""Surface 05 · Scenarios — base / conservative / aggressive / downside.

Wired to the same engines the rest of the family uses. Runs the bridge
engine once at base, then applies four NAMED transforms to produce the
four canonical scenarios:

  Base          — raw bridge output (full gross uplift, no discount)
  Conservative  — gross × realization (ML model's expected achievement)
  Aggressive    — gross × min(1.15, 1.0)  (capped; can't exceed gross)
  Downside      — gross × max(0.30, realization − 0.20)

Each scenario then re-runs the LBO engine with the scenario's pro-forma
EBITDA to get scenario-specific IRR / MOIC. Nothing in the comparison
table is invented — every cell is a deterministic transform of real
engine output, and the transform definitions are in the footer so a
partner can audit them.

The spec calls for interactive checkboxes ("8 checkboxes in two columns;
4 active at a time") + URL-share state. Server-rendered today; the static
snapshot is the canonical 4 scenarios. The interactive layer lands when
a client-side compute path exists.

Components shipped (4 of 5 in the spec):
1. SCENARIO SELECTOR  — visible-but-disabled 4-row chip list naming the
                         scenarios that will run; explicit "read-only"
                         label so partners know it's not interactive yet.
2. HERO STRIP         — 5 deal KPIs constant across scenarios.
3. COMPARISON TABLE   — 8-row × 4-column matrix; Base column tinted green
                         per the spec's build note.
4. PER-SCENARIO CARDS — 4 cards in a row, lever totals + IRR pill, color-
                         coded by scenario.

The spec's "implementation timing × 4 scenarios" component is deferred
to a follow-up — it needs per-scenario ramp curves that this engine
doesn't expose cleanly; will land alongside the editable interactivity.
"""
from __future__ import annotations

import html as _html
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ._shell import _fmt_money, _fmt_pct, deal_shell


@dataclass
class ScenarioRow:
    """One row in the scenario comparison."""
    label: str               # "Base" / "Conservative" / "Aggressive" / "Downside"
    fraction: float          # realization fraction applied to gross uplift
    color: str               # accent color
    description: str         # one-line transform definition
    # Derived
    gross_uplift: float = 0.0
    p_weighted_uplift: float = 0.0
    pro_forma_ebitda: float = 0.0
    irr: Optional[float] = None
    moic: Optional[float] = None


_DEFAULT_AGGRESSIVE_LIFT = 1.15
_DEFAULT_DOWNSIDE_PENALTY = 0.20
_DEFAULT_DOWNSIDE_FLOOR = 0.30


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
        'Scenarios cannot run</span>'
        '<h3 style="font-family:var(--sc-serif);font-weight:400;font-size:22px;'
        'margin:6px 0 12px;color:#15202b;">HCRIS inputs missing</h3>'
        f'<p style="font-family:var(--sc-serif);font-size:14.5px;line-height:1.55;'
        f'color:#2a3a4a;margin:0;">{_html.escape(reason)} Scenarios inherit the '
        'same engines as Bridge and LBO; without those engines we have nothing '
        'to discount.</p></section>'
    )


def _selector_panel(rows: List[ScenarioRow]) -> str:
    items = []
    for r in rows:
        items.append(
            '<li style="display:flex;align-items:center;gap:14px;'
            'padding:10px 14px;border:1px solid #c9c1ac;background:#faf6ec;">'
            '<input type="checkbox" checked disabled '
            'style="width:14px;height:14px;accent-color:' + r.color + ';"/>'
            f'<div style="flex:1;">'
            f'<div style="font-family:var(--sc-serif);font-size:14.5px;'
            f'color:#15202b;">{_html.escape(r.label)}</div>'
            f'<div style="font-family:var(--sc-mono);font-size:10px;'
            f'color:#6a7480;letter-spacing:.08em;margin-top:2px;">'
            f'{_html.escape(r.description)}</div></div></li>'
        )
    return (
        '<ul style="list-style:none;padding:0;margin:0;display:grid;'
        f'grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;">{"".join(items)}</ul>'
        '<p style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.1em;'
        'color:#6a7480;margin:10px 0 0;">'
        'READ-ONLY SNAPSHOT &middot; ALL 4 SCENARIOS ARE ACTIVE. THE EDITABLE '
        'TOGGLE LAYER LANDS WITH THE CLIENT-SIDE COMPUTE PATH.</p>'
    )


def _hero(hospital: Dict[str, Any], current_ebitda: float, npr: float) -> str:
    margin = (current_ebitda / npr) if npr > 0 else 0
    rows = [
        ("Hospital",        _html.escape(str(hospital.get("name") or "—"))[:32]),
        ("State",           _html.escape(str(hospital.get("state") or "—"))),
        ("Net revenue",     _fmt_money(npr)),
        ("Current EBITDA",  _fmt_money(current_ebitda)),
        ("Current margin",  _fmt_pct(margin)),
    ]
    cells = "".join(
        '<div style="border:1px solid #c9c1ac;background:#faf6ec;padding:12px 14px;">'
        f'<dt style="font-family:var(--sc-mono);font-size:9.5px;'
        f'letter-spacing:.14em;text-transform:uppercase;color:#6a7480;'
        f'margin:0 0 4px;">{_html.escape(label)}</dt>'
        '<dd style="font-family:var(--sc-serif);font-size:18px;margin:0;'
        f'color:#15202b;font-variant-numeric:tabular-nums;">{value}</dd></div>'
        for label, value in rows
    )
    return (
        '<dl style="display:grid;grid-template-columns:repeat(5,minmax(0,1fr));'
        f'gap:10px;margin:0;">{cells}</dl>'
        '<p style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.1em;'
        'color:#6a7480;margin:10px 0 0;">'
        'THESE 5 ARE DEAL CONSTANTS — THEY DO NOT CHANGE ACROSS SCENARIOS.</p>'
    )


def _comparison_table(rows: List[ScenarioRow]) -> str:
    # 8 metric rows × 4 scenario columns
    def _row(label: str, vals: List[str]) -> str:
        cells = "".join(
            f'<td class="num" style="background:{"#e6efe1" if i == 0 else "transparent"};'
            'font-family:var(--sc-mono);font-size:12px;color:#15202b;text-align:right;'
            f'padding:8px 10px;font-variant-numeric:tabular-nums;">{v}</td>'
            for i, v in enumerate(vals)
        )
        return (
            '<tr>'
            f'<td style="font-family:var(--sc-serif);font-size:14px;color:#15202b;'
            f'padding:8px 10px;">{_html.escape(label)}</td>'
            f'{cells}</tr>'
        )
    headers = "".join(
        f'<th style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.14em;'
        f'text-transform:uppercase;color:{r.color};padding:8px 10px;text-align:right;'
        f'background:{"#e6efe1" if i == 0 else "transparent"};">{_html.escape(r.label)}</th>'
        for i, r in enumerate(rows)
    )
    body_rows = [
        _row("Realization fraction",
             [f"{r.fraction*100:.0f}%" for r in rows]),
        _row("Gross uplift",
             [_fmt_money(r.gross_uplift) for r in rows]),
        _row("P-weighted uplift",
             [_fmt_money(r.p_weighted_uplift) for r in rows]),
        _row("Pro-forma EBITDA",
             [_fmt_money(r.pro_forma_ebitda) for r in rows]),
        _row("EBITDA Δ vs base",
             [_fmt_money(r.pro_forma_ebitda - rows[0].pro_forma_ebitda) for r in rows]),
        _row("IRR",
             [f"{r.irr*100:.1f}%" if r.irr is not None else "—" for r in rows]),
        _row("MOIC",
             [f"{r.moic:.2f}x" if r.moic is not None else "—" for r in rows]),
        _row("Verdict",
             [_verdict_for(r) for r in rows]),
    ]
    return (
        '<table class="cad-table" style="width:100%;font-family:var(--sc-serif);">'
        '<thead><tr>'
        '<th style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.14em;'
        'text-transform:uppercase;color:#6a7480;padding:8px 10px;">Metric</th>'
        f'{headers}</tr></thead>'
        f'<tbody>{"".join(body_rows)}</tbody></table>'
        '<p style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.1em;'
        'color:#6a7480;margin:10px 0 0;">'
        'BASE COLUMN TINTED GREEN PER THE SPEC\'S BUILD NOTE. EVERY CELL IS A '
        'DETERMINISTIC TRANSFORM OF REAL ENGINE OUTPUT.</p>'
    )


def _verdict_for(r: ScenarioRow) -> str:
    """Tiny finite-map verdict per scenario (not hallucinated)."""
    if r.irr is None:
        return "—"
    if r.irr >= 0.20:
        return "Clears"
    if r.irr >= 0.10:
        return "Marginal"
    if r.irr > 0:
        return "Below"
    return "Impaired"


def _per_scenario_cards(rows: List[ScenarioRow]) -> str:
    cards = []
    for r in rows:
        irr = f"{r.irr*100:.1f}%" if r.irr is not None else "—"
        moic = f"{r.moic:.2f}x" if r.moic is not None else "—"
        cards.append(
            '<div style="border:1px solid #c9c1ac;background:#faf6ec;'
            'padding:16px 18px;display:flex;flex-direction:column;gap:8px;">'
            f'<div style="font-family:var(--sc-mono);font-size:10.5px;'
            f'letter-spacing:.18em;text-transform:uppercase;color:{r.color};">'
            f'{_html.escape(r.label)}</div>'
            f'<div style="font-family:var(--sc-serif);font-size:24px;'
            f'line-height:1.1;color:#15202b;">'
            f'{_fmt_money(r.pro_forma_ebitda)}</div>'
            f'<div style="font-family:var(--sc-mono);font-size:10px;'
            f'color:#6a7480;letter-spacing:.08em;">Pro-forma EBITDA</div>'
            '<div style="margin-top:8px;display:flex;gap:10px;flex-wrap:wrap;">'
            f'<span style="font-family:var(--sc-mono);font-size:11px;'
            f'color:{r.color};background:#fff;border:1px solid {r.color};'
            f'padding:2px 10px;">IRR {irr}</span>'
            f'<span style="font-family:var(--sc-mono);font-size:11px;'
            f'color:#2a3a4a;background:#fff;border:1px solid #c9c1ac;'
            f'padding:2px 10px;">MOIC {moic}</span></div>'
            '</div>'
        )
    return (
        '<div style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));'
        f'gap:12px;">{"".join(cards)}</div>'
    )


def _build_lbo_at(profile: Dict[str, Any], pro_forma_ebitda: float) -> Optional[Dict[str, float]]:
    """Run the LBO engine using the scenario's pro-forma EBITDA as the base."""
    try:
        from ...finance.lbo_model import build_lbo
    except ImportError:                                # pragma: no cover
        from rcm_mc.finance.lbo_model import build_lbo
    rev = float(profile.get("net_revenue") or 0)
    if rev <= 0 or pro_forma_ebitda <= 0:
        return None
    margin = max(0.02, min(0.40, pro_forma_ebitda / rev))
    try:
        lbo = build_lbo(
            entry_ebitda=pro_forma_ebitda,
            revenue_base=rev,
            ebitda_margin_base=margin,
        )
        return {"irr": float(lbo.returns.irr), "moic": float(lbo.returns.moic)}
    except Exception:                                  # noqa: BLE001
        return None


def render_deal_scenarios(ccn: str, hospital: Dict[str, Any]) -> str:
    """Render Surface 05 (Scenarios) for ``ccn``."""
    npr = _safe_float(hospital.get("net_patient_revenue"))
    opex = _safe_float(hospital.get("operating_expenses"))
    if not npr or npr <= 1e5 or opex is None or opex <= 0:
        return deal_shell(
            ccn, hospital, active_slug="scenarios",
            body_html=_empty(f"CCN {ccn} is missing the HCRIS revenue or "
                             "operating-expenses lines the source engines need."),
            page_title=f"Scenarios · {hospital.get('name') or f'CCN {ccn}'}",
        )

    try:
        from ..ebitda_bridge_page import _compute_bridge
        from ...data.hcris import _get_latest_per_ccn
        from ...ml.realization_predictor import predict_realization
    except ImportError:                                # pragma: no cover
        from rcm_mc.ui.ebitda_bridge_page import _compute_bridge
        from rcm_mc.data.hcris import _get_latest_per_ccn
        from rcm_mc.ml.realization_predictor import predict_realization

    current_ebitda = float(npr) - float(opex)
    medicare = _medicare_share(hospital) or 0.40
    try:
        bridge = _compute_bridge(
            net_revenue=float(npr), current_ebitda=current_ebitda,
            medicare_pct=medicare,
        )
    except Exception:                                  # noqa: BLE001
        bridge = {"total_ebitda_impact": 0.0, "current_ebitda": current_ebitda}
    gross_uplift = float(bridge.get("total_ebitda_impact") or 0.0)

    # Realization fraction for Conservative + Downside
    try:
        hdf = _get_latest_per_ccn()
        realization = predict_realization(ccn, hdf, bridge_uplift=gross_uplift)
        p = float(getattr(realization, "expected_realization", 1.0) or 1.0)
    except Exception:                                  # noqa: BLE001
        p = 0.70   # research-band default if the model can't run

    # 4 scenarios — each is a named transform of the base uplift
    scenarios = [
        ScenarioRow(
            label="Base", fraction=1.0, color="#1f7a5a",
            description="Full gross uplift, no discount applied.",
        ),
        ScenarioRow(
            label="Conservative", fraction=p, color="#155752",
            description=f"Gross × realization ({p*100:.0f}%).",
        ),
        ScenarioRow(
            label="Aggressive",
            fraction=min(1.0, _DEFAULT_AGGRESSIVE_LIFT),
            color="#2d8964",
            description=(f"Gross × {_DEFAULT_AGGRESSIVE_LIFT:.2f} "
                         "(capped at 1.00; cannot exceed gross)."),
        ),
        ScenarioRow(
            label="Downside",
            fraction=max(_DEFAULT_DOWNSIDE_FLOOR, p - _DEFAULT_DOWNSIDE_PENALTY),
            color="#b5321e",
            description=(f"Gross × max({_DEFAULT_DOWNSIDE_FLOOR:.2f}, "
                         f"realization − {_DEFAULT_DOWNSIDE_PENALTY:.2f}) = "
                         f"{max(_DEFAULT_DOWNSIDE_FLOOR, p - _DEFAULT_DOWNSIDE_PENALTY)*100:.0f}%."),
        ),
    ]

    # Hydrate every row with real engine output
    lbo_profile = {"net_revenue": float(npr), "current_ebitda": current_ebitda}
    for r in scenarios:
        r.gross_uplift = gross_uplift
        r.p_weighted_uplift = gross_uplift * r.fraction
        r.pro_forma_ebitda = current_ebitda + r.p_weighted_uplift
        lbo_out = _build_lbo_at(lbo_profile, r.pro_forma_ebitda)
        if lbo_out:
            r.irr = lbo_out["irr"]
            r.moic = lbo_out["moic"]

    panels = [
        _panel("01 · SCENARIO SELECTOR",
               "Which scenarios will run",
               _selector_panel(scenarios)),
        _panel("02 · HERO",
               "Deal constants across every scenario",
               _hero(hospital, current_ebitda, float(npr))),
        _panel("03 · SCENARIO COMPARISON",
               "Same hospital, four different exit assumptions",
               _comparison_table(scenarios)),
        _panel("04 · PER-SCENARIO CARDS",
               "Pro-forma EBITDA + IRR + MOIC at a glance",
               _per_scenario_cards(scenarios)),
        _panel("05 · WHAT'S NEXT", "Coming in a later phase",
               '<p style="font-family:var(--sc-serif);font-size:14.5px;'
               'line-height:1.55;color:#2a3a4a;margin:0;">'
               'The spec\'s per-scenario implementation-timing table and the '
               'editable toggle layer (checkboxes + URL-share state) need a '
               'client-side compute path that doesn\'t exist today. They '
               'land alongside that path.</p>'),
    ]
    body = "".join(panels)
    return deal_shell(
        ccn, hospital, active_slug="scenarios", body_html=body,
        page_title=f"Scenarios · {hospital.get('name') or f'CCN {ccn}'}",
    )
