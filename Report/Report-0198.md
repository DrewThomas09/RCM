# Report 0198: Entry Point — `rcm-mc analysis <deal_id>` CLI

## Scope

Traces `rcm-mc analysis` subcommand from invocation. Sister to Reports 0018, 0048, 0078, 0102, 0108, 0138, 0168 (entry points).

## Findings

### Layer 1 — Shell

```bash
rcm-mc analysis <deal_id> [--db p.db] [--scenario X] [--as-of YYYY-MM-DD] [--out PATH] [--rebuild] [--skip-sim|--run-sim] [--indent N]
```

### Layer 2 — `main()` dispatcher (cli.py:1252)

`main` routes `argv[0] == "analysis"` → `analysis_main(argv[1:])` at line 1303.

### Layer 3 — `analysis_main()` (cli.py:1196)

8 argparse args. Default `--db = "portfolio.db"` (cwd-relative — Report 0118 MR679 7th distinct default!).

### Layer 4 — `get_or_build_packet`

```python
from .analysis.analysis_store import get_or_build_packet
packet = get_or_build_packet(
    store, args.deal_id,
    scenario_id=args.scenario, as_of=as_of,
    force_rebuild=bool(args.rebuild),
    skip_simulation=bool(args.skip_sim),
)
```

Per Reports 0008, 0080, 0148: `analysis_store` cache (analysis_runs table, hash_inputs key).

### Layer 5 — Output

JSON via `packet.to_json(indent=args.indent)` → stdout OR `--out` file.

### `--skip-sim default True` — surprising

`ap.add_argument("--skip-sim", action="store_true", default=True, ...)`
`ap.add_argument("--run-sim", dest="skip_sim", action="store_false", ...)`

**MC simulation is OFF BY DEFAULT.** User must pass `--run-sim` to actually run MC. **Surprising** if user expects "rcm-mc analysis = full analysis."

**MR972 below.**

### Error handling — broad except (line 1228)

```python
except Exception as exc:  # noqa: BLE001
    sys.stderr.write(f"build failed: {exc}\n")
    return 1
```

Standard Report 0140 broad-except discipline.

### `--as-of` validation

Lines 1218-1224: `_date.fromisoformat(args.as_of)` with try/except → return 2 (different exit code from build-failure return 1). **Distinguishes user-error vs internal-error.** Good UX.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR972** | **`--skip-sim` defaults TRUE** — `rcm-mc analysis` does NOT run MC by default | UX surprise. CLI users likely expect full analysis. Should default `--run-sim=False` AND show a "(skipped MC)" message. | Medium |
| **MR973** | **7th distinct `--db` default** in CLI subcommand | Cross-link Reports 0118 MR679, 0138 MR782, 0163, 0168 MR896 — pattern. | High (carried) |

## Dependencies

- **Incoming:** `rcm-mc` console script.
- **Outgoing:** PortfolioStore, get_or_build_packet (analysis_store).

## Open questions / Unknowns

- **Q1.** Why is `--skip-sim` default true?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0199** | Env vars (in flight). |

---

Report/Report-0198.md written.
