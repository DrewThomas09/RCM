"""B.3: the Medicaid ambulance rate card for the footprint states.

Six state Medicaid fee schedules pulled and verified against the actual
published file or portal extract on 11 Jul 2026 (medicaid_rates.json):
Nebraska 471-000-504 (July 2026 xlsx), Iowa MedicaidFeeSched portal C11.csv,
Kansas KMAP TXIX fee schedule files (7/1/2026 versions), Missouri MHD
Ambulance.xlsx (7/7/2026), Ohio OAC 5160-15-28 appendix (1/1/2024),
Wisconsin ForwardHealth ambulance max-fee report (rates of 7/1/2008).
Virginia is PARKED for dollar rates (broker-billed non-emergency ambulance;
verified in the DMAS Transportation manual) and carried as PENDING rows.

Comparison panel prices each state's rate against the CY2026 Medicare
national unadjusted base located by scanning Derived_Rate_Card for the
code labels (green links when found; blue AFS re-carry as fallback).
"""

SHEETS = [{'name': 'Medicaid_Rate_Card',
           'question': 'What does Medicaid actually pay for ground ambulance '
                       'in the footprint states, and how much scheduled '
                       'transport never touches these schedules?'}]

CODES = ['A0428', 'A0429', 'A0426', 'A0427', 'A0433', 'A0434', 'A0425']
DESC = {'A0428': 'BLS non-emergency', 'A0429': 'BLS emergency',
        'A0426': 'ALS1 non-emergency', 'A0427': 'ALS1 emergency',
        'A0433': 'ALS2', 'A0434': 'Specialty Care Transport',
        'A0425': 'Ground mileage'}
# CY2026 AFS fallback (blue re-carry) if Derived_Rate_Card scan fails:
AFS_RVU = {'A0428': 1.0, 'A0429': 1.6, 'A0426': 1.2, 'A0427': 1.9,
           'A0433': 2.75, 'A0434': 3.25}
AFS_CF, AFS_MILE = 284.56, 9.15

STATES = ['NE', 'IA', 'KS', 'MO', 'OH', 'WI']
SNAME = {'NE': 'Nebraska', 'IA': 'Iowa', 'KS': 'Kansas', 'MO': 'Missouri',
         'OH': 'Ohio', 'WI': 'Wisconsin', 'VA': 'Virginia'}

# rate, effective (as printed), in-row note  (None rate = not covered)
RATES = {
 'NE': {'A0425': (6.35, '07/01/2026', 'per statute mile'),
        'A0426': (387.24, '07/01/2026', 'flat ALS rate: A0426=A0427=A0433=A0434'),
        'A0427': (387.24, '07/01/2026', ''),
        'A0428': (154.89, '07/01/2026', 'schedule comment: includes bariatric transfers'),
        'A0429': (189.93, '07/01/2026', ''),
        'A0433': (387.24, '07/01/2026', ''),
        'A0434': (387.24, '07/01/2026', '')},
 'IA': {'A0425': (2.61, '07/01/2014', 'per statute mile'),
        'A0426': (101.60, '10/01/2015', ''),
        'A0427': (127.01, '10/01/2015', ''),
        'A0428': (84.67, '07/01/2014', 'lowest A0428 in the footprint'),
        'A0429': (114.30, '10/01/2015', ''),
        'A0433': (232.84, '05/01/2020', ''),
        'A0434': (232.84, '12/01/2020', 'same rate as ALS2')},
 'KS': {'A0425': (13.20, '07/01/2023', 'Ambulance rate-type file; legacy $3.00 '
                  'row (eff 07/01/2022) persists on the general schedule'),
        'A0426': (306.84, '07/01/2023', ''),
        'A0427': (485.83, '07/01/2023', ''),
        'A0428': (255.70, '07/01/2023', 'highest A0428 in the footprint '
                  '(SFY2024 rebase)'),
        'A0429': (409.12, '07/01/2023', ''),
        'A0433': (703.18, '07/01/2023', ''),
        'A0434': (831.03, '07/01/2023', '')},
 'MO': {'A0425': (7.04, '07/01/2024', 'per statute mile'),
        'A0426': (172.26, '07/01/2019', 'HH (hospital-to-hospital) modifier '
                  'ONLY; unmodified code noncovered'),
        'A0427': (474.75, '07/01/2024', ''),
        'A0428': (105.62, '07/01/2019', 'HH and HD (hospital-to-diagnostic) '
                  'contexts ONLY; unmodified code noncovered'),
        'A0429': (379.69, '07/01/2024', ''),
        'A0433': (215.20, '07/01/2019', ''),
        'A0434': (None, '07/01/2002', 'NONCOVERED under MO HealthNet FFS')},
 'OH': {'A0425': (5.05, '01/01/2024', 'per statute mile'),
        'A0426': (244.50, '01/01/2024', ''),
        'A0427': (289.75, '01/01/2024', ''),
        'A0428': (203.75, '01/01/2024', ''),
        'A0429': (244.00, '01/01/2024', ''),
        'A0433': (349.50, '01/01/2024', ''),
        'A0434': (413.00, '01/01/2024', '')},
 'WI': {'A0425': (5.56, '07/01/2008', 'GM multi-patient half-rate $2.78'),
        'A0426': (113.88, '07/01/2008', ''),
        'A0427': (180.31, '07/01/2008', ''),
        'A0428': (94.90, '07/01/2008', 'unchanged for 18 years'),
        'A0429': (151.84, '07/01/2008', ''),
        'A0433': (260.97, '07/01/2008', ''),
        'A0434': (308.42, '07/01/2008', '')},
}

META = {
 'NE': ('Nebraska DHHS fee schedule 471-000-504, Ambulance Services, '
        'July 1 2026 (xlsx). Schedule cover: rates carry NO increase - no '
        'rate-increase appropriations this state fiscal year.',
        'PA column blank on every ground code (no PA flag); policy 471 NAC 4.',
        'YES - Heritage Health MCO brokers (MTM for NE Total Care and '
        'Molina; ModivCare for UHC, MTM Health from 1 Jan 2026); DHHS staff '
        'arrange residual FFS NET under 471-000-503.',
        'No dialysis restriction printed on the ambulance schedule; '
        'scheduled dialysis rides route through the NET benefit.'),
 'IA': ('Iowa Medicaid fee schedule portal extract, provider type 11 '
        'AMBULANCE (C11.csv), accessed 11 Jul 2026; per-code effective '
        'dates 2014-2020, open-ended.',
        'No PA; non-emergency requires bed-confinement or equivalent '
        'necessity criteria (Ambulance Services Provider Manual Ch. III, '
        '1 Oct 2015).',
        'YES - NEMT broker Access2Care renamed MTM Health 18 Sep 2025 '
        '(IA Health Link MCOs); MTM administers FFS NEMT.',
        'Dialysis NEMT rides schedulable 90 days ahead; ambulance claim '
        'destination modifiers G/J are dialysis facilities.'),
 'KS': ('KMAP TXIX fee schedule files, 7/1/2026 versions '
        '(FeeSchedule_20260701_TXIX_AMB.txt / _DEF.txt); ambulance rates '
        'effective 7/1/2023 (SFY2024 rebase).',
        'No PA, but ALL nonemergent transports need a Medical Necessity '
        'form attached to the claim (KMAP manual).',
        'YES - KanCare is near-total managed care; NEMT via MCO broker '
        'ModivCare (taxi to stretcher van and ambulance).',
        'Dialysis named among critical services eligible for NEMT in the '
        'Kansas NEMT provider manual.'),
 'MO': ('MHD Ambulance.xlsx, file dated 7 Jul 2026 (provider files updated '
        '07/08/2026); rate effective dates 2019-2024 per row.',
        'PA = No on all covered rows; A0428 billable ONLY with HH or HD '
        'modifier (MHD hot tip).',
        'YES - statewide NEMT broker MTM (mydss.mo.gov/mhd/nemt).',
        'Dialysis runs are NOT billable as FFS A0428 (HH/HD only); '
        'scheduled dialysis travel is an MTM broker trip.'),
 'OH': ('Appendix to OAC rule 5160-15-28 (file dated 22 Dec 2023), rule '
        'effective 1 Jan 2024.',
        'No PA in rule; necessity per OAC 5160-15-23(B): EMT care, oxygen, '
        'or supervised restraint during transport, or qualifying '
        'hospital-to-hospital transfer.',
        'NO statewide broker - county CDJFS NET programs (5160-15-10) plus '
        'MCO rides; ambulance stays a direct ODM/MCO claim. GEMT '
        'supplemental for public EMS (5160-15-30).',
        'Rules retrieved are silent on dialysis transport.'),
 'WI': ('ForwardHealth AMBULANCE MAXIMUM ALLOWABLE FEE SCHEDULE, live '
        'portal report accessed 11 Jul 2026; every ground code effective '
        '07/01/2008.',
        'No code-level PA flag; non-emergency needs ALS/BLS care or supine '
        'transport, and manager-coordinated trips need a trip ID within '
        'two business days (Update 2014-32).',
        'YES - statewide NEMT manager (MTM Inc.; Veyo from 11/2021 until '
        'MTM acquisition). Manager-coordinated NEMT ambulance claims are '
        'paid by the manager, NOT ForwardHealth.',
        'Recurring dialysis rides are standing rides with the NEMT '
        'manager; stretcher vans sit on the separate SMV schedule.'),
}

URLS = {
 'NE': 'https://dhhs.ne.gov/Medicaid%20Practitioner%20Fee%20Schedules/'
       '471-000-504%20Ambulance%20-%20July%20%2726.xlsx',
 'IA': 'https://secureapp.dhs.state.ia.us/MedicaidFeeSched/C11.csv',
 'KS': 'https://portal.kmap-state-ks.us/PublicPage/ProviderPricing/'
       'FeeSchedules',
 'MO': 'https://apps.dss.mo.gov/fmsfeeschedules/dlfiles/Ambulance.xlsx',
 'OH': 'https://codes.ohio.gov/assets/laws/administrative-code/pdfs/5160/0/'
       '15/5160-15-28_PH_FF_A_APP1_20231222_0942.pdf',
 'WI': 'https://www.forwardhealth.wi.gov/WIPortal/Tab/42/icscontent/'
       'provider/maxfee/pdf/maxfee06_ambulance.pdf.spage',
 'VA': 'https://vamedicaid.dmas.virginia.gov/sites/default/files/2025-12/'
       'Transportation%20Chapter%205%20(updated%2012.5.25)_Final.pdf',
}


def _mc_refs(wb):
    """Scan Derived_Rate_Card for the code labels; return {code: '$D$13'}."""
    if 'Derived_Rate_Card' not in wb.sheetnames:
        return {}
    ws = wb['Derived_Rate_Card']
    refs = {}
    for row in ws.iter_rows(min_col=1, max_col=1):
        v = row[0].value
        if not isinstance(v, str):
            continue
        s = v.strip()
        if s in AFS_RVU and s not in refs:
            refs[s] = f'$D${row[0].row}'          # national unadjusted base
        elif s.startswith('A0425 CY2026 national') and 'A0425' not in refs:
            refs['A0425'] = f'$B${row[0].row}'    # mileage national rate
    return refs


def build(wb, ctx):
    lib = ctx['lib']
    accessed = ctx['accessed']
    facts, sources, excluded, findings = [], [], [], []

    mc = _mc_refs(wb)
    scan_ok = all(c in mc for c in CODES)

    sources += [
        {'key': 'ne_amb_fs', 'publisher': 'Nebraska DHHS Medicaid',
         'document': 'Nebraska Medicaid Fee Schedule, Ambulance Services, '
                     'July 1 2026 (471-000-504 Ambulance - July 26.xlsx)',
         'vintage': 'Effective 1 Jul 2026 (SFY2027, no increase per cover)',
         'locator': 'Rows 000A0425-000A0434, MEDICAID ALLOWABLE column',
         'supplies': 'NE ground ambulance FFS rates + PA flags',
         'url': URLS['NE'], 'tier': 'A', 'accessed': accessed,
         'powers': ['Medicaid_Rate_Card']},
        {'key': 'ia_amb_fs', 'publisher': 'Iowa HHS (Iowa Medicaid)',
         'document': 'Iowa Medicaid fee schedule portal, provider type 11 '
                     'AMBULANCE, file C11.csv (via the I-Accept gate on the '
                     'hhs.iowa.gov fee-schedules page)',
         'vintage': 'Live extract 11 Jul 2026; code rates eff 2014-2020',
         'locator': 'C11.csv rows A0425-A0436, Factor column',
         'supplies': 'IA ground ambulance FFS rates + effective dates',
         'url': URLS['IA'], 'tier': 'A', 'accessed': accessed,
         'powers': ['Medicaid_Rate_Card']},
        {'key': 'ks_kmap_fs', 'publisher': 'Kansas KMAP (KDHE)',
         'document': 'KMAP public fee schedules: FeeSchedule_20260701_TXIX_'
                     'AMB.txt.zip and FeeSchedule_20260701_TXIX_DEF.txt.zip',
         'vintage': 'Posted versions of 7/1/2026; rates eff 7/1/2023',
         'locator': 'Fixed-width rows A0425-A0434, MAX FEE column; retrieved '
                    'by replicating the portal AJAX flow (list POST then '
                    'DownloadFSFile in-session)',
         'supplies': 'KS ground ambulance FFS rates (TXIX)',
         'url': URLS['KS'], 'tier': 'A', 'accessed': accessed,
         'powers': ['Medicaid_Rate_Card']},
        {'key': 'mo_mhd_fs', 'publisher': 'Missouri DSS MO HealthNet',
         'document': 'MHD fee schedule download Ambulance.xlsx, file dated '
                     '7 Jul 2026 (provider files updated 07/08/2026)',
         'vintage': 'Monthly refresh; row effective dates 2019-2024',
         'locator': 'Rows A0425-A0434 with modifier context, Rate and PA '
                    'columns; A0428 HH/HD restriction per MHD hot tip',
         'supplies': 'MO ground ambulance FFS rates, coverage restrictions',
         'url': URLS['MO'], 'tier': 'A', 'accessed': accessed,
         'powers': ['Medicaid_Rate_Card']},
        {'key': 'oh_odm_fs', 'publisher': 'Ohio Dept of Medicaid (OAC)',
         'document': 'Appendix to OAC rule 5160-15-28 (Transportation: '
                     'payment), file 5160-15-28_PH_FF_A_APP1_20231222',
         'vintage': 'Rule and rates effective 1 Jan 2024',
         'locator': 'Appendix pp.1-2, ground ambulance rows A0425-A0434; '
                    'necessity criteria in rule 5160-15-23(B)',
         'supplies': 'OH ground ambulance FFS rates + payment rule',
         'url': URLS['OH'], 'tier': 'A', 'accessed': accessed,
         'powers': ['Medicaid_Rate_Card']},
        {'key': 'wi_maxfee_amb', 'publisher': 'Wisconsin DHS ForwardHealth',
         'document': 'AMBULANCE MAXIMUM ALLOWABLE FEE SCHEDULE (portal-'
                     'generated live report, maxfee06_ambulance.pdf)',
         'vintage': 'Report as in effect 11 Jul 2026; rates eff 7/1/2008',
         'locator': 'Provider type 25 rows A0425-A0436, MAX FEE column; '
                    'NEMT-manager routing per ForwardHealth Update 2014-32',
         'supplies': 'WI ambulance max fees + NEMT manager carve',
         'url': URLS['WI'], 'tier': 'A', 'accessed': accessed,
         'powers': ['Medicaid_Rate_Card']},
        {'key': 'va_dmas_manual', 'publisher': 'Virginia DMAS',
         'document': 'Transportation provider manual Chapter 5, revision '
                     '5 Dec 2025 (Transportation Chapter 5 Final.pdf)',
         'vintage': 'Rev 12/5/2025',
         'locator': 'FFS Non-Emergency Transportation Broker section: '
                    '"A0428 ... preauthorized and billed to the Non-'
                    'Emergency Medicaid Transportation Broker"',
         'supplies': 'VA broker carve of non-emergency ambulance (rates '
                     'PARKED: posted emergency PDF is 2009-2012 vintage)',
         'url': URLS['VA'], 'tier': 'A', 'accessed': accessed,
         'powers': ['Medicaid_Rate_Card']},
    ]

    ws = wb.create_sheet('Medicaid_Rate_Card')
    sb = lib.SheetBuilder(ws, 9, col_widths=[34, 13, 11, 11, 11, 11, 11, 11, 48],
                          tab_color='FF8C1D40')
    sb.title('Medicaid ground ambulance rate card - the footprint states')
    sb.subtitle('The question: what does each footprint state Medicaid FFS '
                'schedule actually pay for ground ambulance (A0425-A0434), '
                'and how much scheduled transport is carved out to NEMT '
                'brokers and never priced on these schedules? Sources: the '
                'six published state fee schedules named on each panel, each '
                'fetched and parsed on 11 Jul 2026; join key is the HCPCS '
                'code. Comparison prices each state against the CY2026 '
                'Medicare national unadjusted base on Derived_Rate_Card.')
    sb.note('DATA QUALITY: Medicaid FFS schedule rates ONLY - managed-care '
            'plans (KanCare, Heritage Health, IA Health Link, MO Managed '
            'Care, OH Next Gen, BadgerCare HMOs) negotiate their own rates, '
            'and broker-carve states route scheduled volume outside these '
            'schedules entirely, so the real price of scheduled transport is '
            'unobservable here. Effective dates differ by 18 years (WI '
            '7/1/2008 vs NE 7/1/2026): the cross-state comparison mixes '
            'vintages by construction. MO rates are context-restricted '
            '(A0428 HH/HD only); KS carries two conflicting A0425 rows.')
    sb.blank()

    cell = {}     # (state, code) -> rate cell 'C12'
    for st in STATES:
        eff, pa, brk, dia = META[st]
        sb.banner(f'Panel {chr(65 + STATES.index(st))}. {SNAME[st]} - '
                  f'{eff.split("(")[0].strip()[:80]}')
        sb.headers(['HCPCS', 'Service level', 'Rate $', 'Unit',
                    'Rate eff.', '', '', '', 'In-row note'])
        for code in CODES:
            rate, reff, note = RATES[st][code]
            r = sb.r + 1
            if rate is None:
                sb.row([(code, 'text'), (DESC[code], 'text'),
                        ('NONCOVERED', 'src'), ('base', 'text'),
                        (reff, 'src'), None, None, None, (note, 'note')])
            else:
                fmt = lib.FMT_USD2
                sb.row([(code, 'text'), (DESC[code], 'text'),
                        (rate, 'src', fmt),
                        ('per mile' if code == 'A0425' else 'base', 'text'),
                        (reff, 'src'), None, None, None,
                        (note, 'note') if note else None])
                cell[(st, code)] = f'C{r}'
        sb.row([('Source file', 'label'), None, None, None, None, None, None,
                None, (URLS[st], 'note')])
        sb.row([('PA rule', 'label'), (pa, 'note')], height=22)
        sb.row([('Broker carve', 'label'), (brk, 'note')], height=22)
        sb.row([('Dialysis policy', 'label'), (dia, 'note')], height=22)
        sb.blank()

    # ── Virginia: parked ─────────────────────────────────────────────
    sb.banner('Panel G. Virginia (extension state) - rates PARKED, carve '
              'verified')
    sb.headers(['HCPCS', 'Service level', 'Rate $', '', '', '', '', '',
                'Why parked / what fills it'])
    sb.row([('A0428', 'text'), (DESC['A0428'], 'text'), ('PENDING', 'note'),
            None, None, None, None, None,
            ('Not payable on a public FFS schedule: DMAS Transportation '
             'manual Ch.5 (rev 12/5/2025) requires A0428 to be preauthorized '
             'and billed to the FFS NEMT broker. Filler dataset: DMAS '
             'procedure fee file search portal (interactive per-code '
             'lookup).', 'note')], height=30)
    sb.row([('A0427/A0429/A0433', 'text'), ('Emergency codes', 'text'),
            ('PENDING', 'note'), None, None, None, None, None,
            ('Posted PDF on dmas.virginia.gov is the Nov 2009-Jun 2012 '
             'sliding-scale vintage (payment caps $75-$150 by mileage band); '
             'current rates sit in the DMAS procedure fee file portal.',
             'note')], height=30)
    sb.row([('Source (verified)', 'label'), None, None, None, None, None,
            None, None, (URLS['VA'], 'note')])
    sb.blank()

    # ── Comparison panel ─────────────────────────────────────────────
    sb.banner('Panel H. Comparison - each state as a multiple of the CY2026 '
              'Medicare national unadjusted base (live formulas)')
    if scan_ok:
        sb.note('Medicare column is a GREEN link to Derived_Rate_Card '
                '(located by scanning that tab for the code labels: base '
                'codes column D, mileage cell B23).')
    else:
        sb.note('Derived_Rate_Card scan did NOT locate all code cells; the '
                'Medicare column re-carries the CY2026 AFS national base '
                '(RVU x $284.56 CF; mileage $9.15) as blue, per the CMS '
                'CY2026 Ambulance Fee Schedule public use file.')
    hdr_r = sb.r + 1
    sb.headers(['HCPCS (service)', 'Medicare CY26 $', 'NE', 'IA', 'KS', 'MO',
                'OH', 'WI', 'Confound printed with the ratio'])
    cmp_row = {}
    for code in CODES:
        r = sb.r + 1
        cmp_row[code] = r
        if scan_ok:
            mc_cell = (f"='Derived_Rate_Card'!{mc[code]}", 'link',
                       lib.FMT_USD2)
        else:
            val = AFS_MILE if code == 'A0425' else AFS_RVU[code] * AFS_CF
            mc_cell = (round(val, 2), 'src', lib.FMT_USD2)
        row = [(f'{code} ({DESC[code]})', 'text'), mc_cell]
        for st in STATES:
            ref = cell.get((st, code))
            if ref is None:
                row.append(('n/a', 'note'))
            else:
                row.append((f'={ref}/$B${r}', 'fml', lib.FMT_X))
        conf = ('Vintages differ (WI 2008, IA 2014-20, KS/OH 2023-24, MO '
                '2019-24, NE 2026); MO is HH/HD-restricted'
                if code == 'A0428' else
                'MO NONCOVERED - no ratio' if code == 'A0434' else
                'KS mileage from the ambulance rate-type file, not the '
                'legacy $3.00 row' if code == 'A0425' else
                'MO rate is HH-modifier context' if code == 'A0426' else
                'Same-code comparison; state schedules do not adjust for '
                'geography the way Medicare does')
        row.append((conf, 'note'))
        sb.row(row)
    r_min = sb.r + 1
    sb.row([('Footprint A0428 range - LOWEST multiple (Iowa)', 'label'),
            None, (f'=MIN(C{cmp_row["A0428"]}:H{cmp_row["A0428"]})', 'fml',
                   lib.FMT_X), None, None, None, None, None,
            ('min over the six live A0428 ratios', 'note')])
    r_max = sb.r + 1
    sb.row([('Footprint A0428 range - HIGHEST multiple (Kansas)', 'label'),
            None, (f'=MAX(C{cmp_row["A0428"]}:H{cmp_row["A0428"]})', 'fml',
                   lib.FMT_X), None, None, None, None, None,
            ('max over the six live A0428 ratios', 'note')])
    sb.row([('Dispersion: highest / lowest A0428 rate', 'label'), None,
            (f'=C{r_max}/C{r_min}', 'fml', lib.FMT_X), None, None, None,
            None, None, ('KS pays 3.0x what IA pays for the same code',
                         'note')])
    lib.add_chart(ws, f'K{hdr_r}',
                  'Medicaid A0428 as a multiple of Medicare CY2026',
                  f"'Medicaid_Rate_Card'!$C${hdr_r}:$H${hdr_r}",
                  [('A0428 multiple',
                    f"'Medicaid_Rate_Card'!$C${cmp_row['A0428']}:"
                    f"$H${cmp_row['A0428']}")],
                  kind='bar', y_fmt='0.00"x"')
    sb.blank()

    # ── Broker-carve summary ─────────────────────────────────────────
    sb.banner('Panel I. Broker carve-out summary - who actually buys '
              'scheduled transport')
    sb.headers(['State', 'Carve?', 'Broker / manager', '', '', '', '', '',
                'What is carved'])
    b0 = sb.r + 1
    carves = [
        ('NE', 'YES', 'MTM / ModivCare (MTM Health from 1/1/26)',
         'NEMT via Heritage Health MCO brokers; FFS NET by DHHS staff'),
        ('IA', 'YES', 'MTM Health (was Access2Care to 9/18/25)',
         'NEMT for MCO and FFS members; ambulance stays FFS-billable'),
        ('KS', 'YES', 'ModivCare (KanCare MCOs)',
         'NEMT incl. stretcher van and NEMT ambulance coordination'),
        ('MO', 'YES', 'MTM (statewide)',
         'All scheduled NEMT; FFS ambulance only in HH/HD contexts'),
        ('OH', 'NO', 'County CDJFS NET + MCO vendors',
         'No statewide broker; ambulance is a direct ODM/MCO claim'),
        ('WI', 'YES', 'MTM Inc. (NEMT manager; Veyo 2021-22)',
         'Manager-coordinated NEMT ambulance is paid by the MANAGER, '
         'not ForwardHealth'),
    ]
    for st, y, who, what in carves:
        sb.row([(SNAME[st], 'text'), (y, 'src'), (who, 'src'), None, None,
                None, None, None, (what, 'note')])
    r_cnt = sb.r + 1
    sb.row([('Broker-carve states among the six footprint states', 'label'),
            (f'=COUNTIF(B{b0}:B{b0 + 5},"YES")', 'fml', lib.FMT_INT),
            None, None, None, None, None, None,
            ('live count over the column above', 'note')])
    sb.row([('Memo - Virginia (extension state)', 'text'), ('YES', 'src'),
            ('DMAS FFS NEMT broker', 'src'), None, None, None, None, None,
            ('Broker pays FFS NON-EMERGENCY AMBULANCE itself: no public '
             'FFS price for scheduled ambulance exists', 'note')])
    sb.blank()

    sb.banner('Read panel')
    sb.prose('What is measured: six published state Medicaid FFS ambulance '
             'schedules, fetched and parsed from the primary file or portal '
             'on 11 Jul 2026. The BLS non-emergency base (A0428), the '
             'workhorse code of scheduled interfacility transport, pays '
             '$84.67 (IA, unchanged since 2014) to $255.70 (KS, 2023 '
             'rebase) - roughly 0.30x to 0.90x the CY2026 Medicare national '
             'base, with WI frozen at $94.90 since 2008. Five of the six '
             'states route scheduled NEMT through a broker or manager (MTM, '
             'MTM Health, ModivCare), and in WI the manager, not '
             'ForwardHealth, pays coordinated NEMT ambulance claims; OH '
             'runs county NET instead. Missouri will not pay A0428 at all '
             'outside hospital-to-hospital or hospital-to-diagnostic '
             'contexts, and will not pay SCT (A0434) at all. What is NOT '
             'measured: managed-care negotiated rates, broker-paid trip '
             'prices, and GEMT supplemental payments - the real price of '
             'most scheduled Medicaid transport is set inside those '
             'channels and is not public.')

    A = 'Medicaid FFS ambulance fee schedule'
    fact_rows = [
        ('NE', 154.89, '1 Jul 2026', 'ne_amb_fs',
         '471-000-504 xlsx row 000A0428, MEDICAID ALLOWABLE',
         'Schedule cover states no increase for SFY2027'),
        ('IA', 84.67, 'eff 1 Jul 2014, current 11 Jul 2026', 'ia_amb_fs',
         'C11.csv row A0428, Factor column',
         'Lowest in footprint; unchanged 12 years'),
        ('KS', 255.70, 'eff 1 Jul 2023, posted 7/1/2026', 'ks_kmap_fs',
         'FeeSchedule_20260701_TXIX_DEF.txt row A0428 MAX FEE',
         'Highest in footprint; SFY2024 rebase'),
        ('MO', 105.62, 'eff 1 Jul 2019, file 7 Jul 2026', 'mo_mhd_fs',
         'Ambulance.xlsx rows A0428 HH / A0428 HD',
         'Payable ONLY in HH/HD contexts; base code noncovered'),
        ('OH', 203.75, '1 Jan 2024', 'oh_odm_fs',
         'OAC 5160-15-28 appendix, row A0428',
         '2024 rebase; GEMT supplemental tops up public providers'),
        ('WI', 94.90, 'eff 1 Jul 2008, report 11 Jul 2026', 'wi_maxfee_amb',
         'maxfee06_ambulance.pdf row A0428 MAX FEE',
         'Unchanged 18 years; manager-coordinated NEMT paid off-schedule'),
    ]
    for st, val, eff, key, loc, xc in fact_rows:
        facts.append({'metric': f'{SNAME[st]} {A}: A0428 BLS non-emergency '
                                f'base rate ({eff})',
                      'year': 2026, 'value': val, 'unit': 'USD per transport',
                      'basis': 'GOV', 'tier': 'A', 'source_keys': [key],
                      'locator': loc, 'lives_on': 'Medicaid_Rate_Card',
                      'cross_check': xc})
    facts += [
        {'metric': 'Lowest footprint Medicaid A0428 rate as a multiple of '
                   'the CY2026 Medicare national base (Iowa)',
         'year': 2026, 'value': 0.2975, 'unit': 'x Medicare',
         'basis': 'DERIVED', 'tier': 'A', 'source_keys': ['ia_amb_fs'],
         'locator': 'Medicaid_Rate_Card Panel H, MIN over the A0428 row; '
                    '84.67 / 284.56',
         'lives_on': 'Medicaid_Rate_Card',
         'cross_check': 'Vintage confound printed in-row: IA rate is a 2014 '
                        'rate against a 2026 Medicare base'},
        {'metric': 'Highest footprint Medicaid A0428 rate as a multiple of '
                   'the CY2026 Medicare national base (Kansas)',
         'year': 2026, 'value': 0.8986, 'unit': 'x Medicare',
         'basis': 'DERIVED', 'tier': 'A', 'source_keys': ['ks_kmap_fs'],
         'locator': 'Medicaid_Rate_Card Panel H, MAX over the A0428 row; '
                    '255.70 / 284.56',
         'lives_on': 'Medicaid_Rate_Card',
         'cross_check': 'KS 2023 rebase; still below Medicare parity'},
        {'metric': 'Footprint states routing scheduled NEMT through a '
                   'broker or transportation manager',
         'year': 2026, 'value': 5, 'unit': 'of 6 states',
         'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['ne_amb_fs', 'ia_amb_fs', 'ks_kmap_fs', 'mo_mhd_fs',
                         'oh_odm_fs', 'wi_maxfee_amb'],
         'locator': 'Medicaid_Rate_Card Panel I, COUNTIF over the carve '
                    'column (OH is the exception: county NET)',
         'lives_on': 'Medicaid_Rate_Card',
         'cross_check': 'VA (extension) goes further: the broker pays FFS '
                        'non-emergency ambulance itself'},
    ]

    findings.append({
        'id_hint': 75,
        'finding': 'The Medicaid price floor for scheduled ambulance '
                   'transport is low and wildly dispersed: the six footprint '
                   'FFS schedules pay $84.67 (IA, set 2014) to $255.70 (KS, '
                   'set 2023) for the same A0428 BLS non-emergency transport '
                   '- about 0.30x to 0.90x the CY2026 Medicare national base '
                   'and a 3.0x spread between neighbouring states - with WI '
                   'frozen since 2008 and NE explicitly flat for SFY2027. '
                   'Five of the six states carve scheduled NEMT to brokers '
                   '(MTM, MTM Health, ModivCare), so the schedule price is '
                   'not even the paid price for most scheduled volume.',
        'numbers': f"='Medicaid_Rate_Card'!C{r_min}",
        'sources': 'ne_amb_fs; ia_amb_fs; ks_kmap_fs; mo_mhd_fs; oh_odm_fs; '
                   'wi_maxfee_amb; va_dmas_manual',
        'confidence': 'High on the schedule values (each read from the '
                      'primary file); the multiples mix rate vintages by '
                      'construction',
        'guardrail': 'FFS schedule rates are NOT what managed-care plans '
                     'pay, and broker-carve states hide the real '
                     'scheduled-transport price inside broker and MCO '
                     'contracts; these floors bound the public price, not '
                     'the market price. MO A0428 exists only in HH/HD '
                     'contexts and MO pays nothing for SCT.'})

    return {'facts': facts, 'sources': sources, 'excluded': excluded,
            'findings': findings,
            'meta': {'states_landed': STATES, 'states_parked': ['VA'],
                     'medicare_scan': 'green links' if scan_ok
                                      else 'blue AFS re-carry',
                     'research_record': 'medicaid_rates.json'}}
