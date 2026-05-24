# PEdesk Route Taxonomy — data-universe classification

**Status:** Phase 4 reference (proposal). Defines the canonical data
universes and classifies the partner-facing pages. The implementation goal is
that **every page renders a visible `data-universe` chip** so a partner never
mistakes corpus for portfolio.

---

## Canonical data universes

| Chip | Meaning | Owns it | Where it belongs |
|---|---|---|---|
| `USER DEALS` | Opportunities the user/fund created or imported | the fund | Pipeline |
| `USER PORTFOLIO` | Actual owned portfolio companies/assets | the fund | Portfolio / Home |
| `CMS PUBLIC DATA` | Public provider/facility data (HCRIS, Care Compare, …) | CMS | Source / Diligence |
| `BENCHMARK CORPUS` | Historical deals / comps used for comparison (the 655-deal set) | reference | Research |
| `RESEARCH REFERENCE` | Payer, sponsor, conference, sector docs | reference | Research |
| `MIXED DATA` | Combines universes — must label each section | — | annotate inline |

**Rule:** a page may only present data from another universe if it is **clearly
labeled**. If `USER PORTFOLIO` has no records, show an honest empty state —
never substitute corpus.

---

## Page classification (partner-named surfaces)

| Route | Page | Universe(s) | User-specific? | Honest label today? |
|---|---|---|---|---|
| `/app` | Command Center | MIXED (USER + summaries) | yes | partial — label sections |
| `/portfolio/map` | Portfolio Map | USER DEALS (state geo) | yes | ✅ (empty state honest) |
| `/portfolio/heatmap` | Portfolio Heatmap | USER DEALS | yes | needs label |
| `/portfolio-analytics` | "Portfolio Analytics" | **BENCHMARK CORPUS** | **no** | ⚠️ body says corpus, **nav label says portfolio** |
| `/lp-update` | LP Update | USER PORTFOLIO | yes | ok |
| `/source` | Deal Sourcing | CMS PUBLIC DATA | no | needs label |
| `/screen` | Hospital Screener | CMS PUBLIC DATA | no | needs label |
| `/predictive-screener` | Predictive Screener | CMS PUBLIC DATA | no | needs label |
| `/pe-intelligence` | PE Intelligence | MIXED / REFERENCE | no | unclear |
| `/deal-screening` | Deal Screening | USER DEALS (verify freshness) | yes | needs label |
| `/find-comps` | Find Comps | BENCHMARK CORPUS | no | needs label |
| `/deal-quality` | Deal Quality Score | USER DEALS / CMS | mixed | needs label |
| `/deal-risk-scores` | Deal Risk Score | USER DEALS | yes | needs label |
| `/deal-flow-heatmap` | Deal Flow Heatmap | USER DEALS | yes | needs label |
| `/pipeline/bridge` | EBITDA Bridge | USER DEALS | yes | ok |
| `/antitrust-screener` | Antitrust Screener | CMS PUBLIC DATA / REF | no | needs label |
| `/sponsor-track-record`, `/sponsor-league` | Sponsor Track Record | BENCHMARK CORPUS / REF | no | needs label + merge |
| `/payer-intelligence` | Payer Intelligence | RESEARCH REFERENCE | **no** | needs label + move |
| `/deals` | New Deal | USER DEALS | yes | rename verb |

---

## The label component (proposed, PR B)

A small mono chip rendered near each page title, e.g.:

```
[ BENCHMARK CORPUS ]   ← amber-toned, for /portfolio-analytics, /find-comps, sponsor, payer
[ CMS PUBLIC DATA ]    ← teal-toned, for screeners, X-Ray, antitrust
[ USER DEALS ]         ← navy-toned, for pipeline pages
[ USER PORTFOLIO ]     ← green-toned, for portfolio/holdings
```

For `MIXED` pages, label each section rather than the whole page.

### Highest-priority labels (PR B scope)
1. `/portfolio-analytics` → `BENCHMARK CORPUS` (+ rename/move in PR C).
2. `/find-comps` → `BENCHMARK CORPUS`.
3. `/payer-intelligence` → `RESEARCH REFERENCE`.
4. `/sponsor-track-record` → `BENCHMARK CORPUS`.
5. The screener trio → `CMS PUBLIC DATA`.

This taxonomy is the contract PR B implements and PRs C–J keep honest.
