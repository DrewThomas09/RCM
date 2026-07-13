"""Run 5, Task 5.1: PSPS re-cut by the HCPCS SECOND modifier (QN / QM / none).

The existing psps_agg_* cache aggregates carrier ambulance lines by the INITIAL
modifier (the origin-destination code). The QN (service furnished directly by a
provider of services) and QM (service provided under arrangement by a provider
of services) payment flags ride in the SECOND modifier field, so they were never
captured. This pass pages every ambulance A-code line per year and aggregates by
a normalized second-modifier bucket, carrying a floor (unsuppressed sum) plus the
count of CMS-suppressed ('*') rows, and a joint origin-destination cut for the
QN and QM buckets. Totals across buckets reconcile to the existing psps_agg total
for the same code and year (live cross-check row in the workbook).

Field names differ across PSPS vintages (older years drop the PSPS_ prefix), so
the numeric and modifier fields are detected by suffix, exactly like pull_psps.
"""
import json
import os
import time

import pull

CACHE = 'ift_v3_cache'
CODES = ['A0425', 'A0426', 'A0427', 'A0428', 'A0429', 'A0433', 'A0434']
SUFFIXES = {'SUBMITTED_SERVICE_CNT': 'services',
            'SUBMITTED_CHARGE_AMT': 'submitted',
            'ALLOWED_CHARGE_AMT': 'allowed',
            'DENIED_SERVICES_CNT': 'denied',
            'NCH_PAYMENT_AMT': 'paid',
            'ASSIGNED_SERVICES_CNT': 'assigned'}


def numsup(v):
    if v in ('*', '', '~', None):
        return 0.0, (1 if v == '*' else 0)
    try:
        return float(str(v).replace(',', '').replace('$', '')), 0
    except ValueError:
        return 0.0, 0


def bucket_of(second):
    s = (second or '').strip().upper()
    return s if s in ('QN', 'QM') else 'none'


def main():
    man = []
    uuids = pull.catalog_uuids('Physician/Supplier Procedure Summary')
    years = sorted(uuids)
    for yr in years:
        uuid = uuids[yr]
        for code in CODES:
            key = f'psps_mod2_{yr}_{code}'
            rows, pages, base = pull.paged_dataapi(uuid, {'HCPCS_CD': code}, sleep=0.12)
            fieldmap, modk, mod2k = {}, None, None
            if rows:
                keys0 = list(rows[0].keys())
                for suf in SUFFIXES:
                    for k in keys0:
                        if k.upper().endswith(suf):
                            fieldmap[suf] = k
                            break
                modk = next((k for k in keys0 if 'INITIAL_MODIFIER' in k.upper()), None)
                mod2k = next((k for k in keys0 if 'SECOND_MODIFIER' in k.upper()), None)
            buckets = {}
            total = {sh: 0.0 for sh in SUFFIXES.values()}
            for r in rows:
                b = bucket_of(r.get(mod2k) if mod2k else '')
                bk = buckets.setdefault(b, {sh: 0.0 for sh in SUFFIXES.values()}
                                        | {'n_rows': 0, 'n_supp': 0, 'by_od': {}})
                for suf, sh in SUFFIXES.items():
                    if suf in fieldmap:
                        val, sup = numsup(r.get(fieldmap[suf]))
                        bk[sh] += val
                        total[sh] += val
                        if suf == 'SUBMITTED_SERVICE_CNT':
                            bk['n_supp'] += sup
                bk['n_rows'] += 1
                if b in ('QN', 'QM'):
                    od = (r.get(modk) or '').strip() if modk else ''
                    od = od or '(none)'
                    sv, _ = numsup(r.get(fieldmap.get('SUBMITTED_SERVICE_CNT')))
                    bk['by_od'][od] = bk['by_od'].get(od, 0.0) + sv
            payload = {'year': yr, 'code': code, 'buckets': buckets,
                       'total': total, 'n_lines': len(rows),
                       'field_map': fieldmap, 'mod2_field': mod2k}
            json.dump(payload, open(os.path.join(CACHE, key + '.json'), 'w'))
            man.append({'key': key, 'dataset': 'Physician/Supplier Procedure Summary',
                        'data_year': yr, 'uuid': uuid, 'endpoint': base,
                        'filters': {'HCPCS_CD': code}, 'pages': pages, 'rows': len(rows),
                        'aggregation': 'client-side sum by HCPCS second modifier (QN/QM/none)',
                        'accessed': time.strftime('%Y-%m-%d')})
            qn = buckets.get('QN', {}).get('services', 0)
            qm = buckets.get('QM', {}).get('services', 0)
            print(f'{yr} {code}: lines={len(rows):5d} total_svc={total["services"]:12,.0f} '
                  f'QN={qn:10,.0f} QM={qm:8,.0f}  mod2={mod2k}', flush=True)
    json.dump(man, open('psps_mod2_manifest.json', 'w'), indent=1)
    print(f'\nDONE: {len(man)} slices across {len(years)} years')


if __name__ == '__main__':
    main()
