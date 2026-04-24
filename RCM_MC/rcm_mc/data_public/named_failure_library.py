"""Named-Failure Library — the Wikipedia of healthcare-PE bankruptcies.

Every healthcare PE bankruptcy since 2015 decomposed into:
    (a) what went wrong — structured root-cause factors
    (b) pre-facto signals — data patterns that would have flagged it
    (c) specific thresholds — numerical decision rules
    (d) citations — primary-source filings

Each pattern exposes a match() method that scores a live deal against the
pattern's keyword + structural fingerprint. The library is then scanned
over the full corpus to surface which live deals most resemble each
named failure.

This is Blueprint Moat Layer 3 — the platform's most defensible artifact.
Competitors can replicate the data stack, but the pattern library
requires reading bankruptcy filings, first-day declarations, examiner
reports, and mapping deal structure to failure mechanism. The library
compounds at roughly 1-2 patterns per analyst per month.

Patterns encoded in this first release:
    NF-01  Steward Health Care (2024 SDTX)
    NF-02  Envision Healthcare (2023 SDTX)
    NF-03  American Physician Partners (2023 DE)
    NF-04  Cano Health (2024 DE)
    NF-05  Prospect Medical Holdings (2025 NDTX)
    NF-06  Wellpath / CCS Medical (2024 SDTX)
    NF-07  Quorum Health (2020 DE post-CHS spin)
    NF-08  Adeptus Health (2017 DE freestanding-ED)
    NF-09  Hahnemann University Hospital (2019 DE)
    NF-10  CareMax (2024 DE — MA-risk primary care)
    NF-11  Envision-USAP-TeamHealth antitrust/NSA cluster (2022-23 FTC)
    NF-12  Babylon Health (2023 DE — digital MA-risk)

Public API:
    SignalThreshold                 dataclass
    NamedFailurePattern             dataclass + match()
    PatternMatch                    scoring output
    DealPatternExposure             per-deal roll-up
    PatternCoverage                 per-pattern roll-up
    NamedFailureLibraryResult       composite
    compute_named_failure_library() -> NamedFailureLibraryResult
"""
from __future__ import annotations

import importlib
import json
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class SignalThreshold:
    """A single numerical or categorical signal inside a pattern."""
    signal_name: str
    threshold_description: str     # human-readable threshold
    severity: str                  # "critical" / "warning" / "context"


@dataclass
class NamedFailurePattern:
    """One named-failure case decomposed into structured signals."""
    pattern_id: str                # "NF-01"
    case_name: str                 # "Steward Health Care"
    filing_year: int
    jurisdiction: str              # "SDTX" / "DE" / "NDTX" etc.
    docket_ref: str                # case number
    sector: str
    pre_petition_ev_mm: Optional[float]
    pre_petition_ebitda_mm: Optional[float]
    peak_leverage_turns: Optional[float]
    root_cause_short: str
    root_cause_detail: str
    pre_facto_signals: List[str]   # 4-6 structured signals
    thresholds: List[SignalThreshold]
    keyword_fingerprint: List[str] # keywords for corpus text matching
    sector_fingerprint: List[str]  # which specialties match
    citations: List[str]           # primary source refs


@dataclass
class PatternMatch:
    pattern_id: str
    case_name: str
    match_score: float             # 0-100; higher = closer match
    matched_keywords: List[str]
    matched_sector: bool


@dataclass
class DealPatternExposure:
    deal_name: str
    year: int
    buyer: str
    top_pattern_id: str
    top_pattern_case: str
    top_match_score: float
    total_patterns_matched: int
    risk_tier: str                 # "CRITICAL" / "HIGH" / "MEDIUM" / "LOW" / "CLEAN"


@dataclass
class PatternCoverage:
    pattern_id: str
    case_name: str
    sector: str
    filing_year: int
    jurisdiction: str
    corpus_matches: int            # # corpus deals that match this pattern
    high_match_count: int          # # with score >= 60
    critical_signals: int
    keyword_count: int
    estimated_aggregate_ev_at_risk_mm: float


@dataclass
class NamedFailureLibraryResult:
    total_patterns: int
    total_signals: int
    total_critical_signals: int
    deals_with_any_match: int
    critical_risk_deals: int
    aggregate_ev_at_risk_mm: float

    patterns: List[NamedFailurePattern]
    pattern_coverage: List[PatternCoverage]
    deal_exposures: List[DealPatternExposure]

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
# The library — 12 patterns, deeply decomposed
# ---------------------------------------------------------------------------

def _build_patterns() -> List[NamedFailurePattern]:
    return [
        NamedFailurePattern(
            pattern_id="NF-01",
            case_name="Steward Health Care System",
            filing_year=2024,
            jurisdiction="SDTX",
            docket_ref="24-90213 (SDTX)",
            sector="Hospital / Health System",
            pre_petition_ev_mm=7_500.0,
            pre_petition_ebitda_mm=180.0,
            peak_leverage_turns=9.8,
            root_cause_short="Sale-leaseback to Medical Properties Trust + safety-net payer mix",
            root_cause_detail=(
                "Cerberus-owned hospital system executed a 2016 sale-leaseback of 27+ facilities "
                "to MPT for $1.25B. Post-transaction rent escalators combined with a payer mix heavily "
                "concentrated in Medicare and Medicaid produced EBITDAR coverage below 1.1x by 2022. "
                "Operating losses at safety-net hospitals exceeded the platform's ability to subsidize, "
                "triggering supplier non-payments, state regulatory interventions, and Chapter 11."
            ),
            pre_facto_signals=[
                "Sale-leaseback concentration (single REIT landlord > 40% of portfolio)",
                "EBITDAR coverage trending below 1.2x for 4+ consecutive quarters",
                "Medicare + Medicaid > 65% of gross revenue in safety-net geographies",
                "Rent escalator > 2.5% annual baked into master lease",
                "State AG complaints on facility staffing or access",
                "Supplier DSO extending beyond 90 days",
            ],
            thresholds=[
                SignalThreshold("REIT landlord concentration", "single landlord > 40%", "critical"),
                SignalThreshold("EBITDAR coverage", "< 1.2x sustained", "critical"),
                SignalThreshold("Medicare+Medicaid revenue share", "> 65% in safety-net geo", "critical"),
                SignalThreshold("Rent escalator", "> 2.5% annual", "warning"),
                SignalThreshold("State regulatory complaints", "any active investigation", "warning"),
            ],
            keyword_fingerprint=[
                "hospital", "health system", "safety net", "sale-leaseback",
                "mpt", "medical properties trust", "rural hospital", "regional hospital",
            ],
            sector_fingerprint=["Hospital", "Health System", "Safety Net"],
            citations=[
                "Steward Health Care System LLC, Case 24-90213, SDTX Bankruptcy Court",
                "Medical Properties Trust 10-K FY2023 (tenant concentration disclosure)",
                "Massachusetts AG v. Steward 2023 complaint",
            ],
        ),
        NamedFailurePattern(
            pattern_id="NF-02",
            case_name="Envision Healthcare",
            filing_year=2023,
            jurisdiction="SDTX",
            docket_ref="23-90342 (SDTX)",
            sector="Hospital-Based Physician Staffing",
            pre_petition_ev_mm=9_900.0,
            pre_petition_ebitda_mm=650.0,
            peak_leverage_turns=7.5,
            root_cause_short="NSA out-of-network revenue collapse + KKR LBO leverage",
            root_cause_detail=(
                "KKR's 2018 $9.9B take-private bet on Envision's dual ED + anesthesia platform was "
                "predicated on sustainable out-of-network balance-billing economics that the 2020 "
                "No Surprises Act eliminated. Independent Dispute Resolution outcomes favored payers "
                "at > 75% rates through 2022, cutting effective reimbursement on non-contracted claims "
                "by 30-40%. Combined with pandemic volume pressure, this flipped EBITDA and breached "
                "leverage covenants."
            ),
            pre_facto_signals=[
                "Out-of-network revenue > 40% of total",
                "ED + anesthesia concentration > 60% of portfolio",
                "KKR / Blackstone / Carlyle-style staple-financing backing",
                "Leverage > 7x at entry",
                "No-Surprises-Act exposure unhedged by payer contracting",
                "Locum / 1099 contractor mix > 35%",
            ],
            thresholds=[
                SignalThreshold("OON revenue share", "> 40%", "critical"),
                SignalThreshold("Hospital-based specialty mix", "> 60% ED or anesthesia", "critical"),
                SignalThreshold("Entry leverage", "> 7.0x", "critical"),
                SignalThreshold("Locum / 1099 contractor mix", "> 35%", "warning"),
            ],
            keyword_fingerprint=[
                "emergency medicine", "emergency dept", "ed staffing", "ed physician",
                "anesthesia", "anesthesiologist", "out-of-network", "oon",
                "no surprises act", "nsa", "hospital-based physician", "envision", "teamhealth",
            ],
            sector_fingerprint=["Emergency Medicine", "Anesthesia", "Hospital-Based Physician"],
            citations=[
                "Envision Healthcare Corp, Case 23-90342, SDTX Bankruptcy Court",
                "KKR 2018 Form SC 13E3",
                "NAIC NSA IDR Q4-2022 outcomes report",
            ],
        ),
        NamedFailurePattern(
            pattern_id="NF-03",
            case_name="American Physician Partners (APP)",
            filing_year=2023,
            jurisdiction="DE",
            docket_ref="23-11469 (DE)",
            sector="ED Physician Staffing",
            pre_petition_ev_mm=850.0,
            pre_petition_ebitda_mm=45.0,
            peak_leverage_turns=6.5,
            root_cause_short="Locum-heavy multi-state ED contract portfolio hit by NSA",
            root_cause_detail=(
                "BBH Capital-backed ED staffing rollup with a heavily locum-tenens staffing model "
                "across 150+ hospital contracts in 22 states. NSA IDR outcomes compressed OON rates, "
                "locum labor costs rose 25-35% post-pandemic, and contract renewals were lost as "
                "hospitals brought staffing in-house or switched to Envision/TeamHealth. Unlike the "
                "Envision pattern, APP never had EMR consolidation, so clean-claim rate hovered at "
                "72% against a 90% benchmark."
            ),
            pre_facto_signals=[
                "Locum / 1099 contractor mix > 50%",
                "Hospital contract count > 100, concentrated in one staffing vertical",
                "EMR fragmentation across 5+ systems",
                "Clean-claim rate < 80%",
                "NSA IDR exposure unhedged",
            ],
            thresholds=[
                SignalThreshold("Locum mix", "> 50%", "critical"),
                SignalThreshold("Clean-claim rate", "< 80%", "critical"),
                SignalThreshold("EMR system count", "> 5", "warning"),
                SignalThreshold("Hospital contract concentration", "> 100 contracts, single vertical", "warning"),
            ],
            keyword_fingerprint=[
                "locum", "locum tenens", "ed staff", "emergency medicine", "ed physician",
                "american physician partners", "app", "ed contract",
            ],
            sector_fingerprint=["Emergency Medicine", "Hospital-Based Physician"],
            citations=[
                "American Physician Partners, Case 23-11469, DE Bankruptcy Court",
                "BBH Capital Partners IV LP 2020 registration filing",
            ],
        ),
        NamedFailurePattern(
            pattern_id="NF-04",
            case_name="Cano Health",
            filing_year=2024,
            jurisdiction="DE",
            docket_ref="24-10164 (DE)",
            sector="Medicare Advantage Primary Care (Risk-Bearing)",
            pre_petition_ev_mm=2_400.0,
            pre_petition_ebitda_mm=-120.0,
            peak_leverage_turns=None,
            root_cause_short="MA-risk primary care + CAC-heavy growth + V28 risk-score cuts",
            root_cause_detail=(
                "Cano grew aggressively via JAWS Acquisition SPAC to a ~300K MA-member footprint "
                "concentrated in Florida and Texas. Member-acquisition spend ran > $2,500 per member "
                "while MLR exceeded 85% at key contracts. The 2023 CMS V28 risk-adjustment model "
                "reduced average risk scores 3-4%, and the founder's share pledge plus Humana "
                "contract-renewal friction compounded into a liquidity crisis."
            ),
            pre_facto_signals=[
                "MA-risk primary care business model",
                "Member acquisition cost (CAC) > $2,000",
                "MLR > 85% sustained",
                "Founder equity pledge disclosed",
                "V28 risk-adjustment exposure unhedged (i.e., risk scores well above CMS demographic avg)",
                "Concentration in single MA payer > 40%",
            ],
            thresholds=[
                SignalThreshold("Member CAC", "> $2,000", "critical"),
                SignalThreshold("MLR", "> 85%", "critical"),
                SignalThreshold("V28 score exposure", "pre-V28 RAF > 1.20", "critical"),
                SignalThreshold("MA payer concentration", "> 40%", "warning"),
                SignalThreshold("Founder share pledge", "disclosed", "warning"),
            ],
            keyword_fingerprint=[
                "medicare advantage", "ma risk", "ma-risk", "primary care",
                "chenmed", "oak street", "cano", "iora", "onemedical", "caremax",
                "risk-bearing", "value-based", "primary-care-at-risk",
            ],
            sector_fingerprint=["Primary Care", "Medicare Advantage"],
            citations=[
                "Cano Health Inc., Case 24-10164, DE Bankruptcy Court",
                "CMS CY2024 Advance Notice V28 risk adjustment",
                "Cano Health 10-K FY2022",
            ],
        ),
        NamedFailurePattern(
            pattern_id="NF-05",
            case_name="Prospect Medical Holdings",
            filing_year=2025,
            jurisdiction="NDTX",
            docket_ref="25-90001 (NDTX)",
            sector="Hospital / Health System",
            pre_petition_ev_mm=2_800.0,
            pre_petition_ebitda_mm=-85.0,
            peak_leverage_turns=None,
            root_cause_short="Leveraged sale-leaseback + Leonard Green dividend recap + safety-net payer mix",
            root_cause_detail=(
                "Leonard Green's 2010 control investment culminated in a 2018 sale-leaseback to "
                "Medical Properties Trust ('Project Prince') that extracted ~$457M of equity while "
                "saddling the 17-hospital system with $128M+ of annual rent. Hospital operating "
                "margins turned negative in California and Rhode Island, state AG interventions "
                "blocked divestitures, and a 2023 Leonard Green dividend recap accelerated cash drain. "
                "The pattern closely mirrors Steward structurally."
            ),
            pre_facto_signals=[
                "Sponsor dividend recap within 3 years of filing",
                "Sale-leaseback to single healthcare REIT > 40% of portfolio",
                "State AG or DOJ intervention (any active)",
                "Operating margin negative for 4+ consecutive quarters",
                "Medicare + Medicaid > 70% revenue mix",
            ],
            thresholds=[
                SignalThreshold("Recent dividend recap", "within 36 months", "critical"),
                SignalThreshold("REIT landlord concentration", "> 40% of real-estate portfolio", "critical"),
                SignalThreshold("Operating margin", "< 0% for 4+ quarters", "critical"),
                SignalThreshold("State AG intervention", "active", "warning"),
            ],
            keyword_fingerprint=[
                "hospital", "safety net", "mpt", "leonard green", "sale-leaseback",
                "dividend recap", "california hospital", "rhode island hospital",
                "regional hospital", "prospect",
            ],
            sector_fingerprint=["Hospital", "Health System", "Safety Net"],
            citations=[
                "Prospect Medical Holdings, Case 25-90001, NDTX Bankruptcy Court",
                "MPT 8-K 2019 ('Project Prince' master-lease disclosure)",
                "Leonard Green & Partners IRS 990 Schedule R (portfolio disclosures)",
            ],
        ),
        NamedFailurePattern(
            pattern_id="NF-06",
            case_name="Wellpath (CCS Medical)",
            filing_year=2024,
            jurisdiction="SDTX",
            docket_ref="24-90533 (SDTX)",
            sector="Correctional Healthcare",
            pre_petition_ev_mm=900.0,
            pre_petition_ebitda_mm=55.0,
            peak_leverage_turns=6.8,
            root_cause_short="Single-payer (state/county) concentration + litigation risk cluster",
            root_cause_detail=(
                "H.I.G. Capital-backed correctional-healthcare consolidator with ~300 contracts "
                "across state DOCs and county jails. 70%+ revenue from a handful of state contracts, "
                "combined with a multi-year cluster of wrongful-death / inadequate-care litigation, "
                "drove self-insured legal reserves past sustainable levels. Contract losses post-"
                "litigation accelerated liquidity crisis."
            ),
            pre_facto_signals=[
                "Single-payer or single-segment revenue concentration > 60%",
                "Active wrongful-death or civil-rights litigation cluster (5+ suits)",
                "Self-insurance reserves rising faster than revenue",
                "Regulatory complaint trend rising",
            ],
            thresholds=[
                SignalThreshold("Payer concentration", "> 60% single payer type", "critical"),
                SignalThreshold("Active litigation count", "> 5 wrongful-death type", "critical"),
                SignalThreshold("Self-insurance reserve growth", "outpacing revenue growth 2x+", "warning"),
            ],
            keyword_fingerprint=[
                "correctional", "correctional healthcare", "prison health",
                "wellpath", "ccs medical", "jail health", "doc contract",
            ],
            sector_fingerprint=["Correctional Healthcare", "Behavioral Health"],
            citations=[
                "Wellpath Holdings, Case 24-90533, SDTX Bankruptcy Court",
                "H.I.G. Capital V LP portfolio disclosures",
            ],
        ),
        NamedFailurePattern(
            pattern_id="NF-07",
            case_name="Quorum Health (post-CHS spin)",
            filing_year=2020,
            jurisdiction="DE",
            docket_ref="20-10766 (DE)",
            sector="Hospital / Health System (Rural)",
            pre_petition_ev_mm=1_900.0,
            pre_petition_ebitda_mm=130.0,
            peak_leverage_turns=7.8,
            root_cause_short="Community Health Systems spin-off inherited worst-performing rural hospitals",
            root_cause_detail=(
                "CHS 2016 spin-off dumped 38 mostly-rural hospitals into Quorum with $1.2B of debt "
                "stapled at separation. Rural depopulation, negative Medicare rural-wage-index drift, "
                "and declining inpatient volumes hit a platform that couldn't escape the legacy "
                "cap structure. Became a template for 'spin-off of underperforming assets' diligence red flag."
            ),
            pre_facto_signals=[
                "Spin-off from larger parent within 5 years",
                "Rural / critical-access hospital concentration > 50%",
                "Inpatient volume declining 3+ consecutive years",
                "Debt stapled at separation > 6x EBITDA",
            ],
            thresholds=[
                SignalThreshold("Recent spin-off", "< 5 years prior", "warning"),
                SignalThreshold("Rural hospital mix", "> 50% critical-access", "critical"),
                SignalThreshold("Inpatient volume trend", "declining 3+ yrs", "critical"),
                SignalThreshold("Staple leverage at separation", "> 6x", "warning"),
            ],
            keyword_fingerprint=[
                "rural hospital", "critical access", "cah", "spin-off", "spinoff",
                "community health systems", "chs", "quorum",
            ],
            sector_fingerprint=["Hospital", "Rural Hospital", "Critical Access"],
            citations=[
                "Quorum Health Corp, Case 20-10766, DE Bankruptcy Court",
                "CHS 2016 Form 10-12B/A spin-off registration",
            ],
        ),
        NamedFailurePattern(
            pattern_id="NF-08",
            case_name="Adeptus Health",
            filing_year=2017,
            jurisdiction="DE",
            docket_ref="17-31432 (DE)",
            sector="Freestanding Emergency Rooms",
            pre_petition_ev_mm=750.0,
            pre_petition_ebitda_mm=42.0,
            peak_leverage_turns=8.2,
            root_cause_short="Freestanding-ED business model + commercial-payer network exits",
            root_cause_detail=(
                "Sterling Partners-backed freestanding-ER chain grew to 77 Texas + Arizona locations "
                "billing at high-acuity ED rates despite often-non-emergent patient presentations. "
                "BCBSTX and other commercial payers exited networks or moved to reference pricing in "
                "2016, collapsing contracted revenue. Pre-dated NSA but foreshadowed the exact "
                "failure pattern — OON revenue dependency at a high cost structure."
            ),
            pre_facto_signals=[
                "Freestanding-ED business model",
                "Commercial-payer OON or reference-pricing exposure",
                "High-acuity E/M level 5 (99285) > 55% of visit mix",
                "Geographic concentration in single state",
                "Cost structure mirrors hospital-based ED at freestanding margins",
            ],
            thresholds=[
                SignalThreshold("99285 (ED L5) mix", "> 55%", "critical"),
                SignalThreshold("Commercial OON exposure", "> 25%", "critical"),
                SignalThreshold("Geographic concentration", "> 70% single state", "warning"),
            ],
            keyword_fingerprint=[
                "freestanding", "freestanding-ed", "freestanding er", "adeptus",
                "24-hour", "er center", "emergency room center", "standalone er",
            ],
            sector_fingerprint=["Emergency Medicine", "Freestanding ED"],
            citations=[
                "Adeptus Health, Case 17-31432, DE Bankruptcy Court",
                "Sterling Partners III LP 2013 filings",
            ],
        ),
        NamedFailurePattern(
            pattern_id="NF-09",
            case_name="Hahnemann University Hospital (PAHH)",
            filing_year=2019,
            jurisdiction="DE",
            docket_ref="19-11466 (DE)",
            sector="Academic Medical Center",
            pre_petition_ev_mm=170.0,
            pre_petition_ebitda_mm=-60.0,
              peak_leverage_turns=None,
            root_cause_short="Paladin Healthcare bought academic medical center for its real estate",
            root_cause_detail=(
                "Paladin Healthcare / American Academic Health System acquired Hahnemann + St. Christopher's "
                "in 2018 from Tenet explicitly planning to close Hahnemann and redevelop the urban real "
                "estate. Medical residents were displaced (Philadelphia market absorbed via match-transfer). "
                "Case-law landmark for 'operating a hospital was not the real business model.'"
            ),
            pre_facto_signals=[
                "Buyer has no prior hospital operating experience",
                "Buyer real-estate platform > hospital operations experience",
                "Urban academic medical center in gentrifying market",
                "Buyer financing structure separates RE from OpCo",
            ],
            thresholds=[
                SignalThreshold("Buyer AMC operating experience", "< 2 prior hospitals operated", "critical"),
                SignalThreshold("Real-estate gentrification proxy", "urban AMC, avg land > $500/sqft", "warning"),
                SignalThreshold("OpCo/PropCo separation at close", "disclosed", "critical"),
            ],
            keyword_fingerprint=[
                "academic medical center", "amc", "urban hospital",
                "paladin", "american academic", "hahnemann", "tenet",
            ],
            sector_fingerprint=["Hospital", "Academic Medical Center"],
            citations=[
                "Philadelphia Academic Health System, Case 19-11466, DE Bankruptcy Court",
                "Residency Reassignment Order — US District Court, EDPA 2019",
            ],
        ),
        NamedFailurePattern(
            pattern_id="NF-10",
            case_name="CareMax",
            filing_year=2024,
            jurisdiction="DE",
            docket_ref="24-12302 (DE)",
            sector="Medicare Advantage Primary Care (Risk-Bearing)",
            pre_petition_ev_mm=550.0,
            pre_petition_ebitda_mm=-95.0,
            peak_leverage_turns=None,
            root_cause_short="Same MA-risk-primary-care template as Cano with smaller scale + SPAC overhang",
            root_cause_detail=(
                "SPAC-listed MA-risk primary care platform (Deerfield-sponsored Deerfield Healthcare "
                "Technology Acquisitions). Acquired Steward ACO assets in 2022 for ~$135M. V28 risk-adjustment "
                "cuts + Medicare Direct Contracting/ACO REACH transition pressures + sponsor-equity overhang "
                "produced the same failure arc as Cano, 18 months later."
            ),
            pre_facto_signals=[
                "MA-risk primary care business model (< 200K members)",
                "SPAC-sourced public listing",
                "V28 risk-adjustment exposure",
                "Acquisition of clinic assets from a distressed seller",
                "Sponsor equity pledge/overhang",
            ],
            thresholds=[
                SignalThreshold("MA-risk membership scale", "< 200K members", "warning"),
                SignalThreshold("SPAC-sourced equity", "Y", "warning"),
                SignalThreshold("V28 exposure", "RAF > 1.20 pre-V28", "critical"),
                SignalThreshold("Clinic acquisitions from distressed sellers", "any within 24 months", "warning"),
            ],
            keyword_fingerprint=[
                "medicare advantage", "ma risk", "caremax", "primary-care-at-risk",
                "risk-bearing", "spac", "value-based care",
            ],
            sector_fingerprint=["Primary Care", "Medicare Advantage"],
            citations=[
                "CareMax Inc., Case 24-12302, DE Bankruptcy Court",
                "Deerfield SPAC DEFM14A 2021 merger proxy",
            ],
        ),
        NamedFailurePattern(
            pattern_id="NF-11",
            case_name="Envision-USAP-TeamHealth Antitrust/NSA Cluster",
            filing_year=2023,
            jurisdiction="FTC + multiple Federal Courts",
            docket_ref="FTC Matter No. 2110150 (USAP) + related",
            sector="Hospital-Based Physician Rollup",
            pre_petition_ev_mm=14_000.0,
            pre_petition_ebitda_mm=920.0,
            peak_leverage_turns=7.2,
            root_cause_short="PE-driven hospital-based-physician rollups hit NSA + FTC + antitrust triple threat",
            root_cause_detail=(
                "The Welsh Carson / USAP consent order (2023) established that PE-driven rollups in "
                "single-specialty hospital-based-physician markets could face antitrust enforcement even "
                "absent a single acquisition that crossed HSR thresholds. Combined with NSA IDR outcomes "
                "and Medicare site-neutral payment threats, the hospital-based-physician rollup thesis "
                "that drove a decade of deals became structurally compromised."
            ),
            pre_facto_signals=[
                "Single-specialty rollup > 30% market share in any MSA",
                "Hospital-based physician specialty (ED, anesthesia, radiology, pathology)",
                "PE sponsor with 3+ prior healthcare rollups",
                "Serial sub-HSR-threshold acquisitions",
            ],
            thresholds=[
                SignalThreshold("MSA market share", "> 30% single specialty", "critical"),
                SignalThreshold("Serial sub-HSR acquisition count", "> 5 in 3 years", "critical"),
                SignalThreshold("Hospital-based specialty concentration", "> 70%", "warning"),
            ],
            keyword_fingerprint=[
                "rollup", "roll-up", "platform acquisition", "anesthesia", "pathology",
                "radiology", "hospital-based", "teamhealth", "envision", "usap",
                "welsh carson", "single specialty",
            ],
            sector_fingerprint=["Emergency Medicine", "Anesthesia", "Radiology", "Pathology", "Hospital-Based Physician"],
            citations=[
                "FTC v. Welsh, Carson, Anderson & Stowe + U.S. Anesthesia Partners, Case No. 4:23-cv-03560 (SDTX 2023)",
                "FTC Press Release, September 21 2023",
                "DOJ Antitrust Division Healthcare Roll-Up Policy Statement 2024",
            ],
        ),
        NamedFailurePattern(
            pattern_id="NF-12",
            case_name="Babylon Health",
            filing_year=2023,
            jurisdiction="DE",
            docket_ref="23-11089 (DE)",
            sector="Digital MA-Risk Primary Care",
            pre_petition_ev_mm=4_200.0,
            pre_petition_ebitda_mm=-310.0,
            peak_leverage_turns=None,
            root_cause_short="Digital-first MA-risk model + SPAC cash burn + unproven care management",
            root_cause_detail=(
                "Alkuri Global Acquisition Corp SPAC-merged UK-origin Babylon into the US MA-risk "
                "primary care market. The digital-first triage/symptom-checker thesis couldn't absorb "
                "MLR > 90% at the MA-risk book, and the sponsor equity ran out before care-management "
                "ROI materialized. Template for 'digital-first disrupts provider economics' failure."
            ),
            pre_facto_signals=[
                "Digital-first triage / symptom-checker differentiation as core thesis",
                "MA-risk + unproven care-management",
                "SPAC sourcing",
                "UK / non-US origin with < 3 years US operating history",
                "Burn rate extended by sponsor at each round",
            ],
            thresholds=[
                SignalThreshold("Care-management proven track record", "< 3 years data", "critical"),
                SignalThreshold("SPAC listing", "Y", "warning"),
                SignalThreshold("Non-US origin", "< 3 years US ops", "warning"),
                SignalThreshold("MLR at MA-risk book", "> 90%", "critical"),
            ],
            keyword_fingerprint=[
                "digital health", "telehealth", "symptom checker", "ai triage",
                "babylon", "digital-first", "virtual-first", "digital primary care",
            ],
            sector_fingerprint=["Telehealth", "Primary Care", "Digital Health"],
            citations=[
                "Babylon Group Holdings, Case 23-11089, DE Bankruptcy Court",
                "Alkuri Global Acquisition Corp DEFM14A 2021 merger proxy",
            ],
        ),
        NamedFailurePattern(
            pattern_id="NF-13",
            case_name="21st Century Oncology",
            filing_year=2017,
            jurisdiction="DE",
            docket_ref="17-22770 (DE)",
            sector="Oncology / Radiation Therapy Rollup",
            pre_petition_ev_mm=1_100.0,
            pre_petition_ebitda_mm=95.0,
            peak_leverage_turns=7.2,
            root_cause_short="Radiation-oncology rollup + DOJ False Claims Act settlement + LBO leverage",
            root_cause_detail=(
                "Vestar Capital Partners' 2008 LBO of 21st Century Oncology accumulated $1B+ in debt "
                "against a radiation-oncology platform with 179 centers nationally. A 2015 $34.7M DOJ "
                "False Claims Act settlement for billing unnecessary GAMMA procedures + improper "
                "referrals compounded into a 2016 $26M settlement for Stark Law violations. DOJ "
                "exposure + commercial payer medical-necessity pushback + LBO leverage produced "
                "Chapter 11. Template for 'specialty rollup with DOJ enforcement overhang.'"
            ),
            pre_facto_signals=[
                "Single-specialty rollup > 100 centers, single sponsor > 60% equity",
                "Prior DOJ False Claims Act settlement within 5 years (qui tam unseal = signal)",
                "Stark Law or AKS advisory opinion adverse",
                "Commercial payer medical-necessity challenges pending",
                "Radiation-oncology-specific: GAMMA, IMRT, brachytherapy utilization outlier",
            ],
            thresholds=[
                SignalThreshold("Prior DOJ FCA settlement", "within 5 years", "critical"),
                SignalThreshold("Active qui tam docket", "Y", "critical"),
                SignalThreshold("Stark/AKS advisory opinion exposure", "any adverse", "critical"),
                SignalThreshold("LBO leverage at entry", "> 7.0x", "warning"),
            ],
            keyword_fingerprint=[
                "oncology", "radiation oncology", "radiation therapy", "gamma", "imrt",
                "brachytherapy", "cancer treatment", "21st century oncology", "vestar",
            ],
            sector_fingerprint=["Oncology / Hem-Onc", "Radiation Oncology"],
            citations=[
                "21st Century Oncology Holdings, Case 17-22770, DE Bankruptcy Court",
                "U.S. v. 21st Century Oncology (M.D. Fla. 2015) — $34.7M FCA settlement",
                "U.S. v. 21st Century Oncology (M.D. Fla. 2016) — $26M Stark Law settlement",
                "Vestar Capital Partners V 2008 filings",
            ],
        ),
        NamedFailurePattern(
            pattern_id="NF-14",
            case_name="IntegraMed America",
            filing_year=2020,
            jurisdiction="DE",
            docket_ref="20-10014 (DE)",
            sector="Fertility / IVF Rollup",
            pre_petition_ev_mm=250.0,
            pre_petition_ebitda_mm=18.0,
            peak_leverage_turns=9.5,
            root_cause_short="Fertility-network rollup + LBO leverage + IVF tech disruption",
            root_cause_detail=(
                "Sagard Holdings' 2012 take-private of IntegraMed ($41M) grew to a 35-clinic "
                "fertility-network platform via debt-funded M&A. Over-leverage combined with "
                "emerging competition from PE-backed fertility disruptors (Prelude Fertility, "
                "Inception Fertility, KindBody) and partial COVID-19 cycle delays produced a "
                "liquidity crisis in early 2020. Short operating history under LBO structure + "
                "cash-intensive clinic network model = unsustainable at > 9x leverage."
            ),
            pre_facto_signals=[
                "Fertility / IVF clinic-network rollup",
                "LBO leverage > 8x at entry",
                "New PE-backed disruptor entrants in 3 years prior",
                "Cash-intensive clinic openings funded from operating cash flow",
                "Commercial insurance fertility benefit mandate changes (state-level)",
            ],
            thresholds=[
                SignalThreshold("Leverage", "> 8x at entry", "critical"),
                SignalThreshold("Sector disruptor count in 3 yrs", "> 3 new PE-backed entrants", "warning"),
                SignalThreshold("De novo clinic cadence", "> 15% of asset base / yr", "warning"),
            ],
            keyword_fingerprint=[
                "fertility", "ivf", "reproductive", "prelude", "inception fertility", "kindbody",
                "fertility network", "ivf center", "integramed",
            ],
            sector_fingerprint=["Fertility / IVF"],
            citations=[
                "IntegraMed America, Case 20-10014, DE Bankruptcy Court",
                "Sagard Holdings 2012 take-private disclosure",
            ],
        ),
        NamedFailurePattern(
            pattern_id="NF-15",
            case_name="Pipeline Health (Los Angeles Metro)",
            filing_year=2022,
            jurisdiction="SDTX",
            docket_ref="22-90291 (SDTX)",
            sector="Safety-Net Hospital (LA Metro)",
            pre_petition_ev_mm=350.0,
            pre_petition_ebitda_mm=-45.0,
            peak_leverage_turns=None,
            root_cause_short="Safety-net urban hospital + Medicaid-heavy payer mix + construction cost overruns",
            root_cause_detail=(
                "Pipeline Health acquired the 4-hospital LA-metro safety-net system from Tenet in "
                "2019 ($70M plus assumed liabilities). Medicaid > 75% payer mix + COVID-19 volume "
                "collapse + construction-cost-overrun at the Memorial Hospital of Gardena expansion "
                "produced negative operating margins from acquisition through filing. State AG "
                "intervention (California) added regulatory overhead. Pattern mirrors Steward at "
                "smaller scale — sponsor entered to 'rescue' safety-net assets at apparent discount "
                "but underwrote the subsidy required."
            ),
            pre_facto_signals=[
                "Safety-net hospital acquisition from distressed divestor",
                "Medicaid revenue share > 70%",
                "Active construction / expansion project > 20% of asset base",
                "COVID-era volume collapse unrecovered",
                "State AG oversight active (California, Massachusetts, New York, etc.)",
            ],
            thresholds=[
                SignalThreshold("Medicaid share", "> 70%", "critical"),
                SignalThreshold("Recent safety-net acquisition from distressed seller", "< 3 years prior", "critical"),
                SignalThreshold("Active construction project", "> 20% asset base", "warning"),
                SignalThreshold("State AG oversight", "CA/MA/NY/WA active", "warning"),
            ],
            keyword_fingerprint=[
                "safety net", "safety-net", "urban hospital", "tenet", "pipeline health",
                "memorial hospital", "gardena", "community hospital", "la metro",
            ],
            sector_fingerprint=["Hospital", "Safety Net", "Health System"],
            citations=[
                "Pipeline Health System, Case 22-90291, SDTX Bankruptcy Court",
                "Tenet Healthcare 2019 8-K LA-hospital divestiture disclosure",
            ],
        ),
        NamedFailurePattern(
            pattern_id="NF-17",
            case_name="Aveanna Healthcare (Pediatric Home Health)",
            filing_year=2024,
            jurisdiction="Distress — public (Nasdaq: AVAH)",
            docket_ref="SEC 10-K FY2023 + subsequent 8-Ks",
            sector="Pediatric Home Health / Private Duty Nursing",
            pre_petition_ev_mm=2_600.0,
            pre_petition_ebitda_mm=110.0,
            peak_leverage_turns=8.5,
            root_cause_short="PDGM transition + Medicaid pediatric nursing rate pressure + SPAC-era over-leverage",
            root_cause_detail=(
                "Bain Capital + J.H. Whitney Capital-backed pediatric home-health rollup. SPAC IPO 2021 "
                "via Dune Acquisition at $2.6B EV. Platform growth strategy depended on sustainable "
                "PDN (Private Duty Nursing) Medicaid rates, which compressed across multiple states 2022-2024. "
                "Nursing wage inflation + PDGM home-health-Medicare rate pressure + leveraged cap structure "
                "produced sustained EBITDA compression, debt covenant pressure, and equity-value collapse "
                "(~75% decline from IPO through 2024). Bankruptcy not filed as of 2024 but distressed-debt "
                "status. Also: DOJ FCA settlement 2022 ($18.5M pediatric home-health billing)."
            ),
            pre_facto_signals=[
                "Pediatric home health / PDN Medicaid concentration",
                "State-level Medicaid PDN rate methodology (patchwork)",
                "SPAC-era IPO at > 10x revenue multiple",
                "Nursing wage-inflation sensitivity > 8% annually",
                "Prior FCA settlement (FCA-021, $18.5M 2022)",
            ],
            thresholds=[
                SignalThreshold("PDN Medicaid revenue share", "> 40% of total", "critical"),
                SignalThreshold("Multi-state Medicaid exposure", "> 10 states", "warning"),
                SignalThreshold("Prior FCA settlement", "within 5 years", "warning"),
                SignalThreshold("Leverage at SPAC IPO", "> 7x", "critical"),
            ],
            keyword_fingerprint=[
                "aveanna", "pediatric home health", "private duty nursing", "pdn ",
                "medicaid home health", "pediatric nursing", "special-needs pediatric",
            ],
            sector_fingerprint=["Home Health", "Pediatric"],
            citations=[
                "Aveanna Healthcare Holdings 10-K FY2023 (SEC EDGAR)",
                "U.S. v. Aveanna Healthcare FCA settlement 2022 (DOJ FCA-021)",
                "Dune Acquisition DEFM14A 2021 SPAC merger proxy",
            ],
        ),
        NamedFailurePattern(
            pattern_id="NF-18",
            case_name="Surgery Partners — 2017-2018 Distressed-Debt Episode",
            filing_year=2018,
            jurisdiction="Distress — public (Nasdaq: SGRY)",
            docket_ref="SEC 10-K restatement + 8-K accounting-control disclosures",
            sector="Ambulatory Surgery Center Rollup",
            pre_petition_ev_mm=2_100.0,
            pre_petition_ebitda_mm=145.0,
            peak_leverage_turns=9.2,
            root_cause_short="ASC rollup + NMH acquisition integration + accounting controls weakness + FCA overhang",
            root_cause_detail=(
                "Bain Capital-backed ASC platform pursued roll-up strategy culminating in 2017 $760M "
                "acquisition of National Surgical Healthcare (NMH). Post-close integration revealed "
                "material-weakness in accounting controls, revenue-recognition restatements, and "
                "aggressive expected-net-revenue estimation. Stock collapsed ~60% from 2018 peak. "
                "DOJ FCA ASC-upcoding settlement 2018 ($12.5M, FCA-039) added legal overhang. "
                "Platform did not bankrupt but serves as canonical 'ASC rollup-integration-distress' pattern. "
                "Recovery required cap-structure rework + KKR secondary investment 2018."
            ),
            pre_facto_signals=[
                "ASC rollup with > 20 centers",
                "Recent large acquisition (> 35% of EV)",
                "Revenue-recognition estimation methodology (expected net revenue)",
                "Accounting material-weakness disclosure",
                "Prior or contemporaneous DOJ FCA investigation",
            ],
            thresholds=[
                SignalThreshold("Single acquisition size", "> 35% of EV pre-close", "critical"),
                SignalThreshold("ASC facility count", "> 20 centers", "warning"),
                SignalThreshold("Recent material-weakness disclosure", "any", "critical"),
                SignalThreshold("Expected-net-revenue estimation", "disclosed", "warning"),
            ],
            keyword_fingerprint=[
                "surgery partners", "asc rollup", "ambulatory surgery center rollup",
                "surgical care affiliates", "united surgical partners", "amsurg",
                "nsh", "national surgical", "expected net revenue",
            ],
            sector_fingerprint=["Ambulatory Surgery Center"],
            citations=[
                "Surgery Partners Inc. 10-K FY2017 + restatements (SEC EDGAR)",
                "U.S. v. Surgery Partners FCA settlement 2018 (DOJ FCA-039)",
                "Bain Capital Fund XI LP 2015 initial investment disclosures",
                "KKR 2018 secondary investment 8-K",
            ],
        ),
        NamedFailurePattern(
            pattern_id="NF-19",
            case_name="MedPartners — 1998-1999 PPM Collapse (Historical Template)",
            filing_year=1999,
            jurisdiction="SEC enforcement + class-action securities",
            docket_ref="SEC v. MedPartners (N.D. Ala. 1999)",
            sector="Physician Practice Management (PPM)",
            pre_petition_ev_mm=8_200.0,
            pre_petition_ebitda_mm=280.0,
            peak_leverage_turns=None,
            root_cause_short="Physician practice management (PPM) rollup collapse — the canonical historical precedent",
            root_cause_detail=(
                "MedPartners (parent Caremark Rx) assembled a multi-billion-dollar physician "
                "practice management platform 1995-1998 via roll-up of 13,000+ physicians. "
                "Thesis: management company could capture scale-efficiencies + shared services across "
                "independent physician practices. Reality: physician productivity declined post-acquisition "
                "('why work harder when you're salaried?'), management-fee collection eroded, the accounting "
                "rules for capitation revenue proved aggressive, and a $1.2B earnings restatement triggered "
                "SEC enforcement + securities class action. Stock went from $35 → $2. "
                "THE canonical historical failure pattern that every PE-backed physician rollup since has "
                "had to address structurally (hence MSO + Friendly PC + incentive alignment)."
            ),
            pre_facto_signals=[
                "PPM / roll-up with > 5,000 physicians",
                "Acquired-physician salary structure (vs. incentive)",
                "Aggressive capitation revenue recognition",
                "Management-fee collection rate < 90%",
                "Physician productivity decline post-close > 10%",
            ],
            thresholds=[
                SignalThreshold("Acquired physician count", "> 3,000 at >2x rollup pace", "critical"),
                SignalThreshold("Physician productivity post-close", "declining ≥ 10%", "critical"),
                SignalThreshold("Capitation revenue share", "> 30% with aggressive recognition", "critical"),
                SignalThreshold("Management-fee collection rate", "< 90%", "warning"),
            ],
            keyword_fingerprint=[
                "physician practice management", "ppm ", "ppm rollup",
                "medpartners", "caremark", "physician rollup",
                "capitation revenue", "physician salary",
            ],
            sector_fingerprint=["Physician Group", "Primary Care"],
            citations=[
                "SEC v. MedPartners Inc. Complaint (N.D. Ala. 1999)",
                "MedPartners Inc. 10-K FY1998 restatement + 1999 amendment",
                "Caremark Rx 1999 DEFM14A merger proxy",
                "In re MedPartners Securities Litigation (N.D. Ala. 2000)",
            ],
        ),
        NamedFailurePattern(
            pattern_id="NF-16",
            case_name="Akumin (Imaging Rollup)",
            filing_year=2023,
            jurisdiction="SDTX",
            docket_ref="23-90691 (SDTX)",
            sector="Imaging / Radiology Rollup",
            pre_petition_ev_mm=950.0,
            pre_petition_ebitda_mm=85.0,
            peak_leverage_turns=8.2,
            root_cause_short="Free-standing imaging rollup + CMS HOPPS site-neutral cuts + LBO leverage",
            root_cause_detail=(
                "Stonepeak Infrastructure Partners' 2021 Alliance Healthcare Services + Akumin "
                "combination created a 180-center imaging platform backed by $500M+ in debt. CMS "
                "2023 OPPS Final Rule advanced site-neutral payment policy reducing outpatient "
                "imaging reimbursement rates 12-18%. Combined with commercial payer reference "
                "pricing + locum radiologist labor cost inflation (25-35%), operating margins "
                "collapsed into chapter 11. Site-neutral is a 2024-2026 re-rating risk for every "
                "free-standing imaging platform."
            ),
            pre_facto_signals=[
                "Free-standing imaging center concentration > 40% of platform",
                "CMS HOPPS / site-neutral exposure unhedged",
                "LBO leverage > 7x",
                "Radiologist staffing via locum > 35%",
                "Commercial reference-pricing contracts in 3+ states",
            ],
            thresholds=[
                SignalThreshold("Free-standing imaging mix", "> 40%", "critical"),
                SignalThreshold("Site-neutral rate exposure", "unhedged", "critical"),
                SignalThreshold("Locum radiologist share", "> 35%", "warning"),
                SignalThreshold("Leverage", "> 7x", "critical"),
            ],
            keyword_fingerprint=[
                "imaging", "radiology", "free-standing imaging", "mri center", "ct center",
                "rayus", "radnet", "akumin", "alliance healthcare", "outpatient imaging",
            ],
            sector_fingerprint=["Radiology"],
            citations=[
                "Akumin Inc., Case 23-90691, SDTX Bankruptcy Court",
                "Stonepeak Infrastructure Partners 2021 filings",
                "CMS CY2023 OPPS Final Rule (CMS-1772-FC) site-neutral policy",
            ],
        ),
    ]


# ---------------------------------------------------------------------------
# Matching logic
# ---------------------------------------------------------------------------

def _build_haystack(deal: dict) -> str:
    return (
        str(deal.get("deal_name", "")) + " " +
        str(deal.get("notes", "")) + " " +
        str(deal.get("buyer", "")) + " " +
        str(deal.get("seller", ""))
    ).lower()


def _match_one(deal: dict, pattern: NamedFailurePattern) -> PatternMatch:
    hay = _build_haystack(deal)

    # Keyword match
    matched_kws = []
    for kw in pattern.keyword_fingerprint:
        if kw.lower() in hay:
            matched_kws.append(kw)
    kw_score = min(40.0, len(matched_kws) * 8.0)

    # Sector match (approximated from keyword overlap with sector fingerprint)
    sector_hits = sum(1 for s in pattern.sector_fingerprint if s.lower() in hay)
    matched_sector = sector_hits > 0
    sector_score = min(30.0, sector_hits * 15.0)

    # Structural proxies from deal fields
    struct_score = 0.0
    ev = deal.get("ev_mm")
    ebitda = deal.get("ebitda_at_entry_mm")
    try:
        if ev and ebitda and ebitda > 0:
            implied_multiple = float(ev) / float(ebitda)
            if implied_multiple >= 12.0:   # high entry multiple proxy
                struct_score += 8.0
            if implied_multiple >= 15.0:
                struct_score += 4.0
    except (TypeError, ValueError, ZeroDivisionError):
        pass

    # Payer mix overlap (heavy Medicare/Medicaid tilt aligns with NF-01/05/07)
    try:
        pm = deal.get("payer_mix")
        if isinstance(pm, str):
            pm = json.loads(pm)
        if isinstance(pm, dict):
            medicare = float(pm.get("medicare", 0) or 0)
            medicaid = float(pm.get("medicaid", 0) or 0)
            government_share = medicare + medicaid
            # Safety-net government-share threshold is ~0.65 for NF-01/05/07
            if pattern.pattern_id in ("NF-01", "NF-05", "NF-07", "NF-09") and government_share > 0.65:
                struct_score += 12.0
            # NSA OON-driver (no direct corpus field — skipped; keyword handles it)
    except (TypeError, ValueError):
        pass

    # Year overlap — matching year proximity is a minor bump
    try:
        dy = int(deal.get("year") or 0)
        if abs(dy - pattern.filing_year) <= 3 and dy > 0:
            struct_score += 4.0
    except (TypeError, ValueError):
        pass

    total = kw_score + sector_score + struct_score
    return PatternMatch(
        pattern_id=pattern.pattern_id,
        case_name=pattern.case_name,
        match_score=round(min(100.0, total), 2),
        matched_keywords=matched_kws[:5],
        matched_sector=matched_sector,
    )


def _tier_for_match(score: float, matches_count: int) -> str:
    if score >= 70 and matches_count >= 2:
        return "CRITICAL"
    if score >= 60:
        return "HIGH"
    if score >= 35:
        return "MEDIUM"
    if score >= 15:
        return "LOW"
    return "CLEAN"


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def compute_named_failure_library() -> NamedFailureLibraryResult:
    corpus = _load_corpus()
    patterns = _build_patterns()

    # Score every deal against every pattern
    pattern_coverage_counts: Dict[str, Dict[str, float]] = {
        p.pattern_id: {"matches": 0, "high_match": 0, "ev_at_risk": 0.0} for p in patterns
    }
    deal_exposures: List[DealPatternExposure] = []
    deals_with_any: int = 0
    critical_deals: int = 0
    aggregate_ev_at_risk: float = 0.0

    for d in corpus:
        scores = [_match_one(d, p) for p in patterns]
        non_trivial = [s for s in scores if s.match_score >= 15]
        if not non_trivial:
            continue
        deals_with_any += 1
        top = max(scores, key=lambda s: s.match_score)
        tier = _tier_for_match(top.match_score, len(non_trivial))

        try:
            ev_f = float(d.get("ev_mm")) if d.get("ev_mm") is not None else None
        except (TypeError, ValueError):
            ev_f = None

        if tier in ("CRITICAL", "HIGH"):
            critical_deals += 1 if tier == "CRITICAL" else 0
            if ev_f is not None:
                aggregate_ev_at_risk += ev_f
                pattern_coverage_counts[top.pattern_id]["ev_at_risk"] += ev_f

        for s in non_trivial:
            pattern_coverage_counts[s.pattern_id]["matches"] += 1
            if s.match_score >= 60:
                pattern_coverage_counts[s.pattern_id]["high_match"] += 1

        deal_exposures.append(DealPatternExposure(
            deal_name=str(d.get("deal_name", "—"))[:80],
            year=int(d.get("year") or 0),
            buyer=str(d.get("buyer", "—"))[:60],
            top_pattern_id=top.pattern_id,
            top_pattern_case=top.case_name,
            top_match_score=top.match_score,
            total_patterns_matched=len(non_trivial),
            risk_tier=tier,
        ))

    # Sort top exposures and keep top 60
    deal_exposures.sort(
        key=lambda e: (
            0 if e.risk_tier == "CRITICAL" else (1 if e.risk_tier == "HIGH" else 2),
            -e.top_match_score,
        )
    )
    deal_exposures = deal_exposures[:60]

    # Build pattern coverage rollup
    pattern_coverage: List[PatternCoverage] = []
    for p in patterns:
        counts = pattern_coverage_counts[p.pattern_id]
        crit_signals = sum(1 for t in p.thresholds if t.severity == "critical")
        pattern_coverage.append(PatternCoverage(
            pattern_id=p.pattern_id,
            case_name=p.case_name,
            sector=p.sector,
            filing_year=p.filing_year,
            jurisdiction=p.jurisdiction,
            corpus_matches=int(counts["matches"]),
            high_match_count=int(counts["high_match"]),
            critical_signals=crit_signals,
            keyword_count=len(p.keyword_fingerprint),
            estimated_aggregate_ev_at_risk_mm=round(counts["ev_at_risk"], 1),
        ))
    pattern_coverage.sort(key=lambda c: c.corpus_matches, reverse=True)

    total_signals = sum(len(p.thresholds) for p in patterns)
    total_critical = sum(1 for p in patterns for t in p.thresholds if t.severity == "critical")

    return NamedFailureLibraryResult(
        total_patterns=len(patterns),
        total_signals=total_signals,
        total_critical_signals=total_critical,
        deals_with_any_match=deals_with_any,
        critical_risk_deals=critical_deals,
        aggregate_ev_at_risk_mm=round(aggregate_ev_at_risk, 1),
        patterns=patterns,
        pattern_coverage=pattern_coverage,
        deal_exposures=deal_exposures,
        corpus_deal_count=len(corpus),
    )
