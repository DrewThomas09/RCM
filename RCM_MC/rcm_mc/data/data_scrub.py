"""
Board-ready data scrubbing: institutional-grade integrity before charts/tables.
- Winsorize fat-tail outliers at operationally plausible caps
- Standardize naming: iteration, IDR, FWR, DAR
- Sanity-cap EBITDA drag to avoid double-count artifacts
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from ..infra.logger import logger


DEFAULT_CAPS = {
    "idr": 0.45,
    "fwr": 0.75,
    "dar_clean": 120,
    "upr": 0.30,
}

DEFAULT_WINSORIZE_PCT = 99.5
DEFAULT_REVENUE_FRACTION_CAP = 0.15


@dataclass
class ScrubReport:
    """Audit trail of what scrubbing changed."""
    clipped_counts: Dict[str, int] = field(default_factory=dict)
    winsorize_bounds: Dict[str, float] = field(default_factory=dict)
    revenue_cap_applied: bool = False
    revenue_cap_value: float = 0.0
    total_rows: int = 0
    caps_used: Dict[str, float] = field(default_factory=dict)
    winsorize_pct_used: float = DEFAULT_WINSORIZE_PCT

    def to_dict(self) -> Dict[str, Any]:
        return {
            "clipped_counts": self.clipped_counts,
            "winsorize_bounds": self.winsorize_bounds,
            "revenue_cap_applied": self.revenue_cap_applied,
            "revenue_cap_value": self.revenue_cap_value,
            "total_rows": self.total_rows,
            "caps_used": self.caps_used,
            "winsorize_pct_used": self.winsorize_pct_used,
        }


def _resolve_caps(cfg: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Extract scrub policy from config if present, else use defaults."""
    scrub_section = {}
    if cfg and isinstance(cfg, dict):
        scrub_section = cfg.get("scrub", {}) or {}
    return {
        "idr": float(scrub_section.get("idr_cap", DEFAULT_CAPS["idr"])),
        "fwr": float(scrub_section.get("fwr_cap", DEFAULT_CAPS["fwr"])),
        "dar_clean": float(scrub_section.get("dar_cap", DEFAULT_CAPS["dar_clean"])),
        "upr": float(scrub_section.get("upr_cap", DEFAULT_CAPS["upr"])),
        "winsorize_pct": float(scrub_section.get("winsorize_pct", DEFAULT_WINSORIZE_PCT)),
        "revenue_fraction_cap": float(scrub_section.get("revenue_fraction_cap", DEFAULT_REVENUE_FRACTION_CAP)),
    }


def _cap_driver_col(df: pd.DataFrame, col: str, cap: float) -> int:
    """In-place cap of a driver column. Returns count of clipped values."""
    if col not in df.columns:
        return 0
    vals = df[col].values
    above = int(np.sum(vals > cap))
    below = int(np.sum(vals < 0))
    df[col] = np.clip(vals, 0, cap)
    return above + below


def scrub_simulation_data(
    df: pd.DataFrame,
    cfg: Optional[Dict[str, Any]] = None,
    revenue: Optional[float] = None,
) -> Tuple[pd.DataFrame, ScrubReport]:
    """
    Institutional-grade scrub of simulation output.

    Returns (scrubbed_df, ScrubReport) tuple.

    When cfg contains a 'scrub' section, those values override the defaults:
        scrub:
          idr_cap: 0.45
          fwr_cap: 0.75
          dar_cap: 120
          upr_cap: 0.30
          winsorize_pct: 99.5
          revenue_fraction_cap: 0.15
    """
    out = df.copy()
    policy = _resolve_caps(cfg)
    report = ScrubReport(
        total_rows=len(out),
        caps_used={k: v for k, v in policy.items() if k not in ("winsorize_pct", "revenue_fraction_cap")},
        winsorize_pct_used=policy["winsorize_pct"],
    )

    if "sim" in out.columns:
        out = out.rename(columns={"sim": "iteration"})

    cap_map = {
        "actual_idr_": policy["idr"],
        "actual_fwr_": policy["fwr"],
        "actual_dar_clean_": policy["dar_clean"],
        "actual_upr_": policy["upr"],
    }
    for col in out.columns:
        for prefix, cap_val in cap_map.items():
            if col.startswith(prefix):
                n_clipped = _cap_driver_col(out, col, cap_val)
                if n_clipped > 0:
                    report.clipped_counts[col] = n_clipped
                break

    win_pct = policy["winsorize_pct"]
    if "ebitda_drag" in out.columns:
        x = out["ebitda_drag"].dropna()
        x = x[np.isfinite(x)]
        if x.size > 10:
            hi = float(np.percentile(x, win_pct))
            lo = float(np.percentile(x, 100 - win_pct))
            report.winsorize_bounds = {"lo": lo, "hi": hi}
            out["ebitda_drag"] = out["ebitda_drag"].clip(lower=lo, upper=hi)

    rev_frac = policy["revenue_fraction_cap"]
    if revenue and revenue > 0 and "ebitda_drag" in out.columns:
        max_drag = revenue * rev_frac
        n_over = int((out["ebitda_drag"] > max_drag).sum())
        if n_over > 0:
            report.revenue_cap_applied = True
            report.revenue_cap_value = max_drag
            report.clipped_counts["ebitda_drag_revenue_cap"] = n_over
        out["ebitda_drag"] = out["ebitda_drag"].clip(upper=max_drag)

    if report.clipped_counts:
        logger.info("Scrub clipped %d values across %d columns",
                     sum(report.clipped_counts.values()), len(report.clipped_counts))

    return out, report


def board_ready_driver_label(name: str) -> str:
    """PE-ready labels for driver variables."""
    parts = name.replace("actual_", "").split("_")
    if len(parts) >= 2:
        var = "_".join(parts[:-1]) if "dar" in parts[0] else parts[0]
        payer = parts[-1].title()
        mapping = {
            "idr": "Initial Denial Rate",
            "fwr": "Final Write-Off Rate",
            "dar_clean": "Days in A/R",
            "upr": "Underpayment Rate",
            "severity": "Underpayment Severity",
            "recovery": "Recovery Rate",
            "revenue_share": "Revenue Share",
        }
        label = mapping.get(var, var.replace("_", " ").title())
        return f"{label} ({payer})"
    return name.replace("_", " ").title()
