# Report 0027: Schema Inventory — `ServerConfig` Class

## Scope

This report covers the **`ServerConfig` class** at `RCM_MC/rcm_mc/server.py:87` on `origin/main` at commit `f3f7e7f`. Documents every field, its type, default, evaluation timing, validators, and every site where instances are constructed or fields are accessed. The schema-level audit was owed since Report 0018 (Q2) and is referenced by Reports 0019 (env-var capture) and 0026 (CI smoke test).

`ServerConfig` was selected because:

- It is the **runtime contract** for the HTTP server (Report 0018 Stage 5).
- It carries the env-var-driven defaults audited in Report 0019.
- It is mutated by `build_server` and read by every request handler — single-mutation, multi-read pattern.
- It is **not** a `@dataclass` despite being shaped like one — that's a notable deviation worth pinning.

Prior reports reviewed before writing: 0023-0026.

## Findings

### Class definition (server.py:85-105, 21 lines)

```python
# ── Configuration container ────────────────────────────────────────────────

class ServerConfig:
    """Runtime config threaded through the handler via class attribute.

    Using a class attribute keeps the handler constructor compatible with
    ``BaseHTTPRequestHandler`` (which is invoked by the server, not us),
    without globals. Write once at ``build_server``; read many in handlers.
    """
    # Default respects $RCM_MC_DB (Heroku / Docker path) before falling back
    # to the single-user-laptop default under ~/.rcm_mc/.
    db_path: str = os.environ.get("RCM_MC_DB") or os.path.expanduser(
        "~/.rcm_mc/portfolio.db")
    outdir: Optional[str] = None      # If set, /outputs/* serves from here
    title: str = "RCM Portfolio"
    # B89: optional HTTP Basic credentials. If None, auth is disabled.
    # When the env-var ``RCM_MC_AUTH`` is set as ``user:pass``, build_server
    # copies it here and every request must carry matching Basic auth.
    auth_user: Optional[str] = None
    auth_pass: Optional[str] = None
```

**Critical structural fact: this is a plain `class`, NOT a `@dataclass`.**

Consequence: the 5 lines `db_path: str = ...`, `outdir: Optional[str] = None`, etc. are **class-level attributes** evaluated once at class-definition time (when `server.py` is imported). They are NOT instance defaults applied per `ServerConfig()` call. Mutation via `instance.db_path = ...` shadows the class attribute on that instance.

Every line annotated with `: <type>` is a type annotation but not a runtime check — Python does not validate types at assignment time without explicit code (e.g. `__post_init__`, `pydantic.validator`, etc.). Since this class is plain (no `@dataclass`, no `pydantic`), **no validation happens anywhere**.

### Field-by-field inventory

| Field | Annotated type | Default | Evaluation timing | Validator |
|---|---|---|---|---|
| `db_path` | `str` | `os.environ.get("RCM_MC_DB") or os.path.expanduser("~/.rcm_mc/portfolio.db")` | **Class-definition time** (once at import) | None |
| `outdir` | `Optional[str]` | `None` | Class-definition | None |
| `title` | `str` | `"RCM Portfolio"` | Class-definition | None |
| `auth_user` | `Optional[str]` | `None` | Class-definition | None |
| `auth_pass` | `Optional[str]` | `None` | Class-definition | None |

**5 fields. Zero runtime validators.**

#### Per-field deep dive

##### `db_path: str`

- Default expression evaluated at module import: `os.environ.get("RCM_MC_DB") or os.path.expanduser("~/.rcm_mc/portfolio.db")`.
- If `RCM_MC_DB` is set at import time, it wins. Else: laptop default.
- Mutated via `RCMHandler.config.db_path = db_path` at `server.py:16257` (inside `build_server`) per Report 0018.
- **References across `rcm_mc/`: 192 sites** — by far the most-touched config field.
- Cross-link Report 0019 MR142: `feature/workbench-corpus-polish` removes the env-var fallback. Cross-link Report 0019 MR145: import-time evaluation is a footgun for tests that patch the env var after import.

##### `outdir: Optional[str]`

- Default `None`. Mutated via `RCMHandler.config.outdir = os.path.abspath(outdir) if outdir else None` at line 16258.
- Used to enable the `/outputs/*` static-file route. When `None`, that route returns 404.
- **References: 8 sites.**

##### `title: str`

- Default `"RCM Portfolio"`. Cosmetic — appears as the dashboard `<title>` and breadcrumb header.
- Mutated at line 16259 from the `--title` CLI flag (per Report 0018).
- **References: 3 sites.**

##### `auth_user: Optional[str]`

- Default `None`. **None = auth disabled.**
- Set by `build_server` (lines 16262-16268) from either the `--auth USER:PASS` flag or the `RCM_MC_AUTH` env var (Report 0019 MR144).
- **References: 12 sites** — distributed across the request-auth-gate handlers (`server.py:1668, 1681, 1685, 1709`).

##### `auth_pass: Optional[str]`

- Default `None`. Stored in plaintext memory.
- Set by `build_server` lines 16263, 16268.
- Compared with `_h.compare_digest(pw, self.config.auth_pass or "")` at line 1683 — **constant-time comparison**, good.
- **References: 4 sites.**

### Instantiation sites

`grep -rn "ServerConfig(" RCM_MC/rcm_mc/ | grep -v __pycache__`:

| Site | Context |
|---|---|
| `server.py:1402` | `config: ServerConfig = ServerConfig()` — the **class-level attribute on `RCMHandler`**, instantiated once at module import. |

**There is exactly ONE production `ServerConfig()` call.** It is the `RCMHandler.config` class-singleton that all per-request handlers reference via `self.config.*` (since `BaseHTTPRequestHandler` doesn't accept extra constructor args).

Test sites (per `grep -rn "ServerConfig" RCM_MC/tests/`):

| Site | Context |
|---|---|
| `tests/test_comparable_export.py:31` | `from rcm_mc.server import RCMHandler, ServerConfig` |
| `tests/test_comparable_export.py:40` | `cfg = ServerConfig()` — test-only fresh instantiation |
| `tests/test_web_production_readiness.py:5, 31` | References (likely a docstring + test of the env-var capture) |

### Field-access frequency (cross-cuts)

`grep -rn "config\.<field>" RCM_MC/rcm_mc/`:

| Field | Total reference sites |
|---|---:|
| `config.db_path` | **192** |
| `config.auth_user` | 12 |
| `config.outdir` | 8 |
| `config.auth_pass` | 4 |
| `config.title` | 3 |

**`db_path` is by far the most-touched config field** — every database operation in any route, every store instantiation, every migration check. A signature change to `db_path` ripples to 192 sites.

### Mutation sites

The contract per the docstring: **"Write once at `build_server`; read many in handlers."** Verified.

Write sites (all in `server.py`):

| Line | Mutation | Caller |
|---|---|---|
| 16257 | `RCMHandler.config.db_path = db_path` | `build_server` |
| 16258 | `RCMHandler.config.outdir = ...` | `build_server` |
| 16259 | `RCMHandler.config.title = title` | `build_server` |
| 16262 | `RCMHandler.config.auth_user = None` | `build_server` (reset) |
| 16263 | `RCMHandler.config.auth_pass = None` | `build_server` (reset) |
| 16267 | `RCMHandler.config.auth_user = u` | `build_server` |
| 16268 | `RCMHandler.config.auth_pass = p` | `build_server` |

**7 mutation lines, all inside one function (`build_server`).** No per-request mutation; no other module mutates these fields. Single-writer contract holds.

Read sites: 219 total (192 + 12 + 8 + 4 + 3) across the codebase. Concentrated in `server.py` (the request handlers).

### Subtle invariants

- `db_path` evaluated at **import time**, not per `ServerConfig()` call — the import-time `RCM_MC_DB` capture is permanent for the process. (Cross-link Report 0019 MR145.)
- `auth_user` + `auth_pass` are **always reset before re-applying** in `build_server` (lines 16262-16263) — defensive against test-leak-credentials scenarios.
- All 5 fields use Python's truthy semantics in conditional reads: `if self.config.auth_user is not None` (line 1668) — explicit None-check, not truthy. Empty-string `auth_user = ""` would pass the `is not None` check but fail the `compare_digest` check. **`auth_user = ""` enables auth gates but no login can succeed.** (Cross-link Report 0021 MR144.)

### Non-fields — what `ServerConfig` does NOT carry

The `RCMHandler` class has additional state set in `build_server`:

- `RCMHandler._request_counter` (line 16286)
- `RCMHandler._response_times` (line 16287)
- `RCMHandler._error_count` (line 16288)
- `RCMHandler._process_started_at` (line 16291)
- `RCMHandler.timeout = 120` (line 16305)

These are class-level attributes on `RCMHandler` itself (NOT inside `ServerConfig`). The split is somewhat arbitrary:

- `ServerConfig` holds **user-supplied / declarative** state (db, outdir, title, auth).
- `RCMHandler.<state>` holds **runtime / observability** state (counters, timeouts).

A future refactor could merge them into a single config struct. **Pre-merge:** any branch that adds a new "config" field needs to choose which side to put it on; inconsistency is a maintainability risk.

## Merge risks flagged

| ID | Risk | Detail | Severity |
|---|---|---|---|
| **MR238** | **`ServerConfig` is NOT a `@dataclass`** | The 5 lines look dataclass-shaped but are plain class attributes. Adding `@dataclass` would change semantics: defaults become per-instance, `__init__` accepts kwargs, `__eq__` becomes structural. Tests that rely on identity (`config is RCMHandler.config`) would still work, but `cfg = ServerConfig(db_path=...)` semantics would change. **Pre-merge: any branch adding `@dataclass` decorator must verify all 219 read sites still work.** | Medium |
| **MR239** | **`db_path` evaluated at import time** | (Cross-link Report 0019 MR145.) Tests that patch `os.environ["RCM_MC_DB"]` after `import rcm_mc.server` see the import-time value, not the patched value. Need `importlib.reload` to refresh. | **High** for test reliability |
| **MR240** | **`auth_user = ""` (empty string) bypasses the `is not None` check but fails `compare_digest`** | Auth is "enabled" (line 1668 evaluates True) but no login can succeed. **Pre-merge: any branch that sets auth via env var with empty values needs explicit-empty-rejection.** Cross-link Report 0021 MR144. | **High** |
| **MR241** | **No runtime validation of any field** | A branch that assigns `RCMHandler.config.db_path = 12345` (an int instead of a path string) succeeds silently, then crashes downstream when `PortfolioStore(int)` opens a path. Recommend: type-check via `@dataclass(frozen=False)` + `__post_init__` validators. | Medium |
| **MR242** | **`db_path` is read by 192 sites — wide blast radius for any signature change** | Adding a 6th config field is cheap (one line). Renaming `db_path` is a 192-site refactor. | **High** |
| **MR243** | **Class-level attribute model means `RCMHandler.config` is shared across handler instances** | Per Report 0018 — this is the documented design. But concurrent calls to `build_server` (e.g. in tests with `pytest-xdist`) would race on `RCMHandler.config.db_path = ...`. **Pre-merge: any test that uses parallelism must use a per-test ServerConfig instance, not the singleton.** | Medium |
| **MR244** | **`auth_pass` stored in plaintext memory** | (Cross-link Report 0021 — passwords-in-memory pattern.) Anyone with debugger / repr / dump access reads plaintext. Acceptable for local-deploy threat model; flagged for any remote-deploy branch. | Medium |
| **MR245** | **`outdir = None` silently disables `/outputs/*`** | A branch that misconfigures `outdir` (e.g. forgets `--outdir`) doesn't error — just silently 404s requests. Recommend: log warning at `build_server` if `outdir is None and any output_*.html exists in cwd`. | Low |
| **MR246** | **Adding a 6th field requires editing both the class definition and `build_server`'s mutation block** | A field added without the corresponding mutation in `build_server` keeps the class default forever. A field mutated in `build_server` but not declared in `ServerConfig` raises AttributeError. Two-place edit. | Medium |
| **MR247** | **`title` field has only 3 references — possibly under-utilized** | Set at boot but might not propagate to all rendered pages. UI sweep needed. | Low |
| **MR248** | **No `__repr__` on `ServerConfig`** | A debug `print(RCMHandler.config)` prints `<rcm_mc.server.ServerConfig object at 0x...>` — useless. Recommend: add `__repr__` or convert to `@dataclass` (which auto-generates one). | Low |
| **MR249** | **`tests/test_comparable_export.py:40` instantiates a fresh `ServerConfig()` independent of the singleton** | Tests can create instances. If a future field has a side-effect at instantiation (e.g. opening a file), each `ServerConfig()` call triggers it — silent test pollution. Currently no side-effects, but potential hazard. | Low |

## Dependencies

- **Incoming:** `RCMHandler.config` (class-level instance, line 1402), every request handler's `self.config.*` (219 sites), `build_server` (7 mutation lines), 2 test files.
- **Outgoing:** stdlib `os` (for env var + path expansion), Python typing (`Optional[str]`).

## Open questions / Unknowns

- **Q1 (this report).** Was `ServerConfig` deliberately not a `@dataclass`, or is it a historical artifact? `git log -p server.py | grep -A2 "class ServerConfig"` would show.
- **Q2.** Why is `auth_user = ""` semantically different from `auth_user = None`? The codebase treats `None` as "disabled" but `""` as "enabled with empty user" — likely unintended.
- **Q3.** Are any feature branches adding new fields to `ServerConfig`? Cross-branch sweep needed.
- **Q4.** What's the test-side behavior when `tests/test_comparable_export.py:40` `cfg = ServerConfig()` mutates fields, then later tests run with the singleton? Any cross-test pollution?
- **Q5.** Does `tests/test_web_production_readiness.py:31` actually verify `db_path` respects `RCM_MC_DB` at import time?
- **Q6.** Should `outdir` reads also handle `Path` objects in addition to `str`? Currently the type annotation is `Optional[str]`; some callers may pass `Path`.
- **Q7.** Why does `RCMHandler` carry `_request_counter`, `_response_times`, etc. as class-level state instead of inside `ServerConfig`? Refactor opportunity.

## Suggested follow-ups

| Iteration | Proposed area | Why |
|---|---|---|
| **0028** | **Audit `analysis/packet.py` `DealAnalysisPacket` dataclass** — the much larger schema (1,283 lines per Report 0004). | The load-bearing invariant per CLAUDE.md. |
| **0029** | **Read `tests/test_web_production_readiness.py`** — verifies env-var capture per MR239. | Resolves Q5. |
| **0030** | **Read `tests/test_comparable_export.py`** — only test that uses `ServerConfig()` directly. | Resolves Q4. |
| **0031** | **Audit `RCMHandler` class-level state** (`_request_counter`, `_response_times`, `_error_count`, `_process_started_at`, `timeout`) — sister observability state. | Resolves Q7. |
| **0032** | **Cross-branch sweep** — does any ahead-of-main branch add a 6th `ServerConfig` field? | Resolves Q3 / MR246. |
| **0033** | **Audit `RCM_MC/deploy/Dockerfile` + `docker-compose.yml`** — owed since Report 0023 / 0026. | Closes deploy stack picture. |

---

Report/Report-0027.md written. Next iteration should: audit `RCM_MC/deploy/Dockerfile` + `RCM_MC/deploy/docker-compose.yml` end-to-end — this is the third-time-deferred follow-up (Reports 0023 Q1 / 0026 / 0027) and resolves whether `pip install -e ".[diligence]"` runs in production, which extras are present, what env vars get set, and whether `RCM_MC_DB` / `RCM_MC_AUTH` are wired into the container.

