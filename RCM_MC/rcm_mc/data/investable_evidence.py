"""Investable-evidence scoring v1 — a transparent, peer-relative evidence
layer over the six live CMS verticals. NOT a black-box model and NOT an
investment recommendation.

For one provider it assembles:
- **quality components** — each higher-is-better public metric, with the
  provider's raw value, its peer percentile (same-state rated peers), and a
  guarded z-score (only when n>=5 and sd>0);
- a transparent **evidence index** — the weighted mean of the *available*
  component percentiles (equal weights by default, every weight exposed);
- **risk flags** — enforcement/staffing/ownership signals surfaced
  *separately* and never silently folded into the index (e.g. SNF Special
  Focus Facility, abuse icon, recent ownership change, low staffing);
- **missingness**, **sample size**, the **formula**, and **caveats**.

Hard rules (enforced in tests):
- No investment recommendation, no commercial-revenue claim, no true
  market-share claim, no causal-impact claim.
- Every component's raw value, weight, peer set, and sample size is exposed —
  nothing hidden behind a single number.
- Percentile is peer deviation; the index is peer-relative quality evidence,
  not a verdict.
- Lower-is-better outcome rates (dialysis mortality, IRF/LTCH readmission &
  MSPB) are deliberately excluded so the "higher = better" index holds.

Lives in data/; only calls data/ loaders (incl. cross_sector). Never imports
the ui/ layer.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .cross_sector import SECTOR_BY_ID, SectorSpec

_MIN_N = 5  # below this, percentile/z-score are unreliable


# Higher-is-better quality metrics per sector (headline first). Lower-is-better
# outcome rates are intentionally omitted so the index stays directional.
_QUALITY_METRICS: Dict[str, List[Tuple[str, str, str]]] = {
    "home-health": [
        ("star_rating", "Quality star rating", ""),
        ("timely_initiation_pct", "Timely initiation of care", "%"),
        ("discharge_to_community_rate", "Discharge to community", "%"),
        ("improve_ambulation_pct", "Improvement in ambulation", "%"),
        # Patient experience (HHCAHPS) — higher is better.
        ("cahps_summary_star", "Patient-survey summary star", ""),
        ("cahps_recommend_pct", "Would recommend the agency", "%"),
    ],
    "hospice": [
        ("care_index_overall", "Hospice Care Index", ""),
        ("composite_process", "Composite process measure", "%"),
        ("pain_screening", "Pain screening", "%"),
        ("treatment_preferences", "Treatment preferences", "%"),
        # Family-caregiver experience (CAHPS Hospice) — higher is better.
        ("cahps_summary_star", "Family-survey summary star", ""),
        ("cahps_recommend_pct", "Would definitely recommend", "%"),
    ],
    "nursing-homes": [
        ("overall_rating", "Overall star rating", ""),
        ("health_inspection_rating", "Health-inspection rating", ""),
        ("staffing_rating", "Staffing rating", ""),
        ("qm_rating", "Quality-measure rating", ""),
    ],
    "dialysis": [
        ("five_star", "Overall 5-star rating", ""),
        # Patient experience (ICH CAHPS) — higher is better.
        ("cahps_facility_star", "Patient-survey facility star", ""),
        ("cahps_center_care_star", "Center care & operations star", ""),
    ],
    "inpatient-rehab": [
        ("dtc_rs_rate", "Successful return to home/community", "%"),
        ("selfcare_fn_pct", "Self-care function at/above expected", "%"),
        ("mobility_fn_pct", "Mobility function at/above expected", "%"),
        ("hcp_flu_pct", "Healthcare-personnel flu vaccination", "%"),
        ("med_review_pct", "Medication review & follow-up", "%"),
        ("med_list_next_pct", "Medication list to next provider", "%"),
    ],
    "long-term-care-hospital": [
        ("dtc_rs_rate", "Successful return to home/community", "%"),
        ("selfcare_fn_pct", "Self-care function at/above expected", "%"),
        ("hcp_flu_pct", "Healthcare-personnel flu vaccination", "%"),
        ("med_review_pct", "Medication review & follow-up", "%"),
        ("vent_weaning_pct", "Successfully weaned from ventilator", "%"),
    ],
}


@dataclass
class EvidenceComponent:
    key: str
    label: str
    suffix: str
    raw_value: Optional[float]
    available: bool
    peer_percentile: Optional[int]   # 0–100 within same-state rated peers
    z_score: Optional[float]         # guarded: n>=5 and sd>0
    weight: float
    note: str = ""


@dataclass
class RiskFlag:
    name: str
    triggered: bool
    detail: str


@dataclass
class EvidenceProfile:
    sector_id: str
    sector_label: str
    ccn: str
    provider_name: str
    state: str
    peer_set_label: str
    sample_size: int                 # rated peers for the headline metric
    components: List[EvidenceComponent]
    evidence_index: Optional[float]  # weighted mean of available percentiles
    formula: str
    weights_note: str
    risk_flags: List[RiskFlag] = field(default_factory=list)
    missingness: List[str] = field(default_factory=list)
    caveats: List[str] = field(default_factory=list)


def _peer_values(quality: Dict[str, Dict[str, Optional[float]]],
                 peer_ccns: List[str], key: str) -> List[float]:
    return sorted(v for v in ((quality.get(c) or {}).get(key)
                              for c in peer_ccns) if v is not None)


def _percentile_rank(sorted_vals: List[float], v: Optional[float]) -> Optional[int]:
    if v is None or not sorted_vals:
        return None
    below = sum(1 for x in sorted_vals if x < v)
    equal = sum(1 for x in sorted_vals if x == v)
    return round(100 * (below + 0.5 * equal) / len(sorted_vals))


def _z_score(vals: List[float], v: Optional[float]) -> Optional[float]:
    """z-score of v within vals — guarded: n>=5 and sd>0, else None."""
    if v is None or len(vals) < _MIN_N:
        return None
    mean = sum(vals) / len(vals)
    var = sum((x - mean) ** 2 for x in vals) / len(vals)
    sd = math.sqrt(var)
    if sd <= 0:
        return None
    return round((v - mean) / sd, 2)


def _snf_risk_flags(provider: Any, q: Dict[str, Optional[float]]) -> List[RiskFlag]:
    """SNF-specific enforcement/staffing/ownership flags (data exists here)."""
    flags: List[RiskFlag] = []
    sff = (getattr(provider, "sff_status", "") or "").strip()
    flags.append(RiskFlag(
        "Special Focus Facility", bool(sff),
        sff or "Not on the SFF / SFF-candidate list."))
    abuse = (getattr(provider, "abuse_icon", "") or "").strip().upper()
    flags.append(RiskFlag(
        "Abuse icon", abuse == "Y",
        "CMS abuse icon present." if abuse == "Y" else "No abuse icon."))
    chg = (getattr(provider, "changed_ownership_12mo", "") or "").strip().upper()
    flags.append(RiskFlag(
        "Ownership change <12mo", chg == "Y",
        "Ownership changed in the last 12 months." if chg == "Y"
        else "No ownership change flagged in the last 12 months."))
    staffing = q.get("staffing_rating")
    flags.append(RiskFlag(
        "Low staffing rating", staffing is not None and staffing <= 1,
        f"Staffing rating = {staffing:g}." if staffing is not None
        else "Staffing rating not reported."))
    penalties = q.get("num_penalties")
    flags.append(RiskFlag(
        "Enforcement penalties", penalties is not None and penalties > 0,
        f"{penalties:g} enforcement penalty(ies) on record."
        if penalties is not None else "Penalty count not reported."))
    return flags


def evidence_profile(sector_id: str, ccn: str) -> Optional[EvidenceProfile]:
    """Transparent peer-relative evidence profile for one provider.

    Returns None if the sector or CCN is unknown.
    """
    spec: Optional[SectorSpec] = SECTOR_BY_ID.get(sector_id)
    if spec is None:
        return None
    providers = spec.providers_loader()
    provider = providers.get(ccn)
    if provider is None:
        return None
    quality = spec.quality_loader()
    state = (getattr(provider, "state", "") or "").strip().upper()
    name = getattr(provider, spec.name_attr, "") or ""

    metrics = _QUALITY_METRICS.get(sector_id, [(spec.headline_key,
                                                spec.headline_label,
                                                spec.headline_suffix)])
    weight = round(1.0 / len(metrics), 4)

    # Peer set = same-state providers (sample size measured on the headline).
    peer_ccns = [c for c, p in providers.items()
                 if (getattr(p, "state", "") or "").strip().upper() == state]
    headline_peers = _peer_values(quality, peer_ccns, spec.headline_key)
    sample_size = len(headline_peers)

    components: List[EvidenceComponent] = []
    missing: List[str] = []
    pct_for_index: List[int] = []
    own_q = quality.get(ccn) or {}
    for key, label, suffix in metrics:
        raw = own_q.get(key)
        peers = _peer_values(quality, peer_ccns, key)
        pct = _percentile_rank(peers, raw) if len(peers) >= _MIN_N else None
        z = _z_score(peers, raw)
        avail = raw is not None
        note = ""
        if not avail:
            missing.append(label)
            note = "Not reported for this provider."
        elif len(peers) < _MIN_N:
            note = f"Only {len(peers)} rated peer(s) in {state} — percentile suppressed."
        components.append(EvidenceComponent(
            key=key, label=label, suffix=suffix, raw_value=raw, available=avail,
            peer_percentile=pct, z_score=z, weight=weight, note=note))
        if pct is not None:
            pct_for_index.append(pct)

    evidence_index = (round(sum(pct_for_index) / len(pct_for_index), 1)
                      if pct_for_index else None)

    risk_flags = _snf_risk_flags(provider, own_q) if sector_id == "nursing-homes" else []

    caveats = [
        "Peer-relative QUALITY evidence over public CMS data — NOT an "
        "investment recommendation, commercial revenue, market share, or a "
        "causal claim.",
        "Percentile is deviation from same-state peers, not a verdict; read "
        "with the sample size and missingness shown.",
        "Risk flags are surfaced separately and are never folded into the "
        "evidence index.",
    ]
    if sample_size < _MIN_N:
        caveats.append(
            f"Only {sample_size} rated peer(s) in {state} — the index and "
            "percentiles are unreliable at this sample size.")
    if missing:
        caveats.append("Missing components (excluded from the index): "
                       + ", ".join(missing) + ".")

    return EvidenceProfile(
        sector_id=sector_id, sector_label=spec.label, ccn=ccn,
        provider_name=name, state=state,
        peer_set_label=f"same-state rated {spec.label} providers in {state}",
        sample_size=sample_size, components=components,
        evidence_index=evidence_index,
        formula="evidence_index = mean(peer_percentile of each AVAILABLE "
                "higher-is-better quality component); equal weights; missing "
                "components excluded; risk flags reported separately.",
        weights_note=f"{len(metrics)} candidate component(s), equal weight "
                     f"{weight:g} each; only components with >= {_MIN_N} rated "
                     "peers and a reported value contribute.",
        risk_flags=risk_flags, missingness=missing, caveats=caveats)
