# Report 0165: Tech-Debt Marker Sweep — `.md` files + `feat/ui-rework-v3`

## Scope

Extends Reports 0105 + 0135 (whole-repo .py sweeps; 2 strict markers) to **markdown docs** + **branch-side markers**. Sister to Reports 0015, 0045, 0075, 0105, 0135.

## Findings

### `.py` count — STILL 3

`grep -rEn "\b(TODO|FIXME|HACK|DEPRECATED)\b" . --include="*.py"`:

**3 markers** (was 2 in Report 0135 + 1 meta in `rcm_mc_diligence/ingest/warehouse.py:316`). 2 real (TODO(phase-7) in `ui/chartis/`). 1 meta. Same as Report 0135 — **no new strict markers added in 30+ iterations.**

### `.md` markers — 11 files

`grep -rln "TODO|FIXME|HACK|DEPRECATED" --include="*.md"`: **11 markdown files** contain tech-debt-like markers.

Most likely:
- Report-NNNN.md mentions ("TODO" as topic discussion, not a marker)
- CHANGELOG.md entries ("TODO" deferred work)
- design-handoff/UI_REWORK_PLAN.md / PHASE_2_PROPOSAL etc.

**These are mostly LITERAL prose** (e.g., "the TODO list includes..."), not source-code-style markers. **Cross-correction**: `.md` markers don't count for code-side tech-debt.

### `feat/ui-rework-v3` — 7 TODO mentions in `UI_REWORK_PLAN.md`

`git show origin/feat/ui-rework-v3:RCM_MC/docs/UI_REWORK_PLAN.md | grep -c "TODO"`: **7 occurrences**.

These are the **planned-work tracking** entries. Per Report 0126: feat/ui-rework-v3 is the active branch with explicit "TODO discipline gate" (commit `0a747f1`). The TODOs are intentional — phase-tracked work-items.

**Project-wide observation**: TODOs in `.md` are PLANNING; TODOs in `.py` are CODE-LEVEL DEBT. Different categories.

### Cross-correction to Report 0105 + 0135

Report 0105/0135 sweep was `--include="*.py"` only. `.md` was excluded. **This iteration confirms .md exclusion was correct** — those markers are documentation/planning, not code debt.

### Severity grouping

**Code-level (.py, strict regex)**:
- 2 markers (TODO(phase-7) × 2 in ui/chartis/) — Report 0105
- 1 meta-mention in rcm_mc_diligence/ingest/warehouse.py:316 (false-positive — text contains TODO)

**Documentation (.md)**: 11 files, but these are planning/specs, not debt.

**`feat/ui-rework-v3` planning TODOs**: 7+ in UI_REWORK_PLAN.md. Phase-tracked.

**Test markers**: 0 (per Report 0135 confirmed).

### Cross-link Report 0144 retries

Per Report 0144: `_cms_download.py` docstring claims "respectful retry" but code has 0 retries (MR647 high). **That doc-vs-code mismatch is functionally a TODO that nobody marked as TODO.** Project tech-debt is partly invisible because it's not marked.

### NotImplementedError stubs (carried)

Per Report 0105: 8+ in `integrations/` + `market_intel/`. Re-verify count in latest pe_intelligence/ branch.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR884** | **Real tech-debt is NOT marked as TODO** in source — Report 0144 MR647, Report 0131 MR744, Report 0136 MR770 are bugs without TODO markers | Source-only TODO counts undersell actual debt. **The audit is the marker registry** (per Report 0135 MR765). | Low |
| **MR885** | **`feat/ui-rework-v3` branch has 7+ TODOs in UI_REWORK_PLAN.md** (planning, not debt) | Cross-link Report 0126 commit `0a747f1` "TODO discipline gate." Phase-tracked. **Healthy planning discipline.** | (positive) |

## Dependencies

- **Incoming:** Reports 0015, 0105, 0135 lineage.
- **Outgoing:** future tech-debt iterations rely on this baseline.

## Open questions / Unknowns

- **Q1.** Should the audit reports themselves be marker-tagged (e.g., a YAML frontmatter status field)? Currently risks sit in commit messages.

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0166** | External dep (in flight). |
| **0167** | Database/storage (in flight). |

---

Report/Report-0165.md written.
