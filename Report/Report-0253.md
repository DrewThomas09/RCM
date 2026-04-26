# Report 0253: API Surface — `rcm_mc/infra/config.py`

## Scope

Public-API enumeration of `RCM_MC/rcm_mc/infra/config.py` (538 LOC). Single-gate validation seam discovered in Report 0252 Hop 5d. Sister to Reports 0207 (Engagement schema), 0245 (ai/ outgoing), 0252 (intake flow).

## Findings

### `__all__` declaration

**MISSING.** No explicit `__all__` in `infra/config.py`. **Public surface is implicit** — every name not prefixed `_` is importable. Cross-link CLAUDE.md "Private helpers prefix with underscore" convention.

### Constants (module level)

| Name | Line | Value |
|---|---|---|
| `MANDATORY_PAYERS` | 16 | `("Medicare", "Medicaid", "Commercial", "SelfPay")` — comment says "Kept for backward compatibility but no longer enforced" |
| `CURRENT_SCHEMA_VERSION` | 18 | `"1.0"` |
| `_VALID_DIST_TYPES` | 104 | `{"fixed", "beta", "normal", "normal_trunc", "gaussian", "triangular", "lognormal", "gamma", "empirical"}` — private (prefix) |
| `_DIST_REQUIRED_FIELDS` | 106 | dict — private |

### Public class

| Class | Line | Signature |
|---|---|---|
| `ConfigError(ValueError)` | 21 | exception type, no body |

### Public functions (12)

| # | Function | Signature | Line | Has docstring? |
|---|---|---|---|---|
| 1 | `load_yaml` | `(path: str) -> Dict[str, Any]` | 58 | YES — "Load YAML with support for _extends inheritance (Step 34) and env var substitution (Step 38)." |
| 2 | `canonical_payer_name` | `(name: str) -> str` | 80 | NO docstring (one of the few without) |
| 3 | `validate_config` | `(cfg: Dict[str, Any]) -> Dict[str, Any]` | 200 | YES |
| 4 | `load_and_validate` | `(path: str) -> Dict[str, Any]` | 436 | NO docstring — 1-liner: `return validate_config(load_yaml(path))` |
| 5 | `diff_configs` | `(cfg_a, cfg_b, prefix: str = "") -> List[Dict[str, Any]]` | 442 | YES |
| 6 | `validate_config_from_path` | `(path: str) -> Tuple[bool, List[str]]` | 469 | YES |
| 7 | `is_multi_site` | `(cfg: Dict[str, Any]) -> bool` | 485 | YES (one-liner) |
| 8 | `expand_multi_site` | `(cfg: Dict[str, Any]) -> List[Dict[str, Any]]` | 490 | YES |
| 9 | `export_config_json` | `(cfg, path: str) -> None` | 512 | YES (one-liner) |
| 10 | `import_config_json` | `(path: str) -> Dict[str, Any]` | 519 | YES (one-liner) |
| 11 | `flatten_config` | `(cfg, prefix: str = "") -> List[Dict[str, str]]` | 528 | YES |

### Private helpers (correctly underscored)

`_deep_merge` (25), `_resolve_env_vars` (36), `_require` (99), `_validate_dist_spec` (119), `_sum_to_one` (146), `_validate_deal_section` (151), `_canonical_payer_name = canonical_payer_name` (96 — alias for back-compat).

### Back-compat alias

`_canonical_payer_name = canonical_payer_name` at line 96. Comment: "Backwards-compatible alias (kept to avoid breaking any external imports)". **Internal-only — but if external code imports via the underscore name it still works.**

### External imports across repo (test files only sampled)

24 test files import from `rcm_mc.infra.config`. Tally of imported symbols:

| Symbol | Test imports |
|---|---|
| `load_and_validate` | 16+ |
| `validate_config` | 7 |
| `ConfigError` | 4 |
| `diff_configs` | 1 (test_config_validation.py) |

**Most imported: `load_and_validate`.** This is the de-facto public seam.

**NOT imported by any sampled test (zero hits):** `load_yaml`, `canonical_payer_name`, `validate_config_from_path`, `is_multi_site`, `expand_multi_site`, `export_config_json`, `import_config_json`, `flatten_config`.

### Undocumented public surface (per CLAUDE.md "Docstrings explain *why*")

Functions missing docstrings:
- `canonical_payer_name` (80) — undocumented payer-canonicalization logic. **Risk:** alias rules (Self-Pay→SelfPay, Private/PHI→Commercial) are non-obvious. Cross-link Report 0153 free-form-text classification pattern.
- `load_and_validate` (436) — one-liner, but contract not stated.

### Duplicate-purpose APIs (interface drift)

- `validate_config_from_path` (469) returns `(bool, List[str])` — soft.
- `load_and_validate` (436) raises on failure — hard.
- Both wrap `validate_config(load_yaml(path))`. **Two ways to do the same thing** with opposite error contracts.

### `_extends` inheritance (line 66-72)

Allows YAML to declare `_extends: <relative_path>` to inherit from another YAML, with deep-merge. **Recursive** — `load_yaml(base_path)` is re-called. **No cycle detection.** A YAML that extends itself transitively would cause infinite recursion → `RecursionError` (depth limit ≈ 1000).

### `${ENV_VAR}` and `${ENV_VAR:default}` substitution (line 36-55)

`_resolve_env_vars` does regex replacement for `${VAR}` and `${VAR:default}` patterns inside any string in cfg. **Recursive into dict + list values.** If env var unset and no default, **emits warning** but leaves placeholder string intact (line 48-49). **Not a hard failure.** Cross-link Report 0131 silent-failure pattern.

### Cross-correction Report 0252 Hop 5d

Report 0252 listed 3 validation entrypoints. **Confirmed precise lines:**
- `validate_config` at 200 (the actual gate)
- `load_and_validate` at 436 (1-liner: `return validate_config(load_yaml(path))`)
- `validate_config_from_path` at 469 (soft return, wraps load_and_validate)

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR1046** | **No `__all__` declared** — every non-underscore name is implicit public surface | A future cleanup that renames any of the 12 public functions risks breaking unknown external callers (24+ test files + production importers not yet enumerated). **Add `__all__`.** Cross-link Report 0249 MR1027. | Medium |
| **MR1047** | **`_extends` recursion has no cycle detection** at line 66-72 | A YAML that extends itself (direct or transitive) → `RecursionError` 1000-deep stack. **Add cycle guard with seen-set.** | Medium |
| **MR1048** | **Env-var substitution `_resolve_env_vars` silent-passes unset vars** at line 48-49 | Returns the literal `${UNSET_VAR}` string in config. Downstream may use it as if it were a valid value. Cross-link Report 0131. | Medium |
| **MR1049** | **`canonical_payer_name` undocumented + non-obvious aliases** at line 80 | "Self-Pay" → "SelfPay", "Private"/"PHI" → "Commercial". Surprising mappings. **Add docstring listing the 4-canonical-payer alias rules.** | Low |
| **MR1050** | **Two contracts for same op: `load_and_validate` (raise) vs `validate_config_from_path` (soft)** | Pick one or document the distinction. Risk: callers use the wrong one. | Low |
| **MR1051** | **`MANDATORY_PAYERS` constant unused per comment** at line 15 | Dead constant kept "for backward compatibility". If no external import remains, **deletion candidate**. | Low |

## Dependencies

- **Incoming:** ≥24 test modules confirmed; production `data/intake.py:27` (`from ..infra.config import validate_config`); production `data/intake.py:219` (`validate_config(cfg)`); likely many more (Report 0252 noted as central seam).
- **Outgoing:** stdlib (json, os, re, copy, dataclasses, typing) + pyyaml + `.logger.logger`.

## Open questions / Unknowns

- **Q1.** Are `is_multi_site`/`expand_multi_site` actually used in production (zero test imports)?
- **Q2.** Are `export_config_json`/`import_config_json` used (zero test imports)?
- **Q3.** Are `flatten_config` and `canonical_payer_name` used externally?
- **Q4.** Does `MANDATORY_PAYERS` have any remaining importer?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0254** | Inspect `vendor/ChartisDrewIntel/` (carried from Report 0250). |
| **0255** | Production importer survey for `is_multi_site`/`expand_multi_site`/`export_config_json`/`flatten_config`/`MANDATORY_PAYERS` (closes Q1-Q4). |
| **0256** | Documentation gap: write `__all__` proposal for `infra/config.py` (closes MR1046). |

---

Report/Report-0253.md written. Next iteration should: documentation gap audit on `infra/config.py` undocumented signatures + propose `__all__` (closes MR1046, MR1049 — cadence due).
