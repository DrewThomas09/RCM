"""US clinical-specialty vertical deep-dive reference (CY2026), chart-ready.

The single source of truth for the *clinical-specialty* deal universe:
13 procedural / care-delivery verticals (ophthalmology, cardiology,
urology, ENT, OB-GYN, oncology, anesthesia/pain, FQHC/RHC, freestanding
EDs, telehealth/RPM, DMEPOS, audiology/optical, ACOs/VBC), each profiled
across the dimensions a deal team charts: billing codes, epidemiology,
workforce, geographic access, throughput benchmarks, reimbursement
mechanics, the 2026 policy drivers reshaping site-of-care, defensible
sources, and the chart types each fact supports.

Why this module exists
----------------------
``fee_schedule_2026.py`` carries the *dollar* backbone (conversion
factors, site-of-service arbitrage). ``site_neutral`` carries the
HOPD-to-ASC migration math. Neither answers "what is this clinical
vertical, how big is it, who works in it, and which 2026 rule is moving
its volume" — the qualitative + epidemiological scaffolding a screen or
an IC memo opens with. This module is that scaffolding, hard-coded and
citable, so the narrative layer (``ai/`` / ``ic_memo/``) and the UI never
fabricate a count or a source.

It deliberately does **not** restate the CY2026 conversion factors — it
imports them from :mod:`rcm_mc.data_public.fee_schedule_2026` so there is
exactly one place those constants live.

Sourcing & precision
--------------------
Figures are the defensible anchors from the CY2026 vertical deep-dive
brief: peer-reviewed journals (PubMed PMIDs where cited), federal
sources (CMS, SEER, CDC USCS, ACS, HRSA, AAMC, GAO), and named
registries (NCDR, IRIS, TVT, UDS). Where the brief gives a range or
flags a soft source, the value carries ``low``/``high`` bounds and a
``note`` — these are diligence-grade *sizing* figures, not claim-level
or epidemiological-study-grade. Confirm against the cited primary source
before publishing a chart. OBL counts, market-research market sizes, and
several prevalence figures are explicitly flagged as order-of-magnitude.

Public API::

    from rcm_mc.data_public.clinical_verticals_2026 import (
        CLINICAL_VERTICALS_2026,    # dict: key -> ClinicalVertical
        ClinicalVertical, CodeSet, Stat, VizSpec,
        POLICY_DRIVERS_2026,        # the cross-cutting 2026 forces
        get_vertical,               # key/alias -> ClinicalVertical
        list_verticals,             # all, sorted
        search_by_code,             # CPT/ICD/HCPCS -> [ClinicalVertical]
        verticals_with_asc_cpl_2026,# ASC-site-shift exposed verticals
        volume_anchors,             # the high-volume epi anchors, sorted
    )
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

# One place for the CY2026 dollar constants — never restated here.
from .fee_schedule_2026 import FEE_SCHEDULE_BACKBONE_2026

# ---------------------------------------------------------------------------
# Cross-cutting 2026 policy drivers (the brief's "single most important
# cross-cutting fact" set). These are the forces a chart annotates against.
# ---------------------------------------------------------------------------

POLICY_DRIVERS_2026: Dict[str, str] = {
    "ipo_phaseout": (
        "Inpatient-Only (IPO) list phase-out accelerated: 285 procedures "
        "removed for CY2026, full elimination by Jan 1, 2028 (CMS-1834-FC)."
    ),
    "asc_cpl_expansion": (
        "ASC Covered Procedures List adds 560 surgical procedures + 35 "
        "ancillary services for 2026 (incl. cardiac ablation, lumbar fusion, "
        "vascular embolization) — accelerates the HOPD->ASC/OBL site shift."
    ),
    "pci_asc_eligibility": (
        "All PCI added to the ASC-CPL; cardiac ablation ASC-eligible — "
        "OBL / cardiac-ASC volume tailwind."
    ),
    "efficiency_adjustment": (
        "-2.5% efficiency adjustment to work RVUs of non-time-based codes; "
        "indirect-PE reallocation cuts facility-based payment ~-7%, raises "
        "non-facility ~+4% (CMS-1832-F)."
    ),
    "nsa_idr": (
        "No Surprises Act IDR: providers won 85% of line-item disputes in "
        "2024; median award 445% of QPA (459% in Q4 2024) — anesthesia / EM "
        "/ radiology revenue-cycle risk."
    ),
    "rpm_expansion": (
        "Two new RPM codes for 2026 (99445 device 2-15 days, 99470 first 10 "
        "min mgmt) plus rate increases — virtual-care reimbursement widened."
    ),
}


# ---------------------------------------------------------------------------
# Value types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Stat:
    """One epidemiology / workforce / access figure with provenance.

    ``value`` is the central (chartable) figure; ``low``/``high`` carry
    the range when the brief gives one (e.g. cataract 3.8-4.2M) so a
    chart can render an error bar instead of a false-precision point.
    ``year`` and ``source`` make the figure citable; ``note`` carries
    the caveat that keeps a soft figure from being charted as hard.
    """

    label: str
    value: Optional[float]
    unit: str
    source: str
    year: Optional[int] = None
    low: Optional[float] = None
    high: Optional[float] = None
    note: str = ""


@dataclass(frozen=True)
class CodeSet:
    """The billing-code surface of a vertical.

    Kept as plain code strings (not rate-bearing) — the dollars live in
    ``fee_schedule_2026``. ``cpt`` are procedure/visit codes, ``hcpcs``
    are J-codes / Level-II device codes, ``icd10`` are the diagnosis
    funnels, ``drg`` the inpatient groupers, ``taxonomy`` the NUCC
    provider taxonomy codes (used to count supply via NPPES).
    """

    cpt: List[str] = field(default_factory=list)
    hcpcs: List[str] = field(default_factory=list)
    icd10: List[str] = field(default_factory=list)
    drg: List[str] = field(default_factory=list)
    taxonomy: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class VizSpec:
    """A chart the vertical's data supports (the brief's 'Viz' line)."""

    chart_type: str
    description: str


@dataclass(frozen=True)
class ClinicalVertical:
    """A single clinical-specialty vertical profile."""

    key: str
    name: str
    aliases: List[str]
    summary: str
    codes: CodeSet
    epidemiology: List[Stat]
    workforce: List[Stat]
    access: List[Stat]
    benchmarks: List[Stat]
    reimbursement: str
    policy_2026: List[str]          # keys into POLICY_DRIVERS_2026
    asc_cpl_2026: bool              # exposed to the ASC site-shift agenda
    sources: List[str]
    viz: List[VizSpec]
    caveats: List[str] = field(default_factory=list)

    def all_codes(self) -> List[str]:
        """Every code (any system) this vertical references, upper-cased."""
        c = self.codes
        return [s.upper() for s in (c.cpt + c.hcpcs + c.icd10 + c.drg + c.taxonomy)]


# ---------------------------------------------------------------------------
# The 13 verticals
# ---------------------------------------------------------------------------

CLINICAL_VERTICALS_2026: Dict[str, ClinicalVertical] = {
    "ophthalmology": ClinicalVertical(
        key="ophthalmology",
        name="Ophthalmology / Cataract / Retina",
        aliases=["eye", "retina", "cataract", "optometry"],
        summary=(
            "High-volume cataract surgery (ASC) plus drug-margin-driven "
            "retina (anti-VEGF buy-and-bill). Strong HOPD->ASC shift; "
            "optometry adjacency."
        ),
        codes=CodeSet(
            cpt=["66984", "66982", "67028", "66174", "65855", "92134",
                 "92083", "66821"],
            hcpcs=["J0178", "J2778", "J9035", "J7999", "J2777"],
            icd10=["H25", "H35.31", "H35.32", "E11.3", "H40"],
            taxonomy=["207W00000X", "152W00000X"],
        ),
        epidemiology=[
            Stat("Cataract surgeries / yr", 3.8e6, "procedures/yr",
                 "Eye/Nature 2025", 2025, low=3.8e6, high=4.2e6,
                 note="~1.4M among Medicare FFS."),
            Stat("Anti-VEGF injections / yr", 2.5e6, "injections/yr",
                 "peer-reviewed", note="Busiest retina specialists ~50/day."),
            Stat("Anti-VEGF Medicare Part B spend (2019)", 4.02e9, "USD",
                 "Berkowitz et al. PMID 38315793", 2019,
                 note="Up from $2.51B in 2014; historically >12% of Part B."),
            Stat("Mean anti-VEGF injections / eye / yr", 4.9, "injections",
                 "peer-reviewed", low=4.8, high=5.0),
        ],
        workforce=[
            Stat("Practicing ophthalmologists", 18500, "count",
                 "Ophthalmology 2024", 2023,
                 note="~21,250 FTE in 2020; projected -12% by 2035."),
            Stat("Optometrists", 42500, "count", "varies by FTE/headcount",
                 low=37000, high=48000),
        ],
        access=[
            Stat("State variation in anti-VEGF injection rate", 6.8, "x fold",
                 "Berkowitz et al. PMID 38315793",
                 note="Correlated with injecting-physician density; choropleth."),
        ],
        benchmarks=[
            Stat("Cataract case time (ASC)", 15.0, "minutes/case",
                 "industry", low=10.0, high=20.0,
                 note="Premium/refractive IOLs are cash-pay add-ons."),
        ],
        reimbursement=(
            "PFS + OPPS/ASC facility + Part B buy-and-bill for retina drugs "
            "(ASP+6%). Strong site shift to ASC. ~11% professional cut on "
            "cataract (66984) in 2026 — largest single-year cut in decades."
        ),
        policy_2026=["asc_cpl_expansion", "efficiency_adjustment"],
        asc_cpl_2026=True,
        sources=["AAO IRIS Registry", "CMS Part B", "Eye (Nature) 2025",
                 "Ophthalmology 2024"],
        viz=[
            VizSpec("100% stacked bar", "Anti-VEGF agent mix (aflibercept / "
                    "bevacizumab / ranibizumab / faricimab)."),
            VizSpec("line", "Anti-VEGF Part B spend 2014->2019."),
            VizSpec("choropleth", "Injection rate by state."),
        ],
        caveats=["Ophthalmologist headcount 16,865-21,250 by FTE vs headcount."],
    ),
    "cardiology": ClinicalVertical(
        key="cardiology",
        name="Cardiology (Cath/IC, EP, Structural, OBL)",
        aliases=["cardiac", "ep", "electrophysiology", "structural heart",
                 "interventional cardiology"],
        summary=(
            "Cath/PCI, electrophysiology (AF ablation), and structural "
            "(TAVR/LAAC). 2026 ASC-CPL adds cardiac ablation and all PCI — "
            "the largest near-term OBL/ASC volume mover in the procedural set."
        ),
        codes=CodeSet(
            cpt=["92920", "92928", "92944", "93452", "93458", "93461",
                 "33361", "33369", "93656", "93657", "33340", "93306",
                 "93015", "78451"],
            icd10=["I25", "I48", "I35", "I50"],
            drg=["216", "227", "246", "251", "266", "267"],
            taxonomy=["207RC0000X"],
        ),
        epidemiology=[
            Stat("PCIs / yr", 600000, "procedures/yr", "JAHA 2023", 2023,
                 note=">1,600 centers; ~1M diagnostic caths/yr."),
            Stat("AF prevalence (US adults)", 10.55e6, "people", "JACC 2024",
                 2024, low=5.3e6, high=10.55e6,
                 note="Older AHA estimate ~5.3M; chart the range."),
            Stat("AF ablations (2023, Medicare)", 76401, "procedures",
                 "JCE 2025", 2023, note="+11.7%/yr; all-payer likely higher."),
            Stat("Isolated TAVRs (TVT Registry, 2020Q1-2024Q1)", 383030,
                 "procedures", "STS/ACC TVT Registry",
                 note="72,991 in 2019 alone, exceeding all SAVR."),
        ],
        workforce=[
            Stat("Active cardiovascular disease specialists", 22243, "count",
                 "AAMC 2022 Physician Specialty Data Report", 2022,
                 note="62.8% over age 55 — aging/shortage signal."),
        ],
        access=[
            Stat("Office-based labs (OBLs)", 600, "count",
                 "industry estimate", low=500, high=700,
                 note="NO government registry; mostly vascular; "
                      "order-of-magnitude only."),
        ],
        benchmarks=[
            Stat("TAVR national 30-day mortality", 2.0, "pct",
                 "TVT Registry", note="Stroke 2.2%; fell from 7.2% (2011)."),
        ],
        reimbursement=(
            "PFS/OPPS/ASC + IPPS DRG. Cardiac ablation + all PCI added to "
            "ASC-CPL for 2026. LAAC (33340) wRVU cut 14.00->10.25 (contested)."
        ),
        policy_2026=["asc_cpl_expansion", "pci_asc_eligibility", "ipo_phaseout"],
        asc_cpl_2026=True,
        sources=["ACC NCDR (CathPCI, AFib Ablation, TVT)",
                 "AHA Heart Disease & Stroke Statistics", "CMS"],
        viz=[
            VizSpec("line", "TAVR vs SAVR volume crossover."),
            VizSpec("range bar", "AF-prevalence estimate range (5.3M vs 10.55M)."),
            VizSpec("stacked bar", "Procedure by site of care."),
        ],
        caveats=["OBL counts are industry estimates — no registry exists.",
                 "Diagnostic cath ~1M is derived, less precisely sourced."],
    ),
    "urology": ClinicalVertical(
        key="urology",
        name="Urology (BPH, Prostate Cancer, Stones)",
        aliases=["bph", "prostate", "kidney stones", "uro"],
        summary=(
            "BPH minimally-invasive surgical therapies (UroLift/Rezum), "
            "prostate cancer, and stone disease. Office-based ancillaries "
            "(path, imaging, LHRH buy-and-bill) drive economics."
        ),
        codes=CodeSet(
            cpt=["52601", "52441", "52442", "53854", "52648", "55700",
                 "55866", "52356", "50590", "50080"],
            hcpcs=["J9217", "J3315"],
            icd10=["N40", "C61", "N20"],
            taxonomy=["208800000X"],
        ),
        epidemiology=[
            Stat("Prostate cancer new cases (2025 est.)", 313780, "cases",
                 "ACS 2025", 2025,
                 note="35,770 deaths; most common male cancer; "
                      "incidence +3.0%/yr since 2014."),
            Stat("Kidney-stone surgeries / yr", 485000, "procedures/yr",
                 "NIDDK / peer-reviewed", low=470000, high=500000,
                 note="URS ~2/3 of stone surgeries, growing ~15%/yr."),
            Stat("BPH-affected US men", 40e6, "men", "commonly cited",
                 note="~50% of men by 60, up to 90% by 80. Soft anchor."),
        ],
        workforce=[
            Stat("Urologists", 13000, "count", "AUA Census",
                 note="Aging/shortage; approximate — verify vs AUA Census."),
        ],
        access=[],
        benchmarks=[
            Stat("Rezum symptom-score improvement", 58.0, "pct",
                 "single-institution study",
                 note="vs UroLift ~44.5%; office-based MIST."),
        ],
        reimbursement=(
            "PFS office + ASC; UroLift/Rezum office-based with bundled device "
            "margin in non-facility fee. LHRH (J9217) buy-and-bill."
        ),
        policy_2026=["asc_cpl_expansion"],
        asc_cpl_2026=True,
        sources=["AUA Census", "SEER", "CDC USCS", "NIDDK", "ACS"],
        viz=[
            VizSpec("trend", "Prostate-cancer incidence by stage (local vs "
                    "advanced)."),
            VizSpec("funnel", "BPH treatment funnel (medical -> MIST -> "
                    "TURP/HoLEP)."),
        ],
        caveats=["Urologist count ~13,000 approximate.",
                 "BPH prevalence (~15M over 30 vs ~40M total) circulates via "
                 "marketing pages — treat as soft."],
    ),
    "otolaryngology": ClinicalVertical(
        key="otolaryngology",
        name="Otolaryngology (ENT)",
        aliases=["ent", "sinus", "otology", "sleep"],
        summary=(
            "Sinus (balloon sinuplasty / FESS), otology (tympanostomy), and "
            "sleep (hypoglossal nerve stim). Office-based balloon procedures "
            "growing fast."
        ),
        codes=CodeSet(
            cpt=["31295", "31298", "31254", "31288", "69436", "69210",
                 "42820", "95810", "42145", "64568", "95004", "95165"],
            icd10=["J32", "J35", "H65", "H66", "G47.33"],
            taxonomy=["207Y00000X"],
        ),
        epidemiology=[
            Stat("Chronic rhinosinusitis prevalence (US adults)", 31e6,
                 "people", "AAO-HNS / peer-reviewed",
                 note="~12% of adults; ~$14.4B direct cost."),
            Stat("Stand-alone balloon sinuplasty share (2011->2014)", 22.5,
                 "pct", "Int Forum Allergy Rhinol", 2014, low=5.0, high=22.5,
                 note="n=661,738 CRS patients."),
        ],
        workforce=[
            Stat("Otolaryngologists", 12000, "count", "AAO-HNS",
                 note="Approximate — verify vs AAO-HNS census."),
        ],
        access=[],
        benchmarks=[
            Stat("Balloon caseload / surgeon / yr (stand-alone)", 12.0,
                 "cases", "survey median", low=12.0, high=31.0,
                 note="~31 when performed with FESS."),
        ],
        reimbursement=(
            "Office vs ASC; balloon bundled when performed with FESS in the "
            "same sinus."
        ),
        policy_2026=["asc_cpl_expansion"],
        asc_cpl_2026=True,
        sources=["AAO-HNS", "AHRQ HCUP", "Int Forum Allergy Rhinol"],
        viz=[
            VizSpec("stacked area", "Balloon vs FESS vs hybrid trend."),
            VizSpec("funnel", "CRS care funnel."),
        ],
        caveats=["Otolaryngologist count ~12,000 approximate."],
    ),
    "obgyn": ClinicalVertical(
        key="obgyn",
        name="OB-GYN / Women's Health",
        aliases=["obstetrics", "gynecology", "maternity", "womens health"],
        summary=(
            "Obstetrics (global maternity payment, Medicaid-heavy) and "
            "gynecology (hysterectomy). Defined by maternity-care deserts and "
            "workforce aging."
        ),
        codes=CodeSet(
            cpt=["59400", "59510", "59409", "59514", "58150", "58571",
                 "76801", "59025"],
            icd10=["O80", "O82", "Z34", "D25"],
            drg=["765", "768", "774", "775"],
            taxonomy=["207V00000X"],
        ),
        epidemiology=[
            Stat("US births / yr", 3.6e6, "births/yr", "NCHS natality"),
            Stat("Medicaid share of births (2022)", 41.0, "pct", "CMS", 2022),
        ],
        workforce=[
            Stat("OB providers practicing rural", 7.0, "pct",
                 "March of Dimes 2024", 2024,
                 note="OB-GYN shortage; CNMs/midwives supplement."),
        ],
        access=[
            Stat("Maternity-care-desert counties", 1104, "counties",
                 "March of Dimes 2024 ('Nowhere to Go')", 2024,
                 note="35.1% of US counties; 61.5% rural."),
            Stat("Reproductive-age women in deserts", 2.3e6, "women",
                 "March of Dimes 2024", 2024,
                 note="~150,000 births affected; 5.5M with no/limited access."),
            Stat("Rural women driving >30 min to OB hospital", 50.0, "pct",
                 "March of Dimes 2024", 2024),
        ],
        benchmarks=[
            Stat("Pre-pregnancy hypertension increase (2015->2022)", 80.0,
                 "pct", "CDC", 2022, note="1.3x higher in deserts."),
        ],
        reimbursement=(
            "Global maternity payment (antepartum + delivery + postpartum); "
            "Medicaid-heavy payer mix -> low reimbursement is a cited closure "
            "driver. 100+ OB units closed 2021-2022."
        ),
        policy_2026=[],
        asc_cpl_2026=False,
        sources=["March of Dimes 2024", "NCHS natality",
                 "HRSA Area Health Resources Files", "CMS NPPES"],
        viz=[
            VizSpec("choropleth", "Maternity access-tier by county."),
            VizSpec("stacked bar", "Payer mix (Medicaid vs commercial)."),
            VizSpec("timeline", "OB-unit closures."),
        ],
        caveats=[],
    ),
    "oncology": ClinicalVertical(
        key="oncology",
        name="Oncology / Hematology",
        aliases=["cancer", "hematology", "medical oncology",
                 "radiation oncology"],
        summary=(
            "Medical + radiation oncology defined by drug-margin economics "
            "(buy-and-bill ASP+6%, 340B spread) and the Enhancing Oncology "
            "Model (EOM) value-based overlay."
        ),
        codes=CodeSet(
            cpt=["96413", "96415", "96417", "96360", "77385", "77386",
                 "77373", "77263", "G2211"],
            hcpcs=["J9271", "J9299"],
            icd10=["C00", "C96"],
            taxonomy=["207RX0202X", "2085R0001X"],
        ),
        epidemiology=[
            Stat("New cancer cases / yr (US)", 2.0e6, "cases/yr", "SEER/ACS",
                 note="EOM covers 7 cancer types."),
        ],
        workforce=[
            Stat("EOM practitioners (Cohort 2, 2025)", 3000, "practitioners",
                 "CMS Innovation Center", 2025,
                 note="~500 sites, 33 states + DC."),
        ],
        access=[],
        benchmarks=[
            Stat("EOM PP1 participants achieving savings", 79.0, "pct",
                 "CMS Innovation Center",
                 note="Of 43 evaluated; >50% earned top quality bonus."),
            Stat("MEOS payment (EOM)", 110.0, "USD PBPM",
                 "CMS Innovation Center",
                 note="$140 dual-eligible; down from OCM's $160."),
        ],
        reimbursement=(
            "Buy-and-bill (ASP+6%); 340B spread defines hospital vs community "
            "economics; EOM $110 PBPM MEOS. CY2026 PFS: heme/onc +2%, "
            "radiation oncology -2%. 340B hospitals to receive $9B lump sum "
            "for 2018-2022 cuts."
        ),
        policy_2026=["efficiency_adjustment"],
        asc_cpl_2026=False,
        sources=["CMS Innovation Center (EOM)", "SEER",
                 "Community Oncology Alliance", "ASCO"],
        viz=[
            VizSpec("scatter", "EOM savings vs quality."),
            VizSpec("waterfall", "Community vs 340B drug-margin."),
            VizSpec("timeline", "MEOS rate (OCM $160 -> EOM $110)."),
        ],
        caveats=["EOM participant counts in flux — confirm current roster "
                 "before time-series charting."],
    ),
    "anesthesia_pain": ClinicalVertical(
        key="anesthesia_pain",
        name="Anesthesiology & Pain Management",
        aliases=["anesthesia", "pain", "interventional pain", "crna"],
        summary=(
            "Anesthesia (separate base+time-unit CF; care-team staffing) and "
            "interventional pain (ESI, RFA, SCS). Defined by the No Surprises "
            "Act IDR battle and an acute workforce shortage."
        ),
        codes=CodeSet(
            cpt=["00100", "01999", "62321", "62323", "64483", "64484",
                 "64493", "64635", "64636", "63650", "63655", "63685"],
            icd10=["M54", "G89", "M47"],
            taxonomy=["207L00000X"],
        ),
        epidemiology=[],
        workforce=[
            Stat("Median pain-medicine compensation", 460000, "USD",
                 "MGMA 2026", 2026, low=420000, high=500000,
                 note="At 6,500-8,500 wRVU."),
        ],
        access=[
            Stat("States requiring physician oversight of CRNAs", 45, "states",
                 "ASA/AANA", note="Care-team vs CRNA-independent models."),
        ],
        benchmarks=[
            Stat("Provider IDR line-item win rate (2024)", 85.0, "pct",
                 "Georgetown CHIR / Federal IDR PUF", 2024,
                 note="Up from 81% in 2023."),
            Stat("Median IDR determination (full-year 2024)", 445.0,
                 "pct of QPA", "Georgetown CHIR / Federal IDR PUF", 2024,
                 note="327% in 2023; 459% in Q4 2024."),
            Stat("SCS implant (63650) work RVU", 11.50, "wRVU",
                 "CMS CY2026 PFS", 2026),
        ],
        reimbursement=(
            "Anesthesia uses a separate CF (base + time units x CF); ASC pain "
            "shift continuing. UnitedHealthcare cut CRNA (QZ-modifier) "
            "reimbursement 15% effective 10/1/2025."
        ),
        policy_2026=["nsa_idr", "asc_cpl_expansion"],
        asc_cpl_2026=True,
        sources=["ASA", "AANA", "CMS Federal IDR Public Use Files",
                 "Georgetown CHIR / Health Affairs", "MGMA"],
        viz=[
            VizSpec("dual-axis line", "IDR win-rate & award-to-QPA multiple."),
            VizSpec("100% stacked bar", "Staffing model mix."),
            VizSpec("grouped bar", "Pain wRVU by procedure."),
        ],
        caveats=[],
    ),
    "fqhc_rhc": ClinicalVertical(
        key="fqhc_rhc",
        name="FQHCs & RHCs",
        aliases=["fqhc", "rhc", "community health center", "safety net"],
        summary=(
            "Federally Qualified Health Centers and Rural Health Clinics — "
            "the safety net. PPS/AIR per-encounter payment, Medicaid/"
            "uninsured-heavy mix, mandatory UDS reporting."
        ),
        codes=CodeSet(
            cpt=["G0466", "G0470"],
            icd10=[],
            taxonomy=["261QF0400X", "261QR1300X"],
        ),
        epidemiology=[
            Stat("CHCs / FQHC organizations", 1512, "organizations",
                 "NACHC / 2024 UDS", 2024,
                 note="17,000+ sites; ~326,000 FTE workforce."),
            Stat("Share of US population served", 14.0, "pct",
                 "NACHC / 2024 UDS", 2024,
                 note="For ~1% of healthcare spending."),
        ],
        workforce=[
            Stat("FQHC FTE workforce", 326000, "FTE", "NACHC / 2024 UDS",
                 2024),
        ],
        access=[
            Stat("FQHC participation growth in MSSP ACOs (2023->2024)", 36.0,
                 "pct", "CMS", 2024),
        ],
        benchmarks=[],
        reimbursement=(
            "FQHC PPS per-encounter rate; RHC all-inclusive rate (AIR, "
            "statutorily capped for non-provider-based); enhanced Medicaid "
            "PPS. RPM billable via individual CPT codes (2025+). Telehealth "
            "billing extended through 2026."
        ),
        policy_2026=["rpm_expansion"],
        asc_cpl_2026=False,
        sources=["HRSA UDS 2024 (data.hrsa.gov)",
                 "NACHC Community Health Center Chartbook"],
        viz=[
            VizSpec("stacked bar", "Payer mix (Medicaid/uninsured/Medicare/"
                    "commercial)."),
            VizSpec("bar", "UDS clinical quality measures vs national HEDIS."),
        ],
        caveats=[],
    ),
    "freestanding_ed": ClinicalVertical(
        key="freestanding_ed",
        name="Freestanding EDs & Emergency Medicine",
        aliases=["fsed", "emergency medicine", "er", "freestanding er"],
        summary=(
            "Freestanding emergency departments (Texas-concentrated) and "
            "emergency medicine. Two-bill (facility + professional) model; a "
            "surprise-billing flashpoint."
        ),
        codes=CodeSet(
            cpt=["99281", "99285", "99291", "99292"],
            taxonomy=["207P00000X"],
        ),
        epidemiology=[
            Stat("FSED growth (2001->2016)", 10.0, "x fold", "KFF/ACEP",
                 note="Concentrated in Texas, Colorado."),
        ],
        workforce=[],
        access=[
            Stat("Urgent-care vs low-acuity ER cost", 10.0, "x cheaper",
                 "KFF Health News"),
        ],
        benchmarks=[],
        reimbursement=(
            "Facility fee comparable to hospital ED; NSA prohibits balance "
            "billing for emergency services. Many FSEDs out-of-network -> "
            "surprise-billing exposure. Level 4-5 codes common (high acuity)."
        ),
        policy_2026=["nsa_idr"],
        asc_cpl_2026=False,
        sources=["Texas HHSC FEMC directory", "KFF Health News", "ACEP"],
        viz=[
            VizSpec("bar", "Acuity mix (E&M level)."),
            VizSpec("bar", "Urgent-care vs FSED cost comparison."),
        ],
        caveats=[],
    ),
    "telehealth_rpm": ClinicalVertical(
        key="telehealth_rpm",
        name="Telehealth / RPM / RTM",
        aliases=["telehealth", "rpm", "rtm", "remote monitoring",
                 "virtual care"],
        summary=(
            "Remote patient/therapeutic monitoring and e-visits. 2026 added "
            "two RPM codes and raised rates; statutory telehealth "
            "flexibilities remain policy-contingent."
        ),
        codes=CodeSet(
            cpt=["99453", "99454", "99457", "99458", "99091", "99445",
                 "99470", "98975", "98977", "98980", "99421", "99423"],
            taxonomy=[],
        ),
        epidemiology=[
            Stat("Per-patient monthly RPM revenue", 160.0, "USD/month",
                 "CMS CY2026 PFS / AMA CPT", 2026, low=78.0, high=245.0,
                 note="~100 patients at minimum service ~= $110K/yr."),
        ],
        workforce=[],
        access=[],
        benchmarks=[
            Stat("99454 device-supply rate (2026)", 52.11, "USD",
                 "CMS CY2026 PFS", 2026,
                 note="99445 (new, 2-15 days) ~$52.11; mutually exclusive."),
            Stat("99457 first-20-min mgmt rate (2026)", 51.77, "USD",
                 "CMS CY2026 PFS", 2026,
                 note="99470 (new, first 10 min) ~$26.05; mutually exclusive."),
        ],
        reimbursement=(
            "Per-code PFS billing. Direct supervision via real-time audio/"
            "video made permanent; FQHC/RHC telehealth billing extended "
            "through 2026. Post-PHE statutory flexibilities policy-contingent."
        ),
        policy_2026=["rpm_expansion"],
        asc_cpl_2026=False,
        sources=["CMS CY2026 PFS Final Rule", "AMA CPT"],
        viz=[
            VizSpec("stacked bar", "Per-patient RPM revenue by code."),
            VizSpec("grouped bar", "2025 vs 2026 rate comparison."),
        ],
        caveats=[],
    ),
    "dmepos": ClinicalVertical(
        key="dmepos",
        name="DME / DMEPOS",
        aliases=["dme", "dmepos", "durable medical equipment",
                 "competitive bidding"],
        summary=(
            "Durable medical equipment, prosthetics, orthotics & supplies. "
            "Defined by the Competitive Bidding Program (CBP) gap period and "
            "the narrowed 2028 bid round."
        ),
        codes=CodeSet(
            hcpcs=["E0601", "E0470", "E1390", "E0431", "K0001", "E0143",
                   "A4253", "E0784", "E2103"],
            taxonomy=["332B00000X"],
        ),
        epidemiology=[],
        workforce=[],
        access=[],
        benchmarks=[
            Stat("Sequestration on all FFS claims", 2.0, "pct", "CMS",
                 note="Applies to all DMEPOS FFS claims."),
        ],
        reimbursement=(
            "CBP gap period — former CBA rates apply; next-round contracts "
            "effective no later than Jan 1, 2028. 2028 round = ONLY 7 Remote "
            "Item Delivery categories (CGMs/insulin pumps, urological, "
            "ostomy, OTS braces). Legacy categories (oxygen, CPAP, standard "
            "wheelchairs, hospital beds, walkers, enteral) EXCLUDED."
        ),
        policy_2026=[],
        asc_cpl_2026=False,
        sources=["CMS DMEPOS Fee Schedule", "CBIC Round 2028", "AAHomecare"],
        viz=[
            VizSpec("bar", "Product category (RID-bid vs excluded)."),
            VizSpec("stacked bar", "Rental vs purchase by category."),
        ],
        caveats=[],
    ),
    "audiology_optical": ClinicalVertical(
        key="audiology_optical",
        name="Audiology & Optical/Vision",
        aliases=["audiology", "hearing", "optical", "vision", "optician"],
        summary=(
            "Hearing (audiometry, hearing aids) and vision (refraction, "
            "spectacle/contact fitting). Largely cash-pay/uncovered; reshaped "
            "by the 2022 OTC hearing-aid rule."
        ),
        codes=CodeSet(
            cpt=["92557", "92567", "92587", "92590", "92015", "92340",
                 "92310"],
            taxonomy=["231H00000X", "156FX1700X"],
        ),
        epidemiology=[
            Stat("US adults who could benefit from hearing aids", 29e6,
                 "people", "GAO-24-106854",
                 note="~38-48M with some hearing loss."),
            Stat("Hearing-aid adoption (2025)", 39.0, "pct",
                 "MarkeTrak 2025", 2025,
                 note="Up from 23% in 1989; OTC ~5.7% of users."),
        ],
        workforce=[],
        access=[
            Stat("OTC hearing-aid users getting full service", 51.0, "pct",
                 "MarkeTrak 2025", 2025, note="vs 90% of traditional-device "
                 "users; OTC ~50% cheaper."),
        ],
        benchmarks=[],
        reimbursement=(
            "Hearing aids largely cash-pay/uncovered (Medicare excludes); "
            "refraction often non-covered."
        ),
        policy_2026=[],
        asc_cpl_2026=False,
        sources=["NIDCD", "MarkeTrak 2025", "GAO-24-106854", "CDC"],
        viz=[
            VizSpec("line", "Hearing-aid adoption trend (1989->2025)."),
            VizSpec("grouped bar", "Traditional vs OTC service level."),
        ],
        caveats=["OTC hearing-aid market size (~$164.9M) is market-research "
                 "grade — less authoritative than federal sources."],
    ),
    "aco_vbc": ClinicalVertical(
        key="aco_vbc",
        name="ACOs & Value-Based Care",
        aliases=["aco", "mssp", "value-based care", "vbc", "shared savings"],
        summary=(
            "Medicare Shared Savings Program ACOs and value-based care. "
            "Physician-led/low-revenue ACOs outperform hospital-led; new "
            "Ambulatory Specialty Model launches 2027."
        ),
        codes=CodeSet(taxonomy=[]),
        epidemiology=[
            Stat("MSSP ACOs (PY2024)", 476, "ACOs", "CMS SSP Results", 2024,
                 note="+5% YoY; 10.3M assigned beneficiaries."),
            Stat("MSSP assigned beneficiaries (PY2024)", 10.3e6,
                 "beneficiaries", "CMS SSP Results", 2024,
                 note="11.2M across MSSP+REACH per MedPAC."),
        ],
        workforce=[],
        access=[],
        benchmarks=[
            Stat("Net Medicare savings (PY2024)", 2.4e9, "USD",
                 "CMS SSP Results", 2024,
                 note="Highest since program inception; $6.6B gross."),
            Stat("ACOs earning performance payments (PY2024)", 75.0, "pct",
                 "CMS SSP Results", 2024,
                 note="$4.1B payments; 67% in downside risk."),
            Stat("Net per-capita savings (PY2024)", 241.0, "USD",
                 "CMS SSP Results", 2024, note="$643 gross per capita."),
        ],
        reimbursement=(
            "Benchmark = 3-yr baseline blended with regional spending + "
            "prior-savings adjustment; BASIC A-E and ENHANCED tracks. CY2026: "
            "remove health-equity adjustment + SDOH screening measure, add "
            "web-based CAHPS (2027). Mandatory Ambulatory Specialty Model "
            "(heart failure, low back pain) launches Jan 1, 2027."
        ),
        policy_2026=[],
        asc_cpl_2026=False,
        sources=["CMS Shared Savings Program data (data.cms.gov)",
                 "MedPAC Payment Basics 2025", "NAACOS",
                 "Health Affairs Forefront"],
        viz=[
            VizSpec("stacked bar", "Savings by track (Enhanced vs others)."),
            VizSpec("line", "Per-capita savings trend."),
            VizSpec("grouped bar", "Physician-led vs hospital-led."),
        ],
        caveats=[],
    ),
}


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

# Alias -> canonical key, resolved once. A vertical also resolves by its
# own key. Aliases are kept lowercase for case-insensitive lookup.
_ALIAS_INDEX: Dict[str, str] = {}
for _key, _v in CLINICAL_VERTICALS_2026.items():
    _ALIAS_INDEX[_key.lower()] = _key
    for _a in _v.aliases:
        _ALIAS_INDEX.setdefault(_a.lower(), _key)


def get_vertical(key: str) -> ClinicalVertical:
    """Resolve a vertical by canonical key or any registered alias.

    Case- and whitespace-insensitive. Raises ``KeyError`` (not a silent
    ``None``) so a caller never charts off a typo'd vertical name.
    """
    norm = str(key).strip().lower()
    canonical = _ALIAS_INDEX.get(norm)
    if canonical is None:
        raise KeyError(f"no clinical vertical for {key!r}")
    return CLINICAL_VERTICALS_2026[canonical]


def list_verticals() -> List[ClinicalVertical]:
    """All 13 verticals, ordered by display name."""
    return sorted(CLINICAL_VERTICALS_2026.values(), key=lambda v: v.name)


def search_by_code(code: str) -> List[ClinicalVertical]:
    """Verticals that reference a given CPT / ICD-10 / HCPCS / DRG code.

    Matches on a normalized (upper-cased, trimmed) exact code OR an
    ICD-10 category prefix — so ``"H25.1"`` finds ophthalmology via its
    ``"H25"`` entry. Returns name-sorted; empty list if nothing matches.
    """
    q = str(code).strip().upper()
    if not q:
        return []
    hits: List[ClinicalVertical] = []
    for v in CLINICAL_VERTICALS_2026.values():
        for c in v.all_codes():
            if q == c or q.startswith(c + ".") or q.startswith(c):
                hits.append(v)
                break
    return sorted(hits, key=lambda v: v.name)


def verticals_with_asc_cpl_2026() -> List[ClinicalVertical]:
    """Verticals exposed to the 2026 ASC site-shift agenda, name-sorted."""
    return sorted(
        (v for v in CLINICAL_VERTICALS_2026.values() if v.asc_cpl_2026),
        key=lambda v: v.name,
    )


def volume_anchors() -> List[Stat]:
    """The high-volume epidemiology anchors across all verticals.

    Pulls every epidemiology ``Stat`` whose unit is a yearly count or a
    population/procedure count, sorted descending by central value — the
    'how big is each vertical' headline list the brief leads with. Stats
    without a numeric value are skipped.
    """
    anchors: List[Stat] = []
    for v in CLINICAL_VERTICALS_2026.values():
        for s in v.epidemiology:
            if s.value is None:
                continue
            u = s.unit.lower()
            if "/yr" in u or u in ("people", "cases", "procedures",
                                   "beneficiaries", "organizations", "men",
                                   "births/yr"):
                anchors.append(s)
    return sorted(anchors, key=lambda s: s.value or 0.0, reverse=True)


# The CY2026 conversion factors, re-exported for convenience so a chart
# can show the vertical reference and its dollar denominator together
# without a second import. Source of truth stays in fee_schedule_2026.
PFS_CF_NONQP_2026 = FEE_SCHEDULE_BACKBONE_2026["pfs_cf_nonqp"].value
OPPS_CF_2026 = FEE_SCHEDULE_BACKBONE_2026["opps_cf"].value
ASC_CF_2026 = FEE_SCHEDULE_BACKBONE_2026["asc_cf"].value


__all__ = [
    "Stat",
    "CodeSet",
    "VizSpec",
    "ClinicalVertical",
    "CLINICAL_VERTICALS_2026",
    "POLICY_DRIVERS_2026",
    "get_vertical",
    "list_verticals",
    "search_by_code",
    "verticals_with_asc_cpl_2026",
    "volume_anchors",
    "PFS_CF_NONQP_2026",
    "OPPS_CF_2026",
    "ASC_CF_2026",
]
