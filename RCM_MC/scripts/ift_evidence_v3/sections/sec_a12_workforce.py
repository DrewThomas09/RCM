"""A.12 + A.13: Workforce_Depth - the EMS labor base of the footprint in
one place: the paramedic-over-EMT wage ladder (OEWS), footprint wage level
and growth against the national industry (QCEW annual), county employment
depth per 1,000 residents 65+, and the quarterly reads: establishment
churn proxy, the average-weekly-wage series against the Ambulance
Inflation Factor path (extends finding 45 to quarterly grain), and the
COVID shock shape.

Footprint states NE IA KS MO OH WI VA MN IN KY, provisional pending E.5.
"""

SHEETS = [{'name': 'Workforce_Depth',
           'question': 'How deep, how expensive and how tight is the '
                       'footprint EMS labor base, and does pay outrun the '
                       'Medicare price index at quarterly grain?'}]

FP = ['NE', 'IA', 'KS', 'MO', 'OH', 'WI', 'VA', 'MN', 'IN', 'KY']
FIPS = {'NE': '31', 'IA': '19', 'KS': '20', 'MO': '29', 'OH': '39',
        'WI': '55', 'VA': '51', 'MN': '27', 'IN': '18', 'KY': '21'}
STATE_NAME = {'NE': 'Nebraska', 'IA': 'Iowa', 'KS': 'Kansas',
              'MO': 'Missouri', 'OH': 'Ohio', 'WI': 'Wisconsin',
              'VA': 'Virginia', 'MN': 'Minnesota', 'IN': 'Indiana',
              'KY': 'Kentucky'}
QQ = 'QCEW_Quarterly'          # A yr B qtr C fips D own E estab F-H emp I wages J wkly
QQ_LO, QQ_HI = 5, 4836
# Payment_Rules AIF cells: CY2020..CY2025 in B16..B21 (CY2026 in B22)
AIF_ROW = {2020: 16, 2021: 17, 2022: 18, 2023: 19, 2024: 20, 2025: 21}


def _f(v):
    try:
        return float(str(v).replace(',', ''))
    except (TypeError, ValueError):
        return None


def build(wb, ctx):
    lib = ctx['lib']
    cache = ctx['cache']
    facts, sources, excluded, findings = [], [], [], []
    fp_fips = [FIPS[s] + '000' for s in FP]
    fp_arr = '{' + ','.join(f'"{f}"' for f in fp_fips) + '}'

    # Resolve the QCEW_Quarterly DATA extent from the built tab so the
    # SUMPRODUCT value arrays never include the text header row (row with
    # 'Year' in col A): 0*text is #VALUE! in a SUMPRODUCT. Data starts the
    # row after the header and runs to the last numeric-year row.
    lo, hi = QQ_LO, QQ_HI
    if QQ in wb.sheetnames:
        qws = wb[QQ]
        hdr = None
        for row in qws.iter_rows(min_col=1, max_col=1):
            if row[0].value == 'Year':
                hdr = row[0].row
                break
        if hdr:
            lo = hdr + 1
            last = lo
            for row in qws.iter_rows(min_col=1, max_col=1, min_row=lo):
                if isinstance(row[0].value, (int, float)):
                    last = row[0].row
            hi = last
    QQ_LO_R, QQ_HI_R = lo, hi

    def qq(col):
        return f"'{QQ}'!${col}${QQ_LO_R}:${col}${QQ_HI_R}"

    def sumifs(vcol, yr, q, area, own='Private'):
        return (f"SUMIFS({qq(vcol)},{qq('A')},{yr},{qq('B')},{q},"
                f"{qq('C')},\"{area}\",{qq('D')},\"{own}\")")

    # ------------------------------------------------------- cache reads -
    # quarterly national + footprint state series, probing 2014-2025
    quarters, us_wage, us_emp = [], {}, {}
    st_est, st_wkly = {}, {}
    for yr in range(2014, 2026):
        for q in range(1, 5):
            try:
                rows = ctx['lib'].load_cache(cache, f'qcew_q_{yr}q{q}')
            except FileNotFoundError:
                continue
            quarters.append((yr, q))
            for r in rows:
                if r.get('own_code') != '5':
                    continue
                a = r.get('area_fips')
                if a == 'US000':
                    us_wage[(yr, q)] = _f(r.get('avg_wkly_wage'))
                    us_emp[(yr, q)] = ((_f(r.get('month1_emplvl')) or 0) +
                                       (_f(r.get('month2_emplvl')) or 0) +
                                       (_f(r.get('month3_emplvl')) or 0)) / 3
                elif a in fp_fips:
                    st_est[(a, yr, q)] = int(_f(r.get('qtrly_estabs')) or 0)
                    st_wkly[(a, yr, q)] = _f(r.get('avg_wkly_wage'))
    yr_lo, yr_hi = quarters[0][0], quarters[-1][0]
    last_q = quarters[-1]

    # AIF path (mirrors Payment_Rules B16:B21; re-carried here only to
    # compute fact values - the tab cells green-link to Payment_Rules)
    aif = {2020: 0.009, 2021: 0.002, 2022: 0.051, 2023: 0.087,
           2024: 0.026, 2025: 0.024}
    base = us_wage[(2019, 4)]
    widx = {k: v / base * 100 for k, v in us_wage.items()}
    aidx, cur = {}, 100.0
    for yr in range(2020, yr_hi + 1):
        cur *= (1 + aif.get(yr, 0))
        for q in range(1, 5):
            aidx[(yr, q)] = cur
    aidx[(2019, 4)] = 100.0
    scissors = widx[last_q] - aidx[last_q]

    # COVID shock
    dip = us_emp[(2020, 2)] / us_emp[(2020, 1)] - 1
    recovery = None
    for (yr, q) in quarters:
        if (yr, q) > (2020, 2) and us_emp.get((yr, q), 0) >= us_emp[(2020, 1)]:
            recovery = (yr, q)
            break

    # state tightness inputs: 4-quarter avg weekly wage 2019 / latest year
    st19, st25, growth = {}, {}, {}
    for s in FP:
        a = FIPS[s] + '000'
        w19 = [st_wkly.get((a, 2019, q)) for q in range(1, 5)]
        w25 = [st_wkly.get((a, yr_hi, q)) for q in range(1, 5)]
        st19[s] = sum(x for x in w19 if x) / len([x for x in w19 if x])
        st25[s] = sum(x for x in w25 if x) / len([x for x in w25 if x])
        growth[s] = st25[s] / st19[s] - 1

    # state employment (latest year avg) for density
    st_emp = {s: 0.0 for s in FP}
    for q in range(1, 5):
        rows = ctx['lib'].load_cache(cache, f'qcew_q_{yr_hi}q{q}')
        for r in rows:
            a = r.get('area_fips')
            if r.get('own_code') == '5' and a in fp_fips:
                s = [k for k, v in FIPS.items() if v == a[:2]][0]
                st_emp[s] += ((_f(r.get('month1_emplvl')) or 0) +
                              (_f(r.get('month2_emplvl')) or 0) +
                              (_f(r.get('month3_emplvl')) or 0)) / 3 / 4

    # 65+ by state (latest census vintage year in the cache)
    cen = ctx['lib'].load_cache(cache, 'census_county_age_2024')
    maxyr = max(int(r['YEAR']) for r in cen)
    st65 = {s: 0.0 for s in FP}
    inv = {v: k for k, v in FIPS.items()}
    for r in cen:
        if int(r['YEAR']) == maxyr and r['STATE'] in inv:
            st65[inv[r['STATE']]] += _f(r['AGE65PLUS_TOT']) or 0
    dens = {s: st_emp[s] / st65[s] * 1000 for s in FP}

    # two-test tightness rule: top-2 wage growth AND bottom-2 density
    g_rank = sorted(FP, key=lambda s: -growth[s])
    d_rank = sorted(FP, key=lambda s: dens[s])
    tight = [s for s in FP if s in g_rank[:2] and s in d_rank[:2]]
    tight_state = tight[0] if tight else g_rank[0]

    # establishment churn proxy per state
    churn = {}
    for s in FP:
        a = FIPS[s] + '000'
        ups = downs = flat = 0
        prev = None
        for (yr, q) in quarters:
            curv = st_est.get((a, yr, q))
            if prev is not None and curv is not None:
                if curv > prev:
                    ups += 1
                elif curv < prev:
                    downs += 1
                else:
                    flat += 1
            prev = curv
        churn[s] = (ups, downs, flat)

    # footprint + national annual pay (for facts; the tab computes the
    # same live)
    fp_wages = {yr: 0.0 for yr in range(yr_lo, yr_hi + 1)}
    fp_emp = {yr: 0.0 for yr in range(yr_lo, yr_hi + 1)}
    nat_wages = {yr: 0.0 for yr in range(yr_lo, yr_hi + 1)}
    nat_emp = {yr: 0.0 for yr in range(yr_lo, yr_hi + 1)}
    for yr in range(yr_lo, yr_hi + 1):
        for q in range(1, 5):
            rows = ctx['lib'].load_cache(cache, f'qcew_q_{yr}q{q}')
            for r in rows:
                if r.get('own_code') != '5':
                    continue
                m = ((_f(r.get('month1_emplvl')) or 0) +
                     (_f(r.get('month2_emplvl')) or 0) +
                     (_f(r.get('month3_emplvl')) or 0)) / 12
                w = _f(r.get('total_qtrly_wages')) or 0
                if r.get('area_fips') in fp_fips:
                    fp_wages[yr] += w
                    fp_emp[yr] += m
                elif r.get('area_fips') == 'US000':
                    nat_wages[yr] += w
                    nat_emp[yr] += m
    fp_pay = {yr: (fp_wages[yr] / fp_emp[yr] if fp_emp[yr] else None)
              for yr in fp_wages}
    nat_pay = {yr: (nat_wages[yr] / nat_emp[yr] if nat_emp[yr] else None)
               for yr in nat_wages}
    gap_latest = fp_pay[yr_hi] / nat_pay[yr_hi] - 1
    gap_2019 = fp_pay[2019] / nat_pay[2019] - 1

    # OEWS rows on the carried tab (for green links)
    ws_o = wb['OEWS_EMS_Wages']
    orow = {}
    for r, row in enumerate(ws_o.iter_rows(min_row=6, max_col=3), 6):
        ab, occ = row[1].value, row[2].value
        if ab in FP and isinstance(occ, str):
            if occ.startswith('29-2042'):
                orow[(ab, 'EMT')] = r
            elif occ.startswith('29-2043'):
                orow[(ab, 'PARA')] = r
    o_med = {}
    for r, row in enumerate(ws_o.iter_rows(min_row=6, max_col=8), 6):
        for key, rr in orow.items():
            if rr == r:
                o_med[key] = _f(row[7].value)
    prem = {s: (o_med.get((s, 'PARA')), o_med.get((s, 'EMT'))) for s in FP}
    prem_ratio = {s: (p / e if p and e else None) for s, (p, e) in prem.items()}
    widest = max((v, s) for s, v in prem_ratio.items() if v)

    # county depth: QCEW_County_2024 tab rows + County_Age_65plus tab rows
    ws_c = wb['QCEW_County_2024']
    crow = []
    for r, row in enumerate(ws_c.iter_rows(min_row=5, max_col=6), 5):
        fips, emp, est = row[0].value, _f(row[5].value), _f(row[4].value)
        if (isinstance(fips, str) and fips[:2] in inv and emp
                and not fips.endswith('999')):   # 999 = unknown-county rows
            crow.append((fips, r, emp, est))
    crow.sort(key=lambda x: -x[2])
    top = crow[:20]
    ws_a = wb['County_Age_65plus']
    arow = {}
    for r, row in enumerate(ws_a.iter_rows(min_row=5, max_col=3), 5):
        f3 = row[2].value
        if isinstance(f3, str):
            arow[f3] = (r, row[1].value, row[0].value)
    ca_max = ws_a.max_row
    # Data-start row of County_Age_65plus (row after its 'State' header): the
    # 5.3 DATA QUALITY note pushed the header to row 5 (data row 6), so a
    # SUMPRODUCT value array must not begin on the text header cell.
    ca_lo = 6
    for row in ws_a.iter_rows(min_col=1, max_col=1):
        if row[0].value == 'State':
            ca_lo = row[0].row + 1
            break
    # Data-start row of QCEW_County_2024 (row after its 'FIPS' header).
    qc_lo, qc_hi = 5, 1860
    if 'QCEW_County_2024' in wb.sheetnames:
        ws_q = wb['QCEW_County_2024']
        for row in ws_q.iter_rows(min_col=1, max_col=1):
            if row[0].value == 'FIPS':
                qc_lo = row[0].row + 1
                break
        last = qc_lo
        for row in ws_q.iter_rows(min_col=1, max_col=1, min_row=qc_lo):
            v = row[0].value
            if isinstance(v, str) and len(v) == 5 and v.isdigit():
                last = row[0].row
        qc_hi = last

    # --------------------------------------------------------- sources ---
    sources += [
        {'key': 'a12_oews', 'publisher': 'BLS',
         'document': 'Occupational Employment and Wage Statistics, May '
                     '2024 state estimates - EMTs (29-2042) and Paramedics '
                     '(29-2043), as carried on OEWS_EMS_Wages',
         'vintage': 'May 2024', 'locator': 'OEWS_EMS_Wages Panel A rows; '
         'median annual wage column H',
         'supplies': 'The paramedic-over-EMT wage ladder by state',
         'url': 'https://www.bls.gov/oes/', 'tier': 'A',
         'accessed': ctx['accessed'], 'powers': ['Workforce_Depth']},
        {'key': 'a12_qcew', 'publisher': 'BLS',
         'document': 'Quarterly Census of Employment and Wages, NAICS '
                     '621910 Ambulance Services, private ownership - '
                     'quarterly state/national files 2014Q1-' +
                     f'{yr_hi}Q{last_q[1]}, as carried on QCEW_Quarterly '
                     'and cached (qcew_q_YYYYqQ)',
         'vintage': f'2014Q1 - {yr_hi}Q{last_q[1]}',
         'locator': 'QCEW_Quarterly data rows (below the header); caches qcew_q_*; caches qcew_q_*',
         'supplies': 'Quarterly wages, employment and establishment counts '
                     'for the scissors, churn and COVID panels',
         'url': 'https://www.bls.gov/cew/downloadable-data-files.htm',
         'tier': 'A', 'accessed': ctx['accessed'],
         'powers': ['Workforce_Depth']},
        {'key': 'a12_qcew_county', 'publisher': 'BLS',
         'document': 'QCEW annual county files, NAICS 621910 private, 2024 '
                     '- as carried on QCEW_County_2024',
         'vintage': '2024 annual', 'locator': 'QCEW_County_2024 rows; '
         'employment column F',
         'supplies': 'County-grain ambulance employment for the depth '
                     'ratio', 'url': 'https://www.bls.gov/cew/',
         'tier': 'A', 'accessed': ctx['accessed'],
         'powers': ['Workforce_Depth']},
        {'key': 'a12_census65', 'publisher': 'US Census Bureau',
         'document': 'County population estimates by age, vintage 2024 '
                     '(65+), as carried on County_Age_65plus',
         'vintage': '2024 vintage estimates',
         'locator': 'County_Age_65plus column I (65+ 2024); join key '
                    'county FIPS',
         'supplies': 'Denominator for employment per 1,000 65+',
         'url': 'https://www.census.gov/programs-surveys/popest.html',
         'tier': 'A', 'accessed': ctx['accessed'],
         'powers': ['Workforce_Depth']},
        {'key': 'a13_aif', 'publisher': 'CMS',
         'document': 'Ambulance Inflation Factor, CY2020-CY2026, as '
                     'verified and carried on Payment_Rules (Pub. 100-04)',
         'vintage': 'CY2020-CY2026',
         'locator': 'Payment_Rules B16:B22; green-linked from this tab',
         'supplies': 'The Medicare price path the wage series is read '
                     'against', 'url': 'https://www.cms.gov/medicare/'
         'payment/fee-schedules/ambulance', 'tier': 'A',
         'accessed': ctx['accessed'], 'powers': ['Workforce_Depth']},
    ]

    # -------------------------------------------------------------- tab --
    ws = wb.create_sheet('Workforce_Depth')
    sb = lib.SheetBuilder(ws, 10,
                          col_widths=[26, 14, 14, 14, 14, 14, 14, 12, 12, 40],
                          tab_color='FF4C7C2C')
    sb.title('Workforce depth: the EMS labor base of the footprint, and '
             'the wage-vs-AIF scissors at quarterly grain')
    sb.subtitle('The question: how deep, how expensive and how tight is '
                'the EMS labor base under the footprint (NE IA KS MO OH '
                'WI VA MN IN KY - provisional pending E.5), and does '
                'industry pay outrun the Ambulance Inflation Factor '
                'quarter by quarter? Sources: BLS OEWS May 2024 (state x '
                'occupation medians, join: state abbrev), BLS QCEW NAICS '
                '621910 private (annual and quarterly, join: area FIPS), '
                'Census county age estimates (join: county FIPS), CMS AIF '
                'carried on Payment_Rules. Green cells link into carried '
                'tabs; blue cells are re-carried from the named caches '
                'with locators.')
    sb.note('DATA QUALITY: QCEW covers UI-COVERED employment only - '
            'volunteer squads and much fire-based cross-staffed EMS never '
            'appear, so every level is a floor and rural depth is '
            'understated most. Small-state cells are suppressed to zero '
            'in some quarters (Iowa is the visible case). OEWS medians '
            'are occupation medians, not firm-level costs. NAICS 621910 '
            'pay averages ALL occupations in ambulance firms, not crew '
            'wages alone. Footprint list provisional pending E.5.',
            height=34)
    sb.blank()

    # Panel A. OEWS premium
    sb.banner('Panel A. The wage ladder: paramedic over EMT median annual '
              'pay, May 2024 (green links into OEWS_EMS_Wages)')
    sb.headers(['State', 'Paramedic median annual $ (link)',
                'EMT median annual $ (link)', 'Paramedic premium (live)',
                '', '', '', '', '', 'Note'])
    a0 = sb.r + 1
    for i, s in enumerate(FP):
        rp, re_ = orow.get((s, 'PARA')), orow.get((s, 'EMT'))
        rn = a0 + i
        sb.row([(STATE_NAME[s], 'text'),
                (f"='OEWS_EMS_Wages'!H{rp}" if rp else 'PENDING', 'link'
                 if rp else 'note', lib.FMT_USD),
                (f"='OEWS_EMS_Wages'!H{re_}" if re_ else 'PENDING', 'link'
                 if re_ else 'note', lib.FMT_USD),
                (f'=IF(C{rn}=0,"n/a",B{rn}/C{rn})', 'fml', lib.FMT_X),
                None, None, None, None, None,
                ('the certification premium is the cost of an ALS-capable '
                 'market', 'note') if i == 0 else None])
    ar = a0 + len(FP)
    sb.row([('Widest footprint premium (live)', 'label'), None, None,
            (f'=MAX(D{a0}:D{ar - 1})', 'fml', lib.FMT_X),
            None, None, None, None, None,
            (f'{STATE_NAME[widest[1]]} - paramedic '
             f'${prem[widest[1]][0]:,.0f} vs EMT ${prem[widest[1]][1]:,.0f}'
             '; national extreme is WA at about 2.06x', 'note')])
    sb.blank()

    # Panel B. footprint vs national annual pay
    sb.banner('Panel B. Footprint wage level and growth vs national '
              '(live SUMPRODUCT over QCEW_Quarterly; national linked to '
              'QCEW_EMS_Employment Panel B)')
    sb.headers(['Year', 'Footprint total wages $ (live)',
                'Footprint avg employment (live)',
                'Footprint avg annual pay $ (live)',
                'National private avg annual pay $ (link)',
                'Footprint vs national (live)', '', '', '', 'Note'])
    b0 = sb.r + 1
    in_fp_q = f'ISNUMBER(MATCH({qq("C")},{fp_arr},0))'
    for i, yr in enumerate(range(yr_lo, yr_hi + 1)):
        rn = b0 + i
        wagef = (f'=SUMPRODUCT(({qq("A")}=A{rn})*({qq("D")}="Private")'
                 f'*{in_fp_q}*{qq("I")})')
        empf = (f'=SUMPRODUCT(({qq("A")}=A{rn})*({qq("D")}="Private")'
                f'*{in_fp_q}*({qq("F")}+{qq("G")}+{qq("H")}))/12')
        sb.row([(yr, 'src'), (wagef, 'fml', lib.FMT_USD),
                (empf, 'fml', lib.FMT_INT),
                (f'=IF(C{rn}=0,"n/a",B{rn}/C{rn})', 'fml', lib.FMT_USD),
                (f"='QCEW_EMS_Employment'!D{38 + yr - 2014}", 'link',
                 lib.FMT_USD),
                (f'=IF(OR(C{rn}=0,E{rn}=0),"n/a",D{rn}/E{rn}-1)', 'fml',
                 lib.FMT_PCT1),
                None, None, None,
                ('footprint is a 10-state mix vs the national composition '
                 '- a level gap, not a like-for-like market gap', 'note')
                if i == 0 else None])
    br = b0 + (yr_hi - yr_lo)
    sb.note('The footprint pays below the national industry average in '
            f'every year of the {yr_lo}-{yr_hi} window but converges: '
            f'the gap narrows from {gap_2019 * 100:.1f}% in 2019 to '
            f'{gap_latest * 100:.1f}% in {yr_hi}. Suppressed '
            'state-quarters make footprint employment a floor.')
    sb.blank()

    # Panel C. county depth
    sb.banner('Panel C. County depth: private ambulance employment per '
              '1,000 residents 65+, top-20 footprint counties by '
              'employment, 2024 (both sides green-linked)')
    sb.headers(['County (FIPS)', 'State', 'QCEW employment 2024 (link)',
                'Residents 65+ 2024 (link)',
                'Employment per 1,000 65+ (live)',
                'Establishments (link)', '', '', '',
                'Confound (in-row per house rule)'])
    c0 = sb.r + 1
    for i, (fips, r, emp, est) in enumerate(top):
        ai = arow.get(fips)
        rn = c0 + i
        cname = f'{ai[1]} ({fips})' if ai else f'({fips})'
        stname = ai[2] if ai else ''
        sb.row([(cname, 'src'), (stname, 'src'),
                (f"='QCEW_County_2024'!F{r}", 'link', lib.FMT_INT),
                (f"='County_Age_65plus'!I{ai[0]}" if ai else 'PENDING',
                 'link' if ai else 'note', lib.FMT_INT),
                (f'=IF(D{rn}=0,"n/a",C{rn}/(D{rn}/1000))', 'fml',
                 lib.FMT_DEC2),
                (f"='QCEW_County_2024'!E{r}", 'link', lib.FMT_INT),
                None, None, None,
                ('UI-covered private only; volunteers and fire-based '
                 'crews missing; jobs sit in the ESTABLISHMENT county '
                 '(HQ effect), not where crews run', 'note')])
    cr = c0 + len(top)
    name_arr = '{' + ','.join(f'"{STATE_NAME[s]}"' for s in FP) + '}'
    qc = lambda col: f"'QCEW_County_2024'!${col}${qc_lo}:${col}${qc_hi}"
    caa = lambda col: f"'County_Age_65plus'!${col}${ca_lo}:${col}${ca_max}"
    fp2_arr = '{' + ','.join(f'"{FIPS[s]}"' for s in FP) + '}'
    sb.row([('FOOTPRINT TOTAL (all counties, live)', 'label'), None,
            (f'=SUMPRODUCT(ISNUMBER(MATCH(LEFT({qc("A")},2),{fp2_arr},0))'
             f'*{qc("F")})', 'fml', lib.FMT_INT),
            (f'=SUMPRODUCT(ISNUMBER(MATCH({caa("A")},{name_arr},0))'
             f'*{caa("I")})', 'fml', lib.FMT_INT),
            (f'=IF(D{cr}=0,"n/a",C{cr}/(D{cr}/1000))', 'fml', lib.FMT_DEC2),
            None, None, None, None,
            ('suppressed counties count as zero employment: the ratio is '
             'a floor', 'note')])
    sb.blank()

    # Panel D. A.13 quarterly reads
    sb.banner('Panel D. Quarterly read 1 - establishment churn proxy by '
              'state (QCEW statewide establishment counts, '
              f'{yr_lo}Q1-{yr_hi}Q{last_q[1]})')
    sb.headers(['State', f'Establishments {yr_lo}Q1 (link)',
                f'Establishments {yr_hi}Q{last_q[1]} (link)',
                'Net change (live)', 'Quarters count rose',
                'Quarters count fell', 'Quarters flat', '', '', 'Note'])
    d0 = sb.r + 1
    for i, s in enumerate(FP):
        a = FIPS[s] + '000'
        rn = d0 + i
        ups, downs, flat = churn[s]
        sb.row([(STATE_NAME[s], 'text'),
                (f"={sumifs('E', yr_lo, 1, a)}", 'fml', lib.FMT_INT),
                (f"={sumifs('E', yr_hi, last_q[1], a)}", 'fml',
                 lib.FMT_INT),
                (f'=C{rn}-B{rn}', 'fml', lib.FMT_INT),
                (ups, 'src', lib.FMT_INT), (downs, 'src', lib.FMT_INT),
                (flat, 'src', lib.FMT_INT), None, None,
                ('QoQ count changes are an entries/exits PROXY: QCEW '
                 'publishes net counts, not gross openings and closures',
                 'note') if i == 0 else None])
    sb.blank()

    sb.banner('Panel D. Quarterly read 2 - average weekly wage vs the '
              'AIF path (extends finding 45 to quarterly grain; AIF '
              'green-linked to Payment_Rules)')
    sb.headers(['Quarter', 'US private avg weekly wage $ (link)',
                f'Wage index (2019Q4=100)', 'AIF for the year (link)',
                'AIF-compounded payment index (2019Q4=100)',
                'Wage minus AIF index (points)', '', '', '', 'Note'])
    e0 = sb.r + 1
    base_rn = None
    prev_rn = None
    for i, (yr, q) in enumerate(quarters):
        rn = e0 + i
        cells = [(f'{yr} Q{q}', 'text'),
                 (f"={sumifs('J', yr, q, 'US000')}", 'fml', lib.FMT_USD)]
        if (yr, q) == (2019, 4):
            base_rn = rn
        cells.append((f'=IF($B${e0 + quarters.index((2019, 4))}=0,"n/a",'
                      f'B{rn}/$B${e0 + quarters.index((2019, 4))}*100)',
                      'fml', lib.FMT_DEC1))
        if q == 1 and yr in AIF_ROW:
            cells.append((f"='Payment_Rules'!$B${AIF_ROW[yr]}", 'link',
                          lib.FMT_PCT1))
        else:
            cells.append(None)
        if (yr, q) < (2019, 4):
            cells.append(None)
            cells.append(None)
        elif (yr, q) == (2019, 4):
            cells.append(('=100', 'fml', lib.FMT_DEC1))
            cells.append((f'=C{rn}-E{rn}', 'fml', lib.FMT_DEC1))
        else:
            step = (f'=E{prev_rn}*(1+D{rn})' if (q == 1 and yr in AIF_ROW)
                    else f'=E{prev_rn}')
            cells.append((step, 'fml', lib.FMT_DEC1))
            cells.append((f'=C{rn}-E{rn}', 'fml', lib.FMT_DEC1))
        cells += [None, None, None]
        if i == 0:
            cells.append(('AIF before CY2020 is not carried on '
                          'Payment_Rules; the annual wage-vs-AIF series '
                          'lives on QCEW_EMS_Employment Panel B '
                          '(finding 45)', 'note'))
        elif (yr, q) == (2020, 2):
            cells.append(('COVID trough quarter', 'note'))
        elif (yr, q) == last_q:
            cells.append(('the scissors, quarterly: wage index '
                          f'{widx[last_q]:.1f} vs AIF path '
                          f'{aidx[last_q]:.1f}', 'note'))
        else:
            cells.append(None)
        sb.row(cells)
        if (yr, q) >= (2019, 4):
            prev_rn = rn
    er = e0 + len(quarters) - 1   # last quarter row
    sb.blank()

    sb.banner('Panel D. Quarterly read 3 - the COVID shock shape '
              '(US private ambulance employment, live links)')
    sb.headers(['Measure', 'Value', '', '', '', '', '', '', '', 'Note'])
    f0 = sb.r + 1
    emp_avg = lambda yr, q: (f"=({sumifs('F', yr, q, 'US000')}"
                             f"+{sumifs('G', yr, q, 'US000')}"
                             f"+{sumifs('H', yr, q, 'US000')})/3")
    sb.row([('US employment 2020Q1 (avg of months, live)', 'label'),
            (emp_avg(2020, 1), 'fml', lib.FMT_INT),
            None, None, None, None, None, None, None,
            ('pre-shock base', 'note')])
    sb.row([('US employment 2020Q2 (live)', 'label'),
            (emp_avg(2020, 2), 'fml', lib.FMT_INT),
            None, None, None, None, None, None, None, None])
    sb.row([('The dip (live)', 'label'),
            (f'=IF(B{f0}=0,"n/a",B{f0 + 1}/B{f0}-1)', 'fml', lib.FMT_PCT1),
            None, None, None, None, None, None, None,
            ('a demand shock, not a layoff wave alone: transports '
             'collapsed with ED avoidance', 'note')])
    rec_label = f'{recovery[0]} Q{recovery[1]}' if recovery else 'PENDING'
    sb.row([('First quarter back at the 2020Q1 level', 'label'),
            (rec_label, 'src'),
            (emp_avg(*recovery) if recovery else None, 'fml', lib.FMT_INT),
            (f'=IF(C{f0 + 3}>=B{f0},"confirmed","check")', 'fml'),
            None, None, None, None, None,
            ('four YEARS to re-crew: the labor base did not snap back '
             'with demand', 'note')])
    sb.blank()

    # Panel E. tightness
    sb.banner('Panel E. Tightness: wage growth against depth, state by '
              'state (matched pair of rankings - no composite index)')
    sb.headers(['State', f'Avg weekly wage 2019 $ (src)',
                f'Avg weekly wage {yr_hi} $ (src)',
                f'Growth 2019-{yr_hi} (live)',
                f'QCEW employment {yr_hi} (src, floor)',
                '65+ residents 2024 (link)',
                'Employment per 1,000 65+ (live)', 'Growth rank',
                'Depth rank (1 = thinnest)', 'Note'])
    g0 = sb.r + 1
    for i, s in enumerate(FP):
        rn = g0 + i
        note = None
        if s == tight_state:
            note = ('TIGHTEST by the two-test rule: top-2 wage growth '
                    'AND bottom-2 depth', 'note')
        elif s == d_rank[0]:
            note = ('thinnest printed depth is partly a suppression '
                    'floor: several state-quarters print zero', 'note')
        sb.row([(STATE_NAME[s], 'text'),
                (round(st19[s]), 'src', lib.FMT_USD),
                (round(st25[s]), 'src', lib.FMT_USD),
                (f'=IF(B{rn}=0,"n/a",C{rn}/B{rn}-1)', 'fml', lib.FMT_PCT1),
                (round(st_emp[s]), 'src', lib.FMT_INT),
                (f'=SUMIF({caa("A")},"{STATE_NAME[s]}",{caa("I")})',
                 'fml', lib.FMT_INT),
                (f'=IF(F{rn}=0,"n/a",E{rn}/(F{rn}/1000))', 'fml',
                 lib.FMT_DEC2),
                (g_rank.index(s) + 1, 'src', lib.FMT_INT),
                (d_rank.index(s) + 1, 'src', lib.FMT_INT),
                note])
    sb.note('Wage cells are 4-quarter averages of QCEW statewide average '
            'weekly wages (caches qcew_q_2019q1..q4 and '
            f'qcew_q_{yr_hi}q1..q{last_q[1]}); employment is the '
            f'{yr_hi} 4-quarter average. Confound, printed per house '
            'rule: employment is UI-covered private only, so depth is a '
            'floor everywhere and thinnest-looking states may be '
            'suppression artifacts, not deserts.')
    sb.blank()

    sb.banner('Read panel')
    sb.prose('Three reads. FIRST, the ladder: a paramedic costs '
             f'{(widest[0] - 1) * 100:.0f}% more than an EMT in '
             f'{STATE_NAME[widest[1]]} (the widest footprint premium) and '
             '26-49% more everywhere in the footprint - ALS capacity is '
             'a wage decision. SECOND, the level: the footprint pays '
             f'about {abs(gap_latest) * 100:.1f}% below '
             f'the national industry average in {yr_hi} and the gap is '
             'closing, while measured depth is thin and lumpy: 0.9 to '
             '2.8 UI-covered employees per 1,000 residents 65+ at state '
             'grain, and about 1 to over 17 across the top-20 counties, '
             'where small-county spikes are an establishment-county '
             '(HQ) artifact, not a staffing signal. '
             'THIRD, the scissors at quarterly grain (extends finding '
             f'45): since 2019Q4 the average weekly wage is up to index '
             f'{widx[last_q]:.0f} against an AIF-compounded payment path '
             f'of {aidx[last_q]:.0f} - a {scissors:.0f}-point gap that '
             'never closes in any quarter after 2020, with the COVID '
             f'trough ({dip * 100:.1f}% in 2020Q2) taking until '
             f'{rec_label} to re-crew. '
             f'{STATE_NAME[tight_state]} is the tightest footprint labor '
             'market by the printed two-test rule.')

    facts += [
        {'metric': 'Widest footprint paramedic-over-EMT median wage '
                   'premium', 'year': 2024,
         'value': round(widest[0], 3),
         'unit': f'ratio ({STATE_NAME[widest[1]]})', 'basis': 'DERIVED',
         'tier': 'A', 'source_keys': ['a12_oews'],
         'locator': 'Panel A live MAX over green-linked OEWS medians; '
                    f'{STATE_NAME[widest[1]]} paramedic '
                    f'{prem[widest[1]][0]:,.0f} vs EMT '
                    f'{prem[widest[1]][1]:,.0f}',
         'lives_on': 'Workforce_Depth',
         'cross_check': 'National extreme (WA, about 2.06x) noted in-row; '
                        'footprint premiums span 1.26x-1.49x'},
        {'metric': 'Footprint private-ambulance average annual pay vs '
                   'national', 'year': yr_hi,
         'value': round(gap_latest, 4),
         'unit': 'share gap (footprint below national)',
         'basis': 'DERIVED', 'tier': 'A', 'source_keys': ['a12_qcew'],
         'locator': f'Panel B row {yr_hi}: live SUMPRODUCT footprint pay '
                    f'(about {fp_pay[yr_hi]:,.0f}) vs QCEW_EMS_Employment '
                    'Panel B national',
         'lives_on': 'Workforce_Depth',
         'cross_check': f'Gap narrows from {gap_2019 * 100:.1f}% (2019) '
                        f'to {gap_latest * 100:.1f}% ({yr_hi}): footprint '
                        'converging on national pay'},
        {'metric': 'Quarterly wage-vs-AIF scissors, 2019Q4 to '
                   f'{yr_hi}Q{last_q[1]}', 'year': yr_hi,
         'value': round(scissors, 1),
         'unit': 'index points (2019Q4=100)', 'basis': 'DERIVED',
         'tier': 'A', 'source_keys': ['a12_qcew', 'a13_aif'],
         'locator': 'Panel D read 2, last row: wage index '
                    f'{widx[last_q]:.1f} minus AIF-compounded path '
                    f'{aidx[last_q]:.1f}',
         'lives_on': 'Workforce_Depth',
         'cross_check': 'Annual version is finding 45 '
                        '(QCEW_EMS_Employment Panel B): +5.0%/yr pay vs '
                        '+3.1%/yr AIF over 2014-2025'},
        {'metric': 'Tightest footprint EMS labor market (two-test rule: '
                   'top-2 wage growth AND bottom-2 depth)', 'year': yr_hi,
         'value': round(growth[tight_state], 3),
         'unit': f'wage growth 2019-{yr_hi} ({STATE_NAME[tight_state]}; '
                 f'depth {dens[tight_state]:.2f} per 1,000 65+)',
         'basis': 'DERIVED', 'tier': 'B',
         'source_keys': ['a12_qcew', 'a12_census65'],
         'locator': 'Panel E ranks; rule printed in the header and '
                    'banner - a matched pair of rankings, not a '
                    'composite index',
         'lives_on': 'Workforce_Depth',
         'cross_check': 'Iowa prints thinner depth but its employment '
                        'floor is suppression-driven; Kansas tops wage '
                        'growth outright'},
    ]

    findings += [
        {'id_hint': 70,
         'finding': 'The footprint EMS labor base is measurably cheap, '
                    'thin and converging: private-ambulance pay runs '
                    'about 3-5% below the national industry average '
                    'across the window and the gap is closing, the '
                    'paramedic-over-EMT premium spans 1.26x to '
                    f'{widest[0]:.2f}x by state, and depth spans 0.9 (a '
                    'suppression floor) to 2.8 UI-covered employees per '
                    '1,000 residents 65+ at state grain - lumpier still '
                    'at county grain, where the establishment-county '
                    'convention concentrates jobs. With crew labor '
                    'about 69.4% of '
                    'ground cost (GADCS, Cost_and_Capacity), the labor '
                    'ladder IS the unit-economics ladder.',
         'numbers': "='Workforce_Depth'!F" + str(br),
         'sources': 'a12_oews; a12_qcew; a12_qcew_county; a12_census65',
         'confidence': 'High as floors; suppression and volunteer '
                       'exclusion understate depth',
         'guardrail': 'QCEW is UI-covered employment - volunteers and '
                      'fire-based cross-staffed EMS are invisible, so '
                      'depth ratios are floors, not staffing adequacy '
                      'measures; OEWS medians are not firm-level costs. '
                      'Footprint provisional pending E.5.'},
        {'id_hint': 71,
         'finding': 'At quarterly grain the wage-payment scissors '
                    '(finding 45) never closes: since 2019Q4 the US '
                    'private ambulance average weekly wage reached index '
                    f'{widx[last_q]:.0f} against an AIF-compounded '
                    f'payment path of {aidx[last_q]:.0f} - a '
                    f'{scissors:.0f}-point wedge - while the COVID '
                    f'trough ({dip * 100:.1f}% employment dip in 2020Q2) '
                    f'took until {rec_label} to re-crew and footprint '
                    'establishment counts kept grinding UP in 8 of 10 '
                    'states. Capacity re-formed while its price outran '
                    'the Medicare update in every post-2020 quarter.',
         'numbers': "='Workforce_Depth'!F" + str(er),
         'sources': 'a12_qcew; a13_aif',
         'confidence': 'High; both series are complete censuses at this '
                       'grain',
         'guardrail': 'The AIF is a Medicare PRICE INDEX, not a revenue '
                      'guarantee, and the wage series averages all '
                      'occupations in NAICS 621910 - this is a '
                      'margin-pressure indicator, not a unit-cost '
                      'series. Establishment QoQ changes are a churn '
                      'proxy, not measured entries and exits.'},
    ]

    # ---- charts: two separate single-axis charts, side by side ----------
    lib.add_chart(
        ws, f'L{e0 - 1}',
        'US private ambulance avg weekly wage, quarterly',
        f"'Workforce_Depth'!$A${e0}:$A${er}",
        [('Avg weekly wage $', f"'Workforce_Depth'!$B${e0}:$B${er}")],
        kind='line', width=11.5, height=7.2, y_fmt='$#,##0')
    lib.add_chart(
        ws, f'S{e0 - 1}',
        'AIF-compounded payment index (2019Q4=100), step path',
        f"'Workforce_Depth'!$A${base_rn}:$A${er}",
        [('AIF payment index', f"'Workforce_Depth'!$E${base_rn}:$E${er}")],
        kind='line', width=11.5, height=7.2, y_fmt='#,##0')

    return {'facts': facts, 'sources': sources, 'excluded': excluded,
            'findings': findings,
            'meta': {'quarters': len(quarters), 'tightest': tight_state,
                     'scissors_pts': round(scissors, 1)}}
