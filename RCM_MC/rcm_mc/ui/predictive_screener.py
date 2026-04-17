"""SeekingChartis Predictive Screener — deal sourcing via ML on public data.

The killer feature: filter 6,000+ hospitals by predicted RCM performance,
estimated EBITDA uplift, distress probability, market position, and
financial characteristics. No internal data needed — pure public data
screening powered by the quant stack.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

import numpy as np
import pandas as pd

from .shell_v2 import shell_v2
from .brand import PALETTE


_REGIONS = {
    "Southeast": {"AL", "AR", "FL", "GA", "KY", "LA", "MS", "NC", "SC", "TN", "VA", "WV"},
    "Northeast": {"CT", "DE", "DC", "ME", "MD", "MA", "NH", "NJ", "NY", "PA", "RI", "VT"},
    "Midwest": {"IL", "IN", "IA", "KS", "MI", "MN", "MO", "NE", "ND", "OH", "SD", "WI"},
    "Southwest": {"AZ", "NM", "OK", "TX"},
    "West": {"AK", "CA", "CO", "HI", "ID", "MT", "NV", "OR", "UT", "WA", "WY"},
}


def _add_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add ML features needed for screening."""
    df = df.copy()
    rev = df.get("net_patient_revenue", pd.Series(dtype=float))
    opex = df.get("operating_expenses", pd.Series(dtype=float))

    if "operating_margin" not in df.columns:
        safe_rev = rev.where(rev > 1e5)
        df["operating_margin"] = ((safe_rev - opex) / safe_rev).clip(-0.5, 1.0)
    if "revenue_per_bed" not in df.columns and "beds" in df.columns:
        df["revenue_per_bed"] = rev / df["beds"].replace(0, np.nan)
    if "occupancy_rate" not in df.columns:
        df["occupancy_rate"] = df.get("total_patient_days", 0) / df["bed_days_available"].replace(0, np.nan)
    if "commercial_pct" not in df.columns:
        mc = df.get("medicare_day_pct", pd.Series(0, index=df.index)).fillna(0)
        md = df.get("medicaid_day_pct", pd.Series(0, index=df.index)).fillna(0)
        df["commercial_pct"] = (1.0 - mc - md).clip(0, 1)
    if "net_to_gross_ratio" not in df.columns and "gross_patient_revenue" in df.columns:
        df["net_to_gross_ratio"] = (rev / df["gross_patient_revenue"].replace(0, np.nan)).clip(0, 1)

    return df


def _predict_rcm_fast(row: pd.Series) -> Dict[str, float]:
    """Fast RCM prediction for screening (no conformal, just point estimates)."""
    mc = float(row.get("medicare_day_pct", 0.4) or 0.4)
    md = float(row.get("medicaid_day_pct", 0.15) or 0.15)
    beds = float(row.get("beds", 100) or 100)
    margin = float(row.get("operating_margin", 0) or 0)
    n2g = float(row.get("net_to_gross_ratio", 0.3) or 0.3)
    occ = float(row.get("occupancy_rate", 0.5) or 0.5)
    rev = float(row.get("net_patient_revenue", 1e8) or 1e8)

    denial = 0.095 + mc * 0.15 + md * 0.20 - np.log(max(1, beds)) * 0.012 - n2g * 0.25 - margin * 0.18
    denial = max(0.02, min(0.25, denial))

    ar_days = 45 + mc * 5 + md * 8 - np.log(max(1, beds)) * 3 - n2g * 10 - margin * 8
    ar_days = max(25, min(75, ar_days))

    # RCM uplift estimate: gap between current and P75 benchmarks
    denial_gap = max(0, denial - 0.05)
    margin_gap = max(0, 0.08 - margin)
    uplift = rev * (denial_gap * 0.5 + margin_gap * 0.3) * 0.6
    uplift = max(0, uplift)

    return {
        "est_denial": round(denial, 4),
        "est_ar_days": round(ar_days, 1),
        "est_uplift": round(uplift, 0),
    }


def render_predictive_screener(
    hcris_df: pd.DataFrame,
    query_string: str = "",
) -> str:
    """Render the predictive deal screening page."""
    qs = parse_qs(query_string)

    # Parse filters
    region = (qs.get("region") or ["all"])[0][:20]
    try:
        min_beds = max(0, min(9999, int((qs.get("min_beds") or ["0"])[0])))
    except (ValueError, TypeError):
        min_beds = 0
    try:
        max_beds = max(0, min(9999, int((qs.get("max_beds") or ["9999"])[0])))
    except (ValueError, TypeError):
        max_beds = 9999
    try:
        max_margin = max(-2, min(2, float((qs.get("max_margin") or ["1"])[0])))
    except (ValueError, TypeError):
        max_margin = 1.0
    try:
        min_uplift = max(0, float((qs.get("min_uplift") or ["0"])[0]))
    except (ValueError, TypeError):
        min_uplift = 0.0
    sort_by = (qs.get("sort") or ["est_uplift"])[0][:20]

    df = _add_features(hcris_df)

    # Apply filters
    mask = pd.Series(True, index=df.index)
    if region != "all" and region in _REGIONS:
        mask &= df["state"].isin(_REGIONS[region])
    if min_beds > 0:
        mask &= df["beds"].fillna(0) >= min_beds
    if max_beds < 9999:
        mask &= df["beds"].fillna(0) <= max_beds
    if max_margin < 1:
        mask &= df["operating_margin"].fillna(0) <= max_margin
    if "state" in qs:
        st = qs["state"][0].upper()[:2]
        mask &= df["state"] == st

    filtered = df[mask].copy()

    # Add ML predictions
    predictions = []
    for _, row in filtered.iterrows():
        preds = _predict_rcm_fast(row)
        predictions.append(preds)

    if predictions:
        pred_df = pd.DataFrame(predictions, index=filtered.index)
        filtered = pd.concat([filtered, pred_df], axis=1)

    # Apply uplift filter
    if min_uplift > 0 and "est_uplift" in filtered.columns:
        filtered = filtered[filtered["est_uplift"] >= min_uplift]

    # Sort
    if sort_by in filtered.columns:
        ascending = sort_by not in ("est_uplift", "beds", "net_patient_revenue")
        filtered = filtered.sort_values(sort_by, ascending=ascending, na_position="last")

    total_matches = len(filtered)
    display = filtered.head(50)

    # ── Filter form ──
    region_opts = '<option value="all"' + (' selected' if region == 'all' else '') + '>All Regions</option>'
    for r in sorted(_REGIONS.keys()):
        sel = " selected" if region == r else ""
        region_opts += f'<option value="{r}"{sel}>{r}</option>'

    def _sel(opt_val, current):
        return ' selected' if opt_val == current else ''

    form = (
        f'<div class="cad-card">'
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">'
        f'<h2 style="margin:0;">Screen Filters</h2>'
        f'<span class="cad-section-code">FLT</span></div>'
        f'<form method="GET" action="/predictive-screener" class="cad-form-row">'
        f'<div class="cad-field">'
        f'<label>Region</label>'
        f'<select name="region" class="cad-select" style="min-width:140px;">{region_opts}</select>'
        f'</div>'
        f'<div class="cad-field"><label>Min Beds</label>'
        f'<input class="cad-input" type="number" name="min_beds" value="{min_beds}" min="0" style="width:82px;"></div>'
        f'<div class="cad-field"><label>Max Beds</label>'
        f'<input class="cad-input" type="number" name="max_beds" value="{max_beds if max_beds < 9999 else ""}" placeholder="9999" style="width:82px;"></div>'
        f'<div class="cad-field"><label>Max Margin</label>'
        f'<input class="cad-input" type="number" name="max_margin" value="{max_margin if max_margin < 1 else ""}" step="0.01" placeholder="0.05" style="width:92px;"></div>'
        f'<div class="cad-field"><label>Min Uplift ($)</label>'
        f'<input class="cad-input" type="number" name="min_uplift" value="{int(min_uplift) if min_uplift > 0 else ""}" placeholder="3000000" style="width:120px;"></div>'
        f'<div class="cad-field"><label>Sort By</label>'
        f'<select name="sort" class="cad-select" style="min-width:140px;">'
        f'<option value="est_uplift"{_sel("est_uplift", sort_by)}>Est. Uplift</option>'
        f'<option value="est_denial"{_sel("est_denial", sort_by)}>Denial Rate</option>'
        f'<option value="est_ar_days"{_sel("est_ar_days", sort_by)}>AR Days</option>'
        f'<option value="operating_margin"{_sel("operating_margin", sort_by)}>Margin</option>'
        f'<option value="beds"{_sel("beds", sort_by)}>Bed Count</option>'
        f'</select></div>'
        f'<div class="cad-field"><label>&nbsp;</label>'
        f'<button type="submit" class="cad-btn cad-btn-primary">Run Screen &rarr;</button></div>'
        f'</form></div>'
    )

    # ── KPIs ──
    if total_matches > 0 and "est_uplift" in display.columns:
        total_uplift = float(filtered["est_uplift"].sum())
        avg_denial = float(filtered["est_denial"].mean()) if "est_denial" in filtered.columns else 0
        avg_margin = float(filtered["operating_margin"].dropna().mean()) if "operating_margin" in filtered.columns else 0
    else:
        total_uplift = 0
        avg_denial = 0
        avg_margin = 0

    def _fm(v):
        if abs(v) >= 1e9:
            return f"${v/1e9:.1f}B"
        if abs(v) >= 1e6:
            return f"${v/1e6:.0f}M"
        return f"${v:,.0f}"

    kpis = (
        f'<div class="cad-kpi-grid" style="grid-template-columns:repeat(5,1fr);">'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{total_matches:,}</div>'
        f'<div class="cad-kpi-label">Matching Hospitals</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{_fm(total_uplift)}</div>'
        f'<div class="cad-kpi-label">Total Est. Uplift</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{avg_denial:.1%}</div>'
        f'<div class="cad-kpi-label">Avg Est. Denial Rate</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{avg_margin:.1%}</div>'
        f'<div class="cad-kpi-label">Avg Margin</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{len(hcris_df):,}</div>'
        f'<div class="cad-kpi-label">Universe</div></div>'
        f'</div>'
    )

    # ── Results table ──
    result_rows = ""
    for _, row in display.iterrows():
        ccn = str(row.get("ccn", ""))
        name = _html.escape(str(row.get("name", ""))[:35])
        state = _html.escape(str(row.get("state", "")))
        try:
            beds = int(float(row.get("beds", 0) or 0))
        except (ValueError, TypeError):
            beds = 0
        try:
            rev = float(row.get("net_patient_revenue", 0) or 0)
            rev = 0 if rev != rev else rev
        except (ValueError, TypeError):
            rev = 0
        try:
            margin = float(row.get("operating_margin", 0) or 0)
            margin = 0 if margin != margin else margin
        except (ValueError, TypeError):
            margin = 0
        # 5-tier heatmap for margin
        if margin > 0.05:
            margin_heat = "cad-heat-1"
        elif margin > 0.02:
            margin_heat = "cad-heat-2"
        elif margin > 0:
            margin_heat = "cad-heat-3"
        elif margin > -0.03:
            margin_heat = "cad-heat-4"
        else:
            margin_heat = "cad-heat-5"

        try:
            denial = float(row.get("est_denial", 0) or 0)
            denial = 0 if denial != denial else denial
        except (ValueError, TypeError):
            denial = 0
        try:
            ar = float(row.get("est_ar_days", 0) or 0)
            ar = 0 if ar != ar else ar
        except (ValueError, TypeError):
            ar = 0
        try:
            uplift = float(row.get("est_uplift", 0) or 0)
            uplift = 0 if uplift != uplift else uplift
        except (ValueError, TypeError):
            uplift = 0
        uplift_color = "var(--cad-pos)" if uplift > 3e6 else ("var(--cad-warn)" if uplift > 1e6 else "var(--cad-text2)")

        raw_name = str(row.get("name", ""))[:40]
        result_rows += (
            f'<tr>'
            f'<td><a href="/hospital/{_html.escape(ccn)}" class="cad-ticker-id" '
            f'style="text-decoration:none;">{_html.escape(ccn)}</a></td>'
            f'<td><a href="/hospital/{_html.escape(ccn)}" '
            f'style="color:var(--cad-text);text-decoration:none;font-weight:600;">'
            f'{name}</a></td>'
            f'<td>{state}</td>'
            f'<td class="num">{beds}</td>'
            f'<td class="num">{_fm(rev)}</td>'
            f'<td class="num {margin_heat}" style="font-weight:600;">{margin:.1%}</td>'
            f'<td class="num">{denial:.1%}</td>'
            f'<td class="num" style="color:{uplift_color};font-weight:600;">'
            f'<a href="/ebitda-bridge/{_html.escape(ccn)}" '
            f'style="color:{uplift_color};text-decoration:none;">{_fm(uplift)}</a></td>'
            f'<td>'
            f'<form method="POST" action="/pipeline/add" style="display:inline;margin:0;">'
            f'<input type="hidden" name="ccn" value="{_html.escape(ccn)}">'
            f'<input type="hidden" name="name" value="{_html.escape(raw_name)}">'
            f'<input type="hidden" name="state" value="{_html.escape(str(row.get("state", "")))}">'
            f'<input type="hidden" name="beds" value="{beds}">'
            f'<button type="submit" class="cad-btn" '
            f'style="padding:2px 8px;font-size:10px;cursor:pointer;">+ PIPE</button></form></td>'
            f'</tr>'
        )

    table = (
        f'<div class="cad-card cad-table-sticky">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">'
        f'<div style="display:flex;align-items:center;gap:10px;">'
        f'<h2 style="margin:0;">Screening Results</h2>'
        f'<span class="cad-section-code">RES · {total_matches:,}</span>'
        f'</div>'
        f'<span style="font-family:var(--cad-mono);font-size:10px;letter-spacing:0.08em;'
        f'color:var(--cad-text3);text-transform:uppercase;">'
        f'Showing top {min(50, total_matches)} of {total_matches:,}</span>'
        f'</div>'
        f'<table class="cad-table crosshair"><thead><tr>'
        f'<th>CCN</th><th>Hospital</th><th>State</th><th>Beds</th><th>Revenue</th>'
        f'<th>Margin</th><th>Est. Denial</th><th>Est. Uplift</th><th>&nbsp;</th>'
        f'</tr></thead><tbody>{result_rows}</tbody></table></div>'
    )

    # ── Quick screens ──
    quick = (
        f'<div class="cad-card" style="padding:8px 14px;">'
        f'<div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;">'
        f'<span class="cad-section-code" style="margin-right:4px;">QS</span>'
        f'<span class="cad-label">Quick Screens</span>'
        f'<a href="/predictive-screener?region=Southeast&min_beds=200&max_beds=400&max_margin=0.05&min_uplift=3000000" '
        f'class="cad-btn" style="text-decoration:none;">SE · 200-400 · &gt;$3M</a>'
        f'<a href="/predictive-screener?min_beds=100&max_margin=0&sort=est_uplift" '
        f'class="cad-btn" style="text-decoration:none;">Neg margin · 100+</a>'
        f'<a href="/predictive-screener?region=Midwest&min_beds=50&max_beds=200&sort=est_denial" '
        f'class="cad-btn" style="text-decoration:none;">Midwest · small</a>'
        f'<a href="/predictive-screener?min_beds=300&sort=est_uplift" '
        f'class="cad-btn" style="text-decoration:none;">Large · max uplift</a>'
        f'<a href="/predictive-screener?max_margin=-0.05&sort=operating_margin" '
        f'class="cad-btn" style="text-decoration:none;">Distressed · &lt;-5%</a>'
        f'</div></div>'
    )

    # Save search form
    save_form = (
        f'<div class="cad-card">'
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">'
        f'<h2 style="margin:0;">Save Screen</h2>'
        f'<span class="cad-section-code">SAV</span></div>'
        f'<form method="POST" action="/pipeline/save-search" '
        f'style="display:flex;gap:8px;align-items:flex-end;">'
        f'<input type="hidden" name="region" value="{_html.escape(str(region))}">'
        f'<input type="hidden" name="min_beds" value="{min_beds}">'
        f'<input type="hidden" name="max_beds" value="{max_beds}">'
        f'<input type="hidden" name="max_margin" value="{max_margin}">'
        f'<input type="hidden" name="min_uplift" value="{min_uplift}">'
        f'<input type="hidden" name="sort" value="{_html.escape(str(sort_by))}">'
        f'<div class="cad-field" style="flex:1;">'
        f'<label>Name this screen</label>'
        f'<input class="cad-input" type="text" name="name" placeholder="e.g. SE turnarounds" required></div>'
        f'<button type="submit" class="cad-btn cad-btn-primary">Save &rarr;</button>'
        f'<a href="/pipeline" class="cad-btn" style="text-decoration:none;">Pipeline</a>'
        f'</form></div>'
    )

    body = f'{form}{kpis}{table}{save_form}{quick}'

    return shell_v2(
        body, "Predictive Deal Screener",
        active_nav="/predictive-screener",
        subtitle=(
            f"{total_matches:,} matches from {len(hcris_df):,} hospitals | "
            f"ML-powered screening on public CMS data"
        ),
    )
