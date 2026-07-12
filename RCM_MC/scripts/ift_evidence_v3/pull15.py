"""Extension X-A.6: national ambulance-organization roster from NPPES bulk file.

Downloads the NPPES monthly full-replacement V2 zip to SCRATCH/_nppes_tmp/,
stream-reads the main npidata CSV from inside the zip (never extracted),
keeps Entity Type 2 rows carrying any NUCC 3416% ambulance taxonomy code
(341600000X general / 3416A0800X air / 3416L0300X land / 3416S0300X water,
family confirmed against nucc_taxonomy_260.csv), skips deactivated NPIs,
then deletes the zip. Fallback if the bulk download fails twice: NPPES API
paged by taxonomy_description=Ambulance per state (limit 200, skip cap 1000
=> hard ceiling 1200/state, recorded as a floor where hit).

Artifacts:
  nppes_ambulance_roster  - slim per-NPI rows
  nppes_roster_by_state   - {state: {registered, air}}
"""
import csv
import io
import os
import shutil
import sys
import time
import urllib.parse
import urllib.request
import zipfile

from pull import (CACHE, OPENER, SCRATCH, get_json, load_manifest, log,
                  record)

TMP = os.path.join(SCRATCH, '_nppes_tmp')
FILE_MONTH = 'June 2026'
ZIP_URL = ('https://download.cms.gov/nppes/'
           'NPPES_Data_Dissemination_June_2026_V2.zip')
ZIP_PATH = os.path.join(TMP, os.path.basename(ZIP_URL))

# NUCC 'Ambulance' classification = the full 3416 family (verified against
# nucc_taxonomy_260.csv, Grouping 'Transportation Services'):
TAX_FAMILY = {
    '341600000X': 'general',
    '3416A0800X': 'air',
    '3416L0300X': 'land',
    '3416S0300X': 'water',
}
AIR_CODE = '3416A0800X'


# ── bulk download (streamed, resumable, 2 attempts) ─────────────────────────

def download_zip():
    os.makedirs(TMP, exist_ok=True)
    for attempt in (1, 2):
        have = os.path.getsize(ZIP_PATH) if os.path.exists(ZIP_PATH) else 0
        req = urllib.request.Request(ZIP_URL)
        if have:
            req.add_header('Range', f'bytes={have}-')
            log(f'download attempt {attempt}: resuming at {have:,} bytes')
        else:
            log(f'download attempt {attempt}: starting from 0')
        try:
            with OPENER.open(req, timeout=180) as r:
                total = have + int(r.headers.get('Content-Length') or 0)
                mode = 'ab' if have and r.status == 206 else 'wb'
                if mode == 'wb':
                    have = 0
                done = have
                nxt = done + 100 * 2**20
                with open(ZIP_PATH, mode) as f:
                    while True:
                        chunk = r.read(1 << 20)
                        if not chunk:
                            break
                        f.write(chunk)
                        done += len(chunk)
                        if done >= nxt:
                            log(f'  {done / 2**20:,.0f} MiB / '
                                f'{total / 2**20:,.0f} MiB')
                            nxt += 100 * 2**20
            size = os.path.getsize(ZIP_PATH)
            log(f'download complete: {size:,} bytes')
            with zipfile.ZipFile(ZIP_PATH) as z:  # central-dir integrity check
                _ = z.namelist()
            return size
        except Exception as e:  # noqa: BLE001 — count as one failed attempt
            log(f'  attempt {attempt} FAILED: {type(e).__name__}: '
                f'{str(e)[:150]}')
            time.sleep(5)
    return None


# ── bulk parse ───────────────────────────────────────────────────────────────

def parse_roster_from_zip():
    with zipfile.ZipFile(ZIP_PATH) as z:
        cands = [i for i in z.infolist()
                 if i.filename.lower().startswith('npidata_pfile')
                 and 'fileheader' not in i.filename.lower()]
        if not cands:
            raise RuntimeError(f'no npidata_pfile in zip: {z.namelist()}')
        info = max(cands, key=lambda i: i.file_size)
        log(f'main CSV: {info.filename} ({info.file_size / 2**30:.2f} GiB '
            'uncompressed, streaming, no extract)')
        with z.open(info) as raw:
            txt = io.TextIOWrapper(raw, encoding='utf-8', errors='replace',
                                   newline='')
            rdr = csv.reader(txt)
            hdr = next(rdr)
            col = {name: i for i, name in enumerate(hdr)}

            def c(name):
                return col[name]

            i_npi = c('NPI')
            i_ent = c('Entity Type Code')
            i_org = c('Provider Organization Name (Legal Business Name)')
            i_oth = c('Provider Other Organization Name')
            i_otht = c('Provider Other Organization Name Type Code')
            i_city = c('Provider Business Practice Location Address City Name')
            i_st = c('Provider Business Practice Location Address State Name')
            i_zip = c('Provider Business Practice Location Address Postal Code')
            i_enum = c('Provider Enumeration Date')
            i_deact = c('NPI Deactivation Date')
            i_react = c('NPI Reactivation Date')
            i_tax = [c(f'Healthcare Provider Taxonomy Code_{k}')
                     for k in range(1, 16)]
            i_prim = [c(f'Healthcare Provider Primary Taxonomy Switch_{k}')
                      for k in range(1, 16)]

            rows, scanned, skipped_deact = [], 0, 0
            seen_codes = {}
            for r in rdr:
                scanned += 1
                if scanned % 1000000 == 0:
                    log(f'  scanned {scanned / 1e6:.0f}M rows, '
                        f'kept {len(rows):,}')
                if r[i_ent] != '2':
                    continue
                fam = [r[i] for i in i_tax if r[i].startswith('3416')]
                if not fam:
                    continue
                deact, react = r[i_deact].strip(), r[i_react].strip()
                if deact and not react:
                    skipped_deact += 1
                    continue
                for code in fam:
                    seen_codes[code] = seen_codes.get(code, 0) + 1
                prim = next((r[i_tax[k]] for k in range(15)
                             if r[i_prim[k]] == 'Y' and r[i_tax[k]]), None)
                if prim is None:
                    prim = fam[0]
                zp = r[i_zip].strip()
                rows.append({
                    'npi': r[i_npi],
                    'org_name': r[i_org].strip(),
                    'dba': r[i_oth].strip() or None,
                    'dba_type_code': r[i_otht].strip() or None,
                    'city': r[i_city].strip(),
                    'state': r[i_st].strip(),
                    'zip5': zp[:5],
                    'zip': zp,
                    'enumeration_date': r[i_enum].strip(),
                    'primary_taxonomy': prim,
                    'taxonomy_3416': fam,
                    'air': AIR_CODE in fam,
                })
    return rows, scanned, skipped_deact, seen_codes, info.filename


def pull_bulk(man):
    key = 'nppes_ambulance_roster'
    if key in man:
        log('roster already cached, skipping bulk pull')
        return True
    size = download_zip()
    if size is None:
        return False
    rows, scanned, skipped, seen, csvname = parse_roster_from_zip()
    log(f'kept {len(rows):,} of {scanned:,} scanned; '
        f'skipped {skipped} deactivated; codes seen {seen}')
    record(man, key, rows, {
        'dataset': 'NPPES Data Dissemination (monthly full replacement, V2)',
        'source_page': 'https://download.cms.gov/nppes/NPI_Files.html',
        'endpoint': ZIP_URL,
        'file_month': FILE_MONTH,
        'zip_bytes': size,
        'main_csv': csvname,
        'method': ('zip stream-read via python zipfile+csv, never extracted; '
                   'zip deleted after parse'),
        'filters': {'Entity Type Code': '2 (organization)',
                    'taxonomy': "any of 15 Healthcare Provider Taxonomy Code "
                                "columns startswith '3416'",
                    'deactivated': 'skipped when NPI Deactivation Date set '
                                   'and no NPI Reactivation Date'},
        'taxonomy_family_kept': TAX_FAMILY,
        'taxonomy_family_source': 'nucc_taxonomy_260.csv (NUCC v26.0), '
                                  "Classification 'Ambulance', full 3416%",
        'air_flag_code': AIR_CODE,
        'taxonomy_codes_observed': seen,
        'rows': len(rows),
        'rows_scanned': scanned,
        'rows_skipped_deactivated': skipped,
        'county_note': 'NPPES carries no county field; practice ZIP only '
                       '(county would need external ZIP->county crosswalk)',
    })
    return True


# ── API fallback ─────────────────────────────────────────────────────────────

STATES = ['AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'DC', 'FL', 'GA',
          'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD', 'MA',
          'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ', 'NM', 'NY',
          'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC', 'SD', 'TN', 'TX',
          'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY', 'PR', 'VI', 'GU', 'AS',
          'MP']


def pull_api_fallback(man):
    key = 'nppes_ambulance_roster'
    if key in man:
        return
    log('FALLBACK: NPPES API paged by taxonomy_description=Ambulance')
    base = 'https://npiregistry.cms.hhs.gov/api/'
    rows, capped, per_state = [], [], {}
    for st in STATES:
        got, skip = 0, 0
        while skip <= 1000:
            q = urllib.parse.urlencode({
                'version': '2.1', 'enumeration_type': 'NPI-2',
                'taxonomy_description': 'Ambulance', 'state': st,
                'limit': 200, 'skip': skip})
            data = get_json(base + '?' + q)
            res = data.get('results', [])
            for it in res:
                b = it.get('basic', {})
                addr = next((a for a in it.get('addresses', [])
                             if a.get('address_purpose') == 'LOCATION'),
                            {})
                taxs = it.get('taxonomies', [])
                fam = [t['code'] for t in taxs
                       if str(t.get('code', '')).startswith('3416')]
                if not fam:
                    continue
                if b.get('status') != 'A':
                    continue
                prim = next((t['code'] for t in taxs if t.get('primary')),
                            fam[0])
                zp = str(addr.get('postal_code', '')).strip()
                rows.append({
                    'npi': str(it.get('number')),
                    'org_name': b.get('organization_name', ''),
                    'dba': None, 'dba_type_code': None,
                    'city': addr.get('city', ''),
                    'state': addr.get('state', st),
                    'zip5': zp[:5], 'zip': zp,
                    'enumeration_date': b.get('enumeration_date', ''),
                    'primary_taxonomy': prim,
                    'taxonomy_3416': fam,
                    'air': AIR_CODE in fam,
                })
                got += 1
            if len(res) < 200:
                break
            skip += 200
            time.sleep(0.3)
        else:
            capped.append(st)
        per_state[st] = got
        log(f'  {st}: {got}{" (CAPPED at 1200 - floor)" if st in capped else ""}')
        time.sleep(0.2)
    record(man, key, rows, {
        'dataset': 'NPPES NPI Registry API v2.1 (bulk-download fallback)',
        'endpoint': base,
        'file_month': 'live API as of run date (bulk file unavailable)',
        'filters': {'enumeration_type': 'NPI-2',
                    'taxonomy_description': 'Ambulance', 'state': 'per state',
                    'client_side': "taxonomy code startswith '3416', "
                                   "status A only"},
        'taxonomy_family_kept': TAX_FAMILY,
        'air_flag_code': AIR_CODE,
        'rows': len(rows),
        'per_state_counts': per_state,
        'states_capped_at_1200': capped,
        'cap_note': 'API limit 200 with skip cap 1000 => max 1200 results '
                    'per state; capped states are FLOORS, not totals',
        'county_note': 'NPPES carries no county field; practice ZIP only',
    })


# ── by-state comparison artifact ─────────────────────────────────────────────

def pull_by_state(man):
    key = 'nppes_roster_by_state'
    if key in man:
        return
    import json
    roster = json.load(open(os.path.join(CACHE,
                                         'nppes_ambulance_roster.json')))
    by = {}
    for r in roster:
        st = r.get('state') or '(blank)'
        d = by.setdefault(st, {'registered': 0, 'air': 0})
        d['registered'] += 1
        if r.get('air'):
            d['air'] += 1
    src = man.get('nppes_ambulance_roster', {})
    record(man, key, by, {
        'dataset': 'derived: nppes_ambulance_roster grouped by practice state',
        'source_artifact': 'nppes_ambulance_roster',
        'source_file_month': src.get('file_month'),
        'source_sha256': src.get('sha256'),
        'rows': len(by),
        'total_registered': sum(v['registered'] for v in by.values()),
        'total_air': sum(v['air'] for v in by.values()),
        'air_definition': f'row carries {AIR_CODE} in any taxonomy slot',
    })


def cleanup():
    if os.path.exists(TMP):
        shutil.rmtree(TMP)
        log(f'deleted {TMP} (zip removed)')
    else:
        log('_nppes_tmp already absent')


def main():
    man = load_manifest()
    ok = pull_bulk(man)
    cleanup()
    if not ok:
        pull_api_fallback(man)
    pull_by_state(man)
    log('ALL DONE')


if __name__ == '__main__':
    main()
