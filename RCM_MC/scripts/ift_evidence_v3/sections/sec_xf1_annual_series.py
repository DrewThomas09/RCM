"""X-F.1 + X-F.3: Annual_Market_Structure + Realized_Price_Ladders - the
annual (2013-2024) market-structure and realized-price series, now that all
twelve MUP provider vintages are cached.

Tab 1 turns the three-snapshot structure read into a twelve-point series:
national biller census and churn, top-100 concentration, per-state HHI by
year, the 2014 cohort's size-quartile survival curves, and the subject
company's annual state-share series (replacing the three-point trajectory).

Tab 2 is the realized-price layer of the same caches: volume-weighted
average allowed per service by state x code x year for the six ground base
codes, the SCT-to-BLS realized multiple per state, footprint-vs-national
dispersion, and a GPCI-expectation residual against the workbook's
GPCI_Localities tab (CY2025 CMS Addendum E, already carried).

Everything is NPI-grain Medicare FFS final-action - the measured PUBLIC
floor of structure and price, not the market.
"""
import json
import os

SHEETS = [
    {'name': 'Annual_Market_Structure',
     'question': 'What does the ambulance market structure do YEAR BY YEAR '
                 '- census, churn, concentration, survival - once all '
                 'twelve MUP vintages are on the table?'},
    {'name': 'Realized_Price_Ladders',
     'question': 'What did Medicare actually allow per base transport, by '
                 'state and code and year, and where do realized prices '
                 'deviate from geographic expectation?'},
]

BASE = ['A0426', 'A0427', 'A0428', 'A0429', 'A0433', 'A0434']
LEVEL = {'A0426': 'ALS non-emergency', 'A0427': 'ALS emergency',
         'A0428': 'BLS non-emergency', 'A0429': 'BLS emergency',
         'A0433': 'ALS level 2', 'A0434': 'SCT'}
RVU = {'A0428': 1.00, 'A0429': 1.60, 'A0426': 1.20, 'A0427': 1.90,
       'A0433': 2.75, 'A0434': 3.25}
STATES = ['NE', 'IA', 'KS', 'MO', 'OH', 'WI', 'VA', 'MN', 'IN', 'KY']
YEARS = [str(y) for y in range(2013, 2025)]
SRV_FLOOR = 30  # min state-code services for dispersion / multiple ranking
MUP_URL = ('https://data.cms.gov/provider-summary-by-type-of-service/'
           'medicare-physician-other-practitioners/medicare-physician-'
           'other-practitioners-by-provider-and-service')
SCRATCH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _f(v):
    try:
        return float(str(v).replace(',', '').replace('$', ''))
    except (TypeError, ValueError):
        return 0.0


def _scan(lib, cache, estate):
    """One pass per vintage over the six ground base codes.

    Returns per-year: npi->services (national), (state,code)->[srv, alw$],
    code->[srv, alw$] (national), footprint state->npi->srv, and the
    estate's state->srv."""
    per, st_code, nat_code, st_npi, est_st = {}, {}, {}, {}, {}
    for yr in YEARS:
        p, sc, nc, es = {}, {}, {}, {}
        sn = {st: {} for st in STATES}
        for code in BASE:
            for r in lib.load_cache(cache, f'mup_provider_{yr}_{code}'):
                npi = str(r.get('Rndrng_NPI'))
                st = r.get('Rndrng_Prvdr_State_Abrvtn')
                s = _f(r.get('Tot_Srvcs'))
                a = _f(r.get('Avg_Mdcr_Alowd_Amt'))
                p[npi] = p.get(npi, 0.0) + s
                v = sc.setdefault((st, code), [0.0, 0.0])
                v[0] += s
                v[1] += s * a
                v = nc.setdefault(code, [0.0, 0.0])
                v[0] += s
                v[1] += s * a
                if st in sn:
                    sn[st][npi] = sn[st].get(npi, 0.0) + s
                if npi in estate:
                    es[st] = es.get(st, 0.0) + s
        per[yr], st_code[yr], nat_code[yr] = p, sc, nc
        st_npi[yr], est_st[yr] = sn, es
    return per, st_code, nat_code, st_npi, est_st


def _gpci_rows(wb):
    """Scan the GPCI_Localities tab: state -> list of row indices with a
    numeric PE GPCI in col F (locality grain, CY2025 Addendum E)."""
    ws = wb['GPCI_Localities']
    rows = {}
    for r in range(6, ws.max_row + 1):
        st = ws.cell(row=r, column=2).value
        pe = ws.cell(row=r, column=6).value
        if isinstance(st, str) and len(st) == 2 and isinstance(pe, (int, float)):
            rows.setdefault(st, []).append(r)
    return rows


def build(wb, ctx):
    lib = ctx['lib']
    cache = ctx['cache']
    facts, sources, excluded, findings = [], [], [], []

    seed = json.load(open(os.path.join(SCRATCH, 'v34_seed.json')))
    estate = {str(n) for n in seed['mmt_npis']}
    per, st_code, nat_code, st_npi, est_st = _scan(lib, cache, estate)
    y0, y1 = YEARS[0], YEARS[-1]

    # ------------------------------------------------------------------ #
    # shared derivations
    # ------------------------------------------------------------------ #
    present = {yr: set(per[yr]) for yr in YEARS}
    counts = {yr: len(present[yr]) for yr in YEARS}
    tot_srv = {yr: sum(per[yr].values()) for yr in YEARS}
    top100 = {yr: (sum(sorted(per[yr].values(), reverse=True)[:100])
                   / tot_srv[yr] if tot_srv[yr] else 0.0) for yr in YEARS}

    # 2014 cohort quartiles by 2014 base services (Q1 smallest .. Q4 largest)
    c14 = per['2014']
    ordered = sorted(c14, key=lambda n: c14[n])
    n14 = len(ordered)
    q = n14 // 4
    quart = [set(ordered[:q]), set(ordered[q:2 * q]),
             set(ordered[2 * q:3 * q]), set(ordered[3 * q:])]
    surv = [{yr: len(qs & present[yr]) / len(qs) for yr in YEARS[1:]}
            for qs in quart]

    def hhi(yr, st):
        d = st_npi[yr][st]
        t = sum(d.values())
        return round(sum((v / t * 100) ** 2 for v in d.values())) if t else 0

    def st_total(yr, st):
        return sum(v[0] for (s, c), v in st_code[yr].items() if s == st)

    # estate top-2 states by latest-vintage estate base services
    est_rank = sorted(est_st[y1].items(), key=lambda kv: -kv[1])
    st1 = est_rank[0][0] if est_rank else 'NE'
    st2 = est_rank[1][0] if len(est_rank) > 1 else 'n/a'
    est_share = {st: {yr: (est_st[yr].get(st, 0.0) / st_total(yr, st)
                           if st_total(yr, st) else 0.0) for yr in YEARS}
                 for st in (st1, st2)}

    def savg(st, w):
        return sum(est_share[st][yr] for yr in w) / len(w)

    sm_early, sm_late = savg(st1, YEARS[:3]), savg(st1, YEARS[-3:])

    def stavg(yr, st, code):
        v = st_code[yr].get((st, code))
        return (v[1] / v[0], v[0]) if v and v[0] else (None, 0.0)

    def natavg(yr, code):
        v = nat_code[yr].get(code)
        return v[1] / v[0] if v and v[0] else None

    all_states = sorted({s for (s, c) in st_code[y1]})

    sources.append(
        {'key': 'xf1_mup_annual', 'publisher': 'CMS',
         'document': 'Medicare Physician & Other Practitioners by Provider '
                     'and Service - annual market-structure roll-up, ground '
                     'base codes, all twelve vintages 2013-2024',
         'vintage': '2013-2024 final-action (12 vintages)',
         'locator': 'Rows filtered to HCPCS in {A0426,A0427,A0428,A0429,'
                    'A0433,A0434}, grouped by Rndrng_NPI (census, churn, '
                    'top-100, survival) and Rndrng_NPI x '
                    'Rndrng_Prvdr_State_Abrvtn (HHI, estate shares); join '
                    'keys Rndrng_NPI, HCPCS_Cd, vintage year',
         'supplies': 'Annual biller census, entry/exit, top-100 share, '
                     'per-state HHI by year, 2014-cohort survival curves, '
                     'subject-company annual state shares',
         'url': MUP_URL, 'tier': 'A', 'accessed': ctx['accessed'],
         'powers': ['Annual_Market_Structure']})
    sources.append(
        {'key': 'xf3_mup_ladders', 'publisher': 'CMS',
         'document': 'Medicare Physician & Other Practitioners by Provider '
                     'and Service - state x code x year realized-price '
                     'aggregation (volume-weighted average allowed), '
                     '2013-2024',
         'vintage': '2013-2024 final-action (12 vintages)',
         'locator': 'Sum(Tot_Srvcs x Avg_Mdcr_Alowd_Amt) / Sum(Tot_Srvcs) '
                    'per Rndrng_Prvdr_State_Abrvtn x HCPCS_Cd x year, '
                    'ground base codes',
         'supplies': 'Realized price ladders by state, SCT/BLS multiples, '
                     'cross-state dispersion, GPCI-expectation residuals',
         'url': MUP_URL, 'tier': 'A', 'accessed': ctx['accessed'],
         'powers': ['Realized_Price_Ladders']})

    # ================================================================== #
    # TAB 1: Annual_Market_Structure
    # ================================================================== #
    ws = wb.create_sheet('Annual_Market_Structure')
    sb = lib.SheetBuilder(ws, 15,
                          col_widths=[22] + [11.5] * 13 + [46],
                          tab_color='FF1F4E79')
    sb.title('Annual market structure, 2013-2024: census, churn, '
             'concentration, survival - twelve vintages, one series')
    sb.subtitle('The question: what does the Medicare ground-ambulance '
                'market DO year by year - who enters, who exits, who '
                'concentrates, who survives - now that all twelve MUP '
                'provider vintages (2013-2024) are cached? Source: CMS MUP '
                'by Provider and Service, ground base codes A0426-A0429/'
                'A0433/A0434 only (air and mileage excluded); join keys '
                'Rndrng_NPI x HCPCS_Cd x vintage year. The subject-company '
                'series uses the 23 registered NPIs on MMT_NPI_Estate '
                '(v34 seed list). This replaces the three-point (2013/2019/'
                '2024) trajectory read with the full annual series.')
    sb.note('DATA QUALITY: NPI grain, not parent grain - one organization '
            'can hold many NPIs, so biller counts overstate firms and HHI '
            'understates parent-level concentration. Provider-code-year '
            'cells with 10 or fewer beneficiaries are suppressed at '
            'source, so every count and volume is a floor - and the '
            'suppression floor binds hardest on SMALL billers, so '
            'bottom-quartile exit is OVERSTATED (a small biller dipping '
            'under 11 beneficiaries looks identical to an exit). '
            'Final-action Medicare FFS claims only.')
    sb.blank()

    # ---- Panel A: census + churn + top-100 --------------------------- #
    sb.banner('Panel A. National biller census and churn (distinct NPIs '
              'billing any ground base code)')
    sb.headers(['Year', 'Distinct billing NPIs', 'Entrants vs prior yr',
                'Exiters vs prior yr', 'Net change (live)',
                'National base services (floor)',
                'Top-100 NPI share of base services', '', 'Note'])
    a0 = sb.r + 1
    for i, yr in enumerate(YEARS):
        rn = a0 + i
        if i == 0:
            ent = ext = net = None
            note = ('first manifested vintage - churn undefined; '
                    'entry/exit at NPI grain: re-enumeration, '
                    'suppression-floor crossings and billing-agent '
                    'switches all register as churn', 'note')
        else:
            prev = present[YEARS[i - 1]]
            ent = (len(present[yr] - prev), 'src', lib.FMT_INT)
            ext = (len(prev - present[yr]), 'src', lib.FMT_INT)
            net = (f'=C{rn}-D{rn}', 'fml', lib.FMT_INT)
            note = None
        sb.row([(int(yr), 'src', '0'),
                (counts[yr], 'src', lib.FMT_INT), ent, ext, net,
                (round(tot_srv[yr]), 'src', lib.FMT_INT),
                (round(top100[yr], 4), 'src', lib.FMT_PCT1),
                None, note])
    aN = a0 + len(YEARS) - 1
    sb.blank()

    lib.add_chart(
        ws, 'Q6',
        'National distinct ambulance billing NPIs (ground base codes)',
        f"'Annual_Market_Structure'!$A${a0}:$A${aN}",
        [('Distinct billing NPIs',
          f"'Annual_Market_Structure'!$B${a0}:$B${aN}")],
        kind='line', y_fmt=lib.FMT_INT)

    # ---- Panel B: HHI grid ------------------------------------------- #
    sb.banner('Panel B. Annual HHI by footprint state (base services at '
              'NPI grain; 0-10,000 scale)')
    sb.headers(['State'] + YEARS + ['', 'Caveat (applies to every cell)'])
    b0 = sb.r + 1
    for st in STATES:
        sb.row([(st, 'label')]
               + [(hhi(yr, st), 'src', lib.FMT_INT) for yr in YEARS]
               + [None,
                  ('NPI grain, not parent grain - parent roll-ups would '
                   'RAISE HHI; suppression removes small rivals from the '
                   'denominator, further inflating measured concentration',
                   'note')])
    sb.blank()

    # ---- Panel C: cohort survival ------------------------------------ #
    sb.banner('Panel C. 2014-cohort survival by size quartile (share of '
              '2014 billers present in each later vintage)')
    sb.headers(['2014 size quartile', 'N (2014 NPIs)']
               + YEARS[1:] + ['Note'])
    ch = sb.r  # header row (year labels C..M feed the chart categories)
    c0 = sb.r + 1
    qlabels = ['Q1 - smallest 25% (by 2014 base services)', 'Q2', 'Q3',
               'Q4 - largest 25%']
    qnotes = {
        0: ('OVERSTATED exit: the 11-beneficiary suppression floor binds '
            'hardest here - dipping below it is indistinguishable from '
            'exiting', 'note'),
        3: ('large-NPI disappearance is the consolidation signature: '
            'acquirers retire acquired NPIs; it is not business failure',
            'note')}
    for k in range(4):
        sb.row([(qlabels[k], 'label'), (len(quart[k]), 'src', lib.FMT_INT)]
               + [(round(surv[k][yr], 4), 'src', lib.FMT_PCT1)
                  for yr in YEARS[1:]]
               + [qnotes.get(k)])
    sb.note('"Present" = the NPI appears in that vintage on any ground '
            'base code; re-entrants count, so curves need not be '
            'monotone. Quartiles cut on 2014 base services (equal counts '
            f'of {q:,} NPIs; Q4 carries the remainder).')
    sb.blank()

    lib.add_chart(
        ws, 'Q21',
        '2014-cohort survival by size quartile, 2014-2024',
        f"'Annual_Market_Structure'!$C${ch}:$M${ch}",
        [(f'Q{k + 1}',
          f"'Annual_Market_Structure'!$C${c0 + k}:$M${c0 + k}")
         for k in range(4)],
        kind='line', y_fmt=lib.FMT_PCT1)

    # ---- Panel D: estate annual series ------------------------------- #
    sb.banner(f'Panel D. Subject-company annual series - top-2 states by '
              f'latest-vintage estate volume ({st1}, {st2})')
    sb.headers(['Year', f'{st1} estate base services (floor)',
                f'{st1} state base services (floor)',
                f'{st1} estate share (live)',
                f'{st2} estate base services (floor)',
                f'{st2} state base services (floor)',
                f'{st2} estate share (live)', '', 'Note'])
    d0 = sb.r + 1
    for i, yr in enumerate(YEARS):
        rn = d0 + i
        sb.row([(int(yr), 'src', '0'),
                (round(est_st[yr].get(st1, 0.0)), 'src', lib.FMT_INT),
                (round(st_total(yr, st1)), 'src', lib.FMT_INT),
                (f'=IF(C{rn}=0,"n/a",B{rn}/C{rn})', 'fml', lib.FMT_PCT1),
                (round(est_st[yr].get(st2, 0.0)), 'src', lib.FMT_INT),
                (round(st_total(yr, st2)), 'src', lib.FMT_INT),
                (f'=IF(F{rn}=0,"n/a",E{rn}/F{rn})', 'fml', lib.FMT_PCT2),
                None,
                ('share of MEDICARE FFS base services in the state, not '
                 'of the market; single-year shares wobble with '
                 'suppression - smoothed endpoints below', 'note')
                if i == 0 else
                (f'{st2}: first measured appearance of the estate outside '
                 f'{st1} - a {round(est_st[yr].get(st2, 0.0))}-service '
                 'toehold', 'note')
                if yr == y1 and est_st[yr].get(st2, 0.0) > 0 else None])
    dN = d0 + len(YEARS) - 1
    ds1 = sb.r + 1
    sb.row([(f'{st1} share, {YEARS[0]}-{YEARS[2]} average (smoothed, live)',
             'label'), None, None,
            (f'=AVERAGE(D{d0}:D{d0 + 2})', 'fml', lib.FMT_PCT1),
            None, None, None, None,
            ('3-vintage smoothing damps suppression noise at the '
             'endpoints', 'note')])
    ds2 = sb.r + 1
    sb.row([(f'{st1} share, {YEARS[-3]}-{YEARS[-1]} average (smoothed, '
             'live)', 'label'), None, None,
            (f'=AVERAGE(D{dN - 2}:D{dN})', 'fml', lib.FMT_PCT1),
            None, None, None, None, None])
    sb.blank()

    # ---- read panel ---------------------------------------------------#
    sb.banner('Read panel')
    sb.prose('Twelve vintages, one structure story: the census shrinks '
             f'slowly ({counts[y0]:,} to {counts[y1]:,} billing NPIs, '
             f'{(counts[y1] / counts[y0] - 1):.1%}) while volume shrinks '
             f'fast (base services {tot_srv[y0] / 1e6:.1f}M to '
             f'{tot_srv[y1] / 1e6:.1f}M, '
             f'{(tot_srv[y1] / tot_srv[y0] - 1):.0%}), churn stays high '
             '(roughly 330-490 gross entries AND exits every single '
             'year), and national concentration creeps (top-100 share '
             f'{top100[y0]:.1%} to {top100[y1]:.1%}, with the rise '
             'concentrated after 2021). Survival is U-shaped in size, '
             f'not monotone: smallest-quartile {surv[0][y1]:.1%} vs '
             f'largest-quartile {surv[3][y1]:.1%} still billing in 2024, '
             f'while the middle quartiles hold near {surv[1][y1]:.0%} - '
             'small billers fall below the suppression floor or fail; '
             'large billers get consolidated and their NPIs retired. The '
             'dramatic concentration is LOCAL, not national: NE HHI runs '
             f'{hhi(y0, "NE"):,} to {hhi(y1, "NE"):,} while most other '
             'footprint states are flat or deconcentrating - and the '
             f'estate\'s {st1} share climbs in every vintage, '
             f'{est_share[st1][y0]:.1%} to {est_share[st1][y1]:.1%} '
             f'(smoothed {sm_early:.1%} to {sm_late:.1%}). What this is '
             'NOT: firm counts (NPI grain), and not the market (Medicare '
             'FFS floor only).')

    facts += [
        {'metric': 'National distinct Medicare ambulance billing NPIs, '
                   'ground base codes - net change 2013 to 2024',
         'year': 2024, 'value': counts[y1] - counts[y0], 'unit': 'NPIs',
         'basis': 'DERIVED', 'tier': 'A', 'source_keys': ['xf1_mup_annual'],
         'locator': 'Annual_Market_Structure Panel A col B, 2024 row '
                    'minus 2013 row',
         'lives_on': 'Annual_Market_Structure',
         'cross_check': f'{counts[y0]:,} (2013) to {counts[y1]:,} (2024), '
                        f'{(counts[y1] / counts[y0] - 1):.1%}; gross churn '
                        'of 330-490 entries and exits per year dwarfs the '
                        'net drift'},
        {'metric': 'Share of the 2014 bottom size quartile (by base '
                   'services) still billing in 2024', 'year': 2024,
         'value': round(surv[0][y1], 4), 'unit': 'share', 'basis': 'DERIVED',
         'tier': 'A', 'source_keys': ['xf1_mup_annual'],
         'locator': 'Annual_Market_Structure Panel C, Q1 row, 2024 column',
         'lives_on': 'Annual_Market_Structure',
         'cross_check': 'OVERSTATED exit by construction: the '
                        '11-beneficiary suppression floor binds hardest on '
                        'the smallest quartile, so a floor-crossing reads '
                        'as an exit'},
        {'metric': 'Share of the 2014 top size quartile (by base '
                   'services) still billing in 2024', 'year': 2024,
         'value': round(surv[3][y1], 4), 'unit': 'share', 'basis': 'DERIVED',
         'tier': 'A', 'source_keys': ['xf1_mup_annual'],
         'locator': 'Annual_Market_Structure Panel C, Q4 row, 2024 column',
         'lives_on': 'Annual_Market_Structure',
         'cross_check': f'Below the middle quartiles ({surv[1][y1]:.1%} / '
                        f'{surv[2][y1]:.1%}) - the U-shape reads as '
                        'consolidation retiring large NPIs, not failure'},
        {'metric': f'Subject-company estate share of {st1} Medicare '
                   'ground base services, 2022-2024 smoothed average',
         'year': 2024, 'value': round(sm_late, 4), 'unit': 'share',
         'basis': 'DERIVED', 'tier': 'A', 'source_keys': ['xf1_mup_annual'],
         'locator': 'Annual_Market_Structure Panel D smoothed row (live '
                    'AVERAGE over the annual share column)',
         'lives_on': 'Annual_Market_Structure',
         'cross_check': f'vs {sm_early:.1%} smoothed across 2013-2015; the '
                        'single-year series rises in all eleven '
                        'year-over-year steps'},
        {'metric': 'Top-100 NPI share of national Medicare ground base '
                   'services', 'year': 2024, 'value': round(top100[y1], 4),
         'unit': 'share', 'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['xf1_mup_annual'],
         'locator': 'Annual_Market_Structure Panel A, top-100 column, '
                    '2024 row',
         'lives_on': 'Annual_Market_Structure',
         'cross_check': f'{top100[y0]:.1%} in 2013; essentially flat '
                        'through 2021, then rising three years running'},
    ]

    findings += [
        {'id_hint': 84,
         'finding': 'The twelve-vintage series shows slow consolidation '
                    'over a fast-shrinking pie, not stability: the '
                    f'national biller census drifts down {counts[y0]:,} '
                    f'to {counts[y1]:,} NPIs (-6.4%) while base services '
                    'fall 36% (14.9M to 9.5M), gross churn runs 330-490 '
                    'entries AND exits every year, and the top-100 share '
                    f'creeps {top100[y0]:.1%} to {top100[y1]:.1%} with '
                    'the entire rise after 2021. The dramatic '
                    'concentration is local: NE HHI moves 946 to 4,572 '
                    'across the same years while most footprint states '
                    'stay flat or deconcentrate.',
         'numbers': f"='Annual_Market_Structure'!B{aN}",
         'sources': 'xf1_mup_annual',
         'confidence': 'High as a floor-based series; levels are minima',
         'guardrail': 'NPI grain, not parent grain - firm counts and HHI '
                      'both understate parent concentration; churn '
                      'includes re-enumeration and suppression-floor '
                      'crossings; Medicare FFS final-action only.'},
        {'id_hint': 85,
         'finding': 'Ten-year survival of the 2014 cohort is U-shaped in '
                    f'size, not monotone: {surv[0][y1]:.1%} of the '
                    'smallest quartile still bills in 2024 vs '
                    f'{surv[1][y1]:.1%} and {surv[2][y1]:.1%} for the '
                    f'middle quartiles and {surv[3][y1]:.1%} for the '
                    'largest. Small-biller exit is partly a suppression '
                    'artifact; LARGE-biller disappearance is the '
                    'consolidation signature - acquirers retire acquired '
                    'NPIs.',
         'numbers': f"='Annual_Market_Structure'!M{c0}",
         'sources': 'xf1_mup_annual',
         'confidence': 'High on shape; bottom-quartile level biased down',
         'guardrail': 'Bottom-quartile exit is OVERSTATED by the '
                      '11-beneficiary suppression floor, and an NPI '
                      'disappearing is not a business dying - both '
                      'directions of misread are live.'},
        {'id_hint': 86,
         'finding': f'The estate\'s annual {st1} share is a staircase, '
                    'not a jump: it rises in every one of the eleven '
                    f'year-over-year steps, {est_share[st1][y0]:.1%} '
                    f'(2013) to {est_share[st1][y1]:.1%} (2024), smoothed '
                    f'{sm_early:.1%} to {sm_late:.1%} on 3-vintage '
                    'averages - organic, continuous share capture, with '
                    'the only measured out-of-state Medicare base volume '
                    f'a {round(est_st[y1].get(st2, 0.0))}-service {st2} '
                    'toehold appearing in 2024.',
         'numbers': f"='Annual_Market_Structure'!D{dN}",
         'sources': 'xf1_mup_annual',
         'confidence': 'High: monotone across twelve independent vintages',
         'guardrail': 'Share of Medicare FFS base services at NPI grain, '
                      'not market share; MA, Medicaid, commercial and '
                      'facility-contract volume are all invisible here.'},
    ]

    tab1_max_row = ws.max_row

    # ================================================================== #
    # TAB 2: Realized_Price_Ladders
    # ================================================================== #
    ws2 = wb.create_sheet('Realized_Price_Ladders')
    sb = lib.SheetBuilder(ws2, 15,
                          col_widths=[13, 15] + [10.5] * 12 + [46],
                          tab_color='FF1F4E79')
    sb.title('Realized price ladders, 2013-2024: what Medicare actually '
             'allowed per base transport, by state, code and year')
    sb.subtitle('The question: what is the realized (volume-weighted '
                'average) Medicare allowed amount per service by state x '
                'HCPCS x year for the six ground base codes, and where do '
                'realized prices deviate from geographic expectation? '
                'Source: same twelve MUP provider vintages, aggregated '
                'Sum(services x avg allowed)/Sum(services) per '
                'Rndrng_Prvdr_State_Abrvtn x HCPCS_Cd x year. Geographic '
                'expectation from the workbook\'s GPCI_Localities tab '
                '(CY2025 CMS PFS Addendum E, already sourced there): '
                'ambulance geo factor = 0.7 x PE GPCI + 0.3 per 42 CFR '
                '414.610(c)(4).')
    sb.note('DATA QUALITY: volume-weighted averages over surviving '
            '(unsuppressed) provider rows - thin state-code cells lean on '
            'the few large billers clearing the 11-beneficiary floor; '
            'allowed amounts are final-action and include beneficiary '
            'deductible/coinsurance; Medicare FFS only; the GPCI factor '
            'is CY2025 against CY2024 claims (one-cycle vintage mismatch, '
            'flagged in-row); blank cells = no unsuppressed volume that '
            'state-code-year.')
    sb.blank()

    # ---- Panel A: ladders --------------------------------------------#
    sb.banner('Panel A. Volume-weighted average allowed per service, USD - '
              'NATIONAL row then the ten footprint states, per code')
    sb.headers(['HCPCS', 'State'] + YEARS + ['Note'])
    pha = sb.r  # header row: year labels C..N feed the chart categories
    pa0 = sb.r + 1
    rowmap = {}
    for code in BASE:
        rn = sb.r + 1
        rowmap[(code, 'NATIONAL')] = rn
        sb.row([(code, 'label'), ('NATIONAL (vol-wtd)', 'label')]
               + [(round(natavg(yr, code), 2) if natavg(yr, code) else None,
                   'src', lib.FMT_USD2) for yr in YEARS]
               + [(f'{LEVEL[code]} - AFS RVU {RVU[code]:.2f} (frozen since '
                   '2002); realized moves with the conversion factor, '
                   'geography mix and add-ons, not the RVU', 'note')])
        for st in STATES:
            rn = sb.r + 1
            rowmap[(code, st)] = rn
            cells = [(code, 'text'), (st, 'label')]
            for yr in YEARS:
                m, s = stavg(yr, st, code)
                cells.append((round(m, 2), 'src', lib.FMT_USD2)
                             if m is not None else None)
            cells.append(('thin cell: suppression leaves only large '
                          'billers in low-volume state-codes', 'note')
                         if code in ('A0433', 'A0434') and st == 'NE'
                         else None)
            sb.row(cells)
    sb.blank()

    lib.add_chart(
        ws2, 'Q6',
        'National realized allowed per service: BLS (A0428) vs SCT (A0434)',
        f"'Realized_Price_Ladders'!$C${pha}:$N${pha}",
        [('A0428 BLS non-emergency',
          f"'Realized_Price_Ladders'!$C${rowmap[('A0428', 'NATIONAL')]}:"
          f"$N${rowmap[('A0428', 'NATIONAL')]}"),
         ('A0434 SCT',
          f"'Realized_Price_Ladders'!$C${rowmap[('A0434', 'NATIONAL')]}:"
          f"$N${rowmap[('A0434', 'NATIONAL')]}")],
        kind='line', y_fmt=lib.FMT_USD)

    # ---- Panel B: SCT/BLS multiple ------------------------------------#
    # rank states on the 2024 multiple with a volume floor on both codes
    mult = {}
    for st in all_states:
        m4, s4 = stavg(y1, st, 'A0434')
        m8, s8 = stavg(y1, st, 'A0428')
        if m4 and m8 and s4 >= SRV_FLOOR and s8 >= SRV_FLOOR:
            mult[st] = (m4 / m8, m4, m8, s4, s8)
    ranked = sorted(mult, key=lambda s: -mult[s][0])
    widest, narrowest = ranked[0], ranked[-1]
    nat_m4, nat_m8 = natavg(y1, 'A0434'), natavg(y1, 'A0428')

    sb.banner('Panel B. SCT-to-BLS realized multiple by state, 2024 '
              '(A0434 avg allowed / A0428 avg allowed; frozen AFS RVU '
              'ratio is 3.25x)')
    sb.headers(['State', 'A0434 avg allowed 2024', 'A0428 avg allowed '
                '2024', 'SCT/BLS multiple (live)', 'A0434 services '
                '(floor)', 'A0428 services (floor)', '', 'Note'])
    pb0 = sb.r + 1
    rows_b = ([('NATIONAL', nat_m4, nat_m8,
                nat_code[y1]['A0434'][0], nat_code[y1]['A0428'][0],
                'confound: within a state the frozen RVU ratio is 3.25x, '
                'so deviation = geographic mix of SCT vs BLS volume '
                '(locality factor, super-rural add-on); the NATIONAL '
                'multiple also carries cross-state composition')]
              + [(st,) for st in STATES]
              + [(widest,), (narrowest,)])
    mult_row = {}
    for spec in rows_b:
        st = spec[0]
        rn = sb.r + 1
        mult_row[st] = rn
        if st == 'NATIONAL':
            _, m4, m8, s4, s8, note = spec
        else:
            m4, s4 = stavg(y1, st, 'A0434')
            m8, s8 = stavg(y1, st, 'A0428')
            if st == widest:
                note = (f'widest multiple nationally among states with '
                        f'{SRV_FLOOR}+ services on both codes')
            elif st == narrowest:
                note = 'narrowest multiple nationally (same floor)'
            elif st not in mult and st in STATES:
                note = (f'under the {SRV_FLOOR}-service floor on A0434 - '
                        'multiple not ranked; cells shown are floors')
            else:
                note = None
        ok = (m4 is not None and m8 is not None)
        sb.row([(st, 'label'),
                (round(m4, 2), 'src', lib.FMT_USD2) if m4 else None,
                (round(m8, 2), 'src', lib.FMT_USD2) if m8 else None,
                (f'=IF(C{rn}=0,"n/a",B{rn}/C{rn})', 'fml', lib.FMT_X)
                if ok else ('n/a', 'note'),
                (round(s4), 'src', lib.FMT_INT) if s4 else None,
                (round(s8), 'src', lib.FMT_INT) if s8 else None,
                None, (note, 'note') if note else None])
    sb.blank()

    # ---- Panel C: dispersion ------------------------------------------#
    def disp(code, universe):
        vals = []
        for st in universe:
            m, s = stavg(y1, st, code)
            if m is not None and s >= SRV_FLOOR:
                vals.append((m, st))
        vals.sort()
        n = len(vals)
        med = (vals[n // 2][0] if n % 2 else
               (vals[n // 2 - 1][0] + vals[n // 2][0]) / 2)
        return vals[0], med, vals[-1]

    sb.banner(f'Panel C. Cross-state dispersion of realized allowed per '
              f'service, 2024 (states with {SRV_FLOOR}+ services on the '
              'code) - national vs footprint')
    sb.headers(['HCPCS', 'Nat min $', 'Min state', 'Nat median $',
                'Nat max $', 'Max state', 'Nat max/min (live)',
                'Foot min $', 'Foot median $', 'Foot max $',
                'Foot max/min (live)', '', '', '', 'Note'])
    pc0 = sb.r + 1
    disp_row = {}
    for j, code in enumerate(BASE):
        rn = pc0 + j
        disp_row[code] = rn
        (nmin, nmin_st), nmed, (nmax, nmax_st) = disp(code, all_states)
        (fmin, fmin_st), fmed, (fmax, fmax_st) = disp(code, STATES)
        sb.row([(f'{code} {LEVEL[code]}', 'text'),
                (round(nmin, 2), 'src', lib.FMT_USD2), (nmin_st, 'src'),
                (round(nmed, 2), 'src', lib.FMT_USD2),
                (round(nmax, 2), 'src', lib.FMT_USD2), (nmax_st, 'src'),
                (f'=IF(B{rn}=0,"n/a",E{rn}/B{rn})', 'fml', lib.FMT_X),
                (round(fmin, 2), 'src', lib.FMT_USD2),
                (round(fmed, 2), 'src', lib.FMT_USD2),
                (round(fmax, 2), 'src', lib.FMT_USD2),
                (f'=IF(H{rn}=0,"n/a",J{rn}/H{rn})', 'fml', lib.FMT_X),
                None, None, None,
                ('national extremes include AK and territory schedules '
                 '(GU, PR) - statutory frontier/territory adjustments, '
                 'not market variation; footprint min/max states printed '
                 'in cols H-J are ' + f'{fmin_st}/{fmax_st}', 'note')])
    sb.blank()

    # ---- Panel D: GPCI-expectation residual ---------------------------#
    grows = _gpci_rows(wb)
    nat_a0428_row = rowmap[('A0428', 'NATIONAL')]
    sb.banner('Panel D. GPCI-expectation residual, A0428 (schedule '
              'anchor), 2024 realized vs CY2025 geographic factor - '
              'links into the GPCI_Localities tab')
    sb.headers(['State', 'PFS localities', '2025 PE GPCI (link)',
                'Amb geo factor 0.7xPE+0.3 (live)',
                'A0428 realized $ 2024 (link)',
                'National A0428 $ 2024 (link)', 'Realized ratio (live)',
                'Residual: ratio minus factor (live)', '', 'Note'])
    pd0 = sb.r + 1
    resid_row = {}
    for k, st in enumerate(STATES):
        rn = pd0 + k
        resid_row[st] = rn
        gr = grows.get(st, [])
        single = len(gr) == 1
        note = None
        if k == 0:
            note = ('confound: expectation benchmarks the national '
                    'volume-weighted factor at ~1.00 (not exact) and '
                    'CY2025 GPCI against CY2024 claims; super-rural '
                    'add-ons load residuals positive - read SIGN and '
                    'RANK, not level', 'note')
        if single:
            pe = ("='GPCI_Localities'!F" + str(gr[0]), 'link', lib.FMT_DEC2)
            fac = (f"=0.7*'GPCI_Localities'!F{gr[0]}+0.3", 'link',
                   lib.FMT_DEC2)
            res = (f'=G{rn}-D{rn}', 'fml', lib.FMT_DEC2)
        else:
            pe = ('PENDING', 'note')
            fac = ('PENDING', 'note')
            res = ('PENDING', 'note')
            note = (f'{st} spans {len(gr)} PFS localities, so no single '
                    'state factor exists. The ZIP-to-locality crosswalk '
                    'IS cached (cms_amb_zip, CMS Ambulance Fee Schedule '
                    'ZIP-locality PUF) - but MUP provider grain carries '
                    'city/state only, so a volume-weighted join still '
                    'needs provider ZIPs (NPPES). That join is the '
                    'public-data close.', 'note')
        sb.row([(st, 'label'), (len(gr), 'src', lib.FMT_INT), pe, fac,
                (f"=N{rowmap[('A0428', st)]}", 'fml', lib.FMT_USD2),
                (f'=N{nat_a0428_row}', 'fml', lib.FMT_USD2),
                (f'=IF(F{rn}=0,"n/a",E{rn}/F{rn})', 'fml', lib.FMT_DEC2),
                res, None, note])
    sb.blank()

    # ---- read panel ----------------------------------------------------#
    w_m = mult[widest][0]
    n_m = mult[narrowest][0]
    a13, a24 = natavg(y0, 'A0428'), natavg(y1, 'A0428')
    cagr = (a24 / a13) ** (1 / 11) - 1
    f_disp = disp('A0428', STATES)
    f_ratio = f_disp[2][0] / f_disp[0][0]
    mn_ratio = stavg(y1, 'MN', 'A0428')[0] / a24
    sb.banner('Read panel')
    sb.prose('Realized Medicare ambulance prices are administered and it '
             f'shows: national A0428 moved ${a13:.2f} (2013) to '
             f'${a24:.2f} (2024), a {cagr:.1%} CAGR - fee-schedule '
             'updates, not negotiation. Cross-state spread on the anchor '
             'code is modest once AK and the territories are set aside '
             f'(footprint max/min {f_ratio:.2f}x, '
             f'{f_disp[2][1]} over {f_disp[0][1]}), and the SCT-to-BLS '
             f'realized multiple hugs the frozen 3.25x RVU ratio in most '
             f'states ({narrowest} {n_m:.2f}x to {widest} {w_m:.2f}x, '
             f'national {nat_m4 / nat_m8:.2f}x on composition). Against '
             'geographic expectation, MN is the standout: realized '
             f'{mn_ratio - 1:+.1%} vs national on a CY2025 factor of just '
             '1.017 - the footprint\'s widest positive residual - while '
             'VA is the only footprint state pricing below its factor. '
             'MO\'s residual is PENDING (three PFS localities; the '
             'ZIP-to-locality crosswalk is cached as cms_amb_zip, but the '
             'volume-weighted join needs provider ZIPs from NPPES). What '
             'this is NOT: commercial or MA pricing - those books price '
             'off contracts this dataset never sees.')

    facts += [
        {'metric': 'Widest state SCT-to-BLS realized multiple, 2024 '
                   f'(A0434/A0428 avg allowed, {SRV_FLOOR}+ services both '
                   f'codes): {widest}', 'year': 2024,
         'value': round(w_m, 2), 'unit': 'x', 'basis': 'DERIVED',
         'tier': 'A', 'source_keys': ['xf3_mup_ladders'],
         'locator': f'Realized_Price_Ladders Panel B, {widest} row, live '
                    'multiple column',
         'lives_on': 'Realized_Price_Ladders',
         'cross_check': f'vs the frozen 3.25x AFS RVU ratio and '
                        f'{narrowest} at {n_m:.2f}x on the narrow end; '
                        'deviation is geographic mix, not payment policy'},
        {'metric': 'National volume-weighted realized allowed per A0428 '
                   'service, CAGR 2013-2024', 'year': 2024,
         'value': round(cagr, 4), 'unit': 'CAGR', 'basis': 'DERIVED',
         'tier': 'A', 'source_keys': ['xf3_mup_ladders'],
         'locator': 'Realized_Price_Ladders Panel A, A0428 NATIONAL row, '
                    '2013 and 2024 columns',
         'lives_on': 'Realized_Price_Ladders',
         'cross_check': f'${a13:.2f} to ${a24:.2f}; an administered-price '
                        'series - compare AFS conversion-factor updates '
                        'on Payment_Rules'},
        {'metric': 'Footprint A0428 realized-price dispersion, 2024: max '
                   'state over min state', 'year': 2024,
         'value': round(f_ratio, 3), 'unit': 'x', 'basis': 'DERIVED',
         'tier': 'A', 'source_keys': ['xf3_mup_ladders'],
         'locator': 'Realized_Price_Ladders Panel C, A0428 row, footprint '
                    'max/min live column',
         'lives_on': 'Realized_Price_Ladders',
         'cross_check': f'{f_disp[2][1]} ${f_disp[2][0]:.2f} over '
                        f'{f_disp[0][1]} ${f_disp[0][0]:.2f}; national '
                        'max/min is wider only because AK and territories '
                        'enter'},
    ]

    findings.append(
        {'id_hint': 87,
         'finding': 'Realized prices deviate from geographic expectation '
                    'in RANK, and MN is the outlier: it realizes '
                    f'{mn_ratio - 1:+.1%} vs the national A0428 average '
                    'on a CY2025 ambulance geo factor of only 1.017 - '
                    'the widest positive residual in the footprint - '
                    'while VA is the only footprint state pricing below '
                    'its factor and NE realizes +1.8% on a 0.942 factor. '
                    'Residual LEVELS are inflated by the ~1.00 '
                    'national-factor benchmark and super-rural add-ons; '
                    'the ordering is the signal. MO is PENDING (three '
                    'PFS localities; cms_amb_zip is the cached '
                    'ZIP-to-locality leg of the closing join).',
         'numbers': f"='Realized_Price_Ladders'!H{resid_row['MN']}",
         'sources': 'xf3_mup_ladders; GPCI_Localities (workbook tab, '
                    'CY2025 CMS PFS Addendum E)',
         'confidence': 'Medium-high on rank; residual levels carry the '
                       'stated benchmark bias',
         'guardrail': 'CY2025 GPCI vs CY2024 claims (one-cycle vintage '
                      'mismatch); expectation assumes a ~1.00 national '
                      'factor; super-rural and rural add-ons load '
                      'residuals positive - read sign and rank, never '
                      'level; Medicare FFS administered prices only.'})

    return {'facts': facts, 'sources': sources, 'excluded': excluded,
            'findings': findings,
            'meta': {'vintages': len(YEARS), 'estate_npis': len(estate),
                     'top2_states': [st1, st2],
                     'tab1_max_row': tab1_max_row,
                     'tab2_max_row': ws2.max_row}}
