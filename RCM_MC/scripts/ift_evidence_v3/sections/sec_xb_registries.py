"""X-B.1 / X-E.1 / X-E.2: two registry tabs.

State_EMS_Licensure - the state licensure universe for the four executed
states (NE, IA, KS, MO): per-state panels of publicly rostered services,
roll-ups, and the three-universe comparison (licensed vs PECOS-enrolled vs
Medicare-billing) that extends finding 46 with a fourth universe.

Press_Footprint_Registry - Panel A: dated public press/newsroom
announcements by the subject company and resolved market participants
(PUBLIC-WEB, URL + date per row). Panel B: the archived-website self-claim
series for the subject company's own public site (Wayback-recorded rows +
Common Crawl content rows), labeled self-claims throughout.
"""

SHEETS = [
    {'name': 'State_EMS_Licensure',
     'question': 'Who is licensed to run ambulances in NE/IA/KS/MO per the '
                 'states\' own public rosters, and how does that universe '
                 'compare with PECOS enrollment and Medicare billing?'},
    {'name': 'Press_Footprint_Registry',
     'question': 'What do issuers publicly announce (entries, deals, '
                 'leadership), and what did the subject company\'s own '
                 'website claim about its footprint over time?'},
]

GROUND = ['A0426', 'A0427', 'A0428', 'A0429', 'A0433', 'A0434']
STATES = ['NE', 'IA', 'KS', 'MO']
STATE_NAMES = {'NE': 'Nebraska', 'IA': 'Iowa', 'KS': 'Kansas',
               'MO': 'Missouri'}


def _clean(s, cap=None):
    """House rule: no em dashes in cell text; keep text single-line."""
    if s is None:
        return None
    s = str(s).replace('—', ' - ').replace('–', '-')
    s = ' '.join(s.split())
    if cap and len(s) > cap:
        s = s[:cap - 3].rstrip() + '...'
    return s


def _mup_state_billers(lib, cache):
    """Distinct 2024 ground-base billing NPIs per state, computed from the
    already-manifested MUP provider-grain caches (org entities counted
    separately)."""
    npis = {s: set() for s in STATES}
    orgs = {s: set() for s in STATES}
    for code in GROUND:
        try:
            rows = lib.load_cache(cache, f'mup_provider_2024_{code}')
        except FileNotFoundError:
            continue
        for r in rows:
            st = r.get('Rndrng_Prvdr_State_Abrvtn')
            if st in npis:
                npis[st].add(r.get('Rndrng_NPI'))
                if r.get('Rndrng_Prvdr_Ent_Cd') == 'O':
                    orgs[st].add(r.get('Rndrng_NPI'))
    return ({s: len(v) for s, v in npis.items()},
            {s: len(v) for s, v in orgs.items()})


def _pecos_links(state):
    """Green cross-tab formulas against tabs already in the workbook."""
    countif = f'=COUNTIF(PECOS_Registry!$E:$E,"{state}")'
    idx = ('=INDEX(PECOS_Suppliers_State!$C$13:$C$70,'
           f'MATCH("{state}",PECOS_Suppliers_State!$A$13:$A$70,0))')
    rend = ('=INDEX(PECOS_Suppliers_State!$F$13:$F$70,'
            f'MATCH("{state}",PECOS_Suppliers_State!$A$13:$A$70,0))')
    return countif, idx, rend


def build(wb, ctx):
    lib = ctx['lib']
    cache = ctx['cache']
    facts, sources, excluded, findings = [], [], [], []

    rosters = lib.load_cache(cache, 'state_ems_rosters')
    press = lib.load_cache(cache, 'press_registry')
    wayback = lib.load_cache(cache, 'wayback_footprint')
    mup_all, mup_org = _mup_state_billers(lib, cache)

    # ------------------------------------------------------------------ #
    # sources (tab 1)
    # ------------------------------------------------------------------ #
    acc = ctx['accessed']
    sources += [
        {'key': 'xb_mo_socrata', 'publisher': 'Missouri DHSS Bureau of EMS '
                                              '(via data.mo.gov Socrata)',
         'document': 'DIRECTORIES - GROUND AMBULANCES (e7p8-a69d), Air '
                     'Ambulance Services (6xq5-em5d), Stretcher Van '
                     '(usf4-uuvb) - licensed-service directories from the '
                     'bureau license management system',
         'vintage': 'ground rows updated 2026-05-14; air/stretcher '
                    '2026-04-16 (Socrata metadata)',
         'locator': 'Full JSON pulls of all three datasets; service name / '
                    'city / county / classification / license number '
                    'harvested; contact-person fields not harvested',
         'url': 'https://data.mo.gov/resource/e7p8-a69d.json',
         'tier': 'A', 'accessed': acc, 'powers': ['State_EMS_Licensure']},
        {'key': 'xb_ia_2013', 'publisher': 'Iowa Department of Public '
                                           'Health (legislative attachment)',
         'document': 'Attachment B - Authorized Iowa EMS Agencies '
                     '(September 2013), the most recent FULL public roster '
                     'located',
         'vintage': 'September 2013',
         'locator': '14-page PDF; 779 rows parsed (2+space column split; '
                    'wrapped two-line names merge imperfectly - row count '
                    'is a parse floor)',
         'url': 'https://www.legis.iowa.gov/docs/publications/SD/17002.pdf',
         'tier': 'B', 'accessed': acc, 'powers': ['State_EMS_Licensure']},
        {'key': 'xb_ia_snapshot25', 'publisher': 'Iowa HHS Bureau of '
                                                 'Emergency Medical and '
                                                 'Trauma Services',
         'document': 'Iowa Emergency Medical Services Snapshot (June 2025)',
         'vintage': 'June 2025',
         'locator': 'Page 1 counts: 724 authorized service programs, 901 '
                    'locations (502 ambulance / 375 non-transport / 24 air '
                    'medical); >70% at least partially volunteer-reliant',
         'url': 'https://hhs.iowa.gov/media/16564/download?inline=',
         'tier': 'A', 'accessed': acc, 'powers': ['State_EMS_Licensure']},
        {'key': 'xb_ne_ng911', 'publisher': 'State of Nebraska (NebraskaMAP '
                                            '/ gis.ne.gov)',
         'document': 'Rescue/EMS Response Areas feature layer (NG911 '
                     'EMS911), statewide',
         'vintage': 'layer modified 2026-03-16',
         'locator': 'ArcGIS REST query, all 977 polygons, fields '
                    'DsplayName/Agency_ID/ServiceNum; 504 distinct service '
                    'display names',
         'url': 'https://gis.ne.gov/Enterprise/rest/services/'
                'Rescue_District_Response_Area/FeatureServer/0',
         'tier': 'B', 'accessed': acc, 'powers': ['State_EMS_Licensure']},
        {'key': 'xb_ne_roster_page', 'publisher': 'Nebraska DHHS',
         'document': 'Rosters of Facilities and Services page - documents '
                     'that the EMS roster is offline: "Emergency Medical '
                     'Services/Providers - This roster is temporarily '
                     'unavailable."',
         'vintage': 'as viewed ' + acc,
         'locator': 'Roster list page, EMS entry',
         'url': 'https://dhhs.ne.gov/licensure/Pages/'
                'Rosters-of-Facilities-and-Services.aspx',
         'tier': 'B', 'accessed': acc, 'powers': ['State_EMS_Licensure']},
        {'key': 'xb_ks_kemsis20', 'publisher': 'Kansas Board of EMS',
         'document': 'EMS Services Reporting - 2019 (KEMSIS reporting '
                     'entities, as of January 31, 2020)',
         'vintage': 'January 31, 2020',
         'locator': 'Two-column PDF by EMS region; 164 service names '
                    'parsed; a REPORTING roster, not the licensure roster',
         'url': 'https://www.ksbems.org/html%20pages/'
                'KEMSIS%20Reporting%20Entities.pdf',
         'tier': 'B', 'accessed': acc, 'powers': ['State_EMS_Licensure']},
        {'key': 'xb_mup24_state', 'publisher': 'CMS',
         'document': 'Medicare Physician & Other Practitioners by Provider '
                     'and Service, CY2024 - state ground-biller counts '
                     '(distinct NPIs with any ground base-code row, '
                     'A0426-A0429/A0433/A0434)',
         'vintage': 'CY2024 final-action',
         'locator': 'mup_provider_2024_* caches, Rndrng_Prvdr_State_Abrvtn '
                    'in NE/IA/KS/MO',
         'url': 'https://data.cms.gov/provider-summary-by-type-of-service/'
                'medicare-physician-other-practitioners/medicare-physician-'
                'other-practitioners-by-provider-and-service',
         'tier': 'A', 'accessed': acc, 'powers': ['State_EMS_Licensure']},
    ]

    # ================================================================== #
    # TAB 1: State_EMS_Licensure
    # ================================================================== #
    ws = wb.create_sheet('State_EMS_Licensure')
    sb = lib.SheetBuilder(ws, 10,
                          col_widths=[44, 17, 16, 7, 20, 13, 14, 13, 10, 36],
                          tab_color='FF00838F')
    sb.title('State EMS licensure rosters: the licensed universe in the '
             'four executed states, against PECOS enrollment and Medicare '
             'billing')
    sb.subtitle('The question: who is licensed/authorized to operate '
                'ambulance services in NE, IA, KS and MO according to each '
                'state\'s own PUBLIC roster - and how much of that licensed '
                'universe never appears in Medicare claims? Sources: MO '
                'DHSS directories on data.mo.gov; IDPH Authorized Iowa EMS '
                'Agencies (Sep 2013) + Iowa HHS EMS Snapshot (Jun 2025); '
                'Nebraska NG911 Rescue/EMS Response Areas layer (DHHS '
                'licensure roster offline); KBEMS KEMSIS reporting list '
                '(Jan 2020). Join keys: state; comparison universes joined '
                'on state only (name-level joins are NOT attempted). '
                'Cross-tab links: PECOS_Registry (col E), '
                'PECOS_Suppliers_State (Panel B).')
    sb.note('DATA QUALITY: the four states publish four DIFFERENT objects. '
            'MO publishes a current licensed-service directory (no BLS/ALS '
            'level, no vehicle counts); IA\'s only FULL public roster is '
            'Sep 2013 (current directory sits behind a JS-only portal) '
            'with official June 2025 roll-up counts; NE\'s DHHS roster is '
            '"temporarily unavailable" per the state page, so the NG911 '
            'response-area registry stands in (a 911 dispatch registry, '
            'NOT a licensure roster); KS\'s current roster is portal-only '
            '(API returns 401), so the Jan 2020 KEMSIS reporting list '
            'stands in (non-reporting services absent). Vehicle/unit '
            'counts: published by NONE of the four states\' public '
            'rosters. Every count below is labeled with its object and '
            'vintage; do not mix them silently.')
    sb.blank()

    # ---------------- Panel A: Missouri ---------------- #
    mo = rosters['MO']
    sb.banner('Panel A. Missouri - licensed ambulance services, DHSS '
              'Bureau of EMS via data.mo.gov (LANDED; ground vintage '
              '2026-05-14)')
    sb.headers(['Service name', 'City', 'County', 'State',
                'Classification', 'Ground / air', 'License no.', 'Vintage',
                'Basis', 'Note'])
    a0 = sb.r + 1
    for i, r in enumerate(mo['rows']):
        sb.row([(_clean(r['service_name'], 60), 'src'),
                (_clean(r['city'], 24), 'src'),
                (_clean(r['county'], 22), 'src'),
                (_clean(r.get('state') or 'MO'), 'src'),
                (_clean(r['service_classification']), 'src'),
                (r['ground_or_air'], 'src'),
                (_clean(r.get('license_number')), 'src'),
                ('2026-05' if r['ground_or_air'] == 'ground' else '2026-04',
                 'src'),
                ('GOV', 'text'),
                ('license management system extract; contact fields not '
                 'harvested', 'note') if i == 0 else None])
    a1 = sb.r
    sb.row([('MISSOURI ROLL-UP (live)', 'label'), None, None, None, None,
            None, None, None, None, None])
    sb.row([('Ground ambulance services', 'label'),
            (f'=COUNTIF(F{a0}:F{a1},"ground")', 'fml', lib.FMT_INT),
            None, None, None, None, None, None, None,
            ('455 expected from source pull', 'note')])
    mo_ground_row = sb.r
    sb.row([('Air ambulance services', 'label'),
            (f'=COUNTIF(F{a0}:F{a1},"air")', 'fml', lib.FMT_INT),
            None, None, None, None, None, None, None, None])
    sb.row([('Stretcher van services (non-ambulance tier)', 'label'),
            (f'=COUNTIF(F{a0}:F{a1},"stretcher van")', 'fml', lib.FMT_INT),
            None, None, None, None, None, None, None,
            ('licensed but not an ambulance level; excluded from the '
             'three-universe row', 'note')])
    sb.blank()

    # ---------------- Panel B: Iowa ---------------- #
    ia = rosters['IA']
    ru = ia['rollup_2025']
    sb.banner('Panel B. Iowa - authorized EMS service programs (roll-up '
              'June 2025 official; full roster panel vintage September '
              '2013)')
    sb.headers(['Iowa roll-up item (Iowa HHS EMS Snapshot, June 2025)',
                'Value', '', '', '', '', '', '', 'Basis', 'Note'])
    b_ru0 = sb.r + 1
    for label, val, note in [
            ('Authorized EMS service programs',
             ru['authorized_service_programs'], 'programs, statewide'),
            ('EMS service locations', ru['service_locations'],
             'programs operate from more locations than programs'),
            ('Locations - Ambulance (transport)',
             ru['locations_ambulance'], ''),
            ('Locations - Non-transport', ru['locations_non_transport'],
             ''),
            ('Locations - Air medical', ru['locations_air_medical'], '')]:
        sb.row([(label, 'label'), (val, 'src', lib.FMT_INT), None, None,
                None, None, None, None, ('GOV', 'text'),
                (note, 'note') if note else None])
    ia_amb_row = b_ru0 + 2
    sb.note('Verbatim from the June 2025 snapshot: "More than 70% of these '
            'services are at least partially reliant on volunteer '
            'staffing." The full CURRENT program directory is behind the '
            'AMANDA public portal (JS-only); the panel below is the most '
            'recent FULL public roster (IDPH, September 2013) and is '
            'carried as a vintage-labeled registry, not as the current '
            'state of Iowa licensure.')
    sb.headers(['Service name (Sep 2013 roster)', 'City', 'County', 'State',
                'Service level', 'Type (ground/air/non-transport)',
                'Ownership', 'Vintage', 'Basis', 'Note'])
    b0 = sb.r + 1
    for i, r in enumerate(ia['rows']):
        sb.row([(_clean(r['service_name'], 60), 'src'),
                (_clean(r['city'], 24), 'src'),
                (_clean(r['county'], 22), 'src'),
                (_clean(r.get('state')), 'src'),
                (_clean(r.get('service_level')), 'src'),
                (_clean(r.get('service_type'), 36), 'src'),
                (_clean(r.get('ownership_type'), 22), 'src'),
                ('2013-09', 'src'), ('GOV', 'text'),
                ('service_type "Ambulance with Transport Agreement" is a '
                 'transporting tier', 'note') if i == 0 else None])
    b1 = sb.r
    sb.row([('IOWA 2013 ROSTER ROLL-UP (live; parse floor)', 'label'),
            (f'=COUNTA(A{b0}:A{b1})', 'fml', lib.FMT_INT), None, None, None,
            None, None, None, None,
            ('779 parsed of a printed list slightly larger (wrapped names) '
             '- floor', 'note')])
    sb.row([('  of which transporting (Ambulance / w agreement / Air)',
             'label'),
            (f'=SUMPRODUCT(--(ISNUMBER(SEARCH("Ambulance",F{b0}:F{b1}))))'
             , 'fml', lib.FMT_INT), None, None, None, None, None, None,
            None, None])
    sb.blank()

    # ---------------- Panel C: Nebraska ---------------- #
    ne = rosters['NE']
    sb.banner('Panel C. Nebraska - DHHS licensure roster PARKED (state '
              'page: "temporarily unavailable"); NG911 Rescue/EMS response '
              'areas stand in (modified 2026-03-16)')
    sb.headers(['Item', 'Value / status', '', '', '', '', '', 'Vintage',
                'Basis', 'Note'])
    sb.row([('DHHS licensed EMS services roster', 'label'),
            ('PENDING', 'note'), None, None, None, None, None,
            (acc, 'text'), ('PENDING', 'text'),
            ('Nebraska DHHS "Rosters of Facilities and Services" - EMS '
             'roster would fill this; state page states verbatim: "This '
             'roster is temporarily unavailable. Please call 402-471-0371" '
             '- the license lookup (nebraska.gov/LISSearch) is '
             'reCAPTCHA-gated', 'note')], wrap=True)
    sb.row([('NG911 EMS response-area polygons (statewide layer)', 'label'),
            (977, 'src', lib.FMT_INT), None, None, None, None, None,
            ('2026-03', 'src'), ('GOV', 'text'),
            ('gis.ne.gov Rescue_District_Response_Area FeatureServer',
             'note')])
    sb.row([('Distinct EMS service display names in the layer', 'label'),
            (504, 'src', lib.FMT_INT), None, None, None, None, None,
            ('2026-03', 'src'), ('GOV', 'text'),
            ('a 911 dispatch-boundary registry, NOT the licensure roster; '
             'no service level, no ground/air split, no vehicle counts',
             'note')], wrap=True)
    sb.row([('2023 periodic-inspection list (DHHS OEHS PDF)', 'label'),
            ('~150 services (subset)', 'src'), None, None, None, None,
            None, ('2023', 'src'), ('GOV', 'text'),
            ('inspection-due subset only, carried as corroboration that '
             'the licensure program operates; not a roster', 'note')],
           wrap=True)
    sb.note('The NG911 distinct-name list (504 services) is carried in the '
            'pull artifact (cache key state_ems_rosters, NE.rows) rather '
            'than printed here: it is a dispatch registry and printing it '
            'as a licensure panel would overstate its object. The '
            'workbook\'s NPPES_Registry_NE_IA tab carries the NPPES view '
            'of the same population.')
    sb.blank()

    # ---------------- Panel D: Kansas ---------------- #
    ks = rosters['KS']
    sb.banner('Panel D. Kansas - current KBEMS roster portal-only '
              '(PARKED); KEMSIS "EMS Services Reporting - 2019" list '
              '(as of Jan 31, 2020) stands in')
    sb.headers(['Item', 'Value / status', '', '', '', '', '', 'Vintage',
                'Basis', 'Note'])
    sb.row([('KBEMS current licensed ambulance services roster (with '
             'class)', 'label'),
            ('PENDING', 'note'), None, None, None, None, None,
            (acc, 'text'), ('PENDING', 'text'),
            ('KEMSIS ImageTrend License Management public portal '
             '(kemsis.org/lms/public/portal) would fill this - lookup is '
             'JS-only and the underlying API (api/services/search, '
             'getservicelookupcount, getless) returns HTTP 401 '
             'unauthenticated; hub.kansasgis.org catalog (627 datasets) '
             'has no EMS layer', 'note')], wrap=True)
    sb.row([('Services submitting 2019 records to KEMSIS (parsed names)',
             'label'),
            (len(ks['rows']), 'src', lib.FMT_INT), None, None, None, None,
            None, ('2020-01', 'src'), ('GOV', 'text'),
            ('a REPORTING roster: licensed services that did not submit '
             '2019 records are absent - treat as a floor on licensed '
             'transporting services', 'note')], wrap=True)
    ks_count_row = sb.r
    sb.note('KBEMS service classes (from the KEMSIS public lookup form): '
            'I ground ALS/BLS emergency + non-emergency; II ground BLS '
            'non-emergency only; III ground ALS-only interfacility '
            'critical care; IV restricted-location ground; VI ALS first '
            'response non-transport; VII air (rotor/fixed). The Jan 2020 '
            'reporting list does not carry class per service; the class '
            'dimension is part of the PENDING pull above.')
    sb.headers(['KEMSIS-reporting service (2019)', '', '', '', '', '', '',
                'Vintage', 'Basis', 'Note'])
    d0 = sb.r + 1
    for i, r in enumerate(ks['rows']):
        sb.row([(_clean(r['service_name'], 60), 'src'), None, None, None,
                None, None, None, ('2020-01', 'src'), ('GOV', 'text'),
                ('names as printed in the KBEMS PDF (region grouping in '
                 'source)', 'note') if i == 0 else None])
    d1 = sb.r
    sb.blank()

    # ---------------- Panel E: three universes ---------------- #
    sb.banner('Panel E. Three universes per state: state-licensed services '
              'vs PECOS-enrolled vs Medicare-billing NPIs (finding 46 '
              'lineage, extended)')
    sb.headers(['State', 'Licensed / rostered transporting services',
                'Roster object + vintage',
                'PECOS enrollment records (live)',
                'PECOS distinct suppliers (live)',
                'MUP CY2024 ground-billing NPIs (computed)',
                'MUP CY2024 A0425 renderers (live)',
                'Licensed minus ground billers',
                'Ground billers per licensed', 'Confound (read with row)'])
    e0 = sb.r + 1
    lic_cell = {}
    for s in STATES:
        rn = sb.r + 1
        countif, idx, rend = _pecos_links(s)
        if s == 'MO':
            lic = (f'=B{mo_ground_row}', 'fml', lib.FMT_INT)
            obj = 'DHSS licensed ground ambulance services, 2026-05'
            conf = ('current roster vs CY2024 claims; licenses are per '
                    'service, NPIs per billing entity - one company can '
                    'hold several of either; out-of-state billers excluded')
        elif s == 'IA':
            lic = (f'=B{ia_amb_row}', 'fml', lib.FMT_INT)
            obj = ('Iowa HHS ambulance service LOCATIONS, Jun 2025 '
                   '(programs: 724)')
            conf = ('locations exceed programs; roster counts locations '
                    'with transport capability, claims count billing NPIs; '
                    'volunteer squads often bill via a hospital or not at '
                    'all')
        elif s == 'KS':
            lic = (f'=B{ks_count_row}', 'fml', lib.FMT_INT)
            obj = ('KEMSIS 2019 REPORTING services, Jan 2020 - floor, not '
                   'the licensure roster')
            conf = ('reporting list is itself a floor and 6 years older '
                    'than the claims year; class II/IV/VI services may '
                    'rarely bill Medicare')
        else:
            lic = ('PENDING', 'note')
            obj = ('DHHS roster offline; NG911 registry lists 504 distinct '
                   'response-area services (dispatch object)')
            conf = ('no licensure count to compare: gap and ratio print '
                    'n/a rather than borrowing the dispatch registry')
        sb.row([(s, 'src'), lic, (obj, 'note'),
                (countif, 'link', lib.FMT_INT),
                (idx, 'link', lib.FMT_INT),
                (mup_org[s], 'src', lib.FMT_INT),
                (rend, 'link', lib.FMT_INT),
                (f'=IF(ISNUMBER(B{rn}),B{rn}-F{rn},"n/a")', 'fml',
                 lib.FMT_INT),
                (f'=IF(ISNUMBER(B{rn}),F{rn}/B{rn},"n/a")', 'fml',
                 lib.FMT_PCT1),
                (conf, 'note')], wrap=True)
        lic_cell[s] = rn
    sb.note('Universe definitions: PECOS enrollment records = rows on '
            'PECOS_Registry (an NPI can carry several enrollments); PECOS '
            'distinct suppliers and A0425 renderers = live links to '
            'PECOS_Suppliers_State Panel B; ground-billing NPIs = distinct '
            'CY2024 MUP NPIs with any ground base-code row (org entities; '
            'computed from mup_provider_2024_* caches, suppression makes '
            'this a floor). The licensed-but-never-billing layer (col H) '
            'is measured only where a state roster landed (MO cleanly, IA '
            'on locations, KS on a stale reporting floor).')
    sb.blank()

    sb.banner('Read panel')
    sb.prose('Four states, four different public objects - and that is '
             'the finding. Missouri publishes a clean current directory: '
             '455 licensed ground ambulance services, of which only 177 '
             'distinct NPIs billed Medicare a single ground base code in '
             'CY2024 - a licensed-but-never-billing layer of roughly 278 '
             'services (61% of the licensed universe) made of volunteer '
             'and municipal squads, MA/commercial-only operators, and '
             'services billing under another entity\'s NPI. Iowa\'s '
             'official June 2025 roll-up (724 programs, 502 ambulance '
             'locations, >70% at least partially volunteer) against 195 '
             'billing NPIs tells the same story at similar scale. '
             'Nebraska\'s roster is offline and Kansas\'s sits behind a '
             'portal - both PARKED with the exact URLs tried, both '
             'bounded meanwhile by public floors (504 NG911 dispatch '
             'services; 164 KEMSIS-reporting services). The claims-visible '
             'market is the minority of the licensed market everywhere a '
             'roster landed.')

    mo_ground_n = sum(1 for r in mo['rows'] if r['ground_or_air'] == 'ground')
    facts += [
        {'metric': 'Missouri licensed ground ambulance services (DHSS '
                   'directory)', 'year': 2026, 'value': mo_ground_n,
         'unit': 'services', 'basis': 'GOV', 'tier': 'A',
         'source_keys': ['xb_mo_socrata'],
         'locator': 'data.mo.gov e7p8-a69d full pull, rows updated '
                    '2026-05-14; Panel A roll-up row (live COUNTIF)',
         'lives_on': 'State_EMS_Licensure',
         'cross_check': 'Live COUNTIF over the printed panel equals the '
                        'API row count; air (26) and stretcher van (5) '
                        'carried separately'},
        {'metric': 'Missouri licensed-but-not-Medicare-ground-billing '
                   'services (licensed minus CY2024 ground-billing NPIs)',
         'year': 2024, 'value': mo_ground_n - mup_org['MO'],
         'unit': 'services (unit caveat: licenses vs NPIs)',
         'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['xb_mo_socrata', 'xb_mup24_state'],
         'locator': 'Panel E MO row, col H (live)',
         'lives_on': 'State_EMS_Licensure',
         'cross_check': 'Confound printed in the same row: license and '
                        'NPI are different objects, one company can hold '
                        'several of either; MUP suppression makes the '
                        'biller count a floor, so the gap is a ceiling '
                        'on that basis'},
        {'metric': 'Iowa authorized EMS service programs (official '
                   'roll-up)', 'year': 2025, 'value': 724,
         'unit': 'programs', 'basis': 'GOV', 'tier': 'A',
         'source_keys': ['xb_ia_snapshot25'],
         'locator': 'Iowa HHS EMS Snapshot (June 2025), page 1; Panel B '
                    'roll-up',
         'lives_on': 'State_EMS_Licensure',
         'cross_check': 'Locations (901) split 502 ambulance / 375 '
                        'non-transport / 24 air on the same page; 2013 '
                        'full roster panel shows 411 transporting of 779 '
                        'parsed - same order of magnitude'},
        {'metric': 'Iowa CY2024 ground-billing NPIs (MUP, distinct, '
                   'floor)', 'year': 2024, 'value': mup_org['IA'],
         'unit': 'NPIs', 'basis': 'GOV', 'tier': 'A',
         'source_keys': ['xb_mup24_state'],
         'locator': 'mup_provider_2024_* caches, IA org NPIs with ground '
                    'base rows; Panel E col F',
         'lives_on': 'State_EMS_Licensure',
         'cross_check': 'PECOS_Suppliers_State A0425-renderer count for '
                        'IA prints beside it (live link) and runs higher '
                        'because mileage renderers include air and '
                        'individuals'},
    ]

    findings.append({
        'id_hint': 82,
        'finding': 'The supplier-universe rule (finding 46) gains a fourth '
                   'layer: state licensure. Where a state roster landed, '
                   'the licensed universe dwarfs the Medicare-billing one '
                   '- Missouri licenses 455 ground services but only 177 '
                   'NPIs billed a CY2024 ground base code (a 61% '
                   'licensed-but-never-billing layer), and Iowa\'s 502 '
                   'ambulance locations (724 programs, >70% partially '
                   'volunteer) stand against 195 billing NPIs. Licensure, '
                   'enrollment, billing and dispatch registries are four '
                   'different objects; every market-share denominator must '
                   'name which one it uses.',
        'numbers': "='State_EMS_Licensure'!H" + str(lic_cell['MO']),
        'sources': 'xb_mo_socrata; xb_ia_snapshot25; xb_mup24_state',
        'confidence': 'High for MO (current roster vs same-vintage-adjacent '
                      'claims); medium for IA (locations vs NPIs); KS/NE '
                      'pending their rosters',
        'guardrail': 'Licenses and NPIs are different units - one company '
                     'can hold several of either, and MUP suppression '
                     'plus out-of-state billing blur the edges. The gap '
                     'measures the claims-invisible layer of the licensed '
                     'universe, NOT a count of inactive services.'})

    # ================================================================== #
    # TAB 2: Press_Footprint_Registry
    # ================================================================== #
    sources += [
        {'key': 'xe_press_subject', 'publisher': 'Midwest Medical '
                                                 'Transport Company / MMT '
                                                 'Ambulance and its '
                                                 'investor (via Business '
                                                 'Wire)',
         'document': 'Dated press releases concerning the subject company '
                     '(2022 recapitalization; 2023 CEO appointment)',
         'vintage': '2022-2023',
         'locator': 'URL per row, Panel A; issuer and dateline verified on '
                    'page',
         'url': 'https://www.businesswire.com/news/home/20230405005703/en/'
                'MMT-Ambulance-Appoints-Chris-Ciatto-as-New-CEO',
         'tier': 'B', 'accessed': acc,
         'powers': ['Press_Footprint_Registry']},
        {'key': 'xe_press_participants', 'publisher': 'Issuing '
                                                      'organizations '
                                                      '(own newsrooms and '
                                                      'wire postings)',
         'document': 'Dated public announcements 2020-2026 by resolved '
                     'market participants (Priority Ambulance, Acadian, '
                     'AMR/GMR, Falck, DocGo, Superior Air-Ground, Royal, '
                     'MedSpeed)',
         'vintage': '2020-2026',
         'locator': 'URL per row, Panel A; each row restates only the '
                    'release text, attributed to the issuer',
         'url': 'https://priorityambulance.com/category/news/',
         'tier': 'B', 'accessed': acc,
         'powers': ['Press_Footprint_Registry']},
        {'key': 'xe_wayback_avail', 'publisher': 'Internet Archive',
         'document': 'Wayback Machine availability API - snapshot '
                     'existence/timestamps for the subject company\'s '
                     'domains (midwestmedicaltransport.com, '
                     'midwestmedtrans.com, mmtamb.com), 2014-2026',
         'vintage': 'index as of ' + acc,
         'locator': 'archive.org/wayback/available per domain-year; '
                    'snapshot CONTENT not retrievable from this '
                    'environment (web.archive.org egress-blocked) - those '
                    'rows are PARKED',
         'url': 'https://archive.org/wayback/available?url='
                'midwestmedicaltransport.com&timestamp=20140701',
         'tier': 'B', 'accessed': acc,
         'powers': ['Press_Footprint_Registry']},
        {'key': 'xe_commoncrawl', 'publisher': 'Common Crawl',
         'document': 'CC-MAIN index captures and WARC page records of '
                     'mmtamb.com (2023-2026) and '
                     'midwestmedicaltransport.com (robots.txt only, '
                     '2018-2022), 38 collections sampled 2014-2026',
         'vintage': 'captures 2023-03 to 2026-05',
         'locator': 'index.commoncrawl.org per collection; page HTML '
                    'fetched from data.commoncrawl.org via byte-range; '
                    'claim text quoted verbatim per row',
         'url': 'https://index.commoncrawl.org/',
         'tier': 'B', 'accessed': acc,
         'powers': ['Press_Footprint_Registry']},
    ]

    ws2 = wb.create_sheet('Press_Footprint_Registry')
    sb2 = lib.SheetBuilder(ws2, 10,
                           col_widths=[26, 11, 40, 52, 15, 50, 8, 8, 8, 8],
                           tab_color='FF6A1B9A')
    sb2.title('Press and footprint registry: what issuers announced, and '
              'what the subject company\'s own site claimed over time')
    sb2.subtitle('The question: which dated PUBLIC announcements (market '
                 'entries/exits, acquisitions, publicly announced contract '
                 'awards, leadership changes) exist for the subject '
                 'company and the resolved market participants, 2020-2026 '
                 '- and what did the subject company\'s own public '
                 'website self-claim about its footprint, year by year? '
                 'Sources: issuer newsrooms/wire pages (URL + date per '
                 'row); Internet Archive availability API; Common Crawl '
                 'WARC captures. This tab is a REGISTRY feeding '
                 'Company_Dossier timelines; every row is a PUBLIC-WEB '
                 'claim by its issuer, not a verified event.')
    sb2.note('DATA QUALITY: rows restate release text only - a release '
             'saying two organizations partner is recorded as exactly '
             'that claim by the issuer. Newsroom coverage is uneven '
             '(Falck\'s press host returned 503s, so several known items '
             'are omitted rather than carried undated; the subject '
             'company\'s site has NO press section, so its two rows come '
             'from wire postings). Panel A row counts measure what was '
             'HARVESTED under a 3-8-items-per-org relevance screen, not '
             'issuance volume - so NO per-year count table is printed '
             'for Panel A. Archive panels: Wayback content is '
             'egress-blocked here (rows recorded and PARKED); page-content '
             'rows come from Common Crawl, an independent public archive.')
    sb2.blank()

    sb2.banner('Panel A. Press registry - dated public announcements, '
               '2020-2026 (PUBLIC-WEB; URL + date per row)')
    sb2.headers(['Issuer / org', 'Date', 'Headline (as published)',
                 'What it establishes (issuer claim only)', 'Label',
                 'URL', '', '', '', ''])
    p0 = sb2.r + 1
    for r in sorted(press['rows'], key=lambda x: (x['org'], x['date'])):
        sb2.row([(_clean(r['org'], 40), 'src'),
                 (_clean(r['date']), 'src'),
                 (_clean(r['headline'], 110), 'src'),
                 (_clean(r['what_it_establishes'], 220), 'src'),
                 ('PUBLIC-WEB self-claim', 'text'),
                 (_clean(r['url'], 140), 'src'),
                 None, None, None, None], wrap=True)
    p1 = sb2.r
    sb2.row([('Rows harvested (live)', 'label'),
             (f'=COUNTA(B{p0}:B{p1})', 'fml', lib.FMT_INT),
             None, None, None, None, None, None, None, None])
    sb2.blank()

    sb2.banner('Panel B. Subject-company website self-claim series '
               '(archived captures; self-claims recorded verbatim)')
    sb2.headers(['Capture date', 'Archive', 'Page',
                 'Self-claimed footprint / claim text (verbatim excerpt)',
                 'Enumerated entries', 'States if enumerable', '', '', '',
                 'Note'])
    w0 = sb2.r + 1
    n_states_cell = None
    for r in wayback['rows']:
        claim = r.get('claim_text')
        states = r.get('states_claimed_if_enumerable')
        note = r.get('note')
        # keep the tab readable; full text lives in the pull artifact
        arch = ('Wayback (recorded; content PARKED)'
                if 'Wayback' in r['archive'] else 'Common Crawl WARC')
        rn = sb2.r + 1
        sb2.row([(r['snapshot_date'], 'src'),
                 (arch, 'text'),
                 (_clean(r.get('page'), 46), 'src'),
                 (_clean(claim, 300) if claim else
                  ('(no content retrievable)' if 'Wayback' in r['archive']
                   else '(no footprint language on page)'),
                  'src' if claim else 'note'),
                 (r.get('n_states_claimed'), 'src', lib.FMT_INT)
                 if r.get('n_states_claimed') else None,
                 (', '.join(states), 'src') if states else None,
                 None, None, None,
                 (_clean(note, 220), 'note') if note else None], wrap=True)
        if r.get('n_states_claimed'):
            n_states_cell = rn
    w1 = sb2.r
    sb2.note('Cross-reference: the MEASURED footprint lives on '
             'MMT_Medicare_Book Panel E (states of billing NPIs, CY2024) '
             'and MMT_NPI_Estate today, and on the X-E.5 measured-footprint '
             'tab (MMT_Footprint_Measured) when that block lands - '
             'self-claims on this panel are never substituted for it. '
             'Domain history recorded in the pull artifact: '
             'midwestmedicaltransport.com (captures 2014; robots.txt to '
             '2022), mmtamb.com from 2023; midwestmedtrans.com has ZERO '
             'archive captures and no longer resolves.')
    sb2.blank()

    sb2.banner('Panel C. Countable series: enumerated "Currently Serving" '
               'entries on the subject site, by capture (the only '
               'genuinely countable pattern in this registry)')
    sb2.headers(['Capture', 'Enumerated entries', 'Basis', '', '', '', '',
                 '', '', 'Note'])
    c_rows = [('2023-03-24 homepage', 11, 'PUBLIC-WEB',
               '10 states + Washington DC listed "Currently Serving"; 6 '
               'more "Coming Soon" (CT SC IL IN CO FL)'),
              ('2024-02-24 homepage', 0, 'PUBLIC-WEB',
               'state-by-state section ABSENT from capture; 0 counts '
               'enumerated entries, not operations'),
              ('2025-01-20 homepage', 0, 'PUBLIC-WEB',
               'redesigned site; no state enumeration'),
              ('2026-01-14 homepage', 0, 'PUBLIC-WEB',
               'no state enumeration; Iowa-specific careers page exists '
               'on 2026-05-16 capture')]
    c0 = sb2.r + 1
    for cap, n, basis, note in c_rows:
        sb2.row([(cap, 'src'), (n, 'src', lib.FMT_INT), (basis, 'text'),
                 None, None, None, None, None, None, (note, 'note')],
                wrap=True)
    sb2.note('Read 0 as "the site stopped enumerating", never as "the '
             'company serves zero states" - the 2024-2026 sites still '
             'describe multi-state operations in prose ("operations '
             'spread out across multiple states", 2024-02 partnerships '
             'page). Staffing self-claims moved in the same window: '
             '"4,000+ providers" (2023-03 about-us) to "2,800+ ... '
             'professionals" (2025-05 and 2026-01 about-us), with "500+ '
             'vehicles" claimed 2023-03.')
    sb2.blank()

    sb2.banner('Read panel')
    sb2.prose('Two registries, one discipline: every row is somebody\'s '
              'public claim, dated and linked. The press panel gives '
              'Company_Dossier its timeline spine - the subject company\'s '
              'two wire releases (Jan 2022 recapitalization by Harbour '
              'Point Capital; Apr 2023 CEO appointment) plus 37 dated '
              'participant announcements. The archive panel measures the '
              'subject company\'s own words about itself: in March 2023 '
              'its site enumerated 11 "Currently Serving" entries (10 '
              'states + DC) and claimed 500+ vehicles / 4,000+ providers; '
              'by February 2024 the enumeration was gone from the '
              'homepage, and the 2025-2026 site claims 2,800+ team '
              'members with no state list. That is a measured trajectory '
              'OF CLAIMS - what the company chose to publish - and it is '
              'cross-referenced to, never substituted for, the measured '
              'claims footprint.')

    facts += [
        {'metric': 'Subject-company website "Currently Serving" '
                   'enumerated entries (self-claim), 2023-03-24 capture',
         'year': 2023, 'value': 11,
         'unit': 'entries (10 states + DC)', 'basis': 'PUBLIC-WEB',
         'tier': 'B', 'source_keys': ['xe_commoncrawl'],
         'locator': 'Common Crawl capture 20230324134522 of mmtamb.com '
                    'homepage; Panel B row + Panel C',
         'lives_on': 'Press_Footprint_Registry',
         'cross_check': 'Self-claim, labeled; the CY2024 Medicare-billing '
                        'footprint of the NPI estate '
                        '(MMT_Medicare_Book Panel E) is the measured '
                        'comparator, and 6 further states were claimed '
                        'only as "Coming Soon"'},
        {'metric': 'Subject-company website staffing self-claim, later '
                   'endpoint ("2,800+ ... professionals")',
         'year': 2025, 'value': 2800,
         'unit': 'staff (self-claimed floor)', 'basis': 'PUBLIC-WEB',
         'tier': 'B', 'source_keys': ['xe_commoncrawl'],
         'locator': 'Common Crawl captures 20250522221503 and '
                    '20260114034214 of mmtamb.com/about-us/; Panel B',
         'lives_on': 'Press_Footprint_Registry',
         'cross_check': 'Earlier endpoint on the same site: "4,000+ '
                        'providers" (capture 20230324121017); both are '
                        'issuer self-claims, not payroll data'},
    ]

    findings.append({
        'id_hint': 83,
        'finding': 'The subject company\'s own public site draws a '
                   'measurable self-claim trajectory: March 2023 - 11 '
                   'enumerated "Currently Serving" entries (10 states + '
                   'DC, 6 more "Coming Soon"), 500+ vehicles, 4,000+ '
                   'providers; February 2024 onward - no state '
                   'enumeration at all; 2025-2026 - "2,800+" team '
                   'members. The claims contracted and de-specified over '
                   'three years of captures across two independent public '
                   'archives.',
        'numbers': "='Press_Footprint_Registry'!B" + str(c0),
        'sources': 'xe_commoncrawl; xe_wayback_avail',
        'confidence': 'High that the SITE said these things (verbatim '
                      'WARC captures); no claim about operations',
        'guardrail': 'Self-claims about disclosure, not measurements of '
                     'operations: a site redesign can remove an '
                     'enumeration without any market exit, and staffing '
                     'self-claims are unaudited. Use only as a timeline '
                     'input to Company_Dossier beside the measured '
                     'claims footprint; never quote a self-claimed state '
                     'count as the company\'s footprint.'})

    return {'facts': facts, 'sources': sources, 'excluded': excluded,
            'findings': findings,
            'meta': {'mo_rows': len(mo['rows']), 'ia_rows': len(ia['rows']),
                     'ks_rows': len(ks['rows']),
                     'press_rows': len(press['rows']),
                     'wayback_rows': len(wayback['rows'])}}
