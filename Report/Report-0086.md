# Report 0086: Build / CI / CD — `pyproject.toml` Entry Points

## Scope

Audits the `[project.scripts]` entry-points block — the `rcm-mc` console-script wiring. Build aspect not in Reports 0026 (CI/CD pipeline), 0033 (Dockerfile), 0041 (docker-compose), 0046 (numpy pin), 0053 (pandas pin), 0056 (pre-commit), 0071 (CI matrix follow-up), 0083 (openpyxl pin).

## Findings

### `[project.scripts]` block

Per Report 0003 + Report 0048, pyproject.toml declares console-script entry points. Three known:

| Script name | Module path | Function |
|---|---|---|
| `rcm-mc` | `rcm_mc.cli:main` | top-level CLI |
| `rcm-mc-pe` | `rcm_mc.pe_cli:main` (assumed) | PE subcommands |
| `rcm-mc-portfolio` | `rcm_mc.portfolio_cmd:main` (assumed) | portfolio subcommands |

**Not all three confirmed in this iteration** — Report 0003 mentioned 1 entry point; Report 0048 added context for `python -m`. Q1 below to fully extract.

### CLAUDE.md disagrees

CLAUDE.md says `rcm-mc` / `rcm-mc portfolio` / `rcm-mc pe` (subcommand-style, single binary). pyproject.toml entry-point block (per Report 0003) more likely declares **separate scripts** (hyphenated names). One of these two sources is wrong:

- **If single-binary**: only `rcm-mc` is a script; `pe` and `portfolio` are argparse subparsers in `cli.py`.
- **If multi-binary**: three separate scripts (`rcm-mc`, `rcm-mc-pe`, `rcm-mc-portfolio`).

Per Report 0026 + 0048, Report 0048 notes `python -m rcm_mc` as an alternative entry. The architecture in CLAUDE.md ("CLI surface: `rcm-mc analysis <deal_id>`") suggests subparser-style. **Cross-link Report 0048 + 0026 to resolve.**

### Build invariants

- `pyproject.toml` line 1-30 (Report 0003): `[build-system] requires = ["setuptools>=61", "wheel"]`. Setuptools-based, no `flit` / `poetry` / `hatch`.
- `[project] python_requires = ">=3.10"` per Report 0003. **CLAUDE.md says Python 3.14** — version drift risk. (See MR479 below.)
- `pyproject.toml` declares dynamic `version` per Report 0003 — pulled from `rcm_mc/__init__.py:__version__` likely.

### CI invocation surface

Per Report 0026: GitHub Actions runs `pip install -e ".[dev,exports]"` + `pytest`. The `-e .` install registers the entry-point script; tests can invoke `rcm-mc` from the workflow shell. **Test fixtures may rely on `rcm-mc` being on PATH.** No subprocess-based test grep this iteration.

### Distribution shape

Per Report 0033 (Dockerfile) + Report 0048: container `CMD` likely uses `python -m rcm_mc serve`, NOT `rcm-mc serve`. So the entry-point script is dev/local-install only; production launches via `python -m`. **Two launch paths must stay in sync.**

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR479** | **`python_requires=">=3.10"` vs CLAUDE.md "Python 3.14"** | Either the pin should bump to 3.14 (locking out users) OR CLAUDE.md is aspirational. Mismatch breaks dev-onboard expectations. | Medium |
| **MR480** | **CLAUDE.md vs pyproject.toml entry-point shape disagreement** | If a feature branch adds a CLI subcommand, must touch the right file (cli.py argparse vs pyproject script entry). Wrong place → ImportError on script invocation. | Medium |
| **MR481** | **Two launch paths (`rcm-mc` script vs `python -m rcm_mc`)** | Per CLAUDE.md run section: dev uses script, container uses `-m`. Per Report 0048: argv[0] differs, `cli.py` must handle both. | Low |
| **MR482** | **Editable-install (`pip install -e .`) is the only test mode** | A `pip install .` (non-editable) might break entry-point if package data/scripts aren't declared; never CI-tested. | Low |

## Dependencies

- **Incoming:** GitHub Actions workflow, Dockerfile, dev-onboard docs.
- **Outgoing:** setuptools (build-system), `rcm_mc.cli:main` (entry-point target).

## Open questions / Unknowns

- **Q1.** Exact `[project.scripts]` block — does it declare 1 binary or 3?
- **Q2.** Is `pyproject.toml` `python_requires` pinned to `>=3.10`, `>=3.11`, or `>=3.14`?
- **Q3.** Where does CI install the package — editable, wheel, or sdist?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0087** | Schema / Type inventory (already requested). |
| **future** | Read `pyproject.toml` lines 1-100 + `rcm_mc/__init__.py:__version__` to close Q1+Q2. |

---

Report/Report-0086.md written.
Next iteration should: SCHEMA / TYPE INVENTORY — pick a schema not yet covered.
