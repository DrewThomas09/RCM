"""Completeness assessment — the analyst's first-look data-quality layer.

Answers three questions before any downstream math runs:

1. *What do we know?* — coverage of the RCM-metric registry.
2. *What's missing?* — ranked by EBITDA sensitivity so the biggest
   holes float to the top of the diligence list.
3. *Can we trust it?* — quality flags for stale data, out-of-range
   values, benchmark outliers, conflicting sources, broken payer mix.

This module deliberately keeps units in **percentage points** (so a
benchmark P50 of ``5.2`` means 5.2%, not 0.052). Callers must pass
observed values in the same scale; the bridge / simulator downstream
convert to fractions where they need them.

The registry is the source of truth. Everywhere else in the codebase
that needs "does this metric exist?" / "what's its display name?" /
"how big is its EBITDA impact?" should import from here.

Benchmark percentiles blend published data from:
- HFMA MAP Keys 2023 publication
- Kodiak Solutions Revenue Cycle Analytics (2,300+ hospitals)
- Crowe Revenue Cycle Analytics (RCA) benchmarks

Where a canonical figure isn't published, we use the tighter of the
two sources so the outlier flag is conservative (prefers to NOT flag
rather than spuriously page a partner).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from .packet import (
    CompletenessAssessment,
    ConflictField,
    HospitalProfile,
    MissingField,
    ObservedMetric,
    QualityFlag,
    RiskSeverity,
    SectionStatus,
    StaleField,
)


# ── Metric categories ─────────────────────────────────────────────────

METRIC_CATEGORIES: Tuple[str, ...] = (
    "denials",
    "collections",
    "ar",
    "claims",
    "coding",
    "financial",
)


# ── Registry ─────────────────────────────────────────────────────────
#
# Shape of each entry:
#
#   {
#       "display_name": human-readable label
#       "category":    one of METRIC_CATEGORIES
#       "unit":        "pct" | "days" | "dollars" | "ratio" | "index"
#       "hfma_map_key": True/False
#       "required_for_bridge": True/False  (input to EBITDA bridge)
#       "ebitda_sensitivity_rank": 1 = highest EBITDA impact
#       "benchmark_p25/p50/p75/p90": percentile anchors
#       "valid_range": (lo, hi)  inclusive
#       "warn_threshold": value at which a single-metric warning fires
#       "stale_after_days": how old an observed_date can be
#       "breakdown_of": optional parent metric — used for MISSING_BREAKDOWN
#   }

RCM_METRIC_REGISTRY: Dict[str, Dict[str, Any]] = {
    # ───── Denials (HFMA MAP Keys 9-15) ──────────────────────────────
    "denial_rate": {
        "display_name": "Initial Denial Rate",
        "category": "denials",
        "unit": "pct",
        "hfma_map_key": True,
        "required_for_bridge": True,
        "ebitda_sensitivity_rank": 1,
        "benchmark_p25": 3.0,
        "benchmark_p50": 5.2,
        "benchmark_p75": 9.8,
        "benchmark_p90": 14.5,
        "valid_range": (0.0, 100.0),
        "warn_threshold": 15.0,
        "stale_after_days": 90,
    },
    "final_denial_rate": {
        "display_name": "Final Denial Write-off %",
        "category": "denials",
        "unit": "pct",
        "hfma_map_key": True,
        "required_for_bridge": True,
        "ebitda_sensitivity_rank": 3,
        "benchmark_p25": 0.5,
        "benchmark_p50": 1.3,
        "benchmark_p75": 2.5,
        "benchmark_p90": 4.0,
        "valid_range": (0.0, 100.0),
        "warn_threshold": 4.0,
        "stale_after_days": 90,
    },
    "appeals_overturn_rate": {
        "display_name": "Denial Overturn Rate",
        "category": "denials",
        "unit": "pct",
        "hfma_map_key": True,
        "required_for_bridge": False,
        "ebitda_sensitivity_rank": 10,
        "benchmark_p25": 30.0,
        "benchmark_p50": 45.0,
        "benchmark_p75": 60.0,
        "benchmark_p90": 72.0,
        "valid_range": (0.0, 100.0),
        "warn_threshold": 30.0,   # low overturn = weak workflow
        "stale_after_days": 180,
    },
    "avoidable_denial_pct": {
        "display_name": "Avoidable Denials Rate",
        "category": "denials",
        "unit": "pct",
        "hfma_map_key": True,
        "required_for_bridge": False,
        "ebitda_sensitivity_rank": 6,
        "benchmark_p25": 40.0,
        "benchmark_p50": 55.0,
        "benchmark_p75": 68.0,
        "benchmark_p90": 78.0,
        "valid_range": (0.0, 100.0),
        "warn_threshold": 65.0,
        "stale_after_days": 180,
    },

    # ───── Denial categorical breakdowns ─────────────────────────────
    "denial_rate_eligibility": {
        "display_name": "Denials — Eligibility",
        "category": "denials",
        "unit": "pct",
        "hfma_map_key": False,
        "required_for_bridge": False,
        "ebitda_sensitivity_rank": 18,
        "benchmark_p25": 0.4,
        "benchmark_p50": 0.9,
        "benchmark_p75": 1.8,
        "benchmark_p90": 3.0,
        "valid_range": (0.0, 100.0),
        "warn_threshold": 2.5,
        "stale_after_days": 180,
        "breakdown_of": "denial_rate",
    },
    "denial_rate_authorization": {
        "display_name": "Denials — Authorization",
        "category": "denials",
        "unit": "pct",
        "hfma_map_key": False,
        "required_for_bridge": False,
        "ebitda_sensitivity_rank": 16,
        "benchmark_p25": 0.5,
        "benchmark_p50": 1.2,
        "benchmark_p75": 2.3,
        "benchmark_p90": 3.8,
        "valid_range": (0.0, 100.0),
        "warn_threshold": 3.0,
        "stale_after_days": 180,
        "breakdown_of": "denial_rate",
    },
    "denial_rate_coding": {
        "display_name": "Denials — Coding",
        "category": "denials",
        "unit": "pct",
        "hfma_map_key": False,
        "required_for_bridge": False,
        "ebitda_sensitivity_rank": 15,
        "benchmark_p25": 0.3,
        "benchmark_p50": 0.8,
        "benchmark_p75": 1.5,
        "benchmark_p90": 2.5,
        "valid_range": (0.0, 100.0),
        "warn_threshold": 2.0,
        "stale_after_days": 180,
        "breakdown_of": "denial_rate",
    },
    "denial_rate_medical_necessity": {
        "display_name": "Denials — Medical Necessity",
        "category": "denials",
        "unit": "pct",
        "hfma_map_key": False,
        "required_for_bridge": False,
        "ebitda_sensitivity_rank": 14,
        "benchmark_p25": 0.4,
        "benchmark_p50": 1.0,
        "benchmark_p75": 2.0,
        "benchmark_p90": 3.3,
        "valid_range": (0.0, 100.0),
        "warn_threshold": 2.5,
        "stale_after_days": 180,
        "breakdown_of": "denial_rate",
    },
    "denial_rate_timely_filing": {
        "display_name": "Denials — Timely Filing",
        "category": "denials",
        "unit": "pct",
        "hfma_map_key": False,
        "required_for_bridge": False,
        "ebitda_sensitivity_rank": 19,
        "benchmark_p25": 0.1,
        "benchmark_p50": 0.3,
        "benchmark_p75": 0.7,
        "benchmark_p90": 1.5,
        "valid_range": (0.0, 100.0),
        "warn_threshold": 1.0,
        "stale_after_days": 180,
        "breakdown_of": "denial_rate",
    },

    # ───── Denial by payer ───────────────────────────────────────────
    "denial_rate_medicare_ffs": {
        "display_name": "Denial Rate — Medicare FFS",
        "category": "denials",
        "unit": "pct",
        "hfma_map_key": False,
        "required_for_bridge": False,
        "ebitda_sensitivity_rank": 17,
        "benchmark_p25": 2.5,
        "benchmark_p50": 4.2,
        "benchmark_p75": 6.8,
        "benchmark_p90": 10.0,
        "valid_range": (0.0, 100.0),
        "warn_threshold": 10.0,
        "stale_after_days": 180,
        "breakdown_of": "denial_rate",
    },
    "denial_rate_medicare_advantage": {
        "display_name": "Denial Rate — Medicare Advantage",
        "category": "denials",
        "unit": "pct",
        "hfma_map_key": False,
        "required_for_bridge": False,
        "ebitda_sensitivity_rank": 11,
        "benchmark_p25": 5.5,
        "benchmark_p50": 9.0,
        "benchmark_p75": 13.5,
        "benchmark_p90": 18.5,
        "valid_range": (0.0, 100.0),
        "warn_threshold": 15.0,
        "stale_after_days": 180,
        "breakdown_of": "denial_rate",
    },
    "denial_rate_commercial": {
        "display_name": "Denial Rate — Commercial",
        "category": "denials",
        "unit": "pct",
        "hfma_map_key": False,
        "required_for_bridge": False,
        "ebitda_sensitivity_rank": 12,
        "benchmark_p25": 4.0,
        "benchmark_p50": 7.5,
        "benchmark_p75": 11.5,
        "benchmark_p90": 15.5,
        "valid_range": (0.0, 100.0),
        "warn_threshold": 13.0,
        "stale_after_days": 180,
        "breakdown_of": "denial_rate",
    },
    "denial_rate_medicaid": {
        "display_name": "Denial Rate — Medicaid",
        "category": "denials",
        "unit": "pct",
        "hfma_map_key": False,
        "required_for_bridge": False,
        "ebitda_sensitivity_rank": 20,
        "benchmark_p25": 4.0,
        "benchmark_p50": 7.0,
        "benchmark_p75": 11.0,
        "benchmark_p90": 15.0,
        "valid_range": (0.0, 100.0),
        "warn_threshold": 12.0,
        "stale_after_days": 180,
        "breakdown_of": "denial_rate",
    },

    # ───── A/R metrics (HFMA MAP 1-2) ───────────────────────────────
    "days_in_ar": {
        "display_name": "Net Days in A/R",
        "category": "ar",
        "unit": "days",
        "hfma_map_key": True,
        "required_for_bridge": True,
        "ebitda_sensitivity_rank": 2,
        "benchmark_p25": 35.0,
        "benchmark_p50": 45.0,
        "benchmark_p75": 55.0,
        "benchmark_p90": 65.0,
        "valid_range": (0.0, 365.0),
        "warn_threshold": 60.0,
        "stale_after_days": 30,
    },
    "ar_over_90_pct": {
        "display_name": "Aged A/R > 90 Days %",
        "category": "ar",
        "unit": "pct",
        "hfma_map_key": True,
        "required_for_bridge": False,
        "ebitda_sensitivity_rank": 7,
        "benchmark_p25": 12.0,
        "benchmark_p50": 18.0,
        "benchmark_p75": 25.0,
        "benchmark_p90": 32.0,
        "valid_range": (0.0, 100.0),
        "warn_threshold": 30.0,
        "stale_after_days": 30,
    },
    "dnfb_days": {
        "display_name": "Days in Discharged Not Final Billed (DNFB)",
        "category": "ar",
        "unit": "days",
        "hfma_map_key": True,
        "required_for_bridge": False,
        "ebitda_sensitivity_rank": 9,
        "benchmark_p25": 4.0,
        "benchmark_p50": 6.5,
        "benchmark_p75": 10.0,
        "benchmark_p90": 14.0,
        "valid_range": (0.0, 60.0),
        "warn_threshold": 10.0,
        "stale_after_days": 30,
    },
    "charge_lag_days": {
        "display_name": "Charge Lag (Days)",
        "category": "ar",
        "unit": "days",
        "hfma_map_key": True,
        "required_for_bridge": False,
        "ebitda_sensitivity_rank": 21,
        "benchmark_p25": 2.0,
        "benchmark_p50": 3.5,
        "benchmark_p75": 5.5,
        "benchmark_p90": 8.0,
        "valid_range": (0.0, 30.0),
        "warn_threshold": 7.0,
        "stale_after_days": 30,
    },

    # ───── Collections (HFMA MAP 4-5, 27-29) ─────────────────────────
    "net_collection_rate": {
        "display_name": "Net Collection Rate (Cash as % of NPSR)",
        "category": "collections",
        "unit": "pct",
        "hfma_map_key": True,
        "required_for_bridge": True,
        "ebitda_sensitivity_rank": 4,
        "benchmark_p25": 94.0,
        "benchmark_p50": 96.5,
        "benchmark_p75": 98.0,
        "benchmark_p90": 99.0,
        "valid_range": (0.0, 100.0),
        "warn_threshold": 93.0,   # lower-is-worse: fire if < warn
        "stale_after_days": 60,
    },
    "cost_to_collect": {
        "display_name": "Cost to Collect (% of NPSR)",
        "category": "collections",
        "unit": "pct",
        "hfma_map_key": True,
        "required_for_bridge": True,
        "ebitda_sensitivity_rank": 5,
        "benchmark_p25": 2.2,
        "benchmark_p50": 2.8,
        "benchmark_p75": 3.5,
        "benchmark_p90": 4.5,
        "valid_range": (0.0, 10.0),
        "warn_threshold": 4.0,
        "stale_after_days": 180,
    },
    "bad_debt_rate": {
        "display_name": "Bad Debt %",
        "category": "collections",
        "unit": "pct",
        "hfma_map_key": True,
        "required_for_bridge": False,
        "ebitda_sensitivity_rank": 8,
        "benchmark_p25": 1.5,
        "benchmark_p50": 3.0,
        "benchmark_p75": 5.0,
        "benchmark_p90": 7.5,
        "valid_range": (0.0, 25.0),
        "warn_threshold": 6.0,
        "stale_after_days": 90,
    },
    "patient_payment_yield": {
        "display_name": "Patient Payment Yield",
        "category": "collections",
        "unit": "pct",
        "hfma_map_key": True,
        "required_for_bridge": False,
        "ebitda_sensitivity_rank": 22,
        "benchmark_p25": 45.0,
        "benchmark_p50": 60.0,
        "benchmark_p75": 72.0,
        "benchmark_p90": 82.0,
        "valid_range": (0.0, 100.0),
        "warn_threshold": 55.0,
        "stale_after_days": 90,
    },
    "autopost_rate": {
        "display_name": "Auto-Posting Rate",
        "category": "collections",
        "unit": "pct",
        "hfma_map_key": True,
        "required_for_bridge": False,
        "ebitda_sensitivity_rank": 23,
        "benchmark_p25": 70.0,
        "benchmark_p50": 85.0,
        "benchmark_p75": 92.0,
        "benchmark_p90": 97.0,
        "valid_range": (0.0, 100.0),
        "warn_threshold": 75.0,
        "stale_after_days": 180,
    },

    # ───── Claims (HFMA MAP 12-13) ───────────────────────────────────
    "clean_claim_rate": {
        "display_name": "Clean Claim Rate",
        "category": "claims",
        "unit": "pct",
        "hfma_map_key": True,
        "required_for_bridge": True,
        "ebitda_sensitivity_rank": 13,
        "benchmark_p25": 88.0,
        "benchmark_p50": 92.0,
        "benchmark_p75": 95.0,
        "benchmark_p90": 97.0,
        "valid_range": (0.0, 100.0),
        "warn_threshold": 88.0,    # lower-is-worse
        "stale_after_days": 60,
    },
    "first_pass_resolution_rate": {
        "display_name": "First Pass Resolution Rate",
        "category": "claims",
        "unit": "pct",
        "hfma_map_key": True,
        "required_for_bridge": True,
        "ebitda_sensitivity_rank": 25,
        "benchmark_p25": 75.0,
        "benchmark_p50": 85.0,
        "benchmark_p75": 92.0,
        "benchmark_p90": 96.0,
        "valid_range": (0.0, 100.0),
        "warn_threshold": 80.0,
        "stale_after_days": 60,
    },
    "claim_rejection_rate": {
        "display_name": "Claim Rejection Rate (Pre-Payer)",
        "category": "claims",
        "unit": "pct",
        "hfma_map_key": True,
        "required_for_bridge": False,
        "ebitda_sensitivity_rank": 24,
        "benchmark_p25": 1.5,
        "benchmark_p50": 3.0,
        "benchmark_p75": 5.0,
        "benchmark_p90": 7.5,
        "valid_range": (0.0, 30.0),
        "warn_threshold": 5.0,
        "stale_after_days": 60,
    },
    "insurance_verification_rate": {
        "display_name": "Insurance Verification Rate",
        "category": "claims",
        "unit": "pct",
        "hfma_map_key": True,
        "required_for_bridge": False,
        "ebitda_sensitivity_rank": 26,
        "benchmark_p25": 85.0,
        "benchmark_p50": 93.0,
        "benchmark_p75": 97.0,
        "benchmark_p90": 99.0,
        "valid_range": (0.0, 100.0),
        "warn_threshold": 90.0,
        "stale_after_days": 90,
    },
    "late_charge_pct": {
        "display_name": "Late Charges %",
        "category": "claims",
        "unit": "pct",
        "hfma_map_key": True,
        "required_for_bridge": False,
        "ebitda_sensitivity_rank": 27,
        "benchmark_p25": 0.5,
        "benchmark_p50": 1.2,
        "benchmark_p75": 2.5,
        "benchmark_p90": 4.0,
        "valid_range": (0.0, 15.0),
        "warn_threshold": 3.0,
        "stale_after_days": 60,
    },

    # ───── Coding (HFMA MAP 22, + CMI) ──────────────────────────────
    "coding_accuracy_rate": {
        "display_name": "Coding Accuracy Rate",
        "category": "coding",
        "unit": "pct",
        "hfma_map_key": True,
        "required_for_bridge": False,
        "ebitda_sensitivity_rank": 28,
        "benchmark_p25": 92.0,
        "benchmark_p50": 95.5,
        "benchmark_p75": 97.5,
        "benchmark_p90": 98.8,
        "valid_range": (0.0, 100.0),
        "warn_threshold": 94.0,
        "stale_after_days": 180,
    },
    "case_mix_index": {
        "display_name": "Case Mix Index (CMI)",
        "category": "coding",
        "unit": "index",
        "hfma_map_key": False,
        "required_for_bridge": False,
        "ebitda_sensitivity_rank": 29,
        "benchmark_p25": 1.40,
        "benchmark_p50": 1.65,
        "benchmark_p75": 1.95,
        "benchmark_p90": 2.30,
        "valid_range": (0.5, 5.0),
        "warn_threshold": 1.3,
        "stale_after_days": 180,
    },

    # ───── Financial (PE-specific) ──────────────────────────────────
    "gross_revenue": {
        "display_name": "Gross Patient Revenue",
        "category": "financial",
        "unit": "dollars",
        "hfma_map_key": False,
        "required_for_bridge": True,
        "ebitda_sensitivity_rank": 30,
        "benchmark_p25": None,
        "benchmark_p50": None,
        "benchmark_p75": None,
        "benchmark_p90": None,
        "valid_range": (0.0, 1e12),
        "warn_threshold": None,
        "stale_after_days": 180,
    },
    "net_revenue": {
        "display_name": "Net Patient Service Revenue (NPSR)",
        "category": "financial",
        "unit": "dollars",
        "hfma_map_key": False,
        "required_for_bridge": True,
        "ebitda_sensitivity_rank": 31,
        "benchmark_p25": None,
        "benchmark_p50": None,
        "benchmark_p75": None,
        "benchmark_p90": None,
        "valid_range": (0.0, 1e12),
        "warn_threshold": None,
        "stale_after_days": 180,
    },
    "total_operating_expenses": {
        "display_name": "Total Operating Expenses",
        "category": "financial",
        "unit": "dollars",
        "hfma_map_key": False,
        "required_for_bridge": True,
        "ebitda_sensitivity_rank": 32,
        "benchmark_p25": None,
        "benchmark_p50": None,
        "benchmark_p75": None,
        "benchmark_p90": None,
        "valid_range": (0.0, 1e12),
        "warn_threshold": None,
        "stale_after_days": 180,
    },
    "current_ebitda": {
        "display_name": "Current EBITDA",
        "category": "financial",
        "unit": "dollars",
        "hfma_map_key": False,
        "required_for_bridge": True,
        "ebitda_sensitivity_rank": 33,
        "benchmark_p25": None,
        "benchmark_p50": None,
        "benchmark_p75": None,
        "benchmark_p90": None,
        "valid_range": (-1e12, 1e12),
        "warn_threshold": None,
        "stale_after_days": 180,
    },
    "ebitda_margin": {
        "display_name": "EBITDA Margin",
        "category": "financial",
        "unit": "pct",
        "hfma_map_key": False,
        "required_for_bridge": False,
        "ebitda_sensitivity_rank": 34,
        "benchmark_p25": 2.5,
        "benchmark_p50": 5.5,
        "benchmark_p75": 9.0,
        "benchmark_p90": 14.0,
        "valid_range": (-50.0, 50.0),
        "warn_threshold": 3.0,
        "stale_after_days": 180,
    },
    "payer_mix_commercial_pct": {
        "display_name": "Payer Mix — Commercial %",
        "category": "financial",
        "unit": "pct",
        "hfma_map_key": False,
        "required_for_bridge": False,
        "ebitda_sensitivity_rank": 35,
        "benchmark_p25": 25.0,
        "benchmark_p50": 35.0,
        "benchmark_p75": 45.0,
        "benchmark_p90": 55.0,
        "valid_range": (0.0, 100.0),
        "warn_threshold": None,
        "stale_after_days": 365,
    },
    "payer_mix_medicare_pct": {
        "display_name": "Payer Mix — Medicare %",
        "category": "financial",
        "unit": "pct",
        "hfma_map_key": False,
        "required_for_bridge": False,
        "ebitda_sensitivity_rank": 36,
        "benchmark_p25": 30.0,
        "benchmark_p50": 40.0,
        "benchmark_p75": 50.0,
        "benchmark_p90": 60.0,
        "valid_range": (0.0, 100.0),
        "warn_threshold": None,
        "stale_after_days": 365,
    },
    "payer_mix_medicaid_pct": {
        "display_name": "Payer Mix — Medicaid %",
        "category": "financial",
        "unit": "pct",
        "hfma_map_key": False,
        "required_for_bridge": False,
        "ebitda_sensitivity_rank": 37,
        "benchmark_p25": 8.0,
        "benchmark_p50": 15.0,
        "benchmark_p75": 22.0,
        "benchmark_p90": 35.0,
        "valid_range": (0.0, 100.0),
        "warn_threshold": None,
        "stale_after_days": 365,
    },
    "payer_mix_selfpay_pct": {
        "display_name": "Payer Mix — Self-Pay %",
        "category": "financial",
        "unit": "pct",
        "hfma_map_key": False,
        "required_for_bridge": False,
        "ebitda_sensitivity_rank": 38,
        "benchmark_p25": 2.0,
        "benchmark_p50": 5.0,
        "benchmark_p75": 9.0,
        "benchmark_p90": 15.0,
        "valid_range": (0.0, 100.0),
        "warn_threshold": None,
        "stale_after_days": 365,
    },
}


# ── Public helpers on the registry ────────────────────────────────────

def metric_keys() -> List[str]:
    """All registered metric keys, sorted by EBITDA sensitivity rank."""
    return sorted(
        RCM_METRIC_REGISTRY.keys(),
        key=lambda k: RCM_METRIC_REGISTRY[k].get("ebitda_sensitivity_rank", 9999),
    )


def hfma_map_key_metrics() -> List[str]:
    """Subset that are HFMA MAP Keys (for partners who want just that view)."""
    return [k for k, m in RCM_METRIC_REGISTRY.items() if m.get("hfma_map_key")]


def metric_display_name(key: str) -> str:
    return RCM_METRIC_REGISTRY.get(key, {}).get("display_name") or key


# ── Detection helpers ─────────────────────────────────────────────────

def _finite(v: Any) -> bool:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return False
    return math.isfinite(f)


def _severity_for(flag_type: str, is_critical_metric: bool) -> RiskSeverity:
    """Severity is how loud to ring the bell.

    ``OUT_OF_RANGE`` and ``PAYER_MIX_INCOMPLETE`` are always HIGH — these
    are structural errors. Other flags rise to MEDIUM when they hit a
    metric critical to the EBITDA bridge, LOW otherwise.
    """
    if flag_type in ("OUT_OF_RANGE", "PAYER_MIX_INCOMPLETE"):
        return RiskSeverity.HIGH
    if is_critical_metric:
        return RiskSeverity.MEDIUM
    return RiskSeverity.LOW


def _in_range(value: float, rng: Optional[Tuple[float, float]]) -> bool:
    if rng is None:
        return True
    lo, hi = float(rng[0]), float(rng[1])
    return lo <= value <= hi


def _is_benchmark_outlier(
    value: float, meta: Dict[str, Any],
) -> Tuple[bool, float]:
    """Heuristic z-like distance from P50 using the IQR as a scale proxy.

    We don't have a true population SD for these benchmarks — IQR ÷ 1.35
    approximates σ under normality, which is the convention when only
    quartiles are published. Returns (is_outlier, z_score).
    """
    p25 = meta.get("benchmark_p25")
    p50 = meta.get("benchmark_p50")
    p75 = meta.get("benchmark_p75")
    if not (_finite(p25) and _finite(p50) and _finite(p75)):
        return (False, 0.0)
    iqr = float(p75) - float(p25)
    if iqr <= 1e-9:
        return (False, 0.0)
    sigma_est = iqr / 1.35
    z = abs(value - float(p50)) / sigma_est
    return (z > 2.0, z)


# ── Assessment ────────────────────────────────────────────────────────

def assess_completeness(
    observed_metrics: Dict[str, ObservedMetric],
    profile: HospitalProfile,
    *,
    as_of: Optional[date] = None,
    historical_values: Optional[Dict[str, List[Tuple[date, float]]]] = None,
    conflict_sources: Optional[Dict[str, List[Tuple[str, float, str]]]] = None,
) -> CompletenessAssessment:
    """Build a full :class:`CompletenessAssessment` from observed inputs.

    Parameters
    ----------
    observed_metrics
        Whatever the partner has supplied. Keys should be registry keys;
        unknown keys are tolerated but contribute nothing to coverage.
    profile
        Used for the payer-mix sum check (and nothing else).
    as_of
        Report as-of date; defaults to today. Used to compute staleness.
    historical_values
        Optional dict of ``metric_key → [(date, value), ...]`` in
        chronological order. When present we run the
        ``SUSPICIOUS_CHANGE`` check (>20% MoM delta).
    conflict_sources
        Optional dict of ``metric_key → [(source, value, as_of), ...]``
        recording multiple sources for the same metric. When present we
        emit a ``ConflictField`` row describing which source the
        ``observed_metrics`` entry came from and why.
    """
    today = as_of or date.today()
    observed_metrics = observed_metrics or {}

    # --- Coverage ---------------------------------------------------------
    registry_keys = set(RCM_METRIC_REGISTRY.keys())
    observed_keys = {k for k in observed_metrics.keys() if k in registry_keys}
    missing_keys = registry_keys - observed_keys
    total = len(registry_keys)
    observed_count = len(observed_keys)
    coverage = (observed_count / total) if total > 0 else 0.0

    # --- Missing (structured) --------------------------------------------
    missing_fields: List[MissingField] = []
    for key in missing_keys:
        meta = RCM_METRIC_REGISTRY[key]
        missing_fields.append(MissingField(
            metric_key=key,
            display_name=str(meta.get("display_name") or key),
            category=str(meta.get("category") or ""),
            ebitda_sensitivity_rank=int(meta.get("ebitda_sensitivity_rank") or 999),
        ))
    missing_fields.sort(key=lambda m: m.ebitda_sensitivity_rank)
    missing_ranked = [m.metric_key for m in missing_fields]

    # --- Stale ------------------------------------------------------------
    stale_fields: List[StaleField] = []
    quality_flags: List[QualityFlag] = []

    for key, om in observed_metrics.items():
        meta = RCM_METRIC_REGISTRY.get(key)
        if meta is None or om is None:
            continue
        threshold = int(meta.get("stale_after_days") or 0)
        if threshold > 0 and om.as_of_date is not None:
            age = (today - om.as_of_date).days
            if age > threshold:
                stale_fields.append(StaleField(
                    metric_key=key,
                    observed_date=om.as_of_date,
                    days_stale=int(age),
                    stale_threshold=threshold,
                ))
                is_critical = bool(meta.get("required_for_bridge"))
                quality_flags.append(QualityFlag(
                    metric_key=key, flag_type="STALE",
                    severity=_severity_for("STALE", is_critical),
                    detail=f"observed {age} days ago; threshold {threshold}",
                    value=float(om.value) if _finite(om.value) else None,
                ))

    # --- Out-of-range / benchmark-outlier ---------------------------------
    for key, om in observed_metrics.items():
        meta = RCM_METRIC_REGISTRY.get(key)
        if meta is None or om is None or not _finite(om.value):
            continue
        v = float(om.value)
        is_critical = bool(meta.get("required_for_bridge"))
        rng = meta.get("valid_range")
        if not _in_range(v, rng):
            quality_flags.append(QualityFlag(
                metric_key=key, flag_type="OUT_OF_RANGE",
                severity=_severity_for("OUT_OF_RANGE", is_critical),
                detail=f"value {v!r} outside valid range {rng!r}",
                value=v,
            ))
            # Skip outlier detection on an out-of-range value — the range
            # violation is the actual story, the z-score is noise.
            continue
        is_out, z = _is_benchmark_outlier(v, meta)
        if is_out:
            quality_flags.append(QualityFlag(
                metric_key=key, flag_type="BENCHMARK_OUTLIER",
                severity=_severity_for("BENCHMARK_OUTLIER", is_critical),
                detail=f"value {v:.2f} is {z:.1f}σ from benchmark P50 "
                       f"({meta.get('benchmark_p50')})",
                value=v,
            ))

    # --- Missing payer breakdown -----------------------------------------
    # If the parent metric (denial_rate) is observed but NO children are,
    # the analyst can't tell a payer-mix story. Fire a single flag on
    # the parent rather than one per child so we don't drown the UI.
    breakdown_parents: Dict[str, List[str]] = {}
    for key, meta in RCM_METRIC_REGISTRY.items():
        parent = meta.get("breakdown_of")
        if parent:
            breakdown_parents.setdefault(parent, []).append(key)
    for parent, children in breakdown_parents.items():
        if parent not in observed_keys:
            continue
        has_any_child = any(c in observed_keys for c in children)
        if not has_any_child:
            quality_flags.append(QualityFlag(
                metric_key=parent, flag_type="MISSING_BREAKDOWN",
                severity=_severity_for("MISSING_BREAKDOWN",
                                       bool(RCM_METRIC_REGISTRY[parent].get("required_for_bridge"))),
                detail=f"{parent} observed but none of its breakdown children "
                       f"({', '.join(children[:3])}...) are present",
            ))

    # --- Suspicious MoM change -------------------------------------------
    if historical_values:
        for key, series in historical_values.items():
            if not series or len(series) < 2:
                continue
            # Series is chronological; compare last two points.
            sorted_series = sorted(series, key=lambda pair: pair[0])
            (_, prev_v) = sorted_series[-2]
            (latest_d, latest_v) = sorted_series[-1]
            if not _finite(prev_v) or abs(prev_v) < 1e-12:
                continue
            pct_change = abs((latest_v - prev_v) / prev_v)
            if pct_change > 0.20:
                meta = RCM_METRIC_REGISTRY.get(key, {})
                is_critical = bool(meta.get("required_for_bridge"))
                quality_flags.append(QualityFlag(
                    metric_key=key, flag_type="SUSPICIOUS_CHANGE",
                    severity=_severity_for("SUSPICIOUS_CHANGE", is_critical),
                    detail=f"{pct_change:.1%} MoM change ({prev_v:.2f} → {latest_v:.2f}) "
                           f"as of {latest_d.isoformat()}",
                    value=float(latest_v),
                ))

    # --- Conflicting sources ---------------------------------------------
    conflicting_fields: List[ConflictField] = []
    if conflict_sources:
        for key, candidates in conflict_sources.items():
            if not candidates or len(candidates) < 2:
                continue
            rows = []
            for src, val, asof in candidates:
                rows.append({"source": src, "value": float(val), "as_of": asof})
            chosen_src = ""
            chosen_val: Optional[float] = None
            reason = ""
            om = observed_metrics.get(key)
            if om is not None:
                chosen_src = om.source
                chosen_val = float(om.value)
                # Default preference order: HCRIS > user-input > fallback.
                reason = f"matched observed source {om.source!r}"
            conflicting_fields.append(ConflictField(
                metric_key=key,
                values=rows,
                chosen_source=chosen_src,
                chosen_value=chosen_val,
                reason=reason,
            ))

    # --- Payer mix consistency -------------------------------------------
    # Sum should land in the 95-105% band. Applies to either:
    #   (a) profile.payer_mix (fraction-scale), or
    #   (b) the four payer_mix_*_pct observed metrics.
    payer_mix_total: Optional[float] = None
    if profile and profile.payer_mix:
        # Fraction scale (sums to ~1.0) — convert to pct for consistency.
        s = sum(float(v or 0.0) for v in profile.payer_mix.values())
        # Heuristic: if the sum is in [0.5, 1.5] treat it as fraction.
        if 0.5 <= s <= 1.5:
            payer_mix_total = s * 100.0
        else:
            payer_mix_total = s
    else:
        pct_keys = [
            "payer_mix_commercial_pct",
            "payer_mix_medicare_pct",
            "payer_mix_medicaid_pct",
            "payer_mix_selfpay_pct",
        ]
        vals = [float(observed_metrics[k].value)
                for k in pct_keys if k in observed_metrics]
        if vals:
            payer_mix_total = sum(vals)
    if payer_mix_total is not None and not (95.0 <= payer_mix_total <= 105.0):
        quality_flags.append(QualityFlag(
            metric_key="payer_mix",
            flag_type="PAYER_MIX_INCOMPLETE",
            severity=RiskSeverity.HIGH,
            detail=f"payer mix sums to {payer_mix_total:.1f}% "
                   f"(expected 95-105%)",
            value=payer_mix_total,
        ))

    # --- Grade ------------------------------------------------------------
    has_critical_flag = any(q.severity == RiskSeverity.HIGH for q in quality_flags)
    if coverage >= 0.90 and not has_critical_flag:
        grade = "A"
    elif coverage >= 0.75:
        grade = "B"
    elif coverage >= 0.50:
        grade = "C"
    else:
        grade = "D"

    status = SectionStatus.OK
    reason = ""
    if coverage < 0.30:
        status = SectionStatus.INCOMPLETE
        reason = f"only {observed_count}/{total} metrics observed"

    return CompletenessAssessment(
        coverage_pct=coverage,
        total_metrics=total,
        observed_count=observed_count,
        missing_fields=missing_fields,
        stale_fields=stale_fields,
        conflicting_fields=conflicting_fields,
        quality_flags=quality_flags,
        missing_ranked_by_sensitivity=missing_ranked,
        missing_fields_ranked=missing_ranked,
        grade=grade,
        status=status,
        reason=reason,
    )
