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
