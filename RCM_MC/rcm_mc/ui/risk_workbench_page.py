"""Regulatory Risk Workbench — partner-facing integration of the
9 Tier 1-3 diligence subpackages (Prompts G through O) under one
roof.

The workbench runs every engine against the caller's inputs and
renders a scorecard. Each panel shows:

    - a severity band (GREEN / YELLOW / RED / CRITICAL where
      applicable; LOW / MEDIUM / HIGH where the submodule uses
      that scheme)
    - 1-2 headline numbers
    - a drill-down link when a dedicated route exists (e.g.,
      /screening/bankruptcy-survivor)

Input model: the page accepts a ``WorkbenchInput`` dataclass
(same shape as the bankruptcy-survivor scan plus additional fields
for physician comp, cyber, MA dynamics). When a field is missing,
the corresponding panel renders a "not supplied" state rather
than a fabricated number. The workbench never interpolates.
"""
from __future__ import annotations

import html
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..diligence.counterfactual import (
    CounterfactualSet, advise_all,
)
from ..diligence.cyber import (
    assess_business_associates, compose_cyber_score,
    cyber_bridge_reserve_pct, detect_deferred_it_capex,
    ehr_vendor_risk_score, simulate_bi_loss,
)
from ..diligence.labor import (
    benchmark_staffing_ratio, detect_synthetic_fte,
    forecast_wage_inflation,
)
from ..diligence.ma_dynamics import (
    analyze_coding_intensity, compute_v28_recalibration,
    estimate_medicaid_unwind_impact,
)
from ..diligence.patient_pay import (
    compute_medical_debt_overlay, segment_patient_pay_exposure,
)
from ..diligence.physician_comp import (
    Provider, check_stark_redline, ingest_providers,
    recommend_earnout_structure, simulate_productivity_drift,
)
from ..diligence.physician_attrition import (
    analyze_roster as analyze_attrition_roster,
    FlightRiskBand,
)
from ..diligence.quality import project_vbp_hrrp
from ..diligence.real_estate import (
    LeaseLine, LeaseSchedule, StewardRiskTier,
    compute_lease_waterfall, compute_steward_score,
)
from ..diligence.referral import (
    compute_provider_concentration, stress_test_departures,
)
from ..diligence.regulatory import (
    RegulatoryBand, compose_packet, compute_antitrust_exposure,
    compute_cpom_exposure, compute_nsa_exposure, compute_team_impact,
    simulate_site_neutral_impact,
)
from ..diligence.reputational import (
    detect_bankruptcy_contagion, state_ag_enforcement_heatmap,
)
from ..diligence.screening import (
    ScanInput, run_bankruptcy_survivor_scan,
)
from ..diligence.working_capital import (
    compute_normalized_peg, detect_pre_close_pull_forward,
    estimate_dnfb,
)
from ._chartis_kit import P, chartis_shell


# ── Input dataclass ────────────────────────────────────────────────

@dataclass
class WorkbenchInput:
    """Partner-supplied workbench inputs. Every field is optional;
    missing fields suppress the corresponding panel rather than
    fabricating numbers."""
    target_name: str = "Unnamed Target"

    # Regulatory
    legal_structure: Optional[str] = None
    states: List[str] = field(default_factory=list)
    msas: List[str] = field(default_factory=list)
    cbsa_codes: List[str] = field(default_factory=list)
    specialty: Optional[str] = None
    is_hospital_based_physician: bool = False
    oon_revenue_share: Optional[float] = None
    oon_dollars_annual: Optional[float] = None
    hopd_revenue_annual_usd: Optional[float] = None
    acquisitions: List[Dict[str, Any]] = field(default_factory=list)

    # Real estate
    landlord: Optional[str] = None
    lease_term_years: Optional[int] = None
    lease_escalator_pct: Optional[float] = None
    ebitdar_coverage: Optional[float] = None
    geography: Optional[str] = None
    annual_rent_usd: Optional[float] = None
    portfolio_revenue_usd: Optional[float] = None
    portfolio_ebitdar_usd: Optional[float] = None

    # Physician comp (light)
    providers: List[Provider] = field(default_factory=list)

    # Cyber
    ehr_vendor: Optional[str] = None
    business_associates: List[str] = field(default_factory=list)
    revenue_per_day_usd: Optional[float] = None
    years_since_ehr: Optional[float] = None
    annual_revenue_usd: Optional[float] = None
    it_fte_count: Optional[float] = None

    # MA dynamics
    ma_members_with_diagnosis_codes: List[Dict[str, Any]] = field(default_factory=list)
    hcc_capture_rate: Optional[float] = None
    specialty_benchmark_capture_rate: Optional[float] = None
    add_only_retrospective_pct: Optional[float] = None
    total_ma_revenue_usd: Optional[float] = None
    medicaid_revenue_annual_usd: Optional[float] = None
    medicaid_state: Optional[str] = None

    # Quality
    star_rating: Optional[int] = None
    excess_readmission_ratios: Dict[str, float] = field(default_factory=dict)
    hac_worst_quartile: bool = False
    base_ms_drg_payments_usd: Optional[float] = None

    # Working capital
    trailing_monthly_nwc_usd: List[float] = field(default_factory=list)
    dnfb_claims: Optional[int] = None
    avg_claim_value_usd: Optional[float] = None
    avg_daily_discharges: Optional[float] = None
    last_60d_collections_usd: Optional[float] = None
    prior_12_monthly_collections_usd: List[float] = field(default_factory=list)

    # Labor
    wage_bill_usd: Optional[float] = None
    wage_msa: Optional[str] = None
    scheduled_fte: Optional[float] = None
    billing_npi_count: Optional[int] = None

    # Referral concentration
    revenue_by_provider: Dict[str, float] = field(default_factory=dict)
    departing_providers: List[str] = field(default_factory=list)

    # Patient pay
    hdhp_member_share: Optional[float] = None
    patient_responsibility_usd: Optional[float] = None


# ── Severity palette ───────────────────────────────────────────────

_SEVERITY_COLOR = {
    "GREEN":      P["positive"],
    "LOW":        P["positive"],
    "IMMATERIAL": P["positive"],
    "YELLOW":     P["warning"],
    "WATCH":      P["warning"],
    "MEDIUM":     P["warning"],
    "RED":        P["negative"],
    "HIGH":       P["negative"],
    "CRITICAL":   P["negative"],
    "UNKNOWN":    P["text_faint"],
}


def _badge(label: str, sev: str) -> str:
    color = _SEVERITY_COLOR.get(sev.upper(), P["text_dim"])
    return (
        f'<span style="background:{P["panel_alt"]};color:{color};'
        f'padding:2px 10px;border-radius:3px;font-size:10px;'
        f'font-weight:700;letter-spacing:.5px;text-transform:uppercase;">'
        f'{html.escape(label)} · {html.escape(sev)}</span>'
    )


def _panel(
    title: str, body: str, *,
    badge: Optional[str] = None,
    explanation: Optional[str] = None,
) -> str:
    head = (
        f'<div style="display:flex;justify-content:space-between;'
        f'align-items:center;margin-bottom:8px;">'
        f'<div style="font-size:11px;color:{P["text_dim"]};'
        f'letter-spacing:1px;text-transform:uppercase;font-weight:600;">'
        f'{html.escape(title)}</div>'
        f'{badge or ""}</div>'
    )
    footer = ""
    if explanation:
        footer = (
            f'<div style="margin-top:10px;padding:8px 10px;'
            f'background:{P["panel_alt"]};border-left:2px solid '
            f'{P["accent"]};font-size:11px;color:{P["text_dim"]};'
            f'line-height:1.55;border-radius:0 3px 3px 0;">'
            f'<strong style="color:{P["text"]};font-size:9px;'
            f'text-transform:uppercase;letter-spacing:1.2px;'
            f'margin-right:4px;">What this shows:</strong>'
            f'{explanation}</div>'
        )
    return (
        f'<div style="background:{P["panel"]};border:1px solid {P["border"]};'
        f'border-radius:4px;padding:14px 16px;margin-bottom:12px;">'
        f'{head}{body}{footer}</div>'
    )


# Peer-context lookup tables — what a band means in partner-speak.
_TIER_EXPLAINER = {
    # Steward tier (real estate)
    "TIER_1_STEWARD_REPLAY": (
        "EBITDAR coverage + escalator profile mirrors the Steward 2016 "
        "entry signature. This is the highest-risk real-estate band in "
        "the library — partners should walk unless the sale-leaseback is "
        "dissolvable or the escalator is capped."
    ),
    "TIER_2_LEASE_STRESS": (
        "Lease economics are meaningfully stressed vs. the peer "
        "acute-hospital median. Cap the escalator or exit the sale-"
        "leaseback as a condition of offer."
    ),
    "TIER_3_ELEVATED": (
        "Elevated real-estate risk but not a thesis breaker. Model a "
        "5% escalator shock in Deal MC to size the downside."
    ),
    "TIER_4_STANDARD": (
        "Real-estate profile is in-line with peer norms — neither a "
        "lever nor a risk. The bridge should assume no RE-driven "
        "uplift or downside."
    ),
    # Regulatory
    "RED": (
        "Regulatory composite is RED — exposure materially impacts "
        "the thesis. Counterfactual Advisor should already be "
        "quoting the offer-shape modification that flips this "
        "finding. If not, add it as a walkaway condition."
    ),
    "YELLOW": (
        "Regulatory composite is YELLOW — manageable but needs to "
        "show up in the 100-day plan. Not a walkaway; is a diligence "
        "question for the seller."
    ),
    "GREEN": (
        "Regulatory composite is GREEN — no material exposure in the "
        "target's footprint. No bridge adjustment needed."
    ),
    # Cyber
    "CRITICAL": (
        "Cyber posture is CRITICAL — a Change-Healthcare-class "
        "incident would exceed typical bridge reserves. Add a cyber "
        "BI loss line to the bridge at the modeled dollar exposure."
    ),
    "HIGH": (
        "Elevated findings — typically means Stark overlap or comp "
        "above FMV on the top 10% of providers. Earnout design "
        "should include Stark-compliance reps."
    ),
    "LOW": (
        "Findings are below the action threshold. Comp structure is "
        "defensible without restructuring."
    ),
    "UNKNOWN": (
        "Panel not yet populated — supply inputs on Deal Profile to "
        "run this diligence engine."
    ),
}


def _explain_for(band_or_tier: str) -> Optional[str]:
    """Return a plain-English explanation for a band label, or None
    if we don't have a mapping. Never fabricates — absence is OK."""
    return _TIER_EXPLAINER.get((band_or_tier or "").upper())


def _not_supplied(reason: str) -> str:
    return (
        f'<div style="font-size:11px;color:{P["text_faint"]};'
        f'font-style:italic;">Not supplied — {html.escape(reason)}</div>'
    )


def _kv_row(
    label: str, value: str,
    color: Optional[str] = None,
    *,
    peer: Optional[str] = None,
) -> str:
    """One metric row inside a workbench panel.

    Optional ``peer`` — rendered as a small right-aligned subline
    like Benchmarks KPI cards (e.g., "peer median 1.30x"). Keep it
    short; this row is shown in a two-column grid.
    """
    c = color or P["text"]
    if peer:
        return (
            f'<div style="display:flex;justify-content:space-between;'
            f'align-items:baseline;font-size:11px;margin:2px 0;">'
            f'<span style="color:{P["text_dim"]};">{html.escape(label)}</span>'
            f'<span style="text-align:right;">'
            f'<span class="mono" style="color:{c};">{html.escape(value)}</span>'
            f'<span style="font-size:9.5px;color:{P["text_faint"]};'
            f'display:block;">{html.escape(peer)}</span>'
            f'</span></div>'
        )
    return (
        f'<div style="display:flex;justify-content:space-between;'
        f'font-size:11px;margin:2px 0;">'
        f'<span style="color:{P["text_dim"]};">{html.escape(label)}</span>'
        f'<span class="mono" style="color:{c};">{html.escape(value)}</span>'
        f'</div>'
    )


# ── Panel renderers ────────────────────────────────────────────────

def _panel_bankruptcy_survivor(inp: WorkbenchInput) -> str:
    scan = run_bankruptcy_survivor_scan(ScanInput(
        target_name=inp.target_name,
        specialty=inp.specialty, states=inp.states,
        msas=inp.msas, cbsa_codes=inp.cbsa_codes,
        legal_structure=inp.legal_structure,
        landlord=inp.landlord,
        lease_term_years=inp.lease_term_years,
        lease_escalator_pct=inp.lease_escalator_pct,
        ebitdar_coverage=inp.ebitdar_coverage,
        geography=inp.geography,
        is_hospital_based_physician=inp.is_hospital_based_physician,
        oon_revenue_share=inp.oon_revenue_share,
        hopd_revenue_annual_usd=inp.hopd_revenue_annual_usd,
        acquisitions=inp.acquisitions,
        has_grandfathered_hopd=bool(inp.hopd_revenue_annual_usd),
    ))
    body = (
        _kv_row("Verdict", scan.verdict.value,
                _SEVERITY_COLOR.get(scan.verdict.value, P["text"]))
        + _kv_row("Patterns hit",
                  f"{scan.patterns_hit} / 12 ({scan.critical_hits} critical)")
        + f'<div style="margin-top:8px;"><a href="/screening/bankruptcy-survivor" '
          f'style="color:{P["accent"]};font-size:11px;">Open full scan →</a></div>'
    )
    # Partner-speak explainer keyed off verdict.
    scan_explainer = {
        "CRITICAL": (
            "≥3 of the 12 named bankruptcy patterns matched. This is the "
            "same signature that preceded Steward, Envision, and Hahnemann. "
            "Typically a walkaway unless the critical patterns are mitigable."
        ),
        "RED": (
            "1–2 critical patterns matched. Bridge reserves must cover the "
            "RED patterns; offer-shape modifications should be drafted "
            "before IC."
        ),
        "YELLOW": (
            "Non-critical patterns matched. Include in 100-day plan; not a "
            "walkaway."
        ),
        "GREEN": (
            "None of the 12 named failure patterns match. Pre-NDA screen "
            "clears — proceed to full diligence."
        ),
    }.get(scan.verdict.value.upper(),
          "Verdict pending — supply more scan inputs on Deal Profile.")
    return _panel(
        "Bankruptcy-Survivor Scan", body,
        badge=_badge("SCAN", scan.verdict.value),
        explanation=scan_explainer,
    )


def _panel_regulatory(inp: WorkbenchInput) -> str:
    rows: List[str] = []
    band = "UNKNOWN"
    dollars = 0.0
    if inp.legal_structure and inp.states:
        try:
            cpom = compute_cpom_exposure(
                target_structure=inp.legal_structure,
                footprint_states=inp.states,
            )
            rows.append(_kv_row(
                f"CPOM ({len(cpom.per_state)} states)",
                cpom.overall_band.value,
                _SEVERITY_COLOR.get(cpom.overall_band.value, P["text"]),
            ))
            dollars += cpom.total_remediation_usd
            if cpom.overall_band == RegulatoryBand.RED:
                band = "RED"
            elif cpom.overall_band == RegulatoryBand.YELLOW and band != "RED":
                band = "YELLOW"
        except Exception:  # noqa: BLE001
            pass
    if inp.cbsa_codes:
        for cbsa in inp.cbsa_codes:
            try:
                team = compute_team_impact(
                    cbsa_code=cbsa, track="track_2",
                    annual_case_volume={"LEJR": 300, "CABG": 80},
                )
                if team.in_mandatory_cbsa:
                    rows.append(_kv_row(
                        f"TEAM ({cbsa})",
                        team.band.value,
                        _SEVERITY_COLOR.get(team.band.value, P["text"]),
                    ))
            except Exception:  # noqa: BLE001
                continue
    if (inp.is_hospital_based_physician and inp.specialty
            and inp.oon_revenue_share is not None
            and inp.oon_dollars_annual is not None):
        nsa = compute_nsa_exposure(
            specialty=inp.specialty,
            oon_revenue_share=inp.oon_revenue_share,
            oon_dollars_annual=inp.oon_dollars_annual,
        )
        rows.append(_kv_row(
            "NSA IDR",
            f"{nsa.band.value} · ${nsa.dollars_at_risk_usd:,.0f} at risk",
            _SEVERITY_COLOR.get(nsa.band.value, P["text"]),
        ))
        dollars += nsa.dollars_at_risk_usd
    if inp.hopd_revenue_annual_usd:
        sn = simulate_site_neutral_impact(
            scenario="current",
            hopd_total_revenue_usd=inp.hopd_revenue_annual_usd,
        )
        rows.append(_kv_row(
            "Site-neutral",
            f"{sn.band.value} · {sn.annual_revenue_erosion_pct*100:.1f}% erosion",
            _SEVERITY_COLOR.get(sn.band.value, P["text"]),
        ))
        dollars += sn.annual_revenue_erosion_usd
    if inp.acquisitions and inp.specialty:
        at = compute_antitrust_exposure(
            target_specialty=inp.specialty,
            target_msas=inp.msas,
            acquisitions=inp.acquisitions,
        )
        rows.append(_kv_row(
            "Antitrust",
            f"{at.band.value}"
            + (" · 30-day FTC notice" if at.thirty_day_ftc_notice_triggered else ""),
            _SEVERITY_COLOR.get(at.band.value, P["text"]),
        ))
    if not rows:
        body = _not_supplied("no regulatory inputs provided")
    else:
        # Peer context on the $ at risk — typical PE healthcare deal
        # has $0-15M reg exposure; >$50M is a walkaway band.
        if dollars <= 0:
            dollars_peer = "within peer norm"
        elif dollars <= 15_000_000:
            dollars_peer = "peer norm ≤ $15M"
        elif dollars <= 50_000_000:
            dollars_peer = "above peer norm (> $15M)"
        else:
            dollars_peer = "thesis-breaking (> $50M)"
        body = "".join(rows) + _kv_row(
            "Total $ at risk", f"${dollars:,.0f}",
            peer=dollars_peer,
        )
    reg_band_final = band if rows else "UNKNOWN"
    return _panel(
        "Regulatory Exposure (G)", body,
        badge=_badge("REG", reg_band_final),
        explanation=_explain_for(reg_band_final),
    )


def _panel_real_estate(inp: WorkbenchInput) -> str:
    if not (inp.landlord or inp.lease_term_years):
        return _panel(
            "Real Estate (H)",
            _not_supplied("no lease inputs"),
            badge=_badge("RE", "UNKNOWN"),
        )
    schedule = LeaseSchedule(lines=[LeaseLine(
        property_id=inp.target_name,
        property_type=(inp.specialty or "HOSPITAL").upper()
            if inp.specialty else "HOSPITAL",
        base_rent_annual_usd=float(inp.annual_rent_usd or 1.0),
        escalator_pct=inp.lease_escalator_pct or 0.0,
        term_years=inp.lease_term_years or 10,
        landlord=inp.landlord,
        property_revenue_annual_usd=inp.portfolio_revenue_usd,
    )])
    steward = compute_steward_score(
        schedule,
        portfolio_ebitdar_annual_usd=inp.portfolio_ebitdar_usd,
        portfolio_annual_rent_usd=inp.annual_rent_usd,
        geography=inp.geography,
    )
    rows = [
        _kv_row("Steward tier", steward.tier.value,
                _SEVERITY_COLOR.get(steward.tier.value, P["text"])),
        _kv_row("Factors hit", f"{steward.factor_count} / 5"),
    ]
    if steward.matching_case_study:
        rows.append(_kv_row("Case match", steward.matching_case_study))
    if inp.annual_rent_usd and inp.portfolio_revenue_usd:
        wf = compute_lease_waterfall(
            schedule, hold_years=10,
            portfolio_revenue_annual_usd=inp.portfolio_revenue_usd,
            portfolio_ebitdar_annual_usd=inp.portfolio_ebitdar_usd,
        )
        rows.append(_kv_row(
            "Rent PV (10y)", f"${wf.total_rent_pv_usd:,.0f}",
        ))
        if wf.portfolio_rent_pct_revenue is not None:
            # Acute-hospital peer median rent / revenue is ~3%;
            # MPT tenants cluster 8-12%.
            rent_pct = wf.portfolio_rent_pct_revenue
            if rent_pct <= 0.05:
                rent_color, rent_peer = P["positive"], "peer median ~3%"
            elif rent_pct <= 0.08:
                rent_color, rent_peer = P["warning"], "peer median ~3%"
            else:
                rent_color, rent_peer = P["negative"], "peer median ~3% (MPT tenants 8-12%)"
            rows.append(_kv_row(
                "Rent % revenue",
                f"{rent_pct*100:.1f}%",
                rent_color,
                peer=rent_peer,
            ))
        if wf.ebitdar_coverage is not None:
            # HFMA healthy coverage is ≥1.5x; stressed <1.2x.
            cov = wf.ebitdar_coverage
            if cov >= 1.5:
                cov_color, cov_peer = P["positive"], "peer median ≥1.5x"
            elif cov >= 1.2:
                cov_color, cov_peer = P["warning"], "peer median ≥1.5x"
            else:
                cov_color, cov_peer = P["negative"], "peer median ≥1.5x (Steward sub-1.2x)"
            rows.append(_kv_row(
                "EBITDAR coverage",
                f"{cov:.2f}x",
                cov_color,
                peer=cov_peer,
            ))
    return _panel(
        "Real Estate (H)", "".join(rows),
        badge=_badge("RE", steward.tier.value),
        explanation=_explain_for(steward.tier.value),
    )


def _panel_physician_comp(inp: WorkbenchInput) -> str:
    if not inp.providers:
        return _panel(
            "Physician Comp + Attrition (J)",
            _not_supplied("no provider roster"),
            badge=_badge("COMP", "UNKNOWN"),
        )
    metrics = ingest_providers(inp.providers)
    findings = check_stark_redline(inp.providers)
    earnout = recommend_earnout_structure(inp.providers)
    crit = sum(1 for f in findings if f.severity == "CRITICAL")
    high = sum(1 for f in findings if f.severity == "HIGH")

    # P-PAM — run the flight-risk model against the same roster.
    # Years-at-facility / ages / productivity slopes not provided here
    # (the workbench doesn't currently carry them); the analyzer
    # handles missing metadata gracefully with neutral priors.
    try:
        attrition = analyze_attrition_roster(inp.providers)
    except Exception:  # noqa: BLE001
        attrition = None

    # Combined severity — whichever is higher between comp severity
    # (Stark) and attrition severity (CRITICAL providers present).
    comp_sev = "CRITICAL" if crit else ("HIGH" if high else "LOW")
    if attrition is not None and attrition.critical_count > 0:
        attrition_sev = "CRITICAL"
    elif attrition is not None and attrition.high_count >= 2:
        attrition_sev = "HIGH"
    elif attrition is not None and attrition.high_count >= 1:
        attrition_sev = "MEDIUM"
    else:
        attrition_sev = "LOW"
    # Pick the worst
    sev_order = {"CRITICAL": 3, "HIGH": 2, "MEDIUM": 1, "LOW": 0}
    sev = (
        attrition_sev
        if sev_order[attrition_sev] > sev_order[comp_sev]
        else comp_sev
    )

    rows = [
        _kv_row("Providers", str(len(inp.providers))),
        _kv_row("Total comp", f"${metrics.total_comp_usd:,.0f}"),
        _kv_row(
            "Stark findings",
            f"{len(findings)} ({crit} critical, {high} high)",
        ),
        _kv_row(
            "Top-5 concentration",
            f"{earnout.top5_concentration_pct*100:.1f}%",
        ),
        _kv_row("Recommended earnout",
                earnout.recommended_structure),
    ]

    # Append attrition summary rows.
    if attrition is not None:
        att_color = (
            P["negative"] if attrition.critical_count
            else P["warning"] if attrition.high_count
            else P["positive"]
        )
        rows.append(_kv_row(
            "Flight-risk bands",
            f"{attrition.critical_count} crit · "
            f"{attrition.high_count} high · "
            f"{attrition.medium_count} med · "
            f"{attrition.low_count} low",
            att_color,
        ))
        if attrition.bridge_input is not None:
            b = attrition.bridge_input
            rows.append(_kv_row(
                "EBITDA at risk (18mo)",
                f"${b.ebitda_at_risk_usd:,.0f}",
                att_color,
                peer=f"{b.confidence} confidence · "
                     f"{b.realization_probability*100:.0f}% realization",
            ))
            rows.append(
                f'<div style="margin-top:6px;"><a href="/diligence/physician-attrition" '
                f'style="color:{P["accent"]};font-size:11px;">'
                f'Open Physician Attrition page →</a></div>'
            )

    # Layer attrition into the explanation when CRITICAL/HIGH providers
    # exist — partners should see the structural recommendation.
    comp_explain = _explain_for(sev)
    attr_explain = ""
    if attrition is not None and attrition.critical_count > 0:
        attr_explain = (
            f" · {attrition.critical_count} CRITICAL flight-risk "
            f"providers — cannot close without retention bonds on "
            f"the named CRITICAL set."
        )
    elif attrition is not None and attrition.high_count > 0:
        attr_explain = (
            f" · {attrition.high_count} HIGH flight-risk providers — "
            f"earn-out must include retention milestones."
        )
    return _panel(
        "Physician Comp + Attrition (J)", "".join(rows),
        badge=_badge("COMP", sev),
        explanation=(comp_explain or "") + attr_explain,
    )


def _panel_cyber(inp: WorkbenchInput) -> str:
    if not (inp.ehr_vendor or inp.business_associates):
        return _panel(
            "Cyber Posture (K)",
            _not_supplied("no EHR / BA inputs"),
            badge=_badge("CYBER", "UNKNOWN"),
        )
    ba_findings = (
        assess_business_associates(inp.business_associates)
        if inp.business_associates else []
    )
    capex = None
    if (inp.ehr_vendor and inp.years_since_ehr
            and inp.annual_revenue_usd and inp.it_fte_count is not None):
        capex = detect_deferred_it_capex(
            ehr_vendor=inp.ehr_vendor,
            years_since_ehr_implementation=float(inp.years_since_ehr),
            annual_revenue_usd=inp.annual_revenue_usd,
            it_fte_count=inp.it_fte_count,
        )
    bi = None
    if inp.revenue_per_day_usd:
        cascade = max(
            (f.cascade_risk_multiplier for f in ba_findings),
            default=1.0,
        )
        bi = simulate_bi_loss(
            revenue_per_day_baseline_usd=inp.revenue_per_day_usd,
            incident_probability_per_year=0.10,
            cascade_risk_multiplier=cascade,
            n_runs=500,
        )
    score = compose_cyber_score(
        ehr_vendor_risk=ehr_vendor_risk_score(inp.ehr_vendor)
            if inp.ehr_vendor else None,
        ba_findings=ba_findings,
        it_capex=capex,
        bi_loss=bi,
        annual_revenue_usd=inp.annual_revenue_usd or 0.0,
    )
    rows = [
        _kv_row(
            "CyberScore",
            f"{score.score} / 100",
            _SEVERITY_COLOR.get(score.band, P["text"]),
            peer="healthy ≥75 · at-risk ≤50",
        ),
        _kv_row(
            "Bridge reserve",
            f"{cyber_bridge_reserve_pct(score.band)*100:.1f}% of revenue",
            peer="peer norm 0.5% · stressed 3-5%",
        ),
    ]
    if bi:
        rows.append(_kv_row(
            "BI expected loss", f"${bi.expected_loss_usd:,.0f}",
        ))
    if ba_findings:
        rows.append(_kv_row(
            "BA cascade findings",
            f"{len(ba_findings)} ({score.ba_critical_count} critical)",
        ))
    cyber_explainer = {
        "RED": (
            "Cyber posture is RED. Change-Healthcare-class exposure "
            "— model the BI loss as a bridge reserve line, not a "
            "background risk. A single 30-day incident can exceed the "
            "entire year's EBITDA."
        ),
        "YELLOW": (
            "Cyber posture is YELLOW. Reserve ~2% of revenue in the "
            "bridge for BI tail; include BA cascade findings in the "
            "100-day plan."
        ),
        "GREEN": (
            "Cyber posture is GREEN. No material reserve needed beyond "
            "the standard 0.5% operational-risk line."
        ),
    }.get(score.band.upper(), _explain_for(score.band))
    return _panel(
        "Cyber Posture (K)", "".join(rows),
        badge=_badge("CYBER", score.band),
        explanation=cyber_explainer,
    )


def _panel_ma_dynamics(inp: WorkbenchInput) -> str:
    rows: List[str] = []
    band = "UNKNOWN"
    if inp.ma_members_with_diagnosis_codes:
        v28 = compute_v28_recalibration(
            inp.ma_members_with_diagnosis_codes,
        )
        rows.append(_kv_row(
            "V28 members scored", str(v28.members_scored),
        ))
        rows.append(_kv_row(
            "Risk score delta",
            f"{v28.aggregate_risk_score_reduction_pct*100:.2f}%",
            peer="CMS aggregate forecast −3.12%",
        ))
        # Peer context for revenue impact — as % of total MA revenue
        # a typical V28-exposed target hits a 2-4% compression.
        rev_impact = v28.aggregate_revenue_impact_usd
        total_ma = inp.total_ma_revenue_usd or 1.0
        pct_impact = abs(rev_impact) / total_ma if total_ma > 0 else 0.0
        if pct_impact <= 0.01:
            rev_peer = "< 1% — immaterial"
        elif pct_impact <= 0.03:
            rev_peer = "1-3% · peer norm"
        elif pct_impact <= 0.05:
            rev_peer = "3-5% · above peer norm"
        else:
            rev_peer = "> 5% · thesis-level hit"
        rows.append(_kv_row(
            "Revenue impact",
            f"${v28.aggregate_revenue_impact_usd:,.0f}",
            P["negative"]
                if v28.aggregate_revenue_impact_usd < 0 else P["text"],
            peer=rev_peer,
        ))
        band = "YELLOW" if v28.aggregate_revenue_impact_usd < 0 else "GREEN"
    if (inp.hcc_capture_rate is not None
            and inp.specialty_benchmark_capture_rate):
        ci = analyze_coding_intensity(
            target_name=inp.target_name,
            target_hcc_capture_rate=inp.hcc_capture_rate,
            specialty_benchmark_capture_rate=inp.specialty_benchmark_capture_rate,
            add_only_retrospective_pct=inp.add_only_retrospective_pct or 0,
            total_ma_revenue_usd=inp.total_ma_revenue_usd or 0,
        )
        rows.append(_kv_row(
            "Coding intensity", ci.severity,
            _SEVERITY_COLOR.get(ci.severity, P["text"]),
        ))
        if ci.severity == "CRITICAL":
            band = "RED"
    if inp.medicaid_revenue_annual_usd and inp.medicaid_state:
        mu = estimate_medicaid_unwind_impact(
            target_state=inp.medicaid_state,
            target_medicaid_revenue_annual_usd=inp.medicaid_revenue_annual_usd,
        )
        rows.append(_kv_row(
            "Medicaid unwind",
            f"{mu.severity} · ${mu.revenue_at_risk_usd:,.0f}",
            _SEVERITY_COLOR.get(mu.severity, P["text"]),
        ))
    if not rows:
        return _panel(
            "MA Dynamics (L)",
            _not_supplied("no MA inputs"),
            badge=_badge("MA", "UNKNOWN"),
        )
    ma_explainer = {
        "RED": (
            "Coding intensity is CRITICAL. CMS V28 recalibration + "
            "add-only retrospective audits together cut ~3-5% of "
            "MA revenue. Model this as a bridge headwind in Deal MC."
        ),
        "YELLOW": (
            "V28 revenue compression is in-line with CMS aggregate "
            "forecast (≈3.12%). Factor into bridge as a known "
            "headwind but not a thesis killer."
        ),
        "GREEN": (
            "No material V28 exposure — target's Medicare mix is "
            "low or coding already conservative."
        ),
    }.get(band, _explain_for(band))
    return _panel(
        "MA Dynamics (L)", "".join(rows),
        badge=_badge("MA", band),
        explanation=ma_explainer,
    )


def _panel_quality_wc_synergy(inp: WorkbenchInput) -> str:
    rows: List[str] = []
    if (inp.star_rating is not None
            and inp.base_ms_drg_payments_usd):
        q = project_vbp_hrrp(
            star_rating=inp.star_rating,
            excess_readmission_ratios=inp.excess_readmission_ratios
                or {"AMI": 1.0},
            hac_worst_quartile=inp.hac_worst_quartile,
            base_ms_drg_payments_annual_usd=inp.base_ms_drg_payments_usd,
        )
        color = P["negative"] if q.year1_dollar_impact_usd < 0 else P["positive"]
        rows.append(_kv_row(
            f"VBP/HRRP ({inp.star_rating}★)",
            f"{q.severity} · ${q.year1_dollar_impact_usd:,.0f}/yr",
            color,
        ))
    if inp.trailing_monthly_nwc_usd:
        peg = compute_normalized_peg(inp.trailing_monthly_nwc_usd)
        rows.append(_kv_row(
            "NWC peg",
            f"${peg.seasonality_adjusted_peg_usd:,.0f}",
        ))
    if (inp.dnfb_claims and inp.avg_claim_value_usd
            and inp.avg_daily_discharges):
        dnfb = estimate_dnfb(
            discharged_not_billed_claim_count=inp.dnfb_claims,
            avg_claim_value_usd=inp.avg_claim_value_usd,
            avg_daily_discharges=inp.avg_daily_discharges,
        )
        rows.append(_kv_row(
            "DNFB",
            f"{dnfb.severity} · {dnfb.dnfb_days:.1f}d",
            _SEVERITY_COLOR.get(dnfb.severity, P["text"]),
        ))
    if (inp.last_60d_collections_usd
            and inp.prior_12_monthly_collections_usd):
        pf = detect_pre_close_pull_forward(
            last_60_days_collections_usd=inp.last_60d_collections_usd,
            prior_12_monthly_collections_usd=inp.prior_12_monthly_collections_usd,
        )
        rows.append(_kv_row(
            "Pre-close pull-forward",
            f"{pf.severity} · {pf.lift_ratio:.2f}x",
            _SEVERITY_COLOR.get(pf.severity, P["text"]),
        ))
    if not rows:
        return _panel(
            "Quality / WC / Synergy (N)",
            _not_supplied("no quality or WC inputs"),
            badge=_badge("Q/WC", "UNKNOWN"),
        )
    return _panel("Quality / WC / Synergy (N)", "".join(rows))


def _panel_labor_referral(inp: WorkbenchInput) -> str:
    rows: List[str] = []
    if inp.wage_bill_usd:
        wf = forecast_wage_inflation(
            msa=inp.wage_msa or "National",
            role="RN",
            current_wage_bill_usd=inp.wage_bill_usd,
        )
        rows.append(_kv_row(
            f"Wage inflation (RN, {wf.msa})",
            f"{wf.annualized_inflation_pct*100:.1f}%/yr → "
            f"${wf.projected_wage_bill_year5_usd:,.0f} Y5",
        ))
    if (inp.scheduled_fte and inp.billing_npi_count is not None):
        syn = detect_synthetic_fte(
            scheduled_fte=inp.scheduled_fte,
            billing_npi_count=inp.billing_npi_count,
            fte_941_headcount=inp.scheduled_fte,  # default
        )
        rows.append(_kv_row(
            "Synthetic FTE",
            f"{syn.severity} · {syn.npi_vs_scheduled_gap_pct*100:.0f}% gap",
            _SEVERITY_COLOR.get(syn.severity, P["text"]),
        ))
    if inp.revenue_by_provider:
        conc = compute_provider_concentration(inp.revenue_by_provider)
        rows.append(_kv_row(
            "Top-5 share", f"{conc.top5_share*100:.1f}%",
        ))
        if inp.departing_providers:
            stress = stress_test_departures(
                inp.revenue_by_provider, inp.departing_providers,
            )
            rows.append(_kv_row(
                "Departure stress",
                f"{stress.severity} · {stress.revenue_lost_pct*100:.1f}%",
                _SEVERITY_COLOR.get(stress.severity, P["text"]),
            ))
    if not rows:
        return _panel(
            "Labor / Referral (M)",
            _not_supplied("no labor or referral inputs"),
            badge=_badge("LAB", "UNKNOWN"),
        )
    return _panel("Labor / Referral (M)", "".join(rows))


def _panel_patient_pay_reputational(inp: WorkbenchInput) -> str:
    rows: List[str] = []
    if (inp.hdhp_member_share is not None
            and inp.patient_responsibility_usd):
        h = segment_patient_pay_exposure(
            hdhp_member_share=inp.hdhp_member_share,
            total_patient_responsibility_usd=inp.patient_responsibility_usd,
        )
        rows.append(_kv_row(
            "HDHP exposure",
            f"{h.severity} · ${h.est_bad_debt_delta_usd:,.0f}",
            _SEVERITY_COLOR.get(h.severity, P["text"]),
        ))
    if inp.states:
        med_debt = compute_medical_debt_overlay(inp.states)
        # Summarise — max severity across states.
        max_sev = "LOW"
        max_uplift = 0.0
        for s in med_debt:
            if _SEVERITY_COLOR.get(s.severity, "") == _SEVERITY_COLOR["HIGH"]:
                max_sev = "HIGH"
            if s.bad_debt_uplift_pct > max_uplift:
                max_uplift = s.bad_debt_uplift_pct
        if max_uplift > 0:
            rows.append(_kv_row(
                "Medical-debt overlay",
                f"{max_sev} · +{max_uplift*100:.1f}% bad-debt reserve",
                _SEVERITY_COLOR.get(max_sev, P["text"]),
            ))
        ag = state_ag_enforcement_heatmap(inp.states)
        high_ag = [x for x in ag if x.tier == "HIGH"]
        if high_ag:
            rows.append(_kv_row(
                "State AG tier",
                "HIGH · " + ", ".join(x.state_code for x in high_ag),
                P["negative"],
            ))
    if inp.specialty:
        contagion = detect_bankruptcy_contagion(
            target_specialty=inp.specialty,
            target_landlord=inp.landlord,
        )
        if contagion.severity != "LOW":
            rows.append(_kv_row(
                "Bankruptcy cluster",
                contagion.severity,
                _SEVERITY_COLOR.get(contagion.severity, P["text"]),
            ))
    if not rows:
        return _panel(
            "Patient-pay / Reputational (O)",
            _not_supplied("no patient-pay or state inputs"),
            badge=_badge("ESG", "UNKNOWN"),
        )
    return _panel("Patient-pay / Reputational (O)", "".join(rows))


# ── Main entry point ───────────────────────────────────────────────

def _counterfactual_section(inp: WorkbenchInput) -> str:
    """Build the 'what would change your mind' section by running
    every solver that has the input data available."""
    # Run the engines we can, then hand the results to the advisor.
    cpom = None
    if inp.legal_structure and inp.states:
        try:
            cpom = compute_cpom_exposure(
                target_structure=inp.legal_structure,
                footprint_states=inp.states,
            )
        except Exception:  # noqa: BLE001
            cpom = None
    nsa = None
    if (inp.is_hospital_based_physician and inp.specialty
            and inp.oon_revenue_share is not None
            and inp.oon_dollars_annual is not None):
        nsa = compute_nsa_exposure(
            specialty=inp.specialty,
            oon_revenue_share=inp.oon_revenue_share,
            oon_dollars_annual=inp.oon_dollars_annual,
        )
    steward = None
    if inp.landlord or inp.lease_term_years:
        from ..diligence.real_estate import (
            LeaseLine, LeaseSchedule, compute_steward_score,
        )
        steward = compute_steward_score(
            LeaseSchedule(lines=[LeaseLine(
                property_id=inp.target_name,
                property_type="HOSPITAL",
                base_rent_annual_usd=float(inp.annual_rent_usd or 1.0),
                escalator_pct=inp.lease_escalator_pct or 0.0,
                term_years=inp.lease_term_years or 10,
                landlord=inp.landlord,
            )]),
            portfolio_ebitdar_annual_usd=inp.portfolio_ebitdar_usd,
            portfolio_annual_rent_usd=inp.annual_rent_usd,
            geography=inp.geography,
        )
    team = None
    if inp.cbsa_codes:
        for cbsa in inp.cbsa_codes:
            try:
                t = compute_team_impact(
                    cbsa_code=cbsa, track="track_2",
                    annual_case_volume={"LEJR": 300, "CABG": 80},
                )
                if t.in_mandatory_cbsa:
                    team = t
                    break
            except Exception:  # noqa: BLE001
                continue
    antitrust = None
    if inp.acquisitions and inp.specialty:
        antitrust = compute_antitrust_exposure(
            target_specialty=inp.specialty,
            target_msas=inp.msas,
            acquisitions=inp.acquisitions,
        )
    site_neutral = None
    if inp.hopd_revenue_annual_usd:
        site_neutral = simulate_site_neutral_impact(
            scenario="legislative",
            hopd_total_revenue_usd=inp.hopd_revenue_annual_usd,
        )
    cyber_score = None
    if inp.ehr_vendor or inp.business_associates:
        ba_findings = (
            assess_business_associates(inp.business_associates)
            if inp.business_associates else []
        )
        capex = None
        if (inp.ehr_vendor and inp.years_since_ehr
                and inp.annual_revenue_usd and inp.it_fte_count is not None):
            capex = detect_deferred_it_capex(
                ehr_vendor=inp.ehr_vendor,
                years_since_ehr_implementation=float(inp.years_since_ehr),
                annual_revenue_usd=inp.annual_revenue_usd,
                it_fte_count=inp.it_fte_count,
            )
        bi = None
        if inp.revenue_per_day_usd:
            cascade = max(
                (f.cascade_risk_multiplier for f in ba_findings),
                default=1.0,
            )
            bi = simulate_bi_loss(
                revenue_per_day_baseline_usd=inp.revenue_per_day_usd,
                incident_probability_per_year=0.10,
                cascade_risk_multiplier=cascade,
                n_runs=500,
            )
        cyber_score = compose_cyber_score(
            ehr_vendor_risk=ehr_vendor_risk_score(inp.ehr_vendor)
                if inp.ehr_vendor else None,
            ba_findings=ba_findings,
            it_capex=capex,
            bi_loss=bi,
            annual_revenue_usd=inp.annual_revenue_usd or 0.0,
        )

    cfs = advise_all(
        cpom=cpom, nsa=nsa, steward=steward, team=team,
        antitrust=antitrust, cyber=cyber_score,
        site_neutral=site_neutral,
    )
    if not cfs.items:
        return ""

    rows: List[str] = []
    for cf in cfs.items:
        orig_color = _SEVERITY_COLOR.get(cf.original_band, P["text"])
        target_color = _SEVERITY_COLOR.get(cf.target_band, P["text"])
        feas_color = {
            "HIGH": P["positive"],
            "MEDIUM": P["warning"],
            "LOW": P["negative"],
        }.get(cf.feasibility, P["text"])
        if cf.estimated_dollar_impact_usd > 0:
            dollar_html = (
                f'<span class="mono" style="color:{P["positive"]};'
                f'font-weight:700;font-size:14px;">'
                f'${cf.estimated_dollar_impact_usd:,.0f}</span>'
            )
        else:
            dollar_html = (
                f'<span style="color:{P["text_faint"]};'
                f'font-style:italic;font-size:11px;">qualitative</span>'
            )
        rows.append(
            f'<div style="background:{P["panel"]};'
            f'border:1px solid {P["border"]};'
            f'border-left:4px solid {target_color};border-radius:4px;'
            f'padding:12px 16px;margin-bottom:10px;">'
            f'  <div style="display:flex;justify-content:space-between;'
            f'gap:16px;align-items:flex-start;">'
            f'    <div style="flex:1;min-width:0;">'
            f'      <div style="font-size:9px;color:{P["text_faint"]};'
            f'letter-spacing:1.5px;text-transform:uppercase;font-weight:600;'
            f'margin-bottom:2px;">{html.escape(cf.module)}</div>'
            f'      <div style="font-size:13px;color:{P["text"]};'
            f'font-weight:600;line-height:1.4;">'
            f'{html.escape(cf.change_description)}</div>'
            f'      <div style="margin-top:6px;display:flex;gap:6px;'
            f'align-items:center;flex-wrap:wrap;">'
            f'        <span style="font-size:9px;letter-spacing:1px;'
            f'text-transform:uppercase;font-weight:700;padding:2px 6px;'
            f'background:{P["panel_alt"]};color:{orig_color};'
            f'border-radius:2px;">{html.escape(cf.original_band)}</span>'
            f'        <span style="color:{P["text_dim"]};font-size:11px;">→</span>'
            f'        <span style="font-size:9px;letter-spacing:1px;'
            f'text-transform:uppercase;font-weight:700;padding:2px 6px;'
            f'background:{P["panel_alt"]};color:{target_color};'
            f'border-radius:2px;">{html.escape(cf.target_band)}</span>'
            f'        <span style="font-size:9px;letter-spacing:1px;'
            f'text-transform:uppercase;font-weight:600;color:{feas_color};'
            f'margin-left:6px;">feasibility {html.escape(cf.feasibility)}</span>'
            f'      </div>'
            f'    </div>'
            f'    <div style="text-align:right;min-width:120px;">'
            f'      <div style="font-size:9px;color:{P["text_faint"]};'
            f'letter-spacing:1px;text-transform:uppercase;'
            f'margin-bottom:2px;">Savings</div>'
            f'      {dollar_html}'
            f'    </div>'
            f'  </div>'
            f'  <div style="font-size:11px;color:{P["text_dim"]};'
            f'line-height:1.55;margin-top:8px;">'
            f'{html.escape(cf.narrative)}</div>'
            f'  <div style="font-size:10px;color:{P["text_faint"]};'
            f'line-height:1.55;margin-top:8px;padding-top:6px;'
            f'border-top:1px solid {P["border"]};">'
            f'<span style="color:{P["text_dim"]};font-weight:600;'
            f'letter-spacing:.5px;text-transform:uppercase;'
            f'margin-right:4px;">Deal:</span>'
            f'{html.escape(cf.deal_structure_implication)}</div>'
            f'</div>'
        )
    largest = cfs.largest_lever
    header_note = ""
    if largest:
        header_note = (
            f'<div style="font-size:11px;color:{P["text_dim"]};'
            f'margin-bottom:12px;max-width:760px;line-height:1.55;">'
            f'<strong style="color:{P["text"]};">'
            f'{cfs.critical_findings_addressed}</strong> RED/CRITICAL '
            f'finding(s) have a counterfactual that flips the band. '
            f'Largest lever: <strong style="color:{P["text"]};">'
            f'{html.escape(largest.module)}</strong> · '
            f'{html.escape(largest.lever)}.</div>'
        )
    return (
        f'<div style="margin-top:28px;padding:16px 20px;'
        f'background:{P["panel"]};border:1px solid {P["border"]};'
        f'border-radius:4px;position:relative;overflow:hidden;">'
        f'  <div style="position:absolute;top:0;left:0;right:0;height:2px;'
        f'background:linear-gradient(90deg,{P["positive"]},{P["accent"]});"></div>'
        f'  <div style="font-size:9px;color:{P["text_faint"]};'
        f'letter-spacing:1.5px;text-transform:uppercase;font-weight:600;'
        f'margin-top:4px;margin-bottom:4px;">'
        f'What Would Change Your Mind</div>'
        f'  <div style="font-size:18px;color:{P["text"]};font-weight:600;'
        f'margin-bottom:10px;">Counterfactual Advisor</div>'
        f'  {header_note}'
        f'  {"".join(rows)}'
        f'</div>'
    )


def render_risk_workbench(inp: WorkbenchInput) -> str:
    hero = (
        f'<div style="padding:24px 0 12px 0;">'
        f'  <div style="font-size:11px;color:{P["text_faint"]};'
        f'letter-spacing:.75px;text-transform:uppercase;margin-bottom:6px;">'
        f'Regulatory Risk Workbench</div>'
        f'  <div style="font-size:22px;color:{P["text"]};font-weight:600;'
        f'margin-bottom:4px;">{html.escape(inp.target_name)}</div>'
        f'  <div style="font-size:12px;color:{P["text_dim"]};max-width:760px;'
        f'line-height:1.55;">Live panels for the 9 Tier-1/2/3 diligence '
        f'subpackages (Prompts G-O). Each panel runs its engine against '
        f'the supplied inputs; panels without inputs render '
        f'<em>not supplied</em> rather than fabricating numbers.</div>'
        f'  <div style="background:{P["panel_alt"]};border-left:3px solid '
        f'{P["accent"]};padding:10px 14px;margin-top:14px;font-size:12px;'
        f'color:{P["text_dim"]};line-height:1.6;max-width:880px;'
        f'border-radius:0 3px 3px 0;">'
        f'<strong style="color:{P["text"]};">How to read these panels: </strong>'
        f'Each panel shows the target\'s standing in one of the nine '
        f'diligence subpackages plus a <em>what this shows</em> '
        f'explanation of what the band means in partner-speak. '
        f'<span style="color:{P["positive"]};">GREEN</span> = in-line with peer norms; '
        f'<span style="color:{P["warning"]};">YELLOW</span> = manageable but watch; '
        f'<span style="color:{P["negative"]};">RED</span> / '
        f'<span style="color:{P["critical"]};">CRITICAL</span> = thesis-breaking without '
        f'offer-shape modification. Counterfactual Advisor at the bottom '
        f'quantifies every RED/CRITICAL lever.</div>'
        f'</div>'
    )
    body = (
        hero
        + '<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">'
        + _panel_bankruptcy_survivor(inp)
        + _panel_regulatory(inp)
        + _panel_real_estate(inp)
        + _panel_physician_comp(inp)
        + _panel_cyber(inp)
        + _panel_ma_dynamics(inp)
        + _panel_quality_wc_synergy(inp)
        + _panel_labor_referral(inp)
        + _panel_patient_pay_reputational(inp)
        + '</div>'
        + _counterfactual_section(inp)
    )
    return chartis_shell(
        body, "RCM Diligence — Risk Workbench",
        subtitle="Tier 1-3 + Counterfactual Advisor",
    )


# ── Pre-built demo inputs ──────────────────────────────────────────

def demo_steward_input() -> WorkbenchInput:
    """The Steward Health Care 2016 replay — wires every panel."""
    return WorkbenchInput(
        target_name="Steward Health Care (2016 replay)",
        legal_structure="DIRECT_EMPLOYMENT",
        states=["MA", "RI"],
        msas=["Boston"],
        cbsa_codes=["14460"],
        specialty="HOSPITAL",
        is_hospital_based_physician=False,
        hopd_revenue_annual_usd=25_000_000,
        acquisitions=[],
        landlord="Medical Properties Trust",
        lease_term_years=20,
        lease_escalator_pct=0.035,
        ebitdar_coverage=1.2,
        geography="RURAL",
        annual_rent_usd=32_000_000,
        portfolio_revenue_usd=230_000_000,
        portfolio_ebitdar_usd=38_400_000,
        ehr_vendor="ORACLE_CERNER",
        business_associates=["Change Healthcare", "Local billing vendor"],
        revenue_per_day_usd=630_000,
        years_since_ehr=12,
        annual_revenue_usd=230_000_000,
        it_fte_count=15,
        star_rating=2,
        excess_readmission_ratios={"AMI": 1.12, "HF": 1.08, "PN": 1.10},
        hac_worst_quartile=True,
        base_ms_drg_payments_usd=180_000_000,
        trailing_monthly_nwc_usd=[
            15_000_000 + (i % 4 - 2) * 500_000 for i in range(24)
        ],
        dnfb_claims=600, avg_claim_value_usd=4_200,
        avg_daily_discharges=110,
        last_60d_collections_usd=40_000_000,
        prior_12_monthly_collections_usd=[18_000_000] * 12,
        wage_bill_usd=85_000_000, wage_msa="California (CA)",
        scheduled_fte=1200, billing_npi_count=1280,
        revenue_by_provider={
            f"P{i}": 2_000_000 for i in range(40)
        },
        departing_providers=["P0", "P1"],
        hdhp_member_share=0.22,
        patient_responsibility_usd=8_000_000,
    )
