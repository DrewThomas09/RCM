"""Map raw OIG LEIE CSV rows → canonical rows.

The LEIE publishes clean uppercase headers (``LASTNAME`` … ``WVRSTATE``)
but sentinel-laden values, so the core of this module is the pair of
value rules every compliance consumer needs applied *before* screening:

  * :func:`clean_npi` — the LEIE stores ``0000000000`` when the NPI is
    unknown (~85% of the historic file). That sentinel is normalized to
    ``''`` so an NPI join can never "match" tens of thousands of
    unrelated exclusions — the single most dangerous foot-gun in this
    dataset.
  * :func:`iso_date` — dates are ``yyyymmdd`` with ``00000000`` = null;
    normalized to ISO ``yyyy-mm-dd`` (sortable, joinable) or ``''``.

:func:`snake` is the one documented header→column rule — tables.py's
column lists are snapshots of the live header row passed through it,
which is what keeps "the schema is derived from a live sample" honest
and reproducible.

Cross-cutting normalizations done here:
  * ``exclusion_key`` composes lastname:firstname:midname:busname:dob:
    excldate:npi:address from the *normalized* values. Validated
    against the full live file (83,464 rows, 2026-06-30 vintage): 31
    residual duplicate keys / 32 excess rows remain — 25 byte-identical
    source lines plus 6 differing only in city spelling or specialty —
    which the idempotent upsert collapses harmlessly. ADDRESS is in the
    key because without it 31 *distinct* multi-location business
    exclusions would collapse.
  * ``reinstatement_key`` appends reindate — reinstatement rows
    accumulate across monthly files and the same person can be excluded
    and reinstated more than once.
  * ``source_endpoint`` records provenance: ``exclusions`` for the full
    file, ``supplement:YYYY-MM`` / ``reinstatements:YYYY-MM`` for the
    monthly deltas (the month is resolved by the connector).

Anything present on the record that the target table does not declare is
recorded as an unmapped column so the pipeline can log schema drift
(OIG adding a column shows up here instead of vanishing silently).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .endpoints import EndpointSpec

_NON_IDENT = re.compile(r"[^0-9A-Za-z]+")
_MULTI_UNDERSCORE = re.compile(r"_+")
_YYYYMMDD = re.compile(r"^\d{8}$")

# The NPI-unknown sentinel OIG writes instead of an empty cell.
_NPI_UNKNOWN = "0000000000"
# The date-null sentinel.
_DATE_NULL = "00000000"

# Canonical columns holding LEIE dates (all published as yyyymmdd).
_DATE_COLUMNS = frozenset({"dob", "excldate", "reindate", "waiverdate"})


def snake(header: str) -> str:
    """Snake-case one raw CSV header.

    LEIE headers are single uppercase tokens (``LASTNAME`` →
    ``lastname``), so this is nearly a ``.lower()``; the non-alphanumeric
    collapse keeps the rule identical to the estate's other CSV
    connectors and future-proofs against OIG adding a prose header.
    """
    s = _NON_IDENT.sub("_", header.strip())
    return _MULTI_UNDERSCORE.sub("_", s).strip("_").lower()


def clean_npi(value: Optional[str]) -> str:
    """Normalize an LEIE NPI cell: the ``0000000000`` unknown-sentinel
    becomes ``''`` so it can never satisfy an NPI equality join."""
    v = (value or "").strip()
    return "" if v == _NPI_UNKNOWN else v


def iso_date(value: Optional[str]) -> str:
    """``yyyymmdd`` → ISO ``yyyy-mm-dd``; ``00000000``/empty → ``''``.

    A value that is not 8 digits is passed through stripped-but-verbatim
    rather than dropped: unexpected formats are schema drift we want
    visible in the data, not silently erased.
    """
    v = (value or "").strip()
    if not v or v == _DATE_NULL:
        return ""
    if _YYYYMMDD.match(v):
        return f"{v[0:4]}-{v[4:6]}-{v[6:8]}"
    return v


@dataclass
class NormalizeResult:
    """Canonical rows grouped by table, plus an unmapped-column audit."""

    rows: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    unmapped: Dict[str, int] = field(default_factory=dict)

    def add(self, table: str, row: Dict[str, Any]) -> None:
        self.rows.setdefault(table, []).append(row)

    def note_unmapped(self, keys: List[str]) -> None:
        for k in keys:
            self.unmapped[k] = self.unmapped.get(k, 0) + 1


def _canonical_row(rec: Dict[str, str], colset: set, res: NormalizeResult
                   ) -> Dict[str, Any]:
    """Snake + strip + apply the value rules; audit anything undeclared."""
    row: Dict[str, Any] = {}
    unknown: List[str] = []
    for raw_header, value in rec.items():
        col = snake(raw_header)
        if not col:
            continue  # defensive: dangling empty header cell
        if col not in colset:
            unknown.append(col)
            continue
        v = value.strip() if isinstance(value, str) else value
        if col == "npi":
            v = clean_npi(v)
        elif col in _DATE_COLUMNS:
            v = iso_date(v)
        row[col] = v
    if unknown:
        res.note_unmapped(unknown)
    return row


def _composed_key(row: Dict[str, Any], spec: EndpointSpec) -> str:
    """Join the spec's id fields from the *normalized* values, so the key
    is stable whether a row arrived via the full file or a supplement
    (both go through the same date/NPI cleanup first)."""
    return ":".join(str(row.get(snake(h), "") or "") for h in spec.id_fields)


def normalize(spec: EndpointSpec, raw_rows: List[Dict[str, str]],
              *, month_tag: Optional[str] = None) -> NormalizeResult:
    """Normalize a batch of raw CSV rows for one dataset into canonical rows.

    ``month_tag`` (``"YYYY-MM"``) is the supplement month the connector
    resolved; it lands in ``source_endpoint`` so provenance survives the
    merge into the shared cumulative table.
    """
    # Imported here (not at module top) to keep normalize importable in
    # isolation for doctest-style use; tables imports nothing from here.
    from .tables import TABLES
    res = NormalizeResult()
    tdef = TABLES[spec.target_table]
    colset = set(tdef.columns)
    source_endpoint = spec.key if not month_tag else f"{spec.key}:{month_tag}"
    for rec in raw_rows:
        if not isinstance(rec, dict):
            continue
        row = _canonical_row(rec, colset, res)
        key = _composed_key(row, spec)
        if not key.replace(":", ""):
            continue  # every key part empty — a blank/garbage line
        row[tdef.pk] = key
        row["source_endpoint"] = source_endpoint
        res.add(spec.target_table, row)
    return res
