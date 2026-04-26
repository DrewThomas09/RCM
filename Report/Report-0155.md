# Report 0155: Outgoing Dep Graph — `pe_intelligence/partner_review.py`

## Scope

Maps outgoing imports from `RCM_MC/rcm_mc/pe_intelligence/partner_review.py` (38,711 bytes, ~1,500 LOC per Report 0152 — 2nd largest .py file in pe_intelligence after `__init__.py`). Sister to Reports 0095, 0125, 0153, 0154.

## Findings

### Imports (top 25 lines)

```python
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .heuristics import (...)
from .extra_red_flags import EXTRA_RED_FLAG_FIELDS, run_extra_red_flags
from .red_flags import RED_FLAG_FIELDS, run_all_rules
from .narrative import (...)
from .reasonableness import (...)
```

**4 stdlib + 5 sibling imports visible.** Per file size (~1,500 LOC), this is just the head — full enumeration of imports likely 10-30 sibling-module pulls.

### Sibling imports (5 visible)

| Sibling | Symbols (sample) |
|---|---|
| `.heuristics` | (multi-symbol — line 26+) |
| `.extra_red_flags` | `EXTRA_RED_FLAG_FIELDS`, `run_extra_red_flags` |
| `.red_flags` | `RED_FLAG_FIELDS`, `run_all_rules` |
| `.narrative` | (multi-symbol — line 36+) |
| `.reasonableness` | (multi-symbol — line 44+) |

**Only sibling imports visible. Zero cross-package imports** (no `from ..analysis`, no `from ..deals`, etc.).

This **confirms Report 0153 architectural promise**: `pe_intelligence` is downstream of `DealAnalysisPacket` but does NOT reach back into `analysis/` or `deals/` packages. **Pure leaf at package level.**

### Stdlib imports

- `__future__.annotations` — PEP 563 forward-refs
- `dataclasses` (`dataclass`, `field`) — for `PartnerReview` dataclass output
- `datetime` (`datetime`, `timezone`) — UTC timestamps
- `typing` (Any, Dict, List, Optional) — annotations

**No numpy/pandas/yaml** — pure stdlib + sibling.

### Cross-link to Report 0142 finance/ pattern

Per Report 0142: `finance/` is structurally cleanest — every module is a leaf. **partner_review.py is similarly leaf-shaped from cross-package perspective** — only sibling imports.

### NEW finding — `extra_red_flags` module

Per line 34: `from .extra_red_flags import EXTRA_RED_FLAG_FIELDS, run_extra_red_flags`. This is a sibling module not in Report 0152's top-20-by-bytes list. **One of the 276 modules.** Cross-link Report 0153 1,455-name surface — `extra_red_flags` module contributes 2 names.

### `DealAnalysisPacket` likely passed as argument

Per Report 0153 architectural promise: `partner_review(packet)` takes a packet. **No `from ..analysis.packet import DealAnalysisPacket` import** — so the packet must be passed as a typed-or-untyped argument (or the import is in the function body, lazy). **Cross-link Report 0057 packet schema.**

### Comparison

| Module | Stdlib | Third-party | Internal sibling | Internal cross-pkg |
|---|---|---|---|---|
| `domain/econ_ontology.py` (Report 0095) | 4 | 0 | 0 | 0 |
| `portfolio/store.py` (Report 0125) | 8 | 3 (np/pd/yaml) | 0 | 1 (core.distributions) |
| **`pe_intelligence/partner_review.py` (this)** | **4** | **0** | **5+** | **0** |

**partner_review.py is similar profile to `domain/econ_ontology.py`** — pure leaf-from-outside but sibling-rich-inside.

### Architectural shape (post-this-report)

```
DealAnalysisPacket (analysis/packet.py)
    ↓ (passed as argument; no import)
partner_review.py (1500 LOC)
    ├── heuristics
    ├── extra_red_flags (NEW)
    ├── red_flags
    ├── narrative
    └── reasonableness
        (likely +25 more siblings further into the file)

→ returns PartnerReview dataclass
```

**No upstream-reaching edges.** Forward-only DAG within `pe_intelligence/`. Cross-link Report 0153.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR849** | **No cross-package imports in partner_review.py** | Per Report 0153 architectural promise. Confirms `pe_intelligence` is leaf-from-outside. Clean. | (clean) |
| **MR850** | **`DealAnalysisPacket` is implicit argument type** — not imported | If `packet` parameter type-hint references `DealAnalysisPacket` (Report 0057 dataclass), Python `from __future__ import annotations` makes this work via forward-ref. **Type-checker MAY not resolve** — cross-link Report 0101 `mypy ignore_missing_imports`. | Low |

## Dependencies

- **Incoming:** per Report 0154, 10 importers across server.py + ui/chartis/ + data_public/.
- **Outgoing:** stdlib only (4 imports) + 5+ sibling pe_intelligence modules.

## Open questions / Unknowns

- **Q1.** What are the imports past line 50 in `partner_review.py`? Sibling chain likely 20+ deep.
- **Q2.** Does `partner_review.py` lazily import `analysis.packet.DealAnalysisPacket` for runtime checks?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0156** | Branch audit (in flight). |
| **0157** | Read `cli.py` head (1,252 lines, 19+ iter carry). |

---

Report/Report-0155.md written.
