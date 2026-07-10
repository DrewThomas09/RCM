"""Granular detail-tab families: per-year raw-data tabs plus full registries.

Families (all direct dataset extractions, Tier A, cited on the family's source):
  PSPS_Detail_YYYY   2010-2024  code x initial-modifier matrices w/ denial rates
  MUP_State_YYYY     2013-2024  state x code utilization/price rows
  MS_County_YYYY     2020-2025  county-grain ambulance saturation, 3 service types
  QCEW_State_YYYY    2014-2025  state x ownership industry rows
  Enroll_State_YYYY  2013-2025  state enrollment + ESRD rows
  Registries         full facility listings (hospitals, SNF, dialysis, IRF, LTCH,
                     hospice, HHA), the PECOS ambulance supplier registry, and the
                     hospital service-area catchment aggregates
"""
import json
import os

CACHE_DIR = os.environ.get(
    'IFT_V3_CACHE',
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 'ift_v3_cache'))

PSPS_CODES = ['A0425', 'A0426', 'A0427', 'A0428', 'A0429', 'A0433', 'A0434']
CODES = ['A0425', 'A0426', 'A0427', 'A0428', 'A0429', 'A0430', 'A0431', 'A0432',
         'A0433', 'A0434', 'A0435', 'A0436']
CODE_LABEL = {
    'A0425': 'Ground mileage', 'A0426': 'ALS1 non-emergency', 'A0427': 'ALS1 emergency',
    'A0428': 'BLS non-emergency', 'A0429': 'BLS emergency', 'A0430': 'Fixed-wing air',
    'A0431': 'Rotary-wing air', 'A0432': 'Paramedic intercept', 'A0433': 'ALS2',
    'A0434': 'Specialty care transport', 'A0435': 'Fixed-wing mileage',
    'A0436': 'Rotary mileage'}


def _have(key):
    p = os.path.join(CACHE_DIR, key + '.json')
    return os.path.exists(p) or os.path.exists(p + '.gz')


def _load(key):
    import gzip
    p = os.path.join(CACHE_DIR, key + '.json')
    if os.path.exists(p):
        return json.load(open(p))
    with gzip.open(p + '.gz', 'rt') as f:
        return json.load(f)


def _years(prefix, lo, hi, per_code=None):
    out = []
    for yr in range(lo, hi + 1):
        key = f'{prefix}_{yr}' if per_code is None else f'{prefix}_{yr}_{per_code}'
        if _have(key):
            out.append(yr)
    return out

PSPS_YEARS = _years('psps_agg', 2010, 2024, per_code='A0428')
MUP_YEARS = [y for y in range(2013, 2025) if _have(f'mup_state_{y}_A0428')]
MS_YEARS = _years('marketsat_county', 2020, 2025)
QCEW_YEARS = _years('qcew_621910', 2014, 2025)
QCEW_CTY_YEARS = _years('qcew_county', 2014, 2025)
ENROLL_HAVE = _have('enrollment_state_year')
ENROLL_YEARS = list(range(2013, 2026)) if ENROLL_HAVE else []

ROLLING_WINDOWS = [
    '2020-04-01 to 2021-03-31', '2020-07-01 to 2021-06-30', '2020-10-01 to 2021-09-30',
    '2021-04-01 to 2022-03-31', '2021-07-01 to 2022-06-30', '2021-10-01 to 2022-09-30',
    '2022-04-01 to 2023-03-31', '2022-07-01 to 2023-06-30', '2022-10-01 to 2023-09-30',
]


def _wkey(period):
    return 'marketsat_county_w' + period[:7].replace('-', '')


def _wtab(period):
    return 'MS_CtyWin_' + period[:7].replace('-', '_')

ROLLING_HAVE = [p for p in ROLLING_WINDOWS if _have(_wkey(p))]

CROSSWALK = ('/home/user/RCM/RCM_MC/rcm_mc/data/vendor/cbsa_crosswalk/'
             'cbsa_county_crosswalk.csv')


def _county_names():
    """FIPS -> (county name, state abbrev, CBSA title).

    Names come from the CMS market-saturation county cache; CBSA titles from the
    vendored OMB 2023 crosswalk. Both joins are documented on the tab.
    """
    import csv as _csv
    out = {}
    for yr in reversed(MS_YEARS):
        try:
            for b in _load(f'marketsat_county_{yr}'):
                for r in b['county_rows']:
                    f = str(r.get('county_fips') or '').zfill(5)
                    if f and f not in out:
                        out[f] = [r.get('county'), r.get('state'), '']
            break
        except FileNotFoundError:
            continue
    try:
        with open(CROSSWALK) as fh:
            for r in _csv.DictReader(fh):
                f = str(r.get('county_fips') or '').zfill(5)
                if f in out:
                    out[f][2] = r.get('cbsa_title') or ''
                elif f:
                    out[f] = [None, None, r.get('cbsa_title') or '']
    except OSError:
        pass
    return out

REGISTRIES = [
    ('pdc2_hospitals', 'Hosp_Registry', 'Hospitals'),
    ('pdc2_nursing_homes', 'SNF_Registry', 'Nursing homes (SNF)'),
    ('pdc2_dialysis', 'Dialysis_Registry', 'Dialysis facilities'),
    ('pdc2_irf', 'IRF_Registry', 'Inpatient rehabilitation facilities'),
    ('pdc2_ltch', 'LTCH_Registry', 'Long-term care hospitals'),
    ('pdc2_hospice', 'Hospice_Registry', 'Hospices'),
    ('pdc2_home_health', 'HHA_Registry', 'Home health agencies'),
]

SHEETS = (
    [{'name': f'PSPS_Detail_{y}', 'tab_color': 'FF1F6F8B'} for y in PSPS_YEARS]
    + [{'name': f'MUP_State_{y}', 'tab_color': 'FF1F6F8B'} for y in MUP_YEARS]
    + [{'name': f'Enroll_State_{y}', 'tab_color': 'FF1F6F8B'} for y in ENROLL_YEARS]
    + [{'name': f'MS_County_{y}', 'tab_color': 'FF1F6F8B'} for y in MS_YEARS]
    + [{'name': _wtab(p), 'tab_color': 'FF1F6F8B'} for p in ROLLING_HAVE]
    + [{'name': f'QCEW_State_{y}', 'tab_color': 'FF1F6F8B'} for y in QCEW_YEARS]
    + [{'name': f'QCEW_County_{y}', 'tab_color': 'FF1F6F8B'} for y in QCEW_CTY_YEARS]
    + [{'name': name, 'tab_color': 'FF00294C'} for key, name, _ in REGISTRIES
       if _have(key)]
    + ([{'name': 'PECOS_Registry', 'tab_color': 'FF00294C'}]
       if _have('pecos_ambulance_registry') else [])
    + ([{'name': 'HSA_Hospital_Catchment', 'tab_color': 'FF00294C'}]
       if _have('hsa_2025_hospital_agg') else [])
    + ([{'name': 'ED_Timeliness_Registry', 'tab_color': 'FF7A5195'}]
       if _have('pdc_timely_ed_hospital') else [])
)


def _f(v):
    if v in (None, '', '*', 'N/A'):
        return None
    try:
        return float(str(v).replace(',', '').replace('$', ''))
    except (TypeError, ValueError):
        return None


def _i(v):
    f = _f(v)
    return int(f) if f is not None and f == int(f) else f


OWN = {'1': 'Federal government', '2': 'State government', '3': 'Local government',
       '5': 'Private'}


def build(wb, ctx):
    lib = ctx['lib']
    facts, sources, excluded = [], [], []
    sources += [
        {'key': 'psps_detail', 'publisher': 'CMS',
         'document': 'Physician/Supplier Procedure Summary (PSPS) - annual detail',
         'vintage': f'Data years {PSPS_YEARS[0]}-{PSPS_YEARS[-1]}' if PSPS_YEARS else 'n/a',
         'locator': 'Per year: HCPCS x initial origin-destination modifier sums of '
                    'submitted/denied services and submitted/allowed charges',
         'supplies': 'The raw-grain PSPS matrices behind PSPS_Denial_Series',
         'url': 'https://data.cms.gov/summary-statistics-on-use-and-payments/physiciansupplier-procedure-summary',
         'tier': 'A', 'accessed': '10 Jul 2026',
         'powers': [f'PSPS_Detail_{y}' for y in PSPS_YEARS]},
        {'key': 'mup_state_detail', 'publisher': 'CMS',
         'document': 'Medicare Physician & Other Practitioners - by Geography and '
                     'Service (state detail)',
         'vintage': f'Data years {MUP_YEARS[0]}-{MUP_YEARS[-1]}' if MUP_YEARS else 'n/a',
         'locator': 'State x ambulance HCPCS rows, all published columns',
         'supplies': 'The per-year state-grain utilization/price detail behind '
                     'MUP_Ambulance_State',
         'url': 'https://data.cms.gov/provider-summary-by-type-of-service/medicare-physician-other-practitioners/medicare-physician-other-practitioners-by-geography-and-service',
         'tier': 'A', 'accessed': '10 Jul 2026',
         'powers': [f'MUP_State_{y}' for y in MUP_YEARS]},
        {'key': 'ms_county', 'publisher': 'CMS',
         'document': 'Market Saturation & Utilization State-County (county grain)',
         'vintage': 'Calendar-aligned windows 2020-2025',
         'locator': 'County rows, three ambulance service types, all kept columns',
         'supplies': 'County-level ambulance supply density: the raw whitespace grain',
         'url': 'https://data.cms.gov/summary-statistics-on-use-and-payments/program-integrity-market-saturation-by-type-of-service/market-saturation-utilization-state-county',
         'tier': 'A', 'accessed': '10 Jul 2026',
         'powers': [f'MS_County_{y}' for y in MS_YEARS]},
        {'key': 'qcew_state_detail', 'publisher': 'BLS',
         'document': 'QCEW NAICS 621910 annual averages - state detail',
         'vintage': f'{QCEW_YEARS[0]}-{QCEW_YEARS[-1]}' if QCEW_YEARS else 'n/a',
         'locator': 'Statewide rollup rows by ownership',
         'supplies': 'Per-year state industry detail behind QCEW_EMS_Employment',
         'url': 'https://www.bls.gov/cew/downloadable-data-files.htm',
         'tier': 'A', 'accessed': '10 Jul 2026',
         'powers': [f'QCEW_State_{y}' for y in QCEW_YEARS]},
        {'key': 'enroll_state_detail', 'publisher': 'CMS',
         'document': 'Medicare Monthly Enrollment - state-year detail',
         'vintage': '2013-2025 (MONTH=Year)',
         'locator': 'State rows: totals, Original Medicare, MA & other, ESRD splits',
         'supplies': 'Per-year state enrollment detail behind Enrollment_ESRD_State',
         'url': 'https://data.cms.gov/summary-statistics-on-beneficiary-enrollment/medicare-and-medicaid-reports/medicare-monthly-enrollment',
         'tier': 'A', 'accessed': '10 Jul 2026',
         'powers': [f'Enroll_State_{y}' for y in ENROLL_YEARS]},
        {'key': 'pdc_registries', 'publisher': 'CMS',
         'document': 'Provider Data Catalog (Care Compare) facility files - full listings',
         'vintage': 'Current snapshots, accessed 10 Jul 2026',
         'locator': 'Facility-level rows: CCN, name, city, state, ZIP, county, '
                    'ownership, class-specific columns',
         'supplies': 'The named facility universe: every certified hospital, SNF, '
                     'dialysis facility, IRF, LTCH, hospice and HHA',
         'url': 'https://data.cms.gov/provider-data/',
         'tier': 'A', 'accessed': '10 Jul 2026',
         'powers': [n for k, n, _ in REGISTRIES if _have(k)]},
        {'key': 'pecos_registry_src', 'publisher': 'CMS',
         'document': 'Medicare FFS Public Provider Enrollment (PECOS) - ambulance '
                     'supplier registry',
         'vintage': '2026 Q1 snapshot, pulled 10 Jul 2026',
         'locator': 'PROVIDER_TYPE_DESC = "PART B SUPPLIER - AMBULANCE SERVICE '
                    'SUPPLIER"; NPI, enrollment ID, organization name, state',
         'supplies': 'Every Medicare-enrolled ambulance supplier, by name',
         'url': 'https://data.cms.gov/provider-characteristics/medicare-provider-supplier-enrollment/medicare-fee-for-service-public-provider-enrollment',
         'tier': 'A', 'accessed': '10 Jul 2026', 'powers': ['PECOS_Registry']},
    ]
    if _have('hsa_2025_hospital_agg'):
        sources.append(
            {'key': 'hsa_agg', 'publisher': 'CMS', 'document': 'Hospital Service Area',
             'vintage': 'Latest published year (see tab)',
             'locator': 'Hospital x ZIP rows aggregated per hospital: ZIPs served, '
                        'total cases, days, charges',
             'supplies': 'Hospital catchment breadth - the transfer-corridor '
                         'denominator',
             'url': 'https://data.cms.gov/summary-statistics-on-use-and-payments/medicare-service-area-reports/hospital-service-area',
             'tier': 'A', 'accessed': '10 Jul 2026',
             'powers': ['HSA_Hospital_Catchment']})

    # ── PSPS_Detail_YYYY ────────────────────────────────────────────────────
    for yr in PSPS_YEARS:
        ws = wb.create_sheet(f'PSPS_Detail_{yr}')
        sb = lib.SheetBuilder(ws, 9, col_widths=[9, 24, 12, 14, 13, 10, 15, 15, 12],
                              tab_color='FF1F6F8B')
        sb.title(f'PSPS raw detail, {yr}: code x origin-destination modifier')
        sb.subtitle('The question: for each ambulance HCPCS, how do submitted '
                    'services, denials and allowed charges distribute across '
                    'origin-destination pairs? Client-side sums over every raw PSPS '
                    f'claim-summary row for data year {yr} (row counts and SHA-256 '
                    'per code on Pull_Manifest). Suppressed cells (<11 services) are '
                    'absent at source: every count is a floor. Modifier letters: '
                    'first = origin, second = destination (H hospital, N SNF, R '
                    'residence, E residential/custodial, D diagnostic site, P '
                    'physician office, S scene, G dialysis, X intermediate stop).')
        sb.blank()
        sb.headers(['HCPCS', 'Level of service', 'Initial modifier',
                    'Submitted services', 'Denied services', 'Denial rate',
                    'Submitted charges $', 'Allowed charges $', 'Share of code'])
        code_tot_rows = {}
        for code in PSPS_CODES:
            try:
                d = _load(f'psps_agg_{yr}_{code}')
            except FileNotFoundError:
                continue
            mods = d['by_initial_modifier']
            tot_sub = sum(a.get('SUBMITTED_SERVICE_CNT', 0) for a in mods.values())
            first = sb.r + 1
            for mod, a in sorted(mods.items(),
                                 key=lambda kv: -kv[1].get('SUBMITTED_SERVICE_CNT', 0)):
                row_n = sb.r + 1
                sb.row([(code, 'src'), CODE_LABEL[code], (mod, 'src'),
                        (a.get('SUBMITTED_SERVICE_CNT'), 'src', lib.FMT_INT),
                        (a.get('DENIED_SERVICES_CNT'), 'src', lib.FMT_INT),
                        (f'=IF(D{row_n}=0,"n/a",E{row_n}/D{row_n})', 'fml', lib.FMT_PCT1),
                        (a.get('SUBMITTED_CHARGE_AMT'), 'src', lib.FMT_USD),
                        (a.get('ALLOWED_CHARGE_AMT'), 'src', lib.FMT_USD),
                        ((f'=D{row_n}/SUM(D{first}:D{first + len(mods) - 1})'
                          if tot_sub else None), 'fml', lib.FMT_PCT1)])
            last = sb.r
            trow = sb.r + 1
            code_tot_rows[code] = trow
            sb.row([(code, 'label'), (f'{CODE_LABEL[code]} - TOTAL', 'label'), 'all',
                    (f'=SUM(D{first}:D{last})', 'fml', lib.FMT_INT),
                    (f'=SUM(E{first}:E{last})', 'fml', lib.FMT_INT),
                    (f'=IF(D{trow}=0,"n/a",E{trow}/D{trow})', 'fml', lib.FMT_PCT1),
                    (f'=SUM(G{first}:G{last})', 'fml', lib.FMT_USD),
                    (f'=SUM(H{first}:H{last})', 'fml', lib.FMT_USD), None])
        if code_tot_rows:
            sb.blank()
            sb.banner('Code totals (live sums of the matrix above)')
            sb.headers(['HCPCS', 'Level of service', '', 'Submitted services',
                        'Denied services', 'Denial rate'], freeze=False)
            t0 = sb.r + 1
            for code, trow in code_tot_rows.items():
                row_n = sb.r + 1
                sb.row([(code, 'label'), CODE_LABEL[code], None,
                        (f'=D{trow}', 'fml', lib.FMT_INT),
                        (f'=E{trow}', 'fml', lib.FMT_INT),
                        (f'=IF(D{row_n}=0,"n/a",E{row_n}/D{row_n})', 'fml',
                         lib.FMT_PCT1)])
            t1 = sb.r
            sb.note(f'Cross-foot: code totals on this tab reconcile to the {yr} rows '
                    'of PSPS_Denial_Series Panel A (same cached artifacts, same '
                    'sums).')
            lib.add_chart(ws, f'K{t0 - 8}',
                          f'Submitted services by code, {yr}',
                          f'PSPS_Detail_{yr}!$A${t0}:$A${t1}',
                          [('Submitted', f'PSPS_Detail_{yr}!$D${t0}:$D${t1}')],
                          kind='bar', width=16, height=8)
    # ── MUP_State_YYYY ─────────────────────────────────────────────────────
    for yr in MUP_YEARS:
        ws = wb.create_sheet(f'MUP_State_{yr}')
        sb = lib.SheetBuilder(ws, 11,
                              col_widths=[18, 7, 9, 24, 11, 12, 13, 12, 12, 12, 13],
                              tab_color='FF1F6F8B')
        sb.title(f'Medicare ambulance by state and code, {yr} (published rows)')
        sb.subtitle('The question: the full state-grain Medicare ambulance record '
                    f'for data year {yr} - every published row, all columns. Source: '
                    'CMS MUP by Geography & Service (final-action). Suppressed '
                    'state-code cells (<=10 beneficiaries) are absent at source. '
                    'Series view with CAGR: MUP_Ambulance_State and '
                    'MUP_Ambulance_National.')
        sb.blank()
        sb.headers(['State', 'Geo', 'HCPCS', 'Level of service', 'Providers',
                    'Beneficiaries', 'Services', 'Bene-day services',
                    'Avg submitted $', 'Avg allowed $', 'Avg paid $'])
        for code in CODES:
            try:
                rows = _load(f'mup_state_{yr}_{code}')
            except FileNotFoundError:
                continue
            for r in sorted(rows, key=lambda x: x['Rndrng_Prvdr_Geo_Desc']):
                sb.row([(r['Rndrng_Prvdr_Geo_Desc'], 'src'),
                        (r.get('Rndrng_Prvdr_Geo_Cd'), 'src'),
                        (r['HCPCS_Cd'], 'src'), CODE_LABEL.get(r['HCPCS_Cd'], ''),
                        (_i(r.get('Tot_Rndrng_Prvdrs')), 'src', lib.FMT_INT),
                        (_i(r.get('Tot_Benes')), 'src', lib.FMT_INT),
                        (_f(r.get('Tot_Srvcs')), 'src', lib.FMT_INT),
                        (_f(r.get('Tot_Bene_Day_Srvcs')), 'src', lib.FMT_INT),
                        (_f(r.get('Avg_Sbmtd_Chrg')), 'src', lib.FMT_USD2),
                        (_f(r.get('Avg_Mdcr_Alowd_Amt')), 'src', lib.FMT_USD2),
                        (_f(r.get('Avg_Mdcr_Pymt_Amt')), 'src', lib.FMT_USD2)])
    # ── Enroll_State_YYYY ──────────────────────────────────────────────────
    if ENROLL_HAVE:
        st = _load('enrollment_state_year')
        by_year = {}
        for r in st:
            by_year.setdefault(int(r['YEAR']), []).append(r)
        for yr in ENROLL_YEARS:
            rows = sorted(by_year.get(yr, []), key=lambda r: r['BENE_STATE_DESC'])
            ws = wb.create_sheet(f'Enroll_State_{yr}')
            sb = lib.SheetBuilder(ws, 10,
                                  col_widths=[17, 7, 12, 13, 12, 10, 11, 12, 11, 11],
                                  tab_color='FF1F6F8B')
            sb.title(f'Medicare enrollment by state, {yr}')
            sb.subtitle('The question: the per-state enrollment denominators for '
                        f'{yr}, all key columns as published (MONTH=Year rows). '
                        'Series view: Enrollment_ESRD_State.')
            sb.blank()
            sb.headers(['State', 'Abbrev', 'Total benes', 'Original Medicare',
                        'MA & other', 'MA share', 'Aged total', 'Aged ESRD',
                        'Disabled total', 'Disabled ESRD'])
            for r in rows:
                row_n = sb.r + 1
                sb.row([(r['BENE_STATE_DESC'], 'src'), (r['BENE_STATE_ABRVTN'], 'src'),
                        (_i(r['TOT_BENES']), 'src', lib.FMT_INT),
                        (_i(r['ORGNL_MDCR_BENES']), 'src', lib.FMT_INT),
                        (_i(r['MA_AND_OTH_BENES']), 'src', lib.FMT_INT),
                        (f'=IF(C{row_n}=0,"n/a",E{row_n}/C{row_n})', 'fml', lib.FMT_PCT1),
                        (_i(r.get('AGED_TOT_BENES')), 'src', lib.FMT_INT),
                        (_i(r.get('AGED_ESRD_BENES')), 'src', lib.FMT_INT),
                        (_i(r.get('DSBLD_TOT_BENES')), 'src', lib.FMT_INT),
                        (_i(r.get('DSBLD_ESRD_AND_ESRD_ONLY_BENES')), 'src', lib.FMT_INT)])
    # ── MS_County_YYYY ─────────────────────────────────────────────────────
    for yr in MS_YEARS:
        blocks = _load(f'marketsat_county_{yr}')
        ws = wb.create_sheet(f'MS_County_{yr}')
        sb = lib.SheetBuilder(ws, 10,
                              col_widths=[30, 18, 7, 11, 13, 11, 11, 10, 14, 11],
                              tab_color='FF1F6F8B')
        sb.title(f'County-grain ambulance market saturation, calendar {yr}')
        sb.subtitle('The question: the raw county-level ambulance supply/use record '
                    f'for the Jan-Dec {yr} window - every county row, all three '
                    'service types. Source: CMS Market Saturation & Utilization. '
                    'Empty cells are CMS small-cell suppression (<11 users): floors, '
                    'not zeros. State roll-up and whitespace bands: '
                    'Market_Saturation_Ambulance.')
        sb.blank()
        sb.headers(['Service type', 'County', 'State', 'County FIPS',
                    'FFS beneficiaries', 'Providers', 'Users', 'Users % of FFS',
                    'Total payment $', 'Moratorium'])
        for b in blocks:
            t = b['type_of_service']
            for r in sorted(b['county_rows'],
                            key=lambda x: (x.get('state') or '', x.get('county') or '')):
                sb.row([t, (r.get('county'), 'src'), (r.get('state'), 'src'),
                        (r.get('county_fips'), 'src'),
                        (_f(r.get('number_of_fee_for_service_beneficiaries')), 'src', lib.FMT_INT),
                        (_f(r.get('number_of_providers')), 'src', lib.FMT_INT),
                        (_f(r.get('number_of_users')), 'src', lib.FMT_INT),
                        (_f(r.get('percentage_of_users_out_of_ffs_beneficiaries')), 'src', lib.FMT_PCT1),
                        (_f(r.get('total_payment')), 'src', lib.FMT_USD),
                        (r.get('moratorium'), 'src')])
    # ── MS_CtyWin (rolling windows) ────────────────────────────────────────
    for period in ROLLING_HAVE:
        blocks = _load(_wkey(period))
        ws = wb.create_sheet(_wtab(period))
        sb = lib.SheetBuilder(ws, 10,
                              col_widths=[30, 18, 7, 11, 13, 11, 11, 10, 14, 11],
                              tab_color='FF1F6F8B')
        sb.title(f'County-grain ambulance market saturation, window {period}')
        sb.subtitle('The question: the raw county-level ambulance supply/use record '
                    f'for the ROLLING 12-month window {period} - every county row, '
                    'all three service types. ROLLING windows OVERLAP adjacent '
                    'windows by nine months: use them for recency and window-'
                    'robustness checks, never as independent annual observations '
                    '(trend on the calendar tabs MS_County_2020..2025). Source: CMS '
                    'Market Saturation & Utilization. Empty cells are small-cell '
                    'suppression: floors, not zeros.')
        sb.blank()
        sb.headers(['Service type', 'County', 'State', 'County FIPS',
                    'FFS beneficiaries', 'Providers', 'Users', 'Users % of FFS',
                    'Total payment $', 'Moratorium'])
        for b in blocks:
            t = b['type_of_service']
            for r in sorted(b['county_rows'],
                            key=lambda x: (x.get('state') or '', x.get('county') or '')):
                sb.row([t, (r.get('county'), 'src'), (r.get('state'), 'src'),
                        (r.get('county_fips'), 'src'),
                        (_f(r.get('number_of_fee_for_service_beneficiaries')), 'src', lib.FMT_INT),
                        (_f(r.get('number_of_providers')), 'src', lib.FMT_INT),
                        (_f(r.get('number_of_users')), 'src', lib.FMT_INT),
                        (_f(r.get('percentage_of_users_out_of_ffs_beneficiaries')), 'src', lib.FMT_PCT1),
                        (_f(r.get('total_payment')), 'src', lib.FMT_USD),
                        (r.get('moratorium'), 'src')])
    if ROLLING_HAVE:
        sources.append(
            {'key': 'ms_county_rolling', 'publisher': 'CMS',
             'document': 'Market Saturation & Utilization State-County (county '
                         'grain, rolling windows)',
             'vintage': 'Nine rolling 12-month windows, 2020-2023',
             'locator': 'County rows, three ambulance service types, overlapping '
                        'reference periods',
             'supplies': 'Window-robustness county detail between the calendar '
                         'windows',
             'url': 'https://data.cms.gov/summary-statistics-on-use-and-payments/program-integrity-market-saturation-by-type-of-service/market-saturation-utilization-state-county',
             'tier': 'A', 'accessed': '10 Jul 2026',
             'powers': [_wtab(p) for p in ROLLING_HAVE]})

    # ── QCEW_State_YYYY ────────────────────────────────────────────────────
    for yr in QCEW_YEARS:
        rows = _load(f'qcew_621910_{yr}')
        ws = wb.create_sheet(f'QCEW_State_{yr}')
        sb = lib.SheetBuilder(ws, 8, col_widths=[10, 20, 13, 13, 16, 13, 14, 12],
                              tab_color='FF1F6F8B')
        sb.title(f'Ambulance industry by state (QCEW NAICS 621910), {yr}')
        sb.subtitle('The question: the per-state ambulance-industry employer record '
                    f'for {yr}: establishments, employment, wages by ownership. '
                    'Statewide rollups; disclosure-suppressed cells are zero in the '
                    'BLS file and carried as published. Series view: '
                    'QCEW_EMS_Employment.')
        sb.blank()
        sb.headers(['Area FIPS', 'Ownership', 'Establishments', 'Employment',
                    'Total annual wages $', 'Avg annual pay $',
                    'Employment location quotient', ''])
        for r in sorted(rows, key=lambda x: (x['area_fips'], x['own_code'])):
            sb.row([(r['area_fips'], 'src'), OWN.get(r['own_code'], r['own_code']),
                    (_f(r.get('annual_avg_estabs')), 'src', lib.FMT_INT),
                    (_f(r.get('annual_avg_emplvl')), 'src', lib.FMT_INT),
                    (_f(r.get('total_annual_wages')), 'src', lib.FMT_USD),
                    (_f(r.get('avg_annual_pay')), 'src', lib.FMT_USD),
                    (_f(r.get('lq_annual_avg_emplvl')), 'src', lib.FMT_DEC2), None])
    # ── QCEW_County_YYYY ───────────────────────────────────────────────────
    if QCEW_CTY_YEARS:
        names = _county_names()
        for yr in QCEW_CTY_YEARS:
            rows = _load(f'qcew_county_{yr}')
            ws = wb.create_sheet(f'QCEW_County_{yr}')
            sb = lib.SheetBuilder(ws, 9,
                                  col_widths=[9, 26, 7, 30, 12, 12, 15, 13, 12],
                                  tab_color='FF1F6F8B')
            sb.title(f'Private ambulance industry by county (QCEW 621910), {yr}')
            sb.subtitle('The question: the county-grain ambulance employer record - '
                        'establishments, employment, wages, private ownership only. '
                        'Zeros are BLS disclosure suppression at source (small-cell), '
                        'not absence of an industry. County names joined from the CMS '
                        'market-saturation county file by FIPS; CBSA titles from the '
                        'vendored OMB Bulletin 23-01 crosswalk (both joins '
                        'documented; unmatched FIPS shown bare).')
            sb.blank()
            sb.headers(['FIPS', 'County', 'State', 'CBSA', 'Establishments',
                        'Employment', 'Total annual wages $', 'Avg annual pay $',
                        'Employment LQ'])
            for r in sorted(rows, key=lambda x: x['area_fips']):
                nm = names.get(r['area_fips'].zfill(5), (None, None, ''))
                sb.row([(r['area_fips'], 'src'), nm[0], nm[1], nm[2],
                        (_f(r.get('annual_avg_estabs')), 'src', lib.FMT_INT),
                        (_f(r.get('annual_avg_emplvl')), 'src', lib.FMT_INT),
                        (_f(r.get('total_annual_wages')), 'src', lib.FMT_USD),
                        (_f(r.get('avg_annual_pay')), 'src', lib.FMT_USD),
                        (_f(r.get('lq_annual_avg_emplvl')), 'src', lib.FMT_DEC2)])
        sources.append(
            {'key': 'qcew_county_detail', 'publisher': 'BLS',
             'document': 'QCEW NAICS 621910 annual averages - county detail, '
                         'private ownership',
             'vintage': f'{QCEW_CTY_YEARS[0]}-{QCEW_CTY_YEARS[-1]}',
             'locator': 'County FIPS rows, own_code 5',
             'supplies': 'County-grain ambulance industry employment and wages',
             'url': 'https://www.bls.gov/cew/downloadable-data-files.htm',
             'tier': 'A', 'accessed': '10 Jul 2026',
             'powers': [f'QCEW_County_{y}' for y in QCEW_CTY_YEARS]})

    # ── Facility registries ────────────────────────────────────────────────
    for key, name, label in REGISTRIES:
        if not _have(key):
            continue
        rows = _load(key)
        cols = list(rows[0].keys()) if rows else []
        ws = wb.create_sheet(name)
        widths = []
        for c in cols:
            if 'name' in c:
                widths.append(42)
            elif 'city' in c or 'county' in c or 'ownership' in c or 'type' in c:
                widths.append(24)
            else:
                widths.append(12)
        sb = lib.SheetBuilder(ws, len(cols), col_widths=widths, tab_color='FF00294C')
        sb.title(f'{label}: the full certified registry ({len(rows):,} facilities)')
        sb.subtitle('The question: every certified facility of this class, by name - '
                    'the physical origin/destination nodes of interfacility '
                    'transport. Source: CMS Provider Data Catalog (Care Compare) '
                    'current snapshot, accessed 10 Jul 2026 (Pull_Manifest). State '
                    'roll-up: Facility_Universe_State.')
        sb.blank()
        sb.headers([c.replace('_', ' ') for c in cols])
        for r in rows:
            sb.row([((_f(r.get(c)), 'src', lib.FMT_INT)
                     if c in ('number_of_certified_beds', '_of_dialysis_stations',
                              'average_number_of_residents_per_day')
                     else (r.get(c), 'src')) for c in cols])
        facts.append(
            {'metric': f'{label}: certified facilities (full registry)', 'year': 2026,
             'value': len(rows), 'unit': 'facilities', 'basis': 'GOV', 'tier': 'A',
             'source_keys': ['pdc_registries'],
             'locator': f'Care Compare snapshot, {name} tab row count',
             'lives_on': name,
             'cross_check': 'Matches Facility_Universe_State state sums (same pull)'})
    # ── PECOS_Registry ─────────────────────────────────────────────────────
    if _have('pecos_ambulance_registry'):
        rows = _load('pecos_ambulance_registry')
        ws = wb.create_sheet('PECOS_Registry')
        sb = lib.SheetBuilder(ws, 6, col_widths=[13, 14, 17, 52, 8, 30],
                              tab_color='FF00294C')
        sb.title(f'Every Medicare-enrolled ambulance supplier ({len(rows):,} organizations)')
        sb.subtitle('The question: who, by name, is enrolled to bill Medicare as an '
                    'ambulance supplier? Source: CMS FFS Public Provider Enrollment '
                    '(PECOS), PROVIDER_TYPE_DESC = "PART B SUPPLIER - AMBULANCE '
                    'SERVICE SUPPLIER", 2026 Q1 snapshot pulled 10 Jul 2026. '
                    'Cross-checks: vendored PPEF 2026.04.01 state table '
                    '(PECOS_Suppliers_State) totals 10,465 - EXACT match; NPPES '
                    'NE/IA sweep on NPPES_Registry_NE_IA.')
        sb.blank()
        sb.headers(['NPI', 'PECOS control ID', 'Enrollment ID', 'Organization name',
                    'State', ''])
        for r in sorted(rows, key=lambda x: ((x.get('STATE_CD') or ''),
                                             (x.get('ORG_NAME') or ''))):
            sb.row([(r.get('NPI'), 'src'), (r.get('PECOS_ASCT_CNTL_ID'), 'src'),
                    (r.get('ENRLMT_ID'), 'src'), (r.get('ORG_NAME'), 'src'),
                    (r.get('STATE_CD'), 'src'), None])
        facts.append(
            {'metric': 'Medicare-enrolled ambulance suppliers (named registry)',
             'year': 2026, 'value': len(rows), 'unit': 'organizations',
             'basis': 'GOV', 'tier': 'A', 'source_keys': ['pecos_registry_src'],
             'locator': 'PECOS public enrollment, ambulance supplier type, 2026Q1',
             'lives_on': 'PECOS_Registry',
             'cross_check': 'EXACT match to vendored PPEF 2026.04.01 national count '
                            'and to the live stats probe (10,465)'})
    # ── HSA_Hospital_Catchment ─────────────────────────────────────────────
    if _have('hsa_2025_hospital_agg'):
        d = _load('hsa_2025_hospital_agg')
        ws = wb.create_sheet('HSA_Hospital_Catchment')
        sb = lib.SheetBuilder(ws, 7, col_widths=[14, 12, 14, 14, 17, 14, 20],
                              tab_color='FF00294C')
        sb.title(f'Hospital catchment breadth: service-area aggregates, {d["data_year"]}')
        sb.subtitle('The question: how broad is each hospital\'s inpatient draw - '
                    'the denominator of transfer-corridor analysis? CMS Hospital '
                    f'Service Area {d["data_year"]}: {d["n_source_rows"]:,} hospital x '
                    'ZIP rows aggregated per hospital by the committed pipeline '
                    '(Pull_Manifest). ZIPs-served counts published rows only '
                    '(suppression drops small cells: floors). Join key: CCN.')
        sb.blank()
        sb.headers(['Provider (CCN)', 'ZIP codes served', 'Total cases',
                    'Total inpatient days', 'Total charges $', 'Cases per ZIP',
                    ''])
        for h in d['hospitals']:
            row_n = sb.r + 1
            sb.row([(h['provider_id'], 'src'), (h['zips'], 'src', lib.FMT_INT),
                    (h['cases'], 'src', lib.FMT_INT), (h['days'], 'src', lib.FMT_INT),
                    (h['charges'], 'src', lib.FMT_USD),
                    (f'=IF(B{row_n}=0,"n/a",C{row_n}/B{row_n})', 'fml', lib.FMT_DEC1),
                    None])
        facts.append(
            {'metric': 'Hospitals in the Hospital Service Area file', 'year':
             int(d['data_year']), 'value': len(d['hospitals']), 'unit': 'hospitals',
             'basis': 'GOV', 'tier': 'A', 'source_keys': ['hsa_agg'],
             'locator': f'HSA {d["data_year"]}, distinct provider IDs',
             'lives_on': 'HSA_Hospital_Catchment',
             'cross_check': 'CCN-joinable to Hosp_Registry (Care Compare)'})

    # ── ED_Timeliness_Registry ─────────────────────────────────────────────
    if _have('pdc_timely_ed_hospital'):
        rows = _load('pdc_timely_ed_hospital')
        ws = wb.create_sheet('ED_Timeliness_Registry')
        sb = lib.SheetBuilder(ws, 9, col_widths=[11, 42, 20, 7, 10, 46, 10, 10, 20],
                              tab_color='FF7A5195')
        sb.title(f'ED throughput by hospital: the transfer-delay registry '
                 f'({len(rows):,} measure rows)')
        sb.subtitle('The question: hospital by hospital, how long do ED patients - '
                    'including those being transferred - wait? CMS Timely & '
                    'Effective Care, hospital grain, filtered to the ED throughput '
                    'measures (OP-18b median ED time to departure, OP-18d for '
                    'psychiatric/mental-health patients, OP-22 left without being '
                    'seen, ED-2 admit-decision-to-departure where reported). This is '
                    'the hospital-level base under the national/state OP-18 panels '
                    'on Demand_Drivers. "Not Available" scores are hospitals below '
                    'reporting thresholds: floors, not zeros.')
        sb.blank()
        sb.headers(['Facility ID', 'Facility name', 'City', 'State', 'Measure',
                    'Measure name', 'Score', 'Sample', 'Period'])
        for r in sorted(rows, key=lambda x: ((x.get('state') or ''),
                                             (x.get('facility_name') or ''),
                                             (x.get('measure_id') or ''))):
            score = r.get('score')
            try:
                score_cell = (float(score), 'src', lib.FMT_INT)
            except (TypeError, ValueError):
                score_cell = (score, 'src')
            sb.row([(r.get('facility_id'), 'src'), (r.get('facility_name'), 'src'),
                    (r.get('citytown'), 'src'), (r.get('state'), 'src'),
                    (r.get('measure_id'), 'src'), r.get('measure_name'),
                    score_cell, (r.get('sample'), 'src'),
                    f"{r.get('start_date', '')} - {r.get('end_date', '')}"])
        sources.append(
            {'key': 'pdc_timely_ed', 'publisher': 'CMS',
             'document': 'Provider Data Catalog: Timely and Effective Care - Hospital',
             'vintage': 'Current snapshot, accessed 10 Jul 2026',
             'locator': 'DKAN dataset yv7e-xc69, measure_ids OP_18b/OP_18d/OP_22/ED_2*',
             'supplies': 'Hospital-grain ED throughput scores - the transfer-delay '
                         'evidence base',
             'url': 'https://data.cms.gov/provider-data/dataset/yv7e-xc69',
             'tier': 'A', 'accessed': '10 Jul 2026',
             'powers': ['ED_Timeliness_Registry']})
        facts.append(
            {'metric': 'Hospital-measure rows in the ED throughput registry',
             'year': 2026, 'value': len(rows), 'unit': 'rows', 'basis': 'GOV',
             'tier': 'A', 'source_keys': ['pdc_timely_ed'],
             'locator': 'Timely & Effective Care hospital file, ED measures',
             'lives_on': 'ED_Timeliness_Registry',
             'cross_check': 'National OP-18 statistics on Demand_Drivers were '
                            're-derived from this same file family in v2.7 (S33)'})

    return {'facts': facts, 'sources': sources, 'excluded': excluded,
            'meta': {'row_counts': {s['name']: wb[s['name']].max_row for s in SHEETS
                                    if s['name'] in wb.sheetnames},
                     'notes': f'families: psps={len(PSPS_YEARS)} mup={len(MUP_YEARS)} '
                              f'ms={len(MS_YEARS)} qcew={len(QCEW_YEARS)} '
                              f'enroll={len(ENROLL_YEARS)}'}}
