# Report 0208: Config Trace — `RCM_MC_PHI_MODE` (refresh + closure of Report 0028)

## Scope

Refreshes `RCM_MC_PHI_MODE` env-var trace per Report 0028 + Report 0127 MR720 (PHI write site found on `feat/ui-rework-v3`). Sister to Reports 0028, 0030, 0049, 0079, 0090, 0109, 0115, 0118, 0127, 0139, 0169, 0178.

## Findings

### Read sites (cumulative)

| Site | Source |
|---|---|
| `auth/auth.py` (Report 0028) | (TBD specific line) |
| `ui/_chartis_kit.py:63` (Report 0169) | `_os.environ.get("RCM_MC_PHI_MODE", "").strip().lower()` |
| `feat/ui-rework-v3` test fixtures (Report 0127 MR720) | grep `os.environ["RCM_MC_PHI_MODE"] = "disallowed"` |

### Write sites — UNUSUAL

Per Report 0127 MR720 high: `os.environ["RCM_MC_PHI_MODE"] = "disallowed"` on `feat/ui-rework-v3`. **Per Report 0028 trace claim**: PHI mode was read-only.

**Cross-corrected by Report 0127** (pre-merge). Likely a TEST FIXTURE (not production code). **Mutates `os.environ` for test isolation.** Cross-link Report 0090 MR499 (ServerConfig class-attribute mutation pattern).

### Default fallback

If unset → empty string `""` → falsy semantics → PHI mode is **disabled by default**.

Per CLAUDE.md "PHI mode": redaction is a feature flag. Off by default.

### Cross-link Report 0028 + 0030 PHI architecture

Per Report 0028 + 0030: PHI mode controls redaction in HTML reports + audit_events. **Disabled-by-default means PHI flows through unredacted unless operator opts in.**

**MR990 below** — defaults invert HIPAA-best-practice (PHI should be ALLOWED only after explicit opt-in to handle PHI; opposite of disallowed-by-default).

### Cross-link Report 0093 phi_scanner

Per Report 0043: `phi_scanner.py` is a regex scanner. Pre-commit hook (Report 0146 phi-scan local hook) enforces commit-time scan. **Two PHI-related controls**:
1. `RCM_MC_PHI_MODE` env-var (this trace)
2. `phi_scanner.py` regex scanner (commit-time)

**Different scopes** — env var controls runtime redaction; scanner controls commit-time leak prevention.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR990** | **`RCM_MC_PHI_MODE` defaults disabled — PHI flows unredacted unless operator opts in** | HIPAA best-practice: deny-by-default. Cross-link Report 0030 PHI architecture. **Should default to "redact" mode.** | **High** |
| **MR991** | **`feat/ui-rework-v3` writes to PHI env var** (Report 0127 MR720) — likely test fixture | If a production code path ever does `os.environ["RCM_MC_PHI_MODE"] = X`, it mutates global state. | (carried) |

## Dependencies

- **Incoming:** auth/auth.py, ui/_chartis_kit.py, test fixtures.
- **Outgoing:** os.environ.

## Open questions / Unknowns

- **Q1.** Does the production-deploy.yml set `RCM_MC_PHI_MODE` explicitly?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0209** | Commits digest (in flight). |

---

Report/Report-0208.md written.
