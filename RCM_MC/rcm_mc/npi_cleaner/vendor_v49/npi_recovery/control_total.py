"""
control_total.py  (v31)
=======================

Answers the transcript problem: "the sum of the unblinded fields is inexplainably
low for Option Care ... we're rebuilding to numbers that are too low."

A rebuilt panel total that lands below a known control total (the client's stated
revenue, or the sum of an unblinded field) is almost never random. This module
takes the control total, measures what the panel actually captured, and then
attributes the shortfall to concrete, testable causes rather than leaving it as
an "inexplicable" gap. The two causes the team already suspected both have a
number attached elsewhere in v31:

  * split-code undercount  - a molecule billed under several J-codes where the
    build only picked up the first code (common_name.common_name_rollup gives
    undercount_if_first_code_only per molecule).
  * government channel      - dollars billed through the client's own pharmacy
    NPIs that were filtered out of the captured book (npi_channel gives the
    government-billing allowed).

Whatever those buckets do not explain is reported as an honest residual, not
buried. The design is confirm-or-deny: state the target, show the capture, and
let each recovery bucket either close the gap or fail to.

Both functions are pure and offline-safe. With no control total supplied they
return an honest note; with no recovery buckets they still report capture vs
target and a fully unexplained residual.
"""

from __future__ import annotations

from collections import OrderedDict

import numpy as np
import pandas as pd

from . import common_name as _cn


def _as_total(captured) -> float:
    if captured is None:
        return 0.0
    if isinstance(captured, (int, float, np.integer, np.floating)):
        return float(captured)
    return float(pd.to_numeric(pd.Series(captured), errors="coerce").fillna(0.0).sum())


def reconcile_control_total(*, captured, control_total,
                            recovery_buckets=None,
                            entity_label: str = "entity",
                            units_label: str = "$") -> pd.DataFrame:
    """Reconcile a captured total against a known control total and attribute the
    shortfall to named recovery buckets.

    captured         float, or a numeric Series that is summed.
    control_total    the target number the rebuild should reach (float).
    recovery_buckets ordered {label: dollars} that each explain part of the
                     shortfall (e.g. {"split-code undercount": 32000,
                     "government pharmacy channel": 41000}). Order is preserved.
    Returns a Control_Total_Reconciliation table."""
    if control_total is None or float(control_total) <= 0:
        return pd.DataFrame({"note": [
            "no control total supplied. Pass --control-total <amount> (the client's "
            "stated revenue or the sum of the unblinded field) to reconcile the rebuild "
            "against it."]})

    ctrl = float(control_total)
    cap = _as_total(captured)
    shortfall = ctrl - cap
    buckets = OrderedDict(recovery_buckets or {})

    rows = [
        {"line": f"control total ({entity_label})", "amount": round(ctrl, 2), "pct_of_control": 100.0},
        {"line": "captured in rebuild", "amount": round(cap, 2),
         "pct_of_control": round(cap / ctrl * 100, 1)},
        {"line": "shortfall (control - captured)", "amount": round(shortfall, 2),
         "pct_of_control": round(shortfall / ctrl * 100, 1)},
        {"line": "---- shortfall attribution ----", "amount": np.nan, "pct_of_control": np.nan},
    ]

    explained = 0.0
    for label, amt in buckets.items():
        val = float(amt or 0.0)
        explained += val
        rows.append({
            "line": f"recoverable: {label}", "amount": round(val, 2),
            "pct_of_control": round(val / ctrl * 100, 1),
            "pct_of_shortfall": (round(val / shortfall * 100, 1) if shortfall > 0 else np.nan),
        })

    residual = shortfall - explained
    rows.append({
        "line": "unexplained residual", "amount": round(residual, 2),
        "pct_of_control": round(residual / ctrl * 100, 1),
        "pct_of_shortfall": (round(residual / shortfall * 100, 1) if shortfall > 0 else np.nan),
    })
    rows.append({
        "line": "capture after recoveries", "amount": round(cap + explained, 2),
        "pct_of_control": round((cap + explained) / ctrl * 100, 1),
    })

    out = pd.DataFrame(rows)
    verdict = (
        "MATCH" if abs(shortfall) / ctrl < 0.02 else
        ("EXPLAINED" if shortfall > 0 and residual / max(shortfall, 1e-9) < 0.10 else
         ("PARTIALLY EXPLAINED" if explained > 0 else "UNEXPLAINED")))
    out.attrs["note"] = (
        "Verdict: {v}. Captured {cp:.1f}% of the control total; recovery buckets explain "
        "{ex:.1f}% of the shortfall, leaving {rz:.1f}% unexplained. Recovery amounts are "
        "additive estimates from the split-code and government-channel diagnostics; they "
        "are candidates to re-include, not a silent adjustment to the rebuilt total."
    ).format(
        v=verdict,
        cp=cap / ctrl * 100,
        ex=(explained / shortfall * 100 if shortfall > 0 else 0.0),
        rz=(residual / shortfall * 100 if shortfall > 0 else 0.0),
    )
    out.attrs["verdict"] = verdict
    return out


def exposure_summary(*, panel_total, split_code_undercount=0.0,
                     government_channel=0.0, control_total=None) -> pd.DataFrame:
    """What a naive rebuild would drop, stated against the full captured panel and
    NOT added to it. This is the direct read on 'our rebuild is inexplicably low':
    a pick-the-first-J-code rebuild loses the split-code dollars; a commercial-only
    rebuild loses the government-pharmacy channel. Both figures already sit inside
    the panel total, so they are shown as exposure, never summed on top of it."""
    panel = float(panel_total or 0.0)
    rows = [
        {"line": "captured panel total", "amount": round(panel, 2),
         "pct_of_panel": 100.0 if panel > 0 else np.nan},
        {"line": "at risk: first-code-only rebuild loses split-code dollars",
         "amount": round(float(split_code_undercount or 0.0), 2),
         "pct_of_panel": (round(float(split_code_undercount or 0.0) / panel * 100, 1)
                          if panel > 0 else np.nan)},
        {"line": "at risk: commercial-only rebuild loses government-pharmacy channel",
         "amount": round(float(government_channel or 0.0), 2),
         "pct_of_panel": (round(float(government_channel or 0.0) / panel * 100, 1)
                          if panel > 0 else np.nan)},
    ]
    if control_total and float(control_total) > 0:
        ctrl = float(control_total)
        rows.append({"line": "control total (target)", "amount": round(ctrl, 2),
                     "pct_of_panel": round(ctrl / panel * 100, 1) if panel > 0 else np.nan})
        rows.append({"line": "panel vs control (panel - control)",
                     "amount": round(panel - ctrl, 2),
                     "pct_of_panel": round((panel - ctrl) / ctrl * 100, 1)})
    out = pd.DataFrame(rows)
    out.attrs["note"] = (
        "Exposure figures already sit inside the captured panel total; they are the "
        "dollars a naive rebuild drops, not amounts to add. Group molecules across "
        "member J-codes (see Common_Name_Rollup) and keep the government-pharmacy NPIs "
        "(see NPI_Channel_Classification) and the rebuild reconciles.")
    return out


def capture_by_drug(std_named: pd.DataFrame, *, allowed,
                    per_drug_control=None, units=None, top_n: int = 200) -> pd.DataFrame:
    """Per common-name molecule, how much the panel captured and (when a per-drug
    control map is supplied) how that compares to target. Molecules are grouped by
    drug_common_name so a split-code drug (Stelara across J3357/J3358/J3590) is
    measured as one line, and the largest-single-code share is surfaced so the
    "only the first J-code was picked up" molecules stand out.

    per_drug_control  optional {common_name: target_dollars}. Rows are sorted by
                      the absolute gap so the biggest misses lead."""
    roll = _cn.common_name_rollup(std_named, allowed=allowed, units=units, top_n=10_000)
    if roll.empty or "note" in roll.columns:
        return roll

    targets = {str(k).strip().lower(): float(v) for k, v in (per_drug_control or {}).items()}
    if targets:
        def _tgt(name):
            return targets.get(str(name).strip().lower(), np.nan)
        roll["target_allowed"] = roll["drug_common_name"].map(_tgt)
        roll["captured_vs_target_pct"] = np.where(
            roll["target_allowed"] > 0,
            np.round(roll["allowed"] / roll["target_allowed"] * 100, 1), np.nan)
        roll["gap_to_target"] = np.where(
            roll["target_allowed"].notna(),
            np.round(roll["target_allowed"] - roll["allowed"], 2), np.nan)
        roll = roll.sort_values(
            "gap_to_target", ascending=False, na_position="last").reset_index(drop=True)
        roll.attrs["note"] = (
            "gap_to_target = target - captured per molecule (grouped across all member "
            "J-codes). Positive gap = undercaptured. split_across_codes with a low "
            "largest_code_share_pct is the signature of a first-code-only pickup.")
    else:
        roll.attrs["note"] = (
            "Per-molecule capture grouped across all member J-codes. Supply a per-drug "
            "control map to compute gap-to-target. split_across_codes molecules with a low "
            "largest_code_share_pct are the ones most at risk of a first-code-only undercount.")

    return roll.head(top_n)
