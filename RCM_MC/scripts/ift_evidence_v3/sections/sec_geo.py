"""Group G — Geography & market structure.

Tabs: Metro_Structure_20 (ift_geo 20-metro SOURCED facility grid + rollup),
County_Demography (ift_mmt 22 GOV county rows + the 2020->2024 CAGR series),
CBSA_Crosswalk_Reference (OMB Bulletin 23-01 national county->CBSA listing),
HPSA_Rural_Designations (HRSA PC-HPSA state table + rural add-on framing).
"""
import csv
import os
import sys

sys.path.insert(0, '/home/user/RCM/RCM_MC')
sys.path.insert(0, '/home/user/RCM')

PURPLE = 'FF7A5195'

SHEETS = [
    {'name': 'Metro_Structure_20', 'tab_color': PURPLE},
    {'name': 'County_Demography', 'tab_color': PURPLE},
    {'name': 'CBSA_Crosswalk_Reference', 'tab_color': PURPLE},
    {'name': 'HPSA_Rural_Designations', 'tab_color': PURPLE},
]

VENDOR = '/home/user/RCM/RCM_MC/rcm_mc/data/vendor'
FOOTPRINT = ('NE', 'OH', 'WI', 'IA', 'KS', 'IN', 'KY', 'MO', 'MN', 'VA', 'WY')
FP_SEARCH = ' ' + ' '.join(FOOTPRINT) + ' '   # " NE OH ... WY " for SEARCH()

# ANSI FIPS state-numeric -> USPS postal (incl. territories in the crosswalk)
FIPS_STATE = {
    '01': 'AL', '02': 'AK', '04': 'AZ', '05': 'AR', '06': 'CA', '08': 'CO',
    '09': 'CT', '10': 'DE', '11': 'DC', '12': 'FL', '13': 'GA', '15': 'HI',
    '16': 'ID', '17': 'IL', '18': 'IN', '19': 'IA', '20': 'KS', '21': 'KY',
    '22': 'LA', '23': 'ME', '24': 'MD', '25': 'MA', '26': 'MI', '27': 'MN',
    '28': 'MS', '29': 'MO', '30': 'MT', '31': 'NE', '32': 'NV', '33': 'NH',
    '34': 'NJ', '35': 'NM', '36': 'NY', '37': 'NC', '38': 'ND', '39': 'OH',
    '40': 'OK', '41': 'OR', '42': 'PA', '44': 'RI', '45': 'SC', '46': 'SD',
    '47': 'TN', '48': 'TX', '49': 'UT', '50': 'VT', '51': 'VA', '53': 'WA',
    '54': 'WV', '55': 'WI', '56': 'WY', '60': 'AS', '66': 'GU', '69': 'MP',
    '72': 'PR', '78': 'VI'}


def build(wb, ctx):
    lib = ctx['lib']
    accessed = ctx['accessed']
    facts, sources, excluded, notes = [], [], [], []

    from rcm_mc.market_reports import ift_geo, ift_mmt

    # ── Sources (integrator assigns S-IDs; keys stable) ─────────────────────
    sources += [
        {'key': 'pdc_geo_rolls', 'publisher': 'CMS',
         'document': 'Care Compare / Provider Data Catalog provider rolls: '
                     'Hospital General Information (geocoded via US Census '
                     'Geocoder 2026-05-23); NH_ProviderInfo (2026-04-01); IRF '
                     'Compare (2026-02-13); LTCH Compare (2026-02-13); Hospice '
                     'General Information yc9t-dgbk (2026-05-23); Home Health '
                     'Agencies 6jpm-sxkc (2026-05-23); DFC_FACILITY (2026-03-25)',
         'vintage': 'Snapshots Feb-May 2026 (per-roll dates above)',
         'locator': 'Vendored rcm_mc/data CSVs (hospital_coords.csv, '
                    'snf/irf/ltch/hospice/home_health/dialysis _providers.csv), '
                    'each row carrying source + source_date; city+state filtered '
                    'to the 20 metro definitions by ift_geo.metro_structure()',
         'supplies': 'Per-metro facility counts: hospitals, SNFs + certified '
                     'beds, IRF, LTCH + beds, hospice, home health, dialysis + '
                     'stations - the origin/destination node structure',
         'url': 'https://data.cms.gov/provider-data/',
         'tier': 'B', 'accessed': accessed, 'powers': ['Metro_Structure_20']},
        {'key': 'hcris_panel', 'publisher': 'CMS',
         'document': 'Healthcare Cost Report Information System (HCRIS), '
                     'hospital cost reports (Form CMS-2552-10, HOSP10 bundles)',
         'vintage': 'FY2020-FY2022 panel; latest filed report per CCN '
                    '(status-rank dedup: audited > settled > submitted)',
         'locator': 'Vendored parquet via rcm_mc/data/hcris.py; fields beds, '
                    'total_patient_days, bed_days_available, joined to the '
                    'metro hospital rolls by CCN',
         'supplies': 'Metro staffed beds, patient days, bed-days available; '
                     'the occupancy inputs',
         'url': 'https://www.cms.gov/data-research/statistics-trends-reports/'
                'cost-reports',
         'tier': 'B', 'accessed': accessed, 'powers': ['Metro_Structure_20']},
        {'key': 'census2020_county', 'publisher': 'U.S. Census Bureau',
         'document': '2020 Decennial Census, county resident population '
                     '(P.L. 94-171 / DEC counts)',
         'vintage': 'April 1, 2020',
         'locator': 'County totals carried per-record in '
                    'rcm_mc/market_reports/ift_mmt.MMT_COUNTIES (source label '
                    '"GOV - U.S. Census 2020 Decennial (county population)")',
         'supplies': '2020 population for the 22 MMT footprint counties',
         'url': 'https://data.census.gov/',
         'tier': 'B', 'accessed': accessed, 'powers': ['County_Demography']},
        {'key': 'census_v2024_est', 'publisher': 'U.S. Census Bureau',
         'document': 'Vintage-2024 county population estimates (CO-EST2024 / '
                     'QuickFacts coverage); Platte NE from 2024 ACS 5-year',
         'vintage': 'July 1, 2024 estimates, captured 2026-07-10',
         'locator': 'ift_mmt.POP_2024_EST (13 counties captured from '
                    'QuickFacts/CO-EST2024 coverage; RE-VERIFY queue until '
                    're-pulled from api.census.gov - pull spec in '
                    'docs/IFT_REDESIGN_AUDIT.md)',
         'supplies': '2024 county population estimates for 13 of 22 footprint '
                     'counties - the only true population time series here',
         'url': 'https://www.census.gov/programs-surveys/popest.html',
         'tier': 'B', 'accessed': accessed, 'powers': ['County_Demography']},
        {'key': 'omb_cbsa_2023', 'publisher': 'U.S. Census Bureau / OMB',
         'document': 'OMB Bulletin No. 23-01 - 2023 Core-Based Statistical '
                     'Area delineations (list1_2023.xlsx)',
         'vintage': 'July 2023 (effective 2023-07-21); vendored 2026-05-26',
         'locator': 'rcm_mc/data/vendor/cbsa_crosswalk/cbsa_county_crosswalk.csv '
                    '(1,915 county rows) + cbsa_crosswalk_meta.json; registry '
                    'row "cbsa_crosswalk" in vendor/source_registry.csv',
         'supplies': 'The national county->CBSA crosswalk: county FIPS, CBSA '
                     'code/title, metro/micro flag, central/outlying flag',
         'url': 'https://www2.census.gov/programs-surveys/metro-micro/'
                'geographies/reference-files/2023/delineation-files/'
                'list1_2023.xlsx',
         'tier': 'A', 'accessed': accessed,
         'powers': ['CBSA_Crosswalk_Reference', 'County_Demography']},
        {'key': 'chr_county_names', 'publisher':
            'County Health Rankings & Roadmaps (UW Population Health '
            'Institute) / U.S. Census Bureau',
         'document': 'County demographics file (Census/ACS delivered via CHR), '
                     'used here ONLY for the county_fips -> county name lookup',
         'vintage': '2024 release; vendored 2026-05-25',
         'locator': 'rcm_mc/data/vendor/county_demographics/'
                    'county_demographics.csv (3,143 rows; registry row '
                    '"chr_county_demographics"); fields county_fips, '
                    'county_name',
         'supplies': 'County display names for the crosswalk listing (the '
                     'vendored OMB extract carries FIPS only)',
         'url': 'https://www.countyhealthrankings.org/',
         'tier': 'A', 'accessed': accessed,
         'powers': ['CBSA_Crosswalk_Reference']},
        {'key': 'hrsa_hpsa_pc', 'publisher': 'HRSA',
         'document': 'HRSA Data Warehouse - Health Professional Shortage '
                     'Areas (HPSA), Primary Care discipline, designated, '
                     'aggregated to state',
         'vintage': 'Snapshot 2026-05-25 (19,696 designated PC-HPSA rows '
                    'aggregated; hrsa_hpsa_report.json)',
         'locator': 'rcm_mc/data/vendor/hrsa/hrsa_hpsa_pc_by_state.csv (60 '
                    'state/territory rows); registry row "hrsa_hpsa_pc" in '
                    'vendor/source_registry.csv',
         'supplies': 'Designated primary-care HPSA counts + median/max HPSA '
                     'scores by state - the shortage-geography table',
         'url': 'https://data.hrsa.gov/',
         'tier': 'A', 'accessed': accessed,
         'powers': ['HPSA_Rural_Designations']},
        {'key': 'ssa1834l_addons', 'publisher': 'U.S. Congress / CMS',
         'document': 'Social Security Act sec. 1834(l)(12)(A) & (l)(13)(A); '
                     '42 CFR 414.610(c)(1)(ii) and (c)(5)(ii); extension: '
                     'Consolidated Appropriations Act, 2026, sec. 6203 '
                     '(Senate Finance section-by-section)',
         'vintage': 'Add-ons extended through December 31, 2027',
         'locator': 'Statute/reg sections as named; carried from repo '
                    'citations (ift_service_levels / ift_growth_evidence, '
                    'flagged needs_reverify in-module)',
         'supplies': 'The +2% urban / +3% rural / +22.6% super-rural ground '
                     'ambulance add-ons and their sunset date',
         'url': 'https://www.finance.senate.gov/imo/media/doc/'
                'consolidated_appropriations_act_2026_section-by-section.pdf',
         'tier': 'B', 'accessed': accessed,
         'powers': ['HPSA_Rural_Designations']},
        {'key': 'ecfr_414_605', 'publisher': 'eCFR (GPO)',
         'document': '42 CFR 414.605 - Ambulance Fee Schedule definitions '
                     '("rural area" = outside an MSA, or a rural census tract '
                     'under the Goldsmith modification)',
         'vintage': 'Current eCFR',
         'locator': '42 CFR 414.605, definition of "rural area"',
         'supplies': 'The payment-side rural definition the add-ons key off '
                     '(ZIP-of-origin based)',
         'url': 'https://www.ecfr.gov/current/title-42/chapter-IV/'
                'subchapter-B/part-414/subpart-H/section-414.605',
         'tier': 'B', 'accessed': accessed,
         'powers': ['HPSA_Rural_Designations', 'CBSA_Crosswalk_Reference']},
        {'key': 'medpac_jun26_ch6', 'publisher': 'MedPAC',
         'document': 'June 2026 Report to Congress, Ch. 6 (ground ambulance); '
                     'CBO score of the CAA 2026 sec. 6203 extension',
         'vintage': 'June 2026',
         'locator': 'Ch. 6 discussion of the temporary add-ons ("did not have '
                     'an underlying empirical basis"); ~$197M CBO score via '
                     'Senate Finance summary - both carried from '
                     'ift_service_levels (GOV-labeled, not reopened)',
         'supplies': 'The policy-durability read on the rural add-ons',
         'url': 'https://www.medpac.gov/wp-content/uploads/2026/06/'
                'Jun26_Ch6_MedPAC_Report_To_Congress_SEC.pdf',
         'tier': 'B', 'accessed': accessed,
         'powers': ['HPSA_Rural_Designations']},
    ]

    # ════════════════════════════════════════════════════════════════════════
    # Tab 1 — Metro_Structure_20
    # ════════════════════════════════════════════════════════════════════════
    metros = ift_geo.all_metros()
    roll = ift_geo.footprint_rollup()

    ws = wb.create_sheet('Metro_Structure_20')
    NC1 = 22
    sb = lib.SheetBuilder(
        ws, NC1,
        col_widths=[20, 17, 7, 9, 9, 10, 12, 12, 10, 7, 11, 6, 6, 9, 8, 8, 8,
                    9, 10, 8, 20, 46],
        tab_color=PURPLE)
    sb.title('The 20-metro footprint: sourced facility structure per metro')
    sb.subtitle(
        'The question: how many transfer origins (hospitals) and destinations '
        '(SNF / IRF / LTCH / hospice / home health / dialysis) physically '
        'exist in each of the 20 target-operator metros - counted from CMS '
        'provider rolls, not asserted? Counts are vendored Care Compare '
        'snapshots (Feb-May 2026) city+state-filtered to each metro '
        'definition; staffed beds / patient days join HCRIS cost reports '
        '(FY2020-22 panel, latest per CCN) by CCN. Occupancy, post-acute and '
        'node totals are live formulas. Anchor systems, named operators and '
        'insource reads (PUBLIC-WEB) are deliberately NOT on this tab.')
    sb.blank()
    sb.banner('Panel A. Facility structure by metro (CMS provider rolls + '
              'HCRIS join)')
    sb.headers(['Metro', 'Region', 'States', 'Hospitals', 'w/ HCRIS row',
                'HCRIS staffed beds', 'HCRIS patient days',
                'HCRIS bed-days available', 'Occupancy (=G/H)', 'SNFs',
                'SNF certified beds', 'IRF', 'LTCH', 'LTCH beds', 'Hospice',
                'Home health', 'Dialysis', 'Dialysis stations',
                'Post-acute dest. (=J+L+M)', 'O/D nodes (=D+S)',
                'Density tier (module)', 'Data caveat (verbatim from module)'])
    a0 = sb.r + 1
    for m in metros:
        r = sb.r + 1
        sb.row([
            (m.name, 'src'), (m.region_label, 'src'),
            ('+'.join(m.states), 'src'),
            (m.n_hospitals, 'src', lib.FMT_INT),
            (m.n_hospitals_with_hcris, 'src', lib.FMT_INT),
            (m.hcris_beds, 'src', lib.FMT_INT),
            (m.hcris_patient_days, 'src', lib.FMT_INT),
            (m.hcris_bed_days_available, 'src', lib.FMT_INT),
            (f'=IF(H{r}>0,G{r}/H{r},"n/a")', 'fml', lib.FMT_PCT1),
            (m.n_snf, 'src', lib.FMT_INT),
            (m.snf_beds, 'src', lib.FMT_INT),
            (m.n_irf, 'src', lib.FMT_INT),
            (m.n_ltch, 'src', lib.FMT_INT),
            (m.ltch_beds, 'src', lib.FMT_INT),
            (m.n_hospice, 'src', lib.FMT_INT),
            (m.n_home_health, 'src', lib.FMT_INT),
            (m.n_dialysis, 'src', lib.FMT_INT),
            (m.dialysis_stations, 'src', lib.FMT_INT),
            (f'=J{r}+L{r}+M{r}', 'fml', lib.FMT_INT),
            (f'=D{r}+S{r}', 'fml', lib.FMT_INT),
            (m.density_tier, 'src'),
            ('; '.join(m.data_caveats) if m.data_caveats else '', 'note'),
        ], wrap=True)
    a1 = sb.r

    # python-side sanity: formula-recomputed post-acute vs module field
    for m in metros:
        if m.n_postacute_destinations != (m.n_snf + m.n_irf + m.n_ltch):
            notes.append(f'postacute identity BROKE for {m.name}')
        if m.n_nodes != m.n_hospitals + m.n_postacute_destinations:
            notes.append(f'node identity BROKE for {m.name}')

    sb.blank()
    sb.banner('Panel B. Region roll-up - live formulas over Panel A')
    sb.headers(['Region', 'Metros', '', 'Hospitals', '', 'HCRIS staffed beds',
                '', '', '', 'SNFs', 'SNF certified beds', '', '', '', '', '',
                '', '', 'Post-acute dest.', '', 'Basis'])
    b0 = sb.r + 1
    region_labels = []
    for m in metros:
        if m.region_label not in region_labels:
            region_labels.append(m.region_label)
    for lab in region_labels:
        r = sb.r + 1
        sb.row([
            (lab, 'label'),
            (f'=COUNTIF($B${a0}:$B${a1},$A{r})', 'fml', lib.FMT_INT), None,
            (f'=SUMIF($B${a0}:$B${a1},$A{r},D${a0}:D${a1})', 'fml',
             lib.FMT_INT), None,
            (f'=SUMIF($B${a0}:$B${a1},$A{r},F${a0}:F${a1})', 'fml',
             lib.FMT_INT), None, None, None,
            (f'=SUMIF($B${a0}:$B${a1},$A{r},J${a0}:J${a1})', 'fml',
             lib.FMT_INT),
            (f'=SUMIF($B${a0}:$B${a1},$A{r},K${a0}:K${a1})', 'fml',
             lib.FMT_INT), None, None, None, None, None, None, None,
            (f'=SUMIF($B${a0}:$B${a1},$A{r},S${a0}:S${a1})', 'fml',
             lib.FMT_INT), None,
            ('DERIVED (over SOURCED rows)', 'note'),
        ])
    b1 = sb.r

    sb.blank()
    sb.banner('Panel C. Footprint totals + national context (denominators '
              'from the same rolls)')
    r = sb.r + 1
    sb.row([('Footprint total (20 metros) - live SUM', 'label'), None, None,
            (f'=SUM(D{a0}:D{a1})', 'fml', lib.FMT_INT),
            (f'=SUM(E{a0}:E{a1})', 'fml', lib.FMT_INT),
            (f'=SUM(F{a0}:F{a1})', 'fml', lib.FMT_INT),
            (f'=SUM(G{a0}:G{a1})', 'fml', lib.FMT_INT),
            (f'=SUM(H{a0}:H{a1})', 'fml', lib.FMT_INT),
            (f'=IF(H{r}>0,G{r}/H{r},"n/a")', 'fml', lib.FMT_PCT1),
            (f'=SUM(J{a0}:J{a1})', 'fml', lib.FMT_INT),
            (f'=SUM(K{a0}:K{a1})', 'fml', lib.FMT_INT),
            (f'=SUM(L{a0}:L{a1})', 'fml', lib.FMT_INT),
            (f'=SUM(M{a0}:M{a1})', 'fml', lib.FMT_INT),
            (f'=SUM(N{a0}:N{a1})', 'fml', lib.FMT_INT),
            (f'=SUM(O{a0}:O{a1})', 'fml', lib.FMT_INT),
            (f'=SUM(P{a0}:P{a1})', 'fml', lib.FMT_INT),
            (f'=SUM(Q{a0}:Q{a1})', 'fml', lib.FMT_INT),
            (f'=SUM(R{a0}:R{a1})', 'fml', lib.FMT_INT),
            (f'=SUM(S{a0}:S{a1})', 'fml', lib.FMT_INT),
            (f'=SUM(T{a0}:T{a1})', 'fml', lib.FMT_INT), None,
            ('DERIVED', 'note')])
    r_tot = sb.r
    sb.row([('National universe (same vendored rolls, full US)', 'label'),
            None, None,
            (roll.n_hospitals_national, 'src', lib.FMT_INT), None, None, None,
            None, None,
            (roll.n_snf_national, 'src', lib.FMT_INT),
            (roll.snf_beds_national, 'src', lib.FMT_INT),
            None, None, None, None, None, None, None, None, None, None,
            ('SOURCED (roll totals)', 'note')])
    r_nat = sb.r
    sb.row([('Footprint 11-STATE totals (NE OH WI IA KS IN KY MO MN VA WY)',
             'label'), None, None,
            (roll.footprint_state_hospitals, 'src', lib.FMT_INT), None, None,
            None, None, None, None,
            (roll.footprint_state_snf_beds, 'src', lib.FMT_INT),
            None, None, None, None, None, None, None, None, None, None,
            ('SOURCED (roll totals)', 'note')])
    r_st = sb.r
    sb.row([('20-metro share of national', 'label'), None, None,
            (f'=D{r_tot}/D{r_nat}', 'fml', lib.FMT_PCT1), None, None, None,
            None, None,
            (f'=J{r_tot}/J{r_nat}', 'fml', lib.FMT_PCT1),
            (f'=K{r_tot}/K{r_nat}', 'fml', lib.FMT_PCT1),
            None, None, None, None, None, None, None, None, None, None,
            ('DERIVED', 'note')])
    r_mshare = sb.r
    sb.row([('Footprint-STATE share of national', 'label'), None, None,
            (f'=D{r_st}/D{r_nat}', 'fml', lib.FMT_PCT1), None, None, None,
            None, None, None,
            (f'=K{r_st}/K{r_nat}', 'fml', lib.FMT_PCT1),
            None, None, None, None, None, None, None, None, None, None,
            ('DERIVED', 'note')])
    r_sshare = sb.r

    sb.blank()
    sb.note('Vintages (each vendored row carries source + source_date): '
            'hospitals = CMS Hospital General Information addresses geocoded '
            'via US Census Geocoder, 2026-05-23; SNF = NH_ProviderInfo '
            '2026-04-01; IRF + LTCH = Compare files 2026-02-13; hospice = '
            'yc9t-dgbk 2026-05-23; home health = 6jpm-sxkc 2026-05-23; '
            'dialysis = DFC_FACILITY 2026-03-25; beds/days = HCRIS FY2020-22 '
            'panel, latest filed report per CCN.')
    sb.note('Undercount caveats (travel with the counts): Nebraska Medicine/'
            'UNMC (CCN 280048) and Ascension Via Christi St. Francis + St. '
            'Joseph (Wichita) are ABSENT from the geocoded hospital roll - '
            'Omaha and Wichita hospital/bed counts are understated. City-list '
            'filtering misses suburbs not on each metro list. 152 of 166 '
            'footprint hospitals matched an HCRIS row (federal/VA, '
            "children's, psych and specialty filers are absent), so HCRIS "
            'bed/day sums are conservative floors. Columbus (OH) home-health '
            'count (288) is statewide HQ-address clustering - directional '
            'only. Louisville hospice count (1) reflects suburb-address '
            'filing - an undercount.')
    sb.note('Module-caveat correction found during this build: the Northern '
            'Virginia caveat text ("zero LTCH in NoVA") predates the Feb 2026 '
            'LTCH roll, which lists 1 (Inova Specialty Hospital, Alexandria; '
            'bed count blank). The count column carries the current roll; the '
            'stale sentence is not reproduced.')
    sb.note('Share-of-national note: Panel C shares on row '
            f'{r_sshare} use footprint-STATE totals (the wider demand pool '
            'the metros sit inside) as numerators, per '
            'ift_geo.footprint_rollup(); the 20-metro share on row '
            f'{r_mshare} uses the metro sums. Both denominators are the full '
            'national rolls (universes differ from AHA hospital counts - '
            'Medicare-certified, geocode-matched only).')
    sb.note('Extraction: rcm_mc/market_reports/ift_geo.py::all_metros() + '
            'footprint_rollup(), run under the project venv (pandas present, '
            f'HCRIS join live), {accessed}. Excluded from this tab: '
            'discharge_base (beds x 53.3 discharges/bed/yr, '
            'ILLUSTRATIVE-with-basis), SAM building blocks and all modeled '
            'SAM/SOM dollars (ift_analytics), and the PUBLIC-WEB anchor-'
            'system / operator / insource-read fields - see '
            'Excluded_Not_Sourced.')

    lib.add_chart(
        ws, f'X{a0}', 'Hospitals (bars, left) and SNF certified beds (line, '
        'right) by metro',
        f'Metro_Structure_20!$A${a0}:$A${a1}',
        [('Hospitals', f'Metro_Structure_20!$D${a0}:$D${a1}')],
        kind='bar', height=12,
        secondary=[('SNF certified beds',
                    f'Metro_Structure_20!$K${a0}:$K${a1}', 'line')])
    lib.add_chart(
        ws, f'X{a0 + 26}', 'HCRIS occupancy by metro (patient days / '
        'bed-days available, FY2020-22 latest per CCN)',
        f'Metro_Structure_20!$A${a0}:$A${a1}',
        [('Occupancy', f'Metro_Structure_20!$I${a0}:$I${a1}')],
        kind='bar', height=12, y_fmt='0%')

    facts += [
        {'metric': 'Footprint hospitals across the 20 target metros',
         'year': 2026, 'value_ref': f'Metro_Structure_20!D{r_tot}',
         'unit': 'hospitals', 'basis': 'DERIVED', 'tier': 'B',
         'source_keys': ['pdc_geo_rolls'],
         'locator': 'SUM over 20 metro rows; geocoded Hospital General '
                    'Information, city+state filtered',
         'lives_on': 'Metro_Structure_20',
         'cross_check': 'footprint_rollup() returns 166; UNMC + Via Christi '
                        'absences make this a floor'},
        {'metric': 'Footprint SNF certified beds across the 20 metros',
         'year': 2026, 'value_ref': f'Metro_Structure_20!K{r_tot}',
         'unit': 'beds', 'basis': 'DERIVED', 'tier': 'B',
         'source_keys': ['pdc_geo_rolls'],
         'locator': 'SUM over 20 metro rows; NH_ProviderInfo 2026-04-01 '
                    'certified beds',
         'lives_on': 'Metro_Structure_20',
         'cross_check': 'footprint_rollup() returns 51,108'},
        {'metric': 'Footprint HCRIS staffed beds across the 20 metros',
         'year': 2026, 'value_ref': f'Metro_Structure_20!F{r_tot}',
         'unit': 'beds', 'basis': 'DERIVED', 'tier': 'B',
         'source_keys': ['hcris_panel', 'pdc_geo_rolls'],
         'locator': 'SUM over 20 metro rows; HCRIS FY2020-22 latest per CCN, '
                    'joined by CCN (152 of 166 hospitals matched - a floor)',
         'lives_on': 'Metro_Structure_20',
         'cross_check': 'footprint_rollup() returns 40,762'},
        {'metric': 'National geocoded hospital roll (denominator)',
         'year': 2026, 'value_ref': f'Metro_Structure_20!D{r_nat}',
         'unit': 'hospitals', 'basis': 'SOURCED', 'tier': 'B',
         'source_keys': ['pdc_geo_rolls'],
         'locator': 'hospital_coords.csv full-US row count (4,630)',
         'lives_on': 'Metro_Structure_20',
         'cross_check': 'Facility_Universe_State counts the same Care Compare '
                        'universe from live pulls; AHA counts ~6,100 (broader '
                        'universe - both stated)'},
        {'metric': 'Footprint-state share of national hospitals (11 states)',
         'year': 2026, 'value_ref': f'Metro_Structure_20!D{r_sshare}',
         'unit': 'share', 'basis': 'DERIVED', 'tier': 'B',
         'source_keys': ['pdc_geo_rolls'],
         'locator': '1,153 footprint-state hospitals / 4,630 national '
                    '(both from the geocoded roll) = 24.9%',
         'lives_on': 'Metro_Structure_20',
         'cross_check': 'Numerator is state-level, not metro-level - stated '
                        'on-sheet'},
        {'metric': 'Footprint-state share of national SNF certified beds',
         'year': 2026, 'value_ref': f'Metro_Structure_20!K{r_sshare}',
         'unit': 'share', 'basis': 'DERIVED', 'tier': 'B',
         'source_keys': ['pdc_geo_rolls'],
         'locator': '347,674 footprint-state SNF beds / 1,569,384 national '
                    '(NH_ProviderInfo 2026-04-01) = 22.2%',
         'lives_on': 'Metro_Structure_20',
         'cross_check': 'National SNF bed base also carried on '
                        'Facility_Universe_State (later snapshot)'},
    ]
    excluded += [
        {'figure': 'Discharge base per metro (HCRIS beds x 53.3 '
                   'discharges/bed/yr)',
         'value': 'e.g. Omaha 75,206',
         'source_label': 'ift_geo.MetroStructure.discharge_base - '
                         'ILLUSTRATIVE-with-basis (module label)',
         'why_excluded': '53.3 = 0.657 occupancy x 365 / 4.5 ALOS is a '
                         'constructed factor, not a published discharge count',
         'what_would_make_citable': 'Metro-level discharges from HCRIS '
                                    'worksheet S-3 or state discharge files'},
        {'figure': 'SAM building blocks / modeled SAM-SOM dollars for the 20 '
                   'metros',
         'value': 'suppressed (incl. MMT SOM $700,686)',
         'source_label': 'ift_geo.footprint_sam_building_blocks() + '
                         'ift_analytics.sam_formula + '
                         'ift_mmt.mmt_serviceable_model()',
         'why_excluded': 'Serviceable-share levers (0.12-0.30) and metro-share '
                         'multipliers are ILLUSTRATIVE per module labels',
         'what_would_make_citable': 'Claims-measured metro volumes (CMS '
                                    'MUP/PSPS pulls at supplier grain) '
                                    'replacing assumed shares'},
        {'figure': 'Anchor systems, named operators, insource reads, moat '
                   'notes per metro',
         'value': 'qualitative (~70 systems, ~60 operators)',
         'source_label': 'ift_geo.MARKETS - PUBLIC-WEB, no per-item citation',
         'why_excluded': 'Embedded stats (e.g. "~77% of county IFT to AMR '
                         '2022", "~34,000 requests/2024") are unverifiable '
                         'in-module',
         'what_would_make_citable': 'Per-claim citations to named public '
                                    'documents (press, contracts, EMS-board '
                                    'minutes)'},
    ]

    # ════════════════════════════════════════════════════════════════════════
    # Tab 2 — County_Demography
    # ════════════════════════════════════════════════════════════════════════
    counties = list(ift_mmt.MMT_COUNTIES)
    growth = ift_mmt.county_growth()
    cbsas = ift_mmt.footprint_cbsas()
    kind_by_code = {c.code: c.kind for c in cbsas}

    ws = wb.create_sheet('County_Demography')
    NC2 = 12
    sb = lib.SheetBuilder(
        ws, NC2,
        col_widths=[15, 6, 8, 10, 26, 8, 17, 15, 13, 13, 13, 44],
        tab_color=PURPLE)
    sb.title('The 22-county MMT footprint: population base and 2020-2024 '
             'growth')
    sb.subtitle(
        'The question: how many people live in the 22 counties (7 CBSAs, '
        'NE+IA) that make up the target operator\'s legacy-core footprint, '
        'and which counties are growing? Population is GOV: 2020 Decennial '
        'Census per county; 2024 is the Census Vintage-2024 estimate where a '
        'published figure was captured (13 of 22 counties - never imputed). '
        'Growth and CAGR are live formulas. County-to-CBSA assignment is OMB '
        'Bulletin 23-01, cross-checked by live COUNTIF against the '
        'CBSA_Crosswalk_Reference tab.')
    sb.blank()
    sb.banner('Panel A. The 22 footprint counties (GOV registry)')
    sb.headers(['County', 'State', 'FIPS', 'CBSA code', 'CBSA title (per '
                'ift_mmt / OMB 2023)', 'MSA / uSA', 'ift_geo metro',
                'Role (module classification)', 'County seat', '',
                'Pop 2020 (Census)', 'Note'])
    a0 = sb.r + 1
    fips_row = {}
    for c in counties:
        r = sb.r + 1
        fips_row[c.fips] = r
        sb.row([
            (c.name, 'src'), (c.state, 'src'), (c.fips, 'src'),
            (c.cbsa_code, 'src'), (c.cbsa_name, 'src'),
            (kind_by_code.get(c.cbsa_code, ''), 'src'),
            (c.metro, 'src'), (c.role, 'text'), (c.seat, 'src'), None,
            (c.pop_2020, 'src', lib.FMT_INT),
            (c.note, 'note'),
        ], wrap=True)
    a1 = sb.r
    r = sb.r + 1
    sb.row([('Footprint total', 'label'),
            None, (f'=COUNTA(C{a0}:C{a1})', 'fml', lib.FMT_INT),
            None, None, None, None, None, None, None,
            (f'=SUM(K{a0}:K{a1})', 'fml', lib.FMT_INT),
            ('DERIVED - 22 counties, pop 1,560,299 expected', 'note')])
    r_ctot = sb.r

    sb.blank()
    sb.banner('Panel B. 2020 -> 2024 growth - the 13 counties with a '
              'published Vintage-2024 estimate (sorted by growth, desc)')
    sb.headers(['County', 'State', 'FIPS', 'Pop 2020 (link, Panel A)',
                'Pop 2024 (Vintage-2024 est.)', 'Growth 2020-2024 (=E/D-1)',
                'CAGR /yr (=(E/D)^(1/4)-1)', 'Trend-eligible?', '', '', '',
                'Note'])
    b0 = sb.r + 1
    for g in growth:
        c = g.county
        r = sb.r + 1
        note = ''
        if c.fips == '31141':
            note = ('2024 figure is the 2024 ACS 5-yr estimate, not '
                    'CO-EST2024 - program mix; treat CAGR as indicative.')
        sb.row([
            (c.name, 'src'), (c.state, 'src'), (c.fips, 'src'),
            (f'=K{fips_row[c.fips]}', 'fml', lib.FMT_INT),
            (g.pop_2024, 'src', lib.FMT_INT),
            (f'=E{r}/D{r}-1', 'fml', lib.FMT_PCT1),
            (lib.cagr_formula(f'E{r}', f'D{r}', 4), 'fml', lib.FMT_PCT2),
            ('YES - single 2-point window, no series break', 'text'),
            None, None, None, (note, 'note'),
        ], wrap=bool(note))
    b1 = sb.r

    sb.note('Basis for the 2024 column (verbatim module label, must travel): '
            '"GOV - Census Vintage-2024 county estimates (captured from '
            'QuickFacts/CO-EST2024 coverage 2026-07-10; RE-VERIFY queue until '
            're-pulled from api.census.gov)". The exact re-pull call is '
            'documented in docs/IFT_REDESIGN_AUDIT.md. 9 of 22 counties have '
            'no captured 2024 figure and are deliberately absent - growth is '
            'never imputed. CAGR window: April 2020 Census Day to July 2024 '
            'estimate, carried as n=4 years (module convention).')

    sb.blank()
    sb.banner('Panel C. CBSA roll-up (7 OMB CBSAs) - live formulas + '
              'crosswalk cross-check')
    sb.headers(['CBSA code', 'CBSA title', 'MSA / uSA', 'ift_geo metro',
                'Footprint counties (COUNTIF Panel A)',
                'Counties in OMB delineation (COUNTIF crosswalk tab)',
                'Composition', 'Pop 2020 (SUMIF Panel A)', '', '', '',
                'Basis'])
    c0 = sb.r + 1
    for cb in cbsas:
        r = sb.r + 1
        sb.row([
            (cb.code, 'src'), (cb.name, 'src'), (cb.kind, 'src'),
            (cb.metro, 'src'),
            (f'=COUNTIF($D${a0}:$D${a1},$A{r})', 'fml', lib.FMT_INT),
            (f"=COUNTIF(CBSA_Crosswalk_Reference!$D:$D,$A{r})", 'link',
             lib.FMT_INT),
            (f'=IF(E{r}=F{r},"complete","PARTIAL")', 'fml'),
            (f'=SUMIF($D${a0}:$D${a1},$A{r},$K${a0}:$K${a1})', 'fml',
             lib.FMT_INT),
            None, None, None,
            ('DERIVED over GOV inputs', 'note'),
        ])
    c1 = sb.r
    r = sb.r + 1
    sb.row([('Total', 'label'), None, None,
            ('7 CBSAs = 3 MSA + 4 uSA', 'text'),
            (f'=SUM(E{c0}:E{c1})', 'fml', lib.FMT_INT),
            (f'=SUM(F{c0}:F{c1})', 'fml', lib.FMT_INT),
            (f'=IF(E{r}=F{r},"footprint = full 7-CBSA composition","gap")',
             'fml'),
            (f'=SUM(H{c0}:H{c1})', 'fml', lib.FMT_INT),
            None, None, None,
            ('DERIVED', 'note')])
    r_cbtot = sb.r
    sb.note('Cross-check: column F counts each CBSA\'s counties in the '
            'vendored OMB Bulletin 23-01 crosswalk (CBSA_Crosswalk_Reference '
            'tab). E=F on every row proves the 22-county footprint is the '
            'COMPLETE OMB composition of all 7 CBSAs - no cherry-picked '
            'counties. Title note: the 2023 delineation file titles the '
            'Omaha CBSA "Omaha, NE-IA"; ift_mmt carries the longer '
            '"Omaha-Council Bluffs, NE-IA" label - same CBSA 36540.')
    sb.note('Excluded from this tab (see Excluded_Not_Sourced): senior-share '
            'tier assumptions (0.145/0.155/0.205) and every pop_65+ column '
            'built on them (module-labeled ILLUSTRATIVE); per-county demand '
            'missions/dollars (the derived demand floor lives with its '
            'derivation chain, not here). Role column is the module\'s '
            'core/suburban/rural-feeder classification - a framework label, '
            'not data. Extraction: ift_mmt.MMT_COUNTIES / POP_2024_EST / '
            f'county_growth() / footprint_cbsas(), {accessed}.')

    lib.add_chart(
        ws, f'N{b0}', 'County population CAGR 2020-2024 (Vintage-2024 '
        'estimates, 13 counties)',
        f'County_Demography!$A${b0}:$A${b1}',
        [('CAGR /yr', f'County_Demography!$G${b0}:$G${b1}')],
        kind='bar', height=11, y_fmt='0.0%')
    lib.add_chart(
        ws, f'N{b0 + 24}', '2020 Census population by footprint CBSA',
        f'County_Demography!$B${c0}:$B${c1}',
        [('Pop 2020', f'County_Demography!$H${c0}:$H${c1}')],
        kind='bar', height=10, y_fmt='#,##0')

    facts += [
        {'metric': 'MMT footprint population (22 counties, 2020 Census)',
         'year': 2020, 'value_ref': f'County_Demography!K{r_ctot}',
         'unit': 'residents', 'basis': 'DERIVED', 'tier': 'B',
         'source_keys': ['census2020_county'],
         'locator': 'SUM of 22 county 2020 Census populations (= 1,560,299)',
         'lives_on': 'County_Demography',
         'cross_check': 'ift_mmt.footprint_summary() pop_2020 = 1,560,299; '
                        'CBSA panel SUM matches'},
        {'metric': 'Douglas County NE population (2020 Census)',
         'year': 2020, 'value_ref': f'County_Demography!K{a0}',
         'unit': 'residents', 'basis': 'SOURCED', 'tier': 'B',
         'source_keys': ['census2020_county'],
         'locator': '2020 Decennial Census, Douglas County NE (FIPS 31055)',
         'lives_on': 'County_Demography',
         'cross_check': 'MMT HQ county; largest footprint county'},
        {'metric': 'Fastest-growing footprint county: Saunders NE CAGR '
                   '2020-2024',
         'year': 2024, 'value_ref': f'County_Demography!G{b0}',
         'unit': '%/yr', 'basis': 'DERIVED', 'tier': 'B',
         'source_keys': ['census_v2024_est', 'census2020_county'],
         'locator': '(23,406 / 21,578)^(1/4)-1 = +2.05%/yr (live formula)',
         'lives_on': 'County_Demography',
         'cross_check': 'ift_mmt.county_growth() computes 2.054%/yr; '
                        're-verify flag travels'},
        {'metric': 'Sarpy County NE population (Vintage-2024 estimate)',
         'year': 2024, 'value_ref': f'County_Demography!E{b0 + 1}',
         'unit': 'residents', 'basis': 'SOURCED', 'tier': 'B',
         'source_keys': ['census_v2024_est'],
         'locator': 'Vintage-2024 estimate 204,828 (captured 2026-07-10; '
                    're-verify queue)',
         'lives_on': 'County_Demography',
         'cross_check': '+7.46% over 2020 - the fastest-growing large NE '
                        'county'},
        {'metric': 'Footprint = complete OMB composition of 7 CBSAs '
                   '(22 counties)',
         'year': 2023, 'value_ref': f'County_Demography!F{r_cbtot}',
         'unit': 'counties', 'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['omb_cbsa_2023'],
         'locator': 'Live COUNTIF per CBSA against the vendored OMB Bulletin '
                    '23-01 crosswalk = 22 = footprint count',
         'lives_on': 'County_Demography',
         'cross_check': '8+2+3+2+3+2+2 counties across CBSAs 36540/30700/'
                        '24260/28260/25580/35820/18100'},
    ]
    excluded += [
        {'figure': 'County senior share / population 65+ columns',
         'value': 'tier shares 14.5% core / 15.5% suburban / 20.5% '
                  'rural-feeder',
         'source_label': 'ift_mmt.MMT_COUNTIES.senior_share - module-labeled '
                         'ILLUSTRATIVE',
         'why_excluded': 'Tier-assigned assumption, not a measured county '
                         'value',
         'what_would_make_citable': 'Census ACS S0101 age-65+ by county '
                                    '(connector spec exists in '
                                    'county_connector_coverage)'},
        {'figure': 'Per-county / per-CBSA IFT demand missions and dollars',
         'value': 'e.g. footprint 16,334 legs / $7.66M at $469/leg',
         'source_label': 'ift_mmt.county_demand() / footprint_cbsas() '
                         'demand columns - DERIVED demand-floor model',
         'why_excluded': 'Belongs with its full derivation chain (rate '
                         'constants, equations, caveats) on the demand tabs, '
                         'not as bare county columns; per-county allocation '
                         'is population-proportional, not measured',
         'what_would_make_citable': 'County-grain claims volumes (CMS MUP '
                                    'by-geo county rows or state EMS data)'},
    ]

    # ════════════════════════════════════════════════════════════════════════
    # Tab 3 — CBSA_Crosswalk_Reference
    # ════════════════════════════════════════════════════════════════════════
    xw_path = os.path.join(VENDOR, 'cbsa_crosswalk', 'cbsa_county_crosswalk.csv')
    xw = list(csv.DictReader(open(xw_path)))
    names = {}
    for r_ in csv.DictReader(open(os.path.join(
            VENDOR, 'county_demographics', 'county_demographics.csv'))):
        names[r_['county_fips']] = r_['county_name']

    def _state(fips):
        return FIPS_STATE.get(fips[:2], fips[:2])

    listing = sorted(
        xw, key=lambda r_: (_state(r_['county_fips']),
                            names.get(r_['county_fips'], ''),
                            r_['county_fips']))
    n_named = sum(1 for r_ in xw if r_['county_fips'] in names)

    ws = wb.create_sheet('CBSA_Crosswalk_Reference')
    NC3 = 9
    sb = lib.SheetBuilder(
        ws, NC3,
        col_widths=[10, 26, 7, 10, 30, 13, 13, 12, 11],
        tab_color=PURPLE)
    sb.title('County-to-CBSA crosswalk: the full 2023 OMB delineation '
             '(reference)')
    sb.subtitle(
        'The question: which counties belong to which metro/micro market - '
        'the geography spine every county-grain dataset (Market Saturation, '
        'PECOS, PLACES, enrollment) rolls up through? Source: OMB Bulletin '
        'No. 23-01 delineation file (July 2023, effective 2023-07-21), '
        'vendored from census.gov (list1_2023.xlsx) on 2026-05-26. 1,915 '
        'county rows -> 935 CBSAs. This is a REFERENCE tab - the full '
        'listing is intentionally long. It closes v2.7 pending item P3 '
        '(MSA_Landscape coverage).')
    sb.blank()
    sb.banner('Summary - live formulas over the full listing below')
    sb.headers(['Area type', 'County rows (live)', 'Distinct CBSAs (live)',
                'Meta: county rows', 'Meta: CBSAs', 'Delta rows (=B-D)',
                'Delta CBSAs (=C-E)', '', 'Basis'], freeze=False)
    # listing block coordinates (computed ahead: rows are deterministic)
    # summary rows: 3 mini-table + 4 label rows + notes; we place the listing
    # after we know how many summary rows we write - track cursor instead.
    s_meta = sb.r + 1   # Metropolitan row
    # placeholders for t0/t1 -> patch after listing writes (write formulas
    # referencing t0/t1 AFTER the listing block exists is cleaner: we know
    # exact listing extent now)
    # compute listing start: current row + 3 mini-table rows (Metropolitan,
    # Micropolitan, Total) + 4 label rows + 2 notes + blank + banner + header
    # + 1 to land on the first data row
    t0 = sb.r + 3 + 4 + 2 + 1 + 1 + 1 + 1
    t1 = t0 + len(listing) - 1
    r = sb.r + 1
    sb.row([('Metropolitan', 'label'),
            (f'=COUNTIF($F${t0}:$F${t1},"Metropolitan")', 'fml', lib.FMT_INT),
            (f'=SUMIFS($H${t0}:$H${t1},$F${t0}:$F${t1},"Metropolitan")',
             'fml', lib.FMT_INT),
            (1252, 'src', lib.FMT_INT), None,
            (f'=B{r}-D{r}', 'fml', lib.FMT_INT), None, None,
            ('GOV / DERIVED', 'note')])
    r = sb.r + 1
    sb.row([('Micropolitan', 'label'),
            (f'=COUNTIF($F${t0}:$F${t1},"Micropolitan")', 'fml', lib.FMT_INT),
            (f'=SUMIFS($H${t0}:$H${t1},$F${t0}:$F${t1},"Micropolitan")',
             'fml', lib.FMT_INT),
            (663, 'src', lib.FMT_INT), None,
            (f'=B{r}-D{r}', 'fml', lib.FMT_INT), None, None,
            ('GOV / DERIVED', 'note')])
    r = sb.r + 1
    sb.row([('Total', 'label'),
            (f'=B{r - 2}+B{r - 1}', 'fml', lib.FMT_INT),
            (f'=C{r - 2}+C{r - 1}', 'fml', lib.FMT_INT),
            (1915, 'src', lib.FMT_INT), (935, 'src', lib.FMT_INT),
            (f'=B{r}-D{r}', 'fml', lib.FMT_INT),
            (f'=C{r}-E{r}', 'fml', lib.FMT_INT), None,
            ('GOV / DERIVED', 'note')])
    r_xtot = sb.r
    s_chart0, s_chart1 = s_meta, s_meta + 1
    r = sb.r + 1
    sb.row([('Central county rows', 'label'),
            (f'=COUNTIF($G${t0}:$G${t1},"Central")', 'fml', lib.FMT_INT),
            None, None, None, None, None, None, ('DERIVED', 'note')])
    r = sb.r + 1
    sb.row([('Outlying county rows', 'label'),
            (f'=COUNTIF($G${t0}:$G${t1},"Outlying")', 'fml', lib.FMT_INT),
            None, None, None, None, None, None, ('DERIVED', 'note')])
    r = sb.r + 1
    sb.row([('Footprint-state county rows (NE OH WI IA KS IN KY MO MN VA WY)',
             'label'),
            (f'=COUNTIF($I${t0}:$I${t1},"Y")', 'fml', lib.FMT_INT),
            None, None, None, None, None, None, ('DERIVED', 'note')])
    r_fp = sb.r
    r = sb.r + 1
    sb.row([('Footprint-state share of CBSA county rows', 'label'),
            (f'=B{r_fp}/B{r_xtot}', 'fml', lib.FMT_PCT1),
            None, None, None, None, None, None, ('DERIVED', 'note')])
    sb.note('Meta columns D-E are the vendored provenance constants from '
            'cbsa_crosswalk_meta.json (vintage 2023, ingested 2026-05-26); '
            'deltas must be 0. Distinct-CBSA counts are live SUMs over the '
            'first-occurrence helper column H below. The meta file counts '
            '1,252 metropolitan / 663 micropolitan COUNTY ROWS; the distinct '
            'CBSA split (393 MSA / 542 uSA) is computed live here.')
    sb.note('Rural context (42 CFR 414.605): for the Ambulance Fee Schedule, '
            '"rural" means outside an MSA (or a Goldsmith rural tract inside '
            'one), determined by ZIP of pickup. Micropolitan counties ARE '
            'rural for AFS purposes, as are the ~1,200 US county-equivalents '
            'outside any CBSA (not listed in this file). County grain '
            'approximates the ZIP-based payment rule - see '
            'HPSA_Rural_Designations for the add-on rates.')
    sb.blank()
    sb.banner('Full county -> CBSA listing (1,915 rows, sorted by state then '
              'county)')
    sb.headers(['County FIPS', 'County name', 'State', 'CBSA code',
                'CBSA title', 'Metro / Micro', 'Central / Outlying',
                '1st occurrence of CBSA (helper)', 'Footprint state?'])
    t0_actual = sb.r + 1
    assert t0_actual == t0, f'listing start drifted: {t0_actual} != {t0}'
    for rec in listing:
        r = sb.r + 1
        f = rec['county_fips']
        sb.row([
            (f, 'src'), (names.get(f, ''), 'src'), (_state(f), 'src'),
            (rec['cbsa_code'], 'src'), (rec['cbsa_title'], 'src'),
            (rec['area_type'], 'src'), (rec['central_outlying'], 'src'),
            (f'=IF(COUNTIF($D${t0}:$D{r},$D{r})=1,1,0)', 'fml', lib.FMT_INT),
            (f'=IF(ISNUMBER(SEARCH(" "&$C{r}&" ","{FP_SEARCH}")),"Y","")',
             'fml'),
        ])
    t1_actual = sb.r
    assert t1_actual == t1, f'listing end drifted: {t1_actual} != {t1}'
    sb.note(f'County names: joined from the vendored Census/CHR county file '
            f'by FIPS ({n_named:,} of {len(listing):,} rows matched). The 80 '
            'blank names are 71 Puerto Rico municipios and 9 Connecticut '
            'planning-region county-equivalents (FIPS 09110-09190, the 2022 '
            'CT county-equivalent change) absent from that file - names '
            'resolvable in the OMB source workbook. State column is decoded '
            'from the FIPS state prefix (ANSI standard). CBSA titles are as '
            'published in the 2023 file and can differ from earlier vintages '
            '(e.g. 36540 is now titled "Omaha, NE-IA").')
    sb.note('Extraction: rcm_mc/data/vendor/cbsa_crosswalk/'
            'cbsa_county_crosswalk.csv read directly for this build '
            f'({accessed}); provenance registry rows "cbsa_crosswalk" and '
            '"chr_county_demographics" in rcm_mc/data/vendor/'
            'source_registry.csv. License: U.S. government work, public '
            'domain.')
    lib.add_chart(
        ws, 'K5', 'County rows and distinct CBSAs by area type (2023 '
        'delineations)',
        f'CBSA_Crosswalk_Reference!$A${s_chart0}:$A${s_chart1}',
        [('County rows', f'CBSA_Crosswalk_Reference!$B${s_chart0}:$B${s_chart1}'),
         ('Distinct CBSAs', f'CBSA_Crosswalk_Reference!$C${s_chart0}:$C${s_chart1}')],
        kind='bar', height=9)

    facts += [
        {'metric': 'Counties inside a CBSA (2023 OMB delineations)',
         'year': 2023, 'value_ref': f'CBSA_Crosswalk_Reference!B{r_xtot}',
         'unit': 'county rows', 'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['omb_cbsa_2023'],
         'locator': 'Live COUNTIF total over the vendored list1_2023 extract '
                    '(= 1,915; meta cross-check delta 0)',
         'lives_on': 'CBSA_Crosswalk_Reference',
         'cross_check': 'cbsa_crosswalk_meta.json counties=1915'},
        {'metric': 'Distinct CBSAs (2023 OMB delineations)',
         'year': 2023, 'value_ref': f'CBSA_Crosswalk_Reference!C{r_xtot}',
         'unit': 'CBSAs', 'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['omb_cbsa_2023'],
         'locator': 'SUM of first-occurrence helper column (= 935 = 393 MSA '
                    '+ 542 uSA)',
         'lives_on': 'CBSA_Crosswalk_Reference',
         'cross_check': 'cbsa_crosswalk_meta.json cbsas=935'},
        {'metric': 'Metropolitan county rows (2023 delineations)',
         'year': 2023, 'value_ref': f'CBSA_Crosswalk_Reference!B{s_meta}',
         'unit': 'county rows', 'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['omb_cbsa_2023'],
         'locator': 'COUNTIF area_type="Metropolitan" (= 1,252; micropolitan '
                    '= 663)',
         'lives_on': 'CBSA_Crosswalk_Reference',
         'cross_check': 'Metro counties sit inside MSAs - the AFS urban '
                        'proxy at county grain'},
        {'metric': 'Footprint-state county rows inside CBSAs (11 states)',
         'year': 2023, 'value_ref': f'CBSA_Crosswalk_Reference!B{r_fp}',
         'unit': 'county rows', 'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['omb_cbsa_2023'],
         'locator': 'COUNTIF footprint-flag column (= 549 of 1,915)',
         'lives_on': 'CBSA_Crosswalk_Reference',
         'cross_check': 'Flag formula is self-contained (SEARCH against the '
                        '11-state string)'},
    ]

    # ════════════════════════════════════════════════════════════════════════
    # Tab 4 — HPSA_Rural_Designations
    # ════════════════════════════════════════════════════════════════════════
    hp = list(csv.DictReader(open(os.path.join(
        VENDOR, 'hrsa', 'hrsa_hpsa_pc_by_state.csv'))))

    ws = wb.create_sheet('HPSA_Rural_Designations')
    NC4 = 8
    sb = lib.SheetBuilder(
        ws, NC4,
        col_widths=[34, 13, 25, 22, 12, 17, 18, 52],
        tab_color=PURPLE)
    sb.title('Shortage & rural designations: HRSA primary-care HPSAs by '
             'state + the ambulance rural add-ons')
    sb.subtitle(
        'The question: where is the clinician-shortage / rural geography '
        'that (a) makes interfacility transport legs long and (b) carries '
        'statutory Medicare ambulance add-ons? Panel A states the payment '
        'facts (statute-cited). Panel B is the HRSA Data Warehouse '
        'primary-care HPSA state table (snapshot 2026-05-25, aggregated from '
        '19,696 designated PC-HPSA records). Honesty note: HPSA status does '
        'NOT itself change ambulance payment - the add-ons key off the '
        'ZIP-of-pickup rural definition in 42 CFR 414.605 - HPSAs are '
        'carried as shortage-geography context.')
    sb.blank()
    sb.banner('Panel A. The statutory rural add-ons (why rural geography is '
              'a payment fact)')
    sb.headers(['Item', 'Value', 'Applies to', 'Effective window', 'Basis',
                '', '', 'Source / locator'])
    r = sb.r + 1
    sb.row([('Urban ground add-on', 'label'), (0.02, 'src', lib.FMT_PCT1),
            ('AFS base rate + mileage, urban pickup ZIPs', 'text'),
            ('through Dec 31, 2027', 'src'), ('GOV (chip; carried via repo '
            'cite - re-verify flag travels)', 'note'), None, None,
            ('SSA sec. 1834(l)(12)(A),(13)(A); extended by CAA 2026 sec. '
             '6203', 'text')], wrap=True)
    r_addon0 = sb.r
    sb.row([('Rural ground add-on', 'label'), (0.03, 'src', lib.FMT_PCT1),
            ('AFS base rate + mileage, rural pickup ZIPs', 'text'),
            ('through Dec 31, 2027', 'src'), ('GOV (as above)', 'note'),
            None, None,
            ('SSA sec. 1834(l)(12)(A),(13)(A); 42 CFR 414.610(c)(1)(ii); '
             'CAA 2026 sec. 6203', 'text')], wrap=True)
    sb.row([('Super-rural base-rate bonus', 'label'),
            (0.226, 'src', lib.FMT_PCT1),
            ('AFS BASE RATE only; pickup in the lowest-quartile rural '
             'population-density areas', 'text'),
            ('through Dec 31, 2027', 'src'), ('GOV (as above)', 'note'),
            None, None,
            ('SSA sec. 1834(l)(12)(A); 42 CFR 414.610(c)(5)(ii)', 'text')],
           wrap=True)
    r_super = sb.r
    sb.row([('CBO score of the 2-year extension', 'label'),
            (197000000, 'src', lib.FMT_USD), ('CAA 2026 sec. 6203', 'text'),
            ('2026-2027', 'src'), ('SOURCED (Senate Finance summary, via '
            'repo cite)', 'note'), None, None,
            ('Senate Finance CAA 2026 section-by-section (~$197M)', 'text')],
           wrap=True)
    sb.row([('MedPAC on the 2%/3% add-ons (verbatim)', 'label'),
            ('"did not have an underlying empirical basis"', 'src'),
            ('policy-durability read: add-ons are temporary, not '
             'cost-justified in MedPAC\'s view', 'text'),
            ('June 2026', 'src'), ('SOURCED (MedPAC Jun 2026 Ch. 6, via '
            'repo cite)', 'note'), None, None,
            ('MedPAC June 2026 Report to Congress, Ch. 6', 'text')],
           wrap=True)
    sb.row([('AFS rural definition', 'label'),
            ('outside an MSA, or a Goldsmith-modification rural census '
             'tract; determined by ZIP of pickup', 'src'),
            ('the trigger geography for the +3% / +22.6% rows above',
             'text'), ('current eCFR', 'src'), ('GOV', 'note'), None, None,
            ('42 CFR 414.605, "rural area" definition', 'text')], wrap=True)
    sb.row([('County-grain approximation of AFS-rural', 'label'),
            ('Micropolitan + non-CBSA counties', 'link'),
            ('see CBSA_Crosswalk_Reference (663 micropolitan county rows '
             'live-counted there)', 'link'),
            None, ('DERIVED (approximation - AFS is ZIP-based)', 'note'),
            None, None,
            ('OMB Bulletin 23-01 crosswalk tab', 'text')], wrap=True)

    sb.blank()
    sb.banner('Panel B. HRSA primary-care HPSA designations by state '
              '(snapshot 2026-05-25)')
    sb.headers(['State', 'Footprint state?', 'Designated PC HPSAs',
                'Median HPSA score (0-25, higher = worse shortage)',
                'Max HPSA score',
                'Sum of designation-listed population (OVERLAPPING - see '
                'note)', 'Basis', 'Note'])
    b0 = sb.r + 1
    ne_row = None
    for rec in hp:
        r = sb.r + 1
        st = rec['state']
        if st == 'NE':
            ne_row = r
        note = ''
        if st == 'XX':
            note = 'State-unassigned designation records in the HRSA file.'
        elif st in ('FM', 'VI', 'GU', 'PW', 'AS', 'MP', 'MH', 'PR'):
            note = 'Territory / freely-associated state.'
        sb.row([
            (st, 'src'),
            (f'=IF(ISNUMBER(SEARCH(" "&$A{r}&" ","{FP_SEARCH}")),"Y","")',
             'fml'),
            (int(rec['designated_pc_hpsas']), 'src', lib.FMT_INT),
            (float(rec['median_hpsa_score']), 'src', lib.FMT_DEC1),
            (int(rec['max_hpsa_score']), 'src', lib.FMT_INT),
            (float(rec['population_in_shortage']), 'src', lib.FMT_INT),
            ('GOV', 'note'), (note, 'note'),
        ])
    b1 = sb.r
    r = sb.r + 1
    sb.row([('Total (states + territories + unassigned)', 'label'), None,
            (f'=SUM(C{b0}:C{b1})', 'fml', lib.FMT_INT), None, None,
            (f'=SUM(F{b0}:F{b1})', 'fml', lib.FMT_INT),
            ('DERIVED', 'note'), None])
    r_htot = sb.r
    r = sb.r + 1
    sb.row([('Footprint 11-state subtotal', 'label'), None,
            (f'=SUMIF($B${b0}:$B${b1},"Y",$C${b0}:$C${b1})', 'fml',
             lib.FMT_INT), None, None, None, ('DERIVED', 'note'), None])
    r_hfp = sb.r
    r = sb.r + 1
    sb.row([('Footprint share of national designations', 'label'), None,
            (f'=C{r_hfp}/C{r_htot}', 'fml', lib.FMT_PCT1), None, None, None,
            ('DERIVED', 'note'), None])
    r_hshare = sb.r

    sb.note('Column F caveat (must travel): the HRSA file sums each '
            'designation\'s listed population; geographic, population-group '
            'and facility designations OVERLAP, so column F double-counts '
            'people and exceeds actual state population in several states '
            '(e.g. CA, NY). Use it only to rank shortage intensity - it is '
            'NEVER a count of distinct residents in shortage areas. '
            'Designation counts (column C) do not have this problem.')
    sb.note('Provenance: HRSA Data Warehouse, Primary Care HPSA discipline, '
            'designated records, snapshot 2026-05-25; 19,696 raw designated '
            'rows aggregated to state (hrsa_hpsa_report.json). Vendored at '
            'rcm_mc/data/vendor/hrsa/hrsa_hpsa_pc_by_state.csv; registry row '
            '"hrsa_hpsa_pc" in vendor/source_registry.csv. Extraction: file '
            f'read directly for this build, {accessed}. "XX" = '
            'state-unassigned records. Scores run 0-25 (26 for some '
            'disciplines); higher = greater shortage.')
    sb.note('Framing, stated precisely: HPSA designation drives clinician '
            'bonuses (physician fee schedule), NOT ambulance rates. The tie '
            'to IFT economics is geographic: shortage counties are where '
            'specialty coverage is thin, transfer legs are long, volunteer '
            'EMS is fragile, and rural pickup ZIPs carry the +3% / +22.6% '
            'add-ons of Panel A. High-HPSA footprint states (MO 340, KY 245, '
            'MN 199, IA 162) are the same geography as the thin/long-leg '
            'metros on Metro_Structure_20.')

    lib.add_chart(
        ws, f'J{b0}', 'Designated primary-care HPSAs by state (HRSA snapshot '
        '2026-05-25)',
        f'HPSA_Rural_Designations!$A${b0}:$A${b1}',
        [('Designated PC HPSAs',
          f'HPSA_Rural_Designations!$C${b0}:$C${b1}')],
        kind='bar', height=18)

    facts += [
        {'metric': 'Designated primary-care HPSAs, national total',
         'year': 2026, 'value_ref': f'HPSA_Rural_Designations!C{r_htot}',
         'unit': 'designations', 'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['hrsa_hpsa_pc'],
         'locator': 'SUM over the 60 state/territory rows (= 7,635), HRSA '
                    'snapshot 2026-05-25',
         'lives_on': 'HPSA_Rural_Designations',
         'cross_check': 'Aggregated from 19,696 raw designated rows '
                        '(hrsa_hpsa_report.json)'},
        {'metric': 'Designated primary-care HPSAs, footprint 11 states',
         'year': 2026, 'value_ref': f'HPSA_Rural_Designations!C{r_hfp}',
         'unit': 'designations', 'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['hrsa_hpsa_pc'],
         'locator': 'SUMIF over footprint flag (= 1,931; 25.3% of national)',
         'lives_on': 'HPSA_Rural_Designations',
         'cross_check': f'Share formula on row {r_hshare}'},
        {'metric': 'Designated primary-care HPSAs, Nebraska',
         'year': 2026,
         'value_ref': f'HPSA_Rural_Designations!C{ne_row}',
         'unit': 'designations', 'basis': 'GOV', 'tier': 'A',
         'source_keys': ['hrsa_hpsa_pc'],
         'locator': 'NE row of hrsa_hpsa_pc_by_state.csv (= 125; median '
                    'score 13, max 20)',
         'lives_on': 'HPSA_Rural_Designations',
         'cross_check': 'NE also has 80%+ volunteer EMS agencies '
                        '(Workforce_Supply) - same thin-coverage geography'},
        {'metric': 'Super-rural ground ambulance base-rate bonus',
         'year': 2026, 'value_ref': f'HPSA_Rural_Designations!B{r_super}',
         'unit': 'share of base rate', 'basis': 'SOURCED', 'tier': 'B',
         'source_keys': ['ssa1834l_addons'],
         'locator': 'SSA sec. 1834(l)(12)(A); 42 CFR 414.610(c)(5)(ii); '
                    '+22.6% for lowest-quartile rural density pickups, '
                    'through 2027-12-31',
         'lives_on': 'HPSA_Rural_Designations',
         'cross_check': 'Same figures carried on Payment_Rules / '
                        'Service_Level_Economics; MedPAC "no empirical '
                        'basis" caveat on-sheet'},
        {'metric': 'Rural ground ambulance add-on (base + mileage)',
         'year': 2026, 'value_ref': f'HPSA_Rural_Designations!B{r_addon0 + 1}',
         'unit': 'share', 'basis': 'SOURCED', 'tier': 'B',
         'source_keys': ['ssa1834l_addons', 'ecfr_414_605'],
         'locator': '+3% rural (urban +2%), SSA sec. 1834(l)(13)(A), '
                    'extended by CAA 2026 sec. 6203 through 2027-12-31',
         'lives_on': 'HPSA_Rural_Designations',
         'cross_check': 'Sunset risk flagged: add-ons lapse 2028-01-01 '
                        'absent re-extension'},
    ]
    excluded += [
        {'figure': 'HPSA "population in shortage" as a distinct-person count',
         'value': 'e.g. CA 125.1M (exceeds CA population)',
         'source_label': 'hrsa_hpsa_pc_by_state.csv population_in_shortage',
         'why_excluded': 'Overlapping designations double-count people; the '
                         'column is carried on-sheet ONLY as a ranking aid '
                         'with the caveat printed, never quoted as persons',
         'what_would_make_citable': 'HRSA\'s de-duplicated "designated '
                                    'population" statistic from the HPSA '
                                    'find-tool national tables'},
    ]

    return {
        'facts': facts, 'sources': sources, 'excluded': excluded,
        'meta': {
            'row_counts': {s['name']: wb[s['name']].max_row for s in SHEETS},
            'notes': ('Group G. HCRIS columns LIVE (pandas present). '
                      'Crosswalk listing 1,915 rows; HPSA 60 rows; '
                      + ('; '.join(notes) if notes else 'identity checks '
                         'passed (postacute=SNF+IRF+LTCH, nodes=hosp+'
                         'postacute, all 20 metros)')),
        },
    }
