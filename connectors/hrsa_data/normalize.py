"""Map raw HRSA CSV rows → canonical rows.

HRSA CSV headers are prose ("MUA/P ID", "% of Population Below 100%
Poverty", "U.S. - Mexico Border 100 Kilometer Indicator"), so the core
of this module is :func:`snake`, the one documented header→column rule —
tables.py's column lists are snapshots of the live headers passed
through it, which is what keeps "the schema is derived from a live
sample" honest and reproducible. Every published column is kept
(TEXT — SQLite is dynamically typed and the uniform query layer casts
explicitly); values are whitespace-stripped because the live files pad
some numerics (e.g. ``" 6"`` in ``PC MCTA Score``).

Cross-cutting normalizations done here:
  * ``hpsa_key`` composes ``{hpsa_id}:{discipline}:{geo_id}`` — the
    three HPSA discipline files share one table, and the spec's
    discipline token makes cross-file collisions impossible; the
    geography id distinguishes the component rows of one designation.
  * ``mua_key`` composes the MUA/P id + service-area name + three
    component-geography fields — MUA/P ids are re-used across
    designations (verified live: a Designated and a Withdrawn
    designation can share id *and* geography, differing only by
    service-area name).
  * ``site_key`` is the BPHC-assigned site number (unique in the live
    file).

  The composed keys were validated against the *full* live files on
  2026-07-06: the only key collisions remaining are byte-identical
  duplicate source lines, which the idempotent upsert collapses.

Anything present on the record that the target table does not declare is
recorded as an unmapped column so the pipeline can log schema drift
(HRSA adding a column shows up here instead of vanishing silently).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List

from .endpoints import EndpointSpec

_NON_IDENT = re.compile(r"[^0-9A-Za-z]+")
_MULTI_UNDERSCORE = re.compile(r"_+")


def snake(header: str) -> str:
    """Snake-case one raw CSV header, losslessly enough to stay readable.

    Rules (in order): ``%`` becomes the token ``pct`` (it carries
    meaning — "% of Population Below 100% Poverty" must not collapse to
    "of_population_below_100_poverty"), every other non-alphanumeric run
    becomes a single ``_``, then lowercase and trim. Examples::

        MUA/P ID                                  -> mua_p_id
        % of Population Below 100% Poverty        -> pct_of_population_below_100_pct_poverty
        U.S. - Mexico Border 100 Kilometer Indicator
                                                  -> u_s_mexico_border_100_kilometer_indicator
    """
    s = header.strip().replace("%", " pct ")
    s = _NON_IDENT.sub("_", s)
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


def _base_row(rec: Dict[str, str], spec: EndpointSpec, colset: set,
              res: NormalizeResult) -> Dict[str, Any]:
    """Snake + strip every published column; audit anything undeclared."""
    row: Dict[str, Any] = {}
    unknown: List[str] = []
    for raw_header, value in rec.items():
        col = snake(raw_header)
        if not col:
            continue  # dangling trailing comma in the source header row
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


# ── per-dataset-kind mappers ──────────────────────────────────────────
def _hpsa(rec: Dict[str, str], res: NormalizeResult, spec: EndpointSpec,
          colset: set) -> None:
    hpsa_id = _key_part(rec, "HPSA ID")
    if not hpsa_id:
        return
    geo_id = _key_part(rec, "HPSA Geography Identification Number")
    row = _base_row(rec, spec, colset, res)
    row["hpsa_key"] = f"{hpsa_id}:{spec.discipline}:{geo_id}"
    row["source_endpoint"] = spec.key
    res.add("hrsa_hpsa", row)


def _mua(rec: Dict[str, str], res: NormalizeResult, spec: EndpointSpec,
         colset: set) -> None:
    muap_id = _key_part(rec, "MUA/P ID")
    if not muap_id:
        return
    parts = [_key_part(rec, h) for h in spec.id_fields]
    row = _base_row(rec, spec, colset, res)
    row["mua_key"] = ":".join(parts)
    row["source_endpoint"] = spec.key
    res.add("hrsa_mua", row)


def _health_center_sites(rec: Dict[str, str], res: NormalizeResult,
                         spec: EndpointSpec, colset: set) -> None:
    bphc = _key_part(rec, "BPHC Assigned Number")
    if not bphc:
        return
    row = _base_row(rec, spec, colset, res)
    row["site_key"] = bphc
    row["source_endpoint"] = spec.key
    res.add("hrsa_health_center_sites", row)


_MAPPERS = {
    "hpsa": _hpsa,
    "mua": _mua,
    "health_center_sites": _health_center_sites,
}


def normalize(spec: EndpointSpec, raw_rows: List[Dict[str, str]]
              ) -> NormalizeResult:
    """Normalize a batch of raw CSV rows for one file into canonical rows."""
    # Imported here (not at module top) to keep normalize importable in
    # isolation for doctest-style use; tables imports nothing from here.
    from .tables import TABLES
    res = NormalizeResult()
    mapper = _MAPPERS.get(spec.dataset_kind)
    if mapper is None:
        raise KeyError(
            f"no normalizer for dataset_kind {spec.dataset_kind!r} "
            f"(endpoint {spec.key!r})")
    colset = set(TABLES[spec.target_table].columns)
    for rec in raw_rows:
        if isinstance(rec, dict):
            mapper(rec, res, spec, colset)
    return res
