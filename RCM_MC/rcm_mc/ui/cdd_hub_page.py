"""Commercial Due Diligence hub — /cdd.

The desk had strong CDD ingredients (TAM/SAM builder, demand forecast,
geographic market, competitor intel, payer analytics) scattered across
four nav sections with nothing presenting them *as a CDD workflow*. An
associate staffed on a commercial sprint had to already know the
product to find the right page. This hub lays the canonical five-module
CDD structure over the existing surfaces — market, competition,
customers, pricing/reimbursement, deliverables — so the sprint has a
table of contents, with each module listing its surfaces in the order
the workstream actually runs.

Pure navigation page: every card links to an existing route (the two
customer-evidence surfaces and the rate tracker shipped in the same
wave as this hub). No data computed here.
"""
from __future__ import annotations

import html as _html

from rcm_mc.ui._chartis_kit import (
    chartis_shell, ck_page_explainer, ck_page_title,
)

# (module title, blurb, [(label, href, one-liner), ...])
_MODULES = [
    ("1 · Market size & growth",
     "How big is the market, and is the growth real or demographic "
     "wishful thinking?",
     [
         ("TAM / SAM / SOM Builder", "/diligence/tam-sam",
          "Driver-tree market sizing with sourced inputs and xlsx export"),
         ("Demand Forecaster", "/demand-forecast",
          "10-year volume projection by age band with payer-mix shift"),
         ("Growth Runway", "/growth-runway",
          "Penetration S-curves and comparable expansion precedents"),
         ("Geographic Market Analyzer", "/geo-market",
          "CBSA-level attractiveness scoring and market-entry tiers"),
     ]),
    ("2 · Competitive landscape",
     "Who else is in the market, how concentrated is it, and where does "
     "the target actually win?",
     [
         ("Competitive Intelligence", "/competitive-intel",
          "Share landscape, strategic moves, capability gap analysis"),
         ("Industry Intelligence", "/industry",
          "Sector deep dives: facility counts, chains, consolidation HHI"),
         ("Win/Loss Analyzer", "/win-loss",
          "Head-to-head conversion record and loss-reason decomposition"),
         ("Find Comps", "/find-comps",
          "Corpus comparables by numeric deal profile"),
     ]),
    ("3 · Customer evidence",
     "What do customers say — and does revenue stay when you stop "
     "asking nicely?",
     [
         ("Voice of Customer / Survey", "/voc-survey",
          "NPS by segment, KPC gap matrix, willingness-to-pay"),
         ("Payer Intelligence", "/payer-intelligence",
          "Payer-mix regimes vs realized MOIC across the corpus"),
         ("Direct-to-Employer Analyzer", "/direct-employer",
          "Employer-contract economics and concentration"),
         ("HCIT / SaaS Analyzer", "/hcit-platform",
          "ARR quality: NRR, gross margin, Rule of 40"),
     ]),
    ("4 · Pricing & reimbursement",
     "Who sets the price in this market — the target, the payer, or "
     "CMS?",
     [
         ("Medicare Rate Environment", "/rate-environment",
          "Setting-level CMS payment updates with blended dollar impact"),
         ("MA Penetration", "/ma-penetration",
          "State-level Medicare Advantage exposure with footprint scorer"),
         ("Market Rates", "/market-rates",
          "Negotiated-rate benchmarks"),
         ("Market Intel (Comps & News)", "/market-intel",
          "Public comps, transaction multiples, curated sector news"),
         ("Sector Momentum", "/sector-momentum",
          "Deal-activity acceleration by sector"),
     ]),
    ("5 · Deliverables",
     "Turn the work into the readout: models first, then the memo.",
     [
         ("Excel Model Templates", "/excel-templates",
          "Live-formula workbooks: market model, payer sensitivity, "
          "cohort/NRR, quick LBO"),
         ("IC Memo Generator", "/ic-memo-gen",
          "Investment-committee memo assembly"),
         ("QoE Memo", "/diligence/qoe-memo",
          "Quality-of-earnings memo from the diligence packet"),
         ("Thesis Screening", "/deal-screening",
          "Screen the thesis against the deal corpus"),
     ]),
]


def render_cdd_hub(params: dict = None) -> str:
    sections = []
    for title, blurb, links in _MODULES:
        cards = "".join(
            f'<a class="cdd-card" href="{_html.escape(href)}">'
            f'<div class="cdd-card-title">{_html.escape(label)}</div>'
            f'<div class="cdd-card-desc">{_html.escape(desc)}</div>'
            f'</a>'
            for label, href, desc in links)
        sections.append(
            f'<section class="cdd-module">'
            f'<h2 class="cdd-module-h">{_html.escape(title)}</h2>'
            f'<p class="cdd-module-blurb">{_html.escape(blurb)}</p>'
            f'<div class="cdd-grid">{cards}</div>'
            f'</section>')

    n_surfaces = sum(len(links) for _, _, links in _MODULES)
    page_title = ck_page_title(
        "Commercial Due Diligence Hub",
        eyebrow="DILIGENCE · CDD WORKFLOW",
        meta=(f"5 workstream modules · {n_surfaces} surfaces · market → "
              "competition → customers → pricing → deliverables"),
    )
    explainer = ck_page_explainer(
        "The commercial sprint, in running order.",
        "Every CDD engagement answers the same five questions in the same "
        "order. This hub maps the desk's surfaces onto that flow so an "
        "associate staffed on a commercial sprint starts here instead of "
        "trawling the nav: size the market, map the competition, test the "
        "customer evidence, pressure-test pricing and reimbursement, then "
        "assemble the deliverables.",
    )
    css = """
<style>
.cdd-module { margin: 26px 0; }
.cdd-module-h { font-size: 20px; margin: 0 0 4px; color: #0b2341; }
.cdd-module-blurb { margin: 0 0 12px; color: #4a5568; font-style: italic; max-width: 72ch; }
.cdd-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 12px; }
.cdd-card { display: block; background: #fffdf9; border: 1px solid #d8d2c4;
            border-radius: 6px; padding: 14px 16px; text-decoration: none; }
.cdd-card:hover { border-color: #155752; }
.cdd-card-title { font-weight: 600; font-size: 14.5px; color: #155752; margin-bottom: 5px; }
.cdd-card-desc { font-size: 12.5px; line-height: 1.4; color: #1a2332; }
</style>"""
    body = f"""
<div class="ck-page-wrap">
  {page_title}
  {explainer}
  {''.join(sections)}
</div>"""
    return chartis_shell(body, title="CDD Hub", active_nav="/cdd",
                         extra_css=css)
