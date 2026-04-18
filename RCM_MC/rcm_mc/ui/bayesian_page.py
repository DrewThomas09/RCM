"""SeekingChartis Bayesian Calibration page — per-hospital calibrated KPIs.

Shows the Bayesian posterior estimates for all RCM metrics, with
shrinkage visualization, credible intervals, and data quality scoring.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional

from ._chartis_kit import chartis_shell
from .brand import PALETTE


def render_bayesian_profile(
    ccn: str,
    hospital_name: str,
    beds: float,
    state: str,
    observed: Dict[str, Any],
) -> str:
    """Render Bayesian-calibrated KPI profile for a hospital."""
    from ..ml.bayesian_calibration import (
        calibrate_hospital_profile, compute_missing_data_score,
    )

    estimates = calibrate_hospital_profile(observed, beds=beds, state=state)
    data_score = compute_missing_data_score(observed)

    # ── Data Quality KPIs ──
    grade_color = {
        "A": "var(--cad-pos)", "B": "var(--cad-accent)",
        "C": "var(--cad-warn)", "D": "var(--cad-neg)",
    }.get(data_score["grade"], "var(--cad-text3)")

    kpis = (
        f'<div class="cad-kpi-grid">'
        f'<div class="cad-kpi"><div class="cad-kpi-value" style="color:{grade_color};">'
        f'{data_score["grade"]}</div>'
        f'<div class="cad-kpi-label">Data Quality Grade</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">'
        f'{data_score["completeness_pct"]:.0f}%</div>'
        f'<div class="cad-kpi-label">Completeness</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">'
        f'{data_score["present_count"]}/{data_score["total_metrics"]}</div>'
        f'<div class="cad-kpi-label">Metrics Provided</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">'
        f'{data_score["missing_count"]}</div>'
        f'<div class="cad-kpi-label">Missing (Imputed)</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">'
        f'{len(data_score["suspicious_values"])}</div>'
        f'<div class="cad-kpi-label">Suspicious Values</div></div>'
        f'</div>'
    )

    # ── Missing data warning ──
    missing_warning = ""
    if data_score["missing_is_informative"]:
        missing_list = ", ".join(m.replace("_", " ").title() for m in data_score["missing_metrics"][:6])
        missing_warning = (
            f'<div class="cad-card" style="border-left:3px solid var(--cad-warn);">'
            f'<h2 style="color:var(--cad-warn);">Missing Data is Informative</h2>'
            f'<p style="font-size:12px;color:var(--cad-text2);">'
            f'Over 30% of metrics are missing. In healthcare PE diligence, sellers who '
            f'don\'t provide denial/AR data often have worse-than-average performance. '
            f'Bayesian estimates below are shrunk toward peer priors — treat as '
            f'conservative baselines, not forecasts.</p>'
            f'<p style="font-size:11px;color:var(--cad-text3);margin-top:6px;">'
            f'Missing: {_html.escape(missing_list)}</p></div>'
        )

    if data_score["suspicious_values"]:
        susp_items = "".join(
            f'<li style="color:var(--cad-neg);">{_html.escape(s)}</li>'
            for s in data_score["suspicious_values"]
        )
        missing_warning += (
            f'<div class="cad-card" style="border-left:3px solid var(--cad-neg);">'
            f'<h2 style="color:var(--cad-neg);">Suspicious Values</h2>'
            f'<ul style="font-size:12px;padding-left:20px;">{susp_items}</ul></div>'
        )

    # ── Calibrated estimates table ──
    est_rows = ""
    for est in estimates:
        quality_badge = {
            "strong": ("var(--cad-pos)", "Strong"),
            "moderate": ("var(--cad-accent)", "Moderate"),
            "weak": ("var(--cad-warn)", "Weak"),
            "prior_only": ("var(--cad-neg)", "Prior Only"),
        }.get(est.data_quality, ("var(--cad-text3)", "Unknown"))

        shrink = est.shrinkage_factor
        shrink_color = "var(--cad-pos)" if shrink < 0.3 else (
            "var(--cad-warn)" if shrink < 0.7 else "var(--cad-neg)")

        # Shrinkage bar
        obs_pct = max(0, min(100, (1 - shrink) * 100))
        bar = (
            f'<div style="display:flex;height:8px;border-radius:3px;overflow:hidden;width:80px;">'
            f'<div style="width:{obs_pct:.0f}%;background:var(--cad-pos);"></div>'
            f'<div style="width:{100 - obs_pct:.0f}%;background:var(--cad-warn);"></div></div>'
        )

        is_rate = est.posterior_mean <= 1 and est.prior_mean <= 1
        fmt_fn = (lambda v: f"{v:.1%}") if is_rate else (lambda v: f"{v:.1f}")

        est_rows += (
            f'<tr>'
            f'<td style="font-weight:500;">'
            f'{_html.escape(est.metric.replace("_", " ").title())}</td>'
            f'<td class="num">{fmt_fn(est.prior_mean)}</td>'
            f'<td class="num">{fmt_fn(est.observed_mean) if est.observed_n > 0 else "—"}</td>'
            f'<td class="num" style="font-weight:600;">{fmt_fn(est.posterior_mean)}</td>'
            f'<td class="num" style="font-size:11px;">'
            f'[{fmt_fn(est.credible_interval_90[0])}, {fmt_fn(est.credible_interval_90[1])}]</td>'
            f'<td class="num" style="color:{shrink_color};">{shrink:.0%}</td>'
            f'<td>{bar}</td>'
            f'<td><span style="color:{quality_badge[0]};font-size:10px;font-weight:600;">'
            f'{quality_badge[1]}</span></td>'
            f'</tr>'
        )

    estimates_section = (
        f'<div class="cad-card">'
        f'<h2>Bayesian-Calibrated KPI Estimates</h2>'
        f'<p style="font-size:12px;color:var(--cad-text2);margin-bottom:10px;">'
        f'Each metric combines peer-group prior (from {beds:.0f}-bed hospital benchmarks) '
        f'with observed data. Shrinkage shows the weight given to prior vs observed: '
        f'0% = all data, 100% = all prior. Green bar = data weight, amber = prior weight.</p>'
        f'<table class="cad-table"><thead><tr>'
        f'<th>Metric</th><th>Prior</th><th>Observed</th><th>Posterior</th>'
        f'<th>90% CI</th><th>Shrinkage</th><th>Data vs Prior</th><th>Quality</th>'
        f'</tr></thead><tbody>{est_rows}</tbody></table></div>'
    )

    # ── Methodology note ──
    method = (
        f'<div class="cad-card" style="border-left:3px solid var(--cad-accent);">'
        f'<h2 style="font-size:13px;">Methodology: Hierarchical Bayesian Partial Pooling</h2>'
        f'<p style="font-size:12px;color:var(--cad-text2);line-height:1.7;">'
        f'Rate metrics (denial rate, collection rate, clean claim rate) use '
        f'<strong>Beta-Binomial</strong> conjugate updating. Continuous metrics (AR days, '
        f'cost to collect) use <strong>Gamma/Normal</strong> approximation. Priors are '
        f'stratified by hospital type (large/medium/small/rural). With zero observations, '
        f'the posterior equals the prior. As n increases, the posterior converges to the '
        f'observed value and the credible interval narrows. This prevents unstable estimates '
        f'from thin data while letting real evidence dominate.</p></div>'
    )

    # ── Actions ──
    actions = (
        f'<div class="cad-card" style="display:flex;gap:8px;flex-wrap:wrap;">'
        f'<a href="/hospital/{_html.escape(ccn)}" class="cad-btn cad-btn-primary" '
        f'style="text-decoration:none;">Hospital Profile</a>'
        f'<a href="/ml-insights/hospital/{_html.escape(ccn)}" class="cad-btn" '
        f'style="text-decoration:none;">ML Analysis</a>'
        f'<a href="/portfolio/regression/hospital/{_html.escape(ccn)}" class="cad-btn" '
        f'style="text-decoration:none;">Statistical Profile</a>'
        f'<a href="/quant-lab" class="cad-btn" style="text-decoration:none;">Quant Lab</a>'
        f'</div>'
    )

    body = f'{kpis}{missing_warning}{estimates_section}{method}{actions}'

    return chartis_shell(
        body,
        f"Bayesian Calibration — {_html.escape(hospital_name)}",
        subtitle=(
            f"CCN {_html.escape(ccn)} | Data quality: {data_score['grade']} "
            f"({data_score['completeness_pct']:.0f}% complete) | "
            f"{data_score['present_count']}/{data_score['total_metrics']} metrics"
        ),
    )
