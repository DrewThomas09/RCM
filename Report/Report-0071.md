# Report 0071: Config Map — `RCM_MC/.pre-commit-config.yaml`

## Scope

Pre-commit config (43 lines). Sister to Report 0056.

## Findings

### Top-level shape

```yaml
repos:
  - repo: <url>
    rev: <pinned>
    hooks: [...]
```

Standard pre-commit format.

### Per-repo + per-hook

| Repo | rev | Hooks | Purpose |
|---|---|---|---|
| `astral-sh/ruff-pre-commit` | v0.3.0 | `ruff --fix`, `ruff-format` | Lint + format |
| `pre-commit/mirrors-mypy` | v1.8.0 | `mypy` (with `pandas-stubs, types-PyYAML`) | Type check |
| `pre-commit/pre-commit-hooks` | v4.5.0 | `trailing-whitespace`, `end-of-file-fixer`, `check-yaml`, `check-added-large-files` (max 500 KB) | Hygiene |
| `local` | — | `phi-scan` (entry: `python -m rcm_mc.compliance scan`) | PHI gate |

### Hook readers / consumers

`pre-commit run --all-files` is the canonical invocation. Each hook reads its own config keys:

| Key | Default | Reader |
|---|---|---|
| `ruff args [--fix]` | (default config from pyproject ruff section per Report 0003) | ruff binary |
| `mypy additional_dependencies` | `[pandas-stubs, types-PyYAML]` | mypy |
| `check-added-large-files args [--maxkb=500]` | 500 KB | pre-commit-hooks `check-added-large-files` |
| `phi-scan entry` | `python -m rcm_mc.compliance scan` | local entry — invokes `compliance/__main__.py` |
| `phi-scan types: [text]` | text only | pre-commit framework filters file types |
| `phi-scan pass_filenames: true` | passes staged filenames | pre-commit framework |

### Allowlist / bypass

`# phi-scan:allow` inline marker (per comments lines 39-44) — operator escape hatch.

### Cross-link

- Ruff config in `pyproject.toml:112-118` (Report 0003)
- mypy config in `pyproject.toml:120-126` (Report 0003)

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR443** | **Pin staleness** (cross-link MR409) | ruff v0.3.0, mypy v1.8.0, pre-commit-hooks v4.5.0 — all old. Update window. | Medium |
| **MR444** | **No CI re-run of pre-commit** (cross-link MR408) | Operator-side gate only. | **High** |

## Dependencies

- **Incoming:** developer commits.
- **Outgoing:** ruff, mypy, pre-commit-hooks framework, `python -m rcm_mc.compliance` entry.

## Open questions / Unknowns

- **Q1.** What does `python -m rcm_mc.compliance scan` actually do (full file-walk semantics)?

## Suggested follow-ups

| Iteration | Area |
|---|---|
| **0072** | Data flow trace (already requested). |

---

Report/Report-0071.md written.

