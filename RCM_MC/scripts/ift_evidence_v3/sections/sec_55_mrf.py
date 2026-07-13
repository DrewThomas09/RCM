"""Run 5, Task 5.5(a): MRF_Attempt_Log - the commercial machine-readable-file
attempt, run to its standing hard stop and formally closed.

Three regional payers were probed for a machine-readable in-network rate file
(the Transparency in Coverage index), in the standing order. None yielded a
retrievable ground-ambulance rate: the index pages are bot-blocked or moved, and
the one reachable data host returns only a small index stub that gates the
multi-gigabyte rate files behind plan/EIN-specific paths not discoverable without
a licensed transparency feed. Per the standing recipe, the commercial-rate MRF
row is therefore CLOSED as PENDING with the three attempts logged, and the
interim commercial anchor falls back to the balance-billing statutory
benchmarks. No commercial rate is asserted.
"""

SHEETS = [{'name': 'MRF_Attempt_Log',
           'question': 'Did a public commercial machine-readable rate file for '
                       'ground ambulance land, and if not, what is the interim '
                       'anchor?'}]

# (payer, portal / index URL, probe result, failure mode)
ATTEMPTS = [
    ('Medica',
     'medica.com/member-support/transparency-in-coverage ; '
     'transparency-in-coverage.medica.com',
     'HTTP 403 on the portal; the MRF subdomain did not resolve (connection '
     'failed)',
     'Portal bot-blocked (403); no machine-readable index reachable without a '
     'licensed feed'),
    ('Blue Cross Blue Shield of Nebraska',
     'nebraskablue.com/en/Legal/Transparency-in-Coverage ; '
     'mrfdata.hmhs.com (Highmark-hosted)',
     'HTTP 404 on the transparency page; the data host returned HTTP 200 but '
     'only a ~2.5 KB index stub',
     'Index stub gates the multi-gigabyte in-network rate files behind '
     'plan/EIN-specific paths not machine-discoverable'),
    ('Wellmark (Iowa)',
     'wellmark.com/transparency-in-coverage',
     'HTTP 403 on the portal',
     'Portal bot-blocked (403); no machine-readable index reachable without a '
     'licensed feed'),
]


def build(wb, ctx):
    lib = ctx['lib']
    accessed = ctx['accessed']
    facts, sources, excluded, findings = [], [], [], []

    sources += [
        {'key': 'mrf_attempts', 'publisher': 'Regional health plans '
                                             '(Transparency in Coverage)',
         'document': 'Machine-readable-file transparency portals for Medica, '
                     'Blue Cross Blue Shield of Nebraska and Wellmark, probed '
                     'for a retrievable in-network ground-ambulance rate file',
         'vintage': f'Probed {accessed}',
         'locator': 'Portal / index URLs and HTTP results printed on Panel A',
         'supplies': 'The attempt log and the PENDING closure on this tab',
         'url': 'https://www.cms.gov/marketplace/about/oversight/other-'
                'insurance-protections/transparency-in-coverage-rule',
         'tier': 'A', 'accessed': accessed, 'powers': ['MRF_Attempt_Log']},
    ]

    ws = wb.create_sheet('MRF_Attempt_Log')
    sb = lib.SheetBuilder(ws, 10,
                          col_widths=[30, 44, 34, 40, 4, 4, 4, 4, 4, 4],
                          tab_color='FF6B7C93')
    sb.title('Commercial machine-readable rate file: the attempt, logged and '
             'formally closed')
    sb.subtitle('The commercial ground-ambulance rate has one remaining public '
                'path - a payer machine-readable file (MRF) under the '
                'Transparency in Coverage rule. Three regional payers were '
                'probed in the standing order (Medica, Blue Cross Blue Shield '
                'of Nebraska, Wellmark Iowa). None yielded a retrievable ground-'
                'ambulance rate. Per the standing recipe this closes the MRF '
                'row: it is marked PENDING with the three attempts logged '
                'below, and the interim commercial anchor falls back to the '
                'balance-billing statutory benchmarks. No commercial rate is '
                'asserted anywhere from this attempt.')
    sb.note('DATA QUALITY: MRF files are technically public but are multi-'
            'gigabyte, plan- and EIN-partitioned, and gated behind index paths '
            'that are not machine-discoverable without a licensed transparency '
            'feed or heavy scraping through bot walls. That is a retrieval '
            'barrier, not a data gap we can paper over - so the row is PENDING '
            'with the dataset named, never estimated.')
    sb.blank()

    # ---------------------------------------------------------- Panel A ---
    sb.banner('Panel A. The three logged attempts (' + accessed + ')')
    sb.headers(['Payer', 'Portal / index URL probed', 'Probe result',
                'Failure mode', '', '', '', '', '', ''])
    for a in ATTEMPTS:
        payer, url, res, mode = a
        sb.row([(payer, 'label'), (url, 'text'), (res, 'text'), (mode, 'text'),
                None, None, None, None, None, None], wrap=True, height=52)
    sb.blank()

    # ---------------------------------------------------------- Panel B ---
    sb.banner('Panel B. The closure and the interim anchor')
    sb.headers(['Item', 'Status', 'Detail', '', '', '', '', '', '', ''])
    sb.row([('Commercial ground-ambulance MRF rate', 'label'),
            ('PENDING', 'note'),
            ('Retrievable only from a licensed Transparency-in-Coverage feed or '
             'a payer-published machine-readable index that resolves to the '
             'in-network rate file; three public attempts failed (Panel A)',
             'text'),
            None, None, None, None, None, None, None], wrap=True, height=44)
    sb.row([('Interim commercial anchor', 'label'),
            ('Fallback', 'text'),
            ('The balance-billing statutory benchmarks (state ground-ambulance '
             'out-of-network payment standards and the No Surprises Act '
             'framework) stand as the interim commercial anchor on the rate-'
             'evidence bridge until a licensed MRF feed replaces them; those '
             'pegs are carried on the commercial-rate evidence tabs, not '
             're-asserted here', 'text'),
            None, None, None, None, None, None, None], wrap=True, height=52)
    sb.note('This matter is now closed until a licensed feed exists: the row is '
            'PENDING, the three attempts are logged, and the interim anchor is '
            'named. No fourth open-ended deferral.')
    sb.blank()

    # ------------------------------------------------------- read panel ---
    sb.banner('Read panel')
    sb.prose(
        'The commercial machine-readable rate file did not land. Three regional '
        'payers - Medica, Blue Cross Blue Shield of Nebraska and Wellmark Iowa '
        '- were probed in the standing order; the transparency portals are '
        'bot-blocked (HTTP 403) or moved (404), and the one reachable data host '
        'returned only a small index stub that gates the actual multi-gigabyte '
        'in-network rate files behind plan- and EIN-specific paths that are not '
        'machine-discoverable without a licensed feed. That is the honest '
        'result, and it closes the question rather than deferring it again: the '
        'MRF commercial-rate row is PENDING with the three attempts logged, and '
        'the balance-billing statutory benchmarks stand as the interim '
        'commercial anchor on the rate-evidence bridge until a licensed '
        'transparency feed makes the payer-specific rate retrievable. No '
        'commercial ground-ambulance rate is asserted from this attempt.')

    # --------------------------------------------------------- findings ---
    findings += [
        {'id_hint': 114,
         'finding': 'The public commercial machine-readable rate file for '
                    'ground ambulance does not retrieve: three regional payers '
                    '(Medica, Blue Cross Blue Shield of Nebraska, Wellmark '
                    'Iowa) were probed in the standing order and none yielded a '
                    'reachable in-network rate - portals bot-blocked (403) or '
                    'moved (404), and the one reachable host returned only a '
                    'small index stub gating the multi-gigabyte files behind '
                    'plan/EIN-specific paths. The commercial-rate MRF row is '
                    'therefore closed as PENDING with the three attempts '
                    'logged, and the balance-billing statutory benchmarks stand '
                    'as the interim commercial anchor until a licensed feed '
                    'exists. No commercial rate is asserted.',
         'numbers': 'Three logged attempts (Panel A); no rate retrieved; row '
                    'PENDING (Panel B)',
         'sources': 'mrf_attempts',
         'confidence': 'High that the public MRF path did not retrieve under '
                       'the standing recipe; the failure is a retrieval barrier',
         'guardrail': 'A retrieval outcome, not a rate. Nothing here estimates '
                      'a commercial rate; the interim anchor is the balance-'
                      'billing statutory pegs already carried elsewhere, not a '
                      'new number.'}]

    return {'facts': facts, 'sources': sources, 'excluded': excluded,
            'findings': findings, 'meta': {}}
