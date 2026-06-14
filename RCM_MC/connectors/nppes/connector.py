"""NppesConnector — the source-facing ingest interface.

Implements the connector contract::

    discover() -> list[dataset descriptors]
    fetch(endpoint, params, cursor) -> (rows, next_cursor)

with pagination, rate-limit handling, and retries kept *internal* to the
connector. Two ingest modes:

  • Bulk dissemination files (monthly full + weekly incrementals + the
    auxiliary other-name / practice-location / endpoint files, plus the
    NUCC CSV). These are large and are fetched to disk, then parsed by the
    streaming parsers — the connector never holds a whole file in memory.
    The API cannot full-dump the universe; the bulk file is the backbone.

  • The NPI Registry API (``https://npiregistry.cms.hhs.gov/api/?version=2.1``)
    for targeted lookups and incremental verification only. It caps at 200
    rows/request and blocks paging past ~1,200 records for a single query,
    so ``fetch`` enforces that ceiling rather than attempting a backfill.

Network-blocked environments: every remote call degrades gracefully —
on failure it returns empty rows with a ``next_cursor`` of ``None`` and
records the reason on ``self.events`` so the pipeline can log it to STATE
and retry at the end of the backlog, never crashing the session.
"""
from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from . import registry

logger = logging.getLogger(__name__)

# Documented API result cap (verified live by ``verify_api_cap`` when the
# network is reachable; falls back to this when blocked).
API_PAGE_CAP = 200
API_DEPTH_CAP = 1200  # API blocks skip+limit beyond ~1,200 for one query
USER_AGENT = "PEDesk-NPPES-Connector/1.0 (+diligence)"


@dataclass
class FetchEvent:
    endpoint: str
    kind: str
    ok: bool
    detail: str
    attempts: int = 1


class NppesConnector:
    def __init__(
        self,
        *,
        max_retries: int = 4,
        backoff_base: float = 2.0,
        timeout: float = 30.0,
        sleeper=time.sleep,
    ) -> None:
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.timeout = timeout
        self._sleep = sleeper
        self.events: List[FetchEvent] = []

    # ── discovery ───────────────────────────────────────────────────
    def discover(self) -> List[Dict]:
        """Enumerate what this connector ingests: the declarative registry
        rows, each annotated with whether it is a bulk-file or API dataset."""
        out = []
        for row in registry.registry_rows():
            kind = row["default_params"].get("kind", "")
            row["ingest_mode"] = (
                "api" if kind == "api_lookup"
                else "derived" if kind == "derived"
                else "bulk_file"
            )
            out.append(row)
        return out

    # ── fetch ───────────────────────────────────────────────────────
    def fetch(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        cursor: Optional[Any] = None,
    ) -> Tuple[List[Dict], Optional[Any]]:
        """Fetch one page. Returns ``(rows, next_cursor)``; ``next_cursor``
        is ``None`` when the stream is exhausted (or unreachable).

        Routing is by ``params['kind']``:
          • ``api_lookup`` → NPI Registry API, cursor is an integer skip.
          • bulk kinds → returns the path the caller should parse (the file
            is downloaded to ``params['dest']`` if reachable); rows is a
            single descriptor row, next_cursor is None.
        """
        params = dict(params or {})
        kind = params.get("kind", "api_lookup")
        if kind == "api_lookup":
            return self._fetch_api(endpoint, params, cursor)
        if kind == "derived":
            return [], None
        return self._fetch_bulk(endpoint, params)

    # ── API path (paginated, cap-aware, retried) ────────────────────
    def _fetch_api(
        self, endpoint: str, params: Dict, cursor: Optional[int]
    ) -> Tuple[List[Dict], Optional[int]]:
        skip = int(cursor or 0)
        limit = min(int(params.get("limit", API_PAGE_CAP)), API_PAGE_CAP)
        if skip >= API_DEPTH_CAP:
            # Honour the hard depth ceiling — do not attempt to page deeper.
            self.events.append(FetchEvent(
                endpoint, "api_lookup", True,
                f"reached API depth cap ({API_DEPTH_CAP}); stop paging"))
            return [], None

        q = {k: v for k, v in params.items()
             if k not in ("kind",) and v not in (None, "")}
        q["version"] = q.get("version", "2.1")
        q["limit"] = limit
        q["skip"] = skip
        url = "https://npiregistry.cms.hhs.gov/api/?" + urllib.parse.urlencode(q)

        payload, attempts, err = self._http_get_json(url)
        if payload is None:
            self.events.append(FetchEvent(
                endpoint, "api_lookup", False,
                f"api unreachable: {err}", attempts))
            return [], None

        results = payload.get("results") or []
        rows = [self._flatten_api_result(r) for r in results]
        self.events.append(FetchEvent(
            endpoint, "api_lookup", True,
            f"skip={skip} got={len(rows)}", attempts))
        # Next cursor only if a full page came back and depth cap allows.
        nxt = skip + limit
        if len(results) < limit or nxt >= API_DEPTH_CAP:
            return rows, None
        return rows, nxt

    @staticmethod
    def _flatten_api_result(r: Dict) -> Dict:
        """Collapse one NPI Registry API result into a flat provider dict
        shaped like a parsed main-file row (so the normalizer is uniform)."""
        basic = r.get("basic", {}) or {}
        addrs = r.get("addresses", []) or []
        taxos = r.get("taxonomies", []) or []
        return {
            "npi": str(r.get("number", "")),
            "entity_type": 2 if (r.get("enumeration_type") == "NPI-2") else 1,
            "organization_name": basic.get("organization_name", "") or basic.get("name", ""),
            "last_name": basic.get("last_name", ""),
            "first_name": basic.get("first_name", ""),
            "middle_name": basic.get("middle_name", ""),
            "credential": basic.get("credential", ""),
            "sole_proprietor": basic.get("sole_proprietor", ""),
            "enumeration_date": basic.get("enumeration_date", ""),
            "last_update_date": basic.get("last_updated", ""),
            "deactivation_date": basic.get("deactivation_date", ""),
            "reactivation_date": basic.get("reactivation_date", ""),
            "status": "deactivated" if basic.get("status") == "I" else "active",
            "authorized_official_last_name": basic.get("authorized_official_last_name", ""),
            "authorized_official_first_name": basic.get("authorized_official_first_name", ""),
            "authorized_official_title": basic.get("authorized_official_title_or_position", ""),
            "taxonomies": [
                {"code": t.get("code", ""), "primary": bool(t.get("primary")),
                 "license_number": t.get("license", ""), "license_state": t.get("state", "")}
                for t in taxos if t.get("code")
            ],
            "addresses": [
                {"purpose": ("mailing" if a.get("address_purpose") == "MAILING" else "practice"),
                 "line_1": a.get("address_1", ""), "line_2": a.get("address_2", ""),
                 "city": (a.get("city", "") or "").upper(),
                 "state": (a.get("state", "") or "").upper(),
                 "postal_code": a.get("postal_code", ""),
                 "country_code": a.get("country_code", "US"),
                 "telephone": a.get("telephone_number", ""), "fax": a.get("fax_number", "")}
                for a in addrs
            ],
            "source_row": "api",
        }

    def verify_api_cap(self) -> int:
        """Probe the live API to confirm the current per-request cap. Asks
        for more than the documented cap and reports what comes back. Falls
        back to the documented cap when the network is blocked."""
        url = ("https://npiregistry.cms.hhs.gov/api/?version=2.1"
               "&taxonomy_description=internal+medicine&limit=500")
        payload, attempts, err = self._http_get_json(url)
        if payload is None:
            self.events.append(FetchEvent(
                "verify_cap", "api_lookup", False,
                f"cannot verify cap live: {err}; using documented {API_PAGE_CAP}",
                attempts))
            return API_PAGE_CAP
        n = len(payload.get("results") or [])
        cap = n if 0 < n <= 500 else API_PAGE_CAP
        self.events.append(FetchEvent(
            "verify_cap", "api_lookup", True, f"live cap observed = {cap}"))
        return cap

    # ── bulk path ───────────────────────────────────────────────────
    def _fetch_bulk(self, endpoint: str, params: Dict) -> Tuple[List[Dict], Optional[Any]]:
        """Download a bulk dissemination file to ``params['dest']`` if a URL
        is reachable. Returns a single descriptor row referencing the local
        path (the caller streams it with the parsers). When the network is
        blocked but a local file is already present (``params['local_path']``),
        we use that — this is how offline / pre-staged runs proceed."""
        local = params.get("local_path")
        if local:
            self.events.append(FetchEvent(
                endpoint, params.get("kind", "bulk"), True,
                f"using pre-staged local file {local}"))
            return [{"local_path": str(local), "kind": params.get("kind")}], None

        url = params.get("url") or (params.get("base_url", "") + endpoint)
        dest = params.get("dest")
        if not url or not dest:
            self.events.append(FetchEvent(
                endpoint, params.get("kind", "bulk"), False,
                "no url/dest and no local_path; cannot fetch bulk file"))
            return [], None
        ok, attempts, err = self._http_download(url, dest)
        if not ok:
            self.events.append(FetchEvent(
                endpoint, params.get("kind", "bulk"), False,
                f"bulk download failed: {err}", attempts))
            return [], None
        self.events.append(FetchEvent(
            endpoint, params.get("kind", "bulk"), True,
            f"downloaded to {dest}", attempts))
        return [{"local_path": str(dest), "kind": params.get("kind")}], None

    # ── HTTP helpers (retries + backoff + rate-limit) ───────────────
    def _http_get_json(self, url: str):
        attempts = 0
        last_err = ""
        for attempt in range(1, self.max_retries + 1):
            attempts = attempt
            try:
                req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    raw = resp.read()
                return json.loads(raw.decode("utf-8", "replace")), attempts, ""
            except urllib.error.HTTPError as e:
                last_err = f"HTTP {e.code}"
                if e.code == 429:  # rate limited — honour Retry-After
                    wait = self._retry_after(e) or self.backoff_base ** attempt
                    self._sleep(wait)
                    continue
                if 500 <= e.code < 600:
                    self._sleep(self.backoff_base ** attempt)
                    continue
                # 4xx other than 429 → not retryable
                return None, attempts, last_err
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                last_err = str(e)
                self._sleep(self.backoff_base ** attempt)
                continue
            except json.JSONDecodeError as e:
                return None, attempts, f"bad json: {e}"
        return None, attempts, last_err

    def _http_download(self, url: str, dest: str):
        attempts = 0
        last_err = ""
        import shutil
        for attempt in range(1, self.max_retries + 1):
            attempts = attempt
            try:
                req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(req, timeout=self.timeout) as resp, \
                        open(dest, "wb") as fh:
                    shutil.copyfileobj(resp, fh, length=1024 * 1024)
                return True, attempts, ""
            except urllib.error.HTTPError as e:
                last_err = f"HTTP {e.code}"
                if e.code == 429 or 500 <= e.code < 600:
                    self._sleep(self.backoff_base ** attempt)
                    continue
                return False, attempts, last_err
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                last_err = str(e)
                self._sleep(self.backoff_base ** attempt)
                continue
        return False, attempts, last_err

    @staticmethod
    def _retry_after(e: urllib.error.HTTPError) -> Optional[float]:
        try:
            ra = e.headers.get("Retry-After")
            return float(ra) if ra else None
        except Exception:  # noqa: BLE001
            return None
