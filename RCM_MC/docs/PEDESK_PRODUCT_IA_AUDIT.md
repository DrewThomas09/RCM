# PEdesk Product Information-Architecture Audit

**Status:** Phase 0–3 audit + proposed plan. **Docs only — no UI, route, nav,
or data changes in this PR.** Nothing here is implemented until reviewed.

**Core principle:** *one page, one job, one data universe.* Today too many
pages mix jobs and mix data universes, which is why the app feels confusing
even though the individual features are strong.

---

## 1. Route inventory (counts)

| Surface | Count | Source of truth |
|---|---|---|
| GET routes registered in `server.py` (`path == "/…"`) | **388** | `rcm_mc/server.py` |
| Surfaces in the Cmd-K palette / Tools index | **~240** | `_DEFAULT_PALETTE_MODULES` |
| Routes surfaced in the topbar nav (top + sub) | **68** | `_CORPUS_NAV` + `_SUB_NAV` |

The gap between 388 routes and ~38 nav-surfaced pages is itself a finding:
most surfaces are reachable only via Cmd-K / deep links, so the **nav is not a
map of the product**. This audit focuses on the ~30 partner-named pages plus
the nav structure; the long tail is catalogued by the route taxonomy doc.

---

## 2. The five concepts PEdesk currently conflates

1. **Market / target discovery** — find providers/targets (CMS public data).
2. **Deal pipeline workflow** — track real opportunities the user created.
3. **Diligence / analysis** — go deep on one provider/deal.
4. **Portfolio / fund monitoring** — the user's actual owned assets.
5. **Research / benchmark corpus** — historical deals, comps, reference intel.

The confusion is that pages from all five live under nav sections that imply a
different concept (e.g. a **corpus** analytics page sits under **Portfolio**).

---

## 3. Current nav map (as shipped today)

```
Home       Command Center · My Dashboard · Alerts · Escalations · Watchlist
Pipeline   Deal Sourcing · Hospital Screener · Predictive Screener ·
           PE Intelligence · Deal Screening · Find Comps · Conferences
Diligence  Deal Profile · Ingestion · Benchmarks · CMS X-Ray · HCRIS X-Ray · QoE Memo
Library    Deals Library · Methodology · Metric Glossary · RCM Benchmarks ·
           Data Catalog · Comparables · Market Rates
Research   Notes · Sector Momentum · IRR Dispersion · Hold Analysis · Market Intel
Portfolio  Portfolio Map · Heatmap · Risk Scan · Portfolio Analytics ·
           Sponsor Track Record · Payer Intelligence · LP Update
```

---

## 4. Per-page audit (partner-named pages)

Legend for **Data universe**: `CMS` public market data · `CORPUS` benchmark/
historical deal corpus · `USER-DEAL` user opportunity records · `USER-PORT`
user portfolio holdings · `REF` research reference · `MIXED`.

| Route | Label · nav | Renderer | Data universe | Job today | Issue | Disposition |
|---|---|---|---|---|---|---|
| `/app` | Command Center · Home | `chartis/app_page` | MIXED (user+corpus) | Daily dashboard | Good; UI polish only | **keep** (Home anchor) |
| `/portfolio/map` | Portfolio Map · Portfolio | `portfolio_map` | USER-DEAL (state geo) | Geo exposure | Good (now real SVG) | **keep** |
| `/portfolio/heatmap` | Heatmap · Portfolio | `portfolio_heatmap` | USER-DEAL | Risk×dim grid | UI + data quality | **keep, data fix** |
| `/portfolio-analytics` | Portfolio Analytics · Portfolio | `chartis/portfolio_analytics_page` | **CORPUS (655 deals)** | Corpus scorecard | **Mislabeled as portfolio**; body already says "corpus" | **rename → Deal Corpus Analytics + move to Research** (or universe selector) |
| `/lp-update` | LP Update · — | `reports/lp_update` | USER-PORT | LP digest | Belongs in Home+Portfolio | **keep** |
| `/source` | Deal Sourcing · Pipeline | `source_page` + `deal_sourcer` | CMS (thesis match) | Thesis→targets | Overlaps screeners | **merge → Target Screener** |
| `/screen` | Hospital Screener · Pipeline | `_route_screener_page` | CMS (HCRIS) | Filter hospitals | Overlaps `/source`,`/predictive-screener` | **merge → Target Screener** |
| `/predictive-screener` | Predictive Screener · Pipeline | `predictive_screener` (HCRIS+ML) | CMS (HCRIS) | ML-rank hospitals | Overlaps above | **merge → Target Screener (Prediction mode)** |
| `/pe-intelligence` | PE Intelligence · Pipeline | `pe_intelligence_hub_page` | MIXED/REF | Generic intel hub | **Doesn't belong in Pipeline** | **move → Research** (or fold) |
| `/deal-screening` | Deal Screening · Pipeline | `deal_screening_page` | USER-DEAL (stale?) | Thesis/deal review | Name collides w/ sourcing; stale records | **reframe → Thesis Workspace (Source)** |
| `/find-comps` | Find Comps · Pipeline | `data_public/find_comps_page` | CORPUS | Comparable txns | Useful; wrong section | **move → Research** |
| `/conferences` | Conferences · Pipeline | — | REF | Conference tracker | Not Pipeline | **move → Source or Research** |
| `/deal-quality` | Deal Quality Score | (AUTO) | USER-DEAL/CMS | Score a target | Unclear home/accuracy | **place as target→pipeline bridge** |
| `/deal-risk-scores` | Deal Risk Score | (AUTO) | USER-DEAL | Risk dashboard | UI + data quality | **keep in Pipeline, data fix** |
| `/deal-flow-heatmap` | Deal Flow Heatmap | (AUTO) | USER-DEAL | Flow viz | UI + data quality | **keep in Pipeline, data fix** |
| `/pipeline/bridge` | EBITDA Bridge | `pe/rcm_ebitda_bridge` | USER-DEAL | Value bridge | Small UI bugs | **keep, UI fix** |
| `/deal-origination` | Deal Origination | (AUTO) | USER-DEAL | unclear | "Makes no sense" | **deprecate/merge into Pipeline** |
| `/deal-pipeline` | Deal Pipeline | (AUTO) | USER-DEAL | Pipeline list | Confusing vs others | **canonical Pipeline list** |
| `/antitrust-screener` | Antitrust Screener | (AUTO) | CMS/REF | HHI/overlap | Functionality broken | **keep in Diligence, fix** |
| `/sponsor-league`, `/sponsor-track-record` | Sponsor League / Track Record | `sponsor_*` | CORPUS/REF | Sponsor history | Duplicate; reference data | **merge → one, move to Research** |
| `/payer-intelligence` | Payer Intelligence · Portfolio | `payer_*` | REF (not user) | Payer intel | Not user-specific; wrong section | **move → Research** (+ deal-specific Payer Analysis in Diligence) |
| `/deals` / New Deal | New Deal | (AUTO) | USER-DEAL | create record | Unclear verb/home | **rename** (Add Target / Import Deal / Create Opportunity) |

> "(AUTO)" = route exists and is palette-surfaced but not in the curated nav;
> renderer to be confirmed in implementation phase. Dispositions are
> **proposals for review**, not decisions.

---

## 5. Duplicate / overlap analysis

### 5a. Deal Sourcing × Hospital Screener × Predictive Screener
All three operate over the **same CMS/HCRIS hospital universe**, differing only
in framing: `/source` matches a thesis library, `/screen` is manual filters,
`/predictive-screener` adds an ML ranking. **Confirmed near-duplicates.**
→ **Unify into one "Target Screener"** with modes: *Market filters ·
Prediction · Thesis · Saved searches · Imported targets*. Keep old routes as
redirects until the unified surface + tests land.

### 5b. Deal Screening × Deal Quality Score × Deal Risk Score
Three different jobs wearing similar names:
- **Deal Quality Score** → "should we care about this target?" (target→pipeline bridge)
- **Deal Risk Score** → "what can go wrong?" (risk dashboard)
- **Deal Screening** → "does this thesis produce attractive targets?" (thesis workspace)
→ Keep all three but **rename for distinct jobs** and verify the deal records
they read are real, not stale.

### 5c. Portfolio Analytics × Deal Corpus Analytics
`/portfolio-analytics` already loads `load_corpus_deals()` and its own copy
says *"Corpus-wide views across the 655-deal universe"* — but it is **labeled
"Portfolio Analytics" under the Portfolio nav**, so it reads as the user's
book. → **Rename to "Deal Corpus Analytics" and move to Research**, OR add a
prominent universe selector (My Portfolio / Firm Corpus / Benchmark). If "My
Portfolio" has no records, show an honest empty state — never show corpus as
portfolio.

### 5d. Sponsor League × Sponsor Track Record
Overlapping sponsor-history views → **merge into one**, place in **Research**.

---

## 6. Proposed nav map (for review — not implemented)

```
Home       Command Center · Recent Work · Portfolio Snapshot · Alerts · LP Update Summary
Source     Target Screener · CMS Sector Screeners · Thesis Workspace · Saved Searches · Conferences
Pipeline   Deal Pipeline · New Deal/Import · Deal Quality · Deal Risk · Deal-Flow Heatmap · EBITDA Bridge · IC Packet
Diligence  HCRIS X-Ray · CMS Provider X-Ray · Antitrust Screener · Payer Analysis (deal) · Market Intelligence · Source Library
Portfolio  Portfolio Map · Portfolio Heatmap · Active Holdings · Portfolio Analytics (real) · LP Update
Research   Deal Corpus Analytics · Find Comps · Sponsor Track Record · Payer Intelligence · Sector Research · Library
```

### Route migration table (proposal)

| Current route | Current label · nav | Data | Problem | Proposed label · nav | Action |
|---|---|---|---|---|---|
| `/portfolio-analytics` | Portfolio Analytics · Portfolio | CORPUS | corpus-as-portfolio | Deal Corpus Analytics · Research | rename+move (redirect) |
| `/sponsor-track-record` | Sponsor Track Record · Portfolio | CORPUS | reference data in Portfolio | Sponsor Track Record · Research | move (redirect) |
| `/payer-intelligence` | Payer Intelligence · Portfolio | REF | not user-specific | Payer Intelligence · Research | move (redirect) |
| `/source`,`/screen`,`/predictive-screener` | 3 screeners · Pipeline | CMS | near-duplicates | Target Screener · Source | merge (redirects) |
| `/pe-intelligence` | PE Intelligence · Pipeline | MIXED | wrong section | Research (or fold) | move/fold |
| `/find-comps` | Find Comps · Pipeline | CORPUS | wrong section | Find Comps · Research | move (redirect) |
| `/conferences` | Conferences · Pipeline | REF | wrong section | Conferences · Source | move (redirect) |
| `/deal-origination` | Deal Origination · — | USER-DEAL | redundant | fold into Deal Pipeline | deprecate (redirect) |

**No route is deleted** — every move ships with a redirect from the old path
and updated Guide context.

---

## 7. Top 10 implementation PRs (proposed order)

1. **PR A — docs(product): IA + workflow audit** *(this PR — docs only)*.
2. **PR B — feat(ui): data-universe labels** on Portfolio Analytics, Find
   Comps, Payer Intelligence, Sponsor Track Record (CMS / CORPUS / USER-DEAL /
   USER-PORT chips). No route moves.
3. **PR C — feat(portfolio): reframe Portfolio Analytics** (rename → Deal
   Corpus Analytics + redirect, or universe selector).
4. **PR D — feat(nav): move Research pages** (Sponsor Track Record, Payer
   Intelligence → Research; Conferences → Source) with redirects + Guide.
5. **PR E — feat(source): Target Screener** shell unifying the screener trio
   (modes + redirects; old routes preserved).
6. **PR F — feat(pipeline): Pipeline = real deals only** (honest empty state;
   remove market pages from Pipeline nav; "Promote to Pipeline" entry points).
7. **PR G — feat(deal): Deal Quality Score as target→pipeline bridge**.
8. **PR H — fix(ui): Deal Flow Heatmap + Deal Risk Score** UI + data quality.
9. **PR I — fix(ui): EBITDA Bridge + Antitrust Screener** bug fixes.
10. **PR J — feat(home): Command Center as the operating dashboard** with
    honest empty states.

Each PR: tests (presence **and** absence of old structure), Guide context,
redirects for moved routes, no fake data, approval before merge.

---

## 8. Data-semantics findings (the root cause)

- **Portfolio Analytics shows a 655-deal CORPUS under a "Portfolio" label.**
  Highest-impact mislabel. (Confirmed in code.)
- **Sponsor Track Record / Payer Intelligence are REFERENCE/CORPUS data in the
  Portfolio section** — they are not user-specific.
- **The screener trio reads the same CMS/HCRIS universe** but presents as three
  products.
- **Pipeline mixes market-discovery pages with deal-workflow pages**, so
  "Pipeline" doesn't mean "my live deals."
- **Fix:** every page renders a `data-universe` chip (see route taxonomy doc),
  and Pipeline/Portfolio show honest empty states when no user records exist.

---

## 9. Risks

- **Route moves can break deep links / Cmd-K / Guide context** → every move
  ships a redirect + palette + Guide update; tests assert old routes still 200.
- **Merging the screener trio** risks losing a unique filter/behavior → inventory
  each screener's filters before consolidating; keep routes as redirects.
- **Renaming "Portfolio Analytics"** may surprise muscle memory → keep the old
  route as a redirect with a one-line "moved to Research" note.
- **"Active Holdings" / real Portfolio Analytics** may have **no user data
  today** → must be an honest empty state, not corpus fallback.
- All nav/UI PRs are **approval-gated**.

---

## 10. What requires user approval before implementation

- The **proposed nav map** (§6) — especially moving Sponsor Track Record,
  Payer Intelligence, Find Comps out of their current sections.
- The **Portfolio Analytics reframe** decision: rename+move vs. universe selector.
- The **screener consolidation** into one Target Screener.
- Any **route rename** (New Deal → Add Target / Import Deal / Create Opportunity).

See `PEDESK_DEAL_WORKFLOW_MODEL.md` for the lifecycle and `PEDESK_ROUTE_TAXONOMY.md`
for the per-page data-universe classification.
