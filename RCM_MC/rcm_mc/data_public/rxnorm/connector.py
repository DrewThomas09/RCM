"""RxNorm / RxNav connector — discover() + fetch() with the network behaviour
(pagination, rate-limit, retries) internal to the connector.

Contract conformed to:
  * ``discover()`` enumerates the datasets this connector ingests (the registry
    rows tagged ``source=rxnorm``).
  * ``fetch(endpoint, params, cursor) -> (rows, next_cursor)`` issues one page
    against an RxNav endpoint, parses RxNav's native JSON into flat rows, and
    returns an opaque cursor for the next page (``""`` when exhausted).

Transport is self-contained here (not the shared ``HttpJsonClient``) because
RxNav's rate-limit and 429/503 semantics are specific: NLM caps at ~20 req/s
per IP, and 429/503 must be retried with exponential backoff *plus jitter*
honouring ``Retry-After`` — whereas the shared client treats every <500 as a
hard fail. Keeping it here avoids perturbing other public-API clients. See
DECISIONS.md.

The opener is injectable so the retry / rate-limit / parse path is fully
testable without a socket; the default opener is stdlib ``urllib``. Nothing
runs at import. Use JSON endpoints only (never XML), per the source spec.
"""
from __future__ import annotations

import json
import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from . import normalize as nz
from .registry import dataset_rows

RXNAV_BASE = "https://rxnav.nlm.nih.gov/REST"

# NLM caps at ~20 req/s/IP; 0.06s floor keeps us comfortably under ~16/s.
# (Confirm the live limit before a bulk run — see DECISIONS.md / STATE.md.)
_RATE_LIMIT_INTERVAL_S = 0.06

_DEFAULT_USER_AGENT = (
    "rcm-mc/rxnorm-connector (github.com/DrewThomas09/RCM_MC; "
    "commercial-diligence research — contact: research@example.com)"
)

# Opener signature: (url, headers, timeout_s) -> raw bytes.
Opener = Callable[[str, Dict[str, str], int], bytes]


class RxNormApiError(RuntimeError):
    """Raised when RxNav is unreachable or returns unexpected data."""


def _default_opener(url: str, headers: Dict[str, str], timeout_s: int) -> bytes:
    req = Request(url, headers=headers)
    with urlopen(req, timeout=timeout_s) as resp:
        return resp.read()


@dataclass
class RxNormConnector:
    """Stateful connector. One instance per ingestion run.

    ``batch_size`` controls client-side pagination of the big ``allconcepts``
    list (RxNav returns it in one response; we page through it so the rest of
    the pipeline sees a uniform paginated ``fetch``).
    """
    base_url: str = RXNAV_BASE
    user_agent: str = _DEFAULT_USER_AGENT
    timeout_s: int = 30
    retry_count: int = 4
    min_interval_s: float = _RATE_LIMIT_INTERVAL_S
    batch_size: int = 500
    backoff_base_s: float = 1.0
    backoff_cap_s: float = 30.0
    _last_call_s: float = field(default=0.0, repr=False)
    # Cache the (large) allconcepts payload across pages within one run so we
    # make exactly one network call and paginate locally.
    _allconcepts_cache: Dict[str, List[nz.ConceptRow]] = field(
        default_factory=dict, repr=False)

    # ── discovery ───────────────────────────────────────────────────────
    def discover(self) -> List[Dict[str, Any]]:
        """Enumerate what this connector ingests: the declarative registry rows."""
        return dataset_rows()

    # ── transport ───────────────────────────────────────────────────────
    def _throttle(self, sleep: Callable[[float], None], now: Callable[[], float]) -> None:
        if self.min_interval_s <= 0:
            return
        wait = self.min_interval_s - (now() - self._last_call_s)
        if wait > 0:
            sleep(wait)

    def _backoff(self, attempt: int, retry_after: Optional[float]) -> float:
        """Exponential backoff with full jitter, honouring Retry-After."""
        if retry_after is not None and retry_after > 0:
            return min(retry_after, self.backoff_cap_s)
        ceil = min(self.backoff_base_s * (2 ** attempt), self.backoff_cap_s)
        return random.uniform(0, ceil)

    def _get_json(
        self,
        path: str,
        params: Optional[Dict[str, str]] = None,
        *,
        opener: Optional[Opener] = None,
        sleep: Callable[[float], None] = time.sleep,
        now: Callable[[], float] = time.monotonic,
    ) -> Any:
        """One GET + JSON parse, with rate-limit floor + retry on 429/503/5xx.

        Fails closed: raises :class:`RxNormApiError` rather than returning
        partial/synthetic data. 4xx other than 429 won't fix on retry → raise.
        """
        opener = opener or _default_opener
        url = self.base_url + path
        if params:
            url = f"{url}?{urlencode(params)}"
        headers = {"User-Agent": self.user_agent, "Accept": "application/json"}
        last_exc: Optional[Exception] = None
        for attempt in range(self.retry_count + 1):
            self._throttle(sleep, now)
            try:
                raw = opener(url, headers, self.timeout_s)
                self._last_call_s = now()
                try:
                    return json.loads(raw)
                except json.JSONDecodeError as exc:
                    raise RxNormApiError(
                        f"{url}: non-JSON response ({len(raw)} bytes)") from exc
            except HTTPError as exc:
                last_exc = exc
                self._last_call_s = now()
                if exc.code in (429, 503) or exc.code >= 500:
                    retry_after = None
                    try:
                        ra = exc.headers.get("Retry-After") if exc.headers else None
                        retry_after = float(ra) if ra else None
                    except (TypeError, ValueError):
                        retry_after = None
                    sleep(self._backoff(attempt, retry_after))
                    continue
                raise RxNormApiError(f"{url}: HTTP {exc.code} {exc.reason}") from exc
            except (URLError, TimeoutError, OSError) as exc:
                last_exc = exc
                self._last_call_s = now()
                sleep(self._backoff(attempt, None))
        raise RxNormApiError(
            f"{url}: failed after {self.retry_count + 1} attempts: {last_exc}"
        ) from last_exc

    # ── fetch ───────────────────────────────────────────────────────────
    def fetch(
        self,
        endpoint: str,
        params: Optional[Dict[str, str]] = None,
        cursor: str = "",
        *,
        opener: Optional[Opener] = None,
        sleep: Callable[[float], None] = time.sleep,
        now: Callable[[], float] = time.monotonic,
    ) -> Tuple[List[Dict[str, Any]], str]:
        """Fetch one page from ``endpoint``; return ``(rows, next_cursor)``.

        ``next_cursor`` is ``""`` when there are no more pages. Most RxNav
        endpoints are single-resource (one row group, no pages); only
        ``allconcepts`` paginates, and we do that client-side over the single
        big response so callers see one uniform paging contract.
        """
        params = dict(params or {})
        kw = {"opener": opener, "sleep": sleep, "now": now}

        if endpoint == "allconcepts":
            return self._fetch_allconcepts(params, cursor, **kw)
        if endpoint == "properties":
            rxcui = params["rxcui"]
            payload = self._get_json(f"/rxcui/{rxcui}/properties.json", **kw)
            row = nz.parse_properties(payload)
            return ([_concept_dict(row)] if row else [], "")
        if endpoint == "historystatus":
            rxcui = params["rxcui"]
            payload = self._get_json(f"/rxcui/{rxcui}/historystatus.json", **kw)
            status, remapped_to = nz.parse_historystatus(payload)
            return ([{"rxcui": rxcui, "status": status,
                      "remapped_to_rxcui": remapped_to}], "")
        if endpoint == "allrelated":
            rxcui = params["rxcui"]
            payload = self._get_json(f"/rxcui/{rxcui}/allrelated.json", **kw)
            rows = [{"rxcui": rxcui, "related_rxcui": r, "tty": tty,
                     "relationship": rel}
                    for (r, tty, rel) in nz.parse_related(payload)]
            return (rows, "")
        if endpoint == "ndcs":
            rxcui = params["rxcui"]
            payload = self._get_json(f"/rxcui/{rxcui}/ndcs.json", **kw)
            rows = [{"rxcui": rxcui, "ndc_raw": n}
                    for n in nz.parse_ndcs_for_rxcui(payload)]
            return (rows, "")
        if endpoint == "rxcui_by_ndc":
            ndc = params["id"]
            payload = self._get_json(
                "/rxcui.json", {"idtype": "NDC", "id": ndc}, **kw)
            rows = [{"ndc_raw": ndc, "rxcui": r}
                    for r in nz.parse_rxcui_by_ndc(payload)]
            return (rows, "")
        if endpoint == "ndcproperties":
            ndc = params["id"]
            payload = self._get_json("/ndcproperties.json", {"id": ndc}, **kw)
            return (_parse_ndcproperties(payload), "")
        if endpoint == "approximateterm":
            term = params["term"]
            payload = self._get_json(
                "/approximateTerm.json",
                {"term": term, "maxEntries": params.get("maxEntries", "20")}, **kw)
            return (nz.parse_approximate(payload), "")
        if endpoint == "drugs":
            name = params["name"]
            payload = self._get_json("/drugs.json", {"name": name}, **kw)
            return (nz.parse_drugs(payload), "")
        if endpoint == "rxclass":
            rxcui = params["rxcui"]
            qp = {"rxcui": rxcui}
            if params.get("relaSource"):
                qp["relaSource"] = params["relaSource"]
            payload = self._get_json("/rxclass/class/byRxcui.json", qp, **kw)
            rows = [{"rxcui": c.rxcui, "class_id": c.class_id,
                     "class_name": c.class_name, "class_type": c.class_type}
                    for c in nz.parse_rxclass(payload, rxcui)]
            return (rows, "")

        raise RxNormApiError(f"unknown endpoint: {endpoint!r}")

    def _fetch_allconcepts(
        self, params: Dict[str, str], cursor: str, **kw: Any
    ) -> Tuple[List[Dict[str, Any]], str]:
        tty = params.get("tty", "+".join(nz.IN_SCOPE_TTY))
        if tty not in self._allconcepts_cache:
            payload = self._get_json("/allconcepts.json", {"tty": tty}, **kw)
            self._allconcepts_cache[tty] = nz.parse_allconcepts(payload)
        all_rows = self._allconcepts_cache[tty]
        start = int(cursor) if cursor else 0
        page = all_rows[start:start + self.batch_size]
        rows = [_concept_dict(c) for c in page]
        next_cursor = (str(start + self.batch_size)
                       if start + self.batch_size < len(all_rows) else "")
        return (rows, next_cursor)


def _concept_dict(c: nz.ConceptRow) -> Dict[str, Any]:
    return {"rxcui": c.rxcui, "name": c.name, "tty": c.tty,
            "status": c.status, "remapped_to_rxcui": c.remapped_to_rxcui}


def _parse_ndcproperties(payload: Dict) -> List[Dict[str, Any]]:
    """Parse /ndcproperties.json → flat rows {ndc_raw, rxcui, labeler, packaging}."""
    if not isinstance(payload, dict):
        return []
    lst = (payload.get("ndcPropertyList", {}) or {}).get("ndcProperty", []) or []
    out: List[Dict[str, Any]] = []
    for p in lst:
        out.append({
            "ndc_raw": str(p.get("ndcItem", "") or p.get("ndc11", "")).strip(),
            "rxcui": str(p.get("rxcui", "")).strip(),
            "labeler": _ndc_attr(p, "LABELER"),
            "packaging": _ndc_attr(p, "PACKAGE"),
            "status": str(p.get("ndcStatus", "")).strip(),
        })
    return out


def _ndc_attr(prop: Dict, name: str) -> str:
    """Pull one named value out of an ndcProperty propertyConceptList."""
    pcl = (prop.get("propertyConceptList", {}) or {}).get("propertyConcept", []) or []
    for pc in pcl:
        if str(pc.get("propName", "")).strip().upper() == name:
            return str(pc.get("propValue", "")).strip()
    return ""
