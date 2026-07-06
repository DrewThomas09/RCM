"""Defensive accessors for healthdata.gov payloads.

SODA row payloads are flat dicts, but two quirks push work here:

  1. Socrata JSON rows OMIT null fields entirely, so no field can be
     assumed present — :func:`dig`/:func:`coalesce` return defaults
     instead of raising on any missing segment.
  2. The catalog metadata API uses camelCase keys (``dataUpdatedAt``)
     and nests the D.CAT "Common Core" block under ``customFields``;
     :func:`to_snake` is the one documented casing normalizer and
     :func:`dig` walks the nesting.

:func:`unmapped_keys` records every top-level field no mapper placed so
schema drift surfaces in ingest logs instead of silently dropping data.
"""
from __future__ import annotations

import re
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


def coalesce(record: Dict[str, Any], paths: Sequence[str], default: Any = None) -> Any:
    """First non-empty value across candidate dotted paths."""
    for p in paths:
        val = dig(record, p)
        if val not in (None, "", []):
            return val
    return default


_SNAKE_RE_1 = re.compile(r"(.)([A-Z][a-z]+)")
_SNAKE_RE_2 = re.compile(r"([a-z0-9])([A-Z])")

# SQL keywords that appear (or could plausibly appear) as Socrata field
# names. The estate's query engine interpolates whitelisted column names
# bare into SELECT/WHERE/ORDER BY, so a canonical column may never be a
# reserved word (data.cdc.gov's live ``group`` field is the estate's
# precedent for this actually happening).
_SQL_RESERVED = {
    "group", "order", "index", "select", "where", "from", "to", "table",
    "join", "union", "limit", "offset", "between", "case", "when", "then",
    "else", "end", "primary", "references", "check", "default", "values",
    "set", "using", "transaction", "and", "or", "not", "in", "is", "on",
}


def to_snake(name: str) -> str:
    """Lowercase snake_case a field name (``dataUpdatedAt`` → ``data_updated_at``).

    The one documented casing normalizer for this connector: SODA row
    columns are already snake_case, but the catalog metadata API is
    camelCase — every canonical column name in :mod:`tables` derives from
    the live field name through this function (via :func:`to_column`).
    """
    s = _SNAKE_RE_1.sub(r"\1_\2", str(name))
    s = _SNAKE_RE_2.sub(r"\1_\2", s)
    s = s.replace("-", "_").replace(" ", "_").lower()
    return re.sub(r"__+", "_", s)


def to_column(name: str) -> str:
    """Live field name → canonical column name: snake_case + SQL-safe.

    A live field that collides with an SQL keyword gets a ``_field``
    suffix (``group`` → ``group_field``) because the uniform query
    engine interpolates whitelisted column identifiers bare. The rule is
    mechanical so a reader can always reconstruct the live name.
    """
    s = to_snake(name)
    return f"{s}_field" if s in _SQL_RESERVED else s


def top_level_keys(obj: Any) -> List[str]:
    return sorted(obj.keys()) if isinstance(obj, dict) else []


def unmapped_keys(record: Dict[str, Any], mapped: Iterable[str]) -> List[str]:
    """First-level keys present on the record but not in ``mapped``.

    Socrata's ``:@computed_region_*`` join columns are platform noise,
    not source schema, so they are excluded from the drift audit.
    """
    mapped_set = {m.split(".", 1)[0] for m in mapped}
    return [k for k in top_level_keys(record)
            if k not in mapped_set and not k.startswith(":")]
