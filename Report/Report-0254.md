# Report 0254: Documentation Gap — `rcm_mc/infra/` README + `config.py`

## Scope

Documentation-gap audit on `RCM_MC/rcm_mc/infra/` (28 .py modules) vs `infra/README.md` (323 LOC, 26 documented sections). Cross-link Reports 0252 (intake flow), 0253 (config.py API surface).

## Findings

### High-priority — README contains FACTUAL ERRORS for `config.py`

`infra/README.md:8` says:

> Provides the `load_and_validate()` function that all modules use to read deal configs.

OK — matches Report 0253 (line 436).

`infra/README.md:10` says:

> Raises `ConfigValidationError` with a descriptive message on failure. Also provides `write_yaml(path, config)` for writing calibrated configs.

**Both claims are WRONG.**

| README claim | Actual code |
|---|---|
| `ConfigValidationError` | **Does not exist.** Class is `ConfigError` at `infra/config.py:21`. |
| `write_yaml(path, config)` | **Does not exist in `config.py`.** It lives at `core/calibration.py:887`, not infra. |

`infra/README.md:10` also says:

> normalizes payer names via `core/_calib_schema.py`

**Misleading.** Payer normalization is `canonical_payer_name()` at `infra/config.py:80` (Report 0253). `core/_calib_schema.py` may exist but is **not** the normalization seam used by `validate_config`.

### Modules MISSING from `infra/README.md`

infra/ has **28 .py files**, README documents **26**. Two modules wholly undocumented:

| File | Status |
|---|---|
| `infra/cache.py` | **No README section.** Function unknown to documentation. |
| `infra/morning_digest.py` | **No README section.** (Modified +13 LOC on `feat/ui-rework-v3` per Report 0247.) |

### Public-API undocumented surface in `config.py` (per Report 0253)

| Function | Line | Docstring? |
|---|---|---|
| `canonical_payer_name` | 80 | NO |
| `load_and_validate` | 436 | NO (1-liner; contract not stated) |

### Module-level docstring missing

`infra/config.py:1-13` opens with imports — **no module-level docstring**. CLAUDE.md ("Docstrings explain *why*") implies module-level should explain the constraint or design rationale. **Module is the central config seam (24+ test importers per Report 0253) and has zero opening narrative.**

### `MANDATORY_PAYERS` constant undocumented (line 16)

Comment says "Step 31: Kept for backward compatibility but no longer enforced." **Unclear:** is this still imported externally? If not, deletion candidate (cross-link Report 0253 MR1051).

### `_DIST_REQUIRED_FIELDS` (line 106-119) — undocumented

Distribution-spec validation rule table. Used by `_validate_dist_spec` (line 119). **Could benefit from a 2-line comment listing required-fields-by-dist-type contract** (per CLAUDE.md "non-obvious WHY").

### `_extends` and `${ENV_VAR:default}` undocumented at module level

`load_yaml` at line 58 has a one-line docstring referencing "Step 34" + "Step 38" — **but these step numbers are internal/historical and provide no usage example**. New contributors cannot discover the `_extends` syntax without reading the implementation.

**Suggested addition (concrete):**
```yaml
# Inheriting another config:
_extends: ./base_hospital.yaml
hospital:
  annual_revenue: 600_000_000  # overrides

# Env-var substitution:
db_path: ${RCM_MC_DB:portfolio.db}
```

### `validate_config_from_path` vs `load_and_validate` confusion

Two near-identical entry points at lines 436 + 469 (cross-link Report 0253 MR1050). README documents **only `load_and_validate`** — `validate_config_from_path` is undocumented in the README. **Risk:** soft-vs-hard error contract not surfaced to consumers.

### Concrete additions proposed

1. **Fix `infra/README.md:10`**: replace `ConfigValidationError` → `ConfigError`. Remove the `write_yaml` claim (move that to core/README if needed).
2. **Add module-level docstring to `infra/config.py`** describing the load/validate/diff/expand/export pipeline + `_extends` + env-var-substitution syntax.
3. **Add README sections for `cache.py` and `morning_digest.py`** — currently undocumented.
4. **Add docstring for `canonical_payer_name`** — list the 4-canonical-payer alias rules (per Report 0253 MR1049).
5. **Add docstring for `load_and_validate`** — note that it raises `ConfigError` on failure (vs `validate_config_from_path` which returns `(bool, errors)`).
6. **Add `__all__` to `config.py`** declaring the 12 public names + `ConfigError` + `MANDATORY_PAYERS` + `CURRENT_SCHEMA_VERSION` (closes Report 0253 MR1046).
7. **Document `_extends` cycle behavior** — currently silent infinite-recursion (Report 0253 MR1047).

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR1052** | **`infra/README.md` references `ConfigValidationError` and `write_yaml` — neither exists in `config.py`** | New contributors will write `except ConfigValidationError:` and silently never catch the real error. **Stale-doc-drives-bug pattern.** | High |
| **MR1053** | **`cache.py` and `morning_digest.py` undocumented** | 2 modules invisible to README readers. `morning_digest.py` was just modified on `feat/ui-rework-v3` (Report 0247) — drift will compound. | Medium |
| **MR1054** | **`config.py` has no module-level docstring** despite being the central validation seam | Cross-link Report 0253 — 24+ test importers, no narrative. | Low |
| **MR1055** | **`_extends` syntax + env-var syntax not documented anywhere** users will see | Discoverable only by reading source. CLAUDE.md does not mention either. | Medium |

## Dependencies

- **Incoming:** all `infra/README.md` readers; new contributors; CI doc-build (if any).
- **Outgoing:** N/A (documentation).

## Open questions / Unknowns

- **Q1.** Was `ConfigValidationError` ever the class name (renamed to `ConfigError` later)?
- **Q2.** What does `infra/cache.py` do (module purpose)?
- **Q3.** What does `infra/morning_digest.py` do (module purpose)?
- **Q4.** Is `MANDATORY_PAYERS` constant imported anywhere? (carried Report 0253 Q4)

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0255** | Inspect `vendor/ChartisDrewIntel/` (carried from Report 0250). |
| **0256** | Read `infra/cache.py` head — close Q2. |
| **0257** | Read `infra/morning_digest.py` head — close Q3. |

---

Report/Report-0254.md written. Next iteration should: tech-debt marker sweep on `infra/` (28 modules) — surface TODO/FIXME/XXX/HACK markers + Step-NN ticket residue (e.g., line 15 "Step 31").
