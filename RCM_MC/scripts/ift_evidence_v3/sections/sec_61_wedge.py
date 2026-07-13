"""Run 6, Workstream 1: Institutional_Ambulance_Wedge + HCRIS_Institutional_Roster.

The model's number-one open question: how much ground ambulance volume is billed
on INSTITUTIONAL claims (hospital outpatient revenue centers 0540-0549, Part A
inpatient-bundled, SNF consolidated-billing) rather than on the Part B carrier
file the whole study is built from. The QN/QM work proved this channel is
structurally invisible to the carrier file; this tab measures its size two free
ways and lays the receiving schema for the definitive route.

1A - the interim wedge: MedPAC's all-claims Medicare FFS ground transport count
     (supplier + provider, from the ambulance fee schedule) minus the carrier-
     file count = institutional residual. Guarded, bounded, single defensible
     year (2023), with the definitive routes bordered PENDING.
1C - the HCRIS operator roster: every hospital that books a Worksheet A line-95
     ambulance cost centre, its cost, and a bounded implied operating volume
     (cost divided by the GADCS cost-per-transport range). This sizes the
     hospital-run ambulance OPERATION per facility; the Medicare-institutional-
     billed slice specifically is the ResDAC route, whose schema ships here.

The ambulance cost centre is paid under the fee schedule, not cost-based, so its
HCRIS Worksheet C CHARGE columns are inconsistently populated and are NOT used;
the reliable Worksheet A COST is used with the sourced GADCS rate range instead.
"""

SHEETS = [
    {'name': 'Institutional_Ambulance_Wedge',
     'question': 'How much Medicare ground ambulance volume is billed '
                 'institutionally rather than on the carrier file, and how do '
                 'we measure it?'},
    {'name': 'HCRIS_Institutional_Roster',
     'question': 'Which hospitals run an ambulance cost centre, at what cost, '
                 'and what operating volume does that imply?'},
]

TRANSPORT = ['A0426', 'A0427', 'A0428', 'A0429', 'A0433', 'A0434']
FOOT = {'NE', 'IA', 'KS', 'MO', 'OH', 'WI', 'VA', 'MN', 'IN', 'KY'}
# Sourced GADCS cost-per-transport bracket (already carried in the workbook):
GADCS_MEAN = 2673.0     # all-in mean -> LOW implied-volume bound
GADCS_MEDIAN = 1340.0   # median -> HIGH implied-volume bound

MEDPAC_URL = 'https://www.medpac.gov/wp-content/uploads/2024/08/Ambulance-MedPAC-03.25sec.pdf'
HCRIS_URL = ('https://www.cms.gov/research-statistics-data-and-systems/'
             'downloadable-public-use-files/cost-reports/hospital-2010-form')
RESDAC_URL = 'https://resdac.org/cms-data/request/cms-data-request-center'


def build(wb, ctx):
    lib = ctx['lib']
    cache = ctx['cache']
    accessed = ctx['accessed']
    facts, sources, excluded, findings = [], [], [], []

    # ---- carrier-file 2023 ground transport count (from the QN/QM re-cut) ----
    carrier23 = 0.0
    for code in TRANSPORT:
        try:
            d = lib.load_cache(cache, f'psps_mod2_2023_{code}')
            carrier23 += d.get('total', {}).get('services', 0.0)
        except Exception:
            pass
    # The workbook already carries MedPAC's all-claims transport count on
    # MedPAC_2026_Mandated (June 2026 mandated report Ch.6, 11.3M for 2023) and
    # the reconciliation computes the wedge live off it. Use the SAME figure so
    # there is one MedPAC number in the book; the displayed cell references that
    # tab. (The March 2025 preliminary presentation rounded it to 11.4M.)
    medpac23 = 11_300_000.0
    inst23 = medpac23 - carrier23
    inst_share23 = inst23 / medpac23 if medpac23 else 0.0

    # ---- HCRIS operator roster (Worksheet A line-95 cost) by year ----------
    hc_years = [2019, 2020, 2021, 2022, 2023]
    hosp_name = {}
    try:
        for h in lib.load_cache(cache, 'pdc2_hospitals'):
            hosp_name[str(h.get('facility_id'))] = (h.get('facility_name'),
                                                    h.get('state'))
    except Exception:
        pass
    by_year = {}         # yr -> {n_ccn, cost}
    latest_rows = []     # per-CCN for the latest year
    for yr in hc_years:
        try:
            rows = lib.load_cache(cache, f'hcris_amb_fy{yr}')['rows']
        except Exception:
            continue
        agg = {}
        for r in rows:
            if r.get('line') != '09500':
                continue
            ccn = r['ccn']
            agg[ccn] = agg.get(ccn, 0.0) + (r.get('total') or 0.0)
        by_year[yr] = {'n_ccn': len(agg), 'cost': sum(agg.values())}
        if yr == hc_years[-1]:
            for ccn, cost in agg.items():
                nm, st = hosp_name.get(ccn, (None, None))
                latest_rows.append((ccn, nm, st, cost))
    latest_rows.sort(key=lambda x: -x[3])
    ylatest = hc_years[-1]
    tot_cost = by_year.get(ylatest, {}).get('cost', 0.0)
    n_ccn = by_year.get(ylatest, {}).get('n_ccn', 0)
    vol_lo = tot_cost / GADCS_MEAN       # low bound (high rate)
    vol_hi = tot_cost / GADCS_MEDIAN     # high bound (low rate)

    sources += [
        {'key': 'wedge_medpac', 'publisher': 'MedPAC',
         'document': 'Mandated report: Payment for ground ambulance services, '
                     'Chapter 6 - the all-claims Medicare FFS ground transport '
                     'count (supplier and provider), 2023. The same figure the '
                     'workbook carries on MedPAC_2026_Mandated and the '
                     'five-universe reconciliation reference',
         'vintage': '2023 (MedPAC mandated report Ch.6)',
         'locator': '"Medicare FFS ambulance transports = 11.3 million" (the '
                    'March 2025 preliminary presentation rounded it to 11.4M); '
                    'the fee schedule pays both suppliers and institutional '
                    'providers',
         'supplies': 'The MedPAC all-claims count in the interim wedge (live '
                     "link to MedPAC_2026_Mandated!B7)",
         'url': MEDPAC_URL, 'tier': 'A', 'accessed': accessed,
         'powers': ['Institutional_Ambulance_Wedge']},
        {'key': 'wedge_hcris', 'publisher': 'CMS',
         'document': 'HCRIS Hospital Cost Report (Form 2552-10), Worksheet A '
                     'line 95 ambulance cost centre, FY2019-FY2023 - as-filed '
                     'ambulance operating COST per hospital',
         'vintage': 'FY2019-FY2023 as-filed',
         'locator': 'Sum of the line-95 total cost column per CCN per year; '
                    'the charge columns are fee-schedule-inconsistent and not '
                    'used',
         'supplies': 'The HCRIS operator roster and its cost totals',
         'url': HCRIS_URL, 'tier': 'A', 'accessed': accessed,
         'powers': ['HCRIS_Institutional_Roster',
                    'Institutional_Ambulance_Wedge']},
    ]

    # =====================================================================
    # TAB 1: Institutional_Ambulance_Wedge
    # =====================================================================
    ws = wb.create_sheet('Institutional_Ambulance_Wedge')
    sb = lib.SheetBuilder(ws, 10,
                          col_widths=[46, 18, 18, 16, 14, 14, 12, 4, 4, 40],
                          tab_color='FFC58F00')
    sb.title('The institutional wedge: Medicare ground ambulance billed off the '
             'carrier file, measured and bounded')
    sb.subtitle('The QN/QM work proved that hospital-billed ambulance is '
                'structurally invisible to the Part B carrier file - it rides '
                'on institutional (UB-04) claims: hospital outpatient revenue '
                'centres 0540-0549, Part A inpatient-bundled transports, and '
                'SNF consolidated-billing transports. This tab sizes that wedge '
                'two free ways - a top-down MedPAC-minus-carrier subtraction '
                'and a bottom-up HCRIS cost roster - and lays the receiving '
                'schema for the definitive claims measurement (ResDAC LDS). '
                'Every definitive cell is bordered PENDING with its dataset '
                'named; nothing is asserted beyond what the two free routes '
                'support.')
    sb.note('DATA QUALITY: the top-down wedge is a guarded interim, not a '
            'precise count. The MedPAC count is paid fee-schedule transports; '
            'the carrier count is submitted carrier services - a slight scope '
            'mismatch that makes the residual approximate. The residual bundles '
            'three distinct channels (hospital OP, IP-bundled, SNF CB) it does '
            'not separate. The bottom-up HCRIS roster sizes the hospital '
            'ambulance OPERATION (all payers, all trip types), a broader '
            'quantity than the Medicare-institutional-billed slice. The '
            'Medicare-institutional volume specifically, per claim, is the '
            'ResDAC route (Panel C), PENDING an organizational data request.')
    sb.blank()

    # ---- Panel A: the interim top-down wedge -------------------------------
    sb.banner('Panel A. Interim wedge (top-down): MedPAC all-claims minus the '
              'carrier file, 2023')
    sb.headers(['Component', 'Ground transports 2023', 'Share of all-claims',
                'Basis', '', '', '', '', '', 'Note'])
    pa = sb.r + 1
    sb.row([('MedPAC all-claims Medicare FFS ground transports', 'label'),
            ("='MedPAC_2026_Mandated'!B7", 'fml', lib.FMT_INT),
            (f'=B{pa}/B${pa}', 'fml', lib.FMT_PCT1),
            ('MedPAC mandated report Ch.6 (live link)', 'text'), None, None,
            None, None, None,
            ('supplier AND institutional provider; the same figure the '
             'five-universe reconciliation already carries', 'note')],
           wrap=True, height=30)
    sb.row([('less: carrier-file (Part B supplier) ground transports', 'label'),
            (round(carrier23), 'src', lib.FMT_INT),
            (f'=B{pa + 1}/B${pa}', 'fml', lib.FMT_PCT1),
            ('PSPS re-cut (this workbook)', 'text'), None, None, None, None,
            None, ('the six ground base codes, submitted services, 2023', 'note')],
           wrap=True, height=30)
    sb.row([('Institutional residual (the wedge)', 'label'),
            (f'=B{pa}-B{pa + 1}', 'fml', lib.FMT_INT),
            (f'=B{pa + 2}/B${pa}', 'fml', lib.FMT_PCT1),
            ('DERIVED (interim)', 'text'), None, None, None, None, None,
            ('hospital OP + IP-bundled + SNF CB, not separated here', 'note')],
           wrap=True, height=30)
    sb.note(f'Read: about {inst23 / 1e3:,.0f} thousand Medicare FFS ground '
            f'transports - roughly {inst_share23 * 100:.0f}% of the 2023 book - '
            'are billed institutionally and never appear in the carrier file. '
            'Interim and approximate; the ResDAC route replaces it with a '
            'per-claim count.')
    sb.blank()

    # ---- Panel B: the bottom-up HCRIS operator sizing ----------------------
    sb.banner('Panel B. Bottom-up (HCRIS): hospital ambulance operating cost '
              'and its bounded implied volume')
    sb.headers(['Cost-report year', 'Hospitals w/ line-95 ambulance centre',
                'Total ambulance operating cost $', 'Implied volume LOW (cost/'
                'GADCS mean)', 'Implied volume HIGH (cost/GADCS median)', '',
                '', '', '', 'Note'])
    b0 = sb.r + 1
    for i, yr in enumerate(hc_years):
        d = by_year.get(yr)
        if not d:
            continue
        rn = sb.r + 1
        sb.row([(yr, 'src'), (d['n_ccn'], 'src', lib.FMT_INT),
                (round(d['cost']), 'src', lib.FMT_USD),
                (f'=C{rn}/{GADCS_MEAN:.0f}', 'fml', lib.FMT_INT),
                (f'=C{rn}/{GADCS_MEDIAN:.0f}', 'fml', lib.FMT_INT),
                None, None, None, None,
                ('latest year-file' if yr == ylatest else None, 'note')
                if yr == ylatest else None])
    sb.note(f'Bounds use the workbook GADCS cost-per-transport range - mean '
            f'${GADCS_MEAN:,.0f} (low-volume bound) to median '
            f'${GADCS_MEDIAN:,.0f} (high-volume bound). This is the hospital '
            'ambulance OPERATION size (all payers, all trip types), the ceiling '
            'context for the Medicare-institutional slice, not the slice '
            'itself.')
    sb.blank()

    # ---- Panel C: the definitive route, receiving schema (2A ResDAC) -------
    sb.banner('Panel C. The definitive route (ResDAC LDS) - receiving schema, '
              'PENDING the data request')
    sb.headers(['Institutional file (2019-2024)', 'Extract rule',
                'National transports', 'National dollars', 'Per-CCN roster',
                '', '', '', '', 'Status'])
    for label, rule in [
        ('Hospital Outpatient (OPPS)',
         'claim lines with revenue centre 0540-0549 and HCPCS A0425-A0436; '
         'retain units, dates, O-D modifiers, billing CCN, state'),
        ('Inpatient (Part A)',
         'the same 054x lines inside covered inpatient stays (bundled '
         'transports)'),
        ('SNF (Part A)',
         'the same 054x lines inside covered SNF stays (consolidated-billing '
         'transports)')]:
        sb.row([(label, 'label'), (rule, 'text'), ('PENDING', 'note'),
                ('PENDING', 'note'), ('PENDING', 'note'), None, None, None,
                None, ('ResDAC LDS; DUA required', 'note')], wrap=True,
               height=44)
    sb.note('These three rows are the ground truth. When the ResDAC Limited '
            'Data Set lands, the PENDING cells fill with national and footprint '
            'institutional transport counts and dollars by year and the per-CCN '
            'institutional billing roster, and they replace the Panel A interim '
            'wedge. T-MSIS TAF (Medicaid) uses the identical revenue-centre '
            'logic in the same request.')
    sb.blank()

    # ---- Panel D: application + coordination specs (human action items) ----
    sb.banner('Panel D. Ready to send: the application and coordination specs')
    sb.headers(['Item', 'Owner', 'Spec (verbatim)', '', '', '', '', '', '',
                'Status'])
    sb.row([('2A ResDAC LDS request', 'label'),
            ('Human (organizational requester + DUA + fee)', 'text'),
            ('Hospital Outpatient + Inpatient + SNF LDS, 2019-2024: all claim '
             'lines with revenue centre 0540-0549; retain HCPCS (A0425-A0436), '
             'units, service dates, O-D modifiers where present, billing CCN, '
             'state; inpatient and SNF the same 054x lines inside covered '
             'stays', 'text'), None, None, None, None, None, None,
            ('quote from ResDAC, then submit', 'note')], wrap=True, height=64)
    sb.row([('2B T-MSIS TAF (Medicaid)', 'label'),
            ('Human (same request)', 'text'),
            ('Same revenue-centre logic on the Medicaid institutional files, '
             'bundled into the same request to amortize the process', 'text'),
            None, None, None, None, None, None,
            ('bundle with 2A', 'note')], wrap=True, height=40)
    sb.row([('3A Commercial extract spec (coordination)', 'label'),
            ('Human (to the sizing lead, before the second extract)', 'text'),
            ('Include institutional claim lines where revenue centre is '
             '0540-0549 or line HCPCS is A0425-A0436, retaining billing entity, '
             'revenue centre, HCPCS, units, service date, and payer, alongside '
             'the professional ambulance lines already specified', 'text'),
            None, None, None, None, None, None,
            ('one sentence; protects the bottoms-up from the wedge', 'note')],
           wrap=True, height=64)
    sb.blank()

    # ---- read panel + facts + findings (wedge) -----------------------------
    sb.banner('Read panel')
    sb.prose(
        'The institutional wedge is the model\'s largest unmeasured number, and '
        'this tab moves it from inference to a bounded interim measurement with '
        'a definitive route staged. Top-down: MedPAC counts '
        f'{medpac23 / 1e6:.1f} million Medicare FFS ground transports in 2023, '
        'the fee schedule paying both suppliers and institutional providers; '
        f'the carrier file holds {carrier23 / 1e6:.1f} million; the residual - '
        f'about {inst23 / 1e3:,.0f} thousand transports, roughly '
        f'{inst_share23 * 100:.0f}% of the book - is billed institutionally and '
        'invisible to every carrier-file exhibit. Bottom-up: '
        f'{n_ccn:,} hospitals booked an ambulance cost centre in {ylatest} at '
        f'${tot_cost / 1e6:,.0f} million of operating cost, implying between '
        f'{vol_lo / 1e3:,.0f} and {vol_hi / 1e3:,.0f} thousand transports of '
        'hospital-run OPERATION across all payers - the ceiling context for the '
        'Medicare slice. Both are free and honest; neither is the per-claim '
        'count. That count is the ResDAC route, whose extract schema (Panel C) '
        'and application spec (Panel D) ship here ready to send. When it lands, '
        'the study can tell an investor not just that hospital-billed volume '
        'exists and why it is invisible, but exactly how many transports it is '
        'and who bills them.')
    facts += [
        {'metric': 'Institutional (off-carrier) share of Medicare FFS ground '
                   'transports, interim top-down wedge', 'year': 2023,
         'value': round(inst_share23, 4), 'unit': 'share of all-claims '
         'transports (interim)', 'basis': 'DERIVED', 'tier': 'B',
         'source_keys': ['wedge_medpac'],
         'locator': f'Institutional_Ambulance_Wedge Panel A residual row, live '
                    f'C{pa + 2}',
         'lives_on': 'Institutional_Ambulance_Wedge',
         'cross_check': f'MedPAC {medpac23 / 1e6:.1f}M minus carrier '
                        f'{carrier23 / 1e6:.1f}M; interim, scope-approximate, '
                        'ResDAC route replaces it'},
        {'metric': 'Institutional (off-carrier) Medicare FFS ground transports, '
                   'interim top-down wedge', 'year': 2023,
         'value': round(inst23), 'unit': 'transports (interim)',
         'basis': 'DERIVED', 'tier': 'B', 'source_keys': ['wedge_medpac'],
         'locator': 'Institutional_Ambulance_Wedge Panel A residual row, live '
                    f'B{pa + 2}',
         'lives_on': 'Institutional_Ambulance_Wedge',
         'cross_check': 'Bundles hospital OP, IP-bundled and SNF CB; not '
                        'separated at this stage'},
        {'metric': 'Hospitals booking a Worksheet A line-95 ambulance cost '
                   'centre', 'year': ylatest, 'value': n_ccn, 'unit': 'hospitals',
         'basis': 'GOV', 'tier': 'A', 'source_keys': ['wedge_hcris'],
         'locator': f'Institutional_Ambulance_Wedge Panel B {ylatest} row',
         'lives_on': 'HCRIS_Institutional_Roster',
         'cross_check': f'${tot_cost / 1e6:,.0f}M operating cost; implied '
                        f'{vol_lo / 1e3:,.0f}-{vol_hi / 1e3:,.0f}K operation '
                        'transports (all payers)'},
    ]
    findings += [
        {'id_hint': 115,
         'finding': 'The institutional wedge - Medicare ground ambulance billed '
                    'on institutional claims rather than the carrier file - is '
                    'now bounded from inference. Top-down, MedPAC counts '
                    f'{medpac23 / 1e6:.1f}M Medicare FFS ground transports in '
                    f'2023 versus {carrier23 / 1e6:.1f}M in the carrier file, a '
                    f'residual of about {inst23 / 1e3:,.0f}K transports '
                    f'(~{inst_share23 * 100:.0f}% of the book) that is billed '
                    'institutionally and invisible to every carrier-file '
                    'exhibit - the structural undercount the QN/QM work '
                    'predicted, now sized. It is an interim, scope-approximate '
                    'figure; the per-claim count is the ResDAC route, staged '
                    'and ready to request.',
         'numbers': "='Institutional_Ambulance_Wedge'!C" + str(pa + 2),
         'sources': 'wedge_medpac; wedge_hcris',
         'confidence': 'Moderate as an interim magnitude and share; high that '
                       'the channel is real and material',
         'guardrail': 'Interim: MedPAC paid transports vs carrier submitted '
                      'services is a scope mismatch, and the residual bundles '
                      'three channels. Do not quote it as a precise count; the '
                      'ResDAC LDS replaces it.'},
        {'id_hint': 116,
         'finding': f'The hospital ambulance operation is sized bottom-up: '
                    f'{n_ccn:,} hospitals booked a Worksheet A line-95 ambulance '
                    f'cost centre in {ylatest} at ${tot_cost / 1e6:,.0f} million '
                    'of operating cost, implying between '
                    f'{vol_lo / 1e3:,.0f}K and {vol_hi / 1e3:,.0f}K transports '
                    'of hospital-run operation across all payers (cost divided '
                    'by the GADCS cost-per-transport range). This is the '
                    'all-payer ceiling context for the Medicare-institutional '
                    'slice, and a per-CCN roster of who runs an ambulance and '
                    'at what scale (HCRIS_Institutional_Roster).',
         'numbers': "='Institutional_Ambulance_Wedge'!C" + str(b0 + len(hc_years) - 1),
         'sources': 'wedge_hcris',
         'confidence': 'High on the cost and hospital count; the volume is a '
                       'bound, not a count',
         'guardrail': 'Cost-to-volume is a bound using an external rate range; '
                      'it measures the whole operation (all payers, 911 and '
                      'IFT), not the Medicare-institutional billed slice, which '
                      'is the ResDAC route.'}]

    # =====================================================================
    # TAB 2: HCRIS_Institutional_Roster (per-CCN, latest year)
    # =====================================================================
    ws2 = wb.create_sheet('HCRIS_Institutional_Roster')
    sb2 = lib.SheetBuilder(ws2, 10,
                           col_widths=[12, 44, 8, 18, 16, 16, 8, 4, 4, 30],
                           tab_color='FFC58F00')
    sb2.title(f'Hospital ambulance operators: the HCRIS line-95 roster, {ylatest}')
    sb2.subtitle('Every hospital that booked a Worksheet A line-95 ambulance '
                 f'cost centre in FY{ylatest}, its as-filed ambulance operating '
                 'cost, and a bounded implied operating volume (cost divided by '
                 'the GADCS cost-per-transport range). This is the roster of '
                 'who runs a hospital-based ambulance and at what scale - the '
                 'operates-and-bills population the insourcing bounds and the '
                 'QN/QM flag measure from the claims side. Volume is a bound, '
                 'not a count, and covers all payers and all trip types.')
    sb2.note('DATA QUALITY: cost is as-filed (Worksheet A, not settled); '
             'reporting is a slight floor (some hospitals book ambulance '
             'elsewhere or do not file). The implied-volume columns are bounds '
             'from an external rate range, not counts, and size the whole '
             'operation, not the Medicare-institutional slice. Footprint = the '
             'ten study-footprint states.')
    sb2.blank()
    sb2.banner(f'The roster: {len(latest_rows):,} hospitals, ranked by ambulance '
               'operating cost')
    sb2.headers(['CCN', 'Hospital (Care Compare)', 'State',
                 f'FY{ylatest} ambulance cost $', 'Implied vol LOW',
                 'Implied vol HIGH', 'Footprint', '', '', 'Note'])
    r0 = sb2.r + 1
    for ccn, nm, st, cost in latest_rows:
        rn = sb2.r + 1
        sb2.row([(ccn, 'label'), (nm or '(name not matched)', 'text'),
                 (st or '', 'text'), (round(cost), 'src', lib.FMT_USD),
                 (f'=D{rn}/{GADCS_MEAN:.0f}', 'fml', lib.FMT_INT),
                 (f'=D{rn}/{GADCS_MEDIAN:.0f}', 'fml', lib.FMT_INT),
                 ('yes' if st in FOOT else '', 'text'),
                 None, None, None])
    sb2.blank()
    sb2.note(f'Total ambulance operating cost across the roster reconciles to '
             f'Institutional_Ambulance_Wedge Panel B {ylatest}: '
             f'${tot_cost / 1e6:,.0f} million over {n_ccn:,} hospitals.')

    return {'facts': facts, 'sources': sources, 'excluded': excluded,
            'findings': findings,
            'meta': {'inst_share_2023': round(inst_share23, 4),
                     'inst_2023': round(inst23), 'hcris_hospitals': n_ccn}}
