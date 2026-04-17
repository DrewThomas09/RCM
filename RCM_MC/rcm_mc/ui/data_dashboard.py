"""SeekingChartis Data Intelligence Dashboard.

Shows the full data estate: HCRIS coverage, benchmark freshness,
multi-year trends, state-level gaps, and data quality metrics.
Makes the data moat visible and auditable.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from .shell_v2 import shell_v2
from .brand import PALETTE


def render_data_dashboard(hcris_df: pd.DataFrame) -> str:
    """Render the data intelligence dashboard."""
    n_hospitals = len(hcris_df)
    n_states = hcris_df["state"].nunique() if "state" in hcris_df.columns else 0

    # Fiscal year distribution
    fy_counts = {}
    if "fiscal_year" in hcris_df.columns:
        for fy, count in hcris_df["fiscal_year"].value_counts().sort_index().items():
            fy_counts[str(int(fy))] = int(count)
    n_years = len(fy_counts)

    # Data completeness by column
    completeness = {}
    key_cols = [
        "beds", "net_patient_revenue", "operating_expenses", "net_income",
        "gross_patient_revenue", "medicare_day_pct", "medicaid_day_pct",
        "total_patient_days", "bed_days_available",
    ]
    for col in key_cols:
        if col in hcris_df.columns:
            non_null = hcris_df[col].notna().sum()
            completeness[col] = round(non_null / n_hospitals * 100, 1) if n_hospitals > 0 else 0

    # State coverage
    state_counts = {}
    if "state" in hcris_df.columns:
        for st, count in hcris_df["state"].value_counts().head(20).items():
            state_counts[str(st)] = int(count)

    # Revenue distribution
    if "net_patient_revenue" in hcris_df.columns:
        rev = hcris_df["net_patient_revenue"].dropna()
        rev_stats = {
            "min": float(rev.min()), "p25": float(rev.quantile(0.25)),
            "median": float(rev.median()), "p75": float(rev.quantile(0.75)),
            "max": float(rev.max()), "total": float(rev.sum()),
        }
    else:
        rev_stats = {}

    # Bed distribution
    if "beds" in hcris_df.columns:
        beds = hcris_df["beds"].dropna()
        bed_brackets = {
            "< 25 beds": int((beds < 25).sum()),
            "25-99 beds": int(((beds >= 25) & (beds < 100)).sum()),
            "100-249 beds": int(((beds >= 100) & (beds < 250)).sum()),
            "250-499 beds": int(((beds >= 250) & (beds < 500)).sum()),
            "500+ beds": int((beds >= 500).sum()),
        }
    else:
        bed_brackets = {}

    def _fmt_money(v):
        if v >= 1e12:
            return f"${v/1e12:.1f}T"
        if v >= 1e9:
            return f"${v/1e9:.1f}B"
        if v >= 1e6:
            return f"${v/1e6:.0f}M"
        return f"${v:,.0f}"

    # ── KPIs ──
    total_rev = rev_stats.get("total", 0)
    total_beds = int(hcris_df["beds"].fillna(0).sum()) if "beds" in hcris_df.columns else 0

    kpis = (
        f'<div class="cad-kpi-grid" style="grid-template-columns:repeat(6,1fr);">'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{n_hospitals:,}</div>'
        f'<div class="cad-kpi-label">Hospitals</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{n_states}</div>'
        f'<div class="cad-kpi-label">States + Territories</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{n_years}</div>'
        f'<div class="cad-kpi-label">Fiscal Years</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{total_beds:,}</div>'
        f'<div class="cad-kpi-label">Total Beds</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{_fmt_money(total_rev)}</div>'
        f'<div class="cad-kpi-label">Total NPSR</div></div>'
        f'<div class="cad-kpi"><div class="cad-kpi-value">{len(key_cols)}</div>'
        f'<div class="cad-kpi-label">Core Metrics</div></div>'
        f'</div>'
    )

    # ── Completeness table ──
    comp_rows = ""
    for col, pct in sorted(completeness.items(), key=lambda x: -x[1]):
        bar_color = "var(--cad-pos)" if pct >= 90 else ("var(--cad-warn)" if pct >= 70 else "var(--cad-neg)")
        comp_rows += (
            f'<tr>'
            f'<td>{_html.escape(col.replace("_", " ").title())}</td>'
            f'<td class="num" style="color:{bar_color};font-weight:600;">{pct:.1f}%</td>'
            f'<td><div style="background:var(--cad-bg3);border-radius:3px;height:8px;width:120px;">'
            f'<div style="width:{pct:.0f}%;background:{bar_color};border-radius:3px;height:8px;"></div>'
            f'</div></td></tr>'
        )

    comp_section = (
        f'<div class="cad-card">'
        f'<h2>Data Completeness by Field</h2>'
        f'<p style="font-size:12px;color:var(--cad-text2);margin-bottom:10px;">'
        f'Percentage of hospitals with non-null values for each core metric. '
        f'Fields below 80% may need imputation or exclusion in analysis.</p>'
        f'<table class="cad-table"><thead><tr>'
        f'<th>Field</th><th>Coverage</th><th></th>'
        f'</tr></thead><tbody>{comp_rows}</tbody></table></div>'
    )

    # ── State coverage ──
    state_rows = ""
    for st, count in sorted(state_counts.items(), key=lambda x: -x[1]):
        state_rows += (
            f'<tr>'
            f'<td><a href="/market-data/state/{_html.escape(st)}" '
            f'style="color:var(--cad-link);text-decoration:none;">{_html.escape(st)}</a></td>'
            f'<td class="num">{count}</td></tr>'
        )

    state_section = (
        f'<div class="cad-card">'
        f'<h2>Coverage by State (Top 20)</h2>'
        f'<table class="cad-table"><thead><tr>'
        f'<th>State</th><th>Hospitals</th>'
        f'</tr></thead><tbody>{state_rows}</tbody></table></div>'
    )

    # ── Bed distribution ──
    bed_rows = ""
    for bracket, count in bed_brackets.items():
        pct = count / n_hospitals * 100 if n_hospitals > 0 else 0
        bed_rows += (
            f'<tr>'
            f'<td>{_html.escape(bracket)}</td>'
            f'<td class="num">{count:,}</td>'
            f'<td class="num">{pct:.1f}%</td></tr>'
        )

    bed_section = (
        f'<div class="cad-card">'
        f'<h2>Hospital Size Distribution</h2>'
        f'<table class="cad-table"><thead><tr>'
        f'<th>Size</th><th>Count</th><th>%</th>'
        f'</tr></thead><tbody>{bed_rows}</tbody></table></div>'
    )

    # ── Revenue stats ──
    rev_section = ""
    if rev_stats:
        rev_section = (
            f'<div class="cad-card">'
            f'<h2>Revenue Distribution</h2>'
            f'<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:8px;font-size:12px;">'
            f'<div><span style="color:var(--cad-text3);">Min:</span><br>'
            f'<strong>{_fmt_money(rev_stats["min"])}</strong></div>'
            f'<div><span style="color:var(--cad-text3);">P25:</span><br>'
            f'<strong>{_fmt_money(rev_stats["p25"])}</strong></div>'
            f'<div><span style="color:var(--cad-text3);">Median:</span><br>'
            f'<strong>{_fmt_money(rev_stats["median"])}</strong></div>'
            f'<div><span style="color:var(--cad-text3);">P75:</span><br>'
            f'<strong>{_fmt_money(rev_stats["p75"])}</strong></div>'
            f'<div><span style="color:var(--cad-text3);">Max:</span><br>'
            f'<strong>{_fmt_money(rev_stats["max"])}</strong></div>'
            f'</div></div>'
        )

    # ── FY distribution ──
    fy_section = ""
    if fy_counts:
        fy_rows = ""
        for fy, count in sorted(fy_counts.items()):
            fy_rows += f'<tr><td>{_html.escape(fy)}</td><td class="num">{count:,}</td></tr>'
        fy_section = (
            f'<div class="cad-card">'
            f'<h2>Fiscal Year Coverage</h2>'
            f'<table class="cad-table"><thead><tr><th>Year</th><th>Hospitals</th>'
            f'</tr></thead><tbody>{fy_rows}</tbody></table></div>'
        )

    # ── Data sources ──
    sources = (
        f'<div class="cad-card" style="border-left:3px solid var(--cad-accent);">'
        f'<h2>Data Sources</h2>'
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;font-size:12px;">'
        f'<div>'
        f'<h3 style="font-size:11px;color:var(--cad-accent);margin-bottom:4px;">CMS HCRIS Cost Reports</h3>'
        f'<p style="color:var(--cad-text2);line-height:1.7;">'
        f'Annual financial statements from every Medicare-certified hospital. Includes revenue, '
        f'expenses, bed counts, patient days, and payer mix. Downloaded from '
        f'downloads.cms.gov/Files/hcris/.</p></div>'
        f'<div>'
        f'<h3 style="font-size:11px;color:var(--cad-accent);margin-bottom:4px;">CMS Utilization (DRG)</h3>'
        f'<p style="color:var(--cad-text2);line-height:1.7;">'
        f'Medicare DRG-level volume and payment per hospital. Service line concentration, '
        f'charge-to-payment ratios, top DRGs by volume.</p></div>'
        f'<div>'
        f'<h3 style="font-size:11px;color:var(--cad-accent);margin-bottom:4px;">CMS Care Compare</h3>'
        f'<p style="color:var(--cad-text2);line-height:1.7;">'
        f'Quality ratings, patient experience (HCAHPS), readmission rates, mortality, '
        f'HAI data from Hospital Compare.</p></div>'
        f'<div>'
        f'<h3 style="font-size:11px;color:var(--cad-accent);margin-bottom:4px;">IRS 990</h3>'
        f'<p style="color:var(--cad-text2);line-height:1.7;">'
        f'Non-profit tax returns with executive compensation, community benefit spending, '
        f'and uncompensated care for 501(c)(3) hospitals.</p></div>'
        f'</div></div>'
    )

    # ── Nav ──
    nav = (
        f'<div class="cad-card" style="display:flex;gap:8px;flex-wrap:wrap;">'
        f'<a href="/quant-lab" class="cad-btn cad-btn-primary" '
        f'style="text-decoration:none;">Quant Lab</a>'
        f'<a href="/ml-insights" class="cad-btn" '
        f'style="text-decoration:none;">ML Insights</a>'
        f'<a href="/portfolio/regression" class="cad-btn" '
        f'style="text-decoration:none;">Regression</a>'
        f'<a href="/market-data/map" class="cad-btn" '
        f'style="text-decoration:none;">Market Heatmap</a>'
        f'<a href="/screen" class="cad-btn" '
        f'style="text-decoration:none;">Screener</a>'
        f'</div>'
    )

    left = f'{comp_section}{bed_section}{fy_section}'
    right = f'{state_section}{rev_section}'

    body = (
        f'{kpis}{sources}'
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">'
        f'<div>{left}</div><div>{right}</div></div>'
        f'{nav}'
    )

    return shell_v2(
        body, "Data Intelligence",
        active_nav="/data",
        subtitle=(
            f"{n_hospitals:,} hospitals | {n_states} states | "
            f"{n_years} fiscal years | {_fmt_money(total_rev)} total NPSR"
        ),
    )
