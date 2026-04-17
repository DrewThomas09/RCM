"""PE math auto-compute hook for `rcm-mc run` (Brick 46).

When the actual config carries a ``deal`` section, this module materializes:

- ``pe_bridge.json``     — value creation bridge at the base hold assumption
- ``pe_returns.json``    — MOIC + IRR at base case
- ``pe_hold_grid.csv``   — hold-years × exit-multiple sensitivity
- ``pe_covenant.json``   — covenant headroom at entry EBITDA

The uplift that feeds the bridge is pulled from the simulation's
``ebitda_uplift`` mean (if present), or ``ebitda_drag`` mean as a fallback.
The design: these are always auto-computed from config + sim, never
hand-edited, so the IC numbers and the simulated numbers cannot drift.

Public API:
    compute_and_persist_pe_math(outdir, actual_cfg, summary_df) → list[str]
        Writes the four artifacts above to ``outdir``, returns the paths
        written. Returns an empty list if the ``deal`` section is absent.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

import pandas as pd

from .pe_math import (
    bridge_to_records,
    compute_returns,
    covenant_check,
    hold_period_grid,
    value_creation_bridge,
)


# ── Defaults ──────────────────────────────────────────────────────────────

# Sensitivity grid — applied when `deal` doesn't override. Covers the
# canonical PE IC question: "what if we exit in 3 vs 5 vs 7, and what if
# multiples compress 1x or expand 1x?"
_DEFAULT_HOLD_YEARS = [3, 5, 7]
_DEFAULT_EXIT_MULTIPLE_DELTAS = [-1.0, 0.0, 1.0]  # relative to deal.exit_multiple


# ── Core auto-compute ──────────────────────────────────────────────────────

def _uplift_from_summary(summary_df: Optional[pd.DataFrame]) -> float:
    """Pull the ``mean`` uplift from the run's summary.csv. 0 if absent."""
    if summary_df is None or summary_df.empty:
        return 0.0
    for metric in ("ebitda_uplift", "ebitda_drag"):
        if metric in summary_df.index and "mean" in summary_df.columns:
            try:
                return float(summary_df.loc[metric, "mean"])
            except (TypeError, ValueError):
                continue
    return 0.0


def _derive_entry_ebitda(deal: Dict[str, Any], hospital: Dict[str, Any]) -> float:
    """Resolve entry EBITDA from the config.

    Priority:
      1. ``deal.entry_ebitda`` — explicit
      2. ``hospital.annual_revenue × hospital.ebitda_margin`` — derived
      3. Raises ValueError if neither is usable
    """
    if "entry_ebitda" in deal and deal["entry_ebitda"] is not None:
        return float(deal["entry_ebitda"])
    if "ebitda_margin" in hospital and "annual_revenue" in hospital:
        rev = float(hospital["annual_revenue"])
        margin = float(hospital["ebitda_margin"])
        return rev * margin
    raise ValueError(
        "Cannot derive entry_ebitda: set deal.entry_ebitda or "
        "hospital.ebitda_margin in the config."
    )


def compute_and_persist_pe_math(
    outdir: str,
    actual_cfg: Dict[str, Any],
    summary_df: Optional[pd.DataFrame] = None,
) -> List[str]:
    """Compute PE math artifacts and persist to ``outdir``.

    Returns the list of files written (empty if no ``deal`` section).
    Never raises on downstream math errors — catches and logs a warning
    to ``pe_math_errors.txt`` so a bad deal config doesn't break a run.
    """
    deal = actual_cfg.get("deal") or {}
    if not deal:
        return []

    hospital = actual_cfg.get("hospital") or {}
    written: List[str] = []
    errors: List[str] = []

    try:
        entry_ebitda = _derive_entry_ebitda(deal, hospital)
    except ValueError as exc:
        errors.append(f"entry_ebitda: {exc}")
        _write_errors(outdir, errors)
        return []

    entry_multiple = float(deal.get("entry_multiple", 9.0))
    exit_multiple = float(deal.get("exit_multiple", entry_multiple))  # default: flat
    hold_years = float(deal.get("hold_years", 5.0))
    organic_growth = float(deal.get("organic_growth_pct", 0.0))
    equity_pct = float(deal.get("equity_pct", 1.0))

    uplift = _uplift_from_summary(summary_df)

    # ── 1. Value creation bridge ──
    try:
        bridge = value_creation_bridge(
            entry_ebitda=entry_ebitda,
            uplift=uplift,
            entry_multiple=entry_multiple,
            exit_multiple=exit_multiple,
            hold_years=hold_years,
            organic_growth_pct=organic_growth,
        )
        bridge_payload = {
            "entry_ebitda": bridge.entry_ebitda,
            "exit_ebitda": bridge.exit_ebitda,
            "entry_multiple": bridge.entry_multiple,
            "exit_multiple": bridge.exit_multiple,
            "hold_years": bridge.hold_years,
            "organic_growth_pct": bridge.organic_growth_pct,
            "rcm_uplift": bridge.rcm_uplift,
            "entry_ev": bridge.entry_ev,
            "exit_ev": bridge.exit_ev,
            "components": bridge_to_records(bridge),
            "total_value_created": bridge.total_value_created,
        }
        path = os.path.join(outdir, "pe_bridge.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(bridge_payload, f, indent=2, default=str)
        written.append(path)
    except (ValueError, TypeError) as exc:
        errors.append(f"bridge: {type(exc).__name__}: {exc}")
        bridge = None

    # ── 2. Base-case equity returns ──
    if bridge is not None:
        try:
            entry_equity = bridge.entry_ev * equity_pct
            # Assume debt held flat to exit unless a schedule is given —
            # conservative (no amortization benefit flowing to equity)
            debt_at_entry = bridge.entry_ev * (1 - equity_pct)
            exit_equity = max(bridge.exit_ev - debt_at_entry, 0.0)
            returns = compute_returns(
                entry_equity=entry_equity,
                exit_proceeds=exit_equity,
                hold_years=hold_years,
            )
            path = os.path.join(outdir, "pe_returns.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump({
                    "entry_equity": returns.entry_equity,
                    "exit_proceeds": returns.exit_proceeds,
                    "hold_years": returns.hold_years,
                    "moic": returns.moic,
                    "irr": returns.irr,
                    "total_distributions": returns.total_distributions,
                }, f, indent=2)
            written.append(path)
        except (ValueError, TypeError) as exc:
            errors.append(f"returns: {type(exc).__name__}: {exc}")

    # ── 3. Hold-years × exit-multiple sensitivity grid ──
    if bridge is not None:
        try:
            hold_years_list = _DEFAULT_HOLD_YEARS
            exit_multiples = [exit_multiple + d for d in _DEFAULT_EXIT_MULTIPLE_DELTAS
                              if exit_multiple + d > 0]
            entry_equity = bridge.entry_ev * equity_pct
            debt_at_entry = bridge.entry_ev * (1 - equity_pct)
            rows = hold_period_grid(
                entry_ebitda=entry_ebitda,
                uplift_by_year={y: uplift for y in hold_years_list},
                entry_multiple=entry_multiple,
                exit_multiples=exit_multiples,
                hold_years_list=hold_years_list,
                entry_equity=entry_equity,
                debt_at_entry=debt_at_entry,
                organic_growth_pct=organic_growth,
            )
            path = os.path.join(outdir, "pe_hold_grid.csv")
            pd.DataFrame(rows).to_csv(path, index=False)
            written.append(path)
        except (ValueError, TypeError) as exc:
            errors.append(f"hold_grid: {type(exc).__name__}: {exc}")

    # ── 4. Covenant headroom ──
    if "covenant_max_leverage" in deal:
        try:
            cov_leverage = float(deal["covenant_max_leverage"])
            interest_rate = float(deal.get("interest_rate", 0.0))
            debt_at_entry = entry_ebitda * entry_multiple * (1 - equity_pct)
            c = covenant_check(
                ebitda=entry_ebitda,
                debt=debt_at_entry,
                covenant_max_leverage=cov_leverage,
                interest_rate=interest_rate,
            )
            path = os.path.join(outdir, "pe_covenant.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump({
                    "ebitda": c.ebitda,
                    "debt": c.debt,
                    "covenant_max_leverage": c.covenant_max_leverage,
                    "actual_leverage": c.actual_leverage,
                    "covenant_headroom_turns": c.covenant_headroom_turns,
                    "ebitda_cushion_pct": c.ebitda_cushion_pct,
                    "covenant_trips_at_ebitda": c.covenant_trips_at_ebitda,
                    "interest_coverage": c.interest_coverage,
                }, f, indent=2)
            written.append(path)
        except (ValueError, TypeError) as exc:
            errors.append(f"covenant: {type(exc).__name__}: {exc}")

    if errors:
        _write_errors(outdir, errors)
    return written


def _write_errors(outdir: str, errors: List[str]) -> None:
    """Persist PE math errors out-of-band so a bad deal config doesn't break the run."""
    path = os.path.join(outdir, "pe_math_errors.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(errors) + "\n")
