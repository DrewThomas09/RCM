"""MSO (Management Service Organization) metric registry (Prompt 79)."""
from __future__ import annotations
from typing import Any, Dict

MSO_METRIC_REGISTRY: Dict[str, Dict[str, Any]] = {
    "wrvus_per_provider": {"display_name": "wRVUs per Provider", "category": "productivity", "unit": "count",
                           "benchmark_p50": 5000, "ebitda_sensitivity_rank": 1},
    "panel_size_per_provider": {"display_name": "Panel Size per Provider", "category": "productivity", "unit": "count",
                                "benchmark_p50": 2000, "ebitda_sensitivity_rank": 2},
    "provider_count": {"display_name": "Provider Count", "category": "scale", "unit": "count",
                       "benchmark_p50": 50, "ebitda_sensitivity_rank": 3},
    "revenue_per_visit": {"display_name": "Revenue per Visit", "category": "revenue", "unit": "dollars",
                          "benchmark_p50": 180, "ebitda_sensitivity_rank": 4},
    "capitation_pmpm": {"display_name": "Capitation PMPM", "category": "revenue", "unit": "dollars",
                        "benchmark_p50": 45, "ebitda_sensitivity_rank": 5},
    "value_based_revenue_pct": {"display_name": "Value-Based Revenue %", "category": "revenue", "unit": "pct",
                                "benchmark_p50": 25, "ebitda_sensitivity_rank": 6},
    "quality_bonus_revenue": {"display_name": "Quality Bonus Revenue", "category": "revenue", "unit": "dollars",
                              "benchmark_p50": 500000, "ebitda_sensitivity_rank": 7},
    "mlr": {"display_name": "Medical Loss Ratio", "category": "risk", "unit": "pct",
            "benchmark_p50": 85, "ebitda_sensitivity_rank": 8},
    "provider_turnover_rate": {"display_name": "Provider Turnover Rate", "category": "operations", "unit": "pct",
                               "benchmark_p50": 12, "ebitda_sensitivity_rank": 9},
    "msa_fee_pct": {"display_name": "MSA Fee %", "category": "economics", "unit": "pct",
                    "benchmark_p50": 15, "ebitda_sensitivity_rank": 10},
}
