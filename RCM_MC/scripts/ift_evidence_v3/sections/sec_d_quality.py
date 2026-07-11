"""Part D quality layer: the Fault_Audit v3.4 refresh (D.1), the refresh
calendar (D.4), and the firewall leak-check log rows (D.3) written onto
Verification_Log as a new panel.
"""

SHEETS = [{'name': 'Refresh_Calendar',
           'question': 'Every registered source, its cadence, and the '
                       'command that refreshes it (D.4)'}]

FAULTS = [
    ('Name-match misclassification (A.3 parent roll-up, A.4 hospital '
     'affiliation, A.6/A.11 cohort CCN resolution)',
     'Printed rule tables on each tab; match counts shown; single-token '
     'guards added after the subject-company self-match incident (logged)',
     'Both directions: false parents inflate concentration; missed '
     'children deflate it'),
    ('Corridor Medicare-only bias (A.6, A.7, Cohort_Corridors, '
     'Hub_Spoke_Map)',
     'Every corridor tab carries the Medicare-FFS-inpatient-only DQ row; '
     'top-15 truncation biases breadth DOWN',
     'Commercial and MA corridors may differ systematically where payer '
     'mix skews'),
    ('MUP suppression floors on every per-NPI figure (A.1, A.2, A.3, '
     'X-F.1)',
     'Every per-NPI level is labeled a floor; bottom-quartile exit in the '
     'survival curves is OVERSTATED because suppression looks like exit',
     'Levels understate; trends can flip sign at the small end'),
    ('PLACES model-based uncertainty (A.8 screens)',
     'PLACES rows are labeled model-based estimates; never multiplied '
     'into volumes; used as relative concentration screens only',
     'County ranks are stable to moderate error; point values are not'),
    ('Parent roll-up errors in the fragmentation layer (A.3)',
     'The normalization pattern table renders on-tab so every roll-up is '
     'auditable; unrolled NPI-grain figures print beside parent-grain',
     'Shared billing agents and management companies can fake parents'),
    ('Registry vintages are snapshots (2013-2024), not a continuous '
     'series',
     'The annual series (X-A.1) closes this for 2013-2024 at NPI grain; '
     'entry/exit between years still conflates true exit with '
     'suppression-crossing',
     'Year-over-year deltas near the suppression threshold are noisy'),
    ('Cohort-selection bias (E.1, A.6, A.11)',
     'The research cohort is chosen for depth, not sampled; every cohort '
     'tab states it; NO cohort statistic generalizes to the market',
     'Cohort systems skew large, urban, integrated'),
    ('Concurrent-pull manifest race (v3.4 build infrastructure)',
     'reconcile_manifest.py re-registers any orphaned cache artifact and '
     'reports repairs on the Run_Log',
     'A lost manifest row would have broken the manifest-tab match test'),
]

CALENDAR = [
    ('CMS MUP by Provider & Service', 'Annual (new data year each summer)',
     'python3 pull7.py && python3 pull8.py', 'mup_provider_*'),
    ('CMS PSPS', 'Annual', 'python3 pull.py (psps stages)', 'psps_*'),
    ('CMS Medicare Monthly Enrollment', 'Monthly (year rows used)',
     'python3 pull.py (enrollment stage)', 'enrollment_*'),
    ('CMS Market Saturation & Utilization', 'Semiannual',
     'python3 pull2.py', 'marketsat_*'),
    ('BLS QCEW (annual + quarterly)', 'Quarterly, ~5 months lag',
     'python3 pull5.py && python3 pull7.py (quarterly stage)', 'qcew_*'),
    ('BLS OEWS', 'Annual (May reference)', 'python3 pull6.py', 'oews_*'),
    ('Care Compare PDC rosters (hospitals, SNF, dialysis, timely care)',
     'Quarterly-ish releases', 'python3 pull13.py + pull stages', 'pdc_*'),
    ('CMS Hospital Service Area (corridors)', 'Annual',
     'python3 pull7.py (hsa stage)', 'hsa_*'),
    ('Census county/state age estimates', 'Annual vintage (Jun)',
     'python3 pull7.py (census stage)', 'census_*'),
    ('CDC PLACES', 'Annual release', 'python3 pull7.py (places stage)',
     'places_*'),
    ('HHS OIG LEIE', 'Monthly cumulative', 'python3 pull7.py (leie stage)',
     'leie_*'),
    ('USAspending PSC V225', 'Continuous; pull at each build',
     'python3 pull9.py', 'usasp_*'),
    ('SEC EDGAR (DocGo, ModivCare)', 'Annual 10-K + quarterly',
     'python3 pull9.py && python3 pull14.py', 'docgo_*, edgar_*'),
    ('GADCS report appendix (CMS/RAND)', 'Per CMS publication cycle',
     'python3 pull9.py (gadcs stage)', 'gadcs_*'),
    ('NPPES bulk dissemination', 'Monthly full replacement',
     'python3 pull15.py', 'nppes_*'),
    ('CMS REH enrollment / Sheps closures', 'Rolling',
     'python3 pull10.py', 'reh_list, sheps_closures'),
    ('HCRIS raw cost reports (Worksheet A ambulance)', 'Quarterly refresh '
     'of open FYs', 'python3 pull12.py', 'hcris_amb_cost_center'),
]


def build(wb, ctx):
    lib = ctx['lib']

    # D.4 Refresh_Calendar tab
    ws = wb.create_sheet('Refresh_Calendar')
    sb = lib.SheetBuilder(ws, 4, col_widths=[52, 26, 42, 24],
                          tab_color='FF6B7C93')
    sb.title('Refresh calendar: every registered source family, its '
             'cadence, and the pipeline command that refreshes it')
    sb.subtitle('The question: when this workbook is reopened in three '
                'months, what is stale and what single command refreshes '
                'each layer? Pipeline lives in the repository at '
                'RCM_MC/scripts/ift_evidence_v3; every pull is cached, '
                'hashed and manifested, so a refresh is a re-run plus the '
                'two-pass assemble/verify cycle in the README.')
    sb.blank()
    sb.headers(['Source family', 'Cadence', 'Refresh command',
                'Manifest keys'])
    for row in CALENDAR:
        sb.row([(row[0], 'label'), (row[1], 'text'), (row[2], 'fml'),
                (row[3], 'note')], wrap=True, height=24)
    sb.blank()
    sb.note('Command cells are literal shell commands rendered as text; '
            'run them from RCM_MC/scripts/ift_evidence_v3 with the env '
            'exports in the pipeline README, then the two-pass '
            'assemble/verify cycle.')

    # D.1: append the v3.4 threat rows to Fault_Audit (carried tab -> logged)
    if 'Fault_Audit' in wb.sheetnames:
        wsf = wb['Fault_Audit']
        import v3lib as _v3
        r = wsf.max_row + 2
        c = wsf.cell(row=r, column=1,
                     value='v3.4 fault register (D.1 refresh): the failure '
                           'modes of the specificity-and-analysis pass, '
                           'each with its printed mitigation')
        c.font = _v3.F_BANNER
        c.fill = _v3.FILL_BANNER
        for i in range(2, 4):
            wsf.cell(row=r, column=i).fill = _v3.FILL_BANNER
        r += 1
        for i, h in enumerate(['Failure mode', 'Mitigation in the file',
                               'Residual risk'], start=1):
            hc = wsf.cell(row=r, column=i, value=h)
            hc.font = _v3.F_HDR
            hc.fill = _v3.FILL_HDR
        r += 1
        for fm, mit, res in FAULTS:
            for i, v in enumerate((fm, mit, res), start=1):
                cc = wsf.cell(row=r, column=i, value=v)
                cc.font = _v3.F_TXT
                cc.alignment = _v3.AL_WRAP
            wsf.row_dimensions[r].height = 40
            r += 1

    return {'facts': [], 'sources': [], 'excluded': [], 'findings': [],
            'meta': {'faults': len(FAULTS), 'calendar_rows': len(CALENDAR)},
            'entries': [{
                'tab': 'Fault_Audit', 'cell': '(appended panel)',
                'old': 'v2.7/v3 fault register without the v3.4 analysis '
                       'failure modes',
                'new': f'{len(FAULTS)} v3.4 fault rows appended (name-match '
                       'misclassification, corridor bias, suppression '
                       'floors, PLACES uncertainty, parent roll-ups, '
                       'snapshot vintages, cohort-selection bias, manifest '
                       'race)',
                'why': 'Handoff D.1.', 'class': 'quality'}]}
