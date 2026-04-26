# Report 0252: Data Flow Trace — `rcm-intake` CLI → `actual.yaml`

## Scope

End-to-end trace of the intake-wizard data path: stdin/argv → `rcm_mc/data/intake.py:main` → 11 prompts → template merge → validation → YAML on disk. Closes Report 0251 MR1035 verification + Q2. Sister to Reports 0163 (cli.py), 0190 (small subpackages).

## Findings

### Entry: console-script `rcm-intake`

`pyproject.toml:70` declares `rcm-intake = "rcm_mc.intake:main"`. **BROKEN** at this hop — `rcm_mc/intake.py` does not exist (Report 0251 MR1035 confirmed). Real `main()` lives at `rcm_mc/data/intake.py:619`. After `pip install`, `rcm-intake` raises `ModuleNotFoundError` before reaching any flow below.

**Workaround paths that DO work:**
- Direct module: `python -m rcm_mc.data.intake`
- Subprocess: `python rcm_mc/data/intake.py` (line 675-676 has `if __name__ == "__main__": sys.exit(main())`)
- Via `rcm-mc intake` if `cli.py` dispatches subcommand (Report 0163; cross-link `tests/test_cli_dispatcher.py:67` "rcm-mc lookup" form)

### Hop 1 — argv parsing

`rcm_mc/data/intake.py:619-644` (`main(argv, prog)`):

| Flag | Default | Purpose |
|---|---|---|
| `--out` | `"actual.yaml"` | Output YAML path |
| `--from-ccn` | `None` | 6-digit Medicare Provider Number (HCRIS pre-fill) |
| `--from-name` | `None` | fuzzy hospital name → CCN resolver |

### Hop 2 — name → CCN resolver (optional, non-interactive)

`intake.py:650-655` calls `_resolve_name_to_ccn(args.from_name)`. Pure-function; can exit non-zero before TTY check. Reads from CMS HCRIS lookup tables.

### Hop 3 — TTY guard

`intake.py:657-662`: if `sys.stdin.isatty()` is False → writes guidance to stderr + returns `2`. Prevents headless runs.

### Hop 4 — `interactive_intake(out, ccn_prefill)`

`intake.py:400` defines `interactive_intake`. Drives the 11-prompt wizard via `_ask()` (line 229) which loops until valid. Calls into `_hcris_prefill_bundle` (line 304) when `--from-ccn` is provided.

### Hop 5 — answers dict → `run_intake()` orchestrator

`intake.py:198-224` `run_intake(answers, template_name, out_path, extra_observations)`:

```python
cfg = load_template(template_name)              # 214
apply_intake_answers(cfg, answers)              # 215
if extra_observations:
    for path, note in extra_observations.items():
        mark_observed(cfg, path, note=note)     # 218 (data/sources.py:159)
validate_config(cfg)                            # 219 (infra/config.py:200)
out_abs = os.path.abspath(out_path)             # 220
os.makedirs(os.path.dirname(out_abs) or ".", exist_ok=True)  # 221
with open(out_abs, "w") as f:
    yaml.safe_dump(cfg, f, sort_keys=False)     # 222-223
return cfg
```

### Hop 5a — `load_template` (line 44-52)

```python
TEMPLATES = {
  "community_hospital_500m": _PACKAGE_ROOT / "configs" / "templates" / "community_hospital_500m.yaml",
  "rural_critical_access":   _PACKAGE_ROOT / "configs" / "templates" / "rural_critical_access.yaml",
  "actual":                   _PACKAGE_ROOT / "configs" / "actual.yaml",
}
```

`_PACKAGE_ROOT = Path(__file__).resolve().parent.parent.parent` (line 34) → repo `RCM_MC/`. **Three templates available; default is `community_hospital_500m`.**

`yaml.safe_load(f) or {}` — empty file becomes `{}` rather than `None`.

### Hop 5b — `apply_intake_answers` (line 121-195)

Mutates cfg in-place; returns list of "touched" dotted paths. Per docstring, collapses 131-field config surface to 11 user answers.

### Hop 5c — `mark_observed` (rcm_mc/data/sources.py:159)

Stamps provenance ("CMS HCRIS FY{Y}, CCN {X}" or "provided via intake wizard") onto specific dotted-path fields. Cross-link Report 0167 — provenance metadata pattern.

### Hop 5d — `validate_config` (rcm_mc/infra/config.py:200)

Raises `ValueError` if cfg malformed. Two related entrypoints exist:
- `infra/config.py:437` — `load_and_validate_path` — `validate_config(load_yaml(path))`
- `infra/config.py:469` — `validate_config_from_path` returns `(bool, List[str])`

**Single validation gate** before YAML emission.

### Hop 6 — YAML emission

`yaml.safe_dump(cfg, f, sort_keys=False)` at line 223 — preserves declared key order. Output goes to `os.path.abspath(out_path)` (default `./actual.yaml`).

### Exit codes

| Code | Source |
|---|---|
| `0` | success (line 672) |
| `1` | ValueError or FileNotFoundError (line 669-670) |
| `2` | non-TTY stdin (line 662) |
| `130` | KeyboardInterrupt (line 666-667) |
| (resolve_name fail code) | `_resolve_name_to_ccn` propagates non-zero (line 654) |

### Downstream consumers of `actual.yaml`

Once written, `actual.yaml` is read by:
- `rcm-mc` runs (per CLAUDE.md "Running" section + Phase 4 packet builder)
- `rcm_mc/infra/config.py:437` — `load_and_validate_path`
- Cross-link Report 0131 (playbook.yaml unparseable issue) — separate config but same yaml.safe_load pattern

### MR1035 verification

`pyproject.toml:70` "rcm_mc.intake:main" → no module exists → `ModuleNotFoundError` at `pip install` invocation time. **Confirmed.** Test path `tests/test_cli_dispatcher.py:141` ("rcm-intake remain functional as aliases") would fail in installed-mode subprocess test. **Q1 below.**

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR1042** | **Step 5 (`run_intake`) writes YAML *before* validation can be re-checked** — atomic-write absent | If `validate_config(cfg)` raises mid-flight after `os.makedirs` but before `yaml.safe_dump`, no file is written. Acceptable. **However**, no temp-file → rename. If process is killed during yaml.safe_dump, partial YAML on disk silently corrupts later loads. | Medium |
| **MR1043** | **Stdin/TTY guard at line 657** — does NOT detect SIGPIPE / orchestrator pipe input | If stdin is piped (a CI test harness), guard returns 2 even if answers could be supplied programmatically. **Use `run_intake()` directly for tests.** | Low |
| **MR1044** | **Default template `community_hospital_500m`** is hard-coded at line 200 | If template removed/renamed, `run_intake()` fails. Cross-link Report 0131 yaml-pattern. | Low |
| **MR1045** | **`yaml.safe_load(f) or {}` at line 52** silently turns malformed-empty into empty dict | Cross-link Report 0131 silent-failure pattern. **Validation later catches malformed structure**, but a wholly-empty template would skip user-visible warning. | Low |
| **MR1035** | (carried) `rcm-intake` console-script broken | (closure pending shim) | (carried) |

## Dependencies

- **Incoming:** `pyproject.toml:70` (broken), `tests/test_cli_dispatcher.py`, `tests/test_lookup.py` (cross-package), `readME/04_Getting_Started.md:60` (`rcm-intake --out actual.yaml`).
- **Outgoing:** `..infra.config.validate_config`, `.sources.mark_observed`, `pyyaml`, `argparse`, CMS HCRIS lookup (CCN resolver).

## Open questions / Unknowns

- **Q1.** Does the test suite run `rcm-intake` as installed-mode subprocess, or only direct-import? (closes MR1035 escape risk)
- **Q2.** Does `_resolve_name_to_ccn` print top-5 matches to stdout or stderr? (affects scripted callers)
- **Q3.** Does `apply_intake_answers` (line 121) mutate cfg in ways that bypass `mark_observed` provenance for non-HCRIS fields?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0253** | Inspect `vendor/ChartisDrewIntel/` (carried from Report 0250 Q1). |
| **0254** | Read `infra/config.py:200` `validate_config` body — single-gate validation contract. |
| **0255** | Read `apply_intake_answers` (line 121-195) for Q3. |

---

Report/Report-0252.md written. Next iteration should: API surface scan of `rcm_mc/infra/config.py` (single-gate validation seam — `validate_config` + `load_and_validate_path` + `validate_config_from_path` per Report 0252 Hop 5d).
