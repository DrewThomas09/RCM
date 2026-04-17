"""
Diligence Requests That Move the Number.
Maps top modeled drivers to specific data pulls for validation.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


# Driver pattern → (short_label, diligence_request)
# Driver format: idr_Commercial, fwr_Medicare, dar_clean_Commercial, upr_Medicaid
_DILIGENCE_MAP: Dict[str, Tuple[str, str]] = {
    "fwr": (
        "Final write-off rate",
        "Denial log with final disposition; 835 denial reason codes; appeal stage outcomes (L1/L2/L3); recent payer policy changes.",
    ),
    "idr": (
        "Initial denial rate",
        "Denial log with initial vs final disposition; 835 denial reason codes; prior-auth capture rate; pre-auth denial breakdown.",
    ),
    "upr": (
        "Underpayment rate",
        "Contract rate schedules; sample 835/EOB remits; top 50 DRG/CPT paid amounts vs expected; underpayment recovery logs.",
    ),
    "dar_clean": (
        "Clean-claim A/R days",
        "A/R aging by payer + status buckets; credit balance report; first-pass clean rate; submission lag by payer.",
    ),
}


def _driver_to_request(driver: str) -> str:
    """Map sensitivity driver column name to diligence request text."""
    driver = str(driver).strip().lower()
    for pattern, (_, request) in _DILIGENCE_MAP.items():
        if driver.startswith(pattern + "_") or driver == pattern:
            return request
    return "Parameter-level denial, underpayment, or A/R data to validate assumptions."


def build_diligence_requests(
    sensitivity_df: Optional[pd.DataFrame],
    top_n: int = 3,
) -> List[Dict[str, Any]]:
    """
    For the top N drivers by |correlation|, return driver_label and diligence_request.
    Returns list of {rank, driver_label, corr, diligence_request}.
    """
    if sensitivity_df is None or len(sensitivity_df) == 0:
        return []

    # Sort by |corr| descending
    df = sensitivity_df.copy()
    df["_abs_corr"] = df["corr"].astype(float).abs()
    df = df.sort_values("_abs_corr", ascending=False).head(top_n)

    rows = []
    for i, (_, r) in enumerate(df.iterrows(), 1):
        driver = str(r.get("driver", ""))
        label = str(r.get("driver_label", driver))
        corr = float(r.get("corr", 0))
        request = _driver_to_request(driver)
        rows.append({
            "rank": i,
            "driver_label": label,
            "corr": corr,
            "diligence_request": request,
        })
    return rows
