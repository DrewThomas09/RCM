# Report 0145: Integration Point — `dbt-core` invocation in `rcm_mc_diligence/ingest/connector.py`

## Scope

Audits the `dbt-core` integration in `rcm_mc_diligence/ingest/connector.py` (314 lines, per Report 0122). Sister to Reports 0025 (Anthropic), 0085 (rate_limit), 0102 (CMS data refresh), 0104 (webhooks dispatch), 0115 (CMS HCRIS).

## Findings

### Integration target

**dbt-core** = data-build-tool, the SQL transformation framework. Used by `rcm_mc_diligence/` to run dbt models against partner-supplied data warehouses (DuckDB / Snowflake / Postgres adapters per Report 0122 + 0136).

Pinned per `[diligence]` extras (Report 0101): `dbt-core>=1.10,<2.0`.

### Client code path

**Layer 1**: `rcm_mc_diligence/ingest/connector.py:200`:
```python
from dbt.cli.main import dbtRunner
```

**Layer 2**: `_dbt_invoke(...)` function at line 188-215:
```python
def _dbt_invoke(args, project_dir, profiles_dir, log_path,
                target_path=None, packages_install_path=None) -> _DbtInvokeResult:
    """Invoke dbt via its programmatic entrypoint."""
    from dbt.cli.main import dbtRunner
    full_args = [*args, "--project-dir", str(project_dir),
                 "--profiles-dir", str(profiles_dir),
                 "--log-path", str(log_path)]
    if target_path is not None:
        full_args += ["--target-path", str(target_path)]
    if packages_install_path is not None:
        full_args += ["--packages-install-path", str(packages_install_path)]
    runner = dbtRunner()
    result = runner.invoke(full_args)
    success = bool(getattr(result, "success", False))
    return _DbtInvokeResult(success=success, results=result, stdout="", stderr="")
```

**Programmatic mode** (NOT subprocess). Per docstring: "Programmatic mode returns a structured result we can introspect without parsing CLI output, which matters for reliability."

**Layer 3**: `_parse_run_results(...)` line 218+ reads `target/run_results.json` produced by dbt (per docstring lines 223-225: "We prefer the file on disk over `invoke_result.results` because the file format is stable across dbt versions; the Python object shape is not.").

### Error handling

- `runner.invoke(full_args)` returns a result object; **no try/except around it**.
- `success` defaults to False if `result.success` attribute missing.
- Inside `_parse_run_results`: `try: ... except (json.JSONDecodeError, FileNotFoundError):` — narrow catch.

**Per Report 0144 retry inventory**: NO RETRY. dbt-core invocation is single-shot. Cross-link MR802.

### Secret management

- `--profiles-dir` arg points to `profiles.yml` (which contains DB credentials per dbt convention).
- The `connectors/seekingchartis/profiles.example.yml` (per Report 0122) is the template.
- A real `profiles.yml` would contain database passwords / API keys.

**Cross-link Report 0122 MR699 medium**: if a real `profiles.yml` is committed accidentally, secrets leak. **`.gitignore` should explicitly cover `profiles.yml` (NOT `profiles.example.yml`).**

### dbt-core version compatibility

Per dbt-core CHANGELOG: programmatic API has been stable since ~1.5.0. Project pin `>=1.10,<2.0` covers 1.10+.

dbt-core CVEs: dbt has had occasional issues (jinja-template injection in v0.x; mostly resolved). Pin `>=1.10` avoids historical issues.

### Trust boundary

**dbt models execute SQL against the data warehouse.** The SQL is in `connectors/seekingchartis/models/input_layer/*.sql` (per Report 0122 — eligibility, medical_claim, pharmacy_claim).

**If a partner can override the project_dir or write SQL into the models/ directory, they get arbitrary SQL execution.** Per the architecture: project_dir is partner-supplied path. **Partner CAN write arbitrary SQL** if they have write access to the dbt project dir. Cross-link Report 0136 MR770 + Report 0137 MR777 path-traversal class.

**MR805 below.**

### Logging

`--log-path` flag set explicitly. dbt logs go to a file in the operator's output dir. **Cross-link Report 0024 logging cross-cut**: dbt is a separate log stream, NOT integrated with `rcm_mc.infra.logger`.

### Subcommand restrictions

Per docstring lines 196-198:
> "Flags like `--target-path` and `--packages-install-path` are only accepted by certain subcommands (`build`, `run`, `test`) — dbt-core 1.11's `deps` rejects them. Pass `None` to skip."

**Subtle dbt-core 1.11 behavior change documented inline.** Good defensive code.

### Importers / call sites

Per Report 0122: `connector.py` is one of 4 modules in `rcm_mc_diligence/ingest/`. `_dbt_invoke` likely called from `pipeline.py:run_ingest` (Report 0122).

### Integration patterns comparison

| Integration | Mode | Retries | Secrets | Audit |
|---|---|---|---|---|
| Anthropic API (Report 0025) | HTTP via `urllib` | (TBD) | env-var API key | logged |
| Webhooks dispatch (Report 0104) | HTTP via `urllib` | 3 with backoff | secret from DB plaintext (MR576 critical) | DB row |
| CMS download (Report 0115) | HTTP via `urllib` | 0 (MR647 high) | none (public) | log |
| **dbt-core (this)** | **programmatic API (in-process)** | **0** | **profiles.yml file** | **dbt log file** |

**4 different integration patterns, 4 different secret-management approaches, 3 different retry counts.** Cross-link Report 0144 MR800 (no shared retry helper).

### Cross-link Report 0136 pyarrow CVE risk

Per Report 0136: `pyarrow>=10.0` allows vulnerable versions; `dbt-duckdb` transitively depends on pyarrow (MR773). **The dbt invocation here pulls in the pyarrow vulnerability transitively.**

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR805** | **Partner can write arbitrary SQL into the dbt models/ directory** | If `project_dir` is partner-controlled (or copied from partner upload), they execute arbitrary SQL against the warehouse. **Trust-boundary violation.** | **High** |
| **MR806** | **No retry on `dbtRunner().invoke(...)`** | Single-shot. Transient warehouse hiccup → instant failure. Cross-link Report 0144 MR802. | Medium |
| **MR807** | **`profiles.yml` is the secret-bearing file** but `.gitignore` covers? Q1 below | If a partner accidentally commits `profiles.yml` (vs `profiles.example.yml`), credentials leak. | **High** |
| **MR808** | **dbt log stream NOT integrated with `rcm_mc.infra.logger`** | Cross-link Report 0024 + 0144. Operators must check 2 log locations on failure. | Low |
| **MR809** | **`success = bool(getattr(result, "success", False))`** uses defensive `getattr` | dbt-core API change (renaming `success` attr) silently produces `success=False` for ALL runs. **Defensive but masks API drift.** | Low |
| **MR810** | **dbt-core 1.11 subcommand-flag-rejection behavior documented inline only** | If dbt-core 2.x changes flag acceptance again, this module needs to track. Cross-link Report 0101 pin `<2.0`. | Low |

## Dependencies

- **Incoming:** `pipeline.py:run_ingest` likely (per Report 0122).
- **Outgoing:** dbt-core (programmatic), JSON file at `target/run_results.json`, partner-supplied `project_dir`/`profiles_dir`/`log_path`.

## Open questions / Unknowns

- **Q1.** Is `profiles.yml` in `.gitignore`? (Cross-link Report 0122 MR699 medium.)
- **Q2.** Does any test exercise the full dbt-invoke + parse-run-results path?
- **Q3.** Are there checks that the `project_dir` and `models/*.sql` are integrity-verified (e.g., signed checksums) before invocation?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0146** | CI/CD refresh (in flight). |
| **0147** | Read `.gitignore` and verify profiles.yml coverage (closes Q1). |

---

Report/Report-0145.md written.
