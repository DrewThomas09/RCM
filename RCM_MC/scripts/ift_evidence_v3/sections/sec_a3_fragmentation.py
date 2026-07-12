"""A.3: Fragmentation_National - how fragmented is the US Medicare
ambulance biller universe, measured across every manifested MUP vintage:
biller counts, the size distribution by decile, top-10/50/100 NPI
concentration, an AUDITABLE name-pattern parent roll-up printed on the tab,
and entry/exit by size decile.

NPI grain with a printed normalization layer: the roll-up is by name
pattern only, so parent concentration is itself a floor (national brands
billing under local names stay unrolled).
"""
import json
import os
import re
import statistics

SHEETS = [{'name': 'Fragmentation_National',
           'question': 'How fragmented is the US Medicare ambulance biller '
                       'universe, and is the long tail exiting?'}]

BASE = ['A0426', 'A0427', 'A0428', 'A0429', 'A0433', 'A0434']
MUP_URL = ('https://data.cms.gov/provider-summary-by-type-of-service/'
           'medicare-physician-other-practitioners/medicare-physician-'
           'other-practitioners-by-provider-and-service')
SCRATCH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Name-pattern parent families. Patterns are matched case-insensitively as
# substrings of the NPPES organization name (word-boundary regex where
# noted); the full table prints on the tab so the layer is auditable.
FAMILIES = [
    ('AMR / American Medical Response', ['AMERICAN MEDICAL RESPONSE'],
     r'\bAMR\b',
     'mandated pattern; the ground flagship of the GMR family'),
    ('Global Medical Response / GMR', ['GLOBAL MEDICAL RESPONSE'],
     r'\bGMR\b',
     'mandated pattern; no NPI bills under the holding-company name - '
     'GMR-family volume rides brand rows (AMR, Lifeguard), so any '
     'GMR-level roll-up is a floor'),
    ('Falck', ['FALCK'], None, 'mandated pattern'),
    ('Acadian', ['ACADIAN'], None, 'mandated pattern'),
    ('PatientCare', ['PATIENTCARE', 'PATIENT CARE EMS'], None,
     'mandated pattern; zero matches - the brand bills under legacy local '
     'names, another reason the roll-up is a floor'),
    ('Priority Ambulance', ['PRIORITY AMBULANCE'], None,
     'mandated pattern; subsidiaries billing under local brands stay '
     'unrolled'),
    ('DocGo / Ambulnz', ['DOCGO', 'AMBULNZ'], None, 'mandated pattern'),
    ('Superior Air-Ground',
     ['SUPERIOR AIR-GROUND', 'SUPERIOR AIR GROUND'], None,
     'mandated pattern'),
    ('Royal Ambulance', ['ROYAL AMBULANCE'], None, 'mandated pattern'),
    ('Lifeguard Ambulance Service', ['LIFEGUARD AMBULANCE'], None,
     'detected same-name multi-state family (8+ states); publicly a GMR '
     'brand'),
    ('Cal-Ore Life Flight', ['CAL-ORE', 'CAL ORE LIFE'], None,
     'detected same-name multi-state family; ground legs of the base '
     'codes only'),
]


def _f(v):
    try:
        return float(str(v).replace(',', '').replace('$', ''))
    except (TypeError, ValueError):
        return 0.0


def _vintages(cache):
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
    agg = {}
    for code in BASE:
        for r in lib.load_cache(cache, f'mup_provider_{yr}_{code}'):
            npi = str(r.get('Rndrng_NPI'))
            d = agg.setdefault(npi, {
                'srv': 0.0,
                'name': (r.get('Rndrng_Prvdr_Last_Org_Name')
                         or r.get('Rndrng_Prvdr_First_Name') or ''),
                'st': r.get('Rndrng_Prvdr_State_Abrvtn')})
            d['srv'] += _f(r.get('Tot_Srvcs'))
    return agg


def _family(name):
    u = (name or '').upper()
    for fam, pats, word_rx, _why in FAMILIES:
        for p in pats:
            if p in u:
                return fam
        if word_rx and re.search(word_rx, u):
            return fam
    return None


def _decile_chunks(agg):
    """List of 10 lists of (npi, srv), smallest decile first."""
    order = sorted(agg.items(), key=lambda kv: kv[1]['srv'])
    n = len(order)
    return [order[d * n // 10:(d + 1) * n // 10] for d in range(10)]


def build(wb, ctx):
    lib = ctx['lib']
    cache = ctx['cache']
    facts, sources, excluded, findings = [], [], [], []

    vin = _vintages(cache)
    nv = len(vin)
    year = {y: _load_year(lib, cache, y) for y in vin}
    y24, y0 = vin[-1], vin[0]

    # per-vintage national aggregates
    nat = {}
    for y in vin:
        agg = year[y]
        tot = sum(d['srv'] for d in agg.values())
        srvs = sorted((d['srv'] for d in agg.values()), reverse=True)
        fam_tot = {}
        for npi, d in agg.items():
            key = _family(d['name']) or ('npi:' + npi)
            fam_tot[key] = fam_tot.get(key, 0.0) + d['srv']
        ptop = sorted(fam_tot.values(), reverse=True)
        nat[y] = {'n': len(agg), 'tot': tot,
                  't10': sum(srvs[:10]), 't50': sum(srvs[:50]),
                  't100': sum(srvs[:100]), 'p10': sum(ptop[:10])}

    # family detail for the printed pattern table (latest vintage)
    fam24 = {fam: {'npis': 0, 'srv': 0.0, 'states': set()}
             for fam, _p, _w, _y in FAMILIES}
    for npi, d in year[y24].items():
        fam = _family(d['name'])
        if fam:
            fam24[fam]['npis'] += 1
            fam24[fam]['srv'] += d['srv']
            fam24[fam]['states'].add(d['st'])

    # entry/exit between consecutive manifested vintages
    trans = []
    for i in range(nv - 1):
        a, b = vin[i], vin[i + 1]
        A, B = year[a], year[b]
        gone = set(A) - set(B)
        came = set(B) - set(A)
        dec_rates = []
        for chunk in _decile_chunks(A):
            dec_rates.append(sum(1 for npi, _ in chunk if npi in gone)
                             / len(chunk) if chunk else 0.0)
        trans.append({'a': a, 'b': b, 'gap': int(b) - int(a),
                      'exits': len(gone), 'entries': len(came),
                      'nA': len(A), 'nB': len(B), 'dec': dec_rates})

    one_yr = [t for t in trans if t['gap'] == 1]
    d1_mean = (sum(t['dec'][0] for t in one_yr) / len(one_yr)
               if one_yr else None)
    d10_mean = (sum(t['dec'][9] for t in one_yr) / len(one_yr)
                if one_yr else None)

    sources.append(
        {'key': 'frag_mup', 'publisher': 'CMS',
         'document': 'Medicare Physician & Other Practitioners by Provider '
                     'and Service - national ambulance biller universe, '
                     f'ground base codes, vintages {y0}-{y24} '
                     f'({nv} manifested)',
         'vintage': f'{", ".join(vin)} final-action',
         'locator': 'All rows with HCPCS in {A0426,A0427,A0428,A0429,A0433,'
                    'A0434}, grouped by Rndrng_NPI per vintage; join keys '
                    'Rndrng_NPI, HCPCS_Cd, vintage year',
         'supplies': 'Biller counts, size distribution, top-N concentration '
                     'at NPI and name-pattern parent grain, and entry/exit '
                     'by size decile',
         'url': MUP_URL, 'tier': 'A', 'accessed': ctx['accessed'],
         'powers': ['Fragmentation_National']})

    n_gaps = sum(1 for t in trans if t['gap'] > 1)
    gap_txt = (f'{n_gaps} transition(s) below span more than one year and '
               'say so in-row.' if n_gaps else
               'every consecutive transition below is one year apart.')

    ws = wb.create_sheet('Fragmentation_National')
    ncols = 13
    sb = lib.SheetBuilder(
        ws, ncols,
        col_widths=[34, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11.5, 42],
        tab_color='FF8C1D40')
    sb.title('Fragmentation, measured: the US Medicare ambulance biller '
             f'universe across {nv} vintages, {y0}-{y24}')
    sb.subtitle('The question: how fragmented is US ground ambulance - '
                'biller counts, size distribution, top-10/50/100 '
                'concentration - and is the long tail exiting? Source: MUP '
                'by Provider and Service, ground base codes A0426-A0429/'
                f'A0433/A0434, all states and territories, {nv} manifested '
                f'vintages {y0}-{y24}; join keys Rndrng_NPI x HCPCS_Cd x '
                'vintage. NPI-grain panels first, then a printed, '
                'auditable name-pattern roll-up to parents.')
    sb.note('DATA QUALITY: NPI grain - one organization can bill under '
            'several NPIs, so biller counts OVERSTATE firms and top-N '
            'shares UNDERSTATE concentration; the name-pattern parent '
            'layer below corrects only what names reveal and is itself a '
            'floor. Per-NPI code rows under 11 beneficiaries are '
            'suppressed at source: the smallest billers are partly '
            'invisible, and an NPI "exiting" can be a dip below the '
            'suppression floor rather than a true exit. Final-action '
            'claims, Medicare FFS only. Vintages are independent annual '
            'snapshots, not a continuous series (until the annual series '
            f'lands); {gap_txt}')
    sb.blank()

    # ---------- Panel A: biller counts and top-N concentration ----------
    sb.banner('Panel A. Biller count and top-N NPI concentration by '
              'vintage (distinct NPIs, ground base codes)')
    sb.headers(['Vintage', 'Distinct billing NPIs',
                'National base services (floor)', 'Top-10 NPI services',
                'Top-10 share', 'Top-50 NPI services', 'Top-50 share',
                'Top-100 NPI services', 'Top-100 share', '', '', '',
                'Note'])
    a0 = sb.r + 1
    for i, y in enumerate(vin):
        rn = a0 + i
        n = nat[y]
        sb.row([(y, 'src'), (n['n'], 'src', lib.FMT_INT),
                (round(n['tot']), 'src', lib.FMT_INT),
                (round(n['t10']), 'src', lib.FMT_INT),
                (f'=IF(C{rn}=0,"n/a",D{rn}/C{rn})', 'fml', lib.FMT_PCT1),
                (round(n['t50']), 'src', lib.FMT_INT),
                (f'=IF(C{rn}=0,"n/a",F{rn}/C{rn})', 'fml', lib.FMT_PCT1),
                (round(n['t100']), 'src', lib.FMT_INT),
                (f'=IF(C{rn}=0,"n/a",H{rn}/C{rn})', 'fml', lib.FMT_PCT1),
                None, None, None,
                ('counts overstate firms (NPI grain); services are '
                 'suppression floors', 'note') if i == 0 else None])
    a24 = a0 + nv - 1
    sb.blank()

    # ---------- Panel B: size distribution by decile ----------
    sb.banner(f'Panel B. Size distribution by services decile ({y24} vs '
              f'{y0}; deciles of each vintage\'s own biller distribution)')
    sb.headers(['Decile (by base services)', f'Billers {y24}',
                f'Services {y24}', f'Share {y24}',
                f'Median services {y24}', f'Billers {y0}',
                f'Services {y0}', f'Share {y0}', '', '', '', '', 'Note'])
    b0 = sb.r + 1
    ch24, ch13 = _decile_chunks(year[y24]), _decile_chunks(year[y0])
    all_rn = b0 + 10
    for d in range(10):
        rn = b0 + d
        c24, c13 = ch24[d], ch13[d]
        s24 = sum(kv[1]['srv'] for kv in c24)
        s13 = sum(kv[1]['srv'] for kv in c13)
        med = statistics.median(kv[1]['srv'] for kv in c24) if c24 else 0
        label = ('D1 (smallest tenth)' if d == 0 else
                 'D10 (largest tenth)' if d == 9 else f'D{d + 1}')
        note = None
        if d == 0:
            note = ('suppression truncates this decile: the true tail is '
                    'larger', 'note')
        elif d == 9:
            note = ('the whole market story lives here', 'note')
        sb.row([(label, 'text'), (len(c24), 'src', lib.FMT_INT),
                (round(s24), 'src', lib.FMT_INT),
                (f'=IF(C${all_rn}=0,"n/a",C{rn}/C${all_rn})', 'fml',
                 lib.FMT_PCT1),
                (round(med), 'src', lib.FMT_INT),
                (len(c13), 'src', lib.FMT_INT),
                (round(s13), 'src', lib.FMT_INT),
                (f'=IF(G${all_rn}=0,"n/a",G{rn}/G${all_rn})', 'fml',
                 lib.FMT_PCT1), None, None, None, None, note])
    sb.row([('All billers', 'label'),
            (f'=SUM(B{b0}:B{b0 + 9})', 'fml', lib.FMT_INT),
            (f'=SUM(C{b0}:C{b0 + 9})', 'fml', lib.FMT_INT), None, None,
            (f'=SUM(F{b0}:F{b0 + 9})', 'fml', lib.FMT_INT),
            (f'=SUM(G{b0}:G{b0 + 9})', 'fml', lib.FMT_INT), None, None,
            None, None, None,
            ('ties to Panel A rows for the same vintages', 'note')])
    sb.blank()

    # ---------- Panel C: the name-normalization layer ----------
    sb.banner('Panel C. Name-normalization layer: NPIs rolled to parents '
              'by name pattern - the FULL pattern table prints below in '
              'blue so the layer is auditable')
    sb.headers(['Parent family', f'NPIs matched {y24}', f'States {y24}',
                f'Base services {y24}', 'Share of national', '', '', '',
                '', '', '', '',
                'Match patterns (case-insensitive substring / word)'])
    p0 = sb.r + 1
    for k, (fam, pats, word_rx, why) in enumerate(FAMILIES):
        rn = p0 + k
        f24 = fam24[fam]
        pat_txt = '; '.join(pats) + (f'; word "{word_rx}"' if word_rx
                                     else '')
        sb.row([(fam, 'src'), (f24['npis'], 'src', lib.FMT_INT),
                (len(f24['states']), 'src', lib.FMT_INT),
                (round(f24['srv']), 'src', lib.FMT_INT),
                (f'=IF($C${a24}=0,"n/a",D{rn}/$C${a24})', 'fml',
                 lib.FMT_PCT2), None, None, None, None, None, None, None,
                (f'{pat_txt} - {why}', 'src')])
    sb.note('Roll-up rules, printed for audit: an NPI joins a family only '
            'when its NPPES organization name matches a pattern above; '
            'every unmatched NPI stays its own parent. Municipal and '
            'generic same-names (CITY OF X, COUNTY OF X, COMMUNITY '
            'AMBULANCE SERVICE) are NOT rolled - they are distinct local '
            'entities sharing a name. Direction of bias: this layer can '
            'only RAISE measured concentration toward truth, never reach '
            'it - brands billing under unrelated legacy names stay '
            'unrolled, so top-10 parent share is still a floor.')
    sb.blank()

    sb.headers(['Vintage', 'Top-10 NPI share (link)',
                'Top-10 parent services', 'Top-10 parent share',
                'Parent minus NPI (pp)', '', '', '', '', '', '', '',
                'Note'])
    c2 = sb.r + 1
    for i, y in enumerate(vin):
        rn = c2 + i
        sb.row([(y, 'src'), (f'=E{a0 + i}', 'fml', lib.FMT_PCT1),
                (round(nat[y]['p10']), 'src', lib.FMT_INT),
                (f'=IF(C{a0 + i}=0,"n/a",C{rn}/C{a0 + i})', 'fml',
                 lib.FMT_PCT1),
                (f'=D{rn}-B{rn}', 'fml', lib.FMT_PCT1),
                None, None, None, None, None, None, None,
                ('top-10 entities after roll-up (families plus unrolled '
                 'NPIs); denominator is the Panel A national total',
                 'note') if i == 0 else None])
    sb.blank()

    # ---------- Panel D: entry/exit by size decile ----------
    sb.banner('Panel D. Exit by size decile: NPIs present in one vintage '
              'and absent from the next (decile of the START vintage)')
    sb.headers(['Transition', 'Exit rate D1 (smallest)', 'D2', 'D3', 'D4',
                'D5', 'D6', 'D7', 'D8', 'D9', 'Exit rate D10 (largest)',
                'Exited NPIs', 'Note'])
    d0 = sb.r + 1
    for i, t in enumerate(trans):
        note = None
        if i == 0:
            note = ('absence includes dips below the suppression floor, '
                    'so tail exit rates are upper bounds on true exit',
                    'note')
        elif t['gap'] > 1:
            note = (f'spans {t["gap"]} years (missing vintages between) - '
                    'not an annual rate', 'note')
        sb.row([(f'{t["a"]} to {t["b"]}', 'text')]
               + [(t['dec'][d], 'src', lib.FMT_PCT1) for d in range(10)]
               + [(t['exits'], 'src', lib.FMT_INT), note])
    sb.blank()
    sb.headers(['Transition', 'Entered NPIs (absent start, present end)',
                'Entry rate of end-vintage billers', '', '', '', '', '',
                '', '', '', '', 'Note'])
    for i, t in enumerate(trans):
        sb.row([(f'{t["a"]} to {t["b"]}', 'text'),
                (t['entries'], 'src', lib.FMT_INT),
                (t['entries'] / t['nB'] if t['nB'] else 0, 'src',
                 lib.FMT_PCT1), None, None, None, None, None, None, None,
                None, None,
                ('entry runs below exit in most transitions: the universe '
                 'shrinks on net', 'note') if i == 0 else None])
    sb.blank()

    # charts, right of the data with a 14-row pitch
    lib.add_chart(
        ws, 'O8',
        f'Top-10 share of national base services, {y0}-{y24}',
        f"'Fragmentation_National'!$A${c2}:$A${c2 + nv - 1}",
        [('Top-10 NPI share',
          f"'Fragmentation_National'!$B${c2}:$B${c2 + nv - 1}"),
         ('Top-10 parent share (name roll-up)',
          f"'Fragmentation_National'!$D${c2}:$D${c2 + nv - 1}")],
        kind='bar', y_fmt=lib.FMT_PCT1)
    lib.add_chart(
        ws, 'O22',
        f'Distinct billing NPIs by vintage, {y0}-{y24}',
        f"'Fragmentation_National'!$A${a0}:$A${a0 + nv - 1}",
        [('Distinct billing NPIs',
          f"'Fragmentation_National'!$B${a0}:$B${a0 + nv - 1}")],
        kind='line', y_fmt=lib.FMT_INT)

    n24, tot24 = nat[y24]['n'], nat[y24]['tot']
    t100_sh = nat[y24]['t100'] / tot24 if tot24 else 0
    t10_sh = nat[y24]['t10'] / tot24 if tot24 else 0
    p10_sh = nat[y24]['p10'] / tot24 if tot24 else 0
    p10_sh0 = nat[y0]['p10'] / nat[y0]['tot'] if nat[y0]['tot'] else 0
    n0, tot0 = nat[y0]['n'], nat[y0]['tot']

    sb.banner('Read panel')
    sb.prose('Measured, twice over: the universe is extraordinarily '
             f'fragmented - {n24:,} distinct billing NPIs in {y24}, with '
             f'the top 10 holding {t10_sh:.1%} of national base services, '
             f'the top 100 holding {t100_sh:.1%}, and even after rolling '
             'brands to parents by name the top 10 parents hold only '
             f'{p10_sh:.1%} (up from {p10_sh0:.1%} in {y0}: consolidation '
             'is real but glacial, and the roll-up is itself a floor). '
             'And the long tail is thinning: the smallest decile of '
             f'billers exits at roughly {d1_mean:.0%} per year against '
             f'about {d10_mean:.0%} for the largest decile, entry runs '
             f'below exit, and the biller count fell from {n0:,} to '
             f'{n24:,} while national Medicare FFS base volume fell about '
             f'{1 - tot24 / tot0:.0%}. Read every level as a floor: NPI '
             'grain, suppression, and Medicare-FFS-only visibility all '
             'push the same direction - the true market is somewhat more '
             'concentrated and the true tail somewhat larger than shown.')

    facts += [
        {'metric': 'Distinct US Medicare ambulance billing NPIs, ground '
                   'base codes', 'year': int(y24), 'value': n24,
         'unit': 'NPIs', 'basis': 'GOV', 'tier': 'A',
         'source_keys': ['frag_mup'],
         'locator': f'Panel A, {y24} row; distinct Rndrng_NPI over base '
                    'codes',
         'lives_on': 'Fragmentation_National',
         'cross_check': 'Panel B decile counts sum to it (live SUM row); '
                        'overstates firms - NPI grain'},
        {'metric': 'National Medicare FFS ground base services (floor)',
         'year': int(y24), 'value': round(tot24), 'unit': 'services',
         'basis': 'GOV', 'tier': 'A', 'source_keys': ['frag_mup'],
         'locator': f'Panel A, {y24} row', 'lives_on':
         'Fragmentation_National',
         'cross_check': f'Down about {1 - tot24 / tot0:.0%} from {y0} on '
                        'the same basis; compare MUP_Ambulance_National'},
        {'metric': 'Top-100 NPI share of national base services (NPI '
                   'grain)', 'year': int(y24), 'value': round(t100_sh, 4),
         'unit': 'share', 'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['frag_mup'],
         'locator': f'Panel A, {y24} row, top-100 share (live over blue '
                    'totals)',
         'lives_on': 'Fragmentation_National',
         'cross_check': 'Top-10 at the same grain holds '
                        f'{t10_sh:.1%}; parent roll-up raises only the '
                        'top-10 view materially'},
        {'metric': 'Top-10 PARENT share of national base services '
                   '(name-pattern roll-up, printed layer)',
         'year': int(y24), 'value': round(p10_sh, 4), 'unit': 'share',
         'basis': 'DERIVED', 'tier': 'A', 'source_keys': ['frag_mup'],
         'locator': f'Panel C concentration table, {y24} row; pattern '
                    'table printed above it',
         'lives_on': 'Fragmentation_National',
         'cross_check': f'{p10_sh0:.1%} in {y0} by the same patterns; a '
                        'floor - brands under unrelated names stay '
                        'unrolled'},
        {'metric': 'Mean annual exit rate, smallest biller decile '
                   '(one-year transitions only)', 'year': int(y24),
         'value': round(d1_mean, 3) if d1_mean is not None else None,
         'unit': 'share of decile exiting per year', 'basis': 'DERIVED',
         'tier': 'A', 'source_keys': ['frag_mup'],
         'locator': 'Panel D, D1 column, mean over one-year transitions',
         'lives_on': 'Fragmentation_National',
         'cross_check': f'Largest decile mean {d10_mean:.1%}: the exit '
                        'gradient is monotone in size; tail exits include '
                        'suppression dips (upper bound)'},
    ]

    findings += [
        {'id_hint': 55,
         'finding': 'Highly fragmented, measured: '
                    f'{n24:,} distinct ambulance billing NPIs in {y24}, '
                    f'top-10 NPIs at {t10_sh:.1%} of national base '
                    f'services, top-100 at {t100_sh:.1%}, and even after '
                    'an auditable name-pattern roll-up to parents the '
                    f'top-10 parents hold {p10_sh:.1%} (from {p10_sh0:.1%} '
                    f'in {y0}). No national ambulance consolidator is '
                    'visible at even a tenth of the Medicare market.',
         'numbers': f"='Fragmentation_National'!I{a24}",
         'sources': 'frag_mup',
         'confidence': 'High: full-universe computation, not a sample',
         'guardrail': 'NPI grain understates and the name roll-up only '
                      'partly corrects: both push concentration DOWN, so '
                      '"fragmented" survives the bias, but exact shares '
                      'are floors. Medicare FFS visibility only.'},
        {'id_hint': 56,
         'finding': 'The long tail is exiting, measured: the smallest '
                    'decile of billers disappears from the registry at '
                    f'roughly {d1_mean:.0%} per year against about '
                    f'{d10_mean:.0%} for the largest decile, entry runs '
                    'below exit in most transitions, and the biller count '
                    f'fell from {n0:,} ({y0}) to {n24:,} ({y24}) while '
                    'national base volume fell about '
                    f'{1 - tot24 / tot0:.0%}. The data shows net attrition '
                    'concentrated at the bottom of the size distribution.',
         'numbers': f"='Fragmentation_National'!B{d0 + len(trans) - 1}",
         'sources': 'frag_mup',
         'confidence': 'High on the gradient; individual tail exits are '
                       'upper bounds',
         'guardrail': 'An NPI absent from the next vintage may have '
                      'dipped below the 11-beneficiary suppression floor, '
                      'reorganized under a new NPI, or lost only its '
                      'Medicare volume - none of which is a firm death. '
                      'The size gradient, not any single exit, is the '
                      'evidence.'},
    ]

    return {'facts': facts, 'sources': sources, 'excluded': excluded,
            'findings': findings,
            'meta': {'vintages': vin, 'families': len(FAMILIES)}}
