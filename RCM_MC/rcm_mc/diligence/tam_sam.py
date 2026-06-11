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
    per cycle by age band); ``growth_pct`` is the segment's OWN annual
    growth — the within-industry divergence map ("where it's growing
    fastest"). None = grows with the composite."""
    name: str
    share_of_volume: float
    success_rate: Optional[float] = None
    note: str = ""
    growth_pct: Optional[float] = None


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
                    note="the volume segment; telehealth-accelerated",
                    growth_pct=8.0),
            Segment("SUD treatment", 0.25, None,
                    note="opioid-epidemic-driven; parity-funded",
                    growth_pct=6.0),
            Segment("Residential / PHP / IOP", 0.15, None,
                    note="highest revenue per patient; payer scrutiny",
                    growth_pct=4.0),
            Segment("Autism / IDD services", 0.12, None,
                    note="the fastest-growing sub-vertical (ABA)",
                    growth_pct=10.0),
            Segment("Psychiatric inpatient", 0.08, None,
                    growth_pct=1.0),
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
            Segment("GI / endoscopy", 0.25, None, growth_pct=4.0),
            Segment("Ophthalmology", 0.20, None,
                    note="cataract — the original ASC franchise",
                    growth_pct=3.0),
            Segment("Ortho / MSK", 0.20, None,
                    note="the fastest-growing slice: total joints "
                         "migrating off the HOPD list",
                    growth_pct=11.0),
            Segment("Pain management", 0.15, None, growth_pct=5.0),
            Segment("Other (ENT, uro, plastics)", 0.20, None,
                    growth_pct=4.0),
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
                    note="VBC/MA-enablement thesis territory",
                    growth_pct=5.0),
            Segment("Ortho / MSK", 0.14, None,
                    note="ancillary-rich: ASC + imaging + PT",
                    growth_pct=6.0),
            Segment("Cardiology", 0.12, None,
                    note="the 2021+ consolidation wave",
                    growth_pct=8.0),
            Segment("GI", 0.10, None, growth_pct=4.0),
            Segment("Dermatology", 0.10, None,
                    note="the first PPM wave — now mature",
                    growth_pct=2.0),
            Segment("Other specialties", 0.22, None, growth_pct=3.0),
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
            Segment("General dentistry", 0.62, None, growth_pct=4.0),
            Segment("Ortho / aligners", 0.12, None,
                    note="consumer-demand cyclical", growth_pct=3.0),
            Segment("Oral surgery / implants", 0.12, None,
                    note="highest-margin specialty", growth_pct=8.0),
            Segment("Pediatric", 0.08, None,
                    note="Medicaid-funded; rate-sensitive",
                    growth_pct=2.0),
            Segment("Endo / perio / other", 0.06, None,
                    growth_pct=4.0),
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
                    note="buy-and-bill economics — the margin engine",
                    growth_pct=7.0),
            Segment("Radiation oncology", 0.18, None,
                    note="capital-intensive; hypofractionation headwind",
                    growth_pct=1.0),
            Segment("Surgical / other", 0.17, None, growth_pct=3.0),
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
                    note="consolidation acquirers, not targets",
                    growth_pct=6.0),
            Segment("Mid-size independents ($250M\u2013$1B)", 0.25, None,
                    note="the PE/JV-able middle \u2014 the thesis segment",
                    growth_pct=3.0),
            Segment("Small / rural / CAH", 0.20, None,
                    note="distress-driven deal flow; regulatory "
                         "protections complicate ownership",
                    growth_pct=-1.0),
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



def infusion_template() -> TamSamModel:
    """Ambulatory + home infusion sizing — NHIA/MedPAC-anchored. The
    site-of-care shift OUT of HOPD is the defining tailwind."""
    return TamSamModel(
        name="Infusion · ambulatory + home infusion market",
        chain=[
            DriverStep("US patients on infused therapies / yr",
                       3_200_000, op="base", unit="patients",
                       source="NHIA industry report (home + suite)"),
            DriverStep("Avg infusions per patient / yr", 18, op="mult",
                       unit="infusions/yr",
                       source="NHIA (biologics q2-8wk blend + "
                              "antibiotics dailies)"),
            DriverStep("Avg revenue per infusion (drug + admin)",
                       650, op="price", unit="$/infusion",
                       source="ASP+6 / AWP-blend across payer mix "
                              "(MedPAC Part B drug chapter)"),
        ],
        segments=[
            Segment("Specialty biologics (immunology)", 0.40, None,
                    note="the margin engine — IVIG, anti-TNF, biologic "
                         "infusions", growth_pct=9.0),
            Segment("Oncology support / chemo", 0.25, None,
                    growth_pct=4.0),
            Segment("Anti-infectives (OPAT)", 0.20, None,
                    note="hospital-discharge driven", growth_pct=5.0),
            Segment("Nutrition / other (TPN)", 0.15, None,
                    growth_pct=3.0),
        ],
        growth_drivers=[
            GrowthDriver("Site-of-care shift from HOPD", 5.0,
                         "payers mandate suite/home over 2–3× HOPD "
                         "pricing — the structural tailwind"),
            GrowthDriver("Biologics pipeline / approvals", 4.0,
                         "new infused/injected agents expand the "
                         "treated population"),
            GrowthDriver("Demographics", 1.5,
                         "autoimmune + oncology prevalence with age"),
            GrowthDriver("Biosimilar price deflation", -2.5,
                         "biosimilar adoption compresses drug revenue "
                         "per infusion — a headwind, shown as one"),
            GrowthDriver("Nursing capacity", -1.0,
                         "infusion-nurse supply caps chair utilization"),
        ],
        sam_share=0.55,
        sam_note="Payer-steered + physician-referred volume an "
                 "independent platform can capture (excl. health-system "
                 "captive suites)",
        som_share=0.04,
        som_note="Obtainable share at entry — Option Care holds ~20% of "
                 "home infusion; the suite market is fragmented",
        horizon_years=5,
        basis_note="Template defaults from NHIA/MedPAC public data — "
                   "replace with engagement data before IC use.",
    )


def imaging_template() -> TamSamModel:
    """Outpatient imaging center sizing — IMV/MedPAC-anchored."""
    return TamSamModel(
        name="Imaging · outpatient center market",
        chain=[
            DriverStep("Freestanding imaging centers", 7_000, op="base",
                       unit="centers", source="IMV census / AHRA"),
            DriverStep("Scans per center / yr", 21_000, op="mult",
                       unit="scans/yr",
                       source="IMV benchmarking (modality-blended)"),
            DriverStep("Avg revenue per scan", 280, op="price",
                       unit="$/scan",
                       source="Medicare PFS technical+professional "
                              "blend × commercial mix (MedPAC)"),
        ],
        segments=[
            Segment("MRI", 0.30, None,
                    note="highest revenue per scan", growth_pct=4.0),
            Segment("CT", 0.22, None, growth_pct=5.0),
            Segment("Ultrasound / X-ray", 0.28, None, growth_pct=2.0),
            Segment("PET / nuclear", 0.10, None,
                    note="the fastest-growing modality — oncology + "
                         "neuro (amyloid) tracers", growth_pct=9.0),
            Segment("Mammography / other", 0.10, None, growth_pct=3.0),
        ],
        growth_drivers=[
            GrowthDriver("Site-of-care shift from HOPD", 4.0,
                         "payer steerage to freestanding at ~half the "
                         "HOPD rate"),
            GrowthDriver("Utilization / demographics", 2.5,
                         "imaging intensity rises with age + new "
                         "indications"),
            GrowthDriver("Advanced-modality mix shift", 1.5,
                         "MRI/CT/PET replacing plain film lifts "
                         "revenue per scan"),
            GrowthDriver("Reimbursement pressure", -2.0,
                         "Medicare PFS technical-component cuts — the "
                         "chronic headwind"),
            GrowthDriver("Radiologist shortage", -1.0,
                         "read capacity constrains volume growth"),
        ],
        sam_share=0.60,
        sam_note="Freestanding + JV-able centers in CON-clear metros",
        som_share=0.05,
        som_note="RadNet, the largest platform, holds ~9% of "
                 "freestanding — fragmentation persists",
        horizon_years=5,
        basis_note="Template defaults from IMV/MedPAC public data — "
                   "replace with engagement data before IC use.",
    )


def physical_therapy_template() -> TamSamModel:
    """Outpatient PT sizing — APTA/CMS-anchored."""
    return TamSamModel(
        name="Physical therapy · outpatient clinic market",
        chain=[
            DriverStep("US outpatient PT clinics", 38_000, op="base",
                       unit="clinics", source="APTA / IBISWorld census"),
            DriverStep("Visits per clinic / yr", 8_300, op="mult",
                       unit="visits/yr",
                       source="APTA benchmarking (~32/working day)"),
            DriverStep("Avg revenue per visit", 105, op="price",
                       unit="$/visit",
                       source="Medicare PFS therapy codes × commercial "
                              "blend (APTA fee surveys)"),
        ],
        segments=[
            Segment("Ortho / post-surgical", 0.45, None,
                    note="the referral engine — joint replacement "
                         "volume feeds PT", growth_pct=5.0),
            Segment("Sports / active", 0.20, None, growth_pct=4.0),
            Segment("Workers' comp / auto", 0.15, None,
                    note="highest rates, slowest payers",
                    growth_pct=2.0),
            Segment("Neuro / vestibular / geriatric", 0.12, None,
                    growth_pct=6.0),
            Segment("Pelvic / specialty", 0.08, None,
                    note="the emerging niche — cash-pay heavy",
                    growth_pct=9.0),
        ],
        growth_drivers=[
            GrowthDriver("Surgical volume growth", 3.0,
                         "total joints + ASC migration feed referrals"),
            GrowthDriver("Direct access / conservative care", 2.0,
                         "payers prefer \$1,200 PT episodes over "
                         "\$30K surgeries"),
            GrowthDriver("Demographics", 1.5,
                         "active-aging demand floor"),
            GrowthDriver("Medicare fee cuts", -2.0,
                         "PFS therapy-code reductions — the chronic "
                         "headwind"),
            GrowthDriver("Therapist wage inflation", -1.5,
                         "PT salary growth outpaces rate growth; "
                         "clinic-level margin squeeze"),
        ],
        sam_share=0.50,
        sam_note="Outpatient private-practice universe (excl. hospital "
                 "OP departments + home/SNF settings)",
        som_share=0.03,
        som_note="Largest platform (Upstream/USPh/ATI class) holds <3% "
                 "— deeply fragmented",
        horizon_years=5,
        basis_note="Template defaults from APTA/CMS public data — "
                   "replace with engagement data before IC use.",
    )



def veterinary_template() -> TamSamModel:
    """Companion-animal veterinary sizing — AVMA/APPA-anchored. The
    most consolidated 'non-healthcare healthcare' PE vertical."""
    return TamSamModel(
        name="Veterinary · companion-animal practice market",
        chain=[
            DriverStep("US pet-owning households", 87_000_000, op="base",
                       unit="households",
                       source="APPA National Pet Owners Survey"),
            DriverStep("Avg vet visits per household / yr", 2.4,
                       op="mult", unit="visits/yr",
                       source="AVMA pet-owner survey (dog+cat blend)"),
            DriverStep("Avg revenue per visit", 260, op="price",
                       unit="$/visit",
                       source="AVMA economic state of the profession "
                              "(exam + dx + rx blend)"),
        ],
        segments=[
            Segment("General practice", 0.62, None,
                    note="the consolidation base — Mars/NVA/Thrive "
                         "rolled the cities", growth_pct=4.0),
            Segment("Specialty / referral (ER, onc, surgery)", 0.22,
                    None, note="the margin + growth engine",
                    growth_pct=8.0),
            Segment("Urgent care / after-hours", 0.08, None,
                    note="the newest format — de-novo economics",
                    growth_pct=10.0),
            Segment("Mobile / at-home", 0.08, None, growth_pct=6.0),
        ],
        growth_drivers=[
            GrowthDriver("Pet spending growth", 4.5,
                         "humanization of pets — spend grows through "
                         "recessions"),
            GrowthDriver("Pricing power", 3.0,
                         "cash-pay; no payer pushback; vet CPI has "
                         "outrun core CPI for a decade"),
            GrowthDriver("Insurance penetration", 1.5,
                         "pet insurance ~4% of pets and climbing — "
                         "loosens the wallet ceiling"),
            GrowthDriver("Veterinarian shortage", -2.5,
                         "DVM supply is the binding constraint — "
                         "appointment caps, not demand"),
            GrowthDriver("Visit-frequency normalization", -1.0,
                         "post-2021 pet-boom cohort aging out"),
        ],
        sam_share=0.55,
        sam_note="Metro + suburban practices a platform can staff "
                 "(rural single-DVM excluded)",
        som_share=0.04,
        som_note="Mars holds ~7% of clinics; the long tail is still "
                 "~75% independent",
        horizon_years=5,
        basis_note="Template defaults from AVMA/APPA public data — "
                   "replace with engagement data before IC use.",
    )


def medspa_template() -> TamSamModel:
    """Medical aesthetics / medspa sizing — AmSpa-anchored. Cash-pay,
    consumer-cyclical, and the fastest-fragmenting clinic format."""
    return TamSamModel(
        name="Medspa · medical aesthetics market",
        chain=[
            DriverStep("US medspa locations", 10_500, op="base",
                       unit="locations", source="AmSpa state of the "
                       "industry report"),
            DriverStep("Avg revenue per location", 1_600_000, op="price",
                       unit="$/location/yr",
                       source="AmSpa benchmarking (median ~$1.2M, "
                              "mean pulled up by multi-room urban)"),
        ],
        segments=[
            Segment("Injectables (tox + filler)", 0.55, None,
                    note="the volume + frequency engine — 3–4 visits/yr "
                         "recurring", growth_pct=9.0),
            Segment("Energy devices (laser, RF, body)", 0.20, None,
                    growth_pct=6.0),
            Segment("Skin / membership facials", 0.15, None,
                    note="the retention layer — membership models",
                    growth_pct=7.0),
            Segment("Weight management (GLP-1 adjacency)", 0.10, None,
                    note="the newest line — compounding-rule risk",
                    growth_pct=15.0),
        ],
        growth_drivers=[
            GrowthDriver("Consumer demand / destigmatization", 6.0,
                         "male + under-35 adoption widening the funnel"),
            GrowthDriver("Unit growth / de-novo", 4.0,
                         "location count compounding ~10%/yr pre-"
                         "saturation"),
            GrowthDriver("GLP-1 halo", 2.0,
                         "weight-loss patients convert to aesthetics"),
            GrowthDriver("Consumer-cyclical exposure", -2.5,
                         "discretionary cash-pay — recession beta is "
                         "the bear case, shown as one"),
            GrowthDriver("Injector supply / scope rules", -1.5,
                         "NP/RN scope-of-practice + med-director rules "
                         "cap throughput"),
        ],
        sam_share=0.50,
        sam_note="Suburban + urban metros with density for multi-"
                 "location brands",
        som_share=0.03,
        som_note="No platform holds >2% — the most fragmented "
                 "consumer-health format",
        horizon_years=5,
        basis_note="Template defaults from AmSpa public reports — "
                   "replace with engagement data before IC use.",
    )


def ems_template() -> TamSamModel:
    """Ambulance / EMS sizing — NEMSIS/GAO-anchored. A regulated,
    municipal-contract niche with structural payer drag."""
    return TamSamModel(
        name="EMS · ambulance transport market",
        chain=[
            DriverStep("US EMS transports / yr", 22_000_000, op="base",
                       unit="transports",
                       source="NEMSIS national EMS data"),
            DriverStep("% by private operators", 0.40, op="rate",
                       unit="of transports",
                       source="GAO / AAA industry estimates (vs fire "
                              "department + hospital-based)"),
            DriverStep("Avg revenue per transport", 1_350, op="price",
                       unit="$/transport",
                       source="Medicare ambulance fee schedule × "
                              "payer blend (GAO)"),
        ],
        segments=[
            Segment("911 emergency (contracted)", 0.45, None,
                    note="municipal contracts — sticky, low-margin",
                    growth_pct=2.0),
            Segment("Interfacility transfer (IFT)", 0.40, None,
                    note="the margin segment — hospital-contracted",
                    growth_pct=4.0),
            Segment("Critical care / specialty (CCT, neo)", 0.10, None,
                    note="highest rate per transport", growth_pct=6.0),
            Segment("Event / standby", 0.05, None, growth_pct=3.0),
        ],
        growth_drivers=[
            GrowthDriver("Utilization / demographics", 2.5,
                         "transport volume scales with 65+ + ED "
                         "throughput"),
            GrowthDriver("Rate relief (state add-ons)", 1.5,
                         "GEMT/supplemental programs patch Medicaid "
                         "underpayment"),
            GrowthDriver("Balance-billing restrictions", -1.5,
                         "No Surprises Act ground-ambulance extension "
                         "risk — the policy headwind"),
            GrowthDriver("EMT/paramedic shortage", -2.0,
                         "crew supply is the binding constraint; "
                         "wage inflation outruns rate updates"),
        ],
        sam_share=0.55,
        sam_note="Private-operator markets ex the municipal-only "
                 "jurisdictions",
        som_share=0.06,
        som_note="Top platforms (GMR class) hold meaningful share — "
                 "less fragmented than other niches",
        horizon_years=5,
        basis_note="Template defaults from NEMSIS/GAO public data — "
                   "replace with engagement data before IC use.",
    )



def clinical_labs_template() -> TamSamModel:
    """Independent clinical laboratory sizing — CMS CLFS/ACLA-anchored.
    The duopoly (Quest/Labcorp) + hospital-outreach divestiture story."""
    return TamSamModel(
        name="Clinical labs · independent laboratory market",
        chain=[
            DriverStep("US lab tests / yr (clinical)", 14_000_000_000,
                       op="base", unit="tests",
                       source="ACLA (13–14B tests/yr; 70% of clinical "
                              "decisions touch a lab result)"),
            DriverStep("% via independent labs", 0.35, op="rate",
                       unit="of tests",
                       source="ACLA / hospital-vs-independent split"),
            DriverStep("Avg revenue per test", 14, op="price",
                       unit="$/test",
                       source="CMS CLFS median × commercial blend "
                              "(routine panel weighted)"),
        ],
        segments=[
            Segment("Routine / core chemistry", 0.55, None,
                    note="PAMA-exposed; scale game", growth_pct=1.5),
            Segment("Molecular / genomics", 0.20, None,
                    note="the growth engine — oncology panels, "
                         "carrier screening, MRD", growth_pct=10.0),
            Segment("Anatomic pathology", 0.15, None, growth_pct=3.0),
            Segment("Toxicology / specialty", 0.10, None,
                    note="post-2018 tox washout survivor pool",
                    growth_pct=2.0),
        ],
        growth_drivers=[
            GrowthDriver("Test-menu expansion (molecular)", 4.0,
                         "genomics + liquid biopsy widen the order "
                         "set"),
            GrowthDriver("Utilization / demographics", 2.0,
                         "chronic-disease monitoring scales with age"),
            GrowthDriver("Hospital outreach divestitures", 1.5,
                         "systems selling outreach books to "
                         "independents — the M&A pipeline itself"),
            GrowthDriver("PAMA rate cuts", -2.5,
                         "CLFS repricing — the structural headwind on "
                         "routine volume"),
            GrowthDriver("Payer leakage programs", -1.0,
                         "payers steering to in-network duopoly labs"),
        ],
        sam_share=0.40,
        sam_note="Regional independents + outreach books acquirable "
                 "outside the duopoly's lock",
        som_share=0.05,
        som_note="Quest + Labcorp hold ~45% of independent volume — "
                 "the regionals are the targets",
        horizon_years=5,
        basis_note="Template defaults from ACLA/CMS CLFS public data — "
                   "replace with engagement data before IC use.",
    )


def specialty_pharmacy_template() -> TamSamModel:
    """Specialty pharmacy sizing — IQVIA/Drug Channels-anchored. The
    biggest dollar pool in the catalogue, with the thinnest margins."""
    return TamSamModel(
        name="Specialty pharmacy · dispensing market",
        chain=[
            DriverStep("US specialty drug spend / yr",
                       400_000_000_000, op="base", unit="$",
                       source="IQVIA / Drug Channels Institute "
                              "(specialty ≈ 55% of net drug spend)"),
            DriverStep("% via specialty pharmacy channel", 0.80,
                       op="rate", unit="of spend",
                       source="Drug Channels (vs buy-and-bill/retail)"),
        ],
        segments=[
            Segment("PBM-owned (vertical) SPs", 0.70, None,
                    note="CVS/ESI/Optum own the channel — the moat "
                         "AGAINST independents", growth_pct=7.0),
            Segment("Independent / health-system SPs", 0.20, None,
                    note="the acquirable layer — limited-distribution "
                         "drug access is the differentiator",
                    growth_pct=9.0),
            Segment("Hub / patient-services adjacency", 0.10, None,
                    note="where PE actually plays — services, not "
                         "dispensing margin", growth_pct=10.0),
        ],
        growth_drivers=[
            GrowthDriver("Specialty pipeline / launches", 7.0,
                         "cell/gene, oncology, immunology launches — "
                         "the dominant driver"),
            GrowthDriver("Utilization growth", 2.0,
                         "prevalence + duration of therapy"),
            GrowthDriver("Biosimilar / net-price deflation", -3.0,
                         "Humira-style LOEs deflate the base — a "
                         "structural headwind"),
            GrowthDriver("DIR / reimbursement pressure", -1.5,
                         "pharmacy DIR + network spread compression"),
        ],
        sam_share=0.20,
        sam_note="The independent + hub/services layer investable "
                 "outside PBM verticals",
        som_share=0.03,
        som_note="Dispensing margin is 2–4%; the services adjacency "
                 "is where returns live",
        horizon_years=5,
        basis_note="Template defaults from IQVIA/Drug Channels public "
                   "data — replace with engagement data before IC use.",
    )


def vision_template() -> TamSamModel:
    """Vision / optometry sizing — Vision Council-anchored."""
    return TamSamModel(
        name="Vision · optometry + optical retail market",
        chain=[
            DriverStep("US adults using vision correction",
                       195_000_000, op="base", unit="adults",
                       source="Vision Council (~76% of adults)"),
            DriverStep("Avg annual vision spend per user", 310,
                       op="price", unit="$/user/yr",
                       source="Vision Council consumer spend (exams + "
                              "frames/lenses/contacts blend)"),
        ],
        segments=[
            Segment("Optical retail (frames/lenses)", 0.45, None,
                    note="consumer-discretionary; online competition",
                    growth_pct=2.0),
            Segment("Exams / clinical optometry", 0.25, None,
                    note="the medical-optometry shift — dry eye, "
                         "myopia management", growth_pct=5.0),
            Segment("Contact lenses", 0.20, None, growth_pct=4.0),
            Segment("Medical / surgical co-management", 0.10, None,
                    note="cataract/refractive co-management — the "
                         "ophtho adjacency", growth_pct=6.0),
        ],
        growth_drivers=[
            GrowthDriver("Demographics / presbyopia wave", 2.5,
                         "45+ population needs progressive correction"),
            GrowthDriver("Medical optometry expansion", 2.0,
                         "scope expansion moves optometry up the "
                         "acuity curve"),
            GrowthDriver("Myopia epidemic", 1.5,
                         "childhood myopia management — the new "
                         "recurring-revenue line"),
            GrowthDriver("Online / DTC disruption", -2.0,
                         "Warby/online refraction skim the retail "
                         "margin — the structural headwind"),
            GrowthDriver("Vision-plan reimbursement", -1.0,
                         "managed-vision-care fee schedules flat"),
        ],
        sam_share=0.45,
        sam_note="Independent OD practices + regional optical chains "
                 "(excl. national verticals like Luxottica retail)",
        som_share=0.03,
        som_note="Largest PE platforms hold ~2% of practices — "
                 "deeply fragmented",
        horizon_years=5,
        basis_note="Template defaults from Vision Council public data "
                   "— replace with engagement data before IC use.",
    )



def aba_template() -> TamSamModel:
    """Autism services / ABA sizing — CDC-anchored. The fastest-grown
    BH sub-vertical, sized standalone for the niche depth CDD needs."""
    return TamSamModel(
        name="ABA · autism therapy services market",
        chain=[
            DriverStep("US children with ASD (3–17)", 1_800_000,
                       op="base", unit="children",
                       source="CDC ADDM (1-in-36 prevalence × census)"),
            DriverStep("% receiving ABA services", 0.30, op="rate",
                       unit="of diagnosed",
                       source="payer claims studies; access-"
                              "constrained, not demand-constrained"),
            DriverStep("Avg ABA hours / wk", 14, op="mult",
                       unit="hrs/wk", source="CASP practice parameters "
                       "(10–25h comprehensive blend)"),
            DriverStep("Weeks in service / yr", 46, op="mult",
                       unit="wks/yr", source="industry standard"),
            DriverStep("Avg reimbursed rate / hr", 65, op="price",
                       unit="$/hr",
                       source="Medicaid + commercial blended BCBA/RBT "
                              "billed rates"),
        ],
        segments=[
            Segment("Center-based", 0.45, None,
                    note="the platform model — utilization + clinical "
                         "supervision economics", growth_pct=10.0),
            Segment("Home-based", 0.40, None,
                    note="labor-logistics heavy; lower margin",
                    growth_pct=6.0),
            Segment("School / community", 0.15, None, growth_pct=5.0),
        ],
        growth_drivers=[
            GrowthDriver("Diagnosed prevalence", 5.0,
                         "ADDM prevalence has compounded ~5%/yr for "
                         "two decades"),
            GrowthDriver("Coverage mandates", 2.0,
                         "all 50 states mandate; Medicaid EPSDT "
                         "enforcement still expanding access"),
            GrowthDriver("Access build-out", 3.0,
                         "waitlists everywhere — supply growth IS "
                         "revenue growth"),
            GrowthDriver("BCBA/RBT labor shortage", -3.0,
                         "certified-staff supply is the binding "
                         "constraint; turnover ~30%+"),
            GrowthDriver("Payer rate scrutiny", -1.5,
                         "Medicaid rate pressure + utilization "
                         "management on comprehensive hours"),
        ],
        sam_share=0.55,
        sam_note="Commercially-insured + managed-Medicaid metros a "
                 "platform can staff",
        som_share=0.03,
        som_note="Largest platforms (CARD/Hopebridge class) hold ~2% "
                 "— hyper-fragmented",
        horizon_years=5,
        basis_note="Template defaults from CDC/CASP public data — "
                   "replace with engagement data before IC use.",
    )


def plasma_template() -> TamSamModel:
    """Plasma collection sizing — PPTA-anchored. Fixed-cost center
    economics feeding a fractionation oligopoly."""
    return TamSamModel(
        name="Plasma · source-plasma collection market",
        chain=[
            DriverStep("US collection centers", 1_100, op="base",
                       unit="centers", source="PPTA / FDA registered "
                       "source-plasma centers"),
            DriverStep("Donations per center / yr", 28_000, op="mult",
                       unit="donations/yr",
                       source="PPTA throughput benchmarks (~550/wk)"),
            DriverStep("Revenue per donation (liter-equivalent)", 150,
                       op="price", unit="$/donation",
                       source="fractionator transfer pricing "
                              "(donor fee ~$50 + margin + processing)"),
        ],
        segments=[
            Segment("Fractionator-owned (CSL/Grifols/Takeda)", 0.80,
                    None, note="vertically integrated — NOT acquirable",
                    growth_pct=5.0),
            Segment("Independent collectors", 0.20, None,
                    note="the investable layer — long-term supply "
                         "agreements with fractionators",
                    growth_pct=8.0),
        ],
        growth_drivers=[
            GrowthDriver("Ig demand growth", 6.0,
                         "immunoglobulin demand compounds 6–8%/yr — "
                         "the pull-through driver"),
            GrowthDriver("Center build-out", 3.0,
                         "post-COVID collection recovery + de-novo "
                         "expansion"),
            GrowthDriver("Donor-pool economics", -1.5,
                         "donor fees are the cost line; competition "
                         "for donors raises them"),
            GrowthDriver("Recombinant substitution", -1.0,
                         "FcRn blockers / recombinant alternatives "
                         "nibble at Ig indications — the tail risk"),
        ],
        sam_share=0.20,
        sam_note="The independent-collector layer (fractionator-owned "
                 "centers are not for sale)",
        som_share=0.10,
        som_note="A platform of 20–30 centers is a meaningful "
                 "independent",
        horizon_years=5,
        basis_note="Template defaults from PPTA/FDA public data — "
                   "replace with engagement data before IC use.",
    )


def clinical_research_template() -> TamSamModel:
    """Clinical research site / SMO sizing — the hottest post-2021
    services niche. IQVIA/CenterWatch-anchored."""
    return TamSamModel(
        name="Clinical research · site network market",
        chain=[
            DriverStep("US industry-funded trials active / yr", 6_000,
                       op="base", unit="trials",
                       source="ClinicalTrials.gov industry-sponsored, "
                              "US-sites active"),
            DriverStep("Avg US sites per trial", 25, op="mult",
                       unit="sites/trial",
                       source="CenterWatch / IQVIA site-count norms"),
            DriverStep("Avg site revenue per trial", 350_000,
                       op="price", unit="$/site/trial",
                       source="per-patient grants × enrollment + "
                              "start-up fees (SCRS benchmarks)"),
        ],
        segments=[
            Segment("Dedicated research sites / SMOs", 0.35, None,
                    note="the platform model — multi-site, multi-"
                         "therapeutic", growth_pct=9.0),
            Segment("Physician-practice embedded", 0.40, None,
                    note="the acquirable long tail", growth_pct=5.0),
            Segment("Academic / health-system", 0.25, None,
                    note="slowest start-up times — sponsors steering "
                         "away", growth_pct=2.0),
        ],
        growth_drivers=[
            GrowthDriver("Pipeline volume (obesity, CNS, onc)", 6.0,
                         "GLP-1 + Alzheimer's + oncology trial waves "
                         "demand site capacity"),
            GrowthDriver("Decentralized / hybrid trial mix", 2.0,
                         "DCT components ADD site coordination "
                         "revenue, not replace it"),
            GrowthDriver("Sponsor site-consolidation preference", 2.5,
                         "sponsors pay for predictable enrollment — "
                         "networks win allocation"),
            GrowthDriver("Coordinator labor shortage", -2.0,
                         "CRC turnover is the binding constraint"),
            GrowthDriver("Biotech funding cyclicality", -1.5,
                         "XBI-correlated trial starts — the cyclical "
                         "bear case, shown as one"),
        ],
        sam_share=0.45,
        sam_note="Dedicated + embedded sites consolidatable into "
                 "networks (academic excluded)",
        som_share=0.04,
        som_note="No site network holds >3% of trial allocation",
        horizon_years=5,
        basis_note="Template defaults from ClinicalTrials.gov/SCRS "
                   "public data — replace with engagement data before "
                   "IC use.",
    )



def wound_care_template() -> TamSamModel:
    """Advanced wound care services sizing — AHRQ/Medicare-anchored."""
    return TamSamModel(
        name="Wound care · advanced wound services market",
        chain=[
            DriverStep("US patients with chronic wounds / yr",
                       8_200_000, op="base", unit="patients",
                       source="Medicare claims analyses (Nussbaum et "
                              "al.) — chronic non-healing wounds"),
            DriverStep("% receiving advanced wound care", 0.25,
                       op="rate", unit="of patients",
                       source="wound-registry penetration estimates"),
            DriverStep("Avg episodes of care / yr", 1.3, op="mult",
                       unit="episodes/yr", source="registry data"),
            DriverStep("Avg revenue per episode", 3_800, op="price",
                       unit="$/episode",
                       source="HOPD wound-clinic + CTP/HBO blend "
                              "(Medicare fee schedules)"),
        ],
        segments=[
            Segment("Hospital-based wound centers (managed)", 0.50,
                    None, note="the management-contract model — "
                         "Healogics/RestorixHealth class",
                    growth_pct=3.0),
            Segment("Office / mobile wound practices", 0.30, None,
                    note="the physician-services roll-up layer",
                    growth_pct=8.0),
            Segment("Post-acute / SNF wound rounds", 0.20, None,
                    growth_pct=6.0),
        ],
        growth_drivers=[
            GrowthDriver("Diabetes / vascular prevalence", 4.0,
                         "diabetic foot ulcers compound with the "
                         "diabetes curve"),
            GrowthDriver("Site-shift to office/mobile", 2.5,
                         "payers steering off HOPD wound-center "
                         "rates"),
            GrowthDriver("CTP (skin-substitute) scrutiny", -2.5,
                         "CMS LCD crackdowns on skin-substitute "
                         "spend — the compliance headwind"),
            GrowthDriver("Documentation/audit burden", -1.0,
                         "TPE audits on debridement frequency"),
        ],
        sam_share=0.45,
        sam_note="Office/mobile + management contracts (hospital-"
                 "employed programs excluded)",
        som_share=0.05,
        som_note="Healogics manages ~600 centers; the office/mobile "
                 "layer is fragmented",
        horizon_years=5,
        basis_note="Template defaults from Medicare claims literature "
                   "— replace with engagement data before IC use.",
    )


def sleep_template() -> TamSamModel:
    """Sleep medicine sizing — AASM-anchored. The HSAT disruption is
    the structural story."""
    return TamSamModel(
        name="Sleep · diagnostics + therapy market",
        chain=[
            DriverStep("US adults with OSA (undiagnosed incl.)",
                       30_000_000, op="base", unit="adults",
                       source="AASM prevalence estimates"),
            DriverStep("% diagnosed and in care / yr", 0.20, op="rate",
                       unit="of prevalent",
                       source="AASM — the diagnosis gap IS the "
                              "whitespace"),
            DriverStep("Avg annual revenue per managed patient", 900,
                       op="price", unit="$/patient/yr",
                       source="dx (PSG/HSAT amortized) + PAP resupply "
                              "annuity blend"),
        ],
        segments=[
            Segment("PAP therapy + resupply", 0.55, None,
                    note="the annuity — resupply is the recurring "
                         "engine", growth_pct=6.0),
            Segment("Home sleep testing (HSAT)", 0.20, None,
                    note="disrupting in-lab PSG at 1/4 the price",
                    growth_pct=9.0),
            Segment("In-lab PSG", 0.15, None,
                    note="declining — complex cases only",
                    growth_pct=-2.0),
            Segment("Oral appliance / surgery / other", 0.10, None,
                    growth_pct=5.0),
        ],
        growth_drivers=[
            GrowthDriver("Diagnosis-gap closure", 4.0,
                         "80% undiagnosed — screening + awareness "
                         "close it slowly"),
            GrowthDriver("Resupply annuity compliance", 2.0,
                         "adherence programs lift the recurring base"),
            GrowthDriver("GLP-1 OSA-indication effect", -1.5,
                         "tirzepatide's OSA label may shrink severe "
                         "OSA over the hold — the new bear case"),
            GrowthDriver("Competitive bidding / DME rates", -1.5,
                         "CMS DMEPOS pricing pressure on PAP"),
        ],
        sam_share=0.55,
        sam_note="Independent sleep practices + DME-integrated "
                 "platforms",
        som_share=0.04,
        som_note="Fragmented behind the device manufacturers",
        horizon_years=5,
        basis_note="Template defaults from AASM/CMS public data — "
                   "replace with engagement data before IC use.",
    )


def occ_health_template() -> TamSamModel:
    """Occupational health sizing — employer-paid, payer-free
    economics. BLS-anchored."""
    return TamSamModel(
        name="Occupational health · employer services market",
        chain=[
            DriverStep("US private-sector workers", 135_000_000,
                       op="base", unit="workers", source="BLS CES"),
            DriverStep("Avg occ-health spend per worker / yr", 190,
                       op="price", unit="$/worker/yr",
                       source="employer benchmarks: injury care + "
                              "exams + screens + surveillance blend"),
        ],
        segments=[
            Segment("Work injury care (comp-funded)", 0.45, None,
                    note="Concentra's franchise — fee-schedule "
                         "protected", growth_pct=3.0),
            Segment("Exams / compliance (DOT, pre-placement)", 0.30,
                    None, note="volume annuity; regulation-driven",
                    growth_pct=4.0),
            Segment("Drug & alcohol screening", 0.15, None,
                    growth_pct=2.0),
            Segment("On-site / near-site clinics", 0.10, None,
                    note="the employer-direct growth format",
                    growth_pct=8.0),
        ],
        growth_drivers=[
            GrowthDriver("Employment / wage base", 1.5,
                         "volume tracks payrolls"),
            GrowthDriver("Comp fee-schedule updates", 2.0,
                         "state WC fee schedules grind upward"),
            GrowthDriver("Employer direct-contracting", 2.0,
                         "on-site/near-site expansion"),
            GrowthDriver("Injury-rate secular decline", -1.5,
                         "TRIR has fallen for decades — the volume "
                         "headwind, shown as one"),
            GrowthDriver("Telehealth triage substitution", -0.5,
                         "tele-triage diverts low-acuity visits"),
        ],
        sam_share=0.50,
        sam_note="Retail occ-health + employer-direct formats "
                 "(carrier-owned networks excluded)",
        som_share=0.05,
        som_note="Concentra holds ~10% of the retail layer; the rest "
                 "is fragmented",
        horizon_years=5,
        basis_note="Template defaults from BLS + employer benchmarks "
                   "— replace with engagement data before IC use.",
    )



def dermatology_template() -> TamSamModel:
    """Dermatology sizing — the FIRST PPM wave, now mature: a worked
    example of underwriting a consolidated specialty."""
    return TamSamModel(
        name="Dermatology · practice + ancillary market",
        chain=[
            DriverStep("US dermatologists (practicing)", 12_500,
                       op="base", unit="physicians",
                       source="AAD workforce census"),
            DriverStep("Avg revenue per dermatologist", 1_500_000,
                       op="price", unit="$/MD/yr",
                       source="MGMA derm medians incl. ancillaries "
                              "(path lab + Mohs + cosmetic)"),
        ],
        segments=[
            Segment("Medical dermatology", 0.50, None,
                    note="the visit engine — biologics referrals the "
                         "hidden value", growth_pct=4.0),
            Segment("Mohs / surgical", 0.20, None,
                    note="the margin engine — skin-cancer volume "
                         "compounds with sun-exposed boomers",
                    growth_pct=6.0),
            Segment("Dermatopathology (in-house)", 0.12, None,
                    note="ancillary capture; payer scrutiny",
                    growth_pct=3.0),
            Segment("Cosmetic (cash-pay)", 0.18, None,
                    note="medspa-adjacent; consumer-cyclical",
                    growth_pct=5.0),
        ],
        growth_drivers=[
            GrowthDriver("Skin-cancer incidence", 3.5,
                         "melanoma + NMSC compound with demographics"),
            GrowthDriver("Biologics-era visit demand", 2.0,
                         "psoriasis/eczema biologics pull patients "
                         "into care"),
            GrowthDriver("Teledermatology triage", 1.0,
                         "access expansion, mild ASP lift"),
            GrowthDriver("Consolidation maturity", -1.5,
                         "the first PPM wave already rolled the best "
                         "markets — entry multiples vs exit paths "
                         "compress, shown as a headwind"),
            GrowthDriver("Derm workforce cap", -1.0,
                         "residency slots flat; NP/PA leverage has "
                         "limits"),
        ],
        sam_share=0.40,
        sam_note="Remaining independent practices + secondary-market "
                 "platforms (first-wave assets trade as re-trades)",
        som_share=0.04,
        som_note="A mature consolidation: the question is exit path, "
                 "not entry runway",
        horizon_years=5,
        basis_note="Template defaults from AAD/MGMA public data — "
                   "replace with engagement data before IC use.",
    )


def pain_management_template() -> TamSamModel:
    """Interventional pain sizing — ASC-adjacent, UM-heavy."""
    return TamSamModel(
        name="Pain management · interventional practice market",
        chain=[
            DriverStep("US adults with chronic pain", 51_000_000,
                       op="base", unit="adults",
                       source="CDC chronic-pain prevalence (20.9%)"),
            DriverStep("% receiving interventional care / yr", 0.07,
                       op="rate", unit="of chronic-pain adults",
                       source="claims-based interventional penetration"),
            DriverStep("Avg procedures per treated patient / yr", 2.6,
                       op="mult", unit="procedures/yr",
                       source="ASIPP utilization norms"),
            DriverStep("Avg revenue per procedure", 1_100, op="price",
                       unit="$/procedure",
                       source="Medicare PFS + facility blend (ESI/RFA/"
                              "SCS-weighted)"),
        ],
        segments=[
            Segment("Injections (ESI, facet, joint)", 0.55, None,
                    note="the volume base — UM-target #1",
                    growth_pct=3.0),
            Segment("RF ablation", 0.20, None, growth_pct=6.0),
            Segment("Neuromodulation (SCS/PNS)", 0.15, None,
                    note="the margin engine — device-partnered",
                    growth_pct=8.0),
            Segment("Regenerative / cash (PRP)", 0.10, None,
                    note="cash-pay; evidence-grade risk",
                    growth_pct=7.0),
        ],
        growth_drivers=[
            GrowthDriver("Opioid-alternative demand", 3.5,
                         "payers + guidelines push interventional "
                         "over opioids"),
            GrowthDriver("ASC migration", 2.0,
                         "pain cases shift to owned ASCs — facility-"
                         "fee capture"),
            GrowthDriver("Neuromodulation adoption", 1.5,
                         "SCS/PNS indication expansion"),
            GrowthDriver("Utilization management", -2.5,
                         "prior-auth + frequency limits on injections "
                         "— the defining payer headwind"),
            GrowthDriver("PFS rate pressure", -1.0,
                         "Medicare conversion-factor cuts"),
        ],
        sam_share=0.50,
        sam_note="Independent interventional practices + pain-ASC "
                 "co-ownership opportunities",
        som_share=0.04,
        som_note="Fragmented; no platform holds >3%",
        horizon_years=5,
        basis_note="Template defaults from CDC/ASIPP/CMS public data "
                   "— replace with engagement data before IC use.",
    )


def hospital_at_home_template() -> TamSamModel:
    """Hospital-at-home sizing — the emerging format. Small TAM today,
    waiver-dependent: the build says BOTH honestly."""
    return TamSamModel(
        name="Hospital-at-home · acute care at home market",
        chain=[
            DriverStep("HaH-eligible inpatient admissions / yr",
                       3_000_000, op="base", unit="admissions",
                       source="literature: ~10% of medical admissions "
                              "meet HaH clinical criteria"),
            DriverStep("% actually treated at home", 0.03, op="rate",
                       unit="of eligible",
                       source="AHCaH waiver volumes — penetration is "
                              "TINY today; that gap is the thesis"),
            DriverStep("Avg revenue per episode", 12_000, op="price",
                       unit="$/episode",
                       source="DRG-equivalent payment under the CMS "
                              "AHCaH waiver"),
        ],
        segments=[
            Segment("Health-system programs (waiver)", 0.75, None,
                    note="the current market — systems own the "
                         "license; vendors enable", growth_pct=15.0),
            Segment("Enabler / tech-services vendors", 0.20, None,
                    note="where PE can actually invest — per-episode "
                         "service fees", growth_pct=20.0),
            Segment("Payer-direct (MA) programs", 0.05, None,
                    growth_pct=18.0),
        ],
        growth_drivers=[
            GrowthDriver("Penetration of eligible admissions", 15.0,
                         "3% → 10%+ of eligible is the base-case "
                         "build — capacity economics favor it"),
            GrowthDriver("Capacity pressure tailwind", 3.0,
                         "hospital bed scarcity makes HaH a relief "
                         "valve"),
            GrowthDriver("Waiver non-renewal risk", -8.0,
                         "the AHCaH waiver needs Congressional "
                         "renewal — THE existential risk, priced as "
                         "a large negative driver"),
            GrowthDriver("Staffing logistics", -2.0,
                         "community-paramedic + nurse supply caps "
                         "scale"),
        ],
        sam_share=0.20,
        sam_note="The enabler/vendor layer + MA-direct (system-owned "
                 "programs are not acquirable)",
        som_share=0.08,
        som_note="An early market — share is available but the "
                 "denominator is small",
        horizon_years=5,
        basis_note="Template defaults from CMS AHCaH public data + "
                   "literature — replace with engagement data before "
                   "IC use. NOTE the waiver-risk driver: this market "
                   "can halve on one appropriations cycle.",
    )



def ltc_pharmacy_template() -> TamSamModel:
    """Long-term-care pharmacy sizing — the SNF/AL med-dispensing
    niche. ASCP-anchored."""
    return TamSamModel(
        name="LTC pharmacy · institutional dispensing market",
        chain=[
            DriverStep("US LTC residents served (SNF+AL+IDD)",
                       3_100_000, op="base", unit="residents",
                       source="ASCP / NIC occupancy-based estimate"),
            DriverStep("Avg scripts per resident / yr", 110, op="mult",
                       unit="scripts/yr",
                       source="ASCP (9+ meds/resident, monthly cycles)"),
            DriverStep("Avg revenue per script", 55, op="price",
                       unit="$/script",
                       source="generic-heavy LTC mix + per-diem "
                              "consulting blend"),
        ],
        segments=[
            Segment("SNF (closed-door)", 0.50, None,
                    note="Omnicare/PharMerica territory — contract "
                         "churn risk", growth_pct=2.0),
            Segment("Assisted living", 0.30, None,
                    note="the growth setting — census shifting from "
                         "SNF to AL", growth_pct=6.0),
            Segment("IDD / behavioral group homes", 0.12, None,
                    note="sticky contracts, regulatory moat",
                    growth_pct=5.0),
            Segment("Hospice / other", 0.08, None, growth_pct=4.0),
        ],
        growth_drivers=[
            GrowthDriver("Senior census growth", 3.0,
                         "the 80+ wave fills AL beds"),
            GrowthDriver("Polypharmacy intensity", 1.5,
                         "meds per resident still climbing"),
            GrowthDriver("Generic deflation", -2.0,
                         "per-script revenue deflates as generics "
                         "deflate — the structural headwind"),
            GrowthDriver("PBM/payer rate pressure", -1.5,
                         "Part D plan reimbursement compression"),
        ],
        sam_share=0.45,
        sam_note="Regional closed-door pharmacies + AL-focused "
                 "platforms (national duopoly accounts excluded)",
        som_share=0.05,
        som_note="Omnicare (CVS) + PharMerica hold ~50% of SNF beds; "
                 "AL is the open flank",
        horizon_years=5,
        basis_note="Template defaults from ASCP/NIC public data — "
                   "replace with engagement data before IC use.",
    )


def dme_template() -> TamSamModel:
    """Durable medical equipment sizing — home-based care's hardware
    layer. CMS DMEPOS-anchored."""
    return TamSamModel(
        name="DME · home medical equipment market",
        chain=[
            DriverStep("US DME patients served / yr", 16_000_000,
                       op="base", unit="patients",
                       source="CMS DMEPOS utilization + AAHomecare"),
            DriverStep("Avg annual DME spend per patient", 3_800,
                       op="price", unit="$/patient/yr",
                       source="CMS DMEPOS fee schedules × category "
                              "mix (O2, PAP, mobility, diabetic)"),
        ],
        segments=[
            Segment("Respiratory (O2, vents, PAP)", 0.40, None,
                    note="the recurring-rental annuity — Lincare/"
                         "AdaptHealth territory", growth_pct=5.0),
            Segment("Diabetes (CGM, pumps)", 0.25, None,
                    note="the fastest line — CGM adoption",
                    growth_pct=12.0),
            Segment("Mobility / complex rehab", 0.20, None,
                    growth_pct=3.0),
            Segment("Wound / urological / other", 0.15, None,
                    growth_pct=4.0),
        ],
        growth_drivers=[
            GrowthDriver("Home-shift of care", 4.0,
                         "everything moving home needs equipment"),
            GrowthDriver("CGM / connected-device adoption", 3.0,
                         "diabetes tech penetration"),
            GrowthDriver("Competitive bidding rounds", -2.5,
                         "CMS DMEPOS bidding resets rates down — the "
                         "defining headwind"),
            GrowthDriver("Audit / documentation burden", -1.0,
                         "RAC/TPE audits on medical necessity"),
        ],
        sam_share=0.50,
        sam_note="Regional DME + specialty categories outside the "
                 "national consolidators' lock",
        som_share=0.04,
        som_note="AdaptHealth/Lincare/Rotech rolled respiratory; "
                 "diabetes + complex rehab are the open lanes",
        horizon_years=5,
        basis_note="Template defaults from CMS DMEPOS/AAHomecare "
                   "public data — replace with engagement data before "
                   "IC use.",
    )


def idd_services_template() -> TamSamModel:
    """IDD residential + day services sizing — the Medicaid-waiver
    niche. KFF/HCBS-anchored."""
    return TamSamModel(
        name="IDD services · residential + day program market",
        chain=[
            DriverStep("US adults with IDD receiving paid supports",
                       1_500_000, op="base", unit="individuals",
                       source="KFF / state IDD agency rollups"),
            DriverStep("Avg annual spend per individual", 45_000,
                       op="price", unit="$/individual/yr",
                       source="HCBS waiver per-capita (residential "
                              "$80-120K / day-only $15-25K blend)"),
        ],
        segments=[
            Segment("Group-home residential", 0.55, None,
                    note="the census base — staffing-cost exposed",
                    growth_pct=3.0),
            Segment("Day programs / employment", 0.20, None,
                    growth_pct=4.0),
            Segment("In-home / SDS supports", 0.18, None,
                    note="the policy-preferred growth setting",
                    growth_pct=8.0),
            Segment("Host-home / family models", 0.07, None,
                    note="the capital-light fastest grower",
                    growth_pct=9.0),
        ],
        growth_drivers=[
            GrowthDriver("Waiver enrollment growth", 3.0,
                         "waitlists in 35+ states unwind slowly — "
                         "funded demand"),
            GrowthDriver("Rate rebasing (DSP wages)", 2.5,
                         "states rebasing rates to fix the DSP wage "
                         "crisis — flows through revenue"),
            GrowthDriver("Institutional → community shift", 1.0,
                         "remaining ICF closures feed community "
                         "providers"),
            GrowthDriver("DSP workforce crisis", -3.0,
                         "direct-support staffing is THE constraint — "
                         "vacancy ~15%+, turnover ~45%"),
            GrowthDriver("Medicaid budget cyclicality", -1.0,
                         "state budget cycles gate rate updates"),
        ],
        sam_share=0.50,
        sam_note="States with managed/stable waiver programs + "
                 "provider-friendly rate structures",
        som_share=0.03,
        som_note="Mosaic/Sevita class platforms hold low single "
                 "digits — fragmentation persists",
        horizon_years=5,
        basis_note="Template defaults from KFF/HCBS public data — "
                   "replace with engagement data before IC use.",
    )



def eating_disorders_template() -> TamSamModel:
    """Eating-disorder treatment sizing — the highest-acuity BH niche.
    Prevalence-anchored with the access-gap thesis."""
    return TamSamModel(
        name="Eating disorders · treatment services market",
        chain=[
            DriverStep("US individuals with an active ED / yr",
                       9_000_000, op="base", unit="individuals",
                       source="NIMH/STRIPED prevalence (~2.7% of "
                              "population in any year)"),
            DriverStep("% receiving specialty treatment", 0.10,
                       op="rate", unit="of prevalent",
                       source="access studies — ~80–90% never receive "
                              "ED-specific care; the gap IS the thesis"),
            DriverStep("Avg treatment spend per patient / yr", 9_000,
                       op="price", unit="$/patient/yr",
                       source="level-of-care blend (OP $3–6K / IOP-PHP "
                              "$20–40K / residential $80K+ episodes)"),
        ],
        segments=[
            Segment("Outpatient / virtual", 0.40, None,
                    note="the access-expansion layer — Equip-style "
                         "virtual FBT", growth_pct=12.0),
            Segment("IOP / PHP", 0.30, None,
                    note="the step-down workhorse", growth_pct=7.0),
            Segment("Residential", 0.25, None,
                    note="highest revenue per stay; payer scrutiny on "
                         "length-of-stay", growth_pct=3.0),
            Segment("Inpatient (medical stabilization)", 0.05, None,
                    growth_pct=1.0),
        ],
        growth_drivers=[
            GrowthDriver("Diagnosed prevalence / awareness", 4.0,
                         "post-2020 adolescent ED incidence step-up"),
            GrowthDriver("Parity enforcement", 2.5,
                         "MHPAEA litigation forces ED coverage at "
                         "parity"),
            GrowthDriver("Virtual access expansion", 3.0,
                         "telehealth FBT widens the treated funnel"),
            GrowthDriver("Clinician scarcity", -2.5,
                         "ED-specialized clinicians are the binding "
                         "constraint"),
            GrowthDriver("Payer LOS management", -1.5,
                         "residential length-of-stay compression"),
        ],
        sam_share=0.55,
        sam_note="Commercially-insured + parity-enforced markets",
        som_share=0.05,
        som_note="A few platforms (ERC/Monte Nido/Alsana class) — "
                 "still fragmented below the top tier",
        horizon_years=5,
        basis_note="Template defaults from NIMH/STRIPED public data — "
                   "replace with engagement data before IC use.",
    )


def nephrology_template() -> TamSamModel:
    """Nephrology practice sizing — the value-based kidney-care niche
    (CKCC/REACH made it investable)."""
    return TamSamModel(
        name="Nephrology · kidney care practice market",
        chain=[
            DriverStep("US nephrologists (practicing)", 11_000,
                       op="base", unit="physicians",
                       source="ASN workforce data"),
            DriverStep("Avg practice revenue per nephrologist",
                       900_000, op="price", unit="$/MD/yr",
                       source="MGMA nephrology + dialysis medical-"
                              "directorship + VBC shared savings "
                              "blend"),
        ],
        segments=[
            Segment("FFS practice (visits, rounding)", 0.55, None,
                    note="the base — flat economics", growth_pct=2.0),
            Segment("Dialysis directorships / JVs", 0.20, None,
                    note="the annuity layer", growth_pct=3.0),
            Segment("Value-based kidney contracts (CKCC/MA)", 0.15,
                    None, note="the thesis layer — total-cost-of-care "
                         "shared savings", growth_pct=15.0),
            Segment("Access centers / ancillaries", 0.10, None,
                    growth_pct=5.0),
        ],
        growth_drivers=[
            GrowthDriver("CKD prevalence", 2.5,
                         "diabetes-driven CKD pipeline"),
            GrowthDriver("VBC contract expansion", 4.0,
                         "CKCC + MA delegation move dollars to "
                         "nephrologists — the structural rerating"),
            GrowthDriver("Home-dialysis economics", 1.0,
                         "home modality favors practice-aligned care"),
            GrowthDriver("Fee-schedule pressure", -1.5,
                         "MCP/visit code compression"),
            GrowthDriver("Model-rule uncertainty", -1.5,
                         "CMMI model parameters reset every cycle — "
                         "the VBC thesis depends on rulemaking"),
        ],
        sam_share=0.45,
        sam_note="Independent practices in VBC-viable markets "
                 "(dialysis-chain-employed excluded)",
        som_share=0.05,
        som_note="Panoramic/Evergreen/IKC class platforms early — "
                 "land-grab phase",
        horizon_years=5,
        basis_note="Template defaults from ASN/MGMA/CMMI public data "
                   "— replace with engagement data before IC use.",
    )


def orthotics_prosthetics_template() -> TamSamModel:
    """O&P sizing — the craft-clinical niche. AOPA-anchored."""
    return TamSamModel(
        name="O&P · orthotics + prosthetics market",
        chain=[
            DriverStep("US O&P patients served / yr", 5_500_000,
                       op="base", unit="patients",
                       source="AOPA industry estimates (orthotic-"
                              "dominant volume)"),
            DriverStep("Avg revenue per patient / yr", 1_300,
                       op="price", unit="$/patient/yr",
                       source="Medicare DMEPOS L-codes × commercial "
                              "blend (prosthetic episodes $15–60K "
                              "amortized over the orthotic base)"),
        ],
        segments=[
            Segment("Orthotics (bracing)", 0.55, None,
                    note="the volume base — OTS-vs-custom payer "
                         "pressure", growth_pct=3.0),
            Segment("Lower-limb prosthetics", 0.30, None,
                    note="the margin engine — diabetic amputation "
                         "volume", growth_pct=5.0),
            Segment("Upper-limb / advanced (MPK, myo)", 0.10, None,
                    note="the technology premium layer",
                    growth_pct=8.0),
            Segment("Pediatric / cranial", 0.05, None, growth_pct=6.0),
        ],
        growth_drivers=[
            GrowthDriver("Diabetes / vascular amputations", 3.0,
                         "the grim demand floor — ~150K amputations/yr "
                         "and rising"),
            GrowthDriver("Technology mix shift (MPK)", 2.0,
                         "microprocessor knees + myoelectric upgrades "
                         "lift revenue per case"),
            GrowthDriver("Coverage expansion advocacy", 1.0,
                         "'insurance fairness' state laws for "
                         "activity-specific prostheses"),
            GrowthDriver("OTS substitution / competitive bid", -1.5,
                         "payers push off-the-shelf bracing — the "
                         "orthotic margin headwind"),
            GrowthDriver("Certified-practitioner pipeline", -1.0,
                         "CPO supply is craft-constrained"),
        ],
        sam_share=0.55,
        sam_note="Independent O&P practices (Hanger holds ~25% — the "
                 "rest is acquirable)",
        som_share=0.05,
        som_note="Hanger is the only scaled platform; regional "
                 "consolidation is open",
        horizon_years=5,
        basis_note="Template defaults from AOPA/CMS public data — "
                   "replace with engagement data before IC use.",
    )



def ophthalmology_template() -> TamSamModel:
    """Ophthalmology / retina sizing — the highest-revenue-per-MD
    specialty consolidation. AAO-anchored."""
    return TamSamModel(
        name="Ophthalmology · surgical eye care market",
        chain=[
            DriverStep("US ophthalmologists (practicing)", 19_000,
                       op="base", unit="physicians",
                       source="AAO workforce census"),
            DriverStep("Avg revenue per ophthalmologist", 1_800_000,
                       op="price", unit="$/MD/yr",
                       source="MGMA ophtho medians incl. ASC + optical "
                              "+ retina drug margin"),
        ],
        segments=[
            Segment("Cataract / anterior segment", 0.40, None,
                    note="the volume franchise — premium-IOL upsell "
                         "is the cash-pay layer", growth_pct=4.0),
            Segment("Retina (medical + surgical)", 0.30, None,
                    note="the margin engine — anti-VEGF buy-and-bill; "
                         "biosimilar exposure", growth_pct=6.0),
            Segment("Glaucoma / cornea / other", 0.20, None,
                    growth_pct=4.0),
            Segment("Refractive (LASIK/SMILE, cash)", 0.10, None,
                    note="consumer-cyclical", growth_pct=3.0),
        ],
        growth_drivers=[
            GrowthDriver("Cataract demographics", 4.0,
                         "4M+ cataract surgeries/yr compounding with "
                         "the 65+ wave"),
            GrowthDriver("Premium-IOL / cash-pay mix", 2.0,
                         "presbyopia-correcting lens adoption"),
            GrowthDriver("Retina therapeutics pipeline", 1.5,
                         "geographic-atrophy agents expand treatable "
                         "volume"),
            GrowthDriver("Anti-VEGF biosimilar erosion", -2.0,
                         "the retina buy-and-bill spread compresses — "
                         "shown as one"),
            GrowthDriver("Cataract fee compression", -1.5,
                         "Medicare PFS facility+professional cuts"),
        ],
        sam_share=0.45,
        sam_note="Independent practices + ASC co-ownership in non-"
                 "academic metros",
        som_share=0.05,
        som_note="EyeCare Partners / retina consolidators class — "
                 "mid-wave consolidation",
        horizon_years=5,
        basis_note="Template defaults from AAO/MGMA public data — "
                   "replace with engagement data before IC use.",
    )


def rcm_services_template() -> TamSamModel:
    """Revenue-cycle management services sizing — the meta-vertical:
    THIS platform's own industry. HFMA/CAQH-anchored."""
    return TamSamModel(
        name="RCM services · revenue cycle outsourcing market",
        chain=[
            DriverStep("US provider net patient revenue",
                       2_600_000_000_000, op="base", unit="$",
                       source="CMS NHE provider lines (hospital + "
                              "physician + post-acute)"),
            DriverStep("% of NPR spent on revenue cycle", 0.04,
                       op="rate", unit="of NPR",
                       source="HFMA cost-to-collect benchmarks "
                              "(3–5%)"),
            DriverStep("% outsourced (vs in-house)", 0.30, op="rate",
                       unit="of RC spend",
                       source="industry surveys — outsourcing "
                              "penetration still climbing"),
        ],
        segments=[
            Segment("End-to-end RCM outsourcing", 0.40, None,
                    note="the platform deals — R1/Ensemble class",
                    growth_pct=8.0),
            Segment("Point solutions (coding, denials, AR)", 0.35,
                    None, note="the tuck-in layer", growth_pct=6.0),
            Segment("Tech-enabled / AI workflow", 0.25, None,
                    note="the rerating layer — automation captures "
                         "the labor arbitrage", growth_pct=12.0),
        ],
        growth_drivers=[
            GrowthDriver("Outsourcing penetration", 4.0,
                         "labor scarcity pushes RC functions out"),
            GrowthDriver("Denial complexity growth", 2.5,
                         "payer friction RISES — bad for providers, "
                         "good for RCM vendors"),
            GrowthDriver("AI automation capture", 2.0,
                         "automation margin accrues to vendors who "
                         "own the workflow"),
            GrowthDriver("Pricing pressure / rebids", -2.0,
                         "contract rebids compress take rates"),
            GrowthDriver("In-sourcing reversals", -1.0,
                         "systems pulling RC back in-house after "
                         "vendor failures — churn risk"),
        ],
        sam_share=0.55,
        sam_note="Mid-market + regional provider segment (the mega-"
                 "systems negotiate direct)",
        som_share=0.04,
        som_note="R1 + Ensemble + Optum hold the megadeals; the "
                 "middle market is open",
        horizon_years=5,
        basis_note="Template defaults from HFMA/CAQH public data — "
                   "replace with engagement data before IC use.",
    )


def cardiology_template() -> TamSamModel:
    """Cardiology practice sizing — the current PPM wave, standalone
    depth. ACC-anchored."""
    return TamSamModel(
        name="Cardiology · practice + ancillary market",
        chain=[
            DriverStep("US cardiologists (practicing)", 33_000,
                       op="base", unit="physicians",
                       source="ACC workforce census"),
            DriverStep("Avg revenue per cardiologist", 1_400_000,
                       op="price", unit="$/MD/yr",
                       source="MGMA cardiology medians incl. imaging "
                              "+ ASC/OBL ancillaries"),
        ],
        segments=[
            Segment("Clinical / E&M base", 0.40, None, growth_pct=3.0),
            Segment("Imaging (echo, nuclear, CTA)", 0.25, None,
                    note="the in-office ancillary engine",
                    growth_pct=5.0),
            Segment("ASC/OBL procedures (PCI, EP)", 0.20, None,
                    note="the thesis layer — CMS added PCI to ASC "
                         "list; OBL economics", growth_pct=11.0),
            Segment("Device clinic / remote monitoring", 0.15, None,
                    growth_pct=7.0),
        ],
        growth_drivers=[
            GrowthDriver("CV disease demographics", 3.0,
                         "prevalence compounds with age + obesity"),
            GrowthDriver("Site-of-care shift (ASC/OBL)", 3.5,
                         "PCI/EP migrating out of HOPD — the wave's "
                         "engine"),
            GrowthDriver("Remote monitoring expansion", 1.5,
                         "RPM/device-clinic recurring revenue"),
            GrowthDriver("Hospital employment gravity", -2.0,
                         "~80% of cardiologists already hospital-"
                         "employed — the acquirable pool shrinks"),
            GrowthDriver("Fee-schedule pressure", -1.0,
                         "PFS conversion-factor cuts"),
        ],
        sam_share=0.20,
        sam_note="The ~20% still-independent pool + employed groups "
                 "that can be lifted out — honestly small",
        som_share=0.06,
        som_note="CVAUSA/Novocardia-class platforms in the land-grab "
                 "phase of a SHRINKING independent pool",
        horizon_years=5,
        basis_note="Template defaults from ACC/MGMA public data — "
                   "replace with engagement data before IC use.",
    )



def gastroenterology_template() -> TamSamModel:
    """GI practice sizing — the screening-annuity specialty. ACG-anchored."""
    return TamSamModel(
        name="Gastroenterology · practice + ASC market",
        chain=[
            DriverStep("US gastroenterologists (practicing)", 16_000,
                       op="base", unit="physicians",
                       source="ACG / AGA workforce census"),
            DriverStep("Avg revenue per gastroenterologist",
                       1_350_000, op="price", unit="$/MD/yr",
                       source="MGMA GI medians incl. ASC + anesthesia "
                              "+ pathology ancillaries"),
        ],
        segments=[
            Segment("Screening colonoscopy", 0.40, None,
                    note="the annuity — USPSTF age-45 start widened "
                         "the funnel by ~20M people", growth_pct=5.0),
            Segment("Diagnostic / therapeutic endo", 0.25, None,
                    growth_pct=4.0),
            Segment("Clinical (IBD, hepatology)", 0.20, None,
                    note="biologics-era complexity — infusion "
                         "adjacency", growth_pct=6.0),
            Segment("Ancillaries (path, anesthesia)", 0.15, None,
                    note="payer scrutiny on company-model anesthesia",
                    growth_pct=3.0),
        ],
        growth_drivers=[
            GrowthDriver("Age-45 screening expansion", 3.5,
                         "the USPSTF change is a structural volume "
                         "step-up still being absorbed"),
            GrowthDriver("Demographics", 2.0,
                         "polyp surveillance compounds"),
            GrowthDriver("ASC migration", 1.5,
                         "endo units shifting from HOPD"),
            GrowthDriver("Non-invasive screening substitution", -2.0,
                         "Cologuard/blood-based tests divert average-"
                         "risk volume — THE bear case, shown as one"),
            GrowthDriver("Anesthesia economics scrutiny", -1.0,
                         "payers attacking the company model"),
        ],
        sam_share=0.45,
        sam_note="Independent GI groups + ASC co-ownership",
        som_share=0.05,
        som_note="GI Alliance class — mid-wave; the Cologuard question "
                 "hangs over every IC",
        horizon_years=5,
        basis_note="Template defaults from ACG/MGMA public data — "
                   "replace with engagement data before IC use.",
    )


def orthopedics_template() -> TamSamModel:
    """Ortho practice sizing — the MSK platform wave. AAOS-anchored."""
    return TamSamModel(
        name="Orthopedics · MSK platform market",
        chain=[
            DriverStep("US orthopedic surgeons (practicing)", 31_000,
                       op="base", unit="physicians",
                       source="AAOS census"),
            DriverStep("Avg revenue per orthopedic surgeon",
                       1_600_000, op="price", unit="$/MD/yr",
                       source="MGMA ortho medians incl. ASC + imaging "
                              "+ PT + bracing ancillaries"),
        ],
        segments=[
            Segment("Total joints (hip/knee)", 0.30, None,
                    note="the ASC-migration engine — CMS list "
                         "additions made it investable",
                    growth_pct=8.0),
            Segment("Sports / arthroscopy", 0.25, None, growth_pct=5.0),
            Segment("Spine", 0.20, None,
                    note="highest revenue per case; UM-heavy",
                    growth_pct=4.0),
            Segment("Hand / foot / trauma", 0.15, None, growth_pct=3.0),
            Segment("Ancillaries (PT, imaging, DME)", 0.10, None,
                    note="the integration capture", growth_pct=6.0),
        ],
        growth_drivers=[
            GrowthDriver("Joint-replacement demographics", 4.0,
                         "active boomers — TJA volume projections "
                         "compound through 2035"),
            GrowthDriver("ASC migration of TJA", 3.0,
                         "site-shift economics: the wave's engine"),
            GrowthDriver("Ancillary integration", 1.5,
                         "PT/imaging/DME capture per episode"),
            GrowthDriver("Bundled-payment risk", -1.5,
                         "CMMI mandatory bundles squeeze episode "
                         "economics"),
            GrowthDriver("Implant cost inflation", -1.0,
                         "device pricing against fixed bundles"),
        ],
        sam_share=0.45,
        sam_note="Independent ortho groups in ASC-favorable states",
        som_share=0.04,
        som_note="OrthoAlliance/US Orthopaedic Partners class — "
                 "early-to-mid wave",
        horizon_years=5,
        basis_note="Template defaults from AAOS/MGMA public data — "
                   "replace with engagement data before IC use.",
    )


def womens_health_template() -> TamSamModel:
    """OBGYN / women's health sizing — ACOG-anchored."""
    return TamSamModel(
        name="Women's health · OBGYN practice market",
        chain=[
            DriverStep("US OBGYNs (practicing)", 42_000, op="base",
                       unit="physicians", source="ACOG workforce"),
            DriverStep("Avg revenue per OBGYN", 850_000, op="price",
                       unit="$/MD/yr",
                       source="MGMA OBGYN medians incl. office "
                              "procedures + ultrasound"),
        ],
        segments=[
            Segment("Obstetrics", 0.40, None,
                    note="volume anchor — but births declining; "
                         "malpractice cost the structural drag",
                    growth_pct=1.0),
            Segment("Gynecology / office procedures", 0.30, None,
                    growth_pct=4.0),
            Segment("Fertility adjacency / REI referral", 0.15, None,
                    note="the growth bridge to the IVF vertical",
                    growth_pct=9.0),
            Segment("Menopause / midlife (cash + Rx)", 0.15, None,
                    note="the re-emerging category — HRT renaissance",
                    growth_pct=8.0),
        ],
        growth_drivers=[
            GrowthDriver("Gyn / midlife demand", 3.0,
                         "menopause care renaissance + procedural gyn"),
            GrowthDriver("Fertility referral economics", 1.5,
                         "REI integration captures the IVF funnel"),
            GrowthDriver("Birth-rate decline", -1.5,
                         "OB volume shrinks slowly — the demographic "
                         "headwind, shown as one"),
            GrowthDriver("Malpractice premium inflation", -1.5,
                         "OB coverage cost is the margin drag"),
            GrowthDriver("Hospital employment gravity", -1.0,
                         "OB call coverage pushes employment"),
        ],
        sam_share=0.40,
        sam_note="Independent OBGYN groups + gyn-focused practices "
                 "(hospital-employed OB excluded)",
        som_share=0.04,
        som_note="Unified/Together Women's Health class — early wave",
        horizon_years=5,
        basis_note="Template defaults from ACOG/MGMA public data — "
                   "replace with engagement data before IC use.",
    )



def podiatry_template() -> TamSamModel:
    """Podiatry sizing — the diabetic-foot annuity niche. APMA-anchored."""
    return TamSamModel(
        name="Podiatry · foot & ankle practice market",
        chain=[
            DriverStep("US podiatrists (practicing)", 18_000, op="base",
                       unit="DPMs", source="APMA workforce"),
            DriverStep("Avg revenue per podiatrist", 550_000,
                       op="price", unit="$/DPM/yr",
                       source="MGMA/PMNews podiatry medians incl. "
                              "in-office ancillaries"),
        ],
        segments=[
            Segment("Diabetic foot / wound", 0.35, None,
                    note="the recurring-care annuity — ties to the "
                         "wound-care vertical", growth_pct=6.0),
            Segment("Surgical (bunion, ankle)", 0.25, None,
                    note="lapiplasty-era cash+ASC upside",
                    growth_pct=5.0),
            Segment("Routine / nail care", 0.20, None, growth_pct=2.0),
            Segment("Orthotics / DME dispensing", 0.12, None,
                    growth_pct=4.0),
            Segment("Sports / pediatric", 0.08, None, growth_pct=5.0),
        ],
        growth_drivers=[
            GrowthDriver("Diabetes prevalence", 4.0,
                         "diabetic foot care compounds with the "
                         "diabetes curve"),
            GrowthDriver("Surgical innovation adoption", 1.5,
                         "minimally-invasive bunion era lifts case "
                         "values"),
            GrowthDriver("Routine-care fee pressure", -1.5,
                         "Medicare routine foot-care restrictions"),
            GrowthDriver("DPM pipeline constraint", -1.0,
                         "podiatry school enrollment flat"),
        ],
        sam_share=0.50,
        sam_note="Independent DPM practices in diabetic-dense metros",
        som_share=0.04,
        som_note="Foot & Ankle Specialists class — early consolidation",
        horizon_years=5,
        basis_note="Template defaults from APMA/MGMA public data — "
                   "replace with engagement data before IC use.",
    )


def ent_allergy_template() -> TamSamModel:
    """ENT + allergy sizing — the office-procedure migration niche."""
    return TamSamModel(
        name="ENT & allergy · practice market",
        chain=[
            DriverStep("US otolaryngologists + allergists", 16_500,
                       op="base", unit="physicians",
                       source="AAO-HNS + AAAAI workforce"),
            DriverStep("Avg revenue per physician", 950_000,
                       op="price", unit="$/MD/yr",
                       source="MGMA ENT/allergy medians incl. CT, "
                              "audiology, allergy extracts"),
        ],
        segments=[
            Segment("General ENT / sinus", 0.35, None,
                    note="balloon sinuplasty moved to the office — "
                         "the site-shift template", growth_pct=5.0),
            Segment("Allergy / immunotherapy", 0.25, None,
                    note="extract economics — the recurring annuity",
                    growth_pct=6.0),
            Segment("Audiology / hearing aids", 0.20, None,
                    note="OTC hearing-aid disruption on the retail "
                         "layer", growth_pct=2.0),
            Segment("Head & neck / complex", 0.20, None,
                    growth_pct=3.0),
        ],
        growth_drivers=[
            GrowthDriver("Office-procedure migration", 3.0,
                         "sinuplasty/turbinate work at office rates"),
            GrowthDriver("Allergy prevalence", 2.0,
                         "environmental allergy burden rising"),
            GrowthDriver("Biologics adjacency", 1.5,
                         "asthma/CRSwNP biologics infusion capture"),
            GrowthDriver("OTC hearing-aid substitution", -1.5,
                         "the audiology retail layer erodes — shown "
                         "as one"),
            GrowthDriver("Prior-auth burden", -1.0,
                         "imaging + biologics UM"),
        ],
        sam_share=0.50,
        sam_note="Independent ENT/allergy groups (academic head & "
                 "neck excluded)",
        som_share=0.04,
        som_note="ENT Partners-class platforms early; allergy roll-ups "
                 "(AllerVie) mid-wave",
        horizon_years=5,
        basis_note="Template defaults from AAO-HNS/AAAAI/MGMA public "
                   "data — replace with engagement data before IC use.",
    )


def anesthesia_template() -> TamSamModel:
    """Anesthesia services sizing — the staffing-economics niche after
    the NSA reset. ASA-anchored."""
    return TamSamModel(
        name="Anesthesia · physician services market",
        chain=[
            DriverStep("US anesthesia cases / yr", 60_000_000,
                       op="base", unit="cases",
                       source="ASA / claims-volume estimates "
                              "(surgical + endo + OB)"),
            DriverStep("Avg revenue per case", 420, op="price",
                       unit="$/case",
                       source="blended commercial + Medicare unit "
                              "values (post-No Surprises reset)"),
        ],
        segments=[
            Segment("Hospital contracts (subsidy-backed)", 0.50, None,
                    note="stipends now fund most contracts — the "
                         "subsidy negotiation IS the business",
                    growth_pct=4.0),
            Segment("ASC / office-based", 0.30, None,
                    note="the growth setting — follows the surgical "
                         "migration", growth_pct=7.0),
            Segment("OB / trauma / call coverage", 0.20, None,
                    growth_pct=3.0),
        ],
        growth_drivers=[
            GrowthDriver("Surgical volume growth", 2.5,
                         "cases compound with demographics + ASC "
                         "expansion"),
            GrowthDriver("Subsidy repricing", 3.0,
                         "hospital stipends re-rate upward on "
                         "scarcity — the post-2021 structural shift"),
            GrowthDriver("CRNA leverage models", 1.0,
                         "care-team ratios expand capacity"),
            GrowthDriver("No Surprises Act rate reset", -2.5,
                         "out-of-network arbitrage is DEAD — the "
                         "old PE playbook does not work; shown as "
                         "the defining headwind"),
            GrowthDriver("Clinician scarcity cost", -2.0,
                         "anesthesiologist/CRNA wage inflation"),
        ],
        sam_share=0.45,
        sam_note="Independent groups + ASC-focused platforms "
                 "(academic + employed excluded)",
        som_share=0.05,
        som_note="Post-Envision/USAP era: the playbook is subsidy "
                 "economics, not OON billing",
        horizon_years=5,
        basis_note="Template defaults from ASA/CMS public data — "
                   "replace with engagement data before IC use. NOTE: "
                   "the NSA driver encodes why the 2010s anesthesia "
                   "playbook failed.",
    )



def home_care_template() -> TamSamModel:
    """Non-medical home care (private duty) sizing — the personal-care
    layer under home health. HCAOA-anchored."""
    return TamSamModel(
        name="Home care · non-medical personal care market",
        chain=[
            DriverStep("US seniors needing ADL support at home",
                       12_000_000, op="base", unit="seniors",
                       source="HHS/ASPE LTSS need estimates"),
            DriverStep("% receiving PAID home care", 0.30, op="rate",
                       unit="of those in need",
                       source="family caregiving fills the rest — the "
                              "paid-penetration gap is the demand "
                              "reservoir"),
            DriverStep("Avg paid hours / wk", 20, op="mult",
                       unit="hrs/wk", source="HCAOA utilization norms"),
            DriverStep("Weeks served / yr", 48, op="mult",
                       unit="wks/yr", source="industry standard"),
            DriverStep("Avg bill rate / hr", 32, op="price",
                       unit="$/hr",
                       source="HCAOA rate surveys (private pay) × "
                              "Medicaid HCBS blend"),
        ],
        segments=[
            Segment("Private pay", 0.45, None,
                    note="the margin segment — rate-taking power",
                    growth_pct=6.0),
            Segment("Medicaid HCBS / waivers", 0.40, None,
                    note="the volume segment — state rate-setting",
                    growth_pct=5.0),
            Segment("VA / other government", 0.10, None,
                    growth_pct=7.0),
            Segment("LTC insurance", 0.05, None,
                    note="a shrinking funding source", growth_pct=-1.0),
        ],
        growth_drivers=[
            GrowthDriver("Aging-in-place demand", 4.5,
                         "the 85+ cohort doubles by 2035; everyone "
                         "prefers home"),
            GrowthDriver("HCBS funding expansion", 2.0,
                         "states rebalancing LTSS away from "
                         "institutions"),
            GrowthDriver("Caregiver wage inflation", -2.5,
                         "the caregiver IS the product — wage "
                         "pass-through compresses margin"),
            GrowthDriver("Caregiver supply ceiling", -2.0,
                         "recruiting/turnover (~65%+) caps served "
                         "hours — the binding constraint"),
        ],
        sam_share=0.50,
        sam_note="Metro private-pay + managed-HCBS markets",
        som_share=0.03,
        som_note="Home Instead/Honor + franchise systems — the "
                 "largest holds <3%",
        horizon_years=5,
        basis_note="Template defaults from HHS/HCAOA public data — "
                   "replace with engagement data before IC use.",
    )


def pace_template() -> TamSamModel:
    """PACE program sizing — capitated frail-elderly care. NPA-anchored."""
    return TamSamModel(
        name="PACE · program of all-inclusive care market",
        chain=[
            DriverStep("US PACE participants", 80_000, op="base",
                       unit="participants",
                       source="National PACE Association census"),
            DriverStep("Avg capitation per participant / yr", 95_000,
                       op="price", unit="$/participant/yr",
                       source="Medicare + Medicaid dual capitation "
                              "(NPA rate norms)"),
        ],
        segments=[
            Segment("Nonprofit legacy programs", 0.60, None,
                    note="the installed base — conversion candidates",
                    growth_pct=6.0),
            Segment("For-profit operators", 0.40, None,
                    note="InnovAge-class — the investable layer; "
                         "compliance is the license to grow",
                    growth_pct=12.0),
        ],
        growth_drivers=[
            GrowthDriver("Eligible-population growth", 4.0,
                         "nursing-home-eligible duals compound with "
                         "the 85+ wave"),
            GrowthDriver("State PACE expansion", 5.0,
                         "new states + service-area expansions — the "
                         "regulatory growth gate"),
            GrowthDriver("Penetration of eligibles", 3.0,
                         "PACE serves <10% of eligibles — the "
                         "whitespace"),
            GrowthDriver("Compliance / audit risk", -3.0,
                         "CMS sanctions halt enrollment (the InnovAge "
                         "lesson) — growth is a privilege revoked on "
                         "audit failure"),
            GrowthDriver("Capitation rate risk", -1.0,
                         "state Medicaid rate-setting cycles"),
        ],
        sam_share=0.40,
        sam_note="For-profit-permitted states with expansion-friendly "
                 "agencies",
        som_share=0.10,
        som_note="A concentrated niche — single programs are "
                 "city-scale",
        horizon_years=5,
        basis_note="Template defaults from NPA public data — replace "
                   "with engagement data before IC use. The InnovAge "
                   "sanction history is the cautionary case study.",
    )


def teleradiology_template() -> TamSamModel:
    """Teleradiology sizing — the read-capacity arbitrage on the
    radiologist shortage. ACR-anchored."""
    return TamSamModel(
        name="Teleradiology · remote reads market",
        chain=[
            DriverStep("US imaging studies needing interpretation",
                       650_000_000, op="base", unit="studies/yr",
                       source="ACR / IMV volume estimates"),
            DriverStep("% read via teleradiology", 0.12, op="rate",
                       unit="of studies",
                       source="industry estimates — overnight + "
                              "overflow + rural coverage"),
            DriverStep("Avg revenue per read", 22, op="price",
                       unit="$/read",
                       source="per-click professional-fee splits "
                              "(modality-blended)"),
        ],
        segments=[
            Segment("Overnight / nighthawk", 0.40, None,
                    note="the original franchise — commoditized",
                    growth_pct=3.0),
            Segment("Daytime overflow / SLA reads", 0.35, None,
                    note="the growth layer — staffing gaps made "
                         "daytime the new market", growth_pct=9.0),
            Segment("Subspecialty (neuro, MSK, peds)", 0.20, None,
                    note="the premium layer", growth_pct=8.0),
            Segment("AI-assisted triage adjacency", 0.05, None,
                    growth_pct=12.0),
        ],
        growth_drivers=[
            GrowthDriver("Radiologist shortage", 4.0,
                         "vacancy rates at record highs — demand for "
                         "remote capacity is structural"),
            GrowthDriver("Imaging volume growth", 2.5,
                         "scans compound with demographics"),
            GrowthDriver("AI productivity capture", 1.5,
                         "AI triage lifts reads/radiologist — accrues "
                         "to platforms that own workflow"),
            GrowthDriver("Per-click fee compression", -2.0,
                         "commoditized nighthawk pricing — the "
                         "chronic headwind"),
            GrowthDriver("In-group recapture", -1.0,
                         "radiology groups building internal remote "
                         "pods claw volume back"),
        ],
        sam_share=0.60,
        sam_note="Hospital + imaging-center outsourced reads "
                 "(in-group remote excluded)",
        som_share=0.06,
        som_note="vRad/RP-class platforms hold meaningful share of "
                 "nighthawk; daytime is open",
        horizon_years=5,
        basis_note="Template defaults from ACR/IMV public data — "
                   "replace with engagement data before IC use.",
    )



def correctional_health_template() -> TamSamModel:
    """Correctional healthcare sizing — the contracted-government
    niche. BJS-anchored."""
    return TamSamModel(
        name="Correctional health · contracted care market",
        chain=[
            DriverStep("US incarcerated population", 1_900_000,
                       op="base", unit="individuals",
                       source="BJS (prisons + jails ADP)"),
            DriverStep("% under contracted (outsourced) care", 0.55,
                       op="rate", unit="of population",
                       source="industry estimates — the rest is "
                              "county/state-employed"),
            DriverStep("Avg healthcare spend per person / yr", 7_500,
                       op="price", unit="$/person/yr",
                       source="Pew/Vera per-capita correctional "
                              "health studies"),
        ],
        segments=[
            Segment("State prison systems", 0.45, None,
                    note="multi-year contracts; rebid risk "
                         "concentrated", growth_pct=3.0),
            Segment("County jails", 0.35, None,
                    note="the fragmented layer — higher churn, "
                         "higher margin", growth_pct=4.0),
            Segment("Behavioral / MAT programs", 0.15, None,
                    note="the growth mandate — litigation-driven "
                         "standards", growth_pct=9.0),
            Segment("Telehealth / specialty in-reach", 0.05, None,
                    growth_pct=10.0),
        ],
        growth_drivers=[
            GrowthDriver("Acuity / aging census", 3.0,
                         "the incarcerated population ages faster "
                         "than it shrinks"),
            GrowthDriver("Litigation-driven standards", 2.5,
                         "consent decrees force spending floors — "
                         "court orders are the rate escalator"),
            GrowthDriver("MAT / behavioral mandates", 2.0,
                         "opioid-treatment requirements expand scope"),
            GrowthDriver("Population decline", -1.5,
                         "decarceration trends shrink the census — "
                         "shown as one"),
            GrowthDriver("Headline / litigation risk", -1.5,
                         "mortality lawsuits are the existential "
                         "operator risk — priced, not hidden"),
        ],
        sam_share=0.55,
        sam_note="Outsourcing-friendly states + county consortia",
        som_share=0.08,
        som_note="Wellpath/YesCare/Centurion concentrated — rebids "
                 "move share in blocks",
        horizon_years=5,
        basis_note="Template defaults from BJS/Pew/Vera public data — "
                   "replace with engagement data before IC use. The "
                   "litigation-risk driver is the diligence centerpiece "
                   "in this vertical.",
    )


def locum_staffing_template() -> TamSamModel:
    """Locum tenens / physician staffing sizing — the scarcity
    arbitrage. SIA-anchored."""
    return TamSamModel(
        name="Locum tenens · physician staffing market",
        chain=[
            DriverStep("US physician FTE-days unfilled / yr",
                       9_000_000, op="base", unit="FTE-days",
                       source="SIA healthcare staffing reports + "
                              "vacancy-rate estimates"),
            DriverStep("% filled via locums agencies", 0.35, op="rate",
                       unit="of unfilled days",
                       source="SIA (vs internal float/overtime)"),
            DriverStep("Avg agency revenue per filled day", 1_900,
                       op="price", unit="$/day",
                       source="bill-rate benchmarks (specialty-"
                              "blended, incl. malpractice + travel)"),
        ],
        segments=[
            Segment("Hospitalist / IM / FM", 0.30, None,
                    growth_pct=4.0),
            Segment("Behavioral health / psych", 0.25, None,
                    note="the deepest shortage — rates re-rate "
                         "fastest", growth_pct=9.0),
            Segment("Surgical / anesthesia", 0.25, None,
                    growth_pct=5.0),
            Segment("Advanced practice (NP/PA)", 0.20, None,
                    note="the leverage layer", growth_pct=7.0),
        ],
        growth_drivers=[
            GrowthDriver("Physician shortage structural", 4.0,
                         "AAMC projects 86K-physician shortfall by "
                         "2036 — scarcity is the product"),
            GrowthDriver("Rural / safety-net dependence", 2.0,
                         "rural facilities run on locums permanently"),
            GrowthDriver("Bill-rate inflation", 2.0,
                         "scarcity pricing"),
            GrowthDriver("Hospital cost crackdowns", -3.0,
                         "the travel-nurse whiplash precedent: "
                         "systems slash agency spend the moment "
                         "census normalizes — the cyclical bear case"),
            GrowthDriver("Direct-sourcing platforms", -1.5,
                         "hospitals building internal float pools + "
                         "tech disintermediation"),
        ],
        sam_share=0.60,
        sam_note="Acute + behavioral demand ex the self-staffed "
                 "mega-systems",
        som_share=0.05,
        som_note="CHG/AMN/Medicus class hold the brand layer; "
                 "specialty boutiques are the targets",
        horizon_years=5,
        basis_note="Template defaults from SIA/AAMC public data — "
                   "replace with engagement data before IC use. The "
                   "travel-nurse whiplash is the cycle lesson priced "
                   "into the headwind.",
    )


def crisis_services_template() -> TamSamModel:
    """Behavioral crisis services sizing — the 988-era build-out.
    SAMHSA-anchored."""
    return TamSamModel(
        name="Crisis services · behavioral crisis continuum market",
        chain=[
            DriverStep("US behavioral crisis episodes / yr",
                       15_000_000, op="base", unit="episodes",
                       source="SAMHSA + 988 contact volumes + ED "
                              "psych-boarding estimates"),
            DriverStep("% reaching a funded crisis service", 0.25,
                       op="rate", unit="of episodes",
                       source="the access gap — most crises still "
                              "land in EDs/police; the buildout IS "
                              "the market"),
            DriverStep("Avg revenue per served episode", 1_400,
                       op="price", unit="$/episode",
                       source="mobile-crisis + stabilization per-"
                              "episode rates (Medicaid crisis codes)"),
        ],
        segments=[
            Segment("Crisis stabilization units", 0.40, None,
                    note="the facility layer — 23-hour + short-stay",
                    growth_pct=10.0),
            Segment("Mobile crisis teams", 0.30, None,
                    note="the Medicaid-mandated growth layer",
                    growth_pct=12.0),
            Segment("Crisis lines / 988 operations", 0.20, None,
                    note="contract-funded; rebid risk", growth_pct=6.0),
            Segment("Post-crisis stepdown", 0.10, None,
                    growth_pct=8.0),
        ],
        growth_drivers=[
            GrowthDriver("988 / crisis-system buildout", 6.0,
                         "federal + state crisis infrastructure "
                         "funding wave"),
            GrowthDriver("Medicaid crisis-benefit mandates", 3.0,
                         "ARPA mobile-crisis option + state plan "
                         "amendments"),
            GrowthDriver("ED-diversion economics", 2.0,
                         "payers fund alternatives to $2K psych "
                         "boarding"),
            GrowthDriver("Grant-funding cliff risk", -3.0,
                         "buildout dollars are appropriations-"
                         "dependent — the sustainability question, "
                         "priced"),
            GrowthDriver("Workforce scarcity", -2.0,
                         "crisis clinicians are the binding "
                         "constraint"),
        ],
        sam_share=0.45,
        sam_note="States with Medicaid crisis benefits + managed-care "
                 "carve-ins",
        som_share=0.05,
        som_note="An emerging market — Connections/RI International "
                 "class early",
        horizon_years=5,
        basis_note="Template defaults from SAMHSA/988 public data — "
                   "replace with engagement data before IC use.",
    )



def school_services_template() -> TamSamModel:
    """School-based therapy services sizing — the IDEA-funded niche.
    NCES-anchored."""
    return TamSamModel(
        name="School services · special-education therapy market",
        chain=[
            DriverStep("US students with IEPs", 7_500_000, op="base",
                       unit="students", source="NCES (15% of K-12)"),
            DriverStep("% receiving related services (OT/PT/SLP/"
                       "psych)", 0.45, op="rate", unit="of IEP students",
                       source="IDEA Part B service-category data"),
            DriverStep("Avg outsourced spend per served student / yr",
                       2_400, op="price", unit="$/student/yr",
                       source="district contract benchmarks (staffing "
                              "+ teletherapy blend)"),
        ],
        segments=[
            Segment("Speech-language pathology", 0.40, None,
                    note="the volume service — chronic SLP shortage",
                    growth_pct=6.0),
            Segment("OT / PT", 0.25, None, growth_pct=5.0),
            Segment("School psych / behavioral", 0.20, None,
                    note="the fastest-need line post-2020",
                    growth_pct=9.0),
            Segment("Teletherapy delivery", 0.15, None,
                    note="the margin model — solves rural coverage",
                    growth_pct=11.0),
        ],
        growth_drivers=[
            GrowthDriver("IEP identification growth", 2.5,
                         "autism + speech identification rates climb"),
            GrowthDriver("Therapist-shortage outsourcing", 3.0,
                         "districts can't hire — contracting IS the "
                         "growth"),
            GrowthDriver("Teletherapy normalization", 2.0,
                         "post-2020 acceptance unlocked rural IEPs"),
            GrowthDriver("District budget cyclicality", -2.0,
                         "ESSER cliff + local levies — the funding "
                         "headwind, shown as one"),
            GrowthDriver("Compliance / due-process exposure", -1.0,
                         "IDEA litigation drives service minutes but "
                         "punishes failures"),
        ],
        sam_share=0.50,
        sam_note="Districts that outsource (large urbans self-staff)",
        som_share=0.04,
        som_note="Presence/ProCare class — teletherapy reset the map",
        horizon_years=5,
        basis_note="Template defaults from NCES/IDEA public data — "
                   "replace with engagement data before IC use.",
    )


def mobile_diagnostics_template() -> TamSamModel:
    """Mobile diagnostics sizing — portable imaging/labs to the
    bedside. The SNF-service niche."""
    return TamSamModel(
        name="Mobile diagnostics · bedside imaging & labs market",
        chain=[
            DriverStep("US LTC/homebound diagnostic encounters / yr",
                       28_000_000, op="base", unit="encounters",
                       source="SNF census × imaging/lab order rates "
                              "(claims-based estimates)"),
            DriverStep("% served by mobile providers", 0.55, op="rate",
                       unit="of encounters",
                       source="vs transport-to-facility — mobile wins "
                              "on total-cost + resident burden"),
            DriverStep("Avg revenue per encounter", 95, op="price",
                       unit="$/encounter",
                       source="portable X-ray/ultrasound/EKG + "
                              "phlebotomy fee blend (Medicare Part B)"),
        ],
        segments=[
            Segment("Portable X-ray / ultrasound", 0.45, None,
                    note="the legacy core — TridentUSA history",
                    growth_pct=3.0),
            Segment("Mobile phlebotomy / labs", 0.30, None,
                    growth_pct=5.0),
            Segment("Home-based (HaH / SNF-at-home adjacency)",
                    0.15, None,
                    note="the growth format — follows care home",
                    growth_pct=10.0),
            Segment("Mobile echo / vascular / advanced", 0.10, None,
                    growth_pct=7.0),
        ],
        growth_drivers=[
            GrowthDriver("Care-at-home migration", 4.0,
                         "every HaH/SNF-at-home episode needs mobile "
                         "diagnostics"),
            GrowthDriver("Transport-cost avoidance", 2.0,
                         "ambulance transport for an X-ray costs 5× "
                         "the mobile visit"),
            GrowthDriver("Part B fee pressure", -1.5,
                         "portable-X-ray transportation-fee cuts — "
                         "the chronic headwind"),
            GrowthDriver("Tech route-density economics", -1.0,
                         "windshield time caps margin without "
                         "density"),
        ],
        sam_share=0.55,
        sam_note="SNF-dense + HaH-active metros where route density "
                 "works",
        som_share=0.06,
        som_note="Post-TridentUSA fragmentation — regional rebuild "
                 "opportunity",
        horizon_years=5,
        basis_note="Template defaults from CMS Part B/claims public "
                   "data — replace with engagement data before IC use.",
    )


def palliative_template() -> TamSamModel:
    """Community-based palliative care sizing — the pre-hospice
    layer. CAPC-anchored."""
    return TamSamModel(
        name="Palliative care · community-based market",
        chain=[
            DriverStep("US adults with serious illness (palliative-"
                       "appropriate)", 12_000_000, op="base",
                       unit="adults", source="CAPC prevalence"),
            DriverStep("% receiving community palliative care", 0.05,
                       op="rate", unit="of appropriate",
                       source="CAPC — hospital programs exist; "
                              "COMMUNITY delivery is nearly absent: "
                              "the gap is the market"),
            DriverStep("Avg revenue per patient / yr", 4_200,
                       op="price", unit="$/patient/yr",
                       source="MA supplemental + VBC PMPM + Part B "
                              "billing blend"),
        ],
        segments=[
            Segment("MA / VBC contracted (PMPM)", 0.50, None,
                    note="the scalable model — payers fund avoided "
                         "admissions", growth_pct=14.0),
            Segment("Hospice-adjacent (pre-hospice)", 0.30, None,
                    note="the referral bridge — hospices build it as "
                         "a feeder", growth_pct=8.0),
            Segment("FFS Part B (MD/NP visits)", 0.20, None,
                    note="the economics-poor legacy model",
                    growth_pct=2.0),
        ],
        growth_drivers=[
            GrowthDriver("Penetration of the eligible gap", 6.0,
                         "5% served → the whitespace is the thesis"),
            GrowthDriver("MA supplemental-benefit adoption", 4.0,
                         "plans add palliative benefits for the "
                         "avoided-admission math"),
            GrowthDriver("Hospice feeder economics", 2.0,
                         "earlier referral lifts hospice LOS — the "
                         "adjacency motive"),
            GrowthDriver("FFS economics weakness", -2.0,
                         "visit billing alone doesn't cover an IDT — "
                         "the model fails without VBC, shown as one"),
            GrowthDriver("Clinician scarcity", -1.5,
                         "palliative-trained NPs/MDs are scarce"),
        ],
        sam_share=0.50,
        sam_note="MA-dense markets with VBC-willing plans",
        som_share=0.05,
        som_note="An emerging market — no scaled pure-play yet",
        horizon_years=5,
        basis_note="Template defaults from CAPC public data — replace "
                   "with engagement data before IC use.",
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
    "infusion": infusion_template,
    "imaging": imaging_template,
    "physical_therapy": physical_therapy_template,
    "veterinary": veterinary_template,
    "medspa": medspa_template,
    "ems": ems_template,
    "clinical_labs": clinical_labs_template,
    "specialty_pharmacy": specialty_pharmacy_template,
    "vision": vision_template,
    "aba": aba_template,
    "plasma": plasma_template,
    "clinical_research": clinical_research_template,
    "wound_care": wound_care_template,
    "sleep": sleep_template,
    "occ_health": occ_health_template,
    "dermatology": dermatology_template,
    "pain_management": pain_management_template,
    "hospital_at_home": hospital_at_home_template,
    "ltc_pharmacy": ltc_pharmacy_template,
    "dme": dme_template,
    "idd_services": idd_services_template,
    "eating_disorders": eating_disorders_template,
    "nephrology": nephrology_template,
    "orthotics_prosthetics": orthotics_prosthetics_template,
    "ophthalmology": ophthalmology_template,
    "rcm_services": rcm_services_template,
    "cardiology": cardiology_template,
    "gastroenterology": gastroenterology_template,
    "orthopedics": orthopedics_template,
    "womens_health": womens_health_template,
    "podiatry": podiatry_template,
    "ent_allergy": ent_allergy_template,
    "anesthesia": anesthesia_template,
    "home_care": home_care_template,
    "pace": pace_template,
    "teleradiology": teleradiology_template,
    "correctional_health": correctional_health_template,
    "locum_staffing": locum_staffing_template,
    "crisis_services": crisis_services_template,
    "school_services": school_services_template,
    "mobile_diagnostics": mobile_diagnostics_template,
    "palliative": palliative_template,
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
        seg_tam = tam * s.share_of_volume
        g = s.growth_pct
        seg_rows.append({
            "name": s.name,
            "share_of_volume": s.share_of_volume,
            "tam_value": seg_tam,
            "success_rate": s.success_rate,
            "note": s.note,
            "growth_pct": g,
            "tam_y_final": (seg_tam * (1 + g / 100.0)
                            ** model.horizon_years
                            if g is not None else None),
        })
    if any(r["growth_pct"] is not None for r in seg_rows):
        fastest = max((r for r in seg_rows
                       if r["growth_pct"] is not None),
                      key=lambda r: r["growth_pct"])
        fastest["is_fastest"] = True

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
