"""B.13: USAspending V225 expansion - obligations by state and recipient,
FY2023-2025, plus the registered Beneficiary Travel citation row so the
procurement channel and the claims channel are never summed.
"""

SHEETS = [{'name': 'Federal_Ambulance_Contracts',
           'question': 'Where do federal ambulance procurement dollars go, '
                       'by state and recipient?'}]

FOOTPRINT = ['NE', 'IA', 'KS', 'MO', 'OH', 'WI', 'VA', 'MN', 'IN', 'KY']


def build(wb, ctx):
    lib = ctx['lib']
    cache = ctx['cache']
    facts, sources, findings = [], [], []

    states = lib.load_cache(cache, 'usasp_v225_states_fy25')['results']
    rec = {fy: lib.load_cache(cache, f'usasp_v225_recipients_fy{fy}')['results']
           for fy in ('23', '24', '25')}

    sources += [
        {'key': 'usasp_v225_geo', 'publisher': 'USAspending.gov (Treasury)',
         'document': 'Award search: PSC V225 spending by geography (place of '
                     'performance, state) and by recipient, FY2023-FY2025',
         'vintage': 'Pulled live 11 Jul 2026 (Pull_Manifest hashes)',
         'locator': 'POST /api/v2/search/spending_by_geography/ and '
                    '/spending_by_category/recipient/, psc_codes=[V225]',
         'supplies': 'The state and recipient grain of the federal '
                     'direct-contract ambulance channel',
         'url': 'https://api.usaspending.gov/api/v2/search/'
                'spending_by_geography/',
         'tier': 'A', 'accessed': ctx['accessed'],
         'powers': ['Federal_Ambulance_Contracts']},
        {'key': 'va_bene_travel', 'publisher': 'Department of Veterans '
         'Affairs',
         'document': 'VA Beneficiary Travel program (special-mode ambulance '
                     'travel is reimbursed as CLAIMS under 38 CFR Part 70, '
                     'not as procurement obligations)',
         'vintage': 'Program page, accessed 11 Jul 2026',
         'locator': 'Program description page (citation row; no dollars '
                    'carried from it here)',
         'supplies': 'The registered citation that keeps the two federal '
                     'channels from ever being summed',
         'url': 'https://www.va.gov/resources/reimbursed-va-travel-expenses-'
                'and-mileage-rate/',
         'tier': 'B', 'accessed': ctx['accessed'],
         'powers': ['Federal_Ambulance_Contracts']},
    ]

    ws = wb.create_sheet('Federal_Ambulance_Contracts')
    sb = lib.SheetBuilder(ws, 8,
                          col_widths=[34, 15, 15, 15, 12, 12, 12, 40],
                          tab_color='FFC58F00')
    sb.title('Federal ambulance procurement: PSC V225 by state and '
             'recipient, FY2023-2025')
    sb.subtitle('The question: where does the measured federal direct-'
                'contract ambulance channel land, geographically and by '
                'operator? USAspending award data, PSC V225 (Ambulance '
                'Service), pulled live with hashes on Pull_Manifest. '
                'Headline series and CAGR live on Facility_Pay_Layer '
                'Panel C; this tab is the state and recipient grain.')
    sb.note('DATA QUALITY: procurement OBLIGATIONS by fiscal year, not '
            'outlays, and place of performance can be a headquarters '
            'state; the VA Beneficiary Travel CLAIMS channel (38 CFR Part '
            '70) is a separate, larger flow and is registered on this tab '
            'precisely so the two are never summed. V225 excludes air '
            'charter PSCs.')
    sb.blank()

    sb.banner('Panel A. FY2025 obligations by place-of-performance state')
    sb.headers(['State', 'FY2025 obligations $', 'Share of national',
                'Footprint state', '', '', '', ''])
    a0 = sb.r + 1
    rows = sorted(states, key=lambda r: -(r.get('aggregated_amount') or 0))
    n_states = len(rows)
    for i, r in enumerate(rows):
        code = (r.get('shape_code') or r.get('display_name') or '')[:2]
        rn = a0 + i
        sb.row([(r.get('display_name') or code, 'src'),
                (r.get('aggregated_amount'), 'src', lib.FMT_USD),
                (f'=IF(SUM(B${a0}:B${a0 + n_states - 1})=0,"n/a",'
                 f'B{rn}/SUM(B${a0}:B${a0 + n_states - 1}))', 'fml',
                 lib.FMT_PCT1),
                ('YES' if code.upper() in FOOTPRINT else '-', 'fml'),
                None, None, None, None])
    fp_sum_row = a0 + n_states
    sb.row([('Footprint states subtotal', 'label'),
            (f'=SUMIF(D{a0}:D{a0 + n_states - 1},"YES",'
             f'B{a0}:B{a0 + n_states - 1})', 'fml', lib.FMT_USD),
            (f'=B{fp_sum_row}/SUM(B{a0}:B{a0 + n_states - 1})', 'fml',
             lib.FMT_PCT1), None, None, None, None, None])
    sb.blank()

    sb.banner('Panel B. Top recipients by fiscal year (obligations)')
    sb.headers(['Recipient', 'FY2023 $', 'FY2024 $', 'FY2025 $', '', '', '',
                ''])
    b0 = sb.r + 1
    byname = {}
    for fy, lst in rec.items():
        for r in lst:
            byname.setdefault(r['name'], {})[fy] = r.get('amount')
    top = sorted(byname.items(),
                 key=lambda kv: -(kv[1].get('25') or 0))[:20]
    for name, vals in top:
        sb.row([(name, 'src'),
                (vals.get('23'), 'src', lib.FMT_USD),
                (vals.get('24'), 'src', lib.FMT_USD),
                (vals.get('25'), 'src', lib.FMT_USD),
                None, None, None, None])
    sb.blank()
    sb.banner('Read panel')
    sb.prose('The federal channel is real, growing and fragmented across '
             'regional operators: the FY2025 state distribution above and '
             'the recipient ladder show mid-eight-figure annual books held '
             'by operators that barely register in the Medicare biller '
             'ladders - direct evidence that contract revenue and claims '
             'revenue select for different operators. The IHS and DoD '
             'slices of V225 are inside the all-agency series on '
             'Facility_Pay_Layer; station-level VA award detail is the '
             'E.2 contract corpus\'s job.')

    lib.add_chart(ws, 'F6', 'FY2025 V225 obligations, top-12 states',
                  f"'Federal_Ambulance_Contracts'!$A${a0}:$A${a0 + 11}",
                  [('FY2025 obligations',
                    f"'Federal_Ambulance_Contracts'!$B${a0}:$B${a0 + 11}")],
                  kind='bar', y_fmt='$#,##0,,"M"')

    fp_states_present = sum(
        1 for r in rows
        if (r.get('shape_code') or r.get('display_name') or '')[:2].upper()
        in FOOTPRINT)
    facts += [
        {'metric': 'States with V225 ambulance obligations, FY2025',
         'year': 2025, 'value': n_states, 'unit': 'states', 'basis': 'GOV',
         'tier': 'A', 'source_keys': ['usasp_v225_geo'],
         'locator': 'spending_by_geography, place_of_performance, FY2025',
         'lives_on': 'Federal_Ambulance_Contracts',
         'cross_check': f'{fp_states_present} footprint states present; '
                        'subtotal is a live SUMIF on the tab'},
        {'metric': 'Distinct top-50 V225 recipients appearing in any of '
                   'FY2023-2025', 'year': 2025, 'value': len(byname),
         'unit': 'recipients', 'basis': 'GOV', 'tier': 'A',
         'source_keys': ['usasp_v225_geo'],
         'locator': 'spending_by_category/recipient, three fiscal years',
         'lives_on': 'Federal_Ambulance_Contracts',
         'cross_check': 'Recipient names are as registered in SAM; parent '
                        'roll-ups not applied (stated)'},
    ]
    findings.append({
        'id_hint': 88,
        'finding': 'The federal direct-contract channel selects for a '
                   'different operator set than Medicare claims: the V225 '
                   'recipient ladder is led by regional contract '
                   'specialists, and footprint states hold a measured '
                   'share of a quarter-billion-dollar annual channel.',
        'numbers': f"='Federal_Ambulance_Contracts'!B{fp_sum_row}",
        'sources': 'usasp_v225_geo',
        'confidence': 'High; obligations are recorded transactions',
        'guardrail': 'Obligations, not revenue recognized; place of '
                     'performance can be an HQ state; the Beneficiary '
                     'Travel claims channel is separate and larger and is '
                     'never summed with this.'})

    return {'facts': facts, 'sources': sources, 'excluded': [],
            'findings': findings, 'meta': {'states': n_states}}
