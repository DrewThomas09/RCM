"""A.7: Hub_Spoke_Map - the regionalization exhibit.

Every hospital CCN in the CMS Hospital Service Area 2025 top-15 corridor
extract is classified HUB / SPOKE / MIXED from two measured dimensions:
total top-15 corridor cases (volume) and corridor breadth (the number of
top-15 origin ZIPs needed to reach 80% of those cases - a shed-width
measure that top-15 truncation biases DOWN). Hubs are counted nationally,
by state, and against the research-cohort systems; the 20-target-metro cut
stays PENDING because the workbook's county-based CBSA crosswalk cannot
place ZIP-grain rows.
"""

import collections
import csv
import gzip
import math

SHEETS = [{'name': 'Hub_Spoke_Map',
           'question': 'How concentrated is hospital inpatient corridor '
                       'volume in high-volume wide-shed hub hospitals - '
                       'the regionalization structure under any '
                       'transfer-lane thesis?'}]

HCRIS_GZ = '/home/user/RCM/RCM_MC/rcm_mc/data/hcris.csv.gz'
BREADTH_HUB = 8
BREADTH_SPOKE = 3
FOOT = ['NE', 'OH', 'WI', 'IA', 'KS', 'IN', 'KY', 'MO', 'MN', 'VA', 'WY']

COHORT_FRAME = ('research cohort of representative multi-hospital health '
                'systems operating in the study footprint, selected for depth')

# SSA state codes: fallback state attribution from the CCN prefix when a
# corridor CCN has no roster row in either public roster.
SSA = {'01': 'AL', '02': 'AK', '03': 'AZ', '04': 'AR', '05': 'CA',
       '06': 'CO', '07': 'CT', '08': 'DE', '09': 'DC', '10': 'FL',
       '11': 'GA', '12': 'HI', '13': 'ID', '14': 'IL', '15': 'IN',
       '16': 'IA', '17': 'KS', '18': 'KY', '19': 'LA', '20': 'ME',
       '21': 'MD', '22': 'MA', '23': 'MI', '24': 'MN', '25': 'MS',
       '26': 'MO', '27': 'MT', '28': 'NE', '29': 'NV', '30': 'NH',
       '31': 'NJ', '32': 'NM', '33': 'NY', '34': 'NC', '35': 'ND',
       '36': 'OH', '37': 'OK', '38': 'OR', '39': 'PA', '40': 'PR',
       '41': 'RI', '42': 'SC', '43': 'SD', '44': 'TN', '45': 'TX',
       '46': 'UT', '47': 'VT', '48': 'VI', '49': 'VA', '50': 'WA',
       '51': 'WV', '52': 'WI', '53': 'WY'}


def _norm(n):
    return (n or '').upper().replace('.', '').replace("'", '')


# Same printed rules as Cohort_Corridors Panel A (kept in lockstep).
COHORT_RULES = [
    ('Cleveland Clinic', lambda n, s, c: 'CLEVELAND CLINIC' in n),
    ('Inova', lambda n, s, c: 'INOVA' in n),
    ('CommonSpirit / CHI Health',
     lambda n, s, c: 'CHI HEALTH' in n or 'COMMONSPIRIT' in n),
    ('Nebraska Methodist',
     lambda n, s, c: ('METHODIST' in n and s == 'NE')
     or 'JENNIE EDMUNDSON' in n),
    ('Premier Health (Dayton)',
     lambda n, s, c: s == 'OH' and ('MIAMI VALLEY HOSPITAL' in n
                                    or 'UPPER VALLEY MEDICAL' in n
                                    or 'ATRIUM MEDICAL' in n)),
    ("Saint Luke's Health System (Kansas City)",
     lambda n, s, c: ('ST LUKE' in _norm(n) or 'SAINT LUKE' in n)
     and s in ('MO', 'KS')
     and c not in ('ST. LOUIS', 'SAINT LOUIS', 'CHESTERFIELD', 'MARION')),
    ('Froedtert', lambda n, s, c: 'FROEDTERT' in n),
    ('Baptist Health (KY/IN)',
     lambda n, s, c: 'BAPTIST HEALTH' in n and s in ('KY', 'IN')),
    ('Ascension', lambda n, s, c: 'ASCENSION' in n),
]


def _pctile(sorted_vals, p):
    k = (len(sorted_vals) - 1) * p
    f, c = math.floor(k), math.ceil(k)
    return sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f)


def build(wb, ctx):
    lib = ctx['lib']
    cache = ctx['cache']
    accessed = ctx['accessed']
    facts, sources, excluded, findings = [], [], [], []

    # ---------------------------------------------------------------- data
    corr = lib.load_cache(cache, 'hsa_2025_corridors_top15')
    by_ccn = collections.defaultdict(list)
    for r in corr:
        by_ccn[r['provider_id']].append(r)

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

    def info(ccn):
        return pdc.get(ccn) or hcris.get(ccn) or {}

    def state_of(ccn):
        d = info(ccn)
        return d.get('state') or SSA.get(ccn[:2], '??')

    n_unrostered = sum(1 for c in by_ccn if c not in pdc and c not in hcris)

    cohort_ccns = {}
    for name, pred in COHORT_RULES:
        hits = set()
        for src in (hcris, pdc):
            for ccn, d in src.items():
                if pred(d['name'], d['state'], d['city']):
                    hits.add(ccn)
        cohort_ccns[name] = hits
    cohort_all = set().union(*cohort_ccns.values())

    # volume + breadth per CCN (breadth over the top-15 rows: truncated)
    stats = {}
    for ccn, rows in by_ccn.items():
        rows = sorted(rows, key=lambda r: r['rank'])
        tot = sum(r['cases'] for r in rows)
        breadth, cum = 0, 0.0
        if tot > 0:
            for i, r in enumerate(rows, 1):
                cum += r['cases']
                if cum >= 0.8 * tot:
                    breadth = i
                    break
        stats[ccn] = (tot, breadth)

    vols = sorted(t for t, _ in stats.values())
    p90 = _pctile(vols, 0.90)
    med = _pctile(vols, 0.50)
    hubs = {c for c, (t, b) in stats.items()
            if t >= p90 and b >= BREADTH_HUB}
    spokes = {c for c, (t, b) in stats.items()
              if t <= med and b <= BREADTH_SPOKE}
    mixed = set(stats) - hubs - spokes
    nat_cases = sum(t for t, _ in stats.values())
    cls_cases = {'HUB': sum(stats[c][0] for c in hubs),
                 'SPOKE': sum(stats[c][0] for c in spokes),
                 'MIXED': sum(stats[c][0] for c in mixed)}
    n_topdecile = sum(1 for t, _ in stats.values() if t >= p90)

    st_hub = collections.Counter(state_of(c) for c in hubs)
    st_hubvol = collections.defaultdict(float)
    for c in hubs:
        st_hubvol[state_of(c)] += stats[c][0]
    st_allvol = collections.defaultdict(float)
    st_n = collections.Counter()
    for c in stats:
        s = state_of(c)
        st_allvol[s] += stats[c][0]
        st_n[s] += 1
    top_states = [s for s, _ in st_hub.most_common(15)]
    foot_hubs = sum(st_hub[s] for s in FOOT)
    cohort_hub_ccns = hubs & cohort_all
    hub_share = cls_cases['HUB'] / nat_cases if nat_cases else 0

    # ------------------------------------------------------------- sources
    sources += [
        {'key': 'hub_hsa_corridors', 'publisher': 'CMS',
         'document': 'Hospital Service Area file, 2025 release - top-15 '
                     'origin-ZIP corridor extract, every hospital CCN '
                     '(cache hsa_2025_corridors_top15; full grain on '
                     'HSA_Corridors)',
         'vintage': '2025 (Medicare FFS inpatient claims)',
         'locator': f'{len(stats):,} CCNs x up to 15 origin-ZIP rows; '
                    'volume = sum of cases, breadth = ZIPs to 80% of '
                    'top-15 cases',
         'supplies': 'The two measured dimensions behind the HUB / SPOKE '
                     '/ MIXED classification',
         'url': 'https://data.cms.gov/summary-statistics-on-use-and-'
                'payments/medicare-service-type-reports/'
                'hospital-service-area',
         'tier': 'A', 'accessed': accessed, 'powers': ['Hub_Spoke_Map']},
        {'key': 'hub_hcris_roster', 'publisher': 'CMS (HCRIS)',
         'document': 'Hospital cost report (HCRIS) panel, vendored extract '
                     'rcm_mc/data/hcris.csv.gz (latest filed year per CCN)',
         'vintage': 'FY2020-FY2022 cost reports',
         'locator': 'ccn -> name / state join for hub attribution',
         'supplies': 'Hospital names and states for the state and cohort '
                     'cuts',
         'url': 'https://www.cms.gov/data-research/statistics-trends-'
                'reports/cost-reports',
         'tier': 'A', 'accessed': accessed, 'powers': ['Hub_Spoke_Map']},
        {'key': 'hub_pdc_roster', 'publisher': 'CMS (Provider Data '
         'Catalog)',
         'document': 'Care Compare - Hospital General Information roster '
                     '(cache pdc2_hospitals)',
         'vintage': '2026 roster',
         'locator': 'facility_id -> facility_name / state join, preferred '
                    'over the cost-report name where both exist',
         'supplies': 'Current hospital names and states; SSA CCN-prefix '
                     'fallback covers CCNs in neither roster',
         'url': 'https://data.cms.gov/provider-data/dataset/xubh-q36u',
         'tier': 'A', 'accessed': accessed, 'powers': ['Hub_Spoke_Map']},
    ]

    # ----------------------------------------------------------------- tab
    ws = wb.create_sheet('Hub_Spoke_Map')
    sb = lib.SheetBuilder(ws, 9,
                          col_widths=[36, 13, 13, 13, 13, 13, 13, 13, 46],
                          tab_color='FF1F6F8B')
    sb.title('Hub and spoke: the measured regionalization of hospital '
             'corridor volume')
    sb.subtitle('The question: how concentrated is inpatient corridor '
                'volume in high-volume, wide-shed hub hospitals - the '
                'regionalization structure that generates interfacility '
                'transfer lanes? Every CCN in the CMS Hospital Service '
                'Area 2025 top-15 extract is scored on two measured '
                'dimensions - total top-15 corridor cases and corridor '
                'breadth (ZIPs to reach 80% of those cases) - and '
                'classified by the printed thresholds of Panel A. Joins: '
                'CCN to HCRIS / Care Compare rosters for names and states '
                '(SSA CCN-prefix fallback), printed cohort name-match '
                'rules from Cohort_Corridors for the cohort cut.',
                height=56)
    sb.note('DATA QUALITY: Medicare FFS INPATIENT corridors only (no MA, '
            'Medicaid, commercial); the top-15 truncation biases breadth '
            'DOWN and caps it at 15, so wide urban sheds understate and '
            'hub counts are conservative; CMS suppresses cells under 11 '
            'cases at source (small-hospital volumes are floors); '
            f'{n_unrostered:,} of {len(stats):,} corridor CCNs have no '
            'row in either roster, so their state comes from the SSA CCN '
            'prefix; HUB / SPOKE / MIXED are workbook-defined constructs '
            'printed in Panel A, not CMS designations; corridor cases '
            'measure a hospital\'s inpatient DRAW, not transfers.',
            height=44)
    sb.blank()

    # Panel A - thresholds
    sb.banner('Panel A. Classification thresholds (printed, from the '
              'measured distribution)')
    sb.headers(['Threshold', 'Value', '', '', '', '', '', '',
                'Justification'])
    a0 = sb.r + 1
    sb.row([('Hospitals scored (CCNs in the corridor extract)', 'label'),
            (len(stats), 'src', lib.FMT_INT), None, None, None, None, None,
            None, ('every CCN with at least one HSA 2025 ZIP row', 'note')])
    sb.row([('90th percentile of top-15 corridor cases', 'label'),
            (round(p90, 1), 'src', lib.FMT_DEC1), None, None, None, None,
            None, None,
            ('volume bar: top decile of the national distribution',
             'note')])
    sb.row([('Median top-15 corridor cases', 'label'),
            (round(med, 1), 'src', lib.FMT_DEC1), None, None, None, None,
            None, None, ('volume bar for the spoke class', 'note')])
    sb.row([('HUB rule: cases at or above the 90th percentile AND breadth '
             'at or above 8 of 15', 'label'),
            (BREADTH_HUB, 'src', lib.FMT_INT), None, None, None, None,
            None, None,
            ('top-decile volume drawn over a wide shed (8+ ZIPs to reach '
             '80% of top-15 cases): the regional-center signature',
             'note')])
    sb.row([('SPOKE rule: cases at or below the median AND breadth at or '
             'below 3 of 15', 'label'),
            (BREADTH_SPOKE, 'src', lib.FMT_INT), None, None, None, None,
            None, None,
            ('at-or-below-median volume drawn almost entirely from its '
             'own few ZIPs: the local-feeder signature', 'note')])
    sb.row([('MIXED: every other hospital', 'label'), ('-', 'text'),
            None, None, None, None, None, None,
            (f'of {n_topdecile:,} top-decile-volume hospitals, '
             f'{len(hubs):,} also clear the breadth bar', 'note')])
    sb.blank()

    # Panel B - national classification
    sb.banner('Panel B. National classification and the concentration of '
              'corridor volume')
    sb.headers(['Class', 'Hospitals', 'Share of hospitals',
                'Corridor cases (floor)', 'Share of national cases',
                'Mean cases per hospital', '', '', 'Note'])
    b0 = sb.r + 1
    btot = b0 + 3
    for i, (label, ccns) in enumerate([('HUB', hubs), ('SPOKE', spokes),
                                       ('MIXED', mixed)]):
        rn = b0 + i
        sb.row([(label, 'label'),
                (len(ccns), 'src', lib.FMT_INT),
                (f'=IF(B${btot}=0,"n/a",B{rn}/B${btot})', 'fml',
                 lib.FMT_PCT1),
                (round(cls_cases[label]), 'src', lib.FMT_INT),
                (f'=IF(D${btot}=0,"n/a",D{rn}/D${btot})', 'fml',
                 lib.FMT_PCT1),
                (f'=IF(B{rn}=0,"n/a",D{rn}/B{rn})', 'fml', lib.FMT_INT),
                None, None,
                ('classes are exhaustive and mutually exclusive by the '
                 'Panel A rules', 'note') if i == 0 else None])
    sb.row([('All hospitals', 'label'),
            (f'=SUM(B{b0}:B{btot - 1})', 'fml', lib.FMT_INT),
            (f'=IF(B{btot}=0,"n/a",1)', 'fml', lib.FMT_PCT1),
            (f'=SUM(D{b0}:D{btot - 1})', 'fml', lib.FMT_INT),
            (f'=IF(D{btot}=0,"n/a",1)', 'fml', lib.FMT_PCT1),
            (f'=IF(B{btot}=0,"n/a",D{btot}/B{btot})', 'fml', lib.FMT_INT),
            None, None, None])
    sb.blank()

    # Panel C - states
    sb.banner('Panel C. Hub geography by state: top-15 states by hub '
              'count, then the 11 footprint states')
    sb.headers(['State', 'Hubs', 'Hospitals scored', 'Hub corridor cases',
                'State corridor cases', 'Share of state cases through '
                'hubs', '', '', 'Note'])
    c0 = sb.r + 1
    for i, s in enumerate(top_states):
        rn = c0 + i
        sb.row([(s, 'src'), (st_hub[s], 'src', lib.FMT_INT),
                (st_n[s], 'src', lib.FMT_INT),
                (round(st_hubvol[s]), 'src', lib.FMT_INT),
                (round(st_allvol[s]), 'src', lib.FMT_INT),
                (f'=IF(E{rn}=0,"n/a",D{rn}/E{rn})', 'fml', lib.FMT_PCT1),
                None, None,
                ('top-15 states by hub count', 'note') if i == 0 else None])
    c_top_end = sb.r
    sb.row([('Footprint states below (NE OH WI IA KS IN KY MO MN VA WY)',
             'note'), None, None, None, None, None, None, None, None])
    f0 = sb.r + 1
    for i, s in enumerate(FOOT):
        rn = f0 + i
        sb.row([(s, 'src'), (st_hub[s], 'src', lib.FMT_INT),
                (st_n[s], 'src', lib.FMT_INT),
                (round(st_hubvol[s]), 'src', lib.FMT_INT),
                (round(st_allvol[s]), 'src', lib.FMT_INT),
                (f'=IF(E{rn}=0,"n/a",D{rn}/E{rn})', 'fml', lib.FMT_PCT1),
                None, None, None])
    ftot = f0 + len(FOOT)
    sb.row([('Footprint total', 'label'),
            (f'=SUM(B{f0}:B{ftot - 1})', 'fml', lib.FMT_INT),
            (f'=SUM(C{f0}:C{ftot - 1})', 'fml', lib.FMT_INT),
            (f'=SUM(D{f0}:D{ftot - 1})', 'fml', lib.FMT_INT),
            (f'=SUM(E{f0}:E{ftot - 1})', 'fml', lib.FMT_INT),
            (f'=IF(E{ftot}=0,"n/a",D{ftot}/E{ftot})', 'fml', lib.FMT_PCT1),
            None, None, None])
    sb.blank()

    # Panel D - top hubs + cohort cross
    sb.banner('Panel D. The 20 largest hubs, and the research-cohort '
              'cross-tag')
    sb.headers(['Hub hospital (roster name)', 'CCN', 'State',
                'Corridor cases', 'Breadth (ZIPs to 80%)',
                'Cohort system (printed rules)', '', '', 'Note'])
    top20 = sorted(hubs, key=lambda c: -stats[c][0])[:20]
    for i, ccn in enumerate(top20):
        d = info(ccn)
        member = next((n for n, cs in cohort_ccns.items() if ccn in cs),
                      '-')
        sb.row([(d.get('name') or '(no roster row)', 'src'),
                (ccn, 'src'), (state_of(ccn), 'src'),
                (round(stats[ccn][0]), 'src', lib.FMT_INT),
                (stats[ccn][1], 'src', lib.FMT_INT),
                (member, 'text'), None, None,
                ('breadth is truncation-capped at 15', 'note')
                if i == 0 else None])
    sb.row([('Hubs matched to a research-cohort system (all hubs, not '
             'just the 20 above)', 'label'),
            (len(cohort_hub_ccns), 'src', lib.FMT_INT),
            None, None, None, None, None, None,
            ('CCN in any Cohort_Corridors Panel A rule match set; the '
             'group is a ' + COHORT_FRAME, 'note')], wrap=True, height=28)
    sb.blank()

    # Panel E - metro cut: PENDING
    sb.banner('Panel E. The 20-target-metro cut (Metro_Structure_20)')
    sb.row([('Hub counts per target metro via ZIP-to-CBSA', 'label'),
            ('PENDING', 'note'), None, None, None, None, None, None,
            ('CBSA_Crosswalk_Reference is the 2023 OMB COUNTY-to-CBSA '
             'delineation: it cannot place a ZIP-grain corridor row or a '
             'hospital ZIP into a CBSA. Public key that fills this cell: '
             'the HUD-USPS ZIP-CBSA crosswalk file (or the Census '
             'ZCTA-to-CBSA relationship file). Until then the state cut '
             'of Panel C is the supported geography.', 'note')],
           wrap=True, height=40)
    sb.blank()

    sb.banner('Read panel')
    sb.prose('The regionalization exhibit, measured: '
             f'{len(hubs):,} hospitals - {len(hubs) / len(stats):.1%} of '
             f'the {len(stats):,} scored - clear both printed bars '
             '(top-decile volume, breadth of 8+ ZIPs) and those hubs '
             f'carry {hub_share:.1%} of all top-15 corridor volume, '
             f'about {cls_cases["HUB"] / 1e6:,.1f}M Medicare FFS '
             f'inpatient cases a year. {foot_hubs} hubs sit in the 11 '
             f'footprint states and {len(cohort_hub_ccns)} hub CCNs '
             'belong to research-cohort systems. The spoke tier is the '
             f'mirror image: {len(spokes):,} hospitals at or below '
             'median volume drawing from 3 or fewer ZIPs - the '
             'local-feeder tier that regionalized service lines must '
             'move patients OUT of. What this is NOT: a transfer matrix. '
             'HSA corridors measure where inpatients come FROM, so hub '
             'status is a structural signature of regional draw; the '
             'transfer-lane volumes themselves live on Acute_IFT_Series '
             'and Medicare_IFT_Series.')

    # ----------------------------------------------------------- registers
    facts += [
        {'metric': 'Hub hospitals nationally (top-decile top-15 corridor '
                   'volume AND breadth >= 8 of 15)',
         'year': 2025, 'value': len(hubs), 'unit': 'hospitals',
         'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['hub_hsa_corridors'],
         'locator': 'Panel B HUB row; thresholds printed in Panel A '
                    f'(p90 = {p90:,.1f} cases, median = {med:,.0f})',
         'lives_on': 'Hub_Spoke_Map',
         'cross_check': f'{n_topdecile:,} hospitals clear the volume bar '
                        'alone; the breadth bar removes the narrow-shed '
                        'fifth of them'},
        {'metric': 'Hub hospitals in the 11 footprint states '
                   '(NE OH WI IA KS IN KY MO MN VA WY)',
         'year': 2025, 'value': foot_hubs, 'unit': 'hospitals',
         'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['hub_hsa_corridors', 'hub_hcris_roster',
                         'hub_pdc_roster'],
         'locator': 'Panel C footprint block, live total row',
         'lives_on': 'Hub_Spoke_Map',
         'cross_check': 'State attribution from rosters with SSA '
                        'CCN-prefix fallback for '
                        f'{n_unrostered:,} unrostered CCNs'},
        {'metric': 'Share of national top-15 corridor volume carried by '
                   'hub hospitals',
         'year': 2025, 'value': round(hub_share, 4),
         'unit': 'share of corridor cases', 'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['hub_hsa_corridors'],
         'locator': 'Panel B HUB row, live share cell',
         'lives_on': 'Hub_Spoke_Map',
         'cross_check': f'Hubs are {len(hubs) / len(stats):.1%} of '
                        'hospitals: roughly a five-to-one concentration '
                        'ratio'},
        {'metric': 'Spoke hospitals nationally (at or below median volume, '
                   'breadth <= 3 of 15)',
         'year': 2025, 'value': len(spokes), 'unit': 'hospitals',
         'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['hub_hsa_corridors'],
         'locator': 'Panel B SPOKE row',
         'lives_on': 'Hub_Spoke_Map',
         'cross_check': 'Spokes carry '
                        f'{cls_cases["SPOKE"] / nat_cases:.1%} of national '
                        'corridor volume despite being '
                        f'{len(spokes) / len(stats):.0%} of hospitals'},
        {'metric': 'Hub CCNs belonging to research-cohort systems',
         'year': 2025, 'value': len(cohort_hub_ccns), 'unit': 'hospitals',
         'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['hub_hsa_corridors', 'hub_hcris_roster',
                         'hub_pdc_roster'],
         'locator': 'Panel D cross-tag row; rules printed on '
                    'Cohort_Corridors Panel A',
         'lives_on': 'Hub_Spoke_Map',
         'cross_check': 'Name-match confounds carried from '
                        'Cohort_Corridors apply here unchanged'},
    ]

    findings.append({
        'id_hint': 60,
        'finding': 'Regionalization is measurable in the corridor file '
                   f'itself: {len(hubs):,} hub hospitals - '
                   f'{len(hubs) / len(stats):.1%} of the {len(stats):,} '
                   'scored - combine top-decile inpatient volume with '
                   'sheds 8+ ZIPs wide and carry '
                   f'{hub_share:.1%} of all Medicare FFS top-15 corridor '
                   f'volume, while {len(spokes):,} narrow-shed spoke '
                   'hospitals sit at or below median volume. '
                   f'{foot_hubs} of those hubs are in the 11 footprint '
                   'states - the measured hub-and-spoke lattice under '
                   'any interfacility transfer lane.',
        'numbers': f"='Hub_Spoke_Map'!B{b0}",
        'sources': 'hub_hsa_corridors; hub_hcris_roster; hub_pdc_roster',
        'confidence': 'High on the concentration direction; class counts '
                      'move with the printed thresholds',
        'guardrail': 'HUB/SPOKE are workbook constructs from printed '
                     'thresholds over Medicare FFS inpatient corridors '
                     'truncated to top-15 ZIPs; breadth is biased down by '
                     'truncation, corridors measure draw rather than '
                     'transfers, and no metro cut exists until a '
                     'ZIP-to-CBSA crosswalk is added (Panel E PENDING).'})

    # ------------------------------------------------------------- chart
    lib.add_chart(
        ws, 'K6', 'Hub hospitals by state (top 15, HSA 2025)',
        f"'Hub_Spoke_Map'!$A${c0}:$A${c_top_end}",
        [('Hubs', f"'Hub_Spoke_Map'!$B${c0}:$B${c_top_end}")],
        kind='bar', y_fmt='#,##0')

    return {'facts': facts, 'sources': sources, 'excluded': excluded,
            'findings': findings,
            'meta': {'hospitals': len(stats), 'p90': round(p90, 1),
                     'median': round(med, 1), 'hubs': len(hubs),
                     'spokes': len(spokes), 'mixed': len(mixed),
                     'hub_vol_share': round(hub_share, 4),
                     'footprint_hubs': foot_hubs,
                     'cohort_hub_ccns': len(cohort_hub_ccns),
                     'unrostered_ccns': n_unrostered}}
