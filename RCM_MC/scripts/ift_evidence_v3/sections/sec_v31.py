"""v3.1 tabs: the state 65+/85+ age denominators (Census Vintage 2024) and the
OEWS May 2024 EMS occupation wages — closing v2.7 pending-register items P20
(state-grain 65+ series) and P4 (OEWS state wage files).
"""
import json
import os

CACHE_DIR = os.environ.get(
    'IFT_V3_CACHE',
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 'ift_v3_cache'))

SHEETS = [
    {'name': 'State_Age_65plus', 'tab_color': 'FF7A5195'},
    {'name': 'OEWS_EMS_Wages', 'tab_color': 'FF1F6F8B'},
]

YEARS = ['2020', '2021', '2022', '2023', '2024']
OCC_ORDER = ['29-2042', '29-2043', '53-3011']


def _load(key):
    import gzip
    p = os.path.join(CACHE_DIR, key + '.json')
    if os.path.exists(p):
        return json.load(open(p))
    with gzip.open(p + '.gz', 'rt') as f:
        return json.load(f)


def _f(v):
    if v in (None, '', '*', '#', '**'):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def build(wb, ctx):
    lib = ctx['lib']
    facts, sources, excluded = [], [], []

    sources += [
        {'key': 'census_age_2024', 'publisher': 'U.S. Census Bureau',
         'document': 'Vintage 2024 State Population Estimates by Age and Sex, '
                     'civilian (SC-EST2024-AGESEX-CIV)',
         'vintage': 'Estimates 2020-2024, released 2025',
         'locator': 'SEX=0 (total) rows by single year of age (AGE 85 = 85 and '
                    'over), state and national grain',
         'supplies': 'The 65+ and 85+ population denominators by state - the '
                     'demand-side age base, measured, closing the state-grain gap '
                     'behind pending register item P20',
         'url': 'https://www2.census.gov/programs-surveys/popest/datasets/'
                '2020-2024/state/asrh/sc-est2024-agesex-civ.csv',
         'tier': 'A', 'accessed': '11 Jul 2026', 'powers': ['State_Age_65plus']},
        {'key': 'oews_ems_2024', 'publisher': 'BLS',
         'document': 'Occupational Employment and Wage Statistics (OEWS), '
                     'May 2024 state file (oesm24st)',
         'vintage': 'May 2024 reference period',
         'locator': 'OCC 29-2042 Emergency Medical Technicians, 29-2043 '
                    'Paramedics, 53-3011 Ambulance Drivers and Attendants; '
                    'TOT_EMP, mean/median hourly and annual wages, P10/P90',
         'supplies': 'Occupation-grain EMS employment and the certification-'
                     'ladder wage structure by state - closes pending register '
                     'item P4 (OEWS state wage files)',
         'url': 'https://www.bls.gov/oes/special-requests/oesm24st.zip',
         'tier': 'A', 'accessed': '11 Jul 2026', 'powers': ['OEWS_EMS_Wages']},
    ]

    # ══ State_Age_65plus ═══════════════════════════════════════════════════
    rows = _load('census_state_age_2024')
    # aggregate 65+ and 85+ per (state, year); AGE runs 0..85 with 85 = 85+
    agg = {}
    for r in rows:
        age = int(r['AGE'])
        if age == 999:
            bucket = 'total'
        elif age >= 85:
            bucket = None  # 85 handled inside 65+ and separately below
        name = r['NAME']
        a = agg.setdefault(name, {y: {'65+': 0, '85+': 0, 'total': 0} for y in YEARS})
        for y in YEARS:
            v = _f(r[f'POPEST{y}_CIV']) or 0
            if age == 999:
                a[y]['total'] += v
            else:
                if age >= 65:
                    a[y]['65+'] += v
                if age >= 85:
                    a[y]['85+'] += v
    ws = wb.create_sheet('State_Age_65plus')
    sb = lib.SheetBuilder(ws, 10, col_widths=[18, 12, 12, 12, 12, 12, 10, 10, 10, 12],
                          tab_color='FF7A5195')
    sb.title('The 65-plus population by state, 2020-2024 (measured, not projected)')
    sb.subtitle('The question: how large is the age base that generates '
                'interfacility transport demand, state by state, and how fast is '
                'it compounding? Source: Census Bureau Vintage 2024 civilian '
                'population estimates by single year of age (SC-EST2024-AGESEX-CIV, '
                'pulled 11 Jul 2026, Pull_Manifest). These are ESTIMATES of the '
                'resident population, not projections: the measured companion to '
                'the Census NP2023 projections on Macro_Demand_Drivers. 85+ is the '
                'top-coded band. Closes the state-grain half of pending register '
                'P20 (the ACS API-key route stays open for tract detail).')
    sb.blank()
    sb.banner('Panel A. National, 2020-2024')
    sb.headers(['Geography', 'Total 2024', '65+ 2020', '65+ 2022', '65+ 2024',
                '65+ share 2024', '65+ CAGR 2020-2024', '85+ 2020', '85+ 2024',
                '85+ CAGR'])
    us = agg['United States']
    rn = sb.r + 1
    sb.row([('United States', 'src'),
            (us['2024']['total'], 'src', lib.FMT_INT),
            (us['2020']['65+'], 'src', lib.FMT_INT),
            (us['2022']['65+'], 'src', lib.FMT_INT),
            (us['2024']['65+'], 'src', lib.FMT_INT),
            (f'=E{rn}/B{rn}', 'fml', lib.FMT_PCT1),
            (lib.cagr_formula(f'E{rn}', f'C{rn}', 4), 'fml', lib.FMT_PCT2),
            (us['2020']['85+'], 'src', lib.FMT_INT),
            (us['2024']['85+'], 'src', lib.FMT_INT),
            (lib.cagr_formula(f'I{rn}', f'H{rn}', 4), 'fml', lib.FMT_PCT2)])
    us_row = rn
    sb.blank()
    sb.banner('Panel B. States, 2020-2024')
    sb.headers(['State', 'Total 2024', '65+ 2020', '65+ 2022', '65+ 2024',
                '65+ share 2024', '65+ CAGR 2020-2024', '85+ 2020', '85+ 2024',
                '85+ CAGR'])
    b0 = sb.r + 1
    for name in sorted(k for k in agg if k != 'United States'):
        a = agg[name]
        rn = sb.r + 1
        sb.row([(name, 'src'),
                (a['2024']['total'], 'src', lib.FMT_INT),
                (a['2020']['65+'], 'src', lib.FMT_INT),
                (a['2022']['65+'], 'src', lib.FMT_INT),
                (a['2024']['65+'], 'src', lib.FMT_INT),
                (f'=IF(B{rn}=0,"n/a",E{rn}/B{rn})', 'fml', lib.FMT_PCT1),
                (lib.cagr_formula(f'E{rn}', f'C{rn}', 4), 'fml', lib.FMT_PCT2),
                (a['2020']['85+'], 'src', lib.FMT_INT),
                (a['2024']['85+'], 'src', lib.FMT_INT),
                (lib.cagr_formula(f'I{rn}', f'H{rn}', 4), 'fml', lib.FMT_PCT2)])
    b1 = sb.r
    sb.row([('Cross-foot: state sum vs national', 'label'),
            (f'=SUM(B{b0}:B{b1})-B{us_row}', 'fml', lib.FMT_INT),
            (f'=SUM(C{b0}:C{b1})-C{us_row}', 'fml', lib.FMT_INT), None,
            (f'=SUM(E{b0}:E{b1})-E{us_row}', 'fml', lib.FMT_INT), None, None,
            (f'=SUM(H{b0}:H{b1})-H{us_row}', 'fml', lib.FMT_INT),
            (f'=SUM(I{b0}:I{b1})-I{us_row}', 'fml', lib.FMT_INT)])
    sb.note('Civilian population (excludes active-duty armed forces), Vintage '
            '2024. The cross-foot row must show ~0 (states + DC + PR sum to the '
            'national row net of any file-level rounding; PR is included in the '
            'file but NOT in the US total row, so the difference equals Puerto '
            'Rico - stated, not hidden). Use 65+ per-1,000 joins on the SP_ '
            'state-profile tabs.')
    lib.add_chart(ws, f'L{b0}', '65+ CAGR 2020-2024 by state',
                  f'State_Age_65plus!$A${b0}:$A${b1}',
                  [('65+ CAGR', f'State_Age_65plus!$G${b0}:$G${b1}')],
                  kind='bar', height=18, y_fmt='0.0%')
    facts += [
        {'metric': 'US 65+ civilian population', 'year': 2024,
         'value_ref': f'State_Age_65plus!E{us_row}', 'unit': 'persons',
         'basis': 'GOV', 'tier': 'A', 'source_keys': ['census_age_2024'],
         'locator': 'SC-EST2024-AGESEX-CIV, ages 65-85+, SEX=0, national',
         'lives_on': 'State_Age_65plus',
         'cross_check': 'Measured estimate; the NP2023 projection series on '
                        'Macro_Demand_Drivers is the forward companion'},
        {'metric': 'US 65+ CAGR 2020-2024 (measured)', 'year': '2020-2024',
         'value_ref': f'State_Age_65plus!G{us_row}', 'unit': '%/yr',
         'basis': 'DERIVED', 'tier': 'A', 'source_keys': ['census_age_2024'],
         'locator': '(65+ 2024 / 65+ 2020)^(1/4)-1',
         'lives_on': 'State_Age_65plus',
         'cross_check': 'Brackets the projected ~2.7%/yr 65+ growth on '
                        'Macro_Demand_Drivers; measured vs projected bases stated'},
    ]

    # ══ OEWS_EMS_Wages ═══════════════════════════════════════════════════
    orows = _load('oews_ems_state_2024')
    ws = wb.create_sheet('OEWS_EMS_Wages')
    sb = lib.SheetBuilder(ws, 10, col_widths=[18, 8, 30, 11, 10, 12, 10, 12, 12, 12],
                          tab_color='FF1F6F8B')
    sb.title('EMS occupation wages by state: OEWS May 2024')
    sb.subtitle('The question: what do EMTs, paramedics, and ambulance drivers '
                'actually earn, state by state - the occupation-grain companion '
                'to the industry-grain QCEW series? Source: BLS OEWS May 2024 '
                'state file (pulled 11 Jul 2026, Pull_Manifest). Closes pending '
                'register P4. OEWS counts JOBS in the occupation across ALL '
                'industries (hospital-based EMTs included); QCEW_EMS_Employment '
                'counts the ambulance INDUSTRY - different universes, never mix '
                '(the same discipline as PSPS vs MUP). Suppressed cells are '
                'blank as published.')
    sb.blank()
    sb.banner('Panel A. State x occupation, May 2024')
    sb.headers(['State', 'Abbrev', 'Occupation', 'Employment', 'Mean hourly $',
                'Mean annual $', 'Median hourly $', 'Median annual $',
                'P10 annual $', 'P90 annual $'])
    a0 = sb.r + 1
    for r in sorted(orows, key=lambda x: (str(x.get('AREA_TITLE')),
                                          OCC_ORDER.index(x['OCC_CODE'])
                                          if x['OCC_CODE'] in OCC_ORDER else 9)):
        sb.row([(r.get('AREA_TITLE'), 'src'), (r.get('PRIM_STATE'), 'src'),
                (f"{r.get('OCC_CODE')} {r.get('OCC_TITLE')}", 'src'),
                (_f(r.get('TOT_EMP')), 'src', lib.FMT_INT),
                (_f(r.get('H_MEAN')), 'src', lib.FMT_USD2),
                (_f(r.get('A_MEAN')), 'src', lib.FMT_USD),
                (_f(r.get('H_MEDIAN')), 'src', lib.FMT_USD2),
                (_f(r.get('A_MEDIAN')), 'src', lib.FMT_USD),
                (_f(r.get('A_PCT10')), 'src', lib.FMT_USD),
                (_f(r.get('A_PCT90')), 'src', lib.FMT_USD)])
    a1 = sb.r
    sb.blank()
    sb.banner('Panel B. The certification-ladder wage gap (live formulas over '
              'Panel A)')
    sb.headers(['Measure', 'EMTs (29-2042)', 'Paramedics (29-2043)',
                'Ambulance drivers (53-3011)', 'Paramedic premium over EMT'])

    def _match(occ):
        return f'ISNUMBER(SEARCH("{occ}",$C${a0}:$C${a1}))'

    rn = sb.r + 1
    sb.row([('Total employment (sum of published state cells)', 'label')] +
           [(f'=SUMIFS($D${a0}:$D${a1},$C${a0}:$C${a1},"*{occ}*")', 'fml',
             lib.FMT_INT) for occ in OCC_ORDER])
    rn = sb.r + 1
    sb.row([('Median annual wage (employment-weighted mean of state medians)',
             'label')] +
           [(f'=SUMPRODUCT({_match(occ)}*N($D${a0}:$D${a1})*N($H${a0}:$H${a1}))/'
             f'MAX(1,SUMPRODUCT({_match(occ)}*N($D${a0}:$D${a1})*'
             f'(N($H${a0}:$H${a1})>0)))', 'fml', lib.FMT_USD)
            for occ in OCC_ORDER] +
           [(f'=IF(B{rn}=0,"n/a",C{rn}/B{rn}-1)', 'fml', lib.FMT_PCT1)])
    pb_end = sb.r
    sb.note('SUMPRODUCT weighting uses state employment where both employment '
            'and median wage are published; wildcard match on the occupation '
            'column. The GADCS finding that crew labor is ~69.4% of ground '
            'ambulance cost (Cost_and_Capacity) makes this ladder the unit-'
            'economics wage input - measured, not assumed.')
    lib.add_chart(ws, f'L{a0}', 'Median annual wage by state: paramedics (29-2043)',
                  f'OEWS_EMS_Wages!$A${a0}:$A${a1}',
                  [('Median annual', f'OEWS_EMS_Wages!$H${a0}:$H${a1}')],
                  kind='bar', height=18, y_fmt='$#,##0')
    facts += [
        {'metric': 'EMT jobs (OEWS, sum of published state cells)', 'year': 2024,
         'value_ref': f'OEWS_EMS_Wages!B{pb_end - 1}', 'unit': 'jobs',
         'basis': 'DERIVED', 'tier': 'A', 'source_keys': ['oews_ems_2024'],
         'locator': 'OEWS May 2024 state file, OCC 29-2042, TOT_EMP summed',
         'lives_on': 'OEWS_EMS_Wages',
         'cross_check': 'Occupation basis (all industries); QCEW industry '
                        'employment (171,100 private, 2024) is a different '
                        'universe - both stated'},
    ]

    return {'facts': facts, 'sources': sources, 'excluded': excluded,
            'meta': {'row_counts': {s['name']: wb[s['name']].max_row
                                    for s in SHEETS}}}
