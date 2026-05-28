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
    # Scan only VISIBLE content for error/leak markers — strip <script> and
    # <style> first. Otherwise bare markers like "undefined" match legitimate
    # inline JS (e.g. `signal: ctrl ? ctrl.signal : undefined`) on every page
    # and drown the report in false positives.
    visible = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", "", body,
                     flags=re.S | re.I)
    for m in _ERROR_MARKERS:
        if m in visible:
            findings.append(f"error-marker: {m!r}")
    for m in _LEAK_MARKERS:
        if m in visible:
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
    # One explanatory block under the title: a page should not stack a
    # bespoke ck-*-explainer deck AND the canonical ck-page-explainer.
    if status < 400:
        n_exp = len(re.findall(r'<p class="ck-[a-z]+-explainer"', body))
        if n_exp > 1:
            findings.append(f"duplicate explainer ({n_exp} blocks)")
    return PageResult(route, status, not findings, findings, len(body))


def _collect_links(body: str, sink: set) -> None:
    """Harvest internal <a href> targets worth integrity-checking.

    Skips API/static/export-file links and JS-template hrefs (those carry
    `' +`/quotes/spaces from in-page string concatenation).
    """
    for m in re.finditer(r'href="(/[^"#?][^"]*)"', body):
        h = m.group(1).split("?")[0].split("#")[0]
        if h.startswith(("/api", "/static", "/logout", "/exports/")):
            continue
        if "'" in h or " " in h or "+" in h:  # JS-built href fragment
            continue
        sink.add(h)


def _walk(base: str, opener, routes: List[str],
          link_sink: Optional[set] = None) -> List[PageResult]:
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
            body = ""
        if link_sink is not None and body:
            _collect_links(body, link_sink)
    return out


def _check_links(base: str, opener, links: set) -> List[tuple]:
    """GET each unique internal link; return [(status, href)] for any
    that 404 / 500 / fail — i.e. broken nav a viewer would hit."""
    dead: List[tuple] = []
    for h in sorted(links):
        try:
            with opener.open(base + h, timeout=20) as r:
                st = r.status
        except urllib.error.HTTPError as e:
            st = e.code
        except Exception:  # noqa: BLE001
            st = -1
        if st in (404, 500, -1):
            dead.append((st, h))
    return dead


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
    # A few corpus-deal detail pages (/library/<source_id>) — the deals
    # library + comparables tables link here. seed_075 carries a
    # JSON-string payer_mix (a past 500), so keep it in coverage.
    try:
        from rcm_mc.ui.data_public.deals_library_page import (
            _get_all_seed_deals,
        )
        sids = [str(d.get("source_id", ""))
                for d in _get_all_seed_deals()[:3]]
        for sid in sids + ["seed_075"]:
            if sid:
                entity.append(f"/library/{sid}")
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

    seen_links: set = set()
    try:
        opener = _login(base, "walker@chartis.com", "RouteWalk1")
        palette, entity = _seeded_routes(db)
        print(f"walking {len(palette)} palette + {len(entity)} entity routes\n")
        results = _walk(base, opener, palette + entity, link_sink=seen_links)
        # Link integrity: every internal <a href> a viewer can click must
        # resolve (no 404/500). This caught the missing /library/<id>
        # route + dead /admin and /diligence/ebitda-bridge nav links.
        print(f"checking {len(seen_links)} internal links\n")
        dead_links = _check_links(base, opener, seen_links)
    finally:
        server.shutdown()
        server.server_close()

    # Second pass — first-run resilience: every non-entity page must
    # degrade gracefully (clean editorial empty states, no 500s / leaks)
    # against an *empty* database, not just the seeded demo.
    edb = os.path.join(tmp, "empty.db")
    estore = PortfolioStore(edb)
    estore.init_db()
    create_user(estore, "walker@chartis.com", "RouteWalk1",
                display_name="Route Walker", role="admin")
    eport = _free_port()
    eserver, _ = build_server(port=eport, db_path=edb)
    et = threading.Thread(target=eserver.serve_forever, daemon=True)
    et.start()
    time.sleep(0.1)
    ebase = f"http://127.0.0.1:{eport}"
    try:
        eopener = _login(ebase, "walker@chartis.com", "RouteWalk1")
        empty_routes, _ = _seeded_routes(edb)  # palette+modules; no deals
        print(f"\nempty-db pass: walking {len(empty_routes)} routes\n")
        empty_results = _walk(ebase, eopener, empty_routes)
    finally:
        eserver.shutdown()
        eserver.server_close()

    bad = [r for r in results if not r.ok]
    ebad = [r for r in empty_results if not r.ok]
    print(f"\n{'='*64}")
    print(f"  seeded: {len(results)} routes · {len(bad)} findings   "
          f"empty-db: {len(empty_results)} routes · {len(ebad)} findings   "
          f"dead links: {len(dead_links)}")
    print(f"{'='*64}")
    for tag, rs in (("seeded", bad), ("empty-db", ebad)):
        for r in rs:
            print(f"\n  [{tag}][{r.status}] {r.route}  ({r.size}b)")
            for f in r.findings:
                print(f"      → {f}")
    for st, h in dead_links:
        print(f"\n  [link][{st}] {h}")
    ok = not bad and not ebad and not dead_links
    if ok:
        print("\n  ✓ every page rendered clean + all internal links resolve")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
