"""CPOM State Lattice — Corporate Practice of Medicine 50-state compliance matrix.

The Corporate Practice of Medicine doctrine prohibits (to varying degrees
by state) non-physician-owned corporate entities from directly employing
physicians or controlling clinical judgment. For PE-backed physician
group investments, the state where professional services are delivered
determines:

    - Whether the platform can use a Friendly PC / Friendly Physician
      structure (MSO + Professional Corporation)
    - What fee-splitting / management-fee arrangements are permitted
    - What non-compete, non-solicit, and clinical-judgment controls
      can be built into the MSO agreement
    - Whether recent AG enforcement has limited structural options

Every PE-backed physician group deal must file into one of a half-dozen
canonical MSO structures calibrated to the state lattice. Getting the
structure wrong means:

    - Potential unenforceability of the MSO agreement
    - State AG enforcement action (CA, MA, NY active 2020-2026)
    - Piercing of the corporate veil in disputes
    - Tax treatment complications (state-level B&O / gross receipts)

This module encodes all 50 states + DC with structured fields. Top PE-
active states receive detailed enforcement history and structural
guidance. All states carry at minimum the CPOM regime tier, statute
citation, and MSO-viability classification.

Integrates with:
    - ic_brief.py — physician-group targets auto-pull state regime + risk
    - doj_fca_tracker.py — FCA settlements often reveal CPOM-adjacent
      structural abuse (Stark/AKS patterns)
    - oig_workplan.py — OIG has active items on MSO-physician-comp
      arrangements

Knowledge base: versioned. Each state carries effective-date + last-
revised + citation to state statute + key AG opinions.

Public API
----------
    CPOMRegimeTier                  enum-like (strict / moderate / friendly / none)
    CPOMState                       one state's full CPOM profile
    CPOMEnforcementAction           recent AG/court action
    CorpusStateOverlay              per-corpus-deal state-risk lookup
    CPOMStateLatticeResult          composite output
    compute_cpom_state_lattice()    -> CPOMStateLatticeResult
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Knowledge-base versioning
# ---------------------------------------------------------------------------

_KB_VERSION = "v1.0.0"
_KB_EFFECTIVE_DATE = "2026-01-01"
_SOURCE_CITATIONS = [
    "American Medical Association Issue Brief: Corporate Practice of Medicine",
    "State medical board rulings and advisory opinions (individual citations per state)",
    "American Health Law Association — CPOM survey updates",
    "Polsinelli / ArentFox Schiff / Foley & Lardner state-CPOM practice surveys",
    "Westlaw 50-state healthcare-practice-restrictions annotations",
    "State Attorneys General active-enforcement press releases",
]


# Regime tiers
_TIER_STRICT = "strict"         # CPOM fully enforced; limited MSO structures viable
_TIER_MODERATE = "moderate"     # CPOM with exceptions; Friendly PC workable with care
_TIER_FRIENDLY = "friendly"     # CPOM limited / easily workable
_TIER_NONE = "none"             # no CPOM doctrine / not state-enforced


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class CPOMEnforcementAction:
    """One recent state AG action or court ruling establishing precedent."""
    year: int
    state: str
    action_type: str               # "AG opinion" / "Court ruling" / "Board action" / "Statute change"
    target_or_case: str
    summary: str
    citation: str


@dataclass
class CPOMState:
    """One state's full CPOM + MSO profile."""
    state_code: str                # "CA" / "NY" / "DC"
    state_name: str
    regime_tier: str               # _TIER_* constant
    cpom_doctrine_summary: str
    permitted_structures: List[str]  # "Professional Corp", "MSO / Friendly PC", "LLP", "Nonprofit only"
    mso_friendly: bool             # can a PE MSO manage a physician group?
    fee_splitting_allowed: bool    # can MSO receive percentage-of-revenue fee?
    non_compete_enforceability: str  # "enforced" / "limited" / "unenforceable"
    key_statute: str               # primary state statute or regulation
    key_regulatory_body: str       # e.g., "Medical Board of California"
    recent_enforcement_count: int  # number of AG / court actions last 5 years
    notable_enforcement: List[str] # 1-3 bullet points of notable recent actions
    pe_activity_intensity: str     # "very high" / "high" / "moderate" / "low"
    structural_risk_score: int     # 0-100 (higher = more risk)
    diligence_note: str
    last_revised_year: int
    primary_citation: str          # primary source URL or statute reference


@dataclass
class CorpusStateOverlay:
    """Per-corpus-deal state-risk lookup for physician-group targets."""
    deal_name: str
    deal_year: int
    inferred_state: str            # best-guess state from deal notes
    state_regime_tier: str
    mso_friendly: bool
    structural_risk_score: int
    enforcement_concerns: List[str]
    risk_tier: str                 # "CRITICAL" / "HIGH" / "MEDIUM" / "LOW" / "N/A"


@dataclass
class CPOMStateLatticeResult:
    knowledge_base_version: str
    effective_date: str
    source_citations: List[str]

    states: List[CPOMState]
    enforcement_actions: List[CPOMEnforcementAction]
    corpus_overlays: List[CorpusStateOverlay]

    # Aggregate stats
    total_states: int
    strict_tier_count: int
    moderate_tier_count: int
    friendly_tier_count: int
    none_tier_count: int
    mso_friendly_count: int
    fee_split_allowed_count: int
    avg_risk_score: float
    corpus_deals_with_state_match: int
    critical_exposure_count: int

    corpus_deal_count: int


# ---------------------------------------------------------------------------
# Corpus loader
# ---------------------------------------------------------------------------

def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 122):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            deals.extend(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    return deals


# ---------------------------------------------------------------------------
# State catalog — all 50 states + DC
# ---------------------------------------------------------------------------

def _build_states() -> List[CPOMState]:
    """Full 50-state + DC CPOM lattice.

    Top 20 PE-active states get detailed profiles; remaining states have
    structured-but-terser entries with tier + statute + MSO viability.
    """
    return [
        # ==== TIER 1: STRICT CPOM STATES (major PE activity) ====
        CPOMState(
            "CA", "California", _TIER_STRICT,
            "California strictly enforces CPOM via Medical Practice Act + Business & Professions Code. Corporations cannot practice medicine. Physicians must control clinical decisions. Non-physician ownership of medical practices prohibited. Friendly PC / MSO structure required.",
            ["Professional Corporation (PC)", "Friendly PC w/ MSO", "Medical Group"],
            True, True,
            "Enforced with duration/geographic limits (B&P § 16600 makes most non-competes unenforceable except in sale-of-business context)",
            "Cal. Bus. & Prof. Code §§ 2400, 2401, 16600; Medical Board of CA regulations",
            "Medical Board of California; Attorney General's office",
            4,
            [
                "CA AG v. Optum/DaVita Medical Group structural review (2022-2024)",
                "OHCA Office of Health Care Affordability material-change filings mandatory >$25M (2024+)",
                "Envision / USAP FTC antitrust proceedings also implicate CA structural concerns",
            ],
            "very high", 78,
            "CA is the strictest CPOM jurisdiction for PE-backed physician groups. Friendly PC + MSO structure is mandatory; MSO fee structures must be carefully calibrated to avoid fee-splitting challenges. Recent OHCA material-change notice requirements add regulatory overhead. Every PE physician-group deal with CA operations needs formal CPOM structure opinion.",
            2024, "https://www.mbc.ca.gov/Licensees/CorporatePractice/",
        ),
        CPOMState(
            "NY", "New York", _TIER_STRICT,
            "New York enforces CPOM via Education Law § 6530 and public-policy doctrine. Lay corporations cannot practice medicine. DOH has rejected attempted PE structures. Friendly PC + MSO is workable but scrutinized.",
            ["Professional Corporation", "Friendly PC / MSO", "PLLC (professional LLC)"],
            True, True,
            "Limited — NY courts require duration + geographic + consideration; post-hire non-competes scrutinized heavily (FTC national rule status unclear)",
            "NY Education Law § 6530; Public Health Law Article 28; BCL § 1503",
            "NY Office of Professions; Department of Health",
            5,
            [
                "NY AG investigation of Optum-owned physician practices (2023)",
                "NY DOH rejection of proposed PE ownership structures 2020-2023",
                "Pending NY legislation (S7492) on healthcare transaction disclosure",
            ],
            "very high", 75,
            "NY is second-strictest after CA. DOH actively reviews PE-backed physician group structures and has rejected certain arrangements. MSO fee caps (typically market-rate management fee + reasonable admin) must be defensible. Article 28 licensure for facilities adds complexity.",
            2024, "https://www.op.nysed.gov/professions/medicine",
        ),
        CPOMState(
            "TX", "Texas", _TIER_STRICT,
            "Texas enforces CPOM via Texas Medical Practice Act. Only physicians + PAs/NPs with delegation may practice. Corporation may not employ physicians directly. Some exceptions for hospital employment via 501(c)(3).",
            ["Professional Association (PA)", "Professional LLC", "MSO / Friendly PA"],
            True, True,
            "Enforced — Texas has relatively business-friendly non-compete regime but physician-specific limits apply (TBA § 15.50 et seq.)",
            "Texas Occupations Code § 164.052; Medical Practice Act",
            "Texas Medical Board; Texas Department of Insurance",
            3,
            [
                "TMB enforcement actions on PE-related structural complaints 2022-2023",
                "Texas 2023 legislation expanding telehealth PE structural permissibility",
                "FTC Welsh Carson / USAP (SDTX) action — Texas state court parallel proceedings",
            ],
            "high", 68,
            "Texas is strict on paper but more transactionally workable than CA/NY in practice. Hospital-employment exception via 501(c)(3) or 5.01(a) is widely used. MSO structures must document physician control of clinical decisions.",
            2023, "https://www.tmb.state.tx.us/page/statutes-and-rules",
        ),
        CPOMState(
            "FL", "Florida", _TIER_MODERATE,
            "Florida does NOT have a strict CPOM doctrine at the statutory level. Physicians may be employed by for-profit corporations. Fee-splitting restrictions apply via statute.",
            ["Professional Service Corporation", "LLC", "For-profit corporation (physician-employer)"],
            True, True,
            "Enforced with reasonable scope/duration (FL Stat § 542.335)",
            "Fla. Stat. § 458.331 (fee splitting); § 817.505 (patient brokering); no blanket CPOM",
            "Florida Board of Medicine; Agency for Health Care Administration",
            2,
            [
                "FL DOH prosecutorial actions on fee-splitting arrangements 2022-2024",
                "Patient brokering act enforcement increasing, esp. in SUD / behavioral health",
                "Cano Health bankruptcy FL-centric (2024)",
            ],
            "very high", 52,
            "FL is the MOST PE-friendly of the top-5 PE-active states. No CPOM doctrine means direct corporate employment of physicians is viable. Watch fee-splitting (Fla § 458.331) and patient-brokering statutes; penalties severe. FL is the preferred jurisdiction for many PE physician-group platforms.",
            2024, "https://flboardofmedicine.gov/statutes-rules/",
        ),
        CPOMState(
            "IL", "Illinois", _TIER_STRICT,
            "Illinois enforces CPOM via the Medical Practice Act. Corporation may not practice medicine. Physicians must form a medical corporation or PLLC.",
            ["Medical Corporation", "Professional LLC", "Friendly PC / MSO"],
            True, True,
            "Enforced with scrutiny — IL Freedom to Work Act (2022) further limits non-competes",
            "225 ILCS 60/; 805 ILCS 15/ (Medical Corporation Act)",
            "Illinois Department of Financial and Professional Regulation",
            2,
            [
                "IL AG rev of Optum-owned physician group structure 2023",
                "Freedom to Work Act (2022) limits physician non-compete enforcement",
            ],
            "high", 65,
            "IL CPOM is strictly enforced. Non-compete enforceability further limited under Freedom to Work Act 2022. MSO structures common but require careful structuring.",
            2023, "https://www.idfpr.com/profs/info/physicians.asp",
        ),
        CPOMState(
            "MA", "Massachusetts", _TIER_STRICT,
            "Massachusetts enforces CPOM via common-law doctrine and Board of Registration rulings. Lay corporations may not employ physicians directly. MSO + Friendly PC required.",
            ["Professional Corporation", "Friendly PC / MSO"],
            True, True,
            "Limited — MA Non-Compete Act (2018) requires consideration + 50% garden-leave pay; physician-specific statutes further limit",
            "M.G.L. c. 112, § 12X; Board of Registration regulations",
            "MA Board of Registration in Medicine; Attorney General; Health Policy Commission",
            4,
            [
                "Steward Health Care state AG investigation 2022-2024",
                "HPC material-change review authority (all healthcare transactions reviewable)",
                "Optum / MA physician-group rev 2023",
            ],
            "high", 72,
            "MA CPOM is strict and HPC material-change review is mandatory for transactions >$10M. Post-Steward AG attention heightened. Structural opinions should address both CPOM + HPC review + Steward-era enforcement posture.",
            2024, "https://www.mass.gov/topics/health-policy-commission",
        ),
        CPOMState(
            "PA", "Pennsylvania", _TIER_MODERATE,
            "PA applies limited CPOM via case law and Medical Practice Act. Professional corporations required for practice of medicine.",
            ["Professional Corporation", "PLLC", "MSO / Friendly PC"],
            True, True,
            "Enforced with scrutiny (reasonable scope)",
            "Pa. Medical Practice Act (63 P.S. § 422.1 et seq.); BCL § 2901 et seq.",
            "Pennsylvania State Board of Medicine",
            1,
            ["PA AG healthcare antitrust guidance 2023"],
            "high", 55,
            "PA is more moderate than CA/NY/IL. PC formation required; MSO structures workable. Recent focus on non-compete enforcement.",
            2023, "https://www.dos.pa.gov/ProfessionalLicensing/BoardsCommissions/Medicine/",
        ),
        CPOMState(
            "OH", "Ohio", _TIER_MODERATE,
            "Ohio applies CPOM via Ohio Medical Board rulings and limited statute. Professional corporations required.",
            ["Professional Corporation", "LLC w/ physician members", "MSO / Friendly PC"],
            True, True,
            "Enforced (reasonable scope)",
            "Ohio Rev. Code § 4731; State Medical Board rules",
            "State Medical Board of Ohio",
            1, [], "high", 45,
            "OH is workable for PE physician-group investments. MSO structures common; focus on documenting physician clinical authority.",
            2022, "https://med.ohio.gov/laws-rules",
        ),
        CPOMState(
            "GA", "Georgia", _TIER_MODERATE,
            "Georgia enforces CPOM via case law; PC required for practice. No detailed statutory framework but AG opinions establish doctrine.",
            ["Professional Corporation", "MSO / Friendly PC"],
            True, True, "Enforced with scrutiny",
            "O.C.G.A. § 14-7-1 et seq.; AG opinions",
            "Georgia Composite Medical Board",
            1, [], "high", 48,
            "GA is moderate CPOM. PC required; MSO structures generally workable. Healthcare-antitrust attention increased post-Envision.",
            2022, "https://medicalboard.georgia.gov/",
        ),
        CPOMState(
            "NC", "North Carolina", _TIER_MODERATE,
            "NC requires PC formation; MSO structures allowed. Fee-splitting prohibited under state statute.",
            ["Professional Corporation", "PLLC", "MSO / Friendly PC"],
            True, True, "Enforced",
            "N.C.G.S. § 55B; Medical Board rules",
            "North Carolina Medical Board",
            1, [], "high", 45,
            "NC moderate CPOM. Fee-splitting statute active. MSO structures common in PE physician-group deals.",
            2022, "https://www.ncmedboard.org/",
        ),

        # ==== TIER 2: MODERATE STATES — top PE activity ====
        CPOMState(
            "NJ", "New Jersey", _TIER_MODERATE,
            "NJ requires PC formation for medical practice; MSO structures allowed with fee-split restrictions.",
            ["Professional Corporation", "PLLC", "MSO / Friendly PC"],
            True, True, "Enforced with scrutiny",
            "N.J.S.A. § 14A:17-1 et seq.; Board of Medical Examiners rules",
            "NJ Board of Medical Examiners",
            1, [], "high", 50,
            "NJ moderate — PC required; MSO structures workable. Fee-splitting enforcement active.",
            2023, "https://www.njconsumeraffairs.gov/bme",
        ),
        CPOMState(
            "VA", "Virginia", _TIER_MODERATE,
            "VA requires PC formation; MSO structures generally workable with documentation of physician clinical control.",
            ["Professional Corporation", "PLLC", "MSO / Friendly PC"],
            True, True, "Enforced",
            "Va. Code § 13.1-542 et seq.",
            "Virginia Board of Medicine",
            1, [], "moderate", 42,
            "VA workable. Less active enforcement than NC/GA/NJ.",
            2022, "https://www.dhp.virginia.gov/medicine/",
        ),
        CPOMState(
            "MI", "Michigan", _TIER_MODERATE,
            "MI permits corporate employment of physicians via hospital exception; CPOM doctrine limited.",
            ["Professional Service Corporation", "PC w/ MSO", "Hospital-employed physicians"],
            True, True, "Enforced with reasonableness",
            "MCL § 450.221 et seq.; Public Health Code",
            "Michigan Board of Medicine",
            1, [], "moderate", 38,
            "MI relatively workable. Hospital-employment exception widely used.",
            2022, "https://www.michigan.gov/lara/bureau-list/bpl/health/hp-lic-health-prof/medicine",
        ),
        CPOMState(
            "WA", "Washington", _TIER_STRICT,
            "WA enforces CPOM with moderate strictness; MSO required. HB 2548 (2024) adds healthcare-transaction disclosure.",
            ["Professional Service Corporation", "PLLC", "MSO / Friendly PC"],
            True, True, "Limited",
            "RCW 18.100 et seq.; Healthcare Consolidation Review (HB 2548)",
            "Washington Medical Commission",
            2,
            [
                "WA healthcare transaction disclosure law HB 2548 (effective 2025)",
                "Optum-owned practice structural review 2023",
            ],
            "high", 62,
            "WA is strict CPOM with emerging transaction-review regime. HB 2548 adds disclosure similar to OR HCMO / CA OHCA.",
            2024, "https://www.doh.wa.gov/licenses-permits-and-certificates/",
        ),
        CPOMState(
            "CO", "Colorado", _TIER_FRIENDLY,
            "CO has no strict CPOM doctrine; physicians may be directly employed by corporations. Fee-splitting limits apply.",
            ["Professional Corporation", "LLC", "For-profit corporation (employer)"],
            True, True, "Enforced with scrutiny (CO HB 22-1317 limits post-employment non-competes)",
            "C.R.S. § 12-240-107; CDPHE rules",
            "Colorado Medical Board",
            1, [], "high", 35,
            "CO is friendly to PE structures. No blanket CPOM; direct employment of physicians permitted.",
            2023, "https://cdphe.colorado.gov/",
        ),
        CPOMState(
            "AZ", "Arizona", _TIER_FRIENDLY,
            "AZ has no strict CPOM doctrine. Physicians may be employed by corporations. Adeptus freestanding-ED precedent limits FSER structures.",
            ["Professional Corporation", "LLC", "For-profit corporation"],
            True, True, "Enforced",
            "A.R.S. § 32-1401 et seq.",
            "Arizona Medical Board",
            1, ["Adeptus bankruptcy 2017 (AZ-TX)"], "high", 38,
            "AZ is friendly. Watch freestanding-ED regulations post-Adeptus.",
            2022, "https://azmd.gov/",
        ),
        CPOMState(
            "TN", "Tennessee", _TIER_MODERATE,
            "TN requires PC formation; MSO structures workable.",
            ["Professional Corporation", "LLC", "MSO / Friendly PC"],
            True, True, "Enforced",
            "Tenn. Code § 48-101-601 et seq.",
            "Tennessee Board of Medical Examiners",
            1, [], "high", 45,
            "TN moderate. Active healthcare PE market; MSO structures standard.",
            2022, "https://www.tn.gov/health/health-program-areas/health-professional-boards/me-board.html",
        ),
        CPOMState(
            "MO", "Missouri", _TIER_MODERATE,
            "MO applies CPOM via case law; PC required.",
            ["Professional Corporation", "LLC", "MSO / Friendly PC"],
            True, True, "Enforced with reasonable scope",
            "Mo. Rev. Stat. § 356 et seq.",
            "Missouri Board of Registration for the Healing Arts",
            1, [], "moderate", 42,
            "MO moderate. Less enforcement visibility than MA/NY/CA.",
            2022, "https://pr.mo.gov/healingarts.asp",
        ),
        CPOMState(
            "MN", "Minnesota", _TIER_STRICT,
            "MN applies strict CPOM via case law. Physicians must form professional entities; MSO structures require careful design.",
            ["Professional Corporation", "Professional LLC", "MSO / Friendly PC"],
            True, True, "Limited (post-employment non-competes enforced narrowly)",
            "Minn. Stat. § 147; § 319B (professional firms)",
            "Minnesota Board of Medical Practice",
            1, [], "high", 62,
            "MN strict CPOM. PC required; active APCD state. Structural opinions recommended.",
            2023, "https://mn.gov/boards/medical-practice/",
        ),
        CPOMState(
            "IN", "Indiana", _TIER_MODERATE,
            "IN requires PC formation; MSO structures workable.",
            ["Professional Corporation", "MSO / Friendly PC"],
            True, True, "Enforced",
            "Ind. Code § 23-1.5 (professional corporations)",
            "Indiana Medical Licensing Board",
            1, [], "moderate", 42,
            "IN moderate. Recently adopted healthcare transaction disclosure.",
            2023, "https://www.in.gov/pla/",
        ),

        # ==== TIER 3: Remaining states — terser structured entries ====
        CPOMState("WI", "Wisconsin", _TIER_MODERATE, "WI moderate CPOM; PC required.",
                  ["Professional Corporation", "MSO / Friendly PC"], True, True, "Enforced",
                  "Wis. Stat. § 180.1901 et seq.", "WI Medical Examining Board",
                  0, [], "moderate", 42, "Workable.", 2022, "https://dsps.wi.gov/Pages/Professions/MD/Default.aspx"),
        CPOMState("MD", "Maryland", _TIER_MODERATE, "MD moderate CPOM; PC required; Global Budget Hospital Model adds unique regulatory overlay.",
                  ["Professional Corporation", "LLC", "MSO / Friendly PC"], True, True, "Enforced",
                  "Md. Code Bus. Occ. & Prof. § 14-101 et seq.", "MD Board of Physicians",
                  1, [], "high", 48, "MD Global Budget Model makes hospital deals structurally distinct.",
                  2023, "https://www.mbp.state.md.us/"),
        CPOMState("CT", "Connecticut", _TIER_MODERATE, "CT moderate CPOM; PC required.",
                  ["Professional Corporation", "MSO / Friendly PC"], True, True, "Enforced with scrutiny",
                  "Conn. Gen. Stat. § 33-182a et seq.; OHS transaction review",
                  "CT Department of Public Health; Office of Health Strategy",
                  1, ["CT OHS mandatory transaction review >$10M"], "high", 55,
                  "CT has OHS transaction-review overlay similar to MA HPC.", 2023, "https://portal.ct.gov/DPH"),
        CPOMState("OR", "Oregon", _TIER_STRICT, "OR strict CPOM; PC required. HB 4130 (2023) healthcare-transaction approval required >$10M.",
                  ["Professional Corporation", "MSO / Friendly PC"], True, True, "Enforced with scrutiny",
                  "ORS Chapter 677; OR Health Care Market Oversight (HCMO)",
                  "OR Medical Board; Health Care Market Oversight Program",
                  2, ["HCMO transaction approval required >$10M (2023+)"], "high", 68,
                  "OR HCMO pre-approval for healthcare transactions changes deal timelines materially.",
                  2023, "https://www.oregon.gov/mb/Pages/default.aspx"),
        CPOMState("NV", "Nevada", _TIER_FRIENDLY, "NV friendly CPOM; direct employment of physicians permitted.",
                  ["Professional Entity", "LLC", "For-profit corporation"], True, True, "Enforced",
                  "NRS Chapter 630", "Nevada State Board of Medical Examiners",
                  0, [], "moderate", 35, "NV friendly.", 2022, "https://medboard.nv.gov/"),
        CPOMState("KY", "Kentucky", _TIER_MODERATE, "KY moderate CPOM; PC required.",
                  ["Professional Corporation", "MSO / Friendly PC"], True, True, "Enforced",
                  "KRS § 274.005 et seq.", "KY Board of Medical Licensure",
                  0, [], "moderate", 42, "Workable.", 2022, "https://kbml.ky.gov/"),
        CPOMState("AL", "Alabama", _TIER_MODERATE, "AL moderate CPOM; PC required.",
                  ["Professional Corporation", "MSO / Friendly PC"], True, True, "Enforced",
                  "Ala. Code § 10A-4-1.01 et seq.", "AL State Board of Medical Examiners",
                  0, [], "moderate", 42, "Workable.", 2022, "https://www.albme.gov/"),
        CPOMState("SC", "South Carolina", _TIER_MODERATE, "SC moderate CPOM; PC required.",
                  ["Professional Corporation", "MSO / Friendly PC"], True, True, "Enforced",
                  "S.C. Code § 33-19 et seq.", "SC Board of Medical Examiners",
                  0, [], "moderate", 42, "Workable.", 2022, "https://llr.sc.gov/med/"),
        CPOMState("LA", "Louisiana", _TIER_MODERATE, "LA moderate CPOM; PC required.",
                  ["Professional Medical Corporation", "MSO / Friendly PC"], True, True, "Enforced",
                  "La. Rev. Stat. § 12:901 et seq.", "LA State Board of Medical Examiners",
                  0, [], "moderate", 42, "Workable.", 2022, "https://www.lsbme.la.gov/"),
        CPOMState("KS", "Kansas", _TIER_MODERATE, "KS moderate CPOM; PC required.",
                  ["Professional Corporation", "MSO / Friendly PC"], True, True, "Enforced",
                  "K.S.A. § 17-2706 et seq.", "KS State Board of Healing Arts",
                  0, [], "moderate", 42, "Workable.", 2022, "https://ksbha.org/"),
        CPOMState("OK", "Oklahoma", _TIER_MODERATE, "OK moderate CPOM; PC required.",
                  ["Professional Corporation", "MSO / Friendly PC"], True, True, "Enforced",
                  "Okla. Stat. tit. 18 § 801 et seq.", "OK State Board of Medical Licensure",
                  0, [], "moderate", 42, "Workable.", 2022, "https://www.okmedicalboard.org/"),
        CPOMState("AR", "Arkansas", _TIER_MODERATE, "AR moderate CPOM; PC required.",
                  ["Professional Corporation", "MSO / Friendly PC"], True, True, "Enforced",
                  "Ark. Code Ann. § 4-29-101 et seq.", "AR State Medical Board",
                  0, [], "moderate", 42, "Workable.", 2022, "https://www.armedicalboard.org/"),
        CPOMState("MS", "Mississippi", _TIER_MODERATE, "MS moderate CPOM; PC required.",
                  ["Professional Corporation", "MSO / Friendly PC"], True, True, "Enforced",
                  "Miss. Code § 79-10-1 et seq.", "MS State Board of Medical Licensure",
                  0, [], "low", 42, "Workable.", 2022, "https://www.msbml.ms.gov/"),
        CPOMState("IA", "Iowa", _TIER_MODERATE, "IA moderate CPOM; PC required.",
                  ["Professional Corporation", "MSO / Friendly PC"], True, True, "Enforced",
                  "Iowa Code § 496C", "Iowa Board of Medicine",
                  0, [], "low", 42, "Workable.", 2022, "https://medicalboard.iowa.gov/"),
        CPOMState("NE", "Nebraska", _TIER_MODERATE, "NE moderate CPOM; PC required.",
                  ["Professional Corporation", "MSO / Friendly PC"], True, True, "Enforced",
                  "Neb. Rev. Stat. § 21-2201 et seq.", "NE Board of Medicine and Surgery",
                  0, [], "low", 42, "Workable.", 2022, "https://dhhs.ne.gov/pages/Medicine-and-Surgery.aspx"),
        CPOMState("UT", "Utah", _TIER_FRIENDLY, "UT friendly CPOM; direct corporate employment permitted.",
                  ["Professional Corporation", "LLC", "For-profit corporation"], True, True, "Enforced",
                  "Utah Code § 16-11-1 et seq.", "UT Physicians Licensing Board",
                  0, [], "moderate", 35, "UT friendly.", 2022, "https://dopl.utah.gov/phys/"),
        CPOMState("ID", "Idaho", _TIER_FRIENDLY, "ID no strict CPOM.",
                  ["Professional Corporation", "LLC", "For-profit corporation"], True, True, "Enforced",
                  "Idaho Code § 30-1301 et seq.", "ID Board of Medicine",
                  0, [], "low", 35, "Friendly.", 2022, "https://bom.idaho.gov/"),
        CPOMState("WY", "Wyoming", _TIER_FRIENDLY, "WY no strict CPOM.",
                  ["Professional Corporation", "LLC", "For-profit corporation"], True, True, "Enforced",
                  "Wyo. Stat. § 17-3-101 et seq.", "WY Board of Medicine",
                  0, [], "low", 35, "Friendly.", 2022, "https://wyomedboard.wyo.gov/"),
        CPOMState("MT", "Montana", _TIER_FRIENDLY, "MT no strict CPOM.",
                  ["Professional Corporation", "LLC", "For-profit corporation"], True, True, "Enforced",
                  "Mont. Code § 35-4-101 et seq.", "MT Board of Medical Examiners",
                  0, [], "low", 35, "Friendly.", 2022, "https://boards.bsd.dli.mt.gov/med/"),
        CPOMState("ND", "North Dakota", _TIER_FRIENDLY, "ND no strict CPOM.",
                  ["Professional Corporation", "LLC", "For-profit corporation"], True, True, "Enforced",
                  "N.D. Cent. Code § 10-31 et seq.", "ND Board of Medicine",
                  0, [], "low", 35, "Friendly.", 2022, "https://www.ndbom.org/"),
        CPOMState("SD", "South Dakota", _TIER_FRIENDLY, "SD no strict CPOM.",
                  ["Professional Corporation", "LLC", "For-profit corporation"], True, True, "Enforced",
                  "S.D. Codified Laws § 47-11 et seq.", "SD State Board of Medical and Osteopathic Examiners",
                  0, [], "low", 35, "Friendly.", 2022, "https://medicine.sd.gov/"),
        CPOMState("NM", "New Mexico", _TIER_MODERATE, "NM moderate CPOM; emerging transaction-review regime.",
                  ["Professional Corporation", "MSO / Friendly PC"], True, True, "Enforced",
                  "N.M. Stat. § 53-6-1 et seq.", "NM Medical Board",
                  1, ["NM emerging transaction review regime"], "moderate", 48,
                  "NM emerging transaction review.", 2023, "https://nmmb.state.nm.us/"),
        CPOMState("AK", "Alaska", _TIER_FRIENDLY, "AK no strict CPOM.",
                  ["Professional Corporation", "LLC", "For-profit corporation"], True, True, "Enforced",
                  "Alaska Stat. § 10.45", "AK State Medical Board",
                  0, [], "low", 35, "Friendly.", 2022, "https://www.commerce.alaska.gov/web/cbpl/ProfessionalLicensing.aspx"),
        CPOMState("HI", "Hawaii", _TIER_MODERATE, "HI moderate CPOM; PC required.",
                  ["Professional Corporation", "MSO / Friendly PC"], True, True, "Enforced",
                  "Haw. Rev. Stat. § 415A et seq.", "HI Board of Medical Examiners",
                  0, [], "low", 45, "Workable.", 2022, "https://cca.hawaii.gov/pvl/boards/medical/"),
        CPOMState("ME", "Maine", _TIER_MODERATE, "ME moderate CPOM; PC required.",
                  ["Professional Corporation", "MSO / Friendly PC"], True, True, "Enforced",
                  "Me. Rev. Stat. tit. 13 § 723 et seq.", "ME Board of Licensure in Medicine",
                  0, [], "low", 42, "Workable.", 2022, "https://www.maine.gov/md/home"),
        CPOMState("NH", "New Hampshire", _TIER_MODERATE, "NH moderate CPOM; PC required.",
                  ["Professional Corporation", "MSO / Friendly PC"], True, True, "Enforced",
                  "N.H. Rev. Stat. § 294-A", "NH Board of Medicine",
                  0, [], "low", 42, "Workable.", 2022, "https://www.oplc.nh.gov/board-medicine"),
        CPOMState("VT", "Vermont", _TIER_MODERATE, "VT moderate CPOM; PC required; APCD state.",
                  ["Professional Corporation", "MSO / Friendly PC"], True, True, "Enforced",
                  "Vt. Stat. tit. 11 § 815 et seq.", "VT Board of Medical Practice",
                  0, [], "low", 42, "Workable; VT APCD state.", 2022, "https://medicalboard.vermont.gov/"),
        CPOMState("RI", "Rhode Island", _TIER_MODERATE, "RI moderate CPOM; PC required.",
                  ["Professional Corporation", "MSO / Friendly PC"], True, True, "Enforced",
                  "R.I. Gen. Laws § 7-5.1", "RI Board of Medical Licensure and Discipline",
                  1, ["Prospect Medical (RI AG 2020 settlement)"], "moderate", 48,
                  "RI — Prospect Medical historical precedent.", 2023, "https://health.ri.gov/"),
        CPOMState("DE", "Delaware", _TIER_MODERATE, "DE moderate CPOM; PC required but DE is favored holding-company state.",
                  ["Professional Corporation", "MSO / Friendly PC"], True, True, "Enforced",
                  "Del. Code tit. 8 § 601 et seq.", "DE Board of Medical Licensure and Discipline",
                  0, [], "high", 42,
                  "DE — most healthcare holdcos incorporate here for DGCL; local physician-group practice falls under DE CPOM.",
                  2022, "https://dpr.delaware.gov/boards/medicalpractice/"),
        CPOMState("WV", "West Virginia", _TIER_MODERATE, "WV moderate CPOM; PC required.",
                  ["Professional Corporation", "MSO / Friendly PC"], True, True, "Enforced",
                  "W.Va. Code § 30-12", "WV Board of Medicine",
                  0, [], "low", 42, "Workable.", 2022, "https://wvbom.wv.gov/"),
        CPOMState("DC", "District of Columbia", _TIER_MODERATE, "DC moderate CPOM; PC required.",
                  ["Professional Corporation", "MSO / Friendly PC"], True, True, "Enforced",
                  "D.C. Code § 29-511", "DC Board of Medicine",
                  0, [], "moderate", 45, "Workable.", 2022, "https://dchealth.dc.gov/service/board-medicine"),
    ]


# ---------------------------------------------------------------------------
# Cross-state enforcement actions (key precedents)
# ---------------------------------------------------------------------------

def _build_enforcement_actions() -> List[CPOMEnforcementAction]:
    return [
        CPOMEnforcementAction(2023, "CA", "AG investigation",
            "Optum / DaVita Medical Group", "CA AG reviewed structural arrangements of PE-affiliated physician groups; outcome pending.",
            "CA Attorney General's Office press release 2023"),
        CPOMEnforcementAction(2024, "CA", "Statute change",
            "OHCA Office of Health Care Affordability",
            "OHCA material-change notice requirement for transactions >$25M, effective 2024; expanded 2025+.",
            "California Health and Safety Code § 127500 et seq."),
        CPOMEnforcementAction(2023, "OR", "Statute change",
            "HB 4130 Health Care Market Oversight",
            "OR HCMO pre-approval required for healthcare transactions >$10M effective 2024.",
            "OR HB 4130 (2023)"),
        CPOMEnforcementAction(2024, "WA", "Statute change",
            "HB 2548 Healthcare Consolidation Review",
            "WA HB 2548 added healthcare-transaction disclosure regime effective 2025.",
            "WA HB 2548 (2024)"),
        CPOMEnforcementAction(2023, "NY", "AG investigation",
            "Optum-owned physician practices",
            "NY AG announced investigation of PE structures in NY physician-group deals.",
            "NY Attorney General press release 2023"),
        CPOMEnforcementAction(2018, "MA", "Statute change",
            "Non-Compete Act",
            "MA 2018 Non-Compete Act required consideration + 50% garden-leave pay; physician-specific limits apply.",
            "M.G.L. c. 149, § 24L"),
        CPOMEnforcementAction(2022, "IL", "Statute change",
            "Freedom to Work Act",
            "IL 2022 Freedom to Work Act prohibits non-competes for workers earning <$75K and imposes strict reasonable-scope limits for physicians.",
            "820 ILCS 90"),
        CPOMEnforcementAction(2023, "FTC", "Federal rule",
            "FTC Non-Compete Rule (status pending)",
            "FTC final rule banning most non-competes (2024); status pending in federal court.",
            "FTC 16 CFR Part 910"),
        CPOMEnforcementAction(2022, "MA", "AG action",
            "Steward Health Care",
            "MA AG investigation of Steward Health Care operations and structural compliance preceding 2024 bankruptcy.",
            "MA AG press release 2022-2024"),
        CPOMEnforcementAction(2020, "RI", "AG settlement",
            "Prospect Medical — Rhode Island hospitals",
            "RI AG settlement with Prospect Medical on billing + patient-access compliance.",
            "RI Attorney General 2020 settlement"),
        CPOMEnforcementAction(2023, "FL", "Patient brokering",
            "FL DOH prosecution — SUD / behavioral",
            "FL patient-brokering act enforcement on SUD + behavioral-health arrangements.",
            "Fla. Stat. § 817.505"),
        CPOMEnforcementAction(2023, "USDC SDTX", "Federal court",
            "FTC v. Welsh Carson / USAP",
            "FTC antitrust proceeding against PE sponsor + physician-group rollup; first PE-specific healthcare antitrust action.",
            "Case No. 4:23-cv-03560 (SDTX)"),
    ]


# ---------------------------------------------------------------------------
# Per-deal state inference + overlay
# ---------------------------------------------------------------------------

_STATE_KEYWORDS: Dict[str, List[str]] = {
    "CA": ["california", " ca ", "los angeles", "san francisco", "san diego", "sacramento", "oakland"],
    "NY": ["new york", " ny ", "nyc", "manhattan", "brooklyn", "queens", "rochester", "buffalo"],
    "TX": ["texas", " tx ", "houston", "dallas", "austin", "san antonio", "fort worth"],
    "FL": ["florida", " fl ", "miami", "tampa", "orlando", "jacksonville"],
    "IL": ["illinois", " il ", "chicago"],
    "MA": ["massachusetts", " ma ", "boston", "cambridge", "steward"],
    "PA": ["pennsylvania", " pa ", "philadelphia", "pittsburgh"],
    "OH": ["ohio", " oh ", "cleveland", "cincinnati", "columbus"],
    "GA": ["georgia", " ga ", "atlanta"],
    "NC": ["north carolina", " nc ", "charlotte", "raleigh"],
    "NJ": ["new jersey", " nj ", "newark"],
    "VA": ["virginia", " va ", "richmond", "arlington"],
    "MI": ["michigan", " mi ", "detroit"],
    "WA": ["washington state", " wa ", "seattle"],
    "CO": ["colorado", " co ", "denver"],
    "AZ": ["arizona", " az ", "phoenix"],
    "TN": ["tennessee", " tn ", "nashville", "memphis"],
    "MO": ["missouri", " mo ", "st. louis", "kansas city"],
    "MN": ["minnesota", " mn ", "minneapolis"],
    "IN": ["indiana", " in ", "indianapolis"],
    "RI": ["rhode island", "providence"],
    "OR": ["oregon", "portland oregon"],
}


def _infer_state(deal: dict) -> Optional[str]:
    hay = (str(deal.get("deal_name", "")) + " " +
           str(deal.get("notes", "")) + " " +
           str(deal.get("buyer", ""))).lower()
    for state_code, kws in _STATE_KEYWORDS.items():
        for kw in kws:
            if kw in hay:
                return state_code
    return None


def _is_physician_group_deal(deal: dict) -> bool:
    hay = (str(deal.get("deal_name", "")) + " " +
           str(deal.get("notes", ""))).lower()
    return any(kw in hay for kw in [
        "physician", "medical group", "mso ", "primary care",
        "dermatology", "cardiology", "gastroenter", "urology", "orthoped",
        "ophthalm", "pain management", "ent ", "anesthesia", "radiology",
    ])


def _overlay_corpus(deals: List[dict], states: List[CPOMState]) -> List[CorpusStateOverlay]:
    states_by_code = {s.state_code: s for s in states}
    overlays: List[CorpusStateOverlay] = []
    for d in deals:
        if not _is_physician_group_deal(d):
            continue
        inferred = _infer_state(d) or "—"
        state = states_by_code.get(inferred)
        if state is None:
            continue
        concerns: List[str] = []
        if state.regime_tier == _TIER_STRICT:
            concerns.append(f"{state.state_name} strict CPOM — Friendly PC / MSO required")
        if not state.mso_friendly:
            concerns.append("MSO arrangement disfavored in state")
        if state.recent_enforcement_count >= 2:
            concerns.append(f"{state.recent_enforcement_count} enforcement actions in last 5yrs")
        if state.structural_risk_score >= 70:
            concerns.append("Top-quartile structural-risk score")

        if state.structural_risk_score >= 75:
            tier = "CRITICAL"
        elif state.structural_risk_score >= 60:
            tier = "HIGH"
        elif state.structural_risk_score >= 45:
            tier = "MEDIUM"
        else:
            tier = "LOW"

        overlays.append(CorpusStateOverlay(
            deal_name=str(d.get("deal_name", "—"))[:80],
            deal_year=int(d.get("year") or 0),
            inferred_state=state.state_code,
            state_regime_tier=state.regime_tier,
            mso_friendly=state.mso_friendly,
            structural_risk_score=state.structural_risk_score,
            enforcement_concerns=concerns,
            risk_tier=tier,
        ))
    tier_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    overlays.sort(key=lambda o: (tier_order.get(o.risk_tier, 9), -o.structural_risk_score))
    return overlays


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def compute_cpom_state_lattice() -> CPOMStateLatticeResult:
    corpus = _load_corpus()
    states = _build_states()
    enforcement = _build_enforcement_actions()
    overlays = _overlay_corpus(corpus, states)
    material = [o for o in overlays if o.risk_tier in ("CRITICAL", "HIGH", "MEDIUM")]
    critical = sum(1 for o in overlays if o.risk_tier == "CRITICAL")

    strict = sum(1 for s in states if s.regime_tier == _TIER_STRICT)
    moderate = sum(1 for s in states if s.regime_tier == _TIER_MODERATE)
    friendly = sum(1 for s in states if s.regime_tier == _TIER_FRIENDLY)
    none_ = sum(1 for s in states if s.regime_tier == _TIER_NONE)
    mso_friendly = sum(1 for s in states if s.mso_friendly)
    fee_split = sum(1 for s in states if s.fee_splitting_allowed)
    avg_score = sum(s.structural_risk_score for s in states) / len(states) if states else 0

    return CPOMStateLatticeResult(
        knowledge_base_version=_KB_VERSION,
        effective_date=_KB_EFFECTIVE_DATE,
        source_citations=_SOURCE_CITATIONS,
        states=states,
        enforcement_actions=enforcement,
        corpus_overlays=overlays[:80],
        total_states=len(states),
        strict_tier_count=strict,
        moderate_tier_count=moderate,
        friendly_tier_count=friendly,
        none_tier_count=none_,
        mso_friendly_count=mso_friendly,
        fee_split_allowed_count=fee_split,
        avg_risk_score=round(avg_score, 1),
        corpus_deals_with_state_match=len(material),
        critical_exposure_count=critical,
        corpus_deal_count=len(corpus),
    )
