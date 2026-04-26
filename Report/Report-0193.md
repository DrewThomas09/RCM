# Report 0193: API Surface — `verticals/registry.py` (smallest unmapped)

## Scope

Reads `RCM_MC/rcm_mc/verticals/registry.py` (33 lines) — smallest module from Report 0190's 12 unmapped subpackages. Closes Report 0190 Q1.

## Findings

### Subpackage layout

```
verticals/
├── README.md
├── __init__.py        (0 LOC — empty file!)
├── asc/               (subdirectory)
├── behavioral_health/ (subdirectory)
├── mso/               (subdirectory)
└── registry.py        (33 LOC)
```

**5 entries: 1 README + 1 empty __init__ + 1 registry.py + 3 subpackage directories.** Per Report 0190 "py: 2" count was top-level only — there are MORE files in subdirs (`asc/`, `mso/`, `behavioral_health/`).

### Public API (registry.py)

| Symbol | Line | Kind | Docstring? |
|---|---|---|---|
| `Vertical` | 12 | Enum (4 values: HOSPITAL, ASC, MSO, BEHAVIORAL_HEALTH) | NONE |
| `get_metric_registry(vertical: str) -> Dict[str, Dict[str, Any]]` | 19 | function | YES (1-line) |

**2 public symbols.**

### `Vertical` Enum

```python
class Vertical(str, Enum):
    HOSPITAL = "HOSPITAL"
    ASC = "ASC"
    MSO = "MSO"
    BEHAVIORAL_HEALTH = "BEHAVIORAL_HEALTH"
```

**4-value enum.** Cross-link Report 0094 (domain/econ_ontology Domain enum) — same `str, Enum` pattern.

### `get_metric_registry()` dispatch

Lines 19-33:
```python
def get_metric_registry(vertical: str) -> Dict[str, Dict[str, Any]]:
    """Return the metric registry for the given vertical."""
    v = vertical.upper()
    if v == "ASC":
        from .asc.ontology import ASC_METRIC_REGISTRY
        return ASC_METRIC_REGISTRY
    if v == "MSO":
        from .mso.ontology import MSO_METRIC_REGISTRY
        return MSO_METRIC_REGISTRY
    if v == "BEHAVIORAL_HEALTH":
        from .behavioral_health.ontology import BH_METRIC_REGISTRY
        return BH_METRIC_REGISTRY
    # Default: hospital.
    from ..analysis.completeness import RCM_METRIC_REGISTRY
    return RCM_METRIC_REGISTRY
```

**Lazy-import dispatcher.** Per CLAUDE.md `analysis/completeness.RCM_METRIC_REGISTRY` → cross-link Report 0091 backlog.

**3 NEW unmapped sub-subpackages discovered**: `verticals/asc/`, `verticals/mso/`, `verticals/behavioral_health/`. Each has `ontology.py` per dispatch lines.

### Default fallback

`if v not in ("ASC", "MSO", "BEHAVIORAL_HEALTH")`: returns `RCM_METRIC_REGISTRY` (hospital). **Implicit hospital default** — caller passes "HOSPITAL" → hits no `if`, gets hospital registry.

### Empty `__init__.py`

**0 LOC.** Cross-link Report 0093 ml/__init__ (30L), 0094 domain/__init__ (58L), 0153 pe_intelligence/__init__ (3,490L). **`verticals/__init__.py` is the OPPOSITE — completely empty.** Means callers must import from `rcm_mc.verticals.registry` directly.

### NEW finding — 4-vertical-extension architecture

**`Vertical` enum has 4 values; 3 sub-ontologies + 1 default.** Per CLAUDE.md "Phase 4 added ... vertical-aware analysis." The verticals subpackage is the **vertical-extension surface**. Each vertical has an ontology in its sub-subpackage.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR960** | **`verticals/__init__.py` is EMPTY (0 LOC)** | Cross-link Report 0093/0094/0153. Means no namespace re-export — callers MUST import from sub-modules directly. **Less ergonomic** than other subpackages. | Low |
| **MR961** | **`Vertical` Enum has NO docstring** | Public-symbol gap. Cross-link Report 0103 MR566 (JOB_STATUSES tuple-not-Enum). Here is the inverse — Enum without docstring. | Low |
| **MR962** | **3 sub-subpackages NEW unmapped**: `verticals/asc/`, `verticals/mso/`, `verticals/behavioral_health/` | Each has an `ontology.py` per dispatcher. **Each likely has a `<X>_METRIC_REGISTRY` const** mirroring `RCM_METRIC_REGISTRY`. Add to backlog. | Medium |
| **MR963** | **NEW unmapped module**: `analysis/completeness.py` (referenced for `RCM_METRIC_REGISTRY`) | Cross-link Report 0091. | Medium |

## Dependencies

- **Incoming:** TBD — likely `analysis/packet_builder.py` (Phase-4 vertical-aware logic).
- **Outgoing:** stdlib (Enum, typing); 4 ontology constants via lazy import.

## Open questions / Unknowns

- **Q1.** What's `RCM_METRIC_REGISTRY` shape (in `analysis/completeness.py`)?
- **Q2.** Per-vertical ontology divergence — how do ASC/MSO/BH metrics differ from hospital?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0194** | Doc gap (in flight). |
| **0195** | Tech-debt (in flight). |

---

Report/Report-0193.md written.
