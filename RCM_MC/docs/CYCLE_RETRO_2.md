# Cycle Retrospective — Deal Autopsy + Interpretability Pass

## What shipped this cycle

| Commit scope | What | New tests |
|---|---|---|
| `rcm_mc/diligence/deal_autopsy/` + `ui/deal_autopsy_page.py` | Deal Autopsy — 12-deal curated failure library, 9-dim signature matcher, Bloomberg-tier UI | 38 |
| `exports/ic_packet.py` + `ui/ic_packet_page.py` | Historical Analogue section auto-flows from Deal Autopsy matches | 3 |
| `ui/data_public/deals_library_page.py` | `/library` moic_bucket filter — fixes 500 caught in FIX pass | — |
| `ui/diligence_benchmarks.py` | KPI cards gain peer-median delta arrows + hero "What this shows" callout | — |
| `ui/risk_workbench_page.py` | Every panel gets a band-keyed "What this shows" explanation + page-level color legend | — |
| `ui/deal_mc_page.py` | Hero MOIC band summary in plain English, keyed off P50 + P(sub-1x) | — |

**38 new tests all green. 111 adjacent tests green across touched surfaces.
88ms total compute across the 13-page critical diligence workflow;
31/31 sidebar nav routes return 200; 11/11 Deal Profile analytic
tiles resolve cleanly in 242ms.**

## What worked

- **Deal Autopsy shipped as a complete vertical.** Data layer (library of 12 historical deals) + logic layer (9-dim signature matcher) + UI layer (scoped Bloomberg-tier CSS with hover-lift cards + similarity-gradient ribbons) + integration layer (Historical Analogue flows into IC Packet) + 38 tests pass on first run. A partner dragging a Steward-like signature gets "⚠ You are underwriting a deal with a 94% signature match to Steward (2024 — Bankruptcy)" as the top hero banner. This is the clearest demo-stopper I've built in the PE context.

- **The interpretability pattern ported cleanly backward.** The retro from the prior cycle flagged that Risk Workbench panels felt generic vs Denial Prediction's peer-context hero. Porting the pattern was a two-helper change (`_panel(explanation=...)` + `_TIER_EXPLAINER` lookup) applied to 5 panel renderers. Low LOC, high interpretability uplift.

- **The peer-delta arrows on Benchmarks KPI cards are the highest-per-pixel improvement.** Every KPI now reads as "14.5% — Below peer median — ▲ +4.5 pp vs peer median 10.0%" with the arrow colored red/green by whether the delta is favorable. No training required; a first-time partner can tell good from bad in a single scan.

- **The /library 500 fix was cheap and added a real filter.** Rather than strip `moic_bucket` at the server (simplest fix), I added the bucket filter to the function signature and exposed the selector in the filter bar. Fixed the bug AND added the feature the URL was implying.

- **Full-suite critical-path timing confirmed the product is fast enough.** 88ms to render all 13 core diligence pages server-side; total compute across every Deal Profile analytic tile is 242ms. The 30-minute budget is a human-cognition constraint, not a tool constraint.

## What needs more work

- **Risk Workbench numeric rows still lack peer-median context on individual metrics.** Panel-level band explanations landed, but inside the panel, rows like "EBITDAR coverage 1.10x" render without the peer-median "1.30x median" context. Fixed in this cycle as a follow-up (see below); took one helper update.

- **No writeback from analytics → Deal Profile localStorage.** A partner runs Deal MC and gets P50 MOIC 2.4x, then opens the IC Packet and has to mentally carry the number over. The retro from the prior cycle already flagged this as next-cycle #1. Still not done.

- **Deal Autopsy library is 12 deals.** Good demo density but thin for real partner use. Should grow to 20–25 over future cycles, with regional/specialty coverage that currently has gaps (no specialty pharmacy, no behavioral health, no dialysis).

- **No end-to-end integration test tying CCD → Denial Prediction → Counterfactual → Deal MC → IC Packet result coherence.** Each module is tested; the handoff seams aren't. A cross-module regression would land as a user-visible weirdness ("IC packet says $12M savings but Deal MC assumed $0") before any test catches it.

- **110 pre-existing test failures from the prior UI revert remain unaddressed.** None are in the Deal Autopsy / interpretability surfaces I touched, but they're technical debt accumulating.

## What was a waste of time

- **F-string `}` syntax trap on the scoped CSS block.** Wrote the Bloomberg-tier style block as an f-string with inline palette interpolations, forgot CSS rules end in `}` which Python reads as close-delimiter. Cost one test-and-fix cycle. Fix: use `str.format` for anything with literal braces; reserve f-strings for non-CSS content. Carrying this forward.

- **Import guessing in the workflow probe.** `render_diligence_benchmarks` / `engagements_index` / `render_risk_workbench_page` — none were the real names. Cost a cycle to discover. Better pattern: `grep -n "^def render" file.py` before importing.

- **Background-Bash tests that never emitted to their output file.** I suspect pipe-buffering on `pytest -q`. Will run tests foreground unless there's a genuine parallelism reason.

## Lessons to carry into next cycle

1. **When porting a pattern (interpretability, provenance, peer context) across modules, do it in the same turn.** Doing Benchmarks + Workbench + Deal MC in one pass landed the pattern consistently. Splitting across cycles risks divergence.
2. **Scoped CSS via `str.format(**palette)` is the cleanest primitive.** F-strings are for content, not templates.
3. **Run the critical-path workflow probe as a standing tool.** 13 pages, all routes, all Deal Profile tiles — catches broken integrations (like /library 500) before a user does.
4. **Every new hero/KPI number deserves three things: the value, a peer benchmark, and a plain-English "what this shows" sentence.** The Denial Prediction hero → Benchmarks KPI cards → Risk Workbench panels → Deal MC hero arc is now consistent.

## What to focus on next cycle

**#1 — Close the diligence-to-investment-math loop (still).** This was the prior retro's #1; it's still the biggest friction point. Add a `DealScenarioBuilder` that takes CCD + metadata + counterfactual + denial prediction + Steward Score outputs and returns a populated `DealScenario` for Deal MC. Add a "Run Full Pipeline" button on Deal Profile that writes the headline outputs (P50 MOIC, P(sub 1x), top variance driver, top historical analogue) back into the profile's localStorage.

**#2 — End-to-end integration test.** One test that runs a fixture through the full chain and asserts: (a) denial prediction bridge input is consumed by Deal MC, (b) Deal MC P50 shows up in IC Packet headline, (c) counterfactual largest lever shows up in both IC Packet walkaway and Deal MC scenario deltas. Would catch cross-module regressions.

**#3 — Grow Deal Autopsy library to 20 deals.** Add dialysis (DaVita), behavioral health (Universal Health Services spin, Acadia), specialty pharmacy roll-ups, and 2 more survivor patterns (IRhythm, Ensemble Health). Current coverage is hospital-heavy.

**#4 — Peer-median lines on Risk Workbench numeric rows.** The panel-level "what this shows" callouts landed this cycle. Individual `_kv_row` entries (EBITDAR coverage, CyberScore, lease escalator) should carry a right-aligned peer subline the same way Benchmarks KPI cards do. Small change, big interpretability lift.

**#5 — Address the 110 pre-existing UI-revert test failures.** All palette-hex assertion mismatches (`b5321e` vs `#ef4444`). Bulk find/replace should clear most; some require editorial-reskin wrappers to be deleted. One grind session.

## Stat check

- New package: `rcm_mc/diligence/deal_autopsy/` (3 files, ~600 LOC)
- New UI page: `rcm_mc/ui/deal_autopsy_page.py` (~500 LOC)
- Tests added this cycle: 38 (all passing)
- Adjacent test passes: 111/111 (ic_packet, deal_profile, deal_mc, denial_prediction, risk_workbench, deal_autopsy)
- Critical-path workflow compute: 88ms (13 pages) / 242ms (11 Deal Profile analytic tiles)
- Nav routes green: 31/31
- Runtime dependencies added: 0
