"""SeekingChartis News — healthcare PE market news aggregator.

Curates healthcare industry news, regulatory updates, and deal
activity into a Seeking Alpha-style article feed.
"""
from __future__ import annotations

import html
from datetime import datetime, timezone
from typing import Any, Dict, List

from ._chartis_kit import chartis_shell
from .brand import PALETTE


_NEWS_CATEGORIES = [
    ("All", "all"),
    ("M&A Activity", "ma"),
    ("Regulatory", "regulatory"),
    ("Payer Policy", "payer"),
    ("RCM Industry", "rcm"),
    ("Financial Results", "earnings"),
    ("Research", "research"),
]

_CURATED_ARTICLES = [
    {
        "title": "CMS Finalizes 2026 OPPS Rule: +2.9% Payment Update",
        "subtitle": "Medicare outpatient payment rates rise, but labor cost pressures remain",
        "category": "regulatory",
        "source": "CMS.gov",
        "date": "2026-04-14",
        "body": (
            "CMS finalized the CY2026 Outpatient Prospective Payment System rule with a net "
            "+2.9% payment update. The update reflects the hospital market basket increase of "
            "3.2% offset by a -0.3 pp productivity adjustment. Key changes include expanded "
            "ASC-covered procedures and revised payment for clinic visits. For PE-backed "
            "hospitals, the update is modestly positive but unlikely to offset wage inflation "
            "in high-cost labor markets."
        ),
        "impact": "Modestly positive for hospital revenue models",
        "severity": "info",
    },
    {
        "title": "UnitedHealth Reports Q1: Denial Rates Tick Up to 16.2%",
        "subtitle": "Commercial payer tightening prior-auth requirements across surgical categories",
        "category": "payer",
        "source": "UNH 10-Q Filing",
        "date": "2026-04-10",
        "body": (
            "UnitedHealth Group's Q1 2026 filing reveals a continued trend of prior "
            "authorization tightening. Medical loss ratio improved to 82.4% (vs 83.1% YoY), "
            "driven partly by higher initial denial rates. Surgical categories seeing the "
            "most aggressive review include orthopedic procedures, advanced imaging, and "
            "outpatient cardiac. Hospitals with >15% denial rates should expect further "
            "headwinds from commercial payers."
        ),
        "impact": "Negative for hospitals with weak denial management",
        "severity": "warning",
    },
    {
        "title": "Lifepoint Health Explores $8.2B Sale Process",
        "subtitle": "PE-backed hospital chain draws interest from strategic buyers",
        "category": "ma",
        "source": "Bloomberg",
        "date": "2026-04-08",
        "body": (
            "Lifepoint Health, owned by Apollo Global Management, is exploring strategic "
            "alternatives including a potential sale valued at $8.2B including debt. The "
            "company operates 89 hospitals across 29 states with $10.4B in annual revenue. "
            "Potential acquirers include HCA Healthcare and a consortium of infrastructure "
            "investors. The implied EV/EBITDA multiple of ~11.5x sets a benchmark for "
            "mid-market hospital valuations."
        ),
        "impact": "Sets valuation benchmark at 11.5x EV/EBITDA",
        "severity": "info",
    },
    {
        "title": "RCM Outsourcing Market Reaches $22B: Consolidation Accelerates",
        "subtitle": "R1 RCM, Ensemble Health, and nThrive compete for hospital contracts",
        "category": "rcm",
        "source": "McKinsey Healthcare",
        "date": "2026-04-05",
        "body": (
            "The revenue cycle management outsourcing market reached $22B in 2025, growing "
            "at 12% CAGR. Key drivers include labor shortages (medical coder vacancy rates "
            "at 18%), payer complexity, and AI adoption for claims processing. Hospitals "
            "outsourcing RCM report average AR day reductions of 8-12 days and denial rate "
            "improvements of 3-5 percentage points. However, switching costs are high: "
            "average contract duration is 5-7 years with $2-4M transition costs."
        ),
        "impact": "Informs RCM improvement thesis for diligence",
        "severity": "info",
    },
    {
        "title": "10-Year Treasury Yield at 4.31%: Impact on Hospital Multiples",
        "subtitle": "Rising rates compress healthcare PE valuations by 0.5-1.0x turns",
        "category": "earnings",
        "source": "Federal Reserve / Capital IQ",
        "date": "2026-04-03",
        "body": (
            "The 10-year Treasury yield reached 4.31%, up 18bps over the past month. "
            "Healthcare hospital multiples show a -0.7 correlation with 10Y rates: each "
            "100bp increase compresses EV/EBITDA by approximately 0.8x. Current hospital "
            "transaction multiples average 10.8x, down from 12.1x at the 2021 rate trough. "
            "For LBO models, higher rates increase interest expense and reduce equity "
            "returns by 200-400bps IRR at typical leverage levels."
        ),
        "impact": "Reduces LBO returns; raises WACC in DCF models",
        "severity": "warning",
    },
    {
        "title": "Medicaid Unwinding Complete: 18.4M Disenrolled Nationwide",
        "subtitle": "Uncompensated care rising at hospitals with high Medicaid mix",
        "category": "regulatory",
        "source": "KFF Health Tracking",
        "date": "2026-03-28",
        "body": (
            "The post-pandemic Medicaid continuous enrollment unwinding is now complete, "
            "with 18.4M individuals disenrolled from Medicaid/CHIP. Approximately 40% of "
            "disenrollments were procedural (not loss of eligibility). Hospitals in states "
            "that did not expand Medicaid are seeing the largest increases in uncompensated "
            "care. Safety-net hospitals report 15-25% increases in self-pay volume. Payer "
            "mix shifts should be modeled in diligence for hospitals with >25% Medicaid days."
        ),
        "impact": "Negative for high-Medicaid hospitals; model payer mix shifts",
        "severity": "critical",
    },
    # Additional M&A
    {
        "title": "HCA Healthcare Completes $2.1B Acquisition of Steward Health Assets",
        "subtitle": "Largest hospital operator expands into new markets via distressed acquisitions",
        "category": "ma",
        "source": "Modern Healthcare",
        "date": "2026-03-20",
        "body": (
            "HCA Healthcare completed the acquisition of select Steward Health Care assets "
            "for $2.1B, adding 14 hospitals across 6 states. The transaction was structured "
            "as an asset purchase from bankruptcy, allowing HCA to cherry-pick the strongest "
            "facilities. Entry multiples averaged 8.5x trailing EBITDA — below the 10-11x "
            "market average — reflecting the distressed seller dynamics. HCA plans $400M in "
            "capital improvements over 3 years."
        ),
        "impact": "Sets distressed-asset valuation benchmarks; watch for more Steward divestitures",
        "severity": "info",
    },
    {
        "title": "Private Equity Hospital Deal Volume Down 22% YoY in Q1 2026",
        "subtitle": "Higher rates and regulatory scrutiny slow healthcare LBO activity",
        "category": "ma",
        "source": "Bain Healthcare Report",
        "date": "2026-04-01",
        "body": (
            "PE-backed hospital transactions fell 22% year-over-year in Q1 2026, driven by "
            "higher financing costs (+150bps vs 2021 trough) and FTC scrutiny of market "
            "concentration. Average hold periods extended to 5.8 years (vs 4.2 historically). "
            "The gap between buyer and seller price expectations remains wide: sellers anchor "
            "to 2021-vintage 12x multiples while buyers bid 9-10x reflecting current rates."
        ),
        "impact": "Buyer's market emerging; patience on entry pricing is rewarded",
        "severity": "info",
    },
    # Payer
    {
        "title": "Prior Authorization Reform: CMS Final Rule Mandates 72-Hour Turnaround",
        "subtitle": "Payers must respond to prior auth requests within 72 hours starting Jan 2027",
        "category": "payer",
        "source": "CMS.gov",
        "date": "2026-03-15",
        "body": (
            "CMS finalized the Interoperability and Prior Authorization Rule (CMS-0057-F), "
            "requiring Medicare Advantage and Medicaid managed care plans to process prior "
            "authorization requests within 72 hours (urgent) or 7 days (standard). Plans must "
            "also provide denial reason codes. Expected to reduce prior auth denials by 15-20% "
            "and accelerate revenue recognition for hospitals with high MA patient populations."
        ),
        "impact": "Positive for hospitals with high denial rates from prior auth delays",
        "severity": "info",
    },
    # RCM
    {
        "title": "AI-Powered Coding: Early Adopters Report 12% Accuracy Improvement",
        "subtitle": "NLP-based auto-coding reduces human coding errors and speeds claim submission",
        "category": "rcm",
        "source": "HFMA Journal",
        "date": "2026-03-10",
        "body": (
            "Hospitals deploying AI-powered medical coding report 12% improvement in first-pass "
            "coding accuracy and 35% reduction in coding turnaround time. Leaders include Epic's "
            "integrated coding assistant and standalone vendors like Nym and AGS Health. ROI is "
            "strongest for hospitals with >200 beds processing >100K annual claims. Implementation "
            "costs range from $500K-$2M with 12-18 month payback periods."
        ),
        "impact": "Factor AI coding into denial reduction thesis for targets with legacy coding",
        "severity": "info",
    },
    {
        "title": "Revenue Cycle Staffing Crisis: 23% Vacancy Rate for Medical Coders",
        "subtitle": "Labor shortage drives outsourcing and automation adoption",
        "category": "rcm",
        "source": "AAPC Workforce Survey",
        "date": "2026-02-28",
        "body": (
            "The 2026 AAPC Workforce Survey reports a 23% vacancy rate for certified medical "
            "coders, up from 18% in 2024. Average coder tenure has fallen to 2.3 years. "
            "Hospitals respond by outsourcing (45% of facilities now use offshore coding), "
            "investing in AI automation (32%), and increasing pay (avg +8% YoY). For PE diligence, "
            "assess the target's coding workforce stability and automation readiness."
        ),
        "impact": "Coding workforce risk is a diligence item; automation readiness is a value lever",
        "severity": "warning",
    },
    # Research / Academic
    {
        "title": "NBER Working Paper: Hospital Market Concentration and Patient Outcomes",
        "subtitle": "New evidence on the relationship between HHI and quality of care",
        "category": "research",
        "source": "National Bureau of Economic Research",
        "date": "2026-03-01",
        "body": (
            "A new NBER working paper (w34521) by Gaynor, Ho, and Town analyzes 15 years of "
            "Medicare claims data across 3,400 hospital markets. Key findings: (1) markets with "
            "HHI >2500 show 3.2% higher 30-day mortality for AMI patients, (2) post-merger "
            "price increases average 7-12% within 3 years, (3) quality effects are heterogeneous — "
            "mergers between close competitors show worse outcomes than mergers between distant "
            "facilities. Implications for PE: market concentration supports pricing power but "
            "may invite regulatory scrutiny."
        ),
        "impact": "Supports moat thesis but flags regulatory risk in concentrated markets",
        "severity": "info",
    },
    {
        "title": "Health Affairs: The Financial Impact of Denial Management Programs",
        "subtitle": "Systematic review of 47 hospitals implementing structured denial programs",
        "category": "research",
        "source": "Health Affairs",
        "date": "2026-02-15",
        "body": (
            "A systematic review in Health Affairs analyzed 47 hospitals that implemented "
            "structured denial management programs between 2019-2024. Results: average denial "
            "rate reduction of 4.3 percentage points (from 14.1% to 9.8%), with $2.8M average "
            "annual revenue recovery. Programs with dedicated denial analysts showed 2x the "
            "improvement vs technology-only approaches. ROI averaged 340% over 24 months. "
            "Key success factors: executive sponsorship, root cause analytics, payer-specific "
            "intervention protocols, and monthly performance reviews."
        ),
        "impact": "Validates denial reduction thesis; 4.3pp improvement is achievable with structure",
        "severity": "info",
    },
    {
        "title": "McKinsey: The $200B RCM Automation Opportunity in US Healthcare",
        "subtitle": "Detailed sizing of automation potential across the revenue cycle",
        "category": "research",
        "source": "McKinsey & Company",
        "date": "2026-01-20",
        "body": (
            "McKinsey's latest healthcare operations report sizes the US RCM automation "
            "opportunity at $200B in annual administrative waste. Breakdown: prior authorization "
            "($42B), claims submission and follow-up ($38B), payment posting and reconciliation "
            "($28B), patient billing ($22B), coding and documentation ($35B), and eligibility "
            "verification ($18B). Current automation penetration is only 12%. Hospitals that "
            "achieve 50%+ automation report 30-40% RCM cost reduction."
        ),
        "impact": "Sizes the total addressable market for RCM improvement thesis",
        "severity": "info",
    },
    {
        "title": "Journal of Health Economics: Price Elasticity of Hospital Demand by Service Line",
        "subtitle": "Empirical estimates of demand elasticity using Medicare claims variation",
        "category": "research",
        "source": "Journal of Health Economics",
        "date": "2026-01-05",
        "body": (
            "Using 2015-2023 Medicare FFS claims and geographic payment variation as natural "
            "experiments, researchers estimate demand elasticity by service line: cardiac surgery "
            "-0.08 (very inelastic), dialysis -0.05, oncology -0.12, orthopedic -0.35, "
            "general surgery -0.28, behavioral health -0.22. Emergency services are perfectly "
            "inelastic (-0.01). Implications: hospitals concentrated in inelastic service lines "
            "have more defensible revenue streams against reimbursement cuts."
        ),
        "impact": "Quantifies demand stickiness by service line — use in demand analysis",
        "severity": "info",
    },
    {
        "title": "Deloitte: 2026 Hospital M&A Outlook — From Volume to Value",
        "subtitle": "Annual survey of 200+ health system CFOs on deal priorities",
        "category": "research",
        "source": "Deloitte Center for Health Solutions",
        "date": "2025-12-15",
        "body": (
            "Deloitte's annual CFO survey reveals shifting M&A priorities: 68% now cite 'access "
            "to technology/analytics' as the primary acquisition driver (vs 42% citing 'market "
            "share' in 2020). Top technology targets: AI coding (71%), patient engagement (58%), "
            "predictive analytics (52%), and automated prior auth (49%). Average deal timeline "
            "extended from 8 months to 14 months due to regulatory review. 45% of respondents "
            "expect to complete at least one acquisition in 2026."
        ),
        "impact": "Technology capabilities increasingly drive deal rationale over geographic footprint",
        "severity": "info",
    },
    # Earnings
    {
        "title": "Tenet Healthcare Q1 2026: Revenue +8.2%, Same-Hospital Admissions +4.1%",
        "subtitle": "Outperforms guidance on volume recovery and payer mix improvement",
        "category": "earnings",
        "source": "THC Earnings Release",
        "date": "2026-04-12",
        "body": (
            "Tenet Healthcare reported Q1 2026 revenue of $5.4B (+8.2% YoY), driven by 4.1% "
            "same-hospital admission growth and favorable payer mix shift (commercial mix +2.1pp). "
            "Adjusted EBITDA margin expanded 80bps to 18.4%. Management raised full-year guidance "
            "by $200M. Key drivers: ambulatory surgery center portfolio (45% of EBITDA, +12% YoY), "
            "reduced labor costs (-3.2% per adjusted admission), and Medicare Advantage volume growth."
        ),
        "impact": "Validates ASC growth thesis; labor cost improvement is replicable",
        "severity": "info",
    },
    {
        "title": "Community Health Systems Warns on Rural Hospital Viability",
        "subtitle": "35% of CHS rural facilities operating below breakeven margin",
        "category": "earnings",
        "source": "CYH 10-Q Filing",
        "date": "2026-04-08",
        "body": (
            "CHS disclosed that 35% of its rural hospital portfolio (28 of 80 facilities) "
            "operated below breakeven in Q1 2026. Contributing factors: 42% Medicare patient "
            "mix (vs 30% system average), staffing costs +15% in rural markets, and limited "
            "commercial payer leverage. CHS is evaluating 'strategic alternatives' for 12 "
            "underperforming rural facilities. For PE diligence: rural hospital targets require "
            "careful assessment of payer mix sustainability and labor market dynamics."
        ),
        "impact": "Rural hospital distress creates acquisition opportunities but with payer mix risk",
        "severity": "warning",
    },
]


def _article_card(article: Dict[str, Any]) -> str:
    sev = article.get("severity", "info")
    color = {
        "critical": PALETTE["critical"],
        "warning": PALETTE["warning"],
    }.get(sev, PALETTE["brand_accent"])

    cat_badge_cls = {
        "ma": "cad-badge-blue",
        "regulatory": "cad-badge-amber",
        "payer": "cad-badge-red",
        "rcm": "cad-badge-green",
        "earnings": "cad-badge-muted",
    }.get(article.get("category", ""), "cad-badge-muted")

    return (
        f'<div class="cad-card" style="border-left:3px solid {color};">'
        f'<div style="display:flex;justify-content:space-between;align-items:start;margin-bottom:6px;">'
        f'<div style="display:flex;gap:8px;align-items:center;">'
        f'<span class="cad-badge {cat_badge_cls}">{html.escape(article.get("category", "").upper())}</span>'
        f'<span style="font-size:11px;color:{PALETTE["text_muted"]};">'
        f'{html.escape(article.get("source", ""))}</span>'
        f'</div>'
        f'<span style="font-size:11px;color:{PALETTE["text_muted"]};">'
        f'{html.escape(article.get("date", ""))}</span>'
        f'</div>'
        f'<h2 style="margin-bottom:4px;">{html.escape(article.get("title", ""))}</h2>'
        f'<div style="color:{PALETTE["text_secondary"]};font-size:12.5px;margin-bottom:10px;">'
        f'{html.escape(article.get("subtitle", ""))}</div>'
        f'<p style="margin-bottom:10px;line-height:1.65;">{html.escape(article.get("body", ""))}</p>'
        f'<div style="background:{PALETTE["bg_tertiary"]};padding:8px 12px;border-radius:6px;'
        f'font-size:12px;display:flex;gap:8px;align-items:center;">'
        f'<span style="font-weight:600;color:{PALETTE["text_secondary"]};">Diligence Impact:</span>'
        f'<span>{html.escape(article.get("impact", ""))}</span>'
        f'</div></div>'
    )


def render_news(category: str = "all") -> str:
    """Render the SeekingChartis news page."""
    # Category filter tabs
    tabs = []
    for label, cat in _NEWS_CATEGORIES:
        active = ' style="color:var(--cad-accent);border-bottom:2px solid var(--cad-accent);"' if cat == category else ""
        tabs.append(
            f'<a href="/news?cat={cat}" '
            f'style="padding:8px 16px;text-decoration:none;color:{PALETTE["text_secondary"]};'
            f'font-size:13px;font-weight:500;"{active}>{html.escape(label)}</a>'
        )
    tab_bar = (
        f'<div style="display:flex;gap:4px;border-bottom:1px solid {PALETTE["border"]};'
        f'margin-bottom:20px;">{"".join(tabs)}</div>'
    )

    # Filter articles
    if category == "all":
        articles = _CURATED_ARTICLES
    else:
        articles = [a for a in _CURATED_ARTICLES if a.get("category") == category]

    cards = "".join(_article_card(a) for a in articles)

    if not cards:
        cards = (
            f'<div class="cad-card"><p style="color:{PALETTE["text_muted"]};">'
            f'No articles in this category yet.</p></div>'
        )

    # Sidebar: market snapshot
    sidebar = (
        f'<div class="cad-card">'
        f'<h2>Market Snapshot</h2>'
        f'<div style="font-size:12px;line-height:2;">'
        f'<div style="display:flex;justify-content:space-between;">'
        f'<span style="color:{PALETTE["text_secondary"]};">Hospital EV/EBITDA</span>'
        f'<span class="cad-mono">10.8x</span></div>'
        f'<div style="display:flex;justify-content:space-between;">'
        f'<span style="color:{PALETTE["text_secondary"]};">10Y Treasury</span>'
        f'<span class="cad-mono">4.31%</span></div>'
        f'<div style="display:flex;justify-content:space-between;">'
        f'<span style="color:{PALETTE["text_secondary"]};">S&P Healthcare</span>'
        f'<span class="cad-mono" style="color:{PALETTE["positive"]};">+0.18%</span></div>'
        f'<div style="display:flex;justify-content:space-between;">'
        f'<span style="color:{PALETTE["text_secondary"]};">HCA Healthcare</span>'
        f'<span class="cad-mono" style="color:{PALETTE["positive"]};">$284.50</span></div>'
        f'<div style="display:flex;justify-content:space-between;">'
        f'<span style="color:{PALETTE["text_secondary"]};">Tenet Healthcare</span>'
        f'<span class="cad-mono" style="color:{PALETTE["negative"]};">$112.30</span></div>'
        f'</div></div>'
        f'<div class="cad-card">'
        f'<h2>Key Dates</h2>'
        f'<div style="font-size:12px;line-height:2;">'
        f'<div><span style="color:{PALETTE["warning"]};">Apr 30</span> — CMS IPPS Proposed Rule</div>'
        f'<div><span style="color:{PALETTE["text_secondary"]};">May 15</span> — Q1 Earnings Season Ends</div>'
        f'<div><span style="color:{PALETTE["text_secondary"]};">Jun 1</span> — Medicaid DSH Reduction Deadline</div>'
        f'<div><span style="color:{PALETTE["text_secondary"]};">Aug 1</span> — CMS IPPS Final Rule</div>'
        f'</div></div>'
        f'<div class="cad-card" style="text-align:center;">'
        f'<a href="/conferences" style="color:var(--cad-link);text-decoration:none;'
        f'font-size:13px;font-weight:500;">'
        f'&#128197; Full Conference Roadmap &rarr;</a></div>'
    )

    body = (
        f'{tab_bar}'
        f'<div style="display:grid;grid-template-columns:1fr 300px;gap:20px;">'
        f'<div>{cards}</div>'
        f'<div>{sidebar}</div>'
        f'</div>'
    )

    return chartis_shell(
        body, "News & Research",
        active_nav="/news",
        subtitle="Healthcare PE market intelligence",
    )
