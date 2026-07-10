"""Group S (pull-backed) — QCEW EMS industry series + the facility O/D universe."""
import json
import os

SHEETS = [
    {'name': 'QCEW_EMS_Employment', 'tab_color': 'FF1F6F8B'},
    {'name': 'Facility_Universe_State', 'tab_color': 'FF1F6F8B'},
]

OWN = {'1': 'Federal government', '2': 'State government', '3': 'Local government',
       '5': 'Private'}

FIPS_STATE = {
    '01': 'Alabama', '02': 'Alaska', '04': 'Arizona', '05': 'Arkansas',
    '06': 'California', '08': 'Colorado', '09': 'Connecticut', '10': 'Delaware',
    '11': 'District of Columbia', '12': 'Florida', '13': 'Georgia', '15': 'Hawaii',
    '16': 'Idaho', '17': 'Illinois', '18': 'Indiana', '19': 'Iowa', '20': 'Kansas',
    '21': 'Kentucky', '22': 'Louisiana', '23': 'Maine', '24': 'Maryland',
    '25': 'Massachusetts', '26': 'Michigan', '27': 'Minnesota', '28': 'Mississippi',
    '29': 'Missouri', '30': 'Montana', '31': 'Nebraska', '32': 'Nevada',
    '33': 'New Hampshire', '34': 'New Jersey', '35': 'New Mexico', '36': 'New York',
    '37': 'North Carolina', '38': 'North Dakota', '39': 'Ohio', '40': 'Oklahoma',
    '41': 'Oregon', '42': 'Pennsylvania', '44': 'Rhode Island', '45': 'South Carolina',
    '46': 'South Dakota', '47': 'Tennessee', '48': 'Texas', '49': 'Utah',
    '50': 'Vermont', '51': 'Virginia', '53': 'Washington', '54': 'West Virginia',
    '55': 'Wisconsin', '56': 'Wyoming', '72': 'Puerto Rico', '78': 'Virgin Islands'}


def _load(cache, key):
    return json.load(open(os.path.join(cache, key + '.json')))


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def build(wb, ctx):
    lib, cache = ctx['lib'], ctx['cache']
    facts, sources, excluded = [], [], []

    sources += [
        {'key': 'qcew_621910', 'publisher': 'BLS',
         'document': 'Quarterly Census of Employment and Wages (QCEW), NAICS 621910 '
                     'Ambulance Services',
         'vintage': 'Annual averages 2014-2025',
         'locator': 'Open-data CSV slices, /cew/data/api/{year}/a/industry/621910.csv; '
                    'US000 national rows by ownership + statewide rollups',
         'supplies': 'Establishments, employment, total wages and average annual pay '
                     'for the ambulance industry - the measured labor-cost series',
         'url': 'https://www.bls.gov/cew/downloadable-data-files.htm',
         'tier': 'A', 'accessed': '10 Jul 2026', 'powers': ['QCEW_EMS_Employment']},
        {'key': 'pdc_universe', 'publisher': 'CMS',
         'document': 'Provider Data Catalog (Care Compare): Hospital General '
                     'Information; Nursing Home Provider Info; Dialysis Facilities; '
                     'IRF, LTCH, Hospice General Information; Home Health Agencies',
         'vintage': 'Current snapshots, accessed 10 Jul 2026',
         'locator': 'DKAN datastore queries (dataset ids xubh-q36u, 4pq5-n9py, '
                    '23ew-n7w9, 7t8x-u3ir, azum-44iv, yc9t-dgbk, 6jpm-sxkc)',
         'supplies': 'The certified facility universe that originates and receives '
                     'interfacility transfers, by state, with emergency-service flags, '
                     'ownership and certified beds',
         'url': 'https://data.cms.gov/provider-data/',
         'tier': 'A', 'accessed': '10 Jul 2026', 'powers': ['Facility_Universe_State']},
    ]

    # ══ QCEW_EMS_Employment ═══════════════════════════════════════════════
    years = []
    nat = {}     # (year, own) -> row
    state = {}   # (year, fips) -> private row
    for yr in range(2014, 2026):
        try:
            rows = _load(cache, f'qcew_621910_{yr}')
        except FileNotFoundError:
            continue
        years.append(yr)
        for r in rows:
            if r['area_fips'] == 'US000':
                nat[(yr, r['own_code'])] = r
            elif r.get('own_code') == '5':
                state[(yr, r['area_fips'][:2])] = r
    ws = wb.create_sheet('QCEW_EMS_Employment')
    sb = lib.SheetBuilder(ws, 9, col_widths=[8, 20, 13, 13, 16, 13, 8, 13, 13],
                          tab_color='FF1F6F8B')
    sb.title('The ambulance industry labor base: BLS QCEW NAICS 621910, 2014-2025')
    sb.subtitle('The question: how many ambulance employers and workers exist, and '
                'what does the industry pay - measured by unemployment-insurance '
                'records, the census of employers? NAICS 621910 = Ambulance Services '
                '(private and government-run units filing UI). Crew labor is ~69.4% '
                'of ground ambulance cost (GADCS, Cost_and_Capacity), so this wage '
                'series is the cost-inflation instrument. Annual averages; no '
                'sampling. 2025 is preliminary until the Q4 final revision.')
    sb.blank()
    sb.banner('Panel A. National, by ownership, annual averages')
    sb.headers(['Year', 'Ownership', 'Establishments', 'Employment',
                'Total annual wages $', 'Avg annual pay $'])
    a0 = sb.r + 1
    for yr in years:
        for own in ('5', '3', '2', '1'):
            r = nat.get((yr, own))
            if not r:
                continue
            sb.row([(yr, 'src'), OWN[own],
                    (_f(r['annual_avg_estabs']), 'src', lib.FMT_INT),
                    (_f(r['annual_avg_emplvl']), 'src', lib.FMT_INT),
                    (_f(r['total_annual_wages']), 'src', lib.FMT_USD),
                    (_f(r['avg_annual_pay']), 'src', lib.FMT_USD)])
    a1 = sb.r
    sb.blank()
    sb.banner('Panel B. Private ambulance services (ownership 5): the series')
    sb.headers(['Year', 'Establishments', 'Employment', 'Avg annual pay $',
                'Pay growth YoY', 'Ambulance Inflation Factor that year (link)'])
    b0 = sb.r + 1
    aif = {2020: 0.9, 2021: 0.2, 2022: 5.1, 2023: 8.7, 2024: 2.6, 2025: 2.4}
    for i, yr in enumerate(years):
        row_n = sb.r + 1
        sb.row([(yr, 'fml'),
                (f'=SUMIFS($C${a0}:$C${a1},$A${a0}:$A${a1},$A{row_n},'
                 f'$B${a0}:$B${a1},"Private")', 'fml', lib.FMT_INT),
                (f'=SUMIFS($D${a0}:$D${a1},$A${a0}:$A${a1},$A{row_n},'
                 f'$B${a0}:$B${a1},"Private")', 'fml', lib.FMT_INT),
                (f'=SUMIFS($F${a0}:$F${a1},$A${a0}:$A${a1},$A{row_n},'
                 f'$B${a0}:$B${a1},"Private")', 'fml', lib.FMT_USD),
                (f'=IF(A{row_n}={years[0]},"n/a",D{row_n}/D{row_n - 1}-1)', 'fml',
                 lib.FMT_PCT1),
                ((f'{aif[yr]}% (Payment_Rules)', 'link') if yr in aif else None)])
    b1 = sb.r
    n = len(years) - 1
    sb.row([('CAGR (full window)', 'label'),
            (lib.cagr_formula(f'B{b1}', f'B{b0}', n), 'fml', lib.FMT_PCT2),
            (lib.cagr_formula(f'C{b1}', f'C{b0}', n), 'fml', lib.FMT_PCT2),
            (lib.cagr_formula(f'D{b1}', f'D{b0}', n), 'fml', lib.FMT_PCT2)])
    sb.note('The wage-vs-payment scissors: private ambulance average pay compounds '
            'faster than the Ambulance Inflation Factor in most years (compare '
            'Payment_Rules) - the measured margin-compression mechanism. Government-'
            'run services filing under public ownership are in Panel A rows 2/3; '
            'volunteer labor never appears in UI records (Workforce_Supply caveat).')
    lib.add_chart(ws, f'H{b0}', 'Private ambulance employment, 2014-2025',
                  f'QCEW_EMS_Employment!$A${b0}:$A${b1}',
                  [('Employment', f'QCEW_EMS_Employment!$C${b0}:$C${b1}')],
                  kind='line', y_fmt='#,##0')
    lib.add_chart(ws, f'H{b0 + 14}', 'Average annual pay, private ambulance services',
                  f'QCEW_EMS_Employment!$A${b0}:$A${b1}',
                  [('Avg annual pay', f'QCEW_EMS_Employment!$D${b0}:$D${b1}')],
                  kind='line', y_fmt='$#,##0')
    # Panel C: states, latest year
    latest = years[-1] if years else None
    have_states = sorted((f, r) for (yr, f), r in state.items() if yr == latest)
    if have_states:
        sb.blank()
        sb.banner(f'Panel C. Private ambulance services by state, {latest} annual averages')
        sb.headers(['State', 'FIPS', 'Establishments', 'Employment',
                    'Total annual wages $', 'Avg annual pay $'])
        c0 = sb.r + 1
        for fips, r in have_states:
            sb.row([(FIPS_STATE.get(fips, fips), 'src'), (fips, 'src'),
                    (_f(r['annual_avg_estabs']), 'src', lib.FMT_INT),
                    (_f(r['annual_avg_emplvl']), 'src', lib.FMT_INT),
                    (_f(r['total_annual_wages']), 'src', lib.FMT_USD),
                    (_f(r['avg_annual_pay']), 'src', lib.FMT_USD)])
        c1 = sb.r
        lib.add_chart(ws, f'H{b0 + 28}', f'Private ambulance employment by state, {latest}',
                      f'QCEW_EMS_Employment!$A${c0}:$A${c1}',
                      [('Employment', f'QCEW_EMS_Employment!$D${c0}:$D${c1}')],
                      kind='bar', height=18)
    if (2024, '5') in nat:
        facts += [
            {'metric': 'Private ambulance services employment (QCEW annual average)',
             'year': 2024, 'value': _f(nat[(2024, '5')]['annual_avg_emplvl']),
             'unit': 'jobs', 'basis': 'GOV', 'tier': 'A', 'source_keys': ['qcew_621910'],
             'locator': 'QCEW NAICS 621910, US000, ownership 5, 2024 annual average',
             'lives_on': 'QCEW_EMS_Employment',
             'cross_check': 'Companion to the OEWS-based Workforce_Supply tab '
                            '(occupation vs industry basis; do not mix)'},
            {'metric': 'Private ambulance establishments', 'year': 2024,
             'value': _f(nat[(2024, '5')]['annual_avg_estabs']), 'unit': 'establishments',
             'basis': 'GOV', 'tier': 'A', 'source_keys': ['qcew_621910'],
             'locator': 'QCEW NAICS 621910, US000, ownership 5, 2024',
             'lives_on': 'QCEW_EMS_Employment',
             'cross_check': 'An establishment is a worksite, not a company: compare '
                            '10,465 PECOS-enrolled suppliers and 8,721 billing NPIs '
                            '(Supplier_Landscape) - three different units'},
            {'metric': 'Private ambulance avg annual pay', 'year': 2024,
             'value': _f(nat[(2024, '5')]['avg_annual_pay']), 'unit': '$/yr',
             'basis': 'GOV', 'tier': 'A', 'source_keys': ['qcew_621910'],
             'locator': 'QCEW NAICS 621910, US000, ownership 5, 2024',
             'lives_on': 'QCEW_EMS_Employment',
             'cross_check': 'Pay CAGR vs AIF: the scissors carried on this tab'},
        ]

    # ══ Facility_Universe_State ═══════════════════════════════════════════
    classes = [
        ('pdc_hospitals', 'Hospitals'), ('pdc_nursing_homes', 'Nursing homes (SNF)'),
        ('pdc_dialysis', 'Dialysis facilities'), ('pdc_irf', 'IRF'),
        ('pdc_ltch', 'LTCH'), ('pdc_hospice', 'Hospices'),
        ('pdc_home_health', 'Home health agencies'),
    ]
    counts = {}
    er_counts = {}
    beds = {}
    n_class = {}
    for key, label in classes:
        try:
            rows = _load(cache, key)
        except FileNotFoundError:
            continue
        n_class[label] = len(rows)
        for r in rows:
            s = (r.get('state') or '').strip()
            if not s:
                continue
            counts[(s, label)] = counts.get((s, label), 0) + 1
            if key == 'pdc_hospitals' and (r.get('emergency_services') or '').lower() == 'yes':
                er_counts[s] = er_counts.get(s, 0) + 1
            if key == 'pdc_nursing_homes':
                b = _f(r.get('number_of_certified_beds'))
                if b:
                    beds[s] = beds.get(s, 0) + b
    states = sorted({s for s, _ in counts})
    ws = wb.create_sheet('Facility_Universe_State')
    sb = lib.SheetBuilder(ws, 11, col_widths=[7, 10, 12, 10, 13, 7, 7, 9, 12, 13, 12],
                          tab_color='FF1F6F8B')
    sb.title('The facility universe that sends and receives transfers, by state')
    sb.subtitle('The question: how many certified facilities of each class exist in '
                'each state - the physical origin/destination nodes of interfacility '
                'transport? Source: CMS Provider Data Catalog (Care Compare) current '
                'snapshots, accessed 10 Jul 2026 (dataset ids on Pull_Manifest). '
                'These are Medicare/Medicaid-certified facilities; cash-only and '
                'tribal facilities outside certification are not counted.')
    sb.blank()
    sb.banner('Panel A. Certified facilities by state and class (current snapshots)')
    sb.headers(['State', 'Hospitals', 'Hospitals w/ emergency services',
                'Nursing homes (SNF)', 'SNF certified beds', 'IRF', 'LTCH',
                'Hospices', 'Home health agencies', 'Dialysis facilities',
                'Post-acute + dialysis total'])
    a0f = sb.r + 1
    for s in states:
        row_n = sb.r + 1
        sb.row([(s, 'src'),
                (counts.get((s, 'Hospitals'), 0), 'src', lib.FMT_INT),
                (er_counts.get(s, 0), 'src', lib.FMT_INT),
                (counts.get((s, 'Nursing homes (SNF)'), 0), 'src', lib.FMT_INT),
                (beds.get(s), 'src', lib.FMT_INT),
                (counts.get((s, 'IRF'), 0), 'src', lib.FMT_INT),
                (counts.get((s, 'LTCH'), 0), 'src', lib.FMT_INT),
                (counts.get((s, 'Hospices'), 0), 'src', lib.FMT_INT),
                (counts.get((s, 'Home health agencies'), 0), 'src', lib.FMT_INT),
                (counts.get((s, 'Dialysis facilities'), 0), 'src', lib.FMT_INT),
                (f'=D{row_n}+F{row_n}+G{row_n}+H{row_n}+I{row_n}+J{row_n}', 'fml',
                 lib.FMT_INT)])
    a1f = sb.r
    tr = sb.r + 1
    sb.row([('US total', 'label')] +
           [(f'=SUM({c}{a0f}:{c}{a1f})', 'fml', lib.FMT_INT)
            for c in 'BCDEFGHIJK'])
    sb.note('Row counts per dataset at access: ' +
            '; '.join(f'{label} {n_class.get(label, 0):,}' for _, label in classes) +
            '. SNF certified beds summed from the provider file. The 35,481 post-'
            'acute destination count on Post_Acute_Supply_State uses the same CMS '
            'provider files at an earlier vintage - snapshot dates differ and both '
            'are stated.')
    lib.add_chart(ws, f'M{a0f}', 'Hospitals and SNFs by state (top of table)',
                  f'Facility_Universe_State!$A${a0f}:$A${a1f}',
                  [('Hospitals', f'Facility_Universe_State!$B${a0f}:$B${a1f}'),
                   ('SNFs', f'Facility_Universe_State!$D${a0f}:$D${a1f}')],
                  kind='bar', height=18)
    facts += [
        {'metric': 'Certified hospitals (Care Compare universe)', 'year': 2026,
         'value_ref': f'Facility_Universe_State!B{tr}', 'unit': 'facilities',
         'basis': 'DERIVED', 'tier': 'A', 'source_keys': ['pdc_universe'],
         'locator': 'Hospital General Information snapshot, sum over states',
         'lives_on': 'Facility_Universe_State',
         'cross_check': 'AHA counts ~6,100 hospitals total / ~5,200 community '
                        '(Demand_Drivers): AHA includes non-Medicare-certified and '
                        'federal units - different universes, both stated'},
        {'metric': 'SNF certified beds (Care Compare universe)', 'year': 2026,
         'value_ref': f'Facility_Universe_State!E{tr}', 'unit': 'beds',
         'basis': 'DERIVED', 'tier': 'A', 'source_keys': ['pdc_universe'],
         'locator': 'Nursing Home Provider Info, number_of_certified_beds summed',
         'lives_on': 'Facility_Universe_State',
         'cross_check': 'The SNF interface is 2.75x the hospital-to-hospital Medicare '
                        'book (Medicare_OD_Matrix): this is the bed base behind it'},
    ]

    return {'facts': facts, 'sources': sources, 'excluded': excluded,
            'meta': {'row_counts': {s['name']: wb[s['name']].max_row for s in SHEETS},
                     'notes': f'QCEW years: {years}; state rows present: '
                              f'{bool(have_states)}'}}
