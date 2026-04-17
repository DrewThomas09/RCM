"""ASC (Ambulatory Surgery Center) metric registry (Prompt 78)."""
from __future__ import annotations
from typing import Any, Dict

ASC_METRIC_REGISTRY: Dict[str, Dict[str, Any]] = {
    "case_volume": {"display_name": "Case Volume", "category": "volume", "unit": "count",
                    "benchmark_p50": 8000, "ebitda_sensitivity_rank": 1},
    "cases_per_room_per_day": {"display_name": "Cases/Room/Day", "category": "volume", "unit": "ratio",
                               "benchmark_p50": 4.0, "ebitda_sensitivity_rank": 2},
    "room_turnover_minutes": {"display_name": "Room Turnover (min)", "category": "operations", "unit": "minutes",
                              "benchmark_p50": 25, "ebitda_sensitivity_rank": 3},
    "asc_facility_fee": {"display_name": "Avg Facility Fee", "category": "revenue", "unit": "dollars",
                         "benchmark_p50": 3500, "ebitda_sensitivity_rank": 4},
    "implant_revenue_pct": {"display_name": "Implant Revenue %", "category": "revenue", "unit": "pct",
                            "benchmark_p50": 15.0, "ebitda_sensitivity_rank": 5},
    "prior_auth_denial_rate": {"display_name": "Prior Auth Denial Rate", "category": "operations", "unit": "pct",
                               "benchmark_p50": 8.0, "ebitda_sensitivity_rank": 6},
    "same_day_cancellation_rate": {"display_name": "Same-Day Cancel Rate", "category": "operations", "unit": "pct",
                                   "benchmark_p50": 3.0, "ebitda_sensitivity_rank": 7},
    "out_of_network_pct": {"display_name": "Out-of-Network %", "category": "revenue", "unit": "pct",
                           "benchmark_p50": 10.0, "ebitda_sensitivity_rank": 8},
    "commercial_asc_premium": {"display_name": "Commercial ASC Rate Premium", "category": "reimbursement", "unit": "pct",
                               "benchmark_p50": 130.0, "ebitda_sensitivity_rank": 9},
    "anesthesia_revenue_pct": {"display_name": "Anesthesia Revenue %", "category": "revenue", "unit": "pct",
                               "benchmark_p50": 12.0, "ebitda_sensitivity_rank": 10},
    "surgeon_distribution_pct": {"display_name": "Surgeon Distribution %", "category": "revenue", "unit": "pct",
                                 "benchmark_p50": 35.0, "ebitda_sensitivity_rank": 11},
    "medicare_asc_rate_pct": {"display_name": "Medicare ASC Rate (% of HOPD)", "category": "reimbursement", "unit": "pct",
                              "benchmark_p50": 58.0, "ebitda_sensitivity_rank": 12},
}
