"""HTTP transport for data.cms.gov: rate-limit floor + backoff.

The CMS Open Data platform (``data.cms.gov``) is public and needs no
API key. Two JSON surfaces flow through this transport:

  * the DCAT catalog ``GET /data.json`` (a JSON *object* with a
    ``dataset`` array), and
  * the data API ``GET /data-api/v1/dataset/{uuid}/data`` (a JSON
    *array* of row objects) plus its ``…/data/stats`` companion.

Because the row endpoint returns a bare array, :meth:`get_json` returns
whatever JSON shape the server sent (list *or* dict) instead of
insisting on a dict the way the CMS Coverage transport does — the
callers in :mod:`connectors.cms_open_data.connector` know which shape
each path yields.

CMS publishes no hard rate limit for the data API, so we keep a
conservative inter-request floor (a courtesy default, NOT a documented
contract — verify at https://data.cms.gov/api-docs before a bulk run).
HTTP 429 and 5xx are retried with exponential backoff + full jitter,
honouring ``Retry-After``; a 404 is treated as "no rows for this
dataset version" (an empty list) rather than an error, because dataset
version UUIDs rotate when CMS publishes new data years.

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
from typing import Any, Callable, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

USER_AGENT = "rcm-connectors/cms_open_data"
DEFAULT_BASE_URL = "https://data.cms.gov"

# Conservative defaults. Overridable via the constructor; documented as a
# floor, not a contract — verify live at data.cms.gov/api-docs.
_DEFAULT_MIN_INTERVAL_S = 0.25        # ~240 req/min, deliberately polite
_DEFAULT_MAX_RETRIES = 3
_DEFAULT_BACKOFF_BASE_S = 1.0
_DEFAULT_BACKOFF_CAP_S = 60.0


class CmsOpenDataApiError(RuntimeError):
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
class CmsOpenDataTransport:
    """Throttled, retrying JSON transport against ``data.cms.gov``."""

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
    def from_env(cls, **overrides: Any) -> "CmsOpenDataTransport":
        """Build a transport. No key exists for data.cms.gov; the env only
        tunes the user agent so a shared crawler can identify itself."""
        params: Dict[str, Any] = {}
        ua = os.environ.get("CMS_OPEN_DATA_USER_AGENT")
        if ua:
            params["user_agent"] = ua
        params.update(overrides)
        return cls(**params)

    def build_url(self, path: str, params: Optional[Dict[str, Any]] = None) -> str:
        """Pure URL builder. Stable key ordering keeps URLs (and test
        assertions) deterministic; ``filter[Col]`` brackets are percent-
        encoded, which the data API accepts (verified live)."""
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
    ) -> Any:
        """Issue one GET, parse JSON, retrying 429/5xx/transport errors.

        Returns the decoded payload — a list for ``…/data`` pages, a dict
        for ``/data.json`` and ``…/data/stats``. A 404 returns an empty
        list (dataset version rotated / no matching rows — not a
        failure). Raises :class:`CmsOpenDataApiError` only after
        exhausting retries or on an unrecoverable 4xx.
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
                # Version UUID rotated or nothing matches — no rows.
                return []
            if status == 429 or status >= 500 or status == 0:
                last_status, last_detail = status, _short_body(resp.body)
                if attempt < self.max_retries:
                    sleep(self._backoff_seconds(attempt, resp, rand))
                    continue
                break
            # Other 4xx (400 bad query, 403 forbidden) won't fix on retry.
            raise CmsOpenDataApiError(
                f"{url}: HTTP {status} {_short_body(resp.body)}"
            )
        raise CmsOpenDataApiError(
            f"{url}: failed after {self.max_retries + 1} attempts "
            f"(last status {last_status}: {last_detail})"
        )

    @staticmethod
    def _parse(body: bytes, url: str) -> Any:
        try:
            doc = json.loads(body)
        except json.JSONDecodeError as exc:
            raise CmsOpenDataApiError(
                f"{url}: non-JSON response ({len(body)} bytes)"
            ) from exc
        if not isinstance(doc, (list, dict)):
            raise CmsOpenDataApiError(
                f"{url}: unexpected JSON shape {type(doc).__name__}")
        return doc


def _short_body(body: bytes, limit: int = 200) -> str:
    try:
        text = body.decode("utf-8", "replace")
    except Exception:
        text = repr(body[:limit])
    text = " ".join(text.split())
    return text[:limit]
