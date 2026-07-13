"""Run 5, Task 5.2: Payment_Rules - the SNF consolidated-billing wedge.

Under SNF consolidated billing, medically necessary ambulance transports of a
beneficiary in a covered Part A SNF stay are, with defined exceptions, bundled
into the SNF's prospective payment and billed by the SNF - so that volume never
generates an ambulance carrier claim. This is a rule-defined claims-invisibility
channel, parallel to the Part A inpatient bundling wedge already documented. No
magnitude is asserted here: the tab states the rule from primary sources, names
the exclusions (which DO appear as carrier claims, notably dialysis round trips),
and marks the bundled magnitude PENDING with the public dataset that would
measure it.
"""

SHEETS = [{'name': 'Payment_Rules',
           'question': 'Which Medicare payment rules make interfacility '
                       'ambulance volume invisible to carrier claims, and '
                       'which transports do still surface?'}]

# Primary-source URLs.
MANUAL6 = 'https://www.cms.gov/regulations-and-guidance/guidance/manuals/downloads/clm104c06.pdf'
CB_PAGE = ('https://www.cms.gov/medicare/coding-billing/skilled-nursing-'
           'facility-snf-consolidated-billing')
CFR_URL = 'https://www.ecfr.gov/current/title-42/part-411/section-411.15'
RAC0049 = ('https://www.cms.gov/research-statistics-data-and-systems/monitoring-'
           'programs/medicare-ffs-compliance-programs/recovery-audit-program/'
           'approved-rac-topics-items/0049-ambulance-snf-to-snf-transfer')


def build(wb, ctx):
    lib = ctx['lib']
    accessed = ctx['accessed']
    facts, sources, excluded, findings = [], [], [], []

    sources += [
        {'key': 'snfcb_manual', 'publisher': 'CMS',
         'document': 'Medicare Claims Processing Manual, Pub. 100-04, Chapter 6 '
                     '(SNF Inpatient Part A Billing and SNF Consolidated '
                     'Billing) and the CMS SNF Consolidated Billing program '
                     'page - the ambulance bundling rule and its exclusions',
         'vintage': 'Current manual chapter and program page at access date',
         'locator': 'Ch 6 ambulance consolidated-billing provisions; SNF CB '
                    'program page exclusion list',
         'supplies': 'The bundling rule and the exclusion list printed on '
                     'Panels A and B',
         'url': CB_PAGE, 'tier': 'A', 'accessed': accessed,
         'powers': ['Payment_Rules']},
        {'key': 'snfcb_law', 'publisher': 'US Code / Code of Federal '
                                          'Regulations',
         'document': 'Social Security Act 1888(e) (SNF prospective payment and '
                     'consolidated billing, added by the Balanced Budget Act '
                     'of 1997) and 42 CFR 411.15(p) / 409.27(c) (Part B '
                     'coverage exclusion for SNF residents; scope of the '
                     'ambulance benefit under the SNF stay)',
         'vintage': 'Current statute and regulation at access date',
         'locator': '42 CFR 411.15(p): services a SNF resident in a covered '
                    'stay may not have billed separately to Part B; '
                    '411.15(p)(3) defines resident',
         'supplies': 'The statutory and regulatory authority behind the rule '
                     'on Panel A',
         'url': CFR_URL, 'tier': 'A', 'accessed': accessed,
         'powers': ['Payment_Rules']},
    ]

    ws = wb.create_sheet('Payment_Rules')
    sb = lib.SheetBuilder(ws, 10,
                          col_widths=[34, 46, 18, 12, 12, 12, 12, 4, 4, 40],
                          tab_color='FF6B7C93')
    sb.title('Payment rules that make interfacility ambulance volume invisible '
             'to carrier claims: the SNF consolidated-billing wedge')
    sb.subtitle('Under SNF consolidated billing, a medically necessary '
                'ambulance transport of a beneficiary in a covered Part A SNF '
                'stay is bundled into the SNF prospective payment and billed by '
                'the SNF, not by the ambulance supplier - so it never generates '
                'a Part B ambulance carrier claim. A defined set of trips is '
                'excluded and stays separately billable, so those DO surface in '
                'claims - notably the dialysis round trips the ESRD channel '
                'already sees. This tab states the rule and its exclusions from '
                'primary sources; it asserts no magnitude, and marks the '
                'bundled volume PENDING with the dataset that would size it.')
    sb.note('DATA QUALITY: this is a RULE tab, not a measurement. It carries no '
            'transport count and asserts no share. The value here is naming a '
            'structural undercount channel precisely enough that no downstream '
            'exhibit mistakes carrier-claim ambulance volume for total '
            'interfacility volume. The bundled magnitude is genuinely '
            'unretrievable from public carrier files - it lives in SNF Part A '
            'institutional claims - so it is marked PENDING with the dataset '
            'named, never estimated.')
    sb.blank()

    # ---------------------------------------------------------- Panel A ---
    sb.banner('Panel A. The rule: ambulance during a covered Part A SNF stay is '
              'bundled and billed by the SNF')
    sb.headers(['Authority', 'What it says', 'Type', '', '', '', '', '', '',
                'Effect on carrier claims'])
    sb.row([('SSA 1888(e); 42 CFR 411.15(p)', 'label'),
            ('A beneficiary in a covered Part A SNF stay is a SNF "resident"; '
             'the services furnished during that stay - including medically '
             'necessary ambulance transport - are bundled into the SNF '
             'prospective payment and may not be billed separately to Part B.',
             'text'),
            ('Statute / regulation', 'text'), None, None, None, None, None,
            None,
            ('The transport is inside the SNF PPS payment, so no ambulance '
             'carrier claim exists', 'note')], wrap=True, height=58)
    sb.row([('Pub. 100-04 Ch. 6', 'label'),
            ('The consolidated-billing requirement confers on the SNF the '
             'billing responsibility for the whole package of care a resident '
             'receives during a covered Part A stay; ambulance is included '
             'except for the trips listed in Panel B.', 'text'),
            ('Operational manual', 'text'), None, None, None, None, None, None,
            ('SNF bills the transport on its Part A institutional claim, not '
             'the ambulance supplier', 'note')], wrap=True, height=48)
    sb.blank()

    # ---------------------------------------------------------- Panel B ---
    sb.banner('Panel B. The exclusions: transports that stay separately '
              'billable and DO appear in carrier claims')
    sb.headers(['Excluded transport', 'Rule', 'Appears in claims?', '', '', '',
                '', '', '', 'Note'])
    excl = [
        ('Ambulance TO the SNF for the initial admission',
         'Excluded from consolidated billing: the admission trip predates '
         'residency', 'Yes - carrier claim',
         'the leading edge of a SNF episode is visible'),
        ('Ambulance FROM the SNF at final discharge',
         'Excluded, EXCEPT when the trip is a transfer to another SNF (that '
         'stays bundled - RAC issue 0049 targets its improper unbundling)',
         'Yes, unless SNF-to-SNF',
         'discharge legs surface; SNF-to-SNF transfers do not'),
        ('Round trip offsite for Part B DIALYSIS at a renal dialysis facility',
         'Excluded: covered ambulance to obtain offsite dialysis is separately '
         'billable', 'Yes - carrier claim',
         'THE scope note the ESRD/dialysis channel needs: these trips ARE in '
         'the claims the dialysis work counts'),
        ('Round trip offsite for certain intensive or emergency outpatient '
         'hospital services',
         'Excluded: the high-cost outpatient categories on the CB exclusion '
         'list travel with their transport', 'Yes - carrier claim',
         'emergency and high-acuity outpatient legs surface'),
    ]
    for e in excl:
        sb.row([(e[0], 'text'), (e[1], 'text'), (e[2], 'label'),
                None, None, None, None, None, None, (e[3], 'note')],
               wrap=True, height=44)
    sb.note('Everything NOT on this list - the ordinary medically necessary '
            'ambulance trip of a resident during the covered stay - is bundled '
            'and invisible to carrier claims.')
    sb.blank()

    # ---------------------------------------------------------- Panel C ---
    sb.banner('Panel C. The claims-invisible wedge: the SNF-bundled component '
              '(magnitude PENDING; see Universe_Reconciliation)')
    sb.headers(['Wedge component', 'Mechanism', 'Magnitude', 'Measuring '
                'dataset (public)', '', '', '', '', '', 'Note'])
    sb.row([('SNF-bundled ambulance (Part A stay)', 'label'),
            ('Rule-defined: bundled into SNF PPS, billed by the SNF, absent '
             'from Part B carrier ambulance claims', 'text'),
            ('PENDING', 'note'),
            ('SNF Part A institutional claims ambulance revenue-center detail '
             '(revenue center 0540) via T-MSIS Analytic Files (TAF) or the CMS '
             'SNF claims PUF', 'text'),
            None, None, None, None, None,
            ('parallel to the Part A inpatient bundling wedge already in the '
             'reconciliation; no magnitude asserted', 'note')],
           wrap=True, height=58)
    sb.note('This component belongs on the five-universe reconciliation as a '
            'named driver of the gap between carrier-claim ambulance volume and '
            'total interfacility volume. Its size is genuinely not retrievable '
            'from any public carrier file, so it ships PENDING with the '
            'institutional-claims dataset named - never estimated, never '
            'assumed.')
    sb.blank()

    # ---------------------------------------------------------- Panel D ---
    sb.banner('Panel D. Cross-links: where this rule re-scopes existing tabs')
    sb.headers(['Tab', 'Scope note this rule adds', '', '', '', '', '', '', '',
                ''])
    xlinks = [
        ('SNF return-leg structure / quality',
         'Return legs DURING a covered Part A stay are bundled and invisible; '
         'the admission trip and the final-discharge leg (unless SNF-to-SNF) '
         'are separately billed and visible. A carrier-claims count of SNF '
         'return legs is therefore a floor on the true volume.'),
        ('Dialysis / ESRD channel',
         'The dialysis exclusion is why those round trips ARE in carrier '
         'claims: the ESRD channel counts real, separately-billed transports, '
         'not a bundled residual. This is the guardrail the dialysis findings '
         'need to avoid double-counting against the bundled wedge.'),
        ('Universe_Reconciliation',
         'The SNF-bundled component is a named driver of the claims-to-total '
         'wedge, PENDING for magnitude with the institutional-claims dataset '
         'named on Panel C.'),
    ]
    for t, note in xlinks:
        sb.row([(t, 'label'), (note, 'text'), None, None, None, None, None,
                None, None, None], wrap=True, height=52)
    sb.blank()

    # ------------------------------------------------------- read panel ---
    sb.banner('Read panel')
    sb.prose(
        'SNF consolidated billing is a second rule-defined invisibility channel '
        'beside inpatient bundling: for a beneficiary in a covered Part A SNF '
        'stay, the ordinary medically necessary ambulance trip is folded into '
        'the SNF prospective payment and billed by the SNF, so it never '
        'generates a Part B carrier claim and never enters the ambulance '
        'universe every claims-based exhibit is built from. The exclusions are '
        'the tell: admission and final-discharge legs, SNF-to-SNF transfers '
        'aside, and above all the offsite dialysis round trips remain '
        'separately billable and DO appear in claims - which is exactly why the '
        'ESRD channel can count them and why a carrier-claims tally of SNF '
        'return legs is a floor, not a total. No magnitude is asserted anywhere '
        'on this tab; the bundled volume lives in SNF Part A institutional '
        'claims, so it is marked PENDING with that dataset named. The point is '
        'scope discipline: no downstream exhibit should read carrier-claim '
        'ambulance volume as total interfacility volume when a whole rule-'
        'defined slice is bundled out of view.')

    # --------------------------------------------------------- findings ---
    findings += [
        {'id_hint': 110,
         'finding': 'SNF consolidated billing is a rule-defined claims-'
                    'invisibility channel for interfacility ambulance: during a '
                    'covered Part A SNF stay, the ordinary medically necessary '
                    'ambulance transport is bundled into the SNF prospective '
                    'payment and billed by the SNF, so it never appears as a '
                    'Part B ambulance carrier claim. The exclusions - admission '
                    'and final-discharge legs (except SNF-to-SNF transfers) and '
                    'offsite dialysis and intensive-outpatient round trips - '
                    'stay separately billable and DO surface, which is why the '
                    'dialysis channel counts real transports. Magnitude is not '
                    'asserted: the bundled volume is retrievable only from SNF '
                    'Part A institutional claims (T-MSIS TAF), so it ships '
                    'PENDING with that dataset named.',
         'numbers': 'Rule, not a magnitude: SSA 1888(e), 42 CFR 411.15(p), '
                    'Pub. 100-04 Ch. 6. Magnitude PENDING (Panel C).',
         'sources': 'snfcb_manual; snfcb_law',
         'confidence': 'High on the rule and its exclusions (primary sources); '
                       'no magnitude claimed',
         'guardrail': 'This names an undercount mechanism; it does not size it. '
                      'Do not infer a bundled volume from this tab, and do not '
                      'double-count the dialysis exclusion (which is visible in '
                      'claims) against the bundled residual.'}]

    return {'facts': facts, 'sources': sources, 'excluded': excluded,
            'findings': findings, 'meta': {}}
