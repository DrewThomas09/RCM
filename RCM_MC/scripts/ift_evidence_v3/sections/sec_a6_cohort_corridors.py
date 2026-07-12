"""A.6: Cohort_Corridors - the research cohort's measured hospital corridors.

For each system in the research cohort of representative multi-hospital
health systems operating in the study footprint, selected for depth:
resolve its hospital CCNs by PRINTED name-match rules over two public
rosters (HCRIS cost-report panel, Care Compare hospitals), roll up its
CMS Hospital Service Area 2025 top-15 origin-ZIP corridors, convert
corridor cases into an implied transfer-demand line via the measured
HCUP transfer rate (green link to Acute_IFT_Series), and classify each
system's corridor volume covered / contested / open by ZIP co-location
with the subject-company estate's registered NPPES locations and the
resolved market-participant registrations.
"""

import collections
import csv
import gzip
import json
import os

SHEETS = [{'name': 'Cohort_Corridors',
           'question': 'Where do the research-cohort systems draw their '
                       'inpatients from, how much implied transfer demand '
                       'does that volume carry, and how much of it sits in '
                       'ZIPs where the subject company or any resolved '
                       'participant is registered?'}]

HCRIS_GZ = '/home/user/RCM/RCM_MC/rcm_mc/data/hcris.csv.gz'

COHORT_FRAME = ('research cohort of representative multi-hospital health '
                'systems operating in the study footprint, selected for depth')


def _norm(n):
    return (n or '').upper().replace('.', '').replace("'", '')


# (system, printed rule, confound, predicate(name_upper, state, city_upper))
RULES = [
    ('Cleveland Clinic',
     "name contains 'CLEVELAND CLINIC'",
     'Under-match: regional hospitals not carrying the brand string '
     '(Fairview, Hillcrest, Akron General, Marymount) are missed; the '
     'Florida hospitals match and are kept',
     lambda n, s, c: 'CLEVELAND CLINIC' in n),
    ('Inova',
     "name contains 'INOVA'",
     'Clean match on a distinctive brand; five VA acute hospitals',
     lambda n, s, c: 'INOVA' in n),
    ('CommonSpirit / CHI Health',
     "name contains 'CHI HEALTH' or 'COMMONSPIRIT'",
     'Footprint brand only: CommonSpirit facilities branded CHI Memorial, '
     'CHI St. * or Dignity Health elsewhere are deliberately missed; this '
     'is the NE/IA CHI Health division, not the national parent',
     lambda n, s, c: 'CHI HEALTH' in n or 'COMMONSPIRIT' in n),
    ('Nebraska Methodist',
     "(name contains 'METHODIST' and state = NE) or name contains "
     "'JENNIE EDMUNDSON'",
     "Methodist Women's Hospital may report under the flagship CCN; Iowa "
     "'METHODIST' names (UnityPoint hospitals) are excluded on purpose",
     lambda n, s, c: ('METHODIST' in n and s == 'NE')
     or 'JENNIE EDMUNDSON' in n),
    ('Premier Health (Dayton)',
     "state = OH and name contains 'MIAMI VALLEY HOSPITAL' or "
     "'UPPER VALLEY MEDICAL' or 'ATRIUM MEDICAL'",
     'The corporate brand never appears in facility names, so the rule '
     'lists the hospitals from the public system roster; renames would '
     'silently drop out',
     lambda n, s, c: s == 'OH' and ('MIAMI VALLEY HOSPITAL' in n
                                    or 'UPPER VALLEY MEDICAL' in n
                                    or 'ATRIUM MEDICAL' in n)),
    ("Saint Luke's Health System (Kansas City)",
     "name (periods and apostrophes stripped) contains 'ST LUKE' or "
     "'SAINT LUKE', state in (MO, KS), city not in (St. Louis, "
     'Chesterfield, Marion)',
     "The St. Louis-area St. Luke's is a DIFFERENT system (excluded by "
     'city); rural affiliates not named St. Luke\'s (Hedrick, Wright '
     'Memorial, Anderson County) are missed: net under-match',
     lambda n, s, c: ('ST LUKE' in _norm(n) or 'SAINT LUKE' in n)
     and s in ('MO', 'KS')
     and c not in ('ST. LOUIS', 'SAINT LOUIS', 'CHESTERFIELD', 'MARION')),
    ('Froedtert',
     "name contains 'FROEDTERT'",
     'ThedaCare hospitals (2024 combination) do not carry the string and '
     'are missed; the legacy three-hospital core matches',
     lambda n, s, c: 'FROEDTERT' in n),
    ('Baptist Health (KY/IN)',
     "name contains 'BAPTIST HEALTH' and state in (KY, IN)",
     'State filter keeps the KY/IN system per its public roster and '
     'excludes the unrelated Baptist systems of other states; the Corbin '
     'CCH unit matches the string and rides along',
     lambda n, s, c: 'BAPTIST HEALTH' in n and s in ('KY', 'IN')),
    ('Ascension',
     "name contains 'ASCENSION'",
     'Hospitals not yet renamed to the Ascension brand are missed and '
     'recently divested hospitals may persist in older roster rows',
     lambda n, s, c: 'ASCENSION' in n),
]


def _load_rosters(lib, cache):
    """Latest-year HCRIS row per CCN + Care Compare roster per CCN."""
    hcris = {}
    with gzip.open(HCRIS_GZ, 'rt') as f:
        for row in csv.DictReader(f):
            k = row['ccn']
            if k not in hcris or row['fiscal_year'] > hcris[k]['fy']:
                hcris[k] = {'fy': row['fiscal_year'],
                            'name': (row['name'] or '').upper(),
                            'state': row['state'],
                            'city': (row['city'] or '').upper()}
    pdc = {}
    for r in lib.load_cache(cache, 'pdc2_hospitals'):
        pdc[r['facility_id']] = {
            'name': (r.get('facility_name') or '').upper(),
            'state': r.get('state'),
            'city': (r.get('citytown') or '').upper()}
    return hcris, pdc


def _find_rate_cell(wb):
    """Scan Acute_IFT_Series for the measured transfer-rate cell: a
    share-formatted col-B value beside an 'IFT % of admissions' label,
    preferring the clean-window mean. Returns (cell, label) or (None, None)."""
    if 'Acute_IFT_Series' not in wb.sheetnames:
        return None, None
    ws = wb['Acute_IFT_Series']
    cands = []
    for row in ws.iter_rows(min_col=1, max_col=2):
        a, b = row[0], row[1]
        if not isinstance(a.value, str):
            continue
        t = a.value.lower()
        if 'ift % of admissions' not in t and 'ift as % of admissions' not in t:
            continue
        if b.value is None or '%' not in (b.number_format or ''):
            continue
        cands.append((0 if 'mean' in t else 1, a.row, a.value))
    if not cands:
        return None, None
    cands.sort()
    _, r, label = cands[0]
    return f'B{r}', label


def build(wb, ctx):
    lib = ctx['lib']
    cache = ctx['cache']
    scratch = os.path.dirname(cache)
    accessed = ctx['accessed']
    facts, sources, excluded, findings = [], [], [], []

    # ---------------------------------------------------------------- data
    corr = lib.load_cache(cache, 'hsa_2025_corridors_top15')
    by_ccn = collections.defaultdict(list)
    for r in corr:
        by_ccn[r['provider_id']].append(r)
    hcris, pdc = _load_rosters(lib, cache)

    sys_ccns, rule_meta = {}, {}
    for name, rule, confound, pred in RULES:
        hits = set()
        for src in (hcris, pdc):
            for ccn, d in src.items():
                if pred(d['name'], d['state'], d['city']):
                    hits.add(ccn)
        sys_ccns[name] = hits
        rule_meta[name] = (rule, confound)

    # subject-company estate registered ZIPs (NPPES pulls, estate_addresses)
    est = json.load(open(os.path.join(scratch, 'estate_addresses.json')))
    est_zip_info = {}          # zip5 -> {'cities': set, 'npis': set}
    for v in est.values():
        locs = ([v['location']] if v.get('location') else []) \
            + (v.get('practice_locations') or [])
        for a in locs:
            z = (a.get('postal_code') or '')[:5]
            if not z:
                continue
            d = est_zip_info.setdefault(z, {'cities': set(), 'npis': set()})
            d['cities'].add(f"{(a.get('city') or '').title()}, "
                            f"{a.get('state') or ''}")
            d['npis'].add(v['npi'])
    est_zips = set(est_zip_info)

    # resolved market participants: best-NPI hits from the NPPES crosswalk
    xwalk = json.load(open(os.path.join(scratch, 'nppes_crosswalk.json')))
    best = {q: set(v.get('best_npis') or []) for q, v in xwalk.items()}
    part = lib.load_cache(cache, 'nppes_participant_resolution')
    part_zip_who = collections.defaultdict(set)   # zip5 -> {query names}
    part_npis = set()
    for rec in part:
        q = rec.get('query')
        for h in rec.get('hits', []):
            if h.get('npi') in best.get(q, set()) and h.get('zip'):
                part_zip_who[h['zip'][:5]].add(q)
                part_npis.add(h['npi'])
    part_zips = set(part_zip_who)
    n_resolved_queries = sum(1 for q, s in best.items() if s)

    # per-system corridor roll-up + ZIP aggregation + coverage split
    agg = {}
    for name in sys_ccns:
        in_corr = sorted(c for c in sys_ccns[name] if c in by_ccn)
        rows = [r for c in in_corr for r in by_ccn[c]]
        zipagg = collections.Counter()
        for r in rows:
            zipagg[r['zip']] += r['cases']
        cases = sum(zipagg.values())
        cov = sum(v for z, v in zipagg.items() if z in est_zips)
        con = sum(v for z, v in zipagg.items()
                  if z not in est_zips and z in part_zips)
        agg[name] = {
            'in_corr': in_corr,
            'cases': cases,
            'days': sum(r['days'] for r in rows),
            'charges': sum(r['charges'] for r in rows),
            'zipagg': zipagg,
            'cov': cov, 'con': con, 'open': cases - cov - con}
    order = sorted(agg, key=lambda k: -agg[k]['cases'])
    tot_cases = sum(a['cases'] for a in agg.values())
    tot_cov = sum(a['cov'] for a in agg.values())
    tot_con = sum(a['con'] for a in agg.values())
    tot_open = sum(a['open'] for a in agg.values())
    top_sys = order[0]

    rate_cell, rate_label = _find_rate_cell(wb)

    # ------------------------------------------------------------- sources
    sources += [
        {'key': 'cohort_hsa_corridors', 'publisher': 'CMS',
         'document': 'Hospital Service Area file, 2025 release - top-15 '
                     'origin-ZIP corridor extract per hospital CCN '
                     '(cache hsa_2025_corridors_top15; full grain carried '
                     'on HSA_Corridors)',
         'vintage': '2025 (Medicare FFS inpatient claims)',
         'locator': 'Rows where provider_id is a CCN matched to a cohort '
                    'system by the printed rules of Panel A',
         'supplies': 'Corridor cases, inpatient days and charges by origin '
                     'ZIP for every cohort-system hospital',
         'url': 'https://data.cms.gov/summary-statistics-on-use-and-'
                'payments/medicare-service-type-reports/'
                'hospital-service-area',
         'tier': 'A', 'accessed': accessed, 'powers': ['Cohort_Corridors']},
        {'key': 'cohort_hcris_roster', 'publisher': 'CMS (HCRIS)',
         'document': 'Hospital cost report (HCRIS) panel, vendored extract '
                     'rcm_mc/data/hcris.csv.gz - ccn, name, city, state, '
                     'latest filed year per CCN (FY2020-FY2022)',
         'vintage': 'FY2020-FY2022 cost reports',
         'locator': 'Latest fiscal-year row per CCN; names uppercased for '
                    'the Panel A match rules',
         'supplies': 'Hospital legal/roster names for CCN name-matching',
         'url': 'https://www.cms.gov/data-research/statistics-trends-'
                'reports/cost-reports',
         'tier': 'A', 'accessed': accessed, 'powers': ['Cohort_Corridors']},
        {'key': 'cohort_pdc_roster', 'publisher': 'CMS (Provider Data '
         'Catalog)',
         'document': 'Care Compare - Hospital General Information roster '
                     '(cache pdc2_hospitals): facility_id, facility_name, '
                     'city, state',
         'vintage': '2026 roster',
         'locator': 'facility_id joined as CCN; names uppercased for the '
                    'Panel A match rules',
         'supplies': 'Current consumer-facing hospital names (catches '
                     'renames the cost-report panel misses)',
         'url': 'https://data.cms.gov/provider-data/dataset/xubh-q36u',
         'tier': 'A', 'accessed': accessed, 'powers': ['Cohort_Corridors']},
        {'key': 'cohort_nppes_locations', 'publisher': 'CMS (NPPES API)',
         'document': 'NPPES registry API pulls: practice locations of the '
                     '23 subject-company estate NPIs (estate_addresses.json,'
                     ' pulled 11 Jul 2026) and the resolved market-'
                     'participant NPIs (cache '
                     'nppes_participant_resolution + nppes_crosswalk best '
                     'NPIs)',
         'vintage': 'NPPES live registry, Jul 2026',
         'locator': 'address_purpose=LOCATION plus secondary practice '
                    'locations; ZIP truncated to 5 digits for the corridor '
                    'join',
         'supplies': 'Registered ZIP-cities used to classify corridor '
                     'volume covered / contested / open',
         'url': 'https://npiregistry.cms.hhs.gov/api/',
         'tier': 'A', 'accessed': accessed, 'powers': ['Cohort_Corridors']},
    ]

    # ----------------------------------------------------------------- tab
    ws = wb.create_sheet('Cohort_Corridors')
    sb = lib.SheetBuilder(ws, 10,
                          col_widths=[30, 13, 12, 14, 13, 15, 12, 15, 40, 40],
                          tab_color='FF1F6F8B')
    sb.title('Cohort corridors: where the research-cohort systems draw '
             'their inpatients, and who is registered there')
    sb.subtitle('The question: where do the cohort systems draw their '
                'inpatient volume, how much implied transfer demand rides '
                'on it, and how much of that corridor volume sits in ZIPs '
                'where the subject company or any resolved market '
                'participant holds a registered location? Group studied: a '
                + COHORT_FRAME + '. Sources and join keys: CMS Hospital '
                'Service Area 2025 (CCN x origin ZIP), hospital CCNs '
                'resolved by the PRINTED name-match rules of Panel A over '
                'the HCRIS cost-report panel and the Care Compare roster, '
                'registered locations from NPPES (23 estate NPIs pulled 11 '
                'Jul 2026; participant NPIs from the resolved crosswalk), '
                'joined on 5-digit ZIP.', height=56)
    sb.note('DATA QUALITY: corridors are MEDICARE FFS INPATIENT stays only '
            '(no MA, Medicaid or commercial volume) and each hospital is '
            'truncated to its top-15 origin ZIPs, so every volume is a '
            'floor; CMS suppresses cells under 11 cases at source; '
            'name-match rules over- and under-match as stated per row in '
            'Panel A (a confound, not a blocker); an NPPES registered '
            'location is a billing/practice registration, NOT a station or '
            'service area, so ZIP co-location is a presence marker and the '
            'covered/contested split understates true operating coverage.',
            height=44)
    sb.blank()

    # Panel A - printed rules
    sb.banner('Panel A. Cohort resolution: the printed name-match rules '
              '(applied to uppercased names in both public rosters)')
    sb.headers(['System', 'CCNs matched (roster union)', 'In corridor file',
                '', '', '', '', '', 'Printed match rule',
                'Confound (stated, not blocking)'])
    for name in order:
        rule, confound = rule_meta[name]
        sb.row([(name, 'label'),
                (len(sys_ccns[name]), 'src', lib.FMT_INT),
                (len(agg[name]['in_corr']), 'src', lib.FMT_INT),
                None, None, None, None, None,
                (rule, 'text'), (confound, 'note')], wrap=True, height=34)
    sb.note('CCNs matched = distinct CCNs where either roster name passes '
            'the rule. In corridor file = those CCNs present in the HSA '
            '2025 top-15 extract (rehab/childrens units and new CCNs can '
            'be absent). Match counts are printed so any rule can be '
            're-run and challenged.')
    sb.blank()

    # Panel B - corridor roll-up + implied transfer demand
    sb.banner('Panel B. System corridor roll-up (HSA 2025 top-15 rows) and '
              'the implied transfer-demand line')
    if rate_cell:
        rrow = sb.r + 1
        sb.row([('Measured transfer rate (green link)', 'label'),
                (f"='Acute_IFT_Series'!{rate_cell}", 'link', lib.FMT_PCT2),
                None, None, None, None, None, None,
                (f'Located by scan: share-formatted cell beside the label '
                 f'"{rate_label}" on Acute_IFT_Series (cell {rate_cell})',
                 'note'),
                ('HCUP all-payer IFT per admission applied to Medicare FFS '
                 'corridor cases: cross-payer, directional only', 'note')],
               wrap=True, height=30)
        rate_ref = f'$B${rrow}'
    else:
        sb.row([('Measured transfer rate', 'label'), ('PENDING', 'note'),
                None, None, None, None, None, None,
                ('Cell needed: the mean IFT % of admissions cell on '
                 'Acute_IFT_Series (B37 in the v3.3 build)', 'note'), None])
        rate_ref = None
    sb.headers(['System', 'Hospitals in corridor file',
                'Corridor cases (floor)', 'Inpatient days', 'Charges $',
                'Share of cohort cases',
                'Implied transfer episodes (cases x linked rate)', '',
                'Note', ''])
    b0 = sb.r + 1
    tot_rn = b0 + len(order)
    for i, name in enumerate(order):
        a = agg[name]
        rn = b0 + i
        sb.row([(name, 'label'),
                (len(a['in_corr']), 'src', lib.FMT_INT),
                (round(a['cases']), 'src', lib.FMT_INT),
                (round(a['days']), 'src', lib.FMT_INT),
                (round(a['charges']), 'src', lib.FMT_USD),
                (f'=IF(C${tot_rn}=0,"n/a",C{rn}/C${tot_rn})', 'fml',
                 lib.FMT_PCT1),
                (f"=C{rn}*'Acute_IFT_Series'!{rate_cell.replace('B', '$B$')}",
                 'link', lib.FMT_INT) if rate_cell
                else ('PENDING', 'note'),
                None,
                ('Medicare FFS inpatient stays over top-15 origin ZIPs '
                 'only: a floor of the system\'s true draw', 'note')
                if i == 0 else None, None])
    sb.row([('Research cohort total', 'label'),
            (f'=SUM(B{b0}:B{tot_rn - 1})', 'fml', lib.FMT_INT),
            (f'=SUM(C{b0}:C{tot_rn - 1})', 'fml', lib.FMT_INT),
            (f'=SUM(D{b0}:D{tot_rn - 1})', 'fml', lib.FMT_INT),
            (f'=SUM(E{b0}:E{tot_rn - 1})', 'fml', lib.FMT_USD),
            (f'=IF(C{tot_rn}=0,"n/a",1)', 'fml', lib.FMT_PCT1),
            (f'=SUM(G{b0}:G{tot_rn - 1})', 'fml', lib.FMT_INT)
            if rate_cell else ('PENDING', 'note'),
            None, None, None])
    sb.blank()

    # Panel C - covered / contested / open
    sb.banner('Panel C. Corridor volume by registration status: covered '
              '(estate ZIP) / contested (participant ZIP) / open (neither)')
    sb.headers(['System', 'Covered cases (estate ZIP present)',
                'Contested cases (participant ZIP, no estate)',
                'Open cases (neither)', 'Total (live)', 'Covered share',
                'Contested share', 'Open share', 'Note', ''])
    c0 = sb.r + 1
    ctot = c0 + len(order)
    for i, name in enumerate(order):
        a = agg[name]
        rn = c0 + i
        sb.row([(name, 'label'),
                (round(a['cov']), 'src', lib.FMT_INT),
                (round(a['con']), 'src', lib.FMT_INT),
                (round(a['open']), 'src', lib.FMT_INT),
                (f'=B{rn}+C{rn}+D{rn}', 'fml', lib.FMT_INT),
                (f'=IF(E{rn}=0,"n/a",B{rn}/E{rn})', 'fml', lib.FMT_PCT1),
                (f'=IF(E{rn}=0,"n/a",C{rn}/E{rn})', 'fml', lib.FMT_PCT1),
                (f'=IF(E{rn}=0,"n/a",D{rn}/E{rn})', 'fml', lib.FMT_PCT1),
                ('precedence: a ZIP with both estate and participant '
                 'registrations counts as covered', 'note')
                if i == 0 else None, None])
    sb.row([('Research cohort total', 'label'),
            (f'=SUM(B{c0}:B{ctot - 1})', 'fml', lib.FMT_INT),
            (f'=SUM(C{c0}:C{ctot - 1})', 'fml', lib.FMT_INT),
            (f'=SUM(D{c0}:D{ctot - 1})', 'fml', lib.FMT_INT),
            (f'=B{ctot}+C{ctot}+D{ctot}', 'fml', lib.FMT_INT),
            (f'=IF(E{ctot}=0,"n/a",B{ctot}/E{ctot})', 'fml', lib.FMT_PCT1),
            (f'=IF(E{ctot}=0,"n/a",C{ctot}/E{ctot})', 'fml', lib.FMT_PCT1),
            (f'=IF(E{ctot}=0,"n/a",D{ctot}/E{ctot})', 'fml', lib.FMT_PCT1),
            None, None])
    sb.note('Status is a REGISTRATION overlay, not market share: covered '
            'means at least one of the 23 estate NPIs registers a practice '
            'location in that 5-digit ZIP; contested means a resolved '
            'participant NPI does and no estate NPI does; open means '
            'neither. Ambulance services operate across ZIPs from few '
            'stations, so all three shares mismeasure operations in the '
            'same direction: registered footprints understate reach.')
    sb.blank()

    # Panel D - top-15 origin ZIPs per system
    sb.banner('Panel D. Top-15 origin ZIPs per system (cases aggregated '
              'over the system\'s hospitals; system-level rank)')
    sb.headers(['System', 'Rank', 'Origin ZIP', 'Corridor cases',
                'Share of system cases', 'Status', 'Registered there', '',
                'Note', ''])
    first = True
    for name in order:
        a = agg[name]
        sys_rn = b0 + order.index(name)
        for rank, (z, v) in enumerate(a['zipagg'].most_common(15), 1):
            if z in est_zips:
                status = 'Covered'
                who = 'estate NPI: ' + '; '.join(
                    sorted(est_zip_info[z]['cities'])[:2])
            elif z in part_zips:
                status = 'Contested'
                who = 'participant: ' + '; '.join(
                    sorted(part_zip_who[z])[:2])
            else:
                status, who = 'Open', '-'
            rn = sb.r + 1
            sb.row([(name, 'text'), (rank, 'src', lib.FMT_INT),
                    (z, 'src'), (round(v), 'src', lib.FMT_INT),
                    (f'=IF(C${sys_rn}=0,"n/a",D{rn}/C${sys_rn})', 'fml',
                     lib.FMT_PCT1),
                    (status, 'src'), (who, 'note'), None,
                    ('share denominators link to Panel B system rows',
                     'note') if first else None, None])
            first = False
    sb.blank()

    # Panel E - the registration base
    sb.banner('Panel E. The registration base used for Panel C/D status')
    sb.headers(['Subject-company estate ZIP', 'Registered city',
                'Estate NPIs at ZIP', '', '', '', '', '', 'Note', ''])
    for i, z in enumerate(sorted(est_zip_info)):
        d = est_zip_info[z]
        sb.row([(z, 'src'), ('; '.join(sorted(d['cities'])), 'src'),
                (len(d['npis']), 'src', lib.FMT_INT),
                None, None, None, None, None,
                ('NPPES practice locations of the 23 estate NPIs, pulled '
                 '11 Jul 2026 (estate_addresses.json)', 'note')
                if i == 0 else None, None])
    sb.row([('Resolved participant registration base', 'label'),
            (f'{n_resolved_queries} resolved queries', 'text'),
            (len(part_npis), 'src', lib.FMT_INT),
            (len(part_zips), 'src', lib.FMT_INT),
            None, None, None, None,
            ('C = distinct best-match participant NPIs with a ZIP; '
             'D = distinct participant ZIP5s (nppes_crosswalk best NPIs '
             'over nppes_participant_resolution)', 'note'), None])
    sb.blank()

    sb.banner('Read panel')
    sb.prose('What is measured: the nine cohort systems draw about '
             f'{round(tot_cases):,} Medicare FFS inpatient cases a year '
             'through their top-15 origin-ZIP corridors (about '
             f'${sum(a["charges"] for a in agg.values()) / 1e9:,.1f}B in '
             f'charges), led by {top_sys} at '
             f'{round(agg[top_sys]["cases"]):,}. Applying the measured '
             'HCUP transfer rate to that corridor volume prices the '
             'implied transfer-demand line per system in Panel B (live, '
             'green-linked). The registration overlay is the striking '
             'part: only about '
             f'{tot_cov / tot_cases:.1%} of cohort corridor volume '
             'originates in ZIPs where the subject-company estate holds a '
             f'registered location and about {tot_con / tot_cases:.1%} '
             'where any resolved participant does; roughly '
             f'{tot_open / tot_cases:.0%} of the corridor map is open '
             'registration territory. What this is NOT: coverage or share. '
             'Registered ZIPs are administrative points, corridors are '
             'Medicare-FFS-only floors, and the match rules carry the '
             'stated confounds of Panel A.')

    # ----------------------------------------------------------- registers
    facts += [
        {'metric': 'Research-cohort corridor cases, nine systems, top-15 '
                   'origin ZIPs (Medicare FFS inpatient floor)',
         'year': 2025, 'value': round(tot_cases), 'unit': 'cases',
         'basis': 'GOV', 'tier': 'A',
         'source_keys': ['cohort_hsa_corridors', 'cohort_hcris_roster',
                         'cohort_pdc_roster'],
         'locator': 'HSA 2025 top-15 extract, CCNs per Panel A printed '
                    'rules; Panel B total row',
         'lives_on': 'Cohort_Corridors',
         'cross_check': 'Sum of nine live system rows; per-CCN rows '
                        're-derivable from HSA_Corridors'},
        {'metric': f'Largest cohort system by corridor volume ({top_sys})',
         'year': 2025, 'value': round(agg[top_sys]['cases']),
         'unit': 'cases', 'basis': 'GOV', 'tier': 'A',
         'source_keys': ['cohort_hsa_corridors', 'cohort_hcris_roster',
                         'cohort_pdc_roster'],
         'locator': 'Panel B first data row (systems sorted by cases)',
         'lives_on': 'Cohort_Corridors',
         'cross_check': f'{len(agg[top_sys]["in_corr"])} hospitals in the '
                        'corridor file under the printed rule'},
        {'metric': 'Cohort corridor volume COVERED: originating in ZIPs '
                   'with a registered subject-company estate location',
         'year': 2025, 'value': round(tot_cov / tot_cases, 4),
         'unit': 'share of cohort corridor cases', 'basis': 'DERIVED',
         'tier': 'A',
         'source_keys': ['cohort_hsa_corridors', 'cohort_nppes_locations'],
         'locator': 'Panel C total row, covered share (live)',
         'lives_on': 'Cohort_Corridors',
         'cross_check': 'Registration presence only; understates operating '
                        'coverage by construction'},
        {'metric': 'Cohort corridor volume CONTESTED: participant ZIP '
                   'present, no estate ZIP',
         'year': 2025, 'value': round(tot_con / tot_cases, 4),
         'unit': 'share of cohort corridor cases', 'basis': 'DERIVED',
         'tier': 'A',
         'source_keys': ['cohort_hsa_corridors', 'cohort_nppes_locations'],
         'locator': 'Panel C total row, contested share (live)',
         'lives_on': 'Cohort_Corridors',
         'cross_check': f'{len(part_zips)} participant ZIP5s from '
                        f'{n_resolved_queries} resolved crosswalk queries'},
        {'metric': 'Cohort corridor volume OPEN: no estate or participant '
                   'registration in the origin ZIP',
         'year': 2025, 'value': round(tot_open / tot_cases, 4),
         'unit': 'share of cohort corridor cases', 'basis': 'DERIVED',
         'tier': 'A',
         'source_keys': ['cohort_hsa_corridors', 'cohort_nppes_locations'],
         'locator': 'Panel C total row, open share (live)',
         'lives_on': 'Cohort_Corridors',
         'cross_check': 'Covered + contested + open sum to 1 in the live '
                        'row'},
    ]

    findings.append({
        'id_hint': 59,
        'finding': 'The cohort corridor map is measured and it is mostly '
                   'unclaimed territory: the nine research-cohort systems '
                   f'draw about {round(tot_cases):,} Medicare FFS inpatient '
                   'cases a year through their top-15 origin-ZIP corridors '
                   f'(led by {top_sys} at '
                   f'{round(agg[top_sys]["cases"]):,}), each system priced '
                   'with a live implied transfer-demand line at the '
                   'measured HCUP rate - yet only about '
                   f'{tot_cov / tot_cases:.1%} of that corridor volume '
                   'originates in ZIPs where the subject-company estate is '
                   f'registered and about {tot_con / tot_cases:.1%} where '
                   'any resolved market participant is.',
        'numbers': f"='Cohort_Corridors'!C{tot_rn}",
        'sources': 'cohort_hsa_corridors; cohort_hcris_roster; '
                   'cohort_pdc_roster; cohort_nppes_locations',
        'confidence': 'High as a floor on corridor volume; the '
                      'registration overlay is exact on NPPES but is a '
                      'presence proxy',
        'guardrail': 'Medicare FFS inpatient corridors truncated to top-15 '
                     'ZIPs per hospital; name-match rules carry the Panel '
                     'A confounds; registered ZIPs are not service areas, '
                     'so covered/contested understate operations and the '
                     'implied transfer line applies an all-payer rate to '
                     'FFS-only volume - directional, never a market size. '
                     'The group is framed strictly as a ' + COHORT_FRAME
                     + '.'})

    # ------------------------------------------------------------- chart
    lib.add_chart(
        ws, 'L6', 'Cohort corridor cases by system (HSA 2025, top-15 ZIPs)',
        f"'Cohort_Corridors'!$A${b0}:$A${tot_rn - 1}",
        [('Corridor cases', f"'Cohort_Corridors'!$C${b0}:$C${tot_rn - 1}")],
        kind='bar', y_fmt='#,##0')

    return {'facts': facts, 'sources': sources, 'excluded': excluded,
            'findings': findings,
            'meta': {'systems': len(RULES),
                     'rate_cell': rate_cell,
                     'estate_zips': len(est_zips),
                     'participant_zips': len(part_zips),
                     'match_counts': {n: len(sys_ccns[n]) for n in order}}}
