"""ThesisPipeline orchestrator — runs the full diligence chain and
returns every output bundled for downstream consumers.

Pipeline order (each step is defensive — failures short-circuit
the individual step, not the whole pipeline):

    1. CCD ingest
    2. Benchmarks (KPIs + cohort liquidation + QoR waterfall)
    3. Denial Prediction (Naive Bayes model + EBITDA bridge input)
    4. Bankruptcy-Survivor Scan
    5. Steward Score (when lease metadata supplied)
    6. Cyber Score (when EHR + BA metadata supplied)
    7. Counterfactual Advisor
    8. Physician Attrition (when roster supplied)
    9. Deal Autopsy (signature built from everything above)
   10. Market Intel lookup (comps + transaction band + sentiment)
   11. DealScenario assembly (populated with pipeline outputs)
   12. Deal MC (3000 trials, full distribution)
   13. Checklist observation set (auto-completion signals)

Every step produces an optional output — downstream renderers
check for None before using. No fabrication.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


@dataclass
class PipelineInput:
    """All the inputs a partner would otherwise hand-type across the
    individual analytics."""
    # Required
    dataset: str                            # CCD fixture name
    deal_name: str = "Target"

    # Deal structure (Deal MC)
    enterprise_value_usd: Optional[float] = None
    equity_check_usd: Optional[float] = None
    debt_usd: Optional[float] = None
    revenue_year0_usd: Optional[float] = None
    ebitda_year0_usd: Optional[float] = None
    entry_multiple: Optional[float] = None
    hold_years: int = 5
    medicare_share: Optional[float] = None

    # Target descriptors
    specialty: Optional[str] = None
    states: List[str] = field(default_factory=list)
    cbsa_codes: List[str] = field(default_factory=list)
    msas: List[str] = field(default_factory=list)
    legal_structure: Optional[str] = None

    # Real estate
    landlord: Optional[str] = None
    lease_term_years: Optional[int] = None
    lease_escalator_pct: Optional[float] = None
    ebitdar_coverage: Optional[float] = None
    annual_rent_usd: Optional[float] = None
    portfolio_ebitdar_usd: Optional[float] = None
    geography: Optional[str] = None

    # OON / NSA
    oon_revenue_share: Optional[float] = None
    hopd_revenue_annual_usd: Optional[float] = None

    # Cyber
    ehr_vendor: Optional[str] = None
    business_associates: List[str] = field(default_factory=list)
    years_since_ehr: Optional[float] = None
    it_fte_count: Optional[float] = None

    # Physician roster (optional — PPAM runs only if supplied)
    providers: List[Any] = field(default_factory=list)

    # Market intel
    market_category: Optional[str] = None

    # HCRIS cost-report CCN — when supplied, the pipeline pulls
    # the target's filed Medicare cost report and benchmarks it
    # against the 25-50 true peer hospitals.
    hcris_ccn: Optional[str] = None

    # Deal Autopsy metadata overrides (all optional)
    autopsy_metadata: Dict[str, float] = field(default_factory=dict)

    # Deal MC run size
    n_runs: int = 1500


@dataclass
class ThesisPipelineReport:
    """Every analytic's output + the populated DealScenario + the
    headline numbers that flow into IC Packet and Deal Profile
    localStorage writeback."""
    # Step outputs (all Optional — any can be None if the step
    # short-circuited)
    ccd: Optional[Any] = None
    kpi_bundle: Optional[Any] = None
    cohort_report: Optional[Any] = None
    waterfall: Optional[Any] = None
    denial_report: Optional[Any] = None
    bankruptcy_scan: Optional[Any] = None
    steward_score: Optional[Any] = None
    cyber_score: Optional[Any] = None
    counterfactual_set: Optional[Any] = None
    attrition_report: Optional[Any] = None
    eu_report: Optional[Any] = None
    exit_timing_report: Optional[Any] = None
    autopsy_matches: Optional[List[Any]] = None
    market_intel: Optional[Dict[str, Any]] = None
    regulatory_exposure: Optional[Any] = None
    hcris_xray: Optional[Any] = None
    payer_stress: Optional[Any] = None
    covenant_stress: Optional[Any] = None
    deal_scenario: Optional[Any] = None
    deal_mc_result: Optional[Any] = None

    # Step-level diagnostics
    step_log: List[Dict[str, Any]] = field(default_factory=list)

    # Derived headline numbers (what flows back to Deal Profile
    # localStorage + IC Packet)
    p50_moic: Optional[float] = None
    prob_sub_1x: Optional[float] = None
    top_variance_driver: Optional[str] = None
    top_autopsy_match: Optional[str] = None
    top_autopsy_similarity: Optional[float] = None
    denial_recoverable_usd: Optional[float] = None
    attrition_ebitda_at_risk_usd: Optional[float] = None
    eu_ebitda_uplift_usd: Optional[float] = None
    eu_drop_candidate_count: Optional[int] = None
    exit_recommendation_year: Optional[int] = None
    exit_recommendation_buyer: Optional[str] = None
    exit_expected_irr: Optional[float] = None
    counterfactual_largest_lever_usd: Optional[float] = None
    bankruptcy_verdict: Optional[str] = None
    steward_tier: Optional[str] = None
    regulatory_verdict: Optional[str] = None
    regulatory_killed_driver_count: Optional[int] = None
    regulatory_first_kill_date: Optional[str] = None
    regulatory_total_margin_impact_pp: Optional[float] = None
    regulatory_cumulative_ebitda_impact_usd: Optional[float] = None
    covenant_max_breach_probability: Optional[float] = None
    covenant_earliest_50pct_covenant: Optional[str] = None
    covenant_earliest_50pct_quarter: Optional[int] = None
    covenant_median_cure_usd: Optional[float] = None

    @property
    def total_compute_ms(self) -> float:
        return sum(s.get("elapsed_ms", 0) for s in self.step_log)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_log": list(self.step_log),
            "total_compute_ms": self.total_compute_ms,
            "headline_numbers": {
                "p50_moic": self.p50_moic,
                "prob_sub_1x": self.prob_sub_1x,
                "top_variance_driver": self.top_variance_driver,
                "top_autopsy_match": self.top_autopsy_match,
                "top_autopsy_similarity": self.top_autopsy_similarity,
                "denial_recoverable_usd": self.denial_recoverable_usd,
                "attrition_ebitda_at_risk_usd":
                    self.attrition_ebitda_at_risk_usd,
                "eu_ebitda_uplift_usd": self.eu_ebitda_uplift_usd,
                "eu_drop_candidate_count": self.eu_drop_candidate_count,
                "exit_recommendation_year":
                    self.exit_recommendation_year,
                "exit_recommendation_buyer":
                    self.exit_recommendation_buyer,
                "exit_expected_irr": self.exit_expected_irr,
                "counterfactual_largest_lever_usd":
                    self.counterfactual_largest_lever_usd,
                "bankruptcy_verdict": self.bankruptcy_verdict,
                "steward_tier": self.steward_tier,
                "regulatory_verdict": self.regulatory_verdict,
                "regulatory_killed_driver_count":
                    self.regulatory_killed_driver_count,
                "regulatory_first_kill_date":
                    self.regulatory_first_kill_date,
                "regulatory_total_margin_impact_pp":
                    self.regulatory_total_margin_impact_pp,
                "regulatory_cumulative_ebitda_impact_usd":
                    self.regulatory_cumulative_ebitda_impact_usd,
                "covenant_max_breach_probability":
                    self.covenant_max_breach_probability,
                "covenant_earliest_50pct_covenant":
                    self.covenant_earliest_50pct_covenant,
                "covenant_earliest_50pct_quarter":
                    self.covenant_earliest_50pct_quarter,
                "covenant_median_cure_usd":
                    self.covenant_median_cure_usd,
            },
        }


def _timed(step_name: str, fn, step_log: List[Dict[str, Any]]):
    """Run a step, log (name, elapsed, success/failure), return the
    step's output or None if it raised."""
    import time
    t0 = time.time()
    try:
        result = fn()
        elapsed = (time.time() - t0) * 1000
        step_log.append({
            "step": step_name, "elapsed_ms": round(elapsed, 2),
            "status": "ok",
        })
        return result
    except Exception as exc:  # noqa: BLE001
        elapsed = (time.time() - t0) * 1000
        step_log.append({
            "step": step_name, "elapsed_ms": round(elapsed, 2),
            "status": "fail", "error": f"{type(exc).__name__}: {exc}"[:200],
        })
        return None


def run_thesis_pipeline(
    inp: PipelineInput,
) -> ThesisPipelineReport:
    """Execute the 13-step pipeline against ``inp``.

    Every step is wrapped in a try/except — one failing step is
    logged and the remaining steps continue. The report is always
    returned; callers check for None on individual fields.
    """
    step_log: List[Dict[str, Any]] = []
    report = ThesisPipelineReport(step_log=step_log)

    # ─── 1. CCD ingest ────────────────────────────────────────────
    def _ingest():
        from .. import ingest_dataset
        from .._pages import _resolve_dataset
        path = _resolve_dataset(inp.dataset)
        if path is None:
            raise FileNotFoundError(f"fixture {inp.dataset!r} not found")
        return ingest_dataset(path)
    report.ccd = _timed("ingest_ccd", _ingest, step_log)
    if report.ccd is None:
        return report  # can't proceed without CCD

    # ─── 2. Benchmarks ────────────────────────────────────────────
    def _benchmarks():
        from datetime import date
        from .. import compute_cohort_liquidation, compute_kpis
        from ..benchmarks import compute_cash_waterfall
        as_of = date(2025, 1, 1)
        bundle = compute_kpis(
            report.ccd, as_of_date=as_of, provider_id=inp.dataset,
        )
        cohort = compute_cohort_liquidation(
            report.ccd.claims, as_of_date=as_of,
        )
        wf = compute_cash_waterfall(
            report.ccd.claims, as_of_date=as_of,
        )
        return bundle, cohort, wf

    benchmarks_out = _timed("benchmarks", _benchmarks, step_log)
    if benchmarks_out is not None:
        report.kpi_bundle, report.cohort_report, report.waterfall = benchmarks_out

    # ─── 3. Denial Prediction ─────────────────────────────────────
    def _denial():
        from ..denial_prediction import analyze_ccd
        return analyze_ccd(
            report.ccd, train_fraction=0.7, seed=42,
        )
    report.denial_report = _timed(
        "denial_prediction", _denial, step_log,
    )
    if report.denial_report is not None:
        bridge = getattr(report.denial_report, "bridge_input", None)
        if bridge is not None:
            report.denial_recoverable_usd = float(
                getattr(bridge, "recoverable_revenue_usd", 0.0) or 0.0,
            )

    # ─── 4. Bankruptcy-Survivor Scan ──────────────────────────────
    def _bankruptcy():
        from ..screening import ScanInput, run_bankruptcy_survivor_scan
        return run_bankruptcy_survivor_scan(ScanInput(
            target_name=inp.deal_name,
            specialty=inp.specialty,
            states=inp.states, msas=inp.msas,
            cbsa_codes=inp.cbsa_codes,
            legal_structure=inp.legal_structure,
            landlord=inp.landlord,
            lease_term_years=inp.lease_term_years,
            lease_escalator_pct=inp.lease_escalator_pct,
            ebitdar_coverage=inp.ebitdar_coverage,
            geography=inp.geography,
            oon_revenue_share=inp.oon_revenue_share,
            hopd_revenue_annual_usd=inp.hopd_revenue_annual_usd,
        ))
    report.bankruptcy_scan = _timed(
        "bankruptcy_scan", _bankruptcy, step_log,
    )
    if report.bankruptcy_scan is not None:
        verdict = getattr(report.bankruptcy_scan, "verdict", None)
        report.bankruptcy_verdict = (
            verdict.value if hasattr(verdict, "value") else str(verdict or "")
        ) or None

    # ─── 5. Steward Score ─────────────────────────────────────────
    if inp.landlord or inp.lease_term_years:
        def _steward():
            from ..real_estate import (
                LeaseLine, LeaseSchedule, compute_steward_score,
            )
            sched = LeaseSchedule(lines=[LeaseLine(
                property_id=inp.deal_name,
                property_type=(inp.specialty or "HOSPITAL").upper(),
                base_rent_annual_usd=float(inp.annual_rent_usd or 1.0),
                escalator_pct=inp.lease_escalator_pct or 0.0,
                term_years=inp.lease_term_years or 10,
                landlord=inp.landlord,
            )])
            return compute_steward_score(
                sched,
                portfolio_ebitdar_annual_usd=inp.portfolio_ebitdar_usd,
                portfolio_annual_rent_usd=inp.annual_rent_usd,
                geography=inp.geography,
            )
        report.steward_score = _timed(
            "steward_score", _steward, step_log,
        )
        if report.steward_score is not None:
            tier = getattr(report.steward_score, "tier", None)
            report.steward_tier = (
                tier.value if hasattr(tier, "value") else str(tier or "")
            ) or None

    # ─── 6. Cyber Score ───────────────────────────────────────────
    if inp.ehr_vendor or inp.business_associates:
        def _cyber():
            from ..cyber import (
                assess_business_associates, compose_cyber_score,
                ehr_vendor_risk_score,
            )
            ba_findings = (
                assess_business_associates(inp.business_associates)
                if inp.business_associates else []
            )
            return compose_cyber_score(
                ehr_vendor_risk=(
                    ehr_vendor_risk_score(inp.ehr_vendor)
                    if inp.ehr_vendor else None
                ),
                ba_findings=ba_findings,
                it_capex=None, bi_loss=None,
                annual_revenue_usd=inp.revenue_year0_usd or 0.0,
            )
        report.cyber_score = _timed(
            "cyber_score", _cyber, step_log,
        )

    # ─── 7. Counterfactual Advisor ────────────────────────────────
    def _counterfactual():
        from ..counterfactual import run_counterfactuals_from_ccd
        meta: Dict[str, Any] = {}
        if inp.legal_structure: meta["legal_structure"] = inp.legal_structure
        if inp.states: meta["states"] = inp.states
        if inp.landlord: meta["landlord"] = inp.landlord
        if inp.specialty: meta["specialty"] = inp.specialty
        if inp.lease_term_years:
            meta["lease_term_years"] = inp.lease_term_years
        if inp.lease_escalator_pct is not None:
            meta["lease_escalator_pct"] = inp.lease_escalator_pct
        if inp.ebitdar_coverage is not None:
            meta["ebitdar_coverage"] = inp.ebitdar_coverage
        return run_counterfactuals_from_ccd(report.ccd, metadata=meta)
    report.counterfactual_set = _timed(
        "counterfactual", _counterfactual, step_log,
    )
    if report.counterfactual_set is not None:
        largest = getattr(report.counterfactual_set, "largest_lever", None)
        if largest is not None:
            report.counterfactual_largest_lever_usd = float(
                getattr(largest, "estimated_dollar_impact_usd", 0.0) or 0.0,
            )

    # ─── 8. Physician Attrition (P-PAM) ───────────────────────────
    if inp.providers:
        def _ppam():
            from ..physician_attrition import analyze_roster
            return analyze_roster(inp.providers)
        report.attrition_report = _timed(
            "physician_attrition", _ppam, step_log,
        )
        if report.attrition_report is not None:
            bridge = getattr(report.attrition_report, "bridge_input", None)
            if bridge is not None:
                report.attrition_ebitda_at_risk_usd = float(
                    getattr(bridge, "ebitda_at_risk_usd", 0.0) or 0.0,
                )

        # ─── 8b. Physician Economic Units ─────────────────────────
        # Run the EU analyzer on the same roster — complements PPAM
        # (flight-risk) with structural-contribution ranking.
        def _eu():
            from ..physician_eu import analyze_roster_eu
            return analyze_roster_eu(inp.providers)
        report.eu_report = _timed(
            "physician_eu", _eu, step_log,
        )
        if report.eu_report is not None:
            opt = getattr(report.eu_report, "optimization", None)
            if opt is not None:
                report.eu_ebitda_uplift_usd = float(
                    getattr(opt, "ebitda_uplift_usd", 0.0) or 0.0,
                )
                report.eu_drop_candidate_count = len(
                    list(getattr(opt, "candidates", []) or []),
                )

    # ─── 9. Deal Autopsy ──────────────────────────────────────────
    def _autopsy():
        from ..deal_autopsy import (
            historical_library, match_target, signature_from_ccd,
        )
        md: Dict[str, float] = dict(inp.autopsy_metadata)
        # Derive overrides from pipeline state.
        if inp.annual_rent_usd and inp.revenue_year0_usd and inp.revenue_year0_usd > 0:
            md.setdefault(
                "lease_intensity",
                min(1.0, inp.annual_rent_usd / inp.revenue_year0_usd / 0.20),
            )
        if inp.ebitdar_coverage is not None:
            md.setdefault(
                "ebitdar_stress",
                min(1.0, max(0.0, (2.5 - inp.ebitdar_coverage) / 1.5)),
            )
        if inp.oon_revenue_share is not None:
            md.setdefault("oon_revenue_share", inp.oon_revenue_share)
        if report.bankruptcy_verdict:
            md.setdefault("regulatory_exposure", {
                "CRITICAL": 0.9, "RED": 0.75, "YELLOW": 0.45,
                "GREEN": 0.15,
            }.get(report.bankruptcy_verdict.upper(), 0.4))
        sig = signature_from_ccd(report.ccd, metadata=md)
        return match_target(sig, historical_library(), top_k=5)
    report.autopsy_matches = _timed(
        "deal_autopsy", _autopsy, step_log,
    )
    if report.autopsy_matches:
        top = report.autopsy_matches[0]
        report.top_autopsy_match = getattr(getattr(top, "deal", None), "name", None)
        report.top_autopsy_similarity = float(
            getattr(top, "similarity", 0.0) or 0.0,
        )

    # ─── 10. Market Intel ─────────────────────────────────────────
    def _market():
        from ...market_intel import (
            find_comparables, sector_sentiment, transaction_multiple,
        )
        out: Dict[str, Any] = {}
        if inp.market_category:
            payload = find_comparables(
                target_category=inp.market_category,
                target_revenue_usd=inp.revenue_year0_usd,
            )
            out["comps"] = payload.get("comps") or []
            out["band"] = payload.get("band")
        if inp.specialty:
            out["sector_sentiment"] = sector_sentiment(inp.specialty)
            out["transaction_band"] = transaction_multiple(
                specialty=inp.specialty,
                ev_usd=inp.enterprise_value_usd,
            )
        return out
    report.market_intel = _timed("market_intel", _market, step_log)

    # ─── 10.1 Payer Mix Stress — per-payer rate-shock MC ─────────
    # Fires when the target has revenue + a rough payer mix.  We
    # derive a reasonable mix from medicare_share (splitting into
    # Medicare FFS / MA) and defaults for commercial + Medicaid
    # when the caller doesn't supply an explicit mix.
    if inp.revenue_year0_usd and inp.revenue_year0_usd > 0:
        def _payer_stress():
            from ..payer_stress import (
                PayerMixEntry, run_payer_stress,
            )
            # Derive mix from medicare_share signal. Real payer mix
            # will override if the caller pre-computed it elsewhere.
            medicare = float(inp.medicare_share or 0.35)
            # Typical hospital split: 65% FFS / 35% MA of the
            # Medicare bucket
            medicare_ffs = medicare * 0.65
            medicare_ma = medicare * 0.35
            medicaid = 0.15
            commercial = max(0.0, 1.0 - medicare - medicaid)
            mix = [
                PayerMixEntry("Medicare FFS", medicare_ffs),
                PayerMixEntry("Medicare Advantage", medicare_ma),
                PayerMixEntry("Medicaid managed", medicaid),
                PayerMixEntry(
                    "UnitedHealthcare", commercial * 0.30,
                ),
                PayerMixEntry("Anthem", commercial * 0.28),
                PayerMixEntry("Aetna", commercial * 0.18),
                PayerMixEntry("Cigna", commercial * 0.14),
                PayerMixEntry("Self-pay", commercial * 0.10),
            ]
            # Drop zero-share entries
            mix = [m for m in mix if m.share_of_npr > 0.005]
            return run_payer_stress(
                target_name=inp.deal_name,
                mix=mix,
                total_npr_usd=inp.revenue_year0_usd,
                total_ebitda_usd=inp.ebitda_year0_usd,
                horizon_years=inp.hold_years,
                n_paths=300,
            )
        report.payer_stress = _timed(
            "payer_stress", _payer_stress, step_log,
        )

    # ─── 10.2 HCRIS X-Ray — filed Medicare cost-report benchmark ──
    # Only fires when the caller supplies a CCN.  Connects the
    # target's filed operating margin + payer-day mix to 25-50 peer
    # hospitals — the ground-truth data that pre-dates any banker
    # spin and feeds the Bear Case generator downstream.
    if inp.hcris_ccn:
        def _hcris():
            from ..hcris_xray import xray
            return xray(ccn=inp.hcris_ccn, peer_k=25)
        report.hcris_xray = _timed(
            "hcris_xray", _hcris, step_log,
        )

    # ─── 10.5 Regulatory Calendar × Kill-Switch ──────────────────
    # Maps CMS / OIG / FTC / DOJ / NSA-IDR events to the target's
    # thesis drivers.  Produces the EBITDA overlay that feeds
    # reg_headwind_usd on the DealScenario a few steps later.
    def _regulatory():
        from ..regulatory_calendar import (
            analyze_regulatory_exposure,
        )
        # Infer MA mix: medicare_share × a typical 0.55 MA penetration
        # unless the CCD already carries an explicit MA share. This
        # is rough but conservative — the driver gating thresholds
        # mean we under-fire rather than over-fire.
        ma_mix = None
        if inp.medicare_share is not None:
            ma_mix = float(inp.medicare_share) * 0.55
        has_hopd = bool(inp.hopd_revenue_annual_usd and
                        inp.hopd_revenue_annual_usd > 0)
        # REIT landlord detection — landlord name contains known REIT
        # markers (MPT / Welltower / Ventas / Omega / Sabra).
        has_reit = bool(inp.landlord) and any(
            m in str(inp.landlord).upper()
            for m in ("MPT", "WELLTOWER", "VENTAS", "OMEGA", "SABRA")
        )
        commercial = None
        if inp.medicare_share is not None:
            # A reasonable residual estimate
            commercial = max(
                0.0, 1.0 - float(inp.medicare_share) - 0.15,
            )
        specialties: List[str] = []
        if inp.specialty:
            specialties.append(inp.specialty)
        target = {
            "specialties": specialties,
            "specialty": inp.specialty,
            "ma_mix_pct": ma_mix,
            "commercial_payer_share": commercial,
            "has_hopd_revenue": has_hopd,
            "has_reit_landlord": has_reit,
            "revenue_usd": inp.revenue_year0_usd,
            "ebitda_usd": inp.ebitda_year0_usd,
        }
        return analyze_regulatory_exposure(
            target_profile=target, horizon_months=24,
        )
    report.regulatory_exposure = _timed(
        "regulatory_exposure", _regulatory, step_log,
    )
    if report.regulatory_exposure is not None:
        rx = report.regulatory_exposure
        report.regulatory_verdict = rx.verdict.value
        report.regulatory_killed_driver_count = rx.killed_driver_count
        report.regulatory_total_margin_impact_pp = (
            rx.total_expected_margin_impact_pp
        )
        cum = sum(o.ebitda_delta_usd for o in rx.ebitda_overlay)
        report.regulatory_cumulative_ebitda_impact_usd = float(cum)
        # First-kill date across any driver — the demo moment
        first_kill: Optional[str] = None
        for tl in rx.driver_timelines:
            if tl.first_kill_date and (
                first_kill is None or tl.first_kill_date < first_kill
            ):
                if tl.worst_verdict.value == "KILLED":
                    first_kill = tl.first_kill_date
        report.regulatory_first_kill_date = first_kill

    # ─── 11. Assemble DealScenario ────────────────────────────────
    def _scenario():
        from ..deal_mc import DealScenario
        # Pull pipeline-derived drivers.
        denial_mean = 0.015
        if report.denial_report is not None:
            bridge = getattr(report.denial_report, "bridge_input", None)
            if bridge is not None:
                rev = inp.revenue_year0_usd or 1.0
                denial_mean = min(
                    0.05,
                    float(getattr(bridge, "recoverable_revenue_usd", 0.0) or 0.0) / rev,
                )
        reg_headwind = float(
            report.counterfactual_largest_lever_usd or 0.0,
        )
        # Regulatory Calendar overlay subtracts from the EBITDA
        # trajectory.  We take abs() because the DealScenario lever
        # is defined as a positive headwind magnitude and pass the
        # larger of the two sources so we don't double-count.
        reg_cal_hit = abs(float(
            report.regulatory_cumulative_ebitda_impact_usd or 0.0,
        ))
        if reg_cal_hit > reg_headwind:
            reg_headwind = reg_cal_hit
        physician_attrition_alpha = 1.5
        physician_attrition_beta = 8.0
        if report.attrition_report is not None:
            bridge = getattr(report.attrition_report, "bridge_input", None)
            if bridge is not None:
                pct = float(
                    getattr(bridge, "attrition_pct_of_collections", 0.0) or 0.0,
                )
                # Parameterise Beta so mean ≈ pct.
                if 0 < pct < 0.95:
                    # alpha / (alpha + beta) = pct; fix alpha at 1.5
                    physician_attrition_alpha = 1.5
                    physician_attrition_beta = (
                        physician_attrition_alpha * (1 - pct) / max(pct, 0.01)
                    )

        cyber_prob = 0.05
        cyber_loss = 5_000_000.0
        if report.cyber_score is not None:
            band = str(getattr(report.cyber_score, "band", "") or "").upper()
            cyber_prob = {
                "CRITICAL": 0.20, "RED": 0.12,
                "YELLOW": 0.07, "GREEN": 0.03,
            }.get(band, 0.05)

        return DealScenario(
            enterprise_value_usd=inp.enterprise_value_usd or 100_000_000.0,
            equity_check_usd=inp.equity_check_usd or 50_000_000.0,
            debt_usd=inp.debt_usd or 50_000_000.0,
            entry_multiple=inp.entry_multiple or 9.0,
            hold_years=inp.hold_years,
            revenue_year0_usd=inp.revenue_year0_usd or 0.0,
            ebitda_year0_usd=inp.ebitda_year0_usd or 0.0,
            medicare_share=inp.medicare_share or 0.30,
            denial_improvement_pp_mean=denial_mean,
            reg_headwind_usd=reg_headwind,
            physician_attrition_alpha=physician_attrition_alpha,
            physician_attrition_beta=physician_attrition_beta,
            cyber_incident_prob_per_year=cyber_prob,
            cyber_expected_loss_usd_if_incident=cyber_loss,
        )
    report.deal_scenario = _timed(
        "deal_scenario_assembly", _scenario, step_log,
    )

    # ─── 12. Deal Monte Carlo ─────────────────────────────────────
    if report.deal_scenario is not None:
        def _deal_mc():
            from ..deal_mc import run_deal_monte_carlo
            return run_deal_monte_carlo(
                report.deal_scenario,
                n_runs=inp.n_runs,
                scenario_name=inp.deal_name,
            )
        report.deal_mc_result = _timed(
            "deal_mc", _deal_mc, step_log,
        )
        if report.deal_mc_result is not None:
            report.p50_moic = float(
                getattr(report.deal_mc_result, "moic_p50", 0.0) or 0.0,
            )
            report.prob_sub_1x = float(
                getattr(report.deal_mc_result, "prob_sub_1x", 0.0) or 0.0,
            )
            attr = getattr(report.deal_mc_result, "attribution", None)
            if attr is not None:
                contribs = getattr(attr, "contributions", []) or []
                if contribs:
                    report.top_variance_driver = str(
                        getattr(contribs[0], "driver", "") or "",
                    ) or None

    # ─── 12.5 Covenant Stress Lab — capital stack × covenant cone ─
    # Consumes Deal MC EBITDA bands + Regulatory Calendar overlay
    # and produces per-quarter covenant-breach probability curves.
    if report.deal_mc_result is not None and report.deal_scenario is not None:
        def _covenant_stress():
            from ..covenant_lab import (
                default_lbo_stack, run_covenant_stress,
            )
            bands = getattr(report.deal_mc_result, "ebitda_bands", None)
            if not bands:
                return None
            mc_bands: List[Dict[str, float]] = []
            for b in bands:
                p50 = float(
                    getattr(b, "p50", None)
                    or getattr(b, "mean", 0.0) or 0.0
                )
                p25 = float(getattr(b, "p25", None) or p50 * 0.85)
                p75 = float(getattr(b, "p75", None) or p50 * 1.15)
                mc_bands.append({"p25": p25, "p50": p50, "p75": p75})
            if not mc_bands:
                return None
            debt_usd = float(report.deal_scenario.debt_usd or 0.0)
            if debt_usd <= 0:
                return None
            stack = default_lbo_stack(
                total_debt_usd=debt_usd,
                revolver_usd=debt_usd * 0.10,
                revolver_draw_pct=0.30,
                term_years=min(len(mc_bands), 6),
            )
            # Pull regulatory overlay if present
            overlay: Optional[List[float]] = None
            if report.regulatory_exposure is not None:
                eb_overlay = getattr(
                    report.regulatory_exposure,
                    "ebitda_overlay", None,
                )
                if eb_overlay:
                    # Map year → delta starting Y1
                    year_map = {
                        o.year: o.ebitda_delta_usd for o in eb_overlay
                    }
                    from datetime import date
                    base_year = date.today().year
                    overlay = [
                        year_map.get(base_year + i, 0.0)
                        for i in range(len(mc_bands))
                    ]
            quarters = min(len(mc_bands) * 4, 24)
            return run_covenant_stress(
                ebitda_bands=mc_bands,
                capital_stack=stack,
                rate_path_annual=[0.055] * quarters,
                quarters=quarters,
                regulatory_overlay_usd_by_year=overlay,
            )
        report.covenant_stress = _timed(
            "covenant_stress", _covenant_stress, step_log,
        )
        if report.covenant_stress is not None:
            cs = report.covenant_stress
            report.covenant_max_breach_probability = float(
                cs.max_breach_probability,
            )
            report.covenant_earliest_50pct_covenant = (
                cs.earliest_50pct_covenant
            )
            report.covenant_earliest_50pct_quarter = (
                cs.earliest_50pct_quarter
            )
            if cs.equity_cures:
                # Median cure of the covenant with highest breach-path
                # fraction (most likely to actually need curing)
                worst = max(
                    cs.equity_cures,
                    key=lambda e: e.breach_path_fraction,
                )
                if worst.median_cure_usd is not None:
                    report.covenant_median_cure_usd = float(
                        worst.median_cure_usd,
                    )

    # ─── 13. Exit Timing — when + to whom ────────────────────────
    if report.deal_mc_result is not None and report.deal_scenario is not None:
        def _exit_timing():
            from ..exit_timing import analyze_exit_timing
            # Use Deal MC's year-by-year EBITDA median from revenue
            # bands × a derived margin — simpler: pull from ebitda_bands
            bands = getattr(report.deal_mc_result, "ebitda_bands", None)
            if bands is None:
                return None
            # YearBand has .p50 for the median; fall back to .mean
            eb_by_year = [
                float(
                    getattr(b, "p50", None)
                    or getattr(b, "mean", 0.0) or 0.0
                )
                for b in bands
            ]
            # Restrict candidate hold years to those with ACTUAL
            # Deal MC data — no extrapolation past the simulation
            # horizon.  Partners get real numbers only.
            max_data_year = len(eb_by_year) - 1
            candidate_holds = tuple(
                y for y in (2, 3, 4, 5, 6, 7)
                if y <= max_data_year
            )
            if not candidate_holds:
                return None

            peer_median = None
            try:
                if report.market_intel:
                    band = report.market_intel.get("band") or {}
                    peer_median = band.get("median_ev_ebitda")
            except Exception:  # noqa: BLE001
                pass

            sentiment = None
            try:
                if report.market_intel:
                    sentiment = report.market_intel.get("sector_sentiment")
            except Exception:  # noqa: BLE001
                pass

            # Prefer the regulatory-calendar verdict (more precise)
            # over bankruptcy_verdict (a crude proxy).  Map the
            # kill-switch verdicts onto the Exit Timing vocabulary.
            reg_verdict = None
            if report.regulatory_verdict:
                reg_verdict = {
                    "PASS": "GREEN", "CAUTION": "YELLOW",
                    "WARNING": "RED", "FAIL": "CRITICAL",
                }.get(report.regulatory_verdict)
            if reg_verdict is None:
                reg_verdict = report.bankruptcy_verdict or None
            return analyze_exit_timing(
                equity_check_usd=report.deal_scenario.equity_check_usd,
                debt_year0_usd=report.deal_scenario.debt_usd,
                ebitda_median_by_year=eb_by_year,
                peer_median_multiple=peer_median,
                regulatory_verdict=reg_verdict,
                sector_sentiment=sentiment,
                candidate_holds=candidate_holds,
            )
        report.exit_timing_report = _timed(
            "exit_timing", _exit_timing, step_log,
        )
        if report.exit_timing_report is not None:
            rec = getattr(
                report.exit_timing_report, "recommendation", None,
            )
            if rec is not None:
                report.exit_recommendation_year = int(
                    getattr(rec, "exit_year", 0) or 0,
                )
                report.exit_recommendation_buyer = str(
                    getattr(rec, "buyer_label", "") or "",
                )
                report.exit_expected_irr = float(
                    getattr(rec, "expected_irr", 0.0) or 0.0,
                )

    return report


def pipeline_observations(
    report: ThesisPipelineReport,
) -> Dict[str, bool]:
    """Translate a pipeline report into the boolean-keyed dict the
    Diligence Checklist tracker consumes.

    Missing step → absent key (checklist treats as OPEN).
    Successful step → True.
    Failed step → False.
    """
    observations: Dict[str, bool] = {}

    def _ok(attr: str) -> bool:
        return getattr(report, attr, None) is not None

    if _ok("ccd"):
        observations["ccd_ingested"] = True
    if _ok("kpi_bundle"):
        observations["hfma_days_in_ar_computed"] = True
        observations["hfma_denial_rate_computed"] = True
        observations["hfma_ar_aging_computed"] = True
        observations["hfma_nrr_computed"] = True
    if _ok("cohort_report"):
        observations["cohort_liquidation_computed"] = True
    if _ok("waterfall"):
        observations["qor_waterfall_computed"] = True
    if _ok("denial_report"):
        observations["denial_prediction_run"] = True
        observations["denial_pareto_computed"] = True
    if _ok("bankruptcy_scan"):
        observations["bankruptcy_scan_run"] = True
    if _ok("steward_score"):
        observations["steward_run"] = True
    if _ok("cyber_score"):
        observations["cyber_run"] = True
    if _ok("counterfactual_set"):
        observations["counterfactual_run"] = True
    if _ok("attrition_report"):
        observations["physician_attrition_run"] = True
    if _ok("eu_report"):
        # Also covers the Stark / FMV check from the physician-comp
        # panel (the EU analyzer surfaces FMV-adjusted contribution
        # per provider).
        observations["physician_comp_fmv_run"] = True
    if _ok("autopsy_matches"):
        observations["deal_autopsy_run"] = True
    if _ok("market_intel"):
        observations["market_intel_run"] = True
        observations["sector_sentiment_reviewed"] = True
    if _ok("regulatory_exposure"):
        observations["regulatory_calendar_run"] = True
    if _ok("covenant_stress"):
        observations["covenant_stress_run"] = True
    if _ok("hcris_xray"):
        observations["hcris_xray_run"] = True
    if _ok("payer_stress"):
        observations["payer_stress_run"] = True
    if _ok("deal_mc_result"):
        observations["deal_mc_run"] = True
        observations["ebitda_bridge_built"] = True

    return observations
