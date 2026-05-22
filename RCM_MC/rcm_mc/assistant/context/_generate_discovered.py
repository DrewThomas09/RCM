"""Regenerate ``discovered_tool_routes.py`` from the Cmd+K / Tools palette.

Run:  .venv/bin/python -m rcm_mc.assistant.context._generate_discovered

The palette (``_DEFAULT_PALETTE_MODULES`` in rcm_mc/ui/_chartis_kit.py)
is the route source of truth; its comment-group headers map 1:1 to the
seven PEdesk tool groups. This script parses that block, normalizes
query strings, de-duplicates by normalized route, and writes a concrete
manifest module. Kept as a committed tool so the manifest is
reproducible rather than hand-maintained.
"""
from __future__ import annotations

import re
from collections import OrderedDict
from pathlib import Path

_GROUP_MAP = {
    "Home + ops": ("HOME_OPERATIONS", "Home & Operations"),
    "Pipeline / sourcing": ("PIPELINE_SOURCING", "Pipeline & Sourcing"),
    "Diligence playbook": ("DILIGENCE_WORKSPACE", "Diligence Workspace"),
    "Library / reference": ("LIBRARY_REFERENCE", "Library & Reference"),
    "Research": ("RESEARCH_BACKTESTING", "Research & Backtesting"),
    "Portfolio": ("PORTFOLIO_LP", "Portfolio & LP"),
    "Admin / system": ("ADMIN_SYSTEM", "Admin & System"),
}


def normalize_route(route: str) -> str:
    r = route.split("?", 1)[0].split("#", 1)[0]
    if len(r) > 1 and r.endswith("/"):
        r = r.rstrip("/")
    return r


def discover() -> "OrderedDict[str, tuple]":
    src = (Path(__file__).resolve().parents[2]
           / "ui" / "_chartis_kit.py").read_text()
    block = re.search(r"_DEFAULT_PALETTE_MODULES = \[(.*?)\n\]", src, re.S).group(1)
    cur_cat, cur_grp = "UNKNOWN", "Unknown"
    buf = ""
    found: "OrderedDict[str, tuple]" = OrderedDict()
    for raw in block.splitlines():
        line = raw.strip()
        if line.startswith("#"):
            label = line.lstrip("# ").strip()
            if label in _GROUP_MAP:
                cur_cat, cur_grp = _GROUP_MAP[label]
            continue
        buf += " " + line
        if "}" in line:
            route_m = re.search(r'"route"\s*:\s*"([^"]+)"', buf)
            title_m = re.search(r'"title"\s*:\s*"([^"]+)"', buf)
            if route_m and title_m:
                n = normalize_route(route_m.group(1))
                if n not in found:
                    found[n] = (title_m.group(1), route_m.group(1),
                                cur_cat, cur_grp)
            buf = ""
    return found


def render(found) -> str:
    lines = [
        '"""AUTO-GENERATED discovered tool routes — the PEdesk route manifest.',
        '',
        'Source of truth: ``_DEFAULT_PALETTE_MODULES`` in rcm_mc/ui/_chartis_kit.py',
        '(the Cmd+K / Tools palette, grouped into the seven PEdesk tool groups).',
        'Regenerate with rcm_mc/assistant/context/_generate_discovered.py.',
        'Routes are query-string-normalized and de-duplicated.',
        '"""',
        'from __future__ import annotations',
        '',
        'from typing import List',
        '',
        'from .types import PageContextCategory, ToolRouteDefinition',
        '',
        '_SOURCE_FILE = "rcm_mc/ui/_chartis_kit.py::_DEFAULT_PALETTE_MODULES"',
        '',
        'DISCOVERED_TOOL_ROUTES: List[ToolRouteDefinition] = [',
    ]
    for n, (title, route, cat, grp) in found.items():
        aliases = [route] if route != n else []
        lines += [
            '    ToolRouteDefinition(',
            f'        title={title!r},',
            f'        route={n!r},',
            f'        category=PageContextCategory.{cat},',
            f'        source_group={grp!r},',
            '        is_auto_generated=True,',
            f'        aliases={aliases!r},',
            '        source_file=_SOURCE_FILE,',
            '    ),',
        ]
    lines += [']', '']
    return "\n".join(lines)


if __name__ == "__main__":
    found = discover()
    out = Path(__file__).with_name("discovered_tool_routes.py")
    out.write_text(render(found))
    print(f"wrote {out} ({len(found)} routes)")
