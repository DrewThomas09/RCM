"""
Value attribution for RCM Monte Carlo: OAT (one-at-a-time) $ contribution by driver bucket.

Buckets are explainable groupings (payer denials, payer underpayments, A/R days, appeals).
Uses mixed configs: for subset S, mixed(S) = actual with benchmark values for buckets in S.
D_S = mean ebitda_drag(mixed(S), benchmark) = remaining drag when S is "fixed".
OAT: uplift_i = D_empty - D_{i}
"""
from __future__ import annotations

import copy
from typing import Any, Dict, Set

import pandas as pd

from ..core.simulator import simulate_compare

BUCKET_NAMES = [
    "Commercial Denials",
    "Medicare Denials",
    "Medicaid Denials",
    "Commercial Underpayments",
    "Medicare Underpayments",
    "Medicaid Underpayments",
    "Clean-claim A/R days",
    "Appeals costs and days",
]


def _apply_commercial_denials(cfg: Dict[str, Any], bench: Dict[str, Any]) -> None:
    p = cfg.get("payers", {})
    b = bench.get("payers", {})
    if "Commercial" in p and "Commercial" in b and "denials" in b["Commercial"]:
        p["Commercial"]["denials"] = copy.deepcopy(b["Commercial"]["denials"])


def _apply_medicare_denials(cfg: Dict[str, Any], bench: Dict[str, Any]) -> None:
    p = cfg.get("payers", {})
    b = bench.get("payers", {})
    if "Medicare" in p and "Medicare" in b and "denials" in b["Medicare"]:
        p["Medicare"]["denials"] = copy.deepcopy(b["Medicare"]["denials"])


def _apply_medicaid_denials(cfg: Dict[str, Any], bench: Dict[str, Any]) -> None:
    p = cfg.get("payers", {})
    b = bench.get("payers", {})
    if "Medicaid" in p and "Medicaid" in b and "denials" in b["Medicaid"]:
        p["Medicaid"]["denials"] = copy.deepcopy(b["Medicaid"]["denials"])


def _apply_commercial_underpayments(cfg: Dict[str, Any], bench: Dict[str, Any]) -> None:
    p = cfg.get("payers", {})
    b = bench.get("payers", {})
    if "Commercial" in p and "Commercial" in b and "underpayments" in b["Commercial"]:
        p["Commercial"]["underpayments"] = copy.deepcopy(b["Commercial"]["underpayments"])


def _apply_medicare_underpayments(cfg: Dict[str, Any], bench: Dict[str, Any]) -> None:
    p = cfg.get("payers", {})
    b = bench.get("payers", {})
    if "Medicare" in p and "Medicare" in b and "underpayments" in b["Medicare"]:
        p["Medicare"]["underpayments"] = copy.deepcopy(b["Medicare"]["underpayments"])


def _apply_medicaid_underpayments(cfg: Dict[str, Any], bench: Dict[str, Any]) -> None:
    p = cfg.get("payers", {})
    b = bench.get("payers", {})
    if "Medicaid" in p and "Medicaid" in b and "underpayments" in b["Medicaid"]:
        p["Medicaid"]["underpayments"] = copy.deepcopy(b["Medicaid"]["underpayments"])


def _apply_dar_clean(cfg: Dict[str, Any], bench: Dict[str, Any]) -> None:
    p = cfg.get("payers", {})
    b = bench.get("payers", {})
    for payer in list(p.keys()):
        if payer in b and "dar_clean_days" in b[payer]:
            p[payer]["dar_clean_days"] = copy.deepcopy(b[payer]["dar_clean_days"])


def _apply_appeals(cfg: Dict[str, Any], bench: Dict[str, Any]) -> None:
    if "appeals" in bench and "stages" in bench["appeals"]:
        cfg["appeals"] = copy.deepcopy(bench["appeals"])


_BUCKET_APPLIERS = [
    _apply_commercial_denials,
    _apply_medicare_denials,
    _apply_medicaid_denials,
    _apply_commercial_underpayments,
    _apply_medicare_underpayments,
    _apply_medicaid_underpayments,
    _apply_dar_clean,
    _apply_appeals,
]


def build_mixed_config(
    actual_cfg: Dict[str, Any],
    benchmark_cfg: Dict[str, Any],
    bucket_indices: Set[int],
) -> Dict[str, Any]:
    """Build config = actual with benchmark values for buckets in bucket_indices (no mutation)."""
    cfg = copy.deepcopy(actual_cfg)
    for i in bucket_indices:
        if 0 <= i < len(_BUCKET_APPLIERS):
            _BUCKET_APPLIERS[i](cfg, benchmark_cfg)
    return cfg


def compute_remaining_drag(
    actual_cfg: Dict[str, Any],
    benchmark_cfg: Dict[str, Any],
    bucket_indices: Set[int],
    n_sims: int,
    seed: int,
    align_profile: bool = True,
) -> float:
    """Mean ebitda_drag for mixed(S) vs benchmark."""
    mixed = build_mixed_config(actual_cfg, benchmark_cfg, bucket_indices)
    df = simulate_compare(mixed, benchmark_cfg, n_sims=n_sims, seed=seed, align_profile=align_profile)
    return float(df["ebitda_drag"].mean())


def run_oat_attribution(
    actual_cfg: Dict[str, Any],
    benchmark_cfg: Dict[str, Any],
    n_sims: int,
    seed: int,
    align_profile: bool = True,
) -> pd.DataFrame:
    """One-at-a-time uplift per bucket: uplift_i = D_empty - D_{i}."""
    d_empty = compute_remaining_drag(actual_cfg, benchmark_cfg, set(), n_sims, seed, align_profile)
    rows = []
    for i, name in enumerate(BUCKET_NAMES):
        d_i = compute_remaining_drag(actual_cfg, benchmark_cfg, {i}, n_sims, seed + 100 + i, align_profile)
        uplift = d_empty - d_i
        rows.append({"bucket": name, "remaining_drag": d_i, "uplift_oat": uplift})
    return pd.DataFrame(rows)


def run_attribution(
    actual_cfg: Dict[str, Any],
    benchmark_cfg: Dict[str, Any],
    n_sims: int = 3000,
    seed: int = 42,
    align_profile: bool = True,
) -> Dict[str, Any]:
    """Run OAT attribution and return results dict (baseline drag + OAT uplifts sorted desc)."""
    oat_df = run_oat_attribution(actual_cfg, benchmark_cfg, n_sims, seed, align_profile)
    baseline_drag = float(
        compute_remaining_drag(actual_cfg, benchmark_cfg, set(), n_sims, seed, align_profile)
    )
    oat_sorted = oat_df.sort_values("uplift_oat", ascending=False).reset_index(drop=True)
    return {
        "oat": oat_sorted,
        "baseline_drag": baseline_drag,
        "bucket_names": BUCKET_NAMES,
    }


def plot_tornado(oat_df: pd.DataFrame, outpath: str, baseline_drag: float) -> None:
    """Bar chart of OAT uplifts (tornado style)."""
    import matplotlib.pyplot as plt

    df = oat_df.sort_values("uplift_oat", ascending=True)
    labels = df["bucket"].tolist()
    vals = df["uplift_oat"].tolist()
    colors = ["#2563eb" if v >= 0 else "#dc2626" for v in vals]

    fig, ax = plt.subplots(figsize=(10, max(6, len(labels) * 0.45)), facecolor="#fafafa")
    ax.set_facecolor("#fafafa")
    y_pos = range(len(labels))
    bars = ax.barh(y_pos, vals, color=colors, edgecolor="white", linewidth=0.8)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=10)
    ax.axvline(0, color="#374151", linewidth=1, linestyle="-")
    ax.set_xlabel("$ uplift if fixed to benchmark (OAT)", fontsize=11)
    ax.set_title("Value Attribution: $ Uplift by Driver Bucket", fontsize=13, fontweight=600)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    def _fmt(x: float) -> str:
        if abs(x) >= 1e6:
            return f"${x/1e6:.1f}M"
        if abs(x) >= 1e3:
            return f"${x/1e3:.0f}K"
        return f"${x:.0f}"

    for bar, v in zip(bars, vals):
        w = bar.get_width()
        ha = "left" if v >= 0 else "right"
        ax.text(w, bar.get_y() + bar.get_height() / 2, _fmt(v), ha=ha, va="center", fontsize=9)

    fig.tight_layout()
    fig.savefig(outpath, dpi=150, bbox_inches="tight", facecolor="#fafafa")
    plt.close(fig)
