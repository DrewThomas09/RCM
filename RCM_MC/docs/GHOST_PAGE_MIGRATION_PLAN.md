# Ghost-page migration plan — surfacing the buried work

_Audit date: 2026-06-15. Regenerate the numbers any time with
`PYTHONPATH=. python scripts/audit_ghost_pages.py`._

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

### Wave 1 — Fix section resolution (mechanical, honesty-preserving)
Route the 211 uncategorized pages into their `/best/<section>` catalogs +
nav backfill + breadcrumbs. **No fake data is exposed as real** — tier dots
still apply.
- In `rank_surfaces.py` `build_rankings()`, when `_resolve_sub_section(route)`
  is None, fall back to `server._heuristic_section(route)` (auto-places 186).
- Add the ~5 CMS vertical slugs the heuristic sends to `more`
  (`/nursing-homes`, `/dialysis`, `/home-health`, `/hospice`,
  `/long-term-care-hospital`) to `_SUB_SECTION_MAP` → `library`.
- Keep the ~20 internal/download routes (auth/admin/`.xlsx`) uncategorized —
  they should not front-face (already covered by `_surface_visibility`).
- Regenerate manifest; verify `/best/<section>` counts jump and
  `test_subnav_integrity` stays green.

### Wave 2 — Un-gate the honest pages (11 GREEN + 120 navy/data_required)
These are honest by `surface_status`'s own definition but hidden as if fake.
- Remove the 11 GREEN + 80 NAVY + 40 DATA_REQUIRED routes from
  `_TOOLS_ILLUSTRATIVE_ROUTES`. They flow into `/tools` with their honest
  tier dot (navy = "calculator", purple = "data required", green = "live").
- Add the highest-value ~30–40 to `_DEFAULT_PALETTE_MODULES` (today only 4 of
  120 are in the palette).
- **Per-page render check** first: a few GREEN pages may still emit a stray
  `ck-illus-note` strip; drop the strip as each graduates (the exclusion list
  was derived by scanning for that strip).
- Update `test_tools_*` / `test_surface_visibility` expectations.

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

## Decision needed
Waves 0–1 are mechanical and honesty-preserving — safe to ship now. **Wave 2
(surfacing 131 honest-but-currently-hidden pages) and Wave 3 (42 seed-corpus
pages) change the product's front face**, so confirm the approach before the
bulk migration:
- **Conservative**: Waves 0–1 only (make everything *already real* browsable).
- **Recommended**: Waves 0–2 (also un-gate the 131 honest pages; yellow/red
  stay gated until data-wired).
- **Full send**: Waves 0–3 (surface everything now with honest tier chips).
