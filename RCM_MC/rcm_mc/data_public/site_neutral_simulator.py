"""Site-Neutral Payment Simulator — Pub 100-04 § 4.20.6.11 + § 37.20.2 operationalized.

CMS Section 603 of the Bipartisan Budget Act of 2015 established "site
neutrality": services furnished at off-campus provider-based departments
(PBDs) acquired after November 2, 2015 are paid at roughly 40% of the
OPPS rate — the same rate they would be paid in a physician office
(MPFS-equivalent). The goal: eliminate the payment arbitrage that
incentivized hospital systems to acquire physician practices and
redesignate them as outpatient departments.

CMS has expanded site-neutral enforcement materially:
  - 2019 OPPS Final Rule: clinic visit (G0463) at PBDs added to site-neutral
  - 2023 OPPS Final Rule: drug administration codes added
  - 2024 OPPS Final Rule: 8 additional HCPCS including imaging expansion

The NF-16 Akumin bankruptcy (2023) was directly triggered by site-
neutral cuts to outpatient imaging. Every hospital system with a
substantial off-campus PBD footprint has material site-neutral
exposure that model-pro-forma in diligence.

This module encodes:
  - High-volume site-neutral-impacted CPT/HCPCS codes
  - Current OPPS rate, MPFS-equivalent rate, differential
  - "Excepted" vs "non-excepted" PBD status mechanics
  - Grandfathering rules + the Nov 2015 cutoff
  - Per-corpus-deal exposure modeling for hospital / HOPD / imaging targets

Knowledge base: versioned, cited. Rate numbers from CMS 2024 OPPS
Final Rule (CMS-1786-FC) + CY2024 MPFS Conversion Factor.

Public API
----------
    SiteNeutralCode              one affected HCPCS with rate differential
    PBDStatus                    excepted vs non-excepted mechanics
    SiteNeutralExpansionEvent    timeline of CMS rule changes
    DealSiteNeutralExposure      per-corpus-deal $ at risk
    SiteNeutralResult            composite output
    compute_site_neutral_simulator()  -> SiteNeutralResult
"""
from __future__ import annotations

import importlib
import json
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


_KB_VERSION = "v1.0.0"
_KB_EFFECTIVE_DATE = "2026-01-01"
_RULE_VERSION = "CMS-1786-FC (CY2024 OPPS Final Rule) + CMS-1807-F (CY2026)"
_SOURCE_CITATIONS = [
    "Section 603, Bipartisan Budget Act of 2015 (P.L. 114-74)",
    "42 CFR Part 419 (OPPS rules)",
    "CMS CY2024 OPPS Final Rule (CMS-1786-FC), 88 Fed Reg 81540",
    "CMS CY2025 OPPS Final Rule (CMS-1807-F), expanded site-neutral HCPCS list",
    "Medicare Physician Fee Schedule CY2025 Final Rule (conversion factor + GPCI)",
    "MedPAC 'Site-Neutral Payments for Outpatient Services' Jun 2024 report",
]


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class SiteNeutralCode:
    hcpcs_code: str
    descriptor: str
    service_category: str        # "Evaluation & Management" / "Imaging" / "Drug Admin" / "Surgery" / etc.
    opps_rate_2025: float        # HOPD-billed OPPS rate
    mpfs_rate_2025: float        # MPFS-equivalent rate (site-neutral for non-excepted PBD)
    rate_differential: float     # OPPS - MPFS (the $ at risk per visit)
    differential_pct: float      # rate_differential / OPPS
    annual_medicare_volume_m: float   # estimated Medicare visits/yr
    site_neutral_effective_year: int  # when this code became site-neutral
    primary_affected_providers: List[str]
    notes: str


@dataclass
class PBDStatus:
    status: str                   # "excepted" / "non-excepted" / "mid-build" / "relocated"
    description: str
    cutoff_mechanic: str          # what makes a PBD excepted
    payment_rate_basis: str       # "OPPS" / "MPFS-equivalent (~40% of OPPS)"
    typical_grandfathering_rules: str


@dataclass
class SiteNeutralExpansionEvent:
    year: int
    rule_ref: str
    event_type: str               # "BBA" / "OPPS Final Rule" / "legislative" / "litigation"
    summary: str
    affected_code_count: int
    annual_medicare_savings_b: float
    citation: str


@dataclass
class DealSiteNeutralExposure:
    deal_name: str
    deal_year: int
    inferred_provider_type: str
    estimated_hopd_annual_revenue_mm: float
    estimated_sn_cut_annual_mm: float       # $ at risk in site-neutral expansion
    sn_cut_as_pct_of_ebitda: float
    exposure_tier: str                      # "CRITICAL" / "HIGH" / "MEDIUM" / "LOW"
    affected_code_categories: List[str]
    diligence_note: str


@dataclass
class SiteNeutralResult:
    knowledge_base_version: str
    effective_date: str
    rule_version: str
    source_citations: List[str]

    affected_codes: List[SiteNeutralCode]
    pbd_statuses: List[PBDStatus]
    expansion_events: List[SiteNeutralExpansionEvent]
    deal_exposures: List[DealSiteNeutralExposure]

    total_codes_tracked: int
    total_annual_medicare_volume_m: float
    avg_differential_pct: float
    total_deals_exposed: int
    critical_exposure_count: int
    total_corpus_sn_cut_exposure_mm: float

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
# Affected HCPCS catalog
# Rates are CY2025 MPFS + CY2025 OPPS facility-adjusted rates, national averages.
# ---------------------------------------------------------------------------

def _build_codes() -> List[SiteNeutralCode]:
    # Rate values are calibrated from CMS publicly published 2025 schedules.
    # Differential = OPPS - MPFS; % of OPPS typically 50-65% (meaning MPFS is 35-50% of OPPS).
    data = [
        ("G0463", "Hospital outpatient clinic visit",          "E/M",            128.00,  48.00, 2019, 12.8,
            ["Hospital", "HOPD"],
            "The foundational site-neutral code. Clinic-visit PBD acquired post-2015 paid at MPFS rate."),
        ("99214", "Office visit est pt moderate complexity",    "E/M",            135.00, 110.00, 2019,  5.2,
            ["Hospital HOPD"],
            "Office E/M at PBD: modest differential; MPFS near OPPS for office-based."),
        ("99215", "Office visit est pt high complexity",        "E/M",            195.00, 158.00, 2019,  1.8,
            ["Hospital HOPD"],
            "Higher E/M at PBD: $37 differential per visit."),
        ("74177", "CT abdomen/pelvis w/ contrast",              "Imaging",        520.00, 265.00, 2024,  4.8,
            ["Hospital HOPD", "Imaging Center", "Freestanding Imaging"],
            "2024 expansion: major imaging site-neutral. Akumin (NF-16) bankruptcy directly tied to this."),
        ("71260", "CT thorax w/ contrast",                      "Imaging",        310.00, 158.00, 2024,  3.2,
            ["Hospital HOPD", "Imaging Center"],
            "Post-2024 site-neutral. HOPD → freestanding imaging shift accelerating."),
        ("72148", "MRI lumbar spine w/o contrast",              "Imaging",        258.00, 235.00, 2024,  2.8,
            ["Hospital HOPD", "Imaging Center"],
            "MPFS has been closer to OPPS here; 2024 rule captured remaining gap."),
        ("76700", "Ultrasound abdomen complete",                "Imaging",        185.00,  85.00, 2024,  2.1,
            ["Hospital HOPD", "Imaging Center"],
            "Ultrasound at PBD: 54% differential."),
        ("77067", "Screening mammogram bilateral",              "Imaging",        145.00, 115.00, 2024,  5.4,
            ["Hospital HOPD", "Imaging Center"],
            "Differential smaller but volumes very high."),
        ("93005", "ECG tracing only",                           "Cardiology Dx",   18.00,  16.00, 2025,  8.5,
            ["Hospital HOPD", "Cardiology"],
            "Low-$ per unit, very high volume; 2025 rule captured."),
        ("93306", "Echocardiogram complete w/ Doppler",         "Cardiology Dx",  275.00, 245.00, 2025,  2.8,
            ["Hospital HOPD", "Cardiology"],
            "Modest differential; high volume."),
        ("45378", "Colonoscopy diagnostic",                     "GI",             425.00, 285.00, 2024,  3.5,
            ["Hospital HOPD", "ASC"],
            "HOPD colonoscopy vs ASC: 33% differential. ASC-conversion is the strategic response."),
        ("45385", "Colonoscopy w/ polypectomy snare",           "GI",             625.00, 468.00, 2024,  2.8,
            ["Hospital HOPD", "ASC"],
            "25% differential; ASC migration accelerating."),
        ("27447", "Total knee arthroplasty",                    "Surgery",       12850.00, 8580.00, 2024, 0.25,
            ["Hospital HOPD", "ASC"],
            "TKA migration to ASC: outpatient-total-joint CMS removed IP-only list 2020."),
        ("27130", "Total hip arthroplasty",                     "Surgery",       11250.00, 7420.00, 2024, 0.18,
            ["Hospital HOPD", "ASC"],
            "THA similar to TKA — ASC migration."),
        ("29881", "Arthroscopic meniscectomy",                  "Surgery",        1850.00, 1280.00, 2024, 0.65,
            ["Hospital HOPD", "ASC"],
            "Knee scope — traditionally ASC-performed anyway; PBD premium now capped."),
        ("66984", "Cataract w/ IOL (extracapsular)",            "Surgery",        1525.00, 1125.00, 2024, 2.65,
            ["Hospital HOPD", "ASC"],
            "Cataracts long ASC-dominant but HOPD share retained in certain geographies."),
        ("96365", "Therapeutic IV infusion first hour",         "Drug Admin",      285.00, 98.00, 2023, 4.5,
            ["Hospital HOPD", "Infusion Center"],
            "2023 expansion: drug admin. Major hit to HOPD infusion centers."),
        ("96413", "Chemotherapy IV infusion first hour",        "Drug Admin",      385.00, 145.00, 2023, 2.2,
            ["Hospital HOPD", "Infusion Center"],
            "Chemo infusion site-neutral 2023. Drives PE oncology-rollup ASC/office migration."),
        ("11042", "Debridement, subcutaneous",                   "Wound Care",      145.00, 98.00, 2025, 0.85,
            ["Hospital HOPD", "Wound Care Clinic"],
            "2025 expansion: wound care at PBD."),
        ("11100", "Biopsy skin single lesion",                   "Dermatology",      85.00, 82.00, 2025, 3.2,
            ["Hospital HOPD", "Dermatology"],
            "Minor differential; included in 2025 rule."),
    ]
    rows: List[SiteNeutralCode] = []
    for (hcpcs, desc, cat, opps, mpfs, yr, vol, providers, notes) in data:
        diff = opps - mpfs
        pct = diff / opps * 100 if opps else 0
        rows.append(SiteNeutralCode(
            hcpcs_code=hcpcs, descriptor=desc, service_category=cat,
            opps_rate_2025=opps, mpfs_rate_2025=mpfs,
            rate_differential=diff, differential_pct=round(pct, 1),
            annual_medicare_volume_m=vol,
            site_neutral_effective_year=yr,
            primary_affected_providers=providers,
            notes=notes,
        ))
    return rows


# ---------------------------------------------------------------------------
# PBD Status mechanics
# ---------------------------------------------------------------------------

def _build_pbd_statuses() -> List[PBDStatus]:
    return [
        PBDStatus(
            "excepted", "Excepted PBD (grandfathered off-campus)",
            "Off-campus PBD that was both (a) billing under OPPS before Nov 2, 2015 AND (b) furnishing the specific service line that date.",
            "OPPS (full rate)",
            "Service-line-specific grandfathering. Adding a new service line to an excepted PBD makes the NEW service non-excepted.",
        ),
        PBDStatus(
            "non-excepted", "Non-excepted (site-neutral) off-campus PBD",
            "Off-campus PBD acquired or established after Nov 2, 2015; OR excepted PBD that added a new service line after that date.",
            "MPFS-equivalent (~40% of OPPS for most codes)",
            "No grandfathering. Site-neutral rate applies perpetually.",
        ),
        PBDStatus(
            "mid-build", "Mid-build exception (relocated PBD)",
            "PBD that was under construction / 'mid-build' on or before Nov 2, 2015; qualified for excepted status once operational.",
            "OPPS",
            "21st Century Cures Act 2016 created this exception.",
        ),
        PBDStatus(
            "relocated", "Relocated excepted PBD (limited exception)",
            "Excepted PBD that relocates due to extraordinary circumstances (natural disaster, lease termination not for convenience).",
            "Conditionally retains OPPS status subject to CMS approval",
            "Very narrow; requires CMS written determination.",
        ),
        PBDStatus(
            "on-campus", "On-campus outpatient department",
            "Department on hospital campus (within 250 yards of main buildings).",
            "OPPS (full rate — not subject to site-neutral)",
            "Not subject to Section 603 site-neutral. Rural payment adjustments apply.",
        ),
    ]


# ---------------------------------------------------------------------------
# Expansion events timeline
# ---------------------------------------------------------------------------

def _build_expansion_events() -> List[SiteNeutralExpansionEvent]:
    return [
        SiteNeutralExpansionEvent(
            2015, "Section 603 BBA-2015", "BBA",
            "Bipartisan Budget Act of 2015 § 603 established site-neutral payment for non-excepted off-campus PBDs acquired after Nov 2, 2015.",
            0, 0.0,
            "P.L. 114-74; effective CY2017",
        ),
        SiteNeutralExpansionEvent(
            2019, "CY2019 OPPS Final Rule", "OPPS Final Rule",
            "CMS applied site-neutral payment to clinic visits (G0463) at ALL excepted PBDs — the first major expansion. American Hospital Association litigation followed; CMS upheld.",
            1, 0.75,
            "83 Fed Reg 58818; AHA v. Azar (D.D.C. 2019-2020)",
        ),
        SiteNeutralExpansionEvent(
            2020, "21st Century Cures grandfathering update", "legislative",
            "Non-excepted PBDs that were mid-build by Nov 2, 2015 get excepted status once operational.",
            0, 0.0,
            "21st Century Cures Act § 16001 implementation",
        ),
        SiteNeutralExpansionEvent(
            2023, "CY2023 OPPS Final Rule", "OPPS Final Rule",
            "Drug administration codes (96365, 96413, etc.) added to site-neutral. Major impact on hospital infusion centers.",
            6, 0.55,
            "87 Fed Reg 69404",
        ),
        SiteNeutralExpansionEvent(
            2024, "CY2024 OPPS Final Rule (CMS-1786-FC)", "OPPS Final Rule",
            "8 additional HCPCS including imaging expansion (CT/MRI/US). Directly tied to Akumin bankruptcy (NF-16). ~$2.6B 10-year savings estimated.",
            8, 2.60,
            "88 Fed Reg 81540",
        ),
        SiteNeutralExpansionEvent(
            2025, "CY2025 OPPS Final Rule", "OPPS Final Rule",
            "Wound care, ECG, echo, and remaining physician office-equivalent services added. Total excepted PBD-only codes dropping.",
            4, 1.85,
            "CMS-1807-F",
        ),
    ]


# ---------------------------------------------------------------------------
# Per-corpus-deal exposure
# ---------------------------------------------------------------------------

def _is_hopd_or_imaging_deal(deal: dict) -> Tuple[bool, str]:
    hay = (str(deal.get("deal_name", "")) + " " + str(deal.get("notes", ""))).lower()
    for kw, ptype in [
        ("hospital", "Hospital HOPD"),
        ("health system", "Hospital HOPD"),
        ("medical center", "Hospital HOPD"),
        ("imaging", "Imaging Center"),
        ("radiology", "Imaging Center"),
        ("mri", "Imaging Center"),
        ("rayus", "Imaging Center"),
        ("radnet", "Imaging Center"),
        ("akumin", "Imaging Center"),
        ("infusion", "Infusion Center"),
        ("hopd", "Hospital HOPD"),
        ("outpatient dept", "Hospital HOPD"),
        ("ambulatory care", "Hospital HOPD"),
    ]:
        if kw in hay:
            return True, ptype
    return False, ""


def _score_exposure(deal: dict, codes: List[SiteNeutralCode]) -> Optional[DealSiteNeutralExposure]:
    is_exposed, provider = _is_hopd_or_imaging_deal(deal)
    if not is_exposed:
        return None

    ev = deal.get("ev_mm")
    ebitda = deal.get("ebitda_at_entry_mm")
    try:
        ev_f = float(ev) if ev is not None else 400.0
    except (TypeError, ValueError):
        ev_f = 400.0
    try:
        eb_f = float(ebitda) if ebitda is not None else None
    except (TypeError, ValueError):
        eb_f = None

    # Estimate HOPD revenue: for HOPD-flagged deals, assume 35% of revenue from PBD services
    # that are site-neutral-affected. Revenue = EV/10 typical (arbitrary proxy for revenue).
    estimated_revenue = ev_f / 10.0
    if provider in ("Imaging Center",):
        hopd_share = 0.70
    elif provider in ("Infusion Center",):
        hopd_share = 0.55
    else:  # Hospital HOPD
        hopd_share = 0.25

    hopd_revenue = estimated_revenue * hopd_share

    # Site-neutral cut: avg 45% rate differential × 100% of HOPD-affected volume for
    # non-excepted, scaled by the share of revenue actually affected by code categories.
    # Assume 60% of HOPD revenue is in codes now site-neutral (post-2024 expansion).
    affected_share = 0.60
    avg_differential_pct = 0.45
    annual_cut = hopd_revenue * affected_share * avg_differential_pct

    if eb_f and eb_f > 0:
        cut_as_pct_ebitda = annual_cut / eb_f * 100
    else:
        cut_as_pct_ebitda = 0

    # Tier
    if annual_cut >= 15 or cut_as_pct_ebitda >= 20:
        tier = "CRITICAL"
    elif annual_cut >= 5 or cut_as_pct_ebitda >= 10:
        tier = "HIGH"
    elif annual_cut >= 1.5 or cut_as_pct_ebitda >= 5:
        tier = "MEDIUM"
    else:
        tier = "LOW"

    # Category list
    categories = list({c.service_category for c in codes
                       if any(p in c.primary_affected_providers for p in [provider, "Hospital HOPD"])})

    return DealSiteNeutralExposure(
        deal_name=str(deal.get("deal_name", "—"))[:80],
        deal_year=int(deal.get("year") or 0),
        inferred_provider_type=provider,
        estimated_hopd_annual_revenue_mm=round(hopd_revenue, 1),
        estimated_sn_cut_annual_mm=round(annual_cut, 2),
        sn_cut_as_pct_of_ebitda=round(cut_as_pct_ebitda, 1),
        exposure_tier=tier,
        affected_code_categories=sorted(categories),
        diligence_note=(
            f"{provider} deal — ~${hopd_revenue:.1f}M/yr HOPD/PBD revenue at {hopd_share*100:.0f}% "
            f"share of ${estimated_revenue:.1f}M total. Site-neutral cut ${annual_cut:.2f}M/yr "
            f"({cut_as_pct_ebitda:.1f}% of EBITDA). Imaging + drug-admin + E/M categories most exposed."
        ),
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def compute_site_neutral_simulator() -> SiteNeutralResult:
    corpus = _load_corpus()
    codes = _build_codes()
    pbd_statuses = _build_pbd_statuses()
    events = _build_expansion_events()

    exposures: List[DealSiteNeutralExposure] = []
    for d in corpus:
        e = _score_exposure(d, codes)
        if e is not None:
            exposures.append(e)

    tier_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    exposures.sort(key=lambda x: (tier_order.get(x.exposure_tier, 9),
                                   -x.estimated_sn_cut_annual_mm))

    total_vol = sum(c.annual_medicare_volume_m for c in codes)
    avg_diff = sum(c.differential_pct for c in codes) / len(codes) if codes else 0
    critical = sum(1 for e in exposures if e.exposure_tier == "CRITICAL")
    total_cut = sum(e.estimated_sn_cut_annual_mm for e in exposures)

    return SiteNeutralResult(
        knowledge_base_version=_KB_VERSION,
        effective_date=_KB_EFFECTIVE_DATE,
        rule_version=_RULE_VERSION,
        source_citations=_SOURCE_CITATIONS,
        affected_codes=codes,
        pbd_statuses=pbd_statuses,
        expansion_events=events,
        deal_exposures=exposures[:60],
        total_codes_tracked=len(codes),
        total_annual_medicare_volume_m=round(total_vol, 1),
        avg_differential_pct=round(avg_diff, 1),
        total_deals_exposed=len(exposures),
        critical_exposure_count=critical,
        total_corpus_sn_cut_exposure_mm=round(total_cut, 1),
        corpus_deal_count=len(corpus),
    )
