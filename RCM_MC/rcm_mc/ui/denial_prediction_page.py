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
from ._chartis_kit import P, chartis_shell
from .power_ui import provenance, sortable_table


def _landing() -> str:
    options = "".join(
        f'<option value="{html.escape(n)}">{html.escape(l)}</option>'
        for n, l in AVAILABLE_FIXTURES
    )
    body = (
        f'<div style="padding:24px 0 12px 0;">'
        f'<div style="font-size:11px;color:{P["text_faint"]};letter-spacing:1.5px;'
        f'text-transform:uppercase;margin-bottom:6px;font-weight:600;">'
        f'Claim-Level Denial Prediction</div>'
        f'<div style="font-size:22px;color:{P["text"]};font-weight:600;'
        f'margin-bottom:4px;">Predictive Denial Model</div>'
        f'<div style="font-size:12px;color:{P["text_dim"]};max-width:720px;'
        f'line-height:1.55;">Trains a per-claim Naive Bayes model on the '
        f'CCD, scores the held-out split, and flags '
        f'<strong>systematic misses</strong> — claims the model '
        f'predicts should be denied but were paid (recoverable '
        f'revenue opportunity) and <strong>systematic false '
        f'positives</strong> — denied claims the model thinks '
        f'should have paid. Feeds the EBITDA bridge denial-reduction '
        f'lever with a data-driven target instead of an industry '
        f'aggregate.</div>'
        f'</div>'
        f'<form method="GET" action="/diligence/denial-prediction" '
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
        f'<button type="submit" style="margin-top:16px;padding:8px 20px;'
        f'background:{P["accent"]};color:{P["panel"]};border:0;'
        f'font-size:10px;letter-spacing:1.5px;text-transform:uppercase;'
        f'font-weight:700;cursor:pointer;">Run prediction</button></form>'
    )
    return chartis_shell(
        body, "RCM Diligence — Denial Prediction",
        subtitle="Claim-level predictive analytic",
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

    return (
        f'<div style="padding:24px 0 16px 0;border-bottom:1px solid '
        f'{P["border"]};margin-bottom:24px;">'
        f'<div style="font-size:11px;color:{P["text_faint"]};letter-spacing:1.5px;'
        f'text-transform:uppercase;margin-bottom:6px;font-weight:600;">'
        f'Denial Prediction</div>'
        f'<div style="font-size:22px;color:{P["text"]};font-weight:600;'
        f'margin-bottom:4px;">'
        f'{html.escape(report.provider_id or "Provider")}</div>'
        f'<div style="font-size:11px;color:{P["text_faint"]};">'
        f'{report.n_claims:,} claims · {report.n_train:,} train · '
        f'{report.n_test:,} test</div>'
        f'<div style="background:{P["panel_alt"]};border-left:3px solid '
        f'{P["accent"]};padding:10px 14px;margin-top:12px;'
        f'font-size:12px;color:{P["text_dim"]};line-height:1.55;'
        f'max-width:760px;">'
        f'<strong style="color:{P["text"]};">What this shows: </strong>'
        f'{html.escape(summary)}</div>'
        f'<div style="display:grid;grid-template-columns:repeat(4,1fr);'
        f'gap:20px;margin-top:20px;">'
        f'<div><div style="font-size:9px;color:{P["text_faint"]};'
        f'letter-spacing:1px;text-transform:uppercase;">Baseline denial rate</div>'
        f'<div style="font-size:26px;font-family:\'JetBrains Mono\',monospace;'
        f'font-weight:700;color:{base_color};">'
        f'{report.baseline_denial_rate*100:.1f}%</div>'
        f'<div style="font-size:10px;color:{base_color};margin-top:2px;">'
        f'{html.escape(base_label)}</div>'
        f'<div style="font-size:9px;color:{P["text_faint"]};margin-top:1px;">'
        f'vs HFMA peer median {PEER_DENIAL_MEDIAN*100:.0f}%</div></div>'
        f'<div><div style="font-size:9px;color:{P["text_faint"]};'
        f'letter-spacing:1px;text-transform:uppercase;">Model AUC</div>'
        f'<div style="font-size:26px;font-family:\'JetBrains Mono\',monospace;'
        f'font-weight:700;color:{auc_color};">'
        f'{cal.auc_rough:.3f}</div>'
        f'<div style="font-size:10px;color:{auc_color};margin-top:2px;">'
        f'{html.escape(auc_label)}</div>'
        f'<div style="font-size:9px;color:{P["text_faint"]};margin-top:1px;">'
        f'0.5 = random, 1.0 = perfect, &gt;0.7 = usable</div></div>'
        f'<div><div style="font-size:9px;color:{P["text_faint"]};'
        f'letter-spacing:1px;text-transform:uppercase;">Systematic misses</div>'
        f'<div style="font-size:26px;font-family:\'JetBrains Mono\',monospace;'
        f'font-weight:700;color:{P["warning"] if report.systematic_miss_count > 0 else P["text_faint"]};">'
        f'{report.systematic_miss_count}</div>'
        f'<div style="font-size:10px;color:{P["text_faint"]};margin-top:2px;">'
        f'Claims flagged as denials but not denied</div></div>'
        f'<div><div style="font-size:9px;color:{P["text_faint"]};'
        f'letter-spacing:1px;text-transform:uppercase;">Recoverable (charge)</div>'
        f'<div style="font-size:22px;font-family:\'JetBrains Mono\',monospace;'
        f'font-weight:700;color:{P["positive"]};">{miss_label}</div>'
        f'<div style="font-size:10px;color:{P["text_faint"]};margin-top:2px;">'
        f'hover for source · 60–80% realistic recovery</div></div>'
        f'</div></div>'
    )


def _calibration_block(report: DenialPredictionReport) -> str:
    c = report.calibration
    return (
        f'<div style="background:{P["panel"]};border:1px solid '
        f'{P["border"]};border-radius:4px;padding:14px 20px;'
        f'margin-bottom:16px;">'
        f'<div style="font-size:9px;color:{P["text_faint"]};'
        f'letter-spacing:1.5px;text-transform:uppercase;font-weight:700;'
        f'margin-bottom:8px;">Calibration</div>'
        f'<div style="display:flex;gap:24px;align-items:baseline;'
        f'margin-bottom:12px;font-size:12px;color:{P["text_dim"]};">'
        f'<div>Brier score: <strong style="color:{P["text"]};">'
        f'{c.brier_score:.4f}</strong></div>'
        f'<div>Log loss: <strong style="color:{P["text"]};">'
        f'{c.log_loss:.4f}</strong></div>'
        f'<div>Accuracy: <strong style="color:{P["text"]};">'
        f'{c.accuracy*100:.1f}%</strong></div>'
        f'<div>AUC (rough): <strong style="color:{P["text"]};">'
        f'{c.auc_rough:.3f}</strong></div>'
        f'</div>'
        f'{_calibration_chart(c.buckets)}'
        f'</div>'
    )


def _bridge_card(report: DenialPredictionReport) -> str:
    b = report.bridge_input
    if b is None:
        return ""
    conf_color = {
        "HIGH": P["positive"],
        "MEDIUM": P["warning"],
        "LOW": P["negative"],
    }.get(b.confidence, P["text_dim"])
    targets_html = "".join(
        f'<li><strong>{html.escape(t["feature"])}</strong> = '
        f'<span class="mono" style="color:{P["text"]};">'
        f'{html.escape(t["value"])}</span> · '
        f'lift {t["lift"]:.2f}x · '
        f'{t["denial_rate"]*100:.0f}% denial rate in matching claims'
        f'</li>'
        for t in b.top_intervention_targets
    )
    return (
        f'<div style="margin-top:16px;background:{P["panel"]};'
        f'border:1px solid {P["border"]};border-radius:4px;'
        f'padding:16px 20px;position:relative;overflow:hidden;">'
        f'<div style="position:absolute;top:0;left:0;right:0;height:2px;'
        f'background:linear-gradient(90deg,{P["positive"]},{P["accent"]});">'
        f'</div>'
        f'<div style="font-size:9px;color:{P["text_faint"]};'
        f'letter-spacing:1.5px;text-transform:uppercase;font-weight:700;'
        f'margin-top:4px;">EBITDA Bridge · Denial Reduction Lever</div>'
        f'<div style="font-size:16px;color:{P["text"]};font-weight:600;'
        f'margin-top:2px;">Data-driven target (vs industry aggregate)</div>'
        f'<div style="display:flex;gap:24px;align-items:baseline;'
        f'margin-top:14px;">'
        f'<div><div style="font-size:9px;color:{P["text_faint"]};'
        f'letter-spacing:.5px;text-transform:uppercase;">Recoverable revenue</div>'
        f'<div style="font-size:22px;font-family:\'JetBrains Mono\',monospace;'
        f'font-weight:700;color:{P["positive"]};">'
        f'${b.recoverable_revenue_usd:,.0f}</div></div>'
        f'<div><div style="font-size:9px;color:{P["text_faint"]};'
        f'letter-spacing:.5px;text-transform:uppercase;">Annualised</div>'
        f'<div style="font-size:16px;color:{P["text"]};">'
        f'${b.annualised_usd:,.0f}</div></div>'
        f'<div><div style="font-size:9px;color:{P["text_faint"]};'
        f'letter-spacing:.5px;text-transform:uppercase;">Claims flagged</div>'
        f'<div style="font-size:16px;color:{P["text"]};">'
        f'{b.claim_count_flagged}</div></div>'
        f'<div><div style="font-size:9px;color:{P["text_faint"]};'
        f'letter-spacing:.5px;text-transform:uppercase;">Confidence</div>'
        f'<div style="font-size:16px;color:{conf_color};font-weight:600;">'
        f'{html.escape(b.confidence)}</div></div>'
        f'</div>'
        f'<div style="margin-top:16px;font-size:11px;color:{P["text_dim"]};">'
        f'Top intervention targets:</div>'
        f'<ul style="margin:4px 0 0 20px;font-size:11px;color:{P["text_dim"]};'
        f'line-height:1.7;">{targets_html}</ul>'
        f'</div>'
    )


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
        _hero(report)
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
    )
    return chartis_shell(
        body, f"Denial Prediction — {dataset}",
        subtitle="Predictive RCM analytic",
    )
