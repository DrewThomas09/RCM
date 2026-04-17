"""
Step 81: Programmatic what-if scenario builder.

Provides a fluent API for adjusting config parameters
and running simulated scenarios.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Optional

import numpy as np

from ..infra.logger import logger


class ScenarioBuilder:
    """Build modified configs programmatically."""

    def __init__(self, base_cfg: Dict[str, Any]):
        self._cfg = deepcopy(base_cfg)
        self._adjustments: list = []

    def adjust_idr(self, payer: str, delta: float) -> "ScenarioBuilder":
        """Adjust initial denial rate by delta (e.g., -0.02 for 2pp improvement)."""
        if payer in self._cfg.get("payers", {}):
            d = self._cfg["payers"][payer].get("denials", {}).get("idr", {})
            if "mean" in d:
                old = float(d["mean"])
                d["mean"] = float(np.clip(old + delta, 0.01, 0.50))
                self._adjustments.append(f"IDR({payer}): {old:.3f} -> {d['mean']:.3f}")
        return self

    def adjust_fwr(self, payer: str, delta: float) -> "ScenarioBuilder":
        """Adjust final write-off rate by delta."""
        if payer in self._cfg.get("payers", {}):
            d = self._cfg["payers"][payer].get("denials", {}).get("fwr", {})
            if "mean" in d:
                old = float(d["mean"])
                d["mean"] = float(np.clip(old + delta, 0.01, 0.95))
                self._adjustments.append(f"FWR({payer}): {old:.3f} -> {d['mean']:.3f}")
        return self

    def set_revenue(self, annual_revenue: float) -> "ScenarioBuilder":
        """Set hospital annual revenue."""
        old = float(self._cfg.get("hospital", {}).get("annual_revenue", 0))
        self._cfg.setdefault("hospital", {})["annual_revenue"] = float(annual_revenue)
        self._adjustments.append(f"Revenue: {old:,.0f} -> {annual_revenue:,.0f}")
        return self

    def set_fte(self, fte: float) -> "ScenarioBuilder":
        """Set denial management FTE count."""
        cap = self._cfg.setdefault("operations", {}).setdefault("denial_capacity", {"fte": 12})
        old = float(cap.get("fte", 12))
        cap["fte"] = float(fte)
        self._adjustments.append(f"FTE: {old} -> {fte}")
        return self

    def adjust_upr(self, payer: str, delta: float) -> "ScenarioBuilder":
        """Adjust underpayment rate by delta."""
        if payer in self._cfg.get("payers", {}):
            u = self._cfg["payers"][payer].get("underpayments", {}).get("upr", {})
            if "mean" in u:
                old = float(u["mean"])
                u["mean"] = float(np.clip(old + delta, 0.001, 0.50))
                self._adjustments.append(f"UPR({payer}): {old:.3f} -> {u['mean']:.3f}")
        return self

    @property
    def description(self) -> str:
        return "; ".join(self._adjustments) if self._adjustments else "No changes"

    def build(self) -> Dict[str, Any]:
        """Return the modified config."""
        if self._adjustments:
            logger.info("Scenario built: %s", self.description)
        return self._cfg


def apply_scenario_dict(base_cfg: Dict[str, Any], adj: Dict[str, Any]) -> Dict[str, Any]:
    """Apply CLI --scenario JSON to a config (idr_delta per payer, fte_change, etc.)."""
    from copy import deepcopy

    cfg = deepcopy(base_cfg)
    for payer, delta in (adj.get("idr_delta_by_payer") or {}).items():
        if payer in cfg.get("payers", {}):
            d = cfg["payers"][payer].get("denials", {}).get("idr", {})
            if "mean" in d:
                d["mean"] = float(np.clip(float(d["mean"]) + float(delta), 0.01, 0.50))
    if "fte_change" in adj:
        cap = cfg.setdefault("operations", {}).setdefault("denial_capacity", {"fte": 12})
        cap["fte"] = float(max(cap.get("fte", 12) + float(adj["fte_change"]), 1))
    if "annual_revenue" in adj:
        cfg.setdefault("hospital", {})["annual_revenue"] = float(adj["annual_revenue"])
    return cfg
