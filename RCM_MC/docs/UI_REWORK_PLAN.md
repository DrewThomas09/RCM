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

(Phase 3/4/5 each get their own rollback sections as they land.)

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

Phase 2 deferred this per the C4 push-back: replacing the spec's hover with click would silently change UX semantics; adding hover via JS would expand the test surface beyond Phase 2's scope. `_app_kpi_strip.py` carries a `# TODO(phase 3): KPI cell hover/click interaction` comment.

Phase 3 makes a deliberate UX call: hover via vanilla JS / click toggle / small-multiples view / palette-style filter. The decision drives whether the right-side paired table is fixed (today: Weighted MOIC), interactive (changes per cell), or replaced (small-multiples show all 8 KPIs simultaneously).

### Q3.2 — Real `covenant_grid` wiring + per-deal threshold mapping

`_app_covenant_heatmap.covenant_grid()` is a Phase 2 stub returning all-empty cells. Phase 3 wires it to `quarterly_snapshots` + per-deal threshold config. The threshold mapping is currently in `deal_sim_inputs` per-deal but not surfaced for v3 — Phase 3 needs a `covenant_thresholds(deal_id)` accessor.

### Q3.3 — Real EBITDA-drag decomposition

`_app_ebitda_drag._decompose_drag()` returns 5 uniform 20% placeholders when a packet has `ebitda_bridge` set. Phase 3 maps the `DealAnalysisPacket.ebitda_bridge` shape to the 5 spec components (Denial workflow gap / Coding-CDI miss / A/R aging / Self-pay leakage / Other) with real per-component dollar impacts. Recovery quarters table + recovery sparkline are Phase 3 too.

### Q3.4 — Cross-portfolio playbook signals on /app

`_app_initiative_tracker` Phase 2 stub: when no deal is focused, shows empty-state copy. Phase 3 implements cross-portfolio aggregation (top variances across all held deals). Spec §6.9 mentions "playbook gap — not a deal-specific issue" — that's the aggregation Phase 3 wires up.

### Q3.5 — Live `exports/` folder for deliverables (DO FIRST)

`_app_deliverables` Phase 2 ships HTML-only from `analysis_runs`. Phase 3 reads the `exports/` filesystem folder for CSV / JSON / XLS artifacts (with sizes from `os.stat()`).

**Embedded product decision:** where on the VM does the export pipeline write to? Currently variable per caller — multiple callsites write to different paths. Until that's standardized, every Phase 3 wiring task that touches deliverables has to either pick a path (creating a fourth variant) or special-case the existing variants (carrying tech debt forward). One meeting establishes the canonical path; subsequent Phase 3 tasks write against the standard.

### Q3.6 — Scroll-aid affordance (only if needed)

Phase 2 ships /app as single-flat-scroll matching the reference HTML (per W4 push-back). `app_page.py` carries a `# TODO(phase 3): consider scroll-aid affordance (sticky TOC? scroll-spy?) IF post-launch usage shows partners getting lost` comment. This is conditional — only acts on real usage signal, not pre-emptive. Run last.

---

## Phase 4 — registered open questions before that phase begins

Surfaced during the Phase 1 IA pass; need explicit decisions before Phase 4 cutover.

### Q4.1 — `/` reroute (the cutover decision)

The legacy codebase serves the dashboard at `/`. Spec §2 reroutes `/` to the marketing landing page in v3. **This is the single most user-visible change in the entire rework.**

**Risk:** Bookmarks break. External monitors that hit `/` for an auth challenge see HTML instead. Partner muscle memory (years of typing the bare domain to get the dashboard) breaks.

**Required before Phase 4 merge:**

1. Explicit decision: does `/` redirect to `/app`? Or does `/` stay as the dashboard for authenticated users and only render marketing for anonymous users?
2. New contract test: `test_authenticated_user_lands_on_dashboard_at_root` — when authenticated, GET `/` returns the dashboard or 302s to it. Locks the chosen behavior so a future commit can't silently regress it.
3. Comms plan: if `/` → marketing, partners must be told before merge, with the new dashboard URL in the announcement.

### Q4.2 — Existing `/dashboard` and `/home` routes

If `/` reroutes, do `/dashboard` and `/home` stay as legacy aliases (302), get repurposed, or 410? Decide alongside Q4.1.

### Q4.3 — `/engagements` (must resolve before Phase 2 begins)

Surface unknown. Listed in `_CORPUS_NAV` but no obvious purpose from the route name. Action: visit it on a running instance, identify what it does. If real, place in PORTFOLIO. If dead, drop. If unanswered when Phase 2 begins, default to dropping (route returns 410).

### Q4.4 — Phase 5 legacy-nav archive

Before deleting `_CORPUS_NAV_LEGACY` in Phase 5, dump its 171 entries to `docs/design-handoff/legacy-nav-archive.md` with a header:

> *"These 171 nav entries existed in the pre-rework codebase. If you're looking for a destination that no longer appears in the topnav, search this archive — it may have been a real surface that was deprecated, or a placeholder that was never built. Removed in commit X of Phase 5."*

This preserves institutional memory at zero ongoing cost and makes the deletion safely reversible. **The archive must exist before the Phase 5 deletion commit lands.**

---

## See also

- [`docs/design-handoff/EDITORIAL_STYLE_PORT.md`](design-handoff/EDITORIAL_STYLE_PORT.md) — the spec
- [`docs/design-handoff/IA_MAP.md`](design-handoff/IA_MAP.md) — full nav inventory + section assignments
- [`tests/test_ui_rework_contract.py`](../tests/test_ui_rework_contract.py) — the 12 contract tests guarding this work
- [`AZURE_DEPLOY.md`](../../AZURE_DEPLOY.md) — production deploy procedure
