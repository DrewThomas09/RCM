"""Surface-visibility registry — the single ruling on what partners see.

The ranking manifest (``_surface_rankings.RANKINGS``, auto-generated) scores
every route-backed page, but a score is not a visibility decision. This
module is the hand-curated layer that says what may appear where. Five
visibility ranks, best-first:

  1. **Flagship** — leads a topbar mega-menu (``_chartis_kit._NAV_FLAGSHIPS``).
  2. **Catalog** — listed in /tools and the /best/<section> catalogs.
  3. **Utility** — real page, but a tool rather than an analysis
     (``_chartis_kit._NAV_DEMOTED``): never in a bar, still in catalogs
     and the Cmd-K palette.
  4. **Internal** — never rendered as a partner-facing destination card
     (``INTERNAL_ROUTES`` below): auth, admin, debug/status, and file
     -download artifacts that the route scanner mis-ranks as pages. They
     remain reachable directly (and admin pages keep their user-menu
     links); they just never read as "a tool we're proud of".
  5. **Hidden** — off every listing surface (``HIDDEN_ROUTES`` +
     ``HIDDEN_PREFIXES`` below): pages whose figures are illustrative
     rather than sourced, single-target/single-market study suites, and
     the sponsor-corpus/PE-narrative long tail. The routes still resolve
     — nothing is deleted, deep links and in-page links keep working —
     they are simply never *offered* anywhere a reader browses.

The product this registry serves is a **public-data verification and
visualization surface**: load a public CMS / Medicare / Medicaid /
hospital dataset, see it charted in seconds, and trace every figure back
to its filing. A page that shows made-up numbers, or that only makes
sense inside one 2026 deal, actively works against that promise even when
it renders beautifully — so it goes Hidden, not Catalog.

``curate_rows`` applies the catalog-level rules to a ranked row list and is
shared by every generic listing renderer (/tools showcase, the auto-built
section catalogs, the ranked /best fallback) so the ruling can't drift
per-surface. ``visible_links`` / ``visible_modules`` do the same job for
the hand-curated catalogs (section pillars, the Cmd-K palette).
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence

# Routes that must never render as partner-facing destination cards.
# Keep this tight and defensible — everything here is either not a page
# (file downloads), not for partners (auth/admin plumbing), or a debug
# surface (build-status, CLI run log).
INTERNAL_ROUTES = frozenset({
    "/login",       # auth plumbing — partners arrive here, never browse to it
    "/forgot",      # auth plumbing
    "/demo",        # seeded demo launcher, not a partner destination
    "/users",       # admin — linked from the user-menu "Admin" item instead
    "/cli-runs",    # CLI run log, debug surface
})


def is_internal(route: str) -> bool:
    """True when a route must not render as a partner-facing card.

    ``.xlsx`` routes are workbook downloads the route scanner picks up as
    pages — clicking a "tool" that downloads a file is a broken browse, so
    the whole class is internal rather than enumerating each artifact.
    """
    route = (route or "").strip()
    return route in INTERNAL_ROUTES or route.endswith(".xlsx")


# ---------------------------------------------------------------------------
# Hidden surfaces — listed nowhere, deleted nowhere
# ---------------------------------------------------------------------------
#
# Three rationales, kept as separate sets so a route's reason for being
# hidden stays legible (and so a page that later earns real wiring is
# removed from exactly one place).

# 1) ILLUSTRATIVE — the figures on the page come from hardcoded dataclass
#    lists, not from a filing. Every one of these renders the
#    ck_illustrative_note strip ("Illustrative template — not this
#    portfolio's live, sourced data"); derived by scanning rendered output
#    for `class="ck-illus-note"`. A verification product cannot offer a
#    page of invented numbers as a destination, however honest its label.
#    Drop a route from this set the day its live-data wiring lands.
_ILLUSTRATIVE_ROUTES = frozenset({
    "/aco-economics", "/acq-timing", "/ai-operating-model", "/antitrust-screener",
    "/backtest", "/backtester", "/base-rates", "/biosimilars",
    "/board-governance", "/bolton-analyzer", "/cap-structure", "/capex-budget",
    "/capital-call", "/capital-efficiency", "/capital-pacing", "/capital-schedule",
    "/cin-analyzer", "/clinical-ai", "/clinical-outcomes", "/cms-apm",
    "/coinvest-pipeline", "/comparables", "/competitive-intel",
    "/compliance-attestation", "/concentration-risk", "/continuation-vehicle",
    "/corpus-coverage", "/corpus-dashboard", "/corpus-ic-memo",
    "/covenant-headroom", "/covenant-monitor", "/cyber-risk",
    "/deal-flow-heatmap", "/deal-origination", "/deal-pipeline",
    "/deal-postmortem", "/deal-quality", "/deal-risk-scores", "/deal-search",
    "/deal-sourcing", "/debt-financing", "/debt-service", "/demand-forecast",
    "/denovo-expansion", "/digital-front-door", "/diligence-vendors",
    "/diligence/cliff-calendar", "/diligence/pe-library",
    "/diligence/pe-reference", "/diligence/physician-attrition",
    "/direct-employer", "/direct-lending", "/dividend-recap", "/dpi-tracker",
    "/drug-pricing-340b", "/drug-shortage", "/earnout", "/entry-multiple",
    "/escrow-earnout", "/esg-dashboard", "/esg-impact", "/exit-multiple",
    "/exit-readiness", "/exit-timing", "/find-comps", "/fraud-detection",
    "/fund-attribution", "/fundraising", "/geo-market", "/gp-benchmarking",
    "/gpo-supply", "/growth-runway", "/hcit-platform", "/health-equity",
    "/hold-analysis", "/hold-optimizer", "/hospital-anchor", "/ic-memo-gen",
    "/insurance-tracker", "/irr-dispersion", "/key-person", "/lbo-stress",
    "/leverage-intel", "/litigation", "/locum-tracker", "/lp-dashboard",
    "/lp-reporting", "/ma-contracts", "/ma-star", "/market-rates",
    "/medicaid-unwinding", "/medical-realestate", "/mgmt-comp",
    "/mgmt-fee-tracker", "/msa-concentration", "/multiple-decomp",
    "/nav-loan-tracker", "/nsa-tracker", "/operating-partners",
    "/partner-economics", "/patient-experience", "/payer-concentration",
    "/payer-contracts", "/payer-intel", "/payer-intelligence",
    "/payer-rate-trends", "/payer-shift", "/peer-transactions",
    "/peer-valuation", "/phys-comp-plan", "/physician-labor",
    "/physician-productivity", "/platform-maturity", "/pmi-integration",
    "/pmi-playbook", "/portfolio-optimizer", "/portfolio-sim",
    "/pricing-power", "/provider-network", "/provider-retention",
    "/qoe-analyzer", "/quality-scorecard", "/rcm-red-flags", "/real-estate",
    "/redflag-scanner", "/ref-pricing", "/refi-optimizer", "/regulatory-risk",
    "/reinvestment", "/reit-analyzer", "/return-attribution",
    "/revenue-leakage", "/risk-adjustment", "/risk-matrix",
    "/rollup-economics", "/rw-insurance", "/scenario-mc",
    "/secondaries-tracker", "/sector-correlation", "/sector-intel",
    "/sector-momentum", "/sellside-process", "/size-intel",
    "/specialty-benchmarks", "/sponsor-heatmap", "/sponsor-league",
    "/sponsor-track-record", "/supply-chain", "/tax-credits", "/tax-structure",
    "/tax-structure-analyzer", "/tech-stack", "/telehealth-econ",
    "/tracker-340b", "/transition-services", "/treasury", "/trial-site-econ",
    "/underwriting", "/underwriting-model", "/unit-economics",
    "/value-creation", "/value-creation-plan", "/vcp-tracker", "/vdr-tracker",
    "/vintage-cohorts", "/vintage-perf", "/voc-survey", "/win-loss",
    "/workforce-planning", "/workforce-retention", "/working-capital",
    "/zbb-tracker",
})

# 2) SINGLE-STUDY suites — real work, but scoped to one operator or one
#    metro in one engagement (the Texas infusion market scan; the IFT /
#    MMT interfacility-transport study). Browsing a national CMS dataset
#    and landing on "TX Infusion · J-code Bench" reads as a stray page,
#    because for every reader who is not on that deal it is one. Whole
#    families go together — see HIDDEN_PREFIXES for the sub-routes.
_SINGLE_STUDY_ROUTES = frozenset({
    "/diligence/texas-infusion",
    "/diligence/texas-infusion-continued",
    "/diligence/infusion-markets",
    "/diligence/jcode-atlas",
    "/diligence/tam-sam",
    "/ift",
    "/in-depth-ift-bls-als1-als2-cct",
})

# 3) SPONSOR-CORPUS / PE-NARRATIVE long tail — pages built on the seeded
#    sponsor-deal corpus or on codified investor judgment rather than on a
#    public filing. They are the "investment platform" framing this product
#    is stepping away from. The deal TRACKERS stay visible (/deal-library,
#    /verified-deals, /news, /market-scan, /pipeline) — those track real,
#    publicly-reported transactions and are the good version of this idea.
_PE_NARRATIVE_ROUTES = frozenset({
    "/bear-cases",
    "/corpus-backtest",
    "/deal-corpus-analytics",
    "/deal-screening",
    "/diligence/bear-case",
    "/diligence/management",
    "/diligence/pe-tool",
    "/diligence/root-cause",
    "/diligence/thesis-pipeline",
    "/fund-learning",
    "/pe-intelligence",
    "/screening/bankruptcy-survivor",
    "/sector-intelligence",
})

HIDDEN_ROUTES = (
    _ILLUSTRATIVE_ROUTES | _SINGLE_STUDY_ROUTES | _PE_NARRATIVE_ROUTES
)

# Route families where every sub-route is hidden with its parent. A prefix
# matches the bare route and anything under it (``/ift`` covers ``/ift-mmt``
# and ``/ift/x``; it does NOT cover an unrelated ``/iftar``).
HIDDEN_PREFIXES: tuple[str, ...] = (
    "/diligence/texas-infusion",
    "/ift",
)


def is_hidden(route: str) -> bool:
    """True when ``route`` must not be OFFERED on any listing surface.

    Hidden is a browse-time ruling, not a routing one: the handler still
    serves the page and a direct link still works. Query strings and
    trailing slashes are normalized so ``/diligence/risk-workbench?demo=x``
    and ``/ift/`` resolve the same as their bare routes.

    A hidden route hides its own sub-paths too: ``/competitive-intel`` is
    an illustrative surface, so its per-facility view
    ``/competitive-intel/<ccn>`` is the same page with a parameter and is
    hidden with it. (No visible route sits under a hidden one — pinned by
    ``tests/test_hidden_surfaces.py``.)
    """
    route = (route or "").strip().split("?", 1)[0].split("#", 1)[0]
    if not route:
        return False
    norm = route.rstrip("/") or route
    if norm in HIDDEN_ROUTES:
        return True
    if any(norm.startswith(h + "/") for h in HIDDEN_ROUTES):
        return True
    # Family prefixes additionally catch sibling slugs: ``/ift`` covers
    # ``/ift-mmt`` as well as ``/ift/x``.
    return any(
        norm == p or norm.startswith(p + "/") or norm.startswith(p + "-")
        for p in HIDDEN_PREFIXES
    )


def is_visible(route: str) -> bool:
    """True when ``route`` may be offered as a partner-facing destination."""
    return not is_internal(route) and not is_hidden(route)


def visible_links(links: Iterable[Mapping]) -> list:
    """Filter a hand-curated link list (dicts carrying ``href``).

    Used by the section pillars and every other catalog that enumerates
    destinations by hand, so a curated rail can't quietly reintroduce a
    surface the registry has ruled out.
    """
    return [link for link in links if is_visible(str(link.get("href") or ""))]


def visible_modules(modules: Sequence[Mapping]) -> list:
    """Filter a Cmd-K palette module list (dicts carrying ``route``).

    The palette is a listing surface like any other: a reader who types
    "infusion" should not be handed a one-metro study as the answer.
    """
    return [m for m in modules if is_visible(str(m.get("route") or ""))]


def curate_rows(rows: Iterable[dict]) -> list[dict]:
    """Filter a ranked row list (dicts with 'route' + 'label') down to what
    a partner-facing catalog may show. Rows must arrive best-first; the
    first occurrence of a destination wins.

    Drops, in order of why:
      * internal routes (see ``is_internal``),
      * hidden routes (see ``is_hidden``) — illustrative-figure pages,
        single-study suites, and the sponsor-corpus long tail,
      * sentinel rows ("All X →" labels — they duplicate the catalog's own
        section link and aren't real leaves),
      * alias duplicates of the same page, by normalized route
        (``/diligence/`` vs ``/diligence``) and by label
        (``/deal-pipeline`` vs ``/pipeline`` both render "Deal Pipeline" —
        a catalog showing the same destination twice reads as a bug).
    """
    out: list[dict] = []
    seen_routes: set = set()
    seen_labels: set = set()
    for r in rows:
        route = str(r.get("route") or "").strip()
        label = str(r.get("label") or "").strip()
        norm = route.rstrip("/") or route
        if not route or norm in seen_routes or label.lower() in seen_labels:
            continue
        # Record the route BEFORE the drop checks so an alias of a dropped
        # row drops with it (`/diligence/` must not survive just because
        # `/diligence` was removed as a sentinel first).
        seen_routes.add(norm)
        if not is_visible(route) or "→" in label:
            continue
        if label:
            seen_labels.add(label.lower())
        out.append(r)
    return out
