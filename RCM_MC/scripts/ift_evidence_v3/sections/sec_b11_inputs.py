"""B.11 + B.12: the input-cost index and the public-operator benchmarks.

Two tabs:
  Input_Cost_Index          - diesel by PADD (EIA), PPI diesel + ECEC (BLS),
                              the QCEW wage leg (green-linked), and the AIF
                              divergence panel: every input series printed
                              separately against the payment update; no
                              blended basket (house rule: no composite
                              indices).
  Public_Operator_Benchmarks- DocGo + ModivCare annual revenues from SEC
                              companyfacts (accession locators), DocGo
                              trips/ATP green-linked to Facility_Pay_Layer,
                              ModivCare as the NEMT-adjacent boundary
                              reference, Falck Annual Report 2025 row.

Pull artifacts: eia_diesel_padd, bls_input_series, edgar_operator_facts,
falck_annual_report, cms_aif_history (pull14.py, 11 Jul 2026).
"""

SHEETS = [
    {'name': 'Input_Cost_Index',
     'question': 'What happened to the measured inputs of running an '
                 'ambulance - fuel, wages, benefits - against the Medicare '
                 'payment update?'},
    {'name': 'Public_Operator_Benchmarks',
     'question': 'What do listed-operator disclosures establish about '
                 'ambulance revenue scale and per-trip economics?'},
]

EIA_XLS = 'https://www.eia.gov/petroleum/gasdiesel/xls/psw18vwall.xls'
BLS_API = 'https://api.bls.gov/publicAPI/v2/timeseries/data/'
CLM15 = ('https://www.cms.gov/Regulations-and-Guidance/Guidance/Manuals/'
         'downloads/clm104c15.pdf')
CF_URL = 'https://data.sec.gov/api/xbrl/companyfacts/CIK{10digit}.json'
FALCK_PDF = ('https://brandportal.falck.com/m/1861cbb053f46e04/original/'
             'Annual-Report-2025.pdf')

PADD_KEYS = [('EMD_EPD2D_PTE_NUS_DPG', 'U.S.'),
             ('EMD_EPD2D_PTE_R10_DPG', 'PADD 1 East Coast'),
             ('EMD_EPD2D_PTE_R20_DPG', 'PADD 2 Midwest'),
             ('EMD_EPD2D_PTE_R30_DPG', 'PADD 3 Gulf Coast'),
             ('EMD_EPD2D_PTE_R40_DPG', 'PADD 4 Rocky Mountain'),
             ('EMD_EPD2D_PTE_R50_DPG', 'PADD 5 West Coast')]
PPI_DSL = 'WPU0531'
ECEC = 'CMU2010000000000D'
PPI_AMB_PARKED = 'PCU621910621910'


def _find_label(ws, needle, max_col=6):
    n = needle.lower()
    for row in ws.iter_rows(max_col=max_col):
        for c in row:
            if isinstance(c.value, str) and n in c.value.lower():
                return c.row, c.column
    return None


def _qcew_panelb_rows(ws):
    """QCEW_EMS_Employment Panel B rows: {year: row} where B is a SUMIFS."""
    out = {}
    for row in ws.iter_rows(min_col=1, max_col=2):
        a, b = row[0].value, row[1].value
        if (isinstance(a, int) and 2014 <= a <= 2025
                and isinstance(b, str) and b.startswith('=SUMIFS')):
            out.setdefault(a, row[0].row)
    return out


def _payment_rules_aif_rows(ws):
    """First AIF table on Payment_Rules: {year: row} (B holds the decimal).

    Year labels on that tab are text cells; coerce digit strings.
    """
    out = {}
    for row in ws.iter_rows(min_col=1, max_col=2):
        a, b = row[0].value, row[1].value
        if isinstance(a, str) and a.strip().isdigit():
            a = int(a)
        if (isinstance(a, int) and 2020 <= a <= 2026
                and isinstance(b, (int, float)) and abs(b) < 0.2):
            out.setdefault(a, row[0].row)
    return out


def build(wb, ctx):
    lib = ctx['lib']
    cache = ctx['cache']
    accessed = ctx['accessed']
    facts, sources, excluded, findings = [], [], [], []

    eia = lib.load_cache(cache, 'eia_diesel_padd')['series']
    bls = lib.load_cache(cache, 'bls_input_series')['series']
    edgar = lib.load_cache(cache, 'edgar_operator_facts')
    aif_doc = lib.load_cache(cache, 'cms_aif_history')
    try:
        falck = lib.load_cache(cache, 'falck_annual_report')
    except FileNotFoundError:
        falck = None
    qcew14 = lib.load_cache(cache, 'qcew_621910_2014')
    qcew25 = lib.load_cache(cache, 'qcew_621910_2025')

    def _us_priv_pay(rows):
        for r in rows:
            if r.get('area_fips') == 'US000' and str(r.get('own_code')) == '5':
                return float(r['avg_annual_pay'])
        return None

    pay14, pay25 = _us_priv_pay(qcew14), _us_priv_pay(qcew25)

    # AIF path: CY2014-2019 from the manual chart (verified, page-located);
    # CY2020+ green-linked from Payment_Rules
    aif_manual = {}
    for yr, rows in aif_doc['candidate_rows_by_year'].items():
        if 2014 <= int(yr) <= 2021:
            aif_manual[int(yr)] = round(
                float(rows[0]['trailing_value']) / 100.0, 6)
    aif_pr = {2020: 0.009, 2021: 0.002, 2022: 0.051, 2023: 0.087,
              2024: 0.026, 2025: 0.024}
    aif = {y: aif_manual[y] for y in range(2014, 2020)}
    aif.update(aif_pr)

    dsl = {k: eia[k]['annual_avg'] for k, _ in PADD_KEYS}
    dsl_wk = eia[PADD_KEYS[0][0]]['n_weeks']
    dsl_last = eia[PADD_KEYS[0][0]]['last_week']
    ppi = bls[PPI_DSL]['annual_avg']
    ppi_n = bls[PPI_DSL]['n_obs_by_year']
    ecec = bls[ECEC]['annual_avg']
    ecec_n = bls[ECEC]['n_obs_by_year']

    # static values for the fact ledger (the live versions sit on the tab)
    aif_cum = 1.0
    for y in range(2015, 2026):
        aif_cum *= 1.0 + aif[y]
    aif_cum -= 1.0
    pay_cum = pay25 / pay14 - 1.0
    scissors = pay_cum - aif_cum
    dsl_swing = dsl['EMD_EPD2D_PTE_NUS_DPG']['2022'] \
        / dsl['EMD_EPD2D_PTE_NUS_DPG']['2021'] - 1.0
    ppi_cum = ppi['2025'] / ppi['2014'] - 1.0
    ppi_gap = ppi_cum - aif_cum
    ecec_cum = ecec['2025'] / ecec['2014'] - 1.0

    sources += [
        {'key': 'eia_diesel', 'publisher': 'US Energy Information '
         'Administration',
         'document': 'Weekly Retail On-Highway Diesel Prices, all areas '
                     '(psw18vwall.xls), weekly through ' + dsl_last,
         'vintage': 'weekly series 1994-2026, pulled live 11 Jul 2026',
         'locator': 'Data sheets, sourcekeys EMD_EPD2D_PTE_'
                    '{NUS,R10,R20,R30,R40,R50}_DPG; annual calendar-year '
                    'means computed client-side (Pull_Manifest '
                    'eia_diesel_padd)',
         'supplies': 'The fuel leg of the input basket: retail on-highway '
                     'diesel by PADD, the only public weekly pump-price '
                     'census', 'url': EIA_XLS, 'tier': 'A',
         'accessed': accessed, 'powers': ['Input_Cost_Index']},
        {'key': 'bls_input', 'publisher': 'US Bureau of Labor Statistics',
         'document': 'Public timeseries API v2 (unregistered): WPU0531 (PPI '
                     'commodity, diesel fuel) and CMU2010000000000D (ECEC, '
                     'private industry total compensation, $/hour)',
         'vintage': '2014-2026 observations, pulled live 11 Jul 2026',
         'locator': 'POST ' + BLS_API + ' seriesid=[WPU0531, '
                    'CMU2010000000000D]; annual means computed client-side; '
                    'PCU621910621910 (PPI ambulance services industry) does '
                    'NOT exist - the pc.series catalog jumps from 621610 to '
                    '621991 (Pull_Manifest bls_input_series)',
         'supplies': 'The producer-price fuel leg and the economy-wide '
                     'compensation leg of the input basket',
         'url': BLS_API, 'tier': 'A', 'accessed': accessed,
         'powers': ['Input_Cost_Index']},
        {'key': 'cms_aif_manual', 'publisher': 'CMS',
         'document': 'Pub. 100-04 Medicare Claims Processing Manual, '
                     'Chapter 15 (Ambulance), Ambulance Inflation Factor '
                     'history chart',
         'vintage': 'manual chart CY2002-CY2021, retrieved 11 Jul 2026',
         'locator': 'AIF chart, p.23 of the chapter PDF: CY2014 1.0, CY2015 '
                    '1.5, CY2016 -0.4, CY2017 0.7, CY2018 1.1, CY2019 2.3 '
                    '(percent); CY2020-2021 rows match Payment_Rules S29',
         'supplies': 'Primary verification of the pre-2020 AIF path that '
                     'Payment_Rules does not carry',
         'url': CLM15, 'tier': 'A', 'accessed': accessed,
         'powers': ['Input_Cost_Index']},
        {'key': 'qcew_wage', 'publisher': 'US Bureau of Labor Statistics',
         'document': 'QCEW NAICS 621910 (Ambulance Services), annual '
                     'averages, private ownership, national',
         'vintage': 'data years 2014-2025 (Pull_Manifest qcew_621910_*)',
         'locator': 'US000 own_code 5 avg_annual_pay; carried in this '
                    'workbook on QCEW_EMS_Employment Panel B (green-linked '
                    'here)',
         'supplies': 'The wage leg of the input basket, industry-exact',
         'url': 'https://data.bls.gov/cew/data/api/2025/a/industry/'
                '621910.csv',
         'tier': 'A', 'accessed': accessed, 'powers': ['Input_Cost_Index']},
        {'key': 'edgar_companyfacts', 'publisher': 'SEC EDGAR (XBRL '
         'companyfacts API)',
         'document': 'companyfacts for DocGo Inc. (CIK 1822359) and '
                     'ModivCare Inc. (CIK 1220754): annual revenue facts '
                     'with accession locators',
         'vintage': 'filings through 11 Jul 2026 (DocGo FY2025 10-K accn '
                    '0001628280-26-018214; ModivCare latest annual FY2024 '
                    '10-K accn 0001220754-25-000008)',
         'locator': CF_URL + ' us-gaap Revenues / RevenueFromContractWith'
                    'CustomerExcludingAssessedTax, 10-K annual durations '
                    '(Pull_Manifest edgar_operator_facts)',
         'supplies': 'Audited annual revenue scale of the two US-listed '
                     'transport-medicine operators',
         'url': 'https://data.sec.gov/api/xbrl/companyfacts/'
                'CIK0001822359.json',
         'tier': 'A', 'accessed': accessed,
         'powers': ['Public_Operator_Benchmarks']},
    ]
    if falck:
        sources.append(
            {'key': 'falck_ar2025', 'publisher': 'Falck A/S',
             'document': 'Annual Report 2025 (Group, DKK), PDF from the '
                         'falck.com financial-reports page',
             'vintage': 'FY2025 audited, published 2026',
             'locator': 'Five-year key figures p.8 (Revenue 12,495 / 12,134 '
                        'DKK m); income statement p.99; Note 2.1 segment '
                        'table p.101 (Societal Care US 2,730; Societal Care '
                        'Europe 3,815); p.61 names Societal Care US as '
                        'ambulance operations',
             'supplies': 'The largest non-US ambulance group P&L: revenue '
                         'scale and the US ambulance segment',
             'url': FALCK_PDF, 'tier': 'A', 'accessed': accessed,
             'powers': ['Public_Operator_Benchmarks']})

    # ════════════════════════ TAB 1: Input_Cost_Index ═══════════════════════
    ws = wb.create_sheet('Input_Cost_Index')
    sb = lib.SheetBuilder(ws, 10, col_widths=[16, 11.5, 11.5, 11.5, 11.5,
                                              11.5, 11.5, 12, 12, 46],
                          tab_color='FF1F6F8B')
    sb.title('The input-cost index: what running an ambulance costs against '
             'what Medicare pays')
    sb.subtitle('The question: what happened to the measured inputs - diesel '
                'at the pump, industry wages, economy-wide compensation - '
                'against the Ambulance Inflation Factor, the single knob '
                'that moves the Medicare fee schedule? Sources: EIA weekly '
                'on-highway diesel by PADD (annual means), BLS PPI diesel '
                'fuel (WPU0531) and ECEC private total compensation, QCEW '
                'private ambulance pay (green-linked from '
                'QCEW_EMS_Employment), and the AIF (CY2014-2019 verified '
                'against the CMS Pub. 100-04 Ch.15 chart; CY2020+ '
                'green-linked from Payment_Rules). Join key: calendar year. '
                'House rule applied: every series is printed separately; '
                'there is NO blended input basket on this tab.', height=52)
    sb.note('DATA QUALITY: diesel is the retail pump price including taxes '
            '(fleet and bulk purchase prices differ in level; the trend is '
            'the signal). WPU0531 is a producer price index (1982=100), not '
            'a retail price. ECEC is ALL private industry, not EMS-specific. '
            'QCEW pay excludes volunteers and the self-employed. The AIF is '
            'a payment update factor (CPI-U less a productivity offset), a '
            'different basis from any measured input series - gaps are '
            'printed in percentage points, never blended. The PPI ambulance '
            'services industry index (PCU621910621910) DOES NOT EXIST; '
            'parked, with the catalog gap as proof. 2026 rows are partial '
            'years and excluded from every cumulative figure.', height=46)
    sb.blank()

    # Panel A - diesel by PADD
    sb.banner('Panel A. Diesel at the pump: EIA weekly on-highway retail '
              'price, annual means by PADD (dollars per gallon)')
    sb.headers(['Year', 'U.S.', 'PADD 1 East', 'PADD 2 Midwest',
                'PADD 3 Gulf', 'PADD 4 Rocky Mtn', 'PADD 5 West',
                'US YoY', '', 'Note'])
    a0 = sb.r + 1
    for i, y in enumerate(range(2014, 2027)):
        ys = str(y)
        note = None
        if y == 2022:
            note = ('Peak year of the window: the 2022 diesel shock',
                    'note')
        if y == 2026:
            note = (f'YTD mean of {dsl_wk.get(ys)} weekly prints through '
                    f'{dsl_last}; partial year, excluded from cumulatives',
                    'note')
        rn = a0 + i
        sb.row([(y, 'src'),
                *[(dsl[k].get(ys), 'src', lib.FMT_USD2) for k, _ in PADD_KEYS],
                (f'=B{rn}/B{rn - 1}-1' if i else 'n/a',
                 'fml' if i else 'note', lib.FMT_PCT1),
                None, note])
    sb.note('Every cell is the mean of that calendar year\'s weekly prints '
            '(52-53 weeks; 2026 partial). Sub-PADD splits (New England, '
            'Central Atlantic, Lower Atlantic, California) are in the '
            'cached artifact eia_diesel_padd.')
    sb.blank()

    # Panel B - BLS series
    sb.banner('Panel B. BLS input series: PPI diesel fuel and ECEC private '
              'total compensation (annual means of monthly / quarterly '
              'observations)')
    sb.headers(['Year', 'PPI diesel fuel WPU0531 (1982=100)', 'PPI YoY',
                'ECEC private total comp $/hr', 'ECEC YoY', '', '', '', '',
                'Note'])
    b0 = sb.r + 1
    for i, y in enumerate(range(2014, 2027)):
        ys = str(y)
        rn = b0 + i
        note = None
        if y == 2026:
            note = (f'Partial: {ppi_n.get(ys, 0)} PPI months, '
                    f'{ecec_n.get(ys, 0)} ECEC quarter(s); excluded from '
                    'cumulatives', 'note')
        sb.row([(y, 'src'),
                (ppi.get(ys), 'src', lib.FMT_DEC1),
                (f'=B{rn}/B{rn - 1}-1' if i else 'n/a',
                 'fml' if i else 'note', lib.FMT_PCT1),
                (ecec.get(ys), 'src', lib.FMT_DEC2),
                (f'=D{rn}/D{rn - 1}-1' if i else 'n/a',
                 'fml' if i else 'note', lib.FMT_PCT1),
                None, None, None, None, note])
    sb.note('PARKED: PCU621910621910, the PPI industry index for NAICS '
            '621910 ambulance services, does not exist - the BLS pc.series '
            'catalog jumps from 621610 (home health) to 621991 (blood and '
            'organ banks). The API confirms "Series does not exist". What '
            'would fill it: a BLS PPI industry index for NAICS 621910, if '
            'ever published. The fuel PPI (WPU0531) and the ECEC '
            'compensation series above are the closest published legs.')
    sb.blank()

    # Panel C - the divergence table
    sb.banner('Panel C. The AIF against each input series, year by year - '
              'each series its own column, gaps in percentage points, no '
              'blended basket')
    qc = wb['QCEW_EMS_Employment'] if 'QCEW_EMS_Employment' in wb.sheetnames \
        else None
    pr = wb['Payment_Rules'] if 'Payment_Rules' in wb.sheetnames else None
    q_rows = _qcew_panelb_rows(qc) if qc is not None else {}
    p_rows = _payment_rules_aif_rows(pr) if pr is not None else {}
    sb.headers(['Calendar year', 'AIF', 'EMS avg pay $ (QCEW link)',
                'Pay YoY', 'Pay minus AIF (pp)', 'Diesel US YoY',
                'Diesel minus AIF (pp)', 'PPI diesel YoY', 'ECEC YoY',
                'Basis note (same row, house rule)'])
    c0 = sb.r + 1
    for i, y in enumerate(range(2014, 2026)):
        rn = c0 + i
        arow = a0 + (y - 2014)          # Panel A row for this year
        brow = b0 + (y - 2014)          # Panel B row for this year
        if y in p_rows:
            aif_cell = (f"='Payment_Rules'!B{p_rows[y]}", 'link',
                        lib.FMT_PCT1)
            basis = ('AIF green-linked from Payment_Rules (S29); gaps are '
                     'measured-series change minus payment update', 'note')
        else:
            aif_cell = (aif[y], 'src', lib.FMT_PCT1)
            basis = ('AIF re-carried blue from CMS Pub. 100-04 Ch.15 AIF '
                     'chart (p.23 of PDF); gaps are measured minus update',
                     'note')
        pay_cell = (f"='QCEW_EMS_Employment'!D{q_rows[y]}", 'link',
                    lib.FMT_USD) if y in q_rows else ('PENDING', 'note')
        sb.row([(y, 'src'), aif_cell, pay_cell,
                (f'=C{rn}/C{rn - 1}-1' if i else 'n/a',
                 'fml' if i else 'note', lib.FMT_PCT1),
                (f'=D{rn}-B{rn}' if i else 'n/a',
                 'fml' if i else 'note', lib.FMT_PCT1),
                (f'=H{arow}' if i else 'n/a',
                 'fml' if i else 'note', lib.FMT_PCT1),
                (f'=F{rn}-B{rn}' if i else 'n/a',
                 'fml' if i else 'note', lib.FMT_PCT1),
                (f'=C{brow}' if i else 'n/a',
                 'fml' if i else 'note', lib.FMT_PCT1),
                (f'=E{brow}' if i else 'n/a',
                 'fml' if i else 'note', lib.FMT_PCT1),
                basis])
    cl = c0 + 11                        # 2025 row
    sb.blank()
    sb.headers(['Cumulative, 2014 to 2025 (2026 excluded: partial)',
                'Value', '', '', '', '', '', '', '', 'Note'])
    d0 = sb.r + 1
    aif_terms = '*'.join(f'(1+B{c0 + i})' for i in range(1, 12))
    sb.row([('Compounded AIF, CY2015-CY2025', 'label'),
            (f'={aif_terms}-1', 'fml', lib.FMT_PCT1),
            None, None, None, None, None, None, None,
            ('Eleven annual updates compounded; a factor path, not an '
             'index', 'note')])
    sb.row([('Private ambulance avg pay growth, 2014-2025 (QCEW)', 'label'),
            (f'=C{cl}/C{c0}-1', 'fml', lib.FMT_PCT1),
            None, None, None, None, None, None, None,
            ('Measured level change; excludes volunteers', 'note')])
    sb.row([('THE SCISSORS: pay growth minus compounded AIF (pp)', 'label'),
            (f'=B{d0 + 1}-B{d0}', 'fml', lib.FMT_PCT1),
            None, None, None, None, None, None, None,
            ('The annual full-basket extension of the quarterly scissors on '
             'QCEW_EMS_Employment; bases differ (level vs update factor), '
             'which is why this is a gap in pp, not a ratio', 'note')])
    sb.row([('ECEC private total comp growth, 2014-2025', 'label'),
            (f'=D{b0 + 11}/D{b0}-1', 'fml', lib.FMT_PCT1),
            None, None, None, None, None, None, None,
            ('All private industry, not EMS-specific', 'note')])
    sb.row([('Diesel US retail change, 2014-2025', 'label'),
            (f'=B{a0 + 11}/B{a0}-1', 'fml', lib.FMT_PCT1),
            None, None, None, None, None, None, None,
            ('2025 pump price sits BELOW 2014; the 2022 shock washed out',
             'note')])
    sb.row([('PPI diesel fuel change, 2014-2025', 'label'),
            (f'=B{b0 + 11}/B{b0}-1', 'fml', lib.FMT_PCT1),
            None, None, None, None, None, None, None,
            ('Producer index change; same wash-out as retail', 'note')])
    sb.row([('Input series that outgrew the compounded AIF, of the four '
             'printed', 'label'),
            (f'=IF(B{d0 + 1}>B{d0},1,0)+IF(B{d0 + 3}>B{d0},1,0)'
             f'+IF(B{d0 + 4}>B{d0},1,0)+IF(B{d0 + 5}>B{d0},1,0)',
             'fml', lib.FMT_INT),
            None, None, None, None, None, None, None,
            ('Both labor legs outgrew the update; both fuel legs did not - '
             'and labor is the dominant ambulance cost line', 'note')])
    sb.blank()
    sb.banner('Read panel')
    sb.prose('What is measured: the payment update and the input series '
             'diverge on the labor side, not the fuel side. Compounded '
             f'CY2015-CY2025 AIF is about {aif_cum:.1%}; private ambulance '
             f'pay grew about {pay_cum:.1%} over the same span (gap about '
             f'{scissors * 100:.0f} pp) and economy-wide private total '
             f'compensation about {ecec_cum:.1%}. Fuel cuts the other way '
             'across the full window: 2025 diesel sits below its 2014 level '
             'at retail and in the PPI - but the path is violent, with a '
             f'{dsl_swing:.0%} single-year US retail jump in 2022 that the '
             'CY2023 AIF (8.7%, the largest since 2002) chased with a lag. '
             'What is NOT measured: any blended cost index - the series '
             'have different bases and are never combined; and the PPI for '
             'the ambulance industry itself, which BLS does not publish.')

    ch_anchor = 'L6'
    lib.add_chart(ws, ch_anchor, 'On-highway diesel, annual mean by PADD '
                  '($/gal)',
                  f"'Input_Cost_Index'!$A${a0}:$A${a0 + 12}",
                  [(nm, f"'Input_Cost_Index'!${chr(66 + j)}${a0}:"
                        f"${chr(66 + j)}${a0 + 12}")
                   for j, (_, nm) in enumerate(PADD_KEYS)],
                  kind='line', y_fmt='$0.00')
    lib.add_chart(ws, 'L20', 'Annual update vs the wage leg: AIF and private '
                  'EMS pay YoY',
                  f"'Input_Cost_Index'!$A${c0 + 1}:$A${cl}",
                  [('AIF', f"'Input_Cost_Index'!$B${c0 + 1}:$B${cl}"),
                   ('EMS avg pay YoY',
                    f"'Input_Cost_Index'!$D${c0 + 1}:$D${cl}")],
                  kind='line', y_fmt='0.0%')

    # ════════════════════ TAB 2: Public_Operator_Benchmarks ═════════════════
    dg = edgar['docgo']['annual_revenues']
    mc = edgar['modivcare']['annual_revenues']
    mc_ytd = edgar['modivcare'].get('latest_interim_ytd') or {}

    ws2 = wb.create_sheet('Public_Operator_Benchmarks')
    sb = lib.SheetBuilder(ws2, 9, col_widths=[44, 13, 13, 13, 13, 13, 13,
                                              13, 46],
                          tab_color='FF7A5195')
    sb.title('Public-operator benchmarks: the listed ambulance and '
             'transport-medicine P&Ls')
    sb.subtitle('The question: what do listed-operator disclosures establish '
                'about ambulance revenue scale and per-trip economics? '
                'Sources: SEC EDGAR XBRL companyfacts for DocGo Inc. (CIK '
                '1822359) and ModivCare Inc. (CIK 1220754), each cell '
                'carrying its filing accession; DocGo trips and average trip '
                'price green-linked from Facility_Pay_Layer Panel B (10-K '
                'primary); Falck A/S Annual Report 2025 for the largest '
                'non-US ambulance group. Join key: fiscal year (all three '
                'report calendar fiscal years).', height=42)
    sb.note('DATA QUALITY: two US-listed operators and one Danish group are '
            'NOT the market - the US industry is thousands of mostly '
            'private and municipal services (see Supplier_Landscape). DocGo '
            'trips/ATP exclude dedicated-unit hourly programs by the filing '
            'definition. ModivCare is a NEMT benefits BROKER, not an '
            'ambulance operator: carried only as the NEMT-adjacent boundary '
            'reference. ModivCare FY2025 annual figures are not in '
            'companyfacts as of 11 Jul 2026 (latest filed period Q3 2025); '
            'the FY2025 row is PENDING, not zero. Falck figures are DKK '
            'million, IFRS, no currency conversion applied.', height=46)
    sb.blank()

    # Panel A - DocGo
    sb.banner('Panel A. DocGo Inc. - the only US-listed pure-play medical '
              'transport P&L (USD)')
    sb.headers(['Metric', 'FY2025', 'FY2024', 'FY2023', 'FY2022', 'FY2021',
                'FY2020', 'FY2019', 'Locator'])
    pa0 = sb.r + 1
    dg_loc = ('companyfacts us-gaap Revenues; FY25-FY23 accn '
              '0001628280-26-018214 (FY2025 10-K); FY22 accn '
              '0001822359-25-000018; FY21 accn 0001822359-24-000016; '
              'FY20 accn 0001213900-22-012545')
    sb.row([('Total revenue $', 'label'),
            *[(dg[str(y)]['val'], 'src', lib.FMT_USD) if str(y) in dg
              else ('n/a - pre-listing', 'note')
              for y in range(2025, 2018, -1)],
            (dg_loc, 'note')], wrap=False)
    fpl = wb['Facility_Pay_Layer'] if 'Facility_Pay_Layer' in wb.sheetnames \
        else None
    seg = trips = atp = imp = None
    if fpl is not None:
        seg = _find_label(fpl, 'transportation services segment revenue')
        trips = _find_label(fpl, 'trips (per-trip billed')
        atp = _find_label(fpl, 'average trip price')
        imp = _find_label(fpl, 'implied per-trip billed revenue')

    def _fpl_cells(hit, label, fmt, locator):
        if hit:
            r = hit[0]
            # Facility_Pay_Layer Panel B geometry: B=FY2025, C=FY2024,
            # D=FY2023 (verified by scan in the smoke test)
            sb.row([(label, 'label'),
                    (f"='Facility_Pay_Layer'!B{r}", 'link', fmt),
                    (f"='Facility_Pay_Layer'!C{r}", 'link', fmt),
                    (f"='Facility_Pay_Layer'!D{r}", 'link', fmt),
                    None, None, None, None, (locator, 'note')])
        else:
            sb.row([(label, 'label'), ('PENDING', 'note'), None, None, None,
                    None, None, None,
                    ('Facility_Pay_Layer (B.1) not present in this build; '
                     'fills from DocGo 10-K Note 2/Note 11 and MD&A',
                     'note')])

    _fpl_cells(seg, 'Transportation Services segment revenue $ (link)',
               lib.FMT_USD,
               'Facility_Pay_Layer Panel B; 10-K Note 2 (F-22), Note 11 '
               '(F-37)')
    seg_row = sb.r
    sb.row([('Transportation share of total revenue', 'label'),
            (f'=B{seg_row}/B{pa0}', 'fml', lib.FMT_PCT1),
            (f'=C{seg_row}/C{pa0}', 'fml', lib.FMT_PCT1),
            (f'=D{seg_row}/D{pa0}', 'fml', lib.FMT_PCT1),
            None, None, None, None,
            ('DERIVED live; the FY2025 jump is the Mobile Health wind-down '
             '(migrant-services contracts), not transport growth - the '
             'confound sits in the denominator', 'note')])
    share_row = sb.r
    _fpl_cells(trips, 'Trips (per-trip billed only) (link)', lib.FMT_INT,
               'Facility_Pay_Layer Panel B; MD&A pp.62/66')
    _fpl_cells(atp, 'Average trip price $ (link)', lib.FMT_USD,
               'Facility_Pay_Layer Panel B; MD&A pp.57/62/66')
    atp_row = sb.r
    _fpl_cells(imp, 'Implied per-trip billed revenue $ (link)', lib.FMT_USD,
               'Facility_Pay_Layer Panel B; trips x ATP, live there')
    sb.note('The per-trip economics DocGo disclosure establishes: a public '
            'trip count, a public average trip price, and (on '
            'Facility_Pay_Layer) the measured share of transport revenue '
            'that never touches a per-trip claim. No other US filer '
            'discloses any of the three.')
    sb.blank()

    # Panel B - ModivCare
    sb.banner('Panel B. ModivCare Inc. - the NEMT-adjacent boundary '
              'reference (USD)')
    sb.headers(['Metric', 'FY2025', 'FY2024', 'FY2023', 'FY2022', 'FY2021',
                'FY2020', 'FY2019', 'Locator'])
    pb0 = sb.r + 1
    mc_loc = ('companyfacts RevenueFromContractWithCustomerExcluding'
              'AssessedTax; FY24-FY23 accn 0001220754-25-000008; FY22-FY21 '
              'accn 0001220754-25-000008 / 0001220754-24-000014; FY20 accn '
              '0001220754-23-000009; FY19 accn 0001220754-22-000007')
    sb.row([('Service revenue $', 'label'),
            ('PENDING', 'note'),
            *[(mc[str(y)]['val'], 'src', lib.FMT_USD) if str(y) in mc
              else None for y in range(2024, 2018, -1)],
            (mc_loc, 'note')])
    sb.row([('FY2025 status', 'label'),
            (mc_ytd.get('val'), 'src', lib.FMT_USD), None, None, None, None,
            None, None,
            (f'9M-2025 YTD revenue (Q3 10-Q accn {mc_ytd.get("accn")}); the '
             'FY2025 annual report is not in companyfacts as of 11 Jul '
             '2026 - the PENDING cell fills from SEC companyfacts CIK '
             '1220754 when the annual filing lands', 'note')])
    sb.row([('Boundary framing', 'label'), None, None, None, None, None,
            None, None, None])
    sb.prose('NEMT-adjacent boundary reference: ModivCare is a non-emergency '
             'medical transportation BENEFITS BROKER - it prices per-member '
             'trip-benefit management for Medicaid and MA plans and '
             'subcontracts the driving. Its book is the adjacent NEMT '
             'channel, NOT ground-ambulance interfacility transport; it is '
             'carried here to bound the payer-funded transport-benefit '
             'economy around the IFT boundary, never summed with ambulance '
             'revenue.', kind='note')
    sb.blank()

    # Panel C - Falck
    sb.banner('Panel C. Falck A/S - the largest non-US ambulance group '
              '(DKK million, IFRS)')
    sb.headers(['Metric', 'FY2025', 'FY2024', '', '', '', '', '', 'Locator'])
    pc0 = sb.r + 1
    if falck:
        sb.row([('Group revenue, DKK m', 'label'),
                (12495, 'src', lib.FMT_INT), (12134, 'src', lib.FMT_INT),
                None, None, None, None, None,
                ('Annual Report 2025, five-year key figures p.8; income '
                 'statement p.99; segment note 2.1 p.101', 'note')])
        sb.row([('Societal Care US (ambulance operations), DKK m', 'label'),
                (2730, 'src', lib.FMT_INT), (2793, 'src', lib.FMT_INT),
                None, None, None, None, None,
                ('Note 2.1 p.101; p.61 names Societal Care US as ambulance '
                 'operations; revenue DECLINED year over year', 'note')])
        sb.row([('Societal Care Europe (ambulance + social care), DKK m',
                 'label'),
                (3815, 'src', lib.FMT_INT), (3612, 'src', lib.FMT_INT),
                None, None, None, None, None,
                ('Note 2.1 p.101; includes non-ambulance social care - a '
                 'ceiling on the Europe ambulance book, stated in-row',
                 'note')])
        sb.note('Falck is carried in DKK with no currency conversion (a '
                'conversion would need a sourced FX rate and adds nothing '
                'to the boundary read). Trip-level metrics exist in the '
                'sustainability statement (Ambulance service rows, p.78) '
                'but the year-column mapping is not machine-verifiable from '
                'the PDF text layer; not carried.')
    else:
        sb.row([('Group revenue, DKK m', 'label'), ('PENDING', 'note'),
                None, None, None, None, None, None,
                ('Falck Annual Report PDF not retrieved; fills from ' +
                 FALCK_PDF, 'note')])
    sb.blank()

    # Panel D - the per-trip economics read
    sb.banner('Panel D. The per-trip economics read (live links; confound '
              'printed in-row)')
    pr_cf = _find_label(wb['Payment_Rules'],
                        'ground ambulance conversion factor') \
        if 'Payment_Rules' in wb.sheetnames else None
    pd0 = sb.r + 1
    sb.row([('Medicare ground conversion factor, CY2024 $ (link)', 'label'),
            (f"='Payment_Rules'!B{pr_cf[0]}", 'link', lib.FMT_USD2)
            if pr_cf else ('PENDING', 'note'),
            None, None, None, None, None, None,
            ('Payment_Rules; MedPAC Payment Basics Oct 2024', 'note')])
    sb.row([('DocGo FY2025 average trip price over the Medicare CF', 'label'),
            (f'=IF(OR(ISTEXT(B{atp_row}),ISTEXT(B{pd0})),"PENDING",'
             f'B{atp_row}/B{pd0})', 'fml', lib.FMT_X),
            None, None, None, None, None, None,
            ('CONFOUND, same row: ATP blends all payers, service levels, '
             'mileage and contracted rates; the CF is the unadjusted '
             'Medicare base before RVU, GPCI and add-ons. A framing ratio '
             'only, never a rate benchmark.', 'note')])
    sb.note('REFRESH: the repo pipeline re-pulls both companyfacts files - '
            'rcm_mc/data_public/public_api_clients.py '
            '(sec_companyfacts_request, client key "sec_edgar"), run via '
            'python -m rcm_mc.data_public.corpus_cli full-ingest --db '
            'corpus.db --sec-edgar; the scratchpad pull is pull14.py '
            '(edgar_operator_facts).')
    sb.blank()
    sb.banner('Read panel')
    sb.prose('What listed-operator disclosure establishes: existence and '
             'scale, and exactly one public per-trip price. DocGo prices '
             'about 296K trips at a $401 average - transportation is now '
             'about 62% of its shrinking total - and Facility_Pay_Layer '
             'shows 41% of that segment arriving outside per-trip claims. '
             'ModivCare books $2.8B a year brokering NEMT benefits without '
             'operating ambulances, and its FY2025 annual report had not '
             'reached companyfacts by 11 Jul 2026. Falck runs a DKK 2.7B '
             'US ambulance segment with no public trip denominator. What '
             'is NOT established: market-level per-trip economics - two '
             'US-listed operators and one Danish group are a corner of a '
             'market that is mostly private and municipal.')

    # ── facts ────────────────────────────────────────────────────────────────
    facts += [
        {'metric': 'Private ambulance average pay growth minus compounded '
                   'AIF, 2014-2025 (the annual full-basket scissors)',
         'year': 2025, 'value': round(scissors, 4),
         'unit': 'percentage points, as share', 'basis': 'DERIVED',
         'tier': 'A', 'source_keys': ['qcew_wage', 'cms_aif_manual'],
         'locator': 'Input_Cost_Index Panel C cumulative block (live); pay '
                    'legs QCEW US000 own 5 avg_annual_pay 2014/2025; AIF '
                    'legs Pub 100-04 Ch.15 chart p.23 + Payment_Rules S29',
         'lives_on': 'Input_Cost_Index',
         'cross_check': f'Pay {pay_cum:.1%} vs compounded AIF {aif_cum:.1%}; '
                        'the quarterly wage scissors on QCEW_EMS_Employment '
                        'is the same phenomenon on a shorter window'},
        {'metric': 'US on-highway diesel retail, peak single-year swing '
                   '(2022 annual mean vs 2021)', 'year': 2022,
         'value': round(dsl_swing, 4), 'unit': 'share change YoY',
         'basis': 'GOV', 'tier': 'A', 'source_keys': ['eia_diesel'],
         'locator': 'EIA psw18vwall.xls, EMD_EPD2D_PTE_NUS_DPG weekly, '
                    'annual means '
                    f"{dsl['EMD_EPD2D_PTE_NUS_DPG']['2022']:.3f} vs "
                    f"{dsl['EMD_EPD2D_PTE_NUS_DPG']['2021']:.3f} $/gal; "
                    'Input_Cost_Index Panel A',
         'lives_on': 'Input_Cost_Index',
         'cross_check': 'The CY2023 AIF of 8.7% (largest since 2002) is the '
                        'lagged CPI response to this shock'},
        {'metric': 'PPI diesel fuel cumulative change 2014-2025 minus '
                   'compounded AIF (the fuel-leg gap)', 'year': 2025,
         'value': round(ppi_gap, 4), 'unit': 'percentage points, as share',
         'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['bls_input', 'cms_aif_manual'],
         'locator': 'WPU0531 annual means 99.8 (2025) vs 182.4 (2014); '
                    'Input_Cost_Index Panels B and C',
         'lives_on': 'Input_Cost_Index',
         'cross_check': 'Fuel deflated over the full window while the '
                        'update compounded +27.8%; the intended PPI '
                        'ambulance industry series (PCU621910621910) does '
                        'not exist and is parked with catalog proof'},
        {'metric': 'ModivCare service revenue, FY2024 (latest annual filing '
                   'in companyfacts)', 'year': 2024,
         'value': mc['2024']['val'], 'unit': 'USD', 'basis': 'SEC-A',
         'tier': 'A', 'source_keys': ['edgar_companyfacts'],
         'locator': 'companyfacts CIK 1220754, RevenueFromContractWith'
                    'CustomerExcludingAssessedTax, FY2024, accn '
                    '0001220754-25-000008',
         'lives_on': 'Public_Operator_Benchmarks',
         'cross_check': 'FY2025 annual is PENDING (not in companyfacts '
                        f'11 Jul 2026); 9M-2025 YTD {mc_ytd.get("val", 0):,}'
                        ' per Q3 10-Q - NEMT brokerage, outside the '
                        'ambulance boundary'},
        {'metric': 'DocGo Transportation Services share of total revenue, '
                   'FY2025', 'year': 2025,
         'value': round(200765608 / dg['2025']['val'], 4), 'unit': 'share',
         'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['edgar_companyfacts'],
         'locator': 'Numerator: Facility_Pay_Layer Panel B (10-K Note 11, '
                    'F-37); denominator: companyfacts Revenues FY2025 '
                    f'{dg["2025"]["val"]:,}, accn 0001628280-26-018214; '
                    'live on Public_Operator_Benchmarks Panel A',
         'lives_on': 'Public_Operator_Benchmarks',
         'cross_check': 'Share rose from about a third in FY2023-24 because '
                        'total revenue FELL (Mobile Health wind-down), not '
                        'because transport grew'},
    ]

    findings += [
        {'id_hint': 80,
         'finding': 'The Medicare payment update lags the measured input '
                    'basket exactly where the money is: on the two labor '
                    'series (private ambulance pay +71%, economy-wide '
                    'private compensation +51%, 2014-2025) the compounded '
                    'AIF of about +28% falls 23-43 pp short, while both '
                    'fuel series (retail diesel, PPI diesel) end 2025 below '
                    'their 2014 level after a +52% single-year shock in '
                    '2022 - so 2 of the 4 printed input series outgrew the '
                    'update, and they are the labor ones.',
         'numbers': f"='Input_Cost_Index'!B{d0 + 2}",
         'sources': 'qcew_wage; cms_aif_manual; eia_diesel; bls_input',
         'confidence': 'High: every leg is a federal series or the CMS '
                       'manual chart, and the arithmetic is live on the tab',
         'guardrail': 'Series bases differ - the AIF is a fee-schedule '
                      'update factor, the others are measured indexes and '
                      'levels - so gaps are printed per series in pp and '
                      'NO blended input basket exists on this tab; the PPI '
                      'ambulance industry index does not exist at BLS.'},
        {'id_hint': 81,
         'finding': 'Listed-operator disclosure establishes existence, '
                    'scale and exactly one public per-trip price for US '
                    'ground ambulance: DocGo (the only US-listed pure '
                    'play) discloses about 296K per-trip-billed trips at a '
                    '$401 average trip price, with transportation about 62% '
                    'of FY2025 total revenue; ModivCare brokers a $2.8B '
                    'NEMT benefit without operating ambulances; Falck '
                    'reports a DKK 2,730m US ambulance segment with no '
                    'trip denominator.',
         'numbers': f"='Public_Operator_Benchmarks'!B{share_row}",
         'sources': 'edgar_companyfacts' + ('; falck_ar2025' if falck
                                            else ''),
         'confidence': 'High on the disclosures themselves; audited '
                       'filings with accession locators',
         'guardrail': 'Two US-listed operators and one Danish group are '
                      'not the market; DocGo ATP blends payers and '
                      'excludes dedicated-unit hourly programs; ModivCare '
                      'is NEMT-adjacent boundary reference only, never '
                      'summed with ambulance revenue.'},
    ]

    return {'facts': facts, 'sources': sources, 'excluded': excluded,
            'findings': findings,
            'meta': {'parked': [
                f'{PPI_AMB_PARKED}: PPI ambulance industry index does not '
                'exist (BLS pc.series catalog gap 621610 -> 621991)',
                'ModivCare FY2025 annual: not in companyfacts as of 11 Jul '
                '2026; PENDING cell on Public_Operator_Benchmarks'],
                'pull': 'pull14.py (eia_diesel_padd, bls_input_series, '
                        'edgar_operator_facts, falck_annual_report, '
                        'cms_aif_history)'}}
