"""Surrogate Model page renderer — shell_v2 version."""
from __future__ import annotations

import html
from typing import Any, Dict

from .shell_v2 import shell_v2
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

    body = (
        f'<div class="cad-card">'
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
    )
    return shell_v2(body, "Surrogate Model",
                    subtitle="Fast approximate prediction for screening")
