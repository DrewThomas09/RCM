"""Automated risk-flag assessment for one deal.

Walks the observed metrics + hospital profile + comparable cohort +
EBITDA bridge and produces a list of :class:`RiskFlag` rows. This is
what an associate would otherwise spend a morning doing by hand — flag
"denial rate is above the partner comfort line", "Medicaid exposure is
hot under OBBBA", "commercial mix is thin enough that payer
renegotiation leverage is gone", etc.

Category taxonomy is the contract — every call site (UI pills,
diligence-question generator, exec summary) branches on these strings:

    OPERATIONAL   — the KPI-level workflow health (denials, AR, claims)
    REGULATORY    — exogenous policy shocks (OBBBA, sequestration)
    PAYER         — concentration, mix, payer-specific friction
    CODING        — CDI / documentation / CMI gaps
    DATA_QUALITY  — analyst-visible reasons to distrust the inputs
    FINANCIAL     — margin-level structural problems

Every flag carries:
- ``title``          — one-line headline (shown in the tornado/card)
- ``detail``         — 2-3 sentences with numbers (shown on hover/drill)
- ``trigger_metrics`` — metric keys that drove the flag (for the
  provenance chain + for packet-level dedup)
- ``ebitda_at_risk`` — dollar estimate of exposure when we can size it,
  else ``None``. Partners do not want fake precision — we leave this
  blank rather than guess on flags we can't size.

This module is intentionally free of package-internal side effects: it
only reads its inputs and returns a flat list. All persistence lives in
the packet layer.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .packet import (
    ComparableSet,
    EBITDABridgeResult,
    HospitalProfile,
    ProfileMetric,
    RiskFlag,
    RiskSeverity,
)
from .completeness import (
    CompletenessAssessment,
    RCM_METRIC_REGISTRY,
)

logger = logging.getLogger(__name__)


# ── Category constants ──────────────────────────────────────────────

CATEGORY_OPERATIONAL = "OPERATIONAL"
CATEGORY_REGULATORY = "REGULATORY"
CATEGORY_PAYER = "PAYER"
CATEGORY_CODING = "CODING"
CATEGORY_DATA_QUALITY = "DATA_QUALITY"
CATEGORY_FINANCIAL = "FINANCIAL"


# States with Medicaid work-requirement waivers approved or active at
# the time of the OBBBA CBO projection. Not exhaustive — these are the
# ones PE diligence teams actively track. Keep as a list so adding
# states is a one-line edit.
_WORK_REQUIREMENT_STATES = {
    "AR", "GA", "KY", "NH", "OH", "UT", "WI", "IA", "MT",
}


# ── Helpers ─────────────────────────────────────────────────────────

def _get_metric(rcm_profile: Dict[str, ProfileMetric], key: str) -> Optional[float]:
    m = (rcm_profile or {}).get(key)
    if m is None:
        return None
    try:
        return float(m.value)
    except (TypeError, ValueError, AttributeError):
        return None


def _normalize_payer_mix(payer_mix: Dict[str, float]) -> Dict[str, float]:
    """Return the mix as fractions (summing ~1.0) regardless of whether
    the caller gave us fractions or percentage points. Robust to common
    partner-sheet inputs."""
    if not payer_mix:
        return {}
    total = sum(float(v or 0.0) for v in payer_mix.values())
    if total <= 0:
        return {}
    if 0.5 <= total <= 1.5:
        return {k: float(v or 0.0) for k, v in payer_mix.items()}
    # Assume pct-scale — scale down to fractions.
    return {k: float(v or 0.0) / total for k, v in payer_mix.items()}


def _cmi_comparable_p25(
    comparables: Optional[ComparableSet],
) -> Optional[float]:
    """P25 of ``case_mix_index`` across the comparable cohort. Returns
    None if fewer than 4 peers carry CMI.
    """
    if comparables is None or not comparables.peers:
        return None
    vals = []
    for p in comparables.peers:
        v = (p.fields or {}).get("case_mix_index")
        if v is None:
            continue
        try:
            vals.append(float(v))
        except (TypeError, ValueError):
            continue
    if len(vals) < 4:
        return None
    vals.sort()
    # Nearest-rank P25 — good enough for a threshold check.
    idx = max(0, int(0.25 * (len(vals) - 1)))
    return float(vals[idx])


def _impact_from_bridge(
    bridge: Optional[EBITDABridgeResult], metric_key: str,
) -> Optional[float]:
    """Pull the matching lever's ``ebitda_impact`` off the bridge as a
    proxy for ``ebitda_at_risk`` on the flag.
    """
    if bridge is None or not bridge.per_metric_impacts:
        return None
    for imp in bridge.per_metric_impacts:
        if imp.metric_key == metric_key:
            return abs(float(imp.ebitda_impact))
    return None


def _rework_estimate(
    denial_rate_pct: float, claims_volume: int, cost_per_rework: float = 30.0,
) -> Optional[float]:
    """Rough annual rework cost from a denial rate. Only populated when
    the caller can tell us volume (via the bridge's financial profile).
    """
    if claims_volume <= 0:
        return None
    return float(denial_rate_pct) / 100.0 * claims_volume * float(cost_per_rework)


# ── Flag builders ───────────────────────────────────────────────────

def _build_operational_flags(
    rcm_profile: Dict[str, ProfileMetric],
    comparables: Optional[ComparableSet],
    bridge: Optional[EBITDABridgeResult],
) -> List[RiskFlag]:
    flags: List[RiskFlag] = []

    dr = _get_metric(rcm_profile, "denial_rate")
    if dr is not None and dr > 10.0:
        # Cohort percentile for the tooltip narrative.
        p50 = RCM_METRIC_REGISTRY["denial_rate"].get("benchmark_p50") or 5.2
        ear = _impact_from_bridge(bridge, "denial_rate")
        flags.append(RiskFlag(
            category=CATEGORY_OPERATIONAL,
            severity=RiskSeverity.CRITICAL if dr > 12.0 else RiskSeverity.HIGH,
            title="Systemic denial problem",
            detail=(
                f"Denial rate of {dr:.1f}% sits well above the "
                f"comparable median ({p50:.1f}%). Above the 10% "
                f"threshold the partner treats this as a workflow "
                f"breakdown — front-end eligibility, authorization, "
                f"and back-end follow-up all warrant targeted "
                f"diligence." +
                (f" Estimated EBITDA at risk: ${ear/1_000_000:.1f}M." if ear else "")
            ),
            trigger_metrics=["denial_rate"],
            trigger_metric="denial_rate",
            trigger_value=float(dr),
            ebitda_at_risk=ear,
        ))

    aro = _get_metric(rcm_profile, "ar_over_90_pct")
    if aro is not None and aro > 20.0:
        flags.append(RiskFlag(
            category=CATEGORY_OPERATIONAL,
            severity=RiskSeverity.HIGH,
            title="Significant aged receivables",
            detail=(
                f"{aro:.1f}% of A/R is over 90 days, above the 20% "
                f"threshold. Typically signals either payer dispute "
                f"backlog or a collection-process breakdown — worth "
                f"obtaining the aging bucket breakdown by payer."
            ),
            trigger_metrics=["ar_over_90_pct"],
            trigger_metric="ar_over_90_pct",
            trigger_value=float(aro),
        ))

    ccr = _get_metric(rcm_profile, "clean_claim_rate")
    if ccr is not None and ccr < 90.0:
        flags.append(RiskFlag(
            category=CATEGORY_OPERATIONAL,
            severity=RiskSeverity.HIGH,
            title="Low clean claim rate",
            detail=(
                f"Clean claim rate of {ccr:.1f}% indicates front-end "
                f"process issues — likely eligibility verification or "
                f"coding errors. Industry target is 95%+."
            ),
            trigger_metrics=["clean_claim_rate"],
            trigger_metric="clean_claim_rate",
            trigger_value=float(ccr),
            ebitda_at_risk=_impact_from_bridge(bridge, "clean_claim_rate"),
        ))

    dnfb = _get_metric(rcm_profile, "dnfb_days")
    if dnfb is not None and dnfb > 7.0:
        flags.append(RiskFlag(
            category=CATEGORY_OPERATIONAL,
            severity=RiskSeverity.MEDIUM,
            title="DNFB bottleneck",
            detail=(
                f"{dnfb:.1f} DNFB days suggests charge capture or "
                f"coding bottleneck. Every day of DNFB ties up cash "
                f"and delays revenue recognition."
            ),
            trigger_metrics=["dnfb_days"],
            trigger_metric="dnfb_days",
            trigger_value=float(dnfb),
        ))

    cld = _get_metric(rcm_profile, "charge_lag_days")
    if cld is not None and cld > 5.0:
        flags.append(RiskFlag(
            category=CATEGORY_OPERATIONAL,
            severity=RiskSeverity.MEDIUM,
            title="Charge lag compresses cash flow",
            detail=(
                f"Charge lag of {cld:.1f} days delays claim "
                f"submission and compresses working-capital recovery."
            ),
            trigger_metrics=["charge_lag_days"],
            trigger_metric="charge_lag_days",
            trigger_value=float(cld),
        ))

    return flags


def _build_regulatory_flags(
    profile: HospitalProfile,
    rcm_profile: Dict[str, ProfileMetric],
) -> List[RiskFlag]:
    flags: List[RiskFlag] = []
    mix = _normalize_payer_mix(profile.payer_mix or {})

    medicaid = float(mix.get("medicaid", 0.0) or 0.0)
    if medicaid > 0.25:
        detail = (
            f"Medicaid exposure at {medicaid*100:.1f}% of payer mix. "
            f"Under OBBBA, CBO projects ~11.8M Medicaid coverage "
            f"losses nationally; hospitals with >25% Medicaid "
            f"revenue face material bad-debt pressure. Work "
            f"requirements take effect Dec 31, 2026."
        )
        state = (profile.state or "").upper().strip()
        if state and state in _WORK_REQUIREMENT_STATES:
            detail += (
                f" {state} has an active or pending work-requirement "
                f"waiver — amplifies coverage-loss impact."
            )
        flags.append(RiskFlag(
            category=CATEGORY_REGULATORY,
            severity=RiskSeverity.HIGH,
            title="OBBBA / Medicaid coverage-loss exposure",
            detail=detail,
            trigger_metrics=["payer_mix.medicaid"],
            trigger_metric="payer_mix.medicaid",
            trigger_value=float(medicaid),
        ))

    medicare = float(mix.get("medicare", 0.0) or 0.0)
    if medicare > 0.55:
        flags.append(RiskFlag(
            category=CATEGORY_REGULATORY,
            severity=RiskSeverity.MEDIUM,
            title="High Medicare dependence",
            detail=(
                f"Medicare mix at {medicare*100:.1f}% exposes the "
                f"hospital to OBBBA sequestration (~4% Medicare "
                f"payment reduction 2026-2034) plus ongoing physician "
                f"conversion-factor declines."
            ),
            trigger_metrics=["payer_mix.medicare"],
            trigger_metric="payer_mix.medicare",
            trigger_value=float(medicare),
        ))

    return flags


def _build_payer_flags(
    profile: HospitalProfile,
    rcm_profile: Dict[str, ProfileMetric],
    bridge: Optional[EBITDABridgeResult],
) -> List[RiskFlag]:
    flags: List[RiskFlag] = []
    mix = _normalize_payer_mix(profile.payer_mix or {})

    # Single-payer concentration.
    for payer, frac in mix.items():
        if float(frac) > 0.30:
            ear = None
            if bridge is not None and bridge.current_ebitda > 0:
                # Rough sizing: a 10% rate cut on that payer →
                # concentration × 10% × net_revenue. We don't know
                # net_revenue from the packet here, so estimate using
                # the bridge's current_ebitda × (frac / ebitda_margin).
                # Instead of guessing, leave it None and let the
                # diligence question prompt for the rate sheet.
                ear = None
            flags.append(RiskFlag(
                category=CATEGORY_PAYER,
                severity=RiskSeverity.HIGH,
                title=f"Payer concentration: {payer}",
                detail=(
                    f"{payer} represents {frac*100:.1f}% of net "
                    f"revenue. Any rate concession or contract loss "
                    f"on a payer over 30% of revenue is a material "
                    f"single-counterparty risk that should be broken "
                    f"out in the debt covenants."
                ),
                trigger_metrics=[f"payer_mix.{payer}"],
                trigger_metric=f"payer_mix.{payer}",
                trigger_value=float(frac),
                ebitda_at_risk=ear,
            ))

    commercial = float(mix.get("commercial", 0.0) or 0.0)
    if 0.0 < commercial < 0.25:
        flags.append(RiskFlag(
            category=CATEGORY_PAYER,
            severity=RiskSeverity.MEDIUM,
            title="Low commercial mix limits upside",
            detail=(
                f"Commercial mix at only {commercial*100:.1f}% limits "
                f"reimbursement upside and payer-renegotiation "
                f"leverage; value-creation plan has fewer levers."
            ),
            trigger_metrics=["payer_mix.commercial"],
            trigger_metric="payer_mix.commercial",
            trigger_value=float(commercial),
        ))

    ma_denial = _get_metric(rcm_profile, "denial_rate_medicare_advantage")
    if ma_denial is not None and ma_denial > 15.0:
        flags.append(RiskFlag(
            category=CATEGORY_PAYER,
            severity=RiskSeverity.HIGH,
            title="Medicare Advantage denial rate elevated",
            detail=(
                f"MA denial rate at {ma_denial:.1f}% — above industry "
                f"average of ~15.7%. MA plans are increasingly using "
                f"AI-powered pre-authorization and retrospective "
                f"reviews; this metric is a leading indicator."
            ),
            trigger_metrics=["denial_rate_medicare_advantage"],
            trigger_metric="denial_rate_medicare_advantage",
            trigger_value=float(ma_denial),
        ))

    return flags


def _build_coding_flags(
    rcm_profile: Dict[str, ProfileMetric],
    comparables: Optional[ComparableSet],
) -> List[RiskFlag]:
    flags: List[RiskFlag] = []

    cmi = _get_metric(rcm_profile, "case_mix_index")
    if cmi is not None:
        p25 = _cmi_comparable_p25(comparables)
        # Fall back to registry P25 when the comparable cohort is thin.
        if p25 is None:
            p25 = float(RCM_METRIC_REGISTRY["case_mix_index"].get("benchmark_p25") or 1.40)
        if cmi < p25:
            flags.append(RiskFlag(
                category=CATEGORY_CODING,
                severity=RiskSeverity.HIGH,
                title="Case Mix Index below cohort P25 — likely undercoding",
                detail=(
                    f"CMI of {cmi:.2f} is below the comparable P25 "
                    f"({p25:.2f}). Typically indicates documentation "
                    f"or CDI gaps; a structured CDI program commonly "
                    f"recovers 3-8% of Medicare revenue."
                ),
                trigger_metrics=["case_mix_index"],
                trigger_metric="case_mix_index",
                trigger_value=float(cmi),
            ))

    car = _get_metric(rcm_profile, "coding_accuracy_rate")
    if car is not None and car < 95.0:
        flags.append(RiskFlag(
            category=CATEGORY_CODING,
            severity=RiskSeverity.MEDIUM,
            title="Coding accuracy below industry bar",
            detail=(
                f"Coding accuracy rate of {car:.1f}% is below the "
                f"95% industry bar. Drives downstream denials and "
                f"compliance exposure; ask for recent audit results."
            ),
            trigger_metrics=["coding_accuracy_rate"],
            trigger_metric="coding_accuracy_rate",
            trigger_value=float(car),
        ))
    return flags


def _build_data_quality_flags(
    completeness: Optional[CompletenessAssessment],
) -> List[RiskFlag]:
    flags: List[RiskFlag] = []
    if completeness is None:
        return flags
    if completeness.grade == "D":
        flags.append(RiskFlag(
            category=CATEGORY_DATA_QUALITY,
            severity=RiskSeverity.CRITICAL,
            title="Insufficient data for reliable analysis",
            detail=(
                f"Only {completeness.coverage_pct*100:.0f}% of required "
                f"metrics are available ({completeness.observed_count}/"
                f"{completeness.total_metrics}). Core diligence "
                f"conclusions need more data before they can be "
                f"defended in IC."
            ),
            trigger_metrics=["completeness.coverage_pct"],
            trigger_metric="completeness.coverage_pct",
            trigger_value=float(completeness.coverage_pct),
        ))
    if completeness.stale_fields:
        max_age = max(
            (int(s.days_stale) for s in completeness.stale_fields),
            default=0,
        )
        flags.append(RiskFlag(
            category=CATEGORY_DATA_QUALITY,
            severity=RiskSeverity.MEDIUM,
            title="Stale data detected",
            detail=(
                f"{len(completeness.stale_fields)} metric(s) are past "
                f"their freshness threshold; oldest is {max_age} days. "
                f"Trend-based conclusions will lag reality."
            ),
            trigger_metrics=[s.metric_key for s in completeness.stale_fields],
            trigger_metric=completeness.stale_fields[0].metric_key if completeness.stale_fields else None,
            trigger_value=float(max_age),
        ))
    return flags


def _build_financial_flags(
    rcm_profile: Dict[str, ProfileMetric],
    bridge: Optional[EBITDABridgeResult],
) -> List[RiskFlag]:
    flags: List[RiskFlag] = []

    em = _get_metric(rcm_profile, "ebitda_margin")
    if em is not None and em < 5.0:
        flags.append(RiskFlag(
            category=CATEGORY_FINANCIAL,
            severity=RiskSeverity.HIGH,
            title="Thin EBITDA margin leaves no execution buffer",
            detail=(
                f"EBITDA margin of {em:.1f}% sits below the 5% "
                f"comfort line. Execution risk on the RCM plan is "
                f"the dominant variable — any miss on denials or "
                f"AR converts directly to covenant pressure."
            ),
            trigger_metrics=["ebitda_margin"],
            trigger_metric="ebitda_margin",
            trigger_value=float(em),
        ))

    # Operating margin — we don't have it as a first-class registry
    # metric, but the bridge knows current vs target EBITDA and can
    # signal the "operating at a loss" case when current_ebitda < 0.
    if bridge is not None and bridge.current_ebitda < 0:
        flags.append(RiskFlag(
            category=CATEGORY_FINANCIAL,
            severity=RiskSeverity.CRITICAL,
            title="Operating at a loss",
            detail=(
                f"Current EBITDA is negative "
                f"(${bridge.current_ebitda/1_000_000:.1f}M). RCM "
                f"improvements alone are unlikely to restore "
                f"profitability — underwriting needs a cost-out or "
                f"rate-reset storyline alongside."
            ),
            trigger_metrics=["current_ebitda"],
            trigger_metric="current_ebitda",
            trigger_value=float(bridge.current_ebitda),
        ))
    return flags


# ── Public entry point ──────────────────────────────────────────────

_SEVERITY_RANK = {
    RiskSeverity.CRITICAL: 0,
    RiskSeverity.HIGH: 1,
    RiskSeverity.MEDIUM: 2,
    RiskSeverity.LOW: 3,
}


def _build_regulatory_context_flags(
    profile: HospitalProfile,
    regulatory_context: Optional[Dict[str, Any]],
) -> List[RiskFlag]:
    """Flags driven by the static state-context registry (Prompt 24).

    Fires four flag types based on the ``RegulatoryAssessment`` the
    packet builder attaches from
    :func:`rcm_mc.data.state_regulatory.assess_regulatory`:

    - ``CON_GROWTH_CEILING`` (MEDIUM) — state has an active CON
      moratorium, limiting capacity growth.
    - ``CON_COMPETITIVE_MOAT`` (LOW / informational) — CON state
      without a moratorium; positive signal for incumbents.
    - ``MEDICAID_RATE_RISK`` (HIGH) — state Medicaid fee index <70%
      of Medicare AND Medicaid is >20% of the mix.
    - ``MARKET_CONCENTRATION`` (MEDIUM) — commercial HHI is HIGH
      and hospital has >30% commercial exposure.

    Regulatory-context flags are additive to the existing OBBBA /
    coverage-loss detector; they describe *steady-state* regulatory
    headwinds rather than a policy event.
    """
    if not regulatory_context:
        return []
    flags: List[RiskFlag] = []
    con_status = regulatory_context.get("con_status") or ""
    con_impl = regulatory_context.get("con_implication") or ""
    medicaid_risk = regulatory_context.get("medicaid_risk") or "LOW"
    market_risk = regulatory_context.get("market_risk") or "LOW"
    payer_profile = regulatory_context.get("payer_profile") or {}
    state = profile.state or regulatory_context.get("state") or ""

    if con_status == "CON_MORATORIUM" or con_impl == "growth_ceiling":
        flags.append(RiskFlag(
            category=CATEGORY_REGULATORY,
            severity=RiskSeverity.MEDIUM,
            title="CON growth ceiling",
            detail=(
                f"{state} operates an active Certificate-of-Need moratorium. "
                f"New capacity or service lines require state approval that "
                f"can take 18+ months; model growth assumptions accordingly."
            ),
            trigger_metrics=["regulatory.con_status"],
            trigger_metric="regulatory.con_status",
        ))
    elif con_status == "CON_ACTIVE" and con_impl == "competitive_moat":
        flags.append(RiskFlag(
            category=CATEGORY_REGULATORY,
            severity=RiskSeverity.LOW,
            title="CON competitive moat",
            detail=(
                f"{state} operates a CON regime — incumbents are shielded "
                f"from new entrants. Positive for existing bed value; "
                f"neutral for same-state acquirors."
            ),
            trigger_metrics=["regulatory.con_status"],
            trigger_metric="regulatory.con_status",
        ))

    if medicaid_risk == "HIGH":
        fee = float(payer_profile.get(
            "medicaid_rate_as_pct_of_medicare", 0.0,
        ) or 0.0)
        flags.append(RiskFlag(
            category=CATEGORY_REGULATORY,
            severity=RiskSeverity.HIGH,
            title="Medicaid rate compression",
            detail=(
                f"{state} Medicaid pays {fee * 100:.0f}% of Medicare "
                f"rates — significantly below the national median — and "
                f"this hospital's Medicaid exposure is material. Every "
                f"1-pp Medicaid share shift adds margin pressure."
            ),
            trigger_metrics=["regulatory.medicaid_risk",
                             "payer_mix.medicaid"],
            trigger_metric="regulatory.medicaid_risk",
        ))

    if market_risk in ("HIGH", "MEDIUM"):
        dominant = payer_profile.get("dominant_insurer") or "the dominant insurer"
        severity = (
            RiskSeverity.MEDIUM if market_risk == "HIGH"
            else RiskSeverity.LOW
        )
        flags.append(RiskFlag(
            category=CATEGORY_PAYER,
            severity=severity,
            title="Commercial market concentration",
            detail=(
                f"{state}'s commercial insurance market is concentrated; "
                f"{dominant} sets contract terms across most MSAs. Rate "
                f"negotiation upside during hold period is limited."
            ),
            trigger_metrics=["regulatory.market_risk",
                             "payer_mix.commercial"],
            trigger_metric="regulatory.market_risk",
        ))

    return flags


_CATEGORY_DATA_ANOMALY = "DATA_ANOMALY"


def _build_anomaly_flags(
    completeness: Optional[Any],
) -> List[RiskFlag]:
    """Materialize ``DATA_ANOMALY`` risk flags from the completeness
    anomalies (Prompt 28). Each anomaly becomes one flag with a
    targeted diligence prompt embedded in ``detail``."""
    if completeness is None:
        return []
    anomalies = getattr(completeness, "anomalies", None) or []
    out: List[RiskFlag] = []
    sev_map = {
        "CRITICAL": RiskSeverity.CRITICAL,
        "HIGH": RiskSeverity.HIGH,
        "MEDIUM": RiskSeverity.MEDIUM,
        "LOW": RiskSeverity.LOW,
    }
    for a in anomalies:
        metric = a.get("metric_key") or ""
        anomaly_type = a.get("anomaly_type") or "UNKNOWN"
        severity = sev_map.get(a.get("severity") or "MEDIUM", RiskSeverity.MEDIUM)
        explanation = a.get("explanation") or ""
        related = a.get("related_metrics") or []
        triggers = [f"anomaly.{metric}"] + [f"anomaly.{r}" for r in related]
        out.append(RiskFlag(
            category=_CATEGORY_DATA_ANOMALY,
            severity=severity,
            title=f"Data anomaly: {metric} ({anomaly_type.lower().replace('_', ' ')})",
            detail=(
                f"{explanation} Please confirm this figure and describe "
                f"the methodology behind the calculation."
            ),
            trigger_metrics=triggers,
            trigger_metric=metric,
        ))
    return out


def _build_trending_flags(
    metric_forecasts: Optional[Dict[str, Dict[str, Any]]],
) -> List[RiskFlag]:
    """Fire ``TRENDING_DETERIORATION`` when a per-metric temporal
    forecast shows the metric moving in the bad direction (Prompt 27).

    Severity model:
    - HIGH when p ≤ 0.05 (strong evidence) on a bridge-critical metric
      (denial_rate / days_in_ar / net_collection_rate / cost_to_collect).
    - MEDIUM on all other deteriorating trends with p ≤ 0.15.

    Uses the forecaster's labelled ``direction`` rather than raw slope
    so the metric-direction awareness (lower-is-better vs higher) is
    already baked in. No flag when direction is "stable" or
    "improving".
    """
    if not metric_forecasts:
        return []
    critical_metrics = frozenset({
        "denial_rate", "final_denial_rate", "days_in_ar",
        "net_collection_rate", "cost_to_collect",
    })
    out: List[RiskFlag] = []
    for metric_key, fdict in (metric_forecasts or {}).items():
        trend = (fdict.get("trend") or {})
        if trend.get("direction") != "deteriorating":
            continue
        p = float(trend.get("p_value_approx") or 1.0)
        slope = float(trend.get("slope_per_period") or 0.0)
        n = int(trend.get("n_periods") or 0)
        if p > 0.15 or n < 3:
            continue
        severity = (
            RiskSeverity.HIGH if p <= 0.05 and metric_key in critical_metrics
            else RiskSeverity.MEDIUM
        )
        forecasted = fdict.get("forecasted") or []
        projection = ""
        if forecasted:
            last = forecasted[-1]
            projection = (
                f" Projection: {last.get('value', 0):.2f} at "
                f"{last.get('period') or 'end of horizon'}."
            )
        out.append(RiskFlag(
            category=CATEGORY_OPERATIONAL,
            severity=severity,
            title=f"{metric_key} trending deterioration",
            detail=(
                f"{metric_key} is deteriorating at "
                f"{slope:+.3f}/period over {n} periods "
                f"(p≈{p:.2f}).{projection}"
            ),
            trigger_metrics=[f"forecast.{metric_key}"],
            trigger_metric=metric_key,
            trigger_value=float(slope),
        ))
    return out


def assess_risks(
    profile: HospitalProfile,
    rcm_profile: Dict[str, ProfileMetric],
    comparables: Optional[ComparableSet] = None,
    ebitda_bridge: Optional[EBITDABridgeResult] = None,
    *,
    completeness: Optional[CompletenessAssessment] = None,
    regulatory_context: Optional[Dict[str, Any]] = None,
    metric_forecasts: Optional[Dict[str, Dict[str, Any]]] = None,
) -> List[RiskFlag]:
    """Run all eight risk detectors and return a severity-sorted list.

    ``completeness`` is kept as a keyword arg so the caller can pass
    the section that the builder computed in step 3; without it the
    data-quality detector is a no-op. ``regulatory_context`` (Prompt
    24) drives CON / Medicaid-rate / market-concentration detectors.
    ``metric_forecasts`` (Prompt 27) drives
    ``TRENDING_DETERIORATION``.
    """
    flags: List[RiskFlag] = []
    flags.extend(_build_operational_flags(rcm_profile, comparables, ebitda_bridge))
    flags.extend(_build_regulatory_flags(profile, rcm_profile))
    flags.extend(_build_regulatory_context_flags(profile, regulatory_context))
    flags.extend(_build_payer_flags(profile, rcm_profile, ebitda_bridge))
    flags.extend(_build_coding_flags(rcm_profile, comparables))
    flags.extend(_build_data_quality_flags(completeness))
    flags.extend(_build_financial_flags(rcm_profile, ebitda_bridge))
    flags.extend(_build_trending_flags(metric_forecasts))
    flags.extend(_build_anomaly_flags(completeness))
    flags.sort(key=lambda f: (_SEVERITY_RANK.get(f.severity, 9), f.category))
    return flags
