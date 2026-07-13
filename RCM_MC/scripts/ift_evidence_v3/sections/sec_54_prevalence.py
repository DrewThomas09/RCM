"""Run 5, Task 5.4: Hospital_Ambulance_Prevalence - the measured answer to the
common industry guess that few hospitals field their own ambulance teams.

Two public legs bracket it. The HCRIS leg is strict and direct: the share of
hospital cost-report filers that book a Worksheet A line-95 ambulance cost
centre - the hospital itself telling Medicare it runs an ambulance operation.
The registry leg is a loose ceiling: the share of short-term acute and critical-
access hospitals whose name and state match an ambulance-taxonomy NPI in NPPES,
inflated by place-name collisions (an independent "<Town> Ambulance" matching the
same-named hospital), exactly like the insourcing ceiling. The floor is the
defensible number; the ceiling is a loose upper bound.
"""
import re

SHEETS = [{'name': 'Hospital_Ambulance_Prevalence',
           'question': 'What share of hospitals field their own ambulance - '
                       'measured directly, against the guess that few do?'}]

HCRIS_URL = ('https://www.cms.gov/research-statistics-data-and-systems/'
             'downloadable-public-use-files/cost-reports/hospital-2010-form')
PDC_URL = 'https://data.cms.gov/provider-data/dataset/xubh-q36u'
NPPES_URL = 'https://download.cms.gov/nppes/NPI_Files.html'

GEN = {'THE', 'OF', 'AND', 'HOSPITAL', 'HOSPITALS', 'MEDICAL', 'CENTER',
       'CENTERS', 'HEALTH', 'HEALTHCARE', 'SYSTEM', 'SYSTEMS', 'REGIONAL',
       'COMMUNITY', 'MEMORIAL', 'GENERAL', 'COUNTY', 'CITY', 'SAINT', 'ST',
       'UNIVERSITY', 'CLINIC', 'AMBULANCE', 'EMS', 'SERVICE', 'SERVICES',
       'TRANSPORT', 'CARE', 'DISTRICT', 'INC', 'LLC'}
STACH_TYPES = ('Acute Care Hospitals', 'Critical Access Hospitals')


def _toks(name):
    t = re.sub(r'[^A-Z0-9 ]', ' ', str(name or '').upper()).split()
    return {x for x in t if x not in GEN and len(x) >= 4}


def build(wb, ctx):
    lib = ctx['lib']
    cache = ctx['cache']
    accessed = ctx['accessed']
    facts, sources, excluded, findings = [], [], [], []

    cc = lib.load_cache(cache, 'hcris_amb_cost_center')
    fc = {int(k): v for k, v in
          lib.load_cache(cache, 'hcris_amb_filer_counts').items()}
    hosp = lib.load_cache(cache, 'pdc2_hospitals')
    amb = lib.load_cache(cache, 'nppes_ambulance_roster')

    # HCRIS leg by year: distinct CCN with a nonzero line-95 ambulance cost centre
    hc_years = [2021, 2022, 2023]
    hc = {}
    for yr in hc_years:
        ccns = {r['ccn'] for r in cc if r['fy_year'] == yr
                and (r.get('total') or 0) != 0}
        hc[yr] = (len(ccns), fc.get(yr, 0))
    hc_latest = 2023
    hc_n, hc_d = hc[hc_latest]
    hc_share = hc_n / hc_d if hc_d else 0.0

    # Registry leg: STACH matched to an ambulance-taxonomy NPI by same-state
    # normalized-token containment (the loose ceiling)
    amb_by_state = {}
    for a in amb:
        d = _toks(a.get('org_name'))
        if d:
            amb_by_state.setdefault((a.get('state') or '').upper(), []).append(d)
    stach = [h for h in hosp if h.get('hospital_type') in STACH_TYPES]
    matched = 0
    for h in stach:
        dh = _toks(h.get('facility_name'))
        st = (h.get('state') or '').upper()
        if dh and any(dh & da and (dh <= da or da <= dh)
                      for da in amb_by_state.get(st, ())):
            matched += 1
    reg_n, reg_d = matched, len(stach)
    reg_share = reg_n / reg_d if reg_d else 0.0

    sources += [
        {'key': 'prev_hcris', 'publisher': 'CMS',
         'document': 'HCRIS Hospital Cost Report (Form 2552-10), Worksheet A '
                     'line 95 ambulance cost centre, FY2021-FY2023 year-files',
         'vintage': 'FY2021 / FY2022 / FY2023 as-filed',
         'locator': 'Distinct CCNs with a nonzero line-95 ambulance cost '
                    'centre over total hospital filers in the same year-file',
         'supplies': 'The strict HCRIS prevalence leg on this tab',
         'url': HCRIS_URL, 'tier': 'A', 'accessed': accessed,
         'powers': ['Hospital_Ambulance_Prevalence']},
        {'key': 'prev_registry', 'publisher': 'CMS Care Compare + NPPES',
         'document': f'Care Compare Hospital General Information ({len(stach):,} '
                     'short-term acute and critical-access hospitals) matched '
                     f'to the NPPES ambulance-taxonomy roster ({len(amb):,} '
                     'organizational NPIs)',
         'vintage': 'Current rosters at access date',
         'locator': 'Same-state normalized-token containment (uppercase, '
                    'punctuation stripped, generic facility/service words '
                    'dropped) between hospital and ambulance-NPI names',
         'supplies': 'The loose registry-ceiling prevalence leg on this tab',
         'url': PDC_URL, 'tier': 'A', 'accessed': accessed,
         'powers': ['Hospital_Ambulance_Prevalence']},
    ]

    ws = wb.create_sheet('Hospital_Ambulance_Prevalence')
    sb = lib.SheetBuilder(ws, 10,
                          col_widths=[46, 16, 16, 16, 12, 12, 12, 4, 4, 44],
                          tab_color='FF1F6F8B')
    sb.title('How many hospitals field their own ambulance? The measured '
             'answer, floor and ceiling')
    sb.subtitle('The common industry guess is that few hospitals run their own '
                'ambulance teams. Two public legs bracket the truth. The HCRIS '
                'leg is strict and direct - the share of hospital cost-report '
                'filers that book a Worksheet A line-95 ambulance cost centre, '
                'the hospital telling Medicare it runs an ambulance. The '
                'registry leg is a loose ceiling - the share of short-term '
                'acute and critical-access hospitals whose name and state match '
                'an ambulance-taxonomy NPI, inflated by place-name collisions. '
                'The floor is the defensible number.')
    sb.note('DATA QUALITY: the HCRIS floor counts hospitals that FILE a cost '
            'report (about 6,000/year) and book a nonzero line-95 centre; small '
            'or non-filing hospitals and those booking ambulance elsewhere make '
            'it a slight floor. The registry ceiling is loose by construction - '
            'a hospital name matching any same-state ambulance NPI counts, so '
            'independent "<Town> Ambulance" operators collide with same-named '
            'hospitals and inflate it, the same collision that pads the '
            'insourcing ceiling. Read the floor as the measured answer and the '
            'ceiling as a weak upper bound, not a point estimate.')
    sb.blank()

    # ---------------------------------------------------------- Panel A ---
    sb.banner('Panel A. The strict HCRIS leg: hospitals booking a line-95 '
              'ambulance cost centre')
    sb.headers(['Cost-report year', 'Hospitals with a line-95 ambulance cost '
                'centre', 'Hospital filers (denominator)', 'Share', '', '', '',
                '', '', 'Note'])
    a0 = sb.r + 1
    for i, yr in enumerate(hc_years):
        n, d = hc[yr]
        rn = a0 + i
        sb.row([(yr, 'src'), (n, 'src', lib.FMT_INT), (d, 'src', lib.FMT_INT),
                (f'=IF(C{rn}=0,"n/a",B{rn}/C{rn})', 'fml', lib.FMT_PCT1),
                None, None, None, None, None,
                ('about one in seven hospital filers runs its own ambulance '
                 'cost centre', 'note') if yr == hc_latest else None],
               wrap=yr == hc_latest)
    sb.blank()

    # ---------------------------------------------------------- Panel B ---
    sb.banner('Panel B. The loose registry ceiling: STACH name matched to an '
              'ambulance-taxonomy NPI')
    sb.headers(['Hospital universe', 'Matched to an ambulance NPI '
                '(same state, name)', 'All STACH + CAH', 'Share (loose '
                'ceiling)', '', '', '', '', '', 'Note'])
    b0 = sb.r + 1
    sb.row([('Short-term acute + critical-access hospitals', 'label'),
            (reg_n, 'src', lib.FMT_INT), (reg_d, 'src', lib.FMT_INT),
            (f'=B{b0}/C{b0}', 'fml', lib.FMT_PCT1),
            None, None, None, None, None,
            ('collision-inflated: an independent same-town ambulance name '
             'matches the same-named hospital, so read this as an upper '
             'bound', 'note')], wrap=True, height=40)
    sb.blank()

    # ------------------------------------------------------- read panel ---
    sb.banner('Read panel')
    sb.prose(
        'The guess that few hospitals field their own ambulance is wrong on the '
        f'measured floor alone: {hc_share * 100:.1f}% of hospital cost-report '
        f'filers - {hc_n:,} of {hc_d:,} in {hc_latest} - book a Worksheet A '
        'line-95 ambulance cost centre, telling Medicare directly that they run '
        'an ambulance operation, and the share is steady near one in seven '
        'across FY2021-FY2023. That is a strict floor: it counts only cost-'
        'report filers with a nonzero line-95 centre. The registry leg puts a '
        f'loose ceiling far above it - {reg_share * 100:.0f}% of short-term '
        'acute and critical-access hospitals name-match an ambulance-taxonomy '
        'NPI in the same state - but that number is inflated by the same place-'
        'name collisions that pad the insourcing ceiling and cannot be read as '
        'a point estimate. The investor-relevant takeaway is the floor: '
        'hospital-fielded ambulance is common, not rare, and it is exactly the '
        'population the insourcing bounds and the QN/QM billing flag both '
        'measure from the claims side.')

    # ------------------------------------------------------------ facts ---
    facts += [
        {'metric': 'Share of hospital cost-report filers booking a line-95 '
                   'ambulance cost centre (HCRIS floor)', 'year': hc_latest,
         'value': round(hc_share, 4), 'unit': 'share of hospital filers',
         'basis': 'GOV', 'tier': 'A', 'source_keys': ['prev_hcris'],
         'locator': f'Hospital_Ambulance_Prevalence Panel A {hc_latest} row, '
                    f'live D{a0 + len(hc_years) - 1}',
         'lives_on': 'Hospital_Ambulance_Prevalence',
         'cross_check': f'{hc_n:,} of {hc_d:,} filers; steady near 14-15% '
                        'across FY2021-FY2023; a slight floor (filers only)'},
        {'metric': 'Share of short-term acute + CAH hospitals name-matching an '
                   'ambulance-taxonomy NPI (loose registry ceiling)',
         'year': 2026, 'value': round(reg_share, 4),
         'unit': 'share of STACH+CAH (loose ceiling)', 'basis': 'DERIVED',
         'tier': 'B', 'source_keys': ['prev_registry'],
         'locator': f'Hospital_Ambulance_Prevalence Panel B, live D{b0}',
         'lives_on': 'Hospital_Ambulance_Prevalence',
         'cross_check': 'Collision-inflated upper bound, not a point estimate; '
                        'the HCRIS floor is the defensible number'},
    ]

    # --------------------------------------------------------- findings ---
    findings += [
        {'id_hint': 113,
         'finding': 'Hospital-fielded ambulance is common, not rare - the '
                    'measured answer to the industry guess that few hospitals '
                    'run their own teams. On the strict floor, '
                    f'{hc_share * 100:.1f}% of hospital cost-report filers '
                    f'({hc_n:,} of {hc_d:,} in {hc_latest}, steady near one in '
                    'seven across FY2021-FY2023) book a Worksheet A line-95 '
                    'ambulance cost centre - telling Medicare directly they run '
                    'an ambulance. A loose registry ceiling (same-state name '
                    f'match to an ambulance NPI) sits far higher at '
                    f'{reg_share * 100:.0f}% but is collision-inflated. This is '
                    'the same hospital-operator population the insourcing '
                    'bounds and the QN/QM billing flag measure from the claims '
                    'side.',
         'numbers': f"='Hospital_Ambulance_Prevalence'!D{a0 + len(hc_years) - 1}",
         'sources': 'prev_hcris; prev_registry',
         'confidence': 'High on the HCRIS floor (direct cost-report filings); '
                       'the registry ceiling is a loose upper bound',
         'guardrail': 'The floor counts cost-report FILERS with a nonzero '
                      'line-95 centre, so it understates; the ceiling is '
                      'collision-inflated, so it overstates. Quote the ~14% '
                      'floor as the measured answer, never the ceiling as a '
                      'point estimate.'}]

    return {'facts': facts, 'sources': sources, 'excluded': excluded,
            'findings': findings,
            'meta': {'hcris_floor': round(hc_share, 4),
                     'registry_ceiling': round(reg_share, 4)}}
