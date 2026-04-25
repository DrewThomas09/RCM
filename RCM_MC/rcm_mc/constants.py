"""Central registry for cross-cutting magic numbers.

Audit of the recent ML and UI sprint surfaced hardcoded constants
scattered across ~15 modules: sanity-range tuples on predictors,
RCM-metric typical ranges, peer-percentile thresholds, freshness
windows on the data catalog.

This module consolidates those values into one named-constant
registry with documentation. Every constant carries:

  • A docstring or inline comment naming the source / rationale.
  • A canonical name imported by callers (no more inline literals).

Modules that have their own deep domain logic (rcm_ebitda_bridge
research-band coefficients, payer_mix_cascade per-payer profiles)
keep their constants local — those are intrinsic to the model,
not cross-cutting. This module is for values that *do* recur
across multiple modules.

Public API::

    from rcm_mc.constants import (
        # RCM KPI sanity ranges
        DENIAL_RATE_RANGE,
        DAYS_IN_AR_RANGE,
        COLLECTION_RATE_RANGE,
        OPERATING_MARGIN_RANGE,
        # Peer comparison
        PEER_SIGNIFICANCE_BAND,
        # Distress thresholds
        DISTRESS_MARGIN_THRESHOLD,
        DAYS_CASH_DISTRESS,
        DAYS_CASH_HEALTHY,
        # Data catalog freshness bands
        FRESHNESS_FRESH_DAYS,
        FRESHNESS_STALE_DAYS,
        # Cache TTLs
        DEFAULT_PANEL_TTL_SECONDS,
    )
"""
from __future__ import annotations

from typing import Tuple


# ── RCM KPI sanity ranges ────────────────────────────────────
# Used by trained predictors (denial_rate, days_in_ar, etc.) to
# clip out-of-distribution predictions back to plausible bounds.
# Sourced from HFMA MAP Keys + the project's existing
# rcm_ebitda_bridge documentation. Format: (lo, hi).

DENIAL_RATE_RANGE: Tuple[float, float] = (0.0, 0.40)
"""Initial denial rate, decimal. National avg 5-15%; the worst
tail rarely exceeds 30%. Negative impossible."""

DAYS_IN_AR_RANGE: Tuple[float, float] = (15.0, 120.0)
"""Days in accounts receivable. National median ~45; <38 is best
in class; >65 is working-capital-trapped territory."""

COLLECTION_RATE_RANGE: Tuple[float, float] = (0.70, 1.00)
"""Net collection rate, decimal. Typical 92-99%; below 85% is
distressed asset territory; above 100% impossible (would be
over-collection or netting issue)."""

OPERATING_MARGIN_RANGE: Tuple[float, float] = (-0.50, 0.30)
"""Operating margin, decimal. <-5% distressed; >5% sustainable;
>10% best-in-class for community hospitals."""

CLEAN_CLAIM_RATE_RANGE: Tuple[float, float] = (0.50, 1.00)
"""Clean claim rate (first-pass acceptance). National 85-96%;
best-in-class >96%."""

CASE_MIX_INDEX_RANGE: Tuple[float, float] = (0.80, 4.00)
"""Case mix index. Typical 1.20-2.50; specialty hospitals can
exceed 3.0."""


# ── Peer comparison ─────────────────────────────────────────

PEER_SIGNIFICANCE_BAND: float = 0.10
"""Default ±10% band around peer p50 within which we call a
deal 'in line'. Outside this band counts as meaningfully
above/below market. Matches the contract_strength + peer_color
defaults across the platform."""

PEER_TARGET_PERCENTILE: int = 75
"""Default peer percentile target for value-creation plans.
p75 (top quartile) is the realistic aspiration partners can
defend; p90 belongs in the bull case."""


# ── Distress thresholds ─────────────────────────────────────

DISTRESS_MARGIN_THRESHOLD: float = -0.05
"""Operating margin below this is the canonical 'distressed'
line in HCRIS-based PE diligence. Used by forward_distress_
predictor, regime_detection, and the partner notes that flag
restructuring territory."""

DAYS_CASH_DISTRESS: float = 15.0
"""Below 15 days cash on hand → restructuring discussion
territory. Used by liquidity panels."""

DAYS_CASH_WARNING: float = 30.0
"""Below 30 days cash on hand → covenant-trip risk band.
Above 30 = monitoring; below 30 = action required."""

DAYS_CASH_HEALTHY: float = 100.0
"""≥100 days cash = healthy band. Hospital can absorb a
reasonable shock without covenant breach."""

DEBT_TO_REVENUE_HIGH: float = 1.0
"""Long-term debt / NPSR above this typically requires
above-average margin to service; drives covenant attention."""

INTEREST_COVERAGE_LOW: float = 1.5
"""EBIT / interest expense below this raises restructuring
discussion. <2.0 is the credit-attention zone."""


# ── Data catalog freshness bands ────────────────────────────

FRESHNESS_FRESH_DAYS: int = 30
"""≤N days since last refresh = 'fresh'. Used by the data
catalog quality score's freshness component."""

FRESHNESS_STALE_DAYS: int = 90
"""≥N days since last refresh = 'stale'. Catalog flags these
to the partner for refresh."""

FRESHNESS_FULL_DECAY_DAYS: int = 365
"""Beyond this, the freshness component fully decays to 0
in the catalog quality score."""


# ── Cache TTLs ───────────────────────────────────────────────

DEFAULT_PANEL_TTL_SECONDS: int = 300
"""5 minutes. Synthesized model panels (model_quality, feature
importance) cache for this long — long enough to amortize the
backtest cost, short enough that code changes propagate quickly."""

DATA_CATALOG_TTL_SECONDS: int = 60
"""1 minute. The data catalog scans live SQL on every render;
short TTL keeps the page snappy without staleness."""


# ── Operating leverage / drop-through ──────────────────────

DEFAULT_FIXED_COST_SHARE: float = 0.70
"""Hospital cost-structure assumption: 70% fixed / 30%
variable. Drives operating-leverage / EBITDA drop-through
math in payer_mix_cascade and improvement_potential."""

DEFAULT_TARGET_EBITDA_MARGIN: float = 0.10
"""Anchor EBITDA margin for cascade computations when no
hospital-specific value is available."""


# ── Health score bands ──────────────────────────────────────

HEALTH_SCORE_HIGH: float = 75.0
"""≥75 = 'good shape; focus on growth plays' (per dashboard
narrative)."""

HEALTH_SCORE_MID: float = 60.0
"""60-74 = 'mid-tier; one or two underperformers'."""


# ── Forecast horizons ────────────────────────────────────────

DEFAULT_FORECAST_PERIODS: int = 4
"""Default n_forward for the temporal forecaster + volume
trend forecaster — 4 periods = 1 year on quarterly data."""

DEFAULT_PERIOD_PER_YEAR: int = 4
"""Quarterly granularity. Use 12 for monthly, 1 for annual."""


# ── ML / training defaults ──────────────────────────────────

DEFAULT_RIDGE_ALPHA: float = 1.0
"""Ridge regression penalty. 1.0 is a safe default for
standardized features; tune via outer search if needed."""

DEFAULT_K_FOLDS: int = 5
"""K-fold cross-validation default. Smaller for tiny training
sets; the trained-predictor scaffold validates ≥2*K rows."""

DEFAULT_NOMINAL_COVERAGE: float = 0.90
"""Conformal-style 90% prediction interval. Match this to the
CI calibration tolerance used in the model quality dashboard."""


# ── UI breakpoints (mirror responsive.py BREAKPOINTS) ──────

BREAKPOINT_TABLET_PX: int = 640
"""Below this, layout switches to single-column for tablets +
narrow phones."""

BREAKPOINT_LAPTOP_PX: int = 1024
"""Below this, KPI strips stack 2-up and dense tables get
horizontal-scroll wrappers."""

BREAKPOINT_DESKTOP_PX: int = 1280
"""Standard laptop width — primary design target."""
