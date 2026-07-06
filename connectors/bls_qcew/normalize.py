"""Map raw QCEW CSV rows → canonical rows.

QCEW is the rare federal source whose CSV headers are ALREADY machine
shaped (``area_fips``, ``month3_emplvl``, ``oty_avg_wkly_wage_pct_chg``)
— so unlike the HRSA connector there is no prose→snake mapping to
perform. :func:`snake` still exists as the one documented header→column
rule, but for QCEW it is (and is tested to be) the identity on every
published header; its job here is to normalize whitespace/case if BLS
ever drifts, and to keep the estate-wide "schema = live headers passed
through the documented rule" contract literal.

Cross-cutting normalizations done here:

  * ``qcew_key`` composes
    ``{slice_key}:{area_fips}:{own_code}:{industry_code}:{year}:{qtr}``.
    The natural observation key is the last five parts — verified
    unique within every live slice sampled 2026-07-06 (``size_code`` is
    always 0 in industry/area slices; ``agglvl_code`` is determined by
    the area/industry pair). The leading ``slice_key`` (the dataset's
    ``source_endpoint`` value) is deliberate: the two datasets share
    one physical table, and the SAME observation legitimately appears
    in both slices (fetching industry 622 and area 48453 for one
    quarter overlaps on Travis County's hospital rows — verified live).
    Without the slice prefix, the second fetch would overwrite the
    first row's ``source_endpoint`` and silently *move* the row out of
    the other dataset's ``source_filter`` slice. With it, each dataset
    stays independently complete and each re-fetch stays idempotent —
    the same reason the HRSA HPSA key carries the discipline token.
  * Values are whitespace-stripped; QCEW quotes its string cells and
    leaves numerics bare, and the csv module already unquotes, so
    stripping is belt-and-braces for uniformity.
  * Rows missing ``area_fips`` are skipped (there is nothing to key on).

Anything present on the record that the target table does not declare is
recorded as an unmapped column so the pipeline can log schema drift
(BLS adding a column shows up here instead of vanishing silently).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List

from .endpoints import EndpointSpec

_NON_IDENT = re.compile(r"[^0-9A-Za-z]+")
_MULTI_UNDERSCORE = re.compile(r"_+")

# Raw headers the composed key is built from (after the slice prefix).
_KEY_FIELDS = ("area_fips", "own_code", "industry_code", "year", "qtr")


def snake(header: str) -> str:
    """Snake-case one raw CSV header (identity for every live QCEW header).

    Same rule family as the estate's other CSV connectors: non-alnum
    runs collapse to ``_``, lowercase, trim. Kept even though QCEW
    headers are already snake_case so the schema-derivation contract
    ("column list = live headers through the documented rule") stays
    checkable — tests assert every table column is a fixed point.
    """
    s = _NON_IDENT.sub("_", header.strip())
    return _MULTI_UNDERSCORE.sub("_", s).strip("_").lower()


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


def _base_row(rec: Dict[str, str], colset: set, res: NormalizeResult
              ) -> Dict[str, Any]:
    """Snake + strip every published column; audit anything undeclared."""
    row: Dict[str, Any] = {}
    unknown: List[str] = []
    for raw_header, value in rec.items():
        col = snake(raw_header)
        if not col:
            continue
        if col in colset:
            row[col] = value.strip() if isinstance(value, str) else value
        else:
            unknown.append(col)
    if unknown:
        res.note_unmapped(unknown)
    return row


def _key_part(rec: Dict[str, str], raw_header: str) -> str:
    v = rec.get(raw_header, "")
    return v.strip() if isinstance(v, str) else str(v)


def normalize(spec: EndpointSpec, raw_rows: List[Dict[str, str]]
              ) -> NormalizeResult:
    """Normalize a batch of raw slice rows into canonical table rows."""
    # Imported here (not at module top) to keep normalize importable in
    # isolation for doctest-style use; tables imports nothing from here.
    from .tables import TABLES
    res = NormalizeResult()
    colset = set(TABLES[spec.target_table].columns)
    for rec in raw_rows:
        if not isinstance(rec, dict):
            continue
        if not _key_part(rec, "area_fips"):
            continue  # nothing to key on
        row = _base_row(rec, colset, res)
        parts = [_key_part(rec, h) for h in _KEY_FIELDS]
        row["qcew_key"] = ":".join([spec.key, *parts])
        row["source_endpoint"] = spec.key
        res.add(spec.target_table, row)
    return res
