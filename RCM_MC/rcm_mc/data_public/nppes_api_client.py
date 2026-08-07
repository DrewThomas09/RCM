"""NPPES NPI Registry API client (live).

The CMS NPI Registry exposes a free, key-less JSON API for resolving
provider names and organizational details by NPI. Used during
commercial diligence to:

  - Enumerate providers at a hospital (Type-2 organization NPI →
    Type-1 individual NPIs linked by practice address).
  - Surface specialty / taxonomy mix per facility.
  - Detect provider concentration risk (top-N producers as a
    share of total roster).

Endpoint: https://npiregistry.cms.hhs.gov/api/?version=2.1

Rate behaviour: NPPES does not advertise a strict rate limit but
returns 503 on aggressive querying. The client retries on transient
errors with exponential backoff and caps per-request results at
200 (NPPES hard cap).

Single-machine, stdlib-only (urllib + json). No new dependencies.

Public API:
    NppesApiError                       — raised on transport / parse failures
    NppesProvider                       — dataclass for one search result
    search_by_organization(name, state) — lookup organization NPIs
    search_by_address(addr, state)      — lookup individuals at a practice address
    fetch_by_npi(npi)                   — single-NPI detail fetch
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


NPPES_BASE = "https://npiregistry.cms.hhs.gov/api/"
_DEFAULT_VERSION = "2.1"
_MAX_LIMIT = 200  # NPPES hard cap per request
# NPPES will not skip past 1,000, so 200 + 1,000 is the most any single
# query can ever enumerate. A server limit, not ours.
_MAX_TOTAL = 1200
# rOpenSci's npi package waits this long between paged calls. NPPES
# does not publish a rate limit but returns 503 under load, and a
# harvest that trips that is slower than one that paces itself.
_THROTTLE_S = 1.5
# ASCII only, and deliberately so. HTTP header values are encoded
# latin-1 by ``http.client.putheader``, which raises UnicodeEncodeError
# on anything above U+00FF — before a socket is even opened. This
# string carried an em dash, so every live NPPES call raised, and
# ``capiq._default_npi_fetch`` caught it under a bare ``except
# Exception: return []`` and reported UNMATCHED. A transport bug that
# presents as "no such provider" is the worst kind, because the answer
# looks like data.
_DEFAULT_USER_AGENT = (
    "rcm-mc/data-public-nppes (github.com/DrewThomas09/RCM_MC; "
    "commercial-diligence research - contact: research@example.com)"
)


class NppesApiError(RuntimeError):
    """Raised when the NPPES API is unreachable or returns
    unexpected data."""


@dataclass(frozen=True)
class NppesProvider:
    """One provider record from the NPPES registry.

    Includes only the fields commercial-diligence partners use during
    a Phase-1 provider scan. Full raw response is retained on
    ``raw_record`` for downstream enrichment.
    """

    npi: str
    entity_type: int  # 1 = individual, 2 = organization
    name: str
    first_name: str = ""
    last_name: str = ""
    organization_name: str = ""
    taxonomy_code: str = ""
    taxonomy_label: str = ""
    primary_specialty: str = ""
    address_line: str = ""
    city: str = ""
    state: str = ""
    postal_code: str = ""
    phone: str = ""
    enumeration_date: str = ""
    last_updated: str = ""
    raw_record: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_organization(self) -> bool:
        return self.entity_type == 2

    @property
    def is_individual(self) -> bool:
        return self.entity_type == 1


def _request_json(
    params: Dict[str, str],
    *,
    timeout_s: int = 30,
    retry_count: int = 2,
    retry_backoff_s: float = 1.5,
    user_agent: str = _DEFAULT_USER_AGENT,
) -> Dict[str, Any]:
    """Issue a single NPPES API request with retry-on-transient.

    NPPES occasionally returns 503 under load; the registry is
    public + key-less so backoff is the only mitigation. Two retries
    by default; total wait < 5s before giving up.
    """
    qs = urlencode(params)
    url = f"{NPPES_BASE}?{qs}"
    last_exc: Optional[Exception] = None
    for attempt in range(retry_count + 1):
        req = Request(url, headers={"User-Agent": user_agent})
        try:
            with urlopen(req, timeout=timeout_s) as resp:
                body = resp.read()
                try:
                    return json.loads(body)
                except json.JSONDecodeError as exc:
                    raise NppesApiError(
                        f"NPPES returned non-JSON body ({len(body)} "
                        f"bytes): {exc}"
                    ) from exc
        except HTTPError as exc:
            last_exc = exc
            # 503 = retry; 4xx = give up immediately
            if exc.code < 500:
                raise NppesApiError(
                    f"NPPES HTTP {exc.code} on {url}: "
                    f"{exc.reason}"
                ) from exc
            time.sleep(retry_backoff_s * (attempt + 1))
        except URLError as exc:
            last_exc = exc
            time.sleep(retry_backoff_s * (attempt + 1))
    raise NppesApiError(
        f"NPPES request failed after {retry_count + 1} attempts: "
        f"{last_exc}"
    ) from last_exc


def _parse_record(rec: Dict[str, Any]) -> NppesProvider:
    """Map one NPPES result row → NppesProvider."""
    basic = rec.get("basic", {}) or {}
    addresses = rec.get("addresses", []) or []
    taxonomies = rec.get("taxonomies", []) or []
    primary_addr: Dict[str, Any] = {}
    for a in addresses:
        if (a or {}).get("address_purpose") == "LOCATION":
            primary_addr = a
            break
    if not primary_addr and addresses:
        primary_addr = addresses[0]
    primary_taxo: Dict[str, Any] = {}
    for t in taxonomies:
        if (t or {}).get("primary"):
            primary_taxo = t
            break
    if not primary_taxo and taxonomies:
        primary_taxo = taxonomies[0]

    entity_type_str = str(rec.get("enumeration_type", "")).strip()
    # "NPI-1" → individual, "NPI-2" → organization
    if entity_type_str.endswith("1"):
        entity_type = 1
    elif entity_type_str.endswith("2"):
        entity_type = 2
    else:
        entity_type = 0

    org_name = basic.get("organization_name") or ""
    first = basic.get("first_name") or ""
    last = basic.get("last_name") or ""
    name = (
        org_name if org_name
        else f"{first} {last}".strip() or f"NPI {rec.get('number','')}"
    )

    return NppesProvider(
        npi=str(rec.get("number", "")),
        entity_type=entity_type,
        name=name,
        first_name=first,
        last_name=last,
        organization_name=org_name,
        taxonomy_code=primary_taxo.get("code", "") or "",
        taxonomy_label=primary_taxo.get("desc", "") or "",
        primary_specialty=(
            primary_taxo.get("desc", "") or primary_taxo.get("code", "")
        ),
        address_line=primary_addr.get("address_1", "") or "",
        city=primary_addr.get("city", "") or "",
        state=primary_addr.get("state", "") or "",
        postal_code=primary_addr.get("postal_code", "") or "",
        phone=primary_addr.get("telephone_number", "") or "",
        enumeration_date=basic.get("enumeration_date", "") or "",
        last_updated=basic.get("last_updated", "") or "",
        raw_record=rec,
    )


def _parse_results(
    payload: Dict[str, Any],
) -> List[NppesProvider]:
    """Map full NPPES response → list of NppesProvider."""
    if "Errors" in payload and payload["Errors"]:
        first = payload["Errors"][0] if payload["Errors"] else {}
        raise NppesApiError(
            f"NPPES error: {first.get('description', payload['Errors'])}"
        )
    return [_parse_record(r) for r in payload.get("results", []) or []]


def paginate(
    params: Dict[str, str],
    *,
    limit: int = _MAX_LIMIT,
    throttle_s: float = _THROTTLE_S,
    sleep: Any = time.sleep,
) -> List[NppesProvider]:
    """Walk one NPPES query past its 200-record page, up to the API cap.

    The API returns at most 200 records per call and will not skip past
    1,000, so **1,200 records is the hard ceiling for any one query** —
    not a client limit, a server one. A query with more matches than
    that cannot be enumerated, and the honest response is to narrow the
    query (add a state, a taxonomy, a postal prefix) rather than to
    believe the first 1,200.

    That ceiling is why this cannot harvest the register. Eight million
    NPIs at 1,200 per query is not a pagination problem, it is a
    different source: the monthly dissemination file, which
    :mod:`rcm_mc.data.nppes_ingest` streams.

    Loop discipline follows the rOpenSci ``npi`` package, which solved
    this first: ``skip`` is the count already returned, each page asks
    for whatever is still wanted up to 200, and a page that comes back
    short ends the walk. The short-page stop is the load-bearing part —
    without it a query whose result set is exhausted spins against the
    cap re-requesting nothing.
    """
    wanted = max(1, min(int(limit), _MAX_TOTAL))
    out: List[NppesProvider] = []
    while len(out) < wanted:
        page_size = min(_MAX_LIMIT, wanted - len(out))
        page_params = dict(params)
        page_params["limit"] = str(page_size)
        if out:
            page_params["skip"] = str(len(out))
        page = _parse_results(_request_json(page_params))
        if not page:
            break
        out.extend(page)
        if len(page) < page_size:
            # The server had nothing more to give. Asking again returns
            # the same short page forever.
            break
        if len(out) < wanted:
            sleep(throttle_s)
    return out[:wanted]


def search_by_organization(
    organization_name: str,
    state: str = "",
    *,
    limit: int = _MAX_LIMIT,
    enumeration_type: str = "NPI-2",
    version: str = _DEFAULT_VERSION,
) -> List[NppesProvider]:
    """Find organization NPIs by name + optional state.

    Use during diligence to resolve a hospital's Type-2 organization
    NPI from its commercial name. Returns up to ``limit`` results
    (NPPES hard cap 200). Wildcard matching: NPPES supports trailing
    ``*`` on name searches; the caller should add it explicitly.
    """
    params = {
        "version": version,
        "organization_name": organization_name,
        "enumeration_type": enumeration_type,
    }
    if state:
        params["state"] = state
    return paginate(params, limit=limit)


def search_by_address(
    city: str,
    state: str,
    *,
    postal_code: str = "",
    enumeration_type: str = "NPI-1",
    taxonomy_description: str = "",
    limit: int = _MAX_LIMIT,
    version: str = _DEFAULT_VERSION,
) -> List[NppesProvider]:
    """Find individuals/orgs at a practice address.

    Used after resolving an organization's location to enumerate
    employed/affiliated providers at the practice address. NPPES
    matches against the LOCATION address purpose by default.

    Pass ``taxonomy_description`` to narrow by specialty (e.g.
    ``"Internal Medicine"``).
    """
    params = {
        "version": version,
        "city": city,
        "state": state,
        "enumeration_type": enumeration_type,
    }
    if postal_code:
        params["postal_code"] = postal_code
    if taxonomy_description:
        params["taxonomy_description"] = taxonomy_description
    return paginate(params, limit=limit)


def fetch_by_npi(npi: str, *, version: str = _DEFAULT_VERSION) -> Optional[NppesProvider]:
    """Single-NPI detail fetch. Returns None if NPI not found."""
    params = {"version": version, "number": str(npi)}
    results = _parse_results(_request_json(params))
    return results[0] if results else None
