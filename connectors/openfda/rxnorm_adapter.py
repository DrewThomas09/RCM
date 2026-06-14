"""NDC → RxCUI resolver backed by NLM RxNav.

The brief assigns NDC→RxCUI resolution to this workstream and notes the
dependency on the RxNorm source: if no RxNorm session has run, leave
RxCUI null and keep the join wireable. This module is the *wire* — a
concrete resolver that calls RxNav's public REST API
(``/REST/rxcui.json?idtype=NDC``) so resolution actually happens when
network egress is available, while still degrading gracefully (any
error → ``None``, never an exception that breaks ingestion).

It plugs straight into :func:`connectors.openfda.crosswalk.resolve_ndc_rxcui`
as the ``resolver=`` callable. The opener is injectable so the parse path
is unit-tested without a socket, matching the rest of the connector.

RxNav is rate-limited; the resolver keeps an in-process cache so repeated
NDCs (common across FAERS/recalls) cost one lookup, and a small interval
floor between live calls.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .normalize import ndc11

_RXNAV_BASE = "https://rxnav.nlm.nih.gov/REST"
_USER_AGENT = "rcm-mc/openfda-connector rxnorm-resolver"

# Opener: (url, timeout_s) -> raw bytes. Injectable for tests.
Opener = Callable[[str, float], bytes]


def _default_opener(url: str, timeout_s: float) -> bytes:
    req = Request(url, headers={"User-Agent": _USER_AGENT,
                                "Accept": "application/json"})
    with urlopen(req, timeout=timeout_s) as resp:
        return resp.read()


@dataclass
class RxNormResolver:
    """Resolve an NDC to a single RxCUI via RxNav, with caching."""

    opener: Optional[Opener] = None
    timeout_s: float = 15.0
    min_interval_s: float = 0.05
    _cache: Dict[str, Optional[str]] = field(default_factory=dict, repr=False)
    _last_call_s: float = field(default=0.0, repr=False)
    calls_made: int = field(default=0, repr=False)

    def __call__(self, ndc: str) -> Optional[str]:
        """Return the RxCUI for an NDC, or ``None`` if unresolved.

        Never raises: RxNav being down or slow must not break a backfill —
        the crosswalk simply records the NDC as deferred.
        """
        if not ndc:
            return None
        key = str(ndc)
        if key in self._cache:
            return self._cache[key]
        rxcui = self._resolve_one(key)
        # RxNav matches the 11-digit NDC form; try it as a fallback.
        if rxcui is None:
            alt = ndc11(key)
            if alt and alt != key:
                rxcui = self._resolve_one(alt)
        self._cache[key] = rxcui
        return rxcui

    def _resolve_one(self, ndc: str) -> Optional[str]:
        url = f"{_RXNAV_BASE}/rxcui.json?" + urlencode(
            {"idtype": "NDC", "id": ndc})
        opener = self.opener or _default_opener
        self._throttle()
        try:
            raw = opener(url, self.timeout_s)
            self._last_call_s = time.monotonic()
            self.calls_made += 1
            doc = json.loads(raw)
        except (HTTPError, URLError, TimeoutError, OSError,
                json.JSONDecodeError, ValueError):
            return None
        group = doc.get("idGroup") if isinstance(doc, dict) else None
        ids = (group or {}).get("rxnormId") or []
        return str(ids[0]) if ids else None

    def _throttle(self) -> None:
        if self.min_interval_s <= 0:
            return
        wait = self.min_interval_s - (time.monotonic() - self._last_call_s)
        if wait > 0:
            time.sleep(wait)


def make_resolver(opener: Optional[Opener] = None) -> RxNormResolver:
    """Build an RxNav-backed resolver to pass to ``resolve_ndc_rxcui``."""
    return RxNormResolver(opener=opener)
