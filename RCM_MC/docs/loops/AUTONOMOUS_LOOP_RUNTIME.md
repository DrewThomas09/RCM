# Autonomous loop runtime control

Tick-driven control for the PEdesk Diligence/data/Guide build loop. **Every
active-loop turn must end by either (A) scheduling the next wakeup in 180-300s,
or (B) declaring loop_end reached with no safe work remaining.** Never a
30-minute heartbeat during an active loop. (Prior failure: a 6h18m gap because
no wakeup was scheduled — fixed by this self-rescheduling rule.)

## Current run
- loop_start:      2026-05-25T14:20Z
- loop_end:        2026-05-25T22:20Z   (loop_start + 8h)
- last_tick:       2026-05-25T15:45Z
- next_tick_due:   +180s after each turn
- last_deploy_sha: ff0dba0b  (/healthz 200)
- active PRs:      coverage-matrix + MIPS RAG card docs (opening)

## Done this run (worst-first RED→NAVY conversions, real-data-anchored)
- #710 Physician Productivity: real HRSA shortage + CMS MIPS quality. RED→NAVY.
- #711 Provider Retention: real CMS nurse-turnover (median 45.3%). RED→NAVY.
- #712 Quality Scorecard: real CMS 5-star Care Compare (3.01★). RED→NAVY.
- #713 Clinical Outcomes: real CMS quality-measure (3.65★). RED→NAVY.
- #714 Onboard CMS MIPS physician-quality dataset (541k → PII-free aggregates).
- #715 Sector-aware quality benchmark (MIPS for physician sectors, SNF for nursing).
- #716 Regulatory Risk: real CMS enforcement base rate (45% fined, $467M). RED→NAVY.
- (this tick) Generated coverage-matrix doc + MIPS RAG source card.
- Surface counts now: red 72, yellow 56, navy 62, green 143 (of 333 live).

## Queue (next 5 actions)
1. Merge coverage-matrix/RAG docs PR (green) + deploy-verify.
2. Audit Deal Quality / Deal Risk (yellow) for real HCRIS-distress / CMS signals.
3. Remaining RED pages with a real anchor (e.g. supply-chain via FDA shortage).
4. Keep Partner Economics + Mgmt Comp RED (no public comp anchor) — honest labels.
5. Onboard next public dataset (CMS Open Payments / price-transparency MRFs).

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
