"""Resolve a data-source id / label / alias to a DataSourceContext.

Case-insensitive; resolves by source_id, label, or alias. Does not guess
beyond registered sources — an unknown query returns a clean fallback.
"""
from __future__ import annotations

from typing import Dict

from .data_source_registry import DATA_SOURCE_REGISTRY
from .types import DataSourceContext, DataSourceLookupResult

_FALLBACK = (
    "No PEdesk Guide data-source description has been documented for that "
    "term yet."
)


def _norm(s: str) -> str:
    return " ".join((s or "").strip().lower().split())


def _build_index() -> Dict[str, str]:
    idx: Dict[str, str] = {}
    for sid, src in DATA_SOURCE_REGISTRY.items():
        idx[_norm(sid)] = sid
        idx[_norm(src.label)] = sid
        for alias in src.aliases:
            idx.setdefault(_norm(alias), sid)
    return idx


_INDEX = _build_index()


def get_data_source_context(source_id_or_label: str) -> DataSourceLookupResult:
    query = source_id_or_label or ""
    key = _norm(query)
    sid = _INDEX.get(key)
    if sid is None:
        return DataSourceLookupResult(False, query, None, None, _FALLBACK)
    return DataSourceLookupResult(True, query, sid, DATA_SOURCE_REGISTRY[sid], None)


def get_data_source(source_id_or_label: str) -> DataSourceContext | None:
    """Convenience: the DataSourceContext or None."""
    return get_data_source_context(source_id_or_label).context
