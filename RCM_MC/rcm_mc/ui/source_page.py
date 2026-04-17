"""Deal sourcing page: find hospitals that fit your thesis.

Route: GET /source — thesis selector + results table.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List, Optional

from .shell_v2 import shell_v2
from .brand import PALETTE


def _esc(s: Any) -> str:
    return html.escape("" if s is None else str(s))


def render_source_page(
    results: Optional[List[Dict[str, Any]]] = None,
    thesis_name: str = "",
) -> str:
    from ..analysis.deal_sourcer import THESIS_LIBRARY

    options = "".join(
        f'<option value="{_esc(k)}" '
        f'{"selected" if k == thesis_name else ""}>'
        f'{_esc(t.name)}</option>'
        for k, t in THESIS_LIBRARY.items()
    )

    results_html = ""
    if results:
        rows = ""
        for r in results:
            score = float(r.get("score") or 0)
            color = PALETTE["positive"] if score >= 70 else (PALETTE["warning"] if score >= 40 else PALETTE["negative"])
            rows += (
                f'<tr><td>{_esc(r.get("name") or "")}</td>'
                f'<td>{_esc(r.get("state") or "")}</td>'
                f'<td class="num">{r.get("bed_count") or "—"}</td>'
                f'<td class="num" style="color:{color};font-weight:600;">{score:.0f}</td>'
                f'<td><a href="/new-deal?q={_esc(r.get("ccn") or "")}" '
                f'class="cad-badge cad-badge-blue" style="text-decoration:none;">'
                f'Screen &rarr;</a></td></tr>'
            )
        results_html = (
            f'<div class="cad-card" style="margin-top:16px;">'
            f'<h2>{len(results)} Matches</h2>'
            f'<table class="cad-table"><thead><tr><th>Hospital</th>'
            f'<th>State</th><th>Beds</th><th>Score</th><th></th></tr></thead>'
            f'<tbody>{rows}</tbody></table></div>'
        )

    body = (
        f'<div class="cad-card">'
        f'<p style="color:{PALETTE["text_secondary"]};font-size:12.5px;margin-bottom:12px;">'
        f'Select an investment thesis and find hospitals from the HCRIS database that match.</p>'
        f'<form method="GET" action="/source" style="display:flex;gap:8px;align-items:center;">'
        f'<select name="thesis" style="padding:8px 12px;border:1px solid var(--cad-border);'
        f'border-radius:6px;background:var(--cad-bg3);color:var(--cad-text);font-size:13px;">'
        f'{options}</select>'
        f'<button type="submit" class="cad-btn cad-btn-primary">Find Matches</button>'
        f'</form></div>'
        f'{results_html or ""}'
    )

    if not results:
        body += (
            f'<div class="cad-card">'
            f'<h2>How Thesis Matching Works</h2>'
            f'<div style="font-size:12.5px;color:{PALETTE["text_secondary"]};line-height:1.7;">'
            f'<p>Each investment thesis defines target criteria: bed count range, revenue range, '
            f'payer mix thresholds, and geographic focus. SeekingChartis searches all ~6,000 HCRIS '
            f'hospitals and ranks matches by fit score.</p>'
            f'<p style="margin-top:6px;">For custom screening (by specific metrics), use the '
            f'<a href="/screen" style="color:{PALETTE["text_link"]};">Hospital Screener</a> instead.</p>'
            f'</div></div>'
        )

    n = len(results) if results else 0
    sub = f"{n} matches found" if results else "Thesis-driven deal origination from HCRIS"
    return shell_v2(body, "Deal Sourcing", subtitle=sub)
