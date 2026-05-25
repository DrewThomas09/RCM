# Full Data Integrity + Diligence + Tools Loop

Active autonomous loop. Order: finish Industry → finish Market → data
verification → every Diligence page → every /tools page → more data → Guide/RAG.
Never pause after one task; if CI/deploy runs, do non-conflicting docs/tests/
audit work. Schedule next wakeup 180–300s while work remains.

## Current run
- loop_start:   2026-05-25T18:30Z
- last_tick:    2026-05-25T19:25Z
- main_sha:     6d2deaed
- deploy:       healthy (/healthz 200)
- blocked?:     no
- status:       **TRUE IDLE on high-value work** (see determination below)

## TRUE IDLE determination (2026-05-25T19:25Z)
Across every loop axis, the high-value work is complete; what remains is
low-value busywork or blocked-by-size/portal:
- Open PRs to merge/fix: none in scope (only parked #579/#580).
- Datasets to profile: feasible high-value ones onboarded; remainder
  (Open Payments, NPPES, price-transparency) are large/separate-portal —
  documented blockers, need a staged ingest or user go-ahead; group MIPS marginal.
- Tools pages: audited + 100% disclosed (0 undisclosed data pages; regression-guarded).
- Diligence pages: cleanly-anchorable calculators converted (12 RED→NAVY);
  rest lack a real public anchor (need user/deal data).
- Guide docs: all important analytic/data/LIVE pages documented; the ~83
  remaining "gaps" are workflow/admin routes (/activity, /audit, /cohorts,
  /dashboard, …) where inferred context is adequate — manual stubs = busywork.
- Validators: page data-source audit + regression test + tier doc all current.
- Market/Industry: built, enriched, cross-linked, Guide-documented.
Therefore: scaling cadence back to a long heartbeat. Will resume active 180–300s
cadence immediately on a new data drop, a new in-scope PR, a CI/deploy failure,
or explicit user direction.

## This run's merged PRs (#742–#751, all deployed, prod healthy)
SNF CHOW · market profile KPIs · Hospital CHOW · integrity refresh · Guide ctx
(market/industry) · deal-flow real consolidation · Guide ctx (9 Diligence) ·
market opportunity ranking · industry→market cross-links · Guide ctx (3 LIVE).

## Open-PR inventory (Phase 1)
| PR | Title | Class | Action |
|---|---|---|---|
| #639 | command-center canvas bg | visible UI (not mine, 05-24) | HOLD — verify vs current main before any merge; not in this loop's scope |
| #580 | tool status dots | FORBIDDEN (parked) | leave |
| #579 | product-quality loop | FORBIDDEN (parked) | leave |
| #25,#19,#18,#17,#6 | old Apr/early-May PRs | stale, pre-session | HOLD — closing others' PRs needs user call |

No safe in-scope green PRs of mine open (this session's #710–734 all merged).

## Phase status
- Phase 2 Industry Intelligence: COMPLETE (#720–724) — verify checklist below.
- Phase 3 Market Intelligence: COMPLETE (#730–734) — verify checklist below.
- Phase 4 Data verification layer: IN PROGRESS (new).
- Phase 5 Diligence page-by-page: pending (12 RED→NAVY done this session; full classification next).
- Phase 6 /tools audit: partial (surface_status taxonomy + generated doc exist; deepen per-tool).
- Phase 7 Guide/RAG: ongoing.

## Data sources live (this build)
CMS HCRIS, CMS Care Compare (SNF turnover/ratings/enforcement), CMS MIPS,
CMS MA Geographic Variation, CIVHC (CO payer/APM/RBP), openFDA drug shortages,
CMS MSSP ACO, HRSA HPSA, licensed IBISWorld (industry, derived),
licensed SimplyAnalytics (market, derived).

## Progress
- #735 Phase 4 data-verification framework — merged + deployed (01172dac). 35 flagged.
- #736 /tools route audit (335) + disclosed 6 pages — merged + deployed (876ada7b). 35→29.
- #737 disclosure batch 2: 14 more seed-corpus pages disclosed — open. 29→15.
- Remaining 15 flagged: 7 GREEN real/admin (not synthetic) + 8 NAVY calculators
  needing ck_source_purpose headers (batch 3 next).

## Disclosure milestone
Undisclosed data pages driven **35 → 0** across batches #736–#739. Every data
page now discloses (real-source / illustrative / benchmark-corpus / data-required),
guarded by a regression test with an EMPTY backlog.

## Next 5 actions
1. Phase 8 dataset: onboard CMS FFS Provider Enrollment → provider-supply
   counts by state × provider_type (aggregate, drop PII). URL confirmed:
   data.cms.gov PPEF_Enrollment_Extract_2026.04.01.csv. Lights up the
   market-intel provider-supply (621111-style) backlog + real supply density.
2. Wire provider supply into market-intel + a diligence page.
3. Deeper Diligence per-page classification (use the tools route audit).
4. Guide/RAG source card for provider supply.
5. Next dataset (Open Payments / NPPES taxonomy if size feasible).

## Dataset-feasibility findings (override Wave 3; document blocker, move on)
- DONE this run: CMS FFS Provider Enrollment (supply), CMS SNF CHOW, CMS Hospital
  CHOW — all real, small aggregates, wired to market context + opportunity ranking.
- BLOCKED (large / separate portal — documented, deferred, not stopped):
  - Open Payments — openpaymentsdata.cms.gov, GB-scale annual zips; not in the
    data.cms.gov opendata API. Needs a staged large-file ingest; deferred.
  - NPPES full file (~1GB+) — deferred (size); MSSP/HRSA/MIPS cover the
    provider/quality need for now.
  - CMS price-transparency MRFs — huge, per-hospital; deferred.
- MARGINAL (lower value vs existing): PY2023 Group MIPS is measures/attestations
  only (no overall score); clinician overall MIPS already onboarded. Skipped.
- Net: the high-value, cleanly-feasible public-dataset queue is largely
  exhausted; remaining candidates are large-download/separate-portal or marginal.

## Recent waves (this run)
#742 SNF CHOW · #743 profile KPIs · #744 Hospital CHOW · #745 integrity refresh ·
#746 Guide ctx (market/industry) · #747 deal-flow real consolidation ·
#748 Guide ctx (9 converted Diligence) · #749 market opportunity ranking ·
(this) industry→market cross-links + dataset-feasibility findings.

## Session 2026-05-25 PRODUCT-READINESS mode (PRs #801–#812; RED 43→1)
User: switch from public-data conversion to product-readiness — convert
anchorless RED pages to honest DATA REQUIRED states (not fabricated anchors).
Delivered: new `data_required` surface tier (🟣) + shared `data_required_panel`
(needed fields + import template + request-from + once-activated; no fake
values) → `docs/reports/RED_PAGE_ACTIVATION_PLAN.md` (43 routes triaged) → 35
schema-only import templates in `docs/import_templates/` → 42 pages converted
RED→DATA REQUIRED (batches 1a/1b/1c/2/3/4) → 42 DOCUMENTED Guide contexts
(what-to-upload/who-to-ask; Guide DOCUMENTED 107→149) → panel template links to
`/import`. Validators: activation-plan, import-templates, panel-presence,
guide-context. Only `/ma-star` stays RED (DEFERRED WITH REASON — CMS Star
Ratings is zip-portal only; page carries a "REAL DATA DEFERRED" note).
**RED 43→1, DATA REQUIRED 0→42.** All merged & deployed, prod healthy.

## Session 2026-05-25 cont. (PRs #793–#799; RED 51→43)
After user "continue getting rid of synthetic data" directive: 6 NEW public-data
pipelines + conversions. CMS Part D Spending by Drug (#793) → drug-pricing-340b,
+reuse tracker-340b (#794) + biosimilars (#796). ClinicalTrials.gov v2 (#795) →
trial-site-econ. ESG pages ← CDC PLACES community-health via shared
community_health_panel (#797). physician-attrition ← HRSA (#798). OIG LEIE
exclusions (PII-dropped) (#799) → fraud-detection. Each: committed PII-free
aggregate + lru_cache loader + registry + test + Guide source + LIVE-panel
regression-guard entry (tests/test_live_data_panels.py).
**Genuine public-data anchors now EXHAUSTED at RED ~43** — remainder are
anchorless internal PE-fund ops / comp / governance / PMI / tech / insurance /
RE / RCM-denials (need the user's own deal/fund data) + ma-star (zip-portal,
deferred). Do NOT fabricate anchors for these.

## Session 2026-05-25 (PRs #767–#786, all merged & deployed; RED 68→51)
Topbar mega-menu layout fix #771 (BLOCKED: needs user screenshot to verify).
RED→NAVY conversions (real LIVE panel + honest illustrative caveat + retier):
provider-network/concentration-risk/msa-concentration/payer-concentration/
competitive-intel/gpo-supply/risk-adjustment(retier)/medicaid-unwinding/
payer-contracts/health-equity/telehealth-econ/patient-experience/locum-tracker/
workforce-retention/antitrust-screener/cin-analyzer/nsa-tracker.
NEW data pipelines: CDC PLACES SDOH (#777), CMS HCAHPS (#780), Census/ACS-via-CHR
county demographics (#781). Market panel now 5 real layers (supply/CHOW/MA/SDOH/
demographics). CLEAN CONVERSIONS EXHAUSTED — remaining ~51 RED are anchorless
internal/financial/governance/tech/drug/RE. NEXT: Guide DATA_SOURCE_REGISTRY does
NOT yet include the new sources (HCAHPS/PLACES/CHR/HRSA/CHOW/MSSP) — register them
+ promote converted pages to DOCUMENTED Guide contexts; then CMS ownership profile.

## Next wakeup
+180–300s while work remains (CI-watch re-invokes sooner).
