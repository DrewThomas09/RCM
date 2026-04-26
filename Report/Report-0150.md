# Report 0150: Follow-up — Closes Report 0145 Q1 (`profiles.yml` gitignore status)

## Scope

Reads `RCM_MC/.gitignore` (66+ lines) + repo-root `.gitignore` to resolve Report 0145 Q1 (dbt profiles.yml secret-leak risk) + Report 0122 MR699 (medium). Sister to Reports 0001 (initial), 0122 (rcm_mc_diligence inventory), 0145 (dbt integration).

## Findings

### CLOSURE: Report 0145 Q1 + Report 0122 MR699

**`profiles.yml` (verbatim filename) is NOT in any `.gitignore`.** What IS:

| Pattern | Source | Coverage |
|---|---|---|
| `dbt_profiles/` | `RCM_MC/.gitignore` | DIRECTORY-level only — would catch `<repo>/dbt_profiles/profiles.yml` |
| `*.pem` | `RCM_MC/.gitignore` line 56 | covers PEM-format keys |
| `.env`, `.env.local` | `RCM_MC/.gitignore` line 54-55 | env-var files |

**`profiles.yml` placed in `rcm_mc_diligence/connectors/seekingchartis/profiles.yml` is NOT gitignored.** Per Report 0122: only `profiles.example.yml` ships intentionally. If a developer accidentally commits a real `profiles.yml` there, **dbt credentials leak.**

**MR699 medium CONFIRMED + escalates to MR-829 high** (escalation because the audit verifies the gap is real).

### Secret-pattern coverage gap

Looking at typical secret-bearing filenames:

| Pattern | In gitignore? | Risk if missed |
|---|---|---|
| `.env`, `.env.local` | YES | clean |
| `*.pem` | YES | clean |
| `*.key` | NO | TLS/JWT keys leak |
| `*.pfx` | NO | Windows certs |
| `id_rsa`, `id_ed25519` | NO | SSH private keys |
| `*.p12` | NO | client certs |
| `profiles.yml` | NO (only dbt_profiles/) | dbt credentials |
| `secrets.yml` | NO | generic |
| `credentials.json` | NO | OAuth |
| `api_key.txt` | NO | bare API key |
| `azure.conf` | NO | Azure creds |

**8+ common secret-file patterns NOT in gitignore.** **MR830 below.**

### What IS well-covered

| Category | Patterns |
|---|---|
| Build artifacts | `__pycache__/`, `build/`, `dist/`, `*.egg-info/` |
| Test/coverage | `.pytest_cache/`, `.coverage`, `.mypy_cache/`, `.ruff_cache/` |
| OS junk | `.DS_Store`, `Thumbs.db`, `.Rhistory` |
| Editor | `.vscode/`, `.idea/`, `*.swp` |
| Run artifacts | `outputs/`, `outputs_*/`, `*.sqlite`, `*.duckdb`, `report.html`, `report.pptx`, `summary.csv`, `simulations.csv`, `provenance.json`, etc. |
| dbt | `dbt_packages/`, `dbt_target/`, `dbt_logs/`, `dbt_profiles/`, `package-lock.yml` |
| Plots | `*.png` |

**Run-artifact coverage is strong.** dbt-specific patterns are present. Secrets-coverage is partial.

### Cross-link Report 0130 (vendor/cms_medicare 102MB)

Per Report 0130: `vendor/cms_medicare/` contains 100MB+ of PNG plots. The `RCM_MC/.gitignore` `*.png` rule does NOT apply to repo-root `vendor/` directory (different gitignore scopes). **Vendored content bypasses the run-artifact ignore.** Acceptable per project intent.

### Cross-link Report 0136 pyarrow + Report 0137 path-traversal

Both flagged user-uploaded file risks. **`.gitignore` doesn't help with runtime file ingestion**, only commit-time leaks. **Different threat models** — neither MR770 nor MR777 is mitigated by gitignore changes.

### Pre-commit `phi-scan` hook (cross-link Report 0146)

Per `.pre-commit-config.yaml`: `python -m rcm_mc.compliance scan` runs on staged files. **Catches PHI patterns** (SSN, DOB, MRN, NPI, etc.) but NOT generic API keys / passwords / dbt profiles.

**Defense layers**:
1. `.gitignore` — partial (covers .env, *.pem)
2. pre-commit phi-scan — covers PHI not secrets
3. CI YAML-parse check (per Report 0146) — doesn't run on existing files
4. NO CI-side secret-scan (e.g., gitleaks, detect-secrets) — **missing**

**MR831 below.**

### Two-tier `.gitignore`

| File | Scope |
|---|---|
| `<repo-root>/.gitignore` | top-level repo (includes `vendor/`) |
| `RCM_MC/.gitignore` | RCM_MC/ subtree |

**Patterns in subtree-gitignore don't apply to parent.** Standard git behavior; worth noting for navigation.

### Closing related questions

| Report | Question | Status |
|---|---|---|
| Report 0145 Q1 | profiles.yml gitignored? | **NO — closure** |
| Report 0122 MR699 medium | profiles.yml leak risk | **CONFIRMED + escalated** |
| Report 0136 (pyarrow user-input) | unrelated | (not closed by this) |
| Report 0137 MR777 (path traversal) | unrelated | (not closed by this) |

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR829** | **`profiles.yml` (verbatim) NOT in `.gitignore`** — if committed inside `rcm_mc_diligence/connectors/seekingchartis/`, dbt credentials leak | Cross-correction Report 0145 Q1 closure. Concrete fix: add `**/profiles.yml` and `!**/profiles.example.yml` to `RCM_MC/.gitignore`. | **High** |
| **MR830** | **8+ common secret-bearing patterns NOT in `.gitignore`**: `*.key`, `*.pfx`, `id_rsa`, `id_ed25519`, `secrets.yml`, `credentials.json`, `api_key.txt`, `azure.conf` | Each individually low-prob; collectively gap. **Recommend adding a `# Secrets` section to gitignore.** | Medium |
| **MR831** | **No CI-side secret-scanner** (gitleaks, detect-secrets, trufflehog) | Combined with MR813 (all gates pre-commit-only): a `--no-verify` push of a real `profiles.yml` lands without ANY check. | **High** |
| **MR832** | **Two-tier gitignore (root + RCM_MC/) has scope ambiguity** | Patterns in `RCM_MC/.gitignore` don't apply to `vendor/` (different scope). Onboarding gap. | Low |
| **MR699-CLOSED** | Report 0122 MR699 confirmed and escalated to MR829. | (closure + escalation) |

## Dependencies

- **Incoming:** every `git commit` operation; `git status` filtering.
- **Outgoing:** none.

## Open questions / Unknowns

- **Q1.** Is `pre-commit run --all-files` part of CI, OR does CI rely on individual hook invocations? Cross-link Report 0146 MR813.
- **Q2.** Has any historical commit ever touched a real `profiles.yml`? (`git log --all -p -- "**/profiles.yml" | head` — not run.)
- **Q3.** Is there a value in adopting `gitleaks` for CI?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0151** | 150+1 meta-survey (multiple-of-30 rhythm slipped — could do at 0151 since 0150 was a follow-up). |
| **0152** | Concrete bug-fix PR: add secret patterns to `.gitignore` + integrate `gitleaks` (closes MR829, MR830, MR831). |
| **0153** | Read `cli.py` head (1,252 lines, 14+ iterations owed). |

---

Report/Report-0150.md written.
Next iteration should: 150-report meta-survey (rhythm +1) — refresh Report 0121's 120-report inventory.
