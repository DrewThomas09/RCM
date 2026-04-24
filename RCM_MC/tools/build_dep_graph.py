#!/usr/bin/env python3
"""Build an automatic dependency graph from rcm_mc/ source via ast.parse.

Self-validating companion to ARCHITECTURE_MAP.md.

Where ARCHITECTURE_MAP.md is hand-authored (and can drift), this script
parses every .py file under rcm_mc/ with Python's ast module, extracts
every `from rcm_mc.X.Y import Z` and `import rcm_mc.X.Y` statement, and
emits two artifacts:

1. A text summary of package-to-package import counts
2. A GitHub-renderable Mermaid flowchart reflecting the **real** import
   graph at the top-package level (29 sub-packages)

Run:
    python RCM_MC/tools/build_dep_graph.py

Writes to stdout; redirect or pipe as you prefer.

Stdlib only — no third-party deps.

Design constraints:
- **Pure functions over parsing** — one function to collect imports, one
  to aggregate, one to render. Each testable in isolation.
- **Read-only** — never modifies source, never writes to the source tree
  (stdout only).
- **Package-level, not file-level** — emits a 29-node graph. File-level
  would be too dense to render. File-level is in FILE_MAP.md.
- **Includes only internal imports** — `from rcm_mc.X import Y` counted;
  stdlib + third-party skipped. We want architectural signal, not noise.
"""
from __future__ import annotations

import ast
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple


# ---------------------------------------------------------------------------
# Pure-function parsing
# ---------------------------------------------------------------------------

def _file_to_module(path: Path) -> str:
    """Path `rcm_mc/ui/chartis/X.py` → dotted module name `rcm_mc.ui.chartis.X`.

    Returns empty string if the path isn't under `rcm_mc/`.
    """
    parts = list(path.parts)
    if "rcm_mc" not in parts:
        return ""
    idx = parts.index("rcm_mc")
    name = parts[-1][:-3]  # strip .py
    return ".".join(parts[idx:-1] + [name])


def _resolve_relative(file_mod: str, level: int, module: str | None) -> str | None:
    """Resolve a relative import to its absolute dotted module path.

    Python's rule: level=N drops N components from the file's containing
    package path; then module_name (if any) is appended.

    Example: file `rcm_mc.ui.foo` with `from .bar import X` (level=1) →
    file's package = `rcm_mc.ui`; drop 0 more (level-1 trailing comps
    from package); append `bar` → `rcm_mc.ui.bar`.

    File `rcm_mc.ui.chartis.X` with `from .._chartis_kit import Y` (level=2):
    file's package = `rcm_mc.ui.chartis`; drop 1 trailing comp → `rcm_mc.ui`;
    append `_chartis_kit` → `rcm_mc.ui._chartis_kit`.
    """
    if not file_mod or level < 1:
        return None
    file_parts = file_mod.split(".")
    # The file's containing package is file_parts[:-1].
    # level=1 means "current package", level=2 means "parent package", etc.
    # So target_package = file_parts[:-level] (trimming level-1 trailing comps from the package).
    if level > len(file_parts) - 1:
        return None
    target_pkg_parts = file_parts[: len(file_parts) - level]
    if not target_pkg_parts:
        return None
    if module:
        return ".".join(target_pkg_parts + module.split("."))
    return ".".join(target_pkg_parts)


def _subpkg_of_module(abs_module: str) -> str | None:
    """`rcm_mc.ui._chartis_kit` → `ui`. `rcm_mc.cli` → None (top-level file)."""
    if not abs_module.startswith("rcm_mc."):
        return None
    parts = abs_module.split(".")
    if len(parts) >= 2:
        return parts[1]
    return None


def _subpkg_of(path: Path) -> str | None:
    """Return the top-level rcm_mc sub-package a path belongs to.

    E.g. `rcm_mc/diligence/hcris_xray/metrics.py` -> 'diligence'.
    Returns None for the top-level `rcm_mc/__init__.py`, `rcm_mc/cli.py`, etc.
    """
    parts = path.parts
    if "rcm_mc" not in parts:
        return None
    idx = parts.index("rcm_mc")
    if idx + 1 >= len(parts):
        return None
    if parts[idx + 1].endswith(".py"):
        # File directly in rcm_mc/ (e.g. rcm_mc/cli.py)
        return None
    return parts[idx + 1]


def collect_imports_from_file(path: Path) -> List[str]:
    """Return the top-level rcm_mc sub-package names this file imports from.

    Handles both absolute and relative imports by resolving each to its
    absolute dotted module path, then extracting the sub-package. Returns
    empty list if the file can't be parsed.
    """
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
    except (SyntaxError, UnicodeDecodeError):
        return []

    subpkgs: List[str] = []
    file_mod = _file_to_module(path)

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.level >= 1:
                abs_mod = _resolve_relative(file_mod, node.level, node.module)
            elif node.module:
                abs_mod = node.module
            else:
                continue
            if abs_mod:
                pkg = _subpkg_of_module(abs_mod)
                if pkg:
                    subpkgs.append(pkg)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                pkg = _subpkg_of_module(alias.name)
                if pkg:
                    subpkgs.append(pkg)
    return subpkgs


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def walk_repo(root: Path) -> Iterable[Path]:
    """Yield every .py file under root, excluding caches and venvs."""
    skip = {"__pycache__", ".venv", "venv", ".egg-info", "build", "dist"}
    for p in root.rglob("*.py"):
        if any(s in p.parts for s in skip):
            continue
        if any(part.endswith(".egg-info") for part in p.parts):
            continue
        # Skip macOS Finder duplicates
        if " 2." in p.name or p.name.endswith(" 2.py"):
            continue
        yield p


def build_edge_counts(root: Path) -> Tuple[Dict[Tuple[str, str], int], Counter]:
    """Return (edges, file_counts).

    edges: {(src_subpkg, dst_subpkg): count_of_imports}
    file_counts: {subpkg: number_of_.py_files}
    """
    edges: Dict[Tuple[str, str], int] = defaultdict(int)
    file_counts: Counter = Counter()

    for path in walk_repo(root):
        src = _subpkg_of(path)
        if src is None:
            continue
        file_counts[src] += 1
        for dst in collect_imports_from_file(path):
            if dst == src:
                continue  # ignore intra-package imports
            edges[(src, dst)] += 1
    return edges, file_counts


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def render_text_summary(edges: Dict[Tuple[str, str], int], file_counts: Counter) -> str:
    """Plain-text summary — top importers per sub-package, sorted by file count."""
    lines = []
    lines.append(f"# Dependency graph summary — {sum(file_counts.values())} files across "
                 f"{len(file_counts)} sub-packages")
    lines.append("")

    inbound: Dict[str, Counter] = defaultdict(Counter)
    for (src, dst), n in edges.items():
        inbound[dst][src] += n

    for subpkg in sorted(file_counts, key=lambda k: -file_counts[k]):
        lines.append(f"## {subpkg}/ ({file_counts[subpkg]} files)")
        top_in = inbound.get(subpkg, Counter()).most_common(6)
        if top_in:
            lines.append("  imported by:")
            for src, n in top_in:
                lines.append(f"    {src:<20} ({n} imports)")
        else:
            lines.append("  (no internal importers — leaf/entry point)")
        lines.append("")
    return "\n".join(lines)


def render_mermaid(edges: Dict[Tuple[str, str], int], file_counts: Counter,
                   min_weight: int = 5) -> str:
    """GitHub-renderable Mermaid flowchart of the top-level import graph.

    Only edges with >= min_weight imports are drawn; smaller edges are
    left out to keep the graph readable. File counts shown per node.
    """
    lines = ["```mermaid", "flowchart LR"]
    # Node definitions with file counts
    for subpkg in sorted(file_counts):
        lines.append(f'    {subpkg}["{subpkg}<br/>({file_counts[subpkg]} files)"]')
    lines.append("")
    # Edges
    heavy_edges = [(s, d, n) for (s, d), n in edges.items() if n >= min_weight]
    heavy_edges.sort(key=lambda e: -e[2])
    for src, dst, n in heavy_edges:
        lines.append(f"    {src} --"
                     f"{'|' + str(n) + '|' if n >= 20 else ''}"
                     f"--> {dst}")
    lines.append("```")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: List[str]) -> int:
    if len(argv) > 1 and argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0

    root = Path(__file__).resolve().parent.parent / "rcm_mc"
    if not root.exists():
        print(f"ERROR: can't find rcm_mc/ at {root}", file=sys.stderr)
        return 1

    edges, file_counts = build_edge_counts(root)

    print(render_text_summary(edges, file_counts))
    print()
    print("# Mermaid diagram")
    print()
    print("Only edges with ≥5 internal imports shown to keep the graph readable.")
    print("Edge labels show import count for heavy edges (≥20).")
    print()
    print(render_mermaid(edges, file_counts, min_weight=5))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
