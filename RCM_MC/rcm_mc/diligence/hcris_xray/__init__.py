"""HCRIS-Native Peer X-Ray.

Turns the 17,000+ Medicare cost-report filings into a
point-and-click peer-benchmark engine for PE hospital diligence.
Partners pick any hospital by CCN or name, get an instant
benchmark against its true peer cohort across 15 RCM / cost /
margin / payer-mix metrics — replacing the $80K/yr CapIQ
subscription for this specific use case.

Public API::

    from rcm_mc.diligence.hcris_xray import (
        HospitalMetrics, MetricBenchmark, MetricSpec, PeerMatch,
        XRayReport, compute_benchmarks, compute_metrics,
        find_hospital, find_peers, load_all_metrics,
        dataset_summary, search_hospitals, xray,
    )
"""
from __future__ import annotations

from .metrics import (
    HospitalMetrics, METRIC_CATALOG, MetricSpec,
    catalog_by_category, compute_metrics,
)
from .xray import (
    MetricBenchmark, PeerMatch, XRayReport,
    compute_benchmarks, dataset_summary, find_hospital,
    find_peers, get_target_history, load_all_metrics,
    search_hospitals, xray,
)

__all__ = [
    "HospitalMetrics",
    "METRIC_CATALOG",
    "MetricBenchmark",
    "MetricSpec",
    "PeerMatch",
    "XRayReport",
    "catalog_by_category",
    "compute_benchmarks",
    "compute_metrics",
    "dataset_summary",
    "find_hospital",
    "find_peers",
    "get_target_history",
    "load_all_metrics",
    "search_hospitals",
    "xray",
]
