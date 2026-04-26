# Report 0138: Entry Point — `python seekingchartis.py` (5th entry surface)

## Scope

Traces the `python seekingchartis.py` launcher (84 lines) — entry surface #5 of 7+ (per Report 0130). Sister to Reports 0018 (rcm-mc serve), 0048 (python -m), 0078 (rcm-mc-diligence), 0102 (POST /api/data/refresh), 0108 (POST /api/login), 0113 (uvicorn rcm_mc.api:app).

## Findings

### Layer-by-layer trace

#### Layer 1 — Shell invocation

```bash
python seekingchartis.py [--port 9090] [--db my_portfolio.db] [--no-browser]
```

Per docstring (lines 4-7). Top-level Python script with shebang `#!/usr/bin/env python3` (line 1). NOT a console-script entry-point in pyproject (per Report 0086 + 0130 — separate from `rcm-mc` etc.).

#### Layer 2 — `if __name__ == "__main__"` (line 83-84)

```python
if __name__ == "__main__":
    main()
```

Standard idiom.

#### Layer 3 — `main()` (line 21-80)

**Step-by-step:**

| Step | Line | Action |
|---|---|---|
| 3.1 | 22-28 | argparse: `--port` (int, default 8080), `--db` (str, default `"seekingchartis.db"`), `--no-browser` (flag) |
| 3.2 | 31-32 | `os.chdir(script_dir)` — **changes process cwd to script's dir** |
| 3.3 | 34-36 | Add script_dir to `sys.path` if missing |
| 3.4 | 38-39 | Import `rcm_mc.__version__`, `rcm_mc.__product__`, `rcm_mc.server.build_server` |
| 3.5 | 43-64 | Print ASCII banner |
| 3.6 | 66 | `server, handler_cls = build_server(port=args.port, db_path=args.db)` |
| 3.7 | 68-72 | If `not no_browser`: spawn daemon thread that sleeps 300ms, then `webbrowser.open(url)` |
| 3.8 | 74-80 | `server.serve_forever()` with KeyboardInterrupt → `shutdown` + `server_close` |

#### Layer 4 — `build_server` (server.py, per Report 0018)

`build_server(port, db_path)` returns `(ThreadingHTTPServer, RCMHandler)`. Per Report 0018 + 0108 trace.

#### Layer 5 — request handling

`server.serve_forever()` enters dispatch loop. Per Reports 0102/0108: each request hits `RCMHandler.do_GET/do_POST` etc.

### NEW finding — different default DB path vs ServerConfig

| Source | Default DB |
|---|---|
| `ServerConfig.db_path` (Report 0090) | `~/.rcm_mc/portfolio.db` (or `$RCM_MC_DB`) |
| `pe_cli.py` (Report 0118) | `portfolio.db` (cwd) |
| `ui/sponsor_detail_page.py` (Report 0118 MR679) | `/tmp/rcm_mc.db` |
| **`seekingchartis.py` (this iteration)** | **`seekingchartis.db`** (cwd-relative) |

**5 different defaults for the database path.** Cross-link Report 0118 MR679 high — adds a 4th unique default. Pattern intensifies.

### `os.chdir(script_dir)` (line 32) — side effect

This launcher **mutates the process working directory** to the script's location. Other CLI entries (rcm-mc, python -m) typically respect the user's cwd.

**Implication**: Relative paths in args (e.g., `--db ./my.db`) resolve against the script's dir, not the user's. **Could surprise.** **MR781 below.**

### Banner ASCII art

Lines 43-64 — multi-line print with embedded URLs. Cosmetic. **No `os.environ.get` reads** (zero env-var dependencies — closes potential MR cross-link).

### `webbrowser.open(url)` (line 71)

After 300ms delay (line 70 `time.sleep(0.3)`), opens browser to `<url>/home`. Standard launcher pattern.

**`/home` route**: per Report 0130 references home page. Cross-link Report 0091 server.py routes (mostly unmapped).

### Importers

`grep "seekingchartis"` (per Report 0130): 9 references but NONE are Python imports of the module. **0 importers.** Standalone launcher.

### Cross-link to Report 0086 + 0130

Report 0086: 4 console scripts in pyproject (`rcm-mc`, `rcm-intake` broken, `rcm-lookup`, `rcm-mc-diligence`).
Report 0113: 1 ASGI app via uvicorn.
Report 0130: `seekingchartis.py` + `demo.py` as 5th + 6th entry surfaces.

**This iteration confirms `seekingchartis.py` is structurally an alternate to `rcm-mc serve`** — both call `build_server(port, db_path)`. The differences:
- argparse vs rcm-mc CLI
- Defaults: `:8080` + `seekingchartis.db` vs `~/.rcm_mc/portfolio.db`
- `os.chdir(script_dir)` (CRITICAL difference)
- Ascii banner + browser auto-open

### KeyboardInterrupt handling

Lines 74-80:
```python
try:
    server.serve_forever()
except KeyboardInterrupt:
    print("\nShutting down...")
    server.shutdown()
    server.server_close()
    print("Done.")
```

**Clean shutdown.** Cross-link Report 0103 MR729 (`JobRegistry.shutdown` not tested) — note: this is `HTTPServer.shutdown`, not job_queue. Different class.

### No env-var reads

`grep "os.environ"` in `seekingchartis.py`: **zero hits.** Pure argparse-driven.

### No CSRF / auth context

The script doesn't touch auth at startup — `build_server` is identical regardless of caller. Auth is per-request (Report 0108).

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR781** | **`os.chdir(script_dir)` (line 32) mutates process cwd** unexpectedly | Other entry surfaces respect user's cwd. Relative path args resolve differently here. Subtle UX surprise. | Medium |
| **MR782** | **5th distinct DB-path default** (`seekingchartis.db` cwd-relative) | Cross-link Report 0118 MR679 high — adds yet another inconsistent default. Now 5 different DB defaults across the project. | **High** |
| **MR783** | **`seekingchartis.py` is a top-level script not declared in `pyproject.toml [project.scripts]`** | Cross-link Report 0086 + 0101 + 0130 MR739. Distribution ships the file but no pip-installed binary points to it. Users must run `python seekingchartis.py` (knowing the path) vs `rcm-mc serve` (a binary). | Medium |
| **MR784** | **Hardcoded `7+` page URLs in the banner** (lines 54-59: `/home`, `/market-data/map`, `/news`, `/screen`, `/library`, `/api/docs`) | If routes are renamed in `feat/ui-rework-v3` (Report 0127 adds `/forgot`, `/app`), banner becomes misleading. | Low |
| **MR785** | **No env-var support in seekingchartis.py** — args only | Other entry surfaces support `RCM_MC_DB`/`RCM_MC_AUTH`/etc. (Report 0118 + 0090). This launcher is argparse-only. | Low |

## Dependencies

- **Incoming:** developer/end-user direct invocation; CLAUDE.md doesn't mention it explicitly (vs `demo.py` which IS in CLAUDE.md "Running" section per Report 0130).
- **Outgoing:** stdlib (argparse, os, sys, threading, time, webbrowser); `rcm_mc.__version__`, `rcm_mc.__product__`, `rcm_mc.server.build_server`.

## Open questions / Unknowns

- **Q1.** What's `rcm_mc.__product__`? A constant in `rcm_mc/__init__.py`?
- **Q2.** Does CI ever exercise `python seekingchartis.py` (e.g., smoke test with --no-browser)?
- **Q3.** Why the discrepancy in DB defaults — should they all converge to one value?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0139** | Env-var sweep on a fresh module (this iteration's task is in flight). |
| **0140** | Error-handling audit (next iteration's task). |
| **0141** | Verify `analysis_runs` FK status (Report 0118 MR678 / Report 0137 carried). |

---

Report/Report-0138.md written.
