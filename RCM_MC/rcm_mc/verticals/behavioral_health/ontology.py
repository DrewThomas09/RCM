"""Behavioral health metric registry (Prompt 80)."""
from __future__ import annotations
from typing import Any, Dict

BH_METRIC_REGISTRY: Dict[str, Dict[str, Any]] = {
    "bed_days": {"display_name": "Bed Days", "category": "volume", "unit": "count",
                 "benchmark_p50": 15000, "ebitda_sensitivity_rank": 1},
    "avg_length_of_stay": {"display_name": "Avg Length of Stay", "category": "operations", "unit": "days",
                           "benchmark_p50": 14, "ebitda_sensitivity_rank": 2},
    "readmission_30day": {"display_name": "30-Day Readmission Rate", "category": "quality", "unit": "pct",
                          "benchmark_p50": 12, "ebitda_sensitivity_rank": 3},
    "prior_auth_days": {"display_name": "Prior Auth Days to Approval", "category": "operations", "unit": "days",
                        "benchmark_p50": 3, "ebitda_sensitivity_rank": 4},
    "level_of_care_php_pct": {"display_name": "PHP % of Revenue", "category": "mix", "unit": "pct",
                              "benchmark_p50": 30, "ebitda_sensitivity_rank": 5},
    "level_of_care_iop_pct": {"display_name": "IOP % of Revenue", "category": "mix", "unit": "pct",
                              "benchmark_p50": 20, "ebitda_sensitivity_rank": 6},
    "clinical_outcome_score": {"display_name": "Clinical Outcome Score", "category": "quality", "unit": "ratio",
                               "benchmark_p50": 0.75, "ebitda_sensitivity_rank": 7},
    "payer_denial_rate": {"display_name": "Payer Denial Rate", "category": "operations", "unit": "pct",
                          "benchmark_p50": 15, "ebitda_sensitivity_rank": 8},
    "self_pay_pct": {"display_name": "Self-Pay %", "category": "revenue", "unit": "pct",
                     "benchmark_p50": 10, "ebitda_sensitivity_rank": 9},
    "occupancy_rate": {"display_name": "Occupancy Rate", "category": "volume", "unit": "pct",
                       "benchmark_p50": 75, "ebitda_sensitivity_rank": 10},
}
