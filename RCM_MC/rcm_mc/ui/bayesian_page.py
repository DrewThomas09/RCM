"""PE Desk Bayesian Calibration page — per-hospital calibrated KPIs.

Shows the Bayesian posterior estimates for all RCM metrics, with
shrinkage visualization, credible intervals, and data quality scoring.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional

from ._chartis_kit import (
    chartis_shell, ck_confidence_band, ck_fmt_num, ck_kpi_block,
    ck_next_section, ck_page_title, ck_provenance_tooltip,
)
from .brand import PALETTE

_EXPLAINER_CSS = """<style>
.ck-bay-explainer{font-family:var(--sc-serif,'Georgia',serif);
  font-size:15px;line-height:1.55;color:var(--sc-text-dim,#4a4a4a);
  margin:0 0 var(--sc-s-6,18px) 0;max-width:72ch;}
.ck-bay-explainer em{color:var(--sc-teal-ink,#155752);font-style:italic;}
</style>"""


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

    # Cycle 53 — port to ck_kpi_block + provenance.
    grade_value = ck_provenance_tooltip(
        "Data quality grade",
        f'<span style="color:{grade_color};">{data_score["grade"]}</span>',
        explainer=(
            f"A-D grade based on completeness ("
            f"{data_score['completeness_pct']:.0f}%) and presence "
            f"of suspicious values ({len(data_score['suspicious_values'])}). "
            f"Lower grades = more prior weight in the posteriors "
            f"below; the model leans on benchmarks when data is thin."
        ),
    )
    kpis = (
        '<div class="ck-kpi-grid">'
        + ck_kpi_block(
            "Data Quality Grade", grade_value, "blended posterior",
            help={
                "definition": (
                    "Composite A–F grade reflecting how confident the "
                    "Bayesian model is in this hospital's underlying "
                    "metrics, given completeness and outlier flags. "
                    "A = full data, no flags; D-F = heavy imputation "
                    "from priors so downstream numbers carry "
                    "explicit uncertainty bands."
                ),
            },
        )
        + ck_kpi_block(
            "Completeness", f"{data_score['completeness_pct']:.0f}%", "fields populated",
        )
        + ck_kpi_block(
            "Metrics Provided", f"{data_score['present_count']}/{data_score['total_metrics']}", "vs. expected",
        )
        + ck_kpi_block(
            "Missing (Imputed)", ck_fmt_num(data_score["missing_count"]), "from prior",
            help={
                "definition": (
                    "Fields the hospital didn't report; the model "
                    "fills them with the Bayesian prior — the "
                    "population-level expected value for hospitals of "
                    "this size/state/teaching status. More imputed "
                    "values = more reliance on priors over actuals."
                ),
            },
        )
        + ck_kpi_block(
            "Suspicious Values", ck_fmt_num(len(data_score["suspicious_values"])), "outliers flagged",
            help={
                "definition": (
                    "Reported values that fall outside the expected "
                    "range for peers (>3σ from the prior). Could be "
                    "true outliers, data-entry errors, or HCRIS lag "
                    "artifacts; partner should sanity-check each "
                    "before relying on downstream comparisons."
                ),
            },
        )
        + '</div>'
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

        # Phase A1: replace the bare [lo, hi] cell with the editorial
        # ck_confidence_band primitive so the posterior + band read as
        # one unit. ``prior_only`` quality means we're below the
        # threshold for trusting the observed data — band gets the
        # warning tone so partners see the soft-data signal.
        post_band = ck_confidence_band(
            fmt_fn(est.posterior_mean),
            fmt_fn(est.credible_interval_90[0]),
            fmt_fn(est.credible_interval_90[1]),
            label="90% CI",
            low_confidence=(est.data_quality in ("weak", "prior_only")),
        )
        est_rows += (
            f'<tr>'
            f'<td style="font-weight:500;">'
            f'{_html.escape(est.metric.replace("_", " ").title())}</td>'
            f'<td class="num">{fmt_fn(est.prior_mean)}</td>'
            f'<td class="num">{fmt_fn(est.observed_mean) if est.observed_n > 0 else "—"}</td>'
            f'<td class="num" style="font-weight:600;">{post_band}</td>'
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
        f'<th>Metric</th><th>Prior</th><th>Observed</th>'
        f'<th>Posterior [90% CI]</th>'
        f'<th>Shrinkage</th><th>Data vs Prior</th><th>Quality</th>'
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

    next_up = ck_next_section(
        "Open the hospital profile",
        f"/hospital/{_html.escape(ccn)}",
        eyebrow="Continue —",
        italic_word="profile",
    )
    page_title = ck_page_title(
        "Bayesian Calibration",
        eyebrow=f"BAYESIAN CALIBRATION · CCN {_html.escape(ccn)}",
        meta=(
            f"Data quality: {data_score['grade']} "
            f"({data_score['completeness_pct']:.0f}% complete) · "
            f"{data_score['present_count']}/{data_score['total_metrics']} metrics"
        ),
    )
    explainer_html = (
        '<p class="ck-bay-explainer">'
        f'<em>{_html.escape(hospital_name)}.</em> '
        "Per-metric Bayesian posteriors blending sector "
        "prior + this hospital's signal. Lower data quality "
        "means tighter prior weight; higher data quality "
        "shifts toward the observed value. Use this to "
        "see what the platform knows vs. is inferring."
        '</p>'
    )
    body = f'{page_title}{explainer_html}{kpis}{missing_warning}{estimates_section}{method}{actions}{next_up}'

    return chartis_shell(
        body,
        f"Bayesian Calibration — {_html.escape(hospital_name)}",
        extra_css=_EXPLAINER_CSS,
    )
