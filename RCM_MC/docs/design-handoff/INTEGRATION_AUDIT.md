# INTEGRATION_AUDIT — Editorial design system coverage

**Status:** Audit · 2026-04-25
**Scope:** Inventory of every HTML-rendering page in `rcm_mc/ui/` and its current relationship to the editorial design system. Maps which pages are fully-ported, partially-ported, chrome-only, or untouched. Output is a phase-assignment matrix the user can use to prioritize Phase 2b/2c/2d/4 work.

**This document does not change any code.** It is reference material for the morning planning session.

---

## TL;DR — the integration is further along than tonight's empty-DB load suggested

Three counts that reframe what "fully integrated" means:

- **289 of 334** page files in `rcm_mc/ui/` import `chartis_shell` from the dispatcher → chrome flips automatically when `CHARTIS_UI_V2=1` is set in the environment. This part of the integration is **already done at the architectural level**.
- **20** files in `rcm_mc/ui/chartis/` are dedicated editorial-namespaced renderers, all wired into server routes (verified — `from .ui.chartis.<page> import render_<page>` appears in 19 distinct route handlers in `server.py`).
- **10 files** use the editorial-native body primitives (`pair_block`, `editorial_page_head`). All 10 are the `/app` dashboard + its 9 helpers — Phase 3 work.

The gap is **not** "port pages to editorial chrome" — that's broadly done. The gap is **deeper-than-chrome editorial body markup** on the 19 Tier-1 chartis pages, plus the 4 cross-cutting nav issues from tonight's local test.

## Tier breakdown

### Tier 0 — Fully editorial-native (chrome + body + paired blocks)

| Route | File | LOC | Status |
|---|---|---|---|
| `/app?ui=v3` | `chartis/app_page.py` + 9 `_app_*.py` | 255 + ~2,500 | Phase 3 complete (commits in feat/ui-rework-v3, tests 25/25) |

**1 page surface.** Uses `pair_block`, `editorial_page_head`, `editorial_topbar`. This is the canonical editorial render and the partner-walkthrough target.

### Tier 1 — Chartis-namespaced, chartis_shell chrome, body NOT yet paired-block

19 pages that are wired into server routes (confirmed via `grep "from .ui.chartis" rcm_mc/server.py`) and use `chartis_shell()` for chrome, but their bodies use chartis-local `_panel()` helpers, raw HTML, or `ck_table()` — not the editorial `pair_block` / `editorial_page_head` primitives.

| Topnav section | Route (likely) | File | LOC |
|---|---|---|---|
| (header/landing) | `/` (marketing) | `chartis/marketing_page.py` | 477 |
| (auth) | `/login` | `chartis/login_page.py` | 352 |
| (auth) | `/forgot` | `chartis/forgot_page.py` | 132 |
| HOME | `/home` (legacy alias) | `chartis/home_page.py` | 723 |
| ANALYSIS | `/analysis/partner-review` | `chartis/partner_review_page.py` | 709 |
| DEALS | `/diligence/archetype` | `chartis/archetype_page.py` | 413 |
| DEALS | `/diligence/investability` | `chartis/investability_page.py` | 375 |
| DEALS | `/diligence/red-flags` | `chartis/red_flags_page.py` | 472 |
| DEALS | `/diligence/stress` | `chartis/stress_page.py` | 261 |
| DEALS | `/diligence/ic-packet` | `chartis/ic_packet_page.py` | 569 |
| DEALS | `/diligence/screening` | `chartis/deal_screening_page.py` | 390 |
| MARKET | `/market/structure` | `chartis/market_structure_page.py` | 285 |
| MARKET | `/market/payer-intelligence` | `chartis/payer_intelligence_page.py` | 358 |
| MARKET | `/market/sponsor-track-record` | `chartis/sponsor_track_record_page.py` | 307 |
| MARKET | `/market/white-space` | `chartis/white_space_page.py` | 314 |
| TOOLS | `/tools/rcm-benchmarks` | `chartis/rcm_benchmarks_page.py` | 356 |
| TOOLS | `/tools/corpus-backtest` | `chartis/corpus_backtest_page.py` | 414 |
| TOOLS | `/tools/pe-intelligence-hub` | `chartis/pe_intelligence_hub_page.py` | 383 |
| PORTFOLIO | `/portfolio/analytics` | `chartis/portfolio_analytics_page.py` | 507 |

**19 pages, ~7,800 LOC.** These are the marquee partner-facing surfaces beyond `/app`. Phase 2b/2c/2d work is **upgrading their bodies** from local `_panel`-style markup to the editorial `pair_block` + `editorial_page_head` primitives — same pattern that worked for the `/app` blocks.

**Routes verified:** routes for these 19 pages were confirmed by grepping `rcm_mc/server.py` for `from .ui.chartis.<filename> import render_*`. Specific path strings (e.g. `/diligence/archetype`) are inferred from filename + `_route_*` handler names; double-check exact paths during Phase 2b kickoff.

### Tier 2 — Legacy pages, chartis_shell chrome via dispatcher

~270 page files in `rcm_mc/ui/*.py` (root) and `rcm_mc/ui/data_public/*.py`. These import `chartis_shell` from the dispatcher (`_chartis_kit.py`), so chrome flips when `CHARTIS_UI_V2=1` is set, BUT their bodies are legacy markup (ck_table, ck_kpi_block, raw HTML).

**Visual state:** parchment topbar + serif title, dark-styled body content. Mixed-state acceptable per the dispatcher's docstring (line 64-71 of `_chartis_kit_editorial.py`): *"the editorial shell + .pair pattern produces the visual identity; the older helpers render their cells with legacy ck_* CSS that the editorial CSS doesn't fight."*

**Implication:** these pages **work** in editorial mode — they don't crash, they don't visually break. They're just not partner-walkthrough quality. Many of them aren't partner-walkthrough surfaces at all (data browser, calibration, audit log) and the cost-vs-benefit of porting their bodies is low.

**Recommendation:** do not blanket-port. Cherry-pick the 5-10 highest-traffic Tier-2 pages and elevate them to Tier 1 in Phase 2c or 2d. Leave the rest at chrome-only adoption indefinitely. Phase 5 cleanup (deleting `_chartis_kit_legacy`) is the forcing function for the long tail.

### Tier 3 — Pure legacy (`_ui_kit.shell`, dispatcher-bypass)

4 files: `csv_to_html.py`, `json_to_html.py`, `sensitivity_dashboard.py`, `text_to_html.py`.

These are utility renderers (CSV → HTML preview, JSON → HTML, etc.), not partner-facing pages. Out of scope for the editorial port; touching them buys nothing for partner walkthrough readiness.

### Detritus — 29 Finder duplicate files

Files literally named `<original> 2.py` (with the space). macOS Finder duplicate artifacts. Examples:

```
rcm_mc/ui/_chartis_kit_legacy 2.py
rcm_mc/ui/_chartis_kit_v2 2.py
rcm_mc/ui/bankruptcy_survivor_page 2.py
rcm_mc/ui/bear_case_page 2.py
... (25 more)
```

**Verified `rg -l " 2\.py"` returns 29 matches in rcm_mc/ui/.** They don't appear to shadow imports (Python doesn't import filenames with spaces) but they triple-count grep results and confuse audits like this one.

**Recommendation:** single cleanup commit — `git rm` all 29. Zero risk; safe to do at any time, including a tired-Andrew morning. Worth doing before Phase 2b begins so subsequent grep-driven audits give honest counts.

---

## What "fully integrated" actually means in priority order

Per your message: *"continue planning the full integration of the claude design and HTML, map out which pages still need updating and update them."*

Decomposed in honest priority order:

### P0 — Cross-cutting nav (small, high-leverage, pre-Phase-2b)

The 4 issues from tonight's gap doc (`UI_REWORK_PLAN.md` "Discovered during local testing 2026-04-25"). Implementation is bounded; risk is low; payoff is the v3 surface stops feeling like an island.

| Issue | Fix shape | Approx LOC | Risk |
|---|---|---|---|
| `?ui=v3` flag propagation | Add `editorial_link()` helper in `_chartis_kit_editorial.py`; wire through `editorial_topbar` brand href + `editorial_crumbs` internal hrefs | ~30 | Low (additive, contract test guards) |
| Topnav buttons non-functional | Convert `<button>` elements to `<a>` with hrefs to Tier 1 pages above | ~15 | Low (additive) |
| Logo drops to legacy | Already covered by P0 #1 (the brand href change) | (folded above) | — |
| DEMO_CHECKLIST verification commands never validated | Run them against a seeded DB after seeder lands; correct any drift | ~0 (no code) | None |

**Total: 1 commit, ~50 LOC, contract suite extends 25 → 27.** Could land alongside the seeder commits in Phase 2b kickoff.

### P1 — Demo seeder (already proposed)

`docs/design-handoff/SEEDER_PROPOSAL.md` (commit `e27c5de`, local-only). Resolves the empty-DB demo failure mode. C1-C6 questions need decisions. Implementation is ~720 LOC across 8 commits. **This is the unblocker for everything else** — until you can see the dashboard with realistic data, you can't visually evaluate Tier-0 polish or Tier-1 body ports.

### P2 — Phase 2b: marquee surface body ports (5 pages)

The 5 highest-leverage Tier-1 pages to upgrade from local `_panel` markup to editorial `pair_block` + `editorial_page_head`. Recommended set:

| Priority | File | Why |
|---|---|---|
| 1 | `chartis/home_page.py` | Authenticated home; first thing partners see post-login |
| 2 | `chartis/deal_screening_page.py` | DEALS section primary destination |
| 3 | `chartis/ic_packet_page.py` | Highest partner-decision-criticality (IC committee artifact) |
| 4 | `chartis/portfolio_analytics_page.py` | PORTFOLIO section primary destination |
| 5 | `chartis/red_flags_page.py` | Diligence-side marquee — pair-block pattern fits the alert/finding shape naturally |

Each page is ~300-700 LOC; body port is roughly 2-3x the LOC because pair_block makes existing markup more verbose. Estimated: **5 weeks of focused work** (1 week per page) at the pace Phase 3 moved. Each can ship as its own phase-numbered series.

### P3 — Phase 2c: secondary surfaces (5-7 pages)

Next set: `archetype_page`, `investability_page`, `market_structure_page`, `payer_intelligence_page`, `stress_page`, `corpus_backtest_page`, `sponsor_track_record_page`. ~3-4 weeks.

### P4 — Phase 2d: long tail (7 pages)

Remaining Tier-1 pages: `partner_review_page`, `pe_intelligence_hub_page`, `marketing_page`, `rcm_benchmarks_page`, `white_space_page`, `forgot_page`, `login_page`. ~2-3 weeks. (Login + forgot are already passable; lower priority.)

### P5 — Phase 4: cutover decisions (Q4.1-Q4.6 in UI_REWORK_PLAN.md)

`/` reroute, `/dashboard` aliases, `/engagements` resolution, legacy-nav archive, covenant schema, `net_collection_rate` decomposition. Pre-merge-to-main work. ~1 week + comms.

### P6 — Phase 5: legacy delete

`_chartis_kit_legacy.py`, the dispatcher in `_chartis_kit.py`, the 29 Finder duplicates, the 4 Tier-3 utility files (consolidate or delete). Cleanup commit. ~half a day.

---

## What I'd touch first if given carte blanche tomorrow

In your shoes, tomorrow morning, after coffee:

1. **Greenlight the seeder** by answering C1-C6 in `SEEDER_PROPOSAL.md` (~10 min). Seeder lands by EOD tomorrow.
2. **Do the P0 cross-cutting nav fix** as a single commit (~1 hour). The `editorial_link()` helper + brand href fixes + 2 contract tests. Closes 3 of the 4 gaps from tonight's local test.
3. **Run the seeder + verification commands.** Loads the dashboard with realistic data. Closes the 4th gap (verification commands validated).
4. **Do the partner-walkthrough rehearsal** against the seeded dashboard. Pass 1 (solo), Pass 2 (hostile-partner with me), Pass 3 (with a human).
5. **Decide Phase 2b vs. cutover sequencing** based on what you observed in rehearsal.

Items 1-4 fit in a single working day. Item 5 is the strategic call that should wait for the partner walkthrough itself.

---

## What I am NOT recommending

- Do not start Phase 2b body ports tonight or tomorrow morning. The seeder + nav fix are higher-leverage and ship in hours, not weeks.
- Do not attempt to port all 19 Tier-1 pages in one phase. Even at the "5 pages = 5 weeks" estimate, a single-phase 19-page port would be 4 months of work — that's not a phase, that's a quarter.
- Do not blanket-port Tier-2 pages. The chrome already adapts; the body cost-vs-benefit is unfavorable for most. Cherry-pick instead.
- Do not skip the partner walkthrough rehearsal even if the seeder + nav fix go smoothly. The walkthrough is what tells you what to prioritize next; without it you're guessing.

---

## Open questions for the morning

1. **P0 implementation:** the hook denied autonomous production-code edits tonight. The `editorial_link()` helper + brand href fix is small (~50 LOC) and has obvious value — do you want to authorize that as a single commit before bed, or keep it for morning review?
2. **Finder-duplicate cleanup:** 29 files `git rm` is risk-free. Bundle with the nav fix commit, or separate?
3. **Tier-1 body-port sequencing:** I recommended 5 pages for Phase 2b. Confirm the order, or substitute based on partner-walkthrough priorities?
4. **Tier-2 cherry-pick list:** which 5-10 of the ~270 Tier-2 pages get elevated to Tier 1 in Phase 2c? Right now I don't have data on partner usage frequency to recommend this.

---

---

## Addendum: CSS-token / inline-style consistency check (added 2026-04-25)

Spot-survey of inline `style="…"` density across the 19 Tier-1 chartis pages, looking for hardcoded hex colors that bypass the editorial palette.

### Critical: `home_page.py` is a dark-shell page in chartis chrome

`rcm_mc/ui/chartis/home_page.py` has **17 distinct hex colors hardcoded inline** across 43 occurrences. None of them are in the editorial palette. They're dark-shell-era values:

| Hex | Count | Likely role | Editorial equivalent |
|---|---|---|---|
| `#1e293b` | 6 | Dark card background | `var(--paper-pure)` (not dark — paper) |
| `#94a3b8` | 5 | Dark-shell muted text | `var(--muted)` (#5C6878) |
| `#f59e0b` | 5 | Dark-shell amber | `var(--amber)` (#B7791F) |
| `#e2e8f0` | 4 | Dark-shell light text | `var(--ink)` (#0F1C2E) |
| `#3b82f6` | 3 | Dark-shell blue accent | `var(--blue)` (#2C5C84) |
| `#111827`, `#0f172a`, `#0a0e17` | 5 | Near-black backgrounds | **Visual rewrite** — editorial doesn't have near-black |
| `#10b981` | 5 | Dark-shell green | `var(--green)` (#3F7D4D) |
| `#64748b` | 3 | Dark-shell neutral | `var(--muted)` |
| `#ec4899`, `#8b5cf6`, `#0891b2`, `#ef4444` | 6 | Decorative accents | Map to editorial blue/teal/red as appropriate |

**Implication:** `home_page.py` was built for the dark shell ORIGINALLY and got `chartis_shell()` wired around it later. Setting `CHARTIS_UI_V2=1` produces a Frankenstein render: parchment topbar + serif title + dark card backgrounds with light text inside. **This is the highest-priority Tier-1 page to body-port** in Phase 2b — the visual mismatch is severe.

### Good news: the other 18 Tier-1 pages are mostly palette-aware

Spot-checking `red_flags_page.py`, `ic_packet_page.py`, `partner_review_page.py`: their inline styles use `f"…color:{P['ink']}"` or `f"…color:{P['muted']}"` — they reference the **palette dictionary `P`** which the dispatcher swaps between editorial and legacy. These pages adapt automatically.

The 14 dark-shell-pattern matches my earlier grep flagged were all in `home_page.py`; the other pages came up clean on the same grep.

**Updated Phase 2b sizing:** instead of "5 weeks for 5 pages of body port," the actual work is closer to:

- `home_page.py` (1 week — visual rewrite, not just `pair_block` adoption — replace 17 hardcoded colors with editorial paper/ink + map dark backgrounds to white cards)
- 4 other pages with `pair_block` adoption only (~3 days each, ~2.5 weeks total)
- **Total: ~3.5 weeks for top-5 Phase 2b pages**, not 5 weeks. `home_page` is the tax payer.

### Other pages with non-trivial inline-style density (FYI, not action items)

| File | Inline styles | Note |
|---|---|---|
| `home_page.py` | 85 | The outlier — see above |
| `partner_review_page.py` | 67 | Palette-aware via `P[…]`; volume implies pair_block port will be substantial |
| `marketing_page.py` | 60 | Public landing page; palette-aware |
| `ic_packet_page.py` | 56 | Palette-aware |
| `red_flags_page.py` | 49 | Palette-aware |
| `portfolio_analytics_page.py` | 35 | Palette-aware |
| Others | 1-32 | Range from minimal to moderate |

**Recommendation:** start Phase 2b with `home_page.py` regardless of whether it's the highest-traffic page — its dark-shell contamination makes the editorial chrome look broken. Other pages can wait.

### Tier 3.5 finding (added 2026-04-25): 9 pages bypass the editorial dispatcher entirely

A second pass — probing the 4 user-named marquee routes (`dashboard`, `deal profile`, `screening`, `exports`) under `CHARTIS_UI_V2=1` — found that **3 of the 4 either bypass the dispatcher entirely or have heavy legacy-CSS contamination**:

| Route | Renderer | State |
|---|---|---|
| `/app?ui=v3` | `chartis/app_page.py` | Fully editorial-native (Tier 0) |
| `/dashboard` | `dashboard_page.py` | chartis_shell chrome ✓ · legacy hex in body ⚠ |
| `/home` | `chartis/home_page.py` | chartis_shell chrome ✓ · 17 hardcoded dark-shell hex ⚠ |
| `/deal/<id>/profile` | `deal_profile_v2.py` | **bypasses dispatcher entirely** — builds own `<!doctype>...` |
| `/screening/dashboard` | `screening/dashboard.py` | **bypasses dispatcher entirely** — builds own `<!doctype>...` |
| `/screening/bankruptcy-survivor` | `bankruptcy_survivor_page.py` | **bypasses dispatcher entirely** |
| `/exports` | `_export_menu.py` | chartis_shell chrome ✓ · legacy hex in body ⚠ |

Full list of renderers that build own HTML (case-insensitive `<!DOCTYPE` grep):

- ~~`rcm_mc/ui/analysis_workbench.py`~~ — **NOT a bypass** (verified 2026-04-27): the original `<!doctype>` grep was case-insensitive and matched the literal string "doctype html" inside this file's docstring (which describes what the function used to do). The actual `render_workbench()` already wraps in `chartis_shell()` (since some prior commit). Ship status: ✅ correctly dispatched.
- ~~`rcm_mc/ui/bankruptcy_survivor_page.py`~~ — **legitimate bypass** (verified 2026-04-26): docstring states *"The result page is intentionally standalone — no Chartis shell — so partners can print it cleanly"*. Uses `@page{size:Letter}` + `@media print` rules. Designed to print as IC-packet PDF attachment. Wrapping it in `chartis_shell` would print the topbar/breadcrumbs/PHI banner on the artifact. **DO NOT port.**
- ~~`rcm_mc/ui/dashboard_v2.py`~~ — **NOT a bypass** (verified 2026-04-27): already passes through `chartis_shell()`. Ship status: ✅ correctly dispatched. Phase 4 cutover decides whether `?v2=1` survives at all.
- `rcm_mc/ui/dashboard_v3.py` — **bypass confirmed**: line 548 emits `<!doctype html><html><head>` directly. Opt-in via `?v3=1`. Phase 4 cutover decides retire-vs-port; if port, same pattern as screening + deal_profile_v2.
- ~~`rcm_mc/ui/deal_profile_v2.py`~~ — **PORTED 2026-04-27 (commit `b283a04`)**. The "needs full rewrite" warning was wrong — the screening port pattern (palette swap + strip doctype + chartis_shell wrap) applied cleanly.
- `rcm_mc/ui/onboarding_wizard.py` — **bypass confirmed**: line 173 emits `<!DOCTYPE html>`. First-time setup wizard, low partner-visibility. Lower priority than dashboard_v3.
- `rcm_mc/ui/sensitivity_dashboard.py` — **bypass confirmed**: emits `<!doctype>` in a return statement. Utility page, low partner-visibility. Lower priority than dashboard_v3.
- `rcm_mc/ui/chartis/marketing_page.py` — public landing page (legitimate bypass; this is the marketing splash and intentionally has its own shell)
- ~~`rcm_mc/screening/dashboard.py`~~ — **PORTED 2026-04-26 (commit `c3d8e5f`)**. Now passes through `chartis_shell()`.

Refined Phase 2b priority list (bypass surfaces with no intent reason to stay bypassed):

| File | Status | Notes |
|---|---|---|
| `screening/dashboard.py` | ✅ ported (`c3d8e5f`) | template for the pattern |
| `analysis_workbench.py` | ⏳ next candidate? | Bloomberg-style; high complexity but high partner visibility |
| `deal_profile_v2.py` | ⚠️ needs rewrite, not port | own theme system fights editorial |
| `dashboard_v2.py` / `v3.py` | 🗑 retire-or-port? | Phase 4 cutover decision: do these survive at all in v3? |
| `onboarding_wizard.py` | ❓ low priority | one-shot setup flow |
| `sensitivity_dashboard.py` | ❓ low priority | utility |

### Why "wrapper port" doesn't work for these pages

Tempting fix: wrap their body in `chartis_shell()` and pass the page-local CSS as `extra_css`. **This would actively make them worse**, not better.

Looking at `screening/dashboard.py:_CSS`, the page-local CSS sets:

```css
body {
  background: var(--c-bg);  /* #0a0e17 — dark navy */
  color: var(--c-text);     /* #e2e8f0 — light gray */
  ...
}
```

If wrapped in `chartis_shell()`, the editorial chrome (parchment topbar) renders at the top, then the body's `background: #0a0e17` overrides editorial parchment, producing a Frankenstein render: parchment topbar → dark navy body. Worse than the current state, which at least is internally consistent dark-shell.

Same shape for `deal_profile_v2.py` (uses `theme_stylesheet()`) and `bankruptcy_survivor_page.py`.

**The correct fix is per-page visual rewrite, not wrapper port.** Each page needs:
1. Strip the global `body { background, color }` overrides
2. Replace `--c-*` palette variable values with editorial palette equivalents
3. Replace dark-shell hex throughout (~30-100 substitutions per file)
4. Verify the page still renders with editorial chrome

That's per-region visual judgment work — same scope as `home_page.py` rewrite from earlier in this audit. Each page is **1 working day** for the wrap-and-token-port (mechanical), **3-5 days** for full editorial body rewrite.

### Updated Phase 2b sizing for the 4 user-named pages

Re-prioritizing per the user's stated direction ("focus on dashboard, deal profile, screening, exports"):

| # | Page | Effort | Notes |
|---|---|---|---|
| 1 | `chartis/home_page.py` (`/home`) | 1 week visual rewrite | 17 hardcoded dark-shell hex; passes chartis_shell chrome already |
| 2 | `screening/dashboard.py` (`/screening/dashboard`) | 1-3 days dispatcher-port + 2-3 days visual | Bypass + dark-shell body |
| 3 | `deal_profile_v2.py` (`/deal/<id>/profile`) | 1-3 days dispatcher-port + 3-5 days visual | Bypass; large file (646 LOC) |
| 4 | `bankruptcy_survivor_page.py` | 1-2 days | Bypass; smaller file |
| 5 | `_export_menu.py` (`/exports`) | 2-3 days visual | chrome works; legacy hex in body |

**Total: ~3 weeks of focused work for the 4 named surfaces.** Half the original Tier-1 estimate because chrome already works on 2 of 4. This is the actual Phase 2b scope the user asked for.

### CSS-side: `chartis.css` is internally consistent

Grep of `rcm_mc/ui/static/v3/chartis.css` (820 lines) shows the palette tokens are used cleanly throughout — `var(--green)`, `var(--teal)`, `var(--ink)`, etc. The Q3.7 PHI banner work added `--green-muted: #3D6F45` cleanly. No drift from the design system inside the CSS file itself.

The inconsistency is **at the page-level Python rendering**, not the CSS.

---

## See also

- [`UI_REWORK_PLAN.md`](../UI_REWORK_PLAN.md) — phase plan, conventions, rollback, Q4.1-Q4.6
- [`SEEDER_PROPOSAL.md`](SEEDER_PROPOSAL.md) — pre-Phase-2b infrastructure (C1-C6 questions)
- [`PHASE_3_PROPOSAL.md`](PHASE_3_PROPOSAL.md) — pattern to follow for Phase 2b proposal
- [`IA_MAP.md`](IA_MAP.md) — full nav inventory; Tier-1 routes here are the topnav destinations
- [`DEMO_CHECKLIST.md`](../DEMO_CHECKLIST.md) — partner-walkthrough script
