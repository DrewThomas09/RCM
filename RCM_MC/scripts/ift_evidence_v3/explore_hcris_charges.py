"""Run 6, 1C exploration: identify the HCRIS worksheet/column that carries the
ambulance cost-center TOTAL CHARGES and Medicare charges, so the charge pull
extracts the right cells (not guessed). Downloads FY2023 HOSP10, then for a
sample of CCNs that have a line-95 ambulance cost centre, dumps every (worksheet,
column) value on line 9500 so the charge cells can be identified empirically
against the known Worksheet A cost."""
import os, sys, zipfile
from collections import defaultdict, Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pull12, v3lib

Y = 2023
url = pull12.URL.format(y=Y)
zp = os.path.join(pull12.TMP, f'HOSP10FY{Y}.zip')
if not os.path.exists(zp):
    print(f'downloading {url}', flush=True)
    pull12.download(url, zp)
print(f'zip {os.path.getsize(zp)/1e6:.0f} MB', flush=True)
zf = zipfile.ZipFile(zp)
names = zf.namelist()
rpt = pull12.member(names, '_RPT.CSV')
nmrc = pull12.member(names, '_NMRC.CSV')

# sample CCNs with a known line-95 ambulance cost centre + their total cost
cc = v3lib.load_cache('ift_v3_cache', 'hcris_amb_fy2023')['rows']
cost_by_rec = {r['rec']: r['total'] for r in cc if r['line'] == '09500'}
sample_recs = set(list(cost_by_rec)[:20])
print(f'{len(cost_by_rec)} line-95 recs; sampling {len(sample_recs)}', flush=True)

# rec -> ccn
rec2ccn = {}
for row in pull12.stream_csv(zf, rpt):
    if len(row) >= 7:
        rec2ccn[row[0].strip()] = row[2].strip()

# NMRC: for sample recs, line 9500, all worksheets/columns
per_rec = defaultdict(dict)   # rec -> {(wksht,clmn): val}
wk_clmn_mag = defaultdict(list)  # (wksht,clmn) -> [vals] across sample
for row in pull12.stream_csv(zf, nmrc):
    if len(row) < 5:
        continue
    rec = row[0].strip()
    if rec not in sample_recs:
        continue
    try:
        li = int(row[2].strip())
    except ValueError:
        continue
    if not (9500 <= li <= 9599):
        continue
    wksht = row[1].strip(); clmn = row[3].strip()
    try:
        val = float(row[4].strip())
    except ValueError:
        continue
    per_rec[rec][(wksht, clmn, li)] = val
    wk_clmn_mag[(wksht, clmn)].append(val)

print('\n=== (worksheet, column) cells on line 95xx: count + median magnitude ===')
import statistics
for k in sorted(wk_clmn_mag, key=lambda k: -len(wk_clmn_mag[k])):
    vals = [v for v in wk_clmn_mag[k] if v]
    if not vals: continue
    med = statistics.median(vals)
    print(f'  {k[0]:10s} col {k[1]:>4s}: n={len(wk_clmn_mag[k]):3d} median={med:14,.0f}')

print('\n=== 3 sample CCNs: cost vs candidate charge cells ===')
for rec in list(sample_recs)[:3]:
    ccn = rec2ccn.get(rec, '?'); cost = cost_by_rec.get(rec)
    print(f'\nCCN {ccn} (rec {rec}) Worksheet-A total COST = {cost:,.0f}')
    for (wk, cl, li), v in sorted(per_rec[rec].items()):
        if v and wk != 'A000000':
            print(f'    {wk} col {cl} line {li}: {v:,.0f}')
