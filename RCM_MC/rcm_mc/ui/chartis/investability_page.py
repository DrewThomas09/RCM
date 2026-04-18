"""Per-deal Investability + Exit Readiness — /deal/<id>/investability.

The "should we be in this deal at all" page. Combines two
pe_intelligence modules:

  - ``investability_scorer.score_investability(inputs)`` — composite
    0-100 score with opportunity / value / stability sub-scores,
    named strengths + weaknesses, and a letter grade.
  - ``exit_readiness.score_exit_readiness(ctx, inputs)`` — 12-
    dimension readiness check (audited financials, KPI reporting,
    data room, QoE, EBITDA trend, margin trend, buyer universe,
    management retention, legal, add-back recon, EBITDA vs plan,
    revenue vs plan) rolling up to a verdict: not_ready /
    needs_work / mostly_ready / exit_ready.

The investability composite is read off the PartnerReview
(already enriched by ``_enrich_secondary_analytics``); the exit
readiness module runs fresh because the review doesn't carry it.
Three-things-that-most-need-to-be-true uses the top 3 weaknesses
as a proxy for "what must be different for this thesis to work."
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional

from .._chartis_kit import (
    P,
    chartis_shell,
    ck_kpi_block,
    ck_section_header,
)
from ._helpers import (
    bullet_list,
    deal_header_nav,
    empty_note,
    fmt_pct,
    insufficient_data_banner,
    safe_dict,
    small_panel,
    verdict_badge,
)
from ._sanity import render_number


_GRADE_COLORS = {
    "A": P["positive"], "B": P["accent"], "C": P["warning"],
    "D": P["negative"], "F": P["critical"],
}

_READINESS_COLORS = {
    "exit_ready": P["positive"],
    "mostly_ready": P["accent"],
    "needs_work": P["warning"],
    "not_ready": P["negative"],
    "ready": P["positive"],  # alias, keep defensive
}

_FINDING_STATUS_COLORS = {
    "ready": P["positive"],
    "strong": P["positive"],
    "healthy": P["positive"],
    "unknown": P["text_faint"],
    "concern": P["warning"],
    "gap": P["warning"],
    "not_ready": P["negative"],
    "weak": P["negative"],
    "missing": P["negative"],
}


def _score_arc(score: int, grade: str) -> str:
    """Render a big score tile with grade + color band."""
    col = _GRADE_COLORS.get(grade.upper(), P["text_dim"])
    # Route through the sanity guard so out-of-0-100-range scores
    # surface as a warning pill rather than silently showing a
    # suspicious integer.
    score_html = render_number(score, "investability_score")
    return (
        f'<div style="display:flex;align-items:baseline;gap:18px;'
        f'padding:14px 18px;background:{P["panel"]};border:1px solid {col};'
        f'border-left-width:4px;border-radius:3px;margin-bottom:14px;">'
        f'<div style="font-family:var(--ck-mono);font-size:42px;font-weight:700;'
        f'color:{col};line-height:1;">{score_html}</div>'
        f'<div style="display:flex;flex-direction:column;">'
        f'<span style="font-family:var(--ck-mono);font-size:9px;'
        f'letter-spacing:0.15em;color:{P["text_faint"]};">COMPOSITE SCORE · 0-100</span>'
        f'<span style="font-family:var(--ck-mono);font-size:24px;font-weight:700;'
        f'color:{col};margin-top:4px;">GRADE {_html.escape(grade.upper())}</span>'
        f'</div>'
        f'</div>'
    )


def _subscore_bar(label: str, value: float, color: str) -> str:
    pct = max(0.0, min(1.0, float(value)))
    return (
        f'<div style="display:flex;align-items:center;gap:10px;padding:6px 0;'
        f'font-size:11.5px;">'
        f'<span style="width:150px;color:{P["text_dim"]};font-family:var(--ck-mono);'
        f'font-size:10px;letter-spacing:0.10em;">{_html.escape(label)}</span>'
        f'<span style="width:50px;text-align:right;color:{P["text"]};'
        f'font-family:var(--ck-mono);font-variant-numeric:tabular-nums;">'
        f'{pct*100:.1f}%</span>'
        f'<span style="flex:1;height:6px;background:{P["border_dim"]};'
        f'border-radius:1px;overflow:hidden;">'
        f'<span style="display:block;height:100%;width:{pct*100:.1f}%;'
        f'background:{color};"></span></span>'
        f'</div>'
    )


def _investability_panel(review: Any) -> str:
    inv = safe_dict(getattr(review, "investability", None))
    if not inv or inv.get("error"):
        err = inv.get("error") if isinstance(inv, dict) else None
        return empty_note(err or "Investability not computed.")
    score = int(inv.get("score", 0) or 0)
    grade = str(inv.get("grade", "—"))
    opportunity = float(inv.get("opportunity_score", 0.0) or 0.0)
    value = float(inv.get("value_score", 0.0) or 0.0)
    stability = float(inv.get("stability_score", 0.0) or 0.0)
    strengths = list(inv.get("strengths", None) or [])
    weaknesses = list(inv.get("weaknesses", None) or [])
    note = str(inv.get("partner_note", "") or "")

    subscores = (
        _subscore_bar("Opportunity", opportunity, P["accent"])
        + _subscore_bar("Value", value, P["warning"])
        + _subscore_bar("Stability", stability, P["positive"])
    )

    return (
        _score_arc(score, grade)
        + f'<div style="margin-bottom:12px;">{subscores}</div>'
        + (
            f'<p style="color:{P["text"]};font-size:12px;line-height:1.6;'
            f'margin-bottom:12px;">{_html.escape(note)}</p>'
            if note else ""
        )
        + f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;">'
        f'<div>'
        f'<div style="font-family:var(--ck-mono);font-size:9px;'
        f'letter-spacing:0.12em;color:{P["positive"]};margin-bottom:4px;">'
        f'STRENGTHS</div>'
        f'{bullet_list(strengths, color=P["text"])}'
        f'</div>'
        f'<div>'
        f'<div style="font-family:var(--ck-mono);font-size:9px;'
        f'letter-spacing:0.12em;color:{P["negative"]};margin-bottom:4px;">'
        f'WEAKNESSES</div>'
        f'{bullet_list(weaknesses, color=P["text"])}'
        f'</div>'
        f'</div>'
    )


def _exit_readiness_panel(report: Any) -> str:
    if report is None:
        return empty_note("Exit readiness was not computed.")
    score = int(getattr(report, "score", 0) or 0)
    verdict = str(getattr(report, "verdict", "—") or "—")
    col = _READINESS_COLORS.get(verdict, P["text_dim"])
    headline = str(getattr(report, "headline", "") or "")
    note = str(getattr(report, "partner_note", "") or "")
    findings = list(getattr(report, "findings", None) or [])

    finding_rows = []
    for f in findings:
        dim = _html.escape(str(getattr(f, "dimension", "—")))
        status = str(getattr(f, "status", "") or "")
        status_col = _FINDING_STATUS_COLORS.get(status, P["text_faint"])
        sc = getattr(f, "score", None)
        score_str = f"{sc:.0f}" if isinstance(sc, (int, float)) else "—"
        commentary = _html.escape(str(getattr(f, "commentary", "") or ""))
        weight = getattr(f, "weight", None)
        weight_str = f"{float(weight):.0%}" if weight is not None else ""
        finding_rows.append(
            f'<tr>'
            f'<td style="color:{P["text"]};font-family:var(--ck-mono);'
            f'font-size:11px;">{dim}</td>'
            f'<td>{verdict_badge(status.upper() or "—", color=status_col)}</td>'
            f'<td style="color:{P["text"]};font-family:var(--ck-mono);'
            f'font-size:11px;text-align:right;'
            f'font-variant-numeric:tabular-nums;">{score_str}</td>'
            f'<td style="color:{P["text_faint"]};font-family:var(--ck-mono);'
            f'font-size:10px;text-align:right;">{weight_str}</td>'
            f'<td style="color:{P["text_dim"]};font-size:11px;'
            f'line-height:1.45;white-space:normal;">{commentary or "—"}</td>'
            f'</tr>'
        )

    banner = (
        f'<div style="display:flex;gap:12px;align-items:baseline;'
        f'margin-bottom:10px;">'
        f'<span style="font-family:var(--ck-mono);font-size:28px;font-weight:700;'
        f'color:{col};line-height:1;">{score}</span>'
        f'<span style="font-family:var(--ck-mono);font-size:9px;'
        f'letter-spacing:0.15em;color:{P["text_faint"]};">EXIT READINESS · 0-100</span>'
        f'{verdict_badge(verdict.upper().replace("_", " "), color=col)}'
        f'</div>'
    )
    body = banner
    if headline:
        body += (
            f'<p style="color:{P["text"]};font-size:13px;font-weight:600;'
            f'margin-bottom:6px;">{_html.escape(headline)}</p>'
        )
    if note:
        body += (
            f'<p style="color:{P["text_dim"]};font-size:11.5px;line-height:1.55;'
            f'margin-bottom:10px;">{_html.escape(note)}</p>'
        )
    if finding_rows:
        body += (
            f'<div class="ck-table-wrap"><table class="ck-table">'
            f'<thead><tr>'
            f'<th>Dimension</th><th>Status</th><th class="num">Score</th>'
            f'<th class="num">Weight</th><th>Commentary</th>'
            f'</tr></thead><tbody>{"".join(finding_rows)}</tbody></table></div>'
        )
    else:
        body += empty_note("No readiness findings.")
    return body


def _three_things(review: Any, exit_report: Any) -> str:
    """'Three things that most need to be true for this to work.'

    Constructed from: investability weaknesses (top-3) augmented by
    any exit-readiness dimensions flagged 'not_ready' / 'weak'.
    """
    inv = safe_dict(getattr(review, "investability", None))
    weaknesses = list(inv.get("weaknesses", None) or [])
    items: List[str] = list(weaknesses[:3])
    if exit_report is not None:
        for f in getattr(exit_report, "findings", None) or []:
            status = str(getattr(f, "status", "") or "")
            if status in ("not_ready", "weak", "missing") and len(items) < 5:
                items.append(
                    f"Fix: {getattr(f, 'dimension', '—')} — "
                    f"{getattr(f, 'commentary', '') or 'no commentary'}"
                )
    if not items:
        return empty_note(
            "The brain did not surface a blocking set — either the packet is "
            "too thin to judge, or every dimension looks acceptable. Sanity-"
            "check the investability subscores above."
        )
    li = []
    for i, it in enumerate(items[:3], start=1):
        li.append(
            f'<li style="padding:6px 0;color:{P["text"]};font-size:12px;'
            f'line-height:1.55;border-bottom:1px solid {P["border_dim"]};">'
            f'<span style="font-family:var(--ck-mono);font-size:14px;'
            f'color:{P["accent"]};font-weight:700;margin-right:10px;">'
            f'{i}.</span>{_html.escape(str(it))}</li>'
        )
    return f'<ol style="list-style:none;padding:0;margin:0;">{"".join(li)}</ol>'


def render_investability(
    review: Any,
    deal_id: str,
    *,
    deal_name: str = "",
    exit_report: Any = None,
    error: Optional[str] = None,
    missing_fields: Optional[List[str]] = None,
    current_user: Optional[str] = None,
) -> str:
    label = deal_name or deal_id
    header = deal_header_nav(deal_id, active="investability")

    if error:
        body = header + insufficient_data_banner(
            deal_id,
            title="Investability",
            error=error,
            missing_fields=missing_fields,
        )
        return chartis_shell(
            body,
            title=f"Investability · {label}",
            active_nav="/pe-intelligence",
            subtitle=f"Investability unavailable for {label}",
        )

    inv = safe_dict(getattr(review, "investability", None))
    score = int(inv.get("score", 0) or 0)
    grade = str(inv.get("grade", "—"))
    inv_col = _GRADE_COLORS.get(grade.upper(), P["text_dim"])

    exit_score = int(getattr(exit_report, "score", 0) or 0) if exit_report else None
    exit_verdict = str(getattr(exit_report, "verdict", "—") or "—") if exit_report else "—"
    exit_col = _READINESS_COLORS.get(exit_verdict, P["text_dim"])

    kpis = (
        ck_kpi_block("Investability", f'{score}', f"grade {grade}")
        + ck_kpi_block("Exit Readiness", f'{exit_score}' if exit_score is not None else "—",
                        exit_verdict.replace("_", " "))
        + ck_kpi_block("Opportunity",
                        fmt_pct(inv.get("opportunity_score"), digits=0),
                        "0-100 sub-score")
        + ck_kpi_block("Value",
                        fmt_pct(inv.get("value_score"), digits=0),
                        "0-100 sub-score")
        + ck_kpi_block("Stability",
                        fmt_pct(inv.get("stability_score"), digits=0),
                        "0-100 sub-score")
    )
    kpi_strip = f'<div class="ck-kpi-grid">{kpis}</div>'

    body = (
        header
        + kpi_strip
        + small_panel(
            "Investability Composite",
            _investability_panel(review),
            code="INV",
        )
        + small_panel(
            "Exit Readiness",
            _exit_readiness_panel(exit_report),
            code="EXR",
        )
        + ck_section_header(
            "THREE THINGS THAT MOST NEED TO BE TRUE",
            "the shortest path to a 'proceed' — ranked by brain weakness signals",
        )
        + small_panel(
            "Critical-path items",
            _three_things(review, exit_report),
            code="CPI",
        )
    )

    return chartis_shell(
        body,
        title=f"Investability · {label}",
        active_nav="/pe-intelligence",
        subtitle=f"{label} · composite {score}/100 · exit {exit_verdict.replace('_', ' ')}",
    )
