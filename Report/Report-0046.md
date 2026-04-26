# Report 0046: External Dependency Audit — `numpy`

## Scope

Audits `numpy` (declared at `RCM_MC/pyproject.toml:27` `numpy>=1.24,<3.0`) on `origin/main` at commit `f3f7e7f`. Sister to Report 0016 (pyyaml). Numpy is the most-imported third-party package across the codebase — Report 0005 noted 4 alias spellings in server.py alone.

Prior reports reviewed: 0042-0045.

## Findings

### Pin

`pyproject.toml:27` — `numpy>=1.24,<3.0`. Mirrored in `legacy/heroku/requirements.txt:3`.

- Floor 1.24 (released Dec 2022) — modern enough; pre-1.24 broke numpy 1.20-era APIs (e.g. `np.float`, `np.int` removal).
- Ceiling `<3.0` — numpy 2.0 (released Jun 2024) introduced breaking changes (renamed `np.NAN`/`np.NaN`/`np.Inf` removed, scalar-promotion rule changes, `np.in1d` → `np.isin`, etc.). The `<3.0` ceiling permits 2.x but blocks the next major.
- **The pin allows BOTH numpy 1.x AND 2.x.** Different installations may have different runtime behavior.

### Production usage scale

| Metric | Value |
|---|---:|
| Files importing numpy | **134** |
| Total import statements | 141 |
| Distinct alias spellings | **5** (per Report 0005 + below) |

```
import numpy as np            (canonical)
import numpy as _np
import numpy as _np_hist
import numpy as _np_ldp
import numpy as _np_scr
```

The 4 underscore-prefixed aliases (`_np_hist`, `_np_ldp`, `_np_scr`) are server.py-local lazy imports per Report 0005 MR29. **Confirmed alias proliferation; not addressed.**

134 files = 22% of the ~600+ Python files in the repo. **Numpy is the most-pervasive third-party.**

### Heaviest consumers

Cannot enumerate per-file count without counting; based on prior reports:

- `core/simulator.py` (Report 0038) — uses numpy for sampling, MC iteration, all stats
- `core/distributions.py` (Report 0013) — sampling primitives (`rng.beta`, `rng.normal`, `rng.choice`, etc.)
- `pe/value_bridge_v2.py`, `pe/breakdowns.py`, `pe/pe_math.py` — value-bridge math
- `analysis/packet_builder.py` — quantile + percentile compute (Report 0020 `_pct` fallback)
- `ml/*` — ridge regression, comparable finder, etc. (Report 0005 ml subpackage)
- `data/*` — data manipulation alongside pandas

### Numpy 1.x vs 2.x compatibility — concerns

Numpy 2.0 removed several long-deprecated APIs:

| Removal | Project's exposure |
|---|---|
| `np.NAN`, `np.NaN`, `np.Inf` aliases | Need to grep — historically used in some math libs |
| `np.float`, `np.int`, `np.bool` aliases (already gone since 1.20) | Removed before pin floor; safe |
| `np.product` → use `np.prod` | Mostly older codebases — would need to verify |
| `np.cumproduct` → `np.cumprod` | Same |
| `np.in1d` → `np.isin` | Common in code that builds masks; need to verify |
| `np.alltrue`/`np.sometrue` → `np.all`/`np.any` | Need to verify |
| Scalar-array promotion rules | **Subtle.** A code path that depends on the old promotion (e.g. `np.float32(1.0) + 1` returning float32) breaks under 2.x's new rules. |

**Without testing the codebase against numpy 2.x explicitly, the `<3.0` pin is allowing untested-with-numpy-2.x installs.**

### CI matrix coverage

Per Report 0026, CI runs Python 3.11/3.12/3.14 with `pip install -e ".[dev]"`. **The matrix doesn't pin numpy version.** So:

- A 3.11 runner gets the latest numpy at install time (likely 2.x as of 2026).
- A 3.14 runner gets the latest 3.14-compatible numpy (likely 2.x).
- **No 1.x test job exists.** The pin allows 1.24+ but CI never tests against 1.x.

If a customer installs with `pip install seekingchartis numpy<2`, they get numpy 1.x — **untested.**

### Upstream status

| Field | Value |
|---|---|
| Project | numpy.org / github.com/numpy/numpy |
| Latest stable | **2.x series** (1.26 was the last 1.x; 2.0 released June 2024; 2.x cadence ~quarterly) |
| Maintenance | **Highly active.** Numpy is foundational; supported by NumFOCUS + Quansight + others. |
| Abandoned? | Absolutely not. |
| Pure-Python? | No — extensively C-accelerated. Wheels ship pre-built for major platforms. |

### Known historical CVEs

Numpy CVEs are rare and usually low-impact (numpy is a math library; the attack surface is narrow). Notable:

- **CVE-2021-33430** — `np.PyArray_NewFromDescr` integer overflow (DoS only; needed crafted input). Affected 1.20.x; fixed in 1.20.x patch. Project pin floor 1.24+ → unaffected.
- **CVE-2017-12852** — `np.pad` infinite loop on negative input. Fixed in 1.13. Pre-historic for this project.

**No actively-exploitable numpy CVEs in the project's call profile.**

### Trust-boundary analysis

Numpy is invoked on:

1. **YAML-loaded config primitives** (Reports 0011, 0012) — YAML → Python dicts → distribution params → `rng.beta(...)`. Trusted.
2. **CSV-loaded HCRIS data** (`data/hcris.py` per Report 0023) — public CMS data. Trusted.
3. **Test fixtures** — synthetic. Trusted.
4. **Output DataFrames** — produced by simulator, written to disk. No remote input.

**Numpy never receives untrusted remote bytes.** Same trust posture as pyyaml (Report 0016).

### `numpy` ↔ `pandas` coupling

Both are core deps. Pandas 2.x can be backed by numpy 1.x or 2.x; pandas 2.2+ has full numpy 2 support. Project pin `pandas>=2.0,<4.0` allows pandas 2.0-3.x. **Pandas-numpy version pairing unverified.**

### Use of new (numpy 2.x) APIs

`grep -rn "np\.in1d\|np\.product\|np\.cumproduct\|np\.alltrue\|np\.sometrue\|np\.NAN\|np\.NaN\b"` — **not run this iteration.** Worth doing.

If the codebase still uses numpy 1.x APIs (e.g. `np.in1d`), it works on 1.x but fails on 2.x. Combined with the unrestricted CI matrix, **a customer running under numpy 2.x would hit `AttributeError` on a 1.x-only API**.

## Merge risks flagged

| ID | Risk | Detail | Severity |
|---|---|---|---|
| **MR363** | **Pin allows numpy 2.x but no 2.x test verification** | CI installs whatever pip resolves. Local dev / Azure deploy may install different versions of numpy. **Untested numpy-2.x installs reach production.** | **High** |
| **MR364** | **No numpy-1.x test job either** | Pin floor 1.24 — but CI never tests against 1.x. Customers who pin numpy<2 (common in scientific Python ecosystems) are untested. | **High** |
| **MR365** | **5 alias spellings in production** (cross-link Report 0005 MR29) | `np`, `_np`, `_np_hist`, `_np_ldp`, `_np_scr`. A consolidation refactor changes 141 import statements + every reference. **Multi-branch-merge minefield**; defer until post-merge. | Medium |
| **MR366** | **`np.in1d` / `np.product` / `np.NAN` deprecated APIs not yet swept** | If used, `<3.0` pin allows install but `>=2.0` runtime fails. Pre-merge: `grep -rn "np\.in1d\|np\.product\|np\.NAN" RCM_MC/rcm_mc`. | **High** until verified |
| **MR367** | **No `requirements-lock.txt`** (cross-link Report 0023 MR189) | Numpy patch versions float. A regression in numpy 2.0.5 → 2.0.6 (hypothetical) appears differently across boxes. | Medium |
| **MR368** | **Pandas-numpy pairing unverified** | Pandas pin `>=2.0,<4.0` allows pandas 3.x — which doesn't exist as of audit time. Pin floor is fine; ceiling is over-permissive. | Low |

## Dependencies

- **Incoming:** 134 production files + tests; via the runtime closure pulled by `pip install`.
- **Outgoing:** Numpy ships its own C extensions — depends on the platform's C runtime + a BLAS/LAPACK provider (numpy 2.x bundles OpenBLAS in wheels). Project doesn't enforce a specific BLAS.

## Open questions / Unknowns

- **Q1.** Does the codebase use `np.in1d`, `np.product`, `np.cumproduct`, `np.NAN`, `np.alltrue`, `np.sometrue`? Sweep needed.
- **Q2.** Is the CI runner's installed numpy version logged anywhere? If yes, post-mortem of a 2.x-vs-1.x split is possible.
- **Q3.** Does the Azure VM's `pip install` (per Dockerfile / vm_setup.sh) lock to a specific numpy major?

## Suggested follow-ups

| Iteration | Proposed area | Why |
|---|---|---|
| **0047** | **Database/storage layer** (already requested as iteration 47). | Pending. |
| **0048** | **Sweep for deprecated numpy APIs** | Resolves Q1 / MR366. |
| **0049** | **Audit `pandas` external dep** | Sister core dep. |

---

Report/Report-0046.md written. Next iteration should: do a database/storage-layer audit on the `runs` SQLite table (the second canonical table created at `portfolio/store.py:125`) — sister to Report 0017 (deals table) and resolves Report 0008's noted gap that `list_runs` and `get_run` have ZERO direct test references.

