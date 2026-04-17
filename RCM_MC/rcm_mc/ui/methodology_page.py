"""SeekingChartis Methodology — how every number is calculated.

Builds trust with users by explaining data sources, scoring models,
and analytical approaches in plain language.
"""
from __future__ import annotations

import html
from typing import Any

from .shell_v2 import shell_v2
from .brand import PALETTE


def _section(title: str, content: str, icon: str = "") -> str:
    return (
        f'<div class="cad-card">'
        f'<h2>{icon} {html.escape(title)}</h2>'
        f'{content}</div>'
    )


def render_methodology() -> str:
    """Render the full methodology page."""

    intro = _section("How SeekingChartis Works", (
        f'<p style="color:{PALETTE["text_secondary"]};line-height:1.7;">'
        f'SeekingChartis combines public hospital data with proprietary analytical models '
        f'to generate diligence-grade intelligence for healthcare PE. Every number on this '
        f'platform traces back to a specific data source and calculation. This page explains '
        f'each one.</p>'
    ))

    data_sources = _section("Data Sources", (
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">'

        f'<div style="padding:12px;border:1px solid {PALETTE["border"]};border-radius:8px;">'
        f'<h3 style="color:{PALETTE["brand_accent"]};margin-bottom:6px;">HCRIS (Hospital Cost Reports)</h3>'
        f'<p style="font-size:12.5px;color:{PALETTE["text_secondary"]};line-height:1.6;">'
        f'The Hospital Cost Report Information System from CMS. Every Medicare-certified hospital '
        f'files an annual cost report containing revenue, expenses, bed counts, patient days, and '
        f'payer mix. SeekingChartis loads the latest report per hospital (~6,000 active hospitals). '
        f'Data has a ~12-18 month lag from filing date.</p>'
        f'<div style="font-size:11px;color:{PALETTE["text_muted"]};margin-top:6px;">'
        f'Source: data.cms.gov/provider-data | Update: Annual | Fields: ~50 per hospital</div></div>'

        f'<div style="padding:12px;border:1px solid {PALETTE["border"]};border-radius:8px;">'
        f'<h3 style="color:{PALETTE["brand_accent"]};margin-bottom:6px;">FRED (Federal Reserve Economic Data)</h3>'
        f'<p style="font-size:12.5px;color:{PALETTE["text_secondary"]};line-height:1.6;">'
        f'Treasury yields and macro indicators from the Federal Reserve Bank of St. Louis. '
        f'SeekingChartis pulls the 10-year Treasury rate (DGS10) as a key input for discount '
        f'rates (WACC) and market sentiment. When the API is unavailable, we fall back to '
        f'the last known value.</p>'
        f'<div style="font-size:11px;color:{PALETTE["text_muted"]};margin-top:6px;">'
        f'Source: api.stlouisfed.org | Update: Daily | Used in: DCF, Market Pulse</div></div>'

        f'<div style="padding:12px;border:1px solid {PALETTE["border"]};border-radius:8px;">'
        f'<h3 style="color:{PALETTE["brand_accent"]};margin-bottom:6px;">Deal Profile Data</h3>'
        f'<p style="font-size:12.5px;color:{PALETTE["text_secondary"]};line-height:1.6;">'
        f'User-entered metrics for deals under diligence: denial rate, days in AR, net collection '
        f'rate, clean claim rate, cost to collect, claims volume, bed count, and net revenue. '
        f'These override HCRIS defaults and drive deal-specific models (DCF, LBO, EBITDA bridge).</p>'
        f'<div style="font-size:11px;color:{PALETTE["text_muted"]};margin-top:6px;">'
        f'Source: User input via /import | Used in: All deal-level models</div></div>'

        f'<div style="padding:12px;border:1px solid {PALETTE["border"]};border-radius:8px;">'
        f'<h3 style="color:{PALETTE["brand_accent"]};margin-bottom:6px;">Transaction Benchmarks</h3>'
        f'<p style="font-size:12.5px;color:{PALETTE["text_secondary"]};line-height:1.6;">'
        f'Hospital transaction multiples and industry benchmarks derived from public filings '
        f'and industry reports. Current median hospital EV/EBITDA: 10.8x (mid-market). '
        f'Used for valuation context and LBO entry/exit assumptions.</p>'
        f'<div style="font-size:11px;color:{PALETTE["text_muted"]};margin-top:6px;">'
        f'Source: Capital IQ, public filings | Update: Quarterly</div></div>'

        f'</div>'
    ), "&#128202;")

    scoring = _section("SeekingChartis Score (0-100)", (
        f'<p style="font-size:12.5px;color:{PALETTE["text_secondary"]};margin-bottom:12px;line-height:1.6;">'
        f'Every hospital gets a composite investability score from 0 to 100, graded A+ to F. '
        f'The score combines four weighted components:</p>'

        f'<table class="cad-table"><thead><tr>'
        f'<th>Component</th><th>Weight</th><th>Max Points</th><th>What It Measures</th>'
        f'</tr></thead><tbody>'
        f'<tr><td style="font-weight:600;">Market Position</td>'
        f'<td class="num">35%</td><td class="num">35</td>'
        f'<td>Bed count (small/mid/large) + net patient revenue (scale advantage)</td></tr>'
        f'<tr><td style="font-weight:600;">Financial Health</td>'
        f'<td class="num">25%</td><td class="num">25</td>'
        f'<td>Operating margin: strong (&gt;10%), moderate (5-10%), thin (0-5%), negative</td></tr>'
        f'<tr><td style="font-weight:600;">Operational Quality</td>'
        f'<td class="num">20%</td><td class="num">20</td>'
        f'<td>Denial rate (&lt;8% excellent, 8-12% good, &gt;12% concerning) + AR days (&lt;42 excellent)</td></tr>'
        f'<tr><td style="font-weight:600;">Competitive Moat</td>'
        f'<td class="num">20%</td><td class="num">20</td>'
        f'<td>Scale vs market avg, HHI concentration, margin premium (Mauboussin framework)</td></tr>'
        f'</tbody></table>'

        f'<div style="margin-top:12px;font-size:12px;color:{PALETTE["text_muted"]};">'
        f'<strong>Grade scale:</strong> A+ (90+), A (85+), A- (80+), B+ (75+), B (70+), '
        f'B- (65+), C+ (60+), C (55+), C- (50+), D (40+), F (&lt;40)</div>'
    ), "&#127942;")

    market_pulse = _section("Market Pulse Indicators", (
        f'<table class="cad-table"><thead><tr>'
        f'<th>Indicator</th><th>Source</th><th>What It Means</th>'
        f'</tr></thead><tbody>'
        f'<tr><td style="font-weight:600;">Hospital EV/EBITDA</td>'
        f'<td>Transaction databases</td>'
        f'<td>Median enterprise-value-to-EBITDA multiple for recent acute care hospital transactions. '
        f'Higher = more expensive market. Current: ~11.2x.</td></tr>'
        f'<tr><td style="font-weight:600;">10Y Treasury</td>'
        f'<td>FRED DGS10</td>'
        f'<td>Risk-free rate benchmark. Drives WACC and discount rates. Higher rates compress '
        f'hospital valuations (~0.8x per 100bp increase).</td></tr>'
        f'<tr><td style="font-weight:600;">S&amp;P Healthcare</td>'
        f'<td>S&amp;P 500 Healthcare</td>'
        f'<td>Sector index level. Tracks public healthcare equity sentiment. Not hospital-specific '
        f'but directionally indicative.</td></tr>'
        f'<tr><td style="font-weight:600;">Market Sentiment</td>'
        f'<td>Composite</td>'
        f'<td>Score from 0 (bearish) to 1 (bullish). Weights: treasury direction, deal flow volume, '
        f'reimbursement trend signals. Labels: Bullish (&gt;0.7), Slightly Positive (0.4-0.7), '
        f'Neutral (-0.1 to 0.4), Bearish (&lt;-0.1).</td></tr>'
        f'</tbody></table>'
    ), "&#128200;")

    models = _section("Financial Models", (
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">'

        f'<div style="padding:12px;border:1px solid {PALETTE["border"]};border-radius:8px;">'
        f'<h3 style="margin-bottom:6px;">DCF (Discounted Cash Flow)</h3>'
        f'<p style="font-size:12px;color:{PALETTE["text_secondary"]};line-height:1.6;">'
        f'5-year projection of free cash flow, discounted at WACC. Inputs: revenue base, '
        f'growth rate, EBITDA margin, capex %, working capital change, tax rate. Terminal value '
        f'via perpetuity growth method. Sensitivity matrix varies WACC (8-14%) x terminal growth (1-4%).</p></div>'

        f'<div style="padding:12px;border:1px solid {PALETTE["border"]};border-radius:8px;">'
        f'<h3 style="margin-bottom:6px;">LBO (Leveraged Buyout)</h3>'
        f'<p style="font-size:12px;color:{PALETTE["text_secondary"]};line-height:1.6;">'
        f'Full LBO model: sources &amp; uses (senior debt, mezzanine, equity), annual P&amp;L with '
        f'debt service, mandatory/optional repayment schedule, and equity returns at year 3-7 exits. '
        f'Returns IRR and MOIC. Green IRR &gt;20%, amber 15-20%, red &lt;15%.</p></div>'

        f'<div style="padding:12px;border:1px solid {PALETTE["border"]};border-radius:8px;">'
        f'<h3 style="margin-bottom:6px;">3-Statement Model</h3>'
        f'<p style="font-size:12px;color:{PALETTE["text_secondary"]};line-height:1.6;">'
        f'Reconstructed income statement, balance sheet, and cash flow from HCRIS cost report data. '
        f'Each line item tagged with provenance: HCRIS (green), deal_profile (blue), benchmark (amber), '
        f'computed (gray). Uses healthcare industry benchmarks for estimation when data is missing.</p></div>'

        f'<div style="padding:12px;border:1px solid {PALETTE["border"]};border-radius:8px;">'
        f'<h3 style="margin-bottom:6px;">EBITDA Bridge</h3>'
        f'<p style="font-size:12px;color:{PALETTE["text_secondary"]};line-height:1.6;">'
        f'7-lever model: denial reduction, AR acceleration, coding uplift, payer mix optimization, '
        f'cost-to-collect reduction, clean claim improvement, volume/rate growth. Each lever has '
        f'a probability-weighted dollar impact. Shows current → target EBITDA path.</p></div>'

        f'</div>'
    ), "&#128176;")

    regression = _section("Regression Analysis", (
        f'<p style="font-size:12.5px;color:{PALETTE["text_secondary"]};margin-bottom:12px;line-height:1.6;">'
        f'Ordinary Least Squares (OLS) regression implemented in pure NumPy (no sklearn). '
        f'Features are standardized (zero mean, unit variance) before fitting so coefficients '
        f'are comparable across variables with different scales.</p>'
        f'<p style="font-size:12.5px;color:{PALETTE["text_secondary"]};line-height:1.6;">'
        f'<strong>Outputs:</strong> R-squared (% of variance explained), adjusted R-squared '
        f'(penalized for feature count), standardized coefficients with t-statistics, significance '
        f'levels (*p&lt;0.05, **p&lt;0.01, ***p&lt;0.001), and pairwise correlation matrix.</p>'
        f'<p style="font-size:12.5px;color:{PALETTE["text_secondary"]};line-height:1.6;">'
        f'<strong>Data sources:</strong> HCRIS national (~6,000 hospitals) or portfolio deals. '
        f'HCRIS regressions identify which state-level factors predict margins. Portfolio regressions '
        f'identify what drives denial rates or other KPIs across your specific deals.</p>'
    ), "&#128208;")

    margins = _section("Margin Calculations", (
        f'<p style="font-size:12.5px;color:{PALETTE["text_secondary"]};line-height:1.6;">'
        f'<strong>Operating margin</strong> = (Net Patient Revenue - Operating Expenses) / Net Patient Revenue. '
        f'Computed from HCRIS cost report fields. Guards applied:</p>'
        f'<ul style="font-size:12.5px;color:{PALETTE["text_secondary"]};line-height:1.8;padding-left:20px;">'
        f'<li>Revenue must exceed $100K (filters cost-report stubs and accounting artifacts)</li>'
        f'<li>Margins clamped to [-100%, +100%] (no hospital truly has a -1,000% margin)</li>'
        f'<li>State-level averages use <strong>median</strong> not mean (robust to outliers)</li>'
        f'<li>HCRIS data quality varies: some reports have mismatched periods or reclassifications</li>'
        f'</ul>'
        f'<p style="font-size:12.5px;color:{PALETTE["text_secondary"]};line-height:1.6;margin-top:8px;">'
        f'<strong>Industry context:</strong> Median US hospital operating margin is approximately '
        f'-5% to +5%. For-profit chains average higher (5-12%) due to case mix and payer optimization. '
        f'Safety-net and critical access hospitals often operate at negative margins.</p>'
    ), "&#128178;")

    # Economic ontology — metric definitions and causal chains
    ontology_section = ""
    try:
        from ..domain.econ_ontology import classify_metric, explain_causal_path
        key_metrics = [
            "denial_rate", "days_in_ar", "net_collection_rate", "clean_claim_rate",
            "cost_to_collect", "case_mix_index", "ebitda_margin",
        ]
        ont_rows = ""
        for mk in key_metrics:
            try:
                defn = classify_metric(mk)
                causal = explain_causal_path(mk)
                ont_rows += (
                    f'<tr>'
                    f'<td style="font-weight:500;">{html.escape(defn.display_name if hasattr(defn, "display_name") else mk.replace("_", " ").title())}</td>'
                    f'<td style="font-size:12px;">{html.escape(str(defn.definition)[:100] if hasattr(defn, "definition") else "")}</td>'
                    f'<td style="font-size:12px;">{html.escape(str(defn.domain.value) if hasattr(defn, "domain") else "")}</td>'
                    f'<td style="font-size:12px;color:{PALETTE["text_secondary"]};">{html.escape(causal[:80])}</td>'
                    f'</tr>'
                )
            except Exception:
                pass
        if ont_rows:
            ontology_section = _section("Metric Definitions & Causal Chains", (
                f'<p style="font-size:12.5px;color:{PALETTE["text_secondary"]};margin-bottom:12px;line-height:1.6;">'
                f'Every metric in SeekingChartis has a formal definition, domain classification, '
                f'and causal chain explaining how it affects EBITDA. From the healthcare economic ontology.</p>'
                f'<table class="cad-table"><thead><tr>'
                f'<th>Metric</th><th>Definition</th><th>Domain</th><th>Causal Chain</th>'
                f'</tr></thead><tbody>{ont_rows}</tbody></table>'
            ), "&#128209;")
    except Exception:
        pass

    related_links = (
        f'<div class="cad-card" style="display:flex;gap:8px;flex-wrap:wrap;">'
        f'<a href="/verticals" class="cad-btn" style="text-decoration:none;">Healthcare Verticals</a>'
        f'<a href="/library" class="cad-btn" style="text-decoration:none;">Reference Library</a>'
        f'<a href="/conferences" class="cad-btn" style="text-decoration:none;">Conference Roadmap</a>'
        f'<a href="/data-intelligence" class="cad-btn" style="text-decoration:none;">Data Intelligence</a>'
        f'<a href="/model-validation" class="cad-btn" style="text-decoration:none;">Model Validation</a>'
        f'</div>'
    )

    body = f'{intro}{data_sources}{scoring}{market_pulse}{models}{regression}{margins}{ontology_section}{related_links}'

    return shell_v2(
        body, "Methodology",
        subtitle="How every number is calculated — data sources, models & assumptions",
    )
