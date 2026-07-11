"""v3.2 raw-granularity pulls: provider-level Medicare ambulance registry,
hospital->ZIP transfer corridors, county 65+ age base, county chronic-disease
prevalence, quarterly QCEW, and the OIG ambulance-exclusion registry.
"""
import csv
import io
import json
import os
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pull import (CACHE, OPENER, catalog_uuids, get, get_json, load_manifest,  # noqa: E402
                  log, num, paged_dataapi, record)

AMB_CODES = ['A0425', 'A0426', 'A0427', 'A0428', 'A0429', 'A0430', 'A0431',
             'A0432', 'A0433', 'A0434', 'A0435', 'A0436']

MUP_PROV_KEEP = ['Rndrng_NPI', 'Rndrng_Prvdr_Last_Org_Name', 'Rndrng_Prvdr_First_Name',
                 'Rndrng_Prvdr_City', 'Rndrng_Prvdr_State_Abrvtn', 'Rndrng_Prvdr_Ent_Cd',
                 'HCPCS_Cd', 'Place_Of_Srvc', 'Tot_Benes', 'Tot_Srvcs',
                 'Tot_Bene_Day_Srvcs', 'Avg_Sbmtd_Chrg', 'Avg_Mdcr_Alowd_Amt',
                 'Avg_Mdcr_Pymt_Amt']


def pull_mup_provider(man):
    uuids = catalog_uuids('Medicare Physician & Other Practitioners - by Provider and Service')
    for yr in ('2013', '2019', '2024'):
        uuid = uuids.get(yr)
        if not uuid:
            log(f'MUP provider {yr}: no uuid; have {sorted(uuids)[:3]}...')
            continue
        for code in AMB_CODES:
            key = f'mup_provider_{yr}_{code}'
            if key in man:
                continue
            log(f'MUP provider {yr} {code}')
            rows, pages, base = paged_dataapi(uuid, {'HCPCS_Cd': code}, sleep=0.15)
            keep_cols = [c for c in MUP_PROV_KEEP if rows and c in rows[0]]
            slim = [{c: r.get(c) for c in keep_cols} for r in rows]
            record(man, key, slim, {
                'dataset': 'Medicare Physician & Other Practitioners - by Provider '
                           'and Service',
                'data_year': yr, 'uuid': uuid, 'endpoint': base,
                'filters': {'HCPCS_Cd': code}, 'pages': pages, 'rows': len(slim),
                'fields_kept': keep_cols,
                'note': 'Provider grain (per NPI); rows with <=10 beneficiaries '
                        'suppressed at source'})


def pull_hsa_corridors(man):
    key = 'hsa_2025_corridors_top15'
    if key in man:
        return
    uuids = catalog_uuids('Hospital Service Area')
    yr = max(uuids)
    uuid = uuids[yr]
    log(f'HSA {yr} corridors: full scan keeping top-10 ZIPs per hospital')
    base = f'https://data.cms.gov/data-api/v1/dataset/{uuid}/data'
    per = {}
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
                        'zip': find('zip'), 'cases': find('cases'),
                        'days': find('days'), 'charges': find('charges')}
            log(f'  fields: {fieldmap}')
        for r in chunk:
            pid = r.get(fieldmap['id'])
            c = num(r.get(fieldmap['cases'])) or 0
            if not pid:
                continue
            lst = per.setdefault(pid, [])
            lst.append((c, r.get(fieldmap['zip']),
                        num(r.get(fieldmap['days'])) or 0,
                        num(r.get(fieldmap['charges'])) or 0))
            if len(lst) > 40:            # keep memory bounded, prune to top 20
                lst.sort(reverse=True)
                del lst[20:]
        pages += 1
        offset += size
        if len(chunk) < size:
            break
        if pages % 40 == 0:
            log(f'  ...{pages} pages, {len(per)} hospitals')
        time.sleep(0.08)
    out = []
    for pid, lst in per.items():
        lst.sort(reverse=True)
        for rank, (c, z, d, ch) in enumerate(lst[:15], start=1):
            out.append({'provider_id': pid, 'rank': rank, 'zip': z,
                        'cases': c, 'days': d, 'charges': ch})
    out.sort(key=lambda r: (r['provider_id'], r['rank']))
    record(man, key, out, {
        'dataset': 'Hospital Service Area (top-15 ZIP corridors per hospital)',
        'data_year': yr, 'uuid': uuid, 'endpoint': base, 'filters': {},
        'pages': pages, 'rows': len(out),
        'aggregation': 'client-side: per hospital, ZIP rows ranked by total cases, '
                       'top 15 kept; suppression drops small cells at source'})


CENSUS_CTY = ('https://www2.census.gov/programs-surveys/popest/datasets/'
              '2020-2024/counties/asrh/cc-est2024-agesex-all.csv')


def pull_census_county_age(man):
    key = 'census_county_age_2024'
    if key in man:
        return
    log('Census county age-sex (cc-est2024-agesex-all)')
    raw = get(CENSUS_CTY, timeout=300).decode('utf-8', 'replace')
    rdr = csv.DictReader(io.StringIO(raw))
    keep = []
    for r in rdr:
        # YEAR 1 = 4/1/2020 base; 2..6 = 7/1/2020..7/1/2024 estimates
        if r.get('YEAR') in ('2', '3', '4', '5', '6'):
            keep.append({k: r.get(k) for k in (
                'STATE', 'COUNTY', 'STNAME', 'CTYNAME', 'YEAR', 'POPESTIMATE',
                'AGE65PLUS_TOT', 'AGE85PLUS_TOT', 'MEDIAN_AGE_TOT')})
    record(man, key, keep, {
        'dataset': 'Census Bureau Vintage 2024 County Population Estimates by '
                   'Age and Sex (CC-EST2024-AGESEX)',
        'data_year': 'July 2020-2024 estimate rows (YEAR codes 2-6)',
        'endpoint': CENSUS_CTY,
        'filters': {'client_side': 'YEAR in (2,6); totals columns kept'},
        'rows': len(keep)})


PLACES_MEASURES = ['KIDNEY', 'CHD', 'STROKE', 'DIABETES', 'BPHIGH', 'COPD']


def pull_places_county(man):
    # KIDNEY was dropped from the newest PLACES release (swc5-untb); it comes
    # from the pinned 2023 county release (h3ej-a9ec) instead.
    dataset_for = {m: 'swc5-untb' for m in PLACES_MEASURES}
    dataset_for['KIDNEY'] = 'h3ej-a9ec'
    for m in PLACES_MEASURES:
        key = f'places_county_{m.lower()}'
        if key in man:
            continue
        log(f'CDC PLACES county: {m}')
        q = urllib.parse.urlencode({
            'measureid': m, 'datavaluetypeid': 'CrdPrv', '$limit': 50000,
            '$select': 'year,stateabbr,statedesc,locationname,locationid,'
                       'measureid,measure,data_value,totalpopulation'})
        url = f'https://data.cdc.gov/resource/{dataset_for[m]}.json?{q}'
        rows = get_json(url)
        record(man, key, rows, {
            'dataset': 'CDC PLACES: Local Data for Better Health, County Data',
            'data_year': rows[0].get('year') if rows else 'n/a',
            'endpoint': f'https://data.cdc.gov/resource/{dataset_for[m]}.json',
            'filters': {'measureid': m, 'datavaluetypeid': 'CrdPrv'},
            'rows': len(rows),
            'note': 'Model-based small-area estimates published by CDC (crude '
                    'prevalence); carried as GOV published statistics with the '
                    'CDC methodology caveat stated on-tab'})


def pull_qcew_quarterly(man):
    for yr in range(2014, 2026):
        for q in (1, 2, 3, 4):
            key = f'qcew_q_{yr}q{q}'
            if key in man:
                continue
            url = f'https://data.bls.gov/cew/data/api/{yr}/{q}/industry/621910.csv'
            log(f'QCEW quarterly {yr}Q{q}')
            try:
                raw = get(url).decode('utf-8', 'replace')
            except RuntimeError as e:
                log(f'  skip (not published?): {str(e)[:80]}')
                continue
            rdr = csv.DictReader(io.StringIO(raw))
            keep = []
            for r in rdr:
                fips = r.get('area_fips', '')
                if fips == 'US000' or (len(fips) == 5 and fips.endswith('000')
                                       and fips[:2].isdigit()):
                    keep.append({k: r.get(k) for k in (
                        'area_fips', 'own_code', 'year', 'qtr', 'qtrly_estabs',
                        'month1_emplvl', 'month2_emplvl', 'month3_emplvl',
                        'total_qtrly_wages', 'avg_wkly_wage') if k in r})
            record(man, key, keep, {
                'dataset': 'BLS QCEW NAICS 621910, quarterly',
                'data_year': f'{yr}Q{q}', 'endpoint': url,
                'filters': {'client_side': 'US000 + statewide rows'},
                'rows': len(keep)})


def pull_leie_ambulance(man):
    key = 'leie_ambulance'
    if key in man:
        return
    log('OIG LEIE exclusions (ambulance-related)')
    raw = get('https://oig.hhs.gov/exclusions/downloadables/UPDATED.csv',
              timeout=300).decode('utf-8', 'replace')
    rdr = csv.DictReader(io.StringIO(raw))
    keep = []
    total = 0
    for r in rdr:
        total += 1
        blob = ' '.join(str(v) for v in (r.get('BUSNAME'), r.get('GENERAL'),
                                         r.get('SPECIALTY'))).upper()
        if 'AMBULANCE' in blob or 'EMT' in (r.get('SPECIALTY') or '').upper():
            keep.append({k: r.get(k) for k in (
                'LASTNAME', 'FIRSTNAME', 'BUSNAME', 'GENERAL', 'SPECIALTY',
                'NPI', 'STATE', 'EXCLTYPE', 'EXCLDATE') if k in r})
    record(man, key, keep, {
        'dataset': 'HHS OIG List of Excluded Individuals/Entities (LEIE)',
        'data_year': 'current file, accessed 11 Jul 2026',
        'endpoint': 'https://oig.hhs.gov/exclusions/downloadables/UPDATED.csv',
        'filters': {'client_side': "'AMBULANCE' in busname/general/specialty or "
                                   "EMT specialty"},
        'rows': len(keep), 'rows_scanned': total})


STAGES = [pull_census_county_age, pull_places_county, pull_leie_ambulance,
          pull_qcew_quarterly, pull_mup_provider, pull_hsa_corridors]

if __name__ == '__main__':
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
    log('ALL DONE 7')
