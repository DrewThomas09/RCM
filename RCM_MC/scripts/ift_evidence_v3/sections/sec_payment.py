"""Group P — Payment depth: GPCI_Localities, Derived_Rate_Card,
Service_Level_Economics, Commercial_Context_APCD.

Data sources (all vendored files or repo accessors run at build time):
  * rcm_mc/data/vendor/cms_gpci/GPCI2025.csv via rcm_mc.data.cms_gpci
  * rcm_mc.market_reports.ift_service_levels (fee_rows, medicare_mix,
    payment_mechanics, mix_readings) — verified July 2026
  * rcm_mc.market_reports.ift_analytics._AMBULANCE_RVU (A0432 RVU only)
  * rcm_mc/data/vendor/payer_data/reference_based_pricing.csv (CIVHC CO APCD)
"""
import csv
import statistics
import sys

sys.path.insert(0, '/home/user/RCM/RCM_MC')
sys.path.insert(0, '/home/user/RCM')

NAVY = 'FF00294C'

SHEETS = [
    {'name': 'GPCI_Localities', 'tab_color': NAVY},
    {'name': 'Derived_Rate_Card', 'tab_color': NAVY},
    {'name': 'Service_Level_Economics', 'tab_color': NAVY},
    {'name': 'Commercial_Context_APCD', 'tab_color': NAVY},
]

FMT_GPCI = '0.000'
FMT_FACTOR = '0.0000'
FMT_D3 = '0.000;(0.000)'


# ── data pulls ───────────────────────────────────────────────────────────────

def _load_gpci():
    from rcm_mc.data import cms_gpci
    return cms_gpci.gpci_localities()


def _load_service_levels():
    from rcm_mc.market_reports import ift_service_levels as sl
    return {
        'fee_rows': sl.fee_rows(),
        'mix': sl.medicare_mix(),
        'mechanics': sl.payment_mechanics(),
        'readings': sl.mix_readings(),
        'cf2026': sl._CY2026_CF,
        'mileage2026': sl._CY2026_MILEAGE,
    }


def _load_a0432_rvu():
    from rcm_mc.market_reports import ift_analytics
    for code, label, rvu in ift_analytics._AMBULANCE_RVU:
        if code == 'A0432':
            return label, rvu
    return None, None


def _load_apcd(repo):
    path = (repo + '/RCM_MC/rcm_mc/data/vendor/payer_data/'
            'reference_based_pricing.csv')
    rows = list(csv.DictReader(open(path)))
    statewide, provider = {}, {}
    for r in rows:
        key = (r['claim_type'], r['year'])
        if r['urban_rural'] == 'STATEWIDE':
            statewide[key] = (float(r['hospital_pct_medicare']),
                              int(r['claims']))
        else:
            provider.setdefault(key, []).append(
                (float(r['hospital_pct_medicare']), int(r['claims'] or 0)))
    dist = {}
    for key, vals in provider.items():
        ratios = sorted(v[0] for v in vals)
        q1, med, q3 = statistics.quantiles(ratios, n=4, method='inclusive')
        dist[key] = {
            'n': len(ratios), 'claims': sum(v[1] for v in vals),
            'min': ratios[0], 'p25': q1, 'median': med, 'p75': q3,
            'max': ratios[-1],
        }
    return len(rows), statewide, dist


# ══════════════════════════════════════════════════════════════════════════
# Tab 1 — GPCI_Localities
# ══════════════════════════════════════════════════════════════════════════

def _build_gpci(wb, lib, locs, accessed, facts):
    ws = wb.create_sheet('GPCI_Localities')
    b = lib.SheetBuilder(
        ws, 9, col_widths=[9, 7, 9, 46, 11, 11, 11, 14, 30],
        tab_color=NAVY)
    b.title('GPCI localities — the geographic price term of the Medicare '
            'Ambulance Fee Schedule (CY2025)')
    b.subtitle(
        'The question: how much does the Medicare ground-ambulance base rate '
        'move with geography? Under 42 CFR 414.610(c)(4) the practice-expense '
        '(PE) GPCI applies to 70% of the base rate and the remaining 30% is '
        'unadjusted — so the ambulance geographic factor for every locality '
        'is 0.7 x PE GPCI + 0.3, derived below as a live formula per row '
        'over the full CY2025 CMS locality file (Addendum E).')
    b.blank()
    b.banner('CY2025 PFS payment localities — CMS Addendum E '
             f'({len(locs)} localities incl. DC / PR / VI)')
    b.headers(['MAC', 'State', 'Locality #', 'Locality name',
               '2025 PW GPCI (with 1.0 floor)', '2025 PE GPCI',
               '2025 MP GPCI',
               'Ambulance geographic factor = 0.7 x PE + 0.3 (DERIVED)',
               'Basis'])
    d0 = b.r + 1
    for loc in locs:
        r = b.r + 1
        b.row([
            (loc['mac'], 'src'),
            (loc['state'], 'src'),
            (loc['locality'], 'src'),
            (loc['name'], 'src'),
            (loc['work'], 'src', FMT_GPCI),
            (loc['pe'], 'src', FMT_GPCI),
            (loc['mp'], 'src', FMT_GPCI),
            (f'=0.7*F{r}+0.3', 'fml', FMT_FACTOR),
            ('GOV (cols E-G) · DERIVED (col H)', 'note'),
        ])
    d1 = b.r
    rng = lambda c: f'${c}${d0}:${c}${d1}'  # noqa: E731

    b.blank()
    b.banner('National screens — live formulas over the locality table')
    b.row([None, None, None, ('Locality count (COUNT of PE GPCI column)',
                              'label'),
           None, None, None, (f'=COUNT({rng("F")})', 'fml', lib.FMT_INT),
           ('DERIVED', 'note')])
    r_count = b.r
    b.row([None, None, None,
           ('Unweighted mean across all localities', 'label'),
           (f'=AVERAGE({rng("E")})', 'fml', FMT_FACTOR),
           (f'=AVERAGE({rng("F")})', 'fml', FMT_FACTOR),
           (f'=AVERAGE({rng("G")})', 'fml', FMT_FACTOR),
           (f'=AVERAGE({rng("H")})', 'fml', FMT_FACTOR),
           ('DERIVED', 'note')])
    r_mean = b.r
    b.row([None, None, None, ('Minimum', 'label'),
           (f'=MIN({rng("E")})', 'fml', FMT_FACTOR),
           (f'=MIN({rng("F")})', 'fml', FMT_FACTOR),
           (f'=MIN({rng("G")})', 'fml', FMT_FACTOR),
           (f'=MIN({rng("H")})', 'fml', FMT_FACTOR),
           ('DERIVED', 'note')])
    r_min = b.r
    b.row([None, None, None, ('Maximum', 'label'),
           (f'=MAX({rng("E")})', 'fml', FMT_FACTOR),
           (f'=MAX({rng("F")})', 'fml', FMT_FACTOR),
           (f'=MAX({rng("G")})', 'fml', FMT_FACTOR),
           (f'=MAX({rng("H")})', 'fml', FMT_FACTOR),
           ('DERIVED', 'note')])
    r_max = b.r
    b.row([None, None, None,
           ('Max / min spread of the ambulance factor', 'label'),
           None, None, None,
           (f'=MAX({rng("H")})/MIN({rng("H")})', 'fml', lib.FMT_X),
           ('DERIVED', 'note')])
    r_spread = b.r
    b.row([None, None, None,
           ('Lowest ambulance-factor locality (INDEX/MATCH)', 'label'),
           None, None, None, None,
           (f'=INDEX({rng("D")},MATCH(MIN({rng("H")}),{rng("H")},0))',
            'fml')], wrap=True)
    b.row([None, None, None,
           ('Highest ambulance-factor locality (INDEX/MATCH)', 'label'),
           None, None, None, None,
           (f'=INDEX({rng("D")},MATCH(MAX({rng("H")}),{rng("H")},0))',
            'fml')], wrap=True)

    # state screen block — contiguous per-state sub-ranges (file is grouped
    # by state; asserted at build time so the MIN/AVERAGE/MAX ranges hold).
    spans, order = {}, []
    for i, loc in enumerate(locs):
        st = loc['state']
        if st not in spans:
            spans[st] = [d0 + i, d0 + i]
            order.append(st)
        else:
            assert spans[st][1] == d0 + i - 1, f'state {st} not contiguous'
            spans[st][1] = d0 + i
    b.blank()
    b.banner('State screens — min / mean / max ambulance geographic factor '
             'by state (live formulas over the locality table)')
    b.headers(['State', 'n localities', 'Min ambulance factor',
               'Mean ambulance factor', 'Max ambulance factor',
               'Mean PE GPCI', 'State max / min', '', 'Basis'])
    s0 = b.r + 1
    for st in order:
        a, z = spans[st]
        r = b.r + 1
        b.row([
            (st, 'src'),
            (f'=COUNTIF({rng("B")},A{r})', 'fml', lib.FMT_INT),
            (f'=MIN($H${a}:$H${z})', 'fml', FMT_FACTOR),
            (f'=AVERAGE($H${a}:$H${z})', 'fml', FMT_FACTOR),
            (f'=MAX($H${a}:$H${z})', 'fml', FMT_FACTOR),
            (f'=AVERAGE($F${a}:$F${z})', 'fml', FMT_FACTOR),
            (f'=E{r}/C{r}', 'fml', lib.FMT_X),
            None,
            ('DERIVED (over GOV rows)', 'note'),
        ])
    s1 = b.r

    b.blank()
    b.note('Source: CMS, "ADDENDUM E. FINAL CY 2025 GEOGRAPHIC PRACTICE COST '
           'INDICES (GPCIs) BY STATE AND MEDICARE LOCALITY" — the CY2025 PFS '
           'GPCI file distributed in the CMS RVU25A relative-value package '
           '(the October RVU25D release is byte-identical, so these values '
           'held all year). MAC assignments as of November 22, 2023.')
    b.note('Provenance: vendored at rcm_mc/data/vendor/cms_gpci/GPCI2025.csv; '
           'registry row "cms_gpci_2025" in rcm_mc/data/vendor/'
           'source_registry.csv (ingested 2026-06-12; 109 locality rows; '
           'license: CMS public-use file, redistributable). Extraction: '
           'rcm_mc/data/cms_gpci.py::gpci_localities(). Accessed for this '
           f'build {accessed}. The raw CSV is 116 lines: 2 title + 1 column '
           'header + 109 locality rows + 4 footnote lines.')
    b.note('Ambulance geographic factor: 42 CFR 414.610(c)(4) — for ground '
           'services the PE GPCI applies to 70% of the base rate; the '
           'remaining 30% is not geographically adjusted. Column H is a live '
           'formula (0.7 x PE + 0.3), never a pasted result. The PW and MP '
           'GPCIs are carried for completeness only — they do NOT enter '
           'ambulance payment.')
    b.note('Floors, as published in the file: * Alaska work GPCI reflects a '
           '1.5 floor (MIPPA); ** PE GPCI reflects a 1.0 floor for frontier '
           'states (ACA). Work GPCI column carries the statutory 1.0 floor '
           'nationally.')
    b.note('Vintage: CY2025 is a single point-in-time file — no trend or '
           'CAGR is computable from this tab. CY2026 ambulance rates on '
           'Derived_Rate_Card pair the CY2026 conversion factor with this '
           'CY2025 GPCI vintage (labeled there).')

    lib.add_chart(
        ws, 'K6', 'Mean ambulance geographic factor by state (CY2025, '
        'unweighted across PFS localities)',
        f'GPCI_Localities!$A${s0}:$A${s1}',
        [('Mean ambulance factor (0.7 x PE + 0.3)',
          f'GPCI_Localities!$D${s0}:$D${s1}')],
        kind='bar', width=30, height=11, y_fmt='0.00',
        y_title='factor (national = ~1.0)')

    facts += [
        {'metric': 'CY2025 PFS payment localities carried (Addendum E)',
         'year': 'CY2025', 'value_ref': f'GPCI_Localities!H{r_count}',
         'unit': 'localities', 'basis': 'GOV', 'tier': 'A',
         'source_keys': ['cms_gpci_2025'],
         'locator': 'Addendum E, RVU25A package; vendored registry row '
                    'cms_gpci_2025 (109 locality rows incl. DC/PR/VI)',
         'lives_on': 'GPCI_Localities',
         'cross_check': 'registry row_count=109; raw CSV 116 lines incl. '
                        'headers/footnotes'},
        {'metric': 'National unweighted mean PE GPCI', 'year': 'CY2025',
         'value_ref': f'GPCI_Localities!F{r_mean}', 'unit': 'index',
         'basis': 'DERIVED', 'tier': 'A', 'source_keys': ['cms_gpci_2025'],
         'locator': 'AVERAGE over Addendum E PE GPCI column (109 localities)',
         'lives_on': 'GPCI_Localities',
         'cross_check': 'python recompute 1.0434'},
        {'metric': 'National unweighted mean ambulance geographic factor '
                   '(0.7 x PE + 0.3)', 'year': 'CY2025',
         'value_ref': f'GPCI_Localities!H{r_mean}', 'unit': 'factor',
         'basis': 'DERIVED', 'tier': 'A', 'source_keys': ['cms_gpci_2025',
                                                          'cfr_414_610'],
         'locator': '42 CFR 414.610(c)(4) 70/30 rule over Addendum E',
         'lives_on': 'GPCI_Localities',
         'cross_check': 'python recompute 1.0304'},
        {'metric': 'Lowest ambulance geographic factor (Mississippi)',
         'year': 'CY2025', 'value_ref': f'GPCI_Localities!H{r_min}',
         'unit': 'factor', 'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['cms_gpci_2025', 'cfr_414_610'],
         'locator': 'MIN over derived col H; MS PE GPCI 0.852 -> 0.8964',
         'lives_on': 'GPCI_Localities',
         'cross_check': '0.7*0.852+0.3 = 0.8964'},
        {'metric': 'Highest ambulance geographic factor (San Jose-Sunnyvale-'
                   'Santa Clara, CA)', 'year': 'CY2025',
         'value_ref': f'GPCI_Localities!H{r_max}', 'unit': 'factor',
         'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['cms_gpci_2025', 'cfr_414_610'],
         'locator': 'MAX over derived col H; Santa Clara/San Benito PE GPCI '
                    '1.435 -> 1.3045', 'lives_on': 'GPCI_Localities',
         'cross_check': '0.7*1.435+0.3 = 1.3045'},
        {'metric': 'Max/min spread of the ambulance geographic factor',
         'year': 'CY2025', 'value_ref': f'GPCI_Localities!H{r_spread}',
         'unit': 'x', 'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['cms_gpci_2025', 'cfr_414_610'],
         'locator': 'MAX/MIN over derived col H',
         'lives_on': 'GPCI_Localities',
         'cross_check': '1.3045/0.8964 = 1.455x — geography moves the base '
                        'rate by at most ~46% end to end'},
    ]
    return r_mean  # row of the national means (col H = amb factor mean)


# ══════════════════════════════════════════════════════════════════════════
# Tab 2 — Derived_Rate_Card
# ══════════════════════════════════════════════════════════════════════════

def _build_rate_card(wb, lib, sl, a0432, gpci_mean_row, accessed, facts):
    ws = wb.create_sheet('Derived_Rate_Card')
    b = lib.SheetBuilder(
        ws, 12, col_widths=[10, 26, 8, 13, 13, 12, 12, 13, 13, 9, 15, 52],
        tab_color=NAVY)
    cf26, cf25 = sl['cf2026'], 278.98
    b.title('Derived Medicare ground rate card — RVU x conversion factor x '
            'geography, CY2026')
    b.subtitle(
        'The question: what does Medicare actually pay per ground transport, '
        'by service level, before and after geography and the statutory '
        'add-ons? Every rate on this tab is a live Excel formula from GOV '
        'inputs shown on-sheet: base = RVU x CY2026 conversion factor '
        f'(${cf26}); geography = 0.7 x PE GPCI + 0.3 (link to '
        'GPCI_Localities); add-ons +2% urban / +3% rural / +22.6% '
        'super-rural per 42 U.S.C. 1395m(l)(12)-(13).')
    b.blank()
    b.banner('Inputs — conversion factor + geographic factor (GOV, blue; '
             'links, green)')
    b.headers(['Input', 'Value', 'Unit', 'Detail', '', '', '', '', '', '',
               'Basis', 'Source'])
    b.row([('CY2026 AFS ground conversion factor (CF)', 'label'),
           (cf26, 'src', lib.FMT_USD2), ('$/RVU', 'text'),
           ('Published CY2026 ambulance fee schedule conversion factor',
            'text'), None, None, None, None, None, None, ('GOV', 'text'),
           ('CMS Ambulance Fee Schedule public use files (CY2026); MedPAC '
            'June 2026 Report to Congress, Ch. 6', 'note')], wrap=True)
    r_cf26 = b.r
    b.row([('CY2025 AFS ground CF (prior year)', 'label'),
           (cf25, 'src', lib.FMT_USD2), ('$/RVU', 'text'),
           ('Prior-year CF, carried for the update trend', 'text'),
           None, None, None, None, None, None, ('GOV', 'text'),
           ('MedPAC June 2026 Ch. 6; MedPAC March 2025 mandated-report '
            'slides', 'note')], wrap=True)
    r_cf25 = b.r
    b.row([('CF update, CY2025 -> CY2026 (1-yr window)', 'label'),
           (lib.cagr_formula(f'$B${r_cf26}', f'$B${r_cf25}', 1), 'fml',
            lib.FMT_PCT1), ('%/yr', 'text'),
           ('Live formula (B-cells above). Equals the published CY2026 '
            'Ambulance Inflation Factor of +2.0%', 'text'),
           None, None, None, None, None, None, ('DERIVED', 'text'),
           ('Cross-check: CMS Transmittal 13464 / CR 14269 (CY2026 AIF)',
            'note')], wrap=True)
    r_cfup = b.r
    b.row([('National-average ambulance geographic factor (CY2025, '
            'unweighted)', 'label'),
           (f"='GPCI_Localities'!$H${gpci_mean_row}", 'link', FMT_FACTOR),
           ('factor', 'text'),
           ('Green link to GPCI_Localities national-screen mean (109 '
            'localities, unweighted). CMS publishes no transport-volume-'
            'weighted factor.', 'text'),
           None, None, None, None, None, None, ('DERIVED', 'text'),
           ('CMS CY2025 GPCI Addendum E + 42 CFR 414.610(c)(4)', 'note')],
          wrap=True)
    r_gaf = b.r

    b.blank()
    b.banner('Worked ground rate card — CY2026 base rates by HCPCS '
             '(ALL row math live formulas)')
    b.headers(['HCPCS', 'Service level', 'RVU',
               'National unadjusted base = RVU x CF',
               'x natl-avg geographic factor',
               'Urban origin +2%', 'Rural origin +3%',
               'Super-rural origin +22.6%',
               'Repo cross-check: ift_service_levels cy2026_base',
               'Delta (D-I)', 'Basis', 'Source'])
    codes = [(fr.hcpcs, fr.level, fr.rvu, fr.cy2026_base)
             for fr in sl['fee_rows']]
    codes.append(('A0432', a0432[0] or 'Paramedic Intercept',
                  a0432[1] or 1.75, None))
    card_rows = {}
    c0 = b.r + 1
    for hcpcs, level, rvu, repo_base in codes:
        r = b.r + 1
        card_rows[hcpcs] = r
        rvu_kind = 'src'
        cells = [
            (hcpcs, 'src'), (level, 'src'), (rvu, rvu_kind, lib.FMT_DEC2),
            (f'=C{r}*$B${r_cf26}', 'fml', lib.FMT_USD2),
            (f'=D{r}*$B${r_gaf}', 'fml', lib.FMT_USD2),
            (f'=D{r}*1.02', 'fml', lib.FMT_USD2),
            (f'=D{r}*1.03', 'fml', lib.FMT_USD2),
            (f'=D{r}*1.226', 'fml', lib.FMT_USD2),
        ]
        if repo_base is not None:
            cells += [(repo_base, 'src', lib.FMT_USD2),
                      (f'=D{r}-I{r}', 'fml', FMT_D3),
                      ('GOV (RVU) · DERIVED', 'text'),
                      ('RVU: CMS AFS PUF CY2026 (42 CFR 414 Subpart H '
                       'ladder), carried via ift_service_levels', 'note')]
        else:
            cells += [('n/a (repo carries no PI base)', 'note'), None,
                      ('SOURCED (RVU) · DERIVED', 'text'),
                      ('RVU 1.75 carried from repo ift_analytics, citing '
                       'the AFS RVU table via a PYA Medicare-payment '
                       'primer — RE-VERIFY against the CY2026 AFS PUF. '
                       'PI is a rural, limited-coverage benefit.', 'note')]
        b.row(cells, wrap=True)
    c1 = b.r

    b.blank()
    b.banner('Mileage — A0425, per loaded statute mile')
    b.headers(['Item', 'Value', 'Unit', 'Detail', '', '', '', '', '', '',
               'Basis', 'Source'])
    b.row([('A0425 CY2026 national rate', 'label'),
           (sl['mileage2026'], 'src', lib.FMT_USD2), ('$/mile', 'text'),
           ('Ground mileage, per loaded statute mile', 'text'),
           None, None, None, None, None, None, ('GOV', 'text'),
           ('MedPAC June 2026 Ch. 6; CMS AFS PUF CY2026', 'note')])
    r_mi26 = b.r
    b.row([('A0425 CY2026 urban', 'label'), (9.33, 'src', lib.FMT_USD2),
           ('$/mile', 'text'), None, None, None, None, None, None, None,
           ('GOV', 'text'), ('MedPAC June 2026 Ch. 6', 'note')])
    b.row([('A0425 CY2026 rural (miles 18+)', 'label'),
           (9.42, 'src', lib.FMT_USD2), ('$/mile', 'text'), None, None,
           None, None, None, None, None, ('GOV', 'text'),
           ('MedPAC June 2026 Ch. 6', 'note')])
    r_mirur = b.r
    b.row([('A0425 CY2026 rural miles 1-17 (statutory 1.5x)', 'label'),
           (f'=B{r_mirur}*1.5', 'fml', lib.FMT_USD2), ('$/mile', 'text'),
           ('Live formula: rural rate x 1.5 = $14.13', 'text'), None, None,
           None, None, None, None, ('DERIVED', 'text'),
           ('42 U.S.C. 1395m(l)(12); MedPAC June 2026 Ch. 6', 'note')])
    r_mi117 = b.r
    b.row([('A0425 CY2025 national (prior year)', 'label'),
           (8.97, 'src', lib.FMT_USD2), ('$/mile', 'text'), None, None,
           None, None, None, None, None, ('GOV', 'text'),
           ('MedPAC June 2026 Ch. 6', 'note')])
    r_mi25 = b.r
    b.row([('Mileage update, CY2025 -> CY2026 (1-yr window)', 'label'),
           (lib.cagr_formula(f'$B${r_mi26}', f'$B${r_mi25}', 1), 'fml',
            lib.FMT_PCT1), ('%/yr', 'text'),
           ('Live formula over the two mileage cells above', 'text'),
           None, None, None, None, None, None, ('DERIVED', 'text'),
           ('', 'note')])

    b.blank()
    b.banner('Add-on authority + policy risk (GOV)')
    b.row([('+2% urban / +3% rural add-ons', 'label'), None, None,
           ('42 U.S.C. 1395m(l)(12)(A): temporary percentage increases for '
            'ground transports originating in urban (+2%) and rural (+3%) '
            'areas.', 'text'), None, None, None, None, None, None,
           ('GOV', 'text'), ('42 U.S.C. 1395m(l)(12)', 'note')], wrap=True)
    b.row([('+22.6% super-rural base bump', 'label'), None, None,
           ('42 U.S.C. 1395m(l)(13): base-rate increase for transports '
            'originating in the lowest-quartile rural population-density '
            'areas ("super-rural"), set at 22.6%.', 'text'), None, None,
           None, None, None, None, ('GOV', 'text'),
           ('42 U.S.C. 1395m(l)(13); 42 CFR 414 Subpart H', 'note')],
          wrap=True)
    b.row([('Extension + cliff', 'label'), None, None,
           ('Extended by §6203 of the Consolidated Appropriations Act, 2026 '
            'through December 31, 2027 (CBO scored ~$197M); absent new '
            'legislation the add-ons lapse January 1, 2028.', 'text'),
           None, None, None, None, None, None, ('GOV', 'text'),
           ('CAA 2026 §6203 (Senate Finance section-by-section)', 'note')],
          wrap=True)
    b.row([('MedPAC read', 'label'), None, None,
           ('MedPAC notes the 2%/3% add-ons "did not have an underlying '
            'empirical basis."', 'text'), None, None, None, None, None,
           None, ('GOV', 'text'), ('MedPAC June 2026 Ch. 6', 'note')],
          wrap=True)

    b.blank()
    b.note('Display convention: the +2%/+3%/+22.6% columns are computed on '
           'the national unadjusted base for comparability. On an actual '
           'claim the add-on applies to the geographically adjusted amount '
           '(42 CFR 414.610(c)), so a locality rate card multiplies column '
           'E, not column D. Column E pairs the CY2026 CF with the CY2025 '
           'GPCI vintage (the vendored GPCI file) — a labeled vintage mix.')
    b.note('Cross-check vs v2.7: the v2.7 Payment_Rules tab carries the same '
           '7-code RVU ladder (GOV-A) at the CY2024 vintage — ground CF '
           '$272.44, mileage $8.76. Differences here are vintage, not '
           'disagreement. The repo cross-check column reproduces '
           'ift_service_levels.fee_rows() cy2026_base; deltas are pure '
           'cent-rounding (max $0.004).')
    b.note('Extraction: conversion factors, mileage and the 6-code RVU '
           'ladder from rcm_mc/market_reports/ift_service_levels.py '
           '(_FEE_TABLE, _CY2026_CF, _CY2026_MILEAGE, payment_mechanics; '
           'module sources verified July 2026); A0432 RVU from '
           f'rcm_mc/market_reports/ift_analytics.py. Accessed {accessed}.')

    lib.add_chart(
        ws, 'N7', 'CY2026 Medicare ground rate card — base and add-on '
        'variants by HCPCS (live formulas)',
        f'Derived_Rate_Card!$A${c0}:$A${c1}',
        [('National unadjusted base', f'Derived_Rate_Card!$D${c0}:$D${c1}'),
         ('Urban +2%', f'Derived_Rate_Card!$F${c0}:$F${c1}'),
         ('Rural +3%', f'Derived_Rate_Card!$G${c0}:$G${c1}'),
         ('Super-rural +22.6%', f'Derived_Rate_Card!$H${c0}:$H${c1}')],
        kind='bar', width=26, height=11, y_fmt='$#,##0',
        y_title='$ per transport (base rate)')

    facts += [
        {'metric': 'CY2026 AFS ground conversion factor', 'year': 'CY2026',
         'value_ref': f'Derived_Rate_Card!B{r_cf26}', 'unit': '$/RVU',
         'basis': 'GOV', 'tier': 'B',
         'source_keys': ['cms_afs_puf_cy2026', 'medpac_jun2026_ch6'],
         'locator': 'CY2026 AFS public use file; MedPAC Jun 2026 Ch.6',
         'lives_on': 'Derived_Rate_Card',
         'cross_check': 'v2.7 Payment_Rules CY2024 CF $272.44 (vintage)'},
        {'metric': 'CY2025 AFS ground conversion factor', 'year': 'CY2025',
         'value_ref': f'Derived_Rate_Card!B{r_cf25}', 'unit': '$/RVU',
         'basis': 'GOV', 'tier': 'B',
         'source_keys': ['medpac_jun2026_ch6', 'medpac_mar2025_slides'],
         'locator': 'MedPAC Jun 2026 Ch.6 (prior-year CF)',
         'lives_on': 'Derived_Rate_Card', 'cross_check': ''},
        {'metric': 'CF update CY2025->CY2026', 'year': 'CY2026',
         'value_ref': f'Derived_Rate_Card!B{r_cfup}', 'unit': '%/yr',
         'basis': 'DERIVED', 'tier': 'B',
         'source_keys': ['cms_transmittal_13464'],
         'locator': 'live formula (284.56/278.98)-1; equals published '
                    'CY2026 AIF +2.0%', 'lives_on': 'Derived_Rate_Card',
         'cross_check': 'CMS Transmittal 13464: AIF = CPI-U 2.7% - TFP '
                        '0.7% = 2.0%'},
        {'metric': 'SCT (A0434) CY2026 national unadjusted base',
         'year': 'CY2026',
         'value_ref': f"Derived_Rate_Card!D{card_rows['A0434']}",
         'unit': '$', 'basis': 'DERIVED', 'tier': 'B',
         'source_keys': ['cms_afs_puf_cy2026', 'medpac_jun2026_ch6'],
         'locator': 'live formula 3.25 RVU x $284.56 = $924.82',
         'lives_on': 'Derived_Rate_Card',
         'cross_check': 'repo cy2026_base column, delta < $0.005'},
        {'metric': 'BLS non-emergency (A0428) super-rural base',
         'year': 'CY2026',
         'value_ref': f"Derived_Rate_Card!H{card_rows['A0428']}",
         'unit': '$', 'basis': 'DERIVED', 'tier': 'B',
         'source_keys': ['usc_1395m_l', 'cms_afs_puf_cy2026'],
         'locator': 'live formula $284.56 x 1.226 = $348.87',
         'lives_on': 'Derived_Rate_Card',
         'cross_check': 'add-on % per 42 U.S.C. 1395m(l)(13)'},
        {'metric': 'Ground mileage A0425, CY2026 national', 'year': 'CY2026',
         'value_ref': f'Derived_Rate_Card!B{r_mi26}', 'unit': '$/mile',
         'basis': 'GOV', 'tier': 'B',
         'source_keys': ['medpac_jun2026_ch6', 'cms_afs_puf_cy2026'],
         'locator': 'MedPAC Jun 2026 Ch.6: $9.15/mile national',
         'lives_on': 'Derived_Rate_Card',
         'cross_check': 'v2.7 Payment_Rules CY2024 $8.76 (vintage)'},
        {'metric': 'Ground mileage A0425, rural miles 1-17', 'year': 'CY2026',
         'value_ref': f'Derived_Rate_Card!B{r_mi117}', 'unit': '$/mile',
         'basis': 'DERIVED', 'tier': 'B',
         'source_keys': ['medpac_jun2026_ch6', 'usc_1395m_l'],
         'locator': 'live formula $9.42 x 1.5 = $14.13',
         'lives_on': 'Derived_Rate_Card', 'cross_check': ''},
        {'metric': 'Paramedic Intercept (A0432) RVU', 'year': 'CY2026',
         'value_ref': f"Derived_Rate_Card!C{card_rows['A0432']}",
         'unit': 'RVU', 'basis': 'SOURCED', 'tier': 'B',
         'source_keys': ['cms_afs_puf_cy2026'],
         'locator': 'AFS RVU ladder; carried from repo ift_analytics '
                    '(cites the RVU table via a PYA Medicare-payment '
                    'primer) — RE-VERIFY against the CY2026 AFS PUF',
         'lives_on': 'Derived_Rate_Card',
         'cross_check': 'flagged re-verify; PI base column derived from '
                        'this RVU'},
    ]
    return r_cf26


# ══════════════════════════════════════════════════════════════════════════
# Tab 3 — Service_Level_Economics
# ══════════════════════════════════════════════════════════════════════════

def _build_sle(wb, lib, sl, cf_row, accessed, facts):
    ws = wb.create_sheet('Service_Level_Economics')
    b = lib.SheetBuilder(
        ws, 12, col_widths=[11, 24, 8, 13, 13, 12, 11, 11, 11, 15, 44, 52],
        tab_color=NAVY)
    b.title('Service-level economics — CY2026 fee ladder x CY2024 Medicare '
            'utilization, mechanics, and mix')
    b.subtitle(
        'The question: what does each ground service level earn and how much '
        'of the market does it carry? CY2026 rates (RVU x $284.56, live '
        'formulas linked to Derived_Rate_Card) against CY2024 published '
        'utilization (CMS Medicare Physician & Other Practitioners supplier '
        'file), the CY2025->CY2026 payment mechanics, and the GADCS / '
        'NEMSIS / MedPAC mix readings. Rows carried from '
        'rcm_mc.market_reports.ift_service_levels (53-source module, '
        'verified July 2026).')
    b.blank()
    b.banner('A. Fee ladder x utilization — 6 ground codes (CY2026 rates, '
             'CY2024 volumes)')
    b.headers(['HCPCS', 'Service level', 'RVU',
               'CY2026 national base $ (RVU x CF, link)',
               'CY2024 services (supplier claims)', 'CY2024 avg allowed $',
               'CY2024 avg paid $', 'Paid / allowed (DERIVED)',
               'CY2024 provider count', 'Basis', 'Source', 'Note'])
    a0 = b.r + 1
    fee_rows_ix = {}
    for fr in sl['fee_rows']:
        r = b.r + 1
        fee_rows_ix[fr.hcpcs] = r
        b.row([
            (fr.hcpcs, 'src'), (fr.level, 'src'),
            (fr.rvu, 'src', lib.FMT_DEC2),
            (f"=C{r}*'Derived_Rate_Card'!$B${cf_row}", 'link', lib.FMT_USD2),
            (fr.cy2024_services, 'src', lib.FMT_INT),
            (fr.cy2024_avg_allowed, 'src', lib.FMT_USD2),
            (fr.cy2024_avg_paid, 'src', lib.FMT_USD2),
            (f'=G{r}/F{r}', 'fml', lib.FMT_PCT1),
            (fr.cy2024_providers, 'src', lib.FMT_INT),
            ('GOV · DERIVED (D,H)', 'text'),
            ('CMS MedPOP by Geography & Service CY2024 (pub. May 2026); '
             'CMS AFS PUF CY2026; 42 CFR 414.610', 'note'),
            None,
        ])
    a1 = b.r
    r = b.r + 1
    b.row([('Total', 'label'), ('Six-code ground ladder', 'label'), None,
           None, (f'=SUM(E{a0}:E{a1})', 'fml', lib.FMT_INT),
           (f'=SUMPRODUCT(E{a0}:E{a1},F{a0}:F{a1})/SUM(E{a0}:E{a1})',
            'fml', lib.FMT_USD2),
           (f'=SUMPRODUCT(E{a0}:E{a1},G{a0}:G{a1})/SUM(E{a0}:E{a1})',
            'fml', lib.FMT_USD2),
           (f'=G{r}/F{r}', 'fml', lib.FMT_PCT1),
           ('do not sum', 'note'), ('DERIVED', 'text'),
           ('Weighted means are live SUMPRODUCT formulas', 'note'),
           ('Provider counts overlap across codes — never summed', 'note')])
    r_tot = b.r

    b.blank()
    b.banner('B. CY2024 Medicare service mix + 2011 -> 2024 drift '
             '(the 13-year pair)')
    b.headers(['HCPCS', 'Service level', 'CY2024 services (link to A)',
               'Share of six-code total (DERIVED)', 'CY2024 avg allowed '
               '(link)', '', '', '', '', 'Basis', 'Source', 'Note'])
    m0 = b.r + 1
    mix_ix = {}
    for fr in sl['fee_rows']:
        r = b.r + 1
        mix_ix[fr.hcpcs] = r
        b.row([
            (fr.hcpcs, 'src'), (fr.level, 'src'),
            (f'=E{fee_rows_ix[fr.hcpcs]}', 'link', lib.FMT_INT),
            (f'=C{r}/$E${r_tot}', 'fml', lib.FMT_PCT1),
            (f'=F{fee_rows_ix[fr.hcpcs]}', 'link', lib.FMT_USD2),
            None, None, None, None,
            ('DERIVED (off GOV)', 'text'),
            ('CMS MedPOP by Geography & Service CY2024', 'note'), None,
        ])
    m1 = b.r
    b.blank()
    b.headers(['Level group', '', '2024 share (from mix rows)',
               '2011 share (MedPAC Jun 2013)', 'Drift 2011->2024 (pp)',
               '', '', '', '', 'Basis', 'Source', 'Note'])
    drift = [
        ('BLS (A0428+A0429)', f"=D{mix_ix['A0428']}+D{mix_ix['A0429']}",
         0.609, 'BLS 60.9% of 2011 transports (42.0% non-emergency)'),
        ('ALS1 (A0426+A0427)', f"=D{mix_ix['A0426']}+D{mix_ix['A0427']}",
         0.384, ''),
        ('ALS2 (A0433)', f"=D{mix_ix['A0433']}", 0.009, ''),
        ('SCT (A0434)', f"=D{mix_ix['A0434']}", 0.008,
         'SCT was the fastest-growing type, +35.5% per FFS beneficiary '
         '2007-2011 (MedPAC 2013)'),
    ]
    dr0 = b.r + 1
    for name, f2024, s2011, note in drift:
        r = b.r + 1
        b.row([(name, 'label'), None, (f2024, 'fml', lib.FMT_PCT1),
               (s2011, 'src', lib.FMT_PCT1),
               (f'=C{r}-D{r}', 'fml', lib.FMT_PCT1),
               None, None, None, None,
               ('GOV (2011) · DERIVED', 'text'),
               ('MedPAC June 2013 mandated report Ch.7; CMS MedPOP CY2024',
                'note'), (note, 'note')], wrap=bool(note))
    dr1 = b.r
    b.row([('Trend flag', 'label'), None, None, None, None, None, None,
           None, None, ('—', 'note'),
           ('2-point pair, 13 years apart', 'note'),
           ('Same six-code ladder both years; 2011 = all claims (MedPAC), '
            '2024 = supplier file — direction-of-drift evidence only; no '
            'CAGR computed on shares.', 'note')], wrap=True)

    b.blank()
    b.banner('C. Payment mechanics — CY2025 -> CY2026 (GOV)')
    b.headers(['Item', 'Value', 'Unit', '', '', '', '', '', '', 'Basis',
               'Source', 'Detail / verbatim'])
    b.row([('Payment formula', 'label'), None, None, None, None, None, None,
           None, None, ('GOV', 'text'),
           ('42 CFR 414.610; MedPAC June 2026 Ch.6', 'note'),
           ('Paid = RVU x CF x (0.7 x PE GPCI + 0.3); mileage paid '
            'separately per loaded statute mile.', 'note')], wrap=True)
    b.row([('AIF CY2026 — CPI-U input', 'label'),
           (0.027, 'src', lib.FMT_PCT1), ('%', 'text'), None, None, None,
           None, None, None, ('GOV', 'text'),
           ('CMS Transmittal 13464 / CR 14269 (Nov 2025)', 'note'),
           ('"The TFP for CY 2026 is 0.7 percent and the CPI-U for 2026 is '
            '2.7... Therefore, the AIF for CY 2026 is 2.0 percent."',
            'note')], wrap=True)
    r_cpiu = b.r
    b.row([('AIF CY2026 — productivity (TFP) input', 'label'),
           (0.007, 'src', lib.FMT_PCT1), ('%', 'text'), None, None, None,
           None, None, None, ('GOV', 'text'),
           ('CMS Transmittal 13464 / CR 14269', 'note'), None])
    r_tfp = b.r
    b.row([('AIF CY2026 = CPI-U - TFP (live)', 'label'),
           (f'=B{r_cpiu}-B{r_tfp}', 'fml', lib.FMT_PCT1), ('%/yr', 'text'),
           None, None, None, None, None, None, ('DERIVED', 'text'),
           ('CMS Transmittal 13464 / CR 14269', 'note'),
           ('Recomputes the published +2.0% update', 'note')])
    r_aif26 = b.r
    b.row([('AIF CY2025 (prior year)', 'label'),
           (0.024, 'src', lib.FMT_PCT1), ('%/yr', 'text'), None, None,
           None, None, None, None, ('GOV', 'text'),
           ('MedPAC June 2026 Ch.6', 'note'), None])
    b.row([('GADCS mean cost per transport', 'label'),
           (2673, 'src', lib.FMT_USD), ('$', 'text'), None, None, None,
           None, None, None, ('GOV', 'text'),
           ('CMS/RAND GADCS report, Year 1 + Year 2 cohorts (Dec 2024)',
            'note'),
           ('Mandatory federal cost survey; median $1,340; labor = 69.4% '
            'of costs; volume the strongest unit-cost driver.', 'note')],
          wrap=True)
    r_gadcs_cost = b.r
    b.row([('GADCS median cost per transport', 'label'),
           (1340, 'src', lib.FMT_USD), ('$', 'text'), None, None, None,
           None, None, None, ('GOV', 'text'),
           ('CMS/RAND GADCS report (Dec 2024)', 'note'), None])
    b.row([('GADCS labor share of costs', 'label'),
           (0.694, 'src', lib.FMT_PCT1), ('%', 'text'), None, None, None,
           None, None, None, ('GOV', 'text'),
           ('CMS/RAND GADCS report (Dec 2024)', 'note'), None])
    b.row([('GAO 2010 cost per transport — median', 'label'),
           (429, 'src', lib.FMT_USD), ('$', 'text'), None, None, None,
           None, None, None, ('GOV', 'text'),
           ('GAO-13-6 (Oct 2012)', 'note'),
           ('Range $224-$2,204 across providers; median Medicare margin '
            'about +2% WITH the add-ons, -1% without.', 'note')], wrap=True)

    b.blank()
    b.banner('D. Market size + mix readings — Medicare, GADCS, NEMSIS')
    b.headers(['Item', 'Value', 'Unit', '', '', '', '', '', '', 'Basis',
               'Source', 'Detail / caveat'])
    b.row([('Medicare FFS ground organizations (2024)', 'label'),
           (10600, 'src', lib.FMT_INT), ('orgs (~)', 'text'), None, None,
           None, None, None, None, ('GOV', 'text'),
           ('MedPAC June 2026 Ch.6', 'note'), None])
    b.row([('Medicare FFS ground transports (2024)', 'label'),
           (11300000, 'src', lib.FMT_INT), ('transports', 'text'), None,
           None, None, None, None, None, ('GOV', 'text'),
           ('MedPAC June 2026 Ch.6', 'note'), None])
    r_trans = b.r
    b.row([('Medicare AFS payments (2024)', 'label'),
           (5300000000, 'src', lib.FMT_USD), ('$', 'text'), None, None,
           None, None, None, None, ('GOV', 'text'),
           ('MedPAC June 2026 Ch.6', 'note'), None])
    r_spend = b.r
    b.row([('Avg AFS payment per transport (live)', 'label'),
           (f'=B{r_spend}/B{r_trans}', 'fml', lib.FMT_USD), ('$', 'text'),
           None, None, None, None, None, None, ('DERIVED', 'text'),
           ('MedPAC June 2026 Ch.6 (both inputs)', 'note'),
           ('$5.3B / 11.3M transports = ~$469', 'note')])
    r_avgpay = b.r
    b.row([('GADCS all-payer mix — BLS share', 'label'),
           (0.56, 'src', lib.FMT_PCT1), ('% of transports', 'text'), None,
           None, None, None, None, None, ('GOV', 'text'),
           ('CMS/RAND GADCS report (Dec 2024), 3,694 reporting orgs',
            'note'),
           ('"Over half—56 percent—of transports were at the basic life '
            'support (BLS) level... ALS1 services accounted for an '
            'additional 42 percent... ALS2 and SCT combined accounted for '
            '3 percent."', 'note')], wrap=True)
    r_gadcs_bls = b.r
    b.row([('GADCS all-payer mix — ALS1 share', 'label'),
           (0.42, 'src', lib.FMT_PCT1), ('% of transports', 'text'), None,
           None, None, None, None, None, ('GOV', 'text'),
           ('CMS/RAND GADCS report (Dec 2024)', 'note'), None])
    b.row([('GADCS all-payer mix — ALS2 + SCT share', 'label'),
           (0.03, 'src', lib.FMT_PCT1), ('% of transports', 'text'), None,
           None, None, None, None, None, ('GOV', 'text'),
           ('CMS/RAND GADCS report (Dec 2024)', 'note'), None])
    b.row([('GADCS — emergency share of responses', 'label'),
           (0.72, 'src', lib.FMT_PCT1), ('%', 'text'), None, None, None,
           None, None, None, ('GOV', 'text'),
           ('CMS/RAND GADCS report (Dec 2024)', 'note'), None])
    b.row([('NEMSIS EMS activations (2024)', 'label'),
           (60298684, 'src', lib.FMT_INT), ('activations', 'text'), None,
           None, None, None, None, None, ('SOURCED', 'text'),
           ('NEMSIS National EMS Data Report 2024', 'note'),
           ('National EMS registry; submission-based, no sampling frame — '
            'coverage caveat carried from v2.7.', 'note')], wrap=True)
    r_nemsis_all = b.r
    b.row([('NEMSIS hospital-to-hospital activations (2024)', 'label'),
           (5510664, 'src', lib.FMT_INT), ('activations', 'text'), None,
           None, None, None, None, None, ('SOURCED', 'text'),
           ('NEMSIS National EMS Data Report 2024', 'note'), None])
    r_nemsis_hh = b.r
    b.row([('... as share of all activations (live)', 'label'),
           (f'=B{r_nemsis_hh}/B{r_nemsis_all}', 'fml', lib.FMT_PCT1),
           ('%', 'text'), None, None, None, None, None, None,
           ('DERIVED', 'text'), ('NEMSIS 2024 (both inputs)', 'note'),
           ('~9.1%', 'note')])
    b.row([('NEMSIS ALL facility-to-facility activations (2024)', 'label'),
           (7512656, 'src', lib.FMT_INT), ('activations', 'text'), None,
           None, None, None, None, None, ('SOURCED', 'text'),
           ('NEMSIS National EMS Data Report 2024', 'note'),
           ('The interfacility book inside US EMS.', 'note')])
    r_nemsis_ff = b.r
    b.row([('... as share of all activations (live)', 'label'),
           (f'=B{r_nemsis_ff}/B{r_nemsis_all}', 'fml', lib.FMT_PCT1),
           ('%', 'text'), None, None, None, None, None, None,
           ('DERIVED', 'text'), ('NEMSIS 2024 (both inputs)', 'note'),
           ('~12.5%', 'note')])
    r_ff_share = b.r
    b.row([('US inpatient discharges per year', 'label'),
           (33000000, 'src', lib.FMT_INT), ('discharges (33M+)', 'text'),
           None, None, None, None, None, None, ('ACADEMIC', 'text'),
           ('HCUP Statistical Brief #205 (2013 data)', 'note'),
           ('STALE-VINTAGE FLAG: 2013 anchor, carried as demand context '
            'only.', 'note')], wrap=True)
    b.row([('Share of discharges to post-acute care', 'label'),
           (0.223, 'src', lib.FMT_PCT1), ('%', 'text'), None, None, None,
           None, None, None, ('ACADEMIC', 'text'),
           ('HCUP Statistical Brief #205 (2013 data)', 'note'),
           ('The BLS discharge book.', 'note')])
    b.row([('Acute-to-acute transfers per year', 'label'),
           (1400000, 'src', lib.FMT_INT), ('transfers (~4% of stays)',
                                           'text'), None, None, None, None,
           None, None, ('ACADEMIC', 'text'),
           ('Hernandez-Boussard et al., J Patient Saf 2017 (2009 NIS)',
            'note'),
           ('STALE-VINTAGE FLAG: 2009 NIS. The ALS/SCT book.', 'note')],
          wrap=True)
    b.row([('US dialysis patients (recurring BLS book)', 'label'),
           (550000, 'src', lib.FMT_INT), ('patients (~)', 'text'), None,
           None, None, None, None, None, ('ACADEMIC', 'text'),
           ('NIDDK/USRDS kidney disease statistics', 'note'), None])

    b.blank()
    b.note('Reconciliation caveat: the six-code CY2024 total (block A, '
           '9,637,068 services) is the SUPPLIER (carrier) claims file only; '
           "MedPAC's 11.3M transports count all ground transports including "
           'institutionally billed claims. The two figures measure '
           'different universes and are both carried deliberately.')
    b.note('Extraction: all rows from rcm_mc/market_reports/'
           'ift_service_levels.py accessors fee_rows(), medicare_mix(), '
           'payment_mechanics(), mix_readings() — run at build time '
           f'{accessed}; module reports 53 unique sources, all URL-linked, '
           'verified July 2026; has_no_illustrative() == True. Tier B: '
           'values carried from the repo module; underlying documents not '
           'reopened for this build.')
    b.note('CY2026 base $ column is a live formula linked to the '
           'Derived_Rate_Card CF cell — one source of truth for the '
           'conversion factor across the workbook.')

    lib.add_chart(
        ws, 'N6', 'CY2024 Medicare ground services by HCPCS '
        '(supplier claims)',
        f'Service_Level_Economics!$A${a0}:$A${a1}',
        [('CY2024 services', f'Service_Level_Economics!$E${a0}:$E${a1}')],
        kind='bar', width=24, height=10, y_fmt='#,##0',
        y_title='services')
    lib.add_chart(
        ws, 'N28', 'Medicare service mix by level group — 2011 vs 2024',
        f'Service_Level_Economics!$A${dr0}:$A${dr1}',
        [('2024 share', f'Service_Level_Economics!$C${dr0}:$C${dr1}'),
         ('2011 share', f'Service_Level_Economics!$D${dr0}:$D${dr1}')],
        kind='bar', width=24, height=10, y_fmt='0%',
        y_title='share of transports')

    facts += [
        {'metric': 'CY2024 Medicare six-code ground services (supplier '
                   'claims)', 'year': 'CY2024',
         'value_ref': f'Service_Level_Economics!E{r_tot}',
         'unit': 'services', 'basis': 'DERIVED', 'tier': 'B',
         'source_keys': ['cms_medpop_cy2024'],
         'locator': 'live SUM over the six A04xx code rows',
         'lives_on': 'Service_Level_Economics',
         'cross_check': '9,637,068 (python recompute)'},
        {'metric': 'ALS1-emergency (A0427) share of six-code services',
         'year': 'CY2024',
         'value_ref': f"Service_Level_Economics!D{mix_ix['A0427']}",
         'unit': '%', 'basis': 'DERIVED', 'tier': 'B',
         'source_keys': ['cms_medpop_cy2024'],
         'locator': 'live formula services/total; 38.4%',
         'lives_on': 'Service_Level_Economics',
         'cross_check': 'module medicare_mix() share_pct 38.4'},
        {'metric': 'Medicare FFS ground transports', 'year': '2024',
         'value_ref': f'Service_Level_Economics!B{r_trans}',
         'unit': 'transports', 'basis': 'GOV', 'tier': 'B',
         'source_keys': ['medpac_jun2026_ch6'],
         'locator': 'MedPAC Jun 2026 Ch.6: 11.3M transports, ~10,600 orgs',
         'lives_on': 'Service_Level_Economics',
         'cross_check': 'supplier-file six-code total 9.64M (different '
                        'universe — see reconciliation note)'},
        {'metric': 'Medicare AFS payments', 'year': '2024',
         'value_ref': f'Service_Level_Economics!B{r_spend}', 'unit': '$',
         'basis': 'GOV', 'tier': 'B',
         'source_keys': ['medpac_jun2026_ch6'],
         'locator': 'MedPAC Jun 2026 Ch.6: $5.3B', 'lives_on':
             'Service_Level_Economics', 'cross_check': ''},
        {'metric': 'Average AFS payment per transport', 'year': '2024',
         'value_ref': f'Service_Level_Economics!B{r_avgpay}', 'unit': '$',
         'basis': 'DERIVED', 'tier': 'B',
         'source_keys': ['medpac_jun2026_ch6'],
         'locator': 'live formula $5.3B / 11.3M = ~$469',
         'lives_on': 'Service_Level_Economics',
         'cross_check': 'ift_unit_economics medicare_avg_payment $469 '
                        '(needs_reverify=False)'},
        {'metric': 'GADCS all-payer BLS share of ground transports',
         'year': '2022-23 cohorts',
         'value_ref': f'Service_Level_Economics!B{r_gadcs_bls}',
         'unit': '%', 'basis': 'GOV', 'tier': 'B',
         'source_keys': ['gadcs_dec2024'],
         'locator': 'GADCS Dec 2024 report, 3,694 reporting orgs; verbatim '
                    'quote carried on-row',
         'lives_on': 'Service_Level_Economics',
         'cross_check': 'ALS1 42%, ALS2+SCT 3% on adjacent rows'},
        {'metric': 'NEMSIS facility-to-facility share of EMS activations',
         'year': '2024',
         'value_ref': f'Service_Level_Economics!B{r_ff_share}',
         'unit': '%', 'basis': 'DERIVED', 'tier': 'B',
         'source_keys': ['nemsis_2024'],
         'locator': 'live formula 7,512,656 / 60,298,684 = ~12.5%',
         'lives_on': 'Service_Level_Economics',
         'cross_check': 'hospital-to-hospital subset 5,510,664 (9.1%)'},
        {'metric': 'GADCS mean cost per transport', 'year': '2022-23 '
         'cohorts', 'value_ref':
             f'Service_Level_Economics!B{r_gadcs_cost}',
         'unit': '$', 'basis': 'GOV', 'tier': 'B',
         'source_keys': ['gadcs_dec2024'],
         'locator': 'GADCS Dec 2024: mean $2,673, median $1,340, labor '
                    '69.4%', 'lives_on': 'Service_Level_Economics',
         'cross_check': 'GAO-13-6 2010 median $429 (range $224-$2,204) on '
                        'adjacent row'},
        {'metric': 'Ambulance Inflation Factor, CY2026', 'year': 'CY2026',
         'value_ref': f'Service_Level_Economics!B{r_aif26}', 'unit': '%/yr',
         'basis': 'DERIVED', 'tier': 'B',
         'source_keys': ['cms_transmittal_13464'],
         'locator': 'live formula CPI-U 2.7% - TFP 0.7% = 2.0%; transmittal '
                    'quote on-row', 'lives_on': 'Service_Level_Economics',
         'cross_check': 'matches Derived_Rate_Card CF update formula'},
    ]


# ══════════════════════════════════════════════════════════════════════════
# Tab 4 — Commercial_Context_APCD
# ══════════════════════════════════════════════════════════════════════════

CT_ORDER = ['Inpatient', 'Outpatient', 'Inpatient/Outpatient Combined']
YEARS = ['2021', '2022', '2023', '2024']


def _build_apcd(wb, lib, n_raw, statewide, dist, accessed, facts):
    ws = wb.create_sheet('Commercial_Context_APCD')
    b = lib.SheetBuilder(
        ws, 12, col_widths=[32, 7, 13, 12, 10, 10, 10, 10, 10, 11, 16, 52],
        tab_color=NAVY)
    b.title('Commercial-vs-Medicare pricing context — Colorado APCD '
            '(CIVHC public-use, facility claims)')
    b.subtitle(
        'The question: where an all-payer claims database publishes it, how '
        'much more than Medicare do commercial payers actually pay? CIVHC '
        '(the Colorado APCD administrator) publishes provider-level '
        'commercial payments as a percent of what Medicare would have paid, '
        '2021-2024. CONTEXT ONLY: these are HOSPITAL / FACILITY claims in '
        'ONE STATE — not ambulance codes, not a national rate, and never an '
        'ambulance commercial multiple.')
    b.blank()
    b.banner('READ THIS FIRST — SCOPE: Colorado hospital/facility claims '
             'only. CONTEXT for commercial multiples. NOT AN AMBULANCE '
             'RATE.')
    b.blank()
    b.banner('A. Published STATEWIDE ratios — commercial paid as a multiple '
             'of Medicare (CIVHC, staging table)')
    b.headers(['Claim type (facility claims)', 'Year',
               'Commercial paid as multiple of Medicare (STATEWIDE, '
               'published)', 'Claims (n)', '', '', '', '', '', '', 'Basis',
               'Source'])
    sw_ix = {}
    groups = {}
    for ct in CT_ORDER:
        g0 = b.r + 1
        for yr in YEARS:
            ratio, claims = statewide[(ct, yr)]
            r = b.r + 1
            sw_ix[(ct, yr)] = r
            b.row([
                (ct, 'src'), (int(yr), 'src'),
                (ratio, 'src', lib.FMT_X),
                (claims, 'src', lib.FMT_INT),
                None, None, None, None, None, None,
                ('SOURCED', 'text'),
                ('CIVHC CO APCD, Medicare Reference-Based Pricing '
                 'public-use file (FY26 release), STATEWIDE row', 'note'),
            ])
        groups[ct] = (g0, b.r)
    sw0 = sw_ix[(CT_ORDER[0], YEARS[0])]
    sw1 = sw_ix[(CT_ORDER[-1], YEARS[-1])]

    b.blank()
    b.banner('B. Summary screens — live formulas over the staging table '
             '(quartiles, trend)')
    b.headers(['Screen', '', 'Value (live formula)', '', '', '', '', '', '',
               '', 'Basis', 'Note'])
    swrng = f'$C${sw0}:$C${sw1}'
    b.row([('Median of the 12 statewide readings (2021-2024)', 'label'),
           None, (f'=MEDIAN({swrng})', 'fml', lib.FMT_X), None, None, None,
           None, None, None, None, ('DERIVED', 'text'),
           ('QUARTILE/MEDIAN formulas run over staging block A', 'note')])
    r_med = b.r
    b.row([('Lower quartile (Q1) of statewide readings', 'label'), None,
           (f'=QUARTILE({swrng},1)', 'fml', lib.FMT_X), None, None, None,
           None, None, None, None, ('DERIVED', 'text'), None])
    b.row([('Upper quartile (Q3) of statewide readings', 'label'), None,
           (f'=QUARTILE({swrng},3)', 'fml', lib.FMT_X), None, None, None,
           None, None, None, None, ('DERIVED', 'text'), None])
    b.row([('Minimum statewide reading (Inpatient 2021)', 'label'), None,
           (f'=MIN({swrng})', 'fml', lib.FMT_X), None, None, None, None,
           None, None, None, ('DERIVED', 'text'), None])
    b.row([('Maximum statewide reading (Outpatient 2024)', 'label'), None,
           (f'=MAX({swrng})', 'fml', lib.FMT_X), None, None, None, None,
           None, None, None, ('DERIVED', 'text'), None])
    cagr_rows = {}
    for ct in CT_ORDER:
        c_end = f"$C${sw_ix[(ct, '2024')]}"
        c_start = f"$C${sw_ix[(ct, '2021')]}"
        r = b.r + 1
        cagr_rows[ct] = r
        b.row([(f'{ct} — ratio drift 2021 -> 2024 (3-yr CAGR window)',
                'label'), None,
               (lib.cagr_formula(c_end, c_start, 3), 'fml', lib.FMT_PCT1),
               None, None, None, None, None, None, None,
               ('DERIVED', 'text'),
               ('Trend-eligible: same file, same method, 4 consecutive '
                'years, no break', 'note')])

    b.blank()
    b.banner('C. Provider-level distribution — quartiles by claim type x '
             'year (215 CO facilities; STATEWIDE rows excluded)')
    b.headers(['Claim type', 'Year', 'n provider rows', 'Claims (sum)',
               'Min', 'p25', 'Median', 'p75', 'Max',
               'IQR (p75-p25, live)', 'Basis', 'Source / extraction'])
    pv_ix = {}
    for ct in CT_ORDER:
        for yr in YEARS:
            d = dist[(ct, yr)]
            r = b.r + 1
            pv_ix[(ct, yr)] = r
            b.row([
                (ct, 'src'), (int(yr), 'src'),
                (d['n'], 'src', lib.FMT_INT),
                (d['claims'], 'src', lib.FMT_INT),
                (round(d['min'], 4), 'src', lib.FMT_X),
                (round(d['p25'], 4), 'src', lib.FMT_X),
                (round(d['median'], 4), 'src', lib.FMT_X),
                (round(d['p75'], 4), 'src', lib.FMT_X),
                (round(d['max'], 4), 'src', lib.FMT_X),
                (f'=H{r}-F{r}', 'fml', lib.FMT_X),
                ('SOURCED (extracted)', 'text'),
                ('Percentiles computed by the build script over the '
                 'provider rows of the vendored file (inclusive-'
                 'quartile method = Excel QUARTILE)', 'note'),
            ])

    b.blank()
    b.note('LOUD CAVEAT (repeated on purpose): this table is hospital / '
           'facility claims in Colorado only. It is CONTEXT for what '
           '"commercial pays a multiple of Medicare" looks like when '
           'actually measured in an APCD — it is NOT an ambulance rate, '
           'NOT a national figure, and must never be applied to the '
           'ambulance fee schedule. Ambulance-specific commercial bounds '
           'live on the v2.7 Payer_Rates_Commercial tab (HCCI / FAIR '
           'Health published ratios).')
    b.note('Source: CIVHC (Colorado APCD administrator), "FY26 Medicare '
           'Reference Based Pricing Public Excel File" (2021-2024). '
           'License note carried from the vendored provenance registry: '
           '"CIVHC public-use file (redistributable)". Vendored at '
           'rcm_mc/data/vendor/payer_data/reference_based_pricing.csv '
           f'({n_raw} rows incl. 12 STATEWIDE rows); registry row '
           '"civhc_rbp_fy26" in source_registry.csv (ingested 2026-05-24). '
           f'Accessed for this build {accessed}.')
    b.note('Method notes: "percent of Medicare" = commercial payments as a '
           'multiple of what Medicare would have paid for the same '
           'services (CIVHC reference-based pricing method). Provider rows '
           'are resolvable to CCN by name; ~1% missingness on the URF/'
           'payer fields of the source file (hospital_pct_medicare column '
           'is complete). The amb_flag field in the source file marks '
           'AMBULATORY surgical centers — not ambulances.')
    b.note('Coverage caveat: per Gobeille v. Liberty Mutual (2016), '
           'self-funded ERISA plans are not required to report to state '
           'APCDs — commercial coverage is partial (public APCDs typically '
           'note a ~30-40% commercial gap). Extraction/recompute path: '
           'rcm_mc/data/state_apcd.py (parse_apcd_csv, '
           'compute_commercial_medicare_ratio) + this build script.')

    ip0, ip1 = groups['Inpatient']
    yr_ref = (f'Commercial_Context_APCD!$B${ip0}:$B${ip1}')
    series = []
    for ct in CT_ORDER:
        g0, g1 = groups[ct]
        series.append((ct, f'Commercial_Context_APCD!$C${g0}:$C${g1}'))
    lib.add_chart(
        ws, 'N7', 'Colorado statewide commercial paid as multiple of '
        'Medicare, 2021-2024 (facility claims — CONTEXT ONLY)',
        yr_ref, series, kind='line', width=24, height=10, y_fmt='0.0"x"',
        y_title='multiple of Medicare')
    med_series = []
    for ct in CT_ORDER:
        r0 = pv_ix[(ct, '2021')]
        r1 = pv_ix[(ct, '2024')]
        med_series.append((f'{ct} (provider median)',
                           f'Commercial_Context_APCD!$G${r0}:$G${r1}'))
    lib.add_chart(
        ws, 'N28', 'Provider-level MEDIAN commercial multiple of Medicare '
        'by year (CO facilities)',
        f'Commercial_Context_APCD!$B${pv_ix[(CT_ORDER[0], "2021")]}:'
        f'$B${pv_ix[(CT_ORDER[0], "2024")]}',
        med_series, kind='bar', width=24, height=10, y_fmt='0.0"x"',
        y_title='multiple of Medicare')

    loud = ('facility/hospital claims, Colorado only — CONTEXT for '
            'commercial multiples, NOT an ambulance rate')
    facts += [
        {'metric': 'CO statewide commercial paid as multiple of Medicare — '
                   'Inpatient/Outpatient combined', 'year': '2024',
         'value_ref': 'Commercial_Context_APCD!'
                      f"C{sw_ix[('Inpatient/Outpatient Combined', '2024')]}",
         'unit': 'x Medicare', 'basis': 'SOURCED', 'tier': 'A',
         'source_keys': ['civhc_rbp_fy26'],
         'locator': 'FY26 RBP public file, STATEWIDE row, IP/OP combined, '
                    f'2024 (2.39x); {loud}',
         'lives_on': 'Commercial_Context_APCD',
         'cross_check': 'claims-weighted provider mean 2.42x (python)'},
        {'metric': 'CO statewide commercial multiple — Outpatient',
         'year': '2024',
         'value_ref': 'Commercial_Context_APCD!'
                      f"C{sw_ix[('Outpatient', '2024')]}",
         'unit': 'x Medicare', 'basis': 'SOURCED', 'tier': 'A',
         'source_keys': ['civhc_rbp_fy26'],
         'locator': f'FY26 RBP public file, STATEWIDE row (2.58x); {loud}',
         'lives_on': 'Commercial_Context_APCD', 'cross_check': ''},
        {'metric': 'CO statewide commercial multiple — Inpatient',
         'year': '2024',
         'value_ref': 'Commercial_Context_APCD!'
                      f"C{sw_ix[('Inpatient', '2024')]}",
         'unit': 'x Medicare', 'basis': 'SOURCED', 'tier': 'A',
         'source_keys': ['civhc_rbp_fy26'],
         'locator': f'FY26 RBP public file, STATEWIDE row (1.91x); {loud}',
         'lives_on': 'Commercial_Context_APCD', 'cross_check': ''},
        {'metric': 'Median of the 12 CO statewide commercial-multiple '
                   'readings', 'year': '2021-2024',
         'value_ref': f'Commercial_Context_APCD!C{r_med}',
         'unit': 'x Medicare', 'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['civhc_rbp_fy26'],
         'locator': f'live MEDIAN formula over staging block A; {loud}',
         'lives_on': 'Commercial_Context_APCD', 'cross_check': ''},
        {'metric': 'CO provider-level median commercial multiple — IP/OP '
                   'combined', 'year': '2024',
         'value_ref': 'Commercial_Context_APCD!'
                      f"G{pv_ix[('Inpatient/Outpatient Combined', '2024')]}",
         'unit': 'x Medicare', 'basis': 'SOURCED', 'tier': 'A',
         'source_keys': ['civhc_rbp_fy26'],
         'locator': 'inclusive-quartile median over 86 provider rows of '
                    f'the vendored file (2.38x); {loud}',
         'lives_on': 'Commercial_Context_APCD',
         'cross_check': 'statewide published 2.39x — consistent'},
        {'metric': 'CO provider-level IQR of commercial multiple — IP/OP '
                   'combined', 'year': '2024',
         'value_ref': 'Commercial_Context_APCD!'
                      f"J{pv_ix[('Inpatient/Outpatient Combined', '2024')]}",
         'unit': 'x Medicare (width)', 'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['civhc_rbp_fy26'],
         'locator': f'live formula p75-p25 (1.79x to 2.77x); {loud}',
         'lives_on': 'Commercial_Context_APCD', 'cross_check': ''},
        {'metric': 'CO statewide commercial-multiple drift — IP/OP '
                   'combined, 3-yr CAGR', 'year': '2021-2024',
         'value_ref': 'Commercial_Context_APCD!'
                      f"C{cagr_rows['Inpatient/Outpatient Combined']}",
         'unit': '%/yr', 'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['civhc_rbp_fy26'],
         'locator': 'live CAGR formula 2021->2024 window over staging '
                    f'block A; {loud}',
         'lives_on': 'Commercial_Context_APCD',
         'cross_check': '2.29x -> 2.39x'},
    ]


# ══════════════════════════════════════════════════════════════════════════

def build(wb, ctx):
    lib = ctx['lib']
    accessed = ctx['accessed']
    repo = ctx['repo']
    facts, notes = [], []

    locs = _load_gpci()
    sl = _load_service_levels()
    a0432 = _load_a0432_rvu()
    n_raw, statewide, dist = _load_apcd(repo)

    gpci_mean_row = _build_gpci(wb, lib, locs, accessed, facts)
    cf_row = _build_rate_card(wb, lib, sl, a0432, gpci_mean_row, accessed,
                              facts)
    _build_sle(wb, lib, sl, cf_row, accessed, facts)
    _build_apcd(wb, lib, n_raw, statewide, dist, accessed, facts)

    sources = [
        {'key': 'cms_gpci_2025', 'publisher': 'CMS',
         'document': 'CY2025 PFS Geographic Practice Cost Indices — '
                     'Addendum E (RVU25A relative-value package)',
         'vintage': 'CY2025 (final)',
         'locator': 'Addendum E table: MAC / state / locality / PW-PE-MP '
                    'GPCIs; vendored rcm_mc/data/vendor/cms_gpci/'
                    'GPCI2025.csv; source_registry.csv row cms_gpci_2025 '
                    '(ingested 2026-06-12); license: CMS public-use file '
                    '(redistributable)',
         'supplies': '109 locality GPCI rows; PE GPCI input to the '
                     'ambulance geographic factor',
         'url': 'https://www.cms.gov/medicare/payment/fee-schedules/'
                'physician/pfs-relative-value-files/rvu25a',
         'tier': 'A', 'accessed': accessed,
         'powers': ['GPCI_Localities', 'Derived_Rate_Card']},
        {'key': 'cfr_414_610', 'publisher': 'eCFR (GPO/OFR)',
         'document': '42 CFR 414.610 — Basis of payment (Ambulance Fee '
                     'Schedule)',
         'vintage': 'current (2026)',
         'locator': '414.610(c)(4): PE GPCI applies to 70% of the base '
                    'rate for ground services',
         'supplies': 'the 0.7 x PE GPCI + 0.3 geographic rule; payment '
                     'formula',
         'url': 'https://www.ecfr.gov/current/title-42/section-414.610',
         'tier': 'B', 'accessed': accessed,
         'powers': ['GPCI_Localities', 'Derived_Rate_Card',
                    'Service_Level_Economics']},
        {'key': 'cms_afs_puf_cy2026', 'publisher': 'CMS',
         'document': 'Ambulance Fee Schedule public use files (CY2026)',
         'vintage': 'CY2026',
         'locator': 'AFS PUF: conversion factor $284.56, RVU ladder, '
                    'mileage rates',
         'supplies': 'CY2026 CF, RVUs, mileage (carried via repo module '
                     'ift_service_levels, verified July 2026)',
         'url': 'https://www.cms.gov/medicare/payment/fee-schedules/'
                'ambulance/ambulance-fee-schedule-public-use-files',
         'tier': 'B', 'accessed': accessed,
         'powers': ['Derived_Rate_Card', 'Service_Level_Economics']},
        {'key': 'medpac_jun2026_ch6', 'publisher': 'MedPAC',
         'document': 'June 2026 Report to Congress, Ch. 6 (ground '
                     'ambulance)', 'vintage': 'June 2026',
         'locator': 'Ch.6: CY2026 CF $284.56 / CY2025 $278.98; mileage '
                    '$9.15/$9.33/$9.42; 11.3M transports / $5.3B / '
                    '~10,600 orgs (2024); add-on empirical-basis quote',
         'supplies': 'CF + mileage series; Medicare market size 2024',
         'url': 'https://www.medpac.gov/wp-content/uploads/2026/06/'
                'Jun26_Ch6_MedPAC_Report_To_Congress_SEC.pdf',
         'tier': 'B', 'accessed': accessed,
         'powers': ['Derived_Rate_Card', 'Service_Level_Economics']},
        {'key': 'medpac_mar2025_slides', 'publisher': 'MedPAC',
         'document': 'March 2025 mandated-report slides (ground ambulance)',
         'vintage': 'March 2025',
         'locator': 'CY2025 CF / mileage corroboration',
         'supplies': 'CY2025 prior-year payment parameters',
         'url': 'https://www.medpac.gov/wp-content/uploads/2025/03/'
                'Ambulance-MedPAC-03.25_SEC.pdf',
         'tier': 'B', 'accessed': accessed,
         'powers': ['Derived_Rate_Card']},
        {'key': 'cms_medpop_cy2024', 'publisher': 'CMS',
         'document': 'Medicare Physician & Other Practitioners — by '
                     'Geography and Service (CY2024)',
         'vintage': 'CY2024 (published May 2026)',
         'locator': 'national rows, HCPCS A0426-A0434: services, avg '
                    'allowed, avg paid, provider counts',
         'supplies': 'CY2024 utilization ladder + service mix',
         'url': 'https://data.cms.gov/provider-summary-by-type-of-service/'
                'medicare-physician-other-practitioners/medicare-physician'
                '-other-practitioners-by-geography-and-service',
         'tier': 'B', 'accessed': accessed,
         'powers': ['Service_Level_Economics']},
        {'key': 'cms_transmittal_13464', 'publisher': 'CMS',
         'document': 'Transmittal 13464 / CR 14269 — CY2026 Ambulance '
                     'Inflation Factor', 'vintage': 'Nov 2025',
         'locator': 'AIF CY2026 = CPI-U 2.7% - TFP 0.7% = 2.0% (verbatim '
                    'quote carried on-row)',
         'supplies': 'CY2026 AIF and its decomposition',
         'url': 'https://www.cms.gov/files/document/r13464cp.pdf',
         'tier': 'B', 'accessed': accessed,
         'powers': ['Derived_Rate_Card', 'Service_Level_Economics']},
        {'key': 'usc_1395m_l', 'publisher': 'U.S. Code (OLRC)',
         'document': '42 U.S.C. 1395m(l)(12)-(13) — ground ambulance '
                     'temporary add-ons', 'vintage': 'current (2026)',
         'locator': '(l)(12)(A) +2% urban / +3% rural; (l)(13) super-rural '
                    '22.6% base increase',
         'supplies': 'statutory authority for the add-on percentages',
         'url': 'https://uscode.house.gov/view.xhtml?req=granuleid:'
                'USC-prelim-title42-section1395m',
         'tier': 'B', 'accessed': accessed,
         'powers': ['Derived_Rate_Card']},
        {'key': 'caa_2026_6203', 'publisher': 'U.S. Senate Committee on '
                                              'Finance',
         'document': 'Consolidated Appropriations Act, 2026 — §6203 '
                     'section-by-section (ambulance add-on extension)',
         'vintage': '2026',
         'locator': '§6203: add-ons extended through Dec 31, 2027; CBO '
                    '~$197M',
         'supplies': 'extension date + score for the add-on cliff row',
         'url': 'https://www.finance.senate.gov/imo/media/doc/'
                'consolidated_appropriations_act_2026_section-by-'
                'section.pdf',
         'tier': 'B', 'accessed': accessed,
         'powers': ['Derived_Rate_Card']},
        {'key': 'gadcs_dec2024', 'publisher': 'CMS / RAND',
         'document': 'Medicare Ground Ambulance Data Collection System '
                     '(GADCS) report — Year 1 + Year 2 cohort analysis',
         'vintage': 'Dec 2024 (2022-23 cohorts)',
         'locator': 'mean cost/transport $2,673 (median $1,340); labor '
                    '69.4%; all-payer mix 56/42/3; 72% emergencies; 3,694 '
                    'orgs (verbatim quote carried on-row)',
         'supplies': 'cost anchors + all-payer service mix',
         'url': 'https://www.cms.gov/files/document/medicare-ground-'
                'ambulance-data-collection-system-gadcs-report-year-1-and-'
                'year-2-cohort-analysis.pdf',
         'tier': 'B', 'accessed': accessed,
         'powers': ['Service_Level_Economics']},
        {'key': 'gao_13_6', 'publisher': 'GAO',
         'document': 'GAO-13-6 — Ambulance Providers: Costs and Medicare '
                     'Margins Varied Widely', 'vintage': 'Oct 2012 (2010 '
                     'data)',
         'locator': '2010 cost/transport median $429 (range $224-$2,204); '
                    'median Medicare margin +2% with add-ons / -1% without',
         'supplies': 'historical cost + margin anchors',
         'url': 'https://www.gao.gov/products/gao-13-6',
         'tier': 'B', 'accessed': accessed,
         'powers': ['Service_Level_Economics']},
        {'key': 'medpac_jun2013_ch7', 'publisher': 'MedPAC',
         'document': 'June 2013 mandated report, Ch. 7 (ambulance)',
         'vintage': 'June 2013 (2011 claims)',
         'locator': '2011 mix: BLS 60.9% (42.0% NE), ALS 38.4%, ALS2 0.9%, '
                    'SCT 0.8%; SCT +35.5%/FFS bene 2007-2011',
         'supplies': 'the 2011 trend base for the 13-year mix drift',
         'url': 'https://www.medpac.gov/wp-content/uploads/import_data/'
                'scrape_files/docs/default-source/reports/chapter-7-'
                'mandated-report-medicare-payment-for-ambulance-services-'
                'june-2013-report-.pdf',
         'tier': 'B', 'accessed': accessed,
         'powers': ['Service_Level_Economics']},
        {'key': 'nemsis_2024', 'publisher': 'NEMSIS TAC (NHTSA)',
         'document': 'NEMSIS National EMS Data Report 2024 (End-of-Year)',
         'vintage': '2024',
         'locator': '60,298,684 activations; hospital-to-hospital '
                    '5,510,664; all facility-to-facility 7,512,656',
         'supplies': 'the interfacility share of US EMS activations',
         'url': 'https://nemsis.org/wp-content/uploads/2025/08/'
                'NEMSIS-End-of-Year-Report-2024.pdf',
         'tier': 'B', 'accessed': accessed,
         'powers': ['Service_Level_Economics']},
        {'key': 'hcup_sb205', 'publisher': 'AHRQ HCUP',
         'document': 'Statistical Brief #205 — discharge disposition',
         'vintage': '2013 data (STALE-VINTAGE FLAG carried)',
         'locator': '33M+ discharges/yr; 22.3% to post-acute care',
         'supplies': 'demand-context anchors (BLS discharge book)',
         'url': 'https://www.ncbi.nlm.nih.gov/books/NBK373736/figure/'
                'sb205.f1/',
         'tier': 'B', 'accessed': accessed,
         'powers': ['Service_Level_Economics']},
        {'key': 'hernandez_boussard_2017', 'publisher': 'J Patient Saf '
                                                        '(Wolters Kluwer)',
         'document': 'Hernandez-Boussard et al. — interhospital transfers '
                     '(2009 NIS)', 'vintage': '2017 (2009 data; '
                     'STALE-VINTAGE FLAG carried)',
         'locator': '~1.4M/yr (~4% of stays) acute-to-acute transfers',
         'supplies': 'the ALS/SCT transfer book anchor',
         'url': 'https://pubmed.ncbi.nlm.nih.gov/25397857/',
         'tier': 'B', 'accessed': accessed,
         'powers': ['Service_Level_Economics']},
        {'key': 'usrds_niddk', 'publisher': 'NIDDK / USRDS',
         'document': 'US kidney disease statistics', 'vintage': 'current',
         'locator': '~550k US dialysis patients',
         'supplies': 'the recurring-BLS dialysis book anchor',
         'url': 'https://www.niddk.nih.gov/health-information/'
                'health-statistics/kidney-disease',
         'tier': 'B', 'accessed': accessed,
         'powers': ['Service_Level_Economics']},
        {'key': 'civhc_rbp_fy26', 'publisher': 'CIVHC (Colorado APCD '
                                               'administrator)',
         'document': 'Medicare Reference-Based Pricing public-use file '
                     '(FY26 release)', 'vintage': '2021-2024',
         'locator': 'FY26_Medicare Reference Based Pricing_Public Excel '
                    'File.xlsx -> vendored reference_based_pricing.csv '
                    '(1,349 rows: 12 STATEWIDE + 1,337 provider rows, 215 '
                    'orgs); source_registry.csv row civhc_rbp_fy26 '
                    '(ingested 2026-05-24); license: "CIVHC public-use '
                    'file (redistributable)"',
         'supplies': 'commercial-as-multiple-of-Medicare ratios, CO '
                     'facility claims (CONTEXT ONLY — not ambulance)',
         'url': 'https://www.civhc.org',
         'tier': 'A', 'accessed': accessed,
         'powers': ['Commercial_Context_APCD']},
    ]

    excluded = [
        {'figure': 'Commercial out-of-network leverage multiple',
         'value': '~2-4x Medicare',
         'source_label': 'ift_tracking.price_lever() component (chip '
                         '"FRAMEWORK" = renamed ILLUSTRATIVE)',
         'why_excluded': 'modeled assertion, no publisher document; the '
                         'measured bounds (HCCI 2.0x 2022, FAIR Health '
                         '1.34-1.64x 2020, MA HPC 2.7x 2019) already live '
                         'on v2.7 Payer_Rates_Commercial',
         'what_would_make_citable': 'cite HCCI/FAIR Health published '
                                    'ratios directly (as v2.7 does)'},
        {'figure': 'Government/commercial pay-mix split',
         'value': '55% / 45%',
         'source_label': 'ift_tracking._GOVT_PAY_SHARE / '
                         '_COMMERCIAL_PAY_SHARE (ILLUSTRATIVE constants)',
         'why_excluded': 'invented blend weights; GADCS publishes actual '
                         'payer-mix revenue shares (Medicare+MA 42%) — '
                         'different measure, real source',
         'what_would_make_citable': 'a GADCS or AAA payer-mix table cited '
                                    'to the primary PDF'},
        {'figure': 'Composite reimbursement-inflation read (price lever)',
         'value': '+2.5 / +2.9 / +3.8 %/yr (incl. facility escalators '
                  '+2-4%/yr)',
         'source_label': 'ift_tracking.price_lever() composite (chip '
                         '"FRAMEWORK" = renamed ILLUSTRATIVE)',
         'why_excluded': 'blends GOV AIF with the two ILLUSTRATIVE rows '
                         'above using the invented 55/45 mix — '
                         'ILLUSTRATIVE-contaminated',
         'what_would_make_citable': 'published escalator data + measured '
                                    'pay mix; until then only the GOV AIF '
                                    'series is carried (Service_Level_'
                                    'Economics / v2.7 Payment_Rules)'},
        {'figure': 'CY2025 fee ladder duplicate (ift_unit_economics.'
                   'fee_ladder)',
         'value': 'CF $278.98 x RVU ladder ("GOV (re-verify)" basis)',
         'source_label': 'ift_unit_economics.FEE_LADDER — CF captured from '
                         'MedPAC Payment Basics 2025 / search synthesis',
         'why_excluded': 'duplicates the CY2026 ladder at a weaker '
                         'evidence grade (needs_reverify=True; SCT RVU '
                         '"not excerpt-confirmed"); the CY2025 CF itself '
                         'is carried from the primary-cited '
                         'payment_mechanics() instead',
         'what_would_make_citable': 'reopen the CY2025 AFS PUF and pin '
                                    'the values to it'},
        {'figure': 'Colorado APCD facility multiple applied to ambulance '
                   'rates',
         'value': '(any use of the 1.9-2.6x CO facility ratios as an '
                  'ambulance commercial multiple)',
         'source_label': 'CIVHC CO APCD reference-based pricing file',
         'why_excluded': 'the file is hospital/facility claims — no '
                         'ambulance HCPCS in it; carried strictly as '
                         'labeled CONTEXT on Commercial_Context_APCD',
         'what_would_make_citable': 'an APCD/HCCI pull of ambulance codes '
                                    '(A0425-A0434) with commercial and '
                                    'Medicare allowed amounts'},
    ]

    notes.append(
        'Group P built from vendored files (GPCI Addendum E, CIVHC CO '
        'APCD — Tier A) and repo module ift_service_levels / ift_analytics '
        '(Tier B; module sources verified July 2026, not reopened for this '
        'build). All derived cells are live Excel formulas; APCD '
        'provider-level percentiles are build-script extractions over the '
        'vendored file (inclusive-quartile method), flagged on-sheet. '
        'GPCI file has 109 locality data rows (the raw CSV is 116 lines '
        'including headers/footnotes). A0432 PI RVU carries a re-verify '
        'flag (repo cites a PYA primer, not the PUF directly).')

    return {
        'facts': facts,
        'sources': sources,
        'excluded': excluded,
        'meta': {
            'notes': ' '.join(notes),
            'row_counts': {s['name']: wb[s['name']].max_row
                           for s in SHEETS},
        },
    }
