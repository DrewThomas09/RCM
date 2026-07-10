"""Hospital-level ED timeliness registry pull (Care Compare Timely & Effective
Care, hospital grain) filtered to the ED throughput measures the workbook
already uses at national/state grain (OP-18b/OP-18d/OP-22, ED-2b where present).
"""
import os
import sys
import time
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pull import get_json, load_manifest, log, record  # noqa: E402

MEASURES = {'OP_18b', 'OP_18d', 'OP_22', 'ED_2b', 'ED_2_Strata_1', 'ED_2_Strata_2'}


def pull_ed_timeliness(man):
    key = 'pdc_timely_ed_hospital'
    if key in man:
        return
    did = 'yv7e-xc69'  # Timely and Effective Care - Hospital
    base = f'https://data.cms.gov/provider-data/api/1/datastore/query/{did}/0'
    rows, offset, pages = [], 0, 0
    while pages < 1200:
        url = base + '?' + urllib.parse.urlencode({'limit': 500, 'offset': offset})
        data = get_json(url)
        chunk = data.get('results', [])
        if pages == 0 and chunk:
            log(f'columns: {sorted(chunk[0].keys())[:20]}')
        for r in chunk:
            mid = r.get('measure_id') or ''
            if mid in MEASURES:
                rows.append({k: r.get(k) for k in (
                    'facility_id', 'facility_name', 'citytown', 'state',
                    'measure_id', 'measure_name', 'score', 'sample',
                    'start_date', 'end_date') if k in r})
        pages += 1
        if len(chunk) < 500:
            break
        offset += 500
        if pages % 40 == 0:
            log(f'  ...{pages} pages, kept {len(rows)}')
        time.sleep(0.1)
    record(man, key, rows, {
        'dataset': 'CMS Provider Data Catalog: Timely and Effective Care - Hospital',
        'dkan_id': did, 'endpoint': base, 'pages': pages, 'rows': len(rows),
        'filters': {'client_side': f'measure_id in {sorted(MEASURES)}'},
        'note': 'ED throughput measures at hospital grain (OP-18b/d median ED time '
                'for transferred patients, OP-22 left without being seen)'})


if __name__ == '__main__':
    pull_ed_timeliness(load_manifest())
    log('ALL DONE 4')
