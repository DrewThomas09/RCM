"""SeekingChartis Market Data — national hospital market intelligence.

Renders market heatmaps, regression analysis, state comparisons,
and hospital density maps. The primary data-exploration page.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from ._chartis_kit import chartis_shell
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
            bar_color = PALETTE["positive"] if coef > 0 else PALETTE["negative"]
            coef_rows += (
                f'<tr>'
                f'<td>{html.escape(feat.replace("_", " ").title())}</td>'
                f'<td class="num" style="color:{bar_color};">{direction}{coef:.4f}</td>'
                f'<td><div style="background:{PALETTE["bg_tertiary"]};border-radius:4px;height:8px;">'
                f'<div style="width:{bar_width:.0f}%;background:{bar_color};'
                f'border-radius:4px;height:8px;"></div></div></td>'
                f'</tr>'
            )

        return (
            f'<div class="cad-card">'
            f'<h2>Regression: What Predicts Hospital Margins?</h2>'
            f'<div style="display:flex;gap:16px;margin-bottom:12px;">'
            f'<div class="cad-kpi" style="flex:1;">'
            f'<div class="cad-kpi-value">{r2:.2%}</div>'
            f'<div class="cad-kpi-label">R-Squared</div></div>'
            f'<div class="cad-kpi" style="flex:1;">'
            f'<div class="cad-kpi-value">{len(stats)}</div>'
            f'<div class="cad-kpi-label">States Analyzed</div></div>'
            f'<div class="cad-kpi" style="flex:1;">'
            f'<div class="cad-kpi-value">{len(available)}</div>'
            f'<div class="cad-kpi-label">Features</div></div>'
            f'</div>'
            f'<p style="color:{PALETTE["text_secondary"]};font-size:12.5px;margin-bottom:12px;">'
            f'OLS regression of state-level average hospital operating margin on market '
            f'structure variables. Standardized coefficients shown.</p>'
            f'<table class="cad-table"><thead><tr>'
            f'<th>Variable</th><th>Coefficient</th><th>Magnitude</th>'
            f'</tr></thead><tbody>{coef_rows}</tbody></table></div>'
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
        f'<div class="cad-kpi-grid">'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{total_hospitals:,}</div>'
        f'<div class="cad-kpi-label">Total Hospitals (HCRIS)</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{total_beds:,}</div>'
        f'<div class="cad-kpi-label">Total Licensed Beds</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">${total_rev/1e12:.1f}T</div>'
        f'<div class="cad-kpi-label">Total Net Patient Revenue</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{avg_margin:.1%}</div>'
        f'<div class="cad-kpi-label">Avg Operating Margin</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{avg_hhi:,.0f}</div>'
        f'<div class="cad-kpi-label">Avg State HHI</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{avg_medicare:.0%}</div>'
        f'<div class="cad-kpi-label">Avg Medicare Mix</div></div>'
        f'</div>'
    )


def render_market_data(
    hcris_df: Optional[pd.DataFrame] = None,
    metric: str = "avg_margin",
) -> str:
    """Render the SeekingChartis market data page."""
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

    data_source = (
        f'<div class="cad-card" style="font-size:12px;">'
        f'<h2>Data Sources</h2>'
        f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;">'
        f'<div>'
        f'<div style="font-weight:600;color:{PALETTE["text_secondary"]};">HCRIS</div>'
        f'<div style="color:{PALETTE["text_muted"]};">CMS Hospital Cost Reports</div>'
        f'<div style="color:{PALETTE["text_muted"]};">~6,000 hospitals, annual</div>'
        f'</div>'
        f'<div>'
        f'<div style="font-weight:600;color:{PALETTE["text_secondary"]};">FRED</div>'
        f'<div style="color:{PALETTE["text_muted"]};">Federal Reserve Economic Data</div>'
        f'<div style="color:{PALETTE["text_muted"]};">Treasury yields, macro indicators</div>'
        f'</div>'
        f'<div>'
        f'<div style="font-weight:600;color:{PALETTE["text_secondary"]};">Capital IQ</div>'
        f'<div style="color:{PALETTE["text_muted"]};">Transaction multiples</div>'
        f'<div style="color:{PALETTE["text_muted"]};">Public hospital comps</div>'
        f'</div></div></div>'
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
    top_markets = (
        f'<div class="cad-card">'
        f'<h2>Top 10 Markets by Revenue</h2>'
        f'<p style="font-size:12px;color:{PALETTE["text_secondary"]};margin-bottom:8px;">'
        f'Top 10 states account for {cumulative_pct:.0f}% of national hospital revenue.</p>'
        f'<table class="cad-table"><thead><tr>'
        f'<th>State</th><th>Total NPR</th><th>% National</th><th>Cumulative</th>'
        f'<th>Hospitals</th><th>Margin</th><th>Concentration</th>'
        f'</tr></thead><tbody>{top_markets_rows}</tbody></table></div>'
    ) if top_markets_rows else ""

    # Margin health distribution
    profitable = sum(1 for s in stats if s["avg_margin"] > 0)
    struggling = len(stats) - profitable
    margin_dist = (
        f'<div class="cad-card">'
        f'<h2>Market Health</h2>'
        f'<div style="display:flex;gap:4px;height:24px;border-radius:6px;overflow:hidden;margin-bottom:8px;">'
        f'<div style="width:{profitable/max(len(stats),1)*100:.0f}%;background:{PALETTE["positive"]};" '
        f'title="Positive margin: {profitable}"></div>'
        f'<div style="width:{struggling/max(len(stats),1)*100:.0f}%;background:{PALETTE["negative"]};" '
        f'title="Negative margin: {struggling}"></div></div>'
        f'<div style="font-size:12px;display:flex;gap:16px;">'
        f'<span style="color:{PALETTE["positive"]};">&#9632; Positive margin: {profitable} states</span>'
        f'<span style="color:{PALETTE["negative"]};">&#9632; Negative margin: {struggling} states</span></div>'
        f'<p style="font-size:11px;color:{PALETTE["text_muted"]};margin-top:4px;">'
        f'Margins from HCRIS cost reports (median per state). Negative margins common '
        f'in states with high uncompensated care.</p></div>'
    ) if stats else ""

    # Medicare concentration
    high_med = sorted(stats, key=lambda s: -s["medicare_pct"])[:5]
    med_rows = ""
    for s in high_med:
        med_rows += (
            f'<tr><td><a href="/market-data/state/{s["state"]}">{s["state"]}</a></td>'
            f'<td class="num">{s["medicare_pct"]:.0%}</td>'
            f'<td class="num">{s["medicaid_pct"]:.0%}</td>'
            f'<td class="num">{s["commercial_pct"]:.0%}</td>'
            f'<td class="num">{s["avg_margin"]:.1%}</td></tr>'
        )
    payer_section = (
        f'<div class="cad-card">'
        f'<h2>Highest Medicare Dependency</h2>'
        f'<p style="font-size:12px;color:{PALETTE["text_secondary"]};margin-bottom:8px;">'
        f'Most exposed to CMS rate changes.</p>'
        f'<table class="cad-table"><thead><tr>'
        f'<th>State</th><th>Medicare</th><th>Medicaid</th><th>Commercial</th><th>Margin</th>'
        f'</tr></thead><tbody>{med_rows}</tbody></table></div>'
    ) if med_rows else ""

    body = (
        f'{kpi_section}'
        f'{margin_dist}'
        f'{top_markets}'
        f'<div class="cad-card"><h2>State Market Heatmap</h2>{heatmap}</div>'
        f'{regression}'
        f'{payer_section}'
        f'{data_source}'
    )

    from rcm_mc.ui._chartis_kit import ck_related_views
    related = ck_related_views([
        ("Deal Screening",        "/deal-screening"),
        ("Portfolio Analytics",   "/portfolio-analytics"),
        ("RCM Benchmarks",        "/rcm-benchmarks"),
        ("Hospital Screener",     "/screen"),
        ("Deals Library",         "/library"),
    ])

    return chartis_shell(
        body + related, "Market Data",
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
        margin_color = PALETTE["positive"] if margin > 0.05 else (PALETTE["warning"] if margin > 0 else PALETTE["negative"])

        rows += (
            f'<tr>'
            f'<td><a href="/hospital/{ccn}" style="font-weight:500;">{name}</a></td>'
            f'<td class="num">{beds}</td>'
            f'<td class="num">${rev/1e6:,.0f}M</td>'
            f'<td class="num" style="color:{margin_color};">{margin:.1%}</td>'
            f'<td style="white-space:nowrap;">'
            f'<a href="/hospital/{ccn}" class="cad-badge cad-badge-blue" '
            f'style="text-decoration:none;">Profile</a> '
            f'<a href="/models/dcf/{ccn}" class="cad-badge cad-badge-muted" '
            f'style="text-decoration:none;">DCF</a></td>'
            f'</tr>'
        )

    n = len(sdf)
    total_beds = int(sdf["beds"].fillna(0).sum())
    total_rev = float(sdf[rev_col].fillna(0).sum()) if rev_col in sdf.columns else 0

    kpis = (
        f'<div class="cad-kpi-grid">'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{n}</div>'
        f'<div class="cad-kpi-label">Hospitals</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{total_beds:,}</div>'
        f'<div class="cad-kpi-label">Total Beds</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">${total_rev/1e9:.1f}B</div>'
        f'<div class="cad-kpi-label">Total NPR</div></div>'
        f'</div>'
    )

    body = (
        f'{kpis}'
        f'<div class="cad-card">'
        f'<h2>Hospitals in {html.escape(state_upper)} ({n})</h2>'
        f'<table class="cad-table"><thead><tr>'
        f'<th>Hospital</th><th>Beds</th><th>NPR</th><th>Margin</th><th>Actions</th>'
        f'</tr></thead><tbody>{rows}</tbody></table></div>'
        f'<div style="display:flex;gap:8px;justify-content:center;margin-top:12px;">'
        f'<a href="/screen?state={html.escape(state_upper)}" class="cad-btn cad-btn-primary" '
        f'style="text-decoration:none;">Screen {html.escape(state_upper)} Hospitals</a>'
        f'<a href="/market-data/map" class="cad-btn" style="text-decoration:none;">'
        f'&larr; National View</a></div>'
    )

    return chartis_shell(
        body, f"Market: {state_upper}",
        active_nav="/market-data/map",
        subtitle=f"{n} hospitals in {state_upper}",
    )
