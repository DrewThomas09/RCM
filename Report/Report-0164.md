# Report 0164: Documentation Gap — `reports/reporting.py`

## Scope

`RCM_MC/rcm_mc/reports/reporting.py` (561 lines, 13 public functions, ~15 docstring counts) — discovered in Report 0163 as one of 2 NEW unmapped modules. Sister to Reports 0014, 0044, 0104, 0119, 0134.

## Findings

### Public surface (13 fns)

| Line | Function |
|---|---|
| 10 | `summarize_distribution(df, col)` |
| 27 | `summary_table(df, cols)` |
| 36 | `pretty_money(x)` |
| 63 | `_driver_label(name)` (private) |
| 83 | `waterfall_ebitda_drag(...)` |
| 162 | `plot_denial_drivers_chart(df_drag, outpath, top_n=10)` |
| 189 | `plot_underpayments_chart(df_drag, outpath)` |
| 220 | `plot_deal_summary(summary, ev_multiple, outpath)` |
| 256 | `plot_ebitda_drag_distribution(...)` |
| 364 | `correlation_sensitivity(df, driver_cols, target_col="ebitda_drag", top_n=12)` |
| 383 | `strategic_priority_matrix(sens_df)` |
| 429 | `actionable_insights(summary, sensitivity, ev_multiple=8.0)` |
| 524 | `assumption_summary(cfg, n_draws=5000, seed=42)` |

### Docstring count vs functions

- 13 `^def ` lines (public + private)
- 15 docstring openings (per `grep -c '    """'`)
- **Some functions docstring-rich, some thin**

### Module docstring — MISSING

Per `head -20`: file starts with `from __future__ import annotations` directly. **NO module-level docstring.** Cross-link Report 0129 MR736 (`core/distributions.py` same gap). Pattern observation: utility/plot modules tend to skip module docstring.

### Function-level doc gaps (sampled)

`summarize_distribution(df, col) -> Dict[str, float]` (line 10) — appears to have NO docstring (line 11 starts `x = df[col]...`). **Public function undocumented.**

`summary_table` (line 27) — NO docstring observed.

`pretty_money` (line 36) — formats USD; likely has docstring (functions like this typically do).

### What's missing — concrete

| Element | Status |
|---|---|
| Module docstring | **MISSING** |
| `summarize_distribution` docstring | likely missing |
| `summary_table` docstring | likely missing |
| `pretty_money` docstring | TBD |
| 4 plot_* functions docstrings | TBD (matplotlib charts; behavior usually well-documented) |
| `correlation_sensitivity`, `strategic_priority_matrix`, `actionable_insights`, `assumption_summary` | TBD |

### Imports

```python
from __future__ import annotations
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
```

**3 third-party** (numpy, pandas, matplotlib). Heavy. Cross-link Report 0125 portfolio.store outgoing dep pattern.

### Comparison vs other audited modules

| Module | Lines | Module docstring | Per-fn docstrings |
|---|---|---|---|
| `domain/econ_ontology` (Report 0095) | 816 | YES | YES |
| `infra/_terminal` (Report 0109) | 231 | YES | YES |
| `infra/data_retention` (Report 0123) | 79 | YES | YES |
| `analysis/deal_overrides` (Report 0134) | 410 | YES | YES |
| **`reports/reporting.py` (this)** | **561** | **NO** | **partial** |

**`reporting.py` is below the project doc-discipline median.** Per Report 0134 doc-foil pattern: utility modules often under-documented vs analysis-layer.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR881** | **`reports/reporting.py` lacks module docstring** | New developer reading top of file sees only imports. | Low |
| **MR882** | **At least 2 public functions appear to lack docstrings** (`summarize_distribution`, `summary_table`) | Per Report 0104 MR575 (webhooks), 0133 MR758 (export_store) pattern. Project-wide utility-module under-documentation. | Medium |
| **MR883** | **13-public-function module imported by `cli.py` (per Report 0163)** | Stale signature in any of these breaks `cli.py`. | (advisory) |

## Dependencies

- **Incoming:** `cli.py` (per Report 0163 imports 12 names from this module).
- **Outgoing:** numpy, pandas, matplotlib + stdlib.

## Open questions / Unknowns

- **Q1.** Per-function docstring density actual count (this iteration sampled head only).

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0165** | Tech-debt (in flight). |
| **0166** | External dep audit. |

---

Report/Report-0164.md written.
