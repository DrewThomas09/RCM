# Report 0125: Outgoing Dep Graph — `portfolio/store.py`

## Scope

Maps every dep `RCM_MC/rcm_mc/portfolio/store.py` (394 lines) pulls in. Sister to Report 0124 (incoming, 237 importers). Closes the cycle-risk question for the most-imported module in the project.

## Findings

### Imports — full enumeration (lines 1-15)

```python
1: from __future__ import annotations
3: import json
4: import sqlite3
5: from contextlib import contextmanager
6: from dataclasses import dataclass
7: from datetime import datetime, timezone
8: from pathlib import Path
9: from typing import Any, Dict, Iterator, List, Optional, Tuple
11: import numpy as np
12: import pandas as pd
13: import yaml
15: from ..core.distributions import sample_dist
```

| # | Import | Category | Use sites |
|---|---|---|---|
| 1 | `__future__.annotations` | stdlib | PEP 563 |
| 2 | `json` | stdlib | 6× |
| 3 | `sqlite3` | stdlib | 5× |
| 4 | `contextlib.contextmanager` | stdlib | `connect()` decorator |
| 5 | `dataclasses.dataclass` | stdlib | dataclass decoration |
| 6 | `datetime, timezone` | stdlib | 2× |
| 7 | `pathlib.Path` | stdlib | 4× |
| 8 | `typing` (6 names) | stdlib | annotations |
| 9 | `numpy` (`as np`) | **third-party** | 11× — distribution sampling helpers |
| 10 | `pandas` (`as pd`) | **third-party** | 5× — `list_deals`/`list_runs` returning DataFrame |
| 11 | `yaml` (PyYAML) | **third-party** | 3× — `yaml.safe_dump` for YAML serialization |
| 12 | `..core.distributions.sample_dist` | internal | 4× |

**12 imports total: 8 stdlib + 3 third-party + 1 internal.**

### Lazy imports — none

`grep -nE "^[[:space:]]+(import|from) "` returns empty. **No in-function imports.** All deps top-level. Cross-link Report 0019 (which noted lazy imports are the standard pattern in larger files like server.py).

### Heaviness analysis

| Dep | Import cost | Use scope |
|---|---|---|
| numpy | HEAVY (~50ms cold) | distribution-sampling helpers (lines 24-50) |
| pandas | HEAVIEST (~200ms cold) | `list_deals`, `list_runs` return DataFrames |
| yaml | MEDIUM (~10ms) | `yaml.safe_dump` 3× |
| stdlib | LIGHT | trivial |
| internal `sample_dist` | LIGHT | one fn |

**Pandas alone is the biggest single dep cost.** Per Report 0053: pandas runtime is ~200ms cold-import.

### COUPLING-VS-COST IMPLICATION

Per Report 0124: 237 importers of `PortfolioStore`. **EVERY ONE of them pays the numpy + pandas + yaml import cost** at module load — even tests that only do `PortfolioStore(tmp).init_db()` and never touch DataFrames.

**Estimated import-time cost cascade**:
- ~250ms × 237 importers = up to ~60 seconds aggregate import time across a full test suite cold-start
- BUT: Python caches imported modules — only the FIRST import pays. Subsequent imports are ~0ms.

So in practice the cost is once-per-process: ~250ms. **Not a real perf issue, but a cleanliness concern.**

### Internal coupling — single edge

`from ..core.distributions import sample_dist` — line 15.

**Per Report 0035** (outgoing-dep graph for infra/config) + Report 0013 (core/distributions API): `core.distributions` is a leaf-ish numpy-only module. **No cycle back to portfolio/.**

**Per Reports 0022, 0052, 0082, 0095, 0112**: no analysis/, infra/, compliance/, domain/, or mc/ subpackage imports `portfolio.store` from above (DAG forward-only). PortfolioStore is the trunk.

### Unused-import check

| Symbol | Used? |
|---|---|
| `json` | YES (6×) |
| `sqlite3` | YES (5×) |
| `contextmanager` | YES (decorator at line 83) |
| `dataclass` | YES (decorator) |
| `datetime`, `timezone` | YES (2×) |
| `Path` | YES (4×) |
| `Any, Dict, Iterator, List, Optional, Tuple` | YES (annotations) |
| `np` | YES (11×) |
| `pd` | YES (5×) |
| `yaml` | YES (3×) |
| `sample_dist` | YES (4×) |

**No unused imports.** Compare to Report 0099 (`domain/custom_metrics.py` had 5 unused imports). Cleaner here.

### `pd.DataFrame` return-type signature

`list_deals` (line 277) and `list_runs` (line 324) return `pd.DataFrame`. **A consumer that doesn't use pandas can't call these.** Per Report 0124's 237 importers, many use only `connect()` / `init_db()` — but the return type forces the import.

**Refactor candidate**: split heavy methods (`list_deals`, `list_runs`) into a separate module that lazily imports pandas, OR change return type to `List[Dict]` (cross-link Report 0065 MR433 — same suggestion for `audit_log.list_events`).

### `yaml` usage

`yaml.safe_dump` 3 sites: serialize priors and config to YAML files. Cross-link Report 0011 (actual.yaml format) + Report 0016 (pyyaml audit).

`yaml.safe_dump` is correct (vs `yaml.dump`) — restricts to safe types. **Compliant with CLAUDE.md PHI-mode patterns.**

### Comparison vs other audited modules' outgoing deps

| Module | Lines | Imports | Third-party | Internal | Style |
|---|---|---|---|---|---|
| `domain/econ_ontology.py` (Report 0095) | 816 | 4 | 0 | 0 | pure stdlib |
| `domain/custom_metrics.py` (Report 0099) | 185 | 6 | 0 | 0 | pure stdlib |
| `infra/_terminal.py` (Report 0109) | 231 | 5 | 0 | 0 | pure stdlib |
| `infra/rate_limit.py` (Report 0085) | 57 | 4 | 0 | 0 | pure stdlib |
| `auth/audit_log.py` (Report 0065) | 192 | 5 | 1 (pandas) | 1 (PortfolioStore) | mixed |
| `infra/data_retention.py` (Report 0123) | 79 | 5 | 0 | 0 | pure stdlib |
| **`portfolio/store.py` (this)** | **394** | **12** | **3 (np/pd/yaml)** | **1 (sample_dist)** | **heaviest** |

**`portfolio/store.py` has the heaviest outgoing-dep load of any audited foundation module.** Trunk position justifies it but reinforces the refactor case (DataFrames are convenient but force pandas everywhere).

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR712** | **`portfolio/store.py` forces numpy + pandas + yaml as transitive deps for all 237 importers** | Per Report 0124 fanout. A bare `PortfolioStore(tmp).init_db()` test pays ~250ms import cost. Acceptable per Python's module cache (paid once per process), but if a future Postgres/cloud-store refactor wants to ship a slimmer abstraction, it must split out the DataFrame methods. | Medium |
| **MR713** | **`pd.DataFrame` return type on `list_deals` and `list_runs`** | Cross-link Report 0065 MR433 (same pattern in `audit_log.list_events`). Forces pandas import. Refactor candidate: return `List[Dict]`. | Low |
| **MR714** | **No DAG cycle** (portfolio/store imports `..core.distributions` only — DAG is forward-only) | Cross-link Reports 0035, 0095. Clean. | (clean) |
| **MR715** | **Top-level imports — no lazy / try/except for optional deps** | If pandas/yaml are ever made optional (per `[diligence]` extras pattern, Report 0113), this file breaks at import-time. The trunk module needs all of them; OK to be top-level. | (clean) |

## Dependencies

- **Incoming:** 237 files (per Report 0124).
- **Outgoing:** stdlib (`json`, `sqlite3`, `contextlib`, `dataclasses`, `datetime`, `pathlib`, `typing`, `__future__`); third-party (`numpy`, `pandas`, `pyyaml`); internal (`core.distributions.sample_dist`).

## Open questions / Unknowns

- **Q1.** What does `sample_dist` (from `core.distributions`) do? Cross-link Report 0013.
- **Q2.** What lines in store.py implement `init_db` (referenced 5+ times in audit reports but body never extracted)?
- **Q3.** Are there tests that import `PortfolioStore` without using DataFrames — would those tests benefit from a slimmer interface?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0126** | Schema-walk `deal_overrides` (Report 0118 MR677, still owed). |
| **0127** | Read `init_db` body in `portfolio/store.py` — schema-walk the foundational `deals` table fully (Report 0017 was partial). |
| **0128** | Read `cli.py` head (1,252 lines, 14+ iterations owed). |
| **0129** | Refactor candidate: explore splitting `list_deals` / `list_runs` into a `portfolio/store_dataframe.py` slim interface. |

---

Report/Report-0125.md written.
Next iteration should: schema-walk `deal_overrides` table (Report 0118 MR677 high, carried 7+ iterations) — most-deferred concrete task.
