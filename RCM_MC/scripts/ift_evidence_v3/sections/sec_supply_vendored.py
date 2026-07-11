"""Group S (vendored) — PECOS supplier universe, NPPES NE/IA registry, CHOW series.

Three tabs built entirely from vendored primary files with provenance registries
(RCM_MC/rcm_mc/data/vendor/* + the repo NPPES reference CSV), cross-checked
against live-pull cache artifacts where available (pecos_stats_check.json,
mup_state_2024_A0425.json).
"""
import csv
import json
import os

SHEETS = [
    {'name': 'PECOS_Suppliers_State', 'tab_color': 'FF1F6F8B'},
    {'name': 'NPPES_Registry_NE_IA', 'tab_color': 'FF1F6F8B'},
    {'name': 'CHOW_Consolidation', 'tab_color': 'FF1F6F8B'},
]

AMB = 'PART B SUPPLIER - AMBULANCE SERVICE SUPPLIER'

STATE_NAME = {
    'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas',
    'CA': 'California', 'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware',
    'DC': 'District of Columbia', 'FL': 'Florida', 'GA': 'Georgia', 'GU': 'Guam',
    'HI': 'Hawaii', 'ID': 'Idaho', 'IL': 'Illinois', 'IN': 'Indiana',
    'IA': 'Iowa', 'KS': 'Kansas', 'KY': 'Kentucky', 'LA': 'Louisiana',
    'ME': 'Maine', 'MD': 'Maryland', 'MA': 'Massachusetts', 'MI': 'Michigan',
    'MN': 'Minnesota', 'MS': 'Mississippi', 'MO': 'Missouri', 'MT': 'Montana',
    'MP': 'Northern Mariana Islands', 'NE': 'Nebraska', 'NV': 'Nevada',
    'NH': 'New Hampshire', 'NJ': 'New Jersey', 'NM': 'New Mexico',
    'NY': 'New York', 'NC': 'North Carolina', 'ND': 'North Dakota',
    'OH': 'Ohio', 'OK': 'Oklahoma', 'OR': 'Oregon', 'PA': 'Pennsylvania',
    'PR': 'Puerto Rico', 'RI': 'Rhode Island', 'SC': 'South Carolina',
    'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah',
    'VT': 'Vermont', 'VA': 'Virginia', 'VI': 'Virgin Islands',
    'WA': 'Washington', 'WV': 'West Virginia', 'WI': 'Wisconsin',
    'WY': 'Wyoming'}
NAME2CODE = {v: k for k, v in STATE_NAME.items()}

CAT_LABEL = {
    'municipal-fire-volunteer': 'Municipal / fire / volunteer squads',
    'private': 'Private / commercial operators',
    'hospital-owned': 'Hospital-owned services',
    'air': 'Air medical',
}


def _load_cache(cache, key):
    return json.load(open(os.path.join(cache, key + '.json')))


def _csv_rows(path):
    with open(path, newline='') as f:
        return list(csv.DictReader(f))


def build(wb, ctx):
    lib, cache, repo = ctx['lib'], ctx['cache'], ctx['repo']
    accessed = ctx['accessed']
    vend = os.path.join(repo, 'RCM_MC', 'rcm_mc', 'data', 'vendor')
    facts, sources, excluded = [], [], []

    # ── Sources ─────────────────────────────────────────────────────────────
    sources += [
        {'key': 'pecos_ppef', 'publisher': 'CMS',
         'document': 'Medicare Fee-For-Service Public Provider Enrollment '
                     '(PECOS public extract), PPEF_Enrollment_Extract_2026.04.01',
         'vintage': 'Extract 2026.04.01 (2026Q1 snapshot; ingested 2026-05-25; '
                    '2,981,799 enrollment rows, PII dropped)',
         'locator': 'PROVIDER_TYPE_DESC = "PART B SUPPLIER - AMBULANCE SERVICE '
                    'SUPPLIER", counts by STATE_CD (55 states/territories) and '
                    'national total',
         'supplies': 'The Medicare-enrolled ambulance supplier universe: 10,465 '
                     'national + per-state fragmentation table',
         'url': 'https://data.cms.gov/provider-characteristics/medicare-provider-'
                'supplier-enrollment/medicare-fee-for-service-public-provider-'
                'enrollment',
         'tier': 'A', 'accessed': accessed, 'powers': ['PECOS_Suppliers_State']},
        {'key': 'pecos_api_check', 'publisher': 'CMS',
         'document': 'Medicare FFS Public Provider Enrollment, data.cms.gov '
                     'data-api row-count probe (/data/stats)',
         'vintage': 'Current API snapshot, probed 2026-07-10T19:31:48Z',
         'locator': 'Dataset UUID 2457ea29-fc82-48b0-86ec-3b0755de7515, filter '
                    'PROVIDER_TYPE_DESC = "PART B SUPPLIER - AMBULANCE SERVICE '
                    'SUPPLIER" -> found_rows',
         'supplies': 'Independent live re-verification of the vendored 10,465 '
                     'supplier count (and the 2,981,799 all-type universe)',
         'url': 'https://data.cms.gov/data-api/v1/dataset/'
                '2457ea29-fc82-48b0-86ec-3b0755de7515/data/stats',
         'tier': 'A', 'accessed': accessed, 'powers': ['PECOS_Suppliers_State']},
        {'key': 'mup_geo_2024_a0425', 'publisher': 'CMS',
         'document': 'Medicare Physician & Other Practitioners - by Geography '
                     'and Service, CY2024',
         'vintage': 'CY2024 (dataset UUID 0c75b0b3-b40f-4007-a5ac-f9f2fed95862), '
                    'pulled 2026-07-10T19:40Z',
         'locator': 'HCPCS_Cd = A0425 (ground mileage), Rndrng_Prvdr_Geo_Lvl = '
                    'State (55 rows) and National; field Tot_Rndrng_Prvdrs',
         'supplies': 'Rendering (billing) ambulance-supplier counts per state, '
                     'CY2024 - the activity-based cross-check on PECOS enrollment',
         'url': 'https://data.cms.gov/summary-statistics-on-use-and-payments/'
                'medicare-physician-other-practitioner-look-up-tool/'
                'medicare-physician-other-practitioners-by-geography-and-service',
         'tier': 'A', 'accessed': accessed, 'powers': ['PECOS_Suppliers_State']},
        {'key': 'nppes_ne_ia', 'publisher': 'CMS',
         'document': 'National Plan and Provider Enumeration System (NPPES) '
                     'Registry API v2.1 - organizational ambulance sweep, NE + IA',
         'vintage': 'Registry snapshot pulled 2026-07-10',
         'locator': 'taxonomy_description = "Ambulance" (text search; the API '
                    'rejects taxonomy codes), enumeration_type = NPI-2, '
                    'state = NE and IA; 751 organization NPIs',
         'supplies': 'The full NE/IA ambulance-organization roster: NPI, name, '
                     'city, address state, primary taxonomy; category column '
                     'keyword-classified downstream',
         'url': 'https://npiregistry.cms.hhs.gov/api/',
         'tier': 'A', 'accessed': accessed, 'powers': ['NPPES_Registry_NE_IA']},
        {'key': 'hospital_chow', 'publisher': 'CMS',
         'document': 'Hospital Change of Ownership (CHOW) public file, '
                     'Hospital_CHOW_2026.04.01',
         'vintage': 'Extract 2026.04.01 (ingested 2026-05-25); CHOWs 2016-2025, '
                    '755 events, 49 states',
         'locator': 'CHOW counts by state and year (facility identifiers '
                    'dropped at ingest); change of ownership per 42 CFR 489.18',
         'supplies': 'Annual count of Medicare-certified hospital ownership '
                     'changes - the official consolidation-event series',
         'url': 'https://data.cms.gov/provider-characteristics/hospitals-and-'
                'other-facilities/hospital-change-of-ownership',
         'tier': 'A', 'accessed': accessed, 'powers': ['CHOW_Consolidation']},
        {'key': 'snf_chow', 'publisher': 'CMS',
         'document': 'Skilled Nursing Facility Change of Ownership (CHOW) '
                     'public file, SNF_CHOW_2026.04.01',
         'vintage': 'Extract 2026.04.01 (ingested 2026-05-25); CHOWs 2016-2025, '
                    '5,141 events, 51 states',
         'locator': 'CHOW counts by state and year (facility identifiers '
                    'dropped at ingest); change of ownership per 42 CFR 489.18',
         'supplies': 'Annual count of Medicare-certified SNF ownership changes '
                     '- the post-acute consolidation-event series',
         'url': 'https://data.cms.gov/provider-characteristics/skilled-nursing-'
                'facilities/skilled-nursing-facility-change-of-ownership',
         'tier': 'A', 'accessed': accessed, 'powers': ['CHOW_Consolidation']},
    ]

    # ════════════════════════════════════════════════════════════════════════
    # Tab 1. PECOS_Suppliers_State
    # ════════════════════════════════════════════════════════════════════════
    ps_dir = os.path.join(vend, 'provider_supply')
    st_rows = [r for r in _csv_rows(os.path.join(ps_dir,
               'provider_supply_state_type.csv')) if r['provider_type'] == AMB]
    nat_rows = [r for r in _csv_rows(os.path.join(ps_dir,
                'provider_supply_national_type.csv')) if r['provider_type'] == AMB]
    report = json.load(open(os.path.join(ps_dir, 'provider_supply_report.json')))
    nat_count = int(nat_rows[0]['enrolled_count']) if nat_rows else None
    by_state = sorted(((r['state'], int(r['enrolled_count'])) for r in st_rows),
                      key=lambda kv: (-kv[1], kv[0]))
    check = _load_cache(cache, 'pecos_stats_check')       # live re-verification
    mup_state = {NAME2CODE.get(r['Rndrng_Prvdr_Geo_Desc']):
                 int(r['Tot_Rndrng_Prvdrs'])
                 for r in _load_cache(cache, 'mup_state_2024_A0425')}
    mup_nat = next(int(r['Tot_Rndrng_Prvdrs']) for r in
                   _load_cache(cache, 'mup_national_2024')
                   if r['HCPCS_Cd'] == 'A0425')

    ws = wb.create_sheet('PECOS_Suppliers_State')
    sb = lib.SheetBuilder(ws, 8, col_widths=[9, 30, 14, 12, 12, 14, 13, 11],
                          tab_color='FF1F6F8B')
    sb.title('Medicare-enrolled ambulance suppliers by state: the PECOS universe')
    sb.subtitle('The question: how many ambulance companies are enrolled to bill '
                'Medicare FFS, and how fragmented is the supplier base by state? '
                'Source: CMS FFS Public Provider Enrollment (PECOS public '
                'extract), PPEF_Enrollment_Extract_2026.04.01, provider type '
                '"PART B SUPPLIER - AMBULANCE SERVICE SUPPLIER". This is '
                'enrollment (permission to bill), not activity: compare the '
                'CY2024 MUP rendering-provider column. Enrollment is a supplier '
                'universe, not an agency census - one company can hold multiple '
                'enrollments and non-Medicare squads never appear.')
    sb.blank()
    sb.banner('Panel A. National anchor + live re-verification '
              '(vendored extract vs 2026-07-10 API probe)')
    sb.headers(['Geo', 'Item', 'Value', 'Detail', '', '', '', 'Basis'])
    sb.row([('US', 'src'), ('Enrolled ambulance suppliers - national', 'label'),
            (nat_count, 'src', lib.FMT_INT),
            (f'{report.get("extract")} (snapshot {report.get("snapshot_date")}); '
             f'provider type "{AMB}"', 'note'),
            None, None, None, ('GOV', 'note')], wrap=True, height=24)
    r_nat = sb.r
    sb.row([None, ('Live re-check: data-api /data/stats found_rows', 'label'),
            (check.get('found_rows'), 'src', lib.FMT_INT),
            ('Same filter, dataset UUID 2457ea29-fc82-48b0-86ec-3b0755de7515, '
             'retrieved 2026-07-10T19:31:48Z', 'note'),
            None, None, None, ('GOV', 'note')], wrap=True, height=24)
    r_live = sb.r
    sb.row([None, ('Vendored = live probe?', 'label'),
            (f'=IF($C${r_nat}=$C${r_live},"MATCH","MISMATCH")', 'fml'),
            ('The v3 pull re-verified the vendored count on 2026-07-10', 'note'),
            None, None, None, ('DERIVED', 'note')])
    r_match = sb.r
    sb.row([None, ('All-provider-type enrollment universe (context)', 'label'),
            (check.get('total_rows'), 'src', lib.FMT_INT),
            (f'Live total_rows; equals the vendored extract raw_rows '
             f'{report.get("raw_rows"):,} - same universe', 'note'),
            None, None, None, ('GOV', 'note')], wrap=True, height=24)

    sb.blank()
    sb.banner('Panel B. State/territory table, sorted by enrolled suppliers '
              '(55 rows = 50 states + DC + GU/MP/PR/VI)')
    sb.headers(['State', 'State / territory', 'Enrolled suppliers',
                'Share of national', 'Cumulative share',
                'MUP CY2024 renderers (A0425)', 'Renderers / enrolled', 'Basis'])
    b0 = sb.r + 1
    for code, cnt in by_state:
        rn = sb.r + 1
        mup_v = mup_state.get(code)
        sb.row([(code, 'src'), (STATE_NAME.get(code, code), 'src'),
                (cnt, 'src', lib.FMT_INT),
                (f'=C{rn}/$C${r_nat}', 'fml', lib.FMT_PCT1),
                (f'=SUM($C${b0}:C{rn})/$C${r_nat}', 'fml', lib.FMT_PCT1),
                ((mup_v, 'src', lib.FMT_INT) if mup_v is not None else None),
                (f'=F{rn}/C{rn}', 'fml', lib.FMT_PCT1) if mup_v is not None
                else None,
                ('GOV', 'note')])
    b1 = sb.r
    sb.row([('US', 'label'), ('Sum of 55 rows (must equal Panel A national)',
            'label'),
            (f'=SUM(C{b0}:C{b1})', 'fml', lib.FMT_INT),
            (f'=C{sb.r + 1}/$C${r_nat}', 'fml', lib.FMT_PCT1), None,
            (f'=SUM(F{b0}:F{b1})', 'fml', lib.FMT_INT), None,
            ('DERIVED', 'note')])
    r_sum = sb.r
    lib.add_chart(ws, f'J{b0}', 'Top-15 states by Medicare-enrolled ambulance '
                  'suppliers (PECOS 2026Q1)',
                  f'PECOS_Suppliers_State!$B${b0}:$B${b0 + 14}',
                  [('Enrolled suppliers',
                    f'PECOS_Suppliers_State!$C${b0}:$C${b0 + 14}')],
                  kind='bar', height=12)
    lib.add_chart(ws, f'J{b0 + 26}', 'Enrolled (PECOS) vs CY2024 billing '
                  'renderers (MUP A0425), top-15 states',
                  f'PECOS_Suppliers_State!$B${b0}:$B${b0 + 14}',
                  [('Enrolled suppliers',
                    f'PECOS_Suppliers_State!$C${b0}:$C${b0 + 14}'),
                   ('MUP renderers CY2024',
                    f'PECOS_Suppliers_State!$F${b0}:$F${b0 + 14}')],
                  kind='bar', height=12)

    sb.blank()
    sb.banner('Panel C. Concentration screens (all live formulas over Panel B)')
    sb.headers(['', 'Screen', 'Value', 'Share of national', 'Detail', '', '',
                'Basis'])
    sb.row([None, ('Top-10 states combined', 'label'),
            (f'=SUM(C{b0}:C{b0 + 9})', 'fml', lib.FMT_INT),
            (f'=C{sb.r + 1}/$C${r_nat}', 'fml', lib.FMT_PCT1),
            ('Panel B is sorted descending, so rows 1-10 are the top 10',
             'note'), None, None, ('DERIVED', 'note')])
    r_top10 = sb.r
    sb.row([None, ('Top-15 states combined (charted)', 'label'),
            (f'=SUM(C{b0}:C{b0 + 14})', 'fml', lib.FMT_INT),
            (f'=C{sb.r + 1}/$C${r_nat}', 'fml', lib.FMT_PCT1),
            None, None, None, ('DERIVED', 'note')])
    sb.row([None, ('Median state/territory count', 'label'),
            (f'=MEDIAN(C{b0}:C{b1})', 'fml', lib.FMT_INT), None,
            ('Half the jurisdictions have fewer enrolled suppliers than this',
             'note'), None, None, ('DERIVED', 'note')])
    sb.row([None, ('States/territories with >= 200 enrolled', 'label'),
            (f'=COUNTIF(C{b0}:C{b1},">=200")', 'fml', lib.FMT_INT), None,
            None, None, None, ('DERIVED', 'note')])
    sb.row([None, ('NE + IA combined (MMT footprint core)', 'label'),
            (f'=SUMIF(A{b0}:A{b1},"NE",C{b0}:C{b1})'
             f'+SUMIF(A{b0}:A{b1},"IA",C{b0}:C{b1})', 'fml', lib.FMT_INT),
            (f'=C{sb.r + 1}/$C${r_nat}', 'fml', lib.FMT_PCT1),
            ('NPPES_Registry_NE_IA carries 751 organization NPIs for the same '
             'two states - the registry universe is wider than Medicare '
             'enrollment (volunteer/non-billing squads included)', 'link'),
            None, None, ('DERIVED', 'note')], wrap=True, height=24)
    r_neia = sb.r
    sb.row([None, ('MUP CY2024 national renderers, A0425 ground mileage',
            'label'), (mup_nat, 'src', lib.FMT_INT),
            (f'=C{sb.r + 1}/$C${r_nat}', 'fml', lib.FMT_PCT1),
            ('Suppliers that actually billed ground mileage in CY2024; ~96% of '
             'the enrolled universe - enrollment slightly overstates active '
             'ground billers', 'note'), None, None, ('GOV', 'note')],
           wrap=True, height=24)
    r_mupnat = sb.r
    sb.note('Units caveat: PECOS counts enrollment records (permission to '
            'bill, 2026Q1 snapshot); MUP counts NPIs that rendered A0425 '
            'ground-mileage services during CY2024 (air-only suppliers and '
            'since-disenrolled billers differ between the two). Neither is an '
            'agency census: one company can hold multiple enrollments/NPIs. '
            'Compare also BLS QCEW establishments (worksites, '
            'QCEW_EMS_Employment) and the 8,721 billing NPIs on the v2.7 '
            'Supplier_Landscape tab - four different units, all stated.')
    sb.note('Extraction: vendored rcm_mc/data/vendor/provider_supply/'
            'provider_supply_{state,national}_type.csv + '
            'provider_supply_report.json (loader rcm_mc/data/provider_supply.py); '
            'live probe cached at ift_v3_cache/pecos_stats_check.json (sha256 '
            'c58a53ec7566ab03a84220583716384e06cd7c698b59b9be391e9538e81c1352); '
            'MUP cross-check cached at ift_v3_cache/mup_state_2024_A0425.json.')

    facts += [
        {'metric': 'Medicare-enrolled ambulance suppliers, national (PECOS)',
         'year': 2026, 'value_ref': f'PECOS_Suppliers_State!C{r_nat}',
         'unit': 'suppliers', 'basis': 'GOV', 'tier': 'A',
         'source_keys': ['pecos_ppef', 'pecos_api_check'],
         'locator': 'PPEF_Enrollment_Extract_2026.04.01, PROVIDER_TYPE_DESC = '
                    '"PART B SUPPLIER - AMBULANCE SERVICE SUPPLIER"',
         'lives_on': 'PECOS_Suppliers_State',
         'cross_check': 'Live /data/stats probe 2026-07-10 returned the same '
                        '10,465 (MATCH cell on-sheet); MUP CY2024 A0425 '
                        'renderers 10,061 (96%)'},
        {'metric': 'Top state by enrolled ambulance suppliers (Ohio)',
         'year': 2026, 'value_ref': f'PECOS_Suppliers_State!C{b0}',
         'unit': 'suppliers', 'basis': 'GOV', 'tier': 'A',
         'source_keys': ['pecos_ppef'],
         'locator': 'State table, STATE_CD = OH', 'lives_on':
         'PECOS_Suppliers_State',
         'cross_check': 'OH 897 > TX 672 > NY 670: supplier counts track '
                        'fragmentation, not population'},
        {'metric': 'Top-10 states share of national enrolled suppliers',
         'year': 2026, 'value_ref': f'PECOS_Suppliers_State!D{r_top10}',
         'unit': 'share', 'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['pecos_ppef'],
         'locator': 'SUM of top-10 sorted state rows / national',
         'lives_on': 'PECOS_Suppliers_State',
         'cross_check': 'about 47% - a long-tail, unconsolidated supplier base'},
        {'metric': 'NE + IA Medicare-enrolled ambulance suppliers',
         'year': 2026, 'value_ref': f'PECOS_Suppliers_State!C{r_neia}',
         'unit': 'suppliers', 'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['pecos_ppef'],
         'locator': 'SUMIF over state rows, NE (287) + IA (296)',
         'lives_on': 'PECOS_Suppliers_State',
         'cross_check': 'NPPES_Registry_NE_IA holds 751 org NPIs for the same '
                        'states - registry universe wider than enrollment'},
        {'metric': 'Ambulance suppliers that billed ground mileage, CY2024 '
                   '(MUP renderers)', 'year': 2024,
         'value_ref': f'PECOS_Suppliers_State!C{r_mupnat}',
         'unit': 'suppliers', 'basis': 'GOV', 'tier': 'A',
         'source_keys': ['mup_geo_2024_a0425'],
         'locator': 'MUP by Geography & Service CY2024, National, A0425, '
                    'Tot_Rndrng_Prvdrs', 'lives_on': 'PECOS_Suppliers_State',
         'cross_check': '96% of the PECOS enrolled universe (formula on-sheet)'},
        {'metric': 'PECOS vendored-vs-live consistency check', 'year': 2026,
         'value_ref': f'PECOS_Suppliers_State!C{r_match}', 'unit': 'flag',
         'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['pecos_ppef', 'pecos_api_check'],
         'locator': 'IF(vendored national = live found_rows)',
         'lives_on': 'PECOS_Suppliers_State',
         'cross_check': 'Also: sum of 55 state rows = national (row below '
                        'Panel B)'},
    ]

    # ════════════════════════════════════════════════════════════════════════
    # Tab 2. NPPES_Registry_NE_IA
    # ════════════════════════════════════════════════════════════════════════
    reg_path = os.path.join(repo, 'RCM_MC', 'rcm_mc', 'market_reports',
                            'reference', 'nppes_ambulance_orgs_ne_ia_20260710.csv')
    reg = _csv_rows(reg_path)
    reg.sort(key=lambda r: (r['search_state'], r['category'],
                            r['org_name'].upper()))
    cats = ['municipal-fire-volunteer', 'private', 'hospital-owned', 'air']

    ws = wb.create_sheet('NPPES_Registry_NE_IA')
    sb = lib.SheetBuilder(ws, 8,
                          col_widths=[12, 44, 18, 9, 8, 27, 24, 10],
                          tab_color='FF1F6F8B')
    sb.title('Who operates ambulances in Nebraska + Iowa: the NPPES registry, '
             'all 751 organizations')
    sb.subtitle('The question: how many ambulance organizations exist in the '
                'MMT footprint core states, and who owns them - municipal/fire/'
                'volunteer squads, private operators, hospitals, or air-medical '
                'programs? Source: CMS NPPES Registry API v2.1 sweep '
                '(taxonomy text "Ambulance", organizational NPI-2, states NE + '
                'IA), pulled 2026-07-10. The registry captures every enumerated '
                'organization including non-Medicare volunteer squads - a wider '
                'universe than the 583 PECOS-enrolled suppliers for the same '
                'two states.')
    sb.blank()

    # Panel A written first; its COUNTIFS reference the roster below.
    sb.banner('Panel A. Summary: organizations by search state x category '
              '(all live formulas over the Panel B roster)')
    sb.headers(['', 'Category (keyword-classified)', 'NE', 'IA', 'Total',
                'Detail', '', 'Basis'])
    # Roster location is known only after writing it; reserve formulas using
    # placeholders is fragile - instead compute roster start deterministically:
    # rows written so far + remaining Panel A rows + banner/headers of Panel B.
    n_sum_rows = len(cats) + 5          # 4 categories + total + 4 diagnostics
    d0 = sb.r + n_sum_rows + 5          # + note + blank + banner + headers + 1
    d1 = d0 + len(reg) - 1
    cat_row = {}
    for c in cats:
        rn = sb.r + 1
        sb.row([None, (CAT_LABEL[c], 'label'),
                (f'=COUNTIFS($E${d0}:$E${d1},"NE",$G${d0}:$G${d1},"{c}")',
                 'fml', lib.FMT_INT),
                (f'=COUNTIFS($E${d0}:$E${d1},"IA",$G${d0}:$G${d1},"{c}")',
                 'fml', lib.FMT_INT),
                (f'=C{rn}+D{rn}', 'fml', lib.FMT_INT),
                (c, 'note'), None, ('DERIVED', 'note')])
        cat_row[c] = sb.r
    rn = sb.r + 1
    sb.row([None, ('Total organization NPIs', 'label'),
            (f'=COUNTIF($E${d0}:$E${d1},"NE")', 'fml', lib.FMT_INT),
            (f'=COUNTIF($E${d0}:$E${d1},"IA")', 'fml', lib.FMT_INT),
            (f'=C{rn}+D{rn}', 'fml', lib.FMT_INT),
            (f'=IF(E{rn}=COUNTA($A${d0}:$A${d1}),"= roster row count",'
             f'"MISMATCH vs roster")', 'fml'), None, ('DERIVED', 'note')])
    r_tot = sb.r
    sb.row([None, ('Distinct organization names', 'label'), None, None,
            (f'=SUMPRODUCT(1/COUNTIF($B${d0}:$B${d1},$B${d0}:$B${d1}))',
             'fml', lib.FMT_INT),
            ('751 NPIs resolve to 686 names: small squads and multi-base '
             'operators hold 2-3 NPIs each', 'note'), None,
            ('DERIVED', 'note')], wrap=True, height=24)
    r_dist = sb.r
    sb.row([None, ('Rows with practice/mailing address outside NE/IA', 'label'),
            None, None,
            (f'=SUMPRODUCT(($D${d0}:$D${d1}<>"NE")*($D${d0}:$D${d1}<>"IA"))',
             'fml', lib.FMT_INT),
            ('NPPES matches search state on practice OR mailing address: '
             'out-of-state air/private operators serving NE/IA appear here',
             'note'), None, ('DERIVED', 'note')], wrap=True, height=24)
    r_oos = sb.r
    sb.row([None, ('Rows whose PRIMARY taxonomy is not an Ambulance code',
            'label'), None, None,
            (f'=SUMPRODUCT(--ISERROR(SEARCH("Ambulance",$F${d0}:$F${d1})))',
             'fml', lib.FMT_INT),
            ('Hospitals/CAHs/NEMT vans holding ambulance as a SECONDARY '
             'taxonomy; the sweep still captures them', 'note'), None,
            ('DERIVED', 'note')], wrap=True, height=24)
    r_nonamb = sb.r
    sb.row([None, ('PECOS-enrolled suppliers, NE + IA (cross-check)', 'label'),
            None, None,
            (f"='PECOS_Suppliers_State'!C{r_neia}", 'link', lib.FMT_INT),
            ('Registry (751) vs Medicare enrollment (583): the gap is the '
             'non-billing / volunteer layer', 'link'), None,
            ('DERIVED', 'note')], wrap=True, height=24)
    sb.note('Caveats that travel with this table: (1) the NPPES API caps every '
            'query at 1,200 results (200/page, skip <= 1,000) - NE (400) and '
            'IA (351) both fit under the cap, so this sweep is complete for '
            'these two states, but the same method truncates in large states '
            '(TX exceeded the cap in testing; use PECOS for national counts). '
            '(2) The API accepts taxonomy TEXT only ("Ambulance"), not codes. '
            '(3) The category column is keyword-classified from the '
            'organization name (DERIVED, rcm_mc ift_npi_landscape) - border '
            'cases straddle categories. (4) Registry enumeration is not an '
            'active-agency census: deactivations lag and multi-NPI '
            'organizations double-count.')
    sb.blank()
    sb.banner('Panel B. Full roster - 751 organization NPIs (sorted: search '
              'state, category, name; row order is presentation only)')
    sb.headers(['NPI', 'Organization name', 'City', 'Addr state',
                'Search state', 'Primary taxonomy', 'Category (keyword)',
                'Basis'])
    d0_actual = sb.r + 1
    for r in reg:
        sb.row([(r['npi'], 'src'), (r['org_name'], 'src'), (r['city'], 'src'),
                (r['state'], 'src'), (r['search_state'], 'src'),
                (r['primary_taxonomy'], 'src'), (r['category'], 'text'),
                ('GOV', 'note')])
    d1_actual = sb.r
    assert d0_actual == d0 and d1_actual == d1, \
        f'roster range drift: planned {d0}-{d1}, actual {d0_actual}-{d1_actual}'
    sb.note('Extraction: rcm_mc/market_reports/reference/'
            'nppes_ambulance_orgs_ne_ia_20260710.csv (7 columns, 751 rows), '
            'surfaced by rcm_mc.market_reports.ift_npi_landscape.registry(); '
            'pull date 2026-07-10 in the filename and module PULL_DATE. Blue '
            'cells are NPPES field values; the Category column is a DERIVED '
            'keyword classification, not an NPPES field.')
    lib.add_chart(ws, 'J6',
                  'NE/IA ambulance organizations by category (NPPES 2026-07-10)',
                  f"NPPES_Registry_NE_IA!$B${cat_row[cats[0]]}:"
                  f"$B${cat_row[cats[-1]]}",
                  [('NE', f"NPPES_Registry_NE_IA!$C${cat_row[cats[0]]}:"
                          f"$C${cat_row[cats[-1]]}"),
                   ('IA', f"NPPES_Registry_NE_IA!$D${cat_row[cats[0]]}:"
                          f"$D${cat_row[cats[-1]]}")],
                  kind='bar', height=10)

    facts += [
        {'metric': 'NE+IA ambulance organization NPIs (NPPES registry)',
         'year': 2026, 'value_ref': f'NPPES_Registry_NE_IA!E{r_tot}',
         'unit': 'organization NPIs', 'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['nppes_ne_ia'],
         'locator': 'COUNTIF over the 751-row roster (NE 400 + IA 351)',
         'lives_on': 'NPPES_Registry_NE_IA',
         'cross_check': 'vs 583 PECOS-enrolled suppliers for NE+IA: the gap '
                        'is the volunteer / non-Medicare-billing layer'},
        {'metric': 'NE municipal/fire/volunteer squads', 'year': 2026,
         'value_ref': f'NPPES_Registry_NE_IA!C{cat_row["municipal-fire-volunteer"]}',
         'unit': 'organization NPIs', 'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['nppes_ne_ia'],
         'locator': 'COUNTIFS search_state=NE, category=municipal-fire-volunteer',
         'lives_on': 'NPPES_Registry_NE_IA',
         'cross_check': '328 of 400 NE org NPIs (82%) - the fragmented '
                        'municipal base the consolidation thesis targets'},
        {'metric': 'IA hospital-owned ambulance services', 'year': 2026,
         'value_ref': f'NPPES_Registry_NE_IA!D{cat_row["hospital-owned"]}',
         'unit': 'organization NPIs', 'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['nppes_ne_ia'],
         'locator': 'COUNTIFS search_state=IA, category=hospital-owned',
         'lives_on': 'NPPES_Registry_NE_IA',
         'cross_check': 'IA 40 vs NE 5: Iowa runs a hospital-owned model - '
                        'the structural contrast between the two states'},
        {'metric': 'Private/commercial ambulance operators, NE+IA',
         'year': 2026, 'value_ref': f'NPPES_Registry_NE_IA!E{cat_row["private"]}',
         'unit': 'organization NPIs', 'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['nppes_ne_ia'],
         'locator': 'COUNTIFS category=private (NE 58 + IA 70)',
         'lives_on': 'NPPES_Registry_NE_IA',
         'cross_check': 'The thin private layer an IFT specialist competes in'},
        {'metric': 'Distinct organization names behind the 751 NPIs',
         'year': 2026, 'value_ref': f'NPPES_Registry_NE_IA!E{r_dist}',
         'unit': 'organizations', 'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['nppes_ne_ia'],
         'locator': 'SUMPRODUCT/COUNTIF distinct-count over org_name',
         'lives_on': 'NPPES_Registry_NE_IA',
         'cross_check': 'Multi-NPI squads mean NPI counts overstate agency '
                        'counts by ~9%'},
        {'metric': 'Roster rows with out-of-state practice/mailing address',
         'year': 2026, 'value_ref': f'NPPES_Registry_NE_IA!E{r_oos}',
         'unit': 'rows', 'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['nppes_ne_ia'],
         'locator': 'SUMPRODUCT over addr-state column',
         'lives_on': 'NPPES_Registry_NE_IA',
         'cross_check': 'Search-state matches practice OR mailing address - '
                        '53 rows are out-of-state operators serving NE/IA'},
        {'metric': 'Roster rows with non-ambulance primary taxonomy',
         'year': 2026, 'value_ref': f'NPPES_Registry_NE_IA!E{r_nonamb}',
         'unit': 'rows', 'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['nppes_ne_ia'],
         'locator': 'SUMPRODUCT ISERROR(SEARCH("Ambulance", primary_taxonomy))',
         'lives_on': 'NPPES_Registry_NE_IA',
         'cross_check': 'Hospitals/CAHs/NEMT vans with ambulance secondary '
                        'taxonomy - 21 rows, kept and flagged'},
    ]

    # ════════════════════════════════════════════════════════════════════════
    # Tab 3. CHOW_Consolidation
    # ════════════════════════════════════════════════════════════════════════
    h_nat = {int(r['year']): int(r['chow_count']) for r in _csv_rows(
        os.path.join(vend, 'hospital_chow', 'hospital_chow_national_year.csv'))}
    s_nat = {int(r['year']): int(r['chow_count']) for r in _csv_rows(
        os.path.join(vend, 'snf_chow', 'snf_chow_national_year.csv'))}
    h_rep = json.load(open(os.path.join(vend, 'hospital_chow',
                                        'hospital_chow_report.json')))
    s_rep = json.load(open(os.path.join(vend, 'snf_chow',
                                        'snf_chow_report.json')))
    h_st, s_st = {}, {}
    for r in _csv_rows(os.path.join(vend, 'hospital_chow',
                                    'hospital_chow_state_year.csv')):
        h_st.setdefault(r['state'], {})[int(r['year'])] = int(r['chow_count'])
    for r in _csv_rows(os.path.join(vend, 'snf_chow',
                                    'snf_chow_state_year.csv')):
        s_st.setdefault(r['state'], {})[int(r['year'])] = int(r['chow_count'])
    years = list(range(2016, 2026))

    ws = wb.create_sheet('CHOW_Consolidation')
    sb = lib.SheetBuilder(ws, 13,
                          col_widths=[13, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 11, 10],
                          tab_color='FF1F6F8B')
    sb.title('Facility consolidation events: CMS change-of-ownership (CHOW) '
             'series, hospitals + SNFs, 2016-2025')
    sb.subtitle('The question: how fast is ownership of the facilities that '
                'originate and receive interfacility transfers changing hands? '
                'A CHOW is a recorded change of ownership of a Medicare-'
                'certified provider under 42 CFR 489.18 (the provider agreement '
                'is assigned to the new owner) - the CMS-official consolidation-'
                'event counter, at state grain. Sources: CMS Hospital CHOW and '
                'SNF CHOW public files, extracts 2026.04.01. CHOWs are a FLOOR '
                'on deal activity: stock deals and system-level mergers that '
                'never reassign the provider agreement do not appear.')
    sb.blank()
    sb.banner('Panel A. National series (events per year)')
    sb.headers(['Year', 'Hospital CHOWs', 'SNF CHOWs', 'Hosp+SNF',
                'Hospital YoY', 'SNF YoY', 'Trend flag', '', '', '', '', '',
                'Basis'])
    a0 = sb.r + 1
    for i, y in enumerate(years):
        rn = sb.r + 1
        flag = ('trend-eligible' if y <= 2024 else
                'FLAGGED - partial accrual, exclude from trend')
        sb.row([(y, 'src'), (h_nat.get(y), 'src', lib.FMT_INT),
                (s_nat.get(y), 'src', lib.FMT_INT),
                (f'=B{rn}+C{rn}', 'fml', lib.FMT_INT),
                ('n/a' if i == 0 else (f'=B{rn}/B{rn - 1}-1', 'fml',
                                       lib.FMT_PCT1)),
                ('n/a' if i == 0 else (f'=C{rn}/C{rn - 1}-1', 'fml',
                                       lib.FMT_PCT1)),
                (flag, 'note' if y > 2024 else 'text'),
                None, None, None, None, None, ('GOV', 'note')])
    a1 = sb.r
    r_2023 = a0 + years.index(2023)
    r_2024 = a0 + years.index(2024)
    sb.row([('CAGR 2016>2024', 'label'),
            (lib.cagr_formula(f'B{r_2024}', f'B{a0}', 8), 'fml', lib.FMT_PCT1),
            (lib.cagr_formula(f'C{r_2024}', f'C{a0}', 8), 'fml', lib.FMT_PCT1),
            (lib.cagr_formula(f'D{r_2024}', f'D{a0}', 8), 'fml', lib.FMT_PCT1),
            ('8-year window ending 2024; 2025 excluded (flag above)', 'note'),
            None, None, None, None, None, None, None, ('DERIVED', 'note')])
    r_cagr = sb.r
    sb.row([('Avg/yr 2022-2024', 'label'),
            (f'=AVERAGE(B{a0 + 6}:B{r_2024})', 'fml', lib.FMT_INT),
            (f'=AVERAGE(C{a0 + 6}:C{r_2024})', 'fml', lib.FMT_INT),
            (f'=AVERAGE(D{a0 + 6}:D{r_2024})', 'fml', lib.FMT_INT),
            None, None, None, None, None, None, None, None,
            ('DERIVED', 'note')])
    sb.note('2025 flag: the extract (2026.04.01) shows 2025 at 39 hospital / '
            '254 SNF CHOWs vs 101 / 708 in 2024. CHOW records post with '
            'processing lag, so the 2025 counts are treated as still accreting '
            '- never trended, and excluded from the CAGR window. Hospital '
            'CHOWs are volatile year to year (38 in 2022, 127 in 2019); the '
            'SNF series is the deeper, steadier consolidation signal '
            '(244 > 882 events/yr 2016>2023).')
    lib.add_chart(ws, f'N{a0}', 'SNF CHOW events per year',
                  f'CHOW_Consolidation!$A${a0}:$A${a1}',
                  [('SNF CHOWs', f'CHOW_Consolidation!$C${a0}:$C${a1}')],
                  kind='line', y_fmt='#,##0')
    lib.add_chart(ws, f'X{a0}', 'Hospital CHOW events per year',
                  f'CHOW_Consolidation!$A${a0}:$A${a1}',
                  [('Hospital CHOWs', f'CHOW_Consolidation!$B${a0}:$B${a1}')],
                  kind='line', y_fmt='#,##0')

    # Panel B: hospital state x year matrix
    sb.blank()
    sb.banner('Panel B. Hospital CHOWs by state x year (49 states with events; '
              'blank = no CHOW recorded that year)')
    sb.headers(['State'] + [str(y) for y in years] + ['Total 16-25', 'Basis'],
               height=15)
    hb0 = sb.r + 1
    h_order = sorted(h_st, key=lambda s: (-sum(h_st[s].values()), s))
    for st in h_order:
        rn = sb.r + 1
        sb.row([(st, 'src')] +
               [((h_st[st][y], 'src', lib.FMT_INT) if y in h_st[st] else None)
                for y in years] +
               [(f'=SUM(B{rn}:K{rn})', 'fml', lib.FMT_INT), ('GOV', 'note')])
    hb1 = sb.r
    rn = sb.r + 1
    sb.row([('All states', 'label')] +
           [(f'=SUM({c}{hb0}:{c}{hb1})', 'fml', lib.FMT_INT)
            for c in 'BCDEFGHIJK'] +
           [(f'=SUM(L{hb0}:L{hb1})', 'fml', lib.FMT_INT), ('DERIVED', 'note')])
    h_tot = sb.r
    sb.row([('Check vs report', 'label'),
            (f'=IF(L{h_tot}={h_rep["total_chows"]},"MATCH - report JSON '
             f'total_chows = {h_rep["total_chows"]}","MISMATCH")', 'fml'),
            None, None, None, None, None, None, None, None, None,
            (h_rep['total_chows'], 'src', lib.FMT_INT), ('GOV', 'note')])
    h_chk = sb.r
    lib.add_chart(ws, f'N{hb0}', 'Top-10 states, hospital CHOWs 2016-2025',
                  f'CHOW_Consolidation!$A${hb0}:$A${hb0 + 9}',
                  [('Hospital CHOWs 2016-25',
                    f'CHOW_Consolidation!$L${hb0}:$L${hb0 + 9}')],
                  kind='bar', height=10)

    # Panel C: SNF state x year matrix
    sb.blank()
    sb.banner('Panel C. SNF CHOWs by state x year (51 states with events; '
              'blank = no CHOW recorded that year)')
    sb.headers(['State'] + [str(y) for y in years] + ['Total 16-25', 'Basis'],
               height=15)
    sb0 = sb.r + 1
    s_order = sorted(s_st, key=lambda s: (-sum(s_st[s].values()), s))
    for st in s_order:
        rn = sb.r + 1
        sb.row([(st, 'src')] +
               [((s_st[st][y], 'src', lib.FMT_INT) if y in s_st[st] else None)
                for y in years] +
               [(f'=SUM(B{rn}:K{rn})', 'fml', lib.FMT_INT), ('GOV', 'note')])
    sb1 = sb.r
    rn = sb.r + 1
    sb.row([('All states', 'label')] +
           [(f'=SUM({c}{sb0}:{c}{sb1})', 'fml', lib.FMT_INT)
            for c in 'BCDEFGHIJK'] +
           [(f'=SUM(L{sb0}:L{sb1})', 'fml', lib.FMT_INT), ('DERIVED', 'note')])
    s_tot = sb.r
    sb.row([('Check vs report', 'label'),
            (f'=IF(L{s_tot}={s_rep["total_chows"]},"MATCH - report JSON '
             f'total_chows = {s_rep["total_chows"]}","MISMATCH")', 'fml'),
            None, None, None, None, None, None, None, None, None,
            (s_rep['total_chows'], 'src', lib.FMT_INT), ('GOV', 'note')])
    s_chk = sb.r
    lib.add_chart(ws, f'N{sb0}', 'Top-10 states, SNF CHOWs 2016-2025',
                  f'CHOW_Consolidation!$A${sb0}:$A${sb0 + 9}',
                  [('SNF CHOWs 2016-25',
                    f'CHOW_Consolidation!$L${sb0}:$L${sb0 + 9}')],
                  kind='bar', height=10)
    sb.note('Extraction: vendored rcm_mc/data/vendor/hospital_chow/ and '
            'snf_chow/ {national,state}_year.csv + report JSONs (extracts '
            'Hospital_CHOW_2026.04.01 / SNF_CHOW_2026.04.01, ingested '
            '2026-05-25, facility identifiers dropped). State x year sums '
            'reconcile exactly to the national series and to the report-JSON '
            'totals (check rows above). Why it matters for IFT: every CHOW is '
            'a repricing/rebid moment for transport contracts, and the SNF '
            'series (7x the hospital count) sits on the discharge leg of the '
            'interfacility book.')

    facts += [
        {'metric': 'Hospital CHOW events, 2016-2025 total', 'year': 2025,
         'value_ref': f'CHOW_Consolidation!L{h_tot}', 'unit': 'events',
         'basis': 'GOV', 'tier': 'A', 'source_keys': ['hospital_chow'],
         'locator': 'Hospital_CHOW_2026.04.01, sum of state x year matrix',
         'lives_on': 'CHOW_Consolidation',
         'cross_check': 'Matches report JSON total_chows 755 (check row); '
                        'state sums = national series exactly'},
        {'metric': 'SNF CHOW events, 2016-2025 total', 'year': 2025,
         'value_ref': f'CHOW_Consolidation!L{s_tot}', 'unit': 'events',
         'basis': 'GOV', 'tier': 'A', 'source_keys': ['snf_chow'],
         'locator': 'SNF_CHOW_2026.04.01, sum of state x year matrix',
         'lives_on': 'CHOW_Consolidation',
         'cross_check': 'Matches report JSON total_chows 5,141 (check row); '
                        '6.8x the hospital CHOW count'},
        {'metric': 'SNF CHOWs, peak year 2023', 'year': 2023,
         'value_ref': f'CHOW_Consolidation!C{r_2023}', 'unit': 'events',
         'basis': 'GOV', 'tier': 'A', 'source_keys': ['snf_chow'],
         'locator': 'National series, year 2023',
         'lives_on': 'CHOW_Consolidation',
         'cross_check': '3.6x the 2016 level (244) - post-acute ownership '
                        'churn accelerated through 2023'},
        {'metric': 'Hospital CHOWs, 2024', 'year': 2024,
         'value_ref': f'CHOW_Consolidation!B{r_2024}', 'unit': 'events',
         'basis': 'GOV', 'tier': 'A', 'source_keys': ['hospital_chow'],
         'locator': 'National series, year 2024',
         'lives_on': 'CHOW_Consolidation',
         'cross_check': 'Volatile series: 38 (2022) to 127 (2019); companion '
                        'to the Kaufman Hall M&A series on '
                        'Growth_Evidence_Registry (announced deals vs '
                        'recorded provider-agreement CHOWs)'},
        {'metric': 'SNF CHOW CAGR 2016>2024', 'year': 2024,
         'value_ref': f'CHOW_Consolidation!C{r_cagr}', 'unit': '%/yr',
         'basis': 'DERIVED', 'tier': 'A', 'source_keys': ['snf_chow'],
         'locator': '(2024/2016)^(1/8)-1 live formula; 2025 excluded '
                    '(partial accrual flag)',
         'lives_on': 'CHOW_Consolidation',
         'cross_check': '244 > 708 events/yr; approx +14%/yr'},
        {'metric': 'Hospital CHOW CAGR 2016>2024', 'year': 2024,
         'value_ref': f'CHOW_Consolidation!B{r_cagr}', 'unit': '%/yr',
         'basis': 'DERIVED', 'tier': 'A', 'source_keys': ['hospital_chow'],
         'locator': '(2024/2016)^(1/8)-1 live formula; 2025 excluded',
         'lives_on': 'CHOW_Consolidation',
         'cross_check': '60 > 101 events/yr; approx +6.7%/yr on a volatile '
                        'base - read with the YoY column'},
        {'metric': 'Top state by SNF CHOWs 2016-2025 (Texas)', 'year': 2025,
         'value_ref': f'CHOW_Consolidation!L{sb0}', 'unit': 'events',
         'basis': 'DERIVED', 'tier': 'A', 'source_keys': ['snf_chow'],
         'locator': 'State matrix row 1 (sorted by total), TX',
         'lives_on': 'CHOW_Consolidation',
         'cross_check': 'TX 697 > CA 393 > OH 310'},
    ]

    # ── Excluded (deliberately kept out) ────────────────────────────────────
    excluded += [
        {'figure': 'US ambulance provider census "~13,000 providers"',
         'value': '~13,000', 'source_label': 'AAA (American Ambulance '
         'Association) census, cited unpinned in RCM_MC/docs/'
         'PEDESK_HEALTHCARE_VERTICALS_LIFE_SCIENCES.md section 9',
         'why_excluded': 'No named AAA document/year; would sit next to the '
                         'PECOS 10,465 as a competing universe without a '
                         'traceable citation',
         'what_would_make_citable': 'Pin the specific AAA census publication '
                                    'and year, then carry both universes '
                                    'side by side'},
        {'figure': '"About 4 in 5 ambulance providers bill under 1,000 '
                   'Medicare-billable trips/yr"',
         'value': '~80% of providers', 'source_label': 'Same unpinned doc '
         'block (AAA/GAO class named, no document)',
         'why_excluded': 'Fragmentation-share claim without a locatable '
                         'source; PECOS/MUP tabs carry the sourced '
                         'fragmentation evidence instead',
         'what_would_make_citable': 'Locate the AAA/GAO source table; or '
                                    'derive from a MUP by-provider pull '
                                    '(dataset documented in CLAIMS_RECIPE)'},
        {'figure': '"80%+ of NE ambulance agencies are all-volunteer"',
         'value': '>80%', 'source_label': 'Nebraska state EMS assessment, '
         'referenced in ift_npi_landscape.summary() read text',
         'why_excluded': 'The assessment document is named by class, not '
                         'pinned; the NPPES tab carries the measured '
                         'municipal/fire/volunteer share (82% of NE org NPIs) '
                         'instead',
         'what_would_make_citable': 'Pin the Nebraska EMS system assessment '
                                    '(publisher, year, table)'},
        {'figure': 'CHOW CAGR computed over 2016-2025 (including 2025)',
         'value': 'hospital -4.7%/yr, SNF +0.5%/yr (window ending 2025)',
         'source_label': 'CMS CHOW files, extract 2026.04.01',
         'why_excluded': '2025 counts (39 hospital / 254 SNF) are partial '
                         'accruals in the 2026.04.01 extract - CHOW records '
                         'post with processing lag; trending across the break '
                         'would fabricate a decline',
         'what_would_make_citable': 'Re-pull a later extract (2027 vintage) '
                                    'and confirm 2025 counts are final'},
    ]

    return {'facts': facts, 'sources': sources, 'excluded': excluded,
            'meta': {'notes': 'All three tabs vendored-file based (zero '
                              'network at build). PECOS national 10,465 '
                              're-verified live 2026-07-10 (cache '
                              'pecos_stats_check.json). NPPES roster rows: '
                              f'{len(reg)}. CHOW state sums reconcile to '
                              'national and report JSONs exactly.',
                     'row_counts': {s['name']: wb[s['name']].max_row
                                    for s in SHEETS}}}
