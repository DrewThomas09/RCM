"""Pull 14: input-cost index + public-operator benchmarks (B.11 / B.12).

Stages:
  (a) eia_diesel_padd      EIA weekly on-highway diesel by PADD -> annual avgs
  (b) bls_input_series     BLS v2 timeseries (no key): PPI ambulance industry,
                           PPI diesel fuel, ECEC private total comp
  (c) edgar_operator_facts SEC companyfacts: DocGo (1822359), ModivCare
                           (1220754) annual revenues FY2019-2025
  (d) falck_annual_report  Falck.com investor pages -> latest annual report
                           PDF; revenue + ambulance segment lines; else PARK
  (e) cms_aif_history      CMS Pub 100-04 Ch.15 (clm104c15.pdf) AIF history
                           chart -> verify CY2014-CY2019 AIF re-carry
"""
import io
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request

SCRATCH = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRATCH)
from pull import (CACHE, OPENER, get, get_json, load_manifest, log,  # noqa: E402
                  record)

UA = 'rcm-mc-research/1.0 (ast3801@gmail.com)'


def get_h(url, headers=None, data=None, tries=4, timeout=90):
    """GET/POST with headers through the same proxied opener."""
    import time
    hdrs = {'User-Agent': UA}
    hdrs.update(headers or {})
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers=hdrs)
            with OPENER.open(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            last = e
            wait = 2 ** i
            log(f'  retry {i + 1} in {wait}s: {type(e).__name__}: {str(e)[:120]}')
            time.sleep(wait)
    raise RuntimeError(f'FETCH failed after {tries}: {url} :: {last}')


# ── (a) EIA weekly on-highway diesel by PADD ────────────────────────────────

def pull_eia_diesel(man):
    key = 'eia_diesel_padd'
    if key in man:
        return
    page_url = 'https://www.eia.gov/petroleum/gasdiesel/'
    log('EIA gasdiesel page probe')
    html = get_h(page_url).decode('utf-8', 'replace')
    links = re.findall(r'href="([^"]*psw18vw[^"]*\.xls[x]?)"', html, re.I)
    if not links:
        raise RuntimeError('no psw18vw* XLS link found on gasdiesel page')
    xls_url = urllib.parse.urljoin(page_url, links[0])
    log(f'  XLS: {xls_url}')
    raw = get_h(xls_url)
    log(f'  downloaded {len(raw)} bytes')

    import pandas as pd
    sheets = pd.read_excel(io.BytesIO(raw), sheet_name=None, header=None,
                           engine='xlrd')
    series = {}
    for sname, df in sheets.items():
        if not sname.lower().startswith('data'):
            continue
        # row with 'Sourcekey' in col 0, next row 'Date' + descriptions
        head = None
        for i in range(min(6, len(df))):
            if str(df.iat[i, 0]).strip().lower() == 'sourcekey':
                head = i
                break
        if head is None:
            continue
        keys = [str(v).strip() for v in df.iloc[head, 1:]]
        names = [str(v).strip() for v in df.iloc[head + 1, 1:]]
        data = df.iloc[head + 2:]
        dates = pd.to_datetime(data.iloc[:, 0], errors='coerce')
        for ci, (k, nm) in enumerate(zip(keys, names), start=1):
            if not k or k == 'nan':
                continue
            vals = pd.to_numeric(data.iloc[:, ci], errors='coerce')
            ok = dates.notna() & vals.notna()
            if not ok.any():
                continue
            yr = dates[ok].dt.year
            v = vals[ok]
            ann = v.groupby(yr).mean()
            nwk = v.groupby(yr).size()
            ent = series.setdefault(k, {'name': nm, 'annual_avg': {},
                                        'n_weeks': {},
                                        'last_week': None})
            for y in ann.index:
                if 2013 <= int(y) <= 2026:
                    ent['annual_avg'][str(int(y))] = round(float(ann[y]), 4)
                    ent['n_weeks'][str(int(y))] = int(nwk[y])
            lw = dates[ok].max()
            if ent['last_week'] is None or str(lw.date()) > ent['last_week']:
                ent['last_week'] = str(lw.date())
    diesel = {k: v for k, v in series.items()
              if k.upper().startswith('EMD_')}
    if not diesel:
        diesel = series  # fall back: cache whatever parsed, keyed
    record(man, key, {'xls_url': xls_url, 'series': diesel},
           {'dataset': 'EIA Weekly Retail On-Highway Diesel Prices '
                       '(psw18vw*, all areas)',
            'endpoint': xls_url, 'source_page': page_url,
            'rows': sum(len(v['annual_avg']) for v in diesel.values()),
            'filters': {'client_side': 'annual calendar-year means of weekly '
                                       'prices, 2013-2026 YTD, per sourcekey'},
            'n_series': len(diesel)})


# ── (b) BLS public timeseries v2, no key ────────────────────────────────────

BLS_SERIES = ['PCU621910621910',    # PPI industry: ambulance services
              'WPU0531',            # PPI commodity: diesel fuel
              'CMU2010000000000D']  # ECEC private industry, total comp $/hr


def _bls_post(series, y0, y1):
    body = json.dumps({'seriesid': series, 'startyear': str(y0),
                       'endyear': str(y1)}).encode()
    raw = get_h('https://api.bls.gov/publicAPI/v2/timeseries/data/',
                headers={'Content-Type': 'application/json'}, data=body)
    return json.loads(raw.decode())


def pull_bls_input(man):
    key = 'bls_input_series'
    if key in man:
        return
    # unregistered quota: 10-year span cap (a 2014-2026 ask is silently cut
    # to 2017-2026), so two windows; still just two POSTs of a 25/day quota
    log('BLS v2 timeseries POST (two windows: 2017-2026 + 2014-2016)')
    out, parked, messages = {}, [], []
    chunks = [_bls_post(BLS_SERIES, 2017, 2026),
              _bls_post(BLS_SERIES, 2014, 2016)]
    messages = sum((c.get('message', []) for c in chunks), [])
    log(f'  statuses={[c.get("status") for c in chunks]} msgs={messages[:3]}')
    for c in chunks:
        if c.get('status') != 'REQUEST_SUCCEEDED':
            continue
        for s in c.get('Results', {}).get('series', []):
            sid = s.get('seriesID')
            rows = s.get('data', [])
            ent = out.setdefault(sid, {'observations': []})
            ent['observations'] += [
                {'year': r.get('year'), 'period': r.get('period'),
                 'periodName': r.get('periodName'), 'value': r.get('value')}
                for r in rows]
    for sid in BLS_SERIES:
        if not out.get(sid, {}).get('observations'):
            parked.append(sid)
            out.pop(sid, None)
    # annual means client-side (M01-M12 for monthly, Q01-Q04 for quarterly)
    for sid, ent in out.items():
        ann = {}
        for ob in ent['observations']:
            p = ob['period']
            if p.startswith('M') and p != 'M13' or p.startswith('Q') and p != 'Q05':
                try:
                    ann.setdefault(ob['year'], []).append(float(ob['value']))
                except ValueError:
                    pass
        ent['annual_avg'] = {y: round(sum(v) / len(v), 3)
                             for y, v in sorted(ann.items())}
        ent['n_obs_by_year'] = {y: len(v) for y, v in sorted(ann.items())}
    if not out:
        log(f'  STAGE PARKED entirely: {parked}')
        return
    record(man, key, {'series': out, 'parked_series': parked,
                      'api_messages': messages},
           {'dataset': 'BLS public timeseries API v2 (unregistered): PPI '
                       'ambulance services industry, PPI diesel fuel, ECEC '
                       'private total compensation',
            'endpoint': 'https://api.bls.gov/publicAPI/v2/timeseries/data/',
            'filters': {'seriesid': BLS_SERIES, 'years': '2014-2026'},
            'rows': sum(len(v['observations']) for v in out.values()),
            'parked_series': parked})
    if parked:
        log(f'  PARKED series ids: {parked}')


# ── (c) EDGAR companyfacts: DocGo + ModivCare ───────────────────────────────

OPERATORS = {'docgo': ('1822359', 'DocGo Inc.'),
             'modivcare': ('1220754', 'ModivCare Inc.')}
REV_TAGS = ['Revenues', 'RevenueFromContractWithCustomerExcludingAssessedTax']


def _annual_revenues(facts):
    """FY duration revenue facts, FY2019-2025, one per fiscal year.

    Prefers 10-K rows; among duplicates keeps the latest-filed accession.
    """
    rows = {}
    gaap = facts.get('facts', {}).get('us-gaap', {})
    for tag in REV_TAGS:
        for u in gaap.get(tag, {}).get('units', {}).get('USD', []):
            fy_end = str(u.get('end', ''))[:4]
            start, end = u.get('start'), u.get('end')
            if not (start and end):
                continue
            try:
                from datetime import date
                d0 = date.fromisoformat(start)
                d1 = date.fromisoformat(end)
            except ValueError:
                continue
            if not 330 <= (d1 - d0).days <= 400:
                continue                      # annual duration only
            yr = int(fy_end)
            if not 2019 <= yr <= 2026:
                continue
            if str(u.get('form', '')) not in ('10-K', '10-K/A', '20-F'):
                continue
            cur = rows.get((yr, tag))
            if cur is None or str(u.get('filed', '')) > str(cur.get('filed', '')):
                rows[(yr, tag)] = {'fy_end': end, 'val': u.get('val'),
                                   'accn': u.get('accn'), 'form': u.get('form'),
                                   'filed': u.get('filed'), 'fy': u.get('fy'),
                                   'fp': u.get('fp'), 'frame': u.get('frame'),
                                   'tag': tag}
    # collapse tags: prefer RevenueFromContract..., else Revenues
    out = {}
    for (yr, tag), r in sorted(rows.items()):
        if yr not in out or tag == REV_TAGS[1]:
            out[yr] = r
    return out


def pull_edgar(man):
    key = 'edgar_operator_facts'
    if key in man:
        return
    payload = {}
    for slug, (cik, name) in OPERATORS.items():
        url = f'https://data.sec.gov/api/xbrl/companyfacts/CIK{int(cik):010d}.json'
        log(f'EDGAR companyfacts {name} ({cik})')
        facts = json.loads(get_h(url).decode())
        ann = _annual_revenues(facts)
        payload[slug] = {'cik': cik, 'entityName': facts.get('entityName'),
                         'endpoint': url,
                         'annual_revenues': {str(y): r for y, r in ann.items()}}
        # latest interim YTD revenue after the last annual row (10-Q), so a
        # missing FY (e.g. an unfiled 10-K) can be shown as PENDING with the
        # measured YTD figure named in the note
        latest = None
        gaap = facts.get('facts', {}).get('us-gaap', {})
        for tag in REV_TAGS:
            for u in gaap.get(tag, {}).get('units', {}).get('USD', []):
                if u.get('form') != '10-Q' or not (u.get('start') and u.get('end')):
                    continue
                from datetime import date
                try:
                    days = (date.fromisoformat(u['end'])
                            - date.fromisoformat(u['start'])).days
                except ValueError:
                    continue
                if days < 150:
                    continue                    # want YTD spans, not quarters
                if latest is None or (u['end'], days) > (latest['end'],
                                                         latest['days']):
                    latest = {'tag': tag, 'start': u['start'], 'end': u['end'],
                              'days': days, 'val': u.get('val'),
                              'accn': u.get('accn'), 'fy': u.get('fy'),
                              'fp': u.get('fp'), 'filed': u.get('filed')}
        payload[slug]['latest_interim_ytd'] = latest
        log(f'  {name}: FY revenue years {sorted(ann)}; latest interim '
            f'{latest["end"] if latest else None}')
    record(man, key, payload,
           {'dataset': 'SEC EDGAR XBRL companyfacts: DocGo (CIK 1822359), '
                       'ModivCare (CIK 1220754)',
            'endpoint': 'https://data.sec.gov/api/xbrl/companyfacts/'
                        'CIK{10digit}.json',
            'filters': {'tags': REV_TAGS, 'forms': '10-K family',
                        'duration': 'annual (330-400 days)',
                        'years': 'FY2019-FY2025'},
            'rows': sum(len(v['annual_revenues']) for v in payload.values())})


# ── (d) Falck annual report ─────────────────────────────────────────────────

FALCK_PDF = ('https://brandportal.falck.com/m/1861cbb053f46e04/original/'
             'Annual-Report-2025.pdf')
FALCK_PAGES = ['https://www.falck.com/about-us/financials/reports/',
               'https://www.falck.com/about-us/financials/',
               'https://www.falck.com/en/investor/']


def pull_falck(man):
    key = 'falck_annual_report'
    if key in man:
        return
    pdfs, page = [FALCK_PDF], 'direct (brandportal.falck.com, found via the '\
                               'falck.com financial-reports page)'
    # probe the financials pages too so the locator chain is on record; if
    # the direct link ever rots, the page scan takes over
    for p in FALCK_PAGES:
        try:
            html = get_h(p, tries=2, timeout=45).decode('utf-8', 'replace')
            hrefs = re.findall(r'href="([^"]+)"', html, re.I)
            found = [urllib.parse.urljoin(p, h) for h in hrefs
                     if re.search(r'annual[-_ ]?report', h, re.I)
                     and h.lower().endswith('.pdf')]
            if found:
                pdfs = found + pdfs
                page = p
            log(f'  falck page {p}: {len(found)} annual-report pdf links')
            break
        except Exception as e:  # noqa: BLE001
            log(f'  falck page miss {p}: {type(e).__name__}')
    pdf_url = pdfs[0]
    log(f'  Falck PDF: {pdf_url}')
    try:
        raw = get_h(pdf_url, tries=2, timeout=120)
    except Exception as e:  # noqa: BLE001
        log(f'  PARK falck_annual_report: PDF fetch failed {type(e).__name__} '
            f'URL {pdf_url}')
        return
    tmp = os.path.join(CACHE, '_falck_ar.pdf')
    open(tmp, 'wb').write(raw)
    txt = subprocess.run(['pdftotext', '-layout', tmp, '-'],
                         capture_output=True, text=True).stdout
    pages = txt.split('\f')
    hits = []
    pat = re.compile(r'revenue|ambulance', re.I)
    for i, ptxt in enumerate(pages, start=1):
        for line in ptxt.splitlines():
            if pat.search(line) and re.search(r'\d', line):
                s = ' '.join(line.split())
                if 8 < len(s) < 220:
                    hits.append({'page': i, 'line': s})
    record(man, key, {'source_page': page, 'pdf_url': pdf_url,
                      'n_pages': len(pages), 'revenue_ambulance_lines':
                      hits[:400]},
           {'dataset': 'Falck A/S annual report (investor site, latest '
                       'linked PDF)', 'endpoint': pdf_url,
            'source_page': page, 'rows': len(hits[:400]),
            'note': 'raw page-located lines mentioning revenue/ambulance; '
                    'figures must be read off with page locators before use'})


# ── (e) CMS AIF history (Pub 100-04 Ch.15 chart) ────────────────────────────

CLM15_URL = ('https://www.cms.gov/Regulations-and-Guidance/Guidance/Manuals/'
             'downloads/clm104c15.pdf')


def pull_aif_history(man):
    key = 'cms_aif_history'
    if key in man:
        return
    log('CMS Pub 100-04 Ch.15 (ambulance) manual PDF')
    raw = get_h(CLM15_URL, timeout=120)
    tmp = os.path.join(CACHE, '_clm104c15.pdf')
    open(tmp, 'wb').write(raw)
    txt = subprocess.run(['pdftotext', '-layout', tmp, '-'],
                         capture_output=True, text=True).stdout
    pages = txt.split('\f')
    aif = {}
    ctx_pages = []
    rowpat = re.compile(r'^\s*(?:CY\s*)?(20\d\d)\b(.*?)(-?\d+\.\d+)\s*%?\s*$')
    for i, ptxt in enumerate(pages, start=1):
        if 'inflation factor' not in ptxt.lower():
            continue
        ctx_pages.append(i)
        for line in ptxt.splitlines():
            m = rowpat.match(line)
            if m:
                yr, mid, val = m.group(1), m.group(2), m.group(3)
                # keep only chart-like rows: the trailing number is the AIF
                if len(mid) < 90:
                    aif.setdefault(yr, []).append(
                        {'page': i, 'line': ' '.join(line.split())[:160],
                         'trailing_value': val})
    record(man, key, {'url': CLM15_URL, 'pages_with_aif_mentions': ctx_pages,
                      'candidate_rows_by_year': aif},
           {'dataset': 'CMS Pub. 100-04 Medicare Claims Processing Manual, '
                       'Chapter 15 (Ambulance), AIF history chart',
            'endpoint': CLM15_URL, 'rows': sum(len(v) for v in aif.values()),
            'note': 'candidate chart rows; the AIF column is the trailing '
                    'percentage on each CY row'})


STAGES = [pull_eia_diesel, pull_bls_input, pull_edgar, pull_falck,
          pull_aif_history]


def main():
    man = load_manifest()
    only = sys.argv[1:] or None
    for stage in STAGES:
        if only and stage.__name__ not in only:
            continue
        log(f'=== {stage.__name__} ===')
        try:
            stage(man)
        except Exception as e:  # noqa: BLE001
            log(f'STAGE FAILED {stage.__name__}: {type(e).__name__}: {e}')
    log('ALL DONE 14')


if __name__ == '__main__':
    main()
