"""FTC/DOJ antitrust rollup detection.

Given a target's acquisition history, specialty, and MSA footprint,
compute:

- Estimated HHI at (MSA, specialty) from the target's disclosed
  market-share deltas
- Whether the 30-day FTC prior-notice regime (post-USAP consent
  order) applies
- Matching historical precedents from the YAML

Banding:
    RED     — estimated HHI ≥ critical threshold (2500) OR
              acquisitions ≥ critical count in a high-risk specialty
    YELLOW  — HHI ≥ watch (2000) OR acquisitions ≥ watch count
    GREEN   — below both thresholds
    UNKNOWN — no acquisition history provided
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence

from .packet import AntitrustExposure, RegulatoryBand, load_yaml


def compute_antitrust_exposure(
    *,
    target_specialty: str,
    target_msas: Iterable[str],
    acquisitions: Optional[Sequence[Dict[str, Any]]] = None,
    estimated_hhi: Optional[float] = None,
) -> AntitrustExposure:
    """Compute antitrust exposure for a target.

    ``acquisitions``: iterable of dicts with keys
        {msa, specialty, year, revenue_usd, market_share_acquired}
    ``estimated_hhi``: caller-provided HHI when they've done the
        computation upstream (e.g., with Trella Health share data).
        When absent, we derive a rough HHI from the sum of
        market_share_acquired squared, which is a coarse lower
        bound.
    """
    content = load_yaml("antitrust_precedents")
    thresholds = content.get("flag_thresholds") or {}
    high_risk = set(content.get("high_risk_specialties") or ())
    consent_orders = content.get("consent_orders") or []

    sp = target_specialty.strip().upper().replace(" ", "_")
    msas = [m for m in (m.strip() for m in (target_msas or ())) if m]

    acqs = list(acquisitions or ())
    # Count same-specialty × same-MSA acquisitions.
    same_sp_same_msa: List[Dict[str, Any]] = []
    for a in acqs:
        a_sp = str(a.get("specialty", "")).upper().replace(" ", "_")
        a_msa = str(a.get("msa", ""))
        if a_sp == sp and a_msa in msas:
            same_sp_same_msa.append(a)
    acq_count = len(same_sp_same_msa)

    # Derive HHI when not supplied. This is a rough lower bound —
    # real HHI requires the denominator (total market revenue) and
    # every competitor's share. When only own-deal shares are known
    # we compute sum(share_i^2) and scale to the 10000 HHI basis.
    if estimated_hhi is None and same_sp_same_msa:
        total_share = sum(
            float(a.get("market_share_acquired", 0) or 0)
            for a in same_sp_same_msa
        )
        # Interpret shares as decimal fractions; typical rollup
        # ends up with 40-70% combined share. HHI post-merger ~=
        # (total_share*100)^2 at a minimum if the acquirer ends
        # with one consolidated entity.
        share_pct = min(total_share, 1.0) * 100.0
        estimated_hhi = share_pct * share_pct
    elif estimated_hhi is None:
        estimated_hhi = None

    hhi_watch = float(thresholds.get("hhi_watch", 2000))
    hhi_critical = float(thresholds.get("hhi_critical", 2500))
    count_watch = int(thresholds.get("rollup_tuck_in_count_watch", 3))
    count_critical = int(thresholds.get("rollup_tuck_in_count_critical", 5))

    # The 30-day FTC prior-notice regime applies to post-USAP
    # hospital-based physician rollups in high-risk specialties.
    thirty_day = (
        sp in high_risk
        and (
            (estimated_hhi is not None and estimated_hhi >= hhi_critical)
            or acq_count >= count_critical
        )
    )

    # Bands.
    bands = []
    if estimated_hhi is not None:
        if estimated_hhi >= hhi_critical:
            bands.append(RegulatoryBand.RED)
        elif estimated_hhi >= hhi_watch:
            bands.append(RegulatoryBand.YELLOW)
        else:
            bands.append(RegulatoryBand.GREEN)
    if acq_count >= count_critical:
        bands.append(RegulatoryBand.RED)
    elif acq_count >= count_watch:
        bands.append(RegulatoryBand.YELLOW)
    elif acq_count > 0:
        bands.append(RegulatoryBand.GREEN)

    if not bands:
        band = RegulatoryBand.UNKNOWN
    elif RegulatoryBand.RED in bands:
        band = RegulatoryBand.RED
    elif RegulatoryBand.YELLOW in bands:
        band = RegulatoryBand.YELLOW
    else:
        band = RegulatoryBand.GREEN

    # Precedent matching — cite USAP/Welsh Carson when the target's
    # specialty matches and band is YELLOW+.
    matches: List[str] = []
    if band in (RegulatoryBand.YELLOW, RegulatoryBand.RED):
        for order in consent_orders:
            if str(order.get("specialty", "")).upper() == sp:
                matches.append(str(order.get("case", "")))

    remediation: List[str] = []
    if band == RegulatoryBand.RED:
        remediation.extend([
            "Geographic carve-out — divest target's MSA-overlap holdings",
            "30-day FTC prior-notice filing required before close",
            "Consider structural separation (MSO only, no practice roll-up)",
        ])
    elif band == RegulatoryBand.YELLOW:
        remediation.extend([
            "Pre-close HSR review with outside antitrust counsel",
            "Documented market-share analysis in diligence file",
        ])

    return AntitrustExposure(
        target_specialty=sp,
        target_msas=msas,
        acquisition_count=acq_count,
        estimated_hhi=estimated_hhi,
        thirty_day_ftc_notice_triggered=thirty_day,
        band=band,
        matching_precedents=matches,
        remediation_options=remediation,
    )
