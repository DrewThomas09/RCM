"""State-level regulatory + payer context the platform should know.

Associates spend 2-4 hours per deal looking up:

- Whether the state has an active Certificate of Need (CON) law and
  which services it covers.
- Whether the state expanded Medicaid under the ACA.
- How the state's Medicaid rates compare to Medicare.
- Whether the commercial market is concentrated enough to signal
  payer leverage.

None of this changes between deals in the same state — it's static
registry data. This module ships that registry plus an
:func:`assess_regulatory` helper that turns state + bed_count +
optional payer_mix into a structured :class:`RegulatoryAssessment`
the risk-flags layer and the workbench both consume.

Sources (not hit at runtime — the registry is a hand-curated
snapshot):
  - CON: NCSL Certificate of Need State Laws tracker (2024 snapshot).
  - Medicaid expansion: KFF Medicaid Expansion State Tracker.
  - Medicaid vs Medicare rates: MACPAC State-Level Medicaid-to-Medicare
    Fee Index.
  - Uninsured rate: Census ACS five-year estimates (2022 release).
  - Commercial HHI: AMA Competition in Health Insurance report
    (2023 edition).

Partners can override any of these values via
:mod:`rcm_mc.analysis.deal_overrides` (Prompt 18) — the registry is a
default, not authoritative data.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ── Dataclasses ────────────────────────────────────────────────────

@dataclass
class CONProfile:
    """Certificate-of-Need status for one state.

    ``covered_services`` lists the major service categories that
    trigger a CON filing (e.g., hospital beds, ASC, imaging). Empty
    list means "no CON" — look at :attr:`has_con` first to branch.

    ``bed_threshold`` / ``capital_threshold``: below these numbers
    the state waives CON review. ``None`` means "any size triggers".

    ``moratorium_active``: some CON states (Illinois at times, South
    Carolina historically) have active moratoriums on new-bed
    applications. This is the tightest form of growth ceiling.
    """
    has_con: bool
    covered_services: List[str] = field(default_factory=list)
    bed_threshold: Optional[int] = None
    capital_threshold: Optional[int] = None
    moratorium_active: bool = False
    source_url: str = "https://www.ncsl.org/health/con-certificate-of-need-state-laws"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StatePayerProfile:
    """Payer-environment snapshot for one state.

    ``medicaid_rate_as_pct_of_medicare`` is the MACPAC fee-index for
    inpatient services — 1.00 means Medicaid pays at parity with
    Medicare; most states sit at 0.6-0.9. Values below 0.70
    materially squeeze margins when Medicaid is >20% of payer mix.

    ``commercial_market_hhi``: HHI band from the AMA report. "HIGH"
    means the top insurer captures >50% share in most MSAs — payer
    leverage is one-sided, limiting rate negotiation upside.
    """
    medicaid_expanded: bool
    medicaid_fmap_pct: float                          # federal match rate
    medicaid_rate_as_pct_of_medicare: float           # fee index
    uninsured_rate: float                             # adult, Census ACS
    commercial_market_hhi: str = "MEDIUM"             # HIGH | MEDIUM | LOW
    dominant_insurer: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RegulatoryAssessment:
    """Combined regulatory + payer assessment for one hospital."""
    state: str
    bed_count: Optional[int] = None
    con_status: str = "NO_CON"              # CON_ACTIVE | CON_MORATORIUM | NO_CON
    con_implication: str = "none"           # competitive_moat | growth_ceiling | none
    medicaid_risk: str = "LOW"              # LOW | MEDIUM | HIGH
    market_risk: str = "LOW"
    risk_score: int = 0                     # composite 0-100
    narrative: str = ""
    con_profile: Optional[CONProfile] = None
    payer_profile: Optional[StatePayerProfile] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self.state,
            "bed_count": self.bed_count,
            "con_status": self.con_status,
            "con_implication": self.con_implication,
            "medicaid_risk": self.medicaid_risk,
            "market_risk": self.market_risk,
            "risk_score": int(self.risk_score),
            "narrative": self.narrative,
            "con_profile": (
                self.con_profile.to_dict() if self.con_profile else None
            ),
            "payer_profile": (
                self.payer_profile.to_dict() if self.payer_profile else None
            ),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "RegulatoryAssessment":
        con = d.get("con_profile") or {}
        payer = d.get("payer_profile") or {}
        return cls(
            state=str(d.get("state") or ""),
            bed_count=d.get("bed_count"),
            con_status=str(d.get("con_status") or "NO_CON"),
            con_implication=str(d.get("con_implication") or "none"),
            medicaid_risk=str(d.get("medicaid_risk") or "LOW"),
            market_risk=str(d.get("market_risk") or "LOW"),
            risk_score=int(d.get("risk_score") or 0),
            narrative=str(d.get("narrative") or ""),
            con_profile=CONProfile(**con) if con else None,
            payer_profile=StatePayerProfile(**payer) if payer else None,
        )


# ── Registry: CON states ───────────────────────────────────────────
#
# 35 CON states + DC carry non-trivial CON review requirements. 15
# non-CON states (TX, CA, AZ, CO, ID, IN, KS, MN, NM, ND, OH, PA,
# SD, UT, WY) ship with ``has_con=False`` and empty service lists.
# NH repealed its CON in 2016 but retained some bed review tied to
# the state hospital association — we mark it CON_LIGHT via
# ``covered_services=["psych_beds"]``.

_DEFAULT_SERVICES = [
    "hospital_beds", "nursing_home_beds", "ambulatory_surgery",
    "imaging", "rehab_beds",
]

CON_STATES: Dict[str, CONProfile] = {
    "AL": CONProfile(True,  _DEFAULT_SERVICES, bed_threshold=None, capital_threshold=4_000_000),
    "AK": CONProfile(True,  ["hospital_beds", "nursing_home_beds", "imaging"], capital_threshold=1_500_000),
    "AZ": CONProfile(False),
    "AR": CONProfile(True,  _DEFAULT_SERVICES, capital_threshold=5_000_000),
    "CA": CONProfile(False),
    "CO": CONProfile(False),
    "CT": CONProfile(True,  _DEFAULT_SERVICES + ["termination_of_services"], capital_threshold=10_000_000),
    "DE": CONProfile(True,  _DEFAULT_SERVICES, capital_threshold=5_800_000),
    "DC": CONProfile(True,  _DEFAULT_SERVICES, capital_threshold=5_000_000),
    "FL": CONProfile(True,  ["nursing_home_beds", "hospice_services"],  # partial — acute repealed 2019
                     capital_threshold=None),
    "GA": CONProfile(True,  _DEFAULT_SERVICES, capital_threshold=2_500_000),
    "HI": CONProfile(True,  _DEFAULT_SERVICES, capital_threshold=4_500_000),
    "ID": CONProfile(False),
    "IL": CONProfile(True,  _DEFAULT_SERVICES + ["cath_lab", "open_heart"],
                     capital_threshold=13_000_000, moratorium_active=False),
    "IN": CONProfile(False),
    "IA": CONProfile(True,  _DEFAULT_SERVICES, capital_threshold=1_500_000),
    "KS": CONProfile(False),
    "KY": CONProfile(True,  _DEFAULT_SERVICES, capital_threshold=2_500_000),
    "LA": CONProfile(True,  ["nursing_home_beds", "hospice_services"]),   # partial
    "ME": CONProfile(True,  _DEFAULT_SERVICES, capital_threshold=4_900_000),
    "MD": CONProfile(True,  _DEFAULT_SERVICES + ["cardiac_surgery"],
                     capital_threshold=20_000_000),
    "MA": CONProfile(True,  ["hospital_beds", "transplant_services"], capital_threshold=25_000_000),
    "MI": CONProfile(True,  _DEFAULT_SERVICES, capital_threshold=3_330_000),
    "MN": CONProfile(False),
    "MS": CONProfile(True,  _DEFAULT_SERVICES, capital_threshold=5_000_000),
    "MO": CONProfile(True,  _DEFAULT_SERVICES, capital_threshold=1_000_000),
    "MT": CONProfile(True,  _DEFAULT_SERVICES, capital_threshold=1_500_000),
    "NE": CONProfile(True,  _DEFAULT_SERVICES),
    "NV": CONProfile(True,  _DEFAULT_SERVICES, capital_threshold=2_000_000),
    "NH": CONProfile(True,  ["psych_beds"], capital_threshold=None),      # repealed 2016 but partial
    "NJ": CONProfile(True,  _DEFAULT_SERVICES, capital_threshold=1_000_000),
    "NM": CONProfile(False),
    "NY": CONProfile(True,  _DEFAULT_SERVICES + ["cath_lab", "organ_transplant"],
                     capital_threshold=6_000_000),
    "NC": CONProfile(True,  _DEFAULT_SERVICES, capital_threshold=2_000_000),
    "ND": CONProfile(False),
    "OH": CONProfile(False),
    "OK": CONProfile(True,  ["nursing_home_beds"]),                       # partial
    "OR": CONProfile(True,  _DEFAULT_SERVICES, capital_threshold=10_000_000),
    "PA": CONProfile(False),
    "RI": CONProfile(True,  _DEFAULT_SERVICES, capital_threshold=2_250_000),
    "SC": CONProfile(True,  _DEFAULT_SERVICES, capital_threshold=2_000_000,
                     moratorium_active=False),
    "SD": CONProfile(False),
    "TN": CONProfile(True,  _DEFAULT_SERVICES, capital_threshold=15_000_000),
    "TX": CONProfile(False),
    "UT": CONProfile(False),
    "VT": CONProfile(True,  _DEFAULT_SERVICES, capital_threshold=3_000_000),
    "VA": CONProfile(True,  _DEFAULT_SERVICES + ["psychiatric_beds"],
                     capital_threshold=15_000_000),
    "WA": CONProfile(True,  _DEFAULT_SERVICES, capital_threshold=4_600_000),
    "WV": CONProfile(True,  _DEFAULT_SERVICES, capital_threshold=5_000_000),
    "WI": CONProfile(False),
    "WY": CONProfile(False),
}


# ── Registry: state payer context ──────────────────────────────────
#
# Medicaid expansion status as of 2024 (NC expanded Dec 2023). FMAP
# is the standard non-expansion match; expansion states get 90% for
# the expansion population but 50-75% for the regular population
# (the baseline value is what we store).
#
# Medicaid-to-Medicare fee index: MACPAC 2023, inpatient services.
# Values clustered around 0.87 with tails at TX (0.62) and NY (1.12).
#
# Commercial HHI band: AMA 2023 concentration report. Most states
# are MEDIUM; HIGH = top-insurer share >45% statewide.

STATE_CONTEXT: Dict[str, StatePayerProfile] = {
    "AL": StatePayerProfile(False, 72.96, 0.82, 11.9, "HIGH",   "Blue Cross Blue Shield of Alabama"),
    "AK": StatePayerProfile(True,  50.00, 1.31, 13.5, "HIGH",   "Premera Blue Cross"),
    "AZ": StatePayerProfile(True,  68.90, 0.83, 10.7, "MEDIUM", None),
    "AR": StatePayerProfile(True,  71.87, 0.80, 8.8,  "HIGH",   "Arkansas Blue Cross"),
    "CA": StatePayerProfile(True,  50.00, 0.88, 7.2,  "MEDIUM", "Kaiser Permanente"),
    "CO": StatePayerProfile(True,  50.00, 0.84, 8.1,  "MEDIUM", None),
    "CT": StatePayerProfile(True,  50.00, 1.05, 6.1,  "MEDIUM", None),
    "DE": StatePayerProfile(True,  62.91, 1.00, 6.5,  "HIGH",   "Highmark BCBS"),
    "DC": StatePayerProfile(True,  70.00, 0.76, 3.4,  "MEDIUM", None),
    "FL": StatePayerProfile(False, 61.12, 0.57, 13.2, "MEDIUM", None),
    "GA": StatePayerProfile(False, 65.89, 0.84, 13.3, "MEDIUM", None),
    "HI": StatePayerProfile(True,  53.56, 0.75, 4.3,  "HIGH",   "HMSA"),
    "ID": StatePayerProfile(True,  68.17, 0.92, 10.2, "MEDIUM", None),
    "IL": StatePayerProfile(True,  50.17, 0.59, 7.4,  "HIGH",   "Blue Cross Blue Shield of Illinois"),
    "IN": StatePayerProfile(True,  65.93, 0.71, 8.2,  "MEDIUM", None),
    "IA": StatePayerProfile(True,  62.61, 0.89, 4.9,  "HIGH",   "Wellmark BCBS"),
    "KS": StatePayerProfile(False, 58.35, 0.93, 9.2,  "MEDIUM", None),
    "KY": StatePayerProfile(True,  71.63, 0.78, 6.4,  "MEDIUM", None),
    "LA": StatePayerProfile(True,  67.31, 0.71, 8.9,  "HIGH",   "Blue Cross Blue Shield of Louisiana"),
    "ME": StatePayerProfile(True,  62.67, 0.88, 6.9,  "MEDIUM", None),
    "MD": StatePayerProfile(True,  50.00, 0.98, 6.4,  "MEDIUM", "CareFirst"),
    "MA": StatePayerProfile(True,  50.00, 0.84, 2.4,  "MEDIUM", "Blue Cross Blue Shield of Massachusetts"),
    "MI": StatePayerProfile(True,  65.58, 0.73, 5.0,  "MEDIUM", "Blue Cross Blue Shield of Michigan"),
    "MN": StatePayerProfile(True,  50.00, 1.02, 4.3,  "MEDIUM", None),
    "MS": StatePayerProfile(False, 77.59, 0.77, 12.3, "HIGH",   "Blue Cross Blue Shield of Mississippi"),
    "MO": StatePayerProfile(True,  65.46, 0.69, 9.6,  "MEDIUM", None),
    "MT": StatePayerProfile(True,  63.07, 0.92, 7.4,  "MEDIUM", None),
    "NE": StatePayerProfile(True,  58.80, 0.92, 7.1,  "HIGH",   "Blue Cross Blue Shield of Nebraska"),
    "NV": StatePayerProfile(True,  60.97, 0.88, 11.4, "MEDIUM", None),
    "NH": StatePayerProfile(True,  50.00, 0.83, 5.9,  "MEDIUM", None),
    "NJ": StatePayerProfile(True,  50.00, 0.42, 7.3,  "MEDIUM", "Horizon BCBS"),
    "NM": StatePayerProfile(True,  71.63, 0.93, 8.0,  "MEDIUM", None),
    "NY": StatePayerProfile(True,  50.00, 1.12, 5.2,  "LOW",    None),
    "NC": StatePayerProfile(True,  64.70, 0.86, 11.0, "HIGH",   "Blue Cross Blue Shield of North Carolina"),
    "ND": StatePayerProfile(True,  50.00, 0.92, 7.5,  "HIGH",   "BCBS of North Dakota"),
    "OH": StatePayerProfile(True,  64.78, 0.79, 7.2,  "MEDIUM", None),
    "OK": StatePayerProfile(True,  67.31, 0.89, 13.1, "MEDIUM", None),
    "OR": StatePayerProfile(True,  63.71, 0.74, 6.1,  "MEDIUM", None),
    "PA": StatePayerProfile(True,  52.39, 0.77, 5.8,  "MEDIUM", None),
    "RI": StatePayerProfile(True,  53.76, 0.95, 3.9,  "HIGH",   "Blue Cross Blue Shield of Rhode Island"),
    "SC": StatePayerProfile(False, 70.51, 0.79, 10.9, "HIGH",   "Blue Cross Blue Shield of South Carolina"),
    "SD": StatePayerProfile(True,  58.61, 1.00, 9.1,  "HIGH",   "Wellmark BCBS"),
    "TN": StatePayerProfile(False, 65.04, 0.68, 10.1, "MEDIUM", "BlueCross BlueShield of Tennessee"),
    "TX": StatePayerProfile(False, 60.25, 0.62, 17.3, "MEDIUM", None),
    "UT": StatePayerProfile(True,  66.49, 0.83, 8.7,  "MEDIUM", None),
    "VT": StatePayerProfile(True,  55.89, 0.96, 4.3,  "HIGH",   "Blue Cross Blue Shield of Vermont"),
    "VA": StatePayerProfile(True,  50.00, 0.92, 9.0,  "MEDIUM", None),
    "WA": StatePayerProfile(True,  50.00, 0.87, 6.8,  "MEDIUM", None),
    "WV": StatePayerProfile(True,  73.80, 0.71, 6.9,  "HIGH",   "Highmark BCBS"),
    "WI": StatePayerProfile(False, 59.86, 0.72, 5.5,  "MEDIUM", None),
    "WY": StatePayerProfile(False, 50.00, 0.97, 12.2, "HIGH",   "Blue Cross Blue Shield of Wyoming"),
}


def _normalize_state(state: str) -> str:
    if not isinstance(state, str):
        return ""
    return state.strip().upper()


# ── Narrative helpers ──────────────────────────────────────────────

def _con_status_for(profile: CONProfile, bed_count: Optional[int]) -> Tuple[str, str]:
    """Return ``(status, implication)``."""
    if not profile.has_con:
        return "NO_CON", "none"
    if profile.moratorium_active:
        return "CON_MORATORIUM", "growth_ceiling"
    # Bed threshold matters: a 25-bed CAH in a high-threshold state
    # may not trigger review even in a CON state.
    if (profile.bed_threshold is not None and bed_count is not None
            and bed_count < profile.bed_threshold):
        return "CON_ACTIVE", "competitive_moat"
    return "CON_ACTIVE", "competitive_moat"


def _medicaid_risk_for(
    profile: StatePayerProfile,
    payer_mix: Optional[Dict[str, float]],
) -> str:
    """HIGH when state fee-index is < 0.70 AND Medicaid is > 20% of mix.

    Without a payer mix we drop a band — we can't prove the exposure,
    but sub-0.70 states are still notable, so MEDIUM.
    """
    fee_index = profile.medicaid_rate_as_pct_of_medicare
    medicaid_share = 0.0
    if payer_mix:
        for k, v in payer_mix.items():
            if "medicaid" in k.lower():
                try:
                    medicaid_share = max(medicaid_share, float(v))
                except (TypeError, ValueError):
                    continue
    # payer_mix values may be either fractions (0.25) or pct-points (25).
    if medicaid_share > 1.0:
        medicaid_share = medicaid_share / 100.0

    if fee_index < 0.70:
        if medicaid_share >= 0.20:
            return "HIGH"
        if medicaid_share >= 0.10 or not payer_mix:
            return "MEDIUM"
    if fee_index < 0.85 and medicaid_share >= 0.30:
        return "MEDIUM"
    return "LOW"


def _market_risk_for(
    profile: StatePayerProfile,
    payer_mix: Optional[Dict[str, float]],
) -> str:
    """HIGH when HHI is HIGH *and* commercial is > 30% of mix."""
    commercial_share = 0.0
    if payer_mix:
        for k, v in payer_mix.items():
            if "commercial" in k.lower():
                try:
                    commercial_share = max(commercial_share, float(v))
                except (TypeError, ValueError):
                    continue
    if commercial_share > 1.0:
        commercial_share = commercial_share / 100.0

    if profile.commercial_market_hhi == "HIGH":
        if commercial_share >= 0.30:
            return "HIGH"
        if commercial_share >= 0.15 or not payer_mix:
            return "MEDIUM"
    if profile.commercial_market_hhi == "MEDIUM" and commercial_share >= 0.40:
        return "MEDIUM"
    return "LOW"


def _narrative_for(a: RegulatoryAssessment) -> str:
    """Two-to-three sentence plain-English summary the UI renders."""
    parts: List[str] = []
    con = a.con_profile
    payer = a.payer_profile
    if con is not None and con.has_con:
        if a.con_status == "CON_MORATORIUM":
            parts.append(
                f"{a.state} has an active CON moratorium on new capacity."
            )
        else:
            svc = ", ".join(con.covered_services[:3]) or "core services"
            parts.append(
                f"{a.state} operates a Certificate-of-Need regime covering "
                f"{svc}, which acts as a competitive moat for incumbents."
            )
    else:
        parts.append(
            f"{a.state} has no active CON law — new entrants can stand up "
            f"competing capacity without state review."
        )

    if payer is not None:
        expansion = "expanded Medicaid" if payer.medicaid_expanded else (
            "did not expand Medicaid"
        )
        parts.append(
            f"The state {expansion} (FMAP {payer.medicaid_fmap_pct:.0f}%, "
            f"Medicaid pays "
            f"{payer.medicaid_rate_as_pct_of_medicare * 100:.0f}% of "
            f"Medicare rates)."
        )
        if payer.commercial_market_hhi == "HIGH":
            dom = payer.dominant_insurer or "the dominant insurer"
            parts.append(
                f"The commercial market is highly concentrated; "
                f"{dom} sets the terms in most MSAs."
            )
    return " ".join(parts)


def _risk_score(a: RegulatoryAssessment) -> int:
    """Composite 0-100.

    Weights: Medicaid risk (40), market risk (30), CON growth ceiling
    (20), everything else (10). Simple linear so partners can
    reason about the number without a lookup table.
    """
    scores = {"LOW": 0, "MEDIUM": 50, "HIGH": 100}
    medicaid = scores.get(a.medicaid_risk, 0) * 0.40
    market = scores.get(a.market_risk, 0) * 0.30
    con = 0
    if a.con_implication == "growth_ceiling":
        con = 60 * 0.20
    elif a.con_implication == "competitive_moat":
        con = 20 * 0.20
    return int(round(medicaid + market + con))


# ── Public entry ──────────────────────────────────────────────────

def assess_regulatory(
    state: str,
    bed_count: Optional[int] = None,
    *,
    payer_mix: Optional[Dict[str, float]] = None,
) -> RegulatoryAssessment:
    """Combine state registries + hospital attributes into an
    assessment the risk-flags layer and workbench both consume.

    Unknown state codes return an empty assessment rather than
    raising — the builder sits one step above this and shouldn't
    break on a typo'd profile.
    """
    st = _normalize_state(state)
    con = CON_STATES.get(st)
    payer = STATE_CONTEXT.get(st)
    a = RegulatoryAssessment(
        state=st, bed_count=bed_count,
        con_profile=con, payer_profile=payer,
    )
    if con is not None:
        a.con_status, a.con_implication = _con_status_for(con, bed_count)
    if payer is not None:
        a.medicaid_risk = _medicaid_risk_for(payer, payer_mix)
        a.market_risk = _market_risk_for(payer, payer_mix)
    a.risk_score = _risk_score(a)
    a.narrative = _narrative_for(a)
    return a


def all_known_states() -> List[str]:
    """Union of both registries — the set of state codes we know
    about. Test helper, exposed publicly because the onboarding
    wizard uses it to populate state dropdowns."""
    return sorted(set(CON_STATES.keys()) | set(STATE_CONTEXT.keys()))
