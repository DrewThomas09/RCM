"""Post-deploy smoke gate for an Azure App Service ship of RCM-MC.

Closes the three ship-side rows that the cycle-12 deploy-readiness
gate left open — they couldn't be verified from local testing
because they depend on the real platform running the container:

  1. ``/healthz`` returns 200 with cold-container response time
     under the ``--max-healthz-ms`` threshold (default 1000ms;
     tune down once you have baseline measurements).
  2. ``/login`` → ``POST /api/login`` → redirected ``/app``
     succeeds end-to-end with the seeded demo credentials.
  3. ``/app`` carries the chartis editorial chrome — navy topbar,
     italic Chartis wordmark, teal accent rule.

Usage::

    python tools/azure_smoke.py https://rcm-mc.azurewebsites.net
    python tools/azure_smoke.py https://staging.example.net \\
        --username andrewthomas@chartis.com \\
        --password ChartisDemo1 \\
        --max-healthz-ms 500 \\
        --json

Exit code is 0 when every check passes, non-zero on any failure.
The ``--json`` flag emits a machine-readable summary instead of
the human-readable banner so this can wire into a CI gate.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from http.cookiejar import CookieJar
from typing import List, Optional


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str = ""
    duration_ms: float = 0.0


@dataclass
class SmokeReport:
    base_url: str
    checks: List[CheckResult] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        return all(c.passed for c in self.checks)


def _open(url: str, *, opener=None, data=None, headers=None,
          method: Optional[str] = None, timeout: int = 30):
    req = urllib.request.Request(
        url, data=data, headers=headers or {}, method=method,
    )
    if opener is None:
        return urllib.request.urlopen(req, timeout=timeout)
    return opener.open(req, timeout=timeout)


def check_healthz(base_url: str, *, max_ms: float) -> CheckResult:
    """Hit /healthz and assert 200 + duration <= max_ms."""
    target = base_url.rstrip("/") + "/healthz"
    start = time.perf_counter()
    try:
        with _open(target) as r:
            status = r.status
            r.read()
    except urllib.error.URLError as exc:
        return CheckResult(
            "healthz", False,
            f"could not reach {target}: {exc}",
        )
    dur_ms = (time.perf_counter() - start) * 1000.0
    if status != 200:
        return CheckResult(
            "healthz", False,
            f"expected 200, got {status}",
            duration_ms=dur_ms,
        )
    if dur_ms > max_ms:
        return CheckResult(
            "healthz", False,
            f"latency {dur_ms:.1f}ms exceeded threshold {max_ms:.0f}ms",
            duration_ms=dur_ms,
        )
    return CheckResult(
        "healthz", True,
        f"200 in {dur_ms:.1f}ms (threshold {max_ms:.0f}ms)",
        duration_ms=dur_ms,
    )


def check_login_round_trip(
    base_url: str,
    *,
    username: str,
    password: str,
) -> tuple[CheckResult, Optional[urllib.request.OpenerDirector]]:
    """POST /api/login, follow redirect, return cookie-bearing opener.

    Returns the round-trip result plus an opener that the caller can
    use to follow up with /app. We don't issue the /app GET inside
    this helper because the chrome assertions are a separate check
    that should produce its own line in the report.
    """
    cj = CookieJar()
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(cj),
    )
    payload = urllib.parse.urlencode({
        "username": username, "password": password,
    }).encode("utf-8")
    target = base_url.rstrip("/") + "/api/login"
    start = time.perf_counter()
    try:
        with _open(
            target, opener=opener, data=payload,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            method="POST",
        ) as r:
            status = r.status
            body = r.read().decode("utf-8", "replace")
    except urllib.error.URLError as exc:
        return (
            CheckResult(
                "login", False,
                f"could not reach {target}: {exc}",
            ),
            None,
        )
    dur_ms = (time.perf_counter() - start) * 1000.0
    if status not in (200, 303):
        return (
            CheckResult(
                "login", False,
                f"expected 200/303, got {status}: {body[:200]}",
                duration_ms=dur_ms,
            ),
            None,
        )
    has_session = any(c.name == "rcm_session" for c in cj)
    if not has_session:
        return (
            CheckResult(
                "login", False,
                "no rcm_session cookie issued",
                duration_ms=dur_ms,
            ),
            None,
        )
    return (
        CheckResult(
            "login", True,
            f"{status} in {dur_ms:.1f}ms; rcm_session cookie set",
            duration_ms=dur_ms,
        ),
        opener,
    )


# Editorial chrome markers we expect on every signed-in v5 page.
# These are the load-bearing strings the chartis_shell topbar
# always emits — if any one is missing the partner is staring at
# either a 404, the legacy dark shell, or a 500.
_CHROME_MARKERS = (
    'class="ck-topbar"',
    'class="ck-wordmark"',
    "Seeking<em>Chartis</em>",
    "ck-nav",
)


def check_app_chrome(
    base_url: str,
    *,
    opener: urllib.request.OpenerDirector,
) -> CheckResult:
    """GET /app with the post-login cookie; assert chrome markers."""
    target = base_url.rstrip("/") + "/app"
    start = time.perf_counter()
    try:
        with _open(target, opener=opener) as r:
            status = r.status
            body = r.read().decode("utf-8", "replace")
    except urllib.error.URLError as exc:
        return CheckResult(
            "app_chrome", False,
            f"could not reach {target}: {exc}",
        )
    dur_ms = (time.perf_counter() - start) * 1000.0
    if status != 200:
        return CheckResult(
            "app_chrome", False,
            f"expected 200, got {status}",
            duration_ms=dur_ms,
        )
    missing = [m for m in _CHROME_MARKERS if m not in body]
    if missing:
        return CheckResult(
            "app_chrome", False,
            f"missing chrome markers: {missing}",
            duration_ms=dur_ms,
        )
    return CheckResult(
        "app_chrome", True,
        f"200 in {dur_ms:.1f}ms; all {len(_CHROME_MARKERS)} chrome markers present",
        duration_ms=dur_ms,
    )


def run_smoke(
    base_url: str,
    *,
    username: str,
    password: str,
    max_healthz_ms: float,
) -> SmokeReport:
    report = SmokeReport(base_url=base_url)
    report.checks.append(check_healthz(base_url, max_ms=max_healthz_ms))

    login_result, opener = check_login_round_trip(
        base_url, username=username, password=password,
    )
    report.checks.append(login_result)
    if opener is not None:
        report.checks.append(check_app_chrome(base_url, opener=opener))
    else:
        # Login failed, can't fetch /app authenticated. Skip chrome
        # check rather than fail-double.
        report.checks.append(CheckResult(
            "app_chrome", False,
            "skipped — login failed",
        ))
    return report


def _print_human(report: SmokeReport, out=sys.stdout) -> None:
    out.write(f"\n  Azure smoke gate — {report.base_url}\n")
    out.write(f"  {'─' * 70}\n")
    for c in report.checks:
        flag = "PASS" if c.passed else "FAIL"
        line = f"  [{flag}] {c.name:<12s} {c.detail}\n"
        out.write(line)
    out.write(f"  {'─' * 70}\n")
    if report.all_passed:
        out.write("  All checks passed. Deploy is healthy.\n\n")
    else:
        out.write("  One or more checks failed. See lines marked [FAIL].\n\n")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="azure_smoke",
        description="Post-deploy smoke gate for an Azure ship of RCM-MC.",
    )
    p.add_argument("base_url", help="https://<app>.azurewebsites.net")
    p.add_argument(
        "--username", default="andrewthomas@chartis.com",
        help="Login username (default: seeded demo partner account)",
    )
    p.add_argument(
        "--password", default="ChartisDemo1",
        help="Login password (default: seeded demo partner account)",
    )
    p.add_argument(
        "--max-healthz-ms", type=float, default=1000.0,
        help="Maximum acceptable /healthz latency in ms (default 1000)",
    )
    p.add_argument(
        "--json", action="store_true",
        help="Emit a machine-readable JSON summary instead of human text",
    )
    args = p.parse_args(argv)

    report = run_smoke(
        args.base_url,
        username=args.username,
        password=args.password,
        max_healthz_ms=args.max_healthz_ms,
    )

    if args.json:
        sys.stdout.write(json.dumps({
            "base_url": report.base_url,
            "all_passed": report.all_passed,
            "checks": [asdict(c) for c in report.checks],
        }, indent=2) + "\n")
    else:
        _print_human(report)

    return 0 if report.all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
