"""Declarative specs for every OIG LEIE download this connector ingests.

One :class:`EndpointSpec` per dataset. The spec is the single place that
knows OIG-specific quirks: the full-replacement file URL, the monthly
supplement path pattern, the raw CSV headers the idempotent upsert key
is composed from, and the canonical table the normalizer writes into.

Why specs and not code branches: adding or retuning a dataset is a data
edit here, never new routing logic elsewhere. The registry rows
(:mod:`connectors.oig_leie.registry`) and the connector both read these.

URLs were verified live on 2026-07-06:

  * ``/exclusions/downloadables/UPDATED.csv`` — the full-replacement
    LEIE database (~83k rows, ~15 MB, refreshed monthly; header row
    LASTNAME,FIRSTNAME,MIDNAME,BUSNAME,GENERAL,SPECIALTY,UPIN,NPI,DOB,
    ADDRESS,CITY,STATE,ZIP,EXCLTYPE,EXCLDATE,REINDATE,WAIVERDATE,
    WVRSTATE).
  * ``/exclusions/downloadables/{yyyy}/{yy}{mm}excl.csv`` — the monthly
    exclusions supplement (new exclusions added that month; usually
    14-70 KB). Same 18-column header as the full file.
  * ``/exclusions/downloadables/{yyyy}/{yy}{mm}rein.csv`` — the monthly
    reinstatements supplement (providers reinstated that month, i.e.
    removed from the LEIE; REINDATE populated). Same header.

Not every month publishes both supplement files (verified live: the
exclusions-list page links no ``2505excl.csv`` and no ``2601rein.csv``),
so the connector walks back from the current month when no explicit
month is requested. The published index of supplement files lives at
https://oig.hhs.gov/exclusions/exclusions_list.asp.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

_OIG_BASE = "https://oig.hhs.gov"
_DL_PREFIX = "/exclusions/downloadables"

# Raw CSV headers the composed upsert key is built from (in order).
# Validated against the FULL live UPDATED.csv (83,464 rows, 2026-06-30
# vintage): this composition leaves 31 duplicate keys / 32 excess rows,
# of which 25 are byte-identical source lines and 6 differ only in city
# spelling or specialty — an upsert collapses them harmlessly. Without
# ADDRESS the key would collapse 31 *distinct* multi-location business
# exclusions (same entity excluded at several addresses), which a
# compliance screen must keep.
_EXCL_ID_FIELDS: Tuple[str, ...] = (
    "LASTNAME", "FIRSTNAME", "MIDNAME", "BUSNAME", "DOB", "EXCLDATE",
    "NPI", "ADDRESS",
)
# Reinstatement rows accumulate across months, and the same person can
# be excluded and reinstated more than once — REINDATE joins the key.
_REIN_ID_FIELDS: Tuple[str, ...] = _EXCL_ID_FIELDS + ("REINDATE",)


def supplement_path(file_kind: str, year: int, month: int) -> str:
    """The monthly supplement path, e.g. ``.../2026/2605excl.csv``.

    The live pattern (verified 2026-07-06) is a 4-digit year directory
    and a 2-digit-year + 2-digit-month file name: May 2026 exclusions
    live at ``/exclusions/downloadables/2026/2605excl.csv``.
    """
    if file_kind not in ("excl", "rein"):
        raise ValueError(f"file_kind must be 'excl' or 'rein', got {file_kind!r}")
    year, month = int(year), int(month)
    if not 1 <= month <= 12:
        raise ValueError(f"month must be 1-12, got {month!r}")
    return f"{_DL_PREFIX}/{year:04d}/{year % 100:02d}{month:02d}{file_kind}.csv"


@dataclass(frozen=True)
class EndpointSpec:
    """One OIG LEIE download dataset.

    Attributes
    ----------
    key:
        Short dataset id; also the base of each row's
        ``source_endpoint`` provenance tag (supplement rows append the
        resolved ``:YYYY-MM``).
    target_table:
        Canonical table the normalizer upserts into.
    dataset_kind:
        ``full`` (the always-available UPDATED.csv) or ``supplement``
        (a month-parameterised delta file).
    file_kind:
        ``excl`` | ``rein`` — the supplement file-name suffix. The full
        file is exclusions-shaped, so it carries ``excl`` too.
    id_fields:
        Ordered *raw* CSV headers the composed upsert key is built from
        in the normalizer (validated against the full live file; see
        module docstring for the residual-duplicate audit).
    date_field:
        Canonical (snake_cased) column used for recency / registry
        ``date_field``.
    """

    key: str
    target_table: str
    dataset_kind: str
    file_kind: str
    id_fields: Tuple[str, ...]
    date_field: str
    join_keys: Tuple[str, ...] = ("npi",)
    refresh_cadence: str = "monthly"
    default_params: Dict[str, str] = field(default_factory=dict)

    @property
    def dataset_id(self) -> str:
        return f"oig_leie_{self.key}"

    @property
    def base_url(self) -> str:
        return _OIG_BASE

    @property
    def path_template(self) -> str:
        """Human-readable path (registry ``endpoint`` field). Supplement
        datasets show the month placeholders they resolve at fetch time."""
        if self.dataset_kind == "full":
            return f"{_DL_PREFIX}/UPDATED.csv"
        return f"{_DL_PREFIX}/{{yyyy}}/{{yy}}{{mm}}{self.file_kind}.csv"

    def path(self, year: int = None, month: int = None) -> str:
        """Resolve the concrete download path for one fetch."""
        if self.dataset_kind == "full":
            return f"{_DL_PREFIX}/UPDATED.csv"
        if year is None or month is None:
            raise ValueError(
                f"dataset {self.key!r} is a monthly supplement; year and "
                f"month are required to resolve its path")
        return supplement_path(self.file_kind, year, month)


ENDPOINTS: Dict[str, EndpointSpec] = {
    s.key: s for s in (
        EndpointSpec(
            key="exclusions",
            target_table="oig_exclusions",
            dataset_kind="full",
            file_kind="excl",
            id_fields=_EXCL_ID_FIELDS,
            date_field="excldate",
        ),
        EndpointSpec(
            key="supplement",
            # Incremental adds merge into the SAME cumulative table as
            # the full file (same natural key), so a compliance screen
            # of oig_exclusions always sees the freshest union.
            target_table="oig_exclusions",
            dataset_kind="supplement",
            file_kind="excl",
            id_fields=_EXCL_ID_FIELDS,
            date_field="excldate",
        ),
        EndpointSpec(
            key="reinstatements",
            target_table="oig_reinstatements",
            dataset_kind="supplement",
            file_kind="rein",
            id_fields=_REIN_ID_FIELDS,
            date_field="reindate",
        ),
    )
}


def get_endpoint(key: str) -> EndpointSpec:
    """Look up an endpoint spec by key, raising a clear error if absent."""
    try:
        return ENDPOINTS[key]
    except KeyError as exc:
        raise KeyError(
            f"unknown OIG LEIE endpoint {key!r}; known: {sorted(ENDPOINTS)}"
        ) from exc
