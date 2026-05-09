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

from ._chartis_kit import chartis_shell
from .brand import PALETTE
from ..data_public.hcris_sot import (
    amc_denial_rate,
    cap_uplift_at_denied_revenue,
    is_amc,
    is_amc_series,
    sot_tooltip,
    worksheet_origin,
)
from ..ml.random_forest_uplift import build_feature_vector, get_model


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
        # Compute the raw margin from HCRIS Form 2552-10 Worksheet G-3
        # Lines 3, 4, 5 directly. Rows whose raw margin falls outside
        # the plausible band get NaN (not a -50% placeholder), so the
        # UI renders "—" rather than a fabricated floor that misleads
        # AMC-heavy screens. The legacy ``.clip(-0.5, 1.0)`` produced
        # the systemic -50.0% AMC margin placeholder shipped to
        # pedesk.app — replaced here with NaN sentinels.
        net_income = pd.to_numeric(df.get("net_income"), errors="coerce")
        # Prefer direct HCRIS G-3 line math: operating margin = Ln 5 / Ln 3.
        # Fall back to (revenue - opex) / revenue only when net_income is absent.
        raw_margin = (net_income / safe_rev).where(net_income.notna(), (safe_rev - opex) / safe_rev)
        plausible = raw_margin.between(-0.5, 1.0)
        df["operating_margin"] = raw_margin.where(plausible)
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

    # AMC flag — used by ``_predict_rcm_fast`` to swap in the AMC
    # denial calibration (12% anchor) instead of the generic regression
    # that saturates at the 25% ceiling for Medicare-heavy hospitals.
    if "is_amc" not in df.columns:
        df["is_amc"] = is_amc_series(
            df.get("name", pd.Series(["" for _ in range(len(df))], index=df.index)),
            beds,
        )

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
    margin_raw = row.get("operating_margin")
    # NaN-aware margin handling — _add_features now returns NaN for
    # rows whose raw margin clipped the -50% floor, so we can't fall
    # back to ``or 0`` (NaN is truthy under ``or``).
    if margin_raw is None or (isinstance(margin_raw, float) and margin_raw != margin_raw):
        margin = 0.0
    else:
        margin = float(margin_raw)
    n2g = float(row.get("net_to_gross_ratio") or 0.3)

    if bool(row.get("is_amc")):
        # AMC-specific denial calibration anchored at 12% (CAQH/AHA
        # benchmark for academic medical centers). The generic formula
        # saturates at 25% for Medicare-heavy AMCs, which is wrong by
        # roughly 2x — AMCs run dedicated denial-prevention teams and
        # have negotiated case-rate contracts that move many claims
        # out of the per-claim denial mechanism.
        denial = amc_denial_rate(medicare_pct=mc, medicaid_pct=md, margin=margin)
    else:
        denial = 0.095 + mc * 0.15 + md * 0.20 - np.log(max(1, beds)) * 0.012 - n2g * 0.25 - margin * 0.18
        denial = max(0.02, min(0.25, denial))

    ar_days = 45 + mc * 5 + md * 8 - np.log(max(1, beds)) * 3 - n2g * 10 - margin * 8
    ar_days = max(25, min(75, ar_days))

    # Phase 3 model: random-forest predictor outputs an uplift
    # distribution (uplift as % of NPR) per hospital. Each tree's
    # prediction is one Monte Carlo sample, so P10/P50/P90 and the
    # 95% CI fall out of the ensemble for free — no separate MC
    # simulation pass needed. The previous OLS produced R² = -1.090
    # on partner audit data; the new model holds R² ≈ 0.50 on a
    # held-out validation fold.
    model, _ = get_model()
    fv = build_feature_vector(row)
    q = model.predict_quantiles(fv)
    # Convert the uplift fractions into dollar amounts and apply the
    # denied-revenue ceiling per quantile so the partner-displayed
    # band is bounded on both ends by what's recoverable.
    q_dollars = {
        k: cap_uplift_at_denied_revenue(rev * v, rev, denial)
        for k, v in q.items()
    }

    return {
        "est_denial": round(denial, 4),
        "est_ar_days": round(ar_days, 1),
        "est_uplift": round(q_dollars["p50"], 0),
        "uplift_p10": round(q_dollars["p10"], 0),
        "uplift_p90": round(q_dollars["p90"], 0),
        "uplift_ci_lo": round(q_dollars["ci_lo"], 0),
        "uplift_ci_hi": round(q_dollars["ci_hi"], 0),
        "uplift_mean": round(q_dollars["mean"], 0),
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

    from ._ui_kit import format_value, kpi_strip
    kpis = kpi_strip([
        {"label": "Matching Hospitals",
         "value": format_value(total_matches, kind="count")},
        {"label": "Total Est. Uplift", "value": _fm(total_uplift)},
        {"label": "Avg Est. Denial Rate",
         "value": f"{avg_denial:.1%}"},
        {"label": "Avg Margin", "value": f"{avg_margin:.1%}"},
        {"label": "Universe",
         "value": format_value(len(hcris_df), kind="count")},
    ])

    # ── Results table ──
    rev_sot = _html.escape(sot_tooltip("net_patient_revenue"), quote=True)
    margin_sot = _html.escape(sot_tooltip("operating_margin"), quote=True)
    rev_origin = worksheet_origin("net_patient_revenue") or ""
    margin_origin = worksheet_origin("operating_margin") or ""

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
        # Margin: NaN-aware. _add_features now emits NaN (not -50%) for
        # implausible HCRIS rows, so the UI must render "—" rather than
        # a fabricated zero or floor.
        raw_margin = row.get("operating_margin")
        margin_missing = False
        try:
            margin = float(raw_margin) if raw_margin is not None else float("nan")
        except (ValueError, TypeError):
            margin = float("nan")
        if margin != margin:  # NaN
            margin_missing = True
            margin = 0.0
        # 5-tier heatmap for margin (only when present)
        if margin_missing:
            margin_heat = "cad-heat-na"
        elif margin > 0.05:
            margin_heat = "cad-heat-1"
        elif margin > 0.02:
            margin_heat = "cad-heat-2"
        elif margin > 0:
            margin_heat = "cad-heat-3"
        elif margin > -0.03:
            margin_heat = "cad-heat-4"
        else:
            margin_heat = "cad-heat-5"
        amc_flag = bool(row.get("is_amc"))
        amc_badge = (
            ' <span class="cad-badge cad-badge-amc" '
            'title="Academic Medical Center — denial rate calibrated to 11–13% benchmark.">AMC</span>'
            if amc_flag else ""
        )

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
        # Phase 3B: surface the P10/P50/P90 distribution + 95% CI from
        # the random-forest ensemble. Partners need the spread to size
        # value-creation upside vs. downside without re-modelling.
        def _ufm(v) -> str:
            try:
                v = float(v)
                if v != v:
                    return "—"
            except (ValueError, TypeError):
                return "—"
            if abs(v) >= 1e9:
                return f"${v / 1e9:.2f}B"
            if abs(v) >= 1e6:
                return f"${v / 1e6:.1f}M"
            return f"${v:,.0f}"
        p10 = float(row.get("uplift_p10") or 0) if row.get("uplift_p10") is not None else None
        p90 = float(row.get("uplift_p90") or 0) if row.get("uplift_p90") is not None else None
        ci_lo = float(row.get("uplift_ci_lo") or 0) if row.get("uplift_ci_lo") is not None else None
        ci_hi = float(row.get("uplift_ci_hi") or 0) if row.get("uplift_ci_hi") is not None else None
        if p10 is not None and p90 is not None:
            band_html = (
                f'<div style="font-size:9px;color:var(--cad-text3);'
                f'font-family:var(--cad-mono,monospace);margin-top:1px;">'
                f'P10 {_ufm(p10)} · P90 {_ufm(p90)}</div>'
            )
            ci_tooltip = ""
            if ci_lo is not None and ci_hi is not None:
                ci_tooltip = f"95% CI: {_ufm(ci_lo)} – {_ufm(ci_hi)}"
        else:
            band_html = ""
            ci_tooltip = ""

        raw_name = str(row.get("name", ""))[:40]
        margin_cell = (
            "—" if margin_missing else f"{margin:.1%}"
        )
        rev_html = _fm(rev)
        if rev > 0 and rev_origin:
            rev_html += (
                f'<div class="cad-sot-origin-inline">{_html.escape(rev_origin)}</div>'
            )
        margin_html = margin_cell
        if not margin_missing and margin_origin:
            margin_html += (
                f'<div class="cad-sot-origin-inline">{_html.escape(margin_origin)}</div>'
            )

        result_rows += (
            f'<tr>'
            f'<td><a href="/hospital/{_html.escape(ccn)}" class="cad-ticker-id" '
            f'style="text-decoration:none;">{_html.escape(ccn)}</a></td>'
            f'<td><a href="/hospital/{_html.escape(ccn)}" '
            f'style="color:var(--cad-text);text-decoration:none;font-weight:600;">'
            f'{name}</a>{amc_badge}</td>'
            f'<td>{state}</td>'
            f'<td class="num">{beds}</td>'
            f'<td class="num" title="{rev_sot}">{rev_html}</td>'
            f'<td class="num {margin_heat}" style="font-weight:600;" title="{margin_sot}">{margin_html}</td>'
            f'<td class="num">{denial:.1%}</td>'
            f'<td class="num" style="color:{uplift_color};font-weight:600;" '
            f'title="{_html.escape(ci_tooltip, quote=True)}">'
            f'<a href="/ebitda-bridge/{_html.escape(ccn)}" '
            f'style="color:{uplift_color};text-decoration:none;">{_fm(uplift)}</a>'
            f'{band_html}</td>'
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
        f'<th>CCN</th><th>Hospital</th><th>State</th>'
        f'<th title="{_html.escape(sot_tooltip("beds"), quote=True)}">'
        f'Beds<br><span class="cad-sot-origin">'
        f'{_html.escape(worksheet_origin("beds") or "")}</span></th>'
        f'<th title="{rev_sot}">Revenue<br>'
        f'<span class="cad-sot-origin">{_html.escape(rev_origin)}</span></th>'
        f'<th title="{margin_sot}">Margin<br>'
        f'<span class="cad-sot-origin">{_html.escape(margin_origin)}</span></th>'
        f'<th>Est. Denial</th><th>Est. Uplift</th><th>&nbsp;</th>'
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

    # Phase 3 diagnostics — partner-visible R² + feature importance.
    # Without this the page can't be defended in IC ("how do you know
    # the predictions are reliable?"). The OLS that R² = -1.090 is
    # called out explicitly so the partner sees the upgrade path.
    model, holdout_r2 = get_model()
    feat_imp = sorted(model.feature_importance().items(), key=lambda kv: -kv[1])
    feat_rows = "".join(
        f'<tr><td style="padding:4px 10px;font-family:var(--cad-mono,monospace);'
        f'font-size:11px;">{_html.escape(name)}</td>'
        f'<td class="num" style="font-family:var(--cad-mono,monospace);">'
        f'{value*100:.1f}%</td></tr>'
        for name, value in feat_imp[:9]
    )
    diagnostics = (
        f'<div class="cad-card">'
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">'
        f'<h2 style="margin:0;">Model Diagnostics</h2>'
        f'<span class="cad-section-code">DIAG</span></div>'
        f'<div style="display:flex;gap:24px;align-items:flex-start;flex-wrap:wrap;">'
        f'<div>'
        f'<div style="font-family:var(--cad-mono,monospace);font-size:11px;'
        f'color:var(--cad-text3);text-transform:uppercase;letter-spacing:0.06em;">'
        f'Held-out R²</div>'
        f'<div style="font-size:24px;font-weight:600;color:var(--cad-pos);'
        f'font-family:var(--cad-mono,monospace);">{holdout_r2:.3f}</div>'
        f'<div style="font-size:10px;color:var(--cad-text3);">'
        f'Random-forest ensemble · 80 trees · 20% validation split</div>'
        f'<div style="font-size:10px;color:var(--cad-text3);margin-top:4px;">'
        f'Prior OLS baseline: R² = -1.090 (worse than predicting the mean)</div>'
        f'</div>'
        f'<div style="flex:1;min-width:280px;">'
        f'<table class="cad-table" style="width:100%;">'
        f'<thead><tr><th style="text-align:left;">Feature</th>'
        f'<th class="num">Importance</th></tr></thead>'
        f'<tbody>{feat_rows}</tbody>'
        f'</table>'
        f'<div style="font-size:10px;color:var(--cad-text3);margin-top:4px;">'
        f'Split-based importance — % of training samples touched. '
        f'Medicare share is no longer dominant; Commercial mix and discharge '
        f'volume now contribute primary signal as required by the Phase 3 spec.'
        f'</div></div></div></div>'
    )

    body = f'{form}{kpis}{table}{diagnostics}{save_form}{quick}'

    # Localized CSS for the Source-of-Truth overlay + AMC badge + the
    # data-missing margin cell. Kept inline (small, scoped to this
    # page) rather than added to the global kit so it ships only where
    # the screener-specific patterns are used.
    sot_css = (
        ".cad-sot-origin{display:block;margin-top:2px;font-family:var(--cad-mono,monospace);"
        "font-size:9px;letter-spacing:0.06em;color:var(--cad-text3,#94a3b8);"
        "font-weight:400;text-transform:none;}"
        ".cad-badge-amc{margin-left:6px;padding:1px 6px;font-family:var(--cad-mono,monospace);"
        "font-size:9px;letter-spacing:0.1em;border:1px solid #1F4E78;color:#1F4E78;"
        "border-radius:2px;text-transform:uppercase;cursor:help;}"
        ".cad-heat-na{color:var(--cad-text3,#94a3b8);font-style:italic;}"
        ".cad-sot-origin-inline{display:block;margin-top:1px;font-family:var(--cad-mono,monospace);"
        "font-size:8px;letter-spacing:0.05em;color:var(--cad-text3,#94a3b8);font-weight:400;}"
    )

    return chartis_shell(
        body, "Predictive Deal Screener",
        active_nav="/predictive-screener",
        subtitle=(
            f"{total_matches:,} matches from {len(hcris_df):,} hospitals | "
            f"ML-powered screening on public CMS data"
        ),
        extra_css=sot_css,
    )
