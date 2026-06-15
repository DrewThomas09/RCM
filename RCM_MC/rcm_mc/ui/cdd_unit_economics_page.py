"""Healthcare unit-economics spine page (/cdd/unit-economics).

Surfaces the unit-economics master spine (cdd features NEW-22 through NEW-26)
as one editorial reference page: the normalized log-scale comparison, the 2026
rate-update scorecard, payer economics, the commercial-to-Medicare multiplier,
and the market-concentration overlay. The page reads straight from the cdd
registry so the numbers, flags, and sourced footnotes are the same ones the
golden suite reconciles, and never drift from a hand-maintained copy.

Pure presentation: every figure comes from a registered Exhibit. The page
computes nothing of its own beyond the log-scale bar widths it draws.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Mapping

from rcm_mc.cdd import registry
from rcm_mc.ui._chartis_kit import (
    chartis_shell, ck_bar_row, ck_fmt_number,
    ck_kpi_block, ck_page_explainer, ck_page_title, ck_panel, ck_table,
    ck_signal_badge,
)

ROUTE = "/cdd/unit-economics"

# Exhibit flag severity to badge tone.
_FLAG_TONE = {"info": "neutral", "warn": "warning", "risk": "negative"}


def _usd(v: float) -> str:
    """Exact dollars to two decimals with thousands separators.

    The shared ck_fmt_currency abbreviates above 1000 ($51K), which would hide
    the exact final-rule anchors this reference page exists to show, so the
    page formats dollars itself.
    """
    return (f"-${abs(v):,.2f}" if v < 0 else f"${v:,.2f}")


def _pct(v: float) -> str:
    """Percent-unit value to one decimal. The shared ck_fmt_percent multiplies
    by 100 (it expects a fraction); these figures are already in percent units.
    """
    return f"{v:.1f}%"


def _flags_html(rendered: Mapping[str, Any]) -> str:
    """Render an exhibit's flags as editorial badges, severity-toned."""
    badges = [
        ck_signal_badge(f["message"], tone=_FLAG_TONE.get(f["severity"], "neutral"))
        for f in rendered.get("flags", [])
    ]
    if not badges:
        return ""
    return '<div class="ue-flags">' + " ".join(badges) + "</div>"


def _footnote_html(rendered: Mapping[str, Any]) -> str:
    """Render the sourced footnote line and the key assumptions."""
    fn = rendered.get("footnote") or {}
    src = fn.get("source", "")
    vintage = fn.get("vintage", "")
    assumptions = fn.get("assumptions", []) or []
    parts = []
    if src or vintage:
        parts.append(
            f'<div class="ue-source">Source: {src}'
            + (f" &middot; Vintage: {vintage}" if vintage else "")
            + "</div>"
        )
    if assumptions:
        items = "".join(f"<li>{a}</li>" for a in assumptions)
        parts.append(f'<ul class="ue-assumptions">{items}</ul>')
    return "".join(parts)


def _log_pct(value: float, lo: float, hi: float) -> float:
    """Position of a value on a log axis from lo to hi, as 0 to 100."""
    if value <= 0 or lo <= 0 or hi <= lo:
        return 2.0
    return (math.log10(value) - math.log10(lo)) / (math.log10(hi) - math.log10(lo)) * 100.0


def _spine_panel() -> str:
    ex = registry.get("NEW-22").demo()
    r = ex.render(internal_mode=True)
    meta = r["meta"]
    table = meta["table"]
    lo, hi = meta["min_representative"], meta["max_representative"]
    # Bars run high to low so the spine reads top-down from the costliest unit.
    bars = []
    for p in sorted(table, key=lambda x: x["value"], reverse=True):
        rng = (f"{_usd(p['low'])} to {_usd(p['high'])}") if p["is_range"] else ""
        label = p["label"] + (" (estimate)" if p["est_verify"] else "")
        tone = "warning" if p["est_verify"] else "teal"
        bars.append(ck_bar_row(
            label,
            _usd(p["value"]) + f"  /  {p['natural_unit']}",
            _log_pct(p["value"], lo, hi),
            tone=tone,
            unit=(f"   [{rng}]" if rng else ""),
        ))
    note = ('<p class="ue-axis-note">Bars are positioned on a log axis. '
            'Amber rows are secondary-source estimates shown as ranges.</p>')
    body = note + '<div class="ue-bars">' + "".join(bars) + "</div>"
    body += _flags_html(r) + _footnote_html(r)
    return ck_panel(body, title=r["title"], code="NEW-22")


def _scorecard_panel() -> str:
    ex = registry.get("NEW-23").demo()
    r = ex.render(internal_mode=True)
    pts = r["series"][0]["points"]
    lo = min(p["value"] for p in pts)
    hi = max(p["value"] for p in pts)
    span = max(abs(lo), abs(hi)) or 1.0
    bars = []
    for p in pts:  # already sorted ascending by the exhibit
        tone = "negative" if p["value"] < 0 else "positive"
        bars.append(ck_bar_row(
            p["label"],
            ("+" if p["value"] >= 0 else "") + _pct(p["value"]),
            abs(p["value"]) / span * 100.0,
            tone=tone,
            unit=f"   {p['rule']}",
        ))
    body = '<div class="ue-bars">' + "".join(bars) + "</div>"
    body += _flags_html(r) + _footnote_html(r)
    return ck_panel(body, title=r["title"], code="NEW-23")


def _payer_panel() -> str:
    ex = registry.get("NEW-24").demo()
    r = ex.render(internal_mode=True)
    pts = r["series"][0]["points"]
    rows = [{
        "segment": p["label"],
        "m24": _usd(p["value"]),
        "m23": _usd(p["margin_2023"]),
        "yoy": _usd(p["yoy_change"]),
        "mlr": _pct(p["mlr_pct"]),
    } for p in pts]
    columns = [
        {"key": "segment", "label": "Segment", "align": "left"},
        {"key": "m24", "label": "2024 margin/enrollee", "align": "right"},
        {"key": "m23", "label": "2023", "align": "right"},
        {"key": "yoy", "label": "YoY", "align": "right"},
        {"key": "mlr", "label": "MLR %", "align": "right"},
    ]
    body = ck_table(rows, columns)
    body += _flags_html(r) + _footnote_html(r)
    return ck_panel(body, title=r["title"], code="NEW-24")


def _multiplier_panel() -> str:
    ex = registry.get("NEW-25").demo()
    r = ex.render(internal_mode=True)
    anchors = r["meta"]["anchors"]
    rows = [{
        "anchor": a["label"],
        "medicare": _usd(a["medicare"]),
        "ratio": _pct(a["ratio_pct"]),
        "commercial": _usd(a["commercial_estimate"]),
    } for a in anchors]
    columns = [
        {"key": "anchor", "label": "Medicare anchor", "align": "left"},
        {"key": "medicare", "label": "Medicare", "align": "right"},
        {"key": "ratio", "label": "RAND ratio %", "align": "right"},
        {"key": "commercial", "label": "Commercial estimate", "align": "right"},
    ]
    body = ck_table(rows, columns)
    body += _flags_html(r) + _footnote_html(r)
    return ck_panel(body, title=r["title"], code="NEW-25")


def _concentration_panel() -> str:
    ex = registry.get("NEW-26").demo()
    r = ex.render(internal_mode=True)
    pts = r["series"][0]["points"]  # sorted descending by share
    bars = []
    for p in pts:
        tone = "negative" if p["value"] >= 70.0 else "teal"
        label = p["label"] + (" (estimate)" if p["est_verify"] else "")
        bars.append(ck_bar_row(
            label,
            _pct(p["value"]),
            p["value"],
            tone=tone,
            unit=f"   {ck_fmt_number(p['firms'])} firms",
        ))
    body = '<div class="ue-bars">' + "".join(bars) + "</div>"
    body += _flags_html(r) + _footnote_html(r)
    return ck_panel(body, title=r["title"], code="NEW-26")


def _kpis() -> str:
    spine = registry.get("NEW-22").demo().meta
    payer = registry.get("NEW-24").demo().meta
    conc = registry.get("NEW-26").demo().meta
    blocks = [
        ck_kpi_block("Verticals on the spine", ck_fmt_number(spine["n_rows"]),
                     f"{spine['n_estimates']} secondary-source estimates"),
        ck_kpi_block("Orders of magnitude",
                     f"{spine['orders_of_magnitude']:.1f}",
                     f"{_usd(spine['min_representative'])} to "
                     f"{_usd(spine['max_representative'])}"),
        ck_kpi_block("Top payer margin",
                     _usd(payer["leader_margin"]),
                     f"{payer['leader']}, per enrollee"),
        ck_kpi_block("Highly concentrated",
                     ck_fmt_number(conc["n_highly_concentrated"]),
                     f"of {conc['n_rows']} verticals at or above 70%"),
    ]
    return '<div class="ck-kpi-grid">' + "".join(blocks) + "</div>"


_CSS = """
<style>
.ue-bars { display: flex; flex-direction: column; gap: 4px; margin: 6px 0 10px; }
.ue-axis-note, .ue-source { font-size: 12px; color: #4a5568; margin: 4px 0; }
.ue-flags { display: flex; flex-wrap: wrap; gap: 6px; margin: 10px 0 6px; }
.ue-assumptions { margin: 4px 0 0; padding-left: 18px; font-size: 12px; color: #4a5568; }
.ue-assumptions li { margin: 2px 0; }
.ck-kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; margin-bottom: 18px; }
</style>"""


def render_cdd_unit_economics(params: dict = None) -> str:
    """Render the unit-economics spine reference page."""
    spine = registry.get("NEW-22").demo().meta
    title = ck_page_title(
        "Healthcare Unit Economics",
        eyebrow="DILIGENCE / CDD / UNIT-ECONOMICS SPINE",
        meta=(f"{spine['n_rows']} verticals on one normalized spine &middot; "
              "2026 final-rule anchors &middot; spans "
              f"{spine['orders_of_magnitude']:.1f} orders of magnitude"),
    )
    explainer = ck_page_explainer(
        "The cost of treating one patient, on one comparable spine.",
        "Every vertical stores its natural unit and a 2026 dollar figure, "
        "either a verified final-rule anchor or a sourced range. The five "
        "panels below read straight from the diligence analytics registry, so "
        "the figures, flags, and sources are the same ones the golden suite "
        "reconciles. Secondary-source estimates are flagged and shown as "
        "ranges, not points, until a primary source is confirmed.",
    )
    body = (
        '<div class="ck-page-wrap">'
        + title + explainer + _kpis()
        + _spine_panel()
        + _scorecard_panel()
        + _payer_panel()
        + _multiplier_panel()
        + _concentration_panel()
        + "</div>"
    )
    return chartis_shell(body, title="Healthcare Unit Economics",
                         active_nav=ROUTE, extra_css=_CSS)
