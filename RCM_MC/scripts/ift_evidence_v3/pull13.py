"""Retry of the three parked PDC pulls with the working 500-row page size:
X-A.3 dialysis full roster, X-A.4 SNF QRP, X-A.7 timely care refresh."""
import os
import sys
import time
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pull import get_json, load_manifest, log, record  # noqa: E402

SETS = {
    'pdc_dialysis_full': ('23ew-n7w9', 'Dialysis Facilities (full roster)',
                          None),   # keep all columns; roster needs ccn/name/chain
    'pdc_snf_qrp': ('fykj-qjee', 'SNF Quality Reporting Program - Provider',
                    None),
    'pdc_timely_2026': ('yv7e-xc69', 'Timely and Effective Care - Hospital',
                        None),
}


def main():
    man = load_manifest()
    for key, (did, title, want) in SETS.items():
        if key in man:
            continue
        log(f'PDC {title}')
        base = f'https://data.cms.gov/provider-data/api/1/datastore/query/{did}/0'
        rows, offset, pages = [], 0, 0
        try:
            while pages < 600:
                url = base + '?' + urllib.parse.urlencode(
                    {'limit': 500, 'offset': offset})
                chunk = get_json(url).get('results', [])
                rows.extend(chunk)
                pages += 1
                if len(chunk) < 500:
                    break
                offset += 500
                time.sleep(0.12)
        except Exception as e:  # noqa: BLE001
            log(f'  PARK {key}: {type(e).__name__}: {str(e)[:120]}')
            continue
        if key == 'pdc_snf_qrp' and rows:
            keep_meas = {'discharge', 'rehosp', 'community'}
            cols = list(rows[0].keys())
            mcol = next((c for c in cols if 'measure' in c and 'code' in c),
                        next((c for c in cols if 'measure' in c), None))
            if mcol:
                rows = [r for r in rows
                        if any(k in str(r.get(mcol, '')).lower()
                               for k in keep_meas)]
        if key == 'pdc_timely_2026' and rows:
            cols = list(rows[0].keys())
            mcol = next((c for c in cols if 'measure_id' in c), None)
            if mcol:
                rows = [r for r in rows
                        if any(t in str(r.get(mcol, '')).upper()
                               for t in ('OP_18', 'OP_22', 'ED_2', 'ED2',
                                         'EDV', 'OP_23'))]
        record(man, key, rows, {
            'dataset': f'CMS Provider Data Catalog: {title}', 'dkan_id': did,
            'endpoint': base, 'pages': pages, 'rows': len(rows),
            'note': 'page size 500 (datastore cap); measure filter applied '
                    'client-side where noted'})
    log('ALL DONE 13')


if __name__ == '__main__':
    main()
