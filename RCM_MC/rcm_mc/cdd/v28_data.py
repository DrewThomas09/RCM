"""CMS-HCC V28 reference data: a deterministic lookup subset.

This ships a representative, clearly-labeled subset of the CMS-HCC V28
community model: an ICD-10 to HCC crosswalk, HCC coefficients, the HCC
hierarchy (more severe HCCs trump less severe ones in the same family), and
demographic factors for the community non-dual aged segment. The full published
model has 115 HCCs and roughly 7,770 codes; drop the complete CMS tables in here
to extend coverage. The mapping path is a pure dictionary lookup. No LLM.

Vintage: CMS-HCC V28, payment year 2024 community model (reference subset).
"""
from __future__ import annotations

import csv
from typing import Dict, List, Mapping, Tuple

VINTAGE = "CMS-HCC V28, PY2024 community model (reference subset)"
SEGMENT = "CNA"  # community non-dual aged (default)

# Community model segments. Each has its own demographic factor table.
SEGMENTS = {
    "CNA": "Community non-dual aged",
    "CND": "Community non-dual disabled",
    "CFA": "Community full-benefit dual aged",
}

# ICD-10 (no dot) to HCC id.
ICD_TO_HCC: Dict[str, str] = {
    "E119": "HCC38",    # Type 2 diabetes without complications
    "E1165": "HCC38",   # Type 2 diabetes with hyperglycemia
    "E1122": "HCC37",   # Type 2 diabetes with diabetic CKD
    "E1142": "HCC37",   # Type 2 diabetes with polyneuropathy
    "I509": "HCC226",   # Heart failure, unspecified
    "I5022": "HCC226",  # Chronic systolic heart failure
    "N186": "HCC329",   # End stage renal disease
    "J449": "HCC280",   # COPD
    "C50911": "HCC151", # Breast cancer
}

# HCC id to (label, community coefficient).
HCC_COEFFICIENTS: Dict[str, Dict[str, object]] = {
    "HCC37": {"label": "Diabetes with chronic complications", "coef": 0.300},
    "HCC38": {"label": "Diabetes with glycemic or no complications", "coef": 0.105},
    "HCC226": {"label": "Heart failure", "coef": 0.330},
    "HCC329": {"label": "End stage renal disease", "coef": 0.435},
    "HCC280": {"label": "COPD", "coef": 0.290},
    "HCC151": {"label": "Breast cancer", "coef": 0.150},
}

# HCC hierarchy: key trumps every HCC in its list (the listed ones are dropped
# when the key is present).
HCC_HIERARCHY: Dict[str, List[str]] = {
    "HCC37": ["HCC38"],
}

# Disease-interaction terms. Each fires only when every HCC in ``requires``
# survives the hierarchy, adding its coefficient on top of the additive sum.
# Reference subset values; drop the published interaction table in to extend.
INTERACTIONS: List[Dict[str, object]] = [
    {"name": "HF_KIDNEY", "label": "Heart failure with kidney disease",
     "requires": ["HCC226", "HCC329"], "coef": 0.100},
    {"name": "HF_COPD", "label": "Heart failure with COPD",
     "requires": ["HCC226", "HCC280"], "coef": 0.080},
]

# Demographic factors keyed by (sex, age_band) for the CNA segment.
AGE_BANDS = [
    (0, 64, "0-64"),
    (65, 69, "65-69"),
    (70, 74, "70-74"),
    (75, 79, "75-79"),
    (80, 84, "80-84"),
    (85, 89, "85-89"),
    (90, 200, "90+"),
]

# CNA demographic factors (default segment, kept stable for the golden fixture).
DEMOGRAPHIC_FACTORS: Dict[str, float] = {
    "M:65-69": 0.330, "M:70-74": 0.395, "M:75-79": 0.485, "M:80-84": 0.600,
    "M:85-89": 0.730, "M:90+": 0.880,
    "F:65-69": 0.300, "F:70-74": 0.360, "F:75-79": 0.440, "F:80-84": 0.540,
    "F:85-89": 0.650, "F:90+": 0.770,
}

# Demographic factors per community segment. CND (disabled) and CFA (full dual)
# carry their own age curves; values are a labeled reference subset.
DEMOGRAPHIC_FACTORS_BY_SEGMENT: Dict[str, Dict[str, float]] = {
    "CNA": DEMOGRAPHIC_FACTORS,
    "CND": {
        "M:0-64": 0.330, "M:65-69": 0.360, "M:70-74": 0.420, "M:75-79": 0.500,
        "F:0-64": 0.320, "F:65-69": 0.340, "F:70-74": 0.380, "F:75-79": 0.460,
    },
    "CFA": {
        "M:65-69": 0.430, "M:70-74": 0.495, "M:75-79": 0.585, "M:80-84": 0.700,
        "M:85-89": 0.830, "M:90+": 0.980,
        "F:65-69": 0.400, "F:70-74": 0.460, "F:75-79": 0.540, "F:80-84": 0.640,
        "F:85-89": 0.750, "F:90+": 0.870,
    },
}


def age_band(age: int) -> str:
    for lo, hi, label in AGE_BANDS:
        if lo <= age <= hi:
            return label
    return "90+"


def demographic_factor(sex: str, age: int, segment: str = "CNA") -> float:
    table = DEMOGRAPHIC_FACTORS_BY_SEGMENT.get(segment, DEMOGRAPHIC_FACTORS)
    key = f"{sex.upper()}:{age_band(age)}"
    return float(table.get(key, 0.0))


def load_crosswalk_csv(path: str) -> Dict[str, str]:
    """Load an ICD-10 to HCC crosswalk from a CSV with columns icd10,hcc.

    Codes are normalized (uppercased, dots stripped) so a real CMS crosswalk
    drops in directly. The mapping stays a pure lookup table. No LLM.
    """
    out: Dict[str, str] = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            code = str(row["icd10"]).replace(".", "").upper().strip()
            out[code] = str(row["hcc"]).strip()
    return out


def load_coefficients_csv(path: str) -> Dict[str, Dict[str, object]]:
    """Load HCC coefficients from a CSV with columns hcc,label,coef."""
    out: Dict[str, Dict[str, object]] = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            out[str(row["hcc"]).strip()] = {
                "label": str(row.get("label", "")).strip(),
                "coef": float(row["coef"]),
            }
    return out
