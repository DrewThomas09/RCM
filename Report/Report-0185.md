# Report 0185: Outgoing Dep Graph — `engagement/store.py`

## Scope

Maps outgoing imports from `engagement/store.py` (707 lines per Report 0182). Sister to Reports 0095, 0125, 0142, 0155.

## Findings

### Imports (top of file)

```python
from __future__ import annotations
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from ..portfolio.store import PortfolioStore
```

**6 stdlib + 1 internal (PortfolioStore).** No third-party.

### Per-category

- stdlib: `json`, `dataclasses`, `datetime`, `enum`, `typing` + `__future__`
- internal: `PortfolioStore` (per Report 0124 — 237 importers; this is one)
- **third-party: NONE**

### Heaviness

**Lightweight import surface.** Pure stdlib + 1 internal. **Cleaner than `portfolio/store.py`** (Report 0125: 12 imports incl numpy/pandas/yaml).

### Cycle check

`engagement/` → `portfolio/` (forward edge). Per Report 0124-0125: portfolio/store imports core.distributions only. No back-edge from portfolio → engagement.

**No cycle.** Forward-only DAG.

### Comparison to other audited stores

| Module | Stdlib | Third-party | Internal |
|---|---|---|---|
| `auth/audit_log.py` (Report 0065) | 5 | 1 (pandas) | 1 (PortfolioStore) |
| `infra/data_retention.py` (Report 0123) | 5 | 0 | 0 |
| `analysis/deal_overrides.py` (Report 0134) | 5 | 0 | 0 |
| `mc/mc_store.py` (Report 0117) | several | 0 | 1 (sibling) |
| `exports/export_store.py` (Report 0133) | 3 | 0 | 0 |
| **`engagement/store.py` (this)** | **6** | **0** | **1 (PortfolioStore)** |

**On par with other store-layer modules.** Tight, focused.

### Branch advance during this batch

Per `git fetch`: `origin/feat/ui-rework-v3` advanced to `c3d8e5f` at 2026-04-26 03:04 (was `80223e4` at 01:23 — +1.5h, **58 ahead** now vs 57 at Report 0179). **+1 commit since 0179.**

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR942** | **`engagement/store.py` is stdlib-only + PortfolioStore** | Cleanest store-layer profile. | (clean) |
| **MR943** | **`feat/ui-rework-v3` advanced to 58 commits** since Report 0179 | +1 in ~2 hours. Slow-but-steady. | (advisory) |

## Dependencies

- **Incoming:** 6 importers per Report 0184.
- **Outgoing:** stdlib + PortfolioStore.

## Open questions / Unknowns

None new.

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0186** | Branch audit (in flight). |

---

Report/Report-0185.md written.
