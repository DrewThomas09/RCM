# MERGE-CONFLICTS — Pre-merge advisory log

Logged whenever a fix on `audit/reports-and-triage` touches a file ALSO modified on an unmerged feature branch, OR whenever the audit chain identifies a deletion/refactor that will require human resolution at merge time.

Format: one entry per file/symbol pair. Each entry names: which branches diverge, what the conflict is, and the recommended resolution.

---

## 1. `RCM_MC/rcm_mc/ui/_chartis_kit.py` × `feat/ui-rework-v3`

**Triage source:** TRIAGE.md MR1015 / Report-0247.md.

**State on `main` (HEAD `bb6a28c` and earlier on origin):**
- `_chartis_kit.py` is a feature-flag dispatcher that imports `_chartis_kit_v2` at runtime when `CHARTIS_UI_V2=1` (line 90).
- `_chartis_kit_v2.py` exists (~600 LOC).
- 4 references to `_chartis_kit_v2` in `_chartis_kit.py`: one active import (line 90), three docstring/comment mentions (lines 9, 46, 190).
- Last commit modifying the file on main: `94772ff` ("revert duplicate Cmd-K injection, extend legacy palette instead").

**State on `origin/feat/ui-rework-v3`:**
- Commit `53350d2` ("chore(ui): retire dead _chartis_kit_v2.py (OLD reverted reskin)") deletes `_chartis_kit_v2.py` outright.
- Commit `a7c0a22` ("feat(shell): _chartis_kit_editorial.py — editorial chartis_shell + atoms") introduces `_chartis_kit_editorial.py` (763 LOC) as the replacement.
- 4 commits on the branch modify `_chartis_kit.py` (+206 LOC vs. main); the rewritten dispatcher is expected to import from `_chartis_kit_editorial` instead of `_chartis_kit_v2`.
- The feature flag may flip from `CHARTIS_UI_V2` to a `?ui=v3` per-request flag (commit `8fc9661` "feat(flag): per-request ?ui=v3 detection in addition to env").

**Conflict at merge:**
- The same file (`_chartis_kit.py`) is modified on both sides.
- Git will either auto-resolve (unlikely given line-90 collision with the deleted module's import) or ask the merge author to resolve manually.
- After merge, any leftover `_chartis_kit_v2` reference inside `_chartis_kit.py` will raise `ImportError` because the module no longer exists in the tree.

**Recommended resolution at merge time:**
1. Accept the feature branch's version of `_chartis_kit.py` wholesale (it has the editorial-aware dispatcher).
2. Verify post-merge with: `python -c "import rcm_mc.ui._chartis_kit"` and the same with `CHARTIS_UI_V2=1` set.
3. Grep for any straggling `_chartis_kit_v2` references in the merged tree (`grep -rn _chartis_kit_v2 RCM_MC/rcm_mc/`); only docstring/comment mentions are acceptable, no live imports.
4. Confirm `legacy/handoff/CHARTIS_KIT_REWORK.py` (Report-0250 MR1032) is still untouched — it is an archival predecessor, not a live module.

**Why no preemptive fix on `audit/reports-and-triage`:**
- Modifying `_chartis_kit.py` on main now would create a worse three-way conflict for the feature branch (which has rewritten the file substantively).
- The merge mechanics resolve this naturally: `feat/ui-rework-v3` is the source of truth for the editorial rework; main is the source of truth for the audit chain. The merge author owns the integration.

---

## 2. `RCM_MC/rcm_mc/dev/seed.py` × audit-branch FK CASCADE additions

**Triage source:** TRIAGE.md MR1017 / Report-0258.md / cross-link iter-23 commit `91097a1`.

**State on `main` (after iter-23):**
- `rcm_mc/dev/seed.py` does not exist.
- 5 deal-child tables (`deal_sim_inputs`, `deal_owner_history`, `deal_health_history`, `deal_deadlines`, `deal_stars`) now declare `FOREIGN KEY(deal_id) REFERENCES deals(deal_id) ON DELETE CASCADE` via fresh-DB CREATE-TABLE-IF-NOT-EXISTS (commit `91097a1`). Live DBs unchanged (MR1059 covers the ALTER migration).

**State on `origin/feat/ui-rework-v3`:**
- `rcm_mc/dev/seed.py` exists (896 LOC); ships a `seed_demo_db()` orchestrator with `--overwrite` flag.
- Has its own pre-iter-23 view of those 5 tables — DDL identical to main pre-iter-23 (no FK on deal_id). Does NOT carry the iter-23 FK additions.

**Conflict at merge:**
- Each of the 5 `deals/*.py` files modified by iter-23 (`deal_sim_inputs.py`, `deal_owners.py`, `health_score.py`, `deal_deadlines.py`, `watchlist.py`) is unmodified on `feat/ui-rework-v3`. So a 3-way merge converges on the iter-23 version — no textual conflict.
- **Functional implication:** post-merge, `dev/seed.py --overwrite` runs against a fresh DB carrying the iter-23 FK CASCADE. Cascades fire as intended; orphan rows do NOT accumulate.
- For live DBs (no iter-23 schema yet — MR1059 pending), `dev/seed.py --overwrite` will still leave orphan rows. Recommend MR1059 ships before any operator runs `--overwrite` against a live-shaped DB.

**Cross-risks captured in Report-0258 for the merge author:**
- MR1061 (Medium) — heuristic prod guard at `seed.py:134` matches only `/data/` and `seekingchartis.db`. Partner's `~/portfolio.db` slips through.
- MR1062 (Low) — seeder couples to `get_or_build_packet`; iter-13 hash_inputs cache key fix (`2fc6715`) is compatible.
- MR1063 (Medium) — `--overwrite` is partially safe post-iter-23 only on FRESH DBs.

**Recommended resolution at merge time:**
1. Accept the iter-23 versions of the 5 `deals/*.py` files (they have the FK + audit-trail comment).
2. Take `dev/seed.py` from `feat/ui-rework-v3` unchanged.
3. Verify with `python -m rcm_mc.dev.seed --db /tmp/demo.db --verify` after merge.
4. Do NOT run `--overwrite` against a live DB until MR1059 (live-DB ALTER migration) ships.

---

## 4. `.github/workflows/deploy.yml` — auto-deploy trigger divergence

**Triage source:** TRIAGE.md MR917 / Report-0119/0120 / verified iter-27.

**State on `main` (HEAD `2e8a02e`):**
- `.github/workflows/deploy.yml` last modified in commit `f3f7e7f` ("chore(repo): deep cleanup").
- `on:` block lines 14-17:
  ```yaml
  on:
    # push:
    #   branches: [main]
    workflow_dispatch:
  ```
- **Auto-deploy on push to main is DISABLED.** The workflow only fires via manual `workflow_dispatch`. Comment at lines 3-12 explicitly says "Once secrets are set and you've verified one manual deploy succeeds, uncomment the `push: branches: [main]` block below to enable auto-deploy on every push to main."
- Uses `appleboy/ssh-action@v1.0.3` for SSH.
- Steps: SSH → git pull → docker compose up → 12×5s health check loop → smoke test.

**State on `origin/feat/ui-rework-v3`:**
- Same file, heavily rewritten.
- `on:` block has `push: branches: [main]` **ENABLED** (lines 4-6) alongside `workflow_dispatch`.
- Different SSH machinery — uses `webfactory/ssh-agent` + heredoc rather than `appleboy/ssh-action`.
- Includes a "Record start time" step for deploy-duration metrics.
- Same secrets (`AZURE_VM_HOST/USER/SSH_KEY`).

**Cross-link:** prior commits on origin/main (`3ef3aa3`, `7d5afb5`, `1c845db` per Report-0246 branch refresh) were CI hardening commits to fix the SSH/secret expansion path — likely the source of the feat-branch's improved SSH machinery.

**Conflict at merge:**
- Same file modified on both sides → guaranteed textual conflict in the `on:` block AND the SSH steps.
- If git auto-resolves to feat-branch's version, **auto-deploy fires immediately** on the merge commit. The merge commit itself becomes a deploy without explicit operator opt-in.
- If git asks the merge author to resolve, the choice is: keep main's manual-only (safe, audit-able) vs. take feat's auto-deploy (faster but irreversible without another commit).

**Recommended resolution at merge time:**
1. **Default to safety: keep `push:` commented out** until AZURE_VM_HOST/USER/SSH_KEY are verified set on the GH repo (`gh secret list` should show all three).
2. Take the feat-branch's improved SSH machinery (`webfactory/ssh-agent` + heredoc) — it's the post-fix iteration of the SSH-quoting issue Report-0246 noted.
3. Run one manual `workflow_dispatch` deploy. If it succeeds, then in a follow-up commit uncomment `push: branches: [main]` to opt into auto-deploy.
4. Verify secrets:
   ```
   gh secret list -R DrewThomas09/RCM
   ```
   must include `AZURE_VM_HOST`, `AZURE_VM_USER`, `AZURE_VM_SSH_KEY`.

**Why no preemptive fix on `audit/reports-and-triage`:**
- `deploy.yml` is heavily rewritten on the feature branch; modifying it on main would deepen the conflict.
- MR917's stated risk ("First merge triggers auto-deploy") is real **only if** the feature branch's auto-enabled `on:` block is what lands. Audit branch can't decide that — the merge author owns it.
- Documenting the gating recipe here means the merge author has the right defaults pre-flighted.

---

## 3. `RCM_MC/rcm_mc/exports/canonical_facade.py` × `RCM_MC/rcm_mc/infra/exports.py`

**Triage source:** TRIAGE.md MR1018 / Report-0259.md / Report-0247 MR1019.

**State on `main`:**
- Neither file exists.
- `rcm_mc/exports/export_store.py:43 record_export(...)` already exists with the kwargs the facade uses — no main-side change required for that seam.

**State on `origin/feat/ui-rework-v3`:**
- `rcm_mc/exports/canonical_facade.py` (424 LOC) — 11 facade functions over existing report writers, each routes the writer's tmp-output to `/data/exports/<deal_id>/<timestamp>_<filename>` via `shutil.move` and writes a `record_export(...)` audit row.
- `rcm_mc/infra/exports.py` (225 LOC, also new) — supplies `canonical_deal_export_path()` and `canonical_portfolio_export_path()`. The facade imports `canonical_deal_export_path` directly.

**Conflict at merge:**
- No textual conflict (both files are net-new on feat-branch).
- **`canonical_facade.py` cannot land alone** — the import on line 48 hard-binds to `infra/exports.canonical_deal_export_path`. If a partial cherry-pick takes the facade but not `infra/exports.py`, the module raises `ImportError` at load time and every report-route on the new server breaks.

**Recommended resolution at merge time:**
1. Treat `canonical_facade.py` and `infra/exports.py` as a **must-land-together** pair — never split across PRs.
2. Verify post-merge with `python -c "from rcm_mc.exports.canonical_facade import export_full_html_report; from rcm_mc.infra.exports import canonical_deal_export_path; print('ok')"`.
3. Spot-check one facade end-to-end (e.g. `export_partner_brief`) against a fresh seeded DB to confirm the `/data/exports/<deal_id>/...` round-trip writes both the file and the `generated_exports` audit row.
4. **Post-merge follow-up MR1066** — promote the `_record` bare-except (line 102-103) to a logged warning so manifest failures don't silently swallow.

**Why no preemptive fix on `audit/reports-and-triage`:**
- Both files are net-new and would conflict with the feature branch's authoritative versions if mirrored on main.
- Audit branch documents the must-land-together coupling so the merge author can sequence the PR atomically.

---
