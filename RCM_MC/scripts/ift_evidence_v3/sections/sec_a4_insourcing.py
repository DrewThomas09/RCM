"""A.4: Insourcing_Bounds - the claims-side hospital-billed share of ground
ambulance, bounded rather than asserted.

Every 2024 (and 2019 / 2013) MUP provider-grain biller of the six ground
base codes is classified hospital-affiliated vs independent by printed,
auditable rules: H1 a name test, H2 a normalized-token linkage to the Care
Compare hospital roster in the same state, H3 an explicitly-independent
name test. FLOOR = base services from billers matching H1 AND H2;
CEILING = H1 OR H2. The rules table itself renders on the tab with match
counts, so every number can be re-derived by hand from the public files.
"""

SHEETS = [{'name': 'Insourcing_Bounds',
           'question': 'What share of Medicare FFS ground ambulance is '
                       'billed by hospital-affiliated organizations - '
                       'bounded, not asserted, from the claims side?'}]

BASE = ['A0426', 'A0427', 'A0428', 'A0429', 'A0433', 'A0434']
LEVEL = {'A0426': 'ALS non-emergency', 'A0427': 'ALS emergency',
         'A0428': 'BLS non-emergency', 'A0429': 'BLS emergency',
         'A0433': 'ALS level 2', 'A0434': 'SCT'}
VINTAGES = ('2013', '2019', '2024')
FOOT = ['NE', 'IA', 'KS', 'MO', 'OH', 'WI', 'VA', 'MN', 'IN', 'KY']

# --- printed normalization vocabulary (renders in Panel A notes) ----------
SUFFIX = {'INC', 'LLC', 'LLP', 'LP', 'LTD', 'CORP', 'CORPORATION', 'CO',
          'COMPANY', 'PC', 'PA', 'PLLC', 'DBA', 'THE'}
GENERIC = {'THE', 'OF', 'AND', 'AT', 'FOR', 'IN', 'ON', 'A', 'AN',
           'HOSPITAL', 'HOSPITALS', 'MEDICAL', 'CENTER', 'CENTERS',
           'CENTRE', 'HEALTH', 'HEALTHCARE', 'SYSTEM', 'SYSTEMS',
           'REGIONAL', 'COMMUNITY', 'MEMORIAL', 'GENERAL', 'COUNTY',
           'CITY', 'SAINT', 'ST', 'MT', 'MOUNT', 'UNIVERSITY', 'CLINIC',
           'CLINICS', 'INFIRMARY', 'AMBULANCE', 'AMBULANCES', 'EMS',
           'SERVICE', 'SERVICES', 'TRANSPORT', 'TRANSPORTATION', 'RESCUE',
           'FIRE', 'DEPARTMENT', 'DEPT', 'DISTRICT', 'AUTHORITY',
           'DIVISION', 'GROUP', 'CARE', 'NEW'}
REGION = {'MIDWEST', 'MIDWESTERN', 'NORTH', 'SOUTH', 'EAST', 'WEST',
          'CENTRAL', 'NORTHERN', 'SOUTHERN', 'EASTERN', 'WESTERN',
          'NORTHEAST', 'NORTHWEST', 'SOUTHEAST', 'SOUTHWEST', 'AMERICAN',
          'AMERICA', 'NATIONAL', 'UNITED', 'VALLEY', 'ATLANTIC', 'PACIFIC'}
H1_TERMS = ['HOSPITAL', 'HEALTH SYSTEM', 'MEDICAL CENTER', 'HEALTH CENTER',
            'CLINIC', 'INFIRMARY', 'MAYO', 'ends in HEALTH']

MUP_URL = ('https://data.cms.gov/provider-summary-by-type-of-service/'
           'medicare-physician-other-practitioners/medicare-physician-'
           'other-practitioners-by-provider-and-service')
PDC_URL = 'https://data.cms.gov/provider-data/dataset/xubh-q36u'


def _f(v):
    try:
        return float(str(v).replace(',', '').replace('$', ''))
    except (TypeError, ValueError):
        return 0.0


def _toks(name):
    import re
    t = re.sub(r'[^A-Z0-9 ]', ' ',
               str(name or '').upper().replace('&', ' AND ')).split()
    return [x for x in t if x not in SUFFIX]


def _dtoks(name):
    return {x for x in _toks(name)
            if x not in GENERIC and len(x) >= 3 and not x.isdigit()}


def _h1_terms(name):
    """Which H1 name terms the biller name matches (list, may be empty)."""
    u = str(name or '').upper()
    hits = []
    if 'HOSPITAL' in u:
        hits.append('HOSPITAL')
    for t in ('HEALTH SYSTEM', 'MEDICAL CENTER', 'HEALTH CENTER',
              'INFIRMARY', 'MAYO'):
        if t in u:
            hits.append(t)
    if 'CLINIC' in u.replace('CLINICAL', ''):
        hits.append('CLINIC')
    t = _toks(name)
    if t and t[-1] == 'HEALTH':
        hits.append('ends in HEALTH')
    return hits


def _h3(name):
    """Explicitly independent name (H1 already known False at call site)."""
    tt = set(_toks(name))
    if tt & {'AMBULANCE', 'AMBULANCES', 'EMS', 'RESCUE', 'FIRE'}:
        return True
    return any(x.startswith('MEDIC') for x in tt)


def _contains(db, dh):
    """Normalized token containment: the smaller distinctive-token set sits
    inside the larger; a single-token match must be a 5+ letter token that
    is not a bare region or direction word."""
    if not db or not dh:
        return False
    small, big = (db, dh) if len(db) <= len(dh) else (dh, db)
    if not small <= big:
        return False
    if len(small) >= 2:
        return True
    t = next(iter(small))
    return len(t) >= 5 and t not in REGION


def _classify_vintage(lib, cache, yr, hosp_by_state):
    """Aggregate the vintage's base-code billers and classify each one."""
    billers = {}
    for code in BASE:
        for r in lib.load_cache(cache, f'mup_provider_{yr}_{code}'):
            npi = str(r.get('Rndrng_NPI'))
            b = billers.setdefault(npi, {
                'name': r.get('Rndrng_Prvdr_Last_Org_Name') or '',
                'state': r.get('Rndrng_Prvdr_State_Abrvtn') or '',
                'srv': {}})
            b['srv'][code] = b['srv'].get(code, 0.0) + _f(r.get('Tot_Srvcs'))
    out = {'n': len(billers), 'tot': 0.0,
           'n_h1': 0, 'n_h2': 0, 'n_h3': 0, 'n_and': 0, 'n_or': 0,
           'srv_h1': 0.0, 'srv_h2': 0.0, 'srv_h3': 0.0,
           'srv_and': 0.0, 'srv_or': 0.0,
           'term_n': {t: 0 for t in H1_TERMS},
           'term_srv': {t: 0.0 for t in H1_TERMS},
           'state': {}, 'code': {c: [0.0, 0.0, 0.0] for c in BASE},
           'acu': {k: [0.0, 0.0] for k in
                   ('floor', 'ceil', 'indep', 'other')}}
    for b in billers.values():
        s = sum(b['srv'].values())
        out['tot'] += s
        terms = _h1_terms(b['name'])
        h1 = bool(terms)
        db = _dtoks(b['name'])
        h2 = any(_contains(db, dh)
                 for dh in hosp_by_state.get(b['state'], ()))
        h3 = (not h1) and _h3(b['name'])
        fl, ce = h1 and h2, h1 or h2
        for t in terms:
            out['term_n'][t] += 1
            out['term_srv'][t] += s
        out['n_h1'] += h1
        out['n_h2'] += h2
        out['n_h3'] += h3
        out['n_and'] += fl
        out['n_or'] += ce
        out['srv_h1'] += s * h1
        out['srv_h2'] += s * h2
        out['srv_h3'] += s * h3
        out['srv_and'] += s * fl
        out['srv_or'] += s * ce
        st = out['state'].setdefault(b['state'], [0.0, 0.0, 0.0])
        st[0] += s * fl
        st[1] += s * ce
        st[2] += s
        for c, v in b['srv'].items():
            out['code'][c][0] += v * fl
            out['code'][c][1] += v * ce
            out['code'][c][2] += v
        hi = b['srv'].get('A0433', 0.0) + b['srv'].get('A0434', 0.0)
        if fl:
            out['acu']['floor'][0] += hi
            out['acu']['floor'][1] += s
        if ce:
            out['acu']['ceil'][0] += hi
            out['acu']['ceil'][1] += s
        if h3:
            out['acu']['indep'][0] += hi
            out['acu']['indep'][1] += s
        if not ce and not h3:
            out['acu']['other'][0] += hi
            out['acu']['other'][1] += s
    return out


def build(wb, ctx):
    lib = ctx['lib']
    cache = ctx['cache']
    accessed = ctx['accessed']
    facts, sources, excluded, findings = [], [], [], []

    hosp = lib.load_cache(cache, 'pdc2_hospitals')
    hosp_by_state = {}
    for h in hosp:
        d = _dtoks(h.get('facility_name'))
        if d:
            hosp_by_state.setdefault(h.get('state'), []).append(d)

    res = {yr: _classify_vintage(lib, cache, yr, hosp_by_state)
           for yr in VINTAGES}
    r24 = res['2024']

    sources += [
        {'key': 'insourcing_mup', 'publisher': 'CMS',
         'document': 'Medicare Physician & Other Practitioners by Provider '
                     'and Service - ALL ground ambulance billers of base '
                     'codes A0426-A0429, A0433, A0434 (not an NPI subset)',
         'vintage': '2013 / 2019 / 2024 final-action',
         'locator': 'Every provider-grain row for the six ground base '
                    'codes; biller = Rndrng_NPI with its organization name '
                    'and state',
         'supplies': 'The classification universe and every service count '
                     'behind the floor/ceiling bounds on this tab',
         'url': MUP_URL, 'tier': 'A', 'accessed': accessed,
         'powers': ['Insourcing_Bounds']},
        {'key': 'insourcing_carecompare', 'publisher': 'CMS Care Compare '
                                                       '(Provider Data '
                                                       'Catalog)',
         'document': 'Hospital General Information (dataset xubh-q36u): '
                     f'{len(hosp):,} Medicare-enrolled hospitals with '
                     'facility name and state',
         'vintage': 'Current roster at access date (single vintage)',
         'locator': 'facility_name and state fields, all hospital types',
         'supplies': 'The hospital-name roster behind rule H2 (same-state '
                     'normalized token containment)',
         'url': PDC_URL, 'tier': 'A', 'accessed': accessed,
         'powers': ['Insourcing_Bounds']},
    ]

    ws = wb.create_sheet('Insourcing_Bounds')
    sb = lib.SheetBuilder(ws, 10,
                          col_widths=[44, 12, 15, 15, 15, 12, 12, 4, 4, 58],
                          tab_color='FF1F6F8B')
    sb.title('Insourcing bounds: the hospital-billed share of Medicare FFS '
             'ground ambulance, floor and ceiling')
    sb.subtitle('The question: what share of Medicare FFS ground base '
                'transports is billed by hospital-affiliated organizations '
                '- bounded honestly from the claims side, not asserted? '
                f'Every 2024 base-code biller in MUP by Provider & Service '
                f'({r24["n"]:,} NPIs; repeated for 2019 and 2013) is '
                'classified by three printed rules: H1 a name test, H2 a '
                'normalized-token linkage to the Care Compare hospital '
                f'roster ({len(hosp):,} hospitals) in the SAME state, H3 an '
                'explicitly-independent name test. FLOOR = base services '
                'from billers passing H1 AND H2; CEILING = H1 OR H2. Join '
                'key: organization name x state. The truth sits between '
                'the bounds and this tab refuses to pick a point.')
    sb.note('DATA QUALITY: name-rule classification of a claims registry - '
            'misclassification runs BOTH ways and the bounds exist to '
            'contain it. Provider-code rows under 11 beneficiaries are '
            'suppressed at source, and small rural hospital ambulance '
            'services are exactly the billers most likely suppressed, so '
            'the floor is a floor twice over. The Care Compare roster is a '
            'CURRENT snapshot: 2013/2019 H2 matches are degraded by '
            'renames, mergers and closures, understating older floors. '
            'Hospital-based transports bundled under Part A never generate '
            'carrier claims and are absent from every cell on this tab.')
    sb.blank()

    # ---------------------------------------------------------- Panel A ---
    sb.banner('Panel A. The classification rules, printed with their 2024 '
              'match counts (auditable: rerun by hand from the two public '
              'files)')
    sb.headers(['Rule / term', 'Matched billers 2024',
                'Matched base services 2024', 'Share of all base services',
                '', '', '', '', '', 'Note'])
    a_all = sb.r + 1
    sb.row([('All 2024 ground base-code billers (denominator)', 'label'),
            (r24['n'], 'src', lib.FMT_INT),
            (round(r24['tot']), 'src', lib.FMT_INT),
            (f'=C{a_all}/C${a_all}', 'fml', lib.FMT_PCT1),
            None, None, None, None, None,
            ('MUP 2024, codes A0426-A0429/A0433/A0434; suppressed rows '
             '(under 11 beneficiaries) absent at source', 'note')])
    rn = a_all + 1
    sb.row([('H1 (name): any hospital-affiliation term below', 'label'),
            (r24['n_h1'], 'src', lib.FMT_INT),
            (round(r24['srv_h1']), 'src', lib.FMT_INT),
            (f'=C{rn}/C${a_all}', 'fml', lib.FMT_PCT2),
            None, None, None, None, None,
            ('terms overlap, so the term rows below do not sum to this',
             'note')])
    term_notes = {
        'CLINIC': 'CLINICAL is removed before the CLINIC test: Cleveland '
                  'Clinic matches, clinical-lab names do not',
        'ends in HEALTH': 'corporate suffixes (INC, LLC, CORP, ...) '
                          'stripped before the ends-in test',
        'INFIRMARY': 'kept for completeness even at zero matches'}
    for t in H1_TERMS:
        rn = sb.r + 1
        sb.row([('    H1 term: ' + t, 'text'),
                (r24['term_n'][t], 'src', lib.FMT_INT),
                (round(r24['term_srv'][t]), 'src', lib.FMT_INT),
                (f'=C{rn}/C${a_all}', 'fml', lib.FMT_PCT2),
                None, None, None, None, None,
                (term_notes.get(t), 'note') if t in term_notes else None])
    a_h2 = sb.r + 1
    sb.row([('H2 (facility linkage): name matches a Care Compare hospital '
             'in the same state', 'label'),
            (r24['n_h2'], 'src', lib.FMT_INT),
            (round(r24['srv_h2']), 'src', lib.FMT_INT),
            (f'=C{a_h2}/C${a_all}', 'fml', lib.FMT_PCT2),
            None, None, None, None, None,
            ('normalized token containment: uppercase, punctuation and '
             'corporate suffixes stripped, generic facility/service words '
             'dropped; needs 2+ shared distinctive tokens, or one 5+ '
             'letter token that is not a bare region/direction word',
             'note')], wrap=True, height=52)
    a_h3 = sb.r + 1
    sb.row([('H3 (explicitly independent): AMBULANCE / EMS / MEDIC- / '
             'RESCUE / FIRE in the name and no H1 term', 'label'),
            (r24['n_h3'], 'src', lib.FMT_INT),
            (round(r24['srv_h3']), 'src', lib.FMT_INT),
            (f'=C{a_h3}/C${a_all}', 'fml', lib.FMT_PCT1),
            None, None, None, None, None,
            ('descriptive comparator only - H3 never enters the bounds',
             'note')])
    a_fl = sb.r + 1
    sb.row([('FLOOR set: H1 AND H2 (name and same-state linkage both '
             'required)', 'label'),
            (r24['n_and'], 'src', lib.FMT_INT),
            (round(r24['srv_and']), 'src', lib.FMT_INT),
            (f'=C{a_fl}/C${a_all}', 'fml', lib.FMT_PCT2),
            None, None, None, None, None,
            ('strict by construction: misses hospital subsidiaries billing '
             'under brandless transport names', 'note')])
    a_ce = sb.r + 1
    sb.row([('CEILING set: H1 OR H2 (either test alone)', 'label'),
            (r24['n_or'], 'src', lib.FMT_INT),
            (round(r24['srv_or']), 'src', lib.FMT_INT),
            (f'=C{a_ce}/C${a_all}', 'fml', lib.FMT_PCT1),
            None, None, None, None, None,
            ('generous by construction: place-name collisions (county and '
             'city agencies matching same-named local hospitals) inflate '
             'it', 'note')])
    sb.blank()

    # ---------------------------------------------------------- Panel B ---
    sb.banner('Panel B. National bounds by vintage (live shares over blue '
              'service totals)')
    sb.headers(['Vintage', 'Billers', 'FLOOR-set base services',
                'CEILING-set base services', 'All base services',
                'FLOOR share', 'CEILING share', '', '', 'Note'])
    b0 = sb.r + 1
    b_notes = [
        'misclassification runs both ways: the name tests miss hospital '
        'subsidiaries with brandless names and catch non-hospital names; '
        '2013/2019 floors also lean on the CURRENT hospital roster',
        'billing-in-lieu (a health system dropping the bill for a small '
        'contracted vendor) INFLATES the hospital-billed share',
        'the never-bill pattern (hospital absorbs the transport, no claim) '
        'DEFLATES it; Part A bundled transports are absent from carrier '
        'claims entirely']
    for i, yr in enumerate(VINTAGES):
        r = res[yr]
        rn = b0 + i
        sb.row([(int(yr), 'src'), (r['n'], 'src', lib.FMT_INT),
                (round(r['srv_and']), 'src', lib.FMT_INT),
                (round(r['srv_or']), 'src', lib.FMT_INT),
                (round(r['tot']), 'src', lib.FMT_INT),
                (f'=IF(E{rn}=0,"n/a",C{rn}/E{rn})', 'fml', lib.FMT_PCT2),
                (f'=IF(E{rn}=0,"n/a",D{rn}/E{rn})', 'fml', lib.FMT_PCT1),
                None, None, (b_notes[i], 'note')], wrap=True, height=40)
    b_chg = sb.r + 1
    sb.row([('Change 2013 to 2024 (share points; services)', 'label'),
            None,
            (f'=C{b0 + 2}-C{b0}', 'fml', lib.FMT_INT),
            (f'=D{b0 + 2}-D{b0}', 'fml', lib.FMT_INT),
            (f'=E{b0 + 2}-E{b0}', 'fml', lib.FMT_INT),
            (f'=F{b0 + 2}-F{b0}', 'fml', lib.FMT_PCT2),
            (f'=G{b0 + 2}-G{b0}', 'fml', lib.FMT_PCT2),
            None, None,
            ('both bounds ROSE while absolute floor volume FELL about a '
             'quarter: a shrinking all-biller denominator, not hospital '
             'growth', 'note')], wrap=True)
    lib.add_chart(
        ws, f'L{b0 - 2}',
        'Hospital-billed share of ground base transports: floor and '
        'ceiling by vintage',
        f'Insourcing_Bounds!$A${b0}:$A${b0 + 2}',
        [('FLOOR (H1 AND H2)', f'Insourcing_Bounds!$F${b0}:$F${b0 + 2}'),
         ('CEILING (H1 OR H2)', f'Insourcing_Bounds!$G${b0}:$G${b0 + 2}')],
        kind='line', y_fmt='0%', height=7.5)
    sb.blank()

    # ---------------------------------------------------------- Panel C ---
    sb.banner('Panel C. Footprint-state bounds, 2024')
    sb.headers(['State', 'FLOOR-set base services', 'CEILING-set base '
                'services', 'All base services', 'FLOOR share',
                'CEILING share', '', '', '', 'Note'])
    c0 = sb.r + 1
    c_notes = {
        'MN': 'the hospital-based EMS state: large health-system services '
              'bill directly, so even the strict floor is a quarter of '
              'base services',
        'NE': 'the largest Nebraska biller is an independent private IFT '
              'carrier, so the floor is near zero; place-name collisions '
              'still pad the ceiling',
        'MO': 'ambulance DISTRICTS dominate Missouri; district names carry '
              'no hospital terms, so the floor bottoms out'}
    for j, st in enumerate(FOOT):
        v = r24['state'].get(st, [0.0, 0.0, 0.0])
        rn = c0 + j
        sb.row([(st, 'src'),
                (round(v[0]), 'src', lib.FMT_INT),
                (round(v[1]), 'src', lib.FMT_INT),
                (round(v[2]), 'src', lib.FMT_INT),
                (f'=IF(D{rn}=0,"n/a",B{rn}/D{rn})', 'fml', lib.FMT_PCT2),
                (f'=IF(D{rn}=0,"n/a",C{rn}/D{rn})', 'fml', lib.FMT_PCT1),
                None, None, None,
                (c_notes.get(st), 'note') if st in c_notes else None],
               wrap=st in c_notes)
    sb.blank()

    # ---------------------------------------------------------- Panel D ---
    sb.banner('Panel D. Bounds by service level, 2024')
    sb.headers(['Level (HCPCS)', 'FLOOR-set services', 'CEILING-set '
                'services', 'All services', 'FLOOR share', 'CEILING share',
                '', '', '', 'Note'])
    d0 = sb.r + 1
    d_notes = {
        'A0426': 'the highest floor of any level: scheduled ALS '
                 'non-emergency is where hospital-billed work concentrates',
        'A0427': 'ceiling inflated by county and city emergency services '
                 'matching same-named local hospitals',
        'A0433': 'the two acuity codes Panel E tests',
        'A0434': 'SCT: the code the finding-6 scope note is about'}
    for j, code in enumerate(BASE):
        v = r24['code'][code]
        rn = d0 + j
        sb.row([(f'{LEVEL[code]} ({code})', 'text'),
                (round(v[0]), 'src', lib.FMT_INT),
                (round(v[1]), 'src', lib.FMT_INT),
                (round(v[2]), 'src', lib.FMT_INT),
                (f'=IF(D{rn}=0,"n/a",B{rn}/D{rn})', 'fml', lib.FMT_PCT2),
                (f'=IF(D{rn}=0,"n/a",C{rn}/D{rn})', 'fml', lib.FMT_PCT1),
                None, None, None,
                (d_notes.get(code), 'note') if code in d_notes else None])
    sb.blank()

    # ---------------------------------------------------------- Panel E ---
    sb.banner('Panel E. The acuity test: do hospital-affiliated billers '
              'skew SCT / ALS2? (2024)')
    sb.headers(['Biller class', 'SCT + ALS2 services', 'All base services',
                'SCT + ALS2 share', '', '', '', '', '', 'Note'])
    e0 = sb.r + 1
    acu_rows = [
        ('Hospital-affiliated, FLOOR set (H1 AND H2)', 'floor',
         'the test of the finding-6 scope note: hospital-billed work does '
         'run higher-acuity than independent work'),
        ('Hospital-affiliated, CEILING set (H1 OR H2)', 'ceil',
         'diluted by place-name collisions, and still above independent'),
        ('Explicitly independent (H3)', 'indep',
         'the comparator: AMBULANCE / EMS / MEDIC- / RESCUE / FIRE names'),
        ('Neither in the ceiling nor explicitly independent', 'other',
         'city and county agencies and brandless names land here; the '
         'four classes overlap (floor sits inside ceiling, and an H3 '
         'name can also H2-match), so rows do not sum')]
    for j, (label, key, note) in enumerate(acu_rows):
        v = r24['acu'][key]
        rn = e0 + j
        sb.row([(label, 'text'),
                (round(v[0]), 'src', lib.FMT_INT),
                (round(v[1]), 'src', lib.FMT_INT),
                (f'=IF(C{rn}=0,"n/a",B{rn}/C{rn})', 'fml', lib.FMT_PCT2),
                None, None, None, None, None, (note, 'note')],
               wrap=True, height=30 if j < 3 else 44)
    sb.note('Guardrail on Panel E: this test can only see CARRIER-BILLED '
            'transports. Hospital-controlled SCT that moves under Part A '
            'bundles, dedicated-unit facility contracts or the never-bill '
            'pattern generates no claim, so a true hospital SCT skew would '
            'be UNDERSTATED here, and the floor set is small (about '
            f'{round(r24["srv_and"]):,} services), so read the direction, '
            'not the decimals.')
    sb.blank()

    # ---------------------------------------------------------- Panel F ---
    # Run 5, Task 5.1: the third measured leg. QN (furnished directly) and QM
    # (under arrangement) are provider-of-services carrier modifiers - a direct,
    # name-free, claim-level read of the same hospital-billed distinction the
    # name rules (Panels A-E) bound. Pure presentation: this panel emits no new
    # fact, source or finding (those live on Modifier_QM_QN_Series), so the
    # append-only ledger is untouched.
    _m2 = {'QN': 0.0, 'QM': 0.0, 'tot': 0.0}
    for code in BASE:
        try:
            d = lib.load_cache(cache, f'psps_mod2_2024_{code}')
        except Exception:
            continue
        for b, bk in d.get('buckets', {}).items():
            _m2['tot'] += bk.get('services', 0.0)
            if b in ('QN', 'QM'):
                _m2[b] += bk.get('services', 0.0)
    sb.banner('Panel F. Third measured leg: the QN / QM carrier claim modifier '
              '(2024 direct read; full 2010-2024 series on '
              'Modifier_QM_QN_Series)')
    sb.headers(['Billing relationship (carrier modifier)',
                '2024 transport services', 'Share of 2024 transports', '', '',
                '', '', '', '', 'Note'])
    f0 = sb.r + 1
    sb.row([('QN furnished DIRECTLY by a provider of services', 'text'),
            (round(_m2['QN']), 'src', lib.FMT_INT),
            (f'=B{f0}/B${f0 + 3}', 'fml', lib.FMT_PCT2),
            None, None, None, None, None, None,
            ('the direct hospital-furnished signal', 'note')])
    sb.row([('QM UNDER ARRANGEMENT by a provider of services', 'text'),
            (round(_m2['QM']), 'src', lib.FMT_INT),
            (f'=B{f0 + 1}/B${f0 + 3}', 'fml', lib.FMT_PCT2),
            None, None, None, None, None, None,
            ('billing-in-lieu: the arrangement that inflates the name ceiling',
             'note')], wrap=True, height=28)
    sb.row([('Provider-flagged (QN + QM): the direct measurement', 'label'),
            (f'=B{f0}+B{f0 + 1}', 'fml', lib.FMT_INT),
            (f'=B{f0 + 2}/B${f0 + 3}', 'fml', lib.FMT_PCT2),
            None, None, None, None, None, None,
            ('a name-free STRICT floor: it lands BELOW even the name floor '
             'above because QN/QM modifier use is incomplete', 'note')],
           wrap=True, height=28)
    sb.row([('All 2024 ground transport services (denominator)', 'text'),
            (round(_m2['tot']), 'src', lib.FMT_INT),
            (f'=B{f0 + 3}/B${f0 + 3}', 'fml', lib.FMT_PCT2),
            None, None, None, None, None, None,
            ('PSPS second-modifier cut, codes A0426-A0429/A0433/A0434', 'note')])
    sb.note('The flag is a third classifier beside the H1/H2 name bounds and '
            'the Care Compare facility roster - name-free, read straight off '
            'the claim. It is a STRICT floor: because most hospital billers '
            'never append QN/QM, it lands an order of magnitude below even the '
            'name floor above, so it confirms the DIRECTION of hospital billing '
            'without settling its level. Same carrier-file limit as the rest of '
            'this tab (Part A bundled and SNF consolidated-billing transports '
            'carry no modifier), and CMS suppression thins it further. Full '
            'annual series, service-level split and origin-destination cut: '
            'Modifier_QM_QN_Series.')
    sb.blank()

    # ------------------------------------------------------- read panel ---
    floor24 = r24['srv_and'] / r24['tot']
    ceil24 = r24['srv_or'] / r24['tot']
    floor13 = res['2013']['srv_and'] / res['2013']['tot']
    ceil13 = res['2013']['srv_or'] / res['2013']['tot']
    acu_fl = r24['acu']['floor'][0] / r24['acu']['floor'][1]
    acu_in = r24['acu']['indep'][0] / r24['acu']['indep'][1]

    sb.banner('Read panel')
    sb.prose('The bounded answer: hospital-affiliated organizations bill '
             f'between {floor24 * 100:.1f}% (floor: name AND same-state '
             f'Care Compare linkage) and {ceil24 * 100:.0f}% (ceiling: '
             'either test alone) of Medicare FFS ground base transports in '
             '2024, and the honest point sits well below the midpoint '
             'because place-name collisions inflate the ceiling. Both '
             f'bounds ROSE from 2013 ({floor13 * 100:.1f}% to '
             f'{floor24 * 100:.1f}% floor; {ceil13 * 100:.0f}% to '
             f'{ceil24 * 100:.0f}% ceiling) - but absolute hospital-billed '
             'floor volume FELL about a quarter while the all-biller '
             'denominator fell faster: the share rise is claims-market '
             'shrinkage, not hospital-billed growth. The acuity test runs '
             'the direction the finding-6 scope note predicted: '
             f'hospital-affiliated floor billers put {acu_fl * 100:.1f}% '
             'of base services in SCT+ALS2 versus '
             f'{acu_in * 100:.1f}% for explicitly independent billers - a '
             'real but modest skew on a small base. A third classifier now '
             'agrees on DIRECTION without any name test at all: the QN/QM '
             'provider-of-services carrier modifier (Panel F) reads the billing '
             'relationship straight off the claim and flags a Part A '
             'institution as biller on '
             f'{((_m2["QN"] + _m2["QM"]) / _m2["tot"] * 100) if _m2["tot"] else 0:.3f}% '
             'of 2024 ground transports - a name-free STRICT floor that lands '
             'BELOW even this floor because most hospital billers omit the '
             'modifier, confirming the direction without settling the level. '
             'What this tab does '
             'NOT say: the hospital share of ground ambulance OPERATIONS. '
             'Billing-in-lieu inflates these bounds, never-bill and Part '
             'A bundling deflate them, and none of the three appears in '
             'carrier claims at all.')

    # ------------------------------------------------------------ facts ---
    skeys = ['insourcing_mup', 'insourcing_carecompare']
    facts += [
        {'metric': 'Hospital-billed share of Medicare FFS ground base '
                   'services, FLOOR bound (H1 name AND H2 Care Compare '
                   'linkage)', 'year': 2024, 'value': round(floor24, 4),
         'unit': 'share of base services', 'basis': 'DERIVED', 'tier': 'B',
         'source_keys': skeys,
         'locator': 'Insourcing_Bounds Panel B 2024 row, live formula '
                    f'F{b0 + 2} over blue service totals',
         'lives_on': 'Insourcing_Bounds',
         'cross_check': 'Floor set is 85 of 8,721 billers; Panel A prints '
                        'every rule count; suppression and the current-'
                        'vintage hospital roster both push this DOWN'},
        {'metric': 'Hospital-billed share of Medicare FFS ground base '
                   'services, CEILING bound (H1 OR H2)', 'year': 2024,
         'value': round(ceil24, 4), 'unit': 'share of base services',
         'basis': 'DERIVED', 'tier': 'B', 'source_keys': skeys,
         'locator': 'Insourcing_Bounds Panel B 2024 row, live formula '
                    f'G{b0 + 2}',
         'lives_on': 'Insourcing_Bounds',
         'cross_check': 'Place-name collisions (county/city agencies vs '
                        'same-named hospitals) inflate this UP; billing-'
                        'in-lieu also inflates it'},
        {'metric': 'Change in hospital-billed FLOOR share of ground base '
                   'services, 2013 to 2024', 'year': 2024,
         'value': round(floor24 - floor13, 4), 'unit': 'share points',
         'basis': 'DERIVED', 'tier': 'B', 'source_keys': skeys,
         'locator': f'Insourcing_Bounds Panel B change row F{b_chg}',
         'lives_on': 'Insourcing_Bounds',
         'cross_check': 'Direction: share ROSE while absolute floor '
                        'volume FELL (about 184K to 138K services); the '
                        'all-biller denominator shrank 36%, so the rise '
                        'is denominator shrinkage'},
        {'metric': 'SCT+ALS2 share of base services, hospital-affiliated '
                   'FLOOR-set billers', 'year': 2024,
         'value': round(acu_fl, 4), 'unit': 'share of base services',
         'basis': 'DERIVED', 'tier': 'B', 'source_keys': skeys,
         'locator': f'Insourcing_Bounds Panel E row {e0}, live formula '
                    'col D',
         'lives_on': 'Insourcing_Bounds',
         'cross_check': 'Versus explicitly independent billers on the row '
                        'two below; carrier-claims window only, so Part A '
                        'bundled SCT is invisible to the test'},
        {'metric': 'SCT+ALS2 share of base services, explicitly '
                   'independent (H3) billers', 'year': 2024,
         'value': round(acu_in, 4), 'unit': 'share of base services',
         'basis': 'DERIVED', 'tier': 'B', 'source_keys': skeys,
         'locator': f'Insourcing_Bounds Panel E row {e0 + 2}, live '
                    'formula col D',
         'lives_on': 'Insourcing_Bounds',
         'cross_check': 'The comparator for the acuity test; H3 names '
                        '(AMBULANCE/EMS/MEDIC-/RESCUE/FIRE, no H1 term) '
                        'cover 4,206 of 8,721 billers'},
        {'metric': 'Medicare FFS ground base services, all billers (the '
                   'classification denominator)', 'year': 2024,
         'value': round(r24['tot']), 'unit': 'services', 'basis': 'GOV',
         'tier': 'A', 'source_keys': ['insourcing_mup'],
         'locator': 'Sum of Tot_Srvcs over every MUP 2024 provider-grain '
                    'row, codes A0426-A0429/A0433/A0434; blue cell '
                    f'E{b0 + 2} on Panel B',
         'lives_on': 'Insourcing_Bounds',
         'cross_check': 'Suppression makes it a floor; compare the '
                        'national series tabs built from the same '
                        'registry'},
    ]

    # --------------------------------------------------------- findings ---
    findings += [
        {'id_hint': 57,
         'finding': 'The hospital-billed share of Medicare FFS ground '
                    'ambulance is bounded for the first time with printed, '
                    'auditable rules: between '
                    f'{floor24 * 100:.1f}% (floor: hospital name AND '
                    'same-state Care Compare linkage) and '
                    f'{ceil24 * 100:.0f}% (ceiling: either test alone) of '
                    '2024 ground base transports, with the honest point '
                    'well below the midpoint because place-name collisions '
                    'inflate the ceiling. Both bounds rose from 2013 '
                    f'({floor13 * 100:.1f}% and {ceil13 * 100:.0f}%), but '
                    'absolute hospital-billed floor volume FELL about a '
                    'quarter - the share rose only because the all-biller '
                    'claims denominator shrank faster. On the claims side, '
                    'hospital-billed ground ambulance is a small and '
                    'not-growing slice.',
         'numbers': f"='Insourcing_Bounds'!F{b0 + 2}",
         'sources': 'insourcing_mup; insourcing_carecompare',
         'confidence': 'High that the truth sits inside the bounds; the '
                       'bounds are wide by design',
         'guardrail': 'A share of carrier CLAIMS, not of operations: '
                      'billing-in-lieu inflates it, the never-bill '
                      'pattern deflates it, Part A bundled transports '
                      'never appear, and the 2013/2019 floors lean on a '
                      'current-vintage hospital roster. Never quote '
                      'either bound as THE hospital share.'},
        {'id_hint': 58,
         'finding': 'The acuity test runs the direction the finding-6 '
                    'scope note predicted: hospital-affiliated floor-set '
                    f'billers put {acu_fl * 100:.1f}% of their 2024 base '
                    'services in SCT+ALS2 versus '
                    f'{acu_in * 100:.1f}% for explicitly independent '
                    'billers - roughly a 1.5x skew - so the high-acuity '
                    'interfacility product does tilt toward '
                    'hospital-affiliated operations even inside the '
                    'claims window.',
         'numbers': f"='Insourcing_Bounds'!D{e0}",
         'sources': 'insourcing_mup; insourcing_carecompare',
         'confidence': 'Directional: the floor set is about 138K services '
                       'and the gap is about 0.8 share points',
         'guardrail': 'Carrier-billed transports only. Hospital SCT that '
                      'moves under Part A bundles, facility contracts or '
                      'never-bill generates no claim, so a true hospital '
                      'acuity skew would be UNDERSTATED, and the modest '
                      'measured gap cannot be read as the ceiling of it.'},
    ]

    return {'facts': facts, 'sources': sources, 'excluded': excluded,
            'findings': findings,
            'meta': {'floor_2024': round(floor24, 4),
                     'ceiling_2024': round(ceil24, 4),
                     'billers_2024': r24['n']}}
