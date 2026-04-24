"""NCCI Edit Compliance Scanner — /ncci-scanner.

The National Correct Coding Initiative (NCCI) publishes quarterly:
  1. Procedure-to-Procedure (PTP) edits — CPT/HCPCS code pairs that may
     not be billed together on the same patient, same day, same provider
     unless a valid modifier override is appended.
  2. Medically Unlikely Edits (MUEs) — maximum unit-of-service limits
     per CPT/HCPCS per patient per date of service.

Every Medicare claim is scrubbed against NCCI edits before payment.
Commercial payers layer identical or tighter rules via Change Healthcare /
Optum / TriZetto ClaimsXten engines. A deal target with code-pair patterns
that map heavily to NCCI exclusions is carrying pre-adjustment billing
risk that standard QoR rarely surfaces.

This module:
  - Encodes a curated library of high-volume, PE-relevant NCCI edits
    (not the full ~1.5M-row CMS table — the subset that actually moves
    diligence needles for the specialties in the corpus).
  - Maps each edit to a specialty footprint (which specialty-profile
    deals are most exposed).
  - Scores each corpus deal by inferred specialty against the edit
    library → per-deal edit-risk percentile.
  - Surfaces modifier-override eligibility (the operational lever a
    post-close billing team can pull to convert denials into paid claims).
  - Crosswalks edits to OIG Work Plan audit topics where the edit type
    is under active federal audit.

Public API:
    NCCIPairEdit                dataclass for a PTP edit row
    MUELimit                    dataclass for a unit-of-service limit
    SpecialtyFootprint          CPT mix + edit density for a specialty
    DealEditExposure            per-deal edit-risk scoring result
    ModifierOverride            modifier reference row
    AuditCrosswalk              NCCI→OIG Work Plan linkage
    NCCIScannerResult           composite output
    compute_ncci_scanner()      -> NCCIScannerResult
"""
from __future__ import annotations

import importlib
import json
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class NCCIPairEdit:
    """One PTP (procedure-to-procedure) edit row."""
    column1_code: str          # "principal" service — this is billed
    column2_code: str          # "component" service — bundled; denial if billed with col-1
    col1_descriptor: str
    col2_descriptor: str
    modifier_indicator: int    # 0 = not allowed, 1 = allowed, 9 = not applicable
    effective_date: str
    specialty: str             # primary specialty affected
    annual_claim_volume_m: float  # rough national annual frequency
    typical_allowed_col1: float   # $ per unit
    rationale: str             # why the pair is bundled


@dataclass
class MUELimit:
    """One medically-unlikely-edit unit limit."""
    code: str
    descriptor: str
    mue_value: int             # maximum units of service per patient per DOS
    mue_adjudication_type: str # "date of service", "line item", "per diem"
    specialty: str
    rationale: str


@dataclass
class SpecialtyFootprint:
    """CPT-mix profile + NCCI edit density for a single specialty."""
    specialty: str
    top_cpt_codes: str         # comma-delimited representative CPT codes
    annual_claim_volume_m: float
    ptp_edits_affecting: int   # count of PTP edits in our library touching this specialty
    mue_limits_affecting: int  # count of MUE limits touching this specialty
    edit_density_score: float  # 0–100; higher = more exposed
    override_eligibility_pct: float  # % of edits with modifier_indicator == 1


@dataclass
class DealEditExposure:
    """Per-deal inferred edit-risk profile."""
    deal_name: str
    year: int
    buyer: str
    inferred_specialty: str
    edit_density_score: float
    ptp_edits_affecting: int
    override_eligibility_pct: float
    estimated_annual_denial_exposure_m: float
    risk_tier: str             # "HIGH" / "MEDIUM" / "LOW"
    ev_mm: Optional[float]


@dataclass
class ModifierOverride:
    """Modifier reference — the lever a billing team uses to override a PTP edit."""
    modifier: str
    full_name: str
    use_case: str
    success_rate_pct: float
    audit_risk: str            # "low" / "medium" / "high"
    notes: str


@dataclass
class AuditCrosswalk:
    """Mapping of NCCI edit types to active OIG Work Plan audit topics."""
    edit_category: str
    oig_work_plan_item: str
    year_added: int
    status: str                # "open" / "active" / "completed"
    typical_recovery_m: float
    affected_specialties: str


@dataclass
class NCCIScannerResult:
    # Headline KPIs
    total_ptp_edits: int
    total_mue_limits: int
    total_specialties_profiled: int
    avg_override_eligibility_pct: float
    high_risk_deals: int
    total_estimated_denial_exposure_m: float

    # Tables
    ptp_edits: List[NCCIPairEdit]
    mue_limits: List[MUELimit]
    specialty_footprints: List[SpecialtyFootprint]
    deal_exposures: List[DealEditExposure]
    modifier_overrides: List[ModifierOverride]
    audit_crosswalks: List[AuditCrosswalk]

    corpus_deal_count: int


# ---------------------------------------------------------------------------
# Corpus loader (identical to the established pattern)
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
# Curated NCCI PTP edit library
# Subset of the CMS NCCI Q4-2025 tables, filtered to pairs that are
# high-volume AND relevant to the specialties represented in the corpus.
# Descriptors are abbreviated from the official CPT long descriptors
# (CPT long descriptors are AMA-licensed; short descriptors are reported
# here as fair-use paraphrase for diligence analysis).
# modifier_indicator: 0 = no modifier permitted (hard bundle), 1 = modifier
# may override (59, XE, XS, XP, XU, or anatomic), 9 = N/A.
# ---------------------------------------------------------------------------

def _build_ptp_edits() -> List[NCCIPairEdit]:
    return [
        # Emergency Medicine / ED Physician
        NCCIPairEdit("99285", "93010", "ED visit high complexity", "ECG interpretation only",
                     1, "2015-01-01", "Emergency Medicine", 18.5, 285.00,
                     "ECG interpretation is bundled into high-level ED E/M unless separately identifiable"),
        NCCIPairEdit("99284", "12001", "ED visit moderate complexity", "Simple wound repair <2.5cm",
                     1, "2015-01-01", "Emergency Medicine", 12.8, 225.00,
                     "Laceration repair included in ED E/M; requires 25 modifier if separately significant"),
        NCCIPairEdit("99285", "31500", "ED visit high complexity", "Emergency endotracheal intubation",
                     1, "2015-01-01", "Emergency Medicine", 3.2, 285.00,
                     "Intubation billed separately with 25 modifier when significant separate procedure"),
        NCCIPairEdit("99291", "92950", "Critical care first hour", "CPR",
                     0, "2015-01-01", "Emergency Medicine", 1.85, 520.00,
                     "CPR time included in critical-care time — hard bundle, no modifier override"),

        # Radiology
        NCCIPairEdit("74177", "74176", "CT abd/pelvis w/contrast", "CT abd/pelvis w/o contrast",
                     0, "2015-01-01", "Radiology", 8.2, 520.00,
                     "Cannot bill with-contrast and without-contrast separately when combined study performed"),
        NCCIPairEdit("71250", "71260", "CT thorax w/o contrast", "CT thorax w/contrast",
                     0, "2015-01-01", "Radiology", 4.5, 310.00,
                     "Same-day thorax CT with and without contrast must be billed as combined 71270"),
        NCCIPairEdit("76700", "76705", "US abd complete", "US abd limited",
                     0, "2015-01-01", "Radiology", 6.8, 185.00,
                     "Complete and limited abdominal ultrasound same-day — complete supersedes"),
        NCCIPairEdit("77067", "77066", "Screening mammogram bilateral", "Diagnostic mammogram bilateral",
                     1, "2015-01-01", "Radiology", 38.5, 145.00,
                     "Screening-converted-to-diagnostic; modifier GG required"),
        NCCIPairEdit("78452", "93350", "SPECT myocardial perfusion", "Stress echo",
                     0, "2015-01-01", "Cardiology", 1.8, 1250.00,
                     "Overlapping stress-imaging modalities — may not be billed same DOS"),

        # Cardiology
        NCCIPairEdit("93306", "93320", "Echo complete w/ Doppler", "Doppler echo complete",
                     0, "2015-01-01", "Cardiology", 12.5, 275.00,
                     "Doppler is included in complete echo — hard bundle"),
        NCCIPairEdit("93458", "93454", "LHC w/ coronary angio", "Coronary angio only",
                     0, "2015-01-01", "Cardiology", 1.65, 2850.00,
                     "Coronary angiography is a component of LHC — cannot unbundle"),
        NCCIPairEdit("93005", "93010", "ECG tracing only", "ECG interpretation only",
                     1, "2015-01-01", "Cardiology", 58.5, 18.00,
                     "Technical + professional components — use 26/TC; modifier 26 overrides"),
        NCCIPairEdit("93015", "93018", "Cardiovascular stress test global", "Stress test interp only",
                     0, "2015-01-01", "Cardiology", 2.4, 165.00,
                     "Global stress test includes both TC and 26 components"),

        # GI / Endoscopy
        NCCIPairEdit("45378", "45380", "Colonoscopy diagnostic", "Colonoscopy w/ biopsy",
                     1, "2015-01-01", "Gastroenterology", 8.5, 425.00,
                     "Biopsy supersedes diagnostic when performed; 59 modifier if separate session"),
        NCCIPairEdit("45385", "45378", "Colonoscopy w/ polypectomy snare", "Colonoscopy diagnostic",
                     0, "2015-01-01", "Gastroenterology", 5.8, 625.00,
                     "Polypectomy supersedes diagnostic colonoscopy — hard bundle"),
        NCCIPairEdit("43239", "43235", "EGD w/ biopsy", "EGD diagnostic",
                     0, "2015-01-01", "Gastroenterology", 4.2, 385.00,
                     "EGD with biopsy supersedes diagnostic EGD"),

        # Orthopedics / MSK
        NCCIPairEdit("27447", "27486", "Total knee arthroplasty", "Knee revision femoral/tibial",
                     0, "2015-01-01", "Orthopedics", 0.68, 12850.00,
                     "Primary and revision arthroplasty are mutually exclusive on same knee same DOS"),
        NCCIPairEdit("27130", "27138", "Total hip arthroplasty", "Hip revision acetabular",
                     0, "2015-01-01", "Orthopedics", 0.45, 11250.00,
                     "Primary and revision hip procedures are mutually exclusive"),
        NCCIPairEdit("29881", "29877", "Arthroscopic meniscectomy", "Arthroscopic chondroplasty",
                     1, "2015-01-01", "Orthopedics", 1.85, 1850.00,
                     "Chondroplasty bundled into meniscectomy unless separate compartment"),
        NCCIPairEdit("20610", "76942", "Major joint injection", "US guidance for needle placement",
                     1, "2015-01-01", "Orthopedics", 15.8, 65.00,
                     "Use 20611 (with guidance) instead; cannot bill 20610+76942 separately"),

        # Urology
        NCCIPairEdit("52000", "52005", "Cystourethroscopy", "Cysto w/ ureteral cath",
                     0, "2015-01-01", "Urology", 2.8, 165.00,
                     "Catheterization is a component of cysto w/ ureteral cath — bundled"),
        NCCIPairEdit("55700", "76872", "Prostate biopsy needle", "Transrectal US",
                     1, "2015-01-01", "Urology", 1.8, 285.00,
                     "TRUS guidance bundled with biopsy unless separately identifiable (use 76942)"),

        # Dermatology
        NCCIPairEdit("17000", "11100", "Destruction premalignant lesion first", "Biopsy skin single lesion",
                     1, "2015-01-01", "Dermatology", 18.5, 82.00,
                     "Biopsy may be separate if different lesion (59 modifier with lesion-location doc)"),
        NCCIPairEdit("17311", "88305", "Mohs surgery first stage", "Pathology level IV surgical",
                     0, "2015-01-01", "Dermatology", 2.8, 585.00,
                     "Mohs includes professional pathology — cannot separately bill 88305"),
        NCCIPairEdit("11042", "97597", "Debridement subcutaneous", "Active wound care <20cm",
                     0, "2015-01-01", "Dermatology / Wound Care", 4.5, 145.00,
                     "Surgical and active wound-care debridement mutually exclusive same wound same DOS"),

        # Anesthesia / Pain Management
        NCCIPairEdit("62321", "62322", "ESI cervical/thoracic w/ imaging", "ESI lumbar w/ imaging",
                     1, "2015-01-01", "Pain Management", 3.5, 485.00,
                     "Multiple-level ESI — 59 modifier on second level if distinct session/anatomy"),
        NCCIPairEdit("64483", "64484", "Transforaminal ESI lumbar first", "Transforaminal ESI lumbar each add'l",
                     9, "2015-01-01", "Pain Management", 5.8, 385.00,
                     "Add-on code — no override needed but MUE limits apply"),
        NCCIPairEdit("20552", "20553", "Trigger point 1-2 muscles", "Trigger point 3+ muscles",
                     0, "2015-01-01", "Pain Management", 2.2, 85.00,
                     "Trigger-point codes are mutually exclusive — cannot bill both same DOS"),

        # Primary Care / Internal Medicine
        NCCIPairEdit("99213", "99214", "Office visit est pt low-mod", "Office visit est pt moderate",
                     0, "2015-01-01", "Primary Care", 185.0, 95.00,
                     "Cannot bill two established-patient E/Ms same DOS — hard bundle"),
        NCCIPairEdit("99213", "90471", "Office visit est pt", "Immunization admin first",
                     1, "2015-01-01", "Primary Care", 42.8, 95.00,
                     "Use 25 modifier on E/M when significant separately identifiable"),
        NCCIPairEdit("99213", "96372", "Office visit est pt", "Therapeutic injection SC/IM",
                     1, "2015-01-01", "Primary Care", 28.5, 95.00,
                     "25 modifier required on E/M for injection-day denials"),

        # Infusion / Specialty Pharmacy / Oncology
        NCCIPairEdit("96413", "96375", "Chemo IV push each addl hour", "Therapeutic injection IV push each addl",
                     0, "2015-01-01", "Oncology / Infusion", 6.8, 185.00,
                     "Chemo and therapeutic-injection add-on codes cannot be billed same DOS"),
        NCCIPairEdit("96413", "96365", "Chemo infusion IV first hour", "Therapeutic IV infusion first hour",
                     0, "2015-01-01", "Oncology / Infusion", 8.2, 385.00,
                     "Chemotherapy supersedes therapeutic infusion when both performed"),
        NCCIPairEdit("36415", "36416", "Routine venipuncture", "Finger stick blood draw",
                     0, "2015-01-01", "Lab / Pathology", 125.0, 8.00,
                     "Cannot bill both vein and finger-stick draw same DOS"),

        # Home Health / Hospice
        NCCIPairEdit("G0154", "G0299", "Skilled nursing services", "Direct skilled RN home",
                     9, "2020-01-01", "Home Health", 18.2, 165.00,
                     "Revenue-code-level bundling under HHVBP; not modifier-overridable"),

        # Physical Therapy / Rehab
        NCCIPairEdit("97110", "97140", "Therapeutic exercise 15min", "Manual therapy 15min",
                     1, "2015-01-01", "Physical Therapy / Rehab", 85.2, 42.00,
                     "Both may be billed with 59 modifier if distinct interventions"),
        NCCIPairEdit("97530", "97110", "Therapeutic activities 15min", "Therapeutic exercise 15min",
                     1, "2015-01-01", "Physical Therapy / Rehab", 32.5, 48.00,
                     "59 modifier required — commonly denied without documentation"),

        # Behavioral Health
        NCCIPairEdit("90834", "90791", "Psychotherapy 45min est", "Psychiatric diag eval",
                     0, "2015-01-01", "Behavioral Health", 12.8, 125.00,
                     "Psychotherapy and diagnostic evaluation mutually exclusive same DOS"),
        NCCIPairEdit("H0038", "H0036", "Peer support services", "Community psychiatric support",
                     0, "2018-01-01", "Behavioral Health", 2.8, 42.00,
                     "State Medicaid-specific HCPCS — bundling varies; typical Medicaid hard-bundle"),

        # Dental (CDT, adjacency) — represented via D-codes only for Medicaid/MCR-Advantage
        NCCIPairEdit("D2150", "D2160", "Amalgam 2-surface primary", "Amalgam 3-surface primary",
                     0, "2015-01-01", "Dental", 18.5, 125.00,
                     "Dental surface-count codes are mutually exclusive — highest surface count wins"),

        # Nephrology / Dialysis
        NCCIPairEdit("90960", "90962", "ESRD monthly services 1-3 visits", "ESRD monthly services 4+ visits",
                     0, "2015-01-01", "Nephrology", 0.92, 285.00,
                     "Visit-count-based MCP — cannot bill overlapping categories"),
        NCCIPairEdit("90935", "90937", "Hemodialysis single eval", "Hemodialysis repeated eval",
                     0, "2015-01-01", "Nephrology", 2.8, 85.00,
                     "Single and repeated-eval hemodialysis codes mutually exclusive per DOS"),

        # Ophthalmology
        NCCIPairEdit("66984", "66821", "Cataract w/ IOL extracapsular", "YAG laser capsulotomy",
                     1, "2015-01-01", "Eye Care / Ophthalmology", 3.85, 1525.00,
                     "Subsequent YAG requires 79 modifier if within global period"),
        NCCIPairEdit("92250", "92133", "Fundus photography", "OCT retina",
                     1, "2015-01-01", "Eye Care / Ophthalmology", 8.5, 65.00,
                     "Distinct anatomic interpretations — 59 modifier if documented"),

        # Ambulatory Surgery / ASC
        NCCIPairEdit("64721", "64719", "Carpal tunnel release", "Ulnar nerve release at wrist",
                     1, "2015-01-01", "ASC / Hand Surgery", 1.25, 985.00,
                     "Separate anatomic sites — modifier required; commonly audited"),

        # Sleep Medicine
        NCCIPairEdit("95810", "95811", "Polysomnography 4+ channels", "PSG w/ CPAP titration",
                     0, "2015-01-01", "Sleep Medicine", 2.85, 685.00,
                     "Titration supersedes baseline PSG — cannot bill both same night"),

        # Fertility / REI
        NCCIPairEdit("58970", "58974", "Oocyte retrieval", "Embryo transfer",
                     0, "2015-01-01", "Fertility / IVF", 0.48, 2250.00,
                     "Different stages of IVF cycle — typically different DOS but bundled if same DOS"),

        # Podiatry
        NCCIPairEdit("11055", "11721", "Paring hyperkeratotic lesion", "Debridement 6+ nails",
                     1, "2015-01-01", "Podiatry", 8.2, 48.00,
                     "59 modifier may apply if distinct treatment areas; commonly denied"),

        # Audiology / ENT
        NCCIPairEdit("92557", "92552", "Comprehensive audiometry", "Pure tone audiometry air only",
                     0, "2015-01-01", "ENT / Audiology", 2.45, 42.00,
                     "Comprehensive audiometry includes pure-tone components — hard bundle"),
    ]


# ---------------------------------------------------------------------------
# Curated MUE (Medically Unlikely Edit) library
# ---------------------------------------------------------------------------

def _build_mue_limits() -> List[MUELimit]:
    return [
        MUELimit("99213", "Office visit est pt low-mod", 1, "date of service", "Primary Care",
                 "Only one established-patient E/M per DOS per provider"),
        MUELimit("99214", "Office visit est pt moderate", 1, "date of service", "Primary Care",
                 "Only one established-patient E/M per DOS per provider"),
        MUELimit("99285", "ED visit high complexity", 1, "date of service", "Emergency Medicine",
                 "One ED E/M per DOS; multiple visits flagged"),
        MUELimit("96413", "Chemo infusion first hour", 1, "date of service", "Oncology / Infusion",
                 "First-hour infusion can bill once per DOS; add-on 96415 for subsequent hours"),
        MUELimit("96415", "Chemo infusion each addl hour", 8, "date of service", "Oncology / Infusion",
                 "Typical max 8 additional hours per DOS"),
        MUELimit("96365", "Therapeutic IV first hour", 1, "date of service", "Infusion", "One first-hour per DOS"),
        MUELimit("36415", "Routine venipuncture", 1, "date of service", "Lab / Pathology",
                 "One venipuncture per DOS typical"),
        MUELimit("80053", "Comprehensive metabolic panel", 1, "date of service", "Lab / Pathology",
                 "One CMP per DOS — repeat panels flagged"),
        MUELimit("85025", "CBC w/ automated diff", 1, "date of service", "Lab / Pathology",
                 "One CBC per DOS typical"),
        MUELimit("88305", "Surgical pathology level IV", 10, "date of service", "Lab / Pathology",
                 "Per-specimen limit; high-volume reviewed"),
        MUELimit("45378", "Colonoscopy diagnostic", 1, "date of service", "Gastroenterology",
                 "One colonoscopy per DOS"),
        MUELimit("43239", "EGD with biopsy", 1, "date of service", "Gastroenterology",
                 "One EGD per DOS"),
        MUELimit("97110", "Therapeutic exercise 15min", 4, "date of service", "Physical Therapy / Rehab",
                 "Typical max 4 units per DOS; audit flag >4"),
        MUELimit("97140", "Manual therapy 15min", 4, "date of service", "Physical Therapy / Rehab",
                 "Max 4 units per DOS typical"),
        MUELimit("97530", "Therapeutic activities 15min", 4, "date of service", "Physical Therapy / Rehab",
                 "Max 4 units per DOS"),
        MUELimit("20610", "Major joint injection", 2, "date of service", "Orthopedics",
                 "Bilateral max 2 — modifier 50 for bilateral"),
        MUELimit("64483", "Transforaminal ESI lumbar first", 1, "date of service", "Pain Management",
                 "One first-level per DOS; add-on 64484 for additional levels"),
        MUELimit("64484", "Transforaminal ESI lumbar each addl", 2, "date of service", "Pain Management",
                 "Max 2 additional levels per DOS"),
        MUELimit("17000", "Destruction premalignant first", 1, "date of service", "Dermatology",
                 "One first lesion; 17003 add-on for 2nd-14th, 17004 for 15+"),
        MUELimit("17003", "Destruction premalignant 2-14", 13, "date of service", "Dermatology",
                 "Add-on up to 14 additional lesions"),
        MUELimit("11055", "Paring hyperkeratotic lesion", 4, "date of service", "Podiatry",
                 "Max 4 lesions per DOS — frequent audit target"),
        MUELimit("11721", "Debridement 6+ nails", 1, "date of service", "Podiatry",
                 "One unit per DOS — covers 6+ nails"),
        MUELimit("92250", "Fundus photography", 2, "date of service", "Eye Care / Ophthalmology",
                 "Bilateral max 2"),
        MUELimit("92133", "OCT retina", 2, "date of service", "Eye Care / Ophthalmology",
                 "Bilateral max 2"),
        MUELimit("93306", "Echo complete w/ Doppler", 1, "date of service", "Cardiology",
                 "One echo per DOS typical"),
        MUELimit("77067", "Screening mammogram bilateral", 1, "date of service", "Radiology",
                 "One screening mammogram per DOS"),
        MUELimit("74177", "CT abd/pelvis w/contrast", 1, "date of service", "Radiology",
                 "One CT abd/pelvis per DOS typical"),
        MUELimit("95810", "Polysomnography 4+ channels", 1, "date of service", "Sleep Medicine",
                 "One study per night"),
        MUELimit("66984", "Cataract w/ IOL extracapsular", 2, "date of service", "Eye Care / Ophthalmology",
                 "Bilateral surgical limit"),
        MUELimit("90834", "Psychotherapy 45min est", 1, "date of service", "Behavioral Health",
                 "One psychotherapy session per DOS per provider"),
        MUELimit("H0038", "Peer support services", 8, "date of service", "Behavioral Health",
                 "State-variable; typical 8-unit-per-DOS cap"),
        MUELimit("G0154", "Skilled nursing services", 16, "date of service", "Home Health",
                 "15-min units — typical max 16 per DOS"),
    ]


# ---------------------------------------------------------------------------
# Specialty footprints — CPT mix + edit density per specialty
# Derived from Medicare Provider Utilization & Payment Data Part B annual
# files for the relevant specialty taxonomy codes (approximated here for
# the corpus specialties).
# ---------------------------------------------------------------------------

_SPECIALTY_CPT_FOOTPRINTS: Dict[str, Tuple[str, float]] = {
    # specialty -> (top_cpt_codes_csv, annual_claim_volume_m)
    "Primary Care":                ("99213, 99214, 99215, 99232, 36415, 85025, 80053, 90471", 485.0),
    "Emergency Medicine":          ("99284, 99285, 99291, 12001, 31500, 93010, 36415", 58.5),
    "Radiology":                   ("74177, 71260, 76700, 77067, 72148, 78452, 93306", 115.0),
    "Cardiology":                  ("93306, 93458, 93454, 93015, 93005, 93010, 78452", 32.8),
    "Gastroenterology":            ("45378, 45380, 45385, 43239, 43235, 88305", 14.2),
    "Orthopedics":                 ("27447, 27130, 29881, 29877, 20610, 20611, 73721", 18.5),
    "Urology":                     ("52000, 52005, 55700, 76872, 76942, 51798", 6.8),
    "Dermatology":                 ("17000, 17003, 11100, 17311, 11042, 97597, 88305", 22.5),
    "Pain Management":             ("62321, 62322, 64483, 64484, 20552, 20553, 76942", 8.5),
    "Oncology / Infusion":         ("96413, 96415, 96365, 96375, 96372, 36415, 85025", 45.2),
    "Lab / Pathology":             ("80053, 85025, 36415, 88305, 88304, 87086, 81001", 685.0),
    "Physical Therapy / Rehab":    ("97110, 97140, 97530, 97535, 97535, 97116, 97112", 125.0),
    "Behavioral Health":           ("90834, 90837, 90791, 90847, H0038, H0036, 96127", 58.5),
    "Nephrology":                  ("90960, 90962, 90935, 90937, 36901, 36905", 3.2),
    "Eye Care / Ophthalmology":    ("66984, 92250, 92133, 92134, 67028, 92014, 66821", 28.5),
    "Sleep Medicine":              ("95810, 95811, 95805, 94660, 95782, 99214", 5.8),
    "Fertility / IVF":             ("58970, 58974, 58760, 76830, 89280, 89255", 0.92),
    "Podiatry":                    ("11055, 11721, 99213, 11730, 97597, 29540", 15.8),
    "ENT / Audiology":             ("92557, 92552, 92567, 99213, 31237, 69210", 18.2),
    "Dental":                      ("D2150, D2160, D1110, D0150, D7140, D2740", 225.0),
    "Home Health":                 ("G0154, G0299, G0300, G0156, G0151", 28.5),
    "Dermatology / Wound Care":    ("11042, 97597, 17311, 11043, 15271, 15275", 12.5),
    "Hand Surgery":                ("64721, 64719, 26055, 26160, 26111", 1.4),
    "ASC / Hand Surgery":          ("64721, 64719, 26055, 29848", 1.4),
}


def _build_specialty_footprints(
    ptp_edits: List[NCCIPairEdit],
    mue_limits: List[MUELimit],
) -> List[SpecialtyFootprint]:
    rows: List[SpecialtyFootprint] = []
    for specialty, (cpts, volume_m) in _SPECIALTY_CPT_FOOTPRINTS.items():
        ptp_touching = [e for e in ptp_edits if _specialty_matches(e.specialty, specialty)]
        mue_touching = [m for m in mue_limits if _specialty_matches(m.specialty, specialty)]
        ptp_count = len(ptp_touching)
        mue_count = len(mue_touching)

        # Density = (edits touching specialty / volume in millions) normalized 0-100
        raw_density = (ptp_count + 0.5 * mue_count) * 10.0 / max(volume_m, 1.0)
        density = min(100.0, max(0.0, raw_density * 10.0))

        overridable = [e for e in ptp_touching if e.modifier_indicator == 1]
        override_pct = (len(overridable) / ptp_count * 100.0) if ptp_count > 0 else 0.0

        rows.append(SpecialtyFootprint(
            specialty=specialty,
            top_cpt_codes=cpts,
            annual_claim_volume_m=volume_m,
            ptp_edits_affecting=ptp_count,
            mue_limits_affecting=mue_count,
            edit_density_score=round(density, 2),
            override_eligibility_pct=round(override_pct, 1),
        ))
    rows.sort(key=lambda r: r.edit_density_score, reverse=True)
    return rows


def _specialty_matches(edit_specialty: str, profile_specialty: str) -> bool:
    """Loose match — edit may tag multiple specialties in string form."""
    e = edit_specialty.lower()
    p = profile_specialty.lower()
    if e == p:
        return True
    # Allow prefix/substring matches for compound specialties
    # e.g. "Dermatology / Wound Care" matches "Dermatology"
    e_head = e.split(" / ")[0].strip()
    p_head = p.split(" / ")[0].strip()
    return e_head == p_head or e_head in p or p_head in e


# ---------------------------------------------------------------------------
# Deal-specialty classifier — keyword lookup over deal_name + notes
# ---------------------------------------------------------------------------

_SPECIALTY_KEYWORDS: List[Tuple[str, List[str]]] = [
    ("Primary Care",               ["primary care", "pcp", "chenmed", "oak street", "iora", "onemedical", "vera whole"]),
    ("Emergency Medicine",         ["emergency medicine", "envision", "teamhealth", "ed staff", "emergency dept"]),
    ("Radiology",                  ["radiology", "imaging", "rayus", "radnet", "smil", "mri", "ct scan"]),
    ("Cardiology",                 ["cardiology", "cardiac", "heart", "cardio", "us heart", "cardiovascular"]),
    ("Gastroenterology",           ["gastroenter", "endoscopy", "gi network", "gi associate", "gastro"]),
    ("Orthopedics",                ["orthoped", "musculoskeletal", "msk", "joint replacement", "ortho rehab", "ortho "]),
    ("Urology",                    ["urolog", "men's health", "mens health", "ushers"]),
    ("Dermatology",                ["dermatol", "aesthetic derm", "skin", "advanced derma", "u.s. dermatology"]),
    ("Pain Management",            ["pain management", "interventional pain", "pain clinic"]),
    ("Oncology / Infusion",        ["oncolog", "cancer", "infusion", "ion solutions", "vivor"]),
    ("Lab / Pathology",            ["lab /", "laboratory", "pathology", "diagnostic lab", "reference lab", "quest adj"]),
    ("Physical Therapy / Rehab",   ["physical therapy", "rehab", "ati phys", "pt net", "select phys", "athletico"]),
    ("Behavioral Health",          ["behavioral", "psych", "mental health", "aba", "autism", "addiction", "substance"]),
    ("Nephrology",                 ["dialysis", "renal", "kidney", "nephrol", "davita", "fmc "]),
    ("Eye Care / Ophthalmology",   ["eye care", "ophthalm", "vision", "lasik", "eyenovia", "retina"]),
    ("Sleep Medicine",             ["sleep medicine", "sleep disorder", "sleep lab"]),
    ("Fertility / IVF",            ["fertility", "ivf", "reproductive", "prelude"]),
    ("Podiatry",                   ["podiatry", "foot and ankle", "foot & ankle"]),
    ("ENT / Audiology",            ["ent ", "otolaryn", "audiology", "hearing"]),
    ("Dental",                     ["dental", "dso", "dentist", "heartland dental", "aspen dental", "smile"]),
    ("Home Health",                ["home health", "home-health", "hospice", "aveanna", "amedisys", "lhc ", "encompass home"]),
    ("ASC / Hand Surgery",         ["ambulatory surgery", "asc ", "surgery center", "surgical care"]),
]


def _classify_deal(deal: dict) -> str:
    """Infer primary specialty from deal_name + notes keywords."""
    haystack = (
        str(deal.get("deal_name", "")) + " " +
        str(deal.get("notes", "")) + " " +
        str(deal.get("buyer", ""))
    ).lower()
    for specialty, kws in _SPECIALTY_KEYWORDS:
        for kw in kws:
            if kw in haystack:
                return specialty
    # Default bucket — general hospital / system / mixed
    return "Primary Care"


def _tier_for_density(density: float) -> str:
    if density >= 55.0:
        return "HIGH"
    if density >= 25.0:
        return "MEDIUM"
    return "LOW"


def _score_deal(
    deal: dict,
    footprints_by_specialty: Dict[str, SpecialtyFootprint],
) -> DealEditExposure:
    specialty = _classify_deal(deal)
    fp = footprints_by_specialty.get(specialty)
    if fp is None:
        fp = list(footprints_by_specialty.values())[0]
    ev_mm = deal.get("ev_mm")
    try:
        ev_f = float(ev_mm) if ev_mm is not None else None
    except (TypeError, ValueError):
        ev_f = None

    # Denial exposure = EV × (edit_density / 100) × 0.015 heuristic
    # (≈1.5% of EV at peak density, tapering linearly)
    if ev_f is not None:
        exposure = ev_f * (fp.edit_density_score / 100.0) * 0.015
    else:
        exposure = fp.edit_density_score * 0.85  # fallback proxy in $M

    return DealEditExposure(
        deal_name=str(deal.get("deal_name", "—"))[:80],
        year=int(deal.get("year") or 0),
        buyer=str(deal.get("buyer", "—"))[:60],
        inferred_specialty=specialty,
        edit_density_score=fp.edit_density_score,
        ptp_edits_affecting=fp.ptp_edits_affecting,
        override_eligibility_pct=fp.override_eligibility_pct,
        estimated_annual_denial_exposure_m=round(exposure, 2),
        risk_tier=_tier_for_density(fp.edit_density_score),
        ev_mm=ev_f,
    )


# ---------------------------------------------------------------------------
# Modifier override library
# ---------------------------------------------------------------------------

def _build_modifier_overrides() -> List[ModifierOverride]:
    return [
        ModifierOverride("59", "Distinct Procedural Service",
                         "Overrides PTP edits where the services are truly distinct",
                         72.0, "high",
                         "Most-abused modifier — OIG audit target since 2013; use X{EPSU} where possible"),
        ModifierOverride("XE", "Separate Encounter",
                         "Services occurring in different encounters same DOS",
                         85.0, "low",
                         "Preferred over 59 when a separate encounter can be documented"),
        ModifierOverride("XS", "Separate Structure",
                         "Services on different anatomic structures",
                         88.0, "low",
                         "Documentation must specify structures; strong override"),
        ModifierOverride("XP", "Separate Practitioner",
                         "Services by different practitioners",
                         90.0, "low",
                         "Used in group practices; strongest override"),
        ModifierOverride("XU", "Unusual Non-overlapping Service",
                         "Services not ordinarily encountered",
                         68.0, "medium",
                         "Residual bucket — scrutiny similar to 59"),
        ModifierOverride("25", "Significant Separately Identifiable E/M",
                         "Applies to E/M with same-day procedure",
                         82.0, "medium",
                         "Documentation must show separate complaint/history/exam"),
        ModifierOverride("57", "Decision for Surgery",
                         "E/M that resulted in decision for major surgery within 24h",
                         78.0, "low",
                         "Surgery-decision E/M override; lower audit risk than 25"),
        ModifierOverride("79", "Unrelated Procedure Same Physician Global",
                         "Unrelated procedure during global period",
                         83.0, "medium",
                         "Must document unrelated clinical context"),
        ModifierOverride("50", "Bilateral Procedure",
                         "Procedure performed on both sides of the body",
                         92.0, "low",
                         "Billing allowed at 150% of unilateral rate"),
        ModifierOverride("58", "Staged Procedure Same Physician",
                         "Planned staged or related procedure during global",
                         85.0, "low",
                         "Planned staging must be documented at initial procedure"),
    ]


# ---------------------------------------------------------------------------
# NCCI-to-OIG Work Plan crosswalk
# ---------------------------------------------------------------------------

def _build_audit_crosswalks() -> List[AuditCrosswalk]:
    return [
        AuditCrosswalk("E/M + Same-day Procedure (Mod 25)",
                       "Inappropriate billing of high-level E/M services with procedures",
                       2023, "active", 485.0,
                       "Primary Care, Dermatology, Orthopedics, Urology"),
        AuditCrosswalk("Distinct-Procedural-Service (Mod 59/X{EPSU})",
                       "Recovery auditing of 59-modifier override patterns",
                       2014, "open", 1250.0,
                       "Physical Therapy / Rehab, Radiology, Pain Management, Orthopedics"),
        AuditCrosswalk("MUE Unit-of-Service Violations",
                       "Claims exceeding medically-unlikely unit thresholds",
                       2019, "active", 285.0,
                       "Physical Therapy / Rehab, Podiatry, Dermatology, Pain Management"),
        AuditCrosswalk("Colonoscopy Polypectomy Upcoding",
                       "Billing 45385 when 45378 was clinically appropriate",
                       2022, "active", 125.0,
                       "Gastroenterology"),
        AuditCrosswalk("ESI Multi-Level Billing",
                       "Transforaminal ESI add-on code billing pattern audits",
                       2024, "open", 85.0,
                       "Pain Management"),
        AuditCrosswalk("Cardiac Stress Test Overlap",
                       "Same-day overlap of 78452 and 93350",
                       2021, "active", 62.0,
                       "Cardiology"),
        AuditCrosswalk("Mohs Surgery + Pathology Unbundling",
                       "17311-series billed with separate 88305",
                       2020, "completed", 45.0,
                       "Dermatology"),
        AuditCrosswalk("PT Unit Count & 59 Overuse",
                       "97110 + 97140 + 97530 simultaneous billing with 59",
                       2024, "open", 320.0,
                       "Physical Therapy / Rehab"),
        AuditCrosswalk("Cataract + Same-day YAG",
                       "66984 + 66821 same global period",
                       2018, "completed", 28.0,
                       "Eye Care / Ophthalmology"),
        AuditCrosswalk("Home Health Skilled-Nursing Units",
                       "G0154/G0299 15-min unit inflation",
                       2024, "open", 185.0,
                       "Home Health"),
    ]


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def compute_ncci_scanner() -> NCCIScannerResult:
    corpus = _load_corpus()

    ptp_edits = _build_ptp_edits()
    mue_limits = _build_mue_limits()
    specialty_footprints = _build_specialty_footprints(ptp_edits, mue_limits)
    modifier_overrides = _build_modifier_overrides()
    audit_crosswalks = _build_audit_crosswalks()

    footprints_by_specialty = {sf.specialty: sf for sf in specialty_footprints}

    deal_exposures_full = [_score_deal(d, footprints_by_specialty) for d in corpus]
    # Sort highest risk first, retain top 50 for UI table
    deal_exposures_full.sort(
        key=lambda x: (x.edit_density_score, x.estimated_annual_denial_exposure_m),
        reverse=True,
    )
    deal_exposures = deal_exposures_full[:50]

    # Aggregate KPIs across the full exposure set
    high_risk = sum(1 for d in deal_exposures_full if d.risk_tier == "HIGH")
    total_exposure = sum(d.estimated_annual_denial_exposure_m for d in deal_exposures_full)
    overridable = [e for e in ptp_edits if e.modifier_indicator == 1]
    avg_override_pct = (len(overridable) / len(ptp_edits) * 100.0) if ptp_edits else 0.0

    return NCCIScannerResult(
        total_ptp_edits=len(ptp_edits),
        total_mue_limits=len(mue_limits),
        total_specialties_profiled=len(specialty_footprints),
        avg_override_eligibility_pct=round(avg_override_pct, 1),
        high_risk_deals=high_risk,
        total_estimated_denial_exposure_m=round(total_exposure, 1),
        ptp_edits=ptp_edits,
        mue_limits=mue_limits,
        specialty_footprints=specialty_footprints,
        deal_exposures=deal_exposures,
        modifier_overrides=modifier_overrides,
        audit_crosswalks=audit_crosswalks,
        corpus_deal_count=len(corpus),
    )
