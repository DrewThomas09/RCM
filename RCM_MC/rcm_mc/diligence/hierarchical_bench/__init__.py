"""Hierarchical (partial-pooling) benchmarking.

Empirical-Bayes shrinkage so a low-volume facility stops looking like
an outlier on noise alone — the statistically correct way to benchmark
small-n units, pairing with the risk-adjusted O/E from
``diligence.risk_adjustment``.

See ``README.md`` and ``docs/TUVA_MYELIN_INTEGRATION.md``.
"""
from __future__ import annotations

from .shrinkage import (
    PartialPoolResult,
    ShrunkenUnit,
    partial_pool,
    partial_pool_nested,
)

__all__ = [
    "PartialPoolResult",
    "ShrunkenUnit",
    "partial_pool",
    "partial_pool_nested",
]
