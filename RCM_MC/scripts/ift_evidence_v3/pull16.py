"""X-A.4 retry: SNF Quality Reporting Program - Provider Data (return-leg
quality layer).

Dataset: CMS Provider Data Catalog 'Skilled Nursing Facility Quality
Reporting Program - Provider Data', identifier fykj-qjee (confirmed via the
provider-data metastore items list, title match). The datastore is long-
format: one row per (provider, measure_code). The working retrieval pattern
is the paginated datastore query with NO filter params:
  https://data.cms.gov/provider-data/api/1/datastore/query/{id}/0?limit=500&offset=N
We paginate the whole table and keep only the two claims-based return-leg
measures, pivoting to one clean record per CCN:
  S_005_02 Discharge to Community (DTC) - risk-standardized + observed
  S_004_01 Potentially Preventable 30-Day Post-Discharge Readmission (PPR-PD)
Cache key: snf_qrp.
"""
import os
import sys
import time
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pull import get_json, load_manifest, log, record  # noqa: E402

DID = 'fykj-qjee'
KEY = 'snf_qrp'

# measure_code -> field name in the pivoted per-provider record
FIELDS = {
    'S_005_02_DTC_RS_RATE':      'dtc_rs_rate',      # risk-standardized DTC %
    'S_005_02_DTC_OBS_RATE':     'dtc_obs_rate',     # observed DTC %
    'S_005_02_DTC_COMP_PERF':    'dtc_comp_perf',    # vs national rate
    'S_005_02_DTC_VOLUME':       'dtc_volume',       # denominator stays
    'S_004_01_PPR_PD_RSRR':      'ppr_rsrr',         # risk-std readmission %
    'S_004_01_PPR_PD_OBS':       'ppr_obs',          # observed readmission %
    'S_004_01_PPR_PD_COMP_PERF': 'ppr_comp_perf',    # vs national rate
    'S_004_01_PPR_PD_VOLUME':    'ppr_volume',       # denominator stays
}
CCN_FIELD = 'cms_certification_number_ccn'
# raw datastore field -> normalized key in the pivoted per-provider record
IDENT = {'provider_name': 'provider_name', 'citytown': 'citytown',
         'state': 'state', 'zip_code': 'zip', 'countyparish': 'county'}


def main():
    man = load_manifest()
    force = '--force' in sys.argv
    if KEY in man and man[KEY].get('rows', 0) > 0 and not force:
        log(f'{KEY} already cached with {man[KEY]["rows"]} rows; skipping '
            '(pass --force to overwrite with the per-provider pivot)')
        return
    base = f'https://data.cms.gov/provider-data/api/1/datastore/query/{DID}/0'
    prov = {}          # ccn -> pivoted record
    offset, pages, kept = 0, 0, 0
    total = None
    while pages < 4000:
        url = base + '?' + urllib.parse.urlencode({'limit': 500, 'offset': offset})
        d = get_json(url)
        if total is None:
            total = d.get('count')
            log(f'total rows reported: {total}')
        chunk = d.get('results', [])
        if not chunk:
            break
        for r in chunk:
            mc = r.get('measure_code')
            fld = FIELDS.get(mc)
            if fld is None:
                continue
            ccn = r.get(CCN_FIELD)
            rec = prov.get(ccn)
            if rec is None:
                rec = {'ccn': ccn}
                rec.update({dst: r.get(src) for src, dst in IDENT.items()})
                prov[ccn] = rec
            rec[fld] = r.get('score')
            # carry the measure window once (same for all rows)
            if 'start_date' not in rec and r.get('start_date') not in (None, '-'):
                rec['start_date'] = r.get('start_date')
                rec['end_date'] = r.get('end_date')
            kept += 1
        pages += 1
        if len(chunk) < 500:
            break
        offset += 500
        if pages % 100 == 0:
            log(f'  page {pages} offset {offset}: providers={len(prov)} kept_rows={kept}')
        time.sleep(0.1)
    out = sorted(prov.values(),
                 key=lambda x: (x.get('state') or '', x.get('ccn') or ''))
    record(man, KEY, out, {
        'dataset': 'CMS Provider Data Catalog: Skilled Nursing Facility '
                   'Quality Reporting Program - Provider Data',
        'dkan_id': DID, 'endpoint': base,
        'filters': {'client_side': 'kept measure_code in S_004_01_PPR_PD_* '
                    'and S_005_02_DTC_*, pivoted to one record per CCN'},
        'pages': pages, 'rows': len(out), 'kept_measure_rows': kept,
        'total_rows_scanned': total,
        'measure_fields': FIELDS})
    log(f'DONE pull16: {len(out)} providers, {kept} measure rows kept '
        f'from ~{total} scanned')


if __name__ == '__main__':
    main()
