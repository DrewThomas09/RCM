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

from typing import Dict, List

VINTAGE = "CMS-HCC V28, PY2024 community model (reference subset)"
SEGMENT = "CNA"  # community non-dual aged

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

DEMOGRAPHIC_FACTORS: Dict[str, float] = {
    "M:65-69": 0.330, "M:70-74": 0.395, "M:75-79": 0.485, "M:80-84": 0.600,
    "M:85-89": 0.730, "M:90+": 0.880,
    "F:65-69": 0.300, "F:70-74": 0.360, "F:75-79": 0.440, "F:80-84": 0.540,
    "F:85-89": 0.650, "F:90+": 0.770,
}


def age_band(age: int) -> str:
    for lo, hi, label in AGE_BANDS:
        if lo <= age <= hi:
            return label
    return "90+"


def demographic_factor(sex: str, age: int) -> float:
    key = f"{sex.upper()}:{age_band(age)}"
    return float(DEMOGRAPHIC_FACTORS.get(key, 0.0))
