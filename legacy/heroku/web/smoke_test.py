"""End-to-end smoke test — run after every deploy.

Exercises the user-visible happy path:
  1. GET /healthz        → 200 "ok"
  2. POST /login         → 302 redirect + session cookie
  3. GET  /home          → 200 (verifies session works)
  4. GET  /diligence/thesis-pipeline?dataset=<fixture>
                         → 200 (triggers a fast analysis inline)
  5. (optional) POST async job → poll status → verify completion

Usage:
    # Against a running local server:
    python -m web.smoke_test http://localhost:8080

    # Against Heroku:
    python -m web.smoke_test https://your-app.herokuapp.com

    # Reads credentials from ADMIN_USERNAME + ADMIN_PASSWORD env vars;
    # override via --user/--pass flags for one-off tests.

Exit codes:
    0 — all checks passed
    1 — any check failed (prints which one to stderr)
    2 — CLI usage error

Stdlib-only (urllib + http.cookiejar + argparse + json).
"""
from __future__ import annotations

import argparse
import http.cookiejar
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional, Tuple


DEFAULT_FIXTURE = "hospital_04_mixed_payer"  # Small CCD fixture; runs in <2s.


# ── Helpers ─────────────────────────────────────────────────────────

class SmokeFail(Exception):
    """Raised when a check fails; formatted by main() for stderr."""


def _build_opener() -> urllib.request.OpenerDirector:
    """Opener with a cookie jar so the session cookie persists across requests."""
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    opener.addheaders = [("User-Agent", "rcm-mc-smoke-test/1.0")]
    # Attach jar so the caller can inspect cookies if needed.
    opener.cookiejar = jar  # type: ignore[attr-defined]
    return opener


def _get(opener, url: str, *, follow_redirects: bool = True,
         timeout: float = 10.0) -> Tuple[int, str]:
    """GET and return (status, body). Raises on network error."""
    try:
        resp = opener.open(url, timeout=timeout)
        return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        if not follow_redirects and exc.code in (301, 302, 303, 307, 308):
            return exc.code, ""
        if exc.code >= 400:
            return exc.code, exc.read().decode("utf-8", errors="replace")
        raise


def _post_form(opener, url: str, data: dict, *,
               timeout: float = 10.0) -> Tuple[int, str]:
    """POST form-urlencoded data, return (status, body)."""
    encoded = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(
        url, data=encoded,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        resp = opener.open(req, timeout=timeout)
        return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace") if exc.fp else ""


def _extract_csrf_token(html: str) -> Optional[str]:
    """Parse the CSRF hidden input from a rendered login page."""
    m = re.search(
        r'<input[^>]+name="csrf_token"[^>]+value="([^"]+)"', html)
    if m:
        return m.group(1)
    # Alternate ordering
    m = re.search(
        r'<input[^>]+value="([^"]+)"[^>]+name="csrf_token"', html)
    return m.group(1) if m else None


# ── Individual checks ──────────────────────────────────────────────

def check_healthz(opener, base: str) -> None:
    status, body = _get(opener, f"{base}/healthz")
    if status != 200:
        raise SmokeFail(f"/healthz returned {status}, expected 200")
    if body.strip() != "ok":
        raise SmokeFail(f"/healthz body was {body!r}, expected 'ok'")


def check_login(opener, base: str, username: str, password: str) -> None:
    """Authenticate via POST /api/login.

    /api/login is in _CSRF_EXEMPT_POSTS (login can't itself require
    a session-derived CSRF token — chicken-and-egg). The login form
    on /login uses a JS shim that reads the rcm_csrf cookie at submit
    time and injects a hidden input — there is no static csrf_token
    in the rendered HTML to scrape, so the smoke test posts directly
    to the API endpoint.

    Expected: 200 (when Accept: application/json) or 303 (redirect
    after successful HTML form submit). Both ship the rcm_session +
    rcm_csrf cookies as Set-Cookie, which the opener's cookie jar
    persists for subsequent requests.
    """
    # GET /login first to confirm the page is intact (and to set any
    # initial CSRF cookie a JS-driven flow would normally read).
    status, _html = _get(opener, f"{base}/login")
    if status != 200:
        raise SmokeFail(f"GET /login returned {status}")

    # POST credentials directly to /api/login — CSRF-exempt.
    status, _body = _post_form(
        opener, f"{base}/api/login",
        {"username": username, "password": password},
    )
    # urllib auto-follows 303 → "/" by default. Success ends at 200.
    if status not in (200, 204):
        raise SmokeFail(
            f"POST /api/login returned {status} — credentials rejected?")

    # Verify a session cookie was actually issued.
    jar = getattr(opener, "cookiejar", None)
    if jar is not None:
        names = {c.name for c in jar}
        if "rcm_session" not in names:
            raise SmokeFail(
                "POST /api/login returned OK but no rcm_session cookie "
                "was set — check the Set-Cookie path on the response")


def check_authenticated_home(opener, base: str) -> None:
    status, html = _get(opener, f"{base}/home")
    if status != 200:
        raise SmokeFail(f"GET /home returned {status}; session not persisting?")
    # Banner sanity: if RCM_MC_PHI_MODE=disallowed was set server-side, we
    # expect the banner in the rendered HTML.
    if os.environ.get("RCM_MC_PHI_MODE", "").lower() == "disallowed":
        if "no PHI permitted" not in html:
            raise SmokeFail(
                "PHI_MODE=disallowed but banner missing from /home — "
                "chartis_shell wiring broken?")


def check_dashboard(opener, base: str) -> None:
    """Private-app landing page — must render the four sections cleanly."""
    status, html = _get(opener, f"{base}/dashboard")
    if status != 200:
        raise SmokeFail(f"GET /dashboard returned {status}")
    for section in ("What you can run", "Recent runs",
                    "System status", "Data freshness"):
        if section not in html:
            raise SmokeFail(f"/dashboard missing section: {section!r}")


def check_fast_analysis(opener, base: str, fixture: str) -> dict:
    """Trigger a thesis-pipeline render against a fixture. Returns parsed result.

    The thesis pipeline is synchronous and runs in ~170 ms on a fixture.
    A 200 response with the expected content markers is end-to-end proof
    that: the analysis fired, every dependency was importable, the
    packet builder ran clean, and the renderer produced HTML.
    """
    url = f"{base}/diligence/thesis-pipeline?dataset={urllib.parse.quote(fixture)}"
    status, html = _get(opener, url, timeout=30.0)
    if status != 200:
        raise SmokeFail(
            f"GET /diligence/thesis-pipeline?dataset={fixture} returned {status}")
    if "Thesis Pipeline" not in html and "thesis_pipeline" not in html.lower():
        # Very loose contract — page changed but still rendered
        raise SmokeFail(
            "thesis-pipeline page rendered but content markers missing")
    return {"length_bytes": len(html), "fixture": fixture}


def check_async_polling_endpoint(opener, base: str) -> dict:
    """Verify the async-job polling infrastructure responds correctly.

    We don't trigger a real long-running job in the smoke path (would
    pull live CMS data + take 30+ seconds). Instead, we hit the polling
    endpoint with a known-bad job id and confirm it returns the
    structured 404 response — proves the route is wired and the JSON
    error envelope is intact, which is what async UIs depend on.
    """
    url = f"{base}/api/jobs/smoke-test-nonexistent-id"
    try:
        resp = opener.open(url, timeout=10.0)
        # 200 means the registry returned a row for this fake id —
        # something is wrong (maybe a test left ghost state behind).
        raise SmokeFail(
            f"/api/jobs/<bogus> returned {resp.status}, expected 404")
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise SmokeFail(
                f"/api/jobs/<bogus> returned {exc.code}, expected 404")
        try:
            body = json.loads(exc.read())
        except json.JSONDecodeError:
            raise SmokeFail("/api/jobs/<bogus> 404 body was not JSON")
        if body.get("code") != "JOB_NOT_FOUND":
            raise SmokeFail(
                f"/api/jobs/<bogus> error code was {body.get('code')!r}, "
                f"expected JOB_NOT_FOUND")
    return {"endpoint": "/api/jobs/<id>", "contract": "404 + JOB_NOT_FOUND"}


# ── Main ───────────────────────────────────────────────────────────

def run_all(base: str, username: str, password: str, fixture: str) -> int:
    steps = [
        ("healthz",              lambda o: check_healthz(o, base)),
        ("login",                lambda o: check_login(o, base, username, password)),
        ("authenticated_home",   lambda o: check_authenticated_home(o, base)),
        ("dashboard",            lambda o: check_dashboard(o, base)),
        ("fast_analysis",        lambda o: check_fast_analysis(o, base, fixture)),
        ("async_polling",        lambda o: check_async_polling_endpoint(o, base)),
    ]
    opener = _build_opener()
    for name, fn in steps:
        t0 = time.perf_counter()
        try:
            result = fn(opener)
        except SmokeFail as exc:
            print(f"  ✗ {name}: {exc}", file=sys.stderr)
            return 1
        except urllib.error.URLError as exc:
            print(f"  ✗ {name}: network error — {exc}", file=sys.stderr)
            return 1
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        extra = f" {result}" if isinstance(result, dict) else ""
        print(f"  ✓ {name:<22} ({elapsed_ms:6.1f} ms){extra}")
    print("\nall smoke checks passed")
    return 0


def main(argv: Optional[list] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("base_url", nargs="?", default="http://localhost:8080",
                    help="Server base URL (default: http://localhost:8080)")
    ap.add_argument("--user", default=os.environ.get("ADMIN_USERNAME"),
                    help="Login username (default: $ADMIN_USERNAME)")
    ap.add_argument("--password", default=os.environ.get("ADMIN_PASSWORD"),
                    help="Login password (default: $ADMIN_PASSWORD)")
    ap.add_argument("--fixture", default=DEFAULT_FIXTURE,
                    help=f"Thesis pipeline fixture (default: {DEFAULT_FIXTURE})")
    args = ap.parse_args(argv)

    if not args.user or not args.password:
        print("error: --user/--password or ADMIN_USERNAME/ADMIN_PASSWORD required",
              file=sys.stderr)
        return 2

    base = args.base_url.rstrip("/")
    print(f"smoke test → {base} (user={args.user}, fixture={args.fixture})")
    return run_all(base, args.user, args.password, args.fixture)


if __name__ == "__main__":
    sys.exit(main())
