"""Orchestrator for the Predictive Physician Attrition Model.

Takes a provider roster + optional per-provider metadata and
produces an :class:`AttritionReport` that:

    - scores each provider's flight-risk probability
    - bands each provider (LOW / MEDIUM / HIGH / CRITICAL)
    - computes roster-level EBITDA-at-risk from the expected
      collections lost to attrition
    - emits per-provider retention recommendations
    - produces a bridge-lever input for the physician-retention
      row in the EBITDA bridge / Deal MC physician_attrition_pct

The bridge input is the key integration artifact: it turns
"physician attrition" from a hand-entered Deal MC parameter into
a data-driven per-provider sum.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from ..physician_comp.comp_ingester import Provider
from ..physician_comp.stark_aks_red_line import (
    check_stark_redline,
)
from .features import AttritionFeatures, extract_features
from .model import (
    DEFAULT_COEFFICIENTS, DEFAULT_INTERCEPT, FlightRiskBand,
    band_for, feature_contributions, flight_risk_probability,
)


# ────────────────────────────────────────────────────────────────────
# Retention recommendations — keyed off the band
# ────────────────────────────────────────────────────────────────────

_RECOMMENDATIONS: Dict[FlightRiskBand, str] = {
    FlightRiskBand.CRITICAL: (
        "Retention bond required pre-close. Do not close the deal "
        "without a 2-3 year retention agreement carrying a "
        "meaningful lockup (typically 25–50% of comp held escrow)."
    ),
    FlightRiskBand.HIGH: (
        "Earn-out structure must include retention milestone. "
        "Tie a portion of seller consideration to the provider "
        "staying through year-2."
    ),
    FlightRiskBand.MEDIUM: (
        "Monitor post-close. No structural change required at "
        "signing; include in the 100-day engagement plan."
    ),
    FlightRiskBand.LOW: (
        "Stable — no specific retention action required."
    ),
}


@dataclass
class RetentionRecommendation:
    """Per-provider retention advice the partner can action."""
    provider_id: str
    band: FlightRiskBand
    recommendation: str
    suggested_bond_usd: Optional[float] = None  # sized off comp
    retention_years: Optional[int] = None


@dataclass
class ProviderAttritionScore:
    """Per-provider score + explanation."""
    provider_id: str
    npi: Optional[str]
    specialty: str
    probability: float
    band: FlightRiskBand
    features: AttritionFeatures
    collections_annual_usd: float
    expected_collections_at_risk_usd: float   # prob × collections
    top_drivers: List[str]                    # ordered list of feature names
    contributions: Dict[str, float]           # β·x per feature (log-odds)
    recommendation: RetentionRecommendation

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "npi": self.npi,
            "specialty": self.specialty,
            "probability": self.probability,
            "band": self.band.value,
            "features": self.features.to_dict(),
            "collections_annual_usd": self.collections_annual_usd,
            "expected_collections_at_risk_usd":
                self.expected_collections_at_risk_usd,
            "top_drivers": self.top_drivers,
            "contributions": dict(self.contributions),
            "recommendation": {
                "band": self.recommendation.band.value,
                "recommendation": self.recommendation.recommendation,
                "suggested_bond_usd":
                    self.recommendation.suggested_bond_usd,
                "retention_years": self.recommendation.retention_years,
            },
        }


@dataclass
class BridgeLeverInput:
    """Physician-retention line for the EBITDA bridge.

    ``ebitda_at_risk_usd`` = sum of per-provider expected
    collections lost × EBITDA-margin assumption (default 15% for
    physician-group deals).  The Deal MC converts this into the
    ``physician_attrition_pct`` driver.
    """
    ebitda_at_risk_usd: float
    expected_collections_lost_usd: float
    ebitda_margin_assumed: float
    attrition_pct_of_collections: float
    confidence: str = "MEDIUM"                # LOW / MEDIUM / HIGH
    realization_probability: float = 0.60     # fraction of at-risk
                                              # collections actually
                                              # lost over the 18-month
                                              # horizon given a
                                              # standard earn-out
                                              # structure

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


@dataclass
class AttritionReport:
    """Roster-level output surface."""
    scores: List[ProviderAttritionScore] = field(default_factory=list)
    roster_size: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    total_collections_usd: float = 0.0
    total_expected_collections_at_risk_usd: float = 0.0
    top_at_risk_contributors_pct_of_roster: float = 0.0
    # Bridge-lever output
    bridge_input: Optional[BridgeLeverInput] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "roster_size": self.roster_size,
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "medium_count": self.medium_count,
            "low_count": self.low_count,
            "total_collections_usd": self.total_collections_usd,
            "total_expected_collections_at_risk_usd":
                self.total_expected_collections_at_risk_usd,
            "top_at_risk_contributors_pct_of_roster":
                self.top_at_risk_contributors_pct_of_roster,
            "scores": [s.to_dict() for s in self.scores],
            "bridge_input":
                self.bridge_input.to_dict() if self.bridge_input else None,
        }

    @property
    def high_or_critical_scores(self) -> List[ProviderAttritionScore]:
        """Providers that typically need structural retention action."""
        return [
            s for s in self.scores
            if s.band in (FlightRiskBand.HIGH, FlightRiskBand.CRITICAL)
        ]


# ────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────

def _top_driver_names(
    contributions: Dict[str, float], k: int = 3,
) -> List[str]:
    """Return the top-k feature names by positive contribution."""
    items = [
        (name, val) for name, val in contributions.items()
        if name != "intercept" and val > 0
    ]
    items.sort(key=lambda t: t[1], reverse=True)
    return [t[0] for t in items[:k]]


def _suggest_bond_usd(
    provider: Provider, band: FlightRiskBand,
) -> Optional[float]:
    """Partner-facing bond sizing:

    - CRITICAL: 40% of total comp
    - HIGH    : 25% of total comp
    - MEDIUM  : none (monitoring only)
    - LOW     : none
    """
    if band == FlightRiskBand.CRITICAL:
        return round(provider.total_comp_usd * 0.40, -3)
    if band == FlightRiskBand.HIGH:
        return round(provider.total_comp_usd * 0.25, -3)
    return None


def _retention_years(band: FlightRiskBand) -> Optional[int]:
    if band == FlightRiskBand.CRITICAL:
        return 3
    if band == FlightRiskBand.HIGH:
        return 2
    return None


def _recommendation_for(
    provider: Provider, band: FlightRiskBand,
) -> RetentionRecommendation:
    return RetentionRecommendation(
        provider_id=provider.provider_id,
        band=band,
        recommendation=_RECOMMENDATIONS[band],
        suggested_bond_usd=_suggest_bond_usd(provider, band),
        retention_years=_retention_years(band),
    )


def _confidence_band(n_providers: int, any_stark: bool) -> str:
    if n_providers < 10:
        return "LOW"
    if n_providers < 30 or not any_stark:
        return "MEDIUM"
    return "HIGH"


# ────────────────────────────────────────────────────────────────────
# Public entry
# ────────────────────────────────────────────────────────────────────

def analyze_roster(
    providers: Sequence[Provider],
    *,
    years_at_facility: Optional[Dict[str, float]] = None,
    ages: Optional[Dict[str, float]] = None,
    yoy_collections_slopes: Optional[Dict[str, float]] = None,
    local_competitors: Optional[int] = None,
    ownership_type: str = "independent",
    ebitda_margin: float = 0.15,
    realization_probability: float = 0.60,
) -> AttritionReport:
    """Run the full attrition analysis against a roster.

    Per-provider maps (``years_at_facility``, ``ages``,
    ``yoy_collections_slopes``) are keyed off ``provider_id``.
    Missing entries default to neutral priors (see features.py).
    """
    years_at_facility = dict(years_at_facility or {})
    ages = dict(ages or {})
    yoy_collections_slopes = dict(yoy_collections_slopes or {})

    providers = list(providers)
    roster_size = len(providers)
    if roster_size == 0:
        return AttritionReport()

    total_collections = sum(
        max(0.0, float(p.collections_annual_usd or 0))
        for p in providers
    )

    # Stark overlap set — keyed by provider_id
    try:
        stark_findings = check_stark_redline(providers)
    except Exception:  # noqa: BLE001
        stark_findings = []
    stark_ids = {getattr(f, "provider_id", None) for f in stark_findings}
    stark_ids.discard(None)

    scores: List[ProviderAttritionScore] = []
    counts = {
        FlightRiskBand.CRITICAL: 0,
        FlightRiskBand.HIGH: 0,
        FlightRiskBand.MEDIUM: 0,
        FlightRiskBand.LOW: 0,
    }
    total_at_risk = 0.0

    for p in providers:
        feats = extract_features(
            p,
            years_at_facility=years_at_facility.get(p.provider_id),
            age_years=ages.get(p.provider_id),
            yoy_collections_slope=yoy_collections_slopes.get(p.provider_id),
            local_competitors=local_competitors,
            roster_size=roster_size,
            roster_collections_total=total_collections,
            has_stark_overlap=(p.provider_id in stark_ids),
            ownership_type=ownership_type,
        )
        prob = flight_risk_probability(feats)
        band = band_for(prob)
        counts[band] += 1

        coll = max(0.0, float(p.collections_annual_usd or 0))
        at_risk = prob * coll
        total_at_risk += at_risk

        contribs = feature_contributions(feats)
        scores.append(ProviderAttritionScore(
            provider_id=p.provider_id,
            npi=p.npi,
            specialty=p.specialty,
            probability=prob,
            band=band,
            features=feats,
            collections_annual_usd=coll,
            expected_collections_at_risk_usd=at_risk,
            top_drivers=_top_driver_names(contribs, k=3),
            contributions=contribs,
            recommendation=_recommendation_for(p, band),
        ))

    # Sort scores descending by expected $ at risk (partners read
    # this way — concentration matters as much as probability).
    scores.sort(
        key=lambda s: s.expected_collections_at_risk_usd, reverse=True,
    )

    # "Top 20%" concentration: what share of total at-risk comes
    # from the top 20% of providers?
    if scores:
        top_n = max(1, int(len(scores) * 0.20))
        top_at_risk = sum(
            s.expected_collections_at_risk_usd for s in scores[:top_n]
        )
        top_share = (
            top_at_risk / total_at_risk
            if total_at_risk > 0 else 0.0
        )
    else:
        top_share = 0.0

    # Bridge lever
    realized_lost = total_at_risk * realization_probability
    bridge_input = BridgeLeverInput(
        ebitda_at_risk_usd=realized_lost * ebitda_margin,
        expected_collections_lost_usd=realized_lost,
        ebitda_margin_assumed=ebitda_margin,
        attrition_pct_of_collections=(
            realized_lost / total_collections
            if total_collections > 0 else 0.0
        ),
        confidence=_confidence_band(roster_size, bool(stark_ids)),
        realization_probability=realization_probability,
    )

    return AttritionReport(
        scores=scores,
        roster_size=roster_size,
        critical_count=counts[FlightRiskBand.CRITICAL],
        high_count=counts[FlightRiskBand.HIGH],
        medium_count=counts[FlightRiskBand.MEDIUM],
        low_count=counts[FlightRiskBand.LOW],
        total_collections_usd=total_collections,
        total_expected_collections_at_risk_usd=total_at_risk,
        top_at_risk_contributors_pct_of_roster=top_share,
        bridge_input=bridge_input,
    )
