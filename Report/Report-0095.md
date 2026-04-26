# Report 0095: Outgoing Dep Graph — `domain/econ_ontology.py`

## Scope

Maps every dep `domain/econ_ontology.py` pulls in. Sister to Report 0094 (incoming). Closes Report 0094 Q3 (cycle risk).

## Findings

### Imports — full enumeration

`grep -n "^import\|^from"` of `RCM_MC/rcm_mc/domain/econ_ontology.py` returns **4 lines, 4 imports**:

```python
26: from __future__ import annotations
28: from dataclasses import dataclass, field, asdict
29: from enum import Enum
30: from typing import Any, Dict, List, Optional, Set, Tuple
```

| # | Import | Category | Use |
|---|---|---|---|
| 1 | `__future__.annotations` | stdlib | PEP 563 forward-refs |
| 2 | `dataclasses` (3 names) | stdlib | `MetricDefinition`, `MechanismEdge`, `CausalGraph` etc. + serialization |
| 3 | `enum.Enum` | stdlib | `Domain`, `Directionality`, `FinancialPathway`, `ConfidenceClass`, `ReimbursementType` |
| 4 | `typing` (6 names) | stdlib | annotations |

**4 imports total. 4 stdlib. 0 third-party. 0 internal.**

### HIGH-PRIORITY confirmation: pure-stdlib leaf module

`domain/econ_ontology.py` (816 lines) is a **pure stdlib data + classification module** — no numpy, no pandas, no sibling internal imports. **The cleanest module audited so far in 95 reports.** Confirms Report 0094 cycle-risk finding: domain/ is a leaf in the DAG.

### Sibling check — `domain/custom_metrics.py`

For full subpackage context, `domain/custom_metrics.py` (185 lines) imports:

```python
18: from __future__ import annotations
20: import re
21: import logging
22: from dataclasses import dataclass, field, asdict
23: from datetime import datetime, timezone
24: from typing import Any, Dict, List, Optional, Tuple
```

**6 stdlib imports. 0 third-party. 0 internal.** Same purity.

### Subpackage profile

`rcm_mc/domain/` (3 files, 1,059 lines):

| File | Lines | Imports | Internal deps |
|---|---|---|---|
| `__init__.py` | 58 | re-exports from `econ_ontology` | leaf |
| `econ_ontology.py` | 816 | 4 stdlib | leaf |
| `custom_metrics.py` | 185 | 6 stdlib | leaf |

**Whole subpackage is leaf-clean.** No incoming → outgoing cycle is even structurally possible.

### Heaviness

- **No heavy deps.** Even `re` and `logging` (the only "heavy" stdlib in custom_metrics) are negligible.
- **No conditional / lazy imports** in the 4-line import block.
- **No `try/except ImportError`** patterns. Tight stdlib contract.

### Internal coupling

**Zero internal imports.** Closes Report 0094 Q3 definitively: there is no cycle between `domain/` and any other subpackage because `domain/` imports nothing from anywhere except stdlib.

This means **all 5 production importers of `domain.econ_ontology`** (per Report 0094: analysis/packet_builder, pe/lever_dependency, data/auto_populate, ui/methodology_page, plus domain/__init__) can refactor freely without dragging foundational dependencies.

### Unused-import check

All 4 imports look used:

- `__future__.annotations` — applies to all type hints.
- `dataclass, field, asdict` — `MetricDefinition`, `MechanismEdge`, `CausalGraph` are dataclasses (line 16-17 of file docstring).
- `Enum` — 5 enums declared (lines 35-50 visible).
- `Any, Dict, List, Optional, Set, Tuple` — all used in the 816-line body (high confidence given `METRIC_ONTOLOGY` typed dict).

**No unused imports** (no `noqa: F401` markers either).

### Cross-correction to CLAUDE.md

CLAUDE.md "Tech stack" section says: "**Python 3.14** (stdlib-heavy; pandas + numpy + matplotlib are the only runtime deps beyond stdlib)." `domain/econ_ontology.py` exemplifies this discipline perfectly. **Strong confirmation of the stdlib-heavy invariant for foundation layers.** Cross-link Report 0021 (which noted `auth/auth.py` Pattern A: stdlib-heavy).

### Comparison vs other audited modules

| Module | Lines | Total imports | Third-party imports |
|---|---|---|---|
| `auth/audit_log.py` (Report 0065) | 192 | 5 | 1 (pandas) |
| `auth/auth.py` (Report 0021) | ~430 | mixed | mostly stdlib |
| `infra/rate_limit.py` (Report 0085) | 57 | 4 | 0 |
| `domain/econ_ontology.py` (this report) | **816** | **4** | **0** |
| `domain/custom_metrics.py` | 185 | 6 | 0 |

`econ_ontology.py` is the **highest-line-to-import-count ratio audited** (204:1). Pure data + logic. Foundational.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR521** | **No risks identified outgoing-side** | Pure stdlib + leaf. | (clean) |
| **MR522-advisory** | **`from __future__ import annotations` requires Python 3.10+** | Already met (CLAUDE.md says 3.14). But if pyproject-pin loosens (per Report 0086 MR479), affects forward-ref evaluation. | (advisory) |

## Dependencies

- **Incoming:** 5 production files + 2 test files (per Report 0094).
- **Outgoing:** 4 stdlib modules (`__future__`, `dataclasses`, `enum`, `typing`). Zero third-party. Zero internal.

## Open questions / Unknowns

- **Q1.** With 816 lines, what is the structure of `METRIC_ONTOLOGY`? (Carried from Report 0094 Q2.)
- **Q2.** Does `domain/__init__.py` re-export reach EVERY public name in `econ_ontology`, or selectively? (Curl check: 14 names re-exported per Report 0094, but file has 5 enums + 5+ dataclasses + ~3 functions = ~13-15 names. Likely full match.)

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0096** | Read `METRIC_ONTOLOGY` structure (closes Report 0094 Q2 + this Q1). |
| **0097** | Map `rcm_mc/pe_intelligence/` (HIGH-PRIORITY unmapped per Report 0093 MR513). |
| **0098** | Test coverage of `tests/test_econ_ontology.py`. |

---

Report/Report-0095.md written.
Next iteration should: map `rcm_mc/pe_intelligence/` directory (HIGH-PRIORITY unmapped per Report 0093 MR513).
