"""Live GOV data pulls for IFT Sourced Evidence Master v3.

Every artifact is cached as JSON under ift_v3_cache/ with a manifest entry:
endpoint(s), filters, pages, rows, sha256 of the canonical payload, UTC
timestamp. Resumable: artifacts already in the manifest are skipped.
"""
import csv
import hashlib
import io
import json
import os
import ssl
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

SCRATCH = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(SCRATCH, 'ift_v3_cache')
os.makedirs(CACHE, exist_ok=True)
MANIFEST = os.path.join(CACHE, 'manifest.json')

CTX = ssl.create_default_context(cafile='/root/.ccr/ca-bundle.crt')
OPENER = urllib.request.build_opener(
    urllib.request.ProxyHandler({'https': os.environ.get('HTTPS_PROXY', '')}),
    urllib.request.HTTPSHandler(context=CTX))

AMB_CODES = ['A0425', 'A0426', 'A0427', 'A0428', 'A0429', 'A0430',
             'A0431', 'A0432', 'A0433', 'A0434', 'A0435', 'A0436']
GROUND_CODES = ['A0425', 'A0426', 'A0427', 'A0428', 'A0429', 'A0433', 'A0434']


def log(msg):
    print(f'[{datetime.now(timezone.utc).strftime("%H:%M:%S")}] {msg}', flush=True)


def load_manifest():
    if os.path.exists(MANIFEST):
        return json.load(open(MANIFEST))
    return {}


def save_manifest(m):
    tmp = MANIFEST + '.tmp'
    json.dump(m, open(tmp, 'w'), indent=1, sort_keys=True)
    os.replace(tmp, MANIFEST)


def get(url, tries=5, timeout=90):
    last = None
    for i in range(tries):
        try:
            with OPENER.open(url, timeout=timeout) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001 — retry any transport error
            last = e
            wait = 2 ** i
            log(f'  retry {i + 1} in {wait}s: {type(e).__name__}: {str(e)[:120]}')
            time.sleep(wait)
    raise RuntimeError(f'GET failed after {tries}: {url} :: {last}')


def get_json(url):
    return json.loads(get(url).decode())


def sha(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()


def record(man, key, payload, meta):
    path = os.path.join(CACHE, key + '.json')
    json.dump(payload, open(path, 'w'))
    meta.update({'sha256': sha(payload), 'retrieved_utc':
                 datetime.now(timezone.utc).isoformat(timespec='seconds'),
                 'file': os.path.basename(path)})
    man[key] = meta
    save_manifest(man)
    log(f'  cached {key}: {meta.get("rows", "?")} rows sha={meta["sha256"][:12]}')


def paged_dataapi(uuid, filters=None, size=5000, max_pages=200, sleep=0.25):
    base = f'https://data.cms.gov/data-api/v1/dataset/{uuid}/data'
    q = {'size': str(size)}
    for k, v in (filters or {}).items():
        q[f'filter[{k}]'] = v
    rows, offset, pages = [], 0, 0
    while pages < max_pages:
        q['offset'] = str(offset)
        url = base + '?' + urllib.parse.urlencode(q)
        chunk = get_json(url)
        if not isinstance(chunk, list):
            raise RuntimeError(f'unexpected response shape at {url}: {str(chunk)[:200]}')
        rows.extend(chunk)
        pages += 1
        if len(chunk) < size:
            break
        offset += size
        time.sleep(sleep)
    return rows, pages, base


def stats_dataapi(uuid, filters=None):
    q = {}
    for k, v in (filters or {}).items():
        q[f'filter[{k}]'] = v
    url = (f'https://data.cms.gov/data-api/v1/dataset/{uuid}/data/stats'
           + ('?' + urllib.parse.urlencode(q) if q else ''))
    return get_json(url)


def catalog_uuids(title):
    """Map data year ('YYYY') -> pinned API uuid from the saved DCAT catalog.

    Versioned API distributions carry the vintage in their title as
    '<dataset> : YYYY-MM-DD'; the rolling 'latest' duplicate of the newest
    vintage is ignored in favour of the pinned uuid.
    """
    cat = json.load(open(os.path.join(SCRATCH, 'cms_catalog.json')))
    for d in cat['dataset']:
        if d.get('title', '') == title:
            out = {}
            for dist in d.get('distribution', []):
                if dist.get('format') != 'API':
                    continue
                if (dist.get('description') or '').strip().lower() == 'latest':
                    continue
                label = dist.get('title') or ''
                api = dist.get('accessURL', '')
                uuid = api.rstrip('/').split('/')[-2] if api.endswith('/data') else api.split('/')[-1]
                m = _re_year.search(label)
                if m:
                    out[m.group(1)] = uuid
            return out
    raise KeyError(title)


import re as _re_mod  # noqa: E402
_re_year = _re_mod.compile(r':\s*((?:19|20)\d\d)-\d\d-\d\d\s*$')


def num(v):
    if v in (None, '', '*'):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


# ── artifacts ────────────────────────────────────────────────────────────────

def pull_mup_national(man):
    uuids = catalog_uuids('Medicare Physician & Other Practitioners - by Geography and Service')
    for yr, uuid in sorted(uuids.items()):
        key = f'mup_national_{yr}'
        if key in man:
            continue
        log(f'MUP national {yr} ({uuid})')
        rows, pages, base = paged_dataapi(uuid, {'Rndrng_Prvdr_Geo_Lvl': 'National'})
        amb = [r for r in rows if str(r.get('HCPCS_Cd', '')).startswith('A04')]
        record(man, key, amb, {
            'dataset': 'Medicare Physician & Other Practitioners - by Geography and Service',
            'data_year': yr, 'uuid': uuid, 'endpoint': base,
            'filters': {'Rndrng_Prvdr_Geo_Lvl': 'National', 'client_side': "HCPCS_Cd startswith 'A04'"},
            'pages': pages, 'rows': len(amb), 'rows_unfiltered': len(rows)})


def pull_mup_state(man):
    uuids = catalog_uuids('Medicare Physician & Other Practitioners - by Geography and Service')
    for yr in ('2019', '2024'):
        uuid = uuids.get(yr)
        if not uuid:
            log(f'MUP state {yr}: no uuid, skipping')
            continue
        for code in AMB_CODES:
            key = f'mup_state_{yr}_{code}'
            if key in man:
                continue
            log(f'MUP state {yr} {code}')
            rows, pages, base = paged_dataapi(
                uuid, {'Rndrng_Prvdr_Geo_Lvl': 'State', 'HCPCS_Cd': code})
            record(man, key, rows, {
                'dataset': 'Medicare Physician & Other Practitioners - by Geography and Service',
                'data_year': yr, 'uuid': uuid, 'endpoint': base,
                'filters': {'Rndrng_Prvdr_Geo_Lvl': 'State', 'HCPCS_Cd': code},
                'pages': pages, 'rows': len(rows)})


def pull_psps(man):
    label_by_year = catalog_uuids('Physician/Supplier Procedure Summary')
    for yr in sorted(label_by_year):
        if int(yr) < 2010:
            continue
        uuid = label_by_year[yr]
        for code in GROUND_CODES:
            key = f'psps_agg_{yr}_{code}'
            if key in man:
                continue
            log(f'PSPS {yr} {code} ({uuid})')
            rows, pages, base = paged_dataapi(uuid, {'HCPCS_CD': code}, sleep=0.15)
            agg = {}
            fieldmap = {}
            if rows:
                keys0 = rows[0].keys()
                for suffix in ('SUBMITTED_SERVICE_CNT', 'SUBMITTED_CHARGE_AMT',
                               'DENIED_SERVICES_CNT', 'ALLOWED_CHARGE_AMT',
                               'NCH_PAYMENT_AMT', 'ASSIGNED_SERVICES_CNT'):
                    for k in keys0:
                        if k.upper().endswith(suffix):
                            fieldmap[suffix] = k
                            break
                modk = next((k for k in keys0 if 'INITIAL_MODIFIER' in k.upper()), None)
            for r in rows:
                mod = (r.get(modk) or '').strip() if rows and modk else ''
                a = agg.setdefault(mod or '(none)', {s: 0.0 for s in fieldmap})
                a['_lines'] = a.get('_lines', 0) + 1
                for suffix, k in fieldmap.items():
                    v = num(r.get(k))
                    if v is not None:
                        a[suffix] += v
            payload = {'year': yr, 'code': code, 'by_initial_modifier': agg,
                       'field_map': fieldmap, 'n_lines': len(rows)}
            record(man, key, payload, {
                'dataset': 'Physician/Supplier Procedure Summary', 'data_year': yr,
                'uuid': uuid, 'endpoint': base, 'filters': {'HCPCS_CD': code},
                'pages': pages, 'rows': len(rows),
                'aggregation': 'client-side sum by HCPCS initial modifier'})


def pull_market_saturation(man):
    key = 'marketsat_state'
    if key in man:
        return
    uuid = '8900b9c5-50b7-43de-9bdd-0d7113a8355e'
    # introspect columns first
    probe, _, _ = paged_dataapi(uuid, size=5, max_pages=1)
    cols = list(probe[0].keys()) if probe else []
    log(f'market saturation columns: {cols[:20]}')
    tos_col = next((c for c in cols if 'type_of_service' in c.lower()), 'type_of_service')
    all_rows = []
    types = ['Ambulance (Emergency & Non-Emergency)', 'Ambulance (Emergency)',
             'Ambulance (Non-Emergency)']
    latest = None
    for t in types:
        log(f'market saturation: {t}')
        rows, pages, base = paged_dataapi(uuid, {tos_col: t}, sleep=0.2)
        all_rows.append(slim_marketsat_block(t, rows, latest))
    record(man, key, all_rows, {
        'dataset': 'Market Saturation & Utilization State-County', 'uuid': uuid,
        'endpoint': f'https://data.cms.gov/data-api/v1/dataset/{uuid}/data',
        'filters': {tos_col: types},
        'rows': sum(len(x['nation_state_rows']) for x in all_rows),
        'note': ('nation+state rows kept in full; county grain reduced to per-state '
                 'provider-count band distributions per period, plus full county rows '
                 'for the latest period only')})


MS_KEEP = ['reference_period', 'aggregation_level', 'state', 'county', 'state_fips',
           'county_fips', 'number_of_fee_for_service_beneficiaries', 'number_of_providers',
           'number_of_users', 'percentage_of_users_out_of_ffs_beneficiaries',
           'total_payment', 'moratorium']


def _ms_band(v):
    if v is None or str(v).strip() in ('', '*', 'N/A'):
        return 'suppressed'
    try:
        n = float(str(v).replace(',', ''))
    except ValueError:
        return 'suppressed'
    if n == 0:
        return '0'
    if n < 3:
        return '1-2'
    if n < 10:
        return '3-9'
    return '10+'


def slim_marketsat_block(t, rows, latest_period=None):
    periods = sorted({r.get('reference_period') for r in rows if r.get('reference_period')})
    latest = latest_period or (periods[-1] if periods else None)
    nation_state = [{k: r.get(k) for k in MS_KEEP} for r in rows
                    if r.get('aggregation_level') in ('NATION + TERRITORIES', 'STATE')]
    county_latest = [{k: r.get(k) for k in MS_KEEP} for r in rows
                     if r.get('aggregation_level') == 'COUNTY'
                     and r.get('reference_period') == latest]
    bands = {}
    for r in rows:
        if r.get('aggregation_level') != 'COUNTY':
            continue
        k = (r.get('reference_period'), r.get('state'))
        b = bands.setdefault(k, {'suppressed': 0, '0': 0, '1-2': 0, '3-9': 0, '10+': 0,
                                 'n_counties': 0})
        b[_ms_band(r.get('number_of_providers'))] += 1
        b['n_counties'] += 1
    return {'type_of_service': t, 'n_total_rows': len(rows), 'periods': periods,
            'latest_period': latest, 'nation_state_rows': nation_state,
            'county_rows_latest': county_latest,
            'county_provider_bands': [{'reference_period': k[0], 'state': k[1], **v}
                                      for k, v in sorted(bands.items())]}


def pull_enrollment(man):
    uuid = 'd7fabe1e-d19b-4333-9eff-e80e0643f2fd'
    for key, geo in (('enrollment_state_year', 'State'), ('enrollment_national_year', 'National')):
        if key in man:
            continue
        log(f'Medicare monthly enrollment {geo} x Year')
        rows, pages, base = paged_dataapi(uuid, {'BENE_GEO_LVL': geo, 'MONTH': 'Year'})
        record(man, key, rows, {
            'dataset': 'Medicare Monthly Enrollment', 'uuid': uuid, 'endpoint': base,
            'filters': {'BENE_GEO_LVL': geo, 'MONTH': 'Year'}, 'pages': pages, 'rows': len(rows)})


def pull_qcew(man):
    for yr in range(2014, 2026):
        key = f'qcew_621910_{yr}'
        if key in man:
            continue
        url = f'https://data.bls.gov/cew/data/api/{yr}/a/industry/621910.csv'
        log(f'QCEW 621910 annual {yr}')
        raw = get(url).decode('utf-8', 'replace')
        rdr = csv.DictReader(io.StringIO(raw))
        keep = []
        for r in rdr:
            fips = r.get('area_fips', '')
            # national rows (US000) + statewide rollups (SS000); county rows dropped
            if fips == 'US000' or (len(fips) == 5 and fips.endswith('000') and fips[:2].isdigit()):
                keep.append({k: r[k] for k in (
                    'area_fips', 'own_code', 'agglvl_code', 'year', 'annual_avg_estabs',
                    'annual_avg_emplvl', 'total_annual_wages', 'avg_annual_pay',
                    'lq_annual_avg_emplvl') if k in r})
        record(man, key, keep, {
            'dataset': 'BLS QCEW NAICS 621910 (Ambulance Services), annual averages',
            'data_year': str(yr), 'endpoint': url,
            'filters': {'client_side': 'US000 + statewide (fips *000, agglvl 50/51) rows'},
            'rows': len(keep)})


def pull_pdc(man):
    sets = {
        'pdc_hospitals': ('xubh-q36u', 'Hospital General Information',
                          ['state', 'hospital_type', 'hospital_ownership', 'emergency_services']),
        'pdc_nursing_homes': ('4pq5-n9py', 'Nursing homes including rehab services — Provider Information',
                              ['state', 'ownership_type', 'number_of_certified_beds']),
        'pdc_dialysis': ('23ew-n7w9', 'Dialysis Facilities',
                         ['state', 'profit_or_non_profit', 'number_of_dialysis_stations']),
        'pdc_irf': ('7t8x-u3ir', 'Inpatient Rehabilitation Facility — General Information', ['state']),
        'pdc_ltch': ('azum-44iv', 'Long-Term Care Hospital — General Information', ['state']),
        'pdc_hospice': ('yc9t-dgbk', 'Hospice — General Information', ['state']),
        'pdc_home_health': ('6jpm-sxkc', 'Home Health Care Agencies', ['state', 'type_of_ownership']),
    }
    for key, (did, title, want) in sets.items():
        if key in man:
            continue
        log(f'PDC {title}')
        base = f'https://data.cms.gov/provider-data/api/1/datastore/query/{did}/0'
        rows, offset, pages = [], 0, 0
        while pages < 300:
            url = base + '?' + urllib.parse.urlencode({'limit': 500, 'offset': offset})
            data = get_json(url)
            chunk = data.get('results', [])
            rows.extend(chunk)
            pages += 1
            if len(chunk) < 500:
                break
            offset += 500
            time.sleep(0.15)
        cols = set(rows[0].keys()) if rows else set()
        kept_fields = [w for w in want if w in cols]
        missing = [w for w in want if w not in cols]
        slim = [{k: r.get(k) for k in kept_fields} for r in rows]
        record(man, key, slim, {
            'dataset': f'CMS Provider Data Catalog: {title}', 'dkan_id': did,
            'endpoint': base, 'pages': pages, 'rows': len(slim),
            'fields_kept': kept_fields, 'fields_missing': missing,
            'all_columns_sample': sorted(cols)[:40]})


def pull_pecos_check(man):
    key = 'pecos_stats_check'
    if key in man:
        return
    uuid = '2457ea29-fc82-48b0-86ec-3b0755de7515'
    log('PECOS ambulance supplier count check')
    st = stats_dataapi(uuid, {'PROVIDER_TYPE_DESC': 'PART B SUPPLIER - AMBULANCE SERVICE SUPPLIER'})
    record(man, key, st, {
        'dataset': 'Medicare Fee-For-Service Public Provider Enrollment', 'uuid': uuid,
        'endpoint': f'https://data.cms.gov/data-api/v1/dataset/{uuid}/data/stats',
        'filters': {'PROVIDER_TYPE_DESC': 'PART B SUPPLIER - AMBULANCE SERVICE SUPPLIER'},
        'rows': st.get('found_rows'),
        'purpose': 'live cross-check of vendored PPEF 2026.04.01 state table (10,465)'})


STAGES = [pull_pecos_check, pull_enrollment, pull_qcew, pull_market_saturation,
          pull_mup_national, pull_mup_state, pull_pdc, pull_psps]


def main():
    man = load_manifest()
    only = sys.argv[1:] or None
    for stage in STAGES:
        if only and stage.__name__ not in only:
            continue
        log(f'=== {stage.__name__} ===')
        try:
            stage(man)
        except Exception as e:  # noqa: BLE001 — keep pulling other stages
            log(f'STAGE FAILED {stage.__name__}: {type(e).__name__}: {e}')
    log('ALL DONE')


if __name__ == '__main__':
    main()
