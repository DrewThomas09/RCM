# Report 0271: Export LOW carry-forwards cleared — MR1069 (docs) + MR1070 (same-second collision) (commit d0e0cec)

## Scope

Cleared the two LOW carry-forward notes the export-hardening work left open (surfaced in Reports 0267 and 0268). Small, concrete, already-scoped.

## Fixes (commit d0e0cec)

**MR1070 — same-second export collision.** `_now_utc_iso()` produced a second-granular timestamp (`%Y-%m-%dT%H-%M-%S`), so two exports of the same `(deal_id, filename)` within one wall-clock second resolved to the identical path, and `canonical_facade._move_to_canonical`'s `shutil.move` silently overwrote the first (plus left two `generated_exports` manifest rows pointing at one file). Fixed by making the **auto-generated** stamp microsecond-precise (`_TIMESTAMP_FMT_MICRO = %Y-%m-%dT%H-%M-%S-%f`).

Verified safe before changing the leaf format:
- The format is only ever *generated* (`strftime`), never *parsed* (`strptime`) — grep-confirmed across the package, so no consumer depends on second granularity.
- Callers that pass an **explicit** timestamp (e.g. `dev/seed` staggering snapshots by hours) are untouched — only the `timestamp or _now_utc_iso()` default path changed.
- Still colon-free / cross-filesystem-safe.

**MR1069 — exports.py undocumented.** `infra/exports.py` was the last of the 29 infra modules missing from `infra/README.md`. Added its section: the canonical path policy, the two-function (deal vs portfolio) design, and the Report-0267/0268 traversal defenses (`_reject_path_chars` + `is_relative_to` backstop). All 29 infra modules now documented.

## Evidence

- `tests/test_export_path_traversal.py` +2: the auto stamp matches the microsecond pattern; five back-to-back `canonical_deal_export_path` calls for the same `(deal_id, filename)` yield more than one distinct path (they collided before).
- Regression: `test_export_path_traversal`, `test_exports_end_to_end`, `test_export_pipeline`, `test_packet_exports`, `test_canonical_facade` → 50 passed, 3 skipped.

## Carry-forward status

Only **MR1071** (deal_sim_inputs path validation — needs an allowlist-dir design decision) remains as a tracked LOW note. The export-hardening thread (Reports 0264/0267/0268/0270/0271) is otherwise fully closed.

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| next | A session PROGRESS rollup (Reports 0262-0271 landed this session), then a never-mapped-package sweep (`pe_intelligence/`, `data_public/`). |

---

Report/Report-0271.md written.
