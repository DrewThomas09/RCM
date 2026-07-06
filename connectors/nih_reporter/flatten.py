"""Defensive accessors for NIH RePORTER records.

RePORTER project records are deeply nested: ``organization`` is a dict of
~18 fields, ``principal_investigators``/``program_officers`` are lists of
person dicts, ``agency_ic_admin`` / ``organization_type`` /
``full_study_section`` / ``geo_lat_lon`` are nested objects, and almost
any of them can be ``null`` (a subproject often omits ``organization``
details; ``covid_response`` is usually ``null``). Two rules everywhere
downstream:

  1. Never assume a field exists — :func:`dig` returns a default instead
     of raising on any missing segment.
  2. Never assume cardinality — :func:`first`/:func:`as_list` collapse
     the scalar-or-list ambiguity; :func:`join_people` collapses person
     lists into one stable string column; :func:`unmapped_keys` records
     every top-level field no mapper placed so schema drift surfaces.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Sequence


def dig(obj: Any, path: str, default: Any = None) -> Any:
    """Walk a dotted path through dicts/lists, collapsing 1-element lists."""
    cur = obj
    for seg in path.split("."):
        if cur is None:
            return default
        if isinstance(cur, list):
            if seg.isdigit():
                idx = int(seg)
                if idx >= len(cur):
                    return default
                cur = cur[idx]
                continue
            if not cur:
                return default
            cur = cur[0]
        if isinstance(cur, dict):
            if seg not in cur:
                return default
            cur = cur[seg]
        elif seg.isdigit():
            return default
        else:
            return default
    return cur if cur is not None else default


def first(value: Any, default: Any = None) -> Any:
    """Return ``value`` if scalar, its first element if a non-empty list."""
    if isinstance(value, list):
        return value[0] if value else default
    return default if value is None else value


def as_list(value: Any) -> List[Any]:
    """Coerce scalar-or-list-or-None into a list (empty when None)."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def join_list(value: Any, sep: str = "|", default: str = "") -> str:
    """Join a list of scalars into a stable delimited string."""
    items = as_list(value)
    parts = [str(x) for x in items if x is not None and x != ""]
    return sep.join(parts) if parts else default


def join_people(value: Any, name_key: str = "full_name", sep: str = "; ",
                default: str = "") -> str:
    """Collapse a RePORTER person list into one delimited name column.

    RePORTER pads ``full_name`` with double spaces when the middle name is
    empty (``"Alejandro  Aballay"``), so each name is whitespace-normalised
    before joining — the column is for humans and LIKE matches, not exact
    round-trips.
    """
    names: List[str] = []
    for person in as_list(value):
        if not isinstance(person, dict):
            continue
        name = person.get(name_key)
        if name in (None, ""):
            name = " ".join(
                str(person.get(k, "")) for k in ("first_name", "last_name")
            )
        name = " ".join(str(name).split())
        if name:
            names.append(name)
    return sep.join(names) if names else default


def coalesce(record: Dict[str, Any], paths: Sequence[str], default: Any = None) -> Any:
    """First non-empty value across candidate dotted paths."""
    for p in paths:
        val = dig(record, p)
        if val not in (None, "", []):
            return val
    return default


def top_level_keys(obj: Any) -> List[str]:
    return sorted(obj.keys()) if isinstance(obj, dict) else []


def unmapped_keys(record: Dict[str, Any], mapped: Iterable[str]) -> List[str]:
    """First-level keys present on the record but not in ``mapped``."""
    mapped_set = {m.split(".", 1)[0] for m in mapped}
    return [k for k in top_level_keys(record) if k not in mapped_set]
