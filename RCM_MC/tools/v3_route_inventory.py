"""Generate docs/V3_ROUTE_INVENTORY.md from server.py.

Walks the GET dispatcher in rcm_mc/server.py, extracts every URL
pattern (exact match + startswith-prefix), traces each block to
its renderer module under rcm_mc/ui/, and classifies the renderer
on two axes:

  - v3 design compliance:
      * v3        — uses chartis_shell from _chartis_kit_editorial,
                    or lives under ui/chartis/
      * legacy    — uses shell() from _ui_kit only
      * bespoke   — neither (custom HTML, raw write, etc.)
      * unknown   — could not resolve renderer module

  - packet-driven (CLAUDE.md load-bearing invariant):
      * yes — renderer calls get_or_build_packet or imports
              DealAnalysisPacket
      * no  — renderer reads database / config directly

Why this script exists:
  Campaign 1B — the v3 transformation campaign needs a single
  source of truth listing every route, its current state, and
  what's left to migrate. Re-run after any migration commit so
  the inventory stays in step with reality.

Usage:
  cd "Coding Projects/"
  python3 RCM_MC/tools/v3_route_inventory.py
  # writes docs/V3_ROUTE_INVENTORY.md and prints summary counts

The classification is heuristic. A line saying "v3" doesn't
mean every aspect of the v3 spec is honored — it means the
renderer at least reaches the v3 chrome. Use the inventory as
a worklist, not an audit.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import NamedTuple

REPO_ROOT = Path(__file__).resolve().parents[2]
SERVER_PY = REPO_ROOT / "RCM_MC" / "rcm_mc" / "server.py"
UI_DIR = REPO_ROOT / "RCM_MC" / "rcm_mc" / "ui"
OUT_PATH = REPO_ROOT / "docs" / "V3_ROUTE_INVENTORY.md"


class Route(NamedTuple):
    pattern: str
    match_kind: str  # "==", "startswith", "in"
    renderer: str  # module path or "(inline)" or "(redirect)"
    v3_status: str  # v3 / legacy / bespoke / redirect / unknown
    packet: str  # yes / no / n/a


_PATH_EQ_RE = re.compile(r'\bpath\s*==\s*"([^"]+)"')
_PATH_STARTSWITH_RE = re.compile(r'\bpath\.startswith\("([^"]+)"\)')
_PATH_IN_RE = re.compile(r'\bpath\s+in\s+\(([^)]+)\)')
_UI_IMPORT_RE = re.compile(r"from \.ui\.([A-Za-z_][A-Za-z0-9_.]*) import")
_RENDER_CALL_RE = re.compile(r"\brender_([A-Za-z_][A-Za-z0-9_]*)\s*\(")
_REDIRECT_RE = re.compile(r"self\._redirect\(")


def _slice_dispatcher(src: str) -> str:
    """Return the body of _do_get_inner from server.py."""
    start = src.find("def _do_get_inner(")
    if start < 0:
        raise SystemExit("could not find _do_get_inner in server.py")
    # End at the next top-level method definition (4-space indent).
    end_re = re.compile(r"^    def [a-zA-Z_]\w*\(", re.M)
    m = end_re.search(src, start + 1)
    end = m.start() if m else len(src)
    return src[start:end]


def _extract_blocks(dispatcher: str) -> list[tuple[str, str, str]]:
    """Walk the dispatcher line-by-line, group consecutive lines into
    if-blocks keyed by the URL pattern they match.

    Returns list of (pattern, kind, body_text) tuples where ``body_text``
    is the lines between the if-condition and the next if/elif at the
    same indent.
    """
    lines = dispatcher.splitlines()
    blocks: list[tuple[str, str, str]] = []

    cur_patterns: list[tuple[str, str]] = []  # (pattern, kind)
    cur_body: list[str] = []
    base_indent = 8  # body of _do_get_inner is indented 8 spaces

    def _flush() -> None:
        if not cur_patterns:
            return
        body = "\n".join(cur_body)
        for pat, kind in cur_patterns:
            blocks.append((pat, kind, body))

    for line in lines:
        stripped = line.strip()
        # Detect new if/elif at base_indent
        if (
            line.startswith(" " * base_indent)
            and not line.startswith(" " * (base_indent + 1))
            and (stripped.startswith("if ") or stripped.startswith("elif "))
        ):
            _flush()
            cur_patterns = []
            cur_body = [line]
            for pat in _PATH_EQ_RE.findall(stripped):
                cur_patterns.append((pat, "=="))
            for pat in _PATH_STARTSWITH_RE.findall(stripped):
                cur_patterns.append((pat, "startswith"))
            for grp in _PATH_IN_RE.findall(stripped):
                for pat in re.findall(r'"([^"]+)"', grp):
                    cur_patterns.append((pat, "in"))
        else:
            cur_body.append(line)
    _flush()
    return blocks


def _classify_renderer(renderer_module: str) -> tuple[str, str]:
    """Return (v3_status, packet_status) for a ui module name like
    'dashboard_page' or 'chartis.app_page'."""
    if not renderer_module:
        return ("unknown", "no")
    if renderer_module.startswith("chartis."):
        path = UI_DIR / "chartis" / (renderer_module.split(".", 1)[1] + ".py")
    else:
        path = UI_DIR / (renderer_module.replace(".", "/") + ".py")
    if not path.is_file():
        return ("unknown", "no")
    text = path.read_text(encoding="utf-8", errors="replace")
    # v3 marker: chartis_shell from editorial OR file is in chartis/
    if renderer_module.startswith("chartis."):
        v3 = "v3"
    elif "chartis_shell" in text or "_chartis_kit_editorial" in text:
        v3 = "v3"
    elif "from ._ui_kit import shell" in text or "from .._ui_kit import shell" in text or " shell(" in text:
        v3 = "legacy"
    else:
        v3 = "bespoke"
    # Packet marker
    if "get_or_build_packet" in text or "DealAnalysisPacket" in text:
        packet = "yes"
    else:
        packet = "no"
    return (v3, packet)


def _resolve_renderer(body: str) -> str:
    """Pick a single representative renderer module for an if-body.

    Heuristic: first .ui import wins. If none, look for render_<name>
    calls and try to match a module by name. If neither, return
    '(inline)' or '(redirect)' as appropriate.
    """
    imports = _UI_IMPORT_RE.findall(body)
    if imports:
        return imports[0]
    if _REDIRECT_RE.search(body):
        return "(redirect)"
    renders = _RENDER_CALL_RE.findall(body)
    if renders:
        return f"(render_{renders[0]})"
    return "(inline)"


def main() -> int:
    src = SERVER_PY.read_text(encoding="utf-8")
    dispatcher = _slice_dispatcher(src)
    blocks = _extract_blocks(dispatcher)

    routes: list[Route] = []
    for pattern, kind, body in blocks:
        renderer = _resolve_renderer(body)
        if renderer == "(redirect)":
            v3, pkt = "redirect", "n/a"
        elif renderer.startswith("("):
            v3, pkt = "unknown", "no"
        else:
            v3, pkt = _classify_renderer(renderer)
        routes.append(Route(pattern, kind, renderer, v3, pkt))

    routes.sort(key=lambda r: (r.pattern, r.match_kind))

    # Counts
    total = len(routes)
    v3_count = sum(1 for r in routes if r.v3_status == "v3")
    legacy_count = sum(1 for r in routes if r.v3_status == "legacy")
    bespoke_count = sum(1 for r in routes if r.v3_status == "bespoke")
    redirect_count = sum(1 for r in routes if r.v3_status == "redirect")
    unknown_count = sum(1 for r in routes if r.v3_status == "unknown")
    packet_yes = sum(1 for r in routes if r.packet == "yes")

    pct = lambda n: f"{(100 * n / total):.0f}%" if total else "n/a"

    md_lines = [
        "# V3 Route Inventory",
        "",
        f"Generated by `RCM_MC/tools/v3_route_inventory.py` from "
        f"`RCM_MC/rcm_mc/server.py`. Re-run after any migration commit.",
        "",
        f"**Total routes mapped:** {total}",
        "",
        "## Compliance summary",
        "",
        f"| Status | Count | % |",
        f"|---|---|---|",
        f"| v3 (chartis_shell or under ui/chartis/) | {v3_count} | {pct(v3_count)} |",
        f"| legacy (`shell()` from `_ui_kit` only) | {legacy_count} | {pct(legacy_count)} |",
        f"| bespoke (no shell — direct HTML) | {bespoke_count} | {pct(bespoke_count)} |",
        f"| redirect | {redirect_count} | {pct(redirect_count)} |",
        f"| unknown / unresolved | {unknown_count} | {pct(unknown_count)} |",
        "",
        f"**Packet-driven (calls `get_or_build_packet` or imports "
        f"`DealAnalysisPacket`):** {packet_yes} of {total} ({pct(packet_yes)})",
        "",
        "## Caveats",
        "",
        "- Classification is heuristic. `v3` means the renderer "
        "*reaches* the v3 chrome — it does not mean every aspect of "
        "the v3 spec (tabular-nums, ISO dates, 2-decimal financials, "
        "`#1F4E78` accent) is honored. Audit before claiming a page "
        "is fully migrated.",
        "- The `unknown` bucket is overwhelmingly inline routes "
        "(static files, JSON endpoints, redirects with no UI module) "
        "— those legitimately have no renderer to classify.",
        "- Some routes have multiple URL aliases (e.g. `/`, "
        "`/index.html`); each alias is listed separately so the "
        "table shows the surface area a partner can hit.",
        "",
        "## Routes",
        "",
        "| URL pattern | Match | Renderer | v3 status | Packet-driven |",
        "|---|---|---|---|---|",
    ]
    for r in routes:
        # Markdown-escape pipe in the rare case it appears
        pat = r.pattern.replace("|", "\\|")
        md_lines.append(
            f"| `{pat}` | {r.match_kind} | `{r.renderer}` | "
            f"{r.v3_status} | {r.packet} |"
        )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    sys.stdout.write(f"wrote {OUT_PATH.relative_to(REPO_ROOT)}\n")
    sys.stdout.write(
        f"  total={total} v3={v3_count} legacy={legacy_count} "
        f"bespoke={bespoke_count} redirect={redirect_count} "
        f"unknown={unknown_count} packet-driven={packet_yes}\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
