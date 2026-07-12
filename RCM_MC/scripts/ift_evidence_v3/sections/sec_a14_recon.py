"""A.14 + A.15: two tabs.

Universe_Reconciliation - the single answer to 'why do the numbers
differ': one row per national volume universe at the latest common data
year (2024), each value a GREEN live link into its home tab, with the
unit and population scope printed IN-ROW and live wedge subtraction
between adjacent rows, the wedge driver named per row.

LEIE_Read_Panel - the OIG exclusion list read, from the carried
LEIE_Ambulance_Exclusions tab cells: by state, by exclusion type,
individuals vs business entities (business-name-blank heuristic),
footprint slice, decade spread. Integrity context ONLY - never a sizing
input.

Footprint states NE IA KS MO OH WI VA MN IN KY, provisional pending E.5.
"""

SHEETS = [
    {'name': 'Universe_Reconciliation',
     'question': 'Why do the five national ambulance volume universes '
                 'print five different numbers for the same year?'},
    {'name': 'LEIE_Read_Panel',
     'question': 'What does the federal exclusion list actually say '
                 'about the ambulance industry - and what may it never '
                 'be used for?'},
]

FP = ['NE', 'IA', 'KS', 'MO', 'OH', 'WI', 'VA', 'MN', 'IN', 'KY']
BASE = ['A0426', 'A0427', 'A0428', 'A0429', 'A0433', 'A0434']
LEIE = 'LEIE_Ambulance_Exclusions'
TYPE_LABEL = {
    '1128a1': 'Program-related crime (mandatory)',
    '1128a2': 'Patient abuse or neglect (mandatory)',
    '1128a3': 'Felony health-care fraud (mandatory)',
    '1128a4': 'Felony controlled-substance conviction (mandatory)',
    '1128b1': 'Misdemeanor health-care fraud (permissive)',
    '1128b4': 'License revocation or suspension (permissive)',
    '1128b5': 'Exclusion or suspension under a federal or state program',
    '1128b7': 'Fraud, kickbacks or other prohibited activity (permissive)',
    '1128b8': 'Entity controlled by a sanctioned individual',
    '1128b11': 'Failure to supply payment information',
    'BRCH SA': 'Breach of settlement agreement',
    'BRCH CIA': 'Breach of corporate integrity agreement',
}


def _f(v):
    try:
        return float(str(v).replace(',', ''))
    except (TypeError, ValueError):
        return None


def _scan_recon_rows(wb):
    """Locate the exact carried cells for each universe at data year 2024."""
    out = {}
    # PSPS_Denial_Series: 2024 ground base rows, submitted services col D
    ws = wb['PSPS_Denial_Series']
    rows, val = [], 0.0
    for r, row in enumerate(ws.iter_rows(min_row=6, max_row=140, max_col=5),
                            6):
        if row[0].value == 2024 and row[1].value in BASE:
            rows.append(r)
            val += _f(row[3].value) or 0
    out['psps'] = {'rows': rows, 'val': val}
    # MUP_Ambulance_National 2024 base rows, services col F
    ws = wb['MUP_Ambulance_National']
    rows, val = [], 0.0
    for r, row in enumerate(ws.iter_rows(min_row=6, max_row=150, max_col=6),
                            6):
        if row[0].value == 2024 and row[1].value in BASE:
            rows.append(r)
            val += _f(row[5].value) or 0
    out['mup_nat'] = {'rows': rows, 'val': val}
    # MUP_Ambulance_State Panel A (2024) block bounds, services col G
    ws = wb['MUP_Ambulance_State']
    lo = hi = None
    val = 0.0
    for r, row in enumerate(ws.iter_rows(min_row=6, max_row=510, max_col=7),
                            6):
        if row[2].value in BASE and isinstance(row[6].value, (int, float)):
            lo = lo or r
            hi = r
            val += row[6].value
    out['mup_state'] = {'lo': lo, 'hi': hi, 'val': val}
    return out


def build(wb, ctx):
    lib = ctx['lib']
    facts, sources, excluded, findings = [], [], [], []
    loc = _scan_recon_rows(wb)

    # scan the carried LEIE tab for the fact values (the tab cells stay
    # live formulas; these are the registered numbers)
    ws_l = wb[LEIE]
    n_tot = n_biz = n_fp = n_fp_biz = 0
    st_count = {}
    for row in ws_l.iter_rows(min_row=5, max_row=570, max_col=9):
        bn, st, etype = row[2].value, row[6].value, row[7].value
        if etype is None and st is None:
            continue
        n_tot += 1
        st_count[st] = st_count.get(st, 0) + 1
        isbiz = bool(bn and str(bn).strip())
        if isbiz:
            n_biz += 1
        if st in FP:
            n_fp += 1
            if isbiz:
                n_fp_biz += 1

    sources += [
        {'key': 'a14_universes', 'publisher': 'NHTSA/NEMSIS; MedPAC; CMS',
         'document': 'Cross-universe map of the five carried national '
                     'ambulance volume series: NEMSIS activations '
                     '(EMS_Transports), MedPAC mandated-report transports '
                     '(MedPAC_2026_Mandated), PSPS submitted services '
                     '(PSPS_Denial_Series), MUP final-action services, '
                     'national and state (MUP_Ambulance_National / '
                     '_State), and the provider-registry sum '
                     '(MUP_Providers_2024)',
         'vintage': 'Data year 2024 (latest common year)',
         'locator': 'Every value on Universe_Reconciliation is a green '
                    'live link into the named home tab; home-tab row '
                    'references printed per row',
         'supplies': 'The reconciliation ladder and wedge arithmetic',
         'url': 'https://data.cms.gov/; https://nemsis.org/; '
                'https://www.medpac.gov/',
         'tier': 'A', 'accessed': ctx['accessed'],
         'powers': ['Universe_Reconciliation']},
        {'key': 'a15_leie', 'publisher': 'HHS OIG',
         'document': 'List of Excluded Individuals and Entities (LEIE), '
                     'ambulance-tagged rows as carried on '
                     'LEIE_Ambulance_Exclusions',
         'vintage': 'Cumulative, exclusion dates 1985-2025, as carried',
         'locator': 'LEIE_Ambulance_Exclusions rows 5-570; state col G, '
                    'type col H, business name col C, date col I',
         'supplies': 'Exclusion counts by state, statutory ground, '
                     'entity type and decade',
         'url': 'https://oig.hhs.gov/exclusions/exclusions_list.asp',
         'tier': 'A', 'accessed': ctx['accessed'],
         'powers': ['LEIE_Read_Panel']},
    ]

    # =========================================== Universe_Reconciliation =
    ws = wb.create_sheet('Universe_Reconciliation')
    sb = lib.SheetBuilder(ws, 8,
                          col_widths=[46, 17, 24, 30, 24, 17, 13, 56],
                          tab_color='FF7A5195')
    sb.title('Universe reconciliation: why the national ambulance numbers '
             'differ, in one ladder')
    sb.subtitle('The question: five public universes print five different '
                'national ambulance volumes for the same data year (2024, '
                'the latest common year) - which number is right? ALL of '
                'them, each for its own object. One row per universe, the '
                'value green-linked live into its home tab, the unit and '
                'population printed in the same row, and the wedge to the '
                'next row computed live with its driver named. Sources: '
                'NEMSIS (EMS_Transports), MedPAC June 2026 mandated '
                'report (MedPAC_2026_Mandated), PSPS carrier file '
                '(PSPS_Denial_Series), MUP final-action national / state '
                '(MUP_Ambulance_National, MUP_Ambulance_State), MUP '
                'provider registry (MUP_Providers_2024).')
    sb.note('DATA QUALITY: the rows deliberately MIX units (activations, '
            'transports, submitted services, final-action services) and '
            'populations (all-payer vs Medicare FFS; carrier-billed vs '
            'carrier+institutional) - that mixing is the SUBJECT of the '
            'tab, quarantined here and nowhere else. Never blend levels '
            'across rows into any single market number; house rule: PSPS '
            'submitted and MUP final-action stay separate everywhere '
            'else in the workbook. Ground base codes = A0426-A0429, '
            'A0433, A0434 (air and mileage excluded).', height=34)
    sb.blank()

    sb.banner('The ladder: one row per universe, data year 2024, wedge '
              'to the next row live')
    sb.headers(['Universe (home tab)', 'Value 2024 (live link)', 'Unit',
                'Population scope', 'Wedge to next row (live)',
                'Wedge share of this row (live)', '',
                'Wedge driver (why the next row is smaller)'])
    r0 = sb.r + 1
    psps_ref = ('=' + '+'.join(f"'PSPS_Denial_Series'!D{r}"
                               for r in loc['psps']['rows']))
    mupn_ref = ('=' + '+'.join(f"'MUP_Ambulance_National'!F{r}"
                               for r in loc['mup_nat']['rows']))
    slo, shi = loc['mup_state']['lo'], loc['mup_state']['hi']
    base_arr = '{' + ','.join(f'"{c}"' for c in BASE) + '}'
    mups_ref = (f"=SUMPRODUCT(ISNUMBER(MATCH('MUP_Ambulance_State'"
                f"!$C${slo}:$C${shi},{base_arr},0))"
                f"*'MUP_Ambulance_State'!$G${slo}:$G${shi})")
    mupp_ref = ('=' + '+'.join(
        f"SUMIF('MUP_Providers_2024'!$F$5:$F$30831,\"{c}\","
        f"'MUP_Providers_2024'!$J$5:$J$30831)" for c in BASE))
    ladder = [
        ('NEMSIS EMS activations (EMS_Transports)',
         "='EMS_Transports'!G6", 'Activations (dispatches; includes '
         'non-transport runs)', 'All-payer, all service types, 54 '
         'reporting states/territories',
         'Payer scope collapses (Medicare FFS only), non-transport and '
         'non-billable runs drop out, activations become billed '
         'transports'),
        ('MedPAC reported Medicare FFS transports '
         '(MedPAC_2026_Mandated)', "='MedPAC_2026_Mandated'!B7",
         'Transports (rounded by MedPAC)', 'Medicare FFS, '
         'carrier-billed AND institutionally billed (hospital-owned '
         'ambulances on Part A/B institutional claims)',
         'Institutional (provider-billed) transports drop out - the '
         'PSPS file is carrier claims only - plus MedPAC rounding'),
        ('PSPS submitted ground base services (PSPS_Denial_Series)',
         psps_ref, 'SUBMITTED services, ground base codes (includes '
         'later-denied lines)', 'Medicare FFS, carrier-billed only',
         'About 1.07M submitted services are denied or do not reach '
         'final action: submitted becomes final-action allowed'),
        ('MUP final-action national, ground base '
         '(MUP_Ambulance_National)', mupn_ref,
         'FINAL-ACTION services, ground base codes',
         'Medicare FFS, carrier-billed, after claim adjudication',
         'State-grain publication suppresses sub-11 state-code cells - '
         'a near-zero wedge at this grain'),
        ('CMS state-file sum, ground base (MUP_Ambulance_State)',
         mups_ref, 'FINAL-ACTION services, summed over the 2024 '
         'state-by-code rows', 'Medicare FFS, carrier-billed - the same '
         'universe as the national row, cut by state',
         'Provider-grain suppression bites harder: every NPI-code row '
         'under 11 beneficiaries vanishes from the registry'),
        ('Provider-registry sum, ground base (MUP_Providers_2024)',
         mupp_ref, 'FINAL-ACTION services, summed over ~30,800 '
         'NPI-code rows (live SUMIF)', 'Medicare FFS, carrier-billed, '
         'provider grain (suppressed rows missing)', None),
    ]
    for i, (name, ref, unit, pop, driver) in enumerate(ladder):
        rn = r0 + i
        wedge = (f'=B{rn}-B{rn + 1}' if i < len(ladder) - 1 else None)
        share = (f'=IF(B{rn}=0,"n/a",E{rn}/B{rn})'
                 if i < len(ladder) - 1 else None)
        sb.row([(name, 'label'), (ref, 'link', lib.FMT_INT),
                (unit, 'text'), (pop, 'text'),
                (wedge, 'fml', lib.FMT_INT) if wedge else None,
                (share, 'fml', lib.FMT_PCT1) if share else None,
                None,
                (driver, 'note') if driver else
                ('floor of the ladder: the finest public grain', 'note')],
               wrap=True, height=40)
    rl = r0 + len(ladder) - 1
    sb.blank()
    sb.note('Wedge arithmetic is live: each E cell subtracts the row '
            'below from the row above, so a re-based workbook re-prints '
            'the ladder without touching this tab. The NEMSIS-to-MedPAC '
            'wedge (about 49M) is the all-payer and non-transport mass; '
            'the MedPAC-to-PSPS wedge (about 0.6M) is institutional '
            'billing plus rounding; the PSPS-to-MUP wedge (about 1.05M) '
            'is denials and adjudication; the two MUP suppression wedges '
            'are near 0 and about 95K.', height=34)
    sb.blank()

    sb.banner('Read panel')
    sb.prose('The five-universe rule: there is no single national '
             'ambulance volume, and every apparent contradiction in this '
             'workbook resolves to a scope line. 60.3M NEMSIS activations '
             'hold all payers and every dispatch; 11.3M is MedPAC\'s '
             'Medicare FFS transport count including hospital-billed '
             'ambulances; 10.7M is what carriers saw SUBMITTED on ground '
             'base codes; 9.64M is what survived to final action; and '
             '9.54M is what the provider-grain registry can still show '
             'after sub-11 suppression. Quote a number only with its '
             'universe attached. The wedges themselves are evidence: the '
             'denial wedge is the eligibility firewall at work, and the '
             'suppression wedge is why every provider-grain read in this '
             'workbook is a floor.')

    findings.append({
        'id_hint': 72,
        'finding': 'The five-universe rule is now arithmetic, not '
                   'doctrine: for data year 2024 the workbook carries '
                   '60.3M NEMSIS activations (all-payer dispatches), '
                   '11.3M MedPAC Medicare FFS transports (carrier plus '
                   'institutional), 10.7M PSPS submitted ground base '
                   'services (carrier only), 9.64M MUP final-action '
                   'services, and a 9.54M provider-registry floor - and '
                   'every adjacent wedge is computed live with its '
                   'driver named (payer scope, institutional billing, '
                   'denials, suppression). Any market number quoted '
                   'without its universe is wrong by construction.',
        'numbers': "='Universe_Reconciliation'!E" + str(r0),
        'sources': 'a14_universes',
        'confidence': 'High; every value is a live link into a carried '
                      'primary tab',
        'guardrail': 'The ladder mixes units and populations ON PURPOSE '
                     'and only here: never blend rows into one market '
                     'size, never mix PSPS submitted with MUP '
                     'final-action outside this tab, and the '
                     'NEMSIS-to-Medicare wedge is NOT addressable '
                     'volume - most of it is 911 work and other payers.'})

    # ==================================================== LEIE_Read_Panel =
    ws2 = wb.create_sheet('LEIE_Read_Panel')
    sb = lib.SheetBuilder(ws2, 10,
                          col_widths=[30, 13, 13, 13, 44, 13, 13, 13, 13,
                                      40],
                          tab_color='FF6B7C93')
    sb.title('LEIE read panel: ambulance-tagged federal exclusions, '
             'counted and fenced')
    sb.subtitle('The question: what does the OIG List of Excluded '
                'Individuals and Entities actually say about the '
                'ambulance industry - who, where, on what statutory '
                'ground, and across what time span? All counts are LIVE '
                'formulas over the carried LEIE_Ambulance_Exclusions tab '
                '(join: state column G, exclusion type column H, '
                'business-name column C, exclusion date column I). '
                'Footprint = NE IA KS MO OH WI VA MN IN KY, provisional '
                'pending E.5.')
    sb.note('DATA QUALITY: the LEIE is CUMULATIVE - exclusion dates here '
            'run from the mid-1980s to 2025 and most excluded parties '
            'are INDIVIDUALS (EMTs, owners, billers), not companies; '
            'reinstatements are not shown; the ambulance tag is the '
            'OIG general/specialty text, which is coarse. A state count '
            'reflects decades of enforcement activity and list '
            'curation, not current-market integrity risk.', height=34)
    sb.blank()

    L = lambda col: f"'{LEIE}'!${col}$5:${col}$570"
    fp_arr = '{' + ','.join(f'"{s}"' for s in FP) + '}'
    top_states = ['PA', 'TX', 'CA', 'OH', 'FL', 'KY', 'NY', 'GA', 'IN',
                  'NC', 'NJ', 'WV', 'AR', 'LA', 'VA']

    sb.banner('Panel A. Where: exclusions by state, top 15 (live counts '
              'over the carried tab)')
    sb.headers(['State', 'Exclusions (live)', 'Share of national (live)',
                '', '', '', '', '', '', 'Note'])
    a0 = sb.r + 1
    tot_f = f'=COUNTIF({L("G")},"?*")'
    for i, st in enumerate(top_states):
        rn = a0 + i
        note = None
        if i == 0:
            note = ('cumulative counts since the 1980s - population and '
                    'enforcement history, not a risk ranking', 'note')
        elif st in FP:
            note = ('footprint state', 'note')
        sb.row([(st, 'label'),
                (f'=COUNTIF({L("G")},"{st}")', 'fml', lib.FMT_INT),
                (f'=IF($B${a0 + 15}=0,"n/a",B{rn}/$B${a0 + 15})', 'fml',
                 lib.FMT_PCT1),
                None, None, None, None, None, None, note])
    sb.row([('NATIONAL TOTAL (live)', 'label'), (tot_f, 'fml',
            lib.FMT_INT), None, None, None, None, None, None, None,
            ('all ambulance-tagged rows on the carried tab', 'note')])
    r_tot = a0 + 15
    sb.blank()

    sb.banner('Panel B. Why: exclusions by statutory ground (live)')
    sb.headers(['Exclusion type', 'Statutory ground', 'Count (live)',
                'Share (live)', '', '', '', '', '', 'Note'])
    b0 = sb.r + 1
    types = ['1128a1', '1128b4', '1128b8', '1128b7', '1128a3', '1128b5',
             '1128a2', '1128a4']
    for i, t in enumerate(types):
        rn = b0 + i
        sb.row([(t, 'label'), (TYPE_LABEL[t], 'text'),
                (f'=COUNTIF({L("H")},"{t}")', 'fml', lib.FMT_INT),
                (f'=IF($B${r_tot}=0,"n/a",C{rn}/$B${r_tot})', 'fml',
                 lib.FMT_PCT1),
                None, None, None, None, None,
                ('mandatory grounds (1128a) are convictions; permissive '
                 '(1128b) include license actions', 'note')
                if i == 0 else None])
    sb.row([('All other codes (live)', 'label'),
            ('breach of settlement / CIA, payment-information and other '
             'permissive grounds', 'text'),
            (f'=$B${r_tot}-SUM(C{b0}:C{b0 + len(types) - 1})', 'fml',
             lib.FMT_INT),
            None, None, None, None, None, None, None])
    sb.blank()

    sb.banner('Panel C. Who: individuals vs business entities '
              '(business-name-blank heuristic, live)')
    sb.headers(['Measure', 'Count (live)', 'Share (live)', '', '', '', '',
                '', '', 'Note'])
    c0 = sb.r + 1
    sb.row([('Business entities (BUSNAME printed)', 'label'),
            (f'=COUNTIF({L("C")},"?*")', 'fml', lib.FMT_INT),
            (f'=IF($B${r_tot}=0,"n/a",B{c0}/$B${r_tot})', 'fml',
             lib.FMT_PCT1),
            None, None, None, None, None, None,
            ('heuristic: a non-blank business-name cell marks an entity '
             'exclusion', 'note')])
    sb.row([('Individuals (BUSNAME blank)', 'label'),
            (f'=$B${r_tot}-B{c0}', 'fml', lib.FMT_INT),
            (f'=IF($B${r_tot}=0,"n/a",B{c0 + 1}/$B${r_tot})', 'fml',
             lib.FMT_PCT1),
            None, None, None, None, None, None,
            ('owners, managers, EMTs and paramedics - four in five rows '
             'are people, not companies', 'note')])
    sb.blank()

    sb.banner('Panel D. The footprint slice (live)')
    sb.headers(['State', 'Exclusions (live)', 'Of which business '
                'entities (live)', '', '', '', '', '', '', 'Note'])
    d0 = sb.r + 1
    for i, st in enumerate(FP):
        rn = d0 + i
        sb.row([(st, 'label'),
                (f'=COUNTIF({L("G")},"{st}")', 'fml', lib.FMT_INT),
                (f'=COUNTIFS({L("G")},"{st}",{L("C")},"?*")', 'fml',
                 lib.FMT_INT),
                None, None, None, None, None, None,
                ('KY and OH carry most of the footprint history', 'note')
                if i == 0 else None])
    dl = d0 + len(FP)
    sb.row([('FOOTPRINT TOTAL (live)', 'label'),
            (f'=SUM(B{d0}:B{dl - 1})', 'fml', lib.FMT_INT),
            (f'=SUM(C{d0}:C{dl - 1})', 'fml', lib.FMT_INT),
            None, None, None, None, None, None,
            ('share of national prints in the read panel below', 'note')])
    r_fp = dl
    sb.blank()

    sb.banner('Panel E. When: exclusions by decade of exclusion date '
              '(live, LEFT on the date field)')
    sb.headers(['Decade', 'Exclusions (live)', '', '', '', '', '', '', '',
                'Note'])
    e0 = sb.r + 1
    for i, (label, pref) in enumerate([('1980s', '198'), ('1990s', '199'),
                                       ('2000s', '200'), ('2010s', '201'),
                                       ('2020s', '202')]):
        sb.row([(label, 'label'),
                (f'=SUMPRODUCT(--(LEFT({L("I")},3)="{pref}"))', 'fml',
                 lib.FMT_INT),
                None, None, None, None, None, None, None,
                ('the modal exclusion on this list is 15-25 years old',
                 'note') if i == 2 else None])
    sb.blank()

    sb.note('GUARDRAIL - read before quoting anything above: the LEIE is '
            'INTEGRITY CONTEXT ONLY and is NEVER a sizing input, a '
            'supplier count, a market-quality score or a diligence '
            'verdict on any operator. Exclusions span four decades, '
            'mostly name individuals, and say nothing about entities '
            'operating today. No row on this tab is connected to any '
            'company elsewhere in this workbook.', height=32)

    sb.banner('Read panel')
    sb.prose(f'The exclusion list, read plainly: {n_tot} '
             'ambulance-tagged exclusions nationally, accumulated since '
             f'the mid-1980s; about one in five ({n_biz}) is a business '
             'entity and the rest are individuals; two thirds sit on '
             'the mandatory program-crime ground (1128a1); and the '
             f'footprint holds {n_fp} of them ({n_fp_biz} entities), '
             'concentrated in Kentucky and Ohio, with the 2000s - not '
             'the 2020s - as the modal decade. The shape says '
             'enforcement history, not present-day market risk: the '
             'list is a compliance screen input, full stop.')

    facts += [
        {'metric': 'Ambulance-tagged LEIE exclusions in footprint '
                   'states (cumulative)', 'year': 2025, 'value': n_fp,
         'unit': f'exclusions (of {n_tot} national)', 'basis': 'GOV',
         'tier': 'A', 'source_keys': ['a15_leie'],
         'locator': 'LEIE_Ambulance_Exclusions col G in {NE IA KS MO OH '
                    'WI VA MN IN KY}; live COUNTIF panel D',
         'lives_on': 'LEIE_Read_Panel',
         'cross_check': f'KY {st_count.get("KY", 0)} + OH '
                        f'{st_count.get("OH", 0)} carry most of the '
                        'footprint total; dates span 1985-2025'},
        {'metric': 'Business-entity share of ambulance-tagged LEIE '
                   'exclusions (BUSNAME heuristic)', 'year': 2025,
         'value': round(n_biz / n_tot, 4), 'unit': 'share',
         'basis': 'DERIVED', 'tier': 'A', 'source_keys': ['a15_leie'],
         'locator': 'Panel C live COUNTIF on business-name column C '
                    f'({n_biz} of {n_tot})',
         'lives_on': 'LEIE_Read_Panel',
         'cross_check': 'Four in five excluded parties are individuals '
                        '- the list is mostly people, not companies'},
    ]

    findings.append({
        'id_hint': 73,
        'finding': 'The federal exclusion list, counted end to end, is '
                   f'integrity context and nothing more: {n_tot} '
                   'ambulance-tagged exclusions accumulated over four '
                   f'decades, {round((1 - n_biz / n_tot) * 100)}% of '
                   'them individuals, two thirds on the mandatory '
                   f'program-crime ground, {n_fp} in the footprint '
                   'states with the 2000s as the modal decade. The '
                   'measured shape - old, individual, '
                   'conviction-driven - is precisely why it can anchor '
                   'a compliance screen and can never anchor a market '
                   'size or a supplier count.',
        'numbers': "='LEIE_Read_Panel'!B" + str(r_fp),
        'sources': 'a15_leie',
        'confidence': 'High; live counts over the carried primary '
                      'extract',
        'guardrail': 'NEVER a sizing input and never a statement about '
                     'any operator active today: cumulative since the '
                     '1980s, reinstatements invisible, individuals '
                     'dominate, and the ambulance tag is coarse OIG '
                     'text. Footprint list provisional pending E.5.'})

    return {'facts': facts, 'sources': sources, 'excluded': excluded,
            'findings': findings,
            'meta': {'ladder_rows': len(ladder),
                     'psps_rows': loc['psps']['rows'],
                     'mup_nat_rows': loc['mup_nat']['rows'],
                     'mup_state_block': (loc['mup_state']['lo'],
                                         loc['mup_state']['hi'])}}
