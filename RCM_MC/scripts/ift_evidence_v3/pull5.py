"""County-grain market saturation for the nine non-calendar rolling windows."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pull import load_manifest, log, paged_dataapi, record  # noqa: E402
from pull2 import MS_KEEP, MS_TYPES, MS_UUID  # noqa: E402

ROLLING = [
    '2020-04-01 to 2021-03-31', '2020-07-01 to 2021-06-30', '2020-10-01 to 2021-09-30',
    '2021-04-01 to 2022-03-31', '2021-07-01 to 2022-06-30', '2021-10-01 to 2022-09-30',
    '2022-04-01 to 2023-03-31', '2022-07-01 to 2023-06-30', '2022-10-01 to 2023-09-30',
]


def pull_rolling(man):
    for period in ROLLING:
        key = 'marketsat_county_w' + period[:7].replace('-', '')
        if key in man:
            continue
        blocks = []
        for t in MS_TYPES:
            log(f'market saturation county window {period}: {t}')
            rows, pages, base = paged_dataapi(
                MS_UUID, {'type_of_service': t, 'reference_period': period},
                sleep=0.12)
            county = [{k: r.get(k) for k in MS_KEEP} for r in rows
                      if r.get('aggregation_level') == 'COUNTY']
            blocks.append({'type_of_service': t, 'reference_period': period,
                           'county_rows': county})
        record(man, key, blocks, {
            'dataset': 'Market Saturation & Utilization State-County (county grain, '
                       'rolling window)',
            'data_year': period, 'uuid': MS_UUID,
            'endpoint': f'https://data.cms.gov/data-api/v1/dataset/{MS_UUID}/data',
            'filters': {'type_of_service': MS_TYPES, 'reference_period': period},
            'rows': sum(len(b['county_rows']) for b in blocks)})


if __name__ == '__main__':
    pull_rolling(load_manifest())
    log('ALL DONE 5')
