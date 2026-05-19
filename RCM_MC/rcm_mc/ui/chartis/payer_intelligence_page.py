"""Payer Intelligence — /payer-intelligence.

Comprehensive payer-mix view. Calls
``data_public/payer_intelligence.compute_payer_intelligence(corpus)``
to produce:

  - Corpus-wide payer mix averages (commercial / medicare / medicaid /
    self-pay).
  - Correlation of commercial %, medicaid %, and self-pay % against
    realized MOIC — the "does payer mix predict outcomes" read.
  - Four payer-mix regime bands (Gov-heavy / Balanced / Commercial-mix
    / Commercial) with per-band MOIC P25/P50/P75, IRR median, deal
    count, and loss rate.

Distinct from the existing ``/payer-intel`` (thinner summary); this
page is the comprehensive view and the older page links here as
"more detail".
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional

from .._chartis_kit import (
    P,
    chartis_shell,
    ck_kpi_block,
    ck_page_title,
    ck_section_header,
)
from ._helpers import (
    empty_note,
    fmt_multiple,
    fmt_pct,
    load_corpus_deals,
    small_panel,
    verdict_badge,
)
from ._sanity import render_number


_EXPLAINER_CSS = """
.ck-pi-explainer{font-family:var(--sc-serif);font-size:15px;line-height:1.6;
color:var(--sc-text-dim);max-width:68ch;
margin:var(--sc-s-4) 0 var(--sc-s-6);}
.ck-pi-explainer em{color:var(--sc-teal-ink);font-style:italic;}
"""


_REGIME_COLORS = {
    "Gov-heavy":        P["warning"],
    "Balanced":         P["accent"],
    "Commercial-mix":   P["positive"],
    "Commercial":       P["positive"],
}


def _fmt_corr(val: Any) -> str:
    try:
        f = float(val)
        if abs(f) < 0.1:
            col = P["text_faint"]
        elif f > 0:
            col = P["positive"]
        else:
            col = P["negative"]
        sign = "+" if f >= 0 else ""
        return (
            f'<span style="color:{col};font-family:var(--ck-mono);'
            f'font-variant-numeric:tabular-nums;">{sign}{f:.3f}</span>'
        )
    except (TypeError, ValueError):
        return f'<span style="color:{P["text_faint"]};">—</span>'


def _mix_bar(commercial: float, medicare: float, medicaid: float, self_pay: float) -> str:
    segments = [
        ("Commercial", commercial, P["positive"]),
        ("Medicare", medicare, P["accent"]),
        ("Medicaid", medicaid, P["warning"]),
        ("Self-pay", self_pay, P["negative"]),
    ]
    bars = []
    legend = []
    for label, val, col in segments:
        pct = max(0.0, min(1.0, float(val or 0.0)))
        if pct > 0:
            bars.append(
                f'<span style="display:inline-block;height:100%;width:{pct*100:.2f}%;'
                f'background:{col};" title="{label} {pct*100:.1f}%"></span>'
            )
        legend.append(
            f'<span style="display:inline-flex;gap:6px;align-items:center;'
            f'margin-right:14px;font-family:var(--ck-mono);font-size:11px;">'
            f'<span style="width:10px;height:10px;background:{col};'
            f'border-radius:1px;"></span>'
            f'<span style="color:{P["text_dim"]};">{label}</span>'
            f'<span style="color:{P["text"]};font-variant-numeric:tabular-nums;">'
            f'{pct*100:.1f}%</span>'
            f'</span>'
        )
    return (
        f'<div style="height:18px;background:{P["border_dim"]};border-radius:2px;'
        f'overflow:hidden;display:flex;">{"".join(bars)}</div>'
        f'<div style="margin-top:8px;">{"".join(legend)}</div>'
    )


def _regime_moic_boxplot(regime_stats: List[Any]) -> str:
    """SVG box-and-whisker of MOIC distribution per payer-mix regime.

    Each regime gets a box from P25 → P75 with a P50 marker line.
    Partner reads:
      - height of box   = spread of outcomes within the regime
      - line in the box = median MOIC
      - color of box    = MOIC band (green ≥2.5x, amber 1.5–2.5x,
                          red <1.5x) keyed off P50

    Glanceable answer to "which payer mix delivers tight returns vs
    a wide range of outcomes?" without scanning columns.
    """
    if not regime_stats:
        return ""
    width = 720
    height = 280
    pad_l, pad_r, pad_t, pad_b = 60, 24, 32, 56
    inner_w = width - pad_l - pad_r
    inner_h = height - pad_t - pad_b
    n = len(regime_stats)
    box_w = max(20.0, inner_w / max(n, 1) * 0.55)
    step = inner_w / max(n, 1)

    # Y scale: 0 to max(P75 + 0.3, 3.0)
    max_p75 = max((float(rs.moic_p75) for rs in regime_stats), default=3.0)
    y_max = max(max_p75 + 0.3, 3.0)

    def sy(v: float) -> float:
        return pad_t + inner_h - (v / y_max) * inner_h

    # Reference gridlines at MOIC = 1, 2, 3 (and the implicit 1.0
    # break-even line stands out as the lower bound for "made money")
    grid = []
    for v in (1.0, 2.0, 3.0):
        if v > y_max:
            continue
        y = sy(v)
        grid.append(
            f'<line x1="{pad_l}" x2="{pad_l + inner_w}" '
            f'y1="{y:.1f}" y2="{y:.1f}" stroke="#d6cfc0" '
            f'stroke-dasharray="2,4" />'
            f'<text x="{pad_l - 6}" y="{y + 3:.1f}" '
            f'fill="#7a8699" text-anchor="end" font-size="10" '
            f'font-family="JetBrains Mono, monospace">{v:.1f}x</text>'
        )

    # Boxes (P25 → P75) + median line + regime label below
    elements = []
    for i, rs in enumerate(regime_stats):
        cx = pad_l + step * i + step / 2
        x = cx - box_w / 2
        y_p25 = sy(float(rs.moic_p25))
        y_p50 = sy(float(rs.moic_p50))
        y_p75 = sy(float(rs.moic_p75))
        # Color by P50 band
        p50 = float(rs.moic_p50)
        color = (
            "#0a8a5f" if p50 >= 2.5
            else "#b8732a" if p50 >= 1.5
            else "#b5321e"
        )
        # Box (P25 to P75 — note SVG y grows downward so P75 is on top)
        elements.append(
            f'<rect x="{x:.1f}" y="{y_p75:.1f}" '
            f'width="{box_w:.1f}" height="{y_p25 - y_p75:.1f}" '
            f'fill="{color}" fill-opacity="0.20" '
            f'stroke="{color}" stroke-width="1.5">'
            f'<title>{_html.escape(str(rs.regime))}: '
            f'P25 {float(rs.moic_p25):.2f}x · '
            f'P50 {p50:.2f}x · '
            f'P75 {float(rs.moic_p75):.2f}x · '
            f'{rs.n_deals} deals · '
            f'loss {float(rs.loss_rate)*100:.0f}%</title>'
            f'</rect>'
        )
        # Median (P50) line — thicker
        elements.append(
            f'<line x1="{x:.1f}" x2="{x + box_w:.1f}" '
            f'y1="{y_p50:.1f}" y2="{y_p50:.1f}" '
            f'stroke="{color}" stroke-width="3" />'
        )
        # P50 value label above the box
        elements.append(
            f'<text x="{cx:.1f}" y="{y_p75 - 6:.1f}" '
            f'fill="{color}" text-anchor="middle" font-size="11" '
            f'font-family="JetBrains Mono, monospace" '
            f'font-weight="700">{p50:.1f}x</text>'
        )
        # Regime label below the axis (two lines: name + n_deals)
        elements.append(
            f'<text x="{cx:.1f}" y="{height - pad_b + 16}" '
            f'fill="#1a2332" text-anchor="middle" font-size="11" '
            f'font-family="Inter, sans-serif" font-weight="600">'
            f'{_html.escape(str(rs.regime))}</text>'
        )
        elements.append(
            f'<text x="{cx:.1f}" y="{height - pad_b + 30}" '
            f'fill="#7a8699" text-anchor="middle" font-size="10" '
            f'font-family="JetBrains Mono, monospace">'
            f'n={rs.n_deals}</text>'
        )

    axis_label = (
        f'<text x="16" y="{pad_t + inner_h/2:.1f}" '
        f'fill="#1a2332" text-anchor="middle" font-size="12" '
        f'font-family="Inter, sans-serif" font-weight="600" '
        f'transform="rotate(-90 16 {pad_t + inner_h/2:.1f})">'
        f'MOIC distribution (P25 → P75, median line)</text>'
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


def _regime_row(rs: Any) -> str:
    regime = str(rs.regime)
    col = _REGIME_COLORS.get(regime, P["text_dim"])
    commercial_range = rs.commercial_range
    if isinstance(commercial_range, (list, tuple)) and len(commercial_range) == 2:
        lo, hi = commercial_range
        try:
            range_str = f"{float(lo)*100:.0f}-{float(hi)*100:.0f}% commercial"
        except (TypeError, ValueError):
            range_str = "—"
    else:
        range_str = "—"

    # Color MOIC p50 by band
    p50 = rs.moic_p50 or 0
    p50_col = P["positive"] if p50 >= 2.5 else (P["warning"] if p50 >= 1.5 else P["negative"])

    loss_col = P["negative"] if (rs.loss_rate or 0) > 0.30 else P["text"]

    return (
        f'<tr>'
        f'<td style="color:{col};font-family:var(--ck-mono);font-weight:700;'
        f'font-size:12px;letter-spacing:0.04em;">{_html.escape(regime)}</td>'
        f'<td style="color:{P["text_dim"]};font-family:var(--ck-mono);'
        f'font-size:11px;">{_html.escape(range_str)}</td>'
        f'<td style="text-align:right;font-family:var(--ck-mono);'
        f'font-variant-numeric:tabular-nums;color:{P["text"]};" data-val="{rs.n_deals}">'
        f'{rs.n_deals}</td>'
        f'<td style="text-align:right;" '
        f'data-val="{rs.moic_p25 or 0}">{render_number(rs.moic_p25, "moic")}</td>'
        f'<td style="text-align:right;font-weight:600;" '
        f'data-val="{p50}">{render_number(p50, "moic")}</td>'
        f'<td style="text-align:right;" '
        f'data-val="{rs.moic_p75 or 0}">{render_number(rs.moic_p75, "moic")}</td>'
        f'<td style="text-align:right;" '
        f'data-val="{rs.irr_p50 or 0}">{render_number(rs.irr_p50, "irr")}</td>'
        f'<td style="text-align:right;" '
        f'data-val="{rs.loss_rate or 0}">{render_number(rs.loss_rate, "loss_rate")}</td>'
        f'<td style="text-align:center;">'
        + _mini_mix_bar(
            rs.avg_commercial_pct or 0, rs.avg_medicare_pct or 0,
            rs.avg_medicaid_pct or 0,
            # self-pay is whatever's left
            max(0.0, 1.0 - float((rs.avg_commercial_pct or 0) + (rs.avg_medicare_pct or 0)
                                 + (rs.avg_medicaid_pct or 0))),
        )
        + f'</td>'
        f'</tr>'
    )


def _mini_mix_bar(commercial: float, medicare: float, medicaid: float, self_pay: float) -> str:
    segs = [
        (commercial, P["positive"]),
        (medicare, P["accent"]),
        (medicaid, P["warning"]),
        (self_pay, P["negative"]),
    ]
    cells = "".join(
        f'<span style="display:inline-block;height:100%;width:{max(0.0, min(1.0, float(v)))*100:.1f}%;'
        f'background:{col};"></span>'
        for v, col in segs
    )
    return (
        f'<span style="display:inline-block;height:10px;width:140px;'
        f'background:{P["border_dim"]};border-radius:1px;overflow:hidden;">'
        f'{cells}</span>'
    )


def render_payer_intelligence(
    store: Any = None,
    current_user: Optional[str] = None,
) -> str:
    def _title(meta: str) -> str:
        return ck_page_title(
            "Payer Intelligence",
            eyebrow="PAYER INTELLIGENCE",
            meta=meta,
        )
    explainer_html = (
        '<p class="ck-pi-explainer">'
        '<em>What the payer mix is really telling you.</em> '
        "Corpus-wide payer-mix averages, commercial-share × MOIC "
        "correlations, and a four-regime breakdown (Gov-heavy / "
        "Balanced / Commercial-mix / Commercial) with per-band MOIC "
        "quartiles, IRR, and loss rate. Use this to read whether a "
        "deal's payer mix is load-bearing or incidental to the thesis."
        '</p>'
    )

    try:
        from ...data_public.payer_intelligence import compute_payer_intelligence
    except Exception as exc:  # noqa: BLE001
        body = small_panel(
            "Payer intelligence unavailable",
            empty_note(f"payer_intelligence module failed: {exc!r}"),
            code="ERR",
        )
        return chartis_shell(
            _title("module unavailable") + explainer_html + body,
            title="Payer Intelligence",
            active_nav="/payer-intelligence",
            extra_css=_EXPLAINER_CSS,
        )

    corpus = load_corpus_deals()
    if not corpus:
        body = small_panel(
            "Payer intelligence — no corpus",
            empty_note("No corpus deals available to analyze."),
            code="NIL",
        )
        return chartis_shell(
            _title("no corpus available") + explainer_html + body,
            title="Payer Intelligence",
            active_nav="/payer-intelligence",
            extra_css=_EXPLAINER_CSS,
        )

    try:
        pi = compute_payer_intelligence(corpus)
    except Exception as exc:  # noqa: BLE001
        body = small_panel(
            "Payer intelligence failed",
            empty_note(f"compute_payer_intelligence raised: {exc!r}"),
            code="ERR",
        )
        return chartis_shell(
            _title("analysis raised an error") + explainer_html + body,
            title="Payer Intelligence",
            active_nav="/payer-intelligence",
            extra_css=_EXPLAINER_CSS,
        )

    commercial = float(pi.avg_commercial or 0)
    medicare = float(pi.avg_medicare or 0)
    medicaid = float(pi.avg_medicaid or 0)
    self_pay = float(pi.avg_self_pay or 0)


    kpis = (
        ck_kpi_block("Commercial %", fmt_pct(commercial), "corpus average")
        + ck_kpi_block("Medicare %", fmt_pct(medicare), "corpus average")
        + ck_kpi_block("Medicaid %", fmt_pct(medicaid), "corpus average")
        + ck_kpi_block("Self-pay %", fmt_pct(self_pay), "corpus average")
    )
    kpi_strip = f'<div class="ck-kpi-grid">{kpis}</div>'

    mix_panel = small_panel(
        "Corpus-wide payer mix",
        _mix_bar(commercial, medicare, medicaid, self_pay),
        code="MIX",
    )

    corr_panel = small_panel(
        "Payer-mix vs MOIC correlation",
        (
            f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;">'
            f'<div>'
            f'<div style="font-family:var(--ck-mono);font-size:9px;'
            f'letter-spacing:0.12em;color:{P["text_faint"]};margin-bottom:4px;">'
            f'COMMERCIAL % ↔ MOIC</div>'
            f'<div style="font-size:26px;">{_fmt_corr(pi.commercial_moic_corr)}</div>'
            f'<div style="color:{P["text_dim"]};font-size:11px;margin-top:4px;'
            f'line-height:1.5;">Positive correlation → more commercial = higher MOIC.</div>'
            f'</div>'
            f'<div>'
            f'<div style="font-family:var(--ck-mono);font-size:9px;'
            f'letter-spacing:0.12em;color:{P["text_faint"]};margin-bottom:4px;">'
            f'MEDICAID % ↔ MOIC</div>'
            f'<div style="font-size:26px;">{_fmt_corr(pi.medicaid_moic_corr)}</div>'
            f'<div style="color:{P["text_dim"]};font-size:11px;margin-top:4px;'
            f'line-height:1.5;">Negative correlation → more medicaid = MOIC drag.</div>'
            f'</div>'
            f'</div>'
        ),
        code="COR",
    )

    # Regime visual: box-and-whisker of MOIC distribution per
    # payer-mix regime above the underlying numbers table.
    regime_chart = _regime_moic_boxplot(pi.regime_stats)

    # Regime table
    regime_rows = []
    for rs in pi.regime_stats:
        regime_rows.append(_regime_row(rs))
    regime_table = (
        f'<div class="ck-table-wrap"><table class="ck-table sortable">'
        f'<thead><tr>'
        f'<th>Regime</th>'
        f'<th>Commercial Range</th>'
        f'<th class="num">Deals</th>'
        f'<th class="num">MOIC P25</th>'
        f'<th class="num">MOIC P50</th>'
        f'<th class="num">MOIC P75</th>'
        f'<th class="num">IRR P50</th>'
        f'<th class="num">Loss %</th>'
        f'<th>Avg Mix</th>'
        f'</tr></thead>'
        f'<tbody>{"".join(regime_rows)}</tbody></table></div>'
    )
    regime_panel = small_panel(
        f"Payer-mix regimes ({len(pi.regime_stats)})",
        regime_chart + regime_table,
        code="REG",
    )

    meta = (
        f"{len(corpus)} corpus deals · {len(pi.regime_stats)} regimes · "
        f"commercial-MOIC corr {pi.commercial_moic_corr:.3f}"
    )
    body = (
        _title(meta)
        + explainer_html
        + kpi_strip
        + ck_section_header(
            "PAYER MIX — CORPUS AVERAGE",
            "65.5% of deals carry non-null payer mix",
        )
        + mix_panel
        + ck_section_header(
            "PAYER % ↔ MOIC CORRELATION",
            "does mix predict outcomes?",
        )
        + corr_panel
        + ck_section_header(
            "PAYER-MIX REGIMES",
            "4-band breakdown with per-band MOIC distribution",
            count=len(pi.regime_stats),
        )
        + regime_panel
    )

    return chartis_shell(
        body,
        title="Payer Intelligence",
        active_nav="/payer-intelligence",
        extra_css=_EXPLAINER_CSS,
    )
