"""CMS-HCC risk-adjustment factor library — stdlib-only, curated.

This is the native, in-philosophy reimplementation of the slice of
the Tuva `cms_hcc` mart we actually need for diligence: turn a
target's demographic mix + diagnosed-condition profile into a Risk
Adjustment Factor (RAF) so peer cost/outcome comparisons can be put
on a case-mix-normalized footing.

Why a curated library instead of the official grouper or the Tuva
mart:
    1. **Zero new runtime dependencies.** The full CMS-HCC model and
       the Tuva mart both assume a dbt/warehouse stack and a
       beneficiary-level claims extract you only get in confirmatory
       diligence. This module runs on the aggregate condition mix you
       can assemble from public CMS files or a banker's book, with
       nothing beyond stdlib.
    2. **Auditable.** Every coefficient lives in one tuple a partner
       can read, with its segment and source documented — the same
       pattern as ``payer_library.py``.
    3. **Swappable.** When a real claims extract arrives, the
       ``optional Myelin/Tuva adapter`` (see
       ``docs/TUVA_MYELIN_INTEGRATION.md``) can replace
       :func:`compute_raf` with the certified grouper without any
       caller change — both return a :class:`RiskScore`.

CALIBRATION + SCOPE (read before trusting a number):
    The coefficients below are *representative* of the CMS-HCC V28
    (payment-year 2024+) **community, non-dual, aged** segment — the
    single most common payment segment, used here as the diligence
    default. They are a CURATED SUBSET (~24 of the ~115 payment HCCs)
    covering the highest-prevalence / highest-weight conditions that
    move a panel's RAF, not the full model. Magnitudes are in the
    published ballpark but are NOT payment-grade; for payment-grade
    precision use the official CMS factor table (published with each
    Rate Announcement) or the Tuva HCC mart. Refresh annually when CMS
    publishes the new factors.

The RAF decomposition this module produces is the standard one:

    RAF = demographic_factor
        + Σ disease_HCC_coefficients   (after hierarchy "trumping")
        + Σ disease_interaction_factors

A RAF of 1.0 is the program-average beneficiary. A panel RAF of 1.30
means the panel is 30% sicker than average and you would *expect* its
costs to run ~30% above the program mean before judging the operator.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

CITATION_KEY = "RA1"
SOURCE_MODULE = "diligence.risk_adjustment"

# Segment this curated table is calibrated to. The full model carries
# a coefficient per (segment × HCC); we ship the most common one and
# document the limitation rather than implying full coverage.
SEGMENT = "CMS-HCC V28 · Community · Non-Dual · Aged"


# ────────────────────────────────────────────────────────────────────
# Demographic factors  (community, non-dual, aged + disabled bands)
# ────────────────────────────────────────────────────────────────────
# Keyed by (sex, age_band). Representative V28 community NonDual values.
# Disabled (under-65) bands carry the "CND" disabled coefficients.
_DEMOGRAPHIC_FACTORS: Dict[Tuple[str, str], float] = {
    # Aged — Female
    ("F", "65-69"): 0.305, ("F", "70-74"): 0.357, ("F", "75-79"): 0.443,
    ("F", "80-84"): 0.518, ("F", "85-89"): 0.616, ("F", "90-94"): 0.702,
    ("F", "95+"): 0.747,
    # Aged — Male
    ("M", "65-69"): 0.349, ("M", "70-74"): 0.444, ("M", "75-79"): 0.541,
    ("M", "80-84"): 0.654, ("M", "85-89"): 0.779, ("M", "90-94"): 0.857,
    ("M", "95+"): 0.882,
    # Disabled (under-65) — representative single band per sex
    ("F", "<65-disabled"): 0.358,
    ("M", "<65-disabled"): 0.330,
}


def _age_band(age: int, disabled: bool) -> str:
    """Map an age to the CMS age/sex band. Under-65 enrollees are
    'disabled' bands (they qualify for Medicare via disability)."""
    if age < 65:
        return "<65-disabled"
    if age >= 95:
        return "95+"
    if age >= 90:
        return "90-94"
    if age >= 85:
        return "85-89"
    if age >= 80:
        return "80-84"
    if age >= 75:
        return "75-79"
    if age >= 70:
        return "70-74"
    return "65-69"


def demographic_factor(sex: str, age: int, disabled: bool = False) -> float:
    """Return the age/sex demographic component of the RAF.

    Unknown sex falls back to the female table (the more conservative,
    lower-weight side, so an unknown-sex panel does not get an
    inflated RAF it cannot defend in diligence)."""
    s = (sex or "F").strip().upper()[:1]
    if s not in ("M", "F"):
        s = "F"
    band = _age_band(int(age), disabled or int(age) < 65)
    return _DEMOGRAPHIC_FACTORS.get((s, band), 0.0)


# ────────────────────────────────────────────────────────────────────
# Disease HCC factors
# ────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class HCCFactor:
    """One Hierarchical Condition Category.

    ``hierarchy`` groups HCCs whose severities trump one another: only
    the highest-coefficient HCC in a hierarchy family counts (CMS
    calls this the disease hierarchy / "trumping"). e.g. metastatic
    cancer trumps lung cancer trumps localized breast/prostate.
    """
    hcc: str                 # model id (V28 family label; see SCOPE note)
    label: str
    coefficient: float       # SEGMENT coefficient
    hierarchy: Optional[str] = None   # family key; None = standalone
    rank: int = 0            # within a family, higher = more severe
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hcc": self.hcc, "label": self.label,
            "coefficient": self.coefficient,
            "hierarchy": self.hierarchy, "rank": self.rank,
            "notes": self.notes,
        }


# Curated subset. coefficient = SEGMENT value (representative; see SCOPE).
HCC_FACTORS: Tuple[HCCFactor, ...] = (
    # Diabetes hierarchy
    HCCFactor("DIAB_CHRONIC", "Diabetes w/ chronic complications",
              0.166, hierarchy="DIABETES", rank=2),
    HCCFactor("DIAB_NOCOMP", "Diabetes w/o complication",
              0.105, hierarchy="DIABETES", rank=1),
    # Cancer hierarchy
    HCCFactor("CANCER_METASTATIC", "Metastatic cancer / acute leukemia",
              1.024, hierarchy="CANCER", rank=4),
    HCCFactor("CANCER_LUNG", "Lung / severe cancers",
              0.711, hierarchy="CANCER", rank=3),
    HCCFactor("CANCER_OTHER", "Other major cancers",
              0.301, hierarchy="CANCER", rank=2),
    HCCFactor("CANCER_LOCAL", "Breast / prostate / localized cancer",
              0.146, hierarchy="CANCER", rank=1),
    # Renal hierarchy
    HCCFactor("ESRD_DIALYSIS", "ESRD / dialysis status",
              0.435, hierarchy="RENAL", rank=3),
    HCCFactor("CKD_5", "CKD stage 5",
              0.237, hierarchy="RENAL", rank=2),
    HCCFactor("CKD_4", "CKD stage 4",
              0.127, hierarchy="RENAL", rank=1),
    # Cardiac / vascular (standalone — they interact, don't trump)
    HCCFactor("CHF", "Congestive heart failure", 0.300),
    HCCFactor("IHD", "Ischemic heart disease / angina", 0.135),
    HCCFactor("ARRHYTHMIA", "Specified heart arrhythmias", 0.224),
    HCCFactor("VASCULAR", "Vascular disease (PAD)", 0.276),
    HCCFactor("STROKE", "Stroke / cerebral hemorrhage", 0.230),
    # Respiratory
    HCCFactor("COPD", "COPD / chronic respiratory failure", 0.234),
    # Psych / neuro
    HCCFactor("DEMENTIA", "Dementia (with/without complication)", 0.346,
              notes="Added as a payment HCC in V28."),
    HCCFactor("SCHIZOPHRENIA", "Schizophrenia", 0.524),
    HCCFactor("DEPRESSION_BIPOLAR", "Major depression / bipolar", 0.309),
    HCCFactor("SEIZURE", "Seizure disorders / epilepsy", 0.211),
    # Inflammatory / metabolic / other
    HCCFactor("RHEUMATOID", "Rheumatoid arthritis / inflammatory", 0.367),
    HCCFactor("MORBID_OBESITY", "Morbid obesity", 0.250),
    HCCFactor("SEPSIS", "Sepsis", 0.371),
    HCCFactor("PRESSURE_ULCER", "Pressure ulcer (severe)", 1.018),
    HCCFactor("HIP_FRACTURE", "Hip / pelvic fracture", 0.305),
)

_HCC_BY_ID: Dict[str, HCCFactor] = {f.hcc: f for f in HCC_FACTORS}


def get_hcc(hcc_id: str) -> Optional[HCCFactor]:
    return _HCC_BY_ID.get(hcc_id)


# ────────────────────────────────────────────────────────────────────
# Disease interactions  (V28 keeps a small, documented set)
# ────────────────────────────────────────────────────────────────────
# Each entry: (frozenset of required HCC ids) -> (label, coefficient).
# Interactions are additive on top of the disease coefficients.
DISEASE_INTERACTIONS: Tuple[Tuple[frozenset, str, float], ...] = (
    (frozenset({"DIAB_CHRONIC", "CHF"}), "Diabetes × CHF", 0.121),
    (frozenset({"DIAB_NOCOMP", "CHF"}), "Diabetes × CHF", 0.121),
    (frozenset({"CHF", "COPD"}), "CHF × COPD", 0.155),
    (frozenset({"CHF", "ESRD_DIALYSIS"}), "CHF × renal failure", 0.203),
    (frozenset({"CHF", "CKD_5"}), "CHF × renal failure", 0.203),
    (frozenset({"COPD", "CKD_5"}), "COPD × renal failure", 0.149),
)


# ────────────────────────────────────────────────────────────────────
# Condition → HCC crosswalk
# ────────────────────────────────────────────────────────────────────
# Maps both ICD-10 prefixes and free-text keywords onto a model HCC.
# This is the curated stand-in for the Tuva ICD-10 → HCC terminology
# set; it covers the conditions in HCC_FACTORS, not all of ICD-10.
_ICD10_PREFIX_TO_HCC: Tuple[Tuple[str, str], ...] = (
    # Diabetes E10/E11 — .2x/.3x/.4x/.5x/.6x ranges are complications
    ("E1009", "DIAB_NOCOMP"), ("E119", "DIAB_NOCOMP"),
    ("E102", "DIAB_CHRONIC"), ("E103", "DIAB_CHRONIC"),
    ("E104", "DIAB_CHRONIC"), ("E105", "DIAB_CHRONIC"),
    ("E112", "DIAB_CHRONIC"), ("E113", "DIAB_CHRONIC"),
    ("E114", "DIAB_CHRONIC"), ("E115", "DIAB_CHRONIC"),
    ("E1165", "DIAB_NOCOMP"),
    # Cancer
    ("C77", "CANCER_METASTATIC"), ("C78", "CANCER_METASTATIC"),
    ("C79", "CANCER_METASTATIC"), ("C80", "CANCER_METASTATIC"),
    ("C92", "CANCER_METASTATIC"), ("C91", "CANCER_METASTATIC"),
    ("C34", "CANCER_LUNG"), ("C25", "CANCER_LUNG"), ("C22", "CANCER_LUNG"),
    ("C18", "CANCER_OTHER"), ("C56", "CANCER_OTHER"),
    ("C50", "CANCER_LOCAL"), ("C61", "CANCER_LOCAL"),
    # Renal
    ("N186", "ESRD_DIALYSIS"), ("Z992", "ESRD_DIALYSIS"),
    ("N185", "CKD_5"), ("N184", "CKD_4"),
    # Cardiac / vascular
    ("I50", "CHF"), ("I110", "CHF"),
    ("I20", "IHD"), ("I25", "IHD"),
    ("I48", "ARRHYTHMIA"), ("I47", "ARRHYTHMIA"),
    ("I70", "VASCULAR"), ("I73", "VASCULAR"),
    ("I63", "STROKE"), ("I61", "STROKE"),
    # Respiratory
    ("J44", "COPD"), ("J96", "COPD"),
    # Psych / neuro
    ("F00", "DEMENTIA"), ("F01", "DEMENTIA"), ("F02", "DEMENTIA"),
    ("F03", "DEMENTIA"), ("G30", "DEMENTIA"),
    ("F20", "SCHIZOPHRENIA"), ("F25", "SCHIZOPHRENIA"),
    ("F31", "DEPRESSION_BIPOLAR"), ("F32", "DEPRESSION_BIPOLAR"),
    ("F33", "DEPRESSION_BIPOLAR"),
    ("G40", "SEIZURE"),
    # Other
    ("M05", "RHEUMATOID"), ("M06", "RHEUMATOID"),
    ("E660", "MORBID_OBESITY"), ("E662", "MORBID_OBESITY"),
    ("A41", "SEPSIS"), ("R652", "SEPSIS"),
    ("L89", "PRESSURE_ULCER"),
    ("S72", "HIP_FRACTURE"),
)

_KEYWORD_TO_HCC: Tuple[Tuple[str, str], ...] = (
    ("metastat", "CANCER_METASTATIC"), ("leukemia", "CANCER_METASTATIC"),
    ("lung cancer", "CANCER_LUNG"), ("pancrea", "CANCER_LUNG"),
    ("breast cancer", "CANCER_LOCAL"), ("prostate cancer", "CANCER_LOCAL"),
    ("colon cancer", "CANCER_OTHER"), ("cancer", "CANCER_OTHER"),
    ("dialysis", "ESRD_DIALYSIS"), ("esrd", "ESRD_DIALYSIS"),
    ("ckd stage 5", "CKD_5"), ("ckd 5", "CKD_5"),
    ("ckd stage 4", "CKD_4"), ("ckd 4", "CKD_4"),
    ("diabetes with", "DIAB_CHRONIC"),
    ("diabetic neuropathy", "DIAB_CHRONIC"),
    ("diabetic retinopathy", "DIAB_CHRONIC"),
    ("diabetes", "DIAB_NOCOMP"),
    ("heart failure", "CHF"), ("chf", "CHF"), ("congestive", "CHF"),
    ("ischemic heart", "IHD"), ("angina", "IHD"), ("coronary", "IHD"),
    ("atrial fibrillation", "ARRHYTHMIA"), ("arrhythmia", "ARRHYTHMIA"),
    ("peripheral arter", "VASCULAR"), ("vascular disease", "VASCULAR"),
    ("stroke", "STROKE"), ("cerebral", "STROKE"),
    ("copd", "COPD"), ("emphysema", "COPD"),
    ("chronic respiratory", "COPD"),
    ("dementia", "DEMENTIA"), ("alzheimer", "DEMENTIA"),
    ("schizophren", "SCHIZOPHRENIA"),
    ("bipolar", "DEPRESSION_BIPOLAR"),
    ("major depress", "DEPRESSION_BIPOLAR"),
    ("seizure", "SEIZURE"), ("epilep", "SEIZURE"),
    ("rheumatoid", "RHEUMATOID"),
    ("morbid obesity", "MORBID_OBESITY"),
    ("sepsis", "SEPSIS"),
    ("pressure ulcer", "PRESSURE_ULCER"),
    ("decubitus", "PRESSURE_ULCER"),
    ("hip fracture", "HIP_FRACTURE"),
)


def map_condition_to_hcc(code_or_text: str) -> Optional[str]:
    """Resolve an ICD-10 code OR a free-text condition to a model HCC.

    ICD-10 is tried first (longest-prefix wins so 'E1165' beats 'E11'),
    then keyword matching. Returns the HCC id, or None if unmapped —
    unmapped conditions are surfaced (not silently dropped) by the
    scorer so the analyst can see crosswalk coverage."""
    if not code_or_text:
        return None
    raw = str(code_or_text).strip()
    # ICD-10 path: strip the dot, upper-case, longest-prefix match.
    code = raw.replace(".", "").upper()
    best: Optional[Tuple[str, str]] = None
    for prefix, hcc in _ICD10_PREFIX_TO_HCC:
        if code.startswith(prefix) and (
            best is None or len(prefix) > len(best[0])
        ):
            best = (prefix, hcc)
    if best is not None:
        return best[1]
    # Keyword path.
    low = raw.lower()
    for kw, hcc in _KEYWORD_TO_HCC:
        if kw in low:
            return hcc
    return None


def apply_hierarchies(hcc_ids: Sequence[str]) -> List[str]:
    """Apply the CMS disease hierarchy: within a hierarchy family keep
    only the highest-rank (most severe) HCC. Standalone HCCs (no
    family) all survive. Order is preserved for the survivors so the
    output is deterministic."""
    # Find, per family, the surviving (max-rank) HCC.
    family_best: Dict[str, Tuple[int, str]] = {}
    standalone: List[str] = []
    seen: set = set()
    ordered_unique: List[str] = []
    for h in hcc_ids:
        if h in seen:
            continue
        seen.add(h)
        ordered_unique.append(h)
    for h in ordered_unique:
        f = _HCC_BY_ID.get(h)
        if f is None:
            continue
        if f.hierarchy is None:
            standalone.append(h)
        else:
            cur = family_best.get(f.hierarchy)
            if cur is None or f.rank > cur[0]:
                family_best[f.hierarchy] = (f.rank, h)
    survivors = {h for _, h in family_best.values()} | set(standalone)
    return [h for h in ordered_unique if h in survivors]
