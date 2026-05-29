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
from ._chartis_kit import (
    P, chartis_shell, ck_kpi_block, ck_next_section, ck_page_title,
    ck_panel, ck_section_intro, ck_source_purpose,
)
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
    title = ck_page_title(
        "Thesis Pipeline",
        eyebrow="DILIGENCE · 13-STEP ORCHESTRATOR",
    )
    explainer = (
        '<p class="tp-explainer">'
        '<em>Close the loop.</em> '
        "Runs the full 13-step diligence chain — bankruptcy scan, CCD "
        "ingest, HFMA benchmarks, denial prediction, physician attrition, "
        "counterfactual advisor, Steward score, cyber score, deal autopsy, "
        "market intel — and returns a populated Deal MC scenario plus "
        "every headline number the IC Packet needs."
        '</p>'
    )
    form = (
        '<form method="GET" action="/diligence/thesis-pipeline" class="tp-form">'
        '<label class="tp-form-label">CCD fixture</label>'
        '<select name="dataset" required class="tp-form-select">'
        '<option value="">— pick a fixture —</option>'
        f'{options}</select>'
        '<div class="tp-form-grid">'
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
            '<div class="tp-form-field">'
            f'<label>{html.escape(label)}</label>'
            f'<input name="{name}" placeholder="{html.escape(placeholder)}">'
            '</div>'
        )
    form += (
        '</div>'
        '<button type="submit" class="cad-btn cad-btn-primary tp-form-submit">'
        '▶ Run Full Pipeline</button>'
        '</form>'
    )
    tp_styles = f"""
<style>
.tp-explainer{{font-family:var(--sc-serif);font-size:15px;line-height:1.6;
color:var(--sc-text-dim);max-width:68ch;
margin:var(--sc-s-4) 0 var(--sc-s-6);}}
.tp-explainer em{{color:var(--sc-teal-ink);font-style:italic;}}
.tp-form{{max-width:640px;}}
.tp-form-label{{font-size:9px;color:{P["text_faint"]};
letter-spacing:1.5px;text-transform:uppercase;font-weight:600;
display:block;margin-bottom:4px;}}
.tp-form-select{{width:100%;padding:6px 8px;background:{P["panel_alt"]};
color:{P["text"]};border:1px solid {P["border"]};
font-family:inherit;margin-bottom:12px;}}
.tp-form-grid{{display:grid;grid-template-columns:1fr 1fr;gap:12px;}}
.tp-form-field label{{font-size:9px;color:{P["text_faint"]};
letter-spacing:1.2px;text-transform:uppercase;font-weight:600;
display:block;margin-bottom:2px;}}
.tp-form-field input{{width:100%;padding:5px 7px;
background:{P["panel_alt"]};color:{P["text"]};
border:1px solid {P["border"]};
font-family:"JetBrains Mono",monospace;font-size:11px;}}
.tp-form-submit{{margin-top:16px;}}
</style>
"""
    body = (
        _scoped_styles()
        + tp_styles
        + '<div class="tp-wrap">'
        + title
        + explainer
        + ck_panel(form, title="Pipeline inputs")
        + '</div>'
    )
    return chartis_shell(
        body, "RCM Diligence — Thesis Pipeline",
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
    sim_pct = (
        f' <span class="ck-eyebrow">{int(report.top_autopsy_similarity*100)}%</span>'
        if report.top_autopsy_similarity else ''
    )
    return (
        '<div class="ck-kpi-strip">'
        + ck_kpi_block(
            "P50 MOIC", moic_num, sub="3000 trials · pipeline-driven",
            help={
                "definition": (
                    "Median MOIC across 3000 Monte Carlo trials seeded "
                    "by the 13-step pipeline. Read alongside P(MOIC<1x) "
                    "below — same median can hide very different "
                    "tail-risk profiles. Above 2.5x median signals "
                    "a deal worth IC time."
                ),
            },
        )
        + ck_kpi_block(
            "P(MOIC < 1x)", downside_num, sub="capital-loss probability",
            help={
                "definition": (
                    "Probability the deal returns less than the LP's "
                    "original equity check. Below 5% = robust; "
                    "5-15% = expected for PE healthcare; >25% = the "
                    "downside profile dominates and IC will dig hard."
                ),
            },
        )
        + ck_kpi_block(
            "Top variance driver",
            html.escape(report.top_variance_driver or "—"),
            sub="stress-test first",
            help={
                "definition": (
                    "Input lever contributing the most variance to the "
                    "MOIC distribution. Stress this one first in IC — "
                    "if the top driver is something the sponsor can "
                    "credibly hedge (rate, denial), the deal narrows; "
                    "if it's structural (payer mix, regulation), the "
                    "deal carries unhedgeable risk."
                ),
            },
        )
        + ck_kpi_block(
            "Historical analogue",
            html.escape(report.top_autopsy_match or "—") + sim_pct,
            sub="signature match",
            help={
                "definition": (
                    "Closest realized deal in the corpus by profile "
                    "signature (sector, size, payer mix, capital "
                    "structure). Use the analogue's actual exit "
                    "outcome as a reality check on the underwriting — "
                    "if the analogue lost money, ask why this deal "
                    "won't."
                ),
            },
        )
        + ck_kpi_block(
            "Denial recoverable", denial_num,
            sub="audit + appeal opportunity",
            help={
                "definition": (
                    "Annual EBITDA recoverable if the denial-driver "
                    "model's flags become appeals. 60-80% realism "
                    "haircut is already baked in; treat as upper "
                    "bound of RCM-only uplift."
                ),
            },
        )
        + ck_kpi_block(
            "Attrition EBITDA @ risk", attr_num,
            sub="PPAM 18-month horizon",
            help={
                "definition": (
                    "EBITDA at risk if predicted-physician-attrition "
                    "(PPAM) flags become actual departures over the "
                    "next 18 months. The metric to watch when the "
                    "deal's economics depend on a small set of "
                    "named providers."
                ),
            },
        )
        + ck_kpi_block(
            "Counterfactual lever", cf_num,
            sub="largest offer-shape fix",
            help={
                "definition": (
                    "Largest single lever that would flip the deal's "
                    "verdict from no to yes — the 'what we're waiting "
                    "for' input to negotiate on. If the counterfactual "
                    "is bigger than what's plausibly achievable, the "
                    "thesis holds without movement."
                ),
            },
        )
        + ck_kpi_block(
            "Bankruptcy verdict",
            html.escape(report.bankruptcy_verdict or "—"),
            sub="12-pattern scan",
            help={
                "definition": (
                    "Output of the 12-pattern bankruptcy-survivor "
                    "scan. GREEN = no critical pattern matches; "
                    "YELLOW = patterns flagged for review; "
                    "RED/CRITICAL = the deal signature matches a "
                    "documented PE healthcare collapse, so this is "
                    "the bear case at IC."
                ),
            },
        )
        + ck_kpi_block(
            "Steward tier",
            html.escape(report.steward_tier or "—"),
            sub="sale-leaseback risk",
            help={
                "definition": (
                    "Risk tier from the Steward-specific bankruptcy "
                    "checklist (sale-leaseback dependency, "
                    "Medical Properties Trust exposure, multi-state "
                    "complexity). Tier 1 = exhibits multiple Steward "
                    "structural signals; lower tiers = less "
                    "Steward-like risk profile."
                ),
            },
        )
        + '</div>'
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

    # 2026-05-28 batch 24 · universal strict 5-block head.
    from ._chartis_kit import ck_editorial_head
    try:
        report = run_thesis_pipeline(inp)
    except Exception as exc:  # noqa: BLE001
        return chartis_shell(
            ck_editorial_head(
                eyebrow="Thesis Pipeline",
                title="Pipeline failed.",
                meta="PIPELINE ERROR · CHECK INPUTS",
                lede_italic_phrase="The pipeline did not complete.",
                lede_body=html.escape(str(exc)),
            ),
            "Thesis Pipeline",
        )

    # Hero
    hero = ck_editorial_head(
        eyebrow=f"Thesis Pipeline · {html.escape(dataset)}",
        title=f"Full diligence chain — {html.escape(inp.deal_name)}",
        meta=(
            f"{len(report.step_log)} STEPS · "
            f"{report.total_compute_ms:.0f}ms TOTAL COMPUTE"
        ),
        lede_italic_phrase="Full diligence chain, end-to-end.",
        lede_body=(
            f"{len(report.step_log)} steps · "
            f"{report.total_compute_ms:.0f}ms total compute. "
            "Every analytic output + populated Deal MC scenario + IC "
            "headline numbers, auto-computed from the CCD and your "
            "supplied metadata."
        ),
    ) + _checklist_preview(report)

    body = (
        _scoped_styles()
        + ck_page_title(
            "Thesis Pipeline",
            eyebrow="RCM DILIGENCE",
            meta=f"Deal: {inp.deal_name} · 13-step orchestrator",
        )
        + '<div class="tp-wrap">'
        + deal_context_bar(qs, active_surface="pipeline")
        + ck_source_purpose(
            purpose="Run the full 13-step diligence chain (intake → analysis → risk → bridge → memo) on a deal in one pass to produce an IC-ready synthesis.",
            universe="illustrative",
            confidence="derived",
            source=f"Orchestrated over the selected '{html.escape(str(inp.dataset))}' CCD fixture + your entered deal economics — fixture claims are a sample, not the target's own. Re-run on the target's CCD before IC.",
            next_action="Open the IC packet",
            next_href="/diligence/ic-packet",
        )
        + export_json_panel(
            hero + _headline_grid(report),
            payload=report.to_dict(),
            name="thesis_pipeline_report",
        )
        + _step_log_block(report)
        + _deeplinks_block(report, inp)
        + '</div>'
        + bookmark_hint()
        + ck_next_section(
            "Open the diligence checklist",
            "/diligence/checklist",
            eyebrow="Continue —",
            italic_word="checklist",
        )
    )
    # 2026-05-28 wave-B: ck_page_actions adds Copy share link
    # + Back-to-top affordances. Idempotent JS guards.
    from ._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(
        body,
        f"Thesis Pipeline — {inp.deal_name}",
        active_nav="/diligence/thesis-pipeline",
        subtitle="13-step orchestrator · closes the loop",
    )
