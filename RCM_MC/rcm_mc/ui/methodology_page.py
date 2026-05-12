"""SeekingChartis Methodology — how every number is calculated.

Builds trust with users by explaining data sources, scoring models,
and analytical approaches in plain language.
"""
from __future__ import annotations

import html
from typing import Any

from ._chartis_kit import (
    chartis_shell, ck_kpi_block, ck_next_section, ck_panel,
    ck_section_header, ck_section_intro, ck_signal_badge,
)
from .brand import PALETTE


def _section(code: str, title: str, content: str, *, anchor: str = "") -> str:
    """Render a methodology section. Editorial wrapper: ck_panel with
    a ck_section_header inside (eyebrow + ck_signal_badge for the
    Bloomberg-style code chip)."""
    header = ck_section_header(title, eyebrow=code)
    aid = f' id="{html.escape(anchor)}"' if anchor else ""
    return (
        f'<div{aid}>'
        + ck_panel(f'{header}{content}')
        + '</div>'
    )


def _source_card(code: str, title: str, body: str, meta: str) -> str:
    """Render a data-source mini card via ck_panel.

    Code → neutral signal-badge in the title row. Body + meta land
    inside the panel as section-body text.
    """
    badge = ck_signal_badge(code, tone="neutral")
    inner = (
        f'<p class="ck-section-body">{body}</p>'
        f'<p class="ck-eyebrow">{html.escape(meta)}</p>'
    )
    return ck_panel(f'{badge} {inner}', title=title)


def _model_card(code: str, title: str, body: str) -> str:
    """Render a model mini card via ck_panel + signal badge."""
    badge = ck_signal_badge(code, tone="neutral")
    inner = f'<p class="ck-section-body">{body}</p>'
    return ck_panel(f'{badge} {inner}', title=title)


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
        f'<a href="#{aid}" class="ck-link">'
        f'{ck_signal_badge(code, tone="neutral")} {html.escape(name)}</a>'
        for code, name, aid in toc_items
    )
    toc = ck_panel(
        f'<div class="ck-toc-list">{toc_html}</div>',
        title="Contents",
    )

    # ── Intro ── ck_section_intro provides the italic-serif "audit"
    # cadence; intro stats sit below in a ck_kpi_strip.
    intro_hero = ck_section_intro(
        eyebrow="METHODOLOGY",
        headline="How every number on the platform can be audited.",
        italic_word="audited",
        body=(
            "SeekingChartis combines public hospital data with "
            "proprietary analytical models to generate diligence-grade "
            "intelligence for healthcare PE. Every number on this "
            "platform traces back to a specific data source and "
            "calculation — you should be able to audit any output "
            "end-to-end."
        ),
    )
    intro_body = (
        f'{intro_hero}'
        '<div class="ck-kpi-strip">'
        + ck_kpi_block(
            "Hospitals Tracked", "6,123",
            help={
                "definition": (
                    "Every short-term acute, CAH, IRF, LTCH, and psych "
                    "hospital that filed a CMS HCRIS cost report in "
                    "the most-recent fiscal year. Used as the "
                    "denominator behind every percentile rank — a "
                    "hospital at P75 outperforms ~4,592 peers."
                ),
            },
        )
        + ck_kpi_block(
            "Analytical Models", "17",
            help={
                "definition": (
                    "Per-deal analytical models the platform runs: "
                    "RCM regression, denial drivers, EBITDA bridge, "
                    "Monte Carlo simulation, scenario layering, "
                    "Bayesian calibration, conformal bands, "
                    "comparable-deal matching, sensitivity sweep, "
                    "and 8 more. Each documented in its own section "
                    "below."
                ),
            },
        )
        + ck_kpi_block(
            "Passing Tests", "3,157",
            help={
                "definition": (
                    "Tests in the unittest suite that pass on every "
                    "commit — the regression gate. Run via "
                    "`pytest -q`. Each model has a dedicated "
                    "test_<feature>.py file + bug-fix regression "
                    "asserts so a partner can verify the platform "
                    "behaves on their machine before trusting outputs."
                ),
            },
        )
        + ck_kpi_block(
            "API Endpoints", "52",
            help={
                "definition": (
                    "Documented HTTP API routes (52 paths across 56 "
                    "method/path combos) covered by the OpenAPI spec "
                    "at /api/docs. Every UI page has a JSON-API "
                    "equivalent so partners can script + automate "
                    "anything the editorial UI does."
                ),
            },
        )
        + '</div>'
    )
    intro = _section("INTRO", "Overview", intro_body, anchor="toc-intro")

    # ── Data sources ──
    data_sources = _section("DAT", "Data Sources", (
        '<div class="ck-card-grid">'
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
        f'<p class="ck-section-body">'
        f'Every hospital gets a composite investability score from 0 to 100, graded A+ to F. '
        f'The score combines four weighted components:</p>'
        f'<table class="cad-table"><thead><tr>'
        f'<th>Component</th><th>Weight</th><th>Max Pts</th><th>What It Measures</th>'
        f'</tr></thead><tbody>'
        f'<tr><td><strong>Market Position</strong></td>'
        f'<td class="num cad-heat-2">35%</td><td class="num">35</td>'
        f'<td>Bed count (small/mid/large) + net patient revenue (scale advantage)</td></tr>'
        f'<tr><td><strong>Financial Health</strong></td>'
        f'<td class="num cad-heat-3">25%</td><td class="num">25</td>'
        f'<td>Operating margin: strong (&gt;10%), moderate (5-10%), thin (0-5%), negative</td></tr>'
        f'<tr><td><strong>Operational Quality</strong></td>'
        f'<td class="num cad-heat-3">20%</td><td class="num">20</td>'
        f'<td>Denial rate (&lt;8% excellent, 8-12% good, &gt;12% concerning) + AR days (&lt;42 excellent)</td></tr>'
        f'<tr><td><strong>Competitive Moat</strong></td>'
        f'<td class="num cad-heat-3">20%</td><td class="num">20</td>'
        f'<td>Scale vs market avg, HHI concentration, margin premium (Mauboussin framework)</td></tr>'
        f'</tbody></table>'
        f'<p class="ck-eyebrow" style="margin-top:12px;">'
        f'<strong>Grade Scale</strong> &nbsp; '
        f'A+ (90+) · A (85+) · A- (80+) · B+ (75+) · B (70+) · B- (65+) · C+ (60+) · '
        f'C (55+) · C- (50+) · D (40+) · F (&lt;40)</p>'
    ), anchor="toc-scoring")

    # ── Market pulse ──
    market_pulse = _section("MPX", "Market Pulse Indicators", (
        f'<table class="cad-table"><thead><tr>'
        f'<th>Indicator</th><th>Source</th><th>What It Means</th>'
        f'</tr></thead><tbody>'
        f'<tr><td><strong>Hospital EV/EBITDA</strong></td>'
        f'<td><span class="cad-ticker-id">TXN</span></td>'
        f'<td>Median enterprise-value-to-EBITDA multiple for recent acute care hospital transactions. '
        f'Higher = more expensive market. Current: ~11.2x.</td></tr>'
        f'<tr><td><strong>10Y Treasury</strong></td>'
        f'<td><span class="cad-ticker-id">FRED</span></td>'
        f'<td>Risk-free rate benchmark. Drives WACC and discount rates. Higher rates compress '
        f'hospital valuations (~0.8x per 100bp increase).</td></tr>'
        f'<tr><td><strong>S&amp;P Healthcare</strong></td>'
        f'<td><span class="cad-ticker-id">SP500</span></td>'
        f'<td>Sector index level. Tracks public healthcare equity sentiment. Not hospital-specific '
        f'but directionally indicative.</td></tr>'
        f'<tr><td><strong>Market Sentiment</strong></td>'
        f'<td><span class="cad-ticker-id">COMP</span></td>'
        f'<td>Composite score 0-1. Weights: treasury direction, deal flow volume, '
        f'reimbursement trend signals. Labels: Bullish (&gt;0.7), Slightly Positive (0.4-0.7), '
        f'Neutral (-0.1 to 0.4), Bearish (&lt;-0.1).</td></tr>'
        f'</tbody></table>'
    ), anchor="toc-pulse")

    # ── Models ──
    models = _section("MDL", "Financial Models", (
        '<div class="ck-card-grid">'
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
        f'<p class="ck-section-body">'
        f'Ordinary Least Squares (OLS) regression implemented in pure NumPy (no sklearn). '
        f'Features are standardized (zero mean, unit variance) before fitting so coefficients '
        f'are comparable across variables with different scales.</p>'
        f'<p class="ck-section-body">'
        f'<strong>Outputs:</strong> R-squared (% of variance explained), adjusted R-squared '
        f'(penalized for feature count), standardized coefficients with t-statistics, '
        f'significance levels (*p&lt;0.05, **p&lt;0.01, ***p&lt;0.001), and pairwise '
        f'correlation matrix.</p>'
        f'<p class="ck-section-body">'
        f'<strong>Data sources:</strong> HCRIS national (~6,000 hospitals) or portfolio deals. '
        f'HCRIS regressions identify which state-level factors predict margins. Portfolio '
        f'regressions identify what drives denial rates or other KPIs across your specific deals.</p>'
    ), anchor="toc-regression")

    # ── Margins ──
    margins = _section("MRG", "Margin Calculations", (
        f'<p class="ck-section-body">'
        f'<strong>Operating margin</strong> = (Net Patient Revenue − Operating Expenses) / '
        f'Net Patient Revenue. Computed from HCRIS cost report fields. Guards applied:</p>'
        f'<ul class="ck-list">'
        f'<li>Revenue must exceed $100K (filters cost-report stubs and accounting artifacts)</li>'
        f'<li>Margins clamped to [−100%, +100%] (no hospital truly has a −1,000% margin)</li>'
        f'<li>State-level averages use <strong>median</strong> not mean (robust to outliers)</li>'
        f'<li>HCRIS data quality varies: some reports have mismatched periods or reclassifications</li>'
        f'</ul>'
        f'<p class="ck-section-body">'
        f'<strong>Industry context:</strong> '
        f'Median US hospital operating margin is approximately −5% to +5%. For-profit chains '
        f'average higher (5-12%) due to case mix and payer optimization. Safety-net and '
        f'critical access hospitals often operate at negative margins.</p>'
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
                    f'<td><strong>{html.escape(name)}</strong></td>'
                    f'<td>{html.escape(str(defn.definition)[:100] if hasattr(defn, "definition") else "")}</td>'
                    f'<td><span class="cad-badge cad-badge-blue">'
                    f'{html.escape(str(defn.domain.value) if hasattr(defn, "domain") else "")}</span></td>'
                    f'<td>{html.escape(causal[:80])}</td>'
                    f'</tr>'
                )
            except Exception:
                pass
        if ont_rows:
            ontology_section = _section("ONT", "Metric Definitions & Causal Chains", (
                f'<p class="ck-section-body">'
                f'Every metric in SeekingChartis has a formal definition, domain classification, '
                f'and causal chain explaining how it affects EBITDA. From the healthcare '
                f'economic ontology.</p>'
                f'<table class="cad-table"><thead><tr>'
                f'<th>Metric</th><th>Definition</th><th>Domain</th><th>Causal Chain</th>'
                f'</tr></thead><tbody>{ont_rows}</tbody></table>'
            ), anchor="toc-ontology")
    except Exception:
        pass

    related_links = ck_panel(
        '<p class="ck-section-body">'
        '<a href="/verticals" class="cad-btn">Healthcare Verticals</a> '
        '<a href="/methodology" class="cad-btn">Reference Library</a> '
        '<a href="/conferences" class="cad-btn">Conference Roadmap</a> '
        '<a href="/data-intelligence" class="cad-btn">Data Intelligence</a> '
        '<a href="/model-validation" class="cad-btn">Model Validation</a>'
        '</p>',
        title="Related References",
    )

    from rcm_mc.ui.chartis._helpers import render_page_explainer
    explainer = render_page_explainer(
        what=(
            "Step-by-step explanations of how each number on the "
            "platform is computed — data sources, scoring model, "
            "model assumptions, and metric ontology."
        ),
        page_key="methodology-calculations",
    )

    next_up = ck_next_section(
        "Open the metric glossary",
        "/metric-glossary",
        eyebrow="Continue —",
        italic_word="glossary",
    )
    body = (
        f'{explainer}{toc}{intro}{data_sources}{scoring}{market_pulse}{models}'
        f'{regression}{margins}{ontology_section}{related_links}{next_up}'
    )

    return chartis_shell(
        body, "Methodology",
        subtitle="How every number is calculated — data sources, models & assumptions",
    )
