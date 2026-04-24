"""No Surprises Act IDR exposure modeler.

For any hospital-based physician group (ER, anesthesia, radiology,
pathology, neonatology, hospitalist), compute:

- OON revenue share from the CCD (or passed explicitly)
- QPA-anchored expected payment per CPT using the
  ``specialty_qpa_anchors`` table
- Dollar shortfall between seller-claimed OON revenue and
  QPA-anchored
- IDR challenge probability derived from QPA shortfall magnitude
- Month-by-month cash impact straight-lined over 12 months (real
  IDR decisions trickle over ~4-6 months; straight-line is a
  first-order approximation)

Anchors to Envision ($9.9B LBO, bankruptcy 2023) and American
Physician Partners ($3.2M/mo NSA drag) when the target's OON
profile matches the pattern.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, Optional, Sequence

from .packet import NSAExposure, RegulatoryBand, load_yaml


def compute_nsa_exposure(
    *,
    specialty: str,
    oon_revenue_share: float,
    oon_dollars_annual: float,
    seller_avg_rate_multiple_of_medicare: Optional[float] = None,
    medicare_total_usd: Optional[float] = None,
) -> NSAExposure:
    """Compute NSA IDR exposure for a hospital-based physician group.

    Required:
        specialty: one of the covered specialties
            (EMERGENCY_MEDICINE, ANESTHESIOLOGY, RADIOLOGY,
            PATHOLOGY, NEONATOLOGY, HOSPITALIST)
        oon_revenue_share: fraction of total revenue that is OON
        oon_dollars_annual: dollar amount of OON revenue per year
    Optional:
        seller_avg_rate_multiple_of_medicare: what the seller
            reports as their effective OON rate as a multiple of
            Medicare. Compared against the YAML's specialty_qpa_anchors.
            When absent, we infer from Medicare total.
        medicare_total_usd: Medicare-equivalent total for the same
            OON volume, used to derive the multiple.
    """
    content = load_yaml("nsa_idr_benchmarks")
    covered = set(content.get("covered_specialties") or ())
    anchors = content.get("specialty_qpa_anchors") or {}
    thresholds = content.get("flag_thresholds") or {}
    cases = content.get("case_studies") or []

    sp = specialty.strip().upper().replace(" ", "_")
    if sp not in covered:
        return NSAExposure(
            specialty=sp, oon_revenue_share=float(oon_revenue_share),
            dollars_at_risk_usd=0.0,
            qpa_shortfall_pct=0.0,
            idr_challenge_probability=0.0,
            band=RegulatoryBand.GREEN,
            case_study_match=None,
            month_by_month_cash_impact_usd=[0.0] * 12,
        )

    qpa_anchor = float(anchors.get(sp, 1.50))
    # Derive the seller's effective rate multiple when not given.
    if seller_avg_rate_multiple_of_medicare is None:
        if medicare_total_usd and medicare_total_usd > 0:
            seller_avg_rate_multiple_of_medicare = (
                oon_dollars_annual / medicare_total_usd
            )
        else:
            seller_avg_rate_multiple_of_medicare = qpa_anchor

    qpa_shortfall = (
        seller_avg_rate_multiple_of_medicare - qpa_anchor
    ) / qpa_anchor
    qpa_shortfall = max(qpa_shortfall, 0.0)  # only positive = at-risk

    # Expected OON revenue under QPA reversion = seller revenue /
    # (1 + shortfall). Dollars-at-risk = diff.
    if qpa_shortfall > 0:
        qpa_expected = oon_dollars_annual / (
            1.0 + qpa_shortfall
        )
    else:
        qpa_expected = oon_dollars_annual
    dollars_at_risk = oon_dollars_annual - qpa_expected

    # IDR challenge probability scales with both OON share and
    # shortfall magnitude. Cap at 0.95.
    prob = min(
        0.95,
        0.3 * float(oon_revenue_share) + 1.5 * qpa_shortfall,
    )

    # Band. Two gates: OON share thresholds AND shortfall thresholds.
    # The worse of the two wins.
    def share_band(s: float) -> RegulatoryBand:
        if s >= float(thresholds.get("oon_revenue_share_critical", 0.35)):
            return RegulatoryBand.RED
        if s >= float(thresholds.get("oon_revenue_share_watch", 0.20)):
            return RegulatoryBand.YELLOW
        return RegulatoryBand.GREEN

    def shortfall_band(s: float) -> RegulatoryBand:
        if s >= float(thresholds.get("qpa_shortfall_critical", 0.25)):
            return RegulatoryBand.RED
        if s >= float(thresholds.get("qpa_shortfall_watch", 0.10)):
            return RegulatoryBand.YELLOW
        return RegulatoryBand.GREEN

    b1 = share_band(oon_revenue_share)
    b2 = shortfall_band(qpa_shortfall)
    ordered = [RegulatoryBand.RED, RegulatoryBand.YELLOW,
               RegulatoryBand.GREEN]
    band = next(b for b in ordered if b in (b1, b2))

    # Case-study match.
    match: Optional[str] = None
    if band == RegulatoryBand.RED:
        # Envision pattern: >35% OON share
        if oon_revenue_share >= 0.35:
            for case in cases:
                if case.get("name") == "Envision Healthcare":
                    match = "Envision Healthcare (2018 LBO → 2023 bankruptcy)"
                    break
        # APP pattern: >20% OON + high shortfall
        if match is None and qpa_shortfall >= 0.25:
            for case in cases:
                if case.get("name") == "American Physician Partners":
                    match = "American Physician Partners (2023 liquidation)"
                    break

    # Month-by-month: straight-line the dollars-at-risk over 12 months.
    monthly = [dollars_at_risk / 12.0] * 12 if dollars_at_risk else [0.0] * 12

    return NSAExposure(
        specialty=sp,
        oon_revenue_share=float(oon_revenue_share),
        dollars_at_risk_usd=float(dollars_at_risk),
        qpa_shortfall_pct=float(qpa_shortfall),
        idr_challenge_probability=float(prob),
        band=band,
        case_study_match=match,
        month_by_month_cash_impact_usd=monthly,
    )


def compute_nsa_from_ccd(
    claims: Sequence[Any],
    *,
    specialty: str,
    oon_predicate: Optional[Any] = None,
) -> NSAExposure:
    """Convenience wrapper that aggregates OON dollars from a
    ``CCD`` claims sequence. A claim counts as OON when
    ``oon_predicate(claim)`` returns True; default predicate checks
    a ``is_oon`` / ``network_status`` attribute."""
    total_amt = 0.0
    oon_amt = 0.0
    for c in claims:
        paid = float(getattr(c, "paid_amount", 0.0) or 0.0)
        if paid <= 0:
            continue
        total_amt += paid
        if oon_predicate is None:
            ns = (getattr(c, "network_status", "") or "").upper()
            if ns in ("OON", "OUT_OF_NETWORK") or \
               bool(getattr(c, "is_oon", False)):
                oon_amt += paid
        elif oon_predicate(c):
            oon_amt += paid
    share = (oon_amt / total_amt) if total_amt > 0 else 0.0
    return compute_nsa_exposure(
        specialty=specialty,
        oon_revenue_share=share,
        oon_dollars_annual=oon_amt,
    )
