"""TAM / SAM / SOM builder — driver-tree market sizing for CDD.

Healthcare PE diligence sizes markets the way the user described for
fertility: a CHAIN of population/utilization drivers multiplied down to
revenue (total births → % via IVF → IVF deliveries → cycles per delivery
→ cycles → price per cycle), SEGMENTED (age bands with very different
utilization + success rates), funneled TAM → SAM → SOM, and PROJECTED
forward on named growth drivers (population growth, price inflation,
benefit expansion, access-barrier mitigation, supply increase,
utilization trend).

This module is the math + the bundled templates; the page renders it and
the exporters (CSV + formatted XLSX, both stdlib) ship it to the deal
team's model. Honesty rules apply: template values carry their source
labels and are explicitly illustrative defaults to be replaced with
engagement data — nothing renders as if it were the fund's own research.

Public API:
    DriverStep, Segment, GrowthDriver, TamSamModel
    fertility_ivf_template() -> TamSamModel
    blank_template() -> TamSamModel
    compute(model) -> dict   (funnel, segments, projection, audit trail)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DriverStep:
    """One link in the TAM driver chain.

    ``op`` is how this step combines with the running value:
      · "base"  — sets the starting population/value;
      · "rate"  — multiplies by a fraction (0–1), e.g. "% via IVF";
      · "mult"  — multiplies by a count, e.g. "cycles per delivery";
      · "price" — multiplies by a $ amount (the chain becomes revenue).
    """
    name: str
    value: float
    op: str = "rate"          # base | rate | mult | price
    unit: str = ""            # display unit, e.g. "births", "$/cycle"
    source: str = ""          # where the default came from — always shown


@dataclass
class Segment:
    """A demand segment (e.g. maternal age band) with its own utilization
    economics. ``share_of_volume`` fractions should sum to ~1.0 across
    segments; ``success_rate`` is segment-specific (e.g. live-birth rate
    per cycle by age band) and drives cycles-per-outcome differences."""
    name: str
    share_of_volume: float
    success_rate: Optional[float] = None
    note: str = ""


@dataclass
class GrowthDriver:
    """A named annual growth driver, composed multiplicatively in the
    projection. Keeping them separate (not one blended CAGR) is the point
    — the IC wants to see WHICH lever carries the growth."""
    name: str
    annual_pct: float          # +2.5 means +2.5%/yr
    note: str = ""


@dataclass
class TamSamModel:
    name: str
    chain: List[DriverStep] = field(default_factory=list)
    segments: List[Segment] = field(default_factory=list)
    growth_drivers: List[GrowthDriver] = field(default_factory=list)
    sam_share: float = 1.0     # fraction of TAM that is addressable
    sam_note: str = ""
    som_share: float = 0.0     # obtainable share of SAM (0 = not set)
    som_note: str = ""
    horizon_years: int = 5
    basis_note: str = ""


def fertility_ivf_template() -> TamSamModel:
    """The fertility/IVF sizing the user described, as a worked template.

    Defaults are public-data magnitudes (CDC births, CDC/SART ART data),
    labeled per-step. They are STARTING POINTS for an engagement, not the
    fund's research — the page says so and every number is editable.
    """
    return TamSamModel(
        name="Fertility · IVF clinic market",
        chain=[
            DriverStep("Total US births / yr", 3_660_000, op="base",
                       unit="births", source="CDC NVSS 2023"),
            DriverStep("% of births via IVF", 0.023, op="rate",
                       unit="of births", source="CDC ART surveillance"),
            DriverStep("Avg cycles per IVF delivery", 2.5, op="mult",
                       unit="cycles/delivery",
                       source="SART national summary (≈1/0.40 per-cycle "
                              "live-birth rate, all ages blended)"),
            DriverStep("Avg revenue per cycle", 20_000, op="price",
                       unit="$/cycle",
                       source="ASRM-cited cash-pay range $15–25K"),
        ],
        segments=[
            Segment("<35", 0.38, success_rate=0.51,
                    note="highest per-cycle live-birth rate"),
            Segment("35–37", 0.20, success_rate=0.38),
            Segment("38–40", 0.19, success_rate=0.25),
            Segment("41–42", 0.11, success_rate=0.12),
            Segment(">42", 0.12, success_rate=0.04,
                    note="most cycles per delivery — donor-egg heavy"),
        ],
        growth_drivers=[
            GrowthDriver("Utilization growth (IVF penetration)", 6.0,
                         "US penetration ~2.3% of births vs 5–10% in "
                         "Western Europe / Israel — the structural gap"),
            GrowthDriver("Price inflation", 3.0,
                         "cash-pay pricing has outrun CPI"),
            GrowthDriver("Benefit expansion", 2.0,
                         "state mandates + employer fertility benefits "
                         "(Carrot/Progyny-style) widen coverage"),
            GrowthDriver("Access-barrier mitigation", 1.5,
                         "clinic capacity, financing products, telehealth "
                         "intake reduce drop-off"),
            GrowthDriver("Population / demographic", -0.5,
                         "births declining slowly; delayed maternal age "
                         "partially offsets for IVF specifically"),
        ],
        sam_share=0.62,
        sam_note="Cash-pay + mandated/covered metros a platform can "
                 "credibly serve (excl. academic-center-locked volume)",
        som_share=0.08,
        som_note="Obtainable share for a multi-clinic platform at entry",
        horizon_years=5,
        basis_note="Template defaults from public CDC/SART/ASRM data — "
                   "replace with engagement data before IC use.",
    )


def dialysis_template() -> TamSamModel:
    """In-center dialysis sizing — second worked template so the builder
    reads as a general tool. Same rules: public-data magnitudes (USRDS/
    CMS), labeled, illustrative, every value editable."""
    return TamSamModel(
        name="Dialysis · in-center treatment market",
        chain=[
            DriverStep("US ESRD patients", 810_000, op="base",
                       unit="patients", source="USRDS annual data report"),
            DriverStep("% on dialysis (vs functioning transplant)", 0.69,
                       op="rate", unit="of ESRD", source="USRDS"),
            DriverStep("% in-center hemodialysis", 0.84, op="rate",
                       unit="of dialysis", source="USRDS modality mix"),
            DriverStep("Treatments per patient / yr", 156, op="mult",
                       unit="treatments/yr",
                       source="3×/week standard of care"),
            DriverStep("Avg revenue per treatment", 280, op="price",
                       unit="$/treatment",
                       source="CMS ESRD PPS base rate + commercial blend"),
        ],
        segments=[
            Segment("Commercial-insured", 0.10, success_rate=None,
                    note="~10% of patients, majority of clinic EBITDA — "
                         "the economics segment, not a volume segment"),
            Segment("Medicare / MA", 0.74, success_rate=None),
            Segment("Medicaid / other", 0.16, success_rate=None),
        ],
        growth_drivers=[
            GrowthDriver("ESRD incidence growth", 1.8,
                         "diabetes/hypertension-driven"),
            GrowthDriver("Rate updates (PPS + commercial)", 2.2,
                         "CMS annual PPS update + commercial escalators"),
            GrowthDriver("Home-modality shift", -1.5,
                         "CMS pushing home dialysis pulls volume from "
                         "in-center — a headwind, shown as one"),
        ],
        sam_share=0.55,
        sam_note="Metros where an independent platform can site clinics "
                 "(excl. the two-national-chain lock-ups)",
        som_share=0.05,
        som_note="Obtainable share for a regional platform at entry",
        horizon_years=5,
        basis_note="Template defaults from public USRDS/CMS data — "
                   "replace with engagement data before IC use.",
    )


def home_health_template() -> TamSamModel:
    """Medicare-certified home health sizing. Magnitudes anchor to MedPAC
    (~3.3M users, ~$16–18B Medicare HH spend) — illustrative defaults,
    every value editable."""
    return TamSamModel(
        name="Home health · Medicare-certified agency market",
        chain=[
            DriverStep("Medicare beneficiaries", 67_000_000, op="base",
                       unit="beneficiaries", source="CMS enrollment"),
            DriverStep("% using home health / yr", 0.05, op="rate",
                       unit="of beneficiaries",
                       source="MedPAC (~3.3M annual HH users)"),
            DriverStep("30-day periods per user / yr", 2.9, op="mult",
                       unit="periods/user", source="MedPAC PDGM data"),
            DriverStep("Avg revenue per 30-day period", 2_010, op="price",
                       unit="$/period",
                       source="CMS PDGM national standardized rate"),
        ],
        segments=[
            Segment("Post-acute (hospital-discharge)", 0.62, None,
                    note="referral-driven; hospital JV/alignment is the "
                         "moat"),
            Segment("Community-admitted", 0.38, None,
                    note="physician/community referrals — slower growth, "
                         "longer episodes"),
        ],
        growth_drivers=[
            GrowthDriver("Aging population (65+ growth)", 3.0,
                         "the demographic floor under demand"),
            GrowthDriver("Site-of-care shift to home", 4.0,
                         "payers + patients prefer home vs SNF; "
                         "hospital-at-home momentum"),
            GrowthDriver("PDGM / rate pressure", -1.5,
                         "CMS behavioral-adjustment clawbacks compress "
                         "rates — a headwind, shown as one"),
            GrowthDriver("Labor supply constraint", -1.0,
                         "nurse/aide wage inflation + capacity caps "
                         "realized volume"),
            GrowthDriver("MA penetration", -0.5,
                         "MA pays below FFS for HH; mix shift drags "
                         "blended rate"),
        ],
        sam_share=0.58,
        sam_note="States/metros a platform can credibly serve with "
                 "clinical staffing density",
        som_share=0.04,
        som_note="Obtainable share for a regional platform at entry",
        horizon_years=5,
        basis_note="Template defaults anchored to MedPAC/CMS public data "
                   "— replace with engagement data before IC use.",
    )



def hospice_template() -> TamSamModel:
    """Medicare hospice sizing — anchors to MedPAC (~1.7M users, ~$25B
    spend). Level-of-care segments; integrity scrutiny carried as a
    headwind."""
    return TamSamModel(
        name="Hospice · Medicare benefit market",
        chain=[
            DriverStep("Medicare hospice users / yr", 1_720_000, op="base",
                       unit="patients", source="MedPAC hospice chapter"),
            DriverStep("Avg covered days per user", 80, op="mult",
                       unit="days/user",
                       source="MedPAC (median LOS ~18d, mean pulled up "
                              "by long-stay tail)"),
            DriverStep("Avg revenue per day (blended)", 185, op="price",
                       unit="$/day",
                       source="CMS RHC $218 d1-60 / $172 d61+ + GIP mix"),
        ],
        segments=[
            Segment("Routine home care", 0.97, None,
                    note="~97% of days — the economics ARE RHC"),
            Segment("General inpatient (GIP)", 0.015, None,
                    note="highest rate, heaviest scrutiny"),
            Segment("Continuous home care", 0.010, None),
            Segment("Respite", 0.005, None),
        ],
        growth_drivers=[
            GrowthDriver("Deaths / demographic growth", 2.0,
                         "boomer mortality curve — the demand floor"),
            GrowthDriver("Penetration of decedents", 1.5,
                         "hospice use still rising as share of Medicare "
                         "decedents"),
            GrowthDriver("Rate updates", 2.5,
                         "CMS annual hospice payment update"),
            GrowthDriver("Length-of-stay mix", 1.0,
                         "dementia/non-cancer admissions extend stays"),
            GrowthDriver("Program-integrity scrutiny", -1.5,
                         "OIG/CMS crackdown on long-stay + the CA "
                         "license glut — a headwind, shown as one"),
            GrowthDriver("Labor supply", -0.5,
                         "nurse/aide wage inflation caps census"),
        ],
        sam_share=0.60,
        sam_note="Metros a platform can staff; excludes hospital-system-"
                 "captive programs",
        som_share=0.05,
        som_note="Obtainable share for a regional platform at entry",
        horizon_years=5,
        basis_note="Template defaults anchored to MedPAC/CMS public data "
                   "— replace with engagement data before IC use.",
    )



def snf_template() -> TamSamModel:
    """Skilled nursing facility sizing. The base driver is the REAL
    certified-bed count from the vendored CMS file; occupancy and the
    blended per-diem anchor to NIC/MedPAC magnitudes (~$130–140B
    industry revenue)."""
    return TamSamModel(
        name="SNF · skilled nursing facility market",
        chain=[
            DriverStep("Certified SNF beds", 1_569_000, op="base",
                       unit="beds",
                       source="CMS Nursing Home Care Compare (vendored "
                              "snapshot — actual certified-bed count)"),
            DriverStep("Average occupancy", 0.77, op="rate",
                       unit="of beds", source="NIC MAP / CMS census"),
            DriverStep("Patient days per occupied bed / yr", 365,
                       op="mult", unit="days/yr", source="calendar"),
            DriverStep("Blended revenue per patient day", 300, op="price",
                       unit="$/day",
                       source="Medicaid ~$250 / Medicare PDPM ~$600 / "
                              "private blend (MedPAC, AHCA)"),
        ],
        segments=[
            Segment("Medicaid (long-stay)", 0.62, None,
                    note="the volume payer — lowest rate, custodial "
                         "census"),
            Segment("Medicare FFS + MA (short-stay)", 0.21, None,
                    note="the margin payer — PDPM rehab stays fund the "
                         "house"),
            Segment("Private / other", 0.17, None),
        ],
        growth_drivers=[
            GrowthDriver("Demographics (80+ growth)", 3.0,
                         "the boomer 80+ wave hits 2026–2035"),
            GrowthDriver("Medicaid rate updates", 2.0,
                         "state budget-driven; lags cost inflation"),
            GrowthDriver("Occupancy recovery", 1.5,
                         "census still rebuilding toward pre-2020 "
                         "levels"),
            GrowthDriver("Staffing mandate / labor", -2.0,
                         "federal minimum-staffing rule + agency wage "
                         "inflation — the sector's defining headwind"),
            GrowthDriver("Site-of-care shift to home", -1.5,
                         "HH/hospital-at-home pulls the short-stay "
                         "rehab census"),
            GrowthDriver("MA penetration", -1.0,
                         "MA pays below FFS and shortens stays"),
        ],
        sam_share=0.55,
        sam_note="States/metros a platform can staff and license; "
                 "excludes hospital-based + government facilities",
        som_share=0.03,
        som_note="Obtainable share for a regional platform at entry",
        horizon_years=5,
        basis_note="Template defaults from CMS/NIC/MedPAC public data — "
                   "replace with engagement data before IC use.",
    )



def irf_template() -> TamSamModel:
    """Inpatient rehab facility sizing — anchors to MedPAC (~370K cases,
    ~$8B Medicare spend). The 60% rule + MA steering carried as
    constraints."""
    return TamSamModel(
        name="IRF · inpatient rehabilitation market",
        chain=[
            DriverStep("Medicare IRF discharges / yr", 370_000, op="base",
                       unit="cases", source="MedPAC IRF chapter"),
            DriverStep("Avg payment per discharge", 22_000, op="price",
                       unit="$/case",
                       source="MedPAC (CMG case-mix weighted)"),
        ],
        segments=[
            Segment("Ortho / fracture", 0.25, None),
            Segment("Stroke", 0.20, None,
                    note="the 60%-rule anchor condition"),
            Segment("Neurological", 0.15, None),
            Segment("Brain injury", 0.10, None),
            Segment("Debility / other", 0.30, None,
                    note="the compliance-watch bucket"),
        ],
        growth_drivers=[
            GrowthDriver("Demographics (65+ growth)", 3.0,
                         "stroke + fracture incidence scale with age"),
            GrowthDriver("Acuity shift from SNF", 1.5,
                         "higher-acuity rehab migrating to IRF level"),
            GrowthDriver("Rate updates", 2.5,
                         "CMS annual IRF PPS update"),
            GrowthDriver("MA penetration / steering", -1.5,
                         "MA plans steer rehab to SNF — a headwind"),
            GrowthDriver("60% rule constraint", -0.5,
                         "compliance threshold caps case-mix expansion"),
        ],
        sam_share=0.60,
        sam_note="Freestanding + JV-able units; excludes academic-"
                 "captive units",
        som_share=0.06,
        som_note="Obtainable share for a platform at entry",
        horizon_years=5,
        basis_note="Template defaults anchored to MedPAC/CMS public data "
                   "— replace with engagement data before IC use.",
    )


def ltch_template() -> TamSamModel:
    """Long-term care hospital sizing — a STRUCTURALLY SHRINKING market
    (dual-rate site-neutral criteria), and the build says so: the
    composite growth is negative. The tool sizes honest declines too."""
    return TamSamModel(
        name="LTCH · long-term care hospital market",
        chain=[
            DriverStep("LTCH cases / yr", 78_000, op="base",
                       unit="cases", source="MedPAC LTCH chapter"),
            DriverStep("Avg payment per case", 45_000, op="price",
                       unit="$/case",
                       source="MedPAC (standard-rate cases ~$47K)"),
        ],
        segments=[
            Segment("Ventilator / pulmonary", 0.45, None,
                    note="the criteria-compliant core"),
            Segment("Wound / complex medical", 0.35, None),
            Segment("Other (site-neutral exposed)", 0.20, None,
                    note="paid at the lower site-neutral rate"),
        ],
        growth_drivers=[
            GrowthDriver("Site-neutral criteria attrition", -3.0,
                         "dual-rate payment shrinks the addressable "
                         "case base — the defining structural decline"),
            GrowthDriver("Demographics / acuity", 2.0,
                         "vent-dependent census grows with age + ICU "
                         "survival"),
            GrowthDriver("Rate updates", 2.0,
                         "CMS annual LTCH PPS update (standard rate)"),
            GrowthDriver("Capacity closures", -1.5,
                         "supply exiting — closures concentrate volume "
                         "but shrink the market"),
        ],
        sam_share=0.50,
        sam_note="Markets with referral ICU density; excludes hospital-"
                 "within-hospital captives",
        som_share=0.08,
        som_note="Consolidation share in a shrinking market",
        horizon_years=5,
        basis_note="Template defaults anchored to MedPAC/CMS public data "
                   "— replace with engagement data before IC use. NOTE: "
                   "composite growth is NEGATIVE by design.",
    )



def behavioral_health_template() -> TamSamModel:
    """Behavioral health sizing — the largest PE services vertical not
    tied to a CMS facility file. SAMHSA-anchored demand chain."""
    return TamSamModel(
        name="Behavioral health · treatment services market",
        chain=[
            DriverStep("US adults with any mental illness", 59_000_000,
                       op="base", unit="adults",
                       source="SAMHSA NSDUH annual report"),
            DriverStep("% receiving treatment / yr", 0.50, op="rate",
                       unit="of those with AMI", source="SAMHSA NSDUH"),
            DriverStep("Avg annual spend per treated patient", 3_000,
                       op="price", unit="$/patient/yr",
                       source="blended OP therapy / SUD / residential "
                              "(SAMHSA spending estimates)"),
        ],
        segments=[
            Segment("Outpatient therapy / psychiatry", 0.40, None,
                    note="the volume segment; telehealth-accelerated"),
            Segment("SUD treatment", 0.25, None,
                    note="opioid-epidemic-driven; parity-funded"),
            Segment("Residential / PHP / IOP", 0.15, None,
                    note="highest revenue per patient; payer scrutiny"),
            Segment("Autism / IDD services", 0.12, None,
                    note="the fastest-growing sub-vertical (ABA)"),
            Segment("Psychiatric inpatient", 0.08, None),
        ],
        growth_drivers=[
            GrowthDriver("Demand / destigmatization", 2.5,
                         "diagnosed prevalence + care-seeking still "
                         "rising post-2020"),
            GrowthDriver("Telehealth access expansion", 3.0,
                         "virtual BH removed the geography constraint — "
                         "the access-barrier mitigation lever"),
            GrowthDriver("Parity enforcement", 2.0,
                         "MHPAEA enforcement narrows the BH/medical "
                         "reimbursement gap"),
            GrowthDriver("Reimbursement gains", 2.0,
                         "commercial + Medicaid BH rate catch-up"),
            GrowthDriver("Clinician workforce shortage", -2.0,
                         "therapist/psychiatrist supply caps realized "
                         "volume — the binding constraint"),
        ],
        sam_share=0.55,
        sam_note="Commercially-insured + Medicaid-managed segments a "
                 "platform can credential into",
        som_share=0.03,
        som_note="Obtainable share — a fragmented market with no "
                 "national leader above ~2%",
        horizon_years=5,
        basis_note="Template defaults from SAMHSA public data — replace "
                   "with engagement data before IC use.",
    )


def asc_template() -> TamSamModel:
    """Ambulatory surgery center sizing — the site-of-care shift
    tailwind made into a chain. CMS/MedPAC + ASCA magnitudes."""
    return TamSamModel(
        name="ASC · ambulatory surgery center market",
        chain=[
            DriverStep("Medicare-certified ASCs", 6_300, op="base",
                       unit="centers", source="CMS / ASCA"),
            DriverStep("Cases per center / yr", 3_650, op="mult",
                       unit="cases/yr",
                       source="ASCA benchmarking (~14/working day)"),
            DriverStep("Avg revenue per case", 2_000, op="price",
                       unit="$/case",
                       source="Medicare ASC fee schedule + commercial "
                              "blend (MedPAC)"),
        ],
        segments=[
            Segment("GI / endoscopy", 0.25, None),
            Segment("Ophthalmology", 0.20, None,
                    note="cataract — the original ASC franchise"),
            Segment("Ortho / MSK", 0.20, None,
                    note="the fastest-growing slice: total joints "
                         "migrating off the HOPD list"),
            Segment("Pain management", 0.15, None),
            Segment("Other (ENT, uro, plastics)", 0.20, None),
        ],
        growth_drivers=[
            GrowthDriver("Site-of-care shift from HOPD", 4.0,
                         "payers push procedures to the cheaper "
                         "setting — the defining structural tailwind"),
            GrowthDriver("CMS covered-procedures expansion", 2.0,
                         "total joints, cardiac added to the ASC list"),
            GrowthDriver("Physician alignment / recruitment", 1.5,
                         "surgeon equity models pull volume"),
            GrowthDriver("Anesthesia / staffing cost", -1.0,
                         "anesthesia coverage inflation compresses "
                         "case economics"),
        ],
        sam_share=0.65,
        sam_note="Multi-specialty + single-specialty centers in CON-"
                 "clear states a platform can partner into",
        som_share=0.05,
        som_note="Obtainable share at entry",
        horizon_years=5,
        basis_note="Template defaults from CMS/MedPAC/ASCA public data — "
                   "replace with engagement data before IC use.",
    )



def physician_group_template() -> TamSamModel:
    """Physician practice management sizing — AMA/MGMA-anchored."""
    return TamSamModel(
        name="Physician groups · practice management market",
        chain=[
            DriverStep("Active US physicians (office-based)", 580_000,
                       op="base", unit="physicians",
                       source="AMA Masterfile (office-based share)"),
            DriverStep("% in independent / acquirable practices", 0.42,
                       op="rate", unit="of office-based",
                       source="AMA PRP (independent practice share, "
                              "declining ~2pp/yr)"),
            DriverStep("Avg practice revenue per physician", 750_000,
                       op="price", unit="$/physician/yr",
                       source="MGMA DataDive medians (multi-specialty "
                              "blend)"),
        ],
        segments=[
            Segment("Primary care", 0.32, None,
                    note="VBC/MA-enablement thesis territory"),
            Segment("Ortho / MSK", 0.14, None,
                    note="ancillary-rich: ASC + imaging + PT"),
            Segment("Cardiology", 0.12, None,
                    note="the 2021+ consolidation wave"),
            Segment("GI", 0.10, None),
            Segment("Dermatology", 0.10, None,
                    note="the first PPM wave — now mature"),
            Segment("Other specialties", 0.22, None),
        ],
        growth_drivers=[
            GrowthDriver("Utilization / demographics", 2.5,
                         "visit volume scales with 65+ growth"),
            GrowthDriver("Ancillary capture", 2.0,
                         "in-practice ASC/imaging/infusion revenue"),
            GrowthDriver("Value-based contracts", 1.5,
                         "MA risk deals add PMPM streams"),
            GrowthDriver("Fee-schedule pressure", -1.5,
                         "Medicare PFS conversion-factor cuts"),
            GrowthDriver("Independent-pool shrinkage", -2.0,
                         "hospital + payer employment drains the "
                         "acquirable pool — the clock on the thesis"),
        ],
        sam_share=0.45,
        sam_note="Specialties + geographies where the PPM model has "
                 "proven economics",
        som_share=0.02,
        som_note="A large platform holds <2% of a deeply fragmented "
                 "market",
        horizon_years=5,
        basis_note="Template defaults from AMA/MGMA public data — "
                   "replace with engagement data before IC use.",
    )


def dental_template() -> TamSamModel:
    """DSO market sizing — ADA HPI-anchored."""
    return TamSamModel(
        name="Dental · DSO-addressable market",
        chain=[
            DriverStep("US dental spend / yr", 165_000_000_000, op="base",
                       unit="$", source="CMS NHE dental services line"),
            DriverStep("% delivered by practices (vs other settings)",
                       0.95, op="rate", unit="of spend",
                       source="ADA Health Policy Institute"),
        ],
        segments=[
            Segment("General dentistry", 0.62, None),
            Segment("Ortho / aligners", 0.12, None,
                    note="consumer-demand cyclical"),
            Segment("Oral surgery / implants", 0.12, None,
                    note="highest-margin specialty"),
            Segment("Pediatric", 0.08, None,
                    note="Medicaid-funded; rate-sensitive"),
            Segment("Endo / perio / other", 0.06, None),
        ],
        growth_drivers=[
            GrowthDriver("Price / fee growth", 3.0,
                         "dental fees track above CPI (ADA HPI)"),
            GrowthDriver("Utilization recovery", 1.0,
                         "adult visit rates still below pre-2020"),
            GrowthDriver("DSO penetration", 2.0,
                         "DSO share of dentists ~13% and climbing — "
                         "the consolidation runway"),
            GrowthDriver("Insurance mix pressure", -1.0,
                         "dental benefit caps flat for decades in "
                         "nominal terms"),
        ],
        sam_share=0.50,
        sam_note="The DSO-consolidatable practice universe (excl. "
                 "rural solo + hospital-based)",
        som_share=0.03,
        som_note="Largest DSO holds ~3% — the fragmentation persists",
        horizon_years=5,
        basis_note="Template defaults from CMS NHE / ADA HPI public "
                   "data — replace with engagement data before IC use.",
    )


def oncology_template() -> TamSamModel:
    """Community oncology sizing — ASCO/MedPAC-anchored."""
    return TamSamModel(
        name="Oncology · community practice market",
        chain=[
            DriverStep("New US cancer cases / yr", 2_000_000, op="base",
                       unit="cases", source="ACS Cancer Facts & Figures"),
            DriverStep("% treated in community setting", 0.55, op="rate",
                       unit="of cases",
                       source="ASCO practice census (vs hospital/"
                              "academic)"),
            DriverStep("Avg first-year treatment revenue", 150_000,
                       op="price", unit="$/case",
                       source="MedPAC oncology spend per beneficiary "
                              "(drug + services blend)"),
        ],
        segments=[
            Segment("Medical oncology (drug spend)", 0.65, None,
                    note="buy-and-bill economics — the margin engine"),
            Segment("Radiation oncology", 0.18, None,
                    note="capital-intensive; hypofractionation headwind"),
            Segment("Surgical / other", 0.17, None),
        ],
        growth_drivers=[
            GrowthDriver("Incidence / demographics", 2.5,
                         "cases scale with the 65+ wave"),
            GrowthDriver("Drug price inflation", 4.0,
                         "novel-agent launch prices — the dominant "
                         "driver"),
            GrowthDriver("Site-of-care shift to community", 1.5,
                         "payers steer infusion out of HOPD"),
            GrowthDriver("IRA drug-price negotiation", -1.5,
                         "Medicare negotiation compresses buy-and-bill "
                         "spread — a structural headwind from 2026"),
            GrowthDriver("340B competition", -1.0,
                         "hospital 340B economics pull volume"),
        ],
        sam_share=0.55,
        sam_note="Community practices a platform can affiliate "
                 "(excl. academic-captive)",
        som_share=0.04,
        som_note="Obtainable share at entry",
        horizon_years=5,
        basis_note="Template defaults from ACS/ASCO/MedPAC public data "
                   "— replace with engagement data before IC use.",
    )


def urgent_care_template() -> TamSamModel:
    """Urgent care sizing — UCA-anchored."""
    return TamSamModel(
        name="Urgent care · clinic market",
        chain=[
            DriverStep("US urgent care centers", 14_000, op="base",
                       unit="centers",
                       source="Urgent Care Association census"),
            DriverStep("Visits per center / yr", 14_600, op="mult",
                       unit="visits/yr", source="UCA (~40/day average)"),
            DriverStep("Avg revenue per visit", 165, op="price",
                       unit="$/visit",
                       source="UCA benchmarking (payer blend)"),
        ],
        segments=[
            Segment("Commercial-insured", 0.55, None,
                    note="the economics segment"),
            Segment("Medicare / MA", 0.20, None),
            Segment("Medicaid", 0.15, None),
            Segment("Self-pay / occ-health", 0.10, None),
        ],
        growth_drivers=[
            GrowthDriver("ED-avoidance steerage", 3.0,
                         "payers + consumers substitute $165 visits "
                         "for $2,000 ED visits"),
            GrowthDriver("Unit growth / de-novo", 2.5,
                         "center count still compounding"),
            GrowthDriver("Retail / telehealth competition", -1.5,
                         "CVS/Amazon/virtual primary care skim the "
                         "low-acuity tail"),
            GrowthDriver("Staffing cost", -1.0,
                         "provider coverage inflation"),
        ],
        sam_share=0.60,
        sam_note="Metro + suburban catchments a platform can brand-"
                 "build in",
        som_share=0.05,
        som_note="Obtainable share at entry",
        horizon_years=5,
        basis_note="Template defaults from UCA public census data — "
                   "replace with engagement data before IC use.",
    )



def hospitals_template() -> TamSamModel:
    """Hospital sector sizing — the flagship vertical, anchored to CMS
    NHE ($1.4T hospital care). The deep dive underneath is computed from
    the vendored HCRIS universe (6.1K filers, real NPR)."""
    return TamSamModel(
        name="Hospitals · acute-care market",
        chain=[
            DriverStep("US hospital care spend / yr",
                       1_400_000_000_000, op="base", unit="$",
                       source="CMS National Health Expenditure (hospital "
                              "care line)"),
            DriverStep("% community / investor-relevant",
                       0.62, op="rate", unit="of spend",
                       source="AHA Hospital Statistics (community "
                              "hospital share excl. federal/psych/LTC)"),
        ],
        segments=[
            Segment("Large systems (>$1B NPR)", 0.55, None,
                    note="consolidation acquirers, not targets"),
            Segment("Mid-size independents ($250M\u2013$1B)", 0.25, None,
                    note="the PE/JV-able middle \u2014 the thesis segment"),
            Segment("Small / rural / CAH", 0.20, None,
                    note="distress-driven deal flow; regulatory "
                         "protections complicate ownership"),
        ],
        growth_drivers=[
            GrowthDriver("Price / rate growth", 4.0,
                         "commercial rate escalators + Medicare updates"),
            GrowthDriver("Utilization / demographics", 1.5,
                         "inpatient flat; outpatient carries growth"),
            GrowthDriver("Outpatient shift (within systems)", 1.0,
                         "HOPD + ASC capture keeps revenue in-system"),
            GrowthDriver("Site-neutral payment risk", -1.0,
                         "HOPD rate parity proposals \u2014 the policy "
                         "headwind"),
            GrowthDriver("Labor cost normalization", -0.5,
                         "contract-labor unwind helps margins, not "
                         "revenue"),
        ],
        sam_share=0.25,
        sam_note="The mid-size independent + distressed segments where "
                 "outside capital can actually transact",
        som_share=0.02,
        som_note="Hospital deals are episodic; share builds slowly",
        horizon_years=5,
        basis_note="Template defaults from CMS NHE / AHA public data \u2014 "
                   "replace with engagement data before IC use. The "
                   "state footprint below is computed from the real "
                   "HCRIS universe.",
    )


def blank_template() -> TamSamModel:
    """Empty scaffold with one of each block so the form renders."""
    return TamSamModel(
        name="Custom market",
        chain=[
            DriverStep("Addressable population", 1_000_000, op="base",
                       unit="people", source=""),
            DriverStep("Utilization rate", 0.05, op="rate",
                       unit="of population", source=""),
            DriverStep("Avg revenue per user / yr", 1_000, op="price",
                       unit="$/yr", source=""),
        ],
        segments=[],
        growth_drivers=[
            GrowthDriver("Population growth", 0.5),
            GrowthDriver("Price inflation", 3.0),
            GrowthDriver("Utilization trend", 2.0),
        ],
        sam_share=0.5,
        som_share=0.05,
        horizon_years=5,
    )


TEMPLATES = {
    "fertility_ivf": fertility_ivf_template,
    "dialysis": dialysis_template,
    "home_health": home_health_template,
    "hospice": hospice_template,
    "snf": snf_template,
    "irf": irf_template,
    "ltch": ltch_template,
    "behavioral_health": behavioral_health_template,
    "asc": asc_template,
    "physician_group": physician_group_template,
    "dental": dental_template,
    "oncology": oncology_template,
    "urgent_care": urgent_care_template,
    "hospitals": hospitals_template,
    "blank": blank_template,
}


def compute(model: TamSamModel) -> Dict[str, Any]:
    """Run the driver chain → funnel → segments → projection.

    Returns an audit-friendly dict: every chain step carries its running
    value so the page (and the export) can show the partner exactly how
    the TAM was built — the chain IS the methodology.
    """
    running = 0.0
    steps: List[Dict[str, Any]] = []
    for i, st in enumerate(model.chain):
        if i == 0 or st.op == "base":
            running = st.value
        elif st.op in ("rate", "mult", "price"):
            running = running * st.value
        steps.append({
            "name": st.name, "value": st.value, "op": st.op,
            "unit": st.unit, "source": st.source,
            "running": running,
        })
    tam = running
    sam = tam * max(0.0, min(1.0, model.sam_share))
    som = sam * max(0.0, min(1.0, model.som_share))

    seg_rows: List[Dict[str, Any]] = []
    for s in model.segments:
        seg_rows.append({
            "name": s.name,
            "share_of_volume": s.share_of_volume,
            "tam_value": tam * s.share_of_volume,
            "success_rate": s.success_rate,
            "note": s.note,
        })

    # Composite growth: drivers multiply (1+g1)(1+g2)… per year — and the
    # decomposition is preserved so the IC sees which lever carries it.
    composite = 1.0
    for g in model.growth_drivers:
        composite *= (1.0 + g.annual_pct / 100.0)
    cagr_pct = (composite - 1.0) * 100.0
    projection: List[Dict[str, Any]] = []
    for yr in range(model.horizon_years + 1):
        factor = composite ** yr
        projection.append({
            "year": yr,
            "tam": tam * factor,
            "sam": sam * factor,
            "som": som * factor,
        })

    return {
        "name": model.name,
        "steps": steps,
        "tam": tam, "sam": sam, "som": som,
        "sam_share": model.sam_share, "som_share": model.som_share,
        "sam_note": model.sam_note, "som_note": model.som_note,
        "segments": seg_rows,
        "growth_drivers": [
            {"name": g.name, "annual_pct": g.annual_pct, "note": g.note}
            for g in model.growth_drivers
        ],
        "composite_cagr_pct": cagr_pct,
        "projection": projection,
        "horizon_years": model.horizon_years,
        "basis_note": model.basis_note,
    }


def sensitivity(model: TamSamModel, *, swing: float = 0.20) -> List[Dict[str, Any]]:
    """Tornado data: TAM impact of swinging each chain driver ±swing
    (rates clamped to [0,1]). Sorted by absolute impact — the classic
    IC sensitivity read: which assumption moves the answer."""
    base = compute(model)["tam"]
    out: List[Dict[str, Any]] = []
    for i, st in enumerate(model.chain):
        lo_m = TamSamModel(name=model.name,
                           chain=[DriverStep(s.name, s.value, op=s.op)
                                  for s in model.chain],
                           sam_share=model.sam_share,
                           som_share=model.som_share)
        hi_m = TamSamModel(name=model.name,
                           chain=[DriverStep(s.name, s.value, op=s.op)
                                  for s in model.chain],
                           sam_share=model.sam_share,
                           som_share=model.som_share)
        lo_v = st.value * (1 - swing)
        hi_v = st.value * (1 + swing)
        if st.op == "rate":
            lo_v = max(0.0, min(1.0, lo_v))
            hi_v = max(0.0, min(1.0, hi_v))
        lo_m.chain[i].value = lo_v
        hi_m.chain[i].value = hi_v
        tam_lo = compute(lo_m)["tam"]
        tam_hi = compute(hi_m)["tam"]
        out.append({
            "name": st.name,
            "tam_low": tam_lo,
            "tam_high": tam_hi,
            "impact": abs(tam_hi - tam_lo),
        })
    out.sort(key=lambda r: -r["impact"])
    return out
