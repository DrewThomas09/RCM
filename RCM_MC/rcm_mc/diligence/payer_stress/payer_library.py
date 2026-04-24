"""Curated US healthcare payer directory with rate-movement behavior.

Every PE healthcare deal lives or dies on its commercial payer
mix. A target with 40% concentration in a single payer that has
a 2-year expiring contract and a history of aggressive
repricing is structurally fragile — even with perfect RCM
execution. Traditional diligence tools name the payers but
don't quantify the dynamic rate-movement risk.

This module ships a curated directory of ~25 major US payers
with:

    * **Historical rate movement** — median / p25 / p75 of
      contracted rate adjustments on renewal events, drawn from
      sector surveys (HFMA, MGMA, AHA annual reports) and
      published 10-K commentary from public comps (HCA / THC
      disclose payer-specific rate movements).
    * **Negotiating leverage score** (0-1) — how much power the
      payer has vs a mid-sized provider. High = UnitedHealth,
      Blues in their home state. Low = smaller MA plans,
      exchange carriers.
    * **Contract cycle months** — typical renewal cadence.
    * **Churn / non-renewal risk** — probability of termination
      rather than renegotiation.
    * **Geographic concentration** — states where the payer has
      significant market share, used for weighting.

The simulator consumes these priors + the target's claimed payer
mix to produce a per-payer rate-shock distribution and a
concentrated-risk-adjusted NPR path.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Mapping, Optional, Tuple


class PayerCategory(str, Enum):
    COMMERCIAL_NATIONAL = "COMMERCIAL_NATIONAL"      # UHC, Aetna, Cigna
    COMMERCIAL_REGIONAL = "COMMERCIAL_REGIONAL"      # BCBS state plans
    MEDICARE_ADVANTAGE = "MEDICARE_ADVANTAGE"
    MEDICARE_FFS = "MEDICARE_FFS"
    MEDICAID_MANAGED = "MEDICAID_MANAGED"
    MEDICAID_FFS = "MEDICAID_FFS"
    TRICARE = "TRICARE"
    VA = "VA"
    WORKERS_COMP = "WORKERS_COMP"
    SELF_PAY = "SELF_PAY"


@dataclass(frozen=True)
class PayerPrior:
    """Empirical rate-behavior prior for one payer."""
    payer_id: str
    name: str
    category: PayerCategory
    # Rate movement distribution (fraction, signed — positive = increase)
    rate_move_median: float              # e.g. 0.015 = +1.5% typical renewal
    rate_move_p25: float                  # downside tail
    rate_move_p75: float                  # upside tail
    # Probability a renewal event fires in the next 12 months
    renewal_prob_12mo: float = 0.33
    # Negotiating leverage vs a mid-sized provider (0 = weak payer, 1 = dominant)
    negotiating_leverage: float = 0.5
    # Probability that a negotiation ends in termination (non-renewal)
    churn_prob: float = 0.05
    # States where the payer has meaningful market share
    dominant_states: Tuple[str, ...] = ()
    # Specialty-specific behavior tags
    behavior_notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "payer_id": self.payer_id,
            "name": self.name,
            "category": self.category.value,
            "rate_move_median": self.rate_move_median,
            "rate_move_p25": self.rate_move_p25,
            "rate_move_p75": self.rate_move_p75,
            "renewal_prob_12mo": self.renewal_prob_12mo,
            "negotiating_leverage": self.negotiating_leverage,
            "churn_prob": self.churn_prob,
            "dominant_states": list(self.dominant_states),
            "behavior_notes": self.behavior_notes,
        }


# ────────────────────────────────────────────────────────────────────
# Curated directory
# ────────────────────────────────────────────────────────────────────

PAYER_PRIORS: Tuple[PayerPrior, ...] = (
    # ─── National commercial — top leverage, aggressive repricing ──
    PayerPrior(
        payer_id="UHC",
        name="UnitedHealthcare",
        category=PayerCategory.COMMERCIAL_NATIONAL,
        rate_move_median=0.015, rate_move_p25=-0.045,
        rate_move_p75=0.055, renewal_prob_12mo=0.35,
        negotiating_leverage=0.92, churn_prob=0.08,
        behavior_notes=(
            "Most aggressive repricing counterparty in US "
            "healthcare. Uses Change Healthcare / Optum data to "
            "drive evidence-based rate cuts on hospital "
            "outliers. Recent 2024-2025 trend: −3 to −5% on "
            "renewals where provider's CMI is below peer median."
        ),
    ),
    PayerPrior(
        payer_id="ANTHEM",
        name="Anthem (Elevance Health)",
        category=PayerCategory.COMMERCIAL_NATIONAL,
        rate_move_median=0.020, rate_move_p25=-0.025,
        rate_move_p75=0.055, renewal_prob_12mo=0.33,
        negotiating_leverage=0.88,
        dominant_states=(
            "CA", "IN", "OH", "KY", "NY", "VA", "CO", "GA",
        ),
        behavior_notes=(
            "Dominant in 14 Blues states. Less aggressive than "
            "UHC on rate cuts but slower on annual escalators."
        ),
    ),
    PayerPrior(
        payer_id="AETNA",
        name="Aetna (CVS Health)",
        category=PayerCategory.COMMERCIAL_NATIONAL,
        rate_move_median=0.025, rate_move_p25=-0.020,
        rate_move_p75=0.060, renewal_prob_12mo=0.30,
        negotiating_leverage=0.78, churn_prob=0.06,
        behavior_notes=(
            "Moderately aggressive. Integration with CVS "
            "formulary creates leverage in MA/Part D tiers."
        ),
    ),
    PayerPrior(
        payer_id="CIGNA",
        name="Cigna",
        category=PayerCategory.COMMERCIAL_NATIONAL,
        rate_move_median=0.022, rate_move_p25=-0.015,
        rate_move_p75=0.055, renewal_prob_12mo=0.32,
        negotiating_leverage=0.72, churn_prob=0.05,
        behavior_notes=(
            "Weaker pricing leverage in hospital contracting; "
            "stronger in ASC / outpatient. Preferred network "
            "positioning drives volume over rate."
        ),
    ),
    PayerPrior(
        payer_id="HUMANA",
        name="Humana",
        category=PayerCategory.COMMERCIAL_NATIONAL,
        rate_move_median=0.018, rate_move_p25=-0.030,
        rate_move_p75=0.045, renewal_prob_12mo=0.28,
        negotiating_leverage=0.70, churn_prob=0.07,
        behavior_notes=(
            "MA-heavy focus. Commercial book small and "
            "declining; renegotiation pressure mostly on MA "
            "capitation arrangements."
        ),
    ),
    # ─── Regional Blues plans — strong local leverage ──────────
    PayerPrior(
        payer_id="BCBS_IL",
        name="BCBS Illinois (HCSC)",
        category=PayerCategory.COMMERCIAL_REGIONAL,
        rate_move_median=0.025, rate_move_p25=-0.010,
        rate_move_p75=0.050, renewal_prob_12mo=0.30,
        negotiating_leverage=0.90, churn_prob=0.03,
        dominant_states=("IL", "TX", "OK", "NM", "MT"),
        behavior_notes=(
            "HCSC operates BCBS plans in 5 states with ~50% "
            "market share in each. Near-monopsony pricing power."
        ),
    ),
    PayerPrior(
        payer_id="BCBS_MI",
        name="Blue Cross Blue Shield of Michigan",
        category=PayerCategory.COMMERCIAL_REGIONAL,
        rate_move_median=0.020, rate_move_p25=-0.015,
        rate_move_p75=0.045, renewal_prob_12mo=0.30,
        negotiating_leverage=0.88, churn_prob=0.03,
        dominant_states=("MI",),
    ),
    PayerPrior(
        payer_id="BCBS_NC",
        name="Blue Cross Blue Shield of North Carolina",
        category=PayerCategory.COMMERCIAL_REGIONAL,
        rate_move_median=0.022, rate_move_p25=-0.020,
        rate_move_p75=0.050, renewal_prob_12mo=0.30,
        negotiating_leverage=0.85, churn_prob=0.04,
        dominant_states=("NC",),
    ),
    PayerPrior(
        payer_id="HIGHMARK",
        name="Highmark (BCBS PA/WV/DE/NY)",
        category=PayerCategory.COMMERCIAL_REGIONAL,
        rate_move_median=0.020, rate_move_p25=-0.015,
        rate_move_p75=0.045, renewal_prob_12mo=0.30,
        negotiating_leverage=0.85,
        dominant_states=("PA", "WV", "DE", "NY"),
    ),
    PayerPrior(
        payer_id="BCBS_CA",
        name="Blue Shield of California",
        category=PayerCategory.COMMERCIAL_REGIONAL,
        rate_move_median=0.020, rate_move_p25=-0.025,
        rate_move_p75=0.045, renewal_prob_12mo=0.30,
        negotiating_leverage=0.80, churn_prob=0.04,
        dominant_states=("CA",),
    ),
    PayerPrior(
        payer_id="KAISER",
        name="Kaiser Permanente",
        category=PayerCategory.COMMERCIAL_REGIONAL,
        rate_move_median=0.015, rate_move_p25=-0.015,
        rate_move_p75=0.040, renewal_prob_12mo=0.25,
        negotiating_leverage=0.95, churn_prob=0.12,
        dominant_states=("CA", "CO", "GA", "HI", "OR", "WA", "MD"),
        behavior_notes=(
            "Integrated delivery + payer — contracts with "
            "external providers are narrow-network carve-outs. "
            "High churn when Kaiser internalizes service lines."
        ),
    ),
    # ─── Medicare / Medicare Advantage ──────────────────────────
    PayerPrior(
        payer_id="MEDICARE_FFS",
        name="Medicare Fee-for-Service",
        category=PayerCategory.MEDICARE_FFS,
        rate_move_median=0.023, rate_move_p25=0.005,
        rate_move_p75=0.040, renewal_prob_12mo=1.0,
        negotiating_leverage=1.0, churn_prob=0.0,
        behavior_notes=(
            "Annual CMS rate update. Provider has no "
            "negotiation; rate is published. Directional tail-"
            "wind at +2-4%/yr but subject to site-neutral + "
            "sequester + other policy cuts."
        ),
    ),
    PayerPrior(
        payer_id="MA_AGGREGATE",
        name="Medicare Advantage (aggregated)",
        category=PayerCategory.MEDICARE_ADVANTAGE,
        rate_move_median=0.015, rate_move_p25=-0.035,
        rate_move_p75=0.045, renewal_prob_12mo=0.40,
        negotiating_leverage=0.75, churn_prob=0.10,
        behavior_notes=(
            "MA plans negotiate independently per geography. "
            "V28 HCC recalibration is a structural compression "
            "factor 2026-2028. Capitation contracts more "
            "volatile than FFS-equivalent."
        ),
    ),
    # ─── Medicaid ───────────────────────────────────────────────
    PayerPrior(
        payer_id="MEDICAID_FFS",
        name="Medicaid Fee-for-Service",
        category=PayerCategory.MEDICAID_FFS,
        rate_move_median=0.012, rate_move_p25=-0.020,
        rate_move_p75=0.040, renewal_prob_12mo=1.0,
        negotiating_leverage=1.0, churn_prob=0.0,
        behavior_notes=(
            "State-set rates; provider has no leverage. Budget "
            "cycles drive volatility — mid-cycle rate cuts "
            "possible in deficit states."
        ),
    ),
    PayerPrior(
        payer_id="CENTENE",
        name="Centene (Medicaid managed care)",
        category=PayerCategory.MEDICAID_MANAGED,
        rate_move_median=0.010, rate_move_p25=-0.040,
        rate_move_p75=0.035, renewal_prob_12mo=0.35,
        negotiating_leverage=0.72, churn_prob=0.08,
        behavior_notes=(
            "Largest Medicaid managed-care plan by lives. "
            "Contract terms pass through state rate cuts to "
            "providers with lag."
        ),
    ),
    PayerPrior(
        payer_id="MOLINA",
        name="Molina Healthcare",
        category=PayerCategory.MEDICAID_MANAGED,
        rate_move_median=0.008, rate_move_p25=-0.035,
        rate_move_p75=0.030, renewal_prob_12mo=0.33,
        negotiating_leverage=0.65, churn_prob=0.10,
    ),
    # ─── Government / specialty ────────────────────────────────
    PayerPrior(
        payer_id="TRICARE",
        name="TRICARE",
        category=PayerCategory.TRICARE,
        rate_move_median=0.020, rate_move_p25=0.005,
        rate_move_p75=0.035, renewal_prob_12mo=1.0,
        negotiating_leverage=1.0, churn_prob=0.0,
        behavior_notes=(
            "Defense Health Agency contracted rates; indexed "
            "to Medicare with some Tricare-specific adjusters."
        ),
    ),
    PayerPrior(
        payer_id="WORKERS_COMP",
        name="Workers' Compensation (aggregated)",
        category=PayerCategory.WORKERS_COMP,
        rate_move_median=0.025, rate_move_p25=-0.010,
        rate_move_p75=0.055, renewal_prob_12mo=0.40,
        negotiating_leverage=0.55, churn_prob=0.08,
        behavior_notes=(
            "Fee-schedule driven by state regulations; "
            "negotiation leverage limited. Typically 3-5% of "
            "NPR for hospitals."
        ),
    ),
    PayerPrior(
        payer_id="SELF_PAY",
        name="Self-pay / uninsured",
        category=PayerCategory.SELF_PAY,
        rate_move_median=0.000, rate_move_p25=-0.050,
        rate_move_p75=0.040, renewal_prob_12mo=1.0,
        negotiating_leverage=0.15, churn_prob=0.0,
        behavior_notes=(
            "Realized rate driven by charity-care policy + "
            "bad-debt dynamics, not contracts. Model as "
            "collection-rate volatility, not rate moves."
        ),
    ),
)


def list_payers(
    category: Optional[PayerCategory] = None,
) -> List[PayerPrior]:
    """Return curated payers, optionally filtered by category."""
    if category is None:
        return list(PAYER_PRIORS)
    return [p for p in PAYER_PRIORS if p.category == category]


def get_payer(payer_id: str) -> Optional[PayerPrior]:
    """Lookup one payer by id.  Returns None if not found."""
    for p in PAYER_PRIORS:
        if p.payer_id.upper() == (payer_id or "").upper():
            return p
    return None


# ────────────────────────────────────────────────────────────────────
# Classifier — maps free-text payer names → PayerPrior via lookup
# ────────────────────────────────────────────────────────────────────

_NAME_ALIASES: Dict[str, str] = {
    "united": "UHC",
    "unitedhealthcare": "UHC",
    "united healthcare": "UHC",
    "optum": "UHC",
    "anthem": "ANTHEM",
    "elevance": "ANTHEM",
    "aetna": "AETNA",
    "cvs": "AETNA",
    "cigna": "CIGNA",
    "humana": "HUMANA",
    "bcbs illinois": "BCBS_IL",
    "bcbs il": "BCBS_IL",
    "hcsc": "BCBS_IL",
    "bcbs michigan": "BCBS_MI",
    "bcbs mi": "BCBS_MI",
    "bcbs north carolina": "BCBS_NC",
    "bcbs nc": "BCBS_NC",
    "highmark": "HIGHMARK",
    "blue shield of california": "BCBS_CA",
    "bcbs ca": "BCBS_CA",
    "kaiser": "KAISER",
    "medicare": "MEDICARE_FFS",
    "medicare advantage": "MA_AGGREGATE",
    "medicaid": "MEDICAID_FFS",
    "centene": "CENTENE",
    "ambetter": "CENTENE",
    "molina": "MOLINA",
    "tricare": "TRICARE",
    "workers comp": "WORKERS_COMP",
    "workers compensation": "WORKERS_COMP",
    "self pay": "SELF_PAY",
    "self-pay": "SELF_PAY",
    "uninsured": "SELF_PAY",
}


def classify_payer(name: str) -> Optional[PayerPrior]:
    """Keyword-based classifier.  Falls back to None when no
    alias matches — caller can assign OTHER / uncategorized
    treatment."""
    low = (name or "").lower().strip()
    if not low:
        return None
    # Exact id match first
    direct = get_payer(name)
    if direct is not None:
        return direct
    # Fuzzy alias match (longest-wins)
    candidates: List[Tuple[int, str]] = []
    for alias, pid in _NAME_ALIASES.items():
        if alias in low:
            candidates.append((len(alias), pid))
    if candidates:
        candidates.sort(reverse=True)
        return get_payer(candidates[0][1])
    return None
