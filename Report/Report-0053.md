# Report 0053: Version Drift — `pandas` Pin vs Imports

## Scope

Audits `pandas` (declared at `pyproject.toml:28` `pandas>=2.0,<4.0`) on `origin/main` at commit `f3f7e7f`. Sister to Reports 0016 (pyyaml) + 0046 (numpy). Pandas is the second-most-imported third-party.

## Findings

### Pin

`pyproject.toml:28` — `pandas>=2.0,<4.0`. Mirrored in `legacy/heroku/requirements.txt:4`.

- Floor 2.0 (released April 2023) — modern enough to drop pandas 1.x edge cases (e.g. SettingWithCopyWarning behavior).
- Ceiling `<4.0` — pandas 3.0 has not been released yet (audit at 2026-04-25). The `<4.0` ceiling is **over-permissive** — allows future pandas 3.x AND 4.x prereleases.

### Production usage scale

| Metric | Estimate |
|---|---:|
| Files importing pandas | likely ~100+ (similar to numpy's 134 per Report 0046) |
| Distinct alias spellings | **10** (per Report 0005 server.py: `_pd`, `_pd_analysis`, `_pd_cal`, `_pd_home`, `_pd_hr`, `_pd_port`, `_pd_pres`, `_pd_reg`, `_pd_runs`, `pd`) |

### Pandas-numpy compatibility

Per Report 0046, numpy pin allows 1.x AND 2.x. Pandas 2.0 supports numpy 1.x; pandas 2.2+ supports both 1.x and 2.x; pandas 3.x will be numpy-2.x-only.

**Project's `pandas>=2.0,<4.0` × `numpy>=1.24,<3.0` matrix produces 4 install combinations:**

| pandas | numpy | Compat | Note |
|---|---|---|---|
| 2.0-2.1 | 1.x | ✅ | Original pin baseline |
| 2.0-2.1 | 2.x | ⚠️ pandas 2.0/2.1 don't fully support numpy 2 | **Untested; risky** |
| 2.2+ | 1.x | ✅ | |
| 2.2+ | 2.x | ✅ | |
| 3.x (future) | 2.x only | ⚠️ pandas 3 drops numpy 1 | Future-incompatible |

### Pandas 3.0 breaking changes (announced)

When pandas 3.0 ships:
- Default index becomes RangeIndex (was Int64Index).
- Copy-on-write becomes default (currently opt-in).
- Numpy 1.x dropped.

A `pip install pandas>=3.0` on a future install would silently install 3.x, changing default behavior. **`<4.0` ceiling does NOT prevent 3.x.** Recommend tightening to `<3.0` for a known-tested baseline, then bump after testing.

### Deprecated pandas APIs

Pandas 3.0 deprecates `df.append`, `df.iteritems`, `pd.Index.is_integer`, etc. Without a sweep, hard to say what the codebase uses.

### CI matrix coverage

Per Report 0026, CI installs `pip install -e ".[dev]"` (no pin). Same hazard as numpy: untested cross-version installs reach production.

### Upstream

- Project: pandas-dev/pandas, very active.
- Latest stable as of audit: 2.2.x.
- 3.0 in alpha/beta as of mid-2026.

### Trust boundary

Same as numpy + yaml: pandas operates on local CSVs, validated YAML configs, simulator outputs. No remote untrusted bytes. Clean.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR396** | **Pin `<4.0` allows pandas 3.x — untested** | Tighten to `<3.0` until 3.x compat verified. | **High** |
| **MR397** | **Pandas-numpy matrix has 4 combinations; not all tested** | Pandas 2.0-2.1 + numpy 2.x is unsupported but the pins allow it. | **High** |
| **MR398** | **10 alias spellings in server.py** (cross-link MR29) | Same as numpy proliferation. | Medium |
| **MR399** | **Deprecated pandas APIs not swept** | `df.append`, `df.iteritems`, `pd.Index.is_integer` etc. — pandas 3 removes them. | Medium |
| **MR400** | **No requirements-lock.txt** (cross-link Report 0023 MR189) | Patch versions float across boxes. | Medium |

## Dependencies

- **Incoming:** ~100+ Python files, including all of `core/`, `pe/`, `analysis/`, `data/`, `data_public/`, `ml/`.
- **Outgoing:** numpy (transitive), Python C extensions (pyarrow optional).

## Open questions / Unknowns

- **Q1.** What pandas version does the production Docker image actually ship?
- **Q2.** Does any code use `df.append` (deprecated) or `df.iteritems` (removed in 2.0)?

## Suggested follow-ups

| Iteration | Proposed area | Why |
|---|---|---|
| **0054** | **Cross-cutting concern** (already requested). | Pending. |
| **0055** | **Integration point** (already requested). | Pending. |

---

Report/Report-0053.md written. Next iteration should: cross-cutting concern audit on caching (already queued as iteration 54).

