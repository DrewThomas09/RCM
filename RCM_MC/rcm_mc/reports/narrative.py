"""
Step 84: Natural language result summary.

Generates a 3-paragraph plain-English summary of simulation results.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

import numpy as np
import pandas as pd


def _fmt_money(val: float) -> str:
    if abs(val) >= 1_000_000:
        return f"${val / 1_000_000:,.1f}M"
    if abs(val) >= 1_000:
        return f"${val / 1_000:,.0f}K"
    return f"${val:,.0f}"


def generate_narrative(
    summary_df: pd.DataFrame,
    hospital_name: str = "the target hospital",
    ev_multiple: float = 8.0,
    sensitivity_df: Optional[pd.DataFrame] = None,
) -> str:
    """Generate a 3-paragraph plain-English summary."""
    paragraphs = []

    # Paragraph 1: Headline opportunity
    ebitda = summary_df.loc["ebitda_drag"] if "ebitda_drag" in summary_df.index else None
    if ebitda is not None:
        mean_drag = float(ebitda["mean"])
        p10 = float(ebitda["p10"])
        p90 = float(ebitda["p90"])
        ev_impact = mean_drag * ev_multiple
        paragraphs.append(
            f"Our Monte Carlo analysis of {hospital_name} identifies a {_fmt_money(mean_drag)} annual "
            f"EBITDA recovery opportunity, translating to {_fmt_money(ev_impact)} in enterprise value "
            f"at a {ev_multiple:.0f}x multiple. The range spans {_fmt_money(p10)} (conservative, P10) "
            f"to {_fmt_money(p90)} (stress, P90), reflecting the uncertainty in denial rates, "
            f"write-off behavior, and A/R management efficiency."
        )

    # Paragraph 2: Biggest drivers (use sensitivity_df if available)
    driver_lines = []
    for metric in ["drag_denial_writeoff", "drag_underpay_leakage", "drag_denial_rework_cost", "economic_drag"]:
        if metric in summary_df.index:
            val = float(summary_df.loc[metric, "mean"])
            label = metric.replace("drag_", "").replace("_", " ").title()
            driver_lines.append(f"{label} ({_fmt_money(val)})")

    if driver_lines:
        drivers_text = ", ".join(driver_lines[:3])
        paragraphs.append(
            f"The primary value drivers are {drivers_text}. "
            f"These represent the gap between current operating performance and industry benchmarks."
        )

    # Name top sensitivity drivers if available
    top_sens_names = []
    if sensitivity_df is not None and len(sensitivity_df) > 0:
        label_col = "driver_label" if "driver_label" in sensitivity_df.columns else "driver"
        for _, row in sensitivity_df.head(3).iterrows():
            top_sens_names.append(str(row.get(label_col, "")))

    # Paragraph 3: Risks (data-aware)
    sens_clause = ""
    if top_sens_names:
        sens_clause = (
            f" Sensitivity analysis identifies {', '.join(top_sens_names[:2])} as the most "
            f"influential inputs; securing accurate data for these variables is the top diligence priority."
        )
    paragraphs.append(
        "Key risks include potential payer policy changes that could increase denial rates, "
        "staffing constraints in the denial management team, and uncertainty around historical "
        "data quality." + sens_clause +
        " We recommend validating denial write-off data through claims-level audit "
        "before incorporating full upside in the purchase price."
    )

    return "\n\n".join(paragraphs)
