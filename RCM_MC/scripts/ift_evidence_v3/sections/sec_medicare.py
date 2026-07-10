"""Group M — Medicare claims depth: five tabs built from the v3 live pulls.

Every value cell is a blue dataset extraction (Tier A: pulled from the primary
CMS/BLS API by the committed pipeline, manifest on Pull_Manifest) or a black
live formula. No modeled numbers.
"""
import json
import os

CODES = ['A0425', 'A0426', 'A0427', 'A0428', 'A0429', 'A0430', 'A0431', 'A0432',
         'A0433', 'A0434', 'A0435', 'A0436']
GROUND_BASE = ['A0426', 'A0427', 'A0428', 'A0429', 'A0433', 'A0434']
PSPS_CODES = ['A0425', 'A0426', 'A0427', 'A0428', 'A0429', 'A0433', 'A0434']
CODE_LABEL = {
    'A0425': 'Ground mileage (per mile)', 'A0426': 'ALS1 non-emergency',
    'A0427': 'ALS1 emergency', 'A0428': 'BLS non-emergency',
    'A0429': 'BLS emergency', 'A0430': 'Fixed-wing air', 'A0431': 'Rotary-wing air',
    'A0432': 'Paramedic intercept', 'A0433': 'ALS2', 'A0434': 'Specialty care transport',
    'A0435': 'Fixed-wing mileage', 'A0436': 'Rotary mileage'}

SHEETS = [
    {'name': 'Enrollment_ESRD_State', 'tab_color': 'FF1F6F8B'},
    {'name': 'MUP_Ambulance_National', 'tab_color': 'FF1F6F8B'},
    {'name': 'MUP_Ambulance_State', 'tab_color': 'FF1F6F8B'},
    {'name': 'PSPS_Denial_Series', 'tab_color': 'FF1F6F8B'},
    {'name': 'Market_Saturation_Ambulance', 'tab_color': 'FF1F6F8B'},
]


def _f(v):
    if v in (None, ''):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _i(v):
    f = _f(v)
    return int(f) if f is not None and f == int(f) else f


def _load(cache, key):
    return json.load(open(os.path.join(cache, key + '.json')))


def build(wb, ctx):
    lib, cache = ctx['lib'], ctx['cache']
    facts, sources, excluded = [], [], []

    sources += [
        {'key': 'mup_geo', 'publisher': 'CMS',
         'document': 'Medicare Physician & Other Practitioners - by Geography and Service',
         'vintage': 'Data years 2013-2024 (12 annual API versions)',
         'locator': 'Ambulance HCPCS A0425-A0436; National and State grain; '
                    'Tot_Rndrng_Prvdrs, Tot_Benes, Tot_Srvcs, Avg_Sbmtd_Chrg, '
                    'Avg_Mdcr_Alowd_Amt, Avg_Mdcr_Pymt_Amt',
         'supplies': 'Final-action Medicare FFS ambulance utilization, allowed and '
                     'paid averages, and rendering-provider counts by code and state',
         'url': 'https://data.cms.gov/provider-summary-by-type-of-service/medicare-physician-other-practitioners/medicare-physician-other-practitioners-by-geography-and-service',
         'tier': 'A', 'accessed': '10 Jul 2026',
         'powers': ['MUP_Ambulance_National', 'MUP_Ambulance_State']},
        {'key': 'psps_v3', 'publisher': 'CMS',
         'document': 'Physician/Supplier Procedure Summary (PSPS)',
         'vintage': 'Data years 2010-2024 (15 annual API versions)',
         'locator': 'Ambulance base + ground mileage HCPCS; submitted vs denied '
                    'service counts and charge/allowed amounts, by initial O/D modifier',
         'supplies': 'The denial-rate series and the submitted-vs-allowed wedge, '
                     'by code and origin-destination pair',
         'url': 'https://data.cms.gov/summary-statistics-on-use-and-payments/physiciansupplier-procedure-summary',
         'tier': 'A', 'accessed': '10 Jul 2026', 'powers': ['PSPS_Denial_Series']},
        {'key': 'marketsat', 'publisher': 'CMS',
         'document': 'Market Saturation & Utilization State-County',
         'vintage': '15 rolling 12-month reference periods, 2020-2025',
         'locator': 'Type of service = Ambulance (Emergency & Non-Emergency / '
                    'Emergency / Non-Emergency); nation, state and county grain',
         'supplies': 'FFS ambulance provider counts, users, beneficiaries and total '
                     'payment by geography and period; the county supply-density base',
         'url': 'https://data.cms.gov/summary-statistics-on-use-and-payments/program-integrity-market-saturation-by-type-of-service/market-saturation-utilization-state-county',
         'tier': 'A', 'accessed': '10 Jul 2026',
         'powers': ['Market_Saturation_Ambulance']},
        {'key': 'enroll_monthly', 'publisher': 'CMS',
         'document': 'Medicare Monthly Enrollment',
         'vintage': 'Calendar years 2013-2025 (MONTH=Year rows)',
         'locator': 'BENE_GEO_LVL National and State; TOT_BENES, ORGNL_MDCR_BENES, '
                    'MA_AND_OTH_BENES, AGED_ESRD_BENES, DSBLD_ESRD_AND_ESRD_ONLY_BENES',
         'supplies': 'Enrollment denominators: total, Original Medicare, MA & other, '
                     'and the ESRD populations that generate dialysis transport',
         'url': 'https://data.cms.gov/summary-statistics-on-beneficiary-enrollment/medicare-and-medicaid-reports/medicare-monthly-enrollment',
         'tier': 'A', 'accessed': '10 Jul 2026',
         'powers': ['Enrollment_ESRD_State', 'MUP_Ambulance_State']},
    ]

    # ══ Enrollment_ESRD_State ══════════════════════════════════════════════
    nat = sorted(_load(cache, 'enrollment_national_year'), key=lambda r: r['YEAR'])
    st = _load(cache, 'enrollment_state_year')
    ws = wb.create_sheet('Enrollment_ESRD_State')
    sb = lib.SheetBuilder(ws, 9, col_widths=[16, 8, 13, 13, 13, 10, 12, 13, 13],
                         tab_color='FF1F6F8B')
    sb.title('Medicare enrollment denominators and the ESRD population, 2013-2025')
    sb.subtitle('The question: how many beneficiaries can generate a fee-for-service '
                'ambulance claim, how fast is that base eroding to Medicare Advantage, '
                'and how large is the ESRD population that generates recurring '
                'dialysis transport? Source: CMS Medicare Monthly Enrollment, '
                'MONTH=Year rows, pulled 10 Jul 2026 (Pull_Manifest). ESRD columns '
                'count aged and disabled beneficiaries with end-stage renal disease.')
    sb.blank()
    sb.banner('Panel A. National, calendar years 2013-2025')
    sb.headers(['Year', '', 'Total benes', 'Original Medicare', 'MA & other',
                'MA & other share', 'Aged ESRD', 'Disabled ESRD (incl. ESRD-only)',
                'ESRD total'])
    a0 = sb.r + 1
    for r in nat:
        row_n = sb.r + 1
        sb.row([(int(r['YEAR']), 'src'), None,
                (_i(r['TOT_BENES']), 'src', lib.FMT_INT),
                (_i(r['ORGNL_MDCR_BENES']), 'src', lib.FMT_INT),
                (_i(r['MA_AND_OTH_BENES']), 'src', lib.FMT_INT),
                (f'=IF(C{row_n}=0,"n/a",E{row_n}/C{row_n})', 'fml', lib.FMT_PCT1),
                (_i(r['AGED_ESRD_BENES']), 'src', lib.FMT_INT),
                (_i(r['DSBLD_ESRD_AND_ESRD_ONLY_BENES']), 'src', lib.FMT_INT),
                (f'=G{row_n}+H{row_n}', 'fml', lib.FMT_INT)])
    a1 = sb.r
    n_yrs = a1 - a0
    sb.row([('CAGR 2013-2025', 'label'), None,
            (lib.cagr_formula(f'C{a1}', f'C{a0}', n_yrs), 'fml', lib.FMT_PCT2),
            (lib.cagr_formula(f'D{a1}', f'D{a0}', n_yrs), 'fml', lib.FMT_PCT2),
            (lib.cagr_formula(f'E{a1}', f'E{a0}', n_yrs), 'fml', lib.FMT_PCT2),
            None,
            (lib.cagr_formula(f'G{a1}', f'G{a0}', n_yrs), 'fml', lib.FMT_PCT2),
            (lib.cagr_formula(f'H{a1}', f'H{a0}', n_yrs), 'fml', lib.FMT_PCT2),
            (lib.cagr_formula(f'I{a1}', f'I{a0}', n_yrs), 'fml', lib.FMT_PCT2)])
    sb.note('Original Medicare is the population that can appear in carrier ambulance '
            'claims (PSPS / MUP tabs). The MA & other share row is the "dark share" '
            'denominator wedge carried on Utilization_Normalized and State_Saturation. '
            'ESRD counts are beneficiaries, not dialysis patients per se; USRDS '
            'prevalence remains pending (README register P5).')
    lib.add_chart(ws, f'K{a0}', 'Original Medicare vs MA & other, 2013-2025',
                  f'Enrollment_ESRD_State!$A${a0}:$A${a1}',
                  [('Enrollment_ESRD_State!$D${}'.format(a0 - 1),
                    f'Enrollment_ESRD_State!$D${a0}:$D${a1}'),
                   ('Enrollment_ESRD_State!$E${}'.format(a0 - 1),
                    f'Enrollment_ESRD_State!$E${a0}:$E${a1}')],
                  kind='line', y_fmt='#,##0,,"M"')
    lib.add_chart(ws, f'K{a0+14}', 'ESRD beneficiaries (aged + disabled), 2013-2025',
                  f'Enrollment_ESRD_State!$A${a0}:$A${a1}',
                  [('ESRD total', f'Enrollment_ESRD_State!$I${a0}:$I${a1}')],
                  kind='line', y_fmt='#,##0')
    sb.blank()
    sb.banner('Panel B. States, calendar year 2024 snapshot')
    sb.headers(['State', 'Abbrev', 'Total benes', 'Original Medicare', 'MA & other',
                'MA & other share', 'Aged ESRD', 'Disabled ESRD', 'ESRD total'])
    b0 = sb.r + 1
    st24 = sorted([r for r in st if r['YEAR'] == '2024'],
                  key=lambda r: r['BENE_STATE_DESC'])
    for r in st24:
        row_n = sb.r + 1
        sb.row([(r['BENE_STATE_DESC'], 'src'), (r['BENE_STATE_ABRVTN'], 'src'),
                (_i(r['TOT_BENES']), 'src', lib.FMT_INT),
                (_i(r['ORGNL_MDCR_BENES']), 'src', lib.FMT_INT),
                (_i(r['MA_AND_OTH_BENES']), 'src', lib.FMT_INT),
                (f'=IF(C{row_n}=0,"n/a",E{row_n}/C{row_n})', 'fml', lib.FMT_PCT1),
                (_i(r['AGED_ESRD_BENES']), 'src', lib.FMT_INT),
                (_i(r['DSBLD_ESRD_AND_ESRD_ONLY_BENES']), 'src', lib.FMT_INT),
                (f'=G{row_n}+H{row_n}', 'fml', lib.FMT_INT)])
    b1 = sb.r
    enroll_2024_span = (b0, b1)
    sb.blank()
    sb.banner('Panel C. ESRD total by state and year, 2013-2025 (long table)')
    sb.headers(['State', 'Year', 'Aged ESRD', 'Disabled ESRD', 'ESRD total',
                'Original Medicare', 'Total benes'])
    for r in sorted(st, key=lambda r: (r['BENE_STATE_DESC'], r['YEAR'])):
        row_n = sb.r + 1
        sb.row([(r['BENE_STATE_DESC'], 'src'), (int(r['YEAR']), 'src'),
                (_i(r['AGED_ESRD_BENES']), 'src', lib.FMT_INT),
                (_i(r['DSBLD_ESRD_AND_ESRD_ONLY_BENES']), 'src', lib.FMT_INT),
                (f'=C{row_n}+D{row_n}', 'fml', lib.FMT_INT),
                (_i(r['ORGNL_MDCR_BENES']), 'src', lib.FMT_INT),
                (_i(r['TOT_BENES']), 'src', lib.FMT_INT)])
    facts += [
        {'metric': 'Original Medicare (any part) beneficiaries, national', 'year': 2024,
         'value_ref': f'Enrollment_ESRD_State!D{a0 + 11}', 'unit': 'beneficiaries',
         'basis': 'GOV', 'tier': 'A', 'source_keys': ['enroll_monthly'],
         'locator': 'Medicare Monthly Enrollment, National, MONTH=Year, 2024',
         'lives_on': 'Enrollment_ESRD_State',
         'cross_check': 'Consistent with the A&B denominator discussion on '
                        'Utilization_Normalized (different definition: any-part vs '
                        'A-and-B; both stated there)'},
        {'metric': 'MA & other share of Medicare beneficiaries, national', 'year': 2025,
         'value_ref': f'Enrollment_ESRD_State!F{a1}', 'unit': '%',
         'basis': 'DERIVED', 'tier': 'A', 'source_keys': ['enroll_monthly'],
         'locator': 'MA_AND_OTH_BENES / TOT_BENES, 2025',
         'lives_on': 'Enrollment_ESRD_State',
         'cross_check': 'Tracks the KFF 54% (2025) MA share on Macro_Demand_Drivers '
                        '(different definition: KFF excludes some "other" plans)'},
        {'metric': 'Medicare ESRD beneficiaries (aged + disabled), national',
         'year': 2025, 'value_ref': f'Enrollment_ESRD_State!I{a1}',
         'unit': 'beneficiaries', 'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['enroll_monthly'],
         'locator': 'AGED_ESRD_BENES + DSBLD_ESRD_AND_ESRD_ONLY_BENES, 2025',
         'lives_on': 'Enrollment_ESRD_State',
         'cross_check': 'Denominator context for the Dialysis_ESRD_Channel RSNAT '
                        'collapse: the patient base did not shrink; the paid volume did'},
    ]

    # ══ MUP_Ambulance_National ═════════════════════════════════════════════
    years = []
    data = {}
    for yr in range(2013, 2025):
        try:
            rows = _load(cache, f'mup_national_{yr}')
        except FileNotFoundError:
            continue
        years.append(yr)
        for r in rows:
            data[(yr, r['HCPCS_Cd'])] = r
    ws = wb.create_sheet('MUP_Ambulance_National')
    sb = lib.SheetBuilder(ws, 10, col_widths=[7, 9, 30, 11, 12, 13, 12, 12, 12, 12],
                          tab_color='FF1F6F8B')
    sb.title('Medicare FFS ambulance utilization and price, national, 2013-2024')
    sb.subtitle('The question: what does the final-action Medicare record say about '
                'ambulance volumes, prices and supplier participation, code by code, '
                'over twelve years? Source: CMS Medicare Physician & Other '
                'Practitioners by Geography and Service (final-action MUP basis - '
                'NOT the same universe as PSPS submitted services; the two bases '
                'differ by ~1.10x in 2024 and must never be mixed, per '
                'Data_Quality_Register #34). Suppression: rows with 10 or fewer '
                'beneficiaries are excluded at source, so counts are floors.')
    sb.blank()
    sb.banner('Panel A. The published rows: one per code and year (final-action)')
    sb.headers(['Year', 'HCPCS', 'Level of service', 'Providers', 'Beneficiaries',
                'Services', 'Avg submitted $', 'Avg allowed $', 'Avg paid $',
                'Paid/allowed'])
    pa0 = sb.r + 1
    for yr in years:
        for code in CODES:
            r = data.get((yr, code))
            if not r:
                continue
            row_n = sb.r + 1
            sb.row([(yr, 'src'), (code, 'src'), CODE_LABEL[code],
                    (_i(r['Tot_Rndrng_Prvdrs']), 'src', lib.FMT_INT),
                    (_i(r['Tot_Benes']), 'src', lib.FMT_INT),
                    (_f(r['Tot_Srvcs']), 'src', lib.FMT_INT),
                    (_f(r['Avg_Sbmtd_Chrg']), 'src', lib.FMT_USD2),
                    (_f(r['Avg_Mdcr_Alowd_Amt']), 'src', lib.FMT_USD2),
                    (_f(r['Avg_Mdcr_Pymt_Amt']), 'src', lib.FMT_USD2),
                    (f'=I{row_n}/H{row_n}', 'fml', lib.FMT_PCT1)])
    pa1 = sb.r
    sb.blank()
    sb.banner('Panel B. Services by code and year (live pivot over Panel A) with CAGR')
    piv_codes = ['A0428', 'A0429', 'A0426', 'A0427', 'A0433', 'A0434', 'A0431', 'A0425']
    sb.headers(['Year'] + [f'{c}\n{CODE_LABEL[c]}' for c in piv_codes]
               + ['Ground base total'])
    pb0 = sb.r + 1
    for yr in years:
        row_n = sb.r + 1
        cells = [(yr, 'fml')]
        for j, code in enumerate(piv_codes):
            col = chr(ord('B') + j)
            cells.append((f'=SUMIFS($F${pa0}:$F${pa1},$A${pa0}:$A${pa1},$A{row_n},'
                          f'$B${pa0}:$B${pa1},"{code}")', 'fml', lib.FMT_INT))
        ground = '+'.join(
            f'SUMIFS($F${pa0}:$F${pa1},$A${pa0}:$A${pa1},$A{row_n},$B${pa0}:$B${pa1},"{c}")'
            for c in GROUND_BASE)
        cells.append((f'={ground}', 'fml', lib.FMT_INT))
        sb.row(cells)
    pb1 = sb.r
    n = len(years) - 1
    sb.row([('CAGR 2013-2024', 'label')] +
           [(lib.cagr_formula(f'{chr(ord("B") + j)}{pb1}', f'{chr(ord("B") + j)}{pb0}', n),
             'fml', lib.FMT_PCT2) for j in range(len(piv_codes) + 1)])
    sb.row([('CAGR 2019-2024 (post-COVID window)', 'label')] +
           [(lib.cagr_formula(f'{chr(ord("B") + j)}{pb1}', f'{chr(ord("B") + j)}{pb0 + 6}', 5),
             'fml', lib.FMT_PCT2) for j in range(len(piv_codes) + 1)])
    sb.note('Trend eligibility: 2020-2021 are COVID-shock years (utilization '
            'collapse and rebound); the 2013-2024 CAGR spans them, so the 2019-2024 '
            'window is shown beside it. Final-action MUP services; decimal service '
            'counts are shared-billing fractions and are summed as floats.')
    sb.blank()
    sb.banner('Panel C. Average Medicare allowed $ per service (live pivot) with CAGR')
    sb.headers(['Year'] + [f'{c}' for c in piv_codes])
    pc0 = sb.r + 1
    for yr in years:
        row_n = sb.r + 1
        cells = [(yr, 'fml')]
        for j, code in enumerate(piv_codes):
            cells.append((f'=SUMIFS($H${pa0}:$H${pa1},$A${pa0}:$A${pa1},$A{row_n},'
                          f'$B${pa0}:$B${pa1},"{code}")', 'fml', lib.FMT_USD2))
        sb.row(cells)
    pc1 = sb.r
    sb.row([('CAGR 2013-2024', 'label')] +
           [(lib.cagr_formula(f'{chr(ord("B") + j)}{pc1}', f'{chr(ord("B") + j)}{pc0}', n),
             'fml', lib.FMT_PCT2) for j in range(len(piv_codes))])
    sb.note('The allowed-per-service series is the realized Medicare price. Compare '
            'Payment_Rules: the schedule updates by the Ambulance Inflation Factor; '
            'realized averages also move with mileage mix and geography.')
    lib.add_chart(ws, f'L{pb0}', 'Ground base services by code, 2013-2024',
                  f'MUP_Ambulance_National!$A${pb0}:$A${pb1}',
                  [(f'MUP_Ambulance_National!${chr(ord("B") + j)}${pb0 - 1}',
                    f'MUP_Ambulance_National!${chr(ord("B") + j)}${pb0}:${chr(ord("B") + j)}${pb1}')
                   for j in range(6)], kind='line', y_fmt='#,##0')
    lib.add_chart(ws, f'L{pb0 + 14}', 'Average allowed $ per service, key codes',
                  f'MUP_Ambulance_National!$A${pc0}:$A${pc1}',
                  [(f'MUP_Ambulance_National!${chr(ord("B") + j)}${pc0 - 1}',
                    f'MUP_Ambulance_National!${chr(ord("B") + j)}${pc0}:${chr(ord("B") + j)}${pc1}')
                   for j in range(6)], kind='line', y_fmt='$#,##0')
    r24 = data.get((2024, 'A0428'))
    if r24:
        facts += [
            {'metric': 'Medicare FFS BLS non-emergency services (A0428, final-action)',
             'year': 2024, 'value': _f(r24['Tot_Srvcs']), 'unit': 'services',
             'basis': 'GOV', 'tier': 'A', 'source_keys': ['mup_geo'],
             'locator': 'MUP by Geography & Service 2024, National, A0428, Tot_Srvcs',
             'lives_on': 'MUP_Ambulance_National',
             'cross_check': 'MUP final-action basis; PSPS submitted basis differs by '
                            'design (~1.10x in 2024, Data_Quality_Register #34)'},
            {'metric': 'Rendering providers billing A0428', 'year': 2024,
             'value': _i(r24['Tot_Rndrng_Prvdrs']), 'unit': 'NPIs',
             'basis': 'GOV', 'tier': 'A', 'source_keys': ['mup_geo'],
             'locator': 'MUP by Geography & Service 2024, National, A0428',
             'lives_on': 'MUP_Ambulance_National',
             'cross_check': 'The scheduled-transport biller base; see Supplier_Trend '
                            'BLS-NE biller exit series'},
        ]
    facts += [
        {'metric': 'SCT (A0434) services CAGR, 2013-2024', 'year': 2024,
         'value_ref': f'MUP_Ambulance_National!G{pb1 + 1}', 'unit': '%/yr',
         'basis': 'DERIVED', 'tier': 'A', 'source_keys': ['mup_geo'],
         'locator': '(2024 services / 2013 services)^(1/11)-1, Panel B',
         'lives_on': 'MUP_Ambulance_National',
         'cross_check': 'Directionally consistent with the SCT share-of-transports '
                        'chart on the Charts tab (PSPS basis)'},
    ]

    # ══ MUP_Ambulance_State ════════════════════════════════════════════════
    ws = wb.create_sheet('MUP_Ambulance_State')
    sb = lib.SheetBuilder(ws, 10, col_widths=[18, 8, 9, 26, 11, 12, 13, 12, 12, 12],
                          tab_color='FF1F6F8B')
    sb.title('Medicare FFS ambulance by state and code: 2024 against 2019')
    sb.subtitle('The question: where is Medicare ambulance volume, price and supplier '
                'participation, state by state - and how did the map shift over the '
                'five COVID-spanning years? Source: CMS MUP by Geography & Service, '
                'State grain, all ambulance HCPCS, data years 2019 and 2024 (pulled '
                '10 Jul 2026). Suppressed state-code cells (<=10 beneficiaries) are '
                'absent at source: state sums are floors.')
    sb.blank()
    state_spans = {}
    for yr in (2024, 2019):
        sb.banner(f'Panel {"A" if yr == 2024 else "B"}. Data year {yr}: one row per '
                  'state and code (final-action)')
        sb.headers(['State', 'Geo code', 'HCPCS', 'Level of service', 'Providers',
                    'Beneficiaries', 'Services', 'Avg submitted $', 'Avg allowed $',
                    'Avg paid $'])
        s0 = sb.r + 1
        rows = []
        for code in CODES:
            try:
                rows += _load(cache, f'mup_state_{yr}_{code}')
            except FileNotFoundError:
                continue
        rows.sort(key=lambda r: (r['Rndrng_Prvdr_Geo_Desc'], r['HCPCS_Cd']))
        for r in rows:
            sb.row([(r['Rndrng_Prvdr_Geo_Desc'], 'src'),
                    (r['Rndrng_Prvdr_Geo_Cd'], 'src'), (r['HCPCS_Cd'], 'src'),
                    CODE_LABEL.get(r['HCPCS_Cd'], ''),
                    (_i(r['Tot_Rndrng_Prvdrs']), 'src', lib.FMT_INT),
                    (_i(r['Tot_Benes']), 'src', lib.FMT_INT),
                    (_f(r['Tot_Srvcs']), 'src', lib.FMT_INT),
                    (_f(r['Avg_Sbmtd_Chrg']), 'src', lib.FMT_USD2),
                    (_f(r['Avg_Mdcr_Alowd_Amt']), 'src', lib.FMT_USD2),
                    (_f(r['Avg_Mdcr_Pymt_Amt']), 'src', lib.FMT_USD2)])
        state_spans[yr] = (s0, sb.r)
        sb.blank()
    # Panel C: state screen 2024 with per-1,000 Original Medicare
    a0s, a1s = state_spans[2024]
    b0s, b1s = state_spans.get(2019, (a0s, a1s))
    e0, e1 = enroll_2024_span
    sb.banner('Panel C. State screen, 2024: ground base services, per-1,000 Original '
              'Medicare, and the 2019 comparison (all live formulas over Panels A/B)')
    sb.headers(['State', 'Ground base services 2024', 'Ground base services 2019',
                'Change', 'Original Medicare benes 2024',
                'Services per 1,000 Original Medicare', 'Providers 2024 (A0428)',
                'Avg allowed $ 2024 (A0428)'])
    states = sorted({r['BENE_STATE_DESC'] for r in st24})
    c0 = sb.r + 1
    ground_or = '{' + ','.join(f'"{c}"' for c in GROUND_BASE) + '}'
    for s in states:
        row_n = sb.r + 1
        g24 = (f'=SUMPRODUCT(SUMIFS($G${a0s}:$G${a1s},$A${a0s}:$A${a1s},$A{row_n},'
               f'$C${a0s}:$C${a1s},{ground_or}))')
        g19 = (f'=SUMPRODUCT(SUMIFS($G${b0s}:$G${b1s},$A${b0s}:$A${b1s},$A{row_n},'
               f'$C${b0s}:$C${b1s},{ground_or}))')
        sb.row([(s, 'src'), (g24, 'fml', lib.FMT_INT), (g19, 'fml', lib.FMT_INT),
                (f'=IF(C{row_n}=0,"n/a",B{row_n}/C{row_n}-1)', 'fml', lib.FMT_PCT1),
                (f"=INDEX(Enrollment_ESRD_State!$D${e0}:$D${e1},"
                 f"MATCH($A{row_n},Enrollment_ESRD_State!$A${e0}:$A${e1},0))",
                 'fml', lib.FMT_INT),
                (f'=IF(E{row_n}=0,"n/a",B{row_n}/(E{row_n}/1000))', 'fml', lib.FMT_DEC1),
                (f'=SUMIFS($E${a0s}:$E${a1s},$A${a0s}:$A${a1s},$A{row_n},'
                 f'$C${a0s}:$C${a1s},"A0428")', 'fml', lib.FMT_INT),
                (f'=SUMIFS($I${a0s}:$I${a1s},$A${a0s}:$A${a1s},$A{row_n},'
                 f'$C${a0s}:$C${a1s},"A0428")', 'fml', lib.FMT_USD2)])
    c1 = sb.r
    sb.note('Per-1,000 uses Original Medicare (any part) from Enrollment_ESRD_State '
            'Panel B - a different denominator than the A-and-B convention on '
            'Utilization_Normalized (both stated; do not mix). 2019 state rows '
            'missing at source (suppression) make the change column a floor-to-floor '
            'comparison. Screen rows cover states present in the enrollment file; '
            'territories in the MUP file without enrollment rows are visible in '
            'Panels A/B.')
    lib.add_chart(ws, f'L{c0}', 'Ground base services per 1,000 Original Medicare, 2024',
                  f'MUP_Ambulance_State!$A${c0}:$A${c1}',
                  [('per 1,000', f'MUP_Ambulance_State!$F${c0}:$F${c1}')],
                  kind='bar', height=18)
    facts += [
        {'metric': 'States/territories with ambulance MUP rows', 'year': 2024,
         'value': len({r['Rndrng_Prvdr_Geo_Desc'] for c in CODES
                       for r in _try_load(cache, f'mup_state_2024_{c}')}),
         'unit': 'geographies', 'basis': 'GOV', 'tier': 'A',
         'source_keys': ['mup_geo'],
         'locator': 'MUP by Geography & Service 2024, State grain, A0425-A0436',
         'lives_on': 'MUP_Ambulance_State',
         'cross_check': 'Suppression makes absent state-code pairs floors, not zeros'},
    ]

    # ══ PSPS_Denial_Series ═════════════════════════════════════════════════
    ws = wb.create_sheet('PSPS_Denial_Series')
    sb = lib.SheetBuilder(ws, 10, col_widths=[7, 9, 26, 14, 14, 11, 15, 15, 12, 14],
                          tab_color='FF1F6F8B')
    sb.title('Medicare ambulance denial rates, 2010-2024: the submitted-vs-denied wedge')
    sb.subtitle('The question: what share of submitted Medicare ambulance services is '
                'denied, by level of service, and is the screen tightening? PSPS is '
                'the only public file that carries submitted AND denied counts on the '
                'same row. Built from the raw PSPS claim-summary rows (client-side '
                'aggregation; row counts and SHA-256 per code-year on Pull_Manifest). '
                'PSPS counts SUBMITTED services - a different universe from the '
                'final-action MUP tabs (never mix; Data_Quality_Register #34).')
    sb.blank()
    psps = {}
    for yr in range(2010, 2025):
        for code in PSPS_CODES:
            try:
                psps[(yr, code)] = _load(cache, f'psps_agg_{yr}_{code}')
            except FileNotFoundError:
                pass
    have_years = sorted({k[0] for k in psps})
    sb.banner('Panel A. National totals by code and year (all initial modifiers)')
    sb.headers(['Year', 'HCPCS', 'Level of service', 'Submitted services',
                'Denied services', 'Denial rate', 'Submitted charges $',
                'Allowed charges $', 'Allowed/submitted $', 'PSPS lines aggregated'])
    a0p = sb.r + 1
    for yr in have_years:
        for code in PSPS_CODES:
            d = psps.get((yr, code))
            if not d:
                continue
            tot = {'SUBMITTED_SERVICE_CNT': 0.0, 'DENIED_SERVICES_CNT': 0.0,
                   'SUBMITTED_CHARGE_AMT': 0.0, 'ALLOWED_CHARGE_AMT': 0.0}
            nlines = 0
            for mod, a in d['by_initial_modifier'].items():
                nlines += a.get('_lines', 0)
                for k in tot:
                    tot[k] += a.get(k, 0.0)
            row_n = sb.r + 1
            sb.row([(yr, 'src'), (code, 'src'), CODE_LABEL[code],
                    (tot['SUBMITTED_SERVICE_CNT'], 'src', lib.FMT_INT),
                    (tot['DENIED_SERVICES_CNT'], 'src', lib.FMT_INT),
                    (f'=IF(D{row_n}=0,"n/a",E{row_n}/D{row_n})', 'fml', lib.FMT_PCT1),
                    (tot['SUBMITTED_CHARGE_AMT'], 'src', lib.FMT_USD),
                    (tot['ALLOWED_CHARGE_AMT'], 'src', lib.FMT_USD),
                    (f'=H{row_n}/G{row_n}', 'fml', lib.FMT_PCT1),
                    (nlines, 'src', lib.FMT_INT)])
    a1p = sb.r
    sb.note('Field-name trap carried from v2.7: the PSPS_ column prefix begins with '
            'data year 2020; the aggregation maps by suffix so all vintages align. '
            'Decimal service counts (shared billing) summed as floats, matching the '
            'v2.7 Medicare_OD_Matrix convention.')
    sb.blank()
    sb.banner('Panel B. Denial rate by code and year (live pivot over Panel A)')
    sb.headers(['Year'] + PSPS_CODES)
    pb0p = sb.r + 1
    for yr in have_years:
        row_n = sb.r + 1
        cells = [(yr, 'fml')]
        for j, code in enumerate(PSPS_CODES):
            den = (f'SUMIFS($D${a0p}:$D${a1p},$A${a0p}:$A${a1p},$A{row_n},'
                   f'$B${a0p}:$B${a1p},"{code}")')
            num = (f'SUMIFS($E${a0p}:$E${a1p},$A${a0p}:$A${a1p},$A{row_n},'
                   f'$B${a0p}:$B${a1p},"{code}")')
            cells.append((f'=IF({den}=0,"n/a",{num}/{den})', 'fml', lib.FMT_PCT1))
        sb.row(cells)
    pb1p = sb.r
    lib.add_chart(ws, f'L{pb0p}', 'Denial rate by level of service, 2010-2024',
                  f'PSPS_Denial_Series!$A${pb0p}:$A${pb1p}',
                  [(f'PSPS_Denial_Series!${chr(ord("B") + j)}${pb0p - 1}',
                    f'PSPS_Denial_Series!${chr(ord("B") + j)}${pb0p}:${chr(ord("B") + j)}${pb1p}')
                   for j in range(len(PSPS_CODES))], kind='line', y_fmt='0%')
    sb.blank()
    sb.banner('Panel C. 2024 denial rate by origin-destination pair, ground base codes')
    sb.headers(['Initial modifier (origin-destination)', 'Submitted services',
                'Denied services', 'Denial rate', 'Share of submitted'])
    mods = {}
    for code in GROUND_BASE:
        d = psps.get((2024, code))
        if not d:
            continue
        for mod, a in d['by_initial_modifier'].items():
            m = mods.setdefault(mod, {'sub': 0.0, 'den': 0.0})
            m['sub'] += a.get('SUBMITTED_SERVICE_CNT', 0.0)
            m['den'] += a.get('DENIED_SERVICES_CNT', 0.0)
    tot_sub = sum(m['sub'] for m in mods.values())
    c0p = sb.r + 1
    for mod, m in sorted(mods.items(), key=lambda kv: -kv[1]['sub'])[:20]:
        row_n = sb.r + 1
        sb.row([(mod, 'src'), (m['sub'], 'src', lib.FMT_INT),
                (m['den'], 'src', lib.FMT_INT),
                (f'=C{row_n}/B{row_n}', 'fml', lib.FMT_PCT1),
                (f'=B{row_n}/{tot_sub}', 'fml', lib.FMT_PCT1)])
    c1p = sb.r
    sb.note('Modifier letters: H hospital, N SNF, R residence, E residential/'
            'custodial, D diagnostic/therapeutic site, P physician office, S scene, '
            'G dialysis (first letter = origin, second = destination; see '
            'Code_Crosswalks). Top 20 pairs by submitted volume shown; the full '
            'distribution is in the cached artifacts.')
    if (2024, 'A0428') in psps and (2010, 'A0428') in psps:
        facts += [
            {'metric': 'BLS non-emergency (A0428) denial rate', 'year': 2024,
             'value_ref': f'PSPS_Denial_Series!E{pb1p}', 'unit': '%',
             'basis': 'DERIVED', 'tier': 'A', 'source_keys': ['psps_v3'],
             'locator': 'Panel B, A0428 column, 2024 row (denied/submitted)',
             'lives_on': 'PSPS_Denial_Series',
             'cross_check': 'The medical-necessity screen on scheduled transport; '
                            'compare the RSNAT natural experiment on '
                            'Dialysis_ESRD_Channel and Payment_Integrity'},
        ]

    # ══ Market_Saturation_Ambulance ════════════════════════════════════════
    ms = _load(cache, 'marketsat_state')
    ws = wb.create_sheet('Market_Saturation_Ambulance')
    sb = lib.SheetBuilder(ws, 10, col_widths=[24, 26, 12, 14, 12, 13, 16, 12, 12, 12],
                          tab_color='FF1F6F8B')
    sb.title('CMS market saturation: ambulance supply density, 2020-2025')
    sb.subtitle('The question: how many ambulance providers serve each geography, '
                'how many beneficiaries use them, and what does Medicare FFS pay - '
                'measured by CMS program-integrity market-saturation windows (15 '
                'rolling 12-month reference periods, 2020-2025)? This is the '
                'fraud-lens companion to the billing-based Supplier tabs: same '
                'market, different instrument. County provider-count bands measure '
                'thin-supply whitespace (pending register P2, partially closed).')
    sb.blank()
    sb.banner('Panel A. National series by service type and reference period')
    sb.headers(['Reference period', 'Service type', 'Providers', 'FFS beneficiaries',
                'Users', 'Users % of FFS', 'Total payment $', 'Payment per user $'])
    a0m = sb.r + 1
    for block in ms:
        t = block['type_of_service']
        for r in block['nation_state_rows']:
            if r['aggregation_level'] != 'NATION + TERRITORIES':
                continue
            row_n = sb.r + 1
            pay = _f(str(r.get('total_payment', '')).replace('$', '').replace(',', ''))
            sb.row([(r['reference_period'], 'src'), t,
                    (_f(str(r.get('number_of_providers', '')).replace(',', '')), 'src', lib.FMT_INT),
                    (_f(str(r.get('number_of_fee_for_service_beneficiaries', '')).replace(',', '')), 'src', lib.FMT_INT),
                    (_f(str(r.get('number_of_users', '')).replace(',', '')), 'src', lib.FMT_INT),
                    (f'=E{row_n}/D{row_n}', 'fml', lib.FMT_PCT1),
                    (pay, 'src', lib.FMT_USD),
                    (f'=G{row_n}/E{row_n}', 'fml', lib.FMT_USD2)])
    a1m = sb.r
    sb.note('Reference periods are rolling 12-month windows and OVERLAP - adjacent '
            'rows share nine months of claims. Trend across calendar-aligned windows '
            '(Jan-Dec) only; the calendar windows are 2020, 2021, 2022, 2023, 2024, '
            '2025.')
    sb.blank()
    sb.banner('Panel B. States, latest window (2025 calendar year), all three types')
    sb.headers(['State', 'Service type', 'Providers', 'FFS beneficiaries', 'Users',
                'Users % of FFS', 'Total payment $', 'Payment per user $'])
    b0m = sb.r + 1
    for block in ms:
        t = block['type_of_service']
        latest = block['latest_period']
        rows = [r for r in block['nation_state_rows']
                if r['aggregation_level'] == 'STATE' and r['reference_period'] == latest]
        for r in sorted(rows, key=lambda x: x.get('state') or ''):
            row_n = sb.r + 1
            pay = _f(str(r.get('total_payment', '')).replace('$', '').replace(',', ''))
            sb.row([(r.get('state'), 'src'), t,
                    (_f(str(r.get('number_of_providers', '')).replace(',', '')), 'src', lib.FMT_INT),
                    (_f(str(r.get('number_of_fee_for_service_beneficiaries', '')).replace(',', '')), 'src', lib.FMT_INT),
                    (_f(str(r.get('number_of_users', '')).replace(',', '')), 'src', lib.FMT_INT),
                    (f'=E{row_n}/D{row_n}', 'fml', lib.FMT_PCT1),
                    (pay, 'src', lib.FMT_USD),
                    (f'=IF(E{row_n}=0,"n/a",G{row_n}/E{row_n})', 'fml', lib.FMT_USD2)])
    b1m = sb.r
    sb.blank()
    sb.banner('Panel C. County whitespace bands: counties by ambulance provider count '
              '(Emergency & Non-Emergency type), latest window per state')
    sb.headers(['State', 'Counties', 'Providers suppressed/0', '1-2 providers',
                '3-9 providers', '10+ providers', 'Share of counties under 3 providers'])
    blk = ms[0]
    latest = blk['latest_period']
    bands = [b for b in blk['county_provider_bands']
             if b['reference_period'] == latest]
    c0m = sb.r + 1
    for b in sorted(bands, key=lambda x: x.get('state') or ''):
        row_n = sb.r + 1
        supp0 = (b.get('suppressed', 0) or 0) + (b.get('0', 0) or 0)
        sb.row([(b['state'], 'src'), (b['n_counties'], 'src', lib.FMT_INT),
                (supp0, 'src', lib.FMT_INT), (b.get('1-2', 0), 'src', lib.FMT_INT),
                (b.get('3-9', 0), 'src', lib.FMT_INT), (b.get('10+', 0), 'src', lib.FMT_INT),
                (f'=(C{row_n}+D{row_n})/B{row_n}', 'fml', lib.FMT_PCT1)])
    c1m = sb.r
    tr = sb.r + 1
    sb.row([('US total', 'label'),
            (f'=SUM(B{c0m}:B{c1m})', 'fml', lib.FMT_INT),
            (f'=SUM(C{c0m}:C{c1m})', 'fml', lib.FMT_INT),
            (f'=SUM(D{c0m}:D{c1m})', 'fml', lib.FMT_INT),
            (f'=SUM(E{c0m}:E{c1m})', 'fml', lib.FMT_INT),
            (f'=SUM(F{c0m}:F{c1m})', 'fml', lib.FMT_INT),
            (f'=(C{tr}+D{tr})/B{tr}', 'fml', lib.FMT_PCT1)])
    sb.note('A suppressed county cell means fewer than 11 users - grouped with zero '
            'as "thin or no measured FFS supply". Bands computed from the county '
            'grain of the same CMS file (cached; per-period band history in the '
            'artifact). This measures Medicare FFS-billing presence, not physical '
            'ambulance posts.')
    lib.add_chart(ws, f'J{c0m}', 'Counties with fewer than 3 measured ambulance '
                                 'providers, by state (latest window)',
                  f'Market_Saturation_Ambulance!$A${c0m}:$A${c1m}',
                  [('under 3', f'Market_Saturation_Ambulance!$G${c0m}:$G${c1m}')],
                  kind='bar', height=18)
    facts += [
        {'metric': 'US counties with <3 measured FFS ambulance providers, share',
         'year': 2025, 'value_ref': f'Market_Saturation_Ambulance!G{tr}',
         'unit': '% of counties', 'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['marketsat'],
         'locator': 'Panel C total row: (suppressed/0 + 1-2) / counties, latest window',
         'lives_on': 'Market_Saturation_Ambulance',
         'cross_check': 'Whitespace measure; complements Imbalance_Ledger and the '
                        'State_Saturation thin-supply screen'},
    ]

    return {'facts': facts, 'sources': sources, 'excluded': excluded,
            'meta': {'notes': 'PSPS years present: %s' % (have_years,),
                     'row_counts': {s['name']: wb[s['name']].max_row for s in SHEETS}}}


def _try_load(cache, key):
    try:
        return _load(cache, key)
    except FileNotFoundError:
        return []
