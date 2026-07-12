"""A.8: County_Whitespace_Screens - matched-ratio whitespace screens for the
ten footprint states (NE IA KS MO OH WI VA MN IN KY - provisional pending
E.5), county grain.

HIGH demand (65+ level and growth, chronic prevalence) over LOW supply
(Medicare-billing ambulance providers, users per provider), ranked by ONE
stated primary ratio - 65+ residents per Medicare-billing ambulance provider
- with every other ratio carried as a context column and its confound
printed in-row. No composite index anywhere.
"""

SHEETS = [{'name': 'County_Whitespace_Screens',
           'question': 'Which footprint counties pair heavy and growing 65+ '
                       'demand with the thinnest Medicare-billing ambulance '
                       'supply?'}]

TAB = 'County_Whitespace_Screens'
FP_FIPS = {'31': 'NE', '19': 'IA', '20': 'KS', '29': 'MO', '39': 'OH',
           '55': 'WI', '51': 'VA', '27': 'MN', '18': 'IN', '21': 'KY'}
ST_FIPS = {v: k for k, v in FP_FIPS.items()}
STATE_ORDER = ['NE', 'IA', 'KS', 'MO', 'OH', 'WI', 'VA', 'MN', 'IN', 'KY']
STATE_NAME = {'NE': 'Nebraska', 'IA': 'Iowa', 'KS': 'Kansas',
              'MO': 'Missouri', 'OH': 'Ohio', 'WI': 'Wisconsin',
              'VA': 'Virginia', 'MN': 'Minnesota', 'IN': 'Indiana',
              'KY': 'Kentucky'}
MEASURES = ['kidney', 'diabetes', 'chd', 'stroke']
SCREEN_65 = 2500          # minimum 65+ residents (2024) to enter a ranking
LARGE_65 = 10000          # 'large county' threshold for the headline fact


def _fl(v):
    try:
        return float(str(v).replace(',', '').replace('$', ''))
    except (TypeError, ValueError):
        return None


def _norm_county(name):
    n = (name or '').upper().strip()
    if n.endswith(' COUNTY'):
        n = n[:-7]
    return n.strip()


def _ms_read(wb):
    """Latest MS_County_* tab: scan headers, return tab name plus
    {fips: {'prov','users','benes'}} for the combined service type and
    {fips: prov} for the non-emergency service type."""
    tab = sorted(n for n in wb.sheetnames if n.startswith('MS_County_'))[-1]
    ws = wb[tab]
    hdr_row, cols = None, {}
    for row in ws.iter_rows(min_row=1, max_row=8):
        vals = [(c.value or '') for c in row]
        if any(str(v).strip().lower() == 'service type' for v in vals):
            hdr_row = row[0].row
            for c in row:
                if isinstance(c.value, str):
                    cols[c.value.strip().lower()] = c.column - 1
            break
    if hdr_row is None:
        raise ValueError(f'{tab}: header row not found')
    i_svc = cols['service type']
    i_st = cols['state']
    i_fips = cols['county fips']
    i_prov = cols['providers']
    i_users = cols['users']
    i_bene = cols['ffs beneficiaries']
    all_amb, ne_amb = {}, {}
    for row in ws.iter_rows(min_row=hdr_row + 1, values_only=True):
        svc, st, cf = row[i_svc], row[i_st], row[i_fips]
        if not svc or st not in ST_FIPS or cf is None:
            continue
        fips = ST_FIPS[st] + str(cf).strip().zfill(3)
        if svc == 'Ambulance (Emergency & Non-Emergency)':
            all_amb[fips] = {'prov': int(row[i_prov] or 0),
                             'users': int(row[i_users] or 0),
                             'benes': int(row[i_bene] or 0)}
        elif svc == 'Ambulance (Non-Emergency)':
            ne_amb[fips] = int(row[i_prov] or 0)
    return tab, all_amb, ne_amb


def build(wb, ctx):
    lib = ctx['lib']
    cache = ctx['cache']
    facts, sources, findings = [], [], []

    # ---- demand: county 65+ level 7/1/2020 and 7/1/2024 (Vintage 2024) ----
    cty = {}
    for r in lib.load_cache(cache, 'census_county_age_2024'):
        if r['STATE'] not in FP_FIPS:
            continue
        fips = r['STATE'] + r['COUNTY']
        d = cty.setdefault(fips, {'st': FP_FIPS[r['STATE']],
                                  'name': r['CTYNAME']})
        if r['YEAR'] == '2':
            d['a65_20'] = _fl(r['AGE65PLUS_TOT'])
        elif r['YEAR'] == '6':
            d['a65_24'] = _fl(r['AGE65PLUS_TOT'])

    # ---- chronic prevalence (CDC PLACES, model-based) ----
    prev = {m: {} for m in MEASURES}
    for m in MEASURES:
        for r in lib.load_cache(cache, f'places_county_{m}'):
            prev[m][r['locationid']] = _fl(r.get('data_value'))

    # ---- supply: Market Saturation providers/users (latest MS tab) ----
    ms_tab, ms, ms_ne = _ms_read(wb)

    # ---- supply context: QCEW private ambulance establishments ----
    qcew_key, qcew = None, {}
    for yr in ('2024', '2025', '2023'):
        try:
            rows = lib.load_cache(cache, f'qcew_county_{yr}')
        except FileNotFoundError:
            continue
        qcew_key = f'qcew_county_{yr}'
        for r in rows:
            if r['area_fips'][:2] in FP_FIPS:
                qcew[r['area_fips']] = int(_fl(r['annual_avg_estabs']) or 0)
        break

    # ---- overlay: dialysis facilities per county (county field at source;
    #      the workbook Dialysis_Registry carries the same registry at
    #      state/ZIP grain) ----
    dial = {}
    for r in lib.load_cache(cache, 'dialysis_facilities'):
        st = r.get('state')
        if st in ST_FIPS:
            k = (st, _norm_county(r.get('county')))
            dial[k] = dial.get(k, 0) + 1

    # ---- the screen table ----
    rows = []
    for fips, d in cty.items():
        a65 = d.get('a65_24')
        if not a65 or fips not in ms:
            continue
        prov = ms[fips]['prov']
        rows.append({
            'fips': fips, 'st': d['st'], 'name': d['name'],
            'a65_20': d.get('a65_20'), 'a65_24': a65,
            'prov': prov, 'users': ms[fips]['users'],
            'ne_prov': ms_ne.get(fips),
            'ratio': (a65 / prov) if prov > 0 else a65,
            'dial': dial.get((d['st'], _norm_county(d['name'])), 0),
            'qcew': qcew.get(fips),
            **{m: prev[m].get(fips) for m in MEASURES}})
    screened = sorted((r for r in rows if r['a65_24'] >= SCREEN_65),
                      key=lambda r: -r['ratio'])
    top25 = screened[:25]
    zero5k = sorted((r for r in rows if r['prov'] == 0
                     and r['a65_24'] >= 5000), key=lambda r: -r['a65_24'])
    large = [r for r in screened if r['a65_24'] >= LARGE_65]
    thin_large = large[0]
    metro = max(top25, key=lambda r: r['a65_24'])
    overlay_n = sum(1 for r in top25 if r['dial'] <= 1)

    # ---- sources ----
    acc = ctx['accessed']
    sources += [
        {'key': 'ws_census_county65', 'publisher': 'US Census Bureau',
         'document': 'County Population Estimates by Age, Vintage 2024 '
                     '(CC-EST2024-AGESEX)',
         'vintage': '7/1/2020 and 7/1/2024 estimates',
         'locator': 'AGE65PLUS_TOT, YEAR codes 2 (2020) and 6 (2024), '
                    'footprint state FIPS',
         'supplies': '65+ level and 2020-2024 growth per county (demand '
                     'numerator and the ranking denominator base)',
         'url': 'https://www2.census.gov/programs-surveys/popest/datasets/'
                '2020-2024/counties/asrh/',
         'tier': 'A', 'accessed': acc, 'powers': [TAB]},
        {'key': 'ws_ms_county', 'publisher': 'CMS',
         'document': 'Market Saturation & Utilization State-County, '
                     'Ambulance (Emergency & Non-Emergency), as carried on '
                     f'{ms_tab}',
         'vintage': ms_tab.replace('MS_County_', '') + ' reference period',
         'locator': f'{ms_tab} tab: Providers, Users, FFS beneficiaries '
                    'columns, service type Ambulance (Emergency & '
                    'Non-Emergency) and Ambulance (Non-Emergency)',
         'supplies': 'Medicare-billing ambulance provider counts and user '
                     'counts per county (the supply denominator)',
         'url': 'https://data.cms.gov/summary-statistics-on-use-and-payments/'
                'program-integrity-market-saturation-by-type-of-service',
         'tier': 'A', 'accessed': acc, 'powers': [TAB]},
        {'key': 'ws_places_county', 'publisher': 'CDC',
         'document': 'PLACES: Local Data for Better Health, county data '
                     '(CKD 2021 release; CHD, stroke, diabetes 2023 release)',
         'vintage': '2021 / 2023 releases (BRFSS model-based)',
         'locator': 'measureids KIDNEY, DIABETES, CHD, STROKE; data_value '
                    'crude prevalence % by county FIPS',
         'supplies': 'Chronic-condition prevalence context columns '
                     '(recurring-transport demand proxies)',
         'url': 'https://data.cdc.gov/500-Cities-Places/PLACES-Local-Data-'
                'for-Better-Health-County-Data-20/swc5-untb',
         'tier': 'A', 'accessed': acc, 'powers': [TAB]},
        {'key': 'ws_qcew_amb_county', 'publisher': 'BLS',
         'document': 'QCEW annual averages, NAICS 621910 Ambulance Services, '
                     'private ownership, county grain',
         'vintage': (qcew_key or 'n/a').replace('qcew_county_', ''),
         'locator': 'annual_avg_estabs by area_fips (employment suppressed '
                    'for nearly all footprint counties, so only '
                    'establishment counts are used)',
         'supplies': 'Private ambulance establishment counts (supply '
                     'context column)',
         'url': 'https://data.bls.gov/cew/data/api/2024/a/industry/'
                '621910.csv',
         'tier': 'A', 'accessed': acc, 'powers': [TAB]},
        {'key': 'ws_dialysis_county', 'publisher': 'CMS',
         'document': 'Medicare Dialysis Facilities (Provider Data Catalog); '
                     'same registry as the Dialysis_Registry tab, which '
                     'carries state/ZIP grain - county field read at source',
         'vintage': 'current facility file',
         'locator': 'Facility county + state, name-matched to census county '
                    'names (suffix County stripped)',
         'supplies': 'Dialysis facility count per county (recurring '
                     'ESRD-transport overlay)',
         'url': 'https://data.cms.gov/provider-data/topics/dialysis-'
                'facilities',
         'tier': 'A', 'accessed': acc, 'powers': [TAB]},
    ]

    # ================================================================ sheet
    ws = wb.create_sheet(TAB)
    n = 17
    sb = lib.SheetBuilder(ws, n,
                          col_widths=[22, 5, 9, 9, 8, 8, 11, 8, 9, 9, 7, 7,
                                      7, 7, 8, 8, 36],
                          tab_color='FF4C7C2C')
    sb.title('County whitespace screens: heavy 65+ demand over thin '
             'Medicare-billing ambulance supply, ten footprint states')
    sb.subtitle('The question: which counties in the footprint (NE IA KS MO '
                'OH WI VA MN IN KY - PROVISIONAL pending the E.5 footprint '
                'decision) pair high and growing 65+ demand with the '
                'thinnest Medicare-billing ambulance supply? Sources: Census '
                'county 65+ (2020/2024) x CMS Market Saturation providers/'
                f'users ({ms_tab}) x CDC PLACES prevalence x BLS QCEW '
                'establishments x CMS dialysis facility registry; join key '
                'county FIPS (dialysis by county name). Ranked by ONE '
                'primary ratio - 65+ residents per Medicare-billing '
                'ambulance provider - never a composite. Screen: counties '
                f'with {SCREEN_65:,}+ residents 65+ in 2024.')
    sb.note('DATA QUALITY: Market Saturation counts billing organizations '
            '(org-NPI grain) located in the county - counties served '
            'entirely from out-of-county bases show ZERO providers while '
            'users stay positive, so the primary ratio flags thin LOCAL '
            'billing supply, not absence of service. PLACES values are '
            'model-based small-area estimates (CKD 2021 release, others '
            '2023), not claims. QCEW covers PRIVATE ownership only and '
            'omits fire-based and volunteer EMS; county employment is '
            'suppressed nearly everywhere, so only establishment counts '
            'print. Dialysis counts are county-NAME matched: 0 can be a '
            'match miss, and Virginia independent cities are the weakest '
            'match. Footprint list is provisional pending E.5.')
    sb.blank()

    # ---- Panel A: ratio dictionary, confound in the SAME row ----
    sb.banner('Panel A. The ratios, one per column - each confound printed '
              'in the same row (house rule: no composite index)')
    for name, defn, conf in [
        ('65+ per billing provider (PRIMARY)',
         '65+ residents (2024) / Market Saturation ambulance providers; '
         'zero-provider counties print the 65+ level as a ratio floor',
         'org-NPI grain by billing location: out-of-county service and '
         'metro consolidation both inflate it'),
        ('65+ growth 2020-2024',
         '65+ level 7/1/2024 vs 7/1/2020, live formula',
         'four-year window; small counties move on small absolute changes'),
        ('Users per provider',
         'Market Saturation ambulance users / providers, same county',
         'users counted by residence, providers by location; a high value '
         'can be one big efficient operator, not shortage'),
        ('Providers per 10k 65+',
         'inverse read of the primary ratio, live formula',
         'same org-NPI confound as the primary; floor when suppression '
         'hides small billers'),
        ('Chronic prevalence % (CKD, diabetes, CHD, stroke)',
         'CDC PLACES crude prevalence, adults 18+',
         'model-based estimates, not claims; CKD is the 2021 release, the '
         'other three the 2023 release'),
        ('Dialysis facilities',
         'CMS dialysis registry facilities in the county',
         'name-matched; presence says nothing about ambulance contract '
         'status - it marks recurring-transport demand only'),
        ('QCEW ambulance establishments',
         'BLS QCEW NAICS 621910 private establishments; the '
         'employment-per-10k ratio is SKIPPED because county employment is '
         'suppressed for nearly all footprint counties',
         'private ownership only - public and volunteer EMS invisible; '
         'establishment county is the employer address'),
    ]:
        sb.row([(name, 'label'), None, (defn, 'text')] + [None] * 13
               + [(conf, 'note')])
    sb.blank()

    # ---- per-state ranked tables ----
    hdrs = ['County', 'St', '65+ 2020', '65+ 2024', '65+ growth',
            'Providers', '65+ per provider', 'Users', 'Users per provider',
            'Providers per 10k 65+', 'CKD %', 'Diab %', 'CHD %', 'Stroke %',
            'Dialysis fac.', 'QCEW estabs', 'Note (confound in-row)']

    def county_row(r, first=False, footprint=False):
        rn = sb.r + 1
        notes = []
        if footprint and r['dial'] <= 1:
            notes.append('DIALYSIS OVERLAY: 0-1 local dialysis facilities - '
                         'recurring ESRD transport demand rides on thin '
                         'local supply')
        if r['prov'] == 0:
            notes.append('zero billing providers - ratio column prints the '
                         '65+ level as a floor; positive Users proves '
                         'out-of-county service')
        elif r['a65_24'] >= 50000:
            notes.append('metro-scale county - few but large billing orgs; '
                         'thinness here is consolidation, not absence')
        if first:
            notes.append('ratio confounds per Panel A rows')
        name = (r['name'].replace(' County', '') + ', ' + r['st']
                if footprint else r['name'])
        sb.row([(name, 'src'), (r['st'], 'src'),
                (round(r['a65_20']) if r['a65_20'] else None, 'src',
                 lib.FMT_INT),
                (round(r['a65_24']), 'src', lib.FMT_INT),
                (f'=IF(C{rn}=0,"n/a",D{rn}/C{rn}-1)', 'fml', lib.FMT_PCT1),
                (r['prov'], 'src', lib.FMT_INT),
                (f'=IF(F{rn}=0,D{rn},D{rn}/F{rn})', 'fml', lib.FMT_INT),
                (r['users'], 'src', lib.FMT_INT),
                (f'=IF(F{rn}=0,"n/a",H{rn}/F{rn})', 'fml', lib.FMT_DEC1),
                (f'=IF(D{rn}=0,"n/a",F{rn}/D{rn}*10000)', 'fml',
                 lib.FMT_DEC2),
                (r['kidney'], 'src', lib.FMT_DEC1),
                (r['diabetes'], 'src', lib.FMT_DEC1),
                (r['chd'], 'src', lib.FMT_DEC1),
                (r['stroke'], 'src', lib.FMT_DEC1),
                (r['dial'], 'src', lib.FMT_INT),
                (r['qcew'], 'src', lib.FMT_INT),
                ('; '.join(notes), 'note') if notes else None])
        return rn

    for i, st in enumerate(STATE_ORDER):
        sb.banner(f'Panel {chr(66 + i)}. {STATE_NAME[st]} - top 10 '
                  'whitespace counties by 65+ residents per billing '
                  'provider')
        sb.headers(hdrs)
        st_rows = [r for r in screened if r['st'] == st][:10]
        for j, r in enumerate(st_rows):
            county_row(r, first=(j == 0))
        sb.blank()

    # ---- footprint top-25 + dialysis overlay ----
    sb.banner('Panel L. Footprint cut - top 25 whitespace counties across '
              'all ten states, dialysis overlay flagged in-row')
    sb.headers(hdrs)
    f0 = sb.r + 1
    for j, r in enumerate(top25):
        county_row(r, first=(j == 0), footprint=True)
    fend = sb.r
    ov_rn = sb.r + 1
    sb.row([('Top-25 counties with 0-1 dialysis facilities (overlay count)',
             'label'), None, None, None, None, None, None, None, None, None,
            None, None, None, None,
            (f'=COUNTIF(O{f0}:O{fend},"<=1")', 'fml', lib.FMT_INT), None,
            ('recurring-transport whitespace: ESRD demand must travel or '
             'be served from outside', 'note')])
    sb.blank()

    # ---- screen facts panel ----
    sb.banner('Panel M. Screen facts')
    tf_rn = sb.r + 1
    sb.row([(f'Thinnest-supply LARGE county ({LARGE_65:,}+ 65+): '
             f"{thin_large['name']}, {thin_large['st']}", 'label'),
            None, None, None, None, None,
            (f'=G{f0}' if top25 and top25[0]['fips'] == thin_large['fips']
             else round(thin_large['ratio']),
             'link' if top25 and top25[0]['fips'] == thin_large['fips']
             else 'src', lib.FMT_INT),
            None, None, None, None, None, None, None, None, None,
            ('65+ residents per billing provider; a floor where providers '
             '= 0', 'note')])
    z_rn = sb.r + 1
    sb.row([('Footprint counties with ZERO billing providers and 5,000+ '
             'residents 65+', 'label'), None, None, None, None,
            (len(zero5k), 'src', lib.FMT_INT), None, None, None, None, None,
            None, None, None, None, None,
            ('; '.join(f"{r['name']} {r['st']}" for r in zero5k), 'note')])
    sb.blank()

    sb.banner('Read panel')
    sb.prose('The screen puts a name on whitespace: '
             f"{thin_large['name']}, {thin_large['st']} carries "
             f"{round(thin_large['a65_24']):,} residents 65+ and not one "
             'Medicare-billing ambulance organization based in the county - '
             f"and {len(zero5k)} footprint counties pair zero billing "
             'providers with 5,000+ seniors. The footprint top-25 splits '
             'into two products: rural and exurban counties where the local '
             'billing base is literally absent (demand already travels), '
             f"and metro counties like {metro['name']}, {metro['st']} "
             f"({round(metro['a65_24']):,} seniors over "
             f"{metro['prov']} billing orgs) where the ratio measures "
             'consolidation - few, large incumbents - rather than absence. '
             f'{overlay_n} of the top 25 also have at most one dialysis '
             'facility, so their recurring ESRD transport demand is served '
             'long-haul by definition. What this is NOT: a service-gap map. '
             'Providers are counted where they bill, users where they live; '
             'every flagged county may be served adequately from next door. '
             'It is a market-entry screen - where demand is measured and '
             'the local Medicare billing base is thin - and the footprint '
             'itself stays provisional until E.5.')

    # ---- facts ----
    facts += [
        {'metric': 'Thinnest-supply large county in the footprint: '
                   f"{thin_large['name']}, {thin_large['st']} - 65+ "
                   'residents per Medicare-billing ambulance provider '
                   '(zero providers based in-county; ratio floor = 65+ '
                   'level)',
         'year': 2024, 'value': round(thin_large['ratio']),
         'unit': '65+ residents per billing provider (floor)',
         'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['ws_census_county65', 'ws_ms_county'],
         'locator': f'Panel L rank 1; census 65+ 7/1/2024 x {ms_tab} '
                    'providers',
         'lives_on': TAB,
         'cross_check': f"{ms_tab} shows {thin_large['users']:,} users in "
                        'the county, proving out-of-county service, not '
                        'zero demand'},
        {'metric': 'Footprint counties with zero Medicare-billing ambulance '
                   'providers and 5,000+ residents 65+',
         'year': 2024, 'value': len(zero5k), 'unit': 'counties',
         'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['ws_census_county65', 'ws_ms_county'],
         'locator': 'Panel M row 2; names printed in the same row',
         'lives_on': TAB,
         'cross_check': 'Each of the named counties shows positive Users '
                        f'in {ms_tab} - served from out of county'},
        {'metric': 'Top-25 footprint whitespace counties with 0-1 dialysis '
                   'facilities (recurring-transport overlay)',
         'year': 2025, 'value': overlay_n, 'unit': 'counties',
         'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['ws_dialysis_county', 'ws_ms_county',
                         'ws_census_county65'],
         'locator': 'Panel L overlay COUNTIF row; per-county counts in '
                    'column O',
         'lives_on': TAB,
         'cross_check': 'Dialysis_Registry carries the same registry at '
                        'state/ZIP grain; county attribution is name-'
                        'matched (0 can be a match miss)'},
        {'metric': 'Largest whitespace county by 65+ population (the metro '
                   f"consolidation read): {metro['name']}, {metro['st']}",
         'year': 2024, 'value': round(metro['ratio']),
         'unit': '65+ residents per billing provider',
         'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['ws_census_county65', 'ws_ms_county'],
         'locator': f"Panel L; {round(metro['a65_24']):,} 65+ over "
                    f"{metro['prov']} billing orgs",
         'lives_on': TAB,
         'cross_check': 'Read as consolidation, not absence: users per '
                        'provider prints in the same row'},
    ]

    findings += [
        {'id_hint': 65,
         'finding': 'The whitespace screen names its counties: '
                    f"{thin_large['name']}, {thin_large['st']} "
                    f"({round(thin_large['a65_24']):,} residents 65+, zero "
                    'Medicare-billing ambulance organizations based '
                    'in-county) is the single thinnest-supply large county '
                    f'in the footprint, one of {len(zero5k)} footprint '
                    'counties pairing zero billing providers with 5,000+ '
                    'seniors ('
                    + '; '.join(f"{r['name']} {r['st']}" for r in zero5k)
                    + '). The footprint top-25 splits between absent-base '
                    'rural counties and consolidated metro counties like '
                    f"{metro['name']}, {metro['st']} - two different entry "
                    'theses ranked by the same stated ratio.',
         'numbers': f"='{TAB}'!G{f0}",
         'sources': 'ws_census_county65; ws_ms_county',
         'confidence': 'High on the arithmetic; the ratio itself is a '
                       'screen, not a service-gap measure',
         'guardrail': 'Market Saturation counts billing orgs by location '
                      'and users by residence: zero providers means no '
                      'LOCAL billing base, not no service. Footprint state '
                      'list is provisional pending E.5. Never present the '
                      'ranking as unmet clinical need.'},
        {'id_hint': 66,
         'finding': f'{overlay_n} of the top-25 footprint whitespace '
                    'counties have at most one dialysis facility, so their '
                    'recurring ESRD transport demand - the most schedulable, '
                    'most contractable product in the book - must either '
                    'travel long-haul to out-of-county chairs or be served '
                    'by out-of-county ambulance suppliers. Thin ambulance '
                    'billing supply and thin dialysis supply coincide in '
                    'the same named counties.',
         'numbers': f"='{TAB}'!O{ov_rn}",
         'sources': 'ws_dialysis_county; ws_ms_county; ws_census_county65',
         'confidence': 'Medium-high: facility counts are registry-grade, '
                       'county attribution is name-matched',
         'guardrail': 'Dialysis facility presence says nothing about '
                      'ambulance contract status or payer mix; a zero can '
                      'be a county-name match miss (Virginia independent '
                      'cities weakest). Overlay marks demand geometry, not '
                      'revenue.'},
    ]

    # ---- chart: top-15 footprint counties ----
    lib.add_chart(ws, f'S{f0 - 2}',
                  'Top-15 footprint whitespace counties: 65+ residents per '
                  'Medicare-billing ambulance provider',
                  f"'{TAB}'!$A${f0}:$A${f0 + 14}",
                  [('65+ per billing provider',
                    f"'{TAB}'!$G${f0}:$G${f0 + 14}")],
                  kind='bar', y_fmt='#,##0', width=16.5, height=9.5)

    return {'facts': facts, 'sources': sources, 'excluded': [],
            'findings': findings,
            'meta': {'footprint': STATE_ORDER,
                     'footprint_status': 'provisional pending E.5',
                     'screen_min_65plus': SCREEN_65,
                     'counties_screened': len(screened),
                     'ms_tab': ms_tab}}
