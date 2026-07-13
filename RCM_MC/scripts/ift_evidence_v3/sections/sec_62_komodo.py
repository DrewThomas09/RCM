"""Run 6.5: Komodo_Linkage_Spec - how a Komodo Health engagement would link into
the IFT evidence model and which open questions it closes.

Komodo's Healthcare Map is an all-payer, closed-and-open claims asset. It is
LICENSED and commercial - it is NOT public and NOT reproducible - so it sits
OUTSIDE the study's public-source firewall as evidence. It enters this workbook
only as a named LINKAGE PLAN, exactly like the ResDAC receiving schema on
Institutional_Ambulance_Wedge: every Komodo-derived output cell is bordered
PENDING a Komodo engagement, and no Komodo-derived figure is asserted anywhere.
The only Komodo values printed are Komodo's own public marketing claims about the
Map's scale, labeled CLAIMED (tier C), cited to Komodo's public pages. The
public estimates already in the workbook - the ~581K institutional wedge, the
balance-billing rate pegs - stand until a Komodo engagement replaces them.
"""

SHEETS = [{'name': 'Komodo_Linkage_Spec',
           'question': 'If a Komodo Health data engagement were licensed, how '
                       'would it link to the IFT model and which open questions '
                       'would it close?'}]

ACC = '2026-07-13'
KH_MAP = 'https://www.komodohealth.com/product/healthcare-map/'
KH_90M = ('https://www.komodohealth.com/press/komodo-health-adds-90m-closed-'
          'lives-per-year-to-expansive-healthcare-map/')
KH_KPI = ('https://www.businesswire.com/news/home/20240612785633/en/Komodo-'
          'Health-Introduces-the-First-Integrated-Patient-Insurance-Dataset')

# (attribute, Komodo public claim, source url) - all CLAIMED (vendor materials)
WHAT = [
    ('Healthcare Map scale',
     '"more than 330 million" US patient lives; medical, clinical, lab and '
     'pharmacy encounters; "15 million new clinical encounters daily"', KH_MAP),
    ('Closed, linkable lives',
     '"160 million closed, linkable lives per year" - full longitudinal '
     'encounter history, spanning Medicare, Medicaid and commercial', KH_90M),
    ('Public + commercial payer coverage',
     '"over 100 million patients covered by Medicare, Medicare Advantage, and '
     'Medicaid," plus commercial health plans and self-insured employers',
     KH_MAP),
    ('Closed vs open claims',
     'closed patients = entire longitudinal history captured; open patients = '
     'portions captured - the closed set is the linkable, analyzable universe',
     KH_MAP),
    ('Komodo Patient Insurance (KPI)',
     'insurance status on "more than 200 million de-identified U.S. patient '
     'lives" - the payer/plan dimension behind the all-payer split', KH_KPI),
]

# The linkage keys: IFT model field -> Komodo dimension it joins on.
KEYS = [
    ('Provider (NPI)',
     'The resolved MMT estate NPIs and the top-30 participant NPIs already in '
     'the workbook join directly to Komodo\'s provider dimension',
     'MMT_NPI_Estate, NPPES resolution tabs'),
    ('Service (HCPCS + modifiers)',
     'Ground ambulance A0425-A0436, the QN/QM provider-of-services modifiers, '
     'and the origin-destination modifiers - the exact grain of the carrier '
     'cut', 'Modifier_QM_QN_Series, Medicare_IFT_Series'),
    ('Institutional grain (revenue centre + POS)',
     'Revenue centres 0540-0549 and place-of-service separate hospital-'
     'institutional ambulance from professional/carrier lines - the wedge grain',
     'Institutional_Ambulance_Wedge, Payment_Rules'),
    ('Payer / plan (KPI)',
     'The commercial / Medicare Advantage / Medicaid managed-care / Medicare '
     'FFS split per line - the all-payer dimension no public file carries',
     'Payer_Rates_Commercial, MRF_Attempt_Log'),
    ('Patient journey (encounter linkage)',
     'Closed-life longitudinal linkage ties a sending-facility encounter to an '
     'ambulance transport to a receiving-facility encounter - the actual IFT '
     'flow', 'Hub_Spoke_Map, transfer-corridor tabs'),
]

# What Komodo closes: each currently-PENDING / carrier-limited item -> the
# Komodo query that fills it. All outputs bordered PENDING.
CLOSES = [
    ('Commercial IFT rate (the MRF dead-end)',
     'Closed-claims paid and allowed amounts by ambulance HCPCS x commercial '
     'payer - the rate the Transparency-in-Coverage MRF attempt could not '
     'retrieve (MRF_Attempt_Log)'),
    ('All-payer IFT VOLUME (beyond the 11.3M Medicare book)',
     'Transport counts by HCPCS across ALL payers - the true addressable market '
     'size, not just the Medicare FFS slice the study is built on'),
    ('The institutional wedge, all-payer (beyond Medicare-only ResDAC)',
     'Institutional (rev 054x) versus professional ambulance lines across all '
     'payers - a direct, all-payer measurement of the wedge the top-down '
     'MedPAC-minus-carrier residual only estimates for Medicare'),
    ('Payer mix per operator (revenue quality)',
     'The Medicare / Medicare Advantage / Medicaid / commercial revenue split '
     'on the estate and participant NPIs - the payer-mix question a deal turns '
     'on, unanswerable from Medicare data alone'),
    ('Sending-to-receiving transfer flows (the real IFT network)',
     'Patient-journey linkage from origin facility to destination facility - '
     'the hub-and-spoke corridor map at the facility level, all payers'),
    ('Subject-company (MMT) all-payer book',
     'Volume, rate and payer mix on the resolved MMT estate NPIs across all '
     'payers - the actual book, replacing the Medicare-FFS-only view on '
     'MMT_Medicare_Book'),
]

# Receiving schema: Komodo extract field -> workbook exhibit it fills.
SCHEMA = [
    ('Rendering / billing NPI', 'operator identity + estate/participant match',
     'MMT_Medicare_Book, Insourcing_Bounds'),
    ('HCPCS + initial + second modifier', 'service level, O-D, QN/QM flag',
     'Modifier_QM_QN_Series'),
    ('Revenue centre (054x) + place of service', 'institutional vs professional',
     'Institutional_Ambulance_Wedge'),
    ('Payer type + plan (KPI)', 'all-payer split; commercial rate',
     'Payer_Rates_Commercial, MRF_Attempt_Log'),
    ('Allowed / paid amount', 'realized rate by payer', 'rate-evidence bridge'),
    ('Transport count / units', 'all-payer volume', 'TAM assembly, demand spine'),
    ('Origin + destination facility (journey)', 'IFT flow corridors',
     'Hub_Spoke_Map'),
    ('Service date', 'annual trajectory, seasonality', 'annual series tabs'),
]


def build(wb, ctx):
    lib = ctx['lib']
    accessed = ctx['accessed']
    facts, sources, excluded, findings = [], [], [], []

    sources += [
        {'key': 'komodo_public', 'publisher': 'Komodo Health (vendor public '
                                              'materials)',
         'document': 'Komodo Health Healthcare Map product page and press '
                     'releases describing the Map\'s scale, payer coverage and '
                     'the Komodo Patient Insurance dataset',
         'vintage': f'Pages as retrieved {ACC}',
         'locator': 'Per-claim URL printed in the Public source column of '
                    'Panel A; all figures are Komodo self-reported (CLAIMED)',
         'supplies': 'The scale claims on Panel A; the linkage plan asserts no '
                     'Komodo-derived measurement',
         'url': KH_MAP, 'tier': 'C', 'accessed': accessed,
         'powers': ['Komodo_Linkage_Spec']},
    ]

    ws = wb.create_sheet('Komodo_Linkage_Spec')
    sb = lib.SheetBuilder(ws, 10,
                          col_widths=[38, 50, 30, 4, 4, 4, 4, 4, 4, 30],
                          tab_color='FF6B7C93')
    sb.title('Komodo Health linkage: how a licensed all-payer engagement would '
             'plug into the IFT model')
    sb.subtitle('Komodo\'s Healthcare Map is an all-payer, closed-and-open '
                'claims asset - the single dataset that would close the '
                'questions the public files cannot: the commercial rate, '
                'all-payer volume, the institutional wedge across every payer, '
                'payer mix per operator, and the real sending-to-receiving '
                'transfer network. It is LICENSED and commercial, so it sits '
                'outside the study\'s public-source firewall as evidence and '
                'enters here only as a named linkage PLAN. Every Komodo output '
                'is bordered PENDING a Komodo engagement; no Komodo-derived '
                'figure is asserted. The only Komodo values shown are Komodo\'s '
                'own public scale claims, labeled CLAIMED and cited.')
    sb.note('DATA QUALITY: this is a linkage specification, not a data source. '
            'Nothing here measures the IFT market from Komodo - a Komodo '
            'engagement is a commercial contract and data license (a human '
            'action item), not a public pull. The public estimates already in '
            'the workbook - the ~581K institutional wedge, the balance-billing '
            'rate pegs, the Medicare-FFS book - stand until a Komodo extract '
            'replaces them. Komodo\'s scale figures are vendor marketing '
            '(CLAIMED, tier C), carried only to size what the engagement would '
            'reach, never as study evidence.')
    sb.blank()

    # ---------------------------------------------------------- Panel A ---
    sb.banner('Panel A. What Komodo is (Komodo public materials; CLAIMED)')
    sb.headers(['Attribute', 'Komodo public claim', 'Public source (retrieved '
                + ACC + ')', '', '', '', '', '', '', ''])
    for attr, claim, url in WHAT:
        sb.row([(attr, 'label'), (claim, 'text'), (url, 'note'),
                None, None, None, None, None, None, None], wrap=True, height=44)
    sb.blank()

    # ---------------------------------------------------------- Panel B ---
    sb.banner('Panel B. The linkage keys - how the IFT model joins to Komodo')
    sb.headers(['Linkage key', 'How it joins', 'Workbook anchor', '', '', '',
                '', '', '', ''])
    for key, how, anchor in KEYS:
        sb.row([(key, 'label'), (how, 'text'), (anchor, 'text'),
                None, None, None, None, None, None, None], wrap=True, height=44)
    sb.blank()

    # ---------------------------------------------------------- Panel C ---
    sb.banner('Panel C. What Komodo closes - each open question and the query '
              'that fills it (outputs PENDING)')
    sb.headers(['Open question (current status)', 'Komodo query that closes it',
                'Output', '', '', '', '', '', '', 'Status'])
    for q, query in CLOSES:
        sb.row([(q, 'label'), (query, 'text'), ('PENDING', 'note'),
                None, None, None, None, None, None,
                ('Komodo engagement', 'note')], wrap=True, height=52)
    sb.blank()

    # ---------------------------------------------------------- Panel D ---
    sb.banner('Panel D. Receiving schema - the Komodo extract fields and the '
              'exhibit each fills (PENDING)')
    sb.headers(['Komodo field', 'What it resolves', 'Target exhibit',
                'Value', '', '', '', '', '', 'Status'])
    for field, resolves, target in SCHEMA:
        sb.row([(field, 'label'), (resolves, 'text'), (target, 'text'),
                ('PENDING', 'note'), None, None, None, None, None,
                ('on landing', 'note')], wrap=True, height=30)
    sb.blank()

    # ------------------------------------------------------- read panel ---
    sb.banner('Read panel')
    sb.prose(
        'One licensed dataset closes five of the study\'s hardest open '
        'questions at once. The public route hit real walls - the commercial '
        'rate is locked behind payer machine-readable files that would not '
        'retrieve, the institutional wedge is only estimable top-down from '
        'Medicare, all-payer volume and payer mix are invisible in Medicare '
        'data, and the actual facility-to-facility transfer network cannot be '
        'built from public claims. Komodo\'s Healthcare Map - all-payer, '
        'closed longitudinal lives, with the provider, HCPCS, revenue-centre, '
        'payer and patient-journey dimensions the model already keys on - '
        'answers every one of them: the commercial rate from closed claims, the '
        'all-payer market size, the institutional wedge measured rather than '
        'inferred, the payer mix a deal turns on, and the sending-to-receiving '
        'corridors from journey linkage. This tab is the plan for that '
        'engagement, not the engagement: it maps the join keys and the '
        'receiving schema so that on the day a Komodo extract lands the fills '
        'are mechanical. Until then nothing here is evidence - it is licensed, '
        'commercial, and outside the public-source firewall - and the workbook\'s '
        'public estimates stand.')

    # ------------------------------------------------------------ facts ---
    facts += [
        {'metric': 'Komodo Healthcare Map scale (vendor-claimed)', 'year': 2026,
         'value': 330000000, 'unit': 'US patient lives (CLAIMED)',
         'basis': 'CLAIMED', 'tier': 'C', 'source_keys': ['komodo_public'],
         'locator': 'Komodo_Linkage_Spec Panel A, Healthcare Map scale row',
         'lives_on': 'Komodo_Linkage_Spec',
         'cross_check': 'Vendor self-reported on komodohealth.com; carried to '
                        'size the engagement\'s reach, not as study evidence'},
        {'metric': 'Komodo closed, linkable lives per year (vendor-claimed)',
         'year': 2026, 'value': 160000000, 'unit': 'closed linkable lives '
         '(CLAIMED)', 'basis': 'CLAIMED', 'tier': 'C',
         'source_keys': ['komodo_public'],
         'locator': 'Komodo_Linkage_Spec Panel A, closed linkable lives row',
         'lives_on': 'Komodo_Linkage_Spec',
         'cross_check': 'Vendor self-reported; the closed set is the linkable '
                        'universe an IFT extract would draw from'},
    ]

    # --------------------------------------------------------- findings ---
    findings += [
        {'id_hint': 117,
         'finding': 'A single licensed dataset - Komodo Health\'s all-payer '
                    'Healthcare Map - would close five of the study\'s hardest '
                    'open questions at once: the commercial IFT rate (locked '
                    'behind the payer MRF wall), all-payer transport VOLUME '
                    '(invisible beyond the 11.3M Medicare book), the '
                    'institutional wedge measured rather than inferred, payer '
                    'mix per operator, and the real sending-to-receiving '
                    'transfer network from patient-journey linkage. The model '
                    'already keys on every join Komodo needs - NPI, HCPCS and '
                    'QN/QM modifiers, revenue centre 054x, payer, and encounter '
                    'linkage - so this tab ships the linkage keys and receiving '
                    'schema, PENDING the engagement.',
         'numbers': 'Linkage plan; Panel C maps 6 open items to Komodo queries, '
                    'all outputs PENDING',
         'sources': 'komodo_public',
         'confidence': 'High that Komodo closes these questions in principle; '
                       'no Komodo-derived figure is asserted',
         'guardrail': 'Licensed, commercial, non-reproducible - OUTSIDE the '
                      'public-source firewall as evidence. A linkage plan, not '
                      'a measurement; the engagement is a contract and data '
                      'license, and the public estimates stand until it lands. '
                      'Komodo scale figures are vendor marketing.'}]

    return {'facts': facts, 'sources': sources, 'excluded': excluded,
            'findings': findings, 'meta': {}}
