"""HTTP transport for data.cdc.gov (Socrata SODA): throttle + backoff.

The CDC's Socrata domain is public and works unauthenticated for modest
volume; unauthenticated clients share a throttled pool, so an optional
application token from ``$CDC_APP_TOKEN`` is sent as the ``X-App-Token``
header when set (register one at https://data.cdc.gov/profile/edit/developer_settings).
VERIFIED LIVE: a *wrong* token hard-403s, so the header is only attached
when the env var (or constructor) actually provides one — never a
placeholder.

This transport:
  * keeps a minimum inter-request interval so a tight ingest loop stays
    polite (a courtesy floor, NOT a documented Socrata contract),
  * handles HTTP 429 and 5xx with exponential backoff + full jitter and
    honours the ``Retry-After`` header when the server sends one,
  * treats a 404 as an empty row list rather than raising (an unknown or
    retired 4x4 yields zero rows, mirroring the estate convention),
  * URL-encodes Socrata's ``$``-prefixed SoQL params (``$limit``,
    ``$offset``, ``$where``, ``$order``) — ``urlencode`` percent-encodes
    ``$`` to ``%24``, which Socrata accepts, so no special casing beyond
    deterministic ordering is needed.

SODA rows endpoints return a JSON *array*; the catalog metadata endpoint
does too; ``/api/views/{id}.json`` returns an object — so ``get_json``
accepts both shapes and callers assert what they need.

The opener is injectable so every retry / backoff / parse path is unit
tested with a fake server and no socket — the same testability contract
the rest of RCM-MC's public-data clients follow.
"""
from __future__ import annotations

import json
import os
import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, Union
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

USER_AGENT = "rcm-connectors/cdc_data"
DEFAULT_BASE_URL = "https://data.cdc.gov"

# Conservative defaults. Overridable via the constructor; documented as a
# floor, not a contract — verify live limits at dev.socrata.com before a
# bulk run.
_DEFAULT_MIN_INTERVAL_S = 0.25
_DEFAULT_MAX_RETRIES = 3
_DEFAULT_BACKOFF_BASE_S = 1.0
_DEFAULT_BACKOFF_CAP_S = 60.0

JsonDoc = Union[Dict[str, Any], list]


class CdcDataApiError(RuntimeError):
    """Raised when data.cdc.gov is unreachable or returns an unrecoverable error."""


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
class CdcSodaTransport:
    """Throttled, retrying JSON transport against ``data.cdc.gov``."""

    app_token: Optional[str] = None
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
    def from_env(cls, **overrides: Any) -> "CdcSodaTransport":
        """Build a transport, reading an optional token from
        ``$CDC_APP_TOKEN``.

        Absent token is fine — data.cdc.gov serves unauthenticated
        requests from a shared throttled pool; the token only buys a
        dedicated rate allocation.
        """
        token = os.environ.get("CDC_APP_TOKEN") or None
        params: Dict[str, Any] = {"app_token": token}
        params.update(overrides)
        return cls(**params)

    @property
    def has_token(self) -> bool:
        return bool(self.app_token)

    def build_url(self, path: str, params: Optional[Dict[str, Any]] = None) -> str:
        """Pure URL builder.

        Stable (sorted) param ordering keeps URLs — and test assertions —
        deterministic; ``urlencode`` percent-encodes SoQL's ``$`` prefix
        and any spaces/quotes inside ``$where`` clauses.
        """
        merged: Dict[str, Any] = dict(params or {})
        query = urlencode([(k, merged[k]) for k in sorted(merged)])
        sep = "&" if "?" in path else "?"
        tail = f"{sep}{query}" if query else ""
        return f"{self.base_url}{path}{tail}"

    def _headers(self) -> Dict[str, str]:
        headers = {"User-Agent": self.user_agent, "Accept": "application/json"}
        # Only attach the token when one is genuinely configured: Socrata
        # 403s on an invalid token (verified live), so a placeholder would
        # be strictly worse than anonymous access.
        if self.app_token:
            headers["X-App-Token"] = self.app_token
        return headers

    def _throttle(self, sleep: Callable[[float], None], now: Callable[[], float]) -> None:
        if self.min_interval_s <= 0:
            return
        wait = self.min_interval_s - (now() - self._last_call_s)
        if wait > 0:
            sleep(wait)

    def _backoff_seconds(self, attempt: int, resp: Optional[RawResponse],
                         rand: Callable[[], float]) -> float:
        """Retry-After wins; otherwise exponential backoff with full jitter."""
        if resp is not None:
            ra = resp.header("retry-after")
            if ra:
                try:
                    return min(float(ra), self.backoff_cap_s)
                except ValueError:
                    pass  # HTTP-date form is rare here; fall through
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

        Returns the decoded payload — a list for SODA row / catalog
        metadata endpoints, a dict for ``/api/views/{id}.json``. A 404
        returns an empty list (unknown 4x4 → zero rows). Raises
        :class:`CdcDataApiError` only after exhausting retries or on an
        unrecoverable 4xx.
        """
        opener = opener or _default_opener
        url = self.build_url(path, params)
        headers = self._headers()
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
                # Unknown/retired 4x4 — an empty row list, not a failure.
                return []
            if status == 429 or status >= 500 or status == 0:
                last_status, last_detail = status, _short_body(resp.body)
                if attempt < self.max_retries:
                    sleep(self._backoff_seconds(attempt, resp, rand))
                    continue
                break
            # Other 4xx (400 bad SoQL, 403 bad token) won't fix on retry.
            raise CdcDataApiError(
                f"{url}: HTTP {status} {_short_body(resp.body)}"
            )
        raise CdcDataApiError(
            f"{url}: failed after {self.max_retries + 1} attempts "
            f"(last status {last_status}: {last_detail})"
        )

    @staticmethod
    def _parse(body: bytes, url: str) -> JsonDoc:
        try:
            doc = json.loads(body)
        except json.JSONDecodeError as exc:
            raise CdcDataApiError(
                f"{url}: non-JSON response ({len(body)} bytes)"
            ) from exc
        if not isinstance(doc, (dict, list)):
            raise CdcDataApiError(
                f"{url}: unexpected JSON shape {type(doc).__name__}")
        return doc


def _short_body(body: bytes, limit: int = 200) -> str:
    try:
        text = body.decode("utf-8", "replace")
    except Exception:
        text = repr(body[:limit])
    text = " ".join(text.split())
    return text[:limit]
