"""HCRIS hospital cost report raw extracts, form CMS-2552-10: Worksheet A
ambulance cost center (form line 95 family), fiscal-year files 2021-2023,
optionally extended to 2019-2020.

Source zips: https://downloads.cms.gov/files/hcris/HOSP10FY{year}.zip
(verified by HEAD 2026-07-11: HTTP/2 200, ~136-139 MB each; the http:// and
/Files/ variants 301/alias to the same object).

DISK HYGIENE (mandated): one fiscal-year zip at a time is downloaded into
SCRATCH/_hcris_tmp/, its CSV members are STREAM-read with zipfile (never
extracted), the harvest is cached, and the zip is DELETED before the next
year begins.

Per year-file:
  HOSP10_{yr}_RPT.CSV   headerless: col0 RPT_REC_NUM, col2 PRVDR_NUM (CCN),
                        col5 FY_BGN_DT, col6 FY_END_DT (sanity-checked)
  HOSP10_{yr}_NMRC.CSV  headerless: RPT_REC_NUM, WKSHT_CD, LINE_NUM,
                        CLMN_NUM, ITM_VAL_NUM
  HOSP10_{yr}_ALPHA.CSV headerless: RPT_REC_NUM, WKSHT_CD, LINE_NUM,
                        CLMN_NUM, ITM_ALPHNMRC_ITM_TXT

Ambulance line verification (handoff-mandated): before harvesting, every
distinct raw LINE_NUM string on WKSHT_CD='A000000' that parses to an int in
{95, 950} or 9000..9999 is counted (formats vary: '9500'/'09500'/'95'), and
the ALPHA cost-center label column (CLMN_NUM int 0) is scanned for labels
containing AMBUL. Harvest keeps int line 9500 (form line 95, pre-printed
'Ambulance Services') unconditionally and subscripted lines 9501-9599 ONLY
when that report's own ALPHA label for the line contains AMBUL. Columns
kept: CLMN_NUM int 100 (salaries), 200 (other), 300 (total, as filed).

Artifacts:
  hcris_amb_fy{year}        per year-file: per-report rows + filer CCN sets
  hcris_amb_cost_center     combined rows {ccn, fy_year, line, salaries,
                            other, total} (+ label, n_reports), deduped by
                            RPT_REC_NUM across year-files
  hcris_amb_filer_counts    distinct CCNs filing per fy_end year (union
                            across year-files) - the share denominator
"""
import csv
import io
import os
import re
import shutil
import sys
import time
import urllib.request
import zipfile
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pull import CACHE, OPENER, SCRATCH, load_manifest, log, record  # noqa: E402

TMP = os.path.join(SCRATCH, '_hcris_tmp')
os.makedirs(TMP, exist_ok=True)
URL = 'https://downloads.cms.gov/files/hcris/HOSP10FY{y}.zip'
DATE_RE = re.compile(r'^\d{2}/\d{2}/\d{4}$')


def download(url, dest, tries=4):
    """Stream a large zip to disk through the agent proxy (chunked)."""
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(
                url, headers={'User-Agent': 'rcm-mc-research/1.0'})
            with OPENER.open(req, timeout=300) as r, open(dest + '.part', 'wb') as f:
                total = 0
                t0 = time.time()
                while True:
                    b = r.read(1 << 20)
                    if not b:
                        break
                    f.write(b)
                    total += len(b)
            os.replace(dest + '.part', dest)
            log(f'  downloaded {total / 1e6:.1f} MB in {time.time() - t0:.0f}s')
            return total
        except Exception as e:  # noqa: BLE001 - retry any transport error
            last = e
            wait = 2 ** (i + 1)
            log(f'  download retry {i + 1} in {wait}s: {type(e).__name__}: {str(e)[:120]}')
            time.sleep(wait)
    raise RuntimeError(f'download failed after {tries}: {url} :: {last}')


def member(names, suffix):
    hits = [n for n in names if n.upper().replace('\\', '/').split('/')[-1].endswith(suffix.upper())]
    if len(hits) != 1:
        raise RuntimeError(f'expected exactly one *{suffix} member, got {hits} in {names}')
    return hits[0]


def stream_csv(zf, name):
    return csv.reader(io.TextIOWrapper(zf.open(name), encoding='latin-1', newline=''))


def process_year(man, y):
    key = f'hcris_amb_fy{y}'
    if key in man:
        log(f'FY{y}: already in manifest, skipping')
        return
    url = URL.format(y=y)
    zp = os.path.join(TMP, f'HOSP10FY{y}.zip')
    if not os.path.exists(zp):
        log(f'FY{y}: downloading {url}')
        download(url, zp)
    zsize = os.path.getsize(zp)
    zf = zipfile.ZipFile(zp)
    names = zf.namelist()
    log(f'FY{y}: members {names}')
    rpt_name = member(names, '_RPT.CSV')
    nmrc_name = member(names, '_NMRC.CSV')
    alpha_name = member(names, '_ALPHA.CSV')

    # ── RPT: report -> (CCN, fy_end year); filer CCNs per fy_end year ──
    rptmap = {}
    filers = {}
    bad_dates = 0
    for i, row in enumerate(stream_csv(zf, rpt_name)):
        if len(row) < 7:
            continue
        rec, ccn, bgn, end = row[0].strip(), row[2].strip(), row[5].strip(), row[6].strip()
        if i < 3:
            log(f'  RPT sample row {i}: rec={rec} ccn={ccn} bgn={bgn} end={end}')
        if not (DATE_RE.match(end) and DATE_RE.match(bgn)):
            bad_dates += 1
            continue
        fy = int(end[-4:])
        rptmap[rec] = (ccn, fy, bgn, end)
        filers.setdefault(fy, set()).add(ccn)
    if bad_dates > len(rptmap) * 0.05:
        raise RuntimeError(f'RPT positional layout suspect: {bad_dates} bad-date rows '
                           f'vs {len(rptmap)} parsed - inspect columns')
    log(f'FY{y}: RPT {len(rptmap)} reports, fy_end years '
        f'{ {k: len(v) for k, v in sorted(filers.items())} }, bad_dates={bad_dates}')

    # ── ALPHA: Worksheet A cost-center labels containing AMBUL ──
    amb_labels = {}            # (rec, line_int) -> label text (CLMN int 0 only)
    amb_label_counter = Counter()   # (line_5char, LABEL) -> n reports
    amb_label_cols = Counter()      # CLMN ints where AMBUL text appears on A000000
    for row in stream_csv(zf, alpha_name):
        if len(row) < 5 or row[1].strip() != 'A000000':
            continue
        txt = row[4]
        if 'AMBUL' not in txt.upper():
            continue
        try:
            li = int(row[2].strip())
            ci = int(row[3].strip())
        except ValueError:
            continue
        amb_label_cols[ci] += 1
        if ci != 0:
            continue
        amb_labels[(row[0].strip(), li)] = txt.strip()
        amb_label_counter[(f'{li:05d}', txt.strip().upper())] += 1
    log(f'FY{y}: ALPHA ambulance-labelled A rows: {sum(amb_label_counter.values())} '
        f'across {len(amb_label_counter)} distinct (line,label); clmn dist {dict(amb_label_cols)}')

    # ── NMRC: line-format diagnostics + 95xx harvest ──
    line_fmt = Counter()       # raw LINE_NUM strings, int in {95,950} or 9000..9999
    clmn_fmt = Counter()       # raw CLMN_NUM strings on harvested 95xx lines
    vals = {}                  # (rec, line_int) -> {col_int: value}
    n_a_rows = 0
    for row in stream_csv(zf, nmrc_name):
        if len(row) < 5 or row[1].strip() != 'A000000':
            continue
        n_a_rows += 1
        lraw = row[2].strip()
        try:
            li = int(lraw)
        except ValueError:
            continue
        if li in (95, 950) or 9000 <= li <= 9999:
            line_fmt[lraw] += 1
        if not 9500 <= li <= 9599:
            continue
        craw = row[3].strip()
        clmn_fmt[craw] += 1
        try:
            ci = int(craw)
        except ValueError:
            continue
        if ci not in (100, 200, 300):
            continue
        v = row[4].strip()
        if not v:
            continue
        try:
            fv = float(v)
        except ValueError:
            continue
        vals.setdefault((row[0].strip(), li), {})[ci] = fv
    fmt95 = {k: v for k, v in line_fmt.items() if int(k) in (95, 950)}
    log(f'FY{y}: NMRC A000000 rows {n_a_rows}; distinct 9xxx LINE_NUM formats '
        f'{dict(sorted(line_fmt.items()))}')
    log(f'FY{y}: ambiguous short forms (int 95/950): {fmt95 or "none"}; '
        f'95xx CLMN formats {dict(sorted(clmn_fmt.items()))}')

    # ── join + filter: 9500 always; 9501-9599 only with an AMBUL label ──
    rows = []
    excl_sub_nolabel = 0
    excl_no_rpt = 0
    for (rec, li), cols in sorted(vals.items()):
        label = amb_labels.get((rec, li))
        if li != 9500 and not label:
            excl_sub_nolabel += 1
            continue
        if rec not in rptmap:
            excl_no_rpt += 1
            continue
        ccn, fy, _, _ = rptmap[rec]
        rows.append({'rec': rec, 'ccn': ccn, 'fy_year': fy, 'line': f'{li:05d}',
                     'salaries': cols.get(100), 'other': cols.get(200),
                     'total': cols.get(300), 'label': label})
    log(f'FY{y}: harvested {len(rows)} report-line rows '
        f'({excl_sub_nolabel} 95xx-subscript rows dropped for non-ambulance/missing '
        f'label, {excl_no_rpt} without RPT join)')

    payload = {'rows': rows,
               'filers_by_fy_end_year': {str(k): sorted(v) for k, v in sorted(filers.items())}}
    record(man, key, payload, {
        'dataset': f'CMS HCRIS HOSP10 (form 2552-10) FY{y} raw extract',
        'endpoint': url, 'zip_bytes': zsize,
        'members': {'rpt': rpt_name, 'nmrc': nmrc_name, 'alpha': alpha_name},
        'rows': len(rows), 'reports_in_rpt': len(rptmap),
        'nmrc_a000000_rows': n_a_rows,
        'line_num_formats_9xxx': dict(sorted(line_fmt.items())),
        'short_form_95_950': fmt95,
        'clmn_formats_95xx': dict(sorted(clmn_fmt.items())),
        'ambulance_labels_observed': [
            {'line': ln, 'label': lb, 'n_reports': n}
            for (ln, lb), n in sorted(amb_label_counter.items(), key=lambda kv: -kv[1])[:40]],
        'harvest_rule': "line int 9500 (form line 95 'Ambulance Services') always; "
                        '9501-9599 only when the report\'s own ALPHA label (CLMN 0) '
                        'contains AMBUL; columns 100=salaries, 200=other, 300=total as filed',
        'excluded_95xx_subscripts_without_ambulance_label': excl_sub_nolabel})
    zf.close()
    os.remove(zp)
    log(f'FY{y}: zip deleted; tmp dir now {sorted(os.listdir(TMP))}')


def combine(man):
    """Rebuild combined artifacts from every hcris_amb_fy* key present."""
    years = sorted(int(k.rsplit('fy', 1)[1]) for k in man if k.startswith('hcris_amb_fy'))
    if not years:
        log('combine: no per-year artifacts yet')
        return
    import json
    seen_rec = {}
    filer_union = {}
    per_year_meta = {}
    for y in years:
        payload = json.load(open(os.path.join(CACHE, f'hcris_amb_fy{y}.json')))
        dup = 0
        for r in payload['rows']:
            k = (r['rec'], r['line'])
            if k in seen_rec:
                dup += 1
            seen_rec[k] = r          # newer year-file wins on the rare dup
        for fy, ccns in payload['filers_by_fy_end_year'].items():
            filer_union.setdefault(fy, set()).update(ccns)
        m = man[f'hcris_amb_fy{y}']
        per_year_meta[str(y)] = {
            'line_num_formats_9xxx': m['line_num_formats_9xxx'],
            'short_form_95_950': m['short_form_95_950'],
            'ambulance_labels_observed': m['ambulance_labels_observed'][:15],
            'rows': m['rows'], 'reports_in_rpt': m['reports_in_rpt']}
        if dup:
            log(f'combine: {dup} (rec,line) dups superseded by FY{y} file')
    agg = {}
    for r in seen_rec.values():
        k = (r['ccn'], r['fy_year'], r['line'])
        a = agg.setdefault(k, {'ccn': r['ccn'], 'fy_year': r['fy_year'],
                               'line': r['line'], 'salaries': None, 'other': None,
                               'total': None, 'label': r['label'], 'n_reports': 0})
        a['n_reports'] += 1
        for f in ('salaries', 'other', 'total'):
            if r[f] is not None:
                a[f] = (a[f] or 0.0) + r[f]
        if r['label']:
            a['label'] = r['label']
    rows = [agg[k] for k in sorted(agg)]
    lines_observed = sorted({r['line'] for r in rows})
    record(man, 'hcris_amb_cost_center', rows, {
        'dataset': 'CMS HCRIS HOSP10 (form 2552-10) Worksheet A ambulance cost center',
        'endpoint': URL.replace('{y}', '{year}'),
        'year_files': years, 'rows': len(rows),
        'grain': 'one row per (ccn, fy_end year, worksheet A line), summed across '
                 'multiple cost reports of the same hospital ending in the same year',
        'columns': {'salaries': 'CLMN 100 (salaries)', 'other': 'CLMN 200 (other)',
                    'total': 'CLMN 300 (total, as filed - not recomputed)'},
        'verified_lines': lines_observed,
        'verification_by_year_file': per_year_meta,
        'harvest_rule': "line int 9500 (form 2552-10 Worksheet A line 95 'Ambulance "
                        "Services') always; subscripts 9501-9599 only when the report's "
                        'own ALPHA cost-center label contains AMBUL',
        'coverage_note': 'HOSP10FY files are grouped by cost-report fiscal-year BEGIN '
                         'date; with year-files ' + str(years) + ' the earliest and '
                         'latest fy_end years are partially covered, and the newest '
                         'fy_end year is additionally incomplete due to filing lag'})
    record(man, 'hcris_amb_filer_counts',
           {fy: len(ccns) for fy, ccns in sorted(filer_union.items())}, {
               'dataset': 'CMS HCRIS HOSP10 distinct hospitals (CCNs) filing, by cost-report '
                          'fiscal-year END year - denominator for the ambulance share',
               'endpoint': URL.replace('{y}', '{year}'), 'year_files': years,
               'rows': len(filer_union),
               'note': 'union of distinct PRVDR_NUM across year-files per FY_END_DT year; '
                       'edge years are partial because year-files group by FY begin date'})


def main():
    man = load_manifest()
    years = [int(a) for a in sys.argv[1:]] or [2021, 2022, 2023]
    for y in years:
        log(f'=== HCRIS FY{y} ===')
        t0 = time.time()
        try:
            process_year(man, y)
        except Exception as e:  # noqa: BLE001 - keep pulling other years
            log(f'YEAR FAILED FY{y}: {type(e).__name__}: {e}')
        log(f'=== FY{y} done in {time.time() - t0:.0f}s; '
            f'disk free {shutil.disk_usage(SCRATCH).free / 1e9:.1f} GB ===')
    combine(man)
    log('ALL DONE')


if __name__ == '__main__':
    main()
