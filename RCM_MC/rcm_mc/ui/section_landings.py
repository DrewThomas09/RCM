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
                 {"href": "/new-deal", "label": "New Deal",
                  "blurb": "Add a target by hand, or import a batch."},
                 {"href": "/watchlist", "label": "Watchlist",
                  "blurb": "The targets you're keeping an eye on."},
             ]},
            # The old "Score & prioritize" pillar (Deal Quality,
            # Deal-Flow Heatmap, Deal Risk) ran entirely on the
            # illustrative seed corpus and is registry-hidden. What
            # replaces it is the workflow that keeps a tracked deal
            # current — no scoring model, just what changed and what you
            # wrote down.
            {"title": "Keep it current", "eyebrow": "WATCH THE TARGETS",
             "body": "What moved on a tracked target, and what you noted.",
             "links": [
                 {"href": "/alerts", "label": "Alerts",
                  "blurb": "What changed on a tracked target."},
                 {"href": "/notes", "label": "Notes",
                  "blurb": "Search every note written against a deal."},
                 {"href": "/diligence/xray", "label": "CMS X-Ray",
                  "blurb": "Resolve a tracked target across every CMS "
                  "vertical it appears in."},
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
                 {"href": "/methodology/calculations", "label": "Calculations",
                  "blurb": "The formula behind each derived metric."},
                 {"href": "/benchmark-reference", "label": "Benchmark Reference",
                  "blurb": "Where each benchmark band comes from."},
                 {"href": "/rcm-benchmarks", "label": "RCM Benchmarks",
                  "blurb": "RCM performance bands by segment."},
                 {"href": "/market-data/map", "label": "Market-Data Map",
                  "blurb": "Geographic coverage of the public data."},
             ]},
            # The identity layer under every provider surface. These are
            # download endpoints rather than pages, but they are the
            # files a reader would want in order to check the mapping
            # themselves — which is the point of this section — and no
            # catalog offered them before.
            {"title": "Provider identity files", "eyebrow": "THE CROSSWALKS",
             "body": "The mapping files behind every facility, system and "
             "NPI on the platform, as CSV.",
             "links": [
                 {"href": "/provider-crosswalk.csv", "label": "Provider Crosswalk",
                  "blurb": "One row per CCN with system, county FIPS, CBSA, "
                  "taxonomy, geocode and NPI — each beside its source."},
                 {"href": "/master-npi-file.csv", "label": "Master NPI File",
                  "blurb": "One row per NPI: identity, status history, "
                  "taxonomy, geography, billing CCN and resolved parent."},
                 {"href": "/npi-registry.csv", "label": "Organization NPI Registry",
                  "blurb": "Organization NPIs from the bundled NPPES "
                  "extracts with d/b/a names, PECOS group and taxonomy."},
                 {"href": "/health-system-lookup.csv", "label": "System Mapping",
                  "blurb": "Filter-aware hospital-to-system mapping, one "
                  "row per facility keyed on CCN."},
                 {"href": "/ownership-clusters.csv", "label": "Ownership Clusters",
                  "blurb": "Facilities grouped by common ownership filing."},
                 {"href": "/discovered-operators.csv", "label": "Discovered Operators",
                  "blurb": "Multi-facility operators the system registry "
                  "does not carry, found by grouping unmapped facilities."},
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
        "eyebrow": "PROVIDER UNIVERSES & CONTEXT",
        "explainer_head": "Every CMS provider universe, already loaded.",
        "explainer_body": "Read a whole Medicare program nationally — every "
        "certified nursing home, home-health agency, hospice, dialysis "
        "facility, rehab and long-term-care hospital — then the "
        "reimbursement and regulatory backdrop that moves those numbers "
        "from one cycle to the next.",
        "intro_headline": "A large Medicare dataset, readable in seconds.",
        "intro_italic": "seconds",
        "intro_body": "The provider-universe reads, plus what CMS is paying "
        "and what is on the rule calendar around them.",
        "next": {"label": "Check where a figure came from", "href": "/best/library", "italic": "where"},
        # The "Chart it" and "Compare & cross-cut" pillars that used to
        # open this section were the graphics toolkit and the two
        # build-your-own explorers (Cross-Dataset Analysis, Further
        # Analysis). All are registry-hidden: they start empty and draw
        # whatever the reader configures, which is a chart tool rather
        # than a read of a filing. The universes themselves now lead.
        "pillars": [
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
                 {"href": "/inpatient-rehab", "label": "Inpatient Rehab",
                  "blurb": "CMS measures for the IRF universe."},
                 {"href": "/long-term-care-hospital", "label": "Long-Term Care Hospitals",
                  "blurb": "CMS measures for the LTCH universe."},
             ]},
            # "Market Intel", its geographic and public-market cuts, and
            # Industry Intelligence all came out of hand-edited YAML or
            # licensed third-party reports rather than a CMS file, and
            # are registry-hidden. What is left here traces to a rule or
            # a published CMS figure.
            {"title": "Reimbursement & regulation", "eyebrow": "WHAT MOVES THE NUMBERS",
             "body": "What CMS is paying this cycle, and what is coming.",
             "links": [
                 {"href": "/rate-environment", "label": "Rate Environment",
                  "blurb": "Setting-level CMS payment updates (IPPS, OPPS, "
                  "PFS, ASC, SNF, HH, Hospice, IRF, ESRD) across three "
                  "rule cycles."},
                 {"href": "/regulatory-calendar", "label": "Regulatory Calendar",
                  "blurb": "CMS rule cycles + rate events."},
                 {"href": "/market-scan", "label": "Market Scan",
                  "blurb": "One state or county in, a public-data brief "
                  "out — demand, supply, spend and shortage."},
                 {"href": "/notes", "label": "Notes",
                  "blurb": "Your research notes."},
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
