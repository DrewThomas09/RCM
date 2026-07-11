"""v3.2 raw-granularity tabs: the provider-level Medicare ambulance registry,
hospital->ZIP transfer corridors, county age and chronic-disease bases, the
quarterly QCEW series, the HCRIS hospital panel, and the OIG ambulance
exclusion registry. Every value is a dataset extraction (blue, Tier A) or a
live formula; no modeled numbers.
"""
import csv
import gzip
import json
import os

CACHE_DIR = os.environ.get(
    'IFT_V3_CACHE',
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 'ift_v3_cache'))
HCRIS_GZ = '/home/user/RCM/RCM_MC/rcm_mc/data/hcris.csv.gz'

AMB_CODES = ['A0425', 'A0426', 'A0427', 'A0428', 'A0429', 'A0430', 'A0431',
             'A0432', 'A0433', 'A0434', 'A0435', 'A0436']
CODE_LABEL = {
    'A0425': 'Ground mileage', 'A0426': 'ALS1 non-emergency', 'A0427': 'ALS1 emergency',
    'A0428': 'BLS non-emergency', 'A0429': 'BLS emergency', 'A0430': 'Fixed-wing air',
    'A0431': 'Rotary-wing air', 'A0432': 'Paramedic intercept', 'A0433': 'ALS2',
    'A0434': 'Specialty care transport', 'A0435': 'Fixed-wing mileage',
    'A0436': 'Rotary mileage'}
PLACES_MEASURES = ['kidney', 'chd', 'stroke', 'diabetes', 'bphigh', 'copd']


def _have(key):
    p = os.path.join(CACHE_DIR, key + '.json')
    return os.path.exists(p) or os.path.exists(p + '.gz')


def _load(key):
    p = os.path.join(CACHE_DIR, key + '.json')
    if os.path.exists(p):
        return json.load(open(p))
    with gzip.open(p + '.gz', 'rt') as f:
        return json.load(f)


def _f(v):
    if v in (None, '', '*', '#', '**', 'N/A'):
        return None
    try:
        return float(str(v).replace(',', '').replace('$', ''))
    except (TypeError, ValueError):
        return None


def _i(v):
    x = _f(v)
    return int(x) if x is not None and x == int(x) else x


MUP_PROV_YEARS = [y for y in ('2013', '2019', '2024')
                  if _have(f'mup_provider_{y}_A0428')]
QCEW_QTRS = [(y, q) for y in range(2014, 2026) for q in (1, 2, 3, 4)
             if _have(f'qcew_q_{y}q{q}')]

SHEETS = (
    [{'name': f'MUP_Providers_{y}', 'tab_color': 'FF1F6F8B'} for y in MUP_PROV_YEARS]
    + ([{'name': 'HSA_Corridors', 'tab_color': 'FF00294C'}]
       if _have('hsa_2025_corridors_top15') else [])
    + ([{'name': 'County_Age_65plus', 'tab_color': 'FF7A5195'}]
       if _have('census_county_age_2024') else [])
    + ([{'name': 'PLACES_County_Chronic', 'tab_color': 'FF7A5195'}]
       if _have('places_county_kidney') else [])
    + ([{'name': 'QCEW_Quarterly', 'tab_color': 'FF1F6F8B'}] if QCEW_QTRS else [])
    + ([{'name': 'HCRIS_Hospital_Panel', 'tab_color': 'FF00294C'}]
       if os.path.exists(HCRIS_GZ) else [])
    + ([{'name': 'LEIE_Ambulance_Exclusions', 'tab_color': 'FF00294C'}]
       if _have('leie_ambulance') else [])
)


def build(wb, ctx):
    lib = ctx['lib']
    facts, sources, excluded = [], [], []

    # ── MUP_Providers_{year} ────────────────────────────────────────────────
    if MUP_PROV_YEARS:
        sources.append(
            {'key': 'mup_provider_grain', 'publisher': 'CMS',
             'document': 'Medicare Physician & Other Practitioners - by Provider '
                         'and Service',
             'vintage': f'Data years {" and ".join(MUP_PROV_YEARS)}',
             'locator': 'Ambulance HCPCS A0425-A0436, one row per rendering NPI x '
                        'code x place of service: beneficiaries, services, average '
                        'submitted/allowed/paid',
             'supplies': 'The most granular public Medicare ambulance record: '
                         'every billing organization by name and NPI with its '
                         'volumes and realized prices',
             'url': 'https://data.cms.gov/provider-summary-by-type-of-service/'
                    'medicare-physician-other-practitioners/'
                    'medicare-physician-other-practitioners-by-provider-and-service',
             'tier': 'A', 'accessed': '11 Jul 2026',
             'powers': [f'MUP_Providers_{y}' for y in MUP_PROV_YEARS]})
    for yr in MUP_PROV_YEARS:
        rows = []
        for code in AMB_CODES:
            try:
                rows += _load(f'mup_provider_{yr}_{code}')
            except FileNotFoundError:
                continue
        rows.sort(key=lambda r: ((r.get('Rndrng_Prvdr_State_Abrvtn') or ''),
                                 (r.get('Rndrng_Prvdr_Last_Org_Name') or ''),
                                 (r.get('HCPCS_Cd') or '')))
        ws = wb.create_sheet(f'MUP_Providers_{yr}')
        sb = lib.SheetBuilder(ws, 14,
                              col_widths=[12, 40, 14, 20, 6, 9, 6, 10, 11, 12,
                                          12, 12, 12, 12],
                              tab_color='FF1F6F8B')
        sb.title(f'Every Medicare ambulance biller, by NPI: provider-grain '
                 f'utilization and price, {yr} ({len(rows):,} rows)')
        sb.subtitle('The question: who bills Medicare for ambulance transport, '
                    'organization by organization, and at what volume and realized '
                    'price? One row per rendering NPI x HCPCS x place of service - '
                    'the most granular public Medicare ambulance record that '
                    'exists. Source: CMS MUP by Provider and Service (final-action; '
                    'pulled 11 Jul 2026, Pull_Manifest). NPIs with 10 or fewer '
                    'beneficiaries on a code are suppressed at source: every count '
                    'is a floor, and small rural suppliers are undercounted. '
                    'Join keys: NPI to PECOS_Registry and NPPES_Registry_NE_IA.')
        sb.blank()
        sb.headers(['NPI', 'Organization / last name', 'First name', 'City',
                    'State', 'HCPCS', 'POS', 'Level of service', 'Beneficiaries',
                    'Services', 'Bene-day services', 'Avg submitted $',
                    'Avg allowed $', 'Avg paid $'])
        for r in rows:
            sb.row([(r.get('Rndrng_NPI'), 'src'),
                    (r.get('Rndrng_Prvdr_Last_Org_Name'), 'src'),
                    (r.get('Rndrng_Prvdr_First_Name'), 'src'),
                    (r.get('Rndrng_Prvdr_City'), 'src'),
                    (r.get('Rndrng_Prvdr_State_Abrvtn'), 'src'),
                    (r.get('HCPCS_Cd'), 'src'), (r.get('Place_Of_Srvc'), 'src'),
                    CODE_LABEL.get(r.get('HCPCS_Cd'), ''),
                    (_i(r.get('Tot_Benes')), 'src', lib.FMT_INT),
                    (_f(r.get('Tot_Srvcs')), 'src', lib.FMT_INT),
                    (_f(r.get('Tot_Bene_Day_Srvcs')), 'src', lib.FMT_INT),
                    (_f(r.get('Avg_Sbmtd_Chrg')), 'src', lib.FMT_USD2),
                    (_f(r.get('Avg_Mdcr_Alowd_Amt')), 'src', lib.FMT_USD2),
                    (_f(r.get('Avg_Mdcr_Pymt_Amt')), 'src', lib.FMT_USD2)])
        npis = len({r.get('Rndrng_NPI') for r in rows})
        facts.append(
            {'metric': f'Distinct NPIs billing Medicare ambulance codes, {yr} '
                       '(provider-grain, floor)',
             'year': int(yr), 'value': npis, 'unit': 'NPIs', 'basis': 'GOV',
             'tier': 'A', 'source_keys': ['mup_provider_grain'],
             'locator': f'MUP by Provider & Service {yr}, distinct Rndrng_NPI over '
                        'A0425-A0436 rows',
             'lives_on': f'MUP_Providers_{yr}',
             'cross_check': 'A floor (suppression); compare Supplier_Landscape '
                            '8,721 billing NPIs (MUP-geo basis) and PECOS 10,465 '
                            'enrolled - three floors of the same universe'})

    # ── HSA_Corridors ───────────────────────────────────────────────────────
    if _have('hsa_2025_corridors_top15'):
        rows = _load('hsa_2025_corridors_top15')
        sources.append(
            {'key': 'hsa_corridors_src', 'publisher': 'CMS',
             'document': 'Hospital Service Area (hospital x ZIP corridor detail)',
             'vintage': 'Latest published year (see Pull_Manifest)',
             'locator': 'Per hospital: top 10 ZIP codes of origin ranked by total '
                        'cases, with cases, days, charges',
             'supplies': 'The transfer-corridor grain: where each hospital\'s '
                         'inpatients actually come from',
             'url': 'https://data.cms.gov/summary-statistics-on-use-and-payments/'
                    'medicare-service-area-reports/hospital-service-area',
             'tier': 'A', 'accessed': '11 Jul 2026', 'powers': ['HSA_Corridors']})
        ws = wb.create_sheet('HSA_Corridors')
        sb = lib.SheetBuilder(ws, 7, col_widths=[14, 7, 10, 12, 14, 16, 30],
                              tab_color='FF00294C')
        sb.title(f'Hospital catchment corridors: top-15 origin ZIPs per hospital '
                 f'({len(rows):,} rows)')
        sb.subtitle('The question: for every hospital, which ZIP codes feed its '
                    'inpatient volume - the corridor grain under any transfer-'
                    'lane claim? CMS Hospital Service Area, every hospital\'s ZIP '
                    'rows ranked by total cases with the top 10 kept (full ranking '
                    'method on Pull_Manifest). Suppressed hospital-ZIP cells are '
                    'absent at source: floors. Join CCN to Hosp_Registry and '
                    'HSA_Hospital_Catchment; ZIP rolls up to CBSA via '
                    'CBSA_Crosswalk_Reference.')
        sb.blank()
        sb.headers(['Provider (CCN)', 'Rank', 'Origin ZIP', 'Total cases',
                    'Total days', 'Total charges $', ''])
        for r in rows:
            sb.row([(r['provider_id'], 'src'), (r['rank'], 'src', lib.FMT_INT),
                    (r['zip'], 'src'), (r['cases'], 'src', lib.FMT_INT),
                    (r['days'], 'src', lib.FMT_INT),
                    (r['charges'], 'src', lib.FMT_USD), None])
        facts.append(
            {'metric': 'Hospital-ZIP corridor rows carried (top-15 per hospital)',
             'year': 2025, 'value': len(rows), 'unit': 'rows', 'basis': 'GOV',
             'tier': 'A', 'source_keys': ['hsa_corridors_src'],
             'locator': 'HSA latest year, per-hospital top-15 ZIPs by cases',
             'lives_on': 'HSA_Corridors',
             'cross_check': 'Per-hospital totals reconcile to '
                            'HSA_Hospital_Catchment (same pull family)'})

    # ── County_Age_65plus ───────────────────────────────────────────────────
    if _have('census_county_age_2024'):
        raw = _load('census_county_age_2024')
        by_cty = {}
        for r in raw:
            k = (r['STNAME'], r['CTYNAME'], r['STATE'], r['COUNTY'])
            by_cty.setdefault(k, {})[r['YEAR']] = r
        sources.append(
            {'key': 'census_county_age', 'publisher': 'U.S. Census Bureau',
             'document': 'Vintage 2024 County Population Estimates by Age and Sex '
                         '(CC-EST2024-AGESEX)',
             'vintage': 'July 2020 through July 2024 estimate rows',
             'locator': 'Per county: total population, 65+, 85+, median age',
             'supplies': 'The county-grain age-demand base - the denominator for '
                         'the county supply and whitespace layers',
             'url': CENSUS_CTY_URL,
             'tier': 'A', 'accessed': '11 Jul 2026',
             'powers': ['County_Age_65plus']})
        ws = wb.create_sheet('County_Age_65plus')
        sb = lib.SheetBuilder(ws, 14,
                              col_widths=[16, 26, 6, 12, 11, 11, 11, 11, 11,
                                          10, 10, 11, 11, 10],
                              tab_color='FF7A5195')
        sb.title(f'The 65-plus base, county by county ({len(by_cty):,} counties, '
                 'annual 2020-2024)')
        sb.subtitle('The question: where, at county grain, is the age base that '
                    'generates transport demand - and how fast is each county '
                    'aging? Census Vintage 2024 county estimates (measured, not '
                    'projected; pulled 11 Jul 2026). FIPS joins to QCEW_County_*, '
                    'MS_County_* and CBSA_Crosswalk_Reference. State roll-up: '
                    'State_Age_65plus.')
        sb.blank()
        sb.headers(['State', 'County', 'FIPS', 'Population 2024', '65+ 2020',
                    '65+ 2021', '65+ 2022', '65+ 2023', '65+ 2024',
                    '65+ share 2024', '65+ CAGR 2020-2024', '85+ 2020',
                    '85+ 2024', 'Median age 2024'])
        for (stname, ctyname, st, cty), yrs in sorted(by_cty.items()):
            r20, r24 = yrs.get('2'), yrs.get('6')
            if not (r20 and r24):
                continue
            rn = sb.r + 1
            mid = [(_i(yrs[c]['AGE65PLUS_TOT']), 'src', lib.FMT_INT)
                   if c in yrs else None for c in ('3', '4', '5')]
            sb.row([(stname, 'src'), (ctyname, 'src'),
                    (st.zfill(2) + cty.zfill(3), 'src'),
                    (_i(r24['POPESTIMATE']), 'src', lib.FMT_INT),
                    (_i(r20['AGE65PLUS_TOT']), 'src', lib.FMT_INT)]
                   + mid +
                   [(_i(r24['AGE65PLUS_TOT']), 'src', lib.FMT_INT),
                    (f'=IF(D{rn}=0,"n/a",I{rn}/D{rn})', 'fml', lib.FMT_PCT1),
                    (f'=IF(E{rn}=0,"n/a",(I{rn}/E{rn})^(1/4)-1)', 'fml',
                     lib.FMT_PCT2),
                    (_i(r20['AGE85PLUS_TOT']), 'src', lib.FMT_INT),
                    (_i(r24['AGE85PLUS_TOT']), 'src', lib.FMT_INT),
                    (_f(r24['MEDIAN_AGE_TOT']), 'src', lib.FMT_DEC1)])
        facts.append(
            {'metric': 'Counties with measured 65+ base carried', 'year': 2024,
             'value': len(by_cty), 'unit': 'counties', 'basis': 'GOV', 'tier': 'A',
             'source_keys': ['census_county_age'],
             'locator': 'CC-EST2024-AGESEX, YEAR codes 2 and 6',
             'lives_on': 'County_Age_65plus',
             'cross_check': 'County 65+ sums reconcile to State_Age_65plus state '
                            'rows (same vintage, civilian-vs-resident definitions '
                            'stated)'})

    # ── PLACES_County_Chronic ───────────────────────────────────────────────
    if _have('places_county_kidney'):
        sources.append(
            {'key': 'cdc_places_county', 'publisher': 'CDC',
             'document': 'PLACES: Local Data for Better Health, County Data '
                         '(model-based small-area estimates)',
             'vintage': 'Latest CDC release (year on each row)',
             'locator': 'Crude prevalence, measures KIDNEY (CKD), CHD, STROKE, '
                        'DIABETES, all US counties',
             'supplies': 'The county-grain chronic-disease demand layer behind '
                         'dialysis and cardiac/stroke transfer volumes',
             'url': 'https://data.cdc.gov/resource/swc5-untb.json',
             'tier': 'A', 'accessed': '11 Jul 2026',
             'powers': ['PLACES_County_Chronic']})
        ws = wb.create_sheet('PLACES_County_Chronic')
        sb = lib.SheetBuilder(ws, 8, col_widths=[8, 7, 16, 24, 12, 34, 12, 13],
                              tab_color='FF7A5195')
        n_rows = 0
        sb.title('Chronic-disease prevalence by county: CKD, CHD, stroke, diabetes')
        sb.subtitle('The question: where do the chronic conditions that generate '
                    'recurring and acute transfers concentrate, county by county? '
                    'CDC PLACES county data, crude prevalence (pulled 11 Jul '
                    '2026). HONESTY NOTE: PLACES values are CDC-published MODEL-'
                    'BASED small-area estimates (BRFSS + Census), carried here as '
                    'the government\'s official county statistics with that '
                    'methodology stated - they are not claims counts and must '
                    'never be multiplied into volumes. Release vintages differ by measure (CKD from the 2023 county release; the year column states each row vintage). FIPS joins to '
                    'County_Age_65plus and MS_County_*.')
        sb.blank()
        sb.headers(['Year', 'State', 'County FIPS', 'County', 'Measure',
                    'Measure (full)', 'Crude prevalence %', 'County population'])
        for m in PLACES_MEASURES:
            try:
                rows = _load(f'places_county_{m}')
            except FileNotFoundError:
                continue
            for r in sorted(rows, key=lambda x: (x.get('stateabbr') or '',
                                                 x.get('locationname') or '')):
                sb.row([(r.get('year'), 'src'), (r.get('stateabbr'), 'src'),
                        (r.get('locationid'), 'src'), (r.get('locationname'), 'src'),
                        (r.get('measureid'), 'src'), r.get('measure'),
                        (_f(r.get('data_value')), 'src', lib.FMT_DEC1),
                        (_i(r.get('totalpopulation')), 'src', lib.FMT_INT)])
                n_rows += 1
        facts.append(
            {'metric': 'County chronic-prevalence rows (4 measures)', 'year': 2024,
             'value': n_rows, 'unit': 'rows', 'basis': 'GOV', 'tier': 'A',
             'source_keys': ['cdc_places_county'],
             'locator': 'PLACES county, KIDNEY/CHD/STROKE/DIABETES, CrdPrv',
             'lives_on': 'PLACES_County_Chronic',
             'cross_check': 'Model-based estimates (stated); the ESRD claims '
                            'denominator on Enrollment_ESRD_State is the '
                            'measured companion'})

    # ── QCEW_Quarterly ──────────────────────────────────────────────────────
    if QCEW_QTRS:
        sources.append(
            {'key': 'qcew_quarterly', 'publisher': 'BLS',
             'document': 'QCEW NAICS 621910, quarterly slices',
             'vintage': f'{QCEW_QTRS[0][0]}Q{QCEW_QTRS[0][1]} - '
                        f'{QCEW_QTRS[-1][0]}Q{QCEW_QTRS[-1][1]}',
             'locator': 'US000 + statewide rows: establishments, three monthly '
                        'employment levels, quarterly wages, average weekly wage',
             'supplies': 'The quarterly pulse of the ambulance industry labor '
                         'base - recency and seasonality the annual series '
                         'cannot show',
             'url': 'https://www.bls.gov/cew/downloadable-data-files.htm',
             'tier': 'A', 'accessed': '11 Jul 2026', 'powers': ['QCEW_Quarterly']})
        ws = wb.create_sheet('QCEW_Quarterly')
        sb = lib.SheetBuilder(ws, 10,
                              col_widths=[9, 5, 10, 20, 12, 12, 12, 12, 15, 13],
                              tab_color='FF1F6F8B')
        sb.title('Ambulance industry, quarterly: QCEW 621910, every quarter '
                 f'{QCEW_QTRS[0][0]}-{QCEW_QTRS[-1][0]}')
        sb.subtitle('The question: what is the quarterly pulse of the ambulance '
                    'employer base - seasonality, the COVID shock, and the most '
                    'recent quarters the annual files cannot show? BLS QCEW '
                    'quarterly slices, national and statewide rows, private and '
                    'government ownership (pulled 11 Jul 2026). Annual-average '
                    'series: QCEW_EMS_Employment; county grain: QCEW_County_*.')
        sb.blank()
        sb.headers(['Year', 'Qtr', 'Area FIPS', 'Ownership', 'Establishments',
                    'Employment M1', 'Employment M2', 'Employment M3',
                    'Total quarterly wages $', 'Avg weekly wage $'])
        OWN = {'1': 'Federal government', '2': 'State government',
               '3': 'Local government', '5': 'Private'}
        n = 0
        for yr, q in QCEW_QTRS:
            for r in sorted(_load(f'qcew_q_{yr}q{q}'),
                            key=lambda x: (x['area_fips'], x['own_code'])):
                sb.row([(yr, 'src'), (q, 'src'), (r['area_fips'], 'src'),
                        OWN.get(r['own_code'], r['own_code']),
                        (_f(r.get('qtrly_estabs')), 'src', lib.FMT_INT),
                        (_f(r.get('month1_emplvl')), 'src', lib.FMT_INT),
                        (_f(r.get('month2_emplvl')), 'src', lib.FMT_INT),
                        (_f(r.get('month3_emplvl')), 'src', lib.FMT_INT),
                        (_f(r.get('total_qtrly_wages')), 'src', lib.FMT_USD),
                        (_f(r.get('avg_wkly_wage')), 'src', lib.FMT_USD)])
                n += 1
        facts.append(
            {'metric': 'Quarterly QCEW rows carried', 'year': '2014-2025',
             'value': n, 'unit': 'rows', 'basis': 'GOV', 'tier': 'A',
             'source_keys': ['qcew_quarterly'],
             'locator': 'QCEW 621910 quarterly, US000 + statewide',
             'lives_on': 'QCEW_Quarterly',
             'cross_check': 'Annual averages on QCEW_EMS_Employment are the '
                            'same program aggregated by BLS'})

    # ── HCRIS_Hospital_Panel ────────────────────────────────────────────────
    if os.path.exists(HCRIS_GZ):
        with gzip.open(HCRIS_GZ, 'rt') as f:
            rdr = csv.DictReader(f)
            hcris = list(rdr)
        cols = list(hcris[0].keys()) if hcris else []
        keep = [c for c in ('ccn', 'name', 'city', 'state', 'county',
                            'fiscal_year', 'beds', 'bed_days_available',
                            'inpatient_days', 'medicare_days', 'discharges',
                            'medicare_discharges') if c in cols]
        sources.append(
            {'key': 'hcris_panel', 'publisher': 'CMS (HCRIS)',
             'document': 'Hospital Cost Report Information System - hospital '
                         'panel (vendored extract in-repo)',
             'vintage': 'Fiscal years 2020-2022',
             'locator': 'Per hospital-year: CCN, name, location, beds, bed days '
                        'available, utilization days/discharges columns as '
                        'extracted',
             'supplies': 'The hospital capacity/occupancy panel behind the '
                         'transfer-demand engine (occupancy pressure drives '
                         'load-balancing transfers)',
             'url': 'repo: RCM_MC/rcm_mc/data/hcris.csv.gz (CMS HCRIS cost '
                    'reports, data.cms.gov/hospital-cost-report)',
             'tier': 'A', 'accessed': '11 Jul 2026',
             'powers': ['HCRIS_Hospital_Panel']})
        ws = wb.create_sheet('HCRIS_Hospital_Panel')
        widths = [10, 38, 16, 6, 16, 8] + [12] * (len(keep) - 6)
        sb = lib.SheetBuilder(ws, len(keep), col_widths=widths,
                              tab_color='FF00294C')
        sb.title(f'Hospital cost-report panel: capacity and utilization, '
                 f'FY2020-2022 ({len(hcris):,} hospital-years)')
        sb.subtitle('The question: hospital by hospital, what capacity exists and '
                    'how full is it - the occupancy pressure that drives load-'
                    'balancing transfers? CMS HCRIS cost reports (vendored '
                    'extract; source dataset on data.cms.gov). Cost-report '
                    'fiscal years differ by hospital; utilization columns are '
                    'as filed by the hospital and unaudited (MedPAC\'s GADCS '
                    'caution on self-reported cost data applies to cost fields '
                    'generally). Join CCN to Hosp_Registry, HSA_Corridors.')
        sb.blank()
        sb.headers([c.replace('_', ' ') for c in keep])
        num_cols = {'beds', 'bed_days_available', 'inpatient_days',
                    'medicare_days', 'discharges', 'medicare_discharges'}
        for r in sorted(hcris, key=lambda x: (x.get('state') or '',
                                              x.get('name') or '',
                                              x.get('fiscal_year') or '')):
            sb.row([((_f(r.get(c)), 'src', lib.FMT_INT) if c in num_cols
                     else (r.get(c), 'src')) for c in keep])
        facts.append(
            {'metric': 'HCRIS hospital-year rows (FY2020-2022)', 'year': '2020-2022',
             'value': len(hcris), 'unit': 'hospital-years', 'basis': 'GOV',
             'tier': 'A', 'source_keys': ['hcris_panel'],
             'locator': 'HCRIS extract, one row per CCN x fiscal year',
             'lives_on': 'HCRIS_Hospital_Panel',
             'cross_check': 'The occupancy_trend statistics quoted in the repo '
                            'modules derive from this same panel'})

    # ── LEIE_Ambulance_Exclusions ───────────────────────────────────────────
    if _have('leie_ambulance'):
        rows = _load('leie_ambulance')
        sources.append(
            {'key': 'leie_amb', 'publisher': 'HHS OIG',
             'document': 'List of Excluded Individuals/Entities (LEIE) - '
                         'ambulance-related rows',
             'vintage': 'Current cumulative file, accessed 11 Jul 2026',
             'locator': "Rows whose business name / general field / specialty "
                        "contains 'AMBULANCE' or EMT specialty",
             'supplies': 'The program-integrity registry: every ambulance-'
                         'related exclusion from federal health programs',
             'url': 'https://oig.hhs.gov/exclusions/exclusions_list.asp',
             'tier': 'A', 'accessed': '11 Jul 2026',
             'powers': ['LEIE_Ambulance_Exclusions']})
        ws = wb.create_sheet('LEIE_Ambulance_Exclusions')
        sb = lib.SheetBuilder(ws, 9, col_widths=[18, 14, 40, 22, 22, 12, 6, 10, 11],
                              tab_color='FF00294C')
        sb.title(f'Ambulance-related federal program exclusions '
                 f'({len(rows):,} LEIE rows)')
        sb.subtitle('The question: which ambulance businesses and EMS personnel '
                    'have been excluded from federal health programs - the '
                    'compliance screen for any supplier roll-up? HHS OIG LEIE '
                    'cumulative file filtered to ambulance-related rows (filter '
                    'stated on Pull_Manifest; the full file is the screen of '
                    'record). NPI joins to PECOS_Registry and MUP_Providers_* '
                    'where populated (older exclusions predate NPI).')
        sb.blank()
        sb.headers(['Last name', 'First name', 'Business name', 'General',
                    'Specialty', 'NPI', 'State', 'Exclusion type',
                    'Exclusion date'])
        for r in sorted(rows, key=lambda x: ((x.get('STATE') or ''),
                                             (x.get('BUSNAME') or ''),
                                             (x.get('LASTNAME') or ''))):
            npi = r.get('NPI')
            sb.row([(r.get('LASTNAME'), 'src'), (r.get('FIRSTNAME'), 'src'),
                    (r.get('BUSNAME'), 'src'), (r.get('GENERAL'), 'src'),
                    (r.get('SPECIALTY'), 'src'),
                    (npi if npi not in ('0', 0) else '', 'src'),
                    (r.get('STATE'), 'src'), (r.get('EXCLTYPE'), 'src'),
                    (r.get('EXCLDATE'), 'src')])
        facts.append(
            {'metric': 'Ambulance-related LEIE exclusions on file', 'year': 2026,
             'value': len(rows), 'unit': 'exclusions', 'basis': 'GOV', 'tier': 'A',
             'source_keys': ['leie_amb'],
             'locator': 'LEIE UPDATED.csv, ambulance filter (manifest)',
             'lives_on': 'LEIE_Ambulance_Exclusions',
             'cross_check': 'Companion to the CERT/RSNAT payment-integrity '
                            'evidence on Payment_Integrity'})

    return {'facts': facts, 'sources': sources, 'excluded': excluded,
            'meta': {'row_counts': {s['name']: wb[s['name']].max_row
                                    for s in SHEETS if s['name'] in wb.sheetnames}}}


CENSUS_CTY_URL = ('https://www2.census.gov/programs-surveys/popest/datasets/'
                  '2020-2024/counties/asrh/cc-est2024-agesex-all.csv')
