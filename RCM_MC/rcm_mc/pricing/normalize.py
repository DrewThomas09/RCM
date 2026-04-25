"""Normalization helpers shared across NPPES, Hospital MRF, and TiC.

Real-world MRF data has wildly inconsistent encoding:
  • CPT codes show up as "27447", " 27447 ", "27447.0", "27447 "
  • Payer names: "BCBS-TX", "Blue Cross of Texas", "Blue Cross
    Blue Shield of Texas, Inc.", "BCBSTX"
  • DRGs published as "MS-DRG 470" vs "470" vs "DRG_470"

Without aggressive normalization, the downstream simulator would
treat the same negotiated rate as belonging to four different
payers. These helpers are the canonical surface — every parser
calls into them before writing to the store.
"""
from __future__ import annotations

import re
from typing import Optional, Tuple


# ── Code normalization ───────────────────────────────────────────

_CODE_PUNCT = re.compile(r"[^A-Z0-9]")


def normalize_code(raw: object,
                   code_type: Optional[str] = None) -> Optional[str]:
    """Strip punctuation, uppercase, drop trailing ".0" from numeric
    codes. Returns None for empty / unparseable input.

    Examples::

        normalize_code(" 27447.0 ")   → "27447"
        normalize_code("MS-DRG 470")  → "MSDRG470"
        normalize_code("99213")       → "99213"
    """
    if raw is None:
        return None
    s = str(raw).strip().upper()
    if not s or s in (
        "NULL", "NONE", "N/A", "NA", "—",
        "NOT AVAILABLE", "NOT APPLICABLE",
    ):
        return None
    # Strip a trailing ".0" from numeric ints encoded as floats
    if s.endswith(".0") and s[:-2].isdigit():
        s = s[:-2]
    # CPT/HCPCS codes are 5 chars and may have leading zeros that
    # should be preserved. DRGs vary. Just remove punctuation.
    s = _CODE_PUNCT.sub("", s)
    return s or None


# ── Payer name canonicalization ──────────────────────────────────
#
# Maps the common variants we see in published MRFs to a single
# canonical payer name. New entries can be added without breaking
# downstream — unmatched names fall through unchanged (post-strip).

_PAYER_ALIASES = {
    # UnitedHealthcare
    "UHC": "UnitedHealthcare",
    "UNITED HEALTHCARE": "UnitedHealthcare",
    "UNITED HEALTH CARE": "UnitedHealthcare",
    "UNITED HEALTHCARE INSURANCE COMPANY": "UnitedHealthcare",
    "UNITEDHEALTHCARE": "UnitedHealthcare",
    "UNITED HEALTHCARE OF TEXAS": "UnitedHealthcare",
    # Anthem / Elevance
    "ANTHEM": "Anthem (Elevance)",
    "ANTHEM BLUE CROSS": "Anthem (Elevance)",
    "ELEVANCE": "Anthem (Elevance)",
    "ELEVANCE HEALTH": "Anthem (Elevance)",
    # BCBS regional
    "BCBS TX": "BCBS Texas",
    "BCBS-TX": "BCBS Texas",
    "BCBSTX": "BCBS Texas",
    "BLUE CROSS BLUE SHIELD OF TEXAS": "BCBS Texas",
    "BLUE CROSS BLUE SHIELD OF TEXAS INC": "BCBS Texas",
    "BLUE CROSS OF TEXAS": "BCBS Texas",
    "BCBS IL": "BCBS Illinois",
    "BCBS-IL": "BCBS Illinois",
    "BLUE CROSS BLUE SHIELD OF ILLINOIS": "BCBS Illinois",
    "BCBS NJ": "BCBS New Jersey",
    "BCBS-NJ": "BCBS New Jersey",
    "HORIZON BCBSNJ": "BCBS New Jersey",
    # Aetna / CVS Health
    "AETNA": "Aetna (CVS)",
    "AETNA INC": "Aetna (CVS)",
    "AETNA HEALTH INC": "Aetna (CVS)",
    "AETNA INSURANCE COMPANY": "Aetna (CVS)",
    # Cigna
    "CIGNA": "Cigna",
    "CIGNA HEALTH AND LIFE INSURANCE CO": "Cigna",
    "CIGNA HEALTHSPRING": "Cigna",
    # Humana
    "HUMANA": "Humana",
    "HUMANA HEALTH PLAN INC": "Humana",
    "HUMANA INSURANCE COMPANY": "Humana",
    # Medicare / Medicaid (federal/state programs)
    "MEDICARE": "Medicare FFS",
    "MEDICARE PART A": "Medicare FFS",
    "MEDICARE FFS": "Medicare FFS",
    "MEDICARE ADVANTAGE": "Medicare Advantage",
    "MEDICAID": "Medicaid",
    "MEDICAID MANAGED CARE": "Medicaid Managed Care",
}


def normalize_payer_name(raw: object) -> str:
    """Canonicalise a payer string into a known alias if possible.

    Returns the input (stripped) when no alias matches. Empty input
    becomes an empty string — never None — so downstream PRIMARY
    KEYs don't blow up on NULL.
    """
    if raw is None:
        return ""
    s = str(raw).strip()
    if not s:
        return ""
    key = re.sub(r"[^A-Z0-9 ]", "", s.upper())
    key = re.sub(r"\s+", " ", key).strip()
    return _PAYER_ALIASES.get(key, s)


# ── Geography: ZIP5 → CBSA (metropolitan statistical area) ───────
#
# Real CBSA crosswalks are 41,000 rows (HUD publishes the file).
# We embed a small commonly-used subset for tests + day-one usage;
# loaders can override via ``zip_to_cbsa.crosswalk_path = ...``.

_ZIP_CBSA_DEFAULT = {
    # Texas
    "75001": "19100", "75201": "19100", "76101": "19100",  # DFW
    "77001": "26420", "77002": "26420", "77003": "26420",
    "77030": "26420",                                       # Houston
    "78201": "41700", "78202": "41700", "78216": "41700",  # San Antonio
    "78701": "12420", "78702": "12420",                    # Austin
    "75901": "00000",                                      # Lufkin (rural)
    # Illinois
    "60601": "16980", "60602": "16980", "60611": "16980",  # Chicago
    # New Jersey
    "07001": "35620", "07601": "35620",                    # NYC metro NJ
    # California
    "90001": "31080", "90210": "31080", "94102": "41860",
    # New York
    "10001": "35620", "10005": "35620",
}


def zip_to_cbsa(zip5: object,
                crosswalk: Optional[dict] = None) -> Optional[str]:
    """Look up CBSA code for a 5-digit ZIP. Returns ``None`` if
    the ZIP isn't in the embedded crosswalk and no override was
    passed in. Pass a richer ``crosswalk`` dict to extend coverage.
    """
    if zip5 is None:
        return None
    s = str(zip5).strip()
    # Trim ZIP+4 suffix
    if "-" in s:
        s = s.split("-", 1)[0]
    if not s.isdigit():
        return None
    s = s.zfill(5)[:5]
    table = crosswalk if crosswalk is not None else _ZIP_CBSA_DEFAULT
    return table.get(s)


# ── Service-line classifier ──────────────────────────────────────
#
# Rough mapping from CPT/DRG ranges to PE-relevant service lines,
# used for analytics rollups in downstream packets.

_CPT_SERVICE_LINES: Tuple[Tuple[str, int, int, str], ...] = (
    ("CPT", 10021, 19499, "Surgery — Integumentary/Breast"),
    ("CPT", 20100, 29999, "Surgery — Musculoskeletal/Ortho"),
    ("CPT", 30000, 32999, "Surgery — Respiratory"),
    ("CPT", 33010, 37799, "Surgery — Cardiovascular"),
    ("CPT", 38100, 39599, "Surgery — Hemic/Lymphatic"),
    ("CPT", 40490, 49999, "Surgery — Digestive"),
    ("CPT", 50010, 53899, "Surgery — Urinary"),
    ("CPT", 54000, 55899, "Surgery — Male Genital"),
    ("CPT", 56405, 58999, "Surgery — Female Genital"),
    ("CPT", 59000, 59899, "Surgery — Maternity/Delivery"),
    ("CPT", 60000, 69990, "Surgery — Endocrine/ENT/Eye"),
    ("CPT", 70010, 79999, "Imaging — Radiology"),
    ("CPT", 80047, 89398, "Lab/Pathology"),
    ("CPT", 90281, 99607, "E&M / Medicine"),
)


def classify_service_line(code: Optional[str],
                          code_type: Optional[str] = None,
                          ) -> Optional[str]:
    """Return a coarse service-line label for a normalized code.
    Used by downstream packets for cross-payer rollups.
    """
    if not code:
        return None

    ct = (code_type or "").upper()

    # DRG ranges (Medicare MS-DRG groupings)
    if ct in ("DRG", "MSDRG", "MS-DRG"):
        try:
            n = int(re.sub(r"[^0-9]", "", str(code)) or "0")
        except ValueError:
            return None
        if 1 <= n <= 8:
            return "Transplant"
        if 23 <= n <= 42:
            return "Nervous System / Neurosurgery"
        if 163 <= n <= 208:
            return "Respiratory / Pulmonary"
        if 215 <= n <= 316:
            return "Circulatory / Cardiac"
        if 326 <= n <= 395:
            return "Digestive / GI"
        if 460 <= n <= 471:
            return "Musculoskeletal / Joint"
        if 581 <= n <= 605:
            return "Endocrine / Diabetes"
        if 765 <= n <= 782:
            return "Maternity / Newborn"
        return "Other Inpatient"

    # CPT (numeric, 5 digits)
    try:
        n = int(re.sub(r"[^0-9]", "", str(code)) or "0")
    except ValueError:
        return None

    for kind, lo, hi, label in _CPT_SERVICE_LINES:
        if lo <= n <= hi:
            return label
    return None
