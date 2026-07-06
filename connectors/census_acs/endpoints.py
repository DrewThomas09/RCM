"""Declarative specs for every Census ACS 5-year profile this connector ingests.

One :class:`EndpointSpec` per geography profile (county / state / CBSA).
The spec is the single place that knows Census-ACS-specific quirks: which
geography string the API expects in ``for=``, which geography columns the
API appends to each response row, whether an ``in=state:XX`` predicate is
supported, and the canonical table the normalizer writes into.

Why specs and not code branches: adding or retuning a profile (or a
variable) is a data edit here, never new routing logic elsewhere. The
registry rows (:mod:`connectors.census_acs.registry`) and the connector
both read these.

Every profile is built from TWO calls per year — the *detail* dataset
(``/data/{year}/acs/acs5``, B-tables) and the *subject* dataset
(``/data/{year}/acs/acs5/subject``, S-tables) — joined on the geography
columns. The variable ids below were verified live against the 2023
vintage via the keyless metadata endpoints, e.g.
``https://api.census.gov/data/2023/acs/acs5/variables/B01001_001E.json``
and ``.../acs/acs5/subject/variables/S0101_C01_030E.json`` (all 200 with
the expected labels on 2026-07-06). The CBSA geography string was
verified against ``/data/2023/acs/acs5/geography.json`` (present in both
detail and subject).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

_CENSUS_BASE = "https://api.census.gov/data"

# The vintage the estate refreshes annually. New ACS 5-year vintages land
# each December; bump this (or pass ``--year``) when 2024 publishes.
DEFAULT_YEAR = 2023

# ── Declared variable → canonical column mappings (never guessed) ──────
# Detail (B-) tables, ``/data/{year}/acs/acs5``. Verified live for 2023:
#   B01001_001E  Estimate!!Total:                       (total population)
#   B01002_001E  Estimate!!Median age --!!Total:
#   B19013_001E  Estimate!!Median household income (2023 infl.-adj. $)
#   B17001_002E  Estimate!!Total:!!Income below poverty level:
DETAIL_VARIABLES: Dict[str, str] = {
    "B01001_001E": "total_pop",
    "B01002_001E": "median_age",
    "B19013_001E": "median_hh_income",
    "B17001_002E": "poverty_count",
}

# Subject (S-) tables, ``/data/{year}/acs/acs5/subject``. Verified live
# for 2023:
#   S0101_C01_030E  Estimate!!Total!!Total population!!SELECTED AGE
#                   CATEGORIES!!65 years and over      (pop 65+, a count)
#   S2701_C05_001E  Estimate!!Percent Uninsured!!Civilian
#                   noninstitutionalized population    (uninsured rate, %)
# S0101_C01_030E replaces the assignment's twelve-variable
# B01001_020E..049E sum — one verified subject cell, same number.
SUBJECT_VARIABLES: Dict[str, str] = {
    "S0101_C01_030E": "pop_65_plus",
    "S2701_C05_001E": "uninsured_rate",
}

# Geography / label headers the API appends to each row, renamed to the
# canonical column names the tables use.
GEO_RENAMES: Dict[str, str] = {
    "NAME": "name",
    "state": "state_fips",
    "county": "county_fips",
    "metropolitan statistical area/micropolitan statistical area": "cbsa_code",
}


@dataclass(frozen=True)
class EndpointSpec:
    """One ACS 5-year geography profile.

    Attributes
    ----------
    key:
        Short dataset id, also the ``/v1/query/{dataset}`` slug suffix and
        the value written into each row's ``source_endpoint`` column.
    geo_for:
        The ``for=`` geography clause (e.g. ``county:*``). The CBSA
        string carries slashes and spaces — the transport URL-encodes it.
    geo_cols:
        Geography columns the API appends to each row for this ``for=``
        clause, in response order. These (plus the year) compose the
        natural upsert key.
    supports_in_state:
        Whether an ``in=state:XX`` predicate narrows this geography
        (counties nest in states; states and CBSAs do not take ``in``).
    target_table:
        Canonical table the normalizer upserts into (one per profile —
        the three geographies have different natural keys).
    """

    key: str
    geo_for: str
    geo_cols: Tuple[str, ...]
    supports_in_state: bool
    target_table: str
    join_keys: Tuple[str, ...] = ()
    refresh_cadence: str = "annual"
    date_field: str = "year"
    default_params: Dict[str, str] = field(default_factory=dict)

    @property
    def dataset_id(self) -> str:
        return f"census_acs_{self.key}"

    @property
    def base_url(self) -> str:
        return _CENSUS_BASE

    def detail_path(self, year: int) -> str:
        """Path of the detail (B-table) dataset for a vintage."""
        return f"/{int(year)}/acs/acs5"

    def subject_path(self, year: int) -> str:
        """Path of the subject (S-table) dataset for a vintage."""
        return f"/{int(year)}/acs/acs5/subject"


ENDPOINTS: Dict[str, EndpointSpec] = {
    s.key: s for s in (
        EndpointSpec(
            key="county_profile",
            geo_for="county:*",
            geo_cols=("state", "county"),
            supports_in_state=True,
            target_table="census_acs_county",
            join_keys=("state_fips", "county_fips"),
            default_params={"year": str(DEFAULT_YEAR), "for": "county:*"},
        ),
        EndpointSpec(
            key="state_profile",
            geo_for="state:*",
            geo_cols=("state",),
            supports_in_state=False,
            target_table="census_acs_state",
            join_keys=("state_fips",),
            default_params={"year": str(DEFAULT_YEAR), "for": "state:*"},
        ),
        EndpointSpec(
            key="cbsa_profile",
            geo_for=("metropolitan statistical area/"
                     "micropolitan statistical area:*"),
            geo_cols=("metropolitan statistical area/"
                      "micropolitan statistical area",),
            supports_in_state=False,
            target_table="census_acs_cbsa",
            join_keys=("cbsa_code",),
            default_params={
                "year": str(DEFAULT_YEAR),
                "for": ("metropolitan statistical area/"
                        "micropolitan statistical area:*"),
            },
        ),
    )
}


def get_endpoint(key: str) -> EndpointSpec:
    """Look up an endpoint spec by key, raising a clear error if absent.

    Accepts either the short key (``county_profile``) or the full dataset
    id (``census_acs_county_profile``) so CLI callers can paste either.
    """
    short = key[len("census_acs_"):] if key.startswith("census_acs_") else key
    try:
        return ENDPOINTS[short]
    except KeyError as exc:
        raise KeyError(
            f"unknown Census ACS endpoint {key!r}; known: {sorted(ENDPOINTS)}"
        ) from exc


def profile_endpoints() -> List[EndpointSpec]:
    return list(ENDPOINTS.values())
