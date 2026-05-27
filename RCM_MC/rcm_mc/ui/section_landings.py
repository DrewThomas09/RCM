"""Curated grouped catalogs for every section — the /diligence pattern,
replicated for Source, Pipeline, Library, Research, and Portfolio.

Each section's surfaces are grouped into a few named pillars with a one-line
job per tool; the shared renderer (section_catalog_page.render_grouped_catalog)
adds the honesty dot (live / computed / illustrative) to every row. This is the
landing that the nav's "All <section> tools" opens, replacing the old ranked
/best list — ranking now only informs ordering, the catalog is the surface.

Diligence keeps its own richer pillars (diligence_index_page); this module
covers the other five. A section with no curated pillars falls back to a single
auto-built "All tools" pillar from the ranking manifest so nothing 500s.
"""
from __future__ import annotations

from typing import Dict, List, Mapping, Optional

# section → page metadata + pillars. Each pillar: title, eyebrow, body, links
# [{href, label, blurb}]. Routes are real; the dot is derived per-route.
_SECTIONS: Dict[str, Dict] = {
    "source": {
        "title": "Source",
        "eyebrow": "TARGET DISCOVERY",
        "explainer_head": "The sourcing workspace at a glance.",
        "explainer_body": "Find acquisition targets across every public "
        "CMS/provider universe, then read the geography before you commit "
        "diligence effort. Start here when you don't yet know which screen "
        "you need.",
        "intro_headline": "Find the target before you spend on diligence.",
        "intro_italic": "Find",
        "intro_body": "Screeners over real CMS/HCRIS universes, plus the "
        "geographic intelligence to decide where to hunt.",
        "next": {"label": "Move a promising target into the Pipeline", "href": "/best/pipeline", "italic": "Pipeline"},
        "pillars": [
            {"title": "Screen for targets", "eyebrow": "SCREEN THE UNIVERSE",
             "body": "Filter real provider universes down to a short list.",
             "links": [
                 {"href": "/target-screener", "label": "Target Screener",
                  "blurb": "Filter every CMS provider universe by map, score, "
                  "and just-missed scan."},
                 {"href": "/screen", "label": "Hospital Screener",
                  "blurb": "Quick HCRIS filter on size, margin, and mix."},
                 {"href": "/predictive-screener", "label": "Predictive Screener",
                  "blurb": "Model-ranked acquisition leads."},
                 {"href": "/deal-screening", "label": "Thesis Screening",
                  "blurb": "Score targets against a named investment thesis."},
                 {"href": "/source", "label": "Deal Sourcing",
                  "blurb": "Origination workspace — promote a target to pipeline."},
             ]},
            {"title": "Geographic intelligence", "eyebrow": "WHERE TO HUNT",
             "body": "Read the market geography behind the targets — all real "
             "public data.",
             "links": [
                 {"href": "/geo-intel", "label": "Geographic Intelligence",
                  "blurb": "State-level provider + demographic hub."},
                 {"href": "/state-compare", "label": "State Comparison",
                  "blurb": "Compare states across real public metrics."},
                 {"href": "/state-rankings", "label": "State Rankings",
                  "blurb": "Rank every state on one metric."},
                 {"href": "/state-profile", "label": "State Profile",
                  "blurb": "One state's metrics + national ranks."},
                 {"href": "/state-peers", "label": "Similar States",
                  "blurb": "States most like a chosen one."},
                 {"href": "/county-explorer", "label": "County Explorer",
                  "blurb": "Drill into a state's counties (real ACS data)."},
                 {"href": "/metro-markets", "label": "Metro Markets",
                  "blurb": "Real CBSA/metro demographics (Census ACS)."},
                 {"href": "/geo-map", "label": "Geo Map",
                  "blurb": "US choropleth of any real state metric."},
                 {"href": "/geo-metrics", "label": "Geo Metrics & Sources",
                  "blurb": "What every geo metric measures + coverage."},
             ]},
            {"title": "Origination", "eyebrow": "FILL THE FUNNEL",
             "body": "Where the next opportunities come from.",
             "links": [
                 {"href": "/conferences", "label": "Conferences",
                  "blurb": "Healthcare-PE conference calendar + target lists."},
             ]},
        ],
    },
    "pipeline": {
        "title": "Pipeline",
        "eyebrow": "LIVE DEALS",
        "explainer_head": "The live-deal workspace at a glance.",
        "explainer_body": "Track real opportunities once they're promoted from "
        "Source — stage them toward IC, and rank the funnel by quality and risk.",
        "intro_headline": "Move real deals toward IC.",
        "intro_italic": "real",
        "intro_body": "The opportunities you're actively working, with the "
        "scoring to prioritize them.",
        "next": {"label": "Take a live deal into the Diligence playbook", "href": "/diligence", "italic": "Diligence"},
        "pillars": [
            {"title": "Build the pipeline", "eyebrow": "TRACK LIVE DEALS",
             "body": "Every opportunity you're working, staged toward IC.",
             "links": [
                 {"href": "/pipeline", "label": "Deal Pipeline",
                  "blurb": "Every live opportunity, staged toward IC."},
                 {"href": "/new-deal/manual", "label": "New Deal",
                  "blurb": "Create a deal by hand."},
                 {"href": "/pipeline/bridge", "label": "EBITDA Bridge",
                  "blurb": "Entry → exit value bridge per deal."},
             ]},
            {"title": "Score & prioritize", "eyebrow": "RANK THE FUNNEL",
             "body": "Decide what to spend diligence effort on next.",
             "links": [
                 {"href": "/deal-quality", "label": "Deal Quality",
                  "blurb": "Composite quality score per deal."},
                 {"href": "/deal-flow-heatmap", "label": "Deal-Flow Heatmap",
                  "blurb": "Where deal flow is concentrating."},
                 {"href": "/deal-risk-scores", "label": "Deal Risk",
                  "blurb": "Risk flags per opportunity."},
             ]},
        ],
    },
    "library": {
        "title": "Library",
        "eyebrow": "REFERENCE",
        "explainer_head": "The reference shelf at a glance.",
        "explainer_body": "Benchmarks, the historical deal corpus, and the data "
        "+ methodology behind every number on the platform. Open this when you "
        "need 'what does good look like' or 'where does this figure come from'.",
        "intro_headline": "What good looks like, and where the numbers come from.",
        "intro_italic": "where",
        "intro_body": "Benchmarks and comps, the deal corpus, and the data "
        "catalog + methodology that back the platform.",
        "next": {"label": "Apply these benchmarks in Diligence", "href": "/diligence", "italic": "Diligence"},
        "pillars": [
            {"title": "Benchmarks & comps", "eyebrow": "WHAT GOOD LOOKS LIKE",
             "body": "The bands and multiples you measure a target against.",
             "links": [
                 {"href": "/rcm-benchmarks", "label": "RCM Benchmarks",
                  "blurb": "RCM performance bands by segment."},
                 {"href": "/deal-library/comps", "label": "Comps",
                  "blurb": "Comparable transaction multiples."},
                 {"href": "/market-rates", "label": "Market Rates",
                  "blurb": "Base-rate MOIC distributions from the corpus."},
             ]},
            {"title": "Deal corpus", "eyebrow": "THE HISTORICAL RECORD",
             "body": "The licensed universe of sponsor-backed companies.",
             "links": [
                 {"href": "/deal-library", "label": "Deal Library",
                  "blurb": "Licensed sponsor-backed company universe."},
                 {"href": "/deal-library/sponsors", "label": "Sponsors",
                  "blurb": "Sponsor profiles + track records."},
                 {"href": "/library", "label": "Browse the Corpus",
                  "blurb": "Search the full deal corpus."},
             ]},
            {"title": "Data & methodology", "eyebrow": "HOW IT'S BUILT",
             "body": "Every dataset and the formulas behind the models.",
             "links": [
                 {"href": "/data", "label": "Data Catalog",
                  "blurb": "Every dataset + its refresh status."},
                 {"href": "/metric-glossary", "label": "Metric Glossary",
                  "blurb": "What each metric on the platform means."},
                 {"href": "/methodology", "label": "Methodology",
                  "blurb": "How the models and scores work."},
                 {"href": "/market-data/map", "label": "Market-Data Map",
                  "blurb": "Geographic coverage of the public data."},
             ]},
        ],
    },
    "research": {
        "title": "Research",
        "eyebrow": "MARKET & INDUSTRY",
        "explainer_head": "The research desk at a glance.",
        "explainer_body": "Read the market and the industry, learn from how "
        "comparable deals actually played out, backtest an edge, and frame the "
        "regulatory + thesis view — before you underwrite.",
        "intro_headline": "Read the market before you underwrite it.",
        "intro_italic": "before",
        "intro_body": "Market and industry intelligence, comparable outcomes, "
        "backtesting, and the regulatory + thesis frame.",
        "next": {"label": "Frame the thesis in the Diligence playbook", "href": "/diligence", "italic": "Diligence"},
        "pillars": [
            {"title": "Market & industry", "eyebrow": "READ THE MARKET",
             "body": "Demand, supply, reimbursement, and where multiples move.",
             "links": [
                 {"href": "/market-intel", "label": "Market Intel",
                  "blurb": "Demand, supply, reimbursement by market."},
                 {"href": "/market-intel/geo", "label": "Geographic Market Intel",
                  "blurb": "Market intel mapped to geography."},
                 {"href": "/industry", "label": "Industry Intelligence",
                  "blurb": "Derived facts from licensed industry reports."},
                 {"href": "/market-intel/seeking-alpha", "label": "Seeking Alpha",
                  "blurb": "Public-market signal on healthcare names."},
                 {"href": "/sector-momentum", "label": "Sector Momentum",
                  "blurb": "Where sector multiples are moving."},
             ]},
            {"title": "Comparables & outcomes", "eyebrow": "LEARN FROM THE RECORD",
             "body": "How similar deals actually played out.",
             "links": [
                 {"href": "/comparable-outcomes", "label": "Comparable Outcomes",
                  "blurb": "How similar deals actually played out."},
                 {"href": "/find-comps", "label": "Find Comps",
                  "blurb": "Find comparable deals by profile."},
                 {"href": "/payer-intelligence", "label": "Payer Intelligence",
                  "blurb": "Payer-mix benchmarks from the corpus."},
                 {"href": "/sponsor-track-record", "label": "Sponsor Track Record",
                  "blurb": "Realized returns by sponsor."},
             ]},
            {"title": "Backtesting & quant", "eyebrow": "TEST THE EDGE",
             "body": "Pressure-test a rule or signal against the corpus.",
             "links": [
                 {"href": "/backtest", "label": "Backtest",
                  "blurb": "Backtest a screening rule on the corpus."},
                 {"href": "/quant-lab", "label": "Quant Lab",
                  "blurb": "Build + test quantitative signals."},
                 {"href": "/deal-corpus-analytics", "label": "Corpus Analytics",
                  "blurb": "Corpus-wide return analytics."},
                 {"href": "/analysis", "label": "Analysis Workbench",
                  "blurb": "Per-deal analysis workbench."},
                 {"href": "/hold-analysis", "label": "Hold Analysis",
                  "blurb": "Hold-period return curves."},
                 {"href": "/irr-dispersion", "label": "IRR Dispersion",
                  "blurb": "IRR spread across the corpus."},
             ]},
            {"title": "Regulatory & thesis", "eyebrow": "FRAME THE VIEW",
             "body": "The rules, the risks, and the codified partner judgment.",
             "links": [
                 {"href": "/regulatory-calendar", "label": "Regulatory Calendar",
                  "blurb": "CMS rule cycles + rate events."},
                 {"href": "/bear-cases", "label": "Bear Cases",
                  "blurb": "Pattern library of how deals break."},
                 {"href": "/pe-intelligence", "label": "PE Intelligence",
                  "blurb": "The codified partner-judgment toolkit."},
                 {"href": "/notes", "label": "Notes",
                  "blurb": "Your research notes."},
             ]},
        ],
    },
    "portfolio": {
        "title": "Portfolio",
        "eyebrow": "PORTFOLIO OPS",
        "explainer_head": "The portfolio console at a glance.",
        "explainer_body": "Operate the book — health, alerts, covenants — and "
        "analyze what drives outcomes across every holding.",
        "intro_headline": "Run the book and find what drives it.",
        "intro_italic": "drives",
        "intro_body": "Monitoring and risk for every holding, plus the "
        "cross-portfolio analytics.",
        "next": {"label": "Source the next add-on acquisition", "href": "/best/source", "italic": "add-on"},
        "pillars": [
            {"title": "Operate the book", "eyebrow": "RUN THE PORTFOLIO",
             "body": "Daily portfolio operations.",
             "links": [
                 {"href": "/portfolio", "label": "Portfolio",
                  "blurb": "Every holding, health score, and alerts."},
                 {"href": "/portfolio/monitor", "label": "Monitor",
                  "blurb": "Live KPI + covenant monitoring."},
                 {"href": "/portfolio/risk-scan", "label": "Risk Scan",
                  "blurb": "Portfolio-wide risk flags."},
             ]},
            {"title": "Analyze", "eyebrow": "FIND THE SIGNAL",
             "body": "What actually drives outcomes across the book.",
             "links": [
                 {"href": "/portfolio/regression", "label": "Regression",
                  "blurb": "What drives outcomes across the book "
                  "(multicollinearity-checked)."},
             ]},
        ],
    },
}


def has_landing(section: str) -> bool:
    return section in _SECTIONS


def _auto_pillars(section: str) -> List[Mapping[str, object]]:
    """Fallback: one 'All tools' pillar built from the ranking manifest."""
    try:
        from ._surface_rankings import RANKINGS
        rows = sorted(RANKINGS.get(section, []),
                      key=lambda r: -r.get("total", 0.0))
    except Exception:  # noqa: BLE001
        rows = []
    links = [{"href": r["route"], "label": r.get("label", r["route"]),
              "blurb": ""} for r in rows]
    return [{"title": "All tools", "eyebrow": section.upper(),
             "body": "Every surface in this section, ordered best-first.",
             "links": links}]


def render_section_landing(section: str) -> Optional[str]:
    """Render a section's grouped catalog, or None if section is unknown and
    has no ranked surfaces to auto-build from."""
    from .section_catalog_page import render_grouped_catalog
    cfg = _SECTIONS.get(section)
    if cfg is None:
        pillars = _auto_pillars(section)
        if not pillars[0]["links"]:
            return None
        return render_grouped_catalog(
            section=section, title=section.title(), eyebrow=section.upper(),
            pillars=pillars, explainer_head=f"All {section} tools.",
            explainer_body="Every surface in this section.",
            explainer_source="Curated catalog.",
            intro_headline=f"Everything in {section}.", intro_body="")
    nxt = cfg.get("next", {})
    return render_grouped_catalog(
        section=section, title=cfg["title"], eyebrow=cfg["eyebrow"],
        pillars=cfg["pillars"], explainer_head=cfg["explainer_head"],
        explainer_body=cfg["explainer_body"],
        explainer_source="Curated catalog of this section's routes.",
        intro_headline=cfg["intro_headline"], intro_italic=cfg.get("intro_italic", ""),
        intro_body=cfg["intro_body"],
        next_label=nxt.get("label"), next_href=nxt.get("href"),
        next_italic=nxt.get("italic", ""),
        subtitle=f"{cfg['title']} · grouped catalog")
