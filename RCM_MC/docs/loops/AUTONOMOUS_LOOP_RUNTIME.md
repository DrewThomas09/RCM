# Autonomous loop runtime control

Tick-driven control for the PEdesk Diligence/data/Guide build loop. **Every
active-loop turn must end by either (A) scheduling the next wakeup in 180-300s,
or (B) declaring loop_end reached with no safe work remaining.** Never a
30-minute heartbeat during an active loop. (Prior failure: a 6h18m gap because
no wakeup was scheduled — fixed by this self-rescheduling rule.)

## Current run
- loop_start:      2026-05-25T14:20Z
- loop_end:        2026-05-25T22:20Z   (loop_start + 8h)
- last_tick:       2026-05-25T15:10Z
- next_tick_due:   +180s after each turn
- last_deploy_sha: e03da5f1  (/healthz 200)
- active PRs:      quality-scorecard CMS star benchmark (opening)

## Done this run (worst-first RED→NAVY conversions, real-data-anchored)
- #710 Physician Productivity: real HRSA shortage context; RED→NAVY. (deployed)
- #711 Provider Retention: real CMS nurse-turnover benchmark (median 45.3%);
  RED→NAVY; At-Risk Watchlist labeled illustrative scaffold. (deployed)
- (this tick) Quality Scorecard: real CMS 5-star Care Compare distribution
  (overall 3.01★); RED→NAVY.

## Queue (next 5 actions)
1. Merge quality-scorecard PR (green) + deploy-verify.
2. Audit Deal Quality / Deal Risk for real HCRIS-distress / CMS signals vs honest labels.
3. Next RED page with a real anchor (clinical-outcomes / patient-experience via
   Care Compare; ma-star / risk-adjustment via CMS MA Star Ratings).
4. Keep Partner Economics + Mgmt Comp RED (no public anchor for comp; honest
   illustrative labels already present) — revisit only if real comp data attached.
5. Guide/RAG source cards + coverage-matrix updates for each change.

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
