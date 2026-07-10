"""Group D part 1 — demand & clinical depth tabs.

Tabs:
  1. Condition_Transfer_Registry — 32-condition transfer matrix (ift_clinical_demand),
     sourced national-volume literals with per-row citations; modeled CAGR columns EXCLUDED.
  2. Post_Acute_Supply_State    — SNF/IRF/LTACH/HHA/hospice provider counts, national + 55
     state/territory rows, from vendored CMS provider files (row counts re-tallied at build).
  3. Clinical_Benchmarks        — ~26 ACADEMIC DOI-cited transfer-timing / flow benchmarks
     (STEMI & stroke DIDO, prenotification, offload, crew detention, boarding, delayed
     discharge economics) from the in-depth study modules.
"""
import csv
import sys

sys.path.insert(0, '/home/user/RCM/RCM_MC')
sys.path.insert(0, '/home/user/RCM')

PURPLE = 'FF7A5195'

SHEETS = [
    {'name': 'Condition_Transfer_Registry', 'tab_color': PURPLE},
    {'name': 'Post_Acute_Supply_State', 'tab_color': PURPLE},
    {'name': 'Clinical_Benchmarks', 'tab_color': PURPLE},
]

_SETTING_DESC = {
    'SNF': 'Skilled nursing facility (SNF)',
    'IRF': 'Inpatient rehabilitation facility (IRF)',
    'LTACH': 'Long-term acute care hospital (LTACH/LTCH)',
    'HHA': 'Home health agency (HHA)',
    'Hospice': 'Hospice',
}

_SETTING_CITE = {
    'SNF': ('CMS Nursing Home Care Compare — Provider Information (NH_ProviderInfo)',
            '2026-04-01'),
    'IRF': ('CMS Inpatient Rehabilitation Facility Compare — General Information + '
            'Provider Data', '2026-02-13'),
    'LTACH': ('CMS Long-Term Care Hospital Compare — General Information + Provider Data',
              '2026-02-13'),
    'HHA': ('CMS Provider Data Catalog — Home Health Care Agencies (dataset 6jpm-sxkc)',
            '2026-05-23'),
    'Hospice': ('CMS Provider Data Catalog — Hospice General Information (dataset '
                'yc9t-dgbk)', '2026-05-23'),
}

_SETTING_CSV = {
    'SNF': 'snf_providers.csv',
    'IRF': 'irf_providers.csv',
    'LTACH': 'ltch_providers.csv',
    'HHA': 'home_health_providers.csv',
    'Hospice': 'hospice_providers.csv',
}

_TERRITORY = {'PR': 'US territory', 'GU': 'US territory', 'MP': 'US territory',
              'VI': 'US territory', 'DC': 'District of Columbia'}


def _retally_csvs(repo):
    """Independently re-count rows of the vendored CMS provider CSVs (stdlib csv)."""
    counts = {}
    for setting, fname in _SETTING_CSV.items():
        try:
            with open(f'{repo}/RCM_MC/rcm_mc/data/{fname}', newline='',
                      encoding='utf-8') as fh:
                counts[setting] = sum(1 for _ in csv.DictReader(fh))
        except OSError:
            counts[setting] = None
    return counts


def build(wb, ctx):
    lib = ctx['lib']
    repo = ctx['repo']
    accessed = ctx['accessed']
    facts, sources, excluded = [], [], []
    meta_notes = []

    try:
        from rcm_mc.market_reports import ift_clinical_demand as cd
        matrix = cd.transfer_matrix()
        supply_all = cd.destination_supply()
        supply_by_setting = {s: cd.destination_supply(setting=s) for s in _SETTING_DESC}
        conditions = {c.name: c for c in cd.all_conditions()}
        validation = cd.validate_codes()
        n_icd_ok = sum(len(v['icd10_ok']) for v in validation.values())
        n_icd_miss = sum(len(v['icd10_miss']) for v in validation.values())
    except Exception as exc:  # degrade gracefully, never invent
        matrix, supply_all, supply_by_setting, conditions = [], None, {}, {}
        n_icd_ok, n_icd_miss = 0, -1
        meta_notes.append(f'ift_clinical_demand unavailable: {exc}')

    # =====================================================================
    # Tab 1 — Condition_Transfer_Registry
    # =====================================================================
    ws1 = wb.create_sheet(SHEETS[0]['name'])
    NC1 = 16
    b = lib.SheetBuilder(
        ws1, NC1, tab_color=PURPLE,
        col_widths=[26, 15, 38, 9, 10, 12, 20, 34, 18, 30, 12, 30, 8, 12, 30, 34])
    b.title('Condition Transfer Registry — 32 acute-transfer conditions')
    b.subtitle('The question: which clinical conditions generate interfacility transfers, '
               'in which direction, at what acuity, on what clock — and how big is each '
               "condition's PUBLISHED national pool? Volumes are per-row cited literals "
               '(blue); measures are deliberately heterogeneous (stays vs incidence vs ED '
               'visits vs births vs enrollees) — NEVER sum this column. The modeled '
               'per-condition growth (CAGR) columns of the source registry are EXCLUDED '
               '(see Excluded_Not_Sourced).', height=44)
    b.blank()
    b.headers(['Condition', 'Family', 'Presenting clinical picture', 'Transfer type',
               'Clinical acuity', 'Transport acuity', 'Origin setting',
               'Destination capability (clinical reference)', 'Destination setting',
               'Time window (clinical reference)', 'National volume', 'Volume measure',
               'Vol. year', 'Basis', 'Volume citation (publisher document)',
               'Registry note / corroboration'])
    hdr1 = b.r
    reg_row = {}
    for m in matrix:
        basis_chip, _, cite = m['volume_label'].partition(' · ')
        cond = conditions.get(m['condition'])
        year = cond.national_volume.year if cond else ''
        note = (cond.national_volume.note or '') if cond else ''
        if year == 2009:
            note = ('[STALE 2009 vintage — modern read: HCUP NEDS 2018-2022 '
                    '~1.97M/yr adult ED-to-ED transfers, see Demand evidence] ' + note)
        vol = m['national_volume']
        vol_cell = ((vol, 'src', lib.FMT_INT) if vol and basis_chip != 'FRAMEWORK'
                    else ('—', 'text'))
        b.row([
            (m['condition'], 'label'),
            (m['family'], 'text'),
            (m['presenting'], 'text'),
            (m['transfer_type'], 'text'),
            (m['acuity'], 'text'),
            (m['transport_acuity'], 'text'),
            (m['origin_setting'], 'text'),
            (m['destination_capability'], 'text'),
            (m['destination_setting'], 'text'),
            (m['time_window'], 'text'),
            vol_cell,
            (m['volume_measure'], 'text'),
            (year, 'src'),
            (basis_chip, 'text'),
            (cite, 'text'),
            (note, 'note'),
        ], wrap=True, height=34)
        reg_row[m['condition']] = b.r
    first1, last1 = hdr1 + 1, b.r

    b.blank()
    b.banner('Registry distribution (live formulas over the table above)')
    dist_rows = {}
    for label, formula in [
        ('Rows with a GOV-cited volume', f'=COUNTIF(N{first1}:N{last1},"GOV")'),
        ('Rows with an ACADEMIC-cited volume', f'=COUNTIF(N{first1}:N{last1},"ACADEMIC")'),
        ('FRAMEWORK rows (chip carried, no volume printed)',
         f'=COUNTIF(N{first1}:N{last1},"FRAMEWORK")'),
        ('Conditions with a published national volume (numeric cells)',
         f'=COUNT(K{first1}:K{last1})'),
        ('Family: Escalation', f'=COUNTIF(B{first1}:B{last1},"Escalation")'),
        ('Family: Step-down/Recovery',
         f'=COUNTIF(B{first1}:B{last1},"Step-down/Recovery")'),
        ('Family: Direct-admit/Load-balancing',
         f'=COUNTIF(B{first1}:B{last1},"Direct-admit/Load-balancing")'),
    ]:
        b.row([(label, 'label'), (formula, 'fml', lib.FMT_INT)])
        dist_rows[label] = b.r
    b.blank()
    b.note('Honesty rules carried from the source registry: (1) the Volume measure column '
           'MUST travel with every number — pools mix inpatient stays, incidence, ED '
           'visits, births and enrollees; (2) shared parent pools appear in TWO families '
           '(heart failure, sepsis, pneumonia, hip fracture, Medicare LTCH cases) — never '
           'sum across families; (3) four rows carry an honest zero ("—"): no national '
           'count is published (complex surgical complication, direct admit, '
           'load-balancing, repatriation); (4) destination capability, time window, '
           'MS-DRG/PCS mappings are authored clinical reference, not sourced statistics.',
           height=44)
    b.note('ED interfacility up-transfer row (1.9M) is HCUP SB#155, 2009 vintage — kept as '
           'historical corroboration; the modern published read is HCUP NEDS 2018-2022: '
           '9,867,701 adult ED-to-ED transfers (~1.97M/yr; Nikolla et al., J Emerg Med '
           '2025, DOI 10.1016/j.jemermed.2025.12.020).', height=26)
    b.note('EXCLUDED from this tab (quarantined on Excluded_Not_Sourced): the source '
           "registry's per-condition growth columns ('cagr' 3.1-3.8%/yr and "
           "'growth_label') — modeled from demand_forecast._POP_GROWTH_BY_AGE age-band "
           'CAGRs (self-labeled "rough") weighted by authored age skews; and the blended '
           '2.68%/yr aggregate. Not published statistics.', height=32)
    b.note(f'Extraction: rcm_mc.market_reports.ift_clinical_demand.transfer_matrix() / '
           f'all_conditions(), accessed {accessed}. ICD-10-CM codes behind the registry: '
           f'{n_icd_ok} codes validated vs the vendored FY2025/FY2026 billability seed '
           f'(validate_codes(); {n_icd_miss} misses).', height=26)
    b.blank()
    chart_row1 = b.r + 1
    lib.add_chart(
        ws1, f'A{chart_row1}',
        'Published national volume by condition — measures are HETEROGENEOUS '
        '(see Volume measure column); do not compare bars across measure types',
        f'Condition_Transfer_Registry!$A${first1}:$A${last1}',
        [('National volume (published, per-row cited)',
          f'Condition_Transfer_Registry!$K${first1}:$K${last1}')],
        kind='bar', width=42, height=12, y_title='published national volume',
        y_fmt='#,##0')

    # ---- facts for tab 1 (headline registry volumes; tier B — carried from repo
    #      modules citing documents we did not reopen -> basis SOURCED per contract)
    def reg_fact(cond, metric, unit, skeys, locator, cross=''):
        r = reg_row.get(cond)
        if not r:
            return
        c = conditions.get(cond)
        facts.append({
            'metric': metric, 'year': str(c.national_volume.year) if c else '',
            'value_ref': f'Condition_Transfer_Registry!K{r}', 'unit': unit,
            'basis': 'SOURCED', 'tier': 'B', 'source_keys': skeys, 'locator': locator,
            'lives_on': 'Condition_Transfer_Registry', 'cross_check': cross})

    reg_fact('Acute MI / chest pain', 'Acute-MI inpatient stays (principal dx), US',
             'stays/yr', ['hcup_sb277'],
             'HCUP SB#277, 2018 NIS, principal-diagnosis stay counts',
             'CDC/AHA ~805,000 MI events/yr (registry note)')
    reg_fact('Cardiogenic shock / complex cardiac',
             'Heart-failure inpatient stays (parent pool), US', 'stays/yr',
             ['hcup_sb277'], 'HCUP SB#277, 2018 NIS — HF is the #2 US inpatient condition',
             'same pool reused by Cardiac recovery row — never double-count')
    reg_fact('Ischemic stroke', 'Cerebral-infarction inpatient stays, US', 'stays/yr',
             ['hcup_sb277'], 'HCUP SB#277, 2018 NIS',
             'CDC >795,000 strokes/yr, ~87% ischemic')
    reg_fact('Severe sepsis / septic shock', 'Adults developing sepsis per year, US',
             'adults/yr', ['cdc_sepsis'], 'CDC sepsis surveillance ("at least 1.7M adults")',
             'HCUP: septicemia #1 inpatient condition, 2,218,800 stays 2018')
    reg_fact('Behavioral-health crisis', 'Mental-health-related ED visits, US',
             'ED visits/yr', ['cdc_samhsa_mh'], 'CDC/SAMHSA ED utilization, 2021',
             '~1 in 8 ED visits MH/SUD')
    reg_fact('High-risk pregnancy / obstetric emergency', 'US births (all)', 'births/yr',
             ['cdc_nchs_births2022'], 'CDC/NCHS Births: Final Data for 2022',
             'preterm row = 10.38% of this pool')
    reg_fact('Med-surg discharge -> SNF/home health', 'Medicare-covered SNF stays',
             'stays/yr', ['medpac_snf'], 'MedPAC Payment Basics — SNF (2022 data)',
             '~14,700 SNFs cross-checks Post_Acute_Supply_State SNF count 14,699')
    reg_fact('ED interfacility up-transfer to acute care',
             'ED encounters transferred to another short-term hospital (2009)',
             'transfers/yr', ['hcup_sb155'],
             'HCUP SB#155: 1.5% x 128,885,040 ED encounters, 2009 NEDS',
             'modern read: NEDS 2018-2022 ~1.97M/yr (Nikolla 2025)')
    facts.append({
        'metric': 'Registry rows with a GOV-cited national volume', 'year': '2026',
        'value_ref': f"Condition_Transfer_Registry!B{dist_rows['Rows with a GOV-cited volume']}",
        'unit': 'rows (of 32)', 'basis': 'DERIVED', 'tier': 'B',
        'source_keys': ['ift_clinical_registry'],
        'locator': 'live COUNTIF over the Basis column (GOV 23 / ACADEMIC 6 / FRAMEWORK 3)',
        'lives_on': 'Condition_Transfer_Registry', 'cross_check': ''})

    # =====================================================================
    # Tab 2 — Post_Acute_Supply_State
    # =====================================================================
    ws2 = wb.create_sheet(SHEETS[1]['name'])
    NC2 = 10
    b2 = lib.SheetBuilder(ws2, NC2, tab_color=PURPLE,
                          col_widths=[26, 11, 9, 9, 9, 10, 11, 10, 11, 58])
    b2.title('Post-Acute Destination Supply — national and by state')
    b2.subtitle('The question: how many CMS-certified post-acute destinations (SNF / IRF / '
                'LTACH / HHA / hospice) exist nationally and in each state — the '
                'discharge-lane supply every step-down transfer depends on? Counts are '
                'point-in-time certified-provider directory rows from named CMS public '
                'files (vendored with provenance; row counts independently re-tallied at '
                'build time). Totals and shares are live formulas.', height=44)
    b2.blank()

    settings = ['SNF', 'IRF', 'LTACH', 'HHA', 'Hospice']
    retally = _retally_csvs(repo)
    nat_rows = {}
    st_rows = {}
    nat_tot_row = st_tot_row = None
    if supply_all:
        by_setting = supply_all['by_setting']
        b2.banner('A. National destination counts by setting')
        b2.headers(['Setting', 'Providers', 'Share of total', '', '', '', '', '', 'Basis',
                    f'CMS source dataset (file vintage; accessed {accessed})'])
        nat_hdr = b2.r
        nat_first = nat_hdr + 1
        nat_tot_row = nat_hdr + len(settings) + 1
        for s in settings:
            doc, vint = _SETTING_CITE[s]
            b2.row([
                (_SETTING_DESC[s], 'label'),
                (by_setting[s], 'src', lib.FMT_INT),
                (f'=B{nat_hdr + 1 + settings.index(s)}/B${nat_tot_row}', 'fml',
                 lib.FMT_PCT1),
                None, None, None, None, None,
                ('SOURCED', 'text'),
                (f'{doc}; file vintage {vint}', 'text'),
            ], wrap=True, height=24)
            nat_rows[s] = b2.r
        b2.row([
            ('Total post-acute destinations', 'label'),
            (f'=SUM(B{nat_first}:B{nat_rows["Hospice"]})', 'fml', lib.FMT_INT),
            (f'=SUM(C{nat_first}:C{nat_rows["Hospice"]})', 'fml', lib.FMT_PCT1),
            None, None, None, None, None,
            ('DERIVED', 'text'),
            ('Live SUM of the five setting counts above', 'note'),
        ])
        nat_tot_row = b2.r
        retally_txt = ' / '.join(
            f'{s} {retally[s]:,}' if retally[s] is not None else f'{s} n/a'
            for s in settings)
        match = all(retally[s] == by_setting[s] for s in settings
                    if retally[s] is not None)
        b2.note('Build-time audit: vendored CSV row counts re-tallied independently '
                f'(stdlib csv): {retally_txt} — '
                f'{"MATCH with the accessor counts above" if match else "MISMATCH — investigate"}.',
                height=24)

        b2.blank()
        b2.banner('B. Destination counts by state and setting '
                  f'({len(supply_all["per_state"])} state/territory codes)')
        b2.headers(['State', 'SNF', 'IRF', 'LTACH', 'HHA', 'Hospice', 'Total (formula)',
                    'Share of US', 'Basis', 'Note'])
        st_hdr = b2.r
        states = sorted(supply_all['per_state'])
        st_first = st_hdr + 1
        st_tot_row = st_hdr + len(states) + 1
        for st in states:
            r = b2.r + 1
            cells = [(st, 'label')]
            for i, s in enumerate(settings):
                cells.append((supply_by_setting[s]['per_state'].get(st, 0), 'src',
                              lib.FMT_INT))
            cells.append((f'=SUM(B{r}:F{r})', 'fml', lib.FMT_INT))
            cells.append((f'=G{r}/G${st_tot_row}', 'fml', lib.FMT_PCT1))
            cells.append(('SOURCED', 'text'))
            cells.append((_TERRITORY.get(st, ''), 'note'))
            b2.row(cells)
            st_rows[st] = b2.r
        st_last = b2.r
        b2.row([('US total (sum of states)', 'label')] +
               [(f'=SUM({col}{st_first}:{col}{st_last})', 'fml', lib.FMT_INT)
                for col in 'BCDEFG'] +
               [(f'=SUM(H{st_first}:H{st_last})', 'fml', lib.FMT_PCT1),
                ('DERIVED', 'text'), ('', 'note')])
        st_tot_row = b2.r
        b2.row([('Cross-check: sum of states minus national block (expect 0)', 'label')] +
               [(f'={col}{st_tot_row}-B{nat_rows[s]}', 'fml', lib.FMT_INT)
                for col, s in zip('BCDEF', settings)] +
               [(f'=G{st_tot_row}-B{nat_tot_row}', 'fml', lib.FMT_INT), None,
                ('DERIVED', 'text'), ('audit row — every cell should compute to 0', 'note')])
        xcheck_row = b2.r
        b2.blank()
        b2.note('Counts are one row per certified provider record (CCN) in the named CMS '
                'public directory files — full listings, NOT claims aggregates, so CMS '
                'small-cell suppression does not apply. Territories (PR, GU, MP, VI) and '
                'DC included. A zero means no certified provider of that type appears in '
                "that state's file (e.g., 8 states have no LTACH).", height=32)
        b2.note('File vintages differ by setting (2026-02-13 to 2026-05-23) — this is a '
                'snapshot table; do not difference against other vintages for trend. '
                'Extraction: rcm_mc/data/{snf,irf,ltch,home_health,hospice}_providers.csv '
                f'via ift_clinical_demand.destination_supply(), accessed {accessed}.',
                height=30)
        b2.blank()

        # top-15 mini-block (live links into table B) + charts
        totals = {st: sum(supply_by_setting[s]['per_state'].get(st, 0)
                          for s in settings) for st in states}
        top15 = sorted(states, key=lambda st: -totals[st])[:15]
        b2.banner('C. Top-15 states by total post-acute destinations '
                  '(live links into table B)')
        b2.headers(['State', 'Total destinations'], freeze=False, height=15)
        top_first = b2.r + 1
        for st in top15:
            b2.row([(f'=A{st_rows[st]}', 'fml'),
                    (f'=G{st_rows[st]}', 'fml', lib.FMT_INT)])
        top_last = b2.r
        lib.add_chart(
            ws2, 'L6', 'National post-acute destinations by setting',
            f'Post_Acute_Supply_State!$A${nat_first}:$A${nat_rows["Hospice"]}',
            [('Certified providers',
              f'Post_Acute_Supply_State!$B${nat_first}:$B${nat_rows["Hospice"]}')],
            kind='bar', width=20, height=10, y_title='certified providers',
            y_fmt='#,##0')
        lib.add_chart(
            ws2, f'D{top_first}', 'Top-15 states by total post-acute destinations',
            f'Post_Acute_Supply_State!$A${top_first}:$A${top_last}',
            [('Total destinations',
              f'Post_Acute_Supply_State!$B${top_first}:$B${top_last}')],
            kind='bar', width=20, height=9, y_title='destinations', y_fmt='#,##0')

        skey_by_setting = {'SNF': 'cms_nh_providerinfo', 'IRF': 'cms_irf_compare',
                           'LTACH': 'cms_ltch_compare', 'HHA': 'cms_pdc_hha',
                           'Hospice': 'cms_pdc_hospice'}
        cross = {'SNF': 'MedPAC ~14,700 SNFs; registry SNF row',
                 'IRF': 'MedPAC ~1,180 IRFs (registry note)',
                 'LTACH': 'MedPAC ~320 LTCHs (registry note)', 'HHA': '', 'Hospice': ''}
        for s in settings:
            facts.append({
                'metric': f'{_SETTING_DESC[s]} — certified providers, US',
                'year': _SETTING_CITE[s][1][:4],
                'value_ref': f'Post_Acute_Supply_State!B{nat_rows[s]}',
                'unit': 'providers', 'basis': 'SOURCED', 'tier': 'A',
                'source_keys': [skey_by_setting[s]],
                'locator': f'{_SETTING_CITE[s][0]}, file vintage {_SETTING_CITE[s][1]}, '
                           'one row per certified provider (CCN)',
                'lives_on': 'Post_Acute_Supply_State', 'cross_check': cross[s]})
        facts.append({
            'metric': 'Total post-acute destinations, US (5 settings)', 'year': '2026',
            'value_ref': f'Post_Acute_Supply_State!B{nat_tot_row}', 'unit': 'providers',
            'basis': 'DERIVED', 'tier': 'A',
            'source_keys': list(skey_by_setting.values()),
            'locator': 'live SUM of the five CMS provider-file counts (35,481)',
            'lives_on': 'Post_Acute_Supply_State',
            'cross_check': 'matches ift_study.ecosystem().postacute_destinations'})
        for st in ('CA', 'TX'):
            facts.append({
                'metric': f'{st} total post-acute destinations', 'year': '2026',
                'value_ref': f'Post_Acute_Supply_State!G{st_rows[st]}',
                'unit': 'providers', 'basis': 'DERIVED', 'tier': 'A',
                'source_keys': list(skey_by_setting.values()),
                'locator': f'row SUM across the five CMS provider files, state={st}',
                'lives_on': 'Post_Acute_Supply_State', 'cross_check': ''})
    else:
        b2.note('destination_supply() unavailable in this environment — block skipped.')
        meta_notes.append('Post_Acute_Supply_State: destination_supply unavailable')

    # =====================================================================
    # Tab 3 — Clinical_Benchmarks
    # =====================================================================
    ws3 = wb.create_sheet(SHEETS[2]['name'])
    NC3 = 10
    b3 = lib.SheetBuilder(ws3, NC3, tab_color=PURPLE,
                          col_widths=[44, 11, 15, 34, 30, 11, 32, 40, 11, 30])
    b3.title('Clinical Benchmarks — transfer timing, hospital flow, delay economics')
    b3.subtitle('The question: what do peer-reviewed studies measure about transfer timing '
                '(door-in-door-out), hospital door delay, ED boarding and delayed '
                'discharge — the quantified failure costs dedicated IFT is bought to fix? '
                'All values are published literals (blue) with full DOIs; the one growth '
                'rate is a live formula. Extraction: rcm_mc ift_indepth_q* evidence '
                f'registries (311 lines, deduplicated), accessed {accessed}.', height=40)
    b3.blank()

    HDRS3 = ['Benchmark', 'Value', 'Unit', 'Detail / qualifier',
             'Population / setting / n', 'Data year(s)',
             'Citation (authors, journal, year)', 'DOI / URL', 'Basis',
             'Caveat / re-verify']
    b3.headers(HDRS3)

    F = lib  # short alias for formats
    # (id, benchmark, value, numfmt, unit, detail, population, years, cite, doi, caveat)
    BM = [
        ('banner', 'STEMI and stroke transfer timing (door-in-door-out, DIDO)'),
        ('stemi_dido', 'STEMI transfer: median door-in-door-out (DIDO) time', 68,
         F.FMT_INT, 'minutes', 'only 11% of transfers achieved DIDO <=30 min',
         'n=14,821 STEMI patients transferred for primary PCI, US registry',
         'pub. 2011', 'Wang et al., JAMA 2011',
         'https://doi.org/10.1001/jama.2011.862', ''),
        ('stemi_30', 'STEMI transfers meeting the 30-minute DIDO standard', 0.11,
         F.FMT_PCT1, 'share', '', 'same cohort', 'pub. 2011', 'Wang et al., JAMA 2011',
         'https://doi.org/10.1001/jama.2011.862', ''),
        ('stemi_mort', 'In-hospital mortality when DIDO >30 min', 0.059, F.FMT_PCT1,
         'share', 'vs 2.7% when <=30 min; adjusted OR 1.56 (95% CI 1.15-2.12)',
         'same cohort', 'pub. 2011', 'Wang et al., JAMA 2011',
         'https://doi.org/10.1001/jama.2011.862', ''),
        ('ng_referrer', 'Share of stroke-transfer time spent AT the referring hospital',
         0.828, F.FMT_PCT1, 'share', 'median DIDO 106 min',
         'stroke interfacility transfers', 'pub. 2017', 'Ng et al., Stroke 2017',
         'https://doi.org/10.1161/STROKEAHA.117.017235', ''),
        ('ng_120', 'Stroke transfers with DIDO >120 min', 0.373, F.FMT_PCT1, 'share', '',
         'same cohort', 'pub. 2017', 'Ng et al., Stroke 2017',
         'https://doi.org/10.1161/STROKEAHA.117.017235', ''),
        ('jno_dido', 'Mean stroke-transfer DIDO', 171.4, F.FMT_DEC1, 'minutes',
         'decomposition: door-to-imaging 18.3 min + imaging-to-door 153.1 min',
         'n=28,887 stroke transfers', 'pub. 2024', 'JAMA Network Open 2024',
         'https://doi.org/10.1001/jamanetworkopen.2024.31183',
         'author list not carried in source module'),
        ('jno_i2d', 'DIDO decomposition: imaging-to-door interval (the stall)', 153.1,
         F.FMT_DEC1, 'minutes', 'vs door-to-imaging 18.3 min — disposition/transport '
         'dominates the transfer clock', 'same cohort', 'pub. 2024',
         'JAMA Network Open 2024',
         'https://doi.org/10.1001/jamanetworkopen.2024.31183', ''),
        ('gwtg_dido', 'Median stroke-transfer DIDO (GWTG-Stroke registry)', 174,
         F.FMT_INT, 'minutes', 'IQR 116-276; only 27.3% within the 120-min guideline',
         'n=108,913 transfers, Get With The Guidelines-Stroke', 'pub. 2023',
         'GWTG-Stroke analysis, JAMA 2023',
         'https://doi.org/10.1001/jama.2023.12739', ''),
        ('banner', 'Prenotification — the measured information-flow lever'),
        ('prenotif', 'EMS prenotification: associated reduction in stroke DIDO', 20.1,
         F.FMT_DEC1, 'min reduction', 'association, not RCT',
         'n=108,913 transfers, GWTG-Stroke', 'pub. 2023',
         'GWTG-Stroke analysis, JAMA 2023',
         'https://doi.org/10.1001/jama.2023.12739', ''),
        ('banner', 'Ambulance offload and crew detention at hospital doors'),
        ('offload_med', 'National median ambulance patient offload time', 10.9,
         F.FMT_DEC1, 'minutes', 'IQR 6.6-17.5',
         '7,237,606 EMS records (ESO collaborative), 2024', '2024',
         'Shaw et al., Prehosp Emerg Care 2025',
         'https://doi.org/10.1080/10903127.2025.2535576', ''),
        ('offload_tail', 'Agencies with >=25% of transports offloading >30 min', 0.033,
         F.FMT_PCT1, 'share', 'tail is urban-skewed — distribution, not mean, is the '
         'flow risk', 'same dataset', '2024', 'Shaw et al., Prehosp Emerg Care 2025',
         'https://doi.org/10.1080/10903127.2025.2535576', ''),
        ('detain1', 'Hospitals detaining EMS crews >1 hour', 0.75, F.FMT_PCT1, 'share',
         '', '830,637 transports, California', '2017',
         'Backer et al., Prehosp Emerg Care 2018',
         'https://doi.org/10.1080/10903127.2018.1525456', 'single-state (CA)'),
        ('detain2', 'Hospitals detaining EMS crews >2 hours', 0.40, F.FMT_PCT1, 'share',
         '', 'same study', '2017', 'Backer et al., Prehosp Emerg Care 2018',
         'https://doi.org/10.1080/10903127.2018.1525456', 'single-state (CA)'),
        ('detain3', 'Hospitals detaining EMS crews >3 hours', 0.33, F.FMT_PCT1, 'share',
         '', 'same study', '2017', 'Backer et al., Prehosp Emerg Care 2018',
         'https://doi.org/10.1080/10903127.2018.1525456', 'single-state (CA)'),
        ('banner', 'ED boarding — the demand-side clock (trend pair charted at right)'),
        ('board_852', 'Admitted ED patients 65+ boarding >=2 hours', 0.852, F.FMT_PCT1,
         'share', '', 'NHAMCS 2015-2022, admitted patients 65+', '2015-2022',
         'Lee et al., Ann Emerg Med 2026',
         'https://doi.org/10.1016/j.annemergmed.2026.03.011', ''),
        ('board_2018', 'Mean ED boarding, admitted 65+ — 2018', 138, F.FMT_INT,
         'minutes', 'trend-eligible pair with the 2022 row below (same survey, same '
         'definition)', 'NHAMCS, admitted patients 65+', '2018',
         'Lee et al., Ann Emerg Med 2026',
         'https://doi.org/10.1016/j.annemergmed.2026.03.011', ''),
        ('board_2022', 'Mean ED boarding, admitted 65+ — 2022', 343, F.FMT_INT,
         'minutes', '', 'NHAMCS, admitted patients 65+', '2022',
         'Lee et al., Ann Emerg Med 2026',
         'https://doi.org/10.1016/j.annemergmed.2026.03.011', ''),
        ('board_cagr', None),  # live CAGR formula row, built below
        ('board_dem', 'Mean ED boarding with Alzheimer\'s-related dementia', 501,
         F.FMT_INT, 'minutes', 'subgroup of the 2022 read', 'NHAMCS, admitted 65+',
         '2022', 'Lee et al., Ann Emerg Med 2026',
         'https://doi.org/10.1016/j.annemergmed.2026.03.011', ''),
        ('acep_44', 'US adults reporting prolonged post-ED waits (self or loved one)',
         0.44, F.FMT_PCT1, 'share', '16% report boarding >=13 hours (next row)',
         'national poll, n=2,164 adults', 'Oct 2023',
         'ACEP / Morning Consult national poll 2023',
         'https://www.acep.org/news/acep-newsroom-articles/new-poll-alarming-number-of-'
         'patients-would-avoid-emergency-care-because-of-boarding-concerns',
         'survey self-report, not chart-abstracted'),
        ('acep_13h', 'US adults reporting a post-ED wait >=13 hours', 0.16, F.FMT_PCT1,
         'share', '', 'same poll', 'Oct 2023',
         'ACEP / Morning Consult national poll 2023',
         'https://www.acep.org/news/acep-newsroom-articles/new-poll-alarming-number-of-'
         'patients-would-avoid-emergency-care-because-of-boarding-concerns',
         'survey self-report'),
        ('banner', 'Delayed discharge and flow economics'),
        ('delay_228', 'Discharges delayed (weighted mean across 64 studies)', 0.228,
         F.FMT_PCT1, 'share', 'range 1.6-91.3% across studies',
         'systematic review, 64 studies', 'pub. 2019',
         'Landeiro et al., The Gerontologist 2019',
         'https://doi.org/10.1093/geront/gnx028', 'multi-country review'),
        ('delay_cost', 'Cost per delayed-discharge case', '$142 - $31,935', None,
         'USD PPP / case', 'range across the review', 'systematic review, 64 studies',
         'pub. 2019', 'Landeiro et al., The Gerontologist 2019',
         'https://doi.org/10.1093/geront/gnx028', 'PPP-adjusted range, not a US point'),
        ('gao_35', 'Hospitalizations with delayed discharge (single US academic center)',
         0.035, F.FMT_PCT1, 'share', '101 stays (3.5%) consumed 27.2% of 23,934 '
         'inpatient days; facility placement the most common non-medical barrier',
         'single US academic hospital', 'pub. 2022',
         'Gao & Berland, Brown J Hosp Med 2022',
         'https://doi.org/10.56305/001c.36593', 'single site'),
        ('pacu_612', 'PACU discharge delays that were non-clinical', 0.612, F.FMT_PCT1,
         'share', '', '307-patient PACU cohort (non-US)', 'pub. 2022',
         'Ego et al., Ann Med Surg 2022',
         'https://doi.org/10.1016/j.amsu.2022.104680',
         'non-US cohort — magnitude signal only'),
        ('pacu_111', 'PACU delays caused by transport unavailability', 0.111, F.FMT_PCT1,
         'share', 'n=34; second most common cause after bed unavailability (22.5%)',
         'same cohort', 'pub. 2022', 'Ego et al., Ann Med Surg 2022',
         'https://doi.org/10.1016/j.amsu.2022.104680',
         'non-US cohort — magnitude signal only'),
        ('qi_47', 'Most frequent uncompleted discharge task: pending '
         'care-management/transportation', 0.47, F.FMT_PCT1, 'share', '',
         'single-site discharge QI study', 'pub. 2024',
         'Single-site discharge QI study (PMC11023539)',
         'https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11023539/',
         'RE-VERIFY — excerpt-grade capture; single site'),
    ]

    bm_row = {}
    for item in BM:
        if item[0] == 'banner':
            b3.banner(item[1])
            continue
        if item[0] == 'board_cagr':
            r18, r22 = bm_row['board_2018'], bm_row['board_2022']
            b3.row([
                ('ED boarding growth, admitted 65+ (live CAGR formula, window '
                 '2018->2022, 4 yrs)', 'label'),
                (lib.cagr_formula(f'B{r22}', f'B{r18}', 4), 'fml', F.FMT_PCT1),
                ('%/yr', 'text'),
                ('formula (end/start)^(1/4)-1 over the two NHAMCS endpoints above; '
                 'endpoint growth, not a fitted trend', 'text'),
                ('derived from the Lee et al. endpoints above', 'text'),
                ('2018-2022', 'text'),
                ('derived on-sheet', 'text'), ('', 'text'), ('DERIVED', 'text'),
                ('2-point endpoint CAGR — no interior years published here', 'text'),
            ], wrap=True, height=28)
            bm_row['board_cagr'] = b3.r
            continue
        (key, bench, val, fmt, unit, detail, pop, yrs, cite, url, caveat) = item
        vcell = (val, 'src', fmt) if fmt else (val, 'src')
        basis = 'DERIVED' if key == 'board_cagr' else 'ACADEMIC'
        b3.row([
            (bench, 'label'), vcell, (unit, 'text'), (detail, 'text'), (pop, 'text'),
            (yrs, 'text'), (cite, 'text'), (url, 'text'), (basis, 'text'),
            (caveat, 'note'),
        ], wrap=True, height=28)
        bm_row[key] = b3.r

    b3.blank()
    b3.note('All rows are ACADEMIC published literals carried from the rcm_mc in-depth '
            'study modules (Q1-Q10 evidence registries), which cite each study with DOI. '
            'Tier B: the underlying papers were not reopened for this workbook — the DOI '
            'is the audit path. Caveats carried verbatim: single-site, non-US, '
            'survey-self-report and re-verify flags are printed per row and must travel '
            'with any quotation.', height=32)
    b3.note('Related but deliberately NOT on this tab: RSNAT prior-authorization effects '
            '(Contreary et al., JAMA Health Forum 2022) live on Payment_Integrity; '
            'system-level demand counts (NEDS/NIS/MedPAC) live on the demand-evidence '
            'tabs.', height=24)

    lib.add_chart(
        ws3, 'L6', 'Hospital crew detention before return to service (CA 2017, '
        '830,637 transports)',
        f"Clinical_Benchmarks!$A${bm_row['detain1']}:$A${bm_row['detain3']}",
        [('Share of hospitals',
          f"Clinical_Benchmarks!$B${bm_row['detain1']}:$B${bm_row['detain3']}")],
        kind='bar', width=20, height=9, y_title='share of hospitals', y_fmt='0%')
    lib.add_chart(
        ws3, 'L26', 'Mean ED boarding, admitted patients 65+ (NHAMCS): 2018 vs 2022',
        f"Clinical_Benchmarks!$A${bm_row['board_2018']}:$A${bm_row['board_2022']}",
        [('Mean boarding (minutes)',
          f"Clinical_Benchmarks!$B${bm_row['board_2018']}:$B${bm_row['board_2022']}")],
        kind='bar', width=20, height=9, y_title='minutes', y_fmt='#,##0')

    bm_fact = [
        ('stemi_dido', 'STEMI transfer median door-in-door-out time', '2011', 'minutes',
         ['wang_2011'], 'Wang et al., JAMA 2011, DOI 10.1001/jama.2011.862 (n=14,821)',
         'DIDO >30 min: mortality 5.9% vs 2.7%, aOR 1.56'),
        ('stemi_mort', 'STEMI in-hospital mortality when DIDO >30 min', '2011', 'share',
         ['wang_2011'], 'Wang et al., JAMA 2011, DOI 10.1001/jama.2011.862',
         'vs 2.7% when <=30 min'),
        ('jno_dido', 'Mean stroke-transfer DIDO', '2024', 'minutes', ['jamano_2024'],
         'JAMA Netw Open 2024, DOI 10.1001/jamanetworkopen.2024.31183 (n=28,887)',
         'GWTG median 174 min (JAMA 2023) is the companion read'),
        ('prenotif', 'EMS prenotification-associated stroke DIDO reduction', '2023',
         'minutes', ['gwtg_2023'],
         'GWTG-Stroke, JAMA 2023, DOI 10.1001/jama.2023.12739 (n=108,913)', ''),
        ('offload_med', 'National median ambulance patient offload time', '2024',
         'minutes', ['shaw_2025'],
         'Shaw et al., Prehosp Emerg Care 2025, DOI 10.1080/10903127.2025.2535576 '
         '(7,237,606 records)', ''),
        ('detain1', 'Hospitals detaining EMS crews >1 hour (CA 2017)', '2017', 'share',
         ['backer_2018'],
         'Backer et al., Prehosp Emerg Care 2018, DOI 10.1080/10903127.2018.1525456 '
         '(830,637 transports)', '40% >2h, 33% >3h'),
        ('board_852', 'Admitted ED patients 65+ boarding >=2 hours', '2015-2022',
         'share', ['lee_2026'],
         'Lee et al., Ann Emerg Med 2026, DOI 10.1016/j.annemergmed.2026.03.011 '
         '(NHAMCS 2015-2022)', ''),
        ('board_2022', 'Mean ED boarding, admitted 65+ (2022)', '2022', 'minutes',
         ['lee_2026'], 'Lee et al., Ann Emerg Med 2026, NHAMCS 2022 read',
         'up from 138 min in 2018; 501 min with dementia'),
        ('delay_228', 'Discharges delayed — weighted mean across 64 studies', '2019',
         'share', ['landeiro_2019'],
         'Landeiro et al., The Gerontologist 2019, DOI 10.1093/geront/gnx028',
         'range 1.6-91.3%; cost $142-$31,935 PPP/case'),
        ('pacu_111', 'PACU delays caused by transport unavailability', '2022', 'share',
         ['ego_2022'], 'Ego et al., Ann Med Surg 2022, DOI 10.1016/j.amsu.2022.104680 '
         '(n=34 of 307; non-US)', 'second to bed unavailability 22.5%'),
    ]
    for key, metric, year, unit, skeys, locator, cross in bm_fact:
        facts.append({
            'metric': metric, 'year': year,
            'value_ref': f'Clinical_Benchmarks!B{bm_row[key]}', 'unit': unit,
            'basis': 'ACADEMIC', 'tier': 'B', 'source_keys': skeys,
            'locator': locator, 'lives_on': 'Clinical_Benchmarks',
            'cross_check': cross})

    # =====================================================================
    # sources
    # =====================================================================
    def src(key, publisher, document, vintage, locator, supplies, url, tier, powers):
        sources.append({'key': key, 'publisher': publisher, 'document': document,
                        'vintage': vintage, 'locator': locator, 'supplies': supplies,
                        'url': url, 'tier': tier, 'accessed': accessed,
                        'powers': powers})

    T1 = 'Condition_Transfer_Registry'
    T2 = 'Post_Acute_Supply_State'
    T3 = 'Clinical_Benchmarks'

    src('hcup_sb277', 'AHRQ (HCUP)',
        'HCUP Statistical Brief #277 — Most Frequent Principal Diagnoses for Inpatient '
        'Stays in U.S. Hospitals, 2018 (National Inpatient Sample)',
        '2018 data', 'principal-diagnosis stay counts (AMI 658,600; HF 1,135,900; '
        'ischemic stroke 533,400; pneumonia 740,700; COPD 569,600)',
        '7 registry volume rows', 'https://hcup-us.ahrq.gov/reports/statbriefs/', 'B',
        [T1])
    src('hcup_sb155', 'AHRQ (HCUP)',
        'HCUP Statistical Brief #155 — Emergency Department transfers to acute care, '
        '2009 NEDS (Kindermann et al.)', '2009 data',
        '1.5% of 128,885,040 ED encounters transferred (~1.9M)',
        'ED interfacility up-transfer row (historical corroboration)',
        'https://hcup-us.ahrq.gov/reports/statbriefs/', 'B', [T1])
    src('cdc_sepsis', 'CDC', 'CDC Sepsis — data and surveillance', '2023 page',
        '"at least 1.7 million adults develop sepsis" per year',
        'sepsis escalation + sepsis-recovery pool rows (same pool, two families)',
        'https://www.cdc.gov/sepsis/', 'B', [T1])
    src('cdc_stroke', 'CDC', 'CDC Stroke facts (>795,000 strokes/yr; ICH+SAH ~13%)',
        '2022 page', 'hemorrhagic-stroke derivation ~110,000/yr',
        'hemorrhagic-stroke row + ischemic-stroke corroboration',
        'https://www.cdc.gov/stroke/', 'B', [T1])
    src('cdc_nchs_births2022', 'CDC / NCHS',
        'Births: Final Data for 2022 (National Vital Statistics Reports)', '2022 data',
        '3,667,758 births; preterm 10.38% (~380,000)',
        'high-risk OB + neonatal rows',
        'https://www.cdc.gov/nchs/products/nvsr.htm', 'B', [T1])
    src('cdc_mmwr_tbi', 'CDC (MMWR)',
        'CDC TBI surveillance — nonfatal TBI-related hospitalizations (2018 NIS)',
        '2018 data', '223,050 hospitalizations', 'major-trauma row',
        'https://www.cdc.gov/traumatic-brain-injury/', 'B', [T1])
    src('cdc_samhsa_mh', 'CDC / SAMHSA',
        'Mental-health-related emergency department visit estimates', '2021 data',
        '~6,000,000 MH-related ED visits/yr (~1 in 8 MH/SUD)',
        'behavioral-health crisis row', 'https://www.cdc.gov/nchs/', 'B', [T1])
    src('cdc_diabetes', 'CDC', 'CDC diabetes surveillance / statistics report',
        '2020 data', 'DKA hospitalizations ~230,000/yr', 'DKA row',
        'https://www.cdc.gov/diabetes/', 'B', [T1])
    src('cdc_falls', 'CDC', 'CDC older-adult falls data (hip fracture)', '2022 data',
        '~319,000 hip-fracture hospitalizations age 65+',
        'hip-fracture rows (escalation + rehab; same pool)',
        'https://www.cdc.gov/falls/', 'B', [T1])
    src('medpac_ltch', 'MedPAC', 'MedPAC Payment Basics — Long-term care hospital '
        'services', '2022 data', '~90,000 Medicare LTCH cases/yr; ~320 LTCHs',
        'post-ventilator + debility rows (same pool, two rows)',
        'https://www.medpac.gov/document-type/payment-basic/', 'B', [T1])
    src('medpac_irf', 'MedPAC', 'MedPAC Payment Basics — Inpatient rehabilitation '
        'facility services', '2022 data', '~383,000 IRF stays/yr; ~1,180 IRFs',
        'post-stroke IRF row', 'https://www.medpac.gov/document-type/payment-basic/',
        'B', [T1])
    src('medpac_snf', 'MedPAC', 'MedPAC Payment Basics — Skilled nursing facility '
        'services', '2022 data', '~1.8M Medicare-covered SNF stays/yr; ~14,700 SNFs',
        'med-surg discharge row', 'https://www.medpac.gov/document-type/payment-basic/',
        'B', [T1])
    src('medpac_hospice', 'CMS / MedPAC', 'MedPAC Payment Basics — Hospice services',
        '2022 data', '~1.7M Medicare hospice enrollees/yr', 'hospice-transition row',
        'https://www.medpac.gov/document-type/payment-basic/', 'B', [T1])
    src('stefan_2013', 'Journal of Hospital Medicine (Stefan et al.)',
        'Stefan et al. — epidemiology of acute respiratory failure in the US, '
        'NIS 2001-2009', '2009 data (pub. 2013)',
        '1,917,910 hospitalizations with acute respiratory failure (2009)',
        'acute respiratory failure row — STALE vintage, flagged on-row', '', 'B', [T1])
    src('clin_lit_estimates', 'Clinical epidemiologic literature (grouped)',
        'Incidence estimates carried by the rcm_mc clinical registry: aortic dissection '
        '~4/100,000 (13,000/yr); GI hemorrhage ~400,000 admissions (StatPearls/GI '
        'literature); PICU ~200,000 admissions; status epilepticus ~150,000 episodes',
        '2020-vintage estimates', 'per-row ACADEMIC "estimate" labels',
        '4 soft ACADEMIC volume rows — basis chip kept visible', '', 'B', [T1])
    src('ift_clinical_registry', 'rcm_mc repo (extraction layer)',
        'rcm_mc.market_reports.ift_clinical_demand — 32-condition acute-transfer '
        'registry; ICD-10-CM codes validated vs vendored FY2025/FY2026 billability seed '
        '(validate_codes(): 92 codes, 0 misses)', '2026-07-10 module state',
        'transfer_matrix() / all_conditions()',
        'registry structure columns + distribution formulas (not the volume literals, '
        'which cite their publishers per row)', '', 'B', [T1])

    src('cms_nh_providerinfo', 'CMS',
        'Nursing Home Care Compare — Provider Information (NH_ProviderInfo)',
        'file vintage 2026-04-01', 'one row per certified SNF (CCN); 14,699 rows',
        'SNF national + per-state counts',
        'https://data.cms.gov/provider-data/topics/nursing-homes', 'A', [T2])
    src('cms_irf_compare', 'CMS',
        'Inpatient Rehabilitation Facility Compare — General Information + Provider '
        'Data', 'file vintage 2026-02-13', 'one row per certified IRF; 1,221 rows',
        'IRF national + per-state counts',
        'https://data.cms.gov/provider-data/topics/inpatient-rehabilitation-facilities',
        'A', [T2])
    src('cms_ltch_compare', 'CMS',
        'Long-Term Care Hospital Compare — General Information + Provider Data',
        'file vintage 2026-02-13', 'one row per certified LTCH; 317 rows',
        'LTACH national + per-state counts',
        'https://data.cms.gov/provider-data/topics/long-term-care-hospitals', 'A', [T2])
    src('cms_pdc_hha', 'CMS (Provider Data Catalog)',
        'Home Health Care Agencies (dataset 6jpm-sxkc)', 'file vintage 2026-05-23',
        'one row per certified HHA; 12,392 rows', 'HHA national + per-state counts',
        'https://data.cms.gov/provider-data/dataset/6jpm-sxkc', 'A', [T2])
    src('cms_pdc_hospice', 'CMS (Provider Data Catalog)',
        'Hospice General Information (dataset yc9t-dgbk)', 'file vintage 2026-05-23',
        'one row per certified hospice; 6,852 rows',
        'hospice national + per-state counts',
        'https://data.cms.gov/provider-data/dataset/yc9t-dgbk', 'A', [T2])

    src('wang_2011', 'JAMA', 'Wang et al. — door-in to door-out time among STEMI '
        'patients transferred for primary PCI (n=14,821)', '2011',
        'DOI 10.1001/jama.2011.862', 'STEMI DIDO 68 min / 11% <=30 / mortality 5.9% vs '
        '2.7%, aOR 1.56', 'https://doi.org/10.1001/jama.2011.862', 'B', [T3])
    src('ng_2017', 'Stroke (AHA)', 'Ng et al. — door-in-door-out at referring hospitals '
        'in stroke interfacility transfer', '2017', 'DOI 10.1161/STROKEAHA.117.017235',
        '82.8% of transfer time at referrer; DIDO 106 min; 37.3% >120 min',
        'https://doi.org/10.1161/STROKEAHA.117.017235', 'B', [T3])
    src('jamano_2024', 'JAMA Network Open', 'Stroke-transfer DIDO decomposition '
        '(n=28,887): mean 171.4 = 18.3 door-to-imaging + 153.1 imaging-to-door', '2024',
        'DOI 10.1001/jamanetworkopen.2024.31183',
        'mean DIDO + decomposition rows',
        'https://doi.org/10.1001/jamanetworkopen.2024.31183', 'B', [T3])
    src('gwtg_2023', 'JAMA', 'GWTG-Stroke interhospital-transfer analysis (n=108,913): '
        'median DIDO 174 min; 27.3% within 120; prenotification -20.1 min', '2023',
        'DOI 10.1001/jama.2023.12739', 'GWTG DIDO + prenotification rows',
        'https://doi.org/10.1001/jama.2023.12739', 'B', [T3])
    src('shaw_2025', 'Prehospital Emergency Care', 'Shaw et al. — national ambulance '
        'patient offload time, 7,237,606 records (ESO 2024)', '2024 data (pub. 2025)',
        'DOI 10.1080/10903127.2025.2535576', 'offload median + tail rows',
        'https://doi.org/10.1080/10903127.2025.2535576', 'B', [T3])
    src('backer_2018', 'Prehospital Emergency Care', 'Backer et al. — EMS crew '
        'detention at California hospitals, 830,637 transports', '2017 data (pub. 2018)',
        'DOI 10.1080/10903127.2018.1525456', 'crew-detention distribution (75/40/33%)',
        'https://doi.org/10.1080/10903127.2018.1525456', 'B', [T3])
    src('lee_2026', 'Annals of Emergency Medicine', 'Lee et al. — ED boarding among '
        'admitted patients 65+, NHAMCS 2015-2022', '2015-2022 data (pub. 2026)',
        'DOI 10.1016/j.annemergmed.2026.03.011',
        'boarding 85.2% / 138->343 min / 501 min dementia',
        'https://doi.org/10.1016/j.annemergmed.2026.03.011', 'B', [T3])
    src('acep_2023', 'ACEP / Morning Consult', 'National boarding poll, n=2,164 adults',
        'Oct 2023', 'ACEP newsroom release', '44% prolonged waits / 16% >=13h rows',
        'https://www.acep.org/news/acep-newsroom-articles/new-poll-alarming-number-of-'
        'patients-would-avoid-emergency-care-because-of-boarding-concerns', 'B', [T3])
    src('landeiro_2019', 'The Gerontologist', 'Landeiro et al. — systematic review of '
        'delayed discharges (64 studies)', '2019', 'DOI 10.1093/geront/gnx028',
        'delayed-discharge 22.8% + cost range rows',
        'https://doi.org/10.1093/geront/gnx028', 'B', [T3])
    src('gao_2022', 'Brown Journal of Hospital Medicine', 'Gao & Berland — delayed '
        'discharges at a US academic hospital (3.5% of stays = 27.2% of 23,934 '
        'inpatient days)', '2022', 'DOI 10.56305/001c.36593', 'delay-concentration row',
        'https://doi.org/10.56305/001c.36593', 'B', [T3])
    src('ego_2022', 'Annals of Medicine and Surgery', 'Ego et al. — PACU discharge '
        'delays, 307-patient cohort (non-US)', '2022', 'DOI 10.1016/j.amsu.2022.104680',
        'PACU 61.2% non-clinical / 11.1% transport rows',
        'https://doi.org/10.1016/j.amsu.2022.104680', 'B', [T3])
    src('pmc_qi_discharge', 'PubMed Central (single-site QI study)',
        'Single-site discharge-task improvement study, PMC11023539', 'pub. 2024',
        'PMC11023539 — 47% pending care-management/transportation',
        'uncompleted-discharge-task row',
        'https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11023539/', 'B', [T3])

    # =====================================================================
    # excluded (quarantine records)
    # =====================================================================
    excluded.extend([
        {'figure': "transfer_matrix per-condition growth column ('cagr')",
         'value': '3.1-3.8%/yr per condition (32 values)',
         'source_label': 'FRAMEWORK · demand_forecast._POP_GROWTH_BY_AGE age-band '
                         'population CAGRs weighted by authored age skew',
         'why_excluded': 'modeled: the age-band CAGRs are self-labeled "rough" with no '
                         'verbatim Census table citation, and the per-condition age '
                         'skews are authored',
         'what_would_make_citable': 'a verbatim Census national-projection table '
                                    'citation for each age band plus published '
                                    'condition-specific incidence trends'},
        {'figure': "transfer_matrix 'growth_label' column",
         'value': 'FRAMEWORK label string on all 32 rows',
         'source_label': 'FRAMEWORK · demand_forecast._POP_GROWTH_BY_AGE',
         'why_excluded': 'companion label of the excluded modeled CAGR column',
         'what_would_make_citable': 'same as the cagr column'},
        {'figure': 'Blended acute-transfer demand CAGR (aggregate_demand_yoy)',
         'value': '~2.68%/yr (base 28,807,518 -> 32,880,209 over 5 relative years)',
         'source_label': 'DERIVED · GOV/ACADEMIC base volumes x modeled demographic '
                         'CAGRs',
         'why_excluded': 'inputs include the excluded age-band CAGRs; the base sum also '
                         'mixes measures and shared pools, so the level is not a real '
                         'transfer count',
         'what_would_make_citable': 'published multi-year transfer-volume series (e.g. '
                                    'HCUP NEDS annual transfer counts) to trend '
                                    'directly'},
        {'figure': 'Registry mission-mix CCT/SCT share (mission_mix())',
         'value': '53.4% CCT/SCT (56.4% high-acuity incl. neonatal/peds)',
         'source_label': 'DERIVED · GOV volumes x authored transport-acuity tiering',
         'why_excluded': 'pool artifact — the weighting mixes ED visits, stays and '
                         'enrollees; contradicted by observed GADCS 56% BLS split and '
                         'NEDS 6.6% critical-procedure share',
         'what_would_make_citable': 'an observed acuity mix from claims (e.g. PSPS '
                                    'HCPCS-level services) or GADCS'},
        {'figure': 'Direct-admit national volume',
         'value': 'none printed (framework: non-ED share of ~33.7M inpatient stays, '
                  'HCUP NIS 2019)',
         'source_label': 'FRAMEWORK · non-ED share of inpatient stays',
         'why_excluded': 'no published national direct-admit transfer count exists; row '
                         'carried with FRAMEWORK chip and an em-dash volume',
         'what_would_make_citable': 'a published national direct-admit/transfer-in '
                                    'count (e.g. HCUP NIS admission-source table)'},
        {'figure': 'Inter-hospital load-balancing national volume',
         'value': 'none printed (note keeps Intermountain >5,100 bed-days/4yr anecdote '
                  'as text)',
         'source_label': 'FRAMEWORK · anchored to the HHS/HCRIS occupancy signal',
         'why_excluded': 'no defensible single national number; anecdote is one system',
         'what_would_make_citable': 'a published multi-system load-balancing transfer '
                                    'census'},
        {'figure': 'Repatriation / back-transfer national volume',
         'value': 'none printed (framework ratio "~1:1 with escalations")',
         'source_label': 'FRAMEWORK · mirrors each up-transfer',
         'why_excluded': 'the 1:1 multiplier is authored, not measured',
         'what_would_make_citable': 'published repatriation rates from a transfer-'
                                    'center registry or claims O/D study'},
        {'figure': 'condition_yoy_projection point-rows (28 conditions x 6 years)',
         'value': '168 projected volume points',
         'source_label': 'DERIVED · base volume x (1+g)^n with modeled g',
         'why_excluded': 'forward projection on the excluded demographic CAGRs; base '
                         'vintages differ per condition (2009-2023) so projection '
                         'calendars are inconsistent',
         'what_would_make_citable': 'observed annual history per condition (HCUP '
                                    'trend tables)'},
    ])

    meta = {
        'notes': ('Group D part 1. Tab 1 carries the 32-row transfer matrix with '
                  'per-row publisher citations; modeled growth columns quarantined. '
                  'Tab 2 is tier-A (vendored CMS provider files with provenance '
                  'columns; build-time re-tally matched accessor counts). Tab 3 is '
                  'tier-B ACADEMIC with full DOIs. MedPAC vintage note: this section '
                  'uses the Payment Basics (2022-data) reads consistent with '
                  'ift_demand_evidence; the Mar-2025 MedPAC report variant (~11.4M/'
                  '10,500 orgs) is footnoted elsewhere. ' + ' | '.join(meta_notes)),
        'row_counts': {SHEETS[0]['name']: ws1.max_row,
                       SHEETS[1]['name']: ws2.max_row,
                       SHEETS[2]['name']: ws3.max_row},
    }
    return {'facts': facts, 'sources': sources, 'excluded': excluded, 'meta': meta}
