"""B.1 primaries: GADCS Year 1-4 appendix PDF, DocGo 10-K (EDGAR),
USAspending PSC V225 series + recipients (+ geography for B.13).
Everything cached with SHA-256 in the manifest; binary docs stored beside the
JSON cache with their own hash records.
"""
import hashlib
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pull import CACHE, OPENER, load_manifest, log, record  # noqa: E402

GADCS_URL = ('https://www.cms.gov/files/document/medicare-ground-ambulance-'
             'data-collection-system-gadcs-report-appendix-year-1-year-4-'
             'cohort-analysis.pdf')
DOCGO_ACC = '0001628280-26-018214'
DOCGO_CIK = '1822359'
DOCGO_DOC = 'dcgo-20251231.htm'
USA_BASE = 'https://api.usaspending.gov/api/v2'


def fetch_binary(man, key, url, note):
    path = os.path.join(CACHE, f'_{key}')
    if key in man and os.path.exists(path):
        return path
    log(f'GET {url}')
    req = urllib.request.Request(url, headers={
        'User-Agent': 'ift-evidence-build (research; contact: ast3801@gmail.com)'})
    data = urllib.request.urlopen(req, timeout=300).read()
    open(path, 'wb').write(data)
    record(man, key, {'file': f'_{key}', 'bytes': len(data),
                      'sha256': hashlib.sha256(data).hexdigest()},
           {'dataset': note, 'endpoint': url, 'rows': 1,
            'note': f'binary document, {len(data):,} bytes, stored in cache dir'})
    return path


def post_json(url, payload):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={'Content-Type': 'application/json',
                 'User-Agent': 'ift-evidence-build (research)'})
    return json.load(urllib.request.urlopen(req, timeout=180))


def pull_gadcs(man):
    fetch_binary(man, 'gadcs_appendix_y1y4.pdf', GADCS_URL,
                 'CMS GADCS Report Appendix, Year 1-Year 4 cohort analysis (RAND)')


def pull_docgo(man):
    acc = DOCGO_ACC.replace('-', '')
    url = f'https://www.sec.gov/Archives/edgar/data/{DOCGO_CIK}/{acc}/{DOCGO_DOC}'
    fetch_binary(man, 'docgo_10k_fy2025.htm', url,
                 f'DocGo Inc. Form 10-K FY2025, EDGAR accession {DOCGO_ACC}')


def pull_usaspending(man):
    fy = [{'start_date': '2022-10-01', 'end_date': '2025-09-30'}]
    jobs = {
        'usasp_v225_time_all': (
            f'{USA_BASE}/search/spending_over_time/',
            {'group': 'fiscal_year',
             'filters': {'time_period': fy, 'psc_codes': ['V225']}}),
        'usasp_v225_time_va': (
            f'{USA_BASE}/search/spending_over_time/',
            {'group': 'fiscal_year',
             'filters': {'time_period': fy, 'psc_codes': ['V225'],
                         'agencies': [{'type': 'awarding', 'tier': 'toptier',
                                       'name': 'Department of Veterans Affairs'}]}}),
        'usasp_v225_recipients_fy25': (
            f'{USA_BASE}/search/spending_by_category/recipient/',
            {'filters': {'time_period': [{'start_date': '2024-10-01',
                                          'end_date': '2025-09-30'}],
                         'psc_codes': ['V225']},
             'limit': 50}),
        'usasp_v225_states_fy25': (
            f'{USA_BASE}/search/spending_by_geography/',
            {'scope': 'place_of_performance', 'geo_layer': 'state',
             'filters': {'time_period': [{'start_date': '2024-10-01',
                                          'end_date': '2025-09-30'}],
                         'psc_codes': ['V225']}}),
        'usasp_v225_recipients_fy24': (
            f'{USA_BASE}/search/spending_by_category/recipient/',
            {'filters': {'time_period': [{'start_date': '2023-10-01',
                                          'end_date': '2024-09-30'}],
                         'psc_codes': ['V225']},
             'limit': 50}),
        'usasp_v225_recipients_fy23': (
            f'{USA_BASE}/search/spending_by_category/recipient/',
            {'filters': {'time_period': [{'start_date': '2022-10-01',
                                          'end_date': '2023-09-30'}],
                         'psc_codes': ['V225']},
             'limit': 50}),
    }
    for key, (url, payload) in jobs.items():
        if key in man:
            continue
        log(f'USAspending {key}')
        try:
            data = post_json(url, payload)
        except Exception as e:  # noqa: BLE001
            log(f'  PARK {key}: {type(e).__name__}: {str(e)[:120]}')
            continue
        record(man, key, data, {
            'dataset': 'USAspending award search, PSC V225 (Ambulance Service)',
            'endpoint': url, 'filters': payload.get('filters'),
            'rows': len(data.get('results', [])),
            'note': 'Procurement obligations only; the VA Beneficiary Travel '
                    'claims channel is separate and larger; never sum the two'})


if __name__ == '__main__':
    man = load_manifest()
    for stage in (pull_gadcs, pull_docgo, pull_usaspending):
        log(f'=== {stage.__name__} ===')
        try:
            stage(man)
        except Exception as e:  # noqa: BLE001
            log(f'STAGE FAILED {stage.__name__}: {type(e).__name__}: {e}')
    log('ALL DONE 9')
