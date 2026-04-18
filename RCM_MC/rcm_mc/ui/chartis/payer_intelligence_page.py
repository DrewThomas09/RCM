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
        f'<td style="text-align:right;font-family:var(--ck-mono);'
        f'font-variant-numeric:tabular-nums;color:{P["text_dim"]};" '
        f'data-val="{rs.moic_p25 or 0}">{fmt_multiple(rs.moic_p25)}</td>'
        f'<td style="text-align:right;font-family:var(--ck-mono);'
        f'font-variant-numeric:tabular-nums;color:{p50_col};font-weight:600;" '
        f'data-val="{p50}">{fmt_multiple(p50)}</td>'
        f'<td style="text-align:right;font-family:var(--ck-mono);'
        f'font-variant-numeric:tabular-nums;color:{P["text_dim"]};" '
        f'data-val="{rs.moic_p75 or 0}">{fmt_multiple(rs.moic_p75)}</td>'
        f'<td style="text-align:right;font-family:var(--ck-mono);'
        f'font-variant-numeric:tabular-nums;color:{P["text"]};" '
        f'data-val="{rs.irr_p50 or 0}">{fmt_pct(rs.irr_p50)}</td>'
        f'<td style="text-align:right;font-family:var(--ck-mono);'
        f'font-variant-numeric:tabular-nums;color:{loss_col};" '
        f'data-val="{rs.loss_rate or 0}">{fmt_pct(rs.loss_rate)}</td>'
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
    try:
        from ...data_public.payer_intelligence import compute_payer_intelligence
    except Exception as exc:  # noqa: BLE001
        body = small_panel(
            "Payer intelligence unavailable",
            empty_note(f"payer_intelligence module failed: {exc!r}"),
            code="ERR",
        )
        return chartis_shell(
            body, title="Payer Intelligence",
            active_nav="/payer-intelligence",
            subtitle="Module unavailable",
        )

    corpus = load_corpus_deals()
    if not corpus:
        body = small_panel(
            "Payer intelligence — no corpus",
            empty_note("No corpus deals available to analyze."),
            code="NIL",
        )
        return chartis_shell(
            body, title="Payer Intelligence",
            active_nav="/payer-intelligence",
            subtitle="Corpus unavailable",
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
            body, title="Payer Intelligence",
            active_nav="/payer-intelligence",
            subtitle="Analysis raised",
        )

    commercial = float(pi.avg_commercial or 0)
    medicare = float(pi.avg_medicare or 0)
    medicaid = float(pi.avg_medicaid or 0)
    self_pay = float(pi.avg_self_pay or 0)

    intro = (
        f'<div style="background:{P["panel"]};border:1px solid {P["border"]};'
        f'border-left:4px solid {P["accent"]};border-radius:3px;'
        f'padding:12px 16px;margin-bottom:14px;">'
        f'<div style="font-family:var(--ck-mono);font-size:9.5px;'
        f'letter-spacing:0.15em;color:{P["accent"]};margin-bottom:4px;">'
        f'COMPREHENSIVE VIEW</div>'
        f'<div style="color:{P["text"]};font-size:12px;line-height:1.6;">'
        f'Full output of <code style="color:{P["accent"]};'
        f'font-family:var(--ck-mono);">data_public/payer_intelligence.py</code>. '
        f'For the thinner summary view, see '
        f'<a href="/payer-intel" style="color:{P["accent"]};">/payer-intel</a>. '
        f'This page is the 4-regime breakdown with MOIC correlations, payer-mix '
        f'bands, and loss-rate by payer-concentration.'
        f'</div></div>'
    )

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
        regime_table,
        code="REG",
    )

    body = (
        intro
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
        subtitle=f"{len(corpus)} corpus deals · {len(pi.regime_stats)} regimes · "
                 f"commercial-MOIC corr {pi.commercial_moic_corr:.3f}",
    )
