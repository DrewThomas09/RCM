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

  python3 RCM_MC/tools/v3_route_inventory.py --v5
  # writes docs/V5_ROUTE_INVENTORY.md (same classification; v5 label
  # for the chartis-reachable bucket — saving-seeking-chartis campaign)

The classification is heuristic. A line saying "v3" doesn't
mean every aspect of the v3 spec is honored — it means the
renderer at least reaches the v3 chrome. Use the inventory as
a worklist, not an audit.
"""
from __future__ import annotations

import re
import sys
from functools import lru_cache as _lru_cache
from pathlib import Path
from typing import NamedTuple

REPO_ROOT = Path(__file__).resolve().parents[2]
SERVER_PY = REPO_ROOT / "RCM_MC" / "rcm_mc" / "server.py"
UI_DIR = REPO_ROOT / "RCM_MC" / "rcm_mc" / "ui"


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
_REDIRECT_RE = re.compile(
    r"self\._redirect\(|"
    r"send_response\(\s*HTTPStatus\.MOVED_PERMANENTLY|"
    r"send_response\(\s*HTTPStatus\.FOUND|"
    r"send_response\(\s*HTTPStatus\.SEE_OTHER|"
    r"send_response\(\s*HTTPStatus\.TEMPORARY_REDIRECT|"
    r"send_response\(\s*HTTPStatus\.PERMANENT_REDIRECT|"
    r"send_response\(\s*30[178]\b"
)
# Many dispatcher blocks delegate to a self._route_<name>() method that
# itself does the import + render_* + chartis_shell call. Follow those
# one level so the classifier reaches the actual renderer.
_ROUTE_CALL_RE = re.compile(r"self\._route_([A-Za-z_][A-Za-z0-9_]*)\s*\(")
# `shell(` preceded by start-of-token (not `chartis_shell` or `_shell`)
_SHELL_CALL_RE = re.compile(r"(?<![A-Za-z0-9_])shell\s*\(")

# Markers that an inline block is serving JSON, a file, or a 204/no-body
# response — i.e. legitimately not a UI page. Used to split the "unknown"
# bucket into an "api/non-ui" sub-bucket so the v5 compliance percentage
# reflects only routes that are SUPPOSED to render HTML.
_JSON_MARKERS = (
    "_send_json(",
    "send_json(",
    "application/json",
    "json.dumps(",
    "self.wfile.write(json.",
)
_FILE_MARKERS = (
    "_send_file(",
    "_send_static(",
    "_serve_static",
    "send_response(HTTPStatus.NO_CONTENT)",
    "image/png",
    "image/svg",
    "text/css",
    "application/octet-stream",
)
_HEALTH_PATHS = {"/health", "/healthz", "/api/health", "/api/health/deep"}


@_lru_cache(maxsize=1)
def _shell_shim_is_chartis() -> bool:
    """True iff ``rcm_mc/ui/_ui_kit.py``'s ``shell`` already delegates
    to ``chartis_shell``. When this is true (Phase 1C of the v5
    campaign), every legacy ``shell()`` caller is *runtime*-compliant
    with v5 chrome — the classifier should treat them as v5 even if
    the source still spells ``shell``."""
    p = REPO_ROOT / "RCM_MC" / "rcm_mc" / "ui" / "_ui_kit.py"
    if not p.is_file():
        return False
    text = p.read_text(encoding="utf-8", errors="replace")
    # Look for `def shell(...): ... return chartis_shell(...)`
    m = re.search(
        r"^def shell\(",
        text, flags=re.M,
    )
    if not m:
        return False
    body_start = m.end()
    next_def = re.search(r"^def [a-zA-Z_]\w*\(", text[body_start:], flags=re.M)
    body = (
        text[body_start: body_start + next_def.start()]
        if next_def else text[body_start:]
    )
    return "chartis_shell(" in body or "from ._chartis_kit import chartis_shell" in text

# Print / export renderers — intentionally bespoke (self-contained HTML,
# @media print styles, designed for PDF generation). Wrapping these in
# chartis_shell would break their print contract, so they're excluded
# from the v5 compliance denominator the same way api/static are.
_PRINT_PATH_PREFIXES = (
    "/diligence/ic-memo",
    "/diligence/synthesis",
    "/exports/",
    "/outputs/",
    "/api/docs",  # SwaggerUI — third-party HTML
    "/digest/morning",  # email-preview HTML; same body as SMTP send
)
_PRINT_FN_HINTS = (
    "render_memo_html",
    "render_html_binder",
    "render_swagger_ui",
    "render_lp_update_html",
    "@media print",
)


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
    'dashboard_page' or 'chartis.app_page'. Also accepts the
    synthetic '(render_<fn>)' marker emitted by _resolve_renderer
    when the dispatcher uses a bare ``render_<fn>()`` call — in
    that case we grep the repo for the function definition and
    classify the file that owns it."""
    if not renderer_module:
        return ("unknown", "no")
    # synthetic marker: (render_<fn>) — locate the function
    if renderer_module.startswith("(render_") and renderer_module.endswith(")"):
        fn_name = renderer_module[1:-1]  # strip parens
        path = _find_function_source(fn_name)
        if path is None:
            return ("unknown", "no")
        text = path.read_text(encoding="utf-8", errors="replace")
        return _classify_text(text, path)
    if renderer_module.startswith("chartis."):
        path = UI_DIR / "chartis" / (renderer_module.split(".", 1)[1] + ".py")
    else:
        path = UI_DIR / (renderer_module.replace(".", "/") + ".py")
    if not path.is_file():
        return ("unknown", "no")
    text = path.read_text(encoding="utf-8", errors="replace")
    return _classify_text(text, path)


def _classify_text(text: str, path: Path) -> tuple[str, str]:
    """Inspect the source of a renderer file and return
    (v3_status, packet_status)."""
    # v3 marker: chartis_shell from editorial OR file is in chartis/
    try:
        rel = path.resolve().relative_to(UI_DIR)
        in_chartis = str(rel).startswith("chartis/")
    except ValueError:
        in_chartis = False
    if in_chartis:
        v3 = "v3"
    elif "chartis_shell" in text or "_chartis_kit_editorial" in text:
        v3 = "v3"
    elif (
        "from ._ui_kit import shell" in text
        or "from .._ui_kit import shell" in text
        or _SHELL_CALL_RE.search(text)
    ):
        # Phase 1C: shell() shim routes to chartis_shell at runtime.
        v3 = "v3" if _shell_shim_is_chartis() else "legacy"
    else:
        v3 = "bespoke"
    # Packet marker
    if "get_or_build_packet" in text or "DealAnalysisPacket" in text:
        packet = "yes"
    else:
        packet = "no"
    return (v3, packet)


@_lru_cache(maxsize=None)
def _find_function_source(fn_name: str) -> "Path | None":
    """Search the rcm_mc package for ``def <fn_name>(`` and return
    the file path it lives in, or None if not found.

    Used when the dispatcher block calls a bare ``render_X()`` we
    couldn't resolve to a module name. Cached so repeated lookups
    on the same function are free.
    """
    needle = f"def {fn_name}("
    pkg_root = REPO_ROOT / "RCM_MC" / "rcm_mc"
    if not pkg_root.is_dir():
        return None
    for py in pkg_root.rglob("*.py"):
        try:
            if needle in py.read_text(encoding="utf-8", errors="replace"):
                return py
        except OSError:
            continue
    return None


def _method_body(src: str, method_name: str) -> str:
    """Return the body of ``def <method_name>(`` in server.py, or ''
    if it can't be found. Used to follow ``self._route_<name>()``
    delegations one level for renderer resolution."""
    pat = re.compile(
        rf"^    def {re.escape(method_name)}\(", re.M
    )
    m = pat.search(src)
    if not m:
        return ""
    end_re = re.compile(r"^    def [a-zA-Z_]\w*\(", re.M)
    n = end_re.search(src, m.end())
    return src[m.start(): n.start() if n else len(src)]


def _resolve_renderer(
    body: str, *, server_src: str = "", _depth: int = 0
) -> str:
    """Pick a single representative renderer module for an if-body.

    Heuristic: first .ui import wins. If none, look for render_<name>
    calls. If the body just calls ``self._route_<name>()`` and we
    have the full server source, follow into that method. Recurse up
    to 3 levels deep so chains like
    ``_route_login_page → _route_login_page_editorial`` resolve.
    """
    imports = _UI_IMPORT_RE.findall(body)
    if imports:
        return imports[0]
    if _REDIRECT_RE.search(body):
        return "(redirect)"
    renders = _RENDER_CALL_RE.findall(body)
    if renders:
        return f"(render_{renders[0]})"
    if server_src and _depth < 3:
        for route_name in _ROUTE_CALL_RE.findall(body):
            inner = _method_body(server_src, f"_route_{route_name}")
            if not inner:
                continue
            inner_imports = _UI_IMPORT_RE.findall(inner)
            if inner_imports:
                return inner_imports[0]
            inner_renders = _RENDER_CALL_RE.findall(inner)
            if inner_renders:
                return f"(render_{inner_renders[0]})"
            if "chartis_shell" in inner:
                return f"(_route_{route_name} -> chartis_shell)"
            # Match the legacy shell helper in any call context:
            # ``shell(``, ``(shell(``, ``=shell(``, etc. — server.py's
            # top-level `from .ui._ui_kit import shell` lets the inner
            # method call it without a re-import in the local body.
            if _SHELL_CALL_RE.search(inner) or "from ._ui_kit import shell" in inner:
                return f"(_route_{route_name} -> shell)"
            # Followed method is a JSON endpoint — propagate so the
            # outer route gets classified as `api` not `unknown`.
            if any(m in inner for m in _JSON_MARKERS):
                return f"(_route_{route_name} -> json)"
            if any(m in inner for m in _FILE_MARKERS):
                return f"(_route_{route_name} -> file)"
            # Recurse: this method itself just calls another _route_*
            recursed = _resolve_renderer(
                inner, server_src=server_src, _depth=_depth + 1
            )
            if recursed != "(inline)":
                return recursed
    return "(inline)"


def _classify_inline_route(pattern: str, body: str) -> str:
    """Sub-classify a route whose body has no .ui import + no
    render_* call + no _redirect, returning one of:

      "api"      — JSON endpoint or file/no-content response
      "static"   — static file serve
      "health"   — health/heartbeat endpoint
      "print"    — print/PDF/export endpoint (self-contained HTML)
      "ui"       — none of the above; presumed inline HTML page

    The non-"ui" rows are excluded from the v5 compliance
    denominator because they have no chartis chrome to migrate.
    """
    if pattern in _HEALTH_PATHS:
        return "health"
    if pattern.startswith("/static") or pattern == "/favicon.ico":
        return "static"
    if any(pattern.startswith(p) for p in _PRINT_PATH_PREFIXES):
        return "print"
    if pattern.startswith("/api/") or pattern == "/api":
        return "api"
    if any(m in body for m in _JSON_MARKERS):
        return "api"
    if any(m in body for m in _FILE_MARKERS):
        return "static"
    # No-op GET handler that just falls through (`pass # handled in
    # POST`) — has no UI surface, classify as api so it doesn't drag
    # the compliance percentage.
    body_no_comments = re.sub(r"#.*", "", body).strip()
    inner_lines = [
        ln.strip() for ln in body_no_comments.splitlines()
        if ln.strip() and not ln.strip().startswith(("if ", "elif ", "else"))
    ]
    if inner_lines and all(ln in ("pass",) for ln in inner_lines):
        return "api"
    return "ui"


def _emit_route_row(r: Route, *, v5_mode: bool) -> str:
    pat = r.pattern.replace("|", "\\|")
    status = "v5" if v5_mode and r.v3_status == "v3" else r.v3_status
    return (
        f"| `{pat}` | {r.match_kind} | `{r.renderer}` | "
        f"{status} | {r.packet} |"
    )


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    v5_mode = "--v5" in argv
    out_path = REPO_ROOT / "docs" / (
        "V5_ROUTE_INVENTORY.md" if v5_mode else "V3_ROUTE_INVENTORY.md"
    )
    src = SERVER_PY.read_text(encoding="utf-8")
    dispatcher = _slice_dispatcher(src)
    blocks = _extract_blocks(dispatcher)

    routes: list[Route] = []
    for pattern, kind, body in blocks:
        renderer = _resolve_renderer(body, server_src=src)
        if renderer == "(redirect)":
            v3, pkt = "redirect", "n/a"
        elif renderer.endswith("-> chartis_shell)"):
            # _route_* method delegates to chartis_shell directly
            v3, pkt = "v3", "no"
        elif renderer.endswith("-> json)"):
            v3, pkt = "api", "n/a"
        elif renderer.endswith("-> file)"):
            v3, pkt = "static", "n/a"
        elif renderer.endswith("-> shell)"):
            # Phase 1C: `_ui_kit.shell` is a chartis_shell shim, so
            # legacy callers are runtime-compliant with v5 chrome.
            # Treat as v3 (chartis-reachable) when the shim is in
            # place; flag as legacy only if the shim hasn't been
            # installed yet.
            v3 = "v3" if _shell_shim_is_chartis() else "legacy"
            pkt = "no"
        elif renderer.startswith("(render_"):
            # render_<fn>() bare call — resolve via repo grep
            v3, pkt = _classify_renderer(renderer)
            # Even if we found the source and it's bespoke, check if
            # the route pattern says "print/export" — those are
            # intentionally bare and excluded from UI surface.
            if any(pattern.startswith(p) for p in _PRINT_PATH_PREFIXES):
                v3, pkt = "print", "n/a"
            else:
                fn_name = renderer[1:-1]  # render_<fn>
                if any(h == fn_name for h in _PRINT_FN_HINTS):
                    v3, pkt = "print", "n/a"
            if v3 == "unknown":
                sub = _classify_inline_route(pattern, body)
                if sub == "api":
                    v3, pkt = "api", "n/a"
                elif sub == "static":
                    v3, pkt = "static", "n/a"
                elif sub == "health":
                    v3, pkt = "health", "n/a"
                elif sub == "print":
                    v3, pkt = "print", "n/a"
        elif renderer.startswith("("):
            sub = _classify_inline_route(pattern, body)
            if sub == "api":
                v3, pkt = "api", "n/a"
            elif sub == "static":
                v3, pkt = "static", "n/a"
            elif sub == "health":
                v3, pkt = "health", "n/a"
            elif sub == "print":
                v3, pkt = "print", "n/a"
            else:
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
    api_count = sum(1 for r in routes if r.v3_status == "api")
    static_count = sum(1 for r in routes if r.v3_status == "static")
    health_count = sum(1 for r in routes if r.v3_status == "health")
    print_count = sum(1 for r in routes if r.v3_status == "print")
    packet_yes = sum(1 for r in routes if r.packet == "yes")

    # UI surface = total − non-UI buckets. Compliance is measured
    # against this denominator, since api/static/health/print/redirect
    # rows have no HTML chrome to migrate.
    non_ui = (
        api_count + static_count + health_count
        + print_count + redirect_count
    )
    ui_surface = total - non_ui
    pct = lambda n: f"{(100 * n / total):.0f}%" if total else "n/a"
    pct_ui = lambda n: (
        f"{(100 * n / ui_surface):.0f}%" if ui_surface else "n/a"
    )

    chartis_label = (
        "v5 (chartis_shell or under ui/chartis/)"
        if v5_mode
        else "v3 (chartis_shell or under ui/chartis/)"
    )
    caveat_chrome = (
        "`v5` means the renderer *reaches* the Chartis / v5 design "
        "chrome (same mechanical bucket as legacy `v3` in the "
        "generator) — it does not prove every v5 spec detail "
        "(tabular-nums, ISO dates, 2-decimal financials, `#1F4E78` "
        "accent) is honored."
        if v5_mode
        else (
            "- Classification is heuristic. `v3` means the renderer "
            "*reaches* the v3 chrome — it does not mean every aspect of "
            "the v3 spec (tabular-nums, ISO dates, 2-decimal financials, "
            "`#1F4E78` accent) is honored. Audit before claiming a page "
            "is fully migrated."
        )
    )
    title = "# V5 Route Inventory" if v5_mode else "# V3 Route Inventory"
    gen_tool = (
        "`RCM_MC/tools/v3_route_inventory.py --v5`"
        if v5_mode
        else "`RCM_MC/tools/v3_route_inventory.py`"
    )
    status_col = "v5 status" if v5_mode else "v3 status"

    md_lines = [
        title,
        "",
        f"Generated by {gen_tool} from "
        f"`RCM_MC/rcm_mc/server.py`. Re-run after any migration commit.",
        "",
        f"**Total routes mapped:** {total}",
        f"**UI surface (excludes api / static / health / redirect):** "
        f"{ui_surface}",
        "",
        "## Compliance summary",
        "",
        f"| Status | Count | % of total | % of UI surface |",
        f"|---|---|---|---|",
        f"| {chartis_label} | {v3_count} | {pct(v3_count)} | "
        f"{pct_ui(v3_count)} |",
        f"| legacy (`shell()` from `_ui_kit` only) | {legacy_count} | "
        f"{pct(legacy_count)} | {pct_ui(legacy_count)} |",
        f"| bespoke (no shell — direct HTML) | {bespoke_count} | "
        f"{pct(bespoke_count)} | {pct_ui(bespoke_count)} |",
        f"| unknown / unresolved (UI route, no renderer) | "
        f"{unknown_count} | {pct(unknown_count)} | {pct_ui(unknown_count)} |",
        f"| api / json (excluded from UI surface) | {api_count} | "
        f"{pct(api_count)} | — |",
        f"| static / file (excluded from UI surface) | {static_count} | "
        f"{pct(static_count)} | — |",
        f"| health / heartbeat (excluded from UI surface) | "
        f"{health_count} | {pct(health_count)} | — |",
        f"| print / export (excluded from UI surface) | {print_count} | "
        f"{pct(print_count)} | — |",
        f"| redirect (excluded from UI surface) | {redirect_count} | "
        f"{pct(redirect_count)} | — |",
        "",
        f"**Packet-driven (calls `get_or_build_packet` or imports "
        f"`DealAnalysisPacket`):** {packet_yes} of {total} ({pct(packet_yes)})",
        "",
        "## Caveats",
        "",
    ]
    if v5_mode:
        md_lines.append(f"- {caveat_chrome}")
    else:
        md_lines.append(caveat_chrome)
    md_lines.extend(
        [
        "- The `unknown` bucket is overwhelmingly inline routes "
        "(static files, JSON endpoints, redirects with no UI module) "
        "— those legitimately have no renderer to classify.",
        "- Some routes have multiple URL aliases (e.g. `/`, "
        "`/index.html`); each alias is listed separately so the "
        "table shows the surface area a partner can hit.",
        "",
        "## Routes",
        "",
        f"| URL pattern | Match | Renderer | {status_col} | Packet-driven |",
        "|---|---|---|---|---|",
        ]
    )
    for r in routes:
        md_lines.append(_emit_route_row(r, v5_mode=v5_mode))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    sys.stdout.write(f"wrote {out_path.relative_to(REPO_ROOT)}\n")
    chrome_key = "v5-chrome" if v5_mode else "v3"
    sys.stdout.write(
        f"  total={total} {chrome_key}={v3_count} legacy={legacy_count} "
        f"bespoke={bespoke_count} redirect={redirect_count} "
        f"unknown={unknown_count} packet-driven={packet_yes}\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
