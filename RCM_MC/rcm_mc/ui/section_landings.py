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
                  "blurb": "Origination workspace: promote a target to pipeline."},
             ]},
            {"title": "Geographic intelligence", "eyebrow": "WHERE TO HUNT",
             "body": "Read the market geography behind the targets, all real "
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
        ],
    },
    "pipeline": {
        "title": "Pipeline",
        "eyebrow": "LIVE DEALS",
        "explainer_head": "The tracked-deal workspace at a glance.",
        "explainer_body": "The transactions you're following, promoted from a "
        "Source screen or entered by hand — each one linkable to the CMS "
        "filings behind the target.",
        "intro_headline": "Track the deals, then read the filings.",
        "intro_italic": "filings",
        "intro_body": "The transactions you're following, and the bridge from "
        "a tracked target to its cost report.",
        "next": {"label": "Take a tracked target into the X-Rays", "href": "/diligence", "italic": "X-Rays"},
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
        "eyebrow": "THE DATASETS",
        "explainer_head": "Every public dataset, and where it came from.",
        "explainer_body": "The catalog of CMS, Medicare, Medicaid and hospital "
        "datasets loaded here — what each one covers, how current it is, and "
        "the filing or file it was read from. Open this to answer 'is this "
        "number real, and where does it come from'.",
        "intro_headline": "Every figure traces back to a public filing.",
        "intro_italic": "traces",
        "intro_body": "The dataset catalog and its refresh status, the source "
        "registry behind every metric, and the methodology for anything the "
        "platform computes rather than reads.",
        "next": {"label": "Chart one of these datasets", "href": "/best/research", "italic": "Chart"},
        "pillars": [
            {"title": "The dataset catalog", "eyebrow": "WHAT'S LOADED",
             "body": "Every public dataset on the platform, with coverage "
             "and refresh state.",
             "links": [
                 {"href": "/data", "label": "Data Catalog",
                  "blurb": "Every dataset + its refresh status."},
                 {"href": "/cms-data-browser", "label": "CMS Data Browser",
                  "blurb": "Browse the curated CMS datasets directly."},
                 {"href": "/cms-sources", "label": "CMS Sources",
                  "blurb": "Every CMS file the platform reads, by program."},
                 {"href": "/tools/open-data", "label": "Open Data",
                  "blurb": "The public open-data endpoints behind the loaders."},
                 {"href": "/data-apis", "label": "Public Data APIs",
                  "blurb": "Live API status for each upstream source."},
                 {"href": "/data-quality", "label": "Data Quality",
                  "blurb": "Coverage gaps and freshness per source."},
             ]},
            {"title": "Verify a number", "eyebrow": "TRACE IT BACK",
             "body": "What a metric means, how it was computed, and which "
             "filing it came from.",
             "links": [
                 {"href": "/metric-glossary", "label": "Metric Glossary",
                  "blurb": "What each metric on the platform means."},
                 {"href": "/methodology", "label": "Methodology",
                  "blurb": "How anything computed here is computed."},
                 {"href": "/benchmark-reference", "label": "Benchmark Reference",
                  "blurb": "Where each benchmark band comes from."},
                 {"href": "/rcm-benchmarks", "label": "RCM Benchmarks",
                  "blurb": "RCM performance bands by segment."},
                 {"href": "/market-data/map", "label": "Market-Data Map",
                  "blurb": "Geographic coverage of the public data."},
             ]},
            {"title": "Deal trackers", "eyebrow": "PUBLICLY REPORTED DEALS",
             "body": "Transactions as they were publicly reported — sourced, "
             "dated, and searchable.",
             "links": [
                 {"href": "/deal-library", "label": "Deal Library",
                  "blurb": "The tracked healthcare transaction universe."},
                 {"href": "/deal-library/sponsors", "label": "Sponsors",
                  "blurb": "Who acquired what, by acquirer."},
                 {"href": "/deal-library/comps", "label": "Comps",
                  "blurb": "Reported transaction multiples."},
                 {"href": "/verified-deals", "label": "Verified Deals",
                  "blurb": "Deals confirmed against a public source."},
                 {"href": "/news", "label": "Deal News",
                  "blurb": "Newly reported transactions as they land."},
                 {"href": "/library", "label": "Browse Everything",
                  "blurb": "Search the full tracked universe."},
             ]},
        ],
    },
    "research": {
        "title": "Research",
        "eyebrow": "VISUALIZE & COMPARE",
        "explainer_head": "Turn a public dataset into a picture.",
        "explainer_body": "Chart any loaded dataset, cut it by provider type, "
        "geography or payer, and put two sources side by side. This is where a "
        "large CMS file stops being a download and starts being something you "
        "can read.",
        "intro_headline": "A large Medicare dataset, charted in seconds.",
        "intro_italic": "seconds",
        "intro_body": "Chart builders and the provider-universe reads, plus "
        "the market and regulatory context around them.",
        "next": {"label": "Check where a figure came from", "href": "/best/library", "italic": "where"},
        "pillars": [
            {"title": "Chart it", "eyebrow": "BUILD THE VISUAL",
             "body": "Point a chart at a loaded dataset and read it.",
             "links": [
                 {"href": "/visuals", "label": "Visuals",
                  "blurb": "The chart gallery across every loaded dataset."},
                 {"href": "/chart-builder", "label": "Chart Builder",
                  "blurb": "Build a chart off any dataset column."},
                 {"href": "/geo-map", "label": "Geo Map",
                  "blurb": "US choropleth of any public state metric."},
                 {"href": "/charts", "label": "Saved Charts",
                  "blurb": "Charts you've built and kept."},
                 {"href": "/exhibit", "label": "Exhibit Composer",
                  "blurb": "Compose several charts into one exhibit."},
                 {"href": "/pie-chart", "label": "Pie Chart",
                  "blurb": "Quick share-of-total from a column."},
             ]},
            {"title": "Provider universes", "eyebrow": "READ ONE SECTOR",
             "body": "Every CMS provider type, already loaded and charted.",
             "links": [
                 {"href": "/verticals", "label": "All Verticals",
                  "blurb": "Every provider universe in one index."},
                 {"href": "/nursing-homes", "label": "Nursing Homes",
                  "blurb": "CMS Care Compare: the SNF universe."},
                 {"href": "/home-health", "label": "Home Health",
                  "blurb": "CMS Care Compare: home-health agencies."},
                 {"href": "/hospice", "label": "Hospice",
                  "blurb": "CMS Care Compare: hospice providers."},
                 {"href": "/dialysis", "label": "Dialysis",
                  "blurb": "CMS Care Compare: dialysis facilities."},
                 {"href": "/health-system-lookup", "label": "Health System Lookup",
                  "blurb": "Find a system and its member facilities."},
                 {"href": "/ma-penetration", "label": "MA Penetration",
                  "blurb": "Medicare Advantage share by county."},
             ]},
            {"title": "Compare & cross-cut", "eyebrow": "PUT TWO SOURCES TOGETHER",
             "body": "Join across datasets, or run one question over all "
             "of them.",
             "links": [
                 {"href": "/cross-analysis", "label": "Cross-Dataset Analysis",
                  "blurb": "Join two public datasets on a shared key."},
                 {"href": "/further-analysis", "label": "Further Analysis",
                  "blurb": "Follow-on cuts from any loaded dataset."},
                 {"href": "/quant-lab", "label": "Quant Lab",
                  "blurb": "Build and test a quantitative signal."},
                 {"href": "/analysis", "label": "Analysis Workbench",
                  "blurb": "The full workbench over a loaded packet."},
                 {"href": "/comparable-outcomes", "label": "Comparable Outcomes",
                  "blurb": "How comparable facilities actually performed."},
             ]},
            {"title": "Market & regulatory context", "eyebrow": "WHAT MOVES THE NUMBERS",
             "body": "The reimbursement and market backdrop behind a "
             "dataset's movement.",
             "links": [
                 {"href": "/market-intel", "label": "Market Intel",
                  "blurb": "Demand, supply, reimbursement by market."},
                 {"href": "/market-intel/geo", "label": "Geographic Market Intel",
                  "blurb": "Market intel mapped to geography."},
                 {"href": "/industry", "label": "Industry Intelligence",
                  "blurb": "Derived facts from licensed industry reports."},
                 {"href": "/market-intel/public-market", "label": "Public Market Intel",
                  "blurb": "Public-market signal on healthcare names."},
                 {"href": "/regulatory-calendar", "label": "Regulatory Calendar",
                  "blurb": "CMS rule cycles + rate events."},
                 {"href": "/notes", "label": "Notes",
                  "blurb": "Your research notes."},
             ]},
        ],
    },
    "portfolio": {
        "title": "Portfolio",
        "eyebrow": "PORTFOLIO OPS",
        "explainer_head": "The portfolio console at a glance.",
        "explainer_body": "Operate the book (health, alerts, covenants) and "
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
    """Fallback: one 'All tools' pillar built from the ranking manifest.

    curate_rows gates the manifest — without it this fallback leaked
    internal routes (login/forgot/demo/.xlsx artifacts in the
    'uncategorized' pool) as partner-facing tool cards.
    """
    from ._surface_visibility import curate_rows
    try:
        from ._surface_rankings import RANKINGS
        rows = curate_rows(sorted(RANKINGS.get(section, []),
                                  key=lambda r: -r.get("total", 0.0)))
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
