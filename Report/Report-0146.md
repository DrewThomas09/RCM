# Report 0146: Build / CI / CD — Pre-commit Hook Re-Audit

## Scope

Re-reads `.pre-commit-config.yaml` to close Report 0143 Q1 + Report 0116 Q4 (mypy in CI). Sister to Reports 0026, 0033, 0041, 0056 (pre-commit initial), 0086, 0101, 0116 (full workflow inventory), 0143 (`[dev]` extras).

## Findings

### Pre-commit hooks (4 repos + 1 local)

Per `.pre-commit-config.yaml`:

| Repo / Local | Hook | Args | Status |
|---|---|---|---|
| astral-sh/ruff-pre-commit v0.3.0 | `ruff` | `--fix` | linter (auto-fix on commit) |
| astral-sh/ruff-pre-commit v0.3.0 | `ruff-format` | (default) | formatter |
| **pre-commit/mirrors-mypy v1.8.0** | **mypy** | `--ignore-missing-imports`; additional_dependencies: pandas-stubs, types-PyYAML | type-checker |
| pre-commit/pre-commit-hooks v4.5.0 | trailing-whitespace | — | hygiene |
| pre-commit/pre-commit-hooks v4.5.0 | end-of-file-fixer | — | hygiene |
| pre-commit/pre-commit-hooks v4.5.0 | check-yaml | — | YAML parse-validate |
| pre-commit/pre-commit-hooks v4.5.0 | check-added-large-files | `--maxkb=500` | binary-bloat blocker |
| local | **phi-scan** | `python -m rcm_mc.compliance scan` | PHI regex scanner |

**8 hooks total.** Cross-link Report 0056 (initial pre-commit audit).

### CLOSURE — Report 0143 Q1 + Report 0116 Q4

> "Q1. Is mypy in `.pre-commit-config.yaml`?"

**YES** — `pre-commit/mirrors-mypy v1.8.0`. Cross-link Report 0143 was correct that mypy is "alive (pre-commit-only)."

> "Q4. Is `mypy>=1.5` actually invoked by pre-commit?"

**YES** — pinned at v1.8.0 in pre-commit. Cross-link Report 0101 pyproject `mypy>=1.5` — pre-commit version (v1.8.0) is compatible with pin. **Aligned.**

### CLOSURE — Report 0131 MR746 + Report 0144

> "MR746 high: No CI test asserts `configs/*.yaml` parses cleanly."

**Pre-commit `check-yaml` hook EXISTS.** Cross-correction to Report 0131 MR746: the YAML parse check IS configured. **Why didn't it catch `configs/playbook.yaml` MR744 critical?**

**Possible reasons**:
1. Pre-commit hooks aren't installed locally (`pre-commit install` not run).
2. Developer used `git commit --no-verify` to bypass.
3. `check-yaml` only checks YAML files in the staged set — if `playbook.yaml` was committed in a batch that errored on a higher-priority hook, check-yaml didn't run.
4. **Most likely**: pre-commit was added AFTER the broken `playbook.yaml` was committed (Apr 17 mtime per Report 0131); pre-commit didn't retroactively check.

**Cross-correction Report 0131 MR746 narrows**: the gap is **CI-side**, not config-side. CI doesn't run check-yaml on existing files. Pre-commit only checks newly-staged files.

**MR811 below.**

### CLOSURE — Report 0099 MR543 ruff F401

> "Why didn't ruff catch the 5 unused imports in `domain/custom_metrics.py`?"

**Pre-commit ruff has `--fix` arg** — would auto-fix. Either:
1. Pre-commit not installed locally (`pre-commit install`)
2. Developer bypassed via `--no-verify`
3. The unused imports were in a staged commit that errored elsewhere (didn't reach ruff)

**MR812 below.**

### `phi-scan` local hook (cross-link Report 0043)

Per `.pre-commit-config.yaml` line 28-32:
```yaml
- repo: local
  hooks:
    - id: phi-scan
      name: PHI pattern scanner
      entry: python -m rcm_mc.compliance scan
      language: system
      pass_filenames: true
      types: [text]
```

**Calls `python -m rcm_mc.compliance scan`** — Report 0043 audited `phi_scanner.py`. **HIPAA-ready PHI guardrail.**

### `check-added-large-files --maxkb=500`

**500KB max file size.** Cross-link Report 0130 (vendor/cms_medicare/ has many ~80-90KB PNG files — within limit). **Per-file 500KB blocks accidental large-binary commits.**

### Cross-link to Report 0116 CI workflows

Per Report 0116: `ci.yml` does NOT run pre-commit hooks. Only:
- `pytest` on 12 named files
- server smoke test

**Pre-commit is local-only enforcement.** A developer with `--no-verify` ships untyped/unlinted/PHI-bearing code.

### Hook version pins

| Hook | Pinned to |
|---|---|
| ruff-pre-commit | v0.3.0 |
| mirrors-mypy | v1.8.0 |
| pre-commit-hooks | v4.5.0 |

**All pinned to specific versions** (not floating). Good supply-chain discipline. Cross-link Report 0116 MR665 (deploy.yml uses `appleboy/ssh-action@v1.0.3` — same pattern).

### `mypy --ignore-missing-imports`

Per pyproject.toml (Report 0101): `mypy ignore_missing_imports = true`. Same flag also passed via `args:` in pre-commit. **Belt-and-braces redundancy** but consistent.

### Observation: 5 pre-commit-only quality gates that ARE NOT CI-enforced

| Gate | Local-only? |
|---|---|
| ruff lint | YES (per Report 0116 MR658) |
| ruff format | YES |
| mypy type-check | YES |
| trailing-whitespace / EOF / check-yaml | YES |
| phi-scan | YES |
| check-added-large-files | YES |

**ALL 8 quality gates are pre-commit-only. NONE runs in CI.** A `--no-verify` push to main lands without ANY of these gates.

### CLAUDE.md says

CLAUDE.md mentions pre-commit but doesn't specify CI vs local. Cross-link Report 0093 MR503 critical doc rot.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR811** | **Pre-commit `check-yaml` hook exists but didn't catch `configs/playbook.yaml` parse error (Report 0131 MR744 critical)** | Pre-commit only checks newly-staged files. The broken file was committed before pre-commit was installed OR via `--no-verify` OR existed before any commit reached it. **CI should also run YAML-parse checks.** | **High** |
| **MR812** | **Pre-commit `ruff` hook didn't catch 5 unused imports in `domain/custom_metrics.py` (Report 0099)** | Same root cause as MR811. Either pre-commit hooks not installed locally, OR `--no-verify` bypass, OR pre-existing commits. | Medium |
| **MR813** | **All 8 quality gates are pre-commit-only — none runs in CI** | Cross-link Report 0116 MR658 (no ruff/mypy in CI). A `git push --no-verify` ships unlinted/untyped code. | **High** |
| **MR814** | **Pre-commit hooks pinned to specific versions** | Good — supply-chain pinned. But version drift: v0.3.0 ruff is from late 2024; latest is ~v0.10+. Should refresh. | Low |
| **MR815** | **`mypy --ignore-missing-imports`** weakens type-checking for any 3rd-party without stubs | Cross-link Report 0101 MR554. duckdb, dbt-core, openpyxl, pyarrow all unstubbed → mypy skips them. Type errors in those interfaces are silent. | Medium |
| **MR816** | **`phi-scan` is the ONLY hipaa control on commit-time** | Cross-link Report 0043 phi_scanner. If the scanner has a false-negative pattern (per Report 0030 HIPAA review), PHI bypasses. Defense-in-depth gap. | Medium |

## Dependencies

- **Incoming:** every `git commit` if pre-commit installed. CI does NOT call pre-commit.
- **Outgoing:** PyPI for ruff/mypy/pre-commit-hooks, GitHub for repo URLs.

## Open questions / Unknowns

- **Q1.** Has every developer run `pre-commit install` locally? (Detectable via `.git/hooks/pre-commit` script presence.)
- **Q2.** Should CI add a `pre-commit run --all-files` step?
- **Q3.** When was pre-commit added vs Apr 17 (when `playbook.yaml` was last modified)?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0147** | Concrete remediation: add `pre-commit run --all-files` step to ci.yml. |
| **0148** | Verify Q3 — `git log .pre-commit-config.yaml` to find when pre-commit was added. |
| **0149** | Refresh hook versions (MR814). |

---

Report/Report-0146.md written.
