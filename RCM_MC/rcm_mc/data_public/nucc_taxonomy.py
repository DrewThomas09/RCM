"""NUCC Health Care Provider Taxonomy crosswalk — provider supply by vertical.

NPPES tags every enrolled provider with one or more NUCC taxonomy codes. The
infusion page hard-coded the three infusion codes inline; this module is the
general crosswalk so *any* PE vertical can count provider supply by taxonomy
instead of re-listing codes per page.

NUCC codes and their grouping/classification/specialization are public facts
(the NUCC code set is published). This is a curated subset — the provider types
PE actually diligences (infusion, home health, hospice, SNF, dialysis, ASC,
urgent care, dental, behavioral, physician primary care) — not the full ~870-
code set; extend ``_TAXONOMIES`` as new verticals come up. Pure data + lookups:
nothing here touches the network or fabricates a provider.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class Taxonomy:
    code: str            # NUCC taxonomy code, e.g. "261QI0500N"
    grouping: str        # top NUCC grouping, e.g. "Ambulatory Health Care Facilities"
    classification: str  # e.g. "Clinic/Center"
    specialization: str  # e.g. "Infusion Therapy" ("" if none)
    vertical: str        # PE vertical tag, e.g. "infusion"
    kind: str            # PE-friendly label, e.g. "Ambulatory infusion center (AIC)"

    @property
    def label(self) -> str:
        """Human label matching the legacy infusion convention
        ``"<classification> — <specialization>"`` (classification alone when
        there is no specialization)."""
        return (f"{self.classification} — {self.specialization}"
                if self.specialization else self.classification)


# Curated crosswalk. Codes are public NUCC facts; ``vertical``/``kind`` are our
# PE-facing labels. Order is stable for deterministic listings.
_TAXONOMIES: List[Taxonomy] = [
    # Infusion (kept byte-identical to the legacy nppes_infusion constants).
    Taxonomy("261QI0500N", "Ambulatory Health Care Facilities", "Clinic/Center",
             "Infusion Therapy", "infusion", "Ambulatory infusion center (AIC)"),
    Taxonomy("3336I0012X", "Suppliers", "Pharmacy",
             "Infusion Therapy", "infusion", "Infusion pharmacy"),
    Taxonomy("251F00000X", "Agencies", "Agencies",
             "Home Infusion", "infusion", "Home-infusion agency"),
    # Home health.
    Taxonomy("251E00000X", "Agencies", "Agencies",
             "Home Health", "home_health", "Home-health agency"),
    # Hospice.
    Taxonomy("251G00000X", "Agencies", "Agencies",
             "Community Based Hospice Care", "hospice", "Community hospice agency"),
    # Skilled nursing.
    Taxonomy("314000000X", "Nursing & Custodial Care Facilities",
             "Skilled Nursing Facility", "", "snf", "Skilled nursing facility"),
    # Dialysis.
    Taxonomy("261QE0700X", "Ambulatory Health Care Facilities", "Clinic/Center",
             "End-Stage Renal Disease (ESRD) Treatment", "dialysis",
             "Dialysis center"),
    # Ambulatory surgery.
    Taxonomy("261QA1903X", "Ambulatory Health Care Facilities", "Clinic/Center",
             "Ambulatory Surgical", "asc", "Ambulatory surgery center"),
    # Urgent care.
    Taxonomy("261QU0200X", "Ambulatory Health Care Facilities", "Clinic/Center",
             "Urgent Care", "urgent_care", "Urgent-care center"),
    # Dental.
    Taxonomy("122300000X", "Dental Providers", "Dentist",
             "", "dental", "Dentist"),
    # Behavioral health.
    Taxonomy("261QM0801X", "Ambulatory Health Care Facilities", "Clinic/Center",
             "Mental Health (Including Community Mental Health Center)",
             "behavioral", "Behavioral-health clinic"),
    # Physician primary care.
    Taxonomy("207Q00000X", "Allopathic & Osteopathic Physicians",
             "Family Medicine", "", "physician_primary_care",
             "Family-medicine physician"),
]

_BY_CODE: Dict[str, Taxonomy] = {t.code: t for t in _TAXONOMIES}

# PE verticals the crosswalk covers, in first-seen order.
VERTICALS: List[str] = list(dict.fromkeys(t.vertical for t in _TAXONOMIES))


def all_taxonomies() -> List[Taxonomy]:
    return list(_TAXONOMIES)


def by_code(code: str) -> Taxonomy | None:
    """Look up one taxonomy by code, or ``None`` if it isn't in the crosswalk
    (the caller treats unknown codes as out-of-scope, not as an error)."""
    return _BY_CODE.get(str(code).strip().upper())


def for_vertical(vertical: str) -> List[Taxonomy]:
    """Every taxonomy mapped to a PE vertical (empty list if unknown)."""
    v = str(vertical).strip().lower()
    return [t for t in _TAXONOMIES if t.vertical == v]


def descriptions_for(vertical: str) -> List[str]:
    """The distinct NPPES ``taxonomy_description`` tokens to query for a
    vertical — the specialization where present, else the classification.
    De-duplicated, order-stable. This is what the NPPES API matches on."""
    out: List[str] = []
    for t in for_vertical(vertical):
        token = t.specialization or t.classification
        if token and token not in out:
            out.append(token)
    return out
