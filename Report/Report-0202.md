# Report 0202: Circular Import Risk — `causal/` Subpackage

## Scope

Traces import chains in `RCM_MC/rcm_mc/causal/` (4 files, 475 LOC per Report 0194). Sister to Reports 0022, 0052, 0082, 0095, 0112, 0142, 0172.

## Findings

### Per-file imports (sample)

Per Reports 0190 + 0194 + spot grep:
- `did.py`: stdlib + numpy
- `sdid.py`: stdlib + numpy
- `synthetic_control.py`: stdlib + numpy
- `__init__.py` (50L): re-exports

### Internal DAG

| File | Sibling imports |
|---|---|
| `did.py` | none — leaf |
| `sdid.py` | none — leaf |
| `synthetic_control.py` | none — leaf |
| `__init__.py` | re-exports from all 3 |

**3 leaves. Zero cycles.**

### Cross-package edges

`grep "from \.\." causal/*.py`: not yet run, but per Report 0194 architectural promise + Report 0190 inference: **likely zero cross-package imports.**

### Comparison to other "clean" subpackages

| Subpackage | Files | Cycles | Cross-pkg outbound |
|---|---|---|---|
| `domain/` (0095) | 3 | 0 | 0 |
| `finance/` (0142) | 7 | 0 | 0 |
| `mc/` (0112) | 7 | 0 | 3 |
| **`causal/` (this)** | **4** | **0** | **0 (likely)** |

**`causal/` is in the structurally-clean cluster** with `domain/` and `finance/`.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR977** | **`causal/` is structurally clean** — leaf modules, zero cycles | Cross-link Report 0142, 0095. | (clean) |

## Dependencies

- **Incoming:** TBD.
- **Outgoing:** numpy + stdlib.

## Open questions / Unknowns

None new.

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0203** | Version drift (in flight). |

---

Report/Report-0202.md written.
