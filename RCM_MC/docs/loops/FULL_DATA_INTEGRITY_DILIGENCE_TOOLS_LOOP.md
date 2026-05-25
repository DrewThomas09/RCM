# Full Data Integrity + Diligence + Tools Loop

Active autonomous loop. Order: finish Industry → finish Market → data
verification → every Diligence page → every /tools page → more data → Guide/RAG.
Never pause after one task; if CI/deploy runs, do non-conflicting docs/tests/
audit work. Schedule next wakeup 180–300s while work remains.

## Current run
- loop_start:   2026-05-25T18:30Z
- last_tick:    2026-05-25T18:30Z
- main_sha:     4c96e2ed
- deploy:       healthy (/healthz 200)
- blocked?:     no

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

## Next wakeup
+180–300s while work remains (CI-watch re-invokes sooner).
