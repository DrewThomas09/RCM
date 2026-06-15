# Ghost-page migration plan — surfacing the buried work

_Audit date: 2026-06-15. Regenerate the numbers any time with
`PYTHONPATH=. python scripts/audit_ghost_pages.py`._

> **Status (2026-06-15): Waves 0–2 shipped.** Front-facing pages **179 → 310**;
> illustrative-gated **174 → 43** (only the 42 seed-corpus + 1 synthetic remain);
> uncategorized manifest rows **211 → 19** (the rest are internal/admin/downloads).
> Waves 3–4 (seed-corpus data wiring + the one synthetic page) are the remaining
> backlog.

## TL;DR

We have built **382 page routes**. Only **179** are front-facing in `/tools`
today. The rest is real work that renders but a partner can't *discover* by
browsing. It is **not** lost — it is buried by two fixable mechanisms, neither
of which requires tearing down the data-honesty system:

1. **Stale ranking manifest** — `_surface_rankings.py` is auto-generated but
   was not regenerated after recent pages landed, so the newest work
   (Benchmark Reference, J-Code Atlas, Texas Infusion · Cont., Cross-Dataset
   Analysis, Further Analysis, Data APIs, RxNorm…) never reached the nav bars
   or the `/best/<section>` catalogs. **Fixed in this PR** (regenerated; 11
   recent real pages now surface; nav/ranking tests green).

2. **Section-resolution gap** — **211** of the 341 ranked pages resolve to an
   `uncategorized` bucket that **no `/best/<section>` page renders**, because
   `_SUB_SECTION_MAP` doesn't list them and the ranker never falls back to the
   `_heuristic_section()` classifier that already exists in `server.py`. That
   classifier can auto-place **186 of the 211** into their correct section.

Separately, **174 pages are gated out of `/tools`** via
`_TOOLS_ILLUSTRATIVE_ROUTES`. But by the codebase's *own* honesty classifier
(`surface_status.classify_surface`), **120 of those are honest** (calculators
that compute off your inputs, or pages that activate on your uploaded data) and
**11 are real-data GREEN pages mislabeled** as illustrative. Only **42 (seed
corpus) + 1 (synthetic)** genuinely need data work before they front-face.

So the headline: **most of the "ghost" work can be surfaced mechanically and
honestly. ~43 pages genuinely need a data decision.**

## The inventory

| Bucket | Count | What it is | Front-face treatment |
|---|---:|---|---|
| Front-facing today | 179 | in `/tools` + nav + palette | — (done) |
| **Real, just buried** (stale manifest) | ~11 | recent green/navy pages dropped from manifest | **Wave 0 — regenerate manifest (done)** |
| **Uncategorized → no catalog** | 211 ranked | resolve to no `/best/<section>` | Wave 1 — section resolution (186 auto) |
| GREEN mislabeled illustrative | 11 | real CMS/public data, wrong list | Wave 2 — un-gate now |
| NAVY (honest calculators) | 80 | "computes off your inputs" | Wave 2 — un-gate now |
| DATA_REQUIRED (honest) | 40 | "activates on your uploaded data" | Wave 2 — un-gate now |
| YELLOW (seed corpus) | 42 | realistic-but-illustrative figures | Wave 3 — data decision |
| RED (synthetic) | 1 | `/ma-star`, deferred-with-reason | Wave 4 — staged ingest |
| Legitimately hidden | 70 | POST-only / parametric / auth / redirects | leave hidden |
| True ghosts | 4 | `.csv`/debug endpoints (not pages) | leave hidden |

Buckets overlap (an illustrative page is also uncategorized); the waves are
ordered so each fixes one mechanism. Full per-route lists are in the appendix
of `scripts/audit_ghost_pages.py` output.

## How "front-facing" actually works (so the fixes are surgical)

- **Top nav**: `_CORPUS_NAV` → 7 sections. Each section's bar is built by
  `_ranked_subnav_items()` = `_NAV_FLAGSHIPS` pins + ranked backfill from
  `_surface_rankings.RANKINGS[section]`, **tier-gated** to green/navy/
  data_required (yellow/red demoted to `/best/<section>`), minus
  `_NAV_DEMOTED` utilities.
- **`/best/<section>`**: the *full* ranked list for that section, with honest
  tier dots. This is where buried-but-honest pages belong.
- **`/tools`**: flat catalog = `_discover_all_routes()` (every page **except**
  `_TOOLS_HIDDEN_ROUTES` and `_TOOLS_ILLUSTRATIVE_ROUTES`).
- **Cmd+K palette**: `_DEFAULT_PALETTE_MODULES` — jump-to.
- **Breadcrumbs / active-nav**: `_resolve_sub_section()` via `_SUB_SECTION_MAP`.

A page is "buried" when it is missing from the ranked manifest *and* the
palette, or when it ranks but resolves to `uncategorized` (no catalog renders
it), or when it is gated out of `/tools` as illustrative.

## The plan — five waves

### Wave 0 — Regenerate the stale manifest ✅ (this PR)
- Ran `python scripts/rank_surfaces.py`; manifest now ranks 341 surfaces.
- Surfaces 11 recent real pages into nav backfill + `/best/<section>`.
- `tests/test_surface_rankings.py`, `test_nav.py`, `test_subnav_integrity.py`,
  `test_command_palette.py`, `test_universal_palette.py`,
  `test_nav_ranked_rail.py`, `test_surface_visibility.py` all green.
- **Make this self-healing**: add a CI/pre-commit check (or a test) that fails
  if `rank_surfaces.py` would change `_surface_rankings.py` — so the manifest
  can never silently go stale again.

### Wave 1 — Fix section resolution ✅ (this PR)
Routed the 211 uncategorized pages into their `/best/<section>` catalogs +
nav backfill + breadcrumbs. **No fake data is exposed as real** — tier dots
still apply. Result: **uncategorized 211 → 19** (the 19 are internal/admin/
`.xlsx` routes that correctly stay out).
- `rank_surfaces.py` `build_rankings()` now falls back to
  `server._heuristic_section(route)` when `_resolve_sub_section` returns None,
  keeping only nav-section verdicts (its `more`/`other` results stay
  uncategorized so auth/admin/downloads don't front-face).
- Added the CMS vertical slugs (`/nursing-homes`, `/dialysis`, `/home-health`,
  `/hospice`, `/long-term-care-hospital`, `/inpatient-rehab`,
  `/data-activation`) to `_SUB_SECTION_MAP` → `library`.
- Manifest regenerated; section counts jumped (diligence 48→163, portfolio
  4→28, research 38→52, library 14→39, pipeline 8→17, home 3→8).

### Wave 2 — Un-gate the honest pages ✅ (this PR) — 11 GREEN + 120 navy/data_required
These are honest by `surface_status`'s own definition but were hidden as if
fake. Removed all 131 from `_TOOLS_ILLUSTRATIVE_ROUTES`; **front-facing pages
179 → 310**, **illustrative-gated 174 → 43**.
- They now flow into `/tools` with their honest tier dot — `live` (green),
  `computed` (navy), `needs data` (data_required) — enforced by
  `test_tools_index_cards.test_status_reflects_real_surface_tier`.
- `test_tools_index_cards.test_every_az_card_returns_200` boots a real server
  and confirms all 310 cards render 200.
- Added a global label de-dup to `tools_showcase_page` so a destination shown
  in two workspaces (e.g. "Benchmarks" in Diligence + Library) renders once.
- The in-page `ck-illus-note` honesty strips are unchanged (their tests stay
  green); for navy calculators the strip honestly flags the illustrative
  *defaults*. Follow-up polish: reword the strip on navy pages to "Illustrative
  defaults — edit inputs to compute on your deal."

### Wave 2.5 — Universal Cmd+K palette ✅ (this PR)
Only 4 of the 120 un-gated calculators were in `_DEFAULT_PALETTE_MODULES`.
Rather than hand-add 120 entries (and risk the same staleness), the palette is
now **augmented from the ranking manifest** at render time
(`_augmented_palette_modules()`): every route in a named nav section that isn't
already curated, internal, or a redirect/parametric slug. Curated titles win.
Result: palette **191 → 348** entries; all 157 additions verified to render 200
(booted server). Self-maintaining — a new ranked page is Cmd+K-reachable the
moment it ships.

### Guardrail ✅ (this PR) — `tests/test_surface_manifest_fresh.py`
Fails CI if `_surface_rankings.py` differs from what `rank_surfaces.py` would
generate, so the manifest can never silently go stale again (the root cause of
the original ghosts). Fix on failure: `python scripts/rank_surfaces.py`.

### Wave 3 — Seed-corpus pages (42 YELLOW) — data decision
Each presents realistic figures on the bundled illustrative seed corpus.
Per page, choose one:
- **(a) Wire real data** → graduates to green/navy, front-faces automatically
  (the honest, higher-effort path; this is the existing "workstream G"
  backlog). Best for the high-value reads (`/sponsor-league`,
  `/specialty-benchmarks`, `/vintage-perf`, `/irr-dispersion`,
  `/market-rates`…).
- **(b) Surface with the existing ILLUSTRATIVE chip** in `/best/<section>`
  only (not the top bar — tier gate already does this) + a one-line "what
  would make this real" explainer. Honest, immediate, low effort.
- **(c) Leave gated** if the page is redundant with a real one.

### Wave 4 — Synthetic (`/ma-star`)
CMS MA Star Ratings is zip-portal only. Build the staged ingest (see
`docs/reports/RED_PAGE_ACTIVATION_PLAN.md`) or keep it deferred-with-reason.

## Guardrails (so we don't re-create ghosts)
1. Manifest-freshness check in CI (Wave 0).
2. A test asserting every `path == "/x"` page route is either front-facing
   (manifest/palette) or explicitly in `_TOOLS_HIDDEN_ROUTES` /
   `INTERNAL_ROUTES` — no silent orphans.
3. When a page graduates off illustrative data, drop it from
   `_TOOLS_ILLUSTRATIVE_ROUTES` in the same PR.

## Decision (2026-06-15): Waves 0–2 — shipped
Chosen approach: surface everything *already real* **and** un-gate the 131
honest pages (navy calculators + data-required + 11 mislabeled GREEN), while
keeping the 42 seed-corpus (yellow) + 1 synthetic (red) gated until data-wired.
Honesty-preserving: every surfaced page carries its real tier dot.

### Remaining backlog
- **Wave 3** — wire real data into the 42 seed-corpus pages (or surface each
  with its ILLUSTRATIVE chip), highest-value reads first
  (`/sponsor-league`, `/specialty-benchmarks`, `/vintage-perf`,
  `/irr-dispersion`, `/market-rates`).
- **Wave 4** — `/ma-star` staged CMS ingest.
- Taxonomy polish: `_heuristic_section` folds sourcing into `pipeline` and
  sends many PE-math pages to `diligence` (now 163 rows) — refine the
  section split so `/best/diligence` isn't overloaded.
- Remove the redundant curated `/deals-library` palette entry (301 → /library).
