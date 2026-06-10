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


def walk(base: str, routes: list[str]) -> list[dict]:
    rows = []
    for r in routes:
        url = base + r + _SAMPLE_SUFFIX.get(r, "")
        row = {"route": r, "status": 0, "bytes": 0}
        try:
            with urllib.request.urlopen(url, timeout=45) as resp:
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8830")
    ap.add_argument("--routes", default="/tmp/routes_all.txt")
    ap.add_argument("--out", default="/tmp/route_walk.tsv")
    args = ap.parse_args()

    with open(args.routes) as f:
        routes = [ln.strip() for ln in f
                  if ln.strip() and not ln.startswith("/api")
                  and not ln.strip().rstrip("/").endswith("/X")
                  and "webhook" not in ln]
    # de-dup trailing-slash twins
    seen, ordered = set(), []
    for r in routes:
        k = r.rstrip("/") or "/"
        if k not in seen:
            seen.add(k)
            ordered.append(k)

    rows = walk(args.base, ordered)
    cols = ["route", "status", "bytes"] + [k for k, _ in _MARKERS] + ["error"]
    with open(args.out, "w") as f:
        f.write("\t".join(cols) + "\n")
        for row in rows:
            f.write("\t".join(str(row.get(c, "")) for c in cols) + "\n")

    n_ok = sum(1 for r in rows if r["status"] == 200)
    n_err = sum(1 for r in rows if r["status"] not in (200, 302, 303))
    n_tb = sum(1 for r in rows if r.get("traceback"))
    print(f"walked {len(rows)} routes: {n_ok} ok, {n_err} non-2xx/3xx, "
          f"{n_tb} tracebacks -> {args.out}")
    return 0 if n_tb == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
