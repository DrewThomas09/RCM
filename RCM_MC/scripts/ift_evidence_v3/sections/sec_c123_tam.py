"""C.1-C.3: the sizing math (Metro_TAM_Panels, TAM_Assembly_State,
Scenario_Matrix).

Three tabs, one discipline: every volume and price step is either a LIVE
formula anchored green to a measured cell already in this workbook, or a
bordered PENDING cell that names the public dataset that would fill it.
No single asserted TAM appears anywhere; the Scenario_Matrix grid IS the
answer, cell by cell, with its gates printed.

Anchors (all scanned at build time, never hardcoded by row):
  - transfer rate: Acute_IFT_Series 'Mean IFT % of admissions' (HCUP NEDS+NIS
    episodes over AHA community-hospital admissions, mean 2019-2023);
  - catchment volume proxy: CMS Hospital Service Area (HSA) 2025 service-area
    total Medicare FFS inpatient cases per hospital CCN
    (HSA_Hospital_Catchment), metro CCN rosters from the same
    rcm_mc.market_reports.ift_geo city+state filter that built the 20
    Metro_ tabs;
  - Medicare-anchored price: Derived_Rate_Card A0428 base (RVU x CY2026 CF)
    at metro/state grain; measured allowed per transport
    (Medicare_IFT_Series) in the scenario grid;
  - gross-up anchors: Insourcing_Bounds floor/ceiling (A.4),
    Facility_Pay_Layer one-in-five unbilled + 18.6% facility-contract
    incidence + MA book calibrator (B.1). Every cross-tab reference is
    guarded with `if name in wb.sheetnames else PENDING`.
"""

SHEETS = [
    {'name': 'Metro_TAM_Panels',
     'question': 'Per target metro, what is the measured mission-demand '
                 'line, and how far can it be priced from public evidence '
                 'alone?'},
    {'name': 'TAM_Assembly_State',
     'question': 'Does the bottom-up state assembly reconcile to the '
                 'carried top-down scenario model, and where exactly do '
                 'the two differ?'},
    {'name': 'Scenario_Matrix',
     'question': 'Across three volume bases and three price bases, which '
                 'sizing cells are live from public evidence and which '
                 'stay PENDING, and what moves them?'},
]

# Metro tab -> ift_geo MetroDef name (same mapping sec_metros.py used to
# build the 20 tabs; panels iterate wb.sheetnames startswith 'Metro_').
_DEF_BY_TAB = {
    'Metro_Omaha': 'Omaha', 'Metro_Lincoln': 'Lincoln',
    'Metro_NorthPlatte': 'North Platte', 'Metro_ColumbusNE': 'Columbus (NE)',
    'Metro_GI_Kearney': 'Grand Island / Kearney',
    'Metro_Cleveland': 'Cleveland', 'Metro_Cincinnati': 'Cincinnati',
    'Metro_ColumbusOH': 'Columbus (OH)', 'Metro_Dayton': 'Dayton',
    'Metro_KansasCity': 'Kansas City (bi-state)', 'Metro_Wichita': 'Wichita',
    'Metro_Madison': 'Madison', 'Metro_Milwaukee': 'Milwaukee',
    'Metro_TwinCities': 'Twin Cities', 'Metro_RochesterMN': 'Rochester (MN)',
    'Metro_DesMoines': 'Des Moines',
    'Metro_NWIndiana': 'Crown Point / NW Indiana',
    'Metro_Louisville': 'Louisville', 'Metro_NoVirginia': 'Northern Virginia',
    'Metro_Cheyenne_Casper': 'Cheyenne / Casper (WY)'}

# Footprint states (provisional footprint, same ten Insourcing_Bounds
# Panel C carries) with their SSA CCN prefixes.
_FOOTPRINT = [('NE', '28'), ('IA', '16'), ('KS', '17'), ('MO', '26'),
              ('OH', '36'), ('WI', '52'), ('VA', '49'), ('MN', '24'),
              ('IN', '15'), ('KY', '18')]

HSA_TAB = 'HSA_Hospital_Catchment'
PEND = ('PENDING', 'note')


def _find_row(ws, needle, col=1, exact=False):
    """First row whose col-`col` string contains (or equals) needle."""
    n = needle.lower()
    for row in ws.iter_rows(min_col=col, max_col=col):
        c = row[0]
        if isinstance(c.value, str):
            v = c.value.lower()
            if (v == n) if exact else (n in v):
                return c.row
    return None


def _find_int_row(ws, target, col=1, after=0):
    for row in ws.iter_rows(min_row=after + 1, min_col=col, max_col=col):
        c = row[0]
        if isinstance(c.value, int) and c.value == target:
            return c.row
    return None


def _metro_ccn_rosters(ctx):
    """{metro_tab: [ccn,...]} via the same city+state filter that built the
    Metro_ tabs. Degrades to {} if the repo rolls are unavailable."""
    import sys
    for p in ('/home/user/RCM/RCM_MC', '/home/user/RCM', ctx.get('repo', '')):
        if p and p not in sys.path:
            sys.path.insert(0, p)
    try:
        from rcm_mc.data.hospital_coords import load_hospital_coords
        from rcm_mc.market_reports import ift_geo
        coords = list(load_hospital_coords().values())
        out = {}
        for tab, name in _DEF_BY_TAB.items():
            md = ift_geo.metro_def(name)
            if md is None:
                continue
            hosp = ift_geo._filter(coords, md.states, md.cities)
            out[tab] = sorted(str(h.ccn).strip() for h in hosp)
        return out
    except Exception:  # noqa: BLE001 - degrade to PENDING cells, never raise
        return {}


def _hsa_cases(wb):
    """{ccn: total service-area Medicare FFS inpatient cases} from the
    HSA_Hospital_Catchment tab, plus the tab's data extent."""
    ws = wb[HSA_TAB]
    hdr = _find_row(ws, 'Provider (CCN)')
    first = (hdr or 4) + 1
    cases, last = {}, first
    for row in ws.iter_rows(min_row=first, max_row=ws.max_row, max_col=3):
        a, c = row[0].value, row[2].value
        if a is None or not isinstance(a, str):
            continue
        cases[a] = c if isinstance(c, (int, float)) else 0
        last = row[0].row
    return cases, first, last


def build(wb, ctx):
    lib = ctx['lib']
    accessed = ctx['accessed']
    facts, sources, excluded, findings = [], [], [], []

    # ------------------------------------------------------------ anchors
    def has(name):
        return name in wb.sheetnames

    # transfer rate (Acute_IFT_Series)
    rate_ref = rate_lo_ref = rate_hi_ref = None
    mean_rate = None
    epi_mean_ref = None
    if has('Acute_IFT_Series'):
        a = wb['Acute_IFT_Series']
        r = _find_row(a, 'Mean IFT % of admissions')
        rate_ref = f"'Acute_IFT_Series'!$B${r}" if r else None
        r = _find_row(a, 'Low of the ratio band')
        rate_lo_ref = f"'Acute_IFT_Series'!$B${r}" if r else None
        r = _find_row(a, 'High of the ratio band')
        rate_hi_ref = f"'Acute_IFT_Series'!$B${r}" if r else None
        r = _find_row(a, 'Mean acute-to-acute episodes per year')
        epi_mean_ref = f"'Acute_IFT_Series'!$B${r}" if r else None
        vals = []
        for yr in range(2019, 2024):
            rr = _find_int_row(a, yr)
            if rr:
                b, c, e = (a.cell(row=rr, column=k).value for k in (2, 3, 5))
                if all(isinstance(x, (int, float)) for x in (b, c, e)) and e:
                    vals.append((b + c) / e)
        mean_rate = sum(vals) / len(vals) if vals else None

    # Medicare-anchored base rate (Derived_Rate_Card, A0428 = RVU x CF)
    base_ref, base_val = None, None
    if has('Derived_Rate_Card'):
        d = wb['Derived_Rate_Card']
        r = _find_row(d, 'A0428', exact=True)
        if r:
            base_ref = f"'Derived_Rate_Card'!$D${r}"
            rvu = d.cell(row=r, column=3).value
            cf_r = _find_row(d, 'CY2026 AFS ground conversion factor')
            cf = d.cell(row=cf_r, column=2).value if cf_r else None
            if isinstance(rvu, (int, float)) and isinstance(cf, (int, float)):
                base_val = rvu * cf

    # measured claims floor (Medicare_IFT_Series 2024 row)
    mis_vol_ref = mis_ppt_ref = mis_mileshare_ref = None
    mis_vol_val = mis_allowed_val = None
    if has('Medicare_IFT_Series'):
        m = wb['Medicare_IFT_Series']
        r = _find_int_row(m, 2024)
        if r:
            mis_vol_ref = f"'Medicare_IFT_Series'!$B${r}"
            mis_ppt_ref = f"'Medicare_IFT_Series'!$G${r}"
            b, c, dd = (m.cell(row=r, column=k).value for k in (2, 3, 4))
            if all(isinstance(x, (int, float)) for x in (b, c, dd)):
                mis_vol_val, mis_allowed_val = b, c + dd
        r = _find_row(m, 'Mileage as a share of allowed dollars, 2024')
        mis_mileshare_ref = f"'Medicare_IFT_Series'!$B${r}" if r else None

    # NEMSIS hospital-to-hospital legs 2024 (EMS_Transports)
    ems_ref, ems_val = None, None
    if has('EMS_Transports'):
        e = wb['EMS_Transports']
        r = _find_row(e, 'Hospital-to-Hospital Transfer')
        if r:
            ems_ref = f"'EMS_Transports'!$B${r}"
            v = e.cell(row=r, column=2).value
            ems_val = v if isinstance(v, (int, float)) else None

    # insourcing bounds (A.4): national 2024 floor/ceiling + per state
    ins_floor_ref = ins_ceil_ref = None
    ins_state = {}
    if has('Insourcing_Bounds'):
        i = wb['Insourcing_Bounds']
        r = _find_int_row(i, 2024)
        if r:
            ins_floor_ref = f"'Insourcing_Bounds'!$F${r}"
            ins_ceil_ref = f"'Insourcing_Bounds'!$G${r}"
        pc = _find_row(i, 'Panel C.')
        if pc:
            for st, _ in _FOOTPRINT:
                rr = _find_row(i, st, exact=True)
                if rr and rr > pc:
                    ins_state[st] = (f"'Insourcing_Bounds'!$E${rr}",
                                     f"'Insourcing_Bounds'!$F${rr}")

    # facility-pay layer (B.1): unbilled anchor, incidence, MA calibrator
    fp_unbilled_ref = fp_incid_ref = fp_ma_ref = None
    if has('Facility_Pay_Layer'):
        f = wb['Facility_Pay_Layer']
        r = _find_row(f, 'did not always bill')
        fp_unbilled_ref = f"'Facility_Pay_Layer'!$B${r}" if r else None
        r = _find_row(f, 'Facility contracts (hospitals')
        fp_incid_ref = f"'Facility_Pay_Layer'!$B${r}" if r else None
        r = _find_row(f, 'MA-to-FFS revenue ratio')
        fp_ma_ref = f"'Facility_Pay_Layer'!$B${r}" if r else None

    # carried top-down model (TAM_Model_National)
    tam = {}
    if has('TAM_Model_National'):
        t = wb['TAM_Model_National']
        for key, needle, cols in (
                ('tam', 'National TAM, 2024', 'BCD'),
                ('seg', 'Scheduled and interfacility segment, 2024', 'BCD'),
                ('vol', 'National ground transports, 2024', 'C'),
                ('ppt', 'Medicare FFS allowed per transport, 2024', 'B'),
                ('cmult', 'Commercial allowed as a multiple of Medicare FFS',
                 'BCD'),
                ('ma_lo', 'MA allowed as a multiple of Medicare FFS', 'B')):
            r = _find_row(t, needle)
            if r:
                tam[key] = {c: f"'TAM_Model_National'!${c}${r}" for c in cols}
        pe = _find_row(t, 'Panel E.')
        if pe:
            r = None
            for row in t.iter_rows(min_row=pe + 1, min_col=1, max_col=1):
                c = row[0]
                if isinstance(c.value, str) and c.value.strip() == 'Commercial':
                    r = c.row
                    break
            if r:
                tam['cvol'] = {'C': f"'TAM_Model_National'!$C${r}"}

    # optional late-landing tabs
    mcaid_ref = None
    if has('Medicaid_Rate_Card'):
        mc = wb['Medicaid_Rate_Card']
        r = _find_row(mc, 'multiple of Medicare')
        mcaid_ref = f"'Medicaid_Rate_Card'!$B${r}" if r else None
    corpus_ref = None
    if has('Contract_Corpus'):
        cc = wb['Contract_Corpus']
        r = _find_row(cc, 'per transport') or _find_row(cc, 'observed rate')
        corpus_ref = f"'Contract_Corpus'!$B${r}" if r else None

    # HSA catchment volume proxy
    hsa_ok = has(HSA_TAB)
    cases, hsa_first, hsa_last = _hsa_cases(wb) if hsa_ok else ({}, 0, 0)
    rosters = _metro_ccn_rosters(ctx)

    # metro iteration: wb.sheetnames startswith Metro_, excluding the two
    # non-metro members, ordered by the Metro_Index directory when present
    metro_tabs = [s for s in wb.sheetnames if s.startswith('Metro_')
                  and s not in ('Metro_Index', 'Metro_Structure_20')]
    meta_names = {}
    if has('Metro_Index'):
        mi = wb['Metro_Index']
        order = []
        for row in mi.iter_rows(min_col=1, max_col=4):
            tab = row[1].value
            if isinstance(tab, str) and tab in metro_tabs:
                order.append(tab)
                meta_names[tab] = (row[0].value or tab,
                                   row[3].value or '')
        metro_tabs = order + [t for t in metro_tabs if t not in order]

    # -------------------------------------------------------------- sources
    sources += [
        {'key': 'c123_hsa_catchment', 'publisher': 'CMS',
         'document': 'Hospital Service Area file, 2025 release - '
                     'service-area aggregates per hospital CCN (ZIPs '
                     'served, total Medicare FFS inpatient cases), as '
                     'carried on HSA_Hospital_Catchment / HSA_Corridors',
         'vintage': '2025 release (Medicare FFS inpatient claims)',
         'locator': 'HSA_Hospital_Catchment col C (total cases) keyed by '
                    'CCN; metro CCN rosters from the '
                    'rcm_mc.market_reports.ift_geo city+state filter that '
                    'built the 20 Metro_ tabs',
         'supplies': 'The catchment volume proxy behind every mission-'
                     'demand line in C.1/C.2',
         'url': 'https://data.cms.gov/summary-statistics-on-use-and-'
                'payments/medicare-service-type-reports/'
                'hospital-service-area',
         'tier': 'A', 'accessed': accessed,
         'powers': ['Metro_TAM_Panels', 'TAM_Assembly_State']},
        {'key': 'c123_hcup_aha_rate', 'publisher': 'AHRQ HCUP; AHA',
         'document': 'HCUP NEDS (DISP_ED=2) + NIS (DISPUNIFORM=2) weighted '
                     'national transfer episodes over AHA community-'
                     'hospital admissions, as carried on Acute_IFT_Series',
         'vintage': '2019-2023 window (mean of the annual ratio)',
         'locator': "Acute_IFT_Series 'Mean IFT % of admissions' row "
                    '(live AVERAGE over the 2019-2023 ratio column)',
         'supplies': 'The measured transfer rate applied to the catchment '
                     'proxy; denominator disclosed in-row on every use',
         'url': 'https://hcup-us.ahrq.gov/nisoverview.jsp',
         'tier': 'A', 'accessed': accessed,
         'powers': ['Metro_TAM_Panels', 'TAM_Assembly_State',
                    'Scenario_Matrix']},
        {'key': 'c123_afs_cy2026', 'publisher': 'CMS',
         'document': 'Ambulance Fee Schedule public use files (CY2026): '
                     'ground conversion factor x RVU, as worked on '
                     'Derived_Rate_Card',
         'vintage': 'CY2026',
         'locator': 'Derived_Rate_Card A0428 row, national unadjusted '
                    'base column (RVU x CF)',
         'supplies': 'The Medicare-anchored $ per transport at metro and '
                     'state grain (base rate only; mileage excluded and '
                     'said so in-row)',
         'url': 'https://www.cms.gov/medicare/payment/fee-schedules/'
                'ambulance/ambulance-fee-schedule-public-use-files',
         'tier': 'A', 'accessed': accessed,
         'powers': ['Metro_TAM_Panels', 'TAM_Assembly_State']},
        {'key': 'c123_psps_ift', 'publisher': 'CMS',
         'document': 'Physician/Supplier Procedure Summary derived '
                     'Medicare FFS interfacility series (hospital-to-'
                     'hospital transports, allowed dollars), as carried '
                     'on Medicare_IFT_Series',
         'vintage': '2024 final-action carrier claims',
         'locator': 'Medicare_IFT_Series 2024 row: transports col B, '
                    'allowed per transport col G',
         'supplies': 'The claims-visible volume basis and the measured '
                     'Medicare-anchored price of the scenario grid; the '
                     'hardest-floor cell is their product',
         'url': 'https://data.cms.gov/summary-statistics-on-use-and-'
                'payments/medicare-medicaid-spending-by-provider/'
                'physician-supplier-procedure-summary',
         'tier': 'A', 'accessed': accessed, 'powers': ['Scenario_Matrix']},
        {'key': 'c123_nemsis_2024', 'publisher': 'NEMSIS TAC (NHTSA)',
         'document': 'NEMSIS National EMS Data Report 2024 (End-of-Year): '
                     'Hospital-to-Hospital Transfer activations, v3.5 '
                     'type-of-service table, as carried on EMS_Transports',
         'vintage': '2024',
         'locator': "EMS_Transports 'Hospital-to-Hospital Transfer' row "
                    '(5,510,664 activations)',
         'supplies': 'The NEMSIS-anchored volume basis of the scenario '
                     'grid (all-payer vehicle legs)',
         'url': 'https://nemsis.org/wp-content/uploads/2025/08/'
                'NEMSIS-End-of-Year-Report-2024.pdf',
         'tier': 'B', 'accessed': accessed, 'powers': ['Scenario_Matrix']},
    ]

    # =====================================================================
    # TAB 1 - Metro_TAM_Panels (C.1)
    # =====================================================================
    ws1 = wb.create_sheet('Metro_TAM_Panels')
    sb = lib.SheetBuilder(ws1, 7, col_widths=[48, 16, 16, 11, 42, 11, 46],
                          tab_color='FFC58F00')
    sb.title('Metro TAM panels: the mission-demand line and its priceable '
             'floor, one panel per target metro')
    sb.subtitle('The question: per target metro, what is the measured '
                'mission-demand line (catchment volume proxy x measured '
                'transfer rate) and how far can it be priced from public '
                'evidence alone? Sources: CMS Hospital Service Area 2025 '
                '(volume proxy, join key CCN), HCUP NEDS+NIS / AHA '
                '(transfer rate), CMS Ambulance Fee Schedule CY2026 '
                '(Medicare price), Insourcing_Bounds and Facility_Pay_Layer '
                '(gross-up anchors). Join keys: metro tab -> hospital '
                'roster (city+state filter) -> CCN -> HSA cases. Every '
                'unpriceable step is a bordered PENDING cell naming its '
                'public dataset; no panel asserts a metro TAM.')
    sb.note('DATA QUALITY: the catchment volume proxy is Medicare FFS '
            'inpatient cases from the CMS HSA file - a FLOOR of all-payer '
            'admissions (Medicare is roughly two-fifths of inpatient '
            'volume), and VA, psychiatric and children\'s hospitals carry '
            'no HSA row (matched counts disclosed per panel). The transfer '
            'rate denominator is AHA ALL-PAYER community-hospital '
            'admissions; applying it to Medicare-only cases keeps every '
            'mission-demand line a floor, and that confound is printed in '
            'each panel. Pricing is Medicare-anchored only at this stage; '
            'Medicaid, commercial and the two gross-up adders stay PENDING '
            'by design - the STRUCTURE is the deliverable.')
    sb.blank()
    sb.banner('How to read a panel (the row math, identical in all 20)')
    sb.prose('Rows 1-2 anchor the metro (hospital count, HCRIS staffed '
             'beds - green links into the metro tab, whose summary rows '
             'were located by scanning that tab for its shared-builder '
             'labels). Row 3 is the catchment volume proxy: the metro '
             'tabs carry no admissions or discharges row, so the stated '
             'proxy is HSA service-area Medicare FFS inpatient cases '
             'summed over the metro hospital CCNs (live SUMIF over '
             'HSA_Hospital_Catchment). Row 4 is the measured transfer '
             'rate (green, denominator disclosed in-row). Row 5 = row 3 x '
             'row 4, the mission-demand line. Row 6 is the NEMSIS '
             'cross-check (PENDING, named dataset). Rows 7-9 price it; '
             'rows 10-13 are the gross-up waterfall in fixed order '
             '(billing-in-lieu reclassification, eligible-but-unbilled, '
             'facility direct-pay), each citing its public evidence; '
             'row 14 is the priced total over live steps only - a floor.')
    sb.headers(['Sizing row', 'Value', 'Band / anchor', 'Basis',
                'Evidence and cell anchors', 'Units',
                'Confound / note (printed in-row)'])

    mission_rows, priced_rows, panel_names = [], [], []
    n_complete = 0
    total_cases_metro = 0

    for idx, tab in enumerate(metro_tabs, start=1):
        disp, states = meta_names.get(tab, (tab.replace('Metro_', ''), ''))
        mt = wb[tab]
        r_hosp = _find_row(mt, 'Hospitals (transfer origins')
        r_beds = _find_row(mt, 'HCRIS staffed beds')
        ccns = rosters.get(tab, [])
        matched = [c for c in ccns if c in cases]
        m_cases = sum(cases[c] for c in matched)
        total_cases_metro += m_cases
        live = bool(matched) and rate_ref and base_ref and hsa_ok
        if live:
            n_complete += 1

        sb.banner(f'Panel {idx}. {disp} ({states}) - source tab {tab}')
        sb.row([('Hospitals (transfer origins), Care Compare roster',
                 'label'),
                (f"='{tab}'!$B${r_hosp}", 'link', lib.FMT_INT)
                if r_hosp else PEND,
                None, ('SOURCED', 'note'),
                (f'{tab} Panel A (label scanned; shared metro builder)',
                 'note'), ('hospitals', 'note'), None])
        sb.row([('HCRIS staffed beds (conservative floor)', 'label'),
                (f"='{tab}'!$B${r_beds}", 'link', lib.FMT_INT)
                if r_beds else PEND,
                None, ('SOURCED', 'note'),
                (f'{tab} Panel B (label scanned)', 'note'),
                ('beds', 'note'), None])
        if matched:
            crit = ','.join(f'"{c}"' for c in matched)
            cases_cell = (f"=SUMPRODUCT(SUMIF('{HSA_TAB}'!$A:$A,"
                          f"{{{crit}}},'{HSA_TAB}'!$C:$C))", 'fml',
                          lib.FMT_INT)
        else:
            cases_cell = PEND
        sb.row([('Catchment volume proxy: Medicare FFS inpatient cases, '
                 'HSA service-area total over metro hospital CCNs',
                 'label'), cases_cell, None, ('DERIVED', 'note'),
                (f'CMS HSA 2025 via {HSA_TAB}; CCN roster from the metro '
                 'city+state filter (rcm_mc ift_geo)' if matched else
                 'PENDING dataset: CMS Hospital Service Area file 2025 '
                 '(no metro CCN matched an HSA row)', 'note'),
                ('cases/yr', 'note'),
                (f'{len(matched)} of {len(ccns)} roster hospitals have an '
                 'HSA row (VA/psych/children\'s excluded by the file); '
                 'Medicare-only cases = a floor of all-payer admissions',
                 'note')], wrap=True)
        r_cases = sb.r
        sb.row([('Measured transfer rate: mean IFT % of admissions, '
                 '2019-2023', 'label'),
                (f'={rate_ref}', 'link', lib.FMT_PCT2) if rate_ref else PEND,
                None, ('DERIVED', 'note'),
                ('Acute_IFT_Series (HCUP NEDS ED-origin + NIS '
                 'inpatient-origin episodes)', 'note'), ('% of adm.',
                                                         'note'),
                ('Denominator: AHA ALL-PAYER community-hospital '
                 'admissions; applied here to Medicare-only cases - the '
                 'product stays a floor', 'note')], wrap=True)
        r_rate = sb.r
        sb.row([('MISSION-DEMAND LINE: transfer episodes per year '
                 '(proxy-based floor)', 'label'),
                (f'=B{r_cases}*B{r_rate}', 'fml', lib.FMT_INT)
                if live else PEND,
                None, ('DERIVED', 'note'),
                ('row 3 x row 4, live', 'note'), ('episodes/yr', 'note'),
                ('Not a metro TAM; a demand floor on the stated proxy',
                 'note')])
        mission_rows.append(sb.r)
        sb.row([('NEMSIS cross-check: state interfacility activations, '
                 'metro split', 'label'), PEND, None, ('PENDING', 'note'),
                ('PENDING dataset: NEMSIS state research extract, '
                 'eResponse.05 interfacility activations (landing shape '
                 'NEMSIS_State_IFT; request logged on '
                 'Engagement_Data_Map)', 'note'), ('legs/yr', 'note'),
                None], wrap=True)
        sb.row([('Medicare-anchored $ per transport (A0428 BLS '
                 'non-emergency base, CY2026)', 'label'),
                (f'={base_ref}', 'link', lib.FMT_USD) if base_ref else PEND,
                None, ('GOV', 'note'),
                ('Derived_Rate_Card A0428 row, RVU x CY2026 CF (scanned)',
                 'note'), ('$/transport', 'note'),
                ('Base rate only - excludes mileage (43-45% of Medicare '
                 'IFT allowed $; see TAM_Assembly_State bridge) and '
                 'service-level mix', 'note')], wrap=True)
        r_price = sb.r
        sb.row([('Medicaid multiple of Medicare', 'label'),
                (f'={mcaid_ref}', 'link', lib.FMT_X) if mcaid_ref else PEND,
                None, ('PENDING' if not mcaid_ref else 'SOURCED', 'note'),
                ('Medicaid_Rate_Card (B.3 state fee-schedule survey)'
                 if mcaid_ref else
                 'PENDING dataset: state Medicaid ambulance fee schedules '
                 '(Medicaid_Rate_Card, B.3; may land late)', 'note'),
                ('x Medicare', 'note'), None])
        sb.row([('Commercial $ per transport', 'label'), PEND, None,
                ('PENDING', 'note'),
                ('PENDING dataset: Transparency-in-Coverage negotiated-'
                 'rate machine-readable files (landing shape '
                 'Commercial_Rate_MRF, empty schema shipped)', 'note'),
                ('$/transport', 'note'), None], wrap=True)
        sb.row([('Medicare-anchored mission revenue (floor $)', 'label'),
                (f'=B{mission_rows[-1]}*B{r_price}', 'fml', lib.FMT_USD)
                if live else PEND,
                None, ('DERIVED', 'note'),
                ('mission-demand line x Medicare base rate, live', 'note'),
                ('$/yr', 'note'),
                ('Floor on floor: Medicare-only volume proxy x base-only '
                 'rate', 'note')])
        r_rev = sb.r
        # gross-up waterfall, fixed order
        sb.row([('Gross-up 1: billing-in-lieu reclassification band '
                 '(hospital-billed share of base services)', 'label'),
                (f'=B{r_rev}*{ins_floor_ref}', 'link', lib.FMT_USD)
                if (live and ins_floor_ref) else PEND,
                (f'=B{r_rev}*{ins_ceil_ref}', 'link', lib.FMT_USD)
                if (live and ins_ceil_ref) else PEND,
                ('DERIVED', 'note'),
                ('Insourcing_Bounds 2024 national FLOOR (H1 AND H2) and '
                 'CEILING (H1 OR H2) shares, green' if ins_floor_ref else
                 'PENDING dataset: MUP provider name-rule bounds '
                 '(Insourcing_Bounds, A.4)', 'note'),
                ('$ band', 'note'),
                ('Reclassification WITHIN the floor (who bills), not an '
                 'adder; national carrier-claim shares applied to a metro '
                 'line - confound printed', 'note')], wrap=True)
        sb.row([('Gross-up 2: eligible-but-unbilled adder', 'label'),
                PEND,
                (f'={fp_unbilled_ref}', 'link', lib.FMT_PCT1)
                if fp_unbilled_ref else PEND,
                ('PENDING', 'note'),
                ('Anchor green: GADCS "about one in five" organizations '
                 'did not always bill (Facility_Pay_Layer, Table S.1)'
                 if fp_unbilled_ref else
                 'PENDING dataset: CMS/RAND GADCS Year 1-4 appendix, '
                 'Table S.1 (Facility_Pay_Layer, B.1)', 'note'),
                ('$ adder', 'note'),
                ('Anchor is incidence of ORGANIZATIONS, not a volume '
                 'share - the metro $ adder is unpriceable publicly; '
                 'needs GADCS microdata or a claims-vendor panel '
                 '(Claims_Vendor_Recv)', 'note')], wrap=True)
        sb.row([('Gross-up 3: facility direct-pay adder', 'label'),
                PEND,
                (f'={fp_incid_ref}', 'link', lib.FMT_PCT1)
                if fp_incid_ref else PEND,
                ('PENDING', 'note'),
                (('Anchors green: GADCS facility-contract incidence '
                  '(Facility_Pay_Layer Panel A)' if fp_incid_ref else
                  'PENDING dataset: GADCS Table 2.32 incidence '
                  '(Facility_Pay_Layer, B.1)') +
                 ('; observed rates ' +
                  ('green Contract_Corpus' if corpus_ref else
                   'PENDING Contract_Corpus (E.2 public contract '
                   'abstracts)')), 'note'),
                ('$ adder', 'note'),
                ('Incidence and existence are measured; the metro '
                 'IFT-specific facility-pay $ has no public source',
                 'note')], wrap=True)
        sb.row([('PRICED TOTAL over live steps only (= the '
                 'Medicare-anchored floor)', 'label'),
                (f'=B{r_rev}', 'fml', lib.FMT_USD) if live else PEND,
                None, ('DERIVED', 'note'),
                ('gross-up adders all PENDING, so the priced total '
                 'equals row 10 by construction', 'note'), ('$/yr',
                                                            'note'),
                ('A floor, and says so', 'note')])
        priced_rows.append(sb.r)
        panel_names.append(disp)

    # summary + recap (contiguous block for the chart and the live SUM)
    sb.blank()
    sb.banner('Panel S. Footprint summary (live over the 20 panels) + '
              'mission-demand recap')
    sum_mission = '=SUM(' + ','.join(f'B{r}' for r in mission_rows) + ')'
    sum_priced = '=SUM(' + ','.join(f'B{r}' for r in priced_rows) + ')'
    cnt_priced = '=COUNT(' + ','.join(f'B{r}' for r in priced_rows) + ')'
    sb.row([('Total mission-demand line over the 20 metros (proxy-based '
             'floor)', 'label'), (sum_mission, 'fml', lib.FMT_INT), None,
            ('DERIVED', 'note'), ('live SUM of the 20 mission-demand '
                                  'lines', 'note'), ('episodes/yr', 'note'),
            ('Fact F-1 of this tab', 'note')])
    r_sum_mission = sb.r
    sb.row([('Metros with complete Medicare-anchored pricing (proxy + '
             'rate + $ anchor all live)', 'label'),
            (cnt_priced, 'fml', lib.FMT_INT), None, ('DERIVED', 'note'),
            ('live COUNT over the 20 priced-total cells', 'note'),
            ('metros', 'note'), ('Fact F-2 of this tab', 'note')])
    sb.row([('Total Medicare-anchored mission revenue floor', 'label'),
            (sum_priced, 'fml', lib.FMT_USD), None, ('DERIVED', 'note'),
            ('live SUM of the 20 priced totals', 'note'), ('$/yr', 'note'),
            ('Floor, not a TAM: Medicare-only proxy x base-only rate',
             'note')])
    sb.blank()
    sb.headers(['Metro (recap for the chart)', 'Mission-demand line',
                '', '', '', '', ''])
    recap_first = sb.r + 1
    for name, r in zip(panel_names, mission_rows):
        sb.row([(name, 'text'), (f'=B{r}', 'fml', lib.FMT_INT), None, None,
                None, None, None])
    recap_last = sb.r
    sb.blank()
    sb.banner('Read panel')
    sb.prose('What is measured: a mission-demand floor per metro built '
             'from two public measurements (HSA catchment cases x the '
             'HCUP/AHA transfer rate) and priced only as far as public '
             'evidence reaches - the CY2026 Medicare base rate. The '
             'gross-up waterfall is structural: its anchors (insourcing '
             'floor/ceiling, the GADCS one-in-five unbilled anchor, the '
             '18.6% facility-contract incidence) are green and live, but '
             'every metro-level adder $ is PENDING with its dataset '
             'named. No panel asserts a metro TAM; the honest output is '
             'the floor and the named gaps.')
    if mission_rows:
        lib.add_chart(
            ws1, f'I{recap_first}',
            'Mission-demand line by metro (proxy-based floor)',
            f"'Metro_TAM_Panels'!$A${recap_first}:$A${recap_last}",
            [('Transfer episodes per year (floor)',
              f"'Metro_TAM_Panels'!$B${recap_first}:$B${recap_last}")],
            kind='bar', y_fmt=lib.FMT_INT)

    mission_total_val = (round(total_cases_metro * mean_rate)
                         if mean_rate else None)
    facts += [
        {'metric': 'Total mission-demand line over the 20 target metros '
                   '(HSA catchment cases x measured transfer rate, '
                   'proxy-based floor)',
         'year': 2025, 'value': mission_total_val,
         'unit': 'transfer episodes per year (floor)',
         'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['c123_hsa_catchment', 'c123_hcup_aha_rate'],
         'locator': 'Metro_TAM_Panels Panel S, live SUM over 20 '
                    'mission-demand lines',
         'lives_on': 'Metro_TAM_Panels',
         'cross_check': 'Medicare-only cases x all-payer rate: a floor '
                        'by construction; 20-metro HSA cases '
                        f'{total_cases_metro:,} x mean rate '
                        f'{(mean_rate or 0):.4f}'},
        {'metric': 'Target metros with complete Medicare-anchored pricing '
                   '(catchment proxy + transfer rate + CY2026 base rate '
                   'all live)',
         'year': 2026, 'value': n_complete, 'unit': 'metros (of 20)',
         'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['c123_afs_cy2026', 'c123_hsa_catchment'],
         'locator': 'Metro_TAM_Panels Panel S, live COUNT over the 20 '
                    'priced-total cells',
         'lives_on': 'Metro_TAM_Panels',
         'cross_check': 'Medicaid/commercial/gross-up adders are PENDING '
                        'in all 20 panels; only the Medicare anchor is '
                        'complete'},
    ]
    findings.append({
        'id_hint': 96,
        'finding': 'The 20-metro mission-demand line is measurable today '
                   'from public data alone - about '
                   f'{total_cases_metro:,} Medicare FFS catchment cases x '
                   'the measured 9.5% transfer rate gives a floor of '
                   f'roughly {mission_total_val:,} transfer episodes a '
                   'year across the footprint metros - but it can only be '
                   'PRICED to the Medicare base-rate anchor in all 20 '
                   'metros; every Medicaid, commercial and gross-up '
                   'dollar is a bordered PENDING cell naming its dataset.'
        if mission_total_val else
        'The 20-metro mission-demand structure is built; volume proxy '
        'PENDING where no HSA match exists.',
        'numbers': f"='Metro_TAM_Panels'!B{r_sum_mission}",
        'sources': 'c123_hsa_catchment; c123_hcup_aha_rate; '
                   'c123_afs_cy2026',
        'confidence': 'High on the floor arithmetic; the proxy is '
                      'Medicare-only and says so in every panel',
        'guardrail': 'No panel value is a metro TAM. The volume proxy is '
                     'a Medicare FFS floor, the rate denominator is '
                     'all-payer, and the confound is printed in each '
                     'panel row.'})

    # =====================================================================
    # TAB 2 - TAM_Assembly_State (C.2)
    # =====================================================================
    ws2 = wb.create_sheet('TAM_Assembly_State')
    sb = lib.SheetBuilder(ws2, 7, col_widths=[40, 17, 17, 17, 15, 15, 48],
                          tab_color='FFC58F00')
    sb.title('State TAM assembly: the same row math at state grain, '
             'reconciled to the carried top-down model')
    sb.subtitle('The question: run the metro row math at state grain for '
                'the ten footprint states plus a national roll-up - does '
                'the bottom-up assembly reconcile to TAM_Model_National, '
                'and where exactly do the two differ? Sources: CMS HSA '
                '2025 (cases by CCN, state = SSA CCN prefix), '
                'Acute_IFT_Series rate, Derived_Rate_Card CY2026 base, '
                'Insourcing_Bounds Panel C state shares. Join key: CCN '
                'prefix -> state. The bridge panel lists every difference '
                'with green links to both sides; the SAM filter row '
                'states its grouping rule.')
    sb.note('DATA QUALITY: state volume is the same Medicare FFS HSA '
            'proxy as the metro panels (floor of all-payer admissions; '
            'VA/psych/children\'s hospitals absent). The transfer rate is '
            'national, not state-specific - state case mix and rurality '
            'shift the true rate and that confound is printed on every '
            'state row. Insourcing shares are name-rule bounds, not a '
            'census. Nothing on this tab is a TAM; the national roll-up '
            'is labeled the proxy floor it is.')
    sb.blank()
    sb.banner('Panel A. The shared spine (green anchors used by every '
              'state row)')
    sb.row([('Measured transfer rate, mean IFT % of admissions '
             '2019-2023', 'label'),
            (f'={rate_ref}', 'link', lib.FMT_PCT2) if rate_ref else PEND,
            None, None,
            None, None,
            ('Denominator: AHA all-payer community-hospital admissions '
             '(HCUP NEDS+NIS numerator) - disclosed here and applied to '
             'Medicare-only cases below', 'note')], wrap=True)
    r2_rate = sb.r
    sb.row([('Medicare-anchored $ per transport (A0428 base, CY2026)',
             'label'),
            (f'={base_ref}', 'link', lib.FMT_USD) if base_ref else PEND,
            None, None, None, None,
            ('Base only; mileage excluded (43-45% of Medicare IFT '
             'allowed $)', 'note')])
    r2_price = sb.r
    sb.blank()
    sb.banner('Panel B. State-grain assembly (footprint states + national '
              'roll-up)')
    sb.headers(['State', 'HSA cases (Medicare FFS)', 'Mission-demand '
                'proxy', 'Medicare-anchored $ floor', 'Insourcing floor '
                'share', 'Insourcing ceiling share', 'Note'])
    state_first = sb.r + 1
    hsa_rng_a = f"'{HSA_TAB}'!$A:$A"
    hsa_rng_c = f"'{HSA_TAB}'!$C:$C"
    state_case_vals = {}
    for st, pfx in _FOOTPRINT:
        st_cases = sum(v for k, v in cases.items() if k.startswith(pfx))
        state_case_vals[st] = st_cases
        r = sb.r + 1
        insf, insc = ins_state.get(st, (None, None))
        sb.row([(st, 'text'),
                (f'=SUMIF({hsa_rng_a},"{pfx}*",{hsa_rng_c})', 'fml',
                 lib.FMT_INT) if hsa_ok else PEND,
                (f'=B{r}*$B${r2_rate}', 'fml', lib.FMT_INT)
                if (hsa_ok and rate_ref) else PEND,
                (f'=C{r}*$B${r2_price}', 'fml', lib.FMT_USD)
                if (hsa_ok and rate_ref and base_ref) else PEND,
                (f'={insf}', 'link', lib.FMT_PCT1) if insf else PEND,
                (f'={insc}', 'link', lib.FMT_PCT1) if insc else PEND,
                (f'CCN prefix "{pfx}"; national rate applied - state '
                 'case mix confound', 'note')])
    state_last = sb.r
    sb.row([('FOOTPRINT (10 states)', 'label'),
            (f'=SUM(B{state_first}:B{state_last})', 'fml', lib.FMT_INT),
            (f'=SUM(C{state_first}:C{state_last})', 'fml', lib.FMT_INT),
            (f'=SUM(D{state_first}:D{state_last})', 'fml', lib.FMT_USD),
            None, None,
            ('provisional footprint; matches Insourcing_Bounds Panel C',
             'note')])
    r2_foot = sb.r
    nat_cases_total = sum(v for v in cases.values())
    sb.row([('NATIONAL roll-up (all CCNs in the HSA file)', 'label'),
            (f"=SUM('{HSA_TAB}'!$C${hsa_first}:$C${hsa_last})", 'fml',
             lib.FMT_INT) if hsa_ok else PEND,
            (f'=B{sb.r + 1}*$B${r2_rate}', 'fml', lib.FMT_INT)
            if (hsa_ok and rate_ref) else PEND,
            (f'=C{sb.r + 1}*$B${r2_price}', 'fml', lib.FMT_USD)
            if (hsa_ok and rate_ref and base_ref) else PEND,
            (f'={ins_floor_ref}', 'link', lib.FMT_PCT1)
            if ins_floor_ref else PEND,
            (f'={ins_ceil_ref}', 'link', lib.FMT_PCT1)
            if ins_ceil_ref else PEND,
            ('the bottom-up side of the bridge below', 'note')])
    r2_nat = sb.r
    sb.blank()
    sb.banner('Panel C. Bridge: this bottom-up assembly vs the carried '
              'top-down scenario model (row per difference, green links '
              'both sides)')
    sb.headers(['Difference', 'Bottom-up side (this tab)',
                'Top-down side (TAM_Model_National)', 'Direction', '', '',
                'Why (stated, public)'])
    tam_c = tam.get('tam', {}).get('C')
    seg_c = tam.get('seg', {}).get('C')
    vol_c = tam.get('vol', {}).get('C')
    ppt_b = tam.get('ppt', {}).get('B')
    sb.row([('Segment scope', 'label'),
            (f'=D{r2_nat}', 'fml', lib.FMT_USD),
            (f'={tam_c}', 'link', lib.FMT_USD) if tam_c else PEND,
            ('top-down higher', 'text'), None, None,
            ('The model prices ALL reimbursed ground ambulance (911 + '
             'IFT, five payer books); this assembly prices acute-to-acute '
             'IFT mission demand only', 'note')], wrap=True)
    sb.row([('The model\'s own scheduled/IFT segment', 'label'),
            (f'=D{r2_nat}', 'fml', lib.FMT_USD),
            (f'={seg_c}', 'link', lib.FMT_USD) if seg_c else PEND,
            ('top-down higher', 'text'), None, None,
            ('Model segment = Medicare CODE mix (non-emergency + SCT + '
             'ALS2) applied across payers; this tab = HCUP transfer '
             'EPISODE definition - different segment definitions, '
             'never mixed', 'note')], wrap=True)
    sb.row([('Volume basis and payer scope', 'label'),
            (f'=B{r2_nat}', 'fml', lib.FMT_INT),
            (f'={vol_c}', 'link', lib.FMT_DEC1) if vol_c else PEND,
            ('assembly lower', 'text'), None, None,
            ('Bottom-up counts Medicare FFS inpatient CASES (HSA); '
             'top-down builds all-payer TRANSPORTS from lives '
             '(top-down cell is in millions) - payer scope and unit '
             'both differ', 'note')], wrap=True)
    sb.row([('Price basis', 'label'),
            (f'=$B${r2_price}', 'fml', lib.FMT_USD),
            (f'={ppt_b}', 'link', lib.FMT_USD) if ppt_b else PEND,
            ('assembly lower', 'text'), None, None,
            ('A0428 base only vs measured allowed per transport incl '
             'mileage' +
             (' (mileage share green: see Medicare_IFT_Series)' if
              mis_mileshare_ref else ''), 'note')], wrap=True)
    sb.row([('Episode vs leg vs billed-transport counting', 'label'),
            (f'={epi_mean_ref}', 'link', lib.FMT_INT)
            if epi_mean_ref else PEND,
            (f'={ems_ref}', 'link', lib.FMT_INT) if ems_ref else PEND,
            ('differs by unit', 'text'), None, None,
            ('HCUP counts sending-side episodes; NEMSIS counts vehicle '
             'legs; claims count billed transports - one transfer can '
             'appear once, twice or zero times depending on the counter',
             'note')], wrap=True)
    sb.row([('Gross-up layers (unbilled; facility direct-pay)', 'label'),
            PEND, ('not in the model (reimbursed spend only)', 'text'),
            ('both understate', 'text'), None, None,
            ('No public IFT-specific volume share exists for either '
             'layer; anchors live on Facility_Pay_Layer; PENDING GADCS '
             'microdata / claims-vendor panel (Claims_Vendor_Recv)',
             'note')], wrap=True)
    sb.blank()
    sb.banner('Panel D. SAM filter: multi-hospital-system share of the '
              'footprint')
    sb.row([('Grouping rule (printed): a system family = hospitals '
             'sharing a health-system crosswalk ID (AHRQ Compendium of '
             'US Health Systems); interim name-family rule = shared '
             'leading corporate token in the Care Compare name', 'label'),
            PEND, None, ('PENDING', 'note'), None, None,
            ('PENDING dataset: AHRQ Compendium hospital-to-system '
             'crosswalk (built on the AHA Annual Survey license); '
             'Hosp_Registry carries name/city/state/ownership but no '
             'system field, so the share is not computed from a weaker '
             'proxy', 'note')], wrap=True)
    sb.blank()
    sb.banner('Read panel')
    sb.prose('What the bridge shows: the bottom-up assembly and the '
             'top-down model are different instruments and the panel '
             'prints why, difference by difference - segment scope (IFT '
             'mission demand vs all ground), payer scope (Medicare FFS '
             'proxy vs five payer books), price basis (base-only vs '
             'measured allowed including mileage), counting unit '
             '(episodes vs legs vs billed transports), and the gross-up '
             'layers both sides leave unpriced. The assembly is the '
             'auditable floor; the model is the scenario envelope; '
             'neither is quoted as a single TAM.')
    if hsa_ok and state_first <= state_last:
        lib.add_chart(
            ws2, f'I{state_first}',
            'Mission-demand proxy by footprint state (floor)',
            f"'TAM_Assembly_State'!$A${state_first}:$A${state_last}",
            [('Transfer episodes per year (proxy floor)',
              f"'TAM_Assembly_State'!$C${state_first}:$C${state_last}")],
            kind='bar', y_fmt=lib.FMT_INT)

    foot_cases = sum(state_case_vals.values())
    foot_floor_val = (round(foot_cases * mean_rate * base_val)
                      if (mean_rate and base_val) else None)
    facts += [
        {'metric': 'Footprint-10-state Medicare-anchored assembly floor '
                   '(HSA cases x transfer rate x CY2026 A0428 base)',
         'year': 2025, 'value': foot_floor_val, 'unit': 'USD per year '
         '(floor)', 'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['c123_hsa_catchment', 'c123_hcup_aha_rate',
                         'c123_afs_cy2026'],
         'locator': 'TAM_Assembly_State Panel B FOOTPRINT row, col D '
                    '(live SUM)',
         'lives_on': 'TAM_Assembly_State',
         'cross_check': f'{foot_cases:,} footprint HSA cases; Medicare-'
                        'only volume x base-only rate keeps it a floor'},
        {'metric': 'National HSA service-area Medicare FFS inpatient '
                   'case roll-up (all CCNs)',
         'year': 2025, 'value': nat_cases_total, 'unit': 'cases',
         'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['c123_hsa_catchment'],
         'locator': 'TAM_Assembly_State Panel B NATIONAL row, col B '
                    '(live SUM over HSA_Hospital_Catchment)',
         'lives_on': 'TAM_Assembly_State',
         'cross_check': 'x the 9.5% rate gives about 1.34M proxy '
                        'episodes vs about 3.06M measured all-payer HCUP '
                        'episodes - the Medicare-slice gap the bridge '
                        'panel prints'},
    ]
    findings.append({
        'id_hint': 97,
        'finding': 'The bottom-up vs top-down bridge shows the two sizing '
                   'instruments differ by construction, not by error: '
                   'the state assembly (Medicare FFS HSA cases x the '
                   'measured 9.5% transfer rate x the CY2026 base rate) '
                   'is an auditable FLOOR - about '
                   f'{foot_floor_val:,} dollars a year across the ten '
                   'footprint states - while TAM_Model_National prices '
                   'all reimbursed ground ambulance across five payer '
                   'books under printed gates; the bridge panel lists '
                   'every difference (segment, payer scope, price basis, '
                   'counting unit, gross-up layers) with green links to '
                   'both sides.' if foot_floor_val else
                   'Bridge built; assembly volume PENDING.',
        'numbers': f"='TAM_Assembly_State'!D{r2_foot}",
        'sources': 'c123_hsa_catchment; c123_hcup_aha_rate; '
                   'c123_afs_cy2026',
        'confidence': 'High on the arithmetic; the reconciliation is '
                      'structural, so no residual is forced to zero',
        'guardrail': 'Neither side of the bridge is quoted as a TAM. The '
                     'assembly is a Medicare-scoped floor with a '
                     'national-rate confound printed per state row; the '
                     'model is scenario arithmetic under its own gates.'})

    # =====================================================================
    # TAB 3 - Scenario_Matrix (C.3)
    # =====================================================================
    ws3 = wb.create_sheet('Scenario_Matrix')
    sb = lib.SheetBuilder(ws3, 7, col_widths=[42, 15, 14, 14, 46, 16, 44],
                          tab_color='FFC58F00')
    sb.title('Scenario matrix: three volume bases x three price bases, '
             'live where measured, PENDING where not')
    sb.subtitle('The question: across volume bases (claims-visible / '
                'NEMSIS-anchored / gross-up-full) and price bases '
                '(Medicare-anchored / blended-observed / MRF-forward), '
                'which sizing cells are live from public evidence today, '
                'and what would close each gate? Sources: PSPS-derived '
                'Medicare_IFT_Series (claims floor), NEMSIS 2024 '
                '(EMS_Transports), Insourcing_Bounds, Facility_Pay_Layer, '
                'TAM_Model_National. No cell of this grid is "the TAM"; '
                'the grid IS the answer, and its gates are printed below '
                'it.')
    sb.note('DATA QUALITY: the claims-visible basis is Medicare FFS '
            'carrier claims only (hospital institutional billing '
            'excluded); the NEMSIS basis counts all-payer vehicle legs '
            'from a voluntary-participation registry (54 states/'
            'territories, coverage grew over time); gross-up volume '
            'shares have no public source and stay PENDING. Blended and '
            'MRF price bases await Medicaid_Rate_Card, Contract_Corpus '
            'rate extraction and Transparency-in-Coverage files. Mixing '
            'any cell across rows or columns re-introduces the exact '
            'double-counting this grid exists to prevent.')
    sb.blank()
    sb.banner('Panel A. The bases (each a green link to its measured '
              'cell, or PENDING naming its dataset)')
    sb.headers(['Basis', 'Value', '', '', 'Source / dataset named', '',
                'Note'])
    sb.row([('V1 claims-visible volume: Medicare FFS hospital-to-'
             'hospital transports, 2024', 'label'),
            (f'={mis_vol_ref}', 'link', lib.FMT_INT) if mis_vol_ref
            else PEND, None, None,
            ('Medicare_IFT_Series 2024 row (PSPS-derived carrier '
             'claims)', 'note'), None,
            ('the hardest, fully measured volume', 'note')])
    r_v1 = sb.r
    sb.row([('V2 NEMSIS-anchored volume: hospital-to-hospital '
             'activations, 2024', 'label'),
            (f'={ems_ref}', 'link', lib.FMT_INT) if ems_ref else PEND,
            None, None,
            ('EMS_Transports v3.5 type-of-service table (NEMSIS 2024 '
             'End-of-Year report)', 'note'), None,
            ('all-payer vehicle LEGS, not billed transports', 'note')])
    r_v2 = sb.r
    sb.row([('V3 gross-up-full volume: claims-visible + unbilled + '
             'facility-paid', 'label'), PEND, None, None,
            ('PENDING datasets: IFT-specific unbilled volume share '
             '(GADCS microdata beyond the published one-in-five '
             'incidence) + facility-pay volume share (claims-vendor '
             'panel, Claims_Vendor_Recv; NEMSIS_State_IFT for the state '
             'wedge)', 'note'), None,
            ('anchors are live on Facility_Pay_Layer; the SHARES are '
             'not public', 'note')], wrap=True)
    r_v3 = sb.r
    sb.row([('P1 Medicare-anchored price: measured allowed per '
             'transport, 2024 (incl mileage)', 'label'),
            (f'={mis_ppt_ref}', 'link', lib.FMT_USD) if mis_ppt_ref
            else PEND, None, None,
            ('Medicare_IFT_Series 2024 row, allowed per transport',
             'note'), None,
            ('reference only: A0428 base-only anchor used at metro '
             'grain sits on Derived_Rate_Card', 'note')], wrap=True)
    r_p1 = sb.r
    sb.row([('P2 blended-observed price', 'label'), PEND, None, None,
            ('PENDING datasets: state Medicaid ambulance fee schedules '
             '(Medicaid_Rate_Card, B.3) + observed public contract '
             'rates (Contract_Corpus, E.2)' if not (mcaid_ref and
                                                    corpus_ref) else
             'Medicaid_Rate_Card + Contract_Corpus (green when '
             'extracted)', 'note'), None,
            ('blend weights would also need payer-mix evidence', 'note')])
    r_p2 = sb.r
    sb.row([('P3 MRF-forward price', 'label'), PEND, None, None,
            ('PENDING dataset: Transparency-in-Coverage negotiated-rate '
             'machine-readable files (landing shape Commercial_Rate_MRF, '
             'shipped as an empty schema)', 'note'), None, None],
           wrap=True)
    sb.blank()
    sb.banner('Panel B. The 3x3 grid (LIVE formula where both bases '
              'exist; PENDING names the missing input)')
    sb.headers(['Volume basis \\ price basis', 'Medicare-anchored',
                'Blended-observed', 'MRF-forward', '', '', 'Gate / note'])
    v1p1_live = bool(mis_vol_ref and mis_ppt_ref)
    sb.row([('Claims-visible', 'label'),
            (f'=B{r_v1}*B{r_p1}', 'fml', lib.FMT_USD) if v1p1_live
            else PEND,
            PEND, PEND, None, None,
            ('THE HARDEST FLOOR: fully measured (equals 2024 Medicare '
             'FFS IFT allowed dollars)', 'note')])
    r_g1 = sb.r
    sb.row([('NEMSIS-anchored', 'label'),
            (f'=B{r_v2}*B{r_p1}', 'fml', lib.FMT_USD)
            if (ems_ref and mis_ppt_ref) else PEND,
            PEND, PEND, None, None,
            ('applies the Medicare price to ALL-PAYER legs - a scale '
             'read under gate G2, NOT a TAM', 'note')])
    r_g2 = sb.r
    sb.row([('Gross-up-full', 'label'), PEND, PEND, PEND, None, None,
            ('PENDING: unbilled + facility-pay volume shares (datasets '
             'named in Panel A row V3)', 'note')])
    r_g3 = sb.r
    sb.row([('Gate G1: NEMSIS x Medicare cell contains the claims floor',
             'label'),
            (f'=IF(B{r_g2}>=B{r_g1},"PASS","FAIL")', 'fml')
            if (v1p1_live and ems_ref) else PEND,
            None, None, None, None,
            ('containment gate: legs must be at least billed transports',
             'note')])
    sb.row([('Gate G2: NEMSIS legs vs claims transports (volume '
             'containment)', 'label'),
            (f'=IF(B{r_v2}>=B{r_v1},"PASS","FAIL")', 'fml')
            if (mis_vol_ref and ems_ref) else PEND,
            None, None, None, None,
            ('if this fails, no scenario arithmetic is run on this grid',
             'note')])
    sb.row([('Honesty metric: LIVE grid cells (of 9)', 'label'),
            (f'=COUNT(B{r_g1}:D{r_g1},B{r_g2}:D{r_g2},B{r_g3}:D{r_g3})',
             'fml', lib.FMT_INT), None, None, None, None,
            ('PENDING cells = 9 minus this count; each names its '
             'dataset', 'note')])
    r_live_cnt = sb.r
    sb.blank()
    sb.banner('Panel C. Tornado: five levers, public bounds only, swings '
              'live against the grid and assembly cells')
    sb.headers(['Lever', 'Base value', 'Low bound', 'High bound',
                'Public source of the bounds', 'Output swing $',
                'Swings which output / confound'])
    torn_first = sb.r + 1
    lever_live = []
    # 1 transfer rate
    l1 = bool(rate_ref and rate_lo_ref and rate_hi_ref)
    sb.row([('Transfer rate (IFT % of admissions)', 'text'),
            (f'={rate_ref}', 'link', lib.FMT_PCT2) if l1 else PEND,
            (f'={rate_lo_ref}', 'link', lib.FMT_PCT2) if l1 else PEND,
            (f'={rate_hi_ref}', 'link', lib.FMT_PCT2) if l1 else PEND,
            ('HCUP NEDS+NIS / AHA annual ratio band, 2019-2023 '
             '(Acute_IFT_Series min/max rows)', 'note'),
            (f"='TAM_Assembly_State'!$D${r2_foot}*(D{sb.r + 1}"
             f"-C{sb.r + 1})/B{sb.r + 1}", 'fml', lib.FMT_USD)
            if l1 else PEND,
            ('swings the bottom-up FOOTPRINT assembly (TAM_Assembly_'
             'State), not the claims floor - the floor is measured',
             'note')], wrap=True)
    lever_live.append(l1)
    # 2 commercial multiple
    cm = tam.get('cmult', {})
    l2 = bool(cm.get('B') and cm.get('C') and cm.get('D')
              and tam.get('cvol', {}).get('C') and tam.get('ppt', {}).get('B'))
    sb.row([('Commercial multiple of Medicare', 'text'),
            (f"={cm.get('C')}", 'link', lib.FMT_X) if l2 else PEND,
            (f"={cm.get('B')}", 'link', lib.FMT_X) if l2 else PEND,
            (f"={cm.get('D')}", 'link', lib.FMT_X) if l2 else PEND,
            ('Low = pinned cross-year FAIR Health ground multiple '
             '(Payer_Rates_Commercial); high = the model\'s published-'
             'bounds high (TAM_Model_National assumption register)',
             'note'),
            (f"=({cm.get('D')}-{cm.get('B')})*{tam.get('cvol', {}).get('C')}"
             f"*1000000*{tam.get('ppt', {}).get('B')}", 'fml', lib.FMT_USD)
            if l2 else PEND,
            ('swings the top-down commercial book at base volume '
             '(TAM_Model_National Panel F)', 'note')], wrap=True)
    lever_live.append(l2)
    # 3 MA gross-up
    ma_lo = tam.get('ma_lo', {}).get('B')
    l3 = bool(fp_ma_ref and ma_lo and v1p1_live)
    sb.row([('MA gross-up (MA book calibrator)', 'text'),
            (f'={fp_ma_ref}', 'link', lib.FMT_X) if fp_ma_ref else PEND,
            (f'={ma_lo}', 'link', lib.FMT_X) if l3 else PEND,
            (f'={fp_ma_ref}', 'link', lib.FMT_X) if l3 else PEND,
            ('High = GADCS Table 2.30 MA-to-FFS revenue per NPI, 1.038x '
             '(Facility_Pay_Layer calibrator); low = fee-schedule parity '
             '(TAM_Model_National MA-multiple low)', 'note'),
            (f'=B{r_g1}*(D{sb.r + 1}-C{sb.r + 1})', 'fml', lib.FMT_USD)
            if l3 else PEND,
            ('MA-book adder bound on the claims floor; a per-NPI revenue '
             'ratio, not a price index - confound printed', 'note')],
           wrap=True)
    lever_live.append(l3)
    # 4 unbilled share
    l4 = bool(fp_unbilled_ref and v1p1_live)
    sb.row([('Unbilled share (eligible-but-unbilled)', 'text'),
            (f'={fp_unbilled_ref}', 'link', lib.FMT_PCT1) if l4 else PEND,
            (0, 'src', lib.FMT_PCT1) if l4 else PEND,
            (f'={fp_unbilled_ref}', 'link', lib.FMT_PCT1) if l4 else PEND,
            ('GADCS Table S.1 "about one in five" organizations did not '
             'always bill (Facility_Pay_Layer); low = definitional zero '
             '(all bill)', 'note'),
            (f'=B{r_g1}*(D{sb.r + 1}-C{sb.r + 1})', 'fml', lib.FMT_USD)
            if l4 else PEND,
            ('incidence of ORGANIZATIONS used as an upper VOLUME bound - '
             'stated, not measured', 'note')], wrap=True)
    lever_live.append(l4)
    # 5 facility-pay share
    l5 = bool(fp_incid_ref and v1p1_live)
    sb.row([('Facility-pay share (direct-pay layer)', 'text'),
            (f'={fp_incid_ref}', 'link', lib.FMT_PCT1) if l5 else PEND,
            (0, 'src', lib.FMT_PCT1) if l5 else PEND,
            (f'={fp_incid_ref}', 'link', lib.FMT_PCT1) if l5 else PEND,
            ('GADCS Table 2.32 facility-contract incidence 18.6% '
             '(Facility_Pay_Layer Panel A); DocGo books about 41% of '
             'transport revenue outside per-trip claims - existence at '
             'one operator, not a bound; low = definitional zero',
             'note'),
            (f'=B{r_g1}*(D{sb.r + 1}-C{sb.r + 1})', 'fml', lib.FMT_USD)
            if l5 else PEND,
            ('incidence used as an upper bound on the claims floor; the '
             'IFT-specific share has no public source', 'note')],
           wrap=True)
    lever_live.append(l5)
    torn_last = sb.r
    sb.note('Tornado read: swings are LIVE formulas against the grid '
            'floor cell (B' + str(r_g1) + '), the footprint assembly and '
            'the carried model - never against a typed number. A lever '
            'without public bounds would stay a PENDING row; the chart '
            'renders only when every lever row is live.')
    sb.blank()
    sb.banner('Read panel')
    sb.prose('The grid is the answer. The one fully measured cell - '
             'claims-visible volume x the measured Medicare allowed per '
             'transport - is the hardest floor, and it equals 2024 '
             'Medicare FFS interfacility allowed dollars by construction. '
             'The NEMSIS-anchored row shows the all-payer volume scale '
             'under gate G2. Every other cell is PENDING and names what '
             'closes it: Medicaid_Rate_Card and Contract_Corpus rate '
             'extraction (blended-observed), Transparency-in-Coverage '
             'files (MRF-forward), and GADCS microdata or a '
             'claims-vendor panel (gross-up-full). No cell of this grid '
             'is "the TAM".')
    if all(lever_live):
        lib.add_chart(
            ws3, f'I{torn_first}',
            'Tornado: output swing by lever (public bounds, live cells '
            'only)',
            f"'Scenario_Matrix'!$A${torn_first}:$A${torn_last}",
            [('Output swing $',
              f"'Scenario_Matrix'!$F${torn_first}:$F${torn_last}")],
            kind='bar', y_fmt=lib.FMT_USD)

    n_live_grid = int(v1p1_live) + int(bool(ems_ref and mis_ppt_ref))
    facts += [
        {'metric': 'Claims-visible x Medicare-anchored grid cell (the '
                   'hardest floor): 2024 Medicare FFS hospital-to-'
                   'hospital transports x measured allowed per transport',
         'year': 2024, 'value': (round(mis_allowed_val, 2)
                                 if mis_allowed_val else None),
         'unit': 'USD (allowed, 2024)', 'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['c123_psps_ift'],
         'locator': 'Scenario_Matrix Panel B, claims-visible row, '
                    'Medicare-anchored column (live product)',
         'lives_on': 'Scenario_Matrix',
         'cross_check': 'Equals Medicare_IFT_Series 2024 total allowed '
                        '(base + mileage) by construction: '
                        f'{mis_vol_val:,} transports' if mis_vol_val
                        else 'PENDING'},
        {'metric': 'Live cells in the 3x3 scenario grid (honesty '
                   'metric)', 'year': 2026, 'value': n_live_grid,
         'unit': 'grid cells live (of 9)', 'basis': 'DERIVED',
         'tier': 'A',
         'source_keys': ['c123_psps_ift', 'c123_nemsis_2024'],
         'locator': 'Scenario_Matrix Panel B honesty-metric row (live '
                    'COUNT over the nine grid cells)',
         'lives_on': 'Scenario_Matrix',
         'cross_check': f'{9 - n_live_grid} PENDING cells, each naming '
                        'the dataset that closes it'},
    ]
    findings.append({
        'id_hint': 98,
        'finding': 'The hardest floor of the sizing math is fully '
                   'measured: the claims-visible x Medicare-anchored '
                   'cell equals 2024 Medicare FFS interfacility allowed '
                   'dollars (about '
                   f'{round(mis_allowed_val):,} on '
                   f'{mis_vol_val:,} transports). Of the nine grid '
                   f'cells, {n_live_grid} are live and '
                   f'{9 - n_live_grid} are PENDING with their gates '
                   'named: blended-observed price waits on '
                   'Medicaid_Rate_Card plus Contract_Corpus rate '
                   'extraction, MRF-forward waits on Transparency-in-'
                   'Coverage file pulls (Commercial_Rate_MRF), and '
                   'gross-up-full volume waits on an IFT-specific '
                   'unbilled and facility-pay volume share (GADCS '
                   'microdata or a claims-vendor panel).'
                   if (mis_allowed_val and mis_vol_val) else
                   'Grid built; floor PENDING.',
        'numbers': f"='Scenario_Matrix'!B{r_g1}",
        'sources': 'c123_psps_ift; c123_nemsis_2024; c123_hcup_aha_rate',
        'confidence': 'High on the floor (final-action claims); the '
                      'tornado bounds are public but coarse',
        'guardrail': 'No cell of this grid is "the TAM"; the grid IS '
                     'the answer. Cells must not be mixed across rows '
                     'or columns, and the NEMSIS row is a scale read '
                     'under gate G2, not a market size.'})

    return {'facts': facts, 'sources': sources, 'excluded': excluded,
            'findings': findings,
            'meta': {
                'metro_anchor': 'Metro tabs scanned for the shared-builder '
                                'labels "Hospitals (transfer origins)" and '
                                '"HCRIS staffed beds"; catchment proxy = '
                                'HSA service-area cases over the ift_geo '
                                'city+state CCN roster (metro tabs carry '
                                'no admissions row)',
                'metros_priced_medicare': n_complete,
                'live_grid_cells': n_live_grid,
                'pending_grid_cells': 9 - n_live_grid,
                'tornado_all_live': all(lever_live)}}
