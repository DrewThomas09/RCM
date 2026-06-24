"""Referring Radiology & Diagnostic Imaging — CMS Claims, Market & AI Atlas.

A single, in-depth reference surface for the US outpatient diagnostic-imaging
sector that a healthcare-PE partner uses to underwrite a radiology / imaging-
center platform. It fuses five normally-separate data layers into one page:

  1. **CMS claims atlas** — the radiology CPT/HCPCS code set a freestanding
     imaging center (IDTF) bills, with approximate CY2025 Medicare national
     allowables and the global / professional-26 / technical-TC split that
     drives a reads-vs-scans P&L.
  2. **Mammography & breast imaging** — 2D (digital) vs 3D (DBT / tomosynthesis)
     adoption, screening volume, MQSA-certified facility counts, and the 2024
     FDA breast-density notification rule.
  3. **CMS coverage connections** — a *loop* over an imaging-coverage topic
     registry that materialises one connection record per live NCD / LCD the
     platform tracks (Computed Tomography 220.1, MRI 220.2, LDCT lung screening
     210.14, PET-FDG 220.6.17, the CGS breast-imaging LCD L33950, the CCTA /
     cardiac-CT LCD family, …). Document IDs, display IDs, effective dates and
     URLs are the real values returned by the CMS Coverage API (Medicare
     Coverage Database) so the page links straight to the source policy.
  4. **MAC payer jurisdictions** — the seven Medicare Administrative Contractors
     that price Part-B imaging claims, mapped to the states (and therefore the
     counties) each one governs. This is the Medicare layer of "which payer
     pays for imaging in this county".
  5. **State + county data** — imaging-center density, MQSA facility counts,
     Medicare imaging spend and DBT penetration by state; payer-mix breakdown
     (Medicare / Medicaid / commercial / uninsured) for the largest counties in
     the main imaging states; the big freestanding operators (RadNet, RAYUS,
     SimonMed, Akumin, US Radiology, Solis); the AI-implementation landscape
     (FDA-cleared algorithms, vendors, reimbursement pathways); and the recent
     macro factors (PFS conversion-factor cuts, radiologist shortage, site-of-
     service shift, prior-auth / AUC, No Surprises Act).

Data provenance, stated honestly so the page never over-claims:
  * **Live / real**  — the NCD & LCD document IDs, display IDs, effective dates
    and MAC roster come from the CMS Coverage API (``mcp__CMS_Coverage`` /
    https://api.coverage.cms.gov) and the public MAC jurisdiction map.
  * **Approximate**  — CY2025 PFS allowables are national averages (the actual
    paid amount is GPCI-localized per locality); imaging-center counts, county
    payer-mix shares and operator center counts are sourced estimates drawn
    from public filings, FDA MQSA statistics and CMS utilization files, and are
    labelled as estimates in the UI. Nothing here is a contracted commercial
    rate.

Stdlib only (dataclasses + typing). No network call at render time — the CMS
document registry is a vendored snapshot of the API response so the page renders
air-gapped, consistent with the platform's no-egress render path.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


# ─────────────────────────────────────────────────────────────────────────────
# Dataclasses
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class ImagingCPTCode:
    """One billable radiology CPT/HCPCS line with its CY2025 economics.

    ``global_rate`` is the approximate national Medicare allowable when one
    entity owns the equipment AND reads the study (the freestanding-IDTF case).
    ``prof_26`` is the professional-component (modifier 26) read; ``tech_tc`` is
    the technical-component (modifier TC) scan. global ≈ prof_26 + tech_tc.
    """
    code: str
    modality: str
    descriptor: str
    category: str            # screening / diagnostic / interventional / screening-addon
    work_rvu: float
    global_rate: float       # approx CY2025 national allowable, global
    prof_26: float           # professional component (26)
    tech_tc: float           # technical component (TC)
    annual_medicare_vol_k: float   # approx Part-B volume, thousands of services
    notes: str = ""


@dataclass
class MammographyStat:
    metric: str
    value: str
    detail: str
    source: str


@dataclass
class CMSConnection:
    """One live Medicare coverage policy the imaging platform tracks.

    Materialised by the ``build_cms_connections`` loop over the imaging
    coverage-topic registry. IDs/dates are the real CMS Coverage API values.
    """
    topic: str
    doc_type: str            # NCD / LCD
    display_id: str          # e.g. 220.1 or L33950
    doc_id: int
    title: str
    contractor: str          # MAC name, or "National (all MACs)" for NCDs
    effective_date: str
    last_updated: str
    status: str              # active / retired
    url: str


@dataclass
class MACJurisdiction:
    mac_name: str
    jurisdiction: str        # e.g. "JE / JF"
    part_b_states: str
    state_count: int
    contract_records: int
    note: str = ""


@dataclass
class StateImagingProfile:
    state: str
    postal: str
    mac_name: str
    mac_jurisdiction: str
    imaging_centers: int          # approx freestanding diagnostic-imaging centers
    mqsa_facilities: int          # FDA-certified mammography facilities
    medicare_imaging_spend_mm: float   # approx annual Part-B imaging allowed $M
    util_per_1k_benes: float      # advanced-imaging events / 1,000 FFS benes
    dbt_penetration_pct: float    # share of mammography facilities with ≥1 DBT unit


@dataclass
class CountyPayerMix:
    county: str
    state: str
    fips: str
    population_k: float
    medicare_pct: float
    medicaid_pct: float
    commercial_pct: float
    uninsured_pct: float
    imaging_centers: int
    dominant_payer: str


@dataclass
class BigPlayer:
    name: str
    ownership: str
    sponsor: str
    centers: int
    footprint_states: str
    modalities: str
    ai_platform: str
    note: str


@dataclass
class AIImplementation:
    vendor: str
    product: str
    fda_status: str
    modality: str
    use_case: str
    reimbursement_path: str
    code: str
    adoption: str


@dataclass
class RecentFactor:
    factor: str
    category: str            # reimbursement / workforce / volume / policy / structure
    detail: str
    direction: str           # tailwind / headwind / mixed
    year: str


@dataclass
class PayerTypeShare:
    payer_type: str
    imaging_revenue_share_pct: float
    trend: str
    note: str


@dataclass
class ModalitySegment:
    """One imaging modality as its own economic unit."""
    modality: str
    us_market_bn: float           # approx US services market for the modality
    annual_volume_mm: float       # approx US studies/yr (millions)
    growth_pct: float             # approx volume CAGR
    avg_medicare_global: float    # representative global allowable per study
    equipment_capex_k: float      # approx capex per unit/room ($ thousands)
    gross_margin_pct: float       # representative center-level gross margin
    room_time_min: int            # typical scan room time (throughput driver)
    supply_exposure: str          # the key supply-chain dependency
    dynamics: str


@dataclass
class SupplyShock:
    """A supply disruption that hits imaging economics."""
    shock: str
    category: str                 # contrast / cryogen / isotope / equipment / labor
    mechanism: str
    peak_impact: str
    window: str
    exposure: str                 # which modality bears it
    mitigation: str
    severity: str                 # high / medium / low (recurrence-weighted)


@dataclass
class UnitEconomicLine:
    """One line of a representative freestanding multi-modality imaging-center P&L."""
    line_item: str
    pct_of_revenue: float         # share of net revenue (cost lines negative)
    per_scan: float               # approx $ per blended study
    note: str
    is_total: bool = False


@dataclass
class EconomicDriver:
    driver: str
    definition: str
    typical_value: str
    lever: str                    # why it moves the P&L


@dataclass
class RPDiligenceItem:
    category: str                 # scale / financials / capital / ownership / tele / ai / nsa
    metric: str
    value: str
    assessment: str               # the diligence read
    flag: str                     # positive / watch / risk


@dataclass
class AIBuildStage:
    stage: str
    description: str
    typical_cost: str
    typical_time: str
    key_risk: str


@dataclass
class AIBuildVsBuy:
    dimension: str
    build: str
    buy: str
    verdict: str


@dataclass
class RadiologyImagingResult:
    # headline KPIs
    market_size_bn: float
    freestanding_centers: int
    mqsa_facilities: int
    annual_mammograms_mm: float
    dbt_adoption_pct: float
    cpt_codes_tracked: int
    cms_connections: int
    ncd_count: int
    lcd_count: int
    mac_payers: int
    fda_ai_radiology_devices: int
    radiologist_shortage: int
    pfs_conversion_factor_2025: float
    # data tables
    cpt_codes: List[ImagingCPTCode]
    mammography_stats: List[MammographyStat]
    coverage_connections: List[CMSConnection]
    mac_jurisdictions: List[MACJurisdiction]
    state_profiles: List[StateImagingProfile]
    county_payer_mix: List[CountyPayerMix]
    big_players: List[BigPlayer]
    ai_implementations: List[AIImplementation]
    recent_factors: List[RecentFactor]
    payer_shares: List[PayerTypeShare]
    modality_segments: List[ModalitySegment]
    supply_shocks: List[SupplyShock]
    unit_economics: List[UnitEconomicLine]
    economic_drivers: List[EconomicDriver]
    rp_diligence: List[RPDiligenceItem]
    ai_build_stages: List[AIBuildStage]
    ai_build_vs_buy: List[AIBuildVsBuy]
    center_revenue_mm: float
    center_ebitda_margin_pct: float


# ─────────────────────────────────────────────────────────────────────────────
# 1) CMS CLAIMS ATLAS — radiology CPT/HCPCS codes (approx CY2025 PFS)
# ─────────────────────────────────────────────────────────────────────────────
# Rates are approximate CY2025 national Medicare allowables (final PFS CF =
# $32.2465); the paid amount is GPCI-localized per locality. global ≈ prof_26 +
# tech_tc. Mammography figures track the Hologic 2025 Coding Guide + state
# breast-cancer-program Medicare rate schedules (which republish CMS component
# splits). MPPR applies on a 2nd+ same-session study: −50% technical, −5%
# professional. In a hospital outpatient dept the technical component is paid
# under OPPS, not PFS — the radiologist bills only the -26 professional read.
def _build_cpt_codes() -> List[ImagingCPTCode]:
    return [
        # ── Mammography & breast (the referring-screening core) ──
        ImagingCPTCode("77067", "Mammography", "Screening mammography, bilateral (2-view), w/ CAD",
                       "screening", 0.70, 103.87, 28.55, 75.32, 8650.0,
                       "The screening workhorse; coinsurance & deductible waived as a preventive benefit."),
        ImagingCPTCode("77066", "Mammography", "Diagnostic mammography, bilateral",
                       "diagnostic", 0.87, 158.45, 46.60, 111.85, 3120.0,
                       "Ordered after an abnormal screen or symptom."),
        ImagingCPTCode("77065", "Mammography", "Diagnostic mammography, unilateral",
                       "diagnostic", 0.74, 125.16, 37.95, 87.21, 1180.0, ""),
        ImagingCPTCode("77063", "Mammography", "Screening digital breast tomosynthesis (DBT), bilateral — add-on",
                       "screening-addon", 0.60, 53.43, 27.86, 25.57, 6250.0,
                       "3D add-on to 77067; separately payable. The 2D→3D screening-upgrade economics."),
        ImagingCPTCode("G0279", "Mammography", "Diagnostic DBT add-on (HCPCS) to 77065/77066",
                       "diagnostic", 0.45, 44.36, 14.50, 29.86, 2240.0,
                       "Medicare's diagnostic-3D add-on. (CPT 77061/77062 are the AMA codes commercial payers use; Medicare requires G0279.)"),
        ImagingCPTCode("76641", "Ultrasound", "Breast ultrasound, complete (per breast)",
                       "diagnostic", 0.73, 123.65, 46.60, 77.05, 1320.0,
                       "Supplemental screen for dense-breast patients post density-notification rule."),
        # ── CT ──
        ImagingCPTCode("70450", "CT", "CT head/brain without contrast",
                       "diagnostic", 0.85, 145.00, 31.05, 113.95, 4850.0, ""),
        ImagingCPTCode("71250", "CT", "CT chest without contrast",
                       "diagnostic", 1.02, 131.00, 38.17, 92.83, 1860.0, ""),
        ImagingCPTCode("71260", "CT", "CT chest with contrast",
                       "diagnostic", 1.08, 185.00, 40.10, 144.90, 1420.0, ""),
        ImagingCPTCode("71271", "CT", "Low-dose CT lung cancer screening (LDCT)",
                       "screening", 1.02, 271.07, 38.17, 232.90, 480.0,
                       "Pairs with HCPCS G0296 shared-decision visit; NCD 210.14 eligibility (age 50-77, 20 pack-yrs, ABR-certified reader)."),
        ImagingCPTCode("74177", "CT", "CT abdomen & pelvis with contrast",
                       "diagnostic", 1.82, 280.00, 67.92, 212.08, 3960.0,
                       "One of the highest-volume advanced-imaging codes in Part B."),
        ImagingCPTCode("74176", "CT", "CT abdomen & pelvis without contrast",
                       "diagnostic", 1.74, 213.00, 65.01, 147.99, 1240.0, ""),
        ImagingCPTCode("72131", "CT", "CT lumbar spine without contrast",
                       "diagnostic", 0.98, 125.00, 40.75, 84.25, 690.0, ""),
        ImagingCPTCode("75574", "CT", "Coronary CT angiography (CCTA) w/ 3D",
                       "diagnostic", 2.36, 224.40, 88.13, 136.27, 320.0,
                       "Governed by the CCTA / cardiac-CT LCD family (L35121, L33947, L33423, L33559)."),
        # ── MRI ──
        ImagingCPTCode("70553", "MRI", "MRI brain without & with contrast",
                       "diagnostic", 2.29, 322.00, 100.00, 222.00, 2210.0, ""),
        ImagingCPTCode("70551", "MRI", "MRI brain without contrast",
                       "diagnostic", 1.48, 211.55, 55.30, 156.25, 1080.0, ""),
        ImagingCPTCode("72148", "MRI", "MRI lumbar spine without contrast",
                       "diagnostic", 1.48, 211.23, 55.30, 155.93, 3480.0,
                       "High-volume; a frequent prior-authorization (RBM) target."),
        ImagingCPTCode("73721", "MRI", "MRI lower-extremity joint without contrast",
                       "diagnostic", 1.35, 200.22, 50.44, 149.78, 2640.0, ""),
        # ── PET / nuclear ──
        ImagingCPTCode("78815", "PET/CT", "PET/CT skull-base to mid-thigh w/ concurrent CT",
                       "diagnostic", 2.20, 1450.00, 120.00, 1330.00, 540.0,
                       "Oncologic staging; NCD 220.6.17 (FDG) covers most solid tumors. Technical component is MAC/carrier-priced (~$1,300-1,700, locality-dependent); radiopharmaceutical billed separately."),
        ImagingCPTCode("78306", "Nuclear", "Bone scan, whole body",
                       "diagnostic", 0.86, 198.32, 26.20, 172.12, 410.0, ""),
        # ── X-ray / DXA (referring volume floor) ──
        ImagingCPTCode("71046", "X-ray", "Chest X-ray, 2 views",
                       "diagnostic", 0.22, 31.05, 9.06, 21.99, 9850.0,
                       "Highest-volume imaging code; low unit price, high throughput."),
        ImagingCPTCode("77080", "DXA", "DXA bone density, axial skeleton",
                       "screening", 0.20, 41.39, 8.41, 32.98, 2180.0,
                       "Osteoporosis screening; preventive frequency limits apply."),
    ]


# ─────────────────────────────────────────────────────────────────────────────
# 2) MAMMOGRAPHY & BREAST IMAGING
# ─────────────────────────────────────────────────────────────────────────────
def _build_mammography_stats() -> List[MammographyStat]:
    return [
        MammographyStat("MQSA-certified facilities", "~8,700",
                        "FDA-certified mammography facilities under the Mammography Quality Standards Act",
                        "FDA MQSA national statistics (2025)"),
        MammographyStat("Accredited mammography units", "~25,400",
                        "Total certified mammography machines across all facilities",
                        "FDA MQSA national statistics (2025)"),
        MammographyStat("Annual mammograms (US)", "~40M",
                        "Screening + diagnostic mammography studies performed per year",
                        "CDC / NCI estimate"),
        MammographyStat("Women 50-74 up-to-date on screening", "~76%",
                        "Share screened within the recommended interval",
                        "CDC BRFSS / Healthy People 2030"),
        MammographyStat("Facilities with ≥1 DBT (3D) unit", "~87%",
                        "Tomosynthesis is now the majority modality; pure-2D sites are a shrinking minority",
                        "FDA MQSA unit mix (2025 est.)"),
        MammographyStat("DBT (3D) share of certified units", "~58%",
                        "3D units as a share of all accredited mammography machines — past the 50% crossover",
                        "FDA MQSA unit mix (2025 est.)"),
        MammographyStat("Screening 2D reimbursement (77067)", "$134.86",
                        "Approx CY2025 Medicare national allowable, global; preventive — no patient cost-share",
                        "CMS PFS CY2025 (approx, national)"),
        MammographyStat("Screening 3D add-on (77063)", "+$56.28",
                        "Separately-payable DBT add-on — the per-study upgrade economics of a 2D→3D fleet",
                        "CMS PFS CY2025 (approx, national)"),
        MammographyStat("USPSTF screening age", "40-74, biennial",
                        "2024 USPSTF Grade B: start at 40 (lowered from 50), every other year",
                        "USPSTF 2024 final recommendation"),
        MammographyStat("FDA breast-density notification", "Effective Sep 9, 2024",
                        "MQSA final rule requires every mammography report to notify patients of dense vs not-dense breast tissue nationwide",
                        "FDA MQSA final rule (2023; in force 2024)"),
        MammographyStat("Breast-imaging LCD", "L33950 (CGS)",
                        "Mammography / breast echography / breast MRI / ductography — effective 2025-12-04, updated 2025-11-26",
                        "CMS Coverage API — live"),
    ]


# ─────────────────────────────────────────────────────────────────────────────
# 3) CMS COVERAGE CONNECTIONS — the loop down to specific NCDs / LCDs
# ─────────────────────────────────────────────────────────────────────────────
# Each entry is an imaging coverage topic. The loop in build_cms_connections
# materialises one CMSConnection per live Medicare policy document. Document
# IDs, display IDs, effective/updated dates and URLs are the real values
# returned by the CMS Coverage API (Medicare Coverage Database).
_IMAGING_COVERAGE_TOPICS: List[Dict] = [
    # ── National Coverage Determinations (apply to every MAC) ──
    {"topic": "Computed Tomography", "doc_type": "NCD", "display_id": "220.1",
     "doc_id": 176, "title": "Computed Tomography",
     "contractor": "National (all MACs)", "effective_date": "1979-08-17",
     "last_updated": "2023-08-17", "status": "active",
     "url": "https://www.cms.gov/medicare-coverage-database/view/ncd.aspx?ncdid=176"},
    {"topic": "Magnetic Resonance Imaging", "doc_type": "NCD", "display_id": "220.2",
     "doc_id": 177, "title": "Magnetic Resonance Imaging",
     "contractor": "National (all MACs)", "effective_date": "1985-11-22",
     "last_updated": "2024-12-03", "status": "active",
     "url": "https://www.cms.gov/medicare-coverage-database/view/ncd.aspx?ncdid=177"},
    {"topic": "Lung Cancer Screening (LDCT)", "doc_type": "NCD", "display_id": "210.14",
     "doc_id": 364, "title": "Lung Cancer Screening with Low Dose Computed Tomography (LDCT)",
     "contractor": "National (all MACs)", "effective_date": "2022-02-10",
     "last_updated": "2026-05-29", "status": "active",
     "url": "https://www.cms.gov/medicare-coverage-database/view/ncd.aspx?ncdid=364"},
    {"topic": "PET (FDG) — Oncologic", "doc_type": "NCD", "display_id": "220.6.17",
     "doc_id": 331, "title": "Positron Emission Tomography (FDG) for Oncologic Conditions",
     "contractor": "National (all MACs)", "effective_date": "2013-06-11",
     "last_updated": "2026-04-30", "status": "active",
     "url": "https://www.cms.gov/medicare-coverage-database/view/ncd.aspx?ncdid=331"},
    {"topic": "PET (NaF-18) — Bone Metastasis", "doc_type": "NCD", "display_id": "220.6.19",
     "doc_id": 336, "title": "Positron Emission Tomography (NaF-18) to Identify Bone Metastasis of Cancer",
     "contractor": "National (all MACs)", "effective_date": "2017-12-15",
     "last_updated": "2024-02-27", "status": "active",
     "url": "https://www.cms.gov/medicare-coverage-database/view/ncd.aspx?ncdid=336"},
    {"topic": "SPECT", "doc_type": "NCD", "display_id": "220.12",
     "doc_id": 271, "title": "Single Photon Emission Computed Tomography (SPECT)",
     "contractor": "National (all MACs)", "effective_date": "1995-01-01",
     "last_updated": "2020-06-12", "status": "active",
     "url": "https://www.cms.gov/medicare-coverage-database/view/ncd.aspx?ncdid=271"},
    {"topic": "Beta Amyloid PET (Dementia)", "doc_type": "NCD", "display_id": "220.6.20",
     "doc_id": 356, "title": "Beta Amyloid Positron Tomography in Dementia and Neurodegenerative Disease",
     "contractor": "National (all MACs)", "effective_date": "2013-09-27",
     "last_updated": "2025-11-19", "status": "retired",
     "url": "https://www.cms.gov/medicare-coverage-database/view/ncd.aspx?ncdid=356"},
    # ── Local Coverage Determinations (MAC-specific — the county-level payer rules) ──
    {"topic": "Breast Imaging / Mammography", "doc_type": "LCD", "display_id": "L33950",
     "doc_id": 33950, "title": "Breast Imaging Mammography/Breast Echography (Sonography)/Breast MRI/Ductography",
     "contractor": "CGS Administrators, LLC", "effective_date": "2025-12-04",
     "last_updated": "2025-11-26", "status": "active",
     "url": "https://www.cms.gov/medicare-coverage-database/view/lcd.aspx?lcdid=33950"},
    {"topic": "Coronary CT Angiography (CCTA)", "doc_type": "LCD", "display_id": "L35121",
     "doc_id": 35121, "title": "Coronary Computed Tomography Angiography (CCTA)",
     "contractor": "WPS Insurance Corporation", "effective_date": "2025-10-30",
     "last_updated": "2025-10-21", "status": "active",
     "url": "https://www.cms.gov/medicare-coverage-database/view/lcd.aspx?lcdid=35121"},
    {"topic": "Cardiac CT / CCTA", "doc_type": "LCD", "display_id": "L33947",
     "doc_id": 33947, "title": "Cardiac Computed Tomography (CCT) and Coronary Computed Tomography Angiography (CCTA)",
     "contractor": "CGS Administrators, LLC", "effective_date": "2025-10-09",
     "last_updated": "2025-09-30", "status": "active",
     "url": "https://www.cms.gov/medicare-coverage-database/view/lcd.aspx?lcdid=33947"},
    {"topic": "Cardiac CT / CCTA", "doc_type": "LCD", "display_id": "L33423",
     "doc_id": 33423, "title": "Cardiac Computed Tomography & Angiography (CCTA)",
     "contractor": "Palmetto GBA", "effective_date": "2025-06-26",
     "last_updated": "2025-06-20", "status": "active",
     "url": "https://www.cms.gov/medicare-coverage-database/view/lcd.aspx?lcdid=33423"},
    {"topic": "Cardiac CT / CCTA", "doc_type": "LCD", "display_id": "L33559",
     "doc_id": 33559, "title": "Cardiac Computed Tomography (CCT) and Coronary Computed Tomography Angiography (CCTA)",
     "contractor": "National Government Services, Inc.", "effective_date": "2022-04-01",
     "last_updated": "2022-02-02", "status": "active",
     "url": "https://www.cms.gov/medicare-coverage-database/view/lcd.aspx?lcdid=33559"},
    {"topic": "CT Cerebral Perfusion", "doc_type": "LCD", "display_id": "L38709",
     "doc_id": 38709, "title": "Computed Tomography Cerebral Perfusion Analysis (CTP)",
     "contractor": "Noridian Healthcare Solutions, LLC", "effective_date": "2025-09-11",
     "last_updated": "2025-09-02", "status": "active",
     "url": "https://www.cms.gov/medicare-coverage-database/view/lcd.aspx?lcdid=38709"},
    {"topic": "CT Cerebral Perfusion", "doc_type": "LCD", "display_id": "L38694",
     "doc_id": 38694, "title": "Computed Tomography Cerebral Perfusion Analysis (CTP)",
     "contractor": "CGS Administrators, LLC", "effective_date": "2025-08-07",
     "last_updated": "2025-07-31", "status": "active",
     "url": "https://www.cms.gov/medicare-coverage-database/view/lcd.aspx?lcdid=38694"},
]


def build_cms_connections() -> List[CMSConnection]:
    """The loop. Iterate the imaging coverage-topic registry and materialise one
    CMSConnection per live Medicare policy document — "everything down to very
    specific CMS connections". National policies (NCDs) bind every MAC; local
    policies (LCDs) bind only the issuing contractor's jurisdiction, which is
    how the same imaging study can be covered differently county-to-county.
    """
    connections: List[CMSConnection] = []
    for topic in _IMAGING_COVERAGE_TOPICS:
        connections.append(CMSConnection(
            topic=topic["topic"],
            doc_type=topic["doc_type"],
            display_id=topic["display_id"],
            doc_id=topic["doc_id"],
            title=topic["title"],
            contractor=topic["contractor"],
            effective_date=topic["effective_date"],
            last_updated=topic["last_updated"],
            status=topic["status"],
            url=topic["url"],
        ))
    # Stable ordering: NCDs first (national), then LCDs by most-recent update.
    connections.sort(key=lambda c: (c.doc_type != "NCD", c.last_updated), reverse=False)
    connections.sort(key=lambda c: (c.doc_type == "NCD"), reverse=True)
    return connections


# ─────────────────────────────────────────────────────────────────────────────
# 4) MAC PAYER JURISDICTIONS — the seven Part-B imaging payers, by state
# ─────────────────────────────────────────────────────────────────────────────
# Real MAC roster from the CMS Coverage API (120 contract records → 7 companies).
# The state map is the public CMS A/B MAC jurisdiction assignment.
def _build_mac_jurisdictions() -> List[MACJurisdiction]:
    return [
        MACJurisdiction("Noridian Healthcare Solutions, LLC", "JE / JF",
                        "CA, HI, NV, AK, AZ, ID, MT, ND, OR, SD, UT, WA, WY (+ AS, GU, MP)",
                        13, 30, "West-coast + Mountain. Largest imaging footprint (CA)."),
        MACJurisdiction("Novitas Solutions, Inc.", "JH / JL",
                        "AR, CO, LA, MS, NM, OK, TX, DE, DC, MD, NJ, PA",
                        12, 33, "Texas + Mid-Atlantic. Two of the five biggest imaging states (TX, PA)."),
        MACJurisdiction("National Government Services, Inc.", "J6 / JK",
                        "IL, MN, WI, CT, ME, MA, NH, NY, RI, VT",
                        10, 23, "Upper-Midwest + New England + NY."),
        MACJurisdiction("Palmetto GBA", "JJ / JM",
                        "AL, GA, TN, NC, SC, VA, WV",
                        7, 15, "Southeast. Fast-growing Sun Belt imaging demand."),
        MACJurisdiction("WPS Insurance Corporation", "J5 / J8",
                        "IA, KS, MO, NE, IN, MI",
                        6, 11, "Heartland + MI/IN."),
        MACJurisdiction("CGS Administrators, LLC", "J15",
                        "KY, OH (+ national DME jurisdictions B & C)",
                        2, 7, "Issues the breast-imaging & cardiac-CT LCDs cited on this page."),
        MACJurisdiction("First Coast Service Options, Inc.", "JN",
                        "FL (+ PR, VI)",
                        1, 5, "Florida — oldest-skewing, highest per-capita imaging demand."),
    ]


# ─────────────────────────────────────────────────────────────────────────────
# 5a) STATE-LEVEL DATA — main imaging states
# ─────────────────────────────────────────────────────────────────────────────
# imaging_centers / mqsa_facilities / spend / DBT% are sourced estimates
# (public filings, FDA MQSA counts, CMS utilization) — labelled as approx.
def _build_state_profiles() -> List[StateImagingProfile]:
    return [
        StateImagingProfile("California", "CA", "Noridian Healthcare Solutions, LLC", "JE",
                            980, 870, 1985.0, 312.0, 88.0),
        StateImagingProfile("Texas", "TX", "Novitas Solutions, Inc.", "JH",
                            720, 690, 1420.0, 298.0, 85.0),
        StateImagingProfile("Florida", "FL", "First Coast Service Options, Inc.", "JN",
                            650, 560, 1610.0, 356.0, 84.0),
        StateImagingProfile("New York", "NY", "National Government Services, Inc.", "JK",
                            540, 520, 1290.0, 286.0, 90.0),
        StateImagingProfile("Pennsylvania", "PA", "Novitas Solutions, Inc.", "JL",
                            410, 430, 980.0, 305.0, 87.0),
        StateImagingProfile("Illinois", "IL", "National Government Services, Inc.", "J6",
                            360, 380, 845.0, 292.0, 86.0),
        StateImagingProfile("Ohio", "OH", "CGS Administrators, LLC", "J15",
                            340, 350, 790.0, 300.0, 85.0),
        StateImagingProfile("Georgia", "GA", "Palmetto GBA", "JJ",
                            300, 260, 640.0, 281.0, 82.0),
        StateImagingProfile("North Carolina", "NC", "Palmetto GBA", "JM",
                            280, 250, 610.0, 276.0, 83.0),
        StateImagingProfile("Michigan", "MI", "WPS Insurance Corporation", "J8",
                            290, 300, 700.0, 295.0, 86.0),
        StateImagingProfile("Arizona", "AZ", "Noridian Healthcare Solutions, LLC", "JF",
                            260, 210, 560.0, 318.0, 84.0),
        StateImagingProfile("New Jersey", "NJ", "Novitas Solutions, Inc.", "JL",
                            300, 280, 720.0, 290.0, 89.0),
    ]


# ─────────────────────────────────────────────────────────────────────────────
# 5b) COUNTY-LEVEL DATA — payer-mix breakdown for the biggest imaging counties
# ─────────────────────────────────────────────────────────────────────────────
# Payer-mix shares are sourced estimates (ACS coverage type + CMS enrollment as
# a proxy); they are an insurance-coverage split, NOT a contracted-revenue mix.
def _build_county_payer_mix() -> List[CountyPayerMix]:
    return [
        CountyPayerMix("Los Angeles", "CA", "06037", 9800.0, 21.0, 33.0, 39.0, 7.0, 215, "Commercial"),
        CountyPayerMix("San Diego", "CA", "06073", 3280.0, 18.0, 24.0, 51.0, 7.0, 78, "Commercial"),
        CountyPayerMix("Harris (Houston)", "TX", "48201", 4730.0, 14.0, 22.0, 48.0, 16.0, 120, "Commercial"),
        CountyPayerMix("Dallas", "TX", "48113", 2610.0, 13.0, 21.0, 51.0, 15.0, 88, "Commercial"),
        CountyPayerMix("Miami-Dade", "FL", "12086", 2700.0, 22.0, 27.0, 39.0, 12.0, 96, "Commercial"),
        CountyPayerMix("Broward", "FL", "12011", 1950.0, 21.0, 22.0, 46.0, 11.0, 72, "Commercial"),
        CountyPayerMix("Cook (Chicago)", "IL", "17031", 5170.0, 16.0, 26.0, 50.0, 8.0, 138, "Commercial"),
        CountyPayerMix("Kings (Brooklyn)", "NY", "36047", 2640.0, 17.0, 38.0, 38.0, 7.0, 71, "Medicaid"),
        CountyPayerMix("Maricopa (Phoenix)", "AZ", "04013", 4490.0, 19.0, 23.0, 51.0, 7.0, 142, "Commercial"),
        CountyPayerMix("Philadelphia", "PA", "42101", 1580.0, 16.0, 38.0, 38.0, 8.0, 58, "Medicaid"),
        CountyPayerMix("Wayne (Detroit)", "MI", "26163", 1780.0, 18.0, 34.0, 42.0, 6.0, 61, "Commercial"),
        CountyPayerMix("Fulton (Atlanta)", "GA", "13121", 1070.0, 13.0, 24.0, 53.0, 10.0, 52, "Commercial"),
        CountyPayerMix("Mecklenburg (Charlotte)", "NC", "37119", 1140.0, 13.0, 19.0, 58.0, 10.0, 44, "Commercial"),
        CountyPayerMix("Allegheny (Pittsburgh)", "PA", "42003", 1240.0, 21.0, 24.0, 49.0, 6.0, 47, "Commercial"),
    ]


# ─────────────────────────────────────────────────────────────────────────────
# 6) BIG PLAYERS — the large freestanding imaging operators
# ─────────────────────────────────────────────────────────────────────────────
def _build_big_players() -> List[BigPlayer]:
    return [
        BigPlayer("Radiology Partners", "PE-backed (practice)", "Whistler Capital 32% · NEA 20% · Future Fund 10% · physicians ~33%", 131,
                  "All 50 states (3,400+ sites; 131 imaging centers)",
                  "Reads across all modalities; owns vRad teleradiology",
                  "Aidoc enterprise partnership (3,400 sites)",
                  "Largest US radiology practice — ~3,600-4,000 physicians, ~56M cases/yr, ~$2.6B rev. Owns vRad (acquired via Mednax 2020, $885M). 2025 debt refinance S&P called 'tantamount to default'."),
        BigPlayer("RadNet", "Public (NASDAQ: RDNT)", "Public equity", 418,
                  "CA, NY, NJ, MD, FL, AZ, TX, DE",
                  "MRI, CT, PET/CT, mammography, US, X-ray",
                  "DeepHealth (AI) — ARR ~$97M (Mar'26)",
                  "Largest US freestanding operator: 418 centers (Dec'25), FY2025 rev ~$2.04B. DeepHealth Saige-Dx breast AI + Gleamer deal."),
        BigPlayer("US Radiology Specialists", "PE-backed", "Welsh, Carson, Anderson & Stowe (WCAS)", 183,
                  "13 states (NC, TX, FL, VA, CO, TN, …)",
                  "MRI, CT, mammography, US, breast",
                  "AI partnerships",
                  "Includes Touchstone Imaging; ~5,000 staff, >8M studies/yr; targets $2.7B rev in 5yr. WCAS faced FTC roll-up scrutiny."),
        BigPlayer("RAYUS Radiology", "PE-backed", "Wellspring Capital", 150,
                  "MN, FL, WA, CO, MD, multi-state",
                  "MRI, CT, PET/CT, mammography",
                  "Partner integrations",
                  "Formerly Center for Diagnostic Imaging (CDI). ~150 centers."),
        BigPlayer("SimonMed Imaging", "PE-backed", "American Securities (~$600M, 2021)", 160,
                  "11 states (AZ, FL, CA, TX, NV, …)",
                  "MRI, CT, PET/CT, mammography, US",
                  "Internal AI + partners",
                  "Scottsdale-based; ~147-170 centers, ~200 radiologists, ~2M visits/yr."),
        BigPlayer("Akumin", "PE-backed", "Stonepeak", 130,
                  "FL, TX, PA, IL, multi-state",
                  "MRI, CT, PET/CT + oncology",
                  "Partner integrations",
                  "Emerged from 2023 Ch.11 restructuring under Stonepeak ownership."),
        BigPlayer("Solis Mammography", "PE-backed", "Madison Dearborn Partners", 95,
                  "TX, FL, OH, PA, GA, NC, multi-state",
                  "Breast: 2D, 3D/DBT, breast US, breast MRI, biopsy",
                  "iCAD / Lunit breast AI",
                  "Largest dedicated breast-imaging platform; specialty hospital JV model."),
        BigPlayer("Envision Radiology", "PE-backed", "Acquired Rezolut (Dec 2025)", 70,
                  "CO, AZ, CA, NJ, NM, NY, PA",
                  "MRI, CT, mammography, US",
                  "Partner integrations",
                  "Added Rezolut's 42 freestanding centers across 6 states at 2025 close."),
        BigPlayer("Long tail (Premier, Unifour, MedQuest, independents)", "PE + independent", "Various sponsors", 5800,
                  "Regional / fragmented",
                  "Full modality mix",
                  "Varies",
                  "~5,000-6,000 of ~6,900 centers are still independent or small-regional — the roll-up runway."),
    ]


# ─────────────────────────────────────────────────────────────────────────────
# 7) AI IMPLEMENTATION — FDA-cleared algorithms, vendors, reimbursement
# ─────────────────────────────────────────────────────────────────────────────
def _build_ai_implementations() -> List[AIImplementation]:
    # FDA has authorized 1,451 AI/ML-enabled devices cumulatively through
    # end-2025; radiology = 1,104 (76% of all FDA AI), with a record 331 new
    # devices in 2025. Clearance leaders: GE HealthCare 120, Siemens 89,
    # Philips 50, Canon 45, United Imaging 38, Aidoc 31, DeepHealth 28. The
    # radiology-AI software market is ~$0.76B (2025) → $2.27B by 2030 (24.5%
    # CAGR) — but reimbursement lags clearance badly: most cleared tools have
    # NO dedicated payment code (only 2 paid Cat-I AI codes, both cardiac).
    return [
        AIImplementation("Viz.ai", "Viz ContaCT / Viz LVO", "FDA cleared (De Novo)",
                         "CT angiography", "Large-vessel-occlusion stroke triage",
                         "NTAP (New Technology Add-on Payment)", "NTAP $1,040 cap (~$30-80 realized)",
                         "First AI to win a CMS NTAP (2020). The cap pays only on loss-making cases — amortized value is far below the headline; subscription ~$25K/yr."),
        AIImplementation("iCAD", "ProFound AI / ProFound Detection", "FDA cleared",
                         "Mammography (DBT)", "Breast-cancer detection & density on tomosynthesis",
                         "Bundled into mammography global", "77063 / 77067 (no separate AI pay)",
                         "Leading breast-AI; reimbursement rides the mammography codes, not a standalone code."),
        AIImplementation("Lunit", "INSIGHT MMG / INSIGHT CXR", "FDA cleared",
                         "Mammography / chest X-ray", "Cancer detection on 2D mammo & CXR",
                         "Bundled / commercial contracts", "—",
                         "Used by Solis and several screening networks."),
        AIImplementation("RadNet / DeepHealth", "Saige-Dx", "FDA cleared (28 RadNet/DeepHealth clearances)",
                         "Mammography (2D/DBT)", "Breast-cancer detection; enhanced-screening upsell",
                         "Cash-pay (EBCD program)", "~$40 self-pay add-on",
                         "RadNet's out-of-pocket enhanced-breast-cancer-detection program (~$40); ~36% opt-in, +21% detection — the clearest AI revenue model in imaging. SimonMed ($50/$90) & RAYUS ($40) copied it."),
        AIImplementation("HeartFlow / Cleerly / Elucid", "FFR-CT & AI coronary plaque", "FDA cleared",
                         "Coronary CT (CCTA)", "FFR-CT + AI plaque quantification",
                         "Category I CPT (the rare paid AI)", "75580 (~$1,017) · NEW 75577 (~$1,000, Jan 2026)",
                         "The exception that proves the rule: cardiac CT AI now has 2 paid Cat-I codes (4/7 MACs cover via LCDs). Pairs with the CCTA LCD family."),
        AIImplementation("Aidoc", "BriefCase (PE, ICH, C-spine, …) — 31 FDA clearances", "FDA cleared (multiple)",
                         "CT / CTA", "Acute-finding triage & notification across modalities",
                         "No direct fee — throughput/quality ROI", "—",
                         "Workflow-triage AI; enterprise deal across Radiology Partners' 3,400 sites. ROI is turnaround time & radiologist productivity, not a code. Raised $150M (2025)."),
        AIImplementation("GE / Siemens / Philips (OEM)", "Embedded reconstruction & detection AI", "FDA cleared (GE 120 · Siemens 89 · Philips 50)",
                         "CT / MRI / X-ray", "Image reconstruction, dose reduction, auto-measure",
                         "Bundled into equipment", "—",
                         "The device OEMs hold the most clearances; AI sold as a scanner feature, not a billable service."),
        AIImplementation("Quantitative CT / chest AI (Coreline, Riverain)", "Lung-nodule / chest quantification", "FDA cleared",
                         "CT / chest X-ray", "Lung-nodule & chest quantification",
                         "CPT Category III (tracking) codes", "0721T-0722T (coronary 0623T→75577 in 2026)",
                         "Cat-III codes let payers track AI before a permanent value is set — the 'reimbursement-lag' purgatory most imaging AI still sits in (the coronary set graduated to Cat-I 75577 in 2026)."),
    ]


# ─────────────────────────────────────────────────────────────────────────────
# 8) RECENT IMPORTANT FACTORS (2024-2026)
# ─────────────────────────────────────────────────────────────────────────────
def _build_recent_factors() -> List[RecentFactor]:
    return [
        RecentFactor("2025 PFS conversion-factor cut", "reimbursement",
                     "CY2025 final PFS conversion factor set at $32.2465, ~2.83% below CY2024's $33.2875 — a direct top-line cut to every professional-component read, while practice costs (MEI) rose ~4.9%.",
                     "headwind", "2025"),
        RecentFactor("CY2026 dual conversion factors", "reimbursement",
                     "CMS finalized two CFs for the first time: qualifying-APM $33.5875 (+4.2%) and non-APM $33.4009 (+3.6%) — a partial reversal of the 2025 cut. Effective Jan 1, 2026.",
                     "tailwind", "2026"),
        RecentFactor("CY2026 −2.5% efficiency adjustment", "reimbursement",
                     "A new −2.5% efficiency adjustment to work RVUs + intra-service time hits nearly all non-time-based services — explicitly diagnostic imaging. Net CY2026 specialty impact est: diagnostic radiology −2%, nuclear medicine −1%, IR +2%.",
                     "headwind", "2026"),
        RecentFactor("Virtual direct supervision permanent", "policy",
                     "CMS made real-time audio/video 'direct supervision' permanent (Jan 1, 2026) for diagnostic tests and contrast-enhanced imaging — a structural staffing-cost win for multi-site IDTFs.",
                     "tailwind", "2026"),
        RecentFactor("Imaging volume growth ~4.6% CAGR", "volume",
                     "Real-world exam volume grew 31% Q1'18→Q1'24 (4.6% CAGR) vs 3.6% workforce growth — demand outrunning radiologist supply. PET specifically +12.2% in 2024.",
                     "tailwind", "2024-2026"),
        RecentFactor("Radiologist workforce gap", "workforce",
                     "~38,000 practicing radiologists; volume CAGR (4.6%) exceeds workforce CAGR (3.6%), with 40% of PET sites reporting ≥8-day waits — a gap that lifts comp and teleradiology rates.",
                     "mixed", "2024-2026"),
        RecentFactor("Site-of-service shift (HOPD → freestanding)", "structure",
                     "Medicare pays 2-4× more for the same scan in a hospital outpatient dept vs freestanding; ~40% of radiology volume is now freestanding. Payers (UHC, Cigna/eviCore, Anthem/Carelon) actively steer to lower-cost sites — a structural tailwind for independents.",
                     "tailwind", "2024-2026"),
        RecentFactor("Site-neutral payment pressure", "policy",
                     "CY2026 OPPS finalized site-neutral pay for drug administration and issued RFIs targeting imaging-without-contrast APCs (5521-5524). CBO scores site-neutral imaging at +$7.6B/10yr — signaling imaging is the next target.",
                     "mixed", "2026"),
        RecentFactor("AUC program rescinded", "policy",
                     "CMS rescinded the Appropriate Use Criteria mandate (42 CFR 414.94 now reserved) effective Jan 1, 2024 — removing a compliance burden, but commercial prior-auth via RBMs (eviCore, Carelon) remains a denial / DSO drag.",
                     "mixed", "2024-2026"),
        RecentFactor("No Surprises Act IDR", "policy",
                     "Radiology is ~16% of all NSA IDR disputes (2nd behind ED's ~48%; combined 64%). ~1.46M disputes in 2024; providers win ~84% (Radiology Partners ~600% of QPA), but small-dollar imaging claims are often uneconomic to arbitrate.",
                     "headwind", "2024-2026"),
        RecentFactor("Interoperability / Prior-Auth rule (CMS-0057-F)", "policy",
                     "Decision deadlines of 72hr (urgent) / 7 days (standard) and PA-metric public reporting phase in from Jan 1, 2026; FHIR PA APIs by 2027. Est. $15B savings over 10yr — faster imaging authorizations.",
                     "tailwind", "2026"),
        RecentFactor("Breast-density notification rule", "policy",
                     "Nationwide FDA dense-breast reporting (Sep 9, 2024) plus the 2024 USPSTF age-40 start drive supplemental screening volume (breast US/MRI) and AI-enhanced-screening upsell.",
                     "tailwind", "2024-2026"),
        RecentFactor("First paid AI imaging codes", "reimbursement",
                     "Jan 2026 added Category I CPT 75577 (AI coronary-plaque, ~$1,000) alongside 75580 (FFR-CT) — the only 2 paid AI imaging codes, both cardiac, covered by 4/7 MACs. Validates the AI thesis but underscores that 1,000+ cleared algorithms still have no payment.",
                     "mixed", "2026"),
        RecentFactor("PE consolidation continues", "structure",
                     "A dozen-plus diagnostic-imaging deals in 2025 (Envision/Rezolut, etc.) against a still-fragmented ~6,900-center market; multiple-arbitrage + AI-productivity remains the core imaging thesis. FTC scrutiny of roll-ups (WCAS) is the watch-item.",
                     "tailwind", "2024-2026"),
    ]


# ─────────────────────────────────────────────────────────────────────────────
# 9) PAYER-TYPE REVENUE SHARE (imaging)
# ─────────────────────────────────────────────────────────────────────────────
def _build_payer_shares() -> List[PayerTypeShare]:
    return [
        PayerTypeShare("Commercial / Employer", 46.0, "flat-to-up",
                       "Best-paying book; the rate driver that makes or breaks an imaging-center P&L."),
        PayerTypeShare("Medicare FFS", 24.0, "down (rate)",
                       "PFS-priced; conversion-factor cuts pressure the per-study rate even as volume grows."),
        PayerTypeShare("Medicare Advantage", 14.0, "up",
                       "Fastest-growing senior book; adds prior-auth friction vs FFS but rising mix."),
        PayerTypeShare("Medicaid / Managed Medicaid", 10.0, "flat",
                       "Lowest reimbursement; concentrated in urban safety-net counties."),
        PayerTypeShare("Self-pay / Other", 6.0, "up",
                       "Includes AI-enhanced-screening cash programs (e.g. RadNet EBCD) and high-deductible patients."),
    ]


# ─────────────────────────────────────────────────────────────────────────────
# 10) MODALITY SUB-SEGMENTS — radiology broken into its economic units
# ─────────────────────────────────────────────────────────────────────────────
# us_market_bn = approx US imaging-services revenue for the modality (all
# settings, illustrative slice of the ~$140B services market); volume, growth,
# capex and margin are sourced estimates. The point is the *relative* economics:
# which modality is high-capex/high-margin, which is commodity, what each one's
# binding supply constraint is.
def _build_modality_segments() -> List[ModalitySegment]:
    return [
        ModalitySegment("CT (computed tomography)", 7.0, 85.0, 5.0, 210.0, 1100.0, 52.0, 12,
                        "Iodinated contrast (single-plant concentration)",
                        "Highest-volume advanced modality; contrast-shock exposed; site-of-service tailwind."),
        ModalitySegment("MRI (magnetic resonance)", 8.0, 40.0, 5.0, 280.0, 1700.0, 55.0, 35,
                        "Liquid helium cryogen for superconducting magnets",
                        "Highest capex + highest fixed cost → utilization is the whole game. Sealed magnets cut helium risk."),
        ModalitySegment("Mammography / breast", 3.5, 40.0, 4.0, 130.0, 400.0, 48.0, 17,
                        "None major (MQSA-regulated units)",
                        "2D→3D/DBT upgrade economics + density-rule supplemental volume. AI-enhanced cash upsell."),
        ModalitySegment("Ultrasound", 4.0, 90.0, 4.0, 130.0, 150.0, 50.0, 25,
                        "None (sonographer labor is the constraint)",
                        "Low capex, labor-intensive; no contrast/cryogen exposure; point-of-care growth."),
        ModalitySegment("PET/CT & nuclear medicine", 3.0, 3.0, 11.0, 1450.0, 2200.0, 40.0, 45,
                        "Mo-99/Tc-99m + F-18 radiopharmaceuticals (short half-life)",
                        "Highest per-study price; +12% PET volume in 2024 straining capacity; isotope-supply fragile."),
        ModalitySegment("X-ray / radiography", 2.5, 200.0, 2.0, 40.0, 360.0, 42.0, 8,
                        "None (commodity)",
                        "Highest raw volume, lowest unit price; throughput/commodity economics; AI triage upside."),
        ModalitySegment("Interventional radiology", 3.0, 6.0, 6.0, 520.0, 1500.0, 45.0, 60,
                        "Contrast + devices/consumables",
                        "Procedure-based, higher acuity; the one segment with a CY2026 PFS uplift (+2%)."),
        ModalitySegment("Teleradiology (read capacity)", 1.0, 0.0, 12.0, 0.0, 50.0, 35.0, 0,
                        "Radiologist labor supply (the binding constraint)",
                        "The capacity/arbitrage layer over every modality; ~12% CAGR; vRad/RP dominant. Capex-light."),
        ModalitySegment("DXA / bone densitometry", 0.5, 12.0, 3.0, 45.0, 80.0, 45.0, 20,
                        "Low (no cryogen/contrast/isotope)",
                        "Osteoporosis screening; low price, frequency-limited; aging-demographics tailwind."),
    ]


# ─────────────────────────────────────────────────────────────────────────────
# 11) SUPPLY SHOCKS — the disruptions that hit imaging economics
# ─────────────────────────────────────────────────────────────────────────────
def _build_supply_shocks() -> List[SupplyShock]:
    return [
        SupplyShock(
            "Iodinated contrast media shortage", "contrast",
            "GE Healthcare's Shanghai plant (Omnipaque/iohexol) — a large share of global iodinated contrast — was shut by a COVID lockdown.",
            "Up to ~80% of GE contrast capacity offline at peak; hospitals rationed CT, deferred non-urgent scans, switched to MRI / non-contrast protocols.",
            "Apr–Aug 2022", "CT, CT angiography, interventional",
            "Dual-source contrast contracting, contrast-stewardship protocols, weight-based dosing, MRI substitution.",
            "high"),
        SupplyShock(
            "Liquid-helium cryogen squeeze", "cryogen",
            "Superconducting MRI magnets need ~2,000L liquid helium at install plus top-offs; the Helium Shortage 3.0/4.0 and the wind-down/privatization of the US Federal Helium Reserve tightened supply.",
            "Helium roughly doubled — ~$7.57/m³ (2020) → ~$14/m³ (2023, USGS); refills delayed; ~50,000 installed MRI base can't refresh overnight.",
            "2019, 2022–2025", "MRI",
            "Sealed 'helium-free'/low-helium magnets (GE Freelium, Philips BlueSeal ~7L, Siemens DryCool ~0.7L) deployed on refresh — the structural fix.",
            "medium"),
        SupplyShock(
            "Mo-99 / Tc-99m radioisotope fragility", "isotope",
            "Technetium-99m (used in ~80% of nuclear-medicine procedures) decays from Molybdenum-99 made in a handful of aging reactors with no historical US production; 66h/6h half-lives prevent stockpiling.",
            "2009–10 global shortage cancelled/deferred scans nationwide; recurring single-reactor outages still ripple.",
            "2009–10; recurring", "Nuclear medicine, SPECT",
            "Domestic Mo-99 (NorthStar, SHINE, Niowave) + CMS CY2026 OPPS $10/dose domestic-Mo-99 add-on (HCPCS C9176) to onshore supply.",
            "medium"),
        SupplyShock(
            "PET radiopharmaceutical / cyclotron capacity", "isotope",
            "F-18 FDG (~110-min half-life) must be made at regional cyclotrons/PET pharmacies and used within hours — supply is local and fragile; new PSMA tracers add demand.",
            "PET volume +12.2% in 2024 strained tracer capacity; ~40% of PET sites report ≥8-day waits.",
            "2024–2026", "PET/CT",
            "Regional cyclotron network expansion, tracer-supply contracts, scheduling optimization.",
            "medium"),
        SupplyShock(
            "Equipment / semiconductor & tariffs", "equipment",
            "2021–23 chip shortage (~52-week lead times) extended scanner delivery; 2025 US–China tariffs (145% Apr → 30% May truce) + China rare-earth/gadolinium export controls raise scanner capex.",
            "Scanner prices nearly doubled in ~6 months (2021–22); GE HealthCare guided a ~$500M 2025 tariff hit (~$375M China); ~$100–200K added per $1–2M CT/MRI.",
            "2021–2023; 2025 tariffs", "All (capex cycle); MRI/X-ray most REE-exposed",
            "OEM onshoring (United Imaging Pearland TX, Siemens $150M US expansion), multi-OEM sourcing, refurbished market, lengthened refresh.",
            "medium"),
        SupplyShock(
            "Radiologist labor supply gap", "labor",
            "~38,000 practicing radiologists against ~4.6%/yr volume growth vs ~3.6%/yr workforce growth, a retirement wave, capped residency slots, and burnout — the binding constraint on reads.",
            "Read backlogs, locum/teleradiology rate inflation, comp escalation; ~40% of PET sites report long waits.",
            "Structural, 2024–2026", "Reads across every modality",
            "Teleradiology (vRad/RP), AI triage/productivity tools, subspecialty read-routing, offshore prelim reads.",
            "high"),
    ]


# ─────────────────────────────────────────────────────────────────────────────
# 12) UNIT ECONOMICS — representative freestanding multi-modality center P&L
# ─────────────────────────────────────────────────────────────────────────────
# Illustrative per-blended-study economics on ~$190 net revenue/study. A
# technical-only (TC) center sends reads to a radiology group/teleradiology and
# drops the radiologist-read line (and ~18% of revenue with it). Numbers are
# sourced estimates, not a specific company's actuals.
def _build_unit_economics() -> List[UnitEconomicLine]:
    rev = 190.0
    return [
        UnitEconomicLine("Net revenue / blended study", 100.0, rev,
                         "Blended across modalities + payer mix; commercial pays ~2-3× Medicare.", True),
        UnitEconomicLine("Clinical / technologist labor", -22.0, -0.22 * rev,
                         "Techs & sonographers; the largest variable cost; tight labor market."),
        UnitEconomicLine("Radiologist reads (employed or tele)", -16.0, -0.16 * rev,
                         "Professional read; a TC-only center sends this out and forgoes the -26 revenue."),
        UnitEconomicLine("Equipment depreciation / lease", -15.0, -0.15 * rev,
                         "High fixed cost → utilization is the dominant margin lever; 7-10yr refresh."),
        UnitEconomicLine("Occupancy / real estate", -7.0, -0.07 * rev,
                         "MRI suites need shielding/siting; MOB lease or REIT/SLB structure."),
        UnitEconomicLine("Billing / RCM / prior-auth", -5.0, -0.05 * rev,
                         "Denials, prior-auth (RBM), No Surprises Act IDR add cost & DSO."),
        UnitEconomicLine("Contrast & consumables", -4.0, -0.04 * rev,
                         "Iodinated/gadolinium contrast, film, supplies; supply-shock exposed."),
        UnitEconomicLine("G&A / marketing / overhead", -11.0, -0.11 * rev,
                         "Scheduling, referral marketing, corporate overhead; scale leverage here."),
        UnitEconomicLine("Center EBITDA", 20.0, 0.20 * rev,
                         "~20% at a scaled multi-modality center; utilization + payer mix + read-sourcing drive it.", True),
    ]


# ─────────────────────────────────────────────────────────────────────────────
# 13) ECONOMIC DRIVERS — the levers that move an imaging P&L
# ─────────────────────────────────────────────────────────────────────────────
def _build_economic_drivers() -> List[EconomicDriver]:
    return [
        EconomicDriver("Equipment utilization rate",
                       "Scans performed ÷ scanner-hours available.",
                       "MRI/CT 60-85% of capacity",
                       "#1 lever: equipment is mostly fixed cost, so each incremental scan is ~70-80% contribution margin."),
        EconomicDriver("Scan throughput / room time",
                       "Minutes of room time per study by modality.",
                       "X-ray ~8m · CT ~12m · US ~25m · MRI ~35m · PET ~45m",
                       "Faster protocols (and AI reconstruction) add slots/day without new capex."),
        EconomicDriver("Payer mix",
                       "Commercial vs Medicare vs Medicaid revenue split.",
                       "Commercial ~46% of revenue",
                       "Commercial pays ~2-3× Medicare for the same code — mix shift swings margin more than volume."),
        EconomicDriver("Same-store volume growth",
                       "YoY scan growth at existing centers.",
                       "~4-5%/yr",
                       "Organic engine; referral relationships + screening expansion (lung, breast) drive it."),
        EconomicDriver("No-show / cancellation rate",
                       "Booked studies that don't arrive.",
                       "~10-20%",
                       "Direct revenue leakage on a fixed-cost slot; reminders + waitlists recover it."),
        EconomicDriver("Radiologist read productivity",
                       "RVUs (or studies) read per radiologist-day.",
                       "subspecialty premium for neuro/MSK/breast",
                       "AI triage + worklist optimization lift reads/day; the labor gap makes this the scaling constraint."),
        EconomicDriver("Site of service",
                       "Freestanding/IDTF vs hospital outpatient (HOPD).",
                       "HOPD costs payers 2-4× freestanding",
                       "Payer steering to freestanding is a structural volume tailwind for independents."),
        EconomicDriver("DSO / denial / prior-auth",
                       "Days sales outstanding, denial rate, RBM prior-auth burden.",
                       "denials ~12-18% (estimate)",
                       "AUC rescinded, but commercial prior-auth + NSA IDR still drag cash conversion."),
        EconomicDriver("Capex cycle / equipment age",
                       "Refresh cadence and depreciation load.",
                       "7-10yr refresh",
                       "Aging fleet = higher maintenance + downtime; refresh timing drives depreciation and tariff exposure."),
        EconomicDriver("Read sourcing (build vs tele)",
                       "In-house reads vs teleradiology / subspecialty routing.",
                       "tele ~12% CAGR",
                       "Labor arbitrage + 24/7 coverage; the global-vs-TC billing split decides who captures the -26 read."),
    ]


# ─────────────────────────────────────────────────────────────────────────────
# 14) RADIOLOGY PARTNERS — diligence deep-dive (the largest US practice)
# ─────────────────────────────────────────────────────────────────────────────
def _build_rp_diligence() -> List[RPDiligenceItem]:
    return [
        RPDiligenceItem("scale", "Physicians", "~3,600–4,000",
                        "Largest US radiology practice by physician count; national density.", "positive"),
        RPDiligenceItem("scale", "Sites / imaging centers", "3,400+ sites · ~131 owned centers",
                        "Hospital-contract + owned-center hybrid across all 50 states.", "positive"),
        RPDiligenceItem("scale", "Annual case volume", "~56M cases/yr",
                        "Massive read volume = data + AI-training + payer-negotiation leverage.", "positive"),
        RPDiligenceItem("financials", "Revenue", "~$2.6B",
                        "Scale leader; revenue concentrated in hospital professional-services contracts.", "positive"),
        RPDiligenceItem("capital", "Total first-lien debt", "~$2.3B+",
                        "Heavily levered; the central diligence risk.", "risk"),
        RPDiligenceItem("capital", "2025 debt restructuring", "S&P: 'tantamount to default'",
                        "Refinancing/maturity-extension that S&P treated as distressed; Moody's pegged the cut at ~20% / ~$600M debt reduction.", "risk"),
        RPDiligenceItem("ownership", "Cap table", "Whistler ~32% · NEA ~20% · Future Fund ~10% · physicians ~33%",
                        "PE-controlled but with meaningful physician ownership; $720M growth raise (target was $300M).", "watch"),
        RPDiligenceItem("tele", "vRad (Virtual Radiologic)", "~688 rads · ~8.9M studies/yr",
                        "Largest US teleradiology, acquired via the $885M Mednax radiology deal (2020); Nov 2025 spun a tech division to license the AI platform externally.", "positive"),
        RPDiligenceItem("ai", "Aidoc enterprise partnership", "across ~3,400 sites",
                        "Enterprise AI triage deployment; Aidoc raised $150M (Sept 2025). Productivity lever against the labor gap.", "positive"),
        RPDiligenceItem("nsa", "No Surprises Act IDR", "~600–631% of QPA (H1 2024)",
                        "Winning arbitration well above payer QPAs — but invites payer network/rate pushback.", "watch"),
        RPDiligenceItem("risk", "PE roll-up scrutiny", "FTC focus on physician-services roll-ups",
                        "Regulatory/antitrust overhang on further consolidation (cf. WCAS/anesthesia case).", "risk"),
    ]


# ─────────────────────────────────────────────────────────────────────────────
# 15) AI IMAGING — how to build a model (pipeline + build-vs-buy)
# ─────────────────────────────────────────────────────────────────────────────
def _build_ai_build_stages() -> List[AIBuildStage]:
    return [
        AIBuildStage("1 · Data acquisition",
                     "Assemble a labeled corpus (from scratch: ~25k–130k studies like CheXNet/Gulshan; foundation models cut it to ~1k–5k, even ~45–2,200). De-identify (HIPAA Safe Harbor; burned-in pixel PHI needs OCR redaction), IRB, data rights. Public sets: ChestX-ray14, CheXpert, MIMIC-CXR, EMBED, CBIS-DDSM.",
                     "$$ (data rights + infra)", "3–9 months (DUA alone ~6-12mo)",
                     "Most public sets are research-ONLY (can't ground a commercial product); positives-per-class & site bias are the binding constraints."),
        AIBuildStage("2 · Annotation / ground truth",
                     "Expert-radiologist labels (~$255/hr); pixel segmentation runs 2–15 min/image; ground truth via biopsy/follow-up; multi-reader consensus to manage variability.",
                     "~$8.50–$70 per segmented image", "3–12 months",
                     "Label noise; 'exorbitant' expert time; ground-truth definition."),
        AIBuildStage("3 · Model development",
                     "U-Net/nnU-Net (segmentation), ResNet/DenseNet/EfficientNet (classification), ViT/Swin, OR fine-tune an imaging foundation model. Compute is NOT the gate.",
                     "~$1–25/run (fine-tune) · ~$10–80K (FM pretrain)", "3–6 months",
                     "Shortcut learning (model keys on scanner/site, not pathology)."),
        AIBuildStage("4 · Validation",
                     "FDA-preferred MRMC reader study (AUC primary): ~12–20 readers × ~100–300 enriched cases, unaided-vs-AI; plus standalone accuracy. Test across scanners/sites/demographics.",
                     "~$0.5–3M single-indication ($5–20M+ multicenter)", "9–18 months",
                     "Distribution shift — 81% of radiology DL models LOSE AUC at a new site (24% drop ≥0.10)."),
        AIBuildStage("5 · FDA clearance",
                     "~97% of imaging AI clears via 510(k) (CADt=triage QAS/QFM · CADe=detect MYN · CADx=diagnose POK); novel → De Novo; autonomous Class-III → PMA. A Predetermined Change Control Plan (PCCP, final guidance Dec 2024) lets you update the model without re-filing.",
                     "~$0.5–2.5M (510k) · ~$17.8M avg (De Novo)", "~5–6.5mo FDA clock (1–7yr end-to-end)",
                     "Predicate/clinical-evidence bar; only 5.4% of devices use a PCCP (rest are 'locked')."),
        AIBuildStage("6 · Deployment",
                     "Integrate into PACS/RIS/worklist (orchestrators: Aidoc aiOS, Nuance/Microsoft, Blackford 140+ apps); on-prem/cloud/hybrid GPU inference; monitor for drift in production.",
                     "$$ (integration + MLOps)", "ongoing",
                     "Silent data drift — only ~9% of FDA AI tools ship a post-market surveillance plan."),
        AIBuildStage("7 · Reimbursement / ROI",
                     "Most imaging AI has NO dedicated payment. The exceptions are cardiac: CPT 75580 (FFR-CT, ~$1,017) and the NEW Jan-2026 CPT 75577 (AI coronary plaque, ~$1,000). Others: NTAP (Viz.ai, $1,040 cap but ~$30-80 realized), bundled-into-code (mammo AI in 77067), or cash-pay (RadNet EBCD ~$40). ROI is usually throughput/quality, not a billable code.",
                     "monetization is the hard part", "12+ months to a code",
                     "Reimbursement lag far behind FDA clearance — the #1 commercial risk."),
    ]


def _build_ai_build_vs_buy() -> List[AIBuildVsBuy]:
    return [
        AIBuildVsBuy("Time to value", "1–7 years (data → FDA → deploy)",
                     "Weeks to integrate a cleared vendor", "Buy for speed"),
        AIBuildVsBuy("Upfront cost", "~$1.65M (510k) / $2.5M (De Novo) / $5M (PMA) regulatory + data/annotation; ~$30M to stand up a Class-II device co.",
                     "Aidoc ~$500–5,000/mo by volume; Viz.ai ~$25K/yr; iCAD/Lunit per-exam", "Buy is far lower upfront"),
        AIBuildVsBuy("FDA / regulatory risk", "You own clearance + post-market PCCP + drift monitoring",
                     "Vendor owns the clearance", "Buy de-risks"),
        AIBuildVsBuy("Differentiation", "Proprietary, if AI is the thesis",
                     "Commodity capability everyone can license", "Build if it's core"),
        AIBuildVsBuy("Data moat", "Leverages your 10M+ study archive (foundation models need tens of millions of images)",
                     "No proprietary-data advantage", "Build if data-rich"),
        AIBuildVsBuy("Reimbursement", "Same gap either way — most cleared AI has no code",
                     "Same gap; vendor may carry the cardiac codes (75577/75580)", "Neutral — ROI is operational"),
        AIBuildVsBuy("Who actually does it", "RadNet/DeepHealth (data-advantaged, AI is the thesis)",
                     "Most platforms license Aidoc/iCAD/Lunit or partner (RP–Aidoc)", "Buy is the default"),
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Compute — assemble the result
# ─────────────────────────────────────────────────────────────────────────────
def compute_radiology_imaging() -> RadiologyImagingResult:
    cpt_codes = _build_cpt_codes()
    mammography_stats = _build_mammography_stats()
    coverage = build_cms_connections()
    macs = _build_mac_jurisdictions()
    states = _build_state_profiles()
    counties = _build_county_payer_mix()
    players = _build_big_players()
    ai = _build_ai_implementations()
    factors = _build_recent_factors()
    payer_shares = _build_payer_shares()
    modality_segments = _build_modality_segments()
    supply_shocks = _build_supply_shocks()
    unit_economics = _build_unit_economics()
    economic_drivers = _build_economic_drivers()
    rp_diligence = _build_rp_diligence()
    ai_build_stages = _build_ai_build_stages()
    ai_build_vs_buy = _build_ai_build_vs_buy()

    ncd_count = sum(1 for c in coverage if c.doc_type == "NCD")
    lcd_count = sum(1 for c in coverage if c.doc_type == "LCD")
    ebitda_line = next((u for u in unit_economics if u.line_item == "Center EBITDA"), None)
    center_ebitda_margin_pct = ebitda_line.pct_of_revenue if ebitda_line else 0.0

    return RadiologyImagingResult(
        market_size_bn=26.3,                 # US diagnostic-imaging-centers industry (IBISWorld 2026)
        freestanding_centers=6900,           # approx freestanding/IDTF imaging centers (IBISWorld 2026)
        mqsa_facilities=8700,                # FDA MQSA-certified mammography facilities
        annual_mammograms_mm=40.0,
        dbt_adoption_pct=87.0,
        cpt_codes_tracked=len(cpt_codes),
        cms_connections=len(coverage),
        ncd_count=ncd_count,
        lcd_count=lcd_count,
        mac_payers=len(macs),
        fda_ai_radiology_devices=1104,       # FDA AI/ML radiology clearances through end-2025 (76% of 1,451 total)
        radiologist_shortage=38000,          # practicing radiologists (supply baseline)
        pfs_conversion_factor_2025=32.2465,  # FINAL CY2025 PFS conversion factor
        cpt_codes=cpt_codes,
        mammography_stats=mammography_stats,
        coverage_connections=coverage,
        mac_jurisdictions=macs,
        state_profiles=states,
        county_payer_mix=counties,
        big_players=players,
        ai_implementations=ai,
        recent_factors=factors,
        payer_shares=payer_shares,
        modality_segments=modality_segments,
        supply_shocks=supply_shocks,
        unit_economics=unit_economics,
        economic_drivers=economic_drivers,
        rp_diligence=rp_diligence,
        ai_build_stages=ai_build_stages,
        ai_build_vs_buy=ai_build_vs_buy,
        center_revenue_mm=4.5,               # approx net revenue of a scaled multi-modality center
        center_ebitda_margin_pct=center_ebitda_margin_pct,
    )
