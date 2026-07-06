"""Stdlib client scaffolds for the top free public-health-data APIs.

The field-guide "wire up first" set: NPPES, openFDA, ClinicalTrials.gov v2,
RxNorm, the Census APIs, and ProPublica Nonprofit Explorer. Each is free and
key-optional (a free key only raises rate limits). This module supplies a
single shared transport with the auth / rate-limit / retry behaviour already
wired in, plus pure URL builders and thin typed fetchers per API.

Design for testability and for a no-egress render path:
  * URL/param construction is **pure** (``*_request`` builders return an
    ``ApiRequest`` you can assert on without a network).
  * Transport is **injectable** (``HttpJsonClient.get_json(opener=...)``) so
    tests exercise retry/rate-limit/parse logic with a fake opener and no
    socket. Default opener is stdlib ``urllib``.
  * Everything **fails closed**: an unreachable API raises ``PublicApiError``
    rather than returning partial/synthetic data. Nothing here runs at import.

Stdlib only (urllib + json + time). No new dependencies. NPPES already has a
fuller client in ``nppes_api_client.py``; this module's NPPES helpers build on
the same endpoint for catalog-driven uniformity.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

_DEFAULT_USER_AGENT = (
    "rcm-mc/public-data-client (github.com/DrewThomas09/RCM_MC; "
    "commercial-diligence research — contact: research@example.com)"
)

# Opener signature: (url, headers, timeout_s) -> raw bytes.
Opener = Callable[[str, Dict[str, str], int], bytes]
# POST opener signature: (url, headers, body_bytes, timeout_s) -> raw bytes.
PostOpener = Callable[[str, Dict[str, str], bytes, int], bytes]


class PublicApiError(RuntimeError):
    """Raised when a public API is unreachable or returns unexpected data."""


# --------------------------------------------------------------------------
# Pure request description — build it without touching the network.
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class ApiRequest:
    url: str
    params: Dict[str, str] = field(default_factory=dict)

    @property
    def full_url(self) -> str:
        if not self.params:
            return self.url
        sep = "&" if "?" in self.url else "?"
        return f"{self.url}{sep}{urlencode(self.params)}"


def _default_opener(url: str, headers: Dict[str, str], timeout_s: int) -> bytes:
    req = Request(url, headers=headers)
    with urlopen(req, timeout=timeout_s) as resp:
        return resp.read()


def _default_post_opener(url: str, headers: Dict[str, str], body: bytes,
                         timeout_s: int) -> bytes:
    req = Request(url, data=body, headers=headers, method="POST")
    with urlopen(req, timeout=timeout_s) as resp:
        return resp.read()


# --------------------------------------------------------------------------
# Shared transport: retry-on-transient + a minimum inter-request interval so a
# loop of calls stays under an API's advertised rate limit.
# --------------------------------------------------------------------------
@dataclass
class HttpJsonClient:
    base_url: str
    user_agent: str = _DEFAULT_USER_AGENT
    timeout_s: int = 30
    retry_count: int = 2
    retry_backoff_s: float = 1.5
    min_interval_s: float = 0.0          # rate-limit floor between requests
    api_key: Optional[str] = None
    api_key_param: Optional[str] = None  # query param name for the key, if any
    _last_call_s: float = field(default=0.0, repr=False)

    def _throttle(self, sleep: Callable[[float], None], now: Callable[[], float]) -> None:
        if self.min_interval_s <= 0:
            return
        elapsed = now() - self._last_call_s
        wait = self.min_interval_s - elapsed
        if wait > 0:
            sleep(wait)

    def request(self, path: str = "", params: Optional[Dict[str, str]] = None) -> ApiRequest:
        """Build the request (pure). Merges the API key in if configured."""
        merged: Dict[str, str] = dict(params or {})
        if self.api_key and self.api_key_param:
            merged.setdefault(self.api_key_param, self.api_key)
        url = self.base_url + path if path else self.base_url
        return ApiRequest(url=url, params=merged)

    def get_json(
        self,
        path: str = "",
        params: Optional[Dict[str, str]] = None,
        *,
        opener: Optional[Opener] = None,
        sleep: Callable[[float], None] = time.sleep,
        now: Callable[[], float] = time.monotonic,
    ) -> Any:
        """Issue one GET and parse JSON, with retry + rate-limit floor.

        ``opener`` is injectable so the retry/parse path is testable without a
        socket. Raises ``PublicApiError`` on unrecoverable transport or parse
        failure — never returns partial data.
        """
        opener = opener or _default_opener
        req = self.request(path, params)
        headers = {"User-Agent": self.user_agent, "Accept": "application/json"}
        last_exc: Optional[Exception] = None
        for attempt in range(self.retry_count + 1):
            self._throttle(sleep, now)
            try:
                raw = opener(req.full_url, headers, self.timeout_s)
                self._last_call_s = now()
                try:
                    return json.loads(raw)
                except json.JSONDecodeError as exc:
                    raise PublicApiError(
                        f"{self.base_url}: non-JSON response ({len(raw)} bytes)"
                    ) from exc
            except HTTPError as exc:
                last_exc = exc
                self._last_call_s = now()
                if exc.code < 500:  # 4xx won't fix on retry
                    raise PublicApiError(
                        f"{req.full_url}: HTTP {exc.code} {exc.reason}"
                    ) from exc
                sleep(self.retry_backoff_s * (attempt + 1))
            except (URLError, TimeoutError, OSError) as exc:
                last_exc = exc
                self._last_call_s = now()
                sleep(self.retry_backoff_s * (attempt + 1))
        raise PublicApiError(
            f"{self.base_url}: failed after {self.retry_count + 1} attempts: "
            f"{last_exc}"
        ) from last_exc

    def post_json(
        self,
        path: str,
        body: Any,
        *,
        opener: Optional[PostOpener] = None,
        sleep: Callable[[float], None] = time.sleep,
        now: Callable[[], float] = time.monotonic,
    ) -> Any:
        """POST a JSON ``body`` and parse the JSON response — same retry,
        rate-limit and fail-closed semantics as ``get_json``. Used by APIs that
        take a query in the request body (USAspending, BLS)."""
        opener = opener or _default_post_opener
        url = self.base_url + path if path else self.base_url
        payload = json.dumps(body).encode("utf-8")
        headers = {"User-Agent": self.user_agent,
                   "Accept": "application/json",
                   "Content-Type": "application/json"}
        last_exc: Optional[Exception] = None
        for attempt in range(self.retry_count + 1):
            self._throttle(sleep, now)
            try:
                raw = opener(url, headers, payload, self.timeout_s)
                self._last_call_s = now()
                try:
                    return json.loads(raw)
                except json.JSONDecodeError as exc:
                    raise PublicApiError(
                        f"{self.base_url}: non-JSON response ({len(raw)} bytes)"
                    ) from exc
            except HTTPError as exc:
                last_exc = exc
                self._last_call_s = now()
                if exc.code < 500:
                    raise PublicApiError(
                        f"{url}: HTTP {exc.code} {exc.reason}") from exc
                sleep(self.retry_backoff_s * (attempt + 1))
            except (URLError, TimeoutError, OSError) as exc:
                last_exc = exc
                self._last_call_s = now()
                sleep(self.retry_backoff_s * (attempt + 1))
        raise PublicApiError(
            f"{self.base_url}: POST failed after {self.retry_count + 1} "
            f"attempts: {last_exc}") from last_exc


# --------------------------------------------------------------------------
# Per-API request builders (pure) + thin fetchers. base URLs mirror the
# catalog in public_api_catalog.py.
# --------------------------------------------------------------------------

# openFDA — https://api.fda.gov/{noun}/{endpoint}.json?search=...&limit=...
_OPENFDA_BASE = "https://api.fda.gov"


def openfda_request(noun: str, endpoint: str, *, search: str = "",
                    count: str = "", limit: int = 1, skip: int = 0,
                    api_key: str = "") -> ApiRequest:
    """Build an openFDA query. ``noun`` is drug|device|food; ``endpoint`` is
    e.g. event, 510k, enforcement, ndc, label."""
    params: Dict[str, str] = {"limit": str(max(1, min(int(limit), 1000)))}
    if search:
        params["search"] = search
    if count:
        params["count"] = count
    if skip:
        params["skip"] = str(int(skip))
    if api_key:
        params["api_key"] = api_key
    url = f"{_OPENFDA_BASE}/{noun}/{endpoint}.json"
    return ApiRequest(url=url, params=params)


def openfda_search(noun: str, endpoint: str, *, opener: Optional[Opener] = None,
                   **kw: Any) -> List[Dict[str, Any]]:
    api_key = kw.pop("api_key", "")
    req = openfda_request(noun, endpoint, api_key=api_key, **kw)
    client = HttpJsonClient(base_url=_OPENFDA_BASE, min_interval_s=0.25)
    payload = client.get_json(req.url.replace(_OPENFDA_BASE, ""),
                              req.params, opener=opener)
    return payload.get("results", []) if isinstance(payload, dict) else []


# ClinicalTrials.gov API v2 — https://clinicaltrials.gov/api/v2/studies?query.term=
_CTGOV_BASE = "https://clinicaltrials.gov/api/v2"


def clinicaltrials_request(*, term: str = "", condition: str = "",
                           sponsor: str = "", phase: str = "",
                           page_size: int = 20,
                           page_token: str = "") -> ApiRequest:
    params: Dict[str, str] = {"format": "json",
                              "pageSize": str(max(1, min(int(page_size), 1000)))}
    if term:
        params["query.term"] = term
    if condition:
        params["query.cond"] = condition
    if sponsor:
        params["query.spons"] = sponsor
    if phase:
        params["filter.advanced"] = f"AREA[Phase]{phase}"
    if page_token:
        params["pageToken"] = page_token
    return ApiRequest(url=f"{_CTGOV_BASE}/studies", params=params)


def clinicaltrials_search(*, opener: Optional[Opener] = None,
                          **kw: Any) -> List[Dict[str, Any]]:
    req = clinicaltrials_request(**kw)
    client = HttpJsonClient(base_url=_CTGOV_BASE, min_interval_s=0.2)
    payload = client.get_json("/studies", req.params, opener=opener)
    return payload.get("studies", []) if isinstance(payload, dict) else []


# NLM RxNorm (RxNav) — https://rxnav.nlm.nih.gov/REST/rxcui.json?name=...
_RXNORM_BASE = "https://rxnav.nlm.nih.gov/REST"


def rxnorm_rxcui_request(name: str, *, search: int = 2) -> ApiRequest:
    return ApiRequest(url=f"{_RXNORM_BASE}/rxcui.json",
                      params={"name": name, "search": str(int(search))})


def rxnorm_rxcui(name: str, *, opener: Optional[Opener] = None) -> List[str]:
    req = rxnorm_rxcui_request(name)
    client = HttpJsonClient(base_url=_RXNORM_BASE, min_interval_s=0.05)
    payload = client.get_json("/rxcui.json", req.params, opener=opener)
    grp = (payload or {}).get("idGroup", {}) if isinstance(payload, dict) else {}
    return list(grp.get("rxnormId", []) or [])


def _clean_ndc(ndc: str) -> str:
    """Strip spaces; keep digits and hyphens. RxNav accepts hyphenated 5-4-2
    and 11-digit NDCs, and openFDA emits both ``product_ndc`` (no package
    segment) and ``package_ndc`` (full) — pass either through unchanged so the
    caller's missingness is preserved rather than guessing a reformat."""
    return "".join(ch for ch in str(ndc).strip() if ch.isdigit() or ch == "-")


def rxnorm_ndc_request(ndc: str) -> ApiRequest:
    """NDC -> RxCUI via the RxNav id crosswalk (``idtype=NDC``). Same
    ``rxcui.json`` endpoint as name lookup, different id type."""
    return ApiRequest(url=f"{_RXNORM_BASE}/rxcui.json",
                      params={"idtype": "NDC", "id": _clean_ndc(ndc)})


def rxnorm_ndc_to_rxcui(ndc: str, *, opener: Optional[Opener] = None) -> List[str]:
    req = rxnorm_ndc_request(ndc)
    client = HttpJsonClient(base_url=_RXNORM_BASE, min_interval_s=0.05)
    payload = client.get_json("/rxcui.json", req.params, opener=opener)
    grp = (payload or {}).get("idGroup", {}) if isinstance(payload, dict) else {}
    return list(grp.get("rxnormId", []) or [])


def rxnorm_hcpcs_request(hcpcs: str) -> ApiRequest:
    """HCPCS code -> RxCUI via the RxNav id crosswalk (``idtype=HCPCS``).

    HCPCS is a source vocabulary inside RxNorm, so a J-code (injectable /
    infusion drug, e.g. ``J1745`` infliximab) resolves to a normalized drug
    concept with no NDC or free-text name in the file — the join that lets a
    J-code-dominant claims extract (infusion pharmacy, oncology) light up the
    drug connectors it obviously needs."""
    code = "".join(ch for ch in str(hcpcs or "").upper()
                   if ch.isalnum())
    return ApiRequest(url=f"{_RXNORM_BASE}/rxcui.json",
                      params={"idtype": "HCPCS", "id": code})


def rxnorm_hcpcs_to_rxcui(hcpcs: str, *, opener: Optional[Opener] = None
                          ) -> List[str]:
    req = rxnorm_hcpcs_request(hcpcs)
    client = HttpJsonClient(base_url=_RXNORM_BASE, min_interval_s=0.05)
    payload = client.get_json("/rxcui.json", req.params, opener=opener)
    grp = (payload or {}).get("idGroup", {}) if isinstance(payload, dict) else {}
    return list(grp.get("rxnormId", []) or [])


def rxnorm_ndcs_request(rxcui: str) -> ApiRequest:
    """RxCUI -> the NDCs that map to it (``/rxcui/{rxcui}/ndcs.json``)."""
    digits = "".join(ch for ch in str(rxcui) if ch.isdigit())
    return ApiRequest(url=f"{_RXNORM_BASE}/rxcui/{digits}/ndcs.json")


def rxnorm_rxcui_ndcs(rxcui: str, *, opener: Optional[Opener] = None) -> List[str]:
    digits = "".join(ch for ch in str(rxcui) if ch.isdigit())
    client = HttpJsonClient(base_url=_RXNORM_BASE, min_interval_s=0.05)
    payload = client.get_json(f"/rxcui/{digits}/ndcs.json", opener=opener)
    grp = (payload or {}).get("ndcGroup", {}) if isinstance(payload, dict) else {}
    lst = grp.get("ndcList", {}) or {}
    return list(lst.get("ndc", []) or [])


def rxnorm_properties_request(rxcui: str) -> ApiRequest:
    """RxCUI -> concept properties (name, term type) for normalization."""
    digits = "".join(ch for ch in str(rxcui) if ch.isdigit())
    return ApiRequest(url=f"{_RXNORM_BASE}/rxcui/{digits}/properties.json")


def rxnorm_properties(rxcui: str, *, opener: Optional[Opener] = None
                      ) -> Dict[str, Any]:
    digits = "".join(ch for ch in str(rxcui) if ch.isdigit())
    client = HttpJsonClient(base_url=_RXNORM_BASE, min_interval_s=0.05)
    payload = client.get_json(f"/rxcui/{digits}/properties.json", opener=opener)
    props = (payload or {}).get("properties", {}) if isinstance(payload, dict) else {}
    return props if isinstance(props, dict) else {}


def rxnorm_normalize(value: str, *, by: str = "name",
                     opener: Optional[Opener] = None) -> Dict[str, Any]:
    """Resolve a drug name or NDC to a stable normalized concept record:
    ``{rxcui, name, tty, ndcs}``. Returns ``{}`` (not a fabricated concept)
    when nothing resolves — the caller must treat an empty dict as unmatched.

    ``by`` is ``"name"``, ``"ndc"``, or ``"hcpcs"`` (J-code / HCPCS drug
    code). One concept is returned (the first RxCUI); ambiguity is the
    caller's to resolve from the raw id list if it needs every candidate.
    """
    if by == "ndc":
        rxcuis = rxnorm_ndc_to_rxcui(value, opener=opener)
    elif by == "hcpcs":
        rxcuis = rxnorm_hcpcs_to_rxcui(value, opener=opener)
    else:
        rxcuis = rxnorm_rxcui(value, opener=opener)
    if not rxcuis:
        return {}
    rxcui = str(rxcuis[0])
    props = rxnorm_properties(rxcui, opener=opener)
    return {
        "rxcui": rxcui,
        "name": props.get("name", ""),
        "tty": props.get("tty", ""),
        "ndcs": rxnorm_rxcui_ndcs(rxcui, opener=opener),
    }


def openfda_ndc_to_rxcui(ndcs: List[str], *, opener: Optional[Opener] = None
                         ) -> Dict[str, List[str]]:
    """Bridge openFDA drug NDCs to RxNorm concepts — the join that lets the
    vendored openFDA drug layer (``product_ndc`` / ``package_ndc``) resolve to
    a normalized RxCUI.

    Returns ``{ndc: [rxcui, ...]}`` for every input NDC; an unresolved NDC maps
    to ``[]`` rather than being dropped, so downstream missingness is explicit
    and never silently imputed. De-duplicates inputs while preserving order.
    """
    out: Dict[str, List[str]] = {}
    for ndc in ndcs:
        key = _clean_ndc(ndc)
        if not key or key in out:
            continue
        out[key] = rxnorm_ndc_to_rxcui(key, opener=opener)
    return out


# Census APIs — https://api.census.gov/data/{year}/{dataset}?get=...&for=...&key=
_CENSUS_BASE = "https://api.census.gov/data"


def census_request(year: int, dataset: str, *, get: List[str],
                   for_geo: str, in_geo: str = "", api_key: str = "") -> ApiRequest:
    params: Dict[str, str] = {"get": ",".join(get), "for": for_geo}
    if in_geo:
        params["in"] = in_geo
    if api_key:
        params["key"] = api_key
    return ApiRequest(url=f"{_CENSUS_BASE}/{year}/{dataset}", params=params)


def census_get(year: int, dataset: str, *, get: List[str], for_geo: str,
               in_geo: str = "", api_key: str = "",
               opener: Optional[Opener] = None) -> List[Dict[str, str]]:
    """Census returns a header row + data rows; zip into list-of-dicts."""
    req = census_request(year, dataset, get=get, for_geo=for_geo,
                         in_geo=in_geo, api_key=api_key)
    client = HttpJsonClient(base_url=_CENSUS_BASE)
    payload = client.get_json(f"/{year}/{dataset}", req.params, opener=opener)
    if not isinstance(payload, list) or len(payload) < 2:
        return []
    header = payload[0]
    return [dict(zip(header, row)) for row in payload[1:]]


# ProPublica Nonprofit Explorer — IRS Form 990
_PROPUBLICA_BASE = "https://projects.propublica.org/nonprofits/api/v2"


def propublica_search_request(query: str, *, state: str = "",
                              ntee: str = "", page: int = 0) -> ApiRequest:
    params: Dict[str, str] = {"q": query, "page": str(int(page))}
    if state:
        params["state%5Bid%5D"] = state
    if ntee:
        params["ntee%5Bid%5D"] = ntee
    return ApiRequest(url=f"{_PROPUBLICA_BASE}/search.json", params=params)


def propublica_organization_request(ein: str) -> ApiRequest:
    digits = "".join(ch for ch in str(ein) if ch.isdigit())
    return ApiRequest(url=f"{_PROPUBLICA_BASE}/organizations/{digits}.json")


def propublica_search(query: str, *, opener: Optional[Opener] = None,
                      **kw: Any) -> List[Dict[str, Any]]:
    req = propublica_search_request(query, **kw)
    client = HttpJsonClient(base_url=_PROPUBLICA_BASE, min_interval_s=0.2)
    payload = client.get_json("/search.json", req.params, opener=opener)
    return payload.get("organizations", []) if isinstance(payload, dict) else []


def propublica_organization(ein: str, *, opener: Optional[Opener] = None
                            ) -> Dict[str, Any]:
    req = propublica_organization_request(ein)
    client = HttpJsonClient(base_url=_PROPUBLICA_BASE, min_interval_s=0.2)
    digits = "".join(ch for ch in str(ein) if ch.isdigit())
    payload = client.get_json(f"/organizations/{digits}.json", opener=opener)
    return payload if isinstance(payload, dict) else {}


# NPPES NPI Registry — https://npiregistry.cms.hhs.gov/api/?version=2.1
# (provider universe; the fuller client lives in nppes_api_client.py)
_NPPES_BASE = "https://npiregistry.cms.hhs.gov/api/"


def nppes_request(*, organization_name: str = "", npi: str = "",
                  state: str = "", city: str = "",
                  enumeration_type: str = "", taxonomy_description: str = "",
                  limit: int = 200, version: str = "2.1") -> ApiRequest:
    params: Dict[str, str] = {"version": version,
                              "limit": str(max(1, min(int(limit), 200)))}
    if organization_name:
        params["organization_name"] = organization_name
    if npi:
        params["number"] = str(npi)
    if state:
        params["state"] = state
    if city:
        params["city"] = city
    if enumeration_type:
        params["enumeration_type"] = enumeration_type
    if taxonomy_description:
        params["taxonomy_description"] = taxonomy_description
    return ApiRequest(url=_NPPES_BASE, params=params)


# WHO Global Health Observatory — OData. https://ghoapi.azureedge.net/api/{IND}
_WHO_GHO_BASE = "https://ghoapi.azureedge.net/api"


def who_gho_request(indicator: str, *, country: str = "", year: str = "",
                    sex: str = "") -> ApiRequest:
    """Fetch a GHO indicator series, optionally filtered with an OData
    ``$filter`` over country (SpatialDim), year (TimeDim), sex (Dim1)."""
    clauses: List[str] = []
    if country:
        clauses.append(f"SpatialDim eq '{country}'")
    if year:
        clauses.append(f"TimeDim eq {int(year)}")
    if sex:
        clauses.append(f"Dim1 eq '{sex}'")
    params: Dict[str, str] = {}
    if clauses:
        params["$filter"] = " and ".join(clauses)
    return ApiRequest(url=f"{_WHO_GHO_BASE}/{indicator}", params=params)


def who_gho_indicator(indicator: str, *, opener: Optional[Opener] = None,
                      **kw: Any) -> List[Dict[str, Any]]:
    req = who_gho_request(indicator, **kw)
    client = HttpJsonClient(base_url=_WHO_GHO_BASE, min_interval_s=0.1)
    payload = client.get_json(f"/{indicator}", req.params, opener=opener)
    return payload.get("value", []) if isinstance(payload, dict) else []


# SEC EDGAR — company facts/concepts. https://data.sec.gov/api/xbrl/...
_SEC_BASE = "https://data.sec.gov"


def sec_companyfacts_request(cik: str) -> ApiRequest:
    """All XBRL facts for a company. CIK is zero-padded to 10 digits."""
    digits = "".join(ch for ch in str(cik) if ch.isdigit())
    cik10 = digits.zfill(10)
    return ApiRequest(url=f"{_SEC_BASE}/api/xbrl/companyfacts/CIK{cik10}.json")


def sec_concept_request(cik: str, taxonomy: str, tag: str) -> ApiRequest:
    digits = "".join(ch for ch in str(cik) if ch.isdigit())
    cik10 = digits.zfill(10)
    return ApiRequest(
        url=f"{_SEC_BASE}/api/xbrl/companyconcept/CIK{cik10}/{taxonomy}/{tag}.json")


# HRSA data warehouse — OData. https://data.hrsa.gov/api/...
_HRSA_BASE = "https://data.hrsa.gov/api"


def hrsa_request(dataset: str, *, top: int = 100, skip: int = 0,
                 odata_filter: str = "") -> ApiRequest:
    params: Dict[str, str] = {"$format": "json",
                              "$top": str(max(1, min(int(top), 1000)))}
    if skip:
        params["$skip"] = str(int(skip))
    if odata_filter:
        params["$filter"] = odata_filter
    return ApiRequest(url=f"{_HRSA_BASE}/{dataset}", params=params)


# USAspending — POST body. https://api.usaspending.gov/api/v2/...
_USASPENDING_BASE = "https://api.usaspending.gov/api/v2"


def usaspending_recipient_body(name: str, *, award_types: Optional[List[str]] = None,
                               limit: int = 10) -> Dict[str, Any]:
    """Body for spending_by_award keyword search on a recipient name."""
    return {
        "filters": {
            "keywords": [name],
            "award_type_codes": award_types or ["A", "B", "C", "D"],
        },
        "fields": ["Award ID", "Recipient Name", "Award Amount",
                   "Awarding Agency"],
        "limit": max(1, min(int(limit), 100)),
        "page": 1,
    }


def usaspending_spending_by_award(name: str, *,
                                  opener: Optional[PostOpener] = None,
                                  **kw: Any) -> List[Dict[str, Any]]:
    body = usaspending_recipient_body(name, **kw)
    client = HttpJsonClient(base_url=_USASPENDING_BASE, min_interval_s=0.2)
    payload = client.post_json("/search/spending_by_award/", body,
                               opener=opener)
    return payload.get("results", []) if isinstance(payload, dict) else []


# BLS — POST body. https://api.bls.gov/publicAPI/v2/timeseries/data/
_BLS_BASE = "https://api.bls.gov/publicAPI/v2"


def bls_timeseries_body(series_ids: List[str], *, start_year: str = "",
                        end_year: str = "", api_key: str = "") -> Dict[str, Any]:
    body: Dict[str, Any] = {"seriesid": list(series_ids)}
    if start_year:
        body["startyear"] = str(start_year)
    if end_year:
        body["endyear"] = str(end_year)
    if api_key:
        body["registrationkey"] = api_key
    return body


def bls_timeseries(series_ids: List[str], *, opener: Optional[PostOpener] = None,
                   **kw: Any) -> List[Dict[str, Any]]:
    body = bls_timeseries_body(series_ids, **kw)
    client = HttpJsonClient(base_url=_BLS_BASE, min_interval_s=0.2)
    payload = client.post_json("/timeseries/data/", body, opener=opener)
    if not isinstance(payload, dict):
        return []
    return (payload.get("Results", {}) or {}).get("series", []) or []


# Registry of the wired clients, for catalog-driven discovery/tests.
CLIENT_BUILDERS: Dict[str, Callable[..., ApiRequest]] = {
    "nppes": nppes_request,
    "sec_edgar": sec_companyfacts_request,
    "hrsa": hrsa_request,
    "openfda": openfda_request,
    "clinicaltrials": clinicaltrials_request,
    "rxnorm": rxnorm_rxcui_request,
    "rxnorm_ndc": rxnorm_ndc_request,
    "rxnorm_ndcs": rxnorm_ndcs_request,
    "rxnorm_properties": rxnorm_properties_request,
    "census_acs": lambda **kw: census_request(**kw),
    "propublica_990": propublica_search_request,
    "who_gho": who_gho_request,
}


def available_clients() -> List[str]:
    return sorted(CLIENT_BUILDERS.keys())
