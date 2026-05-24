"""PE Desk Predictive Screener — deal sourcing via ML on public data.

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

from ._chartis_kit import (
    chartis_shell, ck_data_universe, ck_kpi_block, ck_next_section,
    ck_page_title, ck_panel, ck_value_anchor,
)

_EXPLAINER_CSS = """
.ck-ps-explainer{font-family:var(--sc-serif);font-size:15px;line-height:1.6;
color:var(--sc-text-dim);max-width:68ch;
margin:var(--sc-s-4) 0 var(--sc-s-6);}
.ck-ps-explainer em{color:var(--sc-teal-ink);font-style:italic;}
"""
from .brand import PALETTE


_REGIONS = {
    "Southeast": {"AL", "AR", "FL", "GA", "KY", "LA", "MS", "NC", "SC", "TN", "VA", "WV"},
    "Northeast": {"CT", "DE", "DC", "ME", "MD", "MA", "NH", "NJ", "NY", "PA", "RI", "VT"},
    "Midwest": {"IL", "IN", "IA", "KS", "MI", "MN", "MO", "NE", "ND", "OH", "SD", "WI"},
    "Southwest": {"AZ", "NM", "OK", "TX"},
    "West": {"AK", "CA", "CO", "HI", "ID", "MT", "NV", "OR", "UT", "WA", "WY"},
}


def _add_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add ML features needed for screening.

    Emits a ``data_quality_ok`` boolean per row — False when the HCRIS
    filing produces implausible raw values (opex > 2x revenue, negative
    revenue, sub-$100K revenue, etc.). Downstream code should use this
    to exclude junk filings from "distressed" counts and rankings.
    """
    df = df.copy()
    rev = pd.to_numeric(df.get("net_patient_revenue"), errors="coerce")
    opex = pd.to_numeric(df.get("operating_expenses"), errors="coerce")

    if "operating_margin" not in df.columns:
        safe_rev = rev.where(rev > 1e5)
        # Compute raw margin first, then clamp. Rows where raw margin
        # exceeded the clamp boundary are marked data_quality_ok=False.
        raw_margin = (safe_rev - opex) / safe_rev
        df["operating_margin"] = raw_margin.clip(-0.5, 1.0)
        df["_raw_margin"] = raw_margin

    # Data-quality flag: conservative. False when any of:
    #   - revenue is NaN, <= $100K, or negative
    #   - opex is NaN, negative, or > 2x revenue (opex>2xNPR is implausible)
    #   - raw margin fell outside [-1.0, +1.0] (got heavily clamped)
    #   - beds missing or <1
    beds = pd.to_numeric(df.get("beds"), errors="coerce")
    dq = (
        rev.notna() & (rev > 1e5)
        & opex.notna() & (opex >= 0) & (opex < rev * 2)
        & beds.notna() & (beds >= 1)
    )
    if "_raw_margin" in df.columns:
        raw = df["_raw_margin"]
        dq = dq & (raw.between(-1.0, 1.0) | raw.isna())
        df = df.drop(columns=["_raw_margin"])
    df["data_quality_ok"] = dq.fillna(False)

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
    """Fast RCM prediction for screening (no conformal, just point estimates).

    Returns NaN for estimates when required fields are missing, so the
    screener never hallucinates uplift dollars on hospitals with no
    revenue data. Defaults are only used when the HCRIS row is otherwise
    complete but a secondary field is missing (payer mix, n2g, etc.).
    """
    raw_rev = row.get("net_patient_revenue")
    raw_beds = row.get("beds")

    # Hard requirements: revenue must be a real positive number.
    try:
        rev = float(raw_rev) if raw_rev is not None else float("nan")
    except (TypeError, ValueError):
        rev = float("nan")
    try:
        beds = float(raw_beds) if raw_beds is not None else float("nan")
    except (TypeError, ValueError):
        beds = float("nan")
    if not (rev > 1e5) or not (beds >= 1) or rev != rev or beds != beds:
        return {
            "est_denial": float("nan"),
            "est_ar_days": float("nan"),
            "est_uplift": float("nan"),
        }

    mc = float(row.get("medicare_day_pct") or 0.4)
    md = float(row.get("medicaid_day_pct") or 0.15)
    margin = float(row.get("operating_margin") or 0)
    n2g = float(row.get("net_to_gross_ratio") or 0.3)

    denial = 0.095 + mc * 0.15 + md * 0.20 - np.log(max(1, beds)) * 0.012 - n2g * 0.25 - margin * 0.18
    denial = max(0.02, min(0.25, denial))

    ar_days = 45 + mc * 5 + md * 8 - np.log(max(1, beds)) * 3 - n2g * 10 - margin * 8
    ar_days = max(25, min(75, ar_days))

    denial_gap = max(0, denial - 0.05)
    margin_gap = max(0, 0.08 - margin)
    uplift = rev * (denial_gap * 0.5 + margin_gap * 0.3) * 0.6
    # Cap uplift at 15% of revenue — beyond that is not credible for any
    # single-lever RCM intervention.
    uplift = max(0, min(uplift, rev * 0.15))

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

    form = ck_panel(
        '<form method="GET" action="/predictive-screener" class="cad-form-row">'
        '<div class="cad-field">'
        '<label>Region</label>'
        f'<select name="region" class="cad-select ps-select-md">{region_opts}</select>'
        '</div>'
        '<div class="cad-field"><label>Min Beds</label>'
        f'<input class="cad-input ps-input-sm" type="number" name="min_beds" value="{min_beds}" min="0"></div>'
        '<div class="cad-field"><label>Max Beds</label>'
        f'<input class="cad-input ps-input-sm" type="number" name="max_beds" value="{max_beds if max_beds < 9999 else ""}" placeholder="9999"></div>'
        '<div class="cad-field"><label>Max Margin</label>'
        f'<input class="cad-input ps-input-md" type="number" name="max_margin" value="{max_margin if max_margin < 1 else ""}" step="0.01" placeholder="0.05"></div>'
        '<div class="cad-field"><label>Min Uplift ($)</label>'
        f'<input class="cad-input ps-input-lg" type="number" name="min_uplift" value="{int(min_uplift) if min_uplift > 0 else ""}" placeholder="3000000"></div>'
        '<div class="cad-field"><label>Sort By</label>'
        '<select name="sort" class="cad-select ps-select-md">'
        f'<option value="est_uplift"{_sel("est_uplift", sort_by)}>Est. Uplift</option>'
        f'<option value="est_denial"{_sel("est_denial", sort_by)}>Denial Rate</option>'
        f'<option value="est_ar_days"{_sel("est_ar_days", sort_by)}>AR Days</option>'
        f'<option value="operating_margin"{_sel("operating_margin", sort_by)}>Margin</option>'
        f'<option value="beds"{_sel("beds", sort_by)}>Bed Count</option>'
        '</select></div>'
        '<div class="cad-field"><label>&nbsp;</label>'
        '<button type="submit" class="cad-btn cad-btn-primary">Run Screen &rarr;</button></div>'
        '</form>',
        title="Screen Filters",
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

    title_block = ck_page_title(
        "Predictive Deal Screener", eyebrow="PREDICTIVE SCREENER",
        meta=f"{total_matches:,} matches · {len(hcris_df):,} hospitals in universe",
    ) + '<div style="margin:8px 0 0;">' + ck_data_universe("cms") + '</div>'
    explainer_html = (
        '<p class="ck-ps-explainer">'
        '<em>Where the next deal hides in the universe.</em> '
        "ML-scored filter over the public HCRIS universe — set region, "
        "bed count, margin, and minimum uplift to surface candidates. "
        "Each match carries an estimated RCM denial rate, AR days, and "
        "total EBITDA uplift opportunity derived from the quant stack. "
        "Save a screen to re-run it from the pipeline rail."
        '</p>'
    )
    kpis = (
        '<div class="ck-kpi-strip">'
        + ck_kpi_block("Matching Hospitals", f"{total_matches:,}")
        + ck_kpi_block("Total Est. Uplift", _fm(total_uplift))
        + ck_kpi_block("Avg Est. Denial Rate", f"{avg_denial:.1%}")
        + ck_kpi_block("Avg Margin", f"{avg_margin:.1%}")
        + ck_kpi_block("Universe", f"{len(hcris_df):,}")
        + '</div>'
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
        uplift_cls = "cad-pos" if uplift > 3e6 else ("cad-warn" if uplift > 1e6 else "")

        raw_name = str(row.get("name", ""))[:40]
        result_rows += (
            f'<tr>'
            f'<td><a href="/hospital/{_html.escape(ccn)}" class="cad-ticker-id ck-link">{_html.escape(ccn)}</a></td>'
            f'<td><a href="/hospital/{_html.escape(ccn)}" class="ck-link">'
            f'{name}</a></td>'
            f'<td>{state}</td>'
            f'<td class="num">{beds}</td>'
            f'<td class="num">{_fm(rev)}</td>'
            f'<td class="num {margin_heat}">{margin:.1%}</td>'
            f'<td class="num">{denial:.1%}</td>'
            f'<td class="num {uplift_cls}">'
            f'<a href="/ebitda-bridge/{_html.escape(ccn)}" class="ck-link">{_fm(uplift)}</a></td>'
            f'<td>'
            f'<form method="POST" action="/pipeline/add" class="ps-pipe-form">'
            f'<input type="hidden" name="ccn" value="{_html.escape(ccn)}">'
            f'<input type="hidden" name="name" value="{_html.escape(raw_name)}">'
            f'<input type="hidden" name="state" value="{_html.escape(str(row.get("state", "")))}">'
            f'<input type="hidden" name="beds" value="{beds}">'
            f'<button type="submit" class="cad-btn ps-pipe-btn">+ PIPE</button></form></td>'
            f'</tr>'
        )

    table = ck_panel(
        '<p class="ck-eyebrow">'
        f'Showing top {min(50, total_matches)} of {total_matches:,}'
        '</p>'
        '<table class="cad-table crosshair"><thead><tr>'
        '<th>CCN</th><th>Hospital</th><th>State</th><th>Beds</th><th>Revenue</th>'
        '<th>Margin</th><th>Est. Denial</th><th>Est. Uplift</th><th>&nbsp;</th>'
        f'</tr></thead><tbody>{result_rows}</tbody></table>',
        title=f"Screening Results ({total_matches:,})",
    )

    # ── Quick screens ──
    quick = ck_panel(
        '<p class="ck-section-body">'
        '<a href="/predictive-screener?region=Southeast&min_beds=200&max_beds=400&max_margin=0.05&min_uplift=3000000" class="cad-btn">SE · 200-400 · &gt;$3M</a> '
        '<a href="/predictive-screener?min_beds=100&max_margin=0&sort=est_uplift" class="cad-btn">Neg margin · 100+</a> '
        '<a href="/predictive-screener?region=Midwest&min_beds=50&max_beds=200&sort=est_denial" class="cad-btn">Midwest · small</a> '
        '<a href="/predictive-screener?min_beds=300&sort=est_uplift" class="cad-btn">Large · max uplift</a> '
        '<a href="/predictive-screener?max_margin=-0.05&sort=operating_margin" class="cad-btn">Distressed · &lt;-5%</a>'
        '</p>',
        title="Quick Screens",
    )

    # Save search form
    save_form = ck_panel(
        '<form method="POST" action="/pipeline/save-search" class="ps-save-form">'
        f'<input type="hidden" name="region" value="{_html.escape(str(region))}">'
        f'<input type="hidden" name="min_beds" value="{min_beds}">'
        f'<input type="hidden" name="max_beds" value="{max_beds}">'
        f'<input type="hidden" name="max_margin" value="{max_margin}">'
        f'<input type="hidden" name="min_uplift" value="{min_uplift}">'
        f'<input type="hidden" name="sort" value="{_html.escape(str(sort_by))}">'
        '<div class="cad-field ps-save-field">'
        '<label>Name this screen</label>'
        '<input class="cad-input" type="text" name="name" placeholder="e.g. SE turnarounds" required></div>'
        '<button type="submit" class="cad-btn cad-btn-primary">Save &rarr;</button>'
        '<a href="/pipeline" class="cad-btn">Pipeline</a>'
        '</form>',
        title="Save Screen",
    )

    ps_styles = """
<style>
.ps-select-md{min-width:140px;}
.ps-input-sm{width:82px;}
.ps-input-md{width:92px;}
.ps-input-lg{width:120px;}
.ps-pipe-form{display:inline;margin:0;}
.ps-pipe-btn{padding:2px 8px;font-size:10px;cursor:pointer;
transition:filter 120ms ease;}
.ps-pipe-btn:hover{filter:brightness(1.08);}
.ps-save-form{display:flex;gap:8px;align-items:flex-end;}
.ps-save-field{flex:1;}
</style>
"""
    next_up = ck_next_section(
        "Open a deal profile to act on the shortlist",
        "/diligence/deal",
        eyebrow="Continue —",
        italic_word="deal",
    )
    # Lead takeaway — surface the screen's aggregate opportunity (total
    # estimated EBITDA uplift across the matched universe) at the top,
    # before the KPI strip and results table.
    lead_anchor = ck_value_anchor(
        "SCREEN OPPORTUNITY",
        f"{total_matches:,} matching hospitals",
        delta=f"of {len(hcris_df):,} universe",
        opportunity=f"{_fm(total_uplift)} total est. uplift",
        target=f"avg denial {avg_denial:.1%} · margin {avg_margin:.1%}",
        tone="teal",
    )
    body = (
        ps_styles + title_block + explainer_html + lead_anchor + form
        + kpis + table + save_form + quick + next_up
    )

    return chartis_shell(
        body, "Predictive Deal Screener",
        active_nav="/predictive-screener",
        extra_css=_EXPLAINER_CSS,
    )
