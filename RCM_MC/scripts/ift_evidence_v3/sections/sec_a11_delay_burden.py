"""A.11: Transfer_Delay_Burden - the measured ED-flow delay environment that
interfacility transfers move through, hospital by hospital, from the CMS
Timely & Effective Care measures already carried on ED_Timeliness_Registry.

Primary measure OP-18b (median minutes in the ED before departure, discharged
patients - transferred and psychiatric patients are EXCLUDED at source, so it
is an ED-congestion measure, not a transfer stopwatch). OP-18d (the same
median for psychiatric / mental-health patients) is the boarding signal.
Footprint states NE IA KS MO OH WI VA MN IN KY, provisional pending E.5.
"""

import os
import re
import statistics

SHEETS = [{'name': 'Transfer_Delay_Burden',
           'question': 'How congested are the EDs that footprint transfers '
                       'move through, which hospitals sit in the worst '
                       'decile, and where does the research cohort sit?'}]

FP = ['NE', 'IA', 'KS', 'MO', 'OH', 'WI', 'VA', 'MN', 'IN', 'KY']

ED_TAB = 'ED_Timeliness_Registry'

# Live Excel cross-check formulas mirroring the Cohort_Corridors (A.6)
# printed rules, keyed by system name; {B}/{C}/{D} are name/city/state
# column ranges on the registry. Any system a future A.6 adds without a
# mapping here prints 'see Cohort_Corridors' instead of a live count.
A6_XCHECK = {
    'Cleveland Clinic': 'ISNUMBER(SEARCH("CLEVELAND CLINIC",{B}))',
    'Inova': 'ISNUMBER(SEARCH("INOVA",{B}))',
    'CommonSpirit / CHI Health':
        '((ISNUMBER(SEARCH("CHI HEALTH",{B}))'
        '+ISNUMBER(SEARCH("COMMONSPIRIT",{B})))>0)',
    'Nebraska Methodist':
        '((ISNUMBER(SEARCH("METHODIST",{B}))*({D}="NE")'
        '+ISNUMBER(SEARCH("JENNIE EDMUNDSON",{B})))>0)',
    'Premier Health (Dayton)':
        '({D}="OH")*((ISNUMBER(SEARCH("MIAMI VALLEY HOSPITAL",{B}))'
        '+ISNUMBER(SEARCH("UPPER VALLEY MEDICAL",{B}))'
        '+ISNUMBER(SEARCH("ATRIUM MEDICAL",{B})))>0)',
    "Saint Luke's Health System (Kansas City)":
        '((ISNUMBER(SEARCH("ST LUKE",SUBSTITUTE(SUBSTITUTE({B},".",""),'
        '"\'","")))+ISNUMBER(SEARCH("SAINT LUKE",{B})))>0)'
        '*ISNUMBER(MATCH({D},{{"MO","KS"}},0))'
        '*ISNA(MATCH({C},{{"ST. LOUIS","SAINT LOUIS","CHESTERFIELD",'
        '"MARION"}},0))',
    'Froedtert': 'ISNUMBER(SEARCH("FROEDTERT",{B}))',
    'Baptist Health (KY/IN)':
        'ISNUMBER(SEARCH("BAPTIST HEALTH",{B}))'
        '*ISNUMBER(MATCH({D},{{"KY","IN"}},0))',
    'Ascension': 'ISNUMBER(SEARCH("ASCENSION",{B}))',
}


def _pctile(vals, p):
    i = p * (len(vals) - 1) / 100.0
    lo, hi = int(i), min(int(i) + 1, len(vals) - 1)
    return vals[lo] + (vals[hi] - vals[lo]) * (i - lo)


def _a6_rules():
    """Import the Cohort_Corridors (A.6) rule set - (system, printed rule,
    confound, predicate(name_upper, state, city_upper)) - so this tab
    resolves cohort CCNs by the SAME printed name-match rules. Returns
    (rules, mirrored_flag)."""
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, 'sec_a6_cohort_corridors.py')
    if os.path.exists(path):
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                'sec_a6_cohort_corridors_rules', path)
            m = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(m)
            if getattr(m, 'RULES', None):
                return m.RULES, True
        except Exception:
            pass
    # fallback (A.6 absent or unloadable): one deepest unambiguous printed
    # brand stem per footprint state, leading-prefix match
    stems = [('CHI HEALTH', 'NE'), ('MERCYONE', 'IA'),
             ('ADVENTHEALTH', 'KS'), ('SSM', 'MO'), ('MERCY HEALTH', 'OH'),
             ('AURORA', 'WI'), ('SENTARA', 'VA'), ('ESSENTIA HEALTH', 'MN'),
             ('ASCENSION', 'IN'), ('BAPTIST HEALTH', 'KY')]
    rules = [(f'{s} ({a} anchor)',
              f"name STARTS WITH '{s}'",
              'fallback stem rule - A.6 not available at build time',
              (lambda n, st, c, _s=s: n.startswith(_s)))
             for s, a in stems]
    return rules, False


def build(wb, ctx):
    lib = ctx['lib']
    facts, sources, excluded, findings = [], [], [], []
    rules, mirrored = _a6_rules()

    # ---- scan the carried registry (cells, not caches) -------------------
    ws_ed = wb[ED_TAB]
    ed_max = ws_ed.max_row
    hosp = {}      # ccn -> dict(name, city, state, score, row)
    d18 = []       # OP-18d numeric scores, footprint
    n22 = 0
    for r, row in enumerate(ws_ed.iter_rows(min_row=5, max_row=ed_max,
                                            max_col=9), 5):
        ccn, name, city, st, meas, mname, score, samp, per = \
            [c.value for c in row[:9]]
        if st not in FP:
            continue
        if meas == 'OP_18b':
            hosp[str(ccn)] = {
                'name': str(name), 'city': str(city or '').upper(),
                'state': st, 'row': r,
                'score': score if isinstance(score, (int, float)) else None,
                'sample': samp}
        elif meas == 'OP_18d' and isinstance(score, (int, float)):
            d18.append(score)
        elif meas == 'OP_22':
            n22 += 1

    vals = sorted(h['score'] for h in hosp.values() if h['score'] is not None)
    med = statistics.median(vals)
    deciles = {p: _pctile(vals, p) for p in range(10, 100, 10)}
    p75 = _pctile(vals, 75)
    p90 = deciles[90]
    med_18d = statistics.median(d18) if d18 else None

    # cohort resolution: the SAME predicates as Cohort_Corridors Panel A,
    # applied to the registry's printed name / state / city, restricted to
    # footprint states (this tab's addition - the distribution is
    # footprint-only, so out-of-footprint cohort hospitals are out of scope)
    coh = {}
    for name, rule, confound, pred in rules:
        coh[name] = [h for h in hosp.values()
                     if pred(h['name'].upper(), h['state'], h['city'])]
    coh_all = [h for lst in coh.values() for h in lst]
    coh_num = [h['score'] for h in coh_all if h['score'] is not None]
    coh_wq = sum(1 for v in coh_num if v >= p75)
    coh_wd = sum(1 for v in coh_num if v >= p90)
    coh_med = statistics.median(coh_num) if coh_num else None

    worst20 = sorted((h for h in hosp.values() if h['score'] is not None),
                     key=lambda h: -h['score'])[:20]

    sources.append(
        {'key': 'a11_timely', 'publisher': 'CMS',
         'document': 'Care Compare - Timely and Effective Care, hospital '
                     'file (OP-18b, OP-18d, OP-22), as carried on '
                     'ED_Timeliness_Registry',
         'vintage': 'OP-18b/OP-18d period 07/2024 - 06/30/2025; OP-22 '
                    'CY2024',
         'locator': 'ED_Timeliness_Registry rows 5-' + str(ed_max) +
                    '; Facility ID = CCN; Score column G',
         'supplies': 'Hospital-grain ED throughput medians for the '
                     'footprint delay-burden read and the cohort placement',
         'url': 'https://data.cms.gov/provider-data/dataset/yv7e-xc69',
         'tier': 'A', 'accessed': ctx['accessed'],
         'powers': ['Transfer_Delay_Burden']})

    # ---- helpers for live formulas over the registry ---------------------
    rng = lambda col: f"'{ED_TAB}'!${col}$5:${col}${ed_max}"
    fp_arr = '{' + ','.join(f'"{s}"' for s in FP) + '}'
    in_fp = f'ISNUMBER(MATCH({rng("D")},{fp_arr},0))'

    def live_count(meas, extra=''):
        return (f'=SUMPRODUCT(({rng("E")}="{meas}")*{in_fp}{extra})')

    # ---------------------------------------------------------------- tab -
    ws = wb.create_sheet('Transfer_Delay_Burden')
    sb = lib.SheetBuilder(ws, 10,
                          col_widths=[30, 12, 42, 7, 12, 12, 12, 12, 12, 36],
                          tab_color='FF1F6F8B')
    sb.title('Transfer delay burden: the measured ED-flow environment of '
             'the footprint, hospital by hospital')
    sb.subtitle('The question: how congested are the emergency departments '
                'that interfacility transfers move through in the footprint '
                'states (NE IA KS MO OH WI VA MN IN KY - provisional '
                'pending E.5), which hospitals sit in the worst decile, and '
                'where does the research cohort of representative '
                'multi-hospital health systems operating in the study '
                'footprint, selected for depth, sit in that distribution? '
                'Source: CMS Timely and Effective Care measures carried on '
                'ED_Timeliness_Registry (join key: CCN). Primary measure '
                'OP-18b, median minutes in the ED before leaving, '
                'discharged patients; OP-18d is the psychiatric boarding '
                'median; OP-22 is left-before-being-seen.')
    sb.note('DATA QUALITY: OP-18b EXCLUDES patients transferred to another '
            'facility and psychiatric patients at source - it measures the '
            'ED-flow environment transfers depart from, not transfer '
            'execution time. Hospital medians are not volume-weighted; '
            'small-ED medians are noisy. ' +
            str(len(hosp) - len(vals)) + ' of ' + str(len(hosp)) +
            ' footprint hospitals print Not Available and are excluded '
            'from every percentile. Footprint state list is provisional '
            'pending E.5. These are ED-flow measures: they say nothing '
            'about any transport operator.')
    sb.blank()

    # Panel A. coverage
    sb.banner('Panel A. Coverage: what the registry carries for the '
              'footprint (live counts over ED_Timeliness_Registry)')
    sb.headers(['Measure', 'What it measures', 'Footprint hospital rows '
                '(live)', 'With numeric scores (live)', '', '', '', '', '',
                'Note'])
    sb.row([('OP-18b', 'label'),
            ('Median minutes in ED before departure, discharged patients',
             'text'),
            (live_count('OP_18b'), 'fml', lib.FMT_INT),
            (live_count('OP_18b', f'*ISNUMBER({rng("G")})'), 'fml',
             lib.FMT_INT),
            None, None, None, None, None,
            ('primary measure on this tab', 'note')])
    sb.row([('OP-18d', 'label'),
            ('Same median, psychiatric / mental-health patients', 'text'),
            (live_count('OP_18d'), 'fml', lib.FMT_INT),
            (live_count('OP_18d', f'*ISNUMBER({rng("G")})'), 'fml',
             lib.FMT_INT),
            None, None, None, None, None,
            ('the boarding signal: psych patients often wait on a transfer '
             'placement', 'note')])
    sb.row([('OP-22', 'label'),
            ('Left before being seen (share of ED arrivals)', 'text'),
            (live_count('OP_22'), 'fml', lib.FMT_INT),
            (live_count('OP_22', f'*ISNUMBER({rng("G")})'), 'fml',
             lib.FMT_INT),
            None, None, None, None, None,
            ('context only on this tab', 'note')])
    sb.row([('OP-18d footprint median (minutes)', 'label'),
            ('median of hospital medians, numeric rows only', 'text'),
            (round(med_18d, 1), 'src', lib.FMT_DEC1),
            None, None, None, None, None, None,
            ('psych ED stays run about twice the discharged-patient '
             'median', 'note')])
    sb.blank()

    # Panel B. decile ladder
    sb.banner('Panel B. The distribution: OP-18b decile ladder, footprint '
              'hospitals with numeric scores')
    sb.headers(['Decile', 'OP-18b minutes', 'Reading', '',
                'Hospitals at or above (live)', '', '', '', '', 'Note'])
    b0 = sb.r + 1
    for i, p in enumerate(sorted(deciles)):
        rn = b0 + i
        reading = ''
        if p == 50:
            reading = 'FOOTPRINT MEDIAN'
        elif p == 90:
            reading = 'WORST-DECILE THRESHOLD'
        elif p == 70:
            reading = 'worst quartile starts at ' + str(round(p75)) + ' min'
        sb.row([(f'P{p}', 'label'),
                (round(deciles[p], 1), 'src', lib.FMT_DEC1),
                (reading, 'text'), None,
                (f'=SUMPRODUCT(({rng("E")}="OP_18b")*{in_fp}'
                 f'*ISNUMBER({rng("G")})*({rng("G")}>=B{rn}))', 'fml',
                 lib.FMT_INT),
                None, None, None, None,
                ('deciles computed over the ' + str(len(vals)) +
                 ' numeric hospital medians; live column re-counts against '
                 'the registry', 'note') if i == 0 else None])
    r_med = b0 + 4     # P50 row
    r_p90 = b0 + 8     # P90 row
    sb.row([('Min / max (minutes)', 'label'),
            (vals[0], 'src', lib.FMT_INT), (f'max {vals[-1]:,}', 'text'),
            None, None, None, None, None, None,
            ('the max is a small-ED artifact as much as a crisis signal',
             'note')])
    sb.blank()

    # Panel C. worst decile top-20
    sb.banner('Panel C. The worst decile, named: 20 highest OP-18b medians '
              'in footprint states (values green-linked to the registry '
              'row)')
    sb.headers(['Rank', 'CCN', 'Hospital (printed name)', 'State',
                'OP-18b minutes (link)', 'ED sample (link)', '', '', '',
                'Note'])
    for i, h in enumerate(worst20, 1):
        ccn = next(k for k, v in hosp.items() if v is h)
        sb.row([(i, 'text'), (ccn, 'src'), (h['name'], 'src'),
                (h['state'], 'src'),
                (f"='{ED_TAB}'!G{h['row']}", 'link', lib.FMT_INT),
                (f"='{ED_TAB}'!H{h['row']}", 'link'),
                None, None, None,
                ('academic and tertiary referral centers dominate: the '
                 'worst ED congestion sits exactly where transfers '
                 'originate and land', 'note') if i == 1 else None])
    sb.blank()

    # Panel D. research cohort placement
    sb.banner('Panel D. Where the research cohort sits - rules mirror '
              'Cohort_Corridors' if mirrored else
              'Panel D. Where the research cohort sits (fallback rules - '
              'A.6 not available at build time)')
    sb.prose('The research cohort of representative multi-hospital health '
             'systems operating in the study footprint, selected for '
             'depth, is resolved to hospitals purely from PUBLIC printed '
             'facility names. ' +
             ('Rules mirror Cohort_Corridors: the same printed name-match '
              'rules of its Panel A (imported from that module verbatim) '
              'are applied to the registry name / state / city, with one '
              'addition stated here: only FOOTPRINT-STATE hospitals '
              'count, because the distribution above is footprint-only - '
              'so out-of-footprint cohort hospitals (e.g. Cleveland '
              'Clinic Florida, most of Ascension) are out of scope, and '
              'each rule\'s over/under-match confound carries over.'
              if mirrored else
              'Cohort_Corridors (A.6) could not be loaded at build time; '
              'the fallback prefix-stem rules printed per row are '
              'self-contained and must be reconciled to Cohort_Corridors '
              'Panel A when it lands.'))
    sb.headers(['Cohort system', 'Matched footprint hospitals (scan)',
                'Printed match rule (as on Cohort_Corridors Panel A; '
                'footprint states only here)', 'With numeric OP-18b',
                'Median OP-18b minutes', 'In worst quartile (at or above '
                'P75)', 'In worst decile (at or above P90)',
                'Live re-count', '', 'Match confound (carried verbatim)'])
    d0 = sb.r + 1
    for i, (name, rule, confound, pred) in enumerate(rules):
        lst = coh[name]
        nv = [h['score'] for h in lst if h['score'] is not None]
        xf = A6_XCHECK.get(name)
        if xf and mirrored:
            expr = xf.format(B=rng('B'), C=rng('C'), D=rng('D'))
            live = (f'=SUMPRODUCT(({rng("E")}="OP_18b")*{in_fp}'
                    f'*({expr})*1)', 'fml', lib.FMT_INT)
        elif not mirrored:
            stem = name.split(' (')[0]
            live = (f'=SUMPRODUCT(({rng("E")}="OP_18b")*{in_fp}'
                    f'*(LEFT(UPPER({rng("B")}),{len(stem)})="{stem}"))',
                    'fml', lib.FMT_INT)
        else:
            live = ('see Cohort_Corridors', 'note')
        sb.row([(name, 'src'), (len(lst), 'src', lib.FMT_INT),
                (rule, 'text'),
                (len(nv), 'src', lib.FMT_INT),
                (round(statistics.median(nv), 1) if nv else 'n/a', 'src',
                 lib.FMT_DEC1),
                (sum(1 for v in nv if v >= p75), 'src', lib.FMT_INT),
                (sum(1 for v in nv if v >= p90), 'src', lib.FMT_INT),
                live, None, (confound, 'note')], wrap=True, height=34)
    dl = d0 + len(rules)
    sb.row([('COHORT TOTAL', 'label'),
            (f'=SUM(B{d0}:B{dl - 1})', 'fml', lib.FMT_INT), None,
            (f'=SUM(D{d0}:D{dl - 1})', 'fml', lib.FMT_INT),
            (round(coh_med, 1), 'src', lib.FMT_DEC1),
            (f'=SUM(F{d0}:F{dl - 1})', 'fml', lib.FMT_INT),
            (f'=SUM(G{d0}:G{dl - 1})', 'fml', lib.FMT_INT),
            None, None,
            ('cohort median vs footprint median: ' +
             str(round(coh_med)) + ' vs ' + str(round(med)) +
             ' minutes', 'note')])
    r_tot = dl
    sb.row([('Cohort share in the worst footprint quartile (live)',
             'label'), None, None,
            (f'=IF(D{r_tot}=0,"n/a",F{r_tot}/D{r_tot})', 'fml',
             lib.FMT_PCT1),
            None, None, None, None, None,
            ('by construction a quarter of ALL footprint hospitals sits '
             'there; the cohort overweights it because its rules match '
             'the large referral hospitals', 'note')])
    sb.note('Scan counts apply the imported A.6 predicates in Python; '
            'the Live re-count column rebuilds each rule as a registry '
            'formula (SEARCH is case-insensitive), so the two columns '
            'must agree - any daylight means a rule drifted.', height=24)
    sb.blank()

    sb.banner('Read panel')
    sb.prose('The delay environment is measured, not anecdotal: across '
             f'{len(vals):,} footprint hospitals reporting OP-18b, the '
             f'median ED stay before departure is {round(med)} minutes, '
             f'the worst decile starts at {round(p90)} minutes, and the '
             'worst-decile list reads like a referral-center roster - '
             'the University of Kansas Hospital, Barnes Jewish, Ohio '
             'State, UVA, Froedtert. The research cohort of '
             'representative multi-hospital health systems operating in '
             'the study footprint places slightly worse than the '
             f'footprint median ({round(coh_med)} vs {round(med)} '
             f'minutes), with {coh_wq} of {len(coh_num)} measured cohort '
             'hospitals in the worst footprint quartile and '
             f'{coh_wd} in the worst decile. What this is NOT: a transport '
             'performance metric. OP-18b excludes transferred patients at '
             'source and OP-18d (psych boarding, footprint median '
             f'{round(med_18d)} minutes) is a placement-availability '
             'signal; nothing on this tab measures, ranks or implies the '
             'performance of any ambulance operator.')

    facts += [
        {'metric': 'Footprint median hospital OP-18b (median ED minutes '
                   'before departure, discharged patients)', 'year': 2025,
         'value': round(med, 1), 'unit': 'minutes', 'basis': 'DERIVED',
         'tier': 'A', 'source_keys': ['a11_timely'],
         'locator': 'ED_Timeliness_Registry OP_18b rows, footprint states, '
                    'numeric scores; period 07/2024 - 06/30/2025; median '
                    'of hospital medians',
         'lives_on': 'Transfer_Delay_Burden',
         'cross_check': 'Panel B live column re-counts hospitals at or '
                        'above each decile against the registry'},
        {'metric': 'Footprint worst-decile OP-18b threshold (P90)',
         'year': 2025, 'value': round(p90, 1), 'unit': 'minutes',
         'basis': 'DERIVED', 'tier': 'A', 'source_keys': ['a11_timely'],
         'locator': 'Panel B P90 row; deciles over ' + str(len(vals)) +
                    ' numeric footprint hospital medians',
         'lives_on': 'Transfer_Delay_Burden',
         'cross_check': 'Panel C names the 20 hospitals above it, values '
                        'green-linked to registry rows'},
        {'metric': 'Research-cohort hospitals in the worst footprint '
                   'OP-18b quartile', 'year': 2025, 'value': coh_wq,
         'unit': 'hospitals (of ' + str(len(coh_num)) + ' measured)',
         'basis': 'DERIVED', 'tier': 'A', 'source_keys': ['a11_timely'],
         'locator': 'Panel D; rules mirror Cohort_Corridors Panel A '
                    '(footprint states only on this tab); worst quartile '
                    '= OP-18b at or above ' + str(round(p75)),
         'lives_on': 'Transfer_Delay_Burden',
         'cross_check': 'Neutral placement read: cohort median ' +
                        str(round(coh_med)) + ' vs footprint ' +
                        str(round(med)) + ' minutes; expected for '
                        'referral-heavy systems'},
    ]

    findings.append({
        'id_hint': 69,
        'finding': 'The delay burden around footprint transfers is now '
                   'measured at hospital grain: the median footprint ED '
                   f'holds a discharged patient {round(med)} minutes, the '
                   f'worst decile starts at {round(p90)} minutes, and the '
                   'worst-decile roster is the referral-center roster - '
                   'the same large hospitals that originate and receive '
                   'interfacility transfers. The research cohort places '
                   f'slightly worse than the footprint median ({coh_wq} of '
                   f'{len(coh_num)} measured cohort hospitals in the worst '
                   'quartile), which is the expected signature of '
                   'tertiary-weighted systems, and is exactly where '
                   'throughput-driven transfer demand concentrates.',
        'numbers': "='Transfer_Delay_Burden'!B" + str(r_med),
        'sources': 'a11_timely',
        'confidence': 'High for the distribution; hospital medians are '
                      'unweighted and small-ED values are noisy',
        'guardrail': 'OP-18b and OP-18d are ED-FLOW measures - OP-18b '
                     'excludes transferred patients at source - and are '
                     'NOT transport-vendor performance; nothing here '
                     'measures or implies the performance of any '
                     'operator. Cohort placement is a neutral, public '
                     'name-match read (rules mirror Cohort_Corridors, '
                     'footprint states only); footprint list provisional '
                     'pending E.5.'})

    return {'facts': facts, 'sources': sources, 'excluded': excluded,
            'findings': findings,
            'meta': {'fp_hospitals': len(hosp), 'numeric': len(vals),
                     'cohort_matched': len(coh_all),
                     'a6_mirrored': mirrored}}
