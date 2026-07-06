"""HTTP transport for the US Census ACS API: key handling + backoff.

``api.census.gov`` **now requires an API key on every data request**
(verified live 2026-07-06: keyless data queries 302-redirect to
``/data/missing_key.html``; only the metadata endpoints —
``variables.json`` / ``geography.json`` — stay keyless). This is a policy
change from the old "small keyless volumes per IP per day" behaviour.
Keys are free: https://api.census.gov/data/key_signup.html.

This transport:
  * reads the key from ``$CENSUS_API_KEY`` and merges it into every URL;
    without one it still runs (metadata probes work) but data queries
    fail with a *clear, actionable* error naming the env var instead of a
    cryptic JSON-parse failure,
  * keeps a minimum inter-request interval so a tight ingest loop stays
    polite (each profile refresh is only two requests anyway),
  * handles HTTP 429 and 5xx with exponential backoff + full jitter and
    honours the ``Retry-After`` header when the server sends one,
  * treats HTTP 204 as an empty result (the API's documented "no rows
    matched" response) and raises clearly on 400/404 (bad variable or
    vintage — retrying would not help, and an empty envelope would mask a
    wrong ``--year``).

The response body is a JSON **array of arrays** (first row = headers),
not an object — :meth:`get_rows` returns that list. The opener is
injectable so every retry / backoff / parse path is unit tested with a
fake server and no socket — the same testability contract the rest of
RCM-MC's public-data clients follow.
"""
from __future__ import annotations

import json
import os
import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

USER_AGENT = "rcm-connectors/census_acs"
DEFAULT_BASE_URL = "https://api.census.gov/data"
KEY_SIGNUP_URL = "https://api.census.gov/data/key_signup.html"

# Conservative defaults. Overridable via the constructor; documented as a
# floor, not a contract — verify live at census.gov/data/developers.
_DEFAULT_MIN_INTERVAL_S = 0.5   # each refresh is 2 calls; stay very polite
_DEFAULT_MAX_RETRIES = 3
_DEFAULT_BACKOFF_BASE_S = 1.0
_DEFAULT_BACKOFF_CAP_S = 60.0


class CensusAcsApiError(RuntimeError):
    """Raised when the API is unreachable or returns an unrecoverable error."""


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
    into a :class:`RawResponse` so the retry loop owns all status logic.

    urllib follows the API's missing-key 302 automatically, so a keyless
    data query surfaces here as a 200 with an HTML body — :meth:`get_rows`
    detects that page and raises the actionable key error.
    """
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
class CensusAcsTransport:
    """Throttled, retrying array-of-arrays transport against ``api.census.gov``."""

    api_key: Optional[str] = None
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
    def from_env(cls, **overrides: Any) -> "CensusAcsTransport":
        """Build a transport, reading the key from ``$CENSUS_API_KEY``.

        An absent key is tolerated at construction time so metadata-only
        and test flows work; live data queries will fail with a clear
        message pointing at the env var and the signup URL.
        """
        key = os.environ.get("CENSUS_API_KEY", "").strip() or None
        params: Dict[str, Any] = {"api_key": key}
        params.update(overrides)
        return cls(**params)

    @property
    def has_key(self) -> bool:
        return bool(self.api_key)

    def build_url(self, path: str, params: Optional[Dict[str, Any]] = None) -> str:
        """Pure URL builder; merges the key in when configured.

        ``urlencode`` percent-encodes the CBSA geography string's slashes
        and spaces. Stable (sorted) ordering keeps URLs — and test
        assertions — deterministic; ``get`` and ``for``/``in`` order does
        not matter to the API.
        """
        merged: Dict[str, Any] = dict(params or {})
        if self.api_key:
            merged.setdefault("key", self.api_key)
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

    def get_rows(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        *,
        opener: Optional[Opener] = None,
        sleep: Callable[[float], None] = time.sleep,
        now: Callable[[], float] = time.monotonic,
        rand: Callable[[], float] = random.random,
    ) -> List[List[Any]]:
        """Issue one GET, parse the array-of-arrays, retrying 429/5xx.

        Returns the decoded list (header row first). HTTP 204 — the API's
        "query matched nothing" — returns ``[]``. Raises
        :class:`CensusAcsApiError` on a missing/invalid key, on 400/404
        (bad variable or vintage — won't fix on retry), or after
        exhausting retries on 429/5xx/transport errors.
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
            if status == 204:
                # Documented "no content": the query is valid but matched
                # no geography rows.
                return []
            if status == 302:
                # A fake opener may surface the missing-key redirect
                # unfollowed; treat it exactly like the followed page.
                raise CensusAcsApiError(self._key_message(url))
            if status == 429 or status >= 500 or status == 0:
                last_status, last_detail = status, _short_body(resp.body)
                if attempt < self.max_retries:
                    sleep(self._backoff_seconds(attempt, resp, rand))
                    continue
                break
            # Other 4xx (400 unknown variable, 404 unknown vintage/dataset)
            # won't fix on retry — surface the API's message verbatim.
            raise CensusAcsApiError(
                f"{url}: HTTP {status} {_short_body(resp.body)}"
            )
        raise CensusAcsApiError(
            f"{url}: failed after {self.max_retries + 1} attempts "
            f"(last status {last_status}: {last_detail})"
        )

    def _parse(self, body: bytes, url: str) -> List[List[Any]]:
        try:
            doc = json.loads(body)
        except json.JSONDecodeError as exc:
            # urllib followed the missing/invalid-key redirect to an HTML
            # page — turn that into an actionable error, not a parse error.
            text = body.decode("utf-8", "replace").lower()
            if "missing key" in text or "invalid key" in text or "a valid <em>key</em>" in text:
                raise CensusAcsApiError(self._key_message(url)) from exc
            raise CensusAcsApiError(
                f"{url}: non-JSON response ({len(body)} bytes)"
            ) from exc
        if not isinstance(doc, list):
            raise CensusAcsApiError(
                f"{url}: unexpected JSON shape {type(doc).__name__} "
                "(expected the ACS array-of-arrays)")
        return doc

    def _key_message(self, url: str) -> str:
        state = ("the configured key was rejected" if self.has_key
                 else "no key is configured")
        return (
            f"{url}: api.census.gov requires an API key on every data "
            f"request and {state}. Set $CENSUS_API_KEY (free signup: "
            f"{KEY_SIGNUP_URL})."
        )


def _short_body(body: bytes, limit: int = 200) -> str:
    try:
        text = body.decode("utf-8", "replace")
    except Exception:
        text = repr(body[:limit])
    text = " ".join(text.split())
    return text[:limit]
