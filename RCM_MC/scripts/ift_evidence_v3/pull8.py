"""X-A.1: the remaining nine MUP provider vintages (2014-2018, 2020-2023),
ambulance HCPCS only, same slim schema as pull7's provider pulls.
Converts the three provider snapshots into a true 11-vintage annual series.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pull import catalog_uuids, load_manifest, log, paged_dataapi, record  # noqa: E402
from pull7 import AMB_CODES, MUP_PROV_KEEP  # noqa: E402

YEARS = ['2014', '2015', '2016', '2017', '2018', '2020', '2021', '2022', '2023']


def pull_mup_provider_series(man):
    uuids = catalog_uuids('Medicare Physician & Other Practitioners - by Provider and Service')
    for yr in YEARS:
        uuid = uuids.get(yr)
        if not uuid:
            log(f'MUP provider {yr}: no uuid; have {sorted(uuids)[:4]}...')
            continue
        for code in AMB_CODES:
            key = f'mup_provider_{yr}_{code}'
            if key in man:
                continue
            log(f'MUP provider {yr} {code}')
            try:
                rows, pages, base = paged_dataapi(uuid, {'HCPCS_Cd': code}, sleep=0.15)
            except Exception as e:  # noqa: BLE001
                log(f'  PARK {key}: {type(e).__name__}: {str(e)[:100]}')
                continue
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


if __name__ == '__main__':
    man = load_manifest()
    pull_mup_provider_series(man)
    log('ALL DONE 8')
