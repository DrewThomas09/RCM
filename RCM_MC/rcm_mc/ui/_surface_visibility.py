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
     ``HIDDEN_PREFIXES`` below): illustrative-figure pages,
     single-target/single-sector study suites, the sponsor-corpus/
     PE-narrative long tail, the deal-EXECUTION machinery, the bloat
     that is simply unrelated to what this product does, and the
     duplicate data catalogs. The routes still resolve — nothing is
     deleted, deep links and in-page links keep working — they are
     simply never *offered* anywhere a reader browses.

The product this registry serves does **three** things well, and the
rulings below all come down to whether a page is one of them:

  1. **Display information about providers** — hospitals, health systems,
     and the other outpatient services (SNF, home health, hospice,
     dialysis, IRF, LTCH). The X-RAYS are the centre of gravity: when a
     call is close, favour the filing.
  2. **Scan that universe** — the screeners and lookups that find a
     facility, a system, or a market inside it.
  3. **Track deals in the space** — who acquired what, publicly reported
     and traceable to a source.

A page that shows made-up numbers, that only makes sense inside one 2026
transaction, that is an artifact of *doing* a deal rather than tracking
one, or that is none of the three above, works against that promise even
when it renders beautifully — so it goes Hidden, not Catalog.

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
    # ── Deployment plumbing ────────────────────────────────────────
    # These are operator surfaces for the person running the install,
    # not analytic destinations. Internal rather than Hidden because
    # they are genuinely wanted — from the user menu and the admin
    # nav — just never carded in a catalog as "a tool we're proud of".
    "/jobs",                 # background job queue status
    "/runs",                 # simulation run history
    "/audit",                # audit trail review
    "/admin/audit-chain",    # tamper-evident audit chain
    "/admin/data-sources",   # ingestion health for the operator
    "/ops",                  # deployment/system status
    "/team",                 # members, ownership, activity
    "/guide/context-debug",  # debug view of the Guide's own context packet
    # Preferences. Reached from the user menu; enumerated one by one
    # because is_internal matches exactly (no prefix semantics).
    "/settings",
    "/settings/ai",
    "/settings/workspace",
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
# Seven rationales, kept as separate sets so a route's reason for being
# hidden stays legible (and so a page that later earns real wiring is
# removed from exactly one place). Numbered comments below mark each.

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

# 2) SINGLE-STUDY suites — real work, but scoped to one operator, one
#    metro, or one narrow sector in one engagement (the Texas infusion
#    market scan; the IFT / MMT interfacility-transport study; the
#    radiology/imaging atlas, which is organized around named
#    sponsor-backed operators). Browsing a national CMS dataset and
#    landing on "TX Infusion · J-code Bench" reads as a stray page,
#    because for every reader who is not on that deal it is one.
#
#    The line between this and a KEEPER is sector *breadth*, not subject
#    matter: /nursing-homes, /home-health, /hospice, /dialysis,
#    /inpatient-rehab and /long-term-care-hospital stay visible because
#    each reads a whole CMS program's Care Compare universe nationally —
#    that IS the CMS aggregation this product is for. Infusion, IFT and
#    imaging are bespoke deal-thesis studies wearing the same clothes.
#
#    ``/market`` and its ~80 ``/market/<sector>`` reports go too: they are
#    sector M&A narrative (who's rolling up what) rather than a read of a
#    public filing, and the family includes the infusion and
#    interfacility-transport writeups by name.
#
#    Whole families go together — see HIDDEN_PREFIXES for the sub-routes.
_SINGLE_STUDY_ROUTES = frozenset({
    "/diligence/texas-infusion",
    "/diligence/texas-infusion-continued",
    "/diligence/infusion-markets",
    "/diligence/jcode-atlas",
    "/diligence/tam-sam",
    "/ift",
    "/in-depth-ift-bls-als1-als2-cct",
    "/radiology-imaging",
    "/market",
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

# 4) DEAL EXECUTION — the machinery for *running* a deal, as distinct from
#    *tracking* one. The product is healthcare-PE deal tracking plus CMS
#    data aggregation; that sentence has a seam in it, and this set is
#    everything on the far side of it.
#
#    TRACKING (stays visible): who bought what, when, for how much, and
#    what the filings say about them — /deal-library + sponsors + comps,
#    /verified-deals, /news, /market-scan, /pipeline, /portfolio and its
#    map/heatmap/monitor/risk-scan/regression reads.
#
#    EXECUTION (hidden here): the artifacts of doing a transaction —
#    IC packets, QoE memos, CDD scoping and expert-call programs, CIM
#    cross-checks, counterfactuals, covenant stress, deal Monte Carlo,
#    autopsies, checklists and question ledgers, value plans, roll-up
#    models, LP reporting. None of it reads a CMS dataset; all of it
#    presupposes you are inside a live transaction.
#
#    The X-RAYS are firmly on the tracking side and stay:
#    /diligence/hcris-xray, /diligence/xray, /diligence/benchmarks —
#    these are the CMS cost-report drill-downs the whole product is
#    built around. They read a filing and print what it says.
#
#    Sweep 5 correction: the two payer-stress aliases and /cost-structure
#    were carried here as X-rays through three sweeps. They are not. Each
#    one takes a CCN, seeds a couple of real HCRIS figures, and then hands
#    the reader sliders — "what happens to EBITDA if commercial rates cut
#    5%" — and /cost-structure's own registry entry concedes the COGS /
#    SG&A / labor split "stays illustrative-labeled". A seeded slider
#    model is a deal-economics tool wearing a filing's clothes; the real
#    HCRIS opex figures underneath it are already on /diligence/hcris-xray.
_DEAL_EXECUTION_ROUTES = frozenset({
    # Per-deal diligence workbenches
    "/diligence/deal",
    "/diligence/deal-autopsy",
    "/diligence/deal-mc",
    "/diligence/counterfactual",
    "/diligence/covenant-stress",
    "/diligence/bridge-audit",
    "/diligence/cim-crosscheck",
    "/diligence/denial-prediction",
    "/diligence/exit-timing",
    "/diligence/physician-eu",     # "Provider Economics" — named, and a
                                   # DATA-REQUIRED stub besides
    "/diligence/risk-workbench",   # data-required stub
    "/diligence/snapshot",
    "/diligence/value",
    "/diligence/advanced-analytics",   # its own strip says "illustrative
                                       # worked example"
    # Commercial-diligence engagement scaffolding
    "/cdd",
    "/cdd/tools",
    "/diligence/cdd-scope",
    "/diligence/expert-calls",
    "/engagements",
    # IC / deliverable artifacts
    "/diligence/ic-packet",
    "/diligence/qoe-memo",
    # Checklists + question ledgers (engagement workflow, not data)
    "/diligence/checklist",
    "/diligence-checklist",
    "/diligence/questions",
    "/diligence/ingest",
    # Deal-vs-deal comparison — illustrative tier on both aliases
    "/compare",
    "/diligence/compare",
    # Transaction modelling + stress
    "/pipeline/rollup",
    "/pressure",
    "/portfolio/monte-carlo",
    "/pipeline/bridge",   # a jump-off INTO the EBITDA bridge, which is
                          # itself hidden — a door onto a hidden room
    # Seeded slider models (see the header note above)
    "/payer-stress",
    "/diligence/payer-stress",
    "/cost-structure",
    # Comp modelling: type a sector and an EV, get a MOIC/IRR
    # distribution over "most-similar realized deals". The corpus itself
    # stays browsable at /library; the model over it is underwriting.
    "/comparable-outcomes",
    # Value-creation execution + fund administration
    "/initiatives",
    "/variance",
    "/lp-update",
    # The output shelf for the artifacts above — LP updates and IC
    # packets, every producer of which is hidden on this list.
    "/exports",
})

# 5) NAMED ONE-OFFS — surfaces called out directly rather than fitting a
#    class. /conferences is a healthcare-PE conference calendar: a
#    networking planner, not a dataset or a tracked transaction.
_NAMED_ROUTES = frozenset({
    "/conferences",
})

# 6) BLOAT — pages unrelated to what this product is actually good at.
#    Three things, and everything here is none of them:
#
#      1. Displaying information about hospitals, health systems and other
#         outpatient services — the X-rays, the Care Compare universes,
#         the provider-identity files, the geography.
#      2. The scanners: searching that universe for something.
#      3. Deal tracking in the space: who acquired what, publicly reported.
#
#    Two judgement calls worth recording, because the route NAME misleads
#    in both cases and a future sweep will be tempted to redo them:
#
#      * ``/portfolio/regression`` STAYS. Despite the ``/portfolio/``
#        namespace it is an interactive OLS regression over the CMS HCRIS
#        universe — provider-data display, not portfolio ops.
#      * ``/rate-environment`` STAYS. It reads as market fluff; it is
#        setting-level CMS payment updates (IPPS, OPPS, PFS, ASC, SNF,
#        HH, Hospice), which is exactly the reimbursement backdrop for
#        the facility types above.
_BLOAT_ROUTES = frozenset({
    # ── Portfolio operations ────────────────────────────────────────
    # Running your own book. Deal tracking is about the SPACE — who
    # bought what — not about managing holdings you already own.
    "/portfolio",
    "/portfolio/heatmap",
    "/portfolio/map",
    "/portfolio/monitor",
    "/portfolio/risk-scan",
    "/cohorts",
    "/owners",
    # ── Model plumbing ─────────────────────────────────────────────
    # The internals of the prediction stack rather than a read of the
    # provider universe. (This block once carved out /predictive-screener
    # and /ml-insights on the grounds that they read the public hospital
    # universe. Both are now hidden further down — the read is real, the
    # thing printed on top of it is a prediction, and a prediction is not
    # a filing.)
    "/quant-lab",
    "/scenarios",
    "/surrogate",
    "/calibration",
    "/model-validation",
    "/models/importance",
    "/models/quality",
    # ── Deal-workflow chrome ───────────────────────────────────────
    # Personal/portfolio task management. /alerts and /watchlist stay:
    # watching a provider or a tracked deal is part of tracking.
    #
    # ``/my/<owner>`` is hidden as a CATALOG entry but keeps its link in
    # the topbar user menu — the same exemption INTERNAL_ROUTES already
    # documents for /users ("admin pages keep their user-menu links").
    # Account chrome is not a browse surface; a reader is not being
    # *offered* a destination when they open their own avatar menu.
    "/activity",
    "/deadlines",
    "/escalations",
    "/my/AT",
    "/my",
    "/day-one",
    "/insights",
    "/analysis",
    # ── Off-pillar reference ───────────────────────────────────────
    "/rxnorm",          # drug reference — not a provider or a deal
    "/markets/global",  # cross-country context — not US CMS
    "/labor-market",    # role-level wage/turnover — labor, not facilities
    # ── Revenue-cycle benchmarks ───────────────────────────────────
    # HFMA revenue-cycle KPI bands: the original RCM-diligence product,
    # and the thing this platform has been moving away from for four
    # sweeps.
    #
    # /diligence/benchmarks was carved out of this block twice, on the
    # grounds that it "places a FACILITY against its peer cohort, which
    # is provider-data display". Reading the renderer settles it the
    # other way. Its eyebrow is "RCM DILIGENCE · PHASE 2 OF 4", its lede
    # is "Five HFMA KPIs against acute-care peer bands … the Phase-2
    # evidence base for the RCM thesis", its source note credits the same
    # HFMA MAP Key 2021 bands as the two routes below, and the facility
    # is a FIXTURE claims file chosen from a selector, not a filing. It
    # is Phase 2 of a four-phase workspace whose other three phases
    # (/diligence/snapshot, /diligence/root-cause, /diligence/qoe-memo)
    # are already hidden — the same page family under a third URL.
    "/benchmarks",
    "/rcm-benchmarks",
    "/diligence/benchmarks",
    # ── Meta / upload prompts ──────────────────────────────────────
    "/data-activation",  # "what to upload to unlock DATA-REQUIRED pages"
    # ── The graphics toolkit ───────────────────────────────────────
    # /visuals is the hub for this family and describes itself as "the
    # graphics toolkit — Chart Builder, Pie Chart, Excel Map". They are
    # generators, not reads: each starts empty and asks you to type a
    # label, a value and a colour, then draws a consultant chart. Nothing
    # here displays a CMS filing, so the whole family goes together —
    # including /charts, which only stores configurations for the two
    # builders below it.
    "/visuals",
    "/chart-builder",
    "/pie-chart",
    "/exhibit",
    "/charts",
    "/excel-mapping",
    "/excel-templates",
    # ── Half-working regressions + model output ────────────────────
    # /portfolio/regression is an interactive OLS the reader has to
    # configure before it says anything, and its classical-inference
    # output was never finished. /ml-insights is the same shape: predicted
    # KPIs rather than filed ones. Both were kept through earlier sweeps
    # on the grounds that they read the HCRIS universe; that is true and
    # not sufficient — a regression you have to build yourself is not a
    # provider report.
    "/portfolio/regression",
    "/ml-insights",
    # ── State-level maps ──────────────────────────────────────────
    # /geo-map is a US choropleth; /geo-metrics is the transparency
    # reference for the geo suite rather than a read of it. The
    # state-analysis TABLES (/state-compare, /state-profile,
    # /state-peers, /state-rankings, /county-explorer, /metro-markets)
    # are deliberately still visible — they carry real state-keyed public
    # data rather than a map, and no instruction has ruled on them.
    "/geo-map",
    "/geo-metrics",
    # ── Thin input-driven surfaces ─────────────────────────────────
    "/query",               # "ad-hoc query tool over the app's data"
    "/screening/dashboard",  # a deal-funnel view, not a provider read
    # ── Build-your-own analysis ────────────────────────────────────
    # The same ruling as the graphics toolkit one section up, applied
    # to the analytic side of it. /cross-analysis asks you to pick an X
    # measure and a Y measure and hands back a Pearson r with a
    # least-squares trendline; /further-analysis is a "Tableau-style
    # data explorer" over the vendored datasets. Both start empty and
    # produce whatever you configure. That is a chart tool, and a
    # correlation between two state aggregates is the kind of number
    # that reads as a finding without being one. The datasets behind
    # them stay readable at /state-compare, /state-profile and the
    # provider universes, which print what a filing says rather than
    # asking the reader to derive it.
    "/cross-analysis",
    "/further-analysis",
    # ── Model output dressed as a screen ───────────────────────────
    # /predictive-screener is the last surface in the whole visible set
    # that classify_surface() still tiers YELLOW — "realistic figures
    # built on the bundled ILLUSTRATIVE seed-deal corpus". It ranks
    # hospitals by an estimated RCM EBITDA uplift: a prediction from the
    # retired revenue-cycle product, presented in the same table shape
    # as /screen and /target-screener, which rank on filed figures.
    "/predictive-screener",
    # ── Licensed narrative reference ───────────────────────────────
    # Long-form sector write-ups from third-party licensed material
    # (IBISWorld, SimplyAnalytics, the 2025-2026 payer/vertical
    # references). They are well made and they are not CMS: nothing on
    # them traces to a filing a reader could check, which is the whole
    # promise. /verticals stays — that is the CMS-data-backed index of
    # the provider universes (SNF, home health, hospice, dialysis, IRF,
    # LTCH, hospital), and the near-identical /healthcare-verticals name
    # sitting next to it was its own navigational bloat.
    "/healthcare-verticals",
    "/healthcare-verticals-reference",
    "/healthcare-verticals/unit-economics",
    "/industry",
    "/payer-system",        # "the four payer-economics CDD exhibits"
    "/market-intel/geo",    # licensed SimplyAnalytics market scores
    # Six chart-ready reference domains (compensation surveys, procedure
    # frequency, disease prevalence). Companion to /rcm-benchmarks,
    # hidden one sweep earlier for the same reason.
    "/benchmark-reference",
    # ── Second global search ───────────────────────────────────────
    # /search is the one the topbar field posts to. /global-search is a
    # second results page over the same entities.
    "/global-search",
    # ── Market aggregation ─────────────────────────────────────────
    # /market-data is a real HCRIS read and it is also, by its own
    # registry line, "heatmaps, state comparisons, regression views, and
    # hospital density maps" — three of those four are families this
    # sweep and the last one already retired, and /market-data/map is
    # the same renderer under a second URL. Its state roll-ups are the
    # ones /state-rankings and /state-compare print from the same
    # source; what is left on top is an OLS panel and a choropleth. Its
    # "Data Sources" card credits FRED and Capital IQ, neither of which
    # the page reads.
    "/market-data",
    # /market-intel reads as live market context and is a hand-edited
    # YAML snapshot: public_comps.yaml says in as many words that "no
    # live API call is made", it was last reviewed in April 2026, and
    # the earnings calendar invents its dates by adding 90 days to the
    # previous report. Transaction tracking that IS sourced stays —
    # /verified-deals cites a URL per row, /news is the feed, and
    # /deal-library/comps computes multiples from the licensed universe.
    "/market-intel",
    # ── A third route catalog ──────────────────────────────────────
    # /module-index is a hand-maintained list of 43 Module() literals
    # standing in for the live route registry that /tools renders from,
    # and its featured cards carry sparklines its own docstring calls
    # "decorative editorial flourish (illustrative fixed data)".
    "/module-index",
    # ── Pure input form ────────────────────────────────────────────
    # /import is two forms and a KPI strip of hardcoded string literals
    # ("Required Fields 2", "Bayesian Priors 12+") — it renders no
    # analysis, and it POSTs to /quick-import rather than to itself.
    # /new-deal is the front door for deal entry, manual or bulk.
    "/import",
})

# 7) DUPLICATE CATALOGS — nine surfaces answered "what data do you have".
#    Every one of them is real and honest; having nine of them is the
#    bloat. The instruction was to document the CMS and Medicare report
#    coverage better, and nine competing inventories is the opposite of
#    documenting it — a reader cannot tell which one is authoritative.
#
#    THREE stay, with distinct jobs:
#      * ``/data`` — the canonical inventory: every source with its URL,
#        refresh cadence, last-loaded timestamp, row count and licence.
#      * ``/cms-sources`` — the CMS-specific registry: dataset IDs,
#        granularity, update cadence, key columns. This is the one the
#        "document the CMS reports" instruction points at.
#      * ``/data-quality`` — the verification surface: live row counts,
#        vintages, null rates, and the known-gap register. A product
#        whose promise is "publicly verify datasets" needs the page that
#        admits what is missing.
#
#    The six below duplicate those three, document data we do not hold,
#    or inventory infrastructure rather than datasets.
_DUPLICATE_CATALOG_ROUTES = frozenset({
    "/data/catalog",        # same inventory as /data, different chrome
    "/cms-data-browser",    # same CMS list as /cms-sources, ranked by rows
    "/data-intelligence",   # third pass at "sources wired in and what
                            # they power"
    "/tools/open-data",     # fourth pass, with per-source detail pages
    # Catalogs of data we do NOT have. /data-apis lists free public APIs
    # PEdesk "can draw on"; /tools/nonpublic-cms describes itself as an
    # internal staging surface over the CREDENTIALED CMS microdata
    # programs (ResDAC/CCW, LDS, RIF, CCLF) — a roadmap, not a holding.
    "/data-apis",
    "/tools/nonpublic-cms",
    # An inventory of connectors (openFDA, CDC, HRSA, NIH, Census)
    # rather than of datasets, and off-pillar besides — none of those
    # sources is a provider filing or a tracked deal.
    "/connector-estate",
    # A second research index alongside /best/research, and by the end
    # of the sweeps 11 of its 14 curated entries were hidden — the
    # conference roadmap, the PE Intelligence hub, bear cases, the
    # corpus backtests, the market-intel and hold/IRR narratives. The
    # three that survive (/methodology, /regulatory-calendar, /notes)
    # are one click away in the same rail and carded on the section
    # catalog. An index of three, all of them adjacent, is chrome.
    "/research",
})

HIDDEN_ROUTES = (
    _ILLUSTRATIVE_ROUTES
    | _SINGLE_STUDY_ROUTES
    | _PE_NARRATIVE_ROUTES
    | _DEAL_EXECUTION_ROUTES
    | _NAMED_ROUTES
    | _BLOAT_ROUTES
    | _DUPLICATE_CATALOG_ROUTES
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
