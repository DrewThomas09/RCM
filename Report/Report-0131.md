# Report 0131: Config Map — `configs/playbook.yaml` (CRITICAL parse-failure bug)

## Scope

Maps `RCM_MC/configs/playbook.yaml` (43 lines, 1.7 KB) — one of 5 unmapped YAML configs in `configs/` (Report 0011 covered actual.yaml only). Sister to Reports 0011, 0016, 0083 (yaml). **Discovers a CRITICAL parse-failure bug.**

## Findings

### Module purpose (from file header)

```yaml
# Action plan playbook: maps driver buckets to operational levers, KPIs, and diligence data.
# Edit this file to customize action plan text without code changes.
```

Maps **driver bucket** → 3-field action plan template:
- `lever` (operational intervention)
- `kpi` (metric to track)
- `diligence` (data file/field reference)

### Intended schema (8 driver buckets)

| Bucket | Indent (col) | Status |
|---|---|---|
| `Commercial Denials` | 0 | ✓ valid |
| `Medicare Denials` | 0 | ✓ valid |
| `Medicaid Denials` | **1** | **BROKEN — leading space** |
| `Commercial Underpayments` | **1** | **BROKEN** |
| `Medicare Underpayments` | **1** | **BROKEN** |
| `Medicaid Underpayments` | **1** | **BROKEN** |
| `"Clean-claim A/R days"` | **1** | **BROKEN** |
| `"Appeals costs and days"` | **1** | **BROKEN** |

**6 of 8 keys have a leading space**, making the file invalid YAML.

### CRITICAL: file fails to parse

`python3 -c "yaml.safe_load(open('configs/playbook.yaml'))"`:

```
yaml.parser.ParserError: while parsing a block mapping
  in "RCM_MC/configs/playbook.yaml", line 4, column 1
expected <block end>, but found '<block mapping start>'
  in "RCM_MC/configs/playbook.yaml", line 14, column 2
```

**The file CANNOT be parsed by PyYAML.** Has been broken since `Apr 17 10:27` (per Report 0130 mtime).

### Silent degradation in caller

`reports/html_report.py:1022-1029`:

```python
if attribution_results is not None and playbook_path and os.path.exists(playbook_path):
    try:
        with open(playbook_path) as f:
            playbook = yaml.safe_load(f) or {}
    except Exception:
        playbook = {}
```

**The `except Exception: playbook = {}` SWALLOWS the parse error.** The playbook silently degrades to empty dict.

**Effect**: ALL 8 action-plan rows in the HTML report fall back to "no playbook entry" — even though the file exists, looks valid, and has 43 lines of content. Partners see empty action-plan sections and assume nothing was configured.

**Documented since Apr 17.** Not noticed for 8+ days of audit.

### Reader inventory (3 files)

| File | Line | Pattern |
|---|---|---|
| `cli.py` | (TBD) | likely `--playbook` flag |
| `reports/html_report.py` | 107 (sig) + 1022-1029 (use) | YAML load + `except Exception: playbook = {}` |
| `reports/full_report.py` | 27 (doc), 111 (sig), 151 (passthrough) | passes `playbook_path` to html_report |

### Cross-link to Report 0011 (actual.yaml)

Report 0011 mapped `configs/actual.yaml` — first-mapped config in `configs/`. **Did not test parsability**. This iteration tests parsability and finds 1 of 5 configs broken. **Q1: Are the OTHER 4 also broken? (`benchmark.yaml`, `initiatives_library.yaml`, `value_plan.yaml`, plus `actual.yaml` re-verify.)**

### Cross-link to Report 0024 (logging cross-cut)

The error path `except Exception: playbook = {}` does NOT log. Per Report 0024 + Report 0050 + Report 0104 pattern: another silent-swallow. **MR744 critical** — a parse error of a mission-critical config goes unlogged.

### Cross-link to Report 0099 + 0123 (silent failure pattern)

Project-wide pattern of `try/except Exception: pass` or `try/except: <fallback>` without logging:
- Report 0050 (notifications)
- Report 0099 (custom_metrics dead branch)
- Report 0104 (webhooks delivery write swallow MR578)
- Report 0123 (consistency_check loose `Exception` debug-only)
- **Report 0131 (this — playbook.yaml)**

**5+ instances of silent-failure pattern.** **Project-wide trend.**

### Cross-link to Report 0117 + 0123 schema-version invariants

Same risk class as Report 0058 MR417 (PACKET_SCHEMA_VERSION honor-system) and Report 0123 cross-correction (per-module schema definition with no enforcement). **Pattern**: invariants enforced by convention, not by code.

### `git blame` candidate (not run this iteration)

The broken indentation looks like an accidental space-prefix from a copy-paste. Per file mtime `Apr 17 10:27` — last modified at the same time as 95% of the repo (the `f3f7e7f`-window cleanup commit). **Possibly introduced in that bulk update.**

### Comparison to Report 0011 actual.yaml

Report 0011 cited `actual.yaml` as ~150-line simulator config with mode-specific keys (volumes, payer_mix, denial_rate, etc.). **Verified parsable** at the time. Re-verify needed (Q1).

### Severity assessment

| Aspect | Status |
|---|---|
| File on disk | exists (43 lines, 1.7 KB) |
| Mtime | Apr 17 (8+ days old) |
| Parser status | **FAILS** (yaml.parser.ParserError) |
| Caller behavior | silently degrades to empty dict |
| User-visible | empty action-plan section in HTML report |
| Logged? | NO — `except Exception: pass` swallows |
| CI catch? | NO — no test asserts playbook parses |
| Operator catch? | NO — runs through HTTP report, no error message |

**This is a PRODUCTION BUG that has been silent for 8+ days.** The fix is one-character: remove the leading spaces from 6 lines.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR744** | **`configs/playbook.yaml` is unparseable YAML** — 6 of 8 keys have a leading space causing `ParserError`. File was last modified Apr 17. | **CRITICAL** — silent production bug since Apr 17. All action-plan sections in HTML reports degrade to empty. |
| **MR745** | **`reports/html_report.py:1029` `except Exception: playbook = {}` SWALLOWS the parse error without logging** | Cross-link Reports 0050, 0104, 0123 silent-swallow pattern. Should `logger.warning("playbook YAML parse failed: %s", exc)`. | **High** |
| **MR746** | **No CI test asserts `configs/*.yaml` parses cleanly** | Per Report 0116 ci.yml: 12 named test files. None tests YAML-parse. A schema-validating step would have caught MR744 immediately. | **High** |
| **MR747** | **Project-wide silent-failure pattern**: 5+ instances of `try/except: <fallback>` without logging | Reports 0050, 0099, 0104, 0123, 0131. Each individually low; collectively a discipline gap. | (advisory) |
| **MR748** | **The other 4 unmapped configs may have similar parse bugs** | `benchmark.yaml`, `initiatives_library.yaml`, `value_plan.yaml`. Q1 below — pre-merge requirement. | **Medium** |
| **MR749** | **`reports/full_report.py:27` HTML doc table claims playbook.yaml maps `Driver bucket → lever, kpi, diligence`** | Documentation matches intended schema, not actual broken state. The doc is misleading until MR744 is fixed. | Low |

## Dependencies

- **Incoming:** `cli.py` (CLI flag), `reports/html_report.py:107` (signature), `reports/full_report.py:111` (signature) — 3 sites.
- **Outgoing:** PyYAML's `safe_load`.

## Open questions / Unknowns

- **Q1.** Are the other 4 `configs/*.yaml` files (`actual.yaml`, `benchmark.yaml`, `initiatives_library.yaml`, `value_plan.yaml`) parseable?
- **Q2.** Was the leading-space introduced by the `f3f7e7f` cleanup commit, or earlier? (Run `git blame configs/playbook.yaml`.)
- **Q3.** Is there ANY test that asserts the playbook actually populates the HTML report's action-plan section?
- **Q4.** Does `cli.py` pass `playbook_path=...` by default, or only when `--playbook` flag is given?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0132** | Verify Q1 — test-parse `actual.yaml`, `benchmark.yaml`, `initiatives_library.yaml`, `value_plan.yaml`. |
| **0133** | Concrete bug-fix: remove the leading spaces from playbook.yaml 6 lines. Add `logger.warning` to html_report.py:1029. Add a CI test that asserts all `configs/*.yaml` parse. |
| **0134** | Schema-walk `generated_exports` (Report 0127 MR724, still pre-merge requirement, 5+ iterations carried). |

---

Report/Report-0131.md written.
Next iteration should: test-parse the other 4 `configs/*.yaml` files (Q1) — pre-merge sanity check before any release.
