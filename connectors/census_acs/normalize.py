"""Map raw ACS array-of-arrays payloads → canonical joined profile rows.

The Census API returns ``[[header, ...], [value, ...], ...]`` — the core
of this module is :func:`rows_from_table`, which zips each data row
against the header row and renames headers through the **declared**
mapping (``DETAIL_VARIABLES`` / ``SUBJECT_VARIABLES`` / ``GEO_RENAMES``
in :mod:`connectors.census_acs.endpoints`) — never a guessed
snake_case. Headers outside the mapping are kept verbatim and recorded
as unmapped so schema drift surfaces instead of silently vanishing.

Cross-cutting normalizations done here:
  * the detail (B-table) and subject (S-table) payloads are joined on
    the geography columns — the detail payload drives; a geography
    missing from the subject payload keeps ``None`` for the S-columns,
  * ACS *jam values* — the negative sentinels the Bureau publishes when
    an estimate is suppressed or undefined (e.g. ``-666666666`` = median
    not computable for a tiny geography) — become ``None`` so numeric
    casts downstream never see them,
  * the natural upsert key composes geography + vintage
    (``{fips5}:{year}`` / ``{state_fips}:{year}`` / ``{cbsa_code}:{year}``)
    so re-ingesting a vintage is idempotent and vintages coexist,
  * counties also carry ``fips5`` (state+county concatenated), the join
    key the rest of the estate uses for county-level data.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .endpoints import (DETAIL_VARIABLES, GEO_RENAMES, SUBJECT_VARIABLES,
                        EndpointSpec)

# ACS "jam values": any annotation sentinel at or below this marks a
# suppressed / not-computable estimate (-222222222, -333333333,
# -666666666, -888888888, -999999999, ...). Real estimates are never
# this negative, so a simple threshold is robust across tables.
_JAM_THRESHOLD = -111111111.0

_RENAMES: Dict[str, str] = {**DETAIL_VARIABLES, **SUBJECT_VARIABLES, **GEO_RENAMES}


@dataclass
class NormalizeResult:
    """Canonical rows grouped by table, plus an unmapped-header audit."""

    rows: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    unmapped: Dict[str, int] = field(default_factory=dict)

    def add(self, table: str, row: Dict[str, Any]) -> None:
        self.rows.setdefault(table, []).append(row)

    def note_unmapped(self, keys: List[str]) -> None:
        for k in keys:
            self.unmapped[k] = self.unmapped.get(k, 0) + 1


def clean_value(value: Any) -> Optional[str]:
    """Collapse ACS jam values (and empties) to ``None``; else str."""
    if value is None:
        return None
    text = str(value).strip()
    if text == "":
        return None
    try:
        if float(text) <= _JAM_THRESHOLD:
            return None
    except ValueError:
        pass  # non-numeric (NAME, fips) — keep verbatim
    return text


def rows_from_table(table: List[List[Any]],
                    renames: Optional[Dict[str, str]] = None,
                    ) -> Tuple[List[Dict[str, Any]], List[str]]:
    """The array-of-arrays → dict core: header row → renamed columns.

    Returns ``(rows, unmapped_headers)``. Headers absent from the
    declared mapping keep their original name and are reported so the
    caller can audit drift. Short/long data rows are zipped defensively
    (missing cells → ``None``; extra cells dropped).
    """
    renames = _RENAMES if renames is None else renames
    if not table or not isinstance(table[0], list):
        return [], []
    headers = [str(h) for h in table[0]]
    mapped = [renames.get(h, h) for h in headers]
    unmapped = [h for h in headers if h not in renames]
    out: List[Dict[str, Any]] = []
    for raw in table[1:]:
        if not isinstance(raw, list):
            continue
        row = {col: clean_value(raw[i]) if i < len(raw) else None
               for i, col in enumerate(mapped)}
        out.append(row)
    return out, unmapped


def _geo_tuple(row: Dict[str, Any], geo_cols: Tuple[str, ...]) -> Tuple[str, ...]:
    """The join/identity tuple for a row, in the spec's canonical order."""
    return tuple(str(row.get(GEO_RENAMES.get(g, g)) or "") for g in geo_cols)


def normalize(spec: EndpointSpec, fetched: Any) -> NormalizeResult:
    """Join one profile's detail + subject payloads into canonical rows.

    ``fetched`` is a :class:`connectors.census_acs.connector.FetchResult`
    (duck-typed: needs ``.detail``, ``.subject``, ``.year``). The detail
    payload drives — every ACS geography carries B01001, so a row absent
    there is not a real geography; subject-only rows are dropped.
    """
    res = NormalizeResult()
    detail_rows, unmapped_d = rows_from_table(fetched.detail)
    subject_rows, unmapped_s = rows_from_table(fetched.subject)
    for _ in detail_rows:
        res.note_unmapped(unmapped_d)
    for _ in subject_rows:
        res.note_unmapped(unmapped_s)

    subject_by_geo = {_geo_tuple(r, spec.geo_cols): r for r in subject_rows}
    year = str(int(fetched.year))

    for det in detail_rows:
        geo = _geo_tuple(det, spec.geo_cols)
        if not all(geo):
            continue  # a row missing its geography can't be keyed
        sub = subject_by_geo.get(geo, {})
        row: Dict[str, Any] = {
            "name": det.get("name"),
            "year": year,
            "source_endpoint": spec.key,
        }
        for col in DETAIL_VARIABLES.values():
            row[col] = det.get(col)
        for col in SUBJECT_VARIABLES.values():
            row[col] = sub.get(col)
        _key_row(spec, row, geo, year)
        res.add(spec.target_table, row)
    return res


def _key_row(spec: EndpointSpec, row: Dict[str, Any],
             geo: Tuple[str, ...], year: str) -> None:
    """Attach geography columns + the composed natural PK for one profile."""
    if spec.key == "county_profile":
        state_fips, county_fips = geo
        fips5 = f"{state_fips}{county_fips}"
        row.update(state_fips=state_fips, county_fips=county_fips,
                   fips5=fips5, county_key=f"{fips5}:{year}")
    elif spec.key == "state_profile":
        (state_fips,) = geo
        row.update(state_fips=state_fips, state_key=f"{state_fips}:{year}")
    elif spec.key == "cbsa_profile":
        (cbsa_code,) = geo
        row.update(cbsa_code=cbsa_code, cbsa_key=f"{cbsa_code}:{year}")
    else:  # pragma: no cover — specs are module constants
        raise KeyError(f"no key composer for endpoint {spec.key!r}")
