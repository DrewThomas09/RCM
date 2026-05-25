"""Single source of truth for every PEdesk surface's data-honesty status.

Four-tier indicator (used by the /tools index circles AND the generated
`docs/PEDESK_DILIGENCE_SURFACE_STATUS.md`):

  GREEN  — live/real data (CMS/HCRIS/CIVHC/FDA/MSSP/HRSA public, or the user's
           own real deal/portfolio/system data). Investment-usable as-is.
  NAVY   — a legitimate diligence CALCULATOR/model: illustrative defaults but
           it computes off YOUR inputs (e.g. roll-up, LBO stress, scenario MC).
           Honest as a tool; the output reflects what you put in.
  YELLOW — potentially-fake: presents realistic figures built on the bundled
           ILLUSTRATIVE seed-deal corpus (looks real, isn't this market's data).
  RED    — entirely synthetic: hardcoded fabricated values regardless of input
           (e.g. Management Comp, Partner Economics).

This is a first-pass classification to drive the page-by-page conversion loop;
refine entries as pages are made real. Adding a route to GREEN/NAVY as it is
converted is the mechanism for "turning the circle green".
"""
from __future__ import annotations

from typing import Dict

# colour + human label per tier
TIERS = {
    "green":  ("#0a8a5f", "LIVE — real data"),
    "navy":   ("#0b2341", "Diligence calculator (your inputs)"),
    "yellow": ("#b8842e", "Illustrative seed-corpus data"),
    "red":    ("#b5321e", "Synthetic / hardcoded data"),
}

# ── GREEN: real CMS/public data, or real user/deal/system data ──────────────
_GREEN = frozenset({
    # real-data diligence (wired this loop)
    "/diligence/hcris-xray", "/diligence/xray", "/diligence/snapshot",
    "/ref-pricing", "/cms-apm", "/drug-shortage", "/payer-rate-trends",
    "/cost-structure", "/payer-stress", "/diligence/payer-stress", "/debt-service",
    # Deal Library (real licensed + public enrichment)
    "/deal-library", "/deal-library/comps", "/deal-library/sponsors",
    # CMS public vertical pages
    "/dialysis", "/home-health", "/hospice", "/nursing-homes",
    "/inpatient-rehab", "/long-term-care-hospital", "/hospital-anchor",
    # data catalogs / public sources
    "/cms-sources", "/cms-data-browser", "/data", "/data/catalog",
    "/data/refresh", "/data-intelligence", "/market-data/map",
    "/market-data/state/CA", "/methodology", "/methodology/calculations",
    "/metric-glossary", "/rcm-benchmarks", "/library", "/verticals",
    "/module-index", "/tools", "/benchmarks", "/diligence/benchmarks",
    "/comparable-outcomes", "/diligence/comparable-outcomes",
    "/regulatory-calendar", "/diligence/regulatory-calendar",
    # real deal/portfolio/user workflow (operates on the user's real DB)
    "/app", "/home", "/dashboard", "/pipeline", "/deal-pipeline",
    "/diligence/deal", "/diligence/ingest", "/diligence/checklist",
    "/diligence-checklist", "/diligence/questions", "/diligence/ic-packet",
    "/import", "/quick-import", "/quick-import-json", "/upload", "/new-deal",
    "/new-deal/manual", "/new-deal/upload", "/alerts", "/escalations",
    "/watchlist", "/deadlines", "/cohorts", "/owners", "/notes",
    "/engagements", "/engagements/create", "/initiatives", "/portfolio",
    "/portfolio/map", "/portfolio/monitor", "/portfolio/heatmap",
    "/portfolio/risk-scan", "/lp-update", "/exports", "/exports/lp-update",
    "/digest/morning", "/day-one", "/my/AT", "/activity", "/global-search",
    "/search", "/query", "/pressure", "/ops", "/deals", "/deal-search",
    "/screen", "/screening/dashboard", "/target-screener", "/conferences",
    "/diligence/sponsor-detail", "/diligence/synthesis/",
    # admin / system (real status)
    "/audit", "/users", "/settings", "/settings/ai", "/settings/workspace",
    "/runs", "/jobs", "/cli-runs", "/v3-status", "/v5-status", "/variance",
    "/team", "/admin/audit-chain", "/admin/data-sources", "/calibration",
    "/calibrate", "/ready", "/model-validation", "/guide/context-debug",
    "/news", "/research",
})

# ── NAVY: diligence calculators (compute off your inputs) ───────────────────
_NAVY = frozenset({
    "/physician-productivity", "/phys-comp-plan", "/physician-labor",
    "/provider-retention", "/quality-scorecard", "/clinical-outcomes",
    "/regulatory-risk", "/supply-chain", "/payer-shift", "/ma-contracts",
    "/workforce-planning", "/provider-network", "/concentration-risk",
    "/lbo-stress", "/scenario-mc", "/scenarios", "/diligence/deal-mc",
    "/diligence/covenant-stress", "/diligence/bridge-audit", "/ebitda-bridge/",
    "/multiple-decomp", "/rollup-economics", "/cap-structure", "/entry-multiple",
    "/exit-multiple", "/exit-readiness", "/exit-timing", "/diligence/exit-timing",
    "/value-creation", "/value-creation-plan", "/diligence/value",
    "/growth-runway", "/reinvestment", "/capital-efficiency", "/hold-optimizer",
    "/acq-timing", "/refi-optimizer", "/dividend-recap", "/earnout",
    "/escrow-earnout", "/tax-structure", "/tax-structure-analyzer", "/tax-credits",
    "/peer-valuation", "/qoe-analyzer", "/diligence/qoe-memo", "/bolton-analyzer",
    "/portfolio-sim", "/portfolio-optimizer", "/portfolio/monte-carlo",
    "/portfolio/regression", "/surrogate", "/covenant-headroom",
    "/covenant-monitor", "/capital-pacing", "/capital-schedule", "/capital-call",
    "/unit-economics", "/working-capital", "/demand-forecast",
    "/diligence/counterfactual", "/diligence/denial-prediction", "/underwriting",
    "/underwriting-model", "/quant-lab", "/debt-financing", "/denovo-expansion",
    "/aco-economics", "/scenarios/", "/diligence/deal-autopsy",
})

# ── YELLOW: realistic figures built on the illustrative seed-deal corpus ────
_YELLOW = frozenset({
    "/sponsor-league", "/sponsor-heatmap", "/sponsor-track-record",
    "/sector-intel", "/sector-intelligence", "/sector-momentum",
    "/sector-correlation", "/find-comps", "/comparables", "/compare",
    "/diligence/compare", "/deals-library", "/payer-intel", "/payer-intelligence",
    "/pe-intelligence", "/geo-market", "/specialty-benchmarks", "/vintage-perf",
    "/vintage-cohorts", "/irr-dispersion", "/gp-benchmarking", "/size-intel",
    "/leverage-intel", "/deal-quality", "/deal-risk-scores", "/deal-flow-heatmap",
    "/market-rates", "/corpus-dashboard", "/corpus-coverage", "/corpus-backtest",
    "/backtest", "/backtester", "/deal-corpus-analytics", "/return-attribution",
    "/fund-attribution", "/portfolio-analytics", "/hold-analysis",
    "/peer-transactions", "/base-rates", "/bear-cases", "/diligence/bear-case",
    "/value-backtester", "/predictive-screener", "/deal-screening",
    "/deal-origination", "/deal-sourcing", "/screening/bankruptcy-survivor",
    "/diligence/thesis-pipeline", "/deal-postmortem", "/fund-learning",
    "/dpi-tracker", "/diligence/root-cause",
})

# ── RED: entirely synthetic / hardcoded fabricated values ───────────────────
_RED = frozenset({
    "/mgmt-comp", "/partner-economics",
    "/diligence/physician-attrition", "/diligence/physician-eu",
    "/mgmt-fee-tracker", "/key-person", "/esg-dashboard", "/esg-impact",
    "/hcit-platform", "/biosimilars", "/insurance-tracker", "/rw-insurance",
    "/litigation", "/cyber-risk", "/drug-pricing-340b", "/tracker-340b",
    "/locum-tracker", "/clinical-ai",
    "/patient-experience", "/competitive-intel",
    "/antitrust-screener", "/redflag-scanner", "/rcm-red-flags",
    "/msa-concentration", "/payer-concentration",
    "/payer-contracts", "/ma-star",
    "/nsa-tracker", "/medicaid-unwinding", "/risk-adjustment", "/risk-matrix",
    "/revenue-leakage", "/gpo-supply",
    "/capex-budget", "/treasury", "/fundraising", "/nav-loan-tracker",
    "/secondaries-tracker", "/continuation-vehicle", "/coinvest-pipeline",
    "/operating-partners", "/board-governance", "/compliance-attestation",
    "/transition-services", "/pmi-integration", "/pmi-playbook",
    "/digital-front-door", "/direct-employer", "/direct-lending",
    "/telehealth-econ", "/trial-site-econ", "/tech-stack", "/health-equity",
    "/medical-realestate", "/real-estate", "/platform-maturity",
    "/ai-operating-model", "/cin-analyzer", "/fraud-detection",
    "/workforce-retention", "/zbb-tracker", "/vcp-tracker",
    "/vdr-tracker", "/diligence-vendors", "/diligence/risk-workbench",
    "/sellside-process", "/platform-maturity",
})

_REASON = {
    "green": "Real data (CMS/HCRIS/CIVHC/FDA/MSSP/HRSA public, or your own deal/portfolio/system data).",
    "navy": "Diligence calculator: illustrative defaults but the output is computed from the inputs you provide.",
    "yellow": "Realistic figures built on the bundled ILLUSTRATIVE seed-deal corpus — not this market's real data.",
    "red": "Entirely synthetic / hardcoded values that do not change with input — replace with real data or relabel.",
}


def _norm(route: str) -> str:
    if not route:
        return ""
    r = str(route).split("?", 1)[0]
    # keep trailing slash variants resolvable both ways
    return r


def classify_surface(route: str) -> Dict[str, str]:
    """Return {color, status_label, reason} for a route. Ordered: explicit
    GREEN/NAVY/RED/YELLOW; then illustrative-registry → yellow; else green
    (real workflow/system not flagged illustrative)."""
    r = _norm(route)
    rs = r.rstrip("/") or "/"
    for tier, members in (("green", _GREEN), ("navy", _NAVY),
                          ("red", _RED), ("yellow", _YELLOW)):
        if r in members or rs in members:
            color, label = TIERS[tier]
            return {"color": color, "tier": tier, "status_label": label,
                    "reason": _REASON[tier]}
    # fall back to the route-level illustrative registry
    try:
        from rcm_mc.ui._chartis_kit import _is_illustrative_route
        if _is_illustrative_route(r):
            color, label = TIERS["yellow"]
            return {"color": color, "tier": "yellow", "status_label": label,
                    "reason": _REASON["yellow"] + " (auto: illustrative route, "
                    "not yet hand-classified)"}
    except Exception:
        pass
    color, label = TIERS["green"]
    return {"color": color, "tier": "green", "status_label": label,
            "reason": "Real user/deal/system surface (not flagged illustrative)."}


def status_dot(route: str) -> str:
    """A small colored circle (with tooltip) for the /tools index."""
    c = classify_surface(route)
    return (f'<span class="ck-status-dot" title="{c["status_label"]} — '
            f'{c["reason"]}" style="display:inline-block;width:8px;height:8px;'
            f'border-radius:50%;background:{c["color"]};margin-right:7px;'
            f'flex-shrink:0;vertical-align:middle"></span>')
