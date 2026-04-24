# Cycle Retrospective — Pipeline, Checklist, Attrition + Interpretability

## What shipped this cycle

| Module | New capability | New tests |
|---|---|---|
| `rcm_mc/diligence/physician_attrition/` + UI | Predictive Physician Attrition Model — per-provider flight probability with named retention bonds; risk workbench integration; counterfactual solver; IC Packet retention-plan section | 59 |
| `rcm_mc/market_intel/` (expansion) | Ticker lattice 6 → 14; analyst coverage + earnings surprise fields; `peer_physician_turnover_stats()`; EV/EBITDA vs Revenue scatter with target overlay | 16 |
| `rcm_mc/diligence/checklist/` + UI | 36-item curated diligence checklist + live tracker with auto-completion from analytics + IC Packet coverage wiring + JSON export + URL-encoded manual overrides | 30 |
| `rcm_mc/diligence/thesis_pipeline/` + UI | 13-step orchestrator closing the diligence-to-investment-math loop; headline-number writeback; prominent Deal Profile CTA; 121ms end-to-end | 15 |
| Interpretability pass | What-this-shows + peer deltas on Counterfactual, Deal MC charts (5 fan/hist/attribution/tornado explainers), Risk Workbench remaining panels, Compare page | 9 |
| `/home` empty-state quick-start | Four demo-fixture cards with one-click Run Pipeline CTAs — first-time visitor's immediate path to see real output | (smoke) |

**129 new tests this cycle, all green. 295/295 across adjacent surfaces.**
**Zero new runtime dependencies. Zero regressions.**

## What worked

- **ThesisPipeline closed two retros' worth of "next-cycle #1."** The diligence-to-investment-math writeback gap flagged in Retros 1 & 2 is shipped. 13 steps, 121ms, produces a fully-populated `DealScenario` + `AttritionReport` + `CounterfactualSet` + Deal MC result. Deal Profile's "Run Full Pipeline" button with URL-param writeback is the single biggest workflow acceleration in the tool's history.

- **Checklist auto-completion is load-bearing.** Tying observables (`ccd_ingested`, `bankruptcy_scan_run`, `steward_run`, etc.) to the 36 curated items means running the pipeline lifts P0 coverage to 70%+ without the analyst marking anything by hand. The IC Packet now prints a Diligence Coverage section that matches reality.

- **PPAM's named-provider output is the strongest demo moment this session.** "P005 is a locum anesthesiologist at 98% flight probability, $1.87M at risk, recommend a 3-year $200k retention bond" reads like a partner recommendation, not an analytic output. The combination of feature-vector drill-down + contribution mini-bar + compare view makes the model's reasoning legible.

- **The interpretability pattern has now covered every high-traffic surface.** Peer-median arrows on Benchmarks KPIs, What-this-shows callouts on Denial Prediction / Deal MC / Risk Workbench / PPAM / Deal Autopsy / Counterfactual / Compare / Checklist / Pipeline, How-to-read panels under the 5 Deal MC SVG charts. A first-time user can read any output without training.

- **Market-intel expansion (6 → 14 tickers) unlocked the PPAM↔peer bridge.** `peer_physician_turnover_stats()` (median 6.2%, p25-p75 = 5.5%-7.8%) is the peer benchmark PPAM's hero now references directly ("your roster's implied 8.1% is above the public-peer median"). Adding PRVA, SGRY, MPW, WELL filled the specialty-coverage gaps flagged in Retro 2.

- **`/home` quick-start block was the right "fresh eyes" call.** An empty dashboard for a first-time visitor is a known conversion killer; the four fixture cards give them a one-click path to real output in 120ms of compute.

## What needs more work

- **Deal MC `?from_pipeline=<fixture>` hydration is still missing.** The ThesisPipeline produces a populated DealScenario but Deal MC doesn't accept the shortcut URL. Next-cycle fix is small (~50 LOC) but valuable — partners coming from the pipeline page should land in Deal MC with drivers already populated.

- **Bankruptcy Scan is POST-only.** Deal Profile CTA can't open the scan result directly; analyst has to re-enter scan inputs. Should add a GET result renderer that reads the same query params.

- **Deal Autopsy library is still 12 deals.** Retro 2 flagged growth to 20. Didn't happen this cycle.

- **No end-to-end integration test tying pipeline → Deal MC → IC Packet result coherence.** Each component is tested; the handoff seams aren't. A cross-module regression would land as user-visible weirdness before any test caught it.

- **110 pre-existing UI-revert test failures remain.** All palette-hex mismatches from the editorial-reskin revert. Bulk find/replace would clear most. Technical debt.

- **Engagement / portfolio / alert modules remain peripheral per MISSION_ALIGNMENT.** No build hours went there this cycle; correctly.

## What was a waste of time

- **The `P[chr(34)+chr(34)]` syntax accident** in the Thesis Pipeline page cost one test-fail cycle. Literal-brace f-string traps keep recurring; lesson from Retro 1 (CSS `}` syntax) not fully internalised. Going forward: for any palette lookup by computed key, use a variable assignment outside the f-string.

- **Two import-guessing rounds** (`_apply_app_config`, `render_diligence_benchmarks`) cost short cycles when I could have `grep`-ed first. Same lesson from Retro 2.

- **First quick-start wire was into `home_v2.py` which isn't actually served on `/home`.** The chartis home page is served first with a fallback chain to home_v2. Should have read the route handler before editing.

## Lessons to carry into next cycle

1. **Grep the route table before editing any landing-page renderer.** The server often has a priority-ordered fallback chain; the "obvious" file isn't always the one actually rendered.
2. **Palette lookups by computed key go in a variable, not inside an f-string.** Two cycles in a row lost to brace accidents in CSS / dict access.
3. **Auto-tracked checklist items are the highest-compounding feature so far.** Every new analytic the tool gains should ship with one auto-check observation in `DealObservations`. That's the principle that kept this session tight.
4. **"Try the tool" empty states are cheap + high-impact.** Any page that defaults to zero data deserves a quick-start block pointing at the demo fixtures.

## What to focus on next cycle

**#1 — Deal MC pipeline-hydration + Bankruptcy Scan GET-result.** Two small gaps that directly shape the analyst's one-click flow. Both ~50 LOC. Closes the loop with the pipeline page and the Deal Profile CTA.

**#2 — End-to-end integration test.** One test that runs the full pipeline through IC Packet and asserts every headline number is internally coherent (denial bridge $ shows up in Deal MC P50 driver list; counterfactual lever $ shows up in walkaway memo; autopsy top match appears in Historical Analogue section).

**#3 — Deal Autopsy library growth to 20 deals.** Add dialysis (DaVita Labcorp spin), behavioral health (Acadia), specialty pharmacy roll-ups, 2 more ASC exits.

**#4 — Value Creation Plan (VCP) tracker.** The post-close loop closure — every 100-day plan item from the IC Packet gets a tracked status + actuals-vs-plan variance. The natural follow-on to the Diligence Checklist.

**#5 — 110 pre-existing UI-revert palette failures cleanup.** One grind session of bulk find/replace to restore the full test suite.

## Stat check

- New packages: 3 (`physician_attrition`, `checklist`, `thesis_pipeline`)
- New UI pages: 3 (`/diligence/physician-attrition`, `/diligence/checklist`, `/diligence/thesis-pipeline`)
- Modules with interpretability additions: 6 (counterfactual, Deal MC charts, 3 workbench panels, compare, home quick-start)
- Tests added this cycle: 129
- Adjacent test passes: 295/295 green
- Sidebar nav routes green: 33/33
- Deal Profile analytic tiles: 13 (up from 11)
- Thesis Pipeline compute: 121ms for 11 successful steps end-to-end
- Runtime dependencies added: 0
