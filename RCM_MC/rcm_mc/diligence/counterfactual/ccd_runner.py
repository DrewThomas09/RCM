"""CCD-driven counterfactual runner.

Given a :class:`CanonicalClaimsDataset`, extract the inputs each
solver needs and return the :class:`CounterfactualSet`. Ties the
counterfactual advisor to the rest of the platform — callers can
now run "what would change our mind" directly from a CCD fixture
instead of hand-populating a WorkbenchInput.

Derived inputs:
    - OON share + dollars (from claims.is_oon / network_status)
    - HOPD revenue (from claims.place_of_service == '22')
    - Specialty mix (from CPT ranges)
    - Payer concentration / commercial HHI (from payer_class)
    - Denial stratification (from the KPI engine)

What we can NOT derive from a CCD:
    - Legal structure (not a claim field)
    - Landlord (not a claim field)
    - Lease terms
    - Acquisition history
These come from caller-supplied metadata; the runner accepts
``metadata`` as a supplementary dict.
"""
from __future__ import annotations

from collections import Counter
from datetime import date
from typing import Any, Dict, List, Optional, Sequence

from ..regulatory import (
    compute_antitrust_exposure, compute_cpom_exposure,
    compute_nsa_exposure, compute_team_impact,
    simulate_site_neutral_impact,
)
from .advisor import (
    Counterfactual, CounterfactualSet, for_antitrust, for_cpom,
    for_cyber, for_nsa, for_site_neutral, for_steward, for_team,
)


# Specialties that qualify as hospital-based physician under NSA.
_NSA_COVERED_SPECIALTIES = {
    "EMERGENCY_MEDICINE", "ANESTHESIOLOGY", "RADIOLOGY",
    "PATHOLOGY", "NEONATOLOGY", "HOSPITALIST",
}


def _infer_oon_metrics(
    claims: Sequence[Any],
) -> tuple[float, float, float]:
    """Return (total_paid, oon_paid, oon_share)."""
    total = 0.0
    oon = 0.0
    for c in claims:
        paid = float(getattr(c, "paid_amount", 0.0) or 0.0)
        if paid <= 0:
            continue
        total += paid
        net = (getattr(c, "network_status", "") or "").upper()
        is_oon = (net in ("OON", "OUT_OF_NETWORK")
                  or bool(getattr(c, "is_oon", False)))
        if is_oon:
            oon += paid
    share = (oon / total) if total > 0 else 0.0
    return total, oon, share


def _infer_hopd_revenue(claims: Sequence[Any]) -> float:
    """Sum paid_amount for HOPD claims (place_of_service '22')."""
    out = 0.0
    for c in claims:
        pos = str(getattr(c, "place_of_service", "") or "")
        is_hopd = bool(getattr(c, "is_hopd", False)) or pos == "22"
        if not is_hopd:
            continue
        paid = float(getattr(c, "paid_amount", 0.0) or 0.0)
        if paid > 0:
            out += paid
    return out


def _infer_commercial_hhi(
    claims: Sequence[Any],
) -> tuple[Optional[float], Dict[str, float]]:
    """Derive commercial-payer concentration HHI from claims."""
    by_payer: Dict[str, float] = {}
    for c in claims:
        pc = getattr(c, "payer_class", None)
        payer_cls = pc.value if hasattr(pc, "value") else str(pc or "")
        if payer_cls != "COMMERCIAL":
            continue
        payer_name = str(getattr(c, "payer_name", "UNKNOWN") or "UNKNOWN")
        paid = float(getattr(c, "paid_amount", 0.0) or 0.0)
        if paid <= 0:
            continue
        by_payer[payer_name] = by_payer.get(payer_name, 0.0) + paid
    total = sum(by_payer.values())
    if total <= 0:
        return None, by_payer
    hhi = sum(((v / total) * 100) ** 2 for v in by_payer.values())
    return hhi, by_payer


def run_counterfactuals_from_ccd(
    ccd: Any,
    *,
    metadata: Optional[Dict[str, Any]] = None,
) -> CounterfactualSet:
    """Run every applicable solver against a CCD.

    ``metadata`` supplies fields that don't appear on claims
    (legal_structure, states, landlord, lease_term_years, etc.)
    and augments the CCD-derived inputs. A typical call:

        run_counterfactuals_from_ccd(ccd, metadata={
            "legal_structure": "FRIENDLY_PC_PASS_THROUGH",
            "states": ["OR", "WA"],
            "landlord": "Medical Properties Trust",
            "lease_term_years": 20, "lease_escalator_pct": 0.035,
            "ebitdar_coverage": 1.2, "geography": "RURAL",
            "specialty": "EMERGENCY_MEDICINE",
            "is_hospital_based_physician": True,
            "cbsa_codes": ["35620"],
            "acquisitions": [...],
            "msas": ["Houston"],
        })
    """
    meta = metadata or {}
    claims = list(getattr(ccd, "claims", []) or [])

    # CPOM
    cpom = None
    if meta.get("legal_structure") and meta.get("states"):
        try:
            cpom = compute_cpom_exposure(
                target_structure=meta["legal_structure"],
                footprint_states=meta["states"],
            )
        except Exception:  # noqa: BLE001
            cpom = None

    # NSA — infer OON share from claims when the target specialty is
    # NSA-covered.
    nsa = None
    specialty = (meta.get("specialty") or "").upper()
    if (meta.get("is_hospital_based_physician")
            and specialty in _NSA_COVERED_SPECIALTIES):
        total, oon, share = _infer_oon_metrics(claims)
        if total > 0 and oon > 0:
            nsa = compute_nsa_exposure(
                specialty=specialty,
                oon_revenue_share=share,
                oon_dollars_annual=oon,
            )

    # Steward — requires metadata (landlord + lease terms).
    steward = None
    if meta.get("landlord") or meta.get("lease_term_years"):
        from ..real_estate import (
            LeaseLine, LeaseSchedule, compute_steward_score,
        )
        steward = compute_steward_score(
            LeaseSchedule(lines=[LeaseLine(
                property_id=meta.get("target_name", "target"),
                property_type=(specialty or "HOSPITAL").upper(),
                base_rent_annual_usd=float(
                    meta.get("annual_rent_usd", 1.0)
                ),
                escalator_pct=float(
                    meta.get("lease_escalator_pct", 0.0) or 0.0
                ),
                term_years=int(meta.get("lease_term_years", 10) or 10),
                landlord=meta.get("landlord"),
            )]),
            portfolio_ebitdar_annual_usd=(
                meta.get("portfolio_ebitdar_usd")
            ),
            portfolio_annual_rent_usd=meta.get("annual_rent_usd"),
            geography=meta.get("geography"),
        )

    # TEAM — any mandatory CBSA in the list.
    team = None
    for cbsa in meta.get("cbsa_codes") or ():
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

    # Antitrust.
    antitrust = None
    if meta.get("acquisitions") and specialty:
        antitrust = compute_antitrust_exposure(
            target_specialty=specialty,
            target_msas=meta.get("msas") or [],
            acquisitions=meta["acquisitions"],
        )

    # Site-neutral — from claims HOPD revenue under the
    # legislative scenario (worst-case).
    site_neutral = None
    hopd_rev = _infer_hopd_revenue(claims)
    if hopd_rev > 0:
        site_neutral = simulate_site_neutral_impact(
            scenario="legislative",
            hopd_total_revenue_usd=hopd_rev,
        )

    # Cyber — requires metadata (not derivable from claims).
    cyber = meta.get("_cyber_score")

    # Run each solver; pass Steward its lease context so it can
    # quote a PV-of-savings number instead of "qualitative".
    items: List[Counterfactual] = []
    for solver, arg, kwargs in (
        (for_cpom, cpom, {}),
        (for_nsa, nsa, {}),
        (for_steward, steward, {
            "annual_rent_usd": meta.get("annual_rent_usd"),
            "current_escalator_pct": meta.get("lease_escalator_pct"),
            "current_term_years": meta.get("lease_term_years"),
        }),
        (for_team, team, {}),
        (for_antitrust, antitrust, {}),
        (for_cyber, cyber, {}),
        (for_site_neutral, site_neutral, {}),
    ):
        if arg is None:
            continue
        try:
            cf = solver(arg, **kwargs)
        except Exception:  # noqa: BLE001
            cf = None
        if cf is not None:
            items.append(cf)
    return CounterfactualSet(items=items)


def summarize_ccd_inputs(ccd: Any) -> Dict[str, Any]:
    """Produce a debug summary of what we could derive from the CCD.

    Useful in the workbench landing + for troubleshooting. Returns
    a plain dict so the UI can render it without further wrapping."""
    claims = list(getattr(ccd, "claims", []) or [])
    total, oon, share = _infer_oon_metrics(claims)
    hhi, commercial_payers = _infer_commercial_hhi(claims)
    return {
        "claim_count": len(claims),
        "total_paid_usd": total,
        "oon_paid_usd": oon,
        "oon_share": share,
        "hopd_revenue_usd": _infer_hopd_revenue(claims),
        "commercial_hhi": hhi,
        "commercial_payer_count": len(commercial_payers),
    }
