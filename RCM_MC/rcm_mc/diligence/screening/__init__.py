"""Diligence screening artifacts — pre-packet scans.

``bankruptcy_survivor`` is the go-to-market wedge: a 12-pattern
screening scan a PE associate can run in the first 30 minutes of
looking at a teaser. If RED/CRITICAL, the deal doesn't advance.
"""
from __future__ import annotations

from .bankruptcy_survivor import (
    BankruptcySurvivorScan,
    BankruptcySurvivorVerdict,
    PatternCheck,
    ScanInput,
    run_bankruptcy_survivor_scan,
)

__all__ = [
    "BankruptcySurvivorScan",
    "BankruptcySurvivorVerdict",
    "PatternCheck",
    "ScanInput",
    "run_bankruptcy_survivor_scan",
]
