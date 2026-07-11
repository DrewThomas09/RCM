"""v3.4 geography + facility-network pulls: ZCTA centroids, RUCA rurality
(tract + ZIP), CMS ambulance-fee-schedule ZIP rural/locality file, dialysis
facility roster, SNF QRP outcomes, hospital ED timeliness, Rural Emergency
Hospital conversions, Acute Hospital Care at Home list, Sheps rural closures.

Each stage retries 3x with backoff; a dead endpoint PARKs the stage with a
logged reason and the run continues.
"""
import csv
import html as html_mod
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from html.parser import HTMLParser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pull as pl  # noqa: E402
from pull import CACHE, OPENER, get_json, load_manifest, log, paged_dataapi  # noqa: E402

UA = 'Mozilla/5.0 (research data pull; contact: ast3801@gmail.com)'
PDC_API = 'https://data.cms.gov/provider-data/api/1'
STATUS = {}   # stage name -> ('landed', rows) | ('PARKED', reason)
MAN10 = os.path.join(CACHE, 'manifest10.json')


def load_manifest10():
    if os.path.exists(MAN10):
        return json.load(open(MAN10))
    return {}


def record(man, key, payload, meta):
    """Concurrency-safe record: pull8.py may be running with its own stale
    in-memory manifest, so every write here (a) lands in a pull10 sidecar
    manifest and (b) is merged into the main manifest by fresh read-modify-
    write instead of dumping our snapshot over other writers' keys. A final
    merge pass re-applies the sidecar once concurrent pulls have exited."""
    path = os.path.join(CACHE, key + '.json')
    json.dump(payload, open(path, 'w'))
    meta.update({'sha256': pl.sha(payload),
                 'retrieved_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
                 'file': os.path.basename(path)})
    man[key] = meta
    side = load_manifest10()
    side[key] = meta
    tmp = MAN10 + '.tmp'
    json.dump(side, open(tmp, 'w'), indent=1, sort_keys=True)
    os.replace(tmp, MAN10)
    cur = load_manifest()          # fresh read: keep other writers' new keys
    cur.update(side)
    pl.save_manifest(cur)
    log(f'  cached {key}: {meta.get("rows", "?")} rows sha={meta["sha256"][:12]}')


def get_ua(url, tries=3, timeout=180):
    """GET with a browser UA (cms.gov/ers.usda.gov/shepscenter 403 bare urllib)."""
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            with OPENER.open(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001 — retry any transport error
            last = e
            wait = 2 ** i
            log(f'  retry {i + 1} in {wait}s: {type(e).__name__}: {str(e)[:120]}')
            time.sleep(wait)
    raise RuntimeError(f'GET failed after {tries}: {url} :: {last}')


def park(stage, reason):
    STATUS[stage] = ('PARKED', reason)
    log(f'PARK {stage}: {reason}')


def landed(stage, rows):
    STATUS[stage] = ('landed', rows)


def xlsx_rows(data):
    """Yield tuples from every worksheet of an xlsx blob (data sheet varies)."""
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    for ws in wb.worksheets:
        for row in ws.iter_rows(values_only=True):
            yield row
    wb.close()


def header_index(row, *needles):
    """Column index whose header contains all needles (case-insensitive)."""
    for i, c in enumerate(row):
        lc = str(c or '').lower()
        if all(n.lower() in lc for n in needles):
            return i
    return None


def pdc_fetch(did, conditions=None, max_pages=800, sleep=0.12, limit=500):
    """Pager for the Provider Data Catalog datastore (limit>500 gets HTTP 400)."""
    rows, offset, pages = [], 0, 0
    while pages < max_pages:
        q = {'limit': limit, 'offset': offset}
        for j, (prop, op, val) in enumerate(conditions or []):
            q[f'conditions[{j}][property]'] = prop
            q[f'conditions[{j}][operator]'] = op
            q[f'conditions[{j}][value]'] = val
        url = f'{PDC_API}/datastore/query/{did}/0?' + urllib.parse.urlencode(q)
        chunk = json.loads(get_ua(url).decode()).get('results', [])
        rows.extend(chunk)
        pages += 1
        offset += len(chunk)
        if len(chunk) < limit:
            break
        time.sleep(sleep)
    return rows, pages


_PDC_ITEMS = None


def pdc_item(did):
    global _PDC_ITEMS
    if _PDC_ITEMS is None:
        _PDC_ITEMS = get_json(f'{PDC_API}/metastore/schemas/dataset/items')
    for it in _PDC_ITEMS:
        if it.get('identifier') == did:
            return it
    return {}


def pick(cols, *cands):
    """First column whose name contains any candidate substring, in order."""
    for cand in cands:
        for c in cols:
            if cand in c.lower():
                return c
    return None


class TableGrab(HTMLParser):
    """Collect all <table> contents as lists of row-cell text."""

    def __init__(self):
        super().__init__()
        self.tables, self._rows, self._cells, self._buf = [], None, None, None

    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            self._rows = []
        elif tag == 'tr' and self._rows is not None:
            self._cells = []
        elif tag in ('td', 'th') and self._cells is not None:
            self._buf = []

    def handle_endtag(self, tag):
        if tag in ('td', 'th') and self._buf is not None:
            self._cells.append(html_mod.unescape(' '.join(''.join(self._buf).split())))
            self._buf = None
        elif tag == 'tr' and self._cells is not None:
            self._rows.append(self._cells)
            self._cells = None
        elif tag == 'table' and self._rows is not None:
            self.tables.append(self._rows)
            self._rows = None

    def handle_data(self, data):
        if self._buf is not None:
            self._buf.append(data)


# ── stage 1: ZCTA gazetteer centroids ────────────────────────────────────────

GAZ_URLS = ['https://www2.census.gov/geo/docs/maps-data/data/gazetteer/'
            '2024_Gazetteer/2024_Gaz_zcta_national.zip',
            'https://www2.census.gov/geo/docs/maps-data/data/gazetteer/'
            '2023_Gazetteer/2023_Gaz_zcta_national.zip']


def pull_zcta_gazetteer(man):
    key = 'zcta_gazetteer'
    if key in man:
        landed(key, man[key]['rows'])
        return
    data = vintage = url_used = None
    for url in GAZ_URLS:
        try:
            log(f'gazetteer: {url}')
            data = get_ua(url, timeout=300)
            vintage = url.split('/')[-1][:4]
            url_used = url
            break
        except RuntimeError as e:
            log(f'  gazetteer vintage failed: {str(e)[:120]}')
    if data is None:
        park(key, 'both 2024 and 2023 gazetteer URLs failed')
        return
    zf = zipfile.ZipFile(io.BytesIO(data))
    member = next(n for n in zf.namelist() if n.lower().endswith('.txt'))
    text = zf.read(member).decode('utf-8', 'replace')
    lines = text.splitlines()
    hdr = [h.strip() for h in lines[0].split('\t')]
    gi, lat_i, lon_i = (hdr.index('GEOID'), hdr.index('INTPTLAT'),
                        hdr.index('INTPTLONG'))
    keep = []
    for line in lines[1:]:
        p = [c.strip() for c in line.split('\t')]
        if len(p) > max(gi, lat_i, lon_i) and p[gi]:
            keep.append({'zcta': p[gi], 'lat': p[lat_i], 'lon': p[lon_i]})
    record(man, key, keep, {
        'dataset': f'Census Bureau {vintage} Gazetteer Files - ZIP Code '
                   'Tabulation Areas (national)',
        'endpoint': url_used, 'filters': {'fields': 'GEOID, INTPTLAT, INTPTLONG'},
        'rows': len(keep),
        'note': 'internal-point (centroid) coordinates per ZCTA; member '
                f'{member} tab-delimited inside zip'})
    landed(key, len(keep))


# ── stage 2: USDA ERS RUCA codes (tract + ZIP approximation) ─────────────────

RUCA_ZIP_URLS = [
    'https://www.ers.usda.gov/sites/default/files/_laserfiche/DataFiles/53241/RUCA2010zipcode.xlsx?v=34773',
    'https://www.ers.usda.gov/webdocs/DataFiles/53241/RUCA2010zipcode.xlsx?v=',
]
RUCA_TRACT_URLS = [
    'https://www.ers.usda.gov/sites/default/files/_laserfiche/DataFiles/53241/ruca2010revised.xlsx?v=34773',
    'https://www.ers.usda.gov/webdocs/DataFiles/53241/ruca2010revised.xlsx?v=',
]


def _first_ok(urls, timeout=300):
    for u in urls:
        try:
            return get_ua(u, timeout=timeout), u
        except RuntimeError as e:
            log(f'  candidate failed: {u} :: {str(e)[:100]}')
    return None, None


def pull_ruca_codes(man):
    stage = 'ruca_codes'
    done_rows = 0
    # ZIP-level approximation
    if 'ruca_zip' in man:
        done_rows += man['ruca_zip']['rows']
    else:
        data, url = _first_ok(RUCA_ZIP_URLS)
        if data is None:
            park(stage, 'RUCA ZIP xlsx unreachable at ERS laserfiche + webdocs paths')
            return
        log(f'RUCA ZIP: parsing {len(data):,} bytes xlsx')
        keep, idx = [], None
        for row in xlsx_rows(data):
            if idx is None:
                zi = header_index(row, 'zip')
                r1 = header_index(row, 'ruca1')
                r2 = header_index(row, 'ruca2')
                if zi is not None and r1 is not None and r2 is not None:
                    idx = (zi, r1, r2)
                continue
            if len(row) <= max(idx):   # doc/notes sheets after the data sheet
                continue
            z = row[idx[0]]
            if z is None or row[idx[1]] is None:
                continue
            keep.append({'zip': str(z).zfill(5), 'ruca1': row[idx[1]],
                         'ruca2': row[idx[2]]})
        record(man, 'ruca_zip', keep, {
            'dataset': 'USDA ERS 2010 Rural-Urban Commuting Area Codes - '
                       'ZIP code file (approximation)',
            'endpoint': url, 'filters': {'fields': 'ZIP_CODE, RUCA1, RUCA2'},
            'rows': len(keep),
            'note': 'ERS crosswalk approximating tract-level RUCA to USPS ZIPs; '
                    'RUCA1=primary, RUCA2=secondary code'})
        done_rows += len(keep)
    # tract-level revised codes
    if 'ruca_tract' in man:
        done_rows += man['ruca_tract']['rows']
    else:
        data, url = _first_ok(RUCA_TRACT_URLS)
        if data is None:
            park(stage, 'RUCA tract xlsx unreachable (ZIP-level file landed)')
            return
        log(f'RUCA tract: parsing {len(data):,} bytes xlsx')
        keep, idx = [], None
        for row in xlsx_rows(data):
            if idx is None:
                fi = header_index(row, 'state-county-tract')
                r1 = header_index(row, 'primary ruca')
                r2 = header_index(row, 'secondary ruca')
                if fi is not None and r1 is not None and r2 is not None:
                    idx = (fi, r1, r2)
                continue
            if len(row) <= max(idx):
                continue
            f = row[idx[0]]
            if f is None or row[idx[1]] is None:
                continue
            keep.append({'fips': str(f).zfill(11), 'ruca1': row[idx[1]],
                         'ruca2': row[idx[2]]})
        record(man, 'ruca_tract', keep, {
            'dataset': 'USDA ERS 2010 Rural-Urban Commuting Area Codes - '
                       'census tract file (revised 7/3/2019)',
            'endpoint': url,
            'filters': {'fields': 'State-County-Tract FIPS, primary RUCA, '
                                  'secondary RUCA'},
            'rows': len(keep),
            'note': 'tract grain; 2010 tract geography'})
        done_rows += len(keep)
    landed(stage, done_rows)


# ── stage 3: CMS ambulance/carrier-locality ZIP file ─────────────────────────

FEE_SCHED_PAGE = 'https://www.cms.gov/medicare/payment/fee-schedules'
ZIP_CL_FALLBACK = ('https://www.cms.gov/files/zip/'
                   'zip-code-carrier-locality-file-updated-05-13-2026.zip')


def pull_cms_amb_zip(man):
    key = 'cms_amb_zip'
    if key in man:
        landed(key, man[key]['rows'])
        return
    url = ZIP_CL_FALLBACK
    try:
        page = get_ua(FEE_SCHED_PAGE).decode('utf-8', 'replace')
        m = re.search(r'href="(/files/zip/zip-code-carrier-locality[^"]+\.zip)"', page)
        if m:
            url = 'https://www.cms.gov' + m.group(1)
    except RuntimeError as e:
        log(f'  fee-schedules page scan failed, using fallback URL: {str(e)[:100]}')
    log(f'ZIP-to-carrier-locality: {url}')
    try:
        data = get_ua(url, timeout=300)
    except RuntimeError as e:
        park(key, f'carrier-locality zip download failed: {str(e)[:140]}')
        return
    zf = zipfile.ZipFile(io.BytesIO(data))
    member = next((n for n in zf.namelist()
                   if n.upper().startswith('ZIP5') and n.lower().endswith('.txt')), None)
    if member is None:
        park(key, f'no ZIP5 txt member in archive; members={zf.namelist()}')
        return
    keep = []
    # fixed-width per ZIP5lyout.txt: state 1-2, zip 3-7, carrier 8-12,
    # locality 13-14, rural indicator 15 (blank=urban, R=rural, B=super rural)
    for line in zf.read(member).decode('utf-8', 'replace').splitlines():
        if len(line) < 15:
            continue
        keep.append({'state': line[0:2], 'zip': line[2:7], 'carrier': line[7:12],
                     'locality': line[12:14], 'rural': line[14:15].strip()})
    record(man, key, keep, {
        'dataset': 'CMS Zip Code to Carrier Locality File (ambulance fee '
                   'schedule rural/super-rural ZIP designations)',
        'endpoint': url, 'filters': {'member': member, 'zip9_member': 'skipped (89 MB)'},
        'rows': len(keep),
        'note': "rural: ''=urban, 'R'=rural, 'B'=super rural (lowest-quartile "
                'rural); basis: 2010 RUCA + revised 2013 OMB delineations; '
                'same file is linked from the CMS Ambulance Fee Schedule page'})
    landed(key, len(keep))


# ── stage 4: dialysis facility roster (PDC) ──────────────────────────────────

def pull_dialysis_facilities(man):
    key = 'dialysis_facilities'
    if key in man:
        landed(key, man[key]['rows'])
        return
    did = '23ew-n7w9'
    log(f'PDC Dialysis Facility - Listing by Facility ({did})')
    rows, pages = pdc_fetch(did)
    if not rows:
        park(key, f'PDC datastore {did} returned no rows')
        return
    cols = list(rows[0].keys())
    fm = {'ccn': pick(cols, 'certification', 'ccn'),
          'name': pick(cols, 'facility_name', 'facility name'),
          'chain': pick(cols, 'chain'),
          'stations': pick(cols, 'stations'),
          'city': pick(cols, 'city'),
          'state': pick(cols, 'state'),
          'county': pick(cols, 'county'),
          'zip': pick(cols, 'zip')}
    slim = [{k: r.get(c) for k, c in fm.items() if c} for r in rows]
    it = pdc_item(did)
    record(man, key, slim, {
        'dataset': 'CMS Provider Data Catalog: Dialysis Facility - Listing by Facility',
        'dkan_id': did, 'endpoint': f'{PDC_API}/datastore/query/{did}/0',
        'filters': {}, 'pages': pages, 'rows': len(slim),
        'fields_kept': {k: c for k, c in fm.items() if c},
        'note': f"full Care Compare roster; PDC issued={it.get('issued')} "
                f"modified={it.get('modified')}"})
    landed(key, len(slim))


# ── stage 5: SNF QRP provider file (DTC + rehospitalization measures) ────────

def pull_snf_qrp(man):
    key = 'snf_qrp'
    if key in man:
        landed(key, man[key]['rows'])
        return
    did = 'fykj-qjee'
    log(f'PDC SNF QRP - Provider Data ({did})')
    probe, _ = pdc_fetch(did, max_pages=1)
    if not probe:
        park(key, f'PDC datastore {did} returned no rows')
        return
    cols = list(probe[0].keys())
    mcol = pick(cols, 'measure_code', 'measure code', 'measure')
    fm = {'ccn': pick(cols, 'certification', 'ccn'),
          'state': pick(cols, 'state'),
          'measure_code': mcol,
          'score': pick(cols, 'score')}
    rows, pages, mode = [], 0, 'server-side contains'
    for token in ('DTC', 'PPR'):
        try:
            part, p = pdc_fetch(did, conditions=[(mcol, 'contains', token)])
            if part and token.lower() not in str(part[0].get(mcol, '')).lower():
                raise RuntimeError('contains-filter returned non-matching rows')
            rows.extend(part)
            pages += p
        except RuntimeError as e:
            log(f'  server-side filter failed ({str(e)[:90]}); full scan fallback')
            rows, mode = None, 'client-side after full scan'
            break
    if rows is None:
        allrows, pages = pdc_fetch(did)
        rows = [r for r in allrows
                if 'DTC' in str(r.get(mcol, '')).upper()
                or 'PPR' in str(r.get(mcol, '')).upper()]
    slim = [{k: r.get(c) for k, c in fm.items() if c} for r in rows]
    it = pdc_item(did)
    record(man, key, slim, {
        'dataset': 'CMS Provider Data Catalog: Skilled Nursing Facility '
                   'Quality Reporting Program - Provider Data',
        'dkan_id': did, 'endpoint': f'{PDC_API}/datastore/query/{did}/0',
        'filters': {mcol: "contains 'DTC' or 'PPR'", 'mode': mode},
        'pages': pages, 'rows': len(slim),
        'fields_kept': {k: c for k, c in fm.items() if c},
        'note': 'slimmed to discharge-to-community (DTC) and potentially '
                'preventable readmission/rehospitalization (PPR) measures; '
                f"PDC issued={it.get('issued')} modified={it.get('modified')}"})
    landed(key, len(slim))


# ── stage 6: Timely & Effective Care - Hospital (ED/transfer measures) ───────

ED_EXACT = {'OP_1', 'OP_2', 'OP_3', 'OP_3B', 'OP_5'}


def _ed_measure(mid):
    u = str(mid or '').upper()
    return (u.startswith(('ED', 'OP_18', 'OP_22', 'OP_23')) or u in ED_EXACT)


def pull_timely_care(man):
    key = 'timely_care_2026'
    if key in man:
        landed(key, man[key]['rows'])
        return
    did = 'yv7e-xc69'
    log(f'PDC Timely and Effective Care - Hospital ({did})')
    rows, pages = pdc_fetch(did)
    if not rows:
        park(key, f'PDC datastore {did} returned no rows')
        return
    cols = list(rows[0].keys())
    fm = {'ccn': pick(cols, 'facility_id', 'facility id', 'ccn'),
          'state': pick(cols, 'state'),
          'measure_id': pick(cols, 'measure_id', 'measure id'),
          'score': pick(cols, 'score'),
          'start_date': pick(cols, 'start_date', 'start date'),
          'end_date': pick(cols, 'end_date', 'end date')}
    mid_col = fm['measure_id']
    kept_ids = sorted({str(r.get(mid_col)) for r in rows if _ed_measure(r.get(mid_col))})
    slim = [{k: r.get(c) for k, c in fm.items() if c}
            for r in rows if _ed_measure(r.get(mid_col))]
    it = pdc_item(did)
    record(man, key, slim, {
        'dataset': 'CMS Provider Data Catalog: Timely and Effective Care - Hospital',
        'dkan_id': did, 'endpoint': f'{PDC_API}/datastore/query/{did}/0',
        'filters': {'client_side': 'measure_id startswith ED/EDV/OP_18/OP_22/'
                                   'OP_23 or in OP_1/OP_2/OP_3/OP_3b/OP_5'},
        'pages': pages, 'rows': len(slim), 'rows_unfiltered': len(rows),
        'measure_ids_kept': kept_ids,
        'fields_kept': {k: c for k, c in fm.items() if c},
        'note': f"latest PDC vintage; issued={it.get('issued')} "
                f"modified={it.get('modified')}"})
    landed(key, len(slim))


# ── stage 7: Rural Emergency Hospital list ───────────────────────────────────

HE_UUID = 'f6f6505c-e8b0-4d57-b258-e2b94133aaf2'
REH_KEEP = ['ENROLLMENT ID', 'ENROLLMENT STATE', 'NPI', 'CCN',
            'ORGANIZATION NAME', 'DOING BUSINESS AS NAME', 'CITY', 'STATE',
            'ZIP CODE', 'PROVIDER TYPE TEXT', 'PRACTICE LOCATION TYPE',
            'REH CONVERSION DATE', 'CAH OR HOSPITAL CCN']


def pull_reh_list(man):
    stage = 'reh_list'
    total = 0
    if 'reh_list' in man:
        total += man['reh_list']['rows']
    else:
        log(f'Hospital Enrollments full scan for REH CONVERSION FLAG=Y ({HE_UUID})')
        rows, pages, base = paged_dataapi(HE_UUID)
        reh = [r for r in rows if (r.get('REH CONVERSION FLAG') or '').strip() == 'Y']
        if not reh:
            park(stage, f'Hospital Enrollments scan ({len(rows)} rows) found no '
                        'REH CONVERSION FLAG=Y rows')
            return
        slim = [{k: r.get(k) for k in REH_KEEP} for r in reh]
        record(man, 'reh_list', slim, {
            'dataset': 'CMS Hospital Enrollments (PECOS public enrollment file), '
                       'Rural Emergency Hospital conversions',
            'uuid': HE_UUID, 'endpoint': base,
            'filters': {'client_side': "REH CONVERSION FLAG == 'Y'"},
            'pages': pages, 'rows': len(slim), 'rows_scanned': len(rows),
            'note': 'REH CONVERSION DATE = effective date of REH status; '
                    'CAH OR HOSPITAL CCN = pre-conversion CCN; includes main '
                    'and practice-location rows per enrollment'})
        total += len(slim)
    # cross-check roster: PDC 'Rural Emergency Hospital Timely and Effective Care'
    if 'reh_pdc_roster' in man:
        total += man['reh_pdc_roster']['rows']
    else:
        did = '97xg-v3wv'
        try:
            rows, pages = pdc_fetch(did)
        except RuntimeError as e:
            log(f'  REH PDC roster failed (non-fatal): {str(e)[:100]}')
            rows = []
        if rows:
            cols = list(rows[0].keys())
            fid = pick(cols, 'facility_id', 'facility id', 'ccn')
            fm = {'ccn': fid, 'name': pick(cols, 'facility_name', 'facility name'),
                  'city': pick(cols, 'city'), 'state': pick(cols, 'state'),
                  'zip': pick(cols, 'zip')}
            seen, roster = set(), []
            for r in rows:
                if r.get(fid) in seen:
                    continue
                seen.add(r.get(fid))
                roster.append({k: r.get(c) for k, c in fm.items() if c})
            record(man, 'reh_pdc_roster', roster, {
                'dataset': 'CMS Provider Data Catalog: Rural Emergency Hospital '
                           'Timely and Effective Care - Hospital (deduped roster)',
                'dkan_id': did, 'endpoint': f'{PDC_API}/datastore/query/{did}/0',
                'filters': {'client_side': 'dedup by facility_id'},
                'pages': pages, 'rows': len(roster),
                'note': 'independent Care Compare REH roster used to cross-check '
                        'the enrollment-file REH list'})
            total += len(roster)
    landed(stage, total)


# ── stage 8: Acute Hospital Care at Home approved-waiver list ────────────────

AHCAH_URLS = [
    'https://qualitynet.cms.gov/acute-hospital-care-at-home',
    'https://qualitynet.cms.gov/acute-hospital-care-at-home/resources',
    'https://www.cms.gov/files/document/covid-acute-hospital-care-home-program-'
    'approved-list-hospitals.pdf',
]


def pull_ahcah_list(man):
    key = 'ahcah_list'
    if key in man:
        landed(key, man[key]['rows'])
        return
    tried = []
    for url in AHCAH_URLS:
        try:
            data = get_ua(url, timeout=120)
        except RuntimeError as e:
            tried.append(f'{url} -> {str(e)[:80]}')
            continue
        head = data[:1024]
        if head.startswith(b'%PDF'):
            tried.append(f'{url} -> PDF only ({len(data):,} bytes)')
            continue
        text = data.decode('utf-8', 'replace')
        grab = TableGrab()
        grab.feed(text)
        tables = [t for t in grab.tables if len(t) > 3]
        if not tables:
            marker = 'Angular SPA shell (app-root)' if 'app-root' in text \
                else f'no data table in {len(text):,} chars of HTML'
            tried.append(f'{url} -> {marker}')
            continue
        # a real server-rendered table landed
        rows = []
        hdr = [h.lower() for h in tables[0][0]]
        for cells in tables[0][1:]:
            rows.append(dict(zip(hdr, cells)))
        record(man, key, rows, {
            'dataset': 'CMS Acute Hospital Care at Home approved facilities',
            'endpoint': url, 'filters': {}, 'rows': len(rows),
            'note': 'parsed from server-rendered HTML table'})
        landed(key, len(rows))
        return
    park(key, 'no machine-readable list: qualitynet pages are a JS-only Angular '
              'SPA (content API gateway not present in the shipped bundle; '
              'homeHospital/search endpoint requires per-CCN POST), and the '
              'cms.gov list is a 2021 PDF snapshot. Tried: ' + ' | '.join(tried))


# ── stage 9: Sheps Center rural hospital closures ────────────────────────────

SHEPS_URL = ('https://www.shepscenter.unc.edu/programs-projects/rural-health/'
             'rural-hospital-closures/')


def pull_sheps_closures(man):
    key = 'sheps_closures'
    if key in man:
        landed(key, man[key]['rows'])
        return
    log('Sheps Center rural hospital closures page')
    try:
        text = get_ua(SHEPS_URL, timeout=180).decode('utf-8', 'replace')
    except RuntimeError as e:
        park(key, f'page fetch failed: {str(e)[:140]}')
        return
    grab = TableGrab()
    grab.feed(text)
    tables = [t for t in grab.tables if len(t) > 2]
    if not tables:
        park(key, 'no HTML tables in served page (likely moved behind JS); '
                  f'page was {len(text):,} chars')
        return
    out = []
    for ti, tbl in enumerate(tables):
        hdr = [h.strip().lower().replace(' ', '_') or f'col{i}'
               for i, h in enumerate(tbl[0])]
        for cells in tbl[1:]:
            row = dict(zip(hdr, cells))
            row['_table'] = ti
            out.append(row)
    record(man, key, out, {
        'dataset': 'UNC Sheps Center rural hospital closures list '
                   '(2005-present, complete + converted closures)',
        'endpoint': SHEPS_URL,
        'filters': {'tables_found': len(tables),
                    'headers': [t[0] for t in tables]},
        'rows': len(out),
        'note': 'server-rendered TablePress tables parsed from HTML; _table '
                'index distinguishes the tables as published (closure vs '
                'conversion status is carried in the table columns/headers)'})
    landed(key, len(out))


# ── driver ───────────────────────────────────────────────────────────────────

STAGES = [pull_zcta_gazetteer, pull_ruca_codes, pull_cms_amb_zip,
          pull_dialysis_facilities, pull_snf_qrp, pull_timely_care,
          pull_reh_list, pull_ahcah_list, pull_sheps_closures]

STAGE_KEY = {'pull_zcta_gazetteer': 'zcta_gazetteer', 'pull_ruca_codes': 'ruca_codes',
             'pull_cms_amb_zip': 'cms_amb_zip',
             'pull_dialysis_facilities': 'dialysis_facilities',
             'pull_snf_qrp': 'snf_qrp', 'pull_timely_care': 'timely_care_2026',
             'pull_reh_list': 'reh_list', 'pull_ahcah_list': 'ahcah_list',
             'pull_sheps_closures': 'sheps_closures'}


def main():
    man = load_manifest()
    man.update(load_manifest10())   # sidecar survives concurrent-writer clobbers
    only = sys.argv[1:] or None
    for stage in STAGES:
        if only and stage.__name__ not in only:
            continue
        log(f'=== {stage.__name__} ===')
        try:
            stage(man)
        except Exception as e:  # noqa: BLE001 — keep pulling other stages
            park(STAGE_KEY[stage.__name__], f'unhandled {type(e).__name__}: {e}')
    log('--- SUMMARY ---')
    for fn in STAGES:
        sk = STAGE_KEY[fn.__name__]
        st = STATUS.get(sk)
        if st is None:
            log(f'{sk}: not run')
        elif st[0] == 'landed':
            log(f'{sk}: landed ({st[1]} rows)')
        else:
            log(f'{sk}: PARKED ({st[1]})')
    log('ALL DONE 10')


if __name__ == '__main__':
    main()
