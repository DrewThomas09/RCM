"""Per-deal Stress Grid — /deal/<id>/stress.

Renders ``pe_intelligence.stress_test.run_stress_grid`` output — the
"what if everything goes wrong" page. Each scenario shows whether the
deal passes, the EBITDA delta, and whether covenants would breach.

The review already carries ``stress_scenarios`` via
``_enrich_secondary_analytics``; we group outcomes by severity
(downside / upside / baseline) for display.
"""
from __future__ import annotations

import html as _html
from collections import defaultdict
from typing import Any, Dict, List, Optional

from .._chartis_kit import (
    P,
    chartis_shell,
    ck_kpi_block,
    ck_section_header,
)
from ._helpers import (
    deal_header_nav,
    empty_note,
    fmt_pct,
    insufficient_data_banner,
    render_page_explainer,
    safe_dict,
    small_panel,
    verdict_badge,
)


_GRADE_COLORS = {
    "A": P["positive"],
    "B": P["accent"],
    "C": P["warning"],
    "D": P["negative"],
    "F": P["critical"],
}

_SEVERITY_LABELS = {
    "downside": ("DOWNSIDE", P["negative"]),
    "upside": ("UPSIDE", P["positive"]),
    "baseline": ("BASELINE", P["text_dim"]),
    "regulatory": ("REGULATORY", P["warning"]),
}


def _pass_badge(passes: Any) -> str:
    if passes is True:
        return verdict_badge("PASS", color=P["positive"])
    if passes is False:
        return verdict_badge("FAIL", color=P["negative"])
    return verdict_badge("—", color=P["text_faint"])


def _breach_badge(breach: Any) -> str:
    if breach is True:
        return verdict_badge("BREACH", color=P["critical"])
    if breach is False:
        return verdict_badge("OK", color=P["positive"])
    return verdict_badge("—", color=P["text_faint"])


def _fmt_delta(val: Any) -> str:
    try:
        f = float(val)
        sign = "+" if f >= 0 else ""
        col = P["positive"] if f >= 0 else (P["negative"] if f < -0.05 else P["warning"])
        return (
            f'<span style="color:{col};font-family:var(--ck-mono);'
            f'font-variant-numeric:tabular-nums;">{sign}{f*100:.1f}%</span>'
        )
    except (TypeError, ValueError):
        return f'<span style="color:{P["text_faint"]};">—</span>'


def _scenario_row(out: Dict[str, Any]) -> str:
    name = _html.escape(str(out.get("name", "—")))
    passes = out.get("passes")
    breach = out.get("covenant_breach")
    delta = out.get("ebitda_delta_pct")
    note = _html.escape(str(out.get("partner_note", "") or ""))
    severity = str(out.get("severity", "") or "").lower()
    sev_label, sev_col = _SEVERITY_LABELS.get(severity, (severity.upper(), P["text_dim"]))
    return (
        f'<tr>'
        f'<td style="font-family:var(--ck-mono);font-size:11px;color:{P["text"]};">'
        f'{name.replace("_", " ")}</td>'
        f'<td>{verdict_badge(sev_label, color=sev_col)}</td>'
        f'<td style="text-align:right;">{_fmt_delta(delta)}</td>'
        f'<td>{_pass_badge(passes)}</td>'
        f'<td>{_breach_badge(breach)}</td>'
        f'<td style="color:{P["text_dim"]};font-size:11px;line-height:1.45;'
        f'white-space:normal;">{note or "—"}</td>'
        f'</tr>'
    )


def _grade_banner(grade: str, pass_rate: float, n_breaches: int, partner_summary: str) -> str:
    col = _GRADE_COLORS.get(grade.upper(), P["text_dim"])
    return (
        f'<div style="background:{P["panel"]};border:1px solid {col};'
        f'border-left-width:4px;border-radius:3px;padding:14px 18px;'
        f'margin-bottom:14px;">'
        f'<div style="display:flex;gap:12px;align-items:baseline;margin-bottom:8px;">'
        f'<span style="font-family:var(--ck-mono);font-size:9px;'
        f'color:{P["text_faint"]};letter-spacing:0.15em;">ROBUSTNESS GRADE</span>'
        f'<span style="font-family:var(--ck-mono);font-size:26px;font-weight:700;'
        f'color:{col};letter-spacing:0.04em;">{_html.escape(grade.upper())}</span>'
        f'<span style="font-family:var(--ck-mono);font-size:10px;'
        f'color:{P["text_faint"]};margin-left:auto;">'
        f'{pass_rate*100:.0f}% downside pass-rate · '
        f'{n_breaches} covenant breach{"es" if n_breaches != 1 else ""}</span>'
        f'</div>'
        + (
            f'<p style="color:{P["text"]};font-size:12px;line-height:1.6;">'
            f'{_html.escape(partner_summary)}</p>' if partner_summary else ""
        )
        + f'</div>'
    )


def render_stress(
    review: Any,
    deal_id: str,
    *,
    deal_name: str = "",
    error: Optional[str] = None,
    missing_fields: Optional[List[str]] = None,
    current_user: Optional[str] = None,
) -> str:
    label = deal_name or deal_id
    header = deal_header_nav(deal_id, active="stress")

    if error:
        body = header + insufficient_data_banner(
            deal_id,
            title="Stress grid",
            error=error,
            missing_fields=missing_fields,
        )
        return chartis_shell(
            body,
            title=f"Stress Grid · {label}",
            active_nav="/pe-intelligence",
            subtitle=f"Stress grid unavailable for {label}",
        )

    sg = safe_dict(getattr(review, "stress_scenarios", None))
    if not sg or sg.get("error"):
        err = sg.get("error") if isinstance(sg, dict) else None
        body = header + small_panel(
            "Stress grid — not scored",
            empty_note(err or "Stress grid could not be computed."),
            code="N/A",
        )
        return chartis_shell(
            body,
            title=f"Stress Grid · {label}",
            active_nav="/pe-intelligence",
            subtitle=f"{label} · stress grid unavailable",
        )

    outcomes = list(sg.get("outcomes", None) or [])
    pass_rate = float(sg.get("downside_pass_rate", 0.0) or 0.0)
    upside_capture = float(sg.get("upside_capture_rate", 0.0) or 0.0)
    worst_case = sg.get("worst_case_delta_pct")
    best_case = sg.get("best_case_delta_pct")
    n_breaches = int(sg.get("n_covenant_breaches", 0) or 0)
    grade = str(sg.get("robustness_grade", "—") or "—")
    partner_summary = str(sg.get("partner_summary", "") or "")

    by_sev: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for o in outcomes:
        by_sev[str(o.get("severity", "") or "").lower()].append(o)

    kpis = (
        ck_kpi_block("Robustness", grade, "grade A-F")
        + ck_kpi_block("Downside Pass", fmt_pct(pass_rate, digits=0), "of scenarios")
        + ck_kpi_block("Upside Capture", fmt_pct(upside_capture, digits=0), "of scenarios")
        + ck_kpi_block("Covenant Breaches", str(n_breaches), "across grid")
        + ck_kpi_block("Worst Case",
                        _fmt_delta_simple(worst_case),
                        "EBITDA delta")
        + ck_kpi_block("Best Case",
                        _fmt_delta_simple(best_case),
                        "EBITDA delta")
    )
    kpi_strip = f'<div class="ck-kpi-grid">{kpis}</div>'

    def _section(sev_key: str, title: str) -> str:
        rows = by_sev.get(sev_key, [])
        if not rows:
            return small_panel(title, empty_note("No scenarios in this severity."), code=sev_key.upper()[:3])
        body = (
            f'<div class="ck-table-wrap"><table class="ck-table">'
            f'<thead><tr><th>Scenario</th><th>Severity</th>'
            f'<th class="num">EBITDA Δ</th><th>Passes</th><th>Covenant</th>'
            f'<th>Partner Note</th></tr></thead>'
            f'<tbody>{"".join(_scenario_row(o) for o in rows)}</tbody></table></div>'
        )
        return small_panel(f"{title} ({len(rows)})", body, code=sev_key.upper()[:3])

    explainer = render_page_explainer(
        what=(
            "Runs a grid of rate, volume, multiple-compression, "
            "lever-slip, and labor-shock scenarios against this deal "
            "and scores the deal's robustness across the grid."
        ),
        scale=(
            "Robustness grade: A = ≥ 90% downside pass rate and zero "
            "covenant breaches; B = ≥ 80% pass rate and ≤ 1 breach; "
            "C = ≥ 60% pass rate; D = ≥ 40%; F = below 40%."
        ),
        use=(
            "Use downside pass rate + breach count to size covenant "
            "headroom and stress reserves. A grade-D deal needs more "
            "cushion in the capital structure or should not proceed "
            "at this leverage."
        ),
        source=(
            "pe_intelligence/stress_test.py::_robustness_grade "
            "(grade thresholds); run_stress_grid (scenario set)."
        ),
        page_key="deal-stress",
    )

    body = (
        explainer
        + header
        + _grade_banner(grade, pass_rate, n_breaches, partner_summary)
        + kpi_strip
        + ck_section_header(
            "SCENARIO GRID", "downside + upside + baseline sweep",
            count=len(outcomes),
        )
        + _section("downside", "Downside scenarios")
        + _section("upside", "Upside scenarios")
        + _section("baseline", "Baseline scenarios")
        + _section("regulatory", "Regulatory scenarios")
    )

    return chartis_shell(
        body,
        title=f"Stress Grid · {label}",
        active_nav="/pe-intelligence",
        subtitle=f"{label} · grade {grade} · {pass_rate*100:.0f}% downside pass · "
                 f"{n_breaches} breach{'es' if n_breaches != 1 else ''}",
    )


def _fmt_delta_simple(v: Any) -> str:
    try:
        f = float(v)
        sign = "+" if f >= 0 else ""
        return f"{sign}{f*100:.1f}%"
    except (TypeError, ValueError):
        return "—"
