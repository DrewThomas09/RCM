# Report 0035: Outgoing-Dep Graph for `infra/config.py`

## Scope

Maps every external + internal + stdlib dep of `RCM_MC/rcm_mc/infra/config.py` on `origin/main` at commit `f3f7e7f`. The module's incoming graph was traced in Report 0034. This complements that with the outgoing surface.

Prior reports reviewed: 0031-0034.

## Findings

### Outgoing imports (from earlier reads — Reports 0011, 0012, 0016)

```python
import os
import re
from typing import Any, Dict, List, Optional, Tuple
import yaml                # pyyaml (declared core dep — Report 0016)
from .logger import logger  # Pattern A — central named logger
```

**5 stdlib + 1 third-party + 1 sibling = 7 total imports.**

### Outgoing breakdown

| Category | Symbols | Notes |
|---|---|---|
| **stdlib** | `os` (env vars + path expansion), `re` (regex), `typing` (annotations) | Standard. |
| **third-party** | `yaml` (= pyyaml) | Used for `yaml.safe_load` exclusively (per Report 0016). |
| **internal** | `.logger.logger` | Pattern A central logger — uses the `"rcm_mc"` named logger via `from .logger import logger`. |

**Zero deep-package internal imports.** `infra/config.py` does not depend on `analysis/`, `pe/`, `core/`, `data/`, etc. — it is a pure validator. **Foundation-layer module.**

### Outgoing usage detail

| Import | Internal use sites |
|---|---|
| `os.environ.get(...)` | Inside `_resolve_env_vars` (line 36-50, per Report 0011) — used for `${VAR}` substitution in YAML. |
| `os.path.exists` | Likely `_extends` resolution (per Report 0011 line 71-72). |
| `re.compile`, `re.findall` | Pattern matching for `${VAR}` and `${VAR:default}` substitution. |
| `yaml.safe_load` | Inside `load_yaml` (line 58 per Report 0011/0016). |
| `logger.warning`, `logger.info` (potentially) | Per Report 0024, the central logger is wired via Pattern A. Specific usage inside config.py was not enumerated. |

### Heavy-dep verdict

- **Heavy: NONE.** No matplotlib, numpy, pandas, scipy. Pure validation logic.
- **`re` regex compilation** is the heaviest stdlib operation; cached internally.
- **No third-party HTTP, no DB, no concurrency** — pure synchronous code.
- **No env var capture at module-load** — every read is inside a function.

### Cycle check

- `infra/config.py` imports `.logger` — i.e. `infra/logger.py`.
- `infra/logger.py` imports `logging` (stdlib) only.

**No cycle.** `config.py → logger.py → stdlib`. Clean DAG within `infra/`.

### Unused-import check

Reading the imports list against documented uses:

| Import | Used? |
|---|---|
| `os` | ✅ env vars, paths |
| `re` | ✅ regex |
| `typing.Any/Dict/List/Optional/Tuple` | ✅ annotations |
| `yaml` | ✅ safe_load |
| `.logger.logger` | ✅ (assumed; not verified per-line) |

**No obvious unused imports.**

## Merge risks flagged

| ID | Risk | Detail | Severity |
|---|---|---|---|
| **MR305** | **`infra/config.py` is foundation-layer (zero internal deps)** | Any signature change ripples up to 10 production callers (Report 0034). The module itself depends only on stdlib + pyyaml + sibling logger. **Foundation breaks = whole stack breaks.** | **High** |
| **MR306** | **`pyyaml` is the only third-party dep** | If pyyaml is uninstalled (impossible on a pip-install path; possible on a manual venv), config.py fails at module load. | Low |

## Dependencies

- **Incoming:** 10 production files + ~20 test files (Report 0034).
- **Outgoing:** `os`, `re`, `typing`, `yaml`, `.logger`. **5 imports total.** Foundation layer.

## Open questions / Unknowns

- **Q1.** Does `infra/config.py` ever call `logger.warning(...)` for invalid configs? Per the validator semantics (raises `ValueError` on missing required fields), warnings would be for non-fatal anomalies. Needs full file read.
- **Q2.** Does `_resolve_env_vars` recurse into nested dicts/lists? Or only top-level?

## Suggested follow-ups

| Iteration | Proposed area | Why |
|---|---|---|
| **0036** | **Branch audit** (already requested as iteration 36). | Pending. |
| **0037** | **Read `infra/config.py:_resolve_env_vars` (line 36-50)** | Resolves Q2. |
| **0038** | **Read `infra/config.py:_validate_dist_spec` (line 119)** | Outstanding from Report 0013 Q1. |

---

Report/Report-0035.md written. Next iteration should: produce a branch register update (since Report 0006), confirming the 14-branch register hasn't shifted and re-checking ahead/behind counts.

