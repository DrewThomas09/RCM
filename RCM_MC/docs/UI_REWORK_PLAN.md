# UI Rework — Plan + Safety Rails

**Branch:** `feat/ui-rework-v3`
**Designer:** working with Claude Design
**Created:** 2026-04-25

---

## What this branch is for

A full UI / HTML rework of the SeekingChartis surface. Scope: visual language, page composition, component library, navigation, density, color, typography. All of that can change freely.

## What "stays connected" means

The rework cannot break:

| Connection | Why it matters | How we lock it |
|---|---|---|
| **Routes** | Bookmarks, copy-pasted URLs, mobile shortcuts must keep working | `tests/test_ui_rework_contract.py::test_critical_pages_resolve` |
| **`/health` + `/healthz` body=`"ok"`** | Docker healthcheck + Caddy + uptime probes depend on this exact body | `tests/test_ui_rework_contract.py::test_health_endpoints_return_ok_body` |
| **Auth round-trip** | Session cookies, CSRF, login flow | `tests/test_ui_rework_contract.py::test_login_round_trip` |
| **`DealAnalysisPacket` load-bearing fields** | Every UI surface reads from this single dataclass | `tests/test_ui_rework_contract.py::test_packet_dataclass_load_bearing_fields` |
| **OpenAPI surface** | External callers / integrations / `gh` workflows | `tests/test_ui_rework_contract.py::test_openapi_spec_loads` |
| **JSON endpoints stay JSON** | Any `/api/*` that returns HTML by accident is a regression | `tests/test_ui_rework_contract.py::test_authenticated_data_endpoint_returns_json` |
| **All schema migrations apply** | Server boot must not regress | `tests/test_ui_rework_contract.py::test_all_migrations_applied` |
| **Single shell()-style renderer** | Global treatment consistency depends on one insertion point | `tests/test_ui_rework_contract.py::test_ui_kit_shell_function_exists` |

The contract test runs in <2 seconds and is the pre-flight before any push to this branch.

## What CAN change freely

- Colors, fonts, spacing, shadows, radii, transitions
- HTML structure (div/section/article — refactor at will)
- CSS class names (rename them, just keep data flowing through)
- JavaScript behavior (animations, loading states, empty-state copy)
- Page composition (which components appear where on a page)
- Component library API (`power_table`, `power_chart`, `_ui_kit.*` can all change)
- Navigation IA (move things between pages — but keep the old URL redirecting if it's externally bookmarked)
- Density, typography, voice, microcopy

## Recommended architecture: feature flag for coexistence

Don't replace `rcm_mc/ui/` in-place — that's how the prior reskin broke and got reverted (commit `d8bfac4 revert(ui): restore dark terminal shell`). Instead:

```
rcm_mc/
├── ui/         ← v2 — keeps rendering exactly as today
└── ui_v3/      ← v3 — new look. Renders only when flag is on.
```

**Flag detection** (one-liner in `server.py`):

```python
def _ui_version(self) -> str:
    # Query param overrides env for per-request testing.
    if "ui" in self.query_params:
        return self.query_params["ui"]
    return os.environ.get("RCM_MC_UI_VERSION", "v2")
```

**Routing** (each page picks its renderer):

```python
if self._ui_version() == "v3":
    from .ui_v3 import deal_profile
    return deal_profile.render(packet)
from .ui import deal_profile_v2
return deal_profile_v2.render(packet)
```

This lets Claude Design rebuild any page without touching the v2 surface. Toggle `?ui=v3` in the browser to preview; toggle `RCM_MC_UI_VERSION=v3` on a staging VM to run an isolated end-to-end test.

## Phase plan

| Phase | Scope | Exit criteria |
|---|---|---|
| **1. Foundation (Week 1)** | Design tokens, typography scale, color palette, base components (`Button`, `Card`, `Input`, `KPI`, `Table` shell). Build `ui_v3/_kit.py`. | Contract tests still green; `?ui=v3` renders a single page identically functional to v2 |
| **2. Marquee surfaces (Week 2-3)** | Dashboard, Deal Profile, Screening, Analysis Workbench. The 4 pages that drive 80% of partner time | Each page passes contract tests in both `?ui=v3` and unset; partner walkthrough doesn't surface a regression |
| **3. Long tail (Week 4-5)** | The remaining 30+ pages (LP digest, audit log, settings, calibration, etc.) | All pages render in `?ui=v3` mode |
| **4. Cutover (Week 6)** | Flip `RCM_MC_UI_VERSION=v3` default. Old `ui/` package stays for 30 days as a rollback option | Live traffic on v3, no rollback fired in first 7 days |
| **5. Cleanup (Week 8+)** | Delete old `ui/` package after 30-day soak | Tests still green, package deletion is a single-PR diff |

## Daily-driver: how to test that nothing's broken

```bash
# Before any commit on this branch
cd RCM_MC
.venv/bin/python -m pytest tests/test_ui_rework_contract.py -v

# Before any push
.venv/bin/python -m pytest \
  tests/test_ui_rework_contract.py \
  tests/test_healthz.py \
  tests/test_api_endpoints_smoke.py \
  tests/test_full_pipeline_10_hospitals.py \
  tests/test_readme_links.py \
  tests/test_auth.py \
  tests/test_csrf.py
```

## Rollback procedure

The branch is pure-additive (new `ui_v3/` package + flag check). To roll back:

```bash
# Local
git checkout main
# nothing else needed — main never sees ui_v3/

# Production VM (only relevant after Phase 4 cutover)
ssh azureuser@pedesk.app
sudo -E RCM_MC_UI_VERSION=v2 systemctl restart rcm-mc
# Or: cd /opt/rcm-mc && sudo git checkout <commit-before-cutover>
# Then: sudo docker compose -f RCM_MC/deploy/docker-compose.yml up -d --build
```

## Critical: do NOT merge to main until contract tests pass

The `deploy.yml` workflow auto-deploys `main` to `pedesk.app` on every push. So:

1. Work on `feat/ui-rework-v3` until contract tests are 8/8 green AND every CRITICAL_PAGES route renders in `?ui=v3` mode.
2. Open a PR — never push directly to main.
3. Merge only after a stakeholder has clicked through the v3 surface end-to-end and signed off.
4. On merge, watch the deploy workflow run; have the rollback command ready.

## Why the prior rework was reverted

For learning purposes — these are the connection patterns the prior reskin broke:

1. **In-place CSS replacement** — every page changed at once, no way to A/B test.
2. **No flag** — couldn't preview without affecting all users.
3. **Renamed `_ui_kit.shell()` arguments** — silently broke 14 tests that passed kwargs.
4. **Removed several existing CSS classes** — workbench tabs lost their highlight states.
5. **Different approach for tables across pages** — broke the `power_table` consistency contract.

Today's rework can avoid all five by gating with a flag, keeping the v2 package alongside, and running the contract test on every commit.

## Open questions for Claude Design

- Do we want a single global theme toggle (dark/light/editorial) or per-page treatments?
- Are we keeping the dense-data tables (power_table) as-is for analyst use, with a friendlier surface for partner use?
- Is the navigation moving (sidebar → top-bar, breadcrumbs, command-palette)?
- Is there a typography pairing already chosen?

Document the answers in this file as decisions are made — they become the design system spec.

---

## Phase 1 rollback procedure

If Phase 1 ships and a regression appears post-merge to `main` (deploys to `pedesk.app` automatically per `.github/workflows/deploy.yml`):

### Local rollback

```bash
git checkout main
git revert <commit-range>  # the 9 commits 53350d2..f7fa01f are atomic
git push origin main       # auto-deploys the revert
```

Each of the 9 commits is independently revertable. If the regression is isolated (e.g., only `/login?ui=v3` breaks), revert that single commit (`8d8075c`); the others stay.

### Production VM rollback (no code change needed)

The editorial path is gated behind a flag. To disable v3 instantly without redeploying:

```bash
ssh azureuser@pedesk.app
sudo nano /opt/rcm-mc/.env       # remove RCM_MC_UI_VERSION=v3 or set =v2
sudo systemctl restart rcm-mc
```

The `?ui=v3` query override still works, but no env-driven editorial render will happen. Legacy shell renders unchanged.

### Code-side rollback (full)

```bash
ssh azureuser@pedesk.app
cd /opt/rcm-mc
sudo git fetch origin main
sudo git checkout 6001ec1   # last commit before Phase 1 (or any safer point)
sudo docker compose -f RCM_MC/deploy/docker-compose.yml up -d --build
```

DB schema is untouched by Phase 1 — no migrations to undo.

### CSS-only regression

If the issue is purely visual (font 404, token typo, missing class), patch
`rcm_mc/ui/static/v3/chartis.css` and redeploy. Don't flip the flag — the
broken CSS only affects `?ui=v3` requests; other partners' sessions are fine.

(Phase 2/3/4/5 each get their own rollback section as they land.)

---

## Phase 2 rollback procedure

If Phase 2 ships and a regression appears post-merge to `main`:

### Local rollback (~3 min)

```bash
git checkout main
git revert <commit-range>  # the 11 commits e0cfdda..<commit-11> are atomic
git push origin main       # auto-deploys the revert
```

Phase 2 is pure-additive — every commit is independently revertable. If the regression is isolated to one block helper (e.g., the EBITDA drag rendering wrong on a specific deal), revert that single helper commit; the others stay. The orchestrator (`a3ad808`) imports conditionally; missing helpers degrade to no-render rather than raising.

**Time estimate:** ~3 minutes (commit + push + auto-deploy via `deploy.yml`).

### Production VM env-flag flip (~30 sec)

The editorial path is gated behind a per-request flag. To disable v3 instantly without redeploying:

```bash
ssh azureuser@pedesk.app
sudo nano /opt/rcm-mc/.env       # remove RCM_MC_UI_VERSION=v3 or set =v2
sudo systemctl restart rcm-mc
```

`/app` continues to render for `?ui=v3` query overrides but no longer for env-driven editorial; legacy `/dashboard` continues serving as today. Same flag pattern as Phase 1.

**Time estimate:** ~30 seconds (SSH + edit + restart). Fastest path; use first when uncertain.

### Disabling /app entirely (~5 min)

If `/app` itself is the regression (rare — rendering issues, not the route gate), patch `_route_app_page` in `rcm_mc/server.py` to 303 to `/dashboard` unconditionally. ~3 lines. Cherry-pick + push + redeploy.

**Time estimate:** ~5 minutes (cherry-pick + push + auto-deploy).

### DB-side regression

Phase 2 added zero schema changes. No migrations to undo.

### Communication threshold

Local revert and `/app`-specific patch both go through the auto-deploy pipeline visible to anyone watching `deploy.yml`. Env-flag flip is silent — invisible to anyone not on the VM. **Rule of thumb:** if you're using the env-flag path, no comms needed; if you're using either of the others, post a one-liner in whatever incident channel the team uses ("Reverting Phase 2 commit X due to <symptom>; ETA <minutes>").

(Phase 4/5 each get their own rollback sections as they land.)

---

## Phase 3 rollback procedure

If Phase 3 ships and a regression appears post-merge to `main`:

Phase 3 is **mostly** pure-additive but introduces one infrastructure change: every export writer now writes through the canonical-path facade. The facades are pure wrappers (no DB schema change), so revert is safe at either the commit level or the helper level. The discipline below is "minimum-viable-revert" — reach for the smallest blast radius first.

### Tier 1: single-helper revert (smallest blast radius)

Each of these 4 helper commits is independently revertable. The route handler degrades gracefully if a helper is missing — the block renders the empty-state, not a 500:

- `ffbca70` (initiatives) — revert if cross-portfolio aggregation breaks
- `fd8bd83` (PHI banner) — revert if banner contrast looks wrong on prod
- `45fda05` (covenant heatmap) — revert if Net Leverage row is wrong
- `c51a1a1` (EBITDA drag) — revert if bucketing surfaces a wrong number

```bash
git revert <commit-sha>
```

### Tier 2: coordinated revert (export-refactor chain)

These 5 commits are a chain — reverting one without the others creates mismatched call sites between the canonical facade and the writers that depend on it. Revert as a group if the canonical-path facade itself is broken:

- `87e8d5e` (deliverables wired to `generated_exports`)
- `261d7f0` (3 misc writers facaded)
- `9b07ff5` (3 packet/zip writers facaded)
- `a755cb2` (5 report writers facaded)
- `5e3e851` (`canonical_*_export_path` itself)

```bash
git revert 87e8d5e 261d7f0 9b07ff5 a755cb2 5e3e851
```

### Tier 3: full Phase 3 revert (last resort)

All 10 implementation commits + `0a747f1` (the test commit) + `<commit-11-sha>` (the docs commit). Branch returns to Phase 2 close. Use only if the regression spans both helper and infra work, or if root cause is unclear.

The contract suite + the `test_phase_3_todos_resolved` discipline gate will fail until the test-commit revert removes their assertions — revert `0a747f1` first or the helper-revert commits will appear to "fail tests" even though they're correct.

### Production VM env-flag flip (~30 sec, no code change)

Same pattern as Phase 2: set `CHARTIS_UI_V2=` (empty) on the VM. `/app` falls back to the legacy dark shell; editorial helpers stay imported but are not the default render path. Use this before any code revert if the regression is purely visual on the editorial dashboard — it's the cheapest reversible action available.

### DB-side regression

Phase 3 added zero schema changes. The `generated_exports` table existed before Phase 3 — Phase 3 only began *writing* through it as the canonical manifest. Existing rows are untouched. No migrations to undo.

### Communication threshold

Same rule as Phase 2: env-flag flip is silent, code revert is loud. If you revert any of the Phase 3 commits, post a one-liner.

(Phase 4/5 each get their own rollback sections as they land.)

---

## Discovered during local testing 2026-04-25

> **Status update 2026-04-26:** Issues #1, #3, and #4 below are resolved. #2 remains as Phase 2b/2c/2d destination work.
>
> - **#1** `?ui=v3` flag propagation: ✅ Fixed via `editorial_link()` helper (commit `cddde6a`) + brand-href fix
> - **#2** Topnav non-functional: ✅ Anchors with sensible defaults (commit `aacff1b`); destinations remain Phase 2b/2c/2d
> - **#3** No demo seed script: ✅ `rcm_mc/dev/seed.py` ships (commits `0db3e13`–`b2a2bf0`); see SEEDER_PROPOSAL.md resolution summary
> - **#4** Verification commands never validated: ✅ `--verify` flag runs them programmatically + integration tests in `tests/test_dev_seed_integration.py` exercise all 5 checks against a seeded DB


First end-to-end load of `/app?ui=v3` against an empty local DB surfaced four gaps that the per-helper unit tests + the contract suite did not catch (and were not designed to). Captured here as context preservation, **not as a work plan** — fixes attach to existing phases (Phase 2b/2c/2d for cross-cutting nav, separate seeder ticket for data, no-phase polish for the verification commands).

### 1. `?ui=v3` query flag does not propagate across navigation

Clicking the SeekingChartis logo from `/app?ui=v3` lands on legacy `/`. The flag is set on entry but every internal link rebuilds without it, dropping the user back into the dark legacy shell mid-session. Same issue applies to the topnav buttons (insofar as they navigate at all — see #2).

**Resolution path (Phase 2b prerequisite):** either (a) sticky flag propagation in all internal anchor builders, or (b) `RCM_MC_UI_VERSION=v3` env var so flag-passing isn't required at all. Option (b) is simpler operationally; option (a) preserves per-session A/B without a server restart. Pick at Phase 2b kickoff.

### 2. Topnav dropdowns are non-functional

The 5 editorial topnav sections (DEALS / ANALYSIS / PORTFOLIO / MARKET / TOOLS) render with caret affordances but do not open dropdowns or navigate anywhere. Their target pages haven't been ported to v3 — that's Phase 2b/2c/2d work, by design. The chrome ships ahead of the destinations so the editorial visual language is in place when the per-section ports land.

**Resolution path:** Phase 2b ports DEALS (deal profile editorial), Phase 2c ports ANALYSIS (workbench editorial), Phase 2d ports the remaining sections. Each phase removes the corresponding "decorative-only" line item here.

### 3. No demo seed script exists

`docs/DEMO_CHECKLIST.md` enumerates the data the dashboard needs to render meaningfully (3 hold deals + snapshots + initiative actuals + generated_exports + PHI mode), but never wires the operationalized way to populate it. First load tonight produced empty-state across every block — correctly, given an empty DB, but unusable as a partner-walkthrough surface.

**Resolution path:** tracked separately in `docs/design-handoff/SEEDER_PROPOSAL.md`. Pre-Phase-2b infrastructure work; produces a `seed_demo_db()` entry point invocable as `python -m rcm_mc.dev.seed --db <path>`.

### 4. DEMO_CHECKLIST verification commands never validated against a real run

The "Quick verification commands" section in `DEMO_CHECKLIST.md` was drafted from inferred SQL/CLI shape but never executed against a live DB. At least one command path likely needs adjustment — for example, the `'2025Q3'` literal threshold in the initiative-actuals check is correct as of 2026-04-25 but will go stale; the verification block should compute the threshold rather than hardcode it.

**Resolution path:** after the seeder lands, run all four verification commands against the seeded DB; correct any path/SQL drift; consider promoting the threshold computation to a small helper in `rcm_mc/dev/`.

---

## Visual-diff exit criterion

For solo work the bar is eyeball-level, but explicit. Before declaring "v3 page X matches reference HTML":

1. Open the reference file directly in a browser via `file://` URL
2. Open the deployed v3 page side-by-side via `?ui=v3`
3. Run through this checklist:
   - [ ] Brand mark identical (mark + name + italic on "Chartis")
   - [ ] Topbar height, dividers, padding match
   - [ ] Form-field shape, border, focus state match
   - [ ] Submit button: bg `var(--ink)`, text `.72rem`, letter-spacing `.14em`, hover → teal-deep
   - [ ] Fonts loaded — Source Serif 4 (headings), Inter (labels), JetBrains Mono (numbers / source paths). Network tab shows no font 404s
   - [ ] No box-shadows, no gradients, no border-radius > 0 except pills
   - [ ] Color contrast: ink-on-bg meets WCAG AA at body sizes
4. Save side-by-side screenshots into `docs/design-handoff/diffs/<route>.png` (one per shipped surface)
5. Sign off in the commit message: "visual diff: matches reference at 1280px and 1920px viewports"

Lighthouse a11y ≥ 95 (per spec §11.10) is **also required** before merge to `main`. Run via Chrome DevTools → Lighthouse panel; report the score in the merge comment.

---

## Pre-merge to main: DB backup

The cutover is the single highest-risk moment of the rework. Before merging `feat/ui-rework-v3` to `main`:

```bash
# On the production VM
ssh azureuser@pedesk.app
sudo docker compose -f /opt/rcm-mc/RCM_MC/deploy/docker-compose.yml \
  exec rcm-mc python -c "from rcm_mc.infra.backup import create_backup; print(create_backup())"

# Verify the backup file exists and is non-zero
sudo ls -lh /data/rcm/backup-*.db

# Confirm the file is restoreable on a separate test VM
# (out of scope here, but it's the canonical "did the backup work" check)
```

If the backup helper doesn't exist or fails, do NOT merge. The cost of pausing 30 minutes to fix is dwarfed by the cost of needing the backup post-merge and not having one.

This step is non-negotiable. Add it as a checkbox to every PR description that merges a Phase from this branch into `main`.

---

## Conventions for /app block helpers (Phase 2+)

These conventions apply to every paired-block helper in
`rcm_mc/ui/chartis/_app_*.py`. They were established during the
Phase 2 commit-1 API surface review and apply to commits 2–8 of
Phase 2 plus all subsequent dashboard helpers in Phase 2b/2c/2d.

### 1. Pre-computed inputs by default

Helpers receive their data pre-computed by the orchestrator. The
orchestrator (`app_page.render_app_page`) calls `portfolio_rollup()`
and `latest_per_deal()` once per request and hands the results to
every helper that needs them.

**Taking `store` directly requires a docstring justification** — typically
"this query cannot be batched into the orchestrator's primary fetch."
Reviewer challenge: if the justification doesn't fit in one sentence,
the helper probably belongs in the orchestrator, not as a leaf.

### 2. Helper owns its empty state

Each helper renders its own empty state. The empty-state copy is part
of the helper's contract; if a future page wants different copy for
the same block, it's a kwarg refactor, not an orchestrator change.

### 3. Block CSS lives in chartis.css, not inline

Module-scoped CSS lives in `/static/v3/chartis.css` under the
`/* === /app dashboard blocks === */` section header. Class names are
block-prefixed (`.app-kpi-strip-grid`, `.app-pipeline-funnel-bar`) so
collisions are impossible by construction.

**No inline `<style>` blocks per helper.** Inline styles would re-send
~5KB per `/app` render (uncacheable) and fight future high-contrast /
print / density mode overrides.

### 4. Deferred work uses `# TODO(phase N):` comments

The canonical deferral list is `grep -rn 'TODO(phase' rcm_mc/`.

A contract test (`test_phase_2_todos_resolved`, added in commit 10)
asserts that `grep -rn 'TODO(phase 2)' rcm_mc/` returns zero matches
after Phase 2 ships. Each subsequent phase adds the equivalent for
itself. This forces follow-through and prevents silent slippage.

**Phase 2 result:** the test caught one real violation on its first
run — `_app_pipeline_funnel.py:109` had a `TODO(phase 2)` for
preserving `?deal=<id>` across funnel stage clicks. Resolved in the
same commit (commit 10) by threading `focused_deal_id` through the
orchestrator → funnel link builder. Working as intended: discipline
test catches the deferral; resolution lands alongside, not after.

### 5. Helpers emit complete pairs

`render_*` returns a complete `<div class="pair">…</div>` ready to drop
into the orchestrator's body. The orchestrator just concatenates 9
of these — no "compose the pair externally" step.

### 6. Signature shape

`render_block(primary, *, secondary=...)`. Positional primary input is
what the helper renders; kwarg secondaries are context. Standard
Python convention; keeps call sites readable.

---

## Architectural decision: UI state via URL round-trips, not client-side state

**Decided in Phase 2 (2026-04-26).** All v3 UI state is encoded in the URL — query parameters like `?ui=v3`, `?deal=ccf_2026`, `?stage=hold`, `?tab=request`. There is no client-side state store. There is no JavaScript framework. Selecting a row in the deals table is a server round-trip; filtering the funnel is a server round-trip; switching tabs is a server round-trip.

**Why this is intentional, not an oversight:**

1. **Bookmarkability + shareability.** A partner can paste `/app?deal=ccf_2026` into Slack and the recipient sees the same focused-deal context. Every UI state is reproducible from its URL alone.
2. **Zero state-management complexity.** No framework, no store, no hydration mismatches, no "why is the UI showing one thing but the URL shows another" bugs.
3. **Server round-trips are invisible at this scale.** The platform isn't a real-time trading dashboard; it's a diligence tool. A 50–500ms round-trip is below the threshold of perceptible delay for navigation actions.
4. **Contract tests guard URLs, not JS behavior.** The contract test surface is HTTP-shaped — `?ui=v3 → 200 with editorial markers`. Client-side state would require a JS test framework that doesn't exist in this codebase, and adding one is out of scope.

**Future-reader note:** if you find yourself thinking "we should add client-side filtering for snappiness" or "we should hydrate the deal table with a JS framework," remember this was a deliberate architectural call. Statelessness is the feature, not the constraint. Reach for client-side state only if a measured perf budget cannot be met — and `docs/design-handoff/PHASE_2_PROPOSAL.md §3d-bis` confirms the budget is achievable without it.

The exception is Phase 3+ small interaction patches (e.g., the deferred KPI hover/click decision). Those are measured in lines of vanilla JS, not framework adoptions.

---

## Phase 3 — registered open questions before that phase begins

Surfaced during Phase 2 implementation; resolve before Phase 3 starts.

**Recommended sequencing: Q3.5 first.** It's the only one with a real product decision embedded ("where on the VM does the export pipeline write to? Currently variable per caller"). One-meeting decision that unblocks filesystem work. The other four wiring tasks (Q3.1-Q3.4) are all "implement against known data shapes" — they can parallelize once Q3.5 is decided. Q3.6 is conditional and runs last (only-if-needed). Doing Q3.5 last means by the time it's addressed, three Phase 3 commits will have worked around the problem and canonicalization has to undo their workarounds — cheap to surface now, expensive to discover later.

### Q3.1 — KPI cell hover/click interaction

**Status:** Deferred to Phase 4 polish (Phase 3 review, 2026-04-25). The partner-walkthrough demo doesn't depend on it; the right-side paired table being fixed to the headline KPI's history is acceptable until UX research informs the hover-vs-click decision. `_app_kpi_strip.py` retagged to `# TODO(phase 4):`.

Phase 2 deferred this per the C4 push-back: replacing the spec's hover with click would silently change UX semantics; adding hover via JS would expand the test surface beyond Phase 2's scope.

Phase 4 makes a deliberate UX call: hover via vanilla JS / click toggle / small-multiples view / palette-style filter. The decision drives whether the right-side paired table is fixed (today: Weighted MOIC), interactive (changes per cell), or replaced (small-multiples show all 8 KPIs simultaneously).

### Q3.2 — Real `covenant_grid` wiring + per-deal threshold mapping

**Status:** Resolved (Phase 3 commit 7, `45fda05`). Net Leverage row wired from `deal_snapshots.covenant_leverage`; 5 unwired covenants render `—` honestly with a footnote. Per-deal threshold accessor (`covenant_thresholds(deal_id)`) falls back to spec defaults — full per-deal config tracked in **Q4.5**.

`_app_covenant_heatmap.covenant_grid()` was a Phase 2 stub returning all-empty cells. Phase 3 wired the Net Leverage row to `deal_snapshots.covenant_leverage` ordered by `created_at DESC LIMIT 8` and reversed for display. Bands: ≤6.0x safe / ≤6.5x watch / >6.5x trip.

### Q3.3 — Real EBITDA-drag decomposition

**Status:** Resolved (Phase 3 commit 6, `c51a1a1`). 7 production `metric_key` strings mapped to 5 spec buckets via documented prefix table; unrecognized keys log INFO and fall through to "other". `net_collection_rate` routed to "other" (Decision B3) because it's a composite — see **Q4.6**.

`_app_ebitda_drag._decompose_drag()` was 5 uniform 20% placeholders when a packet had `ebitda_bridge` set. Phase 3 maps `DealAnalysisPacket.ebitda_bridge.per_metric_impacts` to the 5 spec components via the bucketing table; uses absolute values for percentage weighting and signed values for $ display. Self-pay bucket visible at 0% (Decision C) so the spec shape is preserved even when no actuals route there.

### Q3.4 — Cross-portfolio playbook signals on /app

**Status:** Resolved (Phase 3 commit 8, `ffbca70`). Trailing-4Q window default per C3 push-back. "Playbook gap" = mean ≤ -10% AND n_deals ≥ 2. `held_only=False` knob preserved for future cross-portfolio analytics. Time window is currently hardcoded at trailing 4 quarters; making it configurable from the UI surface is the open follow-up — registered as `# TODO(phase 4): make time window configurable` in `_app_initiative_tracker.py`.

`_app_initiative_tracker` Phase 2 stub showed empty-state copy when no deal was focused. Phase 3 implements cross-portfolio aggregation: groups by `initiative_id` across the held subset, computes mean variance + n_deals + is_playbook_gap, sorts by absolute variance, returns top 10. Held-only filter routed through `latest_per_deal` (deal_snapshots) because `list_deals` doesn't surface stage.

### Q3.5 — Live `exports/` folder for deliverables (DO FIRST)

**Status:** Resolved (commits 1–5: `5e3e851`, `a755cb2`, `9b07ff5`, `261d7f0`, `87e8d5e`). Canonical path = `/data/exports/<deal_id>/<timestamp>_<filename>` (or `/_portfolio/`). 11 writers facaded; `_app_deliverables` reads from `generated_exports` first, falls back to `analysis_runs`. The "two named functions" design (Q2 push-back) is now load-bearing — collapsing into one `Optional[str]` would re-introduce the silent mis-routing failure mode.

`_app_deliverables` Phase 2 shipped HTML-only from `analysis_runs`. Phase 3 reads `generated_exports` as the primary manifest, with `analysis_runs` as fallback. Card href strips `/data/exports/` prefix → `/exports/<rest>`; sizes formatted as B / KB / MB.

### Q3.6 — Scroll-aid affordance (only if needed)

**Status:** Deferred to Phase 4 (still conditional on usage signal, not pre-emptive). `app_page.py` retagged to `# TODO(phase 4):`. Re-evaluate after the demo + 30 days of partner usage. The Phase 3 review confirmed the conditional should remain conditional — pre-emptively adding sticky TOC / scroll-spy without real signal would impose IA structure that wasn't asked for.

### Q3.7 — PHI banner visual weight reduction

**Type:** Polish · CSS-only · Low risk
**Status:** Resolved (Phase 3 commit 9, `fd8bd83`). Editorial helper only; legacy `_chartis_kit` banner copy unchanged so legacy-page assertions continue to pass. `--green-muted: #3D6F45` token added; padding `.35rem 1.5rem`, font-size `.75rem`, weight 500, letter-spacing `.02em`. Copy trimmed to "🛡 Public data only — no PHI".
**Trigger:** Address before next stakeholder demo OR during Phase 3 polish pass, whichever comes first.

#### Problem

The current PHI banner is functionally correct but visually dominant. At ~50px tall with full-saturation green and the verbose copy "🛡️ Public data only — no PHI permitted on this instance.", it occupies disproportionate visual real estate on every page and competes with the editorial design system's restrained aesthetic.

User feedback (informal, 2026-04-26): "can we make this more lowkey." The banner remains a non-negotiable compliance surface but its current visual weight exceeds what's needed to communicate the constraint.

#### Constraints (non-negotiable)

- Banner MUST remain present on every authenticated page
- Banner MUST NOT be dismissible (no close button, no cookie-based dismissal, no `RCM_MC_PHI_BANNER_HIDDEN` env override)
- Banner MUST remain visible without scrolling on standard viewports (≥768px wide)
- Compliance signal strength is non-negotiable: anyone viewing any page must see the disclaimer without action

These constraints exist because:

1. The banner is the system's documented disclaimer that this instance does not accept PHI. Removing prominence weakens the legal posture (HIPAA-adjacent system + healthcare PE diligence platform = audit-relevant surface).
2. Users most likely to make a PHI mistake are also most likely to dismiss/ignore reduced-visibility warnings. Permanence is a feature.
3. Existing contract test `test_v3_authenticated_pages_render_phi_banner` asserts the banner's presence in rendered HTML — must continue passing.

#### Proposed implementation

**File:** `RCM_MC/rcm_mc/ui/static/v3/chartis.css`
**Section:** `.phi-banner` (search the file for the existing rule block)

| Property | Current | Proposed |
|---|---|---|
| height (or padding) | ~50px total visual height | ~28px total visual height (reduce vertical padding) |
| background | `var(--green-deep)` (full saturation forest green) | `var(--green-muted)` — new token, ~30% less saturation |
| font-size | ~14–16px | 12px |
| font-weight | bold | medium (500) |
| text content | "🛡️ Public data only — no PHI permitted on this instance." | "🛡️ Public data only — no PHI" |
| letter-spacing | normal | 0.02em (slight, for legibility at small size) |

**New token to add to `:root` block in same file:**

```css
--green-muted: #4A7A52;  /* darker, less saturated than --green-deep */
```

(Verify exact hex against the editorial palette in `chartis_tokens.css`. The goal is "still recognizably green and authoritative, but ~30% less optical weight than the current bar.")

#### What NOT to do

- Do not add a dismiss button or close icon (×)
- Do not implement cookie-based or session-based dismissal
- Do not reduce contrast below WCAG AA (4.5:1 for body text on the banner background)
- Do not move the banner below the fold
- Do not make it conditional on any user state, role, or env flag (other than the existing `RCM_MC_PHI_MODE` which controls whether PHI is allowed at all, not whether the banner shows)
- Do not change anything in the Python rendering layer — `phi_banner(mode)` helper signature stays identical

#### Acceptance criteria

1. Visual diff against current state shows the banner is meaningfully less visually dominant (~40% reduction in optical weight). Eyeball test against `04-command-center.html` or any current `?ui=v3` page.
2. Contract test `test_v3_authenticated_pages_render_phi_banner` continues to pass without modification.
3. Banner remains visible on the dashboard at `/app?ui=v3` at 1280px viewport without scrolling.
4. WCAG AA contrast verified for the new green against white text (any contrast checker; ratio must be ≥4.5:1).
5. No JavaScript added; pure CSS change.

#### Estimated effort

15–30 minutes. Single CSS file edit, ~6 line changes. No tests to write (existing contract test guards the requirement that matters). No Python changes.

#### Dependencies / blocks

- **Blocks:** none — can ship anytime in Phase 3
- **Blocked by:** none — no other Phase 3 question depends on this resolving first
- **Adjacent:** if Phase 3 also tackles Q3.1 (KPI hover/click) at the same time, do this one first — KPI hover changes are bigger surface area; PHI banner is a 30-min warmup that doesn't risk scope contamination

#### Decision authority

- Visual style call (exact green hex, exact height, exact text): user (Andrew)
- Implementation: Claude Code can ship without further architectural review, since it's CSS-only inside an established component
- Compliance posture changes (dismissibility, permanence, content): require explicit user decision documented in `UI_REWORK_PLAN.md` — none requested here

#### Notes for future contributors

If this ticket gets reopened in a future phase asking for further visual reduction or dismissibility, refer back to the "Constraints (non-negotiable)" section above. The current visual treatment was deliberately reduced from a more aggressive baseline; further reduction past this point starts trading compliance signal for aesthetics. That trade requires explicit product + legal input, not just a visual preference.

---

## Phase 4 — registered open questions before that phase begins

Surfaced during the Phase 1 IA pass; need explicit decisions before Phase 4 cutover.

### Q4.1 — `/` reroute (the cutover decision)

**Status:** ✅ Resolved (2026-04-27, commit pending). When v3 mode is active (env `CHARTIS_UI_V2=1` OR per-request `?ui=v3`):

- **Authenticated users** → 303 redirect to `/app` (the editorial dashboard)
- **Anonymous visitors** → marketing splash (preserves the public landing for acquisition)

This is the nuanced split from option 1's "redirect / to /app" framing — the design intent of `/` being **both** a marketing surface AND a dashboard entry point depending on auth state. Authenticated partners typing the bare domain land on the dashboard; anonymous visitors see the splash.

The legacy codebase serves the dashboard at `/`. Spec §2 reroutes `/` to the marketing landing page in v3. **This is the single most user-visible change in the entire rework.**

**Risk:** Bookmarks break. External monitors that hit `/` for an auth challenge see HTML instead. Partner muscle memory (years of typing the bare domain to get the dashboard) breaks. → **Mitigated**: authenticated partners still land on a dashboard (just `/app` instead of legacy `/dashboard`), so muscle memory carries through. Anonymous monitors still see HTML.

**Resolved-by:**

1. Decision: authenticated v3 → `/app`; anonymous v3 → marketing splash.
2. Contract test shipped: `test_q4_1_root_redirects_to_app_for_authenticated_v3_users` locks the redirect behavior.
3. Comms plan: needed before merge to main — partners must know `/` will redirect to `/app` after the env-default flips to `CHARTIS_UI_V2=1`.

### Q4.2 — Existing `/dashboard` and `/home` routes

If `/` reroutes, do `/dashboard` and `/home` stay as legacy aliases (302), get repurposed, or 410? Decide alongside Q4.1.

### Q4.3 — `/engagements` (must resolve before Phase 2 begins)

Surface unknown. Listed in `_CORPUS_NAV` but no obvious purpose from the route name. Action: visit it on a running instance, identify what it does. If real, place in PORTFOLIO. If dead, drop. If unanswered when Phase 2 begins, default to dropping (route returns 410).

### Q4.4 — Phase 5 legacy-nav archive

Before deleting `_CORPUS_NAV_LEGACY` in Phase 5, dump its 171 entries to `docs/design-handoff/legacy-nav-archive.md` with a header:

> *"These 171 nav entries existed in the pre-rework codebase. If you're looking for a destination that no longer appears in the topnav, search this archive — it may have been a real surface that was deprecated, or a placeholder that was never built. Removed in commit X of Phase 5."*

This preserves institutional memory at zero ongoing cost and makes the deletion safely reversible. **The archive must exist before the Phase 5 deletion commit lands.**

### Q4.5 — Covenant schema expansion

**Trigger:** Phase 3 commit 7 (`45fda05`) wired Net Leverage from real data (`covenant_leverage` column on `deal_snapshots`). The other 5 spec covenants (Interest Coverage, Days Cash on Hand, Fixed Charge Coverage, DSCR, Debt-to-EBITDA peer) render `—` honestly with a footnote.

**Required before Phase 4 merge:**

1. Decision: extend `deal_snapshots` with named columns vs. introduce a `covenant_metrics(snapshot_id, covenant_name, value, threshold)` table. Recommendation: the second option — covenants are a true 1-many from snapshots, and the named-column path forces a migration every time the spec covenant set changes. Per-deal threshold config lives there too (resolves the threshold half of Q3.2).
2. Migration: add the table + a backfill that derives the 5 missing covenants from existing `deal_sim_inputs` where possible.
3. Update `covenant_grid()` to read from the new table; remove the "1 of 6 covenants tracked" footnote when `wired_count == 6`.
4. Contract test extension: assert `wired_count == 6` post-migration. Update `test_v3_app_covenant_heatmap_footnote_present` accordingly.

**Estimated effort:** ~half a day (migration + helper rewrite + 2 tests).

### Q4.6 — `net_collection_rate` composite decomposition

**Trigger:** Phase 3 commit 6 (`c51a1a1`) routed `net_collection_rate` to the "other" EBITDA-drag bucket (Decision B3). Reason: it's a composite of patient self-pay leakage + payer underpayment + write-offs. Routing it to a single component (e.g. "Self-pay leakage", which was the initial B1 proposal) would actively mislead partners about which lever to pull.

**Why not ship a documented attribution assumption now (B-2 alternative considered):** the temptation to ship something like "we attribute net_collection_rate variance ⅔ to payer underpayment, ⅓ to self-pay" with a code-comment caveat *feels* responsible because it's documented, but creates the same misdirection problem as B1 with a paper trail. The dashboard label says "Self-pay 67%"; the partner reads the label, not the comment. Once shipped, the number becomes load-bearing for the next "but you told me last quarter it was 67%" conversation. Decision: stay B3 (Other) until real upstream feed split data arrives.

**Required before Phase 4 merge:**

1. Decision: surface a 6th drag bucket ("Payer underpayment" or "Self-pay leakage") and decompose `net_collection_rate` against it, OR keep the 5-bucket model and add a "Composite" expansion-only secondary view.
2. If decomposing: requires the upstream payer/self-pay split from the data feed — a stated-assumption fallback is explicitly ruled out per the reasoning above.
3. Update the unrecognized-prefix logger to no longer fire for `net_collection_rate`.
4. Contract test extension: assert the new bucket renders when present in `per_metric_impacts`.

**Estimated effort:** depends on (1). Pure UI re-routing once feed data is in is ~1 hour; the upstream feed split is a larger data-pipeline question that may need its own ticket.

---

## See also

- [`docs/design-handoff/EDITORIAL_STYLE_PORT.md`](design-handoff/EDITORIAL_STYLE_PORT.md) — the spec
- [`docs/design-handoff/IA_MAP.md`](design-handoff/IA_MAP.md) — full nav inventory + section assignments
- [`docs/DEMO_CHECKLIST.md`](DEMO_CHECKLIST.md) — pre-demo data + walkthrough script + recovery
- [`tests/test_ui_rework_contract.py`](../tests/test_ui_rework_contract.py) — the 25 contract tests guarding this work
- [`AZURE_DEPLOY.md`](../../AZURE_DEPLOY.md) — production deploy procedure
