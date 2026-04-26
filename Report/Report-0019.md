# Report 0019: Environment-Variable Audit — `rcm_mc/server.py`

## Scope

This report covers **every `os.environ` / `os.getenv` read inside `RCM_MC/rcm_mc/server.py`** on `origin/main` at commit `f3f7e7f`. For each var: where it's read, what default applies, what fails (or doesn't) if missing, evaluation timing, and security implications.

`server.py` was selected because it is the merge supersink (Report 0005) and the entry point for `rcm-mc serve` (Report 0018). The next-largest hotspot, `infra/notifications.py` (4 reads — SMTP_HOST/PORT/USER/PASS), is noted for context but reserved for a future iteration.

A whole-codebase inventory of unique env-var names is included at the end so readers can see the broader footprint.

Prior reports reviewed before writing: 0015-0018.

## Findings

### Sweep result for `server.py`

```bash
$ grep -nE "os\.environ|os\.getenv" RCM_MC/rcm_mc/server.py
96:    db_path: str = os.environ.get("RCM_MC_DB") or os.path.expanduser("~/.rcm_mc/portfolio.db")
1953:            home = (os.environ.get("RCM_MC_HOMEPAGE") or "").strip().lower()
3622:            _ai_on = bool(os.environ.get("ANTHROPIC_API_KEY"))
7569:                  or os.environ.get("RCM_MC_DASHBOARD", "").lower() == "v3")
16264:    auth_raw = auth or os.environ.get("RCM_MC_AUTH")
```

**5 distinct environment variables**, all read via `os.environ.get(...)`. None use `os.getenv` (functionally equivalent — both project conventions are `os.environ.get`). None of the 5 raise on missing.

### Per-variable detail

#### 1. `RCM_MC_DB` — database path override

| Field | Value |
|---|---|
| Read at | `server.py:96` |
| Context | `db_path: str = os.environ.get("RCM_MC_DB") or os.path.expanduser("~/.rcm_mc/portfolio.db")` |
| Type | string (filesystem path) |
| Default | `~/.rcm_mc/portfolio.db` (single-user laptop default) |
| Read scope | Class attribute on `ServerConfig` (line 87) |
| **Evaluation timing** | **At import time** (class definition body executes once when `server.py` is first imported). Subsequent changes to `RCM_MC_DB` after import do NOT affect new `ServerConfig()` instances. |
| Failure mode if missing | None — falls back to laptop default. |
| Override mechanism | `build_server(db_path=...)` (Report 0018 Stage 5a) overrides this at runtime via `RCMHandler.config.db_path = db_path` (line 16257). The CLI flag `--db` (line 16375) is the documented override path. |
| Used by | `RCMHandler.config.db_path` is read by every route handler that opens a `PortfolioStore`. |

**Branch-merge sensitivity:** Per Report 0007 MR47, `feature/workbench-corpus-polish` removes this entire env-var fallback (replaces the line with a plain `os.path.expanduser(...)` default). If that branch merges naively, **Heroku and Docker deployments break** because they rely on `RCM_MC_DB` to point inside a writable persistent volume.

#### 2. `RCM_MC_HOMEPAGE` — root-route redirect toggle

| Field | Value |
|---|---|
| Read at | `server.py:1953` |
| Context | `home = (os.environ.get("RCM_MC_HOMEPAGE") or "").strip().lower(); if home == "dashboard": return self._redirect("/dashboard")` |
| Type | string toggle |
| Default | `""` (empty) — unset means root `/` does NOT redirect |
| Read scope | Inside a request handler (per request) |
| **Evaluation timing** | **Per-request** — re-read every time the route fires. Live changes take effect on the next request. |
| Failure mode if missing | None — `/` serves the default page (no redirect). |
| Recognized values | Only `"dashboard"` (case-insensitive). Other values are no-ops. |
| Used by | The root `/` GET handler. |

**Subtle hazard:** values other than the literal `"dashboard"` silently no-op. A typo (`RCM_MC_HOMEPAGE=dashbaord`) doesn't error or warn — just doesn't redirect.

#### 3. `ANTHROPIC_API_KEY` — AI-feature presence flag

| Field | Value |
|---|---|
| Read at | `server.py:3622` |
| Context | `_ai_on = bool(os.environ.get("ANTHROPIC_API_KEY"))` |
| Type | boolean check (presence/absence — value content not validated) |
| Default | falsy (key absent) |
| Read scope | Inside a UI rendering function (per render) |
| **Evaluation timing** | **Per-render** — re-read on every dashboard card refresh. |
| Failure mode if missing | None — AI badge renders as "off" / unavailable. |
| Validation | **Truthy check only.** A non-empty string of *any* content turns the badge green — no API call to validate the key. Could be set to `"placeholder"` and the UI would falsely claim AI is on. |
| Security note | This is the only env var that holds a SECRET. Pre-merge: confirm no branch logs `os.environ.get("ANTHROPIC_API_KEY")` directly (would leak it into request logs). |

**Sister-pattern check:** The actual API call presumably happens inside `rcm_mc/ai/llm_client.py` (per Report 0005 the `.ai` subpackage exists). The badge truthy-check is just a UI gate; the actual call site likely re-reads the env or accepts the key as a parameter. Pre-merge sweep: any branch that adds a 6th `os.environ.get("ANTHROPIC_API_KEY")` site needs careful review for log-redaction.

#### 4. `RCM_MC_DASHBOARD` — dashboard v3 toggle

| Field | Value |
|---|---|
| Read at | `server.py:7569` |
| Context | `use_v3 = (bool(qs.get("v3")) or os.environ.get("RCM_MC_DASHBOARD", "").lower() == "v3")` |
| Type | string toggle |
| Default | `""` (empty) — unset = use legacy dashboard |
| Read scope | Per-request, inside the dashboard route handler |
| **Evaluation timing** | Per-request |
| Failure mode if missing | Legacy dashboard renders. |
| Recognized values | Only `"v3"` (case-insensitive). |
| Override mechanism | A query-string parameter `?v3=1` overrides the env-var (the `bool(qs.get("v3"))` clause precedes the env check). |

**Discovery:** there is a **dashboard v3** toggle. Pre-merge: confirm `feature/workbench-corpus-polish` (per Report 0007 — it deletes `dashboard_page.py` entirely) is compatible with this v3 path. If `dashboard_page.py` is the legacy and `dashboard_v3.py` is the new one (per Report 0015 BLE001 hotspots — `dashboard_v3.py` had 7 BLE001 sites), the deletion-on-polish-branch may be the intended retirement.

#### 5. `RCM_MC_AUTH` — HTTP Basic credentials

| Field | Value |
|---|---|
| Read at | `server.py:16264` |
| Context | `auth_raw = auth or os.environ.get("RCM_MC_AUTH"); if auth_raw and ":" in auth_raw: ...` |
| Type | `user:pass` string |
| Default | None (auth disabled) |
| Read scope | Inside `build_server` (per Report 0018 Stage 5b) |
| **Evaluation timing** | **At server-build time** (once per `build_server` call, normally once per process). |
| Failure mode if missing | Auth is disabled — every request goes through without credentials. |
| Validation | Requires a `:` to be present; partitions on first `:`. **No validation that user/pass are non-empty**, no minimum length, no character restrictions. `RCM_MC_AUTH=:` gives `auth_user=""`, `auth_pass=""`. |
| Override mechanism | The `--auth USER:PASS` CLI flag takes precedence (line 16264 reads `auth or os.environ.get(...)`). |
| Security note | Stored in `RCMHandler.config.auth_user` / `auth_pass` as plaintext class-singleton attributes. Memory-readable from any code in the same process. |

**Subtle behavior:** the env var is consumed inside `build_server`, not on import. So tests that call `build_server(auth=None)` after setting the env var get the env-var value. Tests that call `build_server(auth="explicit:value")` win over the env var. Tests that re-call `build_server(auth=None)` after a prior call with explicit auth correctly reset to None then re-read the env var (per the explicit reset at lines 16262-16263; Report 0018).

### Evaluation-timing summary

| Var | Timing | Why it matters |
|---|---|---|
| `RCM_MC_DB` | **Import-time** (class default) | Changing it after import doesn't affect new ServerConfig()s. The CLI flag overrides this anyway. |
| `RCM_MC_HOMEPAGE` | Per-request | Live config — change takes effect immediately. |
| `ANTHROPIC_API_KEY` | Per-render | Live config; truthy-only check is fragile. |
| `RCM_MC_DASHBOARD` | Per-request | Live; used as fallback to a query-string toggle. |
| `RCM_MC_AUTH` | At `build_server` time | Lives until next `build_server` call. Tests that toggle this between calls work as expected. |

### Failure modes if missing

**All 5 vars fall back gracefully** — none raise. No `KeyError`, no `RuntimeError`, no `sys.exit`. The fallbacks are:

- `RCM_MC_DB` → laptop default `~/.rcm_mc/portfolio.db`.
- `RCM_MC_HOMEPAGE` → no redirect, default landing.
- `ANTHROPIC_API_KEY` → AI badge "off".
- `RCM_MC_DASHBOARD` → legacy dashboard.
- `RCM_MC_AUTH` → auth disabled.

This is consistent with the project's "single-user laptop default; production deploy can opt in" stance (per CLAUDE.md and the Azure VM deploy plan in `RCM_MC/deploy/`).

### Whole-codebase env-var inventory (for context)

`grep -rn "os\.environ\|os\.getenv" RCM_MC/rcm_mc/` returns 35 reads. Unique var names by frequency:

| Var | Count | Primary use |
|---|---:|---|
| `RCM_MC_DB` | **4** | DB path (server.py + 3 sister modules — likely portfolio_cmd.py, cli.py, similar) |
| `ANTHROPIC_API_KEY` | **4** | LLM presence (server.py + ai/* modules) |
| `USERPROFILE` | 2 | Windows home-dir resolution (cross-platform helpers) |
| `RCM_MC_PHI_MODE` | **2** | PHI-mode toggle — interesting; not yet mapped |
| `HOME` | 2 | Unix home-dir resolution |
| `USER` | 1 | Unix user (likely audit-log enrichment) |
| `TERM` | 1 | Terminal capability (CLI color rendering) |
| `SMTP_HOST` | 1 | Email notification server (`infra/notifications.py:84`) |
| `SMTP_PORT` | 1 | Email port (`infra/notifications.py:88`, default 587) |
| `SMTP_USER` | 1 | Email user (`infra/notifications.py:89`) |
| `SMTP_PASS` | 1 | Email password (`infra/notifications.py:90`) |
| `RCM_MC_SESSION_IDLE_MINUTES` | 1 | Session-timeout override (auth subsystem) |
| `RCM_MC_POS_CSV` | 1 | Point-of-service CSV override |
| `RCM_MC_NO_PORTFOLIO` | 1 | Disable portfolio features |
| `RCM_MC_HRRP_CSV` | 1 | HRRP CSV path override |
| `RCM_MC_HOMEPAGE` | 1 | Root redirect (this report) |
| `RCM_MC_GENERAL_CSV` | 1 | General CSV path override |
| `RCM_MC_AUTH` | 1 | HTTP Basic creds (this report) |
| `NO_COLOR` | 1 | Disable terminal color (cross-tool standard) |
| `FORCE_COLOR` | 1 | Force terminal color |

**20 distinct env vars across the project.** Of those, 11 use the `RCM_MC_*` prefix; 9 use upstream/standard names (HOME, USER, TERM, SMTP_*, NO_COLOR, FORCE_COLOR, USERPROFILE, ANTHROPIC_API_KEY).

**HIGH-PRIORITY discovery:** `RCM_MC_PHI_MODE` (2 reads, not yet mapped). PHI = Protected Health Information. A toggle for HIPAA-mode is a security-relevant flag worth its own future iteration.

## Merge risks flagged

| ID | Risk | Detail | Severity |
|---|---|---|---|
| **MR142** | **`RCM_MC_DB` removed by `feature/workbench-corpus-polish`** | Per Report 0007 MR47, that branch replaces `os.environ.get("RCM_MC_DB") or os.path.expanduser(...)` with `os.path.expanduser(...)` plain. **Heroku / Docker / Azure VM deploys that depend on `RCM_MC_DB` to point at a persistent volume break silently** if that branch merges. | **Critical** (cross-link MR47) |
| **MR143** | **`ANTHROPIC_API_KEY` truthy-check is fragile** | `bool(os.environ.get("ANTHROPIC_API_KEY"))` accepts ANY non-empty string. `ANTHROPIC_API_KEY=placeholder` shows AI as "on" while every API call fails downstream. **Recommend: validate format (starts with `sk-ant-`?) at startup, log warning if malformed.** | Medium |
| **MR144** | **`RCM_MC_AUTH=:` (empty user, empty pass) is accepted** | Line 16265 `if auth_raw and ":" in auth_raw:` only checks the colon is present. `RCM_MC_AUTH=:` partitions to `("", "", "")` — auth enabled but with empty creds. Probably accepts any login. **Recommend: reject empty user/pass, log error.** | **High** |
| **MR145** | **`ServerConfig.db_path` evaluated at import time** | The `RCM_MC_DB` env var is captured into the class default at import. Tests that change the env var between imports must reload the module — or call `build_server(db_path=...)` to override. **Pre-merge: any test fixture that patches `os.environ["RCM_MC_DB"]` after `import rcm_mc.server` is buggy.** | Medium |
| **MR146** | **No env-var documentation** | None of the 5 vars in `server.py` are documented in `RCM_MC/README.md` or in `RCM_MC/readME/*`. The CLI `--help` output covers `--db` and `--auth` but not the env-var equivalents (lines 16375, 16385 mention them tangentially). **Operators deploying via Heroku/Docker have no canonical doc** — they must read source. | **High** |
| **MR147** | **`RCM_MC_PHI_MODE` is unmapped** | 2 reads detected; semantically a HIPAA-mode flag. **Security-relevant** — its semantics matter (does it strip PHI from logs? gate routes? prevent exports?). HIGH-PRIORITY follow-up. | **High** |
| **MR148** | **SMTP credentials in `infra/notifications.py`** | 4 reads (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`). Password is read into `password = os.environ.get("SMTP_PASS") or ""` (line 90). If logged, leaks. Pre-merge: cross-branch sweep for `print(password)` or `logger.debug(password)` patterns. | **High** |
| **MR149** | **No `RCM_MC_*` env-var registry / single source of truth** | The 11 RCM_MC_* vars are scattered across files. No central docs file, no validation function, no `_validate_env()` boot check. **A typo in deployment scripts produces silent fallback behavior; no health-check surfaces it.** | Medium |
| **MR150** | **`RCM_MC_DASHBOARD=v3` toggle interacts with `dashboard_page.py` deletion** | `feature/workbench-corpus-polish` deletes `dashboard_page.py` (Report 0007 MR46). If v3 is in `dashboard_v3.py` (which has BLE001 hotspots per Report 0015), the deletion may be the intentional retirement of legacy. **But if both branches are in flight**, the v3 toggle's behavior is uncertain. | Medium |
| **MR151** | **`RCM_MC_HOMEPAGE` typos silently no-op** | Only `"dashboard"` is recognized. `RCM_MC_HOMEPAGE=Dashboard` works (case-insensitive); `RCM_MC_HOMEPAGE=dashbaord` (typo) silently fails. **Recommend: log a warning on unrecognized non-empty values.** | Low |

## Dependencies

- **Incoming (who depends on these env vars):** deploy stack (`RCM_MC/deploy/Dockerfile`, `RCM_MC/deploy/rcm-mc.service`, `RCM_MC/deploy/vm_setup.sh` — content not yet read), `legacy/heroku/requirements.txt`-driven Heroku deploys (per Report 0016), test fixtures, operators running `rcm-mc serve` from shells.
- **Outgoing (what these env vars depend on):** Python `os.environ` (a dict-like view of the process environment); the underlying shell / launcher / systemd / Docker that sets them.

## Open questions / Unknowns

- **Q1 (this report).** What does `RCM_MC_PHI_MODE` actually do? 2 reads detected; security-relevant. Where is it consumed?
- **Q2.** Is there a centralized env-var registry, validation function, or doc file anywhere I haven't found? `grep -rn "RCM_MC_" RCM_MC/readME/` would tell us.
- **Q3.** Does `feature/workbench-corpus-polish`'s removal of `RCM_MC_DB` extend to other `RCM_MC_*` env vars, or is it a targeted Heroku-removal?
- **Q4.** What format does `ANTHROPIC_API_KEY` need to follow? Anthropic keys start with `sk-ant-` per public conventions — the codebase does not enforce this.
- **Q5.** Are SMTP credentials ever logged (debug logging of email-send failures could leak password)?
- **Q6.** What's the actual behavior when `RCM_MC_AUTH=:` (empty creds, valid colon)? Smoke test would reveal.
- **Q7.** Is the dashboard v3 toggle a transient feature flag (eventually removed) or a permanent A/B switch?
- **Q8.** Why is `RCM_MC_DB` evaluated at import time as a class default rather than at instance time? Is there a deliberate caching reason or is it a footgun?

## Suggested follow-ups

| Iteration | Proposed area | Why |
|---|---|---|
| **0020** | **`RCM_MC_PHI_MODE` audit** — find both reads + understand the toggle's behavior. | Resolves Q1 / MR147. PHI mode is security-relevant. |
| **0021** | **`infra/notifications.py` env-var audit + log-redaction sweep** for SMTP_PASS and ANTHROPIC_API_KEY. | Resolves MR148 + part of MR143. Verify no leak vectors. |
| **0022** | **Read the deploy stack** (`RCM_MC/deploy/Dockerfile`, `docker-compose.yml`, `rcm-mc.service`, `vm_setup.sh`) — what env vars are set there? | Tells us the production-side env-var contract. Cross-checks with this report's 5 server.py reads. |
| **0023** | **Cross-branch env-var sweep** — does any ahead-of-main branch add or remove env-var reads? | Catch MR142 / MR150 cross-branch interactions. |
| **0024** | **Walk `cli.py`** (1,252 lines) — owed since Report 0003. | Closes the broken `rcm-intake` entry-point loop and the CLI surface. |
| **0025** | **Read `server.py:91 ServerConfig` end-to-end** — owed from Report 0018 Q2. | Companion to MR145. |

---

Report/Report-0019.md written. Next iteration should: locate and read both `RCM_MC_PHI_MODE` env-var sites — it's a security-relevant HIPAA-mode toggle that hasn't been mapped, and understanding its semantics is required before any deployment audit can call PHI-handling complete (closes Q1 / MR147 here).

