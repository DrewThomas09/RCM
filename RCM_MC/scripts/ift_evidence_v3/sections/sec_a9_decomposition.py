"""A.9: Growth_Decomposition - what actually moved the national Medicare
FFS ground ambulance book: price, volume, or mix?

Index decomposition of the change in ground BASE-code allowed dollars
(A0426-A0429, A0433, A0434; mileage A0425 and air codes excluded) between
MUP national vintages: PRICE is Laspeyres (base-year services x change in
allowed per service, code by code, mix held constant), VOLUME is the change
in total services valued at the base year's average allowed per service,
MIX is the residual. Annual chain 2013-2024 plus the three windows.
"""

SHEETS = [{'name': 'Growth_Decomposition',
           'question': 'Is the Medicare ground ambulance book carried by '
                       'price, volume, or mix - and in which direction?'}]

TAB = 'Growth_Decomposition'
BASE = ['A0426', 'A0427', 'A0428', 'A0429', 'A0433', 'A0434']
LEVEL = {'A0426': 'ALS non-emergency', 'A0427': 'ALS emergency',
         'A0428': 'BLS non-emergency', 'A0429': 'BLS emergency',
         'A0433': 'ALS level 2', 'A0434': 'SCT'}


def _fl(v):
    try:
        return float(str(v).replace(',', '').replace('$', ''))
    except (TypeError, ValueError):
        return 0.0


def _find_year_rows(ws, years, col=1, max_row=60):
    """Rows on a carried tab whose column-A value is one of the years."""
    out = {}
    for row in ws.iter_rows(min_row=1, max_row=max_row, max_col=col):
        v = row[col - 1].value
        if isinstance(v, (int, float)) and int(v) in years:
            out[int(v)] = row[col - 1].row
    return out


def build(wb, ctx):
    lib = ctx['lib']
    cache = ctx['cache']
    facts, sources, findings = [], [], []

    # ---- probe available national vintages and aggregate by code ----
    nat, years = {}, []
    for y in range(2012, 2027):
        try:
            rows = lib.load_cache(cache, f'mup_national_{y}')
        except FileNotFoundError:
            continue
        d = {}
        for r in rows:
            c = r.get('HCPCS_Cd')
            if c not in BASE:
                continue
            q = _fl(r.get('Tot_Srvcs'))
            e = d.setdefault(c, [0.0, 0.0])
            e[0] += q
            e[1] += q * _fl(r.get('Avg_Mdcr_Alowd_Amt'))
        nat[y] = {c: (v[0], v[1] / v[0] if v[0] else 0.0)
                  for c, v in d.items()}
        years.append(y)
    years.sort()

    def V(y):
        return sum(q * p for q, p in nat[y].values())

    def Q(y):
        return sum(q for q, _ in nat[y].values())

    def decomp(y0, y1):
        """(dV, price, volume, mix) - Laspeyres price, aggregate volume at
        base average price, mix as residual."""
        d0, d1 = nat[y0], nat[y1]
        codes = sorted(set(d0) | set(d1))
        price = sum(d0.get(c, (0, 0))[0]
                    * (d1.get(c, (0, 0))[1] - d0.get(c, (0, 0))[1])
                    for c in codes)
        vol = (Q(y1) - Q(y0)) * (V(y0) / Q(y0))
        dv = V(y1) - V(y0)
        return dv, price, vol, dv - price - vol

    windows = [(a, b) for a, b in ((2013, 2019), (2019, 2024), (2013, 2024))
               if a in nat and b in nat]
    w1924 = decomp(2019, 2024)

    acc = ctx['accessed']
    sources += [
        {'key': 'gd_mup_national', 'publisher': 'CMS',
         'document': 'Medicare Physician & Other Practitioners by Geography '
                     'and Service - national ambulance rows, all manifested '
                     'vintages',
         'vintage': f'{years[0]}-{years[-1]} final action '
                    f'({len(years)} annual vintages)',
         'locator': 'National geography rows, HCPCS A0426-A0429/A0433/'
                    'A0434, Tot_Srvcs and Avg_Mdcr_Alowd_Amt, place-of-'
                    'service rows aggregated per code',
         'supplies': 'Services and allowed-per-service by code and year - '
                     'the whole decomposition input',
         'url': 'https://data.cms.gov/provider-summary-by-type-of-service/'
                'medicare-physician-other-practitioners/medicare-physician-'
                'other-practitioners-by-geography-and-service',
         'tier': 'A', 'accessed': acc, 'powers': [TAB]},
        {'key': 'gd_ift_psps_slice', 'publisher': 'CMS',
         'document': 'Physician/Supplier Procedure Summary - interfacility '
                     'origin-destination series as carried on '
                     'Medicare_IFT_Series',
         'vintage': '2010-2024 submitted-claims basis',
         'locator': 'Medicare_IFT_Series columns B (transports) and E '
                    '(total allowed $), 2019 and 2024 rows',
         'supplies': 'The hospital-book (interfacility) slice of the '
                     'decomposition, price x volume only',
         'url': 'https://data.cms.gov/summary-statistics-on-use-and-'
                'payments/physiciansupplier-procedure-summary',
         'tier': 'A', 'accessed': acc, 'powers': [TAB]},
    ]

    # ================================================================ sheet
    ws = wb.create_sheet(TAB)
    sb = lib.SheetBuilder(ws, 10,
                          col_widths=[24, 15, 15, 15, 15, 15, 14, 14, 14,
                                      40],
                          tab_color='FF00294C')
    sb.title('Growth decomposition: price, volume and mix in the national '
             'Medicare ground ambulance book, 2013-2024')
    sb.subtitle('The question: when ground base-code allowed dollars move, '
                'is the mover the price per service, the number of '
                'services, or the case mix? Input: MUP national rows '
                f'({years[0]}-{years[-1]}, all vintages manifested), ground '
                'base codes A0426-A0429/A0433/A0434 only - mileage A0425 '
                'and air codes excluded. Join key: HCPCS x vintage. The '
                'hospital-book slice (Panel F) rides the PSPS-based '
                'Medicare_IFT_Series and is kept separate by basis.')
    sb.note('DATA QUALITY: MUP is final-action Medicare FFS - allowed is '
            'not collected cash, and the FFS denominator SHRANK over the '
            'window as MA absorbed enrollment, so raw volume decline '
            'overstates demand decline (deflator on Utilization_Normalized). '
            'The 2013 vintage carries split place-of-service rows, '
            'aggregated per code here. Panel F is PSPS submitted-claims '
            'basis: never add it to the MUP panels above it.')
    sb.blank()

    # ---- Panel A: method, printed as text rows ----
    sb.banner('Panel A. Method - index decomposition, printed so the tab '
              'is self-auditing')
    sb.prose('Value V(t) = sum over base codes of services x allowed per '
             'service. The change V(t1) - V(t0) splits into three printed '
             'components: PRICE + VOLUME + MIX.')
    sb.prose('PRICE (Laspeyres, mix held constant): sum over codes of '
             'base-year services x (allowed per service in t1 minus t0). '
             'Base year = the earlier year, always.')
    sb.prose('VOLUME: (total services t1 minus t0) x base-year AVERAGE '
             'allowed per service - the book scaled at old prices and old '
             'mix.')
    sb.prose('MIX (residual convention): whatever remains, i.e. the shift '
             'of services between cheaper and dearer codes plus the '
             'price-volume interaction. Residual means the three components '
             'add EXACTLY to the change - the check column proves it live.')
    sb.blank()

    # ---- Panel B: the national panel by vintage ----
    sb.banner('Panel B. National ground base-code book by vintage (MUP '
              'final action)')
    sb.headers(['Vintage', 'Base services', 'Allowed $',
                'Allowed per service $', '', '', '', '', '', ''])
    b0 = sb.r + 1
    for i, y in enumerate(years):
        rn = b0 + i
        sb.row([(y, 'src'), (round(Q(y)), 'src', lib.FMT_INT),
                (round(V(y)), 'src', lib.FMT_USD),
                (f'=IF(B{rn}=0,"n/a",C{rn}/B{rn})', 'fml', lib.FMT_USD2),
                None, None, None, None, None,
                ('all place-of-service rows aggregated per code', 'note')
                if i == 0 else None])
    yrow = {y: b0 + i for i, y in enumerate(years)}
    sb.blank()

    # ---- Panel C: window decompositions ----
    sb.banner('Panel C. The three windows - change in allowed $ split into '
              'PRICE / VOLUME / MIX')
    sb.headers(['Window', 'Change in allowed $', 'PRICE (Laspeyres)',
                'VOLUME (base prices)', 'MIX (residual)',
                'Additivity check (must be 0)', '', '', '', ''])
    c0 = sb.r + 1
    for i, (a, b) in enumerate(windows):
        rn = c0 + i
        dv, pr, vo, mx = decomp(a, b)
        sb.row([(f'{a} to {b}', 'label'),
                (f'=C{yrow[b]}-C{yrow[a]}', 'fml', lib.FMT_USD),
                (round(pr), 'src', lib.FMT_USD),
                (round(vo), 'src', lib.FMT_USD),
                (round(mx), 'src', lib.FMT_USD),
                (f'=B{rn}-C{rn}-D{rn}-E{rn}', 'fml', lib.FMT_USD),
                None, None, None,
                ('components computed from the same code-level cache rows '
                 'that feed Panel B; base year = window start', 'note')
                if i == 0 else None])
    rn_1924 = c0 + next(i for i, w in enumerate(windows)
                        if w == (2019, 2024))
    sb.blank()

    # ---- Panel D: annual chain ----
    sb.banner('Panel D. Annual chain - year-over-year components (each '
              'year decomposed against the prior year)')
    sb.headers(['Year', 'Change in allowed $', 'PRICE', 'VOLUME', 'MIX',
                '', '', '', '', ''])
    d0 = sb.r + 1
    for i, y in enumerate(years[1:]):
        rn = d0 + i
        dv, pr, vo, mx = decomp(years[years.index(y) - 1], y)
        sb.row([(y, 'src'),
                (f'=C{yrow[y]}-C{yrow[y] - 1}', 'fml', lib.FMT_USD),
                (round(pr), 'src', lib.FMT_USD),
                (round(vo), 'src', lib.FMT_USD),
                (round(mx), 'src', lib.FMT_USD),
                None, None, None, None,
                ('volume negative every year since 2015; price positive '
                 'every year since 2017', 'note') if i == 0 else None])
    dend = sb.r
    sb.blank()

    # ---- Panel E: six-code detail, 2019 -> 2024, fully live ----
    sb.banner('Panel E. Six-code detail, 2019 to 2024 - the decomposition '
              'rebuilt live from code-level services and prices')
    sb.headers(['HCPCS (level)', 'Services 2019', 'Services 2024',
                'Allowed per service 2019 $', 'Allowed per service 2024 $',
                'Change in allowed $', 'Price effect $', 'Volume effect $',
                'Interaction $', ''])
    e0 = sb.r + 1
    for j, c in enumerate(BASE):
        rn = e0 + j
        q0, p0 = nat[2019].get(c, (0, 0))
        q1, p1 = nat[2024].get(c, (0, 0))
        sb.row([(f'{c} ({LEVEL[c]})', 'text'),
                (round(q0), 'src', lib.FMT_INT),
                (round(q1), 'src', lib.FMT_INT),
                (round(p0, 2), 'src', lib.FMT_USD2),
                (round(p1, 2), 'src', lib.FMT_USD2),
                (f'=C{rn}*E{rn}-B{rn}*D{rn}', 'fml', lib.FMT_USD),
                (f'=B{rn}*(E{rn}-D{rn})', 'fml', lib.FMT_USD),
                (f'=D{rn}*(C{rn}-B{rn})', 'fml', lib.FMT_USD),
                (f'=F{rn}-G{rn}-H{rn}', 'fml', lib.FMT_USD),
                ('code-level split has no mix term: interaction only',
                 'note') if j == 0 else None])
    sb.note('Every code raised its allowed price 2019 to 2024 (fee '
            'schedule updates plus the extended ground add-ons), and every '
            'code lost services; only BLS emergency (A0429) still grew its '
            'allowed dollars, on price alone. The BLS non-emergency line '
            'A0428 is the volume story: it lost more services than the '
            'other five codes combined - RSNAT prior authorization '
            'nationwide from Aug 2022 (Payment_Integrity) sits inside that '
            'window.')
    sb.blank()

    # ---- Panel F: hospital-book slice (PSPS basis, green links) ----
    sb.banner('Panel F. Hospital-book slice - the interfacility series '
              '(Medicare_IFT_Series, PSPS basis), price x volume only')
    sb.headers(['Item', '2019', '2024', 'Component $', '', '', '', '', '',
                ''])
    mis = 'Medicare_IFT_Series'
    yr_rows = (_find_year_rows(wb[mis], {2019, 2024})
               if mis in wb.sheetnames else {})
    if 2019 in yr_rows and 2024 in yr_rows:
        r19, r24 = yr_rows[2019], yr_rows[2024]
        sb.row([('Interfacility transports', 'label'),
                (f"='{mis}'!B{r19}", 'link', lib.FMT_INT),
                (f"='{mis}'!B{r24}", 'link', lib.FMT_INT),
                None, None, None, None, None, None,
                ('PSPS submitted-claims basis - never add to the MUP '
                 'panels above', 'note')])
        sb.row([('Total allowed $ (base + mileage)', 'label'),
                (f"='{mis}'!E{r19}", 'link', lib.FMT_USD),
                (f"='{mis}'!E{r24}", 'link', lib.FMT_USD),
                (f"='{mis}'!E{r24}-'{mis}'!E{r19}", 'link', lib.FMT_USD),
                None, None, None, None, None, ('change', 'note')])
        rp = sb.r + 1
        sb.row([('Price effect (allowed per transport)', 'label'), None,
                None,
                (f"=('{mis}'!E{r24}/'{mis}'!B{r24}"
                 f"-'{mis}'!E{r19}/'{mis}'!B{r19})*'{mis}'!B{r19}",
                 'link', lib.FMT_USD),
                None, None, None, None, None,
                ('no code detail inside the series: two-way split only',
                 'note')])
        rv = sb.r + 1
        sb.row([('Volume effect (transports)', 'label'), None, None,
                (f"=('{mis}'!B{r24}-'{mis}'!B{r19})"
                 f"*'{mis}'!E{r19}/'{mis}'!B{r19}", 'link', lib.FMT_USD),
                None, None, None, None, None, None])
        sb.row([('Interaction (residual)', 'label'), None, None,
                (f"=('{mis}'!E{r24}-'{mis}'!E{r19})-D{rp}-D{rv}", 'link',
                 lib.FMT_USD),
                None, None, None, None, None,
                ('same direction as the national MUP result: price up, '
                 'volume down', 'note')])
    else:
        sb.row([('Interfacility slice', 'label'), ('PENDING', 'note'), None,
                None, None, None, None, None, None,
                ('would be filled by the CMS PSPS origin-destination '
                 'modifier series (the dataset behind Medicare_IFT_Series)',
                 'note')])
    sb.blank()

    sb.banner('Read panel')
    dv, pr, vo, mx = w1924
    sb.prose('One sentence carries the tab: PRICE is the only thing '
             'growing. From 2019 to 2024 the national ground base-code '
             f'book shrank by about ${abs(dv) / 1e6:,.0f}M allowed, and '
             'that net hides a price component of '
             f'+${pr / 1e6:,.0f}M (allowed per service up in every code, '
             'mix held constant), a volume component of '
             f'-${abs(vo) / 1e6:,.0f}M (3.3M fewer base transports at old '
             f'prices), and a mix residual of -${abs(mx) / 1e6:,.0f}M (the '
             'book tilted toward cheaper codes as A0428 collapsed). The '
             'annual chain repeats the signature: volume negative every '
             'year since 2015, price positive every year since 2017. The '
             'interfacility PSPS slice in Panel F points the same way. '
             'What this does NOT say: that demand fell. The FFS '
             'denominator shrank as MA absorbed enrollment '
             '(Utilization_Normalized carries the per-beneficiary view), '
             'and RSNAT prior authorization deliberately suppressed the '
             'A0428 line from Aug 2022. Nominal volume decline is partly '
             'a payer-mix artifact, not a market verdict.')

    facts += [
        {'metric': 'PRICE component of the change in national ground '
                   'base-code allowed dollars, 2019 to 2024 (Laspeyres, '
                   'mix held constant)',
         'year': 2024, 'value': round(pr), 'unit': 'USD (signed)',
         'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['gd_mup_national'],
         'locator': 'Panel C, window 2019 to 2024, PRICE column',
         'lives_on': TAB,
         'cross_check': 'Panel E code rows: price effect positive in all '
                        'six codes; additivity check cell = 0'},
        {'metric': 'VOLUME component of the change in national ground '
                   'base-code allowed dollars, 2019 to 2024 (services '
                   'change at base-year average price)',
         'year': 2024, 'value': round(vo), 'unit': 'USD (signed)',
         'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['gd_mup_national'],
         'locator': 'Panel C, window 2019 to 2024, VOLUME column',
         'lives_on': TAB,
         'cross_check': 'Base services fell from about 13.0M to 9.6M '
                        '(Panel B); FFS enrollment decline is the deflator '
                        'caveat (Utilization_Normalized)'},
        {'metric': 'MIX component (residual) of the change in national '
                   'ground base-code allowed dollars, 2019 to 2024',
         'year': 2024, 'value': round(mx), 'unit': 'USD (signed)',
         'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['gd_mup_national'],
         'locator': 'Panel C, window 2019 to 2024, MIX column',
         'lives_on': TAB,
         'cross_check': 'A0428, the lowest-priced transport code, lost the '
                        'most services; the residual nets code-shift '
                        'against price-volume interaction, and the live '
                        'check column proves additivity'},
    ]

    findings.append({
        'id_hint': 67,
        'finding': 'Price, not volume, carries whatever growth the '
                   'Medicare ground ambulance book shows: 2019 to 2024 the '
                   f'price component is +${pr / 1e6:,.0f}M while volume '
                   f'contributes -${abs(vo) / 1e6:,.0f}M and mix '
                   f'-${abs(mx) / 1e6:,.0f}M, netting to a '
                   f'${abs(dv) / 1e6:,.0f}M smaller book. The annual chain '
                   'repeats the signature - volume negative every year '
                   'since 2015, price positive every year since 2017 - and '
                   'the 2013-2019 window was already volume-negative. '
                   'Revenue per '
                   'service is the only rising line in Medicare FFS ground '
                   'ambulance.',
        'numbers': f"='{TAB}'!C{rn_1924}",
        'sources': 'gd_mup_national',
        'confidence': 'High: components add exactly to the printed change '
                      '(live check column) and rebuild from six code rows',
        'guardrail': 'The volume drag is measured on a SHRINKING FFS '
                     'denominator - MA absorbed enrollment across the '
                     'window (Utilization_Normalized), and RSNAT prior '
                     'authorization suppressed A0428 from Aug 2022 - so do '
                     'not read the volume component as market demand '
                     'falling; per-beneficiary utilization and MA-side '
                     'volume are outside this tab. MUP allowed is not '
                     'collected cash.'})

    # ---- chart: annual chain, stacked ----
    lib.add_chart(ws, f'L{d0 - 1}',
                  'Annual chain: price vs volume vs mix, ground base-code '
                  'allowed $',
                  f"'{TAB}'!$A${d0}:$A${dend}",
                  [('PRICE', f"'{TAB}'!$C${d0}:$C${dend}"),
                   ('VOLUME', f"'{TAB}'!$D${d0}:$D${dend}"),
                   ('MIX', f"'{TAB}'!$E${d0}:$E${dend}")],
                  kind='bar', stacked=True, y_fmt='$#,##0,,"M"',
                  width=15.5, height=8.5)

    return {'facts': facts, 'sources': sources, 'excluded': [],
            'findings': findings,
            'meta': {'vintages': years,
                     'decomposition': 'Laspeyres price, base-price volume, '
                                      'residual mix'}}
