"""Surrogate Model page renderer — chartis_shell version."""
from __future__ import annotations

import html
from typing import Any, Dict

from ._chartis_kit import (
    chartis_shell, ck_eyebrow, ck_fmt_num, ck_kpi_block,
    ck_next_section, ck_provenance_tooltip,
)
from .brand import PALETTE


def render_surrogate_page(
    schema: Dict[str, Any], model_ready: bool,
) -> str:
    status = "Trained" if model_ready else "Not Trained"
    status_cls = "cad-badge-green" if model_ready else "cad-badge-amber"

    features_html = "".join(
        f'<span class="cad-badge cad-badge-muted" style="margin:2px 4px 2px 0;">'
        f'{html.escape(f)}</span>'
        for f in schema.get("suggested_features", [])
    )
    targets_html = "".join(
        f'<span class="cad-badge cad-badge-blue" style="margin:2px 4px 2px 0;">'
        f'{html.escape(t)}</span>'
        for t in schema.get("suggested_targets", [])
    )

    # Cycle 47 — KPI strip with provenance.
    n_features = len(schema.get("suggested_features", []))
    n_targets = len(schema.get("suggested_targets", []))
    status_value = ck_provenance_tooltip(
        "Surrogate model status",
        status,
        explainer=(
            "Trained = the surrogate has fit on the cached "
            "analysis runs and can predict; Not Trained = no "
            "trained model yet. Run analyses to generate "
            "training data, then re-fit."
        ),
    )
    features_value = ck_provenance_tooltip(
        "Features in schema",
        ck_fmt_num(n_features),
        explainer=(
            "Suggested input features for the surrogate, drawn "
            "from the cached primitives. The platform picks the "
            "subset that's most predictive of the target on the "
            "current corpus."
        ),
        inject_css=False,
    )
    kpi_strip = (
        '<div class="ck-kpi-grid" style="grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:14px;">'
        + ck_kpi_block("Status", status_value, "model state")
        + ck_kpi_block("Features", features_value, "candidate inputs")
        + ck_kpi_block("Targets", ck_fmt_num(n_targets), "predicted outputs")
        + '</div>'
    )

    body = (
        ck_eyebrow("Surrogate Model")
        + kpi_strip
        + f'<div class="cad-card">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;">'
        f'<div>'
        f'<p style="color:{PALETTE["text_secondary"]};font-size:12.5px;">'
        f'Fast approximate EBITDA drag prediction for portfolio screening and what-if analysis.</p>'
        f'</div>'
        f'<span class="cad-badge {status_cls}" style="font-size:12px;padding:4px 12px;">'
        f'{status}</span>'
        f'</div>'
        f'<p style="color:{PALETTE["text_muted"]};font-size:12px;margin-top:8px;">'
        f'{"Model is ready for predictions." if model_ready else "No trained model yet. Analyze a deal to generate training data."}'
        f'</p>'
        + ('' if model_ready else
           f'<a href="/analysis" class="cad-btn cad-btn-primary" '
           f'style="text-decoration:none;margin-top:8px;display:inline-block;">'
           f'Go to Analysis &rarr;</a>')
        + f'</div>'

        f'<div class="cad-card">'
        f'<h2>Training Data Schema</h2>'
        f'<p style="color:{PALETTE["text_secondary"]};font-size:12.5px;margin-bottom:12px;">'
        f'{html.escape(schema.get("description", ""))}</p>'
        f'<h3 style="font-size:12px;color:{PALETTE["text_muted"]};margin-bottom:6px;">'
        f'SUGGESTED FEATURES</h3>'
        f'<div style="margin-bottom:12px;">{features_html or "None defined"}</div>'
        f'<h3 style="font-size:12px;color:{PALETTE["text_muted"]};margin-bottom:6px;">'
        f'SUGGESTED TARGETS</h3>'
        f'<div>{targets_html or "None defined"}</div>'
        f'</div>'

        f'<div class="cad-card" style="display:flex;gap:8px;">'
        f'<a href="/api/surrogate/schema" class="cad-btn" style="text-decoration:none;">'
        f'API: GET /api/surrogate/schema</a></div>'
        + ck_next_section(
            "Open the predictive screener",
            "/predictive-screener",
            eyebrow="Continue —",
            italic_word="screener",
        )
    )
    # 2026-05-28 batch 29 · Phase 3 · universal strict 5-block head.
    from ._chartis_kit import ck_editorial_head
    head = ck_editorial_head(
        eyebrow="SURROGATE MODEL",
        title="What the model predicts in milliseconds.",
        meta=(
            f"{n_features} FEATURE"
            f"{'S' if n_features != 1 else ''} · "
            f"{n_targets} TARGET"
            f"{'S' if n_targets != 1 else ''} · "
            f"{'TRAINED' if model_ready else 'AWAITING TRAINING'}"
        ),
        lede_italic_phrase="What the model predicts in milliseconds.",
        lede_body=(
            "A trained surrogate fits cached analysis runs "
            "and produces fast EBITDA-drag predictions for "
            "screening and what-if work. Use as a triage "
            "filter, not as a substitute for the full "
            "DealAnalysisPacket."
        ),
    )
    body = head + body
    return chartis_shell(body, "Surrogate Model",
                    subtitle="Fast approximate prediction for screening")
