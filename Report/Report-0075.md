# Report 0075: Tech-Debt Sweep — `rcm_mc/auth/`

## Scope

Tech-debt sweep on auth/ (810 LoC). Sister to Reports 0015 (whole rcm_mc/) + 0045 (pe/).

## Findings

### Marker totals

| Marker | auth/ count |
|---|---:|
| TODO | 0 |
| FIXME | 0 |
| XXX | 0 |
| HACK | 0 |
| DEPRECATED | 0 |

**Zero explicit markers.** Same as `pe/` (Report 0045) — clean.

### `# noqa: BLE001` suppressions

6 sites total across 3 files:

| File:line | Context |
|---|---|
| `rbac.py:59` | inside an exception handler |
| `auth.py:160` | INSERT INTO users → wrap as ValueError |
| `auth.py:305` | session-touch swallow |
| `auth.py:415` | helper-table-ensure swallow |
| `auth.py:420` | helper-table-ensure swallow |
| `audit_log.py:66` | "best-effort migration" — silent ALTER swallow |

**6 BLE001 across 3 files.** Each has documented rationale (per Reports 0021 + 0063 reads).

### Subsystem verdict

**auth/ is clean by tech-debt-marker standards.** Same pattern as pe/:

- 0 TODO/FIXME/XXX/HACK/DEPRECATED
- Low noqa count (6 in auth/ vs 14 in pe/ vs 71 in server.py)
- Documented rationale per BLE001

### Comparison

| Subsystem | LoC | Markers | noqa |
|---|---:|---:|---:|
| auth/ | 810 | 0 | 6 |
| pe/ | (multi-file) | 0 | 14 |
| server.py | 16,398 | 0 | 71 |
| ui/dashboard_page.py | (deleted on polish branch) | 0 | 38 |
| analysis/packet_builder.py | 1,454 | 0 | 27 |

**auth/ has the cleanest noqa-density** by file size. Aggressive review zone.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR450** | **`audit_log.py:66` "best-effort migration" silent ALTER swallow** | Cross-link Report 0017 MR127 (migration registry's silent fallback). If a future schema migration fails, audit_events table stays at old shape. | Medium |
| **MR451** | **`rbac.py:59` BLE001 in security-critical module** | Per Report 0073 placeholder. Any silent error in role-resolution = potential auth bypass. **Pre-merge: read context.** | **High** |

## Dependencies

- **Incoming:** server.py, cli.py, tests.
- **Outgoing:** stdlib + portfolio.store.

## Open questions / Unknowns

- **Q1.** What does `rbac.py:59`'s except-block actually do? Returns False? Raises? Swallows?

## Suggested follow-ups

| Iteration | Area |
|---|---|
| **0076** | External dep audit (already requested). |

---

Report/Report-0075.md written.

