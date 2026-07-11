"""A.5: HCRIS_Ambulance_CostCenters - which hospitals run their own
ambulance operation, what it costs them, and who is entering or exiting.

Built from the raw CMS HCRIS HOSP10 (form 2552-10) cost-report extracts,
year-files FY2019-FY2023, pulled 11 Jul 2026 (pull12.py). The ambulance
cost center is Worksheet A line 95: verified in every year-file as
LINE_NUM '09500' on WKSHT_CD 'A000000' with the ALPHA cost-center label
'AMBULANCE SERVICES'; no subscripted lines 09501-09599 exist in any
year-file. Columns kept: 00100 salaries, 00200 other, 00300 total (as
filed). Cache keys: hcris_amb_cost_center (rows) and
hcris_amb_filer_counts (share denominator).
"""

import csv
import gzip
import os
from collections import Counter, defaultdict

SHEETS = [{'name': 'HCRIS_Ambulance_CostCenters',
           'question': 'Which hospitals report an ambulance cost center on '
                       'their Medicare cost report, at what dollar scale, '
                       'and where are hospitals entering or exiting the '
                       'business?'}]

HCRIS_GZ = os.path.join('RCM_MC', 'rcm_mc', 'data', 'hcris.csv.gz')
FOOTPRINT = ['NE', 'IA', 'KS', 'MO', 'OH', 'WI', 'VA', 'MN', 'IN', 'KY']
SHOW_YEARS = [2019, 2020, 2021, 2022, 2023, 2024]
COMPLETE_YEARS = [2020, 2021, 2022, 2023]
LATEST = 2023          # latest common (complete) FY end year
PAIRS = [(2020, 2021), (2021, 2022), (2022, 2023)]
CMS_COST_URL = ('https://www.cms.gov/data-research/statistics-trends-reports/'
                'cost-reports/hospital-2010-form')


def _dollars(r):
    """Ambulance dollars as filed: total (col 0300) when present, else
    salaries + other."""
    if r.get('total') is not None:
        return r['total']
    return (r.get('salaries') or 0.0) + (r.get('other') or 0.0)


def build(wb, ctx):
    lib = ctx['lib']
    cache = ctx['cache']
    repo = ctx['repo']
    accessed = ctx['accessed']
    facts, sources, excluded, findings = [], [], [], []

    rows = lib.load_cache(cache, 'hcris_amb_cost_center')
    filer_counts = {int(k): v for k, v in
                    lib.load_cache(cache, 'hcris_amb_filer_counts').items()}

    # ── roll up: reporters + dollars per FY end year ──
    byfy = defaultdict(set)                       # fy -> set of CCNs, nonzero
    agg = defaultdict(lambda: [0.0, 0.0, 0.0])    # fy -> [total, sal, oth]
    per_ccn = defaultdict(lambda: [0.0, 0.0, 0.0])  # (latest FY) ccn rollup
    labeled = 0
    lines_seen = set()
    for r in rows:
        lines_seen.add(r['line'])
        if r.get('label') and 'AMBULANCE' in r['label'].upper():
            labeled += 1
        d = _dollars(r)
        if not d:
            continue
        fy = r['fy_year']
        byfy[fy].add(r['ccn'])
        agg[fy][0] += d
        agg[fy][1] += r.get('salaries') or 0.0
        agg[fy][2] += r.get('other') or 0.0
        if fy == LATEST:
            p = per_ccn[r['ccn']]
            p[0] += d
            p[1] += r.get('salaries') or 0.0
            p[2] += r.get('other') or 0.0

    # ── names + states: vendored HCRIS panel, Care Compare fallback, then
    #    empirical SSA-prefix majority vote for brand-new CCNs ──
    st, nm = {}, {}
    prefix_votes = defaultdict(Counter)
    with gzip.open(os.path.join(repo, HCRIS_GZ), 'rt') as f:
        for row in csv.DictReader(f):
            ccn, s = row['ccn'], row['state']
            st[ccn] = s
            nm[ccn] = row['name']
            if s:
                prefix_votes[ccn[:2]][s] += 1
    prefix_map = {p: c.most_common(1)[0][0] for p, c in prefix_votes.items()}
    try:
        for h in lib.load_cache(cache, 'pdc2_hospitals'):
            fid = str(h.get('facility_id') or '')
            if fid and fid not in st:
                st[fid] = h.get('state')
                nm[fid] = h.get('facility_name')
    except FileNotFoundError:
        pass
    fallback_n = [0]

    def state_of(ccn):
        s = st.get(ccn)
        if s:
            return s
        fallback_n[0] += 1
        return prefix_map.get(ccn[:2], '??')

    # ── the tab ──
    ws = wb.create_sheet('HCRIS_Ambulance_CostCenters')
    sb = lib.SheetBuilder(ws, 10,
                          col_widths=[14, 15, 36, 14, 15, 14, 14, 14, 13, 48],
                          tab_color='FF8C1D40')
    sb.title('Hospital-run ambulance: the Worksheet A line 95 cost center, '
             'FY2019 - FY2024')
    sb.subtitle('The question: which hospitals report an ambulance cost '
                'center on their Medicare cost report (form 2552-10, '
                'Worksheet A line 95), at what dollar scale, and where are '
                'hospitals entering or exiting the business? Source: raw '
                'HCRIS HOSP10 year-file extracts FY2019-FY2023 (NMRC + RPT '
                '+ ALPHA files, pulled 11 Jul 2026), joined RPT_REC_NUM to '
                'CCN and fiscal-year end date; names and states joined from '
                'the vendored HCRIS panel (rcm_mc/data/hcris.csv.gz) with '
                'Care Compare and SSA state-prefix fallback. One row per '
                'hospital x FY end year; reporting = nonzero line 95 cost '
                '(column 3 total as filed, or salaries + other when no '
                'total is filed).')
    sb.note('DATA QUALITY: cost reports are self-reported and unaudited '
            '(as-filed, not settled). Line 95 captures hospital-based '
            'ambulance of ANY kind - 911 contracts and community EMS as '
            'well as IFT, with no service-mix split. Fiscal years straddle '
            'calendar years (an FY2023 row can begin in 2022). The newest '
            'FY here, fy_end 2024, is INCOMPLETE due to filing lag: only '
            f'{filer_counts.get(2024, 0):,} hospitals filed vs about 6,000 '
            'expected, because year-files group by FY BEGIN date and the '
            'FY2024 file is not yet cut. fy_end 2019 is also partial (the '
            'FY2018 year-file was not pulled). A handful of hospitals '
            '(roughly 30-50 reports per year-file) book ambulance under '
            'Worksheet A line 194 Other Special Purpose subscripts instead; '
            'they are recorded in the pull manifest but excluded here, so '
            'every count is a slight floor.', height=64)
    sb.note('LINE VERIFICATION (handoff-mandated): distinct LINE_NUM values '
            'on WKSHT_CD A000000 were scanned in every year-file; line 95 '
            "appears ONLY as the 5-character form '09500' (about 5,000 NMRC "
            'rows per year-file), never as 9500 or 95, and NO subscripted '
            'lines 09501-09599 exist in any year-file. The ALPHA '
            "cost-center label on line 09500 reads 'AMBULANCE SERVICES' "
            f'(label present on {labeled:,} of {len(rows):,} harvested '
            'hospital-FY rows; the label column also matches AMBULATORY '
            'surgery cost centers on other lines, which were excluded). '
            f'Lines carried on this tab: {", ".join(sorted(lines_seen))}.',
            height=50)
    sb.blank()

    # ── Panel A: coverage + share by FY ──
    sb.banner('Panel A. Hospitals reporting ambulance cost by cost-report '
              'FY end year - and the share of all filers')
    sb.headers(['FY end year', 'Hospitals filing 2552-10',
                'Hospitals with ambulance cost', 'Share of filers',
                'Ambulance total $', 'Salaries (col 1) $', 'Other (col 2) $',
                '', '', 'Coverage note'])
    a0 = sb.r + 1
    share_row = {}
    for i, fy in enumerate(SHOW_YEARS):
        rn = a0 + i
        share_row[fy] = rn
        note = ''
        if fy == 2019:
            note = ('PARTIAL - FY2018 year-file not pulled; reports '
                    'beginning 2018 and ending 2019 are missing')
        elif fy == 2024:
            note = ('INCOMPLETE - filing lag; only begin-2023 reports have '
                    'arrived, no FY2024 year-file yet')
        sb.row([(fy, 'src'),
                (filer_counts.get(fy, 0), 'src', lib.FMT_INT),
                (len(byfy[fy]), 'src', lib.FMT_INT),
                (f'=IF(B{rn}=0,"n/a",C{rn}/B{rn})', 'fml', lib.FMT_PCT1),
                (round(agg[fy][0]), 'src', lib.FMT_USD),
                (round(agg[fy][1]), 'src', lib.FMT_USD),
                (round(agg[fy][2]), 'src', lib.FMT_USD),
                None, None,
                (note, 'note') if note else None])
    sb.note('Salaries + other do not sum exactly to the total column: the '
            'total is kept AS FILED (column 3), and about a quarter of '
            'reporters file no salary line at all (a fully contracted '
            'service is booked entirely under Other).')
    lib.add_chart(
        ws, 'L7',
        'Hospitals reporting an ambulance cost center (complete FYs '
        '2020-2023; 2019 and 2024 are partial-coverage years)',
        f"'HCRIS_Ambulance_CostCenters'!$A${a0 + 1}:$A${a0 + 4}",
        [('Hospitals with ambulance cost',
          f"'HCRIS_Ambulance_CostCenters'!$C${a0 + 1}:$C${a0 + 4}")],
        kind='bar', width=20, height=9, y_title='hospitals', y_fmt='#,##0')
    sb.blank()

    # ── Panel B: state roster, latest complete FY ──
    state_cnt = Counter()
    state_usd = defaultdict(float)
    for ccn in byfy[LATEST]:
        s = state_of(ccn)
        state_cnt[s] += 1
        state_usd[s] += per_ccn[ccn][0]
    sb.banner(f'Panel B. State roster, FY end {LATEST} (latest complete FY '
              'in the extract)')
    sb.headers(['State', 'Hospitals with ambulance cost', 'Ambulance $',
                'Share of national $', 'Footprint?', '', '', '', '', 'Note'])
    b0 = sb.r + 1
    ordered = sorted(state_cnt, key=lambda s: -state_usd[s])
    b_last = b0 + len(ordered) - 1
    for j, s in enumerate(ordered):
        rn = b0 + j
        sb.row([(s, 'src'),
                (state_cnt[s], 'src', lib.FMT_INT),
                (round(state_usd[s]), 'src', lib.FMT_USD),
                (f'=IF(SUM(C${b0}:C${b_last})=0,"n/a",'
                 f'C{rn}/SUM(C${b0}:C${b_last}))', 'fml', lib.FMT_PCT1),
                ('FOOTPRINT', 'label') if s in FOOTPRINT else None,
                None, None, None, None,
                ('state = HCRIS panel roster state; SSA CCN-prefix '
                 f'fallback used for {fallback_n[0]} new CCNs', 'note')
                if j == 0 else None])
    tot_rn = sb.r + 1
    sb.row([('All states (live)', 'label'),
            (f'=SUM(B{b0}:B{b_last})', 'fml', lib.FMT_INT),
            (f'=SUM(C{b0}:C{b_last})', 'fml', lib.FMT_USD),
            None, None, None, None, None, None, None])
    fp_rn = sb.r + 1
    sb.row([('Footprint subtotal (live)', 'label'),
            (f'=SUMIF($E${b0}:$E${b_last},"FOOTPRINT",B${b0}:B${b_last})',
             'fml', lib.FMT_INT),
            (f'=SUMIF($E${b0}:$E${b_last},"FOOTPRINT",C${b0}:C${b_last})',
             'fml', lib.FMT_USD),
            None, None, None, None, None, None,
            ('footprint = NE IA KS MO OH WI VA MN IN KY', 'note')])
    sb.blank()

    # ── Panel C: top 30 hospitals by ambulance dollars, latest FY ──
    sb.banner(f'Panel C. Top 30 hospitals by ambulance cost, FY end {LATEST}')
    sb.headers(['CCN', 'State', 'Hospital (HCRIS panel / Care Compare '
                'roster name)', 'Ambulance total $', 'Salaries $', 'Other $',
                'Salaries share', '', '', 'Note'])
    c0 = sb.r + 1
    top30 = sorted(per_ccn.items(), key=lambda kv: -kv[1][0])[:30]
    for j, (ccn, (tot, sal, oth)) in enumerate(top30):
        rn = c0 + j
        sb.row([(ccn, 'src'), (state_of(ccn), 'src'),
                (nm.get(ccn) or '(not on carried rosters)', 'src'),
                (round(tot), 'src', lib.FMT_USD),
                (round(sal), 'src', lib.FMT_USD),
                (round(oth), 'src', lib.FMT_USD),
                (f'=IF(D{rn}=0,"n/a",E{rn}/D{rn})', 'fml', lib.FMT_PCT1),
                None, None,
                ('gross Worksheet A cost as filed, before reclasses and '
                 'adjustments - not net cost, not revenue', 'note')
                if j == 0 else None])
    sb.blank()

    # ── Panel D: flow series (stops and starts) ──
    sb.banner('Panel D. Candidate exit / entry events: hospitals that '
              'STOPPED or STARTED reporting ambulance cost, by year pair')
    sb.headers(['Year pair', 'Stopped (candidate outsourcing / shutdown)',
                'Started (candidate insourcing)', 'Net (starts - stops)',
                '', '', '', '', '', 'Caveat (same row, always)'])
    d0 = sb.r + 1
    net_row = {}
    pair_flows = {}
    for i, (ya, yb) in enumerate(PAIRS):
        rn = d0 + i
        net_row[(ya, yb)] = rn
        stops = byfy[ya] - byfy[yb]
        starts = byfy[yb] - byfy[ya]
        pair_flows[(ya, yb)] = (stops, starts)
        sb.row([(f'{ya} -> {yb}', 'text'),
                (len(stops), 'src', lib.FMT_INT),
                (len(starts), 'src', lib.FMT_INT),
                (f'=C{rn}-B{rn}', 'fml', lib.FMT_INT),
                None, None, None, None, None,
                ('CANDIDATE events only: a stop can be a fiscal-year '
                 'filing lag, a late/amended report, a hospital closure or '
                 'merger, or a relabeled cost center - not only '
                 'outsourcing; a start can be the mirror artifact',
                 'note')])
    sb.blank()

    sb.banner('Panel D2. Flow by state, the two mandated pairs (states with '
              'any activity; footprint flagged)')
    sb.headers(['State', 'Stops 2021 to 2022', 'Starts 2021 to 2022',
                'Stops 2022 to 2023', 'Starts 2022 to 2023',
                'Net 2022 to 2023', 'Footprint?', '', '', 'Note'])
    e0 = sb.r + 1
    fl = {}
    for (ya, yb) in [(2021, 2022), (2022, 2023)]:
        stops, starts = pair_flows[(ya, yb)]
        for c in stops:
            fl.setdefault(state_of(c), [0, 0, 0, 0])[0 if ya == 2021 else 2] += 1
        for c in starts:
            fl.setdefault(state_of(c), [0, 0, 0, 0])[1 if ya == 2021 else 3] += 1
    e_states = sorted(fl, key=lambda s: -sum(fl[s]))
    e_last = e0 + len(e_states) - 1
    for j, s in enumerate(e_states):
        rn = e0 + j
        v = fl[s]
        sb.row([(s, 'src'),
                (v[0], 'src', lib.FMT_INT), (v[1], 'src', lib.FMT_INT),
                (v[2], 'src', lib.FMT_INT), (v[3], 'src', lib.FMT_INT),
                (f'=E{rn}-D{rn}', 'fml', lib.FMT_INT),
                ('FOOTPRINT', 'label') if s in FOOTPRINT else None,
                None, None,
                ('candidate events, same caveat as Panel D; a state can '
                 'appear on both sides in the same pair', 'note')
                if j == 0 else None])
    efp_rn = sb.r + 1
    sb.row([('Footprint subtotal (live)', 'label'),
            (f'=SUMIF($G${e0}:$G${e_last},"FOOTPRINT",B${e0}:B${e_last})',
             'fml', lib.FMT_INT),
            (f'=SUMIF($G${e0}:$G${e_last},"FOOTPRINT",C${e0}:C${e_last})',
             'fml', lib.FMT_INT),
            (f'=SUMIF($G${e0}:$G${e_last},"FOOTPRINT",D${e0}:D${e_last})',
             'fml', lib.FMT_INT),
            (f'=SUMIF($G${e0}:$G${e_last},"FOOTPRINT",E${e0}:E${e_last})',
             'fml', lib.FMT_INT),
            (f'=E{efp_rn}-D{efp_rn}', 'fml', lib.FMT_INT),
            None, None, None, None])
    sb.blank()

    # ── read panel ──
    n23 = len(byfy[LATEST])
    usd23 = agg[LATEST][0]
    stops23, starts23 = pair_flows[(2022, 2023)]
    fp23 = sum(state_cnt[s] for s in FOOTPRINT)
    sb.banner('Read panel')
    sb.prose('Hospital-run ambulance is a steady minority franchise, not a '
             f'dying one: {n23:,} hospitals - about one in seven filers - '
             f'reported an ambulance cost center in FY{LATEST}, roughly '
             f'${usd23 / 1e9:.1f}B of as-filed cost, and the share has held '
             'near 14-15% across every complete FY in the extract. The '
             'franchise is small-hospital and rural-leaning: Texas, Iowa '
             'and Minnesota lead the roster by count, and the ten footprint '
             f'states hold {fp23} reporting hospitals. Churn runs both '
             f'ways: 2021 to 2022 saw {len(pair_flows[(2021, 2022)][0])} '
             f'candidate stops against {len(pair_flows[(2021, 2022)][1])} '
             f'starts (net exit), while 2022 to 2023 flipped to '
             f'{len(starts23)} starts against {len(stops23)} stops (net '
             'entry) - so the data does NOT show a one-way outsourcing '
             'wave at national scale. What a stop is: a candidate event '
             'only. It can be outsourcing to a private operator, but also '
             'a closure, a merger of provider numbers, a filing lag or a '
             'relabeled cost center; corroborate any single hospital '
             'against local records before reading it as a contract '
             'opportunity. And line 95 is ANY hospital-based ambulance - '
             '911 and community EMS as much as IFT.')

    # ── sources ──
    sources += [
        {'key': 'hcris_amb_ws_a', 'publisher': 'CMS (HCRIS)',
         'document': 'HOSP10 (form CMS-2552-10) raw cost-report extracts, '
                     'year-files FY2019-FY2023 (HOSP10FY{year}.zip, RPT + '
                     'NMRC + ALPHA members) - Worksheet A line 95 ambulance '
                     'harvest, cache hcris_amb_cost_center; filer '
                     'denominators, cache hcris_amb_filer_counts',
         'vintage': 'FY2019-FY2023 year-files, CMS refresh of 30 Apr 2026, '
                    'pulled 11 Jul 2026',
         'locator': "NMRC rows WKSHT_CD='A000000', LINE_NUM='09500' (form "
                    'line 95, ALPHA label AMBULANCE SERVICES; no 09501-'
                    '09599 subscripts exist), CLMN_NUM 00100/00200/00300; '
                    'RPT_REC_NUM joined to PRVDR_NUM and FY_END_DT',
         'supplies': 'Hospitals reporting ambulance cost by FY and state, '
                     'as-filed dollars, filer denominators, stop/start flow',
         'url': CMS_COST_URL, 'tier': 'A', 'accessed': accessed,
         'powers': ['HCRIS_Ambulance_CostCenters']},
        {'key': 'hcris_amb_roster_join', 'publisher': 'CMS',
         'document': 'Hospital name/state join: vendored HCRIS panel '
                     'rcm_mc/data/hcris.csv.gz (ccn, name, state) with Care '
                     'Compare hospital roster (cache pdc2_hospitals) and '
                     'SSA CCN state-prefix majority-vote fallback',
         'vintage': 'HCRIS panel FY2020-FY2022 vintage; Care Compare 2026 '
                    'roster',
         'locator': 'Join on CCN; prefix fallback only where a CCN is on '
                    'neither roster',
         'supplies': 'Hospital names (Panel C) and states (Panels B, D2)',
         'url': 'https://www.cms.gov/data-research/statistics-trends-'
                'reports/cost-reports',
         'tier': 'A', 'accessed': accessed,
         'powers': ['HCRIS_Ambulance_CostCenters']},
    ]

    # ── facts ──
    facts += [
        {'metric': 'Hospitals reporting an ambulance cost center '
                   '(Worksheet A line 95), latest complete FY',
         'year': LATEST, 'value': n23, 'unit': 'hospitals', 'basis': 'GOV',
         'tier': 'A', 'source_keys': ['hcris_amb_ws_a'],
         'locator': 'Panel A, FY end 2023 row; NMRC A000000/09500 nonzero '
                    'cost, RPT-joined',
         'lives_on': 'HCRIS_Ambulance_CostCenters',
         'cross_check': 'Panel B state counts sum to it (live All-states '
                        'row); share of filers prints beside it'},
        {'metric': 'Share of all 2552-10 filers reporting ambulance cost',
         'year': LATEST,
         'value': round(n23 / filer_counts[LATEST], 4),
         'unit': 'share', 'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['hcris_amb_ws_a'],
         'locator': 'Panel A live formula, FY2023 row (reporters / filers)',
         'lives_on': 'HCRIS_Ambulance_CostCenters',
         'cross_check': 'Stable 14.3-14.6% across all four complete FYs '
                        '2020-2023 in the same panel'},
        {'metric': 'As-filed ambulance cost, all reporting hospitals',
         'year': LATEST, 'value': round(usd23), 'unit': 'USD',
         'basis': 'GOV', 'tier': 'A', 'source_keys': ['hcris_amb_ws_a'],
         'locator': 'Panel A, FY2023 row, column 3 totals as filed',
         'lives_on': 'HCRIS_Ambulance_CostCenters',
         'cross_check': 'Panel B state dollars sum to it (live); gross '
                        'Worksheet A cost before reclasses/adjustments'},
        {'metric': 'Net flow of ambulance cost-center reporters, latest '
                   'complete pair (starts minus stops, 2022 to 2023)',
         'year': LATEST, 'value': len(starts23) - len(stops23),
         'unit': 'hospitals (net entry)', 'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['hcris_amb_ws_a'],
         'locator': 'Panel D live net formula, 2022 -> 2023 row '
                    f'({len(starts23)} starts vs {len(stops23)} stops)',
         'lives_on': 'HCRIS_Ambulance_CostCenters',
         'cross_check': 'Direction REVERSED from 2021 -> 2022 (net -17); '
                        'candidate events, filing-lag caveat in the same '
                        'row'},
        {'metric': 'Footprint-state hospitals reporting ambulance cost '
                   '(NE IA KS MO OH WI VA MN IN KY)',
         'year': LATEST, 'value': fp23, 'unit': 'hospitals',
         'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['hcris_amb_ws_a', 'hcris_amb_roster_join'],
         'locator': 'Panel B footprint subtotal (live SUMIF over the '
                    'FOOTPRINT flag column)',
         'lives_on': 'HCRIS_Ambulance_CostCenters',
         'cross_check': 'Iowa (57) and Minnesota (38) sit 2nd and 3rd '
                        'nationally by count; about 30% of all reporters '
                        'sit in the ten footprint states'},
    ]

    # ── findings ──
    findings += [
        {'id_hint': 61,
         'finding': 'One hospital in seven still runs its own ambulance: '
                    f'{n23:,} of {filer_counts[LATEST]:,} cost-report '
                    'filers (14.3%) reported a Worksheet A line 95 '
                    f'ambulance cost center in FY{LATEST}, about '
                    f'${usd23 / 1e9:.1f}B of as-filed cost, and the share '
                    'has been flat at 14.3-14.6% across every complete FY '
                    '2020-2023 - a stable, small-hospital-and-rural '
                    'franchise (TX, IA, MN lead by count), not a segment '
                    'in visible collapse.',
         'numbers': f"='HCRIS_Ambulance_CostCenters'!D{share_row[LATEST]}",
         'sources': 'hcris_amb_ws_a',
         'confidence': 'High: raw HCRIS extracts, line identity verified '
                       'against the ALPHA cost-center labels in every '
                       'year-file',
         'guardrail': 'Self-reported, unaudited, as-filed cost; line 95 is '
                      'ANY hospital-based ambulance (911 contracts and '
                      'community EMS as much as IFT); the ~30-50 '
                      'reports/year booking ambulance under line 194 '
                      'subscripts make every count a slight floor'},
        {'id_hint': 62,
         'finding': 'The exit story is two-sided, not a wave: measured as '
                    'presence/absence of nonzero line 95 cost between '
                    'consecutive FY end years, 2021 to 2022 ran 46 '
                    'candidate stops against 29 starts (net -17), but 2022 '
                    'to 2023 REVERSED to 47 starts against 40 stops (net '
                    '+7). Hospital ambulance shows steady two-way churn of '
                    'roughly 40-50 hospitals a year in each direction - '
                    'a per-market opportunity list, not a national '
                    'outsourcing tide.',
         'numbers': f"='HCRIS_Ambulance_CostCenters'!D{net_row[(2022, 2023)]}",
         'sources': 'hcris_amb_ws_a',
         'confidence': 'Medium-high on the counts; low on attributing any '
                       'single stop to outsourcing',
         'guardrail': 'Candidate events only: a stop can be a fiscal-year '
                      'filing lag, late/amended report, closure, CCN '
                      'merger or relabeled cost center - and fy_end 2024 '
                      'is too lag-incomplete to extend the series; '
                      'corroborate individual hospitals before acting'},
    ]

    return {'facts': facts, 'sources': sources, 'excluded': excluded,
            'findings': findings,
            'meta': {'fy_latest_complete': LATEST,
                     'rows_cached': len(rows),
                     'verified_lines': sorted(lines_seen),
                     'reporters_by_fy': {fy: len(byfy[fy])
                                         for fy in SHOW_YEARS},
                     'state_fallback_ccns': fallback_n[0]}}
