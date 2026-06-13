"""Defensive accessors for openFDA's deeply nested, sparse records.

openFDA documents fields that are frequently absent, sometimes a scalar,
sometimes a list. Two rules everywhere downstream:

  1. Never assume a field exists — :func:`dig` returns a default instead
     of raising on any missing/typed-wrong segment.
  2. Never assume cardinality — :func:`first` collapses the
     scalar-or-list ambiguity; :func:`flatten` records every leaf as a
     dotted path so the normalizer can map known fields and the
     :func:`unmapped_keys` audit can log the rest to DECISIONS.md.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence


def dig(obj: Any, path: str, default: Any = None) -> Any:
    """Walk a dotted path through dicts/lists, collapsing 1-element lists.

    ``"a.b.0.c"`` indexes list element 0. A bare segment against a list
    transparently takes the first element, so ``"openfda.product_ndc"``
    works whether ``openfda`` is a dict or a 1-element list of dicts.
    Returns ``default`` the moment any segment is missing or mistyped.
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
            # Non-numeric segment against a list: descend into element 0.
            if not cur:
                return default
            cur = cur[0]
        if isinstance(cur, dict):
            if seg not in cur:
                return default
            cur = cur[seg]
        elif seg.isdigit():
            # already handled list case above; a scalar can't be indexed
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


def flatten(obj: Any, prefix: str = "", out: Optional[Dict[str, Any]] = None
            ) -> Dict[str, Any]:
    """Flatten nested dicts/lists into dotted-path leaves.

    Lists of scalars become a single ``|``-joined leaf; lists of objects
    expand with numeric indices (capped so a 1000-element MAUDE array
    can't explode the row). Used both for raw-row fingerprinting and for
    the unmapped-field audit.
    """
    out = {} if out is None else out
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = f"{prefix}.{k}" if prefix else str(k)
            flatten(v, key, out)
    elif isinstance(obj, list):
        if obj and all(not isinstance(x, (dict, list)) for x in obj):
            out[prefix] = join_list(obj)
        else:
            for i, v in enumerate(obj[:50]):
                flatten(v, f"{prefix}.{i}", out)
    else:
        out[prefix] = obj
    return out


def top_level_keys(obj: Any) -> List[str]:
    """The record's own first-level keys (for unmapped-field auditing)."""
    return sorted(obj.keys()) if isinstance(obj, dict) else []


def unmapped_keys(record: Dict[str, Any], mapped: Iterable[str]) -> List[str]:
    """First-level keys present on the record but not in ``mapped``.

    ``mapped`` is the set of top-level field names the normalizer knows
    how to place. The remainder is logged to DECISIONS.md so schema
    drift surfaces instead of silently dropping.
    """
    mapped_set = {m.split(".", 1)[0] for m in mapped}
    return [k for k in top_level_keys(record) if k not in mapped_set]


def coalesce(record: Dict[str, Any], paths: Sequence[str], default: Any = None) -> Any:
    """First non-empty value across candidate dotted paths."""
    for p in paths:
        val = dig(record, p)
        if val not in (None, "", []):
            return val
    return default
