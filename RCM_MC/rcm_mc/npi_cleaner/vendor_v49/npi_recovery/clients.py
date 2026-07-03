"""Live API clients for data.cms.gov (Medicare provider summary files) and
NPPES (NPI Registry), with a simple on-disk cache. No API keys required."""

import hashlib
import json
import pickle
import re
import threading
import time
from pathlib import Path

import pandas as pd
import requests

from . import config

CATALOG_URL = "https://data.cms.gov/data.json"
NPPES_URL = "https://npiregistry.cms.hhs.gov/api/"
RXNAV_URL = "https://rxnav.nlm.nih.gov/REST"  # NLM RxNorm — authoritative drug identity, no key
# CMS Provider Data Catalog — "Facility Affiliation Data" (clinician NPI -> facility type + CCN)
PDC_AFFIL_QUERY = "https://data.cms.gov/provider-data/api/1/datastore/query/27ea-46a8/0"
# CMS "Hospital General Information" (CCN -> hospital name, type, ownership, location)
PDC_HOSPITAL_QUERY = "https://data.cms.gov/provider-data/api/1/datastore/query/xubh-q36u/0"
USER_AGENT = "npi-recovery/1.0 (public-data billing-NPI recovery)"

from requests.adapters import HTTPAdapter
try:
    from urllib3.util.retry import Retry
except Exception:  # pragma: no cover
    Retry = None


def _make_session(pool_maxsize=32):
    """A requests session sized for concurrency: a big connection pool so
    threaded lookups reuse sockets instead of churning, plus a short retry with
    backoff so a transient 429/5xx doesn't fail a provider (improves both speed
    and reliability — never changes the data returned)."""
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT})
    kwargs = dict(pool_connections=pool_maxsize, pool_maxsize=pool_maxsize)
    if Retry is not None:
        try:
            kwargs["max_retries"] = Retry(
                total=5, connect=3, read=3, backoff_factor=1.5,
                status_forcelist=(429, 500, 502, 503, 504),
                respect_retry_after_header=True,
                allowed_methods=frozenset(["GET"]))
        except TypeError:  # older urllib3 keyword
            kwargs["max_retries"] = Retry(total=5, backoff_factor=1.5,
                                          status_forcelist=(429, 500, 502, 503, 504))
    adapter = HTTPAdapter(**kwargs)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s


class DiskCache:
    """Pickle-per-key cache. CMS annual files don't change, so there's no TTL."""

    def __init__(self, cache_dir):
        self.dir = Path(cache_dir)
        self.dir.mkdir(parents=True, exist_ok=True)

    def _path(self, namespace, key):
        h = hashlib.sha1(json.dumps(key, sort_keys=True, default=str).encode()).hexdigest()[:20]
        return self.dir / f"{namespace}__{h}.pkl"

    def get(self, namespace, key):
        p = self._path(namespace, key)
        if p.exists():
            try:
                with open(p, "rb") as fh:
                    return pickle.load(fh)
            except Exception:
                return None
        return None

    def set(self, namespace, key, value):
        try:
            with open(self._path(namespace, key), "wb") as fh:
                pickle.dump(value, fh)
        except Exception:
            pass


class CMSClient:
    """Talks to the four data.cms.gov provider-summary datasets used by the playbook."""

    def __init__(self, cache: DiskCache, timeout=120, max_pages=200, polite_delay=0.0):
        self.cache = cache
        self.timeout = timeout
        self.max_pages = max_pages
        self.polite_delay = polite_delay
        self.session = _make_session()
        self._catalog = None
        self._url_cache = {}
        self._catalog_lock = threading.Lock()

    # -- catalog / latest-UUID resolution -----------------------------------
    def _catalog_json(self):
        # Thread-safe: with concurrent pool fetches, the catalog (a single shared
        # /data.json endpoint) must be fetched exactly ONCE — otherwise every
        # worker hammers it at once and CMS returns 429 (too many requests).
        if self._catalog is not None:
            return self._catalog
        with self._catalog_lock:
            if self._catalog is None:
                cached = self.cache.get("catalog", "data.json")
                if cached is not None:
                    self._catalog = cached
                else:
                    self._catalog = self.session.get(CATALOG_URL, timeout=self.timeout).json()
                    self.cache.set("catalog", "data.json", self._catalog)
        return self._catalog

    def warm(self, titles):
        """Resolve the catalog + the given dataset URLs once, serially, BEFORE any
        parallel fetch. This primes the shared catalog so concurrent workers never
        stampede /data.json. Failures are swallowed — the workers will retry."""
        for t in titles:
            try:
                self.latest_api_url(t)
            except Exception:
                pass

    def latest_api_url(self, title):
        """Resolve the stable '/data' endpoint for the latest vintage of a dataset title."""
        if title in self._url_cache:
            return self._url_cache[title]
        for ds in self._catalog_json().get("dataset", []):
            if ds.get("title") == title:
                for d in ds.get("distribution", []):
                    if d.get("format") == "API" and d.get("description") == "latest":
                        self._url_cache[title] = d["accessURL"]
                        return d["accessURL"]
        raise ValueError(f"Dataset title not found in CMS catalog: {title!r}")

    # -- generic paginated, filtered pull -----------------------------------
    def pull(self, title, filters=None, columns=None, page=5000, max_rows=None):
        key = {"title": title, "filters": filters or {}, "columns": columns or [],
               "max_rows": max_rows}
        cached = self.cache.get("cms_pull", key)
        if cached is not None:
            return pd.DataFrame(cached)

        url = self.latest_api_url(title)
        params = {f"filter[{k}]": v for k, v in (filters or {}).items()}
        if columns:
            params["column"] = ",".join(columns)
        rows, offset = [], 0
        for _ in range(self.max_pages):
            params["size"], params["offset"] = page, offset
            for attempt in range(3):
                try:
                    r = self.session.get(url, params=params, timeout=self.timeout)
                    r.raise_for_status()
                    batch = r.json()
                    break
                except Exception:
                    if attempt == 2:
                        batch = []
                    time.sleep(1.5 * (attempt + 1))
            rows += batch
            if max_rows and len(rows) >= max_rows:
                rows = rows[:max_rows]
                break
            if len(batch) < page:
                break
            offset += page
            if self.polite_delay:
                time.sleep(self.polite_delay)

        self.cache.set("cms_pull", key, rows)
        return pd.DataFrame(rows)

    # -- convenience: who bills this code, where ----------------------------
    def billers_physician(self, hcpcs, state):
        cols = list(config.PHYS_COLS.values())
        df = self.pull(config.DATASET_TITLES["physician_provider"],
                       filters={"HCPCS_Cd": hcpcs, "Rndrng_Prvdr_State_Abrvtn": state},
                       columns=cols)
        return self._normalise_physician(df)

    def billers_dme(self, hcpcs, state):
        c = config.DME_COLS
        df = self.pull(config.DATASET_TITLES["dme_supplier"],
                       filters={"HCPCS_Cd": hcpcs, c["state"]: state})
        return self._normalise_dme(df)

    def _normalise_physician(self, df):
        if df.empty:
            return _empty_pool()
        c = config.PHYS_COLS
        out = pd.DataFrame({
            "npi": df[c["npi"]].astype(str),
            "name": df.get(c["name"], "").astype(str),
            "type": df.get(c["type"], "").astype(str),
            "state": df.get(c["state"], "").astype(str),
            "zip5": df.get(c["zip"], "").astype(str),
            "place": df.get(c["place"], "").astype(str),
            "srvcs": pd.to_numeric(df.get(c["srvcs"]), errors="coerce").fillna(0),
            "allowed": pd.to_numeric(df.get(c["allowed"]), errors="coerce").fillna(0),
        })
        out["channel"] = "physician"
        return out.sort_values("srvcs", ascending=False).reset_index(drop=True)

    def _normalise_dme(self, df):
        if df.empty:
            return _empty_pool()
        c = config.DME_COLS
        npi_col = c["supplier_npi"] if c["supplier_npi"] in df.columns else c.get("npi")
        name_col = c["supplier_name"] if c["supplier_name"] in df.columns else c.get("name")
        out = pd.DataFrame({
            "npi": df.get(npi_col, "").astype(str),
            "name": df.get(name_col, "").astype(str),
            "type": "DME supplier",
            "state": df.get(c["state"], "").astype(str),
            "zip5": "",
            "place": "DME",
            "srvcs": pd.to_numeric(df.get(c["srvcs"]), errors="coerce").fillna(0),
            "allowed": pd.to_numeric(df.get(c["allowed"]), errors="coerce").fillna(0),
        })
        out["channel"] = "dme"
        out = out[out["npi"].str.len() >= 8]
        return out.sort_values("srvcs", ascending=False).reset_index(drop=True)

    # -- national pulls: one query per code, all states (efficient at scale) --
    def billers_by_hcpcs(self, hcpcs):
        """Pull every Medicare provider who bills this code nationally, in one
        paginated query. Returns (pool_with_state_column, hcpcs_description)."""
        cols = list(config.PHYS_COLS.values())
        df = self.pull(config.DATASET_TITLES["physician_provider"],
                       filters={"HCPCS_Cd": hcpcs}, columns=cols)
        desc = ""
        c = config.PHYS_COLS
        if not df.empty and c["desc"] in df.columns:
            vals = df[c["desc"]].dropna()
            if len(vals):
                desc = str(vals.iloc[0])
        return self._normalise_physician(df), desc

    def dme_billers_by_hcpcs(self, hcpcs):
        c = config.DME_COLS
        df = self.pull(config.DATASET_TITLES["dme_supplier"], filters={"HCPCS_Cd": hcpcs})
        return self._normalise_dme(df)

    def geography_benchmark(self, hcpcs):
        """National Medicare benchmark for a HCPCS from the Physician-by-Geography
        dataset: how many providers bill it, beneficiaries, services, avg allowed."""
        df = self.pull(config.DATASET_TITLES["physician_geo"],
                       filters={"HCPCS_Cd": hcpcs, "Rndrng_Prvdr_Geo_Lvl": "National"},
                       max_rows=5)
        if df.empty:
            return {}
        row = df.iloc[0]
        num = lambda k: float(pd.to_numeric(row.get(k), errors="coerce")) if pd.notna(row.get(k)) else None
        return {
            "hcpcs": hcpcs,
            "desc": (row.get("HCPCS_Desc") or "").strip(),
            "natl_providers": num("Tot_Rndrng_Prvdrs"),
            "natl_benes": num("Tot_Benes"),
            "natl_services": num("Tot_Srvcs"),
            "avg_allowed_unit": num("Avg_Mdcr_Alowd_Amt"),
            "avg_paid_unit": num("Avg_Mdcr_Pymt_Amt"),
        }

    def geography_benchmark_state(self, hcpcs, state_name):
        """State-level Medicare FFS volume for a HCPCS from the Physician-by-
        Geography dataset: real services, beneficiaries, and allowed $/unit for
        one state. This is ACTUAL Medicare fee-for-service utilization (not a
        candidate universe) and is the measured Medicare segment for sizing."""
        df = self.pull(config.DATASET_TITLES["physician_geo"],
                       filters={"HCPCS_Cd": hcpcs, "Rndrng_Prvdr_Geo_Lvl": "State",
                                "Rndrng_Prvdr_Geo_Desc": state_name},
                       max_rows=5)
        if df.empty:
            return {}
        row = df.iloc[0]
        num = lambda k: float(pd.to_numeric(row.get(k), errors="coerce")) if pd.notna(row.get(k)) else None
        svc = num("Tot_Srvcs"); alw = num("Avg_Mdcr_Alowd_Amt")
        return {
            "hcpcs": hcpcs, "state": state_name,
            "ffs_providers": num("Tot_Rndrng_Prvdrs"),
            "ffs_benes": num("Tot_Benes"),
            "ffs_services": svc,
            "avg_allowed_unit": alw,
            "ffs_allowed_total": (svc * alw) if (svc is not None and alw is not None) else None,
        }

    def partd_presence(self, generic_name, max_rows=400):
        """Best-effort Part-D footprint for a drug by generic name (Part D is not
        HCPCS-keyed). Returns dict with prescriber-row count and total claims."""
        if not generic_name:
            return {}
        df = self.pull(config.DATASET_TITLES["partd_provider"],
                       filters={"Gnrc_Name": generic_name}, max_rows=max_rows)
        if df.empty:
            return {"generic": generic_name, "partd_rows": 0, "partd_claims": 0.0}
        claims = float(pd.to_numeric(df.get("Tot_Clms"), errors="coerce").fillna(0).sum()) if "Tot_Clms" in df else 0.0
        return {"generic": generic_name, "partd_rows": int(len(df)), "partd_claims": claims}

    def psps_site_of_care(self, hcpcs, max_rows=8000):
        """Physician/Supplier Procedure Summary rows for a HCPCS, summarised into
        office vs hospital-outpatient allowed $ and service counts. POS 11=office;
        19/22/24=hospital outpatient/ASC. Returns a dict."""
        df = self.pull(config.DATASET_TITLES["psps"],
                       filters={"HCPCS_CD": hcpcs}, max_rows=max_rows)
        if df.empty:
            return {}
        pos = df.get("PLACE_OF_SERVICE_CD", pd.Series(dtype=str)).astype(str)
        svc = pd.to_numeric(df.get("PSPS_SUBMITTED_SERVICE_CNT"), errors="coerce").fillna(0)
        alw = pd.to_numeric(df.get("PSPS_ALLOWED_CHARGE_AMT"), errors="coerce").fillna(0)
        office = pos.isin(["11"])
        hopd = pos.isin(["19", "22", "24"])
        tot_svc = float(svc.sum())
        return {
            "hcpcs": hcpcs,
            "office_services": float(svc[office].sum()),
            "hopd_services": float(svc[hopd].sum()),
            "office_allowed": float(alw[office].sum()),
            "hopd_allowed": float(alw[hopd].sum()),
            "pct_office_services": round(100 * float(svc[office].sum()) / tot_svc, 1) if tot_svc else None,
        }

    def market_saturation_ffs(self, state, service_keyword="Part B Drugs"):
        """FFS beneficiary counts by county for a state from the Market Saturation
        file, for grossing FFS up to total Medicare. Returns a DataFrame slice."""
        df = self.pull(config.DATASET_TITLES["market_saturation"],
                       filters={"state": state}, max_rows=20000)
        if df.empty:
            return df
        if service_keyword and "type_of_service" in df:
            m = df["type_of_service"].astype(str).str.contains(service_keyword, case=False, na=False)
            if m.any():
                df = df[m]
        return df

    def enrollment_lookup(self, npi):
        """Verify a billing NPI against the Medicare FFS Public Provider Enrollment
        file (PECOS). Returns enrolled flag + provider type + org name, or {}."""
        npi = str(npi).strip()
        if not config.npi_is_valid(npi):
            return {}
        df = self.pull(config.DATASET_TITLES["provider_enrollment"],
                       filters={"NPI": npi}, max_rows=5)
        if df.empty:
            return {"npi": npi, "enrolled": False}
        r = df.iloc[0]
        g = lambda k: (str(r.get(k)).strip() if pd.notna(r.get(k)) else "")
        return {
            "npi": npi, "enrolled": True,
            "provider_type": g("PROVIDER_TYPE_DESC"),
            "provider_type_cd": g("PROVIDER_TYPE_CD"),
            "org_name": g("ORG_NAME"),
            "enrollment_state": g("STATE_CD"),
            "pecos_id": g("PECOS_ASCT_CNTL_ID"),
            "multiple_npi": g("MULTIPLE_NPI_FLAG"),
        }

    def order_referring_lookup(self, npi):
        """Verify a referring/ordering NPI against the Order and Referring file.
        Returns eligibility flags (Part B, DME, HHA, PMD, Hospice) or {}."""
        npi = str(npi).strip()
        if not config.npi_is_valid(npi):
            return {}
        df = self.pull(config.DATASET_TITLES["order_referring"],
                       filters={"NPI": npi}, max_rows=5)
        if df.empty:
            return {"npi": npi, "in_order_referring": False}
        r = df.iloc[0]
        yn = lambda k: str(r.get(k, "")).strip().upper() == "Y"
        return {
            "npi": npi, "in_order_referring": True,
            "can_refer_partb": yn("PARTB"), "can_order_dme": yn("DME"),
            "can_refer_hha": yn("HHA"), "can_order_pmd": yn("PMD"),
            "can_refer_hospice": yn("HOSPICE"),
            "name": " ".join(x for x in [str(r.get("FIRST_NAME", "")).strip(),
                                         str(r.get("LAST_NAME", "")).strip()] if x),
        }

    def opt_out_lookup(self, npi):
        """Check a billing NPI against the Medicare Opt Out Affidavits file. A
        provider who has opted out of Medicare should not be billing it — a real
        red flag. Returns opt-out status + effective/end dates, or {}."""
        npi = str(npi).strip()
        if not config.npi_is_valid(npi):
            return {}
        df = self.pull(config.DATASET_TITLES["opt_out"],
                       filters={"NPI": npi}, max_rows=5)
        if df.empty:
            return {"npi": npi, "opted_out": False}
        r = df.iloc[0]
        g = lambda k: (str(r.get(k)).strip() if pd.notna(r.get(k)) else "")
        return {
            "npi": npi, "opted_out": True,
            "optout_specialty": g("Specialty"),
            "optout_effective": g("Optout Effective Date"),
            "optout_end": g("Optout End Date"),
            "optout_eligible_refer": g("Eligible to Order and Refer"),
        }


class NPPESClient:
    """NPI Registry lookups for entity resolution / parent rollup."""

    def __init__(self, cache: DiskCache, timeout=60):
        self.cache = cache
        self.timeout = timeout
        self.session = _make_session()
        self._mem = {}

    def lookup(self, npi):
        npi = str(npi).strip()
        if not config.npi_is_valid(npi):
            return None
        memo = self._mem.get(npi, False)
        if memo is not False:
            return memo
        cached = self.cache.get("nppes", npi)
        if cached is not None:
            self._mem[npi] = cached
            return cached
        rec = None
        try:
            r = self.session.get(NPPES_URL, params={"version": "2.1", "number": npi}, timeout=self.timeout)
            results = r.json().get("results", [])
            if results:
                rec = self._flatten(results[0])
        except Exception:
            rec = None
        self.cache.set("nppes", npi, rec)
        self._mem[npi] = rec
        return rec

    def search_org(self, org_name, state=None, city=None, taxonomy=None, limit=5):
        """Find an organization NPI by name (+ optional state/city/taxonomy).
        Returns a flattened best match (highest token overlap) or None. Used to
        recover a blank billing NPI when a facility/organization name is present.
        """
        org_name = "" if pd.isna(org_name) else str(org_name)
        state = "" if pd.isna(state) else str(state)
        city = "" if pd.isna(city) else str(city)
        taxonomy = "" if pd.isna(taxonomy) else str(taxonomy)
        name = org_name.strip()
        if len(name) < 4:
            return None
        key = f"org::{name.lower()}::{state.upper()}::{city.lower()}::{taxonomy.lower()}"
        cached = self.cache.get("nppes_search", key)
        if cached is not None:
            return cached
        params = {"version": "2.1", "enumeration_type": "NPI-2",
                  "organization_name": name + "*", "limit": limit}
        if state:
            params["state"] = state
        if city:
            params["city"] = city
        if taxonomy:
            params["taxonomy_description"] = taxonomy
        best = None
        try:
            r = self.session.get(NPPES_URL, params=params, timeout=self.timeout)
            results = r.json().get("results", []) or []
            want = set(re.sub(r"[^a-z0-9 ]", "", name.lower()).split())
            best_score = 0.0
            for res in results:
                flat = self._flatten(res)
                got = set(re.sub(r"[^a-z0-9 ]", "", str(flat.get("name", "")).lower()).split())
                if not got:
                    continue
                score = len(want & got) / max(len(want | got), 1)
                if state and str(flat.get("state", "")).upper() == str(state).upper():
                    score += 0.15
                if score > best_score:
                    best_score, best = score, flat
            best = best if best_score >= 0.5 else None
        except Exception:
            best = None
        self.cache.set("nppes_search", key, best)
        return best

    @staticmethod
    def _flatten(res):
        basic = res.get("basic", {})
        name = basic.get("organization_name") or " ".join(
            x for x in [basic.get("first_name"), basic.get("last_name")] if x)
        taxes = res.get("taxonomies", [])
        primary = next((t for t in taxes if t.get("primary")), taxes[0] if taxes else {})
        addrs = res.get("addresses", [])
        loc = next((a for a in addrs if a.get("address_purpose") == "LOCATION"),
                   addrs[0] if addrs else {})
        mail = next((a for a in addrs if a.get("address_purpose") == "MAILING"), {})
        official = " ".join(x for x in [basic.get("authorized_official_first_name"),
                                        basic.get("authorized_official_last_name")] if x)
        etype = res.get("enumeration_type")  # "NPI-1" individual / "NPI-2" org

        # Other / former / DBA names. NPPES carries these in an "other_names"
        # array; for organizations each entry has an organization_name. This is
        # the field that ties a rebranded or acquired practice back to its
        # parent — e.g. "CSI" registered with the other-name "CLINICAL SPECIALTY
        # INFUSIONS" — so we keep the full set, uppercased and semicolon-joined,
        # for the entity-continuity rollup to cluster on.
        other_raw = res.get("other_names", []) or []
        _other = []
        for o in other_raw:
            nm = (o.get("organization_name")
                  or " ".join(x for x in [o.get("first_name"), o.get("last_name")] if x))
            nm = (nm or "").strip().upper()
            if nm and nm not in _other:
                _other.append(nm)
        other_org_names = "; ".join(_other)

        # Full specialty set: a provider can carry several taxonomies (e.g. an
        # infusion suite registered as both "Infusion Therapy" and "Internal
        # Medicine"). The primary drives routing; the full set is kept as an
        # authoritative verified column so the analyst sees every specialty.
        _alltax = []
        for t in taxes:
            d = (t.get("desc") or "").strip()
            if d and d not in _alltax:
                _alltax.append(d)
        all_taxonomies = "; ".join(_alltax)

        def _line(a):
            return ", ".join(x for x in [a.get("address_1"), a.get("address_2")] if x).strip()

        return {
            "npi": res.get("number"),
            "name": (name or "").strip(),
            "type": etype,
            "entity_type": "Organization" if etype == "NPI-2" else ("Individual" if etype == "NPI-1" else ""),
            "credential": (basic.get("credential") or "").strip(),
            "sole_proprietor": basic.get("sole_proprietor", ""),
            "status": basic.get("status", ""),
            "enumeration_date": basic.get("enumeration_date", ""),
            "last_updated": basic.get("last_updated", ""),
            "taxonomy": (primary.get("desc") or "").strip(),
            "taxonomy_code": (primary.get("code") or "").strip(),
            "license": (primary.get("license") or "").strip(),
            "license_state": (primary.get("state") or "").strip(),
            "addr_line": _line(loc),
            "city": (loc.get("city") or "").strip(),
            "state": (loc.get("state") or "").strip(),
            "postal": (str(loc.get("postal_code") or "").strip())[:5],
            "phone": (loc.get("telephone_number") or "").strip(),
            "loc_addr": _addr_key(loc),
            "mail_addr": _addr_key(mail or loc),
            "mail_line": _line(mail),
            "official": official.strip(),
            "other_org_names": other_org_names,
            "all_taxonomies": all_taxonomies,
        }


def _empty_pool():
    return pd.DataFrame(columns=["npi", "name", "type", "state", "zip5", "place", "srvcs", "allowed", "channel"])


def _addr_key(a):
    if not a:
        return ""
    parts = [a.get("address_1", ""), a.get("city", ""), a.get("state", ""),
             (a.get("postal_code", "") or "")[:5]]
    return " ".join(p.strip().upper() for p in parts if p).strip()


class RxNormClient:
    """NLM RxNorm (RxNav) lookups — authoritative drug identity. Resolves an NDC
    or a free-text drug name to {rxcui, name, ingredient, atc_class}. Public, no
    API key. Cached per key (RxNorm content is stable month to month)."""

    def __init__(self, cache: DiskCache, timeout=20):
        self.cache = cache
        self.timeout = timeout
        self.session = _make_session()
        self._mem = {}

    def _get(self, path):
        try:
            r = self.session.get(RXNAV_URL + path, timeout=self.timeout)
            if r.status_code == 200:
                return r.json()
        except Exception:
            return None
        return None

    def _enrich_rxcui(self, rxcui):
        """rxcui -> (name, ingredient, atc_class)."""
        name = ingredient = atc = ""
        p = (self._get(f"/rxcui/{rxcui}/properties.json") or {}).get("properties", {})
        name = p.get("name", "") or ""
        rel = self._get(f"/rxcui/{rxcui}/related.json?tty=IN") or {}
        ings = []
        for grp in rel.get("relatedGroup", {}).get("conceptGroup", []) or []:
            for c in grp.get("conceptProperties", []) or []:
                if c.get("name"):
                    ings.append(c["name"])
        ingredient = "; ".join(dict.fromkeys(ings))
        cls = self._get(f"/rxclass/class/byRxcui.json?rxcui={rxcui}&relaSource=ATC") or {}
        names = []
        for ci in cls.get("rxclassDrugInfoList", {}).get("rxclassDrugInfo", []) or []:
            nm = ci.get("rxclassMinConceptItem", {}).get("className")
            if nm and nm not in names:
                names.append(nm)
        if not names:
            # fallback: many biologics (e.g. immune globulin / IVIG) carry no ATC
            # class but do have a DailyMed pharmacologic class. Push toward 0% blank.
            dm = self._get(f"/rxclass/class/byRxcui.json?rxcui={rxcui}&relaSource=DAILYMED") or {}
            for ci in dm.get("rxclassDrugInfoList", {}).get("rxclassDrugInfo", []) or []:
                nm = ci.get("rxclassMinConceptItem", {}).get("className")
                if nm and nm not in names:
                    names.append(nm)
        atc = "; ".join(names[:3])
        return name, ingredient, atc

    def lookup_ndc(self, ndc):
        ndc = "".join(ch for ch in str(ndc) if ch.isdigit())
        if len(ndc) < 9:
            return None
        memo = self._mem.get(("ndc", ndc), False)
        if memo is not False:
            return memo
        cached = self.cache.get("rxnorm_ndc", ndc)
        if cached is not None:
            self._mem[("ndc", ndc)] = cached
            return cached
        rec = None
        j = self._get(f"/rxcui.json?idtype=NDC&id={ndc}") or {}
        rxcui = (j.get("idGroup", {}).get("rxnormId", [None]) or [None])[0]
        if rxcui:
            name, ingredient, atc = self._enrich_rxcui(rxcui)
            rec = {"rxcui": rxcui, "name": name, "ingredient": ingredient, "atc_class": atc}
        self.cache.set("rxnorm_ndc", ndc, rec)
        self._mem[("ndc", ndc)] = rec
        return rec

    @staticmethod
    def _name_variants(name):
        """Turn a messy claims drug name into RxNorm-searchable candidates.
        Real claim names look like 'IMMUNE GLOBULIN IVIG (GAMUNEX-C)' or
        'USTEKINUMAB INTRAVENOUS (STELARA)' — RxNorm matches the brand in parens
        or the leading ingredient token far better than the whole string."""
        import re
        s = str(name).strip()
        out = []
        m = re.search(r"\(([^)]+)\)", s)               # brand in parentheses
        if m:
            brand = m.group(1).strip()
            out.append(brand)
            b2 = re.sub(r"\b(BIOSIMILAR|BIOSIM|BRAND)\b", "", brand, flags=re.I).strip()
            if b2 and b2 != brand:
                out.append(b2)
        head = re.sub(r"\(.*?\)", "", s).strip()        # text before parens
        route = (r"\b(IV|INTRAVENOUS|SUBCUTANEOUS|SUBQ|SUB-Q|SQ|INJECTION|INJ|IVIG|"
                 r"SCIG|INFUSION|SOLUTION|CONCENTRATE|UNCLASSIFIED|BIOLOGIC)\b")
        head_clean = re.sub(route, "", head, flags=re.I).strip(" ,-/")
        if head_clean:
            out.append(head_clean)
            toks = head_clean.split()
            if toks:
                out.append(toks[0])
                if len(toks) >= 2:
                    out.append(" ".join(toks[:2]))
        if "IMMUNE GLOBULIN" in s.upper():
            out.append("immune globulin")
        seen = []
        for c in out:
            c = c.strip()
            if len(c) >= 3 and c.lower() not in [x.lower() for x in seen]:
                seen.append(c)
        return seen

    def _resolve_name(self, name):
        from urllib.parse import quote
        for cand in [name] + self._name_variants(name):
            j = self._get(f"/rxcui.json?name={quote(cand)}&search=2") or {}
            rxcui = (j.get("idGroup", {}).get("rxnormId", [None]) or [None])[0]
            if not rxcui:  # approximate match as a last resort for this candidate
                ja = self._get(f"/approximateTerm.json?term={quote(cand)}&maxEntries=1") or {}
                cands = ja.get("approximateGroup", {}).get("candidate", []) or []
                rxcui = cands[0].get("rxcui") if cands else None
            if rxcui:
                nm, ingredient, atc = self._enrich_rxcui(rxcui)
                if ingredient or atc:
                    return {"rxcui": rxcui, "name": nm, "ingredient": ingredient,
                            "atc_class": atc, "matched_on": cand}
        return None

    def lookup_name(self, name):
        name = "" if name is None else str(name).strip()
        if len(name) < 3:
            return None
        key = name.lower()
        memo = self._mem.get(("name", key), False)
        if memo is not False:
            return memo
        cached = self.cache.get("rxnorm_name", key)
        if cached is not None:
            self._mem[("name", key)] = cached
            return cached
        rec = self._resolve_name(name)
        self.cache.set("rxnorm_name", key, rec)
        self._mem[("name", key)] = rec
        return rec


class CMSAffiliationClient:
    """CMS Provider Data Catalog 'Facility Affiliation Data' — authoritative
    clinician-to-facility affiliations keyed on NPI (facility type + CCN). Queried
    per NPI through the datastore API (no multi-GB download), cached per NPI."""

    def __init__(self, cache: DiskCache, timeout=30):
        self.cache = cache
        self.timeout = timeout
        self.session = _make_session()
        self._mem = {}

    def affiliations(self, npi):
        """Return a list of {facility_type, ccn} for an NPI (possibly empty)."""
        npi = str(npi).strip()
        if not config.npi_is_valid(npi):
            return None
        memo = self._mem.get(npi, False)
        if memo is not False:
            return memo
        cached = self.cache.get("cms_affil", npi)
        if cached is not None:
            self._mem[npi] = cached
            return cached
        rows = []
        try:
            params = {
                "conditions[0][property]": "NPI",
                "conditions[0][operator]": "=",
                "conditions[0][value]": npi,
                "limit": 50,
            }
            r = self.session.get(PDC_AFFIL_QUERY, params=params, timeout=self.timeout)
            if r.status_code == 200:
                j = r.json()
                for row in (j.get("results") or j.get("data") or []):
                    if isinstance(row, dict):
                        rows.append({
                            "facility_type": row.get("facility_type", "") or "",
                            "ccn": row.get("facility_affiliations_certification_number", "") or "",
                        })
        except Exception:
            rows = []
        self.cache.set("cms_affil", npi, rows)
        self._mem[npi] = rows
        return rows

    @staticmethod
    def summarize(rows):
        """Compact authoritative-affiliation string, e.g. 'Hospital x2; SNF x1
        (CCNs: 090012, 360112)'. Empty string when there are no affiliations."""
        if not rows:
            return ""
        from collections import Counter
        types = Counter(r.get("facility_type", "").strip() for r in rows if r.get("facility_type"))
        parts = []
        for t, n in types.most_common():
            parts.append(f"{t} x{n}" if n > 1 else t)
        ccns = [r.get("ccn", "").strip() for r in rows if r.get("ccn")]
        ccns = list(dict.fromkeys(ccns))
        tail = f" (CCNs: {', '.join(ccns[:6])}{'…' if len(ccns) > 6 else ''})" if ccns else ""
        return "; ".join(parts) + tail


class CMSHospitalClient:
    """Resolve a CCN (from the Facility Affiliation file) to a named facility +
    type, and ownership when available. Tries CMS 'Hospital General Information'
    first (acute + critical-access, carries ownership), then falls back to the
    Inpatient-Rehab, Long-Term-Care-Hospital, and Hospice general-info files so
    non-acute CCNs resolve to a name too — pushing affiliation toward 0% blank.
    Cached per CCN through the datastore query API."""

    # (dataset_id, ccn_field, name_field, type_label, has_ownership)
    _SOURCES = [
        ("xubh-q36u", "facility_id", "facility_name", None, True),   # acute / CAH
        ("7t8x-u3ir", "cms_certification_number_ccn", "provider_name", "Inpatient Rehab Facility", False),
        ("azum-44iv", "cms_certification_number_ccn", "provider_name", "Long-Term Care Hospital", False),
        ("yc9t-dgbk", "cms_certification_number_ccn", "facility_name", "Hospice", False),
    ]
    _BASE = "https://data.cms.gov/provider-data/api/1/datastore/query/{}/0"

    def __init__(self, cache: DiskCache, timeout=30):
        self.cache = cache
        self.timeout = timeout
        self.session = _make_session()
        self._mem = {}

    def _query(self, dataset_id, field, ccn):
        try:
            params = {
                "conditions[0][property]": field,
                "conditions[0][operator]": "=",
                "conditions[0][value]": ccn,
                "limit": 1,
            }
            r = self.session.get(self._BASE.format(dataset_id), params=params, timeout=self.timeout)
            if r.status_code == 200:
                rows = r.json().get("results") or r.json().get("data") or []
                if rows and isinstance(rows[0], dict):
                    return rows[0]
        except Exception:
            return None
        return None

    def hospital(self, ccn):
        ccn = str(ccn).strip()
        if not ccn:
            return None
        memo = self._mem.get(ccn, False)
        if memo is not False:
            return memo
        cached = self.cache.get("cms_hospital", ccn)
        if cached is not None:
            self._mem[ccn] = cached
            return cached
        rec = None
        for dataset_id, field, name_field, type_label, has_own in self._SOURCES:
            row = self._query(dataset_id, field, ccn)
            if row and (row.get(name_field) or "").strip():
                rec = {
                    "name": (row.get(name_field) or "").strip(),
                    "type": (row.get("hospital_type") or type_label or "").strip() if has_own
                            else (type_label or "").strip(),
                    "ownership": (row.get("hospital_ownership") or "").strip() if has_own else "",
                    "city": (row.get("citytown") or row.get("city") or "").strip(),
                    "state": (row.get("state") or "").strip(),
                }
                break
        self.cache.set("cms_hospital", ccn, rec)
        self._mem[ccn] = rec
        return rec


def summarize_affiliations(rows, hospital_client=None, ccn_map=None):
    """Build (label, ownerships) for a provider's facility affiliations.

    If ccn_map (ccn -> resolved hospital record) is supplied, use it and make NO
    network calls — this lets the caller resolve every distinct CCN once, in
    parallel, then assemble summaries cheaply. Otherwise fall back to resolving
    each CCN through hospital_client inline.

    label: human-readable, hospital NAMES when a CCN resolves, else facility
           type. ownerships: deduped ownership types across resolved hospitals."""
    if not rows:
        return "", ""
    named, unresolved_types, ownerships = [], {}, []
    for r in rows:
        ccn = (r.get("ccn") or "").strip()
        ftype = (r.get("facility_type") or "").strip()
        if ccn_map is not None:
            hosp = ccn_map.get(ccn)
        else:
            hosp = hospital_client.hospital(ccn) if (hospital_client and ccn) else None
        if hosp and hosp.get("name"):
            own = hosp.get("ownership", "")
            tag = hosp["name"].title()
            if own:
                short = own.split(" - ")[0].strip()
                tag += f" ({short})"
                if short not in ownerships:
                    ownerships.append(short)
            if tag not in named:
                named.append(tag)
        else:
            unresolved_types[ftype] = unresolved_types.get(ftype, 0) + 1
    parts = list(named[:6])
    extra = []
    for t, n in unresolved_types.items():
        if t:
            extra.append(f"{n} {t}" if n > 1 else t)
    if extra:
        parts.append("+ " + "; ".join(extra))
    label = "; ".join(parts)
    return label, "; ".join(ownerships)
