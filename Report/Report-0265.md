# Report 0265: Dependency Pins + Repo Hygiene — 6 MRs closed (commit 4d93d38)

## Scope

The pyproject pin cluster (MR1037, MR978, MR1039, MR1040) plus four one-file hygiene items (MR1067 residual, MR1032, MR1034, MR1056). All verified still-open in the Report-0262 sweep.

Sister reports: 0251 (pyproject audit origin), 0250 (root-dir inventory), 0261 (sqlite3.connect census), 0255 (Tuva identification).

## Fixes (commit 4d93d38)

**MR1037 — toolchain pin drift.** `[dev]` had `ruff>=0.1` / `mypy>=1.5` while .pre-commit-config.yaml pins ruff v0.3.0 / mypy v1.8.0 — a fresh `pip install -e .[dev]` resolved different tool versions than the hooks run. Floors raised to `ruff>=0.3,<1.0` / `mypy>=1.8,<2.0` with a keep-in-sync comment naming the hook revs.

**MR978 — unbounded pins.** All 12 uncapped specs got upper bounds at the next major, matching the house style the diligence/edi groups already used: plotly `<7.0`, python-pptx `<2.0`, fastapi `<1.0`, uvicorn `<1.0`, scipy `<2.0`, scikit-learn `<2.0`, lifelines `<1.0`, ruptures `<2.0`, pytest `<10.0`, pytest-cov `<8.0`, ruff `<1.0`, mypy `<2.0`. Every current-latest version stays admissible (pytest 9.1 in this container passes the `<10.0` cap), so nothing downgrades — the caps only stop *future* majors from breaking installs. Uncapped count: 12 → 0.

**MR1039/MR1040 — extras overlap.** Kept as documented-intentional (the comment block already explains the layering) but the duplicated entries now carry identical caps (`openpyxl>=3.1,<4.0`, `python-pptx>=0.6,<2.0` in base/[pptx]/[exports]/[all]) so an extra can never silently widen a base constraint.

**MR1067 residual — last busy_timeout gap.** Report-0261's census left ~28 UI renderers; the 0262 re-verify found ui/ fully migrated upstream with exactly one residual: `ml/fund_learning.py` connected to the portfolio DB with no `busy_timeout`. Added `PRAGMA busy_timeout = 5000`. MR1067 fully closed.

**MR1032 — duplicate 477-line kit file.** `legacy/handoff/CHARTIS_KIT_REWORK.py` was byte-identical to the maintained `design_reference/handoff/` copy. Deleted; legacy README row now points at the survivor. (-477 LOC)

**MR1034 — unrunnable script.** `run_everything.sh` hardcoded `REPO="/Users/andrewthomas/..."` — broken on every machine but one. Now resolves the repo root from `BASH_SOURCE` like run_all.sh; scripts/README.md footgun note replaced. New `tests/test_scripts_bash_syntax.py` runs `bash -n` over every scripts/*.sh and pins the no-hardcoded-path fix.

**MR1056 — Apache-2.0 attribution.** Worse than triaged: `vendor/ChartisDrewIntel/license/license-2.0.txt` was **1 byte** (a lone newline) — the vendored Tuva Project shipped with no license text at all, violating Apache-2.0 §4. Full 11,357-byte Apache-2.0 text restored; "Third-party code and licenses" section added to vendor/README.md; root LICENSE gains a scoping note (MIT does not extend to the vendored snapshot; upstream publishes no NOTICE file, so §4(d) imposes nothing further).

## Evidence

- `pyproject.toml` parses (tomllib; 10 extras); all caps verified to admit the currently-installed versions.
- `tests/test_scripts_bash_syntax.py` (3 new tests) + migration-idempotency suite: 9 passed.
- `test_fund_learning*.py`: 19 passed.
- CI green (6/6 jobs) on the branch as of the Report-0263/0264 pushes.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| (closure) | MR1037, MR978, MR1039, MR1040, MR1067, MR1032, MR1034, MR1056 all closed | — |
| **Q1** | The pytest `<10.0` / pytest-cov `<8.0` caps are guesses at safe ceilings for tools not pinned by pre-commit; if CI's resolver ever needs a newer major, bump deliberately. | LOW |

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| next | engagement guard tests (MR1024, MR988) + doc drift stamps (MR1033) + MR1060 disposition |
| after | remaining MEDIUM tail: MR1053 (infra README), MR1019/MR1021 (unaudited landed files), MR1024, MR988; then fresh audit sweeps |

---

Report/Report-0265.md written.
