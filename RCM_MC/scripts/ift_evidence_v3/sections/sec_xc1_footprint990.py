"""Extension Block X-C.1: the footprint-wide Form 990 contractor sweep
(Footprint_990_Sweep tab) - the largest public window into the facility-pay
layer.

Where the cohort sweep (Cohort_990_Contractors, E.3) parsed 9 large systems
and found ZERO transport vendors in any disclosed top five, this tab widens
the lens to 64 additional nonprofit health systems operating hospitals in
the study footprint (NE IA KS MO OH WI VA MN IN KY), 78 attempted, 128 Form
990 filings parsed. At this breadth transport vendors DO surface among the
five highest-paid contractors at a handful of regional systems - a ground-
ambulance operator, an air-medical operator, and emergency-medical / ED-
coverage groups the broad keyword screen also catches (verbatim service text
shown so the reader can tell them apart). The result is recorded neutrally:
public filings; names that appear, appear; no share-of-wallet inference. The
five-slot information floor still bounds nothing - it establishes only which
vendors cracked the top five.

Input: footprint_990_sweep.json (assembled by footprint_990_sweep.py). The
990s are PUBLIC filings, so system names appear here strictly as filers of
public documents.
"""
import json
import os

SHEETS = [{'name': 'Footprint_990_Sweep',
           'question': 'Across the footprint\'s nonprofit health systems, do '
                       'transport vendors appear among the five highest-paid '
                       'contractors disclosed on their public Form 990 '
                       'filings, and what can that window even show?'}]

FRAME = ('nonprofit multi-hospital health systems operating in the study '
         'footprint, resolved from the public IRS registry')


def _clean(s):
    """No em/en dashes in any cell text; None passes through."""
    if s is None:
        return None
    return str(s).replace('—', ' - ').replace('–', ' - ').strip()


# 4.1 classification rules (printed on the tab). Decided from the verbatim
# Form 990 ServicesDesc text first, then the contractor name; NPPES taxonomy is
# the tiebreaker where a contractor resolves to an NPI. ED-STAFFING is tested
# first so an emergency-physician / provider-coverage group is never counted as
# transport even when its name contains "emergency medical" or "ambulance".
_ED_SERVICE = ('EMERGENCY ROOM PROVIDER', 'EMERGENCY MEDICAL STAFF',
               'PROVIDER COVERAGE', 'MEDICAL STAFF', 'PHYSICIAN', 'HOSPITALIST',
               'ANESTHESIA', 'RADIOLOG', 'PROFESSIONAL SERVICES', 'STAFFING',
               'LOCUM')
_AIR = ('AIR MEDICAL', 'AIR AMBULANCE', 'AVIATION', 'FLIGHT', 'HELICOPTER',
        'LIFE FLIGHT', 'AIR EVAC', 'MED-TRANS', 'MEDEVAC')
_GROUND = ('AMBULANCE', 'EMS', 'PARAMEDIC', 'MEDICAL TRANSPORT',
           'MEDICAL TRANSPORTATION')
_COURIER = ('COURIER', 'LOGISTIC', 'DELIVERY', 'FREIGHT')


def _classify(contractor, services):
    """GROUND TRANSPORT / AIR TRANSPORT / ED STAFFING / COURIER-LOGISTICS /
    OTHER-AMBIGUOUS from the verbatim services text plus the contractor name."""
    c = (contractor or '').upper()
    s = (services or '').upper()
    if any(k in s for k in _ED_SERVICE) or any(
            k in c for k in ('PHYSICIAN', 'ANESTHESIA', 'RADIOLOG',
                             'HOSPITALIST', 'LOCUM')):
        return 'ED STAFFING'
    if any(k in c for k in _AIR) or any(k in s for k in _AIR):
        return 'AIR TRANSPORT'
    if any(k in c for k in _GROUND) or any(k in s for k in _GROUND):
        return 'GROUND TRANSPORT'
    if any(k in c for k in _COURIER) or any(k in s for k in _COURIER):
        return 'COURIER-LOGISTICS'
    return 'OTHER-AMBIGUOUS'


def _emit_wrap(sb, cells, widths, cap=190):
    """A wrapped row sized to the tallest cell given per-column widths."""
    lines = 1
    for i, spec in enumerate(cells):
        if spec is None:
            continue
        v = spec[0] if isinstance(spec, tuple) else spec
        if not isinstance(v, str) or v.startswith('='):
            continue
        cpl = max(8, int(widths[i] * 1.05))
        lines = max(lines, -(-len(v) // cpl))
    sb.row(cells, height=min(cap, lines * 10.8 + 3.6), wrap=True)


def build(wb, ctx):
    lib = ctx['lib']
    scratch = os.path.dirname(ctx['cache'])
    data = json.load(open(os.path.join(scratch, 'footprint_990_sweep.json')))

    facts, sources, findings = [], [], []

    attempted = data['attempted']
    resolved = data['resolved']
    n_filings = data['filings_parsed']
    parked = data['parked']
    observed_all = data['observed_payments']
    freq_all = data['contractor_frequency']
    systems = data['systems']

    # 4.1 CLASSIFICATION: the transport-keyword screen is deliberately broad and
    # also catches emergency-department physician/provider-coverage groups. Every
    # observed row is classified from the verbatim services text plus the
    # contractor name (NPPES taxonomy is the tiebreaker where a contractor
    # resolves to an NPI; here the services text is decisive). Only GROUND and
    # AIR TRANSPORT rows feed the headlines; the rest are quarantined in a
    # labelled exclusion panel and never enter a read panel, fact or finding.
    for o in observed_all:
        o['classification'] = _classify(o.get('contractor'), o.get('services'))
    TRANSPORT_CLASSES = ('GROUND TRANSPORT', 'AIR TRANSPORT')
    observed = [o for o in observed_all
                if o['classification'] in TRANSPORT_CLASSES]
    excluded = [o for o in observed_all
                if o['classification'] not in TRANSPORT_CLASSES]
    transport_contractor_names = {_clean(o['contractor']) for o in observed}
    freq = [fr for fr in freq_all
            if _clean(fr['contractor']) in transport_contractor_names]

    # per-system roster rows (one row per system: EIN, tax years, filings,
    # contractors-over-$100K min/max, transport-matched count)
    roster = []
    gt_all = []
    for s in systems:
        rf = s['resolved_filer']
        ein = f"{rf['ein']:09d}"
        ein_fmt = f'{ein[:2]}-{ein[2:]}'
        yrs = sorted({str(f['tax_year']) for f in s['filings']
                      if f.get('tax_year')}, reverse=True)
        gts = [f['contractors_total'] for f in s['filings']
               if isinstance(f['contractors_total'], int)]
        gt_all += gts
        # classified-transport count only (GROUND + AIR); ED-staffing keyword
        # matches are excluded from the count that feeds the headline total.
        ntrans = sum(1 for f in s['filings'] for t in f['transport_contractors']
                     if _classify(t.get('name'), t.get('services'))
                     in TRANSPORT_CLASSES)
        roster.append({'system': s['system'], 'anchor': s['state_anchor'],
                       'ein': ein_fmt, 'name': rf['name'],
                       'years': ', '.join(yrs) or '-',
                       'nfil': len(s['filings']),
                       'gmin': min(gts) if gts else 0,
                       'gmax': max(gts) if gts else 0,
                       'ntrans': ntrans})
    roster.sort(key=lambda x: (-x['ntrans'], -x['gmax']))
    floor_max = max(gt_all) if gt_all else 0

    amts = [o['amount'] for o in observed if isinstance(o['amount'], int)]
    amt_lo, amt_hi = (min(amts), max(amts)) if amts else (0, 0)
    n_obs = len(observed)
    n_ops = len(freq)
    n_sys_transport = len({o['payer_system'] for o in observed})

    # operator -> systems / service types (for Panel B)
    op_detail = {}
    for o in observed:
        key = _clean(o['contractor'])
        d = op_detail.setdefault(key, {'systems': [], 'services': []})
        if o['payer_system'] not in d['systems']:
            d['systems'].append(o['payer_system'])
        sv = _clean(o['services'])
        if sv and sv not in d['services']:
            d['services'].append(sv)

    widths = [34, 12, 22, 24, 15, 11, 12, 40]
    ws = wb.create_sheet('Footprint_990_Sweep')
    sb = lib.SheetBuilder(ws, len(widths), col_widths=widths,
                          tab_color='FF4C7C2C')

    sb.title('Footprint Form 990 contractor sweep: the widest public window '
             'into the facility-pay layer')
    sb.subtitle(
        f'The question: across the footprint\'s {FRAME}, do ambulance / EMS / '
        f'medical-transport vendors surface among the five highest-paid '
        f'independent contractors disclosed on public Form 990 filings, and '
        f'what can that window show? Sources: IRS e-file 990 XML (Part VII '
        f'Section B) resolved and fetched via ProPublica Nonprofit Explorer, '
        f'latest two XML-available filings per filer. {attempted} systems '
        f'attempted, {resolved} resolved, {n_filings} filings parsed; these '
        f'sit BEYOND the 9 systems already on Cohort_990_Contractors. Join '
        f'key: system to main filer EIN to filing object_id. The 990s are '
        f'PUBLIC filings: system names appear strictly as filers of public '
        f'documents.', height=64)
    sb.note(
        'DATA QUALITY: Form 990 Part VII Section B discloses ONLY the five '
        'highest-compensated independent contractors receiving more than '
        '$100,000, so everything below each fifth slot is invisible by form '
        'design (Panel C floor). Latest two XML-available filings per filer '
        'only; newest-season XML is bot-gated for some filers. Group returns '
        'consolidate subordinate entities, so contractor books are not '
        'hospital-specific. EIN resolution picks the highest-revenue matching '
        'filer over a $50M threshold; 14 systems parked where no filer cleared '
        'that bar or the registry search returned no clean match (Panel D). '
        'The keyword screen matches the disclosed name OR services string and '
        'is deliberately broad: the term "emergency medical" also catches '
        'emergency-department physician-coverage groups. Every hit is therefore '
        'CLASSIFIED (rules panel below) from the verbatim service text; only '
        'GROUND and AIR TRANSPORT rows feed the headlines (Panel A), and the '
        'clinical-staffing hits are quarantined in the exclusion panel. Entries '
        'recorded verbatim from filings; no inference beyond the filing text.',
        height=74)
    sb.blank()

    # ---------------------------------------------------- classification rules
    sb.banner('Classification rules (4.1): every keyword hit is classed from '
              'the verbatim services text, then the contractor name')
    sb.headers(['Class', 'Rule (services text first, then name)', '', '', '',
                '', '', ''])
    for cls, rule in [
        ('ED STAFFING', 'services or name names physician / provider coverage / '
         'medical staff / hospitalist / anesthesia / radiology / staffing - '
         'clinical labor, NOT a transport of a patient. Tested first.'),
        ('AIR TRANSPORT', 'air medical / air ambulance / aviation / flight / '
         'life flight / med-trans - a rotary or fixed-wing patient transport.'),
        ('GROUND TRANSPORT', 'ambulance / EMS / paramedic / medical transport - '
         'a ground patient transport operator.'),
        ('COURIER-LOGISTICS', 'courier / logistics / delivery / freight - moves '
         'specimens or goods, not patients.'),
        ('OTHER-AMBIGUOUS', 'no rule fires; carried but excluded from every '
         'transport headline until resolved.')]:
        _emit_wrap(sb, [(cls, 'label'), (rule, 'note'), None, None, None,
                        None, None, None], widths)
    sb.blank()

    # ------------------------------------------------------------- Panel A
    sb.banner('Panel A. Observed facility-direct TRANSPORT payments - GROUND '
              'and AIR TRANSPORT only (the headline subset; ED-staffing and '
              'other keyword hits are quarantined in the exclusion panel)')
    sb.headers(['Payer system (public Form 990 filer)', 'Filer EIN',
                'Contractor (as disclosed)', 'Services (verbatim)',
                'Amount $', 'Tax year', 'Classification', 'Keyword matched'])
    a0 = sb.r + 1
    for o in observed:
        ein = f"{o['payer_ein']:09d}"
        _emit_wrap(sb, [
            (_clean(o['payer_system']), 'src'),
            (f'{ein[:2]}-{ein[2:]}', 'src'),
            (_clean(o['contractor']), 'src'),
            (_clean(o['services']), 'src'),
            (o['amount'], 'src', lib.FMT_USD),
            (int(o['tax_year']) if str(o['tax_year']).isdigit()
             else o['tax_year'], 'src', lib.FMT_INT),
            (o['classification'], 'label'),
            (_clean(next((t.get('match_term')
                          for s in systems for f in s['filings']
                          for t in f['transport_contractors']
                          if t['name'] == o['contractor']
                          and t['amount'] == o['amount']), '')) or '-', 'note'),
        ], widths)
    a1 = sb.r
    a_tot = sb.r + 1
    sb.row([('Transport appearances (GROUND + AIR)', 'label'), None, None, None,
            (f'=SUM(E{a0}:E{a1})', 'fml', lib.FMT_USD), None,
            (f'=COUNTA(A{a0}:A{a1})', 'fml', lib.FMT_INT), None])
    sb.note(
        'Read: every row here is an unambiguous facility-direct patient-'
        'transport payment - a GROUND ambulance operator (Mercury Ambulance '
        'Service, services "AMBULANCE SERVICES") and an AIR-medical operator '
        '(PHI Air Medical, services "AVIATION TRANS. SVCS" / "TRANSPORTATION"). '
        'The count cell is a live COUNTA and the amount a live SUM, so every '
        'headline downstream reads the transport subset only. Recorded as '
        'public-filing facts, not vendor relationships.')
    sb.blank()

    # ------------------------------------------------- Exclusion panel (4.1)
    sb.banner('Exclusion panel. Keyword hits that are NOT transport - excluded '
              'from every headline figure, read panel and finding')
    sb.headers(['Payer system (public Form 990 filer)', 'Filer EIN',
                'Contractor (as disclosed)', 'Services (verbatim)',
                'Amount $', 'Tax year', 'Classification',
                'Why excluded'])
    x0 = sb.r + 1
    for o in excluded:
        ein = f"{o['payer_ein']:09d}"
        _emit_wrap(sb, [
            (_clean(o['payer_system']), 'src'),
            (f'{ein[:2]}-{ein[2:]}', 'src'),
            (_clean(o['contractor']), 'src'),
            (_clean(o['services']), 'src'),
            (o['amount'], 'src', lib.FMT_USD),
            (int(o['tax_year']) if str(o['tax_year']).isdigit()
             else o['tax_year'], 'src', lib.FMT_INT),
            (o['classification'], 'label'),
            ('emergency-department physician / provider-coverage group: '
             'clinical staffing, not patient transport', 'note'),
        ], widths)
    x1 = sb.r
    sb.note(
        f'These {len(excluded)} rows are emergency-department physician and '
        'provider-coverage contractors (their verbatim service strings are in '
        'the Services column of each row above, classed ED STAFFING) that the '
        'broad "emergency medical" keyword caught. They are clinical labor, not '
        'a transport of a patient, so they are excluded from every transport '
        'figure, read panel and finding on this tab. The largest of them (over '
        '$12M) is why the raw pre-classification count would have overstated '
        'the transport layer roughly fourfold; the corrected transport count is '
        'the live COUNTA in Panel A.')
    sb.blank()

    # ------------------------------------------------------------- Panel B
    sb.banner('Panel B. Transport-operator frequency: GROUND and AIR operators '
              'that recur across the parsed filings (ED-staffing excluded)')
    sb.headers(['Transport operator (as disclosed)', 'Appearances (filings)',
                'Payer systems (public filers)', 'Service type (verbatim)',
                'Classification', '', '', ''])
    b0 = sb.r + 1
    for fr in freq:
        d = op_detail.get(_clean(fr['contractor']), {'systems': [],
                                                     'services': []})
        cls = next((o['classification'] for o in observed
                    if _clean(o['contractor']) == _clean(fr['contractor'])), '-')
        _emit_wrap(sb, [
            (_clean(fr['contractor']), 'src'),
            (fr['appearances'], 'src', lib.FMT_INT),
            ('; '.join(d['systems']) or '-', 'src'),
            ('; '.join(d['services']) or '-', 'src'),
            (cls, 'label'), None, None, None], widths)
    b1 = sb.r
    sb.note(f'Frequency is appearances across the {n_filings} parsed filings, '
            'not a share of any system\'s spend. After classification: '
            f'{n_ops} distinct transport operators, {n_obs} filing appearances '
            '(one ground, one air); no operator appears at more than one '
            'system. The four ED-staffing appearances are in the exclusion '
            'panel above.')
    sb.blank()

    # ------------------------------------------------------------- Panel C
    sb.banner('Panel C. Systems swept: contractors over $100K per filing, and '
              'the five-slot information floor')
    sb.headers(['System (public Form 990 filer)', 'State anchor', 'Filer EIN',
                'Tax years parsed', 'Filings parsed',
                'Contractors >$100K/filing (min)',
                'Contractors >$100K/filing (max)',
                'Transport-keyword contractors'])
    c0 = sb.r + 1
    for r in roster:
        _emit_wrap(sb, [
            (_clean(r['system']), 'src'),
            (r['anchor'], 'src'),
            (r['ein'], 'src'),
            (r['years'], 'src'),
            (r['nfil'], 'src', lib.FMT_INT),
            (r['gmin'], 'src', lib.FMT_INT),
            (r['gmax'], 'src', lib.FMT_INT),
            (r['ntrans'], 'src', lib.FMT_INT)], widths)
    c1 = sb.r
    tot = sb.r + 1
    sb.row([(f'Total ({resolved} systems resolved)', 'label'), None, None, None,
            (f'=SUM(E{c0}:E{c1})', 'fml', lib.FMT_INT),
            (f'=MIN(F{c0}:F{c1})', 'fml', lib.FMT_INT),
            (f'=MAX(G{c0}:G{c1})', 'fml', lib.FMT_INT),
            (f'=SUM(H{c0}:H{c1})', 'fml', lib.FMT_INT)])
    sb.note('Min of 0 in the "min" column reflects filers whose Form 990 '
            'discloses no Section B contractors at all in a parsed year; the '
            'hospital-operating filers disclose from double digits to '
            f'{floor_max:,} contractors over $100,000 in a single filing.')
    sb.prose(
        f'The information floor, stated plainly: THIS BOUNDS NOTHING. Form 990 '
        f'Part VII Section B discloses only the five highest-compensated '
        f'independent contractors over $100,000. Across the parsed filings the '
        f'count of contractors over $100,000 reached as high as {floor_max:,} '
        f'at a single filer, with only five named. A transport vendor billing '
        f'below a filer\'s fifth-highest contractor - at these systems, slots '
        f'held by nine-figure staffing, physician-group and construction '
        f'vendors - is invisible by form design. The {n_obs} classified '
        f'transport appearances in Panel A establish only what CRACKED the top '
        f'five at {n_sys_transport} regional filers; they are NOT an upper '
        f'bound on transport spend, NOT a count of transport relationships, and '
        f'NOT evidence of absence anywhere they do not appear.')
    sb.blank()

    # ------------------------------------------------------------- Panel D
    sb.banner('Panel D. Parked systems: attempted but not resolved to a '
              'parseable main filer (honest failures)')
    sb.headers(['System (attempted)', 'State anchor', 'Park reason', '', '',
                '', '', ''])
    d0 = sb.r + 1
    for p in parked:
        _emit_wrap(sb, [
            (_clean(p['system']), 'label'),
            (p['state_anchor'], 'src'),
            (_clean(p['reason']), 'note'), None, None, None, None, None],
            widths)
    d1 = sb.r
    sb.note('Parks are dominated by group-return structure: the searchable '
            'parent EIN often reports $0 or sub-threshold revenue while the '
            'operating hospitals file under separate subordinate EINs, and a '
            'few common system names return no clean single-filer match. '
            'Recorded as honest failures, not as absence of filings.')
    sb.blank()

    # ------------------------------------------------------------- Read panel
    sb.banner('Read panel')
    sb.prose(
        f'What is measured: {resolved} footprint nonprofit health systems '
        f'({attempted} attempted, {len(parked)} parked) resolved to public '
        f'Form 990 filers, {n_filings} filings parsed. At this breadth the '
        f'facility-pay transport layer becomes VISIBLE in public filings: '
        f'CLASSIFIED transport contractors (ground and air; ED-staffing keyword '
        f'hits excluded to the exclusion panel) surface in the disclosed top '
        f'five at {n_sys_transport} regional systems ({n_ops} distinct '
        f'operators, {n_obs} filing appearances) - a ground-ambulance operator '
        f'and an air-medical operator - with observed amounts from ${amt_lo:,} '
        f'to ${amt_hi:,}. What that means - and all it means: at market scale a '
        f'facility DOES sometimes pay a transport operator enough to crack its '
        f'five-slot disclosure window, which the 9-system cohort never showed. '
        f'What it cannot mean: the window still discloses only five contractors '
        f'while a single filer reports {floor_max:,} over $100,000, so absence '
        f'from the top five is never evidence of absence of spend. The neutral, '
        f'measured statement stands alone: these transport vendors cracked the '
        f'top five at these filers in the parsed years.')

    lib.add_chart(
        ws, f'A{sb.r + 2}',
        'Contractors over $100K at the largest parsed filing per system '
        '(only 5 are disclosed)',
        f"'Footprint_990_Sweep'!$A${c0}:$A${c1}",
        [('Contractors over $100K (max filing)',
          f"'Footprint_990_Sweep'!$G${c0}:$G${c1}")],
        kind='bar', y_fmt='#,##0')

    # ---------------------------------------------------------------- sources
    sources += [
        {'key': 'irs990_partvii_footprint',
         'publisher': 'IRS (e-file Form 990 XML) via ProPublica Nonprofit '
                      'Explorer / GivingTuesday 990 data lake',
         'document': f'Form 990 Part VII Section B '
                     f'(IndependentContractorCompensationGrp, ContractorName / '
                     f'ServicesDesc / CompensationAmt, and '
                     f'CntrctRcvdGreaterThan100KCnt) parsed from IRS e-file '
                     f'XML for {n_filings} filings across {resolved} footprint '
                     f'health-system main filers, latest two XML-available '
                     f'filings per filer (footprint_990_sweep.json)',
         'vintage': 'Tax years 2022-2024 as available per filer',
         'locator': 'Per-filing object_id recorded in footprint_990_sweep.json; '
                    'XML from gt990datalake-rawdata.s3.amazonaws.com, '
                    'download-xml fallback; per-system counts on Panel C',
         'supplies': 'The disclosed five-highest-paid contractor names, '
                     'services and amounts per filer, the count of contractors '
                     'over $100K (the information floor), and every transport-'
                     'keyword match (Panels A/B)',
         'url': 'https://projects.propublica.org/nonprofits/',
         'tier': 'A', 'accessed': ctx['accessed'],
         'powers': ['Footprint_990_Sweep']},
        {'key': 'propublica_registry_footprint',
         'publisher': 'ProPublica Nonprofit Explorer (IRS registry mirror)',
         'document': 'Nonprofit Explorer API v2 organization search used to '
                     'resolve footprint health systems to main filer EINs '
                     '(state and name filtered, foundation / health-plan / '
                     'auxiliary filers excluded, highest-revenue matching '
                     'filer chosen), with parks recorded on Panel D',
         'vintage': 'Registry as accessed for the sweep',
         'locator': 'Panel C EIN column; Panel D park reasons; runner-up '
                    'candidates in footprint_990_sweep.json',
         'supplies': 'The system-to-EIN mapping (analyst-selected from public '
                     'registry facts) and the honest park register',
         'url': 'https://projects.propublica.org/nonprofits/api',
         'tier': 'B', 'accessed': ctx['accessed'],
         'powers': ['Footprint_990_Sweep']},
    ]

    # ------------------------------------------------------------------ facts
    facts += [
        {'metric': 'Footprint nonprofit health systems resolved to public '
                   'Form 990 filers (beyond the 9-system cohort)',
         'year': 2026, 'value': resolved,
         'unit': 'health systems (public filings)', 'basis': 'GOV', 'tier': 'B',
         'source_keys': ['propublica_registry_footprint'],
         'locator': 'Footprint_990_Sweep Panel C roster; total row',
         'lives_on': 'Footprint_990_Sweep',
         'cross_check': f'{attempted} attempted, {len(parked)} parked (Panel '
                        f'D); mapping is analyst-selected from public registry '
                        f'facts (tier B)'},
        {'metric': 'Form 990 filings parsed for Part VII Section B contractors '
                   '(footprint sweep)', 'year': 2024, 'value': n_filings,
         'unit': 'filings (latest two XML-available per filer, tax years '
                 '2022-2024)', 'basis': 'GOV', 'tier': 'A',
         'source_keys': ['irs990_partvii_footprint'],
         'locator': 'Panel C filings column (live SUM in the total row); '
                    'per-filing object_id in footprint_990_sweep.json',
         'lives_on': 'Footprint_990_Sweep',
         'cross_check': f'{resolved} filers; latest two filings each where '
                        'XML available'},
        {'metric': 'Classified transport contractors (ground + air) observed in '
                   'the disclosed five-highest-paid contractors (footprint '
                   'sweep, ED-staffing excluded)',
         'year': 2024, 'value': n_obs,
         'unit': f'filing appearances ({n_ops} distinct operators across '
                 f'{n_sys_transport} systems)', 'basis': 'GOV', 'tier': 'A',
         'source_keys': ['irs990_partvii_footprint'],
         'locator': 'Panel A (GROUND + AIR only), live COUNTA in the transport '
                    'total row; Panel B frequency; Panel C classified column',
         'lives_on': 'Footprint_990_Sweep',
         'cross_check': f'Observed amounts ${amt_lo:,} to ${amt_hi:,}; a '
                        'ground-ambulance and an air-medical operator; the four '
                        'ED-staffing keyword hits are quarantined in the '
                        'exclusion panel and excluded from this count'},
        {'metric': 'Maximum contractors over $100,000 disclosed at a single '
                   'filer (the five-slot information floor)', 'year': 2024,
         'value': floor_max, 'unit': 'contractors over $100K (only five named)',
         'basis': 'GOV', 'tier': 'A',
         'source_keys': ['irs990_partvii_footprint'],
         'locator': 'Panel C max column (live MAX in the total row); '
                    'CntrctRcvdGreaterThan100KCnt as filed',
         'lives_on': 'Footprint_990_Sweep',
         'cross_check': 'Part VII Section B discloses only the top five over '
                        '$100K; with this many undisclosed, absence from the '
                        'top five is NOT evidence of absence of spend'},
    ]

    # --------------------------------------------------------------- finding
    findings.append({
        'id_hint': 103,
        'finding': (
            f'The market-wide 990 window makes the facility-pay transport layer '
            f'VISIBLE where the 9-system cohort could not: across {resolved} '
            f'footprint health systems and {n_filings} parsed filings, and '
            f'after classifying every keyword hit, {n_obs} CLASSIFIED transport '
            f'appearances surface among the disclosed five highest-paid '
            f'contractors at {n_sys_transport} regional systems - a '
            f'ground-ambulance operator (Mercury Ambulance Service) and an '
            f'air-medical operator (PHI Air Medical) - at observed amounts from '
            f'${amt_lo:,} to ${amt_hi:,}. The four emergency-department '
            f'staffing contractors the broad keyword also caught are '
            f'quarantined in the exclusion panel and enter no figure here. That '
            f'a facility can pay a transport operator enough to crack its '
            f'five-slot window is the measured, neutral fact; it establishes '
            f'the layer exists at market scale, nothing more.'),
        'numbers': f"='Footprint_990_Sweep'!G{a_tot}",
        'sources': 'irs990_partvii_footprint; propublica_registry_footprint',
        'confidence': 'High that the parsed filings disclose what Panels A-C '
                      'record; the transport hits are verbatim public-filing '
                      'facts',
        'guardrail': (
            f'This BOUNDS NOTHING. Part VII Section B discloses only the five '
            f'highest-paid contractors over $100,000 while a single filer '
            f'reports up to {floor_max:,} of them, so a transport vendor below '
            f'the fifth slot is invisible by form design. The {n_obs} '
            f'classified transport appearances establish only what cracked the '
            f'top five at {n_sys_transport} filers; they are '
            f'not an upper bound on transport spend, not a count of '
            f'relationships, and absence elsewhere is not evidence of absence. '
            f'No share-of-wallet inference; systems appear solely as filers of '
            f'public documents.')})

    return {'facts': facts, 'sources': sources, 'excluded': [],
            'findings': findings,
            'meta': {'input': 'footprint_990_sweep.json',
                     'attempted': attempted, 'resolved': resolved,
                     'filings_parsed': n_filings,
                     'transport_appearances': n_obs,
                     'distinct_operators': n_ops,
                     'information_floor_max_gt100k': floor_max}}
