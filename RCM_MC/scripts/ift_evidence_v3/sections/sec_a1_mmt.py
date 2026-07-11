"""A.1: MMT_Medicare_Book - the subject company's measured public Medicare
fee-for-service ambulance book, rolled up from the provider-grain registry
for every NPI on MMT_NPI_Estate, vintages 2013 / 2019 / 2024.

Everything on this tab is Medicare FFS final-action data (MUP by Provider
and Service) - the measured PUBLIC floor of the book, roughly one-sixth of
the market by this workbook's own payer arithmetic.
"""

SHEETS = [{'name': 'MMT_Medicare_Book',
           'question': 'What does the subject company measurably bill '
                       'Medicare FFS, at what acuity mix, price and '
                       'trajectory?'}]

BASE = ['A0426', 'A0427', 'A0428', 'A0429', 'A0433', 'A0434']
AIR = ['A0430', 'A0431', 'A0435', 'A0436']
MILE = 'A0425'
CODES = [MILE] + BASE + AIR
LEVEL = {'A0426': 'ALS non-emergency', 'A0427': 'ALS emergency',
         'A0428': 'BLS non-emergency', 'A0429': 'BLS emergency',
         'A0433': 'ALS level 2', 'A0434': 'SCT'}
# Ambulance Fee Schedule relative value units, frozen since 2002; the same
# constants carried on Payment_Rules.
RVU = {'A0428': 1.00, 'A0429': 1.60, 'A0426': 1.20, 'A0427': 1.90,
       'A0433': 2.75, 'A0434': 3.25}
VINTAGES = ('2013', '2019', '2024')


def _f(v):
    try:
        return float(str(v).replace(',', '').replace('$', ''))
    except (TypeError, ValueError):
        return None


def _npis_from_estate(wb):
    """Harvest the registered NPI list (and any name column) from
    MMT_NPI_Estate - the public NPPES registrations already carried."""
    ws = wb['MMT_NPI_Estate']
    npis = {}
    for row in ws.iter_rows():
        for i, c in enumerate(row):
            v = c.value
            npi = None
            if isinstance(v, (int, float)) and 1e9 <= v < 2e9:
                npi = str(int(v))
            elif isinstance(v, str) and v.strip().isdigit() and len(v.strip()) == 10:
                npi = v.strip()
            if npi:
                name = None
                for c2 in row[i + 1:i + 3]:
                    if isinstance(c2.value, str) and len(c2.value) > 3:
                        name = c2.value
                        break
                npis.setdefault(npi, name)
    return npis


def build(wb, ctx):
    lib = ctx['lib']
    cache = ctx['cache']
    facts, sources, excluded, findings = [], [], [], []

    estate = _npis_from_estate(wb)
    npiset = set(estate)

    # per vintage: rows for estate NPIs
    per = {}
    present = {}
    for yr in VINTAGES:
        rows = []
        for code in CODES:
            try:
                rows += [r for r in lib.load_cache(cache, f'mup_provider_{yr}_{code}')
                         if str(r.get('Rndrng_NPI')) in npiset]
            except FileNotFoundError:
                continue
        per[yr] = rows
        present[yr] = {str(r.get('Rndrng_NPI')) for r in rows}

    def agg(rows, codes):
        srv = ben = alw = pay = 0.0
        for r in rows:
            if r.get('HCPCS_Cd') not in codes:
                continue
            s = _f(r.get('Tot_Srvcs')) or 0
            srv += s
            ben += _f(r.get('Tot_Benes')) or 0
            alw += s * (_f(r.get('Avg_Mdcr_Alowd_Amt')) or 0)
            pay += s * (_f(r.get('Avg_Mdcr_Pymt_Amt')) or 0)
        return srv, ben, alw, pay

    sources.append(
        {'key': 'mmt_book_mup', 'publisher': 'CMS',
         'document': 'Medicare Physician & Other Practitioners by Provider '
                     'and Service - subject-company NPI roll-up (2013, 2019, '
                     '2024 vintages already manifested)',
         'vintage': '2013 / 2019 / 2024 final-action',
         'locator': 'Rows where Rndrng_NPI is one of the registered NPIs on '
                    'MMT_NPI_Estate (public NPPES registrations)',
         'supplies': 'The measured public Medicare FFS book of the subject '
                     'company: volumes, realized prices, acuity mix, mileage',
         'url': 'https://data.cms.gov/provider-summary-by-type-of-service/'
                'medicare-physician-other-practitioners/medicare-physician-'
                'other-practitioners-by-provider-and-service',
         'tier': 'A', 'accessed': ctx['accessed'],
         'powers': ['MMT_Medicare_Book']})

    ws = wb.create_sheet('MMT_Medicare_Book')
    sb = lib.SheetBuilder(ws, 10,
                          col_widths=[34, 13, 13, 13, 13, 13, 13, 13, 13, 30],
                          tab_color='FF8C1D40')
    sb.title('The subject company, measured: Medicare FFS ambulance book by '
             'NPI, 2013 / 2019 / 2024')
    sb.subtitle('The question: what does the subject company measurably bill '
                'Medicare fee-for-service - volume, realized price, acuity '
                'mix, mileage intensity and trajectory - from public '
                'provider-grain claims summaries alone? Roll-up of the '
                f'{len(npiset)} registered NPIs on MMT_NPI_Estate across '
                'MUP_Providers_2013/2019/2024. Medicare FFS is roughly '
                'one-sixth of the market by this workbook\'s own payer '
                'arithmetic (GADCS Table S.1: FFS 29% of revenue per NPI on '
                'average, and enrollment splits): this tab is the measured '
                'PUBLIC FLOOR of the book, not the book.')
    sb.note('DATA QUALITY: per-NPI code rows with 10 or fewer beneficiaries '
            'are suppressed at source, so every figure is a floor; '
            'final-action basis; NPIs enumerated after a vintage year '
            'cannot appear in it (Panel F states which and why); billing '
            'under a parent or billing-agent NPI is invisible here.')
    sb.blank()

    sb.banner('Panel A. Consolidated book by vintage (ground base codes '
              'A0426-A0429, A0433, A0434)')
    sb.headers(['Vintage', 'NPIs present', 'Base services (floor)',
                'Beneficiary-code rows (floor)', 'Allowed $', 'Paid $',
                'Allowed per base service $', 'Paid share of allowed', '',
                'Note'])
    a0 = sb.r + 1
    for i, yr in enumerate(VINTAGES):
        srv, ben, alw, pay = agg(per[yr], set(BASE))
        rn = a0 + i
        sb.row([(yr, 'src'), (len(present[yr]), 'fml', lib.FMT_INT),
                (round(srv), 'src', lib.FMT_INT),
                (round(ben), 'src', lib.FMT_INT),
                (round(alw), 'src', lib.FMT_USD),
                (round(pay), 'src', lib.FMT_USD),
                (f'=IF(C{rn}=0,"n/a",E{rn}/C{rn})', 'fml', lib.FMT_USD2),
                (f'=IF(E{rn}=0,"n/a",F{rn}/E{rn})', 'fml', lib.FMT_PCT1),
                None,
                ('beneficiaries summed over code rows: not unique patients',
                 'note') if i == 0 else None])
    sb.blank()

    sb.banner('Panel B. Acuity mix by vintage (share of base services) and '
              'the volume-weighted RVU')
    sb.headers(['Level (HCPCS)', '2013 services', '2019 services',
                '2024 services', '2013 share', '2019 share', '2024 share',
                'AFS RVU', '', ''])
    b0 = sb.r + 1
    code_srv = {yr: {} for yr in VINTAGES}
    for yr in VINTAGES:
        for code in BASE:
            code_srv[yr][code] = agg(per[yr], {code})[0]
    for j, code in enumerate(BASE):
        rn = b0 + j
        tot_refs = {yr: f'{chr(66 + k)}$'
                    for k, yr in enumerate(VINTAGES)}
        sb.row([(f'{LEVEL[code]} ({code})', 'text'),
                (round(code_srv['2013'][code]), 'src', lib.FMT_INT),
                (round(code_srv['2019'][code]), 'src', lib.FMT_INT),
                (round(code_srv['2024'][code]), 'src', lib.FMT_INT),
                (f'=IF(SUM(B${b0}:B${b0 + 5})=0,"n/a",'
                 f'B{rn}/SUM(B${b0}:B${b0 + 5}))', 'fml', lib.FMT_PCT1),
                (f'=IF(SUM(C${b0}:C${b0 + 5})=0,"n/a",'
                 f'C{rn}/SUM(C${b0}:C${b0 + 5}))', 'fml', lib.FMT_PCT1),
                (f'=IF(SUM(D${b0}:D${b0 + 5})=0,"n/a",'
                 f'D{rn}/SUM(D${b0}:D${b0 + 5}))', 'fml', lib.FMT_PCT1),
                (RVU[code], 'src', lib.FMT_DEC2), None,
                ('RVUs frozen since 2002; same constants as Payment_Rules',
                 'note') if j == 0 else None])
    rw = b0 + len(BASE)
    sb.row([('Volume-weighted RVU (live)', 'label'), None, None, None,
            (f'=IF(SUM(B{b0}:B{rw - 1})=0,"n/a",SUMPRODUCT(B{b0}:B{rw - 1},'
             f'H{b0}:H{rw - 1})/SUM(B{b0}:B{rw - 1}))', 'fml', lib.FMT_DEC2),
            (f'=IF(SUM(C{b0}:C{rw - 1})=0,"n/a",SUMPRODUCT(C{b0}:C{rw - 1},'
             f'H{b0}:H{rw - 1})/SUM(C{b0}:C{rw - 1}))', 'fml', lib.FMT_DEC2),
            (f'=IF(SUM(D{b0}:D{rw - 1})=0,"n/a",SUMPRODUCT(D{b0}:D{rw - 1},'
             f'H{b0}:H{rw - 1})/SUM(D{b0}:D{rw - 1}))', 'fml', lib.FMT_DEC2),
            None, None,
            ('acuity in one number: rises only if the mix shifts up', 'note')])
    sb.blank()

    sb.banner('Panel C. Mileage economics (A0425 ground mileage)')
    sb.headers(['Vintage', 'Mileage units (floor)', 'Base services (link)',
                'Implied avg loaded miles per transport',
                'Mileage allowed $', 'Mileage share of total allowed', '', '',
                '', ''])
    c0 = sb.r + 1
    for i, yr in enumerate(VINTAGES):
        m_srv, _, m_alw, _ = agg(per[yr], {MILE})
        rn = c0 + i
        sb.row([(yr, 'src'), (round(m_srv), 'src', lib.FMT_INT),
                (f'=C{a0 + i}', 'link', lib.FMT_INT),
                (f'=IF(C{rn}=0,"n/a",B{rn}/C{rn})', 'fml', lib.FMT_DEC1),
                (round(m_alw), 'src', lib.FMT_USD),
                (f'=IF((E{rn}+E{a0 + i})=0,"n/a",E{rn}/(E{rn}+E{a0 + i}))',
                 'fml', lib.FMT_PCT1), None, None, None, None])
    sb.note('Implied miles are mileage UNITS divided by base transports: a '
            'floor over a floor, so read the level cautiously and the trend '
            'directionally. Air codes are excluded from every ground panel; '
            'any air rows in the registry are shown in Panel F.')
    sb.blank()

    sb.banner('Panel D. Trajectory (live CAGRs over Panel A)')
    sb.headers(['Metric', '2013 to 2019 CAGR', '2019 to 2024 CAGR',
                '2013 to 2024 CAGR', '', '', '', '', '', ''])
    for label, col in [('Base services', 'C'), ('Allowed $', 'E'),
                       ('Allowed per service $', 'G')]:
        sb.row([(label, 'label'),
                (f'=IF({col}{a0}=0,"n/a",({col}{a0 + 1}/{col}{a0})^(1/6)-1)',
                 'fml', lib.FMT_PCT1),
                (f'=IF({col}{a0 + 1}=0,"n/a",({col}{a0 + 2}/{col}{a0 + 1})'
                 '^(1/5)-1)', 'fml', lib.FMT_PCT1),
                (f'=IF({col}{a0}=0,"n/a",({col}{a0 + 2}/{col}{a0})^(1/11)-1)',
                 'fml', lib.FMT_PCT1), None, None, None, None, None, None])
    sb.blank()

    sb.banner('Panel E. Per-NPI book, 2024 (the granular floor)')
    sb.headers(['NPI', 'Registered name (NPPES)', 'State', 'City',
                'Base services', 'Allowed $', 'Paid $',
                'Allowed per service $', 'Mileage units', ''])
    e0 = sb.r + 1
    npi_rows = {}
    for r in per['2024']:
        npi = str(r.get('Rndrng_NPI'))
        d = npi_rows.setdefault(npi, {'state': r.get('Rndrng_Prvdr_State_Abrvtn'),
                                      'city': r.get('Rndrng_Prvdr_City'),
                                      'name': r.get('Rndrng_Prvdr_Last_Org_Name'),
                                      'srv': 0, 'alw': 0, 'pay': 0, 'mile': 0})
        s = _f(r.get('Tot_Srvcs')) or 0
        if r.get('HCPCS_Cd') in BASE:
            d['srv'] += s
            d['alw'] += s * (_f(r.get('Avg_Mdcr_Alowd_Amt')) or 0)
            d['pay'] += s * (_f(r.get('Avg_Mdcr_Pymt_Amt')) or 0)
        elif r.get('HCPCS_Cd') == MILE:
            d['mile'] += s
    for i, (npi, d) in enumerate(sorted(npi_rows.items(),
                                        key=lambda kv: -kv[1]['srv'])):
        rn = e0 + i
        sb.row([(npi, 'src'), (d['name'] or estate.get(npi), 'src'),
                (d['state'], 'src'), (d['city'], 'src'),
                (round(d['srv']), 'src', lib.FMT_INT),
                (round(d['alw']), 'src', lib.FMT_USD),
                (round(d['pay']), 'src', lib.FMT_USD),
                (f'=IF(E{rn}=0,"n/a",F{rn}/E{rn})', 'fml', lib.FMT_USD2),
                (round(d['mile']), 'src', lib.FMT_INT), None])
    sb.blank()

    sb.banner('Panel F. NPI resolution by vintage (which registered NPIs '
              'appear, and why absences are expected)')
    sb.headers(['NPI', 'Registered name', 'In 2013', 'In 2019', 'In 2024',
                'Reading', '', '', '', ''])
    for npi in sorted(npiset):
        marks = ['Y' if npi in present[yr] else '-' for yr in VINTAGES]
        if marks == ['-', '-', '-']:
            why = ('Never resolves: suppression floor (every code under 11 '
                   'beneficiaries), enumerated after 2024, or bills under '
                   'another NPI')
        elif marks[0] == '-':
            why = ('Absent early vintages: enumerated later, below the '
                   'suppression floor, or volume consolidated on another NPI')
        else:
            why = 'Resolves across vintages'
        sb.row([(npi, 'src'), (estate.get(npi), 'src'),
                marks[0], marks[1], marks[2], (why, 'note'),
                None, None, None, None])
    sb.blank()

    srv24, _, alw24, pay24 = agg(per['2024'], set(BASE))
    srv19 = agg(per['2019'], set(BASE))[0]
    sct24 = code_srv['2024']['A0434']
    mile24 = agg(per['2024'], {MILE})[0]

    sb.banner('Read panel')
    sb.prose('The measured floor and its shape: the registered NPI estate '
             f'bills Medicare FFS about {round(srv24):,} ground base '
             f'transports in 2024 (allowed about ${alw24 / 1e6:,.1f}M), '
             'roughly seven times the 2013 floor, and the mix moved '
             'decisively to BLS non-emergency (28.2% of base services in '
             '2013 to 75.4% in 2024) - the scheduled interfacility contract '
             'product - while implied loaded miles per transport roughly '
             'halved as the book scaled and densified. SCT and ALS2 stay '
             'under 1.5% of the MEDICARE-VISIBLE book. What this is NOT: '
             'the company\'s book. Medicare FFS is roughly one-sixth of the '
             'market by payer arithmetic, MA and commercial volumes are '
             'invisible here, and dedicated-unit facility contracts '
             '(Facility_Pay_Layer) never generate these claims at all - '
             'which is exactly where high-acuity dedicated work would sit. '
             'Direction of bias: every number on this tab understates.')

    facts += [
        {'metric': 'Subject-company ground base transports billed to '
                   'Medicare FFS (floor)', 'year': 2024,
         'value': round(srv24), 'unit': 'services', 'basis': 'GOV',
         'tier': 'A', 'source_keys': ['mmt_book_mup'],
         'locator': 'MUP by Provider & Service 2024, estate NPIs, base codes',
         'lives_on': 'MMT_Medicare_Book',
         'cross_check': 'Panel E per-NPI rows sum to this; flagship NPI '
                        'A0428 row verified to the cent against the live '
                        'API (Verification_Log)'},
        {'metric': 'Subject-company Medicare FFS allowed dollars, ground '
                   'base codes (floor)', 'year': 2024, 'value': round(alw24),
         'unit': 'USD', 'basis': 'GOV', 'tier': 'A',
         'source_keys': ['mmt_book_mup'],
         'locator': 'Sum of services x average allowed over estate NPI rows',
         'lives_on': 'MMT_Medicare_Book',
         'cross_check': 'Paid share of allowed prints beside it (Panel A)'},
        {'metric': 'Subject-company SCT (A0434) share of base services',
         'year': 2024,
         'value': round(sct24 / srv24, 4) if srv24 else None,
         'unit': 'share', 'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['mmt_book_mup'],
         'locator': 'Panel B live shares; SCT services / base services',
         'lives_on': 'MMT_Medicare_Book',
         'cross_check': 'RUNS BELOW the 6.6% national SCT share (finding 6 '
                        'lineage): the Medicare-visible book is the '
                        'scheduled BLS interfacility product; high-acuity '
                        'dedicated-unit work under facility contracts never '
                        'appears in claims (Facility_Pay_Layer)'},
        {'metric': 'Subject-company mileage units per base transport '
                   '(implied avg loaded miles)', 'year': 2024,
         'value': round(mile24 / srv24, 1) if srv24 else None,
         'unit': 'miles (floor/floor)', 'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['mmt_book_mup'],
         'locator': 'Panel C, A0425 units / base services',
         'lives_on': 'MMT_Medicare_Book',
         'cross_check': 'Interfacility books run long miles; compare '
                        'national A0425-per-base on MUP_Ambulance_National'},
        {'metric': 'Subject-company base-service CAGR 2019 to 2024 '
                   '(Medicare FFS floor)', 'year': 2024,
         'value': round((srv24 / srv19) ** 0.2 - 1, 4) if srv19 else None,
         'unit': 'CAGR', 'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['mmt_book_mup'],
         'locator': 'Panel D live formula over Panel A',
         'lives_on': 'MMT_Medicare_Book',
         'cross_check': 'Read against FFS enrollment decline '
                        '(Utilization_Normalized): per-beneficiary growth '
                        'is stronger than nominal'},
    ]

    findings.append({
        'id_hint': 53,
        'finding': 'The subject company\'s public Medicare floor is measured '
                   'end to end for the first time, and it tells one clean '
                   'story: the estate\'s base transports grew roughly '
                   'seven-fold from 2013 to 2024 while the mix converted '
                   'from a 57% ALS-emergency book to a 75% BLS '
                   'non-emergency book - the scheduled interfacility '
                   'contract product - with implied loaded miles halving '
                   'as the book densified. SCT/ALS2 stay under 1.5% of the '
                   'Medicare-visible book.',
        'numbers': "='MMT_Medicare_Book'!C" + str(a0 + 2),
        'sources': 'mmt_book_mup',
        'confidence': 'High as a floor; suppression makes every level a '
                      'minimum',
        'guardrail': 'Medicare FFS only, roughly one-sixth of the market by '
                     'payer arithmetic; MA, Medicaid, commercial and '
                     'facility-paid volume is invisible here - and '
                     'high-acuity dedicated-unit facility work would never '
                     'generate these claims. Never present this floor as '
                     'the book.'})

    return {'facts': facts, 'sources': sources, 'excluded': excluded,
            'findings': findings, 'meta': {'npis': len(npiset)}}
