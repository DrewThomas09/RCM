"""Thesis Pipeline page at /diligence/thesis-pipeline.

One button runs the full diligence chain against a fixture +
metadata and shows:

    - Step-by-step execution log with per-step timing
    - Headline numbers (P50 MOIC, P(sub 1x), top variance driver,
      top historical analogue, denial recoverable $, attrition
      EBITDA-at-risk $, counterfactual largest lever $, Steward
      tier, bankruptcy verdict)
    - Deep links to each individual analytic with the params
      already populated

    - Checklist auto-observation signal (which items were covered
      by the pipeline)

This closes the diligence-to-investment-math loop a partner
otherwise maintains by hand.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List, Optional

from ..diligence.thesis_pipeline import (
    PipelineInput, ThesisPipelineReport,
    pipeline_observations, run_thesis_pipeline,
)
from ..diligence._pages import AVAILABLE_FIXTURES, _resolve_dataset
from ..diligence.checklist import compute_status, DealObservations
from ._chartis_kit import P, chartis_shell
from .power_ui import (
    bookmark_hint, deal_context_bar, export_json_panel,
    provenance, sortable_table,
)


def _scoped_styles() -> str:
    css = """
.tp-wrap{{font-family:"Helvetica Neue",Arial,sans-serif;}}
.tp-eyebrow{{font-size:11px;letter-spacing:1.6px;text-transform:uppercase;
color:{tf};font-weight:600;}}
.tp-h1{{font-size:26px;color:{tx};font-weight:600;line-height:1.15;
margin:4px 0 0 0;letter-spacing:-.2px;}}
.tp-callout{{background:{pa};padding:12px 16px;
border-left:3px solid {ac};border-radius:0 3px 3px 0;
font-size:12px;color:{td};line-height:1.65;max-width:880px;margin-top:12px;}}
.tp-section-label{{font-size:10px;letter-spacing:1.6px;text-transform:uppercase;
font-weight:700;color:{tf};margin:22px 0 10px 0;}}
.tp-kpi-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));
gap:14px;margin-top:18px;}}
.tp-kpi{{background:{pn};border:1px solid {bd};border-radius:4px;
padding:14px 16px;transition:border-color 140ms ease;}}
.tp-kpi:hover{{border-color:{tf};}}
.tp-kpi__label{{font-size:9px;letter-spacing:1.4px;text-transform:uppercase;
color:{tf};margin-bottom:6px;font-weight:600;}}
.tp-kpi__val{{font-size:24px;line-height:1;font-family:"JetBrains Mono",monospace;
font-variant-numeric:tabular-nums;font-weight:700;}}
.tp-kpi__note{{font-size:10px;margin-top:4px;color:{tf};}}
.tp-step{{display:grid;grid-template-columns:28px 180px 80px 1fr;
gap:12px;align-items:baseline;padding:8px 14px;font-size:12px;
border-bottom:1px solid {bdim};background:{pn};}}
.tp-step:first-child{{border-top-left-radius:4px;border-top-right-radius:4px;}}
.tp-step:last-child{{border-bottom-left-radius:4px;
border-bottom-right-radius:4px;border-bottom:0;}}
.tp-step__status{{font-size:9px;font-weight:700;letter-spacing:1.3px;
text-transform:uppercase;text-align:center;padding:2px 0;border-radius:3px;}}
.tp-step__status.ok{{color:{po};border:1px solid {po};}}
.tp-step__status.fail{{color:{ne};border:1px solid {ne};}}
.tp-step__name{{color:{tx};font-weight:600;}}
.tp-step__time{{color:{td};font-family:"JetBrains Mono",monospace;
font-variant-numeric:tabular-nums;text-align:right;}}
.tp-step__detail{{color:{tf};font-size:11px;}}
""".format(
        tx=P["text"], td=P["text_dim"], tf=P["text_faint"],
        pn=P["panel"], pa=P["panel_alt"],
        bd=P["border"], bdim=P["border_dim"],
        ac=P["accent"], po=P["positive"], ne=P["negative"],
    )
    return f"<style>{css}</style>"


def _landing() -> str:
    options = "".join(
        f'<option value="{html.escape(n)}">{html.escape(l)}</option>'
        for n, l in AVAILABLE_FIXTURES
    )
    explainer = (
        f'<div style="max-width:720px;margin-bottom:20px;'
        f'font-size:13px;color:{P["text_dim"]};line-height:1.65;">'
        f'Runs the full 13-step diligence chain — bankruptcy scan, '
        f'CCD ingest, HFMA benchmarks, denial prediction, physician '
        f'attrition, counterfactual advisor, Steward score, cyber '
        f'score, deal autopsy, market intel — against a target and '
        f'returns a populated Deal MC scenario plus every headline '
        f'number IC Packet needs. One button replaces running the '
        f'analytics by hand.'
        f'</div>'
    )
    form = (
        f'<form method="GET" action="/diligence/thesis-pipeline" '
        f'style="max-width:640px;background:{P["panel"]};'
        f'border:1px solid {P["border"]};border-radius:4px;'
        f'padding:20px;margin-bottom:20px;">'
        f'<label style="font-size:9px;color:{P["text_faint"]};'
        f'letter-spacing:1.5px;text-transform:uppercase;'
        f'font-weight:600;display:block;margin-bottom:4px;">'
        f'CCD fixture</label>'
        f'<select name="dataset" required style="width:100%;'
        f'padding:6px 8px;background:{P["panel_alt"]};'
        f'color:{P["text"]};border:1px solid {P["border"]};'
        f'font-family:inherit;margin-bottom:12px;">'
        f'<option value="">— pick a fixture —</option>'
        f'{options}</select>'
        f'<div style="display:grid;grid-template-columns:1fr 1fr;'
        f'gap:12px;">'
    )
    for label, name, placeholder in [
        ("Deal name", "deal_name", "300-Bed Community Hospital"),
        ("Specialty", "specialty", "HOSPITAL"),
        ("States (comma-sep)", "states", "TX"),
        ("Legal structure", "legal_structure", "CORPORATE"),
        ("Market category", "market_category", "MULTI_SITE_ACUTE_HOSPITAL"),
        ("EV ($)", "enterprise_value_usd", "350000000"),
        ("Equity ($)", "equity_check_usd", "150000000"),
        ("Debt ($)", "debt_usd", "200000000"),
        ("Revenue Y0 ($)", "revenue_year0_usd", "250000000"),
        ("EBITDA Y0 ($)", "ebitda_year0_usd", "35000000"),
        ("Landlord", "landlord", "Medical Properties Trust"),
        ("Lease term (yrs)", "lease_term_years", "20"),
        ("Lease escalator %", "lease_escalator_pct", "0.035"),
        ("EBITDAR coverage", "ebitdar_coverage", "1.1"),
        ("Annual rent ($)", "annual_rent_usd", "40000000"),
        ("OON rev share", "oon_revenue_share", "0.08"),
    ]:
        form += (
            f'<div><label style="font-size:9px;color:{P["text_faint"]};'
            f'letter-spacing:1.2px;text-transform:uppercase;'
            f'font-weight:600;display:block;margin-bottom:2px;">'
            f'{html.escape(label)}</label>'
            f'<input name="{name}" placeholder="{html.escape(placeholder)}" '
            f'style="width:100%;padding:5px 7px;background:{P["panel_alt"]};'
            f'color:{P["text"]};border:1px solid {P["border"]};'
            f'font-family:\'JetBrains Mono\',monospace;font-size:11px;">'
            f'</div>'
        )
    form += (
        f'</div>'
        f'<button type="submit" style="margin-top:16px;padding:10px 24px;'
        f'background:{P["accent"]};color:{P["panel"]};border:0;'
        f'font-size:11px;letter-spacing:1.5px;text-transform:uppercase;'
        f'font-weight:700;cursor:pointer;border-radius:3px;">'
        f'▶ Run Full Pipeline</button>'
        f'</form>'
    )
    body = (
        _scoped_styles()
        + '<div class="tp-wrap">'
        + f'<div style="padding:24px 0 12px 0;">'
        + f'<div class="tp-eyebrow">RCM Diligence</div>'
        + f'<div class="tp-h1">Thesis Pipeline — close the loop</div>'
        + f'</div>'
        + explainer
        + form
        + '</div>'
    )
    return chartis_shell(
        body, "RCM Diligence — Thesis Pipeline",
        subtitle="13-step orchestrator · full analytic chain",
    )


def _headline_grid(report: ThesisPipelineReport) -> str:
    def _fmt_x(v: Optional[float]) -> str:
        return f'{v:.2f}x' if v is not None else '—'

    def _fmt_pct(v: Optional[float]) -> str:
        return f'{v*100:.1f}%' if v is not None else '—'

    def _fmt_dollar(v: Optional[float]) -> str:
        return f'${v:,.0f}' if v is not None else '—'

    moic_color = (
        P["positive"] if report.p50_moic and report.p50_moic >= 2.5
        else P["warning"] if report.p50_moic and report.p50_moic >= 1.5
        else P["negative"]
    )
    downside_color = (
        P["negative"] if report.prob_sub_1x and report.prob_sub_1x > 0.25
        else P["warning"] if report.prob_sub_1x and report.prob_sub_1x > 0.10
        else P["positive"]
    )
    verdict_color = {
        "CRITICAL": P["critical"], "RED": P["negative"],
        "YELLOW": P["warning"], "GREEN": P["positive"],
    }.get(report.bankruptcy_verdict or "", P["text_dim"])
    steward_color = {
        "TIER_1_STEWARD_REPLAY": P["critical"],
        "TIER_2_LEASE_STRESS": P["negative"],
        "TIER_3_ELEVATED": P["warning"],
        "TIER_4_STANDARD": P["positive"],
    }.get(report.steward_tier or "", P["text_dim"])

    moic_num = provenance(
        _fmt_x(report.p50_moic),
        source="DealMCResult.moic_p50",
        formula="median(equity_exit / equity_check across 1500 trials)",
        detail=(
            "Data-driven P50 with pipeline-populated drivers "
            "(denial improvement from DenialPrediction, reg "
            "headwind from Counterfactual, physician attrition "
            "from PPAM)."
        ),
    )
    downside_num = provenance(
        _fmt_pct(report.prob_sub_1x),
        source="DealMCResult.prob_sub_1x",
        formula="count(trials where MOIC < 1.0) / n_runs",
        detail="Fraction of trials that lose capital over the hold.",
    )
    denial_num = provenance(
        _fmt_dollar(report.denial_recoverable_usd),
        source="DenialPredictionReport.bridge_input.recoverable_revenue_usd",
        formula="sum(predicted_denial × charge where status != DENIED)",
        detail="Systematic misses — claims flagged but not denied.",
    )
    cf_num = provenance(
        _fmt_dollar(report.counterfactual_largest_lever_usd),
        source="CounterfactualSet.largest_lever.estimated_dollar_impact_usd",
        formula="max(counterfactual_lever dollar impact across modules)",
        detail="Largest offer-shape modification that flips a RED/CRITICAL finding.",
    )
    attr_num = provenance(
        _fmt_dollar(report.attrition_ebitda_at_risk_usd),
        source="AttritionReport.bridge_input.ebitda_at_risk_usd",
        formula="expected_collections_lost × ebitda_margin",
        detail="Physician-attrition EBITDA hit (PPAM rolled up).",
    )
    return (
        f'<div class="tp-kpi-grid">'
        f'<div class="tp-kpi">'
        f'<div class="tp-kpi__label">P50 MOIC</div>'
        f'<div class="tp-kpi__val" style="color:{moic_color};">'
        f'{moic_num}</div>'
        f'<div class="tp-kpi__note">3000 trials · pipeline-driven</div>'
        f'</div>'
        f'<div class="tp-kpi">'
        f'<div class="tp-kpi__label">P(MOIC &lt; 1x)</div>'
        f'<div class="tp-kpi__val" style="color:{downside_color};">'
        f'{downside_num}</div>'
        f'<div class="tp-kpi__note">capital-loss probability</div>'
        f'</div>'
        f'<div class="tp-kpi">'
        f'<div class="tp-kpi__label">Top variance driver</div>'
        f'<div class="tp-kpi__val" style="color:{P["text"]};'
        f'font-size:16px;">{html.escape(report.top_variance_driver or "—")}</div>'
        f'<div class="tp-kpi__note">stress-test first</div>'
        f'</div>'
        f'<div class="tp-kpi">'
        f'<div class="tp-kpi__label">Historical analogue</div>'
        f'<div class="tp-kpi__val" style="color:{P["text"]};'
        f'font-size:14px;">'
        f'{html.escape(report.top_autopsy_match or "—")}'
        + (
            f' <span style="color:{P["text_faint"]};font-size:12px;">'
            f'{int(report.top_autopsy_similarity*100)}%</span>'
            if report.top_autopsy_similarity else ''
        )
        + f'</div>'
        f'<div class="tp-kpi__note">signature match</div>'
        f'</div>'
        f'<div class="tp-kpi">'
        f'<div class="tp-kpi__label">Denial recoverable</div>'
        f'<div class="tp-kpi__val" style="color:{P["positive"]};">'
        f'{denial_num}</div>'
        f'<div class="tp-kpi__note">audit + appeal opportunity</div>'
        f'</div>'
        f'<div class="tp-kpi">'
        f'<div class="tp-kpi__label">Attrition EBITDA @ risk</div>'
        f'<div class="tp-kpi__val" style="color:{P["negative"]};">'
        f'{attr_num}</div>'
        f'<div class="tp-kpi__note">PPAM 18-month horizon</div>'
        f'</div>'
        f'<div class="tp-kpi">'
        f'<div class="tp-kpi__label">Counterfactual lever</div>'
        f'<div class="tp-kpi__val" style="color:{P["positive"]};">'
        f'{cf_num}</div>'
        f'<div class="tp-kpi__note">largest offer-shape fix</div>'
        f'</div>'
        f'<div class="tp-kpi">'
        f'<div class="tp-kpi__label">Bankruptcy verdict</div>'
        f'<div class="tp-kpi__val" style="color:{verdict_color};'
        f'font-size:18px;">'
        f'{html.escape(report.bankruptcy_verdict or "—")}</div>'
        f'<div class="tp-kpi__note">12-pattern scan</div>'
        f'</div>'
        f'<div class="tp-kpi">'
        f'<div class="tp-kpi__label">Steward tier</div>'
        f'<div class="tp-kpi__val" style="color:{steward_color};'
        f'font-size:14px;">'
        f'{html.escape(report.steward_tier or "—")}</div>'
        f'<div class="tp-kpi__note">sale-leaseback risk</div>'
        f'</div>'
        f'</div>'
    )


def _step_log_block(report: ThesisPipelineReport) -> str:
    rows: List[str] = []
    for s in report.step_log:
        status = s.get("status", "ok")
        cls = "ok" if status == "ok" else "fail"
        detail = s.get("error", "")
        rows.append(
            f'<div class="tp-step">'
            f'<span class="tp-step__status {cls}">'
            f'{"✓" if cls == "ok" else "✗"}</span>'
            f'<span class="tp-step__name">'
            f'{html.escape(s.get("step", "—"))}</span>'
            f'<span class="tp-step__time">'
            f'{s.get("elapsed_ms", 0):.1f}ms</span>'
            f'<span class="tp-step__detail">{html.escape(detail)}</span>'
            f'</div>'
        )
    total = report.total_compute_ms
    return (
        f'<div class="tp-section-label">Step log · '
        f'{len(report.step_log)} steps · {total:.0f}ms total compute</div>'
        f'<div style="border:1px solid {P["border"]};border-radius:4px;'
        f'overflow:hidden;">{"".join(rows)}</div>'
    )


def _deeplinks_block(report: ThesisPipelineReport, inp: PipelineInput) -> str:
    """Deep-links into each individual analytic with params pre-seeded."""
    import urllib.parse as _urllib
    dataset = inp.dataset
    links: List[tuple] = []
    if report.ccd is not None:
        links.append((
            "Benchmarks (Phase 2)",
            f"/diligence/benchmarks?dataset={_urllib.quote(dataset)}",
        ))
    if report.denial_report is not None:
        links.append((
            "Denial Prediction",
            f"/diligence/denial-prediction?dataset={_urllib.quote(dataset)}",
        ))
    if report.autopsy_matches:
        links.append((
            "Deal Autopsy",
            f"/diligence/deal-autopsy?dataset={_urllib.quote(dataset)}",
        ))
    if report.counterfactual_set is not None:
        links.append((
            "Counterfactual Advisor",
            f"/diligence/counterfactual?dataset={_urllib.quote(dataset)}",
        ))
    if report.deal_mc_result is not None:
        mc_qs = {
            "ev_usd": str(int(inp.enterprise_value_usd or 0)),
            "equity_usd": str(int(inp.equity_check_usd or 0)),
            "debt_usd": str(int(inp.debt_usd or 0)),
            "revenue_usd": str(int(inp.revenue_year0_usd or 0)),
            "ebitda_usd": str(int(inp.ebitda_year0_usd or 0)),
            "entry_multiple": str(inp.entry_multiple or 0),
            "n_runs": str(inp.n_runs),
            "deal_name": inp.deal_name,
        }
        links.append((
            "Deal Monte Carlo",
            f"/diligence/deal-mc?{_urllib.urlencode(mc_qs)}",
        ))
    if report.attrition_report is not None:
        links.append((
            "Physician Attrition",
            f"/diligence/physician-attrition?target_name={_urllib.quote(inp.deal_name)}",
        ))
    if report.market_intel is not None:
        mi_qs = {"category": inp.market_category or ""}
        if inp.revenue_year0_usd:
            mi_qs["revenue_usd"] = str(int(inp.revenue_year0_usd))
        if inp.enterprise_value_usd:
            mi_qs["ev_usd"] = str(int(inp.enterprise_value_usd))
        links.append((
            "Market Intel",
            f"/market-intel?{_urllib.urlencode(mi_qs)}",
        ))
        links.append((
            "Seeking Alpha",
            "/market-intel/seeking-alpha",
        ))

    # New diligence modules — auto-linked when the corresponding
    # pipeline step fired + params are available.
    target_name_q = _urllib.quote(inp.deal_name)
    npr = int(inp.revenue_year0_usd or 0)
    eb = int(inp.ebitda_year0_usd or 0)
    debt = int(inp.debt_usd or 0)
    if report.regulatory_exposure is not None:
        reg_qs = {
            "target_name": inp.deal_name,
            "specialty": inp.specialty or "HOSPITAL",
        }
        if npr:
            reg_qs["revenue_usd"] = str(npr)
        if eb:
            reg_qs["ebitda_usd"] = str(eb)
        if inp.medicare_share:
            reg_qs["ma_mix_pct"] = str(inp.medicare_share)
        links.append((
            "Regulatory Calendar",
            f"/diligence/regulatory-calendar?{_urllib.urlencode(reg_qs)}",
        ))
    if report.covenant_stress is not None and eb and debt:
        cov_qs = {
            "deal_name": inp.deal_name,
            "ebitda_y0": str(eb),
            "total_debt_usd": str(debt),
            "quarters": "20",
        }
        links.append((
            "Covenant Stress",
            f"/diligence/covenant-stress?{_urllib.urlencode(cov_qs)}",
        ))
    if report.payer_stress is not None and npr:
        links.append((
            "Payer Mix Stress",
            f"/diligence/payer-stress?target_name={target_name_q}"
            f"&total_npr_usd={npr}&total_ebitda_usd={eb}",
        ))
    if report.hcris_xray is not None and inp.hcris_ccn:
        links.append((
            "HCRIS X-Ray",
            f"/diligence/hcris-xray?ccn={_urllib.quote(inp.hcris_ccn)}",
        ))
    # Bridge Audit — always available (analyst pastes a bridge)
    ba_qs = {
        "target_name": inp.deal_name,
    }
    if inp.enterprise_value_usd:
        ba_qs["asking_price_usd"] = str(int(inp.enterprise_value_usd))
    if inp.entry_multiple:
        ba_qs["entry_multiple"] = str(inp.entry_multiple)
    if inp.medicare_share:
        ba_qs["ma_mix_pct"] = str(inp.medicare_share)
    links.append((
        "Bridge Audit",
        f"/diligence/bridge-audit?{_urllib.urlencode(ba_qs)}",
    ))
    # Bear Case — always link; page handles missing dataset gracefully
    bc_qs = {
        "dataset": dataset, "deal_name": inp.deal_name,
        "specialty": inp.specialty or "",
    }
    if npr:
        bc_qs["revenue_year0_usd"] = str(npr)
    if eb:
        bc_qs["ebitda_year0_usd"] = str(eb)
    if inp.enterprise_value_usd:
        bc_qs["enterprise_value_usd"] = str(int(inp.enterprise_value_usd))
    if inp.equity_check_usd:
        bc_qs["equity_check_usd"] = str(int(inp.equity_check_usd))
    if debt:
        bc_qs["debt_usd"] = str(debt)
    if inp.medicare_share:
        bc_qs["medicare_share"] = str(inp.medicare_share)
    if inp.hcris_ccn:
        bc_qs["hcris_ccn"] = inp.hcris_ccn
    links.append((
        "Bear Case",
        f"/diligence/bear-case?{_urllib.urlencode(bc_qs)}",
    ))

    links.append((
        "IC Packet",
        f"/diligence/ic-packet?dataset={_urllib.quote(dataset)}&"
        f"deal_name={_urllib.quote(inp.deal_name)}&"
        f"specialty={_urllib.quote(inp.specialty or '')}&"
        f"market_category={_urllib.quote(inp.market_category or '')}&"
        f"revenue_usd={int(inp.revenue_year0_usd or 0)}",
    ))

    cards = "".join(
        f'<a href="{html.escape(url)}" '
        f'style="display:block;padding:10px 14px;'
        f'background:{P["panel"]};border:1px solid {P["border"]};'
        f'border-radius:4px;color:{P["text"]};text-decoration:none;'
        f'font-size:12px;font-weight:600;transition:border-color 140ms ease;" '
        f'onmouseover="this.style.borderColor=\'{P["accent"]}\'" '
        f'onmouseout="this.style.borderColor=\'{P["border"]}\'">'
        f'<span style="color:{P["accent"]};">→</span> '
        f'{html.escape(label)}</a>'
        for label, url in links
    )
    return (
        f'<div class="tp-section-label">'
        f'Drill into each analytic · params pre-seeded</div>'
        f'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px;">'
        f'{cards}</div>'
    )


def _checklist_preview(report: ThesisPipelineReport) -> str:
    """Show the checklist items the pipeline just auto-covered."""
    obs_dict = pipeline_observations(report)
    obs = DealObservations(**obs_dict)
    state = compute_status(obs)
    p0_cov = state.p0_coverage * 100
    color = (
        P["positive"] if p0_cov >= 100
        else P["warning"] if p0_cov >= 70
        else P["negative"]
    )
    return (
        f'<div style="margin-top:14px;padding:12px 14px;'
        f'background:{P["panel_alt"]};border-left:3px solid {color};'
        f'border-radius:0 3px 3px 0;font-size:12px;color:{P["text_dim"]};'
        f'line-height:1.6;max-width:880px;">'
        f'<strong style="color:{P["text"]};">Checklist impact: </strong>'
        f'This pipeline run auto-covered '
        f'{len(obs_dict)} diligence items. P0 coverage is now '
        f'<span style="color:{color};font-weight:600;">{p0_cov:.0f}%</span> '
        f'({state.open_p0} P0 items + {state.open_p1} P1 items remain '
        f'open — mostly manual / legal / management-reference tasks). '
        f'<a href="/diligence/checklist" style="color:{P["accent"]};">'
        f'Open Diligence Checklist →</a>'
        f'</div>'
    )


def render_thesis_pipeline_page(
    qs: Optional[Dict[str, List[str]]] = None,
) -> str:
    qs = qs or {}
    dataset = (qs.get("dataset") or [""])[0].strip()
    if not dataset:
        return _landing()
    if _resolve_dataset(dataset) is None:
        return _landing()

    # Parse structured inputs.
    def _f(key: str) -> Optional[float]:
        raw = (qs.get(key) or [""])[0].strip()
        if not raw:
            return None
        try:
            return float(raw)
        except ValueError:
            return None

    def _i(key: str) -> Optional[int]:
        v = _f(key)
        return int(v) if v is not None else None

    def _s(key: str, default: str = "") -> str:
        return (qs.get(key) or [default])[0].strip() or default

    def _list(key: str) -> List[str]:
        raw = _s(key)
        return [t.strip() for t in raw.split(",") if t.strip()]

    inp = PipelineInput(
        dataset=dataset,
        deal_name=_s("deal_name") or dataset,
        enterprise_value_usd=_f("enterprise_value_usd") or _f("ev_usd"),
        equity_check_usd=_f("equity_check_usd") or _f("equity_usd"),
        debt_usd=_f("debt_usd"),
        revenue_year0_usd=_f("revenue_year0_usd") or _f("revenue_usd"),
        ebitda_year0_usd=_f("ebitda_year0_usd") or _f("ebitda_usd"),
        entry_multiple=_f("entry_multiple"),
        medicare_share=_f("medicare_share"),
        specialty=_s("specialty") or None,
        states=_list("states"),
        cbsa_codes=_list("cbsa_codes"),
        legal_structure=_s("legal_structure") or None,
        landlord=_s("landlord") or None,
        lease_term_years=_i("lease_term_years"),
        lease_escalator_pct=_f("lease_escalator_pct"),
        ebitdar_coverage=_f("ebitdar_coverage"),
        annual_rent_usd=_f("annual_rent_usd"),
        portfolio_ebitdar_usd=_f("portfolio_ebitdar_usd"),
        geography=_s("geography") or None,
        oon_revenue_share=_f("oon_revenue_share"),
        market_category=_s("market_category") or None,
        ehr_vendor=_s("ehr_vendor") or None,
        business_associates=_list("business_associates"),
        n_runs=_i("n_runs") or 1500,
    )

    try:
        report = run_thesis_pipeline(inp)
    except Exception as exc:  # noqa: BLE001
        return chartis_shell(
            f'<div style="padding:24px;color:{P["negative"]};">'
            f'Pipeline failed: {html.escape(str(exc))}</div>',
            "Thesis Pipeline",
        )

    # Hero
    hero = (
        f'<div style="padding:22px 0 12px 0;border-bottom:1px solid '
        f'{P["border"]};margin-bottom:22px;">'
        f'<div class="tp-eyebrow">Thesis Pipeline · {html.escape(dataset)}</div>'
        f'<div class="tp-h1">{html.escape(inp.deal_name)}</div>'
        f'<div style="font-size:11px;color:{P["text_faint"]};margin-top:4px;">'
        f'{len(report.step_log)} steps · '
        f'{report.total_compute_ms:.0f}ms total compute</div>'
        f'<div class="tp-callout">'
        f'<strong style="color:{P["text"]};">What this shows: </strong>'
        f'Every analytic output + populated Deal MC scenario + IC '
        f'headline numbers, auto-computed from the CCD and your '
        f'supplied metadata. The Deal Profile localStorage writeback '
        f'and Deal MC hydration both read this report.'
        f'</div>'
        f'{_checklist_preview(report)}'
        f'</div>'
    )

    body = (
        _scoped_styles()
        + '<div class="tp-wrap">'
        + deal_context_bar(qs, active_surface="pipeline")
        + export_json_panel(
            hero + _headline_grid(report),
            payload=report.to_dict(),
            name="thesis_pipeline_report",
        )
        + _step_log_block(report)
        + _deeplinks_block(report, inp)
        + '</div>'
        + bookmark_hint()
    )
    return chartis_shell(
        body,
        f"Thesis Pipeline — {inp.deal_name}",
        subtitle="13-step orchestrator · closes the loop",
    )
