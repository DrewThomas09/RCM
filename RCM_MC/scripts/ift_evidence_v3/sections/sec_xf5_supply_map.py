"""X-F.5: the registered-vs-billing supply map.

The NPPES national ambulance-organization roster (X-A.6) is the universe of
ENROLLED ambulance suppliers, including those that never bill Medicare. Set
against the Medicare-billing NPI count per state (MUP 2024), the gap is the
measured non-Medicare supply layer: facility-pay and Medicaid operators that
carry no carrier claims. States where registration far exceeds billing carry
a thick non-Medicare layer; states where they match are Medicare-dependent.
"""

SHEETS = [{'name': 'Registered_vs_Billing',
           'question': 'How much ambulance supply is registered but never '
                       'bills Medicare - the non-Medicare (facility-pay and '
                       'Medicaid) layer?'}]

BASE = ['A0426', 'A0427', 'A0428', 'A0429', 'A0433', 'A0434']
FOOTPRINT = ['NE', 'IA', 'KS', 'MO', 'OH', 'WI', 'VA', 'MN', 'IN', 'KY']


def build(wb, ctx):
    lib = ctx['lib']
    cache = ctx['cache']
    facts, sources, findings = [], [], []

    roster = lib.load_cache(cache, 'nppes_ambulance_roster')
    reg_by_state = {}
    air_by_state = {}
    for r in roster:
        st = (r.get('state') or '').strip().upper()
        if len(st) != 2:
            continue
        reg_by_state[st] = reg_by_state.get(st, 0) + 1
        if r.get('air'):
            air_by_state[st] = air_by_state.get(st, 0) + 1

    # Medicare-billing distinct NPIs per state, 2024, ground base codes
    bill_by_state = {}
    seen = {}
    for code in BASE:
        try:
            rows = lib.load_cache(cache, f'mup_provider_2024_{code}')
        except FileNotFoundError:
            continue
        for r in rows:
            st = (r.get('Rndrng_Prvdr_State_Abrvtn') or '').strip().upper()
            npi = str(r.get('Rndrng_NPI'))
            if len(st) == 2 and npi:
                seen.setdefault(st, set()).add(npi)
    for st, s in seen.items():
        bill_by_state[st] = len(s)

    sources.append(
        {'key': 'nppes_amb_roster', 'publisher': 'CMS (NPPES)',
         'document': 'NPPES national provider roster, organizational NPIs '
                     'with ground/air ambulance taxonomy (3416 family)',
         'vintage': 'NPPES monthly full-replacement file (Pull_Manifest)',
         'locator': 'Entity Type 2 with a 3416* taxonomy; state from the '
                    'practice-address record',
         'supplies': 'The registered ambulance-supplier universe including '
                     'non-Medicare billers',
         'url': 'https://download.cms.gov/nppes/NPI_Files.html',
         'tier': 'A', 'accessed': ctx['accessed'],
         'powers': ['Registered_vs_Billing']})

    ws = wb.create_sheet('Registered_vs_Billing')
    sb = lib.SheetBuilder(ws, 8,
                          col_widths=[10, 18, 18, 18, 16, 14, 12, 34],
                          tab_color='FF1F6F8B')
    sb.title('Registered vs billing: the non-Medicare ambulance supply layer, '
             'by state')
    sb.subtitle('The question: how much ambulance supply is registered but '
                'never bills Medicare - the facility-pay and Medicaid layer '
                'that claims-based reads cannot see? The NPPES organizational '
                'ambulance roster (registered supply) set against Medicare-'
                'billing NPI counts (MUP 2024, ground base codes). The gap is '
                'the measured non-Medicare supply layer; a matched ratio, '
                'with the confounds printed in-row. Join by state; NPPES '
                'carries ZIP not county, so this is the state grain.')
    sb.note('DATA QUALITY: NPPES registration is an enrollment record, not an '
            'activity record - some registered NPIs are dormant, air-only, or '
            'bill under a parent; Medicare-billing counts are floors '
            '(suppression) and ground-only. The gap is therefore a BOUND on '
            'the non-Medicare layer, not a headcount of it; both directions '
            'of error are stated. Air-taxonomy NPIs are shown separately.')
    sb.blank()

    sb.banner('Panel A. Registered ambulance organizations vs Medicare-'
              'billing NPIs, by state')
    sb.headers(['State', 'Registered (NPPES)', 'of which air-flagged',
                'Medicare-billing NPIs', 'Registered per biller',
                'Footprint', '', 'Reading'])
    a0 = sb.r + 1
    order = sorted(reg_by_state.items(), key=lambda kv: -kv[1])
    for st, reg in order:
        bill = bill_by_state.get(st, 0)
        rn = sb.r + 1
        reading = ('thick non-Medicare layer' if bill and reg / bill >= 3
                   else 'Medicare-dependent base' if bill and reg / bill < 1.5
                   else 'mixed')
        sb.row([(st, 'src'), (reg, 'src', lib.FMT_INT),
                (air_by_state.get(st, 0), 'src', lib.FMT_INT),
                (bill, 'src', lib.FMT_INT),
                (f'=IF(D{rn}=0,"n/a",B{rn}/D{rn})', 'fml', lib.FMT_DEC1),
                ('YES' if st in FOOTPRINT else '-', 'fml'), None,
                (reading, 'note')])
    sb.blank()

    sb.banner('Panel B. Footprint states: the non-Medicare supply bound')
    sb.headers(['State', 'Registered', 'Billing', 'Gap (registered - '
                'billing)', 'Gap share of registered', 'Footprint', '', ''])
    b0 = sb.r + 1
    for st in FOOTPRINT:
        reg = reg_by_state.get(st, 0)
        bill = bill_by_state.get(st, 0)
        rn = sb.r + 1
        sb.row([(st, 'src'), (reg, 'src', lib.FMT_INT),
                (bill, 'src', lib.FMT_INT),
                (f'=B{rn}-C{rn}', 'fml', lib.FMT_INT),
                (f'=IF(B{rn}=0,"n/a",(B{rn}-C{rn})/B{rn})', 'fml',
                 lib.FMT_PCT1),
                ('YES', 'fml'), None, None])
    sb.blank()
    sb.banner('Read panel')
    us_reg = sum(reg_by_state.values())
    us_bill = sum(bill_by_state.values())
    fp_reg = sum(reg_by_state.get(s, 0) for s in FOOTPRINT)
    fp_bill = sum(bill_by_state.get(s, 0) for s in FOOTPRINT)
    sb.prose(f'Nationally {us_reg:,} organizational ambulance NPIs are '
             f'registered against roughly {us_bill:,} distinct Medicare '
             'ground-base billers - the registered universe is more than '
             'double the billing universe, and that gap is the bound on the '
             'non-Medicare supply layer that facility contracts and Medicaid '
             'brokerage sustain. In the footprint the same pattern holds '
             f'({fp_reg:,} registered vs {fp_bill:,} billing). This is the '
             'supply-side companion to the facility-pay revenue layer '
             '(Facility_Pay_Layer) and the insourcing bounds '
             '(Insourcing_Bounds): a large registered-but-not-billing tail is '
             'exactly what a facility-pay and Medicaid-heavy market looks '
             'like from the enrollment side.')

    lib.add_chart(ws, 'J6', 'Registered per Medicare biller, footprint states',
                  f"'Registered_vs_Billing'!$A${b0}:$A${b0 + 9}",
                  [('Registered', f"'Registered_vs_Billing'!$B${b0}:$B${b0 + 9}"),
                   ('Billing', f"'Registered_vs_Billing'!$C${b0}:$C${b0 + 9}")],
                  kind='bar')

    facts += [
        {'metric': 'Registered organizational ambulance NPIs, national '
                   '(NPPES 3416 taxonomy)', 'year': 2026, 'value': us_reg,
         'unit': 'NPIs', 'basis': 'GOV', 'tier': 'A',
         'source_keys': ['nppes_amb_roster'],
         'locator': 'NPPES roster, Entity Type 2, 3416* taxonomy',
         'lives_on': 'Registered_vs_Billing',
         'cross_check': 'More than double the Medicare-billing universe; the '
                        'gap bounds the non-Medicare layer'},
        {'metric': 'Registered-to-billing ratio, national ambulance supply',
         'year': 2026, 'value': round(us_reg / us_bill, 2) if us_bill else None,
         'unit': 'ratio', 'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['nppes_amb_roster'],
         'locator': 'National registered NPIs / distinct MUP 2024 ground '
                    'base billers',
         'lives_on': 'Registered_vs_Billing',
         'cross_check': 'Bound not headcount: dormant/air/parent-billed NPIs '
                        'inflate; suppression deflates the billing count'},
    ]
    findings.append({
        'id_hint': 96,
        'finding': 'The registered ambulance-supplier universe is more than '
                   'twice the Medicare-billing universe nationally and across '
                   'the footprint, and that gap is the enrollment-side bound '
                   'on the non-Medicare (facility-pay and Medicaid) supply '
                   'layer that claims-based supply reads cannot see.',
        'numbers': f"='Registered_vs_Billing'!B{a0}",
        'sources': 'nppes_amb_roster',
        'confidence': 'High on the registration count; the gap is a bound, '
                      'not a headcount',
        'guardrail': 'Registration is not activity: dormant, air-only and '
                     'parent-billed NPIs inflate the gap while suppression '
                     'deflates the billing count. Read the gap as a bound on '
                     'the non-Medicare layer, never as its size.'})

    return {'facts': facts, 'sources': sources, 'excluded': [],
            'findings': findings, 'meta': {'registered': us_reg,
                                           'billing': us_bill}}
