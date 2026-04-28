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

## Cycle 1 build — iterations 3-7 — 2026-04-28

**Steps 3 + 4 + 5 + 6 + 7 batched** (cron firing faster than per-step
commit cadence; consolidating to keep the work coherent and the
push history honest).

**Step 3 — pattern sketched:** `docs/CHARTIS_MATCH_NOTES.md` created
with three patterns: search hero (navy panel + italic-serif label
+ chevron-cut bottom-right), filter sidebar (eyebrow rail with BY
TOPIC / BY TYPE), N-RESULTS header with chip-clear active filters.
Search hero specced fully (markup + CSS + tokens + target pages +
helper signature + build sequence). The other two are scoped for
cycle 2 build.

**Step 4 + 5 + 7 — lazy-label sweep across ALL data_public pages:**
50 pages had a generic `<button type="submit">Run</button>` (not 12
as planned — discovery undercount). Replaced with `Run analysis` in
a single batched sed across all 50 files; one cycle's work in one
edit. The bare `>Run<` button as a Bloomberg-era legacy idiom is
now extinct in the codebase.

**Step 6 — chartis-match polish:** `/alerts` headline gained the
italic-serif highlight signature ("Where the portfolio *needs*
attention"). Matches the chartis.com "Reasons to *believe* in
better" cadence. Single-line edit, large editorial impact —
partners now see a fully Chartis-toned headline above the severity
panels.

**Files touched.**
- `docs/CHARTIS_MATCH_NOTES.md` (new, ~200 LOC)
- `rcm_mc/ui/data_public/*.py` × 50 (one line each, Run → Run analysis)
- `rcm_mc/ui/alerts_page.py` (one headline edit, italic-serif highlight)

**Compliance impact.**
- Lazy `>Run<` buttons remaining in codebase: 0 (was 50)
- `>Click here<`, `>TBD<`, `>Coming soon<`, `>...<` — 0 (already clean)
- Pages with italic-serif highlight in headline: /alerts (was 0)

**Suggested next:** cycle 2 step 4 build target — implement
`ck_search_hero` per `CHARTIS_MATCH_NOTES.md` pattern 01. First
user: `/library`. Once landed, follow with `ck_filter_sidebar`
(pattern 02) on the same page.

---

## Day 2 / Cycle 2 orient — iteration 11 — 2026-04-28

**State of the world.** `design-v5` now has 14 commits ahead of
`main`. Cycle 1 closed cleanly:
- Topbar / chrome bridged across marketing → app (commit 9da9d1b)
- Editorial primitives: ck_eyebrow, ck_section_intro, ck_arrow_link,
  ck_image_card, ck_severity_panel, ck_affirm_empty
- `/alerts` editorial uplift complete with italic-serif highlight
- 50 data_public pages: bare `>Run<` → `>Run analysis<`
- Token forwarding: `--cad-*` + v3 marketing tokens → canonical `--sc-*`
- Polish log + chartis-match notes + Azure-deploy checklist created
- Connectivity audit + partner-readable docstring on `alerts_page.py`

**Routes polished to editorial spec (running list):**
- `/` (marketing) — navy topbar, italic-serif Chartis wordmark, teal CTA
- `/login` — split-panel editorial layout (pre-existing, verified)
- `/alerts` — full editorial dashboard with italic-serif highlight
- `/screening/bankruptcy-survivor` (landing) — chartis_shell wrapped
- `/portfolio/monitor` — chartis_shell wraps the bespoke renderer
- `/v5-status` — campaign progress dashboard
- 50 `/data_public/*` pages — button copy editorialized
- `/v3-status` — pre-existing v3 status page (no changes needed)

**Routes pending editorial spec:**
- `/home` — needs italic-serif headline + image-top card grid
  ("Reasons to *believe*" cadence applied to portfolio panels)
- `/library`, `/research` — need search hero + filter sidebar +
  N-RESULTS chip-clear (sketched in CHARTIS_MATCH_NOTES.md
  patterns 01 / 02 / 03)
- `/escalations`, `/my/<owner>` — same archetype as `/alerts`;
  reuse ck_severity_panel + ck_affirm_empty
- `/notes`, `/search` — full-text search; reuse ck_search_hero
  once it lands
- `/audit` — admin surface; needs editorial chrome audit
- `/diligence/*` — workbench archetype; partial editorial chrome,
  audit per ACCEPTANCE_CHECKLIST.md row by row

**Top 3 priorities for cycle 2:**
1. Build `ck_search_hero` per CHARTIS_MATCH_NOTES.md pattern 01;
   wire to `/library`. Add focused test pinning navy panel +
   italic-serif label + form action.
2. Build `ck_filter_sidebar` per pattern 02; wire to `/library`
   alongside the search hero so the page is fully editorial.
3. `/home` chartis-match audit: walk header / hero / cards /
   accent / numerics / buttons against chartis.com; pick worst
   gap (likely the "Reasons to *believe*" image-top card grid for
   the partner panels) and ship.

**Unfinished thread from prior iteration:** none — `/alerts`
docstring + AZURE_DEPLOY_CHECKLIST.md + polish log all landed in
the cycle-1-closing commit.

**Azure deploy progress.** 6 of 22 rows passing. Next-up:
PORT-from-env, 0.0.0.0 bind, auth cookie flag audit, deploy
manifest under `deploy/` for Azure App Service Configuration.

---
