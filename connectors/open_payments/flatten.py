"""Defensive accessors for Open Payments records.

Datastore rows are flat dicts of strings, but the DKAN metastore
catalog entries are nested (``contactPoint.hasEmail``,
``distribution[0].downloadURL``, list-valued ``theme``/``keyword``).
Two rules everywhere downstream:

  1. Never assume a field exists — :func:`dig` returns a default instead
     of raising on any missing segment.
  2. Never assume cardinality — :func:`first`/:func:`as_list` collapse
     the scalar-or-list ambiguity; :func:`unmapped_keys` records every
     top-level field no mapper placed so schema drift surfaces.
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
