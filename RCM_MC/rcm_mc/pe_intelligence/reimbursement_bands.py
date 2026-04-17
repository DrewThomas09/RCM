"""Reimbursement bands — payer-rate growth and gross-to-net ranges.

Partners apply sanity checks to stated payer-rate assumptions:

- Medicare rate growth: typically tracks MarketBasket minus
  productivity, net ~1.5-2.5%. Above 3% is implausible.
- Medicaid: typically flat to +2% nationally, state-dependent.
- Commercial: 3-5% is typical; above 8% requires a named re-
  contracting story.
- Gross-to-net ratio: payer-specific ranges for what a hospital
  actually collects vs its chargemaster.
- Rate parity (site-neutral): ratio of HOPD rates to equivalent
  ASC / physician-office rates.

Each check uses `BandCheck` for uniformity with `reasonableness.py`.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .reasonableness import (
    Band,
    BandCheck,
    VERDICT_IMPLAUSIBLE,
    VERDICT_IN_BAND,
    VERDICT_OUT_OF_BAND,
    VERDICT_STRETCH,
    VERDICT_UNKNOWN,
)


# ── Payer rate-growth bands ────────────────────────────────────────

_PAYER_GROWTH_BANDS: Dict[str, Band] = {
    "medicare": Band(
        metric="rate_growth", regime="medicare",
        low=0.015, high=0.025, stretch_high=0.030, implausible_high=0.045,
        implausible_low=-0.02,
        source="CMS MarketBasket historical",
    ),
    "medicaid": Band(
        metric="rate_growth", regime="medicaid",
        low=0.00, high=0.025, stretch_high=0.035, implausible_high=0.05,
        implausible_low=-0.04,
        source="State Medicaid rate review panels",
    ),
    "commercial": Band(
        metric="rate_growth", regime="commercial",
        low=0.03, high=0.055, stretch_high=0.07, implausible_high=0.10,
        implausible_low=0.0,
        source="Commercial contract renegotiation observations",
    ),
}


def check_payer_rate_growth(
    growth: Optional[float], *, payer: str,
) -> BandCheck:
    """Classify a payer-rate-growth assumption against peer norms."""
    if growth is None:
        return BandCheck(
            metric=f"rate_growth:{payer}",
            observed=None, verdict=VERDICT_UNKNOWN,
            rationale="Rate growth not reported.",
        )
    key = (payer or "").lower().strip()
    band = _PAYER_GROWTH_BANDS.get(key)
    if band is None:
        return BandCheck(
            metric=f"rate_growth:{payer}",
            observed=growth, verdict=VERDICT_UNKNOWN,
            rationale=f"No band registered for '{payer}'.",
        )
    verdict = band.classify(growth)
    pct = f"{growth*100:.1f}%"
    hi = f"{band.high*100:.1f}%"
    lo = f"{band.low*100:.1f}%"
    if verdict == VERDICT_IN_BAND:
        note = "Rate growth within peer band."
    elif verdict == VERDICT_STRETCH:
        note = f"Rate growth above {band.regime} peer ceiling ({hi})."
    elif verdict == VERDICT_OUT_OF_BAND:
        note = f"Rate growth outside defensible {band.regime} range."
    elif verdict == VERDICT_IMPLAUSIBLE:
        note = f"Rate growth implausible for {band.regime}."
    else:
        note = ""
    return BandCheck(
        metric=f"rate_growth:{payer}",
        observed=growth, verdict=verdict, band=band,
        rationale=f"{pct} rate growth vs {band.regime} peer band {lo}-{hi}.",
        partner_note=note,
    )


# ── Gross-to-net bands (collection ratio) ──────────────────────────

_GTN_BANDS: Dict[str, Band] = {
    "medicare": Band(
        metric="gross_to_net", regime="medicare",
        low=0.28, high=0.42, stretch_high=0.50, implausible_high=0.65,
        implausible_low=0.18,
        source="CMS IPPS / OPPS reimbursement rates",
    ),
    "medicaid": Band(
        metric="gross_to_net", regime="medicaid",
        low=0.22, high=0.38, stretch_high=0.45, implausible_high=0.55,
        implausible_low=0.12,
        source="State Medicaid fee schedules",
    ),
    "commercial": Band(
        metric="gross_to_net", regime="commercial",
        low=0.40, high=0.65, stretch_high=0.75, implausible_high=0.88,
        implausible_low=0.25,
        source="Commercial contract-rate observations",
    ),
}


def check_gross_to_net(
    ratio: Optional[float], *, payer: str,
) -> BandCheck:
    """Classify a stated gross-to-net collection ratio for a payer."""
    if ratio is None:
        return BandCheck(
            metric=f"gross_to_net:{payer}",
            observed=None, verdict=VERDICT_UNKNOWN,
            rationale="Gross-to-net ratio not reported.",
        )
    key = (payer or "").lower().strip()
    band = _GTN_BANDS.get(key)
    if band is None:
        return BandCheck(
            metric=f"gross_to_net:{payer}",
            observed=ratio, verdict=VERDICT_UNKNOWN,
            rationale=f"No gross-to-net band for '{payer}'.",
        )
    verdict = band.classify(ratio)
    pct = f"{ratio*100:.1f}%"
    note_map = {
        VERDICT_IN_BAND: "Gross-to-net in peer range.",
        VERDICT_STRETCH: "Above-peer collection — verify contract terms.",
        VERDICT_OUT_OF_BAND: "Off-peer collection — chargemaster or "
                             "payer-mix explanation needed.",
        VERDICT_IMPLAUSIBLE: "Gross-to-net implausible — confirm the "
                             "numerator/denominator definition.",
        VERDICT_UNKNOWN: "",
    }
    return BandCheck(
        metric=f"gross_to_net:{payer}",
        observed=ratio, verdict=verdict, band=band,
        rationale=f"{pct} gross-to-net vs {band.regime} peer band "
                  f"{band.low*100:.0f}%-{band.high*100:.0f}%.",
        partner_note=note_map.get(verdict, ""),
    )


# ── Site-neutral rate parity (HOPD vs ASC / office) ────────────────

_SITE_NEUTRAL_BAND = Band(
    metric="hopd_to_asc_parity", regime="site-neutral",
    low=1.20, high=1.60, stretch_high=1.85, implausible_high=2.30,
    implausible_low=0.90,
    source="CMS OPPS/ASC comparative analysis",
)


def check_site_neutral_parity(ratio: Optional[float]) -> BandCheck:
    """HOPD-to-ASC rate ratio. Values too high signal exposure to
    future site-neutral policy compression."""
    if ratio is None:
        return BandCheck(
            metric="hopd_to_asc_parity",
            observed=None, verdict=VERDICT_UNKNOWN,
            rationale="HOPD-to-ASC rate ratio not reported.",
        )
    verdict = _SITE_NEUTRAL_BAND.classify(ratio)
    note_map = {
        VERDICT_IN_BAND: "HOPD / ASC parity typical — moderate policy exposure.",
        VERDICT_STRETCH: "High HOPD premium — expect site-neutral compression.",
        VERDICT_OUT_OF_BAND: "HOPD premium implausibly high or too low.",
        VERDICT_IMPLAUSIBLE: "Review the numerator/denominator definition.",
        VERDICT_UNKNOWN: "",
    }
    return BandCheck(
        metric="hopd_to_asc_parity",
        observed=ratio, verdict=verdict, band=_SITE_NEUTRAL_BAND,
        rationale=(f"HOPD/ASC ratio {ratio:.2f}x vs peer "
                   f"{_SITE_NEUTRAL_BAND.low:.2f}-{_SITE_NEUTRAL_BAND.high:.2f}."),
        partner_note=note_map.get(verdict, ""),
    )


# ── Orchestrator ───────────────────────────────────────────────────

def run_reimbursement_bands(
    *,
    payer_rate_growths: Optional[Dict[str, float]] = None,
    gross_to_net_ratios: Optional[Dict[str, float]] = None,
    hopd_asc_parity: Optional[float] = None,
) -> List[BandCheck]:
    """Run every reimbursement band check that has inputs."""
    out: List[BandCheck] = []
    for payer, growth in (payer_rate_growths or {}).items():
        out.append(check_payer_rate_growth(growth, payer=payer))
    for payer, ratio in (gross_to_net_ratios or {}).items():
        out.append(check_gross_to_net(ratio, payer=payer))
    if hopd_asc_parity is not None:
        out.append(check_site_neutral_parity(hopd_asc_parity))
    return out
