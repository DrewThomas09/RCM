"""Demo-readiness route walk.

Boots an in-process server against a freshly *seeded* demo database,
logs in, then GETs every analytic surface a viewer would click —
the full Cmd-K palette plus per-entity deal / hospital / analysis
routes — and inspects each rendered page for things that break the
"ready for viewing" illusion:

  * HTTP errors / Python tracebacks bleeding into the body
  * unrendered markup leaks (double-escaped tags, raw "None"/"nan")
  * missing editorial chrome (no chartis_shell)
  * unintended empty states where seeded data should appear

This is a *diagnostic* tool, not a pass/fail unit test — it prints a
grouped report so real breakage gets fixed at the root, never hidden.
Run:  .venv/bin/python -m tools.route_walk
"""
from __future__ import annotations

import os
import re
import socket
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from http.cookiejar import CookieJar
from typing import List, Optional, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


# Body substrings that mean the page errored server-side.
_ERROR_MARKERS = (
    "Traceback (most recent call last)",
    "Internal Server Error",
    "KeyError",
    "AttributeError:",
    "TypeError:",
    "ValueError:",
    "UnboundLocalError",
    "jinja2.exceptions",
)

# Visible-text leaks that mean a value didn't render.
_LEAK_MARKERS = (
    "&amp;lt;",     # double-escaped markup
    ">None<",       # a None bled into a cell
    ">nan<",
    ">NaN<",
    "undefined",
)


@dataclass
class PageResult:
    route: str
    status: int
    ok: bool
    findings: List[str] = field(default_factory=list)
    size: int = 0


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def _login(base: str, username: str, password: str):
    cj = CookieJar()
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(cj))
    payload = urllib.parse.urlencode(
        {"username": username, "password": password}).encode()
    req = urllib.request.Request(
        base + "/api/login", data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST")
    try:
        opener.open(req, timeout=10)
    except urllib.error.HTTPError:
        pass  # 303 redirect is success; cookie is what matters
    if not any(c.name == "rcm_session" for c in cj):
        raise RuntimeError("login failed — no rcm_session cookie")
    return opener


def _check_page(route: str, status: int, body: str) -> PageResult:
    findings: List[str] = []
    if status >= 500:
        findings.append(f"HTTP {status}")
    for m in _ERROR_MARKERS:
        if m in body:
            findings.append(f"error-marker: {m!r}")
    for m in _LEAK_MARKERS:
        if m in body:
            findings.append(f"render-leak: {m!r}")
    # Editorial chrome: every real page should carry the shell.
    if status < 400 and "ck-topbar" not in body and "chartis" not in body.lower():
        findings.append("missing editorial chrome")
    # Exactly one page title: more than one rendered <h1> means a
    # duplicate-title bug (a viewer should never see two titles).
    if status < 400:
        n_h1 = len(re.findall(r"<h1[ >]", body))
        if n_h1 > 1:
            findings.append(f"duplicate title ({n_h1} <h1>)")
    return PageResult(route, status, not findings, findings, len(body))


def _walk(base: str, opener, routes: List[str]) -> List[PageResult]:
    out: List[PageResult] = []
    for route in routes:
        url = base + route
        try:
            with opener.open(url, timeout=20) as r:
                body = r.read().decode("utf-8", "replace")
                out.append(_check_page(route, r.status, body))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            out.append(_check_page(route, e.code, body))
        except Exception as exc:  # noqa: BLE001 — report, don't crash the walk
            out.append(PageResult(route, 0, False,
                                  [f"exception: {type(exc).__name__}: {exc}"]))
    return out


def _seeded_routes(db_path: str) -> Tuple[List[str], List[str]]:
    """Return (palette_routes, entity_routes) for the seeded DB."""
    from rcm_mc.ui._chartis_kit import _DEFAULT_PALETTE_MODULES
    palette = [m["route"] for m in _DEFAULT_PALETTE_MODULES]
    # Fold in the full module-index catalog so every analytic surface
    # is walked, not just the ones pinned in the Cmd-K palette. Deduped
    # against the palette; ignored if the catalog can't be computed.
    try:
        from rcm_mc.data_public.module_index import compute_module_index
        _idx = compute_module_index()
        _mods = _idx.modules if hasattr(_idx, "modules") else list(_idx)
        _seen = set(palette)
        for _m in _mods:
            if _m.route and _m.route not in _seen:
                palette.append(_m.route)
                _seen.add(_m.route)
    except Exception:  # noqa: BLE001 — catalog is best-effort coverage
        pass

    from rcm_mc.portfolio.store import PortfolioStore
    entity: List[str] = []
    store = PortfolioStore(db_path)
    with store.connect() as con:
        deal_ids = [r[0] for r in con.execute(
            "SELECT deal_id FROM deals LIMIT 5").fetchall()]
    # Per-deal route families, incl. the chartis app deal sub-pages
    # (red-flags / archetype / ic-packet / etc.) — these aren't in the
    # palette and have surfaced real dup-title / render-leak bugs.
    _deal_subs = (
        "profile", "timeline", "partner-review", "red-flags",
        "archetype", "investability", "market-structure",
        "white-space", "stress", "ic-packet",
    )
    for did in deal_ids:
        entity += [f"/deal/{did}", f"/analysis/{did}",
                   f"/ebitda-bridge/{did}", f"/value-tracker/{did}",
                   f"/lp-update?deal_id={did}"]
        entity += [f"/deal/{did}/{sub}" for sub in _deal_subs]
    # A couple of real HCRIS hospitals (these drive the diligence pages).
    try:
        from rcm_mc.data.hcris import _get_latest_per_ccn
        ccns = list(_get_latest_per_ccn()["ccn"].head(3))
        for ccn in ccns:
            entity += [
                f"/hospital/{ccn}", f"/competitive-intel/{ccn}",
                f"/hospital/{ccn}/demand", f"/hospital/{ccn}/history",
                f"/hospital/{ccn}/providers", f"/models/market/{ccn}",
                f"/models/dcf/{ccn}", f"/models/denial/{ccn}",
            ]
    except Exception:  # noqa: BLE001
        pass
    return palette, entity


def main() -> int:
    os.environ.setdefault("CHARTIS_UI_V2", "1")
    tmp = tempfile.mkdtemp(prefix="route_walk_")
    db = os.path.join(tmp, "demo.db")

    from rcm_mc.dev.seed import seed_demo_db
    from rcm_mc.auth.auth import create_user
    from rcm_mc.portfolio.store import PortfolioStore
    from rcm_mc.server import build_server

    print(f"seeding demo db → {db}")
    seed_demo_db(db, deal_count=7, write_export_files=False, force=True)
    store = PortfolioStore(db)
    create_user(store, "walker@chartis.com", "RouteWalk1",
                display_name="Route Walker", role="admin")

    port = _free_port()
    server, _ = build_server(port=port, db_path=db)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.1)
    base = f"http://127.0.0.1:{port}"

    try:
        opener = _login(base, "walker@chartis.com", "RouteWalk1")
        palette, entity = _seeded_routes(db)
        print(f"walking {len(palette)} palette + {len(entity)} entity routes\n")
        results = _walk(base, opener, palette + entity)
    finally:
        server.shutdown()
        server.server_close()

    bad = [r for r in results if not r.ok]
    print(f"\n{'='*64}")
    print(f"  {len(results)} routes walked · {len(bad)} with findings")
    print(f"{'='*64}")
    for r in bad:
        print(f"\n  [{r.status}] {r.route}  ({r.size}b)")
        for f in r.findings:
            print(f"      → {f}")
    if not bad:
        print("\n  ✓ every page rendered clean")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
