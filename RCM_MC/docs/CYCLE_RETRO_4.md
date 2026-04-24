# Cycle Retrospective — Interpretability + Seeking Alpha + Mgmt + Exit Timing + UX

## What shipped this cycle

| Area | New capability | New tests |
|---|---|---|
| Interpretability pass | Counterfactual feasibility explainers · Deal MC chart how-to-read panels (5 charts) · Risk Workbench regulatory + MA V28 peer context · Compare page delta narrative | 9 |
| Deal Profile redesign | Thesis Snapshot card (live KPI tiles + capital-structure bar + auto-thesis) · Diligence Lifecycle ribbon · Phase-grouped analytic tiles (Workspace/Screening/Diligence/Risk/Financial/Delivery) · Bookmark hint + JSON export | 12 |
| `/home` empty-state | "Try the tool" quickstart with 4 demo-fixture cards + one-click Run-Pipeline CTAs | 1 |
| Deal MC pipeline hydration | `?from_pipeline=<fixture>` auto-runs ThesisPipeline and populates DealScenario | 2 |
| Seeking Alpha integration | `PeerSnapshot` dataclass + `/api/market-intel/peer-snapshot` JSON endpoint · Deal Profile live Market Context block · News feed 10→23 items · Upcoming-earnings calendar | 15 |
| Management Scorecard | New `rcm_mc/diligence/management_scorecard/` package · Forecast reliability × comp × tenure × prior-role scorer · 4-exec demo · guidance-haircut bridge lever · IC packet section · interpretability polish | 30 |
| Exit Timing + Buyer-Type Fit | New `rcm_mc/diligence/exit_timing/` package · IRR × MOIC curve · buyer-fit radar · 4 playbooks · recommendation math · IC packet section · Thesis Pipeline step 13 · interpretability polish | 24 |
| Recent Deals landing | localStorage-driven grid of saved profiles on `/diligence/deal` with Open/Duplicate/Delete actions | 5 |

**98 new tests this cycle. 430/430 green across the adjacent surface. Zero new runtime dependencies.**

## What worked

- **Management Scorecard + Exit Timing are the two strongest shipments this cycle.** Both answer questions partners ask every deal and neither had a systematic tool before. Management Scorecard turns "will this team hit their forecast?" into a scored + partner-readable envelope with a direct EBITDA-bridge haircut recommendation. Exit Timing turns "when + to whom?" into an IRR/MOIC curve with buyer-fit radar. These extend the product beyond the diligence phase into the actual decision math.

- **The interpretability pattern has reached saturation in a good way.** Every numeric-heavy page now carries: a "What this shows" callout, peer benchmark context inline, color-banded numbers, a "How to read" panel on complex charts, and a score-band legend on 0–100 metrics. A first-time partner can read any page top-to-bottom without training. The cross-page consistency (0-40 red / 40-70 amber / 70-100 green) reinforces the mental model.

- **Recent Deals landing was the cheapest high-leverage UX win this session.** ~150 LOC of inline JS turned the blank slug-picker into a "continue where you left off" landing. Compound effect: every prior Deal Profile polish (thesis snapshot, lifecycle ribbon, pipeline CTA) became return-visit-friendly.

- **Seeking Alpha integration became load-bearing across the product.** Before this cycle, `market_intel` was an island — only the Market Intel page used the curated data. Adding `peer_snapshot` + the JSON endpoint + the Deal Profile live Market Context block made peer comparisons appear on every target-aware surface, matching the user's explicit ask.

- **ThesisPipeline is now a 14-step orchestrator** (added EU Analyzer step 8b and Exit Timing step 13). Every new analytic that ships gets plugged into the one-button full-diligence chain automatically.

## What needs more work

- **Exit Timing pipeline integration extrapolates years 6-7 with a 4% EBITDA growth pad.** Deal MC's default `hold_years=5` returns 6 bands (Y0-Y5). The orchestrator pads to year 8 with a hardcoded growth rate. Real data stops at year 5 but the exit curve shows years 2-7. Partners see curve points for years 6-7 that are built on extrapolation, not MC simulation. Fixed this turn — see below.

- **Demo-only surfaces (Management Scorecard, Provider Economics, PPAM).** The roster + executive data is hardcoded in the page renderer. Partners can't edit their own team / provider data without modifying Python. This is the biggest remaining "can't actually use the tool on a real deal" friction. Next cycle candidate.

- **Deal Autopsy library still 12 deals.** Retro #2 and #3 flagged growth to 20. Not done. Specialty coverage gaps remain (dialysis, behavioral health, spec pharmacy).

- **No cross-module coherence test.** Three retros flagged it; still undone. A single test that runs the pipeline end-to-end and asserts that IC Packet headline numbers match Deal MC's P50 match Deal Profile's localStorage writeback would catch handoff-seam regressions before a user does.

- **110 pre-existing UI-revert palette test failures remain.** Technical debt since the editorial-reskin revert. Bulk find/replace would clear most.

- **Exit Timing page isn't cross-linked FROM Deal MC.** An analyst running Deal MC would naturally ask "what's the optimal exit?" but there's no "Open in Exit Timing" button on the Deal MC page. Fixed this turn — see below.

## What was a waste of time

- **Two test-fail cycles from dataclass attribute assumptions.** YearBand has `.p50` not `.median`; Management Scorecard label `"Physician P&L"` gets HTML-escaped to `"Physician P&amp;L"`. Both cost me a test-and-fix round. Lesson: `grep` the dataclass before writing assertions; use labels without reserved HTML characters.

- **The `/home` quickstart wire-in was into `home_v2.py` first before I realized the route actually renders `chartis/home_page.py`.** Carried the lesson from a prior retro but didn't apply it fast enough. Lesson reinforced: always read the route handler's import chain before editing a "home" file.

- **First cut of Exit Timing recommendation ranking used probability-weighted proceeds as the primary sort.** Rewarded long holds and recommended sponsor-hold-extension as #1. Had to swap to probability-weighted IRR with a MOIC ≥ 1.5x filter. Lesson: partner-facing math needs to match what partners actually optimize (IRR for fund returns), not what's easiest to compute ($).

## Lessons to carry into next cycle

1. **Before wiring a new analytic into the Thesis Pipeline, read the actual dataclass fields used by the upstream step.** Assumptions about attribute names cost a test cycle every time.
2. **Any partner-facing ranking math must rank on the metric partners actually optimize.** IRR, not absolute dollars. Probability-weighted, not best-case. Partners push back instantly when you rank the wrong way.
3. **HTML-reserved characters in UI labels silently break substring assertions.** Use plain labels ("Provider Economics", "Management Scorecard") not ones with `&`, `<`, `>`.
4. **Universal UI patterns (score bands, how-to-read, provenance) pay back over many cycles.** Apply them by default on new pages rather than waiting for an interpretability pass.

## What to focus on next cycle

**#1 — Partner-editable Management + PPAM + Provider Economics data.** Currently demo-only. Build a simple "Paste CSV" or "Edit inline" flow so a VP can enter the real target's exec team / provider roster and get scored output on their actual deal. Without this, the tool is a persuasive demo but not a working instrument.

**#2 — Deal Autopsy library 12 → 20 deals.** Three retros flagged. Add dialysis (DaVita Labcorp spin), behavioral health (Acadia), specialty pharmacy roll-ups, 2 more survivors. 1-hour grind; closes a real coverage gap.

**#3 — Cross-module coherence integration test.** One test running the pipeline end-to-end + asserting IC Packet headline numbers match Deal MC P50 match localStorage writeback. Would catch regressions that slip through per-module tests.

**#4 — 110 pre-existing UI-revert palette test failures.** Bulk find/replace + delete dead editorial-reskin wrappers. Restores the full test suite to green.

**#5 — Value Creation Plan (VCP) tracker.** Post-close loop closure. Retro #3 flagged; still undone. Mirror of the Diligence Checklist pattern for post-acquisition tracking.

## Stat check

- New packages: 2 (`management_scorecard`, `exit_timing`) + 1 new API endpoint
- New UI pages: 2 (`/diligence/management`, `/diligence/exit-timing`) + enhanced Deal Profile landing
- Cycle test count: +98 (covering interpretability, Management Scorecard, Exit Timing, Peer Snapshot, news feed, earnings calendar, Recent Deals, Deal Profile visual upgrade)
- Adjacent test passes: 430/430 green
- Sidebar nav routes green: 37/37
- Deal Profile analytic tiles: 15 (up from 13)
- Thesis Pipeline: 14 steps (up from 13) — Exit Timing added
- IC Packet sections: 16+ (up from 15) — Management Scorecard + Exit Strategy added
- Runtime dependencies added: 0
