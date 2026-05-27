"""PE Desk Market Data — national hospital market intelligence.

Renders market heatmaps, regression analysis, state comparisons,
and hospital density maps. The primary data-exploration page.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from ._chartis_kit import (
    chartis_shell, ck_kpi_block, ck_next_section, ck_page_title,
    ck_panel, ck_section_header, ck_section_intro, ck_signal_badge,
    ck_source_purpose,
)
from .brand import PALETTE


_STATE_ABBREVS = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
]


def _compute_state_stats(hcris_df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Aggregate HCRIS data by state for the heatmap."""
    rev_col = "net_patient_revenue" if "net_patient_revenue" in hcris_df.columns else "gross_patient_revenue"
    stats = []
    for state in sorted(hcris_df["state"].dropna().unique()):
        sdf = hcris_df[hcris_df["state"] == state]
        n = len(sdf)
        if n == 0:
            continue
        beds = sdf["beds"].fillna(0)
        rev = sdf[rev_col].fillna(0) if rev_col in sdf.columns else pd.Series(0, index=sdf.index)
        opex = sdf["operating_expenses"].fillna(0) if "operating_expenses" in sdf.columns else pd.Series(0, index=sdf.index)
        margin_vals = []
        for r, o in zip(rev, opex):
            if r > 1e5 and o > 0:
                m = (r - o) / r
                if -1.0 <= m <= 1.0:
                    margin_vals.append(m)

        avg_margin = float(np.median(margin_vals)) if margin_vals else 0
        total_beds = int(beds.sum())
        total_rev = float(rev.sum())
        avg_beds = float(beds.mean())

        # HHI for concentration
        shares = (rev / total_rev).fillna(0) if total_rev > 0 else pd.Series(0, index=sdf.index)
        hhi = float((shares ** 2).sum()) * 10000

        # Medicare/Medicaid mix
        med_pct = float(sdf["medicare_day_pct"].mean()) if "medicare_day_pct" in sdf.columns else 0
        mcd_pct = float(sdf["medicaid_day_pct"].mean()) if "medicaid_day_pct" in sdf.columns else 0

        stats.append({
            "state": state,
            "hospitals": n,
            "total_beds": total_beds,
            "avg_beds": round(avg_beds, 0),
            "total_revenue": total_rev,
            "avg_margin": round(avg_margin, 4),
            "hhi": round(hhi, 0),
            "medicare_pct": round(med_pct, 3),
            "medicaid_pct": round(mcd_pct, 3),
            "commercial_pct": round(max(0, 1 - med_pct - mcd_pct), 3),
        })

    stats.sort(key=lambda s: -s["hospitals"])
    return stats


def _heatmap_color(value: float, low: float, high: float, invert: bool = False) -> str:
    """Map a value to a red-yellow-green color scale."""
    if high == low:
        return PALETTE["text_muted"]
    pct = max(0, min(1, (value - low) / (high - low)))
    if invert:
        pct = 1 - pct
    if pct > 0.5:
        g = int(185 + (pct - 0.5) * 2 * 70)
        r = int(255 - (pct - 0.5) * 2 * 200)
        return f"rgb({r},{g},50)"
    else:
        r = int(239 - pct * 2 * 40)
        g = int(68 + pct * 2 * 180)
        return f"rgb({r},{g},50)"


def _state_heatmap_table(stats: List[Dict[str, Any]], metric: str) -> str:
    """Build an interactive heatmap table colored by the selected metric."""
    if not stats:
        return f'<p style="color:{PALETTE["text_muted"]};">No HCRIS data available.</p>'

    metric_labels = {
        "avg_margin": ("Avg Margin", False),
        "hhi": ("HHI (Concentration)", True),
        "hospitals": ("Hospital Count", False),
        "avg_beds": ("Avg Beds", False),
        "medicare_pct": ("Medicare %", True),
        "total_revenue": ("Total Revenue", False),
    }
    label, invert = metric_labels.get(metric, ("Metric", False))

    vals = [s[metric] for s in stats if metric in s]
    lo, hi = (min(vals), max(vals)) if vals else (0, 1)

    # Metric selector
    selector = '<div style="display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap;">'
    for m, (ml, _) in metric_labels.items():
        active = f'background:{PALETTE["brand_accent"]};color:white;border-color:{PALETTE["brand_accent"]};' if m == metric else ""
        selector += (
            f'<a href="/market-data/map?metric={m}" class="cad-btn" '
            f'style="text-decoration:none;{active}">{html.escape(ml)}</a>'
        )
    selector += '</div>'

    rows = ""
    for s in stats[:30]:
        val = s.get(metric, 0)
        bg = _heatmap_color(val, lo, hi, invert)

        if metric == "avg_margin":
            fmt_val = f"{val:.1%}"
        elif metric == "total_revenue":
            fmt_val = f"${val / 1e9:.1f}B"
        elif metric in ("medicare_pct", "medicaid_pct", "commercial_pct"):
            fmt_val = f"{val:.0%}"
        elif metric == "hhi":
            fmt_val = f"{val:,.0f}"
        else:
            fmt_val = f"{val:,.0f}"

        conc_label = "Concentrated" if s["hhi"] > 2500 else ("Moderate" if s["hhi"] > 1500 else "Competitive")
        conc_cls = "cad-badge-red" if s["hhi"] > 2500 else ("cad-badge-amber" if s["hhi"] > 1500 else "cad-badge-green")

        rows += (
            f'<tr>'
            f'<td><a href="/market-data/state/{s["state"]}" '
            f'style="font-weight:600;">{s["state"]}</a></td>'
            f'<td class="num">{s["hospitals"]}</td>'
            f'<td class="num">{s["total_beds"]:,}</td>'
            f'<td class="num">${s["total_revenue"]/1e9:.1f}B</td>'
            f'<td class="num" style="color:{bg};font-weight:600;">{fmt_val}</td>'
            f'<td class="num">{s["avg_margin"]:.1%}</td>'
            f'<td><span class="cad-badge {conc_cls}">{conc_label}</span></td>'
            f'<td class="num">{s["medicare_pct"]:.0%}</td>'
            f'<td class="num">{s["medicaid_pct"]:.0%}</td>'
            f'</tr>'
        )

    table = (
        f'{selector}'
        f'<table class="cad-table">'
        f'<thead><tr>'
        f'<th>State</th><th>Hospitals</th><th>Total Beds</th><th>Total NPR</th>'
        f'<th style="background:{PALETTE["brand_primary"]}22;">{html.escape(label)}</th>'
        f'<th>Avg Margin</th><th>Concentration</th><th>Medicare</th><th>Medicaid</th>'
        f'</tr></thead>'
        f'<tbody>{rows}</tbody></table>'
    )

    return table


def _regression_section(stats: List[Dict[str, Any]]) -> str:
    """Build a regression summary: what predicts hospital margins?"""
    if len(stats) < 5:
        return ""

    try:
        df = pd.DataFrame(stats)
        features = ["hospitals", "avg_beds", "hhi", "medicare_pct", "medicaid_pct"]
        target = "avg_margin"
        available = [f for f in features if f in df.columns and df[f].notna().sum() > 3]

        if not available or target not in df.columns:
            return ""

        X = df[available].fillna(0).values
        y = df[target].fillna(0).values

        X_mean = X.mean(axis=0)
        X_std = X.std(axis=0)
        X_std[X_std == 0] = 1
        X_norm = (X - X_mean) / X_std
        X_aug = np.column_stack([np.ones(len(X_norm)), X_norm])

        try:
            beta = np.linalg.lstsq(X_aug, y, rcond=None)[0]
        except np.linalg.LinAlgError:
            return ""

        y_hat = X_aug @ beta
        ss_res = np.sum((y - y_hat) ** 2)
        ss_tot = np.sum((y - y.mean()) ** 2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0

        coef_rows = ""
        for i, feat in enumerate(available):
            coef = beta[i + 1]
            direction = "+" if coef > 0 else ""
            magnitude = abs(coef)
            bar_width = min(100, magnitude / max(abs(beta[1:]).max(), 0.001) * 100)
            coef_cls = "cad-pos" if coef > 0 else "cad-neg"
            coef_rows += (
                f'<tr>'
                f'<td>{html.escape(feat.replace("_", " ").title())}</td>'
                f'<td class="num {coef_cls}"><strong>{direction}{coef:.4f}</strong></td>'
                f'<td><div class="md-coef-track">'
                f'<div class="md-coef-fill" style="width:{bar_width:.0f}%;'
                f'background:var(--cad-{"pos" if coef > 0 else "neg"});"></div></div></td>'
                f'</tr>'
            )

        kpi_strip = (
            '<div class="ck-kpi-strip">'
            + ck_kpi_block("R-Squared", f"{r2:.2%}")
            + ck_kpi_block("States Analyzed", f"{len(stats)}")
            + ck_kpi_block("Features", f"{len(available)}")
            + '</div>'
        )
        return ck_panel(
            f'{kpi_strip}'
            '<p class="ck-section-body">'
            'OLS regression of state-level average hospital operating margin on market '
            'structure variables. Standardized coefficients shown.</p>'
            '<table class="cad-table"><thead><tr>'
            '<th>Variable</th><th>Coefficient</th><th>Magnitude</th>'
            f'</tr></thead><tbody>{coef_rows}</tbody></table>',
            title="Regression: What Predicts Hospital Margins?",
        )
    except Exception:
        return ""


def _kpi_summary(stats: List[Dict[str, Any]]) -> str:
    """Top-level KPI cards from HCRIS data."""
    if not stats:
        return ""

    total_hospitals = sum(s["hospitals"] for s in stats)
    total_beds = sum(s["total_beds"] for s in stats)
    total_rev = sum(s["total_revenue"] for s in stats)
    avg_margin = float(np.mean([s["avg_margin"] for s in stats])) if stats else 0
    avg_hhi = float(np.mean([s["hhi"] for s in stats])) if stats else 0
    avg_medicare = float(np.mean([s["medicare_pct"] for s in stats])) if stats else 0

    return (
        '<div class="ck-kpi-strip">'
        + ck_kpi_block("Total Hospitals (HCRIS)", f"{total_hospitals:,}")
        + ck_kpi_block("Total Licensed Beds", f"{total_beds:,}")
        + ck_kpi_block(
            "Total Net Patient Revenue", f"${total_rev/1e12:.1f}T",
            help={
                "definition": (
                    "Aggregate net patient revenue across every "
                    "HCRIS-filing hospital. Runs ~$1.3T US-wide in a "
                    "normal year; growth tracks healthcare CPI + "
                    "utilization shifts. The denominator behind every "
                    "national margin / DAR / denial benchmark."
                ),
            },
        )
        + ck_kpi_block(
            "Avg Operating Margin", f"{avg_margin:.1%}",
            help={
                "definition": (
                    "Mean operating margin across the credibility-"
                    "filtered HCRIS universe. Runs ~3-5% — most "
                    "hospitals don't make money operationally and "
                    "survive on Medicare DSH / 340B / supplemental "
                    "payments. PE underwriting needs to clear this "
                    "operational floor to make economic sense."
                ),
            },
        )
        + ck_kpi_block(
            "Avg State HHI", f"{avg_hhi:,.0f}",
            help={
                "definition": (
                    "Herfindahl-Hirschman Index averaged across "
                    "states — sum of squared market shares × 10,000. "
                    "DOJ thresholds: <1,500 = unconcentrated, "
                    "1,500-2,500 = moderately concentrated, "
                    ">2,500 = highly concentrated. Most US hospital "
                    "markets are concentrated (>2,500); regulatory "
                    "review of bolt-ons gets harder above 3,500."
                ),
                "citation": "DOJ Horizontal Merger Guidelines",
            },
        )
        + ck_kpi_block(
            "Avg Medicare Mix", f"{avg_medicare:.0%}",
            help={
                "definition": (
                    "Share of total inpatient days from Medicare "
                    "patients. US average ~45%; above 60% = the "
                    "hospital is structurally exposed to CMS rate "
                    "decisions; below 30% = unusual (often a "
                    "specialty platform or pediatric center)."
                ),
            },
        )
        + "</div>"
    )


def _top_markets_bar_chart(top_rev: List[Dict[str, Any]],
                           total_national_rev: float,
                           width: int = 720,
                           height: int = 280) -> str:
    """Horizontal bars per state showing revenue share + cumulative line.

    HHI concentration colors the bar:
      - HHI >2500 (concentrated) → red
      - HHI >1500 (moderate)     → amber
      - else (competitive)       → teal-deep
    """
    if not top_rev or total_national_rev <= 0:
        return ""
    pad_l, pad_r, pad_t, pad_b = 70, 100, 20, 24
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b
    n = len(top_rev)
    row_h = plot_h / n
    max_pct = max((s["total_revenue"] / total_national_rev * 100) for s in top_rev)

    bars_svg = ""
    cum_pts: List[tuple] = []
    cum_pct = 0.0
    for i, s in enumerate(top_rev):
        share_pct = s["total_revenue"] / total_national_rev * 100
        cum_pct += share_pct
        cy = pad_t + row_h * i + row_h / 2
        bw = (share_pct / max_pct) * plot_w if max_pct > 0 else 0
        hhi = s.get("hhi", 0)
        fill = (
            "#A53A2D" if hhi > 2500
            else "#b8732a" if hhi > 1500
            else "#155752"
        )
        bars_svg += (
            f'<text x="{pad_l - 10}" y="{cy + 3:.1f}" '
            f'font-family="Inter Tight,sans-serif" font-size="11" '
            f'font-weight="700" fill="#1a2332" text-anchor="end">'
            f'{html.escape(s["state"])}</text>'
            f'<rect x="{pad_l}" y="{cy - row_h * 0.30:.1f}" '
            f'width="{bw:.1f}" height="{row_h * 0.58:.1f}" '
            f'fill="{fill}" opacity="0.9" rx="1"/>'
            f'<text x="{pad_l + bw + 6:.1f}" y="{cy + 4:.1f}" '
            f'font-family="JetBrains Mono,monospace" font-size="10" '
            f'font-weight="700" fill="#1a2332">'
            f'${s["total_revenue"] / 1e9:.1f}B'
            f'</text>'
            f'<text x="{pad_l + bw + 6:.1f}" y="{cy + 16:.1f}" '
            f'font-family="JetBrains Mono,monospace" font-size="9" '
            f'fill="#5C6878">'
            f'{share_pct:.1f}% · {cum_pct:.0f}% cum</text>'
        )
        # Cumulative line point at the END of each row (right-rail)
        cum_pts.append((cy, cum_pct))

    # Cumulative overlay line (anchored to the % axis 0-100)
    line_x = pad_l + plot_w + 40
    line_w = 40
    line_svg = ""
    if cum_pts:
        path = " ".join(
            f"{'M' if j == 0 else 'L'} "
            f"{line_x + (pct / 100) * line_w:.1f},{cy:.1f}"
            for j, (cy, pct) in enumerate(cum_pts)
        )
        line_svg = (
            f'<path d="{path}" stroke="#0F1C2E" stroke-width="1.6" '
            f'fill="none" opacity="0.7"/>'
        )

    # Legend / tone key (bottom row)
    legend_y = height - 6
    legend_svg = (
        f'<rect x="{pad_l}" y="{legend_y - 9}" width="10" height="8" '
        f'fill="#155752" opacity="0.9" rx="1"/>'
        f'<text x="{pad_l + 14}" y="{legend_y - 1}" '
        f'font-family="Inter Tight,sans-serif" font-size="9.5" '
        f'fill="#5C6878">Competitive</text>'
        f'<rect x="{pad_l + 100}" y="{legend_y - 9}" width="10" height="8" '
        f'fill="#b8732a" opacity="0.9" rx="1"/>'
        f'<text x="{pad_l + 114}" y="{legend_y - 1}" '
        f'font-family="Inter Tight,sans-serif" font-size="9.5" '
        f'fill="#5C6878">Moderate</text>'
        f'<rect x="{pad_l + 192}" y="{legend_y - 9}" width="10" height="8" '
        f'fill="#A53A2D" opacity="0.9" rx="1"/>'
        f'<text x="{pad_l + 206}" y="{legend_y - 1}" '
        f'font-family="Inter Tight,sans-serif" font-size="9.5" '
        f'fill="#5C6878">Concentrated (HHI&gt;2500)</text>'
    )

    return (
        f'<svg viewBox="0 0 {width} {height}" '
        f'preserveAspectRatio="xMidYMid meet" '
        f'style="width:100%;max-width:{width}px;height:auto;display:block;'
        f'margin:0 auto 1rem;">'
        f'{bars_svg}{line_svg}{legend_svg}</svg>'
    )


_MARKET_CHART_CAPTION_CSS = """
<style>
.mkt-chart-caption {
  font-family: "Inter Tight","Inter",sans-serif;
  font-size: .72rem; color: #5C6878;
  text-align: center; letter-spacing: 0.06em;
  text-transform: uppercase; margin: -.5rem 0 1.25rem;
}
@media print {
  .mkt-chart-caption { color: #1a2332; }
  svg { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
}
</style>
"""


def render_market_data(
    hcris_df: Optional[pd.DataFrame] = None,
    metric: str = "avg_margin",
) -> str:
    """Render the PE Desk market data page."""
    if hcris_df is None:
        try:
            from ..data.hcris import _get_latest_per_ccn
            hcris_df = _get_latest_per_ccn()
        except Exception:
            hcris_df = pd.DataFrame()

    all_stats = _compute_state_stats(hcris_df) if not hcris_df.empty else []
    # Filter to 50 states + DC for the main view (exclude territories like GU, VI, AS, MP, PR)
    us_states = set(_STATE_ABBREVS) | {"DC"}
    stats = [s for s in all_stats if s["state"] in us_states]
    territory_stats = [s for s in all_stats if s["state"] not in us_states]

    kpi_section = _kpi_summary(stats)
    heatmap = _state_heatmap_table(stats, metric)
    regression = _regression_section(stats)

    # Reusable US state tile-grid map, shaded by the selected metric. Real
    # HCRIS per-state aggregates (same data as the heatmap table below,
    # which is preserved). Local SVG — no external map tiles.
    from .us_geo_map import render_us_geo_map
    _MAP_FMT = {
        "avg_margin": (lambda v: f"{v * 100:.1f}%", "operating margin"),
        "hhi": (lambda v: f"{v:,.0f}", "HHI concentration"),
        "hospitals": (lambda v: f"{int(v):,}", "hospitals"),
        "total_revenue": (lambda v: f"${v / 1e9:.1f}B", "total NPR"),
        "medicare_pct": (lambda v: f"{v * 100:.0f}%", "Medicare day %"),
    }
    _vfmt, _mlabel = _MAP_FMT.get(metric, (None, metric.replace("_", " ")))
    state_map_panel = ""
    if stats:
        _state_vals = {
            s["state"]: s.get(metric)
            for s in stats if s.get(metric) is not None
        }
        state_map_panel = ck_panel(
            render_us_geo_map(
                _state_vals, metric_label=_mlabel, value_format=_vfmt,
                state_link_template="/market-data/state/{state}",
                empty_message="No state-level HCRIS data available yet.",
            )
            + '<p style="font-size:11px;color:var(--sc-text-dim);margin:8px 0 0;">'
            'Real US state map shaded by the metric. '
            'Click a state to drill into its hospitals.</p>',
            title=f"State Map · {_mlabel}",
        )

    data_source = ck_panel(
        '<div class="ck-card-grid">'
        '<div><strong>HCRIS</strong><br>'
        'CMS Hospital Cost Reports<br>'
        '<em>~6,000 hospitals, annual</em></div>'
        '<div><strong>FRED</strong><br>'
        'Federal Reserve Economic Data<br>'
        '<em>Treasury yields, macro indicators</em></div>'
        '<div><strong>Capital IQ</strong><br>'
        'Transaction multiples<br>'
        '<em>Public hospital comps</em></div>'
        '</div>',
        title="Data Sources",
    )

    # Top markets by revenue
    top_rev = sorted(stats, key=lambda s: -s["total_revenue"])[:10]
    top_markets_rows = ""
    total_national_rev = sum(s["total_revenue"] for s in stats)
    cumulative_pct = 0
    for s in top_rev:
        pct = s["total_revenue"] / total_national_rev * 100 if total_national_rev > 0 else 0
        cumulative_pct += pct
        conc_label = "Concentrated" if s["hhi"] > 2500 else ("Moderate" if s["hhi"] > 1500 else "Competitive")
        conc_cls = "cad-badge-red" if s["hhi"] > 2500 else ("cad-badge-amber" if s["hhi"] > 1500 else "cad-badge-green")
        top_markets_rows += (
            f'<tr>'
            f'<td><a href="/market-data/state/{s["state"]}" style="font-weight:600;">{s["state"]}</a></td>'
            f'<td class="num">${s["total_revenue"]/1e9:.1f}B</td>'
            f'<td class="num">{pct:.1f}%</td>'
            f'<td class="num">{cumulative_pct:.0f}%</td>'
            f'<td class="num">{s["hospitals"]}</td>'
            f'<td class="num">{s["avg_margin"]:.1%}</td>'
            f'<td><span class="cad-badge {conc_cls}">{conc_label}</span></td>'
            f'</tr>'
        )
    top_markets_chart = _top_markets_bar_chart(top_rev, total_national_rev)
    top_markets_caption = (
        '<div class="mkt-chart-caption">'
        'Revenue share by state · color = HHI concentration tier'
        '</div>'
    ) if top_markets_chart else ""
    top_markets = ck_panel(
        '<p class="ck-section-body">'
        f'Top 10 states account for {cumulative_pct:.0f}% of national hospital revenue.</p>'
        + top_markets_chart + top_markets_caption +
        '<table class="cad-table"><thead><tr>'
        '<th>State</th><th>Total NPR</th><th>% National</th><th>Cumulative</th>'
        '<th>Hospitals</th><th>Margin</th><th>Concentration</th>'
        f'</tr></thead><tbody>{top_markets_rows}</tbody></table>',
        title="Top 10 Markets by Revenue",
    ) if top_markets_rows else ""

    # Margin health distribution
    profitable = sum(1 for s in stats if s["avg_margin"] > 0)
    struggling = len(stats) - profitable
    pos_pct = profitable/max(len(stats),1)*100
    neg_pct = struggling/max(len(stats),1)*100
    margin_dist = ck_panel(
        '<div class="md-margin-bar">'
        f'<div class="md-margin-pos" style="width:{pos_pct:.0f}%;"></div>'
        f'<div class="md-margin-neg" style="width:{neg_pct:.0f}%;"></div></div>'
        '<p class="ck-section-body">'
        f'<span class="cad-pos">&#9632; Positive margin: {profitable} states</span> &nbsp; '
        f'<span class="cad-neg">&#9632; Negative margin: {struggling} states</span></p>'
        '<p class="ck-eyebrow">'
        'Margins from HCRIS cost reports (median per state). Negative margins common '
        'in states with high uncompensated care.</p>',
        title="Market Health",
    ) if stats else ""

    # Medicare concentration
    high_med = sorted(stats, key=lambda s: -s["medicare_pct"])[:5]
    med_rows = ""
    for s in high_med:
        med_rows += (
            f'<tr><td><a href="/market-data/state/{s["state"]}" class="ck-link">{s["state"]}</a></td>'
            f'<td class="num">{s["medicare_pct"]:.0%}</td>'
            f'<td class="num">{s["medicaid_pct"]:.0%}</td>'
            f'<td class="num">{s["commercial_pct"]:.0%}</td>'
            f'<td class="num">{s["avg_margin"]:.1%}</td></tr>'
        )
    payer_section = ck_panel(
        '<p class="ck-section-body">Most exposed to CMS rate changes.</p>'
        '<table class="cad-table"><thead><tr>'
        '<th>State</th><th>Medicare</th><th>Medicaid</th><th>Commercial</th><th>Margin</th>'
        f'</tr></thead><tbody>{med_rows}</tbody></table>',
        title="Highest Medicare Dependency",
    ) if med_rows else ""

    # B11 — add explicit page title above the section intro. Pre-fix,
    # this page rendered with no h1 (only the breadcrumb + ck_section_intro
    # subhead), so partners landing here saw KPI tiles + heatmap without
    # an editorial anchor explaining what they were looking at.
    page_title = ck_page_title(
        "National Hospital Market Intelligence",
        eyebrow="MARKET DATA",
        meta=f"HCRIS-derived state-level data · 50 states + DC",
    )
    intro = ck_section_intro(
        eyebrow="MARKET DATA",
        headline="National hospital market intelligence.",
        italic_word="market",
        body=(
            "HCRIS-derived state-level operating margin, payer mix, "
            "concentration (HHI), and revenue distribution across "
            "all 50 states + DC. Heatmap on margin / HHI / Medicare "
            "lets partners spot the markets most exposed to rate "
            "compression, payer concentration, or pricing power."
        ),
    )
    md_styles = """
<style>
.md-margin-bar{display:flex;gap:4px;height:24px;border-radius:6px;
overflow:hidden;margin-bottom:8px;}
.md-margin-pos{background:var(--cad-pos);}
.md-margin-neg{background:var(--cad-neg);}
.md-coef-track{background:var(--cad-bg3);border-radius:4px;height:8px;}
.md-coef-fill{border-radius:4px;height:8px;}
</style>
"""
    body = (
        f'{md_styles}'
        f'{_MARKET_CHART_CAPTION_CSS}'
        f'{page_title}'
        f'{intro}'
        f'{kpi_section}'
        f'{margin_dist}'
        f'{top_markets}'
        + state_map_panel
        + ck_panel(heatmap, title="State Market Heatmap")
        + f'{regression}'
        f'{payer_section}'
        f'{data_source}'
        + ck_next_section(
            "Open the hospital screener",
            "/screen",
            eyebrow="Continue —",
            italic_word="screener",
        )
    )

    return chartis_shell(
        body, "Market Data",
        active_nav="/market-data/map",
        subtitle=f"National hospital market intelligence — 50 states + DC" + (
            f" + {len(territory_stats)} US territories" if territory_stats else ""
        ),
    )


def render_state_detail(
    state: str,
    hcris_df: Optional[pd.DataFrame] = None,
) -> str:
    """Render state-level detail page with hospital list."""
    if hcris_df is None:
        try:
            from ..data.hcris import _get_latest_per_ccn
            hcris_df = _get_latest_per_ccn()
        except Exception:
            hcris_df = pd.DataFrame()

    state_upper = state.upper()
    sdf = hcris_df[hcris_df["state"] == state_upper] if not hcris_df.empty else pd.DataFrame()

    rev_col = "net_patient_revenue" if "net_patient_revenue" in sdf.columns else "gross_patient_revenue"

    rows = ""
    for _, h in sdf.sort_values(rev_col, ascending=False).head(50).iterrows():
        ccn = html.escape(str(h.get("ccn", "")))
        name = html.escape(str(h.get("name", ""))[:50])
        beds = int(h.get("beds", 0))
        rev = float(h.get(rev_col, 0))
        opex = float(h.get("operating_expenses", 0))
        margin = (rev - opex) / rev if rev > 1e5 and opex > 0 else 0
        margin = max(-1.0, min(1.0, margin))
        margin_cls = "cad-pos" if margin > 0.05 else ("cad-warn" if margin > 0 else "cad-neg")

        rows += (
            f'<tr>'
            f'<td><a href="/hospital/{ccn}" class="ck-link"><strong>{name}</strong></a></td>'
            f'<td class="num">{beds}</td>'
            f'<td class="num">${rev/1e6:,.0f}M</td>'
            f'<td class="num {margin_cls}">{margin:.1%}</td>'
            f'<td>'
            f'<a href="/hospital/{ccn}" class="cad-badge cad-badge-blue">Profile</a> '
            f'<a href="/models/dcf/{ccn}" class="cad-badge cad-badge-muted">DCF</a></td>'
            f'</tr>'
        )

    n = len(sdf)
    total_beds = int(sdf["beds"].fillna(0).sum())
    total_rev = float(sdf[rev_col].fillna(0).sum()) if rev_col in sdf.columns else 0

    kpis = (
        '<div class="ck-kpi-strip">'
        + ck_kpi_block("Hospitals", f"{n}")
        + ck_kpi_block("Total Beds", f"{total_beds:,}")
        + ck_kpi_block("Total NPR", f"${total_rev/1e9:.1f}B")
        + '</div>'
    )

    intro = ck_section_intro(
        eyebrow=f"MARKET — {html.escape(state_upper)}",
        headline=f"Hospitals in {html.escape(state_upper)}.",
        italic_word=html.escape(state_upper),
        body=f"{n} HCRIS-filed hospitals · ${total_rev/1e9:.1f}B total NPR.",
    )

    # Hospital point map — join this state's HCRIS hospitals to the vendored
    # CCN->lat/lon crosswalk by CCN. Plots ONLY hospitals with a real
    # geocoded coordinate; the rest stay in the table below (no fake points).
    from ..data.hospital_coords import load_hospital_coords, coords_provenance
    _coords = load_hospital_coords()

    def _coord_for(ccn_val) -> Any:
        s = str(ccn_val or "").strip()
        return _coords.get(s) or _coords.get(s.zfill(6))

    state_points = []
    if _coords:
        for _, h in sdf.iterrows():
            c = _coord_for(h.get("ccn", ""))
            if c is not None:
                state_points.append(c)
    map_panel = ""
    if state_points:
        from .us_map import render_state_hospital_points
        map_panel = ck_panel(
            render_state_hospital_points(
                state_points, state=state_upper, total_in_state=n,
                provenance=coords_provenance(),
            ),
            title=f"Hospital locations in {html.escape(state_upper)}",
        )
    table_panel = ck_panel(
        '<table class="cad-table"><thead><tr>'
        '<th>Hospital</th><th>Beds</th><th>NPR</th><th>Margin</th><th>Actions</th>'
        f'</tr></thead><tbody>{rows}</tbody></table>',
        title=f"Hospitals in {html.escape(state_upper)} ({n})",
    )
    actions = ck_panel(
        '<p class="ck-section-body">'
        f'<a href="/screen?state={html.escape(state_upper)}" class="cad-btn cad-btn-primary">'
        f'Screen {html.escape(state_upper)} Hospitals</a> '
        '<a href="/market-data/map" class="cad-btn">&larr; National View</a>'
        '</p>',
        title="Cross-links",
    )
    # Market context (licensed SimplyAnalytics-derived) — demographic/payer
    # context for this state; market context, not provider-specific.
    market_ctx = ""
    try:
        from .data_public.market_geo_page import market_context_panel
        market_ctx = market_context_panel(state_upper)
    except Exception:
        market_ctx = ""

    source_purpose = ck_source_purpose(
        purpose=f"Size the {html.escape(state_upper)} hospital market — count, revenue, margins — from real CMS cost-report filings before screening targets in it.",
        universe="hcris",
        source="CMS HCRIS hospital cost reports (state aggregate); market context, not a single deal.",
        next_action=f"Screen {html.escape(state_upper)} hospitals",
        next_href=f"/screen?state={html.escape(state_upper)}",
    )
    body = f'{intro}{source_purpose}{kpis}{market_ctx}{map_panel}{table_panel}{actions}'

    return chartis_shell(
        body, f"Market: {state_upper}",
        active_nav="/market-data/map",
        subtitle=f"{n} hospitals in {state_upper}",
    )
