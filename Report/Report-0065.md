# Report 0065: Outgoing Dep Graph — `auth/audit_log.py`

## Scope

Maps every dep `auth/audit_log.py` pulls in. Sister to Report 0064.

## Findings

### Imports (per Report 0063 head + 0064 detail)

```python
from __future__ import annotations
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional
import pandas as pd
from ..portfolio.store import PortfolioStore
```

| Import | Category |
|---|---|
| `json` | stdlib |
| `datetime`, `timezone` | stdlib |
| `typing` | stdlib annotation-only |
| `pandas` | core dep (Report 0046) |
| `..portfolio.store.PortfolioStore` | internal |

**5 imports total.** 3 stdlib + 1 third-party + 1 internal.

### Heaviness

- **Heavy: pandas** (only for `list_events` returning a DataFrame). Could be replaced with stdlib (list-of-dicts) to drop the dep, but pandas is core anyway.
- **Light:** stdlib only otherwise.

### Internal coupling

Single internal import: `PortfolioStore` from `portfolio/store.py`. Foundation-layer SQLite gate (Report 0017 + 0027).

### Cycle check

`audit_log.py` → `portfolio.store` → `core.distributions` (per Report 0035 cross-package). Forward-only DAG; no cycle back to `auth/`. Clean.

### Unused-import check

All 5 imports look used:
- `json` — for `detail_json` serialization
- `datetime/timezone` — for `_iso(_utcnow())`
- `Optional` — annotation
- `pandas` — `list_events` returns DataFrame
- `PortfolioStore` — connect()

**No unused imports.**

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR433** | **`pandas` dependency for a small list-events DataFrame** | Could be replaced with `list[dict]` to make `auth/audit_log.py` pandas-free. **Foundation modules are usually best stdlib-only.** Refactor opportunity. | Low |

## Dependencies

- **Incoming:** server.py (3 sites per Report 0064).
- **Outgoing:** stdlib (json, datetime, typing), pandas, portfolio.store.

## Open questions / Unknowns

- **Q1.** None new.

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0066** | Branch audit (already requested). |
| **0067** | Merge risk scan (already requested). |
| **0068** | Test coverage (already requested) — pick `audit_log`. |

---

Report/Report-0065.md written.

