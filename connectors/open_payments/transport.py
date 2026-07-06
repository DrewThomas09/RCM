"""HTTP transport for openpaymentsdata.cms.gov: throttle + 429/5xx backoff.

The Open Payments data portal is public and needs no key. It runs DKAN
(the same engine behind ``data.medicaid.gov``) and publishes no hard
rate limit, so we default to a conservative inter-request floor
(courtesy default, NOT a documented contract — verify before a bulk
run). Two engine quirks this transport knows about:

  * the datastore rejects ``limit`` above 500 with an HTTP 400 JSON
    Schema validation error (verified live 2026-07-06) — page sizing is
    clamped in the connector, and a 400's ``message`` field is surfaced
    in the raised error so the cause is obvious;
  * the metastore catalog endpoint returns a top-level JSON **list**
    while datastore queries return a dict envelope — ``get_json``
    accepts both.

This transport also:
  * keeps a minimum inter-request interval so a tight ingest loop stays
    polite (payment-file queries against 15M-row tables are not cheap
    server-side),
  * handles HTTP 429 and 5xx with exponential backoff + full jitter and
    honours the ``Retry-After`` header when the server sends one,
  * treats a 404 as an empty datastore envelope rather than raising.

The opener is injectable so every retry / backoff / parse path is unit
tested with a fake server and no socket — the same testability contract
the rest of RCM-MC's public-data clients follow.
"""
from __future__ import annotations

import json
import math
import os
import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, Union
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

USER_AGENT = "rcm-connectors/open_payments"
DEFAULT_BASE_URL = "https://openpaymentsdata.cms.gov"

# Conservative defaults. Overridable via the constructor; documented as a
# floor, not a contract — verify live at openpaymentsdata.cms.gov.
_DEFAULT_MIN_INTERVAL_S = 0.25
_DEFAULT_MAX_RETRIES = 3
_DEFAULT_BACKOFF_BASE_S = 1.0
_DEFAULT_BACKOFF_CAP_S = 60.0

# Empty datastore envelope returned on a 404 (mirrors the live shape,
# minus the echo-only "query"/"schema" blocks).
_EMPTY_PAYLOAD: Dict[str, Any] = {"count": 0, "results": []}

JsonDoc = Union[Dict[str, Any], list]


class OpenPaymentsApiError(RuntimeError):
    """Raised when the portal is unreachable or returns an unrecoverable error."""


@dataclass(frozen=True)
class RawResponse:
    """A minimal HTTP response the retry loop can reason about.

    Injectable openers return this so tests can assert on 429 +
    ``Retry-After`` handling without a real socket. ``headers`` keys are
    lower-cased.
    """

    status: int
    headers: Dict[str, str] = field(default_factory=dict)
    body: bytes = b""

    def header(self, name: str) -> Optional[str]:
        return self.headers.get(name.lower())


# Opener signature: (full_url, headers, timeout_s) -> RawResponse.
Opener = Callable[[str, Dict[str, str], float], RawResponse]


def _default_opener(url: str, headers: Dict[str, str], timeout_s: float) -> RawResponse:
    """urllib opener that never raises on HTTP status — it folds HTTPError
    into a :class:`RawResponse` so the retry loop owns all status logic."""
    req = Request(url, headers=headers)
    try:
        with urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read()
            hdrs = {k.lower(): v for k, v in resp.headers.items()}
            return RawResponse(status=resp.status, headers=hdrs, body=raw)
    except HTTPError as exc:
        raw = b""
        try:
            raw = exc.read()
        except Exception:
            pass
        hdrs = {k.lower(): v for k, v in (exc.headers or {}).items()}
        return RawResponse(status=exc.code, headers=hdrs, body=raw)
    except (URLError, TimeoutError, OSError) as exc:
        # Surface transport-level failures as status 0 so the loop retries.
        return RawResponse(status=0, headers={}, body=str(exc).encode())


@dataclass
class OpenPaymentsTransport:
    """Throttled, retrying JSON transport against ``openpaymentsdata.cms.gov``."""

    user_agent: str = USER_AGENT
    base_url: str = DEFAULT_BASE_URL
    timeout_s: float = 30.0
    min_interval_s: float = _DEFAULT_MIN_INTERVAL_S
    max_retries: int = _DEFAULT_MAX_RETRIES
    backoff_base_s: float = _DEFAULT_BACKOFF_BASE_S
    backoff_cap_s: float = _DEFAULT_BACKOFF_CAP_S
    _last_call_s: float = field(default=0.0, repr=False)
    requests_made: int = field(default=0, repr=False)

    @classmethod
    def from_env(cls, **overrides: Any) -> "OpenPaymentsTransport":
        """Build a transport. No key exists for Open Payments; env only
        tunes the user agent so a shared crawler can identify itself."""
        params: Dict[str, Any] = {}
        ua = os.environ.get("OPEN_PAYMENTS_USER_AGENT")
        if ua:
            params["user_agent"] = ua
        params.update(overrides)
        return cls(**params)

    def build_url(self, path: str, params: Optional[Dict[str, Any]] = None) -> str:
        """Pure URL builder.

        Nested DKAN filter params arrive pre-flattened (e.g. the literal
        key ``conditions[0][property]``) so plain :func:`urlencode` is
        enough. Stable key ordering keeps URLs (and test assertions)
        deterministic.
        """
        merged: Dict[str, Any] = dict(params or {})
        query = urlencode([(k, merged[k]) for k in sorted(merged)])
        sep = "&" if "?" in path else "?"
        tail = f"{sep}{query}" if query else ""
        return f"{self.base_url}{path}{tail}"

    def _throttle(self, sleep: Callable[[float], None], now: Callable[[], float]) -> None:
        if self.min_interval_s <= 0:
            return
        wait = self.min_interval_s - (now() - self._last_call_s)
        if wait > 0:
            sleep(wait)

    def _backoff_seconds(self, attempt: int, resp: Optional[RawResponse],
                         rand: Callable[[], float]) -> float:
        """Retry-After wins; otherwise exponential backoff with full jitter.

        Parsed defensively: a finite numeric ``Retry-After`` clamps to
        ``[0, backoff_cap_s]`` — a negative value must never reach
        ``time.sleep()``, where it would raise ``ValueError`` and abort
        the retry loop. Non-numeric values (HTTP-date form, garbage) and
        non-finite floats (``nan``/``inf`` parse but break ``sleep``)
        fall back to the exponential backoff schedule.
        """
        if resp is not None:
            ra = resp.header("retry-after")
            if ra:
                try:
                    ra_s = float(ra)
                except ValueError:
                    ra_s = None  # HTTP-date/garbage → backoff schedule
                if ra_s is not None and math.isfinite(ra_s):
                    return min(max(0.0, ra_s), self.backoff_cap_s)
        ceiling = min(self.backoff_cap_s, self.backoff_base_s * (2 ** attempt))
        return ceiling * rand()  # full jitter in [0, ceiling)

    def get_json(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        *,
        opener: Optional[Opener] = None,
        sleep: Callable[[float], None] = time.sleep,
        now: Callable[[], float] = time.monotonic,
        rand: Callable[[], float] = random.random,
    ) -> JsonDoc:
        """Issue one GET, parse JSON, retrying 429/5xx/transport errors.

        Returns the decoded payload: a dict envelope
        (``{"count":..., "results":[...]}``) for datastore queries or a
        list for the metastore catalog. A 404 returns an empty datastore
        envelope. Raises :class:`OpenPaymentsApiError` only after
        exhausting retries or on an unrecoverable 4xx (the portal's 400
        bodies carry a helpful ``message``, surfaced in the error).
        """
        opener = opener or _default_opener
        url = self.build_url(path, params)
        headers = {"User-Agent": self.user_agent, "Accept": "application/json"}
        last_status = -1
        last_detail = ""
        for attempt in range(self.max_retries + 1):
            self._throttle(sleep, now)
            resp = opener(url, headers, self.timeout_s)
            self._last_call_s = now()
            self.requests_made += 1
            status = resp.status

            if status == 200:
                return self._parse(resp.body, url)
            if status == 404:
                # Unknown dataset UUID / no datastore — empty, not fatal.
                return dict(_EMPTY_PAYLOAD)
            if status == 429 or status >= 500 or status == 0:
                last_status, last_detail = status, _short_body(resp.body)
                if attempt < self.max_retries:
                    sleep(self._backoff_seconds(attempt, resp, rand))
                    continue
                break
            # Other 4xx (400 bad query / limit > 500, 403) won't fix on retry.
            raise OpenPaymentsApiError(
                f"{url}: HTTP {status} {_short_body(resp.body)}"
            )
        raise OpenPaymentsApiError(
            f"{url}: failed after {self.max_retries + 1} attempts "
            f"(last status {last_status}: {last_detail})"
        )

    @staticmethod
    def _parse(body: bytes, url: str) -> JsonDoc:
        try:
            doc = json.loads(body)
        except json.JSONDecodeError as exc:
            raise OpenPaymentsApiError(
                f"{url}: non-JSON response ({len(body)} bytes)"
            ) from exc
        # The metastore catalog is a top-level list; datastore queries a
        # dict envelope. Anything else is a schema surprise worth raising.
        if not isinstance(doc, (dict, list)):
            raise OpenPaymentsApiError(
                f"{url}: unexpected JSON shape {type(doc).__name__}")
        return doc


def _short_body(body: bytes, limit: int = 200) -> str:
    try:
        text = body.decode("utf-8", "replace")
    except Exception:
        text = repr(body[:limit])
    text = " ".join(text.split())
    return text[:limit]
