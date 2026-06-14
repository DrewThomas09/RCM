"""Subsector taxonomy data model.

The diligence workbench historically carried only three first-class
"verticals" (ASC, MSO, behavioral health) plus the hospital default, while a
dermatology roll-up, a home-health agency, an MA plan, and a CDMO are
diligenced with fundamentally different metrics, reimbursement mechanics, and
data. This module is the structured taxonomy layer that the rest of the
platform reads when it needs to know *how* a given subsector is analysed —
which KPIs, which billing codes, which public datasets, which CDD exhibits.

Everything here is **pure data + frozen dataclasses**: no network, no SQLite,
no fabricated benchmarks. KPI benchmark strings are deliberately free-text
(``"target <25% over 120 days"``) rather than numbers, because they are
directional trade/advisory ranges that vary by setting and year — encoding
them as hard floats would imply a precision the sources do not support. The
registry that fills these structures lives in :mod:`rcm_mc.taxonomy.registry`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Tuple


class Grouping(str, Enum):
    """The six top-level groupings PE uses to organise healthcare subsectors.

    String-valued so a grouping round-trips through JSON / query params as its
    human label without a separate lookup.
    """

    PROVIDER_SERVICES = "Provider Services / Physician Practice Management"
    FACILITY_BASED = "Facility-Based Care"
    HEALTHCARE_IT = "Healthcare IT / Tech-Enabled Services"
    PAYER_RISK = "Payer / Risk-Bearing"
    PHARMA_SERVICES = "Pharma Services / Life Sciences Tools"
    CONSUMER_OTHER = "Consumer / Other"


@dataclass(frozen=True)
class KPI:
    """One diligence KPI for a subsector.

    ``benchmark`` is free-text on purpose (see the module docstring): it carries
    the public range *and* its caveat (``"~98% target, often <85%"``) instead of
    collapsing to a single number that would read as authoritative.
    """

    name: str
    unit: str = ""          # "ratio" | "pct" | "count" | "dollars" | "days" | ""
    benchmark: str = ""     # directional range / value, free-text
    note: str = ""


@dataclass(frozen=True)
class Subsector:
    """A single healthcare subsector and everything needed to diligence it.

    The ``vertical`` field crosswalks to the existing
    :class:`rcm_mc.verticals.registry.Vertical` enum where one of the four
    first-class metric registries already exists; ``nucc_verticals`` crosswalks
    to the PE-vertical tags in :mod:`rcm_mc.data_public.nucc_taxonomy` so a
    subsector can be turned into an NPPES provider-supply count. Both are empty
    when no mapping exists rather than forced into an approximate bucket.
    """

    id: str                                    # stable slug, e.g. "dermatology"
    name: str
    grouping: Grouping
    business_model: str
    kpis: Tuple[KPI, ...] = ()
    reimbursement_codes: Tuple[str, ...] = ()  # CPT/HCPCS/DRG/CDT/ASA references
    reimbursement_mechanics: str = ""
    data_sources: Tuple[str, ...] = ()
    thesis: str = ""
    risks: str = ""
    exhibits: Tuple[str, ...] = ()             # CDD exhibit templates
    nucc_verticals: Tuple[str, ...] = ()       # crosswalk to nucc_taxonomy.VERTICALS
    vertical: str = ""                         # crosswalk to verticals.Vertical
    central: bool = False                      # one of Part D's most-central archetypes
    deep_dive: str = ""                        # extra diligence-question detail (central only)

    def matches(self, query: str) -> bool:
        """Case-insensitive substring match across the fields an analyst would
        search on (id, name, business model, thesis, risks). Used by the search
        helper and the CLI so ``taxonomy search "site-of-service"`` finds the
        ASC/orthopedics entries by their thesis text, not just their names."""
        q = query.strip().lower()
        if not q:
            return False
        haystack = " ".join(
            (self.id, self.name, self.business_model, self.thesis, self.risks)
        ).lower()
        return q in haystack


__all__ = ["Grouping", "KPI", "Subsector"]
