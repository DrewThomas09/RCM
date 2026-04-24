# Cycle Retrospective — Recent Build Batch

## What shipped this cycle

Six commits, in order:

| Commit | What | New tests |
|---|---|---|
| `664c14c` | Power UI bundle + Compare page | 13 |
| `e2ff066` | Market Intel (public comps + transaction multiples + news feed) | 22 |
| `47f0e33` | IC Packet Assembler (one-click IC deliverable) | 11 |
| `d0a7477` | Deal Monte Carlo (5-year forward distribution + attribution + stress) | 20 |
| `aa0e5a0` | Mission alignment + Claim-Level Denial Prediction | 19 |
| `a2c7759` | Deal Profile page (single source of truth per deal) | 12 |

**97 new tests, all passing. 146 tests green across the cycle's affected surface.**

## What worked

- **Deal Monte Carlo is the strongest analytic this cycle.** 3000 trials in <100ms. Attribution + sensitivity tornado answer the "what would change my MOIC" question directly. Partners can read it in 30 seconds. Zero new deps. The variance attribution identifying physician-attrition as 41% of MOIC variance on the Steward-replay is exactly the kind of insight that generates "show me more" follow-up.

- **Claim-Level Denial Prediction made the EBITDA bridge honest.** Before this, the denial-reduction lever was an industry-aggregate guess. Now it's `$X of specific flagged claims × 60% recovery` with a per-feature attribution chart and a calibration report the partner can trust or reject on sight.

- **Deal Profile solved a friction that kept tripping me up while doing the VP walkthrough.** Retyping the same fixture name + deal name + legal structure across 8 forms was the actual daily workflow tax. localStorage + a slug-keyed profile + auto-filling links eliminated it in one commit. Low code, high UX.

- **Mission Alignment doc forced honesty about what's core.** Writing it mid-cycle (not at the end) changed what I built next — I stopped adding SaaS-ops and reputational features and leaned hard into CCD-native analytics (Denial Prediction) and deal-level Monte Carlo. The classification makes future "should I build X?" decisions faster.

- **Zero-dep SVG charts held up.** Fan chart, histogram, attribution bars, sensitivity tornado — all rendered cleanly, matched the dark palette, looked good in the browser. Didn't need matplotlib or plotly once.

## What needs more work

- **Risk Workbench hero stats feel generic vs. the Deal MC / Denial Prediction heroes.** The new pages show peer benchmarks inline (e.g., "Top quartile ≤8% vs HFMA peer median 10%") but the workbench panels still just show "NSA · RED" without context. Should port the interpretability pattern backward.

- **Deal Profile links open new pages with pre-filled params but the analytics don't know they came from a deal profile.** There's no breadcrumb "← back to Deal Profile" and no way to save a result *into* the profile (e.g., capture the Deal MC's P50 MOIC into the profile's saved state). Next cycle: two-way sync.

- **No server-side persistence of deal profiles.** Everything's localStorage. If you share the URL, the partner sees an empty profile on their browser. The workaround (URL-seed params) is good for one-off shares but not for team collaboration. Could persist profiles into the engagement model's DB when that path is enabled.

- **The Compare page only does pair-wise.** When a partner is evaluating five targets, they need to pick a winner, not just A vs B. Next cycle: multi-target compare grid.

- **No test that the full end-to-end flow lands a realistic MOIC range.** We test each module's correctness in isolation; no test ties "CCD-derived denial savings → bridge lever → Deal MC result → IC packet recommendation" together in a single assertion. Would catch cross-module regressions.

## What was a waste of time

- **The "premium UI polish" pass on the counterfactual page mid-cycle.** Reasonable decision in isolation, but the user had already flagged the UX friction (cross-page parameter retyping) earlier. I should have built Deal Profile two commits sooner instead of tightening CSS spacing.

- **Re-reading the CSS several times during the power_ui bundle.** The bundle is correct but I over-tuned tooltips + overlays + palette variables across three passes when one focused pass would have done it. Bias toward "ship it, iterate if partners complain."

- **Some of the YAML content breadth** (e.g., transaction_multiples.yaml covering 14 specialties × 3 size bands when 3 × 3 would have demoed the feature and been faster to ship). The bulk data isn't wrong — it just isn't earning interest until partners use it.

## Lessons I'll carry into next cycle

1. **Build UX friction fixes before cosmetic polish.** If a 3-click flow is annoying you, it's annoying users; fix it before re-styling buttons.
2. **Every new analytic needs a plain-English "What this shows" callout + peer benchmark context** (Denial Prediction got this right; backfill the rest).
3. **Commits should each stand up as a demo moment** (Deal MC, Denial Prediction, Deal Profile all did; Market Intel was weaker because the seeded data isn't a live pull).
4. **If I'm tempted to add a sixth stage-3 prompt, ask first "does this feed the EBITDA bridge?"** If no → reject.

## What to focus on next cycle

**#1 — Connect Deal MC inputs to the Deal Profile + Denial Prediction output.** Right now Deal MC accepts `reg_headwind_usd=15_000_000` as a free-form number. It should auto-pull:
- Counterfactual advisor's total dollars-at-risk
- Denial Prediction's bridge input
- Steward Score's lease PV savings
- V28 revenue compression from MA Dynamics

Closes the loop. One-click "Run Deal MC with your diligence findings" instead of hand-entry.

**#2 — Two-way Deal Profile sync.** When Deal MC / Denial Prediction / IC Packet finishes, write its headline number back into the Deal Profile's localStorage so the profile becomes a live dashboard of the deal's current state.

**#3 — Interpretability pass on Risk Workbench panels.** Backfill the "peer benchmark" + "what this shows" pattern from Denial Prediction hero onto every risk panel.

**#4 — End-to-end integration test.** One test that runs a fixture through ingest → benchmarks → denial prediction → counterfactual → deal MC → IC packet and verifies the final recommendation band is coherent.

**#5 — Multi-target Compare** (lower priority — single-deal workflow is the tax we should cut first).

## Stat check

- Product routes: ~20 user-facing (up from 8 at start of cycle)
- Tests passing: 146 (this cycle alone); full new-module suite 550+
- Runtime: every analytic <100ms end-to-end on a laptop
- Zero new runtime dependencies across six commits
