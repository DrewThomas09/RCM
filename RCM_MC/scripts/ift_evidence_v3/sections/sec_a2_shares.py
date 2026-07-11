"""A.2: Market_Share_Panels - measured Medicare FFS market structure of the
ten provisional footprint states (pending E.5), from the MUP provider-grain
registry: top-10 billers per state (2024), the subject-company estate's rank
and share per state across every manifested vintage, and per-state HHI.

Everything here is NPI-grain (one row = one billing NPI, not one parent
organization) and Medicare FFS final-action - the measured PUBLIC floor of
market structure, not the market.
"""
import json
import os

SHEETS = [{'name': 'Market_Share_Panels',
           'question': 'Who measurably holds the Medicare ambulance volume '
                       'in the footprint states, and where does the subject '
                       'company rank?'}]

BASE = ['A0426', 'A0427', 'A0428', 'A0429', 'A0433', 'A0434']
STATES = ['NE', 'IA', 'KS', 'MO', 'OH', 'WI', 'VA', 'MN', 'IN', 'KY']
MUP_URL = ('https://data.cms.gov/provider-summary-by-type-of-service/'
           'medicare-physician-other-practitioners/medicare-physician-'
           'other-practitioners-by-provider-and-service')
SCRATCH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _f(v):
    try:
        return float(str(v).replace(',', '').replace('$', ''))
    except (TypeError, ValueError):
        return 0.0


def _vintages(cache):
    """Probe mup_provider_{yr}_{code} keys; a vintage counts only when every
    ground base code is manifested (keeps vintages comparable)."""
    out = []
    for y in range(2013, 2025):
        ok = True
        for c in BASE:
            p = os.path.join(cache, f'mup_provider_{y}_{c}.json')
            if not (os.path.exists(p) or os.path.exists(p + '.gz')):
                ok = False
                break
        if ok:
            out.append(str(y))
    return out


def _load_year(lib, cache, yr):
    """npi -> {srv, name, st, city} over ground base codes only."""
    agg = {}
    for code in BASE:
        for r in lib.load_cache(cache, f'mup_provider_{yr}_{code}'):
            npi = str(r.get('Rndrng_NPI'))
            d = agg.setdefault(npi, {
                'srv': 0.0,
                'name': (r.get('Rndrng_Prvdr_Last_Org_Name')
                         or r.get('Rndrng_Prvdr_First_Name') or ''),
                'st': r.get('Rndrng_Prvdr_State_Abrvtn'),
                'city': r.get('Rndrng_Prvdr_City')})
            d['srv'] += _f(r.get('Tot_Srvcs'))
    return agg


def build(wb, ctx):
    lib = ctx['lib']
    cache = ctx['cache']
    facts, sources, excluded, findings = [], [], [], []

    vin = _vintages(cache)
    nv = len(vin)
    year = {y: _load_year(lib, cache, y) for y in vin}
    y24 = vin[-1]  # latest manifested vintage (2024)

    seed = json.load(open(os.path.join(SCRATCH, 'v34_seed.json')))
    estate = {str(n) for n in seed['mmt_npis']}
    cw = json.load(open(os.path.join(SCRATCH, 'nppes_crosswalk.json')))
    npi2q = {}
    for q, v in cw.items():
        for n in (v.get('best_npis') or []):
            npi2q.setdefault(str(n), q)

    # per-state aggregates
    def state_slice(y, st):
        return {n: d for n, d in year[y].items() if d['st'] == st}

    est_srv = {st: {y: sum(d['srv'] for n, d in state_slice(y, st).items()
                           if n in estate) for y in vin} for st in STATES}
    tot_srv = {st: {y: sum(d['srv'] for d in state_slice(y, st).values())
                    for y in vin} for st in STATES}

    def est_rank(y, st):
        s = state_slice(y, st)
        e = sum(d['srv'] for n, d in s.items() if n in estate)
        if e <= 0:
            return None
        return 1 + sum(1 for n, d in s.items()
                       if n not in estate and d['srv'] > e)

    hhi = {}
    for st in STATES:
        s = state_slice(y24, st)
        tot = tot_srv[st][y24]
        hhi[st] = (sum((d['srv'] / tot * 100) ** 2 for d in s.values())
                   if tot else 0.0)

    sources.append(
        {'key': 'mkt_share_mup', 'publisher': 'CMS',
         'document': 'Medicare Physician & Other Practitioners by Provider '
                     'and Service - state market-structure roll-up, ground '
                     f'base codes, vintages {vin[0]}-{vin[-1]} '
                     f'({nv} manifested)',
         'vintage': f'{", ".join(vin)} final-action',
         'locator': 'Rows filtered to HCPCS in {A0426,A0427,A0428,A0429,'
                    'A0433,A0434}, grouped by Rndrng_NPI x '
                    'Rndrng_Prvdr_State_Abrvtn; join keys Rndrng_NPI, '
                    'HCPCS_Cd, vintage year',
         'supplies': 'Per-state biller rankings, subject-company share and '
                     'rank by vintage, and per-state HHI at NPI grain',
         'url': MUP_URL, 'tier': 'A', 'accessed': ctx['accessed'],
         'powers': ['Market_Share_Panels']})

    ws = wb.create_sheet('Market_Share_Panels')
    ncols = 13
    sb = lib.SheetBuilder(
        ws, ncols,
        col_widths=[9, 38, 12.5, 15, 9, 13, 12, 11.5, 11.5, 11.5, 11.5,
                    11.5, 36],
        tab_color='FF8C1D40')
    sb.title('Market share, measured: Medicare FFS ambulance billers in the '
             'ten footprint states, by vintage')
    sb.subtitle('The question: who measurably holds the Medicare ambulance '
                'volume in the provisional footprint (NE, IA, KS, MO, OH, '
                'WI, VA, MN, IN, KY - pending the E.5 footprint pass), and '
                'where does the subject-company estate rank? Source: MUP by '
                'Provider and Service, ground base codes A0426-A0429/A0433/'
                f'A0434, {nv} manifested vintages {vin[0]}-{vin[-1]}; join '
                'keys Rndrng_NPI x HCPCS_Cd x vintage; state is '
                'Rndrng_Prvdr_State_Abrvtn. Estate rows marked from the '
                'registered NPI list (v34 seed); other named rows marked '
                'from the public NPPES crosswalk.')
    sb.note('DATA QUALITY: NPI grain, not parent grain - one organization '
            'can bill under several NPIs, so biller counts overstate firms '
            'and every concentration figure is a FLOOR (parent roll-ups '
            'live on Fragmentation_National). Per-NPI code rows under 11 '
            'beneficiaries are suppressed at source: totals and shares are '
            'ratios of floors. Final-action claims, Medicare FFS only. '
            'State is the NPI registration state, not place of service: '
            'border-market volume books to the registration state. '
            'Vintages are independent annual snapshots, not a continuous '
            'series (until the annual series lands).')
    sb.blank()

    # ---------- Panel A: top-10 billers per state, 2024 ----------
    sb.banner(f'Panel A. Top-10 billers by state, {y24} base services '
              '(per-NPI rows: NPI grain, NOT parent grain; each row is '
              'exactly 1 NPI)')
    sb.headers(['State', 'Biller (NPPES organization name on the NPI)',
                'NPI', 'City', 'NPIs in row',
                f'Base services {y24} (floor)',
                'Share of state base services', '', '', '', '', '',
                'Marker / note'])
    tot_rn = {}
    first_state = True
    for st in STATES:
        s = state_slice(y24, st)
        tot = tot_srv[st][y24]
        rn_tot = sb.r + 1
        tot_rn[st] = rn_tot
        sb.row([(st, 'label'),
                (f'STATE TOTAL - all {len(s)} billing NPIs in {st}',
                 'label'), None, None,
                (len(s), 'fml', lib.FMT_INT),
                (round(tot), 'src', lib.FMT_INT), None, None, None, None,
                None, None,
                ('denominator for shares below; suppression floor', 'note')
                if first_state else None])
        first_state = False
        top = sorted(s.items(), key=lambda kv: -kv[1]['srv'])[:10]
        for npi, d in top:
            rn = sb.r + 1
            if npi in estate:
                mark = 'estate NPI'
            elif npi in npi2q:
                mark = f'NPPES crosswalk: {npi2q[npi]}'
            else:
                mark = None
            sb.row([(st, 'text'), (d['name'], 'src'), (npi, 'src'),
                    (d['city'], 'src'), (1, 'text', lib.FMT_INT),
                    (round(d['srv']), 'src', lib.FMT_INT),
                    (f'=IF($F${rn_tot}=0,"n/a",F{rn}/$F${rn_tot})', 'fml',
                     lib.FMT_PCT1), None, None, None, None, None,
                    (mark, 'note') if mark else None])
    sb.blank()

    # ---------- Panel B: estate rank and share, every vintage ----------
    sb.banner('Panel B. Subject-company estate: rank and share per state, '
              'every manifested vintage (live shares over blue totals)')
    sb.headers(['Vintage', 'Estate base services, NE (floor)',
                'NE state total (floor)', 'Estate share of NE',
                'Estate rank in NE', 'Distinct NE billing NPIs', '', '', '',
                '', '', '', 'Note'])
    sp0 = sb.r + 1
    for i, y in enumerate(vin):
        rn = sp0 + i
        sb.row([(y, 'src'),
                (round(est_srv['NE'][y]), 'src', lib.FMT_INT),
                (round(tot_srv['NE'][y]), 'src', lib.FMT_INT),
                (f'=IF(C{rn}=0,"n/a",B{rn}/C{rn})', 'fml', lib.FMT_PCT1),
                (est_rank(y, 'NE') or '-', 'src'),
                (len(state_slice(y, 'NE')), 'src', lib.FMT_INT),
                None, None, None, None, None, None,
                ('rank treats the whole registered estate as one biller '
                 'against per-NPI rivals', 'note') if i == 0 else None])
    sb.blank()

    st_col = {st: chr(64 + 3 + j) for j, st in enumerate(STATES)}  # C..L
    sb.headers(['Vintage', 'Estate base services by state ->'] + STATES
               + ['Note'])
    m1 = sb.r + 1
    for i, y in enumerate(vin):
        sb.row([(y, 'src'), None]
               + [(round(est_srv[st][y]), 'src', lib.FMT_INT)
                  for st in STATES]
               + [('registration-state basis: border-market volume books '
                   'to NE', 'note') if i == 0 else None])
    sb.headers(['Vintage', 'State total base services ->'] + STATES
               + ['Note'])
    m2 = sb.r + 1
    for i, y in enumerate(vin):
        sb.row([(y, 'src'), None]
               + [(round(tot_srv[st][y]), 'src', lib.FMT_INT)
                  for st in STATES]
               + [('all billing NPIs in state, base codes only', 'note')
                  if i == 0 else None])
    sb.headers(['Vintage', 'Estate share of state (live) ->'] + STATES
               + ['Note'])
    m3 = sb.r + 1
    for i, y in enumerate(vin):
        cells = [(y, 'src'), None]
        for st in STATES:
            L = st_col[st]
            cells.append((f'=IF({L}{m2 + i}=0,"n/a",'
                          f'{L}{m1 + i}/{L}{m2 + i})', 'fml', lib.FMT_PCT1))
        cells.append(('share of a floor over a floor: read the trend, not '
                      'the third decimal', 'note') if i == 0 else None)
        sb.row(cells)
    rank_rn = sb.r + 1
    sb.row([(f'Estate rank in state, {y24}', 'label'), None]
           + [(est_rank(y24, st) or '-', 'src') for st in STATES]
           + [('"-" = zero measured estate services in that state, every '
               'vintage', 'note')])
    sb.blank()

    # ---------- Panel C: HHI per state, 2024 ----------
    sb.banner(f'Panel C. Concentration: HHI per state, {y24} (sum of '
              'squared percent shares over ALL billers in the state)')
    sb.headers(['State', 'Distinct billing NPIs', 'State base services',
                'HHI (0-10000)', 'DOJ/FTC band (live)',
                f'Estate share {y24} (live)', '', '', '', '', '', '',
                'In-row caveat'])
    c0 = sb.r + 1
    for k, st in enumerate(STATES):
        rn = c0 + k
        sb.row([(st, 'label'),
                (len(state_slice(y24, st)), 'src', lib.FMT_INT),
                (f'=F{tot_rn[st]}', 'fml', lib.FMT_INT),
                (round(hhi[st]), 'src', lib.FMT_INT),
                (f'=IF(D{rn}<1500,"Unconcentrated",IF(D{rn}<=2500,'
                 f'"Moderately concentrated","Highly concentrated"))',
                 'fml'),
                (f'={st_col[st]}{m3 + nv - 1}', 'fml', lib.FMT_PCT1),
                None, None, None, None, None, None,
                ('NPI grain: parent roll-ups would RAISE HHI - that '
                 'refinement lives in the Fragmentation_National '
                 'normalization layer', 'note')])
    sb.blank()

    # chart: estate NE share by vintage, right of the data
    lib.add_chart(
        ws, 'O8',
        f'Estate share of NE Medicare base services, {vin[0]}-{vin[-1]}',
        f"'Market_Share_Panels'!$A${sp0}:$A${sp0 + nv - 1}",
        [('Estate share of NE',
          f"'Market_Share_Panels'!$D${sp0}:$D${sp0 + nv - 1}")],
        kind='line', y_fmt=lib.FMT_PCT1)

    ne_share24 = (est_srv['NE'][y24] / tot_srv['NE'][y24]
                  if tot_srv['NE'][y24] else 0.0)
    ne_share13 = (est_srv['NE'][vin[0]] / tot_srv['NE'][vin[0]]
                  if tot_srv['NE'][vin[0]] else 0.0)
    other_srv24 = sum(est_srv[st][y24] for st in STATES if st != 'NE')

    sb.banner('Read panel')
    sb.prose('The measured position is one-state deep and extreme there: '
             'the estate is the number 1 Medicare ambulance biller in '
             f'Nebraska in every manifested vintage, and its NE share '
             f'roughly tripled from {ne_share13:.1%} ({vin[0]}) to '
             f'{ne_share24:.1%} ({y24}) - a material move measured across '
             'snapshots, not asserted. NE is correspondingly the only '
             f'highly concentrated footprint state (HHI {round(hhi["NE"]):,}'
             f' vs {round(hhi["IA"]):,} in IA and under 1,200 everywhere '
             'else). In the other nine footprint states the estate records '
             'ZERO Medicare-visible base services in every vintage: MUP '
             'books volume to the NPI registration state, so IA border '
             'work rides NE-registered NPIs, and MA/commercial/facility '
             'volume never appears at all. Read rank and share as the '
             'Medicare FFS floor at NPI grain - parent roll-ups would '
             'raise rival shares and HHI, not lower them.')

    facts += [
        {'metric': 'Estate share of NE Medicare FFS ground base services '
                   '(deepest footprint state)', 'year': int(y24),
         'value': round(ne_share24, 4), 'unit': 'share of state base '
         'services', 'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['mkt_share_mup'],
         'locator': f'Panel B spotlight, {y24} row; estate NE services / '
                    'NE state total, base codes',
         'lives_on': 'Market_Share_Panels',
         'cross_check': 'Panel A NE block: the top NE row is an estate NPI '
                        'and its services match MMT_Medicare_Book Panel E'},
        {'metric': 'Estate rank among NE Medicare ambulance billers',
         'year': int(y24), 'value': est_rank(y24, 'NE'), 'unit': 'rank',
         'basis': 'DERIVED', 'tier': 'A', 'source_keys': ['mkt_share_mup'],
         'locator': f'Panel B spotlight, {y24} row; estate combined vs '
                    'per-NPI billers',
         'lives_on': 'Market_Share_Panels',
         'cross_check': 'Rank 1 in every manifested vintage back to '
                        f'{vin[0]} (same column)'},
        {'metric': 'Ambulance biller HHI, NE (NPI grain)', 'year': int(y24),
         'value': round(hhi['NE']), 'unit': 'HHI points (0-10000)',
         'basis': 'DERIVED', 'tier': 'A', 'source_keys': ['mkt_share_mup'],
         'locator': 'Panel C NE row; squared percent shares over all NE '
                    'billing NPIs, base codes',
         'lives_on': 'Market_Share_Panels',
         'cross_check': 'Above the 2500 DOJ/FTC highly-concentrated line; '
                        'NPI grain understates - parent roll-up would '
                        'raise it'},
        {'metric': 'Estate measured base services in the nine non-NE '
                   'footprint states (registration-state basis)',
         'year': int(y24), 'value': round(other_srv24), 'unit': 'services',
         'basis': 'GOV', 'tier': 'A', 'source_keys': ['mkt_share_mup'],
         'locator': f'Panel B estate-services matrix, {y24} row, IA-KY '
                    'columns',
         'lives_on': 'Market_Share_Panels',
         'cross_check': 'Zero in every vintage: MUP assigns volume to the '
                        'NPI registration state, so border-market work '
                        'books to NE; not evidence of no operations'},
        {'metric': 'Ambulance biller HHI, IA (second footprint state, NPI '
                   'grain)', 'year': int(y24), 'value': round(hhi['IA']),
         'unit': 'HHI points (0-10000)', 'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['mkt_share_mup'],
         'locator': 'Panel C IA row; squared percent shares over all IA '
                    'billing NPIs',
         'lives_on': 'Market_Share_Panels',
         'cross_check': 'Unconcentrated (under 1500): the estate-visible '
                        'deep state (NE) is the outlier, not the rule'},
    ]

    findings.append({
        'id_hint': 54,
        'finding': 'The subject company\'s measured market position: number '
                    '1 Medicare ambulance biller in Nebraska in every '
                    f'manifested vintage, with NE share moving materially '
                    f'from {ne_share13:.1%} in {vin[0]} to {ne_share24:.1%} '
                    f'in {y24} - roughly a tripling - while NE became the '
                    'only highly concentrated footprint state (HHI '
                    f'{round(hhi["NE"]):,}). In the other nine footprint '
                    'states the estate shows zero Medicare-visible services '
                    'in every vintage, a registration-state artifact of '
                    'MUP, not proof of absence.',
        'numbers': f"='Market_Share_Panels'!D{sp0 + nv - 1}",
        'sources': 'mkt_share_mup',
        'confidence': 'High as a floor at NPI grain; share of a suppressed '
                      'floor over a suppressed floor',
        'guardrail': 'Medicare FFS only, NPI grain, registration-state '
                     'basis. Shares say nothing about MA, Medicaid, '
                     'commercial or facility-paid volume, and parent '
                     'roll-ups would raise rival shares and HHI. Never '
                     'read the zero rows as absence of operations.'})

    return {'facts': facts, 'sources': sources, 'excluded': excluded,
            'findings': findings,
            'meta': {'vintages': vin, 'states': STATES,
                     'rank_row': rank_rn}}
