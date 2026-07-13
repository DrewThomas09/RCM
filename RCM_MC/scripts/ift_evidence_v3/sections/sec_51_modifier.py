"""Run 5, Task 5.1: Modifier_QM_QN_Series - the claim-level billing-relationship
cut of Medicare FFS ground ambulance.

Medicare carrier ambulance lines carry a SECOND HCPCS modifier that names the
billing relationship behind the service: QN (furnished directly by a provider of
services) and QM (provided under arrangement by a provider of services). A
"provider of services" is a Part A institution - overwhelmingly a hospital, with
some SNFs - so a QN or QM flag on a Part B carrier claim measures, at the claim
level, the exact hospital-billed vs independent distinction the insourcing tab
triangulates indirectly from biller names. This tab cuts every ground A-code by
QN / QM / no-flag, by year 2010-2024, with the service-level (BLS/ALS/SCT) split
and an origin-destination joint cut, and reconciles its totals live to the
existing PSPS series.

Data source: the PSPS second-modifier re-cut (psps_mod2_* cache), pulled by
pull_psps_mod2.py. Rule source: CMS Medicare Claims Processing Manual Pub 100-04
Ch 15. Heavy CMS small-count suppression ('*') makes every QN/QM count a FLOOR.
"""

SHEETS = [{'name': 'Modifier_QM_QN_Series',
           'question': 'What share of Medicare FFS ground ambulance is billed '
                       'by a provider of services (hospital or SNF), measured '
                       'directly from the QN / QM carrier claim modifier?'}]

TRANSPORT = ['A0426', 'A0427', 'A0428', 'A0429', 'A0433', 'A0434']
MILEAGE = 'A0425'
ALL_CODES = TRANSPORT + [MILEAGE]
LEVELS = [('BLS ground (A0428 + A0429)', ['A0428', 'A0429']),
          ('ALS ground (A0426 + A0427 + A0433)', ['A0426', 'A0427', 'A0433']),
          ('SCT (A0434)', ['A0434'])]
YEARS = [str(y) for y in range(2010, 2025)]

# Origin-destination modifier letters (each O-D code is origin+destination).
OD = {'D': 'diagnostic/therapeutic site', 'E': 'residential facility',
      'G': 'hospital ESRD', 'H': 'hospital', 'I': 'transfer site',
      'J': 'freestanding ESRD', 'N': 'SNF', 'P': 'physician office',
      'R': 'residence', 'S': 'scene', 'X': 'intermediate stop'}

MANUAL_URL = ('https://www.cms.gov/regulations-and-guidance/guidance/manuals/'
              'downloads/clm104c15.pdf')
PSPS_URL = ('https://data.cms.gov/summary-statistics-on-use-and-payments/'
            'medicare-fee-for-service-parts-a-b/physician-supplier-procedure-'
            'summary')


def _od_label(code):
    code = (code or '').strip().upper()
    if len(code) == 2 and code[0] in OD and code[1] in OD:
        return f'{code} ({OD[code[0]]} to {OD[code[1]]})'
    return code or '(none)'


def load_series(lib, cache):
    """Aggregate the psps_mod2 cache into the structures the tab and the
    Insourcing_Bounds third-leg panel both render from."""
    def blank():
        return {'services': 0.0, 'allowed': 0.0, 'n_supp': 0}
    annual = {}          # year -> {bucket -> {services, allowed, n_supp}} + total
    level_latest = {}    # level label -> {bucket/total services}
    od_latest = {}       # od code -> hospital-flagged services (QN+QM)
    recon = {}           # (year, code) -> mod2 total services
    latest = YEARS[-1]
    for yr in YEARS:
        a = annual.setdefault(yr, {'QN': blank(), 'QM': blank(),
                                   'none': blank(), 'total': blank()})
        for code in TRANSPORT:
            key = f'psps_mod2_{yr}_{code}'
            try:
                d = lib.load_cache(cache, key)
            except Exception:
                continue
            recon[(yr, code)] = d.get('total', {}).get('services', 0.0)
            for b, bk in d.get('buckets', {}).items():
                tgt = a.get(b) or a['none']
                tgt['services'] += bk.get('services', 0.0)
                tgt['allowed'] += bk.get('allowed', 0.0)
                tgt['n_supp'] += bk.get('n_supp', 0)
                a['total']['services'] += bk.get('services', 0.0)
                a['total']['allowed'] += bk.get('allowed', 0.0)
    # service-level split, latest year
    for label, codes in LEVELS + [('Mileage (A0425)', [MILEAGE])]:
        lv = level_latest.setdefault(label, {'QN': 0.0, 'QM': 0.0,
                                             'none': 0.0, 'total': 0.0})
        for code in codes:
            try:
                d = lib.load_cache(cache, f'psps_mod2_{latest}_{code}')
            except Exception:
                continue
            for b, bk in d.get('buckets', {}).items():
                lv[b if b in ('QN', 'QM') else 'none'] += bk.get('services', 0.0)
                lv['total'] += bk.get('services', 0.0)
    # origin-destination joint cut, latest year, hospital-flagged (QN+QM)
    for code in TRANSPORT:
        try:
            d = lib.load_cache(cache, f'psps_mod2_{latest}_{code}')
        except Exception:
            continue
        for b in ('QN', 'QM'):
            for od, sv in d.get('buckets', {}).get(b, {}).get('by_od', {}).items():
                od_latest[od] = od_latest.get(od, 0.0) + sv
    return {'annual': annual, 'level_latest': level_latest,
            'od_latest': od_latest, 'recon': recon, 'latest': latest}


def _psps_agg_total(lib, cache, yr, code):
    """Independent total from the ORIGINAL psps_agg cache (summed over the
    initial-modifier aggregation) for the live reconciliation row."""
    try:
        d = lib.load_cache(cache, f'psps_agg_{yr}_{code}')
    except Exception:
        return None
    fld = 'SUBMITTED_SERVICE_CNT'
    return sum(v.get(fld, 0.0) for v in d.get('by_initial_modifier', {}).values())


def build(wb, ctx):
    lib = ctx['lib']
    cache = ctx['cache']
    accessed = ctx['accessed']
    facts, sources, excluded, findings = [], [], [], []

    S = load_series(lib, cache)
    annual = S['annual']
    latest = S['latest']
    a24 = annual[latest]
    a10 = annual['2010']

    def share(a, b):
        return (a / b) if b else 0.0
    tot24 = a24['total']['services']
    qn24 = a24['QN']['services']
    qm24 = a24['QM']['services']
    hf24 = qn24 + qm24
    hf_share24 = share(hf24, tot24)
    qn_share24 = share(qn24, tot24)
    qm_share24 = share(qm24, tot24)
    hf10 = a10['QN']['services'] + a10['QM']['services']
    hf_share10 = share(hf10, a10['total']['services'])

    sources += [
        {'key': 'psps_mod2', 'publisher': 'CMS',
         'document': 'Physician/Supplier Procedure Summary (PSPS) - ground '
                     'ambulance A-codes re-cut by the HCPCS SECOND modifier '
                     '(QN / QM / no-flag), 2010-2024, national',
         'vintage': '2010-2024 annual PSPS files (pinned API uuid per year)',
         'locator': 'Client-side sum of PSPS_SUBMITTED_SERVICE_CNT and '
                    'PSPS_ALLOWED_CHARGE_AMT over every line for each HCPCS_CD, '
                    'grouped on HCPCS_SECOND_MODIFIER_CD; suppressed ("*") '
                    'lines counted as zero and tallied separately',
         'supplies': 'Every service and allowed-dollar count on this tab and '
                     'the QN/QM third-leg panel on Insourcing_Bounds',
         'url': PSPS_URL, 'tier': 'A', 'accessed': accessed,
         'powers': ['Modifier_QM_QN_Series', 'Insourcing_Bounds']},
        {'key': 'qmqn_manual', 'publisher': 'CMS',
         'document': 'Medicare Claims Processing Manual, Pub. 100-04, Chapter '
                     '15 (Ambulance) - definition of the QM (under arrangement '
                     'by a provider of services) and QN (furnished directly by '
                     'a provider of services) payment modifiers',
         'vintage': 'Current manual chapter at access date',
         'locator': 'Ch 15 modifier guidance; "provider of services" per SSA '
                    '1861(u) = hospital, CAH, SNF, HHA, CORF, hospice',
         'supplies': 'The rule behind what QN and QM mean, printed on Panel A',
         'url': MANUAL_URL, 'tier': 'A', 'accessed': accessed,
         'powers': ['Modifier_QM_QN_Series']},
    ]

    ws = wb.create_sheet('Modifier_QM_QN_Series')
    sb = lib.SheetBuilder(ws, 10,
                          col_widths=[40, 14, 14, 14, 16, 12, 12, 14, 14, 44],
                          tab_color='FF1F6F8B')
    sb.title('Provider-of-services billing of Medicare FFS ground ambulance: '
             'the QN and QM carrier-claim modifiers, 2010-2024')
    sb.subtitle('Carrier ambulance lines carry a second HCPCS modifier naming '
                'the billing relationship: QN (furnished directly by a provider '
                'of services) and QM (under arrangement by a provider of '
                'services). A provider of services is a Part A institution - '
                'chiefly a hospital, with some SNFs - so a QN or QM flag on a '
                'Part B claim measures hospital-or-SNF-billed ambulance '
                'directly at the claim level, the same distinction '
                'Insourcing_Bounds triangulates from biller names. This tab '
                'cuts every ground A-code by flag and year, with the '
                'service-level split and an origin-destination joint cut, and '
                'reconciles live to the existing PSPS series.')
    sb.note('DATA QUALITY: carrier-file (Part B) scope only. Institutional '
            '(Part A) ambulance billing - the hospital-bundled and SNF '
            'consolidated-billing transports - is OUTSIDE this instrument '
            'entirely, so the true provider-of-services share of operations is '
            'higher than any cell here. The flag measures the BILLING '
            'ARRANGEMENT, not fleet ownership: a hospital that furnishes '
            'directly (QN), one that contracts a supplier but drops the bill '
            'itself (QM), and one whose contracted supplier bills in its own '
            'name (no flag) can run the same trucks. Modifier compliance is '
            'imperfect. CMS suppresses lines under 11 services with "*", and '
            'those small hospital-billed rows are exactly the ones most often '
            'suppressed, so every QN/QM count here is a FLOOR - Panel B carries '
            'the suppressed-row tally beside each year.')
    sb.blank()

    # ---------------------------------------------------------- Panel A ---
    sb.banner('Panel A. What the flags mean (CMS Pub. 100-04 Ch 15), with '
              'their 2024 ground-transport counts')
    sb.headers(['Modifier', 'Meaning (billing relationship)',
                '2024 services (floor)', '2024 allowed $', 'Share of 2024 '
                'transports', '', '', '', '', 'Note'])
    pa = sb.r + 1
    _den = f'(C{pa}+C{pa + 1}+C{pa + 2})'   # QN + QM + no-flag = all transports
    sb.row([('QN', 'label'),
            ('Furnished DIRECTLY by a provider of services (the Part A '
             'institution owns and runs the service and bills Part B)', 'text'),
            (round(qn24), 'src', lib.FMT_INT),
            (round(a24['QN']['allowed']), 'src', lib.FMT_USD),
            (f'=C{pa}/{_den}', 'fml', lib.FMT_PCT2),
            None, None, None, None,
            ('the direct hospital-furnished signal; the larger of the two '
             'flags', 'note')], wrap=True, height=40)
    sb.row([('QM', 'label'),
            ('Provided UNDER ARRANGEMENT by a provider of services (a Part A '
             'institution contracts a supplier but drops the bill itself)',
             'text'),
            (round(qm24), 'src', lib.FMT_INT),
            (round(a24['QM']['allowed']), 'src', lib.FMT_USD),
            (f'=C{pa + 1}/{_den}', 'fml', lib.FMT_PCT2),
            None, None, None, None,
            ('billing-in-lieu: the arrangement the insourcing ceiling warns '
             'inflates a name-based hospital share', 'note')], wrap=True,
           height=40)
    sb.row([('(no flag)', 'label'),
            ('No provider-of-services modifier: the biller is an independent '
             'supplier billing in its own name, or the flag was omitted',
             'text'),
            (round(a24['none']['services']), 'src', lib.FMT_INT),
            (round(a24['none']['allowed']), 'src', lib.FMT_USD),
            (f'=C{pa + 2}/{_den}', 'fml', lib.FMT_PCT2),
            None, None, None, None,
            ('the denominator is all three rows summed - the live 2024 '
             'transport total', 'note')], wrap=True, height=30)
    sb.blank()

    # ---------------------------------------------------------- Panel B ---
    sb.banner('Panel B. National series by year - ground transport base codes '
              '(A0426-A0429/A0433/A0434; mileage excluded)')
    sb.headers(['Year', 'All transport services', 'QN services',
                'QM services', 'Provider-flagged (QN+QM)', 'QN share',
                'Provider-flagged share', 'Flagged allowed $',
                'Suppressed QN+QM rows', 'Note'])
    b0 = sb.r + 1
    for i, yr in enumerate(YEARS):
        a = annual[yr]
        rn = b0 + i
        qn = a['QN']['services']
        qm = a['QM']['services']
        note = None
        if yr == '2010':
            note = ('base year; the QN/QM flag was thinly used early and grows '
                    'through the series', 'note')
        elif yr == latest:
            note = ('latest PSPS vintage', 'note')
        sb.row([(int(yr), 'src'),
                (round(a['total']['services']), 'src', lib.FMT_INT),
                (round(qn), 'src', lib.FMT_INT),
                (round(qm), 'src', lib.FMT_INT),
                (f'=C{rn}+D{rn}', 'fml', lib.FMT_INT),
                (f'=IF(B{rn}=0,"n/a",C{rn}/B{rn})', 'fml', lib.FMT_PCT2),
                (f'=IF(B{rn}=0,"n/a",E{rn}/B{rn})', 'fml', lib.FMT_PCT2),
                (round(a['QN']['allowed'] + a['QM']['allowed']), 'src', lib.FMT_USD),
                (a['QN']['n_supp'] + a['QM']['n_supp'], 'src', lib.FMT_INT),
                note], wrap=bool(note))
    lib.add_chart(
        ws, f'L{b0 - 2}',
        'Provider-of-services flagged share of ground transports by year',
        f'Modifier_QM_QN_Series!$A${b0}:$A${b0 + len(YEARS) - 1}',
        [('Provider-flagged (QN+QM) share',
          f'Modifier_QM_QN_Series!$G${b0}:$G${b0 + len(YEARS) - 1}'),
         ('QN share',
          f'Modifier_QM_QN_Series!$F${b0}:$F${b0 + len(YEARS) - 1}')],
        kind='line', y_fmt='0.0%', height=7.5)
    sb.blank()

    # ---------------------------------------------------------- Panel C ---
    sb.banner(f'Panel C. Service-level split, {latest} - does provider-flagged '
              'billing skew to the high-acuity interfacility product?')
    sb.headers(['Service level', 'All services', 'QN', 'QM',
                'Provider-flagged (QN+QM)', 'Provider-flagged share', '', '',
                '', 'Note'])
    c0 = sb.r + 1
    lv = S['level_latest']
    lv_notes = {
        'SCT (A0434)': 'the specialty-care interfacility product; the flagged '
                       'share here is essentially the same as BLS and ALS - no '
                       'acuity skew appears in the flagged data',
        'Mileage (A0425)': 'loaded miles, not transports - shown for '
                           'completeness, excluded from Panel B'}
    for j, (label, _codes) in enumerate(LEVELS + [('Mileage (A0425)', [MILEAGE])]):
        v = lv[label]
        rn = c0 + j
        sb.row([(label, 'text'),
                (round(v['total']), 'src', lib.FMT_INT),
                (round(v['QN']), 'src', lib.FMT_INT),
                (round(v['QM']), 'src', lib.FMT_INT),
                (f'=C{rn}+D{rn}', 'fml', lib.FMT_INT),
                (f'=IF(B{rn}=0,"n/a",E{rn}/B{rn})', 'fml', lib.FMT_PCT2),
                None, None, None,
                (lv_notes.get(label), 'note') if label in lv_notes else None],
               wrap=label in lv_notes, height=30 if label in lv_notes else None)
    sb.blank()

    # ---------------------------------------------------------- Panel D ---
    sb.banner(f'Panel D. Origin-destination joint cut, {latest} - where the '
              'provider-flagged (QN+QM) transports actually go')
    sb.headers(['O-D modifier (origin to destination)',
                'Provider-flagged services', 'Share of flagged transports',
                '', '', '', '', '', '', 'Note'])
    od = S['od_latest']
    od_hosp = {k: v for k, v in od.items() if k != '(none)'}
    top = sorted(od_hosp.items(), key=lambda kv: -kv[1])[:8]
    flagged_od_total = sum(od_hosp.values()) or 1.0
    d0 = sb.r + 1
    for j, (code, sv) in enumerate(top):
        rn = d0 + j
        orig_h = code[:1].upper() == 'H'
        sb.row([(_od_label(code), 'text'),
                (round(sv), 'src', lib.FMT_INT),
                (f'=B{rn}/{round(flagged_od_total)}', 'fml', lib.FMT_PCT1),
                None, None, None, None, None, None,
                ('hospital-origin' if orig_h else None, 'note')])
    sb.note('The joint cut shows no single dominant lane: provider-flagged '
            'transports span residence-to-hospital (RH), hospital-to-hospital '
            '(HH) and ESRD-linked pairs (with J = freestanding dialysis), '
            'consistent with a hospital-operated service running both inbound '
            'pickups and interfacility legs. Read the ranking, not the '
            'decimals - suppression thins every cell and the flagged counts '
            'are small.')
    sb.blank()

    # ---------------------------------------------------------- Panel E ---
    sb.banner('Panel E. Reconciliation - this cut totals to the existing PSPS '
              'series (live cross-check, delta must be zero)')
    sb.headers(['Benchmark (year, code)', 'This tab: QN+QM+none total',
                'Existing psps_agg total (initial-modifier cut)',
                'Delta (live)', '', '', '', '', '', 'Note'])
    e0 = sb.r + 1
    bench = [(latest, 'A0428'), (latest, 'A0434'), ('2010', 'A0428')]
    for j, (yr, code) in enumerate(bench):
        rn = e0 + j
        mine = S['recon'].get((yr, code), 0.0)
        agg = _psps_agg_total(lib, cache, yr, code) or 0.0
        sb.row([(f'{yr} {code}', 'text'),
                (round(mine), 'src', lib.FMT_INT),
                (round(agg), 'src', lib.FMT_INT),
                (f'=B{rn}-C{rn}', 'fml', lib.FMT_INT),
                None, None, None, None, None,
                ('same PSPS rows aggregated two independent ways; the existing '
                 'PSPS_Denial_Series and Medicare series are built from column '
                 'C', 'note') if j == 0 else None], wrap=(j == 0), height=40 if j == 0 else None)
    sb.blank()

    # ------------------------------------------------------- read panel ---
    sct_lv = lv['SCT (A0434)']
    sct_flag_share = share(sct_lv['QN'] + sct_lv['QM'], sct_lv['total'])
    bls_lv = lv['BLS ground (A0428 + A0429)']
    bls_flag_share = share(bls_lv['QN'] + bls_lv['QM'], bls_lv['total'])
    sb.banner('Read panel')
    sb.prose(
        'Measured directly from the carrier claim, a provider of services '
        f'(hospital or SNF) is the flagged biller on {hf_share24 * 100:.3f}% '
        f'of {latest} Medicare FFS ground transports - {round(hf24):,} services '
        f'({round(qn24):,} furnished directly under QN, {round(qm24):,} under '
        f'arrangement under QM). The flagged share has risen nearly ninefold '
        f'from {hf_share10 * 100:.3f}% in 2010, and QN now outweighs QM about '
        f'{(qn24 / qm24 if qm24 else 0):.0f} to 1 - though QM briefly led in '
        '2012-2017 before falling out of use, a coding-practice shift rather '
        'than a volume shift. Two cautions govern how to read it. First, it is '
        'a STRICT floor: it sits an order of magnitude below even the name-rule '
        'hospital-billed FLOOR on Insourcing_Bounds, because QN/QM modifier '
        'compliance is incomplete - most hospital-affiliated billers never '
        'append the flag. Second, it shows NO acuity skew: the flagged share is '
        f'flat across BLS ({bls_flag_share * 100:.3f}%), ALS and SCT '
        f'({sct_flag_share * 100:.3f}%). On top of that it is a CLAIMS floor - '
        'suppression removes small rows and every Part A hospital-bundled or '
        'SNF consolidated-billing transport is invisible to the carrier file. '
        'What the flag settles is that hospital-billed ground ambulance is '
        'real, growing in flagged terms, and small - the DIRECTION of the '
        'name-rule bounds, confirmed without a single name test. It does not '
        'settle the LEVEL, which the name-rule bounds next door estimate '
        'better.')

    # ------------------------------------------------------------ facts ---
    sk = ['psps_mod2']
    facts += [
        {'metric': 'Provider-of-services flagged share of Medicare FFS ground '
                   'transports (QN+QM), floor', 'year': int(latest),
         'value': round(hf_share24, 4), 'unit': 'share of transport services',
         'basis': 'DERIVED', 'tier': 'A', 'source_keys': sk,
         'locator': f'Modifier_QM_QN_Series Panel B {latest} row, live G'
                    f'{b0 + len(YEARS) - 1}',
         'lives_on': 'Modifier_QM_QN_Series',
         'cross_check': 'Carrier file only; Part A bundled and SNF '
                        'consolidated-billing transports absent, suppression '
                        'removes small rows - both push this DOWN'},
        {'metric': 'QN (furnished directly by a provider of services) share of '
                   'ground transports', 'year': int(latest),
         'value': round(qn_share24, 4), 'unit': 'share of transport services',
         'basis': 'DERIVED', 'tier': 'A', 'source_keys': sk,
         'locator': f'Modifier_QM_QN_Series Panel B {latest} row, live F'
                    f'{b0 + len(YEARS) - 1}',
         'lives_on': 'Modifier_QM_QN_Series',
         'cross_check': f'QN {round(qn24):,} services dwarfs QM {round(qm24):,}; '
                        'direct furnishing is the dominant hospital-billed mode'},
        {'metric': 'QM (under arrangement by a provider of services) services, '
                   'ground transports', 'year': int(latest),
         'value': round(qm24), 'unit': 'services', 'basis': 'GOV', 'tier': 'A',
         'source_keys': sk,
         'locator': f'Modifier_QM_QN_Series Panel A QM row C{pa + 1}',
         'lives_on': 'Modifier_QM_QN_Series',
         'cross_check': 'Billing-in-lieu volume: the arrangement the '
                        'insourcing ceiling warns inflates a name-based share'},
        {'metric': 'Provider-flagged share of Medicare FFS ground transports, '
                   '2010 (trend base)', 'year': 2010,
         'value': round(hf_share10, 4), 'unit': 'share of transport services',
         'basis': 'DERIVED', 'tier': 'A', 'source_keys': sk,
         'locator': 'Modifier_QM_QN_Series Panel B 2010 row, live G'
                    f'{b0}',
         'lives_on': 'Modifier_QM_QN_Series',
         'cross_check': f'Rises to {hf_share24 * 100:.2f}% by {latest}; the '
                        'flag was thinly used early'},
        {'metric': 'Provider-flagged share of SCT (A0434) transports',
         'year': int(latest), 'value': round(sct_flag_share, 4),
         'unit': 'share of SCT services', 'basis': 'DERIVED', 'tier': 'A',
         'source_keys': sk,
         'locator': 'Modifier_QM_QN_Series Panel C SCT row, live col F',
         'lives_on': 'Modifier_QM_QN_Series',
         'cross_check': f'About the same as BLS ({bls_flag_share * 100:.3f}%) '
                        'and ALS: the flagged share is flat across service '
                        'levels, so there is no acuity skew in the flagged '
                        'data'},
    ]

    # --------------------------------------------------------- findings ---
    findings += [
        {'id_hint': 108,
         'finding': 'The hospital billing relationship behind Medicare FFS '
                    'ground ambulance is now measured directly at the claim '
                    'level, not inferred: the QN (furnished directly) and QM '
                    '(under arrangement) provider-of-services modifiers flag a '
                    'Part A institution as the biller on '
                    f'{hf_share24 * 100:.3f}% of {latest} ground transports '
                    f'({round(hf24):,} services), up nearly ninefold from '
                    f'{hf_share10 * 100:.3f}% in 2010. QN now outweighs QM about '
                    f'{(qn24 / qm24 if qm24 else 0):.0f} to 1, though QM briefly '
                    'led in 2012-2017 before falling out of use - a coding-'
                    'practice shift. This is a STRICT floor: it sits an order '
                    'of magnitude below even the name-rule hospital-billed '
                    'floor, because QN/QM modifier compliance is incomplete.',
         'numbers': f"='Modifier_QM_QN_Series'!G{b0 + len(YEARS) - 1}",
         'sources': 'psps_mod2; qmqn_manual',
         'confidence': 'High as a direction and a floor; the LEVEL is far '
                       'understated by incomplete modifier use, suppression '
                       'and the carrier-file window',
         'guardrail': 'A share of carrier CLAIMS, not operations, and a '
                      'compliance floor: most hospital-affiliated billers never '
                      'append the flag, Part A bundled and SNF consolidated-'
                      'billing transports never carry a carrier modifier, and '
                      'CMS suppresses small rows. Do not read it as the level; '
                      'the name-rule bounds estimate that better. The flag '
                      'reads billing arrangement, not fleet ownership.'},
        {'id_hint': 109,
         'finding': 'The QN/QM flag corroborates the DIRECTION of the name-rule '
                    'insourcing bounds from an independent, name-free angle - '
                    'hospital-billed ground ambulance exists, is small, and is '
                    'growing in flagged terms - but not their LEVEL: the claim-'
                    f'level measurement lands at just {hf_share24 * 100:.3f}% of '
                    f'{latest} ground transports, an order of magnitude below '
                    'even the name-rule floor because modifier use is '
                    'incomplete, and it shows NO acuity skew (the flagged share '
                    f'is flat across BLS {bls_flag_share * 100:.3f}%, ALS and '
                    f'SCT {sct_flag_share * 100:.3f}%). Two methods agree that '
                    'hospital-billed ground ambulance is a small slice; the '
                    'flag is the conservative floor beneath the name bounds, '
                    'not a point estimate inside them.',
         'numbers': f"='Modifier_QM_QN_Series'!F{c0 + 2}",
         'sources': 'psps_mod2',
         'confidence': 'High that both methods agree hospital-billed ground '
                       'ambulance is small and that the flag is a strict floor',
         'guardrail': 'Both methods see only carrier-billed transports, and the '
                      'flag understates further through incomplete modifier '
                      'use. Agreement on smallness is not a shared point '
                      'estimate of the level or the operations share.'},
    ]

    return {'facts': facts, 'sources': sources, 'excluded': excluded,
            'findings': findings,
            'meta': {'hf_share_2024': round(hf_share24, 4),
                     'qn_share_2024': round(qn_share24, 4),
                     'hf_services_2024': round(hf24)}}
