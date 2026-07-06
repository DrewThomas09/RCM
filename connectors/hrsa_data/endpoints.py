"""Declarative specs for every HRSA data-download file this connector ingests.

One :class:`EndpointSpec` per source CSV file. The spec is the single
place that knows HRSA-specific quirks: the exact download file name
(verified live — see below), the raw CSV headers the idempotent upsert
key is composed from, the discipline tag for the three HPSA files that
share one canonical table, and the canonical table the normalizer
writes into.

Why specs and not code branches: adding or retuning a file is a data
edit here, never new routing logic elsewhere. The registry rows
(:mod:`connectors.hrsa_data.registry`) and the connector both read
these.

File names were verified live on 2026-07-06 against
``https://data.hrsa.gov/DataDownload/DD_Files/{name}`` (every one
returned 200 with the expected header row). If HRSA renames a file the
transport raises a clear 404 error pointing at
https://data.hrsa.gov/data/download where the current names are listed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

_HRSA_BASE = "https://data.hrsa.gov"
_DD_PREFIX = "/DataDownload/DD_Files"


@dataclass(frozen=True)
class EndpointSpec:
    """One HRSA CSV download file.

    Attributes
    ----------
    key:
        Short dataset id, also the ``/v1/query/{dataset}`` slug and the
        value written into each row's ``source_endpoint`` column so
        files sharing a table (the three HPSA disciplines) stay
        individually queryable.
    file_name:
        The exact CSV file name under ``/DataDownload/DD_Files/``
        (case-sensitive; verified live).
    target_table:
        Canonical table the normalizer upserts into.
    dataset_kind:
        ``hpsa`` | ``mua`` | ``health_center_sites``. Drives which
        normalizer mapper runs.
    discipline:
        Machine token for the HPSA discipline (``primary_care`` /
        ``dental`` / ``mental_health``); part of the composed upsert
        key so the three files sharing ``hrsa_hpsa`` can never collide.
        ``None`` for non-HPSA files.
    id_fields:
        Ordered *raw* CSV headers the composed upsert key is built from
        in the normalizer (validated for uniqueness against the full
        live files; residual duplicates in the source are byte-identical
        lines, which an upsert collapses harmlessly).
    date_field:
        Canonical (snake_cased) column used for recency / registry
        ``date_field``.
    """

    key: str
    file_name: str
    target_table: str
    dataset_kind: str
    discipline: Optional[str] = None
    id_fields: Tuple[str, ...] = ()
    date_field: Optional[str] = None
    join_keys: Tuple[str, ...] = ()
    refresh_cadence: str = "monthly"
    default_params: Dict[str, str] = field(default_factory=dict)

    @property
    def dataset_id(self) -> str:
        return f"hrsa_data_{self.key}"

    @property
    def path(self) -> str:
        return f"{_DD_PREFIX}/{self.file_name}"

    @property
    def base_url(self) -> str:
        return _HRSA_BASE


# ── HPSA: Health Professional Shortage Areas (three disciplines, one
#    table; each row is one component geography of a designation) ──────
_HPSA_ID_FIELDS = ("HPSA ID", "HPSA Geography Identification Number")
_HPSA_COMMON = dict(
    target_table="hrsa_hpsa",
    dataset_kind="hpsa",
    id_fields=_HPSA_ID_FIELDS,
    date_field="hpsa_designation_last_update_date",
    join_keys=("common_state_abbreviation", "common_state_county_fips_code"),
    refresh_cadence="monthly",
)

_HPSA: List[EndpointSpec] = [
    EndpointSpec(
        key="hpsa_primary_care",
        file_name="BCD_HPSA_FCT_DET_PC.csv",       # ~48 MB, 79k rows (2026-07)
        discipline="primary_care",
        **_HPSA_COMMON,
    ),
    EndpointSpec(
        key="hpsa_dental",
        file_name="BCD_HPSA_FCT_DET_DH.csv",       # ~28 MB, 46k rows (2026-07)
        discipline="dental",
        **_HPSA_COMMON,
    ),
    EndpointSpec(
        key="hpsa_mental_health",
        file_name="BCD_HPSA_FCT_DET_MH.csv",       # ~25 MB, 41k rows (2026-07)
        discipline="mental_health",
        **_HPSA_COMMON,
    ),
]

# ── MUA/P: Medically Underserved Areas/Populations (component rows) ───
_MUA: List[EndpointSpec] = [
    EndpointSpec(
        key="mua",
        file_name="MUA_DET.csv",                   # ~11 MB, 20k rows (2026-07)
        target_table="hrsa_mua",
        dataset_kind="mua",
        # MUA/P IDs are re-used across designations (a Designated and a
        # Withdrawn designation can share an ID *and* a geography), so
        # the service-area name is part of the key; the three geography
        # fields distinguish component rows within one designation.
        id_fields=(
            "MUA/P ID",
            "MUA/P Service Area Name",
            "State and County Federal Information Processing Standard Code",
            "County Subdivision FIPS Code",
            "Census Tract",
            "Medically Underserved Area/Population (MUA/P) Component Geographic Name",
        ),
        date_field="mua_p_update_date_string",
        join_keys=("state_abbreviation",
                   "state_and_county_federal_information_processing_standard_code"),
        refresh_cadence="monthly",
    ),
]

# ── Health Center Program service delivery + look-alike sites ─────────
_SITES: List[EndpointSpec] = [
    EndpointSpec(
        key="health_center_sites",
        # ~14 MB, 19k rows (2026-07)
        file_name="Health_Center_Service_Delivery_and_LookAlike_Sites.csv",
        target_table="hrsa_health_center_sites",
        dataset_kind="health_center_sites",
        # The BPHC-assigned site number is unique across the live file.
        id_fields=("BPHC Assigned Number",),
        date_field="site_added_to_scope_this_date",
        join_keys=("fqhc_site_npi_number", "site_state_abbreviation"),
        refresh_cadence="monthly",
    ),
]

ENDPOINTS: Dict[str, EndpointSpec] = {
    s.key: s for s in (_HPSA + _MUA + _SITES)
}


def get_endpoint(key: str) -> EndpointSpec:
    """Look up an endpoint spec by key, raising a clear error if absent."""
    try:
        return ENDPOINTS[key]
    except KeyError as exc:
        raise KeyError(
            f"unknown HRSA data endpoint {key!r}; known: {sorted(ENDPOINTS)}"
        ) from exc


def hpsa_endpoints() -> List[EndpointSpec]:
    return [s for s in ENDPOINTS.values() if s.dataset_kind == "hpsa"]
