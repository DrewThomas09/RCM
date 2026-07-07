"""Provenance-coverage scan — % of ck_kpi_block call sites carrying a
provenance affordance (tooltip / source / basis), per page renderer.

BACKLOG #32 (P10). The platform's credibility rests on every partner-
facing number being traceable to its origin — that is why the kit ships
``ck_provenance_tooltip``, ``ck_source_link``, and the ``help=`` gloss
on ``ck_kpi_block``. This module measures how much of the KPI surface
actually uses them, so the /methodology page can publish a *live*
coverage number instead of a hand-maintained one that drifts (the same
reason W4-006 loads demo metrics from the vendored HCRIS frame rather
than hardcoding copies).

One scan function, two consumers: the /methodology renderer
(``rcm_mc/ui/library_page.py``) and ``tests/test_provenance_coverage.py``
import THE SAME ``scan_provenance_coverage`` — no duplicated logic, no
stale numbers. Design precedent: ``tools/v5_fidelity_audit.py`` (static
scan published as a metric), but this one lives inside the package
because a page renderer must import it at request time.

What counts as a provenance affordance AT a call site (static, source-
level — we do not execute page renderers, many need a live DB):

  · **tooltip** — a ``help={"definition": ...}`` mapping on the block
    (renders the ``[?]`` gloss via ``ck_help_tooltip``), or a
    ``ck_provenance_tooltip`` / ``provenance_tooltip`` /
    ``ck_help_tooltip`` call inside any argument.
  · **source** — a ``ck_source_link(...)`` call inside any argument,
    or a string literal naming its origin with a ``source:`` marker
    (e.g. ``"Source: CMS HCRIS"``).
  · **basis** — a string literal with a ``basis:`` marker
    (e.g. ``"basis: FY2023 cost reports"``). CSS ``flex-basis:`` is
    explicitly excluded (lookbehind on ``-``).

The scan resolves ONE hop of local names: pages routinely build
``value = ck_provenance_tooltip(...)`` a few lines above the block and
pass the variable (see ``source_page.py``) — a hand count of the
rendered page sees that tooltip, so the scanner must too, or the
published number would be indefensibly low. Deeper indirection
(helpers returning affordance HTML across modules) is deliberately NOT
chased — the metric stays a conservative floor and stays cheap.
"""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple, Union

# Kit helpers whose presence inside a ck_kpi_block argument makes the
# value traceable. ``provenance_tooltip`` is the graph-driven
# implementation in _provenance_tooltip.py that a few pages call
# directly; ``ck_help_tooltip`` is what ``help=`` compiles to when a
# caller pre-wraps the label itself.
_PROVENANCE_CALLS = frozenset({
    "ck_provenance_tooltip",
    "provenance_tooltip",
    "ck_source_link",
    "ck_help_tooltip",
})

# ``Source: CMS HCRIS`` / ``basis: FY2023`` markers inside string
# literals. The lookbehind excludes CSS ``flex-basis:`` (a real string
# that reaches kpi sub-slots via style attributes on wrapped spans).
_RE_MARKER = re.compile(r"(?i)(?<![\w-])(?:source|basis)\s*:")

# Directories under the UI root that are never page renderers.
_SKIP_DIRS = frozenset({"__pycache__", "static"})


@dataclass(frozen=True)
class PageCoverage:
    """Coverage for one page-renderer file (path relative to the UI root)."""
    page: str
    total_sites: int
    with_provenance: int
    pct: float


@dataclass(frozen=True)
class CoverageReport:
    """Whole-scan result. ``pages`` is sorted by path so two scans of the
    same tree compare equal (the reproducibility contract in the
    BACKLOG #32 verification plan)."""
    pages: Tuple[PageCoverage, ...]
    total_sites: int
    with_provenance: int
    pct: float
    skipped: Tuple[str, ...]  # files that failed to parse (mid-edit trees)


def _pct(numerator: int, denominator: int) -> float:
    """Percentage at the house 1dp convention; 0.0 for an empty scan."""
    if denominator <= 0:
        return 0.0
    return round(100.0 * numerator / denominator, 1)


def _call_name(node: ast.Call) -> Optional[str]:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


_SCOPE_NODES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda,
                ast.ClassDef)


def _scope_children(node: ast.AST) -> List[ast.AST]:
    """Descendants of ``node`` WITHOUT descending into nested scopes
    (functions / lambdas / classes). ``ast.walk`` ignores scope
    boundaries, which would let an inner function's assignments shadow
    the analysis of the outer one. Materialized once per scope and
    iterated three times — a recursive generator here made the full
    scan ~10x slower (O(depth) per yield across ~6M nodes)."""
    out: List[ast.AST] = []
    stack: List[ast.AST] = [node]
    while stack:
        current = stack.pop()
        for child in ast.iter_child_nodes(current):
            out.append(child)
            if not isinstance(child, _SCOPE_NODES):
                stack.append(child)
    return out


def _node_carries_affordance(node: ast.AST) -> bool:
    """True when the expression subtree contains a provenance helper
    call or a source:/basis: string marker."""
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            if _call_name(n) in _PROVENANCE_CALLS:
                return True
        elif isinstance(n, ast.Constant) and isinstance(n.value, str):
            if _RE_MARKER.search(n.value):
                return True
    return False


_Assigns = Dict[str, List[Tuple[int, ast.AST]]]


def _site_covered(call: ast.Call, scope_stack: Sequence[_Assigns]) -> bool:
    """Classify one ck_kpi_block call site.

    Order matters only for cost: the direct checks are O(call subtree);
    the one-hop name resolution walks prior assignments in enclosing
    scopes (innermost first) and stops at the first affordance."""
    # help={"definition": ...} → the [?] gloss. An explicit help=None
    # is the "deliberately no tooltip" spelling and does not count.
    for kw in call.keywords:
        if kw.arg == "help":
            if not (isinstance(kw.value, ast.Constant) and kw.value.value is None):
                return True
    arg_nodes: List[ast.AST] = list(call.args) + [
        kw.value for kw in call.keywords if kw.value is not None
    ]
    for node in arg_nodes:
        if _node_carries_affordance(node):
            return True
    # One-hop local-name resolution (see module docstring for why).
    names = {
        n.id
        for node in arg_nodes
        for n in ast.walk(node)
        if isinstance(n, ast.Name)
    }
    for name in names:
        for assigns in reversed(scope_stack):
            for lineno, value in assigns.get(name, ()):
                if lineno <= call.lineno and _node_carries_affordance(value):
                    return True
    return False


def _scan_source(source: str) -> Tuple[int, int]:
    """(total_sites, with_provenance) for one file's source text.

    Raises SyntaxError upward — the caller decides how to report an
    unparseable file (concurrent editors leave transiently broken
    trees; the scan must not take the /methodology page down)."""
    tree = ast.parse(source)
    total = 0
    covered = 0

    def visit_scope(scope_node: ast.AST,
                    outer: Tuple[_Assigns, ...]) -> None:
        nonlocal total, covered
        children = _scope_children(scope_node)
        assigns: _Assigns = {}
        for n in children:
            if isinstance(n, ast.Assign):
                for target in n.targets:
                    if isinstance(target, ast.Name):
                        assigns.setdefault(target.id, []).append(
                            (n.lineno, n.value))
            elif isinstance(n, ast.AnnAssign) and n.value is not None \
                    and isinstance(n.target, ast.Name):
                assigns.setdefault(n.target.id, []).append(
                    (n.lineno, n.value))
            elif isinstance(n, ast.AugAssign) \
                    and isinstance(n.target, ast.Name):
                # s += ck_source_link(...) — the increment can add the
                # affordance even when the seed string had none.
                assigns.setdefault(n.target.id, []).append(
                    (n.lineno, n.value))
        stack = outer + (assigns,)
        for n in children:
            if isinstance(n, ast.Call) and _call_name(n) == "ck_kpi_block":
                total += 1
                if _site_covered(n, stack):
                    covered += 1
        for n in children:
            if isinstance(n, _SCOPE_NODES):
                visit_scope(n, stack)

    visit_scope(tree, ())
    return total, covered


def scan_provenance_coverage(
    root: Union[str, Path, None] = None,
) -> CoverageReport:
    """Scan every ``*.py`` under ``root`` (default: this package's UI
    directory) and return per-page + overall coverage.

    Pure function of the tree on disk: same tree → same report, which
    is what makes the published number reproducible by test. Files
    with zero ck_kpi_block call sites are omitted from ``pages`` —
    they have no KPI surface to cover."""
    ui_root = Path(root) if root is not None else Path(__file__).resolve().parent
    pages: List[PageCoverage] = []
    skipped: List[str] = []
    for path in sorted(ui_root.rglob("*.py")):
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        rel = path.relative_to(ui_root).as_posix()
        try:
            source = path.read_text(encoding="utf-8")
            # Cheap pre-filter before ast.parse — the UI tree carries
            # multi-MB literal modules (geo paths) that can never
            # contain a call site; no point parsing them.
            if "ck_kpi_block" not in source:
                continue
            total, covered = _scan_source(source)
        except (OSError, SyntaxError, ValueError):
            skipped.append(rel)
            continue
        if total == 0:
            continue
        pages.append(PageCoverage(
            page=rel,
            total_sites=total,
            with_provenance=covered,
            pct=_pct(covered, total),
        ))
    total_sites = sum(p.total_sites for p in pages)
    with_provenance = sum(p.with_provenance for p in pages)
    return CoverageReport(
        pages=tuple(pages),
        total_sites=total_sites,
        with_provenance=with_provenance,
        pct=_pct(with_provenance, total_sites),
        skipped=tuple(skipped),
    )


@lru_cache(maxsize=1)
def cached_coverage_report() -> CoverageReport:
    """Process-lifetime cache for the /methodology renderer.

    The scan reads ~470 files and ast-parses ~330 of them (~2 s);
    paying that once per server process is fine, once per request is
    not. The source tree of a running server does not change, so no
    invalidation is needed — tests that mutate fixtures call
    ``scan_provenance_coverage`` directly with their own root."""
    return scan_provenance_coverage()


def _main() -> int:
    """Tiny CLI for hand-verification (same spirit as
    tools/v5_fidelity_audit.py): worst pages first, overall line last."""
    report = scan_provenance_coverage()
    rows = sorted(report.pages,
                  key=lambda p: (p.pct, -p.total_sites, p.page))
    for p in rows:
        print(f"{p.pct:6.1f}%  {p.with_provenance:4d}/{p.total_sites:<4d} {p.page}")
    print("-" * 60)
    print(f"OVERALL {report.pct:.1f}% — {report.with_provenance} of "
          f"{report.total_sites} ck_kpi_block call sites across "
          f"{len(report.pages)} pages carry a provenance affordance")
    if report.skipped:
        print(f"skipped (unparseable): {', '.join(report.skipped)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
