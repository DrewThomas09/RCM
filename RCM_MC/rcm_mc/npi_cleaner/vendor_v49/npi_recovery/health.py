"""Live source health check. Probes every public endpoint the tool depends on
with small, bounded requests and reports PASS/FAIL. Run via:

    python recover_npis.py --health
"""

import time

from . import config
from .clients import CMSClient, NPPESClient, DiskCache


def run_health_check(cache_dir=None):
    """Returns a list of dict rows: {source, ok, detail, seconds}."""
    cms = CMSClient(DiskCache(cache_dir or config.DEFAULT_CACHE_DIR))
    nppes = NPPESClient(DiskCache(cache_dir or config.DEFAULT_CACHE_DIR))
    rows = []

    def probe(source, fn):
        t0 = time.time()
        try:
            ok, detail = fn()
        except Exception as e:
            ok, detail = False, f"{type(e).__name__}: {e}"
        rows.append({"source": source, "ok": bool(ok), "detail": str(detail),
                     "seconds": round(time.time() - t0, 1)})

    # 1) catalog resolution + minimal pull for each CMS dataset
    for key, title in config.DATASET_TITLES.items():
        def _f(title=title):
            url = cms.latest_api_url(title)
            df = cms.pull(title, page=3, max_rows=3)
            return (len(df) > 0 and bool(url), f"{len(df)} rows; {len(df.columns)} cols")
        probe(f"CMS · {key}", _f)

    # 2) the filtered pulls the recovery engine actually issues
    probe("CMS · physician billers (J1745/TX)",
          lambda: ((lambda p: (len(p) > 0, f"{len(p)} providers"))(cms.billers_physician("J1745", "TX"))))
    probe("CMS · physician NATIONAL (J2350)",
          lambda: ((lambda t: (len(t[0]) > 0, f"{len(t[0])} rows / {t[0]['state'].nunique()} states"))(cms.billers_by_hcpcs("J2350"))))
    probe("CMS · DME suppliers (E0601/TX)",
          lambda: ((lambda d: (True, f"{len(d)} suppliers"))(cms.billers_dme("E0601", "TX"))))

    # 3) enrichment sources
    probe("CMS · geography benchmark (J1745)",
          lambda: ((lambda g: (bool(g), f"{int(g.get('natl_providers') or 0):,} natl providers" if g else "no row"))(cms.geography_benchmark("J1745"))))
    probe("CMS · Part D presence (ustekinumab)",
          lambda: ((lambda p: (p.get('partd_rows', 0) > 0, f"{p.get('partd_rows',0)} rows"))(cms.partd_presence("Ustekinumab", max_rows=20))))

    # 4) reconciliation / rate sources (the "no VRDC needed" set)
    probe("CMS · PSPS site-of-care (J1745)",
          lambda: ((lambda d: (bool(d), f"office {d.get('pct_office_services')}% of services" if d else "no row"))(cms.psps_site_of_care("J1745", max_rows=4000))))
    probe("CMS · Market Saturation (TX)",
          lambda: ((lambda df: (len(df) > 0, f"{len(df)} county rows"))(cms.market_saturation_ffs("TX"))))
    from . import cms_rates
    _asp = cms_rates.ASPClient(DiskCache(cache_dir or config.DEFAULT_CACHE_DIR))
    probe("CMS · ASP payment limit (ASP+6%)",
          lambda: ((lambda n: (n > 0, f"{n:,} HCPCS rates; J1745=${_asp.rate('J1745')}"))(_asp.available())))

    # 5) verified-NPI sources (identity / eligibility cross-checks)
    probe("CMS · PECOS provider enrollment",
          lambda: ((lambda e: (e.get("enrolled", False), f"{e.get('provider_type','-')}" if e.get("enrolled") else "lookup ok"))(cms.enrollment_lookup("1003914151"))))
    probe("CMS · Order & Referring eligibility",
          lambda: ((lambda o: (o.get("in_order_referring", False), "can refer Part B" if o.get("can_refer_partb") else "lookup ok"))(cms.order_referring_lookup("1003914151"))))
    probe("CMS · Opt Out Affidavits",
          lambda: ((lambda o: (isinstance(o, dict) and "opted_out" in o, "opted out" if o.get("opted_out") else "lookup ok (not opted out)"))(cms.opt_out_lookup("1003914151"))))

    probe("NPPES · provider lookup",
          lambda: ((lambda r: (bool(r), f"{r.get('name','-')} / {r.get('entity_type','-')}" if r else "not found"))(nppes.lookup("1003914151"))))
    probe("NPPES · organization name search",
          lambda: ((lambda r: (bool(r), f"{r.get('name','-')}" if r else "no match"))(nppes.search_org("Mayo Clinic", state="MN"))))

    # 340B taxonomy classifier (offline sanity check)
    from . import hrsa340b
    def _probe_340b():
        cls, bucket = hrsa340b.classify_taxonomy("261QF0400X")
        arb = hrsa340b.arbitrage_flag("J2507")
        return (bool(cls) and bool(arb), f"FQHC->{cls or '-'}; J2507 arb flag set={bool(arb)}")
    probe("340B · taxonomy classifier + arbitrage flags", _probe_340b)

    # v7 bulk reference tables (load-once, join-locally). Downloads on first run,
    # then cached; the probe forces a real fetch so it reports row counts.
    from . import bulk
    def _probe_bulk(name):
        def _f():
            t = bulk.get_table(name, cache_dir=cache_dir)
            if t is None:
                return (False, "not in registry")
            df = t.ensure()
            if df is None:
                return (False, "download/cache unavailable (live API fallback used)")
            state, age, n = t.status()
            return (len(df) > 0, f"{len(df):,} rows; cache {state}")
        return _f
    probe("BULK · NUCC taxonomy (local join)", _probe_bulk("nucc_taxonomy"))
    probe("BULK · CMS deactivated-NPI (local join)", _probe_bulk("deactivated_npi"))

    # v11 verified-build connectors (authoritative direct lookups)
    from .clients import RxNormClient, CMSAffiliationClient, CMSHospitalClient
    _cache = DiskCache(cache_dir or config.DEFAULT_CACHE_DIR)
    rx = RxNormClient(_cache)
    aff = CMSAffiliationClient(_cache)
    hosp = CMSHospitalClient(_cache)
    probe("RxNorm · NDC → ingredient/class (NLM)",
          lambda: ((lambda r: (bool(r and r.get("ingredient")),
                               f"{r.get('ingredient','-')} / {r.get('atc_class','-')[:32]}" if r else "no match"))
                   (rx.lookup_ndc("00069080901"))))
    probe("RxNorm · drug name → ingredient (NLM)",
          lambda: ((lambda r: (bool(r and r.get("ingredient")),
                               f"{r.get('ingredient','-')}" if r else "no match"))
                   (rx.lookup_name("ustekinumab"))))
    probe("CMS · Facility Affiliation by NPI (PDC)",
          lambda: ((lambda rws: (rws is not None,
                                 CMSAffiliationClient.summarize(rws)[:42] or "no affiliations on file"))
                   (aff.affiliations("1003000126"))))
    probe("CMS · CCN → named hospital + ownership (PDC)",
          lambda: ((lambda h: (bool(h and h.get("name")),
                               f"{h.get('name','-')} / {h.get('ownership','-')[:24]}" if h else "no match"))
                   (hosp.hospital("250009"))))
    # CDC: area-level only (no provider/billing data). Probe PLACES to confirm
    # reachability; it is NOT wired as a fill source because it can't verify a
    # claim's providers or drugs — it would only add county health context.
    probe("CDC · PLACES county health (area context only)",
          lambda: ((lambda j: (len(j) > 0, "reachable — area-level only, not a fill source"))
                   (__import__("requests").get(
                       "https://chronicdata.cdc.gov/resource/swc5-untb.json?$limit=1",
                       timeout=20).json())))

    return rows
