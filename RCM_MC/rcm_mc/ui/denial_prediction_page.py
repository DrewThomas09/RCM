"""Claim-level denial prediction page at /diligence/denial-prediction.

Takes a CCD fixture, trains a Naive Bayes denial model on the
train split, scores the test split, and renders:
    - Hero stat row: baseline denial rate, AUC, recoverable $
    - Calibration bar chart (reliability diagram)
    - Top-5 denial-lift features as a sortable table
    - Flagged claims table (systematic misses + false positives)
    - EBITDA bridge contribution card
"""
from __future__ import annotations

import html
from typing import Any, Dict, List, Optional

from ..diligence import ingest_dataset
from ..diligence._pages import AVAILABLE_FIXTURES, _resolve_dataset
from ..diligence.denial_prediction import (
    DenialPredictionReport, analyze_ccd,
)
from ..diligence.denial_prediction.model import CalibrationBucket
from ._chartis_kit import (
    P, chartis_shell, ck_action_button, ck_kpi_block, ck_next_section,
    ck_page_title, ck_panel, ck_section_intro, ck_page_explainer)
from .power_ui import provenance, sortable_table

_EXPLAINER_CSS = """
.ck-dp-explainer{font-family:var(--sc-serif);font-size:15px;line-height:1.6;
color:var(--sc-text-dim);max-width:68ch;margin:var(--sc-s-4) 0 var(--sc-s-6);}
.ck-dp-explainer em{color:var(--sc-teal-ink);font-style:italic;}
"""


def _landing() -> str:
    options = "".join(
        f'<option value="{html.escape(n)}">{html.escape(l)}</option>'
        for n, l in AVAILABLE_FIXTURES
    )
    title_block = (
        ck_page_title(
        "Predictive Denial Model", eyebrow="PREDICTIVE DENIAL MODEL",
        meta=f"{len(AVAILABLE_FIXTURES)} fixtures · Naive Bayes · claim-level",
    )
        + ck_page_explainer(
            'Claim-level denial prediction from CCD data.',
            "Predicts the per-claim probability of a payer denial using the platform's ML denial model on the deal's CCD (consolidated clinical document) feed. Used to size the recoverable revenue from a denial-management initiative before underwriting it into the EBITDA bridge.",
            source='Selected CCD fixture (sample claims, not a live per-deal feed) + denial ML model trained live on it (rcm_mc.ml.denial_model). Fixture data is for methodology — verify against the target’s own CCD before IC use.',
        )
    )
    explainer_html = (
        '<p class="ck-dp-explainer">'
        '<em>Where the denial revenue hides in the CCD.</em> '
        "Trains a per-claim Naive Bayes model on the CCD, scores the "
        "held-out split, and flags systematic misses — recoverable "
        "revenue the model says shouldn't have been denied. Feeds the "
        "EBITDA bridge denial-reduction lever with a data-driven target."
        "</p>"
    )
    body = (
        title_block
        + f'<form method="GET" action="/diligence/denial-prediction" '
        f'style="max-width:480px;margin-top:20px;background:{P["panel"]};'
        f'border:1px solid {P["border"]};border-radius:4px;padding:20px;">'
        f'<label style="font-size:9px;color:{P["text_faint"]};'
        f'letter-spacing:1.5px;text-transform:uppercase;font-weight:600;'
        f'display:block;margin-bottom:4px;">CCD fixture</label>'
        f'<select name="dataset" required style="width:100%;padding:6px 8px;'
        f'background:{P["panel_alt"]};color:{P["text"]};'
        f'border:1px solid {P["border"]};font-family:inherit;">'
        f'<option value="">— pick a fixture —</option>{options}</select>'
        f'<label style="font-size:9px;color:{P["text_faint"]};'
        f'letter-spacing:1.5px;text-transform:uppercase;font-weight:600;'
        f'display:block;margin-top:12px;margin-bottom:4px;">'
        f'Train fraction (0-1)</label>'
        f'<input name="train_fraction" value="0.7" '
        f'style="width:100%;padding:6px 8px;background:{P["panel_alt"]};'
        f'color:{P["text"]};border:1px solid {P["border"]};'
        f'font-family:inherit;">'
        f'<div style="margin-top:16px;">{ck_action_button("Run prediction")}</div>'
        f'</form>'
    )
    return chartis_shell(
        body, "Predictive Denial Model",
        active_nav="/diligence/denial-prediction",
        extra_css=_EXPLAINER_CSS,
    )


def _calibration_chart(
    buckets: List[CalibrationBucket],
    width: int = 640, height: int = 220,
) -> str:
    """Reliability diagram — predicted mean vs. actual denial rate."""
    if not buckets:
        return ""
    pad_l, pad_r, pad_t, pad_b = 50, 20, 30, 36
    inner_w = width - pad_l - pad_r
    inner_h = height - pad_t - pad_b

    def x(v): return pad_l + v * inner_w
    def y(v): return pad_t + inner_h - v * inner_h

    # Perfect calibration diagonal.
    diag = (
        f'<line x1="{x(0)}" y1="{y(0)}" x2="{x(1)}" y2="{y(1)}" '
        f'stroke="{P["text_faint"]}" stroke-dasharray="3,3" />'
    )
    # Model points + bar chart of count per bucket.
    bars = []
    points = []
    max_cnt = max([b.count for b in buckets]) or 1
    for b in buckets:
        # Bar (count, low-contrast).
        bar_h = (b.count / max_cnt) * (inner_h * 0.3)
        bw = inner_w / len(buckets) * 0.9
        bx = x((b.lower + b.upper) / 2) - bw / 2
        by = pad_t + inner_h - bar_h
        bars.append(
            f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bw:.1f}" '
            f'height="{bar_h:.1f}" fill="{P["border"]}" opacity="0.5" />'
        )
        if b.count > 0:
            px = x(b.predicted_mean)
            py = y(b.actual_rate)
            r = 3 + min(8, b.count ** 0.5)
            points.append(
                f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{r:.1f}" '
                f'fill="{P["accent"]}" opacity="0.8" />'
            )

    # Axis labels.
    x_ticks = "".join(
        f'<text x="{x(v):.1f}" y="{pad_t + inner_h + 14:.1f}" '
        f'fill="{P["text_faint"]}" text-anchor="middle" font-size="9" '
        f'font-family="JetBrains Mono, monospace">{v:.1f}</text>'
        for v in (0.0, 0.25, 0.5, 0.75, 1.0)
    )
    y_ticks = "".join(
        f'<text x="{pad_l - 6:.1f}" y="{y(v) + 3:.1f}" '
        f'fill="{P["text_faint"]}" text-anchor="end" font-size="9" '
        f'font-family="JetBrains Mono, monospace">{v:.1f}</text>'
        for v in (0.0, 0.25, 0.5, 0.75, 1.0)
    )
    return (
        f'<svg viewBox="0 0 {width} {height}" width="100%" '
        f'style="max-width:{width}px;">'
        f'<text x="{pad_l}" y="18" fill="{P["text_dim"]}" '
        f'font-size="10" font-family="Helvetica Neue, Arial, sans-serif" '
        f'letter-spacing="1.5" font-weight="700">CALIBRATION · RELIABILITY</text>'
        f'{"".join(bars)}'
        f'{diag}'
        f'{"".join(points)}'
        f'{x_ticks}{y_ticks}'
        f'<text x="{(pad_l+inner_w)/2 + pad_l/2:.1f}" '
        f'y="{pad_t + inner_h + 30:.1f}" fill="{P["text_faint"]}" '
        f'text-anchor="middle" font-size="9" '
        f'font-family="Helvetica Neue, Arial, sans-serif">'
        f'Predicted denial probability</text>'
        f'<text x="14" y="{pad_t + inner_h/2:.1f}" '
        f'fill="{P["text_faint"]}" font-size="9" '
        f'transform="rotate(-90 14 {pad_t + inner_h/2})" '
        f'text-anchor="middle">Actual rate</text>'
        f'</svg>'
    )


def _top_features_table(report: DenialPredictionReport) -> str:
    if not report.top_features:
        return ""
    headers = ["Feature", "Value", "Denial Lift", "Marginal Rate"]
    rows = []
    sort_keys = []
    for f in report.top_features[:10]:
        rows.append([
            f.feature,
            f.value,
            f"{f.lift:.2f}x",
            f"{f.marginal_denial_rate*100:.1f}%",
        ])
        sort_keys.append([
            f.feature, f.value, f.lift, f.marginal_denial_rate,
        ])
    return sortable_table(
        headers, rows, name="denial_features",
        sort_keys=sort_keys,
    )


def _flagged_claims_table(report: DenialPredictionReport) -> str:
    if not report.flagged_claims:
        return (
            f'<div style="padding:14px 0;color:{P["text_faint"]};'
            f'font-size:11px;font-style:italic;">No systematic misses '
            f'or false positives flagged on this CCD split.</div>'
        )
    headers = [
        "Claim ID", "Reason", "Predicted P(denial)",
        "Actual", "Charge", "Paid", "CPT Family", "Payer",
    ]
    rows = []
    sort_keys = []
    for c in report.flagged_claims[:30]:
        reason_label = (
            "Systematic miss"
            if c.reason == "systematic_miss" else "Systematic FP"
        )
        actual_label = "Denied" if c.actually_denied else "Paid"
        rows.append([
            c.claim_id,
            reason_label,
            f"{c.predicted_denial_probability*100:.1f}%",
            actual_label,
            f"${c.charge_amount_usd:,.0f}",
            f"${c.paid_amount_usd:,.0f}",
            c.cpt_family,
            c.payer_class,
        ])
        sort_keys.append([
            c.claim_id, c.reason,
            c.predicted_denial_probability,
            int(c.actually_denied),
            c.charge_amount_usd,
            c.paid_amount_usd,
            c.cpt_family, c.payer_class,
        ])
    return sortable_table(
        headers, rows, name="flagged_claims",
        sort_keys=sort_keys,
    )


def _hero(report: DenialPredictionReport) -> str:
    cal = report.calibration
    # AUC interpretation — WHAT IT MEANS matters more than the number.
    if cal.auc_rough >= 0.80:
        auc_color = P["positive"]
        auc_label = "Strong"
    elif cal.auc_rough >= 0.70:
        auc_color = P["positive"]
        auc_label = "Good"
    elif cal.auc_rough >= 0.60:
        auc_color = P["warning"]
        auc_label = "Moderate"
    else:
        auc_color = P["negative"]
        auc_label = "Weak — treat outputs with caution"

    # Baseline denial rate vs. HFMA FPDR peer benchmark (8-12%).
    PEER_DENIAL_MEDIAN = 0.10
    baseline = report.baseline_denial_rate
    if baseline <= 0.08:
        base_color = P["positive"]; base_label = "Top quartile (≤8%)"
    elif baseline <= 0.12:
        base_color = P["warning"]; base_label = "Peer median (~10%)"
    elif baseline <= 0.18:
        base_color = P["warning"]; base_label = "Above peer median"
    else:
        base_color = P["negative"]; base_label = "Bottom quartile (>18%)"

    bridge = report.bridge_input
    miss_label = provenance(
        f'${report.systematic_miss_charge_dollars:,.0f}',
        source=(
            f'{report.systematic_miss_count} test-split claims '
            f'with predicted denial probability ≥ 50% that were '
            f'NOT actually denied — sum of charge_amount.'
        ),
        formula=(
            'sum(charge_amount) where predict_proba >= 0.5 '
            'AND status != DENIED'
        ),
        detail=(
            'Audit + appeal can recover 60-80% of charges that '
            'that should not have been denied.'
        ),
    )
    # Plain-English summary composed from the band labels.
    if cal.auc_rough < 0.6:
        summary = (
            f"The model's AUC of {cal.auc_rough:.2f} is below the "
            f"0.60 floor — treat flagged claims as suggestions, not "
            f"directives. Typically means too few training claims "
            f"or a highly uniform CCD."
        )
    elif report.systematic_miss_count == 0:
        summary = (
            f"No systematic misses — the seller's denial profile "
            f"matches what the model predicts. The denial Pareto on "
            f"the benchmarks tab remains the primary Phase-3 input."
        )
    else:
        summary = (
            f"The model flagged "
            f"{report.systematic_miss_count} claims "
            f"({report.systematic_miss_count / max(report.n_test,1)*100:.1f}% "
            f"of test split) that look like denials but weren't. "
            f"${report.systematic_miss_charge_dollars:,.0f} in charges "
            f"— audit + appeal recovery typically 60–80% of that."
        )

    # Editorial intro + KPI strip. The bespoke 4-tile grid is replaced
    # by ck_kpi_block calls so the metrics inherit shell typography
    # (Source Serif label, JetBrains numerics) and the responsive
    # tile layout. Tone-bearing labels go into the ``sub`` slot;
    # secondary peer-comparison strings get appended via
    # newline-separated text since ck_kpi_block sub is single-line.
    intro = ck_section_intro(
        eyebrow="Denial Prediction",
        headline=(
            f"{report.provider_id or 'Provider'} · "
            f"{report.n_claims:,} claims · "
            f"{report.n_train:,} train · {report.n_test:,} test"
        ),
        body=summary,
        italic_word="shows",
    )
    kpis = (
        '<div class="ck-kpi-strip">'
        + ck_kpi_block(
            "Baseline denial rate",
            f"{report.baseline_denial_rate*100:.1f}%",
            sub=f"{base_label} · vs HFMA peer median {PEER_DENIAL_MEDIAN*100:.0f}%",
            help={
                "definition": (
                    "Share of submitted claims that get denied "
                    "before any appeals. HFMA peer median ~10%; "
                    "above 15% is a structural denial issue (often "
                    "payer mix or charge-capture); below 7% on real "
                    "volume is best-in-class."
                ),
                "citation": "HFMA MAP Key 2021",
            },
        )
        + ck_kpi_block(
            "Model AUC",
            f"{cal.auc_rough:.3f}",
            sub=f"{auc_label} · 0.5 = random, 1.0 = perfect, >0.7 usable",
            help={
                "definition": (
                    "Area-under-curve — how well the model separates "
                    "denied from paid claims. 0.5 = coin flip; 0.7-0.8 "
                    "= usable for prioritization; 0.9+ = the model "
                    "rarely confuses the two classes. Below 0.7 the "
                    "model is too noisy to act on at the claim level."
                ),
            },
        )
        + ck_kpi_block(
            "Systematic misses",
            f"{report.systematic_miss_count}",
            sub="Claims flagged as denials but not denied",
            help={
                "definition": (
                    "Claims the model flagged as high-denial-risk "
                    "but that ultimately got paid. Each represents a "
                    "false alarm — wasted appeals effort. High count "
                    "(>5% of flags) means the model is too eager; "
                    "tune the threshold before automating workflow."
                ),
            },
        )
        + ck_kpi_block(
            "Recoverable (charge)",
            miss_label,
            sub="60–80% realistic recovery · hover for source",
            help={
                "definition": (
                    "Dollar charge value of denied claims that the "
                    "model says are recoverable. The 60-80% realism "
                    "haircut accounts for appeals that drag past "
                    "timely-filing deadlines or end in adverse "
                    "decisions. Use this number as an upper bound on "
                    "RCM uplift attributable to denial-driver-only "
                    "interventions."
                ),
            },
        )
        + "</div>"
    )
    return intro + kpis


def _calibration_block(report: DenialPredictionReport) -> str:
    c = report.calibration
    # ck_kpi_strip for the four scalar metrics; the chart stays as
    # rendered SVG/HTML (calibration buckets are visual, not tabular).
    metrics = (
        '<div class="ck-kpi-strip">'
        + ck_kpi_block(
            "Brier score", f"{c.brier_score:.4f}",
            help={
                "definition": (
                    "Mean squared error between predicted "
                    "probability and observed outcome. 0 = perfect "
                    "calibration; 0.25 = no-better-than-random. "
                    "Below 0.10 is a well-calibrated probability "
                    "model; above 0.20 means the probabilities aren't "
                    "trustworthy as decision inputs."
                ),
            },
        )
        + ck_kpi_block(
            "Log loss", f"{c.log_loss:.4f}",
            help={
                "definition": (
                    "Cross-entropy between predicted probabilities "
                    "and observed labels. Penalizes confident wrong "
                    "predictions more than uncertain wrong ones. "
                    "Lower = better; compare against the baseline log "
                    "loss (predicting the base rate alone) to know "
                    "if the model adds value."
                ),
            },
        )
        + ck_kpi_block(
            "Accuracy", f"{c.accuracy*100:.1f}%",
            help={
                "definition": (
                    "Share of claims where the model's most-likely "
                    "class matches reality. Misleading on imbalanced "
                    "data — a 90%-paid base rate makes "
                    "'predict-everything-paid' 90% accurate while "
                    "being useless. Read with AUC + Brier for the "
                    "real signal."
                ),
            },
        )
        + ck_kpi_block(
            "AUC (rough)", f"{c.auc_rough:.3f}",
            help={
                "definition": (
                    "Rough discriminatory power, computed at the "
                    "decile level. Faster than full AUC; close enough "
                    "for IC discussion. For an audit-grade number, "
                    "run the full sklearn-style AUC on the holdout "
                    "set."
                ),
            },
        )
        + "</div>"
    )
    return ck_panel(
        f"{metrics}{_calibration_chart(c.buckets)}",
        title="Calibration",
    )


def _bridge_card(report: DenialPredictionReport) -> str:
    b = report.bridge_input
    if b is None:
        return ""
    targets_html = "".join(
        f'<li><strong>{html.escape(t["feature"])}</strong> = '
        f'<span class="ck-cell-mono">{html.escape(t["value"])}</span> · '
        f'lift {t["lift"]:.2f}x · '
        f'{t["denial_rate"]*100:.0f}% denial rate in matching claims'
        f'</li>'
        for t in b.top_intervention_targets
    )
    metrics = (
        '<div class="ck-kpi-strip">'
        + ck_kpi_block(
            "Recoverable revenue",
            f"${b.recoverable_revenue_usd:,.0f}",
        )
        + ck_kpi_block(
            "Annualised",
            f"${b.annualised_usd:,.0f}",
        )
        + ck_kpi_block(
            "Claims flagged",
            f"{b.claim_count_flagged}",
        )
        + ck_kpi_block(
            "Confidence",
            html.escape(b.confidence),
        )
        + "</div>"
    )
    body = (
        f'{metrics}'
        f'<p class="ck-section-body" style="margin-top:16px;">'
        f'Top intervention targets:</p>'
        f'<ul class="ck-list">{targets_html}</ul>'
    )
    return ck_panel(body, title="EBITDA Bridge · Denial Reduction Lever")


def render_denial_prediction_page(
    *,
    dataset: str = "",
    train_fraction: float = 0.7,
) -> str:
    if not dataset:
        return _landing()
    ds_path = _resolve_dataset(dataset)
    if ds_path is None:
        return _landing()
    try:
        ccd = ingest_dataset(ds_path)
    except Exception as exc:  # noqa: BLE001
        return chartis_shell(
            f'<div style="padding:24px;color:{P["negative"]};">'
            f'Failed to ingest {html.escape(dataset)}: '
            f'{html.escape(str(exc))}</div>',
            "Denial Prediction",
        )
    try:
        report = analyze_ccd(
            ccd, train_fraction=train_fraction, seed=42,
        )
    except Exception as exc:  # noqa: BLE001
        return chartis_shell(
            f'<div style="padding:24px;color:{P["negative"]};">'
            f'Prediction failed: {html.escape(str(exc))}</div>',
            "Denial Prediction",
        )

    body = (
        ck_page_title(
            "Denial Prediction",
            eyebrow="RCM DILIGENCE",
            meta=f"Dataset: {dataset} · ML-trained on labeled CCD",
        )
        + _hero(report)
        + _calibration_block(report)
        + f'<div style="font-size:10px;color:{P["text_faint"]};'
          f'letter-spacing:1.5px;text-transform:uppercase;font-weight:700;'
          f'margin-bottom:8px;">TOP FEATURES BY DENIAL LIFT</div>'
        + _top_features_table(report)
        + f'<div style="font-size:10px;color:{P["text_faint"]};'
          f'letter-spacing:1.5px;text-transform:uppercase;font-weight:700;'
          f'margin:24px 0 8px 0;">FLAGGED CLAIMS</div>'
        + _flagged_claims_table(report)
        + _bridge_card(report)
        + ck_next_section(
            "Bridge these denials to the EBITDA impact",
            "/diligence/bridge-audit",
            eyebrow="Continue —",
            italic_word="bridge",
        )
    )
    return chartis_shell(
        body, f"Denial Prediction — {dataset}",
        active_nav="/diligence/denial-prediction",
        extra_css=_EXPLAINER_CSS,
    )
