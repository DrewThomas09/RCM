"""County-grain QCEW pulls: NAICS 621910 county rows, private ownership."""
import csv
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pull import get, load_manifest, log, record  # noqa: E402


def pull_qcew_county(man):
    for yr in range(2014, 2026):
        key = f'qcew_county_{yr}'
        if key in man:
            continue
        url = f'https://data.bls.gov/cew/data/api/{yr}/a/industry/621910.csv'
        log(f'QCEW county 621910 {yr}')
        raw = get(url).decode('utf-8', 'replace')
        rdr = csv.DictReader(io.StringIO(raw))
        keep = []
        for r in rdr:
            fips = r.get('area_fips', '')
            if (len(fips) == 5 and fips[:2].isdigit() and not fips.endswith('000')
                    and r.get('own_code') == '5'):
                keep.append({k: r[k] for k in (
                    'area_fips', 'own_code', 'year', 'annual_avg_estabs',
                    'annual_avg_emplvl', 'total_annual_wages', 'avg_annual_pay',
                    'annual_avg_wkly_wage', 'lq_annual_avg_emplvl') if k in r})
        record(man, key, keep, {
            'dataset': 'BLS QCEW NAICS 621910 (Ambulance Services), county annual '
                       'averages, private ownership',
            'data_year': str(yr), 'endpoint': url,
            'filters': {'client_side': 'county fips rows (not *000), own_code=5'},
            'rows': len(keep),
            'note': 'County disclosure suppression zeroes small cells at source'})


if __name__ == '__main__':
    man = load_manifest()
    pull_qcew_county(man)
    log('ALL DONE 3')
