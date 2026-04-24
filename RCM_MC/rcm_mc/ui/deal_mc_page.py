"""Deal Monte Carlo UI at /diligence/deal-mc.

One-page view that runs the engine against caller-supplied inputs
(with CCD + risk-module integration when a fixture is picked) and
renders:
    - Hero stat row (P50 MOIC, IRR, P(sub-1x), P(over-3x))
    - Fan charts: revenue + EBITDA across hold
    - MOIC histogram with P50 marker
    - Variance-attribution bar chart
    - Sensitivity tornado
    - Scenario inputs table (partner-auditable)

All charts are zero-dep SVG. Runs <1s on a laptop for 3000 trials.
"""
from __future__ import annotations

import html
import json
from typing import Any, Dict, List, Optional

from ..diligence.deal_mc import (
    DealMCResult, DealScenario, run_deal_monte_carlo,
)
from ..diligence.deal_mc.charts import (
    attribution_chart, fan_chart, moic_histogram_chart,
    sensitivity_tornado,
)
from ._chartis_kit import P, chartis_shell
from .power_ui import provenance


def _landing() -> str:
    # Pre-filled Steward-replay defaults.
    body = (
        f'<div style="padding:24px 0 12px 0;">'
        f'<div style="font-size:11px;color:{P["text_faint"]};letter-spacing:1.5px;'
        f'text-transform:uppercase;margin-bottom:6px;font-weight:600;">'
        f'Deal Monte Carlo</div>'
        f'<div style="font-size:22px;color:{P["text"]};font-weight:600;'
        f'margin-bottom:4px;">5-Year Forward EBITDA + MOIC + IRR</div>'
        f'<div style="font-size:12px;color:{P["text_dim"]};max-width:760px;'
        f'line-height:1.55;">Runs 3,000 Monte Carlo scenarios over every '
        f'lever — organic growth, denial improvement, regulatory headwind '
        f'realization, lease escalator, physician attrition, cyber '
        f'incidents, V28 compression, exit multiple. Produces MOIC / '
        f'IRR distributions, driver attribution, and sensitivity tornado. '
        f'&lt;1 second runtime.</div>'
        f'</div>'
    )
    body += (
        f'<form method="GET" action="/diligence/deal-mc" '
        f'style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;'
        f'max-width:760px;margin-top:20px;background:{P["panel"]};'
        f'border:1px solid {P["border"]};border-radius:4px;padding:20px;">'
    )
    for name, label, default in [
        ("ev_usd", "Enterprise Value ($)", "350000000"),
        ("equity_usd", "Equity Check ($)", "150000000"),
        ("debt_usd", "Debt ($)", "200000000"),
        ("revenue_usd", "Revenue Y0 ($)", "250000000"),
        ("ebitda_usd", "EBITDA Y0 ($)", "35000000"),
        ("entry_multiple", "Entry EV/EBITDA", "10.0"),
        ("medicare_share", "Medicare share (0-1)", "0.25"),
        ("growth_mean", "Growth mean (0-1)", "0.04"),
        ("growth_sd", "Growth σ", "0.025"),
        ("denial_impr_mean", "Denial improvement pp", "0.015"),
        ("reg_headwind_usd", "Reg headwind $", "15000000"),
        ("exit_mult_mean", "Exit multiple mean", "9.0"),
        ("exit_mult_sd", "Exit multiple σ", "1.5"),
        ("cyber_prob", "Cyber prob/yr (0-1)", "0.05"),
        ("v28_mean", "V28 compression (0-1)", "0.0312"),
        ("hold_years", "Hold years", "5"),
        ("n_runs", "# of runs", "3000"),
        ("deal_name", "Deal name", "Project Aurora"),
    ]:
        body += (
            f'<div><label style="font-size:9px;color:{P["text_faint"]};'
            f'letter-spacing:1.5px;text-transform:uppercase;'
            f'font-weight:600;display:block;margin-bottom:4px;">'
            f'{html.escape(label)}</label>'
            f'<input name="{name}" value="{html.escape(default)}" '
            f'style="width:100%;padding:6px 8px;background:{P["panel_alt"]};'
            f'color:{P["text"]};border:1px solid {P["border"]};'
            f'font-family:inherit;"></div>'
        )
    body += (
        f'<button type="submit" style="grid-column:span 3;justify-self:start;'
        f'margin-top:6px;padding:8px 20px;background:{P["accent"]};'
        f'color:{P["panel"]};border:0;font-size:10px;letter-spacing:1.5px;'
        f'text-transform:uppercase;font-weight:700;cursor:pointer;">'
        f'Run Monte Carlo</button></form>'
    )
    return chartis_shell(
        body, "RCM Diligence — Deal Monte Carlo",
        subtitle="5-year forward EBITDA + MOIC + IRR",
    )


def _hero_stats(result: DealMCResult, scenario_name: str) -> str:
    def band_color(moic: float) -> str:
        if moic >= 2.5:
            return P["positive"]
        if moic >= 1.5:
            return P["warning"]
        return P["negative"]

    def prob_color(p: float, higher_is_better: bool = False) -> str:
        if higher_is_better:
            return P["positive"] if p >= 0.3 else P["warning"]
        return P["negative"] if p >= 0.3 else P["warning"] if p >= 0.1 else P["positive"]

    return (
        f'<div style="padding:24px 0 16px 0;border-bottom:1px solid '
        f'{P["border"]};margin-bottom:24px;">'
        f'<div style="font-size:11px;color:{P["text_faint"]};letter-spacing:1.5px;'
        f'text-transform:uppercase;margin-bottom:6px;font-weight:600;">'
        f'Deal Monte Carlo</div>'
        f'<div style="font-size:22px;color:{P["text"]};font-weight:600;'
        f'margin-bottom:4px;">{html.escape(scenario_name)}</div>'
        f'<div style="font-size:11px;color:{P["text_faint"]};">'
        f'{result.n_runs:,} Monte Carlo trials · {result.hold_years}y hold</div>'
        f'<div style="display:grid;grid-template-columns:repeat(6,1fr);'
        f'gap:16px;margin-top:20px;">'
        f'<div><div style="font-size:9px;color:{P["text_faint"]};'
        f'letter-spacing:1px;text-transform:uppercase;">P25 MOIC</div>'
        f'<div style="font-size:26px;font-family:\'JetBrains Mono\',monospace;'
        f'font-weight:700;color:{band_color(result.moic_p25)};">'
        f'{result.moic_p25:.2f}x</div></div>'
        f'<div><div style="font-size:9px;color:{P["text_faint"]};'
        f'letter-spacing:1px;text-transform:uppercase;">P50 MOIC</div>'
        f'<div style="font-size:30px;font-family:\'JetBrains Mono\',monospace;'
        f'font-weight:700;color:{band_color(result.moic_p50)};">'
        f'{result.moic_p50:.2f}x</div></div>'
        f'<div><div style="font-size:9px;color:{P["text_faint"]};'
        f'letter-spacing:1px;text-transform:uppercase;">P75 MOIC</div>'
        f'<div style="font-size:26px;font-family:\'JetBrains Mono\',monospace;'
        f'font-weight:700;color:{band_color(result.moic_p75)};">'
        f'{result.moic_p75:.2f}x</div></div>'
        f'<div><div style="font-size:9px;color:{P["text_faint"]};'
        f'letter-spacing:1px;text-transform:uppercase;">P50 IRR</div>'
        f'<div style="font-size:26px;font-family:\'JetBrains Mono\',monospace;'
        f'font-weight:700;color:{P["text"]};">'
        f'{result.irr_p50*100:.1f}%</div></div>'
        f'<div><div style="font-size:9px;color:{P["text_faint"]};'
        f'letter-spacing:1px;text-transform:uppercase;">P(MOIC &lt; 1x)</div>'
        f'<div style="font-size:22px;font-family:\'JetBrains Mono\',monospace;'
        f'font-weight:700;color:{prob_color(result.prob_sub_1x)};">'
        f'{result.prob_sub_1x*100:.1f}%</div></div>'
        f'<div><div style="font-size:9px;color:{P["text_faint"]};'
        f'letter-spacing:1px;text-transform:uppercase;">P(MOIC &gt;= 3x)</div>'
        f'<div style="font-size:22px;font-family:\'JetBrains Mono\',monospace;'
        f'font-weight:700;color:{prob_color(result.prob_over_3x, higher_is_better=True)};">'
        f'{result.prob_over_3x*100:.1f}%</div></div>'
        f'</div></div>'
    )


def _chart_panel(title: str, svg: str, note: str = "") -> str:
    note_html = (
        f'<div style="font-size:11px;color:{P["text_faint"]};'
        f'line-height:1.5;margin-top:8px;max-width:640px;">'
        f'{html.escape(note)}</div>'
        if note else ""
    )
    return (
        f'<div style="background:{P["panel"]};border:1px solid '
        f'{P["border"]};border-radius:4px;padding:14px 20px;'
        f'margin-bottom:16px;">'
        f'<div style="font-size:9px;color:{P["text_faint"]};'
        f'letter-spacing:1.5px;text-transform:uppercase;font-weight:700;'
        f'margin-bottom:8px;">{html.escape(title)}</div>'
        f'{svg}'
        f'{note_html}'
        f'</div>'
    )


def _attribution_note(result: DealMCResult) -> str:
    if not result.attribution or not result.attribution.contributions:
        return ""
    top = result.attribution.contributions[0]
    return (
        f"Largest variance contributor: "
        f"{top.driver} ({top.share_of_variance*100:.1f}% of MOIC "
        f"variance). Partners should pressure-test this driver first — "
        f"small revisions to the assumption materially move the "
        f"distribution."
    )


def _sensitivity_note(result: DealMCResult) -> str:
    if not result.stress_results:
        return ""
    worst = result.stress_results[0]  # sorted ascending by moic_impact
    return (
        f"Worst-case one-shot sensitivity: {worst.shock_label} "
        f"moves MOIC by {worst.moic_impact:+.2f}x "
        f"(from {worst.base_moic:.2f}x to {worst.stressed_moic:.2f}x). "
        f"Single-driver stress — does not compound with other "
        f"adverse moves."
    )


def _scenario_inputs_table(scn: DealScenario) -> str:
    rows = [
        ("Enterprise Value", f"${scn.enterprise_value_usd:,.0f}"),
        ("Equity Check", f"${scn.equity_check_usd:,.0f}"),
        ("Debt", f"${scn.debt_usd:,.0f}"),
        ("Entry EV/EBITDA", f"{scn.entry_multiple:.2f}x"),
        ("Revenue Y0", f"${scn.revenue_year0_usd:,.0f}"),
        ("EBITDA Y0", f"${scn.ebitda_year0_usd:,.0f}"),
        ("Medicare share", f"{scn.medicare_share*100:.1f}%"),
        ("Organic growth (mean, σ)",
         f"{scn.organic_growth_mean*100:.2f}% / {scn.organic_growth_sd*100:.2f}%"),
        ("Denial improvement (mean, σ)",
         f"{scn.denial_improvement_pp_mean*100:.2f}pp / {scn.denial_improvement_pp_sd*100:.2f}pp"),
        ("Reg headwind ($ at risk)",
         f"${scn.reg_headwind_usd:,.0f}"),
        ("Reg realization Beta(α, β)",
         f"Beta({scn.reg_headwind_realization_alpha}, "
         f"{scn.reg_headwind_realization_beta}) — mean "
         f"{scn.reg_headwind_realization_alpha / (scn.reg_headwind_realization_alpha + scn.reg_headwind_realization_beta):.2f}"),
        ("Lease escalator (mean, σ)",
         f"{scn.lease_escalator_mean*100:.2f}% / {scn.lease_escalator_sd*100:.2f}%"),
        ("Cyber incident prob/yr", f"{scn.cyber_incident_prob_per_year*100:.1f}%"),
        ("V28 compression (mean, σ)",
         f"{scn.v28_compression_mean*100:.2f}% / {scn.v28_compression_sd*100:.2f}%"),
        ("Exit multiple (mean, σ)",
         f"{scn.exit_multiple_mean:.2f}x / {scn.exit_multiple_sd:.2f}x"),
        ("Hold years", f"{scn.hold_years}"),
    ]
    rows_html = "".join(
        f'<tr><td style="padding:5px 10px;color:{P["text_dim"]};">'
        f'{html.escape(label)}</td>'
        f'<td class="num" style="padding:5px 10px;text-align:right;'
        f'font-family:\'JetBrains Mono\',monospace;color:{P["text"]};">'
        f'{html.escape(val)}</td></tr>'
        for label, val in rows
    )
    return (
        f'<div style="background:{P["panel"]};border:1px solid '
        f'{P["border"]};border-radius:4px;padding:14px 20px;'
        f'margin-bottom:16px;">'
        f'<div style="font-size:9px;color:{P["text_faint"]};'
        f'letter-spacing:1.5px;text-transform:uppercase;font-weight:700;'
        f'margin-bottom:8px;">Scenario Inputs</div>'
        f'<table style="width:100%;border-collapse:collapse;font-size:11px;">'
        f'<tbody>{rows_html}</tbody></table>'
        f'</div>'
    )


def render_deal_mc_page(qs: Optional[Dict[str, List[str]]] = None) -> str:
    qs = qs or {}

    def first(k: str, default: str = "") -> str:
        return (qs.get(k) or [default])[0].strip()

    def float_or(k: str, d: float) -> float:
        v = first(k)
        try:
            return float(v) if v else d
        except ValueError:
            return d

    def int_or(k: str, d: int) -> int:
        v = first(k)
        try:
            return int(float(v)) if v else d
        except ValueError:
            return d

    if not first("ev_usd"):
        return _landing()

    try:
        scn = DealScenario(
            enterprise_value_usd=float_or("ev_usd", 0.0),
            equity_check_usd=float_or("equity_usd", 0.0),
            debt_usd=float_or("debt_usd", 0.0),
            entry_multiple=float_or("entry_multiple", 10.0),
            revenue_year0_usd=float_or("revenue_usd", 0.0),
            ebitda_year0_usd=float_or("ebitda_usd", 0.0),
            medicare_share=float_or("medicare_share", 0.25),
            organic_growth_mean=float_or("growth_mean", 0.04),
            organic_growth_sd=float_or("growth_sd", 0.025),
            denial_improvement_pp_mean=float_or("denial_impr_mean", 0.015),
            reg_headwind_usd=float_or("reg_headwind_usd", 0.0),
            exit_multiple_mean=float_or("exit_mult_mean", 9.0),
            exit_multiple_sd=float_or("exit_mult_sd", 1.5),
            cyber_incident_prob_per_year=float_or("cyber_prob", 0.05),
            v28_compression_mean=float_or("v28_mean", 0.0312),
            hold_years=int_or("hold_years", 5),
        )
    except Exception as exc:  # noqa: BLE001
        return chartis_shell(
            f'<div style="padding:24px;color:{P["negative"]};">'
            f'Invalid scenario inputs: {html.escape(str(exc))}</div>',
            "Deal MC",
        )

    if scn.equity_check_usd <= 0 or scn.revenue_year0_usd <= 0:
        return chartis_shell(
            f'<div style="padding:24px;color:{P["negative"]};">'
            f'Equity check and Year-0 revenue must both be positive.'
            f' <a href="/diligence/deal-mc" style="color:{P["accent"]};">'
            f'Back to form</a>.</div>',
            "Deal MC",
        )

    n_runs = max(200, min(10000, int_or("n_runs", 3000)))
    scenario_name = first("deal_name", "Scenario")

    result = run_deal_monte_carlo(
        scn, n_runs=n_runs, scenario_name=scenario_name,
    )

    # Chart panels.
    revenue_fan = _chart_panel(
        "Revenue Projection · P10/P25/P50/P75/P90",
        fan_chart(
            result.revenue_bands, title="", y_label="Revenue (USD)",
        ),
        note=(
            "Solid line is median; shaded bands are P10-P90. "
            "Compounds organic growth, provider attrition, and V28 "
            "compression on Medicare-exposed revenue."
        ),
    )
    ebitda_fan = _chart_panel(
        "EBITDA Projection · P10/P25/P50/P75/P90",
        fan_chart(
            result.ebitda_bands, title="", y_label="EBITDA (USD)",
        ),
        note=(
            "Margin evolves from baseline by denial-rate improvement, "
            "lease escalator drift, reg headwind realization, and "
            "per-year cyber incidents. Y0 is pre-hold baseline."
        ),
    )
    moic_hist = _chart_panel(
        "MOIC Distribution",
        moic_histogram_chart(result),
        note=(
            f"P(MOIC < 1.0x) = {result.prob_sub_1x*100:.1f}% · "
            f"P(MOIC >= 3.0x) = {result.prob_over_3x*100:.1f}%"
        ),
    )
    attribution = _chart_panel(
        "Variance Attribution · MOIC",
        attribution_chart(result),
        note=_attribution_note(result),
    )
    tornado = _chart_panel(
        "Sensitivity Tornado · One-Shot Stress",
        sensitivity_tornado(result),
        note=_sensitivity_note(result),
    )

    # JSON download for IC packet automation.
    json_payload = json.dumps(result.to_dict(), default=str)
    json_data_attr = html.escape(json_payload, quote=True)
    json_btn = (
        f'<div data-export-json="{json_data_attr}" '
        f'data-export-name="deal_mc_{scenario_name.replace(" ", "_")}"></div>'
    )

    body = (
        _hero_stats(result, scenario_name)
        + revenue_fan
        + ebitda_fan
        + moic_hist
        + attribution
        + tornado
        + _scenario_inputs_table(scn)
        + json_btn
    )
    return chartis_shell(
        body, f"Deal MC — {scenario_name}",
        subtitle="5-year forward distribution",
    )
