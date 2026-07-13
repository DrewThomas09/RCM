"""E.2 + E.3: the public contract corpus and the cohort 990 contractor sweep.

Tab 1, Contract_Corpus (E.2): one row per abstracted PUBLIC ambulance /
patient-transport contract document (12 documents, state / county /
municipal issuers) on the 6.4 field schema (per-trip rates, dedicated-unit
rate, subsidy, escalator, term, exclusivity, SLA, penalties, equipment,
technology fees), plus the USAspending PSC V225 top-15 award ladder flagged
for PIID document lookup, an observed-structure mini-table with live
MIN/MAX escalator and subsidy ranges, and the honest parked register (11
items with blockers). Input: contract_corpus.json (assembled 2026-07-11).

Tab 2, Cohort_990_Contractors (E.3): the Form 990 Part VII Section B sweep
across the research cohort of representative multi-hospital health systems
operating in the study footprint, selected for depth - 9 systems, 24 EINs,
46 parsed filings, zero transport-matching contractors among the disclosed
five highest-paid contractors, and the information floor stated plainly:
the five-contractor disclosure window bounds nothing. Input:
cohort_990.json (assembled 2026-07-11). The 990s are public filings, so
system names appear here strictly as filers of public documents.
"""
import json
import os
import re

SHEETS = [
    {'name': 'Contract_Corpus',
     'question': 'What do public contract documents establish about the '
                 'structures by which facilities and governments buy '
                 'ambulance service?'},
    {'name': 'Cohort_990_Contractors',
     'question': 'Do transport vendors appear among the five highest-paid '
                 'contractors disclosed on the cohort systems\' public '
                 'Form 990 filings, and what can that window even show?'},
]

COHORT_FRAME = ('research cohort of representative multi-hospital health '
                'systems operating in the study footprint, selected for '
                'depth')

# 6.4 field schema: (json_key, header)
FIELDS = [
    ('per_trip_rates_by_level', 'Per-trip rates by level'),
    ('dedicated_unit_or_unit_hour_rate', 'Dedicated-unit / unit-hour rate'),
    ('minimum_commitment_or_subsidy', 'Minimum commitment / subsidy'),
    ('escalator_mechanics_and_dates', 'Escalator mechanics and dates'),
    ('term_and_renewal', 'Term and renewal'),
    ('exclusivity_or_first_call', 'Exclusivity / first-call'),
    ('response_time_SLA', 'Response-time SLA'),
    ('penalty_structure', 'Penalty structure'),
    ('equipment_responsibility', 'Equipment responsibility'),
    ('technology_platform_fees', 'Technology / platform fees'),
]

# Observed-structure assignment (analyst-assigned from the document's
# payment and authority structure; rendered BLACK, never blue). Keyed on a
# unique URL token so a reordering of the corpus JSON cannot misalign rows.
# (token, structure class, numeric fixed annual escalator where the
#  document states one, numeric annual dedicated-unit subsidy where stated)
CLASS_BY_TOKEN = [
    ('104886', 'Per-trip rate schedule (state client transport)',
     None, None),
    ('114283', 'Per-trip rate schedule (state client transport)',
     None, None),
    ('cityofcharlescity', 'Dedicated-unit + subsidy', 0.03, 415000),
    ('plaistow', 'Dedicated-unit + subsidy', 0.025, 650000),
    ('topeka-ordinances',
     'Franchise / operating authority (patient-billed)', None, None),
    ('snco.gov', 'Contract performance report', None, None),
    ('siouxfalls.gov', 'Contract performance report', None, None),
    ('extension.wisc', 'Model / template agreement', None, None),
    ('pueblo.us', 'Franchise / operating authority (patient-billed)',
     None, None),
    ('evogov', 'Franchise / operating authority (patient-billed)',
     None, None),
    ('columbiacountyor',
     'Franchise / operating authority (patient-billed)', None, None),
    ('smchealth', 'Franchise / operating authority (patient-billed)',
     None, None),
]
CLASS_ORDER = [
    'Per-trip rate schedule (state client transport)',
    'Dedicated-unit + subsidy',
    'Franchise / operating authority (patient-billed)',
    'Contract performance report',
    'Model / template agreement',
]

USASP_URL = 'https://api.usaspending.gov/api/v2/search/spending_by_award/'


def _clean(s):
    """No em/en dashes in cell text, ever; None passes through."""
    if s is None:
        return None
    return str(s).replace('—', ' - ').replace('–', ' - ').strip()


_LOCAL_RX = re.compile(
    r'\s*\.?\s*(?:local copy[:\s]*)?pdfs/\S+?\.(?:pdf|docx?|xlsx?)\b\.?',
    re.I)


def _strip_local(s):
    """Drop non-retrievable local-copy file-path fragments (e.g. 'Local copy:
    pdfs/topeka_amr_franchise_2021.pdf') from a scope note. The retrievable
    public URL already sits in its own column, so a local path only breaks the
    reproducible-from-the-public-internet promise for a third-party reader.
    Returns None when nothing substantive remains."""
    if s is None:
        return None
    out = _LOCAL_RX.sub('', str(s))
    out = re.sub(r'\s{2,}', ' ', out).strip(' .;,-')
    return out or None


def _per_trip_text(d):
    """Render the per_trip_rates_by_level dict compactly; None -> None."""
    if not d:
        return None
    label = {'BLS': 'BLS', 'ALS': 'ALS', 'SCT': 'SCT', 'note': 'Note',
             'non_ambulance_client_transport':
                 'Non-ambulance client transport'}
    parts = [f'{label.get(k, k)}: {_clean(v)}'
             for k, v in d.items() if v]
    return '; '.join(parts) if parts else None


class _Rows:
    """Wrapped rows with heights sized to the longest cell per column."""

    def __init__(self, sb, widths):
        self.sb = sb
        self.w = widths

    def emit(self, cells, cap=300):
        lines = 1
        for i, spec in enumerate(cells):
            if spec is None:
                continue
            v = spec[0] if isinstance(spec, tuple) else spec
            if not isinstance(v, str) or v.startswith('='):
                continue
            cpl = max(8, int(self.w[i] * 1.05))
            lines = max(lines, -(-len(v) // cpl))
        self.sb.row(cells, height=min(cap, lines * 10.8 + 3.6), wrap=True)


def _src_or_dash(v):
    v = _clean(v)
    return (v, 'src') if v else ('-', 'note')


# ======================================================================
# Tab 1: Contract_Corpus (E.2)
# ======================================================================
def _build_corpus_tab(wb, ctx, corpus, sources, facts, findings):
    lib = ctx['lib']
    docs = corpus['public_contracts']
    parked = corpus['parked']
    va = corpus['va_awards']
    n_va_dept = sum(1 for a in va
                    if a['awarding_agency'] == 'Department of Veterans '
                                               'Affairs')
    # The IFT-relevant federal ladder is the Department of Veterans Affairs
    # subset (VA facilities buying interfacility ambulance transport); show the
    # top 25 by award amount so a reader sees the real recipient set, not a
    # 4-row sample. Falls back to all VA awards when fewer than 25 exist.
    top25 = sorted([a for a in va
                    if a['awarding_agency'] == 'Department of Veterans '
                                               'Affairs'],
                   key=lambda a: -a['award_amount'])[:25]

    # classification aligned by URL token, never by list position alone
    cls = []
    for d in docs:
        url = d.get('url') or ''
        hit = [c for c in CLASS_BY_TOKEN if c[0] in url]
        if len(hit) != 1:
            raise ValueError(f'corpus classification token miss: {url[:60]}')
        cls.append(hit[0])

    widths = [36, 8, 17, 22, 30, 22, 30, 28, 24, 26, 30, 30, 24, 24,
              42, 34, 24, 11, 13]
    ws = wb.create_sheet('Contract_Corpus')
    sb = lib.SheetBuilder(ws, len(widths), col_widths=widths,
                          tab_color='FF8C1D40')
    rr = _Rows(sb, widths)

    sb.title('Contract corpus: how facilities and governments buy '
             'ambulance service, in the documents themselves')
    sb.subtitle('The question: what do PUBLIC contract documents establish '
                'about the structures by which facilities and governments '
                'buy ambulance and patient-transport service - per-trip '
                'rates, dedicated-unit subsidies, escalators, exclusivity, '
                'SLAs, penalties? Sources: 12 abstracted public contract '
                'documents (state, county and municipal issuers; per-row '
                'URLs in column O) on the 6.4 field schema, plus the '
                'USAspending PSC V225 award ladder (top 25 Department of '
                'Veterans Affairs awards by amount, FY2023-FY2025 activity '
                'window), each retrievable by PIID. Join keys: document URL '
                'for the corpus; PIID for '
                'federal awards. Blue = lifted from the fetched document; '
                'black = assigned or computed here; null fields render '
                'as - meaning NOT STATED in the fetched document.',
                height=64)
    sb.note('DATA QUALITY: this corpus is a CONVENIENCE SAMPLE of public '
            'contracts - government buyers are overrepresented by '
            'construction, because private facility-to-operator ambulance '
            'agreements are not public records (stated plainly; see the '
            'final parked row). Dollar figures span document dates from '
            '2018 to 2025 and are not inflation-adjusted or comparable '
            'across years. Two documents are contract performance reports '
            'and one is a model template, not executed rate documents; '
            'they are classed as such in column Q. The two Nebraska DHHS '
            'rows are NON-AMBULANCE client-transport rate contracts, '
            'carried with their scope notes in column P. A - cell means '
            'the fetched document does not state the field, not that the '
            'underlying contract lacks it.', height=54)
    sb.blank()

    # ---------------------------------------------------------- Panel A
    sb.banner('Panel A. Abstracted public contracts - one row per '
              'document, 6.4 field schema (blue = document text)')
    sb.headers(['Issuer', 'State', 'Date', 'Document type']
               + [h for _, h in FIELDS]
               + ['URL', 'Scope note', 'Observed structure (assigned, '
                  'black)', 'Escalator %/yr (numeric where stated)',
                  'Dedicated-unit annual subsidy $ (numeric where '
                  'stated)'])
    a0 = sb.r + 1
    for d, (_, klass, esc, sub) in zip(docs, cls):
        cells = [_src_or_dash(d['issuer']),
                 _src_or_dash(d['state']),
                 _src_or_dash(d['date']),
                 _src_or_dash(d['doc_type'])]
        for key, _ in FIELDS:
            v = d[key]
            if key == 'per_trip_rates_by_level':
                v = _per_trip_text(v)
            cells.append(_src_or_dash(v))
        cells.append((_clean(d['url']), 'text'))
        cells.append(((_strip_local(_clean(d['notes'])) or '-'), 'note'))
        cells.append((klass, 'text'))
        cells.append((esc, 'src', lib.FMT_PCT1) if esc is not None
                     else ('-', 'note'))
        cells.append((sub, 'src', lib.FMT_USD) if sub is not None
                     else ('-', 'note'))
        rr.emit(cells)
    a1 = sb.r
    sb.note('Column Q structure classes are assigned by the analyst from '
            'the payment and authority structure the document evidences '
            '(black text, not document language). Columns R and S carry a '
            'number ONLY where the document states a fixed annual '
            'percentage escalator or an annual dedicated-unit subsidy; '
            'Panel C takes live MIN/MAX over them.')
    sb.blank()

    # ---------------------------------------------------------- Panel B
    sb.banner('Panel B. Federal award ladder: USAspending PSC V225 '
              '(Ambulance Service), top 25 Department of Veterans Affairs '
              'awards by amount, FY2023-FY2025 activity window - the VA is '
              'the largest public interfacility-transport buyer in the data '
              '(blue = USAspending record)')
    sb.headers(['Recipient', 'PoP state', 'Period of performance', 'PIID',
                'Awarding agency / sub-agency', 'Award amount $',
                'Award type', 'Award description (as recorded)'])
    b0 = sb.r + 1
    for a in top25:
        rr.emit([
            (_clean(a['recipient']), 'src'),
            (_clean(a['pop_state']), 'src'),
            (f"{a['start_date']} to {a['end_date']}", 'src'),
            (_clean(a['award_id_piid']), 'src'),
            (f"{_clean(a['awarding_agency'])} / "
             f"{_clean(a['awarding_sub_agency'])}", 'src'),
            (a['award_amount'], 'src', lib.FMT_USD),
            (_clean(a['contract_award_type']), 'src'),
            (_clean(a['description']), 'src')])
    b1 = sb.r
    sb.row([('Top-25 VA award amounts, total', 'label'), None, None, None,
            None, (f'=SUM(F{b0}:F{b1})', 'fml', lib.FMT_USD), None,
            ('live over the ladder above', 'note')])
    sb.note(f'Source: USAspending award search API '
            f'(spending_by_award, psc_codes V225, award types A-D, '
            f'FY2023-FY2025 activity window, sorted by award amount, 300 '
            f'records pulled; assembly method recorded with the corpus '
            f'register). {n_va_dept} of the 300 records are Department of '
            f'Veterans Affairs awards (the VA runs the largest public '
            f'interfacility-transport book in the data); the ladder above is '
            f'the top 25 of them by amount. The rest of the 300 are DoD, '
            f'State, HHS and Peace Corps under the same PSC. Each row is '
            f'retrievable by PIID on USAspending.gov; the underlying '
            f'price-schedule DOCUMENTS require SAM.gov attachment retrieval '
            f'which is key-gated, so those sit in the parked register '
            f'(Panel D, first row). Award amounts are contract ceilings / '
            f'obligated amounts as recorded, NOT annual revenue.',
            height=52)
    sb.blank()

    # ---------------------------------------------------------- Panel C
    sb.banner('Panel C. Observed structure mix and numeric observables '
              '(live over Panel A)')
    sb.headers(['Observed structure (assigned; rule in Panel A note)',
                'Documents'])
    c0 = sb.r + 1
    for k in CLASS_ORDER:
        rn = sb.r + 1
        sb.row([(k, 'text'),
                (f'=COUNTIF($Q${a0}:$Q${a1},A{rn})', 'fml', lib.FMT_INT)])
    c1 = sb.r
    sb.row([('Total corpus documents', 'label'),
            (f'=SUM(B{c0}:B{c1})', 'fml', lib.FMT_INT)])
    c_tot = sb.r
    sb.blank()
    sb.headers(['Numeric observable', '', '', '', '', 'Min', 'Max',
                'Documents supplying the value'])
    esc_row = sb.r + 1
    sb.row([('Fixed annual escalator, where the document states one '
             '(share per year)', 'label'), None, None, None, None,
            (f'=MIN(R{a0}:R{a1})', 'fml', lib.FMT_PCT1),
            (f'=MAX(R{a0}:R{a1})', 'fml', lib.FMT_PCT1),
            ('n=2: five-town NH system 2.5% (renewal-term, built in); '
             'Charles City IA / Floyd County 3.0% annual', 'note')],
           wrap=True, height=24)
    sub_row = sb.r + 1
    sb.row([('Dedicated-unit annual subsidy, where the document states '
             'one (USD per year)', 'label'), None, None, None, None,
            (f'=MIN(S{a0}:S{a1})', 'fml', lib.FMT_USD),
            (f'=MAX(S{a0}:S{a1})', 'fml', lib.FMT_USD),
            ('n=2: Charles City IA USD 415,000 Year 1 (rises to USD '
             '440,273 Year 3); five-town NH system USD 650,000 per year '
             '(USD 130,000 per town)', 'note')], wrap=True, height=24)
    sb.note('MIN/MAX are live over Panel A columns R and S and ignore '
            'the - text cells. n=2 in both rows: these are the observed '
            'ends of a two-document range, not a market distribution.')
    sb.blank()

    # ---------------------------------------------------------- Panel D
    sb.banner('Panel D. Parked register: located but not abstracted, '
              'with the blocker stated (honest rows)')
    sb.headers(['Parked item', '', '', '', 'Blocker', '', '', '', '', '',
                '', '', '', '', 'URL'])
    d0 = sb.r + 1
    for p in parked:
        rr.emit([(_clean(p['source']), 'src'), None, None, None,
                 (_strip_local(_clean(p['blocker'])) or '-', 'note'),
                 None, None, None, None,
                 None, None, None, None, None,
                 ((_clean(p['url']) or '-'), 'text')])
    d1 = sb.r
    sb.blank()

    sb.banner('Read panel')
    sb.prose('What the public record establishes about how ambulance '
             'service is bought: (1) STRUCTURE MIX - of 12 corpus '
             'documents, 5 are franchise / operating-authority documents '
             'where a government grants the territory and the operator is '
             'paid from patient billing (Topeka, Benton, Columbia County '
             'OR, Pueblo, San Mateo EOA), 2 are dedicated-unit + subsidy '
             'contracts where buyers purchase CAPACITY (a 24-hour ALS '
             'unit) rather than trips, 2 are state per-trip rate '
             'schedules for non-ambulance client transport, 2 are '
             'contract performance reports and 1 is a model template. '
             '(2) THE DEDICATED-UNIT PATTERN - Charles City IA (USD '
             '415,000 Year 1, 3.0% built-in annual steps, hospital '
             'pledged USD 100,000 to year one) and the five-town NH '
             'system (USD 650,000 per year, two dedicated ALS ambulances, '
             '2.5% renewal-term escalator): capacity is subsidized, '
             'billing stays with the operator. (3) ESCALATORS - where '
             'stated as a fixed annual step, 2.5-3.0% (live range above). '
             '(4) INTERFACILITY LEGS CARRY THEIR OWN SLAs - Sioux Falls: '
             'scheduled interfacility (Priority 4) paramedic ambulance '
             'within 30 minutes of requested pickup 90% of the time, '
             'unscheduled (Priority 5) 90-minute goal; Benton AR: '
             'hospital transfer 30 minutes emergent / 60 minutes '
             'non-emergent. (5) The San Mateo EOA shows the fee stack a '
             'large-market operator funds (dispatch, CAD, radio, EMS '
             'oversight, JPA first-responder fees). What it does NOT '
             'establish: private facility-to-operator agreement terms - '
             'those are not public records, and the closest public '
             'analogs are the dedicated-unit contracts and the '
             'interfacility SLA clauses above.')

    lib.add_chart(ws, f'A{sb.r + 2}',
                  'Corpus documents by observed structure (n=12)',
                  f"'Contract_Corpus'!$A${c0}:$A${c1}",
                  [('Documents', f"'Contract_Corpus'!$B${c0}:$B${c1}")],
                  kind='bar', y_fmt='#,##0')

    # ------------------------------------------------------------ sources
    sources += [
        {'key': 'contract_corpus_register',
         'publisher': 'Multiple public issuers (state, county and '
                      'municipal; documents fetched from official '
                      'repositories)',
         'document': 'E.2 public ambulance / patient-transport contract '
                     'corpus: 12 documents abstracted on the 6.4 field '
                     'schema, 11 items parked with blockers, assembled '
                     '2026-07-11 (contract_corpus.json)',
         'vintage': 'Document dates 2018-2025; assembled 2026-07-11',
         'locator': 'Per-document URLs in Contract_Corpus column O; local '
                    'copies noted per row in column P',
         'supplies': 'The observed public structures for buying ambulance '
                     'service: franchise/EOA, dedicated-unit + subsidy, '
                     'per-trip schedules, escalators, SLAs, penalties',
         'url': 'https://statecontracts.nebraska.gov/ (portal example; '
                'per-document URLs on Contract_Corpus column O)',
         'tier': 'A', 'accessed': ctx['accessed'],
         'powers': ['Contract_Corpus']},
        {'key': 'usasp_v225_awards', 'publisher': 'USAspending.gov '
                                                  '(Treasury)',
         'document': 'Award search, spending_by_award, PSC V225 '
                     '(Ambulance Service), award types A-D, FY2023-FY2025 '
                     'activity window, top 300 by award amount',
         'vintage': 'Pulled 2026-07-11 (assembly method recorded with the '
                    'corpus register)',
         'locator': 'POST /api/v2/search/spending_by_award/, '
                    'psc_codes=[V225]; top 15 flagged for PIID lookup',
         'supplies': 'The federal award ladder: PIID, recipient, amount, '
                     'period, state for the largest V225 awards',
         'url': USASP_URL, 'tier': 'A', 'accessed': ctx['accessed'],
         'powers': ['Contract_Corpus']},
        {'key': 'ne_dhhs_camelot', 'publisher': 'State of Nebraska DHHS '
                                                '(statecontracts.nebraska.'
                                                'gov)',
         'document': 'Executed services contract 104886-O4 with Camelot '
                     'Transportation Inc, client transportation, with '
                     'rate attachments (Revised July 1, 2025)',
         'vintage': 'Original term 2023-07-01; Renewal 1 effective '
                    '2025-07-01',
         'locator': 'Rate attachment: USD 39.02 per one-way trip or USD '
                    '2.00 per mile, whichever is greater, wholly within '
                    'Douglas and Sarpy counties; local copy '
                    'pdfs/ne_camelot_104886_0.pdf',
         'supplies': 'The one fully stated per-trip rate schedule in the '
                     'corpus (non-ambulance client transport; scope note '
                     'carried in-row)',
         'url': 'https://statecontracts.nebraska.gov/ (contract '
                '104886-O4; download links session-tokenized)',
         'tier': 'A', 'accessed': ctx['accessed'],
         'powers': ['Contract_Corpus']},
        {'key': 'charlescity_amr_2023', 'publisher': 'City of Charles '
                                                     'City / Floyd '
                                                     'County, Iowa',
         'document': 'Executed ambulance services agreement (renewal) '
                     'with American Medical Response (TEK Inc. dba AMR), '
                     'council packet approved June 14, 2023',
         'vintage': 'Term 2023-07-01 through 2026-06-30',
         'locator': 'Agency Contribution schedule: USD 415,000 / 427,450 '
                    '/ 440,273 (3% annual steps); one 24-hour ALS unit '
                    'plus one 24-hour on-call BLS unit; local copy '
                    'pdfs/charlescity_amr_2023.pdf',
         'supplies': 'A fully priced dedicated-unit + subsidy contract '
                     'with a stated escalator and a hospital contribution',
         'url': 'https://www.cityofcharlescity.org/AgendaCenter/ViewFile/'
                'Item/7503?fileID=4667',
         'tier': 'A', 'accessed': ctx['accessed'],
         'powers': ['Contract_Corpus']},
        {'key': 'nh_pridestar_2024', 'publisher': 'Towns of Atkinson, '
                                                  'Danville, Hampstead, '
                                                  'Newton and Sandown, NH',
         'document': 'Executed multi-town ambulance services agreement '
                     'with Pridestar EMS Inc., commencing March 1, 2024 '
                     '(posted on the Town of Plaistow document center '
                     'under a legacy Trinity label)',
         'vintage': 'Twelve months from 2024-03-01; one two-year renewal '
                    'option with built-in escalator',
         'locator': 'Subsidy paragraph: USD 650,000 per year paid '
                    'quarterly (USD 32,500 per town per quarter); renewal '
                    'escalator 2.5%: USD 666,250 then USD 682,906.25; '
                    'local copy pdfs/plaistow_trinity_2024.pdf',
         'supplies': 'The second dedicated-unit + subsidy observation: '
                     'two dedicated ALS ambulances around the clock',
         'url': 'https://www.plaistow.com/DocumentCenter/View/523/'
                'Trinity-Contract-for-other-Towns_Begins-March-2024-PDF',
         'tier': 'A', 'accessed': ctx['accessed'],
         'powers': ['Contract_Corpus']},
    ]

    # -------------------------------------------------------------- facts
    facts += [
        {'metric': 'Public contract documents abstracted on the 6.4 field '
                   'schema (E.2 corpus)', 'year': 2026, 'value': 12,
         'unit': 'documents', 'basis': 'GOV', 'tier': 'A',
         'source_keys': ['contract_corpus_register'],
         'locator': 'Contract_Corpus Panel A, one row per document',
         'lives_on': 'Contract_Corpus',
         'cross_check': 'Convenience sample of PUBLIC contracts; 11 '
                        'further items parked with blockers on Panel D; '
                        'private facility-to-operator agreements are not '
                        'public records'},
        {'metric': 'USAspending PSC V225 award records pulled '
                   '(FY2023-FY2025 activity window, top by amount)',
         'year': 2025, 'value': 300, 'unit': 'award records',
         'basis': 'GOV', 'tier': 'A', 'source_keys': ['usasp_v225_awards'],
         'locator': 'spending_by_award, psc V225, types A-D, 3 pages x '
                    '100, sorted by award amount',
         'lives_on': 'Contract_Corpus',
         'cross_check': f'{n_va_dept} of 300 are Department of Veterans '
                        'Affairs; top 15 flagged for PIID document '
                        'lookup, blocked at SAM.gov (Panel D row 1)'},
        {'metric': 'Fixed annual escalator observed in the corpus, low '
                   'end (five-town NH Pridestar agreement, renewal-term '
                   'built-in)', 'year': 2024, 'value': 0.025,
         'unit': 'share per year', 'basis': 'GOV', 'tier': 'A',
         'source_keys': ['nh_pridestar_2024'],
         'locator': 'Agreement renewal clause: USD 650,000 to USD 666,250 '
                    'to USD 682,906.25 as printed',
         'lives_on': 'Contract_Corpus',
         'cross_check': 'High end 3.0% (Charles City IA); range is live '
                        'MIN/MAX on Panel C over n=2 documents'},
        {'metric': 'Fixed annual escalator observed in the corpus, high '
                   'end (Charles City IA / Floyd County AMR agreement)',
         'year': 2023, 'value': 0.03, 'unit': 'share per year',
         'basis': 'GOV', 'tier': 'A',
         'source_keys': ['charlescity_amr_2023'],
         'locator': 'Agency Contribution schedule: USD 415,000 to USD '
                    '427,450 to USD 440,273',
         'lives_on': 'Contract_Corpus',
         'cross_check': 'Low end 2.5% (NH Pridestar renewal); n=2, an '
                        'observed range, not a market distribution'},
        {'metric': 'Dedicated-unit annual subsidy, five-town NH system '
                   '(two dedicated ALS ambulances around the clock, '
                   'Pridestar EMS)', 'year': 2024, 'value': 650000,
         'unit': 'USD per year', 'basis': 'GOV', 'tier': 'A',
         'source_keys': ['nh_pridestar_2024'],
         'locator': 'Subsidy paragraph: USD 32,500 per town per quarter, '
                    'five towns',
         'lives_on': 'Contract_Corpus',
         'cross_check': 'USD 130,000 per town per year; operator bills '
                        'patients for EMS in addition'},
        {'metric': 'Dedicated-unit annual subsidy, Charles City IA / '
                   'Floyd County (one 24-hour ALS unit plus one 24-hour '
                   'on-call BLS unit, AMR), Year 1', 'year': 2023,
         'value': 415000, 'unit': 'USD per year', 'basis': 'GOV',
         'tier': 'A', 'source_keys': ['charlescity_amr_2023'],
         'locator': 'Agency Contribution: Year 1 USD 415,000, split 50/50 '
                    'city and county',
         'lives_on': 'Contract_Corpus',
         'cross_check': 'Rises to USD 440,273 by Year 3; Floyd County '
                        'Medical Center pledged USD 100,000 toward year '
                        'one - a facility co-paying for ambulance '
                        'capacity in a public document'},
        {'metric': 'Per-trip rate observed, Nebraska DHHS client '
                   'transport, Douglas and Sarpy counties (Camelot '
                   'Transportation contract 104886-O4)', 'year': 2025,
         'value': 39.02, 'unit': 'USD per one-way trip (or USD 2.00 per '
                                 'mile, whichever is greater), as the '
                                 'rate attachment states',
         'basis': 'GOV', 'tier': 'A', 'source_keys': ['ne_dhhs_camelot'],
         'locator': 'Rate attachment Revised July 1, 2025; wholly within '
                    'Douglas and Sarpy counties',
         'lives_on': 'Contract_Corpus',
         'cross_check': 'SCOPE: a state NON-AMBULANCE client-transport '
                        '(NEMT-adjacent) rate under a child-welfare / '
                        'client transportation contract - NOT an '
                        'ambulance rate; recorded exactly as the '
                        'document states, scope note in-row'},
    ]

    # ----------------------------------------------------------- findings
    findings += [
        {'id_hint': 89,
         'finding': 'The observed public structure mix: governments '
                    'predominantly buy ambulance service by granting '
                    'operating authority and letting the operator bill '
                    'patients (5 of 12 corpus documents are franchise / '
                    'EOA instruments), while capacity purchases show up '
                    'as dedicated-unit + subsidy contracts (2 of 12, USD '
                    '415,000-650,000 per year for 24-hour ALS units); '
                    'fully stated per-trip rate schedules appear only in '
                    'state client-transport contracting, not in the '
                    'municipal ambulance documents.',
         'numbers': f"='Contract_Corpus'!B{c_tot}",
         'sources': 'contract_corpus_register; charlescity_amr_2023; '
                    'nh_pridestar_2024',
         'confidence': 'High that each document says what Panel A '
                       'records; the MIX is a property of a 12-document '
                       'convenience sample',
         'guardrail': 'Public contracts only, government buyers '
                      'overrepresented by construction; private '
                      'facility-to-operator agreements are not public '
                      'records, so this mix cannot be read as the '
                      'facility-market mix.'},
        {'id_hint': 90,
         'finding': 'Where public ambulance contracts state a fixed '
                    'annual escalator it runs 2.5-3.0% (n=2, live range '
                    'on Panel C), and interfacility legs carry their own '
                    'SLAs in public documents: Sioux Falls holds the '
                    'contractor to a paramedic ambulance within 30 '
                    'minutes of requested pickup for scheduled '
                    'interfacility transfers (90% standard) with a '
                    '90-minute goal for unscheduled ones, and Benton AR '
                    'sets hospital-transfer response standards of 30 '
                    'minutes emergent / 60 minutes non-emergent.',
         'numbers': f"='Contract_Corpus'!G{esc_row}",
         'sources': 'contract_corpus_register; charlescity_amr_2023; '
                    'nh_pridestar_2024',
         'confidence': 'High on document text; n=2 on escalators, n=2 on '
                       'interfacility SLA documents',
         'guardrail': 'Two-document ranges are observed ends, not a '
                      'distribution; the SLA figures are 911-system '
                      'contract clauses about interfacility legs, not '
                      'terms of any private facility agreement.'},
    ]
    return {'panelA': (a0, a1), 'esc_row': esc_row, 'sub_row': sub_row,
            'parked': (d0, d1)}


# ======================================================================
# Tab 2: Cohort_990_Contractors (E.3)
# ======================================================================
def _build_cohort_tab(wb, ctx, cohort, sources, facts, findings):
    lib = ctx['lib']
    systems = cohort['systems']

    # per-system aggregation, computed from the register (never typed)
    agg = []
    for s in systems:
        eins = s['eins']
        parsed = [f for e in eins for f in e['filings']
                  if isinstance(f.get('contractors_gt100k_count'), int)]
        blocked = [f for e in eins for f in e['filings']
                   if not isinstance(f.get('contractors_gt100k_count'),
                                     int)]
        counts = [f['contractors_gt100k_count'] for f in parsed]
        transport = sum(len(f.get('transport_contractors') or [])
                        for f in parsed)
        agg.append({'system': _clean(s['system']), 'eins': len(eins),
                    'parsed': len(parsed), 'blocked': len(blocked),
                    'cmin': min(counts) if counts else None,
                    'cmax': max(counts) if counts else None,
                    'transport': transport,
                    'note': _clean(s.get('disambiguation_notes')) or '',
                    'raw': s})
    n_sys = len(agg)
    n_eins = sum(a['eins'] for a in agg)
    n_parsed = sum(a['parsed'] for a in agg)
    n_blocked = sum(a['blocked'] for a in agg)
    n_transport = sum(a['transport'] for a in agg)
    zero_disclosure = sum(
        1 for a in agg for e in a['raw']['eins'] for f in e['filings']
        if f.get('contractors_gt100k_count') == 0
        and not (f.get('all_contractors') or []))

    short_note = {
        'Cleveland Clinic (OH)':
            'Group return 91-2153073 consolidates subordinate hospitals; '
            'East Region EIN parked (no e-file XML posted)',
        'Inova Health System (VA)':
            'Operating filer discloses the large contractor counts; '
            'foundation filer discloses 13-15',
        'CommonSpirit Health / CHI Health (NE)':
            'CHI Nebraska filings disclose no Section B contractors; 3 '
            'newest-season filings XML-blocked (parked)',
        'Nebraska Methodist Health System (Omaha NE)': '',
        'Premier Health (Dayton OH)':
            'Miami Valley Hospital filings disclose no Section B '
            'contractors',
        "Saint Luke's Health System (Kansas City MO)":
            'Affiliated with BJC Health System since 2024 per registry '
            'note; BJC-side EINs not swept',
        'Froedtert Health (WI)':
            'Flagship hospital filings disclose no Section B '
            'contractors; 2 newest-season filings XML-blocked',
        'Baptist Health (Kentucky/Indiana)':
            'EIN selected under the disambiguation rule in Panel C',
        'Ascension (multi-state)':
            '6 newest-season filings XML-blocked; Illinois hospitals '
            'file under legacy EINs, not swept',
    }

    widths = [34, 12, 12, 13, 13, 13, 15, 58]
    ws = wb.create_sheet('Cohort_990_Contractors')
    sb = lib.SheetBuilder(ws, len(widths), col_widths=widths,
                          tab_color='FF8C1D40')
    rr = _Rows(sb, widths)

    sb.title('Cohort Form 990 contractor sweep: what the five-contractor '
             'disclosure window shows, and what it cannot')
    sb.subtitle(f'The question: do ambulance / EMS / medical-transport '
                f'vendors appear among the five highest-paid independent '
                f'contractors disclosed on the public Form 990 filings of '
                f'the {COHORT_FRAME}? Sources: IRS e-file 990 XML (Part '
                f'VII Section B) resolved and fetched via ProPublica '
                f'Nonprofit Explorer, latest two XML-available filings '
                f'per EIN; {n_sys} systems, {n_eins} EINs, {n_parsed} '
                f'filings parsed. Join keys: EIN to filing object_id. '
                f'The 990s are PUBLIC filings: system names appear here '
                f'strictly as filers of public documents.', height=52)
    sb.note('DATA QUALITY: Form 990 Part VII Section B discloses ONLY '
            'the five highest-paid independent contractors receiving '
            'more than $100,000, so everything below each fifth slot is '
            'invisible by form design (Panel B). Latest two XML-available '
            'filings per EIN only; the newest filing season is '
            'XML-blocked for 11 filings (parked in-table, Panel C '
            'status). Group returns consolidate subordinate entities, so '
            'contractor books are not hospital-specific. Six filings '
            'across three filers disclose no Section B contractors at '
            'all. Transport matching is a keyword screen on the '
            'disclosed name and services strings (regex recorded in the '
            'Panel B note); a vendor whose disclosed strings name '
            'neither the company nor the service would be missed even '
            'inside a top five. Entries recorded verbatim from filings; '
            'no inference beyond the filing text.', height=62)
    sb.blank()

    # ---------------------------------------------------------- Panel A
    sb.banner('Panel A. Per cohort system: EINs, parsed filings, and the '
              'contractor counts around the five-slot window')
    sb.headers(['Cohort system (public Form 990 filers)', 'EINs resolved',
                'Filings parsed (XML)', 'Newest filings XML-blocked',
                'Contractors over $100K per filing - min',
                'Contractors over $100K per filing - max',
                'Transport contractors in disclosed top five', 'Note'])
    a0 = sb.r + 1
    for a in agg:
        rr.emit([(a['system'], 'src'),
                 (a['eins'], 'src', lib.FMT_INT),
                 (a['parsed'], 'src', lib.FMT_INT),
                 (a['blocked'], 'src', lib.FMT_INT),
                 (a['cmin'], 'src', lib.FMT_INT),
                 (a['cmax'], 'src', lib.FMT_INT),
                 (a['transport'], 'src', lib.FMT_INT),
                 ((short_note.get(a['system'], '') or '-'), 'note')])
    a1 = sb.r
    tot = sb.r + 1
    sb.row([(f'Total ({n_sys} systems)', 'label'),
            (f'=SUM(B{a0}:B{a1})', 'fml', lib.FMT_INT),
            (f'=SUM(C{a0}:C{a1})', 'fml', lib.FMT_INT),
            (f'=SUM(D{a0}:D{a1})', 'fml', lib.FMT_INT),
            (f'=MIN(E{a0}:E{a1})', 'fml', lib.FMT_INT),
            (f'=MAX(F{a0}:F{a1})', 'fml', lib.FMT_INT),
            (f'=SUM(G{a0}:G{a1})', 'fml', lib.FMT_INT),
            ('Transport column: zero matches across every parsed filing; '
             'the - rendering IS the honest zero (house zero format)',
             'note')], wrap=True, height=24)
    sb.note('Min of 0 in column E reflects filings that disclose no '
            'Section B contractors at all (six filings across CHI '
            'Nebraska, Miami Valley Hospital and Froedtert Memorial '
            'Lutheran Hospital); the hospital-operating filers disclose '
            'from 11 to 840 contractors over $100K per filing.')
    sb.blank()

    # ---------------------------------------------------------- Panel B
    sb.banner('Panel B. The information floor, stated plainly: what the '
              'five-contractor window can and cannot show')
    sb.headers(['Quantity', 'Value', '', '', '', '', '', 'Basis'])
    b0 = sb.r + 1
    sb.row([('Filings parsed (latest two XML-available per EIN)', 'text'),
            (f'=C{tot}', 'fml', lib.FMT_INT), None, None, None, None,
            None, ('live from Panel A', 'note')])
    sb.row([('Independent contractors disclosed per filing (form '
             'design)', 'text'), (5, 'src', lib.FMT_INT), None, None,
            None, None, None,
            ('IRS Form 990, Part VII, Section B: the five highest-paid '
             'contractors receiving more than $100,000', 'note')])
    sb.row([('Contractors over $100K at the largest parsed filing (max '
             'observed)', 'text'), (f'=F{tot}', 'fml', lib.FMT_INT),
            None, None, None, None, None,
            ('CntrctRcvdGreaterThan100KCnt, as filed', 'note')])
    inv_row = sb.r + 1
    sb.row([('Contractors invisible below the fifth slot at that filer',
             'text'), (f'=F{tot}-5', 'fml', lib.FMT_INT), None, None,
            None, None, None, ('live arithmetic', 'note')])
    zero_row = sb.r + 1
    sb.row([('Transport-matching contractors among ALL disclosed top '
             'fives', 'text'), (f'=G{tot}', 'fml', lib.FMT_INT), None,
            None, None, None, None,
            ('renders - because the value is zero (house zero format)',
             'note')])
    sb.note('Transport keyword screen applied to disclosed name and '
            'services strings: ambulance, medical transport, patient '
            'transport, EMS, emergency medical, air medical, life '
            'flight, medevac, paramedic, ambulette, NEMT, critical care '
            'transport, mobile intensive care, and named operators '
            '(regex recorded in cohort_990.json).')
    sb.prose('Stated plainly: THIS SWEEP BOUNDS NOTHING. Part VII '
             'Section B discloses only the five highest-paid '
             'contractors over $100,000. The parsed filings disclose up '
             'to 840 contractors over $100,000 at a single filer, so a '
             'transport vendor billing below each filer\'s fifth-highest '
             'contractor - at these systems, slots held by nine-figure '
             'staffing and eight-figure construction vendors - is '
             'invisible by form design. The only measured statement this '
             'sweep supports is the information floor itself: transport '
             'contracts did not crack the top five at these filers in '
             'the parsed years. It is NOT an upper bound on transport '
             'spend, NOT evidence that such contracts are absent, and '
             'NOT a statement about any specific vendor relationship.')
    sb.blank()

    # ---------------------------------------------------------- Panel C
    sb.banner('Panel C. EIN registry and the Baptist disambiguation rule '
              '(public registry facts)')
    baptist = next(a for a in agg
                   if a['system'].startswith('Baptist Health'))
    sb.prose(baptist['note'], kind='text')
    sb.blank()
    sb.headers(['Filer (as registered)', 'EIN', 'Tax years parsed',
                'Status', '', '', '', 'System / disambiguation note '
                '(public registry facts)'])
    c0 = sb.r + 1
    for a in agg:
        note = a['note']
        if a['system'].startswith('Baptist Health'):
            note = 'Rule stated in full above this table.'
        rr.emit([(a['system'], 'label'), None, None, None, None, None,
                 None, ((note or '-'), 'note')])
        for e in a['raw']['eins']:
            ein = f"{e['ein']:09d}"
            ein_fmt = f'{ein[:2]}-{ein[2:]}'
            yrs = sorted({str(f['tax_year']) for f in e['filings']
                          if f.get('tax_year')}, reverse=True)
            n_p = sum(1 for f in e['filings']
                      if isinstance(f.get('contractors_gt100k_count'),
                                    int))
            n_b = len(e['filings']) - n_p
            if not e['filings']:
                status = 'no e-file XML posted; parked'
            elif n_b:
                status = (f'{n_p} parsed; {n_b} newest-season XML-blocked '
                          f'(parked)')
            else:
                status = f'{n_p} parsed'
            rr.emit([('    ' + _clean(e['name']), 'src'),
                     (ein_fmt, 'src'),
                     ((', '.join(yrs) or '-'), 'src'),
                     (status, 'note'), None, None, None,
                     ((_clean(e.get('note')) or None, 'note')
                      if e.get('note') else None)])
    c1 = sb.r
    sb.blank()

    sb.banner('Read panel')
    sb.prose(f'What is measured: across the {COHORT_FRAME}, {n_eins} '
             f'EINs were resolved from the public registry and '
             f'{n_parsed} Form 990 filings (latest two XML-available per '
             f'EIN, tax years 2022-2024) were parsed; zero of the '
             f'disclosed five-highest-paid contractors at any filer '
             f'matched ambulance / EMS / medical-transport keywords. '
             f'What that means - and all it means: at multi-billion-'
             f'dollar systems whose top-five slots are occupied by '
             f'nine-figure staffing and eight-figure construction and IT '
             f'vendors, the Form 990 disclosure window is too coarse to '
             f'see transport spend. The result is the information floor, '
             f'not a bound: with hundreds of contractors over $100,000 '
             f'per filer undisclosed, a transport vendor of any '
             f'plausible size fits under the window. The measured, '
             f'neutral statement stands alone: transport contracts did '
             f'not crack the top five at these filers in the parsed '
             f'years.')

    lib.add_chart(ws, f'A{sb.r + 2}',
                  'Contractors over $100K at the largest parsed filing '
                  'per system (5 are disclosed)',
                  f"'Cohort_990_Contractors'!$A${a0}:$A${a1}",
                  [('Contractors over $100K (max filing)',
                    f"'Cohort_990_Contractors'!$F${a0}:$F${a1}")],
                  kind='bar', y_fmt='#,##0')

    # ------------------------------------------------------------ sources
    sources += [
        {'key': 'irs990_partvii_sweep',
         'publisher': 'IRS (e-file Form 990 XML) via ProPublica Nonprofit '
                      'Explorer',
         'document': f'Form 990 Part VII Section B '
                     f'(ContractorCompensationGrp, '
                     f'CntrctRcvdGreaterThan100KCnt) parsed from IRS '
                     f'e-file XML for {n_parsed} filings across '
                     f'{n_eins} EINs, latest two XML-available filings '
                     f'per EIN (cohort_990.json, assembled 2026-07-11)',
         'vintage': 'Tax years 2022-2024 as available per filer',
         'locator': 'Per-filing object_id recorded in the register; '
                    'download-xml?object_id=... per filing',
         'supplies': 'The disclosed five-highest-paid contractor names, '
                     'services and amounts per filer, and the count of '
                     'contractors over $100K (the information floor)',
         'url': 'https://projects.propublica.org/nonprofits/',
         'tier': 'A', 'accessed': ctx['accessed'],
         'powers': ['Cohort_990_Contractors']},
        {'key': 'propublica_ein_registry',
         'publisher': 'ProPublica Nonprofit Explorer (IRS registry '
                      'mirror)',
         'document': 'Nonprofit Explorer API v2 organization search used '
                     'to resolve cohort systems to filing EINs, with '
                     'per-system disambiguation notes recorded on '
                     'Cohort_990_Contractors Panel C',
         'vintage': 'Registry as of 2026-07-11',
         'locator': 'Panel C EIN table; Baptist disambiguation rule '
                    'stated in full above the table',
         'supplies': 'The system-to-EIN mapping (analyst-selected from '
                     'public registry facts) and the exclusion rules',
         'url': 'https://projects.propublica.org/nonprofits/api',
         'tier': 'B', 'accessed': ctx['accessed'],
         'powers': ['Cohort_990_Contractors']},
    ]

    # -------------------------------------------------------------- facts
    facts += [
        {'metric': 'Cohort systems resolved to public Form 990 filers',
         'year': 2026, 'value': n_sys, 'unit': 'health systems (research '
         'cohort, public filings)', 'basis': 'GOV', 'tier': 'B',
         'source_keys': ['propublica_ein_registry'],
         'locator': 'Cohort_990_Contractors Panel C EIN table',
         'lives_on': 'Cohort_990_Contractors',
         'cross_check': f'{n_eins} EINs resolved; 23 with parsed XML; '
                        'Cleveland Clinic East Region EIN parked with no '
                        'e-file XML posted; mapping is analyst-selected '
                        'from public registry facts (tier B)'},
        {'metric': 'Form 990 filings parsed for Part VII Section B '
                   'contractors', 'year': 2024, 'value': n_parsed,
         'unit': 'filings (latest two XML-available per EIN, tax years '
                 '2022-2024)', 'basis': 'GOV', 'tier': 'A',
         'source_keys': ['irs990_partvii_sweep'],
         'locator': 'Per-filing object_id in the register; per-system '
                    'counts on Panel A',
         'lives_on': 'Cohort_990_Contractors',
         'cross_check': f'{n_blocked} newest-season filings XML-blocked '
                        f'(parked in-table); {zero_disclosure} parsed '
                        'filings disclose no Section B contractors at '
                        'all'},
        {'metric': 'Transport-matching contractors among the disclosed '
                   'five-highest-paid contractors, all parsed cohort '
                   'filings', 'year': 2024, 'value': n_transport,
         'unit': 'contractors (zero; stated as the information floor, '
                 'not a bound)', 'basis': 'GOV', 'tier': 'A',
         'source_keys': ['irs990_partvii_sweep'],
         'locator': 'Panel A column G (live SUM in the total row); '
                    'keyword regex in the Panel B note',
         'lives_on': 'Cohort_990_Contractors',
         'cross_check': 'Part VII Section B discloses only the top '
                        'five contractors over $100K; with up to 840 '
                        'contractors over $100K per filer, absence from '
                        'the top five is NOT evidence of absence of '
                        'spend'},
    ]

    # ----------------------------------------------------------- findings
    findings.append({
        'id_hint': 91,
        'finding': 'NEUTRAL information-floor result: across 46 parsed '
                   'cohort Form 990 filings, zero transport vendors '
                   'appear among the disclosed five-highest-paid '
                   'contractors - and the disclosure window is too '
                   'coarse for that to mean anything about transport '
                   'spend at multi-billion-dollar systems, because the '
                   'form discloses only five contractors while the '
                   'largest parsed filer reports 840 contractors over '
                   '$100,000. The measured statement is the floor '
                   'itself: transport contracts did not crack the top '
                   'five at these filers in the parsed years.',
        'numbers': f"='Cohort_990_Contractors'!F{tot}",
        'sources': 'irs990_partvii_sweep; propublica_ein_registry',
        'confidence': 'High that the parsed filings disclose what Panel '
                      'A records; the neutrality is the point',
        'guardrail': 'Absence from the top five is NOT evidence of '
                     'absence of spend: everything below each fifth '
                     'slot is invisible by form design, and the keyword '
                     'screen sees only disclosed name/services strings. '
                     'No inference beyond the filing text; systems '
                     'appear solely as filers of public documents.'})
    return {'panelA': (a0, a1), 'total_row': tot, 'zero_row': zero_row}


def build(wb, ctx):
    scratch = os.path.dirname(ctx['cache'])
    corpus = json.load(open(os.path.join(scratch, 'contract_corpus.json')))
    cohort = json.load(open(os.path.join(scratch, 'cohort_990.json')))

    facts, sources, findings = [], [], []
    m1 = _build_corpus_tab(wb, ctx, corpus, sources, facts, findings)
    m2 = _build_cohort_tab(wb, ctx, cohort, sources, facts, findings)

    # Portability firewall: no non-retrievable local file paths in any source
    # citation. The retrievable public URL rides in each source's own url
    # field; a 'local copy pdfs/...' fragment in a locator/document only breaks
    # the reproducible-from-the-public-internet promise for a third-party
    # reader, so strip it from every source this module emits.
    for s in sources:
        for k in ('locator', 'document', 'vintage', 'supplies'):
            if s.get(k):
                s[k] = _strip_local(s[k]) or s[k]

    return {'facts': facts, 'sources': sources, 'excluded': [],
            'findings': findings,
            'meta': {'inputs': 'contract_corpus.json + cohort_990.json '
                               '(assembled 2026-07-11)',
                     'corpus_docs': len(corpus['public_contracts']),
                     'va_awards_pulled': len(corpus['va_awards']),
                     'parked_contract_items': len(corpus['parked']),
                     'cohort_systems': len(cohort['systems']),
                     'corpus_rows': m1['panelA'],
                     'cohort_rows': m2['panelA']}}
