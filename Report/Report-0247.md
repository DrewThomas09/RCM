# Report 0247: Merge Risk Scan — `feat/ui-rework-v3` Diff

## Scope

Diff of `origin/main..origin/feat/ui-rework-v3` (59 commits, per Reports 0186/0206/0216/0246). Branch has been live longest among feature branches and has the highest divergence. Sister to Reports 0007/0037/0067/0097/0127/0157/0187/0217 (merge-risk cadence).

## Findings

### Top-line stat

`51 files changed, 14637 insertions(+), 924 deletions(-)` — net **+13.7K LOC**.

### Biggest churn (insertions)

| File | LOC | Type |
|---|---|---|
| `ui/static/v3/chartis.css` | +1033 | NEW — design tokens v3 |
| `dev/seed.py` | +896 | NEW — demo seeder |
| `tests/test_ui_rework_contract.py` | +840 | NEW — contract tests |
| `ui/_chartis_kit_editorial.py` | +763 | NEW — editorial kit |
| `docs/UI_REWORK_PLAN.md` | +661 | NEW — design plan |
| `docs/design-handoff/reference/01-landing.html` | +663 | NEW — design ref |
| `docs/design-handoff/reference/04-command-center.html` | +653 | NEW |
| `docs/design-handoff/reference/cc-app.jsx` | +753 | NEW — JSX reference |
| `exports/canonical_facade.py` | +424 | NEW — exports facade |
| `ui/chartis/_app_covenant_heatmap.py` | +428 | NEW |
| `ui/chartis/_app_initiative_tracker.py` | +371 | NEW |

### Deletions

| File | LOC | Risk |
|---|---|---|
| `ui/_chartis_kit_v2.py` | -600 | **DELETED** — replaced by `_chartis_kit_editorial.py` |

### Schema changes

**Zero `*.sql` or `store.py` changes** in diff — confirmed via filter. UI-rework branch is **schema-clean**. Cross-link Reports 0118/0167/0211 (FK frontier).

### New top-level packages

| Package | Files | Note |
|---|---|---|
| `rcm_mc/dev/` | 2 | NEW — `__init__.py` (7L) + `seed.py` (896L). **First time `dev/` appears.** |
| `rcm_mc/exports/` | 1 | New file `canonical_facade.py` (424L). |
| `rcm_mc/infra/` | 1 NEW + 1 mod | `exports.py` (NEW 225L) + `morning_digest.py` (+13L) |
| `rcm_mc/rcm/` | 1 | `initiative_tracking.py` (NEW 154L) |
| `rcm_mc/ui/chartis/` | 11 NEW | 10 `_app_*.py` + `app_page.py` + `forgot_page.py` + `login_page.py` |

### Server.py modifications

`server.py` +217 LOC (no `def` signatures broken — verified via grep). Likely route additions for new chartis pages. **Risk:** new routes may collide with existing dashboard routes if both branches register paths in same lookup dict.

### Modified existing files

| File | LOC delta | Risk |
|---|---|---|
| `screening/dashboard.py` | +69 | likely behavior change — cross-link Report 0095 (screening logic) |
| `ui/dashboard_page.py` | +321 (mostly mod) | substantial rewrite |
| `ui/_chartis_kit.py` | +206 (heavy mod) | core UI helper |
| `ui/conference_page.py` | +9 | minor |
| `ui/exports_index_page.py` | +4 | minor |
| `ui/portfolio_risk_scan_page.py` | +21 | minor |

### Recent commits (top of branch)

- `ca85e0d` docs(audit): bankruptcy_survivor intentional bypass
- `c3d8e5f` feat(screening): editorial port — pass through chartis_shell()
- `80223e4` fix(dashboard_page): mechanical color-token swap
- `2833957` fix(editorial-chrome): topnav active state
- `118d8c5` fix: covenant_status NaN crash on /dashboard

### High-priority discoveries

- **HIGH-PRIORITY:** `rcm_mc/dev/seed.py` (896L) is a **never-mentioned subsystem** — first appearance in any Report. Seeding/demo path. Adds `--verify` flag re-running DEMO_CHECKLIST.
- **HIGH-PRIORITY:** `rcm_mc/exports/canonical_facade.py` (424L) is a NEW exports facade — contracts unknown.
- **HIGH-PRIORITY:** 11 new `ui/chartis/_app_*.py` files = a NEW app-tier under chartis/ — different shape from `pe_intelligence/` or `verticals/`.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR1015** | **`_chartis_kit_v2.py` deleted** — any importer on main referencing it will break post-merge | Cross-check via grep before landing. Imports of `_chartis_kit_v2` outside of feat branch must be migrated to `_chartis_kit_editorial`. | High |
| **MR1016** | **+13.7K LOC in single PR** | Review burden very high. Bisect-unfriendly if breakage discovered later. | Medium |
| **MR1017** | **NEW `rcm_mc/dev/` subpackage (903L)** lands as a unit | Untouched by audit chain so far. **No prior Report has read seed.py.** | Medium |
| **MR1018** | **NEW `rcm_mc/exports/canonical_facade.py` (424L)** | Concept "canonical_facade" not in any Report. Unknown coupling to existing `infra/exports.py`. | Medium |
| **MR1019** | **NEW `rcm_mc/infra/exports.py` (225L)** + modified `infra/morning_digest.py` | `infra/` had no prior Report mention. Fresh subsystem. | Medium |
| **MR1020** | **server.py +217 LOC** — likely new route registrations | Route-collision risk if main also adds routes. Cross-link Report 0095. | Medium |
| **MR1021** | **`screening/dashboard.py` modified +69 LOC + bankruptcy_survivor commit** | Cross-link Report 0167 / 0211 schema lineage. Behavior diff in screening logic. | Medium |
| **MR1022** | **`ui/dashboard_page.py` substantial rewrite (~321 LOC delta)** | NaN-crash fix commit `118d8c5` indicates branch hit production-shaped data. | Low (test coverage exists per `test_ui_rework_contract.py`) |

## Dependencies

- **Incoming:** future merge to `main` (origin/main frozen at `3ef3aa3` since Report 0096).
- **Outgoing:** introduces 3 new top-level packages (`dev/`, `exports/canonical_facade`, expanded `infra/`, expanded `ui/chartis/`).

## Open questions / Unknowns

- **Q1.** Is `_chartis_kit_v2` referenced anywhere on `main`?
- **Q2.** What does `dev/seed.py` write — does it touch `portfolio.db` or a dev DB?
- **Q3.** Does `exports/canonical_facade.py` replace or wrap `infra/exports.py`?
- **Q4.** Do new chartis routes in `server.py` collide with main's route table?
- **Q5.** Are 51-file diff and 13.7K LOC mergeable atomically, or does this need a series?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0248** | Test coverage gap (in flight) — should look at `test_ui_rework_contract.py` 840-LOC contract surface. |
| **0249** | Read `dev/seed.py` head to close Q2. |
| **0250** | Read `exports/canonical_facade.py` head to close Q3. |

---

Report/Report-0247.md written. Next iteration should: read `tests/test_ui_rework_contract.py` to assess test coverage of the 13.7K-LOC ui-rework branch (closes test-coverage cadence + supports MR1016 review).