# Report 0259: `exports/canonical_facade.py` Audit (MR1018 closure)

## Scope

Closes Report 0247 / MR1018: never-read 424-LOC export facade that lands as part of `feat/ui-rework-v3`. Read via `git show origin/feat/ui-rework-v3:RCM_MC/rcm_mc/exports/canonical_facade.py`. Audits the public-API shape, the `record_export` audit-row coupling, and the dependency on `infra/exports.py` (which is also new on the feature branch — Report 0247 MR1019).

Sister reports: 0247 (feat-branch diff stat), 0258 (dev/seed.py audit, same shape), 0181 (delete-policy matrix), 0136 (trust-boundary).

## Findings

### Inventory

- File: `RCM_MC/rcm_mc/exports/canonical_facade.py` on `origin/feat/ui-rework-v3` (does not exist on `origin/main`).
- Size: **424 LOC**.
- Companion (also new): `RCM_MC/rcm_mc/infra/exports.py` (225 LOC per Report 0247 MR1019) — supplies `canonical_deal_export_path()` + `canonical_portfolio_export_path()` + `_resolve_export_path()`.

### Architecture

The module is a **facade layer** — wrappers around 11 existing report writers — that deliberately *does not* change any writer signature. Per its own docstring (line 1-37):

> Existing writers take `outdir` / `out_path` args used by ~6 call sites across server.py + the CLI. Changing each signature would touch every call site at once — a big-bang refactor with rollback risk. Facades layer on top: existing call sites keep using the writers directly with their existing args (no behavior change); new call sites use the facade and get canonical paths for free.

This is a **non-invasive** way to introduce the canonical `/data/exports/<deal_id>/<timestamp>_<filename>` path layout.

### 11 facade functions (uniform shape)

| Facade | Wraps |
|---|---|
| `export_full_html_report` | `reports.full_report` |
| `export_html_report` | `reports.html_report` |
| `export_markdown_report` | `reports.markdown_report` |
| `export_exit_memo` | `reports.exit_memo` |
| `export_partner_brief` | `reports._partner_brief` |
| `export_diligence_memo` | (diligence memo writer) |
| `export_diligence_package_zip` | (diligence zip writer) |
| `export_exit_package_zip` | (exit zip writer) |
| `export_deal_xlsx` | `reports.deal_xlsx` |
| `export_bridge_xlsx` | `reports.bridge_xlsx` |
| `export_ic_packet_html` | `reports.ic_packet` |

Each follows a 5-step pattern documented at top of file:

1. Compute canonical path via `canonical_deal_export_path` (from `infra/exports.py`).
2. Call existing writer with `tempfile.TemporaryDirectory()` so output lands in scratch.
3. Move via `shutil.move(produced → canonical)` (private helper `_move_to_canonical:51`).
4. Call `record_export(...)` (from `exports/export_store.py:43` — exists on main) for the deliverables manifest.
5. Return the canonical `Path`.

### `_move_to_canonical` — cross-mountpoint safety

Uses `shutil.move` rather than `Path.rename`. Comment at line 56-58:

> the tmp dir lives on a different mountpoint than `/data/exports/` in most production setups (tmpfs vs. persistent volume), and `rename()` fails across filesystem boundaries.

This is correct — `os.rename` is restricted to same-filesystem moves on POSIX. The facade handles it.

Idempotent overwrite: line 64 unlinks the canonical path before moving, so re-running an export of the same `(deal_id, timestamp, filename)` tuple replaces in place.

### `_record` — best-effort manifest write

Wraps `record_export` in `try/except Exception: pass` (line 102-103). Comment at line 84-85:

> Failures here are absorbed: the artifact is on disk and that's the load-bearing thing; the audit row is best-effort.

Cross-link to Report 0131 silent-failure pattern. **This is a deliberate choice** — same trade-off as `_audit` in engagement/store.py. The artifact's existence is canonical; the audit row is a convenience for the deliverables manifest.

### Cross-link to `record_export` on main

`exports/export_store.py:43` already defines `record_export(store, *, deal_id, analysis_run_id, format, filepath, file_size_bytes, generated_by)` — every kwarg the facade calls with. **No signature change needed on main.** Merge will be clean for that seam.

### Cross-link to `infra/exports.py` (Report 0247 MR1019)

The facade depends on `canonical_deal_export_path` from `infra/exports.py` (also new on feat-branch, 225 LOC). MR1019 was Medium-classified previously — this report promotes it to "must-merge-together-with-MR1018" because the facade module has no fallback path if `infra/exports.py` is missing. Documented in MERGE-CONFLICTS.md entry 3.

### Cross-link to iter-23 FK CASCADE

`record_export` writes into `generated_exports`. Per Report 0211 schema inventory, `generated_exports` has FK to `deals(deal_id)` with **`ON DELETE SET NULL`** — derivative artifact behavior, audit-friendly. The facade respects this: deleting a deal nulls the `deal_id` column on past export rows but keeps the rows for historical audit. Consistent with the iter-20 delete-policy matrix.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR1064** | **`canonical_facade.py` cannot land alone** — depends on `canonical_deal_export_path` from the also-new `infra/exports.py` (Report 0247 MR1019). If only one of the two modules is included in a partial merge, `canonical_facade.py` import fails at module load. | Document the must-merge-together coupling. | High at merge boundary |
| **MR1065** | **`_move_to_canonical:64` unconditionally unlinks then moves** — there's a brief window where both target and source are absent if the move fails between `unlink` and `move`. | Use `shutil.move` with `os.replace` semantics instead — atomic on same FS, idempotent across FS via shutil's fallback. (Currently the existing implementation uses shutil.move correctly; the unlink-first is the failure point.) Rewrite as `shutil.move(produced, canonical)` only, since shutil.move handles the existing-target case via copy+unlink already. | Low |
| **MR1066** | **Best-effort `_record` swallows all exceptions** including the artifact-write disk-full case. If `canonical.stat()` succeeds (file is on disk) but `record_export` raises because the SQLite store is locked / corrupt, the deliverables manifest silently misses an export. | Cross-link Report 0131 / MR744. **Promote the bare-except to a logged warning** (one-line `logger.warning("manifest write failed for %s: %s", canonical, exc)`) so operators can grep for missing manifest rows. | Medium |
| **MR1018** | (RETRACTED — closed) `exports/canonical_facade.py` never read | (closure) | (closed) |

## Dependencies

- **Incoming on feat/ui-rework-v3:** new server.py routes calling the facades (per Report 0247 server.py +217 LOC).
- **Outgoing:**
  - `rcm_mc.exports.export_store.record_export` (exists on main).
  - `rcm_mc.infra.exports.canonical_deal_export_path` (also new on feat-branch — MR1019 / MR1064).
  - 11 existing report writers in `rcm_mc/reports/*.py` (exist on main, signatures unchanged).

## Open questions / Unknowns

- **Q1.** Does any of the 11 wrapped writers raise on `outdir` paths longer than the OS limit (e.g. tmpfs paths can exceed 256 chars in tests)? The facade trusts the writer; a writer that fails silently here would produce zero-byte canonical files.
- **Q2.** Is the `/data/exports/` path baked into `canonical_deal_export_path`, or env-var-overridable? Cross-link CLAUDE.md "Phase 4 packet-centric" exports.

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| (post-merge) | MR1066 — promote `_record`'s bare-except to a logged warning. |
| (post-merge) | Read `infra/exports.py` head (Report 0247 MR1019) to close the must-merge-together coupling MR1064. |
| (post-merge) | Verify all 11 facades end-to-end with a real packet build + canonical path round-trip. |

---

Report/Report-0259.md written.
