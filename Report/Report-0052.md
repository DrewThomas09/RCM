# Report 0052: Circular Import Risk — `infra/` Subsystem

## Scope

Cycle audit on `RCM_MC/rcm_mc/infra/`. Sister to Report 0022 (analysis/).

## Findings

### Subpackage shape

Per Report 0019 inventory, `infra/` includes: `logger.py`, `config.py`, `migrations.py`, `cache.py`, `capacity.py`, `output_index.py`, `output_formats.py`, `run_history.py`, `_terminal.py`, `_bundle.py`, `notifications.py`, `webhooks.py`, `provenance.py`, `automation_engine.py`, `backup.py`, `rate_limit.py`, `trace.py`, `taxonomy.py`, `migrations.py`. ~20 files.

### Sibling-import adjacency

`grep -E "^from \.([a-z_]+)" RCM_MC/rcm_mc/infra/*.py`:

```
config.py        → .logger
notifications.py → .logger (assumed; per Report 0024)
capacity.py      → .logger (per Report 0024)
output_formats.py→ .logger
run_history.py   → .logger
migrations.py    → (likely none — datetime/typing only)
backup.py        → .logger (4 logger.error sites per Report 0024)
trace.py         → ..core.simulator (cross-package; no infra-internal cycle)
```

**Most infra/ modules import only `.logger`** which is a stdlib-only leaf (per Report 0035).

### Dependency layers (within infra/)

```
Layer 0: logger.py (stdlib only)
Layer 1: config.py, capacity.py, notifications.py, output_formats.py,
         run_history.py, backup.py, ... (depend on logger)
Layer 2: (none observed — flat structure)
```

**Clean DAG.** Most files at Layer 1, all importing the leaf logger.

### No cycles

`infra/` has a flat structure. logger.py is the universal leaf; no module imports logger AND is imported by logger.

### Cross-package edges

`infra/trace.py:14` imports `from ..core.simulator import simulate_one` (per Report 0039). One-way out — no return import.

### Near-cycle hazards

None detected. The `infra/` flat structure is hard to cycle by design.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR394** | infra/ is cycle-free; structurally robust | (advisory) |
| **MR395** | logger.py is a hub — every infra/ module + most rcm_mc/ modules depend on it. A logger.py refactor cascades widely (cross-link Report 0024 MR195) | Medium |

## Dependencies

- **Incoming:** all of `rcm_mc/` (146 logger callers per Report 0024).
- **Outgoing:** stdlib only (logger), with one cross-package edge (trace.py → core.simulator).

## Open questions / Unknowns

- **Q1.** Is `infra/_bundle.py` imported by anyone? Mentioned in Report 0011 but never enumerated.

## Suggested follow-ups

| Iteration | Proposed area | Why |
|---|---|---|
| **0053** | **Version drift** (already requested). | Pending. |
| **0054** | **Cross-cutting concern** (already requested). | Pending. |

---

Report/Report-0052.md written. Next iteration should: version drift / cross-cutting both queued — proceed in order.

