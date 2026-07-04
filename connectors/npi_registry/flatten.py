"""Defensive accessors for NPPES's nested, sometimes-sparse records.

An NPI record nests ``basic`` (a dict), plus ``addresses``,
``taxonomies``, ``identifiers`` and ``other_names`` (lists of dicts).
Individual (NPI-1) and organization (NPI-2) records carry different
``basic`` keys. Two rules everywhere downstream:

  1. Never assume a field exists — :func:`dig` returns a default instead
     of raising on any missing/typed-wrong segment.
  2. Never assume cardinality — :func:`first` collapses the
     scalar-or-list ambiguity; :func:`first_where` picks the primary
     element (primary taxonomy, LOCATION address) with a graceful
     fallback to the first element.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence


def dig(obj: Any, path: str, default: Any = None) -> Any:
    """Walk a dotted path through dicts/lists, collapsing 1-element lists.

    ``"a.b.0.c"`` indexes list element 0. A bare segment against a list
    transparently takes the first element. Returns ``default`` the moment
    any segment is missing or mistyped.
    """
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


def first_where(items: Any, pred: Callable[[Dict[str, Any]], bool],
                default: Any = None) -> Any:
    """First dict in ``items`` satisfying ``pred``; else the first item.

    NPPES marks a "primary" taxonomy and a ``LOCATION`` address; this
    picks that element and gracefully falls back to element 0 when no
    element matches (never raising on an empty/absent list).
    """
    lst = as_list(items)
    for it in lst:
        if isinstance(it, dict) and pred(it):
            return it
    for it in lst:
        if isinstance(it, dict):
            return it
    return default


def coalesce(record: Dict[str, Any], paths: Sequence[str], default: Any = None) -> Any:
    """First non-empty value across candidate dotted paths."""
    for p in paths:
        val = dig(record, p)
        if val not in (None, "", []):
            return val
    return default


def as_bool_text(value: Any) -> Optional[str]:
    """Normalize a truthy flag to ``"1"``/``"0"`` text (NULL when absent)."""
    if value is None:
        return None
    if isinstance(value, bool):
        return "1" if value else "0"
    s = str(value).strip().lower()
    if s in ("true", "1", "yes", "y", "primary"):
        return "1"
    if s in ("false", "0", "no", "n", ""):
        return "0"
    return s


def top_level_keys(obj: Any) -> List[str]:
    """The record's own first-level keys (for unmapped-field auditing)."""
    return sorted(obj.keys()) if isinstance(obj, dict) else []


def unmapped_keys(record: Dict[str, Any], mapped: Iterable[str]) -> List[str]:
    """First-level keys present on the record but not in ``mapped``."""
    mapped_set = {m.split(".", 1)[0] for m in mapped}
    return [k for k in top_level_keys(record) if k not in mapped_set]
