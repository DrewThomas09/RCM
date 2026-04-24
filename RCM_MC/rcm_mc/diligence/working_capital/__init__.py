"""Working-capital diligence (Gap 7).

    normalized_peg.py         — seasonality-adjusted NWC target
    dnfb_reserve.py           — DNFB estimator
    pull_forward_detector.py  — 60-day pre-close pattern
"""
from __future__ import annotations

from .dnfb_reserve import DNFBResult, estimate_dnfb
from .normalized_peg import PegResult, compute_normalized_peg
from .pull_forward_detector import (
    PullForwardFinding, detect_pre_close_pull_forward,
)

__all__ = [
    "DNFBResult",
    "PegResult",
    "PullForwardFinding",
    "compute_normalized_peg",
    "detect_pre_close_pull_forward",
    "estimate_dnfb",
]
