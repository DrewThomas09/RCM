"""Risk Matrix page — /risk-matrix.

Plots all corpus deals on a 2D risk/return scatter with quadrant annotations.
X axis = composite entry risk score (0-100, higher = riskier).
Y axis = realized MOIC.
Color = sector. Quadrant lines: risk=50, MOIC=2.0.

Also shows a sector-level risk heatmap and the risk dimension breakdown table.
"""
from __future__ import annotations

import html as _html
import importlib
import math
from typing import Any, Dict, List, Optional, Tuple


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
# Risk scoring
# ---------------------------------------------------------------------------

_CORPUS_FOR_SCORING: Optional[List[Dict[str, Any]]] = None


def _entry_risk_score(deal: Dict[str, Any], corpus: Optional[List[Dict[str, Any]]] = None) -> Optional[float]:
    """Simple 0-100 entry risk score from deal characteristics."""
    global _CORPUS_FOR_SCORING
    from rcm_mc.data_public.deal_entry_risk_score import score_entry_risk
    try:
        if corpus is None:
            if _CORPUS_FOR_SCORING is None:
                _CORPUS_FOR_SCORING = _load_corpus()
            corpus = _CORPUS_FOR_SCORING
        result = score_entry_risk(deal, corpus)
        return result.total
    except Exception:
        return None


# Sector color palette (Bloomberg style — no bright colors)
_SECTOR_COLORS = {
    "Physician Practice": "#3b82f6",
    "Behavioral Health": "#8b5cf6",
    "Ambulatory Surgery Centers": "#06b6d4",
    "Dental": "#0891b2",
    "Cardiology": "#2563eb",
    "Dermatology": "#7c3aed",
    "Orthopedics": "#0e7490",
    "Emergency Medicine": "#dc2626",
    "Anesthesiology": "#9333ea",
    "General Hospitals": "#64748b",
    "Behavioral Health / Substance Abuse": "#6d28d9",
    "Home Health": "#0284c7",
    "Skilled Nursing": "#475569",
    "Healthcare IT / RCM": "#059669",
    "Value-Based Care": "#0f766e",
    "Telehealth / DTC": "#14b8a6",
    "Pediatrics": "#0369a1",
    "Oncology": "#b45309",
    "Ophthalmology": "#0d9488",
    "Gastroenterology": "#16a34a",
}
_DEFAULT_COLOR = "#334155"


def _sector_color(sector: str) -> str:
    return _SECTOR_COLORS.get(sector, _DEFAULT_COLOR)


# ---------------------------------------------------------------------------
# SVG scatter plot
# ---------------------------------------------------------------------------

def _risk_return_scatter(
    pts: List[Tuple[float, float, str, str]],  # (risk, moic, sector, deal_name)
    width: int = 700,
    height: int = 420,
) -> str:
    """2D scatter: X=risk score, Y=realized MOIC. Quadrant lines at risk=50, MOIC=2.0."""
    pad_l, pad_r, pad_t, pad_b = 38, 16, 14, 30
    pw = width - pad_l - pad_r
    ph = height - pad_t - pad_b
    x_lo, x_hi = 0.0, 100.0
    y_lo, y_hi = 0.0, 6.5

    def tx(x: float) -> float:
        return pad_l + max(0.0, min(1.0, (x - x_lo) / (x_hi - x_lo))) * pw

    def ty(y: float) -> float:
        return pad_t + (1.0 - max(0.0, min(1.0, (y - y_lo) / (y_hi - y_lo)))) * ph

    # Quadrant lines
    q_risk_x = tx(50)
    q_moic_y = ty(2.0)
    be_y = ty(1.0)
    quadrant_lines = (
        f'<line x1="{q_risk_x:.1f}" y1="{pad_t}" x2="{q_risk_x:.1f}" y2="{pad_t+ph}" '
        f'stroke="#334155" stroke-width="1.2" stroke-dasharray="5,4"/>'
        f'<line x1="{pad_l}" y1="{q_moic_y:.1f}" x2="{pad_l+pw}" y2="{q_moic_y:.1f}" '
        f'stroke="#334155" stroke-width="1.2" stroke-dasharray="5,4"/>'
        f'<line x1="{pad_l}" y1="{be_y:.1f}" x2="{pad_l+pw}" y2="{be_y:.1f}" '
        f'stroke="#ef4444" stroke-width="0.8" stroke-dasharray="3,4" opacity="0.4"/>'
    )

    # Quadrant labels
    q_labels = (
        f'<text x="{pad_l+6}" y="{pad_t+12}" font-size="8" fill="#1e3a5f" opacity="0.8" font-style="italic">Low Risk / High Return</text>'
        f'<text x="{q_risk_x+6}" y="{pad_t+12}" font-size="8" fill="#3d1a1a" opacity="0.8" font-style="italic">High Risk / High Return</text>'
        f'<text x="{pad_l+6}" y="{q_moic_y+18}" font-size="8" fill="#1a3d2a" opacity="0.8" font-style="italic">Low Risk / Low Return</text>'
        f'<text x="{q_risk_x+6}" y="{q_moic_y+18}" font-size="8" fill="#3d2000" opacity="0.8" font-style="italic">Danger Zone</text>'
    )

    # Dots
    dots = []
    for x, y, sector, name in pts:
        if x_lo <= x <= x_hi and y_lo <= y <= y_hi:
            color = _sector_color(sector)
            cx, cy = tx(x), ty(y)
            escaped_name = _html.escape(name[:40])
            escaped_sector = _html.escape(sector[:25])
            dots.append(
                f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="3.2" fill="{color}" fill-opacity="0.75" '
                f'stroke="{color}" stroke-width="0.5" stroke-opacity="0.9">'
                f'<title>{escaped_name}\nSector: {escaped_sector}\nRisk: {x:.0f} · MOIC: {y:.2f}×</title>'
                f'</circle>'
            )

    # Axes
    axes = (
        f'<line x1="{pad_l}" y1="{pad_t}" x2="{pad_l}" y2="{pad_t+ph}" stroke="#334155" stroke-width="1"/>'
        f'<line x1="{pad_l}" y1="{pad_t+ph}" x2="{pad_l+pw}" y2="{pad_t+ph}" stroke="#334155" stroke-width="1"/>'
    )

    x_ticks = "".join(
        f'<text x="{tx(xv):.1f}" y="{pad_t+ph+14}" font-size="7.5" fill="#64748b" text-anchor="middle">{xv:.0f}</text>'
        for xv in range(0, 101, 20)
    )
    y_ticks = "".join(
        f'<text x="{pad_l-4}" y="{ty(yv)+3:.1f}" font-size="7.5" fill="#64748b" text-anchor="end">{yv:.0f}x</text>'
        for yv in range(0, 7)
    )
    labels = (
        f'<text x="{pad_l+pw/2:.1f}" y="{height-2}" font-size="9" fill="#94a3b8" text-anchor="middle">'
        f'Entry Risk Score →</text>'
        f'<text x="10" y="{pad_t+ph/2:.1f}" font-size="9" fill="#94a3b8" text-anchor="middle" '
        f'transform="rotate(-90,10,{pad_t+ph/2:.1f})">Realized MOIC</text>'
    )
    n_lbl = f'<text x="{pad_l+4}" y="{pad_t+10}" font-size="8" fill="#475569">n={len(pts)}</text>'

    # Breakeven label
    be_lbl = (
        f'<text x="{pad_l+pw-2}" y="{be_y-3:.1f}" font-size="7" fill="#ef4444" text-anchor="end" opacity="0.6">1.0×</text>'
    )

    return (
        f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        f'xmlns="http://www.w3.org/2000/svg" style="display:block;">'
        + axes + quadrant_lines + q_labels + "".join(dots) + x_ticks + y_ticks + labels + n_lbl + be_lbl
        + "</svg>"
    )


def _sector_risk_heatmap(rows: List[Dict[str, Any]]) -> str:
    """Table of sector-level risk scores and MOIC outcomes."""
    tbody = []
    for i, r in enumerate(rows):
        stripe = ' style="background:#0f172a"' if i % 2 == 1 else ""
        risk_color = "#ef4444" if r["avg_risk"] >= 65 else ("#f59e0b" if r["avg_risk"] >= 40 else "#22c55e")
        moic_color = "#ef4444" if (r["p50_moic"] or 0) < 1.0 else ("#22c55e" if (r["p50_moic"] or 0) >= 2.5 else "#e2e8f0")
        tbody.append(f"""
<tr{stripe}>
  <td class="dim" style="font-size:11px;">{_html.escape(r['sector'])}</td>
  <td class="mono dim" style="text-align:right;">{r['n']}</td>
  <td style="text-align:right;"><span style="font-family:var(--ck-mono);font-variant-numeric:tabular-nums;color:{risk_color}">{r['avg_risk']:.0f}</span></td>
  <td style="text-align:right;"><span style="font-family:var(--ck-mono);font-variant-numeric:tabular-nums;color:{moic_color};font-weight:600">{r['p50_moic']:.2f}×</span></td>
  <td class="mono" style="text-align:right;color:#ef4444;">{r['loss_rate']*100:.1f}%</td>
</tr>""")

    return f"""
<div class="ck-panel">
  <div class="ck-panel-title">Sector Risk-Return Summary</div>
  <div class="ck-table-wrap">
    <table class="ck-table" style="table-layout:fixed;">
      <colgroup>
        <col style="width:200px"><col style="width:50px">
        <col style="width:90px"><col style="width:90px"><col style="width:80px">
      </colgroup>
      <thead>
        <tr>
          <th>Sector</th>
          <th style="text-align:right;">N</th>
          <th style="text-align:right;">Avg Risk</th>
          <th style="text-align:right;">P50 MOIC</th>
          <th style="text-align:right;">Loss%</th>
        </tr>
      </thead>
      <tbody>{''.join(tbody)}</tbody>
    </table>
  </div>
</div>"""


def _build_scatter_data(
    corpus: List[Dict[str, Any]],
) -> Tuple[List[Tuple[float, float, str, str]], List[Dict[str, Any]]]:
    """Build scatter points and sector stats from corpus."""
    pts = []
    sector_data: Dict[str, Dict[str, Any]] = {}

    for deal in corpus:
        moic = deal.get("realized_moic")
        if moic is None:
            continue
        risk = _entry_risk_score(deal, corpus)
        if risk is None:
            continue
        sector = deal.get("sector") or "Unknown"
        name = deal.get("deal_name") or ""
        pts.append((float(risk), float(moic), sector, name))

        sd = sector_data.setdefault(sector, {"moics": [], "risks": []})
        sd["moics"].append(float(moic))
        sd["risks"].append(float(risk))

    # Sector summary rows
    sector_rows = []
    for s, sd in sorted(sector_data.items()):
        if len(sd["moics"]) < 2:
            continue
        moics_s = sorted(sd["moics"])
        sector_rows.append({
            "sector": s,
            "n": len(moics_s),
            "avg_risk": sum(sd["risks"]) / len(sd["risks"]),
            "p50_moic": _percentile(moics_s, 50),
            "loss_rate": sum(1 for m in moics_s if m < 1.0) / len(moics_s),
        })
    sector_rows.sort(key=lambda r: r["avg_risk"])
    return pts, sector_rows


def _kpi_bar(pts: List[Tuple[float, float, str, str]]) -> str:
    from rcm_mc.ui._chartis_kit import ck_kpi_block
    if not pts:
        return ""

    risks = [p[0] for p in pts]
    moics = [p[1] for p in pts]
    low_risk_high_return = sum(1 for r, m, _, _ in pts if r < 50 and m >= 2.0)
    danger_zone = sum(1 for r, m, _, _ in pts if r >= 50 and m < 1.0)
    avg_risk = sum(risks) / len(risks)

    return (
        '<div class="ck-kpi-grid">'
        + ck_kpi_block("Scored Deals", f'<span class="mn">{len(pts)}</span>', "realized with risk score")
        + ck_kpi_block("Avg Risk Score", f'<span class="mn">{avg_risk:.0f}</span>', "out of 100")
        + ck_kpi_block("Sweet Spot",
                       f'<span class="mn pos">{low_risk_high_return}</span>', "low risk / MOIC ≥ 2.0×")
        + ck_kpi_block("Danger Zone",
                       f'<span class="mn neg">{danger_zone}</span>', "high risk / MOIC < 1.0×")
        + ck_kpi_block("P50 Risk (realized)",
                       f'<span class="mn">{_percentile(sorted(risks), 50):.0f}</span>', "winning deals")
        + '</div>'
    )


def render_risk_matrix(sector_filter: str = "") -> str:
    from rcm_mc.ui._chartis_kit import chartis_shell, ck_section_header

    corpus = _load_corpus()
    if sector_filter:
        corpus_filtered = [d for d in corpus if d.get("sector") == sector_filter]
    else:
        corpus_filtered = corpus

    pts, sector_rows = _build_scatter_data(corpus_filtered)

    # Sector filter form
    sectors = sorted({d.get("sector") for d in corpus if d.get("sector")})
    sec_opts = '<option value="">All Sectors</option>' + "".join(
        f'<option value="{_html.escape(s)}" {"selected" if s==sector_filter else ""}>{_html.escape(s)}</option>'
        for s in sectors
    )
    filter_bar = f"""
<form method="get" action="/risk-matrix" class="ck-filters" style="margin-bottom:10px;">
  <span class="ck-filter-label">Sector</span>
  <select name="sector" class="ck-sel" onchange="this.form.submit()">{sec_opts}</select>
</form>"""

    kpis = _kpi_bar(pts)
    section_scatter = ck_section_header(
        "RISK / RETURN SCATTER",
        "entry risk score vs realized MOIC · hover for deal name"
    )
    scatter_svg = _risk_return_scatter(pts)
    scatter_panel = f"""
<div class="ck-panel">
  <div class="ck-panel-title">Entry Risk vs Realized MOIC — {len(pts)} corpus deals</div>
  <div style="padding:14px 16px 10px;">
    {scatter_svg}
    <div style="margin-top:6px;font-size:9.5px;color:var(--ck-text-faint);">
      X=entry risk (higher = riskier) · Y=realized MOIC · quadrant lines at risk=50, MOIC=2.0×
      · red dashed = 1.0× breakeven · colors = sector · hover dot for deal name
    </div>
  </div>
</div>"""

    section_heatmap = ck_section_header("SECTOR RISK-RETURN MATRIX", "average entry risk vs realized MOIC outcomes")
    heatmap = _sector_risk_heatmap(sector_rows)

    body = kpis + filter_bar + section_scatter + scatter_panel + section_heatmap + heatmap

    return chartis_shell(
        body,
        title="Risk Matrix",
        active_nav="/risk-matrix",
        subtitle=(
            f"{len(pts)} scored deals · "
            + (f"{sector_filter} only · " if sector_filter else "")
            + f"avg risk {sum(p[0] for p in pts)/len(pts):.0f}/100 · {len(sector_rows)} sectors"
        ) if pts else "corpus risk analysis",
    )
