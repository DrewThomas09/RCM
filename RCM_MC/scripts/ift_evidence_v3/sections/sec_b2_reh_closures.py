"""B.2: Rural Emergency Hospitals and the closure flow - the two mechanisms
that convert rural inpatient capacity into structural transfer demand.
REHs hold no inpatient beds by statute, so every admission-grade patient at
an REH is a transfer by design; closures remove the destination entirely.
"""

SHEETS = [{'name': 'REH_Closure_Flow',
           'question': 'How do REH conversions and rural closures create '
                       'structural transfer demand?'}]

FOOTPRINT = ['NE', 'IA', 'KS', 'MO', 'OH', 'WI', 'VA', 'MN', 'IN', 'KY']


def build(wb, ctx):
    lib = ctx['lib']
    cache = ctx['cache']
    facts, sources, findings = [], [], []

    reh = lib.load_cache(cache, 'reh_list')
    sheps = lib.load_cache(cache, 'sheps_closures')

    sources += [
        {'key': 'reh_enroll', 'publisher': 'CMS',
         'document': 'Rural Emergency Hospital enrollment roster (public '
                     'enrollment data)',
         'vintage': 'Current enrollments, pulled 11 Jul 2026',
         'locator': 'One row per enrolled REH: name, state, effective date',
         'supplies': 'The REH universe: facilities statutorily without '
                     'inpatient beds, whose admissions are transfers',
         'url': 'https://data.cms.gov (REH enrollment; endpoint on '
                'Pull_Manifest)',
         'tier': 'A', 'accessed': ctx['accessed'],
         'powers': ['REH_Closure_Flow']},
        {'key': 'sheps_closures', 'publisher': 'UNC Sheps Center',
         'document': 'Rural hospital closures and conversions list',
         'vintage': '2010 to present, pulled 11 Jul 2026',
         'locator': 'One row per closure/conversion: name, city, state, '
                    'year, type',
         'supplies': 'The measured destination-removal series behind '
                     'regionalization',
         'url': 'https://www.shepscenter.unc.edu/programs-projects/'
                'rural-health/rural-hospital-closures/',
         'tier': 'A', 'accessed': ctx['accessed'],
         'powers': ['REH_Closure_Flow']},
    ]

    def st(row, *keys):
        for k in keys:
            v = row.get(k)
            if v:
                return str(v).strip()
        return ''

    reh_by_state = {}
    for r in reh:
        s = st(r, 'state', 'STATE', 'State')[:2].upper()
        if s:
            reh_by_state[s] = reh_by_state.get(s, 0) + 1
    cls_by_state = {}
    cls_by_year = {}
    conv = 0
    for r in sheps:
        s = st(r, 'state', 'STATE', 'State')[:2].upper()
        y = st(r, 'year', 'YEAR', 'Year')[:4]
        t = st(r, 'type', 'closure_type', 'status').lower()
        if s:
            cls_by_state[s] = cls_by_state.get(s, 0) + 1
        if y.isdigit():
            cls_by_year[y] = cls_by_year.get(y, 0) + 1
        if 'convert' in t or 'converted' in t:
            conv += 1

    ws = wb.create_sheet('REH_Closure_Flow')
    sb = lib.SheetBuilder(ws, 8, col_widths=[24, 12, 12, 12, 12, 12, 12, 40],
                          tab_color='FF4C7C2C')
    sb.title('Rural Emergency Hospitals and the closure flow: transfer '
             'demand created by statute and by exit')
    sb.subtitle('The question: where has rural inpatient capacity converted '
                'to transfer-by-design (REH) or disappeared outright '
                '(closure), and what does that do to interfacility demand? '
                'CMS REH enrollments plus the Sheps Center closure list, '
                'both pulled live (Pull_Manifest). An REH holds no inpatient '
                'beds by statute (42 USC 1395x(kkk)): every admission-grade '
                'patient arriving at one must be transferred. A closure '
                'removes the destination and lengthens every remaining '
                'corridor.')
    sb.note('DATA QUALITY: REH enrollment is current-state (conversions '
            'accelerate; the roster grows); Sheps closure years are the '
            'operational closure dates and conversions are counted '
            'separately; neither list carries volumes - they change the '
            'GEOMETRY of demand, not a countable volume on this tab.')
    sb.blank()

    sb.banner('Panel A. REH enrollments by state')
    sb.headers(['State', 'REH count', 'Footprint state', '', '', '', '', ''])
    a0 = sb.r + 1
    for s, n in sorted(reh_by_state.items(), key=lambda kv: -kv[1]):
        sb.row([(s, 'src'), (n, 'src', lib.FMT_INT),
                ('YES' if s in FOOTPRINT else '-', 'fml'),
                None, None, None, None, None])
    sb.row([('Total enrolled REHs', 'label'),
            (f'=SUM(B{a0}:B{a0 + len(reh_by_state) - 1})', 'fml',
             lib.FMT_INT), None, None, None, None, None, None])
    sb.blank()

    sb.banner('Panel B. Rural closures and conversions by year (Sheps)')
    sb.headers(['Year', 'Closures + conversions', '', '', '', '', '', ''])
    b0 = sb.r + 1
    for y in sorted(cls_by_year):
        sb.row([(y, 'src'), (cls_by_year[y], 'src', lib.FMT_INT),
                None, None, None, None, None, None])
    sb.blank()
    sb.banner('Panel C. Closures by state (footprint highlighted)')
    sb.headers(['State', 'Closures since 2010', 'Footprint', '', '', '', '',
                ''])
    c0 = sb.r + 1
    for s, n in sorted(cls_by_state.items(), key=lambda kv: -kv[1])[:30]:
        sb.row([(s, 'src'), (n, 'src', lib.FMT_INT),
                ('YES' if s in FOOTPRINT else '-', 'fml'),
                None, None, None, None, None])
    fp_closures = sum(v for k, v in cls_by_state.items() if k in FOOTPRINT)
    fp_reh = sum(v for k, v in reh_by_state.items() if k in FOOTPRINT)
    sb.blank()
    sb.banner('Read panel')
    sb.prose(f'{len(reh)} Rural Emergency Hospitals are enrolled nationally '
             f'({fp_reh} in footprint states), and the Sheps list carries '
             f'{len(sheps)} rural closures and conversions since 2010 '
             f'({fp_closures} in footprint states, {conv} recorded as '
             'conversions). Both mechanisms are structural transfer-demand '
             'creators: the REH by statute (no inpatient beds, so every '
             'admission is a transfer out) and the closure by geometry '
             '(the nearest destination moves one town further). Neither '
             'carries a volume; join to HSA_Corridors and Hub_Spoke_Map '
             'for the demand geometry they reshape.')

    lib.add_chart(ws, 'E6', 'Rural closures and conversions per year',
                  f"'REH_Closure_Flow'!$A${b0}:$A${b0 + len(cls_by_year) - 1}",
                  [('Closures + conversions',
                    f"'REH_Closure_Flow'!$B${b0}:$B${b0 + len(cls_by_year) - 1}")],
                  kind='bar')

    facts += [
        {'metric': 'Rural Emergency Hospitals enrolled (national)',
         'year': 2026, 'value': len(reh), 'unit': 'facilities',
         'basis': 'GOV', 'tier': 'A', 'source_keys': ['reh_enroll'],
         'locator': 'CMS REH enrollment roster (Pull_Manifest)',
         'lives_on': 'REH_Closure_Flow',
         'cross_check': 'Every REH admission-grade patient is a transfer '
                        'by statute'},
        {'metric': 'Rural closures and conversions since 2010, footprint '
                   'states', 'year': 2026, 'value': fp_closures,
         'unit': 'events', 'basis': 'GOV', 'tier': 'A',
         'source_keys': ['sheps_closures'],
         'locator': 'Sheps closure list, state field in footprint set',
         'lives_on': 'REH_Closure_Flow',
         'cross_check': 'The Sheps-vs-Chartis counting convention caveat '
                        'from Methodology section 4 applies'},
    ]
    findings.append({
        'id_hint': 74,
        'finding': 'Transfer demand is being created by statute and by '
                   f'exit: {len(reh)} REHs (no inpatient beds by law) and '
                   f'{len(sheps)} rural closures/conversions since 2010 '
                   'measurably reshape corridor geometry toward longer, '
                   'hub-bound transfers.',
        'numbers': f"='REH_Closure_Flow'!B{a0}",
        'sources': 'reh_enroll; sheps_closures',
        'confidence': 'High on counts; the volume effect is geometric, '
                      'not counted here',
        'guardrail': 'Neither list carries transport volumes; the REH '
                     'mechanism is a design fact, not a measured flow. '
                     'Join to corridor tabs before any quantitative claim.'})

    return {'facts': facts, 'sources': sources, 'excluded': [],
            'findings': findings, 'meta': {'reh': len(reh),
                                           'closures': len(sheps)}}
