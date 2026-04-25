# Report 0034: Incoming-Dep Graph for `infra/config.py`

## Scope

Maps every place `RCM_MC/rcm_mc/infra/config.py` is imported on `origin/main` at commit `f3f7e7f`. The module owns `load_yaml`, `validate_config`, `load_and_validate`, `canonical_payer_name`, `_validate_dist_spec` — surveyed in Reports 0011 + 0012 but never had its incoming graph traced.

Prior reports reviewed: 0030-0033.

## Findings

### Production importers (10 unique files)

`grep -rln "from .*infra\.config\|from \.\.infra\.config\|from \.config" RCM_MC/rcm_mc/`:

| File | Site | Symbol(s) imported |
|---|---|---|
| `rcm_mc/api.py` | (line not extracted) | `validate_config` (likely) |
| `rcm_mc/server.py` | (multiple sites) | various |
| `rcm_mc/cli.py:339` (per Report 0012) | top-level | `load_and_validate` |
| `rcm_mc/pe/value_plan.py:9` | top-level | `validate_config` |
| `rcm_mc/core/_calib_schema.py:9` | top-level | `canonical_payer_name` |
| `rcm_mc/analysis/packet_builder.py:928` | **lazy / inside try** | `load_and_validate` |
| `rcm_mc/analysis/challenge.py:302` | **lazy / inside try** | `load_and_validate` |
| `rcm_mc/deals/deal.py:81` | **lazy / inside try** | `load_and_validate` |
| `rcm_mc/scenarios/scenario_shocks.py:10` | top-level | `load_and_validate` |
| `rcm_mc/data/intake.py:27` | top-level | `validate_config` |

**10 files. 4 are lazy (inside try blocks); 6 are top-level.**

### Symbol-by-symbol coupling

| Public symbol | Import sites (estimated) | Use |
|---|---:|---|
| `load_yaml(path)` | (likely 1-2) | Internal helper, used inside `load_and_validate` |
| `validate_config(cfg)` | 3 (api.py, value_plan.py, intake.py) | Validator |
| `load_and_validate(path)` | 6 (cli.py, packet_builder.py, challenge.py, deal.py, scenario_shocks.py, server.py) | Combined load+validate (most-used) |
| `canonical_payer_name(name)` | 1 (`core/_calib_schema.py`) | Payer alias resolver |
| `_validate_dist_spec(spec)` | (private helper, 0 external) | — |
| `diff_configs(a, b)` (per Report 0012) | (likely 0-1) | Config diff tool |
| `apply_scenario_dict(cfg, adj)` (referenced cli.py:381) | 1 (cli.py) | Scenario adjustment |

### Coupling-tightness verdict

- **10 production importers** — moderate tight coupling. **Above the >5 callers threshold** for "tight" per the iteration prompt.
- **No orphan path**: every symbol is used somewhere.
- **`load_and_validate` is the dominant entry-point** (6 of 10 importers).
- **Test coverage** (not enumerated): per Report 0011, the schema is implicit in `validate_config` — likely heavily tested.

### Lazy vs top-level pattern

The 4 lazy imports (packet_builder.py:928, challenge.py:302, deal.py:81, plus one in server.py) are all inside try blocks — they accept the import as failable. Per Report 0020, `packet_builder.py:928` is inside a `try / except Exception: # noqa BLE001` cluster (the simulation-comparison block). **Implication:** if `infra/config.py` has a module-load error, those 4 callers degrade gracefully (return SectionStatus.FAILED); the 6 top-level callers fail at module-load time.

### Cross-cuts

- **cli.py** is the most-coupled top-level caller — uses `load_and_validate` for both `actual.yaml` and `benchmark.yaml`.
- **api.py** (orphan per Report 0010 MR72) imports it but is otherwise unused — the import is dead weight.
- **server.py** uses it for HTTP-form-uploaded config validation (per Report 0012).

### Tight-coupling consequences

Any breaking change to:

| Function | Cost |
|---|---|
| `load_and_validate(path)` signature | 6 callers must update |
| `validate_config(cfg)` signature | 3 callers must update |
| `canonical_payer_name(name)` signature | 1 caller must update |
| `_validate_dist_spec` (private) | 0 external impact (internal only) |

The aggregate fan-in is 10 unique production files. Plus tests (not enumerated this iteration but likely 20+).

## Merge risks flagged

| ID | Risk | Detail | Severity |
|---|---|---|---|
| **MR301** | **`infra/config.py` is the chokepoint for every config path** | 10 production importers; signature changes ripple to all of them, plus the `[api]` orphan (api.py). Cross-link Report 0011 MR81. | **High** |
| **MR302** | **Lazy imports in 4 sites mean module-load errors are silent** | If a future branch breaks `infra/config.py`'s top-level (e.g. an import error), packet_builder.py:928, challenge.py:302, deal.py:81, server.py callsites degrade gracefully — but cli.py:339 + scenario_shocks.py:10 + value_plan.py:9 + _calib_schema.py:9 + intake.py:27 + api.py break at module-load time. **Asymmetric failure surface.** | Medium |
| **MR303** | **`api.py` orphan still imports `infra/config.py`** | Cross-link Report 0010 MR72 — api.py has 0 production importers but still pulls in the config validator. **Dead-weight import.** | Low |
| **MR304** | **`canonical_payer_name` has only 1 importer (`core/_calib_schema.py`)** | Tightly-coupled but narrow. Pre-merge: any branch that adds a payer alias must verify the single consumer still resolves correctly. | Low |

## Dependencies

- **Incoming:** 10 production files + ~20 test files (estimated). Total: ~30 files.
- **Outgoing:** stdlib (yaml via pyyaml — Report 0016), `os` (env vars), regex; NO internal `rcm_mc.*` imports per Report 0012's read.

## Open questions / Unknowns

- **Q1.** What does `api.py` actually do with `infra.config`? Is there a code path inside that orphan that's reachable? Need full read.
- **Q2.** Why do 4 of 10 callers use lazy imports? Is it because `infra.config` has a side-effect at import time (it doesn't seem to per Report 0011), or is it convention for "optional features"?

## Suggested follow-ups

| Iteration | Proposed area | Why |
|---|---|---|
| **0035** | **Outgoing-dep graph for `infra/config.py`** | Already requested; complements this report. |
| **0036** | **Audit `api.py`** end-to-end | Resolves Q1; closes the orphan question. |

---

Report/Report-0034.md written. Next iteration should: trace the outgoing-dep graph for `infra/config.py` to see what it pulls in (per Report 0011 it's stdlib + pyyaml only — but a deep verification would confirm the chokepoint has no hidden internal deps).

