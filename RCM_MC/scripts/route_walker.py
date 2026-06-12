#!/usr/bin/env python3
"""Route walker — smoke-render every GET page route and record evidence.

Session tooling for the autonomous improvement loop: walks every exact-match
page route extracted from server.py, GETs it against a running dev server, and
emits a TSV of evidence per route: HTTP status, byte size, and which
data-basis markers the page carries (ILLUSTRATIVE chip, HCRIS chip, gap dots,
'No data' empty-state, literal 'nan'/'None' leaks, Traceback text). This is
the mechanical half of PAGE_INVENTORY grading and the render check for the
every-4th-iteration regression sweep.

Usage:
    python3 scripts/route_walker.py --base http://127.0.0.1:8830 \
        [--routes /tmp/routes_all.txt] [--out /tmp/route_walk.tsv]

Routes needing an id are parameterised via _SAMPLE_SUFFIX (seeded demo ids).
"""
from __future__ import annotations

import argparse
import re
import sys
import urllib.request

# Exact-match page routes that need a sample entity to render meaningfully.
_SAMPLE_SUFFIX = {
    "/deal": "/ccf",
    "/analysis": "/ccf",
    "/hospital": "/450358",       # seeded HCRIS CCN (Texas)
    "/cohort": "/all",
    "/best": "/ccf",
    "/competitive-intel": "/450358",
    "/bayesian/hospital": "/450358",
}

_MARKERS = [
    ("illustrative", "ILLUSTRATIVE"),
    ("hcris", "HCRIS PUBLIC DATA"),
    ("gap_dot", "ck-gap-dot"),
    ("entered", ">ENTERED</span>"),
    ("predicted", ">PREDICTED</span>"),
    ("nan_leak", ">nan<"),
    ("none_leak", ">None<"),
    ("traceback", "Traceback (most recent call last)"),
]


def deal_cookie(deal_id: str, *, name: str = "", state: str = "TX",
                ccn: str = "450358") -> str:
    """Build the pedesk_active_deal_meta cookie the server's
    ``_active_deal_meta`` reader expects — the walker's cookie-context
    mode walks every page AS IF a partner had set an active deal, so
    prefill paths (CIM / roll-up / screener state scoping) render under
    test instead of only on a partner's machine."""
    import json
    import urllib.parse as _up
    payload = _up.quote(json.dumps(
        {"id": deal_id, "name": name or deal_id,
         "state": state, "ccn": ccn}))
    return f"pedesk_active_deal_meta={payload}"


def walk(base: str, routes: list[str], cookie: str = "") -> list[dict]:
    rows = []
    for r in routes:
        url = base + r + _SAMPLE_SUFFIX.get(r, "")
        row = {"route": r, "status": 0, "bytes": 0}
        headers = {"Cookie": cookie} if cookie else {}
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                body = resp.read().decode("utf-8", "replace")
                row["status"] = resp.status
                row["bytes"] = len(body)
                for key, needle in _MARKERS:
                    row[key] = int(needle in body)
        except Exception as exc:  # noqa: BLE001 — record, keep walking
            row["status"] = getattr(exc, "code", -1)
            row["error"] = str(exc)[:60]
        rows.append(row)
    return rows


def _discover_routes() -> list[str]:
    """Pull the exact-match GET page routes from the server itself, so the
    walker is self-contained (no pre-written routes file). Used by --discover
    and the CI smoke job — keeps the catalog automatic and drift-free."""
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from rcm_mc.server import RCMHandler
    return list(RCMHandler._discover_all_routes())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8830")
    ap.add_argument("--routes", default="/tmp/routes_all.txt")
    ap.add_argument("--out", default="/tmp/route_walk.tsv")
    ap.add_argument("--discover", action="store_true",
                    help="discover routes from the server module instead of "
                         "reading --routes (self-contained; used in CI)")
    ap.add_argument("--fail-on-leak", action="store_true",
                    help="also exit non-zero if any page leaks a literal "
                         "nan/None into rendered HTML")
    ap.add_argument("--deal-cookie", default="", metavar="DEAL_ID",
                    help="walk with the active-deal context cookie set to "
                         "this deal id (state TX / CCN 450358 sample meta) — "
                         "exercises the prefill paths (CIM, roll-up, "
                         "screener scoping) that only run with a deal set")
    args = ap.parse_args()

    if args.discover:
        raw = _discover_routes()
    else:
        with open(args.routes) as f:
            raw = [ln.strip() for ln in f]
    routes = [ln for ln in raw
              if ln and not ln.startswith("/api")
              and not ln.rstrip("/").endswith("/X")
              and "webhook" not in ln]
    # de-dup trailing-slash twins
    seen, ordered = set(), []
    for r in routes:
        k = r.rstrip("/") or "/"
        if k not in seen:
            seen.add(k)
            ordered.append(k)

    rows = walk(args.base, ordered,
                cookie=(deal_cookie(args.deal_cookie)
                        if args.deal_cookie else ""))
    cols = ["route", "status", "bytes"] + [k for k, _ in _MARKERS] + ["error"]
    with open(args.out, "w") as f:
        f.write("\t".join(cols) + "\n")
        for row in rows:
            f.write("\t".join(str(row.get(c, "")) for c in cols) + "\n")

    n_ok = sum(1 for r in rows if r["status"] == 200)
    n_err = sum(1 for r in rows if r["status"] not in (200, 302, 303))
    n_tb = sum(1 for r in rows if r.get("traceback"))
    n_leak = sum(1 for r in rows if r.get("nan_leak") or r.get("none_leak"))
    print(f"walked {len(rows)} routes: {n_ok} ok, {n_err} non-2xx/3xx, "
          f"{n_tb} tracebacks, {n_leak} nan/None leaks -> {args.out}")
    if n_tb:
        print("FAIL: tracebacks on " + ", ".join(
            r["route"] for r in rows if r.get("traceback")), file=sys.stderr)
    if args.fail_on_leak and n_leak:
        print("FAIL: nan/None leaks on " + ", ".join(
            r["route"] for r in rows
            if r.get("nan_leak") or r.get("none_leak")), file=sys.stderr)
    bad = n_tb or (args.fail_on_leak and n_leak)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
