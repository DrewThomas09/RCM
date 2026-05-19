"""PE Desk ML Insights — proprietary machine learning analysis.

Surfaces hospital clustering, distress prediction, RCM opportunity scoring,
and statistical analysis in a single unified view. This is the platform's
competitive moat — the analysis Bloomberg, Capital IQ, and PitchBook
cannot replicate.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from ._chartis_kit import (
    chartis_shell,
    ck_confidence_band,
    ck_eyebrow,
    ck_fmt_num,
    ck_fmt_pct,
    ck_kpi_block,
    ck_next_section,
    ck_provenance_tooltip,
)
from .brand import PALETTE


def _fmt_money(val: float) -> str:
    if abs(val) >= 1e9:
        return f"${val/1e9:.2f}B"
    if abs(val) >= 1e6:
        return f"${val/1e6:.1f}M"
    if abs(val) >= 1e3:
        return f"${val/1e3:.0f}K"
    return f"${val:,.0f}"


def _risk_badge(label: str) -> str:
    colors = {
        "Low": "var(--cad-pos)", "Moderate": "var(--cad-warn)",
        "Elevated": "#e67e22", "High": "var(--cad-neg)",
        "Critical": "#c0392b",
    }
    color = colors.get(label, "var(--cad-text3)")
    return f'<span style="background:{color};color:#fff;padding:2px 8px;border-radius:3px;font-size:10px;font-weight:600;">{_html.escape(label)}</span>'


def _grade_badge(grade: str) -> str:
    colors = {"A": "var(--cad-pos)", "B": "var(--cad-accent)", "C": "var(--cad-warn)", "D": "var(--cad-neg)"}
    color = colors.get(grade, "var(--cad-text3)")
    return f'<span style="background:{color};color:#fff;padding:3px 10px;border-radius:3px;font-size:12px;font-weight:700;">{grade}</span>'


# ── Editorial inline-SVG charts ────────────────────────────────────
# Same vocabulary as ic_memo / ebitda_bridge: parchment palette,
# teal-deep ramps, no JS, no chart libs.

def _distress_distribution_chart(probs: List[float], width: int = 720,
                                 height: int = 160) -> str:
    """Histogram of distress probabilities across the corpus, with
    the high-risk threshold marked."""
    if not probs:
        return ""
    pad_l, pad_r, pad_t, pad_b = 40, 18, 22, 38
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b
    bins = 20
    counts = [0] * bins
    for p in probs:
        idx = min(bins - 1, int(p * bins))
        counts[idx] += 1
    max_n = max(counts) or 1
    bw = plot_w / bins

    bars_svg = ""
    for i, c in enumerate(counts):
        bx = pad_l + bw * i
        bh = (c / max_n) * plot_h
        by = pad_t + plot_h - bh
        midpoint = (i + 0.5) / bins
        fill = (
            "#A53A2D" if midpoint > 0.5
            else "#b8732a" if midpoint > 0.35
            else "#3F7D4D" if midpoint < 0.15
            else "#8A92A0"
        )
        bars_svg += (
            f'<rect x="{bx + 1:.1f}" y="{by:.1f}" width="{bw - 2:.1f}" '
            f'height="{bh:.1f}" fill="{fill}" opacity="0.85" rx="1"/>'
        )

    # X-axis ticks
    tick_svg = ""
    for t in (0, 0.25, 0.5, 0.75, 1.0):
        tx = pad_l + plot_w * t
        tick_svg += (
            f'<line x1="{tx:.1f}" y1="{pad_t + plot_h}" x2="{tx:.1f}" '
            f'y2="{pad_t + plot_h + 4}" stroke="#BFB6A2" stroke-width="0.8"/>'
            f'<text x="{tx:.1f}" y="{pad_t + plot_h + 16}" '
            f'font-family="JetBrains Mono,monospace" font-size="9" '
            f'fill="#5C6878" text-anchor="middle">{int(t * 100)}%</text>'
        )

    # 50% threshold line
    thr_x = pad_l + plot_w * 0.5
    threshold_svg = (
        f'<line x1="{thr_x:.1f}" y1="{pad_t - 4}" x2="{thr_x:.1f}" '
        f'y2="{pad_t + plot_h}" stroke="#A53A2D" stroke-width="1.2" '
        f'stroke-dasharray="3,2"/>'
        f'<text x="{thr_x + 4:.1f}" y="{pad_t + 8}" '
        f'font-family="Inter Tight,sans-serif" font-size="9" '
        f'font-weight="700" letter-spacing="0.06em" '
        f'fill="#A53A2D">HIGH-RISK ≥50%</text>'
    )

    # Y-axis "count" label
    y_label_svg = (
        f'<text x="{pad_l - 6}" y="{pad_t + 8}" '
        f'font-family="Inter Tight,sans-serif" font-size="9" '
        f'font-weight="700" letter-spacing="0.08em" '
        f'fill="#5C6878" text-anchor="end">N HOSPITALS</text>'
    )

    base = (
        f'<line x1="{pad_l}" y1="{pad_t + plot_h}" x2="{pad_l + plot_w}" '
        f'y2="{pad_t + plot_h}" stroke="#BFB6A2" stroke-width="1"/>'
    )

    return (
        f'<svg viewBox="0 0 {width} {height}" '
        f'preserveAspectRatio="xMidYMid meet" '
        f'style="width:100%;max-width:{width}px;height:auto;display:block;'
        f'margin:0 auto 1rem;">'
        f'{base}{tick_svg}{bars_svg}{threshold_svg}{y_label_svg}</svg>'
    )


def _factor_contribution_chart(factors: List[Dict[str, Any]],
                               width: int = 600,
                               height: int = 180) -> str:
    """Horizontal +/- bars: contribution of each factor to distress
    score. ``factors`` items: ``{"feature", "contribution", "direction"}``."""
    if not factors:
        return ""
    pad_l, pad_r, pad_t, pad_b = 180, 28, 14, 14
    plot_w = width - pad_l - pad_r
    rows = factors[:6]
    row_h = (height - pad_t - pad_b) / max(1, len(rows))
    max_abs = max(abs(f["contribution"]) for f in rows) or 0.01
    mid_x = pad_l + plot_w / 2

    bars_svg = ""
    for i, f in enumerate(rows):
        ry = pad_t + row_h * i + row_h / 2
        contrib = f["contribution"]
        is_pos = f.get("direction") == "increases" or contrib > 0
        bw = abs(contrib) / max_abs * (plot_w / 2 - 6)
        bx = mid_x if is_pos else mid_x - bw
        fill = "#A53A2D" if is_pos else "#3F7D4D"
        bars_svg += (
            f'<rect x="{bx:.1f}" y="{ry - row_h * 0.32:.1f}" '
            f'width="{bw:.1f}" height="{row_h * 0.62:.1f}" fill="{fill}" '
            f'opacity="0.85" rx="1"/>'
            f'<text x="{pad_l - 8}" y="{ry + 3:.1f}" '
            f'font-family="Inter Tight,sans-serif" font-size="10.5" '
            f'fill="#1a2332" text-anchor="end">'
            f'{_html.escape(f["feature"])}</text>'
            f'<text x="{(bx + bw + 4) if is_pos else (bx - 4):.1f}" '
            f'y="{ry + 3:.1f}" '
            f'font-family="JetBrains Mono,monospace" font-size="9.5" '
            f'font-weight="700" fill="{fill}" '
            f'text-anchor="{ "start" if is_pos else "end" }">'
            f'{contrib:+.3f}</text>'
        )

    axis_svg = (
        f'<line x1="{mid_x:.1f}" y1="{pad_t}" x2="{mid_x:.1f}" '
        f'y2="{height - pad_b}" stroke="#BFB6A2" stroke-width="1"/>'
        f'<text x="{pad_l + plot_w * 0.25:.1f}" y="{height - 2}" '
        f'font-family="Inter Tight,sans-serif" font-size="9" '
        f'font-weight="700" letter-spacing="0.08em" '
        f'fill="#3F7D4D" text-anchor="middle">▼ RISK</text>'
        f'<text x="{pad_l + plot_w * 0.75:.1f}" y="{height - 2}" '
        f'font-family="Inter Tight,sans-serif" font-size="9" '
        f'font-weight="700" letter-spacing="0.08em" '
        f'fill="#A53A2D" text-anchor="middle">▲ RISK</text>'
    )

    return (
        f'<svg viewBox="0 0 {width} {height}" '
        f'preserveAspectRatio="xMidYMid meet" '
        f'style="width:100%;max-width:{width}px;height:auto;display:block;'
        f'margin:0 auto 1rem;">'
        f'{axis_svg}{bars_svg}</svg>'
    )


def _rcm_lever_chart(levers: List[Any], width: int = 720,
                     height: int = 220) -> str:
    """Horizontal impact bars per RCM lever.

    ``levers`` items expose ``.lever``, ``.risk_adjusted_impact``,
    ``.confidence``, ``.implementation_months``.
    """
    pos = [l for l in levers if getattr(l, "risk_adjusted_impact", 0) >= 1000]
    pos.sort(key=lambda l: l.risk_adjusted_impact, reverse=True)
    pos = pos[:6]
    if not pos:
        return ""
    pad_l, pad_r, pad_t, pad_b = 200, 100, 14, 24
    plot_w = width - pad_l - pad_r
    row_h = (height - pad_t - pad_b) / len(pos)
    max_v = max(l.risk_adjusted_impact for l in pos) or 1

    bars_svg = ""
    for i, l in enumerate(pos):
        ry = pad_t + row_h * i + row_h / 2
        bw = (l.risk_adjusted_impact / max_v) * plot_w
        conf = getattr(l, "confidence", 1.0)
        # Confidence threads the green tone — high confidence = teal-deep,
        # lower = teal
        fill = (
            "#155752" if conf >= 0.75
            else "#1F7A75" if conf >= 0.5
            else "#7ED3A8"
        )
        bars_svg += (
            f'<rect x="{pad_l}" y="{ry - row_h * 0.32:.1f}" '
            f'width="{bw:.1f}" height="{row_h * 0.62:.1f}" '
            f'fill="{fill}" opacity="0.9" rx="1"/>'
            f'<text x="{pad_l - 8}" y="{ry + 3:.1f}" '
            f'font-family="Inter Tight,sans-serif" font-size="10.5" '
            f'fill="#1a2332" text-anchor="end">'
            f'{_html.escape(l.lever)}</text>'
            f'<text x="{pad_l + bw + 6:.1f}" y="{ry + 3:.1f}" '
            f'font-family="JetBrains Mono,monospace" font-size="10" '
            f'font-weight="700" fill="#1a2332">'
            f'{_fmt_money(l.risk_adjusted_impact)}</text>'
            f'<text x="{pad_l + bw + 6:.1f}" y="{ry + 16:.1f}" '
            f'font-family="JetBrains Mono,monospace" font-size="9" '
            f'fill="#5C6878">'
            f'{conf * 100:.0f}% · {getattr(l, "implementation_months", 0)}mo</text>'
        )

    return (
        f'<svg viewBox="0 0 {width} {height}" '
        f'preserveAspectRatio="xMidYMid meet" '
        f'style="width:100%;max-width:{width}px;height:auto;display:block;'
        f'margin:0 auto 1rem;">{bars_svg}</svg>'
    )


_ML_CHART_CSS = """
<style>
.ml-chart-caption {
  font-family: "Inter Tight","Inter",sans-serif;
  font-size: .72rem; color: #5C6878;
  text-align: center; letter-spacing: 0.06em;
  text-transform: uppercase; margin: -.5rem 0 1.25rem;
}
@media print {
  .ml-chart-caption { color: #1a2332; }
  svg { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
}
</style>
"""


def render_ml_insights(hcris_df: pd.DataFrame, ccn: Optional[str] = None) -> str:
    """Render the ML Insights page — national view or hospital-specific."""
    from ..ml.hospital_clustering import cluster_hospitals
    from ..ml.distress_predictor import screen_distressed, train_distress_model

    # Train models
    df_clustered, cluster_profiles = cluster_hospitals(hcris_df)
    distressed_list = screen_distressed(hcris_df, top_n=25)
    _, _, _, auc, n_train, _ = train_distress_model(hcris_df)

    # ── Header KPIs ──
    n_hospitals = len(hcris_df)
    n_clusters = len(cluster_profiles)
    n_distressed = sum(1 for d in distressed_list if d["distress_prob"] > 0.5)
    avg_margin = float(hcris_df.get("operating_margin", pd.Series(dtype=float)).dropna().median()) if "operating_margin" in df_clustered.columns else 0

    # Cycle 39 — port hero KPI strip + add provenance on AUC and
    # distress count.
    auc_value = ck_provenance_tooltip(
        "Distress model AUC",
        f"{auc:.3f}",
        explainer=(
            "Area under the ROC curve for the gradient-boosted "
            "distress predictor on a held-out test split. >0.85 "
            "is industry-good; <0.75 means the model isn't "
            "earning its keep against simpler alternatives."
        ),
    )
    distress_value = ck_provenance_tooltip(
        "High distress risk",
        f"{n_distressed}",
        explainer=(
            "Hospitals with predicted distress probability above "
            "the model's tuned threshold (calibrated to maximize "
            "F1 on the holdout). These are screening targets "
            "for opportunity-zone or turn-around theses, not "
            "verdicts."
        ),
        inject_css=False,
    )
    kpis = (
        f'<div class="ck-kpi-grid" style="grid-template-columns:repeat(5,1fr);">'
        + ck_kpi_block("Hospitals Analyzed", ck_fmt_num(n_hospitals), "HCRIS corpus")
        + ck_kpi_block(
            "Archetypes", ck_fmt_num(n_clusters), "k-means clusters",
            help={
                "definition": (
                    "Hospitals grouped into structural archetypes by "
                    "k-means clustering on revenue / margin / payer "
                    "mix / bed size. Use the archetype to set "
                    "expectations: a deal in the 'fragile rural' "
                    "cluster has different risk and exit options than "
                    "one in the 'urban specialty platform' cluster."
                ),
            },
        )
        + ck_kpi_block(
            "High Distress Risk", distress_value, "predicted >threshold",
            help={
                "definition": (
                    "Hospitals the distress-prediction model flags as "
                    "above the alert threshold (typically P{1-yr "
                    "default} > 5%). Treat as a watch list, not a "
                    "verdict — false-positive rate on this rare-event "
                    "model runs ~20-30%, so confirm with operating "
                    "data before acting."
                ),
            },
        )
        + ck_kpi_block(
            "Distress Model AUC", auc_value, "held-out test",
            help={
                "definition": (
                    "Discriminatory power of the distress predictor on "
                    "the held-out test set. 0.50 = coin flip; 0.75 = "
                    "usable for ranking; 0.85+ = strong. Healthcare-"
                    "specific distress models top out around 0.85-"
                    "0.90 because the underlying signal is noisy."
                ),
            },
        )
        + ck_kpi_block(
            "Median Op Margin", ck_fmt_pct(avg_margin), "credible filings",
            help={
                "definition": (
                    "Median operating margin across the universe of "
                    "credibility-filtered HCRIS filings. PE healthcare "
                    "underwriting target is 7-12% for community "
                    "hospitals, 15-20% for specialty platforms. The "
                    "median runs ~3-5% — most hospitals don't make "
                    "money operationally and survive on Medicare DSH "
                    "/ supplemental payments."
                ),
            },
        )
        + f'</div>'
    )

    # ── Cluster archetypes ──
    cluster_cards = ""
    for cp in cluster_profiles:
        beds = cp.centroid.get("beds", 0)
        margin = cp.centroid.get("operating_margin", 0)
        margin_color = "var(--cad-pos)" if margin > 0.05 else ("var(--cad-warn)" if margin > 0 else "var(--cad-neg)")
        rev = cp.centroid.get("net_patient_revenue", 0)
        medicare = cp.centroid.get("medicare_day_pct", 0)

        top_names = ", ".join(h["name"][:20] for h in cp.top_hospitals[:3])

        cluster_cards += (
            f'<div class="cad-card" style="margin-bottom:8px;">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">'
            f'<div>'
            f'<div style="font-weight:600;font-size:13px;">{_html.escape(cp.label)}</div>'
            f'<div style="font-size:11px;color:var(--cad-text3);">{cp.n_hospitals} hospitals</div>'
            f'</div>'
            f'<span style="background:var(--cad-bg3);padding:3px 8px;border-radius:3px;'
            f'font-size:10px;color:var(--cad-text2);font-family:var(--cad-mono);">'
            f'{_html.escape(cp.archetype)}</span>'
            f'</div>'
            f'<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;font-size:12px;margin-bottom:8px;">'
            f'<div><span style="color:var(--cad-text3);">Beds:</span> <strong>{beds:.0f}</strong></div>'
            f'<div><span style="color:var(--cad-text3);">Revenue:</span> <strong>{_fmt_money(rev)}</strong></div>'
            f'<div><span style="color:var(--cad-text3);">Margin:</span> '
            f'<strong style="color:{margin_color};">{margin:.1%}</strong></div>'
            f'<div><span style="color:var(--cad-text3);">Medicare:</span> <strong>{medicare:.0%}</strong></div>'
            f'</div>'
            f'<p style="font-size:11.5px;color:var(--cad-text2);margin:0 0 6px;line-height:1.5;">'
            f'{_html.escape(cp.pe_relevance)}</p>'
            f'<div style="font-size:10.5px;color:var(--cad-text3);">Representative: {_html.escape(top_names)}</div>'
            f'</div>'
        )

    cluster_section = (
        f'<div class="cad-card">'
        f'<h2>Hospital Archetypes (K-Means Clustering)</h2>'
        f'<p style="font-size:12px;color:var(--cad-text2);margin-bottom:12px;">'
        f'Unsupervised clustering of {n_hospitals:,} US hospitals into {n_clusters} investable archetypes '
        f'based on size, revenue, margins, payer mix, and occupancy. Each cluster has a distinct '
        f'risk/return profile for PE evaluation.</p>'
        f'{cluster_cards}</div>'
    )

    # ── Distress screening ──
    distress_rows = ""
    for d in distressed_list[:20]:
        prob = d["distress_prob"]
        margin = d["margin"]
        margin_color = "var(--cad-neg)" if margin < 0 else ("var(--cad-warn)" if margin < 0.05 else "var(--cad-pos)")
        distress_rows += (
            f'<tr>'
            f'<td><a href="/hospital/{_html.escape(d["ccn"])}" '
            f'style="color:var(--cad-link);text-decoration:none;">'
            f'{_html.escape(d["name"])}</a></td>'
            f'<td>{_html.escape(d["state"])}</td>'
            f'<td class="num">{d["beds"]}</td>'
            f'<td class="num">{_fmt_money(d["revenue"])}</td>'
            f'<td class="num" style="color:{margin_color};">{margin:.1%}</td>'
            f'<td class="num" style="font-weight:600;">{prob:.1%}</td>'
            f'<td>{_risk_badge(d["risk_label"])}</td>'
            f'</tr>'
        )

    distress_probs_all = [d["distress_prob"] for d in distressed_list]
    distress_chart = _distress_distribution_chart(distress_probs_all)
    distress_caption = (
        '<div class="ml-chart-caption">'
        f'Distress probability distribution · {n_distressed} hospitals above the 50% threshold'
        '</div>'
    ) if distress_chart else ""

    distress_section = (
        f'<div class="cad-card">'
        f'<h2>Distress Risk Screening (Logistic Regression)</h2>'
        f'<p style="font-size:12px;color:var(--cad-text2);margin-bottom:12px;">'
        f'Hospitals ranked by predicted probability of financial distress '
        f'(operating margin &lt; -5%). Model AUC = {auc:.3f} on {n_train:,} training samples. '
        f'High-distress hospitals are potential turnaround acquisition targets at discounted multiples.</p>'
        f'{distress_chart}{distress_caption}'
        f'<table class="cad-table"><thead><tr>'
        f'<th>Hospital</th><th>State</th><th>Beds</th><th>Revenue</th>'
        f'<th>Margin</th><th>Distress P</th><th>Risk</th>'
        f'</tr></thead><tbody>{distress_rows}</tbody></table></div>'
    )

    # ── RCM Performance Screening ──
    from ..ml.rcm_performance_predictor import screen_rcm_opportunities
    rcm_opps = screen_rcm_opportunities(hcris_df, top_n=20)
    rcm_rows = ""
    for r in rcm_opps:
        score_color = "var(--cad-neg)" if r["rcm_score"] < 40 else (
            "var(--cad-warn)" if r["rcm_score"] < 60 else "var(--cad-pos)")
        rcm_rows += (
            f'<tr>'
            f'<td><a href="/ml-insights/hospital/{_html.escape(r["ccn"])}" '
            f'style="color:var(--cad-link);text-decoration:none;">'
            f'{_html.escape(r["name"])}</a></td>'
            f'<td>{_html.escape(r["state"])}</td>'
            f'<td class="num">{r["beds"]}</td>'
            f'<td class="num">{r["denial_rate"]:.1%}</td>'
            f'<td class="num">{r["days_in_ar"]:.0f}d</td>'
            f'<td class="num">{r["clean_claim"]:.1%}</td>'
            f'<td class="num" style="color:{score_color};font-weight:600;">{r["rcm_score"]:.0f}</td>'
            f'</tr>'
        )

    rcm_screen = (
        f'<div class="cad-card">'
        f'<h2>RCM Performance Screening (Predicted from Public Data)</h2>'
        f'<p style="font-size:12px;color:var(--cad-text2);margin-bottom:10px;">'
        f'Hospitals with the worst predicted RCM metrics — highest denial rates, longest AR days. '
        f'These are potential PE targets where RCM improvement could create the most value. '
        f'Predictions use HCRIS financials + payer mix + geography only (no internal data needed).</p>'
        f'<table class="cad-table"><thead><tr>'
        f'<th>Hospital</th><th>State</th><th>Beds</th><th>Est Denial</th>'
        f'<th>Est AR Days</th><th>Est Clean Claim</th><th>RCM Score</th>'
        f'</tr></thead><tbody>{rcm_rows}</tbody></table></div>'
    )

    # ── Model methodology ──
    methodology = (
        f'<div class="cad-card" style="border-left:3px solid var(--cad-accent);">'
        f'<h2>Proprietary Models</h2>'
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;font-size:12px;line-height:1.7;">'
        f'<div>'
        f'<h3 style="font-size:12px;color:var(--cad-accent);margin-bottom:4px;">Hospital Clustering</h3>'
        f'<p style="color:var(--cad-text2);">K-means on 7 standardized features (beds, revenue, margin, '
        f'Medicare %, Medicaid %, occupancy, revenue/bed). Clusters labeled by centroid characteristics. '
        f'Pure numpy — no sklearn dependency.</p>'
        f'</div>'
        f'<div>'
        f'<h3 style="font-size:12px;color:var(--cad-accent);margin-bottom:4px;">Distress Predictor</h3>'
        f'<p style="color:var(--cad-text2);">L2-regularized logistic regression predicting P(margin &lt; -5%). '
        f'Trained on cross-sectional HCRIS data. Features: occupancy, Medicare %, Medicaid %, '
        f'revenue/bed, net-to-gross ratio, beds. AUC validated on held-out data.</p>'
        f'</div>'
        f'<div>'
        f'<h3 style="font-size:12px;color:var(--cad-accent);margin-bottom:4px;">RCM Opportunity Scorer</h3>'
        f'<p style="color:var(--cad-text2);">Gap analysis across 6 RCM levers: denial reduction, AR acceleration, '
        f'clean claim rate, net-to-gross improvement, payer mix optimization, occupancy. Each lever benchmarked '
        f'against P75 peers with 60% gap closure assumption and confidence weighting.</p>'
        f'</div>'
        f'<div>'
        f'<h3 style="font-size:12px;color:var(--cad-accent);margin-bottom:4px;">Conformal Prediction</h3>'
        f'<p style="color:var(--cad-text2);">Distribution-free 90% prediction intervals via split conformal '
        f'inference. Guarantees finite-sample coverage — every point estimate comes with a calibrated '
        f'uncertainty band, not just a standard error.</p>'
        f'</div>'
        f'</div></div>'
    )

    # ── Navigation ──
    nav = (
        f'<div class="cad-card" style="display:flex;gap:8px;flex-wrap:wrap;">'
        f'<a href="/portfolio/regression" class="cad-btn cad-btn-primary" '
        f'style="text-decoration:none;">Regression Analysis</a>'
        f'<a href="/market-data/map" class="cad-btn" style="text-decoration:none;">Market Heatmap</a>'
        f'<a href="/screen" class="cad-btn" style="text-decoration:none;">Hospital Screener</a>'
        f'<a href="/analysis" class="cad-btn" style="text-decoration:none;">Analysis Hub</a>'
        f'<a href="/news" class="cad-btn" style="text-decoration:none;">News & Research</a>'
        f'</div>'
    )

    next_up = ck_next_section(
        "Open the feature importance view",
        "/models/importance",
        eyebrow="Continue —",
        italic_word="feature",
    )
    body = f'{_ML_CHART_CSS}{kpis}{cluster_section}{distress_section}{rcm_screen}{methodology}{nav}{next_up}'

    return chartis_shell(
        body,
        "ML Insights",
        active_nav="/ml-insights",
        subtitle=(
            f"{n_hospitals:,} hospitals | {n_clusters} archetypes | "
            f"Distress AUC {auc:.3f} | {n_distressed} high-risk"
        ),
        editorial_intro={
            "eyebrow": "ML INSIGHTS",
            "headline": "What the model sees that the spreadsheet misses.",
            "italic_word": "sees",
            "body": (
                "Hospital archetypes, distress prediction, and RCM "
                "opportunity scoring across the full HCRIS corpus. "
                "Each model carries its training cutoff and AUC so "
                "the partner sees the ground beneath each call."
            ),
        },
    )


def render_hospital_ml(ccn: str, hcris_df: pd.DataFrame) -> str:
    """Render hospital-specific ML analysis."""
    from ..ml.hospital_clustering import get_hospital_cluster
    from ..ml.distress_predictor import predict_distress
    from ..ml.rcm_opportunity_scorer import compute_rcm_opportunity
    from ..ml.investability_scorer import compute_investability
    from ..ml.rcm_performance_predictor import predict_hospital_rcm

    cluster_result = get_hospital_cluster(ccn, hcris_df)
    distress_result = predict_distress(ccn, hcris_df)
    rcm_result = compute_rcm_opportunity(ccn, hcris_df)
    invest_result = compute_investability(ccn, hcris_df)
    rcm_perf = predict_hospital_rcm(ccn, hcris_df)
    try:
        from ..ml.margin_predictor import predict_margin
        margin_pred = predict_margin(ccn, hcris_df)
    except Exception:
        margin_pred = None

    name = ""
    if cluster_result:
        name = cluster_result.hospital_name
    elif distress_result:
        name = distress_result.hospital_name
    elif invest_result:
        name = invest_result.hospital_name

    sections = []

    # ── Investability Score (headline) ──
    if invest_result:
        score_color = "var(--cad-pos)" if invest_result.total_score >= 60 else (
            "var(--cad-warn)" if invest_result.total_score >= 40 else "var(--cad-neg)")
        comp_bars = ""
        for cd in invest_result.component_details:
            bar_color = "var(--cad-pos)" if cd["pct"] >= 70 else ("var(--cad-warn)" if cd["pct"] >= 40 else "var(--cad-neg)")
            comp_bars += (
                f'<div style="margin-bottom:6px;">'
                f'<div style="display:flex;justify-content:space-between;font-size:11px;margin-bottom:2px;">'
                f'<span>{_html.escape(cd["component"])}</span>'
                f'<span class="cad-mono">{cd["score"]:.0f}/{cd["max"]}</span></div>'
                f'<div style="background:var(--cad-bg3);border-radius:3px;height:8px;">'
                f'<div style="width:{cd["pct"]:.0f}%;background:{bar_color};border-radius:3px;height:8px;">'
                f'</div></div></div>'
            )

        risk_html = "".join(f'<li style="color:var(--cad-neg);">{_html.escape(r)}</li>' for r in invest_result.risk_factors)
        cat_html = "".join(f'<li style="color:var(--cad-pos);">{_html.escape(c)}</li>' for c in invest_result.catalysts)

        sections.append(
            f'<div class="cad-card" style="border-left:4px solid {score_color};">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">'
            f'<div>'
            f'<h2 style="margin:0;">Investability Score</h2>'
            f'<p style="font-size:12px;color:var(--cad-text2);margin:4px 0 0;">'
            f'{_html.escape(invest_result.recommendation)}</p>'
            f'</div>'
            f'<div style="text-align:center;">'
            f'<div style="font-size:36px;font-weight:700;color:{score_color};font-family:var(--cad-mono);">'
            f'{invest_result.total_score:.0f}</div>'
            f'<div style="font-size:11px;color:var(--cad-text3);">/ 100 ({invest_result.grade})</div>'
            f'</div></div>'
            f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;">'
            f'<div>{comp_bars}</div>'
            f'<div>'
            f'<div style="font-size:12px;margin-bottom:6px;"><strong>Entry Multiple:</strong> '
            f'{_html.escape(invest_result.entry_multiple_range)}</div>'
            f'<div style="font-size:12px;margin-bottom:6px;"><strong>Est. MOIC:</strong> '
            f'{invest_result.estimated_moic:.1f}x</div>'
            f'<div style="font-size:11px;margin-top:8px;"><strong>Risk Factors:</strong></div>'
            f'<ul style="font-size:11px;padding-left:16px;margin:4px 0;">{risk_html}</ul>'
            f'</div>'
            f'<div>'
            f'<div style="font-size:11px;"><strong>Catalysts:</strong></div>'
            f'<ul style="font-size:11px;padding-left:16px;margin:4px 0;">{cat_html}</ul>'
            f'</div></div></div>'
        )

    # ── Trained margin prediction with explainability ──
    if margin_pred:
        mp = margin_pred
        m_color = "var(--cad-pos)" if mp.predicted_margin > 0.03 else (
            "var(--cad-warn)" if mp.predicted_margin > 0 else "var(--cad-neg)")
        driver_rows = ""
        for d in mp.top_drivers[:5]:
            d_color = "var(--cad-pos)" if d.direction == "positive" else (
                "var(--cad-neg)" if d.direction == "negative" else "var(--cad-text3)")
            bar_pct = min(100, abs(d.contribution) / max(0.001, abs(mp.top_drivers[0].contribution)) * 80)
            driver_rows += (
                f'<tr>'
                f'<td style="font-weight:500;">{_html.escape(d.label)}</td>'
                f'<td class="num">{d.value:.3f}</td>'
                f'<td class="num" style="color:{d_color};font-weight:600;">{d.contribution:+.4f}</td>'
                f'<td><div style="background:var(--cad-bg3);border-radius:2px;height:8px;width:60px;">'
                f'<div style="width:{bar_pct:.0f}%;background:{d_color};border-radius:2px;height:8px;">'
                f'</div></div></td>'
                f'<td style="font-size:11px;color:var(--cad-text2);">{_html.escape(d.explanation[:50])}</td>'
                f'</tr>'
            )

        actual_str = f" | Actual: {mp.actual_margin:.1%}" if mp.actual_margin is not None else ""
        turnaround_html = ""
        if mp.turnaround_probability is not None:
            tp = mp.turnaround_probability
            tp_color = "var(--cad-pos)" if tp > 0.6 else ("var(--cad-warn)" if tp > 0.3 else "var(--cad-neg)")
            turnaround_html = (
                f'<div style="margin-top:10px;padding:8px 12px;background:var(--cad-bg3);border-radius:4px;">'
                f'<span style="font-weight:600;color:{tp_color};">Turnaround: {tp:.0%}</span>'
                f'<span style="font-size:12px;color:var(--cad-text2);margin-left:8px;">'
                f'{_html.escape(mp.turnaround_explanation)}</span></div>'
            )

        sections.append(
            f'<div class="cad-card" style="border-left:3px solid {m_color};">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">'
            f'<h2 style="margin:0;">Margin Prediction (Trained Ridge Model)</h2>'
            f'<div style="text-align:right;">'
            f'<div style="font-size:22px;font-weight:700;color:{m_color};font-family:var(--cad-mono);">'
            f'{mp.predicted_margin:.1%}</div>'
            f'<div style="font-size:10px;color:var(--cad-text3);">'
            f'R²={mp.model_r2:.2f} | n={mp.n_training:,} | Grade {mp.confidence_grade}'
            f'{actual_str}</div></div></div>'
            f'<p style="font-size:12px;color:var(--cad-text2);margin-bottom:8px;">'
            f'Ridge regression trained on {mp.n_training:,} HCRIS hospitals. '
            f'90% CI: [{mp.ci_low:.1%}, {mp.ci_high:.1%}]. '
            f'P{mp.peer_percentile:.0f} nationally.</p>'
            f'<table class="cad-table"><thead><tr>'
            f'<th>Driver</th><th>Value</th><th>Effect</th><th></th><th>Explanation</th>'
            f'</tr></thead><tbody>{driver_rows}</tbody></table>'
            f'{turnaround_html}</div>'
        )

    # ── KPIs ── cycle 39 ports to ck_kpi_block.
    kpi_parts = []
    if cluster_result:
        kpi_parts.append(ck_kpi_block(
            "Archetype",
            _html.escape(cluster_result.label[:25]),
            "k-means cluster",
        ))
    if distress_result:
        prob = distress_result.distress_probability
        prob_color = "var(--cad-pos)" if prob < 0.15 else ("var(--cad-warn)" if prob < 0.35 else "var(--cad-neg)")
        kpi_parts.append(ck_kpi_block(
            "Distress Risk",
            f'<span style="color:{prob_color};">{prob:.1%}</span>',
            "predicted probability",
        ))
    if rcm_result:
        kpi_parts.append(ck_kpi_block(
            "RCM Opportunity",
            _fmt_money(rcm_result.risk_adjusted_opportunity),
            "risk-adjusted uplift",
        ))
        kpi_parts.append(ck_kpi_block(
            "Opportunity Grade",
            _grade_badge(rcm_result.grade),
            "tiered scoring",
        ))
        kpi_parts.append(ck_kpi_block(
            "Projected Margin",
            f"{rcm_result.projected_margin:.1%}",
            "post-RCM uplift",
        ))

    if kpi_parts:
        sections.append(
            f'<div class="ck-kpi-grid" style="grid-template-columns:repeat({len(kpi_parts)},1fr);">'
            + "".join(kpi_parts) + '</div>'
        )

    # ── Cluster detail ──
    if cluster_result:
        peer_rows = ""
        for peer in cluster_result.nearest_peers[:6]:
            peer_rows += (
                f'<tr>'
                f'<td><a href="/hospital/{_html.escape(peer["ccn"])}" '
                f'style="color:var(--cad-link);text-decoration:none;">'
                f'{_html.escape(peer["name"])}</a></td>'
                f'<td>{_html.escape(peer["state"])}</td>'
                f'<td class="num">{peer["beds"]}</td>'
                f'</tr>'
            )

        cp = next((p for p in cluster_result.all_clusters if p.cluster_id == cluster_result.cluster_id), None)
        desc = cp.pe_relevance if cp else ""

        sections.append(
            f'<div class="cad-card">'
            f'<h2>Cluster: {_html.escape(cluster_result.label)}</h2>'
            f'<p style="font-size:12px;color:var(--cad-text2);margin-bottom:8px;">'
            f'Percentile within cluster: P{cluster_result.cluster_percentile:.0f}. '
            f'{_html.escape(desc)}</p>'
            f'<h3 style="font-size:12px;margin:10px 0 6px;">Nearest Peers</h3>'
            f'<table class="cad-table"><thead><tr><th>Hospital</th><th>State</th><th>Beds</th>'
            f'</tr></thead><tbody>{peer_rows}</tbody></table></div>'
        )

    # ── Distress detail ──
    if distress_result:
        factor_rows = ""
        for f in distress_result.contributing_factors[:6]:
            dir_color = "var(--cad-neg)" if f["direction"] == "increases" else "var(--cad-pos)"
            factor_rows += (
                f'<tr>'
                f'<td>{_html.escape(f["feature"])}</td>'
                f'<td class="num">{f["value"]:.3f}</td>'
                f'<td class="num" style="color:{dir_color};">{f["contribution"]:+.3f}</td>'
                f'<td style="color:{dir_color};font-size:11px;">'
                f'{"&#9650; risk" if f["direction"] == "increases" else "&#9660; risk"}</td>'
                f'</tr>'
            )

        factor_chart_rows = [
            {"feature": f["feature"], "contribution": f["contribution"],
             "direction": f["direction"]}
            for f in distress_result.contributing_factors[:6]
        ]
        factor_chart = _factor_contribution_chart(factor_chart_rows)
        factor_caption = (
            '<div class="ml-chart-caption">'
            'Per-factor contribution to distress score · right = adds risk · left = reduces risk'
            '</div>'
        ) if factor_chart else ""

        sections.append(
            f'<div class="cad-card">'
            f'<h2>Distress Analysis</h2>'
            f'<div style="display:flex;gap:16px;margin-bottom:10px;font-size:12px;">'
            f'<div>Risk: {_risk_badge(distress_result.risk_label)}</div>'
            f'<div>National distress rate: <strong>{distress_result.peer_distress_rate:.1%}</strong></div>'
            f'<div>{_html.escape(distress_result.state)} distress rate: '
            f'<strong>{distress_result.state_distress_rate:.1%}</strong></div>'
            f'<div>Model AUC: <strong>{distress_result.model_auc:.3f}</strong></div>'
            f'</div>'
            f'{factor_chart}{factor_caption}'
            f'<table class="cad-table"><thead><tr>'
            f'<th>Factor</th><th>Value</th><th>Contribution</th><th>Direction</th>'
            f'</tr></thead><tbody>{factor_rows}</tbody></table></div>'
        )

    # ── RCM Opportunity ──
    if rcm_result:
        lever_rows = ""
        for lev in rcm_result.levers:
            if lev.risk_adjusted_impact < 1000:
                continue
            gap_pct = f"{lev.gap:.1%}" if abs(lev.gap) < 2 else f"{lev.gap:.2f}"
            lever_rows += (
                f'<tr>'
                f'<td style="font-weight:500;">{_html.escape(lev.lever)}</td>'
                f'<td class="num">{lev.current_value:.3f}</td>'
                f'<td class="num">{lev.benchmark_value:.3f}</td>'
                f'<td class="num">{gap_pct}</td>'
                f'<td class="num" style="color:var(--cad-pos);font-weight:600;">'
                f'{_fmt_money(lev.risk_adjusted_impact)}</td>'
                f'<td class="num">{lev.confidence:.0%}</td>'
                f'<td class="num">{lev.implementation_months}mo</td>'
                f'</tr>'
            )

        lever_chart = _rcm_lever_chart(rcm_result.levers)
        lever_caption = (
            '<div class="ml-chart-caption">'
            'Risk-adjusted EBITDA impact per lever · darker = higher confidence · timeline shown in months'
            '</div>'
        ) if lever_chart else ""

        sections.append(
            f'<div class="cad-card">'
            f'<h2>RCM Improvement Opportunity</h2>'
            f'<div style="display:flex;gap:16px;margin-bottom:10px;font-size:12px;">'
            f'<div>Total (risk-adjusted): <strong style="color:var(--cad-pos);">'
            f'{_fmt_money(rcm_result.risk_adjusted_opportunity)}</strong></div>'
            f'<div>Current margin: <strong>{rcm_result.current_margin:.1%}</strong></div>'
            f'<div>Projected margin: <strong style="color:var(--cad-pos);">'
            f'{rcm_result.projected_margin:.1%}</strong></div>'
            f'<div>Grade: {_grade_badge(rcm_result.grade)}</div>'
            f'<div>Comps: <strong>{rcm_result.comparable_count}</strong></div>'
            f'</div>'
            f'<p style="font-size:11.5px;color:var(--cad-text2);margin-bottom:8px;">'
            f'Gap analysis vs P75 peers with 60% closure assumption. Confidence-weighted by '
            f'lever implementation difficulty.</p>'
            f'{lever_chart}{lever_caption}'
            f'<table class="cad-table"><thead><tr>'
            f'<th>Lever</th><th>Current</th><th>Benchmark</th><th>Gap</th>'
            f'<th>Impact</th><th>Confidence</th><th>Timeline</th>'
            f'</tr></thead><tbody>{lever_rows}</tbody></table></div>'
        )

    # ── RCM Performance Predictions ──
    if rcm_perf:
        pred_rows = ""
        for p in rcm_perf.predictions:
            # Phase A1: replace bare [lo, hi] with ck_confidence_band
            # so the predicted value + CI read as one unit. Tail-
            # percentile predictions (P<5 or P>95) get low_confidence
            # tone since extreme positions usually warrant external
            # verification.
            if p.predicted_value < 2:
                fmt = lambda v: f"{v:.1%}"
            else:
                fmt = lambda v: f"{v:.1f}"
            val_band = ck_confidence_band(
                fmt(p.predicted_value),
                fmt(p.confidence_interval[0]),
                fmt(p.confidence_interval[1]),
                label="90% CI",
                low_confidence=(p.peer_percentile < 5 or p.peer_percentile > 95),
            )
            pred_rows += (
                f'<tr>'
                f'<td style="font-weight:500;">{_html.escape(p.metric)}</td>'
                f'<td class="num" style="font-weight:600;">{val_band}</td>'
                f'<td class="num">P{p.peer_percentile:.0f}</td>'
                f'<td style="font-size:11px;">{_html.escape(p.interpretation[:60])}</td>'
                f'</tr>'
            )

        grade_color = {
            "A": "var(--cad-pos)", "B": "var(--cad-accent)",
            "C": "var(--cad-warn)", "D": "var(--cad-neg)",
        }.get(rcm_perf.overall_rcm_grade, "var(--cad-text3)")

        sections.append(
            f'<div class="cad-card">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">'
            f'<h2>Predicted RCM Performance (Public Data Only)</h2>'
            f'<div style="text-align:center;">'
            f'<span style="font-size:24px;font-weight:700;color:{grade_color};'
            f'font-family:var(--cad-mono);">{rcm_perf.overall_rcm_grade}</span>'
            f'<div style="font-size:10px;color:var(--cad-text3);">RCM Grade</div></div></div>'
            f'<p style="font-size:12px;color:var(--cad-text2);margin-bottom:8px;">'
            f'{_html.escape(rcm_perf.screening_recommendation)}</p>'
            f'<table class="cad-table"><thead><tr>'
            f'<th>Metric</th><th>Predicted [90% CI]</th><th>Percentile</th><th>Assessment</th>'
            f'</tr></thead><tbody>{pred_rows}</tbody></table></div>'
        )

    # ── Navigation ──
    sections.append(
        f'<div class="cad-card" style="display:flex;gap:8px;flex-wrap:wrap;">'
        f'<a href="/hospital/{_html.escape(ccn)}" class="cad-btn cad-btn-primary" '
        f'style="text-decoration:none;">Hospital Profile</a>'
        f'<a href="/portfolio/regression/hospital/{_html.escape(ccn)}" class="cad-btn" '
        f'style="text-decoration:none;">Statistical Profile</a>'
        f'<a href="/bayesian/hospital/{_html.escape(ccn)}" class="cad-btn" '
        f'style="text-decoration:none;">Bayesian Calibration</a>'
        f'<a href="/hospital/{_html.escape(ccn)}/demand" class="cad-btn" '
        f'style="text-decoration:none;">Demand Analysis</a>'
        f'<a href="/quant-lab" class="cad-btn" style="text-decoration:none;">Quant Lab</a>'
        f'<a href="/ml-insights" class="cad-btn" style="text-decoration:none;">National ML Insights</a>'
        f'</div>'
    )

    body = _ML_CHART_CSS + "\n".join(sections)
    return chartis_shell(
        body,
        f"ML Analysis — {_html.escape(name)}",
        subtitle=f"CCN {_html.escape(ccn)} | Clustering + Distress + RCM Opportunity",
        editorial_intro={
            "eyebrow": "HOSPITAL ML",
            "headline": "What the model says about this one hospital.",
            "italic_word": "says",
            "body": (
                "Cluster archetype, distress probability, and RCM "
                "opportunity score for this CCN. Each panel surfaces "
                "the model's confidence so the partner can weigh the "
                "signal against their own diligence."
            ),
        },
    )
