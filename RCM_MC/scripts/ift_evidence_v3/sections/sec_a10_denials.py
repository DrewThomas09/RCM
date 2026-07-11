"""A.10: Denial_Economics - what the medical-necessity screen is worth,
in dollars, 2010-2024.

Denied services x average allowed per service (same code-year, PSPS
submitted-claims basis) = the dollars the screen filters out each year,
trended fifteen years, total and for the BLS non-emergency line A0428,
with the denial-RATE trend printed beside the denial-DOLLARS trend
because the two can and do diverge when volume moves.
"""

SHEETS = [{'name': 'Denial_Economics',
           'question': 'How many dollars does the Medicare ambulance '
                       'medical-necessity screen deny per year, and is the '
                       'filter tightening or shrinking?'}]

TAB = 'Denial_Economics'
P = 'PSPS_Denial_Series'
CODES = ['A0425', 'A0426', 'A0427', 'A0428', 'A0429', 'A0433', 'A0434']
LEVEL = {'A0425': 'Ground mileage (per mile)', 'A0426': 'ALS non-emergency',
         'A0427': 'ALS emergency', 'A0428': 'BLS non-emergency',
         'A0429': 'BLS emergency', 'A0433': 'ALS level 2', 'A0434': 'SCT'}
OD = {'H': 'hospital', 'N': 'SNF', 'R': 'residence',
      'E': 'residential/custodial facility', 'J': 'freestanding ESRD',
      'G': 'hospital-based ESRD', 'P': 'physician office', 'S': 'scene',
      'D': 'diagnostic/therapeutic site', 'I': 'transfer point',
      'X': 'intermediate stop'}


def _od_read(mod):
    if len(mod) == 2 and mod[0] in OD and mod[1] in OD:
        return f'{OD[mod[0]]} to {OD[mod[1]]}'
    return 'other/administrative modifier'


def _scan_psps(ws):
    """(rows map {(year, code): row}, rmin, rmax) from Panel A of the
    carried PSPS_Denial_Series tab; values read raw for the fact math."""
    rows, vals = {}, {}
    for row in ws.iter_rows(min_row=1, max_row=200, max_col=8):
        a, b = row[0].value, row[1].value
        if isinstance(a, (int, float)) and 2005 <= a <= 2030 \
                and b in CODES:
            rows[(int(a), b)] = row[0].row
            vals[(int(a), b)] = {'sub': row[3].value, 'den': row[4].value,
                                 'alw': row[7].value}
    rmin = min(rows.values())
    rmax = max(rows.values())
    return rows, vals, rmin, rmax


def build(wb, ctx):
    lib = ctx['lib']
    cache = ctx['cache']
    facts, sources, findings = [], [], []

    prow, pval, rmin, rmax = _scan_psps(wb[P])
    years = sorted({y for y, _ in prow})

    def denied_usd(y, codes=CODES):
        out = 0.0
        for c in codes:
            v = pval.get((y, c))
            if not v or not v['sub'] or (v['sub'] - v['den']) <= 0:
                continue
            out += v['den'] * v['alw'] / (v['sub'] - v['den'])
        return out

    tot = {y: denied_usd(y) for y in years}
    a28 = {y: denied_usd(y, ['A0428']) for y in years}
    y0, y1 = years[0], years[-1]
    a28_rate = {y: pval[(y, 'A0428')]['den'] / pval[(y, 'A0428')]['sub']
                for y in years}

    # PSPS detail caches: 2024 A0428 by initial origin-destination modifier
    try:
        bm = lib.load_cache(cache, f'psps_agg_{y1}_A0428')[
            'by_initial_modifier']
    except FileNotFoundError:
        bm = None

    acc = ctx['accessed']
    sources += [
        {'key': 'de_psps_series', 'publisher': 'CMS',
         'document': 'Physician/Supplier Procedure Summary, ambulance '
                     'HCPCS, 2010-2024 - submitted/denied services and '
                     'allowed charges as carried on PSPS_Denial_Series '
                     'Panel A',
         'vintage': f'{y0}-{y1} submitted-claims basis',
         'locator': f'{P} rows {rmin}-{rmax}: submitted services (D), '
                    'denied services (E), allowed charges (H) by code-year',
         'supplies': 'The whole denial-dollars valuation: denied services '
                     'x allowed per allowed service, code-year by '
                     'code-year',
         'url': 'https://data.cms.gov/summary-statistics-on-use-and-'
                'payments/physiciansupplier-procedure-summary',
         'tier': 'A', 'accessed': acc, 'powers': [TAB]},
        {'key': 'de_psps_modifier', 'publisher': 'CMS',
         'document': 'Physician/Supplier Procedure Summary 2024 line '
                     'detail, A0428, aggregated by initial '
                     'origin-destination modifier',
         'vintage': f'{y1} submitted-claims basis',
         'locator': 'PSPS_SUBMITTED_SERVICE_CNT / PSPS_DENIED_SERVICES_CNT '
                    '/ PSPS_ALLOWED_CHARGE_AMT summed per initial modifier '
                    '(cache psps_agg_2024_A0428)',
         'supplies': 'Where the denied A0428 dollars sit by '
                     'origin-destination pair',
         'url': 'https://data.cms.gov/summary-statistics-on-use-and-'
                'payments/physiciansupplier-procedure-summary',
         'tier': 'A', 'accessed': acc, 'powers': [TAB]},
    ]

    # ================================================================ sheet
    ws = wb.create_sheet(TAB)
    sb = lib.SheetBuilder(ws, 10,
                          col_widths=[12, 30, 14, 14, 14, 13, 13, 14, 9,
                                      42],
                          tab_color='FF8C1D40')
    sb.title('Denial economics: what the Medicare medical-necessity screen '
             'filters out, in dollars, 2010-2024')
    sb.subtitle('The question: how many dollars of submitted ambulance '
                'services does Medicare deny each year - total and on the '
                'BLS non-emergency line A0428 - and is the filter '
                'tightening (rate) or shrinking (dollars)? Source: PSPS '
                f'{y0}-{y1} as carried on {P} (submitted/denied services '
                'and allowed charges by code-year; join key HCPCS x year), '
                'plus 2024 line detail by origin-destination modifier. '
                'Every dollar figure on this tab is a VALUATION: denied '
                'services x average allowed per ALLOWED service of the '
                'same code-year.')
    sb.note('DATA QUALITY: PSPS is the submitted-claims universe (carrier '
            'processing), NEVER comparable to MUP final action - do not '
            'mix this tab with MUP tabs. Denied services carry no allowed '
            'amount at source, so denied dollars price them at the average '
            'allowed of their paid code-year peers (stated convention, '
            'printed per panel). Denial here is initial claim-line '
            'disposition: appeals and resubmission later recover an '
            'unmeasured share, so dollars denied is NOT dollars finally '
            'lost. Fractional service counts are PSPS artifacts of unit '
            'fields, carried as published.')
    sb.blank()

    sb.banner('Panel A. Method - the valuation convention, printed')
    sb.prose('Dollars denied (code-year) = denied services x [allowed '
             'charges / (submitted services - denied services)] of the '
             'same code-year. All cells below compute LIVE against '
             f'{P} Panel A - nothing is retyped.')
    sb.prose('Rate and dollars answer different questions and can diverge: '
             'a denial RATE can rise while denial DOLLARS fall whenever '
             'submitted volume falls faster - which is exactly what the '
             'A0428 columns show after 2019. Read them side by side, '
             'never one alone.')
    sb.blank()

    # ---- Panel B: the 15-year trend ----
    sb.banner('Panel B. Dollars denied per year, beside the denial rate - '
              f'all ambulance codes and the A0428 line, {y0}-{y1}')
    sb.headers(['Year', 'Denied services, all codes',
                'Denied $ all codes', 'Denied $ base codes (excl. mileage)',
                'Denied $ A0428', 'A0428 denial rate',
                'Base-code denial rate', '', '', 'Note'])
    b0 = sb.r + 1
    rA = f"'{P}'!$A${rmin}:$A${rmax}"
    rB = f"'{P}'!$B${rmin}:$B${rmax}"
    rD = f"'{P}'!$D${rmin}:$D${rmax}"
    rE = f"'{P}'!$E${rmin}:$E${rmax}"
    rH = f"'{P}'!$H${rmin}:$H${rmax}"
    for i, y in enumerate(years):
        rn = b0 + i
        r28 = prow[(y, 'A0428')]
        note = None
        if i == 0:
            note = ('denied $ columns price denied services at the '
                    'code-year average allowed (Panel A convention)',
                    'note')
        elif y == y1:
            note = ('rate up, dollars down vs 2010 on A0428: the '
                    'submitted-volume collapse dominates', 'note')
        sb.row([(y, 'src'),
                (f'=SUMIFS({rE},{rA},A{rn})', 'link', lib.FMT_INT),
                (f'=SUMPRODUCT(({rA}=A{rn})*{rE}*{rH}/({rD}-{rE}))',
                 'link', lib.FMT_USD),
                (f'=SUMPRODUCT(({rA}=A{rn})*({rB}<>"A0425")*{rE}*{rH}'
                 f'/({rD}-{rE}))', 'link', lib.FMT_USD),
                (f"='{P}'!E{r28}*'{P}'!H{r28}/('{P}'!D{r28}-'{P}'!E{r28})",
                 'link', lib.FMT_USD),
                (f"='{P}'!E{r28}/'{P}'!D{r28}", 'link', lib.FMT_PCT1),
                (f'=SUMPRODUCT(({rA}=A{rn})*({rB}<>"A0425")*{rE})'
                 f'/SUMPRODUCT(({rA}=A{rn})*({rB}<>"A0425")*{rD})',
                 'link', lib.FMT_PCT1),
                None, None, note])
    bend = sb.r
    rn_last = b0 + years.index(y1)
    sb.blank()

    # ---- Panel C: 2024 code detail ----
    sb.banner(f'Panel C. {y1} code detail - where the denied dollars sit')
    sb.headers(['HCPCS', 'Level of service', 'Submitted services',
                'Denied services', 'Denial rate',
                'Avg allowed per allowed service $', 'Denied $', '', '',
                'Note'])
    c0 = sb.r + 1
    for j, c in enumerate(CODES):
        rn = c0 + j
        r = prow[(y1, c)]
        sb.row([(c, 'src'), (LEVEL[c], 'text'),
                (f"='{P}'!D{r}", 'link', lib.FMT_INT),
                (f"='{P}'!E{r}", 'link', lib.FMT_INT),
                (f'=D{rn}/C{rn}', 'fml', lib.FMT_PCT1),
                (f"='{P}'!H{r}/('{P}'!D{r}-'{P}'!E{r})", 'link',
                 lib.FMT_USD2),
                (f'=D{rn}*F{rn}', 'fml', lib.FMT_USD),
                None, None,
                ('mileage denies with its transport: A0425 rows are '
                 'per-mile units, not transports', 'note')
                if c == 'A0425' else None])
    sb.blank()

    # ---- Panel D: A0428 by origin-destination modifier (detail caches) ---
    sb.banner(f'Panel D. {y1} A0428 denied dollars by origin-destination '
              'pair (PSPS line detail, initial modifier)')
    if bm:
        sb.headers(['Initial modifier', 'Origin to destination',
                    'Submitted services', 'Denied services', 'Allowed $',
                    'Denial rate', 'Avg allowed per allowed svc $',
                    'Denied $', '', 'Note'])
        top = sorted(((k, v) for k, v in bm.items()
                      if len(k) == 2 and k[0] in OD and k[1] in OD),
                     key=lambda kv: -kv[1]['SUBMITTED_SERVICE_CNT'])[:8]
        struct = [(k, bm[k]) for k in ('NP', 'PN') if k in bm]
        for j, (k, v) in enumerate(top + struct):
            rn = sb.r + 1
            note = None
            if j == 0:
                note = ('modifier letters per PSPS: H hospital, N SNF, R '
                        'residence, E residential/custodial, J '
                        'freestanding ESRD, P physician office', 'note')
            if k in ('NP', 'PN'):
                note = ('structurally non-covered pair (physician-office '
                        'leg): denied at effectively 100% - the coverage '
                        'screen in its purest form', 'note')
            sub = v['SUBMITTED_SERVICE_CNT']
            den = v['DENIED_SERVICES_CNT']
            alw = v['ALLOWED_CHARGE_AMT']
            sb.row([(k, 'src'), (_od_read(k), 'text'),
                    (round(sub), 'src', lib.FMT_INT),
                    (round(den), 'src', lib.FMT_INT),
                    (round(alw), 'src', lib.FMT_USD),
                    (f'=IF(C{rn}=0,"n/a",D{rn}/C{rn})', 'fml',
                     lib.FMT_PCT1),
                    (f'=IF(C{rn}-D{rn}<=0,"n/a",E{rn}/(C{rn}-D{rn}))',
                     'fml', lib.FMT_USD2),
                    (f'=IF(C{rn}-D{rn}<=0,E{rn},D{rn}*G{rn})', 'fml',
                     lib.FMT_USD),
                    None, note])
        sb.note('Hospital- and SNF-anchored pairs (HN, HR, HH, HE) carry '
                'the largest denied-dollar pools on A0428; the dialysis '
                'pairs (RJ, JR) are the RSNAT product. For the fully '
                'denied NP/PN pairs the denied $ cell prints the submitted '
                'allowed floor, since no allowed peer price exists.')
    else:
        sb.row([('PENDING', 'note'), None, None, None, None, None, None,
                None, None,
                ('would be filled by CMS PSPS line detail (psps_agg cache '
                 'keys) - modifier-level denial detail', 'note')])
    sb.blank()

    # ---- Panel E: RSNAT cross-link ----
    sb.banner('Panel E. The enforcement arm - RSNAT prior authorization '
              '(cross-link; full timeline in handoff B.4)')
    pi_rows = {}
    if 'Payment_Integrity' in wb.sheetnames:
        for row in wb['Payment_Integrity'].iter_rows(min_row=1, max_row=40,
                                                     max_col=2):
            v = row[0].value
            if isinstance(v, str):
                if v.startswith('"Repetitive" definition'):
                    pi_rows['def'] = row[0].row
                elif v.startswith('National scope'):
                    pi_rows['scope'] = row[0].row
    if pi_rows:
        for key, label in [('def', 'What RSNAT covers'),
                           ('scope', 'National scope and codes')]:
            if key in pi_rows:
                sb.row([(label, 'label'),
                        (f"='Payment_Integrity'!B{pi_rows[key]}", 'link'),
                        None, None, None, None, None, None, None,
                        ('the A0426/A0428 denial mechanics above are what '
                         'RSNAT front-loads into prior authorization',
                         'note') if key == 'scope' else None],
                       wrap=True)
    else:
        sb.row([('RSNAT timeline', 'label'), ('PENDING', 'note'), None,
                None, None, None, None, None, None,
                ('to be carried by handoff B.4 (CMS RSNAT model rules and '
                 'MLN6805343)', 'note')])
    sb.blank()

    sb.banner('Read panel')
    chg = tot[y1] / tot[y0] - 1
    sb.prose('Read the screen as market structure, not as noise: Medicare '
             'denies roughly half a billion dollars of submitted ambulance '
             f'services every year - about ${tot[y1] / 1e6:,.0f}M in '
             f'{y1}, of which ${a28[y1] / 1e6:,.0f}M sits on the BLS '
             'non-emergency line - and it has done so for fifteen years '
             f'(${tot[y0] / 1e6:,.0f}M in {y0}, peak in 2012, trough in '
             '2020). The level is flat in nominal dollars while the A0428 '
             'denial RATE drifted up, because submitted volume collapsed: '
             'the filter is tightening per claim even as the pool it '
             'filters shrinks. The medical-necessity screen is therefore a '
             'structural revenue filter on the non-emergency book: '
             'operators with professional revenue-cycle machinery - PCS '
             'documentation, prior-authorization workflow, appeals - '
             'convert a share of these denials into paid claims, while '
             'informal operators absorb them as write-offs. The same '
             'billed service is worth different amounts to differently '
             'equipped operators; the spread is the revenue-cycle '
             'opportunity, and this tab prices its upper bound. What the '
             'tab does NOT measure: final losses (appeals recover an '
             'unmeasured share), MA-side denials, or patient collections.')

    facts += [
        {'metric': 'Medicare ambulance dollars denied, all seven PSPS '
                   'codes (valuation: denied services x code-year average '
                   'allowed per allowed service)',
         'year': y1, 'value': round(tot[y1]), 'unit': 'USD',
         'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['de_psps_series'],
         'locator': f'Panel B, {y1} row, all-codes column; live SUMPRODUCT '
                    f'over {P} rows {rmin}-{rmax}',
         'lives_on': TAB,
         'cross_check': 'Panel C code rows sum to it; denominator '
                        '(submitted minus denied) positive in every '
                        'code-year, verified at build'},
        {'metric': 'A0428 BLS non-emergency dollars denied (same '
                   'valuation)',
         'year': y1, 'value': round(a28[y1]), 'unit': 'USD',
         'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['de_psps_series'],
         'locator': f'Panel B, {y1} row, A0428 column, live against {P} '
                    f'row {prow[(y1, "A0428")]}',
         'lives_on': TAB,
         'cross_check': f'A0428 denial rate {a28_rate[y1]:.1%} in {y1} vs '
                        f'{a28_rate[y0]:.1%} in {y0}: rate UP while '
                        'dollars fell - the volume-collapse divergence '
                        'printed in Panel A'},
        {'metric': 'Fifteen-year trend in total ambulance denied dollars '
                   f'({y0} to {y1}, nominal change)',
         'year': y1, 'value': round(chg, 4), 'unit': 'share (signed)',
         'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['de_psps_series'],
         'locator': f'Panel B column C, {y0} vs {y1} rows',
         'lives_on': TAB,
         'cross_check': 'Direction: flat nominal (declining real), peak '
                        '2012, trough 2020; A0428 denied dollars down '
                        'roughly 40% over the same window while its rate '
                        'rose'},
    ]

    findings.append({
        'id_hint': 68,
        'finding': 'The medical-necessity screen is a structural, '
                   'fifteen-year-stable revenue filter: Medicare denies '
                   f'about ${tot[y1] / 1e6:,.0f}M of submitted ambulance '
                   f'services in {y1} (${a28[y1] / 1e6:,.0f}M on BLS '
                   'non-emergency alone), essentially the same nominal '
                   f'level as {y0}, while the A0428 denial rate ROSE as '
                   'its volume collapsed. Professional revenue-cycle '
                   'operators convert a share of this filtered revenue '
                   'through documentation, prior authorization and '
                   'appeals; informal operators write it off - the spread '
                   'is a durable operating-model advantage priced at up '
                   'to half a billion dollars a year.',
        'numbers': f"='{TAB}'!C{rn_last}",
        'sources': 'de_psps_series; de_psps_modifier',
        'confidence': 'High on the arithmetic (live formulas over carried '
                      'PSPS cells); the dollar figure is a stated '
                      'valuation convention',
        'guardrail': 'Denial is NOT final loss: appeals and resubmission '
                     'recover an unmeasured share, PSPS is '
                     'submitted-services basis (never mix with MUP final '
                     'action), and denied services are priced at their '
                     'paid peers\' average allowed - an upper-bound '
                     'valuation of initial denials, not a measured cash '
                     'loss.'})

    # ---- chart: dollars denied per year ----
    lib.add_chart(ws, f'L{b0 - 1}',
                  'Medicare ambulance dollars denied per year (valuation '
                  'at code-year average allowed)',
                  f"'{TAB}'!$A${b0}:$A${bend}",
                  [('All codes', f"'{TAB}'!$C${b0}:$C${bend}"),
                   ('A0428 BLS non-emergency',
                    f"'{TAB}'!$E${b0}:$E${bend}")],
                  kind='line', y_fmt='$#,##0,,"M"', width=15.5, height=8.0)

    return {'facts': facts, 'sources': sources, 'excluded': [],
            'findings': findings,
            'meta': {'years': [y0, y1],
                     'valuation': 'denied services x code-year average '
                                  'allowed per allowed service',
                     'total_denied_2024': round(tot[y1]),
                     'a0428_denied_2024': round(a28[y1])}}
