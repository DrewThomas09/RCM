"""Granularity pulls for the 200+-tab v3: MUP state all years, county-grain
market saturation for calendar windows, the full PECOS ambulance supplier
registry, rich facility listings, and hospital service-area aggregates.

Same manifest/cache contract as pull.py (extends the same manifest).
"""
import json
import os
import sys
import time
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pull import (AMB_CODES, CACHE, catalog_uuids, get_json, load_manifest, log,  # noqa: E402
                  num, paged_dataapi, record, save_manifest, stats_dataapi)


def pull_mup_state_all(man):
    uuids = catalog_uuids('Medicare Physician & Other Practitioners - by Geography and Service')
    for yr in sorted(uuids):
        if not (2013 <= int(yr) <= 2024):
            continue
        for code in AMB_CODES:
            key = f'mup_state_{yr}_{code}'
            if key in man:
                continue
            log(f'MUP state {yr} {code}')
            rows, pages, base = paged_dataapi(
                uuids[yr], {'Rndrng_Prvdr_Geo_Lvl': 'State', 'HCPCS_Cd': code},
                sleep=0.1)
            record(man, key, rows, {
                'dataset': 'Medicare Physician & Other Practitioners - by Geography and Service',
                'data_year': yr, 'uuid': uuids[yr], 'endpoint': base,
                'filters': {'Rndrng_Prvdr_Geo_Lvl': 'State', 'HCPCS_Cd': code},
                'pages': pages, 'rows': len(rows)})


MS_UUID = '8900b9c5-50b7-43de-9bdd-0d7113a8355e'
MS_TYPES = ['Ambulance (Emergency & Non-Emergency)', 'Ambulance (Emergency)',
            'Ambulance (Non-Emergency)']
MS_KEEP = ['reference_period', 'aggregation_level', 'state', 'county', 'state_fips',
           'county_fips', 'number_of_fee_for_service_beneficiaries',
           'number_of_providers', 'number_of_users',
           'percentage_of_users_out_of_ffs_beneficiaries', 'total_payment',
           'moratorium']


def pull_marketsat_county_years(man):
    """County grain for the six calendar-aligned windows (Jan-Dec), all 3 types."""
    for yr in range(2020, 2026):
        period = f'{yr}-01-01 to {yr}-12-31'
        key = f'marketsat_county_{yr}'
        if key in man:
            continue
        blocks = []
        for t in MS_TYPES:
            log(f'market saturation county {yr}: {t}')
            rows, pages, base = paged_dataapi(
                MS_UUID, {'type_of_service': t, 'reference_period': period},
                sleep=0.15)
            county = [{k: r.get(k) for k in MS_KEEP} for r in rows
                      if r.get('aggregation_level') == 'COUNTY']
            blocks.append({'type_of_service': t, 'reference_period': period,
                           'n_rows_all_grains': len(rows), 'county_rows': county})
        record(man, key, blocks, {
            'dataset': 'Market Saturation & Utilization State-County (county grain)',
            'data_year': str(yr), 'uuid': MS_UUID,
            'endpoint': f'https://data.cms.gov/data-api/v1/dataset/{MS_UUID}/data',
            'filters': {'type_of_service': MS_TYPES, 'reference_period': period},
            'rows': sum(len(b['county_rows']) for b in blocks)})


PECOS_UUID = '2457ea29-fc82-48b0-86ec-3b0755de7515'


def pull_pecos_registry(man):
    key = 'pecos_ambulance_registry'
    if key in man:
        return
    log('PECOS full ambulance supplier registry')
    rows, pages, base = paged_dataapi(
        PECOS_UUID,
        {'PROVIDER_TYPE_DESC': 'PART B SUPPLIER - AMBULANCE SERVICE SUPPLIER'},
        sleep=0.2)
    keep_cols = None
    if rows:
        pref = ['NPI', 'PECOS_ASCT_CNTL_ID', 'ENRLMT_ID', 'PROVIDER_TYPE_DESC',
                'STATE_CD', 'FIRST_NAME', 'MDL_NAME', 'LAST_NAME', 'ORG_NAME',
                'GNDR_SW']
        keep_cols = [c for c in pref if c in rows[0]]
    slim = [{c: r.get(c) for c in keep_cols} for r in rows] if keep_cols else rows
    record(man, key, slim, {
        'dataset': 'Medicare Fee-For-Service Public Provider Enrollment', 'uuid': PECOS_UUID,
        'endpoint': base,
        'filters': {'PROVIDER_TYPE_DESC': 'PART B SUPPLIER - AMBULANCE SERVICE SUPPLIER'},
        'pages': pages, 'rows': len(slim), 'fields_kept': keep_cols})


PDC2 = {
    'pdc2_hospitals': ('xubh-q36u', 'Hospital General Information',
                       ['facility_id', 'facility_name', 'citytown', 'state',
                        'zip_code', 'countyparish', 'hospital_type',
                        'hospital_ownership', 'emergency_services']),
    'pdc2_nursing_homes': ('4pq5-n9py', 'Nursing homes including rehab services',
                           ['cms_certification_number_ccn', 'provider_name',
                            'citytown', 'state', 'zip_code', 'countyparish',
                            'ownership_type', 'number_of_certified_beds',
                            'average_number_of_residents_per_day',
                            'overall_rating']),
    'pdc2_dialysis': ('23ew-n7w9', 'Dialysis Facilities',
                      ['cms_certification_number_ccn', 'facility_name', 'city',
                       'state', 'zip_code', 'county_parish',
                       'profit_or_nonprofit', '_of_dialysis_stations',
                       'offers_incenter_hemodialysis']),
    'pdc2_irf': ('7t8x-u3ir', 'Inpatient Rehabilitation Facilities',
                 ['cms_certification_number_ccn', 'facility_name', 'citytown',
                  'state', 'zip_code', 'countyparish', 'ownership_type']),
    'pdc2_ltch': ('azum-44iv', 'Long-Term Care Hospitals',
                  ['cms_certification_number_ccn', 'facility_name', 'citytown',
                   'state', 'zip_code', 'countyparish', 'ownership_type']),
    'pdc2_hospice': ('yc9t-dgbk', 'Hospice Providers',
                     ['cms_certification_number_ccn', 'facility_name', 'citytown',
                      'state', 'zip_code', 'countyparish', 'ownership_type']),
    'pdc2_home_health': ('6jpm-sxkc', 'Home Health Agencies',
                         ['cms_certification_number_ccn', 'provider_name',
                          'citytown', 'state', 'zip_code', 'type_of_ownership']),
}


def pull_pdc_rich(man):
    from pull import OPENER  # reuse transport
    for key, (did, title, want) in PDC2.items():
        if key in man:
            continue
        log(f'PDC rich {title}')
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
            time.sleep(0.12)
        cols = set(rows[0].keys()) if rows else set()
        kept = [w for w in want if w in cols]
        missing = [w for w in want if w not in cols]
        slim = [{k: r.get(k) for k in kept} for r in rows]
        record(man, key, slim, {
            'dataset': f'CMS Provider Data Catalog: {title} (rich fields)',
            'dkan_id': did, 'endpoint': base, 'pages': pages, 'rows': len(slim),
            'fields_kept': kept, 'fields_missing': missing,
            'all_columns_sample': sorted(cols)[:50]})


def pull_hsa(man):
    key = 'hsa_2025_hospital_agg'
    if key in man:
        return
    uuids = catalog_uuids('Hospital Service Area')
    yr = max(uuids)
    uuid = uuids[yr]
    st = stats_dataapi(uuid)
    log(f'Hospital Service Area {yr}: {st.get("found_rows")} rows, aggregating per hospital')
    agg = {}
    base = f'https://data.cms.gov/data-api/v1/dataset/{uuid}/data'
    offset, pages, size = 0, 0, 5000
    fieldmap = {}
    while True:
        url = base + '?' + urllib.parse.urlencode({'size': size, 'offset': offset})
        chunk = get_json(url)
        if not chunk:
            break
        if not fieldmap:
            k0 = chunk[0].keys()
            def find(*subs):
                for k in k0:
                    lk = k.lower()
                    if all(s in lk for s in subs):
                        return k
                return None
            fieldmap = {'id': find('medicare', 'prov') or find('provider'),
                        'zip': find('zip'),
                        'cases': find('total', 'cases') or find('cases'),
                        'days': find('total', 'days'),
                        'charges': find('total', 'charges')}
            log(f'  HSA fields: {fieldmap}')
        for r in chunk:
            pid = r.get(fieldmap['id'])
            if not pid:
                continue
            a = agg.setdefault(pid, {'zips': 0, 'cases': 0.0, 'days': 0.0,
                                     'charges': 0.0})
            a['zips'] += 1
            for f in ('cases', 'days', 'charges'):
                v = num(r.get(fieldmap[f])) if fieldmap[f] else None
                if v:
                    a[f] += v
        pages += 1
        offset += size
        if len(chunk) < size:
            break
        if pages % 20 == 0:
            log(f'  ...{pages} pages, {offset} rows, {len(agg)} hospitals')
        time.sleep(0.1)
    payload = {'data_year': yr, 'fieldmap': fieldmap, 'n_source_rows': offset,
               'hospitals': [{'provider_id': k, **v} for k, v in sorted(agg.items())]}
    record(man, key, payload, {
        'dataset': 'Hospital Service Area', 'data_year': yr, 'uuid': uuid,
        'endpoint': base, 'filters': {},
        'pages': pages, 'rows': len(agg),
        'aggregation': 'client-side per-hospital sums over hospital x ZIP rows '
                       '(zips served, total cases/days/charges)'})


STAGES = [pull_pecos_registry, pull_mup_state_all, pull_marketsat_county_years,
          pull_pdc_rich, pull_hsa]


def main():
    man = load_manifest()
    only = sys.argv[1:] or None
    for stage in STAGES:
        if only and stage.__name__ not in only:
            continue
        log(f'=== {stage.__name__} ===')
        try:
            stage(man)
        except Exception as e:  # noqa: BLE001
            log(f'STAGE FAILED {stage.__name__}: {type(e).__name__}: {e}')
    log('ALL DONE 2')


if __name__ == '__main__':
    main()
