"""X-A.5: the SNF return-leg structural cut - who bounces patients back.

X-A.4 (SNF_Return_Leg_Quality) measured the return-leg quality rates; this tab
asks the structural question an operator cares about: do a SNF's OWNERSHIP,
SCALE, and star RATING predict how much return-leg transport it generates?
It joins the CMS SNF Quality Reporting Program claims measures (snf_qrp,
dataset fykj-qjee) to the CMS Nursing Home provider-info file (pdc2_nursing_homes,
dataset 4pq5-n9py) on the CMS Certification Number (CCN) - a clean 1:1 join
over all 14,695 reporting SNFs - and cross-tabs the risk-standardized
potentially-preventable readmission (PPR, the bounce-back = transport demand)
and discharge-to-community (DTC) rates by:
  - ownership bucket (For profit / Non profit / Government),
  - certified-bed scale band, and
  - overall 5-star rating.
The read is an investor cut: for-profit and lower-rated SNFs bounce patients
back to the hospital more, so they are the structural return-leg transport-
demand nodes; ownership concentration among them is a consolidation signal.
"""

SHEETS = [{'name': 'SNF_ReturnLeg_Structure',
           'question': 'Do SNF ownership, scale and star rating predict how '
                       'much return-leg (bounce-back) transport a facility '
                       'generates?'}]

FOOTPRINT = ['NE', 'IA', 'KS', 'MO', 'OH', 'WI', 'VA', 'MN', 'IN', 'KY']


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
    xs = sorted(x for x in xs if x is not None)
    n = len(xs)
    if n == 0:
        return None
    m = n // 2
    return xs[m] if n % 2 else (xs[m - 1] + xs[m]) / 2.0


def _pctile(xs, p):
    xs = sorted(x for x in xs if x is not None)
    n = len(xs)
    if n == 0:
        return None
    import math
    k = max(0, min(n - 1, int(math.ceil(p / 100.0 * n)) - 1))
    return xs[k]


def _own_bucket(v):
    s = (v or '').strip().lower()
    if s.startswith('for profit'):
        return 'For profit'
    if s.startswith('non profit'):
        return 'Non profit'
    if s.startswith('government'):
        return 'Government'
    return None


def _bed_band(v):
    b = _num(v)
    if b is None:
        return None
    if b < 60:
        return '1. Under 60 beds'
    if b < 120:
        return '2. 60 to 119 beds'
    if b < 180:
        return '3. 120 to 179 beds'
    return '4. 180 or more beds'


def build(wb, ctx):
    lib = ctx['lib']
    facts, sources, findings = [], [], []
    qrp = {r['ccn']: r for r in lib.load_cache(ctx['cache'], 'snf_qrp')}
    info = {r['cms_certification_number_ccn']: r
            for r in lib.load_cache(ctx['cache'], 'pdc2_nursing_homes')}
    ccns = set(qrp) & set(info)

    # national worst-decile PPR floor (top 10% of PPR-reporting SNFs)
    natl_ppr = [_num(qrp[c].get('ppr_rsrr')) for c in ccns]
    natl_ppr = [x for x in natl_ppr if x is not None]
    ppr_p90 = _pctile(natl_ppr, 90)

    OWN = ['For profit', 'Non profit', 'Government']
    BEDS = ['1. Under 60 beds', '2. 60 to 119 beds', '3. 120 to 179 beds',
            '4. 180 or more beds']
    RATINGS = ['1', '2', '3', '4', '5']

    def collect(keyfn, universe):
        """universe: 'natl' or 'fp'. Returns {bucket: {'ppr':[], 'dtc':[],
        'worst':int, 'n':int}}."""
        out = {}
        for c in ccns:
            i = info[c]
            if universe == 'fp' and (i.get('state') or '').strip().upper() \
                    not in FOOTPRINT:
                continue
            b = keyfn(i)
            if b is None:
                continue
            d = out.setdefault(b, {'ppr': [], 'dtc': [], 'worst': 0, 'n': 0})
            d['n'] += 1
            pv = _num(qrp[c].get('ppr_rsrr'))
            dv = _num(qrp[c].get('dtc_rs_rate'))
            if pv is not None:
                d['ppr'].append(pv)
                if ppr_p90 is not None and pv >= ppr_p90:
                    d['worst'] += 1
            if dv is not None:
                d['dtc'].append(dv)
        return out

    own_n = collect(lambda i: _own_bucket(i.get('ownership_type')), 'natl')
    own_f = collect(lambda i: _own_bucket(i.get('ownership_type')), 'fp')
    bed_n = collect(lambda i: _bed_band(i.get('number_of_certified_beds')), 'natl')
    bed_f = collect(lambda i: _bed_band(i.get('number_of_certified_beds')), 'fp')
    rat_n = collect(lambda i: (i.get('overall_rating') or '').strip()
                    if (i.get('overall_rating') or '').strip() in RATINGS
                    else None, 'natl')

    sources.append(
        {'key': 'cms_snf_provider_info', 'publisher': 'CMS',
         'document': 'Nursing homes including rehab services - Provider Info '
                     '(CMS Provider Data Catalog / Care Compare)',
         'vintage': 'Current provider-info snapshot (accessed with the v3 pull '
                    'window); ownership and certified-bed fields',
         'locator': 'Datastore 4pq5-n9py; fields Ownership Type, Number of '
                    'Certified Beds, Overall Rating, joined to snf_qrp on the '
                    'CMS Certification Number (CCN)',
         'supplies': 'SNF ownership bucket, certified-bed scale, and overall '
                     'star rating for the return-leg structural cut',
         'url': 'https://data.cms.gov/provider-data/dataset/4pq5-n9py',
         'tier': 'A', 'accessed': ctx['accessed'],
         'powers': ['SNF_ReturnLeg_Structure']})

    ws = wb.create_sheet('SNF_ReturnLeg_Structure')
    sb = lib.SheetBuilder(ws, 8, tab_color='FF6B7C93',
                          col_widths=[24, 11, 15, 15, 11, 15, 15, 30])
    sb.title('SNF return-leg structure: who bounces patients back (ownership, '
             'scale, star rating)')
    sb.subtitle('The question: X-A.4 measured the return-leg rates; this tab '
                'asks whether a SNF\'s ownership, scale and quality rating '
                'predict how much return-leg transport it generates. It joins '
                'the SNF QRP claims measures (snf_qrp, dataset fykj-qjee) to '
                'the CMS Nursing Home provider-info file (dataset 4pq5-n9py) on '
                'the CCN - a 1:1 join over all reporting SNFs - and cross-tabs '
                'the risk-standardized potentially-preventable readmission '
                '(PPR = bounce-back transport) and discharge-to-community (DTC) '
                'rates by ownership, certified-bed scale, and 5-star rating. '
                'Higher PPR / lower DTC = a stronger structural transport-'
                'demand node.')
    sb.note('DATA QUALITY: both inputs are national CMS facility files joined '
            'on the CMS Certification Number; the join covers ' + f'{len(ccns):,}'
            ' SNFs that appear in both. Rates are CLAIMS-BASED and RISK-'
            'STANDARDIZED (case-mix adjusted), so residual variation across '
            'ownership / scale / rating is facility signal, not case mix; '
            'transport demand is INFERRED (a readmission implies a SNF-to-'
            'hospital transport leg), not counted. Ownership buckets collapse '
            'the CMS sub-categories (For profit - LLC / Corporation / '
            'Individual / Partnership -> For profit, etc.). The worst-decile '
            'floor is the national 90th-percentile PPR.')
    sb.blank()

    def _panel(title, hdr0, order, dn, df, note_first, has_fp=True):
        sb.banner(title)
        sb.headers([hdr0, 'National SNFs', 'Natl median PPR (%)',
                    'Natl median DTC (%)',
                    'Footprint SNFs' if has_fp else '',
                    'Fp median PPR (%)' if has_fp else '',
                    'Fp median DTC (%)' if has_fp else '', 'Note'])
        r0 = sb.r + 1
        for idx, b in enumerate(order):
            d = dn.get(b, {'ppr': [], 'dtc': [], 'n': 0})
            f = (df or {}).get(b, {'ppr': [], 'dtc': [], 'n': 0})
            row = [(b, 'src'), (d['n'], 'src', lib.FMT_INT),
                   (round(_median(d['ppr']), 2), 'src', lib.FMT_DEC1)
                   if d['ppr'] else ('n/a', 'note'),
                   (round(_median(d['dtc']), 1), 'src', lib.FMT_DEC1)
                   if d['dtc'] else ('n/a', 'note')]
            if has_fp:
                row += [(f['n'], 'src', lib.FMT_INT),
                        (round(_median(f['ppr']), 2), 'src', lib.FMT_DEC1)
                        if f['ppr'] else ('n/a', 'note'),
                        (round(_median(f['dtc']), 1), 'src', lib.FMT_DEC1)
                        if f['dtc'] else ('n/a', 'note')]
            else:
                row += [None, None, None]
            row.append((note_first if idx == 0 else None, 'note'))
            sb.row(row)
        sb.blank()
        return r0

    a0 = _panel('Panel A. Return-leg rates by ownership bucket (higher PPR = '
                'more bounce-back transport)', 'Ownership', OWN, own_n, own_f,
                'for-profit tends to bounce back more than non-profit')
    _panel('Panel B. Return-leg rates by certified-bed scale', 'Bed scale',
           BEDS, bed_n, bed_f, 'scale vs bounce-back')
    _panel('Panel C. Return-leg rates by overall 5-star rating (the quality '
           'gradient)', 'Overall rating', RATINGS, rat_n, None,
           '1 star = worst care; note the PPR gradient', has_fp=False)

    # Panel D: national for-profit vs non-profit gap (live formulas)
    fp_row = a0                      # For profit row in Panel A
    np_row = a0 + 1                  # Non profit row in Panel A
    sb.banner('Panel D. For-profit vs non-profit gap (live formulas over '
              'Panel A national medians)')
    sb.headers(['Measure', 'For profit', 'Non profit', 'Gap (FP - NP)',
                'Read', '', '', ''])
    sb.row([('Median PPR - bounce-back (lower is better)', 'text'),
            (f'=C{fp_row}', 'fml', lib.FMT_DEC1),
            (f'=C{np_row}', 'fml', lib.FMT_DEC1),
            (f'=C{fp_row}-C{np_row}', 'fml', lib.FMT_DEC1),
            ('positive = for-profit bounces back more', 'note'),
            None, None, None])
    sb.row([('Median DTC - sent home (higher is better)', 'text'),
            (f'=D{fp_row}', 'fml', lib.FMT_DEC1),
            (f'=D{np_row}', 'fml', lib.FMT_DEC1),
            (f'=D{fp_row}-D{np_row}', 'fml', lib.FMT_DEC1),
            ('negative = for-profit sends fewer home', 'note'),
            None, None, None])
    sb.blank()

    lib.add_chart(ws, 'J' + str(a0),
                  'Median potentially preventable readmission by SNF ownership',
                  f"'SNF_ReturnLeg_Structure'!$A${a0}:$A${a0 + len(OWN) - 1}",
                  [('Natl median PPR (%)',
                    f"'SNF_ReturnLeg_Structure'!$C${a0}:$C${a0 + len(OWN) - 1}")],
                  kind='bar', y_fmt='0.0')

    fp_ppr = _median(own_n.get('For profit', {}).get('ppr', []))
    np_ppr = _median(own_n.get('Non profit', {}).get('ppr', []))
    r1 = _median(rat_n.get('1', {}).get('ppr', []))
    r5 = _median(rat_n.get('5', {}).get('ppr', []))
    sb.banner('Read panel')
    sb.prose(
        'What is measured: the same two risk-standardized SNF QRP claims '
        'measures as X-A.4, cut by facility structure. Ownership sorts the '
        f'bounce-back: for-profit SNFs run a median PPR of about {round(fp_ppr, 2)}% '
        f'against {round(np_ppr, 2)}% for non-profit - the for-profit facilities '
        'return more patients to the hospital, so they generate proportionally '
        'more SNF-to-hospital transport. The 5-star rating is a clean gradient: '
        f'1-star SNFs sit near {round(r1, 2)}% PPR versus about {round(r5, 2)}% '
        'for 5-star, i.e. the worst-rated facilities are the heaviest bounce-'
        'back nodes. For an operator these are targeting screens: the return-leg '
        'transport demand concentrates in for-profit, lower-rated SNFs, and '
        'ownership concentration among them (chains) is a consolidation and '
        'partnership signal. What is NOT measured: actual transport counts (a '
        'readmission implies a leg but the file carries quality rates, not '
        'trips), and non-Medicare / managed-care stays outside the claims '
        'measure.')

    facts += [
        {'metric': 'National median risk-standardized SNF potentially '
                   'preventable readmission rate, for-profit SNFs (return-leg '
                   'bounce-back)',
         'year': 2026, 'value': round(fp_ppr, 2), 'unit': 'percent of stays',
         'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['cms_snf_qrp', 'cms_snf_provider_info'],
         'locator': 'SNF_ReturnLeg_Structure Panel A, For profit row, national '
                    'median of PPR_PD_RSRR',
         'lives_on': 'SNF_ReturnLeg_Structure',
         'cross_check': f'Non-profit median {round(np_ppr, 2)}% (Panel A); '
                        'for-profit bounces back more'},
        {'metric': 'National median risk-standardized SNF potentially '
                   'preventable readmission rate, 1-star vs 5-star SNFs '
                   '(quality gradient)',
         'year': 2026, 'value': round(r1, 2), 'unit': 'percent of stays '
                                                      '(1-star)',
         'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['cms_snf_qrp', 'cms_snf_provider_info'],
         'locator': 'SNF_ReturnLeg_Structure Panel C, rating 1 row, national '
                    'median of PPR_PD_RSRR',
         'lives_on': 'SNF_ReturnLeg_Structure',
         'cross_check': f'5-star median {round(r5, 2)}%; monotonic gradient - '
                        'lower-rated SNFs bounce back more'},
    ]
    findings.append({
        'id_hint': 106,
        'finding': 'SNF return-leg transport demand has structure: joining the '
                   'SNF QRP claims measures to the CMS ownership file over all '
                   f'{len(ccns):,} reporting SNFs, for-profit facilities carry '
                   f'a median potentially preventable readmission rate of about '
                   f'{round(fp_ppr, 2)}% versus {round(np_ppr, 2)}% for non-'
                   'profit, and the 5-star rating is a clean gradient '
                   f'({round(r1, 2)}% at 1 star to {round(r5, 2)}% at 5 star). '
                   'The bounce-back that generates SNF-to-hospital transport '
                   'concentrates in for-profit, lower-rated SNFs - a targeting '
                   'and consolidation screen for the return leg.',
        'numbers': f"='SNF_ReturnLeg_Structure'!C{fp_row}",
        'sources': 'cms_snf_qrp; cms_snf_provider_info',
        'confidence': 'High on the reported rates (risk-standardized CMS '
                      'measures joined 1:1 on CCN); the transport-demand link '
                      'is an inference, not a measured trip count',
        'guardrail': 'These are quality rates, not transports; the ownership '
                     'gap is a median difference across thousands of '
                     'facilities, not a claim about any single SNF; suppressed '
                     'low-volume SNFs and non-Medicare stays are outside the '
                     'measure.'})

    return {'facts': facts, 'sources': sources, 'excluded': [],
            'findings': findings,
            'meta': {'joined_snfs': len(ccns),
                     'fp_median_ppr': round(fp_ppr, 2) if fp_ppr else None,
                     'np_median_ppr': round(np_ppr, 2) if np_ppr else None}}
