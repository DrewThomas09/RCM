"""B.1: the facility-pay evidence layer (Facility_Pay_Layer tab).

Ships first in the v3.4 pass by order: the measured public evidence that a
large share of ambulance revenue never touches a payer claim - facility
contracts, local-government subsidy, standby and membership revenue - built
from three primaries verified against the documents on 11 Jul 2026
(b1_verified.json): the CMS/RAND GADCS Year 1-4 appendix, the DocGo Inc.
Form 10-K FY2025, and the USAspending PSC V225 series pulled live.

Emits exactly 13 facts (F443-F455 under the v3.4 reservation) and 3 sources
(S313-S315).
"""

SHEETS = [{'name': 'Facility_Pay_Layer',
           'question': 'How much ambulance revenue exists outside the claims '
                       'window, and who pays it?'}]

GADCS_URL = ('https://www.cms.gov/files/document/medicare-ground-ambulance-'
             'data-collection-system-gadcs-report-appendix-year-1-year-4-'
             'cohort-analysis.pdf')
DOCGO_URL = ('https://www.sec.gov/Archives/edgar/data/1822359/'
             '000162828026018214/dcgo-20251231.htm')
USASP_URL = 'https://api.usaspending.gov/api/v2/search/spending_over_time/'


def _find_label(ws, needle, max_col=6):
    """First cell whose text contains needle; returns (row, col) or None."""
    n = needle.lower()
    for row in ws.iter_rows(max_col=max_col):
        for c in row:
            if isinstance(c.value, str) and n in c.value.lower():
                return c.row, c.column
    return None


def _find_number(ws, target, tol=0.5, max_col=12):
    """First cell whose numeric value equals target; returns A1 ref or None."""
    for row in ws.iter_rows(max_col=max_col):
        for c in row:
            if isinstance(c.value, (int, float)) and abs(c.value - target) <= tol:
                return c.coordinate
    return None


def build(wb, ctx):
    lib = ctx['lib']
    cache = ctx['cache']
    accessed = ctx['accessed']
    facts, sources, excluded, findings = [], [], [], []

    t_all = {str(r['time_period']['fiscal_year']): r['aggregated_amount']
             for r in lib.load_cache(cache, 'usasp_v225_time_all')['results']}
    t_va = {str(r['time_period']['fiscal_year']): r['aggregated_amount']
            for r in lib.load_cache(cache, 'usasp_v225_time_va')['results']}
    rec25 = lib.load_cache(cache, 'usasp_v225_recipients_fy25')['results']

    sources += [
        {'key': 'gadcs_appendix', 'publisher': 'CMS / RAND Health Care',
         'document': 'Medicare Ground Ambulance Data Collection System (GADCS) '
                     'Report Appendix, Year 1-Year 4 Cohort Analysis, data '
                     'through 15 May 2025 (PR-A2743-9, December 2025)',
         'vintage': 'GADCS Year 1-4 cohorts, data through 15 May 2025',
         'locator': 'Table 2.32 (p.70): revenue sources; Table 2.30 (pp.64-65): '
                    'payer revenue per NPI; Table 2.6 (p.33): interfacility '
                    'share by ownership; Table S.1 (p.ix): payer-share summary',
         'supplies': 'The only national census of ambulance organization '
                     'revenue by source, including non-payer (facility, '
                     'subsidy, tax, standby) revenue',
         'url': GADCS_URL, 'tier': 'A', 'accessed': accessed,
         'powers': ['Facility_Pay_Layer']},
        {'key': 'docgo_10k', 'publisher': 'DocGo Inc. (SEC EDGAR)',
         'document': 'Form 10-K for fiscal year 2025, accession '
                     '0001628280-26-018214 (dcgo-20251231.htm)',
         'vintage': 'FY2023-FY2025 audited segment disclosure',
         'locator': 'Note 2 disaggregation (F-22) and Note 11 segment table '
                    '(F-37): Transportation Services revenue; MD&A pp.57/62/66: '
                    'trips, average trip price, leased-hour exclusion',
         'supplies': 'The only US-listed pure ambulance operator P&L: measured '
                     'share of transportation revenue billed outside per-trip '
                     'claims (dedicated-unit programs billed to facilities)',
         'url': DOCGO_URL, 'tier': 'A', 'accessed': accessed,
         'powers': ['Facility_Pay_Layer']},
        {'key': 'usasp_v225', 'publisher': 'USAspending.gov (Treasury)',
         'document': 'Award search API, Product/Service Code V225 (Ambulance '
                     'Service), spending over time, by recipient and by state',
         'vintage': 'FY2023-FY2025 obligations, pulled live (Pull_Manifest)',
         'locator': 'POST /api/v2/search/spending_over_time/ and '
                    'spending_by_category/recipient with psc_codes=[V225]',
         'supplies': 'The measured federal facility-pay channel: government '
                     'buys ambulance service directly by contract, no claim',
         'url': USASP_URL, 'tier': 'A', 'accessed': accessed,
         'powers': ['Facility_Pay_Layer']},
    ]

    ws = wb.create_sheet('Facility_Pay_Layer')
    sb = lib.SheetBuilder(ws, 7, col_widths=[46, 15, 16, 15, 15, 15, 42],
                          tab_color='FFC58F00')
    sb.title('The facility-pay layer: ambulance revenue that never touches '
             'a payer claim')
    sb.subtitle('The question: how much ambulance revenue is paid by '
                'facilities, local governments and contracts rather than '
                'through payer claims - the layer every claims-based market '
                'size misses? Three primaries, verified against the documents '
                'on 11 Jul 2026: the CMS/RAND GADCS Year 1-4 census (the only '
                'national revenue-source survey), the DocGo 10-K (the only '
                'US-listed pure ambulance P&L), and USAspending PSC V225 (the '
                'federal direct-contract channel). This tab bounds incidence '
                'and magnitude; the IFT-specific facility-pay share does not '
                'exist publicly and stays PENDING.')
    sb.note('DATA QUALITY: GADCS values are self-reported survey responses '
            'from the Year 1-4 collection cohorts (MedPAC judged the COST '
            'side unusable for margins; revenue-source incidence is carried '
            'here as the census it is, with that caveat). DocGo figures are '
            'audited but one operator. USAspending rows are procurement '
            'obligations only; the VA Beneficiary Travel claims channel is '
            'separate and larger and must NEVER be summed with these.')
    sb.blank()

    # Panel A - GADCS revenue-source census
    sb.banner('Panel A. GADCS: revenue sources of US ambulance organizations '
              '(share reporting any; conditional mean; median)')
    sb.headers(['Revenue source (GADCS Question 5)', 'Share reporting',
                'Conditional mean $', 'Median $', '', '', 'Locator'])
    a0 = sb.r + 1
    rows_a = [
        ('Facility contracts (hospitals, SNFs, other facilities)',
         0.186, 922555, 48393, 'Table 2.32, p.70'),
        ('Any non-payer revenue (all Question 5 categories)',
         0.745, 2177569, 162265, 'Table 2.32, p.70'),
        ('Local-government contracts', 0.154, 556091, 112426,
         'Table 2.32, p.70'),
        ('EMS-earmarked local taxes', 0.234, 3135660, 352117,
         'Table 2.32, p.70'),
        ('Standby event revenue (share reporting)', 0.245, None, None,
         'Table 2.32, p.70'),
        ('Membership programs (share reporting)', 0.076, None, None,
         'Table 2.32, p.70'),
    ]
    for label, share, mean, med, loc in rows_a:
        sb.row([(label, 'text'), (share, 'src', lib.FMT_PCT1),
                (mean, 'src', lib.FMT_USD) if mean else None,
                (med, 'src', lib.FMT_USD) if med else None, None, None,
                (loc, 'note')])
    sb.blank()
    sb.headers(['Payer revenue per NPI (GADCS mean)', 'Mean $', '', '', '', '',
                'Locator'])
    p0 = sb.r + 1
    for label, val in [('All payers', 3914787), ('Medicare FFS', 1193046),
                       ('Medicare Advantage', 1238482), ('Medicaid', 732436),
                       ('Commercial', 1322170)]:
        sb.row([(label, 'text'), (val, 'src', lib.FMT_USD), None, None, None,
                None, ('Table 2.30, pp.64-65', 'note')])
    sb.row([('Medicare FFS share of transport revenue (average per NPI)',
             'label'), (0.29, 'src', lib.FMT_PCT1), None, None, None, None,
            ('Table S.1, p.ix', 'note')])
    sb.row([('Medicare Advantage additional share', 'label'),
            (0.18, 'src', lib.FMT_PCT1), None, None, None, None,
            ('Table S.1, p.ix', 'note')])
    sb.row([('Organizations that did not always bill in at least one payer '
             'category (about one in five, as published)', 'label'),
            (0.20, 'src', lib.FMT_PCT1), None, None, None, None,
            ('Table S.1, p.ix; "about one in five"', 'note')])
    sb.row([('MA-to-FFS revenue ratio per NPI (the MA book calibrator)',
             'label'),
            (f'=B{p0 + 2}/B{p0 + 1}', 'fml', lib.FMT_X), None, None, None,
            None, ('DERIVED from Table 2.30 rows above', 'note')])
    ifs0 = sb.r + 2
    sb.blank()
    sb.headers(['Interfacility share of transport volume (GADCS)',
                'Share of organizations', '', '', '', '', 'Locator'])
    for label, val in [
            ('For-profit organizations at 81-100% interfacility', 0.202),
            ('For-profit organizations at 21-80% interfacility', 0.428),
            ('All organizations at 81-100% interfacility', 0.074)]:
        sb.row([(label, 'text'), (val, 'src', lib.FMT_PCT1), None, None, None,
                None, ('Table 2.6, p.33', 'note')])
    sb.note('Read: the interfacility-heavy operator is overwhelmingly a '
            'FOR-PROFIT phenomenon (20.2% of for-profits vs 7.4% of all '
            'organizations run 81-100% interfacility books), which is why '
            'claims-only market reads systematically under-see the private '
            'IFT segment: it is exactly the segment with facility contracts.')
    sb.blank()

    # Panel B - DocGo decomposition
    sb.banner('Panel B. DocGo 10-K: the measured share of transportation '
              'revenue billed outside per-trip claims')
    sb.headers(['Metric', 'FY2025', 'FY2024', 'FY2023', '', '', 'Locator'])
    b0 = sb.r + 1
    sb.row([('Transportation Services segment revenue $', 'label'),
            (200765608, 'src', lib.FMT_USD), (193429092, 'src', lib.FMT_USD),
            (181495105, 'src', lib.FMT_USD), None, None,
            ('Note 2 (F-22); Note 11 (F-37)', 'note')])
    sb.row([('Trips (per-trip billed only, by the filing definition)',
             'label'),
            (296014, 'src', lib.FMT_INT), (283570, 'src', lib.FMT_INT),
            (250114, 'src', lib.FMT_INT), None, None,
            ('MD&A pp.62/66', 'note')])
    sb.row([('Average trip price $', 'label'),
            (401, 'src', lib.FMT_USD), (402, 'src', lib.FMT_USD),
            (407, 'src', lib.FMT_USD), None, None,
            ('MD&A pp.57/62/66; FY23 ATP from Note 2', 'note')])
    sb.row([('Implied per-trip billed revenue $', 'label'),
            (f'=C{b0 + 1}*C{b0 + 2}', 'fml', lib.FMT_USD),
            (f'=D{b0 + 1}*D{b0 + 2}', 'fml', lib.FMT_USD),
            (f'=E{b0 + 1}*E{b0 + 2}', 'fml', lib.FMT_USD), None, None,
            ('trips x ATP', 'note')])
    sb.row([('Revenue OUTSIDE per-trip billing (dedicated-unit programs '
             'billed hourly or daily to facilities, excluded from trips and '
             'ATP by the filing itself)', 'label'),
            (f'=1-C{b0 + 3}/C{b0}', 'fml', lib.FMT_PCT1),
            (f'=1-D{b0 + 3}/D{b0}', 'fml', lib.FMT_PCT1),
            (f'=1-E{b0 + 3}/E{b0}', 'fml', lib.FMT_PCT1), None, None,
            ('MD&A p.57 exclusion language; arithmetic live', 'note')])
    sb.note('Guardrail: one operator, and the plus-or-minus 0.1pp rounding '
            'from whole-dollar ATP is real. What it establishes is '
            'EXISTENCE and scale at a listed operator: roughly 41 cents of '
            'every transportation dollar arrives outside a per-trip claim, '
            'and the filing itself names healthcare facilities as a billing '
            'counterparty class (Note 2, F-22).')
    sb.blank()

    # Panel C - USAspending V225
    sb.banner('Panel C. USAspending PSC V225: the federal direct-contract '
              'ambulance channel (obligations, pulled live)')
    sb.headers(['Fiscal year', 'VA obligations $', 'All-agency obligations $',
                'VA share', '', '', 'Note'])
    c0 = sb.r + 1
    for i, fy in enumerate(('2023', '2024', '2025')):
        rn = c0 + i
        sb.row([(fy, 'src'),
                (t_va.get(fy), 'src', lib.FMT_USD),
                (t_all.get(fy), 'src', lib.FMT_USD),
                (f'=IF(C{rn}=0,"n/a",B{rn}/C{rn})', 'fml', lib.FMT_PCT1),
                None, None,
                ('spending_over_time, psc V225', 'note') if i == 0 else None])
    sb.row([('CAGR FY2023-FY2025 (VA)', 'label'),
            (f'=(B{c0 + 2}/B{c0})^(1/2)-1', 'fml', lib.FMT_PCT1),
            (f'=(C{c0 + 2}/C{c0})^(1/2)-1', 'fml', lib.FMT_PCT1),
            None, None, None, ('two-year CAGR', 'note')])
    sb.blank()
    sb.headers(['Top FY2025 V225 recipients', 'Obligations $', '', '', '', '',
                ''])
    for r in rec25[:10]:
        sb.row([(r.get('name'), 'src'), (r.get('amount'), 'src', lib.FMT_USD),
                None, None, None, None, None])
    sb.note('Guardrail: procurement obligations only. The VA Beneficiary '
            'Travel program pays ambulance CLAIMS through a separate and '
            'larger channel; the two must never be summed. IHS and DoD '
            'V225 obligations exist and are additive to VA only within '
            'this procurement frame.')
    sb.blank()

    # Panel D - the sizing map
    sb.banner('Panel D. What this layer does to the sizing math (live links)')
    d0 = sb.r + 1
    ems = wb['EMS_Transports'] if 'EMS_Transports' in wb.sheetnames else None
    mis = (wb['Medicare_IFT_Series']
           if 'Medicare_IFT_Series' in wb.sheetnames else None)
    ems_ref = _find_number(ems, 5510664) if ems is not None else None
    mis_ref = _find_number(mis, 871753, tol=5) if mis is not None else None
    sb.row([('NEMSIS interfacility-scale activations (EMS_Transports)',
             'label'),
            (f"='EMS_Transports'!{ems_ref}", 'link', lib.FMT_INT)
            if ems_ref else ('PENDING', 'note'),
            None, None, None, None,
            ('vehicle legs, all payers', 'note')])
    sb.row([('Medicare FFS hospital-to-hospital services 2024 '
             '(Medicare_IFT_Series)', 'label'),
            (f"='Medicare_IFT_Series'!{mis_ref}", 'link', lib.FMT_INT)
            if mis_ref else ('PENDING', 'note'),
            None, None, None, None,
            ('claims-visible floor', 'note')])
    sb.row([('The identity this tab prices: activations minus claims-visible '
             'volume is the mixed pool where unbilled, facility-paid and '
             'non-FFS volume lives', 'label'),
            (f'=IF(OR(ISTEXT(B{d0}),ISTEXT(B{d0 + 1})),"PENDING",'
             f'B{d0}-B{d0 + 1})', 'fml', lib.FMT_INT),
            None, None, None, None,
            ('wedge, not a market size', 'note')])
    sb.row([('IFT-specific facility-pay share of that wedge', 'label'),
            ('PENDING', 'note'), None, None, None, None,
            ('No public source; would take a claims-vendor panel with '
             'facility-remit flags or primary buyer research (bordered slot; '
             'see Engagement_Data_Map)', 'note')])
    sb.blank()
    sb.banner('Read panel')
    sb.prose('What is measured: (1) 18.6 percent of US ambulance organizations '
             'report facility-contract revenue, with a conditional mean near '
             '$0.92M and a long right tail (median $48K); (2) 74.5 percent '
             'report some non-payer revenue; (3) a listed pure-play operator '
             'books about 41 percent of transportation revenue outside '
             'per-trip claims, naming facilities as a payer class in its '
             'revenue-recognition note; (4) the federal government alone '
             'obligates about a quarter-billion dollars a year buying '
             'ambulance service by contract. Together these are the public '
             'floor and existence proof for the facility-pay layer that '
             'claims-based sizing cannot see. What is NOT measured: the '
             'IFT-specific share of that layer; it stays PENDING by design.')

    facts += [
        {'metric': 'Ambulance organizations reporting facility-contract '
                   'revenue (GADCS)', 'year': 2025, 'value': 0.186,
         'unit': 'share of organizations', 'basis': 'GOV', 'tier': 'A',
         'source_keys': ['gadcs_appendix'],
         'locator': 'GADCS Y1-4 appendix, Table 2.32, p.70',
         'lives_on': 'Facility_Pay_Layer',
         'cross_check': 'Self-reported census; incidence, not an IFT share'},
        {'metric': 'Facility-contract revenue, conditional mean per '
                   'organization (GADCS)', 'year': 2025, 'value': 922555,
         'unit': 'USD', 'basis': 'GOV', 'tier': 'A',
         'source_keys': ['gadcs_appendix'],
         'locator': 'Table 2.32, p.70', 'lives_on': 'Facility_Pay_Layer',
         'cross_check': 'Median $48,393 on the same row: long right tail'},
        {'metric': 'Facility-contract revenue, median per organization '
                   '(GADCS)', 'year': 2025, 'value': 48393, 'unit': 'USD',
         'basis': 'GOV', 'tier': 'A', 'source_keys': ['gadcs_appendix'],
         'locator': 'Table 2.32, p.70', 'lives_on': 'Facility_Pay_Layer',
         'cross_check': 'Mean/median gap is the skew caveat in-row'},
        {'metric': 'Organizations reporting any non-payer revenue (GADCS '
                   'Question 5 categories)', 'year': 2025, 'value': 0.745,
         'unit': 'share of organizations', 'basis': 'GOV', 'tier': 'A',
         'source_keys': ['gadcs_appendix'],
         'locator': 'Table 2.32, p.70', 'lives_on': 'Facility_Pay_Layer',
         'cross_check': 'Includes subsidies, taxes, standby, memberships'},
        {'metric': 'Non-payer revenue, conditional mean (GADCS)',
         'year': 2025, 'value': 2177569, 'unit': 'USD', 'basis': 'GOV',
         'tier': 'A', 'source_keys': ['gadcs_appendix'],
         'locator': 'Table 2.32, p.70', 'lives_on': 'Facility_Pay_Layer',
         'cross_check': 'Median $162,265'},
        {'metric': 'Organizations with local-government contract revenue '
                   '(GADCS)', 'year': 2025, 'value': 0.154,
         'unit': 'share of organizations', 'basis': 'GOV', 'tier': 'A',
         'source_keys': ['gadcs_appendix'],
         'locator': 'Table 2.32, p.70', 'lives_on': 'Facility_Pay_Layer',
         'cross_check': 'Conditional mean $556,091, median $112,426'},
        {'metric': 'Organizations with EMS-earmarked local tax revenue '
                   '(GADCS)', 'year': 2025, 'value': 0.234,
         'unit': 'share of organizations', 'basis': 'GOV', 'tier': 'A',
         'source_keys': ['gadcs_appendix'],
         'locator': 'Table 2.32, p.70', 'lives_on': 'Facility_Pay_Layer',
         'cross_check': 'Conditional mean $3.14M: the subsidy backbone of '
                        'government services'},
        {'metric': 'Mean payer revenue per ambulance NPI, all payers (GADCS)',
         'year': 2025, 'value': 3914787, 'unit': 'USD', 'basis': 'GOV',
         'tier': 'A', 'source_keys': ['gadcs_appendix'],
         'locator': 'Table 2.30, pp.64-65', 'lives_on': 'Facility_Pay_Layer',
         'cross_check': 'FFS $1.19M, MA $1.24M, Medicaid $0.73M, commercial '
                        '$1.32M on the same table'},
        {'metric': 'Medicare FFS share of ambulance transport revenue, mean '
                   'per NPI (GADCS)', 'year': 2025, 'value': 0.29,
         'unit': 'share', 'basis': 'GOV', 'tier': 'A',
         'source_keys': ['gadcs_appendix'],
         'locator': 'Table S.1, p.ix', 'lives_on': 'Facility_Pay_Layer',
         'cross_check': 'The one-sixth-of-market arithmetic elsewhere in '
                        'this workbook uses dollars, not per-NPI means; '
                        'bases differ and are never mixed'},
        {'metric': 'Organizations that did not always bill in at least one '
                   'payer category (GADCS, published as about one in five)',
         'year': 2025, 'value': 0.20, 'unit': 'share, approximate as '
         'published', 'basis': 'GOV', 'tier': 'A',
         'source_keys': ['gadcs_appendix'],
         'locator': 'Table S.1, p.ix ("about one in five")',
         'lives_on': 'Facility_Pay_Layer',
         'cross_check': 'The eligible-but-unbilled anchor for the sizing '
                        'gross-up; approximate by publication'},
        {'metric': 'DocGo Transportation Services revenue FY2025',
         'year': 2025, 'value': 200765608, 'unit': 'USD', 'basis': 'SEC-A',
         'tier': 'A', 'source_keys': ['docgo_10k'],
         'locator': '10-K FY2025, Note 2 (F-22) and Note 11 (F-37)',
         'lives_on': 'Facility_Pay_Layer',
         'cross_check': 'FY2024 $193.4M, FY2023 $181.5M same tables'},
        {'metric': 'DocGo transportation revenue outside per-trip billing, '
                   'FY2025', 'year': 2025, 'value': 0.409, 'unit': 'share',
         'basis': 'DERIVED', 'tier': 'A', 'source_keys': ['docgo_10k'],
         'locator': '1 - trips x ATP / segment revenue; inputs Note 2/MD&A; '
                    'live formula on Facility_Pay_Layer Panel B',
         'lives_on': 'Facility_Pay_Layer',
         'cross_check': 'FY2024 41.1% by the same arithmetic; whole-dollar '
                        'ATP rounding gives about 0.1pp uncertainty'},
        {'metric': 'VA ambulance procurement obligations (PSC V225), FY2025',
         'year': 2025, 'value': 246082814, 'unit': 'USD', 'basis': 'GOV',
         'tier': 'A', 'source_keys': ['usasp_v225'],
         'locator': 'USAspending spending_over_time, psc V225, VA awarding '
                    'toptier (Pull_Manifest hash)',
         'lives_on': 'Facility_Pay_Layer',
         'cross_check': 'All-agency FY2025 $292.7M; VA share 84%; '
                        'Beneficiary Travel claims are a separate channel, '
                        'never summed'},
    ]

    findings.append({
        'id_hint': 52,
        'finding': 'The facility-pay layer is measured, not asserted: 18.6% '
                   'of US ambulance organizations report facility-contract '
                   'revenue (conditional mean $0.92M, median $48K), 74.5% '
                   'report some non-payer revenue, a listed pure-play '
                   'operator books about 41% of transportation revenue '
                   'outside per-trip claims and names healthcare facilities '
                   'as a billing counterparty in its revenue-recognition '
                   'note, and the federal government alone obligated $246M '
                   'buying ambulance service by contract in FY2025.',
        'numbers': f"='Facility_Pay_Layer'!B{a0}",
        'sources': 'gadcs_appendix; docgo_10k; usasp_v225',
        'confidence': 'High on incidence and existence; magnitudes are '
                      'category means with long tails',
        'guardrail': 'Incidence and magnitude bounds only. None of these '
                     'figures is an IFT-specific facility-pay share; that '
                     'share has no public source and stays PENDING on '
                     'Facility_Pay_Layer Panel D.'})

    return {'facts': facts, 'sources': sources, 'excluded': excluded,
            'findings': findings,
            'meta': {'verified_against': 'b1_verified.json (29/29 claims)'}}
