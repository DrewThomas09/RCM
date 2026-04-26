# Report 0142: Circular Import Risk — `rcm_mc/finance/` Subpackage

## Scope

Traces import chains in `RCM_MC/rcm_mc/finance/` (7 .py files + README, 2,791 lines). Sister to Reports 0022 (analysis/), 0052 (infra/), 0082 (compliance/), 0095 (domain/), 0112 (mc/). **`finance/` never reported in 141 prior iterations.**

## Findings

### Subpackage inventory (NEW)

| File | Lines | Status |
|---|---|---|
| `__init__.py` | 57 | re-export |
| `dcf_model.py` | 215 | **never reported** |
| `denial_drivers.py` | 255 | **never reported** |
| `lbo_model.py` | 285 | **never reported** |
| `market_analysis.py` | 245 | **never reported** |
| `regression.py` | 181 | **never reported** |
| `reimbursement_engine.py` | 1,232 | mentioned by name in Reports 0094 (MR516 collision), 0112 (MR628 import), 0117; **never deeply read** |
| `three_statement.py` | 321 | **never reported** |

**6 of 7 modules never reported.** `reimbursement_engine` mentioned only as collision target.

### Per-module import survey

Per `grep -nE "^(from|import) " finance/*.py`:

| File | Internal imports | Third-party |
|---|---|---|
| `__init__.py` | `.reimbursement_engine` (re-export with `noqa: F401`) | none |
| `dcf_model.py` | NONE — leaf | none |
| `denial_drivers.py` | NONE — leaf | numpy, pandas |
| `lbo_model.py` | NONE — leaf | none |
| `market_analysis.py` | NONE — leaf | numpy, pandas |
| `regression.py` | NONE — leaf | numpy, pandas |
| `reimbursement_engine.py` | NONE — leaf | logging only |
| `three_statement.py` | NONE — leaf | numpy |

### Internal DAG (within finance/)

**Every module is a LEAF.** No sibling `from .X import Y` patterns except `__init__.py` re-exports `reimbursement_engine` symbols.

**Zero cycles within `finance/`.** Cleanest internal-DAG of any audited subsystem (cross-link Report 0095 `domain/` which had the same shape).

### Cross-package edges

`grep -nE "^from \.\." finance/*.py` returns **NONE.** Every finance/ module imports stdlib + numpy/pandas only. **No upstream dependency on `rcm_mc/`'s other subpackages.**

This makes `finance/` a **leaf at the package level** — same as `domain/` (Report 0095).

### Inverse cross-package check — does any other subpackage import finance/?

Per Report 0094 + 0112 cross-references:

| Importer | Symbol |
|---|---|
| `mc/v2_monte_carlo.py:41` (Report 0112) | `finance.reimbursement_engine.PayerClass`, `ReimbursementProfile` |

Plus per Report 0094 incoming-dep audit on `domain/econ_ontology`: `finance/reimbursement_engine.py:135` had a docstring cross-reference (no import).

**Cross-package importers**: at least 1 (`mc/v2_monte_carlo`). More TBD.

### Cycle check

`finance/` exports → `mc/`. Does `mc/` export back to `finance/`? Per Report 0112: `mc/` imports `finance.reimbursement_engine` but `finance/` imports nothing from `mc/`. **Forward-only edge.** **No cycle.**

### `reimbursement_engine.py` (1,232 lines) — the mega-module

**Largest single file in finance/.** Per Report 0112: defines `PayerClass`, `ReimbursementProfile`. Per Report 0094 MR516: `ReimbursementProfile` name-collides with `domain.__init__.ReimbursementProfile` (deprecated alias for `MetricReimbursementSensitivity`).

**Imports**: `logging` + `dataclasses` + `enum` + `typing` — pure stdlib. **Heavy reach but no third-party deps** (no numpy/pandas).

### Comparison to other audited subpackages

| Subpackage | Files | Internal cycles | Cross-pkg imports | Privacy violations |
|---|---|---|---|---|
| `domain/` (Report 0095) | 3 | 0 | 0 | 0 |
| `auth/` (Reports 0021-0075) | 5 | 0 | minimal | 0 |
| `mc/` (Report 0112) | 7 | 0 | 3 outbound (pe, finance) | 1 (`_histogram`) |
| `infra/` (Report 0052) | 29+ | 0 | minimal | varies |
| `analysis/` (Report 0022) | many | 0 | several | TBD |
| **`finance/` (this)** | **7** | **0** | **0 outbound** | **0** |

**`finance/` is structurally pure** — leaf at package AND module level. Cleanest profile yet.

### Doc-discipline (cross-link Report 0134 doc-foil)

`finance/` is in the analysis/computation cluster (per Report 0134's pattern observation): "analysis-layer + auth/domain/infra modules document well." **Likely well-documented.** Q1 below — extracting docstring-density.

### Importers of finance/ (incoming sweep — high level)

`grep -rln "from rcm_mc\.finance\|from \.\.finance" RCM_MC/`: not run this iteration. Per known cross-references:
- `mc/v2_monte_carlo.py` (Report 0112)

**Q2**: Full incoming-dep graph TBD.

### `__init__.py` re-export (line 24)

```python
from .reimbursement_engine import (  # noqa: F401
    ...
)
```

**Single re-export site.** Per Report 0100 namespace-aggregator pattern, this means `from rcm_mc.finance import X` works; direct `from rcm_mc.finance.reimbursement_engine import X` ALSO works. Both paths.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR793** | **`finance/` is structurally cleanest subsystem audited** — 7 leaves, 0 cycles, 0 cross-package upstream | Cross-link Reports 0095, 0112. Adds to "structurally pure" cluster. | (clean) |
| **MR794** | **6 of 7 finance/ modules NEVER reported** in 141 prior iterations | Add to backlog. Per CLAUDE.md PE-math layer is Phase 2 ("dcf_model", "lbo_model", "three_statement" likely Phase-2 outputs). | **High** |
| **MR795** | **`reimbursement_engine.py` (1,232 lines) is largest single non-server.py file** in finance/ | Per Report 0094 MR516 the `ReimbursementProfile` name-collision lives here. Worth reading. | High |
| **MR796** | **`__init__.py` re-exports — 1 site** with `noqa: F401` | Standard pattern; clean. | (clean) |

## Dependencies

- **Incoming:** at least `mc/v2_monte_carlo.py` (Report 0112). Full graph TBD.
- **Outgoing:** stdlib (`logging`, `dataclasses`, `enum`, `typing`); numpy + pandas (3 modules); zero internal cross-package edges.

## Open questions / Unknowns

- **Q1.** Doc-density per file (per Report 0134 foil — confirm finance/ documents well).
- **Q2.** Full incoming-dep graph for finance/ — who imports it project-wide?
- **Q3.** Body of `reimbursement_engine.py` (1,232 lines) — schema of `PayerClass` / `ReimbursementProfile`.

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0143** | Map `finance/reimbursement_engine.py` end-to-end (1,232 lines — largest unmapped). |
| **0144** | Map `finance/dcf_model.py` (215 lines, never reported). |
| **0145** | Verify `analysis_runs` FK status (Report 0118 MR678 carried). |

---

Report/Report-0142.md written.
Next iteration should: deep-read `finance/reimbursement_engine.py` (1,232 lines) — largest unmapped non-server.py file, contains the ReimbursementProfile name-collision (Report 0094 MR516).
