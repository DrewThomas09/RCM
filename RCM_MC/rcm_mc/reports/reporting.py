from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def summarize_distribution(df: pd.DataFrame, col: str) -> Dict[str, float]:
    x = df[col].to_numpy(dtype=float)
    # Robustness: ignore NaN/Inf (common when summarizing payback or ratios).
    x = x[np.isfinite(x)]
    if x.size == 0:
        return {"mean": float("nan"), "median": float("nan"), "p10": float("nan"), "p25": float("nan"), "p75": float("nan"), "p90": float("nan"), "p95": float("nan")}
    return {
        "mean": float(np.mean(x)),
        "median": float(np.median(x)),
        "p10": float(np.quantile(x, 0.10)),
        "p25": float(np.quantile(x, 0.25)),
        "p75": float(np.quantile(x, 0.75)),
        "p90": float(np.quantile(x, 0.90)),
        "p95": float(np.quantile(x, 0.95)),
    }


def summary_table(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
    rows = []
    for c in cols:
        s = summarize_distribution(df, c)
        rows.append({"metric": c, **s})
    out = pd.DataFrame(rows)
    return out.set_index("metric")


def pretty_money(x: float) -> str:
    """Compact money display: $8.8M, $-1.2K, etc."""
    sign = "-" if x < 0 else ""
    x = abs(float(x))
    if x >= 1e9:
        return f"{sign}${x/1e9:.1f}B"
    if x >= 1e6:
        return f"{sign}${x/1e6:.1f}M"
    if x >= 1e3:
        return f"{sign}${x/1e3:.0f}K"
    return f"{sign}${x:.0f}"


# Board-ready metric names (PE presentation standard)
METRIC_LABELS = {
    "ebitda_drag": "Total EBITDA Drag",
    "economic_drag": "Working Capital Cost (Economic Drag)",
    "drag_denial_writeoff": "Denial Write-Off Leakage",
    "drag_underpay_leakage": "Underpayment Leakage",
    "drag_denial_rework_cost": "Denial Rework Cost",
    "drag_underpay_cost": "Underpayment Follow-Up Cost",
    "drag_dar_total": "Excess Days in Accounts Receivable",
    "actual_rcm_ebitda_impact": "Actual RCM EBITDA Impact",
    "bench_rcm_ebitda_impact": "Benchmark RCM EBITDA Impact",
}


def _driver_label(name: str) -> str:
    """Convert technical driver names to PE-readable labels."""
    parts = name.replace("actual_", "").split("_")
    mapping = {
        "idr": "Initial Denial Rate",
        "fwr": "Final Write-Off Rate",
        "dar_clean": "Clean A/R Days",
        "upr": "Underpayment Rate",
        "severity": "Underpayment Severity",
        "recovery": "Recovery Rate",
        "revenue_share": "Revenue Share",
    }
    if len(parts) >= 2:
        var = "_".join(parts[:-1]) if "dar" in parts[0] else parts[0]
        payer = parts[-1].title()
        label = mapping.get(var, var.replace("_", " ").title())
        return f"{label} ({payer})"
    return name.replace("_", " ").title()


def waterfall_ebitda_drag(
    df: pd.DataFrame,
    outpath: str,
    reported_ebitda: Optional[float] = None,
) -> None:
    """
    Board-ready waterfall: Reported EBITDA -> bridges (Addressable Leakage) -> Pro-Forma EBITDA.
    Color logic: Red = Drag/Losses, Green = Recoverable Opportunity, Grey/Blue = Structural.
    """
    comps = [
        ("Addressable Denial Leakage", df["drag_denial_writeoff"].mean()),
        ("Addressable Underpayment Leakage", df["drag_underpay_leakage"].mean()),
        ("Denial Rework Cost (Recoverable)", df["drag_denial_rework_cost"].mean()),
        ("Underpayment Rework Cost (Recoverable)", df["drag_underpay_cost"].mean()),
    ]
    total_drag = sum(v for _, v in comps)
    if reported_ebitda is not None and reported_ebitda > 0:
        # Pro-Forma anchor: start with Reported, add recoverable, end with Pro-Forma
        start_val = reported_ebitda
        end_val = reported_ebitda + total_drag
        labels = ["Reported EBITDA"] + [c[0] for c in comps] + ["Pro-Forma EBITDA"]
        values = [start_val] + [c[1] for c in comps] + [end_val]
        cum = [0.0]
        for v in values[:-1]:
            cum.append(cum[-1] + v)
        cum = cum[:-1]
        bar_colors = ["#64748b"] + ["#059669"] * 4 + ["#0f172a"]  # Grey start, Green bridges, Dark end
        # Bridges go UP (recoverable add-backs)
        fig, ax = plt.subplots(figsize=(12, 6), facecolor="#fafafa")
        ax.set_facecolor("#fafafa")
        for i, (lab, v) in enumerate(zip(labels, values)):
            if i == 0:
                ax.bar(i, v, bottom=0, color=bar_colors[i], edgecolor="white", linewidth=0.8)
                y_pos = v
            elif i == len(labels) - 1:
                ax.bar(i, v, bottom=0, color=bar_colors[i], edgecolor="white", linewidth=0.8)
                y_pos = v
            else:
                ax.bar(i, v, bottom=cum[i], color=bar_colors[i], edgecolor="white", linewidth=0.8)
                y_pos = cum[i] + v
            offset = max(total_drag * 0.02, 50000)
            ax.text(i, y_pos + offset, pretty_money(v), ha="center", va="bottom", fontsize=9, fontweight=600)
        ax.axhline(0, color="#374151", linewidth=1, linestyle="-")
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=25, ha="right", fontsize=9)
        ax.set_ylabel("EBITDA ($)", fontsize=11, fontweight=500)
        ax.set_title("Strategic Value Creation: Reported → Pro-Forma EBITDA Bridge", fontsize=13, fontweight=600, pad=14)
    else:
        # Fallback: component decomposition (board labels, red/green)
        labels = [c[0] for c in comps] + ["Total Addressable Opportunity"]
        values = [c[1] for c in comps] + [total_drag]
        cum = [0.0]
        for v in values[:-1]:
            cum.append(cum[-1] + v)
        cum = cum[:-1]
        bar_colors = ["#dc2626", "#dc2626", "#059669", "#059669", "#0f172a"]  # Red leakage, Green recoverable
        fig, ax = plt.subplots(figsize=(11, 6), facecolor="#fafafa")
        ax.set_facecolor("#fafafa")
        for i, (lab, v) in enumerate(comps):
            ax.bar(i, v, bottom=cum[i], color=bar_colors[i], edgecolor="white", linewidth=0.8)
            y_pos = cum[i] + v
            offset = total_drag * 0.02 if total_drag != 0 else 1000
            ax.text(i, y_pos + offset, pretty_money(v), ha="center", va="bottom", fontsize=10, fontweight=600)
        ax.bar(len(comps), total_drag, color=bar_colors[-1], edgecolor="white", linewidth=0.8)
        ax.text(len(comps), total_drag + (total_drag * 0.02 if total_drag != 0 else 1000),
                pretty_money(total_drag), ha="center", va="bottom", fontsize=11, fontweight=700)
        ax.axhline(0, color="#374151", linewidth=1, linestyle="-")
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=20, ha="right", fontsize=10)
        ax.set_ylabel("Annual Addressable Opportunity (Actual vs Benchmark)", fontsize=11, fontweight=500)
        ax.set_title("RCM EBITDA Opportunity: Mean Decomposition", fontsize=13, fontweight=600, pad=14)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: pretty_money(x)))
    fig.tight_layout()
    fig.savefig(outpath, dpi=150, bbox_inches="tight", facecolor="#fafafa")
    plt.close(fig)


def plot_denial_drivers_chart(df_drag: pd.DataFrame, outpath: str, top_n: int = 10) -> None:
    """Horizontal bar chart of top denial write-off drag by payer × root cause (PE-friendly)."""
    if df_drag is None or df_drag.empty or "drag_mean_denial_writeoff" not in df_drag.columns:
        return
    top = df_drag.nlargest(top_n, "drag_mean_denial_writeoff")
    labels = [f"{r['payer']} · {r['root_cause']}" for _, r in top.iterrows()]
    vals = top["drag_mean_denial_writeoff"].values
    fig, ax = plt.subplots(figsize=(10, max(5, len(labels) * 0.5)), facecolor="#fafafa")
    ax.set_facecolor("#fafafa")
    colors = ["#1e40af" if v > 0 else "#dc2626" for v in vals]
    bars = ax.barh(range(len(labels)), vals, color=colors, edgecolor="white", linewidth=0.8)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=10)
    ax.axvline(0, color="#374151", linewidth=1)
    ax.set_xlabel("Annual write-off drag ($)", fontsize=11)
    ax.set_title("Top Denial Drivers by Payer & Root Cause", fontsize=13, fontweight=600)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: pretty_money(x)))
    for bar, v in zip(bars, vals):
        ax.text(bar.get_width(), bar.get_y() + bar.get_height() / 2, pretty_money(v),
                ha="left" if v >= 0 else "right", va="center", fontsize=9, fontweight=500)
    fig.tight_layout()
    fig.savefig(outpath, dpi=150, bbox_inches="tight", facecolor="#fafafa")
    plt.close(fig)


def plot_underpayments_chart(df_drag: pd.DataFrame, outpath: str) -> None:
    """Bar chart of underpayment leakage and rework cost drag by payer (PE-friendly)."""
    if df_drag is None or df_drag.empty:
        return
    df = df_drag[df_drag["payer"] != "SelfPay"] if "SelfPay" in df_drag["payer"].values else df_drag
    leak = df[df["metric"] == "underpay_leakage"].sort_values("drag_mean_value", ascending=False)
    cost = df[df["metric"] == "underpay_cost"]
    if leak.empty:
        return
    payers = leak["payer"].tolist()
    x = range(len(payers))
    w = 0.35
    leak_vals = leak.set_index("payer").reindex(payers)["drag_mean_value"].fillna(0).values
    cost_vals = cost.set_index("payer").reindex(payers)["drag_mean_value"].fillna(0).values
    fig, ax = plt.subplots(figsize=(9, 5), facecolor="#fafafa")
    ax.set_facecolor("#fafafa")
    ax.bar([i - w / 2 for i in x], leak_vals, w, label="Leakage", color="#1e40af", edgecolor="white")
    ax.bar([i + w / 2 for i in x], cost_vals, w, label="Rework cost", color="#64748b", edgecolor="white")
    ax.set_xticks(x)
    ax.set_xticklabels(payers)
    ax.set_ylabel("Annual drag ($)", fontsize=11)
    ax.set_title("Underpayment Drag by Payer", fontsize=13, fontweight=600)
    ax.legend()
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: pretty_money(x)))
    fig.tight_layout()
    fig.savefig(outpath, dpi=150, bbox_inches="tight", facecolor="#fafafa")
    plt.close(fig)


def plot_deal_summary(summary: pd.DataFrame, ev_multiple: float, outpath: str) -> None:
    """Deal opportunity: three bars for P10, Mean, P90 EV (PE-friendly)."""
    if summary is None or "ebitda_drag" not in summary.index:
        return
    ebitda_p10 = float(summary.loc["ebitda_drag", "p10"])
    ebitda_mean = float(summary.loc["ebitda_drag", "mean"])
    ebitda_p90 = float(summary.loc["ebitda_drag", "p90"])
    ev_p10 = ebitda_p10 * ev_multiple
    ev_mean = ebitda_mean * ev_multiple
    ev_p90 = ebitda_p90 * ev_multiple
    fig, ax = plt.subplots(figsize=(10, 5), facecolor="#fafafa")
    ax.set_facecolor("#fafafa")
    labels = ["P10 (conservative)", "Mean", "P90 (aggressive)"]
    vals = [ev_p10, ev_mean, ev_p90]
    colors = ["#64748b", "#1e40af", "#0f172a"]
    bars = ax.barh(labels, vals, 0.5, color=colors, edgecolor="white", linewidth=1)
    ax.set_xlabel("Enterprise value ($)", fontsize=11)
    ax.set_title(f"Deal Opportunity Range (at {ev_multiple}x EBITDA multiple)", fontsize=13, fontweight=600)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: pretty_money(x)))
    max_val = max(vals) if vals else 0.0
    label_pad = max(max_val * 0.03, 1.0)
    x_right = max(max_val + (label_pad * 6.0), 1.0)
    ax.set_xlim(0, x_right)
    for bar, v in zip(bars, vals):
        ax.text(min(bar.get_width() + label_pad, x_right * 0.96),
                bar.get_y() + bar.get_height() / 2, f" {pretty_money(v)}",
                ha="left", va="center", fontsize=10, fontweight=600)
    # Explicit margins keep the value labels inside the figure bounds
    # without relying on tight_layout to expand for text outside axes.
    fig.subplots_adjust(left=0.24, right=0.96, top=0.86, bottom=0.16)
    fig.savefig(outpath, dpi=150, bbox_inches="tight", facecolor="#fafafa")
    plt.close(fig)


def plot_ebitda_drag_distribution(
    df: pd.DataFrame,
    outpath: str,
    covenant_trigger_drag: Optional[float] = None,
    management_case_drag: Optional[float] = None,
) -> None:
    """
    Elite advisory "Risk/Reward" visualization: KDE density, ghosted benchmark, direct callouts.
    """
    try:
        from scipy.stats import gaussian_kde
    except ImportError:
        gaussian_kde = None

    x = df["ebitda_drag"].dropna().values
    x = x[np.isfinite(x)]
    if x.size == 0:
        return
    p10 = float(np.quantile(x, 0.10))
    p90 = float(np.quantile(x, 0.90))
    mean_val = float(np.mean(x))

    fig, ax = plt.subplots(figsize=(11, 6), facecolor="#fafafa")
    ax.set_facecolor("#fafafa")
    x_min, x_max = float(np.percentile(x, 0.5)), float(np.percentile(x, 99.5))
    x_range = np.linspace(max(0, x_min - (x_max - x_min) * 0.1), x_max * 1.15, 300)

    y_hi = 1e-7
    if gaussian_kde is not None and x.size >= 20:
        try:
            kde = gaussian_kde(x, bw_method=0.12)
            y_kde = kde(x_range)
            y_kde = np.maximum(y_kde, 0)
            y_hi = float(np.max(y_kde))
            ax.fill_between(x_range, 0, y_kde, alpha=0.5, color="#1e40af")
            ax.plot(x_range, y_kde, color="#1e40af", linewidth=2.5)
        except Exception:
            n, _, _ = ax.hist(x, bins=min(60, max(25, len(x) // 40)), color="#1e40af", alpha=0.6,
                              edgecolor="white", density=True)
            y_hi = float(np.max(n)) if len(n) > 0 else 1e-7
    else:
        n, _, _ = ax.hist(x, bins=min(60, max(25, len(x) // 40)), color="#1e40af", alpha=0.6,
                          edgecolor="white", density=True)
        y_hi = float(np.max(n)) if len(n) > 0 else 1e-7

    # Ghosted Benchmark: target = zero drag ("what good looks like")
    try:
        from scipy.stats import norm
        std_t = max((x_max - x_min) * 0.08, mean_val * 0.1)
        y_t = norm.pdf(x_range, 0, std_t)
        y_t = np.maximum(y_t, 0)
        if np.max(y_t) > 0 and y_hi > 0:
            scale = 0.35 * y_hi / np.max(y_t)
            ax.fill_between(x_range, 0, y_t * scale, alpha=0.12, color="#64748b")
            ax.plot(x_range, y_t * scale, color="#94a3b8", linestyle="--", linewidth=1.5, alpha=0.5)
    except Exception:
        pass

    # Direct annotation callouts
    ax.annotate(
        f"Model Mean: {pretty_money(mean_val)}",
        xy=(mean_val, y_hi * 0.5),
        xytext=(mean_val + (x_max - x_min) * 0.08, y_hi * 0.7),
        fontsize=10, fontweight=600, color="#1e40af",
        arrowprops=dict(arrowstyle="->", color="#1e40af", lw=1.5),
    )
    ax.axvline(mean_val, color="#1e40af", linestyle="--", linewidth=1.5, alpha=0.8)

    ax.annotate(
        f"High-Stress Scenario: {pretty_money(p90)}",
        xy=(p90, 0),
        xytext=(p90 + (x_max - x_min) * 0.03, y_hi * 0.25),
        fontsize=9, fontweight=600, color="#dc2626",
        arrowprops=dict(arrowstyle="->", color="#dc2626", lw=1.2),
    )
    ax.axvline(p90, color="#dc2626", linestyle=":", linewidth=1.2, alpha=0.7)

    if covenant_trigger_drag is not None and covenant_trigger_drag > 0 and covenant_trigger_drag < x_max * 1.2:
        ax.axvline(covenant_trigger_drag, color="#b91c1c", linestyle="-", linewidth=2, alpha=0.9)
        ax.annotate(
            f"Covenant breach threshold",
            xy=(covenant_trigger_drag, y_hi * 0.35),
            fontsize=8, color="#b91c1c", ha="center",
        )

    if management_case_drag is not None:
        ax.scatter([management_case_drag], [y_hi * 0.15], s=100, color="#059669", zorder=5,
                   edgecolors="#0f172a", linewidths=2)
        ax.annotate(
            f"Mgmt Case: {pretty_money(management_case_drag)}",
            xy=(management_case_drag, y_hi * 0.15),
            xytext=(management_case_drag - (x_max - x_min) * 0.15, y_hi * 0.4),
            fontsize=9, fontweight=500, color="#059669",
            arrowprops=dict(arrowstyle="->", color="#059669", lw=1),
        )

    ax.set_xlabel("EBITDA Drag ($)", fontsize=11)
    ax.set_ylabel("Density", fontsize=11)
    ax.set_title("Risk/Reward Profile: Actual vs Benchmark (Value Gap)", fontsize=13, fontweight=600)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_ylim(bottom=0)
    ax.set_xlim(left=max(0, x_min - (x_max - x_min) * 0.05))
    fig.tight_layout()
    fig.savefig(outpath, dpi=150, bbox_inches="tight", facecolor="#fafafa")
    plt.close(fig)


def correlation_sensitivity(df: pd.DataFrame, driver_cols: List[str], target_col: str = "ebitda_drag", top_n: int = 12) -> pd.DataFrame:
    """Pearson correlation between driver inputs and EBITDA drag (with readable labels)."""
    rows = []
    y = df[target_col].astype(float)
    for c in driver_cols:
        if c not in df.columns:
            continue
        x = df[c].astype(float)
        mask = np.isfinite(x) & np.isfinite(y)
        x2 = x[mask]
        y2 = y[mask]
        if x2.std() == 0 or x2.empty:
            continue
        corr = float(x2.corr(y2))
        rows.append({"driver": c, "driver_label": _driver_label(c), "corr": round(corr, 3)})
    out = pd.DataFrame(rows).sort_values("corr", key=lambda s: s.abs(), ascending=False)
    return out.head(top_n)


def strategic_priority_matrix(sens_df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert sensitivity to Strategic Priority Matrix: Impact, Ease, Tier.
    Board-ready for PE diligence.
    """
    from ..data.data_scrub import board_ready_driver_label

    def _impact(corr: float) -> str:
        a = abs(corr)
        if a >= 0.35:
            return "High"
        if a >= 0.2:
            return "Med"
        return "Low"

    def _ease(driver: str) -> str:
        d = str(driver).lower()
        if "dar" in d:
            return "High (Automation)"
        if "idr" in d or "fwr" in d:
            return "Moderate"
        if "upr" in d:
            return "Low"
        return "Moderate"

    def _tier(corr: float) -> str:
        a = abs(corr)
        if a >= 0.35:
            return "Tier 1: Strategic Fix"
        if a >= 0.2:
            return "Tier 2: Efficiency Play"
        return "Tier 3: Monitor Only"

    rows = []
    for _, r in sens_df.iterrows():
        corr = float(r.get("corr", 0))
        driver = r.get("driver", "")
        rows.append({
            "Variable": board_ready_driver_label(driver),
            "Impact (Correlation)": f"{corr:.2f} ({_impact(corr)})",
            "Ease of Implementation": _ease(driver),
            "Strategic Designation": _tier(corr),
        })
    return pd.DataFrame(rows)


def actionable_insights(summary: pd.DataFrame, sensitivity: Optional[pd.DataFrame], ev_multiple: float = 8.0) -> List[str]:
    """Generate actionable, client-friendly insights with dollar context."""
    insights = []
    ebitda_mean = float(summary.loc["ebitda_drag", "mean"])
    ebitda_p10 = float(summary.loc["ebitda_drag", "p10"])
    ebitda_p90 = float(summary.loc["ebitda_drag", "p90"])
    econ_mean = float(summary.loc["economic_drag", "mean"])

    if ebitda_mean > 0:
        ev_mean = ebitda_mean * ev_multiple
        insights.append(
            f"Total recoverable opportunity: {pretty_money(ebitda_mean)} annual EBITDA "
            f"({pretty_money(ev_mean)} enterprise value at {ev_multiple}x). "
            f"Conservative floor: {pretty_money(ebitda_p10 * ev_multiple)} EV."
        )

    denial_woff = float(summary.loc["drag_denial_writeoff", "mean"])
    total = abs(ebitda_mean) or 1
    denial_pct = (denial_woff / total * 100) if total > 0 else 0
    if denial_woff > 0:
        insights.append(
            f"Denial write-offs account for {pretty_money(denial_woff)} "
            f"({denial_pct:.0f}% of total drag). "
            f"Reducing initial denial rates through better prior-auth capture and clinical documentation "
            f"is the highest-leverage intervention."
        )

    up_leak = float(summary.loc["drag_underpay_leakage", "mean"])
    if up_leak > 100_000:
        insights.append(
            f"Underpayment leakage of {pretty_money(up_leak)} annually indicates payers are paying "
            f"below contracted rates. A targeted contract management and payment variance audit "
            f"program can recover a significant portion of this."
        )

    if econ_mean > 200_000:
        insights.append(
            f"Slow collections create {pretty_money(econ_mean)} in annual working capital drag. "
            f"Accelerating clean-claim submission and automating A/R follow-up reduces the cash "
            f"trapped in receivables and lowers financing costs."
        )

    if ebitda_p90 > ebitda_mean * 1.3:
        gap = pretty_money(ebitda_p90 - ebitda_mean)
        insights.append(
            f"The stress case (P90) exceeds the expected case by {gap}, signaling meaningful tail risk. "
            f"Validate payer-specific denial trends and commercial contract stability before underwriting."
        )

    if sensitivity is not None and len(sensitivity) > 0:
        top = sensitivity.iloc[0]
        driver = top.get("driver_label", top.get("driver", ""))
        corr = float(top.get("corr", 0))
        if abs(corr) > 0.3 and driver:
            insights.append(
                f"Sensitivity analysis identifies {driver} as the single most influential input. "
                f"Securing accurate data for this variable should be the top diligence priority."
            )

    # Composition: rework vs leakage (actionable where appeals workload dominates)
    try:
        rework = float(summary.loc["drag_denial_rework_cost", "mean"]) + float(
            summary.loc["drag_underpay_cost", "mean"]
        )
        if ebitda_mean > 0 and rework / ebitda_mean >= 0.18:
            insights.append(
                f"Rework-related costs ({pretty_money(rework)}) are a material share of total drag. "
                f"Prioritize appeal staffing, routing rules, and root-cause fixes that reduce "
                f"re-submission cycles—not only front-end denial prevention."
            )
    except (KeyError, ZeroDivisionError):
        pass

    # Working-capital vs operational split
    if ebitda_mean > 0 and econ_mean > 200_000:
        wc_share = econ_mean / (ebitda_mean + econ_mean)
        if wc_share >= 0.12:
            insights.append(
                f"Working-capital drag is {wc_share:.0%} of combined RCM+WC friction in this run. "
                f"Cash acceleration (billing lag, discharge-to-bill, A/R follow-up) may be as urgent as denial reduction."
            )

    # Stability: narrow tail vs mean (lower scenario dispersion)
    if ebitda_mean > 0 and ebitda_p90 < ebitda_mean * 1.15:
        insights.append(
            "The P90 stress case is close to the mean—suggesting relatively modest upside tail risk in this "
            "parameterization. Still validate against payer-specific history before sizing downside."
        )

    return insights


from ..core.distributions import sample_dist


def assumption_summary(cfg: Dict[str, Any], n_draws: int = 5000, seed: int = 42) -> pd.DataFrame:
    """
    Generates a compact table of the *input* assumptions implied by the config, by sampling distributions.

    This is useful in diligence to:
      - confirm the model is using the intended ranges, and
      - document what was assumed when diligence data is incomplete.
    """
    rng = np.random.default_rng(int(seed))
    rows = []

    for payer, pconf in cfg["payers"].items():
        # Clean-claim A/R days
        dar = sample_dist(rng, pconf["dar_clean_days"], size=int(n_draws))
        rows.append({"payer": payer, "variable": "dar_clean_days", "mean": float(np.mean(dar)), "p10": float(np.quantile(dar, 0.10)), "p90": float(np.quantile(dar, 0.90))})

        if pconf.get("include_denials", False):
            idr = sample_dist(rng, pconf["denials"]["idr"], size=int(n_draws))
            fwr = sample_dist(rng, pconf["denials"]["fwr"], size=int(n_draws))
            rows.append({"payer": payer, "variable": "initial_denial_rate", "mean": float(np.mean(idr)), "p10": float(np.quantile(idr, 0.10)), "p90": float(np.quantile(idr, 0.90))})
            rows.append({"payer": payer, "variable": "final_writeoff_rate", "mean": float(np.mean(fwr)), "p10": float(np.quantile(fwr, 0.10)), "p90": float(np.quantile(fwr, 0.90))})

        if cfg.get("underpayments", {}).get("enabled", True) and pconf.get("include_underpayments", False):
            upr = sample_dist(rng, pconf["underpayments"]["upr"], size=int(n_draws))
            sev = sample_dist(rng, pconf["underpayments"]["severity"], size=int(n_draws))
            rec = sample_dist(rng, pconf["underpayments"]["recovery"], size=int(n_draws))
            rows.append({"payer": payer, "variable": "underpayment_rate", "mean": float(np.mean(upr)), "p10": float(np.quantile(upr, 0.10)), "p90": float(np.quantile(upr, 0.90))})
            rows.append({"payer": payer, "variable": "underpay_severity", "mean": float(np.mean(sev)), "p10": float(np.quantile(sev, 0.10)), "p90": float(np.quantile(sev, 0.90))})
            rows.append({"payer": payer, "variable": "underpay_recovery_rate", "mean": float(np.mean(rec)), "p10": float(np.quantile(rec, 0.10)), "p90": float(np.quantile(rec, 0.90))})

    # Global appeals assumptions (cost/days per stage)
    for stage, sconf in cfg["appeals"]["stages"].items():
        c = sample_dist(rng, sconf["cost"], size=int(n_draws))
        d = sample_dist(rng, sconf["days"], size=int(n_draws))
        rows.append({"payer": "ALL", "variable": f"appeal_cost_{stage}", "mean": float(np.mean(c)), "p10": float(np.quantile(c, 0.10)), "p90": float(np.quantile(c, 0.90))})
        rows.append({"payer": "ALL", "variable": f"appeal_days_{stage}", "mean": float(np.mean(d)), "p10": float(np.quantile(d, 0.10)), "p90": float(np.quantile(d, 0.90))})

    return pd.DataFrame(rows).sort_values(["payer", "variable"])
