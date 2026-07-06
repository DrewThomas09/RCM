"""Declarative specs for the BLS QCEW open CSV slice API.

The Quarterly Census of Employment & Wages publishes pre-cut CSV
"slices" behind stable URLs — no key, no JSON envelope, no paging::

    https://data.bls.gov/cew/data/api/{year}/{qtr}/industry/{naics}.csv
      → one row per area x ownership for that industry
    https://data.bls.gov/cew/data/api/{year}/{qtr}/area/{area_fips}.csv
      → one row per industry x ownership for that county/MSA/state

Both slice kinds return the SAME 42-column quarterly row shape (verified
live 2026-07-06 — see tables.py), so both datasets land in one shared
table and are told apart by ``source_endpoint`` (the cms_coverage
shared-table + ``source_filter`` pattern).

Availability window (probed live 2026-07-06, one URL per candidate
year/qtr): quarterly slices exist for **2014 Q1 through 2025 Q4**;
2013 and earlier return 404 (BLS keeps older QCEW data in ZIP files,
not this API), and 2026 Q1 is not out yet. :data:`LATEST_YEAR` /
:data:`LATEST_QTR` pin the newest published quarter as the default so a
bare ``fetch`` always lands on data that exists; BLS publishes quarter
Q roughly five months after it ends, so bump these when a new quarter
ships (a stale pin still works — it just isn't the newest data).

Annual-average slices (``qtr=a``) exist but publish a DIFFERENT column
set (``annual_avg_estabs``, ``avg_annual_pay``, …); they would corrupt
the quarterly table, so ``qtr`` is restricted to 1-4 here and the
annual files are documented as out of scope in the README.

Why specs and not code branches: adding or retuning a slice kind is a
data edit here, never new routing logic elsewhere. The registry rows
(:mod:`connectors.bls_qcew.registry`) and the connector both read these.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

_BLS_BASE = "https://data.bls.gov"
_API_PREFIX = "/cew/data/api"

# Newest published quarter + oldest year this API still serves.
# Verified live 2026-07-06: /2025/4/... → 200, /2026/1/... → 404,
# /2014/1/... → 200, /2013/1/... → 404.
LATEST_YEAR = 2025
LATEST_QTR = "4"
EARLIEST_YEAR = 2014

# Default slice codes: NAICS 62 = Health Care and Social Assistance
# (the sector this estate cares about); US000 = national total area.
DEFAULT_INDUSTRY = "62"
DEFAULT_AREA = "US000"

# QCEW industry codes are NAICS-ish: digits, optionally a hyphenated
# sector range ("31-33"). Area codes are 5-char FIPS-ish tokens that may
# lead with letters ("48453", "US000", "C4266" for MSAs, "CS0018").
_INDUSTRY_RE = re.compile(r"^[0-9]{1,6}(-[0-9]{1,6})?$")
_AREA_RE = re.compile(r"^[0-9A-Za-z]{1,7}$")
_YEAR_RE = re.compile(r"^[0-9]{4}$")
_VALID_QTRS = ("1", "2", "3", "4")


@dataclass(frozen=True)
class EndpointSpec:
    """One QCEW slice kind.

    Attributes
    ----------
    key:
        Short dataset id (``industry_area`` / ``area_industry``), also
        the value written into each row's ``source_endpoint`` column so
        the two slice kinds sharing one table stay individually
        queryable, and part of the composed upsert key so an
        observation fetched through both slices can never make one
        dataset's rows vanish from the other (see normalize.py).
    slice_kind:
        ``industry`` or ``area`` — which URL path segment the slice
        code fills.
    code_param:
        The ``params`` key callers use for the slice code (``industry``
        or ``area``); keeps CLI flags and default_params self-describing.
    path_template:
        The registry-facing endpoint template (placeholders, not
        f-string) — :func:`slice_path` renders it after validation.
    """

    key: str
    slice_kind: str
    code_param: str
    path_template: str
    target_table: str = "qcew_industry_area"
    default_code: str = ""
    join_keys: Tuple[str, ...] = ("area_fips", "industry_code")
    refresh_cadence: str = "quarterly"
    date_field: str = "year"
    default_params: Dict[str, str] = field(default_factory=dict)

    @property
    def dataset_id(self) -> str:
        return f"bls_qcew_{self.key}"

    @property
    def base_url(self) -> str:
        return _BLS_BASE


ENDPOINTS: Dict[str, EndpointSpec] = {
    "industry_area": EndpointSpec(
        key="industry_area",
        slice_kind="industry",
        code_param="industry",
        path_template=f"{_API_PREFIX}/{{year}}/{{qtr}}/industry/{{industry}}.csv",
        default_code=DEFAULT_INDUSTRY,
        default_params={"industry": DEFAULT_INDUSTRY,
                        "year": str(LATEST_YEAR), "qtr": LATEST_QTR},
    ),
    "area_industry": EndpointSpec(
        key="area_industry",
        slice_kind="area",
        code_param="area",
        path_template=f"{_API_PREFIX}/{{year}}/{{qtr}}/area/{{area}}.csv",
        default_code=DEFAULT_AREA,
        default_params={"area": DEFAULT_AREA,
                        "year": str(LATEST_YEAR), "qtr": LATEST_QTR},
    ),
}


def get_endpoint(key: str) -> EndpointSpec:
    """Look up an endpoint spec by key, raising a clear error if absent."""
    try:
        return ENDPOINTS[key]
    except KeyError as exc:
        raise KeyError(
            f"unknown QCEW endpoint {key!r}; known: {sorted(ENDPOINTS)}"
        ) from exc


def slice_path(spec: EndpointSpec, year: object, qtr: object, code: object
               ) -> str:
    """Render + validate one slice URL path.

    Validation happens *before* any network call so a bad year/qtr/code
    fails instantly with a message naming the live-verified window,
    instead of burning a request on a guaranteed 404. The code lands in
    a URL path segment, so the whitelist regexes double as the
    identifier-injection guard.
    """
    y = str(year).strip()
    q = str(qtr).strip()
    c = str(code).strip()
    if not _YEAR_RE.match(y):
        raise ValueError(
            f"bad QCEW year {year!r}: expected a 4-digit year in "
            f"{EARLIEST_YEAR}-{LATEST_YEAR} (window verified live 2026-07-06)")
    if q.lower() == "a":
        raise ValueError(
            "QCEW annual-average slices (qtr='a') publish a different "
            "column set and are not supported by this connector; use "
            "qtr 1-4 (see connectors/bls_qcew/README.md)")
    if q not in _VALID_QTRS:
        raise ValueError(
            f"bad QCEW qtr {qtr!r}: expected one of {_VALID_QTRS}; the "
            f"latest published quarter is {LATEST_YEAR} Q{LATEST_QTR}")
    if spec.slice_kind == "industry":
        if not _INDUSTRY_RE.match(c):
            raise ValueError(
                f"bad NAICS industry code {code!r}: expected digits "
                f"(optionally a hyphenated sector range like 31-33), "
                f"e.g. 62, 621, 622, 623, 6216")
    else:
        if not _AREA_RE.match(c):
            raise ValueError(
                f"bad QCEW area code {code!r}: expected a FIPS-ish token "
                f"like 48453 (county), 48000 (state), C4266 (MSA), "
                f"US000 (national)")
    return spec.path_template.format(year=y, qtr=q,
                                     **{spec.code_param: c})


def resolve_params(spec: EndpointSpec, params: Dict[str, object]
                   ) -> Dict[str, str]:
    """Merge caller params over the spec defaults → ``{code,year,qtr}``.

    Rejects a slice code meant for the *other* dataset (``area=`` on
    ``industry_area`` and vice versa) instead of silently ignoring it —
    that mistake would otherwise fetch the default slice and look like
    success.
    """
    merged = dict(spec.default_params)
    for k, v in (params or {}).items():
        if v is None:
            continue
        if k not in ("year", "qtr", spec.code_param):
            raise ValueError(
                f"dataset {spec.key!r} takes params "
                f"({spec.code_param!r}, 'year', 'qtr'); got {k!r}")
        merged[k] = str(v)
    return merged


def known_endpoints() -> List[EndpointSpec]:
    return list(ENDPOINTS.values())
