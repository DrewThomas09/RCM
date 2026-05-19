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
    ck_page_title,
    ck_provenance_tooltip,
    ck_section_header,
)
_EXPLAINER_CSS = """<style>
.ck-stress-explainer{font-family:var(--sc-serif,'Georgia',serif);
  font-size:15px;line-height:1.55;color:var(--sc-text-dim,#4a4a4a);
  margin:0 0 var(--sc-s-6,18px) 0;max-width:72ch;}
.ck-stress-explainer em{color:var(--sc-teal-ink,#155752);font-style:italic;}
</style>"""

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


def _ebitda_delta_tornado(outcomes: List[Dict[str, Any]]) -> str:
    """Horizontal bar chart of EBITDA delta % per scenario.

    Each scenario gets a bar — pivoted around 0%. Negative deltas
    extend left in red; positive extend right in green. Bars
    sorted by delta (most negative on top) so the partner sees the
    "where this deal hurts" lineup at a glance.

    Bar opacity drops for scenarios that pass; failures get full
    opacity so the eye lands on them first.
    """
    plotted = [
        o for o in outcomes
        if isinstance(o.get("ebitda_delta_pct"), (int, float))
    ]
    if not plotted:
        return ""
    plotted = sorted(
        plotted, key=lambda o: float(o.get("ebitda_delta_pct") or 0),
    )

    width = 720
    row_h = 22
    pad_l, pad_r, pad_t, pad_b = 200, 24, 30, 40
    inner_w = width - pad_l - pad_r
    height = pad_t + len(plotted) * row_h + pad_b

    deltas = [float(o.get("ebitda_delta_pct") or 0) for o in plotted]
    max_abs = max(abs(d) for d in deltas) or 0.10
    # Round up to nearest 5% for clean axis
    axis_max = max(0.10, (int(max_abs * 100 + 4) // 5) * 0.05)

    zero_x = pad_l + (axis_max / (2 * axis_max)) * inner_w

    def sx(v: float) -> float:
        # Map [-axis_max, +axis_max] → [pad_l, pad_l + inner_w]
        return pad_l + (v + axis_max) / (2 * axis_max) * inner_w

    # Axis ticks at -axis_max, -axis_max/2, 0, +axis_max/2, +axis_max
    grid = []
    for v in (-axis_max, -axis_max / 2, 0, axis_max / 2, axis_max):
        x = sx(v)
        stroke = "#1a2332" if v == 0 else "#d6cfc0"
        sw = 1.2 if v == 0 else 0.8
        dash = "" if v == 0 else ' stroke-dasharray="2,4"'
        grid.append(
            f'<line x1="{x:.1f}" x2="{x:.1f}" '
            f'y1="{pad_t}" y2="{pad_t + len(plotted) * row_h}" '
            f'stroke="{stroke}" stroke-width="{sw}"{dash} />'
            f'<text x="{x:.1f}" y="{pad_t + len(plotted) * row_h + 16}" '
            f'fill="#7a8699" text-anchor="middle" font-size="10" '
            f'font-family="JetBrains Mono, monospace">'
            f'{v*100:+.0f}%</text>'
        )

    # Bars + labels
    elements = []
    for i, o in enumerate(plotted):
        cy = pad_t + i * row_h + row_h / 2
        delta = float(o.get("ebitda_delta_pct") or 0)
        passes = o.get("passes")
        breach = o.get("covenant_breach")
        # Color: red for negative (and brick-darker if covenant breach),
        # green for positive, dim for failed-but-positive (shouldn't
        # really happen but be defensive)
        if delta < 0:
            color = "#b5321e" if breach else "#b8732a"
        else:
            color = "#0a8a5f"
        # Opacity: full when fails (i.e. passes==False) so failures
        # pop visually; lighter when passes
        opacity = 0.85 if passes is False else 0.45
        x_left = sx(min(delta, 0))
        x_right = sx(max(delta, 0))
        bar_w = max(1.0, x_right - x_left)
        name = _html.escape(str(o.get("name", "—")).replace("_", " "))
        elements.append(
            f'<rect x="{x_left:.1f}" y="{cy - 8:.1f}" '
            f'width="{bar_w:.1f}" height="16" '
            f'fill="{color}" fill-opacity="{opacity}" '
            f'stroke="{color}" stroke-width="0.5">'
            f'<title>{name}: {delta*100:+.1f}% EBITDA · '
            f'{"passes" if passes else "FAILS"}'
            f'{" · covenant breach" if breach else ""}</title>'
            f'</rect>'
        )
        # Row label (left-padded scenario name)
        elements.append(
            f'<text x="{pad_l - 10:.1f}" y="{cy + 3:.1f}" '
            f'fill="#1a2332" text-anchor="end" font-size="11" '
            f'font-family="Inter, sans-serif">'
            f'{name}</text>'
        )
        # Inline value label at the bar end
        if delta < 0:
            label_x = x_left - 4
            anchor = "end"
        else:
            label_x = x_right + 4
            anchor = "start"
        elements.append(
            f'<text x="{label_x:.1f}" y="{cy + 3:.1f}" '
            f'fill="{color}" text-anchor="{anchor}" font-size="10" '
            f'font-family="JetBrains Mono, monospace" '
            f'font-weight="700">{delta*100:+.1f}%</text>'
        )

    axis_label = (
        f'<text x="{pad_l + inner_w / 2:.1f}" y="{height - 8}" '
        f'fill="#1a2332" text-anchor="middle" font-size="12" '
        f'font-family="Inter, sans-serif" font-weight="600">'
        f'EBITDA Δ vs. baseline (red = drag, green = lift)</text>'
    )

    return (
        f'<svg viewBox="0 0 {width} {height}" width="100%" '
        f'style="max-width:{width}px;background:transparent;'
        f'margin:8px 0 16px;">'
        f'{"".join(grid)}'
        f'{"".join(elements)}'
        f'{axis_label}'
        f'</svg>'
    )


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
        breadcrumbs=[
            ("Home", "/app"),
            ("Deals", "/deals"),
            ("Stress Grid", None),
        ],
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
        breadcrumbs=[
            ("Home", "/app"),
            ("Deals", "/deals"),
            ("Stress Grid", None),
        ],
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

    # Cycle 36 — wrap two key KPIs with provenance so the partner sees
    # the grade thresholds and the scenario universe without leaving
    # the page.
    grade_value = ck_provenance_tooltip(
        "Robustness grade",
        grade,
        explainer=(
            "A = >=90% downside pass and zero covenant breaches; "
            "B = >=80% pass and <=1 breach; C = >=60% pass; "
            "D = >=40%; F = below 40%. Source: "
            "pe_intelligence/stress_test.py::_robustness_grade."
        ),
    )
    pass_value = ck_provenance_tooltip(
        "Downside pass rate",
        fmt_pct(pass_rate, digits=0),
        explainer=(
            "Share of downside scenarios in the stress grid that "
            "leave EBITDA above the covenant threshold. Grid covers "
            "rate, volume, multiple-compression, lever-slip, and "
            "labor-shock shocks."
        ),
        inject_css=False,
    )
    kpis = (
        ck_kpi_block("Robustness", grade_value, "grade A-F")
        + ck_kpi_block("Downside Pass", pass_value, "of scenarios")
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

    page_title = ck_page_title(
        "Stress Grid",
        eyebrow=f"STRESS GRID · {_html.escape(deal_id)}",
        meta=(
            f"{_html.escape(label)} · grade {_html.escape(grade)} · "
            f"{pass_rate*100:.0f}% downside pass · "
            f"{n_breaches} breach{'es' if n_breaches != 1 else ''}"
        ),
    )
    stress_explainer = (
        '<p class="ck-stress-explainer">'
        f'<em>{_html.escape(label)}.</em> '
        "Where the deal breaks under pressure — downside, upside, baseline, "
        "and regulatory scenarios run against the live packet."
        "</p>"
    )
    # Horizontal-bar tornado of EBITDA Δ per scenario — partners
    # see "where the deal hurts" at a glance, sorted most-negative
    # on top. Tables below give the full per-scenario detail.
    tornado_svg = _ebitda_delta_tornado(outcomes)
    tornado_block = (
        ck_section_header(
            "EBITDA Δ TORNADO",
            "negative scenarios on top · red = covenant breach · "
            "full opacity = fails",
        ) + tornado_svg
    ) if tornado_svg else ""

    body = (
        page_title
        + stress_explainer
        + explainer
        + header
        + _grade_banner(grade, pass_rate, n_breaches, partner_summary)
        + kpi_strip
        + tornado_block
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
        breadcrumbs=[
            ("Home", "/app"),
            ("Deals", "/deals"),
            ("Stress Grid", None),
        ],
        extra_css=_EXPLAINER_CSS,
    )


def _fmt_delta_simple(v: Any) -> str:
    try:
        f = float(v)
        sign = "+" if f >= 0 else ""
        return f"{sign}{f*100:.1f}%"
    except (TypeError, ValueError):
        return "—"
