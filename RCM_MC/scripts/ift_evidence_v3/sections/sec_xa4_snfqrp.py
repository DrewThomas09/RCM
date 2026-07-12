"""X-A.4: the SNF return-leg / bounce-back quality layer.

Skilled Nursing Facility Quality Reporting Program (SNF QRP) provider data
(CMS Provider Data Catalog, dataset fykj-qjee), two claims-based, risk-
standardized measures that bracket the post-acute return leg:
  Discharge to Community (DTC, measure S_005_02) - the share of SNF stays
    that end back in the community (a completed episode, LESS future
    transport), and
  Potentially Preventable 30-Day Post-Discharge Readmission (PPR-PD, measure
    S_004_01) - the bounce-back rate to the hospital (MORE transport: the
    SNF-to-hospital readmission leg).
A SNF with a low DTC and a high PPR is a structural transport-demand node:
its patients cycle back to the hospital rather than going home. This tab
slices the footprint states, ranks them, and names the worst-decile SNFs.
"""

SHEETS = [{'name': 'SNF_Return_Leg_Quality',
           'question': 'Which footprint SNFs bounce patients back to the '
                       'hospital (transport demand) rather than discharging '
                       'them to the community?'}]

FOOTPRINT = ['NE', 'IA', 'KS', 'MO', 'OH', 'WI', 'VA', 'MN', 'IN', 'KY']
SNAME = {'NE': 'Nebraska', 'IA': 'Iowa', 'KS': 'Kansas', 'MO': 'Missouri',
         'OH': 'Ohio', 'WI': 'Wisconsin', 'VA': 'Virginia', 'MN': 'Minnesota',
         'IN': 'Indiana', 'KY': 'Kentucky'}
WORST_N = 22          # rows shown in the named worst-decile tail


def _num(v):
    if v is None:
        return None
    s = str(v).strip()
    if s in ('', '-', 'Not Available', 'N/A', 'NA', '*'):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _median(xs):
    xs = sorted(xs)
    n = len(xs)
    if n == 0:
        return None
    m = n // 2
    return xs[m] if n % 2 else (xs[m - 1] + xs[m]) / 2.0


def _pctile(xs, p):
    xs = sorted(xs)
    n = len(xs)
    if n == 0:
        return None
    import math
    k = max(0, min(n - 1, int(math.ceil(p / 100.0 * n)) - 1))
    return xs[k]


def build(wb, ctx):
    lib = ctx['lib']
    facts, sources, findings = [], [], []
    rows = lib.load_cache(ctx['cache'], 'snf_qrp')

    # National pool + the worst-decile (highest PPR) threshold.
    natl_ppr = [_num(r.get('ppr_rsrr')) for r in rows]
    natl_ppr = [x for x in natl_ppr if x is not None]
    natl_dtc = [_num(r.get('dtc_rs_rate')) for r in rows]
    natl_dtc = [x for x in natl_dtc if x is not None]
    ppr_p90 = _pctile(natl_ppr, 90)          # worst national decile floor
    natl_med_ppr = _median(natl_ppr)
    natl_med_dtc = _median(natl_dtc)
    n_natl_snf = len({r.get('ccn') for r in rows})

    # Per-footprint-state distribution.
    st_stat = {}
    fp_recs = []
    for r in rows:
        st = (r.get('state') or '').strip().upper()
        if st not in FOOTPRINT:
            continue
        fp_recs.append(r)
        d = st_stat.setdefault(st, {'dtc': [], 'ppr': [], 'worst': 0, 'ccn': set()})
        d['ccn'].add(r.get('ccn'))
        dv = _num(r.get('dtc_rs_rate'))
        pv = _num(r.get('ppr_rsrr'))
        if dv is not None:
            d['dtc'].append(dv)
        if pv is not None:
            d['ppr'].append(pv)
            if ppr_p90 is not None and pv >= ppr_p90:
                d['worst'] += 1

    fp_ppr = [_num(r.get('ppr_rsrr')) for r in fp_recs]
    fp_ppr = [x for x in fp_ppr if x is not None]
    fp_dtc = [_num(r.get('dtc_rs_rate')) for r in fp_recs]
    fp_dtc = [x for x in fp_dtc if x is not None]
    fp_worst_total = sum(d['worst'] for d in st_stat.values())

    # Worst-decile named tail: footprint SNFs with PPR at/above the national
    # 90th percentile, ranked by PPR descending.
    worst = [r for r in fp_recs
             if _num(r.get('ppr_rsrr')) is not None
             and ppr_p90 is not None
             and _num(r.get('ppr_rsrr')) >= ppr_p90]
    worst.sort(key=lambda r: _num(r.get('ppr_rsrr')), reverse=True)

    sources.append(
        {'key': 'cms_snf_qrp', 'publisher': 'CMS',
         'document': 'Skilled Nursing Facility Quality Reporting Program - '
                     'Provider Data (CMS Provider Data Catalog)',
         'vintage': 'PDC release issued 2025-10-01, modified 2026-06-01; '
                    'claims measure window per the Start/End Date fields '
                    '(~2-year Medicare FFS claims period)',
         'locator': 'Datastore fykj-qjee, measures S_005_02 (Discharge to '
                    'Community) and S_004_01 (Potentially Preventable '
                    '30-Day Post-Discharge Readmission); risk-standardized '
                    'rate rows (DTC_RS_RATE, PPR_PD_RSRR), pivoted per CCN',
         'supplies': 'SNF discharge-to-community and rehospitalization rates '
                     'by facility and state (the return-leg quality layer)',
         'url': 'https://data.cms.gov/provider-data/dataset/fykj-qjee',
         'tier': 'A', 'accessed': ctx['accessed'],
         'powers': ['SNF_Return_Leg_Quality']})

    ws = wb.create_sheet('SNF_Return_Leg_Quality')
    sb = lib.SheetBuilder(ws, 8, tab_color='FF6B7C93',
                          col_widths=[30, 12, 15, 15, 17, 12, 12, 34])
    sb.title('SNF return-leg quality: discharge-to-community vs bounce-back '
             'rehospitalization')
    sb.subtitle('The question: which footprint SNFs send patients home '
                '(discharge to community, less future transport) versus '
                'bounce them back to the hospital (potentially preventable '
                'readmission, the SNF-to-hospital return leg = transport '
                'demand)? Source: CMS SNF Quality Reporting Program provider '
                'data (dataset fykj-qjee), risk-standardized measures S_005_02 '
                '(DTC) and S_004_01 (PPR-PD). Join key: CMS Certification '
                'Number (CCN) and state; both are national, risk-adjusted '
                'rates in percent.')
    sb.note('DATA QUALITY: these are CLAIMS-BASED, RISK-STANDARDIZED, '
            'SNF-REPORTED facility measures - not counts of transports. '
            'Transport demand is INFERRED (a readmission implies a '
            'SNF-to-hospital transport leg), not measured. CMS suppresses '
            'facilities below the minimum eligible-stay count (they arrive as '
            '"Not Available" and are dropped here). Risk standardization '
            'already adjusts for case mix, so residual variation is facility '
            'signal; the worst-decile floor is the NATIONAL 90th-percentile '
            'PPR rate. Rates mix a ~2-year claims window (Start/End Date), '
            'not a single year.')
    sb.blank()

    # ── Panel A: footprint state distribution ──
    sb.banner('Panel A. Footprint state distribution - discharge-to-community '
              'and rehospitalization (risk-standardized, percent)')
    sb.headers(['State', 'SNFs (n)', 'Median DTC rate (%)',
                'Median PPR rate (%)', 'SNFs in worst natl PPR decile',
                'Worst-decile share', '', 'Note'])
    a0 = sb.r + 1
    st_row = {}
    for st in FOOTPRINT:
        d = st_stat.get(st)
        rn = sb.r + 1
        st_row[st] = rn
        if not d or not d['ppr']:
            sb.row([(SNAME[st], 'text'), (0, 'src', lib.FMT_INT),
                    ('n/a', 'note'), ('n/a', 'note'), (0, 'src', lib.FMT_INT),
                    None, None, ('no reported SNFs', 'note')])
            continue
        n_ccn = len(d['ccn'])
        sb.row([(SNAME[st], 'src'), (n_ccn, 'src', lib.FMT_INT),
                (round(_median(d['dtc']), 1), 'src', lib.FMT_DEC1)
                if d['dtc'] else ('n/a', 'note'),
                (round(_median(d['ppr']), 1), 'src', lib.FMT_DEC1),
                (d['worst'], 'src', lib.FMT_INT),
                (f'=IF(B{rn}=0,"n/a",E{rn}/B{rn})', 'fml', lib.FMT_PCT1),
                None,
                ('higher PPR / lower DTC = more bounce-back transport'
                 if st == FOOTPRINT[0] else None, 'note')])
    # Footprint pooled + National reference
    fp_row = sb.r + 1
    sb.row([('Footprint (pooled)', 'label'),
            (len({r.get('ccn') for r in fp_recs}), 'src', lib.FMT_INT),
            (round(_median(fp_dtc), 1), 'src', lib.FMT_DEC1),
            (round(_median(fp_ppr), 1), 'src', lib.FMT_DEC1),
            (f'=SUM(E{a0}:E{a0 + len(FOOTPRINT) - 1})', 'fml', lib.FMT_INT),
            (f'=E{sb.r + 1}/B{sb.r + 1}', 'fml', lib.FMT_PCT1), None,
            ('pooled over all footprint SNFs', 'note')])
    natl_row = sb.r + 1
    sb.row([('National (all SNFs)', 'label'), (n_natl_snf, 'src', lib.FMT_INT),
            (round(natl_med_dtc, 1), 'src', lib.FMT_DEC1),
            (round(natl_med_ppr, 1), 'src', lib.FMT_DEC1),
            (len(natl_ppr) - _rank_below(natl_ppr, ppr_p90), 'src', lib.FMT_INT),
            (f'=IF(B{natl_row}=0,"n/a",E{natl_row}/B{natl_row})', 'fml',
             lib.FMT_PCT1), None,
            ('worst decile = top 10% of PPR-reporting SNFs; as a share of ALL '
             'SNFs it is lower because not every SNF reports a PPR rate '
             '(same E/B definition as the footprint rows)', 'note')])
    sb.blank()

    # ── Panel B: footprint vs national gaps (live formulas) ──
    sb.banner('Panel B. Footprint vs national gap (live formulas) - is the '
              'bounce-back worse here?')
    sb.headers(['Measure', 'Footprint median', 'National median',
                'Gap (fp - natl)', 'Read', '', '', ''])
    b_dtc = sb.r + 1
    sb.row([('Discharge to Community (higher is better)', 'text'),
            (f'=C{fp_row}', 'fml', lib.FMT_DEC1),
            (f'=C{natl_row}', 'fml', lib.FMT_DEC1),
            (f'=C{fp_row}-C{natl_row}', 'fml', lib.FMT_DEC1),
            ('negative = footprint sends fewer home', 'note'), None, None, None])
    b_ppr = sb.r + 1
    sb.row([('Potentially Preventable Readmission (lower is better)', 'text'),
            (f'=D{fp_row}', 'fml', lib.FMT_DEC1),
            (f'=D{natl_row}', 'fml', lib.FMT_DEC1),
            (f'=D{fp_row}-D{natl_row}', 'fml', lib.FMT_DEC1),
            ('positive = footprint bounces back more', 'note'), None, None, None])
    b_cnt = sb.r + 1
    sb.row([('Footprint SNFs in the worst NATIONAL PPR decile', 'label'),
            (f'=E{fp_row}', 'fml', lib.FMT_INT), None,
            (f'=E{fp_row}/E{natl_row}', 'fml', lib.FMT_PCT1),
            ('footprint share of the national worst-decile tail', 'note'),
            None, None, None])
    sb.blank()

    # ── Panel C: named worst-decile tail ──
    sb.banner(f'Panel C. Worst-decile SNFs in footprint states - highest '
              f'rehospitalization (top {WORST_N} of {len(worst)} at/above the '
              'national 90th-percentile PPR)')
    sb.headers(['SNF (provider name)', 'State', 'City', 'PPR rate (%)',
                'PPR eligible stays', 'DTC rate (%)', 'vs national', 'CCN'])
    c0 = sb.r + 1
    for r in worst[:WORST_N]:
        dtc = _num(r.get('dtc_rs_rate'))
        sb.row([((r.get('provider_name') or '').title(), 'src'),
                (r.get('state'), 'src'),
                ((r.get('citytown') or '').title(), 'src'),
                (round(_num(r.get('ppr_rsrr')), 1), 'src', lib.FMT_DEC1),
                (int(_num(r.get('ppr_volume'))) if _num(r.get('ppr_volume'))
                 is not None else None, 'src', lib.FMT_INT),
                (round(dtc, 1) if dtc is not None else 'n/a',
                 'src' if dtc is not None else 'note',
                 lib.FMT_DEC1) if dtc is not None else ('n/a', 'note'),
                (r.get('ppr_comp_perf') or '-', 'src'),
                (r.get('ccn'), 'src')])
    sb.blank()

    # ── chart + read panel ──
    lib.add_chart(ws, 'J' + str(a0),
                  'Median potentially preventable readmission rate by state',
                  f"'SNF_Return_Leg_Quality'!$A${a0}:$A${a0 + len(FOOTPRINT) - 1}",
                  [('Median PPR rate (%)',
                    f"'SNF_Return_Leg_Quality'!$D${a0}:$D${a0 + len(FOOTPRINT) - 1}")],
                  kind='bar', y_fmt='0.0')
    sb.banner('Read panel')
    sb.prose('What is measured: two risk-standardized SNF QRP claims measures '
             'across every reporting footprint-state SNF. Discharge to '
             f'community runs about {round(_median(fp_dtc), 1)}% in the '
             'footprint (national '
             f'{round(natl_med_dtc, 1)}%) and potentially preventable '
             f'readmission about {round(_median(fp_ppr), 1)}% (national '
             f'{round(natl_med_ppr, 1)}%). The tail is what matters for '
             f'transport: {fp_worst_total:,} footprint SNFs sit in the worst '
             'NATIONAL decile for rehospitalization - each is a structural '
             'bounce-back node that generates SNF-to-hospital transport '
             'demand rather than discharging patients home. Panel C names the '
             'worst of them by CCN and city so they can be joined to the '
             'corridor and hub-spoke maps. What is NOT measured: actual '
             'transport counts - a readmission implies a transport leg but '
             'the dataset carries quality rates, not trips; and managed-care '
             'or non-Medicare stays are outside the claims-based measure.')

    med_ppr_v = round(_median(fp_ppr), 2)
    facts += [
        {'metric': 'Footprint-state pooled median risk-standardized SNF '
                   'potentially preventable 30-day post-discharge readmission '
                   'rate (SNF QRP S_004_01)',
         'year': 2026, 'value': med_ppr_v, 'unit': 'percent of stays',
         'basis': 'DERIVED', 'tier': 'A', 'source_keys': ['cms_snf_qrp'],
         'locator': 'SNF_Return_Leg_Quality Panel A, Footprint pooled median '
                    'of PPR_PD_RSRR over reporting footprint SNFs',
         'lives_on': 'SNF_Return_Leg_Quality',
         'cross_check': f'National median {round(natl_med_ppr, 2)}% (Panel A '
                        'National row); risk-standardized, case-mix adjusted'},
        {'metric': 'Footprint SNFs in the worst national decile for '
                   'potentially preventable rehospitalization (bounce-back '
                   'transport-demand nodes)',
         'year': 2026, 'value': fp_worst_total, 'unit': 'SNFs',
         'basis': 'DERIVED', 'tier': 'A', 'source_keys': ['cms_snf_qrp'],
         'locator': 'SNF_Return_Leg_Quality Panel A, SUM of per-state '
                    'worst-decile counts (PPR at/above the national 90th '
                    f'percentile = {round(ppr_p90, 1)}%)',
         'lives_on': 'SNF_Return_Leg_Quality',
         'cross_check': f'Out of {len({r.get("ccn") for r in fp_recs}):,} '
                        'reporting footprint SNFs'},
    ]
    findings.append({
        'id_hint': 104,
        'finding': 'The SNF return leg is a measurable transport-demand '
                   'layer: across the footprint, the risk-standardized '
                   f'potentially preventable readmission rate is about '
                   f'{round(_median(fp_ppr), 1)}% and discharge-to-community '
                   f'about {round(_median(fp_dtc), 1)}%, and '
                   f'{fp_worst_total:,} footprint SNFs fall in the worst '
                   'NATIONAL decile for rehospitalization - each a structural '
                   'bounce-back node whose patients cycle back to the '
                   'hospital (a SNF-to-hospital transport leg) instead of '
                   'going home. Panel C names the worst of them for joining '
                   'to the corridor map.',
        'numbers': f"='SNF_Return_Leg_Quality'!E{fp_row}",
        'sources': 'cms_snf_qrp',
        'confidence': 'High on the reported rates (risk-standardized CMS '
                      'measures); the transport-demand link is an inference, '
                      'not a measured trip count',
        'guardrail': 'These are quality rates, not transports: a readmission '
                     'implies a transport leg but the magnitude of transport '
                     'demand is inferred. Suppressed (low-volume) SNFs are '
                     'excluded, and managed-care / non-Medicare stays are '
                     'outside the claims-based measure.'})

    return {'facts': facts, 'sources': sources, 'excluded': [],
            'findings': findings,
            'meta': {'footprint_snfs': len({r.get('ccn') for r in fp_recs}),
                     'worst_decile_footprint': fp_worst_total,
                     'ppr_p90_national': round(ppr_p90, 2) if ppr_p90 else None,
                     'national_snfs': n_natl_snf}}


def _rank_below(xs, thr):
    """Count of values strictly below thr (for the national worst-decile count)."""
    if thr is None:
        return 0
    return sum(1 for x in xs if x < thr)
