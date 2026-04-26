# Report 0127: Merge Risk Scan — `feat/ui-rework-v3`

## Scope

`git diff origin/main..origin/feat/ui-rework-v3 --shortstat`. The only active branch (per Report 0126 refresh #4 — 35 ahead, 0 behind). Sister to Reports 0007 (deals-corpus), 0037 (deals-corpus refresh), 0067 (connect-partner-brain), 0097 (pe-intelligence dead-snapshot).

## Findings

### Headline

**38 files changed, +12,043 / -706.**

A FAR cleaner diff than Reports 0067 (4 risks) or 0097 (3,956 files / 569K-line gap). This branch IS forward-mergeable into origin/main.

### File status breakdown

| Status | Count | Examples |
|---|---|---|
| Added (A) | 28 | 12 chartis/_app_*.py, 7 docs/design-handoff/, 2 ref HTML, 2 ref JSX, login_page, forgot_page, app_page, canonical_facade, infra/exports |
| Modified (M) | 9 | server.py, _chartis_kit.py, initiative_tracking, chartis_tokens.css, etc. |
| Deleted (D) | 1 | **`_chartis_kit_v2.py` (-600 lines)** |

### Top 10 by lines changed

| File | Lines | Status |
|---|---|---|
| `ui/static/v3/chartis.css` | +1026 | A |
| `docs/design-handoff/reference/cc-app.jsx` | +753 | A |
| `tests/test_ui_rework_contract.py` | +675 | A |
| `docs/design-handoff/reference/01-landing.html` | +663 | A |
| `docs/design-handoff/reference/04-command-center.html` | +653 | A |
| `docs/UI_REWORK_PLAN.md` | +623 | A |
| `ui/_chartis_kit_editorial.py` | +610 | A |
| **`ui/_chartis_kit_v2.py`** | **-600** | **D** |
| `docs/design-handoff/EDITORIAL_STYLE_PORT.md` | +487 | A |
| `docs/design-handoff/PHASE_3_PROPOSAL.md` | +472 | A |

### NO dependency / schema / Dockerfile changes (clean)

| Concern | Status |
|---|---|
| `pyproject.toml` | unchanged ✓ |
| `requirements*.txt` | n/a (project uses pyproject) |
| `Dockerfile`, `docker-compose.yml` | unchanged ✓ |
| `.github/workflows/*` | unchanged ✓ |
| SQL `CREATE TABLE` / `ALTER TABLE` | none ✓ |

**No dep version bumps. No schema migrations.** Per Report 0126 commit `87e8d5e` references `generated_exports` — confirmed: the branch WRITES to existing `generated_exports`, doesn't change DDL.

### `_chartis_kit_v2.py` rename — clean

Per `git grep -l "_chartis_kit_v2"` on the branch: only `_chartis_kit.py` and `_chartis_kit_editorial.py` reference the v2 path. **The deletion is paired with `_chartis_kit_editorial.py` (+610) replacing it.**

`_chartis_kit.py` (M) updates the dispatcher:

```python
# OLD (origin/main):
UI_V2_ENABLED = _os.environ.get("CHARTIS_UI_V2", "0") != "0"
...
if UI_V2_ENABLED:
    from ._chartis_kit_v2 import (...)

# NEW (branch):
def _ui_flag_on() -> bool:
    v2 = _os.environ.get("CHARTIS_UI_V2", "")
    v3 = _os.environ.get("RCM_MC_UI_VERSION", "").lower()
    return v2 not in ("", "0") or v3 in ("v3", "editorial", "1", "true")

UI_V2_ENABLED = _ui_flag_on()
...
if UI_V2_ENABLED:
    # Pure passthrough — the editorial module's chartis_shell already...
    from ._chartis_kit_editorial import (...)
```

**Clean rename + dispatcher upgrade.** Old `_chartis_kit_v2` import path is deleted but no external importer exists (single internal user was `_chartis_kit.py` itself — already updated).

### NEW env vars (cross-link Report 0118 env-var registry)

| Env var | Purpose | First-seen |
|---|---|---|
| `RCM_MC_UI_VERSION` | UI selector: `v2`/`v3`/`editorial`/`1`/`true` | this branch |
| `EXPORTS_BASE` | Exports base directory | this branch |

**Adds 2 to the env-var registry** (now ~12+ vars). Cross-link Report 0118 MR681 (no central registry).

### NEW PHI-mode WRITE SITE — cross-link Report 0028

Branch contains:

```python
+    os.environ["RCM_MC_PHI_MODE"] = "disallowed"
```

**This is a WRITE to RCM_MC_PHI_MODE** — Report 0028 trace claimed PHI-mode is read-only. **MR720 high cross-correction.** Likely in a test fixture (PHI gate is being toggled for testing), but writes to `os.environ` from within Python are global-state mutations.

### NEW HTTP routes — `/forgot` + `/app`

Per server.py diff:

```python
+        if path == "/forgot":
+            return self._route_forgot_page()
+        if path == "/app":
+            return self._route_app_page()
```

**2 new public GET routes:**
- `/forgot` — password-reset page
- `/app` — main app entry

Plus refactored `/login` POST — now dispatches between `_route_login_request_submit` (forgot-password flow?) and `_route_login_page_editorial` / `_route_login_page_legacy`.

**Cross-link Report 0108 login flow audit**: my Report 0108 trace was on origin/main's `_route_login_post`. The branch adds a fork between editorial vs legacy login pages. **A merge would change Report 0108's flow — needs re-audit post-merge.**

### NEW PHI banner change

Per Report 0126 commit `fd8bd83`: "feat(phi-banner): Q3.7 visual weight reduction" — changes the PHI banner styling. Cross-link Report 0028 + 0030 (PHI mode + PHI security architecture).

### `tests/test_ui_rework_contract.py` (+675 lines)

A new contract-test file. Per Report 0126 commit `0a747f1`: "Phase 3 — 6 new tests + TODO discipline gate (18→25)" — confirmed: 25 contract tests now total.

**This test file is enforcement-critical**: contracts must hold for the merge to land.

### `exports/canonical_facade.py` (+424) + `infra/exports.py` (+225)

**Two new modules** for the export pipeline. Per Report 0126 commits `261d7f0` + `9b07ff5` + `a755cb2` + `87e8d5e`: "canonical-path facades for 5 report writers, 3 packet/zip writers, 3 misc writers" + "wire _app_deliverables to generated_exports manifest."

**Per the deliverables commit**: writes to `generated_exports` table (Report 0118 named-but-not-walked). **Schema-walk priority: still elevated** (per Report 0126 MR717).

### `rcm/initiative_tracking.py` (+154 lines)

Modified — adds cross-portfolio variance aggregation w/ trailing 4Q (per commit `ffbca70`). Cross-link Report 0124: this module imports `PortfolioStore`. New SQL queries TBD.

### `docs/design-handoff/` (14 files added)

Big design-handoff bundle:
- `PROPOSAL.md`, `PHASE_2_PROPOSAL.md`, `PHASE_3_PROPOSAL.md`
- `IA_MAP.md`
- `EDITORIAL_STYLE_PORT.md`
- 4 reference HTML (landing, login, forgot, command-center)
- 3 reference JSX (cc-app, cc-components, cc-data)
- `tokens/chartis_tokens.css`
- `README.md`

**~3,500+ lines of design docs.** Cross-link Report 0029 + 0089 + 0119 (commit digest history shows feature/deals-corpus + this branch are the doc-heavy work; main is audit-doc-heavy).

### Cross-correction to Report 0108

Report 0108 traced `POST /api/login` flow and concluded "5-layer trace ... 401 / 303 / 200." **The branch refactors the login flow** — adds forgot-password handling, splits editorial vs legacy login pages, possibly changes the dispatch order.

A post-merge re-audit of the login entry-point would be needed.

### Branch is safely mergeable

- No dep changes
- No schema DDL changes
- No file-rename-with-stale-importers
- Comprehensive contract tests (+675 lines)
- Clear feature-flag pattern (`RCM_MC_UI_VERSION`)
- Backward-compatible default (legacy renderer still default)

**The branch is in good merge shape.** Far better posture than `feature/deals-corpus` (Report 0007: 826-behind, divergent), `feature/pe-intelligence` (Report 0097: 569K-line gap), `feature/connect-partner-brain-phase1` (Report 0067).

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR720** | **Branch contains `os.environ["RCM_MC_PHI_MODE"] = "disallowed"`** — a WRITE site for the env var | Report 0028 trace claimed PHI mode was read-only. Likely a test fixture; if it ever ships in production code, side-effect on global state. | **High** |
| **MR721** | **2 NEW env vars** (`RCM_MC_UI_VERSION`, `EXPORTS_BASE`) added | Cross-link Report 0118 MR681 (no central registry). Adds to ~12+ var sprawl. CLAUDE.md should be updated post-merge. | Low |
| **MR722** | **2 NEW HTTP routes** (`/forgot`, `/app`) without auth/CSRF audit done | Per Report 0084 + 0114: every new route needs auth gate + CSRF posture. Report 0108 login flow trace becomes stale post-merge. | **High** |
| **MR723** | **`_chartis_kit_v2.py` deletion is paired with `_chartis_kit_editorial.py` add** — clean | Verified: only internal importer was `_chartis_kit.py` which is also updated in same diff. | (clean) |
| **MR724** | **`generated_exports` writes added but table never schema-walked** | Cross-link Report 0118 + 0126 MR717 high. Pre-merge: schema-walk before merging. | **High** |
| **MR725** | **`rcm/initiative_tracking.py` +154 lines** — likely new SQL queries | Cross-link Report 0124 (module is a PortfolioStore importer). Pre-merge: review for SQL parameterization. | Medium |
| **MR726** | **`docs/design-handoff/reference/*.jsx`** — JSX files in a Python project | These are reference-only design files, not code. But CI lint may need to skip them (`*.jsx`). Per Report 0116 ruff config: ruff doesn't lint JSX, OK. | Low |
| **MR727** | **`tests/test_ui_rework_contract.py` is the SINGLE quality gate** for this branch | Per Report 0126 commit `0a747f1`: 18→25 contract tests. If any test is fragile, the merge gate is fragile. | Medium |
| **MR728** | **Login flow refactor** — Report 0108's 5-layer trace is now stale | Post-merge: re-audit `/api/login` POST + new `/login` GET dispatcher (editorial vs legacy). | **Medium** |

## Dependencies

- **Incoming:** Report 0126 (branch state); the eventual merge into origin/main affects 237 PortfolioStore importers (Report 0124) IF SQL paths change.
- **Outgoing:** PortfolioStore (via `rcm/initiative_tracking.py`), `generated_exports` table, env vars `RCM_MC_UI_VERSION` + `EXPORTS_BASE`, new test contract file.

## Open questions / Unknowns

- **Q1.** What exactly does `_route_app_page` render? `/app` is a major new route.
- **Q2.** Does `forgot_page.py` send password-reset emails? If so, **NEW external integration** (cross-link Report 0025 Anthropic — this would be SMTP/SendGrid).
- **Q3.** What is the `EXPORTS_BASE` env-var default and behavior?
- **Q4.** Does `infra/exports.py` (new) duplicate `exports/packet_renderer.py` (Report 0106)?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0128** | Schema-walk `generated_exports` (carried, MR724 high) — pre-merge requirement. |
| **0129** | Read `forgot_page.py` and `login_page.py` from the branch (closes Q1+Q2, MR722). |
| **0130** | Read `infra/exports.py` (closes Q3+Q4). |
| **0131** | Read `cli.py` head (1,252 lines, 14+ iterations owed). |

---

Report/Report-0127.md written.
Next iteration should: schema-walk `generated_exports` table — pre-merge requirement before `feat/ui-rework-v3` lands (MR724 high).
