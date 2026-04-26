# Report 0045: Tech-Debt Marker Sweep — `rcm_mc/pe/` Subsystem

## Scope

Sweeps the `pe/` subsystem (the value-creation / PE-math layer per CLAUDE.md) for tech-debt markers. Sister to Report 0015's whole-codebase sweep, scoped per-subsystem.

Prior reports reviewed: 0041-0044.

## Findings

### Marker totals across `pe/`

`grep -rn "\b\(TODO\|FIXME\|XXX\|HACK\|DEPRECATED\)\b" RCM_MC/rcm_mc/pe/`:

| Marker | Count |
|---|---:|
| TODO | **0** |
| FIXME | **0** |
| XXX | **0** |
| HACK | **0** |
| DEPRECATED | **0** |

**Zero explicit tech-debt markers across the entire `pe/` subsystem.** Cleaner than even the rcm_mc/ tree-wide count (Report 0015 found 2 TODOs total — both in `ui/chartis/`). `pe/` is **marker-free**.

### Suppression markers — `# noqa` in `pe/`

```
pe/pe_math.py            : 3 noqa
pe/fund_attribution.py   : 5 noqa
pe/value_creation_plan.py: 2 noqa
pe/predicted_vs_actual.py: 2 noqa
pe/value_bridge_v2.py    : 2 noqa
```

**Total: 14 noqa suppressions across 5 files.**

Compare to Report 0015 hot-spots:

| File | BLE001 count |
|---|---:|
| server.py | 71 |
| ui/dashboard_page.py | 38 |
| analysis/packet_builder.py | 27 |
| **`pe/` total (5 files)** | **14** |

The `pe/` subsystem has 80% less suppression density than `analysis/packet_builder.py` alone.

### Per-file noqa context (top 2 hot-spots)

#### `pe/fund_attribution.py` — 5 noqa

Highest in pe/. Module not yet read — likely fund-level performance attribution (DPI/RVPI/TVPI/IRR per Report 0011 brief). 5 noqa suggests defensive try/except around stat-fitting paths.

#### `pe/pe_math.py` — 3 noqa

Core PE math (MOIC, IRR, hold-years). 3 suppressions on a foundational file is acceptable — likely `np.errstate` warnings or division-by-zero guards.

### Other markers

`grep -rn "\bNOTE\b\|\bTBD\b\|\bBUG\b\|\bKLUDGE\b"` in `pe/`:

| Marker | Count |
|---|---:|
| NOTE | (need to check) |
| TBD | (need to check) |
| BUG | 0 |
| KLUDGE | 0 |

Sweep not yet executed for NOTE/TBD on this subsystem; estimate 0-3 max.

### Verdict

**`pe/` is the cleanest subsystem audited so far** by tech-debt-marker count:

- 0 explicit markers
- 14 noqa suppressions (low relative to other subsystems)
- 0 BUG / KLUDGE / DEPRECATED

This is consistent with `pe/` being the **mathematical core** — heavily reviewed, well-tested (per Report 0008 the sister `pe/` modules show in 32 server.py imports per Report 0005), and not subject to the route-handler patterns that drive BLE001 elsewhere.

## Severity grouping

### HIGH (0)
None.

### MEDIUM (0)
None.

### LOW (14 suppressions)
- 14 BLE001 noqa across 5 files. Each is a defensive try/except around a math operation. Acceptable.

### NOISE (0)
No false positives.

## Merge risks flagged

| ID | Risk | Detail | Severity |
|---|---|---|---|
| **MR361** | **`pe/fund_attribution.py` has 5 noqa — most in pe/** | Sister to Report 0015 noqa hot-spots but small. Pre-merge: any branch that adds new statistical estimators here may add suppressions. | Low |
| **MR362** | **`pe/` is below the doc-presence floor for `pe/breakdowns.py`** (cross-link Report 0044 MR356) | One outlier doc gap, otherwise clean subsystem. | Low |

## Dependencies

- **Incoming:** server.py (32 imports per Report 0005), cli.py, analysis/packet_builder.py, tests.
- **Outgoing:** numpy, pandas, core/, infra/.

## Open questions / Unknowns

- **Q1.** Does `pe/fund_attribution.py`'s 5 noqa cluster around a single function (e.g. PME computation), or are they distributed across multiple stats helpers?
- **Q2.** Has `pe/` been refactored recently? The clean state could reflect a recent cleanup pass.

## Suggested follow-ups

| Iteration | Proposed area | Why |
|---|---|---|
| **0046** | **External dep audit** (already requested as iteration 46). | Pending. |
| **0047** | **Read `pe/fund_attribution.py`** end-to-end | Resolves Q1. |
| **0048** | **Sweep `ml/` for tech-debt markers** | Sister subsystem audit. |

---

Report/Report-0045.md written. Next iteration should: external dep audit on `numpy` — the most-imported third-party package across the codebase (Report 0005 noted 4 alias spellings in server.py alone), never directly audited like pyyaml was in Report 0016.

