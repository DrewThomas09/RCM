"""Portfolio Construction Optimizer page — /portfolio-optimizer.

Analyzes a portfolio of corpus deals (selected by sector, vintage, sponsor)
for concentration risk, HHI metrics, and optimal diversification.

Uses the existing deal_portfolio_construction.py analytics module and shows:
- HHI heatmap across sector / vintage / payer dimensions
- Optimal sector weights from corpus performance data
- Marginal diversification analysis for proposed additions

No DB required — all in-memory corpus analytics.
"""
from __future__ import annotations

import html as _html
import importlib
import math
from typing import Any, Dict, List, Optional


def _load_corpus() -> List[Dict[str, Any]]:
    from rcm_mc.data_public.deals_corpus import _SEED_DEALS
    from rcm_mc.data_public.extended_seed import EXTENDED_SEED_DEALS
    result = list(_SEED_DEALS) + list(EXTENDED_SEED_DEALS)
    for i in range(2, 32):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            result += list(getattr(mod, f"EXTENDED_SEED_DEALS_{i}"))
        except (ImportError, AttributeError):
            pass
    return result


def _percentile(vals: List[float], p: float) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    idx = p / 100 * (len(s) - 1)
    lo, hi = int(idx), min(int(idx) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (idx - lo)


# ---------------------------------------------------------------------------
# HHI visualization helpers
# ---------------------------------------------------------------------------

def _hhi_signal(hhi: float) -> str:
    """HHI signal color (0=minimum concentration, 1=monopoly)."""
    if hhi < 0.15:
        return "#22c55e", "Low"
    if hhi < 0.25:
        return "#f59e0b", "Moderate"
    return "#ef4444", "High"


def _hhi_bar(hhi: float, label: str, width: int = 200) -> str:
    """Inline SVG progress bar for HHI score."""
    filled = int(hhi * width)
    color, level = _hhi_signal(hhi)
    return (
        f'<div style="margin:6px 0;">'
        f'<div style="font-size:9px;color:#64748b;margin-bottom:2px;font-family:var(--ck-mono)">'
        f'{_html.escape(label)}</div>'
        f'<div style="display:flex;align-items:center;gap:8px;">'
        f'<svg width="{width}" height="10" xmlns="http://www.w3.org/2000/svg">'
        f'<rect x="0" y="1" width="{width}" height="8" rx="1" fill="#1e293b"/>'
        f'<rect x="0" y="1" width="{filled}" height="8" rx="1" fill="{color}"/>'
        f'<line x1="{int(0.25*width)}" y1="0" x2="{int(0.25*width)}" y2="10" stroke="#334155" stroke-width="1"/>'
        f'<line x1="{int(0.15*width)}" y1="0" x2="{int(0.15*width)}" y2="10" stroke="#22c55e" stroke-width="0.8" stroke-dasharray="2,2"/>'
        f'</svg>'
        f'<span style="font-family:var(--ck-mono);font-variant-numeric:tabular-nums;font-size:10px;color:{color}">'
        f'{hhi:.3f} — {level}</span>'
        f'</div>'
        f'</div>'
    )


def _hhi_panel(composition: Any) -> str:
    return f"""
<div class="ck-panel">
  <div class="ck-panel-title">Concentration Risk (HHI)</div>
  <div style="padding:12px 16px;display:grid;grid-template-columns:1fr 1fr;gap:16px;">
    <div>
      {_hhi_bar(composition.hhi_sector, "Sector HHI")}
      {_hhi_bar(composition.hhi_vintage, "Vintage HHI")}
      {_hhi_bar(composition.hhi_payer, "Payer HHI")}
      <div style="margin-top:8px;font-size:9.5px;color:var(--ck-text-faint);">
        HHI thresholds: green &lt;0.15 · amber 0.15–0.25 · red &gt;0.25 &nbsp;|&nbsp; green line = target &lt;0.15
      </div>
    </div>
    <div>
      <div class="ck-section-label" style="margin-bottom:6px;">Portfolio Summary</div>
      <table style="font-size:10.5px;line-height:1.9;width:100%;">
        <tr><td class="dim">Deals</td><td class="mono" style="text-align:right;">{composition.n_deals}</td></tr>
        <tr><td class="dim">Avg Commercial %</td>
            <td class="mono" style="text-align:right;font-variant-numeric:tabular-nums;">{composition.avg_commercial_pct*100:.1f}%</td></tr>
        <tr><td class="dim">Vintage Risk Score</td>
            <td class="mono" style="text-align:right;font-variant-numeric:tabular-nums;">{composition.weighted_vintage_risk:.2f}</td></tr>
        <tr><td class="dim">Sector HHI</td>
            <td class="mono" style="text-align:right;font-variant-numeric:tabular-nums;">{composition.hhi_sector:.3f}</td></tr>
        <tr><td class="dim">Vintage HHI</td>
            <td class="mono" style="text-align:right;font-variant-numeric:tabular-nums;">{composition.hhi_vintage:.3f}</td></tr>
        <tr><td class="dim">Payer HHI</td>
            <td class="mono" style="text-align:right;font-variant-numeric:tabular-nums;">{composition.hhi_payer:.3f}</td></tr>
      </table>
    </div>
  </div>
</div>"""


def _sector_weight_panel(composition: Any) -> str:
    """Bar chart of sector weights vs corpus-optimal."""
    weights = composition.sector_weights or {}
    if not weights:
        return ""

    items = sorted(weights.items(), key=lambda x: -x[1])[:12]
    bars = []
    for sector, weight in items:
        w_pct = weight * 100
        filled = int(weight * 200)
        color = "#3b82f6" if w_pct <= 20 else ("#f59e0b" if w_pct <= 35 else "#ef4444")
        bars.append(
            f'<div style="margin:4px 0;display:flex;align-items:center;gap:8px;">'
            f'<div style="width:160px;font-size:10px;color:#94a3b8;text-align:right;'
            f'font-family:var(--ck-mono);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">'
            f'{_html.escape(sector[:22])}</div>'
            f'<svg width="200" height="10" xmlns="http://www.w3.org/2000/svg">'
            f'<rect x="0" y="1" width="200" height="8" rx="1" fill="#1e293b"/>'
            f'<rect x="0" y="1" width="{filled}" height="8" rx="1" fill="{color}"/>'
            f'</svg>'
            f'<span style="font-family:var(--ck-mono);font-variant-numeric:tabular-nums;'
            f'font-size:9.5px;color:{color};min-width:35px;">{w_pct:.1f}%</span>'
            f'</div>'
        )
    return f"""
<div class="ck-panel">
  <div class="ck-panel-title">Portfolio Sector Weights</div>
  <div style="padding:12px 16px;">
    {''.join(bars)}
    <div style="margin-top:8px;font-size:9.5px;color:var(--ck-text-faint);">
      Green &lt;20% · amber 20–35% · red &gt;35% single-sector exposure
    </div>
  </div>
</div>"""


def _optimal_weights_panel(optimal: Dict[str, float]) -> str:
    """Corpus-calibrated optimal sector weights table."""
    items = sorted(optimal.items(), key=lambda x: -x[1])[:15]
    rows = []
    for i, (sector, w) in enumerate(items):
        stripe = ' style="background:#0f172a"' if i % 2 == 1 else ""
        rows.append(
            f'<tr{stripe}><td class="dim" style="font-size:10.5px;">{_html.escape(sector[:30])}</td>'
            f'<td class="mono" style="text-align:right;font-variant-numeric:tabular-nums;">{w*100:.1f}%</td></tr>'
        )
    return f"""
<div class="ck-panel">
  <div class="ck-panel-title">Corpus-Optimal Sector Weights (risk-adjusted returns)</div>
  <div class="ck-table-wrap">
    <table class="ck-table" style="width:320px;">
      <thead><tr><th>Sector</th><th style="text-align:right;">Target Weight</th></tr></thead>
      <tbody>{''.join(rows)}</tbody>
    </table>
  </div>
  <div style="padding:0 16px 10px;font-size:9.5px;color:var(--ck-text-faint);">
    Derived from corpus P50 MOIC × (1 - loss rate) by sector · risk_aversion=0.5
  </div>
</div>"""


def _build_sample_portfolio(corpus: List[Dict[str, Any]], sectors: List[str]) -> List[Dict[str, Any]]:
    """Build a representative portfolio from corpus by sampling the given sectors."""
    result = []
    for sector in sectors:
        sector_deals = [d for d in corpus if d.get("sector") == sector]
        # Take the 2-3 most recent deals with highest EV
        by_ev = sorted(sector_deals, key=lambda d: float(d.get("ev_mm") or 0), reverse=True)
        result.extend(by_ev[:2])
    return result[:20]  # cap at 20 deals


def _kpi_bar(composition: Any) -> str:
    from rcm_mc.ui._chartis_kit import ck_kpi_block

    hhi_color, hhi_level = _hhi_signal(composition.hhi_sector)
    return (
        '<div class="ck-kpi-grid">'
        + ck_kpi_block("Portfolio Deals", f'<span class="mn">{composition.n_deals}</span>', "in analysis")
        + ck_kpi_block("Sector HHI",
                       f'<span class="mn" style="color:{hhi_color}">{composition.hhi_sector:.3f}</span>',
                       f"{hhi_level} concentration")
        + ck_kpi_block("Avg Commercial %",
                       f'<span class="mn">{composition.avg_commercial_pct*100:.1f}%</span>', "weighted payer mix")
        + ck_kpi_block("Vintage Risk",
                       f'<span class="mn">{composition.weighted_vintage_risk:.2f}</span>', "weighted score")
        + ck_kpi_block("Unique Sectors",
                       f'<span class="mn">{len(composition.sector_weights or {})}</span>', "in portfolio")
        + '</div>'
    )


def render_portfolio_optimizer(sectors: Optional[List[str]] = None) -> str:
    from rcm_mc.ui._chartis_kit import chartis_shell, ck_section_header
    from rcm_mc.data_public.deal_portfolio_construction import analyze_portfolio, optimal_sector_weights

    corpus = _load_corpus()

    if not sectors:
        # Default: illustrative diversified portfolio
        default_sectors = [
            "Physician Practice", "Behavioral Health", "Ambulatory Surgery Centers",
            "Dental", "Healthcare IT / RCM", "Home Health",
        ]
        portfolio = _build_sample_portfolio(corpus, default_sectors)
        mode = "sample diversified portfolio (6 sectors)"
    else:
        portfolio = _build_sample_portfolio(corpus, sectors)
        mode = f"portfolio: {', '.join(sectors[:3])}" + (f" +{len(sectors)-3} more" if len(sectors) > 3 else "")

    composition = analyze_portfolio(portfolio, corpus)
    optimal = optimal_sector_weights(corpus, risk_aversion=0.5)

    # Sector selector form
    all_sectors = sorted({d.get("sector") for d in corpus if d.get("sector")})
    selected_set = set(sectors or [])
    checkboxes = "".join(
        f'<label style="display:inline-block;margin:3px 8px 3px 0;font-size:10px;color:#94a3b8;cursor:pointer;">'
        f'<input type="checkbox" name="sector" value="{_html.escape(s)}" '
        f'{"checked" if s in selected_set else ""} style="margin-right:3px;">'
        f'{_html.escape(s[:22])}</label>'
        for s in all_sectors
    )
    form_html = f"""
<div class="ck-panel">
  <div class="ck-panel-title">Portfolio Composition</div>
  <form method="get" action="/portfolio-optimizer" style="padding:12px 16px;">
    <div style="font-size:9.5px;color:#64748b;margin-bottom:8px;letter-spacing:0.08em;text-transform:uppercase;">
      Select Sectors (sample 2 top deals per sector)
    </div>
    <div style="max-height:120px;overflow-y:auto;border:1px solid #1e293b;padding:8px;border-radius:3px;">
      {checkboxes}
    </div>
    <div style="margin-top:10px;">
      <button type="submit" class="ck-btn">Analyze Portfolio</button>
      <span style="margin-left:10px;font-size:9.5px;color:#475569;">{len(portfolio)} deals selected</span>
    </div>
  </form>
</div>"""

    kpis = _kpi_bar(composition)
    sec_hhi = ck_section_header("CONCENTRATION ANALYSIS", f"portfolio HHI across sector/vintage/payer — {mode}")
    hhi_p = _hhi_panel(composition)
    sec_weights = ck_section_header("SECTOR WEIGHTS", "current portfolio vs corpus-optimal allocation")
    weight_panels = f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:0;">{_sector_weight_panel(composition)}{_optimal_weights_panel(optimal)}</div>'

    body = kpis + form_html + sec_hhi + hhi_p + sec_weights + weight_panels

    return chartis_shell(
        body,
        title="Portfolio Construction",
        active_nav="/portfolio-optimizer",
        subtitle=(
            f"{composition.n_deals} deals · "
            f"sector HHI {composition.hhi_sector:.3f} · "
            f"vintage HHI {composition.hhi_vintage:.3f} · "
            f"{len(composition.sector_weights or {})} sectors"
        ),
    )
