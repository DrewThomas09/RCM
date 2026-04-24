"""Bankruptcy-Survivor Scan — pre-packet screening artifact.

Twelve deterministic pattern-match checks against:

    Historical failures (6):
        - Steward Health (2016 MPT → 2024)
        - Envision Healthcare (2018 KKR → 2023)
        - American Physician Partners (2016 → 2023)
        - Cano Health (SPAC → 2024)
        - Prospect Medical (2019 Leonard Green → 2025)
        - Wellpath (correctional health → 2024)

    Forward-looking regulatory vectors (6):
        - CPOM kill-zone (CA/OR legal-structure void)
        - TEAM downside exposure (mandatory CBSA hospital)
        - NSA IDR cliff (hospital-based physician group)
        - Site-neutral erosion (HOPD revenue)
        - Antitrust rollup trigger (specialty concentration)
        - Sale-leaseback blocker (MA/CT/PA gating)

Each check is a deterministic pattern (rule-based) — no free-form
inference. Hits are cited with the named historical deal's EV at
LBO and at bankruptcy/recovery.

Output is a :class:`BankruptcySurvivorScan` with:
- 12 individual :class:`PatternCheck` results (pass/fail)
- Overall verdict: GREEN / YELLOW / RED / CRITICAL
- Named case-study comparisons for each RED/CRITICAL hit
- Ordered list of diligence questions the partner should ask

The scan is public-data only — it does NOT require a CCD ingest.
A PE associate runs it on a teaser.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional, Sequence

from ..real_estate import (
    LeaseLine, LeaseSchedule, StewardRiskTier, compute_steward_score,
    rent_is_suicidal, sale_leaseback_feasibility,
)
from ..regulatory import (
    RegulatoryBand, compute_antitrust_exposure, compute_cpom_exposure,
    is_cbsa_mandatory,
)


class BankruptcySurvivorVerdict(str, Enum):
    GREEN    = "GREEN"       # 0 patterns hit
    YELLOW   = "YELLOW"      # 1-2 patterns hit, none CRITICAL
    RED      = "RED"         # 3+ patterns hit OR any CRITICAL
    CRITICAL = "CRITICAL"    # full named-case pattern match
                             # (Steward, Envision) replays cleanly


@dataclass
class PatternCheck:
    name: str                # short id, e.g. "STEWARD_PATTERN"
    category: str            # HISTORICAL | REGULATORY
    fired: bool
    severity: str = "LOW"    # LOW | MEDIUM | HIGH | CRITICAL
    case_study: Optional[str] = None
    narrative: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


@dataclass
class ScanInput:
    """Lightweight inputs — all from a teaser, no CCD required."""
    target_name: str
    specialty: Optional[str] = None          # e.g. EMERGENCY_MEDICINE
    states: List[str] = field(default_factory=list)
    msas: List[str] = field(default_factory=list)
    cbsa_codes: List[str] = field(default_factory=list)

    # Legal structure; drives CPOM kill-zone.
    legal_structure: Optional[str] = None    # e.g. FRIENDLY_PC_PASS_THROUGH

    # Real-estate fingerprint.
    landlord: Optional[str] = None
    lease_term_years: Optional[int] = None
    lease_escalator_pct: Optional[float] = None
    lease_rent_pct_revenue: Optional[float] = None
    ebitdar_coverage: Optional[float] = None
    geography: Optional[str] = None          # RURAL | SAFETY_NET | URBAN_ACADEMIC

    # NSA fingerprint.
    is_hospital_based_physician: bool = False
    oon_revenue_share: Optional[float] = None

    # Site-neutral fingerprint.
    has_grandfathered_hopd: bool = False
    hopd_revenue_annual_usd: Optional[float] = None

    # Antitrust / rollup.
    acquisitions: List[Dict[str, Any]] = field(default_factory=list)

    # Cano Health fingerprint (MA-risk primary care).
    is_ma_risk_primary_care: bool = False
    cac_payback_months: Optional[float] = None

    # Wellpath fingerprint.
    is_correctional_health: bool = False
    payer_hhi: Optional[float] = None        # top-payer concentration

    # APP fingerprint.
    locum_pct_staffing: Optional[float] = None


@dataclass
class BankruptcySurvivorScan:
    target_name: str
    computed_at: str
    checks: List[PatternCheck] = field(default_factory=list)
    verdict: BankruptcySurvivorVerdict = BankruptcySurvivorVerdict.GREEN
    named_comparisons: List[str] = field(default_factory=list)
    diligence_questions: List[str] = field(default_factory=list)

    @property
    def patterns_hit(self) -> int:
        return sum(1 for c in self.checks if c.fired)

    @property
    def critical_hits(self) -> int:
        return sum(1 for c in self.checks
                   if c.fired and c.severity == "CRITICAL")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_name": self.target_name,
            "computed_at": self.computed_at,
            "verdict": self.verdict.value,
            "patterns_hit": self.patterns_hit,
            "critical_hits": self.critical_hits,
            "checks": [c.to_dict() for c in self.checks],
            "named_comparisons": list(self.named_comparisons),
            "diligence_questions": list(self.diligence_questions),
        }


# ── Historical pattern checks ──────────────────────────────────────

def _check_steward(inp: ScanInput) -> PatternCheck:
    """Steward: hospital + REIT landlord + long lease + rural/safety
    net + suicidal rent share."""
    if not inp.landlord or inp.specialty not in ("HOSPITAL", None):
        return PatternCheck(
            name="STEWARD_PATTERN", category="HISTORICAL",
            fired=False, narrative="Insufficient lease data.",
        )
    # Use the real-estate Steward Score if we have enough fields.
    try:
        line = LeaseLine(
            property_id=inp.target_name,
            property_type=inp.specialty or "HOSPITAL",
            base_rent_annual_usd=1.0,            # placeholder; factor-only
            escalator_pct=inp.lease_escalator_pct or 0.0,
            term_years=inp.lease_term_years or 10,
            landlord=inp.landlord,
        )
        schedule = LeaseSchedule(lines=[line])
        rent_annual = inp.lease_rent_pct_revenue and inp.ebitdar_coverage
        # Use EBITDAR coverage field directly if given.
        result = compute_steward_score(
            schedule,
            portfolio_annual_rent_usd=1.0,
            portfolio_ebitdar_annual_usd=(
                float(inp.ebitdar_coverage) if inp.ebitdar_coverage else None
            ),
            geography=inp.geography,
        )
        tier = result.tier
    except Exception:  # noqa: BLE001
        tier = StewardRiskTier.LOW
    if tier == StewardRiskTier.CRITICAL:
        return PatternCheck(
            name="STEWARD_PATTERN", category="HISTORICAL", fired=True,
            severity="CRITICAL",
            case_study=(
                "Steward Health Care — 2016 MPT sale-leaseback "
                "(EV ~$1.25B at deal) → Ch. 11 May 2024."
            ),
            narrative=(
                "Target matches all 5 Steward pattern indicators: "
                "long lease + high escalator + thin EBITDAR coverage "
                "+ rural/safety-net geography + high-risk REIT landlord."
            ),
        )
    if tier == StewardRiskTier.HIGH:
        return PatternCheck(
            name="STEWARD_PATTERN", category="HISTORICAL", fired=True,
            severity="HIGH",
            case_study=(
                "Prospect Medical — 2019 Leonard Green/MPT (EV $1.55B) "
                "→ Ch. 11 January 2025."
            ),
            narrative=(
                "Target matches 4 of 5 Steward pattern indicators — "
                "matches Prospect Medical's 2019 deal-signing profile."
            ),
        )
    return PatternCheck(
        name="STEWARD_PATTERN", category="HISTORICAL",
        fired=False, severity="LOW",
        narrative=f"Steward Score tier {tier.value}.",
    )


def _check_envision(inp: ScanInput) -> PatternCheck:
    """Envision: hospital-based physician + high OON + PE ownership."""
    if not inp.is_hospital_based_physician:
        return PatternCheck(
            name="ENVISION_PATTERN", category="HISTORICAL",
            fired=False, narrative="Not a hospital-based physician group.",
        )
    oon = inp.oon_revenue_share
    if oon is None:
        return PatternCheck(
            name="ENVISION_PATTERN", category="HISTORICAL",
            fired=False, narrative="OON share not disclosed.",
        )
    if oon >= 0.35:
        return PatternCheck(
            name="ENVISION_PATTERN", category="HISTORICAL", fired=True,
            severity="CRITICAL",
            case_study=(
                "Envision Healthcare — 2018 KKR LBO $9.9B → "
                "Ch. 11 May 2023. NSA revenue impact accelerated the "
                "bankruptcy clock."
            ),
            narrative=(
                f"OON revenue share {oon*100:.0f}% exceeds the 35% "
                f"Envision threshold."
            ),
        )
    if oon >= 0.20:
        return PatternCheck(
            name="ENVISION_PATTERN", category="HISTORICAL", fired=True,
            severity="HIGH",
            case_study=(
                "Envision Healthcare (2023) — OON-heavy ER group pattern."
            ),
            narrative=(
                f"OON revenue share {oon*100:.0f}% exceeds the 20% "
                f"watch threshold."
            ),
        )
    return PatternCheck(
        name="ENVISION_PATTERN", category="HISTORICAL",
        fired=False, narrative=f"OON share {oon*100:.1f}% under threshold.",
    )


def _check_app(inp: ScanInput) -> PatternCheck:
    """APP: hospital-based physician + locum dependency + NSA + rollup."""
    if not inp.is_hospital_based_physician:
        return PatternCheck(
            name="APP_PATTERN", category="HISTORICAL", fired=False,
            narrative="Not hospital-based.",
        )
    locum = inp.locum_pct_staffing or 0.0
    nsa_present = bool(inp.oon_revenue_share and inp.oon_revenue_share >= 0.15)
    rollup = len(inp.acquisitions or ()) >= 3
    hits = sum([locum >= 0.30, nsa_present, rollup])
    if hits >= 2:
        return PatternCheck(
            name="APP_PATTERN", category="HISTORICAL", fired=True,
            severity="HIGH" if hits == 2 else "CRITICAL",
            case_study=(
                "American Physician Partners — 2016 LBO → July 2023 "
                "liquidation. Trustee filings cited $3.2M/mo NSA drag."
            ),
            narrative=(
                f"{hits} of 3 APP indicators present (locum dependency "
                f"{locum*100:.0f}%, NSA-OON {nsa_present}, "
                f"rollup {rollup})."
            ),
        )
    return PatternCheck(
        name="APP_PATTERN", category="HISTORICAL", fired=False,
        narrative=f"{hits}/3 indicators.",
    )


def _check_cano(inp: ScanInput) -> PatternCheck:
    """Cano: MA-risk primary care + CAC-heavy growth + V28 exposure."""
    if not inp.is_ma_risk_primary_care:
        return PatternCheck(
            name="CANO_PATTERN", category="HISTORICAL", fired=False,
            narrative="Not an MA-risk-bearing primary care platform.",
        )
    payback = inp.cac_payback_months or 0.0
    # Payback > 24 months on MA-risk PCPs is the Cano pattern.
    if payback > 24:
        return PatternCheck(
            name="CANO_PATTERN", category="HISTORICAL", fired=True,
            severity="CRITICAL",
            case_study=(
                "Cano Health — IPO'd at $4.4B (2021); Ch. 11 "
                "Feb 2024. V28 recalibration + member-acquisition-cost "
                "burn directly preceded failure."
            ),
            narrative=(
                f"CAC payback {payback:.0f}mo on MA-risk PCPs — "
                f"Cano's signature failure profile."
            ),
        )
    return PatternCheck(
        name="CANO_PATTERN", category="HISTORICAL", fired=True,
        severity="HIGH",
        case_study="Cano Health (2024) — MA-risk primary care failure.",
        narrative="MA-risk primary care is inherently exposed to V28.",
    )


def _check_prospect(inp: ScanInput) -> PatternCheck:
    """Prospect: hospital + MPT landlord + aggressive leverage +
    sale-leaseback. Overlaps with Steward pattern but triggers at
    a lower threshold (MPT landlord alone + hospital)."""
    mpt_landlord = bool(
        inp.landlord
        and any(key in inp.landlord.lower()
                for key in ("mpt", "medical properties trust"))
    )
    if not (mpt_landlord and (inp.specialty or "").upper() == "HOSPITAL"):
        return PatternCheck(
            name="PROSPECT_PATTERN", category="HISTORICAL", fired=False,
            narrative="No MPT-landlord hospital signature.",
        )
    # At this point we have the core pattern. Upgrade to CRITICAL
    # when the lease+coverage fingerprint is also bad.
    extras = sum([
        (inp.lease_term_years or 0) > 15,
        (inp.lease_escalator_pct or 0) > 0.03,
        (inp.ebitdar_coverage or 99) < 1.4,
    ])
    if extras >= 2:
        sev = "CRITICAL"
    elif extras == 1:
        sev = "HIGH"
    else:
        sev = "MEDIUM"
    return PatternCheck(
        name="PROSPECT_PATTERN", category="HISTORICAL", fired=True,
        severity=sev,
        case_study=(
            "Prospect Medical — 2019 Leonard Green/MPT (EV $1.55B); "
            "MPT wrote down the master-lease in 2023; Ch. 11 "
            "January 2025."
        ),
        narrative=(
            f"MPT-landlord hospital + {extras}/3 leverage indicators."
        ),
    )


def _check_wellpath(inp: ScanInput) -> PatternCheck:
    """Wellpath: correctional health + thin payer diversification +
    regulatory-complaint cluster. We approximate regulatory-complaint
    cluster via the payer HHI proxy (single-payer dependency)."""
    if not inp.is_correctional_health:
        return PatternCheck(
            name="WELLPATH_PATTERN", category="HISTORICAL", fired=False,
            narrative="Not a correctional health platform.",
        )
    hhi = inp.payer_hhi or 0.0
    if hhi >= 5000:      # single-payer dominance
        sev = "CRITICAL"
    elif hhi >= 3500:
        sev = "HIGH"
    else:
        sev = "MEDIUM"
    return PatternCheck(
        name="WELLPATH_PATTERN", category="HISTORICAL", fired=True,
        severity=sev,
        case_study=(
            "Wellpath — correctional healthcare platform → Ch. 11 "
            "November 2024. Insufficient payer diversity + "
            "litigation exposure compounded the collapse."
        ),
        narrative=(
            f"Correctional health + payer HHI {hhi:.0f} "
            f"({sev.lower()} severity)."
        ),
    )


# ── Regulatory forward-looking pattern checks ─────────────────────

def _check_cpom_kill_zone(inp: ScanInput) -> PatternCheck:
    states = inp.states or []
    structure = inp.legal_structure
    if not states or not structure:
        return PatternCheck(
            name="CPOM_KILL_ZONE", category="REGULATORY", fired=False,
            narrative="Insufficient structure / state data.",
        )
    try:
        rep = compute_cpom_exposure(
            target_structure=structure,
            footprint_states=states,
        )
    except ValueError:
        return PatternCheck(
            name="CPOM_KILL_ZONE", category="REGULATORY", fired=False,
            narrative=f"Unknown structure {structure!r}.",
        )
    if rep.overall_band == RegulatoryBand.RED:
        red_states = [s.state_code for s in rep.per_state
                      if s.band == RegulatoryBand.RED]
        return PatternCheck(
            name="CPOM_KILL_ZONE", category="REGULATORY", fired=True,
            severity="CRITICAL",
            case_study=(
                "Oregon SB 951 / California SB 351 CPOM reform wave."
            ),
            narrative=(
                f"Target structure {structure} voided in: "
                f"{', '.join(red_states)}"
            ),
        )
    if rep.overall_band == RegulatoryBand.YELLOW:
        return PatternCheck(
            name="CPOM_KILL_ZONE", category="REGULATORY", fired=True,
            severity="MEDIUM",
            narrative="CPOM restrictions apply; not an outright ban.",
        )
    return PatternCheck(
        name="CPOM_KILL_ZONE", category="REGULATORY", fired=False,
        narrative=f"CPOM posture {rep.overall_band.value}.",
    )


def _check_team_exposure(inp: ScanInput) -> PatternCheck:
    if not inp.cbsa_codes:
        return PatternCheck(
            name="TEAM_DOWNSIDE", category="REGULATORY", fired=False,
            narrative="No CBSA data provided.",
        )
    hits = [c for c in inp.cbsa_codes if is_cbsa_mandatory(c)]
    if hits:
        return PatternCheck(
            name="TEAM_DOWNSIDE", category="REGULATORY", fired=True,
            severity="HIGH",
            case_study="CMS TEAM final rule (effective 2026-01-01).",
            narrative=(
                f"Target operates in TEAM-mandatory CBSA(s): "
                f"{', '.join(hits)}. Track 2 downside exposure applies."
            ),
        )
    return PatternCheck(
        name="TEAM_DOWNSIDE", category="REGULATORY", fired=False,
        narrative="No mandatory CBSA match.",
    )


def _check_nsa_cliff(inp: ScanInput) -> PatternCheck:
    if not inp.is_hospital_based_physician:
        return PatternCheck(
            name="NSA_CLIFF", category="REGULATORY", fired=False,
            narrative="Not a hospital-based physician group.",
        )
    if inp.oon_revenue_share is None:
        return PatternCheck(
            name="NSA_CLIFF", category="REGULATORY", fired=False,
            narrative="OON share not disclosed.",
        )
    if inp.oon_revenue_share >= 0.20:
        return PatternCheck(
            name="NSA_CLIFF", category="REGULATORY", fired=True,
            severity="HIGH" if inp.oon_revenue_share < 0.35 else "CRITICAL",
            narrative=(
                f"{inp.oon_revenue_share*100:.0f}% OON revenue "
                f"exposes target to NSA IDR compression."
            ),
        )
    return PatternCheck(
        name="NSA_CLIFF", category="REGULATORY", fired=False,
        narrative="OON share below 20% threshold.",
    )


def _check_site_neutral(inp: ScanInput) -> PatternCheck:
    if not inp.has_grandfathered_hopd:
        return PatternCheck(
            name="SITE_NEUTRAL_EROSION", category="REGULATORY",
            fired=False, narrative="No grandfathered HOPD exposure.",
        )
    sev = "HIGH"
    hopd_rev = inp.hopd_revenue_annual_usd or 0.0
    if hopd_rev > 50_000_000:
        sev = "CRITICAL"
    return PatternCheck(
        name="SITE_NEUTRAL_EROSION", category="REGULATORY", fired=True,
        severity=sev,
        case_study=(
            "CY2026 OPPS final rule (40% drug-admin rate in "
            "grandfathered off-campus HOPDs) + MedPAC all-ambulatory "
            "proposal ($31.2B 10-year industry hit)."
        ),
        narrative=(
            f"Grandfathered HOPD with ${hopd_rev:,.0f} annual revenue "
            f"at migration risk."
        ),
    )


def _check_antitrust_rollup(inp: ScanInput) -> PatternCheck:
    if not inp.acquisitions or not inp.specialty:
        return PatternCheck(
            name="ANTITRUST_ROLLUP", category="REGULATORY", fired=False,
            narrative="No acquisition history provided.",
        )
    ex = compute_antitrust_exposure(
        target_specialty=inp.specialty,
        target_msas=inp.msas,
        acquisitions=inp.acquisitions,
    )
    if ex.band == RegulatoryBand.RED:
        return PatternCheck(
            name="ANTITRUST_ROLLUP", category="REGULATORY", fired=True,
            severity="CRITICAL",
            case_study=(
                "Welsh Carson / US Anesthesia Partners FTC consent "
                "order (2024) — 30-day prior-notice regime."
            ),
            narrative=(
                f"{ex.acquisition_count} same-MSA same-specialty "
                f"tuck-ins; 30-day FTC notice triggered."
            ),
        )
    if ex.band == RegulatoryBand.YELLOW:
        return PatternCheck(
            name="ANTITRUST_ROLLUP", category="REGULATORY", fired=True,
            severity="MEDIUM", narrative="Watch-tier concentration.",
        )
    return PatternCheck(
        name="ANTITRUST_ROLLUP", category="REGULATORY", fired=False,
        narrative=f"Antitrust band {ex.band.value}.",
    )


def _check_sale_leaseback_blocker(inp: ScanInput) -> PatternCheck:
    if not inp.states:
        return PatternCheck(
            name="SALE_LEASEBACK_BLOCKER", category="REGULATORY",
            fired=False, narrative="No state data.",
        )
    blockers = sale_leaseback_feasibility(inp.states)
    not_feasible = [b for b in blockers if not b.feasible]
    if not_feasible:
        codes = ", ".join(b.state_code for b in not_feasible)
        return PatternCheck(
            name="SALE_LEASEBACK_BLOCKER", category="REGULATORY",
            fired=True, severity="HIGH",
            case_study="MA H.5159 / CT HB 5316 enacted sale-leaseback regimes.",
            narrative=(
                f"Sale-leaseback exit blocked in: {codes}."
            ),
        )
    return PatternCheck(
        name="SALE_LEASEBACK_BLOCKER", category="REGULATORY",
        fired=False, narrative="No state-level blockers.",
    )


# ── Orchestration ──────────────────────────────────────────────────

_HISTORICAL_CHECKERS = (
    _check_steward, _check_envision, _check_app,
    _check_cano, _check_prospect, _check_wellpath,
)

_REGULATORY_CHECKERS = (
    _check_cpom_kill_zone, _check_team_exposure, _check_nsa_cliff,
    _check_site_neutral, _check_antitrust_rollup,
    _check_sale_leaseback_blocker,
)


def _verdict_for(checks: List[PatternCheck]) -> BankruptcySurvivorVerdict:
    fired = [c for c in checks if c.fired]
    critical = [c for c in fired if c.severity == "CRITICAL"]
    if critical:
        return BankruptcySurvivorVerdict.CRITICAL
    if len(fired) >= 3:
        return BankruptcySurvivorVerdict.RED
    if len(fired) >= 1:
        return BankruptcySurvivorVerdict.YELLOW
    return BankruptcySurvivorVerdict.GREEN


def _diligence_questions_for(checks: List[PatternCheck]) -> List[str]:
    qs: List[str] = []
    for c in checks:
        if not c.fired:
            continue
        if c.name == "STEWARD_PATTERN":
            qs.append(
                "Request the full master-lease schedule, escalator "
                "language, termination fees, and guarantor structure "
                "for every REIT-owned property."
            )
        elif c.name == "ENVISION_PATTERN":
            qs.append(
                "Quantify OON revenue by payer + specialty and "
                "project QPA revert impact under CY2026 IDR anchoring."
            )
        elif c.name == "APP_PATTERN":
            qs.append(
                "Provide locum dependency trend 2021-2025 + NSA "
                "monthly drag figures + acquisition history in "
                "regulated MSAs."
            )
        elif c.name == "CANO_PATTERN":
            qs.append(
                "Document member-acquisition-cost payback curve + "
                "V28 recalibration modeling per member."
            )
        elif c.name == "PROSPECT_PATTERN":
            qs.append(
                "Disclose full MPT lease terms, any write-down "
                "history, and landlord-interest in target's operating "
                "decisions."
            )
        elif c.name == "WELLPATH_PATTERN":
            qs.append(
                "Payer concentration by contract + pending "
                "litigation schedule + state DOC contract renewals."
            )
        elif c.name == "CPOM_KILL_ZONE":
            qs.append(
                "Counsel opinion on whether the target's MSO/PC or "
                "friendly-PC structure would be voided under each "
                "state's CPOM regime at close."
            )
        elif c.name == "TEAM_DOWNSIDE":
            qs.append(
                "Pull 3-year baseline DRG spending for LEJR/SHFFT/"
                "spinal fusion/CABG/bowel; project Track 2 P&L under "
                "the CMS target-price formula."
            )
        elif c.name == "NSA_CLIFF":
            qs.append(
                "Reconcile seller-claimed OON rates to current CMS-"
                "published QPA benchmarks by CPT."
            )
        elif c.name == "SITE_NEUTRAL_EROSION":
            qs.append(
                "Identify every grandfathered off-campus HOPD + "
                "project CY2026 drug-admin rate cuts + MedPAC scenario."
            )
        elif c.name == "ANTITRUST_ROLLUP":
            qs.append(
                "Compute post-close HHI at MSA × specialty; file HSR "
                "notice 30 days pre-close if in USAP-precedent zone."
            )
        elif c.name == "SALE_LEASEBACK_BLOCKER":
            qs.append(
                "Confirm exit options in affected states; reverse "
                "sale-leaseback is ruled out in MA; CT window closes "
                "October 2027."
            )
    # De-duplicate while preserving order.
    seen = set()
    out = []
    for q in qs:
        if q not in seen:
            seen.add(q)
            out.append(q)
    return out


def run_bankruptcy_survivor_scan(inp: ScanInput) -> BankruptcySurvivorScan:
    """Execute all 12 pattern checks and return the scan."""
    checks: List[PatternCheck] = []
    for chk in _HISTORICAL_CHECKERS + _REGULATORY_CHECKERS:
        try:
            checks.append(chk(inp))
        except Exception as exc:  # noqa: BLE001
            checks.append(PatternCheck(
                name=chk.__name__.upper().replace("_CHECK", ""),
                category="HISTORICAL"
                    if chk in _HISTORICAL_CHECKERS else "REGULATORY",
                fired=False,
                narrative=f"Check error: {type(exc).__name__}: {exc}",
            ))
    verdict = _verdict_for(checks)
    comparisons = [
        c.case_study for c in checks
        if c.fired and c.case_study
    ]
    diligence_questions = _diligence_questions_for(checks)
    return BankruptcySurvivorScan(
        target_name=inp.target_name,
        computed_at=datetime.now(timezone.utc).isoformat(),
        checks=checks,
        verdict=verdict,
        named_comparisons=comparisons,
        diligence_questions=diligence_questions,
    )
