"""Bankruptcy + Distress page — facility-level early-warning dashboard.

PEDESK Phase 3 (Week 3, Model Retraining). The page surfaces:

  - The corpus-wide distress band distribution (safe / watch /
    distressed / critical) so the partner sees how much of the
    universe is currently under stress.
  - A sortable facility table ranked by composite distress score,
    with MERC, Altman Z', Days Cash on Hand, Net Days in AR, and
    triggered alerts inline.
  - Filter chips for state and band so the partner can drill into
    a specific risk pocket without re-running.
  - A diagnostics footer noting which Altman inputs were proxied
    (HCRIS slim extract doesn't carry the full balance sheet) so
    every Z' score is auditable.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs

import pandas as pd

from .._chartis_kit import chartis_shell
from ..brand import PALETTE
from ...data_public.distress_models import (
    ALTMAN_Z_DISTRESS_THRESHOLD,
    ALTMAN_Z_SAFE_THRESHOLD,
    AR_DAYS_DISTRESS_THRESHOLD,
    DCOH_DISTRESS_THRESHOLD,
    MERC_DISTRESS_THRESHOLD,
    DistressSignal,
    evaluate_facility,
)


_BAND_COLORS = {
    "safe":        PALETTE.get("positive", "#10B981"),
    "watch":       PALETTE.get("warning", "#F59E0B"),
    "distressed":  PALETTE.get("negative", "#EF4444"),
    "critical":    "#7C1D1D",
}

_BAND_LABELS = {
    "safe":       "Safe",
    "watch":      "Watch",
    "distressed": "Distressed",
    "critical":   "Critical",
}


def _band_chip(band: str, count: int, total: int) -> str:
    color = _BAND_COLORS.get(band, "#666")
    pct = (count / total * 100.0) if total else 0.0
    label = _BAND_LABELS.get(band, band)
    return (
        f'<div style="display:inline-flex;flex-direction:column;align-items:flex-start;'
        f'border-left:3px solid {color};padding:6px 12px;margin-right:10px;'
        f'background:rgba(0,0,0,0.02);min-width:120px;">'
        f'<span style="font-size:10px;letter-spacing:0.08em;text-transform:uppercase;'
        f'color:#666;font-weight:600;">{label}</span>'
        f'<span style="font-size:18px;font-weight:600;color:{color};'
        f'font-family:monospace;">{count}'
        f'<span style="font-size:10px;color:#888;font-weight:400;margin-left:6px;">'
        f'({pct:.0f}%)</span></span></div>'
    )


def _alert_chip(alert: str) -> str:
    """Render one alert string as a colour-coded inline chip."""
    color = "#666"
    bg = "rgba(0,0,0,0.04)"
    if alert.startswith(("ALTMAN-DISTRESS", "MERC-OVERRUN", "LIQUIDITY-CRISIS",
                         "COLLECTIONS-STALL", "AR>DCOH")):
        color = "#7C1D1D"
        bg = "rgba(239,68,68,0.10)"
    elif alert.startswith(("ALTMAN-GREY", "MERC-WATCH", "DCOH-WATCH",
                           "AR-WATCH", "MARGIN-DEEP-NEG")):
        color = "#92400E"
        bg = "rgba(245,158,11,0.10)"
    return (
        f'<span style="display:inline-block;font-family:monospace;'
        f'font-size:10px;padding:2px 6px;margin:1px 3px 1px 0;'
        f'background:{bg};color:{color};border-radius:2px;'
        f'border:1px solid {color};">{_html.escape(alert)}</span>'
    )


def _format_metric(
    value: Optional[float],
    *,
    fmt: str = "{:.2f}",
    threshold: Optional[float] = None,
    direction: str = "lower_is_worse",
) -> str:
    """Format a single distress metric with a colour band tied to its threshold."""
    if value is None:
        return '<span style="color:#999;">—</span>'
    bad = False
    if threshold is not None:
        bad = (
            value < threshold if direction == "lower_is_worse"
            else value > threshold
        )
    color = _BAND_COLORS["distressed"] if bad else PALETTE.get("text", "#1a2332")
    return (
        f'<span style="font-family:monospace;font-variant-numeric:tabular-nums;'
        f'color:{color};font-weight:{600 if bad else 400};">'
        f'{fmt.format(value)}</span>'
    )


def _facility_row(sig: DistressSignal) -> str:
    band_color = _BAND_COLORS.get(sig.band, "#666")
    npr_str = (
        f"${sig.net_patient_revenue / 1e6:.0f}M"
        if sig.net_patient_revenue and sig.net_patient_revenue >= 1e6
        else "—"
    )
    margin_str = (
        f'{sig.operating_margin*100:.1f}%' if sig.operating_margin is not None else '—'
    )
    alerts_html = "".join(_alert_chip(a) for a in sig.alerts) or (
        '<span style="color:#999;font-style:italic;font-size:10px;">no alerts</span>'
    )
    return (
        f'<tr>'
        f'<td style="padding:6px 8px;border-bottom:1px solid #eee;">'
        f'<a href="/hospital/{_html.escape(sig.ccn)}" '
        f'style="color:#1F4E78;text-decoration:none;font-weight:600;'
        f'font-family:monospace;">{_html.escape(sig.ccn)}</a></td>'
        f'<td style="padding:6px 8px;border-bottom:1px solid #eee;">'
        f'<a href="/hospital/{_html.escape(sig.ccn)}" '
        f'style="color:#1a2332;text-decoration:none;">'
        f'{_html.escape(sig.name[:48])}</a></td>'
        f'<td style="padding:6px 8px;border-bottom:1px solid #eee;'
        f'font-family:monospace;">{_html.escape(sig.state)}</td>'
        f'<td style="padding:6px 8px;border-bottom:1px solid #eee;text-align:right;">'
        f'<span style="display:inline-block;padding:2px 8px;background:{band_color};'
        f'color:#fff;font-size:11px;font-weight:600;border-radius:2px;'
        f'font-family:monospace;">{sig.distress_score:.0f}</span></td>'
        f'<td style="padding:6px 8px;border-bottom:1px solid #eee;text-align:right;">'
        f'{_format_metric(sig.merc, threshold=MERC_DISTRESS_THRESHOLD, direction="higher_is_worse")}'
        f'</td>'
        f'<td style="padding:6px 8px;border-bottom:1px solid #eee;text-align:right;">'
        f'{_format_metric(sig.altman_z, threshold=ALTMAN_Z_DISTRESS_THRESHOLD, direction="lower_is_worse")}'
        f'</td>'
        f'<td style="padding:6px 8px;border-bottom:1px solid #eee;text-align:right;">'
        f'{_format_metric(sig.dcoh, fmt="{:.0f}d", threshold=DCOH_DISTRESS_THRESHOLD, direction="lower_is_worse")}'
        f'</td>'
        f'<td style="padding:6px 8px;border-bottom:1px solid #eee;text-align:right;">'
        f'{_format_metric(sig.ar_days, fmt="{:.0f}d", threshold=AR_DAYS_DISTRESS_THRESHOLD, direction="higher_is_worse")}'
        f'</td>'
        f'<td style="padding:6px 8px;border-bottom:1px solid #eee;text-align:right;'
        f'font-family:monospace;">{margin_str}</td>'
        f'<td style="padding:6px 8px;border-bottom:1px solid #eee;text-align:right;'
        f'font-family:monospace;">{npr_str}</td>'
        f'<td style="padding:6px 8px;border-bottom:1px solid #eee;font-size:10px;'
        f'max-width:380px;">{alerts_html}</td>'
        f'</tr>'
    )


def render_distress(
    hcris_df: Optional[pd.DataFrame] = None,
    query_string: str = "",
) -> str:
    """Render the /distress page — facility-level distress dashboard."""
    qs = parse_qs(query_string or "")
    band_filter = (qs.get("band") or ["all"])[0]
    state_filter = (qs.get("state") or [""])[0].upper()[:2]
    limit = max(20, min(500, int((qs.get("limit") or ["100"])[0]))) if (qs.get("limit") or ["100"])[0].isdigit() else 100

    if hcris_df is None:
        try:
            from ...data.hcris import _get_latest_per_ccn
            hcris_df = _get_latest_per_ccn()
        except Exception:
            hcris_df = pd.DataFrame()

    signals: List[DistressSignal] = []
    if hcris_df is not None and not hcris_df.empty:
        for _, row in hcris_df.iterrows():
            sig = evaluate_facility(row.to_dict())
            # Drop rows with no usable signal at all (probably junk
            # filings) so the table doesn't pad with zero-score rows.
            if (
                sig.distress_score == 0
                and sig.altman_z is None
                and sig.merc is None
                and sig.dcoh is None
            ):
                continue
            signals.append(sig)

    band_counts = {"safe": 0, "watch": 0, "distressed": 0, "critical": 0}
    for s in signals:
        band_counts[s.band] = band_counts.get(s.band, 0) + 1
    total_signals = len(signals)
    facilities_at_risk = band_counts["distressed"] + band_counts["critical"]
    revenue_at_risk = sum(
        s.net_patient_revenue or 0
        for s in signals
        if s.band in ("distressed", "critical")
    )

    # Apply filters
    filtered = signals
    if band_filter != "all" and band_filter in band_counts:
        filtered = [s for s in filtered if s.band == band_filter]
    if state_filter:
        filtered = [s for s in filtered if s.state.upper() == state_filter]
    filtered.sort(key=lambda s: -s.distress_score)
    visible = filtered[:limit]

    # Filter chips
    band_filter_chips = ""
    for b in ["all", "critical", "distressed", "watch", "safe"]:
        active = b == band_filter
        color = _BAND_COLORS.get(b, "#666") if b != "all" else "#1F4E78"
        bg = color if active else "transparent"
        fg = "#fff" if active else color
        label = "All" if b == "all" else _BAND_LABELS.get(b, b)
        cnt = total_signals if b == "all" else band_counts.get(b, 0)
        band_filter_chips += (
            f'<a href="/distress?band={b}" '
            f'style="display:inline-block;padding:4px 10px;margin-right:6px;'
            f'border:1px solid {color};background:{bg};color:{fg};'
            f'text-decoration:none;font-size:11px;border-radius:2px;'
            f'font-family:Inter,sans-serif;">{label} '
            f'<span style="font-family:monospace;">{cnt}</span></a>'
        )

    # KPI band strip
    kpi_strip = "".join(
        _band_chip(b, band_counts.get(b, 0), total_signals)
        for b in ["safe", "watch", "distressed", "critical"]
    )

    # Headline KPIs
    revenue_at_risk_str = (
        f"${revenue_at_risk / 1e9:.2f}B"
        if revenue_at_risk >= 1e9
        else f"${revenue_at_risk / 1e6:.0f}M"
    )
    headline = (
        f'<div style="display:flex;gap:24px;align-items:baseline;margin-bottom:16px;">'
        f'<div><div style="font-size:11px;color:#666;letter-spacing:0.08em;text-transform:uppercase;">Facilities Scored</div>'
        f'<div style="font-size:24px;font-weight:600;font-family:monospace;color:#1a2332;">'
        f'{total_signals:,}</div></div>'
        f'<div><div style="font-size:11px;color:#666;letter-spacing:0.08em;text-transform:uppercase;">At Risk</div>'
        f'<div style="font-size:24px;font-weight:600;font-family:monospace;'
        f'color:{_BAND_COLORS["distressed"]};">'
        f'{facilities_at_risk:,} <span style="font-size:14px;color:#888;font-weight:400;">'
        f'({facilities_at_risk/total_signals*100:.1f}%)</span></div></div>'
        f'<div><div style="font-size:11px;color:#666;letter-spacing:0.08em;text-transform:uppercase;">Revenue at Risk</div>'
        f'<div style="font-size:24px;font-weight:600;font-family:monospace;'
        f'color:{_BAND_COLORS["distressed"]};">{revenue_at_risk_str}</div></div>'
        f'</div>'
        if total_signals else ""
    )

    table_rows = "".join(_facility_row(s) for s in visible)
    if not table_rows:
        table_rows = (
            '<tr><td colspan="11" style="padding:24px;text-align:center;'
            'color:#666;font-style:italic;">No facilities matched the current '
            'filters. Widen the band or state filter to see results.</td></tr>'
        )

    table_html = (
        '<table style="width:100%;border-collapse:collapse;font-size:12px;">'
        '<thead>'
        '<tr style="background:#f5f1ea;border-bottom:2px solid #1F4E78;">'
        '<th style="padding:8px;text-align:left;font-size:10px;letter-spacing:0.08em;'
        'text-transform:uppercase;color:#666;">CCN</th>'
        '<th style="padding:8px;text-align:left;font-size:10px;letter-spacing:0.08em;'
        'text-transform:uppercase;color:#666;">Hospital</th>'
        '<th style="padding:8px;text-align:left;font-size:10px;letter-spacing:0.08em;'
        'text-transform:uppercase;color:#666;">St</th>'
        '<th style="padding:8px;text-align:right;font-size:10px;letter-spacing:0.08em;'
        'text-transform:uppercase;color:#666;" '
        'title="Composite distress score 0–100 (Altman 35%, MERC 30%, DCOH 20%, AR 15%)">Score</th>'
        '<th style="padding:8px;text-align:right;font-size:10px;letter-spacing:0.08em;'
        'text-transform:uppercase;color:#666;" '
        'title="Medical Expenditure Ratio to Capital — opex / NPR. ≥1.0 = distress.">MERC</th>'
        '<th style="padding:8px;text-align:right;font-size:10px;letter-spacing:0.08em;'
        'text-transform:uppercase;color:#666;" '
        'title="Altman Z-prime (private firm, 1983). <1.23 = distress, >2.90 = safe.">Altman Z\'</th>'
        '<th style="padding:8px;text-align:right;font-size:10px;letter-spacing:0.08em;'
        'text-transform:uppercase;color:#666;" '
        'title="Days of opex covered by liquid cash. <30d = distress, <60d = watch.">DCOH</th>'
        '<th style="padding:8px;text-align:right;font-size:10px;letter-spacing:0.08em;'
        'text-transform:uppercase;color:#666;" '
        'title="Net days in accounts receivable. >60d = distress, >50d = watch.">AR Days</th>'
        '<th style="padding:8px;text-align:right;font-size:10px;letter-spacing:0.08em;'
        'text-transform:uppercase;color:#666;">Op Margin</th>'
        '<th style="padding:8px;text-align:right;font-size:10px;letter-spacing:0.08em;'
        'text-transform:uppercase;color:#666;">NPR</th>'
        '<th style="padding:8px;text-align:left;font-size:10px;letter-spacing:0.08em;'
        'text-transform:uppercase;color:#666;">Triggered Alerts</th>'
        '</tr></thead>'
        f'<tbody>{table_rows}</tbody></table>'
    )

    methodology = (
        '<details style="margin-top:18px;font-size:11px;color:#666;">'
        '<summary style="cursor:pointer;font-weight:600;color:#1F4E78;">'
        'Methodology &amp; proxied inputs</summary>'
        '<div style="padding:8px 0;line-height:1.5;">'
        '<p><b>Altman Z\' (1983 private-firm)</b> = '
        '0.717·X1 + 0.847·X2 + 3.107·X3 + 0.420·X4 + 0.998·X5 '
        'where X1 = working capital / total assets, X2 = retained earnings / total assets, '
        'X3 = EBIT / total assets, X4 = book equity / total liabilities, '
        'X5 = sales / total assets. Distress &lt; 1.23, grey 1.23–2.90, safe &gt; 2.90.</p>'
        '<p><b>MERC</b> = operating expenses / (net patient revenue + supplemental payments). '
        'A MERC ≥ 1.00 means the hospital spends more than it earns operationally — '
        'the structural shape every recent PE-healthcare bankruptcy carried at filing.</p>'
        '<p><b>DCOH</b> proxied from net-income-to-opex when balance-sheet cash is absent in the HCRIS slim extract; '
        '<b>AR Days</b> proxied from contractual-allowance ratio when explicit AR not loaded. '
        'Per-row proxy flags surface in the audit log; pull the row\'s '
        '<code>proxied_inputs</code> field for the full list.</p>'
        '<p><b>Composite score</b> weights Altman 35%, MERC 30%, DCOH 20%, AR 15%. Missing '
        'inputs reduce the maximum proportionally, so a facility with only two of four signals '
        'still produces a defensible relative ranking.</p>'
        '</div></details>'
    )

    body = (
        '<div style="padding:20px 24px;max-width:1400px;margin:0 auto;">'
        '<h1 style="font-size:22px;font-weight:600;color:#0b2341;margin:0 0 4px 0;">'
        'Bankruptcy &amp; Distress</h1>'
        '<div style="font-size:12px;color:#666;margin-bottom:16px;">'
        'Facility-level early-warning dashboard combining MERC, Altman Z\' (private-firm), '
        'Days Cash on Hand, and Net Days in AR.</div>'
        f'{headline}'
        '<div style="margin-bottom:16px;display:flex;flex-wrap:wrap;gap:8px;">'
        f'{kpi_strip}'
        '</div>'
        '<div style="margin-bottom:14px;">'
        f'{band_filter_chips}'
        '</div>'
        f'{table_html}'
        f'{methodology}'
        '</div>'
    )

    return chartis_shell(
        body, "Bankruptcy & Distress",
        active_nav="/distress",
        subtitle=f"{total_signals:,} facilities scored | {facilities_at_risk:,} at risk",
    )
