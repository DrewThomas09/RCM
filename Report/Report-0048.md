# Report 0048: Entry Point Trace — `python -m rcm_mc`

## Scope

Documents the `python -m rcm_mc` entry point on `origin/main` at commit `f3f7e7f`. This is the production entry-point used by the Dockerfile (per Report 0033 line 27: `ENTRYPOINT ["python", "-m", "rcm_mc", "serve"]`). Sister to Report 0018 (`rcm-mc serve` console-script trace).

Prior reports reviewed: 0044-0047.

## Findings

### Stage 0 — invocation

```
$ python -m rcm_mc serve --port 8080 --host 0.0.0.0
```

Runs in the Dockerfile (per Report 0033 + Report 0019).

### Stage 1 — Python's `-m` resolution

`python -m rcm_mc` runs `RCM_MC/rcm_mc/__main__.py`. Per PEP 338 and Python's `runpy.run_module`, this is equivalent to `python <path>/__main__.py` with `__name__` set to `"__main__"`.

### Stage 2 — `__main__.py` (15 lines)

```python
"""Allow ``python -m rcm_mc`` to invoke the top-level CLI dispatcher.

Mirrors ``rcm-mc`` (the console-script entry point). Useful when the venv
isn't on PATH, or when scripting from inside the package.
"""
from __future__ import annotations
import sys
from .cli import main

if __name__ == "__main__":
    sys.exit(main() or 0)
```

| Line | Action |
|---|---|
| 1-4 | Module docstring explains the purpose |
| 7 | `from .cli import main` — relative import of `cli.py:main` |
| 11 | `if __name__ == "__main__":` — only runs when invoked via `python -m` |
| 12 | `sys.exit(main() or 0)` — passes `argv[1:]` (implicitly via argparse default) and returns exit code |

**The whole entry point is 15 lines.**

### Stage 3 — `cli.py:main(argv=None)` (line 1252 per Report 0018)

`cli.py:main` accepts `argv` via argparse, then dispatches based on the first arg:

```python
if first == "serve":
    from .server import main as serve_main      # cli.py:1300
    return serve_main(argv[1:], prog="rcm-mc serve")
```

(Per Report 0018 Stage 2.) For `python -m rcm_mc serve ...`, this dispatches to `server.py:main`.

**Both entry paths converge at this dispatcher** — `rcm-mc` (console-script) and `python -m rcm_mc` (module-form) both go through `cli.py:main`.

### Stage 4 — `server.py:main` argparse (line 16364 per Report 0018)

Same as Report 0018 Stage 3.

### Stage 5+ — same as Report 0018 (build_server → run_server → ThreadingHTTPServer.serve_forever)

The remaining 5 stages match Report 0018 exactly (the `python -m` form is identical to the console-script form past `cli.py:main`).

### Comparison vs Report 0018 (`rcm-mc serve` console-script)

| Aspect | `rcm-mc` (console-script) | `python -m rcm_mc` |
|---|---|---|
| Entry mechanism | Setuptools-generated `bin/rcm-mc` script | Python's `-m` runpy invocation |
| Entry point | `rcm_mc.cli:main` (via pyproject.toml:69) | `rcm_mc/__main__.py` line 11 |
| First file executed | `<venv>/bin/rcm-mc` (auto-generated) | `RCM_MC/rcm_mc/__main__.py` |
| Arguments | argv from shell | argv from shell |
| Final dispatcher | `cli.py:main` | `cli.py:main` |
| Dependency on `pip install` | YES — needs the console-script generated at install | NO — works as long as `rcm_mc` is importable |

**Production deploys use `python -m rcm_mc serve` per the Dockerfile** because it sidesteps console-script generation issues (per Report 0033 MR300). Specifically — the broken `rcm-intake = "rcm_mc.intake:main"` (Report 0003 MR14) exists in pyproject; running `pip install -e .` may attempt to generate that broken script and either error or generate a half-working entry. **`-m` form is robust to broken entry-point declarations.**

### Why this entry point exists

The module docstring at `__main__.py:1-4` says: "Useful when the venv isn't on PATH, or when scripting from inside the package."

Two motivations:
1. **PATH-independence**: `python -m rcm_mc` works as long as the package is importable; doesn't need `bin/` on PATH.
2. **Container robustness**: Dockerfile uses this form to avoid console-script-generation failure modes.

### Trace summary

```
shell:    $ python -m rcm_mc serve --port 8080 --host 0.0.0.0
              │
   Stage 1 │  Python `-m` resolves to RCM_MC/rcm_mc/__main__.py
              ▼
   Stage 2 │  __main__.py:7  from .cli import main
              │  __main__.py:12 sys.exit(main() or 0)
              ▼
   Stage 3 │  cli.py:1252  main(argv=None)
              │  cli.py:1299 if first == "serve":
              │  cli.py:1300 from .server import main as serve_main
              ▼
   Stage 4-9│  Same as Report 0018 (server.py argparse → run_server → build_server → serve_forever)
```

## Merge risks flagged

| ID | Risk | Detail | Severity |
|---|---|---|---|
| **MR376** | **Two entry-point paths converge at `cli.py:main`** | A signature change to `cli.py:main(argv=None)` ripples to BOTH the console-script + the `__main__.py` callers. Already-known coupling but worth flagging. | Low |
| **MR377** | **`__main__.py` uses relative import `from .cli import main`** | Works only when `rcm_mc` is on `sys.path` AS A PACKAGE — not when run as a directory. Acceptable; flagged for completeness. | Low |
| **MR378** | **`__main__.py` is the production entry per Dockerfile (Report 0033)** | Any branch that breaks `__main__.py` breaks production deploy without breaking the local console-script user (who uses `rcm-mc` directly). **Asymmetric failure.** | Medium |
| **MR379** | **No CLI version flag handler in `__main__.py`** | `python -m rcm_mc --version` would reach cli.py and presumably hit the `--version` flag there. Need to verify. | Low |

## Dependencies

- **Incoming:** Production Dockerfile (Report 0033 line 27); operators running `python -m rcm_mc`.
- **Outgoing:** `rcm_mc.cli:main` (cli.py:1252).

## Open questions / Unknowns

- **Q1.** Does `cli.py:main()` accept argv or read sys.argv? The `__main__.py:12` calls `main()` with no args — relying on argparse defaulting to `sys.argv[1:]`.
- **Q2.** Are there feature branches that rename `__main__.py` or make it more complex?

## Suggested follow-ups

| Iteration | Proposed area | Why |
|---|---|---|
| **0049** | **Env vars** (already requested as iteration 49). | Pending. |
| **0050** | **Read `cli.py:main()` signature + body** | Resolves Q1 + the long-deferred CLI audit (Report 0003). |

---

Report/Report-0048.md written. Next iteration should: env-var sweep on `infra/notifications.py` (4 SMTP env vars deferred since Report 0019 MR148) — sister to Report 0019's server.py sweep.

