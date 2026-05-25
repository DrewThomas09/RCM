# Autonomous loop runtime control

Tick-driven control for the PEdesk Diligence/data/Guide build loop. **Every
active-loop turn must end by either (A) scheduling the next wakeup in 180-300s,
or (B) declaring loop_end reached with no safe work remaining.** Never a
30-minute heartbeat during an active loop. (Prior failure: a 6h18m gap because
no wakeup was scheduled — fixed by this self-rescheduling rule.)

## Current run
- loop_start:      2026-05-25T14:20Z
- loop_end:        2026-05-25T22:20Z   (loop_start + 8h)
- last_tick:       2026-05-25T17:10Z
- next_tick_due:   +180s after each turn
- last_deploy_sha: da60d52d  (/healthz 200)
- active PRs:      esg honesty-label (opening)

## Done this run (all merged + deployed)
- #710-713 RED→NAVY: Physician Productivity (HRSA+MIPS), Provider Retention
  (CMS turnover 45.3%), Quality Scorecard (CMS 5-star 3.01★), Clinical Outcomes
  (CMS QM 3.65★).
- #714 Onboard CMS MIPS dataset (541k → PII-free aggregates).
- #715 Sector-aware quality benchmark (MIPS physician / SNF nursing).
- #716 Regulatory Risk RED→NAVY (CMS enforcement 45% fined, $467M).
- #717 Generated surface-status doc (gen script) + MIPS RAG card + coverage matrix.
- #718 Deal Quality + Deal Risk honest illustrative banners (stay yellow).
- #719 Supply Chain RED→NAVY (FDA drug shortage, 1,156 active).
- #720-724 INDUSTRY INTELLIGENCE LAYER (licensed IBISWorld, derived only):
  audit+policy, extractor+data+loader, /industry pages, RAG card, brief builder.
- #725 Payer Shift RED→NAVY (CIVHC payer-mix trend).
- (this tick) ESG dashboard honest illustrative banner.
- Surface counts now: red 70, yellow 56, navy 64, green 144 (of 334 live).

## Honest state of the conversion
Cleanly-anchorable RED calculators (vendored data) are converted. Remaining RED
splits into: (a) genuinely synthetic dashboards with NO public source (esg,
litigation, cyber, key-person, mgmt-comp, partner-economics, board-governance,
hcit, telehealth-econ) — correct to STAY RED with honest illustrative labels;
(b) pages needing a NEW dataset.

## Queue (next 5 actions)
1. Onboard CMS MA Star Ratings (Excel on cms.gov, multi-sheet) → unlocks
   ma-star / ma-contracts / risk-adjustment. Fresh full-budget tick.
2. FDA biosimilar approvals dataset → biosimilars page.
3. CMS Open Payments (industry→physician payments) → conflicts pages.
4. Verify all remaining RED dashboards carry ck_illustrative_note (sweep).
5. Wire industry_intel as anchor where genuinely relevant (hospital/physician
   market-structure pages).

## Per-tick rule
Until loop_end, each tick does >=1 concrete action (merge / fix / open PR / tests
/ wire dataset / Guide doc / coverage matrix / profile dataset / source-status
improvement / deploy-verify). While CI/deploy runs, work a non-conflicting
docs/tests/Guide/profile branch — never idle. Then ScheduleWakeup 180s (300s if
a deploy is mid-flight). Stop only at loop_end, broken-unfixable deploy,
forbidden scope, or all safe work complete.

## Forbidden scope
login/auth/session · Caddy · systemd · deploy workflow · secrets ·
.pedesk_prod.env · Ollama/Tailscale · RAG runtime · #579/#580.

## Auto-merge scope (green + mergeable, no approval)
honesty labels · source/purpose headers · illustrative demotions · real-data
Diligence conversions (public/already-ingested data) · public dataset
profiles/loaders/tests (clear license) · Guide/RAG docs · tests · coverage
matrices · ledger updates · small Diligence UI integration.
