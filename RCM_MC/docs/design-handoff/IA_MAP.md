# IA Map — Editorial Topnav

**Branch:** `feat/ui-rework-v3`
**Status:** Phase 1 deliverable. Pre-Phase-2 sign-off.
**Source of truth for:** which existing navigation entries map into which of the 5 editorial topnav sections, and which are deprecated.

---

## The headline finding

**The pre-rework codebase had 219 nav entries** distributed across two constants:

- `_CORPUS_NAV` — 48 entries (the "active" nav, surfaced in the legacy sidebar)
- `_CORPUS_NAV_LEGACY` — 171 entries

The vast majority of `_CORPUS_NAV_LEGACY` appears to be aspirational / template placeholders — slugs like `/biosimilars`, `/cms-apm`, `/digital-front-door`, `/health-equity`, `/gpo-supply` that don't correspond to working modules. They are likely drift from a previous fund's nav template carried into this codebase and never pruned.

**This rework treats `_CORPUS_NAV_LEGACY` as dead code pending Phase 5 deletion.** The current rework's IA is built from `_CORPUS_NAV` (48 entries, of which ~30 map to working modules per the section assignments below).

Production navigation in real partner-facing tools has 15–30 destinations grouped into 4–6 sections. The pre-rework 219-entry nav was internally-incoherent and made the product harder to learn. Pruning to a working IA is itself a product clarity win, separate from the visual rework.

---

## The 5 editorial topnav sections

Per spec §6.1: `DEALS · ANALYSIS · PORTFOLIO · MARKET · TOOLS`.

| Section | Captures |
|---|---|
| **DEALS** | Single-deal lifecycle (sourcing → screening → profile → close → post-close → exit) |
| **ANALYSIS** | The diligence modules — analytic engines that answer one partner question each |
| **PORTFOLIO** | Multi-deal / fund-level (LP digest, attribution, hold management, fundraising) |
| **MARKET** | Public-tape / external context (comps, sector, regulatory, payer-side) |
| **TOOLS** | Utilities (library, methodology, audit, settings, admin) |

---

## A. Mapped destinations (canonical routes)

Every destination listed below has been verified as having a wired server-side route in `rcm_mc/server.py`. Routes that previously appeared as duplicates have been consolidated to a single canonical entry; legacy duplicates redirect (302) to the canonical in Phase 5.

### DEALS

| Topnav label | Canonical route | Notes |
|---|---|---|
| Sourcing | `/deal-screening` | The "find me hospitals" surface |
| Profile | `/diligence/deal` | Slug-input form (Phase 2 may reshape — see Open Questions) |
| Bankruptcy Survivor | `/screening/bankruptcy-survivor` | |
| Autopsy | `/diligence/deal-autopsy` | Pattern-match against 12 named historical PE failures |
| Import Deal | `/import` | (May fold into `/diligence/ingest` — see Open Question #14) |

### ANALYSIS

| Topnav label | Canonical route | Notes |
|---|---|---|
| Thesis Pipeline | `/diligence/thesis-pipeline` | Orchestrator, 19 steps |
| Checklist | `/diligence/checklist` | 40+ tasks across 5 phases |
| Ingestion | `/diligence/ingest` | |
| Benchmarks | `/diligence/benchmarks` | HFMA-band peer benchmarks |
| HCRIS X-Ray | `/diligence/hcris-xray` | 17,701 cost reports × 15 metrics |
| Root Cause | `/diligence/root-cause` | |
| Value Creation | `/diligence/value` | Analytic; `/value-creation-plan` is the operational tracker — kept separately under PORTFOLIO |
| Risk Workbench | `/diligence/risk-workbench` | |
| Counterfactual | `/diligence/counterfactual` | |
| Compare | `/diligence/compare` | |
| QoE Memo | `/diligence/qoe-memo` | (`/qoe-analyzer` was a duplicate — 302 here in Phase 5) |
| Denial Predict | `/diligence/denial-prediction` | |
| Physician Attrition | `/diligence/physician-attrition` | |
| Provider Economics | `/diligence/physician-eu` | |
| Management | `/diligence/management` | |
| Deal MC | `/diligence/deal-mc` | 1,500–3,000 trial Monte Carlo |
| Exit Timing | `/diligence/exit-timing` | (`/exit-timing` was the legacy duplicate — 302 here in Phase 5) |
| Reg Calendar | `/diligence/regulatory-calendar` | 11 curated CMS/OIG/FTC events |
| Covenant Stress | `/diligence/covenant-stress` | The MC. (`/covenant-headroom` was redundant — drop in Phase 5) |
| Bridge Audit | `/diligence/bridge-audit` | |
| Bear Case | `/diligence/bear-case` | |
| Payer Stress | `/diligence/payer-stress` | (See payer-page consolidation below) |
| IC Packet | `/diligence/ic-packet` | (`/ic-memo-gen`, `/corpus-ic-memo` were duplicates — 302 here) |
| PE Intelligence Hub | `/pe-intelligence` | Cross-cutting partner brain |
| Risk Matrix | `/risk-matrix` | (`/deal-risk-scores`, `/rcm-red-flags` redirect here) |
| Red-Flag Scanner | `/redflag-scanner` | (Catalog view; complements `/risk-matrix`) |
| Comparables | `/comparables` | (`/find-comps`, `/peer-valuation` redirect here) |

### PORTFOLIO

| Topnav label | Canonical route | Notes |
|---|---|---|
| Command center | `/app` | **Phase 2:** editorial dashboard scaffolded. **Phase 3 (2026-04-25):** functionally real — 8 of 9 blocks wired against live data; covenant heatmap is honestly partial (1 of 6 rows wired — see Q4.5). The block conventions (#1–#6 in `UI_REWORK_PLAN.md`) are load-bearing for future helpers. Editorial-only — legacy `?ui=v2` users 303 to `/dashboard` |
| Dashboard (current `/`) | `/dashboard` | Phase 4 will resolve `/` vs `/dashboard` vs `/home` — see Open Question #12 |
| Home | `/home` | Phase 4 cutover decision pending |
| Engagements | `/engagements` | Pending investigation — see Open Question #15 |
| Portfolio Analytics | `/portfolio-analytics` | |
| Covenant Monitor | `/covenant-monitor` | Operational view — distinct from the diligence-side `covenant-stress` MC |
| Value-Creation Plan | `/value-creation-plan` | The operational tracker. `/vcp-tracker` redirects here in Phase 5 |

### MARKET

| Topnav label | Canonical route | Notes |
|---|---|---|
| Market Intel | `/market-intel` | |
| Seeking Alpha | `/market-intel/seeking-alpha` | |
| Sponsor Track Record | `/sponsor-track-record` | |
| Payer Intelligence | `/payer-intelligence` | Hub for payer-side surfaces |
| Payer Contracts | `/payer-contracts` | TiC pricing detail |
| RCM Benchmarks | `/rcm-benchmarks` | |
| Corpus Backtest | `/corpus-backtest` | |

### TOOLS

| Topnav label | Canonical route | Notes |
|---|---|---|
| Library | `/library` | (Could also fit PORTFOLIO; defer to first real-use feedback) |
| Methodology | `/methodology` | |
| API Docs | `/api/docs` | |
| Module Index | `/module-index` | (Was duplicated — single canonical now) |
| Audit | `/audit` | |
| Data Admin | `/admin/data-sources` | |

---

## B. Direct duplicates resolved

These routes were redundant. Each row collapses N existing routes into 1 canonical. Phase 5 cleanup adds 302s on the non-canonical paths.

| # | Routes consolidated | Canonical | Reason |
|---|---|---|---|
| 1 | `/payer-intelligence` + `/payer-intel` + `/payer-stress` + `/payer-rate-trends` + `/payer-concentration` + `/payer-shift` + `/payer-contracts` | 3 surfaces: `/payer-intelligence` (hub), `/diligence/payer-stress` (MC), `/payer-contracts` (TiC pricing) | 7→3 |
| 2 | `/ic-memo-gen` + `/corpus-ic-memo` + `/diligence/ic-packet` | `/diligence/ic-packet` | 3→1 |
| 3 | `/diligence-checklist` + `/diligence/checklist` | `/diligence/checklist` | 2→1 |
| 4 | `/value-creation` + `/value-creation-plan` + `/diligence/value` + `/vcp-tracker` | 2 surfaces: `/diligence/value` (analytic), `/value-creation-plan` (tracker) | 4→2 |
| 5 | `/exit-timing` + `/diligence/exit-timing` | `/diligence/exit-timing` | 2→1 |
| 6 | `/comparables` + `/find-comps` + `/peer-valuation` | `/comparables` | 3→1 |
| 7 | `/risk-matrix` + `/deal-risk-scores` + `/rcm-red-flags` + `/redflag-scanner` | 2 surfaces: `/risk-matrix` (matrix), `/redflag-scanner` (catalog) | 4→2 |
| 8 | `/payer-stress` (top-level) + `/diligence/payer-stress` | `/diligence/payer-stress` | 2→1 (covered in #1) |
| 9 | `/covenant-stress` + `/covenant-monitor` + `/covenant-headroom` | 2 surfaces: `/diligence/covenant-stress` (MC), `/covenant-monitor` (ops). `/covenant-headroom` dropped | 3→2 |
| 10 | `/qoe-memo` + `/qoe-analyzer` | `/diligence/qoe-memo` | 2→1 |
| 11 | `/module-index` (in both `_CORPUS_NAV` AND `_CORPUS_NAV_LEGACY`) | Single `/module-index` | 2→1 |

**All 16 canonical destinations verified to have wired server routes** (grep on `rcm_mc/server.py` for `path == "/<route>"` or `path.startswith("/<route>")` returned a hit for each).

---

## C. Canonical destinations needing implementation

None at this time. All 16 canonicals listed in Section A above have server-side renderers. If a future canonical is proposed without a renderer, it lands here as a Phase 2/3 implementation gate.

---

## D. Open questions deferred to later phases

Four items surfaced during the IA pass that are real product decisions, not IA decisions. Each is captured here so we don't forget; each gets resolved in the phase named.

### #12 — `/` vs `/dashboard` vs `/home` (Phase 4 first decision)

The legacy codebase has all three. Spec §2 reroutes `/` → marketing landing in v3. **Risk:** rerouting `/` is a behavior change visible to every user. Bookmarks break. External monitors that hit `/` for an auth challenge see HTML instead. Partner muscle memory (years of typing the bare domain to get the dashboard) breaks.

**Resolution:** Phase 4's first open question. Cannot be deferred further. Required: explicit decision + a contract test (`test_authenticated_user_lands_on_dashboard_at_root`) before merge to `main`. See `UI_REWORK_PLAN.md` Phase 4 section.

**Update from Phase 2 (2026-04-26):** the editorial dashboard now lives at `/app` (Phase 2 keystone, commit `a3ad808`). Legacy `/dashboard` survives unchanged. Q4.1 is now specifically:

- Does `/` redirect to `/app` for authenticated v3 users?
- Does `/dashboard` 302 → `/app` for editorial requests, or stay as the legacy alias indefinitely?
- Editorial requests to `/app` already work (verified by `test_v3_app_route_renders_for_authenticated_user`); legacy requests to `/app` 303 to `/dashboard` (verified by `test_v3_app_legacy_request_redirects_to_dashboard`). The redirect is logged via `logger.info("redirect path=/app ui_choice=...")` so volume becomes a measurable Phase 4 input.

### #13 — `/diligence/deal` slug-input form (Phase 2 decision)

Spec §7.2 says this becomes "an editorial form card" with a single slug field. Today it's wired to display whatever deal is selected. **Question:** does the v3 surface stay a form-card entry point, or become `/app/deals` (a list of all deals)? Both have merit; depends on how partners actually navigate.

**Resolution:** Phase 2 deal-profile port. Don't decide now.

### #14 — `/import` vs spec's data-room concept (Phase 3 decision)

Spec doesn't mention `/import` explicitly. The codebase has `/import` (CSV/JSON bulk import) and `/diligence/ingest` (per-deal data ingestion). Could fold them.

**Resolution:** Phase 3 ingestion port. Don't decide now.

### #15 — `/engagements` (resolve before Phase 2)

Surface unknown. Not in the spec. Listed in `_CORPUS_NAV` but no obvious purpose from the route name alone.

**Resolution required before Phase 2 begins.** Action: visit `/engagements` on a running instance, identify what it does. If it's a real surface, decide where it goes in the topnav (likely PORTFOLIO). If it's dead code, drop it (route returns 410 in Phase 5).

If unanswered when Phase 2 starts, default to dropping.

---

## E. Section-placement edge cases

Two destinations sit on a section boundary. Both can be moved with a one-line PR if first-real-use feedback says they feel wrong.

- **`/library`** under TOOLS vs PORTFOLIO — currently TOOLS (it's a reference utility). Could fit PORTFOLIO as "all your fund's deals" if usage shows that's how partners think of it.
- **`/comparables`** under ANALYSIS — currently ANALYSIS (it's an analytic engine). Could fit TOOLS if usage shows partners reach for it as a quick lookup rather than as part of a structured diligence flow.

---

## What the topnav looks like in v3 (final)

```
DEALS              ANALYSIS              PORTFOLIO       MARKET                TOOLS
─────              ──────────            ──────────      ──────                ─────
Sourcing           Thesis Pipeline       Dashboard       Market Intel          Library
Profile            Checklist             Home            Seeking Alpha         Methodology
Bankruptcy         Ingestion             Engagements*    Sponsor Track Record  API Docs
  Survivor         Benchmarks            Portfolio       Payer Intelligence    Module Index
Autopsy            HCRIS X-Ray             Analytics     Payer Contracts       Audit
Import Deal*       Root Cause            Covenant        RCM Benchmarks        Data Admin
                   Value Creation          Monitor       Corpus Backtest
                   Risk Workbench        Value-Creation
                   Counterfactual          Plan
                   Compare
                   QoE Memo
                   Denial Predict
                   Physician Attrition
                   Provider Economics
                   Management
                   Deal MC
                   Exit Timing
                   Reg Calendar
                   Covenant Stress
                   Bridge Audit
                   Bear Case
                   Payer Stress
                   IC Packet
                   PE Intelligence Hub
                   Risk Matrix
                   Red-Flag Scanner
                   Comparables
```

`*` items are pending Open Questions (#13–#15).

---

## Phase 5 cleanup obligation

Before deleting `_CORPUS_NAV_LEGACY`, dump its 171 entries to:

  **`docs/design-handoff/legacy-nav-archive.md`**

with this header:

> *"These 171 nav entries existed in the pre-rework codebase. If you're looking for a destination that no longer appears in the topnav, search this archive — it may have been a real surface that was deprecated, or a placeholder that was never built. Removed in commit X of Phase 5."*

The archive preserves institutional memory at zero ongoing cost and makes the deletion safely reversible if anything breaks.

This step is mandatory before the Phase 5 commit that deletes the constant.
