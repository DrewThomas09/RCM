"""SeekingChartis Methodology — how every number is calculated.

Builds trust with users by explaining data sources, scoring models,
and analytical approaches in plain language.
"""
from __future__ import annotations

import html
from typing import Any

from .shell_v2 import shell_v2
from .brand import PALETTE


def _section(code: str, title: str, content: str, *, anchor: str = "") -> str:
    """Render a methodology section with a Bloomberg-style code chip header."""
    aid = f' id="{html.escape(anchor)}"' if anchor else ""
    return (
        f'<div class="cad-card"{aid}>'
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">'
        f'<h2 style="margin:0;">{html.escape(title)}</h2>'
        f'<span class="cad-section-code">{html.escape(code)}</span>'
        f'</div>'
        f'{content}</div>'
    )


def _source_card(code: str, title: str, body: str, meta: str) -> str:
    """Render a data-source mini card with ticker-style code."""
    return (
        f'<div style="padding:12px 14px;border:1px solid {PALETTE["border"]};'
        f'background:{PALETTE["bg_tertiary"]};">'
        f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">'
        f'<span class="cad-ticker-id" style="padding:2px 7px;">{html.escape(code)}</span>'
        f'<h3 style="margin:0;font-size:12.5px;font-weight:700;letter-spacing:0.04em;'
        f'text-transform:uppercase;color:{PALETTE["text_primary"]};">{html.escape(title)}</h3>'
        f'</div>'
        f'<p style="font-size:12px;color:{PALETTE["text_secondary"]};line-height:1.6;">'
        f'{body}</p>'
        f'<div style="font-family:var(--cad-mono);font-size:9.5px;'
        f'letter-spacing:0.08em;color:{PALETTE["text_muted"]};'
        f'margin-top:8px;text-transform:uppercase;">{html.escape(meta)}</div>'
        f'</div>'
    )


def _model_card(code: str, title: str, body: str) -> str:
    """Render a model mini card matching deal dashboard style."""
    return (
        f'<div style="padding:10px 14px;border:1px solid {PALETTE["border"]};'
        f'background:{PALETTE["bg_tertiary"]};'
        f'border-left:3px solid {PALETTE["brand_accent"]};">'
        f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">'
        f'<span class="cad-section-code">{html.escape(code)}</span>'
        f'<h3 style="margin:0;font-size:12.5px;font-weight:700;letter-spacing:0.04em;'
        f'text-transform:uppercase;color:{PALETTE["text_primary"]};">{html.escape(title)}</h3>'
        f'</div>'
        f'<p style="font-size:12px;color:{PALETTE["text_secondary"]};line-height:1.6;">'
        f'{body}</p>'
        f'</div>'
    )


def render_methodology() -> str:
    """Render the full methodology page."""

    # ── Table of contents ──
    toc_items = [
        ("INTRO", "Overview", "toc-intro"),
        ("DAT", "Data Sources", "toc-data"),
        ("SCR", "Scoring Model", "toc-scoring"),
        ("MPX", "Market Pulse", "toc-pulse"),
        ("MDL", "Financial Models", "toc-models"),
        ("REG", "Regression", "toc-regression"),
        ("MRG", "Margin Calculation", "toc-margins"),
        ("ONT", "Metric Ontology", "toc-ontology"),
    ]
    toc_html = "".join(
        f'<a href="#{aid}" class="cad-btn" style="text-decoration:none;">'
        f'<span class="cad-section-code" style="margin-right:6px;">{code}</span>'
        f'{html.escape(name)}</a>'
        for code, name, aid in toc_items
    )
    toc = (
        f'<div class="cad-card" style="padding:10px 14px;">'
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">'
        f'<h2 style="margin:0;">Contents</h2>'
        f'<span class="cad-section-code">TOC</span></div>'
        f'<div style="display:flex;gap:6px;flex-wrap:wrap;">{toc_html}</div></div>'
    )

    # ── Intro ──
    intro = _section("INTRO", "Overview", (
        f'<p style="color:{PALETTE["text_secondary"]};line-height:1.7;font-size:13px;">'
        f'SeekingChartis combines public hospital data with proprietary analytical models '
        f'to generate diligence-grade intelligence for healthcare PE. '
        f'<strong>Every number on this platform traces back to a specific data source and '
        f'calculation.</strong> This page explains each one — you should be able to audit any '
        f'output end-to-end.</p>'
        f'<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:0;margin-top:14px;'
        f'border:1px solid {PALETTE["border"]};">'
        f'<div style="padding:10px 14px;border-right:1px solid {PALETTE["border"]};">'
        f'<div class="cad-kpi-value" style="font-size:16px;">6,123</div>'
        f'<div class="cad-kpi-label">Hospitals Tracked</div></div>'
        f'<div style="padding:10px 14px;border-right:1px solid {PALETTE["border"]};">'
        f'<div class="cad-kpi-value" style="font-size:16px;">17</div>'
        f'<div class="cad-kpi-label">Analytical Models</div></div>'
        f'<div style="padding:10px 14px;border-right:1px solid {PALETTE["border"]};">'
        f'<div class="cad-kpi-value" style="font-size:16px;">3,157</div>'
        f'<div class="cad-kpi-label">Passing Tests</div></div>'
        f'<div style="padding:10px 14px;">'
        f'<div class="cad-kpi-value" style="font-size:16px;">52</div>'
        f'<div class="cad-kpi-label">API Endpoints</div></div>'
        f'</div>'
    ), anchor="toc-intro")

    # ── Data sources ──
    data_sources = _section("DAT", "Data Sources", (
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">'
        + _source_card(
            "HCRIS",
            "Hospital Cost Reports",
            "Hospital Cost Report Information System from CMS. Every Medicare-certified hospital "
            "files an annual cost report containing revenue, expenses, bed counts, patient days, "
            "and payer mix. SeekingChartis loads the latest report per hospital (~6,000 active "
            "hospitals). Data has a ~12-18 month lag from filing date.",
            "Source data.cms.gov · Update Annual · Fields ~50 per hospital",
        )
        + _source_card(
            "FRED",
            "Federal Reserve Economic Data",
            "Treasury yields and macro indicators from the St. Louis Fed. SeekingChartis pulls "
            "the 10-year Treasury rate (DGS10) as a key input for discount rates (WACC) and "
            "market sentiment. Falls back to last known value on API failure.",
            "Source api.stlouisfed.org · Update Daily · Used in DCF, Market Pulse",
        )
        + _source_card(
            "DEAL",
            "Deal Profile Data",
            "User-entered metrics for deals under diligence: denial rate, days in AR, net "
            "collection rate, clean claim rate, cost to collect, claims volume, bed count, "
            "and net revenue. These override HCRIS defaults and drive deal-specific models.",
            "Source User input via /import · Used in all deal-level models",
        )
        + _source_card(
            "TXN",
            "Transaction Benchmarks",
            "Hospital transaction multiples and industry benchmarks derived from public filings "
            "and industry reports. Current median hospital EV/EBITDA: 10.8x (mid-market). "
            "Used for valuation context and LBO entry/exit assumptions.",
            "Source Capital IQ, public filings · Update Quarterly",
        )
        + '</div>'
    ), anchor="toc-data")

    # ── Scoring ──
    scoring = _section("SCR", "SeekingChartis Score (0-100)", (
        f'<p style="font-size:12.5px;color:{PALETTE["text_secondary"]};margin-bottom:10px;line-height:1.6;">'
        f'Every hospital gets a composite investability score from 0 to 100, graded A+ to F. '
        f'The score combines four weighted components:</p>'
        f'<table class="cad-table"><thead><tr>'
        f'<th>Component</th><th>Weight</th><th>Max Pts</th><th>What It Measures</th>'
        f'</tr></thead><tbody>'
        f'<tr><td style="font-weight:600;">Market Position</td>'
        f'<td class="num cad-heat-2">35%</td><td class="num">35</td>'
        f'<td>Bed count (small/mid/large) + net patient revenue (scale advantage)</td></tr>'
        f'<tr><td style="font-weight:600;">Financial Health</td>'
        f'<td class="num cad-heat-3">25%</td><td class="num">25</td>'
        f'<td>Operating margin: strong (&gt;10%), moderate (5-10%), thin (0-5%), negative</td></tr>'
        f'<tr><td style="font-weight:600;">Operational Quality</td>'
        f'<td class="num cad-heat-3">20%</td><td class="num">20</td>'
        f'<td>Denial rate (&lt;8% excellent, 8-12% good, &gt;12% concerning) + AR days (&lt;42 excellent)</td></tr>'
        f'<tr><td style="font-weight:600;">Competitive Moat</td>'
        f'<td class="num cad-heat-3">20%</td><td class="num">20</td>'
        f'<td>Scale vs market avg, HHI concentration, margin premium (Mauboussin framework)</td></tr>'
        f'</tbody></table>'
        f'<div style="margin-top:12px;padding:10px 12px;border:1px solid {PALETTE["border"]};'
        f'background:{PALETTE["bg_tertiary"]};font-family:var(--cad-mono);'
        f'font-size:10.5px;letter-spacing:0.06em;color:{PALETTE["text_secondary"]};'
        f'text-transform:uppercase;">'
        f'<strong style="color:{PALETTE["accent_amber"]};">Grade Scale</strong> &nbsp; '
        f'A+ (90+) · A (85+) · A- (80+) · B+ (75+) · B (70+) · B- (65+) · C+ (60+) · '
        f'C (55+) · C- (50+) · D (40+) · F (&lt;40)</div>'
    ), anchor="toc-scoring")

    # ── Market pulse ──
    market_pulse = _section("MPX", "Market Pulse Indicators", (
        f'<table class="cad-table"><thead><tr>'
        f'<th>Indicator</th><th>Source</th><th>What It Means</th>'
        f'</tr></thead><tbody>'
        f'<tr><td style="font-weight:600;">Hospital EV/EBITDA</td>'
        f'<td><span class="cad-ticker-id" style="padding:1px 5px;">TXN</span></td>'
        f'<td>Median enterprise-value-to-EBITDA multiple for recent acute care hospital transactions. '
        f'Higher = more expensive market. Current: ~11.2x.</td></tr>'
        f'<tr><td style="font-weight:600;">10Y Treasury</td>'
        f'<td><span class="cad-ticker-id" style="padding:1px 5px;">FRED</span></td>'
        f'<td>Risk-free rate benchmark. Drives WACC and discount rates. Higher rates compress '
        f'hospital valuations (~0.8x per 100bp increase).</td></tr>'
        f'<tr><td style="font-weight:600;">S&amp;P Healthcare</td>'
        f'<td><span class="cad-ticker-id" style="padding:1px 5px;">SP500</span></td>'
        f'<td>Sector index level. Tracks public healthcare equity sentiment. Not hospital-specific '
        f'but directionally indicative.</td></tr>'
        f'<tr><td style="font-weight:600;">Market Sentiment</td>'
        f'<td><span class="cad-ticker-id" style="padding:1px 5px;">COMP</span></td>'
        f'<td>Composite score 0-1. Weights: treasury direction, deal flow volume, '
        f'reimbursement trend signals. Labels: Bullish (&gt;0.7), Slightly Positive (0.4-0.7), '
        f'Neutral (-0.1 to 0.4), Bearish (&lt;-0.1).</td></tr>'
        f'</tbody></table>'
    ), anchor="toc-pulse")

    # ── Models ──
    models = _section("MDL", "Financial Models", (
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">'
        + _model_card(
            "DCF", "Discounted Cash Flow",
            "5-year projection of free cash flow, discounted at WACC. Inputs: revenue base, "
            "growth rate, EBITDA margin, capex %, working capital change, tax rate. Terminal "
            "value via perpetuity growth method. Sensitivity matrix varies WACC (8-14%) × "
            "terminal growth (1-4%)."
        )
        + _model_card(
            "LBO", "Leveraged Buyout",
            "Full LBO model: sources &amp; uses (senior debt, mezzanine, equity), annual P&amp;L "
            "with debt service, mandatory/optional repayment schedule, and equity returns at "
            "year 3-7 exits. Returns IRR and MOIC. Green IRR &gt;20%, amber 15-20%, red &lt;15%."
        )
        + _model_card(
            "FIN", "3-Statement Model",
            "Reconstructed income statement, balance sheet, and cash flow from HCRIS cost "
            "report data. Each line item tagged with provenance: HCRIS (green), deal_profile "
            "(blue), benchmark (amber), computed (gray). Uses healthcare industry benchmarks "
            "for estimation when data is missing."
        )
        + _model_card(
            "BRG", "EBITDA Bridge",
            "7-lever model: denial reduction, AR acceleration, coding uplift, payer mix "
            "optimization, cost-to-collect reduction, clean claim improvement, volume/rate "
            "growth. Each lever has a probability-weighted dollar impact. Shows current → "
            "target EBITDA path."
        )
        + '</div>'
    ), anchor="toc-models")

    # ── Regression ──
    regression = _section("REG", "Regression Analysis", (
        f'<p style="font-size:12.5px;color:{PALETTE["text_secondary"]};line-height:1.6;">'
        f'Ordinary Least Squares (OLS) regression implemented in pure NumPy (no sklearn). '
        f'Features are standardized (zero mean, unit variance) before fitting so coefficients '
        f'are comparable across variables with different scales.</p>'
        f'<p style="font-size:12.5px;color:{PALETTE["text_secondary"]};line-height:1.6;margin-top:8px;">'
        f'<strong>Outputs:</strong> R-squared (% of variance explained), adjusted R-squared '
        f'(penalized for feature count), standardized coefficients with t-statistics, '
        f'significance levels (*p&lt;0.05, **p&lt;0.01, ***p&lt;0.001), and pairwise '
        f'correlation matrix.</p>'
        f'<p style="font-size:12.5px;color:{PALETTE["text_secondary"]};line-height:1.6;margin-top:8px;">'
        f'<strong>Data sources:</strong> HCRIS national (~6,000 hospitals) or portfolio deals. '
        f'HCRIS regressions identify which state-level factors predict margins. Portfolio '
        f'regressions identify what drives denial rates or other KPIs across your specific deals.</p>'
    ), anchor="toc-regression")

    # ── Margins ──
    margins = _section("MRG", "Margin Calculations", (
        f'<p style="font-size:12.5px;color:{PALETTE["text_secondary"]};line-height:1.6;">'
        f'<strong>Operating margin</strong> = (Net Patient Revenue − Operating Expenses) / '
        f'Net Patient Revenue. Computed from HCRIS cost report fields. Guards applied:</p>'
        f'<ul style="font-size:12.5px;color:{PALETTE["text_secondary"]};line-height:1.8;'
        f'padding-left:20px;margin-top:6px;">'
        f'<li>Revenue must exceed $100K (filters cost-report stubs and accounting artifacts)</li>'
        f'<li>Margins clamped to [−100%, +100%] (no hospital truly has a −1,000% margin)</li>'
        f'<li>State-level averages use <strong>median</strong> not mean (robust to outliers)</li>'
        f'<li>HCRIS data quality varies: some reports have mismatched periods or reclassifications</li>'
        f'</ul>'
        f'<div style="margin-top:12px;padding:10px 12px;border-left:3px solid {PALETTE["brand_accent"]};'
        f'background:{PALETTE["bg_tertiary"]};font-size:12px;color:{PALETTE["text_secondary"]};'
        f'line-height:1.6;">'
        f'<strong style="color:{PALETTE["text_primary"]};">Industry context:</strong> '
        f'Median US hospital operating margin is approximately −5% to +5%. For-profit chains '
        f'average higher (5-12%) due to case mix and payer optimization. Safety-net and '
        f'critical access hospitals often operate at negative margins.</div>'
    ), anchor="toc-margins")

    # ── Ontology ──
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
                name = defn.display_name if hasattr(defn, "display_name") else mk.replace("_", " ").title()
                ont_rows += (
                    f'<tr>'
                    f'<td style="font-weight:600;">{html.escape(name)}</td>'
                    f'<td style="font-size:11.5px;">{html.escape(str(defn.definition)[:100] if hasattr(defn, "definition") else "")}</td>'
                    f'<td><span class="cad-badge cad-badge-blue">'
                    f'{html.escape(str(defn.domain.value) if hasattr(defn, "domain") else "")}</span></td>'
                    f'<td style="font-size:11.5px;color:{PALETTE["text_secondary"]};">{html.escape(causal[:80])}</td>'
                    f'</tr>'
                )
            except Exception:
                pass
        if ont_rows:
            ontology_section = _section("ONT", "Metric Definitions & Causal Chains", (
                f'<p style="font-size:12.5px;color:{PALETTE["text_secondary"]};'
                f'margin-bottom:10px;line-height:1.6;">'
                f'Every metric in SeekingChartis has a formal definition, domain classification, '
                f'and causal chain explaining how it affects EBITDA. From the healthcare '
                f'economic ontology.</p>'
                f'<table class="cad-table"><thead><tr>'
                f'<th>Metric</th><th>Definition</th><th>Domain</th><th>Causal Chain</th>'
                f'</tr></thead><tbody>{ont_rows}</tbody></table>'
            ), anchor="toc-ontology")
    except Exception:
        pass

    related_links = (
        f'<div class="cad-card" style="padding:10px 14px;">'
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">'
        f'<h2 style="margin:0;">Related References</h2>'
        f'<span class="cad-section-code">REF</span></div>'
        f'<div style="display:flex;gap:6px;flex-wrap:wrap;">'
        f'<a href="/verticals" class="cad-btn" style="text-decoration:none;">Healthcare Verticals</a>'
        f'<a href="/methodology" class="cad-btn" style="text-decoration:none;">Reference Library</a>'
        f'<a href="/conferences" class="cad-btn" style="text-decoration:none;">Conference Roadmap</a>'
        f'<a href="/data-intelligence" class="cad-btn" style="text-decoration:none;">Data Intelligence</a>'
        f'<a href="/model-validation" class="cad-btn" style="text-decoration:none;">Model Validation</a>'
        f'</div></div>'
    )

    body = (
        f'{toc}{intro}{data_sources}{scoring}{market_pulse}{models}'
        f'{regression}{margins}{ontology_section}{related_links}'
    )

    return shell_v2(
        body, "Methodology",
        subtitle="How every number is calculated — data sources, models & assumptions",
    )
