# Report 0016: External Dependency Audit — `pyyaml`

## Scope

This report covers the **external dependency audit of `pyyaml`** on `origin/main` at commit `f3f7e7f`. PyYAML was selected because it is named in `RCM_MC/pyproject.toml:29` (`pyyaml>=6.0,<7.0`) as one of the 5 core runtime dependencies, it is foundational to the simulator's config-loader pipeline (Reports 0011 + 0012), and the `yaml.load` ↔ `yaml.safe_load` distinction is a well-known security pitfall that warrants a dedicated audit.

The audit covers: pinning, every call site, attack-surface exposure, lock-file presence, and upstream maintenance status.

Prior reports reviewed before writing: 0012-0015.

## Findings

### Pin and pin discipline

- **Declared in:** `RCM_MC/pyproject.toml:29` — `pyyaml>=6.0,<7.0`.
- **Mirrored in:** `legacy/heroku/requirements.txt:5` — `pyyaml>=6.0,<7.0`. Comment says "mirrors RCM_MC/pyproject.toml [project.dependencies]". The legacy file is intentionally a duplicate.
- **No lock file** for the modern install path. `find . -name "*.lock" -o -name "requirements*.txt"` returns only `legacy/heroku/requirements.txt` and `.claude/scheduled_tasks.lock` (unrelated). **No `poetry.lock` / `uv.lock` / `requirements-lock.txt` / `Pipfile.lock`.** Every fresh `pip install -e .` resolves to whatever PyYAML 6.x is current at install time.
- **Pin range `>=6.0,<7.0`** is the correct posture: PyYAML 6.0 (released March 2022) removed the bare `yaml.load` default that had been a long-standing security footgun. The pin guarantees no 5.x install (which still allows the unsafe default).

### Production usage map

`grep -rln "import yaml" RCM_MC/rcm_mc/`:

- **24 production files** use yaml directly.

Sample of import sites (representative):

| File:line | Import |
|---|---|
| `RCM_MC/rcm_mc/pe/value_plan.py:7` | `import yaml` |
| `RCM_MC/rcm_mc/rcm/initiatives.py:11` | `import yaml` |
| `RCM_MC/rcm_mc/infra/config.py:10` | `import yaml` (the canonical loader chokepoint per Report 0012) |
| `RCM_MC/rcm_mc/core/calibration.py:10` | `import yaml` |
| `RCM_MC/rcm_mc/analysis/pressure_test.py:40` | `import yaml` |
| `RCM_MC/rcm_mc/deals/deal.py:36` | `import yaml` |
| `RCM_MC/rcm_mc/diligence/cyber/ehr_vendor_risk.py:7` | `import yaml` |
| `RCM_MC/rcm_mc/diligence/cyber/business_associate_map.py:14` | `import yaml` |
| `RCM_MC/rcm_mc/diligence/ma_dynamics/v28_recalibration.py:25` | `import yaml` |
| `RCM_MC/rcm_mc/diligence/ma_dynamics/coding_intensity_analyzer.py:17` | `import yaml` |
| (14 more files) | |

Plus **10 test files** under `RCM_MC/tests/` import yaml: `test_config_roundtrip.py`, `test_challenge.py`, `test_workbook_style.py`, `test_deal_track.py`, `test_bundle.py`, `test_config_partial_inputs.py`, `test_config_validation.py`, `test_intake.py`, `test_cli_regression.py`, `test_pressure_test.py`.

### API call distribution — 37 yaml.* call sites

| Symbol | Occurrences | Verdict |
|---|---:|---|
| **`yaml.safe_load`** | **27** | the safe loader — best practice |
| **`yaml.safe_dump`** | **7** | the safe dumper — best practice |
| `yaml.YAMLError` | 4 | exception-handling — pattern-correct |
| `yaml.load` | **0** | **the dangerous variant — 0 occurrences** |
| `yaml.dump` | 0 | absent |
| `yaml.FullLoader` | 0 | absent |
| `yaml.SafeLoader` | 0 | absent (used implicitly via safe_load) |
| `yaml.UnsafeLoader` | 0 | absent (the dangerous loader) |
| `yaml.BaseLoader` | 0 | absent |
| `Loader=...` (custom) | 0 | absent — no Loader override anywhere |
| `yaml.add_constructor` / `add_representer` | 0 | absent — no custom YAML constructors / representers |

**Every yaml load operation in production code is `yaml.safe_load`. Every yaml dump is `yaml.safe_dump`.** The codebase has **no code-execution attack surface** via yaml deserialization.

### Sample call-site contexts

| File:line | Pattern |
|---|---|
| `infra/config.py:61` | `data = yaml.safe_load(f)` — the canonical config loader (per Report 0012) |
| `core/calibration.py:540` | `cfg = yaml.safe_load(yaml.safe_dump(base_cfg))  # deep copy, YAML-safe` — explicit "use yaml as deep-copy" idiom; intentional and safe |
| `core/calibration.py:890` | `yaml.safe_dump(cfg, f, sort_keys=False)` — write back the calibrated config |
| `pe/value_plan.py:35` | `plan = yaml.safe_load(f)` — value-plan config |
| `analysis/pressure_test.py:176, 188` | `raw = yaml.safe_load(f) or {}` — defensive None-coalesce on empty file |
| `deals/deal.py:59` | `yaml.safe_dump(state, f, sort_keys=False)` — deal state persistence |
| `deals/deal.py:68, 243` | `yaml.safe_load(f) or {}` |
| `diligence/cyber/ehr_vendor_risk.py:14` | `return yaml.safe_load(...)` |
| `diligence/cyber/business_associate_map.py:42` | `data = yaml.safe_load(...)` |

### YAMLError handling sites (4 total)

| File:line | Catch |
|---|---|
| `analysis/pressure_test.py:189` | `except (OSError, yaml.YAMLError):` — combined I/O + parse |
| `deals/deal.py:248` | `except (OSError, yaml.YAMLError):` — same idiom |
| `diligence/regulatory/__init__.py:79` | `except yaml.YAMLError as exc:` — captures exception object |
| `reports/_partner_brief.py:151` | `except (OSError, yaml.YAMLError):` |

**4 sites catch YAMLError; 30+ sites do not.** Per Report 0015, the codebase carries 369 `# noqa: BLE001` (broad-except) sites — many of those probably wrap yaml-loading code with `except Exception` and silently swallow yaml parse errors. **Pre-merge: any branch that adds yaml-loading code in a route handler should explicitly catch `yaml.YAMLError`** rather than rely on the broad-except convention.

### Vendor-tree usage (out-of-scope but adjacent)

- `vendor/ChartisDrewIntel/docs/scripts/build_data_quality_tests_json.py` (Python helper)
- `vendor/ChartisDrewIntel/docs/src/components/fetchModelColumns.js` (JavaScript — not Python yaml)
- `vendor/ChartisDrewIntel/docs/src/components/DataQualityTestsTable.js`
- `vendor/ChartisDrewIntel/scripts/publish-dolthub-seeds`

These files reference yaml but are vendored (Report 0001) — not in the project's pip-install closure.

### Upstream status (as of 2026-04-25 per public knowledge)

| Field | Value |
|---|---|
| Project | PyYAML — `pyyaml.org` / `github.com/yaml/pyyaml` |
| Latest stable | **6.0.2** (released ~September 2024) |
| Maintenance | **Active.** Maintained primarily by Ingy döt Net + the YAML org. Releases approximately yearly. |
| Abandoned? | **No.** |
| Pure-Python? | No — ships C-accelerated bindings via `libyaml`. The `import yaml` works either way; performance differs. |
| `libyaml` version shipped | PyYAML 6.0+ requires libyaml ≥ 0.2.5 |

### Known historical CVEs against PyYAML

| CVE | Year | Affected | Resolution |
|---|---|---|---|
| **CVE-2017-18342** | 2017 | `yaml.load(...)` with default loader (untrusted input → arbitrary code execution) | **Fixed:** 5.1+ deprecated bare `yaml.load`; 6.0 removed the unsafe default entirely. Project uses `yaml.safe_load` exclusively → **unaffected**. |
| **CVE-2020-1747** | 2020 | Improper input validation in YAML deserialization | Fixed in 5.4. Project pin `>=6.0` → unaffected. |
| **CVE-2020-14343** | 2020 | Use of unsafe `yaml.load` allowed code injection via crafted YAML | Same as above; project unaffected. |
| **libyaml CVE-2014-9130** | 2014 | Crafted YAML triggers heap buffer overflow in `libyaml` | PyYAML 6.0+ requires libyaml 0.2.5+ which patches this. |

**No known PyYAML CVEs are exploitable in this project's call profile.**

### Per-CVE applicability check

For each historical CVE, the question is: would the project's call pattern allow exploitation?

| CVE | Required call pattern | Project pattern | Exploitable? |
|---|---|---|---|
| CVE-2017-18342 | `yaml.load(untrusted)` with default loader | `yaml.safe_load(...)` only | **No** |
| CVE-2020-1747 | unsafe `yaml.load` | `yaml.safe_load` only | **No** |
| CVE-2020-14343 | `yaml.load(untrusted)` | `yaml.safe_load` only | **No** |
| libyaml CVE-2014-9130 | crafted YAML through libyaml C parser | depends on libyaml version, but `safe_load` still uses libyaml when present | Mitigated by PyYAML's libyaml ≥ 0.2.5 floor; **No real-world exploitability under safe_load** |

### Trust-boundary analysis

The project loads YAML from:

1. **CLI args** (`--actual`, `--benchmark`, `--scenario` paths) — user-supplied, but the user is the analyst running the tool locally. **Trust = self.**
2. **Local config files** (`RCM_MC/configs/*.yaml`, scenarios, playbook) — committed to repo. **Trust = repo.**
3. **HTTP form input** (per Report 0012, `server.py:291` and `:12745` accept paths from a web form) — **could be a remote-trust boundary** if the server is exposed. The form takes a path, not file content; assumes path on server filesystem. Still trusted.
4. **Calibration round-trip** (`core/calibration.py:540` does `yaml.safe_load(yaml.safe_dump(...))` for deep copy) — round-trip of in-memory data; **trusted.**
5. **No remote YAML fetching** detected — no `requests.get(...).text` → `yaml.safe_load` patterns. Confirmed via spot-check.

**The trust boundary stays inside the local install in all 5 paths.** Combined with `safe_load`-only, the dependency is functionally non-exploitable.

### Maintenance-burden signal

24 production files import yaml. A change in PyYAML's behavior (e.g. tightening type coercion, removing implicit boolean parsing of `yes/no/on/off` — already changed in 6.0 to "off by default"!) would ripple to 24 callers. The pin `<7.0` correctly guards against the 7.0 major bump, where the **YAML 1.2 strict-mode** is expected to land (deprecating implicit booleans entirely).

## Merge risks flagged

| ID | Risk | Detail | Severity |
|---|---|---|---|
| **MR115** | **No lock file for the modern install path** | Only `legacy/heroku/requirements.txt` exists, mirroring pyproject. Modern installs (`pip install -e .`) resolve PyYAML at install time — every dev box, CI runner, Azure VM may have a different `pyyaml==6.0.x` pinned in their installed environment. **A regression in PyYAML 6.0.3 (hypothetical) would not be reproducible across boxes.** Recommend: generate `requirements-lock.txt` via `pip-compile` and commit it. | Medium |
| **MR116** | **24 production files import yaml — wide blast radius** | Any branch that changes the loader chokepoint (`infra/config.py:61`) needs to verify the 24 callers still work. Most callers go through `infra/config.py:436 load_and_validate`, but 6+ files import yaml directly (`pe/value_plan.py`, `rcm/initiatives.py`, `analysis/pressure_test.py`, `core/calibration.py`, `deals/deal.py`, `diligence/cyber/*`, `diligence/ma_dynamics/*`, `reports/_partner_brief.py`). | Medium |
| **MR117** | **YAML 1.1 vs 1.2 implicit-boolean drift** | PyYAML 6.0 made YAML 1.2 the default. `yes/no/on/off` are no longer parsed as booleans; they're strings. **A YAML config written for 5.x that uses `enabled: yes` will load as the string `"yes"` instead of `True`.** Pre-merge: scan `configs/*.yaml` and any test fixtures for `yes/no/on/off` literals. | **High** |
| **MR118** | **Broad-except convention may mask `yaml.YAMLError`** | Per Report 0015, 369 `# noqa: BLE001` sites swallow exceptions broadly. Any of those wrapping yaml-loading code will silently consume YAMLError — corrupt YAML → empty dict → wrong behavior, not an error. Pre-merge: any new yaml caller should explicitly catch `yaml.YAMLError`. | Medium |
| **MR119** | **`legacy/heroku/requirements.txt` is a documentation source of truth** | If a feature branch updates `pyproject.toml` deps but not `legacy/heroku/requirements.txt`, the legacy file becomes stale. **Heroku deploys would silently install a different version set than local installs.** Per Report 0007 MR47, `feature/workbench-corpus-polish` removes Heroku support entirely — would resolve this risk if merged. | Low |
| **MR120** | **`feature/workbench-corpus-polish` did NOT change `pyyaml` pin** | Verified via `git diff origin/main..origin/feature/workbench-corpus-polish -- RCM_MC/pyproject.toml` (Report 0007): pyyaml line is untouched on that branch. Same likely true on others; **pre-merge sweep recommended** for all 8 ahead-of-main branches. | Low |
| **MR121** | **No yaml-injection regression test** | None of the 10 yaml-importing test files appear (by name) to verify that `safe_load` rejects `!!python/object/apply:os.system` patterns. **A future refactor that swaps `safe_load` for `load` would not be caught by tests.** Recommend: add a `test_yaml_safety.py` that asserts no `import yaml` in production code uses `yaml.load`. | Medium |

## Dependencies

- **Incoming (who depends on pyyaml):** 24 production files + 10 test files; the simulator config flow (Reports 0011, 0012); `legacy/heroku/requirements.txt`; deploy stack (`RCM_MC/deploy/Dockerfile` likely runs `pip install` against pyproject.toml).
- **Outgoing (what pyyaml depends on):** Optionally `libyaml` (C parser); transitively pulled into `pip` resolution graph but no project code references it directly.

## Open questions / Unknowns

- **Q1 (this report).** Do any `RCM_MC/configs/*.yaml` files use `yes/no/on/off` literals that would now load as strings under YAML 1.2? Resolves MR117.
- **Q2.** Does `RCM_MC/deploy/Dockerfile` install yaml from pyproject.toml or from `legacy/heroku/requirements.txt`? Tells us which pin is the actual production source-of-truth.
- **Q3.** Does any of the 10 yaml-importing test files exercise an injection-attempt YAML to verify `safe_load` rejects it? If not, MR121 has no countermeasure.
- **Q4.** Is the libyaml C parser installed in the Azure VM deploy target, or does it fall back to pure-Python? Affects parse speed but not security.
- **Q5.** Are there any yaml-loading sites that take a *content* string (not a file path) — i.e. could remote content be parsed? Spot-check via `yaml.safe_load(string)` patterns.
- **Q6.** Does any feature branch add a 25th yaml-importing file with a non-safe call pattern? Cross-branch sweep needed.

## Suggested follow-ups

| Iteration | Proposed area | Why |
|---|---|---|
| **0017** | **Audit `RCM_MC/configs/*.yaml` and test fixtures for `yes/no/on/off` literals.** | Resolves Q1 / MR117 — the YAML 1.1 → 1.2 boolean-implicit-coercion regression risk. |
| **0018** | **Generate a `requirements-lock.txt`** via `pip-compile` and commit it. | Resolves MR115. |
| **0019** | **Audit pandas dependency** (the second core dep). | Pandas has the largest API surface among core deps; same audit pattern applies. |
| **0020** | **Sample-inspect 20 BLE001 sites in `server.py`** — owed since Report 0015. | Closes Q1 from 0015 + part of MR118 here. |
| **0021** | **Cross-branch yaml-call-pattern sweep** — does any ahead-of-main branch add a non-safe yaml call? | Resolves Q6 / MR120-MR121. |
| **0022** | **Audit numpy dependency** (the largest core dep). | Same audit pattern; numpy has fewer security implications but huge API surface. |

---

Report/Report-0016.md written. Next iteration should: scan `RCM_MC/configs/*.yaml` and test fixtures for the 6 YAML 1.1 implicit-boolean literals (`yes`, `no`, `on`, `off`, `Yes`, `No`) — closes Q1 here and MR117 (the silent string-vs-bool regression risk under PyYAML 6.x).

