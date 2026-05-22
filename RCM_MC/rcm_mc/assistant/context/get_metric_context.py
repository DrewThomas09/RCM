"""Resolve a metric id / label / alias to a MetricContext (read-only).

Case-insensitive; resolves by metric_id, label, or alias. Does not guess
beyond registered aliases — an unknown query returns a clean fallback.
"""
from __future__ import annotations

from typing import Dict

from .metric_registry import METRIC_REGISTRY
from .types import MetricContext, MetricLookupResult

_FALLBACK = (
    "No PEdesk Guide metric definition has been documented for that term yet."
)


def _norm(s: str) -> str:
    return " ".join((s or "").strip().lower().split())


def _build_index() -> Dict[str, str]:
    idx: Dict[str, str] = {}
    for mid, m in METRIC_REGISTRY.items():
        idx[_norm(mid)] = mid
        idx[_norm(m.label)] = mid
        for alias in m.aliases:
            idx.setdefault(_norm(alias), mid)
    return idx


_INDEX = _build_index()


def get_metric_context(metric_id_or_label: str) -> MetricLookupResult:
    query = metric_id_or_label or ""
    key = _norm(query)
    mid = _INDEX.get(key)
    if mid is None:
        return MetricLookupResult(False, query, None, None, _FALLBACK)
    return MetricLookupResult(True, query, mid, METRIC_REGISTRY[mid], None)


def get_metric(metric_id_or_label: str) -> MetricContext | None:
    """Convenience: the MetricContext or None."""
    return get_metric_context(metric_id_or_label).context
