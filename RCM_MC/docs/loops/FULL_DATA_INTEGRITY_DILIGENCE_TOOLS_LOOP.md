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

## Next 5 actions
1. Build Phase 4 data-verification: page_data_source audit script + matrix docs.
2. Generate PAGE_DATA_SOURCE_AUDIT from surface_status + label scan.
3. Diligence page classification pass (extend surface_status coverage).
4. /tools per-tool audit table.
5. Continue dataset backlog (NPPES supply / Open Payments) per feasibility.

## Next wakeup
+180–300s while work remains.
