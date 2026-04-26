# Report 0135: Tech-Debt Marker Sweep — Whole-Repo Refresh

## Scope

Extends Report 0105 (`rcm_mc/` only — found 2 strict markers) to the whole repo: `rcm_mc_diligence/`, `tests/`, top-level scripts, `docs/`, `vendor/`. Sister to Reports 0015, 0045, 0075, 0105.

**Bonus closure**: Report 0116 Q1 (noqa code breakdown).

## Findings

### Strict marker count — whole repo

`grep -rEn "\b(TODO|FIXME|HACK|DEPRECATED)\b" --include="*.py"`:

| Path | Count | Notes |
|---|---|---|
| `RCM_MC/rcm_mc/` | 2 | Report 0105 confirmed: `ui/chartis/ic_packet_page.py:525` + `ui/chartis/_sanity.py:166` (both `TODO(phase-7)`) |
| `RCM_MC/rcm_mc_diligence/` | **1 meta** | `ingest/warehouse.py:316` — "Kept as a real class (not a TODO comment) so the warehouse selector..." — **NOT a real marker, just text containing "TODO"** |
| `RCM_MC/tests/` | **0** | clean |
| Top-level scripts (`seekingchartis.py`, `demo.py`, `scripts/*.sh`, `tools/*.py`) | **0** | clean |
| `RCM_MC/docs/` | **0** | clean |
| `vendor/ChartisDrewIntel/` | **0** | clean |
| **Whole repo** | **2 real + 1 meta** | |

**Real strict markers in the entire repo: 2.** Both `TODO(phase-7)`. Cross-link Report 0105 finding.

**Cleanest tech-debt discipline I have audited.** ~50K-line `rcm_mc/` + ~3,900-line `rcm_mc_diligence/` + ~280 test files + 100MB vendor + docs = **2 real markers**.

### Cross-correction: scaling

Report 0105 said `rcm_mc/` has 2 markers. This iteration extends: **the whole repo has 2 markers.** No additional debris discovered in tests, scripts, docs, or vendor.

### `noqa` density (closes Report 0116 Q1)

`grep -rEhn "noqa: ([A-Z]+[0-9]+)"` in `rcm_mc/`:

| Code | Count | Meaning |
|---|---|---|
| **BLE001** | **369** | broad-except (`except Exception`) — Report 0020 documented discipline |
| **F401** | **149** | unused-import — likely `__init__.py` re-export `noqa: F401` |
| ARG001 | 5 | unused function arg |
| S608 | 2 | SQL string-format (per Reports 0123 + 0133 — `f"DELETE FROM {table}..."` with internal-constant table names) |
| PLC0415 | 1 | lazy import inside function |
| F821 | 1 | undefined name (likely in test fixture) |
| ARG002 | 1 | unused method arg |

**527 noqa occurrences in 127 files** (corrected from Report 0105's "556" approximation).

### `BLE001` is the dominant ignore (369 of 527 = 70%)

Per Reports 0020, 0050, 0080, 0103, 0110, 0111, 0123:

> "broad-except + log + noqa is the documented pattern for partial-failure tolerance"

**70% of all noqa is one pattern: explicit broad-except discipline.** Cross-link Report 0020 (packet_builder error handling — explicit pattern documentation).

### `F401` is the second dominant (149 of 527 = 28%)

Likely all in `__init__.py` re-export blocks (per Reports 0093 ml/__init__, 0094 domain/__init__, 0100 vbc_contracts/__init__ + montecarlo_v3/__init__):

```python
from .module import (  # noqa: F401
    SymbolA,
    SymbolB,
    ...
)
```

**98% of all noqa is the two patterns above.** Project hygiene is excellent — only 9 unusual ignores out of 527.

### `S608` (SQL injection lint) — only 2 instances

Per Report 0123 `data_retention.py:46, 71`: `f"DELETE FROM {table} WHERE {ts_col} < ?"`. Both with `noqa: S608`. Source of `table`/`ts_col` is internal-constant dict — safe.

**MR707 (Report 0123)** flagged this as a future-refactor risk. Confirmed there are exactly 2 sites; both safe. **Tractable surface.**

### `noqa` density elsewhere

| Path | noqa occurrences |
|---|---|
| `rcm_mc/` | 527 |
| `rcm_mc_diligence/` | **0** |
| `tests/` | **14** |
| Whole repo | ~541 |

**`rcm_mc_diligence/` has ZERO noqa across 3,859 lines.** Cleanest module subtree.
**`tests/` has 14 noqa.** Mostly test-specific patterns; not pollution.

### `NotImplementedError` stubs (carried from Report 0105)

Per Report 0105: 8+ in `integrations/` + `market_intel/`. Re-verified count not run this iteration.

### Cross-link to feat/ui-rework-v3

Per Report 0126 commit `0a747f1`: "test(contract): Phase 3 — 6 new tests + **TODO discipline gate** (18→25)". The active branch ADDS a CI gate on TODO discipline. **Project hygiene is being actively enforced**, not just documented. Strong signal.

### Comparison vs project lifecycle

| Iteration | Marker count | Notes |
|---|---|---|
| Report 0015 (initial sweep, substring match) | 9+ | substring `XXX` matched CPT codes — false positives |
| Report 0075 (auth/) | 0 | "cleanest subsystem audited" |
| Report 0105 (whole rcm_mc/, word-boundary) | 2 | only TODO(phase-7) × 2 |
| **Report 0135 (whole repo, word-boundary)** | **2** | same — repo is clean across the board |

### `vendor/cms_medicare/` not directly checked

Per Report 0130: 100MB+ of CMS plot files (mostly `.png`). Per pattern (vendored data), unlikely to have Python tech-debt markers. Excluded from the `--include="*.py"` filter anyway.

### Tests for `validate_override_key` strict regex (Report 0134 cross-link)

`deal_overrides.validate_override_key` (Report 0134) enforces strict prefix validation — breaks the project-wide free-form-text pattern. **Tests for it should exist** (Q1).

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR765** | **2 strict markers in entire repo (`TODO(phase-7)` × 2)** is exemplary discipline OR markers tracked elsewhere (Linear/Jira/issues) but not surfaced in code | If markers are elsewhere, source-only audit understates the actual debt. Per Report 0061 Q1 + 0091 + 0119: ~676 internal MR-tracked risks vs ~2 source-marked TODOs. **The audit is the marker registry.** | Low |
| **MR766** | **`BLE001` is 70% of all noqa — 369 of 527** | Project-wide pattern is intentional broad-except for partial-failure tolerance. But this masks any "honest" broad-except misuse. A reviewer can't tell at-a-glance which are deliberate vs accidental. | Medium |
| **MR767** | **`F401` is 28% of noqa (149 of 527)** | Mostly `__init__.py` re-exports. Convention-aligned. But these become a pain point if a re-export changes target. | (clean) |
| **MR768** | **2 `S608` (SQL string-format) ignores in `data_retention.py`** | Both safe (internal-constant tables). But fragile if extended to env-var-driven retention. Cross-link Report 0123 MR707. | (carried) |
| **MR769** | **`feat/ui-rework-v3`'s "TODO discipline gate"** suggests project is moving toward CI-enforced TODO hygiene | If this lands, future tech-debt sweeps need to know about the contract-test gate. Cross-link Report 0127. | (advisory) |

## Dependencies

- **Incoming:** Reports 0015, 0045, 0075, 0105 (lineage of tech-debt sweeps).
- **Outgoing:** future iterations can rely on the "2 strict markers, ~527 noqa with 70% BLE001 + 28% F401" baseline.

## Open questions / Unknowns

- **Q1.** Is there a test asserting `validate_override_key` rejects each invalid prefix? (Report 0134 module's strict validation should be unit-tested.)
- **Q2.** Where are project-tracked TODOs / debt items? GitHub Issues, Linear, or only in the audit reports?
- **Q3.** Has the contract-test "TODO discipline gate" (per Report 0126 commit `0a747f1`) already shipped, or is it pending merge from `feat/ui-rework-v3`?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0136** | Schema-walk `deal_sim_inputs` (last named-but-unwalked table — Report 0110 backlog). |
| **0137** | Read `cli.py` head (1,252 lines, 14+ iterations owed since Report 0003). |
| **0138** | Verify Q1 — find test for `validate_override_key`. |

---

Report/Report-0135.md written.
Next iteration should: schema-walk `deal_sim_inputs` — last named-but-unwalked table from Report 0110 MR616 backlog.
