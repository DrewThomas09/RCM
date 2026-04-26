# Report 0018: Entry Point Trace — `rcm-mc serve`

## Scope

This report covers the **`rcm-mc serve` CLI command** entry-point trace on `origin/main` at commit `f3f7e7f`. The command starts the local HTTP server that backs the entire web UI; it is the user-facing entry point partners actually run day-to-day per `RCM_MC/README.md` ("rcm-mc serve --db p.db --port 8080").

The trace covers 5 layers from console invocation through `ThreadingHTTPServer.serve_forever()`. Per-request handler logic and route-level dispatch are reserved for future iterations (Report 0005 partially covered the route surface).

Prior reports reviewed before writing: 0014-0017.

## Findings

### Stage 0 — User invocation

```
$ rcm-mc serve --port 8080 --db portfolio.db --outdir output/ --auth user:pass
```

Possible flags (per argparse declaration at `RCM_MC/rcm_mc/server.py:16367-16389`):

- `--port` (default 8765)
- `--host` (default `127.0.0.1` — local only)
- `--db` (default `~/.rcm_mc/portfolio.db`)
- `--outdir` (optional, served at `/outputs/*`)
- `--title` (dashboard title; default `"RCM Portfolio"`)
- `--open` (open dashboard in browser at boot)
- `--auth USER:PASS` (HTTP Basic; also read from `RCM_MC_AUTH` env var)

### Stage 1 — Console-script dispatch

`RCM_MC/pyproject.toml:69`:

```
rcm-mc = "rcm_mc.cli:main"
```

Setuptools generates a small `rcm-mc` console script in `<env>/bin/` that does:

```python
from rcm_mc.cli import main
sys.exit(main())
```

This was confirmed in Report 0003 as the only one of the 4 declared scripts that resolves cleanly (the others — `rcm-intake`, `rcm-lookup`, `rcm-mc-diligence` — have either broken paths or thin shims).

### Stage 2 — CLI top-level dispatch

`RCM_MC/rcm_mc/cli.py:1252` defines:

```python
def main(argv: Optional[list[str]] = None) -> int:
```

Inside `main`, the subcommand router (lines 1297-1305) dispatches:

```python
if first == "serve":
    from .server import main as serve_main      # cli.py:1300
    return serve_main(argv[1:], prog="rcm-mc serve")   # cli.py:1301
```

Note: the `from .server import main` is **lazy** — `server.py` (16,398 lines per Report 0005) is not imported at CLI startup unless the user invokes `serve`. This keeps `rcm-mc --help` and other subcommands fast.

### Stage 3 — Subcommand argparse

`RCM_MC/rcm_mc/server.py:16364`:

```python
def main(argv: Optional[list] = None, prog: str = "rcm-mc serve") -> int:
    import argparse
    ap = argparse.ArgumentParser(prog=prog, description="Start a local web server ...")
    ap.add_argument("--port", type=int, default=8765, ...)
    ap.add_argument("--host", default="127.0.0.1", ...)
    ap.add_argument("--db", default=None, metavar="PATH", ...)
    ap.add_argument("--outdir", default=None, metavar="DIR", ...)
    ap.add_argument("--title", default="RCM Portfolio", ...)
    ap.add_argument("--open", dest="open_browser", action="store_true", ...)
    ap.add_argument("--auth", default=None, metavar="USER:PASS", ...)
    args = ap.parse_args(argv)
    run_server(port=args.port, host=args.host, db_path=args.db,
               outdir=args.outdir, title=args.title,
               open_browser=args.open_browser, auth=args.auth)
    return 0
```

Argparse runs and immediately delegates to `run_server` at line 16392. The function returns 0 unconditionally — error handling is not at this layer.

### Stage 4 — `run_server`: boot orchestrator

`server.py:16309-16359`:

```python
def run_server(*, port=8765, db_path=None, outdir=None,
               title="RCM Portfolio", host="127.0.0.1",
               open_browser=False, auth=None) -> None:
    """Start the server and block until Ctrl+C."""
    import time as _boot_time
    _boot_start = _boot_time.perf_counter()
    server, _ = build_server(   # Stage 5 below
        port=port, db_path=db_path, outdir=outdir, title=title, host=host,
        auth=auth,
    )
    url = f"http://{host}:{port}/"
    from . import __version__

    # Lookup deal count for the boot banner
    deal_count = 0
    try:
        _s = PortfolioStore(RCMHandler.config.db_path)
        deal_count = len(_s.list_deals())
    except Exception:                  # ← BLE001 swallow
        pass

    _boot_ms = round((_boot_time.perf_counter() - _boot_start) * 1000)
    sys.stdout.write(...)             # banner: version, URL, db, deals, outdir, auth, API docs, boot ms

    if open_browser:
        threading.Thread(target=lambda: webbrowser.open(url), daemon=True).start()

    try:
        server.serve_forever()        # block until Ctrl+C
    except KeyboardInterrupt:
        sys.stdout.write("\nShutting down...\n")
    finally:
        server.server_close()
```

Responsibilities:

- Time the boot for the banner (`_boot_ms`).
- Look up deal count to print "deals: N" in the banner — wrapped in a bare `except Exception` (Report 0015 BLE001 pattern; rationale: "never block boot on banner data lookup").
- Print the banner to stdout (URL, db_path, deal count, outdir, auth, API-docs URL, boot time, "Ctrl+C to stop").
- Optionally launch a browser tab in a daemon thread.
- Call `server.serve_forever()` — **blocks until Ctrl+C**.
- On KeyboardInterrupt: clean shutdown.

### Stage 5 — `build_server`: construct the server (line 16241)

`server.py:16241-16306`:

```python
def build_server(*, port=8765, db_path=None, outdir=None,
                 title="RCM Portfolio", host="127.0.0.1",
                 auth=None) -> Tuple[ThreadingHTTPServer, RCMHandler]:
    """Construct (but don't start) the server + configured handler."""

    # 5a. Mutate the class-level config singleton on RCMHandler
    if db_path:
        RCMHandler.config.db_path = db_path
    RCMHandler.config.outdir = os.path.abspath(outdir) if outdir else None
    RCMHandler.config.title = title

    # 5b. Reset auth (so test re-runs don't leak credentials)
    RCMHandler.config.auth_user = None
    RCMHandler.config.auth_pass = None
    auth_raw = auth or os.environ.get("RCM_MC_AUTH")
    if auth_raw and ":" in auth_raw:
        u, _, p = auth_raw.partition(":")
        RCMHandler.config.auth_user = u
        RCMHandler.config.auth_pass = p

    # 5c. Allow socket re-use (TIME_WAIT recovery)
    socketserver.TCPServer.allow_reuse_address = True

    # 5d. Boot-time hygiene: cleanup expired sessions
    try:
        from .auth.auth import cleanup_expired_sessions
        cleanup_expired_sessions(PortfolioStore(RCMHandler.config.db_path))
    except Exception:  # noqa: BLE001 — never block server boot on hygiene
        pass

    # 5e. Boot-time: apply pending DB migrations
    try:
        from .infra.migrations import run_pending
        run_pending(PortfolioStore(RCMHandler.config.db_path))
    except Exception:  # noqa: BLE001 — never block server boot
        pass

    # 5f. Reset metric counters
    RCMHandler._request_counter = 0
    RCMHandler._response_times = []
    RCMHandler._error_count = 0

    # 5g. Record start time for uptime card
    RCMHandler._process_started_at = _dt_boot.now(_tz_boot.utc)

    # 5h. Self-test: verify DB is readable
    try:
        _st = PortfolioStore(RCMHandler.config.db_path)
        with _st.connect() as _con:
            _con.execute("SELECT 1").fetchone()
    except Exception as _exc:
        sys.stderr.write(f"[rcm-mc] WARNING: DB self-test failed: {_exc}\n")
        sys.stderr.flush()

    # 5i. Construct the server
    server = ThreadingHTTPServer((host, port), RCMHandler)
    server.timeout = 300
    RCMHandler.timeout = 120
    return server, RCMHandler
```

### Stage 6 — Per-request dispatch (only briefly)

After `serve_forever()` is called, every TCP connection spawns a thread that runs `RCMHandler` (a `BaseHTTPRequestHandler` subclass). For each request:

- `do_GET` / `do_POST` parse `self.path` and dispatch to a route handler.
- The route handler imports its dependencies lazily (per Report 0005: 974 in-function imports across `server.py`).
- The handler returns HTML or JSON via `_send_html` / `_send_json` / similar helpers.

Per-request mechanics are out of scope for this report.

### Trace summary diagram

```
shell:   $ rcm-mc serve --port 8080
            │
   Stage 1 │   pyproject.toml:69  rcm-mc = "rcm_mc.cli:main"
            ▼
   Stage 2 │   cli.py:1252  main(argv)
            │   cli.py:1299  if first == "serve":
            │   cli.py:1300  from .server import main as serve_main
            ▼
   Stage 3 │   server.py:16364  main(argv, prog="rcm-mc serve")
            │      ↓ argparse: --port --host --db --outdir --title --open --auth
            ▼
   Stage 4 │   server.py:16309  run_server(...)
            │      ↓ time boot
            │      ↓ build_server(...)
            ▼
   Stage 5 │   server.py:16241  build_server(...)
            │      ↓ 5a-5h: config singleton, auth, socket, sessions, migrations,
            │              counters, uptime, DB self-test
            │      ↓ 5i:    ThreadingHTTPServer((host, port), RCMHandler)
            │     ←  return  (server, RCMHandler)
            ▼
   Stage 4'│   run_server  prints boot banner, opens browser thread (optional)
            ▼
   Stage 6 │   server.serve_forever()  — blocks
            │      ↓ per-request: RCMHandler.do_GET / do_POST → route dispatch
            ▼
            (Ctrl+C: KeyboardInterrupt → server.server_close())
```

### Notable behaviors

| Behavior | Site | Rationale |
|---|---|---|
| Lazy import of `server.py` | `cli.py:1300` (`from .server import main`) | 16K-line server module not imported unless user invokes `serve`. Keeps `rcm-mc --help` fast. |
| `RCMHandler.config` is class-level | `build_server` lines 16257-16268 | Singleton mutated at boot; per-request handlers all see the same `config`. **Concurrency note:** test runs that boot multiple servers in-process must reset config between tests. Lines 16262-16263 reset auth specifically. |
| Boot-time DB self-test | lines 16294-16301 | Validates DB connectivity but does NOT block boot if it fails — only writes a warning to stderr. **A broken DB lets the server start and fail per-request instead of failing fast.** |
| Boot-time session hygiene | lines 16277-16280 | `cleanup_expired_sessions` runs once at boot. The auth subsystem also has a `JOIN`-based runtime filter so this is a hygiene optimization, not a correctness requirement. |
| Boot-time migrations | lines 16282-16285 | `run_pending` from `infra/migrations.py` (Report 0017). Failures are silently swallowed via BLE001. |
| `server.timeout = 300`, `RCMHandler.timeout = 120` | lines 16304-16305 | Different timeouts on server (connection) vs handler (request). 300s connection, 120s request. **Mismatched values worth verifying.** |
| `RCM_MC_AUTH` env-var fallback | line 16264 | Auth credentials can come from env. Per Report 0007 MR47, `feature/workbench-corpus-polish` removes the similar `RCM_MC_DB` env-var fallback — pre-merge: verify same branch doesn't also touch `RCM_MC_AUTH`. |
| 4 BLE001 swallows on the critical boot path | lines 16279, 16284, 16298, 16332 | Defensive; comments justify each ("never block boot on hygiene", etc.) — but they do mean a broken auth/migrations/DB layer fails-soft into a running-but-broken server. |

## Merge risks flagged

| ID | Risk | Detail | Severity |
|---|---|---|---|
| **MR132** | **`build_server` signature has 7 keyword-only parameters** | Adding/renaming a kwarg breaks `run_server` (line 16322), test fixtures (`build_server(port=8000, db_path=...)` is the canonical test setup pattern across many test files), and any branch that calls it. **Pre-merge: any signature change to `build_server` must be coordinated across `run_server`, all test fixtures, and `RCMHandler.config` defaults.** | **High** |
| **MR133** | **`RCMHandler.config` is a class-level singleton mutated by `build_server`** | If a feature branch swaps the class-singleton model for instance-level config (a reasonable refactor), every existing test that introspects `RCMHandler.config.db_path` breaks. The class-level model is also a thread-safety hazard if two builds were called concurrently (forbidden in tests but not statically prevented). | **High** |
| **MR134** | **DB self-test at lines 16294-16301 fails-open** | `SELECT 1` on broken DB just writes a stderr warning — server still starts. **A schema-drift breakage (e.g. missing column from a partial migration)** would not surface here; would surface on first user request. Recommend: **fail-fast on missing-column or migration-required errors**, not just on connectivity. | Medium |
| **MR135** | **`RCM_MC_AUTH` env-var fallback** | Combined with Report 0007 MR47 (workbench-corpus-polish removes `RCM_MC_DB` env var support), if any branch removes RCM_MC_AUTH support too, ops-side env-var-driven auth scripts break silently. **Pre-merge: cross-branch sweep for env-var removals.** | Medium |
| **MR136** | **`server.timeout = 300` vs `RCMHandler.timeout = 120`** | Mismatched values. Connection timeout > request timeout means a slow client can hold a thread for 5 minutes after a 2-minute request times out. Worth aligning. | Low |
| **MR137** | **4 BLE001 swallows on the boot path** | Lines 16279, 16284, 16298, 16332. Each individually has a defensive rationale; cumulatively they mean **a broken auth/migration/DB layer can let the server start without surfacing the issue**. **Pre-merge: a future cleanup should distinguish "expected misconfiguration" from "real failure" and fail-fast on the latter.** | Medium |
| **MR138** | **`server.serve_forever()` is single-process, no worker pool** | `ThreadingHTTPServer` spawns a thread per request; one Python process. Performance ceiling at ~CPU-bound contention. Default `threading` GIL applies. Per CLAUDE.md (Report 0002): "Single-machine deployment. No clustering, no Postgres path." This is by design; flagged for awareness only. | Low |
| **MR139** | **Boot banner reads deal count via `len(_s.list_deals())`** | `list_deals()` per Report 0008 is a moderately-tested method; a schema change that breaks it would prevent the banner from printing the deal count (caught by line 16332's BLE001). Banner shows "deals: 0" instead of the real number. | Low |
| **MR140** | **`build_server` mutates global state** | The function modifies `RCMHandler.config.*`, `socketserver.TCPServer.allow_reuse_address`, `RCMHandler._request_counter`, `RCMHandler._response_times`, `RCMHandler._error_count`, `RCMHandler._process_started_at`. **All mutations are class-level singletons.** Calling `build_server` twice in the same Python process leaves state from the first call partially overwritten. Test fixtures must reset between runs — line 16262-16263 (auth reset) is a partial reset; not all state is reset. | Medium |
| **MR141** | **Lazy import `from .server import main` at `cli.py:1300` is the entry-point fragility point** | If `server.py`'s top-level imports fail (e.g. a feature branch adds a buggy module-level import), `rcm-mc serve` fails at this line — but `rcm-mc analysis`, `rcm-mc data`, etc. still work. **Easy to ship a broken `serve` without anyone noticing in CI** unless CI exercises the serve subcommand. | Medium |

## Dependencies

- **Incoming (who invokes `rcm-mc serve`):** users via shell; `RCM_MC/scripts/run_all.sh` and `run_everything.sh` (per Report 0002 — not yet read in detail); the Azure VM deploy systemd unit `RCM_MC/deploy/rcm-mc.service` (per Report 0002); CI smoke tests likely.
- **Outgoing (what `serve` depends on):** `rcm_mc.cli:main`, `rcm_mc.server:main`, `rcm_mc.server:run_server`, `rcm_mc.server:build_server`, `rcm_mc.server:RCMHandler`, `rcm_mc.portfolio.store:PortfolioStore`, `rcm_mc.auth.auth:cleanup_expired_sessions`, `rcm_mc.infra.migrations:run_pending`, stdlib (`socketserver`, `http.server`, `threading`, `webbrowser`, `argparse`).

## Open questions / Unknowns

- **Q1 (this report).** Does `RCMHandler.config` survive across multiple `build_server` calls in the same process correctly? Specifically: do non-auth fields (e.g. `db_path` if not provided in the second call) leak from the first build?
- **Q2.** What is the actual contents of `RCMHandler.config` (the dataclass on line 91 per Report 0007)? Need to enumerate every field. The `dataclass` shape is the contract every test relies on.
- **Q3.** Why is connection timeout (300s) higher than request timeout (120s)? Should they align? Is one the worker idle-keep-alive and the other request-deadline?
- **Q4.** Do all other rcm-mc subcommands (`pe`, `portfolio`, `analysis`, `data`) follow the same lazy-import pattern at `cli.py:1295-1305`, or do some import their server-side dependencies eagerly?
- **Q5.** Is there a way to invoke `rcm-mc serve` programmatically without going through `argparse`? `run_server(...)` looks intended for that, but it's an implementation detail.
- **Q6.** Does any branch on origin add a new flag to `rcm-mc serve` (e.g. `--workers`, `--ssl-cert`)? Cross-branch sweep needed.
- **Q7.** What's the API surface exposed at `/api/docs` (line 16345 banner text claims it exists)? Per Report 0003, there's no FastAPI in the core deps — the OpenAPI doc must be generated some other way.

## Suggested follow-ups

| Iteration | Proposed area | Why |
|---|---|---|
| **0019** | **Read `server.py:91 ServerConfig` dataclass** end-to-end. | Resolves Q2 — the contract every test depends on. |
| **0020** | **Read `auth/auth.py:cleanup_expired_sessions`** end-to-end. | Stage 5d depends on it; not yet mapped. Auth subsystem is unmapped overall. |
| **0021** | **Read `portfolio/store.py:connect()` (lines 84-108)** end-to-end. | Owed since Report 0017 — verify WAL / busy_timeout / foreign_keys=ON. Stage 5h's `_st.connect()` depends on it. |
| **0022** | **Sample a route handler** — e.g. `GET /health` or `GET /` — and trace the per-request anatomy. | The Stage 6 layer of this trace; complements this report. |
| **0023** | **Trace `rcm-mc analysis <deal_id>`** end-to-end. | Sister CLI command; exercises packet builder. Different code path. |
| **0024** | **Cross-branch sweep for new `--*` flags on `rcm-mc serve`.** | Resolves Q6. |
| **0025** | **Audit `RCMHandler.config` field-by-field** (the singleton — what fields exist, who reads each). | Companion to Q2 + MR132 + MR133. |

---

Report/Report-0018.md written. Next iteration should: read `server.py:91 ServerConfig` dataclass end-to-end to enumerate every field RCMHandler.config carries — closes Q2 here and is the contract every test depends on (cross-cutting risk for any signature change in `build_server` or any feature branch that adds/renames fields).

