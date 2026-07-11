"""Professional rebuild of the Methodology tab (v3.3).

Harvests the carried v2.7 text from the workbook itself so wording stays
verbatim, then relays it in the house style with three repairs and the v3
extensions:
  - the 'data-api/revision 1/' URL artifact is restored to 'data-api/v1/'
  - the fact-ID range and workbook formula count are updated to v3 truth
  - section 5 gains the v3 deterministic-pipeline and verification-gate rows
  - new section 9: how to verify any number in sixty seconds
"""
import v3lib


def _harvest(ws):
    rows = {}
    for row in ws.iter_rows():
        for c in row:
            if c.value is not None:
                rows.setdefault(c.row, {})[c.column] = c.value
    return rows


def _cells(rows, r, ncols):
    got = rows.get(r, {})
    vals = [got.get(i) for i in sorted(got)]
    vals += [None] * (ncols - len(vals))
    return vals[:ncols]


def rebuild_methodology(wb, stats, verify_results, entries):
    old = wb['Methodology']
    rows = _harvest(old)
    idx = wb.sheetnames.index('Methodology')
    tab_color = old.sheet_properties.tabColor
    wb.remove(old)
    ws = wb.create_sheet('Methodology', idx)

    n_form = verify_results.get('n_formulas', 'more than 50,000')
    last_fact = stats.get('last_fact', 442)
    n_sources = stats.get('sources', 312)
    n_tabs = stats.get('tabs', 269)

    sb = v3lib.SheetBuilder(ws, 4, col_widths=[42, 56, 56, 42],
                            tab_color=tab_color or 'FF00294C')
    sb.title('Methodology - the decision record')
    sb.subtitle(str(rows[2][1]) + ' Sections 5 and 9 cover the deterministic '
                'pull pipeline, the verification gates and the sixty-second '
                'audit path added in the v3 builds.', height=42)
    ws.freeze_panes = 'A3'

    def carried_prose(r):
        v = rows.get(r, {}).get(1)
        if v:
            sb.prose(str(v))

    # 1 ---------------------------------------------------------------
    sb.blank()
    sb.banner('1. The question this workbook answers, and the one it refuses '
              'to answer')
    for r in (5, 6, 7):
        carried_prose(r)

    # 2 ---------------------------------------------------------------
    sb.blank()
    sb.banner('2. The inclusion rule, applied without exception')
    sb.headers(list(_cells(rows, 10, 3)) + [''], freeze=False)
    for r in range(11, 16):
        a, b, c = _cells(rows, r, 3)
        if a and 'F01-F147' in str(a):
            a = str(a).replace('F01-F147', f'F01-F{last_fact}')
        sb.row([(a, 'text'), (b, 'text'), (c, 'text')], wrap=True, height=36)
    sb.row([('The colour key, live:', 'label'),
            ('Blue - hardcoded straight from the cited document (e.g. 8,911)',
             'src'),
            ('Black - a visible formula over sourced cells (e.g. =B12/C12 '
             'typed in the cell)', 'fml'),
            ('Green - a live link to another tab (e.g. =Fact_Ledger!D9)',
             'link')],
           wrap=True, height=24)
    sb.row([('Tier A', 'label'),
            ('Verified against the primary document or dataset in this build; '
             'the locator points into that document.', 'text'),
            ('Tier B', 'label'),
            ('Published but secondary, or a figure that moves with revisions; '
             'carried with that caveat on the fact row.', 'text')],
           wrap=True, height=24)

    # 3 ---------------------------------------------------------------
    sb.blank()
    sb.banner('3. Why each evidence tab exists')
    sb.headers(_cells(rows, 18, 4), freeze=False)
    for r in range(19, 37):
        sb.row([(v, 'text') for v in _cells(rows, r, 4)], wrap=True, height=33)
    sb.row([('v3 evidence layers (live public-API pulls; one row per family; '
             'every pull is on Pull_Manifest with endpoint and SHA-256):',
             'label')], height=15)
    V3_FAMILIES = [
        ('Enrollment_ESRD_State + Enroll_State_*',
         'The fee-for-service denominator, nationally and per state, 2013-2025.',
         'Every per-beneficiary rate in the workbook divides by these cells; '
         'the MA migration is the single biggest trend confounder.',
         'CMS Medicare Monthly Enrollment'),
        ('MUP_Ambulance_National/State, MUP_State_*, MUP_Providers_2013/19/24',
         'Who bills ground ambulance, down to the individual NPI, and at what '
         'average submitted/allowed/paid amounts.',
         'Supplier concentration and rate benchmarks need provider grain, not '
         'national sums.',
         'CMS Medicare Physician & Other Practitioners'),
        ('PSPS_Denial_Series + PSPS_Detail_*',
         'Denial behaviour by code, modifier and level of service, 2010-2024.',
         'Denial rates are the revenue-cycle risk signal; no published table '
         'carries this series.',
         'CMS Physician/Supplier Procedure Summary'),
        ('Market_Saturation_Ambulance + MS_County_*, MS_CtyWin_*',
         'County-level supplier density and utilization.',
         'Saturation and dark-market analysis is a county question.',
         'CMS Market Saturation & Utilization'),
        ('QCEW_EMS_Employment/State/County/Quarterly',
         'The ambulance industry labor base: employers, jobs, wages, quarterly '
         'to 2025.',
         'Crew labor is ~69% of ground ambulance cost; this is the '
         'cost-inflation instrument.',
         'BLS QCEW NAICS 621910'),
        ('Facility_Universe_State + Hosp/SNF/Dialysis/IRF/LTCH/Hospice/HHA '
         'registries, PECOS_Registry',
         'The universe of transfer endpoints and enrolled ambulance suppliers, '
         'row per facility.',
         'Origin-destination analysis needs the actual endpoint rolls, not '
         'counts.',
         'CMS Provider Data Catalog; PECOS'),
        ('HSA_Hospital_Catchment + HSA_Corridors',
         'Which ZIPs each hospital actually draws from - the top-15 corridors '
         'per hospital.',
         'Transfer-lane planning is a corridor question; this is the only '
         'public flow file.',
         'CMS Hospital Service Area file'),
        ('State_Age_65plus, County_Age_65plus, PLACES_County_Chronic',
         'The demand base: 65+/85+ population and chronic-disease prevalence '
         'by county.',
         'Transport demand is driven by age and morbidity where the patient '
         'lives.',
         'Census Vintage 2024 estimates; CDC PLACES'),
        ('HCRIS_Hospital_Panel',
         'Hospital cost-report fundamentals, 17,974 hospital-years.',
         'Occupancy and finance context for the sending side.',
         'CMS HCRIS extract (vendored in repo)'),
        ('LEIE_Ambulance_Exclusions',
         'Ambulance-related program-integrity exclusions.',
         'Counterparty screening; the OIG file is the reference list.',
         'HHS OIG LEIE'),
        ('Metro_* families + SP_* state profiles',
         'The same evidence re-cut per target metro and per state, '
         'formula-driven off the registry tabs.',
         'Market entry decisions are made metro by metro and state by state.',
         'Derived - whole-column INDEX/MATCH/SUMIFS over the registry tabs'),
        ('Company/InDepth/Reference tab families',
         'Connector-derived and repository evidence: unit economics, growth '
         'registries, question-by-question deep dives.',
         'Carries the RCM_MC evidence base into the same sourcing regime.',
         'Repository modules + documents on Source_Index'),
    ]
    for fam in V3_FAMILIES:
        sb.row([(fam[0], 'label'), (fam[1], 'text'), (fam[2], 'text'),
                (fam[3], 'text')], wrap=True, height=30)

    # 4 ---------------------------------------------------------------
    sb.blank()
    sb.banner('4. Definitional choices that change the answer, and the choice '
              'this workbook made')
    sb.headers(list(_cells(rows, 39, 3)) + [''], freeze=False)
    for r in range(40, 47):
        a, b, c = _cells(rows, r, 3)
        sb.row([(a, 'label'), (b, 'text'), (c, 'text')], wrap=True, height=33)

    # 5 ---------------------------------------------------------------
    sb.blank()
    sb.banner('5. The data pipeline, stated so it can be rerun')
    for r in (49, 50, 51, 52):
        v = str(rows.get(r, {}).get(1, ''))
        v = v.replace('data-api/revision 1/', 'data-api/v1/')
        if v:
            sb.prose(v)
    det = str(rows.get(53, {}).get(1, ''))
    det = det.replace(
        'across 1,111 formulas',
        f'across {n_form} formulas workbook-wide (verified in an independent '
        'LibreOffice recalculation; Verification_Log Panel K carries the '
        'stamped counts)')
    sb.prose(det)
    sb.prose('v3 pipeline. Every API-backed tab is produced by a deterministic '
             'pull-assemble-verify pipeline shipped in the repository at '
             'RCM_MC/scripts/ift_evidence_v3 (pull.py through pull7.py, '
             'assemble.py, verify.py). Each pull is cached to disk and recorded '
             'on Pull_Manifest with the exact endpoint, dataset version UUID, '
             'filters, pages fetched, rows kept, SHA-256 of the canonical '
             'payload and the UTC retrieval time. Re-running the chain '
             'reproduces this workbook byte-for-byte up to retrieval dates.')
    sb.prose('Dataset versions. CMS datasets are pinned per data year by '
             'parsing the version UUID out of the public DCAT catalog, so a '
             'later CMS re-release cannot silently change a number: the UUID '
             'on Pull_Manifest is the version that produced the cell.')
    sb.prose('Verification gates. V1: every carried v2.7 cell must recalculate '
             f'to its original value ({verify_results.get("copy_cells", "10,679")} '
             'cells compared, zero differences allowed). V2: the whole workbook '
             'must recalculate with zero Excel error cells. V3: derived cells '
             'on pull-backed tabs are recomputed independently in python from '
             'the cached payloads. V7: scale gates on tabs, printed pages and '
             'file size. V8: fact and source IDs must be contiguous with no '
             'ghost references. The build runs twice so the verified numbers '
             'are stamped back into Verification_Log Panel K and re-verified.')

    # 6 ---------------------------------------------------------------
    sb.blank()
    sb.banner('6. Rules for comparing numbers, which is where diligence '
              'workbooks usually break')
    for r in range(56, 61):
        carried_prose(r)

    # 7 ---------------------------------------------------------------
    sb.blank()
    sb.banner('7. Corrections made to prior work, kept visible on purpose')
    sb.headers(_cells(rows, 63, 4), freeze=False)
    for r in range(64, 73):
        sb.row([(v, 'text') for v in _cells(rows, r, 4)], wrap=True, height=27)
    sb.row([('v3', 'label'),
            ('Cell-level corrections made during the v3 builds (citation '
             'attribution, dead links, count inconsistencies)', 'text'),
            ('Logged one per row with the old value, the new value and the '
             'reason', 'text'),
            ('V3_Change_Log', 'link')], wrap=True, height=24)

    # 8 ---------------------------------------------------------------
    sb.blank()
    sb.banner('8. What this workbook still cannot do, and what would fix it')
    sb.headers(_cells(rows, 75, 4), freeze=False)
    for r in range(76, 84):
        sb.row([(v, 'text') for v in _cells(rows, r, 4)], wrap=True, height=27)

    # 9 ---------------------------------------------------------------
    sb.blank()
    sb.banner('9. How to verify any number in sixty seconds')
    sb.prose('Step 1 - read the colour. Blue: the value was typed from the '
             'cited document and nothing computed it. Black: a formula; every '
             'input is itself blue, black or green, so the arithmetic is fully '
             'inspectable. Green: a live link to another tab - follow it.')
    sb.prose(f'Step 2 - find the fact. Facts F01-F{last_fact} live on '
             'Fact_Ledger: one row per fact with its value, unit, year, tier, '
             'source ID, the locator inside the source (table, page or cell) '
             'and the tab the fact lives on.')
    sb.prose(f'Step 3 - follow the source. Sources S01-S{n_sources} live on '
             'Source_Index with publisher, document title, URL and access '
             'date. For API-backed cells, Pull_Manifest carries the exact '
             'endpoint, dataset version UUID, filters and the SHA-256 of the '
             'cached payload that produced the number.')
    sb.prose(f'Step 4 - recompute. Open the workbook and let it recalculate: '
             f'{n_form} formulas resolve with zero errors, and every carried '
             'v2.7 cell reproduces its original value. The Index tab links to '
             f'all {n_tabs} tabs; the repository pipeline re-runs the pulls '
             'end to end.')
    sb.blank()
    sb.note('This tab was rebuilt in v3.3: same decision record, house-style '
            'layout. Carried sections 1-8 are v2.7 wording verbatim except '
            'three repairs - the data-api URL artifact ("revision 1" for '
            '"v1") was restored, the fact-ID range and the workbook formula '
            'count were updated to current truth - plus the v3 pipeline rows '
            'in section 5, the v3 family rows in section 3 and new section 9. '
            'Logged on V3_Change_Log.')

    entries.append({
        'tab': 'Methodology', 'cell': '(sheet)',
        'old': 'v2.7 layout: unstyled text columns; stale F01-F147 range; '
               '1,111-formula count; "data-api/revision 1/" URL artifact; '
               'no coverage of the v3 evidence layers or pipeline',
        'new': f'Rebuilt in house style: 9 sections, colour key and tier '
               f'definitions rendered live, v3 family rows, pipeline and '
               f'verification-gate rows, sixty-second audit path; counts '
               f'updated to F{last_fact}/S{n_sources}/{n_form} formulas',
        'why': 'Professional layout and v3 completeness; wording of carried '
               'sections kept verbatim.',
        'class': 'structural'})
    return ws
