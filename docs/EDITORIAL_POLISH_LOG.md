# Editorial Polish Log

The continuous record of the chartis.com editorial-fidelity rotation
on `design-v5`. Each iteration appends a section. Skim top-to-bottom
to see what's been polished, what's pending, and what the next
iteration should target.

Source-of-truth references:
- `chartis.com` (visual reference — navy header, italic-serif
  highlights, teal accent, paper background, generous whitespace)
- `design_reference/handoff/MODULE_ROUTE_MAP.md` (79 surfaces)
- `design_reference/handoff/ACCEPTANCE_CHECKLIST.md` (per-page rows)
- `docs/V5_ROUTE_INVENTORY.md` (mechanical chrome compliance)
- `docs/CHARTIS_MATCH_NOTES.md` (per-pattern observations + sketches)

---

## Day 1 orient — iteration 1 — 2026-04-28

**State of the world.** `design-v5` is live with editorial chrome
end-to-end. Last 11 commits ahead of `main`:

| commit  | summary                                                              |
|---------|----------------------------------------------------------------------|
| 9da9d1b | chartis.com chrome bridge — navy topbar + editorial primitives        |
| c228e44 | Phase 2 sprint — UI surface to 100% v5 compliance                     |
| 0b875f8 | Phase 2 first migration — /alerts → chartis_shell renderer            |
| 4d16d3d | foundation 1E — V5_DISCOVERY_LOG.md scaffold                          |
| 257ce75 | foundation 1B + 1D — V5_ROUTE_INVENTORY.md + /v5-status page          |
| e282664 | P palette gets legacy-key aliases                                    |
| 06d20e5 | seed andrewthomas@chartis.com / ChartisDemo1 + /app fix              |
| 610f452 | login type=email -> type=text so 'demo' submits                      |
| b31d202 | chartis_shell — wire extra_css into <head>                           |
| 37259b6 | chartis_shell accepts subtitle / show_chrome / show_sidebar         |
| 852542c | import design reference: SeekingChartis brand handoff package        |

**Routes already polished to editorial spec (commit 9da9d1b):**
- Topbar across all signed-in routes — navy band, white wordmark
  with italic *Chartis*, uppercase nav with teal active underline,
  teal-on-navy user chip, thin teal accent rule on bottom edge
- `/` (marketing landing) — topbar matches chartis_shell silhouette
  so the bridge from `/` → `/login` → `/home` no longer changes
  shells
- `/alerts` — full editorial dashboard rewrite: serif page intro
  with eyebrow rule, severity-toned panels (`ck_severity_panel`),
  affirmative empty state (`ck_affirm_empty` "Portfolio is clean"),
  tightened ack/snooze copy
- Color discipline — `--cad-*` (Bloomberg-era) and `--teal-deep` /
  `--ink-2` (v3-marketing) tokens now alias to canonical `--sc-*`
  tokens; every legacy caller inherits Chartis colors automatically

**Routes pending Chartis-match polish (top of the list):**
1. `/home` — partner's first-login page; should mirror Chartis
   "Reasons to believe" image-card grid pattern
2. `/library`, `/research` — content-listing pages; need the search
   hero + filter sidebar + N-RESULTS pattern from chartis.com/insights
3. Data public pages (`/capital-pacing`, `/payer-concentration`,
   `/supply-chain`, `/sponsor-heatmap`, `/drug-pricing-340b`,
   `/partner-economics`, `/covenant-headroom`, `/locum-tracker`,
   `/cin-analyzer`, `/provider-retention`, `/aco-economics`,
   `/payer-stress`) — 12 pages with generic "Run" buttons that
   need editorial action verbs
4. `/login` — already split-panel editorial; verify against
   chartis.com aesthetic and italic-serif highlight in headline
5. `/escalations`, `/my/<owner>` — same dashboard archetype as
   `/alerts`; should reuse `ck_severity_panel` + `ck_affirm_empty`

**Top 3 priorities for cycle 1:**
1. Lazy-label sweep on data_public pages (12 generic "Run" buttons
   → action verbs) — finite, high-visibility, ships chartis-tone
   button copy
2. Build `ck_search_hero` + `ck_filter_sidebar` patterns and apply
   to one content-listing page — matches the chartis.com/insights
   pattern that sets the editorial standard
3. Audit `/home` for italic-serif highlights and image-top card
   grid; build the partner-facing "Reasons to believe" equivalent

**Unfinished thread from prior iteration:** none — commit 9da9d1b
closed the in-flight chrome bridge work.

---

## Cycle 1 plan — iteration 2 — 2026-04-28

**Target:** Lazy-label sweep across the 12 `rcm_mc/ui/data_public/*`
pages that ship a generic `<button>Run</button>`.

**Why this one now.** Chartis would never ship a button that just
says "Run". Each page has a specific analysis it triggers; the
button copy is the partner's first read of what's about to happen.
With the chrome already navy/teal editorial, the lazy labels are
now the loudest gap. Twelve 1-line edits eliminate the gap in
under 100 lines of churn. This is the highest-leverage cleanup
left before per-page Chartis-match dives begin.

**Files in scope (12).**
- `rcm_mc/ui/data_public/aco_economics_page.py`
- `rcm_mc/ui/data_public/capital_pacing_page.py`
- `rcm_mc/ui/data_public/cin_analyzer_page.py`
- `rcm_mc/ui/data_public/covenant_headroom_page.py`
- `rcm_mc/ui/data_public/drug_pricing_340b_page.py`
- `rcm_mc/ui/data_public/locum_tracker_page.py`
- `rcm_mc/ui/data_public/partner_economics_page.py`
- `rcm_mc/ui/data_public/payer_concentration_page.py`
- `rcm_mc/ui/data_public/payer_stress_page.py` (renames `Run Stress Test` already specific — verify, otherwise leave)
- `rcm_mc/ui/data_public/provider_retention_page.py`
- `rcm_mc/ui/data_public/sponsor_heatmap_page.py`
- `rcm_mc/ui/data_public/supply_chain_page.py`

**Editorial label per page (Chartis tone — verb + the thing):**

| page                       | from   | to                          |
|----------------------------|--------|-----------------------------|
| aco_economics              | Run    | Run ACO economics scan      |
| capital_pacing             | Run    | Run capital-pacing analysis |
| cin_analyzer               | Run    | Run CIN scan                |
| covenant_headroom          | Run    | Run covenant scan           |
| drug_pricing_340b          | Run    | Run 340B audit              |
| locum_tracker              | Run    | Run locum analysis          |
| partner_economics          | Run    | Run partner economics       |
| payer_concentration        | Run    | Run concentration scan      |
| payer_stress               | Run Stress Test | (verify, keep)     |
| provider_retention         | Run    | Run retention audit         |
| sponsor_heatmap            | Run    | Refresh heatmap             |
| supply_chain               | Run    | Run supply audit            |

**Line-count estimate.** ~12 lines (one button text per file).
No CSS changes. No structural changes.

**Test plan.** No existing tests assert on the bare `>Run<` text,
so no test rewrites needed. Add a single defensive test:
`tests/test_data_public_button_copy.py` — imports the 12 page
modules, calls each renderer with minimal inputs, asserts the
rendered HTML contains an editorial label (regex matching
`Run \w+|Refresh \w+`) and does NOT contain the bare `>Run<`
button. Locks in the Chartis-tone discipline.

**User-visible diff.** A partner who clicks into any data_public
page now sees a button that reads what it does ("Run capital-pacing
analysis", "Refresh heatmap"), not the abbreviation-ese "Run". One
less moment of "what does this do" friction across 12 routes.

**Coverage of cycle's 10 steps:**
- Step 3 (think/design): if a label needs the "verb + the thing"
  pattern that doesn't fit one of these 12, sketch it in
  `CHARTIS_MATCH_NOTES.md` first
- Step 4 (build): apply the table above; one commit per ~3 pages
- Step 5 (legacy elimination): deletes the bare-`>Run<` lazy label
  pattern entirely from the codebase
- Step 6 (chartis match): button copy is part of the editorial
  fidelity audit — confirm against the matching chartis.com page
- Step 7 (no-lazy-labels sweep): IS this; cycle 1 is the sweep
- Step 8 (.py connectivity): verify each page's renderer is wired
  to its server.py route + the route appears in nav
- Step 9 (continue + commit review): finish remaining pages
- Step 10 (Azure deploy): unrelated this cycle; pick the next row

**Stretch:** if cycle 1 finishes the 12-page sweep with budget left,
audit `/home` against the chartis.com "Reasons to believe in better"
image-card grid and start the design pass for `ck_image_card_grid`
as the cycle 2 build target.

---
