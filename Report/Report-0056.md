# Report 0056: Build/CI/CD — `.pre-commit-config.yaml`

## Scope

Pre-commit hooks at `RCM_MC/.pre-commit-config.yaml` (43 lines per Report 0002). Sister to Report 0026 (.github/workflows/).

## Findings

### Hooks (4 repos × multiple hooks)

| Repo | Hooks | Notes |
|---|---|---|
| `astral-sh/ruff-pre-commit@v0.3.0` | `ruff --fix`, `ruff-format` | Lint + format. **v0.3.0 pinned** — older release of the ruff hook (latest is ~v0.5+ as of audit time). |
| `pre-commit/mirrors-mypy@v1.8.0` | `mypy` with `pandas-stubs, types-PyYAML` | Type check on commit. Adds runtime stubs as additional_dependencies. |
| `pre-commit/pre-commit-hooks@v4.5.0` | `trailing-whitespace`, `end-of-file-fixer`, `check-yaml`, `check-added-large-files` (max 500 KB) | Standard hygiene. |
| **`local`** | **`phi-scan`** | `entry: python -m rcm_mc.compliance scan`. **The PHI scanner from Report 0043 IS wired here.** |

### HIGH-PRIORITY DISCOVERY: `phi-scan` is wired via pre-commit

Per `.pre-commit-config.yaml:34-44`:

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

**Refines Report 0028 MR250 + Report 0043's "phi_scanner is unwired" finding.** Per Report 0030, the docs explicitly position phi_scanner as a pre-commit DLP tool; this YAML is the wiring. **Pre-commit gates new commits against PHI patterns.** Runtime PHI handling is still unenforced (per Report 0028), but the developer-side guardrail exists.

### Inline-bypass mechanism

Comment block at lines 39-44:

> "Staged test fixtures / example data may intentionally contain synthetic PHI-shaped tokens — the scanner already tolerates kpi_truth's H6-P000 style IDs. If a commit needs to land text with genuine PHI-shaped content, redact or add an inline `# phi-scan:allow` marker and drop the hit into the exclusion list."

So there's a `# phi-scan:allow` escape hatch. **Effective gate** with documented bypass.

### Pin discipline

| Hook | Pin | Latest (~2026) | Status |
|---|---|---|---|
| ruff-pre-commit | v0.3.0 | ~v0.5+ | **Stale** |
| mirrors-mypy | v1.8.0 | ~v1.11+ | Mid-stale |
| pre-commit-hooks | v4.5.0 | v4.6+ | Slightly behind |

Pins prevent surprise breakage; updates lag.

### What's NOT in pre-commit

- No `bandit` (security linter)
- No `pip-audit`
- No `commitizen` (commit-message linter)
- No `pytest` (would slow commits significantly)

### Run frequency

Hooks fire on `git commit` if pre-commit is installed locally. **Operator-side; not enforced server-side** — commits via GitHub UI or non-pre-commit installations bypass entirely.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR408** | **Pre-commit hooks operator-side only** | A contributor without `pre-commit install` can commit PHI / unformatted code. CI must re-run all hooks server-side. **CI doesn't (per Report 0026)** — only pytest. | **High** |
| **MR409** | **`ruff` v0.3.0 pin is stale** | Newer ruff has additional rules + bug fixes. Update window. | Medium |
| **MR410** | **No `bandit` / `pip-audit` / security linter** | Cross-link Report 0026 MR236 — no security scanning anywhere. | Medium |
| **MR411** | **`phi-scan` runs on commit, not on push** | Force-push or `--no-verify` bypasses. **Bypass-able.** | Medium |
| **MR412** | **Refines Report 0028 MR250: phi_scanner IS wired (pre-commit), just not runtime** | The HIPAA contract is technically met for the dev-side gate. Updates the severity of MR250 (banner overpromises but pre-commit catches). | (advisory) |

## Dependencies

- **Incoming:** every contributor running `git commit` with pre-commit installed.
- **Outgoing:** ruff, mypy, pre-commit-hooks repo (3 third-party + 1 local hook).

## Open questions / Unknowns

- **Q1.** Does CI run `pre-commit run --all-files`? Per Report 0026's ci.yml read, no — only specific pytest paths.
- **Q2.** What does `python -m rcm_mc.compliance scan` actually do (the entry point)?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0057** | Schema/type inventory (already requested). |
| **0058** | Config value trace (already requested). |

---

Report/Report-0056.md written. Next iteration should: schema/type inventory on `analysis/packet.py` `DealAnalysisPacket` (the load-bearing dataclass per CLAUDE.md, never schema-audited per Reports 0004/0027).

