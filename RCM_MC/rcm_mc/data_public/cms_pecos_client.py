"""Stdlib PECOS / Medicare-enrollment client — no third-party deps.

The NPI cleaner's compliance screen wants to check billing NPIs against
the Medicare Fee-For-Service **Public Provider Enrollment** file (are
they actually enrolled?) and the **Opt Out Affidavits** file (an
opted-out provider billing Medicare is a red flag). The vendored v49
``CMSClient`` does this but hard-imports ``requests``, which the platform
does not ship — so on every policy-compliant install the PECOS screen was
permanently dead. This is the same public data over pure ``urllib``.

Design mirrors ``vendor_v49.npi_recovery.clients.CMSClient`` so the two
agree on a real deployment:

  * dataset URLs are resolved from the CMS catalog (``data.cms.gov/data.json``)
    by exact title, taking the ``format=="API" / description=="latest"``
    distribution's ``accessURL`` — so a re-vintaged distribution is picked
    up automatically instead of a hard-coded UUID rotting,
  * the datastore query is ``{accessURL}?filter[NPI]=<npi>&size=&offset=``
    returning a JSON list of row dicts,
  * everything is guarded and short-timed; a blocked network yields ``{}``
    or raises, and the caller (compliance.screen_cms) already runs it
    behind a wall-clock watchdog and swallows failures.

No caching to disk (the caller caps to ≤10 NPIs behind the deep flag);
the catalog fetch is memoized per client instance so one screen touches
``data.json`` at most once.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Dict, List, Optional

CATALOG_URL = "https://data.cms.gov/data.json"

# Exact CMS catalog titles — copied from the vendored config so both
# clients resolve the same distributions. (The double space in the
# enrollment title is intentional; it is how CMS publishes it.)
DATASET_TITLES = {
    "provider_enrollment":
        "Medicare Fee-For-Service  Public Provider Enrollment",
    "opt_out": "Opt Out Affidavits",
}

_USER_AGENT = "rcm-mc-npi-cleaner/1.0 (compliance screen; urllib)"


class CmsPecosClient:
    """Pure-urllib PECOS lookups. Injectable ``opener`` for tests."""

    def __init__(self, timeout: float = 6.0,
                 opener=urllib.request.urlopen) -> None:
        self.timeout = timeout
        self._opener = opener
        self._catalog: Optional[dict] = None
        self._url_cache: Dict[str, str] = {}

    # -- HTTP -------------------------------------------------------------
    def _get_json(self, url: str):
        req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT,
                                                   "Accept": "application/json"})
        with self._opener(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))

    def _catalog_json(self) -> dict:
        if self._catalog is None:
            self._catalog = self._get_json(CATALOG_URL)
        return self._catalog

    def _latest_api_url(self, title: str) -> str:
        if title in self._url_cache:
            return self._url_cache[title]
        for ds in self._catalog_json().get("dataset", []):
            if ds.get("title") == title:
                for d in ds.get("distribution", []):
                    if (d.get("format") == "API"
                            and d.get("description") == "latest"):
                        self._url_cache[title] = d["accessURL"]
                        return d["accessURL"]
        raise ValueError(f"CMS dataset not in catalog: {title!r}")

    def _query_npi(self, title: str, npi: str,
                   size: int = 5) -> List[dict]:
        url = self._latest_api_url(title)
        qs = urllib.parse.urlencode(
            {"filter[NPI]": npi, "size": size, "offset": 0})
        rows = self._get_json(f"{url}?{qs}")
        # The datastore query returns a JSON array of row dicts; some
        # gateways wrap it as {"results": [...]}. Accept both.
        if isinstance(rows, dict):
            rows = rows.get("results") or rows.get("data") or []
        return rows if isinstance(rows, list) else []

    # -- public surface (matches vendored CMSClient) ----------------------
    def enrollment_lookup(self, npi: str) -> dict:
        """Enrolled flag + provider type from the PECOS enrollment file."""
        npi = str(npi).strip()
        if len(npi) != 10 or not npi.isdigit():
            return {}
        rows = self._query_npi(DATASET_TITLES["provider_enrollment"], npi)
        if not rows:
            return {"npi": npi, "enrolled": False}
        r = rows[0]

        def g(k):
            v = r.get(k)
            return str(v).strip() if v is not None else ""
        return {
            "npi": npi, "enrolled": True,
            "provider_type": g("PROVIDER_TYPE_DESC"),
            "provider_type_cd": g("PROVIDER_TYPE_CD"),
            "org_name": g("ORG_NAME"),
            "enrollment_state": g("STATE_CD"),
        }

    def opt_out_lookup(self, npi: str) -> dict:
        """Opt-out status from the Medicare Opt Out Affidavits file."""
        npi = str(npi).strip()
        if len(npi) != 10 or not npi.isdigit():
            return {}
        rows = self._query_npi(DATASET_TITLES["opt_out"], npi)
        if not rows:
            return {"npi": npi, "opted_out": False}
        r = rows[0]

        def g(k):
            v = r.get(k)
            return str(v).strip() if v is not None else ""
        return {
            "npi": npi, "opted_out": True,
            "optout_specialty": g("Specialty"),
            "optout_effective": g("Optout Effective Date"),
            "optout_end": g("Optout End Date"),
        }
