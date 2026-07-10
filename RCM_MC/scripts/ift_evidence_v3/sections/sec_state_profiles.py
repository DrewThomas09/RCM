"""SP family — one live-formula profile tab per state (50 + DC) plus SP_Index.

Every VALUE cell on every profile is a black live Excel formula (kind='fml')
over the workbook's detail tabs, referenced by whole-column ranges:
  Enroll_State_2013 / Enroll_State_2024  (A=name, B=abbrev, C tot, D FFS,
      E MA&other, H aged ESRD, J disabled ESRD; data from row 5)
  MUP_State_2013 / MUP_State_2019 / MUP_State_2024  (A=name, C=HCPCS,
      E providers, F benes, G services, J avg allowed $)
  PECOS_Registry (E=abbrev, one row per enrolled ambulance supplier)
  QCEW_EMS_Employment Panel C (A=name, C estabs, D employment, F avg pay)
  Facility_Universe_State (A=abbrev, B..J facility counts/beds)
  Market_Saturation_Ambulance Panel B (A=abbrev, B=type, C providers,
      E users, G payment) and Panel C (A=abbrev, B=n counties NUMERIC,
      C suppressed/0, D 1-2 providers) — Panel C reached with a
      SUMPRODUCT((A=abbrev)*ISNUMBER(B),...) discriminator because state
      abbrevs repeat in Panel B (text service type in B).
  MS_County_2025 (A=service type, C=abbrev, county grain)
The ONLY typed cells are the state name/abbrev lookup keys and labels.
Those detail tabs do not exist in the harness test workbook — the formulas
are saved as strings and resolve at assembly; nothing is evaluated here.
"""

PURPLE = 'FF7A5195'

STATES = [
    ('Alabama', 'AL'), ('Alaska', 'AK'), ('Arizona', 'AZ'), ('Arkansas', 'AR'),
    ('California', 'CA'), ('Colorado', 'CO'), ('Connecticut', 'CT'),
    ('Delaware', 'DE'), ('District of Columbia', 'DC'), ('Florida', 'FL'),
    ('Georgia', 'GA'), ('Hawaii', 'HI'), ('Idaho', 'ID'), ('Illinois', 'IL'),
    ('Indiana', 'IN'), ('Iowa', 'IA'), ('Kansas', 'KS'), ('Kentucky', 'KY'),
    ('Louisiana', 'LA'), ('Maine', 'ME'), ('Maryland', 'MD'),
    ('Massachusetts', 'MA'), ('Michigan', 'MI'), ('Minnesota', 'MN'),
    ('Mississippi', 'MS'), ('Missouri', 'MO'), ('Montana', 'MT'),
    ('Nebraska', 'NE'), ('Nevada', 'NV'), ('New Hampshire', 'NH'),
    ('New Jersey', 'NJ'), ('New Mexico', 'NM'), ('New York', 'NY'),
    ('North Carolina', 'NC'), ('North Dakota', 'ND'), ('Ohio', 'OH'),
    ('Oklahoma', 'OK'), ('Oregon', 'OR'), ('Pennsylvania', 'PA'),
    ('Rhode Island', 'RI'), ('South Carolina', 'SC'), ('South Dakota', 'SD'),
    ('Tennessee', 'TN'), ('Texas', 'TX'), ('Utah', 'UT'), ('Vermont', 'VT'),
    ('Virginia', 'VA'), ('Washington', 'WA'), ('West Virginia', 'WV'),
    ('Wisconsin', 'WI'), ('Wyoming', 'WY'),
]

GROUND = ['A0426', 'A0427', 'A0428', 'A0429', 'A0433', 'A0434']
MSA = 'Market_Saturation_Ambulance'
EMER_NONEMER = 'Ambulance (Emergency & Non-Emergency)'

SHEETS = ([{'name': 'SP_Index', 'tab_color': PURPLE}]
          + [{'name': f'SP_{ab}', 'tab_color': PURPLE} for _, ab in STATES])


def _ground(tab, key):
    """Six-term SUMIFS sum of ground base-code services for one state."""
    terms = [f'SUMIFS({tab}!G:G,{tab}!A:A,{key},{tab}!C:C,"{c}")' for c in GROUND]
    return '=' + '+'.join(terms)


def _idx(tab, col, key, keycol='A'):
    return (f'=IFERROR(INDEX({tab}!{col}:{col},'
            f'MATCH({key},{tab}!{keycol}:{keycol},0)),"n/a")')


def _profile(wb, lib, name, ab):
    ws = wb.create_sheet(f'SP_{ab}')
    sb = lib.SheetBuilder(ws, 6, col_widths=[41, 14, 17, 10, 27, 36],
                          tab_color=PURPLE)
    sb.title(f'State profile — {name} ({ab})')
    sb.subtitle(
        'The question: what does the Medicare transport market look like in '
        f'{name} — beneficiary base and MA erosion, ground ambulance '
        'utilization, supplier and EMS-workforce supply, facility '
        'origin/destination nodes, and county whitespace? Every value on this '
        'tab is a LIVE formula over the detail tab named in the Source tab '
        'column (whole-column INDEX/MATCH, SUMIFS, SUMPRODUCT, COUNTIF); the '
        'profile recalculates with the underlying data. The only typed cells '
        'are the two lookup keys below and the labels.')
    sb.blank()
    sb.headers(['Metric', 'Value', 'Unit', 'Basis', 'Source tab', 'Note'])
    rows = {}

    sb.row([('State (lookup key)', 'label'), (name, 'text'), ('key', 'text'),
            ('(typed)', 'text'), ('— typed, not a value', 'text'),
            ('MATCH target for detail-tab column A (full state name)', 'note')])
    rows['name'] = sb.r
    sb.row([('Abbrev (lookup key)', 'label'), (ab, 'text'), ('key', 'text'),
            ('(typed)', 'text'), ('— typed, not a value', 'text'),
            ('COUNTIF/MATCH target for abbrev columns', 'note')])
    rows['ab'] = sb.r
    K, A = f'$B${rows["name"]}', f'$B${rows["ab"]}'

    def R(tag, label, formula, unit, src, fmt, note=''):
        sb.row([(label, 'label'), (formula, 'fml', fmt), (unit, 'text'),
                ('DERIVED', 'link'), (src, 'link'), (note, 'note')])
        rows[tag] = sb.r

    F = lib.FMT_INT

    # ── Section 1. Beneficiary base ─────────────────────────────────────
    sb.banner('1. Beneficiary base (CMS Medicare Monthly Enrollment)')
    R('tot24', 'Total Medicare beneficiaries, 2024',
      _idx('Enroll_State_2024', 'C', K), 'beneficiaries',
      'Enroll_State_2024', F)
    R('ffs24', 'Original Medicare (FFS) beneficiaries, 2024',
      _idx('Enroll_State_2024', 'D', K), 'beneficiaries',
      'Enroll_State_2024', F, 'The ambulance FFS claim denominator')
    R('ma24', 'MA & other beneficiaries, 2024',
      _idx('Enroll_State_2024', 'E', K), 'beneficiaries',
      'Enroll_State_2024', F)
    R('mash', 'MA & other share, 2024',
      f'=IFERROR(B{rows["ma24"]}/B{rows["tot24"]},"n/a")', '% of total',
      'Enroll_State_2024', lib.FMT_PCT1)
    R('esrd', 'ESRD beneficiaries (aged + disabled incl. ESRD-only), 2024',
      '=IFERROR(INDEX(Enroll_State_2024!H:H,MATCH(' + K +
      ',Enroll_State_2024!A:A,0))+INDEX(Enroll_State_2024!J:J,MATCH(' + K +
      ',Enroll_State_2024!A:A,0)),"n/a")', 'beneficiaries',
      'Enroll_State_2024', F, 'Recurring dialysis-transport population')
    R('tot13', 'Total Medicare beneficiaries, 2013',
      _idx('Enroll_State_2013', 'C', K), 'beneficiaries',
      'Enroll_State_2013', F, 'Comparison base year')
    R('chg', 'Change in total beneficiaries, 2013 → 2024',
      f'=IFERROR(B{rows["tot24"]}/B{rows["tot13"]}-1,"n/a")', '% change',
      'Enroll_State_2013/_2024', lib.FMT_PCT1)
    cagr = lib.cagr_formula(f'B{rows["tot24"]}', f'B{rows["tot13"]}', 11)
    R('cagr', 'CAGR, total beneficiaries, 2013→2024 (11-yr window)',
      '=IFERROR(' + cagr[1:] + ',"n/a")', '%/yr',
      'Enroll_State_2013/_2024', lib.FMT_PCT1,
      'No series break 2013-2024 in this file — trend-eligible')

    # ── Section 2. Medicare ambulance utilization ───────────────────────
    sb.banner('2. Medicare ground ambulance utilization (CMS MUP Geo & Service; '
              'ground base codes A0426/27/28/29/33/34)')
    R('gs24', 'Ground base-code services, 2024',
      _ground('MUP_State_2024', K), 'services', 'MUP_State_2024', F,
      'Sum of six SUMIFS; suppressed state-code rows absent, so a FLOOR')
    R('gs19', 'Ground base-code services, 2019',
      _ground('MUP_State_2019', K), 'services', 'MUP_State_2019', F,
      'Pre-pandemic comparison year (floor)')
    R('gs13', 'Ground base-code services, 2013',
      _ground('MUP_State_2013', K), 'services', 'MUP_State_2013', F,
      'First MUP year (floor)')
    R('gchg', 'Change in ground base services, 2013 → 2024',
      f'=IFERROR(B{rows["gs24"]}/B{rows["gs13"]}-1,"n/a")', '% change',
      'MUP_State_2013/_2024', lib.FMT_PCT1)
    R('per1k', 'Ground base services per 1,000 Original Medicare, 2024',
      f'=IFERROR(B{rows["gs24"]}/B{rows["ffs24"]}*1000,"n/a")',
      'per 1,000 FFS benes', 'MUP_State_2024 + Enroll_State_2024',
      lib.FMT_DEC1, 'Utilization intensity, FFS denominator')
    R('alw', 'Avg Medicare allowed $ per service, A0428 BLS non-emergency, 2024',
      '=IFERROR(SUMPRODUCT((MUP_State_2024!A:A=' + K +
      ')*(MUP_State_2024!C:C="A0428"),MUP_State_2024!G:G,MUP_State_2024!J:J)'
      '/SUMIFS(MUP_State_2024!G:G,MUP_State_2024!A:A,' + K +
      ',MUP_State_2024!C:C,"A0428"),"n/a")', '$ per service',
      'MUP_State_2024', lib.FMT_USD2,
      'Service-weighted across the state\'s A0428 rows')
    R('prv', 'Rendering providers billing A0428, 2024',
      '=SUMIFS(MUP_State_2024!E:E,MUP_State_2024!A:A,' + K +
      ',MUP_State_2024!C:C,"A0428")', 'providers', 'MUP_State_2024', F,
      'Row-sum; a provider on multiple rows counts per row')
    R('ben', 'Beneficiaries with an A0428 service, 2024',
      '=SUMIFS(MUP_State_2024!F:F,MUP_State_2024!A:A,' + K +
      ',MUP_State_2024!C:C,"A0428")', 'beneficiaries', 'MUP_State_2024', F,
      'Row-sum (floor where suppressed)')

    # ── Section 3. Supply ───────────────────────────────────────────────
    sb.banner('3. Supply: enrolled suppliers, EMS workforce, measured FFS market')
    R('pecos', 'PECOS-enrolled ambulance suppliers (PPEF 2026-04)',
      '=COUNTIF(PECOS_Registry!E:E,' + A + ')', 'suppliers',
      'PECOS_Registry', F, 'One registry row per enrolled supplier')
    R('estab', 'EMS establishments (BLS QCEW, NAICS 621910, latest year)',
      _idx('QCEW_EMS_Employment', 'C', K), 'establishments',
      'QCEW_EMS_Employment', F, 'Panel C state rows')
    R('emp', 'EMS employment (QCEW annual average)',
      _idx('QCEW_EMS_Employment', 'D', K), 'jobs',
      'QCEW_EMS_Employment', F)
    R('pay', 'EMS average annual pay (QCEW)',
      _idx('QCEW_EMS_Employment', 'F', K), '$ per year',
      'QCEW_EMS_Employment', lib.FMT_USD)
    R('msprv', 'Measured FFS ambulance providers, latest window (2025)',
      f'=SUMIFS({MSA}!C:C,{MSA}!A:A,' + A +
      f',{MSA}!B:B,"{EMER_NONEMER}")', 'providers', MSA, F,
      'Emergency & Non-Emergency type, Panel B state row')
    R('msusr', 'FFS ambulance users, latest window',
      f'=SUMIFS({MSA}!E:E,{MSA}!A:A,' + A +
      f',{MSA}!B:B,"{EMER_NONEMER}")', 'users', MSA, F)
    R('mspay', 'Total FFS ambulance payment, latest window',
      f'=SUMIFS({MSA}!G:G,{MSA}!A:A,' + A +
      f',{MSA}!B:B,"{EMER_NONEMER}")', '$', MSA, lib.FMT_USD)
    R('ppu', 'Payment per ambulance user, latest window',
      f'=IFERROR(B{rows["mspay"]}/B{rows["msusr"]},"n/a")', '$ per user',
      MSA, lib.FMT_USD2)

    # ── Section 4. Facility O/D nodes ───────────────────────────────────
    sb.banner('4. Facility origin/destination nodes (CMS Care Compare universe)')
    R('hosp', 'Hospitals', _idx('Facility_Universe_State', 'B', A),
      'facilities', 'Facility_Universe_State', F)
    R('er', 'Hospitals with emergency services',
      _idx('Facility_Universe_State', 'C', A), 'facilities',
      'Facility_Universe_State', F)
    R('snf', 'Skilled nursing facilities (SNFs)',
      _idx('Facility_Universe_State', 'D', A), 'facilities',
      'Facility_Universe_State', F)
    R('irf', 'Inpatient rehabilitation facilities (IRFs)',
      _idx('Facility_Universe_State', 'F', A), 'facilities',
      'Facility_Universe_State', F)
    R('ltch', 'Long-term care hospitals (LTCHs)',
      _idx('Facility_Universe_State', 'G', A), 'facilities',
      'Facility_Universe_State', F)
    R('hospice', 'Hospices', _idx('Facility_Universe_State', 'H', A),
      'facilities', 'Facility_Universe_State', F)
    R('hha', 'Home health agencies (HHAs)',
      _idx('Facility_Universe_State', 'I', A), 'facilities',
      'Facility_Universe_State', F)
    R('dial', 'Dialysis facilities', _idx('Facility_Universe_State', 'J', A),
      'facilities', 'Facility_Universe_State', F,
      'Pairs with the ESRD population in Section 1')
    R('beds', 'SNF certified beds', _idx('Facility_Universe_State', 'E', A),
      'beds', 'Facility_Universe_State', F)
    R('bps', 'Beds per SNF',
      f'=IFERROR(B{rows["beds"]}/B{rows["snf"]},"n/a")', 'beds per SNF',
      'Facility_Universe_State', lib.FMT_DEC1)
    R('ersh', 'Emergency-services share of hospitals',
      f'=IFERROR(B{rows["er"]}/B{rows["hosp"]},"n/a")', '% of hospitals',
      'Facility_Universe_State', lib.FMT_PCT1)

    # ── Section 5. Whitespace ───────────────────────────────────────────
    sb.banner('5. County whitespace (CMS Market Saturation, latest window)')
    R('cty', 'Counties measured (Emergency & Non-Emergency type)',
      '=COUNTIFS(MS_County_2025!C:C,' + A +
      f',MS_County_2025!A:A,"{EMER_NONEMER}")', 'counties',
      'MS_County_2025', F)
    R('lt3', 'Counties with <3 measured FFS ambulance providers',
      f'=SUMPRODUCT(({MSA}!A:A=' + A + f')*ISNUMBER({MSA}!B:B),{MSA}!C:C)'
      f'+SUMPRODUCT(({MSA}!A:A=' + A + f')*ISNUMBER({MSA}!B:B),{MSA}!D:D)',
      'counties', MSA,
      F, 'Panel C bands (suppressed/0 + 1-2); ISNUMBER(col B) isolates '
         'Panel C rows, whose col B is a numeric county count, from Panel B '
         'rows, whose col B is a text service type')
    R('lt3sh', 'Share of counties with <3 measured providers',
      f'=IFERROR(B{rows["lt3"]}/B{rows["cty"]},"n/a")', '% of counties',
      MSA + ' + MS_County_2025', lib.FMT_PCT1,
      'Suppressed county = <11 users, grouped with zero: thin-supply floor')

    sb.blank()
    sb.note('Basis: every value row is DERIVED — a live formula over the detail '
            'tab in column E; no number is retyped on this tab. "n/a" means the '
            'detail tab has no row for this jurisdiction (IFERROR-wrapped '
            'INDEX/MATCH), not zero. CMS small-cell suppression makes MUP and '
            'Market Saturation counts FLOORS. MUP state rows are state x HCPCS '
            '(x place of service): provider/beneficiary row-sums can double-'
            'count, and the A0428 allowed $ is service-weighted across rows. '
            'Citations, vintages and locators for every input live on the '
            'detail tabs and the Source_Register.')

    lib.add_chart(
        ws, 'H6', f'{ab} facility O/D nodes (live formulas)',
        f"SP_{ab}!$A${rows['hosp']}:$A${rows['dial']}",
        [('facilities', f"SP_{ab}!$B${rows['hosp']}:$B${rows['dial']}")],
        kind='bar', width=15, height=9)
    return rows


def build(wb, ctx):
    lib = ctx['lib']
    facts, sources, excluded = [], [], []

    sources.append({
        'key': 'sp_inputs',
        'publisher': 'CMS / BLS (via existing workbook detail tabs — no new pull)',
        'document': 'State-profile inputs: Enroll_State_2013/_2024, '
                    'MUP_State_2013/_2019/_2024, PECOS_Registry, '
                    'QCEW_EMS_Employment, Facility_Universe_State, '
                    'Market_Saturation_Ambulance, MS_County_2025',
        'vintage': 'As registered for each underlying detail tab',
        'locator': 'Whole-column INDEX/MATCH, SUMIFS, SUMPRODUCT and '
                   'COUNTIF(S) references; the Source tab column on every '
                   'profile row names the input tab',
        'supplies': 'Cross-reference stub only — the SP family introduces no '
                    'new external source; integrator should resolve these '
                    'facts to the S-IDs already registered for the named '
                    'detail tabs',
        'url': '(workbook-internal cross-reference)',
        'tier': 'A', 'accessed': ctx['accessed'],
        'powers': ['SP_Index'] + [f'SP_{ab}' for _, ab in STATES]})

    # ══ SP_Index ═══════════════════════════════════════════════════════
    ws = wb.create_sheet('SP_Index')
    sb = lib.SheetBuilder(
        ws, 13,
        col_widths=[22, 8, 13, 13, 11, 13, 12, 11, 12, 10, 10, 9, 10],
        tab_color=PURPLE)
    sb.title('State profile index — 51 jurisdictions on one live screen')
    sb.subtitle(
        'The question: how do the 51 state/DC profiles compare — beneficiary '
        'base, MA erosion, ground ambulance utilization intensity, enrolled '
        'suppliers, EMS workforce and facility nodes? Every value cell is a '
        'live formula over the same detail tabs the SP_ profile tabs use '
        '(Enroll_State_2024, MUP_State_2024, PECOS_Registry, '
        'QCEW_EMS_Employment, Facility_Universe_State); only the state name '
        'and abbrev are typed. Click the Profile column to jump to a state.')
    sb.blank()
    sb.headers(['State', 'Abbr', 'Total benes 2024', 'Original Medicare 2024',
                'MA & other share', 'Ground base svcs 2024',
                'Svcs per 1,000 FFS', 'PECOS suppliers', 'EMS employment',
                'Hospitals', 'Dialysis', 'Profile', 'Basis'])
    i0 = sb.r + 1
    for name, ab in STATES:
        r = sb.r + 1
        sb.row([
            (name, 'text'), (ab, 'text'),
            (_idx('Enroll_State_2024', 'C', f'$A{r}'), 'fml', lib.FMT_INT),
            (_idx('Enroll_State_2024', 'D', f'$A{r}'), 'fml', lib.FMT_INT),
            (f'=IFERROR(INDEX(Enroll_State_2024!E:E,MATCH($A{r},'
             f'Enroll_State_2024!A:A,0))/C{r},"n/a")', 'fml', lib.FMT_PCT1),
            (_ground('MUP_State_2024', f'$A{r}'), 'fml', lib.FMT_INT),
            (f'=IFERROR(F{r}/D{r}*1000,"n/a")', 'fml', lib.FMT_DEC1),
            (f'=COUNTIF(PECOS_Registry!E:E,$B{r})', 'fml', lib.FMT_INT),
            (_idx('QCEW_EMS_Employment', 'D', f'$A{r}'), 'fml', lib.FMT_INT),
            (_idx('Facility_Universe_State', 'B', f'$B{r}'), 'fml', lib.FMT_INT),
            (_idx('Facility_Universe_State', 'J', f'$B{r}'), 'fml', lib.FMT_INT),
            (f'=HYPERLINK("#SP_{ab}!A1","SP_{ab}")', 'link'),
            ('DERIVED', 'link')])
    i1 = sb.r
    tr = sb.r + 1
    sb.row([('US total (51 jurisdictions)', 'label'), ('', 'text'),
            (f'=SUM(C{i0}:C{i1})', 'fml', lib.FMT_INT),
            (f'=SUM(D{i0}:D{i1})', 'fml', lib.FMT_INT),
            (f'=IFERROR(1-D{tr}/C{tr},"n/a")', 'fml', lib.FMT_PCT1),
            (f'=SUM(F{i0}:F{i1})', 'fml', lib.FMT_INT),
            (f'=IFERROR(F{tr}/D{tr}*1000,"n/a")', 'fml', lib.FMT_DEC1),
            (f'=SUM(H{i0}:H{i1})', 'fml', lib.FMT_INT),
            (f'=SUM(I{i0}:I{i1})', 'fml', lib.FMT_INT),
            (f'=SUM(J{i0}:J{i1})', 'fml', lib.FMT_INT),
            (f'=SUM(K{i0}:K{i1})', 'fml', lib.FMT_INT),
            ('', 'text'), ('DERIVED', 'link')])
    sb.blank()
    sb.note('All value columns are DERIVED live formulas over detail tabs '
            '(sources, vintages and locators on those tabs and the '
            'Source_Register); "n/a" = no detail-tab row, not zero. Ground '
            'services are FLOORS (CMS suppression). The US total row sums the '
            '51 formulas — cross-check it against the national rows on '
            'Enrollment_ESRD_State, MUP_Ambulance_National and PECOS_Registry '
            '(PECOS national includes territories/other jurisdictions, so the '
            'COUNTIF sum here may sit slightly below it). Puerto Rico and '
            'territories excluded: detail-tab coverage is not consistent '
            'across all seven inputs (see Excluded_Not_Sourced).')

    lib.add_chart(
        ws, 'O4',
        'Ground base ambulance services per 1,000 Original Medicare '
        'beneficiaries, 2024 (live formula column G)',
        f'SP_Index!$B${i0}:$B${i1}',
        [('per 1,000 FFS', f'SP_Index!$G${i0}:$G${i1}')],
        kind='bar', width=30, height=14)

    # ══ 51 profile tabs ════════════════════════════════════════════════
    for name, ab in STATES:
        _profile(wb, lib, name, ab)

    facts += [
        {'metric': 'Medicare beneficiaries 2024, sum of the 51 SP_Index '
                   'state formulas', 'year': 2024,
         'value_ref': f'SP_Index!C{tr}', 'unit': 'beneficiaries',
         'basis': 'DERIVED', 'tier': 'A', 'source_keys': ['sp_inputs'],
         'locator': 'SP_Index US-total row: SUM of 51 INDEX/MATCH pulls from '
                    'Enroll_State_2024 col C',
         'lives_on': 'SP_Index',
         'cross_check': 'Must reconcile to the 2024 national row on '
                        'Enrollment_ESRD_State (same CMS Monthly Enrollment '
                        'file, national grain)'},
        {'metric': 'Ground base-code ambulance services 2024, 51-state '
                   'formula sum (floor)', 'year': 2024,
         'value_ref': f'SP_Index!F{tr}', 'unit': 'services',
         'basis': 'DERIVED', 'tier': 'A', 'source_keys': ['sp_inputs'],
         'locator': 'SP_Index US-total row: SUM of 51 six-code SUMIFS over '
                    'MUP_State_2024 (A0426/27/28/29/33/34)',
         'lives_on': 'SP_Index',
         'cross_check': 'Sits at or below the 2024 ground-base total on '
                        'MUP_Ambulance_National (state-grain suppression '
                        'makes the state sum a floor)'},
        {'metric': 'PECOS-enrolled ambulance suppliers, 51-state COUNTIF sum',
         'year': 2026, 'value_ref': f'SP_Index!H{tr}', 'unit': 'suppliers',
         'basis': 'DERIVED', 'tier': 'A', 'source_keys': ['sp_inputs'],
         'locator': 'SP_Index US-total row: SUM of 51 COUNTIFs over '
                    'PECOS_Registry col E (PPEF 2026-04-01)',
         'lives_on': 'SP_Index',
         'cross_check': 'PECOS_Registry national count (10,465) minus '
                        'territory/other-jurisdiction rows'},
    ]

    excluded.append({
        'figure': 'SP_PR profile tab (Puerto Rico) and territory profiles',
        'value': '(no value carried)',
        'source_label': 'Same seven detail tabs',
        'why_excluded': 'Detail-tab coverage for PR/territories is not '
                        'consistent across all seven inputs (QCEW state '
                        'panel, Care Compare universe, Market Saturation '
                        'county bands), so a profile would be mostly "n/a" '
                        'and break the family\'s one-layout comparability '
                        'rule',
        'what_would_make_citable': 'Confirm at assembly that PR rows exist '
                                   'on all seven detail tabs; then add SP_PR '
                                   'with the identical layout'})

    return {
        'facts': facts, 'sources': sources, 'excluded': excluded,
        'meta': {
            'notes': 'SP family introduces NO new external source: all 52 '
                     'tabs are live formulas over existing detail tabs '
                     '(Enroll_State_2013/_2024, MUP_State_2013/_2019/_2024, '
                     'PECOS_Registry, QCEW_EMS_Employment, '
                     'Facility_Universe_State, Market_Saturation_Ambulance, '
                     'MS_County_2025). The single declared source key '
                     "'sp_inputs' is a cross-reference stub the integrator "
                     'should resolve to the existing S-IDs of those tabs. '
                     'Detail tabs are absent in the harness test build by '
                     'design — formulas are saved unevaluated and resolve at '
                     'assembly. Counties-with-<3-providers uses '
                     'SUMPRODUCT((A=abbrev)*ISNUMBER(col B)) to isolate '
                     'Market_Saturation_Ambulance Panel C (numeric county '
                     'count in col B) from Panel B (text service type in '
                     'col B), because abbrevs repeat across panels. PR and '
                     'territories excluded (see excluded). All 51 profiles '
                     'share one deterministic row map; lookup keys at B5 '
                     '(name) / B6 (abbrev) make each tab re-pointable and '
                     'auditable.',
            'row_counts': {s['name']: wb[s['name']].max_row for s in SHEETS}}}
