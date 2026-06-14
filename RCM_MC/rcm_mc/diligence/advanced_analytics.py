"""Advanced-analytics suite — one call across the native marts.

The six diligence marts shipped in this work stream
(``risk_adjustment``, ``hierarchical_bench``, ``pmpm``, ``policy_shock``,
``survival``, ``episodes``, ``quality_measures``, ``spatial``) plus the
Benford integrity screen each answer one question. In a real diligence
run a partner wants them composed: feed whatever data the deal has, get
back every finding the data supports, with the EBITDA-at-risk items
rolled into one number and the headlines collected into one narrative.

This facade does exactly that and nothing more. Each section is
*optional* — pass the inputs you have, skip the rest; a section with no
inputs is simply absent from the result. It does **not** reach into the
``DealAnalysisPacket`` or the server (that wiring is a deliberate later
pass with its own invariants); it is a pure, side-effect-free
composition you can call from a notebook, a test, or an eventual packet
builder. Every sub-result keeps its own ``source_module`` /
``citation_key``, so the provenance graph still resolves through it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from rcm_mc.diligence.episodes import (
    ClaimLine,
    EpisodeDefinition,
    EpisodeGroupingResult,
    group_episodes,
)
from rcm_mc.diligence.hierarchical_bench import (
    PartialPoolResult,
    partial_pool,
)
from rcm_mc.diligence.integrity.benford import BenfordResult, benford_first_digit
from rcm_mc.diligence.pmpm import PMPMPeriod, PMPMTrendResult, analyze_pmpm
from rcm_mc.diligence.policy_shock import (
    DiDResult,
    PanelData,
    PolicyEbitdaOverlay,
    estimate_did,
    policy_ebitda_overlay,
)
from rcm_mc.diligence.quality_measures import QualityScorecard, score_quality
from rcm_mc.diligence.risk_adjustment import (
    Demographics,
    PanelRiskScore,
    score_panel,
)
from rcm_mc.diligence.survival import KMResult, kaplan_meier

CITATION_KEY = "AA1"
SOURCE_MODULE = "diligence.advanced_analytics"


@dataclass
class AdvancedAnalyticsInputs:
    """Optional inputs per mart. Provide what the deal has; skip the rest."""
    # Risk adjustment
    panel: Optional[Sequence[Tuple[Demographics, Sequence[str]]]] = None
    # Hierarchical benchmarking (unit-level estimates + SEs)
    unit_ids: Optional[Sequence[str]] = None
    unit_estimates: Optional[Sequence[float]] = None
    unit_ses: Optional[Sequence[float]] = None
    # PMPM trend
    pmpm_periods: Optional[Sequence[PMPMPeriod]] = None
    pmpm_periods_per_year: float = 12.0
    pmpm_annual_member_months: Optional[float] = None
    # Policy shock (DiD)
    policy_panel: Optional[PanelData] = None
    policy_exposed_revenue_usd: Optional[float] = None
    policy_att_is_pct: bool = True
    # Survival
    survival_durations: Optional[Sequence[float]] = None
    survival_events: Optional[Sequence[int]] = None
    # Episodes
    episode_claims: Optional[Sequence[ClaimLine]] = None
    episode_definition: Optional[EpisodeDefinition] = None
    # Quality measures (pre-evaluated MeasureResults)
    quality_results: Optional[Sequence[Any]] = None
    # Benford integrity screen
    billed_amounts: Optional[Sequence[float]] = None


@dataclass
class AdvancedAnalyticsResult:
    risk: Optional[PanelRiskScore] = None
    hierarchical: Optional[PartialPoolResult] = None
    pmpm: Optional[PMPMTrendResult] = None
    policy: Optional[DiDResult] = None
    policy_overlay: Optional[PolicyEbitdaOverlay] = None
    survival: Optional[KMResult] = None
    episodes: Optional[EpisodeGroupingResult] = None
    quality: Optional[QualityScorecard] = None
    integrity: Optional[BenfordResult] = None
    total_ebitda_at_risk_usd: float = 0.0
    findings: List[str] = field(default_factory=list)
    headline: str = ""
    source_module: str = SOURCE_MODULE
    citation_key: str = CITATION_KEY

    def to_dict(self) -> Dict[str, Any]:
        def d(x: Any) -> Any:
            return x.to_dict() if x is not None else None
        return {
            "risk": d(self.risk),
            "hierarchical": d(self.hierarchical),
            "pmpm": d(self.pmpm),
            "policy": d(self.policy),
            "policy_overlay": d(self.policy_overlay),
            "survival": d(self.survival),
            "episodes": d(self.episodes),
            "quality": d(self.quality),
            "integrity": d(self.integrity),
            "total_ebitda_at_risk_usd": round(self.total_ebitda_at_risk_usd, 2),
            "findings": list(self.findings),
            "headline": self.headline,
            "source_module": self.source_module,
            "citation_key": self.citation_key,
        }


def run_advanced_analytics(
    inputs: AdvancedAnalyticsInputs,
) -> AdvancedAnalyticsResult:
    """Run every mart for which inputs were provided; collect the
    findings and roll the EBITDA-at-risk items into one number.

    Returns a single result object whose sections are ``None`` when
    their inputs were absent. Never raises on a missing section —
    diligence data arrives piecemeal, and a partial run is the common
    case."""
    res = AdvancedAnalyticsResult()
    findings: List[str] = []
    ebitda_at_risk = 0.0

    if inputs.panel:
        res.risk = score_panel(inputs.panel)
        findings.append(
            f"[RA1] Panel mean RAF {res.risk.mean_raf:.3f} "
            f"(n={res.risk.n_beneficiaries})."
        )

    if inputs.unit_ids and inputs.unit_estimates and inputs.unit_ses:
        res.hierarchical = partial_pool(
            inputs.unit_ids, inputs.unit_estimates, inputs.unit_ses,
        )
        findings.append(f"[HB1] {res.hierarchical.headline}")

    if inputs.pmpm_periods:
        res.pmpm = analyze_pmpm(
            inputs.pmpm_periods,
            periods_per_year=inputs.pmpm_periods_per_year,
            annual_member_months=inputs.pmpm_annual_member_months,
        )
        findings.append(f"[PM1] {res.pmpm.headline}")
        if res.pmpm.projected_ebitda_impact_usd and \
                res.pmpm.projected_ebitda_impact_usd > 0:
            ebitda_at_risk += res.pmpm.projected_ebitda_impact_usd

    if inputs.policy_panel is not None:
        res.policy = estimate_did(inputs.policy_panel)
        findings.append(f"[PS1] {res.policy.headline}")
        if inputs.policy_exposed_revenue_usd is not None:
            res.policy_overlay = policy_ebitda_overlay(
                res.policy, inputs.policy_exposed_revenue_usd,
                att_is_pct=inputs.policy_att_is_pct,
            )
            # Adverse (negative) impact is the at-risk number.
            if res.policy_overlay.ebitda_impact_usd < 0:
                ebitda_at_risk += abs(res.policy_overlay.ebitda_impact_usd)

    if inputs.survival_durations and inputs.survival_events:
        res.survival = kaplan_meier(
            inputs.survival_durations, inputs.survival_events,
        )
        med = res.survival.median_survival
        findings.append(
            f"[SV1] Median time-to-event "
            f"{'n/a' if med is None else f'{med:.0f}'} "
            f"({res.survival.n_events_total} events / "
            f"{res.survival.n_subjects} subjects)."
        )

    if inputs.episode_claims and inputs.episode_definition is not None:
        res.episodes = group_episodes(
            inputs.episode_claims, inputs.episode_definition,
        )
        findings.append(f"[EP1] {res.episodes.headline}")

    if inputs.quality_results:
        res.quality = score_quality(inputs.quality_results)
        findings.append(f"[QM1] {res.quality.headline}")

    if inputs.billed_amounts:
        res.integrity = benford_first_digit(inputs.billed_amounts)
        findings.append(f"[IN-BEN] {res.integrity.headline}")

    res.findings = findings
    res.total_ebitda_at_risk_usd = ebitda_at_risk
    res.headline = _suite_headline(res, findings, ebitda_at_risk)
    return res


def _suite_headline(
    res: AdvancedAnalyticsResult, findings: List[str], ebitda: float,
) -> str:
    n = sum(1 for s in (
        res.risk, res.hierarchical, res.pmpm, res.policy, res.survival,
        res.episodes, res.quality, res.integrity,
    ) if s is not None)
    if n == 0:
        return "Advanced analytics: no inputs supplied — nothing to run."
    base = f"Advanced analytics ran {n} mart(s)."
    if ebitda > 0:
        base += f" Aggregate EBITDA at risk: ${ebitda / 1e6:.2f}M."
    if res.integrity is not None and \
            res.integrity.verdict.value == "NONCONFORMING":
        base += " ⚠ Billing-integrity screen flagged — investigate before trusting totals."
    return base
