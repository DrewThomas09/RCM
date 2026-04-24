# tools/

Stdlib-only utility scripts. Each file is self-contained — no package imports, no shared helpers, no dependencies beyond the Python standard library.

## Files

| File | Purpose |
|------|---------|
| `build_dep_graph.py` | **AST-parsed automatic dependency graph** over `rcm_mc/` source. Self-validating companion to [`ARCHITECTURE_MAP.md`](../../ARCHITECTURE_MAP.md) at the repo root — where that doc is hand-authored (and can drift), this script reads the actual `import` statements and emits the real graph. |

## `build_dep_graph.py`

### Run

```bash
python RCM_MC/tools/build_dep_graph.py
```

Stdlib-only. Outputs to stdout:

1. **Text summary** — for each sub-package, its file count and the sub-packages that import from it (with counts)
2. **Mermaid flowchart** — GitHub-renderable; nodes = sub-packages (with file counts), edges = cross-package imports with ≥5 count, labels on heavy edges (≥20)

### Scope

- Walks all `.py` under `rcm_mc/`
- Excludes `__pycache__`, `.venv`, `venv`, `.egg-info`, `build`, `dist`, and macOS Finder duplicates (`* 2.py`)
- Handles both absolute (`from rcm_mc.X import Y`) and relative (`from ..X import Y`) imports by resolving each to its absolute dotted module path
- Filters intra-package imports (same src + dst sub-package) so the edge count is pure cross-package

### Design

Pure functions over parsing:

- `collect_imports_from_file(path)` → list of sub-package names this file imports from
- `_file_to_module(path)` → `rcm_mc/ui/chartis/X.py` becomes `rcm_mc.ui.chartis.X`
- `_resolve_relative(file_mod, level, module)` → resolves a relative import to absolute form
- `_subpkg_of_module(abs_module)` → `rcm_mc.ui._chartis_kit` becomes `ui`
- `build_edge_counts(root)` → `{(src, dst): count}` edge dict + file counts per sub-package
- `render_text_summary()` / `render_mermaid()` → output functions

### When to re-run

- After any significant refactor that moves modules between sub-packages
- Before shipping a PR that changes the architectural shape
- Periodically to verify `ARCHITECTURE_MAP.md` still matches reality

### Known limitations

- **Conditional imports** (inside `try/except` or `if ENV == ...`) are captured since `ast.walk` visits all nodes; this is usually what you want (import graph = potential dependencies) but can over-count
- **Dynamic imports** (`importlib.import_module("...")`) are invisible to AST and not counted
- **Package-level granularity only**; file-level graph is in `FILE_MAP.md`
- **`min_weight=5` edge filter** — edges under 5 imports suppressed to keep the diagram readable. Pass a different value by editing `render_mermaid()` call in `main()`.
