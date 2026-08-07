"""Every NUCC taxonomy code → a Level-I grouping and a PE-facing category.

Why this is structural rather than a lookup table
-------------------------------------------------
NPPES tags every one of its ~8 million NPIs with at least one NUCC
taxonomy code, and a master file that only understands hospitals
understands almost nothing: the code space runs from allopathic
physicians through ambulance suppliers, infusion pharmacies, dialysis
clinics and residential treatment facilities.

The full NUCC code set is ~870 codes and is published by NUCC, not by
CMS. It is not bundled in this repository and nucc.org is not reachable
from this build. Hand-writing 870 codes from memory would be inventing
reference data, which is the one thing a crosswalk must never do.

What IS a documented, checkable property of the code set is its
structure. A NUCC code is ten characters — three digits of grouping,
six of classification and specialisation, one trailing letter — and the
leading two digits identify one of the 29 Level-I groupings. That
mapping is stable, and it is checkable here: every distinct code
appearing in this repository's real provider data resolves through it,
and a test asserts exactly that against the data rather than against a
list copied from anywhere.

So classification is *derived from the code*, not looked up. A real
NUCC table, if one is ever vendored, enriches this with the official
classification and specialisation strings — see :func:`load_nucc_table`
— but nothing below depends on it.

Two levels of answer
--------------------
``level_i`` is the NUCC grouping — "Hospitals", "Agencies",
"Transportation Services". Derived from the two-digit prefix, so it is
available for every well-formed code.

``category`` is the PE-facing bucket a deal team screens on. It starts
as the category implied by the Level-I grouping (which is the same
claim as the grouping, just in our vocabulary) and is then *refined*
where a longer prefix says something narrower and verifiable: an
Agency is a ``home_health`` agency at ``251E``, a Supplier is an
``infusion`` pharmacy at ``3336I``.

Refinements are the only place a category can be wrong in a way the
grouping isn't, so the refinement table holds only prefixes
corroborated by reference data already in this repository —
``data_public/nucc_taxonomy.py``, ``npi_cleaner/refdata.py`` and
``npi_recovery/reference/infusion_taxonomies.csv``. A prefix nobody
here can vouch for is left alone and keeps its grouping-level
category. An honest coarse answer beats a precise wrong one.
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Tuple

#: A NUCC code: three digits, six alphanumerics, one trailing letter.
#: The trailing letter is NOT always "X" — 261QI0500N (Infusion Therapy
#: clinic) and 251F00000X sit in the same file, and a pattern that
#: assumes X silently loses whole specialisations.
NUCC_CODE_RE = re.compile(r"^[0-9]{3}[0-9A-Z]{6}[A-Z]$")

_NUCC_CSV = (Path(__file__).resolve().parent / "vendor" / "nucc"
             / "nucc_taxonomy.csv")


# ── The 29 Level-I groupings, by the leading two digits ────────────
#
# Individual and group providers occupy 10-24 plus 36, 37 and 39;
# organisations occupy 25-34 and 38. There is no "35" grouping — a code
# starting 35 is malformed, and saying so is more useful than inventing
# a home for it.
_LEVEL_I_BY_PREFIX: Dict[str, str] = {
    "10": "Behavioral Health & Social Service Providers",
    "11": "Chiropractic Providers",
    "12": "Dental Providers",
    "13": "Dietary & Nutritional Service Providers",
    "14": "Emergency Medical Service Providers",
    "15": "Eye and Vision Services Providers",
    "16": "Nursing Service Providers",
    "17": "Other Service Providers",
    "18": "Pharmacy Service Providers",
    "19": "Group",
    "20": "Allopathic & Osteopathic Physicians",
    "21": "Podiatric Medicine & Surgery Service Providers",
    "22": "Respiratory, Developmental, Rehabilitative and Restorative "
          "Service Providers",
    "23": "Speech, Language and Hearing Service Providers",
    "24": "Technologists, Technicians & Other Technical Service Providers",
    "25": "Agencies",
    "26": "Ambulatory Health Care Facilities",
    "27": "Hospital Units",
    "28": "Hospitals",
    "29": "Laboratories",
    "30": "Managed Care Organizations",
    "31": "Nursing & Custodial Care Facilities",
    "32": "Residential Treatment Facilities",
    "33": "Suppliers",
    "34": "Transportation Services",
    "36": "Physician Assistants & Advanced Practice Nursing Providers",
    "37": "Nursing Service Related Providers",
    "38": "Respite Care Facility",
    "39": "Student, Health Care",
}

#: True where the Level-I grouping describes an organisation rather than
#: a person. Individual NPIs cannot own anything, which is what makes
#: this matter to parent resolution: an individual can be a leaf of the
#: ownership tree but never an interior node.
_ORGANISATION_PREFIXES = frozenset(
    {"19", "25", "26", "27", "28", "29", "30", "31", "32", "33", "34", "38"})


# ── The category each grouping implies ─────────────────────────────
#
# Same claim as the grouping, expressed in the vocabulary a deal team
# screens on. "Other Service Providers" is deliberately absent: the
# grouping itself declines to say what the provider is, so we do too.
_CATEGORY_BY_LEVEL_I_PREFIX: Dict[str, str] = {
    "10": "behavioral",
    "11": "chiropractic",
    "12": "dental",
    "13": "dietary",
    "14": "emergency_medical",
    "15": "vision",
    "16": "nursing",
    "18": "pharmacy",
    "19": "group",
    "20": "physician",
    "21": "podiatry",
    "22": "therapy",
    "23": "speech_hearing",
    "24": "technician",
    "25": "agency",
    "26": "clinic",
    "27": "hospital_unit",
    "28": "hospital",
    "29": "lab",
    "30": "managed_care",
    "31": "nursing_facility",
    "32": "residential_treatment",
    "33": "supplier",
    "34": "medical_transport",
    "36": "advanced_practice",
    "37": "nursing_related",
    "38": "respite",
    "39": "student",
}


# ── Refinements, by the longest prefix that settles it ─────────────
#
# Every entry here is narrower than its grouping and is corroborated by
# reference data already in this repository. Prefixes that merely look
# plausible are omitted on purpose: "261Q" is Clinic/Center generally,
# so it stays ``clinic``, while "261QE07" (End-Stage Renal Disease) and
# "261QI05" (Infusion Therapy) earn their own category.
#
# Source column names the in-repo file that vouches for the prefix.
_CATEGORY_BY_PREFIX: Dict[str, str] = {
    # Agencies — data_public/nucc_taxonomy.py
    "251E": "home_health",
    "251F": "infusion",
    "251G": "hospice",
    "253Z": "in_home_support",
    # Ambulatory facilities — data_public/nucc_taxonomy.py,
    # npi_recovery/reference/infusion_taxonomies.csv
    "261QA19": "ambulatory_surgery",
    "261QE07": "dialysis",
    "261QF04": "federally_qualified_health_center",
    "261QI05": "infusion",
    "261QM": "behavioral",
    "261QU02": "urgent_care",
    # Nursing & custodial — data_public/nucc_taxonomy.py
    "314": "snf",
    # Suppliers — infusion_taxonomies.csv, npi_cleaner/refdata.py
    "332B": "dme",
    "3336": "pharmacy",
    "3336H": "infusion",
    "3336I": "infusion",
    # Transportation — npi_cleaner/refdata.py
    "3416": "ambulance",
}

_MAX_PREFIX = max(len(p) for p in _CATEGORY_BY_PREFIX)
_MIN_PREFIX = min(len(p) for p in _CATEGORY_BY_PREFIX)


@dataclass(frozen=True)
class TaxonomyClass:
    """What a NUCC code says about a provider."""

    code: str
    level_i: str
    category: str
    is_organisation: bool

    @property
    def is_individual(self) -> bool:
        return bool(self.level_i) and not self.is_organisation

    @property
    def is_known(self) -> bool:
        return bool(self.level_i)


@lru_cache(maxsize=None)
def classify_taxonomy(code: Any) -> TaxonomyClass:
    """Level-I grouping and PE category for one NUCC code.

    A malformed code — or one in the unused "35" block — returns blanks
    rather than a guess, and ``is_organisation`` is False so a junk code
    can never be mistaken for an owner.
    """
    text = str(code or "").strip().upper()
    if not NUCC_CODE_RE.match(text):
        return TaxonomyClass(text, "", "", False)

    prefix2 = text[:2]
    level_i = _LEVEL_I_BY_PREFIX.get(prefix2, "")
    if not level_i:
        return TaxonomyClass(text, "", "", False)

    category = _CATEGORY_BY_LEVEL_I_PREFIX.get(prefix2, "")
    for length in range(_MAX_PREFIX, _MIN_PREFIX - 1, -1):
        hit = _CATEGORY_BY_PREFIX.get(text[:length])
        if hit:
            category = hit
            break

    return TaxonomyClass(text, level_i, category,
                         prefix2 in _ORGANISATION_PREFIXES)


def taxonomy_category(code: Any) -> str:
    """The PE-facing bucket, or empty when the code does not settle it."""
    return classify_taxonomy(code).category


def taxonomy_level_i(code: Any) -> str:
    """The NUCC Level-I grouping, or empty for a malformed code."""
    return classify_taxonomy(code).level_i


def is_organisation_taxonomy(code: Any) -> bool:
    """True when the code describes an organisation rather than a person.

    Parent resolution leans on this: an individual NPI has no
    subsidiaries, so it can be a leaf but never an owner.
    """
    return classify_taxonomy(code).is_organisation


def all_categories() -> Tuple[str, ...]:
    """Every category this module can emit, sorted.

    Exported so the master-file schema can be documented and validated
    without importing the private tables.
    """
    return tuple(sorted(set(_CATEGORY_BY_LEVEL_I_PREFIX.values())
                        | set(_CATEGORY_BY_PREFIX.values())))


@lru_cache(maxsize=1)
def load_nucc_table() -> Dict[str, Dict[str, str]]:
    """The official NUCC code set, if one has been vendored.

    Pure enrichment — code → classification and specialisation strings.
    Nothing above depends on it, and it is empty in this build because
    the NUCC code set is published at nucc.org, which this environment
    cannot reach. Drop the published CSV at
    ``vendor/nucc/nucc_taxonomy.csv`` and it is picked up on the next
    process.
    """
    if not _NUCC_CSV.exists():
        return {}
    out: Dict[str, Dict[str, str]] = {}
    try:
        with _NUCC_CSV.open(newline="", encoding="utf-8-sig") as fh:
            for row in csv.DictReader(fh):
                code = str(row.get("Code") or row.get("code") or "").strip().upper()
                if not NUCC_CODE_RE.match(code):
                    continue
                out[code] = {
                    "grouping": str(row.get("Grouping") or "").strip(),
                    "classification": str(row.get("Classification") or "").strip(),
                    "specialization": str(row.get("Specialization") or "").strip(),
                    "display_name": str(row.get("Display Name") or "").strip(),
                }
    except (OSError, ValueError):
        return {}
    return out


def taxonomy_label(code: Any) -> str:
    """Best available human label: the official one if vendored, else the
    derived Level-I grouping, else the bare code."""
    text = str(code or "").strip().upper()
    official = load_nucc_table().get(text)
    if official:
        spec = official.get("specialization") or ""
        base = official.get("classification") or official.get("display_name") or ""
        return f"{base} - {spec}" if spec and base else (base or spec or text)
    return classify_taxonomy(text).level_i or text


def _clear_cache() -> None:
    """Test hook."""
    classify_taxonomy.cache_clear()
    load_nucc_table.cache_clear()
